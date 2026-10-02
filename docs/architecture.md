# Architecture baseline

Derived from product specification sections 8–18 and 23; see decisions/0001-bootstrap.md. The specification chooses React/TypeScript, Python/FastAPI/Pydantic, PostgreSQL, private file storage and a worker sharing domain code. Governance/domain/policy and scoped text/Markdown source/persistence foundations are implemented through RDW-003; other modules remain planned. PostgreSQL is canonical; SQLite shares the same contracts for local tests (ADR 0003).

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

No vector/graph database, agent framework, model SDK or deployment service is selected. Parsing, provider, queue details, retention, identity and hosting require later decisions. No empty module hierarchy is required before its task. RDW-002 covers pure domain/policy only; persistence begins RDW-003.
