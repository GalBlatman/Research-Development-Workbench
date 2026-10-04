# Administrator benchmark-package-v1 handoff

This is the public software exchange contract for a separate private corpus-builder repository. It contains no corpus, paper text, scientific gold, private mutations, or results. Separate Git histories are required. Do not place builder artifacts in this repository. Step 12 has not begun.

The machine schema is `evals/benchmark-package-v1.schema.json`, generated from `domain.benchmark.BenchmarkPackage`. The root has `schema_version`, `manifest`, `projects`, `variants`, and `expectations`. Every variant has one frozen expectation artifact, including an explicit empty tuple when no comparison is planned. Missing/extra JSON fields and unknown controlled states fail validation. Tuples serialize as ordered JSON arrays. Source-package block tuple order is canonical presentation order; hashes never sort source passages.

## Identities and hashes

Hash algorithm: SHA-256 of UTF-8 JSON with recursively sorted object keys, no ASCII escaping, compact separators `,` and `:`, and ordered arrays. Pydantic contracts use `model_dump(mode="json")` before serialization. Unicode is preserved without normalization. Hashes do not depend on pretty-print whitespace.

The frozen manifest records full project hashes and permanent `(paper ID, package ID, source-content hash, split)` assignments. Source-content identity hashes the ordered `(role, text)` block pairs, excluding administrator IDs, gold, expectations and split labels. Paper IDs, package IDs, content identity and original split remain bound across every stored manifest version. Identical underlying content cannot acquire another paper ID, package ID or split. New manifest versions may add genuinely distinct packages and update annotations on unchanged permanent identities; they cannot reassign a held-out paper or overwrite prior artifacts. Canonical project hashes still bind all administrative annotations and package version. Variants bind full package and manifest hashes, and their version equals the project version. Expectations bind the exact variant hash and cannot be edited after freezing.

## Controlled vocabulary and semantic validation

Routes, stages, splits, features, transformations, evidence states and judgment states are schema enums. Judgment keys are `rating:1` through `rating:10`, `finding:<governing rule ID>`, `route:<governing route item>` or `statement:<attributed statement ID>`. Canonical numerical judgment states are lowercase (`assessed`, `pending`, `not_applicable`, `conditional`, `contested`, `unresolved`). Truth and route qualitative states retain their contract spelling. Explicit historical uppercase numerical aliases are normalized on input; arbitrary spelling/case variants are rejected.

Gold anchors name source-package block IDs. Gold features and mutation targets must be owned by supplied blocks. Replacement roles/feature ownership must match their original position; shared ownership losses remain explicit in visibility. Parent and intact/degraded comparison references must belong to the same permanent paper/split. Packet text, visibility and packet hash are regenerated from the declared mutation and compared before import. Unknown anchors, duplicate identities, forged hashes, cross-paper parents and contradictory version bindings fail before registration. Code checks declared structure and identity; it does not invent scientific judgments or certify paraphrase equivalence.

Restoration expectations name both an intact reference and a degraded reference. Successful restoration requires an actual prior scientific change and return to the intact judgment. Verification-only differences have their own metric. Upgrade is not downgrade. Failed/interrupted runs remain visible; variants remain nested within papers and configuration/prompt groups, and duplicate reruns are excluded explicitly.

## Validate and import

From `backend`, with the approved locked uv environment:

```powershell
uv run --locked python -m benchmarks --package C:\private-builder\package.json --validate-only
uv run --locked python -m benchmarks --package C:\private-builder\package.json --output C:\private-runtime\benchmark-import
```

Validation makes no provider calls and writes no administrator artifacts. Import stores immutable administrator artifacts and returns without evaluation. Paths must be outside the publication repository. A separate explicit runner uses only stored frozen manifests, projects, variants and expectations. The existing synthetic smoke command without `--package` remains fake-only.

## Capability boundary

The administrator holds papers, gold, mutation definitions, splits and expectations. It passes only `BlindPacket` into `BlindEvaluator`: neutral packet ID, route/stage and ordered visible `(role, text)` blocks. The evaluator creates an isolated normal Workbench context with no builder path, administrator store, hidden block, feature map, expectation, gold, split label or sibling content. The provider rights declaration is neutral. Physical builder separation and normal application capabilities prevent access; arbitrary malicious Python with operating-system file access is outside this capability claim. Administrator files never enter ordinary project exports.

Before execution, reservations consume conservative budgets. An orphan reservation is reported and stored as `INTERRUPTED_UNCERTAIN`; it is never silently retried. Malformed cases generate administrative invalid-case reports without aborting unrelated cases or entering scientific metric denominators.

## GATE-3 rerun semantic correction

The v1 JSON shape and machine schema remain unchanged. All currently defined gold features require distinct nonempty block anchors owned by that feature; no anchor-free gold feature type exists. A metadata-only block cannot own scientific features. Shared blocks may explicitly own multiple distinct features.

Every controlled-restoration target requires a restore expectation with both references. The degraded reference must be the declared predecessor and must withhold that target; the intact reference must expose that target and differ from both predecessor and restoration. Regenerated restored packets must expose the target and differ from their predecessor. These checks validate declared structure, not scientific paraphrase equivalence. Validate-only and import both enforce them before writing any artifacts.

## Equivalent replacement and observation semantics

The private builder will decompose and paraphrase scientific material, retaining original papers and gold anchors privately. Blind packets contain authorized neutral representations, not direct paper access. INTACT_BLIND and METADATA_BLINDING replacements explicitly mean administrator-certified equivalent anonymization/paraphrase. Code checks ownership and role, never scientific equivalence. Such replacements retain intact feature visibility and observability, and never receive degradation or hidden-content status merely because they replace text.

CONTROLLED_DEGRADATION explicitly substitutes weaker scientific content. `visibility` records availability of the original intact feature; it remains false for a degraded target, preserving historical restoration semantics. Administrator-side `observability` additionally records an exposed degraded substitute. It is derived from the declared transformation, replacement feature ownership and metadata permission, without changing the v1 exchange shape. Hiding removes the target entirely. Neither map reaches the evaluator. Restoration can compare against an equivalent anonymized intact reference.

Degradation replacements are ordered one-to-one with the affected original source blocks in canonical source order. This position declares the target block; each replacement's features explicitly declare its target ownership and must remain within that position's targeted features. Replacement IDs must be distinct and must not collide with untouched block IDs. A fresh ID is permitted; unrelated IDs, positions and feature visibility stay unchanged. Construction and package validation reject violations rather than repairing them.

Observed statements retain text, statement kind, proposed adoption and uninspected evidence separately from checking disposition and source anchors. A supported check is not adoption or scientific truth certification. Explicit unresolved checks can receive withholding credit; an unchecked proposed statement alone cannot. Scientific-change signatures preserve the assertion content/value/kind for statements and scientific state/value/content for other judgments; verification changes are reported separately. Baseline statements are observed through the same translation but are not required to run Workbench checking, and cannot acquire fabricated checks.

## Additive scientific/adoption/checking axis extension (G3-FINAL-B1/B2)

New observations expose `scientific_state`, `adoption`, `verification`, `checking_performed`, and `evaluator_mode` separately. For current observations `state` is a compatibility alias of `scientific_state`, never adoption. Historical observations and saved results are not rewritten: their original `state` and verification fields remain readable, including historical `proposed` states. Legacy `acceptable_states`/`forbidden_states` continue to constrain the observation state, with current state translation corrected to scientific state. Use explicit adoption constraints to test adoption; `proposed` is not a valid new scientific state.

The package-v1 schema adds optional `acceptable_scientific_states`, `forbidden_scientific_states`, `acceptable_verification_states`, `forbidden_verification_states`, `acceptable_adoption_states`, `forbidden_adoption_states`, and `verification_change` (`changed`/`unchanged`). Absent extension fields are omitted on canonical serialization, preserving old package/expectation JSON and hashes. Present constraints enter canonical hashes and frozen expectations normally. No existing saved expectation or result is migrated or recalculated. New run metadata already binds the implementation commit. The additive schema accepts all prior v1 packages; builders using the optional extension require the updated validator.

Scientific legacy and explicit constraints are conjunctive and feed `state` accuracy. Verification and adoption constraints have separate `verification_state` and `adoption_state` accuracy metrics. Workbench-only expected checker changes feed `verification_expectation`; raw `verification_change` remains independent. Baseline verification is null/N/A, checking is false, and checker-specific accuracy/change metrics have denominator zero, rather than a failure. Explicit verification constraints cannot silently become baseline scientific requirements.

Statements use only typed classification/disposition mappings, never text or keyword inference. An explicit existing statement kind `unresolved` maps to scientific uncertainty in either mode. A performed checker maps its supported/unresolved/needs_revision disposition into the bounded assessed scientific status while preserving the actual disposition separately. An ordinary unchecked inference/proposal is `assessed` (an assertion was made), not an abstention or independently verified fact. Adoption remains proposed and evidence remains not inspected in every case. A null value alone earns no withholding credit. A supported or needs-revision statement is not automatically abstention.

Withholding tests legitimate scientific abstention and the relevant scientific constraints; a checker is not required. Workbench verification constraints apply only where that checker exists. For attributed statements, scientific-change signatures compare original assertion content/value/kind; a checker-only epistemic status change does not rewrite that assertion. Other judgment types retain their scientific state/value signatures. Content edits and explicit changes in assertion classification remain detectable. Restoration and invariance compare the same signatures, and aggregation reports the scientific, verification and adoption metrics separately.
