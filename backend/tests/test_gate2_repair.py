"""Synthetic regressions for GATE-2; no scientific keyword judgments or live calls."""

import json

import httpx
import pytest
from test_provider import adapter, envelope, proposed, reference
from test_provider import packet as packet
from test_workspaces import check, decide, propose, save
from test_workspaces import workspace_client as workspace_client

from domain.application import CandidateReview
from domain.models import Adoption
from domain.research import DevelopRequest, WorkspaceTask
from model_adapters.checking import AssessmentChecker
from model_adapters.config import ProviderConfig
from model_adapters.fake import FakeModel
from model_adapters.openai import OpenAIAdapter
from model_adapters.runtime import ProviderFailure
from services.research import ResearchService, identity


def setup_dependency(client, view):
    view = save(client, view, "Argument", {"claim": "Unrelated synthetic assertion"})
    unrelated = view["project"]["objects"][-1]
    view = save(
        client,
        view,
        "Usefulness",
        {"boundaries": "Only use the claim within the synthetic boundary"},
    )
    upstream = view["project"]["objects"][-1]
    view = save(
        client,
        view,
        "Study",
        {"claim": "This narrower claim depends on that boundary"},
        depends_on=[upstream["object_id"]],
    )
    dependent = view["project"]["objects"][-1]
    study_review = check(client, view, "Study")
    argument_review = check(client, view, "Argument")
    return view, upstream, dependent, unrelated, study_review, argument_review


def fetch_review(client, view, review):
    return client.get(
        "/api/projects/"
        + view["project"]["project_id"]
        + "/reviews/"
        + review["snapshot"]["snapshot_id"]
    ).json()


@pytest.mark.parametrize("sequence", ["consequential", "wording_lineage", "dependent_edit"])
def test_exact_audit_dependency_sequences_and_immutable_history(workspace_client, sequence):
    client, w, view = workspace_client
    view, upstream, dependent, unrelated, review, other_review = setup_dependency(client, view)
    identifier = view["project"]["project_id"]
    baseline = w.repository.project(
        w.scope(identifier), view["project"]["revision"]
    ).model_dump_json()
    revision = view["project"]["revision"]
    original_identity = upstream["object_id"]
    if sequence == "wording_lineage":
        view = save(
            client,
            view,
            "Usefulness",
            {"boundaries": "Only use the claim within the  synthetic boundary"},
            object_id=upstream["object_id"],
            change="wording",
        )
        upstream = view["project"]["objects"][-1]
        assert upstream["object_id"] != original_identity
        assert upstream["dependency_identity"] == original_identity
        assert fetch_review(client, view, review)["stale"] is False
        assert (
            next(o for o in view["project"]["objects"] if o["object_id"] == dependent["object_id"])[
                "freshness"
            ]
            == "current"
        )
    if sequence == "dependent_edit":
        previous_dependencies = dependent["dependencies"]
        view = save(
            client,
            view,
            "Study",
            {"claim": "This narrower claim depends on that  boundary"},
            object_id=dependent["object_id"],
            change="wording",
        )
        dependent = view["project"]["objects"][-1]
        assert dependent["dependencies"] == previous_dependencies
        assert fetch_review(client, view, review)["stale"] is False
    view = save(
        client,
        view,
        "Usefulness",
        {"boundaries": "A materially different synthetic condition"},
        object_id=upstream["object_id"],
    )
    current_dependent = next(
        o for o in view["project"]["objects"] if o["object_id"] == dependent["object_id"]
    )
    assert current_dependent["freshness"] == "affected_by_change"
    assert current_dependent["payload"] == dependent["payload"]
    assert current_dependent["evidence_state"] == dependent["evidence_state"]
    changed_review = fetch_review(client, view, review)
    assert changed_review["stale"] is True
    for key in ("snapshot", "summary", "assessment", "policy"):
        assert changed_review[key] == review[key]
    assert (
        next(o for o in view["project"]["objects"] if o["object_id"] == unrelated["object_id"])[
            "freshness"
        ]
        == unrelated["freshness"]
    )
    assert fetch_review(client, view, other_review)["stale"] is False
    assert w.repository.project(w.scope(identifier), revision).model_dump_json() == baseline
    assert w.view(identifier)["project"] == view["project"]
    assert check(client, view, "Study")["stale"] is False


def test_explicit_dependency_removal_is_deliberate_and_transitive_change_is_selective(
    workspace_client,
):
    client, _, view = workspace_client
    view, upstream, dependent, _, _, _ = setup_dependency(client, view)
    view = save(
        client,
        view,
        "Next Actions",
        {"task": "Reinspect the dependent synthetic claim"},
        depends_on=[dependent["object_id"]],
    )
    action = view["project"]["objects"][-1]
    view = save(
        client,
        view,
        "Study",
        {"claim": "Revised conditional claim"},
        object_id=dependent["object_id"],
        change="substantive",
        depends_on=[],
    )
    replacement = view["project"]["objects"][-1]
    assert not any(d["key"].startswith("object:") for d in replacement["dependencies"])
    view = save(
        client,
        view,
        "Usefulness",
        {"boundaries": "Changed upstream condition"},
        object_id=upstream["object_id"],
    )
    assert (
        next(o for o in view["project"]["objects"] if o["object_id"] == replacement["object_id"])[
            "freshness"
        ]
        == "current"
    )
    # An actual Study change still traverses the replacement's stable identity.
    view = save(
        client,
        view,
        "Study",
        {"claim": "Consequentially changed claim"},
        object_id=replacement["object_id"],
    )
    assert (
        next(o for o in view["project"]["objects"] if o["object_id"] == action["object_id"])[
            "freshness"
        ]
        == "affected_by_change"
    )


def test_dependency_lineage_survives_adopted_replacement(workspace_client):
    client, w, view = workspace_client
    view, upstream, dependent, _, _, _ = setup_dependency(client, view)
    view = propose(client, view, "Usefulness", upstream["object_id"])
    suggestion = view["project"]["objects"][-1]
    view = decide(client, view, suggestion, "accepted")
    project = w.repository.project(w.scope(view["project"]["project_id"]))
    assert identity(project, suggestion["object_id"]) == upstream["object_id"]
    assert (
        next(o for o in view["project"]["objects"] if o["object_id"] == dependent["object_id"])[
            "freshness"
        ]
        == "affected_by_change"
    )
    assert (
        next(o for o in project.objects if o.object_id == upstream["object_id"]).adoption
        == Adoption.SUPERSEDED
    )


def test_legacy_lineage_resolves_without_rewriting_objects(workspace_client):
    _, w, view = workspace_client
    project = w.repository.project(w.scope(view["project"]["project_id"]))
    first = project.objects[0]
    replaced = first.model_copy(update={"adoption": Adoption.SUPERSEDED})
    successor = first.model_copy(
        update={
            "object_id": "synthetic-successor",
            "target_object_id": first.object_id,
            "adoption": Adoption.ACCEPTED,
            "dependency_identity": None,
        }
    )
    legacy = project.model_copy(update={"objects": (replaced, successor)})
    assert identity(legacy, successor.object_id) == first.object_id
    assert replaced.dependency_identity is None


@pytest.mark.parametrize("action", ["confirm", "qualify", "narrow", "withdraw"])
def test_checker_cannot_promote_unchecked_summary_and_checked_disposition_survives(
    packet, monkeypatch, action
):
    w, view, task = packet
    original = proposed(task)["summary"]["obstacle"]
    new_allegation = (
        "Synthetic ungrounded new blocking allegation absent from the evaluator statements"
    )

    def change(kind, output):
        if kind == "rdw_checking":
            output["summary"]["obstacle"] = new_allegation
            output["obstacle_action"] = action
            if action == "withdraw":
                for decision in output["decisions"]:
                    if decision["target"] == "statement:principal-obstacle":
                        decision["disposition"] = "needs_revision"
        return output

    model, checker, requests = adapter(monkeypatch, change)
    w.adapter, w.verifier = model, checker
    result = w.run(view["project"]["project_id"], view["project"]["revision"])
    assert new_allegation not in result["summary"]["obstacle"]
    assert any(
        new_allegation in item and "Unresolved checker proposal" in item
        for item in result["summary"]["limitations"]
    )
    if action == "withdraw":
        assert "withdrawn" in result["summary"]["obstacle"]
    else:
        assert original in result["summary"]["obstacle"]
    if action in ("qualify", "narrow"):
        assert result["summary"]["obstacle"].startswith("Within the inspected source scope only:")
    assert len(requests) == 2
    assert requests[-1]["text"]["format"]["strict"] is True
    assert "checking-v4" in model.prompt_configuration
    assert (
        w.review(view["project"]["project_id"], result["snapshot"]["snapshot_id"])["summary"]
        == result["summary"]
    )


def test_new_checker_issue_is_retained_with_refs_but_never_verified(packet, monkeypatch):
    _, _, task = packet

    def change(kind, output):
        if kind == "rdw_checking":
            output["proposed_objections"] = [
                {
                    "statement_id": "synthetic-new-issue",
                    "kind": "model_inference",
                    "text": "Synthetic possible issue requiring a separate inspection",
                    "source_refs": [reference(task.context)],
                }
            ]
        return output

    model, checker, _ = adapter(monkeypatch, change)
    checked = checker.review(task, CandidateReview.model_validate(proposed(task)))
    issue = checked.statements[-1]
    assert issue.statement_id == "synthetic-new-issue" and issue.source_refs
    assert not any(d.target == "statement:" + issue.statement_id for d in checked.checks)
    assert issue.text not in checked.summary.obstacle
    assert any("Unresolved proposed objection" in item for item in checked.summary.limitations)
    model.close()


def test_unsupported_existing_obstacle_is_not_a_settled_blocker(packet, monkeypatch):
    _, _, task = packet

    def change(kind, output):
        if kind == "rdw_checking":
            for decision in output["decisions"]:
                if decision["target"] == "statement:principal-obstacle":
                    decision["disposition"] = "unresolved"
        return output

    model, checker, _ = adapter(monkeypatch, change)
    result = checker.review(task, CandidateReview.model_validate(proposed(task)))
    assert result.summary.obstacle.startswith(
        "Unresolved principal objection (not a settled blocker):"
    )
    model.close()


@pytest.mark.parametrize(
    "omitted", ["generic", "judgment", "input", "output", "branches", "blank", None]
)
def test_generated_diagnostic_action_completeness_actual_adapter(
    workspace_client, monkeypatch, omitted
):
    client, w, view = workspace_client
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-placeholder")
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        payload = json.loads(body["input"])
        if body["text"]["format"]["name"] == "rdw_workspace":
            output = (
                FakeModel().develop(WorkspaceTask.model_validate(payload)).model_dump(mode="json")
            )
            if omitted == "generic":
                output["record"]["fields"] = [
                    dict(output["record"]["fields"][0], text="Do more research.")
                ]
            elif omitted == "blank":
                next(f for f in output["record"]["fields"] if f["key"] == "judgment")["text"] = (
                    "   "
                )
            elif omitted:
                output["record"]["fields"] = [
                    f for f in output["record"]["fields"] if f["key"] != omitted
                ]
        else:
            output = {
                "decisions": [
                    {
                        "target": t,
                        "disposition": "unresolved",
                        "reason": "Synthetic proposal, not verified science",
                        "source_refs": [],
                    }
                    for t in payload["targets"]
                ],
                "limitations": ["Synthetic only"],
            }
        return httpx.Response(200, json=envelope(output))

    model = OpenAIAdapter(
        ProviderConfig(provider="openai"), httpx.Client(transport=httpx.MockTransport(handler))
    )
    w.adapter, w.verifier = model, AssessmentChecker(model)
    identifier = view["project"]["project_id"]
    before = w.bundle(identifier).model_dump_json()
    request = DevelopRequest(
        expected_revision=view["project"]["revision"], workspace="Next Actions"
    )
    if omitted:
        with pytest.raises(ProviderFailure, match="MALFORMED_OUTPUT"):
            ResearchService(w).develop(identifier, request)
        assert w.bundle(identifier).model_dump_json() == before
        assert len(calls) == 1
    else:
        result = ResearchService(w).develop(identifier, request)
        obj = result["project"]["objects"][-1]
        assert obj["adoption"] == "proposed" and obj["evidence_state"] == "not_inspected"
        assert len(calls) == 2
    # Manual notes remain valid; they are never relabeled as generated diagnostic plans.
    w.adapter, w.verifier = FakeModel(), w.verifier
    view = w.view(identifier)
    manual = save(client, view, "Next Actions", {"task": "Partial synthetic user note"})
    assert manual["project"]["objects"][-1]["origin"] == "user_text"
    model.close()


def test_transitive_explicit_invalidation_reaches_actions_without_marking_unrelated_review(
    workspace_client,
):
    client, _, view = workspace_client
    view, upstream, dependent, _, review, unrelated_review = setup_dependency(client, view)
    view = save(
        client,
        view,
        "Next Actions",
        {"task": "Reinspect conditional claim"},
        depends_on=[dependent["object_id"]],
    )
    action = view["project"]["objects"][-1]
    view = save(
        client,
        view,
        "Usefulness",
        {"boundaries": "Changed synthetic boundary"},
        object_id=upstream["object_id"],
    )
    assert (
        next(o for o in view["project"]["objects"] if o["object_id"] == action["object_id"])[
            "freshness"
        ]
        == "affected_by_change"
    )
    assert fetch_review(client, view, review)["stale"] is True
    assert fetch_review(client, view, unrelated_review)["stale"] is False


def test_pre_repair_snapshot_dependencies_are_derived_from_frozen_project(
    workspace_client, monkeypatch
):
    client, w, view = workspace_client
    view, upstream, _, _, review, _ = setup_dependency(client, view)
    identifier = view["project"]["project_id"]
    snapshot_id = review["snapshot"]["snapshot_id"]
    legacy = w.repository.snapshot(w.scope(identifier), snapshot_id)
    legacy = legacy.model_copy(
        update={
            "dependencies": tuple(d for d in legacy.dependencies if not d.key.startswith("object:"))
        }
    )
    original_snapshot = w.repository.snapshot
    monkeypatch.setattr(
        w.repository,
        "snapshot",
        lambda scope, sid: legacy if sid == snapshot_id else original_snapshot(scope, sid),
    )
    assert w.review(identifier, snapshot_id)["stale"] is False
    view = save(
        client,
        view,
        "Usefulness",
        {"boundaries": "Changed condition"},
        object_id=upstream["object_id"],
    )
    assert w.review(identifier, snapshot_id)["stale"] is True
    assert (
        legacy.snapshot.model_dump(
            mode="json",
            exclude_unset=True,
            exclude={"documents": {"__all__": {"original_storage_reference"}}},
        )
        == review["snapshot"]
    )


def test_adopting_a_replacement_preserves_its_targets_explicit_upstream_dependency(
    workspace_client,
):
    client, _, view = workspace_client
    view, upstream, dependent, _, _, _ = setup_dependency(client, view)
    view = propose(client, view, "Study", dependent["object_id"])
    suggestion = view["project"]["objects"][-1]
    view = decide(client, view, suggestion, "accepted")
    review = check(client, view, "Study")
    view = save(
        client,
        view,
        "Usefulness",
        {"boundaries": "Changed condition after adoption"},
        object_id=upstream["object_id"],
    )
    assert (
        next(o for o in view["project"]["objects"] if o["object_id"] == suggestion["object_id"])[
            "freshness"
        ]
        == "affected_by_change"
    )
    assert fetch_review(client, view, review)["stale"] is True


def test_wording_edit_does_not_silently_refresh_already_affected_support(workspace_client):
    client, _, view = workspace_client
    view, upstream, dependent, _, _, _ = setup_dependency(client, view)
    view = save(
        client,
        view,
        "Usefulness",
        {"boundaries": "Changed condition"},
        object_id=upstream["object_id"],
    )
    affected = next(
        o for o in view["project"]["objects"] if o["object_id"] == dependent["object_id"]
    )
    view = save(
        client,
        view,
        "Study",
        {"claim": "This narrower claim depends on that  boundary"},
        object_id=dependent["object_id"],
        change="wording",
    )
    edited = view["project"]["objects"][-1]
    assert edited["freshness"] == "affected_by_change"
    assert edited["dependencies"] == affected["dependencies"]
