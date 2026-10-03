"""Stopped-app private backup and restore, preserving all scientific history.
Integrity hashes detect corruption; they are not authentication of third-party claims.
"""

import base64
import json
import os
import re
from pathlib import Path

from domain.application import RunHandle
from domain.benchmark import BenchmarkProject, BenchmarkRun, BenchmarkVariant, FrozenSplit
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
}


def admitted_path(relative: str) -> bool:
    return bool(
        re.fullmatch(
            r"originals/[a-f0-9]{64}|(?:runs|provider-receipts)/[a-f0-9]{32}\.json|benchmarks/(?:admin/)?(?:projects|variants|runs|splits|claims|batch_slots)/[a-f0-9]{64}\.json",
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
            relative = path.relative_to(runtime).as_posix()
            if (
                path.is_symlink()
                or runtime.resolve() not in path.resolve().parents
                or not admitted_path(relative)
            ):
                raise ValueError("PROHIBITED_BACKUP_FILE")
            data = path.read_bytes()
            file = BackupFile(
                path=relative, sha256=digest(data), content_base64=base64.b64encode(data).decode()
            )
            validate_file(file)
            files.append(file)
    backup = PrivateBackup(
        workspaces=tuple(workspaces), projects=tuple(projects), files=tuple(files)
    )
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
        raise ValueError("RESTORE_VALIDATION_FAILED_NO_MERGE") from None
