# Development environment

RDW-002 uses project Python 3.12.15, uv 0.12.22, Pydantic 2.13.5 and the committed backend/uv.lock. System Python 3.14.7 is not the project interpreter. See decisions/0002-domain-policy.md for compatibility rationale.

From backend run:

```text
uv sync --locked
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy domain policy_engine
```

From the repository root run node scripts/check.mjs and node scripts/publication-guard.mjs --staged before commit. Enable git config core.hooksPath .githooks for the staged-blob publication hook. Fresh environments use the pinned interpreter and lock, not dependency upgrades. The node checks remain dependency-free.

Frontend tooling, persistence, document ingestion and runtime/provider services remain outside RDW-002. No application feature beyond pure domain and calculations is claimed.
