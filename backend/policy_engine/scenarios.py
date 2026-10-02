from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

from domain.models import Route
from policy_engine.engine import Evaluation

Base = Literal["IDEA", "PROJECT"]


@dataclass(frozen=True)
class Branch:
    name: str
    probability: Fraction
    evaluation: Evaluation | None
    description: str


@dataclass(frozen=True)
class Scenario:
    expected_strength: Fraction | None
    expected_change: Fraction | None
    no_change: Fraction
    reason: str


def strength(evaluation: Evaluation, base: Base) -> Fraction:
    if base not in ("IDEA", "PROJECT") or evaluation.route != Route.EXPLAIN:
        raise ValueError("Only comparable EXPLAIN IDEA/PROJECT scores can be used")
    score = evaluation.idea if base == "IDEA" else evaluation.project
    if score.value is None or evaluation.label == "BLOCKED AS STATED":
        raise ValueError("Branch has no scoreable current claim")
    return score.value


def expected_strength(
    current: Evaluation,
    base: Base,
    branches: tuple[Branch, ...],
    budget: str,
    probability_basis: str,
) -> Scenario:
    current_score = strength(current, base)
    if not budget.strip() or not probability_basis.strip():
        return Scenario(None, None, current_score, "Budget/probability basis not specified")
    if not branches or any(
        not isinstance(b.probability, Fraction)
        or not 0 <= b.probability <= 1
        or not b.description.strip()
        or not b.name.strip()
        for b in branches
    ):
        raise ValueError("Explicit bounded probabilities and described branches required")
    if len({b.name for b in branches}) != len(branches):
        raise ValueError("Outcome branches must be distinct")
    if sum(b.probability for b in branches) != 1:
        raise ValueError("Branch probabilities must sum exactly to one")
    if any(b.evaluation is None for b in branches):
        return Scenario(
            None, None, current_score, "STOP/incomplete branch without comparable alternative"
        )
    total = Fraction(0)
    for branch in branches:
        outcome = branch.evaluation
        assert outcome is not None
        if (
            outcome.route != current.route
            or outcome.stage != current.stage
            or outcome.policy_sha256 != current.policy_sha256
            or outcome.policy_manifest_sha256 != current.policy_manifest_sha256
        ):
            raise ValueError("Route, relevant stage and policy must match")
        total += branch.probability * strength(outcome, base)
    return Scenario(
        total, total - current_score, current_score, "Scenario index, not publication probability"
    )


def break_even(plus: Fraction, minus: Fraction, alternative: Fraction) -> Fraction | None:
    if plus == minus:
        return None
    if plus < minus:
        raise ValueError("Success score must exceed failure score")
    return (alternative - minus) / (plus - minus)
