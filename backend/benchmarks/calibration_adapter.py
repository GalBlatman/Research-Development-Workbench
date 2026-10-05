"""Step-13 wire projection: one checker pass, canonical references resolved locally."""

from typing import Annotated, Any, Literal, TypeVar

from pydantic import BaseModel, Field, StrictInt

from domain.application import (
    CandidateReview,
    CheckDecision,
    CheckingTask,
    CheckResult,
)
from domain.models import (
    AttributedStatement,
    Frozen,
    ReviewContent,
    SourceReference,
    Text,
    Verification,
)
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
    prompt_configuration = "evaluation-v3/checking-compact-v1/workspace-v2/workspace-check-v2"
    proposed_review: CandidateReview | None = None

    def call(self, kind: str, payload: dict[str, Any], model: type[T]) -> T:
        result = super().call(kind, payload, model)
        if isinstance(result, CandidateReview):
            self.proposed_review = result
        return result

    def check(self, task: CheckingTask) -> CheckResult:
        packet_check(task.assessment_task.context)
        with provider_session(self):
            payload = task.model_dump(mode="json")
            payload["criteria"] = policy_contract(task.assessment_task)
            raw = self.call("checking-compact", payload, CompactCheckResult)
            # Ordinary AssessmentChecker still validates every target and expanded reference.
            return expand_checked(raw, task)
