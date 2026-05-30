# `task_charts__waterfall__running_total_value`

## Contract
1. Domain: `charts`
2. Scene id: `waterfall`
3. Source implementation domain/group: `charts/waterfall`
4. Query id: `running_total_after_step`
5. Semantic query details are recorded in `query_id` and trace params.
6. Evidence type: `bbox_set` over the printed values and target step label used for the cumulative total.

## Implementation
1. Registered class: `trace.tasks.charts.waterfall.panel_query.ChartsWaterfallRunningTotalValueTask`
2. Prompt lookup domain/group: `charts/waterfall`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
