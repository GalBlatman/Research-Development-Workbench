import json
import sys
from pathlib import Path

import pytest
from test_benchmarks import runner
from test_gate3_final_metrics import manifest as manifest

from benchmarks.evaluator import BlindEvaluator
from benchmarks.fixtures import synthetic
from benchmarks.metrics import compare
from domain.benchmark import BenchmarkExpectation, Feature, Judgment, Observation
from model_adapters.fake import FakeModel
from model_adapters.openai import policy_contract
from services import pilot


@pytest.mark.parametrize("behavior", ("withhold", "unresolved", "not_inspected", "refuse_infer"))
@pytest.mark.parametrize(
    "constraints",
    (
        {"acceptable_scientific_states": ("assessed",)},
        {"acceptable_states": ("supported",)},
        {"acceptable_scientific_states": ("pending",), "forbidden_states": ("pending",)},
        {
            "forbidden_scientific_states": (
                "unresolved",
                "not_inspected",
                "NOT INSPECTED",
                "pending",
                "UNKNOWN",
            )
        },
    ),
)
def test_impossible_withholding_cannot_freeze(tmp_path, manifest, behavior, constraints):
    r, _, cases = runner(tmp_path, manifest)
    e = BenchmarkExpectation(
        feature=Feature.QUESTION, behavior=behavior, judgment="rating:1", **constraints
    )
    with pytest.raises(ValueError):
        e.validate_constraints()
    with pytest.raises(ValueError):
        r.store.freeze_expectations(cases[0].variant, (e,))


def test_restoration_after_judgment_disappears():
    intact = Observation(judgments=(Judgment(key="rating:8", state="assessed", value=7),))
    absent = Observation(judgments=())
    e = BenchmarkExpectation(
        feature=Feature.MEASURES,
        behavior="restore",
        judgment="rating:8",
        reference_variant="intact",
        degraded_reference="degraded",
    )
    project = synthetic()[0][0]
    refs = {"intact": intact, "degraded": absent}
    success = compare(intact, (e,), refs, project).metrics[0].restoration
    failed = compare(absent, (e,), refs, project).metrics[0].restoration
    assert (success.numerator, success.denominator) == (1, 1)
    # A supplied degraded observation distinguishes missing judgment from missing reference.
    assert (failed.numerator, failed.denominator) == (0, 1)
    assert (
        compare(intact, (e,), {"intact": intact}, project).metrics[0].restoration.denominator == 0
    )


@pytest.mark.parametrize("route", ("ESTABLISH", "TEST"))
def test_v5_canonical_route_items_preserve_exact_wording(tmp_path, manifest, route):
    case = next(c for c in synthetic()[1] if c.project.route == route)
    evaluator = BlindEvaluator(case.variant.packet, FakeModel(), manifest, tmp_path / "blind")
    try:
        questions = policy_contract(evaluator.task("FULL"))["route_questions"]
        old = json.loads(
            (Path(__file__).resolve().parents[1] / "prompts/route-questions-v1.json").read_text(
                encoding="utf-8"
            )
        )[route]
        assert list(questions.values()) == list(old.values())
        assert policy_contract(evaluator.task("FULL"))["route_assessment_key_map"] == {
            key: key for key in questions
        }
        assert tuple(questions) == (
            "knowledge_need",
            "increment",
            "scope_precision",
            "capacity_to_learn",
            "evidence_strategy",
            "next_use",
        )
    finally:
        evaluator.close()


@pytest.mark.parametrize(
    "code",
    (
        "ADMIN_ARTIFACT_IDENTITY_INTEGRITY_FAILED",
        "ADMIN_MANIFEST_REFERENCE_INTEGRITY_FAILED",
        "ADMIN_VARIANT_CONTENT_INTEGRITY_FAILED",
        "ADMIN_EXPECTATION_REFERENCE_INTEGRITY_FAILED",
        "ADMIN_VARIANT_REFERENCE_INTEGRITY_FAILED",
        "ADMIN_RUN_REFERENCE_INTEGRITY_FAILED",
    ),
)
def test_operator_preserves_admin_integrity_code(monkeypatch, capsys, code):
    def fail(**kwargs):
        raise ValueError(code)

    monkeypatch.setattr(pilot.LocalConfiguration, "environment", fail)
    monkeypatch.setattr(sys, "argv", ["pilot", "backup"])
    with pytest.raises(SystemExit) as exc:
        pilot.main()
    assert exc.value.code == 1
    assert capsys.readouterr().err.strip() == "FAIL backup: " + code
