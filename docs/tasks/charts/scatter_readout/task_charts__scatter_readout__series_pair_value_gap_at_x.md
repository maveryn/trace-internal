# `task_charts__scatter_readout__series_pair_value_gap_at_x`

## Contract
1. Domain: `charts`
2. Scene id: `scatter_readout`
3. Public task id: `task_charts__scatter_readout__series_pair_value_gap_at_x`
4. Supported `query_id` values: `single`
5. The task always computes an absolute y-value gap between two visible series at one resolved x-axis label.

## Program Contract
- `abs(value(series_a,x_label)-value(series_b,x_label)); output=integer_value; annotation=bbox_map(target_point_readout,comparison_point_readout,x_axis_label); scene=scatter_readout; scope=series_pair_value_gap_at_x`

## Implementation
1. Registered class: `trace.tasks.charts.scatter_readout.series_pair_value_gap_at_x.ChartsScatterSeriesPairValueGapAtXTask`
2. Prompt bundle: `prompts/charts/scatter_readout/charts_scatter_readout_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `bbox_map`.
3. Annotation maps `target_point_readout`, `comparison_point_readout`, and `x_axis_label` to the supporting [x0,y0,x1,y1] pixel boxes.
4. Axes, legends, titles, and distractor text are metadata unless named as one of the annotation roles.

## Query Details

| Query id | Program arguments | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `operation=absolute_difference` | `integer_value` | `bbox_map` |
