# Step 13 DEVELOPMENT calibration report

STATUS: BLOCKED — October 5, 2026 (local time). Roadmap: 13/16 — Calibration development set.

The authorized real-provider run stopped on `EXTERNAL_PROVIDER_BLOCKER:RATE_LIMIT`. Two concurrent Workbench attempts ended with RATE_LIMIT after the existing retry allowance. The client maps HTTP 429 to this code; the provider subcode and reset time were not retained, so temporary throttling versus account quota cannot be established from these records. No further provider request was made after the stop. Standing payload, destination, model and paid-use authorization remain valid.

## Coverage and validity

All 20 DEVELOPMENT papers were attempted under the current candidate. Complete final calibration coverage is **320/440 cases with terminal states in both modes**, including **197 valid pairs**. These are partial results, not completed Step-13 or validation estimates.

| Current candidate | Workbench | Baseline |
| --- | ---: | ---: |
| Immutable terminal attempts | 377 | 319 |
| Valid outputs | 248 | 256 |
| Failed outputs | 129 | 63 |
| Failure rate among attempted cases | 34.22% | 19.75% |
| INCOMPLETE_OUTPUT | 127 | 61 |
| RATE_LIMIT | 2 | 0 |
| TRANSPORT_ERROR_UNCERTAIN | 0 | 2 |

Two earlier uncertain terminal attempts and two earlier interrupted Workbench reservations remain unavailable under their original configurations. They are never relabeled as current valid results or replayed. Including these historical unavailable states, Workbench has 380/440 terminal/unavailable case states and baseline 320/440; **180 mode/case states remain pending**. Graceful worker shutdown left zero new unfinished reservations. The current archive contains 696 unique mode/case attempts and 504 valid outputs.

Execution reached only the completed-study package. Early-idea and specified-proposal execution remain pending. VALIDATION: **0/150 executed**, zero evaluator-result inspection. HELD_OUT: **0/75 executed**, zero evaluator-result inspection. No original papers, private builder source/history or prohibited package was accessed.

## Routing, admission and privacy

All five approved handoff hashes, canonical validation and exact sidecar joins passed: 440 DEVELOPMENT cases, 20 paper identities, 400 completed + 20 early + 20 proposal. Full scheduled routing remains 253 TARGETED_COMPONENT and 187 FULL_WORKBENCH. The stopped candidate actually executed 202 targeted + 175 integrated Workbench attempts and 168 targeted + 151 integrated baseline attempts. Every current attempt's component matches its canonical sidecar routing; no targeted case became FULL and no integrated case was split into independent component evaluations.

The sidecar stays in administrator orchestration and private metric aggregation. Journal, proximity, method/design and substantive-area labels and their detailed strata are retained only in private administrator analysis. None enter evaluator prompts, blind packets or ordinary project context. Gold, expectations, mutations, hidden content, private locators, originals and credentials remain excluded from provider payloads and Git.

Provider: OpenAI Responses, `https://api.openai.com/v1/responses`, configured `gpt-6-sol`; returned-model validation remains strict. Controls: `store=false`, foreground, `background=false`, no web/tools/uploads/files/vector stores. Runtime remains timeout 120 seconds, reasoning low, 6,000 output tokens per call, four calls and 500,000 tokens per run, $5 per-run bound, one retry, concurrency two and four-paper batches. No control was increased.

## Partial scientific metrics and fair comparison

Derived server findings are excluded from these scientific rates. Values below are expectation/judgment numerator/denominator followed by equal-weight paper macro rate over papers with an available metric. Case macro rates, availability counts, judgment families, nested paper results and all authorized strata are preserved privately. Missing or out-of-scope metrics are unavailable, never fabricated zeros or successes.

| Metric | Workbench observed count; paper macro | Baseline observed count; paper macro |
| --- | --- | --- |
| detection | 33/33; 100.00% | 27/27; 100.00% |
| invariance | 0/28; 0.00% | 0/33; 0.00% |
| withholding | 66/208; 29.26% | 83/246; 31.89% |
| state | 66/208; 29.26% | 83/246; 31.89% |
| restoration | 0/4; 0.00% | 0/5; 0.00% |
| direction | unavailable | unavailable |
| attribution | 1007/1007; 100.00% | 628/628; 100.00% |
| action | unavailable | unavailable |

These marginal rates condition on valid outputs and differ in coverage. The more comparable common-availability analysis requires both modes valid and equal feature denominators, averages available features within case, cases within paper, then papers. Its partial results:

- Detection: 100% versus 100%, 11 jointly available cases across eight papers.
- Invariance/isolation: 0% versus 0%, four jointly available cases across four papers. This includes exact statement wording signatures; it does not establish semantic noninvariance.
- Withholding and state: 30.71% versus 24.29%, 116 cases across 16 papers; Workbench minus baseline +6.43 percentage points. Paper-cluster descriptive 95% intervals span zero (withholding approximately -0.24 to +12.94 points; state -0.34 to +13.15).
- Restoration: 0% versus 0%, two jointly available cases across two papers; very limited availability and reference dependence.
- Attribution: 100% versus 100%, 77 jointly available cases across 16 papers. This measures admitted-anchor integrity, not semantic entailment or independent verification.
- Directional sensitivity and action relevance: unavailable. No independent semantic action annotation was manufactured.

There is **no established clear scientific Workbench advantage**. Baseline currently has better output availability, fewer calls and lower recorded cost/latency. Selection from output failures, pending cases and unavailable references limits all comparisons. Bootstrap resamples papers (5,000 draws, seed 13); repeated variants are not independent observations, and intervals are descriptive DEVELOPMENT diagnostics without multiplicity or selection correction.

The actual UNINSPECTED-BLOCK engine trace remains a separate product measurement; it is not a baseline scientific disadvantage. No derived-product scientific comparison is available in this partial snapshot. Model output stays proposed content; adoption never automatically verifies evidence.

## Error analysis A–I

| Class | Current conclusion |
| --- | --- |
| A — model recognition | Scoped scientific nonmatches are retained privately; no independently adjudicated recognition failure is claimed from an exact-prose proxy. |
| B — prompt/task contract | 188 current incomplete outputs under unchanged bounds. Earlier general scope, citation-role, concise-output and promise-mapping repairs are versioned and tested. No output-limit failure was selectively replayed to improve results. |
| C — checker | Earlier shared promise-basis validity discrepancy was repaired in both modes. Strict role, citation, scope and supported-basis checks remain. No new current checker defect established. |
| D — routing | Actual canonical task routing audit passed; full-set execution remains incomplete. |
| E — policy/engine | No new deterministic policy defect established. V5/V4 and engine behavior unchanged. |
| F — benchmark/metric translation | Numerical scope, absent-judgment restoration, runtime reference identity and derived-product separation were repaired generally. Out-of-scope comparisons remain unavailable; semantic action and exact-prose limitations remain explicit. |
| G — corpus/gold | No correction; approved handoff and gold remain unchanged. No private sources accessed to adjudicate gold. |
| H — ambiguity | Unresolved comparisons and missing references remain unavailable or qualified; no invented semantic adjudication. |
| I — recognition leakage | Frozen metadata-blinding equivalents have 17 available Workbench and 15 baseline comparisons, with three/five unavailable. No shared assessed numerical judgment is available for those equivalence pairs. Differences are robustness diagnostics, not proof of memorization. No explicit paraphrase cases exist in the frozen handoff; no new corpus or stochastic repeat-control experiment was added. |

External HTTP 429 and uncertain transport errors are operational failures outside A–I. Two transient current baseline transport failures were followed by successful requests and preserved without replay. The final 429 stop is the genuine current external blocker.

## Changes, checks and executed freeze

The current evaluator includes the earlier documented general repairs: exact baseline-v3 receipt identity, coherent withholding, restoration absence handling, specific integrity diagnostics, terminal failure receipts, V5 route input keys, exact numerical/task scope, deterministic configuration identity, interrupted-claim accounting, compact checking, bounded narrative output, exact citation triples and source-role schema branches, plus shared V5 promise-basis validity. These changes apply generally and use sanitized packets, never expected answers. Core Workbench components were not removed; compact checking simplifies the wire representation and expands back to ordinary checked references. No new service, dependency, database, model or frontend scoring was added.

Executed evaluator commit: `80f141778c64089a914a9cc40b977bd8cf0859f3` on `codex/step-13-calibration`. Source tree: `a96498bdfdf7fd726866414b70cdf402d6708f6871579de35572a02e445b0678`. Policy implementation 5.0.0; V5 canonical SHA-256 `d71a827c3ab1a0a74cbafe27a6907afaac11ae56b6568ab10f0d79d026166107`; policy manifest SHA-256 `6c9d7836e43b458a0c8871a71799835af41e3f5cf0e9dd923557041005032e9b`. V4 historical behavior retained. Prompt/task configuration is `benchmark-v2` with `evaluation-v3/checking-compact-v1/workspace-v2/workspace-check-v2/packet-citations-v2/role-bound-statements-v1/bounded-output-v1/v5-promise-mapping-v1`; baseline-v3 text/version unchanged. Actual sent prompt-plus-criteria hashes and returned-model identities are in immutable per-call receipts.

Exact-head CI [run 73](https://github.com/GalBlatman/Research-Development-Workbench/actions/runs/37394139197) passed foundation, browser and domain-policy, including mandatory PostgreSQL operator CLI smoke/full pytest, before the pilot or broader calls. Local checks: 698 passed, 36 service-dependent skips; ruff, formatting, mypy, API contract and foundation/publication checks passed. The affected/general regression pilot produced seven valid results among eight preserved attempts; its integrated baseline incomplete output was retained. Pilot results were reused only under exactly matching configuration and claims.

V5 unchanged: **YES**. V6 candidates: **none established**. Rubric/code/prompts/runtime/handoff are frozen for this executed partial candidate. **A final evaluator freeze for Step 14 is NOT established**, because Step 13 is incomplete. Validation and held-out packages remain untouched. This report's later documentation commit does not rewrite any executed commit, prompt receipt or runtime record. No main merge.

Handoff SHA-256 identities:

- benchmark-completed-development.json: `554ef5d7210d3ce0f2be20cfa15afb792ee21f75ee2ecb373410363f4d4311b9`.
- benchmark-early-development.json: `8a3c6fc8b12ada7c0d37710c39f9831e2472b7cdc9db312ef9b24a9b09198bf5`.
- benchmark-proposal-development.json: `94359b97e6031ce76aa1d315b25adab605745549a76a2d3db2e6164e8dc13ce6`.
- handoff-manifest.json: `a5177e93099135e6ac0d2cdf695aae8f667b7c4548b2f8fded76d5f46316701d`.
- development-admin-sidecar.json: `25389eff72ffc04b920af309547475e9a1f8c59a64196bcbbee9848147d59ce8`.

Canonical package/split identities:

- builder-splits-completed-v2-development-subset-v1: canonical `0d0b6264919761d3839452086387b0fb1682e3f97e12048f50885d717c0538a5`, split `daa054ba096fe548061396c8a8a777c28d5b20f468135344fd34ae942e175ffd`.
- builder-splits-early-v1-development-subset-v1: canonical `bd05959b3223b006412cc74bc6bec83b3f6432abec3393df03d22e3a0af2bded`, split `c265b996fcb8ac3db8cd7c81b2e04158cce0be24dd83572de968c73ddde362a8`.
- builder-splits-proposal-v1-development-subset-v1: canonical `973674adfe64b27b0340f2791e9d17fdbfe9b628706fa3e0f93058a831818100`, split `b6a13c57c66fcdb3efc76bc34241fd68f01874068c227e894bc9af4134e6e778`.

Prompt file SHA-256 identities:

- baseline-v3.md: `456091ff13dc3a90464a117103a85c14f6b92bc1018ad1c91d709e1c95df11fb`.
- interpretation-v1.md: `933740de1aa960ef393048c32a5e2072cdb0db638d224797bc3779ef191e6293`.
- evaluation-v3.md: `a8e9cc1415becf3bafd31524a49be00b919706b471cbb9db55819b4646d3edab`.
- checking-v4.md: `2868127095d0759ecef688d7298c306a493054401f41c03bd6e52cfe07934b06`.
- checking-compact-v1.md: `f32ce4a52283008d4138c5a9d8609b3f7d868f3ca21bb176c19a9668a722fba9`.
- workspace-v2.md: `b10771338d1fcb718921214e316d832ce29051e6bc8ada810265179ea8063b6c`.
- workspace-check-v2.md: `de433456f7a928e14d97b2a48ff231ecbd0758a75ffc2d77b5b229c099fd5dae`.
- criteria-v1.json: `6b91bae11e2573c072656b6b6d5c52a264eb74bc21731b81d684e2ed6727992c`.
- route-questions-v1.json: `af85eb0f081b831341c927325c1f1616b9d1511b7a3b301058e5dbb38f6c39f4`.
- route-questions-v2.json: `8ff2a9875cbcf5d9184efa406b486c774c80bc4a2e5e914893580bea8cc05ad1`.

Private immutable blocker snapshots are `blocked-freeze.json`, `blocked-analysis.json` and `blocked-supplement.json` under the existing candidate-v8 administrator archive outside Git. The freeze contains per-artifact hashes, original configurations, exact CI evidence, cases, split/variant identities, receipts and detailed strata. Original attempts remain unchanged.

## Usage and latency

| Current candidate receipt ledger | Workbench | Baseline |
| --- | ---: | ---: |
| Recorded calls | 803 | 320 |
| Calls without complete reported usage | 4 | 3 |
| Known input tokens | 12,611,228 | 4,851,807 |
| Known output tokens | 2,276,775 | 1,226,143 |
| Known estimated cost | $51.459699 | $22.3381958 |
| Median attempt duration | 53.625 seconds | 28.610 seconds |
| p95 attempt duration | 82.906 seconds | 55.437 seconds |
| Summed attempt durations | 20,870.736 seconds | 10,980.076 seconds |

Current candidate: 1,123 recorded calls, 17,463,035 known input and 3,502,918 known output tokens; **$73.7978948 known receipt-level estimated cost**. Seven calls lack complete usage, including four rate-limit responses, two uncertain transport failures and one transient provider-error retry. This is not an actual billing total. Receipt-level sums include known calls inside partially unknown runs; whole-run-only aggregates omit those partial known amounts and are lower ($73.6381316).

Across all preserved candidate/pilot archives, deduplicated by immutable run identity: 941 terminal attempts, 1,537 recorded calls, 23,405,089 known input and 4,743,895 known output tokens, **$99.5785001 known estimated cost**. Nine calls lack complete usage. Two additional historical interrupted reservations have unknown call counts and usage; totals remain unknown. No historical success is counted as valid under the current configuration.

Current candidate observation window, including the serial pilot: 2026-10-06T00:32:03.883919+00:00 to 2026-10-06T05:51:35.290730+00:00, approximately 5.33 hours. This is an archive-derived wall-clock window including pauses; summed concurrent attempt durations are not wall-clock. Price estimates use the pinned local rate card, not claimed provider invoices.

## Continuation boundary

Resolve provider HTTP 429 availability before resuming. No authorization increase is needed. Preserve the same executed candidate identity in a clean checkout at `80f141778c64089a914a9cc40b977bd8cf0859f3` and the existing output archive, exact preflight/CI gate and budgets; inspect claim accounting and resume only pending mode/cases. Do not turn a documentation commit into a new evaluator identity or rerun completed cases just to improve results. Historical uncertain attempts/reservations and terminal current failures remain preserved. Any justified general behavior change requires a new checked frozen candidate and bounded DEVELOPMENT regression, never rewritten history.

Step 14/16 frozen blind validation ready: **NO**. Step 14 not started. Step 13 completion requires the remaining 180 mode/case states, final fair scientific/error analysis and a final reviewed freeze.
