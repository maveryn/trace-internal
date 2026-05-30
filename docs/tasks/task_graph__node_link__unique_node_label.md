# `task_graph__node_link__unique_node_label`

## 1) Identity
1. Domain: `graph`
2. Task group: `relation`
3. Scene id: `node_link`
4. Task id: `task_graph__node_link__unique_node_label`
5. Objective: identify the visible node label that is the unique neighbor, successor, or predecessor of one queried node.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. `query_id`: `unique_neighbor_label`, `unique_successor_label`, or `unique_predecessor_label`
3. Supported `graph_directionality`: `undirected|directed`
4. `answer_gt.type`: `string`
5. `evidence_gt.type`: `point_set`
6. Scene contract:
   - one single-panel labeled node-link graph,
   - no self-loops or multi-edges,
   - directed branches reject reciprocal edge pairs,
   - visible node labels use one whole-image label format (`letters`, `numbers`, or `named`),
   - node count is sampled from `6..9` for `unique_neighbor_label` and `4..8` for the directed successor/predecessor branches.
7. Query contract:
   - undirected branch asks for the only neighbor of the queried node,
   - successor branch asks for the only outgoing-arrow target of the queried node,
   - predecessor branch asks for the only incoming-arrow source of the queried node,
   - the requested local relation has exactly one valid answer by construction.

## 3) Prompt Contract
1. Bundle: `graph_relation_v0`
2. `scene_key`: `single_graph_relation`
3. `task_key`: `unique_node_label_query`
4. Modes: `answer_only`, `answer_and_evidence`
5. Answer-only JSON shape: `{"answer":"B"}`
6. Answer+evidence JSON shape: `{"evidence":[[303,187]],"answer":"B"}`
7. Prompt-facing evidence is one pixel-space point at the center of the answer node.
8. When `label_variant=named`, prompt references to queried node labels are quoted.

## 4) Evidence + Trace Contract
1. Prompt-facing evidence is a one-item `point_set` at the answer-node center.
2. `answer_gt.value` equals `execution_trace.answer_label`.
3. `execution_trace.query_label` records the queried node.
4. `execution_trace.supporting_edge` records the relation edge connecting the query node and answer node.
5. `scene_ir.entities` stores node geometry, edge geometry, `is_query_node`, `is_answer_node`, and `is_supporting_edge`.
6. `projected_evidence` includes `point_set`, `pixel_point_set`, and trace/debug `pixel_bbox_set`.

## 5) Visual Policy
1. Rendering uses the shared graph light-panel style from `configs/domains/graph/base.yaml`.
2. Node label format, edge routing, glyph style, named node color, layout transform, and layout are visual variation only.
3. The queried node is visually haloed and the single supporting relation edge is slightly emphasized; the answer is still the opposite node label, and evidence remains the answer-node center point.
4. Post-render graph noise follows the graph-domain coordinate-preserving noise policy.

## 6) Determinism + Constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same finalized topology and rendered node center.
3. No semantic auto-relaxation: failures do not weaken graph directionality, uniqueness, or label constraints.

## 7) Complexity + Tests
1. Complexity components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Tests: `tests/test_graph_relation_unique_node_label_tasks.py`
