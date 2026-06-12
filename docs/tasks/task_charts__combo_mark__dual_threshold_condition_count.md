# `task_charts__combo_mark__dual_threshold_condition_count`

## Contract
1. Domain: `charts`
2. Scene id: `combo_mark`
3. Source implementation domain/group: `charts/combo`
4. Query id: `dual_threshold_condition_count`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.combo.panel_query.ChartsComboDualThresholdConditionCountTask`
2. Prompt lookup domain/group: `charts/combo`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `keyed_point_map`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `dual_threshold_condition_count` | `count.group_predicate` | `integer_count` | `keyed_point_map` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
