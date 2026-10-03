import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal

import psycopg

TABLES = (
    "CREATE TABLE IF NOT EXISTS workspaces (workspace_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS projects (workspace_id TEXT NOT NULL, project_id TEXT NOT NULL, revision INTEGER NOT NULL, PRIMARY KEY(workspace_id,project_id), FOREIGN KEY(workspace_id) REFERENCES workspaces(workspace_id))",
    "CREATE TABLE IF NOT EXISTS revisions (workspace_id TEXT NOT NULL, project_id TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(workspace_id,project_id,revision), FOREIGN KEY(workspace_id,project_id) REFERENCES projects(workspace_id,project_id))",
    "CREATE TABLE IF NOT EXISTS source_documents (workspace_id TEXT NOT NULL, project_id TEXT NOT NULL, document_id TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(workspace_id,project_id,document_id), FOREIGN KEY(workspace_id,project_id) REFERENCES projects(workspace_id,project_id))",
    "CREATE TABLE IF NOT EXISTS source_versions (workspace_id TEXT NOT NULL, project_id TEXT NOT NULL, document_id TEXT NOT NULL, version INTEGER NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(workspace_id,project_id,document_id,version), FOREIGN KEY(workspace_id,project_id,document_id) REFERENCES source_documents(workspace_id,project_id,document_id))",
    "CREATE TABLE IF NOT EXISTS source_anchors (workspace_id TEXT NOT NULL, project_id TEXT NOT NULL, document_id TEXT NOT NULL, version INTEGER NOT NULL, anchor_id TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(workspace_id,project_id,document_id,version,anchor_id), FOREIGN KEY(workspace_id,project_id,document_id,version) REFERENCES source_versions(workspace_id,project_id,document_id,version))",
    "CREATE TABLE IF NOT EXISTS admissions (workspace_id TEXT NOT NULL, project_id TEXT NOT NULL, document_id TEXT NOT NULL, version INTEGER NOT NULL, admitted INTEGER NOT NULL CHECK(admitted IN (0,1)), PRIMARY KEY(workspace_id,project_id,document_id,version), FOREIGN KEY(workspace_id,project_id,document_id,version) REFERENCES source_versions(workspace_id,project_id,document_id,version))",
    "CREATE TABLE IF NOT EXISTS snapshots (workspace_id TEXT NOT NULL, project_id TEXT NOT NULL, snapshot_id TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(workspace_id,project_id,snapshot_id), FOREIGN KEY(workspace_id,project_id,revision) REFERENCES revisions(workspace_id,project_id,revision))",
    "CREATE TABLE IF NOT EXISTS schema_versions (version INTEGER PRIMARY KEY)",
)
SCHEMA_VERSION = 2

IMMUTABLE = ("revisions", "source_documents", "source_versions", "source_anchors", "snapshots")


class Database:
    """One connection per service instance. No global connection or credentials."""

    def __init__(
        self,
        connection: sqlite3.Connection | psycopg.Connection[Any],
        dialect: Literal["sqlite", "postgres"],
    ):
        self.connection = connection
        self.dialect = dialect
        self._sequence = 0

    @classmethod
    def sqlite(cls, filename: str | Path = ":memory:") -> "Database":
        conn = sqlite3.connect(str(filename), isolation_level=None)
        conn.execute("PRAGMA foreign_keys=ON")
        return cls(conn, "sqlite")

    @classmethod
    def postgres(cls, dsn: str) -> "Database":
        return cls(psycopg.connect(dsn, autocommit=True), "postgres")

    def execute(self, sql: str, parameters: Sequence[object] = ()) -> Any:
        if self.dialect == "postgres":
            sql = sql.replace("?", "%s")
        return self.connection.execute(sql, parameters)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        if isinstance(self.connection, psycopg.Connection):
            with self.connection.transaction():
                yield
        else:
            self._sequence += 1
            name = f"rdw_savepoint_{self._sequence}"
            self.connection.execute(f"SAVEPOINT {name}")
            try:
                yield
            except BaseException:
                self.connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
                self.connection.execute(f"RELEASE SAVEPOINT {name}")
                raise
            else:
                self.connection.execute(f"RELEASE SAVEPOINT {name}")

    def schema_version(self) -> int:
        try:
            versions = tuple(
                row[0]
                for row in self.execute(
                    "SELECT version FROM schema_versions ORDER BY version"
                ).fetchall()
            )
        except (sqlite3.OperationalError, psycopg.errors.UndefinedTable):
            return 0
        if versions not in ((), (1,), (1, 2)):
            raise ValueError("INCOMPATIBLE_DATABASE_SCHEMA")
        return versions[-1] if versions else 0

    def validate_schema(self) -> None:
        try:
            with self.transaction():
                for statement in TABLES:
                    table = statement.split()[5]
                    # Only static identifiers from the versioned schema enter SQL.
                    columns = {
                        "workspaces": "workspace_id,owner_id,payload,digest",
                        "projects": "workspace_id,project_id,revision",
                        "revisions": "workspace_id,project_id,revision,payload,digest",
                        "source_documents": "workspace_id,project_id,document_id,payload,digest",
                        "source_versions": "workspace_id,project_id,document_id,version,payload,digest",
                        "source_anchors": "workspace_id,project_id,document_id,version,anchor_id,payload,digest",
                        "admissions": "workspace_id,project_id,document_id,version,admitted",
                        "snapshots": "workspace_id,project_id,snapshot_id,revision,payload,digest",
                        "schema_versions": "version",
                    }[table]
                    self.execute(f"SELECT {columns} FROM {table} LIMIT 0")
                if self.dialect == "sqlite":
                    names = {
                        r[0]
                        for r in self.execute(
                            "SELECT name FROM sqlite_master WHERE type='trigger'"
                        ).fetchall()
                    }
                    required = {
                        table + suffix
                        for table in IMMUTABLE
                        for suffix in ("_immutable", "_immutable_delete")
                    }
                else:
                    names = {
                        r[0]
                        for r in self.execute(
                            "SELECT tgname FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=current_schema()"
                        ).fetchall()
                    }
                    required = {table + "_immutable" for table in IMMUTABLE}
                if not required <= names:
                    raise ValueError("INCOMPATIBLE_DATABASE_SCHEMA")
        except (sqlite3.DatabaseError, psycopg.Error):
            raise ValueError("INCOMPATIBLE_DATABASE_SCHEMA") from None

    def initialize(self) -> None:
        # Version checks precede DDL; unsupported schemas are never silently adopted.
        current = self.schema_version()
        if current:
            self.validate_schema()
        if current == SCHEMA_VERSION:
            return
        if current == 0:
            if self.dialect == "sqlite":
                existing = {
                    row[0]
                    for row in self.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
            else:
                existing = {
                    row[0]
                    for row in self.execute(
                        "SELECT tablename FROM pg_tables WHERE schemaname=current_schema()"
                    ).fetchall()
                }
            if existing & {statement.split()[5] for statement in TABLES}:
                raise ValueError("UNVERSIONED_EXISTING_DATABASE_SCHEMA")
        with self.transaction():
            if self.dialect == "postgres":
                self.execute("SELECT pg_advisory_xact_lock(824008)")
            for statement in TABLES:
                self.execute(statement)
            if self.dialect == "postgres":
                self.execute(
                    "CREATE OR REPLACE FUNCTION rdw_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable history'; END $$"
                )
            for table in IMMUTABLE:
                if self.dialect == "sqlite":
                    self.execute(
                        f"CREATE TRIGGER IF NOT EXISTS {table}_immutable BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT,'immutable history'); END"
                    )
                else:
                    self.execute(f"DROP TRIGGER IF EXISTS {table}_immutable ON {table}")
                    self.execute(
                        f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION rdw_immutable()"
                    )
            if self.dialect == "sqlite":
                for table in IMMUTABLE:
                    self.execute(
                        f"CREATE TRIGGER IF NOT EXISTS {table}_immutable_delete BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT,'immutable history'); END"
                    )
            self.execute(
                "INSERT INTO schema_versions(version) VALUES(1) ON CONFLICT(version) DO NOTHING"
            )

            self.execute(
                "CREATE INDEX IF NOT EXISTS snapshots_revision ON snapshots(workspace_id,project_id,revision)"
            )
            self.execute(
                "INSERT INTO schema_versions(version) VALUES(2) ON CONFLICT(version) DO NOTHING"
            )

            self.validate_schema()

    def close(self) -> None:
        self.connection.close()
