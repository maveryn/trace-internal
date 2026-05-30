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
7. Each game scene should aim for at least five scene-local board/object style variants, separate from shared canvas backgrounds, panel treatments, font families, and post-image noise. These variants should affect the game artifact itself, such as board skins, tile palettes, piece/token treatments, grid/line strokes, card/table chrome, lane skins, or HUD/control styling.
8. If fewer than five scene-local styles are safe because the artifact has a canonical visual identity or tight readability constraints, document the exception in this file and record the active style axis in render metadata.
9. Any answer-bearing path, marker, or option color drawn over known panel/board/lane backgrounds must pass through the shared Lab-distance contrast guard (`resolve_contrasting_palette(...)`) with panel anchors from `game_panel_contrast_anchor_colors(...)`, or an equivalent documented scene-specific guard. Do not rely on hand-picked RGB palettes alone.
10. Board-inside-canvas scenes should use shared slack-based layout jitter by default. The sampled offset should be a fraction of the available safe slack after content size is resolved, not a small fixed pixel offset, and the final `layout_jitter` metadata must record the requested fraction, realized pixel offset, clamp range, and any unit-size jitter.

## 3) Active scenes and tasks
Review artifacts for these tasks use `review/task-reviews/games/<scene_id>/<task_id>/`.

### `2048`
- Visual grammar: 4 x 4 2048 board with numbered tiles and either one shown move arrow or four labeled candidate arrows.
- Visual styles use the shared game panel treatment/palette layer for canvas and board chrome, while tile values keep classic, dark, paper, neon, and pastel 2048 tile palettes for readability.
- The canvas follows the resolved board size so small unit-size samples do not float in an oversized fixed frame; arrow and label padding remain non-semantic and recorded in render metadata.
- Tile-number and option-badge text samples a deterministic font family from the readout font pool.
- Reasoning coverage: one-move merge counting, one-move score computation, post-move maximum-tile value, and goal-cell best-move selection.
- Active default tasks:
  - `task_games__2048__move_result_value`
  - `task_games__2048__best_move_label`

### `backgammon`
- Visual grammar: numbered Backgammon board with black and white checker stacks and two dice.
- Visual styles use the shared game panel treatment/palette layer for canvas and surrounding chrome, while the Backgammon board itself keeps classic, navy, parchment, slate, and tournament palettes for point/checker readability.
- Board size, checker size, dice size, labels, and canvas dimensions vary together; point evidence is projected from the final jittered board geometry.
- Point labels, stack-count text, and the rule header sample one deterministic font family from the readout font pool.
- Reasoning coverage: distinct single-die destination counting for legal moves, hit moves, and blocked destination candidates, with active-player sampling covering black moving 24 to 1 and white moving 1 to 24.
- Active default tasks:
  - `task_games__backgammon__destination_count`

### `bingo`
- Visual grammar: 5 x 5 bingo card.
- Visual styles use the shared game panel treatment/palette layer for canvas and card chrome, while Bingo card palettes, mark shapes, and cell-fill patterns remain scene-local for number and mark readability.
- Card size, cell size, marker geometry, labels, and canvas dimensions vary together; cell evidence is projected from the final jittered card geometry.
- The title, column headers, and cell numbers sample one deterministic font family from the readout font pool.
- Reasoning coverage: completed-line counting and summing printed numbers across completed lines.
- Active default tasks:
  - `task_games__bingo__completed_line_count`
  - `task_games__bingo__line_sum_extremum_value`

### `bowling`
- Visual grammar: bowling lane with a ball, labeled pins, and optional labeled aiming paths.
- Visual styles use the shared game panel treatment/palette layer for canvas and lane chrome, while the five lane themes keep ball, pin, and path palettes scene-local for motion and label readability.
- Path colors are resolved against the current panel/lane/label anchor colors using the shared Lab-distance contrast guard so dashed paths and circular path markers cannot blend into the sampled game background.
- Pin and path labels sample one deterministic font family from the readout font pool.
- Reasoning coverage: first-pin hit labeling by extrapolating a verified first-collision ball trajectory with non-target clearance, and spare-path labeling by comparing shorter visible path cues through the remaining pins.
- Evidence uses pin `bbox_set` witnesses for first-hit queries and selected path `point_pair_set` witnesses for spare-path queries.
- Active default tasks:
  - `task_games__bowling__first_pin_hit_label`
  - `task_games__bowling__spare_path_label`

### `brick_breaker`
- Visual grammar: brick-breaker playfield with labeled top bricks, a short visible dashed motion cue, a neutral paddle marker, and labeled bottom catch lanes.
- Visual styles use the shared game panel treatment/palette layer for canvas and playfield chrome, while classic, neon, paper, blueprint, and arcade playfield palettes stay scene-local.
- Brick and lane labels sample one deterministic font family from the readout font pool; the dashed trajectory cue is resolved against panel, playfield, lane, and paddle colors using the shared Lab-distance contrast guard.
- The canvas follows the resolved playfield size so small unit-size samples do not float in an oversized fixed frame.
- Reasoning coverage: trajectory-target labeling by extrapolating straight ball motion, plus same-row counting after the hit brick is removed.
- Active default tasks:
  - `task_games__brick_breaker__trajectory_target_label`
  - `task_games__brick_breaker__hit_row_remaining_count`

### `bubble_shooter`
- Visual grammar: close-packed bubble-shooter board with colored bubbles, a dashed landing target, and optional labeled next-color choices.
- Visual styles use the shared game panel treatment/palette layer for canvas and playfield chrome, while classic, pastel, neon, paper, and arcade bubble-board palettes stay scene-local.
- Option labels sample one deterministic font family from the readout font pool; the aim cue is resolved against panel, playfield, launcher, and option-panel colors using the shared Lab-distance contrast guard.
- The canvas follows the resolved playfield size so small unit-size samples do not float in an oversized fixed frame.
- Public evidence uses object-center `point_set` witnesses for popped/dropped board bubbles; marked landing slots and selected color options remain trace/render metadata rather than prompt-facing evidence.
- Reasoning coverage: same-color pop counts, post-pop drop counts, and fixed-landing color-option selection.
- Active default tasks:
  - `task_games__bubble_shooter__shot_effect_count`
  - `task_games__bubble_shooter__pop_color_label`

### `cards`
- Visual grammar: visible playing-card hands, rows, and small labeled card-game comparison layouts.
- Visual styles use the shared games background layer, while classic, soft, outlined, ivory, and slate card themes vary card faces, borders, shadows, reference banners, and continuation cues.
- Card ranks, hand labels, player badges, and continuation cues sample one deterministic font family from the readout font pool; suit symbols use the renderer fallback font so sampled font families cannot show missing-glyph boxes.
- Card layouts use final-layout jitter before evidence projection; reference cards, winning hands, and run/triple witnesses are grounded by card bboxes computed after jitter.
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
- Visual styles combine shared games-domain panel backgrounds, sampled fonts, layout jitter, post-image noise, and five scene-local card/tableau styles (`classic_cards`, `ivory_table`, `casino_felt`, `slate_cards`, `paper_tableau`).
- Reasoning coverage: tableau/foundation move legality, foundation-readiness counting, and adjacent tableau-sequence counting.
- Evidence uses `keyed_bbox_map` for move legality (`source_card`, `target`) and homogeneous `bbox_set` witnesses for the two count tasks.
- Active default tasks:
  - `task_games__solitaire__move_legality_label`
  - `task_games__solitaire__foundation_ready_count`
  - `task_games__solitaire__tableau_sequence_count`

### `checkers`
- Visual grammar: checkers board with ordinary men; the capture-chain task additionally marks one king checker.
- Visual styles include six board/token themes (`classic`, `soft`, `outlined`, `wood_token`, `blue_table`, `charcoal`) layered over the shared games/puzzles panel scene styles.
- Rendering uses deterministic font-family sampling for player badges plus unit-size and fractional layout jitter; canvas size can shrink around smaller sampled boards while preserving evidence alignment.
- Reasoning coverage: legal landing-square count, capture landing-square count, and longest capture-chain length for a marked king.
- Evidence contracts use homogeneous `bbox_set` witnesses: landing-square boxes for move-count queries and captured-piece boxes for the chain-length query.
- Active default tasks:
  - `task_games__checkers__move_count`
  - `task_games__checkers__max_capture_chain_length`

### `chess`
- Visual grammar: partial standard chess board with white and black pieces.
- Visual styles include six board/piece themes (`classic`, `soft`, `outlined`, `wood_token`, `blue_glyph`, `monochrome_glyph`) layered over the shared games/puzzles panel scene styles.
- Rendering uses deterministic font-family sampling for player/marked-piece badges while chess-piece glyphs use system symbol fallback; unit-size and fractional layout jitter are recorded after final layout, and smaller boards can use a dynamically smaller canvas.
- Reasoning coverage: marked-piece movement, marked-piece capture, side-wide capture opportunity, marked-king attack counting, and marked-king escape-square counting.
- Evidence contracts use homogeneous `bbox_set` witnesses: destination-square boxes for movement/escape queries and piece boxes for capture/attacker queries.
- Active default tasks:
  - `task_games__chess__marked_piece_destination_count`
  - `task_games__chess__player_capture_piece_count`
  - `task_games__chess__check_attacker_count`
  - `task_games__chess__king_escape_square_count`

### `chess_variant`
- Visual grammar: chess-like 8 by 8 board with W/B tokens, one blue-outlined marked token, and a visible rule-card badge.
- Visual styles use six token-only board palettes layered over the shared games/puzzles panel scene styles to avoid standard chess-glyph assumptions.
- Rendering uses sampled fonts for the rule-card badge and W/B token labels, unit-size and fractional layout jitter, and dynamic canvas sizing for smaller sampled boards.
- Reasoning coverage: marked-token destination counting and marked-token capture counting under visible nonstandard movement rules.
- Evidence uses homogeneous `bbox_set` witnesses over qualifying destination cells; capture queries keep evidence on the occupied destination cell rather than the tighter opponent-token box.
- Active default tasks:
  - `task_games__chess_variant__marked_piece_destination_count`

### `connect_four`
- Visual grammar: Connect Four board with gravity.
- Visual styles include six board/disc themes (`classic`, `soft`, `outlined`, `arcade_blue`, `teal_frame`, `charcoal`) layered over the shared games/puzzles panel scene styles.
- Rendering uses deterministic font-family sampling for player badges, unit-size and fractional layout jitter, variable board dimensions, and dynamic canvas sizing for smaller sampled boards.
- Reasoning coverage: immediate winning drops and safe drops.
- Evidence uses homogeneous `bbox_set` witnesses over qualifying landing cells for immediate winning drops or safe drops.
- Active default tasks:
  - `task_games__connect_four__move_count`

### `crossing`
- Visual grammar: lane-crossing motion board with horizontal traffic rows, direction arrows, start pads, one marked route line, and a goal band.
- Visual styles include day, night, retro, paper, and construction lane palettes,
  shared games/puzzles panel-scene treatments, sampled text fonts, and layout
  jitter for the whole playfield.
- Reasoning coverage: first collision tick on a marked route and moving-object
  intersections with a marked route.
- Evidence uses homogeneous `bbox_set` for moving-object count queries. The
  collision-time query uses role-bound `keyed_bbox_map` evidence with
  `colliding_object` and `route_cell` keys.
- Active default tasks:
  - `task_games__crossing__collision_time_value`
  - `task_games__crossing__moving_object_count`

### `darts`
- Visual grammar: simplified labeled dartboard with dart markers, extra-wide double/triple/bull scoring bands, large sector numbers, image-drawn score options for total-score queries, and lower dart density for count queries.
- Visual styles include six dartboard palettes, shared games/puzzles panel-scene treatments, sampled text fonts, and layout jitter for the dartboard panel.
- Reasoning coverage: score readout, ring membership count, and threshold score count.
- Evidence uses homogeneous dart-center `point_set` witnesses; total-score evidence marks the scored dart, not the selected score option.
- Active default tasks:
  - `task_games__darts__total_score_option_label`
  - `task_games__darts__condition_count`

### `dominoes`
- Visual grammar: domino chain plus loose candidate tiles.
- Visual styles include six domino-tile themes layered over the shared games/puzzles panel-scene treatments, sampled text fonts, and layout jitter for the whole chain/tableau group.
- Reasoning coverage: open-end match, reference pip-sum comparison, target pip sum, double detection, and two-step chain extension.
- Evidence uses homogeneous `bbox_set` witnesses over loose domino tiles for property counts. The two-step extension task uses role-bound `keyed_bbox_map` evidence with `first_step_domino` and `second_step_domino` keys.
- Active default tasks:
  - `task_games__dominoes__property_count`
  - `task_games__dominoes__two_step_extension_label`

### `dots_and_boxes`
- Visual grammar: dots-and-boxes board state.
- Visual styles include six board themes (`classic`, `soft`, `outlined`, `notebook`, `slate`, `wood_panel`) layered over shared games/puzzles panel-scene treatments.
- Rendering uses deterministic font-family sampling for the board title, unit-size jitter, dynamic canvas sizing for smaller sampled boards, and fractional layout jitter before evidence projection.
- Reasoning coverage: three-sided box count and capture move count; the capture task includes both all-missing-edge and highlighted-candidate query ids.
- Evidence uses homogeneous `bbox_set` witnesses: box-region boxes for three-sided-box queries and missing-edge gap boxes for capture-move queries.
- Active default tasks:
  - `task_games__dots_and_boxes__three_sided_box_count`
  - `task_games__dots_and_boxes__capture_move_count`

### `go`
- Visual grammar: Go board with one marked group.
- Visual styles include six board/stone themes (`classic`, `soft`, `outlined`, `wood_board`, `slate_board`, `paper_board`) layered over shared games/puzzles panel-scene treatments.
- Rendering uses unit-size jitter, dynamic canvas sizing for smaller sampled boards, and fractional layout jitter before evidence projection.
- Reasoning coverage: liberty, adjacent enemy, and shared-liberty counts.
- Evidence uses homogeneous `point_set` witnesses at liberty intersections or adjacent enemy-stone centers.
- Active default tasks:
  - `task_games__go__group_liberty_count`
  - `task_games__go__group_adjacent_enemy_count`

### `hex`
- Visual grammar: Hex board with red and blue stones, colored goal sides, and optional labeled empty candidate cells.
- Visual styles include five board/stone themes (`classic`, `soft`, `outlined`, `slate`, `paper`) layered over shared games/puzzles panel-scene treatments.
- Rendering uses sampled candidate-label fonts, unit-size jitter, dynamic canvas sizing for smaller boards, and fractional layout jitter before evidence projection.
- Reasoning coverage: immediate winning-cell selection and minimum empty-cell connection gap counting.
- Evidence uses cell-center `point_set` witnesses: one point for the chosen winning cell, or all empty cells in the minimum connection gap.
- Active default tasks:
  - `task_games__hex__winning_move_cell_label`
  - `task_games__hex__connection_gap_count`

### `marble_chain`
- Visual grammar: Zuma-like colored marble chain on a gray curved or spiral track with a central shooter, shooter marble, and labeled or marked shot arrows.
- Visual styles use the shared game panel treatment/palette layer, five scene-local track/shooter styles, sampled arrow-label fonts, and semicircle, spiral, and double-arc track layouts.
- Reasoning coverage: shot-direction selection by pop effect, plus numeric pop-count queries after a marked shot.
- Evidence uses `point_set` witnesses: one insertion-gap point for shot-direction labels, or popped marble-center points for numeric pop-count queries.
- Active default tasks:
  - `task_games__marble_chain__shot_direction_label`
  - `task_games__marble_chain__shot_effect_value`

### `match3`
- Visual grammar: match-3 jewel grid with row and column numbers, colored gem cells, and marked or labeled adjacent-swap arrows.
- Visual styles use the shared game panel treatment/palette layer, sampled fonts, layout jitter, and five scene-local gem/board styles (`faceted_jewels`, `round_candies`, `beveled_tiles`, `diamond_gems`, `orb_tokens`). The game rule is one adjacent swap followed by immediate run clearing only; no gravity, refill, special effects, or cascades.
- Reasoning coverage: numeric clear/run counts after a marked swap, plus labeled swap selection by maximum or target immediate clear count.
- Evidence uses `point_set`: numeric clear counts mark cleared gem centers, created-run counts mark one point per created run, and labeled swap tasks mark one point on the selected swap arrow.
- Active default tasks:
  - `task_games__match3__swap_effect_value`
  - `task_games__match3__best_swap_label`

### `tetris`
- Visual grammar: variable-size Tetris boards with `7..11` columns and `10..15` rows, colored locked blocks, a NEXT piece preview for placement optimization, a START board with a falling piece at its shown column, and full-size labeled result boards.
- Visual styles combine the shared game panel treatment/palette layer, sampled fonts, layout jitter, post-image noise, and five scene-local tetromino block styles (`classic_blocks`, `beveled_blocks`, `paper_tiles`, `glass_blocks`, `neon_blocks`). The game rule is one hard drop followed by lock, row clear, and gravity; no cascades or new pieces are introduced.
- Reasoning coverage: maximum possible line-clear counting for a next piece with translation/rotation allowed, plus resulting-board selection for a fixed falling piece with no translation or rotation.
- Evidence uses role-bound `keyed_bbox_map` for the line-clear task (`board`, `next_piece`) and a single selected result-board `bbox_set` for the visual option-panel result task.
- Active default tasks:
  - `task_games__tetris__line_clear_count`
  - `task_games__tetris__drop_result_label`

### `ultimate_tictactoe`
- Visual grammar: Ultimate Tic-Tac-Toe board with nine small Tic-Tac-Toe boards, local X/O marks, drawn boards, and optional highlighted local-board answer options. Winning lines are not pre-drawn.
- Visual styles combine shared games-domain panel backgrounds, sampled fonts, unit-size/layout jitter, post-image noise, and five scene-local board styles (`classic_grid`, `soft_marker`, `paper_grid`, `neon_board`, `tournament_board`).
- Reasoning coverage: macro status counting across small boards and local winning/blocking move selection inside one highlighted small board.
- Evidence uses homogeneous `bbox_set`: matching small-board boxes for status counts, and the selected empty cell plus two supporting line cells for local tactic labels.
- Active default tasks:
  - `task_games__ultimate_tictactoe__small_board_status_count`
  - `task_games__ultimate_tictactoe__local_tactic_label`

### `minesweeper`
- Visual grammar: opened Minesweeper number grid with hidden cells and optional flags.
- Visual styles use the shared game panel treatment/palette layer for the canvas, while classic, soft, outlined, notebook, dark, and retro Minesweeper board styles stay scene-local for cell and clue readability.
- Rendering samples the role-aware font family for clue numbers, uses unit-size jitter with a canvas that follows the resolved board size, and applies layout jitter before evidence projection.
- Reasoning coverage: local forced-mine counting, local forced-safe counting, and satisfied-clue counting.
- Calibrated board size support is `4..8` for the scene overall; the forced-cell
  task uses `4..5` and outlines the relevant opened clue cell(s) to keep local
  deduction legible.
- Evidence uses homogeneous `bbox_set` witnesses over counted cells: hidden cells for forced-cell tasks and opened number cells for satisfied-clue counting.
- Active default tasks:
  - `task_games__minesweeper__forced_cell_count`
  - `task_games__minesweeper__satisfied_clue_count`

### `minigolf`
- Visual grammar: Mini-golf putting course with a ball, a hole, obstacles, and short starting-direction shot cues.
- Visual styles use the shared game panel treatment/palette layer for the canvas, while classic, desert, neon, garden, and blueprint course palettes stay scene-local for obstacle and fairway readability.
- Rendering samples the role-aware font family for obstacle and shot labels and applies layout jitter before evidence projection.
- Reasoning coverage: extrapolating a short cue to its first obstacle and choosing the numbered cue whose banked path reaches the hole.
- Evidence uses `point_set` for the target obstacle center in first-hit queries and `point_pair_set` for the selected visible dashed cue segment in path-label queries.
- Active default tasks:
  - `task_games__minigolf__first_obstacle_label`
  - `task_games__minigolf__shot_path_label`

### `minecraft`
- Visual grammar: Minecraft-like isometric block world with cube terrain, ore blocks, marked paths, and labeled mining routes.
- Visual styles use the shared game panel treatment/palette layer for the canvas, while grass, desert, snow, cave, and mesa block-world themes stay scene-local for terrain and ore readability.
- Rendering samples the role-aware font family for player and route labels, uses unit-size jitter with a canvas that follows the resolved world size, applies layout jitter before evidence projection, and contrast-checks rendered route colors against terrain/theme anchors.
- Reasoning coverage: ore-type counting plus route/path block counting over marked tunnel paths and named mining routes.
- Evidence uses homogeneous `bbox_set` witnesses over counted cube blocks; route-cost evidence is empty when the named route has zero cost.
- Active default tasks:
  - `task_games__minecraft__ore_block_count`
  - `task_games__minecraft__route_block_count`

### `battleship`
- Visual grammar: Battleship board with the full fleet placed on the grid, red hit markers on ship cells, miss markers on water, and a side fleet-shape panel.
- Visual styles use the shared game panel treatment/palette layer for canvas and surrounding chrome, while the Battleship grid and fleet panel keep classic blue, soft, outlined, navy, radar, and paper palettes for ship/hit readability.
- Reasoning coverage: counting fleet ships whose every cell has been hit, and counting damaged ships that are hit but not sunk.
- Active default tasks:
  - `task_games__battleship__ship_status_count`

### `nine_mens_morris`
- Visual grammar: Nine Men's Morris board.
- Visual styles use the shared game panel treatment/palette layer for canvas and surrounding chrome, while classic, soft, outlined, wood-panel, slate, and parchment Morris boards stay scene-local for line/piece readability.
- Rendering samples the role-aware font family for the board title, uses unit-size jitter with a canvas that follows the resolved board size, and applies layout jitter before evidence projection.
- Reasoning coverage: all-piece mill membership counts.
- Evidence uses homogeneous `point_set` witnesses at counted piece centers.
- Active default tasks:
  - `task_games__nine_mens_morris__pieces_in_mill_count`

### `pacman`
- Visual grammar: Pac-Man style maze with a visible Pac-Man marker, ghosts, normal pellets, labeled bonus items, and a highlighted route.
- Visual styles use the shared game panel treatment/palette layer for the canvas, while classic, neon, paper, terminal, and pastel Pac-Man maze palettes stay scene-local for route, wall, pellet, item, and ghost readability.
- Rendering samples the role-aware font family for item labels, uses unit-size jitter with a canvas that follows the resolved maze size, and applies slack-based layout jitter before evidence projection.
- Reasoning coverage: route pellet counting, route counting before the first ghost, and first labeled item reached along a route.
- Evidence uses object-center `point_set` witnesses for counted pellets, selected bonus items, and the stop ghost in the before-ghost query.
- Active default tasks:
  - `task_games__pacman__route_pellet_count`
  - `task_games__pacman__next_item_label`

### `platformer`
- Visual grammar: side-scroller platformer level with a player character, platforms, hazards, coins, and dashed jump arcs.
- Visual styles include day, cave, neon, snow, and sunset palettes.
- Reasoning coverage: extrapolating a short jump arc to a landing platform and counting coins along a shown jump arc.
- Evidence uses the landing platform bbox for landing labels and coin-center points for collectible counts.
- Active default tasks:
  - `task_games__platformer__jump_landing_label`
  - `task_games__platformer__collectible_count`

### `pool`
- Visual grammar: pool table with cue ball, numbered object balls, six pockets, and optional marked shot indicators.
- Visual styles include classic green cloth, tournament-blue cloth, burgundy cloth, charcoal cloth, and light-rail tables.
- Reasoning coverage: no-bank direct-shot pottability, current-player group filtering, and blockers on a marked shot lane.
- Evidence uses ball-center `point_set` witnesses for pottable and blocking-ball counts.
- Active default tasks:
  - `task_games__pool__pottable_ball_count`
  - `task_games__pool__blocking_ball_count`

### `reversi`
- Visual grammar: Reversi board state.
- Visual styles include classic green boards, wood-framed boards, slate boards, blue boards, and outlined boards.
- Reasoning coverage: legal moves, corner moves, and marked-move flip counts.
- Evidence uses destination-square `bbox_set` witnesses for legal move counts and flipped-disc-center `point_set` witnesses for marked-move flip counts.
- Active default tasks:
  - `task_games__reversi__legal_destination_count`
  - `task_games__reversi__marked_move_flip_count`

### `rhythm`
- Visual grammar: rhythm-game falling-note lanes with lane numbers and a bottom hit line.
- Visual styles include arcade, neon, paper, dark, and pastel lane/playfield palettes layered over shared games/puzzles panel-scene treatments.
- Lane labels and the hit-line marker sample one deterministic font family from the readout font pool; layout jitter shifts the whole lane grid before evidence projection.
- Reasoning coverage: timing-window note counting, color-filtered timing-window counting, most-arriving lane selection, and earliest-arriving lane selection.
- Evidence uses homogeneous note `bbox_set` witnesses: counted notes for hit-window queries and selected-lane/earliest-note witnesses for lane-choice queries.
- Active default tasks:
  - `task_games__rhythm__hit_window_count`
  - `task_games__rhythm__lane_choice_value`

### `rule_override_board`
- Visual grammar: multiple small game-board panels; the rule is stated in the prompt, not rendered as a visual card.
- Visual styles use the shared game panel treatment/palette layer for the canvas and five scene-local board styles for the mini-boards.
- The board group uses unit-size variation and slack-fraction layout jitter before evidence projection; board labels sample one deterministic font family from the readout font pool.
- Reasoning coverage: result counting under the prompt-stated rule, split into line-pattern outcomes and piece-count outcomes over 4 to 6 mini-boards.
- Evidence uses homogeneous mini-board `bbox_set` witnesses for counted wins or losses; the evidence cardinality is the answer.
- Active default tasks:
  - `task_games__rule_override_board__line_result_count`
  - `task_games__rule_override_board__piece_result_count`

### `snake`
- Visual grammar: Snake game board with a yellow head, connected body cells, red food, gray wall cells, and a square grid.
- Visual styles include classic, neon, forest, paper, and candy board palettes layered over shared games/puzzles panel-scene treatments.
- Option labels and game-over cards sample one deterministic font family from the readout font pool; unit-size and layout jitter are recorded before evidence projection.
- Reasoning coverage: safe-direction counting with wall cells as unsafe blockers, plus planned 3 to 5 move simulation against image-visible point or `GAME OVER` options. Option-letter answers are only used where the option labels are drawn in the image.
- Evidence uses homogeneous board-cell `bbox_set` witnesses: safe destination cells for immediate-move counts and traversed head-path cells for planned-move option selection. The option letter is the answer but not the prompt-facing evidence.
- Active default tasks:
  - `task_games__snake__safe_direction_count`
  - `task_games__snake__path_outcome_option_label`

### `space_shooter`
- Visual grammar: retro space-shooter playfield with vertical lane guides, labeled enemy ships, falling enemy shots, shields or asteroids, a player ship, and bottom lane pads.
- Visual styles combine shared games-domain panel backgrounds, sampled enemy-label fonts, layout jitter, and neon, deep-space, vector, amber, or terminal playfield palettes.
- Generation currently samples `4..8` lanes and `10..16` enemy ships for the denser queries, with count answers in `1..5`. The clear-shot query uses one foreground enemy per lane plus blockers to keep the obstruction judgment readable; the safe-lane query uses a sparse upper enemy backdrop so the bottom-pad shot/asteroid state stays visually primary.
- Reasoning coverage: unobstructed enemy lanes, projectile alignment with the player, lowest-enemy threat labeling, and safe bottom-lane counting.
- Evidence uses homogeneous `bbox_set` witnesses: counted enemy ships for clear shots, counted enemy shots for player-lane projectiles, the selected enemy ship for the lowest-threat label, and counted bottom lane pads for safe lanes.
- Active default tasks:
  - `task_games__space_shooter__clear_shot_count`
  - `task_games__space_shooter__projectile_intercept_count`
  - `task_games__space_shooter__highest_threat_label`
  - `task_games__space_shooter__safe_lane_count`

### `snakes_ladders`
- Visual grammar: 5 x 5, 6 x 6, or 7 x 7 numbered serpentine Snakes and Ladders board with one token, visible snakes, visible ladders, and a side panel for die or planning information.
- Visual styles combine shared games-domain panel backgrounds, sampled fonts, layout jitter, and classic, paper, neon, pastel, or wood board palettes.
- Evidence uses `keyed_bbox_map` for role-bound move-outcome witnesses (`start_square`, `end_square`) and single-square `bbox_set` evidence for the best-roll final square.
- Reasoning coverage: one-die final-square simulation and short-horizon highest-final-square planning over `1..2` chosen die rolls.
- Active default tasks:
  - `task_games__snakes_ladders__move_outcome_value`
  - `task_games__snakes_ladders__best_roll_value`

### `sudoku`
- Visual grammar: partially filled Sudoku grid with optional marked cell or highlighted unit.
- Visual styles combine shared games-domain panel backgrounds, sampled digit fonts, layout jitter, post-image noise, and classic, soft, outlined, notebook, slate, or warm-paper Sudoku board palettes.
- Public evidence stays as homogeneous `bbox_set`: marked-cell tasks include the red-outlined marked cell plus visible peer witnesses, missing-digit tasks include visible filled cells in the highlighted unit, and repeated-digit tasks include highlighted-unit cells whose digit repeats.
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
