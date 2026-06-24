# `task_charts__waterfall__remove_step_final_total`

## Contract
1. Domain: `charts`
2. Scene id: `waterfall`
3. Source implementation: `trace/tasks/charts/waterfall/remove_step_final_total.py`
4. Public query id: `single`
5. Prompt query key: `remove_step_final_total`

## Implementation
1. Registered class: `trace.tasks.charts.waterfall.remove_step_final_total.ChartsWaterfallRemoveStepFinalTotalTask`
2. Prompt bundle: `prompts/charts/waterfall/charts_waterfall_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `bbox_map`.
3. `final_total_value` marks the printed final-total value.
4. `target_contribution_value` marks the printed signed contribution value.
5. `target_step_label` marks the visible step label for the contribution being removed.

## Program Contract
`final_total - delta(target_step); target_step=visible_step_label; output=integer_value; annotation=bbox_map(final_total_value,target_contribution_value,target_step_label); scene=waterfall; scope=remove_step_final_total`

## Query Details

| Query id | Program contract | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `final_total - delta(target_step); target_step=visible_step_label; output=integer_value; annotation=bbox_map(final_total_value,target_contribution_value,target_step_label); scene=waterfall; scope=remove_step_final_total` | `integer_value` | `bbox_map` |
