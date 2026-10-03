# GATE-3 repair contract

Repair the Research Development Workbench findings from GATE-3.

REPOSITORY

C:\Users\galbl\src\Research-Development-Workbench

CURRENT ROADMAP STEP

11/16 — GATE-3

This is repair work required to pass the existing gate.

Do NOT:
- create a new roadmap step, phase, sub-stage, or "11.5";
- start Step 12;
- construct the 50-paper corpus;
- calibrate the evaluator;
- use real/private research papers.

AUDITED COMMIT

fbba2d7c2825bae9d2e118d0c6db2b7bc48f5ea7

GATE-3 RESULT

FAIL

There are:
- 4 blockers;
- 13 important nonblockers;
- 1 genuine rubric question.

Resolve ALL of them before the GATE-3 rerun.

READ FIRST

1. AGENTS.md
2. policies/Research_Idea_Rubric_v4.md or equivalent governing v4 path
3. docs/product-spec.md
4. docs/architecture.md
5. docs/roadmap.*
6. RDW-001 through RDW-008 task contracts
7. GATE-1 audit/resolutions
8. GATE-2 audit/resolutions
9. GATE-3 audit report
10. benchmark-harness documentation
11. private-pilot/operator documentation
12. current implementation/tests

==================================================
A. CREATE RUBRIC V5, SURGICALLY
==================================================

GATE-3 found one genuine policy ambiguity:

G3-R1:
For ESTABLISH and TEST, rubric v4 says route items are:
- ADEQUATE FOR STAGE
- DEVELOPMENT NEEDED
- BLOCKING
- NOT INSPECTED

and says they are not points and are not summed.

Section 8.5 then requires an "adequate completed route assessment" for
submission readiness but does not define how those qualitative statuses map to
readiness.

This cannot remain an undocumented implementation convention.

CREATE RUBRIC V5.

V5 must be V4 plus ONLY the following substantive clarification.

Do not alter:
- EXPLAIN formulas;
- weights;
- caps;
- numerical anchors;
- dimensions;
- three contribution routes;
- Discovery's status as a stage/process;
- study dimensions;
- premise rules;
- calibration philosophy;
- any other substantive rubric rule.

Add/clarify these semantics in the appropriate route-assessment/readiness
sections:

ROUTE ITEM STATUS SEMANTICS

ADEQUATE FOR STAGE:
The item is sufficient for the decision being considered at the current stage.

DEVELOPMENT NEEDED:
A meaningful improvement is warranted, but this item does not by itself defeat
the current-stage decision.

BLOCKING:
The problem prevents a positive decision at the requested stage until resolved
or until the claim/commitment is narrowed appropriately.

NOT INSPECTED:
The evaluator lacks the necessary material to judge the item. Withhold the
affected readiness judgment rather than treating the item as either adequate or
failed.

ESTABLISH / TEST SUBMISSION READINESS MAPPING

For the route-assessment component:

- if any REQUIRED route item is NOT INSPECTED:
  route readiness contribution = UNKNOWN;

- else if any required route item is BLOCKING:
  route readiness contribution = FALSE;

- else:
  the completed route assessment satisfies the route-assessment component of
  submission readiness, even if one or more items are DEVELOPMENT NEEDED.

Other §8.5 requirements still apply independently:
- dimensions 8 and 9 each >= 5 where applicable;
- delivered support for the central claim;
- honest contribution promise;
- no hard stop.

Do NOT count DEVELOPMENT NEEDED items.
Do NOT create a threshold such as "no more than N development-needed items."

If several weaknesses jointly make the project inadequate for the current
stage, the evaluator must identify the stage-defeating problem as BLOCKING and
explain why, rather than relying on an implicit count.

Record this as the explicit V5 clarification of V4 ambiguity G3-R1.

VERSIONING REQUIREMENTS

- Preserve v4 as an immutable historical rubric artifact.
- Add v5 as the new active rubric.
- Existing historical evaluations created under v4 must continue to render from
  their stored v4 PolicyResult and v4 hash/version.
- Do NOT silently reinterpret old v4 reviews under v5.
- New evaluations use v5.
- Benchmark/run metadata must continue to record exact rubric version/hash.
- Update governing baseline hashes/references to make v5 the active rubric.
- Update documentation/task references that say "current rubric v4" where they
  mean the active rubric.
- Do not rewrite historical audit records claiming that those audits used v5.

==================================================
B. G3-B1 — BENCHMARK VARIANT POSITION/ORDER INTEGRITY
==================================================

CURRENT FAILURE

Benchmark block IDs are hash-derived and evaluator presentation follows hash/
repository order rather than original source-package order.

Therefore intact and manipulated variants reshuffle unrelated content.

CONTROLLED_DEGRADATION also appends replacement content rather than replacing
the target in place.

This confounds the intended manipulation.

REQUIRED BEHAVIOR

- Define canonical source-package order explicitly.
- Blind evaluator packets preserve that canonical order.
- HIDE_FEATURE removes only the target block(s).
- HIDE_MULTIPLE removes only specified target blocks.
- CONTROLLED_DEGRADATION replaces target content IN THE SAME POSITION.
- CONTROLLED_RESTORATION restores content to the same canonical position.
- CUMULATIVE_REVEAL preserves stable relative ordering.
- Metadata stripping must not reorder scientific content.
- Block identity may be hashed, but hash order must never determine presentation.

Add tests proving that intact/manipulated paired packets have identical order and
roles except for explicitly manipulated blocks.

==================================================
C. G3-B2 — SPLIT CONTAMINATION / MANIFEST INTEGRITY
==================================================

CURRENT FAILURES

- a later manifest version can move a paper from DEVELOPMENT to HELD_OUT after
  development runs exist;
- identical package content can be registered under different benchmark IDs in
  different splits;
- relabelled variants can cross splits;
- Runner can execute from an unstored/unfrozen manifest.

REQUIRED BEHAVIOR

Create durable paper/package identity.

At minimum:

- bind underlying paper/project identity to a canonical content/package hash;
- bind variants to that underlying identity and manifest hash;
- all variants/siblings of one underlying paper remain in one split forever
  within the benchmark lineage;
- once variants or runs exist for a paper, a new manifest cannot reassign that
  paper to another split;
- duplicate underlying package content cannot be registered under a second
  paper ID in another split;
- package_id/content identity collisions must fail visibly;
- save_variant validates paper identity, package hash, split, and manifest;
- execution repeats those checks;
- Runner must load a stored, frozen manifest;
- an unstored/unfrozen manifest cannot execute;
- manifest versioning may add legitimate new papers but cannot launder an
  existing paper into a new split.

Add direct adversarial regressions for all reproduced GATE-3 cases.

==================================================
D. G3-B3 — FORMAL STEP-12 PACKAGE CONTRACT
==================================================

The separate corpus-builder project must not depend on Python constructors or
Workbench internals.

Publish a formal:

benchmark-package-v1

contract.

REQUIRED ARTIFACTS

Create a versioned machine-readable JSON Schema or equivalent exported schema
covering the corpus-builder handoff.

The contract must define at least:

- schema_version;
- benchmark/paper stable ID;
- canonical package/content hash;
- split assignment;
- route;
- stage;
- ordered source blocks;
- source anchors;
- gold feature decomposition;
- feature/block ownership;
- variant definitions;
- visible/hidden feature map;
- transformation type;
- controlled degradation specification;
- restoration reference;
- cumulative reveal ordering;
- benchmark expectations;
- expected affected judgments;
- expected invariant judgments;
- allowed states;
- forbidden states;
- expectation direction where defined;
- mutation provenance;
- hashes/versioning.

DOCUMENT THE VOCABULARIES

Document and validate:
- judgment keys such as rating:<dimension>, finding:<id>, route:<item>,
  statement:<id>, or the final canonical equivalents;
- route-item names;
- evidence/status states;
- expectation types;
- transformation types;
- restoration references.

CANONICAL HASHING

Document exactly how canonical hashes are calculated:
- serialization rules;
- field ordering/canonical JSON behavior;
- what is included/excluded;
- content hash versus artifact/version hash.

IMPORT / VALIDATE CLI

Add a corpus-package validation/import command suitable for use by a physically
separate private repository.

It must:

1. validate schema;
2. validate semantic references;
3. reject duplicate IDs/hashes;
4. reject anchors to nonexistent blocks;
5. reject gold features with no valid owned block/reference where one is
   required;
6. reject misspelled judgment/state vocabularies;
7. reject invalid restoration/degradation references;
8. validate split consistency;
9. validate all variant-parent relationships;
10. freeze project, gold, variants, expectations and split manifest as immutable
    admin artifacts;
11. report their hashes;
12. refuse mutation after freeze except by explicit new version under the split
    rules.

EXPECTATIONS MUST BE STORED

Do not store only expectations_hash.

Persist the frozen expectation artifact itself so:
- it exists before evaluator results;
- it cannot be rewritten after results are observed;
- runs bind to the exact expectation hash/version.

BLINDNESS

The evaluator-facing import/runtime boundary must still expose only the
sanitized BlindPacket.

Normal evaluator/model code must have no permission/API for:
- gold;
- expectation answers;
- hidden content;
- original full-paper repository;
- mutation rationale;
- sibling variants.

The Step-12 builder may know all of these.

==================================================
E. G3-B4 — CHECKER / ROUTE VERIFICATION DISCIPLINE
==================================================

CURRENT FAILURE

The earlier G2 repair constrained principal obstacle, but other checker-written
summary fields can introduce new unchecked scientific conclusions.

Route assessment items and applicability flags are also not consistently
checked.

REQUIRED BEHAVIOR

SERVER-OWNED FIELDS

- disclaimer must be server-owned;
- checker may not invent claims of independent verification/expert review.

SUMMARY MERGING

Preserve evaluator summary fields unless a checked disposition warrants change.

The checker may:
- confirm;
- qualify;
- narrow;
- withdraw

a checked claim.

A substantively new scientific allegation or recommendation introduced during
checking must:
- have its own explicit checking target/disposition before promotion;
or
- remain clearly unresolved/proposed and must not drive deterministic readiness
  or the settled principal review.

Merge evaluator and checker limitation lists; do not silently drop original
limitations.

ROUTE ITEMS

Create checking targets for applicable route items:
- route:<item>

and for decision-driving applicability flags such as:
- account_articulated;
- study_assessable;
- other equivalent flags used by policy.

Add a verification/disposition field.

The deterministic engine must treat an unverified route item needed for a
decision as NOT INSPECTED / UNKNOWN rather than as established adequacy or
failure.

Do not allow unchecked ESTABLISH/TEST route items to change submission
readiness.

Add adversarial regressions for:
- new unchecked next_action;
- new unchecked contribution claim;
- new unchecked disclaimer;
- limitation deletion;
- unchecked route item;
- unchecked applicability flag;
- confirmed/qualified/withdrawn legitimate existing statements.

==================================================
F. G3-N1 — SCOPED REVIEW STALENESS
==================================================

Scoped reviews must depend on:
- every snapshot document version actually inspected;
- every scientific workspace/dimension whose content overlaps the scoped
  judgment.

Examples:
- Brief novelty/interestingness judgments must stale when predecessor/literature
  evidence they relied on changes;
- mechanism-sensitive Brief judgments must stale when mechanism changes;
- Usefulness judgments stale when relevant source/research content changes.

Do not stale unrelated scopes.

Overview must:
- prefer/display the latest FULL review as the integrated review;
- clearly label scoped review target and stale/current state;
- not silently substitute a later narrow scoped check for the integrated review.

Add regressions.

==================================================
G. G3-N2 — SINGLE ACCEPTED HEAD / LINEAGE CONSISTENCY
==================================================

Prevent multiple accepted current heads within one logical record lineage.

Required:

- save/edit of accepted material must target the current accepted head;
- stale/superseded accepted head edits must conflict;
- accepting a proposal whose target has since changed must conflict or use the
  already-defined explicit rebase/adoption mechanism;
- editing a pending proposal must not create an unrelated current identity that
  escapes its lineage;
- editing rejected content must not silently convert semantic state in a way
  that makes it current;
- one logical lineage has one accepted current head.

Historical nodes remain immutable.

==================================================
H. G3-N3 — FIELD-LEVEL ORIGIN / WORDING-ONLY INTEGRITY
==================================================

Do not relabel an entire model-generated object as user-authored merely because
the user edits one field.

Required:

- preserve origin/provenance at field level where necessary;
- unchanged generated fields remain generated/model-origin;
- user-edited fields record the user's contribution;
- editing does not automatically raise evidence from NOT_INSPECTED to
  SPECIFIED_BUT_UNTESTED;
- acceptance/editing never means verification.

"WORDING ONLY" must be rejected if the change alters:
- source refs;
- anchors;
- evidence states;
- relationship choices;
- scientific keys;
- dependencies;
- route/stage;
- substantive claim meaning.

A wording-only classification must not bypass staleness.

==================================================
I. G3-N4 — IMPORT AUTHORITY ESCALATION / STORAGE REFERENCE LEAK
==================================================

Owner import must not trust self-consistent forged authority.

On import:

- generated/run/provider-bearing objects remain generated even if relabelled;
- document_extraction authority requires resolvable bundled source evidence;
- documented_or_verified requires resolvable bundled verification/source check;
- fabricated analysis_artifact_inspected flags cannot create verification;
- imported stored PolicyResult must match the preserved historical rubric/
  manifest identity and validation rules;
- if verification cannot be established safely, demote rather than strengthen;
- imported snapshots/reviews must carry explicit imported provenance;
- never upgrade accepted -> verified through import.

Exclude original_storage_reference and equivalent local storage/path fields from
all user exports, including nested historical snapshots.

Add forged-import regressions.

==================================================
J. G3-N5 — FABRICATED RESULTS + REVIEW NEXT ACTIONS
==================================================

Generated workspace proposals may not manufacture user-reported results.

Reject generated values such as:
- "completed (user-reported)"
- "demonstrated (user-reported)"
- invented coefficients/sample sizes/findings

unless they are grounded in an existing user-authored or admitted source field.

The model may propose:
- a result to inspect;
- a hypothetical branch;
- a needed analysis;

but must not represent it as observed.

REVIEW SUMMARY NEXT ACTION

Apply the same diagnostic completeness rules already applied to generated
Next Actions.

A published review next action must contain:
- concrete issue/judgment;
- concrete task;
- required input/evidence;
- expected deliverable;
- at least one decision/outcome branch explaining what changes.

Reject:
"Do more research."
"TBD."
or equivalent incomplete advice.

==================================================
K. G3-N6 — ROUTE/STAGE MODEL CONTRACT APPLICABILITY
==================================================

Correct model task construction.

PRE-EXPLANATION EXPLAIN

EARLY IDEA / DISCOVERY PROPOSAL that is still pre-explanation must receive the
appropriate discovery questions from rubric v5 §2.2 rather than being forced
through a completed EXPLAIN mechanism assessment.

ESTABLISH / TEST

- send only applicable route questions;
- send an explicit route-applicability map;
- do not send EXPLAIN mechanism criteria as if applicable;
- do not send NO-ADVANCE or theory dimensions where route-inapplicable.

TARGETED WORKSPACES

Argument/Literature/Alternatives targeted runs must filter requested judgments
by route applicability.

Do not request theory ratings for ESTABLISH/TEST when they are not applicable.

If targeted payloads do not support route-item answers, do not include
route-item questions in those payloads.

HIGH-SCORE BENCHMARK REFERENCES

Published benchmark references used for an 8+ requirement must derive from an
actual admitted/cited source attribution, not unsupported model-authored text.

Add route/stage matrix tests.

==================================================
L. G3-N7 — PROVIDER TRANSACTION / DURABLE USAGE / ERROR CODES
==================================================

Move provider calls outside open DB transactions.

Required pattern:
1. freeze/record authorized request context;
2. commit transaction;
3. perform provider call;
4. durably append provider receipt/usage immediately after each call;
5. reopen transaction;
6. verify project/run state still permits attachment;
7. persist outcome.

Do not hold local DB locks across remote model latency.

USAGE / RECEIPTS

Persist incurred provider usage after each completed call, including when a later
step fails.

Crash/checker failure must not erase already incurred usage.

MODEL IDENTITY

If provider returns a model identity different from the configured/expected
model beyond allowed provider aliasing rules:
- fail visibly as MODEL_MISMATCH;
- do not silently accept substitution.

ERROR CODES

Distinguish meaningful provider failures such as:
- credential/authentication;
- permission;
- model not found/unavailable;
- context/request too large;
- bad request/schema;
- rate limit;
- timeout;
- transient 5xx;
- refusal;
- incomplete response.

Do not collapse unrelated 4xx errors into one generic code.

==================================================
M. G3-N8 — BENCHMARK METRICS AND BASELINE FAIRNESS
==================================================

Fix before any calibration.

WITHHOLDING / STATE ACCURACY

Use typed canonical state enums, not casefold/string-literal accidents.

Do not credit a confident null-valued result merely because a verification field
happens to say unresolved.

RESTORATION

Restoration recognition must compare:
- intact/reference;
- degraded/hidden;
- restored

so an evaluator that never changed cannot receive restoration credit.

DETECTION

Separate:
- scientific value/state change;
from
- verification/disposition change.

Do not advantage the Workbench simply because baseline lacks an internal
verification channel.

DIRECTION

A "downgrade" expectation means scientifically lower/weaker/more uncertain, not
simply "different."

An upgrade must not satisfy downgrade.

UNCHANGED

Actually score expected invariant/unchanged judgments.

AGGREGATION

- group by evaluator configuration/model/prompt/version;
- do not pool incomparable configurations;
- deduplicate explicit reruns appropriately;
- retain/report failed runs rather than silently dropping them;
- paper-level aggregation keeps variants nested under paper.

BASELINE V2

Create a fair baseline prompt that includes the minimum output-validity
constraints required by the shared schema, including:
- valid unresolved/withholding representation;
- inspected_material/source constraints;
- route/stage applicability.

Do not add Workbench multi-stage advantages.
Do not intentionally weaken baseline.

==================================================
N. G3-N9 — BATCH RESUME / NEUTRAL BENCHMARK LABEL
==================================================

- orphan/interrupted reservations must produce a durable INTERRUPTED/ORPHANED
  status or explicit resume report;
- they must not disappear silently;
- one case's pre-claim validation failure must not abort the entire batch result;
- isolate/report per-case failure;
- resume must know what remains.

Replace provider-facing text such as:
"Authorized synthetic benchmark packet"

with a neutral rights/context declaration valid for:
- synthetic fixtures;
- published-paper blind corpus;
- other authorized benchmark material.

Do not prime the evaluator that the input is synthetic or a benchmark unless
that fact is intentionally part of the experimental condition.

==================================================
O. G3-N10 — PRIVATE PILOT HEALTH / BACKUP / MIGRATION
==================================================

HEALTH

Add read-only integrity checks for:
- revision consistency;
- original/source presence;
- original/source hash match;
- important store digests;
- schema integrity;
- benchmark/admin integrity as appropriate.

A tampered revision or missing original must not produce 8/8 PASS.

BACKUP

Before claiming success:
- validate referenced originals exist;
- validate hashes;
- exclude/relocate temporary evaluator scratch and *.tmp material not part of
  canonical state.

A backup that cannot restore is a failed backup.

RESTORE

On failed restore:
- rollback created files/directories;
- allow clean retry;
- no half-created target that blocks subsequent restore.

MIGRATION

Version-0 migration may not simply adopt an arbitrary foreign table named
projects.

Validate actual expected schema after DDL/migration.

OPERATOR ERRORS

Use specific error codes for:
- missing Node/tool dependency;
- invalid schema;
- missing/corrupt source;
- storage permission;
- incompatible backup;
- other material operational cases.

Do not collapse all to INVALID_OPERATOR_INPUT_OR_STORAGE.

==================================================
P. G3-N11 — REVIEW REPRODUCIBILITY DISPLAY / EXPORT
==================================================

Review index/header and Markdown export must expose enough identity to compare
like with like.

Include:
- project revision;
- review scope;
- target workspace/component;
- stale/current status;
- rubric version/hash;
- manifest/policy version/hash;
- model/provider identity;
- prompt/task version where appropriate.

If review differs from currently active rubric/manifest/model configuration,
make that difference visible.

Historical stored output itself remains immutable.

==================================================
Q. G3-N12 — V5 READINESS IMPLEMENTATION
==================================================

Implement the new v5 rule exactly:

For ESTABLISH / TEST route assessment component:

- required item NOT INSPECTED -> UNKNOWN;
- required item BLOCKING -> FALSE;
- otherwise -> TRUE for the route-assessment component, including
  DEVELOPMENT NEEDED.

Then apply all other §8.5 readiness requirements independently.

Do not convert missing/uninspected to failure.

Add exhaustive route-status tests.

==================================================
R. G3-N13 — TEST QUALITY
==================================================

Add requirement-derived regression tests for every GATE-3 defect.

In particular:

- benchmark blindness tests assert stable ORDER/POSITION, not merely absence of
  hidden text;
- split tests cover cross-version reassignment, duplicate content, relabelled
  variants, and unstored manifest execution;
- checker tests cover all summary decision-driving fields, not obstacle only;
- staleness tests cover overlapping scientific dimensions/scopes;
- field-level provenance tests;
- forged import tests;
- route/stage contract matrix;
- provider transaction/usage tests;
- benchmark metric arithmetic tests;
- baseline fairness tests;
- backup/restore negative cases.

Add PostgreSQL-parametrized coverage for:
- backup -> restore;
- RunManager/provider lifecycle where practical;
- operator/migration paths that materially depend on PostgreSQL semantics.

==================================================
S. FORMAL STEP-12 ISOLATION REQUIREMENT
==================================================

The repaired repository must be ready for the agreed Step-12 architecture:

A physically separate PRIVATE corpus-builder repository will contain:
- full papers;
- gold decompositions;
- mutation definitions;
- expectations;
- split assignments.

The Workbench repository will NOT contain those private artifacts.

The builder will export versioned benchmark-package-v1 artifacts.

The Workbench will import/validate them.

The blind evaluator will receive only sanitized evaluator packets.

The blind evaluator must not be able to:
- access the builder repo;
- fetch gold;
- fetch expected outcomes;
- fetch hidden content;
- enumerate sibling variants in a content-leaking manner.

Separate Git histories are assumed.

Design the handoff contract accordingly.

==================================================
T. GOVERNANCE / ROADMAP
==================================================

Add or preserve this governance rule:

Agents may create commits, fixes and task-local work items inside the current
roadmap step, but may not create new roadmap steps, gates, phases or numbered
sub-stages.

Any modification to the 16-step roadmap requires explicit product-owner approval.

Do not renumber the roadmap.

Current step remains:
11/16 — GATE-3 repair

==================================================
U. ACCEPTANCE TESTS
==================================================

Before reporting completion, demonstrate at minimum:

RUBRIC V5
1. v4 remains immutable and available historically.
2. v5 differs substantively only by the documented readiness clarification.
3. new evaluations use v5.
4. old v4 reviews remain byte/stored-result stable.
5. ESTABLISH/TEST NOT INSPECTED -> readiness UNKNOWN.
6. BLOCKING -> FALSE.
7. DEVELOPMENT NEEDED alone does not force FALSE.
8. no implicit count threshold exists.

BENCHMARK EXPERIMENTAL INTEGRITY
9. paired variants preserve unrelated order/position.
10. degradation replaces in place.
11. restoration restores in place.
12. cross-version split reassignment rejected.
13. duplicate underlying package across splits rejected.
14. relabelled sibling cross-split attempt rejected.
15. unstored/unfrozen manifest cannot run.
16. benchmark-package-v1 schema validates.
17. malformed semantic package fails before registration.
18. expectations are frozen before results.
19. blind evaluator cannot access gold/hidden/expectations.
20. Step-12 import/validate CLI works on a synthetic external-style package.

CHECKING / SCIENTIFIC DISCIPLINE
21. unchecked new summary allegation cannot become settled conclusion.
22. disclaimer is server-owned.
23. limitations cannot silently disappear.
24. route items needed for readiness receive verification dispositions.
25. unverified route items remain UNKNOWN/NOT INSPECTED.
26. generated "user-reported" results without grounding are rejected.
27. incomplete review Next Action is rejected.

REVISION / PROVENANCE
28. scoped reviews stale on overlapping relevant changes.
29. unrelated scopes stay current.
30. Overview uses/latest full integrated review appropriately.
31. one accepted head per lineage.
32. stale proposal acceptance conflicts.
33. unchanged generated fields remain model-origin after partial user edit.
34. wording-only cannot hide substantive metadata/evidence/dependency changes.
35. import cannot forge source/documented/verified authority.
36. nested local storage paths do not appear in exports.

MODEL / PROVIDER
37. route/stage payload applicability matrix passes.
38. provider calls occur outside open DB transaction.
39. incurred usage survives later run failure.
40. MODEL_MISMATCH detected.
41. meaningful provider error classes preserved.

BENCHMARK METRICS / BASELINE
42. withholding metric handles canonical states correctly.
43. restoration requires actual degraded->restored recovery.
44. verification-only change is reported separately from scientific change.
45. downgrade cannot be satisfied by upgrade.
46. expected unchanged is measured.
47. failed runs remain in aggregate reporting.
48. configs/reruns are not pooled incorrectly.
49. baseline-v2 produces valid schema without Workbench-only advantages.

OPERATIONS
50. interrupted benchmark reservations remain visible.
51. one invalid benchmark case does not kill whole batch.
52. provider packet label is neutral.
53. health fails on tampered revision.
54. health fails on missing/corrupt source.
55. backup refuses invalid canonical store.
56. backup excludes scratch/temp files.
57. failed restore rolls back cleanly.
58. migration rejects/adjudicates foreign incompatible schema.
59. operator errors are materially specific.
60. PostgreSQL backup/restore parity passes in CI.

REPRODUCIBILITY
61. review UI/export identifies revision/scope/rubric/model/manifest.
62. historical review remains immutable.
63. benchmark run captures exact rubric v5 hash/version.
64. benchmark package/hash/expectation/run lineage is reproducible.

REGRESSION
65. all existing valid RDW-001 through RDW-008 tests pass.
66. prior 16 golden cases either remain valid under v5 or are versioned
    appropriately if readiness expectations changed.
67. browser e2e passes.
68. type/lint/build/contracts pass.
69. publication/security checks pass.
70. no private papers/secrets are tracked.

==================================================
V. WORKFLOW
==================================================

1. Verify clean synchronized main at:
   fbba2d7c2825bae9d2e118d0c6db2b7bc48f5ea7

2. Create a GATE-3 repair branch.

3. Record the GATE-3 audit findings in docs/audits if not already stored.

4. Create rubric v5 first and record the exact V4 -> V5 change.

5. Update policy/version infrastructure while preserving historical v4 behavior.

6. Fix G3-B1 through G3-B4.

7. Fix G3-N1 through G3-N13.

8. Add requirement-derived regressions.

9. Run focused tests as each logical issue is corrected.

10. Run the complete backend suite.

11. Run mandatory PostgreSQL CI/parity.

12. Run browser e2e.

13. Run benchmark synthetic suite.

14. Run operator/backup/restore/health tests.

15. Run publication/security/governing-integrity checks.

16. Commit and push repair branch.

17. Integrate to main only if all acceptance checks pass.

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

RUBRIC:
- active rubric: v5
- v4 historical artifact preserved: YES/NO
- v5 change limited to readiness clarification: YES/NO
- old v4 reviews unchanged: YES/NO

GATE-3 BLOCKERS:
- G3-B1: RESOLVED/UNRESOLVED
- G3-B2: RESOLVED/UNRESOLVED
- G3-B3: RESOLVED/UNRESOLVED
- G3-B4: RESOLVED/UNRESOLVED

GATE-3 NONBLOCKERS:
- G3-N1: RESOLVED/UNRESOLVED
- G3-N2: RESOLVED/UNRESOLVED
- G3-N3: RESOLVED/UNRESOLVED
- G3-N4: RESOLVED/UNRESOLVED
- G3-N5: RESOLVED/UNRESOLVED
- G3-N6: RESOLVED/UNRESOLVED
- G3-N7: RESOLVED/UNRESOLVED
- G3-N8: RESOLVED/UNRESOLVED
- G3-N9: RESOLVED/UNRESOLVED
- G3-N10: RESOLVED/UNRESOLVED
- G3-N11: RESOLVED/UNRESOLVED
- G3-N12: RESOLVED/UNRESOLVED
- G3-N13: RESOLVED/UNRESOLVED

BENCHMARK:
- stable paired ordering: PASS/FAIL
- split contamination protection: PASS/FAIL
- package-v1 schema: PASS/FAIL
- import/validate CLI: PASS/FAIL
- expectations frozen: PASS/FAIL
- gold/evaluator separation: PASS/FAIL
- baseline fairness: PASS/FAIL
- metrics corrected: PASS/FAIL

SCIENTIFIC DISCIPLINE:
- checker cannot promote unchecked conclusions: PASS/FAIL
- route items verified before readiness: PASS/FAIL
- fabricated reported results rejected: PASS/FAIL
- review Next Actions diagnostic: PASS/FAIL
- route/stage applicability: PASS/FAIL

REVISION / PROVENANCE:
- one accepted head per lineage: PASS/FAIL
- scoped staleness correct: PASS/FAIL
- field-level provenance preserved: PASS/FAIL
- import authority escalation blocked: PASS/FAIL

PROVIDER:
- remote calls outside DB transaction: PASS/FAIL
- durable usage receipts: PASS/FAIL
- model mismatch detected: PASS/FAIL
- error taxonomy: PASS/FAIL

OPERATIONS:
- health integrity scan: PASS/FAIL
- backup integrity: PASS/FAIL
- restore rollback: PASS/FAIL
- migration validation: PASS/FAIL
- PostgreSQL parity: PASS/FAIL

TESTS:
- backend passed: ...
- failed: ...
- v5 golden cases: ...
- browser e2e: ...
- synthetic benchmark tests: ...

GOVERNING FILES:
- product spec unchanged: YES/NO
- 16-step roadmap unchanged: YES/NO

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
