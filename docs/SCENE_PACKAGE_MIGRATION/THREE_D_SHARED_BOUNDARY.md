# Three_D Shared Boundary

Use this with `SCENE_MIGRATION_GUIDE.md` when preparing or migrating a
`three_d` scene.

## Purpose

The `three_d` domain has unusually broad reusable object infrastructure:
canonical object resources, projected 3D glyphs, camera/projection math, option
panels, room/street/warehouse object renderers, and object-inventory review
previews. Scene-package migration must separate three layers:

- true `three_d` domain primitives reused by multiple unrelated scenes;
- one scene's spatial grammar, camera constraints, layout, shell/support
  rendering, and reusable scene primitives;
- public task objective code that owns query selection, answer binding,
  annotation binding, prompt slots, task-specific trace fields, and final
  `TaskOutput`.

Public identity remains only:

```text
three_d -> scene_id -> task_id
task_three_d__<scene_id>__<objective_contract>
```

## Status And Inventory

Use `docs/ACTIVE_TASK_INVENTORY.md` for active `three_d` scenes and task
counts. Use scene review artifacts and browser-app human review for migration
status. This document defines shared-code ownership only.

A scene-shaped source package, passing tests, manual source audit, review-ready
status, or review-candidate registration is not by itself accepted. Use
`migrated` only after the human reviewer accepts the scene in the browser app
and a receipt exists under
`review/task-reviews/three_d/<scene_id>/migration_receipt.json`.

## Lessons From Reference Scenes

`charts/annotated_series` keeps public task behavior explicit: the task file
owns the literal public task id, local query ids, target selection, answer,
annotation, prompt slots, trace fields, and final `TaskOutput`. Scene `shared/`
owns state, sampling, rendering, annotation projection, prompt assembly, and
trace scaffolding only.

`games/2048` uses `_lifecycle.py` because several public tasks share a real
scene lifecycle. That private file is acceptable only because public task files
pass objective-owned hooks and support values. The lifecycle does not choose
behavior by public task id or query id.

`illustrations/construction_site` keeps scene grammar local while reusable
object/person drawing stays domain-shared. `three_d` should follow the same
object-rendering split: scenes own placement and verifier semantics; domain
shared owns reusable object identity and renderer implementations.

## Domain Shared

`trace/tasks/three_d/shared/` is for scene-neutral primitives reused by
multiple unrelated `three_d` scenes. It must not know or branch on public task
ids, public query ids, objective contracts, registered task classes, sibling
scene identities, task-specific answer schemas, or task-specific prompt
wording. It must not construct final public `TaskOutput`.

Approved domain-shared categories:

- camera/projection math, floor-plane projection, vector operations, and
  visibility geometry used by multiple scenes;
- deterministic non-semantic color/style variation for 3D objects;
- canonical named-object resources: profile ids, canonical ids, prompt-facing
  names, scene-role profiles, dimensions, renderers, resource kinds, support
  and mounting metadata;
- normalized 3D object records and renderer-neutral placement/style specs;
- renderer-neutral reusable object dispatch and serialization;
- projected loose-object glyphs used by object-scene and object-cluster style
  scenes;
- reusable room wall/floor object renderers;
- reusable street vehicle, pedestrian, fixture, and landscape object renderers;
- reusable warehouse loose-object renderers;
- scene-neutral option-panel layout and option-choice metadata;
- object-inventory preview helpers for resource review.

Domain-shared modules that should generally remain domain-shared:

| Module | Target role |
|---|---|
| `camera_projection.py` | Camera, projection, floor-plane, and vector math. |
| `color_variation.py` | Non-semantic object fill variation. |
| `object_resources.py` | Canonical 3D object resource registry and scene-role profiles. |
| `object_schema.py` | Normalized `ThreeDObjectRecord` payload. |
| `scene_schema.py` | Renderer-neutral placement/style specs. |
| `object_variants.py` | Renderer-style and render-only variant metadata. |
| `projected_object_geometry.py` | Scene-neutral object reference points, projected bbox, and bbox-overlap geometry. |
| `object_rendering.py` | Shared object renderer dispatch and object-record construction. |
| `object_inventory_preview.py` | Native preview routing for canonical object profiles. |
| `option_panel.py` | Scene-neutral visual option panel layout and prompt-color assignment. |
| `object_scene_primitives.py` | Low-level projected-object drawing primitives, after renaming/review if needed. |
| `object_scene_glyphs_*.py` | Reusable projected loose-object glyphs, after renaming/review if needed. |
| `object_scene_rendering.py` | Reusable projected-object draw dispatch only; object-scene room/platform shell drawing is scene-local. |
| `room_wall_rendering_geometry.py` | Shared wall projection/drawing geometry. |
| `room_wall_object_rendering.py`, `room_floor_object_rendering.py` | Reusable room object renderers. |
| `street_*_object_rendering*.py` | Reusable street object renderers and object geometry helpers. |
| `warehouse_object_rendering.py` | Reusable loose warehouse object renderer. |

## Legacy Shared File Guidance

Use this as a boundary guide for `trace/tasks/three_d/shared/` before
scene-by-scene package migration. Do not treat it as migration status.

| File | Classification | Required action before or during scene migration |
|---|---|---|
| `__init__.py` | `keep_shared` | Empty package marker; keep. |
| `camera_projection.py` | `keep_shared` | Keep as domain projection/vector math. |
| `color_variation.py` | `keep_shared` | Keep as non-semantic object color variation. |
| `object_schema.py` | `keep_shared` | Keep as normalized rendered-object payload schema. |
| `scene_schema.py` | `keep_shared` | Keep as renderer-neutral placement/style schema. |
| `object_variants.py` | `keep_shared` | Keep as renderer/style variant metadata. |
| `option_panel.py` | `keep_shared` | Keep as scene-neutral visual option-panel helper. |
| `projected_object_geometry.py` | `keep_shared` | Owns scene-neutral object reference-point, projected-bbox, and bbox-overlap helpers extracted from `object_scene.py`. |
| `object_rendering.py` | `keep_shared_with_legacy_names` | Keep renderer dispatch and object-record construction. It currently imports `object_scene_rendering`; after rendering cleanup, point it at scene-neutral projected-object modules. |
| `object_inventory_preview.py` | `keep_shared_resource_review` | Keep for review-app resource previews only. Internal preview payloads may contain non-public `query_id` labels; do not expand this into task/query routing. |
| `object_resources.py` | `keep_shared_after_dependency_cleanup` | Keep canonical object profiles and resource metadata. Stable surface-fixture resource ids/display names are now owned locally by this registry; domain shared must not import scene shared. |
| `object_landmarks.py` | `move_scene_local_unless_reused` | Currently used only by `object_scene/landmark_correspondence_label.py`. Move into `object_scene/shared/landmarks.py` unless another scene adopts the same landmark contract. |
| `task_support.py` | `partially_narrowed_legacy_wrappers` | Namespace-based helpers now exist for axis/count sampling. Legacy `task_id` wrappers remain for unmigrated code only and should not be used by review-candidate scenes. |
| `object_scene.py` | `split_legacy_mixed_shared` | Generic projected-object geometry has been extracted to `projected_object_geometry.py` and re-exported for compatibility. Move object-scene constants, render params, sample construction, room/platform rendering orchestration, prompt-name safety, and answer-candidate semantics into `object_scene/shared/`. |
| `object_scene_rendering.py` | `keep_shared_after_room_split` | Keep projected-object draw dispatch and low-level label/line/bbox helpers under scene-neutral names. Object-scene room/platform behavior now lives in `object_scene/shared/rendering.py`. |
| `object_scene_primitives.py` | `keep_shared_rename_later` | Keep low-level projected-object drawing primitives. Rename to a scene-neutral name such as `projected_object_primitives.py` after import churn is controlled. |
| `object_scene_glyphs_household.py` | `keep_shared_rename_later` | Keep reusable projected loose-object glyphs; rename away from `object_scene_` prefix later. |
| `object_scene_glyphs_large.py` | `keep_shared_rename_later` | Keep reusable large-object glyph re-exports; rename away from `object_scene_` prefix later. |
| `object_scene_glyphs_large_appliances.py` | `keep_shared_rename_later` | Keep reusable appliance glyphs; rename away from `object_scene_` prefix later. |
| `object_scene_glyphs_large_furniture.py` | `keep_shared_rename_later` | Keep reusable furniture glyphs; rename away from `object_scene_` prefix later. |
| `object_scene_glyphs_large_stage.py` | `keep_shared_rename_later` | Keep reusable stage/support glyphs; rename away from `object_scene_` prefix later. |
| `object_scene_glyphs_misc.py` | `keep_shared_rename_later` | Keep reusable miscellaneous glyphs; rename away from `object_scene_` prefix later. |
| `object_scene_glyphs_nature_apparel.py` | `keep_shared_rename_later` | Keep reusable nature/apparel glyphs; rename away from `object_scene_` prefix later. |
| `object_scene_glyphs_symbolic.py` | `keep_shared_rename_later` | Keep reusable symbolic glyphs; rename away from `object_scene_` prefix later. |
| `object_scene_glyphs_tools_devices.py` | `keep_shared_rename_later` | Keep reusable tools/devices glyphs; rename away from `object_scene_` prefix later. |
| `room_wall_rendering_geometry.py` | `keep_shared` | Keep wall-plane projection and wall-object drawing geometry. |
| `room_wall_object_rendering.py` | `keep_shared` | Keep reusable wall-mounted room object renderers. |
| `room_floor_object_rendering.py` | `keep_shared` | Keep reusable floor-standing room object renderers. |
| `street_object_rendering_common.py` | `split_shared_and_scene_local` | Keep generic street object geometry and renderer helpers. Move intersection-layout helpers such as road-arm presence and missing-arm logic into `street/shared/` during street migration. |
| `street_object_rendering.py` | `keep_shared` | Keep street renderer dispatch for context and candidate objects. |
| `street_vehicle_object_rendering.py` | `keep_shared` | Keep reusable vehicle renderers. |
| `street_pedestrian_object_rendering.py` | `keep_shared` | Keep reusable pedestrian renderer. |
| `street_fixture_object_rendering.py` | `keep_shared` | Keep reusable street fixture renderers. |
| `street_landscape_object_rendering.py` | `keep_shared` | Keep reusable landscape renderers. |
| `warehouse_object_rendering.py` | `keep_shared` | Keep reusable loose warehouse object renderer and robot/object drawing utilities. |

Domain-shared modules that require narrowing before scenes can become
review-candidate scenes:

- `task_support.py` now exposes identity-free namespace helpers for migrated
  code: `resolve_axis_variant_for_namespace(...)` and
  `resolve_count_for_namespace(...)`. The legacy `resolve_axis_variant(...)`
  and `resolve_count(...)` wrappers still accept `task_id` for unmigrated code
  only. Do not use those wrappers in review-candidate `three_d` scenes.
- `object_scene.py` currently still owns object-scene visual grammar, scene
  constants, render params, placement slots, sample construction, and renderer
  orchestration. Generic projected-object geometry has been moved to
  `projected_object_geometry.py`; the remaining object-scene pieces belong in
  `trace/tasks/three_d/object_scene/shared/`.
- `object_scene_rendering.py` has been narrowed to projected-object draw
  dispatch plus low-level label/line/bbox helpers. Object-scene room/platform
  shell behavior now lives in `object_scene/shared/rendering.py`.

## Scene Shared

`trace/tasks/three_d/<scene_id>/shared/` owns one scene's spatial grammar and
reusable scene primitives.

Recommended `three_d` scene-shared role files:

- `state.py`
- `defaults.py`
- `sampling.py`
- `layout.py`
- `projection.py`
- `rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`
- `objects.py`
- `relations.py`
- `metrics.py`
- `components.py`
- `labels.py`
- `styles.py`
- `option_rendering.py`
- `spatial_primitives.py`

The matching scene-package file policy should allow only these direct role
files inside a scene `shared/` package, plus `__init__.py`, and should allow
only `_lifecycle.py` as a private scene-root file. Shared subdirectories should
stay disabled unless a later scene has a documented need for a narrower
package.

Scene shared may know its scene's visual grammar: dense tabletop clusters,
object-scene floor/table/platform layouts, surface-fixture panels, room walls,
street intersections, or warehouse aisles. It must not route behavior by public
task id, public query id, objective contract, public task name, or registered
class.

Scene shared must not:

- accept or branch on public `task_id`;
- accept or branch on public `query_id`;
- export public query-id routing tables;
- register public tasks;
- construct final public `TaskOutput`;
- contain task-named runtime files;
- hide copied public task bodies.

If a helper needs to know which public query branch is running, the public task
file should resolve the branch to neutral semantic arguments and pass those
arguments into shared code.

Example:

- Bad shared argument: `query_id="closer_to_camera_than_reference_count"`.
- Good shared arguments: `depth_comparator="closer_than_reference"`,
  `reference_object_id="obj_04"`, `candidate_object_ids=[...]`.

## Public Task Files

Each public task file owns one objective contract:

- literal public `TASK_ID`;
- `SCENE_ID`;
- local `SUPPORTED_QUERY_IDS`;
- query selection and query validation;
- objective-specific sampling constraints;
- target/candidate construction when objective-specific;
- answer binding;
- `annotation_gt` binding;
- dynamic prompt slots and prompt/query key selection;
- task-specific trace fields;
- retry behavior and final `TaskOutput`.

Public task files may call scene-shared and domain-shared primitives. They must
not remain thin wrappers around shared base classes whose behavior changes only
through class attributes, public task ids, forced query ids, or task-specific
tables in shared code.

Use `_lifecycle.py` only when several public tasks in the same scene share a
real lifecycle. The lifecycle must accept objective-owned hooks or prepared
semantic values from public task files. It must not choose objective behavior
by public task id or query id.

## Current Decomposition Targets

### `object_scene`

Move object-scene grammar out of `three_d/shared/object_scene.py` into
`object_scene/shared/` role files:

- scene constants, dataclasses, supported scene variants -> `state.py`;
- render defaults and render-param resolution -> `defaults.py`;
- camera/sample/placement helpers -> `sampling.py`, `layout.py`, `projection.py`;
- floor/table/platform shell drawing now starts in `rendering.py`; final scene
  rendering orchestration should move there during full scene migration;
- trace scaffolding and render maps -> `output.py`;
- object-scene-specific object filters and prompt-name safety -> `objects.py`;
- relation/count helpers -> `relations.py`, `metrics.py`.

Decompose `object_scene/shared/logical_predicate_count.py` and
`object_scene/shared/view_relation_count.py`. They currently behave as
objective bases. Public task files should own the predicate/relation query
selection, answer count, annotation set, prompt slots, and final output.

Keep reusable projected loose-object glyphs and canonical resource metadata in
domain shared.

### `object_cluster`

Keep dense-cluster scene grammar under `object_cluster/shared/`, but role-split
the current broad helpers:

- cluster state and composition mode metadata -> `state.py`;
- count/object/color support and target construction primitives -> `sampling.py`
  and `objects.py`;
- placement/readability/camera helpers -> `layout.py`, `projection.py`;
- rendering wrappers over domain-shared object rendering -> `rendering.py`;
- predicate helpers that accept neutral predicate specs -> `relations.py`;
- count/arithmetic/frequency metrics -> `metrics.py`;
- common trace scaffolding -> `output.py`;
- annotation projection helpers -> `annotations.py`.

`predicate_counts.py` must not remain a shared public-task base. It currently
routes by task id/query id and constructs `TaskOutput`.

### `surface_fixture`

Keep fixture-panel drawing in scene shared, but decompose `shared/task_base.py`:

- fixture scene state and element catalogs -> `state.py`;
- grid/layout/cell helpers -> `layout.py`;
- panel rendering -> `rendering.py`;
- objective-neutral sampling helpers -> `sampling.py`;
- adjacency/state/color/missing-cell metrics -> `metrics.py`, `relations.py`;
- annotation helpers -> `annotations.py`;
- common trace scaffolding -> `output.py`.

Public task files must own each objective's query ids, target element/state/color
selection, answer binding, annotation binding, prompt slots, and final output.

### `room`

Move scene-root helper modules into `room/shared/` role files:

- `wall_mounted_common.py` -> `state.py`, `layout.py`, `projection.py`,
  `objects.py`, `relations.py`, `metrics.py`;
- `wall_mounted_dataset.py` -> `sampling.py`;
- `wall_mounted_rendering.py` -> `rendering.py`, `components.py`, `output.py`.

Room walls, floor continuation, furniture/support surfaces, wall-object
placement, and room-specific camera constraints are scene-local. Reusable room
wall/floor object drawing stays in `three_d/shared/`.

### `street`

Move intersection scene helpers into `street/shared/` role files:

- `intersection_scene.py` -> `state.py`, `defaults.py`, `layout.py`,
  `projection.py`, `objects.py`, `relations.py`, `metrics.py`;
- `intersection_rendering.py` -> `rendering.py`, `annotations.py`,
  `option_rendering.py`, `output.py`;
- `intersection_road_rendering.py` and `intersection_building_rendering.py`
  -> `components.py` or focused role files if allowed by policy.

Road topology, intersection-center jitter, lane/road-arm semantics, arrows,
markers, sidewalks, crosswalks, and buildings are street-local. Reusable
vehicles, pedestrians, fixtures, and landscape object drawing stays
domain-shared.

### `warehouse`

Move warehouse scene helpers into `warehouse/shared/` role files:

- `warehouse_scene_common.py` -> `state.py`, `defaults.py`, `layout.py`,
  `projection.py`, `objects.py`, `relations.py`, `metrics.py`;
- `warehouse_rendering.py`, `warehouse_shelf_rendering.py`, and
  `warehouse_support_rendering.py` -> `rendering.py`, `components.py`,
  `annotations.py`, `option_rendering.py`, `output.py`.

Warehouse aisles, robot headings/path corridors, shelf-rack levels, shelf-item
layout, arrows, rack frames, and floor/support drawing are warehouse-local.
Reusable loose warehouse objects stay domain-shared.

## Suggested Migration Order

Use this order unless a task-specific priority overrides it:

1. Add the `three_d` scene-package file policy and keep migration registries
   unchanged.
2. Migrate one small scene first, preferably `surface_fixture`, to validate the
   policy and role-file names.
3. Migrate `object_cluster`, because it exercises shared object rendering and
   the strongest current shared-base violation.
4. Migrate `object_scene`, after splitting `three_d/shared/object_scene.py`.
5. Migrate `room`, `street`, and `warehouse`, preserving reusable object
   renderer ownership in domain shared.

Do not add all `three_d` scenes to review-candidate registries at once. Register
one scene only after its source boundary is cleaned enough for migration gates.

## Review Gates

Before task-review generation for a `three_d` scene:

1. Source-audit the scene against this document and `SCENE_MIGRATION_GUIDE.md`.
2. Confirm public files own objective/query logic and final output.
3. Confirm scene `shared/` is role-split and identity-free.
4. Confirm configs do not route task/query behavior.
5. Smoke-generate every task and every supported query branch.
6. Run the scoped migration/review command from `ENFORCEMENT_TESTS.md`.
7. Record manual code audit and migration test status under
   `review/task-reviews/three_d/<scene_id>/`.
8. Generate fresh review artifacts under `review/task-reviews/`.
9. Reload the review app index.
10. Wait for human browser review and acceptance before calling the scene
    migrated or writing a receipt.
