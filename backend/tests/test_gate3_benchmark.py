import json
from pathlib import Path

import pytest

from benchmarks.fixtures import synthetic
from benchmarks.store import AdminStore
from benchmarks.variants import content_hash, freeze
from domain.benchmark import BenchmarkPackage, FrozenExpectations, Split


def exchange():
    projects, cases = synthetic()
    return BenchmarkPackage(
        manifest=freeze(projects, "synthetic-splits-v1"),
        projects=projects,
        variants=tuple(c.variant for c in cases),
        expectations=tuple(
            FrozenExpectations(
                variant_id=c.variant.variant_id,
                variant_hash=content_hash(c.variant),
                expectations=c.expectations,
            )
            for c in cases
        ),
    )


def test_external_package_roundtrip_and_schema():
    package = exchange()
    assert BenchmarkPackage.model_validate_json(package.model_dump_json()) == package
    schema = json.loads(
        (Path(__file__).resolve().parents[2] / "evals/benchmark-package-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert schema == BenchmarkPackage.model_json_schema()
    malformed = package.model_dump(mode="json")
    malformed["projects"][0]["gold"][0]["source_anchors"] = ["missing-block"]
    with pytest.raises(ValueError):
        BenchmarkPackage.model_validate(malformed)


def test_permanent_split_and_content_identity_across_manifest_versions(tmp_path):
    package = exchange()
    store = AdminStore(tmp_path)
    store.freeze(package.manifest)
    first = package.projects[0]
    store.import_project(first, package.manifest)
    changed = first.model_copy(update={"split": Split.HELD_OUT})
    with pytest.raises(ValueError, match="split"):
        store.freeze(freeze((changed,), "new-splits"))
    duplicate = first.model_copy(update={"benchmark_id": "new-label", "split": Split.HELD_OUT})
    new = freeze((duplicate,), "duplicate-splits")
    with pytest.raises(ValueError, match="relabeled"):
        store.freeze(new)


def test_manifest_and_expectations_must_be_stored(tmp_path):
    package = exchange()
    store = AdminStore(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.require_manifest(package.manifest)
    store.freeze(package.manifest)
    for project in package.projects:
        store.import_project(project, package.manifest)
    case = synthetic()[1][0]
    store.save_variant(case.variant, case.project, package.manifest)
    with pytest.raises(FileNotFoundError):
        store.require_case(case.project, case.variant, package.manifest, case.expectations)
    store.freeze_expectations(case.variant, case.expectations)
    store.require_case(case.project, case.variant, package.manifest, case.expectations)
    with pytest.raises(FileExistsError):
        store.freeze_expectations(case.variant, ())


def test_paired_order_is_stable():
    _, cases = synthetic()
    packets = {
        c.variant.variant_id.split("synthetic-EXPLAIN-")[-1]: c.variant.packet
        for c in cases
        if c.project.route == "EXPLAIN"
    }
    intact = packets["intact"].blocks
    degraded = packets["degraded"].blocks
    assert degraded[0] == intact[0] and degraded[2] == intact[2]
    assert "meeting attendance" in degraded[1].text
    assert packets["restored"].blocks == intact
    assert packets["hidden"].blocks == (intact[0], intact[2])


def test_external_style_cli_validates_imports_without_evaluating(tmp_path):
    import os
    import subprocess
    import sys

    package = tmp_path / "synthetic-exchange.json"
    package.write_text(exchange().model_dump_json(), encoding="utf-8")
    backend = Path(__file__).resolve().parents[1]
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    validate = subprocess.run(
        [sys.executable, "-m", "benchmarks", "--package", str(package), "--validate-only"],
        cwd=backend,
        env=env,
        capture_output=True,
        text=True,
    )
    assert validate.returncode == 0, validate.stderr
    output = tmp_path / "imported"
    imported = subprocess.run(
        [sys.executable, "-m", "benchmarks", "--package", str(package), "--output", str(output)],
        cwd=backend,
        env=env,
        capture_output=True,
        text=True,
    )
    assert imported.returncode == 0, imported.stderr
    assert len(list((output / "admin/expectations").glob("*.json"))) == len(exchange().variants)
    assert not (output / "evaluator").exists()
    assert not (output / "admin/runs").exists()


@pytest.mark.parametrize(
    "fault", ("state", "feature", "parent", "hash", "version", "packet", "judgment")
)
def test_malformed_semantic_exchange_rejected(fault):
    data = exchange().model_dump(mode="json")
    if fault == "state":
        data["expectations"][1]["expectations"][0]["acceptable_states"] = ["PENDNG"]
    elif fault == "judgment":
        data["expectations"][1]["expectations"][0]["judgment"] = "finding:MISSPELLED-RULE"
    elif fault == "feature":
        data["projects"][0]["gold"][0]["feature"] = "unrecognized_feature"
    elif fault == "parent":
        data["variants"][5]["mutation"]["parent_variant"] = "unknown-parent"
    elif fault == "hash":
        data["variants"][0]["package_hash"] = "0" * 64
    elif fault == "version":
        data["variants"][0]["version"] = "forged-version"
    else:
        data["variants"][0]["packet"]["blocks"].reverse()
    with pytest.raises(ValueError):
        BenchmarkPackage.model_validate(data)


def test_invalid_case_isolated_and_failed_runs_remain_reported(tmp_path, manifest):
    from test_benchmarks import configuration, runner

    from benchmarks.metrics import aggregate
    from benchmarks.runner import Case

    r, _, cases = runner(tmp_path, manifest)
    bad = Case(cases[0].project, cases[0].variant.model_copy(update={"variant_id": "aaa-invalid"}))
    progress = []
    runs = r.batch(
        (bad, cases[0]),
        configuration("BASELINE"),
        max_calls=8,
        max_tokens=1000000,
        max_cost_usd=10,
        progress=lambda identity, status: progress.append(status),
    )
    assert "INVALID_CASE" in progress and len(runs) == 1
    assert list((tmp_path / "admin/annotations").glob("*.json"))
    failed = runs[0].model_copy(
        update={
            "run_id": "failed-original",
            "status": "FAILED",
            "result": None,
            "variant_id": "different-variant",
        }
    )
    report = aggregate((runs[0], failed))
    mode = report["papers"][runs[0].benchmark_id]["BASELINE"]
    assert mode["cases"] == 2 and mode["failed"] == 1
    duplicate = runs[0].model_copy(update={"run_id": "explicit-rerun", "timestamp": "9999"})
    report = aggregate((runs[0], duplicate))
    assert report["case_count"] == 1
    assert report["papers"][runs[0].benchmark_id]["BASELINE"]["excluded_duplicate_reruns"] == 1
