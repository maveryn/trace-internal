# `task_charts__curve_panels__curve_at_x_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `curve_panels`
3. Source implementation domain/group: `charts/scientific`
4. Query id: `curve_at_x_extremum_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.scientific.multipanel_subplot_query.ChartsScientificCurveAtXExtremumLabelTask`
2. Prompt lookup domain/group: `charts/scientific`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `point_set`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `curve_at_x_extremum_label` | `selection.extreme_metric_label` | `string_label` | `point_set` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
