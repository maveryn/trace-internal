# `task_charts__parallel_coords__axis_delta_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `parallel_coords`
3. Source implementation domain/group: `charts/parallel_coordinates`
4. Query id: `largest_absolute_change_between_axes`, `largest_decrease_between_axes`, `largest_increase_between_axes`
5. Public `query_variant` is `default`; semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.parallel_coordinates.profile_query.ChartsParallelCoordinatesAxisDeltaExtremumLabelTask`
2. Prompt lookup domain/group: `charts/parallel_coordinates`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.
