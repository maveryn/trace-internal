# `task_charts__multiseries__ranked_change_extremum_label`

## Contract
- Domain: `charts`
- Scene id: `multiseries`
- Query id: `single`
- Answer schema: `string_label`
- Annotation schema: `point_map`
- Program contract: `select_ranked(categories, change(value(series_a), value(series_b), change_measure), direction, rank)`

## Program Contract
- `select_label(arg_ranked_extreme(categories, change(value(category, series_a), value(category, series_b), measure), direction, rank)); output=string_label; annotation=point_map(mark_center(answer_category, {series_a,series_b})); scene=multiseries; scope=ranked_change_extremum_label`

## Implementation
- Source: `trace/tasks/charts/multiseries/ranked_change_extremum_label.py`
- Class: `ChartsMultiseriesRankedChangeExtremumTask`
- Prompt bundle: `prompts/charts/multiseries/charts_multiseries_v1.json`

## Annotation
Annotate the two queried series marks in the answer category using keys of the form `<category>:<series>`.
