# Games Task Setup

Use this document for the active `games` domain contract.

For cross-domain coverage rollups, use `docs/ACTIVE_TASK_INVENTORY.md` instead of repeating those inventories here.

## 1) Domain scope
1. `games` stays state-first: the image depicts a recognizable game artifact whose visible pieces are enough to solve the query.
2. Prefer fully observable questions with explicit rules over hidden-information or convention-heavy strategy.
3. Prompt-facing annotation stays on visible witness pieces or board cells, not decorative table chrome.

## 2) Task unit rule
1. Public taxonomy is `domain=games -> scene_id -> task_id`.
2. A `scene_id` is the shared game renderer/grammar, such as `cards` or `connect_four`.
3. A task is separate when it requires a distinct reasoning algorithm or annotation contract, even if it uses the same scene renderer.
4. Mirror or parameter knobs inside one reasoning contract stay as query params, such as player color, row/column axis, board size, or threshold direction.
5. Default and targeted generation should use the active task ids below.

## 2.1 Scene-package objective ownership
1. In migrated scene-package code, each public games task file must own the objective-specific generation program for that task. The task file should contain the registered public task class plus the task's target construction, answer binding, prompt-facing annotation binding, prompt-slot assembly, and task-specific trace payload.
2. Scene-local `shared/` code is for reusable game primitives: board/rule dataclasses, legal move or scoring helper functions, samplers that do not choose the public objective, renderers, style/layout/text/marker helpers, and annotation projection helpers.
3. If multiple games tasks in one scene share rendering, board construction, layout, style, move/scoring primitives, or annotation projection logic, that shared code should stay in `trace/tasks/games/<scene_id>/shared/` and be imported by the public task files.
4. Do not migrate a games scene by moving the old multi-task module into `scene_id/shared/` and replacing public task files with one-line wrappers or subclasses that only force an objective name.
5. If two games task files would be pure wrappers over the same shared generator after factoring, merge them into one public task with a `query_id` axis, or split the objective logic so each task file owns a real distinct program.
6. A games scene is not complete for scene-package migration until both conditions hold: source paths match `trace/tasks/games/<scene_id>/<objective_contract>.py`, and every public task module owns its objective-specific program.

## 2.2 Repeated-unit visual requirement
1. Game scenes built from repeated board cells, grid squares, hexes, lanes, slots, wells, dots, or voxel/block units should include non-semantic unit-size jitter. Try for at least a `2x` min-to-max span (`max_unit_size / min_unit_size >= 2.0`) first, but use a narrower documented range when readability, scene fit, or annotation integrity requires it.
2. This requirement applies to board/grid scenes such as chess, checkers, Go, Hex, Battleship, Minesweeper, Connect Four, Dots and Boxes, Snake, Sokoban, sliding-block boards, 2048, Reversi, Pac-Man, Bubble Shooter, Brick Breaker, Minecraft-like block worlds, and similar repeated-unit renderers.
3. Logical board-size variation alone does not satisfy the requirement; the rendered unit size should vary independently when feasible.
4. Record the sampled unit size or scale in render metadata and compute annotation bboxes/points from the final jittered layout. Document any exception where a canonical board, readability constraint, or verifier contract requires a narrower range.
5. Broad style primitives may live in domain-level config/helpers, but concrete rendering variation is applied scene by scene. Each game scene owns how palettes, strokes, board chrome, piece styling, unit-size jitter, and layout slack map onto its visible rules and annotation.
6. Do not use a blind domain-level recolor/layout pass for game scenes; visual variation must preserve piece/cell readability and must not change the answer, annotation, or rule semantics.
7. Each game scene should aim for at least five scene-local board/object style variants, separate from shared canvas backgrounds, panel treatments, font families, and post-image noise. These variants should affect the game artifact itself, such as board skins, tile palettes, piece/token treatments, grid/line strokes, card/table chrome, lane skins, or HUD/control styling.
8. If fewer than five scene-local styles are safe because the artifact has a canonical visual identity or tight readability constraints, document the exception in this file and record the active style axis in render metadata.
9. Any answer-bearing path, marker, or option color drawn over known panel/board/lane backgrounds must pass through the shared Lab-distance contrast guard (`resolve_contrasting_palette(...)`) with panel anchors from `game_panel_contrast_anchor_colors(...)`, or an equivalent documented scene-specific guard. Do not rely on hand-picked RGB palettes alone.
10. Board-inside-canvas scenes should use shared slack-based layout jitter by default. The sampled offset should be a fraction of the available safe slack after content size is resolved, not a small fixed pixel offset, and the final `layout_jitter` metadata must record the requested fraction, realized pixel offset, clamp range, and any unit-size jitter.
11. Required game readouts, board labels, option labels, card ranks, and readable game symbols must route through `trace/tasks/games/shared/text.py`. Scene themes may provide preferred text colors, but the helper resolves final nonsemantic ink/stroke against the actual surface and records required text-legibility metadata in the trace.
12. Required game markers, including marked cells, selected moves, highlighted groups, routes, rings, and semantic option cues, must route through `trace/tasks/games/shared/marking.py` or an equivalent wrapper over `trace/tasks/shared/marker_legibility.py`. Resolve marker colors against the actual board/cell/object surface, draw a halo/accent marker, and record marker-legibility metadata; do not use fixed outline RGBs on variable game surfaces.

## 2.3 In-image text policy
1. Do not draw generic scene titles that only name the game or artifact, such as `DARTBOARD`, `Dots and Boxes`, `Solitaire tableau`, or `Sokoban grid`; the prompt can provide that context.
2. Keep image text when it is part of the board grammar, answer interface, or local rule/readout needed to parse the visible state. Examples include `BINGO`, called-number headers, row/column coordinates, card ranks/suits, dice values, `Original`, option labels, movement direction strips, roll panels, and fleet-shape legends.
3. If a scene needs a concise legend or status strip, it should describe the local visible rule or state, not restate the scene name.

## 3) Active scenes and tasks
Review artifacts for these tasks use `review/task-reviews/games/<scene_id>/<task_id>/`.

### `2048`
- Visual grammar: 4 x 4 2048 board with numbered tiles, one shown move arrow, four labeled candidate arrows, or six labeled candidate result boards.
- Visual styles use the shared game panel treatment/palette layer for canvas and board chrome, while tile values keep classic, dark, paper, neon, and pastel 2048 tile palettes for readability.
- The canvas follows the resolved board size so small unit-size samples do not float in an oversized fixed frame; arrow and label padding remain non-semantic and recorded in render metadata.
- Tile-number and option-badge text samples a deterministic font family from the readout font pool.
- Reasoning coverage: one-move merge counting, one-move score computation, post-move maximum-tile value, and full post-move board-state selection.
- Annotation uses `point_pair_set` for merge-derived value tasks (`merge_count`, `score_value`), with one pair of original source-tile centers per merge. `max_tile_value` and visual result-board selection use `bbox_set` witnesses.
- Active default tasks:
  - `task_games__2048__move_result_board_label`
  - `task_games__2048__max_tile_value`
  - `task_games__2048__merge_count`
  - `task_games__2048__score_value`

### `backgammon`
- Visual grammar: numbered Backgammon board with black and white checker stacks and two dice.
- Visual styles use the shared game panel treatment/palette layer for canvas and surrounding chrome, while the Backgammon board itself keeps classic, navy, parchment, slate, and tournament palettes for point/checker readability.
- Board size, checker size, dice size, labels, and canvas dimensions vary together; point annotation is projected from the final jittered board geometry.
- Point labels, stack-count text, and the rule header sample one deterministic font family from the readout font pool.
- Reasoning coverage: distinct single-die destination counting for legal moves, hit moves, and blocked destination candidates, plus simple numbered-point state counting by checker color and stack size. Active-player sampling covers black moving 24 to 1 and white moving 1 to 24 for move-based queries.
- Active default tasks:
  - `task_games__backgammon__destination_count`
  - `task_games__backgammon__point_state_count`

### `bingo`
- Visual grammar: 5 x 5 bingo card.
- Visual styles use the shared game panel treatment/palette layer for canvas and card chrome, while Bingo card palettes, mark shapes, and cell-fill patterns remain scene-local for number and mark readability.
- Card size, cell size, marker geometry, labels, and canvas dimensions vary together; cell annotation is projected from the final jittered card geometry.
- The `BINGO` wordmark, column headers, and cell numbers sample one deterministic font family from the readout font pool.
- Reasoning coverage: completed-column identification, near-complete-line counting, called-number matching, and summing printed numbers in one completed row or column.
- Active default tasks:
  - `task_games__bingo__called_number_match_count`
  - `task_games__bingo__completed_column_label`
  - `task_games__bingo__completed_line_sum_value`
  - `task_games__bingo__near_complete_line_count`

### `bowling`
- Visual grammar: bowling lane with a ball, labeled pins, and optional labeled aiming paths.
- Source layout: migrated scene package at `trace/tasks/games/bowling/`, with one public task file per objective and scene-local helpers under `trace/tasks/games/bowling/shared/`.
- Visual styles use the shared game panel treatment/palette layer for canvas and lane chrome, while the five lane themes keep ball, pin, and path palettes scene-local for motion and label readability.
- Path colors are resolved against the current panel/lane/label anchor colors using the shared Lab-distance contrast guard so dashed paths and circular path markers cannot blend into the sampled game background.
- Pin and path labels sample one deterministic font family from the readout font pool.
- Reasoning coverage: first-pin hit labeling by extrapolating a verified first-collision ball trajectory with non-target clearance, and spare-path labeling by comparing shorter visible path cues through the remaining pins.
- Annotation uses pin `bbox_set` witnesses for first-hit queries and selected path `point_pair_set` witnesses for spare-path queries.
- Active default tasks:
  - `task_games__bowling__first_pin_hit_label`
  - `task_games__bowling__spare_path_label`

### `brick_breaker`
- Visual grammar: brick-breaker playfield with labeled top bricks, a short visible dashed motion cue, a neutral paddle marker, and labeled bottom catch lanes.
- Visual styles use the shared game panel treatment/palette layer for canvas and playfield chrome, while classic, neon, paper, blueprint, and arcade playfield palettes stay scene-local.
- Brick and lane labels sample one deterministic font family from the readout font pool; the dashed trajectory cue is resolved against panel, playfield, lane, and paddle colors using the shared Lab-distance contrast guard.
- The canvas follows the resolved playfield size so small unit-size samples do not float in an oversized fixed frame.
- Annotation uses homogeneous `point_set` witnesses at selected brick or catch-lane pad centers.
- Reasoning coverage: trajectory-target labeling by extrapolating straight ball motion, plus same-row counting after the hit brick is removed.
- Active default tasks:
  - `task_games__brick_breaker__hit_row_remaining_count`
  - `task_games__brick_breaker__next_hit_label`
  - `task_games__brick_breaker__paddle_catch_label`

### `bubble_shooter`
- Visual grammar: close-packed bubble-shooter board with colored bubbles, a dashed landing target, and optional labeled next-color choices.
- Visual styles use the shared game panel treatment/palette layer for canvas and playfield chrome, while classic, pastel, neon, paper, and arcade bubble-board palettes stay scene-local.
- Option labels sample one deterministic font family from the readout font pool; the aim cue is resolved against panel, playfield, launcher, and option-panel colors using the shared Lab-distance contrast guard.
- The canvas follows the resolved playfield size so small unit-size samples do not float in an oversized fixed frame.
- Public annotation uses object-center `point_set` witnesses for popped/dropped board bubbles; marked landing slots and selected color options remain trace/render metadata rather than prompt-facing annotation.
- Reasoning coverage: same-color pop counts, post-pop drop counts, and fixed-landing color-option selection.
- Active default tasks:
  - `task_games__bubble_shooter__pop_color_label`
  - `task_games__bubble_shooter__drop_count`
  - `task_games__bubble_shooter__pop_count`

### `cards`
- Visual grammar: visible playing-card hands, rows, and small labeled card-game comparison layouts.
- Visual styles use the shared games background layer, while classic, soft, outlined, ivory, and slate card themes vary card faces, borders, shadows, reference banners, and continuation cues.
- Card ranks, hand labels, player badges, and continuation cues sample one deterministic font family from the readout font pool; suit symbols use the renderer fallback font so sampled font families cannot show missing-glyph boxes.
- Card layouts use final-layout jitter before annotation projection; reference cards, winning hands, pattern-completion candidates, and run/triple witnesses are grounded by card bboxes computed after jitter. Reference-condition tasks anchor the `REF` card at the leftmost card in the top row and shuffle non-reference cards by default. Exact-triple annotation is keyed by rank with one bbox set per exact triple.
- Reasoning coverage: suit match, rank comparison, multiplicity, ordered run reasoning, missing-card pattern completion, blackjack comparison, poker comparison, poker draw completion, trick-taking winner rules, and trick-winning play choice.
- Active default tasks:
  - `task_games__cards__blackjack_best_hand_label`
  - `task_games__cards__exact_triple_count`
  - `task_games__cards__longest_run_length`
  - `task_games__cards__missing_card_to_complete_hand_label`
  - `task_games__cards__poker_best_hand_label`
  - `task_games__cards__poker_draw_card_label`
  - `task_games__cards__higher_than_reference_count`
  - `task_games__cards__same_suit_as_reference_count`
  - `task_games__cards__trick_taking_winner_label`
  - `task_games__cards__trick_winning_play_label`

### `solitaire`
- Visual grammar: solitaire tableau columns with labeled exposed cards, foundation piles, stock/free-cell chrome, and image-drawn move options where needed.
- Visual styles combine shared games-domain panel backgrounds, sampled fonts, layout jitter, post-image noise, and five scene-local card/tableau styles (`classic_cards`, `ivory_table`, `casino_felt`, `slate_cards`, `paper_tableau`).
- Reasoning coverage: tableau/foundation move legality, foundation-readiness counting, adjacent tableau-sequence counting, and marked same-suit run-length measurement.
- Annotation uses `keyed_bbox_map` for move legality (`source_card`, `target`) and homogeneous `bbox_set` witnesses for the count/value tasks.
- Active default tasks:
  - `task_games__solitaire__foundation_ready_count`
  - `task_games__solitaire__move_legality_label`
  - `task_games__solitaire__same_suit_run_length_value`
  - `task_games__solitaire__tableau_sequence_count`

### `checkers`
- Visual grammar: checkers board with ordinary men; the capture-chain task additionally marks one king checker.
- Visual styles include six board/token themes (`classic`, `soft`, `outlined`, `wood_token`, `blue_table`, `charcoal`) layered over the shared games/puzzles panel scene styles.
- Rendering uses deterministic font-family sampling for player badges plus unit-size and fractional layout jitter; canvas size can shrink around smaller sampled boards while preserving annotation alignment.
- Reasoning coverage: legal landing-square count, capture landing-square count, source-piece mobility count, visible piece-state counting, and longest capture-chain length for a marked king.
- Annotation contracts use homogeneous witnesses: `bbox_set` for landing-square and captured-piece boxes, plus `point_set` for source-piece or counted-piece centers in piece-count tasks.
- Active default tasks:
  - `task_games__checkers__max_capture_chain_length`
  - `task_games__checkers__move_count`
  - `task_games__checkers__piece_mobility_count`
  - `task_games__checkers__piece_state_count`

### `chess`
- Visual grammar: partial standard chess board with white and black pieces; movement-rule tasks use material-plausible positions, while piece-count tasks may use arbitrary visible piece sets.
- Visual styles include six board/piece themes (`classic`, `soft`, `outlined`, `wood_token`, `blue_glyph`, `monochrome_glyph`) layered over the shared games/puzzles panel scene styles.
- Rendering uses deterministic font-family sampling for player/marked-piece badges while chess-piece glyphs use system symbol fallback; unit-size and fractional layout jitter are recorded after final layout, and smaller boards can use a dynamically smaller canvas.
- Reasoning coverage: chess-piece type/color counting, marked-piece movement, marked-piece capture, side-wide capture opportunity, target-square attacker counting, line blocker counting, marked-king escape-square counting, and immediate checkmate move selection.
- Annotation contracts use homogeneous `bbox_set` witnesses for count tasks: destination-square boxes for movement/escape queries and piece boxes for type/count/capture/attacker queries. The checkmate move-label task uses `keyed_bbox_map` for the selected move source, destination, and opposing king square.
- Active default tasks:
  - `task_games__chess__target_square_attacker_count`
  - `task_games__chess__checkmate_move_label`
  - `task_games__chess__marked_piece_blocker_count`
  - `task_games__chess__king_escape_square_count`
  - `task_games__chess__marked_piece_destination_count`
  - `task_games__chess__colored_piece_kind_count`
  - `task_games__chess__piece_kind_count`
  - `task_games__chess__player_capture_piece_count`

### `chess_variant`
- Visual grammar: chess-like 8 by 8 material-plausible board with filled white and black chess-piece glyphs, an outlined marked square, and a visible rule-card badge.
- Visual styles use six chess-board palettes layered over the shared games/puzzles panel scene styles; piece glyph rendering matches the regular chess scene while every visible piece follows the displayed rule card rather than its normal chess move.
- Rendering uses sampled fonts for the rule-card badge, fixed chess-symbol rendering for pieces, unit-size and fractional layout jitter, and dynamic canvas sizing for smaller sampled boards.
- Reasoning coverage: marked-piece destination/capture counting and inverse target-square reachability counting under visible nonstandard movement rules.
- Annotation uses homogeneous `bbox_set` witnesses over qualifying destination cells for marked-piece queries, and `point_set` witnesses over source-piece centers for target-square reacher queries.
- Active default tasks:
  - `task_games__chess_variant__marked_piece_destination_count`
  - `task_games__chess_variant__target_square_reacher_count`

### `circular_chess`
- Visual grammar: material-plausible four-ring by sixteen-sector circular chess board with white and black standard chess glyphs; sectors wrap around each ring.
- Visual styles include five circular-board palettes layered over the shared games/puzzles panel scene styles, with unit-size and fractional layout jitter.
- Reasoning coverage: pseudo-legal circular movement destination/capture counting and inverse target-cell reachability counting.
- Annotation uses `point_set` witnesses because annular-sector bboxes are visually awkward: destination-cell centers for marked-piece tasks and source-piece centers for target-cell reacher tasks.
- Active default tasks:
  - `task_games__circular_chess__marked_piece_destination_count`
  - `task_games__circular_chess__target_cell_reacher_count`

### `connect_four`
- Visual grammar: Connect Four board with gravity.
- Visual styles include six board/disc themes (`classic`, `soft`, `outlined`, `arcade_blue`, `teal_frame`, `charcoal`) layered over the shared games/puzzles panel scene styles.
- Rendering uses deterministic font-family sampling for player badges, unit-size and fractional layout jitter, variable board dimensions, and dynamic canvas sizing for smaller sampled boards.
- Reasoning coverage: immediate winning-drop counting, safe-drop counting, and labeled immediate winning-column selection.
- Annotation uses homogeneous `point_set` witnesses at qualifying landing-cell centers for count tasks; the label task marks the selected column's landing cell center rather than the rendered column label.
- Active default tasks:
  - `task_games__connect_four__safe_move_count`
  - `task_games__connect_four__winning_move_column_label`
  - `task_games__connect_four__winning_move_count`

### `crossing`
- Visual grammar: lane-crossing motion board with horizontal traffic rows, direction arrows, start pads, one marked route line, and a goal band.
- Visual styles include day, night, retro, paper, and construction lane palettes,
  shared games/puzzles panel-scene treatments, sampled text fonts, and layout
  jitter for the whole playfield.
- Reasoning coverage: identifying the labeled moving object that hits a marked route, identifying which
  labeled moving object hits the route first among multiple collisions, and moving-object direction counting.
- Annotation uses homogeneous `bbox_set` over the matching moving objects; label tasks mark only the
  selected labeled object.
- Active default tasks:
  - `task_games__crossing__first_hit_object_label`
  - `task_games__crossing__hit_object_label`
  - `task_games__crossing__moving_object_direction_count`

### `darts`
- Visual grammar: simplified labeled dartboard with dart markers, extra-wide double/triple/bull scoring bands, large sector numbers, one-dart image-drawn score options for total-score queries, and higher dart density for count queries.
- Visual styles include six dartboard palettes, shared games/puzzles panel-scene treatments, sampled text fonts, and layout jitter for the dartboard panel.
- Reasoning coverage: score readout, ring membership count, and threshold score count.
- Annotation uses homogeneous dart-center `point_set` witnesses; total-score annotation marks the scored dart, not the selected score option.
- Active default tasks:
  - `task_games__darts__ring_count`
  - `task_games__darts__threshold_score_count`
  - `task_games__darts__total_score_option_label`

### `dominoes`
- Visual grammar: domino chain plus loose candidate tiles.
- Visual styles include six domino-tile themes layered over the shared games/puzzles panel-scene treatments, sampled text fonts, and layout jitter for the whole chain/tableau group.
- Reasoning coverage: direct legal play counts, second-play candidate counts, extendable first-play counts, reference pip-sum comparison, target pip sum, and double detection.
- Annotation uses homogeneous `bbox_set` witnesses over the counted loose domino tiles for both property and chain-play count tasks.
- Active default tasks:
  - `task_games__dominoes__extendable_first_play_count`
  - `task_games__dominoes__matching_end_count`
  - `task_games__dominoes__second_play_candidate_count`
  - `task_games__dominoes__double_count`
  - `task_games__dominoes__higher_sum_than_reference_count`
  - `task_games__dominoes__sum_to_target_count`

### `dots_and_boxes`
- Visual grammar: dots-and-boxes board state.
- Visual styles include six board themes (`classic`, `soft`, `outlined`, `notebook`, `slate`, `wood_panel`) layered over shared games/puzzles panel-scene treatments.
- Rendering uses deterministic font-family sampling for board labels, unit-size jitter, dynamic canvas sizing for smaller sampled boards, and fractional layout jitter before annotation projection.
- Reasoning coverage: three-sided box count, capture move count, and claimed-box ownership count; the capture task includes both all-missing-edge and highlighted-candidate query ids.
- Annotation uses homogeneous witnesses: full-cell `bbox_set` boxes for three-sided-box and owned-box queries, and `point_pair_set` edge endpoints for capture-move queries.
- Active default tasks:
  - `task_games__dots_and_boxes__capture_move_count`
  - `task_games__dots_and_boxes__owned_box_count`
  - `task_games__dots_and_boxes__three_sided_box_count`

### `go`
- Visual grammar: Go board with one marked group for local group-property tasks, or an unmarked Go board for whole-board stone-group counts.
- Visual styles include six board/stone themes (`classic`, `soft`, `outlined`, `wood_board`, `slate_board`, `paper_board`) layered over shared games/puzzles panel-scene treatments.
- Rendering uses unit-size jitter, dynamic canvas sizing for smaller sampled boards, fractional layout jitter before annotation projection, and one shared red contrast-safe marker style for every stone in marked-group tasks.
- Reasoning coverage: liberty, adjacent enemy, shared-liberty, and whole-board connected stone-group counts.
- Annotation uses homogeneous `point_set` witnesses at liberty intersections, adjacent enemy-stone centers, or one representative stone center per counted group.
- Active default tasks:
  - `task_games__go__group_adjacent_enemy_count`
  - `task_games__go__group_liberty_count`
  - `task_games__go__stone_group_count`

### `hex`
- Visual grammar: Hex board with red and blue stones, colored goal sides, optional labeled empty candidate cells, and optional labeled reference cells.
- Visual styles include five board/stone themes (`classic`, `soft`, `outlined`, `slate`, `paper`) layered over shared games/puzzles panel-scene treatments.
- Rendering uses sampled candidate-label fonts, unit-size jitter, dynamic canvas sizing for smaller boards, and fractional layout jitter before annotation projection.
- Reasoning coverage: immediate winning-cell selection, minimum empty-cell connection gap counting, and local neighbor-state counting around a labeled reference cell.
- Annotation uses cell-center `point_set` witnesses: one point for the chosen winning cell, all empty cells in the minimum connection gap, or all neighboring cells matching the requested state.
- Active default tasks:
  - `task_games__hex__candidate_neighbor_count`
  - `task_games__hex__connection_gap_count`
  - `task_games__hex__winning_move_cell_label`

### `lane_runner`
- Visual grammar: two-lane vertical runner track with a start marker, finish band, visible coins, a shown path, hazards, or self-contained labeled route cards depending on the task. Safe-path route cards use the same lane-grid scale as the shown-path task.
- Visual styles use shared games/puzzles panel-scene treatments plus five scene-local lane styles (`arcade_lane`, `city_road`, `forest_path`, `neon_track`, `paper_course`).
- Rendering uses sampled readout fonts, unit-size jitter, dynamic canvas sizing for the sampled row count, and fractional layout jitter before annotation projection.
- Reasoning coverage: counting coins collected by one shown path and selecting the only displayed candidate route that avoids hazards.
- Annotation uses homogeneous coin-center `point_set` witnesses for every coin collected by the shown path; the safe-path label task uses a one-box `bbox_set` witness around the selected route card.
- Active default tasks:
  - `task_games__lane_runner__path_coin_count`
  - `task_games__lane_runner__safe_path_label`

### `ludo_board`
- Visual grammar: Ludo-style cross board with canonical red, green, blue, and yellow player tokens, colored yards/home lanes, square decorative home-yard placeholders, twelve two-cell clockwise track-flow arrows, a central finish, optional image-drawn roll-option cards, and optional board-drawn destination letters.
- Visual styles keep semantic player colors fixed while varying the shared panel background, board material, track fill, outlines, token chrome, font, post-image noise, and fractional board jitter.
- Reasoning coverage: exact-roll finish readout from a home lane, selecting a single-roll or `6 then k` option that lands one token on another, and applying a shown dice sequence to choose the reached board letter.
- Annotation uses role-bound `keyed_bbox_map` witnesses: `token`/`finish` for finish rolls, `mover_token`/`target_token` for capture-option labels, and `moving_token`/`roll_sequence`/`destination_cell` for move-result labels.
- Active default tasks:
  - `task_games__ludo_board__capture_roll_option_label`
  - `task_games__ludo_board__move_result_option_label`
  - `task_games__ludo_board__winning_roll_value`

### `marble_chain`
- Visual grammar: Zuma-like colored marble chain on a gray curved or spiral track with a central shooter, shooter marble, and labeled or marked shot arrows.
- Visual styles use the shared game panel treatment/palette layer, five scene-local track/shooter styles, sampled arrow-label fonts, and semicircle, spiral, and double-arc track layouts.
- Reasoning coverage: shot-direction selection by pop effect, plus numeric pop-count queries after a marked shot.
- Annotation uses `point_set` witnesses: one insertion-gap point for shot-direction labels, or popped marble-center points for numeric pop-count queries.
- Active default tasks:
  - `task_games__marble_chain__max_pop_direction_label`
  - `task_games__marble_chain__target_pop_direction_label`
  - `task_games__marble_chain__shot_effect_value`

### `mancala_pit_board`
- Visual grammar: simplified two-row pit board with 12 labeled pits, visible seeds, a single sowing direction, an X-marked source pit, and an optional target-marked pit.
- Visual styles combine shared games-domain panel backgrounds, sampled readout fonts for pit labels, layout jitter, post-image noise, and five scene-local pit-board styles (`wood_tray`, `sand_stone`, `slate_bowls`, `cloth_pits`, `arcade_pits`).
- Reasoning coverage: last-seed landing pit selection after one short sowing move, and post-sow seed counting for one marked target pit. These tasks intentionally omit capture, stores, extra turns, and strategic Mancala rules.
- Annotation uses a single-pit `bbox_set` for landing labels, and role-bound `keyed_bbox_map` annotation with `source_pit` and `target_pit` for post-sow count values.
- Active default tasks:
  - `task_games__mancala_pit_board__post_sow_pit_count_value`
  - `task_games__mancala_pit_board__sowing_landing_pit_label`

### `match3`
- Visual grammar: match-3 jewel grid with row and column numbers, colored gem cells, and labeled adjacent-swap arrows.
- Visual styles use the shared game panel treatment/palette layer, sampled fonts, layout jitter, and five scene-local gem/board styles (`faceted_jewels`, `round_candies`, `beveled_tiles`, `diamond_gems`, `orb_tokens`). The game rule is one adjacent swap followed by immediate run clearing only; no gravity, refill, special effects, or cascades.
- Reasoning coverage: canonical named-color gem counting in the full grid, one row, or one column; labeled swap selection by maximum or target immediate clear count.
- Annotation uses `point_set`: gem-count tasks mark matching gem centers, and labeled swap tasks mark one point on the selected swap arrow.
- Active default tasks:
  - `task_games__match3__gem_count`
  - `task_games__match3__max_clear_swap_label`
  - `task_games__match3__target_clear_swap_label`

### `tetris`
- Visual grammar: variable-size Tetris boards with `7..11` columns and `10..15` rows, colored locked blocks, a NEXT piece preview for placement optimization, a START board with a falling piece at its shown column, static row-count boards, shifted-drop timing boards, and full-size labeled result boards.
- Visual styles combine the shared game panel treatment/palette layer, sampled fonts, layout jitter, post-image noise, and five scene-local tetromino block styles (`classic_blocks`, `beveled_blocks`, `paper_tiles`, `glass_blocks`, `neon_blocks`). The game rule is one hard drop followed by lock, row clear, and gravity; no cascades or new pieces are introduced.
- Reasoning coverage: maximum possible line-clear counting for a next piece with translation/rotation allowed, static row-occupancy counting, top/bottom occupied-row cell counting, shifted-drop collision timing with no rotation, plus resulting-board selection for a fixed falling piece with no translation or rotation.
- Annotation uses role-bound `keyed_bbox_map` for the line-clear task (`board`, `next_piece`), role-bound `keyed_bbox_set_map` for shifted-drop timing (`start_piece`, `stop_witness`), and homogeneous `bbox_set` for qualifying rows, selected edge-row cells, or selected result-board option panels.
- Active default tasks:
  - `task_games__tetris__drop_collision_time_value`
  - `task_games__tetris__drop_result_label`
  - `task_games__tetris__edge_occupied_row_cell_count`
  - `task_games__tetris__line_clear_count`
  - `task_games__tetris__row_occupancy_status_count`

### `tic_tac_toe_3d`
- Visual grammar: 3 by 3 by 3 Tic-Tac-Toe board shown as three slanted 3 by 3 layers stacked vertically in top-to-bottom order, Atari-style and without layer-name text inside the image.
- Visual styles combine the shared games-domain panel backgrounds, sampled fonts, unit-size/layout jitter, post-image noise, and five scene-local board styles (`classic_grid`, `paper_board`, `arcade_blue`, `mint_table`, `charcoal_lines`).
- Reasoning coverage: immediate 3D line-completion move selection and named-layer X/O piece counting.
- Annotation uses homogeneous witnesses: `bbox_set` over the selected empty cell plus two support cells for winning-move labels, and `point_set` over matching piece centers for layer-count queries.
- Active default tasks:
  - `task_games__tic_tac_toe_3d__layer_piece_count`
  - `task_games__tic_tac_toe_3d__winning_move_cell_label`

### `tower_defense`
- Visual grammar: tower-defense map with a discrete winding path, optional marked enemy, visible towers, and circular tower range rings.
- Visual styles combine shared games-domain panel backgrounds, layout jitter, post-image noise, and five scene-local map skins (`grass_field`, `desert_path`, `blueprint_grid`, `night_ops`, `paper_map`).
- Reasoning coverage: local circular range containment for towers covering the marked enemy, plus union coverage along discrete path nodes.
- Annotation uses homogeneous `point_set` witnesses: tower centers for the marked-enemy task and path-node centers for the path-coverage task. Empty annotation is valid only for the marked-enemy task.
- Active default tasks:
  - `task_games__tower_defense__covered_path_segment_count`
  - `task_games__tower_defense__tower_coverage_count`

### `tower_draughts_board`
- Visual grammar: checkerboard-like tower draughts board on alternating playable squares, with red and black disk stacks, optional crowned top disks, and one X-marked stack for movement tasks.
- Visual styles combine shared games-domain panel backgrounds, unit-size/layout jitter, post-image noise, and five scene-local board skins (`wood_table`, `ink_board`, `felt_mat`, `night_tokens`, `parchment`).
- Reasoning coverage: count stacks by top-disk control, count one-step diagonal destinations for a marked stack, and count immediate diagonal jump captures for a marked stack. Regular top disks move forward only; crowned top disks move in either diagonal direction.
- Annotation uses homogeneous `point_set` witnesses: stack centers for control and capture counts, and empty-cell centers for destination counts. Empty annotation is valid for zero-answer cases.
- Active default tasks:
  - `task_games__tower_draughts_board__controlled_stack_count`
  - `task_games__tower_draughts_board__marked_stack_capture_count`
  - `task_games__tower_draughts_board__marked_stack_destination_count`

### `ultimate_tictactoe`
- Visual grammar: Ultimate Tic-Tac-Toe board with nine small Tic-Tac-Toe boards, local X/O marks, drawn boards, and optional highlighted local-board answer options. Winning lines are not pre-drawn.
- Visual styles combine shared games-domain panel backgrounds, sampled fonts, unit-size/layout jitter, post-image noise, and five scene-local board styles (`classic_grid`, `soft_marker`, `paper_grid`, `neon_board`, `tournament_board`).
- Reasoning coverage: macro status counting across small boards, macro immediate-win board counting, and local winning/blocking move selection inside one highlighted small board.
- Annotation uses homogeneous `bbox_set`: matching small-board boxes for status and macro-threat counts, and the selected empty cell plus two supporting line cells for local tactic labels.
- Active default tasks:
  - `task_games__ultimate_tictactoe__line_completion_move_label`
  - `task_games__ultimate_tictactoe__macro_threat_board_count`
  - `task_games__ultimate_tictactoe__small_board_status_count`

### `minesweeper`
- Visual grammar: opened Minesweeper number grid with hidden cells and optional flags.
- Visual styles use the shared game panel treatment/palette layer for the canvas, while classic, soft, outlined, notebook, dark, and retro Minesweeper board styles stay scene-local for cell and clue readability.
- Rendering samples the role-aware font family for clue numbers, uses unit-size jitter with a canvas that follows the resolved board size, and applies layout jitter before annotation projection.
- Reasoning coverage: local forced-mine counting, local forced-safe counting, marked-clue remaining mine count, hidden-cell reveal outcome selection, and satisfied-clue counting.
- Calibrated board size support is `4..8` for the scene overall; the forced-cell
  task uses `4..5` and outlines the relevant opened clue cell(s) to keep local
  deduction legible.
- Annotation uses homogeneous `bbox_set` witnesses over counted cells for forced-cell and satisfied-clue counting. The remaining-mine task uses the marked opened number cell bbox as the minimal witness for the clue being evaluated. The reveal-outcome task uses `keyed_bbox_set_map` for the marked hidden cell plus supporting clue and flag cells.
- Active default tasks:
  - `task_games__minesweeper__forced_cell_count`
  - `task_games__minesweeper__remaining_mine_count_value`
  - `task_games__minesweeper__reveal_outcome_label`
  - `task_games__minesweeper__satisfied_clue_count`

### `minigolf`
- Visual grammar: Mini-golf putting course with a ball, a hole, obstacles, and short starting-direction shot cues.
- Visual styles use the shared game panel treatment/palette layer for the canvas, while classic, desert, neon, garden, and blueprint course palettes stay scene-local for obstacle and fairway readability.
- Rendering samples the role-aware font family for obstacle and shot labels and applies layout jitter before annotation projection.
- Reasoning coverage: extrapolating a short cue to its first obstacle and choosing the numbered cue whose banked path reaches the hole.
- Annotation uses `point_set` for the target obstacle center in first-hit queries and `point_pair_set` for the selected visible dashed cue segment in path-label queries.
- Active default tasks:
  - `task_games__minigolf__first_obstacle_label`
  - `task_games__minigolf__shot_path_label`

### `minecraft`
- Visual grammar: Minecraft-like isometric cube terrain with ore-topped visible cube stacks, marked paths, labeled mining routes, and a highlighted left-to-right stack line for reachability.
- Visual styles use the shared game panel treatment/palette layer for the canvas, while grass, desert, snow, cave, and mesa block-world themes stay scene-local for terrain and ore readability.
- Rendering samples the role-aware font family for route labels, uses unit-size jitter with a canvas that follows the resolved world size, applies layout jitter before annotation projection, and contrast-checks rendered route colors against terrain/theme anchors.
- Reasoning coverage: top-ore stack counting, height-constrained reachable ore counting, stack-height condition counting, plus route-cost aggregation over named mining routes; route-cost scenes show 2 to 3 labeled routes.
- Annotation uses homogeneous `point_set` witnesses at top-cube centers for counted stacks and selected-route obstacle blocks. Route-cost annotation is empty when the named route has zero cost.
- Active default tasks:
  - `task_games__minecraft__reachable_ore_stack_count`
  - `task_games__minecraft__resource_route_cost`
  - `task_games__minecraft__stack_height_condition_count`
  - `task_games__minecraft__top_ore_stack_count`

### `battleship`
- Visual grammar: Battleship board with the five-ship fleet (`Line 5`, `Line 4`, `Line 3`, `Square 2x2`, `L 3`), red hit markers, miss markers, and a side fleet-shape panel.
- Visual styles use the shared game panel treatment/palette layer for canvas and surrounding chrome, while the Battleship grid and fleet panel keep classic blue, soft, outlined, navy, radar, and paper palettes for ship/hit readability.
- Reasoning coverage: whole-ship status counts, named-ship hit/unhit cell counts, and last-cell reconstruction from a hidden-ship tracking grid. Whole-ship status queries count sunk or partially hit ships. Named-ship cell-status queries count hit or unhit cells inside one displayed fleet shape. Last-cell label queries hide ship bodies, show candidate labels `A-F`, and ask for the only unhit cell of the not-yet-sunk ship.
- Annotation uses `keyed_point_set_map` for whole-ship status counts and homogeneous `point_set` witnesses at counted cell centers for named-ship cell-status counts. Last-cell label annotation is a one-point `point_set` at the selected answer cell center.
- Active default tasks:
  - `task_games__battleship__last_ship_cell_label`
  - `task_games__battleship__ship_cell_status_count`
  - `task_games__battleship__ship_status_count`

### `nine_mens_morris`
- Visual grammar: Nine Men's Morris board.
- Visual styles use the shared game panel treatment/palette layer for canvas and surrounding chrome, while classic, soft, outlined, wood-panel, slate, and parchment Morris boards stay scene-local for line/piece readability.
- Rendering samples the role-aware font family for board labels, uses unit-size jitter with a canvas that follows the resolved board size, and applies layout jitter before annotation projection.
- Reasoning coverage: all-piece mill membership counts and empty completion-point counts.
- Annotation uses homogeneous `point_set` witnesses at counted piece centers or empty board-point centers.
- Active default tasks:
  - `task_games__nine_mens_morris__mill_completion_point_count`
  - `task_games__nine_mens_morris__pieces_in_mill_count`

### `pacman`
- Visual grammar: Pac-Man style maze with a visible Pac-Man marker, ghosts, normal pellets, labeled or scored bonus items, and a highlighted route.
- Visual styles use the shared game panel treatment/palette layer for the canvas, while classic, neon, paper, terminal, and pastel Pac-Man maze palettes stay scene-local for route, wall, pellet, item, and ghost readability.
- Rendering samples the role-aware font family for item labels, uses unit-size jitter with a canvas that follows the resolved maze size, and applies slack-based layout jitter before annotation projection.
- Reasoning coverage: route pellet counting, route counting before the first ghost, first labeled item reached along a route, and score summing over route collectibles.
- Annotation uses object-center `point_set` witnesses for counted pellets, selected bonus items, scored route collectibles, and the stop ghost in the before-ghost query.
- Active default tasks:
  - `task_games__pacman__next_item_label`
  - `task_games__pacman__path_pellet_count`
  - `task_games__pacman__pellet_count_before_ghost`
  - `task_games__pacman__route_score_value`

### `pinball_table`
- Visual grammar: tilted pinball playfield with one ball, either a straight launch cue or a full drawn scoring path, flippers, slingshots, rails, bumpers, lanes, and labeled/scored targets.
- Source layout: migrated scene package at `trace/tasks/games/pinball_table/`, with one public task file per objective and scene-local helpers under `trace/tasks/games/pinball_table/shared/`.
- Answer candidates are labeled or scored bumpers, drop targets, rollover lanes, and standup targets; flippers, rails, posts, and slingshots are decorative playfield structure.
- Visual styles use the shared game panel treatment/palette layer for the canvas, while classic, blueprint, neon, carnival, and paper table styles stay scene-local for table/object readability.
- Rendering uses sampled readout fonts, slack-based layout jitter before annotation projection, and contrast-guarded trajectory colors against table and canvas colors.
- Reasoning coverage: first labeled object hit by extending the shown straight launch cue, and score summing over a full drawn ball path that reaches the bottom edge and may include side/top ricochets or target rebounds.
- Annotation uses object-center witnesses: one selected-object `point_set` center for the first-hit task, and an ordered `point_sequence` of scored-target hit centers for the score-value task. Repeated target hits repeat the same center in the sequence.
- Active default tasks:
  - `task_games__pinball_table__first_hit_object_label`
  - `task_games__pinball_table__path_score_value`

### `irregular_link_board`
- Visual grammar: irregular point-and-link movement board with variable missing links, a marked piece, and blocker pieces on board points.
- Visual styles include five board/piece themes (`woodcut`, `ink_diagram`, `garden_cloth`, `night_lines`, `parchment`) layered over shared games/puzzles panel-scene treatments.
- Rendering uses unit-size jitter, dynamic canvas sizing, fractional layout jitter, post-image noise, and a contrast-safe ring plus X overlay for the marked piece.
- Reasoning coverage: count empty adjacent destination points reachable from the marked piece by one drawn link, and count legal jump-over capture destinations where the marked piece jumps over an adjacent opposing piece and lands on the empty point immediately beyond it.
- Annotation uses homogeneous `point_set` witnesses at the centers of legal empty destination points; zero-count cases use an empty point set.
- Active default tasks:
  - `task_games__irregular_link_board__capture_move_count`
  - `task_games__irregular_link_board__marked_piece_destination_count`

### `platformer`
- Visual grammar: side-scroller platformer level with a player character, platforms, hazards, coins, printed-value bonus items, and dashed jump arcs.
- Visual styles include day, cave, neon, snow, and sunset palettes.
- Reasoning coverage: extrapolating a partial jump arc to a landing platform, counting coins along a shown jump arc, and summing score values for collectibles touched by a jump arc.
- Annotation uses the landing platform bbox for landing labels and collectible-center points for count and score-value tasks.
- Active default tasks:
  - `task_games__platformer__collectible_count`
  - `task_games__platformer__jump_collectible_score_value`
  - `task_games__platformer__jump_landing_label`

### `pool`
- Source layout: scene package at `trace/tasks/games/pool/` with one public task module per objective contract.
- Visual grammar: pool table with cue ball, numbered object balls, six pockets, and optional marked shot indicators.
- Visual styles include classic green cloth, tournament-blue cloth, burgundy cloth, charcoal cloth, and light-rail tables.
- Reasoning coverage: current-player group counting and blockers on a marked two-segment shot.
- Annotation uses ball-center `point_set` witnesses for group-ball counts and for balls blocking either marked shot segment.
- Active default tasks:
  - `task_games__pool__blocking_ball_count`
  - `task_games__pool__group_ball_count`

### `radial_hunt_board`
- Visual grammar: Pretwa-inspired radial point-and-line board with three concentric circles, three diameters, a marked piece, and opposing pieces on playable points.
- Visual styles include five board/piece themes (`ink_rings`, `carved_wood`, `temple_cloth`, `night_gold`, `chalk_circle`) layered over shared games/puzzles panel-scene treatments.
- Rendering uses unit-size jitter, dynamic canvas sizing, fractional layout jitter, post-image noise, and a contrast-safe ring plus X overlay for the marked piece.
- Reasoning coverage: count adjacent empty destinations reachable along one circle/diameter segment, and count jump-over capture landing points along the same circle or diameter line.
- Annotation uses homogeneous `point_set` witnesses at legal destination or capture landing centers; zero-count cases use an empty point set.
- Active default tasks:
  - `task_games__radial_hunt_board__capture_move_count`
  - `task_games__radial_hunt_board__marked_piece_destination_count`

### `reversi`
- Visual grammar: Reversi board state.
- Visual styles include classic green boards, wood-framed boards, slate boards, blue boards, and outlined boards.
- Reasoning coverage: legal moves, corner moves, marked-move flip counts, and queried-color frontier-disc counts.
- Annotation uses destination-square `bbox_set` witnesses for legal move counts, and disc-center `point_set` witnesses for marked-move flip counts and frontier-disc counts.
- Active default tasks:
  - `task_games__reversi__frontier_disc_count`
  - `task_games__reversi__legal_destination_count`
  - `task_games__reversi__marked_move_flip_count`

### `rhythm`
- Visual grammar: rhythm-game falling-note lanes with lane numbers and a bottom hit line.
- Visual styles include arcade, neon, paper, dark, and pastel lane/playfield palettes layered over shared games/puzzles panel-scene treatments.
- Lane labels and the hit-line marker sample one deterministic font family from the readout font pool; layout jitter shifts the whole lane grid before annotation projection.
- Reasoning coverage: timing-window note counting, color-filtered timing-window counting, most-arriving lane selection, and earliest-arriving lane selection.
- Annotation uses homogeneous note `bbox_set` witnesses: counted notes for hit-window queries and selected-lane/earliest-note witnesses for lane-choice queries.
- Active default tasks:
  - `task_games__rhythm__lane_color_hit_count`
  - `task_games__rhythm__lane_hit_count`
  - `task_games__rhythm__earliest_hit_lane_label`
  - `task_games__rhythm__most_hits_lane_label`

### `racing_track`
- Visual grammar: top-down single-lane loop racing tracks with a checkered finish line, direction arrow, and labeled cars.
- Visual styles include asphalt, rally, neon, blueprint, and paper racing themes layered over shared games/puzzles panel-scene treatments.
- Prompt contract: distance is measured along the track in the arrow direction, not as straight-line image distance.
- Annotation uses selected-object center points for label-selection and count tasks.
- Active default tasks:
  - `task_games__racing_track__ahead_object_count`
  - `task_games__racing_track__finish_distance_extremum_label`

### `rule_override_board`
- Visual grammar: multiple small game-board panels; the rule is stated in the prompt, not rendered as a visual card.
- Visual styles use the shared game panel treatment/palette layer for the canvas and five scene-local board styles for the mini-boards.
- The board group uses unit-size variation and slack-fraction layout jitter before annotation projection; board labels sample one deterministic font family from the readout font pool.
- Reasoning coverage: result counting under the prompt-stated rule, split into line-pattern outcomes and piece-count outcomes over 4 to 6 mini-boards.
- Annotation uses homogeneous mini-board `bbox_set` witnesses for counted wins or losses; the annotation cardinality is the answer.
- Active default tasks:
  - `task_games__rule_override_board__line_result_count`
  - `task_games__rule_override_board__piece_result_count`

### `snake`
- Visual grammar: Snake game board with a yellow head, connected body cells, red food, gray wall cells, and a square grid.
- Visual styles include classic, neon, forest, paper, and candy board palettes layered over shared games/puzzles panel-scene treatments.
- Option labels and game-over cards sample one deterministic font family from the readout font pool; unit-size and layout jitter are recorded before annotation projection.
- Reasoning coverage: safe-direction counting with wall cells as unsafe blockers, fixed-obstacle shortest path length to food, plus planned 3 to 5 move simulation against image-visible point or `GAME OVER` options. Option-letter answers are only used where the option labels are drawn in the image.
- Annotation uses homogeneous board-cell `bbox_set` witnesses: safe destination cells for immediate-move counts, one shortest path from head to food for food-path length, and traversed head-path cells for planned-move option selection. The option letter is the answer but not the prompt-facing annotation.
- Active default tasks:
  - `task_games__snake__path_outcome_option_label`
  - `task_games__snake__safe_direction_count`
  - `task_games__snake__shortest_food_path_length`

### `sixteen_soldiers`
- Visual grammar: expanded alquerque-style Sixteen Soldiers board with a 5 by 5 center and two triangular extensions; pieces move and capture along the drawn line graph.
- Visual styles include five board/piece themes (`ground_court`, `ink_court`, `cloth_board`, `slate_court`, `sand_court`) layered over shared games/puzzles panel-scene treatments.
- Rendering uses unit-size jitter, dynamic canvas sizing, fractional layout jitter, and a contrast-safe ring plus X overlay for marked-piece queries.
- Reasoning coverage: adjacent empty destination counting and immediate jump-capture counting for one marked piece.
- Annotation uses homogeneous `point_set` witnesses: empty destination-point centers for movement, or capturable opponent-piece centers for immediate captures. Capture landing points are retained in trace metadata.
- Active default tasks:
  - `task_games__sixteen_soldiers__marked_piece_capture_count`
  - `task_games__sixteen_soldiers__marked_piece_destination_count`

### `space_shooter`
- Visual grammar: retro space-shooter playfield with vertical lane guides, labeled or scored enemy ships, falling enemy shots, shields or asteroids, a player ship, and bottom lane pads.
- Visual styles combine shared games-domain panel backgrounds, sampled enemy-label fonts, layout jitter, and neon, deep-space, vector, amber, or terminal playfield palettes.
- Generation currently samples `4..8` lanes and `10..16` enemy ships for the denser queries, with count-style targets in `1..5`. Clear-shot queries use one foreground enemy per target lane plus blockers to keep the obstruction judgment readable; the safe-lane query uses a sparse upper enemy backdrop so the bottom-pad shot/asteroid state stays visually primary.
- Reasoning coverage: unobstructed enemy lanes, clear-shot score summing, projectile alignment with the player, lowest-enemy threat labeling, and safe bottom-lane counting.
- Annotation uses homogeneous `bbox_set` witnesses: counted or scored enemy ships for clear shots, counted enemy shots for player-lane projectiles, the selected enemy ship for the lowest-threat label, and counted bottom lane pads for safe lanes.
- Active default tasks:
  - `task_games__space_shooter__clear_shot_count`
  - `task_games__space_shooter__clear_shot_score_value`
  - `task_games__space_shooter__highest_threat_label`
  - `task_games__space_shooter__projectile_intercept_count`
  - `task_games__space_shooter__safe_lane_count`

### `snakes_ladders`
- Visual grammar: 5 x 5, 6 x 6, or 7 x 7 numbered serpentine Snakes and Ladders board with one token, visible snakes, visible ladders, and a side panel for die or planning information.
- Visual styles combine shared games-domain panel backgrounds, sampled fonts, layout jitter, and classic, paper, neon, pastel, or wood board palettes.
- Annotation uses `keyed_bbox_map` for role-bound move-outcome witnesses (`start_square`, `end_square`) and `bbox_set` annotation for final-square and special-square witnesses.
- Reasoning coverage: one-die final-square simulation, short-horizon highest-final-square planning over `1..2` chosen die rolls, and visible ladder/snake start counts ahead of the token.
- Active default tasks:
  - `task_games__snakes_ladders__best_roll_value`
  - `task_games__snakes_ladders__move_outcome_value`
  - `task_games__snakes_ladders__special_square_count`

### `sliding_block`
- Visual grammar: sliding-block board with a red target block, other labeled rectangular blocks, and an exit arrow or labeled final-board options.
- Visual styles reuse the existing tray/grid/paper board variants with unit-size jitter and prompt-facing annotation projected after final layout.
- Implementation uses games/shared helpers for style, layout/unit-size jitter, sampling, drawing, and annotation artifacts; it must not import from `trace/tasks/puzzles/shared/`.
- Public annotation stays as homogeneous `bbox_set`: blocker-count tasks mark blocking blocks, and move-result tasks mark moved original blocks plus the correct option panel.
- Reasoning coverage: direct blocker counting along the target block's exit path and final-board selection after a short ordered slide sequence.
- The movable-block count task hides the exit-path cue and asks for non-target blocks that can legally slide at least one cell.
- Active default tasks:
  - `task_games__sliding_block__sliding_block_blocker_count`
  - `task_games__sliding_block__movable_block_count`
  - `task_games__sliding_block__sliding_block_move_result_label`

### `sokoban`
- Visual grammar: Sokoban-style grid with walls, player/start and goal cells, boxes, targets, and labeled move-sequence or board-cell options.
- Visual styles reuse the existing warehouse, paper-grid, and cool-room variants with unit-size jitter and prompt-facing annotation projected after final layout.
- Implementation lives in `trace/tasks/games/sokoban/<objective_contract>.py` with scene-local helpers under `trace/tasks/games/sokoban/shared/`; it must not keep compatibility imports or copies under `trace/tasks/puzzles/shared/`.
- Public annotation stays as homogeneous `bbox_set`: path queries mark the selected option panel, while box/target relation queries mark selected option-lettered board cells.
- Reasoning coverage: path validity, shortest path selection, nearest box/target selection, and Manhattan-distance rank selection over same-letter box-target pairs.
- Active default tasks:
  - `task_games__sokoban__box_target_manhattan_rank_label`
  - `task_games__sokoban__nearest_counterpart_label`
  - `task_games__sokoban__path_validity_sequence_label`
  - `task_games__sokoban__shortest_path_sequence_label`

## 4) Shared helper placement
1. Cross-domain integer-support balancing lives in `trace/tasks/shared/support_sampling.py`.
2. Games visual defaults, style/theme handling, and axis sampling belong under `trace/tasks/games/shared/visual_defaults.py`, the `trace/tasks/games/shared/style.py` facade plus sibling `style_*.py` family modules, and `trace/tasks/games/shared/sampling.py`.
3. Shared nonsemantic renderer placement helpers belong in `trace/tasks/games/shared/layout.py`.
4. Do not use fixed-query wrapper adapters for migrated games tasks. Each public task file must own its objective-specific sampling, answer binding, annotation binding, prompt slots, and task trace rather than narrowing a shared multi-objective generator.
5. For migrated scene packages, game-specific scene helpers belong under `trace/tasks/games/<scene_id>/shared/` unless at least two different scenes import them.
6. Legacy `trace/tasks/games/shared/*_common.py` and `trace/tasks/games/shared/*_scene.py` files should be moved into the owning scene package during migration when they are scene-local. Do not add new scene-local helpers under domain `shared/`.
7. Game readable-text wrappers belong in `trace/tasks/games/shared/text.py`; do not duplicate text contrast/font-color selection in individual scene renderers.
8. Common public annotation artifact construction belongs in `trace/tasks/shared/annotation_artifacts.py`; game task modules should use it for repeated `bbox_set`, `point_set`, and `point_pair_set` `annotation_gt` plus `projected_annotation` payloads.
9. Domain shared helpers must be scene-neutral and identity-free. Do not add public task ids, query ids, objective names, registered task classes, final `TaskOutput` construction, or scene-specific generation programs to `trace/tasks/games/shared/`.
10. New helper code should start scene-local. Promote it to `trace/tasks/games/shared/` only after confirmed multi-scene reuse or an explicitly approved game-family boundary such as chess-family piece glyphs.
11. Migrated games scenes must not import `resolve_games_query_id` from `trace/tasks/games/shared/sampling.py`; public task files should use the repo-global query-selection helper and translate selected query ids into semantic arguments locally.
