"""Stopped-app private backup and restore, preserving all scientific history.
Integrity hashes detect corruption; they are not authentication of third-party claims.
"""

import base64
import json
import os
import re
from pathlib import Path

from domain.application import RunHandle
from domain.benchmark import (
    BenchmarkProject,
    BenchmarkRun,
    BenchmarkVariant,
    FrozenExpectations,
    FrozenSplit,
    InvalidCaseReport,
    ReservationReport,
)
from domain.models import Frozen, ProviderRun, Workspace
from domain.operations import BackupFile, PrivateBackup
from domain.sources import AccessScope, ProjectBundle, SourceVersion, canonical, digest
from persistence.database import SCHEMA_VERSION, Database
from persistence.originals import OriginalFileStore
from persistence.repository import Repository
from services.configuration import ROOT

BENCHMARK_TYPES: dict[str, type[Frozen]] = {
    "projects": BenchmarkProject,
    "variants": BenchmarkVariant,
    "runs": BenchmarkRun,
    "splits": FrozenSplit,
    "expectations": FrozenExpectations,
}


def admitted_path(relative: str) -> bool:
    return bool(
        re.fullmatch(
            r"originals/[a-f0-9]{64}|(?:runs|provider-receipts)/[a-f0-9]{32}(?:\.call-[0-9]+)?\.json|benchmarks/(?:admin/)?(?:projects|variants|runs|splits|expectations|claims|batch_slots|annotations)/[a-f0-9]{64}\.json",
            relative,
        )
    )


def validate_file(file: BackupFile) -> None:
    if not admitted_path(file.path):
        raise ValueError("PROHIBITED_BACKUP_PATH")
    data = base64.b64decode(file.content_base64, validate=True)
    if file.path.startswith("runs/"):
        RunHandle.model_validate_json(data)
    elif file.path.startswith("provider-receipts/"):
        ProviderRun.model_validate_json(data)
    elif file.path.startswith("benchmarks/"):
        category = file.path.split("/")[-2]
        contract = BENCHMARK_TYPES.get(category)
        if contract:
            contract.model_validate_json(data)
        elif category == "annotations":
            record = json.loads(data)
            (
                ReservationReport if "reservation_key" in record else InvalidCaseReport
            ).model_validate(record)
        else:
            record = json.loads(data)
            fields = {"run_id", "state"} if category == "claims" else {"batch_key", "slot"}
            if set(record) != fields:
                raise ValueError("INCOMPATIBLE_BENCHMARK_RESERVATION")


def private_path(path: Path) -> Path:
    path = path.resolve()
    if path == ROOT or ROOT in path.parents:
        raise ValueError("PRIVATE_ARTIFACT_MUST_BE_OUTSIDE_REPOSITORY")
    return path


def create_backup(database: Database, runtime: Path, destination: Path) -> None:
    destination = private_path(destination)
    if database.schema_version() != SCHEMA_VERSION:
        raise ValueError("INCOMPATIBLE_DATABASE_SCHEMA")
    inspect_state(database, runtime)
    repo = Repository(database)
    workspaces = []
    projects = []
    with database.transaction():
        for row in database.execute(
            "SELECT payload,digest FROM workspaces ORDER BY workspace_id"
        ).fetchall():
            workspace = repo._decode(row, Workspace)
            workspaces.append(workspace)
            for (pid,) in database.execute(
                "SELECT project_id FROM projects WHERE workspace_id=? ORDER BY project_id",
                (workspace.workspace_id,),
            ).fetchall():
                scope = AccessScope(
                    actor_id=workspace.owner_id, workspace_id=workspace.workspace_id, project_id=pid
                )
                bundle = ProjectBundle.model_validate_json(repo.export(scope, True))
                # A private backup includes unadmitted originals too; ordinary exports still exclude them.
                versions = repo._all(scope, "source_versions", "document_id,version", SourceVersion)
                projects.append(bundle.model_copy(update={"versions": versions}))
    files = []
    for folder in ("originals", "runs", "provider-receipts", "benchmarks"):
        for path in sorted((runtime / folder).rglob("*")) if (runtime / folder).exists() else []:
            if not path.is_file():
                continue
            if path.suffix == ".tmp" or (
                folder == "benchmarks" and any(part == "evaluator" for part in path.parts)
            ):
                continue
            relative = path.relative_to(runtime).as_posix()
            if (
                path.is_symlink()
                or runtime.resolve() not in path.resolve().parents
                or not admitted_path(relative)
            ):
                raise ValueError("PROHIBITED_BACKUP_FILE")
            data = path.read_bytes()
            artifact = BackupFile(
                path=relative, sha256=digest(data), content_base64=base64.b64encode(data).decode()
            )
            validate_file(artifact)
            files.append(artifact)
    backup = PrivateBackup(
        workspaces=tuple(workspaces), projects=tuple(projects), files=tuple(files)
    )
    validate_backup_references(backup)
    serialized = canonical(backup)
    key = os.getenv("OPENAI_API_KEY")
    if key and (
        key in serialized or any(key.encode() in base64.b64decode(f.content_base64) for f in files)
    ):
        raise ValueError("BACKUP_CONTAINS_CONFIGURED_CREDENTIAL")
    envelope = (
        json.dumps(
            {"sha256": digest(serialized.encode()), "backup": json.loads(serialized)},
            sort_keys=True,
        )
        + "\n"
    )
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(envelope)
        stream.flush()
        os.fsync(stream.fileno())


def restore_backup(database: Database, runtime: Path, source: Path) -> None:
    private_path(runtime)
    try:
        envelope = json.loads(source.read_text(encoding="utf-8"))
        if set(envelope) != {"sha256", "backup"}:
            raise ValueError("INCOMPATIBLE_BACKUP")
        backup = PrivateBackup.model_validate(envelope["backup"])
        if digest(canonical(backup).encode()) != envelope["sha256"]:
            raise ValueError("CORRUPT_BACKUP")
        for file in backup.files:
            validate_file(file)
        validate_backup_references(backup)
    except (ValueError, KeyError, TypeError):
        raise ValueError("CORRUPT_OR_INCOMPATIBLE_BACKUP") from None
    if database.schema_version() != SCHEMA_VERSION:
        raise ValueError("INCOMPATIBLE_DATABASE_SCHEMA")
    if database.execute("SELECT 1 FROM workspaces LIMIT 1").fetchone() or any(
        (runtime / folder).exists() and any((runtime / folder).rglob("*"))
        for folder in ("originals", "runs", "provider-receipts", "benchmarks")
    ):
        raise ValueError("RESTORE_REQUIRES_EMPTY_TARGET")
    repo = Repository(database)
    created: list[Path] = []
    created_folders: set[Path] = set()
    try:
        with database.transaction():
            for workspace in backup.workspaces:
                repo.register_workspace(workspace.owner_id, workspace)
            for project in backup.projects:
                owner = next(
                    w.owner_id for w in backup.workspaces if w.workspace_id == project.workspace_id
                )
                repo.import_bundle(
                    AccessScope(
                        actor_id=owner,
                        workspace_id=project.workspace_id,
                        project_id=project.project_id,
                    ),
                    canonical(project),
                )
            for file in backup.files:
                target = runtime / file.path
                parent = target.parent
                while parent != runtime and not parent.exists():
                    created_folders.add(parent)
                    parent = parent.parent
                target.parent.mkdir(parents=True, exist_ok=True)
                if runtime.resolve() not in target.resolve().parents or target.is_symlink():
                    raise ValueError("PROHIBITED_RESTORE_PATH")
                with target.open("xb") as stream:
                    created.append(target)
                    stream.write(base64.b64decode(file.content_base64, validate=True))
            originals = OriginalFileStore(runtime / "originals")
            for project in backup.projects:
                for version in project.versions:
                    if version.original.storage_key and version.original.sha256:
                        originals.read(version.original.storage_key, version.original.sha256)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        for folder in sorted(created_folders, key=lambda p: len(p.parts), reverse=True):
            if folder.exists() and not any(folder.iterdir()):
                folder.rmdir()
        raise ValueError("RESTORE_VALIDATION_FAILED_NO_MERGE") from None


def inspect_state(database: Database, runtime: Path) -> None:
    """Read-only integrity scan of persisted user state, not a synthetic self-test."""
    from domain.locations import validate_anchor
    from domain.sources import SourceAnchor

    repo = Repository(database)
    owners = {}
    for row in database.execute("SELECT payload,digest FROM workspaces").fetchall():
        workspace = repo._decode(row, Workspace)
        owners[workspace.workspace_id] = workspace.owner_id
    originals = runtime / "originals"
    for wid, pid, head in database.execute(
        "SELECT workspace_id,project_id,revision FROM projects"
    ).fetchall():
        scope = AccessScope(actor_id=owners[wid], workspace_id=wid, project_id=pid)
        bundle = ProjectBundle.model_validate_json(repo.export(scope, True))
        if bundle.revisions[-1].revision != head:
            raise ValueError("PROJECT_HEAD_INTEGRITY_FAILED")
        versions = repo._all(scope, "source_versions", "document_id,version", SourceVersion)
        by_version = {(v.document.document_id, v.document.version): v for v in versions}
        for version in versions:
            original = version.original
            if original.storage_key:
                file = originals / original.storage_key
                if (
                    file.is_symlink()
                    or not file.is_file()
                    or file.parent.resolve() != originals.resolve()
                ):
                    raise ValueError("ORIGINAL_STORAGE_INTEGRITY_FAILED")
                raw = file.read_bytes()
                if digest(raw) != original.sha256 or len(raw) != original.byte_length:
                    raise ValueError("ORIGINAL_CONTENT_INTEGRITY_FAILED")
        anchors = repo._all(scope, "source_anchors", "document_id,version,anchor_id", SourceAnchor)
        for anchor in anchors:
            validate_anchor(anchor, by_version[(anchor.document_id, anchor.version)])
        anchor_ids = {(a.document_id, a.version, a.anchor_id) for a in anchors}
        for project in bundle.revisions:
            for obj in project.objects:
                references = obj.source_refs + tuple(
                    r for f in getattr(obj.payload, "fields", ()) for r in f.source_refs
                )
                if any(
                    (r.document_id, r.version, r.anchor_id) not in anchor_ids for r in references
                ):
                    raise ValueError("PROJECT_SOURCE_REFERENCE_INTEGRITY_FAILED")
        for snapshot in bundle.snapshots:
            frozen = snapshot.snapshot
            if frozen.project != bundle.revisions[frozen.project.revision - 1]:
                raise ValueError("SNAPSHOT_REVISION_INTEGRITY_FAILED")
            if any(by_version[(d.document_id, d.version)].document != d for d in frozen.documents):
                raise ValueError("SNAPSHOT_SOURCE_INTEGRITY_FAILED")
    for administrator in (runtime / "benchmarks", runtime / "benchmarks" / "admin"):
        if administrator.exists():
            inspect_admin_state(administrator)
    for folder in (runtime / "benchmarks", runtime / "provider-receipts", runtime / "runs"):
        if not folder.exists():
            continue
        for path in folder.rglob("*.json"):
            relative = path.relative_to(runtime).as_posix()
            if "evaluator" in path.parts:
                continue
            artifact = BackupFile(
                path=relative,
                sha256=digest(path.read_bytes()),
                content_base64=base64.b64encode(path.read_bytes()).decode(),
            )
            validate_file(artifact)


def validate_backup_references(backup: PrivateBackup) -> None:
    files = {f.path: f for f in backup.files}
    for project in backup.projects:
        for version in project.versions:
            original = version.original
            if original.storage_key:
                artifact = files.get("originals/" + original.storage_key)
                if artifact is None:
                    raise ValueError("BACKUP_REFERENCED_ORIGINAL_MISSING")
                raw = base64.b64decode(artifact.content_base64, validate=True)
                if digest(raw) != original.sha256 or len(raw) != original.byte_length:
                    raise ValueError("BACKUP_REFERENCED_ORIGINAL_CORRUPT")


def inspect_admin_state(root: Path) -> None:
    from benchmarks.variants import construct, content_hash

    projects = {}
    splits = {}
    variants = {}
    expectations = {}
    for category, contract in BENCHMARK_TYPES.items():
        if category == "runs":
            continue
        for path in (root / category).glob("*.json"):
            artifact = contract.model_validate_json(path.read_text(encoding="utf-8"))
            if isinstance(artifact, BenchmarkProject):
                projects[content_hash(artifact)] = artifact
                identity = artifact.benchmark_id + ":" + artifact.version
            elif isinstance(artifact, FrozenSplit):
                splits[content_hash(artifact)] = artifact
                identity = artifact.version
            elif isinstance(artifact, BenchmarkVariant):
                variants[artifact.variant_id] = artifact
                identity = artifact.variant_id
            elif isinstance(artifact, FrozenExpectations):
                expectations[artifact.variant_id] = artifact
                identity = artifact.variant_id
            else:
                raise ValueError("INCOMPATIBLE_ADMIN_ARTIFACT")
            if path.stem != content_hash(identity):
                raise ValueError("ADMIN_ARTIFACT_IDENTITY_INTEGRITY_FAILED")
    for variant in variants.values():
        project, split = projects.get(variant.package_hash), splits.get(variant.split_hash)
        if project is None or split is None:
            raise ValueError("ADMIN_VARIANT_REFERENCE_INTEGRITY_FAILED")
        parent = variants.get(variant.mutation.parent_variant or "")
        if construct(project, variant.mutation, variant.variant_id, split, parent) != variant:
            raise ValueError("ADMIN_VARIANT_CONTENT_INTEGRITY_FAILED")
    for artifact in expectations.values():
        expectation_variant = variants.get(artifact.variant_id)
        if (
            expectation_variant is None
            or content_hash(expectation_variant) != artifact.variant_hash
        ):
            raise ValueError("ADMIN_EXPECTATION_REFERENCE_INTEGRITY_FAILED")
    for path in (root / "runs").glob("*.json"):
        run = BenchmarkRun.model_validate_json(path.read_text(encoding="utf-8"))
        run_variant = variants.get(run.variant_id)
        run_expectations = expectations.get(run.variant_id)
        if (
            run_variant is None
            or run_expectations is None
            or run.package_hash not in projects
            or run.split_hash not in splits
            or content_hash(run_variant) != run.variant_hash
            or run.expectations_hash
            != content_hash([e.model_dump(mode="json") for e in run_expectations.expectations])
        ):
            raise ValueError("ADMIN_RUN_REFERENCE_INTEGRITY_FAILED")
