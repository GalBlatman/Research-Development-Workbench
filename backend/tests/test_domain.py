import pytest
from conftest import make_assessment
from pydantic import ValidationError

from domain.models import (
    Adoption,
    Claim,
    DocumentVersion,
    EvaluationSnapshot,
    EvidenceCheck,
    EvidenceState,
    Origin,
    ProjectObject,
    Provenance,
    Rating,
    SourceReference,
    accept_content,
)
from policy_engine.manifest import Manifest


def proposed() -> ProjectObject:
    return ProjectObject(
        object_id="claim",
        project_id="synthetic-project",
        revision=1,
        payload=Claim(text="Synthetic proposed explanation", claim_type="mechanism"),
        origin=Origin.SUGGESTION,
        adoption=Adoption.PROPOSED,
        evidence_state=EvidenceState.UNTESTED,
        generated_by_run_id="fake-run",
    )


def test_acceptance_preserves_epistemic_state_and_origin() -> None:
    original = proposed()
    accepted = accept_content(original, 2)
    assert accepted.adoption == Adoption.ACCEPTED
    assert accepted.evidence_state == original.evidence_state
    assert accepted.origin == original.origin
    assert original.adoption == Adoption.PROPOSED
    with pytest.raises(ValueError):
        accept_content(accepted, 3)
    with pytest.raises(ValueError):
        accept_content(original, 1)


def test_generated_prose_cannot_self_verify() -> None:
    data = proposed().model_dump()
    data["evidence_state"] = EvidenceState.DOCUMENTED
    with pytest.raises(ValidationError):
        ProjectObject.model_validate(data)
    check = EvidenceCheck(
        check_id="check",
        claim_id="claim",
        object_of_verification="author-reported truth",
        provenance=Provenance.USER_REPORTED,
        checked_by="synthetic-user",
        outcome="reported",
    )
    data["checks"] = [check]
    with pytest.raises(ValidationError):
        ProjectObject.model_validate(data)
    with pytest.raises(ValidationError):
        EvidenceCheck(
            check_id="check",
            claim_id="claim",
            object_of_verification="statistical result",
            provenance=Provenance.APP_REPRODUCED,
            checked_by="app",
            outcome="not actually run",
        )


def test_explicit_bounded_source_verification() -> None:
    ref = SourceReference(document_id="source", version=1, anchor_id="paragraph-1")
    check = EvidenceCheck(
        check_id="check",
        claim_id="claim",
        object_of_verification="source states the claim",
        provenance=Provenance.SOURCE_INSPECTED,
        checked_by="synthetic-user",
        source_refs=(ref,),
        outcome="attribution inspected; truth not independently established",
    )
    data = proposed().model_dump()
    data.update(evidence_state=EvidenceState.DOCUMENTED, checks=(check,))
    obj = ProjectObject.model_validate(data)
    assert obj.checks[0].object_of_verification == "source states the claim"


def test_snapshot_is_deeply_frozen_and_json_roundtrips(manifest: Manifest) -> None:
    assessment = make_assessment(manifest)
    data = assessment.snapshot.model_dump()
    data["project"]["objects"] = [proposed().model_dump()]
    snapshot = EvaluationSnapshot.model_validate(data)
    serialized = snapshot.model_dump_json()
    restored = EvaluationSnapshot.model_validate_json(serialized)
    assert restored == snapshot
    for target, field, value in (
        (snapshot, "snapshot_id", "changed"),
        (snapshot.project, "title", "changed"),
        (snapshot.project.objects[0].payload, "text", "changed"),
    ):
        with pytest.raises(ValidationError):
            setattr(target, field, value)
    accepted = accept_content(snapshot.project.objects[0], 2)
    assert snapshot.project.objects[0].adoption == Adoption.PROPOSED
    assert accepted.revision == 2
    assert snapshot.model_dump_json() == serialized


def test_snapshot_scope_and_source_versions(manifest: Manifest) -> None:
    data = make_assessment(manifest).snapshot.model_dump()
    obj = proposed().model_dump()
    obj["project_id"] = "other-project"
    data["project"]["objects"] = [obj]
    with pytest.raises(ValidationError):
        EvaluationSnapshot.model_validate(data)
    obj["project_id"] = "synthetic-project"
    obj["source_refs"] = [{"document_id": "source", "version": 1, "anchor_id": "paragraph"}]
    with pytest.raises(ValidationError):
        EvaluationSnapshot.model_validate(data)
    data["documents"] = [
        DocumentVersion(
            document_id="source",
            project_id="synthetic-project",
            version=1,
            content_sha256="a" * 64,
            original_storage_reference="private-placeholder",
            role="literature",
        )
    ]
    assert (
        EvaluationSnapshot.model_validate(data).documents[0].original_storage_reference
        == "private-placeholder"
    )


@pytest.mark.parametrize("bad", [True, 5.5, "5", -1, 11])
def test_strict_integer_rating(bad: object, manifest: Manifest) -> None:
    data = make_assessment(manifest).ratings[0].model_dump()
    data["rating"] = bad
    with pytest.raises(ValidationError):
        Rating.model_validate(data)


def test_null_status_roundtrip_and_invalid_range(manifest: Manifest) -> None:
    pending = make_assessment(manifest, [None] * 10).ratings[0]
    assert Rating.model_validate_json(pending.model_dump_json()).rating is None
    data = pending.model_dump()
    data["rating"] = 0
    with pytest.raises(ValidationError):
        Rating.model_validate(data)
    data = make_assessment(manifest).ratings[0].model_dump()
    data["plausible_range"] = (6, 7)
    with pytest.raises(ValidationError):
        Rating.model_validate(data)
