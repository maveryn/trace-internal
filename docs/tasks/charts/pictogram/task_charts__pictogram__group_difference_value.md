# `task_charts__pictogram__group_difference_value`

## Contract
1. Domain: `charts`
2. Scene id: `pictogram`
3. Public task id: `task_charts__pictogram__group_difference_value`
4. Supported `query_id`: `single`

## Implementation
1. Registered class: `trace.tasks.charts.pictogram.group_difference_value.ChartsPictogramGroupDifferenceValueTask`
2. Prompt bundle: `prompts/charts/pictogram/charts_pictogram_v1.json`
3. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `bbox_map`.
3. Annotation maps each compared category label to the bbox around that category row.

## Program Contract

`difference(value(category_total(category_a, unit_scale)), value(category_total(category_b, unit_scale)), mode=absolute); output=integer_value; annotation=bbox_map(category_a_row,category_b_row); scene=pictogram; scope=group_difference_value`
