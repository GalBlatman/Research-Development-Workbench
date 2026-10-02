# Research Development Workbench

An author-facing research workspace intended to turn supplied ideas and authorized literature into inspectable assessments and bounded next actions. Current status: governance plus pure domain and deterministic v4 policy; there is no working application.

Evaluation policy: [rubric v4](policies/rubric-v4.md). Product behavior: [specification](docs/product-spec.md). Read [AGENTS.md](AGENTS.md), [architecture](docs/architecture.md), [roadmap](docs/roadmap.md), and [task contracts](docs/tasks/RDW-001.md). The reference HTML is a synthetic design mockup, not application code.

## Local checks

Use Git and Node 24.19.0 (pinned in .node-version). Clone the repository into a development directory outside private references and synced research folders; change into the checkout, then run:

```text
node scripts/check.mjs
node --test tests/bootstrap.test.mjs
git config core.hooksPath .githooks
```

There are no Node package dependencies to install. The dependency-free checks also run in CI. Frontend React/TypeScript package installation, formatting/linting/build and a lockfile remain pending until package tooling is available; no frontend source exists yet.

The backend keeps the planned Python/FastAPI/Pydantic stack. Pure domain and policy contracts are implemented with Pydantic; no API exists. Use Python 3.12.15 and uv 0.12.22. From backend run uv sync --locked, then uv run --locked pytest -q, uv run --locked ruff check ., uv run --locked ruff format --check . and uv run --locked mypy domain policy_engine. See docs/development.md for reproducible setup.

The intended architecture is a modular monolith. The backend owns deterministic policy; the frontend only presents results. Original files and structured project records are separate. Fake models precede any real provider.

This repository is public. Do not add papers, their conversions, builder exports, uploaded projects, private reports or secrets. Approved governing documents are copied unchanged; their scholarly citations do not authorize redistribution of source papers. Publication checks complement explicit file review and cannot prove all content is safe.

Not implemented: persistence, parsing, UI, models, retrieval, authentication, deployment or research-evaluation harness. Licensing remains an owner decision. Task branches must pass foundation and domain CI before main integration.
