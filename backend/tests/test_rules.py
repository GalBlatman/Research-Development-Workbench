from fractions import Fraction

import pytest
from conftest import make_assessment
from pydantic import ValidationError

from domain.models import Assessment, Finding, RouteItem, Status, Truth, Verification
from policy_engine.engine import Score, evaluate
from policy_engine.manifest import Manifest
from policy_engine.scenarios import Branch, break_even, expected_strength


def gate(result, name):
    return next(g for g in result.gates if g.name == name)


@pytest.mark.parametrize("rule,score", [("NO-ADVANCE", 39), ("NO-CONSEQUENTIAL-STAKE", 69)])
def test_idea_caps_and_trace(rule, score, manifest):
    result = evaluate(make_assessment(manifest, [8] * 10, findings={rule: "TRUE"}), manifest)
    assert result.idea.value == score
    assert gate(result, "strong_idea").state == Truth.FALSE
    assert any(t.rule_id == rule and t.value == Truth.TRUE and t.source for t in result.trace)


@pytest.mark.parametrize("verification", [Verification.UNRESOLVED, Verification.NEEDS_REVISION])
def test_unverified_allegation_cannot_apply_cap(verification, manifest):
    data = make_assessment(manifest, [8] * 10).model_dump()
    data["findings"] = [
        dict(f, verification=verification) if f["rule_id"] == "NO-ADVANCE" else f
        for f in data["findings"]
    ]
    result = evaluate(Assessment.model_validate(data), manifest)
    assert result.idea.value == 80
    assert gate(result, "strong_idea").state == Truth.UNKNOWN
    assert any(t.rule_id == "NO-ADVANCE" and t.value == Truth.UNKNOWN for t in result.trace)


def test_unknown_never_awards_commitment(manifest):
    result = evaluate(
        make_assessment(manifest, [8] * 10, findings={"STAGE-PREREQUISITES": "UNKNOWN"}), manifest
    )
    assert result.project.value == 80
    assert gate(result, "exceptional_project").state == Truth.UNKNOWN
    assert gate(result, "exceptional_project").provisional


def test_audience_withholds_and_contradiction_blocks(manifest):
    result = evaluate(make_assessment(manifest, findings={"AUDIENCE-QUESTION": "TRUE"}), manifest)
    assert result.idea.value is None and result.project.value is None
    result = evaluate(
        make_assessment(manifest, [8] * 10, findings={"PREMISE-CONTRADICTED": "TRUE"}), manifest
    )
    assert result.label == "BLOCKED AS STATED"
    assert gate(result, "submission").state == Truth.FALSE


def test_overreach_requires_existing_rule_not_new_penalty(manifest):
    with pytest.raises(ValueError, match="corresponding"):
        evaluate(make_assessment(manifest, findings={"PROMISE-OVERREACH": "TRUE"}), manifest)
    result = evaluate(
        make_assessment(
            manifest, findings={"PROMISE-OVERREACH": "TRUE", "INFERENCE-UNSUPPORTED": "TRUE"}
        ),
        manifest,
    )
    assert result.project.value == 39
    assert result.idea.value == 50


def test_submission_uses_completed_study_and_idea_floors(manifest):
    result = evaluate(make_assessment(manifest), manifest)
    assert gate(result, "submission").state == Truth.TRUE
    assert gate(result, "strong_idea").state == Truth.FALSE
    assert (
        gate(
            evaluate(make_assessment(manifest, stage="SPECIFIED STUDY PROPOSAL"), manifest),
            "submission",
        ).state
        == Truth.FALSE
    )
    assert (
        gate(
            evaluate(make_assessment(manifest, [5, 5, 4, 5, 5, 5, 5, 5, 5, 5]), manifest),
            "submission",
        ).state
        == Truth.FALSE
    )
    assert (
        gate(
            evaluate(make_assessment(manifest, findings={"SUPPORT-VERIFIED": "UNKNOWN"}), manifest),
            "submission",
        ).state
        == Truth.UNKNOWN
    )


@pytest.mark.parametrize("route", ["ESTABLISH", "TEST"])
def test_nonexplain_submission_has_no_mechanism_floor(route, manifest):
    data = make_assessment(manifest, [None] * 7 + [5] * 3, route=route).model_dump()
    data["route_assessment"] = [
        RouteItem(
            item=item, status="ADEQUATE FOR STAGE", reason="synthetic delivered route evidence"
        )
        for item in manifest.route_items
    ]
    result = evaluate(Assessment.model_validate(data), manifest)
    assert gate(result, "submission").state == Truth.TRUE
    assert result.idea.status == Status.NOT_APPLICABLE


def test_boundary_range_is_provisional_without_replacing_rating(manifest):
    data = make_assessment(manifest, [7] * 10).model_dump()
    data["ratings"][2]["plausible_range"] = (6, 7)
    result = evaluate(Assessment.model_validate(data), manifest)
    assert result.idea.value == 70
    assert gate(result, "strong_idea").state == Truth.TRUE
    assert gate(result, "strong_idea").provisional
    assert "PROVISIONAL" in result.label


def test_proposal_prerequisites_distinct_from_submission(manifest):
    result = evaluate(
        make_assessment(
            manifest, stage="SPECIFIED STUDY PROPOSAL", findings={"PILOT-PREREQUISITES": "FALSE"}
        ),
        manifest,
    )
    assert gate(result, "proposal_readiness").state == Truth.FALSE
    result = evaluate(make_assessment(manifest, findings={"PREMISE-CONDITIONAL": "TRUE"}), manifest)
    assert gate(result, "submission").state == Truth.FALSE


def test_half_up_and_break_even():
    assert Score(Fraction(139, 2), Status.ASSESSED, "synthetic").displayed == 70
    assert break_even(Fraction(70), Fraction(54), Fraction("66.8")) == Fraction(4, 5)
    assert break_even(Fraction(54), Fraction(54), Fraction(70)) is None


def test_missing_budget_withholds_expectation(manifest):
    result = evaluate(make_assessment(manifest), manifest)
    assert (
        expected_strength(
            result, "IDEA", (Branch("same", Fraction(1), result, "no change"),), "", "basis"
        ).expected_strength
        is None
    )


def test_duplicates_unknown_rules_and_policy_version_rejected(manifest):
    original = make_assessment(manifest)
    data = original.model_dump()
    data["ratings"] = [data["ratings"][0], data["ratings"][0]]
    with pytest.raises(ValidationError):
        Assessment.model_validate(data)
    data = original.model_dump()
    data["findings"] = list(data["findings"])
    data["findings"].append(
        Finding(
            rule_id="invented",
            value=Truth.TRUE,
            reasoning="not policy",
            scope=original.snapshot.snapshot_id,
            verification=Verification.SUPPORTED,
        )
    )
    with pytest.raises(ValueError, match="Unknown"):
        evaluate(Assessment.model_validate(data), manifest)
    data = original.model_dump()
    data["snapshot"]["policy_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="hash"):
        evaluate(Assessment.model_validate(data), manifest)


def test_manifest_weights_cannot_silently_change(manifest):
    data = manifest.model_dump()
    data["dimensions"][0]["weight"] = 100
    with pytest.raises(ValidationError):
        Manifest.model_validate(data)


def test_finding_scope_and_strict_boolean_inputs(manifest):
    data = make_assessment(manifest).model_dump()
    data["findings"][0]["scope"] = "another-snapshot"
    with pytest.raises(ValidationError):
        Assessment.model_validate(data)
    data = make_assessment(manifest).model_dump()
    data["account_articulated"] = "yes"
    with pytest.raises(ValidationError):
        Assessment.model_validate(data)


def test_premise_effective_rating_does_not_rewrite_original(manifest):
    original = make_assessment(manifest, [8] * 10, findings={"PREMISE-NO-BASIS": "TRUE"})
    result = evaluate(original, manifest)
    assert original.ratings[0].rating == 8
    assert dict(result.effective_ratings)[1] == 3


def test_unverified_numeric_rating_withholds_only_affected_block(manifest):
    data = make_assessment(manifest).model_dump()
    data["ratings"][0]["verification"] = Verification.UNRESOLVED
    result = evaluate(Assessment.model_validate(data), manifest)
    assert result.idea.value is None
    assert result.project.value is None
    assert result.study.value == 50


def test_snapshot_pins_executable_manifest_not_only_rubric(manifest):
    original = make_assessment(manifest)
    data = manifest.model_dump()
    data["profiles"][0]["minimum_total"] = 1
    changed = Manifest.model_validate(data)
    with pytest.raises(ValueError, match="manifest hash"):
        evaluate(original, changed)


def test_submission_cannot_pass_uninspected_study_dimension(manifest):
    result = evaluate(make_assessment(manifest, [5] * 9 + [None]), manifest)
    assert gate(result, "submission").state == Truth.UNKNOWN
    assert result.study.value is None


def test_nonexplain_study_range_marks_readiness_borderline(manifest):
    data = make_assessment(manifest, [None] * 7 + [5] * 3, route="TEST").model_dump()
    data["route_assessment"] = [
        RouteItem(item=item, status="ADEQUATE FOR STAGE", reason="synthetic delivered evidence")
        for item in manifest.route_items
    ]
    data["ratings"][7]["plausible_range"] = (4, 5)
    result = evaluate(Assessment.model_validate(data), manifest)
    assert gate(result, "submission").state == Truth.TRUE
    assert gate(result, "submission").provisional
    assert any("d8:range" in missed for missed in gate(result, "submission").missed)
