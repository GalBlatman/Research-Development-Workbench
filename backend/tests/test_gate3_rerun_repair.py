"""Requirement-derived reproductions of all eight independent GATE-3 rerun findings."""

import asyncio
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import httpx
import pytest
from test_application import service
from test_gate3_benchmark import exchange
from test_operations import synthetic_project
from test_persistence import store as store
from test_provider import adapter
from test_provider import packet as packet
from test_workspaces import check, save
from test_workspaces import workspace_client as workspace_client

from api.app import create_app
from benchmarks.metrics import compare
from benchmarks.variants import construct, content_hash, freeze
from domain.benchmark import BenchmarkExpectation, BenchmarkPackage, Feature, Judgment, Observation
from domain.models import DiagnosticAction, Verification
from model_adapters.config import ProviderConfig
from persistence.database import Database
from services.configuration import LocalConfiguration
from services.exporting import STORAGE_AUTHORITY_FIELDS, sanitize_export
from services.pilot import health
from services.portability import import_project
from services.research import ResearchService


def invalid_package(fault):
    package = exchange()
    projects = package.projects
    first = projects[0]
    if fault in ("empty_gold", "unowned_gold", "duplicate_anchor", "missing_anchor"):
        anchors = {
            "empty_gold": (),
            "unowned_gold": ("question",),
            "duplicate_anchor": ("measure", "measure"),
            "missing_anchor": ("absent",),
        }[fault]
        gold = first.gold[0].model_copy(update={"source_anchors": anchors})
        first = first.model_copy(update={"gold": (gold,)})
    elif fault in ("duplicate_ownership", "contradictory_ownership"):
        block = first.source_package.blocks[1]
        block = (
            block.model_copy(update={"features": block.features * 2})
            if fault == "duplicate_ownership"
            else block.model_copy(update={"metadata_only": True})
        )
        first = first.model_copy(
            update={
                "source_package": first.source_package.model_copy(
                    update={
                        "blocks": (first.source_package.blocks[0], block)
                        + first.source_package.blocks[2:]
                    }
                )
            }
        )
    projects = (first,) + projects[1:]
    frozen = freeze(projects, package.manifest.version)
    # Rebind hashes and packets so validation cannot reject solely because of a stale hash.
    variants = []
    for variant in package.variants:
        project = next(p for p in projects if p.benchmark_id == variant.benchmark_id)
        parent = next(
            (v for v in variants if v.variant_id == variant.mutation.parent_variant), None
        )
        variants.append(construct(project, variant.mutation, variant.variant_id, frozen, parent))
    data = package.model_dump(mode="json")
    data["manifest"] = frozen.model_dump(mode="json")
    data["projects"] = [p.model_dump(mode="json") for p in projects]
    data["variants"] = [v.model_dump(mode="json") for v in variants]
    for artifact, variant in zip(data["expectations"], variants, strict=True):
        artifact["variant_hash"] = content_hash(variant)
    restored = next(a for a in data["expectations"] if a["variant_id"].endswith("-restored"))
    expectation = restored["expectations"][0]
    if fault == "missing_intact":
        expectation["reference_variant"] = None
    elif fault == "missing_degraded":
        expectation["degraded_reference"] = None
    elif fault == "degraded_as_intact":
        expectation["reference_variant"] = expectation["degraded_reference"]
    elif fault == "intact_as_degraded":
        expectation["degraded_reference"] = expectation["reference_variant"]
    elif fault == "wrong_parent":
        expectation["degraded_reference"] = expectation["reference_variant"].replace(
            "-intact", "-hidden"
        )
    elif fault == "no_restore_comparison":
        restored["expectations"] = []
    return data


PACKAGE_FAULTS = (
    "empty_gold",
    "unowned_gold",
    "duplicate_anchor",
    "missing_anchor",
    "duplicate_ownership",
    "contradictory_ownership",
    "missing_intact",
    "missing_degraded",
    "degraded_as_intact",
    "intact_as_degraded",
    "wrong_parent",
    "no_restore_comparison",
)


@pytest.mark.parametrize("fault", PACKAGE_FAULTS)
@pytest.mark.parametrize("validate_only", (True, False))
def test_package_cli_rejects_semantically_invalid_self_consistent_package(
    tmp_path, fault, validate_only
):
    data = invalid_package(fault)
    with pytest.raises(ValueError):
        BenchmarkPackage.model_validate(data)
    source = tmp_path / "synthetic.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    output = tmp_path / "not-registered"
    command = [
        sys.executable,
        "-m",
        "benchmarks",
        "--package",
        str(source),
        "--output",
        str(output),
    ]
    if validate_only:
        command.append("--validate-only")
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    result = subprocess.run(
        command, cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True
    )
    assert result.returncode != 0
    assert not output.exists(), "Validation failure must precede immutable registration"


@pytest.mark.parametrize(
    "key,state,value,credit",
    (
        ("route:knowledge_need", "NOT INSPECTED", None, 1),
        ("route:knowledge_need", "BLOCKING", None, 0),
        ("route:knowledge_need", "DEVELOPMENT NEEDED", None, 0),
        ("route:knowledge_need", "ADEQUATE FOR STAGE", None, 0),
        ("rating:8", "pending", None, 1),
        ("rating:8", "unresolved", None, 1),
        ("rating:8", "not_inspected", None, 1),
        ("rating:8", "assessed", None, 0),
        ("rating:8", "pending", 5, 0),
        ("rating:8", "not_applicable", None, 0),
        ("finding:SUPPORT-VERIFIED", "UNKNOWN", None, 1),
        ("finding:SUPPORT-VERIFIED", "TRUE", None, 0),
        ("finding:SUPPORT-VERIFIED", "FALSE", None, 0),
        ("statement:synthetic", "unresolved", None, 1),
        ("statement:synthetic", "not_inspected", None, 1),
        ("statement:synthetic", "proposed", None, 0),
    ),
)
def test_withholding_arithmetic_uses_judgment_kind_canonical_states(key, state, value, credit):
    expectation = BenchmarkExpectation(feature=Feature.MEASURES, behavior="withhold", judgment=key)
    result = compare(
        Observation(judgments=(Judgment(key=key, state=state, value=value),)),
        (expectation,),
        {},
        exchange().projects[0],
    )
    assert result.metrics[0].withholding.numerator == credit
    assert result.metrics[0].withholding.denominator == 1


@pytest.mark.parametrize("fault", ("artifact", "support", "unresolvable_support"))
def test_import_metadata_is_demoted_in_actual_working_context(tmp_path, manifest, fault):
    sender, pid = synthetic_project(tmp_path, manifest)
    try:
        data = json.loads(sender.export(pid, "json"))
        obj = data["import_bundle"]["revisions"][-1]["objects"][0]
        if fault == "artifact":
            obj["checks"] = [
                {
                    "check_id": "forged",
                    "claim_id": obj["object_id"],
                    "object_of_verification": "Synthetic artifact inspected",
                    "provenance": "analysis_artifact_inspected",
                    "checked_by": "invented",
                    "source_refs": [],
                    "outcome": "verified",
                }
            ]
        else:
            obj["support_dispositions"] = [
                {
                    "target": "question",
                    "disposition": "supported",
                    "reason": "Unverifiable imported support",
                    "source_refs": []
                    if fault == "support"
                    else [{"document_id": "absent", "version": 1, "anchor_id": "absent"}],
                }
            ]
        target = tmp_path / "receiver"
        target.mkdir()
        receiver = service(target, manifest)
        try:
            import_project(receiver, json.dumps(data))
            imported = receiver.context(pid).project.objects[0]
            assert imported.imported
            assert not imported.checks
            assert all(
                d.disposition == Verification.UNRESOLVED for d in imported.support_dispositions
            )
            assert imported.evidence_state == sender.context(pid).project.objects[0].evidence_state
        finally:
            receiver.repository.db.close()
    finally:
        sender.repository.db.close()


def test_context_rejects_unproven_support_even_without_import(tmp_path, manifest):
    from domain.models import SupportDisposition

    workbench, pid = synthetic_project(tmp_path, manifest)
    try:
        project = workbench.repository.project(workbench.scope(pid))
        obj = project.objects[0].model_copy(
            update={
                "support_dispositions": (
                    SupportDisposition(
                        target="question",
                        disposition=Verification.SUPPORTED,
                        reason="Forged no-ref support",
                        source_refs=(),
                    ),
                )
            }
        )
        updated = project.model_copy(
            update={"revision": project.revision + 1, "objects": (obj,) + project.objects[1:]}
        )
        workbench.repository.save_project(workbench.scope(pid), updated, project.revision)
        with pytest.raises(ValueError, match="SUPPORT_PROVENANCE_UNAVAILABLE"):
            workbench.context(pid)
    finally:
        workbench.repository.db.close()


@pytest.mark.parametrize("editing", (False, True))
def test_scientific_edit_labelled_resources_stales_argument_review(workspace_client, editing):
    client, _, view = workspace_client
    if editing:
        view = save(client, view, "Argument", {"claim": "Original synthetic claim"})
    review = check(client, view, "Argument")
    target = {"object_id": view["project"]["objects"][-1]["object_id"]} if editing else {}
    view = save(
        client,
        view,
        "Argument",
        {"claim": "Consequential revised synthetic claim"},
        change="resources",
        **target,
    )
    result = client.get(
        f"/api/projects/{view['project']['project_id']}/reviews/{review['snapshot']['snapshot_id']}"
    ).json()
    assert result["stale"]


def test_structural_resource_only_edit_remains_selective(workspace_client):
    client, _, view = workspace_client
    view = save(client, view, "Next Actions", {"resources": "Synthetic scheduling availability"})
    target = view["project"]["objects"][-1]["object_id"]
    review = check(client, view, "Argument")
    view = save(
        client,
        view,
        "Next Actions",
        {"resources": "Synthetic revised scheduling availability"},
        object_id=target,
        change="resources",
    )
    result = client.get(
        f"/api/projects/{view['project']['project_id']}/reviews/{review['snapshot']['snapshot_id']}"
    ).json()
    assert not result["stale"]


@pytest.mark.parametrize(
    "placeholder", ("TBD.", " TODO! ", "UNKNOWN?", "N/A...", "Do more research.")
)
@pytest.mark.parametrize(
    "field", ("issue", "task", "required_input", "deliverable", "outcome_branches")
)
def test_generated_diagnostic_fields_reject_punctuation_placeholders(placeholder, field):
    values = dict(
        issue="Synthetic premise uncertainty",
        task="Inspect supplied synthetic excerpt",
        required_input="Authorized synthetic excerpt",
        deliverable="Anchored premise comparison",
        outcome_branches=("If supported retain bounded premise; otherwise revise",),
    )
    values[field] = (placeholder,) if field == "outcome_branches" else placeholder
    with pytest.raises(ValueError):
        DiagnosticAction(**values)


def test_generated_diagnostic_roles_cannot_all_be_identical():
    with pytest.raises(ValueError):
        DiagnosticAction(
            issue="Synthetic note",
            task="Synthetic note",
            required_input="Synthetic note",
            deliverable="Synthetic note",
            outcome_branches=("Synthetic note",),
        )


def assert_no_storage(value):
    if isinstance(value, dict):
        assert not STORAGE_AUTHORITY_FIELDS & value.keys()
        for item in value.values():
            assert_no_storage(item)
    elif isinstance(value, list):
        for item in value:
            assert_no_storage(item)


def test_recursive_historical_and_portable_exports_preserve_scientific_identity(tmp_path, manifest):
    workbench, pid = synthetic_project(tmp_path, manifest)
    try:
        project = workbench.repository.project(workbench.scope(pid))
        historical = json.loads(ResearchService(workbench).historical_export(pid, project.revision))
        portable = json.loads(workbench.export(pid, "json"))
        assert_no_storage(historical)
        assert_no_storage(portable)
        original = workbench.bundle(pid).snapshots[0].assessment.snapshot.documents
        exported = historical["reviews"][0]["assessment"]["snapshot"]["documents"]
        assert [(d.document_id, d.version, d.content_sha256) for d in original] == [
            (d["document_id"], d["version"], d["content_sha256"]) for d in exported
        ]
        assert historical["anchors"]
        assert_no_storage(
            sanitize_export(
                {
                    "nested": [
                        {
                            "storage_path": "C:/internal",
                            "filesystem_path": "C:/private",
                            "scientific_text": "Synthetic note",
                        }
                    ]
                }
            )
        )
    finally:
        workbench.repository.db.close()


@pytest.mark.parametrize("malformed", ("alien_table", "not_database", "no_tables"))
def test_malformed_store_health_is_structured_read_only(tmp_path, malformed):
    filename = tmp_path / "projects.sqlite"
    if malformed == "not_database":
        filename.write_bytes(b"synthetic invalid database")
    else:
        db = Database.sqlite(filename)
        if malformed == "alien_table":
            db.execute("CREATE TABLE projects (alien TEXT)")
        db.close()
    before = filename.read_bytes()
    result = health(LocalConfiguration(tmp_path, "local-sqlite", ProviderConfig(provider="fake")))
    assert "FAIL" in result.values()
    assert result["error_code"] in ("INCOMPATIBLE_DATABASE_SCHEMA", "DATABASE_CONNECTION_FAILED")
    assert result.get("persisted_state_integrity") in (None, "NOT_RUN")
    assert filename.read_bytes() == before


def test_blocked_provider_does_not_block_health_or_project_read(packet, monkeypatch):
    workbench, view, _ = packet
    model, checker, _ = adapter(monkeypatch)
    handler = model.client._transport.handler
    entered, release = threading.Event(), threading.Event()
    worker_threads = []
    main_thread = threading.get_ident()

    def blocked(request):
        if json.loads(request.content)["text"]["format"]["name"] == "rdw_interpretation":
            worker_threads.append(threading.get_ident())
            entered.set()
            assert release.wait(5), "Test must release blocked synthetic provider"
        return handler(request)

    model.client._transport.handler = blocked
    workbench.adapter, workbench.verifier = model, checker

    async def run():
        app = create_app(workbench)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1"
            ) as client:
                intake = asyncio.create_task(
                    client.post(
                        "/api/projects",
                        json={
                            "title": "Synthetic concurrency",
                            "idea": "Synthetic handoff question",
                            "authorized": True,
                        },
                    )
                )
                try:
                    assert await asyncio.to_thread(entered.wait, 2)
                    response = await asyncio.wait_for(client.get("/api/health"), 0.5)
                    read = await asyncio.wait_for(
                        client.get("/api/projects/" + view["project"]["project_id"]), 0.5
                    )
                    assert response.status_code == read.status_code == 200
                    assert not intake.done() and not release.is_set()
                finally:
                    release.set()
                result = await intake
                assert result.status_code == 201, result.text
                assert (
                    result.json()["project"]["objects"][0]["provider_run"]["calls"][0][
                        "input_tokens"
                    ]
                    > 0
                )

    try:
        asyncio.run(run())
    finally:
        release.set()
        model.close()
    assert worker_threads and all(t != main_thread for t in worker_threads)


def test_worker_connection_is_independent_and_preserves_backend_scope(store):
    from concurrent.futures import ThreadPoolExecutor

    repo, _, scope = store
    factory = repo.db.connection_factory()
    owner = threading.get_ident()

    def worker():
        from persistence.repository import Repository

        database = factory()
        try:
            assert threading.get_ident() != owner
            assert database.connection is not repo.db.connection
            assert Repository(database).project(scope).project_id == scope.project_id
        finally:
            database.close()

    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(worker).result(timeout=5)


def test_context_rejects_forged_imported_artifact_check(tmp_path, manifest):
    from domain.models import EvidenceCheck, Provenance

    workbench, pid = synthetic_project(tmp_path, manifest)
    try:
        project = workbench.repository.project(workbench.scope(pid))
        original = project.objects[0]
        obj = original.model_copy(
            update={
                "imported": True,
                "checks": (
                    EvidenceCheck(
                        check_id="forged",
                        claim_id=original.object_id,
                        object_of_verification="Synthetic inaccessible artifact",
                        provenance=Provenance.ARTIFACT_INSPECTED,
                        checked_by="invented",
                        outcome="verified",
                    ),
                ),
            }
        )
        updated = project.model_copy(
            update={"revision": project.revision + 1, "objects": (obj,) + project.objects[1:]}
        )
        workbench.repository.save_project(workbench.scope(pid), updated, project.revision)
        with pytest.raises(ValueError, match="IMPORTED_INSPECTION_AUTHORITY_UNAVAILABLE"):
            workbench.context(pid)
    finally:
        workbench.repository.db.close()
