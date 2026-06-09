# `task_misc__abacus_match_panel__target_value_match_label`

## 1) Identity
1. Domain: `misc`
2. Scene id: `abacus_match_panel`
3. Source task group: `abacus`
4. Task id: `task_misc__abacus_match_panel__target_value_match_label`
5. Objective: select the labeled abacus option whose bead positions represent the target integer named in the prompt.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. Supported `query_id` values:
   - `target_value_match_label`
3. Supported non-semantic visual axes:
   - `scene_variant`: `clean_card|wood_frame|worksheet`
   - shared misc background/panel style
4. `answer_gt.type`: `option_letter`
5. `annotation_gt.type`: `bbox_set`
6. Scene contract:
   - exactly six visual option cards labeled `A..F`,
   - each option card contains one compact three-column soroban-style abacus with columns labeled `100`, `10`, and `1`,
   - each abacus column has one upper bead worth `5` and four lower beads worth `1`,
   - the target value appears in the prompt, not as target text inside the image,
   - exactly one option represents the target value,
   - v1 target value support is `0..999`.

## 3) Prompt Contract
1. Bundle: `misc_abacus_v0`
2. `scene_key`: `abacus_match_panel`
3. `task_key`: `abacus_target_value_match_query`
4. Query key: `target_value_match_label`
5. Required slots:
   - scene: `object_description`
   - query: `target_value`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
6. Modes: `answer_only`, `answer_and_annotation`
7. Prompt-facing answer is the single capital-letter option label.

## 4) Annotation + Trace Contract
1. Prompt-facing annotation is a one-box `bbox_set` containing the selected option card bbox.
2. `projected_annotation` includes `bbox_set` and `pixel_bbox_set`.
3. `scene_ir.entities` stores option cards, option label badges, abacus frames, columns, and beads.
4. `render_map` includes:
   - `option_card_bboxes_px`
   - `option_abacus_bboxes_px`
   - `selected_option_card_bbox_px`
   - `selected_option_abacus_bbox_px`
   - `correct_label`
5. `execution_trace` records:
   - active query id and scene variant,
   - target value and target digits,
   - option labels and option values,
   - correct label,
   - support range and sampling probabilities.

## 5) Visual Policy
1. Option labels are fixed in row-major `A..F` positions.
2. Annotation marks the selected option card, not the individual beads or option label text alone.
3. Active and inactive beads use the same fill color within a rendered scene variant; value state is conveyed by bead position relative to the beam.
4. The image contains only the six abacus options; target-value text belongs in the prompt.
5. Post-image noise uses the conservative abacus default.

## 6) Determinism + Constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Scene variant, target value, and correct option label are sampled internally unless explicitly overridden.
3. Answers and annotation come from finalized rendered option-card positions.
4. Reject conditions:
   - target support outside `0..999`,
   - explicit target outside configured support,
   - non-six option label support,
   - duplicate option labels,
   - failure to construct exactly one matching option.

## 7) Complexity + Tests
1. Complexity components: `visual_scan`, `reasoning_load`, `scene_variant_load`
2. Behavior/trace/prompt tests: `tests/test_misc_abacus_tasks.py`
3. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_misc_core_task_group_config.py`
