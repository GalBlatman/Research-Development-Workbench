from typing import Literal

from domain.models import (
    Finding,
    Frozen,
    Project,
    Rating,
    ReviewSummary,
    Route,
    RouteItem,
    Scope,
    Stage,
    Status,
    Truth,
)
from domain.sources import SourceAnchor, SourceRecord


class ExactValue(Frozen):
    numerator: int
    denominator: int


class ScoreView(Frozen):
    value: ExactValue | None
    displayed: int | None
    status: Status
    reason: str


class TraceView(Frozen):
    rule_id: str
    value: Truth
    consequence: str
    reasoning: str
    source: str


class GateView(Frozen):
    name: str
    state: Truth
    provisional: bool
    missed: tuple[str, ...]


class PolicyResult(Frozen):
    route: Route
    stage: Stage
    snapshot_id: str
    policy_sha256: str
    policy_manifest_sha256: str
    idea_uncapped: ScoreView
    idea: ScoreView
    study: ScoreView
    project_uncapped: ScoreView
    project_before_caps: ScoreView
    project: ScoreView
    effective_ratings: tuple[tuple[int, int | None], ...]
    gates: tuple[GateView, ...]
    trace: tuple[TraceView, ...]
    label: str
    endorsement_stage: str
    editorial_status: Literal["UNCALIBRATED"]


class SourceView(Frozen):
    source: SourceRecord
    version: int
    state: str
    admitted: bool
    text: str | None
    anchors: tuple[SourceAnchor, ...]


class ReviewIndex(Frozen):
    snapshot_id: str
    revision: int


class ProjectView(Frozen):
    project: Project
    sources: tuple[SourceView, ...]
    reviews: tuple[ReviewIndex, ...]


class PublicDocument(Frozen):
    document_id: str
    project_id: str
    version: int
    content_sha256: str | None
    role: str


class SnapshotView(Frozen):
    snapshot_id: str
    project: Project
    documents: tuple[PublicDocument, ...]
    policy_version: str
    policy_sha256: str
    policy_manifest_sha256: str
    policy_implementation_version: str
    prompt_version: str | None
    model_configuration: str | None
    scope: Scope


class AssessmentView(Frozen):
    account_articulated: bool
    study_assessable: bool
    ratings: tuple[Rating, ...]
    findings: tuple[Finding, ...]
    route_assessment: tuple[RouteItem, ...]


class CoverageView(Frozen):
    document_id: str
    title: str
    version: int
    state: str
    anchors: tuple[SourceAnchor, ...]
    note: str


class ReviewView(Frozen):
    snapshot: SnapshotView
    summary: ReviewSummary
    assessment: AssessmentView
    policy: PolicyResult
    stale: bool
    coverage: tuple[CoverageView, ...]
