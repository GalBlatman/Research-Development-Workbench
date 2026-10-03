"""Synthetic fake-provider smoke CLI. No paper import or live spending command."""

import argparse
import json
import subprocess
from collections.abc import Callable
from functools import partial
from pathlib import Path

from benchmarks.fixtures import synthetic
from benchmarks.metrics import aggregate
from benchmarks.runner import Runner
from benchmarks.store import AdminStore
from benchmarks.variants import freeze
from domain.benchmark import BenchmarkPackage, RunBudget, RunConfiguration
from domain.models import Frozen
from model_adapters.fake import FakeModel
from policy_engine.manifest import Manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="RDW-007 synthetic harness; fake provider only")
    parser.add_argument("--package", type=Path, help="Authorized administrator package JSON")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument(
        "--output",
        required=False,
        type=Path,
        help="Explicit private administrator runtime directory outside repository",
    )
    parser.add_argument("--mode", choices=("WORKBENCH", "BASELINE"), default="WORKBENCH")
    parser.add_argument(
        "--component",
        choices=("FULL", "Argument", "Study", "Literature", "Alternatives"),
        default="FULL",
    )
    parser.add_argument("--concurrency", type=int, default=1)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    package = (
        BenchmarkPackage.model_validate_json(args.package.read_text(encoding="utf-8"))
        if args.package
        else None
    )
    if args.validate_only:
        if package is None:
            parser.error("--validate-only requires --package")
        print("benchmark-package-v1 valid")
        return
    if args.output is None:
        parser.error("--output is required for import or synthetic execution")
    output = args.output.resolve()
    if output == root or root in output.parents:
        parser.error("Runtime artifacts must stay outside the publication repository")
    manifest = Manifest.model_validate_json(
        (root / "policies/rubric-v5.manifest.json").read_text(encoding="utf-8")
    )
    projects, cases = synthetic()
    splits = freeze(projects, "synthetic-splits-v1")
    store = AdminStore(output / "admin")
    if package is not None:
        from benchmarks.runner import Case

        projects, splits = package.projects, package.manifest
        definitions = {e.variant_id: e.expectations for e in package.expectations}
        by_id = {p.benchmark_id: p for p in projects}
        cases = tuple(
            Case(by_id[v.benchmark_id], v, definitions[v.variant_id]) for v in package.variants
        )
    operations: list[tuple[str, str, Frozen, Callable[[], None]]] = [
        ("splits", splits.version, splits, partial(store.freeze, splits))
    ]
    operations += [
        (
            "projects",
            p.benchmark_id + ":" + p.version,
            p,
            partial(store.import_project, p, splits),
        )
        for p in projects
    ]
    for category, identity, value, operation in operations:
        try:
            operation()
        except FileExistsError:
            if store.read(category, identity, type(value)) != value:
                raise ValueError("Frozen artifact differs; use a new version")
    for case in cases:
        try:
            store.save_variant(case.variant, case.project, splits)
        except FileExistsError:
            if store.read("variants", case.variant.variant_id, type(case.variant)) != case.variant:
                raise ValueError("Frozen variant differs")
        try:
            store.freeze_expectations(case.variant, case.expectations)
        except FileExistsError:
            from domain.benchmark import FrozenExpectations

            if (
                store.read("expectations", case.variant.variant_id, FrozenExpectations).expectations
                != case.expectations
            ):
                raise ValueError("Frozen expectations differ")
    if package is not None:
        print("Authorized package imported; no evaluator execution requested")
        return
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    config = RunConfiguration(
        mode=args.mode,
        component=args.component,
        provider="fake",
        model=FakeModel.configuration,
        budget=RunBudget(max_calls=4, max_tokens=500000, max_cost_usd=0),
        code_commit=commit,
    )
    runner = Runner(store, output / "evaluator", manifest, splits, FakeModel)
    runs = runner.batch(
        cases,
        config,
        concurrency=args.concurrency,
        max_calls=4 * len(cases),
        max_tokens=500000 * len(cases),
        max_cost_usd=0,
        progress=lambda v, s: print(v + ": " + s),
    )
    print(json.dumps(aggregate(runs), indent=2))


if __name__ == "__main__":
    main()
