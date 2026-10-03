from typing import Protocol

from domain.application import (
    AssessmentFields,
    AssessmentTask,
    CandidateReview,
    CheckedReview,
    Interpretation,
    InterpretationTask,
)


class ModelAdapter(Protocol):
    configuration: str

    def interpret(self, task: InterpretationTask) -> Interpretation: ...
    def assess(self, task: AssessmentTask) -> CandidateReview: ...


class OutputVerifier(Protocol):
    def interpretation(self, task: InterpretationTask, candidate: Interpretation) -> None: ...
    def verify(self, task: AssessmentTask, candidate: CandidateReview) -> AssessmentFields: ...
    def review(self, task: AssessmentTask, candidate: CandidateReview) -> CheckedReview: ...
