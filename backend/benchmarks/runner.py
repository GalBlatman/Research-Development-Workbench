"""Administrator runner: explicit immutable reservations, bounded execution and reporting."""

import hashlib
import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Any
from uuid import uuid4

from benchmarks.evaluator import BlindEvaluator
from benchmarks.metrics import compare
from benchmarks.store import AdminStore
from benchmarks.variants import content_hash, validate_import
from domain.benchmark import (
    BenchmarkExpectation,
    BenchmarkProject,
    BenchmarkRun,
    BenchmarkVariant,
    FrozenSplit,
    InvalidCaseReport,
    Observation,
    RunConfiguration,
)
from model_adapters.contracts import ModelAdapter
from model_adapters.openai import PROMPTS, OpenAIAdapter
from model_adapters.runtime import ProviderFailure, provider_session, timestamp
from policy_engine.manifest import Manifest


@dataclass(frozen=True)
class Case:
    project: BenchmarkProject
    variant: BenchmarkVariant
    expectations: tuple[BenchmarkExpectation, ...] = ()


def estimated_cost(receipt: Any) -> float | None:
    if receipt is None or any(
        c.input_tokens is None or c.output_tokens is None for c in receipt.calls
    ):
        return None
    total = 0.0
    for c in receipt.calls:
        cached = c.usage_details.get("input_tokens_details.cached_tokens", 0)
        written = c.usage_details.get("input_tokens_details.cache_write_tokens", 0)
        if cached + written > c.input_tokens:
            return None
        total += (
            (c.input_tokens - cached - written) * c.input_usd_per_million
            + cached * c.cached_input_usd_per_million
            + written * c.cache_write_usd_per_million
            + c.output_tokens * c.output_usd_per_million
        ) / 1_000_000
    return total


class Runner:
    def __init__(
        self,
        store: AdminStore,
        runtime: Path,
        manifest: Manifest,
        splits: FrozenSplit,
        adapter_factory: Callable[[], ModelAdapter],
    ):
        self.store, self.runtime, self.manifest, self.splits, self.adapter_factory = (
            store,
            runtime,
            manifest,
            splits,
            adapter_factory,
        )
        store.require_manifest(splits)
        self.stop = Event()
        # No administrator capability is passed to BlindEvaluator or adapter.

    def execute(
        self,
        case: Case,
        config: RunConfiguration,
        references: dict[str, BenchmarkRun] | None = None,
        rerun: bool = False,
    ) -> BenchmarkRun | None:
        self.store.require_case(case.project, case.variant, self.splits, case.expectations)
        validate_import(case.project, self.splits)
        if (
            case.variant.benchmark_id != case.project.benchmark_id
            or case.variant.split != case.project.split
        ):
            raise ValueError("Cross-split execution rejected")
        reference_observations: dict[str, Observation] = {}
        for variant_id, reference in (references or {}).items():
            if (
                reference.variant_id != variant_id
                or reference.benchmark_id != case.project.benchmark_id
                or reference.split != case.project.split
                or reference.split_hash != content_hash(self.splits)
                or reference.package_hash != case.variant.package_hash
                or not (
                    reference.configuration == config
                    or (
                        config.task_version == "benchmark-v2"
                        and reference.configuration.model_copy(
                            update={"component": config.component}
                        )
                        == config
                    )
                )
            ):
                raise ValueError("Cross-split/configuration reference rejected")
            if self.store.read("runs", reference.run_id, BenchmarkRun) != reference:
                raise ValueError("Stored reference run differs")
            if reference.status == "SUCCEEDED" and reference.observation is not None:
                reference_observations[variant_id] = reference.observation
        identifier = uuid4().hex
        key = self.store.cache_key(case.variant, self.splits, config)
        if not self.store.claim(key, identifier, rerun):
            self.store.reservation_report(key)
            return None
        started, clock = timestamp(), time.monotonic()
        components: tuple[str, ...] = ()
        receipt, output, observation, result, failure = None, None, None, None, None
        adapter = None
        ledger = None
        evaluator = None
        try:
            adapter = self.adapter_factory()
            expected_calls = (
                1 if config.mode == "BASELINE" else (3 if config.component == "FULL" else 2)
            )
            if expected_calls > config.budget.max_calls:
                raise ProviderFailure("BUDGET_EXHAUSTED")
            if isinstance(adapter, OpenAIAdapter):
                pc = adapter.provider_config
                if config.provider != "openai" or config.model != pc.model:
                    raise ValueError("Runtime provider/model differs from frozen configuration")
                actual = {k: getattr(pc, k) for k, _ in config.parameters}
                if dict(config.parameters) != actual or set(actual) != set(vars(pc)) - {
                    "provider",
                    "model",
                }:
                    raise ValueError("Record every non-secret provider parameter")
                worst_cost = (
                    pc.max_run_tokens
                    * max(pc.input_rate, pc.output_rate, pc.cached_rate, pc.cache_write_rate)
                    / 1_000_000
                )
                if (
                    pc.max_calls > config.budget.max_calls
                    or pc.max_run_tokens > config.budget.max_tokens
                    or worst_cost > config.budget.max_cost_usd
                ):
                    raise ProviderFailure("BUDGET_EXHAUSTED")
            elif config.provider != "fake" or config.model != adapter.configuration:
                raise ValueError("Runtime fake configuration mismatch")
            evaluator = BlindEvaluator(
                case.variant.packet, adapter, self.manifest, self.runtime / identifier
            )
            with provider_session(adapter) as ledger:
                output, components = (
                    evaluator.run(config.mode, config.component, extended=True)
                    if config.task_version == "benchmark-v2"
                    else evaluator.run(config.mode, config.component)
                )
                observation = evaluator.observe(output)
                # Diagnostics see only administrator-approved observability at this step.
                observable = dict(case.variant.visibility)
                project = case.project.model_copy(
                    update={
                        "gold": tuple(
                            g.model_copy(update={"observable": observable.get(g.feature, False)})
                            for g in case.project.gold
                        )
                    }
                )
                if case.variant.mutation.permit_metadata:
                    project = project.model_copy(
                        update={
                            "source_package": project.source_package.model_copy(
                                update={"identifying_metadata": ()}
                            )
                        }
                    )
                result = compare(observation, case.expectations, reference_observations, project)
            receipt = ledger.receipt() if ledger else None
        except Exception as exc:
            proposed = getattr(adapter, "proposed_review", None) or getattr(
                adapter, "proposed_interpretation", None
            )
            if output is None and proposed is not None:
                output = proposed.model_dump(mode="json")
            failure = exc.code if isinstance(exc, ProviderFailure) else type(exc).__name__
            receipt = (
                exc.metadata
                if isinstance(exc, ProviderFailure)
                else (ledger.receipt() if ledger else receipt)
            )
            if receipt and not isinstance(exc, ProviderFailure):
                receipt = receipt.model_copy(
                    update={"status": "FAILED", "failure_kind": "downstream"}
                )
        finally:
            if evaluator:
                evaluator.close()
            if isinstance(adapter, OpenAIAdapter):
                adapter.close()
        prompts = tuple(
            (name, hashlib.sha256((PROMPTS / name).read_bytes()).hexdigest())
            for name in (
                "baseline-v3.md",
                "interpretation-v1.md",
                "evaluation-v3.md",
                "checking-v4.md",
                "checking-compact-v1.md",
                "workspace-v2.md",
                "workspace-check-v2.md",
                "criteria-v1.json",
                "route-questions-v1.json",
                "route-questions-v2.json",
            )
        )
        run = BenchmarkRun(
            run_id=identifier,
            variant_id=case.variant.variant_id,
            benchmark_id=case.project.benchmark_id,
            split=case.project.split,
            configuration=config,
            package_hash=content_hash(case.project),
            package_version=case.project.version,
            variant_version=case.variant.version,
            split_version=self.splits.version,
            expectations_hash=content_hash([e.model_dump(mode="json") for e in case.expectations]),
            reference_run_ids=tuple(r.run_id for _, r in sorted((references or {}).items())),
            reference_unavailable=tuple(
                sorted(
                    {
                        v
                        for e in case.expectations
                        for v in (e.reference_variant, e.degraded_reference)
                        if v and v not in reference_observations
                    }
                )
            ),
            packet_hash=case.variant.packet.packet_id,
            code_tree_hash=content_hash(
                tuple(
                    (str(p.relative_to(PROMPTS.parent)), hashlib.sha256(p.read_bytes()).hexdigest())
                    for p in sorted(
                        p
                        for module in (
                            "domain",
                            "policy_engine",
                            "persistence",
                            "services",
                            "model_adapters",
                            "api",
                            "benchmarks",
                        )
                        for p in (PROMPTS.parent / module).rglob("*.py")
                    )
                )
            ),
            policy_manifest_hash=self.manifest.sha256,
            policy_implementation_version=self.manifest.implementation_version,
            variant_hash=content_hash(case.variant),
            split_hash=content_hash(self.splits),
            rubric_hash=self.manifest.canonical_sha256,
            rubric_version=self.manifest.version,
            timestamp=started,
            duration_seconds=time.monotonic() - clock,
            components=tuple(c.task for c in receipt.calls) if receipt else components,
            prompt_hashes=prompts,
            receipt=receipt,
            calls=len(receipt.calls)
            if receipt
            else (sum(not c.startswith("fixture-") for c in components) if components else 0),
            input_tokens=sum(c.input_tokens or 0 for c in receipt.calls)
            if receipt and all(c.input_tokens is not None for c in receipt.calls)
            else None,
            output_tokens=sum(c.output_tokens or 0 for c in receipt.calls)
            if receipt and all(c.output_tokens is not None for c in receipt.calls)
            else None,
            estimated_cost_usd=estimated_cost(receipt),
            status="FAILED" if failure else "SUCCEEDED",
            failure_type=failure,
            output_json=json.dumps(output, sort_keys=True) if output else None,
            policy_json=json.dumps(output["policy"], sort_keys=True)
            if output and "policy" in output
            else None,
            observation=observation,
            result=result,
        )
        self.store.save_run(run)
        return run

    def batch(
        self,
        cases: tuple[Case, ...],
        config: RunConfiguration,
        *,
        concurrency: int = 1,
        max_calls: int,
        max_tokens: int,
        max_cost_usd: float,
        progress: Callable[[str, str], None] | None = None,
        rerun: bool = False,
        batch_id: str | None = None,
        references: dict[str, BenchmarkRun] | None = None,
    ) -> tuple[BenchmarkRun, ...]:
        if not 1 <= concurrency <= 4 or min(max_calls, max_tokens, max_cost_usd) < 0:
            raise ValueError("Invalid bounded batch configuration")
        # Conservative reservation, even on unknown usage/failure. No uncertain refunds.
        limit = min(
            max_calls // config.budget.max_calls,
            max_tokens // config.budget.max_tokens,
            int(max_cost_usd // config.budget.max_cost_usd)
            if config.budget.max_cost_usd
            else len(cases),
        )
        batch_key = content_hash(
            (
                batch_id,
                tuple(sorted(c.variant.variant_id for c in cases)),
                content_hash(self.splits),
                config.model_dump(mode="json"),
                max_calls,
                max_tokens,
                max_cost_usd,
            )
        )
        if rerun and not batch_id:
            raise ValueError("Explicit rerun requires a new batch identity")
        selected: list[Case] = []
        for case in sorted(cases, key=lambda c: (c.project.benchmark_id, c.variant.variant_id)):
            key = self.store.cache_key(case.variant, self.splits, config)
            if not rerun and self.store._path("claims", key).exists():
                report = self.store.reservation_report(key)
                if progress:
                    progress(case.variant.variant_id, report.status)
                continue
            if len(selected) >= limit or self.stop.is_set():
                break
            selected.append(case)

        def perform(case: Case) -> BenchmarkRun | None:
            if self.stop.is_set():
                return None
            if not self.store.reserve_batch_slot(batch_key, limit):
                return None
            applicable_references = {
                k: r
                for k, r in (references or {}).items()
                if r.benchmark_id == case.project.benchmark_id
                and k
                in {
                    v
                    for e in case.expectations
                    for v in (e.reference_variant, e.degraded_reference)
                    if v
                }
            }
            try:
                run = self.execute(case, config, references=applicable_references, rerun=rerun)
            except (ValueError, FileNotFoundError) as exc:
                # A malformed administrator case is isolated, not a scientific result.
                self.store.write(
                    "annotations",
                    uuid4().hex,
                    InvalidCaseReport(
                        variant_id=case.variant.variant_id, error_code=type(exc).__name__
                    ),
                )
                if progress:
                    progress(case.variant.variant_id, "INVALID_CASE")
                return None
            if progress:
                progress(case.variant.variant_id, run.status if run else "SKIPPED")
            return run

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            return tuple(r for r in pool.map(perform, selected) if r is not None)
