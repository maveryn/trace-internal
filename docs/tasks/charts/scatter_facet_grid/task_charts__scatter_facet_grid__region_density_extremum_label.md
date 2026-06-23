# `task_charts__scatter_facet_grid__region_density_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `scatter_facet_grid`
3. Task id: `task_charts__scatter_facet_grid__region_density_extremum_label`
4. Supported `query_id`s: `upper_right_density_extremum_label`, `upper_left_density_extremum_label`, `lower_right_density_extremum_label`, `lower_left_density_extremum_label`

## Implementation
1. Registered class: `trace.tasks.charts.scatter_facet_grid.region_density_extremum_label.ChartsScatterFacetGridRegionDensityExtremumLabelTask`
2. Prompt bundle: `prompts/charts/scatter_facet_grid/charts_scatter_facet_grid_v1.json`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Program Contract
`argmax_label(panel, local_point_density(panel, target_region)); scene=scatter_facet_grid; scope=region_density_extremum_label`

## Annotation Contract
1. Answer schema: `string`.
2. Annotation schema: `bbox`.
3. Annotation should mark the densest supporting point region inside the answer panel's queried quadrant, not the panel title, axes, or surrounding context.
4. Renderer context such as axes, highlighted quadrant guides, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `upper_right_density_extremum_label` | `target_region=upper_right` | `string` | `bbox` |
| `upper_left_density_extremum_label` | `target_region=upper_left` | `string` | `bbox` |
| `lower_right_density_extremum_label` | `target_region=lower_right` | `string` | `bbox` |
| `lower_left_density_extremum_label` | `target_region=lower_left` | `string` | `bbox` |
