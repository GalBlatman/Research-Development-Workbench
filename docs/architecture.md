# Architecture baseline

Derived from product specification sections 8–18 and 23; see decisions/0001-bootstrap.md. The specification chooses React/TypeScript, Python/FastAPI/Pydantic, PostgreSQL, private file storage and a worker sharing domain code. Governance/domain/policy, scoped text/Markdown persistence and a minimal loopback browser/API/fake-adapter/review slice are implemented through RDW-004; a bounded replaceable OpenAI provider is implemented in RDW-005 (ADR 0006); all ten research workspaces and the revision loop are implemented in RDW-006 (ADR 0007). PostgreSQL is canonical; SQLite shares the same contracts for local tests (ADR 0003).

## Ownership boundaries

- API: request contracts and server-side authorization.
- Domain/project service: typed records, independent origin/adoption/evidence/freshness states, revisions and immutable evaluation snapshots.
- Policy engine: pure deterministic scores, caps, applicability, readiness and traces. No model, database or network dependency. Frontend and report renderer never recalculate grades.
- Source service: preserve immutable originals separately from structured records; parsing is isolated from privileged operations; anchors and coverage describe what was inspected.
- Retrieval: only explicitly authorized source material, with server-provided authorization scope and recorded exclusions. Identifiers or model text cannot confer access.
- Workflow: bounded stages, budgets, cancellation and idempotent publication; durable queue interface later.
- LLM adapter: typed provider interface, no direct database credentials or arbitrary file access; fake implementations must exercise the same interface.
- Verifier: check anchors and semantic support; schema validity alone is insufficient.
- Planner/report/history: bounded proposals, presentation without policy changes, dependency invalidation and immutable historical results.

Source text and generated text remain distinct. Accepting a proposal confirms representation/adoption, never verified evidence. Revisions create new snapshots; no historical score overwrite or silent route comparison.

No vector/graph database, agent framework, provider SDK or deployment service is selected. OpenAI uses direct Responses REST via the locked existing HTTPX client; model/budgets are runtime configuration. Parsing, distributed queue, deployment retention, identity and hosting require later decisions. The current local single-worker run handles have durable safe receipts, bounded calls and no paid replay on interruption. No empty module hierarchy is required before its task. RDW-002 covers pure domain/policy only; persistence begins RDW-003.
