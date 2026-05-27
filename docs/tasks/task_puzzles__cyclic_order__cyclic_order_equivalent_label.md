# `task_puzzles__cyclic_order__cyclic_order_equivalent_label`

## 1) Identity
1. Domain: `puzzles`
2. Task group: `topology`
3. Scene id: `cyclic_order`
4. Task id: `task_puzzles__cyclic_order__cyclic_order_equivalent_label`
5. Objective: identify the unique option loop with the same cyclic token order as a reference loop when rotation and smooth deformation are allowed but reflection is not.

## 2) Scene + task contract
1. Public `query_variant`: `default`
2. `query_id`: `cyclic_order_equivalent_label`
3. Supported `token_render_style` values:
   - `colored_beads`
   - `shape_tokens`
   - `colored_shape_tokens`
   - `outline_shape_tokens`
   - `symbol_badges`
4. Supported `scene_variant` values:
   - `necklace_board`
   - `charm_card_grid`
   - `route_loop_diagram`
   - `token_ring_outline`
5. Supported `loop_path_style` values:
   - `ellipse`
   - `rounded_rect`
   - `polygon_loop`
   - `wavy_loop`
   - `beaded_string`
6. `answer_gt.type`: `option_letter`
7. `evidence_gt.type`: `bbox_set`
8. Generation guarantees:
   - option count is fixed at `6`,
   - exactly one option is valid,
   - token count defaults to `4..5`,
   - color-bearing token render styles use distinct colors with minimum Lab separation `DeltaE*ab >= 50`,
   - the valid option preserves the reference cyclic order up to rotation,
   - every invalid option breaks the cyclic order by construction.

## 3) Prompt contract
1. Bundle: `puzzles_topology_v0`
2. `scene_key`: `topology_cyclic_order_puzzle`
3. `task_key`: `cyclic_order_match_query`
4. `query_key`: `cyclic_order_equivalent_label`
5. Required slots:
   - scene: `object_description`
   - query-variant: `token_render_style_instruction`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt-facing answer is the unique valid option letter. Prompt-facing evidence is the matching option-image bounding box.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` containing exactly one option-image bbox.
2. `projected_evidence` includes `bbox_set`.
3. `render_map.option_choice_bboxes_px` stores option-image bboxes keyed by `option_choice_id`.
4. `execution_trace` records `query_variant=default`, `query_id=cyclic_order_equivalent_label`, `internal_query_variant=cyclic_order_equivalent_label`, token/render axes, option specs, answer option id/label, valid option id, and solver trace.
5. Prompt-facing evidence is projected from the recorded valid option id, not inferred from pixels.

## 5) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same generated reference/option set.
3. No semantic auto-relaxation.
4. Review overlays rely on recorded option-image projections.
