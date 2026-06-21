# `task_charts__pictogram__category_total_value`

## Contract
1. Domain: `charts`
2. Scene id: `pictogram`
3. Public task id: `task_charts__pictogram__category_total_value`
4. Supported `query_id`: `single`

## Implementation
1. Registered class: `trace.tasks.charts.pictogram.category_total_value.ChartsPictogramCategoryTotalValueTask`
2. Prompt bundle: `prompts/charts/pictogram/charts_pictogram_v1.json`
3. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `bbox`.
3. Annotation marks the requested category row as one `[x0, y0, x1, y1]` pixel box.

## Program Contract

`value(category_total(target_category, unit_scale)); output=integer_value; annotation=bbox(target_category_row); scene=pictogram; scope=category_total_value`
