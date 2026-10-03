from fractions import Fraction

import pytest
from conftest import make_assessment

from domain.models import Commitment, GateState, Stage, Truth
from policy_engine.engine import evaluate


def gate(result, name):
    return next(g for g in result.gates if g.name == name)


@pytest.mark.parametrize(
    "rule,commitment",
    [
        ("PREMISE-NO-BASIS", Commitment.PREMISE_VERIFY_OR_REFORMULATE),
        ("PREMISE-CONDITIONAL", Commitment.BOUNDED_PREMISE_CHECK),
    ],
)
def test_premise_prevents_unrestricted_proposal(rule, commitment, manifest):
    result = evaluate(
        make_assessment(manifest, [8] * 10, stage=Stage.PROPOSAL, findings={rule: "TRUE"}), manifest
    )
    readiness = gate(result, "proposal_readiness")
    assert readiness.state == GateState.FALSE
    assert readiness.commitment == commitment
    assert gate(result, "strong_idea").state != GateState.TRUE
    if rule == "PREMISE-CONDITIONAL":
        assert result.label == "PREMISE-CONDITIONAL"
        assert result.idea.status == "conditional"
        assert result.project.status == "conditional"
    else:
        clamp = next(t for t in result.trace if t.dimension == 1)
        assert (clamp.rule_id, clamp.before, clamp.after) == ("PREMISE-NO-BASIS", 8, 3)
        assert clamp.source == "v4 §§8.2"


@pytest.mark.parametrize("route", ["ESTABLISH", "TEST"])
def test_inapplicable_theory_gates_and_inspection(route, manifest):
    result = evaluate(make_assessment(manifest, [None] * 7 + [5] * 3, route=route), manifest)
    assert result.idea.status == "not_applicable"
    for name in ("strong_idea", "exceptional_idea", "strong_project", "exceptional_project"):
        assert gate(result, name).state == GateState.NOT_APPLICABLE
        assert next(t for t in result.trace if t.rule_id == name).value == GateState.NOT_APPLICABLE
    assert next(t for t in result.trace if t.rule_id == "UNINSPECTED-BLOCK").value == Truth.FALSE
    assert next(t for t in result.trace if t.rule_id == "HIGH-SCORE-BENCHMARK").value == Truth.FALSE


@pytest.mark.parametrize("stage", [Stage.EARLY_IDEA, Stage.DISCOVERY])
def test_pre_explanation_is_pending(stage, manifest):
    result = evaluate(
        make_assessment(manifest, [None] * 10, stage=stage, articulated=False, study=False),
        manifest,
    )
    assert result.idea.status == "pending"
    assert next(t for t in result.trace if t.rule_id == "DISCOVERY-PENDING").value == Truth.TRUE
    for name in ("strong_idea", "exceptional_idea", "strong_project", "exceptional_project"):
        assert gate(result, name).state == GateState.PENDING


@pytest.mark.parametrize("stage", [Stage.PROPOSAL, Stage.COMPLETED])
@pytest.mark.parametrize("mechanism", [None, 0])
def test_later_missing_account_is_not_discovery_exemption(stage, mechanism, manifest):
    result = evaluate(
        make_assessment(
            manifest, [5, 5, 5, mechanism, 5, 5, 5, 5, 5, 5], stage=stage, articulated=False
        ),
        manifest,
    )
    assert next(t for t in result.trace if t.rule_id == "DISCOVERY-PENDING").value == Truth.FALSE
    assert result.idea.value == (None if mechanism is None else Fraction(40))
    assert dict(result.effective_ratings)[4] == mechanism
    assert next(t for t in result.trace if t.rule_id == "UNINSPECTED-BLOCK").value == (
        Truth.TRUE if mechanism is None else Truth.FALSE
    )


@pytest.mark.parametrize(
    "stage,suffix", [(Stage.PROPOSAL, "PROPOSED"), (Stage.COMPLETED, "COMPLETED")]
)
def test_project_endorsement_carries_stage(stage, suffix, manifest):
    result = evaluate(make_assessment(manifest, [8] * 10, stage=stage), manifest)
    assert result.label == "EXCEPTIONAL_PROJECT " + suffix
    assert result.endorsement_stage == suffix


def test_no_high_rating_nontriggered_and_ordinary_readiness(manifest):
    result = evaluate(make_assessment(manifest, [5] * 10, stage=Stage.PROPOSAL), manifest)
    assert next(t for t in result.trace if t.rule_id == "HIGH-SCORE-BENCHMARK").value == Truth.FALSE
    assert gate(result, "proposal_readiness").state == GateState.TRUE
    assert gate(result, "proposal_readiness").commitment == Commitment.ORDINARY
