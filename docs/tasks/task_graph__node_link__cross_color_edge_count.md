# `task_graph__node_link__cross_color_edge_count`

## 1) Identity
1. Domain: `graph`
2. Scene: `counting`
3. Scene id: `node_link`
4. Task id: `task_graph__node_link__cross_color_edge_count`
5. Objective: count graph edges whose endpoint nodes have two queried semantic colors.

## 2) Scene + task contract
1. Branch metadata: `query_id`
2. `query_id`: `cross_color_edge_count` for undirected graphs, `directed_cross_color_edge_count` for directed graphs
3. Supported `graph_directionality` values: `undirected|directed`
4. Supported node colors: shared TRACE named-color palette
5. `answer_gt.type`: `integer`
6. `annotation_gt.type`: `point_pair_set`
7. Undirected query: count edges with one endpoint in the first queried color and the other endpoint in the second queried color.
8. Directed query: count arrows whose source node has the first queried color and target node has the second queried color.

## 3) Prompt contract
1. Bundle: `graph_counting_v0`
2. `scene_key`: `single_graph_counting`
3. `task_key`: `cross_color_edge_count_query`
4. Modes: `answer_only`, `answer_and_annotation`
5. Answer-only JSON shape: `{"answer":2}`
6. Answer+annotation JSON shape: `{"annotation":[[[180,220],[310,180]],[[180,220],[430,260]]],"answer":2}`
7. Prompt-facing color text uses `<color_name> [#RRGGBB]`.

## 4) Annotation + trace contract
1. Prompt-facing annotation is a `point_pair_set` of endpoint-node-center pairs for every counted edge; each endpoint is a `[x,y]` pixel point.
2. For directed graphs, each annotation pair is ordered source-to-target.
3. `answer_gt.value == len(annotation_gt.value)` by construction, including zero-answer cases.
4. `execution_trace.node_color_names_by_label` records every node's semantic color.
5. `execution_trace.matching_edges` records the symbolic counted edge labels.

## 5) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. The sampler assigns node colors so the realized graph has exactly the requested cross-color edge count.
3. Failures reject/resample; generation does not relax color, directionality, or target-count constraints.

## 6) Complexity + tests
1. Complexity components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Tests: `tests/test_graph_counting_cross_color_edge_count_tasks.py`
