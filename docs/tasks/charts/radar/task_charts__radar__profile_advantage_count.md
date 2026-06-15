# `task_charts__radar__profile_advantage_count`

## Contract
1. Domain: `charts`
2. Scene id: `radar`
3. Source implementation scene package: `charts/radar`
4. Query id: `single`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.radar.profile_advantage_count.ChartsRadarProfileAdvantageCountTask`
2. Prompt lookup domain/scene: `charts/radar`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `segment_set`.
3. Annotation is a `segment_set`; each segment is `[[x1, y1], [x2, y2]]` and connects the two named profile points for one counted metric.
4. Renderer context such as legends, axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `count.pairwise_comparison` | `integer_count` | `segment_set` |
