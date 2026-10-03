import json
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from domain.models import (
    Adoption,
    Dependency,
    EvidenceState,
    Freshness,
    Origin,
    Project,
    ProjectObject,
    ResearchRecord,
    SourceReference,
    SupportDisposition,
    UserAction,
)
from domain.research import (
    AFFECTED,
    CHOICES,
    DIMENSIONS,
    FIELDS,
    WORKSPACES,
    DecisionRequest,
    DevelopRequest,
    RecordRequest,
    SettingsRequest,
    WorkspaceProposal,
    WorkspaceTask,
    validate_record,
)
from model_adapters.runtime import ProviderFailure, provider_session
from persistence.repository import Conflict
from services.exporting import sanitize_export

if TYPE_CHECKING:
    from services.workbench import Workbench


def workspace_of(obj: ProjectObject) -> str:
    if isinstance(obj.payload, ResearchRecord):
        return obj.payload.workspace
    return {
        "brief": "Brief",
        "question": "Brief",
        "construct": "Argument",
        "claim": "Argument",
        "study": "Study",
        "comparison": "Alternatives",
    }[obj.payload.kind]


def dependencies(project: Project, keys: tuple[str, ...]) -> tuple[Dependency, ...]:
    return tuple(
        Dependency(
            key=k,
            version=project.dependency_versions.get(k, 0),
            reason="Explicit object dependency or specification 12.2 conservative dependency group",
        )
        for k in sorted(set(keys))
    )


def identity(project: Project, object_id: str) -> str:
    """Stable logical identity; resolve pre-repair records through replacement lineage."""
    objects = {o.object_id: o for o in project.objects}
    seen: set[str] = set()
    while object_id in objects and object_id not in seen:
        seen.add(object_id)
        obj = objects[object_id]
        if obj.dependency_identity:
            return obj.dependency_identity
        if obj.target_object_id is None:
            break
        object_id = obj.target_object_id
    return object_id


def object_keys(project: Project, object_id: str) -> tuple[str, ...]:
    logical = identity(project, object_id)
    # Keep legacy UUID-keyed snapshots resolvable without rewriting their metadata.
    aliases = {logical, object_id}
    aliases.update(
        o.object_id for o in project.objects if identity(project, o.object_id) == logical
    )
    return tuple("object:" + i for i in sorted(aliases))


def propagate(project: Project, versions: dict[str, int]) -> dict[str, int]:
    """Propagate this change through explicit dependencies, once per logical object."""
    versions = dict(versions)
    visited: set[str] = set()
    while True:
        affected = [
            o
            for o in project.objects
            if o.adoption not in (Adoption.REJECTED, Adoption.SUPERSEDED)
            and identity(project, o.object_id) not in visited
            and any(
                versions.get(d.key, 0) != project.dependency_versions.get(d.key, 0)
                for d in o.dependencies
            )
        ]
        if not affected:
            return versions
        for obj in affected:
            visited.add(identity(project, obj.object_id))
            for key in object_keys(project, obj.object_id):
                if versions.get(key, 0) == project.dependency_versions.get(key, 0):
                    versions[key] = versions.get(key, 0) + 1


def changed(
    project: Project, group: str, object_id: str | None = None, wording: bool = False
) -> dict[str, int]:
    versions = dict(project.dependency_versions)
    if not wording:
        keys = list(AFFECTED.get(group, (group,)))
        if object_id:
            keys.extend(object_keys(project, object_id))
        for key in set(keys):
            versions[key] = versions.get(key, 0) + 1
    return propagate(project, versions)


def review_keys(project: Project, workspace: str | None) -> tuple[str, ...]:
    """Track the logical records actually available within this assessment scope."""
    keys: set[str] = set((workspace,) if workspace else tuple(FIELDS))
    if workspace in ("Brief", "Usefulness"):
        keys.update(("Literature", "Argument"))
    if workspace:
        keys.update(
            other
            for other, dims in DIMENSIONS.items()
            if set(dims) & set(DIMENSIONS.get(workspace, ()))
        )
    for obj in project.objects:
        if obj.adoption in (Adoption.REJECTED, Adoption.SUPERSEDED):
            continue
        related = workspace is None or workspace_of(obj) == workspace
        if workspace is not None:
            related = related or bool(
                set(DIMENSIONS.get(workspace, ())) & set(DIMENSIONS.get(workspace_of(obj), ()))
            )
            related = related or (
                workspace in ("Brief", "Usefulness")
                and workspace_of(obj) in ("Literature", "Argument")
            )
        if related:
            keys.add("object:" + identity(project, obj.object_id))
            keys.update(d.key for d in obj.dependencies)
    return tuple(sorted(keys))


def invalidate(
    objects: tuple[ProjectObject, ...], versions: dict[str, int], exclude: tuple[str, ...] = ()
) -> tuple[ProjectObject, ...]:
    return tuple(
        o.model_copy(update={"freshness": Freshness.AFFECTED})
        if o.object_id not in exclude
        and o.adoption not in (Adoption.REJECTED, Adoption.SUPERSEDED)
        and any(versions.get(d.key, 0) != d.version for d in o.dependencies)
        else o
        for o in objects
    )


def record_origin(record: ResearchRecord) -> Origin:
    if any(f.origin in (Origin.INFERENCE, Origin.SUGGESTION) for f in record.fields):
        return Origin.INFERENCE
    return Origin.USER


def preserve_field_origins(old: ProjectObject | None, record: ResearchRecord) -> ResearchRecord:
    if old is None or not isinstance(old.payload, ResearchRecord):
        return record
    previous = {f.key: f for f in old.payload.fields}
    fields = tuple(
        previous[f.key]
        if f.key in previous
        and f.model_dump(exclude={"origin"}) == previous[f.key].model_dump(exclude={"origin"})
        else f
        for f in record.fields
    )
    return record.model_copy(update={"fields": fields})


class ResearchService:
    def __init__(self, workbench: "Workbench"):
        self.w = workbench

    def catalog(self, project_id: str) -> dict[str, Any]:
        project = self.w.repository.project(self.w.scope(project_id))
        fields = {
            k: {
                name: label
                for name, label in values.items()
                if not (
                    project.route != "EXPLAIN"
                    and k in ("Brief", "Argument")
                    and name in ("account", "sequence")
                )
            }
            for k, values in FIELDS.items()
        }
        return {
            "workspaces": WORKSPACES,
            "fields": fields,
            "choices": CHOICES,
            "targeted_workspaces": tuple(DIMENSIONS),
            "note": "Admitted packet only; absence of a hit never establishes absence in the literature. Acceptance is representation, not evidence verification.",
        }

    def _refs(self, project_id: str, request: RecordRequest) -> tuple[Any, ...]:
        refs = tuple(
            dict.fromkeys(
                request.source_refs + tuple(r for f in request.record.fields for r in f.source_refs)
            )
        )
        for ref in refs:
            self.w.repository.get_anchor(self.w.scope(project_id), ref)
        if (
            request.record.workspace == "Literature"
            and any(f.key == "source_claim" and f.text for f in request.record.fields)
            and not refs
        ):
            raise ValueError("A source claim needs an admitted supporting passage")
        if request.record.workspace == "Literature" and any(
            f.key == "source_claim" and f.text for f in request.record.fields
        ):
            if any(
                self.w.repository.source(self.w.scope(project_id), r.document_id).role
                != "literature"
                for r in refs
            ):
                raise ValueError(
                    "Attributed source claims require literature passages, not project assertions"
                )
        return refs

    def save(self, project_id: str, request: RecordRequest) -> dict[str, Any]:
        with self.w.repository.db.transaction():
            project = self.w._current(project_id, request.expected_revision)
            if len(project.objects) >= 200:
                raise ValueError("Project record limit reached; narrow the working record")
            validate_record(request.record, project.route)
            if any(f.origin != Origin.USER for f in request.record.fields):
                raise ValueError(
                    "Manual edits must be user-authored, not claimed model/source verification"
                )
            refs = self._refs(project_id, request)
            ids = {o.object_id for o in project.objects}
            if any(i not in ids for i in request.depends_on or ()):
                raise ValueError("Dependency outside this project")
            old = next((o for o in project.objects if o.object_id == request.object_id), None)
            if request.object_id and (old is None or workspace_of(old) != request.record.workspace):
                raise ValueError("Edited record unavailable in this workspace")
            if old and old.adoption in (Adoption.SUPERSEDED, Adoption.REJECTED):
                raise Conflict("Edit must target the current accepted head or pending proposal")
            if old:
                heads = [
                    o
                    for o in project.objects
                    if o.adoption == Adoption.ACCEPTED
                    and identity(project, o.object_id) == identity(project, old.object_id)
                ]
                if old.adoption == Adoption.ACCEPTED and any(
                    o.object_id != old.object_id for o in heads
                ):
                    raise Conflict("Accepted lineage has another current head")
                if (
                    old.adoption == Adoption.PROPOSED
                    and old.target_object_id
                    and heads
                    and all(o.object_id != old.target_object_id for o in heads)
                ):
                    raise Conflict("Proposal targets an obsolete accepted head")
            if request.change == "wording":
                if old is None or not isinstance(old.payload, ResearchRecord):
                    raise ValueError("Wording edit requires an existing typed record")
                if request.record.title.split() != old.payload.title.split():
                    raise ValueError("Wording-only cannot change the record title meaning")
                original_fields = {f.key: f for f in old.payload.fields}
                if set(original_fields) != {f.key for f in request.record.fields}:
                    raise ValueError("Wording edit cannot change field identities")
                for field in request.record.fields:
                    before = original_fields[field.key]
                    if (
                        field.state != before.state
                        or field.source_refs != before.source_refs
                        or field.claim_kind != before.claim_kind
                    ):
                        raise ValueError("Wording edit cannot change evidence or source references")
                    if (field.text or "").split() != (before.text or "").split():
                        raise ValueError(
                            "Wording-only permits presentation whitespace; changed claim wording requires a substantive edit"
                        )
                    if field.key in CHOICES and field.text != before.text:
                        raise ValueError("Wording edit cannot change a scientific choice")
                if refs != old.source_refs or request.depends_on is not None:
                    raise ValueError("Wording edit cannot change references or dependencies")
            payload = preserve_field_origins(old, request.record)
            identifier = uuid4().hex
            explicit = (
                tuple(d.key for d in old.dependencies if d.key.startswith("object:"))
                if request.depends_on is None and old
                else tuple("object:" + identity(project, i) for i in request.depends_on or ())
            )
            versions = changed(
                project,
                request.record.workspace,
                request.object_id,
                request.change == "wording",
            )
            updated = project.model_copy(
                update={"revision": project.revision + 1, "dependency_versions": versions}
            )
            record = ProjectObject(
                object_id=identifier,
                project_id=project_id,
                revision=updated.revision,
                payload=payload,
                origin=record_origin(payload),
                generated_by_run_id=old.generated_by_run_id
                if old and record_origin(payload) != Origin.USER
                else None,
                adoption=Adoption.ACCEPTED,
                evidence_state=old.evidence_state if old else EvidenceState.UNTESTED,
                source_refs=refs,
                dependencies=old.dependencies
                if old and request.change == "wording" and request.depends_on is None
                else dependencies(updated, (request.record.workspace,) + explicit),
                freshness=old.freshness
                if old and request.change == "wording" and request.depends_on is None
                else Freshness.CURRENT,
                dependency_identity=identity(project, old.object_id) if old else identifier,
                target_object_id=request.object_id,
                reason="User-authored workspace edit",
            )
            objects = tuple(
                o.model_copy(
                    update={"adoption": Adoption.SUPERSEDED, "freshness": Freshness.SUPERSEDED}
                )
                if old
                and (
                    o.object_id == old.object_id
                    or (
                        o.adoption == Adoption.ACCEPTED
                        and identity(project, o.object_id) == identity(project, old.object_id)
                    )
                )
                else o
                for o in project.objects
            )
            actions = project.actions + (
                UserAction(
                    object_id=identifier,
                    action="edited",
                    actor=self.w.actor,
                    revision=updated.revision,
                    reason="User classified change as " + request.change,
                ),
            )
            updated = updated.model_copy(
                update={
                    "objects": invalidate(objects + (record,), versions, (identifier,)),
                    "actions": actions,
                }
            )
            self.w.repository.save_project(self.w.scope(project_id), updated, project.revision)
        return self.w.view(project_id)

    def decide(self, project_id: str, object_id: str, request: DecisionRequest) -> dict[str, Any]:
        with self.w.repository.db.transaction():
            project = self.w._current(project_id, request.expected_revision)
            obj = next((o for o in project.objects if o.object_id == object_id), None)
            if obj is None or obj.adoption != Adoption.PROPOSED:
                raise ValueError("Choose a proposed suggestion in this project")
            if request.action == "accepted" and obj.freshness != Freshness.CURRENT:
                raise Conflict(
                    "Suggestion dependencies changed; request a fresh suggestion or save a manual alternative"
                )
            if request.edited_record is not None and request.action != "accepted":
                raise ValueError("Edited adoption requires acceptance")
            versions = (
                changed(project, workspace_of(obj), obj.target_object_id)
                if request.action == "accepted"
                else dict(project.dependency_versions)
            )
            updated = project.model_copy(
                update={"revision": project.revision + 1, "dependency_versions": versions}
            )
            logical = (
                identity(project, obj.target_object_id)
                if obj.target_object_id
                else identity(project, obj.object_id)
            )
            target = next((o for o in project.objects if o.object_id == obj.target_object_id), None)
            if (
                request.action == "accepted"
                and target is not None
                and target.adoption != Adoption.ACCEPTED
            ):
                raise Conflict("Suggestion targets an obsolete accepted head")
            if request.action == "accepted" and any(
                o.adoption == Adoption.ACCEPTED
                and identity(project, o.object_id) == logical
                and (target is None or o.object_id != target.object_id)
                for o in project.objects
            ):
                raise Conflict("Lineage already has another accepted head")
            retained_keys = tuple(d.key for d in obj.dependencies)
            if request.action == "accepted" and target:
                retained_keys += tuple(d.key for d in target.dependencies)
                retained_keys = tuple(
                    k for k in retained_keys if k not in object_keys(project, target.object_id)
                )
            replacement = obj.model_copy(
                update={
                    "dependency_identity": logical
                    if request.action == "accepted"
                    else identity(project, obj.object_id),
                    "adoption": Adoption(request.action),
                    "freshness": Freshness.SUPERSEDED
                    if request.action == "superseded"
                    else obj.freshness,
                    "revision": updated.revision,
                    "dependencies": dependencies(updated, retained_keys),
                }
            )
            # An edited adoption gets its own user record; untouched original suggestion remains retained.
            if request.edited_record is not None:
                validate_record(request.edited_record, project.route)
                if request.edited_record.workspace != workspace_of(obj) or any(
                    f.origin != Origin.USER for f in request.edited_record.fields
                ):
                    raise ValueError("Edited adoption must be user-authored in the same workspace")
                self._refs(
                    project_id,
                    RecordRequest(expected_revision=project.revision, record=request.edited_record),
                )
                replacement = obj.model_copy(
                    update={"adoption": Adoption.SUPERSEDED, "freshness": Freshness.SUPERSEDED}
                )
                edited = ProjectObject(
                    object_id=uuid4().hex,
                    project_id=project_id,
                    revision=updated.revision,
                    payload=preserve_field_origins(obj, request.edited_record),
                    origin=record_origin(preserve_field_origins(obj, request.edited_record)),
                    generated_by_run_id=obj.generated_by_run_id
                    if record_origin(preserve_field_origins(obj, request.edited_record))
                    != Origin.USER
                    else None,
                    adoption=Adoption.ACCEPTED,
                    evidence_state=obj.evidence_state,
                    target_object_id=obj.object_id,
                    source_refs=tuple(
                        r for f in request.edited_record.fields for r in f.source_refs
                    ),
                    dependency_identity=logical,
                    dependencies=dependencies(updated, retained_keys),
                )
            else:
                edited = None
            objects = tuple(
                replacement
                if o.object_id == object_id
                else o.model_copy(
                    update={"adoption": Adoption.SUPERSEDED, "freshness": Freshness.SUPERSEDED}
                )
                if request.action == "accepted" and o.object_id == obj.target_object_id
                else o
                for o in project.objects
            )
            if edited:
                objects += (edited,)
            updated = updated.model_copy(
                update={
                    "objects": invalidate(
                        objects, versions, (object_id,) + ((edited.object_id,) if edited else ())
                    ),
                    "actions": project.actions
                    + (
                        UserAction(
                            object_id=object_id,
                            action=request.action,
                            actor=self.w.actor,
                            revision=updated.revision,
                            reason=request.reason,
                        ),
                    ),
                }
            )
            self.w.repository.save_project(self.w.scope(project_id), updated, project.revision)
        return self.w.view(project_id)

    def settings(self, project_id: str, request: SettingsRequest) -> dict[str, Any]:
        with self.w.repository.db.transaction():
            project = self.w._current(project_id, request.expected_revision)
            group = (
                "Brief"
                if (request.route, request.stage, request.evaluation_target)
                != (project.route, project.stage, project.evaluation_target)
                else "resources"
            )
            versions = changed(project, group)
            updated = project.model_copy(
                update={
                    "revision": project.revision + 1,
                    "route": request.route,
                    "stage": request.stage,
                    "session_goal": request.session_goal,
                    "evaluation_target": request.evaluation_target,
                    "dependency_versions": versions,
                    "objects": invalidate(project.objects, versions),
                }
            )
            self.w.repository.save_project(self.w.scope(project_id), updated, project.revision)
        return self.w.view(project_id)

    def develop(
        self, project_id: str, request: DevelopRequest, operation_id: str | None = None
    ) -> dict[str, Any]:
        project = self.w._current(project_id, request.expected_revision)
        target = next((o for o in project.objects if o.object_id == request.object_id), None)
        if request.object_id and (
            target is None
            or workspace_of(target) != request.workspace
            or target.adoption in (Adoption.REJECTED, Adoption.SUPERSEDED)
        ):
            raise ValueError("Target unavailable in this workspace")
        if len(project.objects) >= 200:
            raise ValueError("Project record limit reached; narrow the working record")
        catalog = self.catalog(project_id)
        task = WorkspaceTask(
            context=self.w.context(project_id),
            workspace=request.workspace,
            target_object_id=request.object_id,
            instruction=request.instruction,
            allowed_fields=tuple(catalog["fields"][request.workspace]),
        )
        with provider_session(self.w.adapter) as ledger:
            candidate = WorkspaceProposal.model_validate(self.w.adapter.develop(task))
            if candidate.record.workspace != request.workspace:
                raise ProviderFailure("WORKSPACE_SCOPE_MISMATCH")
            validate_record(candidate.record, project.route)
            try:
                self.w._current(project_id, request.expected_revision)
            except Conflict as exc:
                exc.provider_metadata = ledger.receipt() if ledger else None
                raise
            for passage in task.context.passages:
                self.w.repository.get_anchor(
                    self.w.scope(project_id),
                    SourceReference(
                        document_id=passage.source.document_id,
                        version=passage.anchor.version,
                        anchor_id=passage.anchor.anchor_id,
                    ),
                )
            refs = tuple(dict.fromkeys(r for f in candidate.record.fields for r in f.source_refs))
            for ref in refs:
                self.w.repository.get_anchor(self.w.scope(project_id), ref)
            for grounding in candidate.result_grounding:
                field = next((f for f in candidate.record.fields if f.key == grounding.field), None)
                if field is None:
                    raise ProviderFailure("RESULT_GROUNDING_FIELD_MISMATCH")
                if grounding.existing_object_id:
                    original = next(
                        (
                            o
                            for o in project.objects
                            if o.object_id == grounding.existing_object_id
                            and o.adoption == Adoption.ACCEPTED
                        ),
                        None,
                    )
                    original_field = (
                        next(
                            (
                                f
                                for f in getattr(original.payload, "fields", ())
                                if f.key == grounding.field and f.origin == Origin.USER
                            ),
                            None,
                        )
                        if original
                        else None
                    )
                    if original_field is None or original_field.text != field.text:
                        raise ProviderFailure("FABRICATED_REPORTED_RESULT")
                for ref in grounding.source_refs:
                    self.w.repository.get_anchor(self.w.scope(project_id), ref)
            checked = self.w.verifier.workspace(task, candidate)
            for grounding in candidate.result_grounding:
                if grounding.source_refs and not grounding.existing_object_id:
                    disposition = next(
                        (d for d in checked.decisions if d.target == grounding.field), None
                    )
                    if disposition is None or disposition.disposition != "supported":
                        raise ProviderFailure("UNSUPPORTED_REPORTED_RESULT")
            refs = tuple(
                dict.fromkeys(refs + tuple(r for d in checked.decisions for r in d.source_refs))
            )
            if ledger:
                ledger.state = "SUCCEEDED"
            metadata = ledger.receipt() if ledger else None
        with self.w.repository.db.transaction():
            try:
                self.w._current(project_id, request.expected_revision)
            except Conflict as exc:
                exc.provider_metadata = metadata
                raise
            for ref in refs:
                self.w.repository.get_anchor(self.w.scope(project_id), ref)
            obj = ProjectObject(
                object_id=uuid4().hex,
                project_id=project_id,
                revision=project.revision + 1,
                payload=candidate.record,
                origin=Origin.SUGGESTION,
                adoption=Adoption.PROPOSED,
                evidence_state=EvidenceState.UNINSPECTED,
                source_refs=refs,
                provider_run=metadata,
                generated_by_run_id=metadata.run_id if metadata else "fake-workspace-v1",
                operation_id=operation_id,
                dependencies=dependencies(
                    project,
                    (request.workspace,)
                    + tuple("source:" + p.source.document_id for p in task.context.passages)
                    + (("object:" + request.object_id,) if request.object_id else ()),
                ),
                target_object_id=request.object_id,
                reason=candidate.reason
                + "; "
                + "; ".join(candidate.limitations + checked.limitations),
                support_dispositions=tuple(
                    SupportDisposition(**d.model_dump()) for d in checked.decisions
                ),
            )
            updated = project.model_copy(
                update={"revision": project.revision + 1, "objects": project.objects + (obj,)}
            )
            self.w.repository.save_project(self.w.scope(project_id), updated, project.revision)
        return self.w.view(project_id)

    def history(self, project_id: str) -> dict[str, Any]:
        bundle = self.w.bundle(project_id)
        return {
            "revisions": [p.model_dump(mode="json") for p in bundle.revisions],
            "actions": bundle.revisions[-1].actions,
            "source_versions": [
                {
                    "document_id": v.document.document_id,
                    "version": v.document.version,
                    "role": v.document.role,
                    "state": v.extraction_state,
                    "anchors": [
                        a.model_dump(mode="json")
                        for a in bundle.anchors
                        if a.document_id == v.document.document_id
                        and a.version == v.document.version
                    ],
                }
                for v in bundle.versions
            ],
            "reviews": self.w.view(project_id)["reviews"],
        }

    def historical_export(self, project_id: str, revision: int) -> str:
        bundle = self.w.bundle(project_id)
        project = self.w.repository.project(self.w.scope(project_id), revision)
        refs = tuple(r for o in project.objects for r in o.source_refs)
        versions = {(r.document_id, r.version) for r in refs}
        reviews = tuple(s for s in bundle.snapshots if s.snapshot.project.revision <= revision)
        versions |= {(d.document_id, d.version) for s in reviews for d in s.snapshot.documents}
        # Choose source versions by immutable project chronology, not later current admissions.
        return json.dumps(
            sanitize_export(
                {
                    "schema_version": "rdw-history-1",
                    "project": project.model_dump(mode="json"),
                    "reviews": [
                        s.model_dump(
                            mode="json",
                            exclude={
                                "snapshot": {
                                    "documents": {"__all__": {"original_storage_reference"}}
                                }
                            },
                        )
                        for s in reviews
                    ],
                    "source_versions": [
                        v.document.model_dump(mode="json", exclude={"original_storage_reference"})
                        for v in bundle.versions
                        if (v.document.document_id, v.document.version) in versions
                    ],
                    "anchors": [
                        a.model_dump(mode="json")
                        for a in bundle.anchors
                        if (a.document_id, a.version) in versions
                    ],
                }
            ),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )

    def source_version(self, project_id: str, document_id: str, request: Any) -> dict[str, Any]:
        with self.w.repository.db.transaction():
            project = self.w._current(project_id, request.expected_revision)
            scope = self.w.scope(project_id)
            source = self.w.repository.source(scope, document_id)
            previous = self.w.repository.version(scope, document_id)
            version = self.w.sources.append(
                scope, document_id, previous.document.version + 1, request.text.encode("utf-8")
            )
            self.w.repository.set_admission(
                scope, document_id, version.document.version, request.admitted
            )
            versions = changed(project, "Brief" if source.role == "project_draft" else "Literature")
            linked_groups = {
                workspace_of(o)
                for o in project.objects
                if o.adoption not in (Adoption.REJECTED, Adoption.SUPERSEDED)
                and any(r.document_id == document_id for r in o.source_refs)
            }
            for group in linked_groups:
                for key in AFFECTED[group]:
                    versions[key] = versions.get(key, 0) + 1
            versions["source:" + document_id] = versions.get("source:" + document_id, 0) + 1
            versions = propagate(project, versions)
            objects = tuple(
                o.model_copy(update={"freshness": Freshness.AFFECTED})
                if any(r.document_id == document_id for r in o.source_refs)
                else o
                for o in invalidate(project.objects, versions)
            )
            updated = project.model_copy(
                update={
                    "revision": project.revision + 1,
                    "objects": objects,
                    "dependency_versions": versions,
                }
            )
            self.w.repository.save_project(scope, updated, project.revision)
        return self.w.view(project_id)
