# `task_charts__part_whole__ordered_segment_value`

## Contract
1. Domain: `charts`
2. Scene id: `part_whole`
3. Source implementation domain/group: `charts/composition`
4. Query id: sampled internally and recorded in `query_id`
5. Answer type: integer
6. Evidence type: `keyed_point_map`
7. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.composition.share_arithmetic_value.ChartsCompositionChartOrderedSegmentValueTask`
2. Prompt lookup domain/group: `charts/composition`
3. Generation is deterministic for the same seed, params, and task versions.
4. Answers and evidence are verifier-backed by trace metadata, not image pixels.
5. Prompt-facing evidence maps each supporting category label to the center
   point of its chart segment. Count-conversion queries use the displayed total
   for answer verification, but `total_count` remains render metadata rather
   than public evidence.
