# `task_puzzles_logic_adjacency_completion_label`

## 1) Identity
1. Domain: `puzzles`
2. Task group: `logic`
3. Task id: `task_puzzles_logic_adjacency_completion_label`
4. Objective: choose the labeled option that correctly fills the missing grid cell while obeying an explicit non-touch rule.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `king_non_touch`
2. Supported `scene_variant` values:
   - `logic_strip`
   - `logic_card`
   - `logic_outline`
3. `answer_gt.type`: `option_letter`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one square logic grid per image,
   - board size ranges from `3x3` through `5x5`,
   - exactly one board cell shows `?`,
   - exactly six labeled image options (`A..F`) appear below the board,
   - each option panel contains one candidate shape,
   - the prompt explicitly states that identical symbols may not touch edge-to-edge or corner-to-corner,
   - the answer is the option letter, not the shape name.
6. Generation guarantees:
   - the query cell always has neighboring cells that already show the five non-answer shapes,
   - exactly one option remains valid under the stated no-touch rule in every accepted scene.

## 3) Prompt contract
1. Bundle: `puzzles_logic_v1`
2. `task_family_key`: `logic_option_completion_puzzle`
3. `task_key`: `adjacency_completion_query`
4. `task_variant_key`: `king_non_touch`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt-facing answer is the option letter; prompt-facing evidence is the winning option-panel bbox.

## 4) Evidence + trace contract
1. Prompt-facing evidence is exactly one `bbox_set` item:
   - the correct option-panel bbox.
2. `projected_evidence` includes:
   - `bbox_set`
3. `scene_ir.entities` stores:
   - `puzzle_logic_cell`
   - `puzzle_logic_option_panel`
   - `puzzle_logic_option_label`
   - `puzzle_logic_option_symbol_box`
4. `render_map` includes:
   - `scene_bbox_px`
   - `cell_bboxes_px`
   - `option_panel_bboxes_px`
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `query_cell_id`
   - `query_row_index`
   - `query_col_index`
   - `board_values`
   - `grid_rows`
   - `symbol_pool`
   - `neighbor_coords`
   - `forced_neighbor_coords`
   - `forced_neighbor_types`
   - `query_neighbor_object_types`
   - `valid_option_object_types`
   - `answer_object_type`
   - `answer_option_label`
   - `correct_option_index`
   - `correct_option_panel_id`
   - `option_specs`
   - `board_size`
   - `board_size_range`
   - `cell_count`
   - `cell_count_range`
   - `option_count`
   - `solver_trace`
6. Prompt-facing evidence is projected from `correct_option_panel_id`, not inferred from the board cell itself.

## 5) Visual policy
1. The task reuses the active logic board-plus-options renderer so the interaction grammar stays consistent across logic tasks.
2. The board and all six options share the same shape vocabulary.
3. Scene variants only change outer chrome while preserving the same board-plus-options interaction pattern.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. The active rule is explicit in the prompt rather than hidden.
4. No semantic auto-relaxation.
