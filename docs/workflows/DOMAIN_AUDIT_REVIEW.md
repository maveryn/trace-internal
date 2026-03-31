# TRACE Domain Audit Review

Use this workflow for repo-wide sanitation passes that review one active domain at a time.

## 1) Purpose
1. Catch contract drift, visual clarity problems, stale docs/configs/tests, and lingering review inconsistencies after a domain has grown over multiple patches.
2. Keep audits domain-scoped so fixes stay tractable and validation remains targeted.
3. Turn recurring findings into reusable guidance by updating `docs/workflows/CODE_REVIEW_GUIDELINES.md` when needed.

## 2) Audit inputs per domain
For the domain being reviewed, inspect:
1. Domain setup doc in `docs/domains/`.
2. Active task inventory in `docs/project/STATUS.md` and `docs/tasks/README.md`.
3. Repo-local domain skill in `skills/domain-<domain>/`.
4. Task modules, domain/task-group configs, prompt bundles, task docs, and tests.
5. Existing task-review artifacts under `task-reviews/<domain>/`.

## 3) Required audit checklist
### A. Inventory and registration
1. Active task ids in code, docs, configs, and review folders agree.
2. Task ids, filenames, and module layout match the documented taxonomy.
3. Retired tasks are not still listed as active examples, prompts, or review rows.

### B. Contract and prompt audit
1. Prompt wording matches the real scene contract and evidence contract.
2. Prompt-facing evidence is local, non-vacuous, and visually discoverable.
3. Zero-answer cases use the documented empty evidence contract rather than widened fallback evidence.
4. Prompt examples remain valid for the active task/variant surface.

### C. Visual audit
1. The queried object, marker, or reference is easy to locate.
2. Labels do not overlap figures, points, cells, or critical geometry when avoidable.
3. Non-semantic style variation does not create semantic ambiguity.
4. Layout size, gutters, and text scale still support the task at the configured max scene density.

### D. Sampling and answer-support audit
1. Scene construction still supports the configured answer range by construction or explicit feasibility checks.
2. No task variant has collapsed to a tiny answer support unintentionally.
3. Reference/context objects are not accidentally counted when the prompt only asks about the candidate pool.

### E. Shared-infra audit
1. Helpers still live at the narrowest reusable layer that fits.
2. No task-local wrapper has silently become shared infrastructure.
3. Config defaults live in domain/task-group config instead of repeated task-local literals.

### F. Docs and tests audit
1. Domain setup docs and task docs still describe the live contract.
2. Tests cover the actual contract surface and do not only assert stale defaults.
3. Review status and review summary reflect the active task surface.

## 4) Audit conventions
1. Work domain by domain; do not mix fixes from unrelated domains in the same audit patch unless they are truly shared infrastructure.
2. Start by reading the domain setup doc and existing review artifacts before changing code.
3. Fix safe, clearly correct issues immediately rather than building a long deferred list.
4. If an issue repeats across tasks, add one reusable rule to `docs/workflows/CODE_REVIEW_GUIDELINES.md` in the same patch.
5. Keep a short issue taxonomy in notes and handoff:
   - `contract`
   - `visual`
   - `distribution`
   - `shared`
   - `docs`

## 5) Validation expectations
1. For audit-only reading with no code changes, inspection of the existing review artifacts is enough.
2. If code, prompts, configs, or docs change:
   - run focused pytest for the touched area first,
   - run `python -m py_compile` when shared/task modules changed,
   - run `git diff --check`,
   - run full task review for every touched task:
     - `PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode full`
3. If the audit changes shared infrastructure, expand pytest coverage to the affected sibling tasks.

## 6) Recommended audit order inside one domain
1. Domain inventory and task list.
2. Shared helpers and configs.
3. Prompt bundles and docs.
4. Task modules.
5. Tests.
6. Review artifacts and targeted image sampling.
7. Fixes + validation.

## 7) Handoff format
Summarize each domain audit under:
1. `Fixed` — issues corrected in this pass.
2. `Deferred` — issues intentionally left for later, with reason.
3. `Rules added` — any new distilled reusable review rules.
4. `Validation` — focused tests and task reviews that were rerun.
