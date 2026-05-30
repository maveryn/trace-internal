# `task_charts__size_encoding__reference_size_neighbor_label`

## Contract
1. Domain: `charts`
2. Scene id: `size_encoding`
3. Source implementation domain/group: `charts/size_encoding`
4. Query id: `reference_size_neighbor_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.size_encoding.comparison_label.ChartsSizeEncodingReferenceSizeNeighborLabelTask`
2. Prompt lookup domain/group: `charts/size_encoding`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.

## Evidence
1. Public evidence type: `keyed_bbox_map`.
2. Required keys are `reference_item` and `answer_item`.
3. Each value is the bbox around the corresponding visible item mark and label.
