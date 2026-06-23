# `task_charts__radial_progress__remaining_threshold_count`

## Contract
1. Domain: `charts`
2. Scene id: `radial_progress`
3. Task id: `task_charts__radial_progress__remaining_threshold_count`
4. Objective contract: `remaining_threshold_count`
5. Supported `query_id` values: `single`

## Program Contract
`count(filter(radial_progress_widgets, 100 - progress_value(widget) >= remaining_threshold)); scene=radial_progress; scope=remaining_threshold_count`

## Implementation
1. Registered class: `trace.tasks.charts.radial_progress.remaining_threshold_count.ChartsRadialProgressRemainingThresholdCountTask`
2. Prompt bundle: `charts_radial_progress_v1`
3. Scene key: `radial_progress_scene`
4. Task key: `radial_progress_condition_count_query`
5. Prompt query key: `remaining_at_least_threshold_count`

## Annotation Contract
1. Answer schema: `integer_count`
2. Annotation schema: `bbox_set`
3. Annotation marks one widget card bbox for each counted widget.
4. Titles, tick marks, card decorations, and uncounted widgets are context, not annotation.

## Query Details

| Query id | Program argument | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `predicate=remaining_at_least_threshold` | `integer_count` | `bbox_set` |
