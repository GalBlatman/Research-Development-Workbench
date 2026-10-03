import json
from dataclasses import asdict
from fractions import Fraction
from typing import Any
from uuid import uuid4

from domain.application import (
    AddSource,
    CandidateReview,
    ContextPacket,
    CreateProject,
    EditProject,
    Interpretation,
    Passage,
)
from domain.locations import anchors
from domain.models import (
    Adoption,
    EvaluationSnapshot,
    EvidenceState,
    Freshness,
    Origin,
    Project,
    ProjectObject,
    ReviewSummary,
    Scope,
    SourceReference,
    Workspace,
    accept_content,
)
from domain.presentation import PolicyResult
from domain.sources import AccessScope, ProjectBundle, SourceRecord, SourceRole, StoredSnapshot
from model_adapters.fake import FakeModel, FixtureVerifier, ModelAdapter, OutputVerifier
from persistence.repository import Conflict, Repository
from policy_engine.engine import evaluate
from policy_engine.manifest import Manifest
from services.sources import SourceService


class InvalidModelOutput(ValueError):
    pass


def policy_view(value: Any) -> Any:
    if isinstance(value, Fraction):
        return {"numerator": value.numerator, "denominator": value.denominator}
    if isinstance(value, dict):
        return {key: policy_view(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [policy_view(item) for item in value]
    return value


class Workbench:
    def __init__(
        self,
        repository: Repository,
        sources: SourceService,
        manifest: Manifest,
        adapter: ModelAdapter | None = None,
        verifier: OutputVerifier | None = None,
    ):
        self.repository, self.sources, self.manifest = repository, sources, manifest
        self.adapter = adapter or FakeModel()
        self.verifier = verifier or FixtureVerifier()
        self.actor, self.workspace = "local-owner", "local-workspace"
        repository.register_workspace(
            self.actor,
            Workspace(
                workspace_id=self.workspace,
                owner_id=self.actor,
                access_policy="loopback single owner; no authentication",
                model_processing_policy="fake only; no external processing",
                storage_policy="explicit private runtime",
            ),
        )

    def scope(self, project_id: str) -> AccessScope:
        return AccessScope(actor_id=self.actor, workspace_id=self.workspace, project_id=project_id)

    def bundle(self, project_id: str, text: bool = False) -> ProjectBundle:
        return ProjectBundle.model_validate_json(
            self.repository.export(self.scope(project_id), text)
        )

    def context(self, project_id: str) -> ContextPacket:
        scope = self.scope(project_id)
        bundle = self.bundle(project_id, True)
        current = {v.document.document_id: v for v in bundle.versions}
        admitted = {(a.document_id, a.version) for a in bundle.admissions if a.admitted}
        passages, exclusions = [], []
        for source in bundle.sources:
            version = current[source.document_id]
            key = (source.document_id, version.document.version)
            if key not in admitted:
                exclusions.append(f"{source.title}: not admitted")
                continue
            if version.text is None:
                exclusions.append(
                    f"{source.title}: {version.extraction_state}/{version.text_presence}"
                )
                continue
            for anchor in anchors(version):
                self.repository.get_anchor(
                    scope,
                    SourceReference(
                        document_id=source.document_id,
                        version=version.document.version,
                        anchor_id=anchor.anchor_id,
                    ),
                )
                passages.append(
                    Passage(
                        source=source, anchor=anchor, text=version.text[anchor.start : anchor.end]
                    )
                )
        if sum(len(p.text) for p in passages) > 100000:
            raise ValueError("Fake context limit exceeded; narrow the supplied packet")
        return ContextPacket(
            project=self.repository.project(scope),
            passages=tuple(passages),
            exclusions=tuple(exclusions),
        )

    def _proposal(self, context: ContextPacket, revision: int) -> ProjectObject:
        try:
            output = Interpretation.model_validate(self.adapter.interpret(context))
            self.verifier.interpretation(context, output)
        except (ValueError, TypeError) as exc:
            raise InvalidModelOutput(
                "Invalid fake-model interpretation; no proposal was saved"
            ) from exc
        return ProjectObject(
            object_id=uuid4().hex,
            project_id=context.project.project_id,
            revision=revision,
            payload=output.brief,
            origin=Origin.INFERENCE,
            adoption=Adoption.PROPOSED,
            evidence_state=EvidenceState.UNINSPECTED,
            generated_by_run_id="fake-interpretation-v1",
        )

    def create(self, request: CreateProject) -> dict[str, Any]:
        if not request.idea.strip() or not request.title.strip():
            raise ValueError("Title and idea must contain text")
        identifier = uuid4().hex
        scope = self.scope(identifier)
        with self.repository.db.transaction():
            project = Project(
                project_id=identifier,
                workspace_id=self.workspace,
                title=request.title,
                revision=1,
                route=request.route,
                stage=request.stage,
            )
            self.repository.create_project(scope, project)
            source = SourceRecord(
                document_id=uuid4().hex,
                workspace_id=self.workspace,
                project_id=identifier,
                title="Original idea",
                source_kind="pasted_original",
                role=SourceRole.DRAFT,
                media_type="text/plain",
                rights_declaration="User authorized local processing of their original text",
            )
            self.sources.paste(scope, source, request.idea)
            self.repository.set_admission(scope, source.document_id, 1, True)
            proposal = self._proposal(self.context(identifier), 2)
            updated = Project.model_validate(
                {**project.model_dump(), "revision": 2, "objects": (proposal,)}
            )
            self.repository.save_project(scope, updated, 1)
        return self.view(identifier)

    def _current(self, project_id: str, expected: int) -> Project:
        project = self.repository.project(self.scope(project_id))
        if project.revision != expected:
            raise Conflict("Working revision changed; reload before saving")
        return project

    def edit(self, project_id: str, request: EditProject) -> dict[str, Any]:
        if not request.idea.strip():
            raise ValueError("Idea must contain text")
        scope = self.scope(project_id)
        with self.repository.db.transaction():
            project = self._current(project_id, request.expected_revision)
            draft = next(
                source.document_id
                for source in self.bundle(project_id).sources
                if source.role == SourceRole.DRAFT
            )
            previous = self.repository.version(scope, draft)
            version = self.sources.append(
                scope, draft, previous.document.version + 1, request.idea.encode("utf-8")
            )
            self.repository.set_admission(scope, draft, version.document.version, True)
            changed = tuple(
                ProjectObject.model_validate(
                    {
                        **obj.model_dump(),
                        "freshness": Freshness.AFFECTED,
                        "revision": project.revision + 1,
                    }
                )
                for obj in project.objects
            )
            updated = Project.model_validate(
                {**project.model_dump(), "revision": project.revision + 1, "objects": changed}
            )
            self.repository.save_project(scope, updated, project.revision)
        return self.view(project_id)

    def add_source(self, project_id: str, request: AddSource) -> dict[str, Any]:
        if not request.attribution.strip() or not request.text.strip():
            raise ValueError("Source text and attribution must contain text")
        scope = self.scope(project_id)
        with self.repository.db.transaction():
            project = self._current(project_id, request.expected_revision)
            if len(self.bundle(project_id).sources) >= 20:
                raise ValueError("Local slice limit: 20 sources per project")
            source = SourceRecord(
                document_id=uuid4().hex,
                workspace_id=self.workspace,
                project_id=project_id,
                title=request.title,
                attribution=request.attribution,
                source_kind="pasted_excerpt",
                role=SourceRole.LITERATURE,
                media_type="text/plain",
                rights_declaration="User authorized local processing; attribution is user-reported",
            )
            self.sources.paste(scope, source, request.text)
            self.repository.set_admission(scope, source.document_id, 1, request.admitted)
            updated = Project.model_validate(
                {**project.model_dump(), "revision": project.revision + 1}
            )
            self.repository.save_project(scope, updated, project.revision)
        return self.view(project_id)

    def accept(self, project_id: str, object_id: str, expected: int) -> dict[str, Any]:
        with self.repository.db.transaction():
            project = self._current(project_id, expected)
            if object_id not in {o.object_id for o in project.objects}:
                raise ValueError("Proposal not found in this project")
            objects = tuple(
                accept_content(o, project.revision + 1) if o.object_id == object_id else o
                for o in project.objects
            )
            updated = Project.model_validate(
                {**project.model_dump(), "revision": project.revision + 1, "objects": objects}
            )
            self.repository.save_project(self.scope(project_id), updated, project.revision)
        return self.view(project_id)

    def run(self, project_id: str, expected: int, fixture: str) -> dict[str, Any]:
        scope = self.scope(project_id)
        with self.repository.db.transaction():
            project = self._current(project_id, expected)
            context = self.context(project_id)
            versions = {(p.source.document_id, p.anchor.version) for p in context.passages}
            documents = tuple(
                self.repository.version(scope, d, v).document for d, v in sorted(versions)
            )
            snapshot = EvaluationSnapshot(
                snapshot_id=uuid4().hex,
                project=project,
                documents=documents,
                policy_version=self.manifest.version,
                policy_sha256=self.manifest.canonical_sha256,
                policy_manifest_sha256=self.manifest.sha256,
                policy_implementation_version=self.manifest.implementation_version,
                scope=Scope.INITIAL_SCREEN,
                model_configuration=self.adapter.configuration,
            )
            try:
                candidate = CandidateReview.model_validate(
                    self.adapter.assess(context, snapshot, fixture)
                )
                assessment = self.verifier.verify(context, snapshot, fixture, candidate)
                evaluate(assessment, self.manifest)
            except (ValueError, TypeError) as exc:
                raise InvalidModelOutput(
                    "Invalid fake-model evaluation: " + str(exc).split("\n")[0]
                ) from exc
            # Recheck scoped sources and revision at publication, not merely at intake.
            self._current(project_id, expected)
            self.repository.save_snapshot(
                scope,
                StoredSnapshot(snapshot=snapshot, assessment=assessment, review=candidate.summary),
            )
        return self.review(project_id, snapshot.snapshot_id)

    def review(self, project_id: str, snapshot_id: str) -> dict[str, Any]:
        stored = self.repository.snapshot(self.scope(project_id), snapshot_id)
        if stored.assessment is None or stored.review is None:
            raise ValueError("Snapshot has no application review")
        evaluation = evaluate(stored.assessment, self.manifest)
        result = policy_view(asdict(evaluation))
        for name in (
            "idea_uncapped",
            "idea",
            "study",
            "project_uncapped",
            "project_before_caps",
            "project",
        ):
            result[name]["displayed"] = getattr(evaluation, name).displayed
        return {
            "snapshot": stored.snapshot.model_dump(
                mode="json", exclude={"documents": {"__all__": {"original_storage_reference"}}}
            ),
            "coverage": [
                {
                    "document_id": doc.document_id,
                    "title": self.repository.source(self.scope(project_id), doc.document_id).title,
                    "version": doc.version,
                    "state": self.repository.version(
                        self.scope(project_id), doc.document_id, doc.version
                    ).extraction_state,
                    "anchors": [
                        a.model_dump(mode="json")
                        for a in anchors(
                            self.repository.version(
                                self.scope(project_id), doc.document_id, doc.version
                            )
                        )
                    ],
                    "note": "Provided to fake fixture; no semantic source inspection.",
                }
                for doc in stored.snapshot.documents
            ],
            "summary": stored.review.model_dump(mode="json"),
            "assessment": stored.assessment.model_dump(mode="json", exclude={"snapshot"}),
            "policy": PolicyResult.model_validate(result).model_dump(mode="json"),
            "stale": self.repository.project(self.scope(project_id)).revision
            != stored.snapshot.project.revision,
        }

    def view(self, project_id: str) -> dict[str, Any]:
        bundle = self.bundle(project_id, True)
        latest = {v.document.document_id: v for v in bundle.versions}
        admissions = {(a.document_id, a.version): a.admitted for a in bundle.admissions}
        sources = [
            {
                "source": s.model_dump(mode="json"),
                "version": latest[s.document_id].document.version,
                "state": latest[s.document_id].extraction_state,
                "admitted": admissions[(s.document_id, latest[s.document_id].document.version)],
                "text": latest[s.document_id].text,
                "anchors": [
                    a.model_dump(mode="json")
                    for a in bundle.anchors
                    if a.document_id == s.document_id
                    and a.version == latest[s.document_id].document.version
                ],
            }
            for s in bundle.sources
        ]
        return {
            "project": bundle.revisions[-1].model_dump(mode="json"),
            "sources": sources,
            "reviews": [
                {"snapshot_id": s.snapshot.snapshot_id, "revision": s.snapshot.project.revision}
                for s in bundle.snapshots
                if s.review is not None
            ],
        }

    def source(
        self, project_id: str, document_id: str, version: int, anchor_id: str
    ) -> dict[str, Any]:
        scope = self.scope(project_id)
        anchor = self.repository.get_anchor(
            scope, SourceReference(document_id=document_id, version=version, anchor_id=anchor_id)
        )
        record = self.repository.version(scope, document_id, version)
        if record.text is None:
            raise ValueError("Source text unavailable")
        return {
            "anchor": anchor.model_dump(mode="json"),
            "text": record.text[anchor.start : anchor.end],
        }

    def export(self, project_id: str, format: str) -> str:
        bundle = self.bundle(project_id)
        reviews = [
            self.review(project_id, s.snapshot.snapshot_id)
            for s in bundle.snapshots
            if s.review is not None
        ]
        if format == "json":
            # Public application export excludes originals, source text, opaque storage keys.
            safe = bundle.model_dump(
                mode="json",
                exclude={
                    "versions": {
                        "__all__": {"original": True, "document": {"original_storage_reference"}}
                    },
                    "snapshots": True,
                },
            )
            return json.dumps(
                {"schema_version": "rdw-app-1", "project_history": safe, "reviews": reviews},
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        if format != "markdown":
            raise ValueError("Supported exports: markdown, json")
        lines = [
            "# " + bundle.revisions[-1].title,
            "",
            "Fake-model local slice; no scientific validation.",
            "",
            f"Working revision: {bundle.revisions[-1].revision}",
        ]
        for review in reviews:
            summary = ReviewSummary.model_validate(review["summary"])
            lines.extend(
                [
                    "",
                    "## Review " + review["snapshot"]["snapshot_id"],
                    "",
                    summary.disclaimer,
                    "",
                    "Contribution to preserve: " + summary.contribution,
                    "",
                    "Principal obstacle: " + summary.obstacle,
                    "",
                    "Next action: " + summary.next_action,
                    "",
                    "Deliverable: " + summary.deliverable,
                    "",
                    "Limitations: " + "; ".join(summary.limitations),
                    "",
                    "Outcome branches: " + "; ".join(summary.outcome_branches),
                    "",
                    "```json",
                    json.dumps(
                        {"assessment": review["assessment"], "policy": review["policy"]},
                        ensure_ascii=False,
                        indent=2,
                    ),
                    "```",
                ]
            )
        return "\n".join(lines) + "\n"
