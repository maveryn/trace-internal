# Graph Task-Unit Audit

Task-unit audit for `domain=graph` using `docs/workflows/TASK_UNIT_AUDIT.md`.

## Domain summary
1. The graph domain is one of the cleanest task-unit inventories in the repo.
2. Every current graph task uses the same broad visual grammar (single labeled node-link graph), but each task still corresponds to a clearly different grounded graph-theoretic witness.
3. The domain benefits from strong evidence-type separation across node sets, edge sets, and ordered paths/sequences.
4. Recommended domain outcome:
   - `Keep`: `10`
   - `Split`: `0`
   - `Merge`: `0`
   - `Retire`: `0`

## Task findings

### `task_graph_comparison_largest_component_size`
- Outcome: `Keep`
- Why: one coherent connected-component extremum family over a single undirected graph.
- Scene variety: moderate; fixed node-link scaffold with topology, label, glyph, and layout variation.
- Query variety: narrow but still appropriate for a standalone extremum task (`largest_component_size`).
- Grounding necessity: strong; the model must identify all connected components and compare their sizes.
- Evidence fit: good; the largest component node labels are the natural witness.
- Follow-up: none required now.

### `task_graph_counting_articulation_point_count`
- Outcome: `Keep`
- Why: one coherent articulation-point counting family with a stable node-witness contract.
- Scene variety: moderate with strong topology variation under one graph scaffold.
- Query variety: narrow but legitimate (`articulation_point_count`).
- Grounding necessity: strong; the model must reason about graph connectivity under node removal.
- Evidence fit: good; articulation-node labels are the right witness.
- Follow-up: none required now.

### `task_graph_counting_bridge_count`
- Outcome: `Keep`
- Why: one coherent bridge-edge counting family with a stable edge-witness contract.
- Scene variety: moderate with strong topology variation under one graph scaffold.
- Query variety: narrow but legitimate (`bridge_count`).
- Grounding necessity: strong; the model must reason about graph connectivity under edge removal.
- Evidence fit: good; bridge endpoint pairs are the right witness.
- Follow-up: none required now.

### `task_graph_counting_degree_count`
- Outcome: `Keep`
- Why: one coherent degree-counting family even though it spans undirected degree and directed in/out-degree.
- Scene variety: moderate; all variants remain single node-link graphs with one queried degree threshold.
- Query variety: moderate (`degree_count|in_degree_count|out_degree_count`) but still one stable node-qualification family.
- Grounding necessity: strong; the model must inspect local adjacency or arrow direction around nodes.
- Evidence fit: good; qualifying node labels stay the same witness type across all variants.
- Follow-up: none required now.

### `task_graph_optimization_minimum_spanning_tree_weight`
- Outcome: `Keep`
- Why: one coherent weighted-edge optimization family with a stable MST witness contract.
- Scene variety: moderate; one weighted connected graph scaffold with topology and layout variation.
- Query variety: narrow but appropriate (`minimum_spanning_tree_weight`).
- Grounding necessity: strong; the solver must use both adjacency and rendered edge weights.
- Evidence fit: good; MST edge pairs are the natural witness.
- Follow-up: none required now.

### `task_graph_order_topological_position`
- Outcome: `Keep`
- Why: one coherent topological-order family with a stable ordered-sequence witness.
- Scene variety: moderate; one DAG scaffold with directed edges and stable query-node markup.
- Query variety: narrow but appropriate (`topological_position`).
- Grounding necessity: strong; the model must infer the unique topological order from the visible DAG.
- Evidence fit: good; the full ordered label sequence is the right witness.
- Follow-up: none required now.

### `task_graph_path_shortest_path_length`
- Outcome: `Keep`
- Why: one coherent unique-shortest-path family over a visible source-goal graph.
- Scene variety: moderate; one node-link scaffold with topology/layout variation plus directed-vs-undirected path variants.
- Query variety: modest but coherent (`shortest_path_length|directed_shortest_path_length`).
- Grounding necessity: strong; the model must trace the visible graph structure and preserve path order.
- Evidence fit: good; ordered node-label path evidence is stable across both variants.
- Follow-up: none required now.

### `task_graph_relation_reachable_count`
- Outcome: `Keep`
- Why: one coherent directed reachability family rooted at a queried source node.
- Scene variety: moderate with strong topology variation under a stable directed-graph scaffold.
- Query variety: narrow but appropriate (`reachable_count`).
- Grounding necessity: strong; the model must follow arrow direction through the graph.
- Evidence fit: good; reachable node labels are the right witness.
- Follow-up: none required now.

### `task_graph_relation_same_component_count`
- Outcome: `Keep`
- Why: one coherent rooted connected-component family over an undirected graph.
- Scene variety: moderate; stable undirected node-link scaffold with topology/layout variation.
- Query variety: narrow but appropriate (`same_component_count`).
- Grounding necessity: strong; the model must determine the full connected component containing the queried node.
- Evidence fit: good; same-component node labels are the right witness.
- Follow-up: none required now.

### `task_graph_relation_unique_cycle_size`
- Outcome: `Keep`
- Why: one coherent unique-cycle family over a connected unicyclic graph.
- Scene variety: moderate with strong topology variation under one stable scaffold.
- Query variety: narrow but appropriate (`unique_cycle_size`).
- Grounding necessity: strong; the model must identify exactly which nodes lie on the single cycle.
- Evidence fit: good; cycle-node labels are the natural witness.
- Follow-up: none required now.

## Recommended next action
1. Leave the graph domain unchanged for now.
2. Use graph as one of the benchmark examples of a well-calibrated task-unit inventory: shared visual grammar, but distinct grounded witness families.
