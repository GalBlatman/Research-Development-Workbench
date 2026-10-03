# GATE-3 rerun repair contract

Repair the remaining GATE-3 rerun findings for the Research Development Workbench.

REPOSITORY

C:\Users\galbl\src\Research-Development-Workbench

CURRENT ROADMAP STEP

11/16 — GATE-3

Do not create a new roadmap step, phase, sub-stage, or "11.5".

Do NOT:
- start Step 12;
- construct the 50-paper corpus;
- calibrate the evaluator;
- modify rubric v5;
- modify the product specification;
- use private or published benchmark papers.

CURRENT MAIN / AUDITED COMMIT

90d0c12aa4ba997991c19cd05acda4e3f68db79a

GATE-3 RERUN RESULT

FAIL

The independent rerun found:

BLOCKERS
- G3-RERUN-B1
- G3-RERUN-B2
- G3-RERUN-B3
- G3-RERUN-B4

IMPORTANT NONBLOCKERS
- G3-RERUN-N1
- G3-RERUN-N2
- G3-RERUN-N3
- G3-RERUN-N4

Rubric questions:
NONE

Resolve all eight findings.

Read first:

1. AGENTS.md
2. active rubric v5
3. product specification
4. architecture
5. roadmap
6. RDW-007/RDW-008 task contracts
7. original GATE-3 audit
8. GATE-3 repair record
9. GATE-3 rerun report
10. benchmark-package-v1 schema/docs
11. relevant implementation/tests

Do not reopen already resolved findings unless required by one of the eight
remaining defects.

==================================================
1. G3-RERUN-B1
PACKAGE VALIDATION: GOLD OWNERSHIP / RESTORATION SEMANTICS
==================================================

CURRENT FAILURE

benchmark-package-v1 accepts semantically invalid but self-consistent packages:

- gold features with empty required anchors;
- gold anchors that belong only to an unrelated feature;
- restoration expectations with no valid intact reference;
- restoration definitions where the supposed intact/reference variant is
  actually the degraded variant.

This makes Step-12 corpus authoring unsafe because malformed gold can freeze
successfully.

REQUIRED BEHAVIOR

Strengthen package semantic validation BEFORE registration/freezing.

GOLD FEATURE OWNERSHIP

For every gold feature that requires evidentiary support:

- require at least one valid owned source/block/anchor reference;
- every referenced block/anchor must exist;
- the referenced material must actually belong to that feature according to
  the package's declared feature/block ownership;
- an unrelated feature's anchor cannot satisfy the requirement;
- duplicates or contradictory ownership mappings fail visibly.

If a feature legitimately requires no source anchor under the contract, that
must be explicit in the schema/feature type rather than represented by an
accidental empty list.

RESTORATION SEMANTICS

A CONTROLLED_RESTORATION must reference valid comparison states:

- intact/reference variant exists;
- degraded/hidden predecessor exists;
- restored variant exists;
- all belong to the same underlying paper/project and compatible lineage;
- intact reference is actually intact for the restored target;
- degraded reference actually contains the specified degradation/removal;
- restored variant restores the target relative to that degradation;
- a degraded variant cannot be passed as the intact reference;
- missing intact or degraded references fail validation.

Validate the semantic ROLE of each referenced variant, not merely that its ID
exists.

CLI

The validate-only/import CLI must reject these packages before any immutable
artifact is registered.

Add negative CLI regressions for every reproduced case.

==================================================
2. G3-RERUN-B2
BENCHMARK WITHHOLDING METRIC
==================================================

CURRENT FAILURE

A canonical qualitative route judgment such as:

route:knowledge_need
state = NOT INSPECTED
value = null

is receiving withholding 0/1.

The metric currently mishandles the canonical qualitative representation.

REQUIRED BEHAVIOR

Use typed/canonical state semantics, not ad hoc string matching.

Define a single canonical abstention/withholding mapping for each judgment type.

At minimum distinguish:

- NOT INSPECTED
- PENDING where applicable
- UNRESOLVED where applicable
- NOT APPLICABLE
- BLOCKING
- DEVELOPMENT NEEDED
- ADEQUATE FOR STAGE
- supported/contradicted equivalents where applicable

WITHHOLDING ACCURACY

When evidence is insufficient and the benchmark expectation says withholding is
correct:

- canonical NOT INSPECTED must count as correct withholding;
- canonical PENDING/UNRESOLVED must count where they are permitted abstention
  states;
- confident null or missing-value output with no valid withholding state must
  NOT receive credit;
- NOT APPLICABLE must not be confused with uncertainty;
- BLOCKING/DEVELOPMENT NEEDED must not be treated as withholding.

Use typed enums/normalized internal values rather than casefold comparisons to
presentation strings.

Add direct arithmetic tests for route items, ratings/findings and other judgment
kinds used by the harness.

==================================================
3. G3-RERUN-B3
PORTABLE IMPORT: FORGED CHECK / SUPPORT METADATA
==================================================

CURRENT FAILURE

Import accepts:

- invented analysis_artifact_inspected metadata with no resolvable artifact;
- supported dispositions with no source references.

The imported objects may remain NOT INSPECTED at the broad evidence-state level,
but forged support/inspection metadata still survives into normal model-facing
ContextPacket content.

REQUIRED BEHAVIOR

Untrusted portable imports must not preserve stronger scientific verification
claims merely because the package is internally consistent.

On import:

INSPECTION CLAIMS

- analysis_artifact_inspected or equivalent must resolve to a bundled,
  authorized, verifiable artifact/check;
- if it cannot be resolved, reject or explicitly demote/remove the inspection
  claim;
- forged inspection metadata must never reach the working ContextPacket as if
  genuine.

SUPPORT DISPOSITIONS

- SUPPORTED or equivalent source-backed disposition requires resolvable source
  refs/anchors or the exact allowed non-source verification record;
- absent required support provenance -> demote to unresolved/not inspected or
  reject according to the existing import policy;
- never preserve "supported" while stripping the evidence that makes it
  supported.

IMPORT PROVENANCE

Continue marking imported records as imported.

Imported provenance must not itself imply scientific verification.

MODEL CONTEXT

Before model-facing ContextPacket assembly, assert that inspection/support
claims satisfy current provenance invariants.

Add forged-import tests that inspect the actual resulting ContextPacket, not only
stored database state.

==================================================
4. G3-RERUN-B4
"RESOURCES" CHANGE CLASSIFICATION CANNOT BYPASS STALENESS
==================================================

CURRENT FAILURE

After an Argument review, a consequential Argument claim can be added with:

change = resources

and the existing Argument review stays stale=false.

REQUIRED BEHAVIOR

"resources" may be used only for genuinely resource/logistical changes that do
not alter the scientific project state.

Examples of potentially resource-only changes:
- access logistics;
- budget;
- scheduling;
- non-scientific execution availability.

It may NOT cover a change to:
- argument;
- claim;
- mechanism;
- contribution;
- construct;
- rival;
- source evidence;
- study design;
- evidence status;
- route/stage;
- boundary;
- usefulness claim;
- other scientific content.

Implement one of these cleanly:

A. validate that resources-classified mutations touch only explicitly
resource-only fields;

or

B. if classification cannot be proven resource-only, conservatively invalidate
the scientific workspace dependencies actually touched.

Do not implement scientific keyword heuristics.

A user-supplied classification must not override structural evidence that
scientific fields changed.

Add regression:
- Argument review;
- add/change consequential Argument content while declaring resources;
- review must stale.

Also test:
- true resource-only change;
- relevant scientific review remains current where appropriate.

==================================================
5. G3-RERUN-N1
DIAGNOSTIC PLACEHOLDER VALIDATION
==================================================

CURRENT FAILURE

Punctuation variants evade generic-placeholder rejection:

- "Do more research."
- "TBD."

can satisfy required DiagnosticAction fields.

REQUIRED BEHAVIOR

Do not build a broad scientific keyword blacklist.

Instead normalize mechanical placeholder/generic-empty values for validation:

- trim whitespace;
- strip terminal punctuation where appropriate for placeholder detection;
- normalize case;
- reject known structural placeholders such as TBD / N/A-as-placeholder /
  TODO / UNKNOWN when used where a substantive generated field is required;
- reject a generated action whose fields do not contain distinct usable
  diagnostic content.

For model-generated DiagnosticAction require genuinely populated:
- issue/judgment;
- concrete task;
- required input/evidence;
- deliverable;
- outcome/decision branch.

"Do more research." plus "TBD." placeholders must fail.

Manual free-form notes may remain looser if already allowed by the product spec.

==================================================
6. G3-RERUN-N2
HISTORICAL EXPORT STORAGE REFERENCE LEAK
==================================================

CURRENT FAILURE

Historical export still contains:

reviews[].assessment.snapshot.documents[*].original_storage_reference

REQUIRED BEHAVIOR

No portable/user export may contain internal local storage authority/locator
fields anywhere in the nested object graph.

Create a centralized export sanitizer or equivalent invariant rather than
patching only one nesting level.

Strip:
- original_storage_reference;
- local filesystem paths;
- internal storage locators;
- equivalent authority-bearing implementation fields.

Preserve scientific source identity/version/hash/anchor data needed for
reproducibility.

Add recursive/nested export tests.

==================================================
7. G3-RERUN-N3
HEALTH CHECK ON MALFORMED SCHEMA
==================================================

CURRENT FAILURE

A database with an incompatible projects table causes an uncaught:

sqlite3.OperationalError: no such table: workspaces

after schema validation has already failed.

REQUIRED BEHAVIOR

Health is read-only and failure-safe.

Order checks so that:

1. connectivity can be tested;
2. schema compatibility can be tested;
3. deeper integrity queries execute only when their required schema is valid.

If schema is invalid:
- return a structured failed health result;
- use a specific schema/incompatible-store error;
- do not continue into queries requiring absent tables;
- do not emit a raw stack trace as the user-facing result.

Catch underlying DB/OSError classes at the correct boundary while preserving
diagnostic classification.

Add malformed-schema health regressions.

==================================================
8. G3-RERUN-N4
SYNCHRONOUS PROVIDER WORK BLOCKS API EVENT LOOP
==================================================

CURRENT FAILURE

The async API endpoint directly executes the synchronous interpretation/provider
workflow.

During a mocked ~500 ms provider call, a concurrent health request completes
only after ~532 ms.

The DB transaction issue was repaired previously, but blocking remote work still
runs on the API event loop.

REQUIRED BEHAVIOR

Move blocking provider/workflow execution off the API event loop.

Use the project's existing concurrency/runtime architecture and keep the change
small.

Requirements:

- remote/model work must not monopolize the async API event loop;
- concurrent health/read requests remain responsive;
- database ownership/connection safety remains correct;
- no DB connection may be improperly shared across worker threads/tasks;
- frozen context semantics remain unchanged;
- provider call remains outside DB transaction;
- durable usage receipt behavior remains intact;
- idempotency/run lifecycle remains intact.

Do not introduce a distributed task queue or new service architecture.

A bounded thread/offload mechanism or equivalent within the approved modular
monolith is sufficient if correct.

Add a concurrency regression demonstrating:
- provider mock blocks for a controlled interval;
- health request completes independently before provider finishes.

==================================================
9. TEST QUALITY
==================================================

The independent rerun again demonstrated that green implementation tests were
not sufficient.

For every fix above, write a requirement-derived negative regression reproducing
the exact GATE-3 rerun failure.

Minimum permanent tests:

1. gold feature with required empty anchor rejected;
2. gold feature using another feature's anchor rejected;
3. restoration missing intact ref rejected;
4. restoration using degraded variant as intact ref rejected;
5. canonical NOT INSPECTED withholding scores correctly;
6. confident null without abstention state does not score as withholding;
7. imported forged inspection claim demoted/rejected;
8. imported unsupported "SUPPORTED" disposition demoted/rejected;
9. actual ContextPacket contains no forged support metadata;
10. scientific edit labelled resources stales affected review;
11. genuine resource-only edit does not over-stale;
12. punctuation placeholder DiagnosticAction rejected;
13. nested historical storage reference removed from export;
14. malformed schema returns structured health FAIL;
15. provider sleep does not block concurrent health request.

==================================================
10. REGRESSION / GOVERNANCE
==================================================

Preserve:

- rubric v5 unchanged;
- rubric v4 historical artifact unchanged;
- product spec unchanged;
- 16-step roadmap unchanged;
- historical v4 review behavior;
- all resolved GATE-1/GATE-2/GATE-3 findings;
- benchmark split integrity;
- benchmark ordering;
- checker discipline;
- route applicability;
- baseline fairness;
- gold/evaluator separation;
- package-v1 schema/version unless a backward-compatible semantic-validation
  correction is sufficient.

If package-v1 must change incompatibly, do NOT silently mutate its meaning.
Create an explicit schema version decision and explain why. Prefer keeping v1
and strengthening validation if schema shape need not change.

==================================================
11. WORKFLOW
==================================================

1. Verify clean synchronized main at:
   90d0c12aa4ba997991c19cd05acda4e3f68db79a

2. Create a GATE-3 repair branch.

3. Record the rerun findings if not already stored.

4. Fix G3-RERUN-B1 through B4.

5. Fix G3-RERUN-N1 through N4.

6. Run focused reproductions after each fix.

7. Run the full backend suite.

8. Run PostgreSQL CI/parity required by existing governance.

9. Run browser e2e.

10. Run benchmark package validation/import tests.

11. Run benchmark fake Workbench and baseline suites.

12. Run operator/health/backup/export tests.

13. Run type/lint/contracts/publication/governing checks.

14. Commit and push.

15. Integrate to main only if every required check passes.

16. Push main.

17. STOP.

Do not start Step 12.

==================================================
FINAL RESPONSE
==================================================

STATUS: PASS | BLOCKED

ROADMAP STEP:
11/16 — GATE-3 repair

COMMIT:
<final integrated commit>

RERUN BLOCKERS:
- G3-RERUN-B1: RESOLVED/UNRESOLVED
- G3-RERUN-B2: RESOLVED/UNRESOLVED
- G3-RERUN-B3: RESOLVED/UNRESOLVED
- G3-RERUN-B4: RESOLVED/UNRESOLVED

RERUN NONBLOCKERS:
- G3-RERUN-N1: RESOLVED/UNRESOLVED
- G3-RERUN-N2: RESOLVED/UNRESOLVED
- G3-RERUN-N3: RESOLVED/UNRESOLVED
- G3-RERUN-N4: RESOLVED/UNRESOLVED

PACKAGE VALIDATION:
- gold ownership validation: PASS/FAIL
- restoration semantics: PASS/FAIL
- validate-only negative cases: PASS/FAIL

METRICS:
- canonical NOT INSPECTED withholding: PASS/FAIL
- confident null not credited: PASS/FAIL

IMPORT:
- forged inspection metadata blocked: PASS/FAIL
- unsupported support disposition blocked: PASS/FAIL
- working ContextPacket clean: PASS/FAIL

STALENESS:
- scientific resources-bypass blocked: PASS/FAIL
- true resource-only change remains selective: PASS/FAIL

SCIENTIFIC OUTPUT:
- generic/punctuation placeholders rejected: PASS/FAIL

EXPORT:
- nested storage references removed: PASS/FAIL

OPERATIONS:
- malformed schema health failure-safe: PASS/FAIL
- provider work off event loop: PASS/FAIL
- concurrent health remains responsive: PASS/FAIL

TESTS:
- backend passed: ...
- failed: ...
- v5 golden cases: X/16
- browser e2e: ...
- benchmark tests: ...
- PostgreSQL CI: PASS/FAIL

GOVERNING FILES:
- rubric v5 unchanged: YES/NO
- historical rubric v4 unchanged: YES/NO
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
