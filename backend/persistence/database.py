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

    def initialize(self) -> None:
        with self.transaction():
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

    def close(self) -> None:
        self.connection.close()
