# `task_charts__multiseries__series_rank_at_category_label`

## Contract
- Domain: `charts`
- Scene id: `multiseries`
- Query id: `single`
- Answer schema: `string_label`
- Annotation schema: `point_map`
- Program contract: `select_ranked(series, value_at(category), extremum_direction, rank)`

## Program Contract
- `select_label(arg_ranked_extreme(series, value(target_category, series), direction={largest,smallest}, rank)); output=string_label; annotation=point_map(mark_center(target_category, all_series)); scene=multiseries; scope=series_rank_at_category_label`

## Implementation
- Source: `trace/tasks/charts/multiseries/series_rank_at_category_label.py`
- Class: `ChartsMultiseriesSeriesRankAtCategoryLabelTask`
- Prompt bundle: `prompts/charts/multiseries/charts_multiseries_v1.json`

## Annotation
Annotate every series mark in the queried category using keys of the form `<category>:<series>`.
