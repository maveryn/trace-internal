# `task_graph_counting_articulation_point_count`

## 1) Identity
1. Domain: `graph`
2. Task group: `counting`
3. Task id: `task_graph_counting_articulation_point_count`
4. Objective: count how many labeled graph nodes are articulation points.

## 2) Scene + task contract
1. Supported `task_variant` values: `articulation_point_count`
2. Supported `scene_variant` values: `circular`, `shell`, `spring`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `label_set`
5. Scene contract:
   - one single-panel labeled undirected node-link graph per image,
   - simple unweighted graph only,
   - no self-loops,
   - no multi-edges,
   - node count sampled from `5..10`,
   - visible node labels use one whole-image label format (`A..J` or `1..10`).
6. Query contract:
   - the prompt asks `How many nodes are articulation points?`,
   - answer is the number of nodes whose removal increases the number of connected components of the graph.
7. Count policy:
   - `target_count` is sampled from `0..8`,
   - node count is chosen from the feasible support that can realize the requested articulation-point count,
   - the sampler verifies the final articulation-point set from the realized adjacency map before emitting answer/evidence.
8. Topology variation:
   - `topology_profile` values are `balanced`, `low_degree`, and `hub_heavy`,
   - topology profile affects how articulation-supporting substructures are assembled,
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
1. Bundle: `graph_counting_v1`
2. `task_family_key`: `single_graph_counting`
3. `task_key`: `articulation_point_count_query`
4. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Modes: `answer_only`, `answer_and_evidence`
6. Answer-only JSON shape: `{"answer":3}`
7. Answer+evidence JSON shape: `{"evidence":["B","D","G"],"answer":3}`
8. Prompt-facing evidence uses node labels rather than pixel boxes because labels are the canonical node identities for this domain.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the `label_set` of all articulation-point nodes.
2. The witness set is unordered semantically; the implementation only canonicalizes label order internally for deterministic serialization.
3. `answer_gt.value == len(evidence_gt.value)` by construction.
4. `scene_ir.entities` stores one node entity per rendered node with:
   - visible label,
   - articulation-point flag,
   - neighbors,
   - node center,
   - node bbox.
5. `scene_ir.relations` stores one undirected edge relation per graph edge.
6. `projected_evidence` includes:
   - `label_set`
   - `bbox_set`
7. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `target_count`
   - feasible support distributions for node count / target count
   - `topology_profile`
   - requested and realized layout variants
   - articulation-point labels and adjacency map

## 5) Visual policy
1. Background and post-image noise use the merged graph-domain visual defaults from `configs/domains/graph/base.yaml`.
2. V1 graphs use a single rounded light panel on a light solid background.
3. Node labels are rendered inside the nodes and stay visually stable across layout, label-format, shape, and color variants.
4. Layout and styling may vary for readability and diversity, but the prompt never refers to node position, node color, or node shape as the semantic source of truth.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same finalized adjacency map and articulation-point computation.
3. Unique-answer policy: the sampler targets one explicit articulation-point count and rejects any graph whose realized articulation-point set does not match it exactly.
4. Reject/resample conditions:
   - no feasible node-count support for the requested articulation-point count,
   - failure to realize a simple graph with the requested articulation-point support,
   - unreadable layout that cannot keep nodes sufficiently separated.
5. No semantic auto-relaxation: failures do not weaken the graph, label, or articulation-point contract.

## 7) Complexity + tests
1. Complexity definition/components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Determinism/build tests: `tests/test_graph_counting_articulation_point_count_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_graph_counting_articulation_point_count_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
