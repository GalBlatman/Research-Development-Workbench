from typing import Literal

from domain.models import Commitment, Frozen, GateState, Route, Stage, Status, Truth


class ExactValue(Frozen):
    numerator: int
    denominator: int


class ScoreView(Frozen):
    value: ExactValue | None
    displayed: int | None
    status: Status
    reason: str


class TraceView(Frozen):
    rule_id: str
    value: Truth | GateState
    consequence: str
    reasoning: str
    source: str
    dimension: int | None = None
    before: int | None = None
    after: int | None = None


class GateView(Frozen):
    name: str
    state: GateState
    provisional: bool
    missed: tuple[str, ...]
    commitment: Commitment | None = None


class PolicyResult(Frozen):
    route: Route
    stage: Stage
    snapshot_id: str
    policy_sha256: str
    policy_manifest_sha256: str
    idea_uncapped: ScoreView
    idea: ScoreView
    study: ScoreView
    project_uncapped: ScoreView
    project_before_caps: ScoreView
    project: ScoreView
    effective_ratings: tuple[tuple[int, int | None], ...]
    gates: tuple[GateView, ...]
    trace: tuple[TraceView, ...]
    label: str
    endorsement_stage: str
    policy_version: str
    policy_implementation_version: str
    policy_engine: Literal["rdw-python-policy-engine"] = "rdw-python-policy-engine"
    editorial_status: Literal["UNCALIBRATED"]
