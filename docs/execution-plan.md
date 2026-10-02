# Research Development Workbench: execution plan

**Version:** 1.0, October 2, 2026  
**Status:** Proposed execution policy for owner approval. No repository changes have been made by producing this document.  
**Repository:** `GalBlatman/Research-Development-Workbench`  
**Governing product document:** `Research_Development_App_Spec_v1.md`  
**Governing research policy:** `Research_Idea_Rubric_v4.md`

## Contents

1. Operating decision and first useful release
2. Separate public software, reference materials, and runtime data
3. Local environment and safe bootstrap
4. Authority, roles, and approval boundaries
5. Minimal project-management system
6. Architecture and executable boundaries
7. Build sequence and exit gates
8. Task contracts and session protocol
9. Testing and research-quality evaluation
10. Public-repository and CI controls
11. Versioning, releases, and recovery
12. Initial backlog and immediate next action
13. Evidence basis and source limitations

## 1. Operating decision and first useful release

Build the existing specification incrementally. Do not restart product design, treat the interface mockup as production code, or ask a coding agent to implement the full specification in one session.

The first useful release completes this loop:

> Submit an idea and a small authorized literature packet; inspect the app's interpretation; receive a source-linked assessment under v4; adopt a bounded action; revise the project; obtain an assessment that recognizes the change while retaining the original record.

First prove a smaller end-to-end slice with synthetic material and a fake model. Then connect one real model under explicit cost and data-processing limits. A fake model validates application behavior, not research judgment.

The public code repository is not a public manuscript service. The first usable deployment remains private and author-facing. Public signup, subscriptions, external literature discovery, autonomous agents, arbitrary code execution, broad disciplinary coverage, and statistical analysis of uploaded datasets remain outside this first release.

Success means accurate source interpretation, useful issue identification, appropriate rubric behavior, and actions worth doing. Report length, number of screens, number of agents, or a rising rubric score are not sufficient success measures. [P, §§1, 21–23]

## 2. Separate public software, reference materials, and runtime data

Use three locations with different purposes.

| Location | Purpose | Treatment |
|---|---|---|
| Public Git checkout | Code, tests, approved first-party documentation, reviewed policy files, synthetic examples | Versioned and publishable only after review |
| Existing reference folder | Papers, Markdown conversions, builder exports, source screenshots, original planning files | External to Git; preserve and treat as read-only |
| Private runtime/evaluation directory | Uploads, extracted text, model responses, reports, local configuration, private evaluation cases | External to Git; restricted, explicit retention and backup rules |

Existing reference folder supplied by the owner:

```text
C:\Users\galbl\OneDrive\מסמכים\Postdoc\Projects\Research Ideas Rubric
```

Proposed WSL locations, subject to the read-only environment check:

```text
~/src/research-development-workbench/          # builder's code checkout
~/src/research-development-workbench-review/   # separate reviewer checkout when needed
~/.local/share/research-development-workbench/ # private runtime data, not a Git checkout
```

Do not initialize Git in the reference folder. Do not clone into it. Do not place it inside the code checkout or use a symlink to make the whole library appear inside the checkout. Resolve its mounted path locally rather than assuming the Windows path is directly usable in Linux.

Before the first public push, approve an explicit publication list. Normally eligible: original application code, tests using synthetic content, public bibliographic references, and reviewed first-party documents. Not eligible by default: journal PDFs, their Markdown/text conversions, builder exports, source screenshots, unpublished research, private evaluation examples, credentials, extracted text, logs, and live model outputs.

The supplied articles include redistribution restrictions. Conversion to Markdown does not make an article suitable for publishing in the repository. Keeping a paper outside Git does not itself authorize every use by a model provider. [S]

The app specification and rubric can become tracked policy/design files only after owner review of their publication scope. Preserve the reference originals. Remove private paths or other private material from publishable derivatives only through an explicit, documented change; do not silently change research policy.

Use environment variables or local configuration for the external reference and runtime roots. Commit examples containing placeholders, not the owner's absolute paths. A private inventory may contain filenames and hashes; a public bibliography should contain only information cleared for publication.

A `.gitignore` is a convenience, not a confidentiality boundary. Git ignores do not affect already tracked files. Use separation, explicit staging, local checks, and public-tree review together. [T2]

**Licensing is an owner decision.** A public repository is not automatically an open-source licensing grant. Do not let scaffolding tools choose MIT, Apache, Creative Commons, or a license for third-party materials without approval. Until selected, describe the licensing decision as pending without claiming that public visibility keeps content confidential. [T3]

## 3. Local environment and safe bootstrap

### Environment

Use the owner's Windows/WSL development approach, with Linux development files in the WSL filesystem. Microsoft recommends keeping files in the filesystem of the tools being used for performance. The decision to keep the checkout outside OneDrive also gives this project a clear separation between code and references. It is not a claim that Git cannot run in a synced folder. [T1]

Inspect first: current working directory, any existing checkout, Git status and remote, WSL availability, Python and `uv`, Node and the selected frontend package manager, and Docker/PostgreSQL availability. Do not install, upgrade, or reconfigure anything during onboarding.

Use an isolated `uv`-managed Python environment and a committed lockfile once compatibility is checked. Pin the interpreter and frontend toolchain in repository configuration. Choose one frontend package manager and one lockfile. Do not install project dependencies globally. Dependency installation requires its own authorized setup task; the setup task may then run without approval for every package already listed in its agreed scope.

### Bootstrap sequence

1. Complete Task RDW-000, read-only onboarding. Report, then stop.
2. Owner approves paths, publishable files, the first milestone, and the next bounded task.
3. Create or clone the dedicated code checkout if absent. Do not overwrite a nonempty directory or replace a different remote.
4. Prepare minimal repository controls and approved documentation. Review the exact staged list and diff.
5. Because the remote starts empty, create the initial `main` through one explicitly authorized seed commit/push. This is a recorded bootstrap exception, not ongoing permission for direct pushes.
6. Configure PR and status-check requirements as soon as the first branch and checks exist. All later substantive work goes through task branches and reviewed PRs.

No cloud deployment, model-provider calls, or bulk corpus ingestion belongs in bootstrap. Local execution of a coding assistant does not imply offline inference; source-reading scope and provider exposure still require care.

## 4. Authority, roles, and approval boundaries

### Authority

Research policy: the frozen rubric v4 plus the reviewed executable interpretation. Product behavior: the application specification. Engineering decisions: accepted architecture decision records. Current work: one approved task contract. Chat messages and generated suggestions become authoritative only when the owner accepts the relevant change into the record.

A checksum detects a changed file; it does not prove the change is correct. Compare canonical bytes and explain any line-ending or encoding differences before accepting a new baseline. The baseline files inspected for this execution plan have these SHA-256 values:

```text
Research_Idea_Rubric_v4.md
  a94c195f1f95547cad00d9f2bdcd384cca58ae85bf40646d4b36146379b8f26d
Research_Development_App_Spec_v1.md
  a5eaffb4ac19207e3d0fa8a1ec704792678934d6c5479a95b9bb16421797eeb6
```

These are hashes of the conversation copies, not a verification of the owner's Windows folder. RDW-000 compares the local copies.

### Roles

| Role | Responsibility | Does not control |
|---|---|---|
| Owner | Product priorities, research rulings, publication permissions, expenditure, consequential architecture choices, merge/release acceptance | Cannot establish scientific truth simply by accepting a suggestion |
| Planning/review assistance | Turn approved goals into bounded tasks; analyze risks and evidence; help adjudicate design choices | Does not silently modify the repository or approve changes on the owner's behalf |
| Codex | Default builder: implement the current task, run checks, explain changes, report and stop | No automatic scope expansion, policy changes, merge, deployment, or permission escalation |
| Targeted independent reviewer | Fresh review of a specified commit for a high-risk boundary or unresolved failure; Claude Code is one available choice | No simultaneous editing of the builder's checkout; no routine second implementation of everything |
| CI | Enforce deterministic tests, contracts, import rules, and publication checks | Does not certify scientific merit or complete security |

Use one active implementation task at a time initially. Independent review is especially useful for policy interpretation, evidence-state transitions, authorization, schema migrations, and unresolved research-judgment failures. Do not make every trivial UI edit a two-model ceremony.

Use separate checkouts for builder and reviewer when both are active. Reviews name the exact commit SHA. The reviewer may run tests in its own environment, but proposed source changes go back as findings unless assigned a separate bounded fix task. Owner retains final acceptance.

### Decisions requiring explicit approval

A change to rubric semantics; a new model/provider; a new external service or network destination; nontrivial dependencies; migrations affecting stored data; privacy or retention changes; broader filesystem/tool access; additional expenditure; publication of source material; opening access to another person; merging or deployment.

Routine edits and tests already inside an approved task need not trigger repeated approval prompts. Stop when a genuine boundary is crossed, not after every line of code.

## 5. Minimal project-management system

Use the existing specification rather than duplicating it into a second large requirements document. Maintain:

| Record | Purpose |
|---|---|
| `README.md` | Current status, what works, how to run the current slice, boundaries |
| `docs/product-spec.md` | Approved copy/reference of the application specification |
| `policies/rubric-v4.md` and manifest | Research policy and its executable representation |
| `docs/architecture.md` | Module ownership and allowed dependencies |
| `docs/decisions/` | Short accepted decisions and explicit supersessions |
| `docs/acceptance-cases.md` | User journeys and failure conditions that define success |
| `AGENTS.md` | Concise coding-agent operating rules and links to authority |
| GitHub issues and PRs | Scoped tasks, evidence, decisions, and delivery history |

A reviewer-specific instruction file may point to `AGENTS.md`; it must not become a conflicting second policy. Verify instruction loading rather than assuming every tool uses the same file automatically. Codex documents repository instruction discovery via `AGENTS.md`. [T6]

A small board is enough: Backlog, Ready, In progress, Review, Done, Blocked. Work-in-progress limit: one builder task. Keep later ideas in Backlog, not in the current task's acceptance criteria.

Each milestone has one user outcome and an exit gate. Each task links to a specification section, a permitted module boundary, and acceptance tests. Do not track progress as percentage of folders created. Track demonstrated behavior, open risks, and time/cost consumed.

After each milestone, decide continue, simplify, change direction, or stop. Estimate later work from actual throughput; do not promise a complete launch date before the first functioning slice is measured.

Public issue/PR text must use synthetic examples and generic project IDs. Private research judgments and logs belong in the private evaluation record, not pasted into GitHub discussions.

## 6. Architecture and executable boundaries

Retain the specified modular monolith: React/TypeScript interface, Python/FastAPI backend, PostgreSQL, private file storage, and a separately running worker using the same domain code when durable processing becomes necessary. [P, §13]

The module map in the specification is an ownership map, not a demand to create every empty folder now. Implement only the boundaries needed by the current slice.

| Module | Owns | Must not do |
|---|---|---|
| Domain | Project objects, status types, provenance, snapshots, change semantics | Depend on HTTP, database drivers, or model SDKs |
| Policy engine | Exact eligibility, totals, caps, profile checks, rule traces | Perform network/model calls or accept arbitrary executable rules |
| Source/ingestion | Originals, parsed text, anchors, coverage records | Invent readable text or label uninspected content as inspected |
| Retrieval | Scope-limited context from authorized source versions | Search across projects based on an LLM-supplied identifier |
| Workflow | Stage sequencing, budgets, retries, cancellation, run state | Let model prose select arbitrary actions or permissions |
| Model adapter | Typed provider calls, usage, provider error mapping | Hold database credentials or choose arbitrary files |
| Verification | Quote/anchor checks and targeted semantic assessment | Treat quote accuracy as proof of scientific truth |
| Reports | Display verified judgments and calculated results | Recalculate grades or silently edit ratings |
| History/actions | Changes, action branches, resolution evidence, stale judgments | Treat task completion as proof the scientific objection is resolved |
| API/UI | Authorized requests and views | Embed a second scoring engine |

Enforce dependency direction with tests or static import rules. Document and test exported interfaces; generate browser contracts from server schemas where practical. Do not hand-maintain competing versions of the same contract.

The most important state invariant is:

> Origin, user adoption, evidence status, and freshness are different properties.

Accepting a model proposal does not change its evidence status to verified. Saving a new revision does not mutate an older evaluation snapshot. A document with unreadable sections cannot support a claim of complete inspection. A model score proposal is not a final score until validation and policy application have completed.

### Minimal initial architecture decisions

Record only real choices: code/reference/data separation; policy and schema ownership; module dependency direction; synthetic/fake-provider first slice; staged admission of documents and paid model calls. Provider, hosting, and external search decisions remain pending until needed.

One rollout refinement needs owner approval: minimal budgets, timeouts, scope restrictions, and safe logging must precede the first live model request or private upload. The full durability and hosting controls can remain in the later reliability stage. This clarifies rollout order without changing research policy.

## 7. Build sequence and exit gates

| Milestone | Deliverable | Exit gate |
|---|---|---|
| M0: Safe foundation | Read-only onboarding, clean checkout, publication boundary, minimal docs and test command | Known environment; no corpus in Git; approved plan; meaningful baseline checks run |
| M1: Rules and record | Typed objects, provenance/status axes, snapshots, pure v4 engine | Exact conformance fixtures pass; no hidden network; pending/inapplicable preserved |
| M2: Thin end-to-end slice | A synthetic idea and synthetic literature go through input, snapshot, fake provider, verification, report, and export | One complete visible flow; source links work; incomplete/invalid responses fail honestly |
| M3: Real research assessment | One provider, authorized small packet, bounded context and budget, evaluation harness | Source claims inspected; provider failures handled; comparison against simple-prompt baseline recorded |
| M4: Development loop | Correct an interpretation, act on an objection, revise, reassess | New review recognizes actual change; original remains intact; no automatic truth promotion |
| M5: Private pilot | Formats, workspaces, durable jobs, deletion, restore, permission/cost controls | Failure tests and private-use review pass; known critical problems resolved |
| M6: Invited use | Tested isolation, onboarding/rights rules, support, retention | Another person cannot retrieve owner's content; deletion survives restore; explicit owner release |

M2 should use only the few screens needed to demonstrate the loop. The broader workspaces in the mockup are a roadmap, not simultaneous construction tasks.

Text and Markdown can precede PDF and DOCX parsing. This is an engineering staging choice, not a permanent product exclusion. Each parser is admitted only after its source-location and failure handling tests pass. No silent OCR or implied table inspection.

M3 must test substantive usefulness before M4/M5 polish consumes most effort. Avoid spending months constructing generic infrastructure for a reviewer that has not yet passed a small source-interpretation test.

## 8. Task contracts and session protocol

### Before implementation

A task is Ready only when its outcome, relevant specification, allowed files/modules, exclusions, interfaces, and acceptance checks are known. Unresolved product choices are not invitations for the coding agent to guess.

Reusable task format:

```text
TASK ID AND TITLE:
USER OUTCOME:
AUTHORITY: specification/rubric sections and accepted decisions
BASE COMMIT / BRANCH:
ALLOWED MODULES AND FILES:
INPUT / OUTPUT CONTRACT:
IN SCOPE:
EXPLICITLY OUT OF SCOPE:
DATA CLASSIFICATION / PERMITTED SOURCES:
NETWORK / PROVIDER / SPEND PERMISSIONS:
ACCEPTANCE CASES: normal, boundary, and failure behavior
TEST COMMANDS:
POLICY / SCHEMA / PRIVACY IMPACT:
STOP CONDITIONS:
REQUIRED HANDOFF:
```

### The working loop

Orient to current repository state. Reproduce the baseline. Explain the bounded plan. Implement only that plan after authorization. Run tests and inspect the diff. Report evidence and stop. After owner review, merge the authorized PR. Start the next task from the current accepted baseline.

Do not automatically pull, stash, reset, rebase, or overwrite a dirty working tree to make onboarding succeed. Report it and resolve it explicitly. A task-specific branch belongs to the current task, not a permanent branch for a particular model.

### Handoff required from the builder

State the branch and commit; task outcome; changed modules and why those modules own the behavior; exact tests run and results; tests not run; a simple demo command; changes to prompts/rules/schemas; risks and unresolved decisions; and confirmation that restricted materials were not added.

A claimed test result is not evidence unless a command was run and its outcome recorded. Label omitted tests as not run. Do not declare the milestone complete solely because the coding agent says it is.

### Scope changes

If a new concern belongs to another module, propose a separate task or a revised contract. Do not opportunistically add new services, frameworks, statistics, score conversions, agents, or screens. Small fixes necessary to complete the stated outcome may be included only when their impact stays inside the approved boundaries and the handoff explains them.

## 9. Testing and research-quality evaluation

Keep four kinds of checks distinct.

**Policy conformance:** independently specified cases for scores, rounding, caps, eligibility, pending states, contribution routes, readiness, and incomparable development branches. Use the v4 text and reviewed examples as the oracle, not the implementation itself. Never change expected results merely to make a failing implementation pass.

**Application behavior:** snapshot immutability, provenance, acceptance without truth promotion, authorized retrieval, import/export round trips, duplicate-click behavior, cancellation, missing sources, and honest partial failure. Include integration tests against PostgreSQL when persistence is introduced rather than relying entirely on in-memory doubles.

**Security/publication:** staged-file review, secret scanning, public-tree checks, permissions, malicious documents, output escaping, source deletion, late-job publication, and restore behavior. Local hooks are bypassable and CI runs only after code is sent to the remote; neither replaces keeping sensitive content outside the checkout.

**Research judgment:** authorized examples with human notes on the contribution, relevant predecessor, valid/invalid objections, and reasonable action families. Include sound cases, not only flawed work. Check source accuracy, false blocking objections, missed important issues, preserved insight, and recognition of repairs.

Public fixtures should be independently authored synthetic research and literature. Synthetic papers need prominent fictitious labels; do not invent real DOIs or authors to make them appear published. Private evaluation examples stay outside public source control, CI logs, and artifacts.

Split development examples from held-out cases. Keep detailed holdout labels out of the builder's working context and out of prompts used by the app. Once a case is used for debugging, treat it as development material and add a new untouched case. Do not call repeated agreement by models independent human validation. [P, §21; T8]

Compare the workflow to a simple application of v4 using the same model and source packet. Record differences in processing and cost. Add complexity only when it improves the identified failure or materially improves the user workflow.

A prompt, context-selection rule, model version, parser, schema, or rubric change can alter the result. Each needs the tests relevant to that impact. Reusing stored outputs makes deterministic report replay possible; it does not guarantee that a new model call will reproduce the same assessment.

## 10. Public-repository and CI controls

After the initial authorized seed push, use short-lived task branches and PRs. Keep `main` releasable for the current declared slice, with passing required checks, resolved review conversations, no force pushes or deletion, and no routine bypass. GitHub supports these protections; verify actual settings after configuration. [T4]

**Single-maintainer caveat:** PR authors cannot approve their own PRs. If Codex and owner publish through the same GitHub identity, requiring an additional approving reviewer can deadlock delivery. Require PRs and checks now, record the owner's manual review/merge decision, and add a required independent reviewer when a genuinely separate authorized reviewer exists. Do not create a rubber-stamp identity to evade this. [T5]

`CODEOWNERS` documents sensitive paths and can support review routing. It is not an automatic, universal human-approval guarantee. Configure it consistently with the actual maintainer arrangement.

Proposed CI checks, activated when the relevant code exists:

| Check | Purpose |
|---|---|
| `repo-policy` | Required files, approved tracked paths, disallowed generated/private artifacts, canonical policy checks |
| `backend-quality` | Formatting/lint, typing, unit and contract checks |
| `rubric-conformance` | Exact rule and boundary cases |
| `architecture-boundaries` | Forbidden dependency/import checks |
| `frontend-quality` | Typecheck, tests, build when a frontend exists |
| `integration` | Real persistence and API behavior when introduced |
| `smoke` | End-to-end synthetic flow with fake model |
| `security` | Secret/dependency checks and relevant security regressions |

Never show placeholder jobs as passed tests for behavior not implemented. Introduce checks with real assertions. Keep required job names stable and avoid a matrix entry that skips all meaningful tests yet reports success.

Public CI has no private research corpus and no model-provider key. Paid/live evaluation is an owner-triggered separate process, initially local, with an approved budget and private outputs. It is not triggered by arbitrary pull requests.

Use least-privilege workflow tokens, trusted pinned action revisions, reviewed dependency locks, and no privileged execution of untrusted PR code. Do not run public-repo contributions on a self-hosted runner that can access the owner's papers or credentials. These controls reflect GitHub's secure-use guidance. [T7]

If a secret is published, revoke/rotate it and investigate; deleting the visible file is not sufficient. If restricted documents are accidentally published, stop further publication and handle the incident rather than assume a history edit retrieves existing copies.

## 11. Versioning, releases, and recovery

Keep research policy version, executable-policy revision, application version, prompt versions, parser version, model identifier, and project revision separate. Persist the relevant identifiers with each run. A prompt change must not silently reinterpret historical evaluations.

At a release gate, demonstrate the current loop from a clean checkout, using locked dependencies and synthetic inputs. Tag the accepted release only after owner approval. Store a brief changelog and known limitations. Do not treat tags as a substitute for backups or data migrations.

Back up private runtime data separately from Git. Test a restore and deletion behavior before relying on it for confidential research. Migration changes require a forward plan and a recovery approach; do not assume every destructive migration has a trivial rollback.

Track observed time/cost, failed or repeated tasks, source coverage problems, and research-evaluation errors. Operational logging should use IDs and counts rather than document text or raw provider payloads.

## 12. Initial backlog and immediate next action

These IDs are proposed task identifiers, not claims that GitHub issues have been created.

| ID | Task | Main exclusions |
|---|---|---|
| RDW-000 | Read-only onboarding and publication-boundary report | No filesystem/repo writes, installs, pushes, or app-model calls |
| RDW-001 | Approved minimal bootstrap, first-party publication list, instructions, checks | No source corpus import, no application features, no invented license |
| RDW-002 | Core contracts and independent state axes | No database or LLM shortcuts |
| RDW-003 | Pure v4 rules and conformance fixtures | No altered rubric, no acceptance probabilities |
| RDW-004 | Text/Markdown source versions and anchors | No bulk ingestion, OCR, external search, PDF/DOCX claims |
| RDW-005 | Minimal persistence and evaluation snapshots | No mutable historical reviews |
| RDW-006 | Fake-provider end-to-end flow and minimal browser view | No live keys, no full UI implementation |
| RDW-007 | Research-evaluation harness and source-comparison fixtures | No private material in public tests, no fabricated ground truth |
| RDW-008 | One live provider with bounded context, cost, and failures | No uncontrolled retries, browsing, or automatic upgrades |
| RDW-009 | Revision/action loop with targeted reassessment | No automatic strengthening or wholesale rewrite |

RDW-007's case design can begin as soon as the initial contracts are clear. Its execution depends on the review path. RDW-008 is not ready until the source, snapshot, fake-workflow, and budget checks pass.

**Immediate action:** Save the existing app specification and mockup alongside the v4 rubric in the reference folder if they are not already there. Run the separate RDW-000 prompt in the local coding environment. It returns an inventory, environment report, unresolved decisions, and a proposed RDW-001 plan, then stops. Its output is for the owner, not automatic publication to GitHub.

## 13. Evidence basis and source limitations

This document is a proposed engineering execution plan. It does not claim that the scholarly papers prescribe GitHub settings, tools, or release gates.

**[P]** Research Development Workbench, Product, interaction, and technical specification 1.0, October 2, 2026. Especially §§1–2, 13–14, 21–25. Supplies the product scope, module boundaries, state distinctions, build stages, and change requirements. The research rubric v4 remains the research-policy authority.

**[S]** Rights notices in supplied source papers, including Grant and Pollock (2011) and Wickert et al. (2021). They are the basis for not bulk-publishing the reference collection, not a comprehensive legal opinion about every possible use.

Primary technical sources checked October 2, 2026. Recheck settings and provider rules at implementation:

- [T1] Microsoft Learn, Working across Windows and Linux file systems. Recommends storing project files in the filesystem of the tools used.
- [T2] Git documentation, gitignore. Ignored-file rules do not affect already tracked files.
- [T3] GitHub Docs, Licensing a repository. Public visibility and licensing are distinct; public content can be viewed/forked.
- [T4] GitHub Docs, Managing a branch protection rule; About protected branches. Required PRs/checks and protection behavior.
- [T5] GitHub Docs, Approving a pull request with required reviews. PR authors cannot approve their own PRs.
- [T6] OpenAI/ChatGPT Learn, Custom instructions with AGENTS.md. Instruction discovery is a mechanism for supplying guidance, not a substitute for permissions or tests.
- [T7] GitHub Docs, Secure use reference for GitHub Actions. Least privilege, immutable action pins, and untrusted-code risks.
- [T8] OpenAI API documentation, Evaluation best practices. Task-specific testing and human calibration.
- [T9] NIST SP 800-218, Secure Software Development Framework version 1.1. General support for integrating security into the development lifecycle rather than adding it only at release. This plan is not a claim of SSDF certification or complete implementation.
