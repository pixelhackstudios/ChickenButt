---
name: software-development
description: |
  Executes approved, bounded software changes (bug fixes, feature additions, refactoring) from a valid task frame.
  Execute when implementing application code modifications, database schema edits, configuration changes, or dependency updates.

  Trigger immediately for:
  - Implementing coded solutions, bug fixes, or refactoring tasks.
  - Modifying source files, schemas, dependencies, or configuration within granted authority.

  DO NOT trigger for:
  - Initial task framing or cross-disciplinary scope definition.
  - Product design or user workflow definition.
  - Defining copywriting tone or visual layouts.
---

# Software Development

This skill governs the inspection, modification, and validation of application source code, configuration, schemas, and dependencies within an established task frame.

## Purpose and Exclusive Responsibility
- **Goal**: Standardize the implementation and self-validation of bounded software changes, ensuring minimal complete modifications, explicit change classification, and rigorous validation.
- **Exclusive Responsibility**: This skill owns the general implementation workflow for bounded software changes. Specialist development skills may edit application code within their explicitly delegated domains, while conforming to this skill’s implementation, scope-protection, and evidence requirements.

## Responsibility Boundaries
- **Primary Responsibility**: Inspect task-relevant implementation surfaces, identify the smallest complete change, modify code/configuration within granted authority, validate changes through direct evidence, and report completion status and residual risks.
- **Adjacent Responsibilities**: Consumes task frames from `task-framing` and generates changes that integrate with existing configurations. For frontend implementation surfaces, activates jointly with the installed `frontend-development` specialist skill: this skill supplies the governing implementation baseline (scope discipline, change classification, evidence honesty, completion reporting), and `frontend-development` supplies frontend-specific execution and decisions within it. This baseline is not excluded from frontend work merely because the specialist is also active.
- **Explicit Exclusions**: Does not perform initial cross-disciplinary task framing, product/workflow design, copywriting, independent quality policy definition, deployment authorization, or material architectural, dependency, schema, or security decisions that were not pre-authorized.
  - Design and copy skills provide controlling specifications or artifacts, while development skills implement them within granted authority.
- **Handoff Conditions**: After implementation and validation, return the completed change and evidence to the current workflow, user review, or `testing-and-verification` when independent verification is required.

## Activation and Non-Activation Conditions
- **Activation**: Triggers when executing any code change, configuration update, schema edit, or dependency modification.
  - Internal and Reported frames may proceed when they contain no blocking unresolved material decisions.
  - An Approval-Required frame becomes executable only after the required decision has been supplied and recorded.
  - If implementation discoveries invalidate the frame, hand the task back to `task-framing` rather than silently expanding scope.
- **Non-Activation**: Does not trigger for task framing, visual layouts, copywriting, or when blocked by an unresolved material decision.

## Required Inputs
- A clear, bounded request that can proceed as an Internal Frame, or a valid executable frame supplied by `task-framing` for work that required explicit framing.
- Task-relevant implementation surfaces (code files, configuration, tests, schemas).

## Authority Boundaries
- **Authorized Actions**:
  - Inspect only the files, assets, configuration, and repository state relevant to the task.
  - Read files relevant to the task (expanding read scope only when dependencies or execution evidence justify it).
  - Modify source code, configurations, schemas, or dependencies strictly within the limits defined by the task frame.
  - Add or update tests directly required to validate the implementation.
- **Unauthorized Actions**:
  - Modifying files unrelated to the task frame.
  - Performing unrelated cleanups, cosmetic edits, or opportunistic refactorings.
  - Silently making material architectural, dependency, schema, security, licensing, or cost decisions.
  - Independent test strategy, adversarial verification, broad regression design, or quality-policy decisions. These belong to `testing-and-verification`.
  - Specialist implementation domains belong to specialist skills operating within their delegated domain while conforming to this skill's governing baseline. `frontend-development` is installed and activates jointly with this skill for frontend implementation surfaces, per its own SKILL.md. `backend-development`, `database-development`, and `infrastructure-development` remain hypothetical until installed.

## Ordered Procedure
1. **Confirm Frame and Authority**: Confirm a valid and executable task frame.
2. **Record Repository Baseline State**: Record relevant repository and worktree baseline state (pre-existing modified, staged, and untracked files). Distinguish agent-created changes from pre-existing user work. Do not overwrite, revert, stage, or clean unrelated user changes.
3. **Inspect Relevant Surface**: Inspect task-relevant implementation surfaces and conventions.
4. **Trace Paths**: Trace affected runtime paths, imports, data flow, and dependencies.
5. **Classify Proposed Changes**: Classify proposed changes as mechanical, bounded, or material.
6. **Define Smallest Change**: Define the smallest complete change required to satisfy the acceptance criteria.
7. **Implement Incrementally**: Implement incrementally while preserving unrelated work.
8. **Add or Update Tests**: Add or update implementation-proximate tests when required.
9. **Validate Behavior**: Validate the affected behaviour with evidence appropriate to the changed path.
10. **Inspect Diff**: Inspect the resulting diff against the recorded baseline.
11. **Report Completion**: Report acceptance-criteria status, evidence, unperformed validation, and residual risk.

## Evidence Requirements
- **Actionability**: Every procedural step must use imperative language and identify a concrete action plus its expected outcome or validation evidence.
- **Demonstrated Execution**: Include concise examples demonstrating:
  - a bounded mechanical correction;
  - a multi-file implementation using established architecture;
  - an implementation discovery that invalidates the existing frame and requires a material decision.

## Exact Deliverables
A validated code modification matching the task frame and a structured completion report defining:
- baseline repository state;
- files intentionally changed;
- behaviour implemented;
- change classifications;
- commands and checks actually executed;
- exact results;
- tests or checks not run and why;
- pre-existing failures encountered;
- acceptance criteria satisfied, unsatisfied, blocked, or not verified;
- residual risks;
- whether further task framing or specialist verification is required.

## Validation Gates
Before claiming completion or handing off the implementation:
- [ ] **Baseline Integrity**: Pre-existing user changes were identified and preserved.
- [ ] **Scope Integrity**: Only task-relevant files were intentionally changed.
- [ ] **Change Classification**: Material decisions were not implemented without authority.
- [ ] **Runtime Integration**: The modified path was exercised where reasonably possible; compilation, lint, or diff inspection alone is not behavioural proof.
- [ ] **Test Honesty**: Distinguish passed tests, failed tests, tests not run, unavailable tests, and manual checks. No tests are claimed as passed unless executed.
- [ ] **Introduced Placeholder Check**: No unresolved TODO, stub, debug code, temporary bypass, or placeholder was introduced by the implementation unless explicitly authorized.
- [ ] **Diff Inspection**: The resulting change set contains no accidental, unrelated, generated, debugging, or temporary files.
- [ ] **Acceptance Criteria Status**: Every task-frame acceptance criterion is explicitly marked satisfied, unsatisfied, blocked, or not verified. Do not infer full completion from partial validation.
- [ ] **Link Verification**: Apply link verification only when the task creates or modifies links.

## Stop and Failure Conditions
- **Halt Execution immediately when**:
  - The failure prevents valid completion within granted authority.
- **On Failure**:
  - Attempt to correct implementation defects that remain within the frame. Do not automatically halt because a compiler or test command fails.
  - Classify failures as:
    - implementation defect;
    - pre-existing repository failure;
    - environmental/tooling failure;
    - unavailable dependency or service;
    - unresolved material decision;
    - out-of-scope blocker.
  - Preserve partial work unless demonstrably invalid. Report the exact failing command, affected surface, current repository state, and distinguish implementation defects from environmental or policy blockers. Never claim full completion when integration remains incomplete.

## Prohibited Behaviours
- **Vague Self-Validation**: Claiming code works without presenting direct, inspectable validation evidence.
- **Opportunistic Refactoring**: Rewriting adjacent systems merely because they appear imperfect.
- **Destructive Worktree Actions**: Never use destructive worktree commands such as `git reset --hard`, `git clean -fd`, or broad checkout/restore operations that could erase unrelated user work.
- **Silent Schema/Dependency Decisions**: Adding dependencies, altering schemas, or changing APIs without authorization.

## Change Classification
Every change must be classified as one of:
- **Mechanical Change**: A predictable edit whose consequences are fully determined by existing requirements, such as correcting an internal typo, changing a private constant, or adding a guard clause with already-defined behaviour.
- **Bounded Implementation Decision**: Selecting internal logic, helper structure, or logging details consistent with established architecture and privacy/security conventions.
- **Material Decision**: Schema, dependency, public API, authentication, authorization, security, licensing, cost, persistent-data, or externally consequential changes unless already authorized.

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

## Concrete Usage Examples

> [!NOTE]
> Named execution skills, commands, files, and repository paths in these examples are hypothetical unless explicitly identified as existing.

### Example 1: Bounded Mechanical Correction
- **Task**: Fix division-by-zero error in `./src/math.js` (hypothetical) when utility rate is zero.
- **Frame**: Bounded to `./src/math.js` (hypothetical) (Internal Frame).
- **Classification**: Mechanical Change (adding rate check guard clause).
- **Action**: Add rate guard check in `./src/math.js` (hypothetical).
- **Validation**: Executed `node ./tests/math.test.js` (hypothetical). Observed result: `14 tests passed, 0 failed.`
- **Report**:
  - Baseline: Clean worktree.
  - Changed: `./src/math.js` (hypothetical).
  - Verification: Run `node ./tests/math.test.js` (hypothetical) returning exactly `14 tests passed, 0 failed`.

### Example 2: Multi-File Implementation Using Established Architecture
- **Task**: Add a helper method to serialize users in `./src/models/User.js` (hypothetical) and consume it in `./src/controllers/UserController.js` (hypothetical).
- **Frame**: Bounded to model and controller files. (Reported Frame).
- **Classification**: Bounded Implementation Decision.
- **Action**: Add `toJSON()` to User model, ensuring sensitive fields (like `passwordHash`) are not exposed according to the existing serialization contract. Treat any public response-schema changes as material unless already authorized.
- **Validation**: Curled `/api/users/1` locally (hypothetical), verifying that fields match serialization contracts and `passwordHash` is absent.
- **Report**: Modified model and controller. Confirmed sensitive fields are protected.

### Example 3: Frame Invalidation and Material Dependency Block
- **Task**: Parse a complex CSV file upload in `./src/handlers/upload.js` (hypothetical).
- **Frame**: Bounded to upload handler, using existing custom parser. (Reported Frame).
- **Classification**: Escalated to Material Decision (Blocked).
- **Discovery Flow**:
  - Implementation inspection reveals that the existing custom parser cannot satisfy nested-quote requirements.
  - Adding `csv-parse` library is outside current authority.
  - The discovery invalidates the existing frame, and execution stops.
  - The task returns to `task-framing` and becomes Approval-Required.
  - The agent preserves any analysis or isolated tests that remain valid.
  - Incomplete production-path edits are removed without disturbing pre-existing user changes.
- **Report**:
  - Completed: Verified custom parser limits.
  - Blocker: Requires `csv-parse` package authorization. Code restored to baseline.
