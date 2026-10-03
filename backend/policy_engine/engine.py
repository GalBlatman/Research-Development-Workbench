from dataclasses import dataclass
from fractions import Fraction

from domain.models import (
    Assessment,
    Commitment,
    GateState,
    Route,
    Stage,
    Status,
    Truth,
    Verification,
)
from policy_engine.manifest import Manifest


@dataclass(frozen=True)
class Score:
    value: Fraction | None
    status: Status
    reason: str

    @property
    def displayed(self) -> int | None:
        if self.value is None:
            return None
        return (2 * self.value.numerator + self.value.denominator) // (2 * self.value.denominator)


@dataclass(frozen=True)
class Trace:
    rule_id: str
    value: Truth | GateState
    consequence: str
    reasoning: str
    source: str
    dimension: int | None = None
    before: int | None = None
    after: int | None = None


@dataclass(frozen=True)
class Gate:
    name: str
    state: GateState
    provisional: bool
    missed: tuple[str, ...]
    commitment: Commitment | None = None


@dataclass(frozen=True)
class Evaluation:
    route: Route
    stage: Stage
    snapshot_id: str
    policy_sha256: str
    policy_manifest_sha256: str
    idea_uncapped: Score
    idea: Score
    study: Score
    project_uncapped: Score
    project_before_caps: Score
    project: Score
    effective_ratings: tuple[tuple[int, int | None], ...]
    gates: tuple[Gate, ...]
    trace: tuple[Trace, ...]
    label: str
    endorsement_stage: str
    editorial_status: str = "UNCALIBRATED"


def conjunction(values: list[Truth]) -> Truth:
    if Truth.FALSE in values:
        return Truth.FALSE
    return Truth.UNKNOWN if Truth.UNKNOWN in values else Truth.TRUE


def evaluate(assessment: Assessment, manifest: Manifest) -> Evaluation:
    """Interpretive findings are inputs; only deterministic consequences occur here."""
    if assessment.snapshot.policy_sha256 != manifest.canonical_sha256:
        raise ValueError("Snapshot policy hash differs from manifest")
    if assessment.snapshot.policy_version != manifest.version:
        raise ValueError("Snapshot policy version differs from manifest")
    if assessment.snapshot.policy_manifest_sha256 != manifest.sha256:
        raise ValueError("Snapshot executable manifest hash differs from manifest")
    if assessment.snapshot.policy_implementation_version != manifest.implementation_version:
        raise ValueError("Snapshot implementation version differs from manifest")
    specs = {r.id: r for r in manifest.rules}
    facts = {f.rule_id: f for f in assessment.findings}
    unknown_ids = set(facts) - set(specs)
    if unknown_ids:
        raise ValueError("Unknown policy findings: " + ", ".join(sorted(unknown_ids)))
    route = assessment.snapshot.project.route
    stage = assessment.snapshot.project.stage
    trace: list[Trace] = []

    def fact(identifier: str) -> Truth:
        finding = facts.get(identifier)
        return finding.effective_value if finding else Truth.UNKNOWN

    def record(identifier: str, value: Truth, consequence: str) -> None:
        finding = facts.get(identifier)
        spec = specs[identifier]
        trace.append(
            Trace(
                identifier,
                value,
                consequence,
                finding.reasoning
                if finding
                else "Derived from typed inputs"
                if identifier
                in {
                    "ROUTE-TOTAL",
                    "DISCOVERY-PENDING",
                    "UNINSPECTED-BLOCK",
                    "HIGH-SCORE-BENCHMARK",
                    "EDITORIAL-UNCALIBRATED",
                }
                else "No supported finding supplied",
                spec.source,
            )
        )

    def adverse_clear(identifier: str) -> Truth:
        value = fact(identifier)
        return {Truth.TRUE: Truth.FALSE, Truth.FALSE: Truth.TRUE, Truth.UNKNOWN: Truth.UNKNOWN}[
            value
        ]

    discovery = (
        route == Route.EXPLAIN
        and not assessment.account_articulated
        and stage in (Stage.EARLY_IDEA, Stage.DISCOVERY)
    )
    theory = route == Route.EXPLAIN and not discovery
    applicable = set(range(1, 8)) if theory else set()
    if assessment.study_assessable:
        applicable.update(range(8, 11))
    record(
        "ROUTE-TOTAL",
        Truth.TRUE if route != Route.EXPLAIN else Truth.FALSE,
        "Idea/project not applicable" if route != Route.EXPLAIN else "EXPLAIN routing",
    )
    record(
        "DISCOVERY-PENDING",
        Truth.TRUE if discovery else Truth.FALSE,
        "Pre-explanation stage: await articulated account"
        if discovery
        else "No discovery exemption; use applicable supplied judgments",
    )
    ratings: dict[int, int | None] = {i: None for i in range(1, 11)}
    input_ratings = {r.dimension: r for r in assessment.ratings}
    conditional: set[int] = set()
    for dimension, rating in input_ratings.items():
        if dimension not in applicable:
            continue
        if (
            rating.rating is not None
            and rating.verification == Verification.SUPPORTED
            and rating.status not in (Status.PENDING, Status.UNRESOLVED, Status.NOT_APPLICABLE)
        ):
            ratings[dimension] = rating.rating
            if rating.status in (Status.CONDITIONAL, Status.CONTESTED):
                conditional.add(dimension)
            if rating.rating >= 8 and (rating.benchmark is None or not rating.benchmark.supported):
                ratings[dimension] = None
                record(
                    "HIGH-SCORE-BENCHMARK",
                    Truth.TRUE,
                    f"d{dimension} withheld; benchmark or reassessment required",
                )
    if not any(t.rule_id == "HIGH-SCORE-BENCHMARK" for t in trace):
        unverified_high = any(
            r.dimension in applicable
            and r.rating is not None
            and r.rating >= 8
            and r.verification != Verification.SUPPORTED
            for r in assessment.ratings
        )
        record(
            "HIGH-SCORE-BENCHMARK",
            Truth.UNKNOWN if unverified_high else Truth.FALSE,
            "Unverified exceptional request"
            if unverified_high
            else "No unsupported applicable exceptional rating",
        )
    record(
        "UNINSPECTED-BLOCK",
        Truth.TRUE if any(ratings[i] is None for i in applicable) else Truth.FALSE,
        "Withhold each unavailable affected block; never substitute zero",
    )
    idea_caps: list[int] = []
    project_caps: list[int] = []
    for identifier, cap in (
        ("PREMISE-NO-BASIS", 39),
        ("NO-ADVANCE", 39),
        ("NO-CONSEQUENTIAL-STAKE", 69),
    ):
        value = fact(identifier)
        if theory and value == Truth.TRUE:
            idea_caps.append(cap)
            if identifier == "PREMISE-NO-BASIS" and ratings[1] is not None:
                original_d1 = ratings[1]
                ratings[1] = min(ratings[1], 3)
                if original_d1 != ratings[1]:
                    trace.append(
                        Trace(
                            identifier,
                            Truth.TRUE,
                            "Dimension 1 maximum 3",
                            facts[identifier].reasoning,
                            specs[identifier].source,
                            dimension=1,
                            before=original_d1,
                            after=ratings[1],
                        )
                    )
        record(
            identifier,
            value,
            f"Idea cap {cap}"
            if theory and value == Truth.TRUE
            else "No cap inferred from false/unknown or inapplicable finding",
        )
    for identifier in ("DESIGN-MISMATCH", "INFERENCE-UNSUPPORTED"):
        value = fact(identifier)
        if theory and value == Truth.TRUE:
            project_caps.append(39)
        record(
            identifier,
            value,
            "Project cap 39" if theory and value == Truth.TRUE else "No punitive cap inferred",
        )
    for identifier in ("AUDIENCE-QUESTION", "PREMISE-CONDITIONAL", "PREMISE-CONTRADICTED"):
        record(
            identifier,
            fact(identifier),
            {
                "AUDIENCE-QUESTION": "Withhold intellectual assessment when true",
                "PREMISE-CONDITIONAL": "No unqualified endorsement/full-study commitment when true",
                "PREMISE-CONTRADICTED": "Block explanatory version as stated when true",
            }[identifier],
        )
    if fact("PROMISE-OVERREACH") == Truth.TRUE:
        # An interpretive mapping is required, rather than a new penalty/keyword rule.
        mapped = any(
            fact(i) == Truth.TRUE
            for i in (
                "PREMISE-NO-BASIS",
                "NO-ADVANCE",
                "NO-CONSEQUENTIAL-STAKE",
                "DESIGN-MISMATCH",
                "INFERENCE-UNSUPPORTED",
            )
        )
        if not mapped:
            raise ValueError("PROMISE-OVERREACH needs the corresponding supported existing rule")
    record(
        "PROMISE-OVERREACH", fact("PROMISE-OVERREACH"), "Use mapped existing rule; no extra penalty"
    )

    def block(ids: range, available: bool, na: bool = False) -> Score:
        if na:
            return Score(None, Status.NOT_APPLICABLE, "Not applicable to this route")
        if not available or any(ratings[i] is None for i in ids):
            return Score(None, Status.PENDING, "Required account/study/rating unavailable")
        dims = [d for d in manifest.dimensions if d.id in ids]
        total = sum((Fraction(d.weight * int(ratings[d.id] or 0)) for d in dims), Fraction(0))
        status = Status.CONDITIONAL if any(i in conditional for i in ids) else Status.ASSESSED
        return Score(10 * total / sum(d.weight for d in dims), status, "Assessed eligible block")

    idea_uncapped = block(range(1, 8), theory, route != Route.EXPLAIN)
    if theory and fact("AUDIENCE-QUESTION") == Truth.TRUE:
        idea_uncapped = Score(None, Status.PENDING, "Audience/question must be specified")
    idea = Score(
        min([idea_uncapped.value, *map(Fraction, idea_caps)])
        if idea_uncapped.value is not None
        else None,
        idea_uncapped.status,
        "Lowest applicable idea cap" if idea_caps else idea_uncapped.reason,
    )
    if theory and fact("PREMISE-CONDITIONAL") == Truth.TRUE and idea.value is not None:
        idea = Score(idea.value, Status.CONDITIONAL, "PREMISE-CONDITIONAL")
    study = block(range(8, 11), assessment.study_assessable)

    def combine(i: Score, d: Score) -> Score:
        if route != Route.EXPLAIN:
            return Score(None, Status.NOT_APPLICABLE, "Not applicable to this route")
        if i.value is None or d.value is None:
            return Score(None, Status.PENDING, "Both eligible blocks required")
        status = (
            Status.CONDITIONAL if Status.CONDITIONAL in (i.status, d.status) else Status.ASSESSED
        )
        return Score((i.value + d.value) / 2, status, "50/50 convention")

    project_uncapped = combine(idea_uncapped, study)
    project_before = combine(idea, study)
    project = Score(
        min([project_before.value, *map(Fraction, project_caps)])
        if project_before.value is not None
        else None,
        project_before.status,
        "Lowest applicable project cap" if project_caps else project_before.reason,
    )
    gates: list[Gate] = []

    def numeric_gate(
        name: str,
        score: Score,
        floor: int,
        floors: tuple[tuple[int, int], ...],
        requirements: list[Truth],
    ) -> Gate:
        numeric: list[Truth] = [
            Truth.UNKNOWN
            if score.value is None
            else Truth.TRUE
            if score.value >= floor
            else Truth.FALSE
        ]
        for dim, minimum in floors:
            value = ratings[dim]
            numeric.append(
                Truth.UNKNOWN if value is None else Truth.TRUE if value >= minimum else Truth.FALSE
            )
        state = GateState(conjunction(numeric + requirements))
        # Range extrema only flag a possible gate change, never change the central score.
        crossing = False
        score_is_study = score is study
        block_ids = range(8, 11) if score_is_study else range(1, 8)
        relevant = sorted(set(block_ids) | {dimension for dimension, _ in floors})
        for dim in relevant:
            r = input_ratings.get(dim)
            if r and r.plausible_range and r.plausible_range[0] != r.plausible_range[1]:
                lows = dict(ratings)
                highs = dict(ratings)
                for k in relevant:
                    candidate = input_ratings.get(k)
                    if candidate and candidate.plausible_range and ratings[k] is not None:
                        lows[k], highs[k] = candidate.plausible_range
                        if k == 1 and fact("PREMISE-NO-BASIS") == Truth.TRUE:
                            lows[k], highs[k] = (
                                min(int(lows[k] or 0), 3),
                                min(int(highs[k] or 0), 3),
                            )

                def passes(values: dict[int, int | None]) -> bool:
                    if any(values[k] is None for k in block_ids):
                        return False
                    weights = [d for d in manifest.dimensions if d.id in block_ids]
                    tested = sum(
                        (Fraction(d.weight * int(values[d.id] or 0)) for d in weights), Fraction(0)
                    ) * Fraction(10, sum(d.weight for d in weights))
                    if not score_is_study:
                        tested = min([tested, *map(Fraction, idea_caps)])
                    return tested >= floor and all(
                        values[d] is not None and int(values[d] or 0) >= f for d, f in floors
                    )

                crossing = passes(lows) != passes(highs)
                break
        missed = tuple(
            f"condition-{n + 1}:{v.value}"
            for n, v in enumerate(numeric + requirements)
            if v != Truth.TRUE
        )
        if crossing:
            missed += tuple(
                f"d{d}:range={input_ratings[d].plausible_range}"
                for d in relevant
                if d in input_ratings and input_ratings[d].plausible_range
            )
        return Gate(
            name, state, crossing or state == GateState.UNKNOWN or bool(conditional), missed
        )

    idea_clear = [
        adverse_clear(i)
        for i in (
            "AUDIENCE-QUESTION",
            "PREMISE-NO-BASIS",
            "PREMISE-CONDITIONAL",
            "PREMISE-CONTRADICTED",
            "NO-ADVANCE",
            "NO-CONSEQUENTIAL-STAKE",
        )
    ]
    stage_clear = [adverse_clear(i) for i in ("DESIGN-MISMATCH", "INFERENCE-UNSUPPORTED")]
    stage_clear.append(fact("STAGE-PREREQUISITES"))
    profiles = {p.id: p for p in manifest.profiles}
    for name in ("strong_idea", "exceptional_idea"):
        profile = profiles[name]
        requirements = list(idea_clear)
        if name == "exceptional_idea":
            requirements.append(fact("PREDECESSORS-INSPECTED"))
        if route != Route.EXPLAIN:
            gate = Gate(
                name,
                GateState.NOT_APPLICABLE,
                False,
                ("Explanatory excellence does not apply to this route",),
            )
        elif discovery:
            gate = Gate(
                name,
                GateState.PENDING,
                False,
                ("Await articulated explanatory account at pre-explanation stage",),
            )
        else:
            gate = numeric_gate(
                name, idea, int(profile.minimum_total or 0), profile.floors, requirements
            )
        gates.append(gate)
    for name, parent in (("strong_project", gates[0]), ("exceptional_project", gates[1])):
        profile = profiles[name]
        requirements = (
            [Truth(parent.state), *stage_clear]
            if parent.state in (GateState.TRUE, GateState.FALSE, GateState.UNKNOWN)
            else stage_clear
        )
        if parent.state in (GateState.NOT_APPLICABLE, GateState.PENDING):
            gate = Gate(name, parent.state, False, parent.missed)
        else:
            gate = numeric_gate(
                name, study, int(profile.minimum_total or 0), profile.floors, requirements
            )
        gates.append(
            Gate(gate.name, gate.state, gate.provisional or parent.provisional, gate.missed)
        )
    submission_requirements = [
        Truth.TRUE if stage == Stage.COMPLETED else Truth.FALSE,
        *stage_clear[:-1],
        fact("SUPPORT-VERIFIED"),
        fact("PROMISE-ALIGNED"),
        adverse_clear("AUDIENCE-QUESTION"),
        adverse_clear("PROMISE-OVERREACH"),
    ]
    submission_requirements.append(Truth.TRUE if study.value is not None else Truth.UNKNOWN)
    if theory:
        submission_requirements += idea_clear + [fact("CONSEQUENTIAL-STAKE")]
        submission = numeric_gate(
            "submission",
            idea,
            int(profiles["submission_explain"].minimum_total or 0),
            profiles["submission_explain"].floors,
            submission_requirements,
        )
    elif route in (Route.ESTABLISH, Route.TEST):
        route_complete = len(assessment.route_assessment) == len(manifest.route_items) and all(
            item.status == "ADEQUATE FOR STAGE" for item in assessment.route_assessment
        )
        submission_requirements += [
            Truth.TRUE if route_complete else Truth.FALSE,
            fact("DELIVERED-SUPPORT"),
            fact("ROUTE-NO-HARD-STOP"),
        ]
        submission = numeric_gate(
            "submission", study, 0, profiles["submission_route"].floors, submission_requirements
        )
    else:
        submission = Gate(
            "submission",
            GateState.PENDING if discovery else GateState.UNKNOWN,
            False,
            ("Articulated account required",),
        )
    gates.append(submission)
    proposal_requirements = [
        fact("CONTRIBUTION-STUDY-SPECIFIED"),
        fact("PILOT-PREREQUISITES"),
        adverse_clear("STAGE-MISMATCH"),
    ]
    if route == Route.EXPLAIN:
        proposal_requirements += [
            adverse_clear("PREMISE-CONTRADICTED"),
            adverse_clear("PREMISE-NO-BASIS"),
            adverse_clear("PREMISE-CONDITIONAL"),
        ]
    proposal = GateState(conjunction(proposal_requirements))
    commitment = Commitment.ORDINARY if proposal == GateState.TRUE else Commitment.WITHHELD
    if route == Route.EXPLAIN and fact("PREMISE-NO-BASIS") == Truth.TRUE:
        commitment = Commitment.PREMISE_VERIFY_OR_REFORMULATE
    elif route == Route.EXPLAIN and fact("PREMISE-CONDITIONAL") == Truth.TRUE:
        commitment = Commitment.BOUNDED_PREMISE_CHECK
    if route == Route.EXPLAIN and fact("PREMISE-CONTRADICTED") == Truth.TRUE:
        commitment = Commitment.WITHHELD
    gates.append(
        Gate(
            "proposal_readiness",
            proposal,
            proposal == GateState.UNKNOWN,
            ()
            if proposal == GateState.TRUE
            else ("Stage prerequisites unmet/unresolved or premise restricts commitment",),
            commitment,
        )
    )
    route_development = conjunction(
        [fact("KNOWLEDGE-NEED"), fact("IDENTIFIABLE-INCREMENT"), fact("CREDIBLE-BOUNDED-ACTION")]
    )
    route_uninspected = len(assessment.route_assessment) != len(manifest.route_items) or any(
        r.status == "NOT INSPECTED" for r in assessment.route_assessment
    )
    gates.append(
        Gate(
            "bounded_route_development",
            GateState(route_development),
            route_development == Truth.UNKNOWN or route_uninspected,
            (),
        )
    )
    for gate in gates:
        trace.append(
            Trace(
                gate.name,
                gate.state,
                "Not applicable"
                if gate.state == GateState.NOT_APPLICABLE
                else "Pending"
                if gate.state == GateState.PENDING
                else "Provisional/borderline"
                if gate.provisional
                else "Gate evaluated",
                "; ".join(gate.missed) or "Requirements satisfied",
                "v4 §§2.2, 8.4–8.5",
            )
        )
    label = "NO EXCELLENCE ENDORSEMENT"
    for gate in gates[:4]:
        if gate.state == GateState.TRUE:
            label = (
                gate.name.upper()
                + (
                    (" COMPLETED" if stage == Stage.COMPLETED else " PROPOSED")
                    if gate.name.endswith("project")
                    else ""
                )
                + (" PROVISIONAL" if gate.provisional else "")
            )
    if theory and fact("PREMISE-CONDITIONAL") == Truth.TRUE:
        label = "PREMISE-CONDITIONAL"
    if theory and fact("PREMISE-CONTRADICTED") == Truth.TRUE:
        label = "BLOCKED AS STATED"
    for identifier, spec in specs.items():
        if identifier not in {entry.rule_id for entry in trace}:
            record(identifier, fact(identifier), spec.consequence)
    record("EDITORIAL-UNCALIBRATED", Truth.TRUE, "Editorial target remains UNCALIBRATED")
    return Evaluation(
        route,
        stage,
        assessment.snapshot.snapshot_id,
        manifest.canonical_sha256,
        manifest.sha256,
        idea_uncapped,
        idea,
        study,
        project_uncapped,
        project_before,
        project,
        tuple(ratings.items()),
        tuple(gates),
        tuple(trace),
        label,
        "COMPLETED" if stage == Stage.COMPLETED else "PROPOSED",
    )
