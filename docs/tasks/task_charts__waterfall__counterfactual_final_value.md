# `task_charts__waterfall__counterfactual_final_value`

## Contract
1. Domain: `charts`
2. Scene id: `waterfall`
3. Source implementation domain/group: `charts/waterfall`
4. Query id: `remove_step_final_total`, `reverse_step_final_total`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.waterfall.panel_query.ChartsWaterfallCounterfactualFinalValueTask`
2. Prompt lookup domain/group: `charts/waterfall`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
