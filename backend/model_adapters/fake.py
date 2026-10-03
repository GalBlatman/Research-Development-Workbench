from typing import Final

from domain.application import (
    AssessmentFields,
    AssessmentTask,
    CandidateReview,
    CheckedReview,
    Interpretation,
    InterpretationTask,
    ProposedAssessment,
)
from domain.models import (
    Brief,
    Rating,
    ReviewContent,
    Status,
    Verification,
)
from model_adapters.contracts import ModelAdapter as ModelAdapter
from model_adapters.contracts import OutputVerifier as OutputVerifier

DEMO_IDEA = "Synthetic example: Why do fictional teams share knowledge? A proposed explanation links explicit requests to shared understanding, with conditions and rival predictions specified."
DEMO_SOURCE = "Synthetic predecessor: fictional teams may share knowledge because of shared incentives. This is a test fixture, not a published article or empirical evidence."
DISCLAIMER: Final = "Fake fixture output; no scientific assessment or semantic verification."


class FakeModel:
    configuration = "deterministic-fake-v1"

    def interpret(self, task: InterpretationTask) -> Interpretation:
        context = task.context
        draft = tuple(p.text for p in context.passages if p.source.role == "project_draft")
        if draft == (DEMO_IDEA,):
            return Interpretation(
                brief=Brief(
                    question="Why do fictional teams share knowledge?",
                    core_insight="A request-driven explanation is proposed for shared understanding (synthetic fixture).",
                    intended_contribution="An explanatory account with specified conditions and rival predictions; not verified.",
                ),
                limitations=(
                    DISCLAIMER,
                    "Fixed interpretation of the exact synthetic idea fixture.",
                ),
            )
        return Interpretation(
            brief=Brief(
                question="What specific knowledge would this project add?",
                core_insight="No distinctive insight has been assessed by this fake adapter.",
                intended_contribution="Unresolved; confirm or correct the intended contribution.",
            ),
            limitations=(
                DISCLAIMER,
                "This fixed proposal does not extract meaning from your text.",
            ),
        )

    def assess(self, task: AssessmentTask) -> CandidateReview:
        context = task.context
        # Exact internal fixture identity only; never a scientific keyword heuristic.
        drafts = tuple(p.text for p in context.passages if p.source.role == "project_draft")
        literature = tuple(p.text for p in context.passages if p.source.role == "literature")
        scored = (
            drafts == (DEMO_IDEA,)
            and literature == (DEMO_SOURCE,)
            and context.project.route == "EXPLAIN"
            and context.project.stage == "EARLY IDEA"
        )
        ratings = tuple(
            Rating(
                dimension=dim,
                rating=5 if scored and dim <= 7 else None,
                status=Status.ASSESSED if scored and dim <= 7 else Status.PENDING,
                rationale="Fixed synthetic judgment for exercising the backend policy engine."
                if scored and dim <= 7
                else "No substantive inspection by the fake adapter.",
                main_limitation=DISCLAIMER,
                inspected_material=("exact-synthetic-fixture",) if scored and dim <= 7 else (),
                verification=Verification.UNRESOLVED,
            )
            for dim in (task.dimensions or tuple(range(1, 11)))
        )
        return CandidateReview(
            assessment=ProposedAssessment(
                account_articulated=scored,
                study_assessable=False,
                ratings=ratings,
                findings=(),
            ),
            summary=ReviewContent(
                contribution="Preserve the distinction between the proposed explanation and its rival (synthetic fixture only)."
                if scored
                else "No distinctive contribution has yet been assessed; preserve the original question for clarification.",
                obstacle="The study and evidence have not been assessed."
                if scored
                else "The intended question and contribution remain unresolved in this fixed interpretation.",
                limitations=(
                    DISCLAIMER,
                    "Supplied excerpts are not an exhaustive literature review.",
                    *context.exclusions,
                ),
                next_action="Clarify the intended contribution and inspect the nearest relevant predecessor.",
                deliverable="A bounded question and an attributed overlap/departure note; resources remain unspecified.",
                outcome_branches=(
                    "A defensible departure is identified.",
                    "The question needs reformulation.",
                    "Inspection remains incomplete; retain pending status.",
                ),
                disclaimer=DISCLAIMER,
            ),
        )


class FixtureVerifier:
    """Exact fixture conformance only; no semantic research verification."""

    def interpretation(self, task: InterpretationTask, candidate: Interpretation) -> None:
        if candidate != FakeModel().interpret(task):
            raise ValueError("Interpretation differs from declared fake fixture")

    def verify(self, task: AssessmentTask, candidate: CandidateReview) -> AssessmentFields:
        if candidate != FakeModel().assess(task):
            raise ValueError(
                "Invalid fake-model output: not the internal fixture; no automatic repairs"
            )
        data = candidate.assessment.model_dump()
        for rating in data["ratings"]:
            if rating["rating"] is not None:
                rating["verification"] = Verification.SUPPORTED
        return AssessmentFields.model_validate(data)

    def review(self, task: AssessmentTask, candidate: CandidateReview) -> CheckedReview:
        return CheckedReview(assessment=self.verify(task, candidate), summary=candidate.summary)
