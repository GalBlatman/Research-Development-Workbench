Repair the remaining findings from the second independent GATE-3 rerun.

REPOSITORY

C:\Users\galbl\src\Research-Development-Workbench

CURRENT ROADMAP STEP

11/16 — GATE-3

Do not create a new roadmap step, phase, sub-stage, or fractional step.

Do NOT:
- start Step 12;
- construct the 50-paper corpus;
- calibrate the evaluator;
- modify rubric v5;
- modify historical rubric v4;
- modify the product specification;
- use real/private research papers.

AUDITED COMMIT

ec20bc7d5d3fe744f2789601441e6a19aec68bc0

SECOND GATE-3 RERUN RESULT

FAIL

All original 25 GATE-3 probes and all 38 prior-rerun adversarial probes passed.

Remaining findings:

BLOCKERS
- G3-SECOND-B1
- G3-SECOND-B2
- G3-SECOND-B3

IMPORTANT NONBLOCKER
- G3-SECOND-N1

Rubric questions:
NONE

Resolve all four findings and preserve every previously resolved requirement.

READ FIRST

1. AGENTS.md
2. active rubric v5
3. historical rubric v4
4. product specification
5. architecture
6. frozen roadmap
7. original GATE-3 audit
8. first repair record
9. first rerun audit
10. second repair record
11. second rerun audit
12. benchmark-package-v1 schema/docs
13. benchmark metrics/evaluator code
14. relevant permanent tests

==================================================
1. G3-SECOND-B1
EQUIVALENT ANONYMIZATION MUST NOT HIDE THE FEATURE
==================================================

CURRENT FAILURE

INTACT_BLIND and METADATA_BLINDING may use an administrator-certified
substantively equivalent replacement for anonymization/paraphrase.

The evaluator packet correctly contains the replacement content, but feature
visibility is calculated as false because the implementation currently excludes
all replacement block IDs from visibility.

This is wrong.

A scientifically equivalent anonymizing/paraphrasing replacement is still
VISIBLE evidence for that feature.

This matters directly for Step 12 because the real corpus will be decomposed and
paraphrased rather than exposing original paper text.

REQUIRED MODEL

Explicitly distinguish at least:

A. EQUIVALENT_REPLACEMENT
   Purpose:
   - anonymization;
   - neutral paraphrase;
   - identifier removal;
   - surface-language substitution preserving scientific content.

   Effect:
   - feature remains VISIBLE;
   - observability remains true;
   - scientific state should be invariant;
   - no degradation credit;
   - no hidden-content label.

B. CONTROLLED_DEGRADATION
   Purpose:
   - scientifically weaken or alter the target feature.

   Effect:
   - original target content is replaced;
   - target remains observable as the degraded version where appropriate;
   - benchmark knows it is degraded;
   - evaluator does NOT know mutation metadata.

C. HIDE_FEATURE / HIDE_MULTIPLE
   Purpose:
   - remove the target feature.

   Effect:
   - target visibility false.

Do not infer replacement semantics from "has replacement block".
Use an explicit transformation semantic/type already present in the package
model, or add the smallest typed distinction needed.

INTACT_BLIND and METADATA_BLINDING with certified equivalent paraphrase must
retain feature visibility.

This is a critical Step-12 behavior because the planned 50-paper corpus will use
paraphrased decompositions.

TESTS

Add permanent regressions proving:

1. intact original feature -> visible;
2. intact equivalent paraphrase -> visible;
3. metadata-blinded equivalent paraphrase -> visible;
4. equivalent anonymization does not change observability expectation;
5. controlled degradation remains distinguishable from equivalent paraphrase;
6. hidden feature remains hidden;
7. restoration using an equivalent anonymized intact reference validates
   correctly.

==================================================
2. G3-SECOND-B2
REPLACEMENT BLOCK IDENTITY COLLISIONS
==================================================

CURRENT FAILURE

A controlled degradation can assign its replacement the block ID of an
untouched block.

Example:
- measurement block is being degraded;
- replacement is assigned the question block's ID;
- package validation accepts it;
- evaluator packet contains inconsistent scientific ownership;
- unrelated feature visibility becomes false.

This must be impossible before freezing/import.

REQUIRED BEHAVIOR

Replacement block identity must be structurally safe.

For every mutation/replacement:

- replacement block ID must not collide with any untouched block ID;
- replacement block ID must not collide with another replacement unless the
  schema explicitly defines them as the same logical replacement;
- replacement must declare the target block/feature it replaces;
- target ownership must match transformation ownership;
- unrelated block IDs and ownership remain unchanged;
- canonical reconstruction must preserve unrelated feature visibility;
- duplicate scientific identity cannot be created through ID reuse.

VALIDATION

Reject collisions at benchmark-package validation before registration.

Also validate again at variant construction/runtime as defense in depth.

Do not rely on generated canonical output to "fix" a malformed package.

TESTS

Add regressions:

1. replacement ID equals untouched question ID -> reject;
2. replacement ID equals unrelated literature block ID -> reject;
3. two replacements use same ID -> reject unless explicitly valid by schema;
4. legitimate new replacement ID -> accept;
5. unrelated question remains visible after measurement degradation;
6. unrelated feature observability remains identical between intact/degraded
   pair.

==================================================
3. G3-SECOND-B3
BENCHMARK OBSERVATIONS MUST PRESERVE ACTUAL CHECKING DISPOSITIONS
==================================================

CURRENT FAILURE

A normal Workbench run through the actual adapter/checking boundary can produce
explicit checking dispositions such as:

- SUPPORTED
- UNRESOLVED
- NEEDS_REVISION

But benchmark evaluator observe() currently translates statements as:

state = proposed
verification = unresolved

regardless of what the checker actually returned.

Therefore the benchmark metrics are not measuring the behavior of the actual
Workbench.

This especially corrupts:
- withholding;
- verification-change;
- supported/needs-revision distinctions.

REQUIRED BEHAVIOR

Create a typed translation from actual checked scientific statements into
benchmark observations.

For every observed statement/judgment:

preserve separately:

- scientific content/value/state;
- proposal/adoption state where applicable;
- checker verification disposition;
- evidence/support state;
- source/anchor attribution where applicable.

Map checker dispositions explicitly.

At minimum preserve:

SUPPORTED
UNRESOLVED
NEEDS_REVISION

plus any existing valid dispositions such as:
- withdrawn;
- contradicted;
- not inspected;
- qualified;
- confirmed;
or their canonical equivalents.

Do not collapse them all to PROPOSED/UNRESOLVED.

METRIC RULE

Keep scientific-state change distinct from verification/disposition change.

Examples:

- same scientific assertion, verification changes UNRESOLVED -> SUPPORTED:
  record a verification change, not necessarily a scientific-value change.

- assertion changes because checker says NEEDS_REVISION:
  preserve both the modified scientific output and the checking disposition.

- correct UNRESOLVED checking must be eligible for withholding credit when the
  benchmark expectation calls for withholding.

- supported assertion must not be scored as unresolved.

END-TO-END TESTS

Use the same actual OpenAI adapter boundary with mocked transport used in the
audit.

At minimum:

1. checker returns UNRESOLVED -> observation preserves UNRESOLVED;
2. checker returns SUPPORTED -> observation preserves SUPPORTED;
3. checker returns NEEDS_REVISION -> observation preserves NEEDS_REVISION;
4. unresolved expected withholding -> receives correct metric credit;
5. supported output does not receive withholding credit;
6. verification-only change is reported separately from scientific change;
7. source/statement identity survives translation;
8. baseline behavior remains fairly comparable without being forced to imitate
   Workbench-internal checking machinery.

==================================================
4. G3-SECOND-N1
NEXT ACTIONS WORKSPACE PLACEHOLDERS
==================================================

CURRENT FAILURE

The standalone/generated Next Actions workspace has a separate validation path
from DiagnosticAction.

It still accepts:

- "Do more research."
- "Do more research!"
- "TBD."

when other required fields are filled with equally mechanical placeholders.

The earlier placeholder repair covered one contract but not this workspace.

REQUIRED BEHAVIOR

Apply the same mechanical placeholder normalization and completeness semantics
to MODEL-GENERATED Next Actions workspace proposals.

For generated action fields:

- trim whitespace;
- normalize case;
- normalize terminal punctuation for placeholder detection;
- reject structural placeholders such as:
  TBD
  TODO
  UNKNOWN
  N/A used as filler
  equivalent empty placeholders;
- reject generic task text that carries no usable action when paired with
  placeholder diagnostic fields.

Required generated action content remains:

- issue/judgment to change;
- concrete task;
- required evidence/input;
- expected deliverable;
- outcome/decision branch.

Do NOT create a broad scientific keyword heuristic.

Do NOT reject valid tasks simply because they contain words like "research",
"review", or "analyze".

Manual user-authored partial notes may remain looser if the product spec already
allows them.

TESTS

Add:

1. "Do more research." + TBD fields -> reject;
2. "Do more research!" + "TBD." -> reject;
3. punctuation/case/whitespace variants -> reject;
4. complete concrete generated action -> accept;
5. partial manual note -> preserve according to existing user-note rules.

==================================================
5. PRESERVE ALL PRIOR REPAIRS
==================================================

Do not regress:

- rubric v5 readiness mapping;
- historical v4 behavior;
- benchmark stable order/position;
- split integrity;
- package-v1 external handoff;
- gold/evaluator separation;
- restoration semantics;
- canonical withholding states;
- import provenance sanitation;
- resources/staleness protection;
- nested export sanitation;
- malformed-schema health;
- provider event-loop offload;
- checker scientific discipline;
- one accepted head;
- field-level provenance;
- provider usage durability;
- baseline-v2 fairness;
- interrupted batch visibility;
- review reproducibility.

==================================================
6. STEP-12 DESIGN ASSUMPTION
==================================================

Preserve this explicit future-corpus assumption:

The 50 published papers will NOT be given directly to the blind evaluator.

The non-blind corpus builder will:

1. read the original paper;
2. decompose it into research components relevant to rubric/workspaces;
3. privately preserve source evidence/anchors for the gold decomposition;
4. paraphrase scientific content;
5. remove paper identifiers;
6. create idea/proposal/completed-study representations;
7. create hidden, degraded, restored and combined variants.

Therefore:

Equivalent scientific paraphrase MUST remain observable.

A benchmark must distinguish:

- equivalent paraphrase/anonymization;
- hiding;
- scientific degradation.

Do not design the harness around verbatim paper text.

==================================================
7. TEST / ACCEPTANCE
==================================================

Before completion prove:

EQUIVALENT ANONYMIZATION
1. intact paraphrased feature remains visible;
2. metadata-blinded paraphrased feature remains visible;
3. equivalent paraphrase does not count as degradation;
4. restoration may use valid equivalent anonymized intact reference.

REPLACEMENT IDENTITY
5. replacement/untouched collision rejected;
6. replacement/replacement collision rejected where invalid;
7. valid replacement accepted;
8. unrelated feature visibility preserved.

CHECKING OBSERVATIONS
9. UNRESOLVED disposition survives Workbench -> observation;
10. SUPPORTED survives;
11. NEEDS_REVISION survives;
12. correct unresolved withholding metric = success where expected;
13. supported output does not receive withholding credit;
14. scientific versus verification changes remain distinct.

NEXT ACTIONS
15. punctuation placeholder generated action rejected;
16. complete generated action accepted;
17. manual partial note behavior preserved.

REGRESSION
18. all 16 v5 golden cases pass;
19. all benchmark/package tests pass;
20. both 27-case fake Workbench/baseline modes pass;
21. all browser e2e pass;
22. full backend suite passes;
23. PostgreSQL CI passes;
24. lint/type/contracts/build pass;
25. publication guard passes;
26. rubric v5 unchanged;
27. rubric v4 unchanged;
28. product specification unchanged;
29. roadmap remains 16 steps;
30. no private/source papers or secrets tracked.

==================================================
8. WORKFLOW
==================================================

1. Verify clean synchronized main at:
   ec20bc7d5d3fe744f2789601441e6a19aec68bc0

2. Create GATE-3 repair branch.

3. Record the second rerun findings if not already stored.

4. Fix G3-SECOND-B1.

5. Fix G3-SECOND-B2.

6. Fix G3-SECOND-B3.

7. Fix G3-SECOND-N1.

8. Run focused reproductions.

9. Run complete backend suite.

10. Run benchmark/package tests.

11. Run both fake benchmark modes.

12. Run browser e2e.

13. Run mandatory PostgreSQL CI/parity.

14. Run type/lint/contracts/build checks.

15. Run publication/governing checks.

16. Commit and push.

17. Integrate to main only if all checks pass.

18. Push main.

19. STOP.

Do not start Step 12.

==================================================
FINAL RESPONSE
==================================================

STATUS: PASS | BLOCKED

ROADMAP STEP:
11/16 — GATE-3 repair

COMMIT:
<final integrated commit>

SECOND-RERUN BLOCKERS:
- G3-SECOND-B1: RESOLVED/UNRESOLVED
- G3-SECOND-B2: RESOLVED/UNRESOLVED
- G3-SECOND-B3: RESOLVED/UNRESOLVED

SECOND-RERUN NONBLOCKERS:
- G3-SECOND-N1: RESOLVED/UNRESOLVED

ANONYMIZATION:
- equivalent paraphrase remains visible: PASS/FAIL
- metadata blinding preserves visibility: PASS/FAIL
- degradation remains distinct: PASS/FAIL

VARIANT IDENTITY:
- replacement collisions rejected: PASS/FAIL
- unrelated visibility preserved: PASS/FAIL

BENCHMARK OBSERVATION:
- supported disposition preserved: PASS/FAIL
- unresolved disposition preserved: PASS/FAIL
- needs_revision disposition preserved: PASS/FAIL
- scientific vs verification changes separate: PASS/FAIL
- withholding metric end-to-end: PASS/FAIL

NEXT ACTIONS:
- punctuation placeholders rejected: PASS/FAIL
- complete generated actions accepted: PASS/FAIL
- manual notes preserved appropriately: PASS/FAIL

TESTS:
- backend passed: ...
- failed: ...
- v5 golden cases: X/16
- browser e2e: ...
- benchmark/package tests: ...
- fake Workbench benchmark: X/27
- fake baseline benchmark: X/27
- PostgreSQL CI: PASS/FAIL

GOVERNING FILES:
- rubric v5 unchanged: YES/NO
- rubric v4 unchanged: YES/NO
- product spec unchanged: YES/NO
- roadmap unchanged: YES/NO

PUBLICATION SAFETY:
- private/source papers tracked: YES/NO
- secrets tracked: YES/NO

REMOTE:
- main synced to origin: YES/NO

BLOCKERS:
- none
or
- ...

NEXT:
GATE-3 rerun ready: YES/NO

Do not start Step 12.
