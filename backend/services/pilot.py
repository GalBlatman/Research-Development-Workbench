"""Local operator CLI; self-check performs no live provider calls or scientific edits."""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import psycopg

from domain.application import AddSource, CreateProject, EditProject
from domain.models import Route, Stage
from model_adapters.fake import FakeModel
from persistence.database import SCHEMA_VERSION
from persistence.originals import OriginalFileStore
from persistence.repository import Repository
from policy_engine.manifest import Manifest
from services.backup import create_backup, inspect_state, restore_backup
from services.configuration import ROOT, LocalConfiguration
from services.portability import import_project
from services.sources import SourceService
from services.workbench import Workbench

SCENARIOS = (
    (
        "A - EXPLAIN early idea",
        Route.EXPLAIN,
        Stage.EARLY_IDEA,
        "Synthetic early question about handoffs.",
        "A synthetic predecessor does not resolve the question.",
    ),
    (
        "B - EXPLAIN specified proposal",
        Route.EXPLAIN,
        Stage.PROPOSAL,
        "Synthetic proposed account: explicit requests may change shared understanding.",
        "Proposed direct handoff measures with a temporal plan, not completed evidence.",
    ),
    (
        "C - EXPLAIN completed study",
        Route.EXPLAIN,
        Stage.COMPLETED,
        "Synthetic fictional completed study reports a bounded pattern; causal explanation remains to be checked.",
        "Fictional findings only, not empirical or calibration data.",
    ),
    (
        "D - ESTABLISH",
        Route.ESTABLISH,
        Stage.PROPOSAL,
        "Synthetic plan to document whether irregular handoffs exist.",
        "A fictional prior account leaves frequency unknown.",
    ),
    (
        "E - TEST",
        Route.TEST,
        Stage.PROPOSAL,
        "Synthetic replication plan to test a fictional handoff claim.",
        "A fictional original claim has uncertain support.",
    ),
    (
        "F - source disagreement",
        Route.ESTABLISH,
        Stage.EARLY_IDEA,
        "Synthetic sources disagree; do not settle the factual premise.",
        "Source one proposes frequent interruptions; source two reports no such pattern. Both are fictional.",
    ),
    (
        "G - serious rival",
        Route.EXPLAIN,
        Stage.PROPOSAL,
        "Synthetic request-driven account competes with a shared-incentive account.",
        "The rival predicts handoffs change when incentives change even without requests.",
    ),
    (
        "H - stale dependency",
        Route.EXPLAIN,
        Stage.PROPOSAL,
        "Synthetic initial claim before a consequential revision.",
        "A fictional source bounds the original premise.",
    ),
    (
        "I - incomplete result",
        Route.TEST,
        Stage.EARLY_IDEA,
        "Synthetic incomplete-provider recovery scenario; fixed fake output remains pending.",
        "No supplied evidence resolves the claim. Failure is tested by MockTransport, not by a live call.",
    ),
)


def workbench(config: LocalConfiguration) -> Workbench:
    if config.provider.provider != "fake":
        raise ValueError("OPERATOR_STATE_COMMAND_REQUIRES_FAKE_MODE_NO_LIVE_CALLS")
    database = config.database()
    if database.schema_version() != SCHEMA_VERSION:
        database.close()
        raise ValueError("RUN_MIGRATE_BEFORE_OPERATOR_COMMAND")
    manifest = Manifest.model_validate_json(
        (ROOT / "policies/rubric-v5.manifest.json").read_text(encoding="utf-8")
    )
    repo = Repository(database)
    return Workbench(
        repo,
        SourceService(repo, OriginalFileStore(config.runtime / "originals")),
        manifest,
        FakeModel(),
    )


def seed(service: Workbench) -> tuple[str, ...]:
    if service.repository.db.execute("SELECT 1 FROM projects LIMIT 1").fetchone():
        raise ValueError("SCENARIO_SEED_REQUIRES_EMPTY_PROJECT_STORE")
    identifiers = []
    for title, route, stage, idea, source in SCENARIOS:
        view = service.create(
            CreateProject(title=title, route=route, stage=stage, idea=idea, authorized=True)
        )
        identifier = view["project"]["project_id"]
        view = service.add_source(
            identifier,
            AddSource(
                expected_revision=view["project"]["revision"],
                title="Synthetic source",
                attribution="Original fictional pilot scenario",
                text=source,
                authorized=True,
                admitted=True,
            ),
        )
        service.run(identifier, view["project"]["revision"])
        if title.startswith("H"):
            service.edit(
                identifier,
                EditProject(
                    expected_revision=view["project"]["revision"],
                    idea="Synthetic revised claim changes the interpretation dependency.",
                ),
            )
        identifiers.append(identifier)
    # J is the harness's hidden-feature cannot-know fixture; preserve administrator separation.
    from benchmarks.fixtures import synthetic
    from benchmarks.store import AdminStore
    from benchmarks.variants import freeze

    projects, cases = synthetic()
    store = AdminStore(service.sources.originals.root.parent / "benchmarks")
    frozen = freeze(projects, "synthetic-splits-v1")
    store.freeze(frozen)
    for project in projects:
        store.import_project(project, frozen)
    for case in cases:
        store.save_variant(case.variant, case.project, frozen)
        store.freeze_expectations(case.variant, case.expectations)
    return tuple(identifiers)


def health(config: LocalConfiguration) -> dict[str, str]:
    report = {"configuration": "PASS"}
    if (
        config.database_mode == "local-sqlite"
        and not (config.runtime / "projects.sqlite").is_file()
    ):
        return {
            "configuration": "PASS",
            "database_connectivity": "FAIL",
            "error_code": "DATABASE_FILE_MISSING",
        }
    try:
        database = config.database()
    except (ValueError, OSError, sqlite3.DatabaseError, psycopg.Error):
        return {
            **report,
            "database_connectivity": "FAIL",
            "error_code": "DATABASE_CONNECTION_FAILED",
        }
    try:
        database.execute("SELECT 1")
        report["database_connectivity"] = "PASS"
        try:
            database.validate_schema()
            report["schema_version"] = (
                "PASS" if database.schema_version() == SCHEMA_VERSION else "FAIL"
            )
        except (ValueError, OSError, sqlite3.DatabaseError, psycopg.Error):
            report["schema_version"] = "FAIL"
        if report["schema_version"] != "PASS":
            return {
                **report,
                "persisted_state_integrity": "NOT_RUN",
                "error_code": "INCOMPATIBLE_DATABASE_SCHEMA",
            }
        try:
            inspect_state(database, config.runtime)
            report["persisted_state_integrity"] = "PASS"
        except (ValueError, KeyError, OSError, sqlite3.DatabaseError, psycopg.Error):
            report["persisted_state_integrity"] = "FAIL"
            report["error_code"] = "PERSISTED_STATE_INTEGRITY_FAILED"
    except (OSError, sqlite3.DatabaseError, psycopg.Error):
        return {
            **report,
            "database_connectivity": "FAIL",
            "error_code": "DATABASE_CONNECTION_FAILED",
        }
    finally:
        database.close()
    # Isolated tests use synthetic temporary data only; do not write to the pilot projects.
    suites = {
        "fake_source_persistence": ("tests/test_application.py", "tests/test_persistence.py"),
        "policy_golden": ("tests/test_golden.py",),
        "benchmark_blindness": ("tests/test_benchmarks.py",),
    }
    for name, paths in suites.items():
        env = {**os.environ, "RDW_PROVIDER": "fake"}
        env.pop("OPENAI_API_KEY", None)
        env.pop("RDW_TEST_POSTGRES_DSN", None)
        env.pop("RDW_REQUIRE_POSTGRES", None)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", *paths],
            cwd=ROOT / "backend",
            env=env,
            capture_output=True,
        )
        report[name] = "PASS" if result.returncode == 0 else "FAIL"
    for name, command, cwd in (
        ("contracts", [sys.executable, "-m", "api.contracts", "--check"], ROOT / "backend"),
        ("publication", ["node", "scripts/check.mjs"], ROOT),
    ):
        try:
            result = subprocess.run(command, cwd=cwd, capture_output=True)
        except FileNotFoundError:
            report[name] = "FAIL"
            report["missing_operator_tool"] = (
                "NODE_MISSING" if command[0] == "node" else "PYTHON_MISSING"
            )
            continue
        report[name] = "PASS" if result.returncode == 0 else "FAIL"
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Private Workbench local operations; no live provider calls"
    )
    parser.add_argument(
        "command", choices=("status", "migrate", "health", "seed", "backup", "restore", "import")
    )
    parser.add_argument("--file", type=Path)
    args = parser.parse_args()
    try:
        config = LocalConfiguration.environment(probe_storage=args.command != "health")
        if args.command == "status":
            print(json.dumps(config.status(), sort_keys=True))
        elif args.command == "health":
            report = health(config)
            print(json.dumps(report, sort_keys=True))
            if "FAIL" in report.values():
                raise SystemExit(1)
        elif args.command in ("migrate", "backup", "restore"):
            database = config.database()
            try:
                if args.command == "migrate":
                    database.initialize()
                elif args.file is None:
                    raise ValueError("FILE_ARGUMENT_REQUIRED")
                elif args.command == "backup":
                    create_backup(database, config.runtime, args.file)
                else:
                    restore_backup(database, config.runtime, args.file)
            finally:
                database.close()
            print("PASS " + args.command)
        else:
            service = workbench(config)
            try:
                if args.command == "seed":
                    identifiers = seed(service)
                    print(
                        json.dumps(
                            {
                                "scenario_projects": len(identifiers),
                                "hidden_feature_scenario": "benchmarks administrator store",
                            }
                        )
                    )
                elif args.file:
                    import_project(service, args.file.read_text(encoding="utf-8"))
                    print("PASS import")
                else:
                    raise ValueError("FILE_ARGUMENT_REQUIRED")
            finally:
                service.repository.db.close()
    except (ValueError, OSError, sqlite3.DatabaseError, psycopg.Error, KeyError) as exc:
        # Never echo exception messages that might contain manuscript input or a DSN.
        code = (
            str(exc)
            if str(exc)
            in {
                "MISSING_PRIVATE_RUNTIME_ROOT",
                "RUNTIME_MUST_BE_OUTSIDE_REPOSITORY",
                "UNSUPPORTED_DATABASE_MODE",
                "OPERATOR_STATE_COMMAND_REQUIRES_FAKE_MODE_NO_LIVE_CALLS",
                "MISSING_POSTGRES_CONFIGURATION",
                "BLOCKED_CREDENTIAL",
                "INVALID_PROVIDER_CONFIGURATION",
                "PRIVATE_STORAGE_UNAVAILABLE",
                "DATABASE_CONNECTION_FAILED",
                "INCOMPATIBLE_DATABASE_SCHEMA",
                "UNVERSIONED_EXISTING_DATABASE_SCHEMA",
                "NODE_MISSING",
                "ORIGINAL_STORAGE_INTEGRITY_FAILED",
                "ORIGINAL_CONTENT_INTEGRITY_FAILED",
                "PROJECT_HEAD_INTEGRITY_FAILED",
                "SNAPSHOT_REVISION_INTEGRITY_FAILED",
                "SNAPSHOT_SOURCE_INTEGRITY_FAILED",
                "PROHIBITED_BACKUP_FILE",
                "BACKUP_REFERENCED_ORIGINAL_MISSING",
                "BACKUP_REFERENCED_ORIGINAL_CORRUPT",
                "RESTORE_VALIDATION_FAILED_NO_MERGE",
                "FILE_ARGUMENT_REQUIRED",
                "PROJECT_SOURCE_REFERENCE_INTEGRITY_FAILED",
                "SOURCE_ANCHOR_SET_INTEGRITY_FAILED",
                "ADMIN_ARTIFACT_IDENTITY_INTEGRITY_FAILED",
                "ADMIN_MANIFEST_REFERENCE_INTEGRITY_FAILED",
                "ADMIN_VARIANT_CONTENT_INTEGRITY_FAILED",
                "ADMIN_EXPECTATION_REFERENCE_INTEGRITY_FAILED",
                "ADMIN_VARIANT_REFERENCE_INTEGRITY_FAILED",
                "ADMIN_RUN_REFERENCE_INTEGRITY_FAILED",
                "PRIVATE_ARTIFACT_MUST_BE_OUTSIDE_REPOSITORY",
                "INVALID_OR_INCOMPATIBLE_PORTABLE_IMPORT",
                "RESTORE_REQUIRES_EMPTY_TARGET",
                "CORRUPT_OR_INCOMPATIBLE_BACKUP",
                "SCENARIO_SEED_REQUIRES_EMPTY_PROJECT_STORE",
                "RUN_MIGRATE_BEFORE_OPERATOR_COMMAND",
            }
            else "DATABASE_OPERATION_FAILED"
            if isinstance(exc, (sqlite3.DatabaseError, psycopg.Error))
            else "STATE_REFERENCE_INTEGRITY_FAILED"
            if isinstance(exc, KeyError)
            else "STORAGE_PERMISSION_DENIED"
            if isinstance(exc, PermissionError)
            else "STORAGE_FILE_MISSING"
            if isinstance(exc, FileNotFoundError)
            else "INVALID_OPERATOR_INPUT"
        )
        print("FAIL " + args.command + ": " + code, file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
