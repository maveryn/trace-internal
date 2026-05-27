# Games Task Setup

Use this document for the active `games` domain contract.

For cross-domain coverage rollups, use `docs/project/STATUS.md` and `docs/domains/SCENE_TASK_QUERY_GUIDE.md` instead of repeating those inventories here.

## 1) Domain scope
1. `games` stays state-first: the image depicts a recognizable game artifact whose visible pieces are enough to solve the query.
2. Prefer fully observable questions with explicit rules over hidden-information or convention-heavy strategy.
3. Prompt-facing evidence stays on visible witness pieces or board cells, not decorative table chrome.

## 2) Task unit rule
1. Public taxonomy is `domain=games -> scene_id -> task_id`.
2. A `scene_id` is the shared game renderer/grammar, such as `cards` or `connect_four`.
3. A task is separate when it requires a distinct reasoning algorithm or evidence contract, even if it uses the same scene renderer.
4. Mirror or parameter knobs inside one reasoning contract stay as query params, such as player color, row/column axis, board size, or threshold direction.
5. Default and targeted generation should use the active task ids below.

## 2.1 Repeated-unit visual requirement
1. Game scenes built from repeated board cells, grid squares, hexes, lanes, slots, wells, dots, or voxel/block units should include non-semantic unit-size jitter. Try for at least a `2x` min-to-max span (`max_unit_size / min_unit_size >= 2.0`) first, but use a narrower documented range when readability, scene fit, or evidence integrity requires it.
2. This requirement applies to board/grid scenes such as chess, checkers, Go, Hex, Battleship, Minesweeper, Sudoku, Connect Four, Dots and Boxes, Snake, 2048, Reversi, Pac-Man, Bubble Shooter, Brick Breaker, Minecraft-like block worlds, and similar repeated-unit renderers.
3. Logical board-size variation alone does not satisfy the requirement; the rendered unit size should vary independently when feasible.
4. Record the sampled unit size or scale in render metadata and compute evidence bboxes/points from the final jittered layout. Document any exception where a canonical board, readability constraint, or verifier contract requires a narrower range.
5. Broad style primitives may live in domain-level config/helpers, but concrete rendering variation is applied scene by scene. Each game scene owns how palettes, strokes, board chrome, piece styling, unit-size jitter, and layout slack map onto its visible rules and evidence.
6. Do not use a blind domain-level recolor/layout pass for game scenes; visual variation must preserve piece/cell readability and must not change the answer, evidence, or rule semantics.

## 3) Active scenes and tasks
Review artifacts for these tasks use `plans/task-reviews/games/<scene_id>/<task_id>/`.

### `2048`
- Visual grammar: 4 x 4 2048 board with numbered tiles and either one shown move arrow or four labeled candidate arrows.
- Visual styles use the shared game panel treatment/palette layer for canvas and board chrome, while tile values keep classic, dark, paper, neon, and pastel 2048 tile palettes for readability.
- Reasoning coverage: one-move merge counting, one-move score computation, post-move maximum-tile value, and goal-cell best-move selection.
- Active default tasks:
  - `task_games__2048__move_result_value`
  - `task_games__2048__best_move_label`

### `backgammon`
- Visual grammar: numbered Backgammon board with black and white checker stacks and two dice.
- Visual styles use the shared game panel treatment/palette layer for canvas and surrounding chrome, while the Backgammon board itself keeps classic, navy, parchment, slate, and tournament palettes for point/checker readability.
- Reasoning coverage: distinct single-die destination counting for legal moves, hit moves, and blocked destination candidates.
- Active default tasks:
  - `task_games__backgammon__destination_count`

### `bingo`
- Visual grammar: 5 x 5 bingo card.
- Visual styles use the shared game panel treatment/palette layer for canvas and card chrome, while Bingo card palettes, mark shapes, and cell-fill patterns remain scene-local for number and mark readability.
- Reasoning coverage: completed-line counting and summing printed numbers across completed lines.
- Active default tasks:
  - `task_games__bingo__completed_line_count`
  - `task_games__bingo__line_sum_extremum_value`

### `bowling`
- Visual grammar: bowling lane with a ball, labeled pins, and optional labeled aiming paths.
- Visual styles use the shared game panel treatment/palette layer for canvas and lane chrome, while the lane, ball, pin, and path palettes remain scene-local for motion and label readability.
- Reasoning coverage: first-pin hit labeling by extrapolating a verified first-collision ball trajectory with non-target clearance, and spare-path labeling by comparing shorter visible path cues through the remaining pins.
- Active default tasks:
  - `task_games__bowling__first_pin_hit_label`
  - `task_games__bowling__spare_path_label`

### `brick_breaker`
- Visual grammar: brick-breaker playfield with labeled top bricks, a short visible dashed motion cue, a neutral paddle marker, and labeled bottom catch lanes.
- Visual styles include classic, neon, paper, blueprint, and arcade palettes.
- Reasoning coverage: trajectory-target labeling by extrapolating straight ball motion, plus same-row counting after the hit brick is removed.
- Active default tasks:
  - `task_games__brick_breaker__trajectory_target_label`
  - `task_games__brick_breaker__hit_row_remaining_count`

### `bubble_shooter`
- Visual grammar: close-packed bubble-shooter board with colored bubbles, a dashed landing target, and optional labeled next-color choices.
- Visual styles include classic, pastel, neon, paper, and arcade boards.
- Reasoning coverage: same-color pop counts, post-pop drop counts, and fixed-landing color-option selection.
- Active default tasks:
  - `task_games__bubble_shooter__shot_effect_count`
  - `task_games__bubble_shooter__pop_color_label`

### `cards`
- Visual grammar: visible playing-card hands, rows, and small labeled card-game comparison layouts.
- Reasoning coverage: suit match, rank comparison, multiplicity, ordered run reasoning, blackjack comparison, poker comparison, and trick-taking winner rules.
- Active default tasks:
  - `task_games__cards__reference_condition_count`
  - `task_games__cards__exact_triple_count`
  - `task_games__cards__longest_run_length`
  - `task_games__cards__blackjack_best_hand_label`
  - `task_games__cards__poker_best_hand_label`
  - `task_games__cards__trick_taking_winner_label`

### `solitaire`
- Visual grammar: solitaire tableau columns with labeled exposed cards, foundation piles, stock/free-cell chrome, and image-drawn move options where needed.
- Reasoning coverage: tableau/foundation move legality, foundation-readiness counting, and adjacent tableau-sequence counting.
- Active default tasks:
  - `task_games__solitaire__move_legality_label`
  - `task_games__solitaire__foundation_ready_count`
  - `task_games__solitaire__tableau_sequence_count`

### `checkers`
- Visual grammar: checkers board with ordinary men; the capture-chain task additionally marks one king checker.
- Visual styles include classic brown boards, inset wood boards, blue table boards, and charcoal high-contrast boards.
- Reasoning coverage: legal landing-square count, capture landing-square count, and longest capture-chain length for a marked king.
- Active default tasks:
  - `task_games__checkers__move_count`
  - `task_games__checkers__max_capture_chain_length`

### `chess`
- Visual grammar: partial standard chess board with white and black pieces.
- Visual styles include flat token boards, inset wood boards, blue tournament-style glyph boards, and monochrome glyph boards.
- Reasoning coverage: marked-piece movement, marked-piece capture, side-wide capture opportunity, marked-king attack counting, and marked-king escape-square counting.
- Active default tasks:
  - `task_games__chess__marked_piece_destination_count`
  - `task_games__chess__player_capture_piece_count`
  - `task_games__chess__check_attacker_count`
  - `task_games__chess__king_escape_square_count`

### `chess_variant`
- Visual grammar: chess-like 8 by 8 board with W/B tokens, one blue-outlined marked token, and a visible rule-card badge.
- Visual styles use token-only chess board palettes to avoid standard chess-glyph assumptions.
- Reasoning coverage: marked-token destination counting and marked-token capture counting under visible nonstandard movement rules.
- Active default tasks:
  - `task_games__chess_variant__marked_piece_destination_count`

### `connect_four`
- Visual grammar: Connect Four board with gravity.
- Visual styles include classic blue boards, high-contrast arcade boards, teal-framed boards, and charcoal boards with varied well/disc treatments.
- Reasoning coverage: immediate winning drops and safe drops.
- Active default tasks:
  - `task_games__connect_four__move_count`

### `crossing`
- Visual grammar: lane-crossing motion board with horizontal traffic rows, direction arrows, start pads, optional route lines, and a goal band.
- Visual styles include day, night, retro, paper, and construction palettes.
- Reasoning coverage: safe route selection over straight starts or labeled route options, first collision tick on a marked route, and moving-object intersections with a marked route.
- Active default tasks:
  - `task_games__crossing__safe_route_label`
  - `task_games__crossing__collision_time_value`
  - `task_games__crossing__moving_object_count`

### `darts`
- Visual grammar: simplified labeled dartboard with dart markers, extra-wide double/triple/bull scoring bands, large sector numbers, image-drawn score options for total-score queries, and lower dart density for count queries.
- Reasoning coverage: score readout, ring membership count, and threshold score count.
- Active default tasks:
  - `task_games__darts__total_score_option_label`
  - `task_games__darts__condition_count`

### `dominoes`
- Visual grammar: domino chain plus loose candidate tiles.
- Visual styles include classic white tiles, ivory tiles, charcoal tiles, and wood-toned tiles.
- Reasoning coverage: open-end match, reference pip-sum comparison, target pip sum, double detection, and two-step chain extension.
- Active default tasks:
  - `task_games__dominoes__property_count`
  - `task_games__dominoes__two_step_extension_label`

### `dots_and_boxes`
- Visual grammar: dots-and-boxes board state.
- Visual styles include classic panels, notebook-paper boards, slate boards, and wood-toned boards.
- Reasoning coverage: three-sided box count and capture move count; the capture task includes both all-missing-edge and highlighted-candidate query ids.
- Active default tasks:
  - `task_games__dots_and_boxes__three_sided_box_count`
  - `task_games__dots_and_boxes__capture_move_count`

### `go`
- Visual grammar: Go board with one marked group.
- Visual styles include classic wood boards, slate boards, paper boards, and outlined boards.
- Reasoning coverage: liberty, adjacent enemy, and shared-liberty counts.
- Active default tasks:
  - `task_games__go__group_liberty_count`
  - `task_games__go__group_adjacent_enemy_count`

### `hex`
- Visual grammar: Hex board with red and blue stones, colored goal sides, and optional labeled empty candidate cells.
- Visual styles include classic, soft, outlined, slate, and paper boards.
- Reasoning coverage: immediate winning-cell selection and minimum empty-cell connection gap counting.
- Active default tasks:
  - `task_games__hex__winning_move_cell_label`
  - `task_games__hex__connection_gap_count`

### `marble_chain`
- Visual grammar: Zuma-like colored marble chain on a gray curved or spiral track with a central shooter, shooter marble, and labeled or marked shot arrows.
- Visual styles use the shared game panel treatment/palette layer, with semicircle, spiral, and double-arc track layouts.
- Reasoning coverage: shot-direction selection by pop effect, plus numeric pop-count queries after a marked shot.
- Active default tasks:
  - `task_games__marble_chain__shot_direction_label`
  - `task_games__marble_chain__shot_effect_value`

### `match3`
- Visual grammar: match-3 jewel grid with row and column numbers, colored gem cells, and marked or labeled adjacent-swap arrows.
- Visual styles use the shared game panel treatment/palette layer. The game rule is one adjacent swap followed by immediate run clearing only; no gravity, refill, special effects, or cascades.
- Reasoning coverage: numeric clear/run counts after a marked swap, plus labeled swap selection by maximum or target immediate clear count.
- Active default tasks:
  - `task_games__match3__swap_effect_value`
  - `task_games__match3__best_swap_label`

### `tetris`
- Visual grammar: variable-size Tetris boards with `7..11` columns and `10..15` rows, colored locked blocks, a NEXT piece preview for placement optimization, a START board with a falling piece at its shown column, and full-size labeled result boards.
- Visual styles use the shared game panel treatment/palette layer. The game rule is one hard drop followed by lock, row clear, and gravity; no cascades or new pieces are introduced.
- Reasoning coverage: maximum possible line-clear counting for a next piece with translation/rotation allowed, plus resulting-board selection for a fixed falling piece with no translation or rotation.
- Active default tasks:
  - `task_games__tetris__line_clear_count`
  - `task_games__tetris__drop_result_label`

### `ultimate_tictactoe`
- Visual grammar: Ultimate Tic-Tac-Toe board with nine small Tic-Tac-Toe boards, local X/O marks, local win lines, drawn boards, and optional highlighted local-board answer options.
- Visual styles use the shared game panel treatment/palette layer.
- Reasoning coverage: macro status counting across small boards and local winning/blocking move selection inside one highlighted small board.
- Active default tasks:
  - `task_games__ultimate_tictactoe__small_board_status_count`
  - `task_games__ultimate_tictactoe__local_tactic_label`

### `minesweeper`
- Visual grammar: opened Minesweeper number grid with hidden cells and optional flags.
- Visual styles include classic grids, notebook grids, dark grids, retro grids, and outlined grids.
- Reasoning coverage: local forced-mine counting, local forced-safe counting, and satisfied-clue counting.
- Calibrated board size support is `4..8` for the scene overall; the forced-cell
  task uses `4..5` and outlines the relevant opened clue cell(s) to keep local
  deduction legible.
- Active default tasks:
  - `task_games__minesweeper__forced_cell_count`
  - `task_games__minesweeper__satisfied_clue_count`

### `minigolf`
- Visual grammar: Mini-golf putting course with a ball, a hole, obstacles, and short starting-direction shot cues.
- Visual styles include classic, desert, neon, garden, and blueprint course palettes.
- Reasoning coverage: extrapolating a short cue to its first obstacle and choosing the numbered cue whose banked path reaches the hole.
- Active default tasks:
  - `task_games__minigolf__first_obstacle_label`
  - `task_games__minigolf__shot_path_label`

### `minecraft`
- Visual grammar: Minecraft-like isometric block world with cube terrain, ore blocks, marked paths, and labeled mining routes.
- Visual styles include grass, desert, snow, cave, and mesa palettes.
- Reasoning coverage: ore-type counting, marked tunnel clearance counts, and named-route block-cost counting.
- Active default tasks:
  - `task_games__minecraft__ore_block_count`
  - `task_games__minecraft__tunnel_clearance_count`
  - `task_games__minecraft__resource_route_cost_value`

### `battleship`
- Visual grammar: Battleship board with the full fleet placed on the grid, red hit markers on ship cells, miss markers on water, and a side fleet-shape panel.
- Visual styles use the shared game panel treatment/palette layer for canvas and surrounding chrome, while the Battleship grid and fleet panel keep classic blue, soft, outlined, navy, radar, and paper palettes for ship/hit readability.
- Reasoning coverage: counting fleet ships whose every cell has been hit, and counting damaged ships that are hit but not sunk.
- Active default tasks:
  - `task_games__battleship__ship_status_count`

### `nine_mens_morris`
- Visual grammar: Nine Men's Morris board.
- Visual styles include classic panels, wood panels, slate panels, parchment panels, and outlined boards.
- Reasoning coverage: all-piece mill membership counts.
- Active default tasks:
  - `task_games__nine_mens_morris__pieces_in_mill_count`

### `pacman`
- Visual grammar: Pac-Man style maze with a visible Pac-Man marker, ghosts, normal pellets, labeled bonus items, and a highlighted route.
- Visual styles include classic, neon, paper, terminal, and pastel palettes.
- Reasoning coverage: route pellet counting, route counting before the first ghost, and first labeled item reached along a route.
- Active default tasks:
  - `task_games__pacman__route_pellet_count`
  - `task_games__pacman__next_item_label`

### `platformer`
- Visual grammar: side-scroller platformer level with a player character, platforms, hazards, coins, and dashed jump arcs.
- Visual styles include day, cave, neon, snow, and sunset palettes.
- Reasoning coverage: extrapolating a short jump arc to a landing platform and counting coins along a shown jump arc.
- Active default tasks:
  - `task_games__platformer__jump_landing_label`
  - `task_games__platformer__collectible_count`

### `pool`
- Visual grammar: pool table with cue ball, numbered object balls, six pockets, and optional marked shot indicators.
- Visual styles include classic green cloth, tournament-blue cloth, burgundy cloth, charcoal cloth, and light-rail tables.
- Reasoning coverage: no-bank direct-shot pottability, current-player group filtering, and blockers on a marked shot lane.
- Active default tasks:
  - `task_games__pool__pottable_ball_count`
  - `task_games__pool__blocking_ball_count`

### `reversi`
- Visual grammar: Reversi board state.
- Visual styles include classic green boards, wood-framed boards, slate boards, blue boards, and outlined boards.
- Reasoning coverage: legal moves, corner moves, and marked-move flip counts.
- Active default tasks:
  - `task_games__reversi__legal_destination_count`
  - `task_games__reversi__marked_move_flip_count`

### `rhythm`
- Visual grammar: rhythm-game falling-note lanes with lane numbers and a bottom hit line.
- Visual styles include arcade, neon, paper, dark, and pastel palettes.
- Reasoning coverage: timing-window note counting, color-filtered timing-window counting, most-arriving lane selection, and earliest-arriving lane selection.
- Active default tasks:
  - `task_games__rhythm__hit_window_count`
  - `task_games__rhythm__lane_choice_value`

### `snake`
- Visual grammar: Snake game board with a yellow head, connected body cells, red food, gray wall cells, and a square grid.
- Visual styles include classic, neon, forest, paper, and candy palettes.
- Reasoning coverage: safe-direction counting with wall cells as unsafe blockers, plus planned 3 to 5 move simulation against image-visible point or `GAME OVER` options. Option-letter answers are only used where the option labels are drawn in the image.
- Active default tasks:
  - `task_games__snake__safe_direction_count`
  - `task_games__snake__path_outcome_option_label`

### `space_shooter`
- Visual grammar: retro space-shooter playfield with vertical lane guides, labeled enemy ships, falling enemy shots, shields or asteroids, a player ship, and bottom lane pads.
- Visual styles include neon, deep-space, vector, amber, and terminal palettes.
- Generation currently samples `4..8` lanes and `10..16` enemy ships for the denser queries, with count answers in `1..5`. The clear-shot query uses one foreground enemy per lane plus blockers to keep the obstruction judgment readable; the safe-lane query uses a sparse upper enemy backdrop so the bottom-pad shot/asteroid state stays visually primary.
- Reasoning coverage: unobstructed enemy lanes, projectile alignment with the player, lowest-enemy threat labeling, and safe bottom-lane counting.
- Active default tasks:
  - `task_games__space_shooter__clear_shot_count`
  - `task_games__space_shooter__projectile_intercept_count`
  - `task_games__space_shooter__highest_threat_label`
  - `task_games__space_shooter__safe_lane_count`

### `snakes_ladders`
- Visual grammar: 10 x 10 numbered serpentine Snakes and Ladders board with one token, visible snakes, visible ladders, and a side panel for die or planning information.
- Visual styles include classic, paper, neon, pastel, and wood board palettes.
- Reasoning coverage: one-die final-square simulation and short-horizon highest-final-square planning over `1..3` chosen die rolls.
- Active default tasks:
  - `task_games__snakes_ladders__move_outcome_value`
  - `task_games__snakes_ladders__best_roll_value`

### `sudoku`
- Visual grammar: partially filled Sudoku grid with optional marked cell or highlighted unit.
- Visual styles include classic grids, notebook grids, slate grids, warm-paper grids, and outlined grids.
- Reasoning coverage: single-cell digit placement, candidate-count reasoning for a marked cell, missing-digit counting in a row/column/box, and repeated-digit counting in a row/column/box.
- Active default tasks:
  - `task_games__sudoku__marked_cell_value`
  - `task_games__sudoku__marked_cell_candidate_count`
  - `task_games__sudoku__unit_missing_digits_count`
  - `task_games__sudoku__repeated_digit_count`

## 4) Shared helper placement
1. Cross-domain integer-support balancing lives in `trace/tasks/shared/support_sampling.py`.
2. Games visual defaults, style/theme handling, axis sampling, and normalized complexity helpers belong under `trace/tasks/games/shared/visual_defaults.py`, `trace/tasks/games/shared/style.py`, `trace/tasks/games/shared/sampling.py`, and `trace/tasks/games/shared/complexity.py`.
3. Shared nonsemantic renderer placement helpers belong in `trace/tasks/games/shared/layout.py`.
4. The game fixed-query wrapper adapter lives in `trace/tasks/games/shared/fixed_query_task.py` and should delegate public-query metadata rewriting to `trace/tasks/shared/fixed_query.py`; use it only when one shared scene renderer exposes multiple distinct public tasks.
5. Game-specific rules/data helpers belong under the narrow reusable `trace/tasks/games/shared/*_common.py` module for that game when one exists.
6. Game-specific renderers belong under the corresponding `trace/tasks/games/shared/*_scene.py` module.
