import json
import os
from uuid import uuid4

import pytest
from conftest import make_assessment
from pydantic import ValidationError

from domain.locations import anchors
from domain.models import (
    Adoption,
    Assessment,
    Claim,
    EvaluationSnapshot,
    EvidenceCheck,
    EvidenceState,
    Origin,
    Project,
    ProjectObject,
    SourceReference,
    Workspace,
    accept_content,
)
from domain.sources import (
    AccessScope,
    ExtractionState,
    ProjectBundle,
    SourceRecord,
    SourceVersion,
    StoredSnapshot,
    canonical,
)
from persistence.database import IMMUTABLE, Database
from persistence.originals import OriginalFileStore, OriginalUnavailable
from persistence.repository import AccessDenied, Conflict, Repository
from services.sources import SourceService


@pytest.fixture(params=["sqlite", "postgres"])
def store(request, tmp_path, manifest):
    schema = None
    if request.param == "sqlite":
        db = Database.sqlite(tmp_path / "synthetic.sqlite")
    else:
        dsn = os.environ.get("RDW_TEST_POSTGRES_DSN")
        if not dsn and os.environ.get("RDW_REQUIRE_POSTGRES") == "1":
            pytest.fail("PostgreSQL contract is mandatory in this CI environment")
        if not dsn:
            pytest.skip("PostgreSQL parity runs in CI; no local DSN supplied")
        db = Database.postgres(dsn)
        schema = "rdw_test_" + uuid4().hex
        db.execute(f"CREATE SCHEMA {schema}")
        db.execute(f"SET search_path TO {schema}")
    db.initialize()
    scope = AccessScope(
        actor_id="owner", workspace_id="synthetic-workspace", project_id="synthetic-project"
    )
    repo = Repository(db)
    repo.register_workspace(
        "owner",
        Workspace(
            workspace_id=scope.workspace_id,
            owner_id="owner",
            access_policy="private owner",
            model_processing_policy="none",
            storage_policy="private test files",
        ),
    )
    repo.create_project(scope, make_assessment(manifest).snapshot.project)
    service = SourceService(repo, OriginalFileStore(tmp_path / "private-originals"))
    yield repo, service, scope
    if schema:
        db.execute("SET search_path TO public")
        db.execute(f"DROP SCHEMA {schema} CASCADE")
    db.close()


def source(scope, identifier="synthetic-source", kind="uploaded_original"):
    return SourceRecord(
        document_id=identifier,
        workspace_id=scope.workspace_id,
        project_id=scope.project_id,
        title="Synthetic source",
        source_kind=kind,
        role="literature",
        media_type="text/markdown",
        rights_declaration="Synthetic text authored for tests only",
        attribution="Synthetic user-attributed excerpt" if kind == "pasted_excerpt" else None,
    )


def add_text(
    store, text="# First\nSynthetic alpha mechanism.\n\n# Second\nSynthetic beta observation.\n"
):
    repo, service, scope = store
    repo.add_source(scope, source(scope))
    version = service.append(scope, "synthetic-source", 1, text.encode("utf-8"))
    repo.set_admission(scope, "synthetic-source", 1, True)
    return version


def stored_snapshot(repo, scope, manifest, documents=(), identifier="snapshot-1", assessment=None):
    data = make_assessment(manifest).snapshot.model_dump()
    data.update(
        snapshot_id=identifier, project=repo.project(scope).model_dump(), documents=documents
    )
    snapshot = EvaluationSnapshot.model_validate(data)
    if assessment is not None:
        assessment_data = assessment.model_dump()
        assessment_data["snapshot"] = snapshot.model_dump()
        assessment_data["findings"] = [
            dict(f, scope=identifier) for f in assessment_data["findings"]
        ]
        assessment = Assessment.model_validate(assessment_data)
    return StoredSnapshot(snapshot=snapshot, assessment=assessment)


def test_save_reload_revisions_and_conflicts(store):
    repo, _, scope = store
    original = repo.project(scope)
    data = original.model_dump()
    data.update(title="Revised synthetic title", revision=2)
    revised = Project.model_validate(data)
    repo.save_project(scope, revised, 1)
    assert repo.project(scope) == revised
    assert repo.project(scope, 1) == original
    with pytest.raises(Conflict):
        repo.save_project(scope, revised, 1)
    assert repo.project(scope, 1) == original
    # Reload through a new repository instance over the same adapter.
    assert Repository(repo.db).project(scope) == revised


def test_document_versions_and_anchors_are_immutable(store):
    repo, service, scope = store
    first = add_text(store)
    second = service.append(scope, "synthetic-source", 2, b"# Revised\nSynthetic gamma result.\n")
    repo.set_admission(scope, "synthetic-source", 2, True)
    assert repo.version(scope, "synthetic-source") == second
    assert repo.version(scope, "synthetic-source", 1) == first
    a = anchors(first)[0]
    ref = SourceReference(document_id="synthetic-source", version=1, anchor_id=a.anchor_id)
    assert repo.get_anchor(scope, ref) == a
    assert first.text[a.start : a.end].startswith("# First")
    assert service.original(scope, "synthetic-source", 1) == first.text.encode("utf-8")
    assert len(anchors(first)) == 2
    with pytest.raises(AccessDenied):
        repo.get_anchor(
            scope, SourceReference(document_id="synthetic-source", version=2, anchor_id=a.anchor_id)
        )
    with pytest.raises(Conflict):
        service.append(scope, "synthetic-source", 1, b"Attempted rewrite")
    assert repo.version(scope, "synthetic-source", 1) == first


def test_snapshot_stays_unchanged_after_later_project_and_source_edits(store, manifest):
    repo, service, scope = store
    first = add_text(store)
    snapshot = stored_snapshot(repo, scope, manifest, (first.document,))
    repo.save_snapshot(scope, snapshot)
    encoded = canonical(repo.snapshot(scope, "snapshot-1"))
    data = repo.project(scope).model_dump()
    data.update(title="Changed after evaluation", revision=2)
    repo.save_project(scope, Project.model_validate(data), 1)
    service.append(scope, "synthetic-source", 2, b"Different later text")
    assert canonical(repo.snapshot(scope, "snapshot-1")) == encoded
    with pytest.raises(Conflict):
        repo.save_snapshot(scope, snapshot)


def test_generated_content_rejected_and_adoption_not_verification(store):
    repo, service, scope = store
    data = source(scope).model_dump()
    data["source_kind"] = "model_inference"
    with pytest.raises(ValidationError):
        SourceRecord.model_validate(data)
    data = source(scope).model_dump()
    data["generated_by_run_id"] = "fake-model-output"
    with pytest.raises(ValidationError):
        SourceRecord.model_validate(data)
    obj = ProjectObject(
        object_id="claim",
        project_id=scope.project_id,
        revision=1,
        payload=Claim(text="Synthetic proposed mechanism", claim_type="mechanism"),
        origin=Origin.SUGGESTION,
        adoption=Adoption.PROPOSED,
        evidence_state=EvidenceState.UNTESTED,
    )
    accepted = accept_content(obj, 2)
    data = repo.project(scope).model_dump()
    data.update(revision=2, objects=(accepted,))
    repo.save_project(scope, Project.model_validate(data), 1)
    assert repo.project(scope).objects[0].evidence_state == EvidenceState.UNTESTED


def test_cross_project_workspace_and_actor_access_rejected(store, manifest):
    repo, service, scope = store
    add_text(store)
    other_scope = AccessScope(
        actor_id="owner", workspace_id=scope.workspace_id, project_id="other-project"
    )
    data = repo.project(scope).model_dump()
    data.update(project_id="other-project")
    repo.create_project(other_scope, Project.model_validate(data))
    for wrong_scope in (
        other_scope,
        AccessScope(
            actor_id="intruder", workspace_id=scope.workspace_id, project_id=scope.project_id
        ),
        AccessScope(actor_id="owner", workspace_id="other-workspace", project_id=scope.project_id),
    ):
        with pytest.raises(AccessDenied):
            service.search(wrong_scope, (("synthetic-source", 1),), "alpha")
        with pytest.raises(AccessDenied):
            service.original(wrong_scope, "synthetic-source", 1)


def test_missing_unreadable_and_empty_text_are_distinct(store):
    repo, service, scope = store
    repo.add_source(scope, source(scope))
    missing = service.append(scope, "synthetic-source", 1, None)
    unreadable = service.append(scope, "synthetic-source", 2, b"\xff\xfe synthetic")
    empty = service.append(scope, "synthetic-source", 3, b"")
    for v in (1, 2, 3):
        repo.set_admission(scope, "synthetic-source", v, True)
    assert missing.extraction_state == ExtractionState.MISSING
    assert missing.original.sha256 is None
    assert missing.document.content_sha256 is None
    assert unreadable.extraction_state == ExtractionState.UNREADABLE
    assert service.original(scope, "synthetic-source", 2) == b"\xff\xfe synthetic"
    assert empty.text == "" and empty.extraction_state == ExtractionState.AVAILABLE
    with pytest.raises(OriginalUnavailable):
        service.original(scope, "synthetic-source", 1)
    result = service.search(scope, (("synthetic-source", 1), ("synthetic-source", 2)), "alpha")
    assert len(result.exclusions) == 2 and result.hits == ()


def test_retrieval_is_selected_admitted_and_not_absence_proof(store):
    repo, service, scope = store
    first = add_text(store)
    service.append(scope, "synthetic-source", 2, b"A newer synthetic alpha assertion")
    result = service.search(scope, (("synthetic-source", 1),), "ALPHA")
    assert len(result.hits) == 1 and result.hits[0].version == 1
    assert "# First" in result.hits[0].source_text
    assert "# Second" not in result.hits[0].source_text
    with pytest.raises(AccessDenied):
        service.search(scope, (("synthetic-source", 2),), "alpha")
    no_match = service.search(scope, (("synthetic-source", 1),), "not_a_real_token")
    assert no_match.hits == () and "not evidence of absence" in no_match.limitation
    assert repo.version(scope, "synthetic-source", 1) == first


def test_admission_revocation_blocks_retrieval_and_late_snapshot(store, manifest):
    repo, service, scope = store
    version = add_text(store)
    candidate = stored_snapshot(repo, scope, manifest, (version.document,))
    repo.set_admission(scope, "synthetic-source", 1, False)
    with pytest.raises(AccessDenied):
        service.search(scope, (("synthetic-source", 1),), "alpha")
    with pytest.raises(AccessDenied):
        repo.save_snapshot(scope, candidate)


def test_export_import_roundtrip_preserves_states_and_snapshots(store, manifest, tmp_path):
    repo, service, scope = store
    version = add_text(store)
    anchor = anchors(version)[0]
    reference = SourceReference(
        document_id="synthetic-source", version=1, anchor_id=anchor.anchor_id
    )
    objects = []
    for i, state in enumerate(EvidenceState):
        checks = ()
        if state == EvidenceState.DOCUMENTED:
            checks = (
                EvidenceCheck(
                    check_id="check",
                    claim_id=f"claim-{i}",
                    object_of_verification="Source states this bounded claim, not independent truth",
                    provenance="source_text_inspected",
                    checked_by="synthetic-user",
                    source_refs=(reference,),
                    outcome="Attribution inspected",
                ),
            )
        objects.append(
            ProjectObject(
                object_id=f"claim-{i}",
                project_id=scope.project_id,
                revision=2,
                payload=Claim(text=f"Synthetic claim {i}", claim_type="assumption"),
                origin=Origin.INFERENCE,
                adoption=Adoption.PROPOSED if i % 2 else Adoption.ACCEPTED,
                evidence_state=state,
                source_refs=(reference,),
                checks=checks,
            )
        )
    data = repo.project(scope).model_dump()
    data.update(revision=2, objects=tuple(objects))
    repo.save_project(scope, Project.model_validate(data), 1)
    rating_data = make_assessment(manifest, [None] * 10).model_dump()
    rating_data["ratings"][3]["status"] = "not_applicable"
    assessment = Assessment.model_validate(rating_data)
    snap = stored_snapshot(repo, scope, manifest, (version.document,), assessment=assessment)
    repo.save_snapshot(scope, snap)
    exported = repo.export(scope, include_source_text=True)
    assert exported == repo.export(scope, include_source_text=True)
    target_db = Database.sqlite()
    target_db.initialize()
    target = Repository(target_db)
    target.register_workspace(
        "owner",
        Workspace(
            workspace_id=scope.workspace_id,
            owner_id="owner",
            access_policy="private",
            model_processing_policy="none",
            storage_policy="synthetic",
        ),
    )
    target.import_bundle(scope, exported)
    assert target.export(scope, include_source_text=True) == exported
    restored = target.snapshot(scope, "snapshot-1")
    assert restored == snap
    assert restored.assessment.ratings[0].rating is None
    assert restored.assessment.ratings[0].status == "pending"
    assert restored.assessment.ratings[3].status == "not_applicable"
    target_db.close()


def test_default_export_excludes_source_text_and_original_bytes(store):
    repo, service, scope = store
    add_text(store)
    exported = repo.export(scope)
    bundle = ProjectBundle.model_validate_json(exported)
    assert bundle.versions[0].text is None
    assert bundle.versions[0].text_presence == "external"
    assert bundle.versions[0].extraction_state == ExtractionState.AVAILABLE
    repo.set_admission(scope, "synthetic-source", 1, False)
    assert ProjectBundle.model_validate_json(repo.export(scope, True)).versions[0].text is None


def test_import_failure_is_atomic_and_cannot_overwrite(store, manifest):
    repo, service, scope = store
    version = add_text(store)
    exported = repo.export(scope, True)
    with pytest.raises(Conflict):
        repo.import_bundle(scope, exported)
    data = json.loads(exported)
    data["versions"][0]["document"]["version"] = 2
    data["anchors"] = []
    data["admissions"][0]["version"] = 2
    target_db = Database.sqlite()
    target_db.initialize()
    target = Repository(target_db)
    target.register_workspace(
        "owner",
        Workspace(
            workspace_id=scope.workspace_id,
            owner_id="owner",
            access_policy="private",
            model_processing_policy="none",
            storage_policy="synthetic",
        ),
    )
    with pytest.raises((Conflict, ValidationError)):
        target.import_bundle(scope, json.dumps(data))
    assert target_db.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0
    assert target_db.execute("SELECT COUNT(*) FROM source_documents").fetchone()[0] == 0
    target.import_bundle(scope, exported)
    assert target.version(scope, "synthetic-source", 1) == version
    target_db.close()


@pytest.mark.parametrize("table", IMMUTABLE)
def test_database_rejects_history_updates_and_deletes(store, manifest, table):
    repo, _, scope = store
    version = add_text(store)
    repo.save_snapshot(scope, stored_snapshot(repo, scope, manifest, (version.document,)))
    for statement in (f"UPDATE {table} SET payload=payload", f"DELETE FROM {table}"):
        with pytest.raises(Exception, match="immutable history"):
            with repo.db.transaction():
                repo.db.execute(statement)
    assert repo.project(scope).revision == 1


def test_hash_tampering_and_invalid_anchor_import_rejected(store):
    repo, _, scope = store
    add_text(store)
    data = json.loads(repo.export(scope, True))
    data["versions"][0]["text"] = "Altered synthetic text"
    with pytest.raises(ValidationError):
        ProjectBundle.model_validate(data)
    data = json.loads(repo.export(scope, True))
    data["anchors"][0]["version"] = 999
    with pytest.raises(ValidationError):
        ProjectBundle.model_validate(data)


def test_original_file_missing_is_explicit_without_mutating_history(store):
    repo, service, scope = store
    first = add_text(store)
    # Synthetic loss in this test's own private store only.
    target = service.originals.root / first.original.storage_key
    target.unlink()
    with pytest.raises(OriginalUnavailable):
        service.original(scope, "synthetic-source", 1)
    assert repo.version(scope, "synthetic-source", 1) == first


def test_pasted_excerpt_requires_attribution_and_is_not_verified(store):
    repo, service, scope = store
    excerpt = source(scope, kind="pasted_excerpt")
    record = service.paste(scope, excerpt, "Synthetic user-attributed excerpt")
    assert record.text == "Synthetic user-attributed excerpt"
    assert (
        repo.source(scope, excerpt.document_id).attribution == "Synthetic user-attributed excerpt"
    )
    data = excerpt.model_dump()
    data["attribution"] = None
    with pytest.raises(ValidationError):
        SourceRecord.model_validate(data)
    with pytest.raises(AccessDenied):
        service.search(scope, ((excerpt.document_id, 1),), "excerpt")


def test_lossless_hash_and_scope_key_collisions_rejected(store):
    repo, service, scope = store
    version = add_text(store)
    data = version.model_dump()
    data["text"] = "Different synthetic text"
    from domain.sources import digest

    data["text_sha256"] = digest(data["text"].encode())
    with pytest.raises(ValidationError):
        SourceVersion.model_validate(data)
    left = AccessScope(actor_id="owner", workspace_id="a:b", project_id="c")
    right = AccessScope(actor_id="owner", workspace_id="a", project_id="b:c")
    assert service.originals.key(left, "d", 1, "a" * 64) != service.originals.key(
        right, "d", 1, "a" * 64
    )


def test_plain_text_and_markdown_fences_keep_stable_locations(store):
    repo, service, scope = store
    text = "# Header\r\nSynthetic \u03b1 claim.\r\n```text\r\n# Inside code\r\n```\r\n# Next\r\nSynthetic second claim.\r\n"
    version = add_text(store, text)
    locations = anchors(version)
    assert len(locations) == 2
    assert version.text == text
    assert "# Inside code" in version.text[locations[0].start : locations[0].end]
    assert locations[1].line_start == 6
    plain = SourceRecord(
        document_id="plain",
        workspace_id=scope.workspace_id,
        project_id=scope.project_id,
        title="Plain text",
        source_kind="pasted_original",
        role="author_note",
        media_type="text/plain",
        rights_declaration="Synthetic original",
    )
    plain_version = service.paste(scope, plain, text)
    assert len(anchors(plain_version)) == 1


def test_admission_is_rechecked_before_return(store, monkeypatch):
    repo, service, scope = store
    add_text(store)
    original_get = repo.get_anchor

    def revoke_after_anchor(*args, **kwargs):
        result = original_get(*args, **kwargs)
        repo.set_admission(scope, "synthetic-source", 1, False)
        return result

    monkeypatch.setattr(repo, "get_anchor", revoke_after_anchor)
    with pytest.raises(AccessDenied):
        service.search(scope, (("synthetic-source", 1),), "alpha")


def test_file_database_survives_connection_reopen(store):
    repo, service, scope = store
    before = repo.project(scope)
    if repo.db.dialect == "sqlite":
        filename = repo.db.execute("PRAGMA database_list").fetchone()[2]
        reopened = Database.sqlite(filename)
        reopened.initialize()
        assert Repository(reopened).project(scope) == before
        reopened.close()
    else:
        # Independent repository reads exercise persisted SQL records; PostgreSQL
        # server durability is also verified by its real service contract in CI.
        assert Repository(repo.db).project(scope) == before


def test_export_anchor_order_does_not_change_locations_on_import(store):
    repo, service, scope = store
    version = add_text(
        store, "# A\nSynthetic one\n# B\nSynthetic two\n# C\nSynthetic three\n# D\nSynthetic four\n"
    )
    serialized = repo.export(scope, True)
    target_db = Database.sqlite()
    target_db.initialize()
    target = Repository(target_db)
    target.register_workspace(
        "owner",
        Workspace(
            workspace_id=scope.workspace_id,
            owner_id="owner",
            access_policy="private",
            model_processing_policy="none",
            storage_policy="synthetic",
        ),
    )
    target.import_bundle(scope, serialized)
    assert anchors(target.version(scope, "synthetic-source", 1)) == anchors(version)
    assert target.export(scope, True) == serialized
    target_db.close()
