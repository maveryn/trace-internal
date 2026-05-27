# `task_charts__part_whole__order_share_sum_value`

## Contract
1. Domain: `charts`
2. Scene id: `part_whole`
3. Source implementation domain/group: `charts/composition`
4. Query id: `contiguous_chart_order_sum`, `positional_segment_share_sum`
5. Public `query_variant` is `default`; semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.composition.share_arithmetic_value.ChartsCompositionChartOrderShareSumValueTask`
2. Prompt lookup domain/group: `charts/composition`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
