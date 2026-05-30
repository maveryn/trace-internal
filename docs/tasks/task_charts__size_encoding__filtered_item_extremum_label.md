# `task_charts__size_encoding__filtered_item_extremum_label`

## Contract
1. Domain: `charts`
2. Scene id: `size_encoding`
3. Source implementation domain/group: `charts/size_encoding`
4. Query id: `filtered_item_extremum_label`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.size_encoding.comparison_label.ChartsSizeEncodingFilteredItemExtremumLabelTask`
2. Prompt lookup domain/group: `charts/size_encoding`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.

## Evidence
1. Public evidence type: `bbox_set`.
2. The set contains exactly one bbox around the answer item mark and label.
3. The category filter is grounded by the item's visible category marker in the same bbox; the category legend is not included as separate evidence.
