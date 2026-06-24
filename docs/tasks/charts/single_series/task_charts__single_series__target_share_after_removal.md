# `task_charts__single_series__target_share_after_removal`

## Contract
1. Domain: `charts`
2. Scene id: `single_series`
3. Source implementation: `trace/tasks/charts/single_series/target_share_after_removal.py`
4. Public task id: `task_charts__single_series__target_share_after_removal`
5. Supported `query_id` values: `single`
6. Query ids are internal replay/review metadata; scene style, label pool, mark count, and context mode are generation metadata.

## Implementation
1. Registered class: `trace.tasks.charts.single_series.target_share_after_removal.ChartsHypotheticalTargetShareAfterRemovalPublicTask`
2. Prompt lookup: `prompts/charts/single_series/charts_hypothetical_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Program Contract
`percent_share(value(target_label), sum(values(marks excluding removed_labels))); output=integer_value; annotation=point_set(retained_marks); scene=single_series; scope=target_share_after_removal`

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `point_set`.
3. Annotation marks every retained visible mark used in the denominator, including the target mark.
4. Axes, legend, titles, captions, decorative context, and distractor text are context unless the task explicitly asks for them as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `percent_share.target_value_after_named_removal` | `integer_value` | `point_set` |
