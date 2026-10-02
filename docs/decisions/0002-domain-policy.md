# ADR 0002: exact pure policy and immutable domain contracts

Status: accepted within owner-authorized RDW-002, 2026-10-02.

Keep Python 3.12 and pin 3.12.15, selected by uv. This conservatively preserves RDW-001's minor target; Pydantic v2 supports it and FastAPI advertises Python 3.12 compatibility. Sources: https://pydantic.dev/docs/validation/2.12/get-started/install/ and https://github.com/fastapi/fastapi/blob/master/pyproject.toml . System Python 3.14.7 remains separate. Installed Pydantic 2.13.5 and test/lint/type dependencies resolve and run under 3.12.15; no FastAPI runtime is installed for this pure task.

Pin uv 0.12.22 in CI and exact direct dependency versions; backend/uv.lock freezes transitive artifacts. Use uv sync --locked for reproducibility. The initial uv Python installation reported a minor-link error, but uv find and the resulting isolated interpreter executed successfully.

Pydantic is already the specified contract technology, not a new framework decision. Frozen models and tuple collections preserve deep snapshot records. Fractions retain exact rational totals; whole-point display rounds halves upward after gate evaluation. Manifest owns weights and excellence profiles; executable rule branches are traced to immutable v4 clauses. Origin/adoption/evidence/check provenance/freshness remain independent. Only supported findings act as TRUE/FALSE; unresolved verification acts as UNKNOWN, never a fabricated cap or default endorsement.

PROMISE-OVERREACH needs an explicit supported mapping to a named existing idea/project rule; without that mapping the input is rejected for clarification. This implements v4 §8.3 without adding a penalty or language heuristic. Exceptional ratings without relevant inspected comparisons are withheld, not clamped. No automatic scientific interpretation exists.

Scope: pure domain/policy only; no models, network, parser, database, API or frontend implementation. Semantic route/prerequisite judgments remain human/evaluator inputs. Reproduction provenance is represented but cannot be assigned by this release because it executes no statistical analyses.

Integration follows the owner's explicit authorization: task branch, complete checks, review of scope/diff and actual CI, then main integration. No fabricated reviewer or independent scientific audit is claimed.

Snapshots additionally pin the executable manifest digest and implementation version, not just the scholarly rubric hash. UTF-8 decoding is explicit so digest identity survives platform changes. Required uninspected study dimensions prevent an unqualified submission-readiness gate.
