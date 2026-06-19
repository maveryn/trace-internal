# `task_graph__node_link__edge_text_count`

## Program Contract
- `count(filter(edge_labels(graph), text=target_edge_label)); scene=node_link; scope=edge_text_count`

## 1) Identity
1. Domain: `graph`
2. Scene: `node_link`
3. Scene id: `node_link`
4. Task id: `task_graph__node_link__edge_text_count`
5. Objective: count how many visible edge-label text boxes show one queried label.

## 2) Scene + task contract
1. Branch metadata: `query_id`
2. `query_id`: `single`
3. Supported `graph_directionality` values: `undirected`
4. `answer_gt.type`: `integer`
5. `annotation_gt.type`: `bbox_set`
6. Scene contract:
   - one single-panel labeled node-link graph,
   - every edge or arrow has a visible boxed text label,
   - no self-loops or multi-edges,
   - visible node labels use one whole-image label format (`letters`, `numbers`, or `named`),
   - node count is sampled from `5..8`,
   - visible labeled edge count is capped at `12`.
7. Query contract:
   - prompt asks for the count of edge-label boxes whose text exactly matches the queried label,
   - default answer support is `1..5`,
   - answer is the count of matching visible edge-label boxes.
3. Default visible edge labels are sampled from the shared label manifest with per-instance support size `16`.
4. Edge labels are lowercase text of `3..5` characters and are filtered so they do not duplicate any visible node label.

## 3) Prompt contract
1. Bundle: `graph_counting_v0`
2. `scene_key`: `single_graph_counting`
3. `task_key`: `edge_text_label_count_query`
4. Modes: `answer_only`, `answer_and_annotation`
5. Answer-only JSON shape: `{"answer":2}`
6. Answer+annotation JSON shape: `{"annotation":[[248,190,300,214],[420,238,472,262]],"answer":2}`
7. Prompt-facing annotation uses pixel-space boxes around every matching visible edge-label text box.

## 4) Annotation + trace contract
1. Prompt-facing annotation is the `bbox_set` of all visible edge-label text boxes whose text equals the queried label.
2. `answer_gt.value == len(annotation_gt.value)` by construction.
3. `execution_trace.target_edge_label` records the queried visible label.
4. `execution_trace.edge_attribute_labels_by_label_pair` records every rendered edge label.
5. `execution_trace.matching_edges` records the symbolic witness edge-label pairs in deterministic order.
6. `scene_ir.entities` stores node geometry, edge geometry, edge-label bboxes, and edge-label values.
7. `projected_annotation` includes `bbox_set` and edge-label bbox projections.

## 5) Visual policy
1. Rendering uses the shared graph light-panel style from `configs/domains/graph/base.yaml`.
2. Edge-label boxes are placed by the shared node-link renderer and must avoid nodes and other edge-label boxes.
3. Node label format, edge routing, glyph style, named node color, layout transform, and layout remain visual variation only.
4. Edge-label task rendering uses a `960x720` canvas and keeps node labels at `20px` while drawing edge-label text at `19px`.
5. Post-render graph noise follows the graph-domain coordinate-preserving noise policy.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and annotation come from the same finalized edge-label assignment and rendered bboxes.
3. Generation assigns exactly the requested number of edges to the queried label, and all other edges receive non-target labels.
4. No semantic auto-relaxation: failures do not weaken the graph, directionality, label support, or count contract.

## 7) Complexity + tests
1. Complexity components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Tests: `tests/test_graph_counting_edge_text_label_count_tasks.py`, `tests/test_prompt_system.py`, `tests/test_scene_config.py`
