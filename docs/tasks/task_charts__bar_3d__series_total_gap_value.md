# `task_charts__bar_3d__series_total_gap_value`

## Contract
1. Domain: `charts`
2. Scene id: `bar_3d`
3. Source implementation scene package: `charts/bar_3d`
4. Query id: `series_total_gap_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.bar_3d.series_total_gap_value.ChartsThreeDBarSeriesTotalGapValueTask`
2. Prompt lookup scene: `charts/bar_3d`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `keyed_point_set_map`.
3. Annotation is keyed by the two compared series labels; each key maps to the top-center points for that series across displayed categories.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `series_total_gap_value` | `numeric.difference_or_change` | `integer_value` | `keyed_point_set_map` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
