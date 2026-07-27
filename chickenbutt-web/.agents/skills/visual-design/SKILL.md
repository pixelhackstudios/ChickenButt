---
name: visual-design
description: |
  Translating approved requirements — product behaviour and information hierarchy when applicable, an approved
  creative-direction thesis when one exists, or a bounded task-frame request otherwise — plus brand direction and
  reference assets, into coherent visual specifications and visual artifacts.
  Execute when translating product requirements into visual hierarchy, layouts, spacing, color scales, or typography styles.

  Trigger immediately for:
  - Defining visual layouts, spacing guides, grid alignments, and density scales.
  - Designing color usage, component surfaces, and typography scales based on brand rules.
  - Creating visual specifications for product states or responsive viewport adaptations.

  DO NOT trigger for:
  - Product workflows, business rules, permissions, state transitions, or product acceptance criteria.
  - Final interface wording, labels, error messages, or copywriting.
  - Production-code implementation.
  - Independent verification of implemented behaviour.
---

# Visual Design

This skill governs the translation of approved requirements — product behaviour and information hierarchy when
applicable, an approved creative-direction thesis when one exists, or a bounded task-frame request otherwise —
plus brand direction and reference assets, into coherent visual specifications and visual artifacts.

## Purpose and Exclusive Responsibility
- **Goal**: Define coherent visual layouts, hierarchy, spacing, typography, and color systems within granted authority to express approved requirements — product priorities when applicable, an approved creative thesis when one exists, or a bounded task-frame request otherwise.
- **Exclusive Responsibility**: Translating approved requirements — product behaviour and information hierarchy when applicable, an approved creative-direction thesis when one exists, or a bounded task-frame request otherwise — plus brand direction and reference assets, into coherent visual specifications and visual artifacts.

## Responsibility Boundaries
- **Primary Responsibility**: Defining visual hierarchy, composition/spatial organization, layout systems, typography/color application, spacing/density, component appearance, shapes/elevation, imagery treatment, responsive adaptations, state styling, and visual acceptance criteria.
- **Adjacent Responsibilities**: Consumes product specifications from `product-design` when applicable, an approved creative-direction thesis when one exists, or a bounded task-frame request otherwise. Hands visual specifications to `software-development`/`frontend-development`, and observable visual criteria to `testing-and-verification` when independent verification is required.
- **Explicit Exclusions**: Does not own product workflows, business rules, permissions, state transitions, product acceptance criteria, final interface copy/labels, production code implementation, or independent verification.
  - Approved design references, copy, schemas, contracts, and product specifications may serve as controlling evidence. This skill interprets and applies their visual implications but does not redefine approved product behaviour, final wording, architecture, or implementation.
  - Excludes editorial and public-copy decisions, security-policy decisions, licensing and cost decisions, dependency selection, and changes to expected results that are not already authorized.
  - Does not silently replace approved product behaviour because another arrangement appears visually preferable. Does not invent logos, fonts, palettes, illustration styles, or brand meaning when those are material unresolved decisions.
- **Handoff Conditions**: After the visual specification is complete, hand implementation-ready visual requirements to `software-development`/`frontend-development`, supplied text requirements to UX writing when applicable, and observable visual criteria to `testing-and-verification`. Return unresolved behavioural conflicts to `product-design` and unresolved material visual decisions to `task-framing`.

## Activation and Non-Activation Conditions
- **Activation**: Triggers when translating approved requirements into layouts, composition, color, spacing, and typography systems.
  - Validate the proposed design through comparison walkthroughs to evaluate visual spec coherence.
- **Non-Activation**: Does not trigger for writing code, writing copy, defining behavioral rules, or independent verification.

## Required Inputs
- original request or valid task frame;
- approved product-design specification or clearly bounded visual request;
- approved screenshots, prototypes, visual references, design-system files, tokens, themes, or brand assets when available;
- required states, information hierarchy, interaction priorities, and responsive contexts;
- existing interface surfaces and visual conventions relevant to the task;
- supplied copy or clearly marked content requirements.
- *Note*: Not all inputs must exist; explicitly identify missing material visual decisions.

## Authority Boundaries
- **Authorized Actions**:
  - Inspect only task-relevant visual surfaces and configuration.
  - Choose spacing within an established scale or arrange approved content within an established component pattern.
  - Define visual layout systems, grids, and responsive flow.
  - Define typography roles and relationships using an established system.
- **Unauthorized Actions**:
  - Writing production code or production configuration.
  - Modifying product workflow, business rules, or permissions to simplify layout composition.
  - Choosing final interface wording or final copy labels.
  - Silently creating a new font family, new type scale, new cross-product heading hierarchy, or new editorial typographic voice. Those are material unless already authorized.
  - Establishing or changing brand palette, logo treatments, or visual themes unless explicitly authorized.

## Ordered Procedure
1. **Confirm Boundary**: Confirm the task boundary and visual-design authority.
2. **Inspect Inputs**: Inspect controlling product requirements and visual evidence.
3. **Record Constraints**: Record approved visual constraints and unresolved material decisions.
4. **Analyze Current State**: Analyze the current visual surface where one exists. Inspect only task-relevant visual surfaces. Distinguish approved visual direction, current rendered appearance, current design-system rules, inherited framework defaults, inconsistent/accidental styling, and model assumptions. Identify hierarchy failures, density inconsistencies, contrast/legibility issues, and generic framework defaults.
5. **Define Visual Hierarchy**: Define the visual hierarchy (primary/secondary/tertiary information and actions, reading order, grouping).
6. **Define Composition**: Define composition and layout relationships.
7. **Define Styling**: Define typography, colour, spacing, surfaces, and component treatment within authority.
8. **Define Responsive Adaptations**: Define responsive adaptations.
9. **Define State Treatment**: Define visual treatment for applicable product states.
10. **Visual-Comparison Procedure**: When fidelity to a reference is required:
    - identify the exact reference state and viewport;
    - compare hierarchy, composition, alignment, spacing, typography, colour roles, component treatment, imagery, and visible states;
    - record deliberate deviations and their authority;
    - do not claim fidelity for unexamined states or viewport conditions. (Independent verification of the implemented result remains owned by `testing-and-verification`).
11. **Compare Design**: Compare the proposed design against approved references and system consistency.
12. **Produce Deliverable**: Produce the visual specification and downstream handoff.
13. **Record Risks**: Record assumptions, exclusions, and unresolved risks.

## Evidence Requirements
- **Actionability**: Every procedural step must use imperative language and identify a concrete action plus its expected outcome or validation evidence.
- **Demonstrated Evidence**: Include concise examples demonstrating: improving an existing interface's visual hierarchy while preserving its approved information structure; reproducing an approved screenshot without treating framework defaults as authoritative; responsive adaptation that preserves priority rather than merely stacking elements; a design blocked by unresolved palette or typography direction; identifying that a requested visual change actually requires a product-design decision; and applying an approved creative thesis to produce a non-generic, non-templated composition for a public or expressive surface.

## Visual-Design Boundary
- Product design determines what information and actions exist, their behavioural priority, and applicable states.
- Visual design determines how those approved requirements are visually organized, distinguished, emphasized, and adapted.
- Visual design may identify that a requested treatment conflicts with approved hierarchy, behaviour, accessibility constraints, brand direction, or reference fidelity. It must report the conflict and return it to `product-design` or `task-framing` rather than silently changing the requirements.
- Visual design may identify when behavioural requirements cannot be visually expressed coherently without violating controlling requirements, but must return the conflict to `product-design` or `task-framing`. It must not change workflow or content requirements to simplify the composition.

## Visual Evidence Hierarchy
The applicable evidence depends on the discipline.
1. Current explicit user visual instructions and approvals.
2. Approved screenshots, prototypes, mockups, and reference assets (screenshots govern visual fidelity).
3. Approved design-system tokens, themes, components, and brand assets.
4. Product-design hierarchy and behavioural requirements (product specifications govern behavior/info).
5. Existing visual patterns that remain applicable.
6. Observable rendered output (existing implementation is evidence of current appearance, not automatic visual authority).
7. Authoritative accessibility and platform guidance.
8. Skill defaults and model assumptions.
*Note*: Written design prose does not override a later explicit user-approved visual reference.

## Exact Visual Values from Screenshots
An approved screenshot governs visual fidelity, but a screenshot alone may not reliably establish exact source tokens because of scaling, compression, colour profiles, or antialiasing.
When exact tokens are unavailable:
- distinguish directly supplied values from visually inferred values;
- treat inferred values as bounded approximations only when the task permits;
- record uncertainty;
- do not falsely claim that an inferred hex value, radius, spacing value, or font metric is the original source value.

## Visual Decision Classification
- **Observed Visual Constraint**: A requirement imposed by approved references, brand assets, design-system rules, accessibility requirements, platform constraints, or approved product hierarchy. Current rendered appearance is controlling only when the task requires preserving it or other controlling evidence approves it. Existing appearance alone is not automatic visual authority.
- **Bounded Visual Decision**: A reversible local choice clearly supported by the approved direction, such as spacing within an established scale or arranging approved content within an established component pattern.
- **Material Visual Decision**: A choice that establishes or substantially changes the brand palette, typography system, logo treatment, illustration or photographic direction, major layout paradigm, theme strategy, visual density, public-facing aesthetic, or cross-product design language. Accessibility and platform requirements normally act as constraints. Escalation is required only when satisfying them would require changing approved behaviour, scope, brand direction, or another unresolved material decision.

## Visual Hierarchy
Define, where applicable: primary, secondary, and tertiary information; primary and secondary actions; reading order; grouping and separation; persistent versus contextual controls; emphasis and de-emphasis; density and whitespace; visual distinction among navigation, controls, system feedback, and user content. Visually express the approved hierarchy without changing product priority.

## Composition and Layout
Define: page regions; grid or alignment logic; container relationships; component arrangement; spacing rhythm; fixed, sticky, scrolling, or contextual presentation when behaviour permits; responsive reflow; content width and density; navigation/tools relationships. Explain why the composition supports the hierarchy rather than describing it as merely clean, modern, premium, or intuitive.

## Typography
Define, where authorized: type roles; hierarchy; size relationships; weight; line height; measure; casing; emphasis; numeric/data presentation; responsive adaptation. Do not select a new font family when typography direction is unresolved. Avoid arbitrary font scales, excessive weights, decorative type harming legibility, or manipulating type to contradict product priority.

## Colour and Contrast
Define: semantic roles (background, surface, text, border, action, feedback, focus, data-visualization) rather than isolated colour names; state relationships; light/dark theme behaviour where authorized; contrast and legibility requirements. Do not invent a new palette when brand direction is unresolved, use colour as the sole signal for meaning, treat framework defaults as brand colors, or claim accessibility solely from visual inspection.

## Spacing, Surfaces, and Component Treatment
Define: spacing scale usage; internal versus external spacing; grouping distance; corner treatment; borders/separators; elevation/shadows; surface hierarchy; control sizing. Require every decorative choice to serve hierarchy, grouping, affordance, feedback, brand expression, or legibility.

## Imagery, Illustration, and Iconography
Define only when applicable: functional role; visual style; consistency; cropping/placement; icon meaning; decorative/informative status; alternative-text or content requirements. Do not use stock imagery, abstract gradients, decorative blobs, or icons merely to fill space. Selecting a new style is material unless established.

## Responsive Design
Define behaviour across viewports: hierarchy preservation; reflow; wrapping; stacking; visibility changes; overflow/scrolling; density adjustments; touch-targets; long-content handling. Do not treat "responsive" as simply stacking everything vertically.

## Product-State Visualization
For states supplied by product design, define visual treatment for applicable:
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

Visual design determines presentation, not state logic or final wording.

## Specificity Requirement
Prohibit unsupported adjectives such as clean, modern, premium, elegant, intuitive, polished, professional, visually appealing. Translate all terms into observable design decisions.
- *Avoid*: “Make the card more premium.”
- *Use*: “Increase separation between the metadata and primary action, reduce border contrast, preserve the established corner radius, and use the approved heading role for the record name.”

## Exact Deliverables
A bounded visual specification or layout package (delivered internally, conversationally, or persisted):
- controlling visual evidence;
- current-state findings;
- visual hierarchy;
- composition and layout specification;
- typography roles;
- colour roles;
- spacing and surface treatment;
- component appearance;
- state treatments;
- responsive adaptations;
- imagery or icon requirements;
- bounded visual decisions;
- unresolved material visual decisions;
- implementation annotations;
- visual acceptance criteria;
- downstream handoffs;
- assumptions and exclusions.

## Visual Acceptance Criteria
Criteria must be observable and tied to approved evidence:
- **Desktop read priority**: "At desktop width, the record identity and current status form the first reading group, while administrative metadata remains visually subordinate."
- **Narrow width actions visibility**: "At narrow widths, primary actions remain available without horizontal page scrolling."
- **Non-color state indicators**: "Error and success states remain distinguishable without relying on colour alone."
- *Avoid*: "Looks polished.", "Feels premium.", "Has good spacing.", "Matches the vibe."

## Validation Gates
Before claiming the visual specification complete:
- [ ] **Evidence Identified**: Controlling visual evidence is identified.
- [ ] **Hierarchy Preserved**: Product hierarchy and behaviour are preserved.
- [ ] **Current vs. Approved separation**: Current appearance is distinguished from approved direction.
- [ ] **Decision Separation**: Bounded and material visual decisions are separated.
- [ ] **No Silently Invented Brand Decisions**: Unresolved brand or visual-system decisions are not silently invented.
- [ ] **Complete Styling definition**: Hierarchy, composition, typography, colour, spacing, and states are defined where applicable.
- [ ] **Responsive Extremes Check**: Responsive extremes are considered.
- [ ] **Non-Color State Indicators**: Visual treatment does not depend on colour alone.
- [ ] **Copy Integrity**: Final copy is not invented.
- [ ] **Product Integrity**: Product workflow has not been altered.
- [ ] **Annotation Integrity**: Implementation details remain annotations rather than unauthorized code decisions.
- [ ] **Observable Criteria**: Visual criteria are observable.
- [ ] **Specificity Check**: Unsupported aesthetic adjectives are absent.
- [ ] **Handoff Clarity**: Implementation annotations, UX-writing needs, verification criteria, behavioural conflicts, and unresolved material visual decisions are routed to the correct downstream discipline.
- [ ] **Exclusions & Assumptions Check**: Assumptions and exclusions are documented.
- [ ] **No Placeholders**: No TODOs, accidental placeholders, or unresolved drafting markers remain. Clearly defined metavariables (such as `<theme-color>`) are permitted.
- [ ] **Link Verification**: Apply link verification only when the task creates or modifies links.

## Stop and Failure Conditions
- **Halt Execution immediately when**:
  - Approved visual references materially conflict and authority cannot resolve them.
  - Brand palette, typography, logo, theme, or overarching visual direction must be selected without authorization.
  - Product requirements do not establish the information or actions that must be presented.
  - A requested visual treatment would violate controlling accessibility, platform, or product constraints.
  - The task requires changing product behaviour rather than visually expressing it.
- **On Failure**: Preserve partial visual layouts. Report the exact blocker, missing context, and whether it requires a policy clarification. Do not stop for minor reversible details.

## Prohibited Behaviours
- **Default Presentation**: Generic framework-default design presented as intentional visual design.
- **Preference Substitution**: Replacing supplied visual references with personal preference.
- **Silent Behavior Inventions**: Inventing product behaviour to make a layout work.
- **Visual Blobs**: Arbitrary gradients, excessive shadows, decorative blobs, needless glass effects, or animation without functional or approved expressive purpose.
- **Inconsistent Styles**: Inconsistent spacing, radii, typography, iconography, or surface treatment.
- **Final copy generation**: Writing final interface or marketing copy.
- **Production alterations**: Modifying production code or production configuration.
- **Aesthetic accessibility claims**: Using accessibility terminology or claiming compliance without appropriate evidence.
- **Fidelity assumptions**: Claiming screenshot fidelity without comparing the relevant states and viewport conditions.
- **Scope expansion**: Redesigning unrelated surfaces for consistency without task authority.
- **Priority modification**: Changing visibility, navigation, interaction sequence, or content priority merely to simplify the layout.

## Conflict-Resolution and Evidence Hierarchy
This hierarchy resolves conflicts among workspace instructions and skill documents. It does not override
platform-level, system-level, safety, security, or tool-use requirements governing the agent.
- **Conflict Resolution**:
  1. User's explicit instructions in the current prompt.
  2. Workspace rules (`AGENTS.md` or equivalent).
  3. Governing standard (`.agents/skills/skill-authoring-standard/SKILL.md`).
  4. Individual skill `SKILL.md`.
  5. Global agent guidelines.
- **Evidence Hierarchy (Source of Truth)**: Same ordering as
  [Visual Evidence Hierarchy](#visual-evidence-hierarchy).
  1. Current explicit user visual instructions and approvals.
  2. Approved screenshots, prototypes, mockups, and reference assets (screenshots govern visual fidelity).
  3. Approved design-system tokens, themes, components, and brand assets.
  4. Product-design hierarchy and behavioural requirements (product specifications govern behavior/info).
  5. Existing visual patterns that remain applicable.
  6. Observable rendered output (existing implementation is evidence of current appearance, not automatic
     visual authority).
  7. Authoritative accessibility and platform guidance.
  8. Skill defaults and model assumptions.

  *Note*: Written design prose does not override a later explicit user-approved visual reference.

## Concrete Usage Examples

> [!NOTE]
> Named execution skills, commands, files, paths, design systems, screenshots, products, components, fonts, colours, or commands in these examples are hypothetical unless explicitly identified as existing.

### Example 1: Improving Dashboard Visual Hierarchy
- **Task**: Improve record-card dashboard visual hierarchy.
- **Controlling Evidence**: The existing approved design system defines `Heading 2`, `Caption`, and secondary-action roles. The approved card pattern permits a trailing action region.
- **Specification**: Apply those established roles rather than inventing them:
  - Record name utilizes the `Heading 2` typographic role.
  - Action items are grouped on the card's right-hand side using the secondary action role.
  - Administrative metadata is set to `Caption` role, visually subordinating it against the card background while retaining required legibility and approved contrast constraints.
  - Preserves behavioral sequence (archiving/viewing the record remains identical).

### Example 2: Reproducing an Approved Screenshot
- **Task**: Style a custom button based on approved screenshot `./design/spec.png` (hypothetical).
- **Fidelity rules**:
  - The screenshot is approved and governs visual fidelity for the represented viewport and state.
  - Exact color and radius values come from supplied design tokens or inspectable source assets when available.
  - Visually inferred hex value `#3B4252` and border radius `4px` are recorded as approximations rather than original source values because of antialiasing and color profiles.
  - Do not infer unshown responsive states, hover interactions, or validation error states from one screenshot.

### Example 3: Responsive Priority Preservation
- **Task**: Define responsive adaptation for a record list.
- **Prerequisites**: Product design has already classified Record Name, Alerts, and the primary action as required at narrow viewports. Secondary metadata (Last Login, Joined Date) may be collapsed or hidden according to the approved specification. All authorized actions remain available. Breakpoints follow the established responsive scale.
- **Specification**:
  - At viewports >= 1024px, display all columns in a row.
  - At viewports < 768px, hide secondary metadata and flow actions into an overflow menu using the existing design system breakpoints and overflow-menu pattern.
  - If priority, visibility, or overflow behaviour is not approved, return the issue to `product-design` rather than deciding it visually. Do not invent arbitrary breakpoints.

### Example 4: Blocked by Unresolved Palette / Typography Direction
- **Task**: Style a new landing page.
- **Blocker**: Brand strategy, campaign concept, public aesthetic, imagery direction, or expressive tone is unresolved.
- **Classification**: Material Visual Decision (Blocked).
- **Handoff**:
  - Route brand or campaign direction to `creative-direction`.
  - Route material palette, typography, logo, or theme approval to `task-framing`.

### Example 5: Visual Request Requiring Product-Design Decision
- **Task**: "Make the record details page fit on one screen without scrolling by moving the record history into a modal."
- **Analysis**: Moving persistent history into a modal changes information visibility, access sequence, discoverability, and comparison behaviour. These are product-design concerns, not merely visual rearrangement.
- **Action**: Stop execution. Present the mismatch and behavioural alternatives to `product-design` or `task-framing` to obtain authorization.

### Example 6: Applying an Approved Creative Thesis to a Public Editorial Page
- **Task**: Style a long-form public article page once `creative-direction` has supplied an approved thesis emphasizing asymmetric reading rhythm and restrained, non-card-based grouping.
- **Controlling Evidence**: Approved creative brief anti-reference excludes repeating card grids and pill-badge metadata; approved thesis calls for treating the article body and its supporting media as one continuous reading path rather than segmented widgets.
- **Specification**: Apply an asymmetric single-column measure with margin-anchored captions instead of a sidebar-card pattern; use established type roles for a reading hierarchy (headline, deck, body, caption) without introducing dashboard-style metadata chrome; responsive behavior collapses margin captions inline rather than into an overflow menu, preserving the continuous-reading-path requirement.
- **No product-design gate required**: The task has no accounts, permissions, or persisted user data; visual-design proceeds directly from the approved creative brief and a bounded visual request, consistent with this skill's Required Inputs, which already permit "a clearly bounded visual request" as an alternative to a product-design specification.
