# Step 14 frozen blind validation report

STATUS: COMPLETE — all 300 mode/case states across 150 cases and 15 papers accounted for; failures retained.

This public summary records the owner-supplied completed Step-14 results. It does not publish private runtime artifacts, benchmark packets, gold or administrator metadata.

## Core result

A generalizing Workbench advantage is not established.

| Matched withholding/state | Workbench | Baseline | Difference |
| --- | ---: | ---: | ---: |
| Step-13 DEVELOPMENT | 28.95% | 24.64% | +4.31 percentage points |
| Step-14 VALIDATION | 31.11% | 24.44% | +6.67 percentage points |

The VALIDATION difference has a descriptive 95% interval of [-10.00 pp, +23.33 pp]. The withholding/state difference repeated in the same positive direction as DEVELOPMENT but remained too uncertain to establish a general advantage. No clear scientific advantage was established on unseen validation papers.

## Output availability and resources

| Measure | Workbench | Baseline |
| --- | ---: | ---: |
| Cases accounted | 150 | 150 |
| Valid outputs | 112 | 119 |
| Failed outputs | 38 | 31 |
| Recorded provider calls | 315 | 150 |
| Known input tokens | 4,719,446 | 2,137,408 |
| Known output tokens | 842,004 | 531,400 |
| Known estimated cost USD | 19.329161 | 9.955436 |
| Median attempt latency seconds | 50.289 | 27.641 |
| p95 attempt latency seconds | 87.750 | 60.000 |

Valid-output rate: Workbench 74.67%; Baseline 79.33%. Jointly valid case pairs: 104.

Failure types:

- BASELINE: INCOMPLETE_OUTPUT 31.
- WORKBENCH: INCOMPLETE_OUTPUT 37.
- WORKBENCH: INCOMPLETE_CHECK 1.

Workbench was less reliable on valid-output availability. Workbench was about twice as expensive. Workbench was substantially slower. Costs are known estimates, rather than a claim about provider invoices.

## Frozen scientific metrics

| Metric | Workbench | Baseline |
| --- | --- | --- |
| detection | 6/6; 100% paper macro | 3/3; 100% paper macro |
| invariance | 0/36; 0% paper macro | 0/28; 0% paper macro |
| withholding | 23/54; 38.89% paper macro | 24/58; 31.11% paper macro |
| state | 23/54; 38.89% paper macro | 24/58; 31.11% paper macro |
| restoration | unavailable | unavailable |
| direction | unavailable | unavailable |
| attribution | 413/413; 100% paper macro | 359/359; 100% paper macro |
| action relevance | unavailable | unavailable |

## Matched comparison

| Metric | Workbench paper macro | Baseline paper macro | Difference [95% interval] | Cases / features / papers |
| --- | ---: | ---: | --- | ---: |
| detection | 100.00% | 100.00% | +0.00 pp [+0.00, +0.00] | 1 / 1 / 1 |
| invariance | 0.00% | 0.00% | +0.00 pp [+0.00, +0.00] | 6 / 12 / 4 |
| withholding | 31.11% | 24.44% | +6.67 pp [-10.00, +23.33] | 33 / 42 / 15 |
| state | 31.11% | 24.44% | +6.67 pp [-10.00, +23.33] | 33 / 42 / 15 |
| restoration | unavailable | unavailable | unavailable | 0 / 0 / 0 |
| direction | unavailable | unavailable | unavailable | 0 / 0 / 0 |
| attribution | 100.00% | 100.00% | +0.00 pp [+0.00, +0.00] | 51 / 57 / 15 |
| action relevance | unavailable | unavailable | unavailable | 0 / 0 / 0 |

Exact-wording invariance/restoration metrics are not semantic-equivalence measures. Attribution measures authorized-anchor integrity, not truth or entailment. Direction and action relevance were unavailable under the frozen benchmark.

## Frozen evaluator and execution boundaries

Frozen evaluator: `80f141778c64089a914a9cc40b977bd8cf0859f3`.

Provider/model: `gpt-6-sol` through the OpenAI Responses API. The frozen evaluator's [baseline-v3 prompt](https://github.com/GalBlatman/Research-Development-Workbench/blob/80f141778c64089a914a9cc40b977bd8cf0859f3/backend/prompts/baseline-v3.md) and [rubric V5](https://github.com/GalBlatman/Research-Development-Workbench/blob/80f141778c64089a914a9cc40b977bd8cf0859f3/policies/rubric-v5.md) remain pinned. The [Step-13 calibration report](STEP-13-calibration-report.md) records the DEVELOPMENT comparison and evaluator freeze.

- No tuning occurred during validation.
- No selective replay occurred.
- DEVELOPMENT execution during Step 14: 0.
- HELD_OUT execution: 0.
- Step 15 was not started.
