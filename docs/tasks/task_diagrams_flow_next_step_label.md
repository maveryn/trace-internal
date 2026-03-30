# `task_diagrams_flow_next_step_label`

## 1) Identity
1. Domain: `diagrams`
2. Task group: `flow`
3. Task id: `task_diagrams_flow_next_step_label`
4. Objective: read one labeled process diagram and return the exact visible label of the next step requested by the prompt.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `direct_next_step`
   - `branch_next_step`
2. Supported `scene_variant` values:
   - `flowchart`
   - `swimlane`
3. `answer_gt.type`: `string`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one process diagram panel is shown on a light background,
   - the panel contains labeled process nodes connected by arrows,
   - the prompt asks for the next visible step after one queried node or one queried branch from a decision node,
   - the answer is the exact visible target-step label,
   - the active scene variants keep the same step/arrow semantics while changing only the diagram chrome.
6. Generation guarantees:
   - visible node labels are unique within one diagram,
   - the queried relationship has exactly one valid next-step answer,
   - branch queries make the branch label explicit in the prompt.

## 3) Prompt contract
1. Bundle: `diagrams_flow_v1`
2. `task_family_key`: `process_flow_diagram`
3. `task_key`: `next_step_query`
4. `task_variant_key`: one of `direct_next_step|branch_next_step`
5. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/diagrams/flow.yaml`,
   - deterministic bundle selection from `prompts/diagrams/flow/diagrams_flow_v1.json`,
   - task-local JSON examples keyed by the active flow-query variant.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the exact visible next-step label; prompt-facing evidence is the single target-node bbox.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` with exactly one box:
   - the bbox of the correct next-step node.
2. `scene_ir.entities` stores:
   - `diagram_panel`
   - `diagram_title`
   - `diagram_lane` / `diagram_lane_label` for swimlanes
   - `diagram_node`
   - `diagram_node_label`
   - `diagram_edge`
   - `diagram_edge_label` for labeled branch edges
3. `render_map` includes:
   - `panel_bbox_px`
   - `title_bbox_px`
   - `lane_bboxes_px`
   - `lane_label_bboxes_px`
   - `node_bboxes_px`
   - `node_label_bboxes_px`
   - `edge_label_bboxes_px`
4. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `question_format`
   - `view_family`
   - `scene_title`
   - `question_text`
   - `topology_node_count`
   - `lane_count`
   - `lane_specs`
   - `node_specs`
   - `edge_specs`
   - `query_node_id`
   - `query_node_label`
   - `query_branch_label`
   - `answer_node_id`
   - `answer_node_label`
   - `answer_node_bbox_id`
5. `witness_symbolic` stores the answer node id, while `projected_evidence` stores the target-node bbox.

## 5) Visual policy
1. Background and post-image noise use the merged diagrams-domain visual defaults from `configs/domains/diagrams/base.yaml`.
2. V1 flow scenes stay schematic and OCR-light:
   - short visible step labels,
   - high-contrast nodes and arrows,
   - no long paragraph text inside boxes.
3. The scene variants should feel visibly different:
   - `flowchart` uses one plain process chart panel,
   - `swimlane` uses horizontal lane bands with left-side lane labels.
4. Layout reasoning should stay local:
   - the prompt references one visible node and optionally one explicit branch label,
   - the answer is one visible target node label,
   - evidence stays on the target node itself.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same exact rendered target node.
4. No semantic auto-relaxation.
5. If a sampled diagram would produce duplicate visible node labels or multiple next-step answers for the queried relationship, reject and resample instead of silently rewriting the query.
