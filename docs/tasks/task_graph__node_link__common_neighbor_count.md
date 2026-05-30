# `task_graph__node_link__common_neighbor_count`

## 1) Identity
1. Domain: `graph`
2. Task group: `relation`
3. Scene id: `node_link`
4. Task id: `task_graph__node_link__common_neighbor_count`
5. Objective: count shared adjacent nodes for two queried labels in undirected or directed node-link graphs.

## 2) Scene + task contract
1. Branch metadata: `query_id`
2. `query_id`: `undirected_common_neighbor_count`, `directed_common_successor_count`, or `directed_common_predecessor_count`
3. Supported `graph_directionality` values: `undirected|directed`
4. Supported `common_neighbor_mode` values: `undirected_common_neighbor`, `directed_common_successor`, `directed_common_predecessor`
5. `answer_gt.type`: `integer`
6. `evidence_gt.type`: `point_set`
7. Scene contract:
   - one single-panel labeled node-link graph,
   - simple unweighted graph only,
   - no self-loops or multi-edges,
   - directed branches reject reciprocal edge pairs,
   - visible node labels use one whole-image label format (`letters`, `numbers`, or `short_names`),
   - node count is sampled from `6..10`.
8. Query contract:
   - undirected branch counts nodes adjacent to both queried nodes,
   - common-successor branch counts nodes that both queried nodes point to directly,
   - common-predecessor branch counts nodes that point directly to both queried nodes,
   - answer support is `0..4`, including zero-answer cases,
   - answer is the count of matching nodes.

## 3) Prompt contract
1. Bundle: `graph_relation_v0`
2. `scene_key`: `single_graph_relation`
3. `task_key`: `common_neighbor_count_query`
4. Modes: `answer_only`, `answer_and_evidence`
5. Answer-only JSON shape: `{"answer":2}`
6. Answer+evidence JSON shape: `{"evidence":[[180,220],[310,180]],"answer":2}`
7. Prompt-facing evidence uses pixel-space node-center points for every matching node.
8. When `label_variant=short_names`, prompt references to queried labels are quoted, for example node `"Abby"`.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the unordered `point_set` of pixel centers for all nodes matching the active query branch: adjacent to both queried nodes, pointed to by both queried nodes, or pointing to both queried nodes.
2. `answer_gt.value == len(evidence_gt.value)` by construction, including zero-answer cases where evidence is an empty array.
3. `execution_trace.common_neighbor_mode` records the exact relation mode.
4. `execution_trace.query_label_a` and `execution_trace.query_label_b` record the two queried labels.
5. `execution_trace.matching_labels` records the symbolic witness labels in deterministic label order.
6. `scene_ir.entities` stores node labels, degrees, in-degrees, out-degrees, neighbors/successors/predecessors, center points, node bboxes, query-node flags, and `is_common_neighbor_node`.
7. `projected_evidence` includes `point_set`, `pixel_point_set`, and `pixel_bbox_set`.

## 5) Visual policy
1. Rendering uses the shared graph light-panel style from `configs/domains/graph/base.yaml`.
2. Directed branches render arrowheads and reject reciprocal edge pairs so the common predecessor/successor relation remains readable.
3. Node label format, edge routing, glyph style, named node color, layout transform, and layout are visual variation only.
4. The prompt never refers to node position, color, or shape as semantic evidence.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same finalized adjacency map and rendered node assignment.
3. Generation directly constructs graphs with exactly the requested count of matching nodes, then verifies the witness set before returning.
4. No semantic auto-relaxation: failures do not weaken the graph, directionality, label, or relation contract.

## 7) Complexity + tests
1. Complexity components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Tests: `tests/test_graph_relation_common_neighbor_count_contracts.py`, `tests/test_graph_relation_common_neighbor_count_tasks.py`, `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
