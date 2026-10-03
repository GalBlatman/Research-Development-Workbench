"""Private local backup contracts, distinct from ordinary publication exports."""

import base64
from typing import Literal, Self

from pydantic import model_validator

from domain.models import Frozen, Hash, Workspace
from domain.sources import ProjectBundle, digest


class BackupFile(Frozen):
    path: str
    sha256: Hash
    content_base64: str

    @model_validator(mode="after")
    def checked_content(self) -> Self:
        try:
            data = base64.b64decode(self.content_base64, validate=True)
        except ValueError:
            raise ValueError("CORRUPT_BACKUP_FILE") from None
        if digest(data) != self.sha256:
            raise ValueError("CORRUPT_BACKUP_FILE")
        return self


class PrivateBackup(Frozen):
    format_version: Literal[1] = 1
    schema_version: Literal[2] = 2
    workspaces: tuple[Workspace, ...]
    projects: tuple[ProjectBundle, ...]
    files: tuple[BackupFile, ...]

    @model_validator(mode="after")
    def unique_scopes(self) -> Self:
        if (
            len({w.workspace_id for w in self.workspaces}) != len(self.workspaces)
            or len({(p.workspace_id, p.project_id) for p in self.projects}) != len(self.projects)
            or len({f.path for f in self.files}) != len(self.files)
        ):
            raise ValueError("DUPLICATE_BACKUP_RECORD")
        if any(
            p.workspace_id not in {w.workspace_id for w in self.workspaces} for p in self.projects
        ):
            raise ValueError("BACKUP_WORKSPACE_MISMATCH")
        return self
