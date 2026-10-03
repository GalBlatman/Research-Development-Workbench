from typing import Final, Protocol

from domain.application import CandidateReview, ContextPacket, Interpretation
from domain.models import (
    Assessment,
    Brief,
    EvaluationSnapshot,
    Rating,
    ReviewSummary,
    Status,
    Verification,
)

DEMO_IDEA = "Synthetic example: Why do fictional teams share knowledge? A proposed explanation links explicit requests to shared understanding, with conditions and rival predictions specified."
DEMO_SOURCE = "Synthetic predecessor: fictional teams may share knowledge because of shared incentives. This is a test fixture, not a published article or empirical evidence."
DISCLAIMER: Final = "Fake fixture output; no scientific assessment or semantic verification."


class ModelAdapter(Protocol):
    configuration: str

    def interpret(self, context: ContextPacket) -> object: ...

    def assess(
        self, context: ContextPacket, snapshot: EvaluationSnapshot, fixture: str
    ) -> object: ...


class FakeModel:
    configuration = "deterministic-fake-v1"

    def interpret(self, context: ContextPacket) -> object:
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
            ).model_dump(mode="json")
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
        ).model_dump(mode="json")

    def assess(self, context: ContextPacket, snapshot: EvaluationSnapshot, fixture: str) -> object:
        scored = fixture == "scored"
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
            for dim in range(1, 11)
        )
        return CandidateReview(
            assessment=Assessment(
                snapshot=snapshot,
                account_articulated=scored,
                study_assessable=False,
                ratings=ratings,
                findings=(),
            ),
            summary=ReviewSummary(
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
                fixture="scored" if scored else "limited",
                disclaimer=DISCLAIMER,
            ),
        ).model_dump(mode="json")


class OutputVerifier(Protocol):
    def interpretation(self, context: ContextPacket, candidate: Interpretation) -> None: ...

    def verify(
        self,
        context: ContextPacket,
        snapshot: EvaluationSnapshot,
        fixture: str,
        candidate: CandidateReview,
    ) -> Assessment: ...


class FixtureVerifier:
    """Checks a known fixture, never claims semantic verification of research."""

    def interpretation(self, context: ContextPacket, candidate: Interpretation) -> None:
        expected = Interpretation.model_validate(FakeModel().interpret(context))
        if candidate != expected:
            raise ValueError("Interpretation differs from declared fake fixture")

    def verify(
        self,
        context: ContextPacket,
        snapshot: EvaluationSnapshot,
        fixture: str,
        candidate: CandidateReview,
    ) -> Assessment:
        if fixture == "scored":
            drafts = tuple(p.text for p in context.passages if p.source.role == "project_draft")
            literature = tuple(p.text for p in context.passages if p.source.role == "literature")
            if drafts != (DEMO_IDEA,) or literature != (DEMO_SOURCE,):
                raise ValueError(
                    "Scored fixture requires the exact synthetic idea and literature; use limited review for other text"
                )
            if snapshot.project.route != "EXPLAIN" or snapshot.project.stage != "EARLY IDEA":
                raise ValueError("Scored fixture requires EXPLAIN / EARLY IDEA")
        expected = CandidateReview.model_validate(FakeModel().assess(context, snapshot, fixture))
        if candidate != expected:
            raise ValueError(
                "Invalid fake-model output: not the declared fixture; no automatic repairs"
            )
        # Supported denotes exact fixture conformance only; the report states its limit.
        data = candidate.assessment.model_dump()
        for rating in data["ratings"]:
            if rating["rating"] is not None:
                rating["verification"] = Verification.SUPPORTED
        return Assessment.model_validate(data)
