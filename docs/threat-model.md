# Initial threat model

Assets: private drafts/literature, project records, immutable snapshots, provider credentials and budgets. Trust boundaries: browser/server; untrusted uploaded text/parser; authorization/retrieval; workflow/provider; private runtime/public repository.

| Threat | Intended control | Verification task |
|---|---|---|
| Accidental publication | Separate checkout/runtime/reference roots; explicit stage review; ignore plus publication guard | RDW-001 |
| Cross-project disclosure | Server authorization for every record/context and late publication | RDW-003/004 and release security gate |
| Prompt injection | Untrusted source text cannot grant permissions/tools; adapter has no DB credentials | RDW-005 |
| Fabricated evidence | Anchors, coverage, semantic verification; generation/adoption/evidence separate | RDW-002/005 |
| Malicious uploads | Restricted types/size; isolated parser; private storage | RDW-003/008 |
| Corrupted history/retries | Immutable snapshots, atomic outputs, leases/idempotency and budget reservations | RDW-003/008 |
| Retention leakage | Tested deletion/backups and restricted logs | RDW-008 |

The repository guard detects obvious names/extensions and credential patterns, not all copyrighted prose or every possible secret. Human content review remains required. No deployed security or model judgment quality is claimed.
