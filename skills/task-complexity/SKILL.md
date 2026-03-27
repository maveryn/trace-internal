---
name: task-complexity
description: Use when defining or revising TRACE task complexity policy, especially for within-task normalized difficulty, domain-level complexity criteria, task-group weight overrides, and migration away from ad hoc scalar `complexity_score` formulas.
---

# Task Complexity

Use this whenever a change touches `complexity_score`, `complexity_components`, curriculum buckets, or domain/task-family difficulty policy.

## Read first
1. `docs/workflows/TASK_AUTHORING.md`
2. `docs/workflows/CODE_REVIEW_GUIDELINES.md`
3. `docs/project/STATUS.md`
4. `docs/project/TODO.md`

## Core policy
- Treat `complexity_score` as **within-task normalized difficulty only**.
- Make tasks emit normalized criterion values in `[0,1]`; do not compare raw scores across tasks or domains.
- Keep raw-to-normalized transforms in task/domain code, not in config.
- Let config own **weights and active criteria**, with precedence `domain -> task_group -> task`.
- Use domain defaults for the base criteria vocabulary, task-group overrides for emphasis, and task overrides only when a task materially breaks the family pattern.
- Treat existing one-off scalar formulas as legacy. Do not copy them forward when touching a task.

## Workflow
1. Open the domain reference from `references/` and choose the criteria vocabulary for that domain.
2. Decide the default domain weights and any task-group override weights.
3. In the task code, measure each active criterion and normalize it into `[0,1]`.
4. Keep any raw diagnostics in trace/debug payloads, not in `complexity_components`.
5. Compute the final score from the resolved weights over the normalized criterion values.
6. Check monotonicity against the task's obvious difficulty knobs before finalizing.

## Read as needed
- General policy and config shape: `references/policy.md`
- Geometry: `references/geometry.md`
- Icons: `references/icons.md`
- Tile: `references/tile.md`
- Charts: `references/charts.md`
- Tables: `references/tables.md`

## Update discipline
- When adding a new domain or task family, add or update the corresponding domain reference in this skill in the same change.
- When introducing a new criterion name, update the domain reference before using it in task code.
- When migrating a legacy task, preserve the task's relative easy/medium/hard ordering as closely as possible while moving to named normalized criteria.

## Pair with
- `skills/task-design/SKILL.md`
- `skills/task-implementation/SKILL.md`
- relevant domain skills under `skills/domain-*/SKILL.md`
