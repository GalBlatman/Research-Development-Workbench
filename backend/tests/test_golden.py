from fractions import Fraction

import pytest
from conftest import CASES, make_assessment

from policy_engine.engine import evaluate
from policy_engine.manifest import Manifest
from policy_engine.scenarios import Branch, expected_strength


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_golden(case: dict, manifest: Manifest) -> None:
    scenario = case.get("scenario")
    if scenario:
        current = evaluate(make_assessment(manifest), manifest)
        plus = evaluate(make_assessment(manifest, [7] * 10), manifest)
        # Explicit unfavorable branch: weighted total 405 -> I=54.
        minus = evaluate(make_assessment(manifest, [6, 6, 8, 6, 3, 3, 3, 5, 5, 5]), manifest)
        good = (
            Branch("repair", Fraction(4, 5), plus, "Explicit revised argument"),
            Branch("weakness", Fraction(1, 5), minus, "Explicit unfavorable same-route version"),
        )
        if scenario == "expected":
            result = expected_strength(
                current, "IDEA", good, "One-week common budget", "Manual planning basis"
            )
            assert result.expected_strength == Fraction(case["expected_strength"])
            assert result.expected_change == Fraction("16.8")
            assert current.idea.value == 50
        elif scenario == "stop":
            stop = (
                good[0],
                Branch("STOP", Fraction(1, 5), None, "No viable same-base alternative"),
            )
            assert expected_strength(current, "IDEA", stop, "B", "basis").expected_strength is None
        else:
            wrong_route = evaluate(make_assessment(manifest, route="ESTABLISH"), manifest)
            wrong_stage = evaluate(
                make_assessment(manifest, stage="SPECIFIED STUDY PROPOSAL"), manifest
            )
            for invalid in (wrong_route, wrong_stage):
                with pytest.raises(ValueError):
                    expected_strength(
                        current,
                        "IDEA",
                        (Branch("different", Fraction(1), invalid, "version"),),
                        "B",
                        "basis",
                    )
            with pytest.raises(ValueError):
                expected_strength(current, "INVALID", good, "B", "basis")
            with pytest.raises(ValueError):
                expected_strength(current, "IDEA", good[:1], "B", "basis")
        return
    arguments = {
        k: case[k]
        for k in ("route", "stage", "findings", "study", "articulated", "benchmarks")
        if k in case
    }
    assessment = make_assessment(manifest, case.get("ratings"), **arguments)
    result = evaluate(assessment, manifest)
    for name, expected in case["expected"].items():
        assert getattr(result, name).value == (None if expected is None else Fraction(expected))
    for name in ("project_uncapped", "project_before_caps"):
        if name in case:
            assert getattr(result, name).value == Fraction(case[name])
    if "display" in case:
        assert result.idea.displayed == case["display"]
    if "gate" in case:
        assert next(g for g in result.gates if g.name == case["gate"]).state == "TRUE"
    if "gate_false" in case:
        assert next(g for g in result.gates if g.name == case["gate_false"]).state == "FALSE"
    if "d1" in case:
        assert dict(result.effective_ratings)[1] == case["d1"]
    if "label" in case:
        assert result.label == case["label"]
    if "idea_status" in case:
        assert result.idea.status == case["idea_status"]
