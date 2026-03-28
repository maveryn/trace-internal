# `task_graph_counting_degree_count`

## 1) Identity
1. Domain: `graph`
2. Task group: `counting`
3. Task id: `task_graph_counting_degree_count`
4. Objective: count how many labeled graph nodes have a queried degree measure.

## 2) Scene + task contract
1. Supported `task_variant` values: `degree_count`, `in_degree_count`, `out_degree_count`
2. Supported `scene_variant` values: `circular`, `shell`, `spring`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `label_set`
5. Scene contract:
   - one single-panel labeled node-link graph per image,
   - simple unweighted graph only,
   - no self-loops,
   - no multi-edges,
   - directed variants also reject reciprocal edge pairs so arrowheads stay readable,
   - visible node labels use one whole-image label format (`A..J` or `1..10`),
   - undirected variant node count sampled from `5..10`,
   - directed variants node count sampled from `5..9`.
6. Query contract:
   - `degree_count`: ask for one queried degree `k` in an undirected graph,
   - `in_degree_count`: ask for one queried in-degree `k` in a directed graph,
   - `out_degree_count`: ask for one queried out-degree `k` in a directed graph,
   - default `query_degree` support is `0..4`,
   - answer is the number of nodes whose queried degree measure equals `k`.
7. Count policy:
   - `target_count` is sampled from `0..5`,
   - node count is chosen from the feasible support that can realize the requested `(query_degree, target_count)` pair,
   - the graph sampler constructs a simple graph with exactly that many matching nodes,
   - directed variants use a lower default max degree cap so arrowed scenes stay readable.
8. Topology variation:
   - `topology_profile` values are `balanced`, `low_degree`, and `hub_heavy`,
   - topology profile affects the degree-sequence search distribution only,
   - graph semantics always come from adjacency, never from layout position.
9. Layout variation:
   - `scene_variant` records the realized graph layout,
   - requested layout variants are `circular`, `shell`, and `spring`,
   - the renderer may fall back to `circular` when a sampled layout is too cramped for readable node separation.
10. Visual variation:
   - one whole-image named node color is sampled from the shared TRACE named-color palette,
   - one whole-image node glyph style is sampled from `circle|rounded_square|hexagon`,
   - one whole-image layout transform is sampled from `identity|rotate_90|rotate_180|rotate_270|mirror_left_right|mirror_up_down`,
   - these style axes are non-semantic for this task and are recorded in trace metadata.

## 3) Prompt contract
1. Bundle: `graph_counting_v1`
2. `task_family_key`: `single_graph_counting`
3. `task_key`: `degree_count_query`
4. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Modes: `answer_only`, `answer_and_evidence`
6. Answer-only JSON shape: `{"answer":2}`
7. Answer+evidence JSON shape: `{"evidence":["B","F"],"answer":2}`
8. Prompt-facing evidence uses node labels rather than pixel boxes because labels are the canonical node identities for this domain.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the ascending-label-order `label_set` of all nodes whose degree equals the queried degree.
2. `answer_gt.value == len(evidence_gt.value)` by construction.
3. `scene_ir.entities` stores one node entity per rendered node with:
   - visible label,
   - degree,
   - neighbors,
   - node center,
   - node bbox.
4. `scene_ir.relations` stores one edge relation per graph edge and records both graph directionality and the active degree mode.
5. `projected_evidence` includes:
   - `label_set`
   - `bbox_set`
6. `execution_trace` records:
   - `task_variant`
   - `graph_directionality`
   - `degree_mode`
   - `scene_variant`
   - `query_degree`
   - `target_count`
   - feasible support distributions for node count / query degree / target count
   - `topology_profile`
   - requested and realized layout variants
   - degree table and adjacency map

## 5) Visual policy
1. Background and post-image noise use the merged graph-domain visual defaults from `configs/domains/graph/base.yaml`.
2. V1 graphs use a single rounded light panel on a light solid background.
3. Node labels are rendered inside the nodes and stay visually stable across layout, label-format, shape, and color variants.
4. Directed variants render arrowheads and fit labels to the available glyph interior so numeric labels remain readable inside compact nodes.
5. Layout and styling are allowed to vary for readability and diversity, but the prompt never refers to node position, node color, or node shape as the semantic source of truth.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same adjacency map and rendered node-label assignment.
3. Unique-answer policy: the graph sampler targets one explicit `(query_degree, target_count)` pair and rejects any sample that does not realize it exactly.
4. Reject/resample conditions:
   - no feasible node count for the requested degree-count pair,
   - failure to realize a simple graph with the requested support,
   - unreadable layout that cannot keep nodes sufficiently separated.
5. No semantic auto-relaxation: failures do not weaken the graph, label, or degree-count contract.

## 7) Complexity + tests
1. Complexity definition/components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Determinism/build tests: `tests/test_graph_counting_degree_count_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_graph_counting_degree_count_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
