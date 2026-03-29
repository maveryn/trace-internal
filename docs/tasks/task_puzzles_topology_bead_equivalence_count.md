# `task_puzzles_topology_bead_equivalence_count`

## 1) Identity
1. Domain: `puzzles`
2. Task group: `topology`
3. Task id: `task_puzzles_topology_bead_equivalence_count`
4. Objective: count how many option loops preserve the same bead order around the loop as the reference loop when rotation and smooth deformation are allowed but reflection is not.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `color_cycle_count`
   - `shape_cycle_count`
   - `mixed_cycle_count`
2. Supported `scene_variant` values:
   - `loop_strip`
   - `loop_card`
   - `loop_outline`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one reference bead loop appears above several labeled option loops,
   - the reference loop and option loops may deform between circle-like, wide, and tall shapes,
   - the bead order is read around each loop, not along a straight row,
   - the task treats loops as equivalent only up to cyclic rotation; flipping the loop is not allowed,
   - the answer is the number of valid option loops as an integer.
6. Generation guarantees:
   - option count defaults to `6..7`,
   - valid option count defaults to `1..5`,
   - bead count defaults to `5..7` (`shape_cycle_count` caps at `6` because the shape pool has six distinct symbols),
   - all valid options preserve the same cyclic order as the reference loop up to rotation,
   - all invalid options break that cyclic order by construction.

## 3) Prompt contract
1. Bundle: `puzzles_topology_v1`
2. `task_family_key`: `topology_bead_equivalence_puzzle`
3. `task_key`: `bead_equivalence_count_query`
4. `task_variant_key`: `color_cycle_count|shape_cycle_count|mixed_cycle_count`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/puzzles/topology.yaml`,
   - deterministic bundle selection from `prompts/puzzles/topology/puzzles_topology_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the valid-option count; prompt-facing evidence is the ordered set of valid option-image bboxes in reading order.

## 4) Evidence + trace contract
1. Prompt-facing evidence is one `bbox_set` item per valid option image, ordered left to right and then top to bottom.
2. `projected_evidence` includes:
   - `bbox_set`
3. `scene_ir.entities` stores:
   - `puzzle_topology_reference_panel`
   - `puzzle_topology_reference_label`
   - `puzzle_topology_reference_loop`
   - `puzzle_topology_reference_bead`
   - `puzzle_topology_option_choice`
   - `puzzle_topology_option_label`
   - `puzzle_topology_option_loop`
   - `puzzle_topology_option_bead`
4. `render_map` includes:
   - `scene_bbox_px`
   - `reference_loop_bbox_px`
   - `option_choice_bboxes_px`
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `question_format`
   - `view_family`
   - `equivalence_rule`
   - `reference_token_sequence`
   - `reference_loop_shape_variant`
   - `reference_start_angle_deg`
   - `option_specs`
   - `option_count`
   - `option_count_range`
   - `valid_option_count`
   - `valid_option_count_range`
   - `bead_count`
   - `bead_count_range`
   - `valid_option_choice_ids`
   - `valid_option_labels`
   - `supporting_option_choice_ids`
   - `solver_trace`
6. Prompt-facing evidence is projected from the ordered `valid_option_choice_ids`.

## 5) Visual policy
1. Background and post-image noise use the merged puzzles-domain visual defaults from `configs/domains/puzzles/base.yaml`.
2. V1 topology scenes use clean light backgrounds and simple loop outlines so the bead order remains the salient signal.
3. Scene variants change outer reference-panel chrome while preserving the same reference-plus-options grammar.
4. Option letters appear below the loop images; the answer is still an integer count, not an option letter.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same generated reference/option set.
4. No semantic auto-relaxation.
5. Review overlays rely on the recorded option-image projections, not OCR or re-derived loop matching from pixels.
