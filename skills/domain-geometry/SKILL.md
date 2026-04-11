---
name: domain-geometry
description: Use when designing, implementing, or reviewing TRACE geometry-domain tasks, especially for task-group conventions, evidence projections, and geometry shared-helper reuse.
---

# Geometry Domain

Use this whenever the task lives under `domain=geometry`.

## Read first
1. `docs/domains/TASK_FAMILY_VARIANTS.md`
2. `docs/project/STATUS.md`
3. `docs/workflows/TASK_AUTHORING.md`
4. `docs/workflows/SHARED_UTILITIES.md`

## Active-contract reminders
- `docs/domains/TASK_FAMILY_VARIANTS.md` owns geometry family-boundary rules and the active geometry scene/query/evidence surface.
- Active geometry tasks follow a chart-style two-axis contract: `scene_variant` names the geometric scene family, while `query_variant` names the requested question type.
- Measurement tasks use graph-paper-style coordinate grounding and geometry shared helpers.
- Analytical 2D / 3D tasks use symbolic `ANNOTATION=VALUE` `label_set` evidence.
- Comparison tasks use labeled objects with `option_letter` answers and winner evidence.
- Counting tasks use non-graph-paper multi-object scenes with unordered `label_set` evidence when labels are the canonical witness.
- Coordinate-relation tasks may use `graph_point_set` evidence even for counting variants when the visible witness is an unlabeled point set on graph paper.
- Shared geometry logic belongs in `trace/tasks/geometry/shared/`; task-group shared code belongs inside the task-group package.

## Practical review checklist
- Prefer coordinate-grounded evidence when geometry itself is the source of truth.
- Reuse existing scene samplers/renderers before introducing a new object-family stack.
- Keep label placement collision-aware and matched to the object footprint; point labels should stay off the labeled point itself, other nearby markers, and the geometry lines/edges whenever a collision-free placement exists.
- If sibling geometry objectives reuse the same scene/prompt/trace flow, factor that into shared helpers instead of copying task-local logic.
- When refactoring geometry coverage, prefer widening `query_variant` or `scene_variant` support inside the existing geometry surface before adding new geometry task ids; add a fresh task id only when the visual scaffold or answer/evidence contract materially changes (as with the newer transformation, similarity, and coordinate-relation families).
