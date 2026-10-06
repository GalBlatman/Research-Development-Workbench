import json
import socket
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient
from test_application import add, create, service

from api.app import create_app
from domain.application import (
    AssessmentTask,
    CandidateReview,
    InterpretationTask,
)
from domain.models import Scope, Verification
from model_adapters.checking import AssessmentChecker
from model_adapters.config import ProviderConfig
from model_adapters.fake import FakeModel
from model_adapters.openai import OpenAIAdapter, policy_contract
from model_adapters.runtime import ProviderFailure, provider_session
from model_adapters.schema import strict_schema
from persistence.repository import AccessDenied


@pytest.fixture
def packet(tmp_path, manifest):
    workbench = service(tmp_path, manifest)
    with TestClient(create_app(workbench)) as client:
        view = add(client, create(client))
    context = workbench.context(view["project"]["project_id"])
    task = AssessmentTask(
        context=context,
        scope="INITIAL_SCREEN",
        policy_version=manifest.version,
        policy_sha256=manifest.canonical_sha256,
        policy_manifest_sha256=manifest.sha256,
        policy_implementation_version=manifest.implementation_version,
    )
    yield workbench, view, task
    workbench.repository.db.close()


def reference(context):
    p = next(p for p in context.passages if p.source.role == "project_draft")
    return {
        "document_id": p.source.document_id,
        "version": p.anchor.version,
        "anchor_id": p.anchor.anchor_id,
    }


def proposed(task):
    candidate = FakeModel().assess(task).model_dump(mode="json")
    anchors = [p.anchor.anchor_id for p in task.context.passages]
    for rating in candidate["assessment"]["ratings"]:
        rating["inspected_material"] = anchors if rating["rating"] is not None else []
    candidate["summary"]["disclaimer"] = "Synthetic mocked provider, no independent verification."
    candidate["statements"] = [
        {
            "statement_id": "principal-obstacle",
            "kind": "model_inference",
            "text": candidate["summary"]["obstacle"],
            "source_refs": [reference(task.context)],
        }
    ]
    return candidate


def envelope(output, status="completed", content_type="output_text"):
    return {
        "id": "synthetic-response",
        "status": status,
        "model": "gpt-6-sol",
        "output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "content": [{"type": content_type, "text": json.dumps(output)}]},
        ],
        "usage": {
            "input_tokens": 400,
            "output_tokens": 150,
            "input_tokens_details": {"cached_tokens": 20},
            "output_tokens_details": {"reasoning_tokens": 30},
        },
    }


def transport(monkeypatch, change=None):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-placeholder")
    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        payload = json.loads(body["input"])
        kind = body["text"]["format"]["name"]
        if kind == "rdw_interpretation":
            task = InterpretationTask.model_validate(
                {k: v for k, v in payload.items() if k != "criteria"}
            )
            output = FakeModel().interpret(task).model_dump(mode="json")
            output["statements"] = [
                {
                    "statement_id": "project-question",
                    "kind": "user_project",
                    "text": output["brief"]["question"],
                    "source_refs": [reference(task.context)],
                }
            ]
        elif kind in ("rdw_evaluation", "rdw_baseline"):
            task = AssessmentTask.model_validate(
                {k: v for k, v in payload.items() if k != "criteria"}
            )
            output = proposed(task)
        else:
            task = AssessmentTask.model_validate(payload["assessment_task"])
            candidate = CandidateReview.model_validate(payload["candidate"])
            targets = payload["targets"]
            output = {
                "summary": candidate.summary.model_dump(mode="json"),
                "decisions": [
                    {
                        "target": t,
                        "disposition": "supported",
                        "reason": "Synthetic anchored support disposition, not empirical verification.",
                        "source_refs": [reference(task.context)],
                    }
                    for t in targets
                ],
            }
        if change:
            output = change(kind, output)
        return httpx.Response(
            200, json=envelope(output), headers={"x-request-id": "synthetic-request"}
        )

    return httpx.Client(transport=httpx.MockTransport(handler)), requests


def adapter(monkeypatch, change=None, config=None):
    client, requests = transport(monkeypatch, change)
    model = OpenAIAdapter(config or ProviderConfig(provider="openai"), client)
    return model, AssessmentChecker(model), requests


def test_strict_request_typed_round_trip_and_privacy(packet, monkeypatch, caplog):
    _, _, task = packet
    model, checker, requests = adapter(monkeypatch)
    with provider_session(model) as ledger:
        interpretation = model.interpret(InterpretationTask(context=task.context))
        checker.interpretation(InterpretationTask(context=task.context), interpretation)
        candidate = model.assess(task)
        checked = checker.review(task, candidate)
        assert checked.assessment.ratings[0].verification == Verification.SUPPORTED
        receipt = ledger.receipt().model_dump(mode="json")
    assert len(requests) == 3
    for body in requests:
        assert body["model"] == "gpt-6-sol"
        assert body["store"] is False and body["background"] is False
        assert not any(
            k in body
            for k in (
                "tools",
                "tool_choice",
                "files",
                "conversation",
                "previous_response_id",
                "include",
            )
        )
        assert body["text"]["format"]["strict"] is True
        assert body["max_output_tokens"] == 6000
        assert "synthetic-placeholder" not in json.dumps(body)
    assert "synthetic-placeholder" not in json.dumps(receipt)
    assert "synthetic-placeholder" not in caplog.text
    assert receipt["calls"][0]["usage_details"]["output_tokens_details.reasoning_tokens"] == 30
    assert receipt["calls"][0]["returned_model"] == "gpt-6-sol"
    assert len(receipt["calls"][0]["prompt_sha256"]) == 64
    assert receipt["calls"][0]["request_id"] == "synthetic-request"


def test_schema_is_closed_required_and_no_provider_snapshot():
    schema = strict_schema(CandidateReview)

    def check(node):
        if isinstance(node, dict):
            assert "default" not in node and "prefixItems" not in node
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for value in node.values():
                check(value)
        if isinstance(node, list):
            for value in node:
                check(value)

    check(schema)
    assert "snapshot" not in schema["properties"]
    assert "SourceRecord" not in schema["$defs"]


def test_targeted_dimension_only_uses_evaluation_and_focused_check(packet, monkeypatch):
    _, _, task = packet
    task = task.model_copy(update={"dimensions": (4,), "scope": Scope.TARGETED_CHECK})
    model, checker, requests = adapter(monkeypatch)
    with provider_session(model):
        checked = checker.review(task, model.assess(task))
    assert [r.dimension for r in checked.assessment.ratings] == [4]
    assert [r["text"]["format"]["name"] for r in requests] == ["rdw_evaluation", "rdw_checking"]
    assert set(json.loads(requests[0]["input"])["criteria"]["dimensions"]) == {"4"}
    assert not json.loads(requests[0]["input"])["criteria"]["semantic_rules"]


def test_checker_withdraws_unsupported_judgment_without_policy_change(packet, monkeypatch):
    workbench, view, task = packet

    def change(kind, output):
        if kind == "rdw_checking":
            next(d for d in output["decisions"] if d["target"] == "rating:1")["disposition"] = (
                "needs_revision"
            )
            output["decisions"][0]["reason"] = (
                "Allegation not supported by supplied original passage."
            )
            output["summary"]["obstacle"] = (
                "Original allegation withdrawn; relevant support remains unresolved."
            )
            output["obstacle_action"] = "withdraw"
            for decision in output["decisions"]:
                if decision["target"] == "statement:principal-obstacle":
                    decision["disposition"] = "needs_revision"
        return output

    model, checker, _ = adapter(monkeypatch, change)
    workbench.adapter, workbench.verifier = model, checker
    result = workbench.run(view["project"]["project_id"], view["project"]["revision"])
    assert result["policy"]["idea"]["value"] is None
    assert result["assessment"]["ratings"][0]["verification"] == "needs_revision"
    assert "withdrawn" in result["summary"]["obstacle"]
    assert result["policy"]["policy_implementation_version"] == "4.2.0"
    assert result["provider_run"]["status"] == "SUCCEEDED"
    assert result["structural_checks"][0]["status"] == "SOURCE_REFS_RESOLVED"
    assert (
        next(d for d in result["checks"] if d["target"] == "rating:1")["disposition"]
        == "needs_revision"
    )
    assert result["snapshot"]["project"] == view["project"]
    assert all(
        s.source_kind != "model" for s in workbench.bundle(view["project"]["project_id"]).sources
    )


@pytest.mark.parametrize("kind", ["source_backed", "user_project"])
def test_missing_or_forged_source_reference_rejected(packet, monkeypatch, kind):
    _, _, task = packet
    model, checker, requests = adapter(monkeypatch)
    candidate = proposed(task)
    candidate["statements"][0]["kind"] = kind
    candidate["statements"][0]["source_refs"][0]["anchor_id"] = "f" * 64
    with pytest.raises(ProviderFailure, match="MISSING_SOURCE_SUPPORT"):
        checker.review(task, CandidateReview.model_validate(candidate))
    assert not requests


def test_unauthorized_source_text_excluded_from_real_request(packet, monkeypatch):
    workbench, view, _ = packet
    with TestClient(create_app(workbench)) as client:
        view = add(client, view, text="EXCLUDED_SYNTHETIC_TEXT", admitted=False)
    model, _, requests = adapter(monkeypatch)
    model.interpret(InterpretationTask(context=workbench.context(view["project"]["project_id"])))
    assert "EXCLUDED_SYNTHETIC_TEXT" not in json.dumps(requests)


def test_foreign_packet_rejected_before_provider(packet, monkeypatch):
    _, _, task = packet
    model, _, requests = adapter(monkeypatch)
    p = task.context.passages[0]
    foreign = p.model_copy(
        update={"source": p.source.model_copy(update={"project_id": "foreign-project"})}
    )
    context = task.context.model_copy(update={"passages": (foreign,)})
    with pytest.raises(ProviderFailure, match="CONTEXT_SCOPE_MISMATCH"):
        model.interpret(InterpretationTask(context=context))
    assert requests == []


@pytest.mark.parametrize(
    "scenario,code",
    [
        ("refusal", "REFUSAL"),
        ("incomplete", "INCOMPLETE_OUTPUT"),
        ("malformed", "MALFORMED_OUTPUT"),
        ("timeout", "TIMEOUT_UNCERTAIN"),
        ("transport", "TRANSPORT_ERROR_UNCERTAIN"),
        ("tool", "UNEXPECTED_TOOL_OUTPUT"),
        ("usage", "USAGE_UNAVAILABLE"),
    ],
)
def test_explicit_failures_no_retry_or_private_error_leak(packet, monkeypatch, scenario, code):
    _, _, task = packet
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-placeholder")
    calls = []

    def handler(request):
        calls.append(request)
        if scenario == "timeout":
            raise httpx.ReadTimeout("synthetic-private-error", request=request)
        if scenario == "transport":
            raise httpx.ConnectError("synthetic-private-error", request=request)
        data = envelope(
            FakeModel().interpret(InterpretationTask(context=task.context)).model_dump(mode="json")
        )
        if scenario == "refusal":
            data["output"][1]["content"] = [
                {"type": "refusal", "refusal": "synthetic-private-error"}
            ]
        if scenario == "incomplete":
            data["status"] = "incomplete"
        if scenario == "malformed":
            data["output"][1]["content"][0]["text"] = "invalid private structured content"
        if scenario == "tool":
            data["output"].append({"type": "web_search_call"})
        if scenario == "usage":
            data.pop("usage")
        return httpx.Response(200, json=data)

    model = OpenAIAdapter(
        ProviderConfig(provider="openai"), httpx.Client(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(ProviderFailure, match=code) as caught:
        model.interpret(InterpretationTask(context=task.context))
    assert len(calls) == 1
    assert caught.value.metadata.status == "FAILED"
    assert "synthetic-private-error" not in caught.value.metadata.model_dump_json()


@pytest.mark.parametrize("status", [429, 500, 400, 404])
def test_retry_bounds_and_attempt_budget(packet, monkeypatch, status):
    _, _, task = packet
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-placeholder")
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status, json={"error": {"message": "synthetic-private-provider-error"}}
        )

    model = OpenAIAdapter(
        ProviderConfig(provider="openai", retries=1),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(ProviderFailure) as caught:
        model.interpret(InterpretationTask(context=task.context))
    assert len(calls) == (1 if status in (400, 404) else 2)
    assert len(caught.value.metadata.calls) == len(calls)
    assert "synthetic-private-provider-error" not in caught.value.metadata.model_dump_json()


@pytest.mark.parametrize("limit", ["calls", "tokens", "context", "input"])
def test_budget_exhaustion_prevents_additional_calls(packet, monkeypatch, limit):
    _, _, task = packet
    config = ProviderConfig(provider="openai")
    config = replace(
        config,
        **{
            "calls": {"max_calls": 1},
            "tokens": {"max_run_tokens": 1},
            "context": {"max_context_bytes": 1},
            "input": {"max_input_tokens": 1},
        }[limit],
    )
    model, checker, requests = adapter(monkeypatch, config=config)
    with pytest.raises(ProviderFailure):
        with provider_session(model):
            checker.review(task, model.assess(task))
    assert len(requests) == (1 if limit == "calls" else 0)


def test_key_missing_blocks_without_network(packet, monkeypatch):
    _, _, task = packet
    model, _, requests = adapter(monkeypatch)
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(ProviderFailure, match="BLOCKED_CREDENTIAL"):
        model.interpret(InterpretationTask(context=task.context))
    assert requests == []


def test_no_provider_source_record_or_self_verification(packet, monkeypatch):
    _, _, task = packet
    model, _, _ = adapter(monkeypatch)
    data = proposed(task)
    data["sources"] = []
    with pytest.raises(ValueError):
        CandidateReview.model_validate(data)
    data.pop("sources")
    data["assessment"]["ratings"][0]["verification"] = "supported"
    with pytest.raises(ValueError, match="cannot self-verify"):
        CandidateReview.model_validate(data)


def test_openai_metadata_and_claims_survive_save_reload_policy_change(packet, monkeypatch):
    workbench, view, task = packet
    model, checker, requests = adapter(monkeypatch)
    workbench.adapter, workbench.verifier = model, checker
    review = workbench.run(view["project"]["project_id"], view["project"]["revision"])
    export = workbench.export(view["project"]["project_id"], "json")
    monkeypatch.setattr(
        "services.workbench.evaluate", lambda *args: pytest.fail("Historical recomputation")
    )
    assert (
        workbench.review(view["project"]["project_id"], review["snapshot"]["snapshot_id"]) == review
    )
    assert workbench.export(view["project"]["project_id"], "json") == export
    assert len(requests) == 2
    assert "synthetic-placeholder" not in export


def test_prompts_and_criteria_preserve_governing_anchors(packet):
    _, _, task = packet
    from model_adapters.openai import PROMPTS

    rubric = (PROMPTS.parents[1] / "policies/rubric-v4.md").read_text(encoding="utf-8")
    criteria = policy_contract(task)["dimensions"]
    assert set(criteria) == {str(d) for d in range(1, 11)}
    for value in criteria.values():
        for line in value.splitlines()[1:]:
            if line:
                assert line in rubric
    for name in ("interpretation", "evaluation", "checking"):
        prompt = (PROMPTS / (name + "-v1.md")).read_text(encoding="utf-8")
        assert "hidden reasoning" in prompt
        assert "tools" in prompt


def test_fake_remains_network_free(packet, monkeypatch):
    _, _, task = packet
    monkeypatch.setattr(socket, "create_connection", lambda *a: pytest.fail("Fake network"))
    assert FakeModel().assess(task) == FakeModel().assess(task)


def test_real_configured_api_run_handle_reload_and_source_separation(
    tmp_path, manifest, monkeypatch
):
    import time

    from domain.models import Adoption, EvidenceState

    model, checker, requests = adapter(monkeypatch)
    monkeypatch.setenv("RDW_PROVIDER", "openai")
    monkeypatch.setenv("RDW_RUNTIME_ROOT", str(tmp_path / "private-runtime"))
    monkeypatch.setenv("RDW_DATABASE_MODE", "local-sqlite")
    # Each worker owns its own connection/client; mocks replace transport only.
    monkeypatch.setattr(
        "api.app.OpenAIAdapter",
        lambda config, receipt_sink=None: OpenAIAdapter(
            config, httpx.Client(transport=model.client._transport), receipt_sink=receipt_sink
        ),
    )
    with TestClient(create_app()) as client:
        assert client.get("/api/health").json()["model"] == "openai:gpt-6-sol"
        view = add(client, create(client))
        obj = view["project"]["objects"][0]
        assert (
            obj["adoption"] == Adoption.PROPOSED
            and obj["evidence_state"] == EvidenceState.UNINSPECTED
        )
        assert obj["statements"][0]["kind"] == "user_project"
        assert obj["provider_run"]["calls"][0]["task"] == "interpretation"
        identifier = view["project"]["project_id"]
        response = client.post(
            f"/api/projects/{identifier}/evaluations",
            json={"expected_revision": view["project"]["revision"]},
        )
        assert response.status_code == 202, response.text
        handle = response.json()
        path = f"/api/projects/{identifier}/runs/{handle['run_id']}"
        for _ in range(100):
            state = client.get(path).json()
            if state["state"] in ("succeeded", "failed"):
                break
            time.sleep(0.01)
        assert state["state"] == "succeeded", state
        review = client.get(f"/api/projects/{identifier}/reviews/{state['snapshot_id']}").json()
        assert review["policy"]["idea"]["displayed"] == 50
        assert len(review["provider_run"]["calls"]) == 2
        assert review["checks"] and review["statements"]
        assert "synthetic-placeholder" not in client.get("/openapi.json").text
        assert (
            "synthetic-placeholder"
            not in client.get(f"/api/projects/{identifier}/exports/json").text
        )
        assert client.get(f"/api/projects/foreign/runs/{handle['run_id']}").status_code == 404
    with TestClient(create_app()) as client:
        assert client.get(path).json()["state"] == "succeeded"
        assert (
            client.get(f"/api/projects/{identifier}/reviews/{state['snapshot_id']}").json()
            == review
        )
    assert len(requests) == 3


def test_failed_provider_job_persists_safe_status_without_snapshot(packet, tmp_path, monkeypatch):
    import time

    from services.runs import RunManager

    workbench, view, task = packet
    identifier = view["project"]["project_id"]
    model, checker, requests = adapter(
        monkeypatch, config=ProviderConfig(provider="openai", max_calls=1)
    )

    def factory():
        result = service(tmp_path, workbench.manifest)
        result.adapter, result.verifier = model, checker
        return result

    manager = RunManager(tmp_path / "run-receipts", factory)
    handle = manager.submit(identifier, view["project"]["revision"])
    for _ in range(100):
        result = manager.get(identifier, handle.run_id)
        if result.state == "failed":
            break
        time.sleep(0.01)
    manager.close()
    assert result.state == "failed" and result.error_code == "BUDGET_EXHAUSTED"
    assert result.provider_run.status == "FAILED"
    assert len(requests) == 1
    assert workbench.bundle(identifier).snapshots == ()
    assert "synthetic-placeholder" not in (
        tmp_path / "run-receipts" / (handle.run_id + ".json")
    ).read_text(encoding="utf-8")


def test_interrupted_receipt_is_not_replayed(tmp_path):
    from domain.application import RunHandle
    from services.runs import RunManager

    root = tmp_path / "receipts"
    root.mkdir()
    run = RunHandle(
        run_id="a" * 32, project_id="synthetic-project", expected_revision=1, state="running"
    )
    (root / (run.run_id + ".json")).write_text(run.model_dump_json(), encoding="utf-8")
    manager = RunManager(root, lambda: pytest.fail("Paid replay"))
    recovered = manager.get(run.project_id, run.run_id)
    assert recovered.state == "failed" and recovered.error_code == "INTERRUPTED_NO_AUTOMATIC_REPLAY"
    with pytest.raises(ValueError):
        manager.get(run.project_id, "../escape")
    manager.close()


def test_configuration_is_runtime_and_alternate_model_requires_price_inputs(monkeypatch):
    monkeypatch.setenv("RDW_PROVIDER", "openai")
    monkeypatch.setenv("RDW_MODEL", "synthetic-other-model")
    for name in (
        "RDW_INPUT_RATE",
        "RDW_CACHED_RATE",
        "RDW_CACHE_WRITE_RATE",
        "RDW_OUTPUT_RATE",
        "RDW_PRICE_DATE",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="dated price"):
        ProviderConfig.environment()
    for name in ("RDW_INPUT_RATE", "RDW_CACHED_RATE", "RDW_CACHE_WRITE_RATE", "RDW_OUTPUT_RATE"):
        monkeypatch.setenv(name, "1")
    monkeypatch.setenv("RDW_PRICE_DATE", "2026-10-02")
    assert ProviderConfig.environment().model == "synthetic-other-model"


def test_new_interpretation_never_verifies_evidence(packet, monkeypatch):
    workbench, _, task = packet
    model, checker, _ = adapter(monkeypatch)
    workbench.adapter, workbench.verifier = model, checker
    proposal = workbench._proposal(task.context, task.context.project.revision + 1)
    assert proposal.evidence_state == "not_inspected"
    assert proposal.adoption == "proposed"
    assert proposal.provider_run.status == "SUCCEEDED"
    assert proposal.statements and proposal.source_refs


def test_failed_intake_call_receipt_is_durable_and_redacted(packet, monkeypatch):
    _, _, task = packet
    records = []
    model, _, requests = adapter(monkeypatch)
    model.receipt_sink = records.append
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(ProviderFailure):
        model.interpret(InterpretationTask(context=task.context))
    assert records[0].status == "FAILED"
    assert records[0].calls == ()
    assert not requests


@pytest.mark.parametrize(
    "broken",
    [
        [],
        {"status": "completed", "usage": "wrong"},
        {"status": "completed", "output": [], "usage": {"input_tokens": 1, "output_tokens": True}},
    ],
)
def test_malformed_provider_envelope_always_fails_safely(packet, monkeypatch, broken):
    _, _, task = packet
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-placeholder")
    model = OpenAIAdapter(
        ProviderConfig(provider="openai"),
        httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=broken))
        ),
    )
    with pytest.raises(ProviderFailure):
        model.interpret(InterpretationTask(context=task.context))


def test_real_interpretation_provenance_survives_later_edit_and_reevaluation(packet, monkeypatch):
    from domain.application import EditProject

    workbench, view, task = packet
    model, checker, requests = adapter(monkeypatch)
    workbench.adapter, workbench.verifier = model, checker
    identifier = view["project"]["project_id"]
    proposal = workbench._proposal(task.context, view["project"]["revision"] + 1)
    project = workbench.repository.project(workbench.scope(identifier))
    updated = project.model_copy(update={"revision": project.revision + 1, "objects": (proposal,)})
    workbench.repository.save_project(workbench.scope(identifier), updated, project.revision)
    view = workbench.edit(
        identifier,
        EditProject(
            expected_revision=updated.revision,
            idea="Synthetic changed question; no articulated account.",
        ),
    )
    context = workbench.context(identifier)
    assert any(p.historical for p in context.passages)
    assert any(not p.historical and "changed question" in p.text for p in context.passages)
    result = workbench.run(identifier, view["project"]["revision"])
    assert result["policy"]["idea"]["status"] == "pending"
    assert len(result["snapshot"]["documents"]) == 3
    assert result["snapshot"]["project"]["objects"][0]["freshness"] == "affected_by_change"


def test_revoked_packet_stops_before_focused_check(packet, monkeypatch):
    workbench, view, task = packet
    project_id = view["project"]["project_id"]

    def revoke(kind, output):
        assert not workbench.repository.db.connection.in_transaction
        if kind == "rdw_evaluation":
            passage = task.context.passages[0]
            workbench.repository.set_admission(
                workbench.scope(project_id),
                passage.source.document_id,
                passage.anchor.version,
                False,
            )
        return output

    model, checker, requests = adapter(monkeypatch, revoke)
    workbench.adapter, workbench.verifier = model, checker
    with pytest.raises(AccessDenied):
        workbench.run(project_id, view["project"]["revision"])
    assert len(requests) == 1
    assert not workbench.bundle(project_id).snapshots


def test_checking_contract_explicit_targets_and_rejects_omissions(packet, monkeypatch):
    _, _, task = packet
    model, checker, requests = adapter(monkeypatch)
    candidate = CandidateReview.model_validate(proposed(task))
    checker.review(task, candidate)
    payload = json.loads(requests[-1]["input"])
    expected = {
        "rating:" + str(r.dimension) for r in candidate.assessment.ratings if r.rating is not None
    }
    expected |= {"flag:account_articulated", "flag:study_assessable"}
    expected |= {"finding:" + f.rule_id for f in candidate.assessment.findings}
    expected |= {"statement:" + s.statement_id for s in candidate.statements}
    assert set(payload["targets"]) == expected
    assert "targets array" in requests[-1]["instructions"]
    assert "rating:8" not in payload["targets"]

    def omit(kind, output):
        if kind == "rdw_checking":
            output["decisions"].pop()
        return output

    model, checker, requests = adapter(monkeypatch, omit)
    with pytest.raises(ProviderFailure, match="INCOMPLETE_CHECK"):
        checker.review(task, candidate)
    assert len(requests) == 1


def test_publication_race_retains_incurred_checking_usage(packet, monkeypatch):
    from domain.application import EditProject
    from persistence.repository import Conflict

    w, view, _ = packet
    pid, revision = view["project"]["project_id"], view["project"]["revision"]

    def change(kind, output):
        if kind == "rdw_checking":
            w.edit(
                pid, EditProject(expected_revision=revision, idea="Synthetic edit during checking.")
            )
        return output

    model, checker, requests = adapter(monkeypatch, change)
    w.adapter, w.verifier = model, checker
    with pytest.raises(Conflict) as caught:
        w.run(pid, revision)
    assert len(requests) == 2
    assert caught.value.provider_metadata and len(caught.value.provider_metadata.calls) == 2
    assert sum(c.input_tokens for c in caught.value.provider_metadata.calls) == 800
    assert not w.bundle(pid).snapshots
