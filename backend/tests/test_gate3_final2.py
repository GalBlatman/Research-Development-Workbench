"""Requirement-derived final audit repairs; synthetic fixtures and mocked provider only."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import make_assessment
from test_application import service
from test_benchmarks import configuration, runner
from test_gate3_benchmark import exchange
from test_gate3_final_metrics import execute, expectation, metric
from test_gate3_final_metrics import manifest as manifest
from test_operations import synthetic_project
from test_persistence import store as store
from test_provider import adapter
from test_workspaces import check, save
from test_workspaces import workspace_client as workspace_client

from benchmarks.evaluator import BlindEvaluator
from benchmarks.metrics import aggregate, compare
from benchmarks.store import AdminStore
from benchmarks.variants import construct, freeze, normalized_identity
from domain.benchmark import (
    BenchmarkPackage,
    Feature,
    InvalidCaseReport,
    Judgment,
    Mutation,
    Observation,
    ReservationReport,
    Split,
    Transformation,
)
from domain.models import DiagnosticAction, RouteItem, Stage, Verification
from domain.sources import SourceRole
from persistence.database import Database
from policy_engine.engine import evaluate
from services.backup import create_backup, inspect_state
from services.portability import import_project, portable_bundle

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("disposition", ("supported", "needs_revision", "unresolved"))
def test_scientific_abstention_independent_of_real_checker(
    tmp_path, monkeypatch, manifest, disposition
):
    observed = execute(tmp_path, monkeypatch, manifest, "WORKBENCH", disposition, kind="unresolved")
    j = next(j for j in observed.judgments if j.key == "statement:principal-obstacle")
    assert (
        j.scientific_state == "unresolved"
        and j.verification == disposition
        and j.checking_performed
    )
    e = expectation(
        acceptable_scientific_states=("unresolved",), acceptable_verification_states=(disposition,)
    )
    m = metric(observed, e)
    assert m.withholding.numerator == m.state.numerator == m.verification_state.numerator == 1
    wrong = "needs_revision" if disposition == "supported" else "supported"
    m = metric(observed, expectation(acceptable_verification_states=(wrong,)))
    assert m.withholding.numerator == 1 and m.verification_state.numerator == 0


@pytest.mark.parametrize("mode", ("WORKBENCH", "BASELINE"))
def test_ratings_findings_route_scientific_uncertainty_and_no_fake_checks(
    tmp_path, monkeypatch, manifest, mode
):
    def mutate(name, output):
        if name == "rdw_evaluation":
            output["assessment"]["findings"] = [
                {
                    "rule_id": "KNOWLEDGE-NEED",
                    "value": "UNKNOWN",
                    "reasoning": "Insufficient synthetic evidence",
                    "verification": "unresolved",
                    "source_refs": [],
                }
            ]
            output["assessment"]["route_assessment"] = [
                {
                    "item": "knowledge_need",
                    "status": "NOT INSPECTED",
                    "reason": "No inspected synthetic basis",
                    "verification": "unresolved",
                    "source_refs": [],
                }
            ]
        if name == "rdw_checking":
            for d in output["decisions"]:
                d["disposition"] = "unresolved"
        return output

    model, _, _ = adapter(monkeypatch, mutate)
    evaluator = BlindEvaluator(exchange().variants[0].packet, model, manifest, tmp_path / mode)
    try:
        output, _ = evaluator.run("WORKBENCH", "FULL")
        if mode == "BASELINE":
            evaluator.mode = "BASELINE"
            output.pop("checks")
        observed = evaluator.observe(output)
        for key in ("rating:8", "finding:KNOWLEDGE-NEED", "route:knowledge_need"):
            j = next(j for j in observed.judgments if j.key == key)
            e = expectation().model_copy(update={"judgment": key})
            assert metric(observed, e).withholding.numerator == 1
            if key == "rating:8" or mode == "BASELINE":
                assert not j.checking_performed and j.verification is None
            else:
                assert j.checking_performed and j.verification == "unresolved"
    finally:
        evaluator.close()
        model.close()


@pytest.mark.parametrize(
    "key,before,after,values,expected",
    (
        ("rating:8", "assessed", "assessed", (5, 7), (0, 1)),
        ("rating:8", "assessed", "assessed", (7, 5), (1, 1)),
        ("route:knowledge_need", "BLOCKING", "DEVELOPMENT NEEDED", (None, None), (0, 1)),
        ("route:knowledge_need", "ADEQUATE FOR STAGE", "DEVELOPMENT NEEDED", (None, None), (1, 1)),
        ("rating:8", "not_applicable", "pending", (None, None), (0, 0)),
    ),
)
def test_strict_ordered_downgrade(key, before, after, values, expected):
    old = Observation(judgments=(Judgment(key=key, state=before, value=values[0]),))
    new = Observation(judgments=(Judgment(key=key, state=after, value=values[1]),))
    e = expectation().model_copy(
        update={"judgment": key, "behavior": "downgrade", "reference_variant": "old"}
    )
    m = compare(new, (e,), {"old": old}, exchange().projects[0]).metrics[0].detection
    assert (m.numerator, m.denominator) == expected


@pytest.mark.parametrize(
    "constraints",
    (
        {"acceptable_states": ("proposed",)},
        {"acceptable_states": ("unresolved",), "acceptable_scientific_states": ("supported",)},
        {"acceptable_states": ("unresolved",), "forbidden_scientific_states": ("unresolved",)},
        {
            "acceptable_verification_states": (Verification.SUPPORTED,),
            "forbidden_verification_states": (Verification.SUPPORTED,),
        },
        {"behavior": "downgrade", "direction": "higher"},
        {"behavior": "downgrade", "judgment": "finding:KNOWLEDGE-NEED"},
        {"behavior": "downgrade", "judgment": "rating:8", "acceptable_states": ("pending",)},
        {"behavior": "unchanged", "direction": "lower"},
        {
            "behavior": "downgrade",
            "judgment": "route:knowledge_need",
            "acceptable_states": ("ADEQUATE FOR STAGE",),
        },
    ),
)
def test_impossible_expectations_rejected_before_freeze(constraints):
    e = expectation().model_copy(update=constraints)
    with pytest.raises(ValueError):
        e.validate_constraints()
    data = exchange().model_dump(mode="json")
    data["expectations"][0]["expectations"] = [e.model_dump(mode="json")]
    with pytest.raises(ValueError):
        BenchmarkPackage.model_validate(data)


def test_exact_execution_binding_precedes_adapter(tmp_path, manifest):
    r, projects, cases = runner(tmp_path, manifest)
    old = cases[0]
    p = old.project.model_copy(update={"version": "corrected-v2"})
    splits = freeze(
        tuple(p if x.benchmark_id == p.benchmark_id else x for x in projects), "split-v2"
    )
    r.store.freeze(splits)
    r.store.import_project(p, splits)
    r.splits = splits
    r.adapter_factory = lambda: pytest.fail("Provider must not be constructed for invalid lineage")
    from benchmarks.runner import Case

    with pytest.raises(ValueError, match="lineage"):
        r.execute(Case(p, old.variant, old.expectations), configuration())
    assert not list((r.store.root / "runs").glob("*.json"))


@pytest.mark.parametrize("fault", ("same_text", "metadata"))
def test_noop_or_metadata_scientific_degradation_rejected(tmp_path, fault):
    p = exchange().projects[0]
    b = next(b for b in p.source_package.blocks if Feature.MEASURES in b.features)
    replacement = b.model_copy(
        update={"block_id": "replacement", "metadata_only": fault == "metadata"}
    )
    m = Mutation(
        transformation=Transformation.DEGRADE,
        targets=(Feature.MEASURES,),
        replacements=(replacement,),
    )
    with pytest.raises(ValueError):
        construct(p, m, "invalid", exchange().manifest)
    data = exchange().model_dump(mode="json")
    v = next(
        v for v in data["variants"] if v["mutation"]["transformation"] == "CONTROLLED_DEGRADATION"
    )
    v["mutation"]["replacements"][0] = replacement.model_dump(mode="json")
    package = tmp_path / "bad.json"
    package.write_text(json.dumps(data), encoding="utf-8")
    command = [sys.executable, "-m", "benchmarks", "--package", str(package), "--validate-only"]
    result = subprocess.run(command, cwd=ROOT / "backend", capture_output=True, text=True)
    assert result.returncode != 0 and "Traceback" not in result.stderr


def test_missing_references_disappearance_and_action_annotations():
    p = exchange().projects[0]
    old = Observation(judgments=(Judgment(key="rating:8", state="assessed", value=5),))
    empty = Observation(judgments=())
    e = expectation().model_copy(
        update={
            "judgment": "rating:8",
            "behavior": "restore",
            "reference_variant": "old",
            "degraded_reference": "absent",
        }
    )
    assert compare(old, (e,), {"old": old}, p).metrics[0].restoration.denominator == 0
    e = e.model_copy(update={"behavior": "unchanged"})
    assert compare(empty, (e,), {"old": old}, p).metrics[0].invariance.denominator == 1
    assert compare(empty, (e,), {"old": old}, p).metrics[0].invariance.numerator == 0
    e = e.model_copy(update={"action_target": "synthetic-action"})
    assert compare(old, (e,), {}, p).metrics[0].action.denominator == 0


@pytest.mark.parametrize("surface", ("reorder", "whitespace", "unicode", "role", "rename"))
def test_normalized_duplicate_identity_prevents_relabel_split(tmp_path, surface):
    p = exchange().projects[0]
    if surface == "unicode":
        p = p.model_copy(
            update={
                "source_package": p.source_package.model_copy(
                    update={
                        "blocks": tuple(
                            b.model_copy(update={"text": b.text + " café"})
                            for b in p.source_package.blocks
                        )
                    }
                )
            }
        )
    admin = AdminStore(tmp_path / "admin")
    manifest = freeze((p,), "first")
    admin.freeze(manifest)
    admin.import_project(p, manifest)
    blocks = p.source_package.blocks
    if surface == "reorder":
        blocks = tuple(reversed(blocks))
    if surface == "whitespace":
        blocks = tuple(b.model_copy(update={"text": b.text + "  \n"}) for b in blocks)
    if surface == "unicode":
        blocks = tuple(
            b.model_copy(update={"text": b.text.replace("é", "e\u0301")}) for b in blocks
        )
    if surface == "role":
        blocks = tuple(b.model_copy(update={"role": SourceRole.LITERATURE}) for b in blocks)
    renamed = p.model_copy(
        update={
            "benchmark_id": "different-label",
            "split": Split.HELD_OUT,
            "source_package": p.source_package.model_copy(
                update={"package_id": "new-package", "blocks": blocks}
            ),
        }
    )
    assert normalized_identity(renamed) == normalized_identity(p)
    new = freeze((renamed,), "second")
    with pytest.raises(ValueError, match="relabeled"):
        admin.freeze(new)
        admin.import_project(renamed, new)


def test_explicit_paper_identity_correction_lineage(tmp_path):
    p = exchange().projects[0].model_copy(update={"paper_identity": "opaque-paper-1"})
    admin = AdminStore(tmp_path / "admin")
    first = freeze((p,), "first")
    admin.freeze(first)
    admin.import_project(p, first)
    corrected = p.model_copy(
        update={
            "version": "v2",
            "supersedes": p.version,
            "source_package": p.source_package.model_copy(
                update={
                    "version": "v2",
                    "blocks": tuple(
                        b.model_copy(update={"role": SourceRole.LITERATURE})
                        for b in p.source_package.blocks
                    ),
                }
            ),
        }
    )
    second = freeze((corrected,), "second")
    admin.freeze(second)
    admin.import_project(corrected, second)
    assert corrected.paper_identity == p.paper_identity and corrected.split == p.split
    with pytest.raises(ValueError):
        admin.freeze(freeze((corrected.model_copy(update={"split": Split.HELD_OUT}),), "third"))


def test_atomic_import_preflight_and_runtime_rollback(tmp_path, monkeypatch):
    package = exchange()
    admin = AdminStore(tmp_path / "admin")
    admin.preflight_import(package)
    assert not list(admin.root.rglob("*.json"))
    original = admin.write
    counter = 0

    def fail(category, identity, value):
        nonlocal counter
        counter += 1
        original(category, identity, value)
        if counter == 5:
            raise OSError("Synthetic disk failure after publication")

    monkeypatch.setattr(admin, "write", fail)
    with pytest.raises(OSError):
        admin.import_package(package)
    assert not list(admin.root.rglob("*.json"))
    monkeypatch.setattr(admin, "write", original)
    admin.import_package(package)
    before = {p: p.read_bytes() for p in admin.root.rglob("*.json")}
    changed = package.model_dump(mode="json")
    changed["manifest"]["version"] = "different"
    # A contradictory package or collision fails before any persistent write.
    with pytest.raises(ValueError):
        BenchmarkPackage.model_validate(changed)
    assert before == {p: p.read_bytes() for p in admin.root.rglob("*.json")}


@pytest.mark.parametrize(
    "placeholder",
    (
        "TBD",
        "T.B.D.",
        "(TBD)",
        '"TBD"',
        "TBD - TBD",
        "TODO",
        "To be determined.",
        "None.",
        "N / A",
        "-",
        "   ",
        "ＴＢＤ",
    ),
)
def test_mechanical_placeholder_normalization(placeholder):
    with pytest.raises(ValueError):
        DiagnosticAction(
            issue="Bounded synthetic uncertainty",
            task="Inspect the synthetic comparison",
            required_input=placeholder,
            deliverable="A contrast note",
            outcome_branches=("Retain if supported",),
        )
    from domain.research import WorkspaceProposal

    fields = {
        "task": "Inspect the synthetic contrast",
        "reason": "Resolve the bounded uncertainty",
        "judgment": "Uncertain contrast",
        "input": placeholder,
        "output": "A contrast table",
        "workspace": "Argument",
        "dependency": "The synthetic premise",
        "branches": "Retain if supported; revise otherwise",
    }
    with pytest.raises(ValueError):
        WorkspaceProposal.model_validate(
            {
                "record": {
                    "workspace": "Next Actions",
                    "title": "Synthetic action",
                    "fields": [
                        {"key": k, "text": v, "origin": "model_inference"}
                        for k, v in fields.items()
                    ],
                },
                "reason": "Resolve uncertainty",
                "limitations": ["Synthetic only"],
            }
        )


@pytest.mark.parametrize("route", ("ESTABLISH", "TEST"))
@pytest.mark.parametrize("stage", tuple(Stage))
@pytest.mark.parametrize("verification", ("supported", "unresolved"))
def test_blocking_stage_decisions(route, stage, verification, manifest):
    assessment = make_assessment(manifest, route=route, stage=stage)
    items = tuple(
        RouteItem(
            item=k,
            status="BLOCKING" if k == "knowledge_need" else "ADEQUATE FOR STAGE",
            reason="Synthetic typed stage disposition",
            verification=verification,
        )
        for k in manifest.route_items
    )
    result = evaluate(assessment.model_copy(update={"route_assessment": items}), manifest)
    expected = "FALSE" if verification == "supported" else "UNKNOWN"
    assert next(g for g in result.gates if g.name == "proposal_readiness").state == expected
    assert next(g for g in result.gates if g.name == "bounded_route_development").state == expected


def test_imported_anchor_support_demoted_and_provider_context_excludes_history(
    tmp_path, manifest, monkeypatch
):
    (tmp_path / "sender").mkdir()
    (tmp_path / "receiver").mkdir()
    sender, pid = synthetic_project(tmp_path / "sender", manifest)
    data = json.loads(sender.export(pid, "json"))
    anchor = data["import_bundle"]["anchors"][0]
    ref = {k: anchor[k] for k in ("document_id", "version", "anchor_id")}
    obj = data["import_bundle"]["revisions"][-1]["objects"][0]
    obj["support_dispositions"] = [
        {
            "target": "question",
            "disposition": "supported",
            "reason": "Imported self-asserted support",
            "source_refs": [ref],
        }
    ]
    receiver = service(tmp_path / "receiver", manifest)
    try:
        import_project(receiver, json.dumps(data))
        saved = receiver.repository.project(receiver.scope(pid)).objects[0]
        assert saved.support_dispositions[0].disposition == "unresolved"
        assert saved.imported_support_history[0].disposition == "supported"
        # New current text makes the project evaluable; old unavailable source references stay excluded.
        from domain.application import EditProject

        current = receiver.repository.project(receiver.scope(pid))
        receiver.edit(
            pid,
            EditProject(
                expected_revision=current.revision, idea="A new synthetic current description"
            ),
        )
        model, checker, requests = adapter(monkeypatch)
        receiver.adapter, receiver.verifier = model, checker
        current = receiver.repository.project(receiver.scope(pid))
        result = receiver.run(pid, current.revision)
        body = json.loads(
            next(r["input"] for r in requests if r["text"]["format"]["name"] == "rdw_evaluation")
        )
        project = body["context"]["project"]
        assert all(not o["imported_support_history"] for o in project["objects"])
        assert all(
            d["disposition"] != "supported"
            for o in project["objects"]
            for d in o["support_dispositions"]
        )
        assert result["exclusions"]
        model.close()
    finally:
        sender.repository.db.close()
        receiver.repository.db.close()


def test_cross_revision_generated_origin_cannot_be_laundered(tmp_path, manifest):
    w, pid = synthetic_project(tmp_path, manifest)
    data = json.loads(w.export(pid, "json"))
    obj = data["import_bundle"]["revisions"][-1]["objects"][0]
    obj.update(origin="user_text", generated_by_run_id=None, provider_run=None, operation_id=None)
    with pytest.raises(ValueError):
        portable_bundle(json.dumps(data))
    w.repository.db.close()


def test_anchor_deletion_blocks_health_and_backup(tmp_path, manifest):
    w, pid = synthetic_project(tmp_path, manifest)
    try:
        db = w.repository.db
        db.execute("DROP TRIGGER source_anchors_immutable_delete")
        db.execute("DELETE FROM source_anchors")
        db.execute(
            "CREATE TRIGGER source_anchors_immutable_delete BEFORE DELETE ON source_anchors BEGIN SELECT RAISE(ABORT,'immutable history'); END"
        )
        with pytest.raises(ValueError):
            inspect_state(db, tmp_path)
        with pytest.raises(ValueError):
            create_backup(db, tmp_path, tmp_path / "invalid-backup.json")
        assert not (tmp_path / "invalid-backup.json").exists()
    finally:
        w.repository.db.close()


def test_foreign_version_zero_database_refused():
    db = Database.sqlite()
    try:
        db.execute("CREATE TABLE unrelated(value TEXT)")
        with pytest.raises(ValueError, match="UNVERSIONED"):
            db.initialize()
        assert db.schema_version() == 0
    finally:
        db.close()


def test_failure_attempts_and_admin_annotations_remain_visible(tmp_path, manifest):
    r, _, cases = runner(tmp_path, manifest)
    original = r.adapter_factory
    r.adapter_factory = lambda: (_ for _ in ()).throw(ValueError("Synthetic failure"))
    failed = r.execute(cases[0], configuration())
    r.adapter_factory = original
    success = r.execute(cases[0], configuration(), rerun=True)
    annotations = (
        InvalidCaseReport(variant_id="bad", error_code="invalid"),
        ReservationReport(
            reservation_key="a" * 64, run_id="orphan", status="INTERRUPTED_UNCERTAIN"
        ),
    )
    report = aggregate((failed, success), annotations)
    mode = report["papers"][cases[0].project.benchmark_id]["WORKBENCH"]
    assert (
        mode["failed"] == 1
        and mode["final_successful_variants"] == 1
        and len(mode["attempts"]) == 2
    )
    assert report["invalid_cases"] == report["orphan_reservations"] == 1
    assert all(
        group["failed"] == 1 and len(group["attempts"]) == 2
        for group in mode["configurations"].values()
    )


def test_usefulness_consequential_edit_stales_brief_not_study(workspace_client):
    client, _, view = workspace_client
    view = save(
        client,
        view,
        "Usefulness",
        {"audience": "Fictional planners", "decision": "Choose handoff scheduling"},
    )
    brief = check(client, view, "Brief")
    study = check(client, view, "Study")
    view = save(
        client,
        view,
        "Usefulness",
        {"audience": "Fictional analysts", "decision": "Change resource allocation"},
    )
    root = "/api/projects/" + view["project"]["project_id"] + "/reviews/"
    assert client.get(root + brief["snapshot"]["snapshot_id"]).json()["stale"] is True
    assert client.get(root + study["snapshot"]["snapshot_id"]).json()["stale"] is False


def test_operator_cli_sqlite_postgres_health_backup_restore(
    store, tmp_path, manifest, monkeypatch, capsys
):
    from model_adapters.config import ProviderConfig
    from services import pilot
    from services.configuration import LocalConfiguration

    repo, _, _ = store
    original = repo.db
    runtime = tmp_path / "operator"
    runtime.mkdir()
    backup = tmp_path / "operator-backup.json"
    schemas = []
    if original.dialect == "postgres":
        schema = original.execute("SHOW search_path").fetchone()[0]

        def connect():
            db = Database.postgres(os.environ["RDW_TEST_POSTGRES_DSN"])
            db.execute(f"SET search_path TO {schema}")
            return db

        mode = "postgres"
    else:
        path = original.execute("PRAGMA database_list").fetchone()[2]
        # Health intentionally verifies existence before connecting.
        (runtime / "projects.sqlite").touch()

        def connect():
            return Database.sqlite(path)

        mode = "local-sqlite"
    config = LocalConfiguration(runtime, mode, ProviderConfig(provider="fake"))
    monkeypatch.setattr(
        LocalConfiguration, "environment", classmethod(lambda cls, **kwargs: config)
    )
    monkeypatch.setattr(LocalConfiguration, "database", lambda self: connect())
    monkeypatch.setattr(pilot.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0))

    def cli(*args):
        monkeypatch.setattr(sys, "argv", ["pilot", *args])
        pilot.main()
        return capsys.readouterr()

    assert "PASS migrate" in cli("migrate").out
    assert '"persisted_state_integrity": "PASS"' in cli("health").out
    assert "PASS backup" in cli("backup", "--file", str(backup)).out
    if original.dialect == "postgres":
        from uuid import uuid4

        target = "rdw_operator_" + uuid4().hex
        original.execute(f"CREATE SCHEMA {target}")
        schemas.append(target)
        schema = target
    else:
        path = tmp_path / "restored.sqlite"
    try:
        assert "PASS migrate" in cli("migrate").out
        assert "PASS restore" in cli("restore", "--file", str(backup)).out
        assert '"persisted_state_integrity": "PASS"' in cli("health").out
        monkeypatch.setattr(sys, "argv", ["pilot", "backup"])
        with pytest.raises(SystemExit):
            pilot.main()
        assert "FILE_ARGUMENT_REQUIRED" in capsys.readouterr().err
    finally:
        for name in schemas:
            original.execute(f"DROP SCHEMA {name} CASCADE")


@pytest.mark.parametrize("failure", ("invalid_output", "checking", "attachment"))
def test_usage_attached_to_failed_downstream_run(store, tmp_path, manifest, monkeypatch, failure):
    from domain.sources import SourceRecord
    from persistence.repository import Repository
    from services.runs import RunManager, write_provider_receipt
    from services.sources import SourceService
    from services.workbench import Workbench

    repo, sources, scope = store
    sources.paste(
        scope,
        SourceRecord(
            document_id="synthetic-paid-input",
            workspace_id=scope.workspace_id,
            project_id=scope.project_id,
            title="Synthetic",
            source_kind="pasted_original",
            role="project_draft",
            media_type="text/plain",
            rights_declaration="Synthetic authorized mock",
        ),
        "Synthetic original fictional handoff question.",
    )
    repo.set_admission(scope, "synthetic-paid-input", 1, True)
    path = (
        repo.db.execute("PRAGMA database_list").fetchone()[2]
        if repo.db.dialect == "sqlite"
        else None
    )
    schema = repo.db.execute("SHOW search_path").fetchone()[0] if not path else None

    def mutate(name, output):
        if failure == "invalid_output" and name == "rdw_evaluation":
            output["assessment"]["ratings"] = []
        if failure == "checking" and name == "rdw_checking":
            output["decisions"] = []
        return output

    def factory():
        db = (
            Database.sqlite(path)
            if path
            else Database.postgres(os.environ["RDW_TEST_POSTGRES_DSN"])
        )
        if schema:
            db.execute(f"SET search_path TO {schema}")
        repository = Repository(db)
        model, checker, _ = adapter(monkeypatch, mutate)
        model.receipt_sink = lambda receipt: write_provider_receipt(tmp_path / "receipts", receipt)
        if failure == "attachment":
            repository.save_snapshot = lambda *a, **k: (_ for _ in ()).throw(
                OSError("Synthetic attachment failure")
            )
        w = Workbench(
            repository, SourceService(repository, sources.originals), manifest, model, checker
        )
        w.actor, w.workspace = scope.actor_id, scope.workspace_id
        return w

    manager = RunManager(tmp_path / "runs", factory)
    try:
        submitted = manager.submit(scope.project_id, 1)
        for _ in range(300):
            current = manager.get(scope.project_id, submitted.run_id)
            if current.state == "failed":
                break
            time.sleep(0.01)
        assert current.state == "failed" and current.failure_kind
        assert current.provider_run and current.provider_run.status == "FAILED"
        assert current.provider_run.calls and all(
            c.input_tokens == 400 for c in current.provider_run.calls
        )
        terminal = [
            json.loads(p.read_text(encoding="utf-8"))
            for p in (tmp_path / "receipts").glob("*.json")
        ]
        assert any(
            r["status"] == "FAILED" and r["run_id"] == current.provider_run.run_id for r in terminal
        )
        assert not any(
            r["status"] == "SUCCEEDED" and r["run_id"] == current.provider_run.run_id
            for r in terminal
        )
    finally:
        manager.close()


def test_docs_only_external_json_builder_and_stored_runner(tmp_path):
    builder = ROOT / "backend/tests/external_json_builder.py"
    text = builder.read_text(encoding="utf-8")
    assert all(
        module not in text for module in ("from benchmarks", "from domain", "import pydantic")
    )
    package = tmp_path / "synthetic-external.json"
    result = subprocess.run(
        [
            sys.executable,
            str(builder),
            str(ROOT / "evals/benchmark-package-v1.schema.json"),
            str(package),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    output = tmp_path / "private-runtime"
    base = [sys.executable, "-m", "benchmarks"]
    for args in (
        ("--package", str(package), "--validate-only", "--output", str(output)),
        ("--package", str(package), "--output", str(output)),
        (
            "--execute-stored",
            "--split-version",
            "synthetic-external-splits-v1",
            "--output",
            str(output),
        ),
    ):
        result = subprocess.run(
            [*base, *args], cwd=ROOT / "backend", capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
    assert '"successful_cases": 1' in result.stdout
    assert len(list((output / "admin/runs").glob("*.json"))) == 1


def test_baseline_prompt_is_self_contained():
    prompt = (ROOT / "backend/prompts/baseline-v3.md").read_text(encoding="utf-8")
    assert "evaluation-v3" not in prompt
    for required in ("inspected_material", "UNRESOLVED", "TARGETED", "FULL", "source_refs"):
        assert required.casefold() in prompt.casefold()


def test_identical_restoration_reference_cli_rejected(tmp_path):
    data = exchange().model_dump(mode="json")
    intact = next(v for v in data["variants"] if v["mutation"]["transformation"] == "INTACT_BLIND")
    degraded = next(
        v for v in data["variants"] if v["mutation"]["transformation"] == "CONTROLLED_DEGRADATION"
    )
    intact["packet"] = degraded["packet"]
    path = tmp_path / "synthetic-invalid-restoration.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "benchmarks", "--package", str(path), "--validate-only"],
        cwd=ROOT / "backend",
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and "Traceback" not in result.stderr


@pytest.mark.parametrize("route", ("EXPLAIN", "ESTABLISH", "TEST"))
def test_actual_mock_provider_task_route_contract(tmp_path, manifest, monkeypatch, route):
    from fastapi.testclient import TestClient
    from test_application import create

    from api.app import create_app

    w = service(tmp_path, manifest)
    with TestClient(create_app(w)) as client:
        view = create(client, idea="Synthetic unresolved original handoff question.", route=route)
    model, checker, requests = adapter(monkeypatch)
    w.adapter, w.verifier = model, checker
    try:
        w.run(view["project"]["project_id"], view["project"]["revision"])
        body = next(r for r in requests if r["text"]["format"]["name"] == "rdw_evaluation")
        criteria = json.loads(body["input"])["criteria"]
        assert set(criteria["dimensions"]) == (
            {str(i) for i in range(1, 11)} if route == "EXPLAIN" else {"8", "9", "10"}
        )
        expected = json.loads(
            (ROOT / "backend/prompts/route-questions-v1.json").read_text(encoding="utf-8")
        )["ESTABLISH" if route == "EXPLAIN" else route]
        questions = criteria["route_questions"]
        assert list(questions.values()) == list(expected.values()) and len(questions) == 6
        if route == "EXPLAIN":
            assert set(questions) == {
                "knowledge_need",
                "increment_over_existing_knowledge",
                "scope_and_precision",
                "capacity_to_learn",
                "evidence_strategy",
                "next_use",
            }
        if route != "EXPLAIN":

            def mutate(name, output):
                if name == "rdw_evaluation":
                    output["assessment"]["ratings"].append(
                        {
                            **output["assessment"]["ratings"][0],
                            "dimension": 1,
                            "rating": 5,
                            "status": "assessed",
                            "inspected_material": [
                                p.anchor.anchor_id
                                for p in w.context(view["project"]["project_id"]).passages
                            ],
                        }
                    )
                return output

            invalid, checking, _ = adapter(monkeypatch, mutate)
            w.adapter, w.verifier = invalid, checking
            with pytest.raises(ValueError, match="INAPPLICABLE_RATING"):
                w.run(view["project"]["project_id"], view["project"]["revision"])
            invalid.close()
    finally:
        model.close()
        w.repository.db.close()


def test_postgres_services_pilot_subprocess_cli_smoke(tmp_path):
    from uuid import uuid4

    from psycopg.conninfo import make_conninfo

    dsn = os.getenv("RDW_TEST_POSTGRES_DSN")
    if not dsn:
        if os.getenv("RDW_REQUIRE_POSTGRES") == "1":
            pytest.fail("PostgreSQL operator smoke is mandatory")
        pytest.skip("PostgreSQL operator CLI runs in mandatory CI")
    admin = Database.postgres(dsn)
    schemas = ["rdw_cli_" + uuid4().hex, "rdw_cli_" + uuid4().hex]
    for schema in schemas:
        admin.execute(f"CREATE SCHEMA {schema}")
    backup = tmp_path / "synthetic-cli-backup.json"
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    env.update(RDW_PROVIDER="fake", RDW_DATABASE_MODE="postgres")

    def run(schema, runtime, *args):
        env.update(
            RDW_POSTGRES_DSN=make_conninfo(dsn, options=f"-csearch_path={schema}"),
            RDW_RUNTIME_ROOT=str(runtime),
        )
        result = subprocess.run(
            [sys.executable, "-m", "services.pilot", *args],
            cwd=ROOT / "backend",
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "Traceback" not in result.stderr
        return result.stdout

    try:
        source = tmp_path / "cli-source"
        target = tmp_path / "cli-restored"
        assert "PASS migrate" in run(schemas[0], source, "migrate")
        assert '"scenario_projects": 9' in run(schemas[0], source, "seed")
        assert '"persisted_state_integrity": "PASS"' in run(schemas[0], source, "health")
        assert "PASS backup" in run(schemas[0], source, "backup", "--file", str(backup))
        assert "PASS migrate" in run(schemas[1], target, "migrate")
        assert "PASS restore" in run(schemas[1], target, "restore", "--file", str(backup))
        assert '"persisted_state_integrity": "PASS"' in run(schemas[1], target, "health")
    finally:
        for schema in schemas:
            admin.execute(f"DROP SCHEMA {schema} CASCADE")
        admin.close()


def test_cli_store_preflight_collisions_and_publication_path(tmp_path):
    from benchmarks.variants import content_hash
    from domain.benchmark import FrozenExpectations

    package = exchange()
    output = tmp_path / "private-store"
    admin = AdminStore(output / "admin")
    admin.import_package(package)
    project = package.projects[0]
    changed = project.model_copy(update={"neutral_identifier": "Synthetic changed annotation"})
    projects = tuple(
        changed if p.benchmark_id == changed.benchmark_id else p for p in package.projects
    )
    manifest = freeze(projects, "synthetic-collision-preflight")
    rebuilt = {}
    for v in package.variants:
        p = next(p for p in projects if p.benchmark_id == v.benchmark_id)
        rebuilt[v.variant_id] = construct(
            p, v.mutation, v.variant_id, manifest, rebuilt.get(v.mutation.parent_variant)
        )
    expectations = tuple(
        FrozenExpectations(
            variant_id=e.variant_id,
            variant_hash=content_hash(rebuilt[e.variant_id]),
            expectations=e.expectations,
        )
        for e in package.expectations
    )
    collision = BenchmarkPackage(
        manifest=manifest,
        projects=projects,
        variants=tuple(rebuilt.values()),
        expectations=expectations,
    )
    path = tmp_path / "synthetic-collision.json"
    path.write_text(collision.model_dump_json(), encoding="utf-8")
    before = {p: p.read_bytes() for p in admin.root.rglob("*.json")}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "benchmarks",
            "--package",
            str(path),
            "--validate-only",
            "--output",
            str(output),
        ],
        cwd=ROOT / "backend",
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and "Traceback" not in result.stderr
    assert before == {p: p.read_bytes() for p in admin.root.rglob("*.json")}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "benchmarks",
            "--package",
            str(ROOT / "evals/benchmark-package-v1.schema.json"),
            "--validate-only",
        ],
        cwd=ROOT / "backend",
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and "publication repository" in result.stderr


def test_identifier_only_degradation_is_not_scientific_change():
    p = exchange().projects[0]
    b = p.source_package.blocks[1]
    original = b.model_copy(update={"text": "Synthetic Alpha measures handoffs."})
    p = p.model_copy(
        update={
            "source_package": p.source_package.model_copy(
                update={
                    "blocks": tuple(
                        original if x.block_id == b.block_id else x for x in p.source_package.blocks
                    ),
                    "identifying_metadata": ("Alpha", "Beta"),
                }
            )
        }
    )
    replacement = original.model_copy(update={"text": "Synthetic Beta measures handoffs."})
    with pytest.raises(ValueError, match="no-op"):
        construct(
            p,
            Mutation(
                transformation=Transformation.DEGRADE,
                targets=(Feature.MEASURES,),
                replacements=(replacement,),
            ),
            "synthetic-noop",
            freeze((p,), "synthetic-noop-split"),
        )
