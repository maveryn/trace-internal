# `task_graph__graph_options__structure_match_label`

## Summary
1. Domain: `graph`
2. Task group: `relation`
3. Scene id: `graph_options`
4. Goal: choose the labeled option graph that satisfies a structure relation against the top graph.
5. Public `query_variant`: `default`
6. Query ids: `same_structure_label`, `contained_subgraph_label`

## Contract
1. The scene shows one Reference or Target Graph panel and six labeled option panels.
2. Graphs may be undirected or directed; for directed instances, arrow directions matter.
3. `same_structure_label` asks for the option with the same labeled graph structure as the Reference, ignoring layout.
4. `same_structure_label` uses 4..6 nodes in the Reference and each option graph.
5. `contained_subgraph_label` asks for the option whose labeled nodes and edges are contained in the Target Graph.
6. `contained_subgraph_label` uses a 4..6-node Target Graph and 3..4-node option subgraphs.
7. Answers are option letters.
8. Evidence is a one-box `bbox_set` containing the selected option panel in final image pixel space.
9. Verifier payload stores node labels, edge pairs/arrows, option signatures, correct option id, `edge_mode`, and the sampled query rule.
