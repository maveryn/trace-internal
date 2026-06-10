# Charts Scene Refactor Guidelines

This is the charts-domain companion to
`SCENE_REFACTOR_GUIDELINES.md`. It applies while migrating scenes under:

```text
trace/tasks/charts/<scene_id>/
configs/domains/charts/<scene_id>.yaml
review/task-reviews/charts/<scene_id>/
```

Use it together with `charts.md`. The roadmap tracks every scene and task; this
document defines the concrete source layout and ownership rules each migrated
chart scene must follow.

Charts already live in scene-looking folders, but many files are still shallow
wrappers around shared multi-objective generators. A scene is migrated only
after the public task files own their objective logic.

## Charts Scene Package Shape

Most chart scenes should use this structure:

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
    projection.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Only create files that are useful for the scene. A small scene can omit
`dataset.py`, `projection.py`, or `output.py` when the public task files are
clearer without them.

Do not use catch-all names like `tasks.py`, `queries.py`, `grid_task.py`, or
`cross_panel_task.py` for shared objective logic. Those names usually mean the
scene still has a hidden dispatcher.

## File Responsibilities

### `defaults.py`

Scene-local fallback constants only. YAML remains source of truth.

Charts examples:

- fallback canvas size;
- fallback value, series, category, panel, bin, or region ranges;
- fallback option-count support;
- renderer-style support tuples;
- small fallback constants used by resolvers.

Do not keep broad `_TaskDefaults` dataclasses in public task files or in shared
catch-all modules. Do not mutate defaults at runtime. Do not keep user-facing
prompt prose, static slots, examples, or required slot declarations in
`defaults.py`.

### `state.py`

Scene state, typed contracts, stable ids, and query-neutral validation.

Charts examples:

- dataclasses for marks, series, categories, bins, bars, candles, regions,
  cells, panels, flows, legend entries, or option markers;
- stable entity-id helpers such as `series_id`, `mark_id`, `cell_id`,
  `region_id`, `panel_id`, or `flow_id`;
- render-map contracts that expose chart-space and pixel-space entities;
- validation helpers that check neutral scene invariants.

This file must not choose the final task target, bind the answer, bind the
annotation, assemble prompts, or build `TaskOutput`.

### `dataset.py`

Neutral chart data construction and scene-specific symbolic data models.

Charts examples:

- generate a mark table, grid, matrix, region table, Sankey flow list, OHLC
  table, density field, or panel collection;
- compute reusable neutral aggregates such as row totals, series totals,
  interval sums, density classes, category support, or adjacency lists;
- expose lookup maps that public tasks can use after they choose their target.

Allowed helpers may build data with primitive constraints, such as "at least
two unique totals" or "enough bins above and below a threshold". They must not
select the final answer for several public tasks.

Forbidden patterns:

- `build_dataset_for_query_id(query_id, ...)`;
- `sample_for_task_id(task_id, ...)`;
- returning a complete answer/annotation pair;
- branching across public objectives.

Small scenes can fold this into `sampling.py` if there is no meaningful data
model beyond sampled primitive values.

### `sampling.py`

Axis resolution and neutral sample construction.

Charts examples:

- resolve style, font, palette, label bucket, panel count, option count,
  category count, series count, bin count, region source, and numeric support;
- choose chart-type renderer variants when they are valid representation
  variants of the same scene;
- build candidate scenes and retry neutral constraints;
- sample distractor text/context-layer settings without covering chart content.

Sampling may expose objective-adjacent primitive helpers like
`sample_threshold(...)`, `sample_interval(...)`, or `sample_rank_pair(...)`,
but the public task still decides which primitive belongs to the objective.

Do not expose `generate_<objective>_output(...)` or a shared
`sample_for_query(query_id)` that dispatches among multiple task contracts.

### `scales.py`

Chart-space math and scale conversion.

Charts examples:

- linear/log/category axis scale helpers;
- tick/value conversion;
- colorbar interpolation;
- interval normalization;
- rank and order helper primitives;
- generic geometry computations that are not renderer side effects.

Use `scales.py` for math that is independent of a concrete image draw call.

### `projection.py`

Pixel projection and nontrivial chart geometry.

Charts examples:

- 3D bar and surface projection;
- map projection, region polygon transforms, and region centroid/bbox helpers;
- Sankey path/arc geometry;
- contour, hexbin, density, or curve hit targets;
- converting chart-space intervals or marks into pixel anchors.

Use `projection.py` only when the scene has enough pixel geometry to justify
separating it from `rendering.py`.

### `rendering.py`

Renderer params, image drawing, layout, styles, legends, and render maps.

Charts examples:

- chart canvas and plot-area layout;
- axis, legend, title, label, table, panel, and map drawing;
- series/bar/point/cell/region/path drawing;
- chart-specific style variants, including scientific-paper style variants;
- context-layer placement that avoids plot, legend, and annotation-critical
  areas;
- render maps for every entity that a task may later annotate.

Rendering must update entity geometry consistently with jitter, scaling, font
choice, panel layout, and legend placement. Annotation must be projected from
the render map, never from hardcoded pre-jitter coordinates.

Rendering must not decide task answers or final annotation witnesses.

### `prompts.py`

Prompt loading and thin prompt artifact assembly around external prompt assets.

Charts examples:

- prompt bundle lookup;
- merge prompt-asset static slots with public-task dynamic slots;
- scene/task/query template key rendering;
- prompt trace metadata;
- label quoting helpers for dynamic prompt slots.

Prompt text, JSON examples, static slots, and required slot declarations must
come from prompt assets, not task code or ordinary config. New text must use
`annotation`, not `evidence`.

Public task files decide task-specific dynamic prompt slots. `prompts.py` may
format those slots into the common prompt artifact.

### `annotations.py`

Scene-local annotation projection helpers.

Charts examples:

- map selected mark ids to point annotations;
- map selected bars, cells, bins, regions, candles, panels, or options to bbox
  annotations;
- build keyed point or keyed bbox maps when roles matter;
- normalize point/bbox coordinates;
- project task-selected flow/path/node witnesses from Sankey render maps.

This file may project selected ids, but the public task file still decides
which ids are correct for the objective.

Do not hide objective-specific witness selection here. For example,
`annotations.py` can expose `point_for_mark(render_map, mark_id)`, but it must
not choose "the first crossing mark" for a threshold-crossing task.

### `output.py`

Common chart scene output assembly, only if objective-neutral.

Allowed:

- assemble common trace sections;
- include rendered chart metadata, render map, prompt metadata, answer,
  annotation, context-layer metadata, and task versions;
- accept already-bound answer and annotation artifacts from the public task.

Forbidden:

- branching by public task id, objective contract, or top-level query id;
- choosing target objects;
- computing the task answer;
- selecting annotation witnesses;
- replacing public task files with shared full-output functions.

If `output.py` starts deciding what a chart question means, move that code back
to the public task file.

## Public Chart Task Files

Each `trace/tasks/charts/<scene_id>/<objective_contract>.py` must:

- define exactly one registered public task class;
- set `domain = "charts"`, `scene_id = "<scene_id>"`, and the public
  `task_id`;
- own objective-specific sampling loops and semantic constraints;
- choose the target operands;
- compute and bind `answer_gt`;
- choose and bind `annotation_gt`;
- assemble task-specific dynamic prompt slots;
- record task-specific trace fields;
- call shared renderer/prompt/output helpers only after answer and annotation
  semantics are already determined;
- expose meaningful `query_id` only for narrow operand variants inside the
  same objective contract.

Do not use fixed-query wrappers, query-subset mixins, `_SourceTask` wrappers,
or shared public task engines in migrated chart scenes.

## Public Task Ownership Examples

### Threshold count

Public task file owns:

- threshold direction and threshold value;
- counted entity ids;
- answer integer;
- annotation ids for counted entities or keyed threshold witnesses;
- dynamic prompt slots naming the threshold and direction.

Shared code may own:

- neutral data table;
- threshold sampling primitive;
- renderer and render map;
- projection from selected ids to annotations.

### Extremum label

Public task file owns:

- extremum direction;
- metric expression;
- candidate set;
- tie rejection or deterministic tie policy;
- winning label answer;
- annotation witness for the winning visual mark.

Shared code may own:

- candidate metric helper;
- chart renderer;
- label formatting and quoted dynamic prompt slots;
- mark-to-point or mark-to-bbox projection.

### Difference value

Public task file owns:

- operand roles;
- operand selection constraints;
- signed/absolute mode if it is an allowed narrow query axis;
- numeric answer;
- keyed annotations for each operand role when unordered witnesses would be
  ambiguous.

Shared code may own:

- value lookup helpers;
- support generation;
- projection of each selected operand id.

### Option selection

Public task file owns:

- the true option;
- distractor option semantics;
- option labels and answer label;
- selected option annotation when the options are visual.

Shared code may own:

- 4/6 option layout;
- option-card rendering;
- option bbox projection.

## Current Chart Anti-Patterns And Rewrites

### Wrapper-only public files

Bad:

```text
category_total_value.py
  class Task(_SourceTask):
      task_id = "task_charts__bar_3d__category_total_value"
      query_id = "category_total_value"
```

Good:

```text
category_total_value.py
  class Task(ChartTask):
      def generate(...):
          sample = sampling.build_grid_sample(...)
          target_category = self._choose_category(...)
          answer_gt = dataset.category_total(sample, target_category)
          render = rendering.render(sample, ...)
          annotation_gt = annotations.bboxes_for_category(render, target_category)
          prompt = prompts.build_prompt(...)
          return output.assemble(...)
```

The exact implementation can use helper functions, but the public file must
own the objective decisions shown above.

### Shared multi-objective task engines

Bad:

```text
shared/grid_task.py
  if query_id == "category_total_value": ...
  elif query_id == "series_total_gap_value": ...
  elif query_id == "series_threshold_count": ...
```

Good:

```text
shared/dataset.py       # grid data and aggregate helpers
shared/rendering.py     # 3D bar renderer and render map
shared/annotations.py   # projection from selected bar ids

category_total_value.py
series_total_gap_value.py
series_threshold_count.py
```

Each public file chooses its operands, answer, annotation, and dynamic prompt
slots.

### Query ids hiding task boundaries

Allowed query axes are narrow mirrors or operand settings inside one stable
program contract, such as:

- `higher` vs `lower`;
- `minimum` vs `maximum`;
- `source` vs `target` side for the same Sankey aggregation program;
- mean vs median only when the task contract intentionally defines a single
  statistic-selection program and the answer/annotation schema stay identical.

Not allowed:

- threshold count and interval count in the same public task;
- sum, mean, median, and option selection in one task because they use the
  same rendered chart;
- tasks with different annotation role structure hidden behind query ids.

## Scene Examples

### `annotated_series`

Target structure:

```text
trace/tasks/charts/annotated_series/
  callout_endpoint_change_value.py
  event_window_extremum_label.py
  event_window_threshold_count.py
  shared/
    defaults.py
    state.py
    dataset.py
    sampling.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Expected placement:

- `state.py`: series point dataclass, callout/window ids, mark ids, render-map
  contracts.
- `dataset.py`: neutral ordered series generation and value lookup.
- `sampling.py`: window size, callout position, threshold, label bucket, and
  style resolution.
- `rendering.py`: annotated line/dot plot renderer, callout/window rendering,
  context-layer placement.
- `annotations.py`: keyed points for callout/endpoint operands, point sets or
  bboxes for selected window marks.
- `prompts.py`: scene prompt artifact and quoted label slots.
- `output.py`: common annotated-series trace/output assembly only.

Public task ownership:

- `callout_endpoint_change_value.py`: selects callout and endpoint operands,
  computes difference, binds keyed operand annotations.
- `event_window_extremum_label.py`: selects the window and extremum direction,
  computes winning label, binds winning mark/window annotations.
- `event_window_threshold_count.py`: selects window threshold predicate,
  computes count, binds counted mark annotations.

### `bar_3d`

Target structure:

```text
trace/tasks/charts/bar_3d/
  category_extremum_gap_value.py
  category_threshold_count.py
  category_total_gap_value.py
  category_total_value.py
  pairwise_comparison_count.py
  series_category_scope_total_value.py
  series_threshold_count.py
  series_total_gap_value.py
  shared/
    defaults.py
    state.py
    dataset.py
    sampling.py
    projection.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Expected placement:

- `state.py`: series/category/bar ids, bar value grid, 3D render-map contracts.
- `dataset.py`: category totals, series totals, gaps, threshold helper
  primitives, pairwise comparison primitives.
- `sampling.py`: series/category counts, value support, camera/style, max bar
  count constraints.
- `projection.py`: 3D-to-2D bar projection and visible anchor helpers.
- `rendering.py`: 3D axes, bars, labels, value text, occlusion-aware draw
  order, render maps.
- `annotations.py`: selected bar/category/series bbox or point projection.

Public task ownership:

- total tasks select their category/series/scope and compute totals.
- gap tasks select candidate sets and compute target gaps.
- threshold tasks select predicate and counted bars/categories/series.
- pairwise comparison selects comparison operands and counted relations.

`shared/grid_task.py` and `shared/grid_query.py` style engines must disappear
after migration.

### `dashboard`

Target structure:

```text
trace/tasks/charts/dashboard/
  category_panel_condition_count.py
  dual_condition_count.py
  dual_source_target_sum_value.py
  panel_gap_extremum_category_label.py
  shared_label_rank_gap_extremum.py
  source_rank_difference_value.py
  source_rank_target_value.py
  statement_option_selection_label.py
  top_k_overlap_count.py
  shared/
    defaults.py
    state.py
    dataset.py
    sampling.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Expected placement:

- `state.py`: panel ids, source ids, category ids, dashboard mark ids,
  statement option ids.
- `dataset.py`: neutral panel/source/category values and reusable rank/gap/top-k
  helpers.
- `sampling.py`: panel count, panel type, source/category support, option
  count, distractor text/context settings.
- `rendering.py`: mixed dashboard layout, panel renderers, legends, safe
  context-layer placement outside active plot/legend regions.
- `annotations.py`: selected panel/category/source mark projection and visual
  option bbox projection.

Public task ownership:

- each cross-panel task chooses its panels, sources, categories, condition,
  rank, top-k set, or statement options;
- `statement_option_selection_label.py` constructs the true/false statements
  and binds the selected visual option;
- no shared `cross_panel_task.py` can branch over these objectives.

### `region_map`

Target structure:

```text
trace/tasks/charts/region_map/
  adjacent_category_count.py
  adjacent_numeric_threshold_count.py
  adjacent_same_category_count.py
  categorical_region_count.py
  continent_category_region_count.py
  continent_region_count.py
  continent_threshold_region_count.py
  group_filtered_region_value.py
  named_region_set_total_value.py
  numeric_interval_region_count.py
  numeric_threshold_region_count.py
  shared/
    defaults.py
    state.py
    geography.py
    dataset.py
    sampling.py
    projection.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Expected placement:

- `geography.py`: natural/synthetic map source loading, topology, region
  groups, adjacency, and license-tracked asset references.
- `state.py`: region ids, value/category records, map source contracts.
- `dataset.py`: map value/category assignment and group/filter helpers.
- `sampling.py`: map-source weights, value/category support, legend bins,
  target group/continent selection.
- `projection.py`: polygon transforms, centroid, bbox, and adjacency geometry
  projection.
- `rendering.py`: map renderer, legends, region labels, palette/style variants.
- `annotations.py`: selected region bboxes/points and keyed role maps.

Public task ownership:

- numeric threshold/interval tasks choose thresholds and counted regions;
- categorical tasks choose categories and counted regions;
- continent/group tasks choose the geographic group and filter semantics;
- adjacent tasks choose the anchor relation and counted neighbor set;
- aggregate tasks choose named region sets and aggregate mode.

The current `choropleth_*` helper names should be normalized during migration
when they describe generic map-region behavior, not a specific old scene name.

### `sankey` and `radial_sankey`

Use separate scene-local shared packages. Do not promote Sankey layout code to
domain shared until both scenes are cleaned and the common API is genuinely
small.

Expected shared roles:

- `state.py`: node ids, side/layer ids, flow/path ids.
- `dataset.py`: neutral flow graph construction and reusable side/node/path
  aggregation helpers.
- `sampling.py`: path count, node count, source/target mirror axis, palette and
  separation settings.
- `projection.py`: path geometry, label anchors, node bboxes.
- `rendering.py`: straight or radial Sankey rendering and render maps.
- `annotations.py`: selected node/path/flow projection.

Public task files own source/target mirror selection, aggregate target
selection, answer binding, and annotation witnesses. Source and target mirror
variants should use the same program contract when only the side role changes.

### `table`

Tables belong in charts when the task is numeric/structured chart readout.

Expected shared roles:

- `state.py`: row ids, column ids, cell ids, row/column label contracts.
- `dataset.py`: table value generation, row/column aggregates, interval
  helpers.
- `sampling.py`: row/column count, temporal/numeric label support, font and
  spacing constraints.
- `rendering.py`: table grid renderer with text-fit validation.
- `annotations.py`: selected cell/row/column projection.

Public task files own the aggregate/query program and target cells. They must
not rely on visual text overflow or column-boundary ambiguity.

### `curve_panels`, `scientific_axis_frame`, and scientific-style plots

Scientific-looking render style is a chart style variant, not a separate task
objective by itself.

Expected shared roles:

- scientific style presets live in scene/domain shared style helpers only when
  reused across multiple cleaned scenes;
- panel labels and legend labels must come from separate pools when both appear
  in one image;
- monochrome style binding tasks own their line/marker style semantics in the
  public task file.

Public tasks still own the reasoning program: at-x extremum, intersection
count, threshold crossing, reference-line readout, legend-style binding, or
panel comparison.

## Domain Shared Promotion Candidates

During the scene loop, record possible promotions but do not move new code into
`trace/tasks/charts/shared/` immediately.

Likely chart-domain candidates:

- font selection wrappers and text-fit helpers;
- chart label pools, temporal label sampling, and panel-title sampling;
- palette/background/context-layer sampling;
- generic axis tick helpers;
- generic point/bbox/keyed annotation artifact helpers;
- generic 4/6 visual option layout;
- prompt JSON example helpers;
- simple chart statistics primitives reused by at least two cleaned scenes.

Keep scene-local:

- any renderer tied to one scene grammar;
- any dataset dataclass tied to one scene;
- 3D bar projection;
- Sankey/radial Sankey path layout until a shared API is proven after cleanup;
- map asset/topology/projection code;
- table layout and text-fit code;
- contour/hexbin/density-specific geometry;
- dashboard mixed-panel layout;
- prompt examples specific to one scene.

At the final charts-domain checkpoint, compare all recorded candidates and
promote only narrow primitives reused by at least two cleaned scenes.

## Scene Migration Checklist

For each chart scene:

1. List active task ids and current files.
2. Identify wrapper files, shared task classes, shared full-output generators,
   and objective dispatchers.
3. Write one objective contract per public task: answer schema, annotation
   schema, operands, candidate set, operation, tie policy, and query axes.
4. Split shared code into the role files above.
5. Rewrite each public task file so it owns objective sampling, answer binding,
   annotation binding, dynamic prompt slots, and task trace.
6. Delete wrapper-only files and shared task engines.
7. Normalize scene-owned helper names away from old task-group names when the
   name is no longer accurate.
8. Update config, prompt assets, taxonomy records, tests, docs, and review
   paths together.
9. Regenerate changed review artifacts under `review/task-reviews/charts/`.
10. Run scene compile/import/generation smoke checks.
11. Add a completion note to `charts.md`.

## Charts Scene Completion Note

Each completed charts scene section in `charts.md` should include:

```text
Completion note:
- source ownership:
- split/merge decision:
- scene shared helpers:
- domain shared candidates deferred:
- config/prompt/docs updated:
- annotation/prompt terminology checked:
- task reviews regenerated/stale folders purged:
- checks:
- blockers:
```

The `domain shared candidates deferred` line is required even when it says
`none`. This keeps promotion decisions explicit and prevents accidental
one-scene abstractions from moving into domain shared too early.
