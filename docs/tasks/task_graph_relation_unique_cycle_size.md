# `task_graph_relation_unique_cycle_size`

## 1) Identity
1. Domain: `graph`
2. Task group: `relation`
3. Task id: `task_graph_relation_unique_cycle_size`
4. Objective: count how many labeled nodes lie on the unique cycle of one graph.

## 2) Scene + task contract
1. Supported `task_variant` values: `unique_cycle_size`
2. Supported `scene_variant` values: `circular`, `shell`, `spring`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `label_set`
5. Scene contract:
   - one single-panel labeled undirected node-link graph per image,
   - simple unweighted graph only,
   - no self-loops,
   - no multi-edges,
   - the graph is connected and contains exactly one cycle,
   - node count sampled from `5..10`,
   - visible node labels use one whole-image label format (`A..J` or `1..10`).
6. Query contract:
   - the prompt states `The graph contains exactly one cycle. How many nodes are in that cycle?`,
   - answer is the number of nodes on that unique cycle.
7. Cycle policy:
   - `target_cycle_size` is sampled from `3..10`,
   - node count is chosen from the feasible support that can realize the requested cycle size,
   - generation constructs a unicyclic graph by design and verifies that the finalized graph still has exactly one cycle.
8. Topology variation:
   - `topology_profile` values are `balanced`, `low_degree`, and `hub_heavy`,
   - topology profile affects how trees are attached around the cycle,
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
1. Bundle: `graph_relation_v1`
2. `task_family_key`: `single_graph_relation`
3. `task_key`: `unique_cycle_size_query`
4. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Modes: `answer_only`, `answer_and_evidence`
6. Answer-only JSON shape: `{"answer":4}`
7. Answer+evidence JSON shape: `{"evidence":["B","D","H","J"],"answer":4}`
8. Prompt-facing evidence uses node labels rather than pixel boxes because labels are the canonical node identities for this domain.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the `label_set` of all nodes in the unique cycle.
2. The witness set is unordered semantically; the implementation only canonicalizes label order internally for deterministic serialization.
3. `answer_gt.value == len(evidence_gt.value)` by construction.
4. `scene_ir.entities` stores one node entity per rendered node with:
   - visible label,
   - on-cycle flag,
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
   - `target_cycle_size`
   - feasible support distributions for node count / cycle size
   - `topology_profile`
   - requested and realized layout variants
   - cycle-node labels, cycle basis, and adjacency map

## 5) Visual policy
1. Background and post-image noise use the merged graph-domain visual defaults from `configs/domains/graph/base.yaml`.
2. V1 graphs use a single rounded light panel on a light solid background.
3. Node labels are rendered inside the nodes and stay visually stable across layout, label-format, shape, and color variants.
4. Layout and styling may vary for readability and diversity, but the prompt never refers to node position, node color, or node shape as the semantic source of truth.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same finalized adjacency map and unique-cycle computation.
3. Unique-answer policy: the sampler targets one explicit cycle size and rejects any graph that is not unicyclic or whose unique cycle has the wrong size.
4. Reject/resample conditions:
   - no feasible node-count support for the requested cycle-size target,
   - failure to realize a connected unicyclic simple graph with the requested support,
   - more than one cycle or zero cycles after construction,
   - unreadable layout that cannot keep nodes sufficiently separated.
5. No semantic auto-relaxation: failures do not weaken the graph, label, or unique-cycle contract.

## 7) Complexity + tests
1. Complexity definition/components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Determinism/build tests: `tests/test_graph_relation_unique_cycle_size_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_graph_relation_unique_cycle_size_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
