# Development environment

RDW-002 uses project Python 3.12.15, uv 0.12.22, Pydantic 2.13.5 and the committed backend/uv.lock. System Python 3.14.7 is not the project interpreter. See decisions/0002-domain-policy.md for compatibility rationale.

From backend run:

```text
uv sync --locked
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy domain policy_engine persistence services
```

From the repository root run node scripts/check.mjs and node scripts/publication-guard.mjs --staged before commit. Enable git config core.hooksPath .githooks for the staged-blob publication hook. Fresh environments use the pinned interpreter and lock, not dependency upgrades. The node checks remain dependency-free.

RDW-003 adds the locked Psycopg driver and scoped source/persistence contracts. Local tests run SQLite; set RDW_TEST_POSTGRES_DSN to a private disposable test database to run PostgreSQL parity. CI requires PostgreSQL via RDW_REQUIRE_POSTGRES=1 and a digest-pinned ephemeral service. Never put production credentials in fixtures/logs. Frontend tooling, PDF/DOCX and provider/evaluation services remain outside this milestone. No application feature beyond pure domain and calculations is claimed.
