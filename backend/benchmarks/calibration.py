"""DEVELOPMENT-only administrator orchestration; metadata never crosses the blind boundary."""

import argparse
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from benchmarks.calibration_adapter import CalibrationAdapter
from benchmarks.metrics import aggregate
from benchmarks.runner import Case, Runner
from benchmarks.store import AdminStore
from benchmarks.variants import content_hash
from domain.benchmark import BenchmarkPackage, BenchmarkRun, RunBudget, RunConfiguration, Split
from model_adapters.config import ProviderConfig
from policy_engine.manifest import Manifest

FILES = {
    "benchmark-completed-development.json": "554ef5d7210d3ce0f2be20cfa15afb792ee21f75ee2ecb373410363f4d4311b9",
    "benchmark-early-development.json": "8a3c6fc8b12ada7c0d37710c39f9831e2472b7cdc9db312ef9b24a9b09198bf5",
    "benchmark-proposal-development.json": "94359b97e6031ce76aa1d315b25adab605745549a76a2d3db2e6164e8dc13ce6",
    "handoff-manifest.json": "a5177e93099135e6ac0d2cdf695aae8f667b7c4548b2f8fded76d5f46316701d",
    "development-admin-sidecar.json": "25389eff72ffc04b920af309547475e9a1f8c59a64196bcbbee9848147d59ce8",
}
COMPONENTS = {"Argument", "Brief", "Literature", "Study", "Usefulness", "Alternatives"}


def provider_identity(pc: ProviderConfig) -> dict[str, Any]:
    """Equivalent constructor/environment numerics have one frozen identity."""
    values = asdict(pc)
    for key in ("timeout", "input_rate", "cached_rate", "cache_write_rate", "output_rate"):
        values[key] = float(values[key])
    return values


def preflight(handoff: Path) -> tuple[tuple[BenchmarkPackage, ...], dict[str, Any]]:
    data = {}
    for name, digest in FILES.items():
        raw = (handoff / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("HANDOFF_HASH_MISMATCH")
        data[name] = json.loads(raw)
    packages = tuple(
        BenchmarkPackage.model_validate(data[n]) for n in FILES if n.startswith("benchmark-")
    )
    sidecar = data["development-admin-sidecar.json"]
    if sidecar["split"] != "DEVELOPMENT" or sidecar["access_scope"] != "ADMINISTRATOR_ONLY":
        raise ValueError("DEVELOPMENT_ADMIN_BOUNDARY_REQUIRED")
    if sidecar["existing_handoff_manifest_sha256"] != FILES["handoff-manifest.json"]:
        raise ValueError("SIDECAR_HANDOFF_MISMATCH")
    projects = {p.benchmark_id: p for package in packages for p in package.projects}
    variants = {v.variant_id: v for package in packages for v in package.variants}
    if any(p.split != Split.DEVELOPMENT for package in packages for p in package.projects) or any(
        v.split != Split.DEVELOPMENT for v in variants.values()
    ):
        raise ValueError("NON_DEVELOPMENT_EXECUTION_REJECTED")
    cases = {c["case_id"]: c for c in sidecar["cases"]}
    papers = {p["private_paper_id"]: p for p in sidecar["papers"]}
    if len(cases) != len(sidecar["cases"]) or len(cases) != 440 or set(cases) != set(variants):
        raise ValueError("SIDECAR_CASE_JOIN_MISMATCH")
    if (
        len(papers) != len(sidecar["papers"])
        or len(papers) != 20
        or set(papers) != {p.paper_identity for p in projects.values()}
    ):
        raise ValueError("SIDECAR_PAPER_JOIN_MISMATCH")
    for identifier, mapping in cases.items():
        variant = variants[identifier]
        project = projects[variant.benchmark_id]
        if (mapping["private_paper_id"], mapping["route"], mapping["stage"]) != (
            project.paper_identity,
            project.route,
            variant.packet.stage,
        ):
            raise ValueError("SIDECAR_SCIENTIFIC_IDENTITY_MISMATCH")
        if mapping["execution_scope"] == "TARGETED_COMPONENT":
            if mapping["target_component"] not in COMPONENTS:
                raise ValueError("UNKNOWN_CANONICAL_COMPONENT")
        elif mapping["execution_scope"] == "FULL_WORKBENCH":
            if (
                not mapping.get("target_components")
                or not set(mapping["target_components"]) <= COMPONENTS
            ):
                raise ValueError("UNKNOWN_INTEGRATED_COMPONENT")
        else:
            raise ValueError("UNKNOWN_EXECUTION_SCOPE")
    if Counter(c["execution_scope"] for c in cases.values()) != {
        "TARGETED_COMPONENT": 253,
        "FULL_WORKBENCH": 187,
    }:
        raise ValueError("ROUTING_COUNT_MISMATCH")
    lineages = {
        entry["derived_filename"]: entry for entry in data["handoff-manifest.json"]["lineage"]
    }
    for name, package in zip(
        (name for name in FILES if name.startswith("benchmark-")), packages, strict=True
    ):
        lineage = lineages[name]
        if (
            content_hash(package) != lineage["derived_canonical_sha256"]
            or content_hash(package.manifest) != lineage["derived_manifest_canonical_sha256"]
        ):
            raise ValueError("FROZEN_LINEAGE_MISMATCH")
    return packages, sidecar


def configuration(pc: ProviderConfig, component: str, mode: str, commit: str) -> RunConfiguration:
    worst = (
        pc.max_run_tokens
        * max(pc.input_rate, pc.output_rate, pc.cached_rate, pc.cache_write_rate)
        / 1_000_000
    )
    return RunConfiguration.model_validate(
        dict(
            mode=mode,
            component=component,
            provider="openai",
            model=pc.model,
            parameters=tuple(
                (k, v) for k, v in provider_identity(pc).items() if k not in ("provider", "model")
            ),
            budget=RunBudget(
                max_calls=pc.max_calls, max_tokens=pc.max_run_tokens, max_cost_usd=worst
            ),
            code_commit=commit,
            task_version="benchmark-v2",
        )
    )


def freeze(path: Path, value: dict[str, Any]) -> None:
    text = json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise ValueError("FROZEN_CALIBRATION_CONFIGURATION_CHANGED")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)


def uncertain_attempts(
    previous_outputs: tuple[Path, ...], packages: tuple[BenchmarkPackage, ...]
) -> tuple[BenchmarkRun, ...]:
    """Carry immutable uncertain failures as unavailable, never as valid science."""
    selected: dict[tuple[str, str], BenchmarkRun] = {}
    for previous in previous_outputs:
        for package in packages:
            folder = previous / "admin" / package.manifest.version / "runs"
            variants = {v.variant_id: v for v in package.variants}
            for path in sorted(folder.glob("*.json")):
                run = BenchmarkRun.model_validate_json(path.read_text(encoding="utf-8"))
                if run.failure_type not in {"TIMEOUT_UNCERTAIN", "TRANSPORT_ERROR_UNCERTAIN"}:
                    continue
                variant = variants.get(run.variant_id)
                if (
                    variant is None
                    or run.split != Split.DEVELOPMENT
                    or run.status != "FAILED"
                    or run.observation is not None
                    or run.variant_hash != content_hash(variant)
                    or run.split_hash != content_hash(package.manifest)
                ):
                    raise ValueError("INVALID_UNCERTAIN_CARRY_FORWARD")
                selected[(run.configuration.mode, run.variant_id)] = run
    return tuple(selected.values())


def interrupted_reservations(
    previous_outputs: tuple[Path, ...],
    packages: tuple[BenchmarkPackage, ...],
    sidecar: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Bind unfinished claims to admitted cases; never invent usage or replay them."""
    mappings = {c["case_id"]: c for c in sidecar["cases"]}
    selected = []
    for previous in previous_outputs:
        frozen = []
        for name in ("configuration.json", "pilot-configuration.json"):
            path = previous / "admin" / name
            if path.exists():
                frozen.append(json.loads(path.read_text(encoding="utf-8")))
        for package in packages:
            directory = previous / "admin" / package.manifest.version
            if not directory.exists():
                continue
            store = AdminStore(directory)
            runs = store.artifacts("runs", BenchmarkRun)
            completed = {r.run_id for r in runs}
            pending = {}
            for path in (directory / "claims").glob("*.json"):
                claim = json.loads(path.read_text(encoding="utf-8"))
                if claim["run_id"] not in completed:
                    pending[path.name] = claim
            if not pending:
                continue
            configs = {content_hash(r.configuration): r.configuration for r in runs}
            for record in frozen:
                pc = ProviderConfig(**record["provider"])
                for mode in ("WORKBENCH", "BASELINE"):
                    cfg = configuration(pc, "FULL", mode, record["commit"])
                    # Preserve pre-normalization claim bytes as well as the canonical form.
                    # Frozen JSON sorts object keys; original parameter order is dataclass order.
                    raw = cfg.model_copy(
                        update={
                            "parameters": tuple(
                                (k, record["provider"][k])
                                for k in asdict(pc)
                                if k not in ("provider", "model")
                            )
                        }
                    )
                    configs[content_hash(cfg)] = cfg
                    configs[content_hash(raw)] = raw
            matched = set()
            for variant in package.variants:
                mapping = mappings[variant.variant_id]
                component = (
                    "FULL"
                    if mapping["execution_scope"] == "FULL_WORKBENCH"
                    else mapping["target_component"]
                )
                for config in configs.values():
                    config = config.model_copy(update={"component": component})
                    key = store.cache_key(variant, package.manifest, config)
                    name = content_hash(key) + ".json"
                    if name not in pending or name in matched:
                        continue
                    report = store.reservation_report(key)
                    selected.append(
                        {
                            "mode": config.mode,
                            "variant_id": variant.variant_id,
                            "variant_hash": content_hash(variant),
                            "split_hash": content_hash(package.manifest),
                            "configuration": config.model_dump(mode="json"),
                            "reservation": report.model_dump(mode="json"),
                            "source": str(directory),
                            "calls": None,
                            "usage": None,
                            "cost": None,
                        }
                    )
                    matched.add(name)
            if matched != set(pending):
                raise ValueError("UNBOUND_INTERRUPTED_RESERVATION")
    return tuple(selected)


def run_development(
    handoff: Path,
    output: Path,
    *,
    execute: bool,
    concurrency: int = 2,
    paper_batch: int = 4,
    limit: int | None = None,
    previous_outputs: tuple[Path, ...] = (),
) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    if (
        output.resolve() == root
        or root in output.resolve().parents
        or output.resolve() == handoff.resolve()
        or handoff.resolve() in output.resolve().parents
    ):
        raise ValueError("PRIVATE_RUNTIME_MUST_BE_SEPARATE")
    if not 1 <= concurrency <= 4 or not 1 <= paper_batch <= 5:
        raise ValueError("INVALID_BOUNDED_BATCH")
    packages, sidecar = preflight(handoff)
    if not execute:
        return {
            "preflight": "PASS",
            "papers": 20,
            "cases": 440,
            "targeted": 253,
            "full": 187,
            "provider_calls": 0,
        }
    pc = replace(ProviderConfig.environment(), provider="openai")
    carried = uncertain_attempts(previous_outputs, packages)
    interrupted = interrupted_reservations(previous_outputs, packages, sidecar)
    excluded = {(r.configuration.mode, r.variant_id) for r in carried}
    excluded.update((r["mode"], r["variant_id"]) for r in interrupted)
    policy = Manifest.model_validate_json(
        (root / "policies/rubric-v5.manifest.json").read_text(encoding="utf-8")
    )
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip():
        raise ValueError("CALIBRATION_REQUIRES_CLEAN_FROZEN_COMMIT")
    freeze(
        output / "admin" / "configuration.json",
        {
            "commit": commit,
            "policy": policy.model_dump(mode="json"),
            "handoff_hashes": FILES,
            "provider": provider_identity(pc),
            "concurrency": concurrency,
            "paper_batch": paper_batch,
            "task_version": "benchmark-v2",
            "sidecar_admission": "ADMINISTRATOR_ONLY",
            "uncertain_carried_runs": [r.model_dump(mode="json") for r in carried],
            "interrupted_uncertain_reservations": interrupted,
            "max_reserved_calls": 880 * pc.max_calls,
            "max_reserved_tokens": 880 * pc.max_run_tokens,
            "max_reserved_cost_usd": 880
            * pc.max_run_tokens
            * max(pc.input_rate, pc.output_rate, pc.cached_rate, pc.cache_write_rate)
            / 1_000_000,
        },
    )
    mappings = {c["case_id"]: c for c in sidecar["cases"]}
    case_metadata = {
        v.variant_id: {
            "transformation": v.mutation.transformation,
            "manipulation": "combined"
            if len(v.mutation.targets) > 1
            else "single"
            if v.mutation.targets
            else "none",
        }
        for package in packages
        for v in package.variants
    }
    all_runs: list[BenchmarkRun] = list(carried)
    remaining = limit
    for package in packages:
        store = AdminStore(output / "admin" / package.manifest.version)
        store.import_package(package)
        runner = Runner(
            store,
            output / "evaluator" / package.manifest.version,
            policy,
            package.manifest,
            lambda: CalibrationAdapter(pc),
        )
        projects = {p.benchmark_id: p for p in package.projects}
        expectations = {e.variant_id: e.expectations for e in package.expectations}
        cases = [
            Case(projects[v.benchmark_id], v, expectations[v.variant_id]) for v in package.variants
        ]
        papers = sorted(
            {c.project.paper_identity for c in cases if c.project.paper_identity is not None}
        )
        for start in range(0, len(papers), paper_batch):
            selected_papers = set(papers[start : start + paper_batch])
            for mode in ("WORKBENCH", "BASELINE"):
                references = {
                    r.variant_id: r
                    for r in sorted(
                        store.artifacts("runs", BenchmarkRun), key=lambda r: r.timestamp
                    )
                    if r.configuration.model_dump(exclude={"component"})
                    == configuration(pc, "FULL", mode, commit).model_dump(exclude={"component"})
                }
                pending = sorted(
                    (
                        c
                        for c in cases
                        if c.project.paper_identity in selected_papers
                        and (mode, c.variant.variant_id) not in excluded
                    ),
                    key=lambda c: c.variant.variant_id,
                )
                while pending:
                    ready = [
                        c
                        for c in pending
                        if all(
                            v in references or (mode, v) in excluded
                            for e in c.expectations
                            for v in (e.reference_variant, e.degraded_reference)
                            if v
                        )
                    ]
                    if not ready:
                        ready = pending[:]
                    ready = ready[:concurrency]
                    if remaining is not None:
                        ready = ready[:remaining]
                    if not ready:
                        return summarize(
                            tuple(all_runs) + store.artifacts("runs", BenchmarkRun),
                            sidecar,
                            interrupted=interrupted,
                        )

                    def perform(case: Case) -> BenchmarkRun | None:
                        mapping = mappings[case.variant.variant_id]
                        component = (
                            "FULL"
                            if mapping["execution_scope"] == "FULL_WORKBENCH"
                            else mapping["target_component"]
                        )
                        config = configuration(pc, component, mode, commit)
                        needed = {
                            v
                            for e in case.expectations
                            for v in (e.reference_variant, e.degraded_reference)
                            if v
                        }
                        return runner.execute(
                            case, config, {v: references[v] for v in needed if v in references}
                        )

                    with ThreadPoolExecutor(max_workers=concurrency) as pool:
                        completed = tuple(pool.map(perform, ready))
                    for case, run in zip(ready, completed, strict=True):
                        if run is not None:
                            references[run.variant_id] = run
                            print(
                                json.dumps(
                                    {
                                        "mode": mode,
                                        "status": run.status,
                                        "failure": run.failure_type,
                                        "calls": run.calls,
                                        "completed_in_package": len(references),
                                    }
                                ),
                                flush=True,
                            )
                            if run.failure_type in {
                                "AUTHENTICATION_FAILED",
                                "MODEL_UNAVAILABLE",
                                "BLOCKED_CREDENTIAL",
                                "PERMISSION_DENIED",
                                "RATE_LIMIT",
                            }:
                                raise ValueError("EXTERNAL_PROVIDER_BLOCKER:" + run.failure_type)
                    pending = [c for c in pending if c not in ready]
                    if remaining is not None:
                        remaining -= len(ready)
        all_runs.extend(store.artifacts("runs", BenchmarkRun))
    result = summarize(tuple(all_runs), sidecar, case_metadata, interrupted=interrupted)
    freeze(output / "admin" / "initial-results.json", result)
    return result


def summarize(
    runs: tuple[BenchmarkRun, ...],
    sidecar: dict[str, Any],
    case_metadata: dict[str, dict[str, str]] | None = None,
    *,
    interrupted: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    cases = {c["case_id"]: c for c in sidecar["cases"]}
    runs = tuple(
        r.model_copy(update={"benchmark_id": cases[r.variant_id]["private_paper_id"]}) for r in runs
    )
    papers = {p["private_paper_id"]: p for p in sidecar["papers"]}
    groups: dict[str, list[BenchmarkRun]] = defaultdict(list)
    for run in runs:
        c = cases[run.variant_id]
        p = papers[c["private_paper_id"]]
        for field, value in (
            ("route", c["route"]),
            ("stage", c["stage"]),
            ("component", run.configuration.component),
            ("execution_scope", c["execution_scope"]),
            ("journal", p["journal"]),
            ("interest_proximity", p["interest_proximity"]),
            ("substantive_area", p["primary_substantive_area"]),
        ):
            groups[field + ":" + str(value)].append(run)
        for method in p["method_families"]:
            groups["method:" + method].append(run)
        for component in c.get("target_components", [c.get("target_component")]):
            groups["component_membership:" + str(component)].append(run)
        for field, value in (case_metadata or {}).get(run.variant_id, {}).items():
            groups[field + ":" + value].append(run)
    names = (
        "detection",
        "invariance",
        "withholding",
        "state",
        "restoration",
        "direction",
        "attribution",
        "action",
    )
    totals: dict[str, Any] = {}
    for mode in ("WORKBENCH", "BASELINE"):
        selected = [r for r in runs if r.configuration.mode == mode]
        totals[mode] = {}
        for name in names:
            metrics = [getattr(m, name) for r in selected if r.result for m in r.result.metrics]
            n, d = sum(m.numerator for m in metrics), sum(m.denominator for m in metrics)
            paper_rates = []
            for paper in {r.benchmark_id for r in selected}:
                pm = [
                    getattr(m, name)
                    for r in selected
                    if r.benchmark_id == paper and r.result
                    for m in r.result.metrics
                ]
                pn, pd = sum(m.numerator for m in pm), sum(m.denominator for m in pm)
                if pd:
                    paper_rates.append(pn / pd)
            totals[mode][name] = {
                "numerator": n,
                "denominator": d,
                "case_rate": n / d if d else None,
                "paper_macro_rate": sum(paper_rates) / len(paper_rates) if paper_rates else None,
                "papers_with_available_metric": len(paper_rates),
            }
        uncertain = len({r["variant_id"] for r in interrupted if r["mode"] == mode})
        total = len(selected) + uncertain
        totals[mode]["failure_rate"] = (
            (sum(r.status != "SUCCEEDED" for r in selected) + uncertain) / total if total else None
        )

    return {
        "overall": aggregate(runs),
        "metric_totals": totals,
        "strata": {k: aggregate(tuple(v)) for k, v in groups.items()},
        "calls": sum(r.calls for r in runs),
        "input_tokens": sum(r.input_tokens or 0 for r in runs),
        "output_tokens": sum(r.output_tokens or 0 for r in runs),
        "estimated_cost_usd": sum(r.estimated_cost_usd or 0 for r in runs),
        "latency_seconds": sum(r.duration_seconds for r in runs),
        "unknown_usage_runs": sum(
            r.calls > 0 and (r.input_tokens is None or r.output_tokens is None) for r in runs
        ),
        "unknown_cost_runs": sum(r.calls > 0 and r.estimated_cost_usd is None for r in runs),
        "interrupted_uncertain_reservations": interrupted,
        "unknown_call_reservations": len(interrupted),
        "independence_unit": "paper; variants are nested observations",
        "validation_cases_executed": 0,
        "held_out_cases_executed": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--paper-batch", type=int, default=4)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--previous-output", type=Path, action="append", default=[])
    args = parser.parse_args()
    try:
        result = run_development(
            args.handoff,
            args.output,
            execute=args.execute,
            concurrency=args.concurrency,
            paper_batch=args.paper_batch,
            limit=args.limit,
            previous_outputs=tuple(args.previous_output),
        )
    except (ValueError, OSError, KeyError) as exc:
        print(
            "CALIBRATION_BLOCKED:"
            + (
                str(exc)
                if str(exc).startswith("EXTERNAL_PROVIDER_BLOCKER:")
                else type(exc).__name__
            ),
            flush=True,
        )
        raise SystemExit(1) from None
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k
                not in (
                    "overall",
                    "strata",
                    "metric_totals",
                    "interrupted_uncertain_reservations",
                )
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
