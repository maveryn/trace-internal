# `task_charts__radar__highlighted_metric_threshold_panel_count`

## Taxonomy

1. Domain: `charts`
2. Scene id: `radar`
3. Source implementation scene package: `charts/radar`
4. Public task id: `task_charts__radar__highlighted_metric_threshold_panel_count`

## Implementation

1. Registered class: `trace.tasks.charts.radar.highlighted_metric_threshold_panel_count.ChartsRadarHighlightedMetricThresholdPanelCountTask`
2. Prompt lookup domain/scene: `charts/radar`
3. Default dataset: enabled

## Contract

1. Supported `query_id` values: `single`
2. Answer schema: `integer_count`
3. Annotation schema: `bbox_set`
4. Annotation marks one bbox around each radar panel whose highlighted metric is above the sampled threshold.

## Program Contract

`count(filter(radar_panels, value(panel, highlighted_metric) > threshold)); scene=radar; scope=highlighted_metric_threshold_panel_count`

Arguments:
- `highlighted_metric`: sampled visible metric spoke label
- `threshold`: sampled visible ring-scale integer
