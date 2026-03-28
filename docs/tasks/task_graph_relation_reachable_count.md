# `task_graph_relation_reachable_count`

## 1) Identity
1. Domain: `graph`
2. Task group: `relation`
3. Task id: `task_graph_relation_reachable_count`
4. Objective: count how many labeled nodes are reachable from one queried source node in a directed graph.

## 2) Scene + task contract
1. Supported `task_variant` values: `reachable_count`
2. Supported `scene_variant` values: `circular`, `shell`, `spring`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `label_set`
5. Scene contract:
   - one single-panel labeled directed node-link graph per image,
   - simple unweighted graph only,
   - no self-loops,
   - no reciprocal edge pairs,
   - node count sampled from `5..9`,
   - visible node labels use one whole-image label format (`A..I` or `1..9`).
6. Query contract:
   - the prompt states `How many nodes, including node X itself, are reachable from X by following the direction of the arrows?`,
   - answer is the number of nodes reachable from the queried source node when traversal follows arrow direction,
   - the queried source node itself is included in both the answer and the evidence set.
7. Reachability policy:
   - `target_reachable_count` is sampled from `1..7`,
   - node count is chosen from the feasible support that can realize the requested reachable count while leaving at least one unreachable node,
   - generation constructs a directed reachable subgraph rooted at the query node, separately constructs unreachable structure, and verifies the finalized successor adjacency before exposing the witness set.
8. Topology variation:
   - `topology_profile` values are `balanced`, `low_degree`, and `hub_heavy`,
   - topology profile affects branching inside the reachable region and how extra safe directed edges are retained,
   - graph semantics always come from directed adjacency, never from layout position.
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
3. `task_key`: `reachable_count_query`
4. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Modes: `answer_only`, `answer_and_evidence`
6. Answer-only JSON shape: `{"answer":3}`
7. Answer+evidence JSON shape: `{"evidence":["B","D","H"],"answer":3}`
8. Prompt-facing evidence uses node labels rather than pixel boxes because labels are the canonical node identities for this domain.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the `label_set` of all nodes reachable from the queried source node, including the queried node itself.
2. The witness set is unordered semantically; the implementation only canonicalizes label order internally for deterministic serialization.
3. `answer_gt.value == len(evidence_gt.value)` by construction.
4. `scene_ir.entities` stores one node entity per rendered node with:
   - visible label,
   - query-node flag,
   - reachable flag,
   - successors,
   - predecessors,
   - node center,
   - node bbox.
5. `scene_ir.relations` stores directed edge relations plus directed successor/predecessor adjacency maps.
6. `projected_evidence` includes:
   - `label_set`
   - `pixel_point_set`
   - `pixel_bbox_set`
7. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `target_reachable_count`
   - feasible support distributions for node count / reachable count
   - `query_label`
   - `matching_labels`
   - `unreachable_labels`
   - directed successor/predecessor adjacency maps
   - `topology_profile`
   - requested and realized layout variants

## 5) Visual policy
1. Background and post-image noise use the merged graph-domain visual defaults from `configs/domains/graph/base.yaml`.
2. V1 graphs use a single rounded light panel on a light solid background.
3. Node labels are rendered inside the nodes and stay visually stable across layout, label-format, shape, and color variants.
4. Directed edges always render arrowheads.
5. Layout and styling may vary for readability and diversity, but the prompt never refers to node position, node color, or node shape as the semantic source of truth.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same finalized directed successor adjacency map.
3. Unique-answer policy: the sampler targets one explicit reachable-count value and rejects any graph whose queried source reaches the wrong node set.
4. Reject/resample conditions:
   - no feasible node-count support for the requested reachable-count target,
   - failure to preserve at least one unreachable node,
   - any extra directed edge that changes the reachable witness set,
   - unreadable layout that cannot keep nodes sufficiently separated.
5. No semantic auto-relaxation: failures do not weaken the graph, label, or directed-reachability contract.

## 7) Complexity + tests
1. Complexity definition/components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Determinism/build tests: `tests/test_graph_relation_reachable_count_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_graph_relation_reachable_count_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
