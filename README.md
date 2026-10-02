# Research Development Workbench

An author-facing research workspace intended to turn supplied ideas and authorized literature into inspectable assessments and bounded next actions. Current status: foundation only; there is no working application.

Evaluation policy: [rubric v4](policies/rubric-v4.md). Product behavior: [specification](docs/product-spec.md). Read [AGENTS.md](AGENTS.md), [architecture](docs/architecture.md), [roadmap](docs/roadmap.md), and [task contracts](docs/tasks/RDW-001.md). The reference HTML is a synthetic design mockup, not application code.

## Local checks

Use Git and Node 24.19.0 (pinned in .node-version). Clone the repository into a development directory outside private references and synced research folders; change into the checkout, then run:

```text
node scripts/check.mjs
node --test tests/bootstrap.test.mjs
git config core.hooksPath .githooks
```

There are no Node package dependencies to install. The dependency-free checks also run in CI. Frontend React/TypeScript package installation, formatting/linting/build and a lockfile remain pending until package tooling is available; no frontend source exists yet.

The backend remains Python/FastAPI with Pydantic. Before RDW-002, provision Python 3.12 and uv, resolve and commit a reviewed backend lockfile, then run uv sync, uv run ruff check ., uv run ruff format --check ., uv run mypy domain policy_engine and uv run pytest from backend. Those commands become applicable when RDW-002 adds those modules/tests; the bootstrap deliberately contains neither. See docs/development.md for pending environment work.

The intended architecture is a modular monolith. The backend owns deterministic policy; the frontend only presents results. Original files and structured project records are separate. Fake models precede any real provider.

This repository is public. Do not add papers, their conversions, builder exports, uploaded projects, private reports or secrets. Approved governing documents are copied unchanged; their scholarly citations do not authorize redistribution of source papers. Publication checks complement explicit file review and cannot prove all content is safe.

Not implemented: domain/scoring engine, persistence, parsing, UI, models, retrieval, authentication, deployment or evaluation harness. Licensing remains an owner decision. Remote synchronization and GitHub Actions execution are pending.
