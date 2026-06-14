# `task_symbolic__abacus_readout__displayed_value_readout`

## 1) Identity
1. Domain: `symbolic`
2. Scene id: `abacus_readout`
3. Source scene: `abacus`
4. Task id: `task_symbolic__abacus_readout__displayed_value_readout`
5. Objective: read the integer value represented by a three-column soroban-style abacus.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. Supported `query_id` values:
   - `displayed_value_readout`
3. Supported non-semantic visual axes:
   - `scene_variant`: `clean_card|wood_frame|worksheet`
   - shared symbolic background/panel style
4. `answer_gt.type`: `integer`
5. `annotation_gt.type`: `keyed_point_set_map`
6. Scene contract:
   - exactly three place-value columns labeled `100`, `10`, and `1`,
   - each column has one upper bead worth `5` and four lower beads worth `1`,
   - active beads are the beads moved toward the center beam,
   - the answer is `hundreds_digit * 100 + tens_digit * 10 + ones_digit`,
   - Answer support is `0..999`.

## 3) Prompt Contract
1. Bundle: `symbolic_abacus_v0`
2. `scene_key`: `abacus_readout`
3. `task_key`: `abacus_displayed_value_query`
4. Query key: `displayed_value_readout`
5. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
6. Modes: `answer_only`, `answer_and_annotation`
7. Prompt-facing answer is the integer shown by the abacus.

## 4) Annotation + Trace Contract
1. Prompt-facing annotation is role-keyed:
   - `hundreds_active_beads`: pixel-space center-point list for active beads in the `100` column,
   - `tens_active_beads`: pixel-space center-point list for active beads in the `10` column,
   - `ones_active_beads`: pixel-space center-point list for active beads in the `1` column.
2. Empty lists are valid for columns whose digit is `0`.
3. `projected_annotation` includes `keyed_point_set_map` and `pixel_keyed_point_set_map`.
4. `scene_ir.entities` stores column and bead entities.
5. `render_map` includes:
   - `bead_bboxes_px`
   - `active_bead_bboxes_by_column_px`
   - `active_bead_points_by_column_px`
   - `active_bead_ids_by_column`
   - `column_bboxes_px`
   - `label_bboxes_px`
6. `execution_trace` records:
   - active query id and scene variant,
   - digits and place values by column role,
   - answer value,
   - active bead ids for each column.

## 5) Visual Policy
1. Place labels identify column value but are not annotation witnesses.
2. Annotation marks active bead center points only, not rods, labels, or the frame.
3. Active and inactive beads use the same fill color within a rendered scene variant; value state is conveyed by bead position relative to the beam.
4. All labels use one deterministic readout font family recorded by the shared task wrapper.
5. Post-image noise uses the conservative abacus default.

## 6) Determinism + Constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Scene variant and displayed value are sampled internally unless explicitly overridden.
3. Answers and annotation come from the finalized rendered bead positions.
4. Reject conditions:
   - answer support outside `0..999`,
   - explicit answer outside configured support,
   - non-three-column scene requests.

## 7) Complexity + Tests
1. Complexity components: `visual_scan`, `reasoning_load`, `scene_variant_load`
2. Behavior/trace/prompt tests: `tests/test_symbolic_abacus_tasks.py`
3. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_symbolic_core_scene_config.py`
