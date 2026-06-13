# Charts Shared Boundary

Use this with `SCENE_MIGRATION_GUIDE.md` when migrating a charts scene.

## Purpose

Charts has many scenes that share rendering mechanics without sharing public
task identity. This document defines where those implementation helpers belong
so scene migration does not create duplicate local helpers or a new hidden
taxonomy layer.

Public identity remains only:

```text
charts -> scene_id -> task_id
task_charts__<scene_id>__<objective_contract>
```

Renderer packages are implementation details. They are not public taxonomy,
not scene groups, not scenes, and not sampling weights.

## Current Domain Snapshot

The current scene-package tree has 44 chart scenes and 186 chart public task
files. Several scenes are already partially or fully scene-packaged, but the
shared-code boundary is uneven:

- `trace/tasks/charts/shared/` contains true domain helpers, broad legacy
  renderers, and old task/query helpers.
- many scene packages contain similarly named `shared/prompts.py`,
  `shared/runtime.py`, `shared/output.py`, `shared/rendering.py`, and
  `shared/sampling.py`.
- some duplication is legitimate scene ownership, but repeated primitive logic
  should move only through an approved domain-shared renderer-package boundary.

Do not use this snapshot as a task-count source of truth. It is only the
motivation for the shared-boundary cleanup.

## Domain Shared

`trace/tasks/charts/shared/` is for chart-domain helpers reused by multiple
unrelated chart scenes.

Allowed domain-shared categories:

- chart label and panel-label pools
- chart font, background, noise, palette, and context-text defaults
- chart-safe distractor/context layer helpers
- generic metadata helpers
- generic annotation artifact helpers when not already repo-global
- implementation-only renderer-package packages
- small neutral utilities that are demonstrably reused by several chart scenes

Domain shared code must not know or branch on:

- public task ids
- public query ids
- objective contracts
- registered task classes
- sibling scene identities
- task-specific answer schemas
- task-specific prompt wording

Domain shared code must not construct final public `TaskOutput`.

## Renderer Packages

Renderer packages live under:

```text
trace/tasks/charts/shared/<renderer_package>/
```

They group reusable implementation primitives by visual mechanics. They do not
create another public taxonomy axis.

Allowed renderer package names for charts:

| Package | Intended scenes | Allowed primitive responsibilities |
|---|---|---|
| `cartesian/` | `single_series`, `multiseries`, `combo_mark`, `scatter_points`, `scatter_readout`, `scatter_cluster`, `curve_panels`, `errorbar_series`, `uncertainty_band`, `density_curve`, `dumbbell`, `waterfall`, `candlestick`, `scientific_axis_frame`, `style_legend` | axes, ticks, scales, chart frames, series line/point/bar primitives, axis projections, mark label placement |
| `distribution/` | `boxplot`, `histogram`, `violin`, `density_curve`, `hexbin_density` | distribution supports, bin/quantile helpers, density/violin/box shape primitives, distribution-specific axis defaults |
| `map/` | `region_map`, `marker_map` | permissive map assets, region shapes, region label placement, synthetic/real map sampling primitives, choropleth/marker projection helpers |
| `flow/` | `sankey`, `radial_sankey` | node/link shapes, flow widths, path layout, link label placement, flow projection helpers |
| `grid/` | `heatmap`, `matrix`, `table` | grid shapes, row/column label placement, cell bbox/point projection, grid value formatting |
| `composition/` | `part_whole`, `sunburst`, `treemap`, `small_multiple`, `pictogram` when quantity composition is central | part-whole value allocation, segment/leaf shapes, composition palette helpers, segment projection helpers |
| `polar/` | `radar`, `radial_progress`, `sunburst` where polar layout is central | polar angle/radius math, radial axes, annular segment shapes, polar projection helpers |
| `panel/` | `dashboard`, `curve_panels`, `scatter_facet_grid`, `small_multiple`, `surface_3d` where layout is multi-panel | panel grid layout, panel label placement, panel bbox bookkeeping, panel-safe context placement |
| `three_d/` | `bar_3d`, `surface_3d` | perspective projection helpers, 3D axis layout, surface/bar depth primitives, 3D annotation projection helpers |

These families may be refined later. Do not add a new family during scene work
unless the scene migration is blocked and the user approves the family boundary.

## Renderer-Family Rules

Renderer-family code may own neutral visual primitives:

- dataclasses for reusable marks, scales, axes, panels, and projected shapes
- pure math for scales, projections, ticks, polar coordinates, 3D projection,
  grid cells, flow widths, or map regions
- reusable drawing primitives
- reusable layout constraints
- reusable annotation projection helpers
- reusable style adapters

Renderer-family code must not own public behavior:

- no `task_id`
- no public `query_id`
- no objective contract names
- no task registry imports
- no final answer binding
- no final `annotation_gt` binding for a public task
- no final `TaskOutput`
- no prompt prose or static prompt instructions
- no query-weight or task-weight policy
- no dispatch table keyed by public task/query/scene names

If a helper needs a public query id to decide behavior, the helper is too high
level. Resolve that branch in the public task file and pass neutral semantic
arguments into shared code.

Example:

- Bad shared argument: `query_id="above_threshold_count"`
- Good shared arguments: `comparison="above"`, `threshold=32`,
  `candidate_marks=[...]`

For chart tasks with mirrored threshold/comparison wording, expose the mirror
as task-local query ids when the answer and annotation schemas stay fixed. For
example, use separate query ids for above/below or at-least/below threshold
counts, then translate the selected query id inside the public task file into a
semantic comparator passed to shared helpers.

## Scene Shared

`trace/tasks/charts/<scene_id>/shared/` owns one scene's reusable primitives.

Allowed scene-shared role files:

- `state.py`
- `defaults.py`
- `sampling.py`
- `rendering.py`
- `layout.py`
- `annotations.py`
- `projection.py`
- `prompts.py`
- `output.py`
- `styles.py`
- `scales.py`
- `dataset.py`

Scene shared may know the scene's visual grammar. It may know that `bar_3d`
has perspective bars, or that `boxplot` has medians and whiskers, or that
`region_map` has region polygons. It must not route behavior by public
task/query identity.

Scene shared should stay scene-local when:

- only one scene uses the helper
- the helper depends on scene-specific dataclasses or visual grammar
- the helper constructs a full scene sample
- the helper projects scene-specific annotation witnesses
- the helper is not stable enough for reuse

## Public Task Files

Public task files own objective behavior:

- literal public task id
- supported local query ids
- query selection and validation
- objective-specific sampling constraints
- answer binding
- annotation binding
- dynamic prompt slots
- task-specific trace fields
- retry and final `TaskOutput`

The public task file may call scene-shared and domain-shared primitives. It
must not delegate the objective to a shared `runtime.generate(...)` that chooses
the answer/annotation contract from public identity.

## Current `charts/shared` Classification

Use this as the starting audit map before more chart scene migrations.

### Keep Domain-Shared

These are current domain-shared helpers or strong candidates:

- `visual_defaults.py`
- `information_style.py`
- `label_assets.py`
- `render_audit_defaults.py`, though it should eventually be split into a
  clearer context-text/background helper surface
- `scene_package_attrs.py` only as a small compatibility helper for scenes
  already using it; avoid expanding it

### Review And Narrow

These modules contain useful primitives but are too broad for the final shape.
During migration, either move primitives into renderer-package packages or keep
only the pieces still needed by migrated scenes:

- `chart_scene.py`
- `chart_scene_types.py`
- `chart_scene_primitives.py`
- `chart_scene_labeled.py`
- `chart_scene_multiseries.py`
- `chart_scene_stacked.py`
- `chart_scene_boxplot.py`
- `chart_scene_histogram.py`
- `chart_scene_violin.py`
- `distribution_chart_common.py`
- `distribution_chart_config.py`
- `distribution_boxplot.py`
- `distribution_histogram.py`
- `distribution_density.py`
- `labeled_chart_common.py`
- `labeled_chart_core.py`
- `labeled_chart_dataset_core.py`
- `labeled_chart_count_datasets.py`
- `labeled_chart_readout_datasets.py`
- `labeled_chart_summary_datasets.py`
- `labeled_chart_trend_datasets.py`
- `labeled_chart_render_params.py`

Likely final homes:

- cartesian primitives -> `charts/shared/cartesian/`
- distribution primitives -> `charts/shared/distribution/`
- composition/part-whole primitives -> `charts/shared/composition/`
- generic labels remain in `label_assets.py` or a future `labels/` package

### Retire Or Avoid Expanding

These modules represent old task/query infrastructure or broad compatibility
surfaces. Migrated scenes should not add new imports from them:

- `sampling_defaults.py`
- `param_overrides.py`
- `unanswerable.py` unless a current migrated task explicitly keeps an
  unanswerable branch and the helper is rewritten as neutral task-owned support

Do not delete these during an unrelated scene migration. Remove them only in a
dedicated cleanup after confirming no active migrated scene imports them.

## Current Scene-Family Promotion Candidates

Promotion candidates should be recorded during scene migration and handled in a
separate cleanup pass unless the scene is blocked.

High-priority candidates:

1. Map family:
   - consolidate duplicated `choropleth_*` helpers across `region_map` and
     `marker_map` into `charts/shared/map/`.
2. Flow family:
   - compare `sankey/shared/*` and `radial_sankey/shared/*`; promote neutral
     node/link/flow-width primitives into `charts/shared/flow/`.
3. Cartesian family:
   - extract axis/tick/scale/label-placement primitives used by
     `single_series`, `multiseries`, `scatter_*`, `curve_panels`,
     `errorbar_series`, `uncertainty_band`, and `density_curve`.
4. Grid family:
   - extract row/column/cell projection primitives shared by `heatmap`,
     `matrix`, and `table`.
5. Panel family:
   - extract panel layout and panel label primitives shared by `dashboard`,
     `curve_panels`, `scatter_facet_grid`, `small_multiple`, and related scenes.
6. 3D family:
   - compare `bar_3d` and `surface_3d` after both are migrated; only then
     promote projection/depth helpers that truly match.

## Migration Workflow For Charts

For each chart scene:

1. Inventory scene task files, prompt bundle, config, docs, tests, review
   artifacts, and current imports from `charts/shared`.
2. Identify the renderer package or families used by the scene. This is
   implementation-only metadata for the migration note; do not add it to public
   task identity.
3. Keep scene-specific state/sampling/rendering/projection in scene `shared/`.
4. Import existing domain-shared primitives only when they are neutral and
   already approved by this doc.
5. If duplicated logic appears, record a promotion candidate instead of moving
   it immediately.
6. Public task files must own answer and annotation binding.
7. Do not introduce a scene-wide shared runtime that branches on public query
   ids.
8. Do not introduce a renderer-package helper that branches on public scene
   names.
9. Run the scene-scoped migration gate before generating review artifacts.
10. Regenerate review artifacts only after source audit and tests pass.

## Naming Guidance

Prefer role names over task names:

- `scales.py`, not `threshold_count_utils.py`
- `axis.py`, not `single_series_helpers.py`
- `projection.py`, not `answer_points.py`
- `layout.py`, not `dashboard_task_layout.py`

Scene-local files may use scene nouns when the primitive is truly scene
specific, such as `pyramid.py`, `waffle_chart.py`, or `sankey_rendering.py`.

Avoid `runtime.py` for new migrated scenes unless it is strictly neutral and
does not own objective behavior. If a current scene has `shared/runtime.py`,
audit it carefully before marking the scene review-ready.

## Anti-Patterns

Do not:

- add `scene_group`, `scene_kind`, or renderer-package fields to public
  taxonomy
- import from a sibling scene package
- move a scene dispatcher into `charts/shared`
- pass public task/query names into renderer-package helpers
- put prompt prose into task modules or renderer-package code
- use config files for query weights, prompt text, or task coverage
- generate review artifacts for a scene that has unresolved shared-boundary
  violations

## Handoff Requirements

When handing off a migrated chart scene, report:

- renderer package or families used
- scene-local shared files and their roles
- domain-shared imports and why each is valid
- promotion candidates found, if any
- task ids and query ids smoke-generated
- tests run
- review artifacts generated
- app reload status
- open reviewer issues

Do not call a scene accepted. Human review in the browser app is required.
