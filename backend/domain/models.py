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
    content_sha256: Hash
    original_storage_reference: Text
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


Payload = Annotated[
    Question | Construct | Claim | Study | Comparison | Brief, Field(discriminator="kind")
]


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
    generated_by_run_id: str | None = None

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

    @model_validator(mode="after")
    def consistent_documents(self) -> Self:
        if any(doc.project_id != self.project.project_id for doc in self.documents):
            raise ValueError("Document outside snapshot project")
        versions = {(doc.document_id, doc.version) for doc in self.documents}
        if len(versions) != len(self.documents):
            raise ValueError("Duplicate document versions")
        for obj in self.project.objects:
            refs = obj.source_refs + tuple(ref for check in obj.checks for ref in check.source_refs)
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


class Assessment(Frozen):
    snapshot: EvaluationSnapshot
    account_articulated: StrictBool
    study_assessable: StrictBool
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
