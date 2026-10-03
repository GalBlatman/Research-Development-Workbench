import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_governing_integrity():
    baseline = json.loads((ROOT / "docs/baselines.json").read_text(encoding="utf-8"))
    for doc in baseline["documents"]:
        assert (
            hashlib.sha256((ROOT / doc["repository_path"]).read_bytes()).hexdigest()
            == doc["source_sha256"]
        )


def test_policy_imports_only_pure_dependencies():
    allowed = {
        "__future__",
        "dataclasses",
        "fractions",
        "hashlib",
        "json",
        "typing",
        "pydantic",
        "domain",
        "policy_engine",
    }
    for filename in (ROOT / "backend/policy_engine").glob("*.py"):
        tree = ast.parse(filename.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".")[0] in allowed for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.level == 0:
                assert (node.module or "").split(".")[0] in allowed
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"open", "exec", "eval", "__import__"}


def test_policy_import_without_network_or_model_clients():
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import policy_engine; import sys; assert not any(n in sys.modules for n in ('httpx','requests','openai','anthropic','sqlalchemy','psycopg'))",
        ],
        check=True,
    )


def test_fake_adapter_cannot_access_network_or_persistence():
    allowed = {"typing", "domain", "model_adapters"}
    for filename in [
        ROOT / "backend/model_adapters/fake.py",
        ROOT / "backend/model_adapters/contracts.py",
    ]:
        tree = ast.parse(filename.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".")[0] in allowed for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.level == 0:
                assert (node.module or "").split(".")[0] in allowed


def test_provider_adapter_has_no_persistence_or_application_access():
    for filename in (ROOT / "backend/model_adapters").glob("*.py"):
        tree = ast.parse(filename.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(
                    alias.name.split(".")[0]
                    not in {"persistence", "services", "api", "psycopg", "sqlite3"}
                    for alias in node.names
                )
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in {
                    "persistence",
                    "services",
                    "api",
                    "psycopg",
                    "sqlite3",
                }
