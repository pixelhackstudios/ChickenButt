# Agentic Skills — Repository Operating Contract

This file is `AGENTS.md` at the repository root — the single authoritative operating contract for work performed
**on this repository**: authoring, modifying, auditing, or integrating the skill framework itself under
`.agents/skills/`, and maintaining this repository's own documentation and tooling. It does not govern
application code in a separate host project that later copies `.agents/skills/` into its own codebase; a host
project that consumes these skills defines its own workspace-rules contract for its own work.

Every installed skill's Conflict-Resolution and Evidence Hierarchy places workspace rules at position 2, above
`skill-authoring-standard`. In this repository, this root `AGENTS.md` is that authoritative contract. A host
project that copies the skills may supply its own equivalent workspace-rules contract.

## 1. Repository Purpose and Scope

This repository contains the installed skills under `.agents/skills/`. `README.md` is the current inventory and
responsibility overview — inspect it when a task affects repository purpose, the installed-skill inventory, the
routing overview, installation instructions, or current public status. `ROADMAP.md` distinguishes completed,
active, planned, and possible work — inspect it when a task affects milestone status, real-world validation,
future capability planning, tooling order, or release preparation. Inspect only the sections relevant to the
task; this file does not require reading either document end-to-end for every task, consistent with
`task-framing`'s own instruction to avoid reading the entire workspace by default.

This file governs maintenance and evolution of the skill framework itself, not the execution of an external
project that happens to use the skills.

## 2. Source of Truth and Conflict Resolution

Use the standard hierarchy already established across every installed skill:

1. Current explicit user instructions.
2. Workspace rules (this file).
3. `skill-authoring-standard` (`.agents/skills/skill-authoring-standard/SKILL.md`).
4. Applicable individual `SKILL.md` files.
5. Global agent guidelines.

This numbered order does not create a standing exception where this file overrides the others on their own
subject matter — it resolves generic conflicts, while claim-specific direct authority determines which source
actually governs a given question within the boundaries this file authorizes:
- this file governs repository-level workflow and process — routing, reporting, git discipline, and validation;
- `skill-authoring-standard` has the most direct authority over the structure and validation requirements of
  skill files, and this file does not redefine or duplicate that authority;
- individual skills have the most direct authority over their own discipline-level procedures, activation
  conditions, and evidence models, and this file does not redefine or duplicate that authority either.

Use the source with the most direct authority over the specific claim; do not flatten all evidence into one
universal ranking. Current repository files (`README.md`, `ROADMAP.md`, the installed `SKILL.md` files, `git log`
/ `git status`) always outrank memory of a prior session or a prior conversation's summary of repository state —
verify against the actual file before relying on a remembered claim.

This hierarchy does not override platform-level, system-level, safety, security, or tool-use requirements
governing the agent.

## 3. Mandatory Skill Loading Before Writes

Before creating, editing, deleting, or restructuring any file in this repository, the agent must:

1. Classify the task using the Repository-Maintenance Routing table (Section 4).
2. Identify every mandatory skill for that classification.
3. Open and read the complete `SKILL.md` for each mandatory skill during the current task. Knowing a skill's
   name, its one-line description, or having used it in an earlier session does not satisfy this requirement —
   it must be opened this task.
4. Inspect the actual current state of every repository file the task will touch or reference.
5. Produce the Pre-Change Report (Section 5).
6. Only then begin writing.

## 4. Repository-Maintenance Routing

| Repository task | Mandatory loading |
|---|---|
| Create, modify, or audit a skill | `skill-authoring-standard` and every skill directly or semantically affected |
| Change cross-skill authority, activation, or handoffs | `skill-authoring-standard`, `task-framing`, and every affected skill |
| Update `README.md` or `ROADMAP.md` claims | No skill is strictly mandatory, but every changed claim must be grounded in the actual current skills and repository state, not memory |
| Add repository validation scripts or tooling | `software-development` as the governing implementation baseline; `testing-and-verification` only when conducting a distinct independent verification pass |
| Record, assess, or integrate real-world validation findings into this repository | `task-framing` when reopening a foundational skill is under consideration; the specific skill(s) the finding concerns |
| Mechanical documentation correction (typo, broken link, stale count) | Load only what is necessary to establish the correction; do not expand into a broader audit |
| Create or materially modify `AGENTS.md` or equivalent workspace rules | `task-framing`; every installed skill semantically affected; `skill-authoring-standard` when skill files are also created, modified, or audited |

A task may match more than one row; combine the mandatory loading from every matching row. When a change is
cross-disciplinary, changes authority or handoffs, is multi-stage, or contains an unresolved material decision,
also load `task-framing`.

A real-world-validation task is governed by the *host project's own* workspace rules, not this file — that
project loads skills according to its own requirements. This file governs only the evaluation and integration of
findings back into this repository: whether a finding is concrete and reproducible, how it is documented here,
whether it justifies reopening a skill, and how any resulting repository change is classified and validated. A
foundational skill may be reopened only for a concrete, reproducible defect or a repeated capability gap —
inconvenience, agent preference, or one weak execution is not sufficient evidence by itself.

A mechanical typo, formatting correction, or broken link in this file follows the Mechanical Documentation
Correction row instead — it does not activate `task-framing` or `skill-authoring-standard` unless their own
activation conditions independently apply. A change to the conflict-resolution hierarchy, the mandatory-loading
rules, the Pre-Change Report gate, material-decision authority, or the validation requirements in this file is
Material (Section 7) and requires explicit authorization — never disguise a change to this file as ordinary
documentation cleanup.

Do not invent a mandatory skill that is not one of the installed skills under `.agents/skills/`. Do not treat a
skill proposed in `ROADMAP.md`'s "Future skills" list as though it is installed.

## 5. Pre-Change Report

Before the first write operation in a repository-maintenance task, produce this compact report. Read-only
inspection may precede it.

```text
Task classification:
- [skill authoring / cross-skill integration / documentation / tooling / real-world validation finding / mechanical correction / AGENTS.md change]

Skills loaded:
- [skill]: [why it applies]

Repository sources inspected:
- [files]

Authorized change:
- [bounded scope]

Material decisions or blockers:
- [none, or the exact unresolved issue]

Planned validation:
- [checks appropriate to the change]
```

Do not claim a skill was loaded unless its complete `SKILL.md` was opened during the current task. This report is
optional for purely read-only questions that do not modify a file.

## 6. Git Baseline and Unrelated-Work Protection

Before modifying files:
- record staged, unstaged, and untracked baseline state (`git status`);
- distinguish pre-existing user work from agent-created changes;
- never use destructive worktree commands (`git reset --hard`, `git clean -fd`, broad `checkout`/`restore`) that
  could erase unrelated work.

Before reporting completion:
- inspect the resulting diff against the recorded baseline;
- confirm only files justified by the authorized scope were changed;
- preserve unrelated pre-existing changes exactly as found.

## 7. Change Classification: Mechanical, Bounded, Material

Use the classification model already established by `software-development` and `task-framing` — do not create a
competing one:
- **Mechanical**: evidence completely determines the correction — a stale installed-skill count, a
  completed-commit reference, a broken link, a heading typo, or a milestone status whose authorized completion
  is already established in the repository.
- **Bounded**: a reversible clarification within already-settled authority and repository policy.
- **Material**: a change to skill ownership, activation, routing, conflict-resolution priority,
  material-decision authority, the installed-skill inventory, required handoff relationships, release policy,
  validation policy, or the meaning of a roadmap milestone. A documentation edit may be Material because of
  *what* it changes, not merely because it edits a repository-state claim.

Examples of material framework changes that require authorization through `task-framing` or the user before
implementation, never silently resolved during a "cleanup" pass:
- changing which skill owns a responsibility;
- changing activation in a way that alters project routing;
- changing conflict-resolution priority;
- changing material-decision authority;
- adding or removing an installed skill;
- changing a required handoff relationship;
- declaring the motion-skill boundary (`ROADMAP.md` Milestone 3) resolved;
- moving or renaming the authoritative `AGENTS.md` contract without updating every skill's workspace-rules
  reference in the same change.

## 8. Cross-Skill Authority and Handoff Integrity

When a change touches ownership, activation, handoffs, conflict priority, material-decision authority, the
installed-skill inventory, or framework routing: open and inspect every affected skill directly. Do not infer
compatibility from a skill's name, its one-line description, or a prior session's summary of its content.

When installing or removing a skill, update, in the same change:
- every affected existing installed-skill inventory (a skill's own `Concrete Usage Examples` note, `README.md`'s
  table, `ROADMAP.md`'s foundation list);
- every stale hypothetical-versus-installed statement referencing it;
- every affected handoff and routing reference;
- any `README.md`/`ROADMAP.md` claim that became stale as a result.

Do not require adding an installed-skill inventory to a skill file that did not already contain one, merely so
the new skill can be listed there — update only the inventories and references that already exist.

When a reference cannot be updated in the current change (for example, it requires an authorization not yet
granted), do not report the installation as complete — report the specific remaining inconsistency.

## 9. README and ROADMAP Synchronization

`README.md` describes the current framework, installed skills, routing overview, and usage. `ROADMAP.md`
distinguishes completed, active, planned, and possible work — it is expected to contain planned and merely
possible items, and that alone is not a staleness defect.

- Ground every changed claim in the actual current skills and repository state; verify before writing, don't
  recall.
- Never represent planned or possible work as installed, completed, or validated.
- Completed or active status must trace to repository evidence, not memory or intention.
- Never update an installed-skill count or inventory from memory — inspect the actual `.agents/skills/`
  directory.
- Structural validation and real-world validation remain distinct; never describe one as proof of the other.
- Do not change a `ROADMAP.md` milestone's status without the repository evidence that justifies the new status.
- Do not require a documentation update when no documented claim actually became stale.

## 10. Validation Requirements

Apply the checks proportionate to the change; not every check applies to every task:
- YAML frontmatter parsing (all touched `SKILL.md` files);
- required-section presence (per `skill-authoring-standard`);
- in-file anchor resolution;
- Markdown fence balance;
- repository-relative link resolution;
- unresolved-placeholder detection;
- stale hypothetical-vs-installed reference detection;
- stale handoff/routing reference detection;
- installed-skill count/inventory consistency between `README.md`, `ROADMAP.md`, and the actual skill
  directories;
- contamination/residue search for external names, technologies, or assumptions when adapting material from
  outside this repository;
- diff-scope inspection against the recorded baseline;
- final worktree state.

When a change touches this file's own installation or path:
- verify the authoritative root `AGENTS.md` exists;
- verify every installed skill's workspace-rules reference resolves to `AGENTS.md`, or explicitly allows an
  equivalent host-project contract;
- verify no reference to a prior, pre-installation workspace-rules path remains in any skill file;
- verify no second authoritative or pointer contract exists.

These path-validation checks apply during this contract's installation and any future path-related maintenance,
not every unrelated task.

Report each check's exact command, tool invocation, or manual procedure actually used, and its result.
Distinguish **passed**, **failed**, **blocked**, and **not run** — never claim a check passed without having
executed it. Structural validation passing is never itself proof of real-world effectiveness; state that
distinction whenever both are discussed.

## 11. Commit and Push Rules

Do not assume every change should be committed or pushed. Commit and push only when:
- the task explicitly requests it;
- an existing, already-authorized frame covers it; or
- the user authorizes it after reviewing the proposed change.

Before committing: inspect the full diff, confirm validation passed or disclose exactly what remains unverified,
and confirm no unrelated files are staged.

## 12. Fail-Closed Conditions

Stop before writing when:
- a mandatory skill cannot be located or opened;
- an unresolved material authority or routing decision blocks valid execution;
- an unresolved conflict remains after applying the conflict hierarchy (Section 2) and claim-specific authority;
- an affected cross-skill relationship cannot be determined from the current files;
- the repository baseline cannot be safely distinguished from unrelated user work;
- a destructive operation would be required without explicit authorization.

Do not halt merely because one nonessential check is unavailable — continue with the valid evidence available
and report exactly what remains unverified.

## 13. Prohibited Shortcuts

Do not:
- load a skill's `SKILL.md` after editing has already begun;
- claim a skill was loaded based on its name or one-line description alone;
- load every skill indiscriminately, or load an unrelated skill as performative compliance;
- invent an installed skill that does not exist in `.agents/skills/`;
- treat a skill proposed in `ROADMAP.md`'s "Future skills" list as though it were installed;
- change which skill owns a responsibility, or any cross-skill authority, silently during an otherwise bounded
  or "cleanup" task;
- run a broad architectural audit when the task frame authorized a bounded implementation;
- update `README.md` or `ROADMAP.md` from memory instead of the actual current files;
- describe structural validation as proof of real-world effectiveness;
- expand the framework speculatively — add a skill, section, or capability the task does not require and no
  concrete defect justifies;
- import another repository's product names, technology stack, terminology, file paths, or design assumptions
  when adapting external reference material into this repository;
- rewrite an existing fictional example merely because it is fictional, absent an actual defect in what it
  demonstrates;
- claim independent verification (`testing-and-verification`'s exclusive authority) from implementation
  self-validation (`software-development`/`frontend-development`'s authority);
- treat existing prose or implementation as automatically authoritative over more direct evidence (a current
  file, a run command's actual output).

## 14. User Overrides

An explicit user instruction in the current prompt outranks this file and every installed skill (Section 2).
When the user explicitly names a skill, load it even if this file's routing table would not otherwise select it.

User authority may expand or change task scope. It cannot:
- make an unexecuted check "passed";
- make unsupported evidence "verified";
- authorize false completion reporting.

Explicit authorization remains scoped to the current task and action — it does not carry forward to later,
unrelated actions in the same or a later session.

User authorization cannot suspend platform-level, system-level, safety, security, or tool-use requirements
governing the agent.
