# `task_graph__node_link__reachable_node_count`

## 1) Identity
1. Domain: `graph`
2. Task group: `relation`
3. Task id: `task_graph__node_link__reachable_node_count`
4. Objective: count how many labeled nodes are reachable from one queried source node in a directed graph, either directly or after one hypothetical arrow edit.

## 2) Scene + task contract
1. Branch metadata: `query_id`
2. `query_id`: `reachable_count`, `reachable_count_after_edge_removal`, or `reachable_count_after_edge_addition`
3. Supported `scene_variant` values: `circular`, `shell`, `spring`, `grid_jitter`, `layered`, `component_clustered`, `path_spine`, `radial_tree`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `point_set`
5. Scene contract:
   - one single-panel labeled directed node-link graph per image,
   - simple unweighted graph only,
   - no self-loops,
   - no reciprocal edge pairs,
   - node count is branch-specific,
   - visible node labels use one whole-image label format (`letters`, `numbers`, or `named`).
6. Query contract:
   - direct branch asks how many nodes are reachable from the queried node by following arrow directions,
   - edit branches ask the same reachability count after adding or removing one specified arrow,
   - the queried source node itself is included in both the answer and the evidence set.
7. Reachability policy:
   - `target_reachable_count` is sampled from branch-specific support,
   - node count is chosen from the feasible support that can realize the requested reachable count while leaving at least one unreachable node,
   - generation constructs a directed reachable subgraph rooted at the query node, separately constructs unreachable structure, and verifies the finalized successor adjacency before exposing the witness set.
8. Topology variation:
   - `topology_profile` values are `balanced`, `low_degree`, and `hub_heavy`,
   - topology profile affects branching inside the reachable region and how extra safe directed edges are retained,
   - graph semantics always come from directed adjacency, never from layout position.
9. Layout variation:
   - `scene_variant` records the realized graph layout,
   - requested layout variants are all reusable node-link layouts: `circular|shell|spring|grid_jitter|layered|component_clustered|path_spine|radial_tree`,
   - the renderer may fall back to `circular` when a sampled layout is too cramped for readable node separation.
10. Visual variation:
   - one whole-image named node color is sampled from the shared TRACE named-color palette,
   - one whole-image node glyph style is sampled from `circle|rounded_square|hexagon`,
   - one whole-image label format is sampled from `letters|numbers|named`,
   - one whole-image edge routing style is sampled from `straight|mixed_arc`,
   - one whole-image layout transform is sampled from `identity|rotate_90|rotate_180|rotate_270|mirror_left_right|mirror_up_down`,
   - these style axes are non-semantic for this task and are recorded in trace metadata.

## 3) Prompt contract
1. Bundle: `graph_relation_v0`
2. `scene_key`: `single_graph_relation`
3. `task_key`: `reachable_count_query` or `reachable_count_after_edge_edit_query`
4. Required slots:
   - scene: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Modes: `answer_only`, `answer_and_evidence`
6. Answer-only JSON shape: `{"answer":3}`
7. Answer+evidence JSON shape: `{"evidence":[[180,220],[310,180],[430,260]],"answer":3}`
8. Prompt-facing evidence uses pixel-space node-center points; node labels remain in `witness_symbolic`.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the `point_set` of node-center pixel points for all nodes reachable from the queried source node, including the queried node itself.
2. The witness set is unordered semantically; the implementation keeps the corresponding labels in `witness_symbolic` and canonicalizes label order internally for deterministic serialization.
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
   - `point_set`
   - `pixel_point_set`
   - `pixel_bbox_set`
7. `execution_trace` records:
   - `query_id`
   - `query_id` (always `default`)
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
2. Current graph scenes use a single rounded light panel on a light solid background.
3. Node labels are rendered inside the nodes and stay visually stable across layout, label-format, shape, and color variants.
4. Directed edges always render arrowheads.
5. Layout and styling may vary for readability and diversity, but the prompt never refers to node position, node color, or node shape as the semantic source of truth.
6. When `label_variant=named`, prompt references to the queried node are quoted, for example node `"Abby"`.

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
