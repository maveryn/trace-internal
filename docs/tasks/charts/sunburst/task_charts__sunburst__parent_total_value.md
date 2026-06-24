# `task_charts__sunburst__parent_total_value`

## Contract
1. Domain: `charts`
2. Scene id: `sunburst`
3. Public task id: `task_charts__sunburst__parent_total_value`
4. Supported `query_id`: `single`

## Implementation
1. Registered class: `trace.tasks.charts.sunburst.parent_total_value.ChartsSunburstParentTotalValueTask`
2. Prompt bundle: `charts_sunburst_v1`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `bbox_set`.
3. Annotation marks the printed outer leaf value labels under the requested parent category.
4. Renderer context such as decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
`sum(value(leaf) for leaf under parent); output=integer_value; annotation=bbox_set(leaf_value_labels); scene=sunburst; scope=parent_total_value`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `sum(value(leaf) for leaf under parent)` | `integer_value` | `bbox_set` |
