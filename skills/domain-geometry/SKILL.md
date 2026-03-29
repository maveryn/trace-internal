---
name: domain-geometry
description: Use when designing, implementing, or reviewing TRACE geometry-domain tasks, especially for task-group conventions, evidence projections, and geometry shared-helper reuse.
---

# Geometry Domain

Use this whenever the task lives under `domain=geometry`.

## Read first
1. `docs/project/STATUS.md`
2. `docs/core/SYSTEM_ARCHITECTURE.md`
3. `docs/workflows/TASK_AUTHORING.md`
4. `docs/workflows/SHARED_UTILITIES.md`

## Geometry-domain rules
- Geometry currently uses five consolidated value tasks plus two distinct visual families: `task_geometry_measurement_value`, `task_geometry_comparison_value`, `task_geometry_counting_value`, `task_geometry_analytical_2d_value`, `task_geometry_analytical_3d_value`, `task_geometry_transformation_match`, and `task_geometry_similarity_count`.
- Active geometry tasks follow a chart-style two-axis contract: `scene_variant` names the geometric scene family, while `query_variant` names the requested question type.
- Measurement tasks use graph-paper-style coordinate grounding and geometry shared helpers.
- Analytical 2D / 3D tasks use structured `measurement_ref_map` evidence.
- Comparison tasks use labeled objects with `option_letter` answers and winner evidence.
- Counting tasks use non-graph-paper multi-object scenes with unordered `label_set` evidence when labels are the canonical witness.
- Shared geometry logic belongs in `trace/tasks/geometry/shared/`; task-group shared code belongs inside the task-group package.

## Design heuristics
- Prefer coordinate-grounded evidence when geometry itself is the source of truth.
- Reuse existing scene samplers/renderers before introducing a new object-family stack.
- Keep label placement collision-aware and matched to the object footprint.
- If sibling geometry objectives reuse the same scene/prompt/trace flow, factor that into shared helpers instead of copying task-local logic.
- When refactoring geometry coverage, prefer widening `query_variant` or `scene_variant` support inside the existing geometry surface before adding new geometry task ids; add a fresh task id only when the visual scaffold or answer/evidence contract materially changes (as with the new transformation and similarity families).

## Coverage reference
For current geometry coverage and active task families, use:
- `docs/project/STATUS.md`
- `docs/domains/TASK_FAMILY_VARIANTS.md`

## Pair with
- `skills/task-design/SKILL.md`
- `skills/task-complexity/SKILL.md`
- `skills/task-implementation/SKILL.md`
- `skills/verification-review/SKILL.md`
