# `task_charts__single_series__baseline_from_aggregate_percent_change`

## Contract
1. Domain: `charts`
2. Scene id: `single_series`
3. Source implementation domain/group: `charts/hypothetical`
4. Query id: `baseline_from_aggregate_percent_change`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.hypothetical.counterfactual_value.ChartsHypotheticalBaselineFromAggregatePercentChangePublicTask`
2. Prompt lookup domain/group: `charts/hypothetical`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `unknown_answer_schema`.
2. Annotation schema: `unknown_annotation_schema`.
3. Annotation should mark the minimal visual witnesses required by the task, following the cross-domain annotation policy.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `baseline_from_aggregate_percent_change` | `numeric.difference_or_change` | `unknown_answer_schema` | `unknown_annotation_schema` |

## Review
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`.
