import json
from pathlib import Path

from domain.sources import AccessScope, digest


class OriginalUnavailable(FileNotFoundError):
    pass


class OriginalFileStore:
    """Private filesystem adapter. Invoke only after repository authorization."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def key(self, scope: AccessScope, document_id: str, version: int, content_hash: str) -> str:
        identity = json.dumps(
            [scope.workspace_id, scope.project_id, document_id, version, content_hash],
            separators=(",", ":"),
        )
        return digest(identity.encode("utf-8"))

    def _path(self, key: str) -> Path:
        if len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
            raise ValueError("Invalid opaque original storage key")
        target = self.root / key
        if target.resolve().parent != self.root or target.is_symlink():
            raise ValueError("Original storage must remain within private root")
        return target

    def put(self, key: str, data: bytes) -> None:
        target = self._path(key)
        try:
            with target.open("xb") as stream:
                stream.write(data)
        except FileExistsError:
            if target.read_bytes() != data:
                raise ValueError("Cannot mutate original file")

    def read(self, key: str, expected_hash: str) -> bytes:
        target = self._path(key)
        if not target.is_file():
            raise OriginalUnavailable("Original file unavailable in this store")
        data = target.read_bytes()
        if digest(data) != expected_hash:
            raise ValueError("Original file hash mismatch")
        return data
