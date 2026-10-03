from domain.application import AttributedStatement, CheckDecision
from domain.models import (
    Finding,
    Frozen,
    Project,
    ProviderRun,
    Rating,
    ReviewContent,
    ReviewSummary,
    RouteItem,
    Scope,
    StructuralCheck,
)
from domain.results import PolicyResult as PolicyResult
from domain.sources import HistoricalCoverage as CoverageView
from domain.sources import HistoricalExclusion, SourceAnchor, SourceRecord


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


class ReviewView(Frozen):
    snapshot: SnapshotView
    summary: ReviewSummary | ReviewContent
    assessment: AssessmentView
    policy: PolicyResult
    stale: bool
    coverage: tuple[CoverageView, ...]
    exclusions: tuple[HistoricalExclusion, ...]

    provider_run: ProviderRun | None = None
    statements: tuple[AttributedStatement, ...] = ()
    checks: tuple[CheckDecision, ...] = ()
    structural_checks: tuple[StructuralCheck, ...] = ()
