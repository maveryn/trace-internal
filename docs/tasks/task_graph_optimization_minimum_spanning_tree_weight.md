# `task_graph_optimization_minimum_spanning_tree_weight`

## 1) Identity
1. Domain: `graph`
2. Task group: `optimization`
3. Task id: `task_graph_optimization_minimum_spanning_tree_weight`
4. Objective: return the total weight of the graph's unique minimum spanning tree.

## 2) Scene + task contract
1. Supported `task_variant` values: `minimum_spanning_tree_weight`
2. Supported `scene_variant` values: `circular`, `shell`, `spring`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `edge_set`
5. Scene contract:
   - one single-panel labeled connected weighted graph per image,
   - undirected graph only,
   - no self-loops,
   - no multi-edges,
   - visible node labels use one whole-image label format (`A..J` or `1..10`),
   - node count is sampled from `5..8`,
   - generation always includes at least one non-tree edge so the scene never collapses to a bare tree.
6. Query contract:
   - the prompt states `The weighted graph has a unique minimum spanning tree. What is its total weight?`,
   - answer is the sum of the weights on the unique minimum spanning tree,
   - evidence is the unordered set of MST edges, represented as unordered endpoint-label pairs.
7. Weight policy:
   - edge weights are distinct integers from `1..9`,
   - generation samples `1..2` non-tree edges,
   - the heaviest sampled weights are assigned to non-tree edges so the intended spanning tree is the unique MST by construction,
   - the finalized weighted graph is rechecked with `networkx.minimum_spanning_tree(...)` before exposing answer or evidence.
8. Topology variation:
   - `topology_profile` values are `balanced`, `low_degree`, and `hub_heavy`,
   - topology profile affects both the spanning-tree shape and which non-tree edges are added,
   - graph semantics always come from adjacency + weights, never from layout position.
9. Layout variation:
   - `scene_variant` records the realized graph layout,
   - requested layout variants are `circular`, `shell`, and `spring`,
   - the renderer may fall back to `circular` when a sampled layout is too cramped for readable node separation.
10. Visual variation:
   - one whole-image named node color is sampled from the shared TRACE named-color palette,
   - one whole-image node glyph style is sampled from `circle|rounded_square|hexagon`,
   - one whole-image label format is sampled from `letters|numbers`,
   - one whole-image layout transform is sampled from `identity|rotate_90|rotate_180|rotate_270|mirror_left_right|mirror_up_down`,
   - edge weights are rendered as small boxed integers near each edge,
   - these style axes are non-semantic for this task and are recorded in trace metadata.

## 3) Prompt contract
1. Bundle: `graph_optimization_v1`
2. `task_family_key`: `single_graph_optimization`
3. `task_key`: `minimum_spanning_tree_weight_query`
4. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Modes: `answer_only`, `answer_and_evidence`
6. Answer-only JSON shape: `{"answer":12}`
7. Answer+evidence JSON shape: `{"evidence":[["B","D"],["D","G"],["C","G"]],"answer":12}`
8. Prompt-facing evidence uses `edge_set`; each edge is one unordered endpoint-label pair.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the `edge_set` of all MST edges.
2. Each evidence item is a two-label endpoint pair and is unordered semantically.
3. `scene_ir.entities` stores one node entity per rendered node plus one edge entity per rendered edge with:
   - endpoint labels,
   - rendered segment,
   - integer edge weight,
   - weight-label bbox,
   - MST-membership flag.
4. `scene_ir.relations` stores:
   - graph directionality,
   - full edge-weight list,
   - MST edge list,
   - adjacency map,
   - degree map.
5. `projected_evidence` includes:
   - `edge_set`
   - `pixel_edge_set`
6. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `node_count`
   - `extra_edge_count`
   - edge-weight range
   - total MST weight
   - MST edges
   - weighted edge list
   - topology profile
   - requested and realized layout variants

## 5) Visual policy
1. Background and post-image noise use the merged graph-domain visual defaults from `configs/domains/graph/base.yaml`.
2. V1 weighted graphs use a single rounded light panel on a light solid background.
3. Node labels are rendered inside the nodes; edge weights are rendered in small boxed labels near edge midpoints.
4. Layout and styling may vary for readability and diversity, but the prompt never refers to node position, node color, or node shape as the semantic source of truth.
5. Weight labels stay semantic for this task, so trace metadata and rendered labels come from the same canonical edge-weight map.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same finalized weighted graph.
3. Unique-answer policy: generation enforces a unique MST by construction and rejects any graph whose final weighted edges do not preserve that unique witness.
4. Reject/resample conditions:
   - infeasible node-count / extra-edge-count / weight-range combination,
   - failure to realize a connected weighted graph with at least one non-tree edge,
   - failure to preserve the intended unique MST after weight assignment,
   - unreadable layout that cannot keep nodes sufficiently separated.
5. No semantic auto-relaxation: failures do not weaken the connectivity, weight, or unique-MST contract.

## 7) Complexity + tests
1. Complexity definition/components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Determinism/build tests: `tests/test_graph_optimization_minimum_spanning_tree_weight_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_graph_optimization_minimum_spanning_tree_weight_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
