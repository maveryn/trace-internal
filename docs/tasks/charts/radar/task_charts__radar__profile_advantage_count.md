# `task_charts__radar__profile_advantage_count`

## Taxonomy

1. Domain: `charts`
2. Scene id: `radar`
3. Source implementation scene package: `charts/radar`
4. Public task id: `task_charts__radar__profile_advantage_count`

## Implementation

1. Registered class: `trace.tasks.charts.radar.profile_advantage_count.ChartsRadarProfileAdvantageCountTask`
2. Prompt lookup domain/scene: `charts/radar`
3. Default dataset: enabled

## Contract

1. Supported `query_id` values: `single`
2. Answer schema: `integer_count`
3. Annotation schema: `segment_set`
4. Annotation marks one segment per counted metric, connecting the two profile vertices on that metric spoke.

## Program Contract

`count(filter(metrics, value(profile_a, metric) > value(profile_b, metric))); scene=radar; scope=profile_advantage_count`

Arguments:
- `profile_a`: sampled visible legend label for the first profile
- `profile_b`: sampled visible legend label for the second profile
