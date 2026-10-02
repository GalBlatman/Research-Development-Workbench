# RDW-003 acceptance and scope review

Required acceptance maps to backend/tests/test_persistence.py: reload/revisions/conflicts; document version/anchor identity; immutable snapshots; generated-source rejection and adoption/evidence distinction; deterministic round-trip of all evidence states and pending/not-applicable assessments; workspace/project/actor denial; missing/unreadable/external source handling; selected admitted retrieval and revocation; atomic import; database immutability triggers; hash/UTF-8/Markdown fence integrity.

Local full regression includes the 16 unchanged RDW-002 golden cases, all policy/domain tests, SQLite contracts, Node foundation tests, strict mypy and Ruff lint/format. PostgreSQL tests are explicitly skipped only when local DSN is absent; RDW_REQUIRE_POSTGRES=1 forbids that skip in CI. Actual PostgreSQL parity must pass before main integration.

Reviewed publication scope: synthetic tests, source/persistence/service code, dependency lock, CI and first-party task documentation only. No private references, uploaded research, builder exports, source papers, environment files or production credentials. Policy text/product specification stay byte-identical. No evaluation prompts, model dependencies, frontend research feature or RDW-004 implementation.

This is same-session implementation review, not an independent architecture/scientific audit. The owner explicitly authorized integration after acceptance; independent audits retain their roadmap gates.

Acceptance completed: GitHub Actions run 37078043138 on implementation commit 66621c57275159a18b9825a7eb668ca2d299e0df passed 101 Python tests (including all 24 PostgreSQL and 24 SQLite cases), four Node foundation tests, locked dependency installation, Ruff lint/format, strict mypy, publication guard and governing-file integrity. All 16 RDW-002 golden cases remain unchanged and pass. PostgreSQL 17 ran as an ephemeral CI service; no skips or failed checks. RDW-004 is ready but not started.
