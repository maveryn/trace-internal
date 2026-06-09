# `task_charts__parallel_coords__axis_delta_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `parallel_coords`
3. Source implementation domain/group: `charts/parallel_coordinates`
4. Query id: sampled from `largest_absolute_change_between_axes`, `largest_decrease_between_axes`, `largest_increase_between_axes`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.parallel_coordinates.profile_query.ChartsParallelCoordinatesAxisDeltaExtremumLabelTask`
2. Prompt lookup domain/group: `charts/parallel_coordinates`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `keyed_point_map`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `largest_absolute_change_between_axes` | `selection.extreme_metric_label` | `string_label` | `keyed_point_map` |
| `largest_decrease_between_axes` | `selection.extreme_metric_label` | `string_label` | `keyed_point_map` |
| `largest_increase_between_axes` | `selection.extreme_metric_label` | `string_label` | `keyed_point_map` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
