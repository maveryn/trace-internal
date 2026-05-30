# `task_charts__region_map__group_filtered_region_value`

## Contract
1. Domain: `charts`
2. Scene id: `region_map`
3. Source implementation domain/group: `charts/map`
4. Query id: `group_filtered_region_value`
5. Answer type: integer total value.

## Implementation
1. Registered class: `trace.tasks.charts.map.choropleth_region_label.ChartsMapGroupFilteredRegionValueTask`
2. Prompt lookup domain/group: `charts/map`
3. This task fixes the scene to a world-country geographic region map.
4. Generation is deterministic for the same seed, params, and task versions.
5. Answers and evidence are verifier-backed by trace metadata, not image pixels.

## Evidence
1. Evidence type: `bbox_set`.
2. Boxes mark the visible geographic regions included in the sum.
