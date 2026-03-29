# `task_graph_order_topological_position`

## 1) Identity
1. Domain: `graph`
2. Task group: `order`
3. Task id: `task_graph_order_topological_position`
4. Objective: return the 1-based position of one queried node in the graph's unique topological order.

## 2) Scene + task contract
1. Supported `task_variant` values: `topological_position`
2. Supported `scene_variant` values: `circular`, `shell`, `spring`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `label_sequence`
5. Scene contract:
   - one single-panel labeled directed acyclic graph per image,
   - unique topological order guaranteed by construction and verified on the finalized successor adjacency,
   - visible node labels use one whole-image label format (`A..G` or `1..7`),
   - node count samples from `5..7`,
   - graphs remain simple, directed, and acyclic.
6. Query contract:
   - the prompt asks `What is the position of node X in the unique topological order, counting from 1?`,
   - answer is the queried node's 1-based position in the unique topological order,
   - evidence is the full ordered node-label sequence from first to last in that unique order.
7. Topology policy:
   - `target_position` is sampled from `1..7`,
   - node count is chosen from feasible support that can realize the requested position,
   - construction uses one full backbone chain over the hidden node order plus additional forward edges that preserve the same unique order,
   - `topology_profile` controls how many non-chain forward edges are added and how long-range they tend to be.
8. Visual variation:
   - one whole-image named node color is sampled from the shared TRACE named-color palette,
   - one whole-image node glyph style is sampled from `circle|rounded_square|hexagon`,
   - one whole-image label format is sampled from `letters|numbers`,
   - one whole-image layout transform is sampled from `identity|rotate_90|rotate_180|rotate_270|mirror_left_right|mirror_up_down`,
   - these style axes are non-semantic for this task.

## 3) Prompt contract
1. Bundle: `graph_order_v1`
2. `task_family_key`: `single_graph_order`
3. `task_key`: `topological_position_query`
4. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Modes: `answer_only`, `answer_and_evidence`
6. Answer-only JSON shape: `{"answer":3}`
7. Answer+evidence JSON shape: `{"evidence":["A","B","C","D","E"],"answer":3}`
8. Prompt-facing evidence uses an ordered node-label sequence because node order is semantically required, but consecutive labels are not required to form graph edges.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the `label_sequence` of all node labels in the unique topological order, from first to last.
2. `answer_gt.value` equals the 1-based index of the queried node inside that ordered evidence sequence.
3. `scene_ir.entities` stores one node entity per rendered node with:
   - visible label,
   - total/in/out degree,
   - predecessors and successors,
   - query-node flag,
   - resolved topological position,
   - node center and bbox.
4. `scene_ir.relations` stores:
   - relation rule id,
   - query label,
   - unique topological order labels,
   - directed successor/predecessor adjacency,
   - target position.
5. `projected_evidence` includes:
   - `label_sequence`
   - `pixel_point_path`
   - `pixel_bbox_set`
6. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `query_label`
   - `target_position`
   - `topological_order_labels`
   - `extra_edge_count`
   - feasible support distributions for node count / target position
   - requested and realized layout variants
   - finalized successor/predecessor adjacency

## 5) Visual policy
1. Background and post-image noise use the merged graph-domain visual defaults from `configs/domains/graph/base.yaml`.
2. V1 graphs use a single rounded light panel on a light solid background.
3. Directed edges render arrowheads, but semantics still come from adjacency rather than layout.
4. Ordered evidence overlays may connect node centers in witness order for review, but that overlay path is only a visualization of the sequence, not a claim that consecutive labels are adjacent.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same finalized successor adjacency.
3. Unique-answer policy: generation targets one explicit node position inside a unique topological order and rejects any finalized graph with either multiple valid topological orders or a mismatched queried position.
4. Reject/resample conditions:
   - no feasible node-count support for the requested position,
   - graph is not acyclic after construction,
   - finalized successor adjacency admits more than one topological order,
   - unreadable layout that cannot keep nodes sufficiently separated.
5. No semantic auto-relaxation: failures do not weaken the DAG or unique-order contract.

## 7) Complexity + tests
1. Complexity definition/components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Determinism/build tests: `tests/test_graph_order_topological_position_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_graph_order_topological_position_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
