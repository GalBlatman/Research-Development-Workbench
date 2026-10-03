from typing import Annotated, Literal, Self

from pydantic import Field, StrictBool, model_validator

from domain.models import (
    Brief,
    Frozen,
    Hash,
    Project,
    Rating,
    ReviewContent,
    Revision,
    Route,
    RouteItem,
    Scope,
    SourceReference,
    Stage,
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


class Interpretation(Frozen):
    brief: Brief
    limitations: tuple[Text, ...]


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


class Passage(Frozen):
    source: SourceRecord
    anchor: SourceAnchor
    text: str


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
