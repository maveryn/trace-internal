# `task_graph__node_link__component_membership_count`

## 1) Identity
1. Domain: `graph`
2. Task group: `relation`
3. Scene id: `node_link`
4. Task id: `task_graph__node_link__component_membership_count`
5. Objective: count the size of a connected component under direct or one-edge-edit conditions.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. `query_id`: `same_component_count`, `largest_component_size`, `component_size_after_edge_removal`, or `component_size_after_edge_addition`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `point_set`
5. Supported graph type: simple undirected node-link graph.
6. The answer is the number of nodes in the requested component set.

## 3) Prompt Contract
1. Bundle: `graph_relation_v0` for same-component and edge-edit queries.
2. Bundle: `graph_comparison_v0` for the largest-component query.
3. Answer-only JSON: `{"answer":3}`
4. Answer+evidence JSON: `{"evidence":[[180,220],[310,180],[430,260]],"answer":3}`
5. Evidence instructions use pixel-space node-center points for every node in the counted component.

## 4) Verification
1. The verifier payload stores component labels, node centers, and projected point evidence.
2. `answer_gt.value == len(evidence_gt.value)`.
3. For edge-edit branches, component membership is computed after the hypothetical edge addition/removal recorded in trace metadata.
4. Earlier narrower public ids were absorbed into this task's `query_id` branches and should not be reintroduced.
