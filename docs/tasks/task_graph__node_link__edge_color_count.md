# `task_graph__node_link__edge_color_count`

## 1) Identity
1. Domain: `graph`
2. Task group: `counting`
3. Scene id: `node_link`
4. Task id: `task_graph__node_link__edge_color_count`
5. Objective: count how many graph edges use one queried semantic edge color.

## 2) Scene + task contract
1. Public `query_variant`: `default`
2. `query_id`: `edge_color_count`
3. Supported `graph_directionality` values: `undirected|directed`
4. Supported target colors: shared TRACE named-color palette (`red`, `blue`, `green`, `yellow`, `orange`, `purple`, `brown`, `cyan`, `magenta`, `maroon`)
5. `answer_gt.type`: `integer`
6. `evidence_gt.type`: `point_pair_set`
7. Scene contract:
   - one single-panel labeled node-link graph,
   - simple unweighted graph only,
   - no self-loops or multi-edges,
   - directed variants reject reciprocal edge pairs,
   - visible node labels use one whole-image label format (`letters`, `numbers`, or `short_names`),
   - node count is sampled from `5..10`.
8. Query contract:
   - prompt asks for the count of edges drawn with one shared named color plus its hex code,
   - answer support is `0..8`, including zero-answer cases,
   - answer is the count of matching edges.

## 3) Prompt contract
1. Bundle: `graph_counting_v0`
2. `scene_key`: `single_graph_counting`
3. `task_key`: `edge_color_count_query`
4. Modes: `answer_only`, `answer_and_evidence`
5. Answer-only JSON shape: `{"answer":2}`
6. Answer+evidence JSON shape: `{"evidence":[[[180,220],[310,180]],[[180,220],[430,260]]],"answer":2}`
7. Prompt-facing color text uses `<color_name> [#RRGGBB]`, for example `green [#37B94B]`.
8. Prompt-facing evidence uses pixel-space endpoint-center pairs for every matching edge; directed edge pairs are ordered source-to-target.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the unordered `point_pair_set` of endpoint-center pairs for all edges whose semantic stroke color matches the queried color.
2. `answer_gt.value == len(evidence_gt.value)` by construction, including zero-answer cases where evidence is an empty array.
3. `execution_trace.target_color_name` records the queried color name.
4. `execution_trace.edge_color_names_by_label_pair` records every rendered edge's semantic color.
5. `execution_trace.matching_edges` records the symbolic witness edge-label pairs in deterministic order.
6. `scene_ir.entities` stores node labels, degrees, in-degrees, out-degrees, neighbors/successors/predecessors, edge labels, edge colors, edge segments, and `is_target_color_edge`.
7. `projected_evidence` includes `point_pair_set` and pixel endpoint pairs.

## 5) Visual policy
1. Rendering uses the shared graph light-panel style from `configs/domains/graph/base.yaml`.
2. This task promotes per-edge stroke color from visual style into explicit task semantics.
3. The non-semantic node theme color still controls node and panel styling; `render_spec.style.semantic_edge_color_names_by_label_pair` records the actual edge colors used for the query.
4. Node label format, edge routing, glyph style, layout transform, and layout remain visual variation only.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same rendered edge-color assignment.
3. Generation assigns exactly the requested number of edges to the queried color, and all other edges receive non-target colors.
4. No semantic auto-relaxation: failures do not weaken the graph, directionality, color, or count contract.

## 7) Complexity + tests
1. Complexity components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Tests: `tests/test_graph_counting_edge_color_count_tasks.py`, `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
