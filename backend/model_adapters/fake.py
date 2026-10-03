from typing import Final

from domain.application import (
    AssessmentFields,
    AssessmentTask,
    CandidateReview,
    CheckDecision,
    CheckedReview,
    Interpretation,
    InterpretationTask,
    ProposedAssessment,
)
from domain.models import (
    Brief,
    DiagnosticAction,
    EvidenceState,
    Origin,
    Rating,
    ResearchField,
    ResearchRecord,
    ReviewContent,
    SourceReference,
    Status,
    Verification,
)
from domain.research import (
    CHOICES,
    ResultGrounding,
    WorkspaceCheckResult,
    WorkspaceProposal,
    WorkspaceTask,
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
            and not any(
                isinstance(o.payload, ResearchRecord) and o.adoption == "accepted"
                for o in context.project.objects
            )
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
                diagnostic_action=DiagnosticAction(
                    issue="Contribution and attributed departure remain uninspected",
                    task="Clarify the intended contribution and inspect the nearest relevant predecessor.",
                    required_input="Author question and admitted original literature passage",
                    deliverable="A bounded question and an attributed overlap/departure note; resources remain unspecified.",
                    outcome_branches=(
                        "A defensible departure is identified.",
                        "The question needs reformulation.",
                        "Inspection remains incomplete; retain pending status.",
                    ),
                ),
                disclaimer=DISCLAIMER,
            ),
        )

    def develop(self, task: WorkspaceTask) -> WorkspaceProposal:
        existing = next(
            (
                o
                for o in task.context.project.objects
                if o.object_id == task.target_object_id and isinstance(o.payload, ResearchRecord)
            ),
            None,
        )
        if existing and isinstance(existing.payload, ResearchRecord):
            fields = tuple(
                f.model_copy(
                    update={"origin": Origin.SUGGESTION, "state": EvidenceState.UNINSPECTED}
                )
                for f in existing.payload.fields
            )
        elif task.workspace == "Literature":
            passage = next(
                (p for p in task.context.passages if p.source.role == "literature"), None
            )
            if passage:
                ref = SourceReference(
                    document_id=passage.source.document_id,
                    version=passage.anchor.version,
                    anchor_id=passage.anchor.anchor_id,
                )
                fields = (
                    ResearchField(
                        key="source_claim",
                        text=passage.text,
                        origin=Origin.SUGGESTION,
                        source_refs=(ref,),
                    ),
                    ResearchField(
                        key="model_synthesis",
                        text="Fixed fixture: overlap remains unresolved; no semantic comparison",
                        origin=Origin.SUGGESTION,
                    ),
                    ResearchField(
                        key="relation", text="unresolved overlap", origin=Origin.SUGGESTION
                    ),
                )
            else:
                fields = (
                    ResearchField(
                        key="coverage",
                        text="No admitted literature passage; novelty remains unresolved",
                        origin=Origin.SUGGESTION,
                    ),
                )
        elif task.workspace == "Next Actions":
            values = {
                "task": "Inspect the nearest supplied predecessor passage",
                "reason": "Resolve the attributed overlap before changing the promise",
                "judgment": "Whether the proposed departure is supported remains unresolved",
                "input": "Admitted original source passage and the author's current question",
                "output": "A short attributed overlap / departure note",
                "workspace": "Literature",
                "dependency": "Current question and supplied source version",
                "order": "1",
                "branches": "Support, disagreement or incomplete inspection remain possible",
                "state": "proposed",
            }
            fields = tuple(
                ResearchField(key=k, text=v, origin=Origin.SUGGESTION) for k, v in values.items()
            )
        else:
            key = task.allowed_fields[0]
            fields = (
                ResearchField(
                    key=key,
                    text=CHOICES[key][0]
                    if key in CHOICES
                    else "Fixed offline proposal: clarify this record using the original text; no scientific inference has been made.",
                    origin=Origin.SUGGESTION,
                ),
            )
        return WorkspaceProposal(
            record=ResearchRecord(
                workspace=task.workspace,
                title="Proposed " + task.workspace + " note",
                fields=fields,
            ),
            reason="Fixed synthetic development fixture; adopt only as representation",
            limitations=(DISCLAIMER,),
            result_grounding=tuple(
                ResultGrounding(field=f.key, existing_object_id=existing.object_id)
                for f in fields
                if existing
                and (
                    f.claim_kind == "reported_result"
                    or (f.key == "evidence_phase" and f.text == "completed (user-reported)")
                    or (f.key == "support" and f.text == "demonstrated (user-reported)")
                )
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
        data["account_articulated_verification"] = Verification.SUPPORTED
        data["study_assessable_verification"] = Verification.SUPPORTED
        for rating in data["ratings"]:
            if rating["rating"] is not None:
                rating["verification"] = Verification.SUPPORTED
        return AssessmentFields.model_validate(data)

    def review(self, task: AssessmentTask, candidate: CandidateReview) -> CheckedReview:
        return CheckedReview(assessment=self.verify(task, candidate), summary=candidate.summary)

    def workspace(self, task: WorkspaceTask, candidate: WorkspaceProposal) -> WorkspaceCheckResult:
        if candidate != FakeModel().develop(task):
            raise ValueError("Invalid fake workspace proposal")
        return WorkspaceCheckResult(
            decisions=tuple(
                CheckDecision(
                    target=f.key,
                    disposition=Verification.UNRESOLVED,
                    reason=DISCLAIMER,
                    source_refs=f.source_refs,
                )
                for f in candidate.record.fields
            ),
            limitations=(DISCLAIMER,),
        )
