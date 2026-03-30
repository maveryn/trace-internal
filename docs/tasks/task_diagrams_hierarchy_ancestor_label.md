# `task_diagrams_hierarchy_ancestor_label`

## 1) Identity
1. Domain: `diagrams`
2. Task group: `hierarchy`
3. Task id: `task_diagrams_hierarchy_ancestor_label`
4. Objective: read one labeled org chart and return the exact visible parent or lowest common ancestor label requested by the prompt.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `parent_of_node`
   - `lowest_common_ancestor_of_two_nodes`
2. Supported `scene_variant` values:
   - `org_chart`
3. `answer_gt.type`: `string`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one hierarchy diagram panel is shown on a light background,
   - the panel contains labeled org-chart boxes connected by visible parent-child lines,
   - the prompt asks either for one queried node's parent or for the lowest common ancestor of two queried nodes,
   - the answer is the exact visible target-node label,
   - the active scene variant keeps one reusable org-chart grammar for both hierarchy-query variants.
6. Generation guarantees:
   - visible node labels are unique within one hierarchy,
   - the hierarchy is a rooted tree with one unique parent per non-root node,
   - LCA queries use two visible non-root nodes and have exactly one valid common-ancestor answer.

## 3) Prompt contract
1. Bundle: `diagrams_hierarchy_v1`
2. `task_family_key`: `hierarchy_diagram`
3. `task_key`: `ancestor_query`
4. `task_variant_key`: one of `parent_of_node|lowest_common_ancestor_of_two_nodes`
5. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/diagrams/hierarchy.yaml`,
   - deterministic bundle selection from `prompts/diagrams/hierarchy/diagrams_hierarchy_v1.json`,
   - task-local JSON examples keyed by the active hierarchy-query variant.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the exact visible ancestor label; prompt-facing evidence is the single target-node bbox.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` with exactly one box:
   - the bbox of the correct parent or lowest-common-ancestor node.
2. `scene_ir.entities` stores:
   - `diagram_panel`
   - `diagram_title`
   - `diagram_node`
   - `diagram_node_label`
   - `diagram_edge`
3. `render_map` includes:
   - `panel_bbox_px`
   - `title_bbox_px`
   - `node_bboxes_px`
   - `node_label_bboxes_px`
   - `edge_bboxes_px`
4. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `question_format`
   - `view_family`
   - `scene_title`
   - `question_text`
   - `template_id`
   - `tree_node_count`
   - `tree_depth`
   - `leaf_count`
   - `root_node_id`
   - `node_specs`
   - `edge_specs`
   - `query_node_ids`
   - `query_node_labels`
   - `query_depths`
   - `query_relationship`
   - `answer_node_id`
   - `answer_node_label`
   - `answer_node_bbox_id`
   - `answer_node_depth`
   - `lca_span`
5. `witness_symbolic` stores the answer node id, while `projected_evidence` stores the target-node bbox.

## 5) Visual policy
1. Background and post-image noise use the merged diagrams-domain visual defaults from `configs/domains/diagrams/base.yaml`.
2. V1 hierarchy scenes stay schematic and OCR-light:
   - short visible node labels,
   - high-contrast parent-child connectors,
   - no extra decorations beyond the org-chart panel chrome.
3. The first hierarchy scene variant is `org_chart`, which keeps a top-down rooted tree layout with one highlighted root style and consistent branch routing.
4. Layout reasoning should stay local:
   - the prompt references one or two visible node labels,
   - the answer is one visible target node label,
   - evidence stays on the target node itself.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same exact rendered target node.
4. No semantic auto-relaxation.
5. If a sampled hierarchy would produce duplicate visible node labels or a malformed tree relation, reject and resample instead of silently rewriting the query.
