# `task_charts__region_map__legend_predicate_region_count`

## Contract
1. Domain: `charts`
2. Scene id: `region_map`
3. Source implementation domain/group: `charts/map`
4. Query id: sampled internally and recorded in `query_id`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.map.choropleth_region_label.ChartsMapLegendPredicateRegionCountTask`
2. Prompt lookup domain/group: `charts/map`
3. Generation is deterministic for the same seed, params, and task versions.
4. Answers and evidence are verifier-backed by trace metadata, not image pixels.
