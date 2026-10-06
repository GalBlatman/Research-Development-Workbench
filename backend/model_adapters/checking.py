import json
from collections.abc import Iterable

from domain.application import (
    AssessmentFields,
    AssessmentTask,
    AttributedStatement,
    CandidateReview,
    CheckedReview,
    CheckingTask,
    ContextPacket,
    Interpretation,
    InterpretationTask,
)
from domain.models import SourceReference, StructuralCheck, Truth, Verification
from domain.research import (
    WorkspaceCheckingTask,
    WorkspaceCheckResult,
    WorkspaceProposal,
    WorkspaceTask,
)
from domain.sources import SourceRole
from model_adapters.openai import DERIVED, PROMPTS, OpenAIAdapter, packet_check, policy_contract
from model_adapters.runtime import ProviderFailure

ATTRIBUTION_ROLES = {
    "source_backed": frozenset(
        (
            SourceRole.LITERATURE,
            SourceRole.PREDECESSOR,
            SourceRole.ALTERNATIVE,
            SourceRole.METHOD,
            SourceRole.CONTEXT,
        )
    ),
    "user_project": frozenset((SourceRole.DRAFT, SourceRole.AUTHOR_NOTE)),
}


class AssessmentChecker:
    """Structural source resolution plus one explicitly limited semantic model check."""

    def __init__(self, adapter: OpenAIAdapter):
        self.adapter = adapter

    def promise_mapping(
        self,
        task: AssessmentTask,
        candidate: CandidateReview,
        supported_targets: set[str] | None = None,
    ) -> None:
        if task.policy_version != "5":
            return
        findings = {f.rule_id: f for f in candidate.assessment.findings}
        promise = findings.get("PROMISE-OVERREACH")
        if promise is None or promise.value != Truth.TRUE:
            return
        if supported_targets is not None and "finding:PROMISE-OVERREACH" not in supported_targets:
            return
        eligible = policy_contract(task).get("promise_mapping", {}).get("basis_rules", ())
        if not any(
            (basis := findings.get(rule)) is not None
            and basis.value == Truth.TRUE
            and (supported_targets is None or "finding:" + rule in supported_targets)
            for rule in eligible
        ):
            raise ProviderFailure(
                "UNMAPPED_PROMISE_OVERREACH"
                if supported_targets is None
                else "UNSUPPORTED_PROMISE_MAPPING"
            )

    def references(self, context: ContextPacket, refs: Iterable[SourceReference]) -> None:
        allowed = {
            (p.source.document_id, p.anchor.version, p.anchor.anchor_id) for p in context.passages
        }
        for ref in refs:
            assert isinstance(ref, SourceReference)
            if (ref.document_id, ref.version, ref.anchor_id) not in allowed:
                raise ProviderFailure("MISSING_SOURCE_SUPPORT")

    def statements(self, context: ContextPacket, items: tuple[AttributedStatement, ...]) -> None:
        ids = [s.statement_id for s in items]
        if len(ids) != len(set(ids)):
            raise ProviderFailure("DUPLICATE_STATEMENT")
        roles = {
            (p.source.document_id, p.anchor.version, p.anchor.anchor_id): p.source.role
            for p in context.passages
        }
        for statement in items:
            self.references(context, statement.source_refs)
            if statement.kind in ("source_backed", "user_project"):
                if not statement.source_refs:
                    raise ProviderFailure("MISSING_SOURCE_SUPPORT")
                expected_roles = ATTRIBUTION_ROLES[statement.kind]
                if any(
                    roles[(r.document_id, r.version, r.anchor_id)] not in expected_roles
                    for r in statement.source_refs
                ):
                    raise ProviderFailure("ATTRIBUTION_ROLE_MISMATCH")

    def interpretation(self, task: InterpretationTask, candidate: Interpretation) -> None:
        packet_check(task.context)
        self.statements(task.context, candidate.statements)

    def verify(self, task: AssessmentTask, candidate: CandidateReview) -> AssessmentFields:
        return self.review(task, candidate).assessment

    def validate_candidate(self, task: AssessmentTask, candidate: CandidateReview) -> None:
        packet_check(task.context)
        self.statements(task.context, candidate.statements)
        dimensions = {
            d
            for d in (
                task.dimensions if task.targeted_component else (task.dimensions or range(1, 11))
            )
            if task.context.project.route == "EXPLAIN" or d >= 8
        }
        inapplicable = tuple(
            r
            for r in candidate.assessment.ratings
            if task.context.project.route != "EXPLAIN" and r.dimension <= 7
        )
        if any(r.rating is not None or r.status != "not_applicable" for r in inapplicable):
            raise ProviderFailure("INAPPLICABLE_RATING")
        if task.dimensions and inapplicable:
            raise ProviderFailure("TARGETED_SCOPE_MISMATCH")
        applicable = tuple(r for r in candidate.assessment.ratings if r not in inapplicable)
        if {r.dimension for r in applicable} != dimensions or len(applicable) != len(dimensions):
            raise ProviderFailure("ASSESSMENT_SCOPE_MISMATCH")
        if task.targeted_component:
            if {r.item for r in candidate.assessment.route_assessment} != set(
                task.route_items
            ) or len(candidate.assessment.route_assessment) != len(task.route_items):
                raise ProviderFailure("TARGETED_SCOPE_MISMATCH")
            if any(f.rule_id not in task.semantic_rule_ids for f in candidate.assessment.findings):
                raise ProviderFailure("TARGETED_SCOPE_MISMATCH")
        elif task.dimensions and (
            candidate.assessment.findings or candidate.assessment.route_assessment
        ):
            raise ProviderFailure("TARGETED_SCOPE_MISMATCH")
        if not any(
            s.statement_id == "principal-obstacle" and s.text == candidate.summary.obstacle
            for s in candidate.statements
        ):
            raise ProviderFailure("UNCHECKED_PRINCIPAL_OBSTACLE")
        allowed = {p.anchor.anchor_id for p in task.context.passages}
        for rating in candidate.assessment.ratings:
            if any(item not in allowed for item in rating.inspected_material):
                raise ProviderFailure("MISSING_SOURCE_SUPPORT")
        known = {
            r["id"]
            for r in json.loads(
                (
                    PROMPTS.parents[1] / f"policies/rubric-v{task.policy_version}.manifest.json"
                ).read_text(encoding="utf-8")
            )["rules"]
        }
        for finding in candidate.assessment.findings:
            if finding.rule_id not in known - DERIVED:
                raise ProviderFailure("UNKNOWN_OR_DERIVED_FINDING")
            self.references(task.context, finding.source_refs)
        self.promise_mapping(task, candidate)
        for rating in candidate.assessment.ratings:
            if rating.rating is not None and rating.rating >= 8:
                benchmark = rating.benchmark
                statement = next(
                    (
                        s
                        for s in candidate.statements
                        if s.statement_id == "benchmark:" + str(rating.dimension)
                        and s.kind == "source_backed"
                    ),
                    None,
                )
                if benchmark is None or statement is None or not statement.source_refs:
                    raise ProviderFailure("MISSING_PUBLISHED_BENCHMARK")
                referenced = {ref.anchor_id for ref in statement.source_refs}
                identities = {
                    label
                    for p in task.context.passages
                    if p.anchor.anchor_id in referenced and p.source.role == "literature"
                    for label in (p.source.title, p.source.attribution)
                    if label
                }
                if benchmark.published_reference not in identities:
                    raise ProviderFailure("BENCHMARK_ATTRIBUTION_MISMATCH")

    def review(self, task: AssessmentTask, candidate: CandidateReview) -> CheckedReview:
        self.validate_candidate(task, candidate)
        targets = {
            "rating:" + str(r.dimension)
            for r in candidate.assessment.ratings
            if r.rating is not None
        }
        targets |= {"finding:" + f.rule_id for f in candidate.assessment.findings}
        targets |= {"route:" + item.item for item in candidate.assessment.route_assessment}
        targets |= {"flag:account_articulated", "flag:study_assessable"}
        for item in candidate.assessment.route_assessment:
            self.references(task.context, item.source_refs)
        targets |= {"statement:" + s.statement_id for s in candidate.statements}
        checked = self.adapter.check(
            CheckingTask(assessment_task=task, candidate=candidate, targets=tuple(sorted(targets)))
        )
        if {d.target for d in checked.decisions} != targets or len(checked.decisions) != len(
            targets
        ):
            raise ProviderFailure("INCOMPLETE_CHECK")
        decisions = {d.target: d for d in checked.decisions}
        for check_decision in checked.decisions:
            self.references(task.context, check_decision.source_refs)
            if (
                check_decision.disposition == Verification.SUPPORTED
                and not check_decision.source_refs
            ):
                raise ProviderFailure("MISSING_SOURCE_SUPPORT")
        self.promise_mapping(
            task,
            candidate,
            {d.target for d in checked.decisions if d.disposition == Verification.SUPPORTED},
        )
        fields = candidate.assessment.model_dump()
        for rating in fields["ratings"]:
            decision = decisions.get("rating:" + str(rating["dimension"]))
            rating["verification"] = decision.disposition if decision else Verification.UNRESOLVED
            # Benchmark support must be separately attributed to supplied literature.
            if rating["benchmark"] is not None:
                statement = next(
                    (
                        s
                        for s in candidate.statements
                        if s.statement_id == "benchmark:" + str(rating["dimension"])
                        and s.kind == "source_backed"
                    ),
                    None,
                )
                disposition = (
                    decisions.get("statement:" + statement.statement_id) if statement else None
                )
                rating["benchmark"]["verification"] = (
                    disposition.disposition if disposition else Verification.UNRESOLVED
                )
            if decision and decision.disposition != Verification.SUPPORTED:
                # Preserve the original judgment; deterministic engine withholds unsupported inputs.
                rating["main_limitation"] += "; Focused check: " + decision.reason
        for finding in fields["findings"]:
            finding["verification"] = decisions["finding:" + finding["rule_id"]].disposition
        for item in fields["route_assessment"]:
            decision = decisions["route:" + item["item"]]
            item["verification"] = decision.disposition
            item["source_refs"] = tuple(decision.source_refs)
        for flag in ("account_articulated", "study_assessable"):
            fields[flag + "_verification"] = decisions["flag:" + flag].disposition
        limitations = list(
            dict.fromkeys(candidate.summary.limitations + checked.summary.limitations)
        )
        for field in (
            "contribution",
            "next_action",
            "deliverable",
            "outcome_branches",
            "diagnostic_action",
        ):
            original_value = getattr(candidate.summary, field)
            proposed_value = getattr(checked.summary, field)
            if proposed_value != original_value:
                limitations.append(
                    "Unresolved checker proposal for " + field + ": " + str(proposed_value)
                )
        limitations.append(
            "Focused model checking assesses support in supplied passages; it does not independently verify data or establish exhaustive literature coverage."
        )
        for decision in checked.decisions:
            if decision.disposition != Verification.SUPPORTED:
                limitations.append(
                    decision.target + ": " + decision.disposition.value + " — " + decision.reason
                )
        # Only an existing checked statement can drive the final principal obstacle.
        # Free-text checker rewrites/new allegations remain explicitly unresolved proposals.
        original = next(s for s in candidate.statements if s.statement_id == "principal-obstacle")
        principal = decisions["statement:principal-obstacle"]
        if checked.obstacle_action == "withdraw":
            if principal.disposition == Verification.SUPPORTED:
                raise ProviderFailure("OBSTACLE_DISPOSITION_MISMATCH")
            obstacle = "Original principal objection withdrawn after checking; no replacement blocking objection has been checked."
        elif principal.disposition != Verification.SUPPORTED:
            obstacle = "Unresolved principal objection (not a settled blocker): " + original.text
        elif checked.obstacle_action in ("qualify", "narrow"):
            obstacle = "Within the inspected source scope only: " + original.text
        else:
            obstacle = original.text
        if checked.summary.obstacle != original.text:
            limitations.append(
                "Unresolved checker proposal (not a settled blocker): " + checked.summary.obstacle
            )
        self.statements(task.context, candidate.statements + checked.proposed_objections)
        for objection in checked.proposed_objections:
            limitations.append(
                "Unresolved proposed objection (not a settled blocker): " + objection.text
            )
        limitations.append(
            "Principal-obstacle check: " + principal.disposition.value + " — " + principal.reason
        )
        summary = candidate.summary.model_copy(
            update={
                "obstacle": obstacle,
                "limitations": tuple(limitations),
                "disclaimer": "Structured review of supplied material only; generated suggestions are proposed, not verified evidence. Focused checking does not independently verify data or establish exhaustive literature coverage.",
            }
        )
        return CheckedReview(
            assessment=AssessmentFields.model_validate(fields),
            summary=summary,
            statements=candidate.statements + checked.proposed_objections,
            checks=checked.decisions,
            structural_checks=tuple(
                StructuralCheck(
                    target=decision.target,
                    status="SOURCE_REFS_RESOLVED",
                    source_refs=decision.source_refs,
                )
                for decision in checked.decisions
                if decision.source_refs
            ),
        )

    def workspace(self, task: WorkspaceTask, candidate: WorkspaceProposal) -> WorkspaceCheckResult:
        packet_check(task.context)
        for field in candidate.record.fields:
            self.references(task.context, field.source_refs)
            if field.key == "source_claim" and field.text:
                roles = {p.anchor.anchor_id: p.source.role for p in task.context.passages}
                if not field.source_refs or any(
                    roles[r.anchor_id] != "literature" for r in field.source_refs
                ):
                    raise ProviderFailure("MISSING_SOURCE_SUPPORT")
        targets = tuple(f.key for f in candidate.record.fields)
        checked = self.adapter.workspace_check(
            WorkspaceCheckingTask(context=task.context, candidate=candidate, targets=targets)
        )
        if len(checked.decisions) != len(targets) or {d.target for d in checked.decisions} != set(
            targets
        ):
            raise ProviderFailure("INCOMPLETE_CHECK")
        for decision in checked.decisions:
            self.references(task.context, decision.source_refs)
            if decision.disposition == Verification.SUPPORTED and not decision.source_refs:
                raise ProviderFailure("MISSING_SOURCE_SUPPORT")
        return checked
