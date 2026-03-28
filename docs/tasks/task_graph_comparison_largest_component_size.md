# `task_graph_comparison_largest_component_size`

## 1) Identity
1. Domain: `graph`
2. Task group: `comparison`
3. Task id: `task_graph_comparison_largest_component_size`
4. Objective: count how many nodes are in the unique largest connected component of one labeled graph.

## 2) Scene + task contract
1. Supported `task_variant` values: `largest_component_size`
2. Supported `scene_variant` values: `circular`, `shell`, `spring`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `label_set`
5. Scene contract:
   - one single-panel labeled undirected node-link graph per image,
   - simple unweighted graph only,
   - no self-loops,
   - no multi-edges,
   - node count sampled from `5..10`,
   - connected-component count sampled from `2..4`,
   - unique-largest-component size sampled from `2..6`.
6. Comparison contract:
   - the prompt asks `How many nodes are in the largest connected component?`,
   - generation enforces that the largest connected component is unique by size,
   - answer is the size of that unique largest component.
7. Topology variation:
   - `topology_profile` values are `balanced`, `low_degree`, and `hub_heavy`,
   - topology profile affects disconnected-component construction only,
   - graph semantics always come from adjacency, never from layout position.
8. Layout variation:
   - `scene_variant` records the realized graph layout,
   - requested layout variants are `circular`, `shell`, and `spring`,
   - the renderer may fall back to `circular` when a sampled layout is too cramped for readable node separation.
9. Visual variation:
   - one whole-image named node color is sampled from the shared TRACE named-color palette,
   - one whole-image node glyph style is sampled from `circle|rounded_square|hexagon`,
   - one whole-image label format is sampled from `letters|numbers`,
   - one whole-image layout transform is sampled from `identity|rotate_90|rotate_180|rotate_270|mirror_left_right|mirror_up_down`,
   - these style axes are non-semantic for this task and are recorded in trace metadata.

## 3) Prompt contract
1. Bundle: `graph_comparison_v1`
2. `task_family_key`: `single_graph_comparison`
3. `task_key`: `largest_component_size_query`
4. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Modes: `answer_only`, `answer_and_evidence`
6. Answer-only JSON shape: `{"answer":4}`
7. Answer+evidence JSON shape: `{"evidence":["B","D","H","J"],"answer":4}`

## 4) Evidence + trace contract
1. Prompt-facing evidence is the ascending-label-order `label_set` of every node in the unique largest connected component.
2. `answer_gt.value == len(evidence_gt.value)` by construction.
3. `scene_ir.entities` stores one node entity per rendered node with:
   - visible label,
   - connected-component id,
   - node center,
   - node bbox.
4. `scene_ir.relations` stores one undirected edge relation per graph edge.
5. `projected_evidence` includes:
   - `label_set`
   - `bbox_set`
6. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `component_count`
   - `largest_component_size`
   - feasible support distributions for node count / component count / largest-component size
   - `topology_profile`
   - requested and realized layout variants
   - connected-component membership and adjacency map

## 5) Visual policy
1. Background and post-image noise use the merged graph-domain visual defaults from `configs/domains/graph/base.yaml`.
2. V1 graphs use a single rounded light panel on a light solid background.
3. Node labels are rendered inside the nodes and stay visually stable across layout, label-format, shape, and color variants.
4. Layout and styling may vary for readability and diversity, but the prompt never refers to node position, node color, or node shape as the semantic source of truth.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same connected-component decomposition and rendered node-label assignment.
3. Unique-answer policy: the sampler targets one explicit unique-largest-component size and rejects any graph with a tie for the largest component.
4. Reject/resample conditions:
   - no feasible node-count support for the requested `(component_count, largest_component_size)` pair,
   - failure to realize a disconnected simple graph with the requested support,
   - largest-component tie,
   - unreadable layout that cannot keep nodes sufficiently separated.
5. No semantic auto-relaxation: failures do not weaken the graph, component, or unique-largest contract.

## 7) Complexity + tests
1. Complexity definition/components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Determinism/build tests: `tests/test_graph_comparison_largest_component_size_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_graph_comparison_largest_component_size_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
