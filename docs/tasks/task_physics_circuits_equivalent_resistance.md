# `task_physics_circuits_equivalent_resistance`

## 1) Identity
1. Domain: `physics`
2. Task group: `circuits`
3. Task id: `task_physics_circuits_equivalent_resistance`
4. Objective: answer one simple equivalent-resistance question from a resistor network drawn between labeled terminals `A` and `B`.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `parallel`
   - `simple_series_parallel`
2. Supported `query_variant` / emitted `task_variant` values:
   - `total_resistance`
   - `missing_resistor_value`
3. Compatibility:
   - both scene variants support both query variants.
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - `total_resistance` shows one resistor network between labeled terminals `A` and `B`,
   - `missing_resistor_value` shows two side-by-side resistor networks between labeled terminals `A` and `B`, with one red `?` resistor in the left circuit and both circuits constructed to have the same total equivalent resistance,
   - resistor values are printed as plain integers inside resistor boxes,
   - every valid scene includes at least one parallel section,
   - `parallel` uses three or four single-resistor branches between the same terminal rails,
   - `simple_series_parallel` combines a short one- or two-resistor series chain with a two- or three-branch parallel bank for a total of four or five visible resistors,
   - `missing_resistor_value` uses smaller paired layouts: `parallel` uses `2..3` branches per circuit, and `simple_series_parallel` uses one missing series resistor plus a two-branch parallel bank on the left with a matching three-resistor right circuit,
   - one non-semantic `accent_color_name` axis may recolor the wires, terminals, and resistor boxes without changing the circuit semantics.
7. Query contract:
   - `total_resistance` asks for the total equivalent resistance between terminals `A` and `B`.
   - `missing_resistor_value` asks for the integer value that should replace the red `?` resistor in the left circuit so the left and right circuits have the same total equivalent resistance between `A` and `B`.
8. Answer policy:
   - all answers are positive integers,
   - all scenes are sampled only when the resulting equivalent resistance is integral.

## 3) Prompt contract
1. Bundle: `physics_circuits_v1`
2. `task_family_key`: `resistor_network_diagram`
3. `task_key`: `equivalent_resistance_query`
4. `task_variant_key`: `total_resistance|missing_resistor_value`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/physics/circuits.yaml`,
   - deterministic bundle selection from `prompts/physics/circuits/physics_circuits_v1.json`,
   - prompt JSON examples are generated in task code from the active `bbox_set` schema.
7. Modes: `answer_only`, `answer_and_evidence`

## 4) Evidence + trace contract
1. Prompt-facing evidence is:
   - an unordered `bbox_set` over all resistor boxes in the asked network for `total_resistance`,
   - a one-box `bbox_set` over the marked red `?` resistor in the left circuit for `missing_resistor_value`.
2. `scene_ir.entities` stores:
   - two `physics_circuit_terminal` entities (`A` and `B`),
   - one `physics_resistor` entity per visible resistor box, with `meta.missing=true` on the hidden-value resistor when present.
3. `render_map` includes:
   - `accent_color_name`,
   - `resistor_bboxes_px`,
   - `wire_segments_px`,
   - `terminal_bboxes_px`,
   - `terminal_label_bboxes_px`,
   - `evidence_entity_ids`,
   - `missing_resistor_entity_ids` for `missing_resistor_value`,
   - `equals_sign_bbox_px` for the paired-circuit scene.
4. `execution_trace` records:
   - `scene_variant`
   - `query_variant`
   - `accent_color_name`
   - `target_answer`
   - `target_answer_support`
   - optional `series_parallel_orientation`
   - one spec per resistor (`resistor_id`, `value`, `missing`)
   - paired-scene layout fields for `missing_resistor_value` (`paired_total_resistance`, left/right component values, left/right orientations, `missing_resistor_index`)
   - `evidence_entity_ids`

## 5) Visual policy
1. Background and post-image noise use the merged physics-domain visual defaults from `configs/domains/physics/base.yaml`.
2. Terminals `A` and `B` must stay visibly labeled in the scene, because the prompt asks about equivalent resistance specifically between those two endpoints.
3. Prompt-facing evidence should stay on the resistor boxes rather than on the wires or decorative scene chrome.
4. In `missing_resistor_value`, the missing resistor should stay visibly red and the two circuits should be clearly separated as left/right diagrams with an equality cue between them.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `scene_variant`, `query_variant`, `accent_color_name`, and `target_answer` are sampled through explicit supports/weights with deterministic balancing.
3. Answers and evidence come from the same finalized resistor layout.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - unsupported scene/query combinations,
   - explicit `target_answer` outside the active scene/query-specific support,
   - failure to construct an integer-valued resistor layout for the requested scene/answer pair,
   - any layout that lacks a parallel section.

## 7) Complexity + tests
1. Complexity definition/components: `visual_scan`, `circuit_reasoning`, `ambiguity`, `output_burden`
2. Determinism/build tests: `tests/test_physics_circuits_equivalent_resistance_contracts.py`
3. Config tests: `tests/test_physics_circuits_equivalent_resistance_task_group_config.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
