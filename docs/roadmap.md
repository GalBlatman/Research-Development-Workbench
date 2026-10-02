# Roadmap

| Item | Scope | Dependency | State |
|---|---|---|---|
| RDW-001 | Bootstrap repository and governance | Canonical rubric/spec | Complete |
| RDW-002 | Domain model and deterministic rubric engine | RDW-001; Python environment and locked tooling | Complete |
| RDW-003 | Source/document core and project persistence | RDW-002 | Pending |
| RDW-004 | Minimal end-to-end app using a fake model | RDW-003 | Pending |
| GATE-1 | Independent architecture/acceptance audit | RDW-004 | Required before RDW-005 |
| RDW-005 | Real bounded LLM evaluation workflow | GATE-1 passed; provider/data/budget decisions | Pending |
| RDW-006 | Research workspaces and revision loop | RDW-005 | Pending |
| GATE-2 | Independent scientific-behavior audit | RDW-006 | Required before RDW-007 |
| RDW-007 | Benchmark and ablation harness | GATE-2 passed | Pending |
| RDW-008 | Private-pilot reliability and hardening | RDW-007 | Pending |
| GATE-3 | Final independent acceptance audit | RDW-008 | Required before pilot acceptance |

No audit is claimed complete. Fake-model correctness does not validate research judgment.
