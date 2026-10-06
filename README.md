# Research Development Workbench

An author-facing research workspace for inspectable assessments and bounded next actions. RDW-006 provides ten research workspaces over one canonical project with bounded model proposals, adoption, dependency staleness and targeted reviews. It demonstrates state, sources, policy calculations and review delivery; it does not assess scientific judgment.

Create a project, paste an idea and authorized literature excerpt, inspect the proposed interpretation, run a limited or exact synthetic fake evaluation, inspect source passages and backend rubric traces, edit/reload, and export Markdown/JSON. Old evaluation snapshots remain unchanged. React/TypeScript displays backend results; Python/FastAPI/Pydantic services own state and policy. PostgreSQL is canonical; SQLite supports the local demonstration/tests. Originals stay outside Git and structured records.

See [development instructions](docs/development.md), [task contract](docs/tasks/RDW-006.md), [architecture](docs/architecture.md), [roadmap](docs/roadmap.md), [product specification](docs/product-spec.md), and [immutable rubric](policies/rubric-v4.md). Python 3.12.15 / uv 0.12.22 and Node 24.19.0 / pnpm 11.19.0 have committed dependency locks. Run node scripts/check.mjs, full backend tests/type/lint, generated contract checks, frontend build and browser tests before integration.

The app is loopback-only development, without authentication or deployment. A bounded replaceable OpenAI Responses adapter is available by explicit server configuration; offline fake remains the default. No provider SDK, external literature discovery, PDF/DOCX or calibration. Fake suggestions remain proposed/not inspected unless explicitly adopted as representation; adoption never verifies evidence. GATE-1 findings are resolved; RDW-005 real-provider implementation preserves the pure policy boundary. RDW-005 live compatibility is recorded in its task contract; RDW-006 uses synthetic offline/mock-provider regressions. Licensing remains an owner decision.

This repository is public. Never add private papers/conversions, builder exports, uploads, runtime records, reviews or secrets. Synthetic fixtures only. Publication checks complement exact staged-tree review; scholarly citations do not authorize redistribution. The reference HTML is an approved synthetic design mockup, not the running application.

## Research review prompt

The [single-file Baseline-Plus research review prompt](docs/tools/Baseline_Plus_Research_Review_Prompt_v1.md) is derived from the Research Development Workbench work and intended for direct use with a research idea or project packet. This exact single-file prompt has not itself been empirically validated. This repository is its canonical home, including its provenance and version history.
