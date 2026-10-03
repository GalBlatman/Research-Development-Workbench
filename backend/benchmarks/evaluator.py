"""Evaluator capability: one admitted packet and one private Workbench repository.
This module has no administrator store or variant/gold access interface.
"""

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from domain.application import AssessmentTask, CandidateReview
from domain.benchmark import BlindPacket, Judgment, Observation
from domain.models import Project, Scope
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
}


class BlindEvaluator:
    def __init__(
        self, packet: BlindPacket, adapter: ModelAdapter, manifest: Manifest, runtime: Path
    ):
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
                document_id=hashlib.sha256(
                    (packet.packet_id + ":" + str(index)).encode()
                ).hexdigest(),
                workspace_id=project.workspace_id,
                project_id=project.project_id,
                title=f"Supplied section {index + 1}",
                source_kind="pasted_original",
                role=block.role,
                media_type="text/plain",
                rights_declaration="Authorized synthetic benchmark packet",
            )
            self.workbench.sources.paste(scope, source, block.text)
            repository.set_admission(scope, source.document_id, 1, True)

    def task(self, component: str) -> AssessmentTask:
        m = self.workbench.manifest
        return AssessmentTask(
            context=self.workbench.context(self.project_id),
            dimensions=DIMENSIONS[component],
            scope=Scope.TARGETED_CHECK if component != "FULL" else Scope.FULL_EVALUATION,
            policy_version=m.version,
            policy_sha256=m.canonical_sha256,
            policy_manifest_sha256=m.sha256,
            policy_implementation_version=m.implementation_version,
        )

    def run(self, mode: str, component: str) -> tuple[dict[str, Any], tuple[str, ...]]:
        w = self.workbench
        if mode == "BASELINE":
            task = self.task(component)
            if isinstance(w.adapter, OpenAIAdapter):
                with provider_session(w.adapter):
                    payload = task.model_dump(mode="json")
                    payload["criteria"] = policy_contract(task)
                    output = w.adapter.call("baseline", payload, CandidateReview)
            else:
                output = CandidateReview.model_validate(w.adapter.assess(task))
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
        review_output = w.run(
            self.project_id,
            revision,
            dimensions=DIMENSIONS[component],
            target_workspace=None if component == "FULL" else component,
            evaluation_scope=Scope.FULL_EVALUATION,
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
            Judgment(key="route:" + r["item"], state=r["status"])
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
        judgments.extend(
            Judgment(
                key="statement:" + s["statement_id"],
                state="proposed",
                source_refs=tuple(r["anchor_id"] for r in s["source_refs"]),
            )
            for s in output.get("statements", output.get("checked_statements", []))
        )
        return Observation(
            judgments=tuple(judgments),
            authorized_anchors=tuple(p.anchor.anchor_id for p in context.passages),
            output_text=json.dumps(output, ensure_ascii=False),
        )

    def export(self) -> str:
        return self.workbench.repository.export(self.workbench.scope(self.project_id), True)

    def close(self) -> None:
        self.workbench.repository.db.close()
