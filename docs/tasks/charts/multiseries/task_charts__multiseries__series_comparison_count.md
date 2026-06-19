# `task_charts__multiseries__series_comparison_count`

## Contract
- Domain: `charts`
- Scene id: `multiseries`
- Query id: `single`
- Answer schema: `integer_count`
- Annotation schema: `point_map`
- Program contract: `count(filter(categories, compare(value(series_a), value(series_b), comparison)))`

## Program Contract
- `count(filter(categories, compare(value(category, series_a), value(category, series_b), relation={greater_than,less_than}))); output=integer_count; annotation=point_map(mark_center(matching_category, {series_a,series_b})); scene=multiseries; scope=series_comparison_count`

## Implementation
- Source: `trace/tasks/charts/multiseries/series_comparison_count.py`
- Class: `ChartsMultiseriesSeriesComparisonCountTask`
- Prompt bundle: `prompts/charts/multiseries/charts_multiseries_v1.json`

## Annotation
Annotate the two queried series marks in every counted category using keys of the form `<category>:<series>`.
