# `task_graph__node_link__degree_predicate_count`

## 1) Identity
1. Domain: `graph`
2. Task group: `counting`
3. Scene id: `node_link`
4. Task id: `task_graph__node_link__degree_predicate_count`
5. Objective: count how many labeled nodes satisfy a degree-style predicate.

## 2) Scene + task contract
1. Branch metadata: `query_id`
2. `query_id`: `undirected_degree_count`, `directed_in_degree_count`, `directed_out_degree_count`, `undirected_degree_one_filter_remaining_count`, `directed_in_degree_one_filter_remaining_count`, `directed_out_degree_one_filter_remaining_count`, `directed_source_count`, or `directed_sink_count`
3. Supported `graph_directionality` values: `undirected`, `directed`
4. Supported `scene_variant` values: `circular`, `shell`, `spring`, `grid_jitter`, `layered`, `component_clustered`, `path_spine`, `radial_tree`
5. `answer_gt.type`: `integer`
6. `evidence_gt.type`: `point_set`
7. Scene contract:
   - one single-panel labeled node-link graph,
   - simple unweighted graph only,
   - no self-loops or multi-edges,
   - directed branches also reject reciprocal directed edge pairs,
   - visible node labels use one whole-image label format (`letters`, `numbers`, or `named`),
   - node count is sampled from `5..10`.
8. Query contract:
   - degree-count branches ask how many nodes have degree, in-degree, or out-degree `k`,
   - degree-filter branches ask how many nodes would remain after removing nodes with exactly one queried connection,
   - source/sink branches ask how many directed nodes have no incoming arrows or no outgoing arrows,
   - answer is the number of nodes satisfying the concrete branch predicate.

## 3) Prompt contract
1. Bundle: `graph_counting_v0`
2. `scene_key`: `single_graph_counting`
3. `task_key`: branch-specific graph-counting prompt key from `graph_counting_v0`
4. Modes: `answer_only`, `answer_and_evidence`
5. Answer-only JSON shape: `{"answer":2}`
6. Answer+evidence JSON shape: `{"evidence":[[180,220],[310,180]],"answer":2}`
7. Prompt-facing evidence uses pixel-space node-center points; node labels remain in `witness_symbolic`.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the unordered `point_set` of pixel centers for all nodes whose queried degree equals the requested value.
2. `answer_gt.value == len(evidence_gt.value)` by construction.
3. `execution_trace.query_id == "default"` and `execution_trace.query_id` records the concrete branch.
4. Absorbed branch generators can record `internal_task_id` or `internal_query_id` for diagnostic compatibility; public output task id remains `task_graph__node_link__degree_predicate_count`.
5. `execution_trace.graph_directionality` records `undirected` or `directed`; `execution_trace.degree_mode` records `degree`, `in_degree`, or `out_degree`.
6. `scene_ir.entities` stores node labels, degrees, directed degrees, neighbors/successors/predecessors, center points, and node bboxes.
7. `projected_evidence` includes `point_set`, `pixel_point_set`, and `pixel_bbox_set`.

## 5) Visual policy
1. Rendering uses the shared graph light-panel style from `configs/domains/graph/base.yaml`.
2. Directed branches render arrowheads and reject reciprocal edge pairs so the queried degree mode remains readable.
3. Node label format, edge routing, glyph style, named node color, layout transform, and layout are visual variation only.
4. The prompt never refers to node position, color, or shape as semantic evidence.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same adjacency map and rendered node assignment.
3. Generation rejects samples that cannot realize the requested branch predicate and answer count exactly.

## 7) Complexity + tests
1. Complexity components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Tests: `tests/test_graph_counting_degree_count_contracts.py`, branch contract tests for absorbed degree-filter/source-sink generators, and `tests/test_task_group_config.py`
