# RDW-007 benchmark harness

This is an implementation harness, not a new rubric or calibration result. Only original synthetic fixtures are included. No provider calls, paper downloads, corpus construction or RDW-008 work are required.

## Contracts and storage

`domain/benchmark.py` defines versioned projects, gold features, source packages, variants, frozen splits, explicit expectations, observations, separate metrics, configurations and immutable run records. Feature names identify administrator annotations; code never determines scientific feature presence by keywords. Source anchors on gold records refer to source-package block IDs; evaluator anchors are created by the existing source service after admission.

`benchmarks/store.py` is an administrator capability. Its JSON artifacts are created exclusively and never overwritten. `benchmarks/variants.py` may read gold and mutation instructions. All sibling variants retain the underlying project's split; frozen manifests bind project content, including the source package, to that assignment. Imports with changed content or split are rejected. Cache keys bind variant, frozen split and complete evaluator configuration. Reference runs must match underlying project, split, manifest and evaluator configuration.

## Blindness boundary

Only `BlindPacket` crosses into `BlindEvaluator`: neutral packet hash, route, stage, and admitted text/roles. It carries no benchmark ID, split, gold, expectations, feature map, mutation label, hidden block ID, sibling identifier or administrator-store handle. Each execution gets a separate existing Workbench repository and original-file store with just that packet. Model adapters receive ordinary scoped ContextPackets; they have no administrator capability, retrieval tool or file path. Normal repository interfaces deny hidden/gold/sibling identifiers. Evaluator exports contain only their admitted project and sources. Administrator reports must never be substituted for evaluator exports.

This is capability separation through normal application interfaces; it does not claim an operating-system sandbox against arbitrary malicious Python code. Administrator runtime directories must remain outside the publication repository. The fake-only CLI enforces that boundary.

Administrator feature ownership must identify every block containing the feature, including repetitions. Shared blocks cause shared observability loss, recorded in the visibility map. Degradation marks the original gold component unobservable even though its weaker replacement is present. The constructor removes all feature-owned blocks, not just a single match. It does not semantically certify an administrator's decomposition. Identifying metadata-only blocks are excluded by default; explicitly supplied identifying strings are removed from admitted text. Explicit permission can retain metadata. An administrator may supply substantively equivalent replacements for neutral paraphrase/anonymization; code cannot certify equivalence.

## Variants

Intact blind and metadata blinding admit the permitted full packet. Single/multiple hides remove named feature blocks. Cumulative reveal has an explicit ordered sequence and count; linked stages must progress monotonically. Controlled degradation requires explicit replacement text owned by the affected feature. Provenance stays administrative. Restoration must link to a prior hidden/degraded/reveal variant of the same project/split and name its affected features; it restores the original component. No automatic mutation generator or exhaustive subset search exists. Mechanism/prediction ablations require EXPLAIN.

## Execution and comparator

Argument assesses dimensions 4â€“5, Study 8â€“10, Literature 2â€“3, and Alternatives 6 using the existing server targeted assessment/checking boundary. Full mode interprets the admitted packet, retains the proposed interpretation as uninspected, then runs the actual full Workbench evaluation/check/policy workflow. No generated suggestion becomes source evidence.

Baseline mode uses the same packet, provider/model parameters, applicable rubric and CandidateReview schema in one careful evaluation prompt (`baseline-v1`). It has no interpretation/checker pipeline. Its judgments remain proposed; no fake support confirmation is added merely to manufacture a baseline policy score. Workbench policy results come only from the existing deterministic engine. The comparator reports separate judgments, verification states, outputs and costs. Differences in verification reflect the workflow, not a claim that the baseline's science is wrong.

All route-specific questions are copied exactly from rubric v4 section 2.2 into `route-questions-v1.json`. Applicable ESTABLISH/TEST evaluation and checking criteria receive only their column. EXPLAIN criteria are unchanged. These questions are qualitative and are never summed.

## Expectations, annotations and metrics

Expectations are explicit behavior contracts: detect, downgrade, withhold, unresolved, not inspected, unchanged, restore or refuse inference. They identify affected and invariant judgments, acceptable/forbidden states, optional direction, optional reference variant and optional action target. Hidden gold text is never automatically rewarded as a correct reconstruction. A withheld/null judgment can be the intended success.

`compare` reports independent detection, invariance, withholding, restoration, direction, state, source authorization and action metrics with numerators and denominators. An unavailable comparison has denominator zero, not a fabricated pass. Restoration compares the restored judgment with an explicit intact reference; direction compares numeric judgments only when a direction was supplied. State requirements and withholding jointly distinguish uncertainty from confident invention. Source attribution measures whether listed anchors are admitted; it does not assert semantic entailment. The existing checker separately preserves its limited support dispositions.

Action relevance and recognition can use explicit administrator annotations in `Observation.action_targets`, `recognition_claim` and `action_annotation`. No keyword matching resolves those scientific judgments. To annotate, retain the immutable original run, create an annotated observation with a stated reason, compute a separate result and save it as a new administrator artifact using `AdminStore.write`. Do not overwrite original observations. Content/identity diagnostics are literal exact-match flags only. `equivalent_diagnostic` records judgment differences across administrator-certified equivalent packets. Recognition or a changed answer is not proof of contamination or plagiarism.

`aggregate` reports case counts and nested per-paper, per-mode metrics. Repeated variants remain one paper. There is no composite quality score or journal-acceptance gold target. The synthetic fake fixtures exercise contracts, not sensitivity of scientific reasoning.

## Reproducibility, budgets and resume

Each run records project/package version/hash, variant version/hash, packet hash, frozen split version/hash, expectations hash, reference run IDs, commit and backend source-tree hash, rubric/manifest/implementation identity, prompt/task hashes, provider/model parameters, component/mode, budgets, timestamp, duration, outputs, deterministic policy where applicable, status and usage receipt. Only enumerated non-secret provider parameters may be stored. Provider-reported token counts and dated price inputs support explicitly estimated costs (not a billing invoice). Missing usage stays null. Fake verification is not counted as a paid call.

`Runner.batch` orders cases deterministically, bounds concurrency to 1â€“4, and reserves conservative per-run call/token/cost budgets. Immutable batch slots preserve the ceiling across resumptions and concurrent controllers. Unknown charges and failures are not refunded. Completed, failed and interrupted run claims all prevent implicit replay; an explicit rerun uses a fresh run ID, and batch reruns require a new batch identity. A reservation with no terminal result means interrupted/uncertain execution; inspect it before explicitly authorizing another attempt. Stop prevents unstarted work. Failures are stored separately and do not stop unrelated valid cases. Progress reports per-case status, and results return in deterministic order. A new budget/configuration identifies a new batch; existing global run claims still prevent duplicates.

Use `Runner.execute(..., references={variant_id: successful_run})` for scoped paired metrics, or supply reference runs to a later batch. Missing references remain unmeasured. Paid execution uses the existing bounded provider ledger; runtime limits must fit the recorded run budget. A transient provider error is a visible failed run, not a scientific defect.

## Synthetic operation and later corpus interface

From `backend`, run `uv run --locked python -m benchmarks --output <private-runtime-directory> --mode WORKBENCH --component FULL --concurrency 2`. The command only uses the fake provider and writes administrator artifacts outside this repository. Repeating it skips existing reservations. BASELINE selects the one-call comparator. Aggregate output describes newly executed cases; stored immutable runs remain available through `AdminStore.read` for cumulative reporting.

Later authorized corpus construction supplies validated BenchmarkProjects/SourcePackages, explicit gold block mappings, split assignments, mutations and expectations through these contracts. Freeze the manifest before importing. All variants of one paper stay in one split. No real papers, fifty-paper set, calibrated rubric, publication outcomes or provider-spending command are included in RDW-007. Mocked Responses tests exercise the actual OpenAI adapter and strict output boundary without network calls.

## GATE-3 repair contract

The active policy is rubric v5; historical v4 records keep their frozen policy identity and results. External administrator handoff, permanent split/package identities, frozen expectation artifacts and validation/import commands are specified in [benchmark-package-v1](benchmark-package-v1.md). Paired order is canonical source tuple order. Degradation and restoration preserve affected positions. Scientific changes and verification-only changes are reported separately; restoration requires intact and actually degraded references. Baseline-v2 shares the server validity constraints while retaining its single-pass architecture. Orphan reservations and invalid cases remain visible without automatic paid replay. No Step-12 corpus is included.
