# `task_charts__heatmap__condition_run_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `heatmap`
3. Source implementation: `trace/tasks/charts/heatmap/condition_run_extremum_label.py`
4. Query id: `single`
5. Condition kind is a sampled generation parameter; it does not change the public query branch.

## Implementation
1. Registered class: `trace.tasks.charts.heatmap.condition_run_extremum_label.ChartsHeatmapConditionRunExtremumLabelTask`
2. Prompt lookup: `prompts/charts/heatmap/charts_heatmap_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Program Contract
`arg_extreme(row_label, longest_run(filter(row_cells, condition_kind)), direction=largest); output=string_label; annotation=bbox_set(winning_consecutive_run_cells); scene=heatmap; scope=condition_run_extremum_label`

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `bbox_set`.
3. Annotation marks the winning consecutive run cells from left to right.
4. Axes, legend, title, and distractor text are context unless the task explicitly asks for them as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `arg_extreme.longest_axis_run` | `string_label` | `bbox_set` |
