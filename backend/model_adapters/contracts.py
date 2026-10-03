from typing import Protocol

from domain.application import (
    AssessmentFields,
    AssessmentTask,
    CandidateReview,
    CheckedReview,
    Interpretation,
    InterpretationTask,
)
from domain.research import WorkspaceCheckResult, WorkspaceProposal, WorkspaceTask


class ModelAdapter(Protocol):
    configuration: str

    def interpret(self, task: InterpretationTask) -> Interpretation: ...
    def assess(self, task: AssessmentTask) -> CandidateReview: ...
    def develop(self, task: WorkspaceTask) -> WorkspaceProposal: ...


class OutputVerifier(Protocol):
    def interpretation(self, task: InterpretationTask, candidate: Interpretation) -> None: ...
    def verify(self, task: AssessmentTask, candidate: CandidateReview) -> AssessmentFields: ...
    def review(self, task: AssessmentTask, candidate: CandidateReview) -> CheckedReview: ...
    def workspace(
        self, task: WorkspaceTask, candidate: WorkspaceProposal
    ) -> WorkspaceCheckResult: ...
