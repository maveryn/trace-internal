# `task_graph__node_link__edge_attribute_label`

## 1) Identity
1. Domain: `graph`
2. Task group: `relation`
3. Scene id: `node_link`
4. Task id: `task_graph__node_link__edge_attribute_label`
5. Objective: read the visible text label attached to a specified edge, directed arrow, or first edge on a unique shortest path.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. `query_id`: `edge_between_nodes_label`, `directed_edge_between_nodes_label`, or `shortest_path_first_edge_label`
3. Supported `graph_directionality`: `undirected|directed`
4. `answer_gt.type`: `string`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - one single-panel labeled node-link graph,
   - every edge or arrow has a visible boxed text label,
   - no self-loops or multi-edges,
   - directed branches reject reciprocal edge pairs,
   - visible node labels use one whole-image label format (`letters`, `numbers`, or `short_names`),
   - node count is sampled from `5..8`.
7. Query contract:
   - undirected branch asks for the label on the edge between two nodes,
   - directed branch asks for the label on the arrow from one node to another,
   - shortest-path branch asks for the label on the first edge or arrow along a unique shortest path,
   - answer is the lowercase text label shown on the active branch's requested edge, arrow, or first shortest-path edge,
   - default edge-label support is `feeds|blocks|joins|routes|checks|updates`.

## 3) Prompt Contract
1. Bundle: `graph_relation_v0`
2. `scene_key`: `single_graph_relation`
3. `task_key`: `edge_attribute_label_query`
4. Modes: `answer_only`, `answer_and_evidence`
5. Answer-only JSON shape: `{"answer":"feeds"}`
6. Answer+evidence JSON shape: `{"evidence":[[240,190,308,214]],"answer":"feeds"}`
7. Prompt-facing evidence is one pixel-space bbox around the visible edge-label text for the active branch's requested edge, arrow, or first shortest-path edge.
8. When `label_variant=short_names`, prompt references to queried node labels are quoted, for example node `"Abby"`.

## 4) Evidence + Trace Contract
1. Prompt-facing evidence is a one-item `bbox_set` around the active branch's requested edge-label box.
2. `answer_gt.value` equals the visible edge label recorded for `execution_trace.query_edge`.
3. `execution_trace.query_edge` records the symbolic queried edge; for shortest-path queries this is the first edge on `execution_trace.query_path_labels`.
4. `execution_trace.edge_attribute_labels_by_label_pair` records every rendered edge label.
5. `execution_trace.query_path_labels` records the path endpoints and intermediate nodes for shortest-path queries.
6. `scene_ir.entities` stores node geometry, edge geometry, edge-label bboxes, edge-label values, and `is_query_edge`.
7. `projected_evidence` includes `bbox_set` and `pixel_bbox_set`.

## 5) Visual Policy
1. Rendering uses the shared graph light-panel style from `configs/domains/graph/base.yaml`.
2. Edge-label boxes are placed by the shared node-link renderer and avoid nodes, other edge labels, and edge segments where possible.
3. Node label format, edge routing, glyph style, named node color, layout transform, and layout are visual variation only.
4. Post-render graph noise follows the graph-domain coordinate-preserving noise policy.

## 6) Determinism + Constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same finalized edge-label assignment and rendered edge-label bbox.
3. The query id and target answer label are decoupled under seeded cycling so calibration samples cover all labels within each query branch.
4. No semantic auto-relaxation: failures do not weaken graph directionality, label support, or edge-label visibility constraints.

## 7) Complexity + Tests
1. Complexity components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Tests: `tests/test_graph_relation_edge_attribute_label_tasks.py`, `tests/test_graph_node_link_visual_variants.py`, `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
