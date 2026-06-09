---
name: code-review
description: Use when reviewing TRACE changes for helper placement, duplication, contract drift, doc sync, or validation gaps before commit or merge.
---

# Code Review

Use this for implementation reviews, refactor reviews, and pre-merge checks.

## Read first
1. `docs/workflows/CODE_REVIEW_GUIDELINES.md`
2. `docs/workflows/SHARED_UTILITIES.md`
3. `docs/core/BLUEPRINT.md`

## Review checklist
1. Helper placement is correct and no duplicated deterministic utility was introduced.
2. Prompt text remains externalized and prompt metadata stays complete.
3. Answer, annotation, witness, and trace projections still come from one execution path.
4. Public task ids, filenames, and module layout match the documented conventions.
5. Docs changed together with code/config/module-boundary changes.
6. Dead shims, stale exports, and orphaned helpers were removed during refactors.
7. Tests and task reviews cover the changed contract surface.

## Extra review checks for repo structure changes
- If docs move, update `docs/README.md`, `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, and any repo-local skills that point at the moved files.
- Keep docs canonical and skills thin; do not fork policy into parallel skill prose.

## Handoff
If the review finds a reusable issue, add a distilled rule to `docs/workflows/CODE_REVIEW_GUIDELINES.md`.
