---
name: copywriting
description: |
  Own promotional, persuasive, campaign, editorial, and public-facing brand-voice language, translating approved
  creative direction and supplied brand voice into implementation-ready public-facing copy.
  Execute when writing headlines, hero statements, page-level narrative, campaign messaging, editorial
  introductions/transitions, persuasive calls to action, or about-page/positioning-supporting copy.

  Trigger immediately for:
  - Public-facing marketing, campaign, launch, or editorial copy, including headlines, hero statements, and
    page-level narrative or storytelling.
  - Persuasive calls to action and campaign messaging distinct from interface utility copy.
  - About-page, positioning-supporting, or brand-storytelling copy executed within approved positioning.

  DO NOT trigger for:
  - Interface utility copy, validation messages, system errors, or action labels for in-product workflow steps
    (owned by `ux-writing`).
  - Product behaviour, workflows, states, or business rules (owned by `product-design`).
  - Establishing the creative thesis, brand voice, or verbal character itself (owned by `creative-direction`) —
    copywriting executes within an approved thesis rather than originating one.
  - Establishing product naming, brand positioning, legal meaning, or material public claims without
    authorization.
  - Production implementation or independent verification of implemented copy.
---

# Copywriting

This skill governs the translation of approved creative direction, brand voice, and product grounding into
promotional, persuasive, campaign, editorial, and public-facing brand-voice language.

## Purpose and Exclusive Responsibility
- **Goal**: Produce accurate, on-voice, persuasive, and implementation-ready public-facing copy within granted
  authority, without inventing brand meaning, product claims, or evidence.
- **Exclusive Responsibility**: Own promotional, persuasive, campaign, editorial, and public-facing brand-voice
  language — including headlines, hero statements, page-level narrative, product and brand storytelling, campaign
  messaging, editorial introductions and transitions, persuasive calls to action, and about-page and
  positioning-supporting copy — while consuming approved creative direction and avoiding overreach into
  `ux-writing`, product behaviour, naming, positioning, or material brand authority.

## Responsibility Boundaries
- **Primary Responsibility**: Headlines and hero statements; page-level narrative; product/brand storytelling;
  campaign messaging; editorial introductions and transitions; persuasive calls to action; about-page and
  positioning-supporting copy; public-facing tone execution; distinguishing approved copy from newly proposed
  copy; defining observable copy acceptance criteria.
- **Adjacent Responsibilities**: Consumes the approved `creative-direction` thesis and intended verbal character as
  primary grounding when one exists. When no creative-direction thesis exists and the task is bounded or minor —
  not materially establishing or changing brand voice — grounds directly in the task frame's stated audience,
  communication objective, and content requirements instead: direct task-frame grounding, the same approach
  `creative-direction` itself uses when no product-design specification exists. Consumes confirmed
  `product-design` behaviour and facts as the controlling source for any factual claim. Consumes supplied brand
  voice, terminology, legal-approved claims, and existing approved copy. Coordinates length and hierarchy with
  `visual-design`'s space constraints without letting fit override essential meaning. Hands implementation-ready
  copy and its approval status to `software-development`/`frontend-development`, and observable copy acceptance
  criteria to `testing-and-verification`. When an approved creative-direction thesis exists and `creative-direction` is
  activated for conformance review, submits its output to that bounded creative-conformance gate; bounded,
  task-frame-grounded copy with no thesis is not submitted to a review that does not exist.
- **Explicit Exclusions**: Does not own interface utility copy, validation, errors, system feedback, or in-product
  action labels — those remain `ux-writing`'s domain regardless of tone. Does not define product behaviour or
  workflows. Does not establish product naming, brand positioning, legal meaning, or material public claims
  without authorization. Does not silently create unsupported promises, guarantees, evidence, statistics,
  testimonials, or customer claims. Does not modify production code.
  - Approved creative-direction theses, product-design specifications, brand voice guides, and legal-approved
    claims are controlling evidence this skill executes through — it does not redefine them.
- **Handoff Conditions**: After copy is drafted, hand implementation-ready strings and their approval status to
  `software-development`/`frontend-development`, and observable copy acceptance criteria to
  `testing-and-verification`. Return unresolved
  product-behaviour or factual-accuracy questions to `product-design`. Return unresolved brand-voice, positioning,
  naming, or claims-authorization decisions to `task-framing`. Route to `creative-direction` when a task requires
  establishing or materially changing brand voice or verbal character rather than executing within it.

## Activation and Non-Activation Conditions
- **Activation**: Triggers when translating an approved creative thesis, supplied brand voice, or a bounded task
  frame into promotional, persuasive, campaign, editorial, or brand-narrative copy.
  - For campaign or brand-narrative work with an approved creative-direction thesis, load it as controlling
    evidence for verbal character, tone, and permitted/prohibited devices.
  - For bounded or minor public-facing copy with no approved thesis and no material brand-voice question at
    stake, ground directly in the task frame's audience, communication objective, and content requirements.
- **Non-Activation**: Does not trigger for interface utility copy, product workflow definition, visual layout,
  coding, or independent verification. Does not trigger to originate a creative thesis, brand voice, or verbal
  character — that activation belongs to `creative-direction`. A task that would require establishing or
  materially changing brand voice or verbal character without an approved thesis is not resolved by this skill
  unilaterally; it is routed to `creative-direction` via `task-framing`.

## Required Inputs
- Original request or valid task frame.
- Approved `creative-direction` thesis, intended impression, and verbal-character concept, when one exists;
  otherwise the task frame's stated audience, communication objective, and content requirements.
- Approved `product-design` specification or confirmed product facts, when a claim depends on actual product
  behaviour.
- Supplied brand voice, terminology, style guide, legal-approved claims, and existing approved copy.
- Supplied evidence for any factual, comparative, statistical, or testimonial claim.
- Applicable `visual-design` space, hierarchy, and layout constraints.
- Known legal, regulatory, or compliance constraints on public claims.
- *Note*: Not all inputs must exist; explicitly identify missing grounding that prevents an accurate or
  authorized draft.

## Authority Boundaries
- **Authorized Actions**:
  - Draft headlines, hero statements, page-level narrative, storytelling, campaign messaging, editorial
    introductions and transitions, and persuasive calls to action within approved voice and grounding.
  - Draft about-page and positioning-supporting narrative that executes approved positioning without originating
    it.
  - Propose multiple candidate copy variants for user or creative-direction selection.
  - Execute within supplied brand-voice and terminology constraints, preserving exact controlled terms where
    required.
- **Unauthorized Actions**:
  - Writing production code or production configuration.
  - Authoring interface utility copy, validation messages, system errors, or in-product action labels
    (`ux-writing`'s domain).
  - Modifying or inventing product workflow, behaviour, or business rules.
  - Establishing or materially changing brand voice, verbal character, product naming, or brand positioning
    without explicit authorization.
  - Inventing unsupported promises, guarantees, statistics, testimonials, social proof, or customer claims not
    backed by supplied evidence.
  - Rewriting approved legal, regulatory, or compliance-reviewed claim language without authority.

## Ordered Procedure
1. **Confirm Boundary**: Confirm the task boundary and copywriting authority, including whether the task requires
   establishing or changing brand voice (out of bounds) versus executing within an existing or task-frame-grounded
   voice (in bounds).
2. **Identify Context**: Identify the audience, communication objective, surface/campaign type, and intended
   action.
3. **Inspect Grounding**: Inspect the approved creative-direction thesis and verbal character when one exists, the
   task frame's audience/objective/content requirements otherwise, confirmed product-design facts relevant to any
   claim, and supplied brand voice, terminology, and existing approved copy.
4. **Classify Copy Type**: Distinguish promotional/persuasive/editorial copy from interface utility copy using the
   [CTA Ownership Boundary](#cta-ownership-boundary).
5. **Draft Copy**: Draft candidate copy honoring the approved voice or grounded tone, accurate to confirmed product
   behaviour, without inventing claims.
6. **Verify Claims Integrity**: Confirm every factual, comparative, or proof claim traces to supplied evidence per
   [Claims and Evidence Integrity](#claims-and-evidence-integrity); flag unsupported claims rather than invent
   support.
7. **Self-Check Conformance (When a Thesis Exists)**: When an approved creative-direction thesis exists, check
   drafted copy against it and its anti-references before handoff; `creative-direction` still runs its own
   conformance gate independently when activated for review. When no thesis exists, skip this step — there is no
   brief to conform against.
8. **Check Space Constraints**: Coordinate headline/CTA length and hierarchy with `visual-design`'s constraints.
9. **Define Acceptance Criteria**: Define observable copy acceptance criteria.
10. **Produce Deliverable**: Produce the copy package, distinguishing approved copy from newly proposed copy.
11. **Record Risks**: Record assumptions, exclusions, and unresolved material decisions.

## Copywriting Boundary
- `creative-direction` establishes the expressive thesis and intended verbal character; `copywriting` executes
  exact public-facing wording within it.
- `product-design` defines what the product actually does; `copywriting` may only make claims that trace to it.
- `ux-writing` owns interface utility copy for in-product workflow steps; `copywriting` owns promotional and
  persuasive language, including CTAs that sit in a marketing/editorial context rather than inside a workflow.
- `visual-design` determines presentation, space, and hierarchy; `copywriting` fits meaning within those
  constraints without silently cutting essential claims or CTAs.
- `software-development`/`frontend-development` implements supplied copy. `testing-and-verification`
  independently verifies rendered copy against the approved package.
- `copywriting` must not silently establish brand voice, positioning, or product naming.
- `creative-direction`'s conformance gate applies only when an approved thesis exists and creative direction is
  activated for review; bounded, task-frame-grounded copy is not held to a brief that does not exist.

## CTA Ownership Boundary
A call to action's owner follows its surrounding context and behavioural consequence, not its verb alone:
- **Copywriting** owns persuasive narrative and CTAs that navigate to informational or promotional content
  without themselves beginning a consequential product workflow (for example, a hero section's "See how it
  works" linking to an explainer section).
- **UX writing** owns the exact label of a control that immediately initiates or advances a real,
  consequence-bearing workflow — starting a signup, checkout, account creation, submission, or a
  download/action with material consequences — because behavioural accuracy and consequence disclosure control
  that wording, not persuasive framing.
- **Dual-purpose controls**: A hero button can be persuasive while also immediately starting such a workflow (for
  example, "Start your free trial," which both persuades and creates an account). In this case, `ux-writing` owns
  the exact action label and must confirm its behavioural and consequence accuracy; `copywriting` may propose
  candidate wording for it but does not finalize it, and continues to own the surrounding persuasive lead-in copy.
- On a mixed page (an expressive surface with one bounded interactive element), the persuasive lead-in copy is
  `copywriting`'s; once the element's own consequence-bearing workflow behaviour starts (submit, validate,
  confirm), the exact control label is `ux-writing`'s. Do not let either discipline silently absorb the other's
  half by proximity alone. Unresolved ownership disputes route to `task-framing`, with confirmed product
  behaviour controlling the action's meaning.

## Claims and Evidence Integrity
Every factual, comparative, statistical, testimonial, award, certification, adoption, performance, or
social-proof claim in copywriting output must trace to confirmed product-design behaviour or supplied evidence
(data, quotes, case studies, certifications, an authoritative source) — regardless of how persuasive or
restrained the surrounding voice is.
- **Authorization is not evidence**: Explicit user authorization can approve wording, publication, or acceptance
  of a disclosed risk. It cannot verify a factual, comparative, statistical, testimonial, or social-proof claim.
  A user-supplied claim with no independent supporting evidence must be identified as user-supplied and
  unverified, classified as a Material Copy Decision, and never described as evidence-backed.
- Do not invent statistics, percentages, customer counts, testimonials, awards, comparisons, or guarantees.
- Do not imply a capability, outcome, or timeline the product-design specification does not confirm.
- Do not rewrite approved legal, regulatory, or compliance-reviewed claim language without authority.
- When a persuasive claim would strengthen the copy but no supporting evidence exists, state the gap and propose
  restrained alternatives that do not depend on the missing evidence, rather than drafting the unsupported
  version. Block the specific unsupported claim, not the surrounding, unaffected copy.

## Positioning and Brand-Voice Boundary
`copywriting` executes approved positioning and brand voice into public-facing narrative. It does not originate,
redefine, or materially extend positioning, brand identity, or verbal character.
- When approved positioning or an approved creative-direction thesis exists, execute within it.
- When no approved positioning or thesis exists and the task is bounded/minor (a single restrained piece of copy
  with no lasting brand-voice consequence), draft directly from the task frame's audience and objective, and mark
  the tone as task-scoped rather than an established brand voice.
- When the task requires establishing or materially changing positioning or brand voice, that is a material
  decision outside this skill's authority — return it to `creative-direction` via `task-framing` rather than
  drafting a de facto positioning statement.

## Campaign Variant Handling
Proposing multiple candidate headlines, CTAs, or narrative openings for user or creative-direction selection does
not automatically make every candidate a Bounded Copy Decision — candidate status describes approval workflow,
not decision materiality.
- A candidate is bounded only when it remains inside approved positioning and verbal character, introduces no new
  factual or public claim, and does not establish a new audience, product name, promise, or brand direction.
- A proposed but unselected candidate that crosses any of those boundaries is still a Material Copy Decision and
  must be flagged as such even though it has not been selected.
- Do not present an unselected variant as approved copy, and do not silently narrow to a single option when the
  task calls for candidates.

## Copy Decision Classification
- **Observed Copy Constraint**: Wording, claim, or tone requirement imposed by an approved creative-direction
  thesis, approved product-design behaviour, supplied brand voice/terminology, or approved legal/regulated
  language.
- **Bounded Copy Decision**: A reversible wording, structure, or variant choice that remains within approved voice
  and grounding, makes no new claim, and does not establish or change positioning, naming, or brand voice.
- **Material Copy Decision**: A choice that establishes or materially changes brand voice, verbal character,
  positioning, product naming; introduces a public/legal claim not already authorized; or presents a
  user-supplied factual, comparative, statistical, or testimonial claim with no independent supporting evidence
  as though it were verified.

Material copy decisions require authorization through `task-framing`. This skill must not apply a material
decision merely because it drafted or proposed it.

## Evidence Requirements
- **Actionability**: Every procedural step must use imperative language and identify a concrete action plus its
  expected outcome or validation evidence.
- **Demonstrated Execution**: Include concrete examples demonstrating: a campaign headline executed from both an
  approved creative-direction thesis and confirmed product-design facts; a restrained editorial introduction that
  does not force marketing language onto a non-promotional surface; a dual-purpose CTA correctly split so
  `ux-writing` owns the exact action label while copywriting owns the persuasive lead-in; an about-page draft
  executed within approved positioning; an unsupported claim blocked without halting the rest of the task; a set
  of campaign headline variants checked individually for materiality rather than assumed bounded merely because
  unselected.
- **Grounding Requirement**: Every copy claim must trace to the approved creative-direction thesis, confirmed
  product-design behaviour, supplied brand voice/evidence, or the task frame's stated audience and objective when
  no thesis exists. Copy invented independently of all available grounding is not implementation-ready.

## Exact Deliverables
A copywriting package containing, as applicable (conversational, tabular, annotated, or persisted when
operationally valuable):
- surface/campaign context, audience, and communication objective;
- controlling grounding (creative-direction thesis or task frame elements used instead);
- proposed copy, marked approved or newly proposed;
- claims and their evidence basis, distinguishing verified claims from user-supplied unverified claims;
- CTA classification per the CTA Ownership Boundary;
- bounded copy decisions and their authority basis;
- unresolved material copy decisions;
- copy acceptance criteria;
- downstream handoffs;
- assumptions and exclusions.

## Copywriting Acceptance Criteria
Criteria must be observable and traceable:
- **Claim traceability**: "Every statistic or customer claim in the hero section cites its supplying evidence."
- **Voice conformance**: "The campaign headline matches the approved creative-direction verbal character and
  contains no listed anti-reference pattern."
- **CTA boundary**: "The persuasive headline and lead-in are distinct from the signup form's own submit-button
  label, which `ux-writing` owns and confirms for consequence accuracy even though the button is persuasively
  framed."
- *Avoid*: "Sounds punchy.", "Feels on-brand.", "Reads well."

## Validation Gates
Before claiming the copy package complete:
- [ ] **Grounding Check**: Copy traces to an approved creative-direction thesis or, absent one, to the task
      frame's audience and communication objective — not an invented voice.
- [ ] **Claims Integrity**: Every factual, comparative, statistical, or testimonial claim traces to supplied
      evidence or confirmed product-design behaviour, not merely user authorization; any user-supplied unverified
      claim is flagged as such rather than presented as evidence-backed.
- [ ] **CTA Boundary Check**: Persuasive CTAs are distinguished from adjacent in-workflow action labels per the
      CTA Ownership Boundary, including dual-purpose controls where `ux-writing` owns the exact action label.
- [ ] **Conformance Applicability**: The creative-conformance self-check was applied only when an approved
      creative-direction thesis exists; bounded, task-frame-grounded copy was not held to a nonexistent brief.
- [ ] **Variant Materiality Check**: Candidate copy variants are checked individually against positioning, claims,
      audience, and brand-voice boundaries; unselected status alone did not exempt a variant from material
      classification.
- [ ] **Positioning Boundary**: No positioning, brand voice, or product naming was originated or materially
      changed without authorization.
- [ ] **Decision Separation**: Bounded and material copy decisions are separated; material decisions are not
      disguised as bounded ones.
- [ ] **Approval-Status Integrity**: Proposed copy is distinguishable from approved copy at every point in the
      deliverable.
- [ ] **No Utility-Copy Overreach**: No interface utility copy, validation, error, or system-feedback string was
      authored in place of `ux-writing`.
- [ ] **Restraint Check**: Marketing language was not forced onto a surface the grounding calls for restraint on.
- [ ] **Space Constraint Check**: Copy fits supplied visual constraints without silently cutting a claim or CTA.
- [ ] **Handoff Clarity**: Implementation-ready copy goes to `software-development`/`frontend-development`;
      acceptance criteria go to `testing-and-verification`; unresolved product-fact questions go to
      `product-design`; unresolved voice/positioning/claims-authorization decisions go to `task-framing`.
- [ ] **Exclusions & Assumptions Check**: Assumptions and exclusions are documented.
- [ ] **No Placeholders**: No TODOs, accidental placeholders, or unresolved drafting markers remain. Clearly
      defined metavariables (such as `<product-name>`) are permitted.
- [ ] **Link Verification**: Apply link verification only when the task creates or modifies links.

## Stop and Failure Conditions
- **Halt Execution immediately when**:
  - An unsupported claim is essential to the requested deliverable and no authorized, accurate alternative can
    satisfy it — otherwise, block only that specific claim and continue with unaffected copy and evidence-safe
    alternatives.
  - The task requires establishing or materially changing brand voice, verbal character, or positioning and no
    approved creative-direction thesis or authorization exists.
  - Legal, regulatory, or compliance-reviewed claim language requires rewriting without authority to do so.
  - CTA ownership on a specific surface remains genuinely ambiguous after applying the CTA Ownership Boundary,
    including its dual-purpose-control case.
- **On Failure**: Preserve partial copy drafts, variants, and unaffected completed copy unless demonstrably
  invalid. Report the exact blocker, whether it is a missing-evidence gap scoped to one claim, a positioning/voice
  authorization gap, or a claims-authorization gap, and what remains valid.

## Prohibited Behaviours
- **Fabricated Claims**: Inventing statistics, customer counts, testimonials, awards, comparisons, or guarantees
  not backed by supplied evidence.
- **Positioning Overreach**: Originating or materially changing brand positioning, identity, or product naming
  without authorization.
- **Utility-Copy Overreach**: Authoring interface utility copy, validation, error, or system-feedback strings
  instead of handing them to `ux-writing`.
- **Voice Invention**: Establishing a brand voice or verbal character rather than executing an approved one or a
  task-scoped restrained default.
- **Unjustified Marketing Creep**: Forcing promotional language onto a surface whose grounding calls for
  restraint.
- **Proposed-as-Approved Presentation**: Presenting newly proposed or unselected variant copy as approved.
- **Production Alterations**: Modifying production code or production configuration.
- **Regulated Wording Overrides**: Rewriting approved legal or regulated claim language without authority.

## Conflict-Resolution and Evidence Hierarchy
This hierarchy resolves conflicts among workspace instructions and skill documents. It does not override
platform-level, system-level, safety, security, or tool-use requirements governing the agent.
- **Conflict Resolution**:
  1. User's explicit instructions in the current prompt.
  2. Workspace rules (`AGENTS.md` or equivalent).
  3. Governing standard (`.agents/skills/skill-authoring-standard/SKILL.md`).
  4. Individual skill `SKILL.md`.
  5. Global agent guidelines.
- **Copy Evidence Hierarchy (Source of Truth)**:
  The applicable authority depends on the specific issue at stake — the source with the most direct authority
  over that issue controls, not a single fixed ranking applied identically to every claim type.
  1. Current explicit user copy decisions and approvals, controlling only within the user's demonstrated
     authority over that specific issue (a user may approve wording or accept a disclosed risk without thereby
     verifying a factual claim).
  2. Approved legal, regulatory, or compliance-reviewed claim language, which governs regulated meaning and must
     not be casually rewritten.
  3. Confirmed product-design behaviour and supplied evidence, which govern the factual accuracy of any claim —
     no creative thesis, brand voice, or space constraint can override contrary factual evidence.
  4. Approved creative-direction thesis, intended impression, and verbal-character concept, which govern
     expressive voice, tone, and anti-references, not factual accuracy.
  5. Approved positioning and brand guidance, which govern public meaning and terminology.
  6. Supplied existing approved copy and terminology, for consistency.
  7. Applicable visual-design space, hierarchy, and layout constraints, which govern fit and presentation but
     cannot remove or alter essential meaning or a required claim.
  8. The task frame's stated audience, communication objective, and content requirements, which govern intended
     outcome and control grounding when no creative-direction thesis exists.
  9. Skill defaults and model assumptions.

## Concrete Usage Examples

> [!NOTE]
> Named execution skills, files, paths, products, campaigns, or brands in these examples are hypothetical unless
> explicitly identified as an installed skill. The repository currently contains `skill-authoring-standard`,
> `task-framing`, `product-design`, `creative-direction`, `visual-design`, `ux-writing`, `software-development`,
> `testing-and-verification`, `copywriting`, and `frontend-development`.

### Example 1: Campaign Headline Executed from Both an Approved Thesis and Confirmed Product Facts
- **Task**: Write the launch-campaign headline and hero statement for a hypothetical volunteer ecological
  field-monitoring app (`FieldNotes`).
- **Verbal-Character Grounding**: `creative-direction`'s approved thesis establishes that `FieldNotes` reads as a
  continuing seasonal record of a place, not a data-entry form, with time and continuity as the primary subject.
- **Factual Grounding**: `product-design`'s approved specification confirms that prior seasonal observations
  remain visible alongside new entries for the same location — the factual basis for any continuity claim,
  distinct from the thesis's expressive framing of that same behaviour.
- **Draft**:
  - Headline: "Every season, the same place, one continuing record."
  - Hero statement: "FieldNotes keeps this season's observations connected to every one you've logged before at
    the same location."
- **Conformance Self-Check**: An approved thesis exists, so the draft is checked against it — avoids the approved
  anti-reference (a generic form-based data-collection template) and avoids adjective-only claims ("premium,"
  "seamless").
- **Approval Status**: Newly proposed, pending `creative-direction`'s conformance gate and user approval.

### Example 2: Restrained Editorial Introduction (No Forced Marketing Language)
- **Task**: Write the introduction for a long-form public article about seasonal wetland surveying methods, on a
  page with no accounts or transactional behaviour.
- **Grounding**: Direct task-frame grounding — no creative-direction thesis exists for this article, and the
  stated communication objective is reader comprehension, not conversion.
- **Draft**: "Wetland surveys change with the season, and the methods volunteers use change with them. This
  article walks through what to record in early spring, what shifts by midsummer, and why the difference matters
  for the data that follows."
- **Restraint Check**: No CTA, superlative, or promotional framing was added merely because copywriting activated;
  the introduction states subject and relevance only.

### Example 3: CTA Ownership Split on a Mixed Landing Page (Dual-Purpose Control)
- **Task**: Write copy for a product-announcement launch page whose only interactive element is an email-signup
  form beginning a real subscription workflow.
- **Product/Operational Grounding**: The approved launch plan and product-design specification confirm a phased
  regional rollout, an email notification when a submitted region becomes available, and that the signup creates
  only an email subscription record — no account or payment is involved.
- **Analysis**: The page's dominant purpose is persuasive/expressive; the signup form is one bounded interactive
  element with its own workflow (submit, validation error, success, duplicate/failure). The form's submit button
  is a dual-purpose control: persuasive in framing, but it immediately starts a consequence-bearing workflow
  (creating a subscription record).
- **Copywriting Output** (persuasive lead-in, not the control label):
  - Headline: "Be the first to know when FieldNotes opens for your region."
  - Lead-in: "We're rolling out to volunteer programs one region at a time. Leave your email and we'll tell you
    the moment yours is live."
- **Dual-Purpose Control**: Copywriting may propose a candidate label for the submit button (for example, "Notify
  me") but does not finalize it. `ux-writing` owns the exact action label and confirms it accurately discloses the
  confirmed consequence (a subscription is created; no payment or account is involved) before it is
  implementation-ready.
- **Ownership Boundary**: Validation messages, duplicate-email handling, and success/failure copy for the form
  remain `ux-writing`'s once the workflow begins; the surrounding persuasive headline and lead-in remain
  copywriting's.

### Example 4: About-Page Copy Executed Within Approved Positioning
- **Task**: Draft About-page narrative for `FieldNotes`.
- **Grounding**: An approved positioning statement exists: "FieldNotes supports volunteer ecological monitoring
  programs, not individual citizen-science hobbyists." No other positioning, origin, or philosophy claim is
  supplied.
- **Draft**: "FieldNotes is built for volunteer ecological monitoring programs, not individual hobbyists."
- **Boundary Held**: The draft executes only the supplied positioning and adds no unsupported claim about product
  origin, audience relationship, or philosophy. Copywriting does not decide whether `FieldNotes` should also
  target individual hobbyist users — extending the audience would be a material positioning change requiring
  authorization, not a copywriting decision.

### Example 5: Claim Blocked by Missing Supporting Evidence (Not the Whole Task)
- **Task**: Write full launch-campaign copy including a subheadline claiming "Used by over 500 monitoring programs
  worldwide."
- **Blocker**: No supplied evidence confirms this figure, and product-design has not confirmed adoption data of
  this kind. The user offering to approve the claim does not verify it — user authorization can approve wording,
  not manufacture proof of an adoption figure.
- **Action**: Block only the unsupported subheadline claim; it is flagged user-supplied and unverified rather than
  evidence-backed, and classified as a Material Copy Decision pending actual supporting evidence. Continue
  drafting the rest of the campaign copy (headline, hero statement, CTA) using confirmed grounding. Propose a
  restrained subheadline alternative scoped to confirmed product capability instead of the unverified adoption
  figure.

### Example 6: Campaign Headline Variants Checked Individually for Materiality
- **Task**: Propose candidate hero headlines for a seasonal-campaign relaunch.
- **Candidates** (each marked "newly proposed, unselected"):
  1. "Every season, the same place, one continuing record." — Bounded: stays within the approved thesis,
     introduces no new claim.
  2. "This season's notes, connected to every one before it." — Bounded: same thesis element, no new claim.
  3. "FieldNotes for every nature lover." — Material: shifts the approved positioning from volunteer monitoring
     programs toward individual hobbyists and a broad consumer audience, and is flagged as such rather than
     proposed as an ordinary bounded variant, pending positioning authorization.
- **Analysis**: Unselected status alone did not make candidate 3 bounded; it is checked against the claims and
  positioning boundaries individually, the same as any other proposed copy. Candidate 3 is material because it
  changes the approved audience, not because it fabricates a claim.
