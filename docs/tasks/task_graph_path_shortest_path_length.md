# `task_graph_path_shortest_path_length`

## 1) Identity
1. Domain: `graph`
2. Task group: `path`
3. Task id: `task_graph_path_shortest_path_length`
4. Objective: count how many edges lie on the unique shortest path between two labeled graph nodes.

## 2) Scene + task contract
1. Supported `task_variant` values: `shortest_path_length`, `directed_shortest_path_length`
2. Supported `scene_variant` values: `circular`, `shell`, `spring`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `label_path`
5. Scene contract:
   - one single-panel labeled node-link graph per image,
   - simple unweighted graph only,
   - no self-loops,
   - no multi-edges,
   - visible node labels use one whole-image label format (`A..J` or `1..10`),
   - undirected variant samples node count from `5..10`,
   - directed variant samples node count from `5..9`,
   - generation always leaves at least one node outside the queried shortest path so the scene does not collapse to a pure path graph.
6. Query contract:
   - the undirected prompt states `The graph has a unique shortest path from node X to node Y. How many edges are in that path?`,
   - the directed prompt states `The directed graph has a unique shortest path from node X to node Y, following the direction of the arrows. How many edges are in that path?`,
   - answer is the number of edges on that unique shortest path.
7. Path policy:
   - `target_shortest_path_length` is sampled from `1..5`,
   - node count is chosen from the feasible support that can realize the requested path length while leaving at least one off-path node,
   - generation builds a backbone path of the requested length, attaches off-path nodes, optionally adds safe off-path extra edges, and then verifies that the finalized graph still has exactly one shortest path between the queried endpoints,
   - directed-path verification follows edge direction and reconstructs the witness from source to goal only.
8. Topology variation:
   - `topology_profile` values are `balanced`, `low_degree`, and `hub_heavy`,
   - topology profile affects how branches attach around the backbone path and how many safe off-path cycle edges are retained,
   - graph semantics always come from adjacency, never from layout position.
9. Layout variation:
   - `scene_variant` records the realized graph layout,
   - requested layout variants are `circular`, `shell`, and `spring`,
   - the renderer may fall back to `circular` when a sampled layout is too cramped for readable node separation.
10. Visual variation:
   - one whole-image named node color is sampled from the shared TRACE named-color palette,
   - one whole-image node glyph style is sampled from `circle|rounded_square|hexagon`,
   - one whole-image label format is sampled from `letters|numbers`,
   - one whole-image layout transform is sampled from `identity|rotate_90|rotate_180|rotate_270|mirror_left_right|mirror_up_down`,
   - these style axes are non-semantic for this task and are recorded in trace metadata.

## 3) Prompt contract
1. Bundle: `graph_path_v1`
2. `task_family_key`: `single_graph_path`
3. `task_key`: `shortest_path_length_query`
4. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Modes: `answer_only`, `answer_and_evidence`
6. Answer-only JSON shape: `{"answer":2}`
7. Answer+evidence JSON shape: `{"evidence":["B","D","H"],"answer":2}`
8. Prompt-facing evidence uses an ordered node-label sequence because shortest-path semantics depend on source-to-goal order.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the `label_path` of node labels along the unique shortest path, ordered from the queried source node to the queried goal node.
2. The evidence path includes both queried endpoints.
3. `answer_gt.value == len(evidence_gt.value) - 1` by construction.
4. `scene_ir.entities` stores one node entity per rendered node with:
   - visible label,
   - degree,
   - neighbors,
   - source/goal flags,
   - on-path flag,
   - node center,
   - node bbox.
5. `scene_ir.relations` stores graph-directionality metadata plus the ordered witness path and ordered witness edge list.
6. `projected_evidence` includes:
   - `label_path`
   - `pixel_point_path`
   - `pixel_bbox_set`
7. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `source_label`
   - `goal_label`
   - `target_shortest_path_length`
   - feasible support distributions for node count / shortest-path length
   - `topology_profile`
   - requested and realized layout variants
   - ordered shortest-path labels / edges and the finalized adjacency map

## 5) Visual policy
1. Background and post-image noise use the merged graph-domain visual defaults from `configs/domains/graph/base.yaml`.
2. V1 graphs use a single rounded light panel on a light solid background.
3. Node labels are rendered inside the nodes and stay visually stable across layout, label-format, shape, and color variants.
4. Layout and styling may vary for readability and diversity, but the prompt never refers to node position, node color, or node shape as the semantic source of truth.
5. Directed variants render arrowheads and use explicit direction-following wording so the user-facing contract stays unambiguous.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same finalized adjacency map and verified unique-shortest-path computation.
3. Unique-answer policy: generation targets one explicit shortest-path length and rejects any graph whose queried endpoints do not realize exactly one shortest path of that length.
4. Reject/resample conditions:
   - no feasible node-count support for the requested path-length target,
   - failure to realize a connected graph with the requested unique shortest path,
   - a second shortest-path witness of the same length between the queried endpoints,
   - unreadable layout that cannot keep nodes sufficiently separated.
5. No semantic auto-relaxation: failures do not weaken the graph, label, or ordered-path contract.

## 7) Complexity + tests
1. Complexity definition/components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Determinism/build tests: `tests/test_graph_path_shortest_path_length_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_graph_path_shortest_path_length_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
