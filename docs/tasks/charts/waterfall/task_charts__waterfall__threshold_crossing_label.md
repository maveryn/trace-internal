# `task_charts__waterfall__threshold_crossing_label`

## Contract
1. Domain: `charts`
2. Scene id: `waterfall`
3. Source implementation: `trace/tasks/charts/waterfall/threshold_crossing_label.py`
4. Public query ids: `first_total_at_least_threshold`, `first_total_at_most_threshold`
5. Query ids are semantic prompt/program branches because the comparator changes.

## Implementation
1. Registered class: `trace.tasks.charts.waterfall.threshold_crossing_label.ChartsWaterfallThresholdCrossingLabelTask`
2. Prompt bundle: `prompts/charts/waterfall/charts_waterfall_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label_or_unanswerable`.
2. Annotation schema: `bbox_set_map`.
3. `running_values` contains printed value boxes from the start value through the first crossing step.
4. `threshold_label` contains the visible threshold-label box.
5. If the answer is `unanswerable`, annotation is an empty object.

## Program Contract
`first(label where running_total_after_step comparator threshold); comparator={at_least,at_most}; output=string_label_or_unanswerable; annotation=bbox_set_map(running_values,threshold_label) or empty; scene=waterfall; scope=threshold_crossing_label`

## Query Details

| Query id | Program contract | Answer schema | Annotation schema |
|---|---|---|---|
| `first_total_at_least_threshold` | `first(label where running_total_after_step >= threshold); output=string_label_or_unanswerable; annotation=bbox_set_map(running_values,threshold_label) or empty; scene=waterfall; scope=threshold_crossing_label` | `string_label_or_unanswerable` | `bbox_set_map` |
| `first_total_at_most_threshold` | `first(label where running_total_after_step <= threshold); output=string_label_or_unanswerable; annotation=bbox_set_map(running_values,threshold_label) or empty; scene=waterfall; scope=threshold_crossing_label` | `string_label_or_unanswerable` | `bbox_set_map` |
