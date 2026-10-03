# Coding agent contract

Read policies/rubric-v4.md, docs/product-spec.md, docs/architecture.md and the named docs/tasks task contract before modifying behavior. Authority: rubric v4, specification, accepted decisions, task contract, implementation.

Execute only the named task. Preserve module boundaries; stop and report when required work exceeds scope. Never change rubric policy implicitly or duplicate scoring in the frontend. Prompts are versioned code and require relevant tests. Model output is proposed content; adoption never automatically verifies evidence.

Never expose private references, uploads, unpublished research, builder exports or credentials. Review every staged file and run node scripts/check.mjs and required task tests before completion. No new external service, agent, database or major dependency without a documented accepted architecture decision. No software license has been selected.

Workflow: short-lived task branch -> required checks -> human review -> merge. The initial local main commit is the RDW-001 bootstrap exception. Main integration requires successful task checks and documented review; follow the owner-authorized integration workflow. RDW-004 is the minimal fake-model UI/API slice; real providers and independent GATE-1 require separate named tasks. Persistence SQL is never a model-facing interface; recheck server scope and admitted document versions before returning source material.
