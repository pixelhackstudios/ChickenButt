---
name: creative-direction
description: |
  Establishes and governs the approved expressive thesis and cross-disciplinary coherence rules that make a
  product or digital experience specific, authored, and recognizably itself rather than an interchangeable
  assembly of familiar interface patterns.
  Execute when establishing or reusing a product's creative thesis, defining anti-references and signature
  devices, reviewing downstream creative specifications for conformance, or reviewing a rendered implementation
  for concept fidelity.

  Trigger immediately for:
  - New products, major redesigns, or establishing/materially changing a visual or expressive language.
  - Flagship or public-facing work, or internal work whose success materially depends on distinctive authorship.
  - Reviewing whether a visual-design, ux-writing, or copywriting output — or a rendered implementation —
    conforms to an approved creative thesis, anti-reference, signature device, or coherence rule.

  DO NOT trigger for:
  - Product behaviour, workflows, states, permissions, or business rules (owned by `product-design`).
  - Authoring exact layout, spacing, colour values, typography scales, or component specifications (owned by
    `visual-design`) — creative direction may review these for conformance without authoring them.
  - Authoring exact interface strings (owned by `ux-writing`) — creative direction may review these for
    conformance without authoring them.
  - Production implementation or independent technical/behavioural/accessibility verification (owned by
    `software-development`/`frontend-development`, `testing-and-verification`).
  - Purely mechanical, invisible, or minor local work that cannot materially affect the established expressive
    identity.
---

# Creative Direction

This skill governs the establishment, persistence, and conformance review of a product's expressive creative
thesis and the cross-disciplinary coherence rules that unify visual design, typography, imagery, motion,
interaction, copy, and sound into one authored identity. It exists to prevent technically compliant, disciplined
execution from still producing a competent but interchangeable result.

## Purpose and Exclusive Responsibility
- **Goal**: Establish, persist, and defend a product-specific creative thesis that gives downstream disciplines a
  concrete, falsifiable basis for distinctive, coherent execution — and to catch drift toward generic patterns
  before and after implementation.
- **Exclusive Responsibility**: Establish and govern the approved expressive thesis and cross-disciplinary
  coherence rules that make a product or digital experience specific, authored, and recognizably itself rather
  than an interchangeable assembly of familiar interface patterns.

## Responsibility Boundaries
- **Primary Responsibility**: Owns the expressive thesis; intended emotional and cultural impression; creative
  ambition; anti-references; product-specific generic-design prohibitions; concept-level signature devices;
  cross-disciplinary relationships among typography, imagery, motion, interaction, copy, sound, and space;
  reference decomposition; deliberate departures from convention; creative-conformance criteria; and the
  authored-coherence review of both specifications and rendered implementation.
  - Creative direction may define the intended verbal character or tone concept (for example, "understated and
    confident rather than promotional") as part of the expressive thesis. It does not author exact public-facing
    copy, interface strings, or promotional wording — those remain `copywriting`'s and `ux-writing`'s domains
    respectively — and it does not establish brand positioning, product naming, or material brand identity
    without authorization.
- **Adjacent Responsibilities**: Consumes the approved specification from `product-design` as grounding when one
  exists. For a task with no product-design specification — a public, expressive, editorial, or campaign surface
  with no accounts, workflows, or state-changing behaviour — grounds directly in the valid task frame, target
  audience, communication objective, content requirements, approved brand evidence, and user-approved references
  instead. Hands
  approved creative-brief entries and task-authorized bounded creative decisions to `visual-design`, `ux-writing`,
  and `copywriting` (the discipline responsible for promotional or public-facing copy) as controlling creative
  evidence. Clearly marks newly proposed, unresolved, rejected, or superseded entries as non-controlling. Reviews
  their output through the bounded creative-conformance gate. Reviews rendered implementation whenever a
  rendered implementation exists, running alongside `testing-and-verification` when independent verification is
  also required for that task, without replacing it.
  - `visual-design` authors exact visual specifications; `ux-writing` authors exact interface strings;
    `copywriting` authors promotional and public-facing copy. `creative-direction` may review those outputs for
    conformance but does not author their discipline-specific execution.
- **Explicit Exclusions**: Does not own product behaviour, workflows, states, permissions, information
  architecture, or business rules; exact layouts, spacing, colour values, type scales, components, or responsive
  specifications; exact interface strings; promotional copy execution; production implementation; testing or
  technical/accessibility/performance verification; or unrestricted brand strategy, product positioning, naming,
  logos, palettes, typography systems, mascots, or illustration systems without authorization.
  - Approved product specifications, references, and explicit user decisions are controlling evidence this skill
    interprets and expresses through — it does not redefine them.
- **Handoff Conditions**: After the thesis is established or reused, hand approved creative-brief entries and
  task-authorized bounded creative decisions to `visual-design`, `ux-writing`, and `copywriting` as controlling
  creative evidence; newly proposed, unresolved, rejected, or superseded entries may be
  shared for review but do not control implementation until approved or task-authorized. After their
  specifications exist, run the creative-conformance gate and route violations back to the responsible
  discipline. After implementation exists, run rendered creative review and route fidelity losses to the
  responsible discipline. Return unresolved brand/positioning decisions, persistence-location decisions, and
  unresolved conformance disputes to `task-framing`.

## Activation and Non-Activation Conditions
Three explicit activation modes. `task-framing` selects the mode but must not silently classify
identity-establishing or identity-changing work as bypassed.

### Full Creative-Direction Exercise
Required for:
- new products;
- major redesigns;
- establishing or materially changing a visual or expressive language;
- flagship or public-facing work;
- internal product surfaces whose success materially depends on distinctive authorship;
- work that establishes or changes the intended impression, signature devices, anti-references, or cross-product
  creative rules.

Produces proposed creative-brief content. This becomes a durable, reusable creative brief only once persisted at
an authorized location with its approval and version status recorded — see [Durable Creative Brief](#durable-creative-brief).

### Thesis Reuse with Bounded Conformance Review
Required when an established thesis exists and the task could affect:
- signature devices;
- intended impression;
- anti-references;
- visual/verbal relationships;
- motion, imagery, or interaction character;
- cross-surface coherence.

Does not re-derive the thesis. Loads the existing brief as controlling evidence and runs the bounded
conformance gate against the specific task.

### Bypass
Permitted only for work that is mechanical, invisible, technical, or minor and local, and that cannot materially
affect the established expressive identity.

- **Non-Activation**: Creative direction does not own the creation of exact visual specifications, exact
  interface strings, promotional copy execution, production implementation, or independent technical
  verification. It may activate to review those artifacts for conformance with an approved creative thesis when
  the applicable activation mode requires it.
  - `visual-design` creates exact visual specifications.
  - `ux-writing` creates exact interface strings.
  - `copywriting` creates promotional and public-facing copy.
  - `creative-direction` may review those outputs but does not author their discipline-specific execution.

## Required Inputs
- Original request or valid task frame.
- Approved `product-design` specification (users, problem, workflows, states) as grounding, when one exists;
  otherwise, the task frame's stated audience, communication objective, content requirements, approved brand
  evidence, and user-approved references serve as grounding.
- The existing creative brief, when one exists, at a location supplied by the task or governed by workspace
  convention.
- User-supplied references, anti-references, and explicit creative decisions.
- Accessibility, platform, behavioural, and technical constraints supplied by other disciplines.
- Downstream specifications (`visual-design`, `ux-writing`, and `copywriting`) when running the conformance gate.
- A rendered implementation or observable artifact when running rendered creative review.
- *Note*: Not all inputs must exist; explicitly identify missing information that prevents grounding the thesis.

## Authority Boundaries
- **Authorized Actions**:
  - Inspect the approved product specification, existing creative brief, and task-relevant references.
  - Draft a new thesis, intended impression, anti-references, signature devices, and cross-disciplinary
    coherence rules; propose amendments to any of these; and apply bounded amendments only when the current task
    frame or governing process authorizes that class of decision.
  - Conduct bounded proactive reference research under the conditions in [Bounded Proactive Reference Research](#bounded-proactive-reference-research).
  - Operate the bounded creative-conformance gate against downstream specifications.
  - Conduct rendered creative review against an existing implementation.
  - Propose amendments to the durable creative brief, and write them only when the location is supplied or
    governed by workspace convention, the task authorizes creating or amending it, and the change preserves
    version history, approval status, and superseded decisions. See [Durable Creative Brief](#durable-creative-brief).
- **Unauthorized Actions**:
  - Writing production code or production configuration.
  - Authoring exact visual specifications (`visual-design`'s domain) or exact interface strings (`ux-writing`'s
    domain).
  - Making or silently altering product behaviour, workflow, or business rules.
  - Establishing brand identity, product positioning, naming, logos, palettes, typography systems, mascots, or
    illustration systems without explicit authorization.
  - Applying a material thesis amendment merely because creative-direction classified or proposed it, rather
    than because `task-framing` authorized it.
  - Assuming, inventing, or writing to any persistence path for the durable creative brief that is not supplied
    by the task or governed by an existing workspace convention. Selecting or changing that location is a
    workspace-level decision when no governing convention exists, and must be routed to `task-framing` rather
    than decided silently.
  - Writing outside its own skill package (`.agents/skills/creative-direction/`) except for an authorized creative
    brief update meeting the conditions above.
  - Holding downstream work indefinitely through repeated subjective rejection.
  - Prescribing execution details owned by another discipline when returning work through the conformance gate.
  - Describing a self-drafted thesis, amendment, signature device, anti-reference, or coherence rule as approved
    without supporting approval evidence. See [Approval-Status Integrity](#approval-status-integrity).
  - Treating a newly proposed or unresolved entry as controlling creative evidence for downstream implementation.
  - Rewriting or weakening an approved creative brief entry after implementation solely to make a divergent
    execution appear conformant. See [Rendered Creative Review](#rendered-creative-review).

## Ordered Procedure
1. **Confirm Activation Mode**: Confirm whether the task requires a full exercise, thesis reuse with bounded
   conformance review, or bypass, per the activation conditions above.
2. **Inspect Grounding**: Inspect the approved `product-design` specification when one exists; otherwise inspect
   the task frame's audience, communication objective, and content requirements. In both cases, also inspect the
   existing creative brief (if any) and any user-supplied references, anti-references, and explicit decisions.
3. **Assess Evidence Sufficiency**: For full-exercise tasks, determine whether supplied evidence is sufficient to
   calibrate ambition. If not, conduct bounded proactive reference research.
4. **Draft or Reuse the Thesis**: For full-exercise tasks, draft the creative thesis, intended impression, and
   memorable idea, stating what it emphasizes, suppresses, repeats, contrasts, permits, and prohibits, satisfying
   [Creative Quality Criteria](#creative-quality-criteria). Mark it newly proposed and non-controlling. For reuse
   tasks, load the existing approved thesis as controlling evidence.
5. **Define Anti-References and Prohibitions**: Define product-specific anti-references and evaluate the
   operational anti-generic standard, documenting any justified exception.
6. **Define and Classify Signature Devices**: Propose signature devices at the concept level and classify each
   per [Creative Decision Classification](#creative-decision-classification) and its specialization in
   [Signature Device Classification](#signature-device-classification). Route material devices to `task-framing`.
7. **Define Cross-Disciplinary Coherence Rules**: Define how typography, imagery, motion, interaction, copy,
   sound, and space relate to express the thesis consistently.
8. **Define Creative Acceptance Criteria**: Define observable, falsifiable creative criteria the thesis implies.
9. **Persist or Flag the Brief**: Propose the durable brief content, distinguishing supplied-approved, authorized
   bounded, newly-proposed, rejected, superseded, and unresolved entries per [Approval-Status Integrity](#approval-status-integrity).
   Write it only within the persistence boundaries in [Durable Creative Brief](#durable-creative-brief); otherwise
   present it conversationally or task-scoped, report the persistence status explicitly, and flag the missing
   persistence decision.
10. **Hand Off Controlling Evidence**: Hand approved creative-brief entries and task-authorized bounded creative
    decisions to `visual-design`, `ux-writing`, and `copywriting` as controlling creative evidence. Mark any
    remaining newly proposed, unresolved, rejected, or superseded entries as non-controlling.
11. **Run the Conformance Gate**: When downstream specifications exist, run the bounded creative-conformance
    gate in [Bounded Creative-Conformance Gate](#bounded-creative-conformance-gate). Route violations to the
    responsible discipline with the required citation. Route unresolved disputes per the dispute-resolution rule.
12. **Run Rendered Creative Review**: When an implementation exists, run [Rendered Creative Review](#rendered-creative-review).
    Identify whether fidelity was lost in the brief, the specifications, or the implementation, and route
    accordingly without retroactively weakening the approved brief.
13. **Report**: Report the thesis status, conformance verdicts, rendered-review verdict, escalations, persistence
    status, and brief update status.

## Evidence Requirements
- **Actionability**: Every procedural step must use imperative language and identify a concrete action plus its
  expected outcome or validation evidence.
- **Demonstrated Execution**: Include concrete examples demonstrating: establishing a product-specific thesis
  that prevents a generic dashboard; decomposing an external reference without copying its aesthetic; returning
  a visual-design execution that violates an approved anti-reference; accepting an unconventional treatment
  justified by the thesis; classifying a signature device as material; reusing an existing thesis for a bounded
  feature; reviewing a rendered implementation and routing a fidelity loss; a request blocked by unresolved brand
  authority.
- **Grounding Requirement**: Every thesis claim must trace to the approved product specification (when one
  exists), the task's stated audience and communication objective (when there is no product-design
  specification), or explicit user/reference evidence. A thesis invented independently of all available grounding
  — product-design's specification, the task frame, or user-supplied evidence — is not valid evidence for
  downstream disciplines.

## Durable Creative Brief
A versioned, product-scoped artifact containing, as applicable (do not require an irrelevant category):
- product and audience grounding;
- approved creative thesis;
- intended emotional and cultural impression;
- memorable experience or central idea;
- anti-references;
- prohibited generic patterns;
- signature devices and their decision classifications;
- cross-disciplinary coherence rules;
- relationships among typography, imagery, motion, interaction, copy, sound, and space;
- deliberate departures from convention;
- accessibility, platform, behavioural, and technical constraints affecting the concept;
- reference decomposition;
- explicit "must not copy" boundaries;
- creative acceptance criteria;
- bounded decisions;
- unresolved material decisions;
- current approval status;
- proposed amendments;
- superseded decisions;
- task-specific application history;
- assumptions and exclusions.

### Persistence Boundary
- A full creative-direction exercise must produce proposed creative-brief content. A durable, reusable creative
  brief exists only after that content has been persisted at an authorized location with its approval and
  version status recorded. This skill does **not** assume where that artifact lives.
- Any storage path referenced in this document or in examples (for instance a path under `.agents/resources/`) is
  **hypothetical** and illustrative only, not an authorized or existing location.
- The requirement to persist the artifact is distinct from the decision about where it is persisted. When no
  workspace convention governs creative-brief storage, selecting or changing that location is a workspace-level
  decision and must be routed to `task-framing`, not decided silently by this skill.
- This skill may create or amend the authorized creative brief only when all of the following hold:
  - its location is supplied by the task or governed by an existing workspace rule;
  - the task authorizes creating or amending it;
  - the change preserves version history, approval status, and superseded decisions rather than overwriting them.
- Absent an authorized, governed location, this skill presents the thesis conversationally or as a task-scoped
  artifact and explicitly flags the unresolved persistence decision rather than writing it anywhere.
- This skill has no standing write authority outside its own skill package (`.agents/skills/creative-direction/`)
  beyond an authorized brief update meeting the conditions above.

### Completion Status Without Persistence
- The creative analysis may complete without an authorized persistence location; only the resulting brief's
  durability is blocked, not the analysis itself.
- An unpersisted conversational or task-scoped output is not a durable brief and must never be reported as one.
- Downstream work within the same bounded task may use approved or task-authorized thesis elements even before
  persistence occurs.
- Cross-task thesis reuse requires a persisted artifact at an authorized location — a later task cannot treat a
  prior task's conversational draft as an approved, reusable brief.
- The agent must always report the persistence status explicitly (`persisted`, `not persisted`, or `blocked`) and
  never imply persistence occurred when it did not.
- Halt only when the requested work explicitly depends on cross-task persistence and no location is authorized.

## Approval-Status Integrity
Creative direction may draft or propose a thesis, amendment, anti-reference, signature device, or coherence rule.
It must not treat any of these as approved merely because the skill itself created them.

The following must remain distinguishable at all times:
- supplied approved decisions;
- current approved brief entries;
- authorized bounded creative decisions, including their authority basis;
- newly proposed bounded decisions awaiting authorization, when the task frame does not grant decision authority;
- proposed material amendments;
- rejected decisions;
- superseded decisions;
- unresolved decisions.

A bounded creative decision may be recorded as authorized without separate user approval when the current task
frame, workspace rules, or another controlling source explicitly grants creative-direction authority to make
that reversible class of decision. The output must record the authority basis. The decision is not authorized
merely because the model generated it.

A newly drafted thesis element is a proposal until it is approved by the applicable authority (the user, a
governing brief update process, or another explicitly authorized source), or recorded as an authorized bounded
decision under an explicit authority grant — never by virtue of having been authored.

## Creative Decision Classification
Every creative decision — not only signature devices — is classified using this model.

### Observed Creative Constraint
A creative requirement or boundary imposed by:
- explicit user decisions;
- approved references or anti-references;
- approved product grounding;
- an approved creative brief;
- approved brand or voice assets;
- accessibility, platform, behavioural, safety, performance, or technical constraints.

Observed constraints are recorded, not invented.

### Bounded Creative Decision
A reversible, product-specific expressive choice that:
- is supported by controlling evidence;
- does not establish or materially change brand identity or public positioning;
- does not alter product behaviour, navigation, information visibility, accessibility approach, supported users,
  architecture, or performance policy;
- remains within the current approved thesis;
- can be revised without creating externally consequential meaning.

When the current task frame, workspace rules, or another controlling source grants creative-direction authority
to make this class of decision, it may proceed as an authorized bounded decision without separate approval,
recording its authority basis. Absent that grant, it remains a proposed bounded decision awaiting authorization
rather than proceeding on its own.

Examples include: selecting a concept-level pacing principle; defining a bounded anti-reference for one surface;
proposing a reversible relationship between imagery and typography; choosing a concept-level signature treatment
that remains within approved product and technical constraints.

### Material Creative Decision
A decision that establishes or materially changes:
- brand identity;
- product positioning;
- intended audience impression;
- product naming;
- public meaning;
- cross-product expressive language;
- major signature devices;
- navigation or interaction paradigms;
- accessibility approach;
- supported users;
- major motion or spatial behaviour;
- performance budget;
- implementation architecture;
- persistent cross-surface visual or verbal rules.

Material creative decisions require authorization through `task-framing`. This skill must not apply a material
amendment merely because it classified or proposed it.

## Signature Device Classification
This is a specialized application of [Creative Decision Classification](#creative-decision-classification) to
signature devices specifically. Signature devices are not automatically bounded — classify each proposed device
by its consequences.

- **Bounded Creative Decision**: Reversible, supported by the approved product and creative direction, limited to
  expressive treatment, and compatible with established behaviour, accessibility, platform, performance, and
  architecture constraints. Example: an editorial asymmetric type treatment on a marketing header.
- **Material Decision**: Establishes or changes navigation behaviour, interaction sequence, information
  visibility, accessibility approach, supported users, performance budget, implementation architecture, brand
  identity, product-wide visual language, major motion or spatial behaviour, or public meaning. Example:
  replacing standard dashboard navigation with a cinematic spatial journey.

Material signature-device decisions return to `task-framing` for authorization, the same escalation pattern
`product-design` and `visual-design` already use for their own material decisions. A device originating from a
creative idea is not exempt from this scan.

## Anti-Generic Standard (Operational)
This skill actively evaluates for unjustified use of:
- bootcamp-tier Tailwind composition;
- framework defaults presented as authored design;
- generic shadcn/component-library appearance;
- interchangeable SaaS dashboards;
- repetitive card grids;
- excessive rounded containers;
- decorative pill badges;
- default hero-copy-plus-illustration structures;
- arbitrary gradients, blobs, glass effects, and excessive shadows;
- animation added as decoration after composition rather than integrated into the concept;
- trend imitation without a product-specific rationale;
- visual uniformity that removes hierarchy, rhythm, tension, or memorable structure;
- "clean," "modern," "premium," "beautiful," "bold," or "immersive" used as complete creative concepts.

These patterns are not universally forbidden. They may be used when a documented, thesis-specific reason
justifies them. Evaluate the relationship between the technique and the concept, not merely whether the
technique is common.

"Bootcamp-tier Tailwind composition" is a summary label for the target failure, not itself an observable finding
and not a standalone basis for a conformance-gate rejection. Any rejection must cite the actual observable
pattern and the violated creative criterion — for example: framework defaults left intact without adaptation,
repetitive undifferentiated cards, arbitrary pill badges, generic hero composition, absent product-specific
hierarchy, or the specific absence of a documented thesis-specific rationale for a listed pattern.

## Creative Quality Criteria
A credible full creative-direction exercise must make it possible to determine:
- why the concept belongs to this product and its users;
- what a viewer or user should remember;
- what the design deliberately refuses to become;
- what distinguishes it from competent category conventions;
- how the concept changes downstream visual, verbal, motion, imagery, interaction, and spatial choices;
- where deliberate convention-breaking is permitted;
- what must remain conventional for usability, accessibility, or product integrity;
- how coherence will be evaluated before and after implementation.

Do not require spectacle, animation, asymmetry, editorial typography, or unconventional navigation by default.
Do not require a signature device merely to satisfy a checklist. Instead:

> A full exercise must either define at least one justified memorable or differentiating device, relationship, or
> structural principle, or explicitly explain why restraint and the absence of a conspicuous device better
> express the product-specific thesis.

## Observable Creative Consequences
Every creative thesis must translate into consequences that can guide downstream work, not remain an adjective.
- *Avoid*: "The product should feel premium, human, and immersive."
- *Prefer*: "The tool treats each season's field observations as a continuing record of a place rather than a
  batch of isolated form submissions. Typography establishes seasonal reading breaks, prior observations remain
  spatially present alongside new ones, motion communicates continuity between visits, and entry metadata is
  prevented from becoming the dominant visual structure."

Define what the thesis emphasizes, suppresses, repeats, contrasts, permits, prohibits, makes memorable, and
requires across disciplines.

## Bounded Proactive Reference Research
Begin with:
- approved product behaviour;
- users and product context;
- the existing creative brief;
- user-supplied references and anti-references;
- explicit user decisions.

External research is permitted only for full-exercise tasks, and only when supplied evidence is insufficient to
calibrate ambition or explore relevant approaches. Research output must:
- name the reference;
- identify the specific principle being studied;
- distinguish structure, typography, imagery, motion, interaction, pacing, density, and narrative treatment where
  applicable;
- explain relevance to the current product;
- state what must not be copied;
- derive a product-specific rule;
- avoid importing another product's identity wholesale.

User-approved references and anti-references outrank independently sourced references. Routine thesis-reuse
tasks do not trigger fresh research automatically.

## Bounded Creative-Conformance Gate
`creative-direction` may return `visual-design`, `ux-writing`, or `copywriting` output for revision only by
identifying:
- the exact approved thesis element, anti-reference, signature device, coherence rule, or creative acceptance
  criterion that is violated;
- the observable conflict;
- the required outcome;
- the discipline responsible for resolving it.

It may not reject work based on unstated personal taste, invent new creative requirements during review, or
override explicit user decisions, approved references, product behaviour, accessibility or platform constraints,
or unresolved material brand decisions — those conflicts escalate through `task-framing`. Downstream work
determines the compliant execution within its own authority; `creative-direction` does not prescribe details
owned by another discipline.

### Dispute Resolution
When `creative-direction` and the responsible downstream discipline disagree about whether a criterion is
violated:
- each discipline records its evidence and authority basis;
- the dispute returns to `task-framing`;
- material, preference-sensitive, or unresolved interpretation conflicts escalate to the user;
- `creative-direction` may not hold work indefinitely through repeated subjective rejection;
- downstream work may not be declared complete while a documented, unresolved conformance conflict remains.

## Rendered Creative Review
```text
task-framing (routes according to the task's dominant purpose)
    ├─ product-design, only when behaviour, workflow, forms, transactions, permissions, or interaction-state
    │  logic require it
    └─ creative-direction establishes or reuses the thesis
           ↓ (both branches feed forward)
visual-design / ux-writing / copywriting
    ↓
creative-conformance specification review
    ↓
software-development baseline + frontend-development specialist execution (when the implementation is a frontend surface)
    ↓
    ├─ rendered creative review (creative-direction), whenever a rendered implementation exists
    └─ testing-and-verification, when independent verification is required by the task frame, governing
       process, risk, or acceptance criteria
    ↓ (both, when both run, produce independent verdicts over the same implementation)
final completion or routed revision
```

Rendered creative review:
- occurs after an implementation exists;
- evaluates the rendered experience against the approved thesis and creative acceptance criteria;
- identifies whether fidelity was lost in the creative brief, the visual or language specifications, or the
  implementation;
- routes revisions to the responsible discipline (`creative-direction` itself if the brief was insufficient,
  `visual-design`/`ux-writing`/`copywriting` if the specification was the point of loss,
  `software-development`/`frontend-development` if implementation diverged from a faithful specification);
- does not modify production code;
- runs whether or not independent technical verification is required for this task;
- does not own behavioural testing, technical correctness, accessibility verification, or performance
  verification — independent verification evidence and its formal verdict remain owned by
  `testing-and-verification`, when independent verification is required; implementation and self-validation
  evidence remain owned by `software-development`/`frontend-development`;
- does not replace `testing-and-verification` when it does run; both may run over the same implementation, each
  producing its own independent verdict.

### Brief Integrity During Rendered Review
When rendered work conflicts with the current approved brief, `creative-direction` must first determine whether
the brief, the downstream specification, or the implementation is the point of failure. It may propose a brief
amendment only when new evidence genuinely justifies changing the direction — not merely because the current
implementation diverges from it. It must not retroactively weaken, reinterpret, or replace an approved criterion
merely to permit the current implementation to pass.

If a proposed amendment is material:
- route it through `task-framing`;
- preserve the current approved criterion until the amendment is authorized;
- keep the rendered implementation classified nonconformant against the current brief until then.

## Exact Deliverables
As applicable, delivered internally, conversationally, or as a persisted brief update within the persistence
boundary:
- the creative thesis and its grounding;
- anti-references and prohibited generic patterns with justified exceptions;
- signature devices with classification;
- cross-disciplinary coherence rules;
- creative acceptance criteria;
- reference decomposition, when research was conducted;
- bounded decisions, marked authorized or proposed;
- unresolved material decisions;
- conformance-gate verdicts, with citation of the violated element, observable conflict, required outcome, and
  responsible discipline;
- dispute records, when a conformance disagreement occurred;
- rendered-review verdict and fidelity-loss attribution;
- approval status for every entry (supplied-approved, authorized bounded, newly-proposed, rejected, superseded,
  or unresolved) — only supplied-approved and authorized-bounded entries are controlling creative evidence for
  downstream disciplines;
- persistence status (persisted approved, persisted proposed amendment, task-scoped draft, or blocked);
- brief update status (created, amended, unchanged, or blocked on a persistence decision);
- assumptions and exclusions.

## Validation Gates
Before claiming a creative-direction pass complete:
- [ ] **Activation Mode Justified**: The selected mode (full, reuse, bypass) matches the activation conditions.
- [ ] **Grounding Check**: The thesis traces to the approved product specification and users when one exists, or
      to the task frame's audience, communication objective, and content requirements when it does not — not an
      invented vacuum.
- [ ] **Adjective Ban**: No thesis statement relies solely on unsupported adjectives ("premium," "clean,"
      "modern," "beautiful," "bold," "immersive") without translated, observable consequences.
- [ ] **Anti-Pattern Justification**: Any use of a listed generic pattern carries a documented, thesis-specific
      rationale, and any rejection cites the actual observable pattern rather than the summary label alone.
- [ ] **Creative Quality Check**: A full exercise establishes why the concept belongs to this product, what
      should be remembered, what category conventions it rejects or transforms, how it affects downstream
      disciplines, and how coherence will be reviewed. It either defines a justified differentiating device,
      relationship, or structural principle, or explains why deliberate restraint is the more product-specific
      expression. This gate must not require spectacle, animation, asymmetry, editorial typography, or
      unconventional navigation.
- [ ] **Creative Decision Classification**: Every proposed creative decision, not only signature devices, is
      classified as an observed constraint, bounded decision, or material decision by its actual consequences.
- [ ] **Signature Device Classification**: Every proposed device is classified bounded or material by its actual
      consequences, and material devices are routed to `task-framing`.
- [ ] **Persistence Boundary Check**: No creative-brief write occurred outside an authorized, governed location;
      an unresolved persistence decision is flagged rather than silently resolved.
- [ ] **Persistence-Status Accuracy**: The output distinguishes persisted approved briefs, persisted proposed
      amendments, task-scoped drafts, and blocked persistence. It never describes an unpersisted draft as a
      durable artifact.
- [ ] **Approval-Status Integrity**: Every creative entry records its status and authority basis. Model-authored
      work is not treated as approved by authorship alone, while bounded decisions explicitly authorized by the
      task frame are not unnecessarily escalated.
- [ ] **Controlling-Evidence Integrity**: Only supplied-approved entries and task-authorized bounded decisions are
      handed to downstream disciplines as controlling creative evidence; newly proposed, unresolved, rejected, or
      superseded entries are marked non-controlling.
- [ ] **Gate Citation Completeness**: Every conformance-gate return names the violated element, the observable
      conflict, the required outcome, and the responsible discipline, without prescribing another discipline's
      execution detail.
- [ ] **Dispute Trace**: Any disagreement is recorded with evidence and authority basis before escalating to
      `task-framing` or the user.
- [ ] **No Indefinite Hold**: A conformance rejection does not recur without new evidence; unresolved disputes
      escalate rather than repeat.
- [ ] **Rendered-Review Scope**: Rendered review claims no behavioural, accessibility, or performance
      verification and made no production-code change.
- [ ] **Brief Integrity Under Review**: A rendered-review finding did not retroactively weaken or reinterpret an
      approved brief criterion merely to make a divergent implementation appear conformant.
- [ ] **Brief Currency**: When the brief was touched, approval status, superseded decisions, and amendments are
      recorded.
- [ ] **No Placeholders**: No TODOs, accidental placeholders, or unresolved drafting markers remain. Clearly
      defined metavariables (such as `<product-name>`) are permitted.
- [ ] **Link Verification**: Apply link verification only when the task creates or modifies links.

## Stop and Failure Conditions
- **Halt Execution immediately when**:
  - Establishing or changing brand identity, product positioning, naming, logos, or a cross-product visual
    language would be required without authorization.
  - The task explicitly requires persistent cross-task reuse of the creative brief and no persistence location is
    supplied or governed by workspace convention.
  - A proposed signature device or other creative decision is classified material and lacks authorization.
  - A conformance dispute remains unresolved after escalation to `task-framing` and requires the user.
  - Satisfying accessibility, platform, behavioural, or technical constraints would require abandoning the thesis
    and no authorized adaptation exists.
- **On Failure**: Preserve partial thesis drafts, briefs, and review findings unless demonstrably invalid. Report
  the exact blocker, whether it is a persistence-location decision, a material creative decision, or a dispute,
  and what remains valid.

## Prohibited Behaviours
- **Adjective-Only Concepts**: Presenting an adjective ("premium," "modern," "clean") as a complete creative
  thesis.
- **Unjustified Genericism**: Using a listed generic pattern without a documented, thesis-specific rationale.
- **Label-Only Rejection**: Rejecting work by citing "bootcamp-tier Tailwind" or an equivalent summary label
  without naming the actual observable pattern and violated criterion.
- **Unbounded Veto**: Rejecting downstream work on unstated taste, or holding it indefinitely through repeated
  subjective rejection.
- **Prescriptive Overreach**: Prescribing exact layout, spacing, colour, or copy details owned by another
  discipline when returning work through the conformance gate.
- **Persistence Assumption**: Assuming, inventing, or writing to a creative-brief storage location that is not
  supplied by the task or governed by workspace convention.
- **Self-Approval**: Treating a model-generated thesis, amendment, or creative rule as approved merely because
  creative direction authored it.
- **Premature Control**: Treating a newly proposed or unresolved creative entry as controlling evidence for
  downstream implementation before it is approved or task-authorized.
- **Retroactive Rationalization**: Rewriting or weakening the creative brief after implementation solely to make
  a divergent execution appear conformant.
- **Silent Brand Invention**: Establishing brand identity, positioning, naming, logos, palettes, typography
  systems, mascots, or illustration systems without authorization.
- **Reference Copying**: Importing another product's identity wholesale instead of deriving a product-specific
  rule.
- **Production Alterations**: Modifying production code or production configuration.
- **Verification Overreach**: Claiming behavioural, accessibility, or performance verification during rendered
  creative review.
- **Completion Concealment**: Declaring downstream work complete while a documented, unresolved conformance
  conflict remains.

## Conflict-Resolution and Evidence Hierarchy
This hierarchy resolves conflicts among workspace instructions and skill documents. It does not override
platform-level, system-level, safety, security, or tool-use requirements governing the agent.
- **Conflict Resolution**:
  1. User's explicit instructions in the current prompt.
  2. Workspace rules (`AGENTS.md` or equivalent).
  3. Governing standard (`.agents/skills/skill-authoring-standard/SKILL.md`).
  4. Individual skill `SKILL.md`.
  5. Global agent guidelines.
- **Creative Evidence Hierarchy (Source of Truth)**:
  1. Current explicit user creative instructions, decisions, and approvals.
  2. User-approved references and anti-references, for the visual, verbal, behavioural, or experiential claims
     they directly establish.
  3. Approved product behaviour, users, information requirements, and product constraints from `product-design`,
     when a product-design specification exists for the task.
  4. Controlling accessibility, platform, behavioural, safety, performance, and technical constraints.
  5. The current approved creative brief, provided it remains consistent with items 1–4.
  6. Approved brand assets, design-system rules, voice guidance, and existing cross-product creative conventions
     that remain applicable.
  7. Independently sourced and decomposed references, bounded per [Bounded Proactive Reference Research](#bounded-proactive-reference-research)
     (always subordinate to user-approved references).
  8. Existing visual, verbal, motion, or interaction patterns that remain applicable.
  9. Skill defaults and model assumptions.

The creative brief governs standing creative direction only while it remains consistent with its controlling
sources and hard constraints (items 1–4). When the brief conflicts with a later explicit user decision, approved
reference, product requirement, or controlling constraint, the brief must be amended or marked superseded — it
does not override the conflict. Independently sourced references are always subordinate to user-approved
references. The thesis adapts to accessibility, platform, behavioural, safety, performance, and technical
constraints — never the reverse.

## Concrete Usage Examples

> [!NOTE]
> All named products, briefs, storage paths, and references not already present in this repository are
> hypothetical. The repository currently contains `skill-authoring-standard`, `task-framing`,
> `software-development`, `testing-and-verification`, `product-design`, `visual-design`, `ux-writing`,
> `creative-direction`, `copywriting`, and `frontend-development`. The example product used below (`FieldNotes`, a
> volunteer ecological
> field-monitoring app) is invented solely for these examples and is unrelated to any product referenced by other
> skill files.

### Example 1: Establishing a Product-Specific Thesis (Preventing a Generic Dashboard)
- **Task**: Establish creative direction for a new volunteer ecological field-monitoring app (hypothetical
  `FieldNotes`).
- **Grounding**: `product-design`'s specification establishes that volunteer observers primarily need to see how
  a monitored place has changed across seasons, and that the product's differentiator is continuity of
  observation over time, not one-off form submission.
- **Initial Status**: The thesis and anti-reference below are newly proposed and do not yet control downstream
  work.
- **Thesis**: "FieldNotes reads as a continuing seasonal record of a place, not a data-entry form. Time and
  continuity across observation seasons are the primary visual subjects; individual entries are secondary."
- **Consequence**: Rejects a default card-grid-of-entries layout as the primary structure; requires a
  time/continuity-oriented visual metaphor instead, handed to `visual-design` as a concept-level requirement, not
  a layout spec, once approved.
- **Anti-Reference**: A generic form-based data-collection template (hypothetical `FormGrid` template) explicitly
  excluded as a structural model.
- **Approval Event**: The hypothetical user explicitly approves the thesis, the anti-reference, and the bounded
  structural principle (time/continuity as the primary visual subject).
- **Persistence Event**: The approved entries are written to an authorized hypothetical `FieldNotes` product
  creative brief, with version and approval status recorded. (Approval and persistence are assumed complete
  before Example 6.)

### Example 2: Decomposing an External Reference Without Copying It
- **Task**: Full-exercise thesis for a public marketing site; supplied evidence insufficient to calibrate
  ambition.
- **Research**: Decompose a named editorial site (hypothetical `Reference Site A`) for its use of asymmetric
  vertical rhythm and restrained motion timing.
- **Output**: "Adopt the principle of asymmetric vertical rhythm to create reading pauses; do not adopt Reference
  Site A's monochrome palette or its specific grid module, which are unrelated to this product's identity."
- **Derived Rule**: A product-specific pacing rule for section transitions, not a visual clone.

### Example 3: Returning a Visual-Design Execution That Violates an Anti-Reference
- **Task**: Conformance review of a submitted `visual-design` specification.
- **Finding**: The specification introduces a repeating card grid with rounded pill-badge status indicators,
  which the approved brief lists as an anti-reference for this product with no documented exception.
- **Gate Action**: Return to `visual-design`, citing: violated element = anti-reference "no pill-badge status
  indicators"; observable conflict = status indicators specified as rounded pill badges in the submitted visual
  specification; required outcome = status must be expressed without the prohibited pattern; responsible
  discipline = `visual-design`. Does not prescribe the replacement treatment.

### Example 4: Accepting an Unconventional Treatment Justified by the Thesis
- **Task**: `visual-design` proposes an asymmetric, non-grid content layout with intentional overflow.
- **Analysis**: The approved thesis calls for "controlled spatial tension reflecting an ongoing, unfinished
  process," and the proposed overflow directly expresses that concept without violating accessibility or
  behavioural requirements.
- **Gate Action**: No conformance violation found; the departure from conventional grid layout is accepted
  because it is justified by the thesis rather than being unconventional for its own sake.

### Example 5: Classifying a Signature Device as Material
- **Task**: `visual-design` proposes replacing standard sidebar navigation with a cinematic, scroll-driven
  spatial journey as a signature device.
- **Analysis**: The device changes navigation behaviour, interaction sequence, and potentially accessibility
  approach (keyboard/screen-reader navigation patterns) and performance budget.
- **Classification**: Material Decision (Blocked). Routed to `task-framing` for authorization rather than
  accepted as a bounded creative choice.

### Example 6: Reusing an Existing Thesis for a Bounded Feature
- **Task**: Add a new "seasonal comparison" feature to `FieldNotes`. `FieldNotes` has an approved, persisted
  creative brief established from the explicitly approved outcome of Example 1.
- **Activation Mode**: Thesis Reuse with Bounded Conformance Review (an established, persisted thesis exists; the
  feature could affect intended impression through its presentation of comparison content).
- **Action**: Load the existing approved brief as controlling evidence; confirm the proposed comparison
  presentation continues the continuity/seasonal-record metaphor; no full exercise re-run.

### Example 7: Reviewing a Rendered Implementation and Routing a Fidelity Loss
- **Task**: Rendered creative review of the shipped `FieldNotes` app.
- **Finding**: The approved `visual-design` specification faithfully expressed the continuity metaphor, but the
  shipped implementation renders all observations as a flat, undifferentiated list, losing the time/continuity
  visual structure specified.
- **Attribution**: Fidelity loss occurred in implementation, not in the brief or the specification. The approved
  brief criterion is left unchanged rather than reinterpreted to fit the shipped result.
- **Routing**: Return to `software-development`/`frontend-development` with the specific divergence from the
  approved specification. `testing-and-verification` separately confirms behavioural correctness of the same
  implementation; the two verdicts are independent.

### Example 8: Request Blocked by Unresolved Brand Identity / Positioning Authority
- **Task**: "Give the product a distinctive creative identity for its public launch."
- **Blocker**: No approved brand name, logo, palette, or product positioning exists yet, and establishing them is
  outside this skill's authority without explicit authorization.
- **Action**: Stop full-exercise work that depends on brand identity. Report: completed grounding analysis from
  `product-design`'s specification; blocker = brand identity and positioning require user/business-owner
  authorization before a creative thesis can be finalized; unblocked partial work (e.g., anti-references, users,
  and problem grounding) is preserved for reuse once authorization is obtained.
