"""Evaluator capability: one admitted packet and one private Workbench repository.
This module has no administrator store or variant/gold access interface.
"""

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Literal

from domain.application import AssessmentTask, CandidateReview, CheckDecision
from domain.benchmark import BlindPacket, Judgment, Observation, ScientificState
from domain.models import Adoption, AttributedStatement, EvidenceState, Project, Scope
from domain.research import DIMENSIONS as WORKSPACE_DIMENSIONS
from domain.sources import SourceRecord
from model_adapters.checking import AssessmentChecker
from model_adapters.contracts import ModelAdapter
from model_adapters.fake import FixtureVerifier
from model_adapters.openai import OpenAIAdapter, policy_contract
from model_adapters.runtime import provider_session
from persistence.database import Database
from persistence.originals import OriginalFileStore
from persistence.repository import Repository
from policy_engine.manifest import Manifest
from services.sources import SourceService
from services.workbench import Workbench

DIMENSIONS = {
    "Argument": (4, 5),
    "Study": (8, 9, 10),
    "Literature": (2, 3),
    "Alternatives": (6,),
    "FULL": (),
    "Brief": WORKSPACE_DIMENSIONS["Brief"],
    "Usefulness": WORKSPACE_DIMENSIONS["Usefulness"],
}

ROUTE_TARGETS = {
    "Brief": ("knowledge_need", "scope_precision"),
    "Literature": ("increment",),
    "Argument": ("capacity_to_learn",),
    "Alternatives": ("capacity_to_learn", "evidence_strategy"),
    "Study": ("evidence_strategy", "capacity_to_learn"),
    "Usefulness": ("knowledge_need", "next_use"),
}
RULE_TARGETS = {
    "Brief": (
        "AUDIENCE-QUESTION",
        "PREMISE-NO-BASIS",
        "PREMISE-CONDITIONAL",
        "PREMISE-CONTRADICTED",
    ),
    "Literature": ("NO-ADVANCE", "PROMISE-OVERREACH"),
    "Argument": ("PROMISE-OVERREACH",),
    "Alternatives": ("INFERENCE-UNSUPPORTED",),
    "Study": ("DESIGN-MISMATCH", "INFERENCE-UNSUPPORTED", "STAGE-MISMATCH"),
    "Usefulness": ("NO-CONSEQUENTIAL-STAKE",),
}


class BlindEvaluator:
    def __init__(
        self, packet: BlindPacket, adapter: ModelAdapter, manifest: Manifest, runtime: Path
    ):
        self.mode: Literal["WORKBENCH", "BASELINE"] = "WORKBENCH"
        runtime.mkdir(parents=True, exist_ok=False)
        db = Database(sqlite3.connect(runtime / "packet.sqlite", isolation_level=None), "sqlite")
        db.execute("PRAGMA foreign_keys=ON")
        db.initialize()
        repository = Repository(db)
        verifier = (
            AssessmentChecker(adapter) if isinstance(adapter, OpenAIAdapter) else FixtureVerifier()
        )
        self.workbench = Workbench(
            repository,
            SourceService(repository, OriginalFileStore(runtime / "originals")),
            manifest,
            adapter,
            verifier,
        )
        self.project_id = packet.packet_id
        scope = self.workbench.scope(self.project_id)
        project = Project(
            project_id=self.project_id,
            workspace_id=self.workbench.workspace,
            title="Neutral evaluation packet",
            revision=1,
            route=packet.route,
            stage=packet.stage,
        )
        repository.create_project(scope, project)
        for index, block in enumerate(packet.blocks):
            source = SourceRecord(
                presentation_order=index,
                document_id=hashlib.sha256(
                    (packet.packet_id + ":" + str(index)).encode()
                ).hexdigest(),
                workspace_id=project.workspace_id,
                project_id=project.project_id,
                title=f"Supplied section {index + 1}",
                source_kind="pasted_original",
                role=block.role,
                media_type="text/plain",
                rights_declaration="Authorized supplied material for this scoped evaluation",
            )
            self.workbench.sources.paste(scope, source, block.text)
            repository.set_admission(scope, source.document_id, 1, True)

    def task(self, component: str, extended: bool = False) -> AssessmentTask:
        m = self.workbench.manifest
        context = self.workbench.context(self.project_id)
        dimensions = tuple(
            d for d in DIMENSIONS[component] if context.project.route == "EXPLAIN" or d >= 8
        )
        if component != "FULL" and not dimensions and not extended:
            raise ValueError("NO_APPLICABLE_TARGETED_DIMENSIONS")
        return AssessmentTask.model_validate(
            dict(
                context=context,
                dimensions=dimensions,
                scope=Scope.TARGETED_CHECK if component != "FULL" else Scope.FULL_EVALUATION,
                policy_version=m.version,
                policy_sha256=m.canonical_sha256,
                policy_manifest_sha256=m.sha256,
                policy_implementation_version=m.implementation_version,
                targeted_component=component if extended and component != "FULL" else None,
                route_items=ROUTE_TARGETS[component]
                if extended
                and component != "FULL"
                and (
                    context.project.route != "EXPLAIN"
                    or context.project.stage in ("EARLY IDEA", "DISCOVERY PROPOSAL")
                )
                else (),
                semantic_rule_ids=tuple(
                    r
                    for r in RULE_TARGETS[component]
                    if r != "NO-ADVANCE" or context.project.route == "EXPLAIN"
                )
                if extended and component != "FULL"
                else (),
            )
        )

    def run(
        self, mode: str, component: str, extended: bool = False
    ) -> tuple[dict[str, Any], tuple[str, ...]]:
        if mode not in ("WORKBENCH", "BASELINE"):
            raise ValueError("Unknown evaluator mode")
        self.mode = "BASELINE" if mode == "BASELINE" else "WORKBENCH"
        w = self.workbench
        if mode == "BASELINE":
            task = self.task(component, extended)
            if isinstance(w.adapter, OpenAIAdapter):
                with provider_session(w.adapter):
                    payload = task.model_dump(mode="json")
                    payload["criteria"] = policy_contract(task)
                    output = w.adapter.call("baseline", payload, CandidateReview)
            else:
                output = CandidateReview.model_validate(w.adapter.assess(task))
            if isinstance(w.adapter, OpenAIAdapter):
                from model_adapters.checking import AssessmentChecker

                AssessmentChecker(w.adapter).validate_candidate(task, output)
            return output.model_dump(mode="json"), ("baseline",)
        components = []
        if component == "FULL":
            project = w.repository.project(w.scope(self.project_id))
            proposal = w._proposal(w.context(self.project_id), 2)
            updated = Project.model_validate(
                {**project.model_dump(), "revision": 2, "objects": (proposal,)}
            )
            w.repository.save_project(w.scope(self.project_id), updated, 1)
            components.append("interpretation")
        revision = w.repository.project(w.scope(self.project_id)).revision
        scoped_task = self.task(component, extended) if extended and component != "FULL" else None
        review_output = w.run(
            self.project_id,
            revision,
            dimensions=scoped_task.dimensions if scoped_task else DIMENSIONS[component],
            target_workspace=None if component == "FULL" else component,
            evaluation_scope=Scope.FULL_EVALUATION,
            targeted_task=scoped_task,
        )
        components.extend(
            (
                "evaluation:" + component,
                "checking" if isinstance(w.adapter, OpenAIAdapter) else "fixture-verification",
            )
        )
        return review_output, tuple(components)

    def observe(self, output: dict[str, Any]) -> Observation:
        fields = output["assessment"]
        context = self.workbench.context(self.project_id)
        checks = tuple(CheckDecision.model_validate(c) for c in output.get("checks", []))
        if len({c.target for c in checks}) != len(checks):
            raise ValueError("Duplicate statement checking target")
        if self.mode == "BASELINE" and checks:
            raise ValueError("Baseline cannot contain Workbench checking records")
        by_target = {c.target: c for c in checks}
        judgments = [
            Judgment(
                key="rating:" + str(r["dimension"]),
                state=r["status"],
                value=r["rating"],
                verification=r["verification"],
                source_refs=tuple(r["inspected_material"]),
            )
            for r in fields["ratings"]
        ]
        judgments.extend(
            Judgment(key="route:" + r["item"], state=r["status"], verification=r["verification"])
            for r in fields.get("route_assessment", [])
        )
        judgments.extend(
            Judgment(
                key="finding:" + f["rule_id"],
                state=f["value"],
                verification=f["verification"],
                source_refs=tuple(r["anchor_id"] for r in f["source_refs"]),
            )
            for f in fields.get("findings", [])
        )
        for raw in output.get("statements", output.get("checked_statements", [])):
            statement = AttributedStatement.model_validate(raw)
            decision = by_target.get("statement:" + statement.statement_id)
            if self.mode == "BASELINE" and decision is not None:
                raise ValueError("Baseline cannot acquire Workbench checker dispositions")
            refs = statement.source_refs + (decision.source_refs if decision else ())
            scientific_state: ScientificState = (
                "unresolved" if statement.kind == "unresolved" else "assessed"
            )
            judgments.append(
                Judgment(
                    key="statement:" + statement.statement_id,
                    state=scientific_state,
                    scientific_state=scientific_state,
                    checking_performed=decision is not None,
                    content=statement.text,
                    adoption=Adoption.PROPOSED,
                    evidence_state=EvidenceState.UNINSPECTED,
                    statement_kind=statement.kind,
                    verification=decision.disposition if decision else None,
                    source_refs=tuple(dict.fromkeys(r.anchor_id for r in refs)),
                )
            )
        judgments = [
            j.model_copy(
                update={
                    "scientific_state": j.scientific_state or j.state,
                    "evaluator_mode": self.mode,
                    "checking_performed": self.mode == "WORKBENCH" and j.key in by_target,
                    "verification": (
                        by_target[j.key].disposition
                        if self.mode == "WORKBENCH" and j.key in by_target
                        else None
                    ),
                }
            )
            for j in judgments
        ]
        return Observation(
            evaluator_mode=self.mode,
            judgments=tuple(judgments),
            authorized_anchors=tuple(p.anchor.anchor_id for p in context.passages),
            output_text=json.dumps(output, ensure_ascii=False),
        )

    def export(self) -> str:
        return self.workbench.repository.export(self.workbench.scope(self.project_id), True)

    def close(self) -> None:
        self.workbench.repository.db.close()
