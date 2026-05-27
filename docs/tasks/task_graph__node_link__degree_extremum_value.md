# `task_graph__node_link__degree_extremum_value`

## 1) Identity
1. Domain: `graph`
2. Task group: `comparison`
3. Scene id: `node_link`
4. Task id: `task_graph__node_link__degree_extremum_value`
5. Objective: ask for the highest or lowest degree-style value present in one labeled node-link graph.

## 2) Scene + task contract
1. Branch metadata: `query_id`
2. `query_id`: one of `undirected_max_degree_value`, `undirected_min_degree_value`, `directed_max_in_degree_value`, `directed_min_in_degree_value`, `directed_max_out_degree_value`, `directed_min_out_degree_value`, `directed_max_total_degree_value`, or `directed_min_total_degree_value`
3. Supported `graph_directionality` values: `undirected`, `directed`
4. Supported directed `degree_mode` values: `in_degree`, `out_degree`, `total_degree`
5. Supported `scene_variant` values: `circular`, `shell`, `spring`, `grid_jitter`, `layered`, `component_clustered`, `path_spine`, `radial_tree`
6. `answer_gt.type`: `integer`
7. `evidence_gt.type`: `point_set`
8. Scene contract:
   - one single-panel labeled node-link graph,
   - simple unweighted graph only,
   - no self-loops or multi-edges,
   - directed branches also reject reciprocal directed edge pairs,
   - visible node labels use one whole-image label format (`letters`, `numbers`, or `short_names`),
   - node count is sampled from `5..10`.
9. Query contract:
   - undirected branches ask for the maximum or minimum node degree value,
   - directed branches ask for the maximum or minimum in-degree, out-degree, or total-degree value,
   - `target_degree` support is `0..4`,
   - answer is the queried extreme degree value, not the number of nodes attaining it.

## 3) Prompt contract
1. Bundle: `graph_comparison_v0`
2. `scene_key`: `single_graph_comparison`
3. `task_key`: `extreme_degree_value_query`
4. Modes: `answer_only`, `answer_and_evidence`
5. Answer-only JSON shape: `{"answer":3}`
6. Answer+evidence JSON shape: `{"evidence":[[180,220],[310,180]],"answer":3}`
7. Prompt-facing evidence uses pixel-space node centers for every node attaining the queried extreme degree value.
8. If the node label format is `short_names`, prompt references quote the node label, for example node `"Abby"`.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the `point_set` of node centers for all nodes whose queried degree equals the extreme value.
2. `answer_gt.value == execution_trace.target_degree` by construction.
3. `len(evidence_gt.value)` may be greater than one when multiple nodes tie for the same extreme value.
4. `execution_trace.graph_directionality` records `undirected` or `directed`; `execution_trace.degree_mode` records `degree`, `in_degree`, `out_degree`, or `total_degree`.
5. `execution_trace.extremum_mode` records `max` or `min`.
6. `execution_trace.queried_degrees_by_label` stores the degree map used to compute the answer.
7. `execution_trace.matching_labels` and `witness_symbolic.labels` store every label attaining the queried extreme value.
8. `scene_ir.entities` stores node labels, total degrees, directed degrees, queried degree values, center points, bboxes, and `is_extreme_degree_node`.
9. `projected_evidence` includes `point_set`.

## 5) Visual policy
1. Rendering uses the shared graph light-panel style from `configs/domains/graph/base.yaml`.
2. Directed branches render arrowheads and reject reciprocal edge pairs so the queried degree mode remains readable.
3. Node label format, edge routing, glyph style, named node color, layout transform, and layout are visual variation only.
4. The prompt never refers to node position, color, or shape as semantic evidence.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same adjacency map and rendered node assignment.
3. Generation rejects samples that cannot realize the requested `(graph_directionality, degree_mode, extremum_mode, target_degree)` exactly.
4. There is no unique-node constraint: the answer is unique because it is the single extreme integer value.

## 7) Complexity + tests
1. Complexity components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Tests: `tests/test_graph_comparison_extreme_degree_value_contracts.py`, `tests/test_graph_comparison_extreme_degree_value_tasks.py`, `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
