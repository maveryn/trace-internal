# `task_charts__radar__threshold_metric_count_for_panel`

## Taxonomy

1. Domain: `charts`
2. Scene id: `radar`
3. Source implementation scene package: `charts/radar`
4. Public task id: `task_charts__radar__threshold_metric_count_for_panel`

## Implementation

1. Registered class: `trace.tasks.charts.radar.threshold_metric_count_for_panel.ChartsRadarThresholdMetricCountForPanelTask`
2. Prompt lookup domain/scene: `charts/radar`
3. Default dataset: enabled

## Contract

1. Supported `query_id` values: `single`
2. Answer schema: `integer_count`
3. Annotation schema: `point_set`
4. Annotation marks one point at each counted radar vertex in the requested panel.

## Program Contract

`count(filter(metrics_in_panel, value(selected_panel, metric) > threshold)); scene=radar; scope=threshold_metric_count_for_panel`

Arguments:
- `selected_panel`: sampled visible radar panel label
- `threshold`: sampled visible ring-scale integer
