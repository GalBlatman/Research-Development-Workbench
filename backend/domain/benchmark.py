"""Versioned administrator contracts. No scientific judgments inferred by this module."""

from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, model_validator

from domain.models import Frozen, Hash, ProviderRun, Route, Stage, Text
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
    status: Text
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
    provenance: Text = "Administrator-specified synthetic transformation"


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


class FrozenSplit(Frozen):
    version: Text
    assignments: tuple[tuple[Text, Split, Hash], ...]

    @model_validator(mode="after")
    def unique(self) -> Self:
        if len({a[0] for a in self.assignments}) != len(self.assignments):
            raise ValueError("Same underlying project assigned twice")
        return self


class Judgment(Frozen):
    key: Text
    state: Text
    value: float | None = None
    verification: Text = "unresolved"
    source_refs: tuple[Text, ...] = ()


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
    judgment: Text
    acceptable_states: tuple[Text, ...] = ()
    forbidden_states: tuple[Text, ...] = ()
    invariant_judgments: tuple[Text, ...] = ()
    reference_variant: str | None = None
    direction: Literal["lower", "higher"] | None = None
    action_target: str | None = None


class Observation(Frozen):
    judgments: tuple[Judgment, ...]
    authorized_anchors: tuple[Text, ...] = ()
    action_targets: tuple[Text, ...] = ()
    recognition_claim: bool | None = None
    action_annotation: Text = "No semantic annotation supplied"
    output_text: str = ""


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
