Repair all remaining findings from the final independent GATE-3 audit.

REPOSITORY

C:\Users\galbl\src\Research-Development-Workbench

CURRENT ROADMAP STEP

11/16 — GATE-3

Do not create another roadmap step, phase, sub-stage, or fractional step.

Do NOT:
- start Step 12;
- access the 50-paper corpus;
- construct real benchmark packages;
- calibrate the evaluator;
- modify rubric v5;
- modify historical rubric v4;
- modify the product specification;
- change the frozen 16-step roadmap.

AUDITED COMMIT

96b64b22303f258b020e1543bcf70b1b96d2b6af

GATE-3 RESULT

FAIL

Remaining findings:

BLOCKERS
- G3-FINAL2-B1
- G3-FINAL2-B2
- G3-FINAL2-B3
- G3-FINAL2-B4

IMPORTANT NONBLOCKERS
- G3-FINAL2-N1 through G3-FINAL2-N16

Rubric questions:
NONE

Resolve all 20 findings before the next independent GATE-3 rerun.

Do not reinterpret rubric policy. These are implementation, benchmark-contract,
scientific-state, provenance, operational, UI, and test defects.

==================================================
READ FIRST
==================================================

1. AGENTS.md
2. active rubric v5
3. historical rubric v4
4. product specification
5. architecture
6. frozen roadmap
7. RDW-001 through RDW-008 task contracts
8. all GATE-1, GATE-2 and GATE-3 audit/resolution records
9. benchmark-package-v1 schema/docs
10. benchmark evaluator, metrics, variants, runner and store
11. portability/provenance code
12. model task contracts/checker
13. operator/backup/health code
14. frontend review/workspace code
15. existing permanent tests

==================================================
A. G3-FINAL2-B1
SCIENTIFIC STATE MUST NOT BE CHECKER DISPOSITION
==================================================

ROOT DEFECT

For statements, the benchmark translator currently allows the Workbench checker
disposition to overwrite or define scientific_state.

This is conceptually wrong.

The three axes remain separate:

1. SCIENTIFIC STATE
   What the evaluator is scientifically asserting.

2. ADOPTION / AUTHORING STATE
   Proposed, adopted, rejected, superseded, etc.

3. VERIFICATION / CHECKING DISPOSITION
   What the Workbench checker says about that assertion.

The checker does not change scientific state merely because it SUPPORTS,
NEEDS_REVISION, or otherwise verifies the assertion.

EXAMPLE

Evaluator says:

kind = unresolved
"Cannot determine the bounded claim from inspected material."

That scientific state remains UNRESOLVED whether the checker says:

- SUPPORTED
- NEEDS_REVISION
- UNRESOLVED

The checker result belongs on the verification axis.

REQUIRED TRANSLATION

Derive scientific_state only from the evaluator's scientific output:

- statement kind/status;
- route-item status;
- finding status;
- rating/evidence status;
- other typed scientific representation.

Do NOT derive scientific_state from checker disposition.

Keep checker disposition only in verification_state.

checking_performed must be TRUE only when an actual check occurred.

An unchecked judgment must NOT receive a fake default verification=UNRESOLVED.

Use:
verification_state = NONE / NOT_CHECKED
or equivalent typed absence.

Checker-proposed objections are not "checked" merely because the checker
generated them. They require an actual checking disposition under the existing
checker rules.

WITHHOLDING

Define one architecture-neutral scientific withholding rule across judgment
types.

If the evaluator scientifically abstains:

- UNRESOLVED
- NOT INSPECTED
- PENDING where allowed
- equivalent legitimate typed uncertainty

then it may receive withholding credit when expected.

This should work regardless of whether the evaluator is:

- Workbench;
- baseline.

Checker verification is a separate metric.

Apply the same principle to:

- statements;
- ratings;
- findings;
- route items.

Currently route/rating/finding checker UNRESOLVED does not propagate correctly.
Fix the translation consistently.

REQUIRED END-TO-END TESTS

Through actual OpenAIAdapter + AssessmentChecker with mocked transport:

1. evaluator statement kind=UNRESOLVED, checker=SUPPORTED
   -> scientific_state UNRESOLVED
   -> verification_state SUPPORTED.

2. same evaluator output, checker=NEEDS_REVISION
   -> scientific_state still UNRESOLVED
   -> verification_state NEEDS_REVISION.

3. same evaluator output, checker=UNRESOLVED
   -> scientific_state UNRESOLVED
   -> verification_state UNRESOLVED.

4. all three receive scientific withholding credit when the expectation permits
   UNRESOLVED.

5. verification-state expectations distinguish the three cases.

6. unchecked Workbench judgment:
   checking_performed FALSE;
   verification_state absent;
   no fake UNRESOLVED verification.

7. baseline scientific UNRESOLVED gets the same scientific withholding credit.

8. ratings/findings/route items follow the same typed logic where applicable.

==================================================
B. G3-FINAL2-B2
DOWNGRADE MUST MEAN STRICT SCIENTIFIC WORSENING
==================================================

CURRENT DEFECT

The harness currently allows:

- upgrade to satisfy downgrade;
- sideways/non-comparable move to satisfy downgrade;
- malformed downgrade + direction=higher expectations;
- state changes without typed scientific ordering.

REQUIRED VALIDATION

Reject impossible expectation combinations at package validation.

At minimum:

behavior = downgrade
+
direction = higher

must be invalid.

Likewise reject any internally contradictory behavior/direction specification.

TYPED ORDERING

Define scientific ordering only where the judgment type actually has one.

Examples:

ROUTE ITEM:
ADEQUATE FOR STAGE
    >
DEVELOPMENT NEEDED
    >
BLOCKING

Uncertainty states are not automatically "lower quality" in every context.
Treat them according to the expectation type:

- more uncertain;
- withheld;
- unavailable;
- not applicable.

Do not force all states onto one universal numeric ladder.

NUMERIC RATINGS

For ratings:
lower numeric value = downgrade,
when the comparison is defined.

A 5 -> 7 change can NEVER satisfy downgrade.

ROUTE EXAMPLE

BLOCKING -> DEVELOPMENT NEEDED
is an improvement, not degradation.

It cannot satisfy downgrade.

NON-COMPARABLE EXAMPLE

NOT APPLICABLE -> PENDING

is not automatically downgrade.

It should be unavailable/non-comparable unless the expectation explicitly
defines an uncertainty transition.

PACKAGE VALIDATION

If a downgrade expectation names acceptable terminal states, validate that the
combination is coherent with the applicable ordering.

Do not freeze a logically impossible expectation.

TEST:

- rating 5->7 under downgrade -> FAIL;
- rating 7->5 -> PASS;
- BLOCKING->DEVELOPMENT NEEDED -> not downgrade;
- ADEQUATE->DEVELOPMENT NEEDED -> downgrade;
- direction=higher + downgrade -> schema/semantic rejection;
- sideways/unordered transition -> unavailable unless explicitly defined.

==================================================
C. G3-FINAL2-B3
EXECUTION MUST BIND EXACT PACKAGE / MANIFEST / TRANSFORMATION SEMANTICS
==================================================

CURRENT DEFECT A

A variant created under package X:1 / manifest v1 can be executed under project
X:2 / manifest v2.

The run then records X:2 provenance even though the packet came from X:1.

This is unacceptable.

EXECUTION BINDING

Before every benchmark execution verify:

- variant package hash == executing project package hash;
- variant manifest hash == stored frozen executing manifest hash;
- underlying paper identity matches;
- split matches;
- variant belongs to that frozen package version;
- expectation belongs to the same frozen benchmark lineage.

Failure must occur BEFORE evaluator execution.

Never rewrite provenance to the currently supplied project.

CURRENT DEFECT B

CONTROLLED_DEGRADATION may use replacement content identical to the original.

Reject no-op degradation.

For scientific degradation:

- target original exists;
- replacement is actually different in relevant scientific content;
- replacement role is scientifically valid;
- evaluator packet must differ from intact on the targeted content.

A no-op replacement cannot be labelled degradation.

CURRENT DEFECT C

metadata_only replacement can own a scientific feature and produce a packet
equivalent to hiding.

Reject this.

A metadata-only block cannot own scientific features.

Metadata stripping is not scientific degradation.

CURRENT DEFECT D

Restoration can use an "intact" reference packet identical to the degraded
packet.

RESTORATION SEMANTICS

Require:

- intact/reference packet differs from degraded predecessor on target;
- degraded predecessor actually contains target degradation/removal;
- restored packet returns the target toward the intact scientific content;
- semantic roles must be validated, not merely variant IDs/visibility bits.

Add negative CLI/package tests for all four cases.

==================================================
D. G3-FINAL2-B4
PORTABLE IMPORT CAN NEVER ASSERT VERIFIED SUPPORT IT CANNOT RECHECK
==================================================

CURRENT DEFECT

Portable imports do not carry source passages.

A forged imported file can include:

- admitted text-less document version;
- self-hashed anchor;
- SUPPORTED disposition.

Because refs exist internally, the import retains SUPPORTED and sends it to the
model even though the application cannot re-verify the source.

REQUIRED POLICY

For PORTABLE IMPORT:

Every imported SUPPORTED scientific disposition must be demoted to UNRESOLVED
unless support can be independently reconstructed and verified from trusted
bundled evidence under an explicitly supported import format.

Current portable format does not carry source text.

Therefore for current portable import:

SUPPORTED -> UNRESOLVED

Preserve:
- original imported claim;
- original imported disposition as historical/import provenance;
- reason for demotion.

Do not silently delete history.

WORKING CONTEXT

The active model-facing ContextPacket must contain only the demoted current
scientific support state.

Never expose imported self-asserted SUPPORTED as genuine verified support.

Add an end-to-end regression inspecting the actual provider request.

==================================================
E. G3-FINAL2-N1
UNAVAILABLE METRIC COMPARISONS
==================================================

Metrics must distinguish:

0 = evaluated and failed
from
None / unavailable = comparison cannot be evaluated.

RESTORATION

If required intact/degraded/restored reference is missing:
metric = unavailable / None,
not 0/1.

INVARIANCE / UNCHANGED

If a judgment exists in one required side and disappears in the other:
that is a CHANGE and must be evaluated appropriately.

Do not silently turn it into denominator 0.

ACTION RELEVANCE

If no action annotation exists:
metric = unavailable / None,
not 0/1.

Report denominators explicitly.

==================================================
F. G3-FINAL2-N2
FAILURES / RERUNS / ORPHANS MUST REMAIN VISIBLE
==================================================

Do not allow successful reruns to erase failed attempts.

Aggregate reporting must expose at least:

- successful cases;
- failed attempts;
- final successful variants;
- invalid cases;
- orphan/interrupted reservations;
- reference-unavailable cases.

A failed attempt followed by success should retain both facts.

REFERENCE HANDLING

A failed reference should affect only cases that actually name that reference.

Do not poison every case for the same paper.

Do not silently remove INVALID_CASE cases from aggregate reporting.

==================================================
G. G3-FINAL2-N3
EXPECTATION CONSTRAINT COHERENCE
==================================================

Legacy acceptable_states / forbidden_states now refer to scientific states.

They must NOT accept adoption values such as:

- proposed
- accepted
- rejected
- superseded

Reject these at package validation.

Also reject contradictory combinations between legacy and typed constraints.

Examples:

legacy acceptable states excludes every explicit typed acceptable scientific
state -> reject.

acceptable and forbidden sets overlap in an impossible way -> reject.

Do not allow unsatisfiable expectations to freeze.

==================================================
H. G3-FINAL2-N4
BASELINE PROMPT MUST BE SELF-CONTAINED
==================================================

The baseline model does NOT see evaluation-v3.

Do not refer to invisible instructions.

Create the next baseline prompt version with all output-validity requirements it
actually needs.

Include explicitly:

- required output schema behavior;
- all required dimensions for FULL mode;
- inspected_material must use authorized anchor IDs;
- TARGETED run must emit only applicable requested judgments;
- permitted statement kinds, including UNRESOLVED;
- route/stage applicability;
- legitimate abstention representation;
- no fabricated checking/verification field;
- source attribution constraints.

Do not give baseline Workbench's multi-stage checker or other workflow advantage.

The baseline remains one fair, well-written prompt.

==================================================
I. G3-FINAL2-N5
SPLIT IDENTITY MUST SURVIVE HARMLESS SURFACE CHANGES
==================================================

Current identity check is too dependent on exact bytes.

A held-out paper can be reintroduced under a new ID after:

- block reorder;
- trailing whitespace;
- Unicode normalization difference;
- package ID rename;
- role-only change.

STEP-12 NEED

Underlying-paper identity must be stronger than exact decomposition bytes.

Implement a separate stable underlying-paper identity.

Preferred design:

- opaque paper_identity / source_identity fingerprint supplied by the non-blind
  corpus builder;
- not exposed to the blind evaluator;
- permanently bound to split;
- all package versions/supersessions for that paper retain this identity.

Also compute an administrative normalized-content fingerprint as a duplicate
diagnostic.

Normalize only for IDENTITY detection, not scientific evaluation:

- Unicode canonical normalization;
- whitespace normalization;
- deterministic block ordering for identity fingerprint where safe;
- surface package IDs excluded.

Do not use normalization to rewrite evaluator content.

ROLE CHANGES

A role change may alter scientific interpretation, so it can create a new
package VERSION while retaining the same underlying paper identity.

That paper stays in the same split.

LINEAGE

Support explicit:

- retire;
- supersede;
- corrected package version;

without forcing the paper into a new identity/split.

==================================================
J. G3-FINAL2-N6
STEP-12 IMPORT MUST BE PREFLIGHTED AND ATOMIC
==================================================

--validate-only must perform all checks that import will perform, including
collisions against the current store.

IMPORT ORDER

Do ALL validation/preflight before first persistent write.

If any later failure occurs:
rollback the entire import.

Do not leave:
- manifest;
- project;
- gold;
- variants;
- expectations

partially registered.

OUTPUT

Successful validate/import should report all relevant frozen hashes:

- package;
- paper identity;
- project;
- gold;
- variants;
- expectations;
- split manifest.

SECURITY

Refuse --package paths located inside the publication/public Workbench
repository where governance prohibits corpus artifacts.

Step 12 packages come from the separate private builder/export location.

==================================================
K. G3-FINAL2-N7
PACKAGE CONTRACT MUST BE AUTHORABLE FROM DOCS ALONE
==================================================

A separate corpus-builder must not need to inspect Workbench source code to
construct a valid package.

Document every current fail-closed construction rule, including:

- manifest sort order;
- identifier-scrub text and order;
- visibility-map semantics;
- reveal semantics;
- equivalent-replacement ID rules;
- packet_id hashing;
- transformation arity;
- artifact/file layout;
- runner glue required after import;
- canonical hashing;
- package/split/version identity;
- expectation semantics.

Add a command that can execute/import already-stored benchmark artifacts without
the builder repository.

Test:

A pure-JSON external-style builder using ONLY:
- docs;
- schema

can produce a valid package that:
- validates;
- imports;
- executes;
without importing Workbench implementation modules.

==================================================
L. G3-FINAL2-N8
ROBUST PLACEHOLDER NORMALIZATION
==================================================

Existing literal placeholder detection is too weak.

For generated required fields, normalize mechanically:

1. Unicode NFKC;
2. casefold;
3. collapse whitespace;
4. strip quotes/brackets/terminal punctuation;
5. for placeholder matching, remove non-alphanumeric separators.

Reject equivalent empty/placeholders such as:

- TBD
- T.B.D.
- (TBD)
- "TBD"
- TBD - TBD
- TODO
- To be determined.
- None.
- N / A
- "-"
- whitespace only

Also reject generic empty-action forms such as:
- Do  more research.
- do\tmore research
when the rest of the required diagnostic fields are placeholders.

Do NOT create a broad scientific keyword blacklist.

Valid concrete research tasks must still pass.

Apply consistently to:
- DiagnosticAction;
- generated Next Actions workspace.

==================================================
M. G3-FINAL2-N9
ROUTE/STAGE TASK CONTRACTS MUST MATCH RUBRIC V5 EXACTLY
==================================================

PRE-EXPLANATION EXPLAIN

Supply all six exact applicable §2.2 discovery assessment items with canonical
keys:

- knowledge_need
- increment_over_existing_knowledge
- scope_and_precision
- capacity_to_learn
- evidence_strategy
- next_use

Do not omit three of them.
Do not mislabel capacity_to_learn.

ESTABLISH / TEST

Filter dimension requests by route applicability.

Do not request d1-d7 EXPLAIN ratings for ESTABLISH/TEST.

TARGETED CHECKS

Argument/Literature/Alternatives targeted runs must not request inapplicable
theory dimensions.

Reject non-null returned ratings for dimensions that are NOT APPLICABLE to the
route.

Do not merely display them and continue.

Use exact v5 route questions, not approximate paraphrases that change the task.

==================================================
N. G3-FINAL2-N10
BLOCKING MUST ACTUALLY BLOCK NON-EXPLAIN STAGE DECISIONS
==================================================

Rubric v5 is explicit:

BLOCKING:
"prevents a positive decision at the requested stage"

Implement this for ESTABLISH / TEST.

For applicable route decisions:

verified BLOCKING ->
positive proposal/stage readiness FALSE where that route item governs the
requested commitment.

NOT INSPECTED / unverified required route item ->
UNKNOWN / provisional as appropriate.

Do not leave:

proposal_readiness = TRUE
or
bounded_route_development = TRUE

when a verified BLOCKING item defeats that requested stage.

A lower bounded premise-check or repair action may still be permissible if the
rubric allows it, but that is a different decision from positive advancement of
the blocked project.

Add stage-by-stage tests.

==================================================
O. G3-FINAL2-N11
USEFULNESS DEPENDENCY MAPPING
==================================================

Usefulness supports:

- dimension 1;
- dimension 7.

Map Usefulness -> dimensions (1,7) in dependency/staleness behavior.

If a consequential Usefulness edit changes material relied on by a Brief review
rating d1/d7:
the relevant Brief/scoped review must stale.

Do not stale unrelated dimensions/workspaces.

==================================================
P. G3-FINAL2-N12
IMPORT ORIGIN LINEAGE + IMPORTED PROJECT EVALUATION
==================================================

ORIGIN LINEAGE

Across revisions of the same object_id:

An object that was generated/provider-bearing in prior history cannot later be
imported as pure user_text merely by relabelling the latest revision.

Validate consistent provenance lineage.

Preserve:
- generated origin;
- user edits at field level;
- imported origin.

Do not allow provenance laundering across revisions.

IMPORTED PROJECT EVALUATION

Imported projects must remain evaluable where sufficient current material exists.

Unavailable historical references should be recorded as exclusions, not cause a
generic 422 snapshot validation failure when they are not required for current
evaluation.

Preserve historical limitation explicitly.

==================================================
Q. G3-FINAL2-N13
UI MUST SHOW ROUTE-ASSESSMENT BASIS
==================================================

For ESTABLISH / TEST and pre-explanation discovery, the user must be able to see
the basis for readiness.

Render:

- each route assessment item;
- status;
- reason;
- verification/checking disposition;
- applicable flags;
- gate outcome;
- missed/unknown reasons.

Do not force the user to infer readiness from a TRUE/FALSE label.

Keep display plain and compact.

No decorative dashboard needed.

==================================================
R. G3-FINAL2-N14
OPERATIONS: HEALTH / BACKUP / RESTORE / MIGRATION / ERROR CODES
==================================================

HEALTH

Detect:
- deleted anchor rows;
- incomplete reference sets;
- missing/corrupt source originals;
- hash mismatches;
- admin-binding inconsistencies.

BACKUP

Before PASS:
- validate schema;
- validate canonical references;
- validate full anchor/source sets;
- validate admin bindings;
- ensure backup can pass restore preflight.

A backup that cannot restore is FAILED.

RESTORE

Validate schema/admin bindings before commit.

Rollback cleanly on failure.

CLI

Do not print raw tracebacks for expected operational failures.

Map to specific useful error codes.

MIGRATION VERSION 0

If a supposedly fresh version-0 database already contains unrelated/preexisting
tables:
refuse/adjudicate explicitly.

Do not silently adopt them.

POSTGRESQL

Add equivalent smoke coverage for operator/CLI behavior under PostgreSQL where
semantics matter.

==================================================
S. G3-FINAL2-N15
PROVIDER USAGE MUST LINK TO FAILED RUN RECEIPT
==================================================

If paid provider calls occurred and a later non-provider failure happens:

- preserve usage ledger;
- attach it to the failed run receipt;
- provider_run/run metadata must reference incurred usage;
- failure_kind must be populated;
- ledger status must not misleadingly remain SUCCEEDED as if the overall run
  succeeded.

Handle:
- InvalidModelOutput;
- checker failure;
- persistence attachment failure;
- generic downstream exception.

Do not lose incurred cost.

==================================================
T. G3-FINAL2-N16
REQUIREMENT-DERIVED TESTS
==================================================

Add permanent tests reproducing every blocker and relevant nonblocker above.

The audit specifically found existing helpers too narrow.

Do NOT only test model_inference statement helpers.

At minimum add regressions for:

BLOCKERS
- Workbench abstention + checker SUPPORTED;
- Workbench abstention + checker NEEDS_REVISION;
- route/rating/finding UNRESOLVED withholding;
- downgrade state ordering;
- impossible downgrade+direction combination;
- package/manifest execution mismatch;
- no-op degradation;
- metadata-only degradation;
- identical restore reference;
- bundled text-less anchor SUPPORTED import forgery.

NONBLOCKERS
- unavailable metrics;
- failed rerun reporting;
- expectation constraint contradictions;
- baseline output-validity prompt;
- normalized paper identity;
- atomic import;
- docs-only package construction;
- robust placeholder normalization;
- exact route applicability;
- BLOCKING stage decisions;
- Usefulness staleness;
- cross-revision origin laundering;
- imported-project evaluation;
- route assessment UI;
- anchor-deletion backup/health;
- usage-linked downstream failure.

Add a PostgreSQL services.pilot / CLI smoke test in CI.

==================================================
U. PACKAGE / SCHEMA VERSIONING
==================================================

Prefer backward-compatible strengthening of benchmark-package-v1.

However, if the typed identity/expectation correction truly requires an
incompatible external schema change:

- do not silently redefine v1;
- create an explicit new schema version;
- retain a clear compatibility/migration rule;
- update external builder docs.

Because Step 12 has NOT started, this is the last safe point for such a change.

Do not bump schema merely for convenience.

==================================================
V. STEP-12 CORPUS ASSUMPTION
==================================================

Preserve this future architecture:

SOURCE CORPUS, READ ONLY

C:\Users\galbl\OneDrive\מסמכים\Postdoc\Projects\Research Ideas Rubric\Calibration Papers

50 papers:
- journal subfolders;
- MD + PDF for each paper.

PRIVATE REPO A
benchmark-corpus-builder

Non-blind builder:
- reads MD primarily;
- checks PDF where needed;
- decomposes scientific content;
- keeps private source traceability;
- paraphrases scientific content;
- strips identifiers;
- creates idea/proposal/completed representations;
- creates hide/degrade/restore/combined variants;
- assigns gold expectations and splits.

REPO B
Research-Development-Workbench

Receives only sanitized versioned packages.

The blind evaluator never receives original papers.

Therefore:
- equivalent paraphrase remains visible;
- paraphrase != hiding;
- paraphrase != degradation;
- normalized paper identity is administrative only;
- evaluator content is never normalized into altered scientific text.

==================================================
W. ACCEPTANCE
==================================================

Before completion prove at minimum:

BLOCKER B1
1. scientific state independent of checker disposition;
2. Workbench abstention + checker SUPPORTED gets scientific withholding credit;
3. Workbench abstention + NEEDS_REVISION gets scientific withholding credit;
4. checker verification remains separately measurable;
5. unchecked judgment has no fake verification;
6. all judgment types use consistent withholding semantics.

BLOCKER B2
7. downgrade cannot be satisfied by upgrade;
8. route-state ordering correct;
9. unordered transition not falsely credited;
10. contradictory downgrade direction rejected.

BLOCKER B3
11. package mismatch rejected at execution;
12. manifest mismatch rejected;
13. no-op degradation rejected;
14. metadata-only scientific degradation rejected;
15. identical intact/degraded restoration rejected.

BLOCKER B4
16. imported SUPPORTED demoted to UNRESOLVED;
17. historical imported disposition preserved as provenance;
18. provider request receives only demoted active state.

METRICS / REPORTING
19. missing references -> unavailable, not 0;
20. judgment disappearance affects invariance;
21. absent action annotation -> unavailable;
22. failed attempts remain visible after rerun;
23. invalid/orphan/reference-unavailable counts visible.

EXPECTATIONS / BASELINE
24. adoption values rejected from scientific-state constraints;
25. contradictory constraints rejected;
26. baseline prompt self-contained;
27. baseline valid abstention remains fair.

SPLIT / HANDOFF
28. normalized/stable paper identity prevents cosmetic split laundering;
29. supersede/correction lineage works;
30. validate-only performs store collision preflight;
31. failed import is atomic;
32. import reports frozen hashes;
33. package path governance works;
34. docs-only external package authoring works;
35. stored-artifact runner works without builder repo.

SCIENTIFIC BEHAVIOR
36. robust placeholder variants rejected;
37. exact six discovery route questions supplied;
38. ESTABLISH/TEST do not receive EXPLAIN ratings;
39. inapplicable returned ratings rejected;
40. verified BLOCKING prevents positive stage decision;
41. unverified required item makes decision provisional/UNKNOWN;
42. Usefulness consequential edit stales d1/d7-dependent review;
43. cross-revision provenance laundering blocked;
44. imported project can evaluate with explicit exclusions;
45. route-assessment basis visible in UI.

OPERATIONS
46. deleted anchor detected;
47. invalid store backup refused;
48. backup/restore schema validation passes;
49. version-0 foreign DB refused;
50. user-facing operational failures return specific codes;
51. incurred provider usage attached to failed run.

REGRESSION
52. 16/16 v5 golden;
53. historical v4 goldens;
54. backend full suite;
55. benchmark/package suite;
56. fake Workbench 27/27;
57. fake baseline 27/27;
58. browser suite;
59. PostgreSQL required suite with no skips;
60. PostgreSQL operator CLI smoke;
61. lint/format/mypy/contracts/build;
62. publication/governing checks;
63. rubric v5 unchanged;
64. historical v4 unchanged;
65. product spec unchanged;
66. roadmap unchanged;
67. no private papers or secrets tracked.

==================================================
X. WORKFLOW
==================================================

1. Verify clean synchronized main at:
   96b64b22303f258b020e1543bcf70b1b96d2b6af

2. Create GATE-3 repair branch.

3. Record G3-FINAL2 findings.

4. Fix B1 through B4 first.

5. Run exact reproductions.

6. Fix N1 through N16.

7. Add requirement-derived tests.

8. Run full backend suite.

9. Run benchmark/package/policy suite.

10. Run fake Workbench and baseline modes.

11. Run browser e2e.

12. Run operator/health/backup/import tests.

13. Run mandatory PostgreSQL CI including operator smoke.

14. Run lint/format/mypy/contracts/build.

15. Run publication/governing checks.

16. Commit and push.

17. Integrate to main only if every required check passes.

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

FINAL2 BLOCKERS:
- G3-FINAL2-B1: RESOLVED/UNRESOLVED
- G3-FINAL2-B2: RESOLVED/UNRESOLVED
- G3-FINAL2-B3: RESOLVED/UNRESOLVED
- G3-FINAL2-B4: RESOLVED/UNRESOLVED

FINAL2 NONBLOCKERS:
- G3-FINAL2-N1: RESOLVED/UNRESOLVED
- G3-FINAL2-N2: RESOLVED/UNRESOLVED
- G3-FINAL2-N3: RESOLVED/UNRESOLVED
- G3-FINAL2-N4: RESOLVED/UNRESOLVED
- G3-FINAL2-N5: RESOLVED/UNRESOLVED
- G3-FINAL2-N6: RESOLVED/UNRESOLVED
- G3-FINAL2-N7: RESOLVED/UNRESOLVED
- G3-FINAL2-N8: RESOLVED/UNRESOLVED
- G3-FINAL2-N9: RESOLVED/UNRESOLVED
- G3-FINAL2-N10: RESOLVED/UNRESOLVED
- G3-FINAL2-N11: RESOLVED/UNRESOLVED
- G3-FINAL2-N12: RESOLVED/UNRESOLVED
- G3-FINAL2-N13: RESOLVED/UNRESOLVED
- G3-FINAL2-N14: RESOLVED/UNRESOLVED
- G3-FINAL2-N15: RESOLVED/UNRESOLVED
- G3-FINAL2-N16: RESOLVED/UNRESOLVED

BENCHMARK SEMANTICS:
- scientific state independent from verification: PASS/FAIL
- architecture-neutral withholding: PASS/FAIL
- strict downgrade semantics: PASS/FAIL
- unavailable comparisons handled: PASS/FAIL
- failed attempts retained: PASS/FAIL

PACKAGE / SPLITS:
- execution package binding: PASS/FAIL
- no-op degradation rejected: PASS/FAIL
- restoration semantics: PASS/FAIL
- stable paper identity: PASS/FAIL
- atomic external import: PASS/FAIL
- docs-only builder contract: PASS/FAIL

PROVENANCE:
- imported support demoted safely: PASS/FAIL
- cross-revision origin laundering blocked: PASS/FAIL
- imported projects evaluable with exclusions: PASS/FAIL

SCIENTIFIC / ROUTES:
- robust generated placeholder rejection: PASS/FAIL
- exact discovery questions: PASS/FAIL
- route-inapplicable ratings rejected: PASS/FAIL
- BLOCKING stage decisions correct: PASS/FAIL
- Usefulness dependency correct: PASS/FAIL
- route assessment visible: PASS/FAIL

OPERATIONS:
- health/backup reference integrity: PASS/FAIL
- migration validation: PASS/FAIL
- specific CLI failures: PASS/FAIL
- downstream failure usage linked: PASS/FAIL
- PostgreSQL operator smoke: PASS/FAIL

TESTS:
- backend passed: ...
- failed: ...
- v5 golden: X/16
- benchmark/package: ...
- fake Workbench: X/27
- fake baseline: X/27
- browser: ...
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
- main synced: YES/NO
- working tree clean: YES/NO

BLOCKERS:
- none
or
- ...

NEXT:
GATE-3 independent rerun ready: YES/NO

Do not start Step 12.
