import json
from dataclasses import asdict
from fractions import Fraction
from typing import Any
from uuid import uuid4

from domain.application import (
    AddSource,
    AssessmentTask,
    CandidateReview,
    ContextPacket,
    CreateProject,
    EditProject,
    Interpretation,
    InterpretationTask,
    Passage,
)
from domain.locations import anchors
from domain.models import (
    Adoption,
    Assessment,
    EvaluationSnapshot,
    EvidenceState,
    Finding,
    Freshness,
    Origin,
    Project,
    ProjectObject,
    ResearchRecord,
    ReviewContent,
    Scope,
    SourceReference,
    Workspace,
)
from domain.research import AFFECTED, FIELDS
from domain.results import PolicyResult
from domain.sources import (
    AccessScope,
    HistoricalCoverage,
    HistoricalExclusion,
    ProjectBundle,
    SourceRecord,
    SourceRole,
    StoredSnapshot,
)
from model_adapters.contracts import ModelAdapter, OutputVerifier
from model_adapters.fake import FakeModel, FixtureVerifier
from model_adapters.runtime import ProviderFailure, provider_session, timestamp
from persistence.repository import Conflict, Repository
from policy_engine.engine import evaluate
from policy_engine.manifest import Manifest
from services.research import changed, dependencies, invalidate, review_keys
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
                model_processing_policy="bounded OpenAI packet processing authorized by runtime configuration/intake"
                if getattr(self.adapter, "provider_config", None)
                else "fake only; no external processing",
                storage_policy="explicit private runtime",
            ),
            allow_model_policy_change=True,
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
        project = self.repository.project(scope)
        refs = tuple(
            ref
            for obj in project.objects
            for ref in (
                obj.source_refs
                + tuple(r for check in obj.checks for r in check.source_refs)
                + tuple(r for statement in obj.statements for r in statement.source_refs)
            )
        )
        referenced = {(r.document_id, r.version) for r in refs}
        for ref in refs:
            self.repository.get_anchor(scope, ref)
        passages, exclusions = [], []
        for source in bundle.sources:
            latest = current[source.document_id]
            key = (source.document_id, latest.document.version)
            if key not in admitted:
                exclusions.append(f"{source.title}: not admitted")
            selected = [
                v
                for v in bundle.versions
                if v.document.document_id == source.document_id
                and (v.document.document_id, v.document.version) in admitted
                and (
                    (v.document.document_id, v.document.version) == key
                    or (v.document.document_id, v.document.version) in referenced
                )
            ]
            for version in selected:
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
                            source=source,
                            anchor=anchor,
                            text=version.text[anchor.start : anchor.end],
                            historical=version.document.version != latest.document.version,
                        )
                    )
        if sum(len(p.text) for p in passages) > 100000:
            raise ValueError("Context limit exceeded; narrow the supplied packet")
        return ContextPacket(
            project=self.repository.project(scope),
            passages=tuple(passages),
            exclusions=tuple(exclusions),
        )

    def _proposal(self, context: ContextPacket, revision: int) -> ProjectObject:
        try:
            task = InterpretationTask(context=context)
            with provider_session(self.adapter) as ledger:
                output = Interpretation.model_validate(self.adapter.interpret(task))
                self.verifier.interpretation(task, output)
                if ledger:
                    ledger.state = "SUCCEEDED"
                run_metadata = ledger.receipt() if ledger else None
        except ProviderFailure:
            raise
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
            generated_by_run_id=run_metadata.run_id if run_metadata else "fake-interpretation-v1",
            provider_run=run_metadata,
            statements=output.statements,
            source_refs=tuple(
                {ref for statement in output.statements for ref in statement.source_refs}
            ),
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
                session_goal=request.session_goal,
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
                rights_declaration="User authorized bounded OpenAI processing of their original text"
                if getattr(self.adapter, "provider_config", None)
                else "User authorized local processing of their original text",
            )
            self.sources.paste(scope, source, request.idea)
            self.repository.set_admission(scope, source.document_id, 1, True)
            proposal = self._proposal(self.context(identifier), 2)
            proposal = proposal.model_copy(
                update={"dependencies": dependencies(project, ("Brief",))}
            )
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
            versions = dict(project.dependency_versions)
            for key in AFFECTED["Brief"] + ("source:" + draft,):
                versions[key] = versions.get(key, 0) + 1
            updated = Project.model_validate(
                {
                    **project.model_dump(),
                    "revision": project.revision + 1,
                    "objects": changed,
                    "dependency_versions": versions,
                }
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
                rights_declaration="User authorized bounded OpenAI processing; attribution is user-reported"
                if getattr(self.adapter, "provider_config", None)
                else "User authorized local processing; attribution is user-reported",
            )
            self.sources.paste(scope, source, request.text)
            self.repository.set_admission(scope, source.document_id, 1, request.admitted)
            versions = (
                changed(project, "Literature")
                if request.admitted
                else dict(project.dependency_versions)
            )
            updated = Project.model_validate(
                {
                    **project.model_dump(),
                    "revision": project.revision + 1,
                    "dependency_versions": versions,
                    "objects": invalidate(project.objects, versions),
                }
            )
            self.repository.save_project(scope, updated, project.revision)
        return self.view(project_id)

    def accept(self, project_id: str, object_id: str, expected: int) -> dict[str, Any]:
        from domain.research import DecisionRequest
        from services.research import ResearchService

        return ResearchService(self).decide(
            project_id, object_id, DecisionRequest(expected_revision=expected, action="accepted")
        )

    def run(
        self,
        project_id: str,
        expected: int,
        dimensions: tuple[int, ...] = (),
        target_workspace: str | None = None,
        evaluation_scope: Scope = Scope.INITIAL_SCREEN,
    ) -> dict[str, Any]:
        scope = self.scope(project_id)
        project = self._current(project_id, expected)
        context = self.context(project_id)
        if context.project != project:
            raise Conflict("Working revision changed during context assembly")
        versions = {(p.source.document_id, p.anchor.version) for p in context.passages}
        documents = tuple(
            self.repository.version(scope, d, v).document for d, v in sorted(versions)
        )
        snapshot = EvaluationSnapshot(
            snapshot_id=uuid4().hex,
            created_at=timestamp(),
            project=project,
            documents=documents,
            policy_version=self.manifest.version,
            policy_sha256=self.manifest.canonical_sha256,
            policy_manifest_sha256=self.manifest.sha256,
            policy_implementation_version=self.manifest.implementation_version,
            scope=Scope.TARGETED_CHECK if dimensions else evaluation_scope,
            prompt_version=getattr(self.adapter, "prompt_configuration", None),
            model_configuration=self.adapter.configuration,
        )
        task = AssessmentTask(
            context=context,
            dimensions=dimensions,
            scope=snapshot.scope,
            policy_version=snapshot.policy_version,
            policy_sha256=snapshot.policy_sha256,
            policy_manifest_sha256=snapshot.policy_manifest_sha256,
            policy_implementation_version=snapshot.policy_implementation_version,
        )
        try:
            with provider_session(self.adapter) as ledger:
                candidate = CandidateReview.model_validate(self.adapter.assess(task))
                self._current(project_id, expected)
                for passage in context.passages:
                    self.repository.get_anchor(
                        scope,
                        SourceReference(
                            document_id=passage.source.document_id,
                            version=passage.anchor.version,
                            anchor_id=passage.anchor.anchor_id,
                        ),
                    )
                checked = self.verifier.review(task, candidate)
                verified = checked.assessment
                if ledger:
                    ledger.state = "SUCCEEDED"
                run_metadata = ledger.receipt() if ledger else None
            # Provider never supplies/echoes snapshot or scope identifiers.
            fields = verified.model_dump(exclude={"findings"})
            findings = tuple(
                Finding(**finding.model_dump(), scope=snapshot.snapshot_id)
                for finding in verified.findings
            )
            assessment = Assessment(snapshot=snapshot, findings=findings, **fields)
            evaluated = evaluate(assessment, self.manifest)
        except ProviderFailure:
            raise
        except (ValueError, TypeError) as exc:
            raise InvalidModelOutput(
                "Invalid model evaluation: " + str(exc).split("\n")[0]
            ) from exc
        with self.repository.db.transaction():
            # Recheck scoped sources and revision at publication, not merely at intake.
            self._current(project_id, expected)
            result = policy_view(asdict(evaluated))
            for name in (
                "idea_uncapped",
                "idea",
                "study",
                "project_uncapped",
                "project_before_caps",
                "project",
            ):
                result[name]["displayed"] = getattr(evaluated, name).displayed
            result.update(
                policy_version=snapshot.policy_version,
                policy_implementation_version=snapshot.policy_implementation_version,
            )
            coverage = tuple(
                HistoricalCoverage(
                    document_id=d,
                    title=self.repository.source(scope, d).title,
                    version=v,
                    state=self.repository.version(scope, d, v).extraction_state,
                    anchors=anchors(self.repository.version(scope, d, v)),
                    note="Supplied packet; focused support dispositions are interpretive, not independent data verification."
                    if run_metadata
                    else "Provided to fake fixture; no semantic source inspection.",
                )
                for d, v in sorted(versions)
            )
            bundle = self.bundle(project_id)
            latest = {v.document.document_id: v for v in bundle.versions}
            exclusions = tuple(
                HistoricalExclusion(
                    document_id=source.document_id,
                    title=source.title,
                    version=latest[source.document_id].document.version,
                    reason="Not admitted"
                    if (source.document_id, latest[source.document_id].document.version)
                    not in {(a.document_id, a.version) for a in bundle.admissions if a.admitted}
                    else "Source text unavailable or empty",
                )
                for source in bundle.sources
                if (source.document_id, latest[source.document_id].document.version) not in versions
            )
            self.repository.save_snapshot(
                scope,
                StoredSnapshot(
                    snapshot=snapshot,
                    assessment=assessment,
                    review=checked.summary,
                    provider_run=run_metadata,
                    checked_statements=checked.statements,
                    checks=tuple(c.model_dump(mode="json") for c in checked.checks),
                    structural_checks=checked.structural_checks,
                    target_workspace=target_workspace,
                    dependencies=dependencies(
                        project,
                        ((target_workspace,) if target_workspace else tuple(FIELDS))
                        + review_keys(project, target_workspace)
                        + tuple(
                            "source:" + ref.document_id
                            for decision in checked.checks
                            for ref in decision.source_refs
                        ),
                    ),
                    policy_result=PolicyResult.model_validate(result),
                    coverage=coverage,
                    exclusions=exclusions,
                ),
            )
        return self.review(project_id, snapshot.snapshot_id)

    def review(self, project_id: str, snapshot_id: str) -> dict[str, Any]:
        stored = self.repository.snapshot(self.scope(project_id), snapshot_id)
        if stored.assessment is None or stored.review is None:
            raise ValueError("Snapshot has no application review")
        if stored.policy_result is None or stored.coverage is None or stored.exclusions is None:
            raise ValueError(
                "Historical rendering was not captured for this legacy snapshot; deliberate reevaluation is required"
            )
        current = self.repository.project(self.scope(project_id))
        # Older snapshots predate explicit review dependency capture. Derive their
        # logical dependencies from their own frozen project, never today's objects.
        tracked = {
            d.key: d
            for d in dependencies(
                stored.snapshot.project,
                review_keys(stored.snapshot.project, stored.target_workspace),
            )
        }
        tracked.update({d.key: d for d in stored.dependencies})
        affected = tuple(
            d.key
            for d in tracked.values()
            if current.dependency_versions.get(d.key, 0) != d.version
        )
        result = {
            "snapshot": stored.snapshot.model_dump(
                mode="json",
                exclude_unset=True,
                exclude={"documents": {"__all__": {"original_storage_reference"}}},
            ),
            "coverage": [c.model_dump(mode="json") for c in stored.coverage],
            "exclusions": [c.model_dump(mode="json") for c in stored.exclusions],
            "summary": stored.review.model_dump(mode="json"),
            "assessment": stored.assessment.model_dump(mode="json", exclude={"snapshot"}),
            "policy": stored.policy_result.model_dump(mode="json", exclude_unset=True),
            "stale": bool(affected)
            if tracked
            else current.revision != stored.snapshot.project.revision,
            "affected_workspaces": list(affected),
            "target_workspace": stored.target_workspace,
        }
        if stored.provider_run is not None:
            result["provider_run"] = stored.provider_run.model_dump(mode="json")
            result["statements"] = [s.model_dump(mode="json") for s in stored.checked_statements]
            result["checks"] = list(stored.checks)
            result["structural_checks"] = [
                c.model_dump(mode="json") for c in stored.structural_checks
            ]
        return result

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
                {
                    "snapshot_id": s.snapshot.snapshot_id,
                    "revision": s.snapshot.project.revision,
                    "workspace": s.target_workspace,
                    "stale": bool(self.review(project_id, s.snapshot.snapshot_id)["stale"]),
                }
                for s in sorted(
                    bundle.snapshots,
                    key=lambda item: (
                        item.snapshot.project.revision,
                        item.snapshot.created_at or "",
                    ),
                )
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
        if format not in ("markdown", "plan"):
            raise ValueError("Supported exports: markdown, json")
        lines = [
            "# " + bundle.revisions[-1].title,
            "",
            "Development review; interpretive checking is not independent scientific validation.",
            "",
            f"Working revision: {bundle.revisions[-1].revision}",
            f"Route: {bundle.revisions[-1].route}; stage: {bundle.revisions[-1].stage}",
            f"Evaluation target: {bundle.revisions[-1].evaluation_target}",
            f"Current help request: {bundle.revisions[-1].session_goal}",
        ]
        for obj in bundle.revisions[-1].objects:
            if isinstance(obj.payload, ResearchRecord) and (
                format != "plan" or obj.payload.workspace == "Next Actions"
            ):
                lines += [
                    "",
                    "## " + obj.payload.workspace + ": " + obj.payload.title,
                    "",
                    f"Object {obj.object_id}; revision {obj.revision}; origin {obj.origin}; adoption {obj.adoption}; evidence {obj.evidence_state}; freshness {obj.freshness}",
                ]
                for field in obj.payload.fields:
                    lines += [
                        "",
                        f"{field.key}: {field.text or 'Not known yet'} (origin: {field.origin}; state: {field.state})",
                    ]
                lines += [
                    "",
                    "Provenance: "
                    + json.dumps([r.model_dump(mode="json") for r in obj.source_refs]),
                    "",
                    "Dependencies: "
                    + json.dumps([d.model_dump(mode="json") for d in obj.dependencies]),
                ]
        for review in reviews if format != "plan" else []:
            summary = ReviewContent.model_validate(
                {k: v for k, v in review["summary"].items() if k != "fixture"}
            )
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
                        {
                            "assessment": review["assessment"],
                            "policy": review["policy"],
                            **(
                                {
                                    "provider_run": review["provider_run"],
                                    "statements": review["statements"],
                                    "checks": review["checks"],
                                    "structural_checks": review["structural_checks"],
                                }
                                if "provider_run" in review
                                else {}
                            ),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    "```",
                ]
            )
        return "\n".join(lines) + "\n"
