"""Explicit expectation comparisons; no reconstruction or keyword science scoring."""

from collections import defaultdict

from domain.benchmark import (
    BenchmarkExpectation,
    BenchmarkProject,
    BenchmarkResult,
    BenchmarkRun,
    FeatureMetrics,
    Judgment,
    Metric,
    Observation,
)


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
            return (item.state.casefold(), item.value, item.verification) if item else None

        changed = signature(j) != signature(old) if j is not None and old is not None else None
        allowed = (
            (
                j.state.casefold() in {s.casefold() for s in e.acceptable_states}
                if e.acceptable_states
                else True
            )
            and j.state.casefold() not in {s.casefold() for s in e.forbidden_states}
            if j is not None
            else False
        )
        state = allowed if e.acceptable_states or e.forbidden_states else None
        invariant = []
        for key in e.invariant_judgments:
            if key in previous and key in judgments:
                same = signature(previous[key]) == signature(judgments[key])
                invariant.append(same)
                if not same:
                    violations.append(key)
        direction = None
        if e.direction and old and j and old.value is not None and j.value is not None:
            direction = j.value < old.value if e.direction == "lower" else j.value > old.value
        withholding = None
        if e.behavior in ("withhold", "unresolved", "not_inspected", "refuse_infer"):
            withholding = bool(
                j
                and j.value is None
                and allowed
                and (
                    j.state.casefold()
                    in ("PENDING", "NOT_INSPECTED", "UNRESOLVED", "missing", "not_inspected")
                    or j.verification == "unresolved"
                )
            )
        metrics.append(
            FeatureMetrics(
                feature=e.feature,
                detection=count(changed if e.behavior in ("detect", "downgrade") else None),
                invariance=Metric(numerator=sum(invariant), denominator=len(invariant)),
                withholding=count(withholding),
                restoration=count(
                    not changed if changed is not None and e.behavior == "restore" else None
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
                    e.action_target in observed.action_targets if e.action_target else None
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


def aggregate(runs: tuple[BenchmarkRun, ...]) -> dict[str, object]:
    """Paper is the aggregation unit; variants remain nested case observations."""
    groups: dict[str, list[BenchmarkRun]] = defaultdict(list)
    for run in runs:
        groups[run.benchmark_id].append(run)
    papers = {}
    names = (
        "detection",
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
            records = [r for r in nested if r.configuration.mode == mode]
            values = {}
            for name in names:
                counts = [getattr(m, name) for r in records if r.result for m in r.result.metrics]
                n, d = sum(c.numerator for c in counts), sum(c.denominator for c in counts)
                values[name] = {"numerator": n, "denominator": d, "rate": n / d if d else None}
            modes[mode] = {"cases": len(records), "metrics": values}
        papers[paper] = modes
    return {"paper_count": len(groups), "case_count": len(runs), "papers": papers}


def equivalent_diagnostic(first: Observation, paraphrased: Observation) -> tuple[str, ...]:
    """Caller certifies substantive equivalence; difference alone is not contamination."""
    a = {j.key: (j.state, j.value, j.verification) for j in first.judgments}
    b = {j.key: (j.state, j.value, j.verification) for j in paraphrased.judgments}
    return tuple(
        "Equivalent-packet judgment changed: " + key
        for key in sorted(a.keys() | b.keys())
        if a.get(key) != b.get(key)
    )
