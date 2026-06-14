# Three_D Shared-Boundary Audit

Date: 2026-06-13

Purpose: define what belongs in `trace/tasks/three_d/shared/` before
scene-package migration starts for the `three_d` domain. This is a
source-boundary report, not a scene acceptance record. No `three_d` scene should
be marked migrated from this file alone.

## Boundary Rule

`trace/tasks/three_d/shared/` is for scene-neutral 3D-domain primitives:
projection math, canonical object resources, object schemas, renderer-neutral
placement specs, shared object renderer dispatch, reusable loose-object glyphs,
room/street/warehouse reusable object renderers, option panels, and resource
preview helpers.

`trace/tasks/three_d/<scene_id>/shared/` is for one scene's spatial grammar:
layout, camera constraints, shell/support rendering, target construction,
relation helpers, metrics, annotation projection, prompt-slot assembly, and
scene trace scaffolding.

Public task files own the objective contract: public task id, supported query
ids, query selection and validation, objective-specific constraints,
answer binding, annotation binding, dynamic prompt slots, task-specific trace
fields, retry behavior, and final `TaskOutput` construction.

## Domain Shared Decisions

The detailed file-by-file audit is maintained in
`docs/SCENE_PACKAGE_MIGRATION/THREE_D_SHARED_BOUNDARY.md`.

| Area | Decision | Action |
|---|---|---|
| Projection and vector math | Keep domain-shared. | `camera_projection.py` remains the common projection/math module. |
| Object resource registry | Keep domain-shared after dependency cleanup. | `object_resources.py` remains the domain object registry. Stable surface-fixture resource ids/display names are now owned locally by the registry; domain shared must not depend on scene shared. |
| Object schemas and placement specs | Keep domain-shared. | `object_schema.py`, `scene_schema.py`, and `object_variants.py` stay as domain contracts. |
| Object renderer dispatch | Keep with legacy names. | `object_rendering.py` stays. Later point it at scene-neutral projected-object modules instead of `object_scene_rendering`. |
| Projected glyphs and primitives | Keep, then rename later. | `object_scene_primitives.py` and `object_scene_glyphs_*.py` are reusable but misnamed. Rename only after import churn is controlled. |
| Projected object geometry | Keep domain-shared. | `projected_object_geometry.py` now owns scene-neutral reference-point, projected-bbox, and bbox-overlap helpers extracted from `object_scene.py`. |
| Object-scene assembly | Split. | `object_scene.py` still mixes object-scene grammar with compatibility re-exports. Move scene constants/render params/sample construction/shell orchestration into `object_scene/shared/`. |
| Object-scene rendering | Narrowed. | Keep generic draw dispatch, bbox/line/label helpers. Room/platform shell drawing now lives in `object_scene/shared/rendering.py`. |
| Landmark correspondence | Move scene-local unless reused. | `object_landmarks.py` is currently used only by `object_scene/landmark_correspondence_label.py`; move to `object_scene/shared/landmarks.py` unless a second scene adopts the contract. |
| Task support helpers | Partially narrowed; legacy wrappers remain. | `task_support.py` now exposes identity-free namespace helpers for axis/count sampling. Existing `task_id` wrappers remain only for unmigrated code and must not be used by review-candidate scenes. |
| Room object renderers | Keep domain-shared. | `room_wall_rendering_geometry.py`, `room_wall_object_rendering.py`, and `room_floor_object_rendering.py` are reusable object renderers. |
| Street object renderers | Keep but split layout logic. | Street vehicles, pedestrians, fixtures, landscape, and object dispatch stay shared. Intersection layout helpers in `street_object_rendering_common.py` should move scene-local during street migration. |
| Warehouse object renderer | Keep domain-shared. | `warehouse_object_rendering.py` stays as reusable loose warehouse object/robot drawing utilities. |
| Resource preview | Keep as review utility. | `object_inventory_preview.py` may carry internal preview labels but must not become task/query routing. |

## Scene Shared Target

Future `three_d` scene packages should use only these direct scene-shared role
files when needed:

```text
trace/tasks/three_d/<scene_id>/
  <objective_contract>.py
  _lifecycle.py          # optional, no objective routing
  shared/
    state.py
    defaults.py
    sampling.py
    layout.py
    projection.py
    rendering.py
    annotations.py
    prompts.py
    output.py
    objects.py
    relations.py
    metrics.py
    components.py
    labels.py
    styles.py
    option_rendering.py
    spatial_primitives.py
```

Avoid broad scene-shared files like `common.py`, `task_base.py`, and
objective-named shared bases in migrated scenes. Split them by role during that
scene's migration.

## Current Scene Inventory

| Scene | Current shared shape | Boundary action before or during migration |
|---|---|---|
| `surface_fixture` | Thin public task files plus `shared/task_base.py`, `shared/common.py`, and `shared/rendering.py`. | Decompose `task_base.py`; public files must own query/objective behavior and final output. |
| `object_cluster` | Public task files plus `shared/{attribute_count,instance_count,predicate_counts}.py`. | Keep dense-cluster grammar scene-local; decompose shared objective bases and move answer/annotation/prompt binding into public files. |
| `object_scene` | Public task files plus several scene-local helpers, with major grammar still in domain `shared/object_scene.py`. | Move object-scene grammar/render params/layout/render orchestration into `object_scene/shared/`; generic projected-object geometry is now in `projected_object_geometry.py`. |
| `room` | Scene root modules such as `wall_mounted_common.py`, `wall_mounted_dataset.py`, and `wall_mounted_rendering.py`. | Move root helpers into `room/shared/` role files; keep reusable wall/floor object drawing in domain shared. |
| `street` | Scene root intersection modules plus domain street object renderers. | Move intersection topology, road/building/shell rendering, and road-arm relation logic scene-local. Keep reusable vehicles/fixtures/pedestrians/landscape drawing domain-shared. |
| `warehouse` | Scene root warehouse scene/rendering modules plus domain warehouse object renderer. | Move aisle/shelf/robot path grammar and support rendering scene-local. Keep reusable loose warehouse object rendering domain-shared. |

## Immediate Pre-Migration Fixes

1. Keep migration registries unchanged; no `three_d` scene is review-candidate
   or migrated yet.
2. Use the new `three_d` scene-package file policy for future migration gates.
3. Use `resolve_axis_variant_for_namespace(...)` and
   `resolve_count_for_namespace(...)` in migrated scenes. Do not use the legacy
   public-`task_id` wrappers in review-candidate scenes.
4. Keep the scene-shared import out of `object_resources.py`; this is now
   guarded by a scoped migration contract test.
5. Continue splitting `object_scene.py` before registering `object_scene` as a
   review candidate; room/platform shell rendering has already moved scene-local.
6. Rename `object_scene_primitives.py` and `object_scene_glyphs_*.py` only in a
   controlled mechanical pass after the first small scene validates the policy.

## Checks Used For This Audit

- Listed all direct files under `trace/tasks/three_d/shared/`.
- Scanned `trace/tasks/three_d/shared/` for public task/query routing terms.
- Scanned scene imports of `object_scene.py`, `object_scene_rendering.py`, and
  `task_support.py`.
- Added and pinned the `three_d` scene-package file policy.

No task reviews, solve-rate jobs, or scene migrations were run for this audit.
