"""Import own versioned portable exports without original-file authority."""

import json
from typing import Any

from domain.sources import ProjectBundle, StoredSnapshot, canonical
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
    return bundle


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
