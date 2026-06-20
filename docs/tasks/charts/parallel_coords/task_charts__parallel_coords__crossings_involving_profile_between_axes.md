# `task_charts__parallel_coords__crossings_involving_profile_between_axes`

## Contract
1. Domain: `charts`
2. Scene id: `parallel_coords`
3. Source implementation domain/scene: `charts/parallel_coords`
4. Supported `query_id`: `single`
5. The semantic prompt branch is `crossings_involving_profile_between_axes`; public replay/review metadata uses `single`.

## Implementation
1. Registered class: `trace.tasks.charts.parallel_coords.crossings_involving_profile_between_axes.ChartsParallelCoordinatesCrossingsInvolvingProfileBetweenAxesTask`
2. Prompt lookup domain/scene: `charts/parallel_coords`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Program Contract
`count(intersections(reference_profile_line, other_profile_lines, adjacent_axis_interval)); output=integer_count; annotation=point_set(crossing_points); scene=parallel_coords; scope=crossings_involving_profile_between_axes`

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `point_set`.
3. Annotation marks one point at each counted crossing involving the named reference profile.
4. Axes, labels, threshold text, and decorative context are renderer context unless explicitly requested.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `count.reference_profile_intersections` | `integer_count` | `point_set` |
