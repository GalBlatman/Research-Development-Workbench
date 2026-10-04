import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from test_application import create, service
from test_operations import synthetic_project
from test_persistence import store as store
from test_provider import adapter, envelope, proposed
from test_provider import packet as packet
from test_workspaces import check, propose, save
from test_workspaces import workspace_client as workspace_client

from api.app import create_app
from benchmarks.fixtures import synthetic
from benchmarks.metrics import compare
from benchmarks.store import AdminStore
from domain.application import CandidateReview
from domain.benchmark import BenchmarkExpectation, Feature, Judgment, Observation
from domain.models import DiagnosticAction, Verification
from domain.research import WorkspaceProposal
from model_adapters.config import ProviderConfig
from model_adapters.openai import OpenAIAdapter, policy_contract
from model_adapters.runtime import ProviderFailure
from persistence.database import Database
from services.backup import create_backup, inspect_state, restore_backup
from services.portability import portable_bundle
from services.runs import write_provider_receipt


def test_checker_preserves_all_unchecked_review_fields_and_server_disclaimer(packet, monkeypatch):
    _, _, task = packet
    candidate = CandidateReview.model_validate(proposed(task))

    def change(kind, output):
        if kind == "rdw_checking":
            output["summary"]["contribution"] = "Unchecked new contribution"
            output["summary"]["next_action"] = "Unchecked expensive new task"
            output["summary"]["deliverable"] = "Unchecked new deliverable"
            output["summary"]["outcome_branches"] = ["Unchecked success"]
            output["summary"]["limitations"] = ["Checker-specific limitation"]
            output["summary"]["disclaimer"] = "No caveats"
        return output

    model, checker, _ = adapter(monkeypatch, change)
    result = checker.review(task, candidate)
    for key in (
        "contribution",
        "next_action",
        "deliverable",
        "outcome_branches",
        "diagnostic_action",
    ):
        assert getattr(result.summary, key) == getattr(candidate.summary, key)
    assert set(candidate.summary.limitations) <= set(result.summary.limitations)
    assert "Checker-specific limitation" in result.summary.limitations
    assert "Unchecked new contribution" in " ".join(result.summary.limitations)
    assert result.summary.disclaimer != "No caveats"
    assert "not verified evidence" in result.summary.disclaimer
    model.close()


@pytest.mark.parametrize(
    "field", ("issue", "task", "required_input", "deliverable", "outcome_branches")
)
def test_diagnostic_action_rejects_placeholder_structure(field):
    values = dict(
        issue="A specified uncertainty",
        task="Inspect a source",
        required_input="Admitted source",
        deliverable="Attributed note",
        outcome_branches=("Supported", "Unsupported"),
    )
    values[field] = ("TBD", "TODO") if field == "outcome_branches" else "TBD"
    with pytest.raises(ValueError):
        DiagnosticAction(**values)


@pytest.mark.parametrize(
    "key,value,workspace",
    (
        ("evidence_phase", "completed (user-reported)", "Study"),
        ("support", "demonstrated (user-reported)", "Usefulness"),
    ),
)
def test_generated_reported_result_requires_grounding(key, value, workspace):
    with pytest.raises(ValueError, match="grounding"):
        WorkspaceProposal.model_validate(
            dict(
                record=dict(
                    workspace=workspace,
                    title="Synthetic",
                    fields=[dict(key=key, text=value, origin="model_inference")],
                ),
                reason="Proposal",
                limitations=["Synthetic only"],
            )
        )


@pytest.mark.parametrize("workspace", ("Brief", "Usefulness"))
def test_literature_overlap_invalidates_related_scope_only(workspace_client, workspace):
    client, _, view = workspace_client
    related = check(client, view, workspace)
    unrelated = check(client, view, "Study")
    view = save(client, view, "Literature", {"novelty": "unresolved overlap"})
    root = "/api/projects/" + view["project"]["project_id"] + "/reviews/"
    assert client.get(root + related["snapshot"]["snapshot_id"]).json()["stale"]
    assert not client.get(root + unrelated["snapshot"]["snapshot_id"]).json()["stale"]


def test_stale_accepted_head_rejected_and_one_head_remains(workspace_client):
    client, _, view = workspace_client
    view = save(client, view, "Study", {"claim": "Synthetic original claim"})
    first = view["project"]["objects"][-1]
    view = save(
        client, view, "Study", {"claim": "Synthetic revised claim"}, object_id=first["object_id"]
    )
    root = "/api/projects/" + view["project"]["project_id"]
    response = client.post(
        root + "/records",
        json=dict(
            expected_revision=view["project"]["revision"],
            object_id=first["object_id"],
            record=first["payload"],
        ),
    )
    assert response.status_code == 409
    assert (
        len(
            [
                o
                for o in view["project"]["objects"]
                if o["payload"].get("workspace") == "Study" and o["adoption"] == "accepted"
            ]
        )
        == 1
    )


def test_editing_generated_fields_preserves_unchanged_origin_and_evidence(workspace_client):
    client, _, view = workspace_client
    view = propose(client, view, "Next Actions")
    proposal = view["project"]["objects"][-1]
    record = json.loads(json.dumps(proposal["payload"]))
    for field in record["fields"]:
        field["origin"] = "user_text"
    record["fields"][0]["text"] += " (author clarification)"
    response = client.post(
        "/api/projects/" + view["project"]["project_id"] + "/records",
        json=dict(
            expected_revision=view["project"]["revision"],
            object_id=proposal["object_id"],
            record=record,
        ),
    )
    assert response.status_code == 200, response.text
    edited = response.json()["project"]["objects"][-1]
    assert edited["origin"] != "user_text"
    assert edited["payload"]["fields"][0]["origin"] == "user_text"
    assert edited["payload"]["fields"][1]["origin"] == proposal["payload"]["fields"][1]["origin"]
    assert edited["evidence_state"] == proposal["evidence_state"] == "not_inspected"


def test_wording_cannot_change_scientific_choice(workspace_client):
    client, _, view = workspace_client
    view = save(client, view, "Study", {"evidence_phase": "proposed"})
    obj = view["project"]["objects"][-1]
    record = obj["payload"]
    record["fields"][0]["text"] = "completed (user-reported)"
    response = client.post(
        "/api/projects/" + view["project"]["project_id"] + "/records",
        json=dict(
            expected_revision=view["project"]["revision"],
            object_id=obj["object_id"],
            record=record,
            change="wording",
        ),
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "forgery", ("provider_user", "generated_source", "documented", "policy_score", "policy_hash")
)
def test_portable_import_cannot_escalate_authority(tmp_path, manifest, forgery):
    w, pid = synthetic_project(tmp_path, manifest)
    data = json.loads(w.export(pid, "json"))
    obj = data["import_bundle"]["revisions"][-1]["objects"][0]
    if forgery == "provider_user":
        obj["origin"] = "user_text"
        obj["generated_by_run_id"] = None
        obj["operation_id"] = "synthetic-provider-operation"
    elif forgery == "generated_source":
        obj["origin"] = "document_extraction"
    elif forgery == "documented":
        obj["evidence_state"] = "documented_or_verified"
    elif forgery == "policy_score":
        data["import_bundle"]["snapshots"][0]["policy_result"]["label"] = "Forged endorsement"
    else:
        for part in ("snapshot",):
            data["import_bundle"]["snapshots"][0][part]["policy_manifest_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        portable_bundle(json.dumps(data))
    w.repository.db.close()


@pytest.mark.parametrize(
    "status,code",
    (
        (401, "AUTHENTICATION_FAILED"),
        (403, "PERMISSION_DENIED"),
        (404, "MODEL_UNAVAILABLE"),
        (400, "INVALID_REQUEST"),
        (413, "CONTEXT_LIMIT"),
        (429, "RATE_LIMIT"),
        (503, "TRANSIENT_PROVIDER_ERROR"),
    ),
)
def test_provider_specific_error_taxonomy(packet, monkeypatch, status, code):
    _, _, task = packet
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-placeholder")
    model = OpenAIAdapter(
        ProviderConfig(retries=0),
        httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(status, json={"error": {"code": "synthetic"}})
            )
        ),
    )
    with pytest.raises(ProviderFailure) as failure:
        model.assess(task)
    assert failure.value.code == code
    assert failure.value.metadata.calls[-1].status == code
    model.close()


def test_returned_model_mismatch_is_recorded(packet, monkeypatch):
    _, _, task = packet
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-placeholder")
    data = envelope(proposed(task))
    data["model"] = "unauthorized-model"
    model = OpenAIAdapter(
        ProviderConfig(),
        httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=data))),
    )
    with pytest.raises(ProviderFailure) as failure:
        model.assess(task)
    assert failure.value.code == "MODEL_MISMATCH"
    assert failure.value.metadata.calls[-1].returned_model == "unauthorized-model"
    model.close()


def test_interpretation_call_has_no_database_transaction_and_durable_receipt(
    tmp_path, manifest, monkeypatch
):
    w = service(tmp_path, manifest)
    model, checker, _ = adapter(monkeypatch)
    handler = model.client._transport.handler

    def outside_transaction(request):
        assert not w.repository.db.connection.in_transaction
        return handler(request)

    model.client = httpx.Client(transport=httpx.MockTransport(outside_transaction))
    root = tmp_path / "receipts"
    model.receipt_sink = lambda receipt: write_provider_receipt(root, receipt)
    w.adapter, w.verifier = model, checker
    with TestClient(create_app(w)) as client:
        create(client)
    assert len(list(root.glob("*.call-1.json"))) == 1
    assert len([p for p in root.glob("*.json") if ".call-" not in p.name]) == 1
    model.close()
    w.repository.db.close()


@pytest.mark.parametrize("mutation", ("missing_original", "corrupt_original", "head"))
def test_health_and_backup_inspect_actual_state(tmp_path, manifest, mutation):
    w, pid = synthetic_project(tmp_path, manifest)
    inspect_state(w.repository.db, tmp_path)
    if mutation == "head":
        w.repository.db.execute("UPDATE projects SET revision=revision+1")
    else:
        path = next((tmp_path / "originals").iterdir())
        if mutation == "missing_original":
            path.unlink()
        else:
            path.write_bytes(b"Corrupt synthetic original")
    before = sorted(p.as_posix() for p in tmp_path.rglob("*"))
    with pytest.raises((ValueError, KeyError)):
        inspect_state(w.repository.db, tmp_path)
    assert before == sorted(p.as_posix() for p in tmp_path.rglob("*"))
    with pytest.raises((ValueError, KeyError)):
        create_backup(w.repository.db, tmp_path, tmp_path / "bad-backup.json")
    assert not (tmp_path / "bad-backup.json").exists()
    w.repository.db.close()


def test_restore_failure_cleans_directories_and_allows_retry(tmp_path, manifest, monkeypatch):
    w, _ = synthetic_project(tmp_path, manifest)
    artifact = tmp_path / "backup.json"
    create_backup(w.repository.db, tmp_path, artifact)
    target = tmp_path / "restored"
    target.mkdir()
    db = Database.sqlite(target / "projects.sqlite")
    db.initialize()
    original_open = Path.open
    count = 0

    def interrupted(path, mode="r", *args, **kwargs):
        nonlocal count
        if mode == "xb":
            count += 1
            if count == 2:
                raise OSError("Synthetic interrupted write")
        return original_open(path, mode, *args, **kwargs)

    with monkeypatch.context() as change:
        change.setattr(Path, "open", interrupted)
        with pytest.raises(ValueError, match="NO_MERGE"):
            restore_backup(db, target, artifact)
    assert not (target / "originals").exists()
    assert db.execute("SELECT 1 FROM projects").fetchone() is None
    restore_backup(db, target, artifact)
    inspect_state(db, target)
    db.close()
    w.repository.db.close()


def test_version_zero_foreign_projects_rejected_without_ddl():
    db = Database.sqlite()
    db.execute("CREATE TABLE projects (foreign_payload TEXT)")
    with pytest.raises(ValueError, match="UNVERSIONED"):
        db.initialize()
    assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == [
        ("projects",)
    ]
    db.close()


def test_verification_change_and_upgrade_do_not_count_as_scientific_detection():
    project = synthetic()[0][0]
    original = Observation(judgments=(Judgment(key="rating:8", state="assessed", value=5),))
    checked = original.model_copy(
        update={
            "judgments": (
                original.judgments[0].model_copy(update={"verification": Verification.SUPPORTED}),
            )
        }
    )
    detect = BenchmarkExpectation(
        feature=Feature.MEASURES, behavior="detect", judgment="rating:8", reference_variant="intact"
    )
    result = compare(checked, (detect,), {"intact": original}, project).metrics[0]
    assert result.detection.numerator == 0 and result.verification_change.numerator == 1
    higher = Observation(judgments=(Judgment(key="rating:8", state="assessed", value=7),))
    downgrade = detect.model_copy(update={"behavior": "downgrade", "direction": "lower"})
    assert (
        compare(higher, (downgrade,), {"intact": original}, project).metrics[0].detection.numerator
        == 0
    )


def test_confident_null_does_not_receive_withholding_credit():
    observed = Observation(judgments=(Judgment(key="rating:8", state="assessed"),))
    expectation = BenchmarkExpectation(
        feature=Feature.MEASURES, behavior="withhold", judgment="rating:8"
    )
    assert (
        compare(observed, (expectation,), {}, synthetic()[0][0]).metrics[0].withholding.numerator
        == 0
    )


def test_interrupted_reservation_report_survives_reopen(tmp_path):
    store = AdminStore(tmp_path)
    key = "0" * 64
    assert store.claim(key, "synthetic-reservation")
    report = AdminStore(tmp_path).reservation_report(key)
    assert report.status == "INTERRUPTED_UNCERTAIN" and not report.retry_allowed
    assert list((tmp_path / "annotations").glob("*.json"))


def test_v5_non_explain_criteria_are_explicitly_inapplicable(packet):
    _, _, task = packet
    project = task.context.project.model_copy(update={"route": "TEST"})
    context = task.context.model_copy(update={"project": project})
    task = task.model_copy(update={"context": context, "policy_version": "5"})
    contract = policy_contract(task)
    assert all(str(d) not in contract["dimensions"] for d in range(1, 8))
    assert not any(r["id"] == "NO-ADVANCE" for r in contract["semantic_rules"])
    assert "route_questions" not in policy_contract(task.model_copy(update={"dimensions": (4, 5)}))


def test_postgres_and_sqlite_backup_restore_parity(store, tmp_path):
    repo, _, scope = store
    artifact = tmp_path / "parity.json"
    create_backup(repo.db, tmp_path, artifact)
    target = tmp_path / "target"
    target.mkdir()
    if repo.db.dialect == "postgres":
        schema = "rdw_restore_parity"
        repo.db.execute(f"CREATE SCHEMA {schema}")
        current = repo.db.execute("SHOW search_path").fetchone()[0]
        repo.db.execute(f"SET search_path TO {schema}")
        target_db = repo.db
    else:
        target_db = Database.sqlite(target / "projects.sqlite")
    try:
        target_db.initialize()
        restore_backup(target_db, target, artifact)
        assert target_db.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 1
        inspect_state(target_db, target)
    finally:
        if repo.db.dialect == "postgres":
            repo.db.execute(f"SET search_path TO {current}")
            repo.db.execute(f"DROP SCHEMA {schema} CASCADE")
        else:
            target_db.close()


@pytest.mark.parametrize("route", ("EXPLAIN", "ESTABLISH", "TEST"))
@pytest.mark.parametrize(
    "stage", ("EARLY IDEA", "DISCOVERY PROPOSAL", "SPECIFIED STUDY PROPOSAL", "COMPLETED STUDY")
)
def test_route_stage_contract_matrix(packet, route, stage):
    _, _, task = packet
    project = task.context.project.model_copy(update={"route": route, "stage": stage})
    task = task.model_copy(
        update={
            "context": task.context.model_copy(update={"project": project}),
            "policy_version": "5",
        }
    )
    payload = policy_contract(task)
    if route != "EXPLAIN":
        assert "route_questions" in payload
        assert not any(r["id"] == "NO-ADVANCE" for r in payload["semantic_rules"])
    elif stage in ("EARLY IDEA", "DISCOVERY PROPOSAL"):
        assert set(payload["route_questions"]) == {
            "knowledge_need",
            "increment_over_existing_knowledge",
            "scope_and_precision",
            "capacity_to_learn",
            "evidence_strategy",
            "next_use",
        }
    else:
        assert "route_questions" not in payload
    assert "route_questions" not in policy_contract(task.model_copy(update={"dimensions": (9,)}))


def test_restoration_requires_actual_degradation_and_recovers():
    intact = Observation(judgments=(Judgment(key="rating:8", state="assessed", value=7),))
    degraded = Observation(judgments=(Judgment(key="rating:8", state="assessed", value=3),))
    expectation = BenchmarkExpectation(
        feature=Feature.MEASURES,
        behavior="restore",
        judgment="rating:8",
        reference_variant="intact",
        degraded_reference="degraded",
    )
    refs = {"intact": intact, "degraded": degraded}
    project = synthetic()[0][0]
    assert compare(intact, (expectation,), refs, project).metrics[0].restoration.numerator == 1
    assert compare(degraded, (expectation,), refs, project).metrics[0].restoration.numerator == 0
    assert (
        compare(intact, (expectation,), {"intact": intact, "degraded": intact}, project)
        .metrics[0]
        .restoration.numerator
        == 0
    )


def test_backup_excludes_temporary_evaluator_scratch(tmp_path, manifest):
    w, _ = synthetic_project(tmp_path, manifest)
    scratch = tmp_path / "benchmarks/evaluator/arbitrary-scratch"
    scratch.mkdir(parents=True)
    (scratch / "project.sqlite").write_bytes(b"synthetic scratch")
    (tmp_path / "provider-receipts").mkdir()
    (tmp_path / "provider-receipts/incomplete.tmp").write_bytes(b"incomplete")
    artifact = tmp_path / "backup.json"
    create_backup(w.repository.db, tmp_path, artifact)
    assert not any(
        "scratch" in f["path"] or f["path"].endswith(".tmp")
        for f in json.loads(artifact.read_text(encoding="utf-8"))["backup"]["files"]
    )
    w.repository.db.close()


def test_sqlite_postgres_runmanager_mock_provider_lifecycle(store, tmp_path, manifest, monkeypatch):
    import os
    import time

    from domain.sources import SourceRecord
    from persistence.repository import Repository
    from services.runs import RunManager
    from services.sources import SourceService
    from services.workbench import Workbench

    repo, sources, scope = store
    sources.paste(
        scope,
        SourceRecord(
            document_id="synthetic-draft",
            workspace_id=scope.workspace_id,
            project_id=scope.project_id,
            title="Original synthetic question",
            source_kind="pasted_original",
            role="project_draft",
            media_type="text/plain",
            rights_declaration="Authorized synthetic mock processing",
        ),
        "Synthetic question about an original fictional intervention; no real data.",
    )
    repo.set_admission(scope, "synthetic-draft", 1, True)
    path = (
        repo.db.execute("PRAGMA database_list").fetchone()[2]
        if repo.db.dialect == "sqlite"
        else None
    )
    schema = (
        repo.db.execute("SHOW search_path").fetchone()[0] if repo.db.dialect == "postgres" else None
    )

    def factory():
        db = (
            Database.sqlite(path)
            if path
            else Database.postgres(os.environ["RDW_TEST_POSTGRES_DSN"])
        )
        if schema:
            db.execute(f"SET search_path TO {schema}")
        repository = Repository(db)
        model, checker, _ = adapter(monkeypatch)
        model.receipt_sink = lambda receipt: write_provider_receipt(tmp_path / "receipts", receipt)
        workbench = Workbench(
            repository, SourceService(repository, sources.originals), manifest, model, checker
        )
        workbench.actor, workbench.workspace = scope.actor_id, scope.workspace_id
        return workbench

    manager = RunManager(tmp_path / "runs", factory)
    run = manager.submit(scope.project_id, 1)
    for _ in range(200):
        current = manager.get(scope.project_id, run.run_id)
        if current.state in ("succeeded", "failed"):
            break
        time.sleep(0.01)
    assert current.state == "succeeded", current.model_dump_json()
    assert current.provider_run and len(current.provider_run.calls) == 2
    assert len(list((tmp_path / "receipts").glob("*.call-*.json"))) == 2
    manager.close()
    restarted = RunManager(tmp_path / "runs", factory)
    assert restarted.get(scope.project_id, run.run_id).snapshot_id == current.snapshot_id
    restarted.close()


def test_reported_numeric_claim_without_existing_grounding_is_rejected():
    with pytest.raises(ValueError, match="grounding"):
        WorkspaceProposal.model_validate(
            dict(
                record=dict(
                    workspace="Study",
                    title="Synthetic",
                    fields=[
                        dict(
                            key="analysis",
                            text="Reported synthetic coefficient 0.7 in 400 cases",
                            claim_kind="reported_result",
                            origin="model_inference",
                        )
                    ],
                ),
                reason="Ungrounded",
                limitations=["Synthetic only"],
            )
        )


def test_changed_claim_cannot_evade_staleness_as_wording_only(workspace_client):
    client, _, view = workspace_client
    view = save(client, view, "Study", {"claim": "The synthetic intervention has no effect"})
    obj = view["project"]["objects"][-1]
    record = obj["payload"]
    record["fields"][0]["text"] = "The synthetic intervention has an effect"
    response = client.post(
        "/api/projects/" + view["project"]["project_id"] + "/records",
        json=dict(
            expected_revision=view["project"]["revision"],
            object_id=obj["object_id"],
            record=record,
            change="wording",
        ),
    )
    assert response.status_code == 422
