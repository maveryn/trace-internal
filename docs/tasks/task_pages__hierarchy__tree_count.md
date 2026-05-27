# `task_pages__hierarchy__tree_count`

## 1) Identity
1. Domain: `pages`
2. Task group: `hierarchy`
3. Task id: `task_pages__hierarchy__tree_count`
4. Objective: read one generic rooted tree diagram and return the requested integer count.

## 2) Scene + task contract
1. Supported `query_id` values:
   - `subtree_descendant_count`
   - `subtree_leaf_count`
   - `path_length_between_two_nodes`
2. Supported `scene_variant` values:
   - `rooted_tree`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one rooted tree diagram panel is shown on a light background,
   - the panel contains short labeled node boxes connected by visible parent-child lines,
   - the answer is computed from the rooted tree structure, not from free-form graph adjacency,
   - tree size is larger than the old hierarchy ancestor task: `16..30` nodes and total depth `4..8`.
6. Answer supports:
   - `subtree_descendant_count`: `4..18`
   - `subtree_leaf_count`: `2..12`
   - `path_length_between_two_nodes`: `3..16`

## 3) Prompt contract
1. Bundle: `pages_hierarchy_v0`
2. `scene_key`: `hierarchy_diagram`
3. `task_key`: `tree_count_query`
4. `query_key`: one of `subtree_descendant_count|subtree_leaf_count|path_length_between_two_nodes`
5. Required slots:
   - scene: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt-facing answer is an integer count.

## 4) Evidence + trace contract
1. `subtree_descendant_count` evidence is the unordered set of node bboxes for all counted descendants of the queried node.
2. `subtree_leaf_count` evidence is the unordered set of node bboxes for all counted leaf descendants in the queried subtree.
3. `path_length_between_two_nodes` evidence is the ordered set of node bboxes on the path from the first queried node to the second queried node. The answer counts hops, so evidence length is `answer + 1`.
4. `execution_trace` records:
   - `query_id`
   - `scene_variant`
   - `question_format`
   - `view_family`
   - `tree_node_count`
   - `tree_depth`
   - `leaf_count`
   - `root_node_id`
   - `node_specs`
   - `edge_specs`
   - `query_node_ids`
   - `query_node_labels`
   - `query_relationship`
   - `answer_count`
   - `evidence_node_ids`
   - `evidence_node_bbox_ids`
   - `descendant_count`
   - `leaf_descendant_count`
   - `path_node_ids`
   - `path_length_between_nodes`
   - `path_lca_node_id`
   - `path_lca_depth`

## 5) Visual policy
1. The active renderer is the shared top-down hierarchy renderer with a neutral rooted-tree scene title.
2. Node labels stay short and unique within a scene.
3. Evidence remains on node boxes; connector geometry stays in trace unless a later task explicitly queries connectors.
4. This task stays in `pages/hierarchy` because it asks about a visually rooted parent-child hierarchy, not arbitrary graph connectivity.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `query_id`, answer support, tree size, and tree depth are balanced through seeded sampling under the normal seeded sampler.
3. Answers and evidence come from the same generated tree trace.
4. No semantic auto-relaxation.
