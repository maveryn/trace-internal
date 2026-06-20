# `task_charts__parallel_coords__axis_delta_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `parallel_coords`
3. Source implementation domain/scene: `charts/parallel_coords`
4. Supported `query_id`: `largest_increase_between_axes`, `largest_decrease_between_axes`, `largest_absolute_change_between_axes`
5. Query ids select the change mode used in the prompt and program.

## Implementation
1. Registered class: `trace.tasks.charts.parallel_coords.axis_delta_extremum_label.ChartsParallelCoordinatesAxisDeltaExtremumLabelTask`
2. Prompt lookup domain/scene: `charts/parallel_coords`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Program Contract
`select_label(arg_extreme(profiles, change(value(axis_i), value(axis_j), mode={increase,decrease,absolute}), direction=largest)); output=string_label; annotation=point(answer_profile_segment_midpoint); scene=parallel_coords; scope=axis_delta_extremum_label`

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `point`.
3. Annotation marks one midpoint on the answer profile segment between the named axes.
4. Axes, labels, threshold text, and decorative context are renderer context unless explicitly requested.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `largest_increase_between_axes` | `select.extreme_axis_change_label` | `string_label` | `point` |
| `largest_decrease_between_axes` | `select.extreme_axis_change_label` | `string_label` | `point` |
| `largest_absolute_change_between_axes` | `select.extreme_axis_change_label` | `string_label` | `point` |
