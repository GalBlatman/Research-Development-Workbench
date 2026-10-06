# Step 13 DEVELOPMENT calibration report

STATUS: PASS — October 6, 2026. Roadmap: 13/16 — Calibration development set.

Step 13 completion criteria are met: all **440/440 DEVELOPMENT cases across 20/20 papers** have valid or documented failed/unavailable states in both modes, comparative/error analysis is recorded, and the executed evaluator is frozen. This is completion of calibration work, not a claim of scientific superiority or high evaluator accuracy. No quality pass threshold was added after observing results. Step 14 was not started.

## Coverage and preserved history

| Final accounting | Workbench | Baseline |
| --- | ---: | ---: |
| Cases accounted for | 440 | 440 |
| Current-configuration terminal attempts | 437 | 439 |
| Current valid outputs | 301 | 359 |
| Current failed outputs | 136 | 80 |
| Current attempt failure rate | 31.12% | 18.22% |
| Failures/unavailable states over all 440 cases | 139 (31.59%) | 81 (18.41%) |
| INCOMPLETE_OUTPUT | 134 | 78 |
| Historical current-candidate RATE_LIMIT failures | 2 | 0 |
| Current-candidate TRANSPORT_ERROR_UNCERTAIN | 0 | 2 |
| Older uncertain terminal records/reservations | 3 | 1 |

There are **876 current attempts, 660 valid outputs, 216 current failures, and 283 valid pairs**. Four older unavailable mode/case states retain their original configurations: two uncertain terminal attempts and two interrupted Workbench reservations. They were never relabeled as valid under this candidate or automatically replayed. Thus 878 actual terminal records plus two documented reservations account for all 880 mode/case states. Zero pending states and zero new unfinished reservations remain.

The 400 completed-study cases have 261 valid Workbench and 319 valid baseline outputs; remaining cases have documented failed/unavailable states. All 20 early-idea and all 20 specified-proposal cases passed output validity in both modes. Validity does not verify scientific truth. Each of the 20 underlying papers has current-candidate evaluation records.

After the owner replenished API credit, the run resumed at the **same frozen evaluator commit and runtime** from a clean isolated checkout. It added exactly 180 pending attempts, 244 calls and $14.2634156 known estimated cost, with no new unknown-usage call. All 696 pre-resume terminal record hashes were verified unchanged. Two preserved rate-limit failures remain failures; no selective success-only replay occurred. The earlier blocker report is retained in [the historical blocker report](STEP-13-calibration-blocked-report.md) and Git history.

VALIDATION: **0/150 executed**, zero evaluator-result inspection. HELD_OUT: **0/75 executed**, zero evaluator-result inspection. No original papers or private builder source/history were accessed. No main merge.

## Routing, preflight and privacy

All five handoff SHA-256 identities, canonical package validation, public validate-only checks and exact 440-case/20-paper sidecar joins passed. Packages contain 400 completed, 20 early and 20 proposal cases, all DEVELOPMENT. Scheduled routing is exactly 253 TARGETED_COMPONENT and 187 FULL_WORKBENCH. Current Workbench attempts comprise 251 targeted and 186 integrated cases; its three older unavailable states account for the remaining two targeted/one integrated cases. Current baseline attempts comprise 252 targeted and 187 integrated cases; its older unavailable targeted state accounts for the remaining case. Actual current components match canonical routing. No targeted case substituted FULL; no integrated case was split into independent targeted evaluations.

The sidecar remains administrator-only. Journal, proximity, method/design and area labels remain in private administrator stratified analysis, excluded from evaluator prompts, blind packets and ordinary project context. Gold, expected judgments/states/directions, mutation labels, hidden content, administrator routing metadata, originals, locators, private exports and credentials remain excluded from provider requests and Git.

Provider: `https://api.openai.com/v1/responses`, configured `gpt-6-sol`, with strict returned-model checks. Privacy/runtime: store=false, foreground, background=false, no web/search/tools/uploads/files/vector stores; timeout 120 seconds, low reasoning, 6,000 output tokens per call, four calls and 500,000 tokens/$5 per run, one retry, concurrency two and four-paper batches. None of these controls increased. Paid payload/destination authorization remained in force.

## Scientific metrics and fair baseline

Derived server findings are excluded from fair scientific metrics. Each observed count below is an expectation/judgment numerator/denominator, followed by case macro and equal-weight paper macro rates and available case/paper counts. The denominator is restricted to available comparisons with valid output; failures and missing references are reported separately. Out-of-scope comparisons remain unavailable.

| Metric | Workbench | Baseline |
| --- | --- | --- |
| detection | 34/34; 100.00% case; 100.00% paper; 27 cases/13 papers | 33/33; 100.00% case; 100.00% paper; 27 cases/17 papers |
| invariance | 0/28; 0.00% case; 0.00% paper; 6 cases/4 papers | 0/33; 0.00% case; 0.00% paper; 7 cases/5 papers |
| withholding | 71/222; 29.75% case; 30.31% paper; 149 cases/20 papers | 102/309; 29.77% case; 31.82% paper; 187 cases/20 papers |
| state | 71/222; 29.75% case; 30.31% paper; 149 cases/20 papers | 102/309; 29.77% case; 31.82% paper; 187 cases/20 papers |
| restoration | 0/4; 0.00% case; 0.00% paper; 4 cases/4 papers | 0/6; 0.00% case; 0.00% paper; 6 cases/5 papers |
| direction | unavailable (0/0) | unavailable (0/0) |
| attribution | 1187/1187; 100.00% case; 100.00% paper; 271 cases/20 papers | 907/907; 100.00% case; 100.00% paper; 270 cases/20 papers |
| action | unavailable (0/0) | unavailable (0/0) |

The fairer matched analysis requires both modes valid and equal feature denominators. It averages available features within case, cases within paper, then papers. Paper-cluster bootstrap uses 5,000 draws, seed 13; repeated variants are nested rather than treated as independent observations. Intervals are descriptive DEVELOPMENT uncertainty, without multiplicity or availability-selection correction.

| Matched metric | Workbench paper macro | Baseline paper macro | Difference and descriptive 95% interval | Available cases/papers |
| --- | ---: | ---: | --- | ---: |
| detection | 100.00% | 100.00% | +0.00 pp [+0.00, +0.00] | 12/9 |
| invariance | 0.00% | 0.00% | +0.00 pp [+0.00, +0.00] | 4/4 |
| withholding | 28.95% | 24.64% | +4.31 pp [-2.21, +10.48] | 144/20 |
| state | 28.95% | 24.64% | +4.31 pp [-1.99, +10.38] | 144/20 |
| restoration | 0.00% | 0.00% | +0.00 pp [+0.00, +0.00] | 3/3 |
| direction | unavailable | unavailable | unavailable | 0/0 |
| attribution | 100.00% | 100.00% | +0.00 pp [+0.00, +0.00] | 102/20 |
| action | unavailable | unavailable | unavailable | 0/0 |

**Clear Workbench scientific advantages: none established.** Its matched withholding/state point estimate is +4.31 percentage points, with intervals spanning zero. Detection and anchor attribution tie on available comparisons. Baseline has better output availability, fewer calls, lower known cost and shorter attempt duration. The marginal paper rates differ in coverage and must not be read as a randomized comparison. The current selection and metric limits prevent broad accuracy claims.

Invariance/isolation and restoration include exact statement wording signatures; zero matching signatures do not establish semantic noninvariance or lack of recognition. Directional sensitivity has no available denominator after scope/reference constraints. Source attribution measures authorized-anchor integrity, not entailment or independent verification. Action relevance remains unavailable without independent semantic annotation; no keyword proxy or fabricated annotation was substituted. Failed/unavailable references remain unavailable, never fabricated comparison baselines.

The existing UNINSPECTED-BLOCK engine consequence is a separate product observation. Derived product findings are not a baseline scientific disadvantage, and none of the eight derived-product comparison denominators is available in this final snapshot. Model output remains proposed content; adoption never automatically verifies evidence.

Private final analysis retains overall and case/paper metrics, judgment families, nested variants, single/combined transformations and authorized strata. The private scientific-strata artifact contains 92 mode/stratum groups over component, execution scope, route, stage, journal, proximity, method/design and substantive area, with availability and paper macro rates. These overlapping groups are not independent tests, and their labels stay outside Git.

## Error analysis A–I

| Category | Conclusion |
| --- | --- |
| A — model recognition failure | Scoped scientific nonmatches remain in private analysis. They indicate calibration limitations; exact wording alone cannot establish a semantic recognition failure or separate model error from ambiguity/gold assumptions. |
| B — prompt/task-contract failure | 212 current incomplete outputs under unchanged bounds remain failures. Earlier general task, source-role, concise-output and promise-basis repairs were versioned and regression-tested; no gold-specific patch or selective truncation replay was used. |
| C — checker failure | Shared unmapped promise-basis validity was repaired before this candidate. Current strict source triples, roles, scope and supported-basis checks remain authoritative. No new current checker defect established. |
| D — routing failure | Exact canonical task audit passed. All 440 mode/case pairs are accounted for; older uncertain states retain original routing/configuration. |
| E — deterministic policy/engine | No new policy defect established. V5/V4 and scoring engine behavior remain unchanged. |
| F — benchmark/metric translation | General absent-judgment restoration, coherent withholding, reference identity, numerical scope and derived-product separation are implemented. The existing private scope audit identifies 195 comparison requests across 35 cases/20 papers, including 75 direct out-of-scope dimension targets; these remain unavailable rather than widened tasks or fabricated outcomes. Semantic-action and exact-prose limits remain explicit. |
| G — corpus/gold error | No corpus or gold correction. Approved handoff, splits and expectations unchanged; prohibited originals were not accessed to adjudicate them. |
| H — genuine ambiguity | Unresolved support, unavailable references and nonadjudicated semantic interpretations remain qualified/unavailable. No case-specific truth was invented. |
| I — possible recognition leakage | Frozen metadata-blinding equivalents have 19 available and one unavailable comparison per mode. No shared assessed numerical judgment is available in these equivalence pairs. Differences are robustness diagnostics, not proof of memorization; single draws confound metadata effects with stochastic generation. No explicit paraphrase cases exist in the frozen handoff, and no new paraphrase corpus or repeat-control experiment was added. |

Runtime/provider failures are outside A–I. Current-candidate two uncertain transport failures and two rate-limit terminal failures are preserved; the credit blocker resolved before the pending-only resume. Two older uncertain calls and two older unfinished reservations remain separate. Recognition diagnostics emitted no exact-match flags; that does not prove absence of leakage. Generic historical downstream errors retain diagnostic limits and were not rewritten as precise causes.

## General calibration changes and validation

General implemented changes within Step 13: exact baseline-v3 instructions/receipt identity; coherent withholding and absent-judgment restoration; specific integrity diagnostics and terminal failure receipts; V5 route input keys; exact admitted numerical/task scopes and scientific-basis fields; runtime numeric normalization/reference identity; interrupted-claim accounting; compact checking; concise bounded output; exact admitted citation triples and source-role schema branches; shared V5 promise-basis validity. None reads gold into evaluator requests or modifies case-specific scientific truth.

Both modes receive the same sanitized packet/provider/model/task and shared validity constraints. Baseline remains one direct baseline-v3 evaluation. Workbench retains ordinary integrated or canonical component assessment/checking. Compact checking simplifies the wire representation, expands back to actual references, and preserves ordinary checking; no core component was removed. No new service, major dependency, database, provider/model or frontend scoring was introduced. No rubric, routing or corpus correction occurred during the credit resume.

The current general-repair pilot preserved eight attempts, seven valid outputs and one incomplete baseline output, covering affected and unaffected targeted/integrated tasks. Its results were reused only with exact matching runtime/configuration/claims. All earlier attempts remain historical; prior successes are not counted as current-candidate valid results.

Exact executed-head [CI run 73](https://github.com/GalBlatman/Research-Development-Workbench/actions/runs/37394139197) passed foundation, browser and domain-policy, including mandatory PostgreSQL operator CLI smoke/full pytest, before any current-candidate provider calls. Local evaluator checks: 698 passed, 36 service-dependent skips; ruff, formatting, mypy, API contract and foundation/publication checks passed. The final documentation is separately reviewed and checked; its commit does not change the executed evaluator identity.

V5 unchanged: **YES**. Historical V4 behavior retained: **YES**. V6 candidates: **none established**. Main integration still requires human review.

## Frozen evaluator for later validation

- Evaluator configuration frozen: **YES**, with validity, reference and availability limitations recorded.
- Executed code commit frozen: **YES**, `80f141778c64089a914a9cc40b977bd8cf0859f3`; source tree `a96498bdfdf7fd726866414b70cdf402d6708f6871579de35572a02e445b0678`.
- Rubric frozen: **YES**, V5 canonical SHA-256 `d71a827c3ab1a0a74cbafe27a6907afaac11ae56b6568ab10f0d79d026166107`; policy manifest `6c9d7836e43b458a0c8871a71799835af41e3f5cf0e9dd923557041005032e9b`; implementation 5.0.0. V4 remains immutable.
- Prompts frozen: **YES**, task benchmark-v2; configuration `evaluation-v3/checking-compact-v1/workspace-v2/workspace-check-v2/packet-citations-v2/role-bound-statements-v1/bounded-output-v1/v5-promise-mapping-v1`; baseline-v3 unchanged. Actual augmented prompt/criteria hashes and returned models are retained per call.
- Runtime/provider/privacy/budgets frozen: **YES**, unchanged settings above.
- Package/manifest/splits frozen: **YES**, verified identities below; no cross-split execution.
- VALIDATION package untouched: **YES**. HELD_OUT package untouched: **YES**.

Immutable administrator artifacts outside Git include final-analysis.json, final-supplement.json, final-scientific-strata.json and authoritative final-freeze-v2.json. The final freeze binds configurations, exact CI, artifact hashes, package/split/variant identities and receipts. It verifies all 696 pre-resume terminal record hashes; original blocked snapshots and attempts remain intact. The initial administrative final-freeze inventory audit was superseded to correct Windows path separators/hashed filenames; no execution record, scientific output or receipt was changed. The clean isolated executed-code checkout remains available for the frozen candidate. Later task-documentation commits must not be substituted into existing run identities.

Handoff file SHA-256 identities:

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

## Calls, tokens, cost and latency

| Current candidate receipt ledger | Workbench | Baseline |
| --- | ---: | ---: |
| Recorded calls | 927 | 440 |
| Calls without complete reported usage | 4 | 3 |
| Known input tokens | 14,173,992 | 6,468,412 |
| Known output tokens | 2,576,702 | 1,628,496 |
| Known estimated cost | $58.2080257 | $29.8532847 |
| Median attempt duration | 51.110 seconds | 27.375 seconds |
| p95 attempt duration | 84.546 seconds | 58.609 seconds |
| Summed attempt durations | 24068.929 seconds | 15206.988 seconds |

Current candidate: **1367 recorded calls**, 20,642,404 known input and 4,205,198 known output tokens; **$88.0613104 known receipt-level estimated cost**. Seven calls lack complete usage (four rate-limit responses, two uncertain transport failures, one transient provider-error retry). Whole-run-only cost sums omit partial known calls and are lower; this report uses individual receipt ledgers.

Across all preserved candidate/pilot archives deduplicated by immutable run identity: **1121 terminal attempts, 1781 recorded calls**, 26,584,458 known input and 5,446,175 known output tokens; **$113.8419157 known estimated cost**. Nine calls lack complete usage, and two additional historical interrupted reservations have unknown calls/usage. Actual billing/total cost remains unknown; these are pinned local rate-card estimates, not provider invoices.

Workbench used 487 extra recorded calls, 7,705,580 extra known input tokens, 948,206 extra known output tokens and $28.3547410 extra known cost. Its median attempt is 23.735 seconds longer. These marginal resource totals differ slightly in attempted-case coverage; they do not imply scientific benefit.

Archive-derived wall-clock window including pilot, pauses and the external-credit gap: 2026-10-06T00:32:03.883919+00:00 to 2026-10-06T17:39:38.743319+00:00 (17.13 hours). Summed concurrent attempt durations are not wall-clock or active-session time.

## Blockers and next boundary

Current execution blockers: **none**. The former API-credit/rate-limit blocker is resolved, with failed attempts preserved. Scientific accuracy, availability and metric limitations above remain material owner-review findings.

Step 14/16 frozen blind validation technically ready: **YES**, using this frozen candidate and documented limitations, subject to explicit owner authorization/review. This does not certify strong scientific accuracy or authorize a new step. **Step 14 not started.** No VALIDATION/HELD_OUT execution, automatic rubric change or main integration occurred.
