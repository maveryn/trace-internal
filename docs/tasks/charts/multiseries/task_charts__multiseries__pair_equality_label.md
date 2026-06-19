# `task_charts__multiseries__pair_equality_label`

## Contract
- Domain: `charts`
- Scene id: `multiseries`
- Query id: `single`
- Answer schema: `string_label`
- Annotation schema: `point_map`
- Program contract: `select_unique(categories, value(series_a) == value(series_b))`

## Program Contract
- `select_label(unique(category where value(category, series_a) == value(category, series_b))); output=string_label; annotation=point_map(mark_center(answer_category, {series_a,series_b})); scene=multiseries; scope=pair_equality_label`

## Implementation
- Source: `trace/tasks/charts/multiseries/pair_equality_label.py`
- Class: `ChartsMultiseriesPairEqualityLabelTask`
- Prompt bundle: `prompts/charts/multiseries/charts_multiseries_v1.json`

## Annotation
Annotate the two queried series marks in the answer category using keys of the form `<category>:<series>`.
