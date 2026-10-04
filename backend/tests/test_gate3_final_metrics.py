import json
from pathlib import Path

import httpx
import pytest
from test_gate3_benchmark import exchange
from test_provider import adapter, envelope, proposed

from benchmarks.evaluator import BlindEvaluator
from benchmarks.metrics import compare
from benchmarks.variants import content_hash
from domain.application import AssessmentTask
from domain.benchmark import BenchmarkExpectation, BenchmarkPackage, Feature, Judgment
from domain.models import Verification
from model_adapters.config import ProviderConfig
from model_adapters.openai import OpenAIAdapter
from policy_engine.manifest import Manifest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def manifest():
    return Manifest.model_validate_json((ROOT / "policies/rubric-v5.manifest.json").read_text())


def execute(
    tmp_path, monkeypatch, manifest, mode, disposition="unresolved", kind="model_inference"
):
    def change(name, output):
        if name == "rdw_evaluation":
            output["statements"][0]["kind"] = kind
        if name == "rdw_checking":
            for d in output["decisions"]:
                if d["target"] == "statement:principal-obstacle":
                    d["disposition"] = disposition
        return output

    if mode == "WORKBENCH":
        model, _, requests = adapter(monkeypatch, change)
    else:
        monkeypatch.setenv("OPENAI_API_KEY", "synthetic-placeholder")
        requests = []

        def handler(request):
            body = json.loads(request.content)
            requests.append(body)
            assert body["text"]["format"]["name"] == "rdw_baseline"
            payload = json.loads(body["input"])
            task = AssessmentTask.model_validate(
                {k: v for k, v in payload.items() if k != "criteria"}
            )
            result = proposed(task)
            result["statements"][0]["kind"] = kind
            if kind == "unresolved":
                result["statements"][0]["text"] = (
                    "Cannot determine the bounded synthetic claim from inspected material."
                )
                result["summary"]["obstacle"] = result["statements"][0]["text"]
            return httpx.Response(200, json=envelope(result))

        model = OpenAIAdapter(
            ProviderConfig(provider="openai"), httpx.Client(transport=httpx.MockTransport(handler))
        )
    evaluator = BlindEvaluator(
        exchange().variants[0].packet, model, manifest, tmp_path / (mode + disposition + kind)
    )
    try:
        output, components = evaluator.run(mode, "FULL")
        observation = evaluator.observe(output)
        statement = next(
            j for j in observation.judgments if j.key == "statement:principal-obstacle"
        )
        assert statement.content == output["statements"][0]["text"]
        assert statement.adoption == "proposed" and statement.evidence_state == "not_inspected"
        assert statement.evaluator_mode == mode == observation.evaluator_mode
        assert set(statement.source_refs) <= set(observation.authorized_anchors)
        if mode == "BASELINE":
            assert components == ("baseline",) and len(requests) == 1
            assert not statement.checking_performed and statement.verification is None
        else:
            assert statement.checking_performed and statement.verification == Verification(
                disposition
            )
        return observation
    finally:
        evaluator.close()
        model.close()


def expectation(**constraints):
    return BenchmarkExpectation(
        feature=Feature.QUESTION,
        behavior="withhold",
        judgment="statement:principal-obstacle",
        **constraints,
    )


def metric(observation, e):
    return compare(observation, (e,), {}, exchange().projects[0]).metrics[0]


@pytest.mark.parametrize(
    "constraints",
    (
        {},
        {"acceptable_states": ("unresolved",)},
        {"acceptable_scientific_states": ("unresolved",)},
        {"acceptable_verification_states": ("unresolved",)},
        {
            "acceptable_scientific_states": ("unresolved",),
            "acceptable_verification_states": ("unresolved",),
        },
        {"forbidden_scientific_states": ("supported",)},
        {"acceptable_adoption_states": ("proposed",)},
    ),
)
def test_workbench_unresolved_correct_axes_end_to_end(tmp_path, monkeypatch, manifest, constraints):
    observed = execute(tmp_path, monkeypatch, manifest, "WORKBENCH", kind="unresolved")
    m = metric(observed, expectation(**constraints))
    assert m.withholding.numerator == 1
    if (
        "acceptable_states" in constraints
        or "acceptable_scientific_states" in constraints
        or "forbidden_scientific_states" in constraints
    ):
        assert (m.state.numerator, m.state.denominator) == (1, 1)
    if "acceptable_verification_states" in constraints:
        assert (m.verification_state.numerator, m.verification_state.denominator) == (1, 1)
    if "acceptable_adoption_states" in constraints:
        assert (m.adoption_state.numerator, m.adoption_state.denominator) == (1, 1)


@pytest.mark.parametrize(
    "constraints",
    (
        {},
        {"acceptable_states": ("unresolved",)},
        {"acceptable_scientific_states": ("unresolved",)},
        {"acceptable_verification_states": ("supported",)},
        {"verification_change": "changed"},
    ),
)
def test_baseline_explicit_abstention_no_fabricated_verification(
    tmp_path, monkeypatch, manifest, constraints
):
    observed = execute(tmp_path, monkeypatch, manifest, "BASELINE", kind="unresolved")
    m = metric(observed, expectation(**constraints))
    assert m.withholding.numerator == 1
    assert (
        m.verification_state.denominator
        == m.verification_change.denominator
        == m.verification_expectation.denominator
        == 0
    )


@pytest.mark.parametrize(
    "mode,disposition,kind",
    (
        ("WORKBENCH", "supported", "model_inference"),
        ("WORKBENCH", "needs_revision", "model_inference"),
        ("BASELINE", "unresolved", "model_inference"),
        ("BASELINE", "unresolved", "proposed_improvement"),
    ),
)
def test_confident_or_needs_revision_is_not_abstention(
    tmp_path, monkeypatch, manifest, mode, disposition, kind
):
    observed = execute(tmp_path, monkeypatch, manifest, mode, disposition, kind)
    j = next(j for j in observed.judgments if j.key == "statement:principal-obstacle")
    assert j.value is None
    assert metric(observed, expectation()).withholding.numerator == 0
    if disposition == "needs_revision":
        assert j.verification == Verification.NEEDS_REVISION


def test_fair_withholding_and_separate_verification_only_change(tmp_path, monkeypatch, manifest):
    uncertain = execute(tmp_path, monkeypatch, manifest, "WORKBENCH", kind="unresolved")
    baseline = execute(tmp_path, monkeypatch, manifest, "BASELINE", kind="unresolved")
    e = expectation(acceptable_scientific_states=("unresolved",))
    assert metric(uncertain, e).withholding == metric(baseline, e).withholding
    checked = execute(tmp_path, monkeypatch, manifest, "WORKBENCH", "supported", kind="unresolved")
    change = e.model_copy(
        update={"behavior": "detect", "reference_variant": "old", "verification_change": "changed"}
    )
    m = compare(checked, (change,), {"old": uncertain}, exchange().projects[0]).metrics[0]
    assert (
        m.detection.numerator == 0
        and m.verification_change.numerator == m.verification_expectation.numerator == 1
    )
    assert checked.judgments[-1].scientific_state == "unresolved"


def test_forbidden_scientific_and_verification_axes_do_not_follow_adoption(
    tmp_path, monkeypatch, manifest
):
    observed = execute(tmp_path, monkeypatch, manifest, "WORKBENCH", kind="unresolved")
    assert (
        metric(observed, expectation(forbidden_scientific_states=("unresolved",))).state.numerator
        == 0
    )
    m = metric(
        observed,
        expectation(
            acceptable_scientific_states=("unresolved",),
            forbidden_verification_states=("unresolved",),
        ),
    )
    assert (
        m.state.numerator == 1
        and m.verification_state.numerator == 0
        and m.withholding.numerator == 1
    )
    assert (
        metric(
            observed, expectation(forbidden_adoption_states=("proposed",))
        ).adoption_state.numerator
        == 0
    )


def test_axis_types_and_legacy_frozen_package_hashes():
    package = exchange()
    # Captured using the unmodified eaace9f implementation, before the additive fields.
    assert (
        content_hash(package) == "9d72cf9d5f52c81c50f40bfe0261b8320dfb0960df95df8a4a753b07abda8d6d"
    )
    data = package.model_dump(mode="json")
    assert BenchmarkPackage.model_validate(data) == package
    extension = {
        "acceptable_scientific_states",
        "forbidden_scientific_states",
        "acceptable_verification_states",
        "forbidden_verification_states",
        "acceptable_adoption_states",
        "forbidden_adoption_states",
        "verification_change",
    }
    for artifact in data["expectations"]:
        for e in artifact["expectations"]:
            assert not extension.intersection(e)
    assert content_hash(BenchmarkPackage.model_validate(data)) == content_hash(data)
    e = expectation(
        acceptable_scientific_states=("unresolved",), acceptable_verification_states=("unresolved",)
    )
    serialized = e.model_dump(mode="json")
    assert serialized["acceptable_scientific_states"] == ["unresolved"]
    assert serialized["acceptable_verification_states"] == ["unresolved"]
    assert BenchmarkExpectation.model_validate(serialized) == e
    with pytest.raises(ValueError):
        expectation(acceptable_scientific_states=("proposed",))
    with pytest.raises(ValueError):
        expectation(acceptable_verification_states=("accepted",))


@pytest.mark.parametrize(
    "axes",
    (
        {"scientific_state": "supported"},
        {"evaluator_mode": "BASELINE", "verification": "unresolved"},
        {"evaluator_mode": "BASELINE", "verification": None, "checking_performed": True},
    ),
)
def test_incoherent_or_fabricated_axes_rejected(axes):
    with pytest.raises(ValueError):
        Judgment(key="statement:principal-obstacle", state="unresolved", **axes)


def test_historical_checked_proposal_keeps_legacy_state_semantics():
    from benchmarks.metrics import is_withholding
    from domain.benchmark import Observation

    old = Judgment(
        key="statement:principal-obstacle",
        state="proposed",
        checking_performed=True,
        verification="unresolved",
    )
    observed = Observation(judgments=(old,))
    assert is_withholding(old)
    assert metric(observed, expectation()).withholding.numerator == 1
    assert metric(observed, expectation(acceptable_states=("proposed",))).state.numerator == 1
    assert metric(observed, expectation(acceptable_states=("unresolved",))).state.numerator == 0
    assert not is_withholding(old.model_copy(update={"checking_performed": False}))
