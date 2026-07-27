---
name: ux-writing
description: |
  Translating approved product behaviour, user objectives, interface states, and content requirements into precise, usable interface language.
  Execute when defining interface text, error messages, validation messages based on approved rules, button labels, helper text, or empty-state language.

  Trigger immediately for:
  - Defining button labels, action labels, system error messages, and validation messages based on approved rules.
  - Defining success and status feedback copy, loading and processing language, and destructive warning copy.
  - Establishing consistent naming conventions and terminology.

  DO NOT trigger for:
  - Product workflows, state logic, permissions, business rules, or product acceptance criteria.
  - Visual styling, layout aesthetics, typography, or spacing.
  - Promotional, marketing, sales copy, campaign slogans, or long-form creative copywriting.
  - Production-code implementation.
  - Independent verification of implemented behaviour.
---

# UX Writing

This skill governs the translation of approved product behaviour, user objectives, interface states, and content requirements into precise, usable interface language.

## Purpose and Exclusive Responsibility
- **Goal**: Define accurate, concise, consistent, behaviourally faithful, and actionable interface language within granted authority.
- **Exclusive Responsibility**: Translating approved product behaviour, user objectives, interface states, and content requirements into precise, usable interface language.

## Responsibility Boundaries
- **Primary Responsibility**: Defining navigation labels, page and section headings, field labels, helper text, button/action labels, validation messages based on approved rules, system errors, success/status feedback, empty-state copy, loading/processing copy, permission/access messages, destructive confirmations, undo/recovery copy, notifications, terminology consistency, interface-content hierarchies, and language criteria.
  - May define exact accessible names and alternative text when the underlying control purpose or image meaning is established. It must not invent the functional meaning of controls or imagery.
- **Adjacent Responsibilities**: Consumes product specifications from `product-design` and visual constraints from `visual-design`. Hands implementation-ready strings and their approval status to `software-development`/`frontend-development`, and observable language criteria to `testing-and-verification`.
- **Explicit Exclusions**: Does not own product workflows, state logic, permissions, business rules, visual layout, typography, color, spacing, marketing/campaign copy, brand slogans, production implementation, or independent verification.
  - Approved design references, copy, schemas, contracts, and product specifications may serve as controlling evidence. This skill interprets and applies their language implications. It may define final interface wording within granted authority, but it must not redefine approved product behaviour, visual presentation, architecture, policy, or implementation.
  - Excludes editorial and public-copy decisions, security-policy decisions, licensing and cost decisions, dependency selection, and changes to expected results that are not already authorized.
  - Does not silently alter product behaviour through wording. Does not invent legal, privacy, security, support, refund, payment, or policy promises. Does not change an approved workflow to make wording easier. Does not fabricate system capabilities, timelines, outcomes, guarantees, or causes.
- **Handoff Conditions**: After the interface copy is complete, hand implementation-ready strings and their approval status to `software-development`/`frontend-development` and language verification criteria to `testing-and-verification`. Return unresolved behavioural conflicts to `product-design` and unresolved material policy or wording decisions to `task-framing`.

## Activation and Non-Activation Conditions
- **Activation**: Triggers when translating approved requirements into copy strings, navigation labels, warnings, headings, or error messages.
  - Evaluate proposed wording through state and consequence walkthroughs to confirm language-specification coherence.
- **Non-Activation**: Does not trigger for visual layout design, writing promotional copy, coding, defining workflow rules, or independent verification.

## Required Inputs
- original request or valid task frame;
- approved product workflow or bounded language request;
- actor, objective, state, and intended action;
- content requirements from product design;
- supplied terminology, brand voice, style guide, legal language, or approved copy;
- applicable visual constraints such as available space, hierarchy, component type, and responsive context;
- existing interface language relevant to consistency;
- known localization, accessibility, regulatory, or platform constraints.
- *Note*: Not all inputs must exist; explicitly identify missing information that materially changes meaning, policy, or user action.

## Authority Boundaries
- **Authorized Actions**:
  - Choose wording within approved terminology guidelines and behavioral rules.
  - Select concise action labels matching approved interactions (initiating, confirming, cancelling, undoing, retrying, navigating).
  - Draft validation and error messages using actual system rules.
  - Specify accessible-name and alternative-text requirements when image/control purpose is established.
- **Unauthorized Actions**:
  - Writing production code or production configuration.
  - Modifying product workflow, business rules, or layout constraints.
  - Inventing validation rules or errors that are not established by product behavior.
  - Rewriting approved legal, safety, policy, or regulated language.
  - Establishing new brand terminology or external product names without explicit authorization.

## Ordered Procedure
1. **Confirm Boundary**: Confirm the task boundary and UX-writing authority.
2. **Identify Context**: Identify the actor, objective, product state, intended action, and consequence.
3. **Inspect Inputs**: Inspect controlling behaviour, terminology, supplied copy, and language constraints.
4. **Analyze Current Language**: Analyze current wording where it exists. Inspect only task-relevant surfaces. Distinguish approved terminology, current wording, placeholder/framework defaults, duplicated/inconsistent labels, jargon, ambiguous pronouns, and model assumptions. Identify unclear actions, failure messages lacking recovery instructions, vague confirmations, and overly technical errors.
5. **Establish Hierarchy**: Define the content hierarchy and required message components.
6. **Draft Copy**: Draft language appropriate to the interface surface and state.
7. **Verify Accuracy**: Check behavioural accuracy and consequence transparency.
8. **Check Consistency**: Check terminology consistency and reading burden.
9. **Check Constraints**: Check accessibility, localization, and responsive constraints where applicable.
10. **Define Acceptance Criteria**: Define language acceptance criteria.
11. **Produce Deliverable**: Produce the interface-copy package and downstream handoff.
12. **Record Risks**: Record assumptions, exclusions, and unresolved material decisions.

## UX-Writing Boundary
- Product design defines what happens, when it happens, and what information must be communicated.
- UX writing defines the exact interface language used to communicate those approved requirements.
- Visual design determines presentation and emphasis.
- Copywriting owns promotional, persuasive, campaign, and broader brand-facing copy.
- Software development supplies the governing implementation baseline for implementing supplied text;
  `frontend-development` supplies specialist execution when the string is rendered on a frontend surface, and
  another future specialist may apply in a non-frontend domain.
- Testing-and-verification independently checks rendered wording, state accuracy, and interaction results, when
  independent verification is required.
- UX writing must not silently alter product behaviour through wording.

## Evidence Requirements
- Every proposed string must be traceable to an approved behaviour, state, rule, terminology decision, disclosure requirement, or supplied source.
- Every string package must identify the applicable interface surface, product state or trigger, controlling source, intended user action or understanding, and approval status where relevant.
- Language-specification walkthroughs evaluate whether proposed wording accurately represents the supplied behaviour and consequences; they do not independently verify rendered implementation.
- Examples must demonstrate: an accurate destructive confirmation; validation wording derived from an approved rule; an error message that avoids inventing a cause or recovery path; terminology consistency across a bounded workflow; a policy-dependent request that must stop; a space constraint requiring visual-design or product-design handoff.
- Existing wording is evidence of current language, not automatic authority.
- A concise string is not acceptable when it removes material consequence or recovery information.
- Proposed wording must be distinguishable from supplied, previously approved, legally controlled, and placeholder wording.

## Language Evidence Hierarchy
Use the source with the most direct authority over the wording or meaning at issue. A general user preference does not authorize rewriting binding legal, regulated, contractual, or policy language when the user has not established authority to change it.
1. Current explicit user wording decisions and approvals (control only within the user’s demonstrated authority).
2. Approved legal, policy, safety, privacy, security, payment, or regulated language (approved policy language must not be casually rewritten).
3. Approved product behaviour, state definitions, and content requirements.
4. Approved terminology, naming systems, voice guides, and interface patterns.
5. Supplied screenshots, prototypes, and existing approved copy (screenshots govern wording only for the text visibly approved in them).
6. Current interface wording that remains applicable (current wording is evidence of existing language, not automatic language authority).
7. Authoritative platform and accessibility guidance.
8. Skill defaults and model assumptions.
*Note*: Later explicit user decisions override older generic prose. Brand voice may be applied when supplied, but UX writing must not establish a new brand voice or public positioning.

## Language Decision Classification
- **Observed Language Constraint**: Wording, terminology, meaning, or disclosure imposed by approved policy, product behaviour, legal requirements, established naming, platform conventions, or supplied copy.
- **Bounded Language Decision**: A reversible wording choice whose meaning and consequence are fully established, such as choosing a concise action label from an approved terminology set.
- **Material Language Decision**: A choice that creates or changes public meaning, legal meaning, policy, promise, liability, user consent, pricing, data use, safety guidance, brand positioning, product naming, or externally consequential terminology.

## Current-Language Analysis
Distinguish: supplied approved wording; current interface wording; framework or placeholder wording; inconsistent terminology; wording that misrepresents behaviour; unsupported promises; unexplained jargon; ambiguous references; concealed consequences; missing recovery guidance; model assumptions. Inspect only task-relevant surfaces. Do not expand into unrelated screens merely to standardize terminology without authority.

## Interface-Action Language
Action labels must communicate the action or immediate outcome accurately.
- *Prefer*: “Archive record”, “Save changes”, “Send invitation”, “Try again”.
- *Avoid*: “Yes”, “Submit”, “Continue” (when the consequence is specific and material).
- Labels must not conceal deletion, payment, publication, sharing, or irreversible effects.

## Confirmation and Destructive Language
For consequential actions, define: the action being confirmed; the affected object; the consequence; whether the action is reversible; the primary action; the safe alternative; recovery or undo information where available. Do not invent details (e.g. retention periods or deletion semantics).
- *Avoid vague warnings*: “Are you sure?”, “Proceed?”, “This action may have consequences.”

## Errors and Recovery
Error language should identify: what failed; what was or was not saved; likely user-correctable cause; what the user can do next; whether retrying is safe; whether support or another role is required.
- Do not: expose internal stack traces; invent error causes; blame the user; promise support resolution times.
- Avoid generic errors: do not use “Something went wrong” as the entire message when actionable details exist.

## Validation Messages
Define field-level validation using the actual rule.
- *Prefer*: “Enter an email address in the format name@example.com.” (Do not render as markdown links or mailto URLs).
- *Avoid*: “Invalid input.”, “Incorrect.”, “There was an error.”
- Do not invent validation requirements not established by behavior or constraints.

## Success and Status Feedback
State: what completed; which object was affected; what happens next when material; whether more action is required. Tone must follow the approved context. Do not use celebratory copy automatically, and do not claim success until the product state represents completion.

## Empty States
Define: why the area is empty when known; whether the state is expected, filtered, permission-limited, loading-related, or truly empty; what the user can do next; whether an action should be offered. Do not manufacture activity, urgency, or promotional content.

## Loading and Processing
Distinguish: loading existing information; saving; uploading; sending; processing; synchronizing; waiting for external completion. Do not promise exact durations unless supplied by authoritative behaviour. Avoid endless-progress copy that implies success when the operation is only pending.

## Permissions and Access
Communicate: whether content is restricted or nonexistent; who has access when approved; available actions; request workflows. Do not reveal protected resource existence or sensitive details when rules prohibit it, and do not invent access-escalation workflows.

## Terminology System
Maintain one approved term per concept unless context requires a documented distinction. Terminology consistency does not require identical grammatical form on every surface. Track object/actor names, status names, action verbs, capitalization, abbreviations, and system versus user content. Do not rename established concepts for stylistic variety.

## Voice and Tone
Voice is stable. Tone adapts: neutral/direct for routine actions; calm/specific for errors; explicit/restrained for destructive/financial actions; supportive for sensitive contexts; concise for high-frequency controls; explanatory where misunderstanding carries risk.
- **Prohibitions**:
  - Do not anthropomorphize the system unless an approved product voice explicitly requires it.
  - Do not use forced personality, excessive enthusiasm, jokes, or emotional reassurance in errors or consequential states.
  - Do not use generic instructions such as “friendly and professional” without translating them into observable language rules.
- This approved voice, when a public-facing tone concept exists, originates from `creative-direction`'s intended verbal character or from supplied brand voice guidance; `ux-writing` executes within it but does not establish it.

## Accessibility and Comprehension
UX writing may define: visible control labels, accessible names, alternative text when image/control purpose is known, instructions not depending solely on position/color/iconography, error/field associations. It must not claim: accessibility compliance, screen-reader correctness, correct technical association of labels and errors, sufficient contrast/legibility.

## Localization Readiness
When localization is applicable:
- distinguish fixed text from variables and dynamic content;
- define variable meaning and permitted values;
- support pluralization and grammatical variation rather than assuming English sentence structure;
- avoid constructing translatable sentences from fragments;
- avoid unnecessary idioms, wordplay, culture-specific references, and abbreviations;
- account for text expansion and contraction;
- identify strings whose meaning depends on locale, jurisdiction, currency, date format, number format, measurement system, or formality;
- preserve complete meaning when variables are reordered;
- document terminology that requires an approved locale-specific equivalent.
- Do not translate unless translation is part of the authorized task.
- Do not claim localization readiness merely because strings were extracted into a resource file.

## Space Constraints
Visual space is a constraint, not authority to remove essential meaning. When text does not fit: remove redundancy; use an established shorter term; coordinate hierarchy with visual design; return behavioural conflicts to product design. Do not conceal consequences to fit a component.

## Exact Deliverables
Produce, as applicable (do not describe strings as “approved” unless approval evidence exists. Distinguish: supplied approved strings, newly proposed strings, and strings requiring user or policy approval):
- controlling language evidence;
- current-language findings;
- terminology decisions;
- proposed strings and their approval status;
- string identifiers or surface locations;
- actor, state, trigger, and consequence;
- variables and dynamic-content rules;
- character or layout constraints;
- accessible-name and alternative-text requirements;
- localization notes;
- bounded language decisions;
- unresolved material language decisions;
- language acceptance criteria;
- downstream handoffs;
- assumptions and exclusions.
*Note*: The deliverable does not require a standalone content document for every task. It may be conversational, tabular, annotated, persisted, or supplied as an implementation-ready string package when operationally appropriate.

## UX-Writing Acceptance Criteria
Criteria must be observable and behaviourally accurate:
- **Destructive warning confirmation**: “The destructive confirmation identifies the record affected and states that archived records can be restored.”
- **Associated validation rules**: “The validation message states the actual email-format requirement and remains associated with the relevant field.”
- **Restricted resources disclosure**: “The permission message does not reveal whether a restricted record exists.”
- *Avoid*: “Sounds friendly.”, “Feels clear.”, “Has good UX.”

## Validation Gates
Before claiming the interface-copy package complete:
- [ ] **Context Verified**: Controlling behaviour and terminology are identified.
- [ ] **Wording Context**: Actor, state, action, consequence, and recovery are understood where applicable.
- [ ] **Current vs. Approved Wording**: Current wording is distinguished from approved wording.
- [ ] **Decision Separation**: Bounded and material language decisions are separated.
- [ ] **Behavior Preserved**: Product behaviour has not been changed through wording.
- [ ] **Approved Consequence Disclosure**: Final strings match the approved state and consequence.
- [ ] **Destructive Disclosures**: Destructive actions disclose material consequences.
- [ ] **Recovery Guidance**: Errors provide accurate recovery guidance where available.
- [ ] **No Fabricated System Claims**: No unsupported causes, guarantees, timelines, or capabilities are invented.
- [ ] **Terminology Consistency**: Terminology is consistent.
- [ ] **Clarity Preservation**: Language is concise without removing essential meaning.
- [ ] **Accessibility text requirements**: Accessibility-facing requirements are defined where applicable.
- [ ] **Localization check**: Localization and text expansion are considered where applicable.
- [ ] **No Marketing Drifts**: Final copy does not drift into promotional copy.
- [ ] **Observable Criteria**: Language criteria are observable.
- [ ] **Handoff Clarity**: Behavioral ambiguities go to `product-design`; spatial and hierarchy conflicts go to `visual-design`; policy, legal, naming, consent, pricing, and public-meaning decisions go to `task-framing` and the appropriate authorized owner; implementation-ready strings go to `software-development`/`frontend-development`; observable language criteria go to `testing-and-verification`; promotional or campaign writing goes to `copywriting`.
- [ ] **Exclusions & Assumptions Check**: Assumptions and exclusions are documented.
- [ ] **No Placeholders**: No TODOs, accidental placeholders, or unresolved drafting markers remain. Clearly defined metavariables (such as `<object-name>`) are permitted.
- [ ] **Link Verification**: Apply link verification only when the task creates or modifies links.

## Stop and Failure Conditions
- **Halt Execution immediately when**:
  - Product behaviour or consequence is too ambiguous to word accurately.
  - Legal, privacy, payment, consent, safety, or policy language requires authorization.
  - Approved terminology or naming conflicts cannot be resolved.
  - Available space cannot contain required meaning and resolving it requires a product or visual decision.
  - The requested wording would misrepresent system capabilities or user consequences.
  - The task requires promotional or brand-positioning decisions outside UX-writing authority.
- **On Failure**: Preserve partial copy specifications. Report the exact blocker, missing context, and whether it requires a policy clarification. Do not stop for minor reversible details.

## Prohibited Behaviours
- **Behavior Changes**: Changing product behaviour through wording.
- **Invented Promises**: Inventing policy, legal meaning, consent, guarantees, support timelines, or recovery promises.
- **Consequence Masking**: Using vague labels that hide consequential actions.
- **Technical Exposure**: Exposing internal technical details to users.
- **User Blame**: Blaming users.
- **Humor in Errors**: Forced humour or personality in errors.
- **Marketing in Controls**: Marketing language in routine interface controls.
- **Style Inconsistencies**: Inconsistent terminology for stylistic variety.
- **Meaning Stripping**: Deleting essential meaning to satisfy arbitrary character limits.
- **Production Modifications**: Modifying production code or production configuration.
- **Accessibility Claims**: Claiming accessibility or usability without appropriate evidence.
- **Regulated Wording Overrides**: Rewriting approved regulated language without authority.
- **Scope expansion**: Expanding the task into unrelated interface surfaces for terminology or tone consistency without authority.
- **Proposed copy presentation**: Presenting proposed copy as approved.
- **Invented variables**: Inventing variables, dynamic values, record names, or personalization data not supplied by the product specification.
- **Styling instructions**: Writing visual styling directions.
- **Expected state alterations**: Altering expected system states to support preferred wording.

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
  1. Current explicit user wording decisions and approvals (control only within the user’s demonstrated authority).
  2. Approved legal, policy, safety, privacy, security, payment, or regulated language (approved policy language must not be casually rewritten).
  3. Approved product behaviour, state definitions, and content requirements.
  4. Approved terminology, naming systems, voice guides, and interface patterns.
  5. Supplied screenshots, prototypes, and existing approved copy (screenshots govern wording only for the text visibly approved in them).
  6. Current interface wording that remains applicable (current wording is evidence of existing language, not automatic language authority).
  7. Authoritative platform and accessibility guidance.
  8. Skill defaults and model assumptions.

## Concrete Usage Examples

> [!NOTE]
> Named execution skills, files, paths, products, components, terminology systems, policies, or commands in these examples are hypothetical unless explicitly identified as existing.

### Example 1: Destructive Confirmation Language
- **Task**: Replace vague destructive confirmation modal wording.
- **Prerequisites**: Approved product behaviour confirms that deletion is permanent, identifies that only the record is deleted, and confirms that no recovery or undo exists.
- **Wording Specification**:
  - Title: “Delete record?”
  - Body: “This permanently deletes the record. This action cannot be undone.”
  - Primary action: “Delete record”
  - Safe alternative: “Keep record”
  - Visual handoff: Specify strings. Do not prescribe "warning styling" or visual treatments; route visual treatment to `visual-design`.

### Example 2: Validation Wording from Rules
- **Task**: Write field validation message for a password input field.
- **Controlling Rule**: The product rules specify that passwords must contain at least 12 characters and at least one number.
- **Specification**:
  - Validation text: "Password must contain at least 12 characters and at least one number."
  - Avoids vague: "Invalid input." or "Error."

### Example 3: Replace a technical save-failure message shown to the user
- **Task**: Replace a technical save-failure message shown to the user.
- **Controlling evidence**: The request failed, the record was not saved, and retry safety is unknown.
- **Specification**:
  - Error text: “We couldn’t save the record. Your changes have not been saved.”
  - Avoids exposing internal port, database naming (PostgreSQL), stack traces, or inventing causes ("temporarily unavailable", "wait a moment") or retry safety.

### Example 4: Terminology Consistency Check
- **Task**: Resolve inconsistent labels in a record workflow.
- **Analysis**: The project's approved terminology system mandates `Record` as the single term. Consistency does not require identical grammatical form on every surface.
- **Specification**:
  - Navigation label: “Records”
  - Page heading: “Records”
  - Action label: “Archive record”
  - Confirmation title: “Archive record?”
  - Do not rename a modal to an action phrase unless the modal's actual purpose supports it.

### Example 5: Writing Request Blocked by Unresolved Policy
- **Task**: Write copy for a privacy policy consent checkbox.
- **Blocker**: The exact user data sharing policies with third-party tracking services are unresolved and lack legal approval.
- **Action**: Stop drafting. Return the unresolved data-sharing meaning to `task-framing` so the task can identify and obtain a decision from the authorized product, privacy, policy, or legal owner. UX writing must not draft consent language until the underlying disclosure and authorized source are established.

### Example 6: Text Size Conflict Handled
- **Task**: Fit "Confirm record archival" button label on a mobile viewport.
- **Visual constraint**: Visual layout indicates button text must be under 12 characters.
- **Action**: First attempt an approved shorter term. If no accurate term fits, return the spatial conflict to `visual-design`. Return to `product-design` only if resolving it requires changing action hierarchy, disclosure placement, or interaction behaviour. Do not shorten a consequential label until it becomes ambiguous.
