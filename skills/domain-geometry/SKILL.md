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
- Measurement tasks use graph-paper-style coordinate grounding and geometry shared helpers.
- Analytical 2D tasks use solid non-graph-paper scenes with structured `measurement_ref_map` evidence.
- Comparison tasks use labeled objects with `option_letter` answers and winner evidence.
- Counting tasks use non-graph-paper multi-object scenes with sorted `label_set` evidence when labels are the canonical witness.
- Shared geometry logic belongs in `trace/tasks/geometry/shared/`; task-group shared code belongs inside the task-group package.

## Design heuristics
- Prefer coordinate-grounded evidence when geometry itself is the source of truth.
- Reuse existing scene samplers/renderers before introducing a new object-family stack.
- Keep label placement collision-aware and matched to the object footprint.
- If sibling geometry objectives reuse the same scene/prompt/trace flow, factor that into shared helpers instead of copying task-local logic.

## Coverage reference
For current geometry coverage and active task families, use:
- `docs/project/STATUS.md`
- `docs/domains/TASK_FAMILY_VARIANTS.md`

## Pair with
- `skills/task-design/SKILL.md`
- `skills/task-complexity/SKILL.md`
- `skills/task-implementation/SKILL.md`
- `skills/verification-review/SKILL.md`
