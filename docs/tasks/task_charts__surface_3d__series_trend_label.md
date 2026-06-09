# `task_charts__surface_3d__series_trend_label`

## Contract
1. Domain: `charts`
2. Scene id: `surface_3d`
3. Source implementation domain/group: `charts/three_d`
4. Query id: `series_trend_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.three_d.panel_query.ChartsThreeDSeriesTrendLabelTask`
2. Prompt lookup domain/group: `charts/three_d`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `bbox_set`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `series_trend_label` | `selection.extreme_metric_label` | `string_label` | `bbox_set` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
