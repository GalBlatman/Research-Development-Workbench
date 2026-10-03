# Private pilot operations

RDW-008 hardens the existing local Workbench. Use synthetic projects for acceptance. PostgreSQL 17 remains canonical; SQLite is an explicit lightweight local option. Bind both servers to loopback. There is no authentication, multi-user isolation or public deployment support. GATE-3 is separate and has not been started.

## Install and configuration

Use the repository's Python 3.12.15, uv 0.12.22, Node 24.19.0 and pnpm 11.19.0. From the checkout:

```powershell
uv sync --locked --directory backend
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
$env:RDW_RUNTIME_ROOT = Join-Path $env:LOCALAPPDATA 'ResearchDevelopmentWorkbench/pilot'
$env:RDW_PROVIDER = 'fake'
$env:RDW_DATABASE_MODE = 'postgres'
```

Provision a local PostgreSQL 17 server using its normal installer/service, create a dedicated owner role and empty database, and supply its connection string as `RDW_POSTGRES_DSN` in the backend process environment. Use the database's password prompt or protected local credential mechanism; do not put credentials in this checkout, commands committed to Git, browser configuration or exports. PostgreSQL must be running before migration/startup. A disposable test database uses `RDW_TEST_POSTGRES_DSN`, never the pilot database.

For a deliberately selected lightweight local demonstration, set `$env:RDW_DATABASE_MODE = 'local-sqlite'` instead. This writes `projects.sqlite` in the private runtime directory and requires no PostgreSQL service. Missing PostgreSQL configuration never switches to SQLite. Place the runtime outside this repository and private-reference folders, on a writable local filesystem. Protect it with owner-only OS access. Keep originals, receipts and administrator benchmark gold private.

```powershell
uv run --locked --directory backend python -m services.pilot status
uv run --locked --directory backend python -m services.pilot migrate
uv run --locked --directory backend python -m services.pilot health
uv run --locked --directory backend uvicorn api.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

In a second terminal, from the same checkout, run `pnpm --dir frontend dev` and open `http://127.0.0.1:5173`. Keep the backend configuration in the backend terminal only. Status reports provider/model, storage mode, credential presence and budgets, never key values or DSNs. Startup rejects missing credentials, unsupported provider/configuration, inaccessible storage and incompatible schema with fixed diagnostics. Migration supports empty databases and version 1 to version 2; it adds a snapshot revision index without rewriting scientific records. Repeating migration at version 2 validates tables, columns and immutability guards without changing projects.

## Synthetic pilot and manual flow

Before starting the backend, load an empty local store with:

```powershell
uv run --locked --directory backend python -m services.pilot seed
```

The seed refuses a nonempty project store. A–I are nine original fictional projects: EXPLAIN early idea, specified proposal and completed study; ESTABLISH; TEST; source disagreement; serious rival; stale dependency after a consequential edit; and incomplete/pending output. J is the existing harness's hidden-feature `cannot know` fixture, in the administrator benchmark store. They demonstrate state and interfaces, not scientific calibration. The deterministic fake does not semantically judge their prose: unsupported interpretations remain pending. Mocked provider tests separately demonstrate actual incomplete/refusal/timeout failures; scenario I does not pretend a pending fake judgment is a transport failure.

Alternatively, use Load synthetic example in the browser. Authorize local processing, create the project, inspect the proposed representation, accept or correct it, add an authorized supplied source, and request a fake evaluation. Inspect the contribution, obstacle, evidence limitations, next bounded action and backend rule trace. Use Argument/Study or another existing workspace for a targeted check. Accepting a suggestion creates a revision but never verifies evidence. Edit consequential content or add a source version, inspect selective staleness and History, and open the old review. Its frozen revision, provenance and policy result stay unchanged. Export JSON or Markdown from the current project or a historical review.

Stop the frontend and backend with Ctrl+C, retaining the runtime directory/database. Restart with the same configuration and reload the bookmarked project. Navigation, reload and rendering invoke no provider calls. The restart browser test stops the actual backend process and confirms revision, source hashes and immutable review recovery.

## Optional real provider

Real processing requires an intentional backend configuration change: `RDW_PROVIDER=openai`, the existing runtime `RDW_MODEL=gpt-6-sol` default, and `OPENAI_API_KEY` supplied only to the server through protected environment handling. Restart the backend; inspect safe status and the browser provider disclosure before authorizing content transmission. Never set keys in frontend environment variables. Missing credentials fail; there is no fake fallback. Alternate models retain the existing explicit dated pricing requirement and may fail visibly if unavailable; no automatic substitution occurs.

Existing `RDW_REQUEST_TIMEOUT`, `RDW_MAX_CONTEXT_BYTES`, `RDW_MAX_INPUT_TOKENS`, `RDW_MAX_OUTPUT_TOKENS`, `RDW_MAX_CALLS`, `RDW_MAX_RUN_TOKENS` and `RDW_RETRIES` bound requests. See development.md for defaults. Foreground requests use `store=false`, no tools/web/background/provider files. Account retention controls remain an owner responsibility. Neither seed, health, backup nor this task's acceptance invokes a live provider.

## Failure and recovery

A project-scoped run receipt records queued/running/succeeded/failed state, timestamps/duration, failure classification, frozen expected revision and available provider task/model/usage metadata. Safe operational logs record identifiers, transitions, timing and token/call summaries; they exclude prompts, source passages, raw provider errors, hidden gold and secrets. Missing usage stays unknown in the provider receipt. User validation errors do not echo submitted text.

Only one asynchronous local worker operates in one backend process. Run requests with the same project/revision/task scope return the existing receipt, including completed or failed receipts. Restart reconciles a committed snapshot or proposal using its server operation ID; incomplete work becomes `interrupted_uncertain` and is never automatically replayed. Timeout/connection uncertainty remains uncertain. No partial unchecked final review is published. A concurrent revision/source change produces a conflict and retains incurred provider usage; reload before making a new bounded request.

Ordinary UI requests leave `retry_failed=false`. An owner may deliberately authorize another attempt through the existing evaluation/targeted/workspace request API with `retry_failed:true` and the current `expected_revision`, after inspecting the failed receipt and any uncertain charge. This creates a new run ID and retains the failed history. Do not automate retries after uncertainty. Deterministic fake synchronous requests do not incur provider spend. Idempotency is scoped to the local worker's scientific request, not a distributed lock across independently launched backend processes; run only one backend per runtime. Repeating the same completed request at the same revision reuses the result even after a provider configuration change; a fresh bounded scientific request needs a new revision/scope.

## Private backup and restore

Stop the backend and any benchmark controller first. This is a stopped-app logical backup, not a hot-backup or PostgreSQL disaster recovery system. Put the destination outside Git and protect it: backups contain source text/originals, all project histories and administrator gold. They are not ordinary publication exports and are not encrypted by the application.

```powershell
$backupFile = Join-Path $env:LOCALAPPDATA 'ResearchDevelopmentWorkbench/pilot-backup.json'
uv run --locked --directory backend python -m services.pilot backup --file $backupFile
```

A new exclusive destination prevents accidental overwrite. Versioned checksums detect corruption. Projects, revisions, admitted and unadmitted source versions, anchors, provenance, suggestions, evaluations, immutable reviews, run/provider receipts and supported benchmark definitions/reservations/runs are preserved. Configuration/environment credentials are excluded; finding the configured API key in data rejects creation. User-authored text must itself be free of secrets.

Restore only your own trusted backup into a fresh private runtime and empty database. Set the new `RDW_RUNTIME_ROOT` and a new empty PostgreSQL database/DSN, or explicitly select local SQLite. Do not start the app before restore:

```powershell
uv run --locked --directory backend python -m services.pilot migrate
uv run --locked --directory backend python -m services.pilot restore --file $backupFile
uv run --locked --directory backend python -m services.pilot health
```

Unknown versions, invalid hashes/paths/contracts or missing original files fail visibly. Restore refuses populated targets and never merges conflicting histories. Failure rolls back the database and removes only newly created files. Checksums are not authenticity or scientific truth certification. Benchmark annotations or arbitrary extra files are unsupported and fail rather than being silently discarded; retain such administrator artifacts separately. Use ordinary PostgreSQL backup tooling separately if broader server recovery is needed.

## Portable project import

JSON exports retain typed project/review history, route/stage, evidence/adoption states, source/version/anchor identities and provider metadata. They exclude source text, original bytes and local storage keys. JSON exports use `rdw-app-1`; the operator importer supports both the new typed import bundle and the previous view-only export shape. Import into the same local owner workspace in a separate store:

```powershell
uv run --locked --directory backend python -m services.pilot import --file 'C:\private-runtime\project-export.json'
```

Import state commands require fake mode and make no model calls. They reject malformed/unknown contracts, cross-project references, role changes, generated-source authority escalation and an existing project ID. Preserved source hashes identify external originals; portable import does not reconstruct source text or confer verification. Already inspected checks are historical assertions, not reverified by import. Use private backup for complete source recovery. Markdown is a readable export, not a supported import format.

## Harness and self-check

Run the existing fake-only harness outside Git, preferably in a separate pilot runtime's benchmark directory:

```powershell
uv run --locked --directory backend python -m benchmarks --output "$env:RDW_RUNTIME_ROOT/benchmarks" --mode WORKBENCH --component FULL --concurrency 2
uv run --locked --directory backend python -m benchmarks --output "$env:RDW_RUNTIME_ROOT/benchmarks" --mode BASELINE --component FULL --concurrency 2
uv run --locked --directory backend python -m services.pilot health
```

Harness outputs keep administrator gold separate from evaluator packets. Immutable artifacts publish atomically on local filesystems supporting hard links. Existing reservations prevent duplicate completion/replay; resumable batches honor conservative call/token/cost ceilings. Failed/uncertain reservations require inspection, not automatic recharge. Baseline and Workbench results and per-paper aggregation remain distinct. Evaluator scratch databases are disposable; preserved administrator run records contain outputs. Do not mix administrator reports into evaluator inputs. See benchmark-harness.md for versioning, blindness and limitations.

Health returns concise JSON PASS/FAIL and a failing exit status for a failed check. It parses safe configuration, connects to the configured database, validates schema/version/immutability guards, and runs isolated synthetic fake/source/persistence, 16 golden and benchmark tests, generated OpenAPI compatibility and publication/governing checks. It does not migrate, seed, read private project content, alter scientific state or make live calls. Local PostgreSQL parity is checked separately using a disposable test database and is mandatory in CI. Full frontend build and browser acceptance are separate developer checks.

No operating-system sandbox against arbitrary malicious local Python code, encrypted backup service, distributed worker, OS power-loss durability guarantee, public security boundary or new scientific validation is claimed. Leave GATE-3 to the independent auditor.
