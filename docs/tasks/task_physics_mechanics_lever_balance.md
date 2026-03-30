# `task_physics_mechanics_lever_balance`

## 1) Identity
1. Domain: `physics`
2. Task group: `mechanics`
3. Task id: `task_physics_mechanics_lever_balance`
4. Objective: answer one simple lever-balance question from the shown beam, fulcrum, distances, and weight blocks using lightweight integer arithmetic.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `center_fulcrum`
   - `offset_fulcrum`
   - `textured_beam`
2. Supported `query_variant` / emitted `task_variant` values:
   - `left_torque`
   - `right_torque`
   - `missing_weight_to_balance`
3. Compatibility:
   - all three scene variants support all three query variants.
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - the image shows one horizontal beam, one triangular fulcrum, integer distance marks `1..4` on both sides, and weight blocks resting on the beam,
   - weight blocks display plain integer values in the image, except `missing_weight_to_balance`, which replaces one block value with a visible red `?`,
   - `offset_fulcrum` shifts the pivot away from the image center for visual variety,
   - `textured_beam` adds subtle beam texture only; it does not change the arithmetic contract,
   - one non-semantic `accent_color_name` axis randomizes the beam / fulcrum / weight palette, while the marked red `?` weight stays fixed for salience.
7. Query contract:
   - `left_torque` asks for the total torque from the left-side weights about the fulcrum,
   - `right_torque` asks for the total torque from the right-side weights about the fulcrum,
   - `missing_weight_to_balance` asks for the value of the marked `?` weight that would balance the lever.
8. Answer policy:
   - all answers are non-negative integers,
   - torque answers come from the configured torque support,
   - missing-weight answers come from the configured missing-weight support.

## 3) Prompt contract
1. Bundle: `physics_mechanics_v1`
2. `task_family_key`: `lever_balance_diagram`
3. `task_key`: `lever_balance_query`
4. `task_variant_key`: `left_torque|right_torque|missing_weight_to_balance`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/physics/mechanics.yaml`,
   - deterministic bundle selection from `prompts/physics/mechanics/physics_mechanics_v1.json`,
   - prompt JSON examples are generated in task code from the active `bbox_set` schema.
7. Modes: `answer_only`, `answer_and_evidence`

## 4) Evidence + trace contract
1. `left_torque` and `right_torque` use prompt-facing unordered `bbox_set` evidence over the weight blocks on the queried side of the fulcrum.
2. `missing_weight_to_balance` uses prompt-facing one-box `bbox_set` evidence over the marked red `?` weight block.
3. `scene_ir.entities` stores:
   - one `physics_lever_beam`,
   - one `physics_fulcrum`,
   - one `physics_lever_weight` entity per shown weight block,
   - zero or one `physics_missing_weight_marker`.
4. `render_map` includes:
   - `beam_bbox_px`,
   - `fulcrum_bbox_px`,
   - `weight_bboxes_px`,
   - `relevant_weight_ids`,
   - `evidence_entity_ids`,
   - optional `missing_weight_marker_bbox_px`.
5. `execution_trace` records:
   - `scene_variant`
   - `query_variant`
   - `accent_color_name`
   - `target_answer`
   - optional `query_side`
   - optional `placeholder_side`
   - optional `placeholder_distance_units`
   - `known_torque_left`
   - `known_torque_right`
   - one spec per visible weight block (`side`, `distance_units`, `value`, `missing`, `relevant_to_query`)
   - `relevant_weight_ids`
   - `evidence_entity_ids`

## 5) Visual policy
1. Background and post-image noise use the merged physics-domain visual defaults from `configs/domains/physics/base.yaml`.
2. Weight labels should stay centered in their blocks, and distance labels should stay readable beneath their tick marks.
3. Prompt-facing evidence should stay on the operative weight blocks rather than on the beam, fulcrum, or decorative texture.
4. The sampled accent color may restyle the beam, fulcrum, and shown weight blocks, but it must not change the prompt contract or the red missing-weight marker semantics.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `scene_variant`, `query_variant`, and `target_answer` are each sampled through explicit supports/weights with deterministic balancing.
3. Answers and evidence come from the same finalized lever layout.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - unsupported scene/query combinations,
   - explicit `target_answer` outside the active support,
   - failure to construct bounded integer weight layouts for the requested answer.

## 7) Complexity + tests
1. Complexity definition/components: `visual_scan`, `torque_reasoning`, `ambiguity`, `output_burden`
2. Determinism/build tests: `tests/test_physics_mechanics_lever_balance_contracts.py`
3. Config tests: `tests/test_physics_mechanics_lever_balance_task_group_config.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
