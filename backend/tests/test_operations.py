import json
import logging
import socket
import time

import pytest
from fastapi.testclient import TestClient
from test_application import add, create, service
from test_persistence import store as store

from api.app import create_app
from domain.application import EditProject, RunHandle
from domain.models import Route
from persistence.database import Database
from persistence.repository import Conflict, Repository
from services.backup import create_backup, restore_backup
from services.configuration import LocalConfiguration
from services.pilot import seed
from services.portability import import_project
from services.runs import RunManager


def environment(monkeypatch, tmp_path):
    monkeypatch.setenv("RDW_RUNTIME_ROOT", str(tmp_path / "pilot"))
    monkeypatch.setenv("RDW_DATABASE_MODE", "local-sqlite")
    monkeypatch.setenv("RDW_PROVIDER", "fake")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.mark.parametrize(
    "case,code",
    (
        ("database", "MISSING_POSTGRES"),
        ("credential", "BLOCKED_CREDENTIAL"),
        ("provider", "INVALID_PROVIDER"),
        ("root", "MISSING_PRIVATE"),
        ("mode", "UNSUPPORTED_DATABASE"),
    ),
)
def test_startup_failures_clear_no_fallback(tmp_path, monkeypatch, case, code):
    environment(monkeypatch, tmp_path)
    if case == "database":
        monkeypatch.setenv("RDW_DATABASE_MODE", "postgres")
        monkeypatch.delenv("RDW_POSTGRES_DSN", raising=False)
    elif case == "credential":
        monkeypatch.setenv("RDW_PROVIDER", "openai")
    elif case == "provider":
        monkeypatch.setenv("RDW_PROVIDER", "unsupported")
    elif case == "root":
        monkeypatch.delenv("RDW_RUNTIME_ROOT")
    else:
        monkeypatch.setenv("RDW_DATABASE_MODE", "unsupported")
    with pytest.raises(ValueError, match=code):
        LocalConfiguration.environment()


def test_startup_storage_failure_and_safe_status(tmp_path, monkeypatch):
    environment(monkeypatch, tmp_path)
    (tmp_path / "pilot").write_text("synthetic obstruction", encoding="utf-8")
    with pytest.raises(ValueError, match="STORAGE_UNAVAILABLE"):
        LocalConfiguration.environment()
    config = LocalConfiguration.environment(probe_storage=False)
    assert "DSN" not in json.dumps(config.status()) and "api_key" not in json.dumps(config.status())


def test_restart_offline_source_revision_history_unchanged(tmp_path, monkeypatch, caplog):
    environment(monkeypatch, tmp_path)
    monkeypatch.setattr(
        socket, "create_connection", lambda *a, **k: pytest.fail("Unexpected network")
    )
    caplog.set_level(logging.INFO)
    with TestClient(create_app()) as client:
        view = add(client, create(client))
        pid = view["project"]["project_id"]
        response = client.post(
            f"/api/projects/{pid}/evaluations",
            json={"expected_revision": view["project"]["revision"]},
        )
        assert response.status_code == 201
        review = response.json()
        sid = review["snapshot"]["snapshot_id"]
        before = client.get(f"/api/projects/{pid}/exports/json").text
        assert "original_storage_reference" not in before
        client.patch(
            f"/api/projects/{pid}",
            json={
                "expected_revision": view["project"]["revision"],
                "idea": "Synthetic consequential revision.",
            },
        )
        history = client.get(f"/api/projects/{pid}/history").json()
    with TestClient(create_app()) as restarted:
        assert restarted.get(f"/api/projects/{pid}/history").json() == history
        historical = restarted.get(f"/api/projects/{pid}/reviews/{sid}").json()
        assert historical["stale"] is True and historical["snapshot"] == review["snapshot"]
        assert historical["policy"] == review["policy"]
    assert "Synthetic consequential revision" not in caplog.text


def test_migration_repeat_upgrade_and_unknown_schema(store):
    repo, _, scope = store
    before = repo.export(scope, True)
    repo.db.execute("DELETE FROM schema_versions WHERE version=2")
    assert repo.db.schema_version() == 1
    repo.db.initialize()
    repo.db.initialize()
    assert repo.db.schema_version() == 2 and repo.export(scope, True) == before
    repo.db.execute("INSERT INTO schema_versions VALUES(99)")
    with pytest.raises(ValueError, match="INCOMPATIBLE"):
        repo.db.initialize()
    assert repo.export(scope, True) == before


def synthetic_project(tmp_path, manifest):
    w = service(tmp_path, manifest)
    with TestClient(create_app(w)) as client:
        view = add(client, create(client))
    pid = view["project"]["project_id"]
    w.run(pid, view["project"]["revision"])
    w.edit(
        pid,
        EditProject(
            expected_revision=view["project"]["revision"], idea="Synthetic revised dependency."
        ),
    )
    return w, pid


def test_private_backup_restores_all_history_originals_and_benchmark(
    tmp_path, manifest, monkeypatch
):
    w, pid = synthetic_project(tmp_path, manifest)
    from benchmarks.fixtures import synthetic
    from benchmarks.store import AdminStore
    from benchmarks.variants import freeze

    projects, _ = synthetic()
    for folder, version in (("benchmarks", "v1"), ("benchmarks/admin", "cli-v1")):
        store = AdminStore(tmp_path / folder)
        frozen = freeze(projects, version)
        store.freeze(frozen)
        for project in projects:
            store.import_project(project, frozen)
    before = w.repository.export(w.scope(pid), True)
    artifact = tmp_path / "backup.json"
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-credential-not-in-data")
    create_backup(w.repository.db, tmp_path, artifact)
    assert "synthetic-credential-not-in-data" not in artifact.read_text(encoding="utf-8")
    target = tmp_path / "restored"
    target.mkdir()
    db = Database.sqlite(target / "projects.sqlite")
    db.initialize()
    restore_backup(db, target, artifact)
    repo = Repository(db)
    assert repo.export(w.scope(pid), True) == before
    assert sorted(p.name for p in (target / "originals").iterdir()) == sorted(
        p.name for p in (tmp_path / "originals").iterdir()
    )
    assert (target / "benchmarks/splits").exists()
    assert (target / "benchmarks/admin/splits").exists()
    with pytest.raises(ValueError, match="EMPTY"):
        restore_backup(db, target, artifact)
    w.repository.db.close()
    db.close()


@pytest.mark.parametrize("fault", ("corrupt", "version", "path"))
def test_backup_rejects_bad_artifacts_atomically(tmp_path, manifest, fault):
    w, _ = synthetic_project(tmp_path, manifest)
    artifact = tmp_path / "backup.json"
    create_backup(w.repository.db, tmp_path, artifact)
    envelope = json.loads(artifact.read_text(encoding="utf-8"))
    if fault == "version":
        envelope["backup"]["format_version"] = 99
    elif fault == "path":
        envelope["backup"]["files"][0]["path"] = "../escape"
    else:
        envelope["sha256"] = "0" * 64
    artifact.write_text(json.dumps(envelope), encoding="utf-8")
    target = tmp_path / "restored"
    target.mkdir()
    db = Database.sqlite(target / "projects.sqlite")
    db.initialize()
    with pytest.raises(ValueError, match="CORRUPT"):
        restore_backup(db, target, artifact)
    assert db.execute("SELECT 1 FROM workspaces").fetchone() is None
    db.close()
    w.repository.db.close()


def test_portable_export_import_preserves_state_without_file_authority(tmp_path, manifest):
    w, pid = synthetic_project(tmp_path, manifest)
    export = w.export(pid, "json")
    target = tmp_path / "imported"
    target.mkdir()
    other = service(target, manifest)
    assert import_project(other, export) == pid
    source = w.bundle(pid)
    imported = other.bundle(pid)
    assert all(o.imported for p in imported.revisions for o in p.objects)
    assert (
        tuple(
            p.model_copy(
                update={
                    "objects": tuple(o.model_copy(update={"imported": False}) for o in p.objects)
                }
            )
            for p in imported.revisions
        )
        == source.revisions
    )
    assert len(source.snapshots) == len(imported.snapshots)
    assert imported.snapshots[0].policy_result == source.snapshots[0].policy_result
    assert imported.snapshots[0].snapshot.snapshot_id == source.snapshots[0].snapshot.snapshot_id
    assert all(v.original.storage_key is None and v.original.external for v in imported.versions)
    assert other.review(pid, imported.snapshots[0].snapshot.snapshot_id)["stale"] is True
    assert "original_storage_reference" not in other.export(pid, "json")
    legacy = json.loads(export)
    del legacy["import_bundle"]
    from services.portability import portable_bundle

    assert (
        portable_bundle(json.dumps(legacy)).snapshots[0].snapshot.snapshot_id
        == imported.snapshots[0].snapshot.snapshot_id
    )
    with pytest.raises(Conflict):
        import_project(other, export)
    w.repository.db.close()
    other.repository.db.close()


def test_import_provenance_escalation_rejected(tmp_path, manifest):
    w, pid = synthetic_project(tmp_path, manifest)
    data = json.loads(w.repository.export(w.scope(pid), True))
    data["revisions"][1]["objects"][0]["origin"] = "document_extraction"
    target = tmp_path / "target"
    target.mkdir()
    other = service(target, manifest)
    with pytest.raises(ValueError, match="authority"):
        other.repository.import_bundle(other.scope(pid), json.dumps(data))
    assert other.repository.db.execute("SELECT 1 FROM projects").fetchone() is None
    w.repository.db.close()
    other.repository.db.close()


def wait(manager, pid, rid):
    for _ in range(200):
        result = manager.get(pid, rid)
        if result.state in ("succeeded", "failed"):
            return result
        time.sleep(0.01)
    pytest.fail("Synthetic run did not terminate")


def test_duplicate_run_terminal_immutable_and_restart_reuses_result(tmp_path, manifest, caplog):
    w, pid = synthetic_project(tmp_path, manifest)
    revision = w.repository.project(w.scope(pid)).revision

    def factory():
        return service(tmp_path, manifest)

    caplog.set_level(logging.INFO, logger="rdw.operations")
    manager = RunManager(tmp_path / "runs", factory)
    first = manager.submit(pid, revision)
    second = manager.submit(pid, revision)
    assert first.run_id == second.run_id
    result = wait(manager, pid, first.run_id)
    assert result.state == "succeeded" and result.finished_at and result.duration_seconds >= 0
    with pytest.raises(ValueError, match="immutable"):
        manager.write(result.model_copy(update={"state": "failed"}))
    manager.close()
    restarted = RunManager(tmp_path / "runs", factory)
    assert restarted.submit(pid, revision).run_id == first.run_id
    restarted.close()
    w.repository.db.close()
    assert "Synthetic revised dependency" not in caplog.text and "run_transition" in caplog.text


def test_crash_after_publication_reconciles_without_provider_replay(
    tmp_path, manifest, monkeypatch
):
    w, pid = synthetic_project(tmp_path, manifest)
    revision = w.repository.project(w.scope(pid)).revision

    def factory():
        return service(tmp_path, manifest)

    manager = RunManager(tmp_path / "runs", factory)
    run = RunHandle(
        run_id="b" * 32,
        project_id=pid,
        expected_revision=revision,
        request_key="c" * 64,
        state="queued",
    )
    manager.write(run)
    write = manager.write

    def crash(value):
        if value.state == "succeeded":
            raise OSError("Synthetic process interruption after publication")
        write(value)

    monkeypatch.setattr(manager, "write", crash)
    with pytest.raises(OSError):
        manager.execute(run, ())
    manager.close()
    restarted = RunManager(tmp_path / "runs", factory)
    recovered = restarted.get(pid, run.run_id)
    assert recovered.state == "succeeded" and recovered.snapshot_id
    assert len([s for s in w.bundle(pid).snapshots if s.operation_id == run.run_id]) == 1
    restarted.close()
    w.repository.db.close()


def test_frozen_revision_conflict_and_two_edits_no_lost_update(tmp_path, manifest):
    w, pid = synthetic_project(tmp_path, manifest)
    revision = w.repository.project(w.scope(pid)).revision
    from model_adapters.fake import FakeModel

    class Racing(FakeModel):
        def assess(self, task):
            w.edit(pid, EditProject(expected_revision=revision, idea="Synthetic concurrent edit."))
            return super().assess(task)

    w.adapter = Racing()
    snapshots = w.bundle(pid).snapshots
    with pytest.raises(Conflict):
        w.run(pid, revision)
    assert w.bundle(pid).snapshots == snapshots
    with pytest.raises(Conflict):
        w.edit(pid, EditProject(expected_revision=revision, idea="Synthetic losing edit."))
    assert w.repository.project(w.scope(pid)).revision == revision + 1
    w.repository.db.close()


def test_scenario_pack_loads_all_routes_and_stale_history(tmp_path, manifest):
    w = service(tmp_path, manifest)
    identifiers = seed(w)
    assert len(identifiers) == 9
    assert {w.repository.project(w.scope(p)).route for p in identifiers} == set(Route)
    stale = identifiers[7]
    assert w.review(stale, w.bundle(stale).snapshots[0].snapshot.snapshot_id)["stale"] is True
    assert (tmp_path / "benchmarks/splits").exists()
    with pytest.raises(ValueError, match="EMPTY"):
        seed(w)
    w.repository.db.close()


def test_actual_parallel_edits_preserve_one_head(tmp_path, manifest):
    import sqlite3
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    w, pid = synthetic_project(tmp_path, manifest)
    revision = w.repository.project(w.scope(pid)).revision
    workers = [service(tmp_path, manifest), service(tmp_path, manifest)]
    barrier = Barrier(2)

    def edit(index):
        barrier.wait(timeout=5)
        try:
            workers[index].edit(
                pid,
                EditProject(
                    expected_revision=revision, idea="Synthetic parallel edit " + str(index)
                ),
            )
            return "saved"
        except (Conflict, sqlite3.OperationalError):
            return "conflict_or_busy"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(edit, (0, 1)))
    assert results.count("saved") == 1
    assert w.repository.project(w.scope(pid)).revision == revision + 1
    assert len(w.bundle(pid).revisions) == revision + 1
    for worker in workers:
        worker.repository.db.close()
    w.repository.db.close()


def test_source_change_and_targeted_recheck_race_keep_history(tmp_path, manifest):
    from domain.application import AddSource
    from model_adapters.fake import FakeModel
    from services.research import ResearchService

    w, pid = synthetic_project(tmp_path, manifest)
    revision = w.repository.project(w.scope(pid)).revision
    bundle = w.bundle(pid)
    original = bundle.snapshots[0]
    literature = next(s for s in bundle.sources if s.role == "literature")

    class SourceRace(FakeModel):
        def assess(self, task):
            assert task.dimensions == (4, 5)
            ResearchService(w).source_version(
                pid,
                literature.document_id,
                AddSource(
                    expected_revision=revision,
                    title="Synthetic source",
                    attribution="Fictional source",
                    text="Synthetic changed source with contrary claim.",
                    authorized=True,
                    admitted=True,
                ),
            )
            return super().assess(task)

    w.adapter = SourceRace()
    with pytest.raises(Conflict):
        w.run(pid, revision, (4, 5), "Argument")
    assert w.bundle(pid).snapshots[0] == original
    assert (
        w.repository.version(w.scope(pid), literature.document_id, 1).text
        != w.repository.version(w.scope(pid), literature.document_id, 2).text
    )
    w.repository.db.close()


def test_superseded_suggestion_acceptance_and_import_role_rejected(tmp_path, manifest):
    from domain.research import DecisionRequest
    from services.research import ResearchService

    w, pid = synthetic_project(tmp_path, manifest)
    project = w.repository.project(w.scope(pid))
    proposal = project.objects[0]
    with pytest.raises(Conflict):
        ResearchService(w).decide(
            pid,
            proposal.object_id,
            DecisionRequest(expected_revision=project.revision - 1, action="accepted"),
        )
    data = json.loads(w.repository.export(w.scope(pid), True))
    data["versions"][0]["document"]["role"] = (
        "literature" if data["versions"][0]["document"]["role"] != "literature" else "project_draft"
    )
    target = tmp_path / "target"
    target.mkdir()
    other = service(target, manifest)
    with pytest.raises(ValueError, match="role"):
        other.repository.import_bundle(other.scope(pid), json.dumps(data))
    assert other.repository.db.execute("SELECT 1 FROM projects").fetchone() is None
    other.repository.db.close()
    w.repository.db.close()


def test_navigation_and_request_errors_do_not_call_provider_or_echo_sources(tmp_path, manifest):
    from model_adapters.fake import FakeModel

    class Counter(FakeModel):
        calls = 0

        def assess(self, task):
            self.calls += 1
            return super().assess(task)

        def interpret(self, task):
            self.calls += 1
            return super().interpret(task)

    model = Counter()
    w = service(tmp_path, manifest, model)
    with TestClient(create_app(w)) as client:
        view = add(client, create(client))
        pid = view["project"]["project_id"]
        model.calls = 0
        for _ in range(3):
            for path in (
                f"/api/projects/{pid}",
                f"/api/projects/{pid}/workspaces",
                f"/api/projects/{pid}/history",
                f"/api/projects/{pid}/exports/json",
            ):
                assert client.get(path).status_code == 200
        assert model.calls == 0
        response = client.post(
            f"/api/projects/{pid}/evaluations",
            json={"expected_revision": "synthetic-private-secret-input"},
        )
        assert response.status_code == 422
        assert (
            "synthetic-private-secret-input" not in response.text
            and "traceback" not in response.text.lower()
        )
    w.repository.db.close()


def test_failure_retry_is_explicit_and_failed_history_survives(tmp_path, manifest):
    from model_adapters.fake import FakeModel
    from model_adapters.runtime import ProviderFailure

    w, pid = synthetic_project(tmp_path, manifest)
    revision = w.repository.project(w.scope(pid)).revision

    class Timeout(FakeModel):
        def assess(self, task):
            raise ProviderFailure("TIMEOUT_UNCERTAIN")

    calls = []

    def factory():
        calls.append("factory")
        return service(tmp_path, manifest, Timeout())

    manager = RunManager(tmp_path / "runs", factory)
    run = manager.submit(pid, revision)
    failed = wait(manager, pid, run.run_id)
    assert failed.failure_kind == "timeout_uncertain"
    assert manager.submit(pid, revision).run_id == run.run_id and len(calls) == 1
    retry = manager.submit(pid, revision, retry_failed=True)
    assert retry.run_id != run.run_id
    wait(manager, pid, retry.run_id)
    assert manager.get(pid, run.run_id) == failed
    assert len(w.bundle(pid).snapshots) == 1
    manager.close()
    w.repository.db.close()


def test_health_checks_are_read_only_and_do_not_send_credentials(tmp_path, manifest, monkeypatch):
    from services.pilot import health

    w, pid = synthetic_project(tmp_path, manifest)
    before = w.repository.export(w.scope(pid), True)
    environment(monkeypatch, tmp_path)
    monkeypatch.setenv("RDW_RUNTIME_ROOT", str(tmp_path))
    from types import SimpleNamespace

    commands = []

    def run(command, **kwargs):
        commands.append(command)
        if "env" in kwargs:
            assert "OPENAI_API_KEY" not in kwargs["env"] and kwargs["env"]["RDW_PROVIDER"] == "fake"
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("services.pilot.subprocess.run", run)
    config = LocalConfiguration.environment()
    (tmp_path / "projects.sqlite").touch()
    # The test substitutes an existing synthetic store after the read-only existence preflight.
    monkeypatch.setattr(
        LocalConfiguration, "database", lambda self: Database.sqlite(tmp_path / "synthetic.sqlite")
    )
    report = health(config)
    assert set(report.values()) == {"PASS"} and len(commands) == 5
    assert w.repository.export(w.scope(pid), True) == before
    monkeypatch.setattr(
        "services.pilot.subprocess.run", lambda *a, **k: SimpleNamespace(returncode=1)
    )
    assert health(config)["contracts"] == "FAIL"
    w.repository.db.close()


def test_startup_rejects_missing_immutability_guard(store):
    repo, _, _ = store
    repo.db.execute(
        "DROP TRIGGER snapshots_immutable"
        + (" ON snapshots" if repo.db.dialect == "postgres" else "")
    )
    with pytest.raises(ValueError, match="INCOMPATIBLE"):
        repo.db.initialize()


def test_benchmark_atomic_artifact_and_category_boundary(tmp_path):
    from benchmarks.fixtures import synthetic
    from benchmarks.store import AdminStore
    from benchmarks.variants import freeze

    projects, _ = synthetic()
    store = AdminStore(tmp_path / "administrator")
    manifest = freeze(projects, "v1")
    store.freeze(manifest)
    with pytest.raises(FileExistsError):
        store.freeze(manifest)
    assert store.read("splits", "v1", type(manifest)) == manifest
    assert not list((tmp_path / "administrator").rglob("*.tmp"))
    with pytest.raises(ValueError):
        store._path("../escape", "synthetic")


def test_schema_declared_version_cannot_hide_missing_column(store):
    repo, _, _ = store
    repo.db.execute("ALTER TABLE snapshots DROP COLUMN digest")
    with pytest.raises(ValueError, match="INCOMPATIBLE"):
        repo.db.initialize()


def test_supported_large_text_packet_is_bounded_and_usable(tmp_path, manifest, record_property):
    from domain.application import AddSource, CreateProject

    w = service(tmp_path, manifest)
    started = time.monotonic()
    view = w.create(
        CreateProject(
            title="Synthetic size probe", idea="Synthetic handoff. " * 1000, authorized=True
        )
    )
    pid = view["project"]["project_id"]
    large = ("Synthetic fictional passage. " * 1800)[:50000]
    view = w.add_source(
        pid,
        AddSource(
            expected_revision=view["project"]["revision"],
            title="Synthetic large source",
            attribution="Fictional",
            text=large,
            authorized=True,
            admitted=True,
        ),
    )
    packet = w.context(pid)
    size = sum(len(p.text) for p in packet.passages)
    assert 50000 <= size <= 100000
    w.run(pid, view["project"]["revision"])
    duration = time.monotonic() - started
    record_property("synthetic_packet_characters", size)
    record_property("synthetic_local_seconds", round(duration, 3))
    # A generous operational ceiling catches pathological work, not scientific complexity.
    assert duration < 20
    w.repository.db.close()


@pytest.mark.parametrize(
    "serialized",
    ("[]", "null", '{"schema_version":"rdw-app-1"}', '{"schema_version":"unknown"}', "invalid"),
)
def test_malformed_portable_import_fails_safely(serialized):
    from services.portability import portable_bundle

    with pytest.raises(ValueError, match="INVALID_OR_INCOMPATIBLE"):
        portable_bundle(serialized)


def test_fake_targeted_api_stays_on_normal_boundary(tmp_path, manifest):
    w, pid = synthetic_project(tmp_path, manifest)
    revision = w.repository.project(w.scope(pid)).revision
    with TestClient(create_app(w)) as client:
        response = client.post(
            f"/api/projects/{pid}/evaluations/targeted",
            json={"expected_revision": revision, "dimensions": [4, 5]},
        )
        assert response.status_code == 200
        assert {r["dimension"] for r in response.json()["assessment"]["ratings"]} == {4, 5}
    w.repository.db.close()


def test_provider_receipts_publish_complete_and_remain_immutable(tmp_path):
    from domain.models import ProviderRun
    from services.runs import write_provider_receipt

    receipt = ProviderRun(
        run_id="d" * 32,
        status="SUCCEEDED",
        calls=(),
        max_calls=4,
        max_tokens=500000,
        output_limit=6000,
        reasoning_effort="low",
    )
    write_provider_receipt(tmp_path, receipt)
    write_provider_receipt(tmp_path, receipt)
    with pytest.raises(ValueError, match="immutable"):
        write_provider_receipt(tmp_path, receipt.model_copy(update={"status": "FAILED"}))
    assert (
        ProviderRun.model_validate_json(
            (tmp_path / (receipt.run_id + ".json")).read_text(encoding="utf-8")
        )
        == receipt
    )
    assert not list(tmp_path.glob("*.tmp"))
