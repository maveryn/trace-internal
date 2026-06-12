# Charts Shared-Boundary Audit

Date: 2026-06-12

## Summary

This is an audit-only report for the charts scene-package migration. It does
not move code or mark any scene migrated. It records where reusable charts code
should live before the remaining scene migrations continue.

Current checked state:

- 44 chart scene directories.
- 186 chart public task files on disk.
- 186 chart task ids registered successfully when importing scenes one at a
  time.
- 31 top-level `trace/tasks/charts/shared/*.py` modules were present, excluding
  `__init__.py`.

Main finding: charts has a legitimate need for domain-level implementation
families, but the current boundary is uneven. Some code in
`trace/tasks/charts/shared/` is true domain infrastructure, some is broad
legacy renderer code, and many scene-local `shared/` modules still own
objective behavior that must move into public task files during scene
migration.

## Boundary Rules

Use these rules for all future chart scene migration work.

- `trace/tasks/charts/shared/` is only for helpers reused across unrelated
  chart scenes and independent of public task/query identity.
- Renderer-family packages under `trace/tasks/charts/shared/<family>/` are
  implementation details only. They are not scene ids, public taxonomy,
  sampling axes, or task grouping.
- `trace/tasks/charts/<scene_id>/shared/` is for one scene's visual grammar:
  state, layout, sampling primitives, rendering primitives, projection, and
  scene-specific annotation helpers.
- Public task files own objective behavior: task id, local query ids, query
  selection, answer binding, annotation binding, prompt slots, task trace
  fields, retry policy, and final `TaskOutput`.
- Shared code must not branch on public `task_id`, public `query_id`,
  objective contract, or scene name. If a helper needs that branch, the branch
  belongs in the task file and the helper should receive semantic arguments.

## Domain-Shared Module Classification

| Module | Current use | Decision |
|---|---:|---|
| `visual_defaults.py` | 7+ scenes | Keep domain-shared. Valid chart-wide font/background/noise adapter. |
| `label_assets.py` | 30+ scenes by semantic use | Keep domain-shared. Valid chart-wide label and panel-label source. |
| `information_style.py` | 3+ scenes | Keep domain-shared, but only as style/background adapter. Do not add objective logic. |
| `labeled_chart_common.py` | broad use | Keep as transitional domain-shared. Split long-term into labels, scaling, numeric sampling, and cartesian primitives. |
| `chart_scene.py` | annotated/boxplot plus legacy users | Review and narrow. Move neutral axes/mark primitives to `shared/cartesian/`; scene-specific renderers should become scene-local. |
| `distribution_chart_common.py` | boxplot/violin/histogram/density | Review and narrow. Move reusable distribution primitives to `shared/distribution/`; keep task objective assembly out. |
| `labeled_chart_core.py` | annotated only | Scene-localize unless another migrated scene needs the same neutral type. |
| `render_audit_defaults.py` | no direct chart-scene imports found | Review before reuse. Likely split into context/background helpers if still needed. |
| `scene_package_attrs.py` | waterfall only | Retire after waterfall migration. Do not expand. |
| `unanswerable.py` | sparse use | Keep only as neutral answer-branch utility for tasks that still explicitly support unanswerable construction. Do not use as a shared task runtime. |
| `sampling_defaults.py` | legacy/sparse use | Retire or replace with repo-global neutral sampling helpers during scene migration. Do not expand. |
| `param_overrides.py` | no direct use found | Candidate for removal after dependency verification. |
| `chart_scene_*`, `distribution_*`, `labeled_chart_*_datasets.py` with no current imports | Candidate stale domain helpers. Confirm no dynamic imports before deletion in a dedicated cleanup. |

## Renderer-Family Targets

These are implementation packages, not taxonomy.

| Family | Scenes to audit together | Move here only when neutral |
|---|---|---|
| `cartesian/` | `single_series`, `multiseries`, `combo_mark`, `scatter_points`, `scatter_readout`, `scatter_cluster`, `curve_panels`, `errorbar_series`, `uncertainty_band`, `density_curve`, `dumbbell`, `waterfall`, `candlestick`, `scientific_axis_frame`, `style_legend` | axes, ticks, value scales, chart frames, line/point/bar mark primitives, point projection, tick-label layout |
| `distribution/` | `boxplot`, `histogram`, `violin`, `density_curve`, `hexbin_density` | bins, quantiles, density support, violin/box/hist primitives, distribution axis defaults |
| `map/` | `region_map`, `marker_map` | map assets, geography geometry, synthetic/real map sampling, region projection, marker projection |
| `flow/` | `sankey`, `radial_sankey` | flow width math, node/link layout, label placement, link projection |
| `grid/` | `heatmap`, `matrix`, `table` | row/column/cell geometry, table/grid rendering, cell bbox/point projection |
| `composition/` | `part_whole`, `sunburst`, `treemap`, `small_multiple`, `pictogram` | part-whole allocation, segment geometry, leaf/segment projection, quantity-composition palettes |
| `polar/` | `radar`, `radial_progress`, `sunburst` | angle/radius math, annular segments, radial axes, polar projection |
| `panel/` | `dashboard`, `curve_panels`, `scatter_facet_grid`, `small_multiple`, `surface_3d` | panel-grid layout, panel labels, panel bbox bookkeeping, panel-safe context placement |
| `three_d/` | `bar_3d`, `surface_3d` | perspective projection, 3D axes, depth ordering, 3D annotation projection |

Do not create a new renderer family during ordinary scene work. Record a
promotion candidate and continue scene-local unless the scene is blocked.

## Scene-Level Audit

| Scene | Tasks | Family | Current boundary finding | Required action during migration |
|---|---:|---|---|---|
| `annotated_series` | 1 | cartesian | Already mostly scene-packaged; imports legacy `chart_scene`, `labeled_chart_core`, and chart style helpers. | Keep scene-local state/layout/rendering. Promote only neutral cartesian axis/mark primitives later. |
| `area` | 3 | cartesian | Good scene-local split. Uses domain labels/style/defaults. | Keep current shape; public tasks must continue owning answer and annotation binding. |
| `bar_3d` | 8 | three_d | Good scene-local split after recent migration work. 3D projection/render primitives are scene-local. | Keep local until `surface_3d` is migrated; then compare for `shared/three_d/` extraction. |
| `boxplot` | 4 | distribution | Uses `distribution_chart_common` and `chart_scene`; scene shared has branches/defaults/rendering. | Extract reusable distribution primitives later; keep task-specific rank/reference objectives in task files. |
| `candlestick` | 2 | cartesian | `shared/ohlc.py` owns scene grammar and prompt defaults. | Keep scene-local; only axis/tick helpers are candidates for `cartesian/`. |
| `combo_mark` | 8 | cartesian/panel | `shared/runtime.py` and panel helpers are broad; prompt and annotation helpers are scene-local. | Remove objective assembly from runtime during migration; keep panel rendering local unless reused with dashboard/curve panels. |
| `contour_density` | 5 | distribution/cartesian | `shared/field_query.py` is a scene-local multi-objective helper. | Split objective behavior into task files; keep field rendering/projection local. |
| `curve_panels` | 8 | cartesian/panel | Multipanel shared modules include query-specific prompt keys and runtime behavior. | Move objective/query branches to task files. Panel and curve rendering may later feed `panel/` and `cartesian/`. |
| `dashboard` | 9 | panel/cartesian | Cross-panel runtime owns multi-task behavior. | Public tasks must own objective-specific logic; keep panel layout/rendering local first. |
| `density_curve` | 4 | distribution/cartesian | `density_curve.py` and runtime carry scene behavior. | Keep density sampling/rendering local; promote only neutral density support after comparison with violin/uncertainty scenes. |
| `dumbbell` | 3 | cartesian | `pairwise_comparison_query.py` branches by prompt key. | Split objective behavior into task files; keep row/pair rendering local or later cartesian. |
| `error_interval` | 3 | cartesian | `interval_chart.py` owns interval scene grammar. | Keep local; promote interval projection only if reused by uncertainty/errorbar scenes. |
| `errorbar_series` | 3 | cartesian | `series_query.py` is scene-local query helper. | Move objective branching to task files; keep errorbar rendering local. |
| `heatmap` | 5 | grid | Grid shared files are legitimate scene grammar but runtime has objective behavior. | Keep grid primitives local first; later compare with matrix/table for `grid/`. |
| `hexbin_density` | 1 | distribution | No scene-local shared beyond package. Direct task imports broad domain helpers. | Keep as simple task file; extract hexbin primitives only if another scene reuses them. |
| `histogram` | 3 | distribution | `histogram_count.py` is scene-local objective helper. | Split task objectives; promote bin helpers only after distribution cleanup. |
| `marker_map` | 2 | map | Duplicates many `choropleth_*` files with `region_map`. | High-priority `shared/map/` candidate. Do not keep duplicating map assets/geography. |
| `matrix` | 3 | grid | Cell helpers are scene-local but runtime handles objectives. | Move objective behavior to task files; later compare cell geometry with heatmap/table. |
| `multiseries` | 7 | cartesian | Many shared modules branch by query and task semantics. | Split objective logic into task files; keep chart rendering/data primitives local until cartesian extraction. |
| `parallel_coords` | 4 | cartesian/profile | `profile_sampling.py` branches heavily by query. | Move query branches to tasks; keep profile geometry/rendering local. |
| `part_whole` | 6 | composition | Share-arithmetic helpers branch by query. | Split objectives; keep segment allocation/rendering local before composition extraction. |
| `pictogram` | 3 | composition | `waffle_chart.py` branches by query. | Move objective-specific branches to task files; keep waffle/pictogram rendering local. |
| `population_pyramid` | 2 | cartesian | `pyramid.py` branches by query. | Split objective behavior; keep pyramid scene grammar local. |
| `radar` | 4 | polar | Profile helpers mirror parallel-coordinates patterns. | Move query/objective branches to tasks; consider polar/profile primitives later. |
| `radial_progress` | 4 | polar | `progress_chart.py` branches by query. | Move objective logic to tasks; keep radial progress rendering local. |
| `radial_sankey` | 2 | flow/polar | Flow helpers duplicate sankey concepts; sampling/output branch by query. | High-priority comparison with `sankey`; promote neutral flow layout/projection later. |
| `region_map` | 11 | map | Large duplicated map helper set with `marker_map`; several query-specific helpers. | High-priority `shared/map/` candidate; move task-specific query branches to task files. |
| `sankey` | 4 | flow | Flow helpers are scene-local but overlap radial sankey. | Compare with radial sankey before extraction; keep objective binding in task files. |
| `scatter_cluster` | 5 | cartesian | Cluster helpers are scene-local with output/runtime split. | Keep cluster sampling/rendering local; only point/axis primitives belong in cartesian. |
| `scatter_facet_grid` | 1 | cartesian/panel | Single task with facet query helper. | Keep local unless future facet tasks are added; panel layout may later share. |
| `scatter_points` | 3 | cartesian | `points_query.py` carries scene/objective logic. | Split objective logic into task files; promote only axis/point primitives. |
| `scatter_readout` | 3 | cartesian | `series_readout.py` branches by query and uses unanswerable helper. | Split objective branches; keep readout scene grammar local. |
| `scientific_axis_frame` | 2 | cartesian | `axis_frame_query.py` branches by query. | Split objective logic; axis/tick primitives may move to cartesian. |
| `single_series` | 13 | cartesian | Legacy value/query modules still own task/query behavior and query weights. | Major migration scene. Public task files must own all objectives; cartesian primitives should be extracted only after task split. |
| `size_encoding` | 3 | cartesian | Comparison helpers branch by query and output helpers know task ids. | Move objective behavior to task files; keep size encoding rendering local. |
| `small_multiple` | 4 | composition/panel | `small_multiples_aggregate_value.py` branches by query and task id. | Split objective behavior; promote only neutral panel grid/composition primitives later. |
| `style_legend` | 3 | cartesian | Style legend sampling branches by query. | Move objective branches to tasks; style/legend rendering may feed cartesian/style primitives later. |
| `sunburst` | 4 | composition/polar | `sunburst_hierarchy.py` branches by query and task id. | Split objective behavior; polar/composition extraction only after split. |
| `surface_3d` | 4 | three_d/panel | Panel helpers branch by query. | Migrate after `bar_3d` comparison; promote only matching 3D projection primitives. |
| `table` | 8 | grid | Counting/ranking/statistics/temporal shared modules own answer binding and query branches. | Treat as a major migration. Public tasks own objectives; table scene/rendering stays local, grid primitives may be promoted later. |
| `treemap` | 2 | composition | `treemap_composition.py` branches by query/task id. | Split objectives; keep treemap composition local until composition extraction. |
| `uncertainty_band` | 2 | cartesian | `band_query.py` branches by query. | Split objective logic; interval/band primitives can later compare with error scenes. |
| `violin` | 3 | distribution | Uses `distribution_chart_common`; local `violin_label.py` scene logic. | Keep violin scene logic local; promote shared density/quantile primitives later. |
| `waterfall` | 4 | cartesian | `panel_query.py` still registers tasks and returns `TaskOutput` from shared code. | High-priority violation. Public task files must replace shared registered/runtime behavior. |

## Priority Findings

1. `waterfall/shared/panel_query.py` is the clearest current boundary violation:
   scene shared registers tasks, owns answer/annotation binding, and constructs
   final outputs. Fix before calling waterfall scene-package migrated.
2. `single_series`, `table`, `multiseries`, `region_map`, `curve_panels`,
   `dashboard`, and `combo_mark` are high-risk scenes because scene-local shared
   modules still centralize objective/query behavior for many tasks.
3. `region_map` and `marker_map` duplicate enough map code that a dedicated
   `charts/shared/map/` extraction should happen before repeatedly migrating
   map-related scenes.
4. `sankey` and `radial_sankey` should be audited together before extraction
   into `charts/shared/flow/`.
5. Broad legacy modules in `charts/shared/` with zero direct imports should not
   be deleted during scene migration. Delete only in a dedicated cleanup after
   checking dynamic imports and tests.

## Allowed Imports For New Scene Migrations

Until a renderer-family extraction is approved, migrated scenes may import:

- `trace.tasks.charts.shared.visual_defaults`
- `trace.tasks.charts.shared.label_assets`
- `trace.tasks.charts.shared.information_style`
- narrowly used neutral pieces from `labeled_chart_common.py`, but do not add
  new objective/query behavior there

Avoid adding new imports from:

- `sampling_defaults.py`
- `param_overrides.py`
- `scene_package_attrs.py`
- broad `chart_scene_*` legacy files
- broad `labeled_chart_*_datasets.py` files
- scene sibling packages

## Extraction Backlog

Handle these as separate commits from scene migrations unless the scene is
blocked.

1. Map family:
   - Create `trace/tasks/charts/shared/map/`.
   - Move neutral map assets, geography geometry, region projection, style, and
     marker projection primitives shared by `region_map` and `marker_map`.
   - Leave region-count, continent, threshold, marker-extremum, and marker-count
     objective logic in public task files.
2. Flow family:
   - Create `trace/tasks/charts/shared/flow/`.
   - Move only neutral node/link layout, flow width, and path projection shared
     by `sankey` and `radial_sankey`.
3. Cartesian family:
   - Create `trace/tasks/charts/shared/cartesian/` after auditing
     `single_series`, `multiseries`, and scatter scenes.
   - Move axes, ticks, scales, point/line/bar primitive drawing, and projection.
4. Grid family:
   - Compare `heatmap`, `matrix`, and `table` after their task objectives are
     split.
   - Move row/column/cell geometry only when the same primitive is used by more
     than one scene.
5. Composition/polar/panel/3D families:
   - Defer until at least two scenes in the family are properly migrated and can
     prove the helper is neutral.

## Validation Performed

- `git status --short` was clean before writing this report.
- Scene inventory found 44 chart scenes and 186 public task files.
- Scene-by-scene registry import succeeded for every chart scene and registered
  186 chart task ids.
- Static scans found no active chart source references to retired difficulty
  scoring terminology before this report.
