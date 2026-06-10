# Charts Scene-Package Migration Roadmap

This is the tracked migration roadmap for migrating the `charts` domain under
`docs/workflows/SCENE_PACKAGE_MIGRATION/README.md`.
Use it together with:

```text
docs/workflows/SCENE_PACKAGE_MIGRATION/SCENE_REFACTOR_GUIDELINES.md
docs/workflows/SCENE_PACKAGE_MIGRATION/CHARTS_SCENE_REFACTOR_GUIDELINES.md
docs/workflows/SCENE_PACKAGE_MIGRATION/DOMAIN_AUDIT_PLAYBOOK.md
docs/domains/CHART_TASK_SETUP.md
```

Do not treat the current `trace/tasks/charts/<scene_id>/` source layout as
proof that charts is migrated. Some chart files were moved into scene folders
by a shallow path migration, but many public files are still wrappers around
shared multi-objective generators. The scene-package migration must be an
objective-ownership migration, not a wrapper migration.

## Status

- Domain: `charts`
- Active public task inventory: 188 tasks across 44 scenes.
- Target task count: keep 188 unless a scene review finds a real task-contract
  merge/split.
- Target source layout:

```text
trace/tasks/charts/<scene_id>/<objective_contract>.py
trace/tasks/charts/<scene_id>/shared/
trace/tasks/charts/shared/        # cross-scene chart utilities only
configs/domains/charts/<scene_id>.yaml
prompts/charts/<scene_id>/
review/task-reviews/charts/<scene_id>/<task_id>/
```

- Migration state: not complete. Charts must not be considered fully migrated
  until every scene below passes the gates in this document.

## Current Anti-Patterns To Remove

The current chart tree contains several migration failure modes:

1. Public task files that only subclass a `_SourceTask` from scene `shared/`.
2. Shared modules named like `*_task.py` or `*_query.py` that define task
   classes or own complete `generate()` methods.
3. Shared task engines that branch over `task_id`, `objective_contract`, or
   top-level `query_id` and return complete `TaskOutput` objects.
4. Shared annotation builders that decide the final task witnesses for several
   public tasks.
5. Scene-local helpers copied from older task-group modules without being split
   by role.
6. Domain-shared chart helpers used as scene-local catch-alls.
7. Any active chart code, config, docs, prompt assets, or generated current
   records that use `task_group` as routing or public metadata.
8. Any new or migrated prompt text using `evidence` instead of `annotation`.

The migration must replace these patterns with objective-owned public task
files and narrowly-scoped scene-local helpers.

## Non-Negotiable Gates

Before `charts` can be marked migrated:

1. `trace.tasks` imports every active chart scene-package task.
2. Registered/default chart task count matches the active inventory: 188.
3. Every active chart task id maps to exactly one file at
   `trace/tasks/charts/<scene_id>/<objective_contract>.py`.
4. Every public task file defines exactly one registered public chart task.
5. No public task file is a wrapper around `_SourceTask`, fixed-query mixins,
   query-subset mixins, or shared full-output generators.
6. No public task file defines sibling public task ids or sibling public task
   classes.
7. No scene `shared/` module defines registered public task classes.
8. No scene `shared/` module branches across public objectives to build final
   answers, final annotations, or complete `TaskOutput` objects.
9. Scene `shared/` modules may expose reusable datasets, render maps,
   projections, primitive chart operations, thin prompt-asset rendering, and
   neutral output assembly only.
10. Public task files own objective-specific sampling, target construction,
    answer binding, annotation binding, dynamic prompt slots, and
    task-specific trace fields.
11. Domain `shared/` contains only utilities reused by at least two cleaned
    chart scenes.
12. Scene configs live under `configs/domains/charts/<scene_id>.yaml`.
13. Prompt assets live under scene-aligned chart prompt bundles and own prompt
    wording, static slots, examples, and required slot declarations.
14. Active chart code/config/docs/prompts use `annotation`, not `evidence`.
15. Active chart code/config/docs do not use `task_group` routing or public
    metadata.
16. Task-review artifacts are regenerated for changed active chart tasks under
    `review/task-reviews/charts/`; stale folders for retired or renamed chart
    task ids are purged.

## Charts Scene Package Shape

Charts should follow the generic scene-package migration shape but with chart-specific roles. Use
only files that are useful for the scene.

```text
trace/tasks/charts/<scene_id>/
  <objective_contract>.py
  ...
  shared/
    defaults.py
    state.py
    dataset.py
    sampling.py
    scales.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

### `defaults.py`

Owns fallback constants only. YAML remains source of truth.

Allowed examples:

- fallback canvas dimensions;
- fallback value/count ranges;
- fallback label count ranges;
- supported renderer/style variants;
- small fallback constants used by resolvers.

Not allowed:

- broad `_TaskDefaults` containers that hide scene config;
- runtime defaults mutation;
- objective dispatch.

### `state.py`

Owns scene-local data contracts and ids.

Allowed examples:

- chart sample, mark, series, category, bin, region, cell, panel, or flow
  dataclasses;
- stable entity id helpers;
- query-neutral rendered-scene contracts;
- validation helpers that do not select final task targets.

Not allowed:

- final answer binding;
- final annotation witness selection;
- prompt or `TaskOutput` assembly.

### `dataset.py`

Owns neutral chart data construction and chart-specific symbolic data models.

Allowed examples:

- generate a table of marks/series/categories/regions/panels;
- construct neutral candidate data satisfying primitive support constraints;
- expose lookup maps and aggregate primitives.

Not allowed:

- `build_dataset_for_query_id(...)` that owns multiple public objectives;
- selecting the final target answer for public tasks;
- deciding which annotations are required.

Small scenes may fold `dataset.py` into `sampling.py` if that is clearer.

### `sampling.py`

Owns neutral axis/support/style/label sampling.

Allowed examples:

- resolve chart type, style, font, label bucket, panel count, option count, and
  numeric support axes;
- expose reusable candidate sampling helpers;
- retry neutral scene data construction.

Not allowed:

- `sample_for_task_id(...)`;
- choosing among public task objectives;
- returning full task outputs.

### `scales.py` / `projection.py`

Owns chart coordinate transforms and scale math.

Allowed examples:

- axis scale conversion;
- colorbar interpolation;
- map projection support;
- chart geometry hit/projection helpers;
- 3D-to-2D projection math.

Use `projection.py` when the scene has substantial pixel projection logic;
otherwise `scales.py` is enough.

### `rendering.py`

Owns scene rendering and render maps.

Allowed examples:

- chart renderer parameters;
- palette/style variants;
- legend/layout rendering;
- drawing marks, axes, panels, tables, maps, labels, and annotations-neutral
  entity maps.

Rendering must not decide task answers or final annotation witnesses.

### `annotations.py`

Owns annotation projection primitives.

Allowed examples:

- map selected mark ids to point sets;
- map selected bins/cells/regions/options to bbox sets;
- construct keyed annotation payloads from task-selected entity ids;
- normalize point/bbox coordinates.

The public task file decides which ids are selected. `annotations.py` only
projects them.

### `prompts.py`

Owns thin prompt artifact assembly around prompt assets.

Allowed examples:

- prompt bundle lookup;
- merge prompt-asset static slots with task-provided dynamic slots;
- scene/task/query template key rendering;
- prompt trace metadata.

Prompt text, JSON examples, static slots, and required slot declarations must
come from prompt assets, not task code or ordinary config. New text must use
`annotation`, not `evidence`.

### `output.py`

Owns objective-neutral output assembly only.

Allowed:

- assemble a `TaskOutput` after the task has already bound answer,
  annotation, prompt artifacts, rendered chart, and task trace fragments;
- serialize common scene trace sections.

Forbidden:

- branching by public task id, objective contract, or top-level query id;
- choosing targets;
- choosing annotations;
- computing final answers;
- replacing public task files with a shared full-output generator.

## Public Chart Task File Requirements

Each `trace/tasks/charts/<scene_id>/<objective_contract>.py` must:

1. define exactly one registered public task class;
2. set `domain = "charts"` and `scene_id = "<scene_id>"`;
3. set the public `task_id`;
4. own the objective-specific sampling loop and semantic constraints;
5. bind final `answer_gt`;
6. bind final `annotation_gt`;
7. call shared renderer/prompt/output helpers only after the objective is
   already determined;
8. include task-specific trace fields and validation;
9. expose `query_id` only for narrow operand variants inside the same objective
   contract.

Examples of objective ownership:

- `threshold_value_count.py` chooses threshold direction/value and counted
  mark ids; `annotations.py` only projects those ids.
- `range_extremum_label.py` chooses the candle range metric and winning candle;
  `rendering.py` only draws candles and exposes candle anchors.
- `statement_option_selection_label.py` constructs candidate statements and
  selects the true option; option layout is reusable but truth selection is not.
- `node_side_total_value.py` chooses source/target side and node, computes the
  total, and selects flow witnesses; Sankey rendering is shared.

## Domain Shared Boundary

Keep scene-local code local during the scene loop. Promote only after all
scenes are cleaned and only when at least two cleaned scenes need the same
narrow primitive.

Likely valid `trace/tasks/charts/shared/` utilities:

- generic chart font/style/background/context-layer helpers;
- reusable label pools and label formatting;
- generic chart palette helpers;
- generic axis tick helpers;
- generic point/bbox annotation artifact helpers;
- generic chart prompt example helpers;
- generic label sampling and temporal-label sampling.

Keep scene-local:

- any renderer tied to one scene grammar;
- any dataset schema tied to one scene;
- any chart-specific mark id vocabulary used by only one scene;
- Sankey, map, 3D bar, table, heatmap, radar, or dashboard-specific
  render/data/projection helpers unless a second cleaned scene uses the same
  narrow API;
- any helper whose name contains one scene id.

Do not promote a helper just because two shallow-migrated scenes currently
share copied code. First clean both scenes, then compare the cleaned APIs.

## Preflight Before Scene Loop

1. Create/refresh this charts roadmap.
2. Snapshot active chart task inventory from `docs/ACTIVE_TASK_INVENTORY.md`
   and registry once imports are healthy.
3. Remove `charts` from completed migration allowlists until all scenes pass.
4. If runtime routing needs scene-package imports before cleanup is complete,
   keep chart scenes in a pending scene-package routing allowlist and mark them
   objective-ownership pending.
5. Add or update enforcement tests for charts:
   - no `_SourceTask` imports in public task files;
   - no registered classes under `trace/tasks/charts/*/shared/`;
   - no `TaskOutput` returns from scene shared modules unless the function name
     and signature prove it is objective-neutral assembly;
   - no `task_group` strings in migrated chart code/config/docs;
   - registered chart task count equals 188.
6. Do not start by moving code into `trace/tasks/charts/shared/`.
7. Do not regenerate solve-rate artifacts during source migration.

## One-Pass Execution Model

Process charts scene-by-scene in the order below. For each scene:

1. Confirm active task ids and current source files.
2. Decide whether the listed tasks remain separate or need a merge/split.
3. Write each task's contract: answer schema, annotation schema, program
   schema, candidate set, operand roles, final operation, and annotation role
   template.
4. Split scene-local shared code by role.
5. Rewrite every public task file so it owns one objective.
6. Remove wrapper-only public files, shared task classes, and shared
   multi-objective generators.
7. Replace task-group naming in scene-owned code/config/docs with scene/task
   naming.
8. Ensure prompts and payloads say `annotation`, not `evidence`.
9. Update scene config, prompt assets, active task docs, imports, taxonomy
   review data, and tests.
10. Purge stale review folders only for retired/renamed task ids.
11. Regenerate review artifacts for changed active tasks under
    `review/task-reviews/charts/<scene_id>/`.
12. Run scene compile/import/generation smoke checks.
13. Add a completion note before moving to the next scene.

## Per-Scene Completion Note Template

Add a short completion note under each scene while executing the pass:

```text
Completion note:
- source ownership:
- split/merge decision:
- scene shared helpers:
- domain shared candidates deferred:
- config/prompt/docs updated:
- task reviews regenerated/stale folders purged:
- checks:
- final post-migration review:
- blockers:
```

## Per-Scene Roadmap

### annotated_series

- Tasks: `callout_endpoint_change_value`, `event_window_extremum_label`,
  `event_window_threshold_count`.
- Shared target: annotated-series data/state, event-window/callout rendering,
  point/bbox projection, dynamic prompt-slot formatting,
  objective-neutral output assembly.
- Objective ownership: each public task chooses its endpoint/window predicate,
  binds answer, and chooses keyed/point annotation witnesses.
- Current risk: wrapper-style public task files and shared event-window task
  engine must be removed.

### area

- Tasks: `interval_area_value`, `stacked_band_dominance_label`,
  `stacked_band_interval_sum_value`.
- Shared target: area/stacked-band dataset, interval projection, renderer, and
  annotation projection.
- Objective ownership: interval integration, dominance selection, and stacked
  interval sum target logic belong in separate public task files.

### bar_3d

- Tasks: `category_extremum_gap_value`, `category_threshold_count`,
  `category_total_gap_value`, `category_total_value`,
  `pairwise_comparison_count`, `series_category_scope_total_value`,
  `series_threshold_count`, `series_total_gap_value`.
- Shared target: 3D bar grid state, projection math, renderer, label/palette
  sampling, bar id projection, prompt helpers, objective-neutral output.
- Objective ownership: category totals, series totals, gaps, threshold counts,
  and pairwise comparisons must be separate task programs.
- Current risk: shared `grid_task.py`/`grid_query.py` owns multiple objectives.

### boxplot

- Tasks: `iqr_extremum_label`, `median_rank_difference_value`,
  `median_reference_label`, `paired_median_shift_label`.
- Shared target: boxplot summary state, distribution sampling, renderer, point
  annotation for medians/IQRs, prompt helpers.
- Objective ownership: ranked difference, reference comparison, paired shift,
  and IQR extremum selection stay in public task files.

### candlestick

- Tasks: `counterfactual_close_value`, `range_extremum_label`.
- Shared target: OHLC state, candlestick renderer, candle center projection,
  prompt helpers.
- Objective ownership: counterfactual close computation and range extremum
  selection stay separate.

### combo_mark

- Tasks: `absolute_gap_extremum_label`, `conditioned_line_extremum_label`,
  `conditioned_primary_extremum_label`, `cross_mark_difference_value`,
  `directional_gap_extremum_label`, `dual_threshold_condition_count`,
  `interval_threshold_condition_count`, `series_threshold_crossing_label`.
- Shared target: combo-series dataset, mark role ids, dual-axis renderer,
  scale/projection helpers, prompt helpers.
- Objective ownership: gap extrema, conditioned extrema, cross-mark
  difference, threshold conditions, and crossing selection must not be hidden
  behind shared `panel_task.py`.

### contour_density

- Tasks: `density_extremum_region_label`, `density_threshold_region_count`,
  `nearest_region_option_label`, `reference_distance_extremum_label`,
  `spread_extremum_region_label`.
- Shared target: contour field state, region/level geometry, renderer,
  option layout where needed, annotation projection.
- Objective ownership: density, distance, spread, option selection, and
  threshold count target logic stay in public task files.

### curve_panels

- Tasks: `cross_panel_delta_extremum_label`,
  `cross_panel_threshold_earliest_label`, `curve_at_x_extremum_label`,
  `curve_intersection_count`, `earliest_maximum_panel_label`,
  `panel_curve_threshold_crossing_count`, `panel_point_threshold_count`,
  `threshold_series_count`.
- Shared target: multipanel curve data, style legend data, renderer, curve
  sampling, intersection/crossing primitives, annotation projection.
- Objective ownership: panel delta, earliest crossing, at-x extremum,
  intersection count, maxima, point predicates, and series threshold counts
  stay separate.

### dashboard

- Tasks: `category_panel_condition_count`, `dual_condition_count`,
  `dual_source_target_sum_value`, `panel_gap_extremum_category_label`,
  `shared_label_rank_gap_extremum`, `source_rank_difference_value`,
  `source_rank_target_value`, `statement_option_selection_label`,
  `top_k_overlap_count`.
- Shared target: dashboard panel/category state, mixed chart rendering,
  support point/bbox projection, option layout, prompt helpers.
- Objective ownership: each dashboard task must select its own panels,
  categories, statement/options, answer, and annotation refs.
- Current risk: shared `cross_panel_task.py` branches over many objectives and
  builds final outputs.

### density_curve

- Tasks: `density_at_x_extremum_label`, `interval_mass_extremum_label`,
  `mean_extremum_label`, `mode_location_extremum_label`.
- Shared target: density curve sampling, renderer, interval/x projection,
  prompt helpers.
- Objective ownership: at-x density, interval mass, mean, and mode location
  selections stay in public task files.

### dumbbell

- Tasks: `absolute_gap_threshold_count`, `gap_rank_row_label`,
  `side_winner_count`.
- Shared target: paired row data, endpoint projection, dumbbell renderer.
- Objective ownership: threshold count, ranked gap row, and side-winner count
  target logic stay separate.

### error_interval

- Tasks: `interval_width_rank_label`, `reference_containment_count`,
  `reference_exclusion_side_count`.
- Shared target: interval chart data, reference-line rendering, interval bbox
  projection.
- Objective ownership: width ranking, containment count, and exclusion-side
  count stay separate.

### errorbar_series

- Tasks: `bound_extremum_x_label`, `same_x_interval_overlap_count`,
  `threshold_support_count`.
- Shared target: errorbar series data, whisker/bound projection, renderer.
- Objective ownership: bound extremum, overlap count, and threshold support
  count stay separate.

### heatmap

- Tasks: `axis_cell_extremum_label`, `axis_condition_extremum_label`,
  `colorbar_interval_cell_count`, `colorbar_threshold_cell_count`,
  `condition_run_extremum_label`.
- Shared target: heatmap grid state, color scale, renderer, cell projection,
  prompt helpers.
- Objective ownership: each task chooses the relevant axis/cell/condition/run
  target and annotation witnesses.
- Current risk: shared `grid_task.py`/`grid_query.py` owns multiple objectives.

### hexbin_density

- Tasks: `threshold_bin_count`.
- Shared target: hexbin grid state, density class/color scale, renderer,
  bin annotation projection.
- Objective ownership: threshold direction/range and counted bins stay in the
  public task file.

### histogram

- Tasks: `bin_count_between_values`, `cumulative_rank_bin_label`,
  `interval_mass`.
- Shared target: histogram bin data, axis/bin projection, renderer.
- Objective ownership: interval count, cumulative rank, and interval mass
  target logic stay separate.

### marker_map

- Tasks: `marker_region_extremum_label`, `marker_region_threshold_count`.
- Shared target: map/region state, marker placement, renderer, map projection,
  region/marker annotation projection.
- Objective ownership: extremum marker selection and threshold count stay
  separate.

### matrix

- Tasks: `axis_extremum_label`, `off_diagonal_confusion_label`,
  `threshold_cell_count`.
- Shared target: matrix grid state, cell projection, renderer, prompt helpers.
- Objective ownership: axis extremum, off-diagonal confusion, and threshold
  counting stay separate.
- Current risk: shared cell task/query mixins must be removed.

### multiseries

- Tasks: `category_total_extremum_label`, `pair_equality_label`,
  `ranked_change_extremum_label`, `ranked_pair_ratio_extremum_label`,
  `ranked_series_share_extremum_label`, `series_comparison_count`,
  `series_rank_at_category_label`.
- Shared target: multiseries dataset, grouped/stacked/line/bar rendering,
  legend/label sampling, mark projection.
- Objective ownership: totals, equality, ranked changes, ratios, shares,
  comparisons, and rank-at-category stay in public task files.

### parallel_coords

- Tasks: `all_crossings_between_adjacent_axes`, `axis_condition_count`,
  `axis_delta_extremum_label`, `crossings_involving_profile_between_axes`.
- Shared target: profile data, axis layout, crossing computation primitive,
  renderer, profile/axis annotation projection.
- Objective ownership: all-crossing count, conditioned profile count,
  delta extremum, and profile-specific crossings stay separate.

### part_whole

- Tasks: `adjacent_transfer_gap_value`, `chart_order_share_to_count`,
  `contiguous_chart_order_sum`, `positional_segment_share_sum`,
  `sector_share_to_angle`, `subset_denominator_share_value`.
- Shared target: part/whole chart data, pie/donut/bar composition renderers,
  segment projection, label/legend sampling.
- Objective ownership: transfer gaps, share-to-count, contiguous sums,
  positional sums, sector angles, and denominator ratios stay separate.

### pictogram

- Tasks: `category_total_value`, `group_difference_value`,
  `threshold_count`.
- Shared target: pictogram/waffle state, icon/block renderer, category
  projection.
- Objective ownership: category total, group difference, and threshold count
  stay separate.

### population_pyramid

- Tasks: `age_group_threshold_count`, `side_gap_extremum_label`.
- Shared target: pyramid data, age/side scale, renderer, bar projection.
- Objective ownership: threshold count and side-gap extremum stay separate.

### radar

- Tasks: `highlighted_metric_threshold_panel_count`,
  `matching_condition_panel_count`, `profile_advantage_count`,
  `threshold_metric_count_for_panel`.
- Shared target: radar profile data, polar projection, renderer, metric
  annotation projection.
- Objective ownership: highlighted metric threshold, matching condition panel,
  profile advantage, and threshold metric counts stay separate.

### radial_progress

- Tasks: `extremum_remaining_label`, `progress_interval_count`,
  `progress_threshold_count`, `remaining_threshold_count`.
- Shared target: radial progress state, arc renderer, arc/label projection.
- Objective ownership: remaining extremum, progress interval, progress
  threshold, and remaining threshold count stay separate.

### radial_sankey

- Tasks: `dominant_endpoint_label`, `transfer_total_value`.
- Shared target: radial flow graph state, radial Sankey renderer, flow/node
  projection.
- Objective ownership: dominant endpoint and transfer total stay separate.

### region_map

- Tasks: `adjacent_category_count`, `adjacent_numeric_threshold_count`,
  `adjacent_same_category_count`, `categorical_region_count`,
  `continent_category_region_count`, `continent_region_count`,
  `continent_threshold_region_count`, `group_filtered_region_value`,
  `named_region_set_total_value`, `numeric_interval_region_count`,
  `numeric_threshold_region_count`.
- Shared target: synthetic/natural map state, region adjacency, categories,
  numeric values, geographic group metadata, renderer, region projection.
- Objective ownership: adjacent-category, adjacent-threshold, same-category,
  categorical count, continent filters, named-set totals, numeric interval,
  and numeric threshold programs stay in public task files.

### sankey

- Tasks: `node_side_total_value`, `path_bottleneck_value`,
  `path_flow_difference`, `source_to_target_total_flow`.
- Shared target: flow graph state, layout, flow renderer, node/link
  projection.
- Objective ownership: node-side total, bottleneck path, path difference, and
  source-target total flow stay separate.

### scatter_cluster

- Tasks: `centroid_option_selection_label`, `cluster_area_rank_label`,
  `cluster_separation_extremum_label`, `cluster_spread_extremum_label`,
  `cluster_trend_direction_label`.
- Shared target: scatter cluster state, convex hull/spread/centroid
  primitives, renderer, option layout, point/cluster projection.
- Objective ownership: centroid option, area rank, separation, spread, and
  trend direction stay separate.

### scatter_facet_grid

- Tasks: `region_density_extremum_label`.
- Shared target: faceted scatter state, density region primitive, renderer,
  panel/region projection.
- Objective ownership: region density extremum stays in the public task file.

### scatter_points

- Tasks: `axis_threshold_point_count`, `category_axis_mean_extremum_label`,
  `category_threshold_point_count`.
- Shared target: scatter point state, category sampling, renderer,
  point/category projection.
- Objective ownership: axis threshold count, category-axis mean extremum, and
  category threshold count stay separate.

### scatter_readout

- Tasks: `series_pair_value_gap_at_x`, `series_x_extremum_label`,
  `series_y_anchor_other_series_value`.
- Shared target: scatter/line readout data, x/y scale, renderer, series/point
  projection.
- Objective ownership: pair gap at x, x extremum, and y-anchor readout stay
  separate.

### scientific_axis_frame

- Tasks: `axis_span_value`, `tick_spacing_value`.
- Shared target: scientific-style axis frame renderer, tick data, projection.
- Objective ownership: axis span and tick spacing value computations stay
  separate.

### single_series

- Tasks: `baseline_from_aggregate_percent_change`, `endpoint_change_value`,
  `interval_rate_value`, `interval_value_count`, `monotone_streak_length`,
  `observed_threshold_crossing_label`, `order_statistic_label`,
  `order_statistic_value`, `projected_threshold_crossing_label`,
  `remaining_mean_after_removal`, `target_share_after_removal`,
  `threshold_value_count`, `turning_point_count`.
- Shared target: single-series data, chart-type renderers, scale projection,
  temporal/generic label sampling, mark annotation projection.
- Objective ownership: each value/count/rate/order/crossing/mean/share/streak
  program stays in its public task file.
- Current risk: old value/statistics/counting/hypothetical route helpers must
  be split into scene-neutral data/render/projection helpers and task-owned
  objective files.

### size_encoding

- Tasks: `category_total_extremum_label`, `filtered_item_extremum_label`,
  `reference_size_neighbor_label`.
- Shared target: size-encoded chart state, bubble/marker renderer, item
  projection.
- Objective ownership: total extremum, filtered item extremum, and reference
  neighbor selection stay separate.

### small_multiple

- Tasks: `average_top_k_minus_average_bottom_k`,
  `composition_shift_l1_distance`, `conditioned_panel_sum_from_percent`,
  `top_k_by_segment_then_sum_other_segment_count`.
- Shared target: small-multiple composition data, panel renderer, segment
  projection.
- Objective ownership: top/bottom average difference, L1 shift, conditioned
  panel sum, and top-k segment counting stay separate.

### style_legend

- Tasks: `pairwise_gap_value`, `threshold_series_count`,
  `x_position_extremum_series_label`.
- Shared target: style/legend bound series data, renderer, series style
  binding, mark projection.
- Objective ownership: pairwise gap, threshold count, and x-position extremum
  stay separate.

### sunburst

- Tasks: `leaf_range_count_under_parent`, `leaf_threshold_count_under_parent`,
  `parent_total_extremum_label`, `parent_total_value`.
- Shared target: hierarchy state, sunburst renderer, segment projection.
- Objective ownership: leaf range, leaf threshold, parent total extremum, and
  parent total value stay separate.

### surface_3d

- Tasks: `panel_variation_label`, `reference_nearest_label`,
  `series_trend_label`, `surface_extremum_label`.
- Shared target: 3D surface/panel state, projection, renderer, point/surface
  annotation projection.
- Objective ownership: panel variation, nearest reference, trend label, and
  surface extremum stay separate.

### table

- Tasks: `absolute_difference_between_rows_over_year_interval`,
  `categorical_value_count`, `column_rank_label`, `column_summary_value`,
  `filtered_column_mean`, `interval_value_count`,
  `sum_absolute_differences_between_rows_over_year_interval`,
  `threshold_count`.
- Shared target: table grid state, text layout, cell projection, row/column
  metadata, prompt helpers.
- Objective ownership: temporal row differences, categorical counts, ranking,
  summaries, filtered means, interval counts, summed row differences, and
  thresholds stay separate.

### treemap

- Tasks: `group_total_value`, `repeated_leaf_aggregate_value`.
- Shared target: treemap hierarchy, layout, renderer, rectangle projection.
- Objective ownership: group totals and repeated-leaf aggregate stay separate.

### uncertainty_band

- Tasks: `band_overlap_count`, `band_width_extremum_x_label`.
- Shared target: banded series state, renderer, overlap/width primitives,
  band/x annotation projection.
- Objective ownership: overlap count and width-extremum x-label stay separate.

### violin

- Tasks: `modality_label`, `mode_extremum_label`,
  `support_width_extremum_label`.
- Shared target: violin distribution state, renderer, distribution statistic
  helpers, annotation projection.
- Objective ownership: modality, mode extremum, and support-width extremum
  stay separate.

### waterfall

- Tasks: `remove_step_final_total`, `reverse_step_final_total`,
  `running_total_value`, `threshold_crossing_label`.
- Shared target: waterfall step state, running-total primitives, renderer,
  step/bar projection.
- Objective ownership: remove-step total, reverse-step total, running total,
  and threshold crossing stay separate.

## Final Domain Checkpoint

After every scene has a completion note:

1. Compare cleaned scene-local `shared/` helpers for real duplication.
2. Promote only narrow cross-scene chart primitives to
   `trace/tasks/charts/shared/`.
3. Remove scene-local code from domain shared if it is used by only one scene.
4. Re-run enforcement tests.
5. Run a chart registry import/count check: exactly 188 active chart tasks.
6. Run compile checks for `trace/tasks/charts`.
7. Run chart unit tests.
8. Regenerate current chart task-review artifacts under `review/task-reviews`.
9. Reload the review app index.
10. Update `docs/domains/CHART_TASK_SETUP.md`, task docs, active inventory,
    taxonomy review data, and any migration notes to reflect the completed
    scene-package layout.
