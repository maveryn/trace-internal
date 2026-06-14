---
name: code-review
description: Use when reviewing TRACE changes for helper placement, duplication, contract drift, doc sync, or validation gaps before commit or merge.
---

# Code Review

Use this for implementation reviews, refactor reviews, and pre-merge checks.

## Read first
1. `docs/workflows/CODE_REVIEW_GUIDELINES.md`
2. `docs/contracts/SYSTEM_ARCHITECTURE.md`
3. `docs/SCENE_PACKAGE_MIGRATION/SCENE_MIGRATION_GUIDE.md` when reviewing scene-package migration work
4. `docs/contracts/BLUEPRINT.md`

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

## Stop conditions
- If the review uncovers unclear task/query boundaries, switch to
  `skills/task-unit-audit/SKILL.md` before approving implementation shape.
- If the patch changes generated artifacts or reviewer issues, include
  `skills/verification-review/SKILL.md`.

## Handoff
If the review finds a reusable issue, update the relevant source-of-truth doc. Update `docs/workflows/CODE_REVIEW_GUIDELINES.md` only when the compact repo-wide checklist itself needs a new rule.
