# Games Task-Unit Audit

Task-unit audit for `domain=games` using `docs/workflows/TASK_UNIT_AUDIT.md`.

## Domain summary
1. The games domain is mostly healthy as a task-unit inventory.
2. Most current games tasks are good state-first grounding units with clearly distinct visible game scaffolds.
3. The main task-unit pressure points are:
   - `task_games_cards_hand_count`, which mixes unordered hand-property counting with ordered run reasoning,
   - `task_games_reversi_move_count`, which mixes legal-destination counting with marked-move flip-consequence reasoning.
4. Recommended domain outcome:
   - `Keep`: `8`
   - `Split`: `2`
   - `Merge`: `0`
   - `Retire`: `0`

## Task findings

### `task_games_bingo_completed_line_count`
- Outcome: `Keep`
- Why: one coherent bingo-card counting family with stable witness semantics over completed marked lines.
- Scene variety: moderate; one `5 x 5` bingo-card scaffold with style variation and varying mark patterns.
- Query variety: moderate (`completed_row_count|completed_column_count|completed_straight_line_count`)
- Grounding necessity: strong; the model must read the marked-cell pattern on the visible card.
- Evidence fit: good; marked cells on counted lines are the natural witness.
- Follow-up: none required now.

### `task_games_cards_hand_count`
- Outcome: `Split`
- Why: this task currently mixes two different hand-grounding families:
  - unordered card-property counting (`same_suit_as_reference_count|higher_than_reference_count|pair_count`)
  - ordered display-sequence reasoning (`longest_run_length`)
- Scene variety: high, but mixed rather than uniformly broad.
- Query variety: high, but split across incompatible grounding jobs.
- Grounding necessity: strong in both halves, but the visual grounding pattern differs:
  - unordered matching/counting over cards,
  - ordered run reading with continuation cues and explicit display order.
- Evidence fit: mixed but valid; both use card boxes, yet the ordered-run witness has different semantics from the unordered card subsets.
- Follow-up:
  1. Keep the unordered card-property variants together as one task.
  2. Move `longest_run_length` into a separate ordered-card-sequence task, especially if future card-order variants are added.

### `task_games_checkers_move_count`
- Outcome: `Keep`
- Why: one coherent checkers move-generation family over visible ordinary-men board states.
- Scene variety: moderate (`midgame_board|crowded_board`)
- Query variety: modest but sufficient (`legal_move_count|capture_move_count`)
- Grounding necessity: strong; the model must reason over visible piece placement and landing squares.
- Evidence fit: good; landing-square `bbox_set` is stable across both variants.
- Follow-up: none required now.

### `task_games_connect_four_move_count`
- Outcome: `Keep`
- Why: one coherent landing-square move-quality family over visible Connect Four states.
- Scene variety: moderate (`midgame_board|crowded_board`)
- Query variety: moderate (`winning_move_count|safe_move_count`)
- Grounding necessity: strong; requires board-state reading plus next-move consequence reasoning.
- Evidence fit: good; landing-square `bbox_set` stays stable across both variants.
- Follow-up: none required now.

### `task_games_dominoes_chain_count`
- Outcome: `Keep`
- Why: one coherent loose-domino qualification family grounded on a visible top chain plus candidate tiles below.
- Scene variety: moderate (`single_row|two_row`) with stable top-chain + candidate layout.
- Query variety: strong (`matching_end_count|higher_sum_than_reference_count|sum_to_target_count|double_count`)
- Grounding necessity: strong; the model must read pips and connect the loose tiles to the visible chain or target rule.
- Evidence fit: good; qualifying loose domino boxes remain a natural witness across variants.
- Follow-up: none required now.

### `task_games_dots_and_boxes_capture_count`
- Outcome: `Keep`
- Why: one coherent forced-turn capture family over a visible dots-and-boxes board.
- Scene variety: narrower than some games tasks, but still a legitimate single grounding unit because the forced-turn capture scaffold is specific and distinctive.
- Query variety: currently narrow (`forced_turn_capture_count` only), but still within one stable grounding family.
- Grounding necessity: strong; requires following the highlighted edge and visible forced captures on the board.
- Evidence fit: good; captured boxes are the right local witness.
- Follow-up: broaden later within the same family if more forced-turn variants are added, but do not split now.

### `task_games_go_group_liberty_count`
- Outcome: `Keep`
- Why: one coherent Go group-liberty family with a stable witness contract on empty intersections.
- Scene variety: moderate (`open_board|crowded_board`)
- Query variety: modest but sufficient (`marked_black_group_liberty_count|marked_white_group_liberty_count`)
- Grounding necessity: strong; requires local group identification plus liberty counting.
- Evidence fit: good; liberty intersections are the natural counted witness.
- Follow-up: none required now.

### `task_games_mancala_move_count`
- Outcome: `Keep`
- Why: one coherent starting-pit qualification family on a visible Mancala board.
- Scene variety: moderate (`midgame_board|crowded_board`)
- Query variety: moderate (`extra_turn_move_count|capture_move_count`)
- Grounding necessity: strong; requires visible pit counts and local sowing-rule consequences.
- Evidence fit: good; starting-pit `bbox_set` stays stable across both variants.
- Follow-up: none required now.

### `task_games_nine_mens_morris_pieces_in_mill_count`
- Outcome: `Keep`
- Why: one coherent counted-piece-in-mill family on a visible Morris board.
- Scene variety: moderate; fixed board scaffold with varied piece placement and overlapping-mill structure.
- Query variety: modest but sufficient (`white_pieces_in_mill_count|black_pieces_in_mill_count|all_pieces_in_mill_count`)
- Grounding necessity: strong; requires reading the board lines and which pieces belong to one or more mills.
- Evidence fit: good; counted piece boxes are the natural witness.
- Follow-up: none required now.

### `task_games_reversi_move_count`
- Outcome: `Split`
- Why: this task mixes two different move-grounding families:
  - legal-destination counting (`legal_move_count|corner_move_count`)
  - marked-move flip consequence reasoning (`flip_count_for_marked_move`)
- Scene variety: high, but mixed rather than uniformly broad.
- Query variety: moderate, but split across different witness semantics.
- Grounding necessity: strong in both halves, but the operative witness differs:
  - legal move squares for the count variants,
  - flipped discs for the marked-move variant.
- Evidence fit: mixed; the task currently switches from destination-square evidence to flipped-disc evidence inside one task id.
- Follow-up:
  1. Keep `legal_move_count` and `corner_move_count` together as a legal-destination task.
  2. Move `flip_count_for_marked_move` into a separate marked-move consequence task.

## Recommended next action
1. Leave the other games tasks unchanged for now.
2. Treat `task_games_cards_hand_count` and `task_games_reversi_move_count` as the first concrete split candidates when doing benchmark-unit rebalancing.
3. Keep future strategic/optimal-play game tasks as new task units rather than folding them into the current mostly state-first task ids.
