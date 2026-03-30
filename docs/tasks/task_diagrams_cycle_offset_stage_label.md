# `task_diagrams_cycle_offset_stage_label`

## 1) Identity
1. Domain: `diagrams`
2. Task group: `cycle`
3. Task id: `task_diagrams_cycle_offset_stage_label`
4. Objective: read one directed cycle diagram and return the exact visible stage label that is `k` steps before or after a queried stage.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `after_k_steps`
   - `before_k_steps`
2. Supported `scene_variant` values:
   - `cycle_ring`
3. `answer_gt.type`: `string`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one cycle diagram panel is shown on a light background,
   - the panel contains `5..10` labeled stages arranged around a directed ring,
   - visible arrows and a clockwise badge establish the cycle direction,
   - the prompt asks for the exact visible stage that is `k` steps before or after one queried stage,
   - the answer is the exact visible target-stage label.
6. Generation guarantees:
   - visible stage labels are unique within one cycle,
   - `stage_count` is always between `5` and `10`,
   - `step_count` is always between `1` and `stage_count - 1`,
   - the rendered cycle order yields exactly one valid target-stage answer.

## 3) Prompt contract
1. Bundle: `diagrams_cycle_v1`
2. `task_family_key`: `cycle_diagram`
3. `task_key`: `offset_stage_query`
4. `task_variant_key`: one of `after_k_steps|before_k_steps`
5. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/diagrams/cycle.yaml`,
   - deterministic bundle selection from `prompts/diagrams/cycle/diagrams_cycle_v1.json`,
   - task-local JSON examples keyed by the active cycle-query variant.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the exact visible target-stage label; prompt-facing evidence is the single target-stage bbox.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` with exactly one box:
   - the bbox of the correct target stage.
2. `scene_ir.entities` stores:
   - `diagram_panel`
   - `diagram_title`
   - `diagram_direction_badge`
   - `diagram_direction_badge_label`
   - `diagram_stage`
   - `diagram_stage_label`
   - `diagram_edge`
3. `render_map` includes:
   - `panel_bbox_px`
   - `title_bbox_px`
   - `direction_badge_bbox_px`
   - `stage_bboxes_px`
   - `stage_label_bboxes_px`
   - `edge_bboxes_px`
4. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `question_format`
   - `view_family`
   - `scene_title`
   - `question_text`
   - `direction`
   - `stage_count`
   - `step_count`
   - `query_relationship`
   - `query_stage_id`
   - `query_stage_label`
   - `query_stage_index`
   - `answer_stage_id`
   - `answer_stage_label`
   - `answer_stage_bbox_id`
   - `answer_stage_index`
   - `stage_specs`
   - `edge_specs`
5. `witness_symbolic` stores the answer stage id, while `projected_evidence` stores the target-stage bbox.

## 5) Visual policy
1. Background and post-image noise use the merged diagrams-domain visual defaults from `configs/domains/diagrams/base.yaml`.
2. V1 cycle scenes stay schematic and OCR-light:
   - short visible stage labels,
   - one consistent ring layout,
   - clear arrow direction around the cycle,
   - no extra decorations beyond the panel chrome and clockwise badge.
3. The first cycle scene variant is `cycle_ring`, which keeps one reusable circular stage layout for both `before` and `after` queries.
4. Layout reasoning should stay local:
   - the prompt references one visible stage label and one visible step count,
   - the answer is one visible target-stage label,
   - evidence stays on the target stage itself.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same exact rendered target stage.
4. No semantic auto-relaxation.
5. If a sampled cycle would produce duplicate visible labels or an invalid `k` range, reject and resample instead of silently rewriting the query.
