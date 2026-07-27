# ChickenButt Agent Instructions

These instructions apply to every agent working in this repository.

## Ground truth

* Current source code and verified test behavior outrank documentation when they conflict.
* Report real conflicts instead of silently choosing an interpretation.
* Do not treat old comments, line numbers, test counts, or status claims as current without checking the present tree.
* `web/` is the embedded transcript interface used by the desktop app.
* `chickenbutt-web/` is the public React/Vite project website.
* Do not confuse, merge, rename, or replace these directories without explicit authorization.

## Change discipline

* Preserve observable behavior unless the user explicitly authorizes a behavior change.
* Keep each change narrowly scoped.
* Do not mix feature work, behavior changes, structural refactoring, and unrelated cleanup.
* Do not rewrite major modules wholesale when a bounded change will work.
* Inspect current call sites and relevant tests before changing interfaces or ownership.
* Do not create roadmaps, progress logs, handoff files, audit documents, or project ledgers unless explicitly requested.
* Do not introduce new dependencies when the existing stack can reasonably perform the task.

## Authorization

* Diagnosis and review do not authorize implementation.
* Implementation, commits, pushes, publication, pull-request review, and merging are separate actions unless explicitly combined by the user.
* Do not make repository-wide structural changes without explicit authorization.
* Stop on a failed verification gate, live mismatch, or genuine ambiguity that would materially affect the result.

## Desktop application

* ChickenButt is a native Python GTK4/libadwaita application.
* PyGObject, GTK4, libadwaita, WebKitGTK, and dasbus are system dependencies, not normal project-local `pip` dependencies.
* Preserve the distinction between the default WebKit transcript and the native GTK transcript fallback.
* Changes affecting installed layout, desktop metadata, icons, launchers, or system integration must be tested through the Meson-backed installation checks.

## Website

* The public website lives in `chickenbutt-web/`.
* Preserve its local `.agents/` instructions and skills.
* Do not commit generated website output:

  * `chickenbutt-web/node_modules/`
  * `chickenbutt-web/dist/`
* Run `npm run build` after changes that affect the website application or its build configuration.

## Git

* Begin substantial work from a clean working tree.
* Inspect the diff before staging or committing.
* Use short-lived branches for substantial or risky changes once the repository is publicly active.
* Do not rebase, squash, reset, force-push, rewrite shared history, or amend published commits without explicit authorization.
* Do not push, merge, publish, create releases, or open pull requests without explicit authorization.
* Do not add `Co-authored-by` trailers or automated AI attribution to commits unless the user explicitly requests it.
* Before reporting a push or merge as complete, verify the local branch, remote branch, and working-tree state.

## Verification

* Confirm that every changed file belongs to the requested scope.
* Run compilation, targeted tests, and broader tests in proportion to the risk.
* For Python changes, run the relevant scripts under `scripts/`.
* For website changes, run the Vite production build.
* For installed-layout or desktop-integration changes, ensure the Meson-backed tests genuinely execute; a skipped critical test is not a pass.
* Distinguish local test results from GitHub Actions results.
* Perform one bounded self-review after implementation.
* Do not initiate repeated review loops after a clean result.
* Never claim a Git, test, CI, build, or runtime fact was verified unless it was actually checked.

## Reporting

* Lead with the outcome.
* State the exact scope of the work.
* State what verification was performed.
* State whether any commit, push, pull request, merge, or publication occurred.
* Separate observed facts, supported risks, proposed changes, and decisions requiring authorization.
* Keep reports concise.
