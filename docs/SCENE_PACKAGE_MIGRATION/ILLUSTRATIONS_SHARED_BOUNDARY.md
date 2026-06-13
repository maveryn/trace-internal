# Illustrations Shared Boundary

Use this with `SCENE_MIGRATION_GUIDE.md` when migrating an illustrations scene.

## Purpose

The illustrations domain already exposes public taxonomy as:

```text
illustrations -> scene_id -> task_id
task_illustrations__<scene_id>__<objective_contract>
```

The source layout is only partially aligned with that taxonomy. Several public
scenes still depend on scene-specific modules under
`trace/tasks/illustrations/shared/`, and some public task files are wrappers
around private branch tasks. Scene-package migration must separate three layers:

- true illustration-domain primitives reused by unrelated scenes;
- one scene's visual grammar and reusable scene primitives;
- public task objective code that owns query selection, answer binding,
  annotation binding, prompt slots, and final `TaskOutput`.

Old implementation folders such as `counting` are not public taxonomy nodes.
During migration, each public scene gets its own package under:

```text
trace/tasks/illustrations/<scene_id>/
```

## Current Domain Inventory

The current registry has 9 active illustrations scenes and 23 active public
tasks.

| Scene | Active tasks | Current source shape | Boundary notes |
|---|---:|---|---|
| `construction_site` | 3 | migrated scene package with role-split scene-local `shared/{state,labels,layout,rendering,annotations,output,sampling}.py` | Zone, worker, equipment, material, and site-layout grammar is scene-local. Reusable object/person drawing remains domain-shared. |
| `environment` | 4 | implemented under `counting/` plus `shared/environment_*` | Road/river/building/window/bridge/crosswalk grammar is scene-local. Shared object drawing remains domain-shared. |
| `indoor_room` | 2 | has scene folder and noncompliant `shared/task_common.py` | Room furniture/surface/container grammar belongs in scene shared. `task_common.py` must be role-split. |
| `library` | 2 | implemented under `counting/` plus `shared/library_*` | Section/book/setting grammar is scene-local. Book drawing and object records may use domain-shared primitives. |
| `park_playground` | 4 | implemented under `counting/` plus private branch modules and `shared/park_*` | Activity/area/equipment grammar is scene-local. Branch wrappers must be replaced by public objective files or a compliant `_lifecycle.py`. |
| `pixel_village` | 4 | has scene folder and noncompliant `shared/counting.py` | Pixel map grammar belongs in scene shared. Current shared file owns task ids/query ids and generation, so it must be decomposed. |
| `single_object_figure` | 1 | has scene folder, uses domain object rendering | Object canvas and visible-part layout are scene-local; reusable object glyphs remain domain-shared. |
| `source_scene_edit` | 1 | has scene folder, calls source tasks directly | Derived counterfactual scene. Source-image/task selection is public-task-owned objective logic. |
| `transit_terminal` | 3 | implemented under `counting/` plus private branch modules and `shared/transit_*` | Boarding-area, queue, luggage, service-point grammar is scene-local. Branch wrappers must be replaced by public objective files or a compliant `_lifecycle.py`. |

Do not treat this table as a migration allowlist. It is an audit map for
future one-scene-at-a-time work.

The retired generic visual scenes `image_cutout_board` and `missing_patch` are
not active public scenes. Their reusable jigsaw, rotated-tile, option-label,
and missing-patch mechanics now live in illustration domain-shared helpers and
should be reintroduced only as source-scene-owned public tasks.

## Lessons From Migrated Reference Scenes

`charts/annotated_series` keeps the public task explicit. The task file owns the
literal public task id, local query ids, target selection, answer computation,
annotation binding, prompt slots, trace fields, and final `TaskOutput`. Scene
`shared/` owns sampled scene state, rendering, annotation projection, prompt
assembly, and trace scaffolding.

`games/2048` uses `_lifecycle.py` because several public tasks share a board
lifecycle. That private file is acceptable only because public task files pass
objective-owned hooks and support values. The lifecycle does not choose public
task behavior by task id or query id. Scene `shared/` remains state, rules,
sampling, rendering, annotations, prompts, and output fragments.

For illustrations, use the annotated-series pattern for single-task scenes and
small scenes. Use `_lifecycle.py` only for scenes where several public tasks
share a real scene lifecycle, such as `park_playground`, `transit_terminal`, or
`pixel_village`, and only if public task files still own objective selection,
answer binding, annotation binding, task-specific prompt slots, retry
semantics, and final public fields.

## Domain Shared

`trace/tasks/illustrations/shared/` is for illustration-domain helpers reused by
multiple unrelated scenes. Domain shared code must be scene-neutral and
identity-free. It must not know or branch on public task ids, public query ids,
objective contracts, registered task classes, sibling scene identities,
task-specific answer schemas, or task-specific prompt wording. It must not
construct final public `TaskOutput`.

Approved domain-shared categories:

- public object catalog, object schema, object registry, and object metadata
  normalization;
- reusable vector and pixel object renderers that are used by unrelated scenes;
- reusable person rendering primitives and render-only person appearance
  helpers;
- art-style registry, palette/style resolution, and scene-neutral visual
  defaults;
- renderer-neutral object dispatch and serialization helpers;
- low-level geometry helpers such as bbox, point, and placement math;
- small annotation artifact adapters reused by multiple illustration scenes,
  when repo-global helpers are not already sufficient;
- source-image acquisition helpers for derived visual scenes, provided they do
  not route public objectives by task id or query id.

Current domain-shared modules that should generally remain domain-shared after
cleanup:

| Module | Target role |
|---|---|
| `object_catalog.py` | Public object/background vocabulary, tags, size classes, scene tags, and renderer ids. |
| `object_schema.py` | Normalized object-record payload. |
| `object_registry.py` | Catalog-backed object-record construction. |
| `object_variants.py` | Shared render-only object variant identities and profiles. |
| `object_rendering.py` | Renderer-neutral reusable object dispatch. |
| `object_library.py` | Reusable glyph drawing and visible-part records. |
| `vector_object_renderers.py` | Registered reusable vector object family renderers. |
| `vector_person_rendering.py` | Shared vector person silhouettes, poses, and support items. |
| `person_rendering.py` | Low-level person-appearance helpers. |
| `style_registry.py` | Shared illustration style ids and style resolution. |
| `render_geometry.py` | Scene-neutral bbox/point geometry helpers. |
| `scene_objects.py` | Extraction of normalized object records from scene outputs. |
| `option_rendering.py` | Scene-neutral option-label, panel-label, bbox, font-trace, image-fit, and crop-detail helpers. |
| `cutouts.py` | Scene-neutral visual-reconstruction mechanics for jigsaw boards, rotated grids, and patch-option layouts. |

Current domain-shared modules that should move to scene-local shared during
scene migration:

| Module | Scene-local target |
|---|---|
| `environment_object_scene.py`, `environment_object_rendering.py`, `environment_task_common.py` | `trace/tasks/illustrations/environment/shared/{state,layout,rendering,annotations,prompts,output,sampling,regions}.py` as needed. |
| `library_scene.py`, `library_rendering.py`, `library_task_common.py` | `trace/tasks/illustrations/library/shared/{state,layout,rendering,annotations,prompts,output,sampling}.py` as needed. |
| `park_playground_scene.py`, `park_playground_rendering.py`, `park_task_common.py` | `trace/tasks/illustrations/park_playground/shared/{state,layout,rendering,annotations,prompts,output,sampling,regions}.py` as needed. |
| `transit_terminal_scene.py`, `transit_terminal_rendering.py`, `transit_task_common.py` | `trace/tasks/illustrations/transit_terminal/shared/{state,layout,rendering,annotations,prompts,output,sampling,regions}.py` as needed. |
| `mixed_object_scene.py`, `mixed_object_rendering.py`, `mixed_task_common.py` | Scene-local package for the public scene that owns the mixed-object grammar, if retained. |
| `pixel_village_rendering.py`, `pixel_territory_rendering.py` | `trace/tasks/illustrations/pixel_village/shared/{state,layout,rendering,annotations,prompts,output,sampling,regions,objects}.py` unless another accepted pixel-map scene needs the same primitive. |

Current shared surfaces that require decomposition before their scenes can
become review-candidate scenes:

- `trace/tasks/illustrations/shared/merged_counting_task.py` rewrites branch
  outputs to public task identities. Migrated public task files should produce
  public query metadata directly.
- `trace/tasks/illustrations/indoor_room/shared/task_common.py` is a
  task-common role file and passes `task_id` into scene rendering. It should be
  split into role files, and public task files should pass neutral namespaces or
  resolved semantic arguments instead of task identity.
- `trace/tasks/illustrations/pixel_village/shared/counting.py` defines public
  task ids, query ids, and generation logic inside shared. It must be split into
  public objective files and scene-shared role primitives.
- Private branch modules under `trace/tasks/illustrations/counting/` may be
  useful extraction sources, but migrated public task files must not remain
  thin wrappers around private branch task classes.

## Scene Shared

`trace/tasks/illustrations/<scene_id>/shared/` owns one scene's visual grammar
and reusable scene primitives.

Recommended illustrations scene-shared role files:

- `state.py`
- `defaults.py`
- `sampling.py`
- `layout.py`
- `rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`
- `styles.py`
- `assets.py`
- `components.py`
- `labels.py`
- `objects.py`
- `people.py`
- `regions.py`
- `relations.py`
- `transforms.py`
- `metrics.py`
- `spatial_primitives.py`
- `option_rendering.py`
- `cutouts.py`
- `edits.py`
- `source_images.py`

The matching scene-package file policy should allow only these role files
inside a scene `shared/` package, plus `__init__.py`, and should allow only
`_lifecycle.py` as a private scene-root file. Shared subdirectories should stay
disabled unless a later scene has a documented need for a narrower package.

Scene shared may know its visual grammar: a library shelf layout, transit
terminal boarding areas, a playground map, a room interior, a construction
site, a pixel village map, a cutout board, or a patch-option layout. It must not
route behavior by public task id, public query id, objective contract, public
task name, or registered class.

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

- Bad shared argument: `query_id="helmet_worker_count"`.
- Good shared arguments: `target_entity="worker"`,
  `attribute_name="wearing_helmet"`.

## Public Task Files

Each public task file owns one objective contract:

- literal public `TASK_ID`;
- `SCENE_ID`;
- local `SUPPORTED_QUERY_IDS`;
- query selection and query validation;
- objective-specific target/candidate construction;
- answer binding;
- `annotation_gt` binding;
- dynamic prompt slots and prompt/query key selection;
- task-specific trace fields;
- retry and final `TaskOutput`.

Public task files may call scene-shared and domain-shared primitives. They must
not delegate objective behavior to a shared base task whose subclasses differ
only by class attributes, forced query ids, or task ids.

## Config And Prompt Migration

Current illustrations configs are partially scene-keyed but still include
legacy group-level files:

- `configs/domains/illustrations/counting.yaml` contains scene-specific
  settings for `construction_site`, `environment`, `library`, `park_playground`,
  and `transit_terminal`.
- `configs/domains/illustrations/indoor_room.yaml`,
  `pixel_village.yaml`, `single_object_figure.yaml`, and
  `source_scene_edit.yaml` are already scene-keyed but still need review for
  task/query routing keys before a scene is registered.

Scene-package migration should create or update one config per public scene:

```text
configs/domains/illustrations/<scene_id>.yaml
```

Do this only for the assigned scene. Configs should hold scene/task generation
and rendering knobs, but no public task routing, query routing, objective
dispatch, or task coverage.

Prompt assets should move toward scene-scoped bundles such as:

```text
prompts/illustrations/<scene_id>/illustrations_<scene_id>_v1.json
```

The broad `prompts/illustrations/counting/` bundle should be split as the
counting scenes migrate. Retired generic visual-scene prompt bundles should not
be restored; future jigsaw or patch prompts belong under the source scene's
prompt bundle. User-facing prompt prose must remain in prompt assets; task code
should supply only prompt keys and dynamic slot values.
