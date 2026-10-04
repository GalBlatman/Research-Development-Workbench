from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

Text = Annotated[str, Field(min_length=1)]
Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Revision = Annotated[StrictInt, Field(ge=1)]


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=True)


class Route(StrEnum):
    EXPLAIN = "EXPLAIN"
    ESTABLISH = "ESTABLISH"
    TEST = "TEST"


class Stage(StrEnum):
    EARLY_IDEA = "EARLY IDEA"
    DISCOVERY = "DISCOVERY PROPOSAL"
    PROPOSAL = "SPECIFIED STUDY PROPOSAL"
    COMPLETED = "COMPLETED STUDY"


class EvidenceState(StrEnum):
    DOCUMENTED = "documented_or_verified"
    UNTESTED = "specified_but_untested"
    CONTESTED = "contested"
    MISSING = "missing"
    UNINSPECTED = "not_inspected"
    CONTRADICTED = "contradicted"
    NOT_APPLICABLE = "not_applicable"


class Origin(StrEnum):
    USER = "user_text"
    EXTRACTION = "document_extraction"
    INFERENCE = "model_inference"
    SUGGESTION = "development_suggestion"


class Adoption(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class Provenance(StrEnum):
    USER_REPORTED = "user_reported"
    SOURCE_INSPECTED = "source_text_inspected"
    ARTIFACT_INSPECTED = "analysis_artifact_inspected"
    APP_REPRODUCED = "app_reproduced"


class Freshness(StrEnum):
    CURRENT = "current"
    AFFECTED = "affected_by_change"
    SUPERSEDED = "superseded"


class Status(StrEnum):
    ASSESSED = "assessed"
    PENDING = "pending"
    NOT_APPLICABLE = "not_applicable"
    CONDITIONAL = "conditional"
    CONTESTED = "contested"
    UNRESOLVED = "unresolved"


class Truth(StrEnum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class GateState(StrEnum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Commitment(StrEnum):
    ORDINARY = "ORDINARY_STAGE_COMMITMENT"
    PREMISE_VERIFY_OR_REFORMULATE = "PREMISE_VERIFICATION_OR_REFORMULATION"
    BOUNDED_PREMISE_CHECK = "BOUNDED_PREMISE_CHECK_ONLY"
    WITHHELD = "WITHHELD"


class Verification(StrEnum):
    SUPPORTED = "supported"
    NEEDS_REVISION = "needs_revision"
    UNRESOLVED = "unresolved"


class Scope(StrEnum):
    INITIAL_SCREEN = "INITIAL_SCREEN"
    TARGETED_CHECK = "TARGETED_CHECK"
    FULL_EVALUATION = "FULL_EVALUATION"
    REVISION_REVIEW = "REVISION_REVIEW"


class SourceReference(Frozen):
    document_id: Text
    version: Revision
    anchor_id: Text


class DocumentVersion(Frozen):
    document_id: Text
    project_id: Text
    version: Revision
    content_sha256: Hash | None
    original_storage_reference: Text | None = None
    role: Text


class EvidenceCheck(Frozen):
    check_id: Text
    claim_id: Text
    object_of_verification: Text
    provenance: Provenance
    checked_by: Text
    source_refs: tuple[SourceReference, ...] = ()
    outcome: Text

    @model_validator(mode="after")
    def valid_check(self) -> Self:
        if self.provenance == Provenance.APP_REPRODUCED:
            raise ValueError("App reproduction is outside this release; do not claim it")
        if self.provenance == Provenance.SOURCE_INSPECTED and not self.source_refs:
            raise ValueError("Inspected source checks need anchored references")
        return self


class Question(Frozen):
    kind: Literal["question"] = "question"
    text: Text
    audience: str | None = None


class Construct(Frozen):
    kind: Literal["construct"] = "construct"
    definition: Text
    level: str | None = None
    timing: str | None = None


class Claim(Frozen):
    kind: Literal["claim"] = "claim"
    text: Text
    claim_type: Literal["premise", "mechanism", "prediction", "assumption", "contribution"]
    construct_ids: tuple[str, ...] = ()


class Study(Frozen):
    kind: Literal["study"] = "study"
    inference: Text
    design: Text
    claim_ids: tuple[str, ...] = ()
    sample: str | None = None
    measures: tuple[str, ...] = ()
    comparisons: tuple[str, ...] = ()


class Comparison(Frozen):
    kind: Literal["comparison"] = "comparison"
    account_ids: tuple[str, ...]
    expected_observations: tuple[str, ...]
    discrimination: str | None = None


class Brief(Frozen):
    kind: Literal["brief"] = "brief"
    question: Text
    stakes: str | None = None
    core_insight: str | None = None
    intended_contribution: str | None = None


class ResearchField(Frozen):
    key: Text
    claim_kind: Literal[
        "interpretive_judgment", "proposed_action", "hypothetical_result", "reported_result"
    ] = "interpretive_judgment"
    text: Annotated[str, Field(max_length=20000)] | None = None
    state: EvidenceState = EvidenceState.UNINSPECTED
    origin: Origin = Origin.USER
    source_refs: tuple[SourceReference, ...] = ()


class ResearchRecord(Frozen):
    kind: Literal["research_record"] = "research_record"
    workspace: Literal[
        "Brief", "Literature", "Argument", "Alternatives", "Study", "Usefulness", "Next Actions"
    ]
    title: Annotated[str, Field(min_length=1, max_length=200)]
    fields: Annotated[tuple[ResearchField, ...], Field(min_length=1, max_length=32)]

    @model_validator(mode="after")
    def unique_fields(self) -> Self:
        if not self.fields or len({f.key for f in self.fields}) != len(self.fields):
            raise ValueError("Research records require distinct fields")
        if any(f.state == EvidenceState.DOCUMENTED for f in self.fields):
            raise ValueError("Workspace entries do not independently verify evidence")
        return self


class Dependency(Frozen):
    key: Text
    version: Annotated[StrictInt, Field(ge=0)]
    reason: Text


class UserAction(Frozen):
    object_id: Text
    action: Literal["accepted", "rejected", "edited", "superseded"]
    actor: Text
    revision: Revision
    reason: Text


Payload = Annotated[
    Question | Construct | Claim | Study | Comparison | Brief | ResearchRecord,
    Field(discriminator="kind"),
]


class ProviderCall(Frozen):
    task: Text
    provider: Text
    configured_model: Text
    returned_model: str | None = None
    timestamp: Text
    prompt_version: Text
    prompt_sha256: Hash
    status: Text
    request_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    usage_details: dict[str, int] = {}
    reserved_tokens: int
    input_usd_per_million: float
    cached_input_usd_per_million: float
    cache_write_usd_per_million: float
    output_usd_per_million: float
    price_date: Text


class ProviderRun(Frozen):
    run_id: Text
    status: Text
    calls: tuple[ProviderCall, ...]
    max_calls: int
    max_tokens: int
    output_limit: int
    reasoning_effort: str | None


class StructuralCheck(Frozen):
    target: Text
    status: Literal["SOURCE_REFS_RESOLVED"]
    source_refs: tuple[SourceReference, ...]


class AttributedStatement(Frozen):
    statement_id: Text
    kind: Literal[
        "source_backed", "user_project", "model_inference", "proposed_improvement", "unresolved"
    ]
    text: Text
    source_refs: tuple[SourceReference, ...] = ()


class SupportDisposition(Frozen):
    target: Text
    disposition: Verification
    reason: Text
    source_refs: tuple[SourceReference, ...]


class ProjectObject(Frozen):
    object_id: Text
    project_id: Text
    revision: Revision
    payload: Payload
    origin: Origin
    adoption: Adoption
    evidence_state: EvidenceState
    freshness: Freshness = Freshness.CURRENT
    source_refs: tuple[SourceReference, ...] = ()
    checks: tuple[EvidenceCheck, ...] = ()
    operation_id: str | None = None
    generated_by_run_id: str | None = None
    imported: StrictBool = False
    provider_run: ProviderRun | None = None
    statements: tuple[AttributedStatement, ...] = ()
    dependencies: tuple[Dependency, ...] = ()
    dependency_identity: Text | None = None
    target_object_id: str | None = None
    reason: str | None = None
    support_dispositions: tuple[SupportDisposition, ...] = ()

    @model_validator(mode="after")
    def evidence_is_explicit(self) -> Self:
        if any(check.claim_id != self.object_id for check in self.checks):
            raise ValueError("Check must identify this bounded object")
        if self.evidence_state == EvidenceState.DOCUMENTED and not any(
            check.provenance != Provenance.USER_REPORTED for check in self.checks
        ):
            raise ValueError("Documented claims need an explicit inspected check")
        return self


def accept_content(content: ProjectObject, revision: int) -> ProjectObject:
    """Adoption changes representation only; preserve origin and epistemic state."""
    if content.adoption != Adoption.PROPOSED or revision <= content.revision:
        raise ValueError("Accept a proposed object into a newer revision")
    data = content.model_dump()
    data.update(adoption=Adoption.ACCEPTED, revision=revision)
    return ProjectObject.model_validate(data)


class Workspace(Frozen):
    workspace_id: Text
    owner_id: Text
    access_policy: Text
    model_processing_policy: Text
    storage_policy: Text


class Project(Frozen):
    project_id: Text
    workspace_id: Text
    title: Text
    revision: Revision
    route: Route
    stage: Stage
    objects: tuple[ProjectObject, ...] = ()
    session_goal: str = "Assess the idea and identify the next useful step"
    evaluation_target: Literal["manuscript_as_written", "current_project_as_clarified"] = (
        "current_project_as_clarified"
    )
    dependency_versions: dict[str, int] = {}
    actions: tuple[UserAction, ...] = ()

    @model_validator(mode="after")
    def consistent_objects(self) -> Self:
        if len({obj.object_id for obj in self.objects}) != len(self.objects):
            raise ValueError("Duplicate project object IDs")
        if any(
            obj.project_id != self.project_id or obj.revision > self.revision
            for obj in self.objects
        ):
            raise ValueError("Object scope/revision mismatch")
        return self


class EvaluationSnapshot(Frozen):
    imported: StrictBool = False
    snapshot_id: Text
    project: Project
    documents: tuple[DocumentVersion, ...] = ()
    policy_version: Text
    policy_sha256: Hash
    policy_manifest_sha256: Hash
    policy_implementation_version: Text
    prompt_version: str | None = None
    model_configuration: str | None = None
    scope: Scope
    created_at: str | None = None

    @model_validator(mode="after")
    def consistent_documents(self) -> Self:
        if any(doc.project_id != self.project.project_id for doc in self.documents):
            raise ValueError("Document outside snapshot project")
        versions = {(doc.document_id, doc.version) for doc in self.documents}
        if len(versions) != len(self.documents):
            raise ValueError("Duplicate document versions")
        for obj in self.project.objects:
            refs = (
                obj.source_refs
                + tuple(ref for check in obj.checks for ref in check.source_refs)
                + tuple(ref for statement in obj.statements for ref in statement.source_refs)
            )
            if any((ref.document_id, ref.version) not in versions for ref in refs):
                raise ValueError("Object refers to a document version outside snapshot")
        return self


class Finding(Frozen):
    rule_id: Text
    value: Truth
    reasoning: Text
    scope: Text
    verification: Verification
    source_refs: tuple[SourceReference, ...] = ()

    @property
    def effective_value(self) -> Truth:
        return self.value if self.verification == Verification.SUPPORTED else Truth.UNKNOWN


class Benchmark(Frozen):
    comparison: Text
    dimension_reason: Text
    published_reference: Text
    inspected: StrictBool
    relevant: StrictBool
    verification: Verification

    @property
    def supported(self) -> bool:
        return self.inspected and self.relevant and self.verification == Verification.SUPPORTED


class Rating(Frozen):
    dimension: Annotated[StrictInt, Field(ge=1, le=10)]
    rating: Annotated[StrictInt, Field(ge=0, le=10)] | None
    status: Status
    rationale: Text
    main_limitation: Text
    inspected_material: tuple[str, ...] = ()
    verification: Verification
    benchmark: Benchmark | None = None
    plausible_range: (
        tuple[Annotated[StrictInt, Field(ge=0, le=10)], Annotated[StrictInt, Field(ge=0, le=10)]]
        | None
    ) = None

    @model_validator(mode="after")
    def valid_rating(self) -> Self:
        if self.status in (Status.PENDING, Status.NOT_APPLICABLE, Status.UNRESOLVED):
            if self.rating is not None:
                raise ValueError("Unavailable rating must be null, not zero")
        elif self.rating is None:
            raise ValueError("Assessed/conditional/contested rating needs an integer")
        if self.rating is not None and not self.inspected_material:
            raise ValueError("Ratings require inspected material")
        if self.plausible_range:
            lo, hi = self.plausible_range
            if self.rating is None or not lo <= self.rating <= hi:
                raise ValueError("Range must contain the assessed rating")
        return self


class RouteItem(Frozen):
    item: Literal[
        "knowledge_need",
        "increment",
        "scope_precision",
        "capacity_to_learn",
        "evidence_strategy",
        "next_use",
    ]
    status: Literal["ADEQUATE FOR STAGE", "DEVELOPMENT NEEDED", "BLOCKING", "NOT INSPECTED"]
    reason: Text
    verification: Verification = Verification.SUPPORTED
    source_refs: tuple[SourceReference, ...] = ()


class Assessment(Frozen):
    snapshot: EvaluationSnapshot
    account_articulated: StrictBool
    study_assessable: StrictBool
    account_articulated_verification: Verification = Verification.SUPPORTED
    study_assessable_verification: Verification = Verification.SUPPORTED
    ratings: tuple[Rating, ...]
    findings: tuple[Finding, ...]
    route_assessment: tuple[RouteItem, ...] = ()

    @model_validator(mode="after")
    def no_duplicate_inputs(self) -> Self:
        for values in (
            [r.dimension for r in self.ratings],
            [f.rule_id for f in self.findings],
            [r.item for r in self.route_assessment],
        ):
            if len(values) != len(set(values)):
                raise ValueError("Duplicate assessment input")
        versions = {(d.document_id, d.version) for d in self.snapshot.documents}
        for finding in self.findings:
            if finding.scope != self.snapshot.snapshot_id:
                raise ValueError("Finding must target this frozen snapshot")
            if any((ref.document_id, ref.version) not in versions for ref in finding.source_refs):
                raise ValueError("Finding refers to a document outside snapshot")
        return self


def validate_diagnostic_fields(texts: tuple[str, ...]) -> None:
    values = tuple(text.strip().rstrip(".!?;:,… ").casefold() for text in texts)
    placeholders = {
        "tbd",
        "todo",
        "n/a",
        "na",
        "unknown",
        "unspecified",
        "placeholder",
        "do more research",
    }
    if any(not v or v in placeholders for v in values) or len(set(values[:4])) == 1:
        raise ValueError("Diagnostic action requires distinct specified inputs and outputs")


class DiagnosticAction(Frozen):
    issue: Text
    task: Text
    required_input: Text
    deliverable: Text
    outcome_branches: Annotated[tuple[Text, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def substantive_structure(self) -> Self:
        validate_diagnostic_fields(
            (self.issue, self.task, self.required_input, self.deliverable, *self.outcome_branches)
        )
        return self


class ReviewContent(Frozen):
    contribution: Text
    obstacle: Text
    limitations: tuple[Text, ...]
    next_action: Text
    deliverable: Text
    outcome_branches: tuple[Text, ...]
    disclaimer: Text
    diagnostic_action: DiagnosticAction | None = None


class ReviewSummary(ReviewContent):
    """Legacy RDW-004 summary; retain historical metadata, never use as provider output."""

    fixture: Literal["limited", "scored"]
