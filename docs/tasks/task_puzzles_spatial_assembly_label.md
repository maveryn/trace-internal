# `task_puzzles_spatial_assembly_label`

## 1) Identity
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles_spatial_assembly_label`
4. Objective: choose the labeled silhouette that can be built from the shown pieces.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `can_be_built`
2. Supported `scene_variant` values:
   - `assembly_strip`
   - `assembly_card`
   - `assembly_outline`
3. `answer_gt.type`: `option_letter`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one assembly puzzle per image,
   - `2..4` polyomino pieces appear above the options,
   - `5..6` labeled silhouette options appear below the pieces,
   - each option uses the same total area as the shown pieces,
   - the prompt states that all pieces must be used exactly once,
   - the prompt states that pieces may be rotated but not flipped,
   - the answer is the letter of the one option that can be built.
6. Generation guarantees:
   - piece totals default to `8..11` occupied unit cells,
   - the hidden target silhouette fits within a `5 x 5` cell box by default,
   - the accepted correct option is verified exactly by a rotation-only tiling solver,
   - every distractor has the same total area but is rejected if it is tileable by the shown pieces,
   - exactly one option is buildable in every accepted scene.

## 3) Prompt contract
1. Bundle: `puzzles_spatial_v1`
2. `task_family_key`: `spatial_assembly_puzzle`
3. `task_key`: `assembly_label_query`
4. `task_variant_key`: `can_be_built`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/puzzles/spatial.yaml`,
   - deterministic bundle selection from `prompts/puzzles/spatial/puzzles_spatial_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the option letter; prompt-facing evidence is the winning option-panel bbox.

## 4) Evidence + trace contract
1. Prompt-facing evidence is exactly one `bbox_set` item:
   - the correct option panel bbox.
2. `projected_evidence` includes:
   - `bbox_set`
3. `scene_ir.entities` stores:
   - `puzzle_assembly_piece_card`
   - `puzzle_assembly_piece_cell`
   - `puzzle_assembly_option_panel`
   - `puzzle_assembly_option_label`
   - `puzzle_assembly_option_shape_box`
   - `puzzle_assembly_option_shape_cell`
4. `render_map` includes:
   - `scene_bbox_px`
   - `piece_card_bboxes_px`
   - `option_panel_bboxes_px`
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `question_format`
   - `view_family`
   - `piece_specs`
   - `piece_count`
   - `piece_count_range`
   - `option_specs`
   - `option_count`
   - `option_count_range`
   - `target_cells`
   - `target_bbox_dims`
   - `target_cell_count`
   - `target_cell_count_range`
   - `answer_option_label`
   - `correct_option_index`
   - `correct_option_panel_id`
   - `supporting_option_panel_ids`
   - `solver_trace`
6. Prompt-facing evidence is projected from `correct_option_panel_id`, not from inferred assembly overlays.

## 5) Visual policy
1. Background and post-image noise use the merged puzzles-domain visual defaults from `configs/domains/puzzles/base.yaml`.
2. V1 assembly scenes keep the pieces and options on the same unit-square drawing grammar so the task is about assembly, not style mismatch.
3. Scene variants only change outer panel chrome and outline treatment while preserving the same top-pieces / bottom-options layout.
4. The reference pieces and the options use the same neutral shape fill and the same polyomino cell style so the task reads as one consistent assembly grammar.
5. Every assembly image uses one shared polyomino cell size across both the top pieces and the option silhouettes; the top pieces are centered with extra whitespace instead of being scaled up to fill their cards.
6. Prompt-facing evidence should align to the winning option panel, not to the individual source pieces.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same exact tiling check.
4. No semantic auto-relaxation.
5. Review overlays rely on the recorded winning option-panel projection, not OCR or perceptual shape matching from pixels.
