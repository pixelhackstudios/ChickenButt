---
name: frontend-development
description: |
  Implements approved frontend requirements — supplied through applicable specifications or a bounded task
  frame — into working, rendered frontend code that implements approved accessibility mechanics and performance
  constraints, operating jointly with `software-development`'s governing implementation baseline as the
  specialist execution authority for the frontend surface.
  Execute alongside `software-development` whenever implementing a production change to rendered markup, styles,
  frontend components, responsive behaviour, client-side interaction, browser-side accessibility mechanics,
  frontend performance, server-rendered frontend concerns, or approved motion — regardless of visual ambition.
  Does not activate for audits, design-only reviews, or independent verification of frontend behaviour where no
  production implementation is requested.

  Trigger immediately for:
  - Any production change to rendered markup, styles, or frontend components, including ordinary, non-distinctive
    interfaces.
  - Responsive behaviour, client-side interaction/state wiring, or browser-side accessibility mechanics.
  - SSR, hydration, route-level rendering, frontend data-loading integration, or frontend build/bundling
    configuration that directly implements the web surface.
  - Implementation of approved visual specifications or approved motion/interaction behaviour.

  DO NOT trigger for:
  - Product behaviour, workflows, states, or business rules (owned by `product-design`).
  - Establishing the creative thesis, brand voice, or verbal character (owned by `creative-direction`).
  - Authoring exact visual specifications (owned by `visual-design`) or exact interface/promotional copy (owned
    by `ux-writing`/`copywriting`).
  - Database schemas, persistence policy, authorization/security policy, backend domain rules, or
    infrastructure/deployment architecture with no frontend-rendering component.
  - Independent verification of implemented behaviour (owned by `testing-and-verification`).
---

# Frontend Development

This skill governs the implementation of approved frontend requirements — supplied through applicable
specifications or a bounded task frame — into markup, styles, components,
responsive behaviour, client-side interaction, server-rendered frontend concerns, accessibility mechanics,
performance, and approved motion — as the specialist execution authority operating jointly with
`software-development`'s governing implementation baseline.

## Purpose and Exclusive Responsibility
- **Goal**: Implement approved frontend requirements — supplied through applicable specifications or a bounded
  task frame — into working, rendered frontend code that implements approved accessibility mechanics and
  performance constraints, while conforming to `software-development`'s
  governing implementation discipline, without redefining product behaviour, visual specification, creative
  thesis, or copy, and without claiming compliance or comprehensiveness this skill's self-validation cannot
  establish.
- **Exclusive Responsibility**: Own frontend-specific implementation mechanics — rendered markup, styles,
  frontend components, responsive behaviour, client-side interaction and state wiring, server-rendered frontend
  concerns (SSR, hydration, route rendering, frontend data-loading integration) where they directly implement the
  web surface, browser-side accessibility mechanics, frontend performance, and implementation of approved
  motion — as the specialist execution authority operating jointly with `software-development`'s governing
  baseline, not as a parallel or competing authority.

## Responsibility Boundaries
- **Primary Responsibility**: Rendered markup and styles; semantic HTML and document structure (landmarks,
  heading hierarchy, native controls before custom substitutes); frontend component implementation; responsive
  behaviour; supported-browser behaviour where a browser-support requirement or platform constraint exists;
  client-side interaction and state wiring; SSR/hydration/route-level rendering and frontend data-loading
  integration; frontend build/bundling configuration; browser-side accessibility mechanics; frontend performance;
  implementation of approved visual specifications; implementation of approved motion and interaction behaviour;
  rendered-fidelity and behavioural self-validation.
- **Adjacent Responsibilities**: Activates jointly with `software-development` for any frontend implementation
  surface — `software-development` supplies the governing implementation baseline (scope discipline, change
  classification, evidence honesty, completion reporting); this skill supplies the specialist frontend execution
  procedure and owns frontend-specific decisions within it. Consumes approved `product-design` behaviour/states
  when applicable, the approved `creative-direction` thesis when one exists, `visual-design`'s exact
  specifications when one exists, and `ux-writing`/`copywriting`'s exact strings when applicable — otherwise
  grounds directly in the task frame and approved current behaviour. Hands implementation and self-validation
  evidence to `testing-and-verification` when independent verification is required.
- **Explicit Exclusions**: Does not define product behaviour, workflows, or business rules. Does not establish or
  originate the creative thesis, brand voice, or verbal character. Does not author exact visual specifications or
  exact interface/promotional copy. Does not own database schemas, persistence policy, authorization/security
  policy, backend domain rules, externally consequential API contracts, or infrastructure/deployment
  architecture — regardless of whether that code lives in the same repository or framework directory as the
  frontend. Does not perform independent verification. Does not claim accessibility compliance, comprehensive
  assistive-technology support, or comprehensive performance acceptability from its own self-validation — see
  [Implementation-Proximate Accessibility and Performance Boundary](#implementation-proximate-accessibility-and-performance-boundary).
  - Approved product, creative, visual, and copy specifications are controlling evidence this skill implements
    through — it does not redefine them.
- **Handoff Conditions**: When independent verification is required by the task frame, governing process, risk,
  or acceptance criteria, hand the completed change and its self-validation evidence to
  `testing-and-verification`. Otherwise, return the implementation and its clearly labeled self-validation
  evidence to the current workflow or user. Self-validation is never represented as an independent verdict either
  way, and a self-validated pass never exempts work from independent verification when independent verification
  is required. Return unresolved behavioural conflicts to `product-design`, unresolved creative-conformance
  disputes to `creative-direction`,
  unresolved visual-specification gaps to `visual-design`, and unresolved material decisions (new dependency,
  new design-token system, backend-boundary crossing, material motion/choreography treatment) to `task-framing`,
  which determines the authority that resolves each one rather than this skill routing it there itself.

## Activation and Non-Activation Conditions
- **Activation**: Activates jointly with `software-development` for any production change to a frontend
  implementation surface — rendered markup, styles, frontend components, responsive behaviour, client-side
  interaction/state, browser-side accessibility mechanics, frontend performance, SSR/hydration/route rendering,
  or implementation of approved visual/motion specifications — regardless of whether the surface is visually
  distinctive or the task also touches backend code. `software-development` supplies the governing implementation
  baseline for the same task; `frontend-development` supplies the specialist execution procedure and owns
  frontend-specific decisions within it. Neither skill excludes the other for frontend work.
  - A task mixing frontend and backend surfaces splits by file/surface, the same way `task-framing` already
    splits mixed creative/product surfaces: the frontend-touching portion activates `frontend-development`; the
    backend portion proceeds under `software-development` alone.
- **Non-Activation**: Does not activate for surfaces with no frontend implementation component — pure backend
  business logic, database schemas, authorization policy, or infrastructure/deployment configuration. Does not
  activate to establish product behaviour, creative thesis, exact visual specification, or exact copy/strings —
  those remain owned by `product-design`, `creative-direction`, `visual-design`, `ux-writing`, and `copywriting`
  respectively; this skill implements their approved output.

## Required Inputs
- Original request or valid task frame.
- Approved `product-design` specification (behaviour, states, transitions), when applicable to the task.
- Approved `creative-direction` thesis, anti-references, and coherence rules, when one exists.
- Approved `visual-design` specification and reference screenshots or prototypes, when one exists and reference
  fidelity is required.
- Approved `ux-writing` interface strings and `copywriting` public-facing copy, when applicable.
- Existing frontend codebase architecture, conventions, and design-token/component-library setup.
- Accessibility, platform, browser-support, and performance constraints, when supplied or governed by project
  convention.
- Repository/worktree baseline state.
- *Note*: Not all inputs must exist. A bounded frontend task with no upstream specification package — a minor
  markup correction, an accessibility fix, or a maintenance change — grounds directly in the task frame, approved
  current behaviour, the approved design system, and established frontend conventions instead. The absence of an
  upstream package is a blocker only when the missing input is itself a material decision or prevents an accurate
  implementation, not merely because no package exists for this task.

## Authority Boundaries
- **Authorized Actions**:
  - Inspect only task-relevant frontend implementation surfaces, assets, and configuration, expanding read scope
    only when dependencies or execution evidence justify it.
  - Modify rendered markup, styles, frontend components, responsive behaviour, client-side interaction/state
    wiring, SSR/hydration/route rendering, frontend data-loading integration, and frontend build/bundling
    configuration within the task frame.
  - Choose internal component decomposition, local state-management structure, and CSS/styling organization
    consistent with established architecture.
  - Choose semantic HTML elements, document structure, and native interactive controls before custom substitutes,
    consistent with approved behaviour.
  - Implement approved motion, and make local, convention-supported motion-timing choices where no exact
    specification exists.
  - Add or update implementation-proximate frontend tests.
  - Run direct runtime self-validation: browser execution, viewport/interaction/keyboard-focus/reduced-motion
    checks, and performance measurement.
- **Unauthorized Actions**:
  - Modifying database schemas, persistence policy, authorization/security policy, backend domain rules, or
    infrastructure/deployment configuration.
  - Establishing product behaviour, workflows, states, or business rules.
  - Establishing or changing the creative thesis, brand voice, exact visual specification, or exact
    interface/promotional copy.
  - Adding a new frontend dependency, introducing a new design-token system, or overriding an approved token
    without authorization.
  - Originating signature choreography or a new interaction model.
  - Claiming independent verification or rendered-fidelity/behavioural correctness from code inspection alone.
  - Destructive worktree actions (`git reset --hard`, `git clean -fd`, broad checkout/restore) that could erase
    unrelated user work.

## Governing Baseline Contract
`frontend-development` operates under `software-development`'s general implementation discipline. The following
baseline is restated here, concisely, so this skill remains operationally self-contained rather than merely
referencing another file:
- Record the repository/worktree baseline (pre-existing modified, staged, and untracked files) before making
  changes, and preserve unrelated user work exactly as found.
- Confirm scope: modify only files within the frontend implementation surface authorized by the task frame; no
  opportunistic refactoring or unrelated cosmetic edits.
- Classify every proposed change as Mechanical, Bounded, or Material per
  [Frontend Change Classification](#frontend-change-classification) before implementing it.
- Implement the smallest complete change that satisfies the approved specifications and acceptance criteria.
- Add or update implementation-proximate tests directly required to validate the change.
- Validate the affected behaviour with direct runtime self-validation evidence — compilation, linting, or diff
  inspection alone is not behavioural proof.
- Inspect the resulting diff against the recorded baseline before reporting completion.
- Report exactly which checks were run, their exact results, which were not run and why, and residual risk —
  never claim untested behaviour as verified.
- Never use destructive worktree commands that could erase unrelated user work.

## Ordered Procedure
1. **Confirm Frame and Joint Authority**: Confirm a valid, executable task frame and that the task touches a
   frontend implementation surface, activating jointly with `software-development`'s baseline per
   [Activation and Non-Activation Conditions](#activation-and-non-activation-conditions).
2. **Record Baseline**: Record the repository/worktree baseline per the
   [Governing Baseline Contract](#governing-baseline-contract); distinguish pre-existing user work from
   agent-created changes.
3. **Inspect Grounding**: Inspect the approved product-design specification, approved creative-direction thesis,
   approved visual-design specification, and approved ux-writing/copywriting strings — each when applicable and
   when one exists — plus existing frontend architecture and conventions. For a bounded task with no applicable
   upstream package, ground directly in the task frame, approved current behaviour, and established conventions
   instead.
4. **Trace Implementation Surface**: Trace affected components, routes, rendering paths (SSR/hydration/client),
   data-fetch integration, imports, and dependencies.
5. **Classify Proposed Changes**: Classify every proposed change as Mechanical, Bounded, or Material per
   [Frontend Change Classification](#frontend-change-classification).
6. **Define Smallest Complete Change**: Define the smallest complete implementation that satisfies the approved
   specifications and acceptance criteria.
7. **Implement Incrementally**: Implement markup, styles, components, interaction, and approved motion within
   approved grounding, preserving unrelated work and respecting the
   [Product State vs Implementation State](#product-state-vs-implementation-state) and
   [Server-Rendered Frontend vs Backend](#server-rendered-frontend-vs-backend) boundaries.
8. **Add or Update Tests**: Add or update implementation-proximate frontend tests directly required to validate
   the change.
9. **Self-Check Creative Conformance**: When an approved creative-direction thesis exists, self-check the
   implementation against it per [Creative Conformance Self-Check](#creative-conformance-self-check), regardless
   of whether `creative-direction` is separately activated for review on this task.
10. **Compare Against Visual Specification (When Applicable)**: When an approved visual-design specification or
    explicit fidelity requirement exists, perform rendered comparison against it and reference screenshots at the
    required viewports, distinguishing supplied values from visually inferred approximations. When no reference
    target exists, validate against the applicable task frame and established conventions instead, and state
    explicitly that no external fidelity claim was made.
11. **Validate Runtime Behaviour**: Run the interface and gather self-validation evidence per
    [Self-Validation vs Independent Verification](#self-validation-vs-independent-verification) — exercised
    interactions, viewport checks, semantic structure and landmark inspection, keyboard/focus/reduced-motion
    behaviour, supported-browser checks when a browser matrix or platform constraint exists, and relevant
    performance evidence.
12. **Inspect Diff**: Inspect the resulting diff against the recorded baseline.
13. **Report Completion**: Report acceptance-criteria status, self-validation evidence (explicitly labeled as
    such), checks not run, residual risk, and the handoff status — to `testing-and-verification` when independent
    verification is required, or back to the current workflow/user otherwise.

## Frontend Implementation Boundary
- `product-design` owns user-visible behaviour, states, and consequences; `frontend-development` implements them
  and may organize internal structure without redefining them, per
  [Product State vs Implementation State](#product-state-vs-implementation-state).
- `creative-direction` owns the expressive thesis; `frontend-development` self-checks its implementation against
  an approved thesis per [Creative Conformance Self-Check](#creative-conformance-self-check) but does not
  originate the thesis.
- `visual-design` owns the exact visual specification when one exists; `frontend-development` implements it and
  performs rendered-fidelity self-validation against it. Absent an applicable specification or fidelity
  requirement, `frontend-development` grounds directly in the task frame and established conventions and does not
  claim external fidelity.
- `ux-writing` and `copywriting` own exact rendered wording; `frontend-development` implements the supplied
  strings without altering their meaning.
- `software-development` supplies the governing implementation baseline (scope, classification, evidence
  honesty) jointly with this skill's specialist frontend execution, per
  [Governing Baseline Contract](#governing-baseline-contract).
- `testing-and-verification` owns the independent verification verdict; this skill's own runtime checks are
  self-validation only, per
  [Self-Validation vs Independent Verification](#self-validation-vs-independent-verification).
- Backend domain rules, schemas, authorization policy, and infrastructure remain outside frontend authority
  regardless of repository structure, per
  [Server-Rendered Frontend vs Backend](#server-rendered-frontend-vs-backend).

## Disciplinary Routing
```text
task-framing
    ├─ product-design, when behaviour/workflows/states require definition
    ├─ creative-direction, when expressive authorship requires it
    └─ direct bounded task-frame grounding, when no upstream design package is required
           ↓
    applicable visual-design / ux-writing / copywriting outputs
           ↓
    software-development baseline + frontend-development specialist execution
           ↓
    ├─ testing-and-verification, when independently required
    └─ current workflow or user, otherwise
```
`frontend-development` consumes only the approved outputs applicable to the specific task — a bounded
interactive element consumes `product-design`'s states without waiting on an unrelated `creative-direction`
exercise, an expressive surface with no accounts consumes `creative-direction`'s thesis without a
`product-design` specification, and a bounded task with no applicable upstream package grounds directly in the
task frame, per `task-framing`'s existing conditional/parallel routing. Visual-design, ux-writing, copywriting,
and independent verification do not activate merely because `frontend-development` did; each activates only when
its own applicable conditions are met.

## Product State vs Implementation State
- `product-design` owns user-visible states, transitions, workflow consequences, permissions, and behavioural
  rules.
- `frontend-development` may choose internal implementation structure — component decomposition, local state
  organization, reducers, hooks, stores, and event wiring — only insofar as it preserves approved behaviour.
- A state-management choice that changes visible behaviour, persistence, permissions, recovery, or cross-surface
  consequences is Material and returns to the owning discipline. An internal reorganization that leaves every
  approved state, transition, and consequence observably unchanged is Bounded.

## Server-Rendered Frontend vs Backend
Frontend authority includes, where directly tied to rendering the web surface:
- server-rendered presentation, SSR, and hydration;
- route-level rendering;
- server components that render the frontend surface;
- browser-facing request wiring and rendering adapters;
- consuming and presenting data from existing, already-authorized contracts;
- framework loaders/actions only to the extent they delegate to already-authorized domain operations without
  redefining those operations' rules;
- frontend build and bundling configuration.

It excludes:
- persistence logic and database schemas;
- authorization and security decisions;
- domain validation policy;
- transaction semantics;
- destructive-operation policy;
- backend mutation rules;
- externally consequential API-contract changes.

A framework function called a "loader," "action," "server component," or "route handler" is not automatically
frontend-owned merely by that name or its file location. Classify it by responsibility and observable
consequence: a loader/action that calls an already-authorized operation and passes its result through to the
frontend is frontend work; a loader/action that itself decides what is permitted, validated, persisted, or
mutated is backend work regardless of which file it lives in.

## Frontend Change Classification
Preserves `software-development`'s Mechanical / Bounded / Material categories, specialized for frontend work.
- **Mechanical**: Exact implementation of a fully specified token/value; correcting a class-name typo; wiring an
  already-defined state; replacing an accidental framework default with the exact approved specification.
- **Bounded**: Component decomposition; local CSS/styling organization; internal state-management structure
  (local state, reducers, hooks, stores) that preserves approved behaviour; local, convention-supported motion
  timing.
- **Material**: New dependencies; new design-token systems; overriding an approved token; changing public
  behaviour or accessibility contracts; introducing a new responsive interaction model; originating choreography
  or interaction meaning; changing architecture or contracts outside existing authority.

A local accessibility implementation choice is not automatically Material. It becomes Material only when it
changes supported behaviour, keyboard/focus contracts, accommodation scope, dependencies, or established
interaction contracts.

## Semantic HTML and Browser Behaviour
`frontend-development` owns semantic element selection and document structure, not merely "rendered markup" in
the abstract:
- Semantic HTML elements and coherent document structure — headings, landmarks, lists, and native interactive
  elements (`button`, `a`, `input`, `select`, `dialog`) before custom substitutes, whenever they satisfy the
  approved behaviour.
- Correct landmark and heading relationships supporting the approved information hierarchy.
- Browser-specific rendering and interaction behaviour, verified against a supplied browser-support matrix or
  platform constraint when one exists.

Every completion report identifies the browser/runtime environment actually exercised, any relevant environments
not exercised, and the resulting uncertainty — this baseline reporting applies whether or not a browser-support
matrix exists. When a supplied browser-support matrix or platform constraint exists, additionally report coverage
against that matrix. When no matrix is supplied, do not invent one — validate in the available/default browser
environment and report exactly what was and was not exercised, the same evidence-honesty discipline
`testing-and-verification` already requires for untested paths.

## Motion Implementation
Kept as a distinct, separable section so a future independent motion skill could be split out without
restructuring the rest of this file; installing `frontend-development` does not resolve that question.

`frontend-development` may implement approved motion and make local, convention-supported choices involving:
- timing and easing;
- reduced-motion behaviour;
- interruption and reversal;
- lifecycle cleanup;
- input and viewport response;
- performance-conscious execution.

It may not originate signature choreography, interaction meaning, or a brand-defining motion language. Where no
exact motion specification exists, only local, reversible choices supported by established convention are
permitted (Bounded); anything establishing a new choreography or interaction model is Material and returns to
`task-framing` rather than being routed automatically and solely to any one discipline. `task-framing` determines
which authority resolves it: `creative-direction` may resolve expressive concept, signature meaning, and motion
character; `visual-design` may resolve only visual presentation aspects already within its installed authority
(for example, an established easing or spacing token), not exact choreography. Neither discipline automatically
owns exact choreography absent explicit authorization — the exact treatment may require explicit user
authorization or may remain unresolved while Milestone 3 gathers real implementation evidence.
`frontend-development` does not select the missing authority itself.

## Creative Conformance Self-Check
Whenever an approved creative-direction thesis exists, `frontend-development` self-checks its own implementation
against the thesis, anti-references, signature devices, and coherence rules as part of its own ordered
procedure — regardless of whether `creative-direction` is separately activated to run its own conformance or
rendered-review gate for this task. The two checks are independent:
- the self-check does not substitute for `creative-direction`'s own gate when it is activated;
- the absence of `creative-direction`'s gate on a given task does not exempt `frontend-development` from
  self-checking against an existing approved thesis.

## Self-Validation vs Independent Verification
`frontend-development` runs the interface, exercises affected interactions, inspects required viewports, compares
rendering against an approved visual-design specification or reference when one exists or fidelity is required —
otherwise validates against the applicable task frame, approved current behaviour, approved design-system
assets, and established conventions, explicitly stating that no external fidelity claim was made when no
reference target exists — inspects keyboard/focus/reduced-motion and responsive behaviour, and gathers relevant
performance evidence — using the same evidence classes
`testing-and-verification` already defines (visual/reference comparison, direct runtime observation, manual
interaction, accessibility checks) without redefining them.

This is **implementation self-validation**, never an independent verification verdict. Every deliverable must
label it as such. `testing-and-verification` independently selects proportionate checks, inspects the
implementation without relying on this skill's expectations, reconciles evidence against acceptance criteria, and
issues the formal verdict — unchanged and untouched by this skill. Self-validation does not override a later
independent finding, and a self-validation pass does not exempt the task from independent verification when it
is required.

## Implementation-Proximate Accessibility and Performance Boundary
`frontend-development` implements semantic structure, labels and relationships supplied by the relevant
disciplines (`ux-writing`'s accessible names and alternative text, `product-design`'s behavioural requirements),
keyboard and focus mechanics, reduced-motion handling, responsive behaviour, loading behaviour, and approved
performance constraints. It may run browser accessibility inspections and measure affected performance paths,
reporting the exact procedure and observed result for each.

It does not claim, from its own implementation self-validation:
- accessibility compliance;
- comprehensive assistive-technology support;
- comprehensive performance acceptability.

Performance budgets, browser-support requirements, and accessibility policies must come from supplied
requirements, project conventions, or authoritative platform constraints — this skill does not invent them.
Introducing a new supported-user scope, accommodation contract, or performance budget is a Material Decision.

## Evidence Requirements
- **Actionability**: Every procedural step must use imperative language and identify a concrete action plus its
  expected outcome or validation evidence.
- **Demonstrated Execution**: Include concrete examples demonstrating: joint activation for an ordinary,
  non-distinctive frontend surface; a bounded frontend task grounded directly in the task frame and established
  conventions with no applicable upstream specification package; rendered visual-fidelity self-validation
  distinguishing supplied from inferred values; a creative-thesis self-check performed independently of
  creative-direction's own gate activation; a product-state-vs-implementation-state boundary held during
  internal state-management reorganization; a server-rendered action that delegates to an already-authorized
  backend operation contrasted with one that would invent backend policy; a bounded local motion choice
  contrasted with a blocked material choreography proposal correctly returned to task-framing; a self-validation
  report later contradicted by testing-and-verification's independent finding.
- **Grounding Requirement**: Every implementation claim must trace to the applicable task frame, approved current
  behaviour, an applicable approved upstream discipline output (product-design, creative-direction, visual-design,
  ux-writing, or copywriting), approved design-system assets, or established architecture/convention. Every
  runtime claim must trace to direct browser/runtime observation, not static code inspection alone.

## Exact Deliverables
A frontend implementation package containing, as applicable:
- baseline repository/worktree state;
- files intentionally changed;
- controlling grounding consumed (the task frame, approved current behaviour, product-design, creative-direction,
  visual-design, ux-writing, copywriting, approved design-system assets, or existing conventions);
- change classifications;
- self-validation evidence (actions executed and exact observed results), explicitly labeled as self-validation;
- visual-fidelity comparison results when applicable, or an explicit statement that no reference target existed
  and no external fidelity claim was made;
- creative-conformance self-check result, when applicable;
- accessibility mechanics implemented and observed inspection results, explicitly not claimed as compliance;
- the browser/runtime environment actually exercised, relevant environments not exercised, and resulting
  uncertainty; additionally, coverage against a supplied browser-support matrix when one exists;
- motion implemented and its classification;
- acceptance-criteria status;
- tests or checks not run and why;
- residual risks;
- required handoff — to `testing-and-verification` when independent verification is required, or back to the
  current workflow/user otherwise.

## Frontend Acceptance Criteria
Criteria must be observable and traceable:
- **Rendered fidelity**: "At desktop width, the record list matches the approved visual-design specification's
  hierarchy and spacing; at narrow width, secondary metadata collapses per the approved responsive
  specification."
- **Behavioural fidelity**: "The archive confirmation flow matches product-design's approved state sequence
  exactly; no additional state was introduced."
- **Accessibility mechanics**: "Keyboard focus order follows the approved interaction sequence; visible focus
  indicators are present on all interactive elements."
- **Self-validation labeling**: "The completion report explicitly labels browser-executed checks as
  self-validation, not an independent verification verdict."
- **Reference fidelity applicability**: "No approved visual-design reference existed for this bounded fix;
  implementation followed established conventions and no external fidelity claim was made."
- **Performance-budget sourcing**: "The image-lazy-loading threshold matches the supplied performance budget; no
  budget was invented where none was supplied."
- *Avoid*: "Looks great.", "Feels smooth.", "Works well.", "Accessible.", "Fast."

## Validation Gates
Before claiming the frontend implementation complete:
- [ ] **Baseline Integrity**: Pre-existing user changes were identified and preserved.
- [ ] **Scope Integrity**: Only task-relevant frontend files were intentionally changed.
- [ ] **Change Classification**: Every change is classified per Frontend Change Classification; exact
      implementation of a fully specified value is not misclassified as Bounded.
- [ ] **Joint Activation Check**: `frontend-development` activated for the frontend surface regardless of visual
      ambition; `software-development`'s baseline was not silently excluded from frontend work.
- [ ] **Runtime Self-Validation**: Affected behaviour was exercised in a running interface; compilation, linting,
      or diff inspection alone is not claimed as behavioural proof.
- [ ] **Visual Fidelity Check**: One of the following holds and is explicitly stated: reference fidelity was
      checked against an approved visual-design specification/reference; reference fidelity was not applicable
      because no approved reference target or explicit fidelity requirement existed; or fidelity is blocked
      because a required material specification was missing. Inferred values are distinguished from supplied
      source values whenever fidelity was checked.
- [ ] **Semantic HTML Check**: Interactive and structural elements use semantic HTML and native controls before
      custom substitutes where they satisfy approved behaviour; heading and landmark structure is coherent.
- [ ] **Browser Behaviour Check**: The completion report always identifies the browser/runtime environment
      actually exercised, relevant environments not exercised, and the resulting uncertainty. When a
      browser-support matrix or platform constraint exists, the implementation was additionally checked against
      it and coverage is reported. No browser-support matrix is invented when none is supplied.
- [ ] **Creative Conformance Self-Check Performed**: When an approved thesis exists, the self-check ran
      regardless of whether creative-direction's own gate was separately activated.
- [ ] **Product-State Integrity**: No user-visible state, transition, or consequence was altered beyond what
      product-design approved; internal structure choices stayed internal.
- [ ] **Frontend/Backend Boundary Check**: No backend domain rule, schema, authorization, persistence, or
      infrastructure decision was made under frontend authority; a loader/action was classified by responsibility
      and observable consequence, not by its framework name or file location.
- [ ] **Motion Boundary Check**: Motion implementation stayed within approved or convention-supported bounds; a
      new choreography or interaction model was not originated, and any such need was returned to `task-framing`
      for authority determination rather than routed automatically and solely to `creative-direction`.
- [ ] **Accessibility Escalation Accuracy**: Accessibility choices were classified Material only when they
      changed supported behaviour, keyboard/focus contracts, accommodation scope, dependencies, or interaction
      contracts.
- [ ] **Accessibility/Performance Claim Integrity**: No claim of accessibility compliance, comprehensive
      assistive-technology support, or comprehensive performance acceptability was made from self-validation
      alone; any budget or policy applied was supplied or authoritative, not invented.
- [ ] **Self-Validation vs Verdict Labeling**: Every self-validation deliverable is explicitly labeled as such and
      not presented as an independent verification verdict.
- [ ] **Test Honesty**: Distinguish passed, failed, not-run, and unavailable checks. No check is claimed as
      passed unless executed.
- [ ] **Diff Inspection**: The resulting change set contains no accidental, unrelated, generated, or temporary
      files.
- [ ] **Acceptance Criteria Status**: Every acceptance criterion is explicitly marked satisfied, unsatisfied,
      blocked, or not verified.
- [ ] **Exclusions & Assumptions Check**: Assumptions and exclusions are documented.
- [ ] **No Placeholders**: No TODOs, accidental placeholders, or unresolved drafting markers remain. Clearly
      defined metavariables (such as `<component-name>`) are permitted.
- [ ] **Link Verification**: Apply link verification only when the task creates or modifies links.

## Stop and Failure Conditions
- **Halt Execution immediately when**:
  - An unresolved material decision (a new dependency, an accessibility-contract change, a new choreography
    proposal, a backend-boundary crossing) prevents valid completion within granted authority.
  - Approved visual, creative, or product specifications conflict and authority cannot resolve the conflict.
  - Runtime evidence is essential to valid completion of the requested outcome and no available alternative
    evidence (static inspection, compilation, implementation-proximate tests) can support it.
  - The task would require a database, authorization, or backend domain-rule decision outside frontend authority.
- **On Failure**:
  - Attempt to correct implementation defects that remain within the frame. Do not automatically halt because a
    compiler or test command fails.
  - When the environment cannot produce meaningful runtime self-validation evidence but a mechanical or
    statically checkable change remains implementable, continue: gather the compilation, static-inspection,
    and implementation-proximate test evidence that remains available, and mark runtime-dependent acceptance
    criteria `blocked` or `not verified` rather than treating their absence as an automatic hard stop.
  - Classify failures as: implementation defect; pre-existing repository failure; environmental/tooling failure;
    unavailable dependency or service; unresolved material decision; out-of-scope backend blocker.
  - Preserve partial work and self-validation evidence unless demonstrably invalid. Report the exact failing
    command, affected surface, current repository state, the environmental limitation and residual uncertainty,
    and distinguish implementation defects from environmental or policy blockers. Never claim behavioural
    completion without runtime evidence.

## Prohibited Behaviours
- **Framework-Default Substitution**: Silently replacing approved composition with a generic component-library
  default.
- **Behavioural Invention**: Changing product-visible state, permissions, or consequences to simplify
  implementation.
- **Backend Overreach**: Making database, authorization, or backend domain-rule decisions under frontend
  authority merely because the code lives in the same repository or framework directory.
- **Choreography Origination**: Inventing signature motion or interaction meaning instead of implementing
  approved direction or a local, convention-supported choice.
- **Verification Overclaim**: Presenting self-validation as an independent verification verdict, or claiming
  fidelity/behavioural correctness from code inspection alone.
- **Accessibility Misclassification**: Treating every accessibility implementation choice as Material, or
  conversely treating a supported-behaviour-changing accessibility choice as merely Bounded.
- **Opportunistic Refactoring**: Rewriting adjacent frontend systems merely because they appear imperfect.
- **Destructive Worktree Actions**: Using destructive worktree commands that could erase unrelated user work.
- **Silent Material Decisions**: Adding dependencies, introducing a new design-token system, or changing
  architecture/contracts without authorization.

## Conflict-Resolution and Evidence Hierarchy
This hierarchy resolves conflicts among workspace instructions and skill documents. It does not override
platform-level, system-level, safety, security, or tool-use requirements governing the agent.
- **Conflict Resolution**:
  1. User's explicit instructions in the current prompt.
  2. Workspace rules (`AGENTS.md` or equivalent).
  3. Governing standard (`.agents/skills/skill-authoring-standard/SKILL.md`).
  4. Individual skill `SKILL.md`.
  5. Global agent guidelines.
- **Frontend Evidence Authority (Source of Truth)**:
  The applicable authority depends on the specific issue at stake — the source with the most direct authority
  over that issue controls, not a single fixed ranking applied identically to every claim type.
  1. Current explicit user decisions and approvals, controlling only within the user's demonstrated authority
     over that specific issue.
  2. Approved accessibility, platform, and behavioural/security constraints, which bound every other source and
     are not relaxed by aesthetic or expressive goals.
  3. Approved product-design specification, which governs intended behaviour, states, and consequences.
  4. Approved visual-design specification and reference screenshots, which govern intended visual output and
     fidelity.
  5. Approved creative-direction thesis, anti-references, and coherence rules, which govern expressive
     conformance, not behaviour or visual token values.
  6. Approved ux-writing/copywriting packages, which govern exact rendered wording.
  7. Current architecture and established frontend conventions, which govern bounded implementation choices
     absent a controlling rule above.
  8. Direct browser/runtime observation, which governs what the implementation actually does — existing
     conventions or specifications cannot override observed runtime behaviour, and no specification authorizes a
     false claim about it.
  9. Skill defaults and model assumptions.

  Implementation self-validation under item 8 does not constitute an independent verification verdict;
  `testing-and-verification`'s formal verdict is the controlling completion authority once produced, and no
  self-validation result overrides a later independent finding.

## Concrete Usage Examples

> [!NOTE]
> Named execution skills, files, paths, products, and components in these examples are hypothetical unless
> explicitly identified as an installed skill. The repository currently contains `skill-authoring-standard`,
> `task-framing`, `product-design`, `creative-direction`, `visual-design`, `ux-writing`, `copywriting`,
> `software-development`, `testing-and-verification`, and `frontend-development`.

### Example 1: Joint Activation Regardless of Visual Ambition
- **Task**: Implement an ordinary "add staff member" form with no distinctive visual requirement.
- **Analysis**: No creative thesis or visual ambition is required for `frontend-development` to activate — the
  task touches rendered markup, a frontend component, and client-side validation wiring, so
  `frontend-development` and `software-development`'s baseline both apply jointly.
- **Classification**: Wiring the form's already-defined validation states to the approved product-design
  behaviour is Bounded (component decomposition); rendering the exact approved visual-design spacing/typography
  values is Mechanical.
- **Self-Validation**: Ran the form in the browser, exercised submit/validation-error/success states, confirmed
  rendered markup matches the approved specification.

### Example 2: Visual-Design Fidelity Self-Validation
- **Task**: Implement an approved visual-design specification for a record list at desktop and narrow viewports.
- **Grounding**: The approved specification states the record name uses the `Heading 2` role and secondary
  metadata uses the `Caption` role, subordinated at narrow width.
- **Self-Validation**: Rendered at >=1024px and <768px; confirmed the hierarchy is preserved at both widths;
  recorded a visually inferred hex value as an approximation rather than the source token, per visual-design's
  own screenshot-fidelity caution.
- **Labeling**: Reported explicitly as self-validation; `testing-and-verification` has not yet run its own
  independent check on this implementation.

### Example 3: Creative-Thesis Self-Check Independent of Creative-Direction's Own Gate
- **Task**: Implement the `FieldNotes` campaign hero section per `creative-direction`'s approved thesis
  (continuing seasonal record) and `visual-design`'s and `copywriting`'s specifications. `creative-direction` is
  not separately activated for review on this pass.
- **Self-Check**: `frontend-development` checks its own implementation against the approved anti-reference (no
  generic form-based data-collection template) and confirms the continuity metaphor is preserved in the rendered
  composition — performed regardless of whether `creative-direction` runs its own review this pass.
- **Boundary Held**: This self-check does not substitute for `creative-direction`'s own conformance or
  rendered-review gate when it is later activated; the two checks remain independent.

### Example 4: Product State vs Implementation State Boundary
- **Task**: Implement a multi-step record-archiving confirmation flow.
- **Grounding**: `product-design`'s approved states: initiate archive → confirmation → confirm archive → success;
  no persistence or permission change beyond what is approved.
- **Bounded Decision**: `frontend-development` organizes the confirmation flow internally using local component
  state and a single reducer — purely an implementation-structure choice that leaves the approved state
  sequence, its visible transitions, and its consequences unchanged.
- **Boundary Held**: A proposal to add a silent auto-save state not present in the approved specification would
  be Material and would return to `product-design`.

### Example 5: Server-Rendered Frontend vs Backend Boundary
- **Task**: Implement a server-rendered record-detail route using an existing framework data loader, and a
  companion "archive record" server action triggered from the same page.
- **Frontend Authority**: Route-level rendering, hydration, and the loader's browser-facing request wiring are
  `frontend-development`'s to implement. The loader calls an existing, already-authorized read endpoint;
  `frontend-development` consumes that contract as-is without redefining the underlying authorization policy or
  backend query logic, even though the loader function lives in the same repository/framework directory as the
  frontend code.
- **Contrast — Delegating Action (Frontend Work)**: The "archive record" action calls an existing,
  already-authorized `archiveRecord()` domain operation and returns its result to the page. Implementing the
  action's request wiring and passing the call through is frontend work.
- **Contrast — Rule-Inventing Action (Backend Work, Excluded)**: If the action instead decided for itself which
  users may archive which records, or persisted the status change directly against the database without going
  through an authorized operation, that is backend authorization/persistence policy — excluded regardless of the
  function's name or file location, and returned to `software-development` or the appropriate backend authority.

### Example 6: Motion — Bounded Local Choice vs Blocked Material Choreography
- **Task**: Implement a hover-state transition with no exact timing specified anywhere.
- **Bounded**: Apply the project's established 150ms ease-out convention already used elsewhere, since no
  approved motion specification conflicts with it.
- **Material (Blocked)**: A proposal to add a full-page scroll-driven parallax entrance for the same feature is
  Material — it introduces a new interaction model, not merely a hover timing. `frontend-development` does not
  route it directly to `creative-direction`; it returns the unresolved treatment to `task-framing`. Neither
  installed discipline automatically owns the exact choreography: `creative-direction` may resolve expressive
  concept, signature meaning, and motion character, but not necessarily the exact treatment; `visual-design` may
  resolve only visual presentation aspects already within its installed authority (for example, which
  established easing or spacing token applies), not exact choreography. Absent explicit user authorization, the
  exact treatment remains unresolved pending real implementation evidence under Milestone 3.

### Example 7: Self-Validation Later Contradicted by Independent Verification
- **Task**: Implement and report completion for a responsive navigation menu.
- **Grounding**: The approved `product-design` specification defines the narrow-viewport menu as a modal/dialog
  interaction. A supplied accessibility/platform requirement defines the focus contract: containment while open
  and return to the trigger control after close. `visual-design` may define the modal's visual presentation, but
  is not cited as authority for focus behaviour.
- **Self-Validation Report**: `frontend-development` ran the interface, exercised the menu open/close interaction
  at three viewports, confirmed keyboard focus order for the visible tab sequence, and reported this explicitly
  as self-validation, not a verification verdict.
- **Independent Verification**: `testing-and-verification` later independently performs keyboard and
  assistive-technology interaction not included in the self-validation pass, and observes that focus escapes the
  open menu into the page background instead of remaining contained within it as the approved contract requires,
  and fails to return to the trigger button after the menu closes.
- **Resolution**: The acceptance criterion for focus management fails against the approved modal/dialog contract;
  the defect routes back to `frontend-development` for correction. (A landmark inspection would separately verify
  landmark semantics, not focus-trap behaviour — the two checks are not interchangeable.)
- The episode demonstrates why self-validation does not substitute for, or override, the independent verdict —
  and, since this task's acceptance criteria required it, why the self-validation pass did not exempt the work
  from independent verification.

### Example 8: Bounded Task With No Applicable Upstream Specification Package
- **Task**: Fix an accessibility defect where a settings toggle has no accessible name, on a page with no active
  product-design, creative-direction, or visual-design engagement for this task.
- **Grounding**: No upstream specification package exists for this bounded fix. `frontend-development` grounds
  directly in the task frame (fix the missing accessible name) and the approved current behaviour (the toggle's
  existing function, unchanged).
- **Action**: The toggle already has an approved visible label rendered beside it. `frontend-development`
  mechanically associates that existing label with the control using `aria-labelledby` — a technical association
  and rendering fix, not new wording authorship, requiring no `ux-writing` involvement.
- **Boundary Held**: If no approved visible label or accessible-name string existed anywhere for this control,
  `frontend-development` would not invent one; the exact wording would return to `ux-writing`, and this skill
  would implement whatever string it supplies.
- **Fidelity Statement**: No approved visual-design reference existed for this fix. Reference fidelity is
  reported as **not applicable**, not as checked or blocked — no external fidelity claim is made.
