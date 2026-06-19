# `task_charts__multiseries__ranked_pair_ratio_extremum_label`

## Contract
- Domain: `charts`
- Scene id: `multiseries`
- Query id: `single`
- Answer schema: `string_label`
- Annotation schema: `point_map`
- Program contract: `select_ranked(categories, ratio(value(numerator_series), value(denominator_series)), extremum_direction, rank)`

## Program Contract
- `select_label(arg_ranked_extreme(categories, ratio(value(category, numerator_series), value(category, denominator_series)), direction={largest,smallest}, rank)); output=string_label; annotation=point_map(mark_center(answer_category, {numerator_series,denominator_series})); scene=multiseries; scope=ranked_pair_ratio_extremum_label`

## Implementation
- Source: `trace/tasks/charts/multiseries/ranked_pair_ratio_extremum_label.py`
- Class: `ChartsMultiseriesRankedPairRatioExtremumTask`
- Prompt bundle: `prompts/charts/multiseries/charts_multiseries_v1.json`

## Annotation
Annotate the numerator and denominator series marks in the answer category using keys of the form `<category>:<series>`.
