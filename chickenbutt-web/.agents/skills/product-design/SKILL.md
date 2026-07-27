---
name: product-design
description: |
  Defining and validating product behaviour, user workflows, information architecture, interaction requirements, states, and product-level acceptance criteria.
  Execute when translating user requests into workflows, state specifications, content hierarchies, or product specifications.

  Trigger immediately for:
  - Defining entry points, transitions, success, failure, and recovery paths for user actions.
  - Specifying information hierarchy, content prominence, and data groupings.
  - Designing product-level acceptance criteria.

  DO NOT trigger for:
  - Visual styling, layout aesthetics, color, typography, or branding.
  - Writing final interface copy, labels, error messages, or marketing copy.
  - Production software implementation or code modification.
  - Independent verification of implemented behaviour.
---

# Product Design

This skill governs the definition, scoping, and validation of user workflows, behavioral states, information architecture, and product acceptance criteria.

## Purpose and Exclusive Responsibility
- **Goal**: Define coherent, evidence-grounded product behaviour, user workflows, information architecture, interaction states, and observable product acceptance criteria within granted authority.
- **Exclusive Responsibility**: Define intended product behaviour, user workflows, information architecture, interaction requirements, states, and product-level acceptance criteria. Evaluate the internal coherence and problem-solution fit of the proposed specification, but do not independently verify implemented behaviour.

## Responsibility Boundaries
- **Primary Responsibility**: Identifying users and objectives, translating product requests into workflows, defining transitions/states, defining information hierarchy, evaluating features against user problems, producing product specifications/criteria, and identifying exclusions/assumptions.
- **Adjacent Responsibilities**: Consumes task frames from `task-framing` and hands approved specifications, as applicable, to `visual-design`, `ux-writing`, `software-development` (jointly with the installed `frontend-development` specialist when the implementation surface is frontend), and `testing-and-verification` when independent verification is required — not every product-design task requires every downstream discipline.
- **Explicit Exclusions**: Does not own visual styling (colors, typography, branding, aesthetic direction), final interface/marketing copy, production implementation, independent verification, material architecture/dependencies/schema/security decisions, or business/monetization policy.
  - Approved screenshots, prototypes, product documents, schemas, contracts, copy, and current behaviour may serve as controlling evidence. Product design interprets their behavioural implications but does not redefine approved visual direction, final wording, architecture, or implementation.
  - Excludes editorial and public-copy decisions, security-policy decisions, licensing and cost decisions, dependency selection, and changes to expected results that are not already authorized.
- **Handoff Conditions**: After the product behaviour and workflow specification is complete, hand behavioural requirements, as applicable, to `visual-design`, `ux-writing`, and `software-development` (jointly with `frontend-development` when the implementation surface is frontend); hand observable criteria to `testing-and-verification` when independent verification is required. Return unresolved material product decisions to `task-framing`.

## Activation and Non-Activation Conditions
- **Activation**: Triggers when translating bounded product requests into workflows, defining state coverage, mapping information architecture, or designing product specifications.
  - Validate the proposed workflow through scenario walkthroughs to evaluate specification coherence.
- **Non-Activation**: Does not trigger for visual design, writing copy, coding, or independent validation. Does not trigger merely because the deliverable is a website — a public, expressive, or editorial surface with no accounts, workflows, permissions, or state-changing interactions may proceed directly from `creative-direction` and `visual-design` without a product-design specification. This skill activates only when there is actual behaviour, information architecture, forms, transactions, or interaction-state logic requiring definition.

## Required Inputs
- Original request or valid task frame.
- Target users or roles, when known.
- Stated user problem and intended outcome.
- Current workflows, screenshots, prototypes, product documents, schemas, or application behaviour relevant to the request.
- Known business rules, permissions, constraints, and acceptance criteria.
- Controlling user decisions and reference assets.
- *Note*: Not all inputs must exist; explicitly identify missing information that materially affects the workflow.

## Authority Boundaries
- **Authorized Actions**:
  - Inspect only task-relevant workflows, application surfaces, and configuration.
  - Define information groupings, prominence, ordering, persistence, feedback, and discoverability.
  - Define product-level state transitions and acceptance criteria.
- **Unauthorized Actions**:
  - Prescribing colors, font families, shadows, exact styling, or aesthetic direction.
  - Choosing final visual styling or final copy labels.
  - Modifying production source code or production configuration.
  - Product design may challenge whether a proposed solution addresses the stated problem, but it must not silently reject or replace an explicit user-selected feature. It must present the mismatch, consequences, and behavioural alternatives for authorization.

## Ordered Procedure
1. **Confirm Boundary**: Confirm the task boundary and product-design authority.
2. **Identify Objectives**: Identify the user, problem, and intended outcome.
3. **Inspect Current State**: Inspect task-relevant workflows and controlling evidence. Map the current workflow where one exists, and distinguish observed implementation, documented intent, user-approved behaviour, and model assumptions. Do not mistake existing implementation for approved product policy.
4. **Identify Friction**: Identify friction, ambiguity, missing states, and policy assumptions.
5. **Define Proposed Workflow**: Define the proposed workflow and state model.
6. **Classify Decisions**: Separate observed constraints, bounded decisions, and unresolved material decisions.
7. **Define Information Architecture**: Define information and content requirements.
8. **Define Product Acceptance Criteria**: Define observable product acceptance criteria.
9. **Review Consequences**: Review cross-workflow consequences and explicit exclusions.
10. **Produce Specification**: Produce the product specification and handoff package.

## Evidence Requirements
- **Actionability**: Every procedural step must use imperative language and identify a concrete action plus its expected outcome or validation evidence.
- **Demonstrated Execution**: Include concrete examples demonstrating:
  - a bounded workflow improvement governed by approved conventions;
  - information hierarchy without visual styling;
  - a workflow blocked by unresolved permissions or ownership policy, when the product involves accounts or shared data;
  - a proposed feature whose solution does not match the stated user problem and therefore requires reframing approval;
  - defining the workflow and information hierarchy for a public, non-transactional surface (for example, an editorial, portfolio, or campaign page) with no accounts, permissions, or persisted user data.
  - Product-design evidence may include: explicit user decisions, approved workflows, screenshots/prototypes, schemas/permission models, scenario walkthroughs, state matrices, and criteria reviews. Existing implementation is evidence of current behaviour, not automatic authority for intended behaviour.

## Exact Deliverables
A bounded product-design specification or workflow package containing the fields required for the task’s complexity. It may be internal, conversational, or persisted when operationally valuable:
- product problem and intended outcome;
- users or roles;
- current-state findings;
- proposed workflow;
- state coverage;
- information and content requirements;
- observed constraints;
- authorized bounded decisions;
- unresolved material decisions;
- explicit exclusions;
- product acceptance criteria;
- downstream handoffs;
- residual assumptions or risks.

## Validation Gates
Before claiming the product specification complete:
- [ ] **User and Objective Check**: User and objective are identified where relevant.
- [ ] **Current vs. Intended separation**: Current and intended behaviour are distinguished.
- [ ] **Workflow Integrity**: Workflow entry, success, failure, and recovery paths are covered.
- [ ] **State Coverage**: Relevant states (initial/default, loading or processing, empty, partial, success, validation error, system error, offline or unavailable dependency, disabled, permission denied, destructive confirmation, undo or recovery, stale or conflicting data, first-time versus returning user) are accounted for, stating why each matters. Do not manufacture states that cannot occur.
- [ ] **Visibility & Permissions Check**: Permissions and visibility are defined where applicable.
- [ ] **Decision Separation**: Bounded and material decisions are separated. Unresolved material decisions are not disguised as recommendations.
- [ ] **Acceptance Criteria check**: Acceptance criteria describe observable product behaviour, not implementation details (e.g. defines actors, actions, expected system behaviour, completion state).
- [ ] **No Styling/Implementation Leaks**: Visual styling and implementation details have not leaked into the specification without authorization.
- [ ] **Copy Integrity**: Final copy has not been invented where a copy skill should own it.
- [ ] **Handoff Clarity**: Downstream handoffs are explicit.
- [ ] **Exclusions & Assumptions Check**: Assumptions and exclusions are documented.
- [ ] **Scenario Walkthrough Verification**: Walk through representative scenarios covering normal completion, relevant failure/invalid-input path, permission-restricted path, recovery/continuation path, and cross-workflow consequences to validate the coherence of the proposed specification.
- [ ] **No Placeholders**: No TODOs, accidental placeholders, or unresolved drafting markers remain. Clearly defined metavariables (such as `<role-name>`) are permitted.
- [ ] **Link Verification**: Apply link verification only when the task creates or modifies links.

## Stop and Failure Conditions
- **Halt Execution immediately when**:
  - An unresolved material product decision prevents defining a valid workflow.
  - Roles, permissions, ownership, or business rules are contradictory and cannot be resolved from controlling evidence.
  - The requested workflow would require unauthorized privacy, security, legal, financial, licensing, or policy decisions.
  - Available evidence cannot establish what product problem is being solved.
- **On Failure**: Preserve partial workflow designs and specifications. Report the exact blocker, missing context, and whether it requires a policy clarification. Do not stop for minor reversible details.

## Prohibited Behaviours
- **Aesthetic Prescription**: Choosing color, fonts, or stylistic layout elements.
- **Silent Business Rules**: Making silent assumptions about user data ownership, monetization, or permissions.
- **Placeholder Final Copy**: Fabricating final marketing or interface copy rather than identifying content requirements.

## Workflow Model
For each workflow, define the elements that actually apply to it; omit elements the workflow does not involve rather than forcing a value:
- actor or role;
- entry point;
- prerequisite state;
- user objective;
- sequence of user actions;
- system responses;
- data created, changed, displayed, or persisted, when the workflow involves data;
- permissions and visibility, when access is restricted;
- success state;
- alternate paths;
- failure and recovery paths;
- exit or continuation points.

A workflow with no persisted data, accounts, or restricted access (for example, a public reading or exploration path) still defines actor, objective, sequence, system response, and success/failure/exit — it simply has no applicable entry for data persistence or permissions.

## State Coverage
Evaluate, where applicable:
- **initial/default**: The workflow’s normal starting state before the relevant action begins.
- **loading or processing**: The system is retrieving information or completing an action.
- **empty**: No applicable records or content exist.
- **partial**: Some required or expected information exists, but the workflow or record is incomplete.
- **success**: The intended product outcome has been reached.
- **validation error**: User-provided information does not satisfy an established rule.
- **system error**: The system cannot complete the requested action.
- **offline or unavailable dependency**: Required connectivity, service, or dependency is unavailable.
- **disabled**: An action is unavailable because of current state, permissions, or rules.
- **permission denied**: The actor lacks authority to view or perform the action.
- **destructive confirmation**: The product requires explicit confirmation before a consequential action.
- **undo or recovery**: The actor can reverse, retry, or recover from an action or failure.
- **stale or conflicting data**: Displayed or submitted information conflicts with newer or concurrent state.
- **first-time versus returning user**: The workflow differs based on prior setup, history, or familiarity.

State why each included state matters. Do not manufacture states that cannot occur.

## Information Architecture
The skill may define:
- what information belongs together;
- hierarchy and ordering;
- global versus object-specific information;
- navigation relationships;
- persistence and contextual visibility;
- search, filter, grouping, collapsing, and permission visibility requirements;
- labels or content areas that require UX-writing work.

It must not choose exact visual styling or final wording unless those have already been supplied and approved.

## Product Acceptance Criteria
Every criterion should identify, where applicable:
- actor;
- action or triggering condition;
- expected system behaviour;
- observable completion state;
- relevant failure, recovery, or permission behaviour.

Criteria must describe product behaviour rather than implementation or aesthetics.
- *Prefer*: "A user can identify records requiring attention without opening each record."
- *Avoid*: "Render red cards with a React map.", "Make the dashboard intuitive.", "Use a beautiful responsive layout."

## Decision Classification
- **Observed Constraint**: Behaviour required by existing approved rules, data, or platform limitations. Existing implementation is an observed constraint only when the task requires preserving it or controlling evidence approves it. Existing behaviour alone does not make a workflow decision authoritative.
- **Bounded Product Decision**: A reversible workflow detail clearly determined by the task, references, or established product conventions.
- **Material Product Decision**: A choice that meaningfully changes user roles, workflow, permissions, data ownership, public meaning, business rules, scope, monetization, safety, privacy, or acceptance criteria. Material escalation applies when a choice changes accessibility policy, supported user groups, accommodation scope, or product behaviour and controlling evidence does not resolve it.

## Conflict-Resolution and Evidence Hierarchy
This hierarchy resolves conflicts among workspace instructions and skill documents. It does not override platform-level, system-level, safety, security, or tool-use requirements governing the agent.
- **Conflict Resolution**:
  1. User's explicit instructions in the current prompt.
  2. Workspace rules (`AGENTS.md` or equivalent).
  3. Governing standard (`.agents/skills/skill-authoring-standard/SKILL.md`).
  4. Individual skill `SKILL.md`.
  5. Global agent guidelines.
- **Evidence Hierarchy (Source of Truth)**:
  The applicable evidence depends on the discipline.
  1. Explicit user instructions and decisions from the current task.
  2. Supplied acceptance criteria, screenshots, prototypes, examples, and reference assets.
  3. Observable behaviour and direct execution evidence.
  4. Current workspace files, schemas, architecture, and established conventions.
  5. Tests, compiler output, lint results, and runtime logs where applicable.
  6. Project documentation.
  7. External authoritative references.
  8. Skill defaults and model assumptions.

## Concrete Usage Examples

> [!NOTE]
> Named execution skills, commands, files, paths, users, products, or workflows in these examples are hypothetical unless explicitly identified as existing.

### Example 1: Bounded Workflow Improvement (Archiving)
- **Task**: Improve the record-archiving workflow in a hypothetical record-management system.
- **Controlling Evidence**: Project product definitions establish that "archive" means a reversible status change rather than hard deletion. (If deletion-versus-archival semantics were unresolved, it would be a Material Product Decision).
- **Classification**: Bounded Product Decision (workflow details governed by conventions).
- **Proposed Workflow**:
  - Actor: Authorized staff member.
  - Entry Point: Record details page.
  - Sequence: Click to *initiate archive* -> system displays a confirmation dialog. Click to *confirm archive* -> record status set to "Archived", record removed from the active record list, system shows success feedback.
  - Alt Path: Click to *cancel* -> modal closes, state remains unchanged.
  - Visual/Copy handoff: Specify that a confirmation check and feedback are required. Exact button labels and confirmation wording belong to UX writing unless already supplied and approved. Modal layout is handed to visual design.

### Example 2: Information Hierarchy for a Record Alert Dashboard
- **Task**: Define information hierarchy for a record alert dashboard.
- **Design Boundary**: The specification details what information must be grouped and prioritized, avoiding aesthetic layout details:
  1. **Primary Grouping**: Records requiring immediate feedback (unreviewed submissions). This section must be persistent and prominently ordered at the top.
  2. **Secondary Grouping**: Records approaching a scheduled status deadline this week. This section is collapsible.
  3. **Content Requirement**: Each alert item must expose the record's name, alert age (time elapsed), and a link to the related submission.
  4. **No styling leak**: Hand visual realization and layout composition to visual design.

### Example 3: Workflow Blocked by Unresolved Permissions / Data-Ownership Policy
- **Task**: Allow authorized staff to share records with other authorized staff.
- **Analysis**:
  - Exposes privacy questions: Does sharing grant read-only or read-write access? Can a staff member who receives access invite other staff? Who retains ownership if the original staff account is closed?
- **Classification**: Material Product Decision (Blocked).
- **Action**: Stop execution. Report:
  - *Completed*: Identified actors, sharing entry point, required permission questions, visibility consequences, revocation needs, and ownership-policy gaps.
  - *Blocker*: User authorization is required for read/write permissions, onward sharing, revocation, and ownership after account closure.

### Example 4: Proposed Feature Requiring Reframing Approval
- **Task**: "Add a chat bot to the workspace so users can ask why their service request hasn't received a response."
- **Analysis**:
  - Stated user problem: Users feel anxious when staff take more than 24 hours to respond to a service request.
  - Chatbot Mismatch: A chatbot may address uncertainty in some form, but it does not itself improve staff response time and may create unsupported claims about availability.
  - Action: Identify the chatbot-responsiveness mismatch and document risks and unsupported assumptions.
  - Behavioural Alternatives: Propose options such as response-status visibility, expectation-setting (e.g. displaying staff response-time targets), escalation workflows, or automated acknowledgements. Document required product data for each option (e.g., staff availability configuration or unreviewed service-request timestamps).
  - Classification: Material Product Decision (Replacing or choosing the requested chatbot approach changes agreed scope).
  - Handoff: Return the decision, consequences, and behavioural alternatives to `task-framing` or user approval. Do not assume schedules exist and do not write final interface copy.

### Example 5: Workflow and Information Hierarchy for a Public Editorial Page
- **Task**: Define the workflow and information hierarchy for a long-form public article page with no accounts, permissions, or persisted user data.
- **Controlling Evidence**: The site has no login, no user-specific data, and no destructive or state-changing actions; its purpose is reading and discovery.
- **Proposed Workflow**:
  - Actor: Public reader.
  - Entry Point: Article link from a listing page or external referral.
  - Sequence: Reader lands on the article, reads the primary content, optionally follows related-article links or shares the page.
  - System Response: Article renders; related-content links are surfaced at defined points; no data is created, changed, or persisted by the reader's visit.
  - Success State: Reader reaches the end of the article or a related-content link.
  - Failure/Recovery: A broken related-content link falls back to the listing page rather than a dead end.
  - No applicable entries: no permissions, no destructive confirmation, no persisted user data — per the Workflow Model, these are correctly omitted rather than fabricated.
- **Information Architecture**: Primary grouping is the article body and its immediate supporting media; secondary grouping is related/further-reading links, ordered by relevance rather than recency; no permission-visibility requirement applies.
- **Visual/Copy handoff**: Hand composition and hierarchy expression to `visual-design`, informed by any approved creative brief; hand headline/deck/body voice to `copywriting` rather than `ux-writing`, since this is public-facing editorial language, not interface utility copy.
