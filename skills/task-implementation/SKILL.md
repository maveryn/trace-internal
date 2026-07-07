---
name: task-implementation
description: Use when implementing or refactoring TRACE task code, wiring configs and registration, or deciding helper placement and module layout.
---

# Task Implementation

Use this when turning a TRACE task design into code.

## Read first
1. `docs/contracts/SYSTEM_ARCHITECTURE.md`
2. `docs/workflows/TASK_AUTHORING.md`
3. `docs/workflows/DOC_STRUCTURE.md`
4. `docs/contracts/SOURCE_LAYOUT.md`
5. `docs/workflows/DOCS_AND_SKILLS_MAINTENANCE.md`

If domain behavior matters, also open the matching `docs/domains/<domain>.md`.

## Implementation workflow
1. Choose module placement before writing code.
   - Current source layout:
     `trace/tasks/<domain>/<scene_id>/<objective_contract>.py`
   - Scene-local reusable code belongs under
     `trace/tasks/<domain>/<scene_id>/shared/`.
   - Domain shared code is only for real cross-scene reuse.
2. Search for reusable helpers before adding new logic:
   - `trace/core/`
   - `trace/tasks/shared/`
   - `trace/tasks/<domain>/shared/`
   - domain-specific shared folders
3. Put new helpers at the narrowest reusable layer that fits.
4. Keep prompt text out of task modules and wire bundle/config keys instead.
5. Register the task through the active registration path for that package; do
   not add compatibility aliases or broad eager imports.
6. Keep trace, projected annotation, and public answer/annotation derived from the same execution path.
7. Update docs in the same patch when module boundaries or helper placement change.

## Implementation checks
- Determinism must hold for fixed seed/spec inputs.
- Do not add hidden randomness or silent constraint relaxation.
- Remove stale wrappers and dead re-exports after refactors.
- If a second task reuses task-local logic, promote it in the same patch.

## Stop conditions
- If the task boundary or query split is unclear, stop implementation and use
  `skills/task-unit-audit/SKILL.md`.
- If prompt wording or JSON examples change, include
  `skills/prompt-design/SKILL.md`.
- If validation requires review artifacts, use
  `skills/verification-review/SKILL.md` before handing off.

## Handoff
After code and docs are in place, move to:
- `skills/prompt-design/SKILL.md` for prompt wiring changes.
- `skills/verification-review/SKILL.md` for tests and task reviews.
