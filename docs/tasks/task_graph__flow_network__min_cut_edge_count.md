# `task_graph__flow_network__min_cut_edge_count`

## 1) Identity
1. Domain: `graph`
2. Task group: `optimization`
3. Scene id: `flow_network`
4. Task id: `task_graph__flow_network__min_cut_edge_count`
5. Objective: count the directed edges in the unique minimum cut of a capacity network.

## 2) Scene + Task Contract
1. Public `query_variant`: `default`
2. `query_id`: `minimum_cut_edge_count`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `point_pair_set`
5. Scene contract:
   - one single-panel directed capacity graph,
   - node `S` is the source and node `T` is the sink,
   - every arrow has a visible integer capacity,
   - the source-sink minimum cut used for evidence is unique by construction,
   - default node count is `5..6`.
6. Query contract:
   - `minimum_cut_edge_count` asks how many directed edges are in the unique minimum cut.

## 3) Prompt Contract
1. Bundle: `graph_optimization_v0`
2. `scene_key`: `single_graph_optimization`
3. `task_key`: `max_flow_query`
4. Modes: `answer_only`, `answer_and_evidence`
5. Answer-only JSON shape: `{"answer":2}`
6. Answer+evidence JSON shape: `{"evidence":[[[180,220],[310,180]],[[310,180],[430,260]]],"answer":2}`
7. Prompt-facing evidence is an array of directed edge point-pairs for the unique minimum cut; each pair is ordered from edge source center to edge target center.

## 4) Evidence + Trace Contract
1. Prompt-facing evidence is a `point_pair_set` over directed minimum-cut edges.
2. `answer_gt.value` equals `execution_trace.answer`.
3. `execution_trace.capacity_by_edge` records every visible capacity.
4. `execution_trace.original_max_flow_value` and `original_min_cut_edges` record the network solution.
5. `scene_ir.entities` stores node geometry, edge geometry, capacity-label bboxes, source/sink roles, and cut-edge flags.
6. `projected_evidence` includes the public `point_pair_set`.

## 5) Visual Policy
1. Rendering uses the shared graph light-panel style from `configs/domains/graph/base.yaml`.
2. Source `S` and sink `T` are visually highlighted.
3. Flow-network calibration uses a layered left-to-right layout with straight arrows so the source/sink direction remains readable.

## 6) Determinism + Constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same finalized capacity graph and cut enumeration.
3. No semantic auto-relaxation: failures do not weaken unique-cut, capacity, or edge constraints.

## 7) Complexity + Tests
1. Complexity components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Tests: `tests/test_graph_optimization_max_flow_value_tasks.py`
