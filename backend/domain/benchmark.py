"""Versioned administrator contracts. No scientific judgments inferred by this module."""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from domain.models import EvidenceState, Frozen, Hash, ProviderRun, Route, Stage, Text, Verification
from domain.sources import SourceRole


class Split(StrEnum):
    DEVELOPMENT = "DEVELOPMENT"
    VALIDATION = "VALIDATION"
    HELD_OUT = "HELD_OUT"


class Feature(StrEnum):
    PUZZLE = "puzzle"
    QUESTION = "question"
    AUDIENCE = "audience_prior_work"
    PREDECESSOR = "closest_predecessor"
    CONTRIBUTION = "contribution"
    CONSTRUCTS = "constructs"
    MECHANISM = "mechanism_account"
    PREDICTIONS = "predictions_implications"
    RIVALS = "rivals"
    BOUNDARIES = "boundaries"
    SAMPLE = "unit_setting_sample"
    MEASURES = "measures"
    TIME = "temporal_structure"
    IDENTIFICATION = "identification"
    FINDINGS = "findings_evidence"
    USEFULNESS = "usefulness"
    PREMISE = "premise_basis"
    ATTRIBUTION = "source_attribution"
    ROUTE_STAGE = "route_stage"


class Transformation(StrEnum):
    INTACT = "INTACT_BLIND"
    HIDE = "HIDE_FEATURE"
    MULTIPLE = "HIDE_MULTIPLE"
    REVEAL = "CUMULATIVE_REVEAL"
    DEGRADE = "CONTROLLED_DEGRADATION"
    RESTORE = "CONTROLLED_RESTORATION"
    METADATA = "METADATA_BLINDING"


class Block(Frozen):
    block_id: Text
    text: Text
    role: SourceRole = SourceRole.DRAFT
    features: tuple[Feature, ...] = ()
    metadata_only: bool = False


class SourcePackage(Frozen):
    package_id: Text
    version: Text
    blocks: tuple[Block, ...]
    identifying_metadata: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def unique(self) -> Self:
        if len({b.block_id for b in self.blocks}) != len(self.blocks):
            raise ValueError("Duplicate source block")
        return self


class GoldFeature(Frozen):
    feature: Feature
    content: Text
    source_anchors: tuple[Text, ...]
    confidence: Literal["high", "medium", "low"]
    status: EvidenceState
    observable: bool = True


class BenchmarkProject(Frozen):
    benchmark_id: Text
    split: Split
    route: Route
    stage: Stage
    neutral_identifier: Text
    source_package: SourcePackage
    gold: tuple[GoldFeature, ...]
    version: Text


class Mutation(Frozen):
    transformation: Transformation
    targets: tuple[Feature, ...] = ()
    replacements: tuple[Block, ...] = ()
    parent_variant: str | None = None
    reveal_order: tuple[Feature, ...] = ()
    reveal_count: int = Field(default=0, ge=0)
    permit_metadata: bool = False
    provenance: Text = "Administrator-specified transformation"

    @model_validator(mode="after")
    def distinct(self) -> Self:
        if len(set(self.targets)) != len(self.targets) or len(
            {b.block_id for b in self.replacements}
        ) != len(self.replacements):
            raise ValueError("Duplicate mutation target or replacement")
        return self


class VisibleBlock(Frozen):
    text: Text
    role: SourceRole


class BlindPacket(Frozen):
    """Only this contract crosses into evaluator code; no administrator identifiers."""

    packet_id: Hash
    route: Route
    stage: Stage
    blocks: tuple[VisibleBlock, ...]


class BenchmarkVariant(Frozen):
    variant_id: Text
    benchmark_id: Text
    split: Split
    version: Text
    mutation: Mutation
    visibility: tuple[tuple[Feature, bool], ...]
    packet: BlindPacket
    package_hash: Hash
    split_hash: Hash


class FrozenSplit(Frozen):
    version: Text
    assignments: tuple[tuple[Text, Split, Hash], ...]
    package_assignments: tuple[tuple[Text, Text, Hash, Split], ...]

    @model_validator(mode="after")
    def unique(self) -> Self:
        if len({a[0] for a in self.assignments}) != len(self.assignments):
            raise ValueError("Same underlying project assigned twice")
        packages = self.package_assignments
        if {a[0] for a in packages} != {a[0] for a in self.assignments} or len(packages) != len(
            self.assignments
        ):
            raise ValueError("Every split assignment requires permanent package identity")
        if len({a[1] for a in packages}) != len(packages) or len({a[2] for a in packages}) != len(
            packages
        ):
            raise ValueError("Duplicate underlying source package")
        if {a[0]: a[3] for a in packages} != {a[0]: a[1] for a in self.assignments}:
            raise ValueError("Package and split assignments differ")
        return self


JudgmentKey = Annotated[
    str,
    Field(
        pattern=r"^(rating:([1-9]|10)|finding:(ROUTE-TOTAL|DISCOVERY-PENDING|UNINSPECTED-BLOCK|AUDIENCE-QUESTION|PREMISE-NO-BASIS|PREMISE-CONDITIONAL|PREMISE-CONTRADICTED|NO-ADVANCE|NO-CONSEQUENTIAL-STAKE|DESIGN-MISMATCH|INFERENCE-UNSUPPORTED|PROMISE-OVERREACH|HIGH-SCORE-BENCHMARK|EDITORIAL-UNCALIBRATED|PREDECESSORS-INSPECTED|STAGE-PREREQUISITES|CONSEQUENTIAL-STAKE|SUPPORT-VERIFIED|PROMISE-ALIGNED|DELIVERED-SUPPORT|ROUTE-NO-HARD-STOP|CONTRIBUTION-STUDY-SPECIFIED|PILOT-PREREQUISITES|STAGE-MISMATCH|KNOWLEDGE-NEED|IDENTIFIABLE-INCREMENT|CREDIBLE-BOUNDED-ACTION)|route:(knowledge_need|increment|scope_precision|capacity_to_learn|evidence_strategy|next_use)|statement:[A-Za-z0-9:_-]+)$"
    ),
]
JudgmentState = Literal[
    "assessed",
    "pending",
    "not_applicable",
    "conditional",
    "contested",
    "unresolved",
    "documented_or_verified",
    "specified_but_untested",
    "missing",
    "not_inspected",
    "contradicted",
    "TRUE",
    "FALSE",
    "UNKNOWN",
    "ADEQUATE FOR STAGE",
    "DEVELOPMENT NEEDED",
    "BLOCKING",
    "NOT INSPECTED",
    "proposed",
]
STATE_ALIASES = {
    name.upper(): name
    for name in (
        "assessed",
        "pending",
        "not_applicable",
        "conditional",
        "contested",
        "unresolved",
        "not_inspected",
    )
}


class Judgment(Frozen):
    key: JudgmentKey
    state: JudgmentState
    value: float | None = None
    verification: Verification = Verification.UNRESOLVED
    source_refs: tuple[Text, ...] = ()

    @field_validator("state", mode="before")
    @classmethod
    def canonical_state(cls, value: object) -> object:
        return STATE_ALIASES.get(value, value) if isinstance(value, str) else value


class BenchmarkExpectation(Frozen):
    feature: Feature
    behavior: Literal[
        "detect",
        "downgrade",
        "withhold",
        "unresolved",
        "not_inspected",
        "unchanged",
        "restore",
        "refuse_infer",
    ]
    judgment: JudgmentKey
    acceptable_states: tuple[JudgmentState, ...] = ()
    forbidden_states: tuple[JudgmentState, ...] = ()
    invariant_judgments: tuple[JudgmentKey, ...] = ()
    reference_variant: str | None = None
    degraded_reference: str | None = None
    direction: Literal["lower", "higher"] | None = None
    action_target: str | None = None

    @field_validator("acceptable_states", "forbidden_states", mode="before")
    @classmethod
    def canonical_states(cls, values: object) -> object:
        if isinstance(values, (tuple, list)):
            return tuple(
                STATE_ALIASES.get(value, value) if isinstance(value, str) else value
                for value in values
            )
        return values


class Observation(Frozen):
    judgments: tuple[Judgment, ...]
    authorized_anchors: tuple[Text, ...] = ()
    action_targets: tuple[Text, ...] = ()
    recognition_claim: bool | None = None
    action_annotation: Text = "No semantic annotation supplied"
    output_text: str = ""

    @model_validator(mode="after")
    def distinct(self) -> Self:
        if len({j.key for j in self.judgments}) != len(self.judgments):
            raise ValueError("Duplicate observed judgment")
        return self


class Metric(Frozen):
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)

    @model_validator(mode="after")
    def bounded(self) -> Self:
        if self.numerator > self.denominator:
            raise ValueError("Invalid metric counts")
        return self


class FeatureMetrics(Frozen):
    feature: Feature
    detection: Metric
    verification_change: Metric = Metric(numerator=0, denominator=0)
    invariance: Metric
    withholding: Metric
    restoration: Metric
    direction: Metric
    state: Metric
    attribution: Metric
    action: Metric


class BenchmarkResult(Frozen):
    metrics: tuple[FeatureMetrics, ...]
    invariant_violations: tuple[Text, ...]
    diagnostics: tuple[Text, ...]
    diagnostic_interpretation: Literal[
        "Flags require interpretation; recognition is not proof of contamination"
    ] = "Flags require interpretation; recognition is not proof of contamination"


class RunBudget(Frozen):
    max_calls: int = Field(ge=1, le=20)
    max_tokens: int = Field(ge=1)
    max_cost_usd: float = Field(ge=0)


class RunConfiguration(Frozen):
    mode: Literal["WORKBENCH", "BASELINE"]
    component: Literal["FULL", "Argument", "Study", "Literature", "Alternatives"] = "FULL"
    provider: Literal["fake", "openai"]
    model: Text
    parameters: tuple[tuple[Text, str | int | float | None], ...] = ()
    budget: RunBudget
    code_commit: Text
    task_version: Literal["benchmark-v1"] = "benchmark-v1"

    @model_validator(mode="after")
    def no_credentials(self) -> Self:
        allowed = {
            "timeout",
            "reasoning_effort",
            "max_output_tokens",
            "max_context_bytes",
            "max_input_tokens",
            "max_calls",
            "max_run_tokens",
            "retries",
            "input_rate",
            "cached_rate",
            "cache_write_rate",
            "output_rate",
            "price_date",
        }
        if len({k for k, _ in self.parameters}) != len(self.parameters):
            raise ValueError("Duplicate provider parameter")
        if any(k not in allowed for k, _ in self.parameters):
            raise ValueError("Only non-secret runtime parameters may be recorded")
        return self


class BenchmarkRun(Frozen):
    run_id: Text
    variant_id: Text
    benchmark_id: Text
    split: Split
    configuration: RunConfiguration
    package_hash: Hash
    package_version: Text
    variant_version: Text
    split_version: Text
    expectations_hash: Hash
    reference_run_ids: tuple[Text, ...] = ()
    packet_hash: Hash
    code_tree_hash: Hash
    policy_manifest_hash: Hash
    policy_implementation_version: Text
    variant_hash: Hash
    split_hash: Hash
    rubric_hash: Hash
    rubric_version: Text
    timestamp: Text
    duration_seconds: float = Field(ge=0)
    components: tuple[Text, ...]
    prompt_hashes: tuple[tuple[Text, Hash], ...]
    receipt: ProviderRun | None = None
    calls: int = Field(ge=0)
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    status: Literal["SUCCEEDED", "FAILED", "INTERRUPTED"]
    failure_type: str | None = None
    output_json: str | None = None
    policy_json: str | None = None
    observation: Observation | None = None
    result: BenchmarkResult | None = None


class FrozenExpectations(Frozen):
    variant_id: Text
    variant_hash: Hash
    expectations: tuple[BenchmarkExpectation, ...]


class BenchmarkPackage(Frozen):
    """Administrator exchange artifact; never passed to a model."""

    schema_version: Literal["benchmark-package-v1"] = "benchmark-package-v1"
    manifest: FrozenSplit
    projects: tuple[BenchmarkProject, ...]
    variants: tuple[BenchmarkVariant, ...]
    expectations: tuple[FrozenExpectations, ...]

    @model_validator(mode="after")
    def semantic_validation(self) -> Self:
        from benchmarks.variants import construct, content_hash, freeze, validate_import

        if freeze(self.projects, self.manifest.version) != self.manifest:
            raise ValueError("Package frozen manifest differs from canonical project identities")
        projects = {p.benchmark_id: p for p in self.projects}
        variants = {v.variant_id: v for v in self.variants}
        if len(projects) != len(self.projects) or len(variants) != len(self.variants):
            raise ValueError("Duplicate project or variant identity")
        if set(projects) != {a[0] for a in self.manifest.assignments}:
            raise ValueError("Manifest and package project identities differ")
        for project in self.projects:
            validate_import(project, self.manifest)
            blocks = {b.block_id for b in project.source_package.blocks}
            features = {f for b in project.source_package.blocks for f in b.features}
            if len({g.feature for g in project.gold}) != len(project.gold):
                raise ValueError("Duplicate gold feature")
            for gold in project.gold:
                if gold.feature not in features or not set(gold.source_anchors) <= blocks:
                    raise ValueError("Gold references unknown feature or source block")
        for variant in self.variants:
            variant_project = projects.get(variant.benchmark_id)
            if variant_project is None:
                raise ValueError("Unknown variant project")
            if (
                variant.split != variant_project.split
                or variant.package_hash != content_hash(variant_project)
                or variant.split_hash != content_hash(self.manifest)
            ):
                raise ValueError("Variant package or split binding differs")
            if variant.version != variant_project.version:
                raise ValueError("Variant/project version differs")
            parent = variant.mutation.parent_variant
            if parent is not None and (
                parent not in variants or variants[parent].benchmark_id != variant.benchmark_id
            ):
                raise ValueError("Unknown or cross-project mutation parent")
            regenerated = construct(
                variant_project,
                variant.mutation,
                variant.variant_id,
                self.manifest,
                variants.get(parent) if parent else None,
            )
            if regenerated != variant:
                raise ValueError("Variant packet or visibility differs from declared mutation")
        if len({e.variant_id for e in self.expectations}) != len(self.expectations):
            raise ValueError("Duplicate expectation artifact")
        if {e.variant_id for e in self.expectations} != set(variants):
            raise ValueError("Every variant requires frozen expectations")
        for artifact in self.expectations:
            if artifact.variant_hash != content_hash(variants[artifact.variant_id]):
                raise ValueError("Expectation variant hash differs")
            for expectation in artifact.expectations:
                owned = {
                    f
                    for b in projects[
                        variants[artifact.variant_id].benchmark_id
                    ].source_package.blocks
                    for f in b.features
                }
                if expectation.feature not in owned:
                    raise ValueError("Expectation references unknown feature")
                if expectation.behavior == "restore" and not expectation.degraded_reference:
                    raise ValueError("Restoration needs intact and degraded references")
                degraded_ref = expectation.degraded_reference
                if degraded_ref is not None and (
                    degraded_ref not in variants
                    or variants[degraded_ref].benchmark_id
                    != variants[artifact.variant_id].benchmark_id
                ):
                    raise ValueError("Unknown or cross-project degraded reference")
                ref = expectation.reference_variant
                if ref is not None and (
                    ref not in variants
                    or variants[ref].benchmark_id != variants[artifact.variant_id].benchmark_id
                ):
                    raise ValueError("Unknown or cross-project expectation reference")
        return self


class ReservationReport(Frozen):
    reservation_key: Hash
    run_id: Text
    status: Literal["INTERRUPTED_UNCERTAIN", "SUCCEEDED", "FAILED", "INTERRUPTED"]
    retry_allowed: Literal[False] = False


class InvalidCaseReport(Frozen):
    variant_id: Text
    status: Literal["INVALID_CASE"] = "INVALID_CASE"
    error_code: Text
