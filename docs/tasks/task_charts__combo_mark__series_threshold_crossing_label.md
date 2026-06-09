# `task_charts__combo_mark__series_threshold_crossing_label`

## Contract
1. Domain: `charts`
2. Scene id: `combo_mark`
3. Source implementation domain/group: `charts/combo`
4. Query id: `series_threshold_crossing_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.combo.panel_query.ChartsComboSeriesThresholdCrossingLabelTask`
2. Prompt lookup domain/group: `charts/combo`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `keyed_point_map`.
3. Annotation marks the queried target series from the first category through the answer category.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `primary_first_above_threshold_label` | `sequence.threshold_crossing_label` | `string_label` | `keyed_point_map` |
| `primary_first_below_threshold_label` | `sequence.threshold_crossing_label` | `string_label` | `keyed_point_map` |
| `line_first_above_threshold_label` | `sequence.threshold_crossing_label` | `string_label` | `keyed_point_map` |
| `line_first_below_threshold_label` | `sequence.threshold_crossing_label` | `string_label` | `keyed_point_map` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
