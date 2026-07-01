# Icons Shared Boundary

Use this with `SCENE_MIGRATION_GUIDE.md` when migrating an icons scene.

## Purpose

The icons domain has three different implementation concerns that must stay
separate:

- true icon-domain primitives, such as curated SVG loading, procedural named
  icon rasterization, transform helpers, style sampling, and icon noise;
- reusable visual grammars that belong to one scene, such as pair grids,
  overlap grids, sequence strips, and named icon fields;
- legacy public query/task plumbing that rewrites outputs or constructs
  `TaskOutput` records from shared code.

Scene-package migration must separate these layers before any icons scene is
registered as review-ready.

Public identity remains only:

```text
icons -> scene_id -> task_id
task_icons__<scene_id>__<objective_contract>
```

Old implementation folders such as `counting`, `relation`, `pattern`, and
`sequence` are not public taxonomy nodes. During migration, each public scene
gets its own package under `trace/tasks/icons/<scene_id>/`.

Use `docs/ACTIVE_TASK_INVENTORY.md` for active icon scenes and task counts.
Record scene-specific migration findings in review artifacts, not in this
shared-boundary policy.

## Lessons From Migrated Reference Scenes

`charts/annotated_series` keeps each public task explicit: task files select
query ids, bind targets, compute answers, bind annotation, assemble prompt
slots, and return `TaskOutput`. Scene `shared/` owns only sampled series,
rendering, annotations, prompts, and trace scaffolding.

`games/2048` uses a private `_lifecycle.py` because several public tasks share
the same board lifecycle. That lifecycle is acceptable only because each task
file passes objective-owned hooks and support values. The public task still
owns the objective contract. Scene `shared/` remains state, rules, sampling,
rendering, annotations, prompts, and output fragments.

For icons, start with the annotated-series pattern when possible. Use a private
`_lifecycle.py` only for scenes with a genuinely shared visual lifecycle and
only if public task files still own objective selection, answer binding,
annotation binding, prompt slots, retry semantics, and final public fields.

## Domain Shared

`trace/tasks/icons/shared/` is for icon-domain helpers reused by multiple
unrelated scenes. Domain shared code must be scene-neutral and identity-free.
It must not know or branch on public task ids, public query ids, objective
contracts, registered task classes, sibling scene identities, task-specific
answer schemas, or task-specific prompt wording. It must not construct final
public `TaskOutput`.

Approved domain-shared categories:

- curated icon asset manifest loading and SVG rasterization;
- procedural named icon vocabulary, display names, fill styles, and rasterized
  sprites;
- canonical D4/icon transform primitives;
- per-icon photometric/noise helpers that preserve annotation coordinates;
- icon palette, tint, contrast, and canvas-style adapters;
- small annotation artifact adapters reused by multiple icons scenes, when a
  repo-global helper is not already sufficient;
- panel, bbox, placement, and grid-slot primitives that are genuinely reused by
  multiple scene packages;
- anchor marker drawing, when multiple icon scenes use reference markers;
- visual option-grid primitives shared by true option-image scenes such as
  `icon_cutout`, `mirror_grid`, and `single_transform_options`.

Domain-shared modules that should remain domain-shared:

| Module | Target role |
|---|---|
| `icon_assets.py` | Curated SVG manifests, icon-id resolution, and transformed RGBA rendering. |
| `procedural_named_icons.py` | Procedural named icon vocabulary, display names, fill styles, and glyph rasterization. |
| `icon_transform.py` | Canonical transform ids and low-level D4 image transforms. |
| `icon_noise.py` | Coordinate-preserving per-icon noise sampling/application and trace serialization. |
| `icon_style.py` | Palette and tint sampling with distance constraints. |
| `scene_style.py` | Canvas/background/panel-style adapter backed by shared visual-style helpers. |
| `annotation.py` | Reusable icon bbox/keyed-bbox annotation adapters, pending later repo-global promotion if another domain needs the same shape. |
| `anchor_marking.py` | Neutral visible anchor marker drawing. |

Domain-shared modules that should be narrowed before or during scene migration:

| Module | Target |
|---|---|
| `defaults.py` | Keep only cross-scene visual defaults. Move scene-specific count, panel, or option defaults into scene `shared/defaults.py` and scene config. |
| `icon_scene.py` | Keep low-level dataclasses, bbox placement, panel layout, panel chrome, serialization, and trace geometry helpers. Move `render_two_panel_icon_scene` to `reference_canvas/shared/rendering.py` unless another migrated scene needs exactly that renderer. |
| `icon_grid_scene.py` | Keep neutral grid/row slot math. Do not let it choose scene semantics or task answers. |
| `icon_task_rendering.py` | Keep neutral render-param/style/noise resolution only. Remove task-group wording and any scene/task-specific fallback logic as scenes migrate. |
| `icon_labeled_grid_scene.py` | Either rename/narrow into a domain-level visual option-grid primitive, or keep scene-local until a second migrated option scene uses it. It must not know task ids or query ids. |

Domain-shared modules that should move to scene-local shared when their owning
scene is migrated:

| Module | Scene-local target |
|---|---|
| `icon_pair_grid_scene.py` | `trace/tasks/icons/pair_grid/shared/{state,layout,rendering,annotations}.py` as needed. |
| `icon_sequence_scene.py` | `trace/tasks/icons/sequence_strip/shared/{state,layout,rendering,annotations}.py` as needed. |
| `procedural_named_icon_field_scene.py` | Mostly `trace/tasks/icons/named_field/shared/`; extract only small bbox/fill-style helpers if multiple named scenes truly need them. |

Domain-shared modules retired from migrated scenes:

| Module | Reason |
|---|---|
| `public_query_task.py` | Retired. Output rewriting was legacy public-query plumbing; migrated public task files use repo-global query helpers directly or build final output/query metadata in task-owned code. |

## Scene Shared

`trace/tasks/icons/<scene_id>/shared/` owns one scene's visual grammar and
scene-specific reusable primitives.

Recommended icons scene-shared role files:

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
- `transforms.py`
- `metrics.py`
- `spatial_primitives.py`
- `option_rendering.py`
- `labels.py`

The matching scene-package file policy should allow only these role files
inside a scene `shared/` package, plus `__init__.py`, and should allow only
`_lifecycle.py` as a private scene-root file. Shared subdirectories should stay
disabled for icons unless a later scene has a documented need for a narrower
family package.

Scene shared may know the scene grammar, such as a pair grid, Venn field,
ring, path, sequence strip, mirror grid, wallpaper panel, or reference canvas.
It must not route behavior by public task id, public query id, objective
contract, public task name, or registered class.

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

- Bad shared argument: `query_id="left_of_anchor"`.
- Good shared arguments: `axis="x"`, `side="negative"`,
  `anchor_bbox=...`, `candidate_bboxes=...`.

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

## Legacy Shared Surfaces To Audit

During scene migration, audit legacy shared files for public task/query routing
and decompose any that construct final public outputs:

- `trace/tasks/icons/reference_canvas/shared/reference_match_count.py`
  defines public task ids, chooses query ids, branches on query ids, owns prompt
  text selection, and contains a shared base task that constructs `TaskOutput`.
- `trace/tasks/icons/reference_canvas/shared/size_relation.py`
  defines the public metric-relation task implementation and constructs
  `TaskOutput` from shared code.
- `trace/tasks/icons/paired_canvas/shared/common.py`
  chooses public query ids and builds final paired-canvas `TaskOutput`.
- `trace/tasks/icons/paired_canvas/shared/panel_added_removed_count.py` and
  `panel_exact_match_count.py` define task-specific classes for one public task
  inside `shared/`.
- Public task files should not call retired icon-specific output rewriters;
  public output/query metadata should be produced directly by the task file or
  by a permitted private `_lifecycle.py`.

## Config And Prompt Migration

Current icons configs should not introduce old reasoning-group files such as
`relation.yaml`, `sequence.yaml`, or `pattern.yaml`.

`named_strip`, `overlap_grid`, and `wallpaper_panels` now have
scene-scoped config files.

Scene-package migration should create or update one config per public scene:

```text
configs/domains/icons/<scene_id>.yaml
```

Do this only for the assigned scene. Do not reshape every icons config as part
of one scene migration. Configs should hold scene/task generation and rendering
knobs, but no public task routing, query routing, objective dispatch, or task
coverage.

Prompt assets should likewise move toward scene-scoped bundles such as:

```text
prompts/icons/<scene_id>/icons_<scene_id>_v1.json
```

Prompt prose stays in prompt assets. Public task files provide dynamic slots
and selected prompt/query keys.

## Suggested Migration Order

Start with a small scene whose renderer is already close to scene-local:

1. `pair_grid`
   - two public tasks;
   - one obvious scene renderer currently in `icon_pair_grid_scene.py`;
   - good first test for moving a domain-shared scene renderer into scene
     `shared/`.
2. `single_transform_options` or `icon_cutout`
   - one public task each;
   - useful for deciding whether `icon_labeled_grid_scene.py` should become an
     approved domain-level visual option-grid primitive.
3. `sequence_strip`
   - two public tasks;
   - direct move target for `icon_sequence_scene.py`.
4. `overlap_grid`
   - one public task;
   - migrated to scene-local overlap rendering helpers.

Avoid migrating `named_field`, `reference_canvas`, or `paired_canvas` first.
They are high-value scenes but contain the most legacy task/query plumbing and
should follow after the first small scene validates the icons file policy and
shared role split.

## Scene Migration Procedure For Icons

For each icons scene:

1. Inventory active task ids, current source files, config keys, prompt bundle,
   tests, docs, and review artifacts.
2. Write the scene contract: visual grammar, layout/view, style axes, and
   annotation projection assumptions.
3. Write one task contract per public task: answer schema, annotation schema,
   query ids, reasoning program, and objective-owned logic.
4. Move scene grammar into scene `shared/` role files.
5. Keep or import only approved identity-free domain shared primitives.
6. Rewrite each public task file so it owns objective logic and final public
   output fields.
7. Remove retired wrappers, compatibility aliases, stale prompt/config keys,
   and stale review artifacts for that scene.
8. Smoke-generate every public task and supported query branch.
9. Add the scene to the review-candidate registry only after the source shape
   is ready for the migration gate.
10. Record manual code audit status under
    `review/task-reviews/icons/<scene_id>/manual_code_audit_status.json`.
11. Run the scene-scoped migration gate.
12. Generate review artifacts only after manual and automated gates pass.
13. Reload the review app index.

Do not mark an icons scene accepted from source code. Human review in the
browser app is still required.
