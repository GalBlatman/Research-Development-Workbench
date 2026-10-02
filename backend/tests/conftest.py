import json
from pathlib import Path

import pytest

from domain.models import (
    Assessment,
    Benchmark,
    EvaluationSnapshot,
    Finding,
    Project,
    Rating,
    Route,
    Stage,
    Status,
    Truth,
    Verification,
)
from policy_engine.manifest import Manifest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def manifest() -> Manifest:
    return Manifest.model_validate_json(
        (ROOT / "policies/rubric-v4.manifest.json").read_text(encoding="utf-8")
    )


def make_assessment(
    manifest: Manifest,
    values: list[int | None] | None = None,
    route: str = "EXPLAIN",
    stage: str = "COMPLETED STUDY",
    findings: dict[str, str] | None = None,
    study: bool = True,
    articulated: bool = True,
    benchmarks: bool = True,
) -> Assessment:
    adverse = {
        "AUDIENCE-QUESTION",
        "PREMISE-NO-BASIS",
        "PREMISE-CONDITIONAL",
        "PREMISE-CONTRADICTED",
        "NO-ADVANCE",
        "NO-CONSEQUENTIAL-STAKE",
        "DESIGN-MISMATCH",
        "INFERENCE-UNSUPPORTED",
        "PROMISE-OVERREACH",
        "STAGE-MISMATCH",
    }
    derived = {
        "ROUTE-TOTAL",
        "DISCOVERY-PENDING",
        "UNINSPECTED-BLOCK",
        "HIGH-SCORE-BENCHMARK",
        "EDITORIAL-UNCALIBRATED",
    }
    facts = {
        r.id: "FALSE" if r.id in adverse else "TRUE" for r in manifest.rules if r.id not in derived
    }
    facts.update(findings or {})
    ratings = []
    for dim, value in enumerate(values or [5] * 10, 1):
        benchmark = Benchmark(
            comparison="Synthetic published-comparison placeholder",
            dimension_reason="Synthetic dimension-specific comparison",
            published_reference="Synthetic reference, no real article text",
            inspected=True,
            relevant=True,
            verification=Verification.SUPPORTED,
        )
        ratings.append(
            Rating(
                dimension=dim,
                rating=value,
                status=Status.ASSESSED if value is not None else Status.PENDING,
                rationale="Synthetic manually supplied judgment",
                main_limitation="Synthetic fixture only",
                inspected_material=("synthetic-note",) if value is not None else (),
                verification=Verification.SUPPORTED,
                benchmark=benchmark if benchmarks and value is not None and value >= 8 else None,
            )
        )
    project = Project(
        project_id="synthetic-project",
        workspace_id="synthetic-workspace",
        title="Synthetic project",
        revision=1,
        route=Route(route),
        stage=Stage(stage),
    )
    snapshot = EvaluationSnapshot(
        snapshot_id="synthetic-snapshot",
        project=project,
        policy_version=manifest.version,
        policy_sha256=manifest.canonical_sha256,
        policy_manifest_sha256=manifest.sha256,
        policy_implementation_version=manifest.implementation_version,
        scope="FULL_EVALUATION",
    )
    return Assessment(
        snapshot=snapshot,
        account_articulated=articulated,
        study_assessable=study,
        ratings=tuple(ratings),
        findings=tuple(
            Finding(
                rule_id=k,
                value=Truth(v),
                reasoning="Explicit synthetic condition",
                scope="synthetic-snapshot",
                verification=Verification.SUPPORTED,
            )
            for k, v in facts.items()
        ),
    )


CASES = json.loads((ROOT / "policies/rubric-v4.test-fixtures.json").read_text(encoding="utf-8"))[
    "cases"
]
