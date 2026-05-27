# `task_charts__parallel_coords__axis_condition_count`

## Contract
1. Domain: `charts`
2. Scene id: `parallel_coords`
3. Source implementation domain/group: `charts/parallel_coordinates`
4. Query id: `above_on_both_axes`, `above_on_one_below_on_other`, `below_on_both_axes`
5. Public `query_variant` is `default`; semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.parallel_coordinates.profile_query.ChartsParallelCoordinatesAxisConditionCountTask`
2. Prompt lookup domain/group: `charts/parallel_coordinates`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
