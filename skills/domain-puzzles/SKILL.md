---
name: domain-puzzles
description: Use when designing, implementing, or reviewing TRACE puzzles-domain tasks, especially hidden-rule reasoning families and clean local annotation contracts for visual puzzle scenes.
---

# Puzzles Domain

Use this whenever the task lives under `domain=puzzles`.

## Read first
1. `docs/domains/PUZZLES_TASK_SETUP.md`
2. `docs/ACTIVE_TASK_INVENTORY.md` for the generated active scene/task list.
3. `docs/project/STATUS.md`
4. `docs/workflows/TASK_AUTHORING.md`
5. `docs/workflows/SHARED_UTILITIES.md`
6. `docs/workflows/PUZZLE_GAME_RENDERING_UPGRADE.md` when touching repeated-cell, board, sticker, or voxel scenes

## Active-contract reminders
- `docs/domains/PUZZLES_TASK_SETUP.md` owns the active puzzles contract.
- Treat `cell_board` as a puzzle scene.
- Treat puzzles as hidden-rule / hidden-variable reasoning tasks, not generic icon grids or mini tables.
- Define `task_group` by reasoning family: `arithmetic`, `logic`, `spatial`, `topology`, and later genuinely new puzzle families.
- Keep prompts explicit about the queried unknown, missing slot, target option, or equivalence rule.

## Practical review checklist
- Keep prompt-facing annotation simple and local: unknown slot, winning option, ordered visible-structure pair, or valid option images.
- Prefer `option_letter` answers for option-based puzzles and integer answers for explicit count/value puzzles.
- Add variants inside an existing task when the scene grammar and annotation contract stay the same.
- Split only when a new puzzle changes the visual grammar or witness semantics enough to be a healthy standalone task.
- Reuse puzzle helpers under `trace/tasks/puzzles/shared/` before adding task-local layout or rule-building utilities.
- For cell-board implementation work, follow the `puzzles/cell_board` section in `docs/domains/PUZZLES_TASK_SETUP.md` and the board-rendering checklist.
