# ADR 0008 — Administrator benchmark boundary

Status: Accepted within the owner-authorized RDW-007 architecture and task scope.

Use immutable private filesystem artifacts for benchmark administration and separate per-run instances of the existing repository/source service for blind evaluation. No new database, external service, agent framework or dependency is added. Pydantic owns benchmark contracts. Administrator records never enter provider packets; only a narrow BlindPacket crosses the execution boundary. Existing scoped repositories and bounded provider ledgers enforce source admission and provider limits. A small bounded thread pool supports batches; immutable exclusive reservations prevent uncertain automatic replay.

The baseline reuses the same adapter, packet and structured candidate schema with a single versioned prompt. Full and targeted modes call existing Workbench workflow methods and the deterministic policy engine. Metrics compare explicit typed expectations and preserve uncertainty. Detailed contracts, limitations and later corpus import are documented in docs/benchmark-harness.md. This decision does not authorize live spending, real corpus ingestion, calibration or RDW-008.
