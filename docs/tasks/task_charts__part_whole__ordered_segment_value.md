# `task_charts__part_whole__ordered_segment_value`

## Contract
1. Domain: `charts`
2. Scene id: `part_whole`
3. Source implementation domain/group: `charts/composition`
4. Query id: sampled internally and recorded in `query_id`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.composition.share_arithmetic_value.ChartsCompositionChartOrderedSegmentValueTask`
2. Prompt lookup domain/group: `charts/composition`
3. Generation is deterministic for the same seed, params, and task versions.
4. Answers and evidence are verifier-backed by trace metadata, not image pixels.
