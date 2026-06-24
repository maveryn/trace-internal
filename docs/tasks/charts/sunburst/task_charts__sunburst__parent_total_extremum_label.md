# `task_charts__sunburst__parent_total_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `sunburst`
3. Public task id: `task_charts__sunburst__parent_total_extremum_label`
4. Supported `query_id`: `highest_parent_total_label`, `lowest_parent_total_label`

## Implementation
1. Registered class: `trace.tasks.charts.sunburst.parent_total_extremum_label.ChartsSunburstParentTotalExtremumLabelTask`
2. Prompt bundle: `charts_sunburst_v1`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `bbox_set`.
3. Annotation marks the printed outer leaf value labels used to compare all parent-category totals.
4. Renderer context such as decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
`arg_extremum(parent, sum(value(leaf) for leaf under parent), direction={highest,lowest}); output=string_label; annotation=bbox_set(all_leaf_value_labels); scene=sunburst; scope=parent_total_extremum_label`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `highest_parent_total_label` | `argmax(parent, sum(value(leaf) for leaf under parent))` | `string_label` | `bbox_set` |
| `lowest_parent_total_label` | `argmin(parent, sum(value(leaf) for leaf under parent))` | `string_label` | `bbox_set` |
