import hashlib
import itertools

import pytest
from conftest import CASES, ROOT
from test_golden import test_golden as check_golden

from domain.models import RouteItem, Truth, Verification
from policy_engine.engine import route_readiness
from policy_engine.manifest import Manifest


@pytest.fixture
def v5():
    return Manifest.model_validate_json(
        (ROOT / "policies/rubric-v5.manifest.json").read_text(encoding="utf-8")
    )


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_v5_golden(case, v5):
    check_golden(case, v5)


def test_v4_bytes_and_v5_surgical_changes():
    original = ROOT / "policies/rubric-v4.md"
    assert (
        hashlib.sha256(original.read_bytes()).hexdigest()
        == "a94c195f1f95547cad00d9f2bdcd384cca58ae85bf40646d4b36146379b8f26d"
    )
    v4 = original.read_text(encoding="utf-8")
    v5 = (ROOT / "policies/rubric-v5.md").read_text(encoding="utf-8")
    import re

    assert v5.count("**V5 clarification") == 2
    cleaned = re.sub(
        r"\n\*\*V5 clarification of V4 ambiguity G3-R1 — route item status semantics:\*\*.*?implicit count\.\n",
        "",
        v5,
        flags=re.S,
    )
    cleaned = re.sub(
        r"\n\*\*V5 clarification of V4 ambiguity G3-R1 — ESTABLISH/TEST route-assessment component of submission readiness:\*\*.*?and no hard stop\.\n",
        "",
        cleaned,
        flags=re.S,
    )
    cleaned = (
        cleaned.replace("Version 5:", "Version 4:", 1)
        .replace("October 3, 2026", "October 2, 2026", 1)
        .replace("Research_Idea_Rubric_v4.md", "Research_Idea_Rubric_v3.md", 1)
    )
    assert cleaned == v4


@pytest.mark.parametrize("size", (3, 4, 5, 6))
def test_exhaustive_readiness_matrix(size):
    names = (
        "knowledge_need",
        "increment",
        "scope_precision",
        "capacity_to_learn",
        "evidence_strategy",
        "next_use",
    )[:size]
    statuses = ("ADEQUATE FOR STAGE", "DEVELOPMENT NEEDED", "BLOCKING", "NOT INSPECTED")
    for values in itertools.product(statuses, repeat=size):
        items = tuple(
            RouteItem(item=name, status=value, reason="Explicit synthetic stage judgment")
            for name, value in zip(names, values, strict=True)
        )
        expected = (
            Truth.UNKNOWN
            if "NOT INSPECTED" in values
            else Truth.FALSE
            if "BLOCKING" in values
            else Truth.TRUE
        )
        assert route_readiness(items, names) == expected
        assert route_readiness(items[:-1], names) == Truth.UNKNOWN
        unchecked = items[0].model_copy(update={"verification": Verification.UNRESOLVED})
        assert route_readiness((unchecked,) + items[1:], names) == Truth.UNKNOWN


@pytest.mark.parametrize("route", ("ESTABLISH", "TEST"))
@pytest.mark.parametrize(
    "status,expected",
    (
        ("ADEQUATE FOR STAGE", "TRUE"),
        ("DEVELOPMENT NEEDED", "TRUE"),
        ("BLOCKING", "FALSE"),
        ("NOT INSPECTED", "UNKNOWN"),
    ),
)
def test_v5_submission_gate_uses_status_component_and_preserves_other_prerequisites(
    v5, route, status, expected
):
    from conftest import make_assessment

    from policy_engine.engine import evaluate

    items = tuple(
        RouteItem(item=name, status=status, reason="Explicit stage judgment")
        for name in v5.route_items
    )
    assessment = make_assessment(v5, route=route).model_copy(update={"route_assessment": items})
    assert (
        next(g for g in evaluate(assessment, v5).gates if g.name == "submission").state == expected
    )
    unchecked = assessment.model_copy(
        update={
            "route_assessment": tuple(
                item.model_copy(update={"verification": Verification.UNRESOLVED}) for item in items
            )
        }
    )
    assert (
        next(g for g in evaluate(unchecked, v5).gates if g.name == "submission").state == "UNKNOWN"
    )
    inadequate = make_assessment(v5, values=[5] * 7 + [4, 5, 5], route=route).model_copy(
        update={"route_assessment": items}
    )
    assert (
        next(g for g in evaluate(inadequate, v5).gates if g.name == "submission").state == "FALSE"
    )
