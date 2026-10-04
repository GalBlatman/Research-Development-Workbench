# ADR 0010: Owner-authorized rubric v5 clarification

GATE-3 repair, step 11/16. The owner resolves ambiguity G3-R1 with the exact inserted route-status semantics in sections 2.2 and 8.5 of rubric-v5.md. Version/date/replaces headers identify this release. Removing those two inserted blocks and reverting those headers recovers v4 text exactly after line-ending normalization. No formula, weight, cap, anchor, dimension, route, stage, premise, study or calibration rule changes. V4 remains byte-identical and historically addressable.

New evaluations use v5 and its manifest/hash. Stored v4 results render without recalculation; historical audits/task contracts continue to name their actual policy. The product spec and 16-step roadmap remain unchanged. No implicit development-needed count is permitted; unknown required inspection takes precedence in the route component. Other submission prerequisites still apply independently.

## Owner-authorized V5 documentation cleanup

The subsequent GATE-3 documentation cleanup corrects active version references, clarifies historical V4 provenance, and replaces Section 18 with the V4-to-V5 change summary. It changes no scientific policy and creates no V6. The exact reversible wording allowlist and before/after document hashes are in `policies/rubric-v5.documentation-edits.json`. The surgical-change regression first reverses those documentation edits, then removes the original two G3-R1 blocks and reverts the release headers to recover V4 exactly. Historical audit records remain unchanged. New evaluations use the updated V5 canonical hash; stored assessments retain their frozen version/hash and are not silently recalculated.
