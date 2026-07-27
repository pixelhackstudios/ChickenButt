---
name: task-framing
description: |
  Converts user requests into a bounded execution contract (task frame) before starting work.
  Execute when framing would materially reduce ambiguity, scope creep, conflicting assumptions, or execution risk.

  Trigger immediately for:
  - ambiguous, complex, cross-disciplinary, destructive, or multi-stage tasks;
  - requests containing unresolved material decisions;
  - significant scope changes or blockers that invalidate the existing frame.

  DO NOT trigger for:
  - clear, bounded tasks that can be executed directly;
  - minor corrections;
  - continued execution under an existing valid frame.
---

# Task Framing

This skill governs the initial scoping, boundary definition, and mode selection of tasks to prevent scope drift while maintaining execution velocity.

## Purpose and Exclusive Responsibility
- **Goal**: Standardize task onboarding and boundary definition.
- **Exclusive Responsibility**: Task framing owns the cross-disciplinary execution boundary, including intended outcomes, constraints, exclusions, authority, acceptance criteria, and completion evidence. Downstream discipline skills retain authority to decompose and interpret work within their assigned boundaries.

## Responsibility Boundaries
- **Primary Responsibility**: Define the task frame boundaries, outcome specifications, and correct framing mode.
- **Adjacent Responsibilities**: Consumes rules from `AGENTS.md` (or equivalent) and passes bounded tasks to specialized execution skills.
- **Explicit Exclusions**: Does not perform actual design, coding, copywriting, or testing of features.
- **Handoff Conditions**: After framing, hand the bounded task to the appropriate discipline or existing skill, or continue execution in the current agent workflow when no separate handoff is required.

## Activation and Non-Activation Conditions
- **Activation**: Triggers whenever a task is ambiguous, complex, cross-disciplinary, destructive, multi-stage, contains unresolved material decisions, or when significant scope shifts invalidate an existing frame.
- **Non-Activation**: Does not trigger for clear, bounded tasks that can be executed directly, minor corrections, or continued work under an existing valid frame.

## Required Inputs
- Raw user request or prompt.
- Task-relevant workspace context (files, assets, configuration, and repository state relevant to the task). Do not read the entire workspace by default.

## Authority Boundaries
- **Authorized Actions**:
  - Inspect only the files, assets, configuration, and repository state relevant to the task.
  - Choose the appropriate framing mode: Internal, Reported, or Approval-Required.
  - Persist task frames when requested, already established by the project, necessary across sessions, or operationally valuable.
- **Unauthorized Actions**:
  - Writing application code, visual designs, or copy before task framing is completed.
  - Reading the entire workspace by default.
  - Silently making product, architectural, visual, editorial, or policy decisions outside of granted authority.

## Ordered Procedure
1. **Determine Framing Need**: Assess whether the task requires framing based on complexity, ambiguity, or execution risk.
2. **Inspect Context**: Inspect only the files, assets, configuration, and repository state relevant to the task.
3. **Define Scope**: Identify the intended outcome and explicit exclusions.
4. **Identify Constraints**: Record supplied constraints and controlling evidence.
5. **Define Success Gates**: Define observable acceptance criteria and completion evidence.
6. **Separate Decisions**: Distinguish authorized implementation decisions from unresolved material decisions.
7. **Select Framing Mode**: Choose from:
   - **Internal Frame**: If the task is clear, establish the frame internally and proceed without interrupting the user.
   - **Reported Frame**: If the task is complex but executable, briefly report the important boundaries in the response and proceed.
   - **Approval-Required Frame**: Stop and request a decision only when an unresolved material choice prevents valid execution.
8. **Select Execution Destination**: Identify the downstream discipline or skill. For a task that produces or modifies a web surface, determine whether product behaviour, workflows, information architecture, forms, transactions, permissions, or interaction-state logic are involved, and to what extent. Route the overall project according to its dominant purpose; invoke `product-design` only for the specific surfaces or behaviours that actually need workflow, state, transaction, permission, form, or interaction definition. When a task mixes an expressive or public surface with one or more bounded interactive elements, split it into parallel concerns — `creative-direction` for the overall concept, `product-design` narrowly for the interactive element's behaviour — rather than forcing the entire surface through a single sequential, product-design-led pipeline. Do not default to `product-design` merely because the deliverable is a website or contains any interactive element.
9. **Handoff & Proceed**: Hand off or proceed according to the selected mode.

## Evidence Requirements
- **Actionability**: Every procedural step must use imperative language and identify a concrete action plus its expected outcome or validation evidence.
- **Demonstrated Execution**: Include concise examples demonstrating the distinction among Internal, Reported, and Approval-Required framing modes.

## Exact Deliverables
A bounded task frame containing the fields required for the task’s complexity. The frame may be internal, reported conversationally, or persisted as a planning artifact. Do not create documents solely to prove that framing occurred. Every task frame must define, as applicable:
- intended outcome;
- explicit exclusions;
- controlling evidence and constraints;
- acceptance criteria;
- completion evidence;
- authorized decisions;
- unresolved material decisions;
- selected framing mode;
- execution destination.

## Validation Gates
Before proceeding:
- [ ] **Frame Completeness**: All applicable fields are present.
- [ ] **Decision Separation**: Bounded implementation decisions and material decisions are not conflated.
- [ ] **Mode Justification**: The selected mode matches the task’s ambiguity, complexity, and execution risk.
- [ ] **Approval Safety**: Internal and Reported frames contain no unresolved material decision that blocks execution.
- [ ] **Acceptance Evidence**: Acceptance criteria and completion evidence are directly observable.
- [ ] **Destination Check**: Identify an appropriate discipline, execution mode, current agent workflow, or existing skill without inventing a skill as though it exists.
- [ ] **No Placeholders**: No TODOs, accidental placeholders, unfinished template text, or unresolved drafting markers remain. Clearly defined metavariables (such as `<skill-name>`) are permitted.
- [ ] **Link Verification**: All file links resolve correctly. Prefer repository-relative links; use absolute links only when explicitly required or justified.

## Stop and Failure Conditions
- **Halt Execution immediately when**:
  - An unresolved material decision prevents a valid execution boundary.
  - Higher-priority instructions cannot resolve a consequential contradiction.
  - Execution would require unauthorized destructive, security-sensitive, legal, financial, or policy action.
- **On Failure**: Preserve partial work unless demonstrably invalid. Report what was completed, what remains, the exact blocker, and whether it is mechanical or requires a policy decision.

## Prohibited Behaviours
- **Vague Acceptance Criteria**: Every criterion must be directly testable or observable.
- **Silent Policy Decisions**: Do not silently make material decisions outside granted authority.
- **Early Execution**: Do not write code or assets before completing framing.

## Material Decisions vs. Bounded Implementation
- **Material Decision**: Any decision that meaningfully changes:
  - product behaviour or user workflow;
  - public-facing meaning, copy, or brand direction;
  - architecture, schemas, persistent data, or external interfaces;
  - security, privacy, licensing, cost, or dependencies;
  - destructive or difficult-to-reverse state;
  - agreed scope or acceptance criteria.
- **Bounded Implementation Decisions**: Minor, reversible implementation choices. Use existing project conventions or clearly bounded defaults.

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

When evidence conflicts, use the source with the most direct authority over the specific claim.

## Concrete Usage Examples: Framing Modes

> [!NOTE]
> All named execution skills and resource paths in these examples are hypothetical unless explicitly identified as an installed skill. The repository currently contains `skill-authoring-standard`, `task-framing`, `software-development`, `testing-and-verification`, `product-design`, `visual-design`, `ux-writing`, `creative-direction`, `copywriting`, and `frontend-development`.

### Example 1: Internal Frame Mode (Theme Toggle)
- **Task**: "Add a theme toggle button to the navbar."
- **Selected Mode**: **Internal Frame** (No unresolved material decisions; navbar conventions and theme structures are clearly defined in current files).
- **Intended Outcome**: A functional theme toggle button in the navbar that switches the site between light and dark modes, persisting the state across reloads.
- **Explicit Exclusions**: Does not implement any new page layouts or modify themes of pages other than applying the theme variables.
- **Controlling Evidence and Constraints**: Matches existing CSS variables in `./src/styles/theme.json` (hypothetical).
- **Acceptance Criteria**:
  - Navbar contains a toggle button.
  - Clicking changes the theme class (`.dark`) on `<html>`.
  - The choice is saved in `localStorage`.
- **Completion Evidence**: HTML class toggling after user interaction and correct initialization after reload.
- **Authorized Decisions**: Icon selection, component naming, and navbar placement under existing conventions.
- **Unresolved Material Decisions**: None. (Placement would only escalate if references conflicted or all viable placements materially altered the design).
- **Execution Destination**: `software-development` baseline + `frontend-development` specialist execution, proceeding within the current agent workflow — installed execution skills still apply even when execution continues in the same workflow rather than requiring a separate handoff.

### Example 2: Reported Frame Mode (Refactor API Error Handling)
- **Task**: "Improve error handling across all API routes to return clean JSON and log errors."
- **Selected Mode**: **Reported Frame** (Complex, multi-file execution. Boundaries and logging conventions must be surfaced to the user before proceeding, but no decision blocks execution).
- **Intended Outcome**: All routes in `./src/pages/api/` (hypothetical) consistently catch exceptions, return standardized JSON responses (e.g., `{ error: "message" }`), and log details to console.error.
- **Explicit Exclusions**: Does not modify frontend UI components or change public API route paths.
- **Controlling Evidence and Constraints**: Existing `APIError` helpers and the project’s established public API response contract define the response schema and status-code semantics.
- **Acceptance Criteria**:
  - API routes catch database exceptions without crashing.
  - JSON payload returned has `{ success: false, error: ... }` with a 400 or 500 status code.
- **Completion Evidence**: Observed HTTP JSON response codes and terminal execution output.
- **Authorized Decisions**: Internal logging metadata, helper structure, and implementation details consistent with existing conventions. Public response schemas, status-code semantics, and user-visible error wording are bounded decisions only when an existing API contract or project convention already governs them. Otherwise, treat consequential changes as unresolved material decisions.
- **Unresolved Material Decisions**: None.
- **Execution Destination**: Current agent workflow or the installed `software-development` skill. (A future `backend-development` specialist may apply once installed; unlike `software-development`, it remains hypothetical.)

### Example 3: Creative-First Routing with Parallel Concerns (Public Campaign Page)
- **Task**: "Build a launch page for our new product announcement. No accounts — the only interactive element is an email-signup form."
- **Selected Mode**: **Reported Frame** (cross-disciplinary, but no unresolved material decision blocks execution).
- **Analysis**: The page's dominant purpose is expressive/public messaging, not a transactional application. One bounded element — the email-signup form — has real workflow/state/validation behaviour (submit, validation error, success, duplicate/failure handling). The presence of that one element does not make the entire page product-design-led.
- **Execution Destination**: Split into parallel concerns rather than one sequential pipeline:
  - `creative-direction` establishes the overall expressive thesis for the page.
  - `product-design`, narrowly, defines only the signup form's behaviour: submit action, validation states, success state, failure/recovery state.
  - `visual-design` and `ux-writing`/`copywriting` each consume the applicable approved output from both branches — `visual-design` applies the creative thesis to the page's overall composition and the approved form states to that one element; `ux-writing` writes the signup form's validation/error copy from product-design's states; `copywriting` writes the surrounding headline and persuasive copy from the creative thesis.
  - Both branches then proceed to `software-development` baseline + `frontend-development` specialist execution,
    and to `testing-and-verification` only when independent verification is required.
- **Unresolved Material Decisions**: None.
- **Note**: Do not route the whole page through `product-design` first merely because it contains a form; do not route the form's behaviour through `creative-direction` merely because the page is expressive.

### Example 4: Approval-Required Frame Mode (Database Migration / Schema Modification)
- **Task**: "We need to allow users to sign up with phone numbers as their primary ID instead of email."
- **Selected Mode**: **Approval-Required Frame** (High execution risk; changes the database schema and authentication workflow).
- **Intended Outcome**: Modify User table schema and auth configuration to accept phone numbers.
- **Explicit Exclusions**: Out of scope to implement SMS gateway provider integrations (uses mock gateway for now).
- **Controlling Evidence and Constraints**: Database schema definitions in `./prisma/schema.prisma` (hypothetical).
- **Acceptance Criteria**:
  - Schema supports `phoneNumber` column.
  - User can register and authenticate with phone number.
- **Completion Evidence**: Schema migration file generated, test suite verification.
- **Authorized Decisions**: Column type, model variable names.
- **Unresolved Material Decisions**: Should phone numbers be unique, or can multiple accounts share a number? Does this replace email logins entirely, or is it an addition? (Decision required from user before proceeding).
- **Execution Destination**: `backend-development` skill (hypothetical).
