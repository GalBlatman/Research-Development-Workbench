"""Authorized package preflight/import and stored-artifact execution; fake provider only."""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from benchmarks.fixtures import synthetic
from benchmarks.metrics import aggregate
from benchmarks.runner import Case, Runner
from benchmarks.store import AdminStore
from benchmarks.variants import content_hash, freeze, normalized_identity, package_identity
from domain.benchmark import (
    BenchmarkPackage,
    BenchmarkProject,
    BenchmarkRun,
    BenchmarkVariant,
    FrozenExpectations,
    FrozenSplit,
    InvalidCaseReport,
    ReservationReport,
    RunBudget,
    RunConfiguration,
)
from model_adapters.fake import FakeModel
from policy_engine.manifest import Manifest


def hashes(package: BenchmarkPackage) -> dict[str, object]:
    return {
        "package": content_hash(package),
        "split_manifest": content_hash(package.manifest),
        "papers": [
            {
                "paper_identity": package_identity(p),
                "normalized_content": normalized_identity(p),
                "project": content_hash(p),
                "gold": content_hash([g.model_dump(mode="json") for g in p.gold]),
                "source_package": content_hash(p.source_package),
            }
            for p in package.projects
        ],
        "variants": {v.variant_id: content_hash(v) for v in package.variants},
        "expectations": {e.variant_id: content_hash(e) for e in package.expectations},
    }


def stored_package(store: AdminStore, version: str) -> BenchmarkPackage:
    splits = store.read("splits", version, FrozenSplit)
    projects = {content_hash(p): p for p in store.artifacts("projects", BenchmarkProject)}
    selected = tuple(projects[h] for _, _, h in splits.assignments)
    variants = tuple(
        v
        for v in store.artifacts("variants", BenchmarkVariant)
        if v.split_hash == content_hash(splits)
    )
    expectations = tuple(
        store.read("expectations", v.variant_id, FrozenExpectations) for v in variants
    )
    return BenchmarkPackage(
        manifest=splits, projects=selected, variants=variants, expectations=expectations
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Authorized administrator harness; fake provider only"
    )
    parser.add_argument("--package", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--execute-stored", action="store_true")
    parser.add_argument("--split-version")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--mode", choices=("WORKBENCH", "BASELINE"), default="WORKBENCH")
    parser.add_argument(
        "--component",
        choices=("FULL", "Argument", "Study", "Literature", "Alternatives"),
        default="FULL",
    )
    parser.add_argument("--concurrency", type=int, default=1)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.package and (args.package.resolve() == root or root in args.package.resolve().parents):
        parser.error("Package artifacts must stay outside the publication repository")
    if args.output and (args.output.resolve() == root or root in args.output.resolve().parents):
        parser.error("Runtime artifacts must stay outside the publication repository")
    if args.execute_stored and (
        args.package or args.validate_only or not args.split_version or not args.output
    ):
        parser.error("--execute-stored requires --output and --split-version, without --package")
    if args.validate_only and not args.package:
        parser.error("--validate-only requires --package")
    if not args.output and not args.validate_only:
        parser.error("--output is required for import or execution")
    try:
        package = (
            BenchmarkPackage.model_validate_json(args.package.read_text(encoding="utf-8"))
            if args.package
            else None
        )
        if args.validate_only:
            assert package is not None
            # Existing store preflight is identical to import; absent stores remain unwritten.
            with tempfile.TemporaryDirectory() as directory:
                target = (
                    args.output / "admin"
                    if args.output and (args.output / "admin").exists()
                    else Path(directory) / "admin"
                )
                AdminStore(target).preflight_import(package)
            print("benchmark-package-v1 valid " + json.dumps(hashes(package), sort_keys=True))
            return
        assert args.output is not None
        output = args.output.resolve()
        store = AdminStore(output / "admin")
        if args.execute_stored:
            package = stored_package(store, args.split_version)
        elif package:
            store.import_package(package)
            print(
                "Authorized package imported; no evaluator execution requested "
                + json.dumps(hashes(package), sort_keys=True)
            )
            return
        else:
            projects, synthetic_cases = synthetic()
            package = BenchmarkPackage(
                manifest=freeze(projects, "synthetic-splits-v1"),
                projects=projects,
                variants=tuple(c.variant for c in synthetic_cases),
                expectations=tuple(
                    FrozenExpectations(
                        variant_id=c.variant.variant_id,
                        variant_hash=content_hash(c.variant),
                        expectations=c.expectations,
                    )
                    for c in synthetic_cases
                ),
            )
            store.import_package(package)
        by_project = {p.benchmark_id: p for p in package.projects}
        definitions = {e.variant_id: e.expectations for e in package.expectations}
        cases = tuple(
            Case(by_project[v.benchmark_id], v, definitions[v.variant_id]) for v in package.variants
        )
        policy = Manifest.model_validate_json(
            (root / "policies/rubric-v5.manifest.json").read_text(encoding="utf-8")
        )
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        config = RunConfiguration(
            mode=args.mode,
            component=args.component,
            provider="fake",
            model=FakeModel.configuration,
            budget=RunBudget(max_calls=4, max_tokens=500000, max_cost_usd=0),
            code_commit=commit,
        )
        runner = Runner(store, output / "evaluator", policy, package.manifest, FakeModel)
        references = {
            r.variant_id: r
            for r in sorted(store.artifacts("runs", BenchmarkRun), key=lambda r: r.timestamp)
            if r.configuration == config and r.split_hash == content_hash(package.manifest)
        }
        pending = list(cases)
        while pending:
            ready = [
                c
                for c in pending
                if all(
                    v in references
                    for e in c.expectations
                    for v in (e.reference_variant, e.degraded_reference)
                    if v
                )
            ]
            # Cyclic/missing comparison references do not prevent independent evaluation.
            # Their comparisons remain explicitly unavailable; no model call is replayed.
            if not ready:
                ready = pending[:]
            completed = runner.batch(
                tuple(ready),
                config,
                references=references,
                concurrency=args.concurrency,
                max_calls=4 * len(ready),
                max_tokens=500000 * len(ready),
                max_cost_usd=0,
                progress=lambda v, status: print(v + ": " + status),
            )
            references.update({r.variant_id: r for r in completed})
            pending = [c for c in pending if c not in ready]
        annotations = tuple(
            InvalidCaseReport.model_validate_json(p.read_text(encoding="utf-8"))
            if "variant_id" in json.loads(p.read_text(encoding="utf-8"))
            else ReservationReport.model_validate_json(p.read_text(encoding="utf-8"))
            for p in (store.root / "annotations").glob("*.json")
        )
        print(json.dumps(aggregate(store.artifacts("runs", BenchmarkRun), annotations), indent=2))
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(1, "BENCHMARK_IMPORT_OR_EXECUTION_FAILED: " + type(exc).__name__ + "\n")


if __name__ == "__main__":
    main()
