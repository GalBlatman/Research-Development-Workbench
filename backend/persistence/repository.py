from typing import TypeVar

from domain.locations import anchors as expected_anchors
from domain.locations import validate_anchor
from domain.models import Frozen, Project, SourceReference, Workspace
from domain.sources import (
    AccessScope,
    Admission,
    ProjectBundle,
    SourceAnchor,
    SourceRecord,
    SourceVersion,
    StoredSnapshot,
    canonical,
    digest,
)
from persistence.database import Database

T = TypeVar("T", bound=Frozen)


class AccessDenied(PermissionError):
    pass


class Conflict(ValueError):
    pass


class IntegrityViolation(ValueError):
    pass


class Repository:
    def __init__(self, database: Database):
        self.db = database

    def _decode(self, row: tuple[str, str] | None, model: type[T]) -> T:
        if row is None:
            raise AccessDenied("Record not available in authorized scope")
        payload, recorded_hash = row
        if digest(payload.encode("utf-8")) != recorded_hash:
            raise IntegrityViolation("Stored record hash mismatch")
        return model.model_validate_json(payload)

    def register_workspace(
        self, actor: str, workspace: Workspace, allow_model_policy_change: bool = False
    ) -> None:
        if actor != workspace.owner_id:
            raise AccessDenied("Only the owner can register this workspace")
        with self.db.transaction():
            row = self.db.execute(
                "SELECT payload,digest FROM workspaces WHERE workspace_id=?",
                (workspace.workspace_id,),
            ).fetchone()
            if row is not None:
                existing = self._decode(row, Workspace)
                if existing != workspace:
                    if (
                        not allow_model_policy_change
                        or existing.model_copy(
                            update={"model_processing_policy": workspace.model_processing_policy}
                        )
                        != workspace
                    ):
                        raise Conflict(
                            "Workspace already exists with different owner/configuration"
                        )
                    payload = canonical(workspace)
                    self.db.execute(
                        "UPDATE workspaces SET payload=?,digest=? WHERE workspace_id=? AND owner_id=?",
                        (payload, digest(payload.encode()), workspace.workspace_id, actor),
                    )
                return
            payload = canonical(workspace)
            self.db.execute(
                "INSERT INTO workspaces VALUES(?,?,?,?)",
                (workspace.workspace_id, workspace.owner_id, payload, digest(payload.encode())),
            )

    def _workspace(self, scope: AccessScope) -> None:
        row = self.db.execute(
            "SELECT payload,digest FROM workspaces WHERE workspace_id=?", (scope.workspace_id,)
        ).fetchone()
        workspace = self._decode(row, Workspace)
        if workspace.owner_id != scope.actor_id:
            raise AccessDenied("Actor has no workspace access")

    def authorize(self, scope: AccessScope) -> None:
        self._workspace(scope)
        row = self.db.execute(
            "SELECT revision FROM projects WHERE workspace_id=? AND project_id=?",
            (scope.workspace_id, scope.project_id),
        ).fetchone()
        if row is None:
            raise AccessDenied("Project not available in this workspace")

    def _insert(
        self, table: str, scope: AccessScope, keys: tuple[object, ...], record: Frozen
    ) -> None:
        if table not in {
            "revisions",
            "source_documents",
            "source_versions",
            "source_anchors",
            "snapshots",
        }:
            raise ValueError("Invalid internal table")
        payload = canonical(record)
        values = (scope.workspace_id, scope.project_id, *keys, payload, digest(payload.encode()))
        marks = ",".join("?" for _ in values)
        self.db.execute(f"INSERT INTO {table} VALUES({marks})", values)

    def create_project(self, scope: AccessScope, project: Project) -> None:
        with self.db.transaction():
            self._workspace(scope)
            if (project.workspace_id, project.project_id, project.revision) != (
                scope.workspace_id,
                scope.project_id,
                1,
            ):
                raise ValueError("Initial project must match scope and start at revision one")
            if self.db.execute(
                "SELECT 1 FROM projects WHERE workspace_id=? AND project_id=?",
                (scope.workspace_id, scope.project_id),
            ).fetchone():
                raise Conflict("Project already exists")
            self._references(scope, project)
            self.db.execute(
                "INSERT INTO projects VALUES(?,?,1)", (scope.workspace_id, scope.project_id)
            )
            self._insert("revisions", scope, (1,), project)

    def project(self, scope: AccessScope, revision: int | None = None) -> Project:
        self.authorize(scope)
        if revision is None:
            revision = self.db.execute(
                "SELECT revision FROM projects WHERE workspace_id=? AND project_id=?",
                (scope.workspace_id, scope.project_id),
            ).fetchone()[0]
        row = self.db.execute(
            "SELECT payload,digest FROM revisions WHERE workspace_id=? AND project_id=? AND revision=?",
            (scope.workspace_id, scope.project_id, revision),
        ).fetchone()
        return self._decode(row, Project)

    def save_project(self, scope: AccessScope, project: Project, expected_revision: int) -> None:
        with self.db.transaction():
            self.authorize(scope)
            if (project.workspace_id, project.project_id, project.revision) != (
                scope.workspace_id,
                scope.project_id,
                expected_revision + 1,
            ):
                raise ValueError("Revision must match scope and increment exactly once")
            self._references(scope, project)
            changed = self.db.execute(
                "UPDATE projects SET revision=? WHERE workspace_id=? AND project_id=? AND revision=?",
                (project.revision, scope.workspace_id, scope.project_id, expected_revision),
            ).rowcount
            if changed != 1:
                raise Conflict("Working revision changed; reload before saving")
            self._insert("revisions", scope, (project.revision,), project)

    def add_source(self, scope: AccessScope, source: SourceRecord) -> None:
        with self.db.transaction():
            self.authorize(scope)
            if (source.workspace_id, source.project_id) != (scope.workspace_id, scope.project_id):
                raise AccessDenied("Source outside selected project")
            if self.db.execute(
                "SELECT 1 FROM source_documents WHERE workspace_id=? AND project_id=? AND document_id=?",
                (scope.workspace_id, scope.project_id, source.document_id),
            ).fetchone():
                raise Conflict("Source identity already exists")
            self._insert("source_documents", scope, (source.document_id,), source)

    def source(self, scope: AccessScope, document_id: str) -> SourceRecord:
        self.authorize(scope)
        row = self.db.execute(
            "SELECT payload,digest FROM source_documents WHERE workspace_id=? AND project_id=? AND document_id=?",
            (scope.workspace_id, scope.project_id, document_id),
        ).fetchone()
        return self._decode(row, SourceRecord)

    def add_version(
        self,
        scope: AccessScope,
        version: SourceVersion,
        anchors: tuple[SourceAnchor, ...],
        admitted: bool = False,
    ) -> None:
        with self.db.transaction():
            source = self.source(scope, version.document.document_id)
            if version.document.project_id != scope.project_id:
                raise AccessDenied("Source version outside selected project")
            current = (
                self.db.execute(
                    "SELECT MAX(version) FROM source_versions WHERE workspace_id=? AND project_id=? AND document_id=?",
                    (scope.workspace_id, scope.project_id, source.document_id),
                ).fetchone()[0]
                or 0
            )
            if version.document.version != current + 1:
                raise Conflict("Source versions must append without rewriting history")
            if version.text is not None and anchors != expected_anchors(version):
                raise ValueError(
                    "Source version must preserve its complete deterministic anchor set"
                )
            for anchor in anchors:
                validate_anchor(anchor, version)
            if len({a.anchor_id for a in anchors}) != len(anchors):
                raise ValueError("Duplicate anchors")
            self._insert(
                "source_versions", scope, (source.document_id, version.document.version), version
            )
            for anchor in anchors:
                self._insert(
                    "source_anchors",
                    scope,
                    (source.document_id, version.document.version, anchor.anchor_id),
                    anchor,
                )
            self.db.execute(
                "INSERT INTO admissions VALUES(?,?,?,?,?)",
                (
                    scope.workspace_id,
                    scope.project_id,
                    source.document_id,
                    version.document.version,
                    int(admitted),
                ),
            )

    def version(
        self, scope: AccessScope, document_id: str, version: int | None = None
    ) -> SourceVersion:
        self.authorize(scope)
        if version is None:
            version = self.db.execute(
                "SELECT MAX(version) FROM source_versions WHERE workspace_id=? AND project_id=? AND document_id=?",
                (scope.workspace_id, scope.project_id, document_id),
            ).fetchone()[0]
        row = self.db.execute(
            "SELECT payload,digest FROM source_versions WHERE workspace_id=? AND project_id=? AND document_id=? AND version=?",
            (scope.workspace_id, scope.project_id, document_id, version),
        ).fetchone()
        return self._decode(row, SourceVersion)

    def admitted(self, scope: AccessScope, document_id: str, version: int) -> None:
        self.authorize(scope)
        row = self.db.execute(
            "SELECT admitted FROM admissions WHERE workspace_id=? AND project_id=? AND document_id=? AND version=?",
            (scope.workspace_id, scope.project_id, document_id, version),
        ).fetchone()
        if row is None or row[0] != 1:
            raise AccessDenied("Source version is not admitted in this project")

    def set_admission(
        self, scope: AccessScope, document_id: str, version: int, admitted: bool
    ) -> None:
        with self.db.transaction():
            self.version(scope, document_id, version)
            self.db.execute(
                "UPDATE admissions SET admitted=? WHERE workspace_id=? AND project_id=? AND document_id=? AND version=?",
                (int(admitted), scope.workspace_id, scope.project_id, document_id, version),
            )

    def get_anchor(
        self, scope: AccessScope, reference: SourceReference, require_admission: bool = True
    ) -> SourceAnchor:
        self.authorize(scope)
        if require_admission:
            self.admitted(scope, reference.document_id, reference.version)
        row = self.db.execute(
            "SELECT payload,digest FROM source_anchors WHERE workspace_id=? AND project_id=? AND document_id=? AND version=? AND anchor_id=?",
            (
                scope.workspace_id,
                scope.project_id,
                reference.document_id,
                reference.version,
                reference.anchor_id,
            ),
        ).fetchone()
        anchor = self._decode(row, SourceAnchor)
        validate_anchor(anchor, self.version(scope, reference.document_id, reference.version))
        return anchor

    def _references(self, scope: AccessScope, project: Project) -> None:
        for obj in project.objects:
            from domain.models import ResearchRecord

            for reference in (
                obj.source_refs
                + tuple(ref for check in obj.checks for ref in check.source_refs)
                + tuple(
                    ref
                    for disposition in obj.support_dispositions
                    for ref in disposition.source_refs
                )
                + tuple(ref for statement in obj.statements for ref in statement.source_refs)
                + (
                    tuple(ref for field in obj.payload.fields for ref in field.source_refs)
                    if isinstance(obj.payload, ResearchRecord)
                    else ()
                )
            ):
                self.get_anchor(scope, reference)

    def save_snapshot(self, scope: AccessScope, stored: StoredSnapshot) -> None:
        self._save_snapshot(scope, stored, require_admission=True)

    def _save_snapshot(
        self, scope: AccessScope, stored: StoredSnapshot, require_admission: bool
    ) -> None:
        with self.db.transaction():
            self.authorize(scope)
            snapshot = stored.snapshot
            if snapshot.project != self.project(scope, snapshot.project.revision):
                raise ValueError("Snapshot does not match persisted historical project revision")
            for doc in snapshot.documents:
                if self.version(scope, doc.document_id, doc.version).document != doc:
                    raise ValueError("Snapshot does not match persisted source version")
                if require_admission:
                    self.admitted(scope, doc.document_id, doc.version)
            if stored.assessment:
                for finding in stored.assessment.findings:
                    for ref in finding.source_refs:
                        self.get_anchor(scope, ref, require_admission)
            if self.db.execute(
                "SELECT 1 FROM snapshots WHERE workspace_id=? AND project_id=? AND snapshot_id=?",
                (scope.workspace_id, scope.project_id, snapshot.snapshot_id),
            ).fetchone():
                raise Conflict("Historical snapshot is immutable")
            self._insert(
                "snapshots", scope, (snapshot.snapshot_id, snapshot.project.revision), stored
            )

    def snapshot(self, scope: AccessScope, snapshot_id: str) -> StoredSnapshot:
        self.authorize(scope)
        row = self.db.execute(
            "SELECT payload,digest FROM snapshots WHERE workspace_id=? AND project_id=? AND snapshot_id=?",
            (scope.workspace_id, scope.project_id, snapshot_id),
        ).fetchone()
        return self._decode(row, StoredSnapshot)

    def _all(self, scope: AccessScope, table: str, order: str, model: type[T]) -> tuple[T, ...]:
        rows = self.db.execute(
            f"SELECT payload,digest FROM {table} WHERE workspace_id=? AND project_id=? ORDER BY {order}",
            (scope.workspace_id, scope.project_id),
        ).fetchall()
        return tuple(self._decode(row, model) for row in rows)

    def export(self, scope: AccessScope, include_source_text: bool = False) -> str:
        with self.db.transaction():
            self.authorize(scope)
            versions = []
            for version in self._all(
                scope, "source_versions", "document_id,version", SourceVersion
            ):
                row = self.db.execute(
                    "SELECT admitted FROM admissions WHERE workspace_id=? AND project_id=? AND document_id=? AND version=?",
                    (
                        scope.workspace_id,
                        scope.project_id,
                        version.document.document_id,
                        version.document.version,
                    ),
                ).fetchone()
                if version.text is not None and (not include_source_text or row[0] != 1):
                    data = version.model_dump()
                    data.update(text=None, text_presence="external")
                    version = SourceVersion.model_validate(data)
                versions.append(version)
            admissions = tuple(
                Admission(document_id=d, version=v, admitted=bool(a))
                for d, v, a in self.db.execute(
                    "SELECT document_id,version,admitted FROM admissions WHERE workspace_id=? AND project_id=? ORDER BY document_id,version",
                    (scope.workspace_id, scope.project_id),
                ).fetchall()
            )
            bundle = ProjectBundle(
                workspace_id=scope.workspace_id,
                project_id=scope.project_id,
                revisions=self._all(scope, "revisions", "revision", Project),
                sources=self._all(scope, "source_documents", "document_id", SourceRecord),
                versions=tuple(versions),
                anchors=self._all(
                    scope, "source_anchors", "document_id,version,anchor_id", SourceAnchor
                ),
                admissions=admissions,
                snapshots=self._all(scope, "snapshots", "snapshot_id", StoredSnapshot),
            )
            return canonical(bundle)

    def import_bundle(self, scope: AccessScope, serialized: str) -> None:
        bundle = ProjectBundle.model_validate_json(serialized)
        if (bundle.workspace_id, bundle.project_id) != (scope.workspace_id, scope.project_id):
            raise AccessDenied("Bundle scope differs from target")
        with self.db.transaction():
            self._workspace(scope)
            if self.db.execute(
                "SELECT 1 FROM projects WHERE workspace_id=? AND project_id=?",
                (scope.workspace_id, scope.project_id),
            ).fetchone():
                raise Conflict("Import cannot overwrite an existing project")
            # Create the head within this transaction; insert immutable revisions after source validation.
            self.db.execute(
                "INSERT INTO projects VALUES(?,?,1)", (scope.workspace_id, scope.project_id)
            )
            for source in bundle.sources:
                self.add_source(scope, source)
            for version in sorted(
                bundle.versions, key=lambda v: (v.document.document_id, v.document.version)
            ):
                matching = tuple(
                    a
                    for a in bundle.anchors
                    if (a.document_id, a.version)
                    == (version.document.document_id, version.document.version)
                )
                matching = tuple(sorted(matching, key=lambda a: (a.start, a.end, a.anchor_id)))
                self.add_version(scope, version, matching, True)
            self._references(scope, bundle.revisions[0])
            self._insert("revisions", scope, (1,), bundle.revisions[0])
            for project in bundle.revisions[1:]:
                self.save_project(scope, project, project.revision - 1)
            for snapshot in bundle.snapshots:
                self._save_snapshot(scope, snapshot, require_admission=False)
            for admission in bundle.admissions:
                self.set_admission(
                    scope, admission.document_id, admission.version, admission.admitted
                )
