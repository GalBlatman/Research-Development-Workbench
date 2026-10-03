from typing import Annotated, Literal, Self

from pydantic import Field, StrictBool, model_validator

from domain.models import AttributedStatement as AttributedStatement
from domain.models import (
    Brief,
    Frozen,
    Hash,
    Project,
    ProviderRun,
    Rating,
    ReviewContent,
    Revision,
    Route,
    RouteItem,
    Scope,
    SourceReference,
    Stage,
    StructuralCheck,
    Text,
    Truth,
    Verification,
)
from domain.sources import SourceAnchor, SourceRecord

InputText = Annotated[str, Field(min_length=1, max_length=20000)]
SourceText = Annotated[str, Field(min_length=1, max_length=50000)]


class CreateProject(Frozen):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    idea: InputText
    route: Route = Route.EXPLAIN
    stage: Stage = Stage.DISCOVERY
    authorized: Literal[True]
    session_goal: str = "Assess the idea and identify the next useful step"


class EditProject(Frozen):
    expected_revision: Revision
    idea: InputText


class AddSource(Frozen):
    expected_revision: Revision
    title: Annotated[str, Field(min_length=1, max_length=200)]
    attribution: Annotated[str, Field(min_length=1, max_length=500)]
    text: SourceText
    authorized: Literal[True]
    admitted: StrictBool


class RevisionRequest(Frozen):
    expected_revision: Revision


class EvaluateRequest(RevisionRequest):
    """The server selects workflow/provider configuration, never the browser."""

    scope: Literal[Scope.INITIAL_SCREEN, Scope.FULL_EVALUATION, Scope.REVISION_REVIEW] = (
        Scope.INITIAL_SCREEN
    )


class Interpretation(Frozen):
    brief: Brief
    limitations: tuple[Text, ...]
    statements: tuple[AttributedStatement, ...] = ()


class RuleJudgment(Frozen):
    rule_id: Text
    value: Truth
    reasoning: Text
    verification: Verification = Verification.UNRESOLVED
    source_refs: tuple[SourceReference, ...] = ()


class AssessmentFields(Frozen):
    account_articulated: StrictBool
    study_assessable: StrictBool
    ratings: tuple[Rating, ...]
    findings: tuple[RuleJudgment, ...]
    route_assessment: tuple[RouteItem, ...] = ()


class ProposedAssessment(AssessmentFields):
    @model_validator(mode="after")
    def cannot_self_verify(self) -> Self:
        if any(
            r.verification != Verification.UNRESOLVED
            or (r.benchmark is not None and r.benchmark.verification != Verification.UNRESOLVED)
            for r in self.ratings
        ) or any(f.verification != Verification.UNRESOLVED for f in self.findings):
            raise ValueError("Provider output cannot self-verify judgments")
        return self


class CandidateReview(Frozen):
    assessment: ProposedAssessment
    summary: ReviewContent
    statements: tuple[AttributedStatement, ...] = ()


class CheckDecision(Frozen):
    target: Text
    disposition: Verification
    reason: Text
    source_refs: tuple[SourceReference, ...]


class CheckResult(Frozen):
    decisions: tuple[CheckDecision, ...]
    summary: ReviewContent


class CheckedReview(Frozen):
    assessment: AssessmentFields
    summary: ReviewContent
    statements: tuple[AttributedStatement, ...] = ()
    checks: tuple[CheckDecision, ...] = ()
    structural_checks: tuple[StructuralCheck, ...] = ()


class Passage(Frozen):
    source: SourceRecord
    anchor: SourceAnchor
    text: str
    historical: StrictBool = False


class ContextPacket(Frozen):
    project: Project
    passages: tuple[Passage, ...]
    exclusions: tuple[str, ...]


class InterpretationTask(Frozen):
    schema_version: Literal["rdw-task-1"] = "rdw-task-1"
    task: Literal["ExtractProject"] = "ExtractProject"
    context: ContextPacket


class AssessmentTask(Frozen):
    schema_version: Literal["rdw-task-1"] = "rdw-task-1"
    task: Literal["AssessProject"] = "AssessProject"
    context: ContextPacket
    scope: Scope
    policy_version: Text
    policy_sha256: Hash
    policy_manifest_sha256: Hash
    policy_implementation_version: Text
    dimensions: tuple[Annotated[int, Field(ge=1, le=10)], ...] = ()

    @model_validator(mode="after")
    def unique_targets(self) -> Self:
        if len(set(self.dimensions)) != len(self.dimensions):
            raise ValueError("Duplicate targeted dimensions")
        return self


class CheckingTask(Frozen):
    schema_version: Literal["rdw-task-1"] = "rdw-task-1"
    task: Literal["VerifyAssessment"] = "VerifyAssessment"
    assessment_task: AssessmentTask
    candidate: CandidateReview
    targets: tuple[Text, ...]


class RunHandle(Frozen):
    run_id: Text
    project_id: Text
    expected_revision: Revision
    state: Literal["queued", "running", "succeeded", "failed"]
    snapshot_id: str | None = None
    error_code: str | None = None
    result_revision: int | None = None
    provider_run: ProviderRun | None = None


class TargetedEvaluation(RevisionRequest):
    dimensions: Annotated[
        tuple[Annotated[int, Field(ge=1, le=10)], ...], Field(min_length=1, max_length=10)
    ]

    @model_validator(mode="after")
    def unique_dimensions(self) -> Self:
        if len(set(self.dimensions)) != len(self.dimensions):
            raise ValueError("Duplicate targeted dimensions")
        return self
