---
name: testing-and-verification
description: |
  Independently determines whether claimed behaviour, acceptance criteria, integrations, and completion statements are supported by appropriate evidence.
  Execute when independently validating implementation results or completion claims, conducting regression checks, or running test suites.

  Trigger immediately for:
  - independently verifying a completed implementation;
  - independently verifying a reported defect or regression;
  - independently verifying an existing behavioural claim;
  - independently verifying acceptance criteria, integration behaviour, visual interaction, or completion evidence.

  DO NOT trigger for:
  - Implementing production code fixes.
  - Modifying application configurations, schemas, or production code.
  - Initial task framing or altering acceptance criteria.
---

# Testing and Verification

This skill governs the independent planning, execution, and reporting of tests and verification procedures to ensure code changes meet acceptance criteria and do not introduce regressions.

## Purpose and Exclusive Responsibility
- **Goal**: Ensure rigorous, independent, evidence-backed verification of implementation claims, reported defects, existing behaviour, acceptance criteria, and integrations.
- **Exclusive Responsibility**: Independently determining whether claimed behaviour, acceptance criteria, integrations, and completion statements are supported by appropriate evidence.

## Responsibility Boundaries
- **Primary Responsibility**: Independent verification planning, selecting proportionate checks, reviewing implementation diffs, executing automated and manual checks, writing tests/reproductions, identifying unsupported completion claims, and classifying/reporting defects.
- **Adjacent Responsibilities**: Consumes task frames from `task-framing` and completion reports/diffs from `software-development`, including `frontend-development`'s specialist execution and self-validation evidence for frontend surfaces.
- **Explicit Exclusions**: Does not perform initial cross-disciplinary task framing, product/workflow design, copywriting, independent quality policy definition, deployment authorization, or material architectural, dependency, schema, or security decisions that were not pre-authorized.
  - Approved design references, copy, schemas, contracts, and product specifications may serve as controlling evidence. This skill verifies against them but does not redefine or implement them.
  - Excludes editorial and public-copy decisions, security-policy decisions, licensing and cost decisions, dependency selection, and changes to expected results that are not already authorized.
  - It does not accept existing test passes as proof of untested behaviour.
- **Handoff Conditions**: If production repair is required, report the defect and hand back to the responsible discipline (`software-development`, or the applicable specialist such as `frontend-development` within its delegated domain). If verification is complete, hand the final verification verdict to the user or subsequent workflow.

## Activation and Non-Activation Conditions
- **Activation**: Triggers when independently verifying a completed implementation, a reported defect or regression, an existing behavioural claim, or acceptance criteria, integration behaviour, visual interaction, or completion evidence.
  - Verification may occur in the same agent workflow as implementation, but the verification pass must independently inspect the claim, affected path, applicable contract, and evidence. Do not derive the verdict merely from the implementation agent’s expectations or completion report.
- **Non-Activation**: Does not trigger for writing production code or altering task frames.

## Required Inputs
- Original request, claim, defect report, or valid task frame.
- Applicable acceptance criteria or expected contract.
- Implementation report and diff, when verifying a new implementation.
- Relevant repository baseline.
- Applicable tests, runtime surfaces, schemas, contracts, screenshots, or reference assets.
- The skill must also support:
  - reproducing a reported defect before implementation;
  - auditing existing behaviour;
  - verifying a completion claim that lacks a formal implementation report.

## Authority Boundaries
- **Authorized Actions**:
  - Create or modify bounded test files, fixtures, mocks, test-only configuration, and isolated reproductions when authorized and necessary for verification.
  - Inspect relevant repository state, baseline test results, and runtime environments.
  - Correct mechanical defects in newly created verification artifacts within the verification pass.
  - Removing a newly created, invalid verification artifact is allowed only when it was created during the current pass and no valid evidence depends on it.
- **Unauthorized Actions**:
  - Modifying production source code, production configuration, production schemas, runtime feature flags, application defaults, or dependencies.
  - Adding or changing a test dependency remains material unless already authorized.
  - Deleting, disabling, skipping, quarantining, or materially weakening an existing test without explicit authorization.
  - Shared test-runner configuration, global fixtures, seeds, or test infrastructure may be changed only when the frame authorizes their broader effects.

## Ordered Procedure
1. **Confirm Frame and Authority**: Confirm the task frame, acceptance criteria, and verification authority.
2. **Record Repository and Test Baseline**: Record relevant repository and test baseline (pre-existing modified, staged, untracked, failing, skipped, or flaky state). Preserve unrelated user work and distinguish new failures from baseline failures. Do not stage, revert, clean, or overwrite unrelated files.
3. **Inspect Inputs**: Inspect the implementation report and diff when verifying a new implementation. For defect reproduction or existing-behaviour audits, inspect the originating claim, current implementation, applicable contract, and available evidence.
4. **Trace Claims**: Trace each claim to affected runtime paths and contracts.
5. **Assess Risk and Scope Verification**: Assess risk and select proportionate verification. State why each check is relevant. Do not run the entire suite automatically when narrow checks suffice, but do not omit regressions if the change has wide impact.
6. **Verify Normal Behaviour**: Execute checks for the happy path.
7. **Verify Failure Paths**: Execute checks for boundaries, errors, and invalid inputs.
8. **Check Integrations**: Verify affected integration points and regression zones.
9. **Reconcile Evidence**: Reconcile observed evidence with every acceptance criterion.
10. **Classify Failures**: Classify observed failures and document uncertainty.
11. **Produce Verdict**: Produce an independent verification verdict and hand off.

## Evidence Requirements
- **Actionability**: Every procedural step must use imperative language and identify a concrete action plus its expected outcome or validation evidence.
- **Verification Honesty**: Passing tests prove only what they exercise and assert. A test that does not reach the modified path is not evidence for that path. Compilation is not behavioural proof. Manual inspection is not automatically sufficient for runtime behaviour. Screenshots prove only the rendered state shown. Absence of observed failure does not establish correctness. Do not claim a check was run without the exact command and observed result.

## Evidence Classes
No evidence class automatically substitutes for another. Define and distinguish:
- **Static Inspection**: Manual review of the code structure and logic.
- **Compilation/Type Checking**: Ensuring code builds and satisfies type constraints.
- **Linting**: Conformance to style rules and static safety checks.
- **Unit Tests**: Isolated testing of individual functions or classes.
- **Integration Tests**: Verifying interaction between multiple components or modules.
- **End-to-End Tests**: Testing the full application workflow from user input to database/network outputs.
- **Direct Runtime Observation**: Verifying console logs, network payloads, or database state during execution.
- **Manual Interaction**: Interacting directly with the running application.
- **Visual/Reference Comparison**: Comparing visual output (rendering, layout) against reference specifications or screenshots.
- **Accessibility Checks**: Verifying compliance with access guidelines (e.g., ARIA roles).
- **Security or Data-Boundary Checks**: Testing validation boundaries, access limits, and protection.
- **Contract/Schema Validation**: Checking API payloads and schema integrity.

## Exact Deliverables
An independent verification completion report containing:
- baseline state;
- implementation claims reviewed;
- files and runtime paths inspected;
- checks selected and why;
- commands or procedures executed;
- exact observed results;
- acceptance-criterion verdicts;
- failures and classifications;
- checks not run and why;
- limitations and residual uncertainty;
- overall verification verdict;
- required handoff.

## Validation Gates
Before claiming completion of verification or handing off:
- [ ] **Independence Integrity**: Diffs, paths, and contracts were reviewed independently without blindly relying on the developer report.
- [ ] **Baseline Preservation**: Unrelated user changes remain unaltered and retain their recorded staged, unstaged, and untracked state.
- [ ] **No Production Code Modifications**: No production files or production configurations were changed.
- [ ] **Assertion Integrity**: Assertions were not weakened, tests skipped, or tolerances broadened.
- [ ] **Introduced Artifact Integrity**: No unresolved TODO, stub, temporary bypass, disabled assertion, debug instrumentation, or placeholder was introduced into verification artifacts unless explicitly authorized. Pre-existing items must be reported when they affect evidence.
- [ ] **Claim Traceability**: Every implementation or behavioural claim reviewed is tied to an affected path, contract, criterion, or observable outcome.
- [ ] **Check Relevance**: Each selected check states which claim or risk it verifies.
- [ ] **Criterion Reconciliation**: Every acceptance criterion is classified as verified, failed, blocked, inconclusive, or not tested.
- [ ] **Failure Classification Integrity**: Failures are not attributed to production code without evidence distinguishing implementation defects from test, environment, service, baseline, or specification failures.
- [ ] **Evidence Honesty**: Every executed check includes the exact command or procedure and the relevant exact observed result.
- [ ] **Unperformed Checks**: Material checks not run are listed with the reason and resulting uncertainty.
- [ ] **Overall Verdict Consistency**: The overall verdict follows from the individual criterion verdicts and does not conceal failed, blocked, or untested critical criteria.
- [ ] **Link Verification**: Apply link verification only when the task creates or modifies links.

## Stop and Failure Conditions
- **Halt Verification immediately when**:
  - Required verification would be destructive or unauthorized.
  - An unresolved material decision prevents determining expected behaviour.
  - The environment cannot produce meaningful evidence.
  - Continuing would modify production behaviour rather than verify it.
- **On Failure**:
  - Correct mechanical defects only in verification artifacts created during the current pass.
  - Do not repair production code or production configuration.
  - Classify production defects and hand them to the responsible discipline (`software-development`, or the applicable specialist such as `frontend-development` within its delegated domain).
  - If a pre-existing test defect prevents meaningful verification, report it and modify it only when explicit authority permits.
  - Do not automatically stop because a check fails; classify the result and determine whether other meaningful verification remains possible.
  - Preserve valid test artifacts and evidence.
  - Do not conceal blocked or inconclusive evidence behind a pass/fail verdict.

## Prohibited Behaviours
- **Production Repair**: Attempting to fix production code or production configuration directly. Instead, report the defect and hand back.
- **Ad-Hoc Weakening**: Modifying test expectations, loosening thresholds, or bypassing failing assertions without explicit authorization.
- **Vague Evidence Claims**: Asserting a test passed without showing the execution command and exact log output.
- **Destructive Worktree Cleaning**: Running commands that risk erasing user changes.

## Result Classifications

### For Individual Checks:
- **Passed**: The check ran successfully and met expected metrics or assertions.
- **Failed**: The check ran but failed to meet assertions.
- **Blocked**: The check could not produce meaningful evidence because required authority, infrastructure, tooling, environment, service, dependency, or expected behaviour was unavailable.
- **Inconclusive**: The check ran but yielded ambiguous results.
- **Not Run**: The check was planned but not executed.

### For Acceptance Criteria:
- **Verified**: Directly observed evidence proves the criterion is fully satisfied.
- **Failed**: Evidence proves the criterion is violated.
- **Blocked**: Missing resources, tools, or dependencies prevent verification.
- **Inconclusive**: Evidence is mixed, ambiguous, or insufficient.
- **Not Tested**: No executed check addressed this acceptance criterion.

### For the Overall Task:
- **Verified**: All applicable acceptance criteria are verified and no material contrary evidence remains.
- **Verified with Limitations**: No acceptance criterion failed; core criteria are verified, but explicitly identified non-critical checks are blocked, inconclusive, or not tested.
- **Not Verified**: At least one acceptance criterion failed, critical evidence is inconclusive, or available evidence does not support the completion claim.
- **Blocked**: Verification could not obtain meaningful evidence because required infrastructure, authority, environment, service, or expected behaviour was unavailable.

## Failure Classification
Every check failure must be classified as one of:
- **Implementation Defect**: A bug in the production code change.
- **Test Defect**: A bug in the test code, assertions, or mocks.
- **Pre-existing Repository Failure**: A test or pipeline failure present in the baseline before changes.
- **Environmental or Tooling Failure**: Network, compiler, VM, or local execution environment failure.
- **Unavailable Service or Dependency**: Third-party API, database, or library is down/missing.
- **Flaky or Nondeterministic Result**: Flaky test behavior.
- **Specification Ambiguity**: Acceptance criteria are conflicting or vague.
- **Unresolved Material Decision**: Blocker requiring a policy decision.
- **Insufficient Evidence**: Verification path could not be sufficiently exercised.

For each observed failure, the verifier must distinguish:
- the **check result**;
- the **acceptance-criterion verdict**;
- the **failure classification**;
- the **overall verification verdict**.

## Defect Reporting Format
Report the observable consequence. Use severity labels only when the project supplies a severity rubric; otherwise do not invent arbitrary classifications. Every reported defect must document:
1. **Violated Acceptance Criterion**: The specific criterion or contract violated.
2. **Reproduction Steps**: Step-by-step instructions to trigger the failure.
3. **Expected Result**: What should have occurred.
4. **Observed Result**: What actually occurred.
5. **Affected Surface**: Files, functions, or UI paths affected.
6. **Evidence**: Command outputs, error logs, or screenshot references.
7. **Consequence**: Impact on user experience, security, or stability.
8. **Origin**: New, pre-existing, or uncertain.
9. **Recommended Handoff**: Target discipline (e.g., `software-development`, `frontend-development`, or `backend-development`).

## Conflict-Resolution and Evidence Hierarchy
This hierarchy resolves conflicts among workspace instructions and skill documents. It does not override
platform-level, system-level, safety, security, or tool-use requirements governing the agent.
- **Conflict Resolution**:
  1. User's explicit instructions in the current prompt.
  2. Workspace rules (`AGENTS.md` or equivalent).
  3. Governing standard (`.agents/skills/skill-authoring-standard/SKILL.md`).
  4. Individual skill `SKILL.md`.
  5. Global agent guidelines.
- **Evidence Hierarchy (Source of Truth)**:
  The applicable evidence depends on the discipline; see also [Evidence Classes](#evidence-classes) for the
  distinct concept of which verification technique produced a given result.
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

### Example 1: Bounded Bug Fix Verification (Targeted Regression Test)
- **Claim**: Fixed division-by-zero bug in `./src/math.js` (hypothetical).
- **Procedure**:
  - Verifier inspects the relevant diff to trace modifications.
  - Confirms the targeted test reaches the modified zero-rate branch.
  - Runs the exact targeted test command: `node ./tests/math.test.js` (hypothetical).
  - Observed Result: `Test 'rate === 0 returns 0' passed.`
  - Verdict: Verified. (Does not infer wider correctness beyond that criterion).

### Example 2: Integration Failure (Passing Units, Crashing Route)
- **Claim**: Completed UserController serialisation updates.
- **Procedure**:
  - Baseline: UserController unit tests pass.
  - Action: Execute integration curl request.
  - Command: `curl -i http://localhost:3000/api/users/1` (hypothetical).
  - Observed Result: `HTTP/1.1 500 Internal Server Error` (Database connection timeout).
  - Verdict Analysis:
    - Verifier checks whether the database was available in the recorded baseline (it was).
    - Determines if the timeout is caused by the implementation, environment, or unavailable service. 
    - **Scenario A (Serialization path caused the timeout)**:
      - Individual check: **Failed**
      - Acceptance criterion: **Failed**
      - Failure classification: **Implementation Defect**
      - Overall verdict: **Not Verified**
      - (And hands back to `software-development`).
    - **Scenario B (Database VM went down independently)**:
      - Individual check: **Blocked**
      - Acceptance criterion: **Blocked**
      - Failure classification: **Unavailable Service or Dependency**
      - Overall verdict: **Blocked** (if meaningful integration evidence cannot otherwise be obtained).
    - Demonstrates that passing unit tests do not prove runtime integration.

### Example 3: Verification Blocked by Infrastructure
- **Task**: Verify payment webhook integration in `./src/handlers/webhook.js` (hypothetical).
- **Procedure**:
  - Baseline: Clean worktree.
  - Action: Execute webhook receiver integration tests.
  - Command: `node ./tests/webhook.test.js` (hypothetical).
  - Observed Result: Webhook test times out trying to connect to Stripe Sandbox (local sandbox gateway blocks network access).
  - Verdict Classifications:
    - Individual integration check: **Blocked**
    - Acceptance criterion: **Blocked**
    - Failure classification: **Environmental or Tooling Failure** (sandbox gateway block).
    - Overall verdict: **Blocked**
    - Do not call the same result "Inconclusive" since the check failed to connect entirely due to environmental limits.

### Example 4: Visual Claim and Tool Constraints
- **Task**: Verify navbar responsive hamburger menu interaction.
- **Claim**: Hamburger menu displays correctly and opens when clicked.
- **Procedure**:
  - Developer Report: Shows a screenshot of the closed hamburger menu.
  - Testing Action: Screenshots only show static state. Must execute interactive browser testing.
  - Setup check: Verifier confirms an already-authorized, existing Playwright setup is present. (If Playwright is not installed, adding it is a material dependency decision; verification must use another authorized method or become blocked).
  - Command: `npx playwright test` (hypothetical) clicking the menu.
  - Attributed Check: Confirms the JavaScript bundle loaded successfully in baseline, the failure is reproducible, and the loading error originates from the changed implementation rather than the environment/harness.
  - Observed Result: The hamburger icon renders, but clicking it fails to add the `.open` class to the navbar due to a javascript loading error.
  - Verdict Classifications:
    - Individual check: **Failed**
    - Acceptance criterion: **Failed**
    - Failure classification: **Implementation Defect**
    - Overall verdict: **Not Verified**
