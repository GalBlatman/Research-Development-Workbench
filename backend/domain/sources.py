import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, StrictBool, StrictInt, model_validator

from domain.models import (
    Assessment,
    DocumentVersion,
    EvaluationSnapshot,
    Frozen,
    Hash,
    Project,
    ReviewSummary,
    Revision,
    Text,
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(record: Frozen) -> str:
    return json.dumps(
        record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


class AccessScope(Frozen):
    """Internal server actor scope; never trust a model/browser-provided identity."""

    actor_id: Text
    workspace_id: Text
    project_id: Text


class SourceRole(StrEnum):
    DRAFT = "project_draft"
    AUTHOR_NOTE = "author_note"
    PREDECESSOR = "closest_predecessor"
    LITERATURE = "literature"
    ALTERNATIVE = "alternative_account"
    METHOD = "method_or_measure"
    CONTEXT = "context"


class ExtractionState(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    UNREADABLE = "unreadable"


class SourceRecord(Frozen):
    document_id: Text
    workspace_id: Text
    project_id: Text
    title: Text
    source_kind: Literal["uploaded_original", "pasted_original", "pasted_excerpt"]
    role: SourceRole
    media_type: Literal["text/plain", "text/markdown"]
    rights_declaration: Text
    attribution: str | None = None

    @model_validator(mode="after")
    def attributed_excerpt(self) -> Self:
        if self.source_kind == "pasted_excerpt" and not (self.attribution or "").strip():
            raise ValueError("Pasted excerpts require explicit user-reported attribution")
        return self


class OriginalMetadata(Frozen):
    storage_key: Hash | None
    sha256: Hash | None
    byte_length: Annotated[StrictInt, Field(ge=0)] | None
    original_name: str | None = None


class SourceVersion(Frozen):
    document: DocumentVersion
    original: OriginalMetadata
    extraction_state: ExtractionState
    extraction_reason: Text
    media_type: Literal["text/plain", "text/markdown"] = "text/plain"
    parser_version: Literal["utf8-sections-v1"] = "utf8-sections-v1"
    text: str | None = None
    text_sha256: Hash | None = None
    text_presence: Literal["present", "external", "unavailable"]

    @model_validator(mode="after")
    def integrity(self) -> Self:
        SourceRole(self.document.role)
        metadata = (self.original.storage_key, self.original.sha256, self.original.byte_length)
        if any(v is None for v in metadata) and any(v is not None for v in metadata):
            raise ValueError("Original metadata must be complete or explicitly missing")
        if (
            self.extraction_state == ExtractionState.AVAILABLE
            and self.text_sha256 != self.original.sha256
        ):
            raise ValueError("This lossless UTF-8 parser must retain the original text hash")
        if (
            self.extraction_state == ExtractionState.MISSING
            and self.document.content_sha256 is not None
        ):
            raise ValueError("Missing original has no known content hash")
        if (
            self.original.storage_key is not None
            and self.document.original_storage_reference != self.original.storage_key
        ):
            raise ValueError("Original storage reference mismatch")
        if (
            self.original.sha256 is not None
            and self.document.content_sha256 != self.original.sha256
        ):
            raise ValueError("Original/document hash mismatch")
        if self.text_presence == "present":
            if self.text is None or self.extraction_state != ExtractionState.AVAILABLE:
                raise ValueError("Present source text must be available")
            if digest(self.text.encode("utf-8")) != self.text_sha256:
                raise ValueError("Extracted text hash mismatch")
        elif self.text is not None:
            raise ValueError("External/unavailable text cannot contain source text")
        if (
            self.extraction_state != ExtractionState.AVAILABLE
            and self.text_presence != "unavailable"
        ):
            raise ValueError("Missing/unreadable extraction must be explicitly unavailable")
        if self.extraction_state == ExtractionState.MISSING and any(
            value is not None
            for value in (
                self.original.storage_key,
                self.original.sha256,
                self.original.byte_length,
            )
        ):
            raise ValueError("Missing original cannot have invented storage/hash metadata")
        return self


class SourceAnchor(Frozen):
    anchor_id: Hash
    document_id: Text
    version: Revision
    start: Annotated[StrictInt, Field(ge=0)]
    end: Annotated[StrictInt, Field(ge=0)]
    line_start: Annotated[StrictInt, Field(ge=1)]
    line_end: Annotated[StrictInt, Field(ge=1)]
    location_kind: Literal["section"] = "section"
    quoted_text_sha256: Hash

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end < self.start or self.line_end < self.line_start:
            raise ValueError("Invalid source location")
        expected = digest(
            f"{self.document_id}:{self.version}:{self.start}:{self.end}:{self.quoted_text_sha256}".encode()
        )
        if self.anchor_id != expected:
            raise ValueError("Anchor identity mismatch")
        return self


class Admission(Frozen):
    document_id: Text
    version: Revision
    admitted: StrictBool


class StoredSnapshot(Frozen):
    snapshot: EvaluationSnapshot
    assessment: Assessment | None = None
    review: ReviewSummary | None = None

    @model_validator(mode="after")
    def same_target(self) -> Self:
        if self.review is not None and self.assessment is None:
            raise ValueError("Application review requires its frozen assessment")
        if self.assessment is not None and self.assessment.snapshot != self.snapshot:
            raise ValueError("Assessment must retain exactly this frozen snapshot")
        return self


class ProjectBundle(Frozen):
    schema_version: Literal[1] = 1
    workspace_id: Text
    project_id: Text
    revisions: tuple[Project, ...]
    sources: tuple[SourceRecord, ...]
    versions: tuple[SourceVersion, ...]
    anchors: tuple[SourceAnchor, ...]
    admissions: tuple[Admission, ...]
    snapshots: tuple[StoredSnapshot, ...]

    @model_validator(mode="after")
    def unique_scoped_history(self) -> Self:
        if not self.revisions or tuple(p.revision for p in self.revisions) != tuple(
            range(1, len(self.revisions) + 1)
        ):
            raise ValueError("Bundle must contain complete ordered revision history")
        if any(
            p.workspace_id != self.workspace_id or p.project_id != self.project_id
            for p in self.revisions
        ):
            raise ValueError("Project revision outside bundle scope")
        if any(
            s.workspace_id != self.workspace_id or s.project_id != self.project_id
            for s in self.sources
        ):
            raise ValueError("Source outside bundle scope")
        if len({s.document_id for s in self.sources}) != len(self.sources):
            raise ValueError("Duplicate source identity")
        keys = [(v.document.document_id, v.document.version) for v in self.versions]
        if len(set(keys)) != len(keys):
            raise ValueError("Duplicate document version")
        if len({a.anchor_id for a in self.anchors}) != len(self.anchors):
            raise ValueError("Duplicate anchor")
        if len({s.snapshot.snapshot_id for s in self.snapshots}) != len(self.snapshots):
            raise ValueError("Duplicate snapshot identity")
        if set((a.document_id, a.version) for a in self.admissions) != set(keys) or len(
            self.admissions
        ) != len(keys):
            raise ValueError("Exactly one admission per source version required")
        source_ids = {source.document_id for source in self.sources}
        for version in self.versions:
            if (
                version.document.project_id != self.project_id
                or version.document.document_id not in source_ids
            ):
                raise ValueError("Source version outside bundle sources/project")
        if any((a.document_id, a.version) not in set(keys) for a in self.anchors):
            raise ValueError("Anchor outside bundle versions")
        return self
