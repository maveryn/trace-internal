# `task_graph__flow_network__max_flow_value`

## 1) Identity
1. Domain: `graph`
2. Task group: `optimization`
3. Scene id: `flow_network`
4. Task id: `task_graph__flow_network__max_flow_value`
5. Objective: compute the maximum flow value on a directed capacity network.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. `query_id`: `max_flow_value`
3. `answer_gt.type`: `integer`
4. `annotation_gt.type`: `point_pair_set`
5. Scene contract:
   - one single-panel directed capacity graph,
   - node `S` is the source and node `T` is the sink,
   - every arrow has a visible integer capacity,
   - the source-sink minimum cut used for annotation is unique by construction,
   - default node count is `5..6`,
   - max-flow value questions use answer support `2..6` and cut-edge support `1..2`.
6. Query contract:
   - `max_flow_value` asks for the maximum flow from `S` to `T`.

## 3) Prompt Contract
1. Bundle: `graph_optimization_v0`
2. `scene_key`: `single_graph_optimization`
3. `task_key`: `max_flow_query`
4. Modes: `answer_only`, `answer_and_annotation`
5. Answer-only JSON shape: `{"answer":7}`
6. Answer+annotation JSON shape: `{"annotation":[[[180,220],[310,180]],[[310,180],[430,260]]],"answer":7}`
7. Prompt-facing annotation is an array of directed edge point-pairs for the unique minimum cut; each pair contains the two endpoint node centers of one directed edge.

## 4) Annotation + Trace Contract
1. Prompt-facing annotation is a `point_pair_set` over directed minimum-cut edges.
2. `answer_gt.value` equals `execution_trace.answer`.
3. `execution_trace.capacity_by_edge` records every visible capacity.
4. `execution_trace.original_max_flow_value` and `original_min_cut_edges` record the unedited network solution.
5. `scene_ir.entities` stores node geometry, edge geometry, capacity-label bboxes, source/sink roles, and cut-edge flags.
6. `projected_annotation` includes the public `point_pair_set`.

## 5) Visual Policy
1. Rendering uses the shared graph light-panel style and role-appropriate shared font pool from `configs/domains/graph/base.yaml`.
2. Source `S` and sink `T` are visually highlighted.
3. Title, node labels, and capacity labels use readable text styles with recorded contrast metadata.
4. Flow-network calibration uses a layered left-to-right layout with straight arrows so the source/sink direction remains readable; non-source/sink node color remains visual variation only.
5. Optional graph context text can appear as non-answer visual context.
6. Post-render graph noise follows the graph-domain coordinate-preserving noise policy.

## 6) Determinism + Constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and annotation come from the same finalized capacity graph and cut enumeration.
3. No semantic auto-relaxation: failures do not weaken max-flow value, unique-cut, capacity, or edge-removal constraints.

## 7) Complexity + Tests
1. Complexity components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Tests: `tests/test_graph_optimization_max_flow_value_tasks.py`
