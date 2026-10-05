"""Step-13 wire projection: one checker pass, canonical references resolved locally."""

from copy import deepcopy
from typing import Annotated, Any, Literal, TypeVar

from pydantic import BaseModel, Field, StrictInt

from domain.application import (
    CandidateReview,
    CheckDecision,
    CheckingTask,
    CheckResult,
    Interpretation,
)
from domain.models import (
    AttributedStatement,
    Frozen,
    ReviewContent,
    SourceReference,
    Text,
    Verification,
)
from model_adapters.checking import ATTRIBUTION_ROLES
from model_adapters.openai import OpenAIAdapter, packet_check, policy_contract
from model_adapters.runtime import ProviderFailure, provider_session

T = TypeVar("T", bound=BaseModel)


class CompactDecision(Frozen):
    target: Text
    disposition: Verification
    reason: Text
    source_refs: tuple[Annotated[StrictInt, Field(ge=0)], ...]


class CompactCheckResult(Frozen):
    decisions: tuple[CompactDecision, ...]
    summary: ReviewContent
    obstacle_action: Literal["confirm", "qualify", "narrow", "withdraw"] = "confirm"
    proposed_objections: tuple[AttributedStatement, ...] = ()


def expand_checked(raw: CompactCheckResult, task: CheckingTask) -> CheckResult:
    passages = task.assessment_task.context.passages
    decisions = []
    for decision in raw.decisions:
        if any(not 0 <= index < len(passages) for index in decision.source_refs):
            raise ProviderFailure("MISSING_SOURCE_SUPPORT")
        refs = tuple(
            SourceReference(
                document_id=passages[index].source.document_id,
                version=passages[index].anchor.version,
                anchor_id=passages[index].anchor.anchor_id,
            )
            for index in decision.source_refs
        )
        decisions.append(
            CheckDecision(
                target=decision.target,
                disposition=decision.disposition,
                reason=decision.reason,
                source_refs=refs,
            )
        )
    return CheckResult(
        decisions=tuple(decisions),
        summary=raw.summary,
        obstacle_action=raw.obstacle_action,
        proposed_objections=raw.proposed_objections,
    )


class CalibrationAdapter(OpenAIAdapter):
    prompt_configuration = (
        "evaluation-v3/checking-compact-v1/workspace-v2/workspace-check-v2/"
        "packet-citations-v2/role-bound-statements-v1/bounded-output-v1"
    )
    proposed_review: CandidateReview | None = None
    proposed_interpretation: Interpretation | None = None

    def call(self, kind: str, payload: dict[str, Any], model: type[T]) -> T:
        payload = {
            **payload,
            "criteria": {
                **payload.get("criteria", {}),
                "output_contract_version": "bounded-output-v1",
                "citation_contract_version": "packet-citations-v2/role-bound-statements-v1",
                "output_contract": (
                    "Keep narrative fields concise within the supplied output limit. "
                    "Use one or two short sentences per rationale, statement, limitation or action field; "
                    "do not repeat the packet or rubric. Preserve every required judgment, "
                    "checking target, evidence distinction, citation and diagnostic-action field. "
                    "Do not omit scientific support to save space. inspected_material and source_refs "
                    "may select only identifiers from the supplied passages. Missing material is "
                    "unavailable, never a new citation identifier."
                ),
            },
        }
        result = super().call(kind, payload, model)
        if isinstance(result, CandidateReview):
            self.proposed_review = result
        elif isinstance(result, Interpretation):
            self.proposed_interpretation = result
        return result

    def response_schema(self, payload: dict[str, Any], model: type[T]) -> dict[str, Any]:
        schema = super().response_schema(payload, model)
        context = payload.get("context") or payload.get("assessment_task", {}).get("context")
        passages = context.get("passages", []) if context else []
        if not passages:
            return schema
        documents = sorted({p["source"]["document_id"] for p in passages})
        anchors = sorted({p["anchor"]["anchor_id"] for p in passages})
        versions = sorted({p["anchor"]["version"] for p in passages})
        definitions = schema.get("$defs", {})
        reference = definitions.get("SourceReference", {}).get("properties", {})
        for key, values in (
            ("document_id", documents),
            ("anchor_id", anchors),
            ("version", versions),
        ):
            if key in reference:
                reference[key]["enum"] = values
        for definition in definitions.values():
            inspected = definition.get("properties", {}).get("inspected_material")
            if inspected:
                inspected["items"]["enum"] = anchors
        reference_definition = definitions.get("SourceReference")
        if reference_definition:

            def exact_reference(passage: dict[str, Any]) -> dict[str, Any]:
                result: dict[str, Any] = deepcopy(reference_definition)
                for key, value in (
                    ("document_id", passage["source"]["document_id"]),
                    ("version", passage["anchor"]["version"]),
                    ("anchor_id", passage["anchor"]["anchor_id"]),
                ):
                    result["properties"][key]["enum"] = [value]
                return result

            definitions["SourceReference"] = {"anyOf": [exact_reference(p) for p in passages]}
            statement = definitions.get("AttributedStatement")
            if statement:
                options = []
                for kind in statement["properties"]["kind"]["enum"]:
                    option = deepcopy(statement)
                    option["properties"]["kind"]["enum"] = [kind]
                    if kind in ATTRIBUTION_ROLES:
                        admitted = [
                            p for p in passages if p["source"]["role"] in ATTRIBUTION_ROLES[kind]
                        ]
                        if not admitted:
                            continue
                        refs = option["properties"]["source_refs"]
                        refs["minItems"] = 1
                        refs["items"] = {"anyOf": [exact_reference(p) for p in admitted]}
                    options.append(option)
                definitions["AttributedStatement"] = {"anyOf": options}
        # Enums reduce invented identifiers; ordinary checking still resolves exact triples,
        # source roles and semantic support. Membership alone never verifies a claim.
        return schema

    def check(self, task: CheckingTask) -> CheckResult:
        packet_check(task.assessment_task.context)
        with provider_session(self):
            payload = task.model_dump(mode="json")
            payload["criteria"] = policy_contract(task.assessment_task)
            raw = self.call("checking-compact", payload, CompactCheckResult)
            # Ordinary AssessmentChecker still validates every target and expanded reference.
            return expand_checked(raw, task)
