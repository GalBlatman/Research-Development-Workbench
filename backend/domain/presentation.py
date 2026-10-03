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
    UserAction,
    Verification,
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
    workspace: str | None = None
    stale: bool = False
    scope: Scope = Scope.INITIAL_SCREEN
    policy_version: str = "4"
    policy_sha256: str | None = None
    policy_implementation_version: str | None = None
    policy_manifest_sha256: str | None = None
    prompt_version: str | None = None
    model_configuration: str | None = None


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
    imported: bool = False
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
    created_at: str | None = None


class AssessmentView(Frozen):
    account_articulated: bool
    study_assessable: bool
    account_articulated_verification: Verification = Verification.SUPPORTED
    study_assessable_verification: Verification = Verification.SUPPORTED
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
    affected_workspaces: tuple[str, ...] = ()
    target_workspace: str | None = None


class SourceHistoryView(Frozen):
    document_id: str
    version: int
    role: str
    state: str
    anchors: tuple[SourceAnchor, ...]


class HistoryView(Frozen):
    revisions: tuple[Project, ...]
    actions: tuple[UserAction, ...]
    source_versions: tuple[SourceHistoryView, ...]
    reviews: tuple[ReviewIndex, ...]
