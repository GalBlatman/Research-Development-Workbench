"""Import own versioned portable exports without original-file authority."""

import json
from typing import Any

from domain.models import EvidenceState, Origin
from domain.sources import ProjectBundle, StoredSnapshot, canonical
from policy_engine.manifest import Manifest
from services.configuration import ROOT
from services.workbench import Workbench


def _portable_bundle(serialized: str) -> ProjectBundle:
    data: dict[str, Any] = json.loads(serialized)
    if not isinstance(data, dict):
        raise ValueError("INVALID_PORTABLE_IMPORT")
    if data.get("schema_version") != "rdw-app-1":
        raise ValueError("INCOMPATIBLE_IMPORT_VERSION")
    if "import_bundle" in data:
        bundle = ProjectBundle.model_validate(data["import_bundle"])
    else:
        # Legacy view-only exports have source hashes but no original byte-length/storage.
        record = data["project_history"]
        for version in record["versions"]:
            version["document"]["original_storage_reference"] = None
            version["original"] = {
                "external": True,
                "storage_key": None,
                "sha256": version["document"]["content_sha256"],
                "byte_length": None,
            }
        snapshots = []
        for review in data["reviews"]:
            snapshot = review["snapshot"]
            for document in snapshot["documents"]:
                document["original_storage_reference"] = None
            assessment = {**review["assessment"], "snapshot": snapshot}
            snapshots.append(
                StoredSnapshot.model_validate(
                    {
                        "snapshot": snapshot,
                        "assessment": assessment,
                        "review": review["summary"],
                        "policy_result": review["policy"],
                        "coverage": review["coverage"],
                        "exclusions": review["exclusions"],
                        "provider_run": review.get("provider_run"),
                        "checked_statements": review.get("statements", []),
                        "checks": review.get("checks", []),
                        "structural_checks": review.get("structural_checks", []),
                    }
                ).model_dump(mode="json")
            )
        record["snapshots"] = snapshots
        bundle = ProjectBundle.model_validate(record)
    if any(
        v.original.storage_key is not None
        or v.document.original_storage_reference is not None
        or v.text is not None
        for v in bundle.versions
    ):
        raise ValueError(
            "Portable import cannot grant original-file access or admit embedded sources"
        )
    source_versions = {(v.document.document_id, v.document.version) for v in bundle.versions}
    anchor_refs = {(a.document_id, a.version, a.anchor_id) for a in bundle.anchors}
    for revision in bundle.revisions:
        for obj in revision.objects:
            fields = tuple(getattr(obj.payload, "fields", ()))
            generated = bool(obj.generated_by_run_id or obj.provider_run or obj.operation_id)
            entirely_generated = bool(fields) and all(
                field.origin in (Origin.INFERENCE, Origin.SUGGESTION) for field in fields
            )
            if (generated or entirely_generated) and obj.origin not in (
                Origin.INFERENCE,
                Origin.SUGGESTION,
            ):
                raise ValueError("Imported generated content cannot claim user/source origin")
            if obj.origin == Origin.EXTRACTION and (
                not obj.source_refs
                or any(
                    (ref.document_id, ref.version, ref.anchor_id) not in anchor_refs
                    for ref in obj.source_refs
                )
            ):
                raise ValueError("Imported extraction lacks bundled resolvable source refs")
            if obj.evidence_state == EvidenceState.DOCUMENTED:
                # Portable exports grant no original/artifact access. Flags alone cannot prove inspection.
                raise ValueError("Portable import cannot establish documented evidence authority")
    for stored in bundle.snapshots:
        snapshot = stored.snapshot
        if snapshot.policy_version not in ("4", "5"):
            raise ValueError("Unknown historical policy version")
        manifest = Manifest.model_validate_json(
            (ROOT / f"policies/rubric-v{snapshot.policy_version}.manifest.json").read_text(
                encoding="utf-8"
            )
        )
        if (
            snapshot.policy_sha256 != manifest.canonical_sha256
            or snapshot.policy_manifest_sha256 != manifest.sha256
            or snapshot.policy_implementation_version != manifest.implementation_version
        ):
            raise ValueError("Historical policy identity differs from preserved manifest")
        if stored.assessment is not None and stored.policy_result is not None:
            from dataclasses import asdict

            from domain.results import PolicyResult
            from policy_engine.engine import evaluate
            from services.workbench import policy_view

            evaluated = evaluate(stored.assessment, manifest)
            values = policy_view(asdict(evaluated))
            for name in (
                "idea_uncapped",
                "idea",
                "study",
                "project_uncapped",
                "project_before_caps",
                "project",
            ):
                values[name]["displayed"] = getattr(evaluated, name).displayed
            values.update(
                policy_version=manifest.version,
                policy_implementation_version=manifest.implementation_version,
            )
            if PolicyResult.model_validate(values) != stored.policy_result:
                raise ValueError(
                    "Imported historical policy result differs from preserved deterministic policy"
                )
        if any((d.document_id, d.version) not in source_versions for d in snapshot.documents):
            raise ValueError("Historical snapshot references unavailable source version")
    revisions = tuple(
        project.model_copy(
            update={
                "objects": tuple(
                    obj.model_copy(update={"imported": True}) for obj in project.objects
                )
            }
        )
        for project in bundle.revisions
    )
    annotated_snapshots: list[StoredSnapshot] = []
    for stored in bundle.snapshots:
        snapshot = stored.snapshot.model_copy(
            update={"project": revisions[stored.snapshot.project.revision - 1], "imported": True}
        )
        annotated_assessment = (
            stored.assessment.model_copy(update={"snapshot": snapshot})
            if stored.assessment
            else None
        )
        annotated_snapshots.append(
            stored.model_copy(update={"snapshot": snapshot, "assessment": annotated_assessment})
        )
    return bundle.model_copy(
        update={"revisions": revisions, "snapshots": tuple(annotated_snapshots)}
    )


def portable_bundle(serialized: str) -> ProjectBundle:
    try:
        return _portable_bundle(serialized)
    except (ValueError, KeyError, TypeError, AttributeError):
        raise ValueError("INVALID_OR_INCOMPATIBLE_PORTABLE_IMPORT") from None


def import_project(workbench: Workbench, serialized: str) -> str:
    bundle = portable_bundle(serialized)
    if bundle.workspace_id != workbench.workspace:
        raise ValueError("Import workspace differs; use supported owner backup restore")
    workbench.repository.import_bundle(workbench.scope(bundle.project_id), canonical(bundle))
    return bundle.project_id
