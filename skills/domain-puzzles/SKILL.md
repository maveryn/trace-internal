---
name: domain-puzzles
description: Use when designing, implementing, or reviewing TRACE puzzle-domain tasks, especially hidden-rule reasoning families and clean local evidence contracts for visual puzzle scenes.
---

# Puzzles Domain

Use this whenever the task lives under `domain=puzzles`.

## Read first
1. `docs/domains/PUZZLE_TASK_SETUP.md`
2. `docs/project/STATUS.md`
3. `docs/workflows/TASK_AUTHORING.md`
4. `docs/workflows/SHARED_UTILITIES.md`

## Active-contract reminders
- `docs/domains/PUZZLE_TASK_SETUP.md` owns the active puzzles contract.
- Treat puzzles as hidden-rule / hidden-variable reasoning tasks, not generic icon grids or mini tables.
- Define `task_group` by reasoning family: `arithmetic`, `logic`, `spatial`, `topology`, and later genuinely new puzzle families.
- Keep prompts explicit about the queried unknown, missing slot, target option, or equivalence rule.

## Practical review checklist
- Keep prompt-facing evidence simple and local: unknown slot, winning option, ordered visible-structure pair, or valid option images.
- Prefer `option_letter` answers for option-based puzzles and integer answers for explicit count/value puzzles.
- Add variants inside an existing task when the scene grammar and evidence contract stay the same.
- Split only when a new puzzle changes the visual grammar or witness semantics enough to be a healthy standalone task.
- Reuse puzzle helpers under `trace/tasks/puzzles/shared/` before adding task-local layout or rule-building utilities.
