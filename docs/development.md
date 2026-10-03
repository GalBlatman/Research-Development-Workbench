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

## Bounded OpenAI workflow

Offline fake remains the default. To authorize real processing, set RDW_PROVIDER=openai on the server and provide OPENAI_API_KEY only in its environment. The browser intake discloses the provider before enabling processing. No key is part of a project, schema, frontend or checked-in example. Do not put private material in environment examples.

Server settings: RDW_MODEL (development default gpt-6-sol), RDW_REQUEST_TIMEOUT (30 seconds), RDW_REASONING_EFFORT (low, empty omits), RDW_MAX_OUTPUT_TOKENS (6000, includes reasoning), RDW_MAX_CONTEXT_BYTES (150000), RDW_MAX_INPUT_TOKENS (200000 conservative text-byte bound), RDW_MAX_CALLS (4), RDW_MAX_RUN_TOKENS (500000) and RDW_RETRIES (1). Set explicit dated RDW_INPUT_RATE/RDW_CACHED_RATE/RDW_CACHE_WRITE_RATE/RDW_OUTPUT_RATE/RDW_PRICE_DATE for another model. The token ceiling is authoritative; rates support later reporting and are not a charge guarantee. Reserve allowances for checking/retries; exhaustion never publishes an unchecked success. No silent model substitution.

Real evaluation returns HTTP 202 with a run handle; the browser polls its project-scoped status and opens the stored review on success. POST /api/projects/{id}/evaluations/targeted accepts expected_revision and a nonempty dimensions array; it performs only those dimension judgments and their focused checks. Missing other dimensions withhold corresponding totals. This supports later calibration without implementing calibration itself. Local receipts under the private runtime preserve request/model/prompt hashes/status/usage and interruption/failure information, never request/response text or hidden reasoning. A restarted interrupted run fails visibly; it is never automatically recharged. See ADR 0006 for bounded local-worker limits.

Privacy settings are foreground store=false with no web/tools, provider files/vector storage, background responses or conversations. This is not a guarantee of Zero Data Retention; eligible account controls are required. Source-backed statements establish attributed supplied-source content, not empirical truth. Focused checking can withdraw judgments and correct/qualify the summary while retaining original proposals and dispositions. Existing scientific policy remains pure and unchanged.

The explicitly invoked synthetic smoke is uv run --locked python -m api.smoke from backend. It checks credential availability first; with no key it emits BLOCKED_CREDENTIAL and sends nothing. With a key it runs one synthetic interpretation/evaluation/check workflow with zero retries, validates schemas/server snapshot/policy/usage, and prints safe status only. It never reads the private reference folder or a user's project. Do not run repeated live experimentation.
