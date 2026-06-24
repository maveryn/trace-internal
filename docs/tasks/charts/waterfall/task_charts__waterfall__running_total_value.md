# `task_charts__waterfall__running_total_value`

## Contract
1. Domain: `charts`
2. Scene id: `waterfall`
3. Source implementation: `trace/tasks/charts/waterfall/running_total_value.py`
4. Public query id: `single`
5. Prompt query key: `running_total_after_step`

## Implementation
1. Registered class: `trace.tasks.charts.waterfall.running_total_value.ChartsWaterfallRunningTotalValueTask`
2. Prompt bundle: `prompts/charts/waterfall/charts_waterfall_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `bbox_set_map`.
3. `running_values` contains printed value boxes from the start value through the requested step.
4. `target_step_label` contains the visible x-axis label box for the requested step.

## Program Contract
`sum(start_value, signed_deltas_through(target_step)); target_step=visible_step_label; output=integer_value; annotation=bbox_set_map(running_values,target_step_label); scene=waterfall; scope=running_total_value`

## Query Details

| Query id | Program contract | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `sum(start_value, signed_deltas_through(target_step)); target_step=visible_step_label; output=integer_value; annotation=bbox_set_map(running_values,target_step_label); scene=waterfall; scope=running_total_value` | `integer_value` | `bbox_set_map` |
