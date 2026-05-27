---
name: task-design
description: Use when designing or reshaping a TRACE task contract, choosing answer and evidence types, deciding task versus query_id placement, or planning sampling and balancing before implementation.
---

# Task Design

Use this before writing code for a new task or before changing a task's contract.

## Read first
1. `docs/core/BLUEPRINT.md`
2. `docs/workflows/TASK_AUTHORING.md`
3. `docs/domains/SCENE_TASK_QUERY_GUIDE.md`
4. `docs/project/STATUS.md`

If the task is domain-specific, also open the matching `docs/domains/*_TASK_SETUP.md` file and `skills/domain-<domain>/SKILL.md`.

If the task needs a new or revised difficulty policy, also open:
- `skills/task-complexity/SKILL.md`

## Design workflow
1. Confirm `domain`, `scene_id`, `task_group`, `task_id`, and whether the idea should be a new public task or a `query_id` inside an existing task.
2. Check `docs/project/STATUS.md` and `docs/tasks/README.md` so you do not create a near-duplicate scene.
3. Freeze the public contract before coding:
   - scene and query structure,
   - answer type,
   - evidence type,
   - uniqueness/rejection constraints,
   - trace payload additions.
4. Decide whether answer support depends on layout or board size.
   - If yes, prefer target-first sampling from feasible support instead of naive board-first sampling.
5. Decide what prompt bundle layers are needed:
   - scene,
   - task,
   - optional query,
   - output mode.
6. Decide which docs must change in the same patch:
   - task doc,
   - `docs/project/STATUS.md`,
   - `docs/TODO.md`,
   - domain/workflow docs if the new task changes reusable policy.

## Design checks
- Answer and evidence must come from the same execution path.
- Evidence should be as direct as possible; do not invent a weaker proxy if a canonical witness exists.
- Prefer reusing an existing task group unless the reasoning style is materially different.
- Keep prompt-facing contracts minimal; richer partitions and diagnostics can live in trace.

## Handoff
After the contract is stable, move to `skills/task-implementation/SKILL.md`.
