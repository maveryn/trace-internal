# `task_graph__pipe_network__junction_path_count`

## 1) Identity
1. Domain: `graph`
2. Task group: `relation`
3. Scene id: `pipe_network`
4. Task id: `task_graph__pipe_network__junction_path_count`
5. Objective: count pipe junctions satisfying an open-pipe path relation.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. `query_id`: `pipe_reachable_junction_count` or `pipe_exact_distance_count`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `point_set`
5. Scene contract:
   - one labeled pipe-junction network,
   - open pipes are traversable,
   - blocked pipes are visible distractors and are not traversable,
   - supported grid shapes are `3x4`, `3x5`, `4x4`, and `4x5`.
6. Query contract:
   - `pipe_reachable_junction_count` asks for all junctions reachable from a named junction through open pipes,
   - `pipe_exact_distance_count` asks for junctions exactly `query_distance` open-pipe segments away from a named junction.

## 3) Prompt Contract
1. Bundle: `graph_relation_v0`
2. `scene_key`: `single_graph_relation`
3. `task_key`: `junction_path_count_query`
4. Modes: `answer_only`, `answer_and_evidence`
5. Answer-only JSON shape: `{"answer":3}`
6. Answer+evidence JSON shape: `{"evidence":[[180,220],[310,220],[430,300]],"answer":3}`
7. Prompt-facing evidence is an array of `[x,y]` pixel points at the centers of all counted junctions.

## 4) Evidence + Trace Contract
1. Prompt-facing evidence is a `point_set` over counted junction centers.
2. `answer_gt.value` equals the number of labels in `execution_trace.matching_labels`.
3. `execution_trace.open_adjacency_by_label` records the traversable graph used for verification.
4. `execution_trace.blocked_edge_labels` records visible non-traversable distractor pipes.
5. `projected_evidence` includes the public `point_set`.

## 5) Visual Policy
1. Rendering uses the shared graph light-panel style from `configs/domains/graph/base.yaml`.
2. Open and blocked pipes have distinct visual treatments.
3. Junction labels use one whole-image label format.

## 6) Determinism + Constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same open-pipe adjacency trace.
3. Blocked pipes are never included in path calculations.

## 7) Complexity + Tests
1. Complexity components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Tests: `tests/test_graph_pipe_junction_tasks.py`
