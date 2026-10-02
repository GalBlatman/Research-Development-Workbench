# Research Development Workbench
## Product, interaction, and technical specification 1.0

**Date:** October 2, 2026  
**Evaluation authority:** Research Idea Evaluation and Development Protocol, Version 4  
**Release described:** Private pilot, with explicit boundaries for later expansion  
**Status:** Proposed build specification. This is not an implemented or validated application.  
**Companion:** `Research_Development_App_Wireframes.html`, a browser-viewable interface mockup with fictional content and no model connection.

## Executive decision

Build a private, browser-based research workspace. A researcher starts with a description or draft, adds the literature they want examined, and states the decision they need help making. The app proposes a structured interpretation, lets the researcher correct it, evaluates an explicit snapshot under v4, and returns a source-linked review and a bounded development plan.

**Default input is a few substantial inputs, followed by selective correction. It is not a mandatory form for every rubric field, and it is not an autonomous system that fills missing scientific content as fact.** Experienced users may enter structured information directly. The same project record supports both paths.

**The engines are a document and source service, a retrieval service, a bounded LLM workflow, a deterministic rubric rules engine, an assessment-checking stage, a planning module, and a version/dependency service.** These are modules of one application, not seven microservices or seven independent AI agents.

The language model interprets and evaluates. Application code handles permissions, state, calculations, prerequisites, budgets, and versioning. The researcher controls the intended argument and whether to adopt proposed changes. No participant can turn an assumption into verified evidence merely by accepting a suggestion.

---

## Contents

1. [Product purpose, users, and boundaries](#1-product-purpose-users-and-boundaries)
2. [Authority and decisions already made](#2-authority-and-decisions-already-made)
3. [Input model: few inputs, expandable detail](#3-input-model-few-inputs-expandable-detail)
4. [End-to-end user journeys](#4-end-to-end-user-journeys)
5. [Information architecture and visual design](#5-information-architecture-and-visual-design)
6. [Screen and feature specifications](#6-screen-and-feature-specifications)
7. [Literature and evidence workflow](#7-literature-and-evidence-workflow)
8. [Ownership, evidence states, and project data](#8-ownership-evidence-states-and-project-data)
9. [Evaluation workflow and model contracts](#9-evaluation-workflow-and-model-contracts)
10. [Deterministic rubric and decision rules](#10-deterministic-rubric-and-decision-rules)
11. [Review, explanations, and development actions](#11-review-explanations-and-development-actions)
12. [Revision tracking and dependency invalidation](#12-revision-tracking-and-dependency-invalidation)
13. [Software architecture and module boundaries](#13-software-architecture-and-module-boundaries)
14. [Data entities, schemas, and interfaces](#14-data-entities-schemas-and-interfaces)
15. [Public application API](#15-public-application-api)
16. [Document processing and source locations](#16-document-processing-and-source-locations)
17. [Model selection, context, cost, and failure controls](#17-model-selection-context-cost-and-failure-controls)
18. [Privacy, security, and permitted use](#18-privacy-security-and-permitted-use)
19. [Import, export, and portability](#19-import-export-and-portability)
20. [Operational and accessibility requirements](#20-operational-and-accessibility-requirements)
21. [Testing, evaluations, and release gates](#21-testing-evaluations-and-release-gates)
22. [Build stages and acceptance criteria](#22-build-stages-and-acceptance-criteria)
23. [Architecture governance for AI-assisted development](#23-architecture-governance-for-ai-assisted-development)
24. [Requirement-to-rubric traceability](#24-requirement-to-rubric-traceability)
25. [Decisions to resolve before deployment](#25-decisions-to-resolve-before-deployment)
26. [References and source-use limits](#26-references-and-source-use-limits)

---

## 1. Product purpose, users, and boundaries

### 1.1 The job the product performs

Help a researcher answer four questions:

1. What contribution is actually present in this version?
2. What is the most consequential obstacle to defending it?
3. What supports that judgment, and what remains unexamined?
4. What specific action is worth doing next, and how would its possible outcomes change the decision?

An initial review must be useful even when the appropriate conclusion is that the research question needs clarification. A completed manuscript review must not pretend that reading the methods section independently verifies the underlying data.

The product is an author-development tool. It is not a journal acceptance predictor, plagiarism detector, legal originality certificate, automatic paper-writing service, or substitute for scientific judgment. It supports the scientific and editorial-fit distinctions in v4 rather than translating a score into acceptance odds. [R4, §§1–3, 8]

### 1.2 Initial users

The private pilot serves one researcher working primarily in management and organization research. Design the data model with workspace and project ownership from the beginning, but do not add public registration, billing, a marketplace, or real-time collaboration to the first release.

The next release may admit a small number of invited researchers, each with isolated projects. Coauthor access is a separate capability requiring explicit project permissions and document-sharing rules.

The interface must support both an experienced researcher with a developed argument and an early-stage researcher who needs help specifying it. Neither user should have to learn every rubric label before entering a project.

### 1.3 First-release scope

Include project intake; authorized document upload and pasted excerpts; source-linked extraction; editable argument and literature records; alternative-explanation comparisons; study-planning records; a selective usefulness profile; v4 evaluation and calculations; targeted clarification; development actions; revision comparison; and Markdown/JSON export.

Do not include automatic external literature discovery, arbitrary URL fetching, raw-data execution, model training, unrestricted tool-using agents, journal submission, sending emails, public project sharing, or a universal ranking across contribution types.

The absence of external search is a deliberate first-release boundary, not a claim that the supplied literature is exhaustive. The report must distinguish a contribution assessment relative to supplied sources from a broader literature search.

### 1.4 Success

The product succeeds when it finds real, important issues, represents the research and literature accurately, proposes useful next work, and recognizes when that work has resolved the issue. Producing longer reports, filling every field, or raising scores is not success by itself. This follows the assessment and calibration priorities in v4. [R4, §§11, 15]

---

## 2. Authority and decisions already made

### 2.1 Authority hierarchy

| Layer | Authority | What it may change |
|---|---|---|
| Evaluation policy | Frozen v4 text and a reviewed executable policy manifest | Criteria, anchors, formulas, caps, eligibility, and report requirements, only through a new policy release |
| Application specification | This document | Workflow, interface, software responsibilities, security, and product limits |
| Project record | Researcher-authored content and accepted interpretations, with provenance | The intended project and selected materials |
| Source record | Immutable source version and anchored text | Evidence of what the supplied document states, not automatic evidence that its statements are true |
| Model output | A attributed proposal or assessment | Suggested interpretations, ratings, objections, and actions, subject to validation |
| User response | Correction, new evidence, preference, or disagreement | Updates the project or records a response; does not overwrite an evaluation's historical result |

The Aguinis builder is interface inspiration. Its contribution categories, default verdicts, templates, and scorecard are not evaluation policy. The supplied JSON files contain empty `state` objects and repeated default reports, not a recoverable specification of the original app's implementation. The screenshot provides a concrete example of an alternatives table and inference planner. [B]

### 2.2 Fixed product choices

**Hybrid input:** three intake areas plus short settings, with optional structured workspaces afterward.

**Source-grounded core:** user-supplied literature is a first-class input. External discovery is a later opt-in module.

**Human-directed, not human-burdened:** the app proposes records from supplied content and asks only for corrections that matter. It does not require approval of every extracted sentence before giving a limited review.

**One project record:** screens are different views of shared objects. Do not make the user paste the same definition into three forms.

**Versioned rules:** the rubric is stable application policy, not an editable paragraph the model can rewrite during a conversation.

**Explanations before totals:** the main review emphasizes contribution, obstacle, and next action. Scores remain visible where valid.

**No silent strengthening:** extraction must represent the submitted argument. Proposed improvements are stored separately and do not inflate the original assessment.

### 2.3 Spec versus rubric changes

New software states such as `STALE`, `QUEUED`, or `AWAITING_CORRECTION` are application states, not additions to the rubric's quality scale. New operational limits are not scientific prerequisites. A new interpretation of a rubric rule requires an explicit decision record; it must not be hidden in a prompt or front-end conditional.

The canonical rubric file used for this specification has SHA-256:

```text
a94c195f1f95547cad00d9f2bdcd384cca58ae85bf40646d4b36146379b8f26d
```

---

## 3. Input model: few inputs, expandable detail

### 3.1 The new-project screen

Present three main areas:

| Area | User input | Required to start? | What happens next |
|---|---|---|---|
| **Your idea or draft** | Paste a description, upload a draft, or both | At least one substantive source | Preserve original text; propose a project brief and argument record |
| **Literature and supporting material** | Upload papers, add attributed excerpts, and optionally paste a literature summary | No for an initial screen; needed for source-grounded comparison | Create source records; suggest roles; prepare comparison records |
| **What help do you need?** | A brief request, concerns, prior author feedback, and optional resource constraints | A default task is available | Define the evaluation scope and desired next decision |

Below these areas are compact selectors for stage, current task, and audience if known. Each includes an uncertainty option. Project title may be entered or proposed. Authorization to process the material and consent to the configured external model are separate controls, not buried in the research text.

Example task options: assess the idea; examine contribution relative to sources; examine the study; work on a particular objection; review a revision; or help decide the next research step. These select work scope, not favorable outcomes.

**Only the idea/draft and processing authorization are essential for the smallest useful screen.** Unknown audience, missing literature, or vague design can limit the result without preventing the user from starting.

### 3.2 Where multiple pasted texts belong

Several texts may be pasted, but each is labeled by purpose: project description, supplementary author note, source excerpt, literature interpretation, design note, or response to an objection. Pasting into a source excerpt asks for a source identifier; it cannot silently become an authenticated quotation from a named paper.

Inside a workspace, fields can be edited directly. A user can paste a mechanism into the argument workspace or an account of a competing theory into an alternatives row. That is optional precision, not the default onboarding burden.

The app must offer `Not known yet`, `Not part of this contribution`, and `Needs a source` where appropriate. These record meaning, not generic empty strings.

### 3.3 The model's input assistance

The model may extract a research question, premise, audience, intended route, construct definition, proposed explanation, rival, claim, or study description from supplied text. Each extracted item needs a source location or an explicit label that it is a proposed synthesis.

The model may infer a likely connection, but it must label that inference and identify what assumption it adds. It may propose an improved argument only in development mode or in a separately identified suggestion.

It must not invent a sample, data-access confirmation, result, citation, measurement validation, researcher commitment, or probability of successful repair. A blank field is not an invitation to make the project appear complete.

### 3.4 Confirmation without a bottleneck

After extraction, show a short interpretation panel containing the question, main promise, route, stage, central explanation or task, and selected evaluation materials. The researcher can confirm the interpretation, correct it, or proceed with listed unresolved items.

A full evaluation must flag unresolved ambiguities that could change the applicable rules. A limited screen may continue with conditional interpretations. Confirmation means “this represents my intended project,” not “the claims have been proven.”

Do not ask for information already clearly stated in the materials. Clarifying questions should concern the few unknowns that could materially change the assessment or next action. Show up to three together as an interface default, not a permanent cap on substantive inquiry.

### 3.5 Input precedence and evaluation targets

A project can have a draft plus a newer author note that changes the intended argument. The app must ask which target to evaluate: **the manuscript as written** or **the current project as clarified**. A critique of the manuscript must not credit improvements existing only in a note. A project assessment may use that note but must identify the manuscript sections not yet updated.

Conflicting assertions are preserved and surfaced. Recency alone is not a license for the model to silently resolve a substantive contradiction. The user can designate a current field, and the earlier value remains in history until deletion.

---

## 4. End-to-end user journeys

### 4.1 Early idea

The researcher pastes several paragraphs and asks whether the idea is worth developing. The app extracts a brief, identifies the intended contribution, asks a necessary clarification if one exists, and returns a limited screen. It identifies what is promising, what is not yet assessable, and the smallest informative next action.

No literature supplied means no independent source-based novelty conclusion. No specified study means no study total. No completed explanation in a discovery proposal means a pending explanatory block, not a zero mechanism score. [R4, §§1–2]

### 4.2 Draft with a user-supplied literature packet

The researcher uploads a draft and selected papers. The app reports extraction quality and proposes source roles. The researcher marks the most important predecessors if known. The app reads the admitted packet at the declared depth, drafts source-backed comparisons, and asks about consequential conflicts.

After the interpretation checkpoint, the user starts the full evaluation. The resulting report links objections to the draft, relevant sources, and v4 requirements. Clicking an objection opens the appropriate workspace with existing material already populated.

### 4.3 Manual or focused work

An experienced user opens the alternatives workspace directly, enters two accounts, and asks whether their predictions diverge. The app runs a targeted task against those objects and the selected sources. It does not present that result as a full-project review or silently reevaluate unrelated dimensions.

Manual editing, reading, saving, and exports work without a live model connection. The application is useful as a structured worksheet even when evaluation is paused.

### 4.4 Revision after feedback

The researcher uploads a new draft or accepts edits into the project record. The app shows material differences and which earlier assessments are affected. A new evaluation reads the revised evidence and records each prior issue as addressed, still present, changed, or not yet assessable.

User disagreement does not erase an objection. The user can identify a misreading, provide a passage, or explain why the recommendation is not appropriate. The app rechecks that issue. It may withdraw it, revise it, or retain it with a response to the user's reasoning.

### 4.5 A project changes contribution type

A discovery project may develop an explanation. A failed explanatory premise may motivate a descriptive question. The app creates a route-change revision, keeps the earlier record, and applies the new route requirements. It does not graph an artificial increase or decrease between incomparable theory totals.

---

## 5. Information architecture and visual design

### 5.1 Navigation

Use a persistent left navigation rail:

```text
Projects
  Overview
  Brief
  Literature
  Argument
  Alternatives
  Study
  Usefulness
  Review
  Next actions
  History
Settings and data
```

The list is navigation, not a required linear sequence. For an initial idea, Overview emphasizes only the relevant next work; advanced sections remain available without large empty checklists dominating the screen.

### 5.2 Desktop layout

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Project title | Revision 3 | Rubric 4 | Saved       [Evaluate] [Export] │
├───────────────┬───────────────────────────────────┬────────────────────┤
│ Overview      │ Active workspace                  │ Evidence / Help    │
│ Brief         │                                   │                    │
│ Literature    │ Main content, comparison, or task  │ Linked passage     │
│ Argument      │                                   │ Rubric requirement │
│ Alternatives  │ Editable records                   │ Interpretation     │
│ Study         │                                   │ Remaining unknowns │
│ Usefulness    │ [Check this] [Propose change]      │                    │
│ Review        │                                   │ [Open source]      │
│ Next actions  │                                   │                    │
│ History       │                                   │                    │
└───────────────┴───────────────────────────────────┴────────────────────┘
```

The evidence drawer opens when needed; it need not consume space continuously. Main content should remain readable on a normal laptop. On narrow screens, the drawer becomes a separate panel and wide comparisons become stacked cards with labeled columns.

### 5.3 Visual character

Use a restrained, document-oriented interface: light background, dark readable text, one primary accent, clear spacing, and modest borders. Avoid oversized gauges, animated score celebrations, traffic-light verdicts without explanations, and a screen full of tiny textareas.

Default body text should be comfortably readable, with resizable multiline inputs. Tables need sticky headers, wrapped text, and row expansion. Long evidence passages open in a reader rather than enlarging every table cell.

Use three separate status concepts:

| Display | Meaning |
|---|---|
| Information available | Which project components have material |
| Evidence/inspection status | What has been supplied, examined, or checked |
| Research assessment | The actual quality judgment and applicable scores |

There is no universal “project completeness percentage” that masquerades as research quality.

### 5.4 Shared actions

Each editable object supports edit, attach evidence, view history, and ask for targeted help. Model proposals support accept, edit before accepting, reject, or keep as an alternative. Each review issue supports open evidence, respond, open related workspace, and add a linked action.

Saving a user edit must not automatically start a paid model evaluation. A deterministic stale-status update may run on save. The user explicitly requests substantive rechecking, with scope and cost controls visible.

---

## 6. Screen and feature specifications

### 6.1 Overview

**Purpose:** Tell the researcher where the project stands and what to do next.

Show the current question, intended contribution, stage, review scope, last evaluation revision, and whether it is current. Below that show the core insight to preserve, the principal obstacle, and the recommended next action. A compact coverage panel identifies missing sources or unexamined checks.

Before a review exists, show extracted interpretation and the next useful setup step. Do not display default numeric scores or default condemnation for an empty project.

**Primary action:** Start an initial screen, start a full evaluation, or work on the next action, depending on state. These states should not be selected by keyword matching alone.

### 6.2 Brief

**Purpose:** Establish the question and promised contribution.

Editable records cover broad puzzle, narrow question, concrete basis, claimed scope, scholarly audience, whose perspective defines the problem, intended contribution, route, stage, and decision sought. Optional cards capture what the researcher believes is known and what needs to be learned.

The app may extract these from the draft and propose a three-part summary: why it matters; what is known and unresolved; what the project would add. That presentation is informed by Grant and Pollock, while the evidence and route requirements remain v4's. [H; R4, §6]

**Output:** An accepted or explicitly provisional brief, not a rewritten introduction masquerading as the original argument.

### 6.3 Literature

**Purpose:** Build an inspectable account of prior work and the proposed increment.

Use two views: a source shelf and a comparison table. The shelf shows bibliographic identity, role, version, availability, processing quality, and inspection coverage. Roles may include closest predecessor, rival explanation, foundation, empirical evidence, or benchmark; one source can have several roles.

The comparison table contains source claim; supporting passage; relevant conditions; overlap; departure; why the departure matters; and unresolved coverage. Allow the user's interpretation and the app's interpretation to be viewed separately.

**Actions:** Add a paper, paste an attributed excerpt, edit an interpretation, inspect a source, compare selected works, mark a lead that needs obtaining, and request reconsideration of a disputed comparison.

**Output:** v4's prior-work categories: already stated, immediate application, nontrivial assembly, distinct explanatory change, or unresolved overlap. These are descriptive judgments, not a second novelty scale. [R4, §6.2]

A paper already making the proposed argument can be a predecessor without being a rival. A cited source's existence does not show that its argument has been inspected.

### 6.4 Argument

**Purpose:** Make the explanation and its assumptions inspectable.

Use claim cards with because-logic, conditions, units, timing, and implications. A construct view contains definitions, neighboring concepts, inclusion/exclusion boundaries, and source links. A simple sequence view can show steps in a process, but no diagram is mandatory.

Provide targeted checks for circular explanation, a missing logical step, mismatched levels or timing, construct slippage, and a hypothesis that does not follow from its argument. Any suggested improvement must identify what it changes and preserve an untouched original.

For discovery before an explanation exists, present an explanatory task and candidate interpretations rather than mandatory mechanism fields. A fully articulated explanatory project cannot use the discovery label to hide an absent mechanism. [R4, §§2, 4]

**Output:** Claims and assumptions linked to sources and implications, with unresolved issues clearly labeled.

### 6.5 Alternatives

**Purpose:** Translate competing accounts into a potentially informative study.

Adapt the screenshot into two connected panels rather than copying its scoring or default messages. [B]

**Panel A: comparison matrix**

| Account | Source or explicit assumption | Why plausible | What it predicts | Shared outcomes | Distinguishing implications | Evidence that could weaken it |
|---|---|---|---|---|---|---|
| Current explanation | Source anchors or author argument | Editable | Editable | Editable | Editable | Editable |
| Alternative | Source anchors or labeled proposal | Editable | Editable | Editable | Editable | Editable |

**Panel B: study contrast**

Record the particular comparison, observations needed, timing and sampling, measurement assumptions, feasibility, and what supporting, conflicting, negligible, imprecise, or missing evidence would mean.

Use the screenshot's yes/no/unclear questions as diagnostic prompts with reasons, not as a point checklist. “Could this evidence distinguish the accounts?” is a substantive judgment. “Do all rows contain text?” is only a form check.

Do not require a minimum number of rivals, numerical effect-size predictions for every theory, a contest between incompatible theories where accounts are complementary, or elimination of an entire theory. Distinguish failed confirmation from evidence that meaningfully weakens a particular claim under stated assumptions. [R4, §4.6]

**Output:** An explicit inference plan and any unresolved design requirement, not a declaration that the proposed theory will win.

### 6.6 Study

**Purpose:** Connect the claim to the evidence needed and the evidence currently available.

Use a claim-to-observation map and method-appropriate support records. Core fields include setting, sample/cases, unit, time, measures or documentation, comparison, analysis plan or reported analysis, and claimed inference.

For quantitative work, expose the v4 audit items: sample; independent changes or assignments; usable comparison; residual spread and overlap; concentration and influence; outcome information; substantive/design sensitivity; justified bounds; and remaining uncertainty. For qualitative/process work, expose cases, episodes, independence of accounts, contrasts, direct versus inferred processes, and influential or missing evidence. [R4, §7]

The first release accepts descriptions, tables, results reports, and codebooks as documents. It does not execute uploaded code or inspect raw datasets. A calculated quantity can be recorded as reported by the user or observed in an analysis artifact, not as reproduced by the app.

**Output:** An assessment of the stated study and a list of checks with statuses `EXPECTED`, `VERIFIED`, `PENDING`, or `UNAVAILABLE`, each specifying what that status refers to. A reviewer finding that a check is absent is not the same as evidence that the check would fail.

### 6.7 Usefulness

**Purpose:** Specify what the contribution could help someone understand or do.

Offer optional cards for scholarly, practical, societal, policy, and educational use. Each records audience, concrete change, route to use, supporting basis, status, conditions, and possible costs or unintended consequences. One specific use can suffice.

Separate potential relevance, route to use, attention, actual use, and consequences of use. A proposed classroom case is not demonstrated learning impact; an implementation plan is not evidence of successful intervention. [R4, §10]

**Output:** Supporting records for dimensions 1 and 7 and for action planning. No separate impact total and no points for selecting all five forms.

### 6.8 Review

**Purpose:** Present the assessment as a reasoned, inspectable decision.

Default order: assessment scope; contribution; insight to preserve; principal obstacle; next action; evidence and inspection limits; dimension/route profile; other substantive issues; study and promise checks; version change summary. Details expand rather than dominate the opening.

Each rating opens its anchor, rationale, evidence, limitation, status, and benchmark if required. Each cap opens its exact v4 rule and the semantic finding that triggered it. Unknown prerequisites are not treated as passed.

Display both current score and pending/conditional labels honestly. No acceptance probability, originality percentage, or hidden composite that mixes unrelated contribution types.

**Output:** A published-in-project evaluation artifact. “Published” here means saved as an immutable app report, not journal publication.

### 6.9 Next actions

**Purpose:** Turn a review into bounded work.

Show one recommended action and at most two meaningful alternatives by default. Store additional necessary checks in a secondary list. Each action contains the related issue, deliverable, rationale, success condition, resources, what must be preserved, possible outcomes, and subsequent decisions.

Action states: proposed, selected, in progress, submitted for check, checked, deferred, abandoned. Task completion and resolution of the scientific issue are separate. The user can complete a literature-reading task without resolving novelty.

Optional numerical scenarios follow v4. An LLM must not supply ungrounded repair probabilities just to make the interface look finished. Keep `STOP` and inconclusive branches valid without numerical expected strength. [R4, §12]

### 6.10 History and comparison

**Purpose:** Preserve what changed and avoid repetitive, ungrounded reviewing.

Show source additions/removals, accepted edits, route changes, assessments, user responses, and action outcomes. Separate content changes from new evaluator information, model changes, prompt changes, and rubric changes.

Compare versions by contribution, central objections, affected evidence, and next action. Show score differences only when their basis is comparable, and label model/policy changes that weaken attribution to project improvement.

### 6.11 Contextual assistant

A collapsible assistant can explain the selected issue, examine a source passage, propose an edit, or help formulate an action. It must know which project revision and selected objects are in scope.

Conversation is not the database. A chat answer becomes project content only through an explicit proposal-and-accept operation. The assistant cannot alter grades, source text, policy, access rights, or historical reports by conversational request. A scoped conversation may lead to a new evaluation, not an invisible overwrite.

---

## 7. Literature and evidence workflow

### 7.1 Three evidence modes

| Mode | Permitted conclusion | Visible limitation |
|---|---|---|
| Idea and user summaries | Assess the argument as described; suggest what needs checking | Account of prior work not independently checked |
| Supplied excerpts or papers | Compare the project with inspected supplied evidence | Coverage limited to supplied and inspected material |
| External discovery, later release | Add authorized search, candidate screening, and inspected new sources | Search scope, date, exclusions, access limits, and unresolved candidates remain explicit |

The mode describes evidence coverage, not subscription quality. A user who supplies excellent literature may receive a strong grounded assessment without any external search.

### 7.2 Source processing

Identify documents and versions; extract text and structure; preserve locations; label source roles; construct a source synopsis for navigation; and create claim-linked evidence records. A synopsis never replaces the source passage behind a consequential judgment.

Distinguish what a paper proposes, tests, reports, and interprets. A claim in a discussion section is not automatically an empirically established result. Record whether the relevant statement is direct or quoted through another work.

### 7.3 Read depth and honest coverage

For a full evaluation, the app must process the complete admitted project material, including relevant appendices, through section-aware passes. Every section must have a coverage record. A summary-only shortcut cannot silently qualify as full inspection.

For admitted literature, the app prepares complete-text orientation where text is available and focused rereading of relevant argument, methods, results, and boundaries for decision-driving comparisons. A record of text supplied to a model is not proof of comprehension; call it inspection coverage, not “understood with certainty.”

If the packet exceeds configured limits, offer a narrower targeted review or staged processing. The user must see which material is excluded. Never silently truncate and label the output a complete review.

### 7.4 Retrieval within the supplied packet

Use section structure and lexical search as the initial retrieval baseline. Preserve whole sections and neighboring context around hits. A semantic index may supplement that baseline after it demonstrably improves retrieval on test cases; it must not become the sole basis for concluding that something is absent.

Every request is filtered by workspace, project, selected document versions, and run scope before material reaches the model. Search results from another project are unavailable even if they are semantically similar.

A negative assertion such as “this is not addressed” requires a documented absence check across relevant sections and variants. A snippet search that returns nothing is insufficient. If coverage is inadequate, the language must state “not located in inspected material” and the affected conclusion remains limited.

### 7.5 Novelty and disagreement

Use v4's overlap categories, with passage-level support. Do not call a matching prediction duplication when mechanism or scope differs materially. Do not treat familiar components as proving that a new assembly has already been published. Any cross-paper synthesis made by the app is labeled as such. [R4, §6.2]

A researcher can challenge a source interpretation. Preserve both accounts, review the source, and update the comparison if warranted. Acceptance of the app's phrasing is not an endorsement by the original source's author.

---

## 8. Ownership, evidence states, and project data

### 8.1 Independent state axes

Do not compress all status into one green checkmark.

| Axis | Examples | Interpretation |
|---|---|---|
| Origin | User text; extraction from document; model inference; development suggestion | Where content came from |
| Adoption | Proposed; accepted as project representation; rejected; superseded | Whether it is part of the working project |
| Evidence state | Documented/verified; specified but untested; contested; missing; not inspected; contradicted; not applicable | The v4 epistemic state of the bounded claim |
| Check provenance | User-reported; source text inspected; analysis artifact inspected; app reproduced | What was actually checked and by whom |
| Assessment status | Assessed; pending; not applicable; conditional; contested | Whether a judgment is supported for this target |
| Freshness | Current; affected by change; superseded | Whether dependencies match the current revision |

The first release must never assign `app reproduced` to a statistical analysis it did not run. `Documented` requires a stated object of verification: that a source makes a claim is different from verifying the claim's truth.

### 8.2 Core records

The working project stores brief fields, constructs, claims, assumptions, predictions, comparisons, studies, evidence checks, uses, and actions. The records form a linked model using ordinary identifiers and relational tables. They do not require a graph database.

A claim can have multiple source anchors and a source can support multiple claims. An evidence relation may support, challenge, contextualize, or merely document attribution. Mere citation is not positive support.

### 8.3 No circular evidence

A review, model-generated synopsis, or polished contribution statement must never be treated as independent literature evidence for the very assessment that created it. Such artifacts may be navigation context or revision history. Source-based judgments must remain traceable to the original project or literature text.

### 8.4 Review versus development

Extraction mode preserves the submitted account. Evaluation mode judges the chosen snapshot. Development mode proposes improvements. These tasks use separate prompts and output types.

If a model proposes a missing mechanism while reviewing, that mechanism remains a proposed action or alternative version. The original project is not rescored as though it already contained it.


## 9. Evaluation workflow and model contracts

### 9.1 Bounded workflow, not an autonomous agent swarm

The application runs a known sequence of jobs. One approved capable model can perform several tasks with different instructions. A second model is optional for later comparison, not required architecture and not independent human validation. The workflow controller, not the model, decides whether a permitted task can run.

```text
Authorize processing and choose materials
    -> Validate and parse documents
    -> Propose project interpretation and source records
    -> Confirm or record unresolved interpretation
    -> Freeze evaluation snapshot
    -> Prepare source evidence and coverage records
    -> Evaluate intellectual contribution or route task
    -> Evaluate specified study, when applicable
    -> Check source links and substantive objections
    -> Apply deterministic scores, caps, and prerequisites
    -> Propose bounded actions
    -> Validate action dependencies and conditional calculations
    -> Render and save the review
```

These are conceptual stages, not a claim that every run requires the same number of API calls. A short screen may use a few calls; a full packet needs additional document-reading passes. Budgets bound those passes. Processing cannot silently skip essential work to fit an advertised call count.

### 9.2 Task contracts

| Task | Receives | Produces | Prohibited behavior |
|---|---|---|---|
| `ExtractProject` | Original project material, field definitions, provenance rules | Proposed brief, claims, concepts, study facts, ambiguities, source anchors | Improve the argument silently; invent missing facts |
| `ReadSource` | Source text and structure, explicit reading purpose | Attributed claims, scope, predictions, findings, limits, anchors, coverage | Attribute app inference to the paper; assert unseen content |
| `ComparePriorWork` | Project claims and inspected source evidence | Overlap/departure records and unresolved comparisons | Certify exhaustive novelty or create a consensus from unsupported fragments |
| `AssessIntellectual` | Frozen project representation, original passages, policy text, relevant sources and benchmarks | Proposed d1–d7 judgments or route assessment; semantic rule findings; insight; objections | Use data convenience to inflate intellectual value; score imagined repairs |
| `AssessStudy` | Claimed inference, study material, evidence/check records, applicable policy | Proposed d8–d10 judgments; support limits; mismatch findings | Reproduce nonexistent diagnostics or infer design quality from a method label |
| `VerifyAssessment` | Proposed judgment, original passages, counterevidence, policy clause | Supported, needs revision, or unresolved disposition for important claims | Treat agreement with another model as proof; add an unrelated new research agenda |
| `PlanActions` | Validated assessment, binding issues, project constraints, v4 repair rules | Ranked, bounded action proposals and outcome branches | Invent time/cost certainty, probabilities, or future favorable findings |
| `ExplainOrProposeEdit` | User's scoped question, selected objects, allowed evidence | Explanation or a proposed patch | Change canonical records without explicit acceptance |

Use structured output schemas for every task. Providers can support schema-constrained output, but schema adherence does not establish factual or scientific correctness; validate both structure and content-related requirements. [T1]

### 9.3 Interpretation and route routing

The model proposes a route using the project's actual main promise. The researcher confirms the intended contribution. The evaluator may flag a mismatch between that declared route and the manuscript's claims. Record the disagreement; do not quietly choose the more flattering scoring path.

The deterministic router maps a sufficiently established route and stage to required fields, eligible blocks, and applicable rule families. It is a finite set of routing rules, not a decision tree that purports to establish theory quality by itself.

### 9.4 Source checking before final judgment

Structural checks verify that a cited anchor exists, belongs to the authorized source version, and matches the quoted text after documented normalization. They do not establish that the passage entails the interpretation.

A semantic checking pass examines whether a decision-driving objection or comparison is supported, qualified appropriately, and contradicted elsewhere. Search and section inspection support that pass. Structural and semantic check results are stored separately.

Every blocking objection must receive a check. Other consequential claims are checked according to declared review scope. An unverified evaluator allegation cannot appear as a settled blocking premise or novelty objection. If checking cannot resolve it, the report must label that judgment unresolved. A completed evaluation can conclude that the science is uncertain; that differs from a run that failed to inspect the required material.

One bounded correction pass is allowed by default after substantive verification. Persistent disagreement is surfaced, not resolved by indefinite model debate. New material requires an explicit new scope or run.

### 9.5 Intellectual pass ordering

When assessing an articulated theory, do not provide current data-access convenience, prior scores, author prestige, or desired verdict as reasons to rate the idea more highly. When completed inductive evidence is necessary to understand the theory, include it and label its role. Never pretend a completed discovery was known at proposal stage. [R4, §§1.2, 15.1]

The app may need original results to interpret an inductive contribution, but it must still keep intellectual argument quality separate from the credibility of the study. Visibility of evidence does not license outcome-based score inflation.

### 9.6 Explicit report scope

Reports are labeled `INITIAL_SCREEN`, `TARGETED_CHECK`, `FULL_EVALUATION`, or `REVISION_REVIEW`, plus route, stage, target revision, and source coverage. `FULL_EVALUATION` means the full applicable protocol has been assessed or explicitly marked pending; it does not mean the app has independently replicated the study or searched all literature.

A review of a completed study may legitimately conclude that indispensable support is still unverified. The work's stage and the evaluator's coverage are distinct.

---

## 10. Deterministic rubric and decision rules

### 10.1 What is fixed in code and configuration

Maintain a versioned policy package with the exact v4 text, a reviewed manifest, pure calculation functions, named rule IDs, traceability to sections, and golden test cases. Anchors and requirement text are data. Arithmetic, state validation, and rule application are deterministic functions.

Do not scatter duplicate weights across prompts, browser code, and backend services. The backend rules engine is the authority; the interface displays its result. Prompts receive the applicable policy text and schema, not permission to redefine it.

### 10.2 What still requires judgment

Whether an explanation is circular, whether an advance is nontrivial, whether a comparison warrants causality, and whether the source accurately supports the author are not reliably reducible to checkbox logic.

The model or a human evaluator supplies a supported finding for these questions. Each finding has a rule ID, `TRUE`, `FALSE`, or `UNKNOWN`, evidence anchors or explicit reasoning, scope, and verification status. The rules engine decides the consequence only after input validation.

For example, the rule is fixed: an EXPLAIN project with no nontrivial advance receives the specified cap. Whether that project really has no nontrivial advance is a contestable substantive assessment. The app must show both layers.

### 10.3 Numerical core

| Dimension | Weight within original blocks |
|---|---:|
| d1 Consequential puzzle | 10 |
| d2 Audience-relative interestingness | 10 |
| d3 Theoretical advance | 15 |
| d4 Explanatory logic and mechanism | 15 |
| d5 Constructs, levels, and timing | 8 |
| d6 Discriminating implications and intellectual risk | 9 |
| d7 Coherence, reach, and usefulness | 8 |
| d8 Construct–evidence alignment | 10 |
| d9 Credibility for the claimed inference | 10 |
| d10 Informative setting and sampling | 5 |

Apply to eligible assessed blocks:

```text
I_uncapped = (10/75) * (10*d1 + 10*d2 + 15*d3 + 15*d4 + 8*d5 + 9*d6 + 8*d7)
D_raw = (10/25) * (10*d8 + 10*d9 + 5*d10)
P_uncapped = 0.5*I_uncapped + 0.5*D_raw
I_raw = min(I_uncapped, applicable idea caps)
P_before_project_caps = 0.5*I_raw + 0.5*D_raw
P_raw = min(P_before_project_caps, applicable project caps)
```

When no cap applies, do not supply an arbitrary cap. There is no additional independent `D_raw` cap in v4. Preserve uncapped results and a rule trace. Use exact or sufficient-precision decimal/rational arithmetic, never rounded displayed inputs. Display whole points with exact halves rounded upward; test gates before rounding. [R4, §8.1]

### 10.4 Core guards and hard stops

| Rule ID | Validated condition | Required result |
|---|---|---|
| `ROUTE-TOTAL` | ESTABLISH or TEST | `I_raw` and `P_raw` not applicable; eligible `D_raw` may be reported with route |
| `DISCOVERY-PENDING` | Future explanatory account not articulated | Explanatory block pending; use route assessment rather than replacement scores |
| `UNINSPECTED-BLOCK` | Required dimension not inspected | No affected block total; no zero or midpoint substitution |
| `AUDIENCE-QUESTION` | Audience or question cannot be identified | Withhold final intellectual assessment; permit clarification |
| `PREMISE-NO-BASIS` | EXPLAIN asserts central phenomenon without support or credible establishing plan | d1 no higher than 3; idea cap 39; premise check or reformulation required |
| `PREMISE-CONDITIONAL` | Unsupported central asserted premise has a credible establishing plan | Conditional assessment; no unqualified strong/exceptional endorsement or unsupported full-study commitment |
| `PREMISE-CONTRADICTED` | Retained central premise contradicted | Block explanatory version as stated; a different claim requires a new version |
| `NO-ADVANCE` | EXPLAIN has no nontrivial advance beyond existing answer | Idea cap 39 |
| `NO-CONSEQUENTIAL-STAKE` | Surprise without consequential stake | Idea cap 69; no strong/exceptional label |
| `DESIGN-MISMATCH` | Central question and design mismatch | Project cap 39; submission readiness blocked |
| `INFERENCE-UNSUPPORTED` | Evidence cannot support central promised inference | Project cap 39 until claim/design changes |
| `PROMISE-OVERREACH` | Contribution exceeds what argument/evidence can deliver | Apply corresponding existing idea/project rule; no duplicate penalty |
| `HIGH-SCORE-BENCHMARK` | Proposed d_i ≥ 8 without inspected relevant comparison | Withhold exceptional rating; request benchmark or supported lower reassessment, never silently clamp to 7 |
| `EDITORIAL-UNCALIBRATED` | No approved empirical editorial calibration | Editorial field remains uncalibrated |

Unknown is not false. If an unknown prerequisite could materially change the label or allowed commitment, report a conditional/provisional result. Do not award a gate by default. Do not apply a punitive cap merely because an issue has not been inspected.

### 10.5 Quality profiles and readiness

**Strong explanatory idea:** `I_raw >= 70`; d3 and d4 ≥ 7; d1 and d6 ≥ 6; all remaining theory dimensions ≥ 4; no unresolved blocking premise or unidentified audience. An unsupported premise with a credible check still prevents an unqualified endorsement.

**Exceptional explanatory idea:** `I_raw >= 80`; d3 and d4 ≥ 8; d1 and d2 ≥ 7; remaining theory dimensions ≥ 6; required predecessors and high-score benchmarks inspected; no unresolved central premise.

**Strong project:** strong idea, `D_raw >= 60`, d8 and d9 ≥ 6, and stage-appropriate prerequisites.

**Exceptional project:** exceptional idea, `D_raw >= 70`, d8 and d9 ≥ 7, and stage-appropriate prerequisites.

**Basic EXPLAIN empirical submission readiness:** completed study, `I_raw >= 50`, d3 and d4 ≥ 5, consequential stake, d8 and d9 ≥ 5, aligned promise, no hard stop, and no indispensable support check unverified.

**ESTABLISH/TEST submission readiness:** adequate completed route assessment, d8 and d9 ≥ 5, delivered support for the central claim, aligned promise, and no hard stop. No theoretical novelty or mechanism floor is added.

Proposal readiness concerns the next commitment, not journal submission. Attach `PROPOSED` or `COMPLETED` to applicable project endorsements. Missing an excellence profile is not a fatal flaw. A rating range that crosses a gate yields a borderline/provisional label. [R4, §§8.4–8.5]

### 10.6 No scientific shortcuts

Do not automatically penalize a predictable sign, familiar setting, moderator, qualitative design, small number of cases, or null result. Do not reward prestigious labels, data access, significant coefficients, additional stakeholders, field completion, or confident writing.

The engine can enforce that a rationale and source check exist. It cannot establish that the rationale is correct. Its interface must never claim that code makes research evaluation objective.

---

## 11. Review, explanations, and development actions

### 11.1 Every major objection has a contract

An objection contains the specific claim being questioned; its location; the relevant source or argument; the applicable rubric requirement; why the problem matters; the strongest counterevidence found; severity; and a feasible response or a statement that none has been identified.

Expose a readable explanation of the decision. Do not display or request hidden chain-of-thought traces. Users need the evidence, explicit assumptions, inference, uncertainty, and practical consequence, not an internal token-by-token deliberation.

### 11.2 Example output, entirely hypothetical

> **Claim being assessed:** The study explains why firms select a particular practice.  
> **Issue:** Both supplied explanations predict the main relationship.  
> **Basis:** The predictions in the current draft and supplied comparison accounts coincide.  
> **Consequence:** A result in the predicted direction would not distinguish the proposed process.  
> **Next action:** Specify one condition under which the accounts imply different observations, then check whether the design can observe that condition.  
> **Possible outcomes:** A credible distinction can be tested; the accounts are complementary; or the available study supports the association but not the claimed mechanism.

The production report replaces generic references with real authorized anchors. It must not use this example as an automatic template judgment for all projects.

### 11.3 Action recommendation logic

The model proposes actions based on validated issues. A rules layer checks that each action references a real issue, names a deliverable, preserves the recorded insight or explicitly marks a pivot, fits stated resource constraints or flags the uncertainty, and has outcome branches.

Use v4's repair menu as a starting set of tactics, not a lookup that promises a score gain. The principal action may be a premise check, source inspection, conceptual clarification, measure validation, design comparison, narrowing, or explicit pivot. [R4, §11]

Prefer the smallest action that could materially change the current decision. Do not replace a single binding issue with a to-do list for rebuilding the whole project.

### 11.4 Conditional numerical planning

When comparable, defensible scenarios exist:

```text
V_a(B) = sum_k(p_k * S_k)
Expected score change = V_a(B) - S0
```

All probabilities must sum to one and be explicitly justified as planning assumptions, not calibrated model confidence. Every branch uses the same route and score base, with v4 caps applied. Distinguish completing work from resolving a problem. Scores describe articulated branch versions, not undefined future improvements.

Do not calculate `V(B)` without a resource budget, comparable branch scores, or defensible probabilities. A `STOP` branch without a described comparable alternative is not zero. Retain the decision tree without a numeric index. A low-cost decisive check can take priority even when the index is unavailable or falls. [R4, §12]

The retained v4 scenario priors can appear in an advanced panel labeled “optional planning assumptions.” They are not prefilled facts. The user is not required to invent a probability.

---

## 12. Revision tracking and dependency invalidation

### 12.1 Snapshot versus live project

The working project can change continuously. Each evaluation refers to an immutable snapshot of project objects, selected source versions, unresolved interpretations, rubric version, application policy manifest, prompt versions, model settings, and inspection scope.

A new upload or edit does not alter an earlier report. Instead, mark the affected report or component stale for the new working version. Historical reproducibility is subordinate to a deletion request: deleted content is not retained merely to replay an old run.

### 12.2 Dependency rules

| Change | Minimum affected assessments |
|---|---|
| Central question or contribution route | Intellectual/route assessment, study fit, promise, readiness, plan |
| Construct definition | Related claim, overlap comparison, measurement, inference, conclusion |
| Mechanism or condition | Relevant predictions, alternatives, contribution, study contrast |
| New predecessor or changed source interpretation | Related overlap, interestingness, novelty, and associated actions |
| Sample or analysis description | Study ratings, support audit, inference, promised conclusion |
| Resource constraints | Action feasibility and numerical scenarios, not automatic theory-score change |
| Wording with unchanged meaning | Usually no scientific reassessment; record edit classification |
| Model, prompt, or rubric version | New assessment configuration; old reports remain unchanged |

Record explicit object dependencies and a conservative fallback map. When change impact is uncertain, flag related judgments for review rather than presenting them as current. Do not assert that a dependency graph guarantees all semantic changes are detected.

### 12.3 No endless moving target

For each reopened issue, identify the new text, evidence, claim, or rule that makes reopening appropriate. A previously resolved issue is not reopened solely because a fresh generation phrases its preference differently.

Incremental reevaluation may reuse unaffected source notes and judgments only with matching dependency hashes and current permissions. Before a final full report, run a cross-module consistency check on the complete snapshot. Reuse saves work; it must not create a falsely integrated report from incompatible revisions.

### 12.4 Compare like with like

Version comparison shows whether improvement occurred in the research, in presentation, in the evaluator's source coverage, or because the model/policy changed. Do not interpret the same score under a different rubric or a different contribution route as directly comparable.

---

## 13. Software architecture and module boundaries

### 13.1 Proposed stack

Use a **modular monolith**: one backend codebase with explicit internal modules, exposed through an API, plus a worker running the same domain code for long tasks.

| Layer | Proposed implementation | Reason for this project |
|---|---|---|
| Browser | React and TypeScript, built as a client application | Editable records, source drawers, and revision views without embedding research rules in presentation |
| API/backend | Python with FastAPI and Pydantic contracts | A typed boundary for document, evaluation, and workflow requests; generated OpenAPI/JSON Schema support is documented [T2] |
| Canonical store | PostgreSQL | Project records, revisions, job state, source anchors, and audit metadata; built-in full-text search supports an initial lexical retrieval layer [T3] |
| File store | Private object storage in hosted deployment; local filesystem adapter for private development | Preserve originals separately from relational records |
| Long-running work | A durable job table and separately running worker, behind a queue interface | Explicit resumable stages without browser request timeouts |
| Retrieval | Section-aware search plus PostgreSQL full-text search; semantic supplement optional | Small supplied packets do not require a separate search platform |
| Models | A provider adapter with per-task schema and capability checks | Swap or test providers without rewriting the policy/domain code |
| Tests | Unit, integration, end-to-end, security fixtures, and a research-evaluation harness | Test deterministic compliance separately from scientific judgment quality |

These technology selections are proposed design choices, not findings derived from the scholarly sources. Lock actual dependency versions during implementation after compatibility and security review. Do not begin with a vector database, graph database, Kubernetes cluster, or custom-trained model.

### 13.2 Boundary map

```text
Browser
  -> API: authentication, authorization, request contracts
      -> Project service: working objects, proposals, snapshots
      -> Source service: upload, parsing, anchors, coverage
      -> Retrieval service: authorized context packets
      -> Workflow service: tasks, budgets, state, cancellation
          -> LLM adapter: typed calls, no direct database access
          -> Assessment verifier: anchor checks + semantic checks
          -> Policy engine: pure scores, caps, eligibility, traces
          -> Action planner: bounded recommendations + validation
      -> Report/export service
      -> Dependency/history service

Private database and private file store sit behind the services.
Only authorized service modules may read or write them.
```

### 13.3 Hard architecture rules

The model adapter has no database credentials and cannot select arbitrary files. The retrieval service receives an authorization context from the server, not tenant identifiers invented by model text. The policy engine has no network or model dependency. The report renderer cannot change ratings. The interface does not implement a second copy of grading logic.

Document parsers run separately from privileged API operations. The first release exposes no shell, code interpreter, email, browser automation, or arbitrary network tool to a document-reading model.

### 13.4 Deployment

Run the browser, API, worker, database, and file store in a private development environment first. A hosted pilot adds managed identity, encrypted storage/backups, TLS, deployment monitoring, and tested deletion. It remains invitation-only.

Local deployment with a cloud model is not offline. True offline operation would need a local approved inference backend and locally executed supporting components, with no external processing. The product must identify its actual data flow rather than use “local” as a privacy promise.

### 13.5 Queue and run semantics

A queued task contains project/snapshot IDs, allowed task type, input hash, budget reservation, lease, attempt number, and status. Workers claim tasks atomically; expired leases permit controlled recovery. Each stage commits an output atomically or leaves no accepted result.

Effects must be idempotent even if a task executes more than once. The app must not assume all external model APIs provide exactly-once billing. If a timeout leaves provider completion uncertain, record that state and any request ID before retrying; further calls stay within the remaining budget.

A deliberate user rerun creates a new run, not an overwrite. Duplicate clicks with the same idempotency key return the existing job. Cancellation prevents later stages; a remote call already in progress may still incur cost, which must be disclosed.

---

## 14. Data entities, schemas, and interfaces

### 14.1 Required entities

| Entity | Key fields |
|---|---|
| `Workspace` | Owner, access policy, model-processing policy, storage policy |
| `Project` | Workspace, title, working revision, route/stage, settings |
| `DocumentVersion` | Project, role, content hash, storage reference, parser version, availability, rights declaration |
| `SourceAnchor` | Document version, section, paragraph/page, text offsets, quoted-text hash |
| `SourceCoverage` | Run/task, document/section, inspected text ranges, exclusions, extraction issues |
| `ProjectObject` | Kind, value, origin, adoption state, evidence state, source refs, revision |
| `Comparison` | Related claims/accounts, overlap type, implications, evidence, uncertainties |
| `StudyRecord` | Claim IDs, design, sample, measures, comparisons, audit records |
| `Proposal` | Target object/version, proposed patch, reason, source refs, accept/reject state |
| `EvaluationSnapshot` | Frozen object/document versions, policy/prompt/model configuration, scope |
| `EvaluationRun` | Snapshot, stage state, budget, provider requests, outputs, limitations |
| `AssessmentItem` | Dimension/route item, proposed/validated judgment, rating if eligible, rationale, limitation, evidence |
| `RuleFinding` | Rule ID, true/false/unknown, supporting record, semantic verification |
| `Issue` | Related claims/ratings, severity, basis, counterevidence, user response, resolution history |
| `Action` | Issue, deliverable, resources, branches, success criterion, state, outcome evidence |
| `UseRecord` | Audience, form, intended change, route, status, conditions, consequences |
| `Dependency` | Upstream/downstream object version IDs and reason |
| `ExportJob` | Snapshot, format, included sources, authorization and deletion status |

All content-bearing records include workspace/project scope directly or through enforced ownership relationships. Identifiers alone are not authorization.

### 14.2 Example field record

Illustrative schema shape, not an implemented endpoint response:

```json
{
  "object_id": "claim-017",
  "project_id": "project-example",
  "revision": 3,
  "kind": "mechanism_claim",
  "text": "The proposed process operates under the stated condition.",
  "origin": "document_extraction",
  "adoption": "accepted",
  "evidence_state": "specified_but_untested",
  "source_anchor_ids": ["anchor-draft-021"],
  "generated_by_run_id": "extract-example",
  "confirmed_as_representation_by": "user-example",
  "dependencies": ["construct-004@2", "condition-003@1"]
}
```

The accepted state does not upgrade evidence. An underlying document can contain a false assertion; an exact quote establishes attribution, not truth.

### 14.3 Assessment item contract

A numeric item must include dimension ID; integer rating or null with an explicit reason; source/policy references; rationale; main limitation; material inspected; uncertainty range if relevant; benchmark evidence for ratings ≥ 8; and verifier disposition.

A null score is not serialized as zero. The schema distinguishes `PENDING`, `NOT_APPLICABLE`, and `UNRESOLVED`. Numerical block availability is computed from those states and the route.

A semantic judgment about a nonexistent empirical comparison is not accepted just because it has the right JSON keys. The verifier must be able to identify its evidential basis, or retain it only as an unresolved check.

### 14.4 Core internal interfaces

```text
parse_document(document_version, parser_policy) -> ParsedDocument
build_context(auth_scope, snapshot, task, query_plan) -> ContextPacket
call_model(task_contract, context_packet, budget) -> TypedTaskResult
validate_anchors(task_result, authorized_documents) -> AnchorCheckResult
check_assessment(candidate, original_context) -> VerificationResult
apply_rubric(validated_judgments, policy_version) -> ScoresAndRuleTrace
propose_actions(validated_review, constraints) -> ActionProposalSet
accept_proposal(proposal_id, expected_revision, user) -> NewRevision
invalidate_dependencies(change_set) -> AffectedObjects
render_report(snapshot, validated_review, calculated_results) -> Report
```

Inputs and outputs are typed and versioned. The `ContextPacket` records every included passage and exclusion. The model is never allowed to return arbitrary SQL or file paths as an instruction for these services to execute.

### 14.5 Policy manifest

Store rubric ID/version/hash; dimensions with weights, anchors, and requirements; route applicability; named hard-stop rules; profile and readiness requirements; rounding behavior; optional scenario rules; and report obligations.

Represent semantic inputs as named facts with tri-state values, not arbitrary executable expressions supplied by the model. Changes to manifests undergo the same review as code and trigger a new application policy version even when the scholarly rubric file is unchanged.

---

## 15. Public application API

The API is private to authenticated app clients; “public” here distinguishes it from internal module functions.

| Method and route | Behavior |
|---|---|
| `POST /projects` | Create a project under the authenticated workspace |
| `GET /projects/{id}` | Return authorized working state and freshness metadata |
| `PATCH /projects/{id}` | Update permitted settings with an expected revision |
| `POST /projects/{id}/documents` | Create an upload record and authorized upload destination |
| `POST /documents/{id}/complete` | Validate receipt and queue parsing |
| `GET /documents/{id}/content` | Authorized, bounded source-reader content |
| `POST /projects/{id}/extract` | Queue structured extraction for selected versions |
| `GET /projects/{id}/proposals` | List proposed records or edits |
| `POST /proposals/{id}/accept` | Apply an explicit patch with optimistic concurrency |
| `POST /proposals/{id}/reject` | Record nonadoption without rewriting original content |
| `POST /projects/{id}/evaluations` | Freeze snapshot, estimate/reserve cost, create run |
| `GET /runs/{id}` | Return stage, coverage, safe error details, and budget status |
| `POST /runs/{id}/cancel` | Stop future stages and request supported cancellation |
| `POST /projects/{id}/checks` | Run a targeted task against named objects |
| `POST /issues/{id}/responses` | Add a correction, passage, or disagreement |
| `POST /actions/{id}/outcomes` | Record work completed and supplied evidence |
| `POST /projects/{id}/compare` | Compare two authorized revisions with scope labels |
| `POST /projects/{id}/exports` | Create an authorized export job |
| `DELETE /projects/{id}` | Revoke access and schedule documented deletion |

All mutations require authorization and revision checks. Long jobs return an acknowledgment and run ID, not an open HTTP request until the model finishes. Polling suffices initially; server events can be added for progress. Rate limits and budget checks occur server-side.

User-supplied workspace IDs, document IDs, and model-produced anchors are checked against the authenticated scope. An error does not reveal whether an unauthorized project's identifier exists.

---

## 16. Document processing and source locations

### 16.1 Supported first-release formats

Support UTF-8 text/Markdown, DOCX, and text-readable PDF. Treat bibliographic metadata alone as a source record without full text. Do not automatically fetch a URL just because it appears in a reference. Pasted excerpts retain their provided attribution and an excerpt-only status.

Scanned documents, corrupted files, encrypted PDFs without accessible text, and unsupported embedded content require a supported replacement or an explicit later image-processing path. No silent OCR or unreported omission. A parser quality warning can downgrade the affected assessment scope.

For PDF, preserve page index and printed page label when detectable. For DOCX, use heading/paragraph/table-cell anchors rather than invent stable page numbers. For Markdown/text, preserve line or paragraph offsets. Existing page markers in converted Markdown can be retained but must be identified as supplied metadata.

### 16.2 Intake protection

Validate actual type, size, content, and decompression limits. Use generated storage names, quarantine, malware checks where supported, and parsers with least privilege and no network. Reject executable and macro-enabled content. Do not run embedded scripts, follow remote document links, or expose originals directly from a public web directory. These safeguards are informed by OWASP's file-upload guidance. [T4]

Suggested pilot operational limits are 25 MiB per file, 20 active files per run, and a total extracted-word admission limit configured before launch. These are tunable product limits, not scientific requirements. The configured token/context budget is authoritative for model admission, and excess content must trigger staged processing or an explicit narrower scope.

### 16.3 Extraction quality

Store page/section counts, detected tables, extraction errors, empty ranges, and whether figures contain unprocessed information. The app cannot assess an unparsed statistical table simply because nearby prose mentions it.

A content hash identifies the original bytes and a separate hash identifies the parsed representation. Parser upgrades produce a new extraction version and invalidate affected anchors only through an explicit remapping step. Historical anchors continue to point to their original representation until deletion.

### 16.4 Citation enforcement

Check that anchor IDs resolve to allowed document versions and that quoted text matches the stored passage. Mark punctuation/whitespace normalization explicitly. A citation to an article title does not satisfy a passage-level requirement for a claim about its mechanism.

Store the actual passage and context used in judgment, not only a model-written paraphrase. The source reader lets the researcher inspect the passage in context. Unavailable/deleted evidence produces a visible limitation, not a fabricated citation.

---

## 17. Model selection, context, cost, and failure controls

### 17.1 Selection policy

Select a capable model based on task-specific tests of source fidelity, argument interpretation, route discipline, and actionable feedback. Do not assume that the largest context window or highest price guarantees the best review. Do not silently substitute a weaker model when the configured model is unavailable.

The first release can use one provider and one approved model for substantive judgments. Cheap deterministic extraction should not become a paid reasoning task without a reason. Less expensive models may later handle demonstrated low-risk tasks, with regression testing.

Store the actual model identifier/version returned where available, configured reasoning/output limits, prompt IDs/hashes, schema version, and provider settings. Even with the same configuration, identical prose or ratings are not guaranteed; preserve the actual run results.

### 17.2 Context assembly

Every task receives the relevant policy clauses, accepted or explicitly provisional project objects, original source passages, scope and exclusions, and task-specific instructions. A compact global brief prevents isolated tasks from losing the central question.

Document summaries are lossy navigation aids. A decision-driving claim requires original supporting and potentially contrary material. Context overflow results in staged processing or an explicit partial scope, never silent deletion of inconvenient evidence.

### 17.3 Call and budget controls

Before a run, estimate input volume, expected output limits, selected reading depth, and an approximate cost range using a dated provider price card. State that the estimate is not a guarantee. The user authorizes a maximum spend or token allowance. Reserve budget for each stage, including checking and output.

Track all billed usage available from the provider, including relevant reasoning, cache, tool, and retry categories. Keep research time budgets in action planning separate from API computation budgets.

Use per-stage call caps, per-run caps, and a maximum correction count. The run pauses when remaining budget is insufficient; it does not choose a cheaper scientific standard silently. Display the available partial result and what would require more processing.

### 17.4 Failure behavior

| Failure | User-visible behavior |
|---|---|
| Model refusal or unsupported task | Explain the affected step, preserve work, do not manufacture a review |
| Incomplete or schema-invalid result | Retry within a small budgeted limit; otherwise mark stage incomplete |
| Source-link mismatch | Exclude or repair the claim; never present as verified |
| Source interpretation disputed | Show unresolved comparison or request focused recheck |
| Rate limit/provider outage | Pause/retry transparently; allow manual editing and export |
| Budget exceeded | Pause at boundary; show completed scope and authorized continuation option |
| Browser closed | Server-side job can continue if authorized; results persist under the existing retention policy |
| Worker restart | Resume from durable stage output without duplicate accepted effects |
| New revision during run | Finish against original snapshot; mark it as reviewing an earlier revision |
| Document deleted during run | Revoke use; cancel affected work and prevent its late outputs being published |

Structured-output documentation explicitly notes refusal and truncation cases. The app handles those as states, not as empty valid evaluations. [T1]

---

## 18. Privacy, security, and permitted use

### 18.1 Product use policy

The initial application is for researchers assessing their own work and other material they are authorized to process. It does not accept confidential manuscripts received in a peer-review role. This is a chosen product boundary; applicable journal, employer, funder, participant-consent, and contractual conditions still require review for particular material.

Do not accept identifiable participant data, sensitive interview records, or restricted datasets in the first pilot. Such inputs require an explicitly reviewed deployment and data-handling protocol, not a casual extension of the upload form.

A rights declaration is not a legal determination. Public expansion requires a review of document-processing rights, source-library licenses, terms, and privacy obligations. Do not redistribute the supplied scholarly readings or clone the source site's code/assets merely because they were accessible for personal research.

### 18.2 Data flow and model processing

Show what stays in the application, what is sent to the chosen model provider, and what optional services receive data. Explain whether full documents, selected passages, or images are submitted. No model calls occur before the applicable authorization.

Provider training use, provider retention, app storage, logs, and backups are separate controls. For example, OpenAI's documented API data controls distinguish default nontraining use from abuse-monitoring and application-state retention, and specify endpoint/model-dependent controls. No “zero retention” promise is inferred from a single request flag. Verify the selected service configuration before deployment. [T5]

The provider adapter must declare its retention and processing capabilities. A model fallback that changes the permitted data flow requires new authorization or is blocked.

### 18.3 Isolation and least privilege

Enforce workspace and project authorization in the API, retrieval, background jobs, exports, and file access. Add database row-level controls where appropriate as defense in depth, not a replacement for application authorization. PostgreSQL documents that table owners and bypass roles can evade ordinary row policies; service roles and worker access must be designed and tested accordingly. [T6]

No cross-user retrieval or content cache is allowed. Similar documents uploaded by different users must not expose each other's existence, filenames, extracts, or analyses. Reuse within a project requires matching scope, content, and permission checks.

### 18.4 Prompt injection and untrusted content

Treat uploaded manuscripts, papers, excerpts, metadata, and retrieved text as evidence, not instructions. The model receives clear data boundaries, but boundary text alone is not a security control.

Restrict document-reading tasks to authorized evidence access and structured output. They cannot execute code, call arbitrary URLs, change rules, access secrets, or send data. Validate output references and render generated content safely. Prompt-injection risks through documents and retrieval are documented by OWASP. [T7]

A malicious passage asking the app to award all tens may remain visible as source content, but cannot alter the policy manifest or automatically fill semantic findings. Adversarial tests must exercise both model manipulation and unauthorized data access.

### 18.5 Logging and storage

Use encrypted storage and transport in hosted deployment. Secrets stay server-side, outside project exports and prompts. Log job IDs, timings, token usage, safe error categories, and configuration hashes by default, not manuscript text or full prompts in general telemetry.

Scientific run artifacts may retain the context needed to inspect an assessment under the same protection and retention as the project. They are distinct from general diagnostic logs. Avoid third-party session replay or analytics that capture document or review text.

### 18.6 Deletion and retention

The deployment must publish concrete retention periods for originals, extracted text, project revisions, review artifacts, indexes/embeddings, caches, logs, exports, and backups before inviting users. Do not deploy with an indefinite undocumented retention default.

Deleting a project immediately revokes ordinary access and prevents new processing. A deletion job removes originals and derivatives from live storage, pending jobs, indexes, and caches, and records only a noncontent deletion receipt. Backups expire under the disclosed schedule; a restore must replay deletion records so deleted projects do not reappear.

Where provider-side deletion or expiry is relevant, track it separately. Do not claim that app deletion retracts already transmitted content from every external system. Export links must be short-lived and permission checked.

### 18.7 Later external search

External discovery is off in the first release. A later module must disclose query contents and destinations. It should default to general concepts and known-public identifiers rather than distinctive unpublished paragraphs. User approval is needed when a search would disclose more. Link fetching requires allowlists, redirect validation, private-network blocking, and acquisition-rights checks.

---

## 19. Import, export, and portability

### 19.1 Exports

Provide a readable Markdown review, a Markdown development plan, and a versioned JSON project export. The structured export contains project records, evidence relations, source metadata, review scope, provenance, assessment configuration, rule traces, and action history. No API keys or privileged internal references appear.

Original copyrighted source files are excluded from ordinary review export. An explicit authorized project bundle can include selected originals in a later option, with a separate confirmation. Reports and excerpts remain subject to appropriate confidentiality and reuse restrictions.

### 19.2 Import

Import the app's own schema versions with validation, ownership reassignment to the current user, and explicit migration. Imported assertions preserve their reported provenance but do not gain verified status merely because they contain a field named `verified`.

Aguinis exports may be retained as external reference material or mapped only where meaningful data exists. The supplied empty-state default reports must not seed ratings or project facts. Do not equate the filenames' numeric suffixes with fifteen distinct application modules.

### 19.3 Reproducibility

An exported review records the rubric version, snapshot ID, model/prompt configuration, supplied-source coverage, and calculation trace. Exported source anchors identify the local document version; an absent original may prevent a new reader from verifying it, and that limitation must remain visible.

Reimporting an old report displays a historical evaluation. It does not update the current project score until a new authorized assessment is performed.

---

## 20. Operational and accessibility requirements

### 20.1 Proposed service targets

Targets are acceptance goals to test, not current performance claims. The interface should respond to local navigation without a model call, acknowledge job creation promptly, autosave ordinary edits with a visible state, and recover unsent edits after a transient connection failure within the chosen security policy.

Measure evaluation latency by task, document size, and depth. Do not promise a fixed whole-review turnaround until actual usage has been tested. Show stages and available results rather than an invented percent complete.

For the pilot, allow one active full evaluation per user and bounded worker concurrency. This is a cost/reliability default, not a product limitation that must remain forever.

### 20.2 Accessibility

Use semantic labels, keyboard navigation, visible focus, accessible dialogs, adequate contrast, readable text, and noncolor status indicators. Wide tables must have a usable narrow-screen alternative. A source drawer must not trap focus or hide the main task without a way back.

No important meaning depends on a hover-only tooltip, animation, or a radar chart. Explain technical rubric labels in ordinary language without changing their underlying meaning.

### 20.3 Recovery and support

Provide a safe error identifier for support without exposing content. Preserve successful manual work when model processing fails. Give users a project export before risky migrations. Backups and restores must be tested, not merely configured.

Maintain a run manifest that can explain which stage failed, what data was sent, and which outputs were actually saved. Never display “full review complete” when a required stage is missing.

---

## 21. Testing, evaluations, and release gates

### 21.1 Separate deterministic correctness from research judgment

Deterministic tests should be exact. Model judgment evaluations require expert review, scope-aware interpretation, and documented disagreement. A finite evaluation set does not establish universal correctness. V4 calls for an anchor-and-reliability pilot and warns against interpreting repeated model agreement as human validation. [R4, §15]

### 21.2 Deterministic golden cases

Required tests include:

| Fixture | Expected behavior |
|---|---|
| All eligible ratings = 5 | Uncapped I, D, P equal 50 |
| All ratings = 8 with valid benchmark records | Uncapped I, D, P equal 80; labels still depend on prerequisites |
| All theory ratings = 7, no study | I = 70; D and P pending; no project endorsement |
| ESTABLISH or TEST with an assessable study | D may exist; I and P not applicable |
| Unarticulated discovery account | No invented theory total |
| Required uninspected dimension | Affected total withheld |
| Unsupported asserted premise without plan | d1 maximum 3 and I cap 39 |
| Credible plan, unsupported premise | Conditional label and appropriate commitment restriction, not invented empirical support |
| I_uncapped = 80, D = 30, design mismatch | P_uncapped = 55; P_raw = 39; I retained |
| Idea cap with otherwise strong study | Cap propagates through I before project caps |
| Unrounded I = 69.6 | Displays 70 but fails ≥70 gate |
| Rating ≥8 with no benchmark | Invalid for publication as an exceptional rating |
| V branches 70 and 54, p=.8 | V=66.8; current score unchanged |
| STOP branch with no comparable alternative | V withheld, qualitative branch retained |
| Incomparable route/base or probabilities not summing to 1 | Calculation rejected |
| Source/project access removed | Retrieval and late task publication denied |

Use explicit synthetic conditions to isolate each rule. A numeric test does not bypass the source and stage validation required in a real run.

### 21.3 Research-evaluation set

Build a fixed set of authorized cases covering early ideas, full explanations, discovery, direct testing, quantitative designs, and qualitative/process accounts. Include both real weaknesses and deliberately sound cases to measure false objections.

Important fixtures include a close predecessor using different terminology; a genuine boundary contribution; an explanation in an appendix; a hypothesis already weakened in the discussion; an unsupported claimed regularity; a null but precise test; a changed construct whose measure is no longer valid; and a revision that resolves the original objection.

Annotate the intended contribution, closest supplied sources, valid objections, invalid objections, necessary checks, and acceptable action families. Expert evaluators may disagree; record the basis rather than force a single “correct” score for every idea.

### 21.4 What to measure

Measure source-attribution fidelity, unsupported decision-driving claims, false blocking objections, missed important issues, route-rule compliance, action relevance, preservation of the core insight, and recognition of resolved issues. Also measure token cost, latency, retry behavior, and coverage gaps.

Assess the accuracy of source retrieval separately from the quality of the model's interpretation. Compare the app to a straightforward v4 prompt on the same material, budget, and model. A complex workflow that is not more useful or reliable should be simplified.

Use fresh, blinded expert judgments of before/after cases where possible. Do not optimize to make the same rubric scorer congratulate its own edits. Provider evaluation guidance also recommends task-specific tests and human calibration rather than generic model scores. [T8]

### 21.5 Release gate

Before private pilot, require all deterministic rules and permission tests to pass; all decision-driving citations in release fixtures to resolve; no known critical source fabrication or rule bypass left unaddressed; and human inspection of the pilot reports showing that they provide a usable contribution, obstacle, and next action.

Before inviting other users, add isolation, deletion/restore, malicious-upload, prompt-injection, cost-abuse, and authorization regression tests. A single known critical disclosure path blocks release. No test suite is described as proving complete security.

Choose numerical quality targets after measuring a baseline and before evaluating a candidate release. Do not invent a “95% expert-level” claim without a definition, appropriate sample, and uncertainty.

---

## 22. Build stages and acceptance criteria

### Stage A: policy and project record

Implement typed project objects, source identifiers, accepted/proposed distinction, snapshots, and the pure rubric engine. Use manual assessment fixtures. No paid model calls are needed to validate arithmetic and route behavior.

**Exit:** Golden rule tests pass; export/import preserves nulls and statuses; no duplicated scoring logic; original inputs remain separate from proposed edits.

### Stage B: one end-to-end source-grounded review

Implement intake, text/Markdown and text-readable PDF processing, source anchors, one model adapter, interpretation review, a bounded evaluation, and a Markdown report. Add DOCX support within this stage only when its anchors and table handling pass tests.

**Exit:** One idea and a small supplied packet can produce a review whose principal source claims and next action a human can inspect. Known missing or unreadable text does not produce a false complete assessment.

### Stage C: working features and revision loop

Implement the brief, literature, argument, alternatives, study, usefulness, review, and actions views over shared records. Add proposal acceptance, responses to objections, dependency invalidation, and revision comparison.

**Exit:** A user can fix an issue in its workspace and see a new review accurately recognize the change without losing prior evidence or rewriting the original version. A two-account comparison flows through to a study contrast and a bounded action.

### Stage D: private-pilot reliability

Add durable jobs, cost reservations, cancellation, controlled retries, source-coverage reporting, secure hosted deployment if selected, deletion, backups, and the research-evaluation harness.

**Exit:** The pilot survives failed calls, restarts, partial documents, malicious text, and user edits during runs without corrupting results or silently expanding data access or spend.

### Stage E: invitation-only expansion

Add tested multi-user isolation and optional coauthor permissions, with disclosure/rights review, support procedures, and a defined retention policy.

**Exit:** Another researcher can use the app without access to the owner's research, and project deletion is demonstrably enforced through all derived stores and restore processes.

### Later, only after evidence of need

External literature discovery; broader domain libraries; local inference; richer visual argument maps; permitted statistical checks; team workflows; and public commercial access. Each requires a separate decision record, tests, and data-flow review. Do not smuggle these into prompts while their service boundaries are absent.

---

## 23. Architecture governance for AI-assisted development

### 23.1 Repository layout

```text
research-workbench/
  docs/
    product-spec.md
    decisions/
    threat-model.md
    data-flow.md
    acceptance-cases.md
  policies/
    rubric-v4.md
    rubric-v4.manifest.json
    rubric-v4.test-fixtures.json
  backend/
    domain/
      projects/
      sources/
      assessments/
      actions/
      history/
    services/
      ingestion/
      retrieval/
      workflow/
      verification/
      reports/
    policy_engine/
    model_adapters/
    api/
    workers/
    persistence/
  frontend/
    components/
    features/
    generated-contracts/
  prompts/
    extraction/
    source-reading/
    evaluation/
    checking/
    development/
  evals/
    fixtures/
    annotations/
    harness/
  tests/
    unit/
    integration/
    security/
    end-to-end/
  deploy/
```

This is an ownership map, not a demand to create empty abstraction layers for every possible feature. Shared contracts should be generated where practical; avoid manually synchronizing incompatible schemas.

### 23.2 Change requirements

Every build task specifies its user-visible outcome, allowed modules, input/output contract, tests, and exclusions. A change that alters route interpretation, ratings, evidence requirements, or output labels requires policy-impact review.

Reject changes that let UI code compute final grades, let model text become SQL or permissions, let generated prose become an authoritative source, or let convenience data silently replace the research question.

Record architecture decisions for provider selection, queue implementation, source parsing, schema ownership, and deployment. Do not add a new agent, database, external service, or background loop without documenting why an existing module is insufficient.

### 23.3 Definition of done

A feature is done when its behavior matches the spec, typed contracts and permissions are enforced, acceptance tests pass, failures are visible, data flow and deletion are covered, the relevant documentation is updated, and no unrelated research or infrastructure capability has been added.

A prompt is versioned code for evaluation purposes. Prompt edits require tests just as calculation changes do. Human approval of a code change does not count as evidence that the model's scientific judgments improved.

---

## 24. Requirement-to-rubric traceability

| V4 section | App implementation | Important acceptance check |
|---|---|---|
| 1 Decisions and quick use | Initial screen/full evaluation, distinct outputs | No full-review claim from a short screen |
| 2 Route, stage, status | Intake, route classifier, router, state model | No invented mechanism for discovery/TEST |
| 3 Scales and ratings | Policy manifest, integer validation, benchmark guard | No default midpoint or unsupported 8+ |
| 4 Theory dimensions | Argument, literature, alternatives, usefulness | Distinct rationale per dimension |
| 5 Study dimensions | Study workspace and evaluator | Design assessment not method-name ranking |
| 6 Cross-checks | Grounding, source comparisons, promise map | Source accuracy and coverage remain separate |
| 7 Support audit | Method-appropriate evidence/check records | Reported analysis not app reproduction |
| 8 Calculations and gates | Pure policy engine and trace | Caps, rounding, readiness, and route exclusions exact |
| 9 Procedure | Bounded evaluation workflow | Intellectual/evidence/development tasks remain distinct |
| 10 Usefulness | Selective audience/use profiles | No five-impact checklist score |
| 11 Repair | Issues, response workflow, action templates | Preserve core insight; pivot not silent repair |
| 12 Next investment | Branch planning and optional arithmetic | STOP/inconclusive valid without fabricated V |
| 13 Comparing ideas | Initially version comparisons; later explicit project comparison | No cross-route or unequal-coverage ranking |
| 14 Worked examples | Golden tests and demo fixtures | Examples not actual project ratings |
| 15 Calibration | Evaluation harness and release gates | Model agreement not human validation |
| 16 Templates | Review renderer and exports | Complete required records at declared scope |
| 17 Source basis | References and policy documentation | Source-derived rule separated from app convention |
| 18 Version changes | Policy migration and report history | No silent reinterpretation of old scores |

The first release need not expose a multi-project ranking screen to preserve Section 13's restrictions. Those restrictions apply whenever comparison is attempted, including optional later features.

---

## 25. Decisions to resolve before deployment

The specification chooses the product shape. The following deployment decisions require evidence or owner authorization, not invention by a coding assistant:

| Decision | Default direction | Evidence or approval required |
|---|---|---|
| Model/provider | One capable structured-output model via adapter | Comparative task tests and permissible data-processing terms |
| Hosting | Private local development, then restricted hosted pilot if needed | Actual storage region, identity, retention, and backup configuration |
| Per-run budget | Explicit bounded budget, no unlimited default | Dated rates, measured token usage, user-approved cap |
| Active packet limit | Small supplied packet with visible admission limits | Parsing/context/cost tests, not an arbitrary scientific source count |
| Uploaded document rights | Process only authorized material; no public redistribution | Review before public/commercial expansion |
| Human evaluation set | Authorized examples and identified expert assessors | Consent, storage policy, blinded comparison design |
| New user access | Invitation-only after isolation tests | Security and deletion review |

None blocks writing the domain model, policy engine, manual workspaces, or mocked workflow. They do block pretending that an untested deployment is ready for confidential third-party material.

---

## 26. References and source-use limits

### Governing and design sources

**[R4]** *Research Idea Evaluation and Development Protocol, Version 4*, October 2, 2026. Supplied file: `Research_Idea_Rubric_v4.md`. Companion: `Research_Idea_Rubric_v4_Evaluation_Card.md`. Section citations in this specification refer to that fixed file. V4 is source-informed but its numerical conventions and contribution categories are not empirically calibrated editorial rules.

**[B]** Herman Aguinis, *Theory Contribution Builder*. User-supplied source page: `https://www.hermanaguinis.com/theorycontribution.html`. Evidence used here: fifteen supplied JSON exports and the supplied Section 6 screenshot. The exports have empty state objects and the same default report content after whitespace normalization. They supply visible topic/feature prompts, not the app's hidden implementation or full book contents. This specification does not copy its scorecard, code, site styling, or automatic defense statements.

**[H]** Grant, A. M., and Pollock, T. G. (2011). *Publishing in AMJ, Part 3: Setting the Hook*. Supplied article. Used for concise statement of the question, existing knowledge, and promised contribution; v4's rules govern evaluation rather than rhetorical polish.

**[C]** Dorobantu, S., Gruber, M., Ravasi, D., and Wellman, N. (2024). *The AMJ Management Research Canvas: A Tool for Conducting and Reporting Empirical Research*. Supplied article. Its emphasis on connected elements and iteration informs the workspace concept, not a copied interface.

**[L]** Lepak, D. P. (2009), *What Is Good Reviewing?*, and Ballinger, G. A., and Johnson, R. E. (2015), *Your First AMR Review*. Supplied articles. Their developmental-review principles are represented through v4's insight-preservation, reasons, recommendations, and recognition requirements.

The other supplied scholarly sources remain part of v4's reference base. This specification implements v4 rather than independently inventing a different criterion for each reading. References in an article are not represented as separately inspected originals. No source in this set prescribes the web stack, job queue, API schemas, or security controls proposed here.

### External technical references checked for this specification

These support limited technical capabilities or risks, not validation of the product's scientific judgments. Provider policies and software capabilities must be rechecked at implementation/deployment.

**[T1]** OpenAI, *Structured model outputs*, and *Introducing Structured Outputs in the API*. Schema-constrained output, incomplete/refused-output handling, and the distinction between schema correctness and mistakes within values. `https://developers.openai.com/api/docs/guides/structured-outputs` and `https://openai.com/index/introducing-structured-outputs-in-the-api/`

**[T2]** FastAPI, *Features*. OpenAPI, JSON Schema, and Pydantic-based data validation. `https://fastapi.tiangolo.com/features/`

**[T3]** PostgreSQL, *Full Text Search*. Basis for an initial in-database lexical retrieval implementation. `https://www.postgresql.org/docs/current/textsearch.html`

**[T4]** OWASP Cheat Sheet Series, *File Upload*. Validation, restricted file handling, and storage/processing safeguards. `https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html`

**[T5]** OpenAI, *Data controls in the OpenAI platform*. Distinguishes training use, abuse-monitoring retention, application state, and service-dependent controls. `https://developers.openai.com/api/docs/guides/your-data`

**[T6]** PostgreSQL, *Row Security Policies*. Default-deny behavior after row security is enabled, and exceptions for owners/bypass roles. `https://www.postgresql.org/docs/15/ddl-rowsecurity.html`

**[T7]** OWASP Cheat Sheet Series, *LLM Prompt Injection Prevention*. Documents risks through untrusted documents and retrieval; supports least-privilege and explicit tool/data boundaries. `https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html`

**[T8]** OpenAI, *Evaluation best practices*. Task-specific evaluation and human calibration. `https://developers.openai.com/api/docs/guides/evaluation-best-practices`

---

## Final product contract

**A few user inputs create an editable, source-linked research record. Bounded LLM tasks interpret and evaluate it. Deterministic rules enforce the rubric. The researcher can inspect, correct, and develop the work without losing what was originally claimed. The output is a justified assessment and a next research action, not a certificate of originality or a promise of publication.**
