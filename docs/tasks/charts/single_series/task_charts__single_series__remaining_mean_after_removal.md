# `task_charts__single_series__remaining_mean_after_removal`

## Contract
1. Domain: `charts`
2. Scene id: `single_series`
3. Source implementation domain/group: `charts/hypothetical`
4. Query id: `remaining_mean_after_removal`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.hypothetical.counterfactual_value.ChartsHypotheticalRemainingMeanAfterRemovalPublicTask`
2. Prompt lookup domain/group: `charts/hypothetical`
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
| `remaining_mean_after_removal` | `numeric.summary_statistic` | `integer_value` | `point_set` |
