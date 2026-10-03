from typing import Annotated, Literal

from pydantic import Field, StrictBool

from domain.models import (
    Assessment,
    Brief,
    Frozen,
    Project,
    ReviewSummary,
    Revision,
    Route,
    Stage,
    Text,
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
    fixture: Literal["limited", "scored"] = "limited"


class Interpretation(Frozen):
    brief: Brief
    limitations: tuple[Text, ...]


class CandidateReview(Frozen):
    assessment: Assessment
    summary: ReviewSummary


class Passage(Frozen):
    source: SourceRecord
    anchor: SourceAnchor
    text: str


class ContextPacket(Frozen):
    project: Project
    passages: tuple[Passage, ...]
    exclusions: tuple[str, ...]
