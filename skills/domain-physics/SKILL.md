---
name: domain-physics
description: Use when designing, implementing, or reviewing TRACE physics-domain tasks, especially simple diagram-first mechanics, circuits, and optics tasks with local annotation contracts.
---

# Physics Domain

Use this whenever the task lives under `domain=physics`.

## Read first
1. `docs/domains/PHYSICS_TASK_SETUP.md`
2. `docs/ACTIVE_TASK_INVENTORY.md` for the generated active scene/task list.
3. `docs/project/STATUS.md`
4. `docs/workflows/TASK_AUTHORING.md`
5. `docs/workflows/SHARED_UTILITIES.md`

## Active-contract reminders
- `docs/domains/PHYSICS_TASK_SETUP.md` owns the active mechanics/circuits/optics contract.
- Keep the domain diagram-first: the image should contain the operative values, directions, or placements needed to solve the task.
- Prefer visible, diagram-grounded arithmetic or formulas over hidden assumptions.
- Keep prompt-facing annotation local to the visible witness objects (force arrows, weights, resistors, target points, bounce points, etc.).
- For early mechanics tasks, keep vectors axis-aligned unless the task is explicitly about decomposition.
- When a task varies scene scaffold and semantic branch independently, record the visual scaffold in `scene_variant` and the semantic branch in `query_id`; `query_id` is internal replay metadata for narrowed public tasks.

## Practical review checklist
- Keep all required quantities visible or explicitly implied by the diagram; do not add hidden formula knowledge to tasks.
- Keep prompt-facing annotation on force arrows, weights, resistors, target points, bounce points, or other decisive witnesses, not decorative chrome.
- Prefer shared physics helpers under `trace/tasks/physics/shared/` and cross-domain sampling/support helpers before adding task-local utilities.
- Add new query ids inside an existing task when the scene scaffold and witness semantics stay the same.
- Split only when the scene grammar or answer/annotation contract changes enough to be a healthy standalone task.
