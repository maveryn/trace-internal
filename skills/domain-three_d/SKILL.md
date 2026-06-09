---
name: domain-three_d
description: Use when designing, implementing, or reviewing TRACE three_d-domain tasks, especially perspective 3D scenes with camera/projection metadata and spatial annotation contracts.
---

# Three-D Domain

Use this whenever the task lives under `domain=three_d`.

## Read first
1. `docs/domains/THREE_D_TASK_SETUP.md`
2. `docs/ACTIVE_TASK_INVENTORY.md` for the generated active scene/task list.
3. `docs/project/STATUS.md`
4. `docs/workflows/TASK_AUTHORING.md`
5. `docs/workflows/SHARED_UTILITIES.md`

## Active-contract reminders
- `docs/domains/THREE_D_TASK_SETUP.md` owns the active three_d contract.
- Scenes should read as proper 3D environments with explicit camera pose, world coordinates, projected pixel geometry, and metadata-grounded verifiers.
- Keep this domain separate from abstract 3D puzzle boards; use natural room/platform/object-scene context when possible.
- Answers must come from finalized 3D metadata such as camera distances, reference-object distances, heights, or occlusion order, not from pixel inference.
- Prompt-facing annotation should stay local to the decisive visible object, usually a `bbox_set` in final-image pixel coordinates.
- Closely related query stems over the same scene and annotation contract should be `query_id` variants inside one public task.

## Practical review checklist
- Verify camera pose, projection frame, world coordinates, projected bboxes, and solver trace are recorded from the same execution trace.
- Ensure sampled objects are visually separated enough after projection and have unique answers by construction.
- Keep style, room, and surface variants non-semantic unless the task explicitly reasons over them.
- Promote camera/projection/room helpers to `trace/tasks/three_d/shared/` once a second task needs them.
- Keep task modules drawing-free when a scene-local renderer module exists: sampling, prompt/trace assembly, and verifier construction stay in the task; PIL/ImageDraw code, marker overlays, panel composition, and projected fixture drawing stay in focused `*_rendering.py` modules.
- Room task modules use `wall_mounted_common.py` and `wall_mounted_dataset.py` for geometry/sampling/data construction, while `wall_mounted_rendering.py` owns PIL/ImageDraw scene orchestration and the rendered-scene result type.
- Warehouse task modules use `warehouse_scene_common.py` for scene geometry/sampling, `warehouse_rendering.py` for robot forward/nearest rendered scenes, `warehouse_shelf_rendering.py` for shelf-count rendered scenes, and `warehouse_support_rendering.py` only inside renderer modules for shelf-rack support drawing.
- Street task modules use `intersection_scene.py` for drawing-free scene geometry/sampling and `intersection_rendering.py` for final rendered scenes; keep road/building/shared street `_draw_*` helpers behind renderer modules, not public task modules.
