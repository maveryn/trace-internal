# `task_charts__radar__matching_condition_panel_count`

## Taxonomy

1. Domain: `charts`
2. Scene id: `radar`
3. Source implementation scene package: `charts/radar`
4. Public task id: `task_charts__radar__matching_condition_panel_count`

## Implementation

1. Registered class: `trace.tasks.charts.radar.matching_condition_panel_count.ChartsRadarMatchingConditionPanelCountTask`
2. Prompt lookup domain/scene: `charts/radar`
3. Default dataset: enabled

## Contract

1. Supported `query_id` values: `single`
2. Answer schema: `integer_count`
3. Annotation schema: `bbox_set`
4. Annotation marks one bbox around each radar panel with at least the requested number of metrics above the sampled threshold.

## Program Contract

`count(filter(radar_panels, count(filter(metrics, value(panel, metric) > threshold)) >= minimum_metric_count)); scene=radar; scope=matching_condition_panel_count`

Arguments:
- `threshold`: sampled visible ring-scale integer
- `minimum_metric_count`: sampled integer lower bound on high metric vertices
