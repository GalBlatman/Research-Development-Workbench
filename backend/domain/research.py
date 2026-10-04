"""Research-task records and UI contracts; no scoring or scientific heuristics."""

from typing import Literal, Self

from pydantic import model_validator

from domain.application import CheckDecision, ContextPacket, RevisionRequest
from domain.models import (
    EvidenceState,
    Frozen,
    Origin,
    ResearchRecord,
    Route,
    SourceReference,
    Stage,
    Text,
    validate_diagnostic_fields,
)

WORKSPACES = (
    "Overview",
    "Brief",
    "Literature",
    "Argument",
    "Alternatives",
    "Study",
    "Usefulness",
    "Review",
    "Next Actions",
    "History",
)
FIELDS: dict[str, dict[str, str]] = {
    "Brief": {
        "puzzle": "Phenomenon / puzzle",
        "question": "Research question",
        "audience": "Audience / conversation",
        "contribution": "Proposed answer / contribution",
        "constructs": "Core constructs",
        "account": "Mechanism / account (where applicable)",
        "setting": "Empirical setting",
        "study_status": "Study status",
        "perspective": "Whose perspective defines the problem?",
        "scope": "Claimed scope",
        "basis": "Concrete basis",
        "known": "What is known?",
        "unknown": "What needs learning?",
    },
    "Literature": {
        "source_claim": "What the source claims",
        "user_interpretation": "User interpretation",
        "model_synthesis": "Model synthesis / unresolved inference",
        "relation": "Relation to the project",
        "novelty": "Overlap / departure",
        "conditions": "Relevant conditions",
        "overlap": "Overlap",
        "departure": "Departure",
        "why_matters": "Why the departure matters",
        "coverage": "Unresolved coverage / source needed",
    },
    "Argument": {
        "puzzle": "Puzzle / knowledge need",
        "claim": "Focal claim / answer",
        "constructs": "Construct definitions / neighboring concepts",
        "account": "Because-logic / explanatory account",
        "sequence": "Logical / causal sequence",
        "assumptions": "Assumptions",
        "scope": "Scope / boundaries",
        "units": "Units / levels",
        "timing": "Timing",
        "implications": "Predictions / observable implications",
        "establish_task": "What will be established?",
        "test_claim": "Existing claim to test",
    },
    "Alternatives": {
        "focal": "Focal explanation / claim",
        "alternative": "Alternative account",
        "plausibility": "Why this account is plausible",
        "assumption": "Source or explicit assumption",
        "implications": "What it implies",
        "shared_outcomes": "Shared outcomes",
        "distinguishing": "Distinguishing implications",
        "weakening": "Evidence that could weaken it",
        "evidence": "Discriminating evidence needed",
        "adjudication": "Does the current design adjudicate this?",
        "unresolved": "Unresolved alternatives / assumptions",
        "changes": "Proposed study changes",
    },
    "Study": {
        "claim": "What claim can this design support?",
        "unit": "Unit of analysis",
        "sample": "Setting / sample / cases",
        "measures": "Constructs and measures / documentation",
        "time": "Temporal ordering",
        "comparison": "Comparison / counterfactual",
        "inference": "Identification / inferential logic",
        "availability": "Data availability",
        "evidence_phase": "Evidence phase",
        "analysis": "Planned / reported analysis",
        "limitations": "Material design limitations",
        "quantitative_support": "Quantitative support audit: independent changes, overlap, influence, sensitivity, bounds",
        "qualitative_support": "Qualitative / process audit: cases, episodes, contrasts, direct vs inferred process",
        "checks": "Checks: EXPECTED / VERIFIED (reported) / PENDING / NOT APPLICABLE",
    },
    "Usefulness": {
        "audience": "Who could use the insight?",
        "decision": "Decision / action informed",
        "change": "What changes if true?",
        "boundaries": "Boundaries on use",
        "support": "Usefulness support",
        "scholarly_distinction": "How this differs from scholarly contribution",
    },
    "Next Actions": {
        "task": "Concrete bounded task",
        "reason": "Why it matters",
        "judgment": "Unresolved judgment it can change",
        "input": "Required input / evidence",
        "output": "Expected deliverable",
        "workspace": "Affected workspace",
        "dependency": "Affected dependency",
        "order": "Order",
        "resources": "Resources / constraints",
        "branches": "Supporting / conflicting / inconclusive outcomes",
        "criterion": "Success criterion",
        "outcome": "Reported outcome / evidence",
        "state": "Action state",
    },
}
CHOICES: dict[str, tuple[str, ...]] = {
    "relation": (
        "closest predecessor",
        "neighboring work",
        "possible rival",
        "supporting source",
        "boundary / construct source",
        "unresolved overlap",
    ),
    "novelty": (
        "already stated",
        "immediate application",
        "nontrivial assembly",
        "distinct explanatory change",
        "unresolved overlap",
    ),
    "evidence_phase": ("proposed", "completed (user-reported)"),
    "support": ("demonstrated (user-reported)", "plausible", "proposed", "unsupported"),
    "adjudication": ("yes", "no", "unclear"),
    "state": (
        "proposed",
        "selected",
        "in progress",
        "submitted for check",
        "checked (reported)",
        "deferred",
        "abandoned",
    ),
    "workspace": WORKSPACES,
}
# Conservative dependency groups from specification 12.2, not rubric rules.
AFFECTED: dict[str, tuple[str, ...]] = {
    "Brief": (
        "Brief",
        "Literature",
        "Argument",
        "Alternatives",
        "Study",
        "Usefulness",
        "Review",
        "Next Actions",
    ),
    "Literature": ("Literature", "Argument", "Alternatives", "Review", "Next Actions"),
    "Argument": ("Argument", "Literature", "Alternatives", "Study", "Review", "Next Actions"),
    "Alternatives": ("Alternatives", "Argument", "Study", "Review", "Next Actions"),
    "Study": ("Study", "Review", "Next Actions"),
    "Usefulness": ("Usefulness", "Review", "Next Actions"),
    "Next Actions": ("Next Actions",),
    "resources": ("Next Actions",),
}
DIMENSIONS: dict[str, tuple[int, ...]] = {
    "Brief": (1, 2, 3),
    "Literature": (2, 3),
    "Argument": (4, 5),
    "Alternatives": (6,),
    "Study": (8, 9, 10),
    "Usefulness": (7,),
}


def validate_record(record: ResearchRecord, route: Route) -> None:
    allowed = set(FIELDS[record.workspace])
    if route != Route.EXPLAIN and record.workspace in ("Brief", "Argument"):
        allowed -= {"account", "sequence"}
    if any(f.key not in allowed for f in record.fields):
        raise ValueError("Field is not applicable to this workspace / route")
    for field in record.fields:
        if field.key in CHOICES and field.text and field.text not in CHOICES[field.key]:
            raise ValueError("Invalid structured field choice")


class RecordRequest(RevisionRequest):
    record: ResearchRecord
    object_id: str | None = None
    source_refs: tuple[SourceReference, ...] = ()
    # None preserves existing dependencies; an explicit empty tuple removes them.
    depends_on: tuple[str, ...] | None = None
    change: Literal["substantive", "wording", "resources"] = "substantive"


class DecisionRequest(RevisionRequest):
    action: Literal["accepted", "rejected", "superseded"]
    reason: Text = "User decision"
    edited_record: ResearchRecord | None = None


class SettingsRequest(RevisionRequest):
    route: Route
    stage: Stage
    session_goal: Text
    evaluation_target: Literal["manuscript_as_written", "current_project_as_clarified"]


class DevelopRequest(RevisionRequest):
    workspace: Literal[
        "Brief", "Literature", "Argument", "Alternatives", "Study", "Usefulness", "Next Actions"
    ]
    object_id: str | None = None
    instruction: Text = "Propose the smallest useful improvement, preserving uncertainty"


class WorkspaceTask(Frozen):
    schema_version: Literal["rdw-task-1"] = "rdw-task-1"
    task: Literal["DevelopWorkspace"] = "DevelopWorkspace"
    context: ContextPacket
    workspace: Literal[
        "Brief", "Literature", "Argument", "Alternatives", "Study", "Usefulness", "Next Actions"
    ]
    target_object_id: str | None
    instruction: Text
    allowed_fields: tuple[str, ...]


class ResultGrounding(Frozen):
    field: Text
    existing_object_id: str | None = None
    source_refs: tuple[SourceReference, ...] = ()

    @model_validator(mode="after")
    def bounded(self) -> Self:
        if not self.existing_object_id and not self.source_refs:
            raise ValueError(
                "Reported-result grounding requires existing author input or admitted source refs"
            )
        return self


class WorkspaceProposal(Frozen):
    record: ResearchRecord
    reason: Text
    limitations: tuple[Text, ...]
    result_grounding: tuple[ResultGrounding, ...] = ()

    @model_validator(mode="after")
    def proposed_not_evidence(self) -> Self:
        if any(
            f.origin not in (Origin.INFERENCE, Origin.SUGGESTION)
            or f.state == EvidenceState.DOCUMENTED
            for f in self.record.fields
        ):
            raise ValueError("Model proposals cannot become user text or verified evidence")
        reported = {
            f.key
            for f in self.record.fields
            if f.claim_kind == "reported_result"
            or (f.key == "evidence_phase" and f.text == "completed (user-reported)")
            or (f.key == "support" and f.text == "demonstrated (user-reported)")
        }
        if not reported <= {g.field for g in self.result_grounding}:
            raise ValueError("Generated reported results require explicit existing-input grounding")
        if self.record.workspace == "Next Actions":
            required = {
                "task",
                "reason",
                "judgment",
                "input",
                "output",
                "workspace",
                "dependency",
                "branches",
            }
            present = {f.key for f in self.record.fields if f.text and f.text.strip()}
            if not required <= present:
                raise ValueError(
                    "Incomplete diagnostic Next Action: " + ", ".join(sorted(required - present))
                )
            fields = {f.key: f.text for f in self.record.fields if f.text is not None}
            validate_diagnostic_fields(
                tuple(
                    fields[k]
                    for k in (
                        "judgment",
                        "task",
                        "input",
                        "output",
                        "branches",
                        "reason",
                        "dependency",
                    )
                )
            )
        return self


class WorkspaceCheckingTask(Frozen):
    context: ContextPacket
    candidate: WorkspaceProposal
    targets: tuple[str, ...]


class WorkspaceCheckResult(Frozen):
    decisions: tuple[CheckDecision, ...]
    limitations: tuple[Text, ...]


class WorkspaceCheckRequest(RevisionRequest):
    workspace: Literal["Brief", "Literature", "Argument", "Alternatives", "Study", "Usefulness"]


class WorkspaceCatalog(Frozen):
    workspaces: tuple[Text, ...]
    fields: dict[str, dict[str, str]]
    choices: dict[str, tuple[str, ...]]
    targeted_workspaces: tuple[str, ...]
    note: Text
