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


def test_frontend_remains_placeholder():
    assert sorted(p.name for p in (ROOT / "frontend").iterdir()) == ["README.md"]
