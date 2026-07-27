---
name: skill-authoring-standard
description: |
  Governing standard for authoring, reviewing, and validating all agent skills. 
  MANDATORY: Execute whenever creating, modifying, or auditing files in `.agents/skills/`.

  Trigger immediately for:
  - Designing a new skill structure.
  - Modifying or updating an existing skill file.
  - Auditing skills for quality compliance.

  DO NOT trigger for:
  - Performing application code development or testing that does not modify the skill framework itself.
---

# Skill Authoring Standard

This document governs the quality, structure, boundaries, and validation of all agent skills.

## Purpose and Exclusive Responsibility
- **Goal**: Standardize the construction of agent skills to ensure they are actionable, reliable, self-contained, and clear.
- **Exclusive Responsibility**: Governing the authoring and evolution of the skill framework in `.agents/skills/`. No other skill may define structure or validation rules for skill authoring.

## Responsibility Boundaries
- **Primary Responsibility**: Defining the structure, quality rules, layout, and validation guidelines for files within `.agents/skills/`.
- **Adjacent Responsibilities**: Integrates with workspace-level configurations (e.g., `AGENTS.md`) and validation pipelines.
- **Explicit Exclusions**: Does not govern actual application runtime logic, product features, or tests of software applications.
- **Handoff Conditions**: When a skill has been authored and validated, handoff control to the relevant agent execution flow or user review.

## Activation and Non-Activation Conditions
- **Activation**: Triggers whenever the agent is tasked to:
  - Create a new skill (e.g., creating a new directory in `.agents/skills/`).
  - Modify, extend, or audit any existing skill.
- **Non-Activation**: Does not activate during ordinary software engineering tasks (e.g., editing application source code, writing tests for application features, deploying, etc.) unless those tasks explicitly involve changing or referencing the definition of an agent skill.

## Required Inputs
- Target location for the skill (e.g., `.agents/skills/<skill-name>/`, which may not exist yet).
- Proposed or existing `SKILL.md` (which may not exist yet).
- The context/documentation of the specific task or discipline the skill is designed to solve.

## Authority Boundaries
- **Authorized Actions**:
  - Read access to all existing files under `.agents/skills/` to inspect for duplicate ownership, conflicting instructions, or required handoffs.
  - Write and structure files and directories inside `.agents/skills/<skill-name>/`.
  - Create standard helper scripts under `.agents/skills/<skill-name>/scripts/`.
- **Unauthorized Actions**:
  - Write access outside the target skill (e.g., `.agents/skills/<skill-name>/`) unless broader modification is explicitly authorized.
  - Deleting global configurations or existing skills without explicit user consent.
  - Silently making product, architectural, visual, editorial, or policy decisions outside granted authority.

## Ordered Procedure
1. **Scope definition**: Identify the skill’s single primary responsibility, the outcomes it owns, and the responsibilities it explicitly does not own.
2. **Audit & Check**: Check current `.agents/skills/` to confirm that duplicate procedures or competing ownership are avoided.
3. **Structure Initialization**: Create the directory structure:
   - `.agents/skills/<skill-name>/SKILL.md`
   - (Optional) `scripts/`, `examples/`, `resources/`, `references/`
4. **Draft SKILL.md**: Write the YAML frontmatter and the body conforming to this standard.
5. **Add Operational Assets**: Add only the supporting assets required for reliable execution. Include examples, scripts, tests, rubrics, references, or resources when they provide operational value. Do not create empty or decorative directories.
6. **Self-Audit**: Run the validation gates listed in this standard.
7. **Report & Propose**: Present the skill to the user for final verification.

## Evidence Requirements
- **Actionability**: Every procedural step must use imperative language and identify a concrete action plus its expected outcome or validation evidence. Every instruction must map to an observable action, decision, artifact, evaluation criterion, or verification method.
- **Demonstrated Execution**: The skill must contain at least one concrete usage example (stored in `examples/` or documented in `SKILL.md`).
- **Tested Skills**: Execution evidence (e.g., run logs) is required only when the skill has actually been tested.

## Exact Deliverables
A complete skill package must consist of:
1. `SKILL.md` containing:
   - YAML frontmatter with `name` and `description` (with triggers).
   - Core sections: Purpose, Responsibility Boundaries, Activation Conditions, Required Inputs, Authority Boundaries, Ordered Procedure, Evidence Requirements, Deliverables, Validation Gates, Stop/Failure Conditions, Prohibited Behaviours, Conflict Resolution.
2. Supporting assets (optional):
   - Detailed manuals, rubrics, and reference material moved to supporting files (e.g., `references/`) to keep `SKILL.md` focused.

## Validation Gates
Before presenting a skill to the user:
- [ ] **Target File Existence**: The file exists at the correct path.
- [ ] **Frontmatter Check**: File starts with a valid YAML frontmatter containing `name` and `description` with explicit triggers (Trigger immediately / DO NOT trigger) and parses successfully.
- [ ] **Required Sections Check**: All mandatory sections are present: Purpose and Exclusive Responsibility, Responsibility Boundaries, Activation and Non-Activation Conditions, Required Inputs, Authority Boundaries, Ordered Procedure, Evidence Requirements, Exact Deliverables, Validation Gates, Stop and Failure Conditions, Prohibited Behaviours, Conflict-Resolution and Evidence Hierarchy.
- [ ] **Concrete Example**: The concrete usage example is present.
- [ ] **No Placeholders**: No TODOs, accidental placeholders, unfinished template text, or unresolved drafting markers remain. Clearly defined instructional metavariables such as `<skill-name>` are permitted.
- [ ] **Link Verification**: All file links resolve correctly. Prefer repository-relative links; use absolute links only when explicitly required or justified.
- [ ] **Clean Package Check**: `git diff` (or workspace audit) contains only the authorized target skill package, explicitly authorized integration changes to existing skills or repository documentation (e.g., updating cross-skill handoffs when a new skill is installed), and no unrelated edits.

## Stop and Failure Conditions
- **Halt Execution immediately when**:
  - The skill cannot be implemented without modifying global configurations that are out of bounds.
  - A required external tool or dependency is unavailable.
- **On Failure**: Preserve partial work unless it is demonstrably invalid or the user explicitly authorizes deletion. Report:
  - What was completed;
  - What remains;
  - The exact blocker;
  - Whether it is mechanical or requires a policy decision.

## Prohibited Behaviours
- **Vague Advice**: Prohibit phrases like "ensure code is clean", "be careful when editing", "optimize if necessary", or "follow best practices". Every instruction must specify *exactly* how to achieve and verify the outcome.
- **Overlapping Ownership**: Each skill must have one clearly defined primary responsibility. Adjacent skills may intersect only through explicitly documented boundaries and handoffs. Duplicate procedures or competing ownership are prohibited.
- **Unsupported Completion Claims**: Do not declare a step or skill complete without evidence appropriate to the claimed outcome. Evidence may include test results, runtime output, diffs, validated artifacts, reference comparisons, acceptance-criteria checks, evaluation rubrics, link checks, or other directly inspectable results.
- **Silent Policy Decisions**: A skill must not silently make product, architectural, visual, editorial, or policy decisions outside its granted authority. Do not interrupt the user for every minor choice: use established project rules and reversible defaults where authorized, and surface only material decisions.
- **Generic Phrases**: Every instruction must map to an observable action, decision, artifact, evaluation criterion, or verification method.

## Conflict-Resolution and Evidence Hierarchy
This hierarchy resolves conflicts among workspace instructions and skill documents. It does not override platform-level, system-level, safety, security, or tool-use requirements governing the agent.
- **Conflict Resolution**:
  1. User's explicit instructions in the current prompt.
  2. Workspace rules (`AGENTS.md` or equivalent).
  3. Governing standard (`.agents/skills/skill-authoring-standard/SKILL.md`).
  4. Individual skill `SKILL.md`.
  5. Global agent guidelines.
- **Evidence Hierarchy (Source of Truth)**:
  The applicable evidence depends on the discipline. Console output is not automatically superior to visual references, approved copy, or explicit user decisions.
  1. Explicit user instructions and decisions from the current task.
  2. Supplied acceptance criteria, screenshots, prototypes, examples, and reference assets.
  3. Observable behaviour and direct execution evidence.
  4. Current workspace files, schemas, architecture, and established conventions.
  5. Tests, compiler output, lint results, and runtime logs where applicable.
  6. Project documentation.
  7. External authoritative references.
  8. Skill defaults and model assumptions.

When evidence conflicts, use the source with the most direct authority over the specific claim. For example, an approved screenshot governs visual fidelity, current official API documentation governs external API behaviour, runtime evidence governs observed application behaviour, and explicit user decisions govern intended outcomes.

## Concrete Usage Example: Skill Review

Below is a concise example of using this standard to review a proposed skill (`ui-layout-guidance`):

> [!NOTE]
> All named execution skills and resource paths in this example are hypothetical. The repository currently contains `skill-authoring-standard`, `task-framing`, `software-development`, `testing-and-verification`, `product-design`, `visual-design`, `ux-writing`, `creative-direction`, `copywriting`, and `frontend-development`.

1. **Primary Responsibility**: Define responsive layout mechanics using Grid, Flexbox, container queries, breakpoints, and structural spacing.
2. **Adjacent Responsibility**: Consume approved design tokens and visual specifications (e.g., from `.agents/resources/tokens.json`).
3. **Explicit Exclusion**: Does not choose colours, typography, visual identity, component behaviour, state management, or API logic.
4. **Handoff Conditions**: Hand visual decisions to the `visual-design` skill and interactive behaviour to the `frontend-development` skill.
5. **Applicable Evidence**:
   - Approved screenshots or layout specifications.
   - Browser inspection at required viewport sizes.
   - Validation of overflow and responsive behaviour.
   - Inspection of the resulting HTML/CSS.
