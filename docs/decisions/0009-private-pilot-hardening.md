# ADR 0009: Private local recovery boundary

Accepted for owner-authorized RDW-008 scope, conditional on required checks and CI.

PostgreSQL remains canonical. Configuration requires explicit database selection and a private writable runtime outside Git; local SQLite is an explicit lightweight option, never a fallback. Existing versioned SQL migrates 1 to 2 with an index only. Startup validates schema and immutable guards without rewriting science.

One local asynchronous worker writes atomic safe receipts. Request identity prevents ordinary duplicate submissions; an explicit failed-run retry creates a new immutable attempt. Server-only operation IDs reconcile a committed snapshot/proposal after interruption. Uncommitted or uncertain work is not replayed. Optimistic revisions reject concurrent updates and preserve frozen source/context histories and incurred provider receipts.

Private stopped-app logical backups preserve scoped scientific histories and allowlisted runtime originals/receipts/benchmark records. Restore requires a fresh target, validates hashes/contracts before publication and rolls back on failure. Ordinary portable exports preserve scientific distinctions but strip local file authority and source text. Imports never confer verification, merge project identities or promote generated origins.

An operator CLI provides safe status, migration, fake-only scenarios, import, backup/restore and read-only synthetic health. No dependency, provider, database framework, distributed worker, public service, rubric or research workspace is added. These checks support the existing private pilot; they are not GATE-3 or scientific calibration. Operational limitations and commands are in docs/private-pilot.md.
