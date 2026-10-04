Repair the two remaining final GATE-3 blockers.

REPOSITORY

C:\Users\galbl\src\Research-Development-Workbench

CURRENT ROADMAP STEP

11/16 â€” GATE-3

Do not create a new step, phase, sub-stage, or fractional step.
Do not start Step 12.
Do not construct the 50-paper corpus.
Do not modify rubric v5, rubric v4, product spec, or roadmap.

CURRENT AUDITED COMMIT

eaace9f13ab939b6b0f70cdee54eb933fb9668d4

FINAL GATE-3 RESULT

FAIL

Everything except two benchmark-metric blockers passed.

Remaining blockers:

- G3-FINAL-B1
- G3-FINAL-B2

Rubric questions:
NONE

Fix both with one coherent typed-semantics correction.

==================================================
1. ROOT PROBLEM
==================================================

The benchmark currently conflates or incompletely separates:

A. SCIENTIFIC STATE
What the evaluator is saying about the scientific claim.

Examples:
- supported
- unresolved
- needs revision
- contradicted
- not inspected
- not applicable
- blocking
- development needed
- adequate for stage

B. ADOPTION / AUTHORING STATE
What kind of project artifact this is.

Examples:
- proposed
- accepted/adopted
- rejected
- superseded

C. CHECKING / VERIFICATION DISPOSITION
What the Workbench checker concluded about a particular statement.

Examples:
- supported
- unresolved
- needs_revision
- confirmed
- qualified
- withdrawn

These are different axes.

The benchmark expectation and metric layer must not use "proposed" as a
substitute for scientific state or verification disposition.

==================================================
2. G3-FINAL-B1
CHECKED UNRESOLVED STATEMENT + acceptable_states
==================================================

CURRENT FAILURE

A normal Workbench workflow returns:

principal-obstacle checker disposition = UNRESOLVED

With no acceptable-state constraint:
withholding = 1/1

But when the valid expectation says:

acceptable_states = ["unresolved"]

the exact same output receives:

withholding = 0/1
state accuracy = 0/1

Cause:
statement translation keeps:
state = proposed

and stores unresolved only in verification/disposition.

Expectation filtering looks only at "state".

REQUIRED BEHAVIOR

Define explicit typed expectation semantics.

For each observation, expose distinct fields such as equivalent canonical forms
of:

- scientific_state
- adoption_state
- verification_state

Do not overload one `state` field with all meanings.

If backward compatibility requires keeping `state`, define its exact semantics
and do not make it stand for adoption state when the expectation concerns a
scientific/checking state.

EXPECTATION SEMANTICS

A benchmark expectation must specify which axis it constrains.

For example:

acceptable_scientific_states
acceptable_verification_states
acceptable_adoption_states

or an equivalent typed structure.

If the existing benchmark-package-v1 already has acceptable_states, preserve
backward compatibility by assigning it one unambiguous documented meaning and
adding explicit fields where needed.

Do not silently change frozen package meaning.

For a CHECKED Workbench statement:

checker disposition UNRESOLVED
must satisfy an expectation that explicitly permits unresolved verification /
scientific uncertainty.

It must not fail merely because adoption_state == proposed.

WITHHOLDING

Correct withholding must depend on legitimate uncertainty/abstention semantics,
not on whether the statement is adopted.

Examples:

- checked UNRESOLVED -> may receive withholding credit;
- NOT INSPECTED -> may receive withholding credit where expected;
- confident SUPPORTED -> does not receive withholding credit;
- ordinary proposed claim with no uncertainty state -> does not receive
  withholding credit just because it is "proposed".

==================================================
3. G3-FINAL-B2
BASELINE MUST RECEIVE FAIR ABSTENTION CREDIT
==================================================

CURRENT FAILURE

The baseline returns a schema-valid statement explicitly saying the bounded claim
cannot be determined from inspected material.

The baseline has no Workbench checker, correctly.

But withholding receives 0/1 because statement withholding currently requires:

checking_performed = true

That structurally advantages Workbench.

REQUIRED BEHAVIOR

Baseline can express legitimate scientific abstention WITHOUT pretending to have
Workbench verification.

Create a typed scientific uncertainty/abstention representation usable by both:

- Workbench
- baseline

For baseline:

- no fake checking_performed;
- no fake verification;
- explicit scientific_state = unresolved / not_inspected / equivalent where
  supported by the baseline output;
- withholding metric can credit that legitimate abstention.

For Workbench:

- scientific_state and checker verification remain separate;
- checker UNRESOLVED can also legitimately support withholding.

FAIRNESS RULE

The benchmark comparison should ask:

"Did the evaluator appropriately withhold scientific certainty?"

not:

"Did the evaluator have a Workbench checking stage?"

A baseline must not need to imitate Workbench architecture to receive the same
scientific withholding credit.

At the same time:

An unchecked confident proposal must still receive zero withholding credit.

Do not weaken this safeguard.

==================================================
4. TYPED OBSERVATION CONTRACT
==================================================

Implement or clarify one canonical observation model that can represent:

- judgment identity
- scientific value/content
- scientific state
- adoption state, if applicable
- verification/checking disposition, if applicable
- checking_performed
- evidence/source linkage
- evaluator mode: WORKBENCH or BASELINE

Do not create free-form string inference.

Use enums/typed mappings.

The model should support both:

WORKBENCH example:
scientific_state = unresolved
adoption_state = proposed
verification_state = unresolved
checking_performed = true

BASELINE example:
scientific_state = unresolved
adoption_state = proposed or N/A as appropriate
verification_state = N/A
checking_performed = false

Both may receive withholding credit when the expectation is that the scientific
claim cannot be determined.

==================================================
5. EXPECTATION CONTRACT
==================================================

Make expectation constraints explicit by semantic axis.

At minimum support equivalent behavior for:

- acceptable scientific states;
- acceptable verification states;
- forbidden scientific states;
- expected withholding/abstention;
- expected scientific change/no-change;
- expected verification change/no-change where Workbench-only checking is being
  tested.

Do NOT make baseline fail a verification expectation that is explicitly
Workbench-internal unless that case is intentionally testing checker behavior.

For baseline-vs-Workbench comparison cases, scientific expectations must be
architecture-neutral where possible.

If benchmark-package-v1 requires a compatible extension, do the smallest
backward-compatible change.

If an incompatible schema change is unavoidable:
STOP and report BLOCKED rather than silently redefining existing package-v1.

==================================================
6. METRIC RULES
==================================================

WITHHOLDING

Credit when:
- expectation calls for uncertainty/withholding; AND
- scientific_state is an allowed abstention state.

May additionally use Workbench verification disposition where relevant, but
verification must not be mandatory for baseline.

Do NOT credit:
- null value alone;
- proposed adoption state alone;
- missing output;
- confident supported assertion;
- ordinary unchecked proposal.

STATE ACCURACY

Compare expectations against the correct semantic axis.

Do not compare:
acceptable scientific unresolved
against:
adoption_state = proposed.

VERIFICATION METRIC

Keep this separate.

Workbench verification changes should continue to be measured independently.

Baseline can be N/A on internal checker-specific verification metrics.

SCIENTIFIC CHANGE

Keep separate from verification-only change.

A change from:
verification unresolved -> supported
with identical scientific claim
is not automatically a scientific-content change.

==================================================
7. REQUIRED END-TO-END REGRESSIONS
==================================================

Use the actual evaluator translation and metric path, not only direct metric unit
tests.

At minimum prove:

WORKBENCH

1. checker UNRESOLVED + expectation allows unresolved
   -> withholding PASS.

2. checker UNRESOLVED + acceptable scientific/verification state constraint
   -> state accuracy PASS on the appropriate axis.

3. checker SUPPORTED when withholding expected
   -> withholding FAIL.

4. NEEDS_REVISION disposition preserved.

5. adoption_state=proposed does not override legitimate unresolved scientific
   state.

BASELINE

6. baseline explicitly unresolved scientific statement
   -> withholding PASS when uncertainty is expected.

7. baseline unresolved does NOT require checking_performed=true.

8. baseline gets no fabricated verification state.

9. baseline confident proposal with no uncertainty
   -> withholding FAIL.

10. baseline null value without explicit abstention
    -> withholding FAIL.

FAIRNESS

11. Same permitted packet and same scientific unresolved conclusion can receive
    equivalent scientific withholding credit in baseline and Workbench.

12. Workbench checker-specific metrics remain Workbench-specific and do not
    unfairly count against baseline.

EXPECTATIONS

13. acceptable_states legacy behavior, if retained, is explicitly mapped and
    tested.

14. explicit typed acceptable scientific states work.

15. explicit typed acceptable verification states work.

16. forbidden state semantics use the correct axis.

REGRESSION

17. G3-FINAL-B1 exact reproduction now passes.
18. G3-FINAL-B2 exact reproduction now passes.
19. all previous 101 GATE-3 synthetic/adversarial probes remain passing where
    permanently encoded.
20. all 16 v5 golden cases pass.
21. benchmark/package tests pass.
22. fake Workbench 27/27.
23. fake baseline 27/27.
24. browser 11/11.
25. full backend passes.
26. PostgreSQL CI passes with no required skips.
27. lint/type/contracts/build/publication checks pass.

==================================================
8. DO NOT REGRESS
==================================================

Preserve:

- equivalent paraphrase visibility;
- degradation distinction;
- replacement collision protection;
- split integrity;
- gold/evaluator isolation;
- package-v1 validation;
- frozen expectations;
- stable ordering;
- restoration semantics;
- import provenance sanitation;
- staleness;
- checker discipline;
- route applicability;
- provider offload/usage/error handling;
- Next Actions validation;
- v5 documentation integrity;
- historical v4 behavior.

==================================================
9. WORKFLOW
==================================================

1. Verify clean synced main at:
   eaace9f13ab939b6b0f70cdee54eb933fb9668d4

2. Create a GATE-3 repair branch.

3. Record G3-FINAL-B1/B2.

4. Implement the typed observation/expectation semantics correction.

5. Add exact end-to-end reproductions.

6. Run focused benchmark tests.

7. Run full backend suite.

8. Run both fake benchmark modes.

9. Run browser suite.

10. Run PostgreSQL CI/parity.

11. Run lint/type/contracts/build/publication checks.

12. Commit and push.

13. Integrate to main only if all required tests pass.

14. Push main.

15. STOP.

Do not start Step 12.

==================================================
FINAL RESPONSE
==================================================

STATUS: PASS | BLOCKED

ROADMAP STEP:
11/16 â€” GATE-3 repair

COMMIT:
<final integrated commit>

FINAL BLOCKERS:
- G3-FINAL-B1: RESOLVED/UNRESOLVED
- G3-FINAL-B2: RESOLVED/UNRESOLVED

OBSERVATION MODEL:
- scientific state distinct: YES/NO
- adoption state distinct: YES/NO
- verification state distinct: YES/NO
- baseline abstention representable without fake checking: YES/NO

EXPECTATIONS:
- scientific-state constraint typed: PASS/FAIL
- verification-state constraint typed: PASS/FAIL
- legacy acceptable_states unambiguous: PASS/FAIL

WITHHOLDING:
- Workbench unresolved gets correct credit: PASS/FAIL
- baseline unresolved gets correct credit: PASS/FAIL
- confident proposal not credited: PASS/FAIL
- null without abstention not credited: PASS/FAIL

BASELINE FAIRNESS:
- scientific withholding architecture-neutral: PASS/FAIL
- no fake verification required: PASS/FAIL
- checker-specific metrics remain separate: PASS/FAIL

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

BLOCKERS:
- none
or
- ...

NEXT:
GATE-3 independent rerun ready: YES/NO

Do not start Step 12.
