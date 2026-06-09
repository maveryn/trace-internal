# `task_charts__population_pyramid__side_gap_extremum_label`

## Taxonomy

1. Domain: `charts`
2. Scene id: `population_pyramid`
3. Source implementation domain/group: `charts/population_pyramid`
4. Public task id: `task_charts__population_pyramid__side_gap_extremum_label`

## Implementation

1. Registered class: `trace.tasks.charts.population_pyramid.pyramid_query.ChartsPopulationPyramidSideGapExtremumLabelTask`
2. Prompt lookup domain/group: `charts/population_pyramid`
3. Default dataset: enabled

## Contract

1. Query ids: `largest_side_gap_label`, `smallest_nonzero_side_gap_label`
2. Answer type: string age-group label
3. Annotation type: `bbox_set`
4. Annotation marks one bbox around the paired left/right bars in the answer row.
