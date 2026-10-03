# ADR 0006: bounded replaceable OpenAI provider

Accepted by the owner’s RDW-005 completion request. OpenAI is the first provider, not the permanent scientific standard. The provider-neutral domain/policy remain independent of HTTP/provider types. Use direct Responses REST through the already-used HTTPX library (promoted to runtime dependency), not an agent framework. Model, timeout, reasoning effort, output ceiling, context/call/token limits and dated cost inputs are server environment configuration. Default development model is gpt-6-sol; no silent model substitution. Final quality requires later benchmark/calibration evidence.

Privacy: foreground store=false, no tools, web, provider files/vector storage, previous response IDs or provider conversations. Only server-authorized ContextPacket text is sent; source IDs/anchors remain available. OPENAI_API_KEY is read only from the server environment and never enters configuration serialization, domain records, browser or ordinary logs. store=false does not guarantee Zero Data Retention; that requires eligible account controls. Provider retention/abuse monitoring and cache behavior still apply.

Interpretation is proposed representation, never evidence verification. Evaluation produces judgments with typed attribution. A focused checker inspects decision-driving judgments against the same original packet, records structural and semantic dispositions separately, and can withdraw unsupported judgments. Model agreement is not empirical verification. Final arithmetic/readiness remain the immutable deterministic policy engine. A targeted dimension task requests only that dimension and its focused check; unrelated dimensions remain uninspected, never zero.

Reserve worst-case request input/output token allowances before each attempt, including checking and retries. Context admission uses a conservative UTF-8 byte bound, not a claimed precise tokenizer. Timeout/transport uncertainty consumes the reserved allowance; only 429 and 5xx get bounded retries, and every attempt consumes a call and budget. No timeout or malformed-content retry. Prices are reporting inputs, not a billing guarantee; token ceiling is the authoritative overall guard. GPT-6 Sol default rates dated 2026-10-02 are $2/M input, $0.20/M cached input, $2.50/M cache-write and $10/M output; record all returned usage details without hidden reasoning text. Alternate models require explicit rate inputs.

Long evaluation jobs return a run handle and run in a single bounded local worker; private durable receipts contain only safe status/usage metadata. Interrupted receipts fail visibly on restart, never automatically repeat paid calls. This is local development, not a deployed durable distributed queue. Snapshot publication rechecks current authorization/admission/revision atomically; failures preserve existing history.

Official references checked 2026-10-02:
- https://developers.openai.com/api/docs/models/gpt-6-sol
- https://developers.openai.com/api/docs/guides/structured-outputs
- https://developers.openai.com/api/docs/guides/your-data

At initial implementation, the environment lacked a key and live smoke was BLOCKED_CREDENTIAL. The subsequent owner-authorized compatibility acceptance combines previously observed live interpretation/evaluation with one successful corrected targeted checker call. See the RDW-005 task record; scientific calibration remains future work.

Source-version convention: the current packet includes latest admitted versions plus admitted versions cited by retained project interpretations. Earlier versions are marked historical, retained for provenance, and cannot silently replace the current draft. A revoked reference fails before model processing. Structural source resolution and semantic dispositions are stored separately; neither is independent empirical data verification. Safe private provider receipts also preserve failed intake calls without storing request/response text.
