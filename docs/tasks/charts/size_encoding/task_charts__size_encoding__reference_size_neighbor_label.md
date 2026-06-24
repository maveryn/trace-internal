# `task_charts__size_encoding__reference_size_neighbor_label`

## Contract
1. Domain: `charts`
2. Scene id: `size_encoding`
3. Source implementation: `trace/tasks/charts/size_encoding/reference_size_neighbor_label.py`
4. Supported `query_id` values: `single`
5. Semantic query details are recorded in trace params.

## Implementation
1. Registered class: `trace.tasks.charts.size_encoding.reference_size_neighbor_label.ChartsSizeEncodingReferenceSizeNeighborLabelTask`
2. Prompt lookup domain/group: `charts/size_encoding`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `string_label`.
2. Annotation schema: `bbox_map`.
3. Annotation maps `reference_item` and `answer_item` to their displayed boxes.
4. Renderer context such as legends, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
`select_label(argmin(filter(items, category=target_category and item != reference_item), abs(encoded_value(item) - encoded_value(reference_item)))); output=string_label; annotation=bbox_map(reference_item,answer_item); scene=size_encoding; scope=reference_size_neighbor_label`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `selection.nearest_label` | `string_label` | `bbox_map` |
