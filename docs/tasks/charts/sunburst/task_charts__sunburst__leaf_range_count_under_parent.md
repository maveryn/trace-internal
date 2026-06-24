# `task_charts__sunburst__leaf_range_count_under_parent`

## Contract
1. Domain: `charts`
2. Scene id: `sunburst`
3. Public task id: `task_charts__sunburst__leaf_range_count_under_parent`
4. Supported `query_id`: `single`

## Implementation
1. Registered class: `trace.tasks.charts.sunburst.leaf_range_count_under_parent.ChartsSunburstLeafRangeCountUnderParentTask`
2. Prompt bundle: `charts_sunburst_v1`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `bbox_set`.
3. Annotation marks the printed outer leaf value labels inside the requested inclusive value range under the requested parent category.
4. Renderer context such as decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
`count(leaf under parent where lower <= value(leaf) <= upper); output=integer_count; annotation=bbox_set(matching_leaf_value_labels); scene=sunburst; scope=leaf_range_count_under_parent`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `count(leaf under parent where lower <= value(leaf) <= upper)` | `integer_count` | `bbox_set` |
