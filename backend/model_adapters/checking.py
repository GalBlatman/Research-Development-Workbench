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
from domain.models import SourceReference, StructuralCheck, Verification
from model_adapters.openai import DERIVED, PROMPTS, OpenAIAdapter, packet_check
from model_adapters.runtime import ProviderFailure


class AssessmentChecker:
    """Structural source resolution plus one explicitly limited semantic model check."""

    def __init__(self, adapter: OpenAIAdapter):
        self.adapter = adapter

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
        roles = {p.anchor.anchor_id: p.source.role for p in context.passages}
        for statement in items:
            self.references(context, statement.source_refs)
            if statement.kind in ("source_backed", "user_project"):
                if not statement.source_refs:
                    raise ProviderFailure("MISSING_SOURCE_SUPPORT")
                expected_role = (
                    "literature" if statement.kind == "source_backed" else "project_draft"
                )
                if any(roles[r.anchor_id] != expected_role for r in statement.source_refs):
                    raise ProviderFailure("ATTRIBUTION_ROLE_MISMATCH")

    def interpretation(self, task: InterpretationTask, candidate: Interpretation) -> None:
        packet_check(task.context)
        self.statements(task.context, candidate.statements)

    def verify(self, task: AssessmentTask, candidate: CandidateReview) -> AssessmentFields:
        return self.review(task, candidate).assessment

    def review(self, task: AssessmentTask, candidate: CandidateReview) -> CheckedReview:
        packet_check(task.context)
        self.statements(task.context, candidate.statements)
        dimensions = set(task.dimensions or range(1, 11))
        if {r.dimension for r in candidate.assessment.ratings} != dimensions or len(
            candidate.assessment.ratings
        ) != len(dimensions):
            raise ProviderFailure("ASSESSMENT_SCOPE_MISMATCH")
        if task.dimensions and (
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
                (PROMPTS.parents[1] / "policies/rubric-v4.manifest.json").read_text(
                    encoding="utf-8"
                )
            )["rules"]
        }
        for finding in candidate.assessment.findings:
            if finding.rule_id not in known - DERIVED:
                raise ProviderFailure("UNKNOWN_OR_DERIVED_FINDING")
            self.references(task.context, finding.source_refs)
        targets = {
            "rating:" + str(r.dimension)
            for r in candidate.assessment.ratings
            if r.rating is not None
        }
        targets |= {"finding:" + f.rule_id for f in candidate.assessment.findings}
        targets |= {"statement:" + s.statement_id for s in candidate.statements}
        checked = self.adapter.check(CheckingTask(assessment_task=task, candidate=candidate))
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
        limitations = list(checked.summary.limitations)
        limitations.append(
            "Focused model checking assesses support in supplied passages; it does not independently verify data or establish exhaustive literature coverage."
        )
        for decision in checked.decisions:
            if decision.disposition != Verification.SUPPORTED:
                limitations.append(
                    decision.target + ": " + decision.disposition.value + " — " + decision.reason
                )
        summary = checked.summary.model_copy(update={"limitations": tuple(limitations)})
        return CheckedReview(
            assessment=AssessmentFields.model_validate(fields),
            summary=summary,
            statements=candidate.statements,
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
