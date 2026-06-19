# `task_charts__multiseries__ranked_series_share_extremum_label`

## Contract
- Domain: `charts`
- Scene id: `multiseries`
- Query id: `single`
- Answer schema: `string_label`
- Annotation schema: `point_map`
- Program contract: `select_ranked(categories, ratio(value(target_series), sum(series_values)), extremum_direction, rank)`

## Program Contract
- `select_label(arg_ranked_extreme(categories, ratio(value(category, target_series), sum(series_values(category))), direction={largest,smallest}, rank)); output=string_label; annotation=point_map(mark_center(answer_category, all_series)); scene=multiseries; scope=ranked_series_share_extremum_label`

## Implementation
- Source: `trace/tasks/charts/multiseries/ranked_series_share_extremum_label.py`
- Class: `ChartsMultiseriesRankedSeriesShareExtremumTask`
- Prompt bundle: `prompts/charts/multiseries/charts_multiseries_v1.json`

## Annotation
Annotate every series mark in the answer category using keys of the form `<category>:<series>`.
