# Roadmap

| Item | Scope | Dependency | State |
|---|---|---|---|
| RDW-001 | Bootstrap repository and governance | Canonical rubric/spec | Complete |
| RDW-002 | Domain model and deterministic rubric engine | RDW-001; Python environment and locked tooling | Complete |
| RDW-003 | Source/document core and project persistence | RDW-002 | Complete |
| RDW-004 | Minimal end-to-end app using a fake model | RDW-003 | Complete |
| GATE-1 | Independent architecture/acceptance audit | RDW-004 | PASS on RDW-004 baseline; five findings resolved in RDW-005 6A |
| RDW-005 | Real bounded LLM evaluation workflow | GATE-1 passed; provider/data/budget decisions | Complete; live compatibility accepted (see RDW-005 task record) |
| RDW-006 | Research workspaces and revision loop | RDW-005 | Complete; GATE-2 passed on 419b96f |
| GATE-2 | Independent scientific-behavior audit | RDW-006 | Owner-supplied PASS on 419b96f: 47/47 probes; G2-N2 resolved in RDW-007 |
| RDW-007 | Benchmark and ablation harness | GATE-2 passed | Complete; required CI gates owner-authorized integration |
| RDW-008 | Private-pilot reliability and hardening | RDW-007 | Complete; required CI gates owner-authorized integration |
| GATE-3 | Final independent acceptance audit | RDW-008 | Required before pilot acceptance |

GATE-1 PASS was supplied by the owner for the exact RDW-004 baseline; provenance and corrective resolution are recorded in docs/audits/gate-1.json. GATE-2 PASS on 419b96fc188951305be34a09c904082246b74052 was also supplied by the owner; G2-N2 resolution is recorded in docs/audits/g2-n2-resolution.json. No new independent audit is claimed by the implementation agent. Fake-model correctness does not validate research judgment.
