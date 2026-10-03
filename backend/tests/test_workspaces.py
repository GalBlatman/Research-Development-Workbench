import json
import socket

import httpx
import pytest
from fastapi.testclient import TestClient
from test_application import add, create, service

from api.app import create_app
from domain.research import (
    DevelopRequest,
    WorkspaceTask,
)
from model_adapters.checking import AssessmentChecker
from model_adapters.config import ProviderConfig
from model_adapters.fake import FakeModel
from model_adapters.openai import OpenAIAdapter
from model_adapters.runtime import ProviderFailure
from services.research import ResearchService


@pytest.fixture
def workspace_client(tmp_path, manifest):
    w = service(tmp_path, manifest)
    with TestClient(create_app(w)) as client:
        view = add(client, create(client))
        yield client, w, view
    w.repository.db.close()


def save(client, view, workspace, fields, **extra):
    root = "/api/projects/" + view["project"]["project_id"]
    response = client.post(
        root + "/records",
        json={
            "expected_revision": view["project"]["revision"],
            "record": {
                "kind": "research_record",
                "workspace": workspace,
                "title": extra.pop("title", workspace + " synthetic record"),
                "fields": [
                    {
                        "key": key,
                        "text": value,
                        "state": "specified_but_untested",
                        "origin": "user_text",
                        "source_refs": [],
                    }
                    for key, value in fields.items()
                ],
            },
            **extra,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def check(client, view, workspace):
    response = client.post(
        "/api/projects/" + view["project"]["project_id"] + "/workspace-checks",
        json={"expected_revision": view["project"]["revision"], "workspace": workspace},
    )
    assert response.status_code == 200, response.text
    return response.json()


def propose(client, view, workspace, object_id=None):
    response = client.post(
        "/api/projects/" + view["project"]["project_id"] + "/workspace-proposals",
        json={
            "expected_revision": view["project"]["revision"],
            "workspace": workspace,
            "object_id": object_id,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def decide(client, view, obj, action):
    response = client.post(
        "/api/projects/"
        + view["project"]["project_id"]
        + "/proposals/"
        + obj["object_id"]
        + "/decision",
        json={
            "expected_revision": view["project"]["revision"],
            "action": action,
            "reason": "Synthetic user decision",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("route", ["EXPLAIN", "ESTABLISH", "TEST"])
def test_all_workspace_catalogs_routes_and_manual_records(workspace_client, route):
    client, w, _ = workspace_client
    view = add(client, create(client, route=route))
    root = "/api/projects/" + view["project"]["project_id"]
    catalog = client.get(root + "/workspaces").json()
    assert len(catalog["workspaces"]) == 10
    assert ("account" in catalog["fields"]["Argument"]) == (route == "EXPLAIN")
    for workspace, fields in catalog["fields"].items():
        key = next(k for k in fields if k not in catalog["choices"] and k != "source_claim")
        view = save(client, view, workspace, {key: "Synthetic user-authored research note"})
    assert (
        len([o for o in view["project"]["objects"] if o["payload"]["kind"] == "research_record"])
        == 7
    )
    assert client.get(root).json()["project"] == view["project"]
    assert client.get(root + "/history").json()["revisions"][-1] == view["project"]


def test_literature_axes_predecessor_not_rival_and_source_provenance(workspace_client):
    client, w, view = workspace_client
    source = next(s for s in view["sources"] if s["source"]["role"] == "literature")
    ref = {
        "document_id": source["source"]["document_id"],
        "version": 1,
        "anchor_id": source["anchors"][0]["anchor_id"],
    }
    view = save(
        client,
        view,
        "Literature",
        {
            "source_claim": "Synthetic attributed claim",
            "user_interpretation": "My tentative interpretation",
            "model_synthesis": "No model inference inspected",
            "relation": "closest predecessor",
            "novelty": "unresolved overlap",
            "coverage": "Only the supplied excerpt; absence is not a literature gap",
        },
        source_refs=[ref],
    )
    obj = view["project"]["objects"][-1]
    assert obj["source_refs"] == [ref]
    assert obj["evidence_state"] == "specified_but_untested"
    fields = {f["key"]: f["text"] for f in obj["payload"]["fields"]}
    assert fields["relation"] == "closest predecessor" and "rival" not in fields["relation"]
    assert len({fields[k] for k in ("source_claim", "user_interpretation", "model_synthesis")}) == 3
    view = propose(client, view, "Literature")
    generated = view["project"]["objects"][-1]
    assert generated["origin"] == "development_suggestion"
    assert generated["source_refs"][0] == ref
    assert generated["evidence_state"] == "not_inspected"
    assert all(f["origin"] == "development_suggestion" for f in generated["payload"]["fields"])
    assert (
        "exhaustive"
        in client.get("/api/projects/" + view["project"]["project_id"] + "/workspaces").json()[
            "note"
        ]
        or "absence"
        in client.get("/api/projects/" + view["project"]["project_id"] + "/workspaces").json()[
            "note"
        ]
    )


def test_multiple_alternatives_and_proposed_completed_study(workspace_client):
    client, _, view = workspace_client
    for account, implication in (
        ("Shared incentives", "Responds to changed pay"),
        ("Common understanding", "Responds to changed requests"),
    ):
        view = save(
            client,
            view,
            "Alternatives",
            {
                "focal": "Explicit requests",
                "alternative": account,
                "plausibility": "Explicit synthetic assumption",
                "implications": implication,
                "evidence": "Compare requests and incentives",
                "adjudication": "unclear",
            },
            title=account,
        )
    alternatives = [
        o
        for o in view["project"]["objects"]
        if isinstance(o["payload"], dict) and o["payload"].get("workspace") == "Alternatives"
    ]
    assert len(alternatives) == 2
    view = save(
        client,
        view,
        "Study",
        {
            "claim": "A bounded association",
            "evidence_phase": "proposed",
            "analysis": "Planned descriptive comparison",
        },
    )
    planned = view["project"]["objects"][-1]
    view = save(
        client,
        view,
        "Study",
        {
            "claim": "A bounded association",
            "evidence_phase": "completed (user-reported)",
            "analysis": "Synthetic user-reported description, not reproduced",
        },
    )
    completed = view["project"]["objects"][-1]
    assert planned["payload"] != completed["payload"]
    assert completed["evidence_state"] != "documented_or_verified"


def test_accept_reject_history_and_selective_staleness_refresh(workspace_client):
    client, w, view = workspace_client
    root = "/api/projects/" + view["project"]["project_id"]
    study_review = check(client, view, "Study")
    argument_review = check(client, view, "Argument")
    before = w.repository.snapshot(
        w.scope(view["project"]["project_id"]), argument_review["snapshot"]["snapshot_id"]
    ).model_dump_json()
    historical = client.get(root + "/history/" + str(view["project"]["revision"]) + "/export").text
    view = propose(client, view, "Study")
    original = view["project"]["objects"][-1]
    earlier = view["project"]["revision"]
    view = decide(client, view, original, "accepted")
    adopted = next(o for o in view["project"]["objects"] if o["object_id"] == original["object_id"])
    assert view["project"]["revision"] == earlier + 1
    assert adopted["evidence_state"] == original["evidence_state"] == "not_inspected"
    assert (
        adopted["payload"] == original["payload"]
        and adopted["generated_by_run_id"] == original["generated_by_run_id"]
    )
    assert view["project"]["actions"][-1]["action"] == "accepted"
    assert (
        client.get(root + "/reviews/" + study_review["snapshot"]["snapshot_id"]).json()["stale"]
        is True
    )
    assert (
        client.get(root + "/reviews/" + argument_review["snapshot"]["snapshot_id"]).json()["stale"]
        is False
    )
    assert (
        w.repository.snapshot(
            w.scope(view["project"]["project_id"]), argument_review["snapshot"]["snapshot_id"]
        ).model_dump_json()
        == before
    )
    assert (
        client.get(
            root + "/history/" + str(argument_review["snapshot"]["project"]["revision"]) + "/export"
        ).text
        == historical
    )
    refreshed = check(client, view, "Study")
    assert refreshed["stale"] is False and refreshed["target_workspace"] == "Study"
    assert [r["dimension"] for r in refreshed["assessment"]["ratings"]] == [8, 9, 10]
    old_project_content = [
        o["payload"] for o in view["project"]["objects"] if o["adoption"] == "accepted"
    ]
    view = propose(client, view, "Alternatives")
    suggestion = view["project"]["objects"][-1]
    view = decide(client, view, suggestion, "rejected")
    assert [
        o["payload"] for o in view["project"]["objects"] if o["adoption"] == "accepted"
    ] == old_project_content
    assert (
        client.get(root + "/reviews/" + refreshed["snapshot"]["snapshot_id"]).json()["stale"]
        is False
    )
    assert client.get(root + "/history").json()["actions"][-1]["action"] == "rejected"


def test_explicit_dependencies_wording_resources_and_source_changes(workspace_client):
    client, _, view = workspace_client
    root = "/api/projects/" + view["project"]["project_id"]
    view = save(client, view, "Argument", {"claim": "Synthetic original claim"})
    argument = view["project"]["objects"][-1]
    view = save(
        client, view, "Study", {"claim": "Tests that argument"}, depends_on=[argument["object_id"]]
    )
    study = view["project"]["objects"][-1]
    review = check(client, view, "Argument")
    view = save(
        client,
        view,
        "Argument",
        {"claim": "Synthetic original  claim"},
        object_id=argument["object_id"],
        change="wording",
    )
    assert (
        next(o for o in view["project"]["objects"] if o["object_id"] == study["object_id"])[
            "freshness"
        ]
        == "current"
    )
    assert (
        client.get(root + "/reviews/" + review["snapshot"]["snapshot_id"]).json()["stale"] is False
    )
    view = save(
        client,
        view,
        "Next Actions",
        {"task": "Read an excerpt", "resources": "One bounded reading session"},
        change="resources",
    )
    assert (
        client.get(root + "/reviews/" + review["snapshot"]["snapshot_id"]).json()["stale"] is False
    )
    current = next(
        o
        for o in reversed(view["project"]["objects"])
        if o["payload"].get("workspace") == "Argument"
    )
    view = save(
        client,
        view,
        "Argument",
        {"claim": "Synthetic substantively different claim"},
        object_id=current["object_id"],
    )
    assert (
        next(o for o in view["project"]["objects"] if o["object_id"] == study["object_id"])[
            "freshness"
        ]
        == "affected_by_change"
    )
    source = next(s for s in view["sources"] if s["source"]["role"] == "literature")
    old_version = source["version"]
    response = client.post(
        root + "/sources/" + source["source"]["document_id"] + "/versions",
        json={
            "expected_revision": view["project"]["revision"],
            "title": source["source"]["title"],
            "attribution": "Synthetic source",
            "text": "Synthetic revised original excerpt",
            "authorized": True,
            "admitted": True,
        },
    )
    assert response.status_code == 200, response.text
    source = next(
        s
        for s in response.json()["sources"]
        if s["source"]["document_id"] == source["source"]["document_id"]
    )
    assert source["version"] == old_version + 1


def test_bounded_actions_exports_and_invalid_scope(workspace_client, monkeypatch):
    client, w, view = workspace_client
    monkeypatch.setattr(socket, "create_connection", lambda *a: pytest.fail("Offline network"))
    view = propose(client, view, "Next Actions")
    obj = view["project"]["objects"][-1]
    fields = {f["key"]: f["text"] for f in obj["payload"]["fields"]}
    assert all(
        fields[k]
        for k in (
            "task",
            "reason",
            "judgment",
            "input",
            "output",
            "workspace",
            "dependency",
            "branches",
        )
    )
    root = "/api/projects/" + view["project"]["project_id"]
    for kind in ("json", "markdown", "plan"):
        export = client.get(root + "/exports/" + kind)
        assert export.status_code == 200
        assert "not_inspected" in export.text
        assert "original_storage_reference" not in export.text
    bad = client.post(
        root + "/records",
        json={
            "expected_revision": view["project"]["revision"],
            "record": {
                "kind": "research_record",
                "workspace": "Study",
                "title": "Bad",
                "fields": [
                    {
                        "key": "claim",
                        "text": "Invented verified data",
                        "state": "documented_or_verified",
                    }
                ],
            },
        },
    )
    assert bad.status_code == 422
    foreign = client.get("/api/projects/foreign-project/workspaces")
    assert foreign.status_code == 404
    assert (
        client.post(
            root + "/workspace-proposals", json={"expected_revision": 1, "workspace": "Study"}
        ).status_code
        == 409
    )


@pytest.mark.parametrize("failure", [None, "budget", "invalid", "missing"])
def test_real_workspace_adapter_mapping_checks_and_budget(
    workspace_client, monkeypatch, failure, tmp_path
):
    client, w, view = workspace_client
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-placeholder")
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        assert body["store"] is False and body["background"] is False and "tools" not in body
        assert "synthetic-placeholder" not in json.dumps(body)
        payload = json.loads(body["input"])
        if body["text"]["format"]["name"] == "rdw_workspace":
            task = WorkspaceTask.model_validate(payload)
            result = FakeModel().develop(task).model_dump(mode="json")
            if failure == "invalid":
                result["source_records"] = []
        else:
            result = {
                "decisions": [
                    {
                        "target": target,
                        "disposition": "unresolved",
                        "reason": "Synthetic support remains uninspected",
                        "source_refs": [],
                    }
                    for target in payload["targets"]
                ],
                "limitations": ["Synthetic mocked check, not scientific validation"],
            }
            if failure == "missing":
                result["decisions"].pop()
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "model": "gpt-6-sol",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(result)}],
                    }
                ],
                "usage": {"input_tokens": 100, "output_tokens": 100},
            },
        )

    model = OpenAIAdapter(
        ProviderConfig(provider="openai", max_calls=1 if failure == "budget" else 4),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )
    w.adapter, w.verifier = model, AssessmentChecker(model)
    before = w.bundle(view["project"]["project_id"]).model_dump_json()
    if failure:
        with pytest.raises(ProviderFailure):
            ResearchService(w).develop(
                view["project"]["project_id"],
                DevelopRequest(expected_revision=view["project"]["revision"], workspace="Study"),
            )
        assert before == w.bundle(view["project"]["project_id"]).model_dump_json()
        assert len(calls) == (2 if failure == "missing" else 1)
    else:
        from services.runs import RunManager

        identifier = view["project"]["project_id"]

        def factory():
            result = service(tmp_path, w.manifest)
            result.adapter, result.verifier = model, AssessmentChecker(model)
            return result

        manager = RunManager(tmp_path / "receipts", factory)
        client.app.state.runs = manager
        response = client.post(
            "/api/projects/" + identifier + "/workspace-proposals",
            json={"expected_revision": view["project"]["revision"], "workspace": "Study"},
        )
        assert response.status_code == 202
        manager.close()
        handle = manager.get(identifier, response.json()["run_id"])
        assert (
            handle.state == "succeeded"
            and handle.result_revision == view["project"]["revision"] + 1
        )
        assert handle.snapshot_id is None and handle.provider_run.status == "SUCCEEDED"
        client.app.state.runs = None
        result = client.get("/api/projects/" + identifier).json()
        obj = result["project"]["objects"][-1]
        assert obj["evidence_state"] == "not_inspected" and obj["adoption"] == "proposed"
        assert obj["provider_run"]["status"] == "SUCCEEDED"
        assert len(calls) == 2 and [c["text"]["format"]["name"] for c in calls] == [
            "rdw_workspace",
            "rdw_workspace-check",
        ]
        assert obj["support_dispositions"][0]["disposition"] == "unresolved"
    model.close()


def test_workspace_target_scope_and_adopted_content_is_not_fixture_scored(workspace_client):
    client, w, view = workspace_client
    root = "/api/projects/" + view["project"]["project_id"]
    view = save(client, view, "Study", {"claim": "Synthetic new claim"})
    study = view["project"]["objects"][-1]
    before = w.bundle(view["project"]["project_id"]).model_dump_json()
    bad = client.post(
        root + "/workspace-proposals",
        json={
            "expected_revision": view["project"]["revision"],
            "workspace": "Argument",
            "object_id": study["object_id"],
        },
    )
    assert (
        bad.status_code == 422
        and before == w.bundle(view["project"]["project_id"]).model_dump_json()
    )
    review = client.post(
        root + "/evaluations",
        json={
            "expected_revision": view["project"]["revision"],
            "scope": "FULL_EVALUATION",
        },
    )
    assert review.status_code == 201, review.text
    assert review.json()["snapshot"]["scope"] == "FULL_EVALUATION"
    assert all(r["rating"] is None for r in review.json()["assessment"]["ratings"])
    view = propose(client, view, "Study", study["object_id"])
    obj = view["project"]["objects"][-1]
    view = decide(client, view, obj, "superseded")
    assert view["project"]["objects"][-1]["freshness"] == "superseded"


def test_source_linked_study_review_invalidates_but_excluded_upload_does_not(workspace_client):
    client, _, view = workspace_client
    root = "/api/projects/" + view["project"]["project_id"]
    source = next(s for s in view["sources"] if s["source"]["role"] == "literature")
    ref = {
        "document_id": source["source"]["document_id"],
        "version": source["version"],
        "anchor_id": source["anchors"][0]["anchor_id"],
    }
    view = save(client, view, "Study", {"claim": "Design uses supplied source"}, source_refs=[ref])
    review = check(client, view, "Study")
    literature = check(client, view, "Literature")
    view = add(client, view, text="Synthetic excluded excerpt", admitted=False)
    assert (
        client.get(root + "/reviews/" + literature["snapshot"]["snapshot_id"]).json()["stale"]
        is False
    )
    response = client.post(
        root + "/sources/" + ref["document_id"] + "/versions",
        json={
            "expected_revision": view["project"]["revision"],
            "title": "Synthetic source",
            "attribution": "Synthetic fixture",
            "text": "Synthetic changed design-relevant passage",
            "authorized": True,
            "admitted": True,
        },
    )
    assert response.status_code == 200
    assert (
        client.get(root + "/reviews/" + review["snapshot"]["snapshot_id"]).json()["stale"] is True
    )
    obj = next(
        o for o in response.json()["project"]["objects"] if o["payload"].get("workspace") == "Study"
    )
    assert obj["source_refs"] == [ref] and obj["freshness"] == "affected_by_change"
