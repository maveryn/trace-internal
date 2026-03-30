---
name: domain-physics
description: Use when designing, implementing, or reviewing TRACE physics-domain tasks, especially simple diagram-first mechanics, circuits, and optics tasks with local evidence contracts.
---

# Physics Domain

Use this whenever the task lives under `domain=physics`.

## Read first
1. `docs/domains/PHYSICS_TASK_SETUP.md`
2. `docs/domains/TASK_FAMILY_VARIANTS.md`
3. `docs/project/STATUS.md`
4. `docs/workflows/TASK_AUTHORING.md`
5. `docs/workflows/SHARED_UTILITIES.md`

## V1 physics-domain policy
- Keep the domain diagram-first: the image should contain the operative values, directions, or placements needed to solve the task.
- Prefer light arithmetic over formula-heavy derivations in the first physics families.
- Keep prompt-facing evidence local to the visible witness objects (force arrows, weights, resistors, target points, bounce points, etc.).
- For early mechanics tasks, keep vectors axis-aligned unless the task is explicitly about decomposition.
- When a task varies scene scaffold and query type independently, use the chart-style `scene_variant` / `query_variant` split rather than one task id per question stem.

## Current coverage
- `mechanics`
  - `task_physics_mechanics_force_diagram`
  - `task_physics_mechanics_lever_balance`
- `circuits`
  - `task_physics_circuits_equivalent_resistance`
- `optics`
  - `task_physics_optics_ray_trace`

## Shared helpers to prefer
- `trace/tasks/shared/variant_sampling.py`
- `trace/tasks/physics/shared/circuit_scene.py`
- `trace/tasks/physics/shared/optics_scene.py`
- `trace/tasks/physics/shared/visual_defaults.py`
- `trace/tasks/physics/shared/complexity.py`
- `trace/tasks/physics/shared/style.py`
- `trace/tasks/physics/shared/support_sampling.py`
- `trace/tasks/shared/drawing.py`
- `trace/tasks/shared/graph_point_evidence.py`
- `trace/tasks/shared/text_rendering.py`

## Pair with
- `skills/task-design/SKILL.md`
- `skills/task-complexity/SKILL.md`
- `skills/task-implementation/SKILL.md`
- `skills/verification-review/SKILL.md`
