"""Explicit expectation comparisons; no reconstruction or keyword science scoring."""

from collections import defaultdict
from typing import Any

from domain.benchmark import (
    BenchmarkExpectation,
    BenchmarkProject,
    BenchmarkResult,
    BenchmarkRun,
    FeatureMetrics,
    Judgment,
    JudgmentState,
    Metric,
    Observation,
)

WITHHOLDING_STATES: frozenset[JudgmentState] = frozenset(
    (
        "unresolved",
        "not_inspected",
        "NOT INSPECTED",
        "pending",
        "UNKNOWN",
    )
)
ROUTE_ORDER = {"BLOCKING": 0, "DEVELOPMENT NEEDED": 1, "ADEQUATE FOR STAGE": 2}


def is_withholding(judgment: Judgment) -> bool:
    if judgment.scientific_state is None and judgment.state == "proposed":
        # Historical observations retain the prior explicit-check interpretation.
        return (
            judgment.value is None
            and judgment.checking_performed
            and judgment.verification == "unresolved"
        )
    state = judgment.scientific_state or judgment.state
    return judgment.value is None and state in WITHHOLDING_STATES


def count(value: bool | None) -> Metric:
    return Metric(numerator=int(value is True), denominator=int(value is not None))


def compare(
    observed: Observation,
    expectations: tuple[BenchmarkExpectation, ...],
    references: dict[str, Observation],
    project: BenchmarkProject,
) -> BenchmarkResult:
    judgments = {j.key: j for j in observed.judgments}
    metrics = []
    violations = []
    for e in expectations:
        j = judgments.get(e.judgment)
        reference = references.get(e.reference_variant or "")
        previous = {x.key: x for x in reference.judgments} if reference else {}
        old = previous.get(e.judgment)

        def signature(item: Judgment | None) -> object:
            if item is None:
                return None
            if item.key.startswith("statement:") and item.content is not None:
                # Checker-driven epistemic disposition does not rewrite the assertion.
                return (item.value, item.content, item.statement_kind)
            return (item.scientific_state or item.state, item.value, item.content)

        changed = signature(j) != signature(old) if reference is not None and (j or old) else None
        science = (j.scientific_state or j.state) if j else None
        allowed = bool(j) and (
            (science in e.acceptable_states if e.acceptable_states else True)
            and science not in e.forbidden_states
            and (
                science in e.acceptable_scientific_states
                if e.acceptable_scientific_states
                else True
            )
            and science not in e.forbidden_scientific_states
        )
        science_constrained = bool(
            e.acceptable_states
            or e.forbidden_states
            or e.acceptable_scientific_states
            or e.forbidden_scientific_states
        )
        state = allowed if science_constrained else None
        checker_applicable = bool(
            j and j.evaluator_mode != "BASELINE" and j.verification is not None
        )
        verification_constrained = bool(
            e.acceptable_verification_states or e.forbidden_verification_states
        )
        verification_allowed = (
            (
                j.verification in e.acceptable_verification_states
                if e.acceptable_verification_states
                else True
            )
            and j.verification not in e.forbidden_verification_states
            if j and checker_applicable and verification_constrained
            else None
        )
        adoption_allowed = (
            (j.adoption in e.acceptable_adoption_states if e.acceptable_adoption_states else True)
            and j.adoption not in e.forbidden_adoption_states
            if j and (e.acceptable_adoption_states or e.forbidden_adoption_states)
            else None
        )
        verification_changed = (
            j.verification != old.verification
            if j
            and old
            and checker_applicable
            and old.evaluator_mode != "BASELINE"
            and old.verification is not None
            else None
        )
        invariant = []
        for key in e.invariant_judgments:
            if reference is not None and (key in previous or key in judgments):
                same = signature(previous.get(key)) == signature(judgments.get(key))
                invariant.append(same)
                if not same:
                    violations.append(key)
        direction = None
        if e.direction and old and j and old.value is not None and j.value is not None:
            direction = j.value < old.value if e.direction == "lower" else j.value > old.value
        degraded = references.get(e.degraded_reference or "")
        degraded_judgment = (
            next((x for x in degraded.judgments if x.key == e.judgment), None) if degraded else None
        )
        degraded_changed = (
            old is not None
            and degraded is not None
            and signature(old) != signature(degraded_judgment)
        )
        if e.behavior == "unchanged" and changed is not None:
            invariant.append(signature(old) == signature(j))
            if signature(old) != signature(j):
                violations.append(e.judgment)
        downgrade = None
        if e.behavior == "downgrade" and j and old and e.direction != "higher":
            if j.key.startswith("rating:") and old.value is not None and j.value is not None:
                downgrade = j.value < old.value
            elif j.key.startswith("route:"):
                new_state, old_state = (
                    j.scientific_state or j.state,
                    old.scientific_state or old.state,
                )
                if new_state in ROUTE_ORDER and old_state in ROUTE_ORDER:
                    downgrade = ROUTE_ORDER[new_state] < ROUTE_ORDER[old_state]
            if downgrade is not None:
                downgrade = bool(downgrade and allowed)
        withholding = None
        if e.behavior in ("withhold", "unresolved", "not_inspected", "refuse_infer"):
            withholding = bool(j and allowed and is_withholding(j))
        metrics.append(
            FeatureMetrics(
                feature=e.feature,
                verification_change=count(verification_changed),
                verification_state=count(verification_allowed),
                adoption_state=count(adoption_allowed),
                verification_expectation=count(
                    verification_changed == (e.verification_change == "changed")
                    if e.verification_change and verification_changed is not None
                    else None
                ),
                detection=count(
                    downgrade
                    if e.behavior == "downgrade"
                    else changed
                    if e.behavior == "detect"
                    else None
                ),
                invariance=Metric(numerator=sum(invariant), denominator=len(invariant)),
                withholding=count(withholding),
                restoration=count(
                    (not changed and degraded_changed)
                    if changed is not None
                    and old is not None
                    and degraded is not None
                    and e.behavior == "restore"
                    else None
                ),
                direction=count(direction),
                state=count(state),
                attribution=Metric(
                    numerator=sum(
                        ref in observed.authorized_anchors for ref in (j.source_refs if j else ())
                    ),
                    denominator=len(j.source_refs) if j else 0,
                ),
                action=count(
                    e.action_target in observed.action_targets
                    if e.action_target and observed.action_targets is not None
                    else None
                ),
            )
        )
    diagnostics = []
    if observed.recognition_claim:
        diagnostics.append("Evaluator claimed recognition (explicit annotation)")
    for identity in project.source_package.identifying_metadata:
        if identity in observed.output_text:
            diagnostics.append("Identifying metadata reproduced")
    for feature in project.gold:
        if not feature.observable and feature.content in observed.output_text:
            diagnostics.append("Nonobservable gold text reproduced; exact-match diagnostic only")
    return BenchmarkResult(
        metrics=tuple(metrics),
        invariant_violations=tuple(sorted(set(violations))),
        diagnostics=tuple(sorted(set(diagnostics))),
    )


def aggregate(
    runs: tuple[BenchmarkRun, ...], annotations: tuple[object, ...] = ()
) -> dict[str, object]:
    """Paper is the aggregation unit; variants remain nested case observations."""
    groups: dict[str, list[BenchmarkRun]] = defaultdict(list)
    for run in runs:
        groups[run.benchmark_id].append(run)
    papers: dict[str, Any] = {}
    names = (
        "detection",
        "verification_change",
        "verification_state",
        "verification_expectation",
        "adoption_state",
        "invariance",
        "withholding",
        "restoration",
        "direction",
        "state",
        "attribution",
        "action",
    )
    for paper, nested in sorted(groups.items()):
        modes = {}
        for mode in sorted({r.configuration.mode for r in nested}):
            raw_records = [r for r in nested if r.configuration.mode == mode]
            from benchmarks.variants import content_hash

            unique = {}
            for r in sorted(raw_records, key=lambda r: (r.timestamp, r.run_id)):
                unique[
                    (r.variant_id, content_hash(r.configuration), content_hash(r.prompt_hashes))
                ] = r
            records = list(unique.values())
            values = {}
            for name in names:
                counts = [getattr(m, name) for r in records if r.result for m in r.result.metrics]
                n, d = sum(c.numerator for c in counts), sum(c.denominator for c in counts)
                values[name] = {"numerator": n, "denominator": d, "rate": n / d if d else None}
            configurations: dict[str, Any] = {}
            for r in records:
                identity = content_hash((r.configuration.model_dump(mode="json"), r.prompt_hashes))
                group = configurations.setdefault(
                    identity,
                    {
                        "configuration": r.configuration.model_dump(mode="json"),
                        "prompt_hashes": r.prompt_hashes,
                        "cases": [],
                        "failed": 0,
                        "interrupted": 0,
                    },
                )
                group["cases"].append(
                    {
                        "variant_id": r.variant_id,
                        "run_id": r.run_id,
                        "status": r.status,
                        "failure_type": r.failure_type,
                        "metrics": r.result.model_dump(mode="json") if r.result else None,
                    }
                )
                group["failed"] += int(r.status == "FAILED")
                group["interrupted"] += int(r.status == "INTERRUPTED")
            for configuration_id, group in configurations.items():
                matching = [
                    r
                    for r in records
                    if content_hash((r.configuration.model_dump(mode="json"), r.prompt_hashes))
                    == configuration_id
                ]
                attempts = [
                    r
                    for r in raw_records
                    if content_hash((r.configuration.model_dump(mode="json"), r.prompt_hashes))
                    == configuration_id
                ]
                group["failed"] = sum(r.status == "FAILED" for r in attempts)
                group["interrupted"] = sum(r.status == "INTERRUPTED" for r in attempts)
                group["attempts"] = [
                    {
                        "run_id": r.run_id,
                        "variant_id": r.variant_id,
                        "status": r.status,
                        "failure_type": r.failure_type,
                    }
                    for r in attempts
                ]
                group["metrics"] = {}
                for name in names:
                    counts = [
                        getattr(metric, name)
                        for record in matching
                        if record.result
                        for metric in record.result.metrics
                    ]
                    numerator, denominator = (
                        sum(c.numerator for c in counts),
                        sum(c.denominator for c in counts),
                    )
                    group["metrics"][name] = {
                        "numerator": numerator,
                        "denominator": denominator,
                        "rate": numerator / denominator if denominator else None,
                    }
            modes[mode] = {
                "cases": len(records),
                "metrics": values if len(configurations) == 1 else None,
                "configurations": configurations,
                "excluded_duplicate_reruns": len(raw_records) - len(records),
                "successful_cases": sum(r.status == "SUCCEEDED" for r in records),
                "final_successful_variants": len(
                    {r.variant_id for r in records if r.status == "SUCCEEDED"}
                ),
                "attempts": [
                    {
                        "run_id": r.run_id,
                        "variant_id": r.variant_id,
                        "status": r.status,
                        "failure_type": r.failure_type,
                    }
                    for r in raw_records
                ],
                "failed": sum(r.status == "FAILED" for r in raw_records),
                "interrupted": sum(r.status == "INTERRUPTED" for r in raw_records),
                "reference_unavailable": sum(bool(r.reference_unavailable) for r in records),
            }
        papers[paper] = modes
    return {
        "invalid_cases": sum(getattr(a, "status", None) == "INVALID_CASE" for a in annotations),
        "orphan_reservations": sum(
            getattr(a, "status", None) == "INTERRUPTED_UNCERTAIN" for a in annotations
        ),
        "annotations": [a.model_dump(mode="json") for a in annotations if hasattr(a, "model_dump")],
        "paper_count": len(groups),
        "case_count": sum(mode["cases"] for paper in papers.values() for mode in paper.values()),
        "submitted_run_count": len(runs),
        "papers": papers,
    }


def equivalent_diagnostic(first: Observation, paraphrased: Observation) -> tuple[str, ...]:
    """Caller certifies substantive equivalence; difference alone is not contamination."""
    a = {j.key: (j.state, j.value, j.verification) for j in first.judgments}
    b = {j.key: (j.state, j.value, j.verification) for j in paraphrased.judgments}
    return tuple(
        "Equivalent-packet judgment changed: " + key
        for key in sorted(a.keys() | b.keys())
        if a.get(key) != b.get(key)
    )
