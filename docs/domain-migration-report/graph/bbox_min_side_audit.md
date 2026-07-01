# Bbox Minimum-Side Audit From Existing Task Reviews

- Checked at: `2026-06-27T09:54:15Z`
- Review root: `review/task-reviews`
- Minimum required side: `24.0 px`
- Scenes: `10`
- Tasks: `60`
- Bbox-family runtime tasks: `11`
- Samples inspected: `6000`
- Bboxes inspected: `3133`
- Failing bbox tasks: `0`
- Invalid bbox tasks: `0`
- Missing review-artifact tasks: `0`
- Doc/runtime annotation mismatches: `0`

## Bbox-Family Task Observations

| Domain | Scene | Task | Runtime Type | Samples | Bboxes | Min W | Min H | Min Side | Status |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| graph | adjacency | `task_graph__adjacency__directed_strong_component_count` | ['bbox_set'] | 100 | 403 | 49 | 35 | 35 | pass |
| graph | adjacency | `task_graph__adjacency__mst_weight` | ['bbox_set'] | 100 | 466 | 61 | 61 | 61 | pass |
| graph | adjacency | `task_graph__adjacency__traversal_kth_label` | ['bbox_sequence'] | 100 | 425 | 88 | 36 | 36 | pass |
| graph | adjacency | `task_graph__adjacency__undirected_component_count` | ['bbox_set'] | 100 | 411 | 49 | 35 | 35 | pass |
| graph | graph_options | `task_graph__graph_options__contained_subgraph_label` | ['bbox'] | 100 | 100 | 551 | 235 | 235 | pass |
| graph | graph_options | `task_graph__graph_options__same_structure_label` | ['bbox'] | 100 | 100 | 551 | 235 | 235 | pass |
| graph | node_link | `task_graph__node_link__edge_between_nodes_label` | ['bbox'] | 100 | 100 | 36 | 24 | 24 | pass |
| graph | node_link | `task_graph__node_link__edge_text_count` | ['bbox_set'] | 100 | 300 | 35 | 24 | 24 | pass |
| graph | pedigree_chart | `task_graph__pedigree_chart__relatedness_coefficient_label` | ['bbox_set'] | 100 | 460 | 36 | 36 | 36 | pass |
| graph | pedigree_chart | `task_graph__pedigree_chart__relationship_label` | ['bbox_set'] | 100 | 268 | 36 | 36 | 36 | pass |
| graph | phylogeny_tree | `task_graph__phylogeny_tree__topology_outlier_label` | ['bbox'] | 100 | 100 | 589 | 419 | 419 | pass |
