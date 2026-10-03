"""Synthetic fake-provider smoke CLI. No paper import or live spending command."""

import argparse
import json
import subprocess
from pathlib import Path

from benchmarks.fixtures import synthetic
from benchmarks.metrics import aggregate
from benchmarks.runner import Runner
from benchmarks.store import AdminStore
from benchmarks.variants import freeze
from domain.benchmark import RunBudget, RunConfiguration
from model_adapters.fake import FakeModel
from policy_engine.manifest import Manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="RDW-007 synthetic harness; fake provider only")
    parser.add_argument(
        "--output",
        required=True,
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
    output = args.output.resolve()
    if output == root or root in output.parents:
        parser.error("Runtime artifacts must stay outside the publication repository")
    manifest = Manifest.model_validate_json(
        (root / "policies/rubric-v4.manifest.json").read_text(encoding="utf-8")
    )
    projects, cases = synthetic()
    splits = freeze(projects, "synthetic-splits-v1")
    store = AdminStore(output / "admin")
    for category, identity, value in (
        [("splits", splits.version, splits)]
        + [("projects", p.benchmark_id, p) for p in projects]
        + [("variants", c.variant.variant_id, c.variant) for c in cases]
    ):
        try:
            store.write(category, identity, value)
        except FileExistsError:
            if store.read(category, identity, type(value)) != value:
                raise ValueError("Frozen artifact differs; use a new administrator directory")
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
