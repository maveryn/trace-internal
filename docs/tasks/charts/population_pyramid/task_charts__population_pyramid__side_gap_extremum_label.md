# `task_charts__population_pyramid__side_gap_extremum_label`

## Taxonomy

1. Domain: `charts`
2. Scene id: `population_pyramid`
3. Source implementation scene package: `charts/population_pyramid`
4. Public task id: `task_charts__population_pyramid__side_gap_extremum_label`

## Implementation

1. Registered class: `trace.tasks.charts.population_pyramid.side_gap_extremum_label.ChartsPopulationPyramidSideGapExtremumLabelTask`
2. Prompt lookup domain/scene: `charts/population_pyramid`
3. Default dataset: enabled

## Contract

1. Query ids: `largest_side_gap_label`, `smallest_nonzero_side_gap_label`
2. Answer schema: `string_label`.
3. Annotation schema: `bbox_set`
4. Annotation marks one bbox around the paired left/right bars in the answer row.
