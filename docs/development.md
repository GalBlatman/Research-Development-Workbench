# Development environment

Project Python 3.12.15, uv 0.12.22, Node 24.19.0, pnpm 11.19.0, exact dependencies and both committed locks. System Python is not the project interpreter. ADRs 0002–0004 record compatibility and boundaries.

From backend run uv sync --locked, uv run --locked pytest -q, uv run --locked ruff check ., uv run --locked ruff format --check ., uv run --locked mypy domain policy_engine persistence services model_adapters api. PostgreSQL parity uses a disposable RDW_TEST_POSTGRES_DSN; CI forbids skipping it. Never use production credentials. From root run node scripts/check.mjs and node scripts/publication-guard.mjs --staged; enable git config core.hooksPath .githooks.

## Run the local fake app

Choose an explicit private runtime directory outside the checkout and references. Set RDW_RUNTIME_ROOT to that directory. If RDW_POSTGRES_DSN is configured, it is the canonical backend; otherwise the local demo uses SQLite in the private directory. No runtime data is tracked. In backend run:

```text
uv sync --locked
uv run --locked uvicorn api.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

From frontend, with pnpm 11.19.0 available (install that pinned CLI if needed):

```text
pnpm install --frozen-lockfile
pnpm build
pnpm dev
```

Open http://127.0.0.1:5173. Paste your text for a limited fake review or load the synthetic example, authorize local idea/source processing, create the project, add the prefilled synthetic source, then run fake evaluation. Bookmark the project URL for reload. Arbitrary text gets pending judgments; fixture choice is internal and changed/mismatched material keeps judgments pending. Fake outputs do not evaluate science. Binding only to loopback is required; this slice has no authentication and must not be deployed/exposed to other users.

## Contracts and browser tests

In backend run uv run --locked python -m api.contracts (or --check). In frontend run pnpm contracts to regenerate types, pnpm check, pnpm exec playwright install chromium, then pnpm test:e2e. The browser test launcher creates a random temporary synthetic runtime outside Git, starts both loopback servers and cleans up its own test directory after exit. CI also checks that regeneration produces no diff. The backend/publication/golden tests remain separate from browser acceptance. No private data or screenshots are fixtures.
