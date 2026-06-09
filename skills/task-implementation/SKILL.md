---
name: task-implementation
description: Use when implementing or refactoring TRACE task code, wiring configs and registration, or deciding helper placement and module layout.
---

# Task Implementation

Use this when turning a TRACE task design into code.

## Read first
1. `docs/core/SYSTEM_ARCHITECTURE.md`
2. `docs/workflows/TASK_AUTHORING.md`
3. `docs/workflows/SHARED_UTILITIES.md`
4. `docs/workflows/CODE_DOCUMENTATION.md`

If the task is domain-specific, also open the matching domain setup doc and `skills/domain-<domain>/SKILL.md`.

## Implementation workflow
1. Choose module placement before writing code.
   - Default task layout: `trace/tasks/<domain>/<task_group>/<task_name>.py`
   - Cell-board puzzle implementations live under `trace/tasks/puzzles/cell_board/`
2. Search for reusable helpers before adding new logic:
   - `trace/core/`
   - `trace/tasks/shared/`
   - `trace/tasks/<domain>/shared/`
   - domain-specific shared folders
3. Put new helpers at the narrowest reusable layer that fits.
4. Keep prompt text out of task modules and wire bundle/config keys instead.
5. Register the task and import it from `trace/tasks/__init__.py`.
6. Keep trace, projected annotation, and public answer/annotation derived from the same execution path.
7. Update docs in the same patch when module boundaries or helper placement change.

## Implementation checks
- Determinism must hold for fixed seed/spec inputs.
- Do not add hidden randomness or silent constraint relaxation.
- Remove stale wrappers and dead re-exports after refactors.
- If a second task reuses task-local logic, promote it in the same patch.

## Handoff
After code and docs are in place, move to:
- `skills/prompt-design/SKILL.md` for prompt wiring changes.
- `skills/verification-review/SKILL.md` for tests and task reviews.
