# `task_charts__parallel_coords__all_crossings_between_adjacent_axes`

## Contract
1. Domain: `charts`
2. Scene id: `parallel_coords`
3. Source implementation domain/group: `charts/parallel_coordinates`
4. Query id: `all_crossings_between_adjacent_axes`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.parallel_coordinates.profile_query.ChartsParallelCoordinatesAllCrossingsBetweenAdjacentAxesTask`
2. Prompt lookup domain/group: `charts/parallel_coordinates`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `point_set`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `all_crossings_between_adjacent_axes` | `count.intersection_or_crossing` | `integer_value` | `point_set` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
