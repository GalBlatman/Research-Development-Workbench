import re
from dataclasses import dataclass

from domain.locations import anchors
from domain.models import DocumentVersion, SourceReference
from domain.sources import (
    AccessScope,
    ExtractionState,
    OriginalMetadata,
    SourceAnchor,
    SourceRecord,
    SourceVersion,
    digest,
)
from persistence.originals import OriginalFileStore, OriginalUnavailable
from persistence.repository import AccessDenied, Repository


@dataclass(frozen=True)
class SearchHit:
    document_id: str
    version: int
    anchor: SourceAnchor
    source_text: str
    matched_terms: tuple[str, ...]


@dataclass(frozen=True)
class SearchResult:
    hits: tuple[SearchHit, ...]
    exclusions: tuple[str, ...]
    limitation: str = "Lexical search only; no match is not evidence of absence. No scientific comprehension claimed."


class SourceService:
    def __init__(self, repository: Repository, originals: OriginalFileStore):
        self.repository = repository
        self.originals = originals

    def append(
        self,
        scope: AccessScope,
        document_id: str,
        version: int,
        data: bytes | None,
        original_name: str | None = None,
    ) -> SourceVersion:
        source = self.repository.source(scope, document_id)
        if data is None:
            state, reason, text = ExtractionState.MISSING, "Original not supplied", None
            original = OriginalMetadata(
                storage_key=None, sha256=None, byte_length=None, original_name=original_name
            )
            content_hash = None
            storage_reference = "unavailable"
        else:
            content_hash = digest(data)
            key = self.originals.key(scope, document_id, version, content_hash)
            self.originals.put(key, data)
            original = OriginalMetadata(
                storage_key=key,
                sha256=content_hash,
                byte_length=len(data),
                original_name=original_name,
            )
            storage_reference = key
            try:
                text = data.decode("utf-8")
                if "\x00" in text:
                    raise UnicodeError("NUL in source text")
                state, reason = (
                    ExtractionState.AVAILABLE,
                    "UTF-8 text retained without normalization",
                )
            except UnicodeError:
                text = None
                state, reason = (
                    ExtractionState.UNREADABLE,
                    "Not readable UTF-8 text/Markdown; original retained",
                )
        document = DocumentVersion(
            document_id=document_id,
            project_id=scope.project_id,
            version=version,
            content_sha256=content_hash,
            original_storage_reference=storage_reference,
            role=source.role.value,
        )
        record = SourceVersion(
            document=document,
            original=original,
            extraction_state=state,
            extraction_reason=reason,
            media_type=source.media_type,
            text=text,
            text_sha256=digest(text.encode("utf-8")) if text is not None else None,
            text_presence="present" if text is not None else "unavailable",
        )
        self.repository.add_version(scope, record, anchors(record))
        return record

    def paste(self, scope: AccessScope, source: SourceRecord, text: str) -> SourceVersion:
        if source.source_kind not in ("pasted_original", "pasted_excerpt"):
            raise ValueError("Paste only original user text or explicitly attributed excerpts")
        with self.repository.db.transaction():
            self.repository.add_source(scope, source)
            return self.append(scope, source.document_id, 1, text.encode("utf-8"))

    def original(self, scope: AccessScope, document_id: str, version: int) -> bytes:
        self.repository.admitted(scope, document_id, version)
        record = self.repository.version(scope, document_id, version)
        key, expected = record.original.storage_key, record.original.sha256
        if key is None or expected is None:
            raise OriginalUnavailable("Original explicitly missing")
        bound = self.originals.key(scope, document_id, version, expected)
        if key != bound:
            raise AccessDenied("Original storage reference outside requested scope")
        return self.originals.read(key, expected)

    def search(
        self, scope: AccessScope, selected: tuple[tuple[str, int], ...], query: str
    ) -> SearchResult:
        terms = tuple(sorted(set(re.findall(r"\w+", query.casefold()))))
        if not terms:
            raise ValueError("Provide a lexical query")
        self.repository.authorize(scope)
        hits: list[SearchHit] = []
        exclusions: list[str] = []
        for document_id, version in sorted(set(selected)):
            self.repository.admitted(scope, document_id, version)
            record = self.repository.version(scope, document_id, version)
            if record.extraction_state != ExtractionState.AVAILABLE or record.text is None:
                exclusions.append(
                    f"{document_id}@{version}: {record.extraction_state.value}/{record.text_presence}"
                )
                continue
            for anchor in anchors(record):
                reference = SourceReference(
                    document_id=document_id, version=version, anchor_id=anchor.anchor_id
                )
                self.repository.get_anchor(scope, reference)
                text = record.text[anchor.start : anchor.end]
                words = set(re.findall(r"\w+", text.casefold()))
                matching = tuple(t for t in terms if t in words)
                if matching:
                    hits.append(SearchHit(document_id, version, anchor, text, matching))
        # Permissions/admissions are rechecked before returning any material.
        for document_id, version in set(selected):
            self.repository.admitted(scope, document_id, version)
        return SearchResult(
            tuple(
                sorted(
                    hits,
                    key=lambda h: (-len(h.matched_terms), h.document_id, h.version, h.anchor.start),
                )
            ),
            tuple(exclusions),
        )
