"""Safe explicit local configuration; no credentials are serialized or logged."""

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from model_adapters.config import ProviderConfig
from persistence.database import Database

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class LocalConfiguration:
    runtime: Path
    database_mode: str
    provider: ProviderConfig

    @classmethod
    def environment(cls, probe_storage: bool = True) -> "LocalConfiguration":
        try:
            provider = ProviderConfig.environment()
        except (ValueError, TypeError):
            raise ValueError("INVALID_PROVIDER_CONFIGURATION") from None
        configured = os.getenv("RDW_RUNTIME_ROOT")
        if not configured:
            raise ValueError("MISSING_PRIVATE_RUNTIME_ROOT")
        runtime = Path(configured).resolve()
        if runtime == ROOT or ROOT in runtime.parents:
            raise ValueError("RUNTIME_MUST_BE_OUTSIDE_REPOSITORY")
        mode = os.getenv("RDW_DATABASE_MODE", "postgres")
        if mode not in ("postgres", "local-sqlite"):
            raise ValueError("UNSUPPORTED_DATABASE_MODE")
        if mode == "postgres" and not os.getenv("RDW_POSTGRES_DSN"):
            raise ValueError("MISSING_POSTGRES_CONFIGURATION")
        if provider.provider == "openai" and not os.getenv("OPENAI_API_KEY"):
            raise ValueError("BLOCKED_CREDENTIAL")
        if probe_storage:
            try:
                runtime.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryFile(dir=runtime) as file:
                    file.write(b"storage-probe")
                    file.flush()
            except OSError:
                raise ValueError("PRIVATE_STORAGE_UNAVAILABLE") from None
        return cls(runtime, mode, provider)

    def database(self) -> Database:
        try:
            return (
                Database.postgres(os.environ["RDW_POSTGRES_DSN"])
                if self.database_mode == "postgres"
                else Database.sqlite(self.runtime / "projects.sqlite")
            )
        except Exception:
            raise ValueError("DATABASE_CONNECTION_FAILED") from None

    def status(self) -> dict[str, object]:
        return {
            "database_mode": self.database_mode,
            "provider": self.provider.provider,
            "model": self.provider.model
            if self.provider.provider == "openai"
            else "deterministic-fake-v1",
            "credential_present": bool(os.getenv("OPENAI_API_KEY"))
            if self.provider.provider == "openai"
            else None,
            "max_calls": self.provider.max_calls,
            "max_run_tokens": self.provider.max_run_tokens,
        }
