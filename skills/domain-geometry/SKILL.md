---
name: domain-geometry
description: Use when designing, implementing, or reviewing TRACE geometry-domain tasks, especially for task-group conventions, annotation projections, and geometry shared-helper reuse.
---

# Geometry Domain

Use this whenever the task lives under `domain=geometry`.

## Read first
1. `docs/domains/SCENE_TASK_QUERY_GUIDE.md`
2. `docs/domains/GEOMETRY_TASK_SETUP.md`
3. `docs/ACTIVE_TASK_INVENTORY.md` for the generated active scene/task list.
4. `docs/project/STATUS.md`
5. `docs/workflows/TASK_AUTHORING.md`
6. `docs/workflows/SHARED_UTILITIES.md`

## Active-contract reminders
- `docs/domains/SCENE_TASK_QUERY_GUIDE.md` owns geometry family-boundary rules and the active geometry scene/query/annotation surface.
- Public identity follows `domain=geometry -> scene_id -> task_id`; task-internal semantic branches should be recorded in `query_id`.
- `scene_variant` may record visual or object-family axes inside a task, but it is not a public sampling unit.
- Measurement tasks use coordinate-grounded diagrams and geometry shared helpers.
- Analytical panel tasks answer with visible panel labels or option labels and ground annotation on the selected panel or supporting plotted objects.
- Comparison tasks use labeled objects with `option_letter` answers and winner annotation.
- Counting tasks use non-graph-paper multi-object scenes with unordered `bbox_set` annotation over the matched objects.
- Coordinate-relation tasks may use `point_set` annotation even for counting variants when the visible witness is an unlabeled point set on graph paper.
- Shared geometry logic belongs in `trace/tasks/geometry/shared/`; task-group shared code belongs inside the task-group package.

## Practical review checklist
- Prefer coordinate-grounded annotation when geometry itself is the source of truth.
- Reuse existing scene samplers/renderers before introducing a new object-family stack.
- Keep label placement collision-aware and matched to the object footprint; point labels should stay off the labeled point itself, other nearby markers, and the geometry lines/edges whenever a collision-free placement exists.
- If sibling geometry objectives reuse the same scene/prompt/trace flow, factor that into shared helpers instead of copying task-local logic.
- When refactoring geometry coverage, prefer adding `query_id` branches or safe `scene_variant` support inside an existing task only when the visual scaffold, reasoning algorithm, and answer/annotation contract stay the same.
- Add a fresh task id when the visual scaffold or answer/annotation contract materially changes.
