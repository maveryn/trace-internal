# `task_charts__region_map__named_region_set_total_value`

## Contract
1. Domain: `charts`
2. Scene id: `region_map`
3. Source implementation domain/group: `charts/map`
4. Query id: `named_region_set_total_value`
5. The prompt names a set of visible region labels; the answer is the sum of the printed integer values in those regions.

## Implementation
1. Registered class: `trace.tasks.charts.map.choropleth_region_label.ChartsMapNamedRegionSetTotalValueTask`
2. Prompt lookup domain/group: `charts/map`
3. Generation is deterministic for the same seed, params, and task versions.
4. Answers and evidence are verifier-backed by trace metadata, not image pixels.

## Evidence
1. Evidence type: `bbox_set`.
2. Boxes mark the named regions whose printed integer values are included in the total.
