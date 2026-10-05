import json

import pytest
from pydantic import ValidationError
from test_gate3_final_metrics import manifest as manifest

from benchmarks.calibration_adapter import CalibrationAdapter, CompactDecision
from benchmarks.evaluator import BlindEvaluator
from benchmarks.fixtures import synthetic
from domain.models import AttributedStatement, SourceReference
from domain.sources import SourceRole
from model_adapters.checking import AssessmentChecker
from model_adapters.config import ProviderConfig
from model_adapters.fake import FakeModel
from model_adapters.runtime import ProviderFailure


@pytest.mark.parametrize("role", list(SourceRole))
@pytest.mark.parametrize("kind", ("source_backed", "user_project"))
def test_attribution_uses_source_role_family_without_mixing_author_assertions(
    tmp_path, manifest, role, kind
):
    evaluator = BlindEvaluator(
        synthetic()[1][0].variant.packet, FakeModel(), manifest, tmp_path / "blind"
    )
    model = CalibrationAdapter(ProviderConfig())
    try:
        context = evaluator.task("Brief", extended=True).context
        passage = context.passages[0]
        passage = passage.model_copy(
            update={"source": passage.source.model_copy(update={"role": role})}
        )
        context = context.model_copy(update={"passages": (passage,)})
        statement = AttributedStatement(
            statement_id="synthetic-claim",
            kind=kind,
            text="Synthetic source assertion, not independent empirical verification.",
            source_refs=(
                SourceReference(
                    document_id=passage.source.document_id,
                    version=passage.anchor.version,
                    anchor_id=passage.anchor.anchor_id,
                ),
            ),
        )
        author = role in {SourceRole.DRAFT, SourceRole.AUTHOR_NOTE}
        if (kind == "user_project") == author:
            AssessmentChecker(model).statements(context, (statement,))
        else:
            with pytest.raises(ProviderFailure, match="ATTRIBUTION_ROLE_MISMATCH"):
                AssessmentChecker(model).statements(context, (statement,))
    finally:
        evaluator.close()
        model.close()


@pytest.mark.parametrize("mode", ["WORKBENCH", "BASELINE"])
def test_failed_candidate_is_preserved_as_unchecked_diagnostic(
    tmp_path, manifest, monkeypatch, mode
):
    from test_benchmarks import runner
    from test_provider import transport

    from benchmarks.calibration import configuration

    def change(kind, output):
        if kind in ("rdw_evaluation", "rdw_baseline"):
            output["statements"][0]["kind"] = "source_backed"
        return output

    client, requests = transport(monkeypatch, change)
    pc = ProviderConfig(provider="openai")
    r, _, cases = runner(tmp_path, manifest, lambda: CalibrationAdapter(pc, client))
    run = r.execute(cases[0], configuration(pc, "Brief", mode, "synthetic-commit"))
    assert run.status == "FAILED" and run.failure_type == "ATTRIBUTION_ROLE_MISMATCH"
    assert run.observation is None and run.result is None
    assert json.loads(run.output_json)["statements"][0]["kind"] == "source_backed"
    assert run.receipt.status == "FAILED"
    assert len(requests) == 1


@pytest.mark.parametrize("bad_index", [-1, True, "0"])
def test_compact_reference_cannot_coerce_non_integer_or_negative(bad_index):
    with pytest.raises(ValidationError):
        CompactDecision(
            target="statement:synthetic",
            disposition="supported",
            reason="Synthetic reason",
            source_refs=(bad_index,),
        )


@pytest.mark.parametrize("bad_index", [None, 999])
def test_compact_checker_transport_preserves_one_pass_and_reference_boundary(
    tmp_path, manifest, monkeypatch, bad_index
):
    from test_provider import transport

    def change(kind, output):
        if kind == "rdw_checking-compact":
            for decision in output["decisions"]:
                decision["source_refs"] = [0 if bad_index is None else bad_index]
        return output

    client, requests = transport(monkeypatch, change)
    model = CalibrationAdapter(ProviderConfig(provider="openai"), client)
    evaluator = BlindEvaluator(
        synthetic()[1][0].variant.packet, model, manifest, tmp_path / "blind"
    )
    try:
        if bad_index is not None:
            with pytest.raises(ProviderFailure, match="MISSING_SOURCE_SUPPORT"):
                evaluator.run("WORKBENCH", "Brief", extended=True)
        else:
            output, _ = evaluator.run("WORKBENCH", "Brief", extended=True)
            context = evaluator.task("Brief", extended=True).context
            reference = context.passages[0]
            assert all(
                d["source_refs"]
                == [
                    {
                        "document_id": reference.source.document_id,
                        "version": reference.anchor.version,
                        "anchor_id": reference.anchor.anchor_id,
                    }
                ]
                for d in output["checks"]
            )
        assert len(requests) == 2
        assert requests[1]["text"]["format"]["name"] == "rdw_checking-compact"
        assert "zero-based integer indexes" in requests[1]["instructions"]
        assert all(body["store"] is False and body["background"] is False for body in requests)
        assert all(not {"tools", "files", "vector_store_ids"}.intersection(b) for b in requests)
        payload = json.loads(requests[1]["input"])
        assert "private_paper_id" not in json.dumps(payload)
        assert "execution_scope" not in json.dumps(payload)
        assert model.proposed_review is not None
    finally:
        evaluator.close()
        model.close()
