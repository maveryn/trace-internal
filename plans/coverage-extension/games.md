# Games Coverage Extension

## Scope

This note tracks game-domain coverage gaps found from external benchmark
failure analysis, then records candidate changes for `games`.

Current registry snapshot: `93` active public game tasks across `36`
game-state scenes. The active game surface covers 2048, Backgammon,
Battleship, Bingo, Bowling, Brick Breaker, Bubble Shooter, cards, Checkers,
Chess, Chess Variants, Connect Four, Crossing, Darts, Dominoes, Dots and Boxes, Go, Hex,
Marble Chain/Zuma-style insertion, Match-3/Jewel swap, Minesweeper, Minigolf,
Minecraft-like block worlds, Nine Men's Morris, Pac-Man, Platformer, Pool,
Reversi, Rhythm, Snake, Snakes and Ladders, Solitaire, Space Shooter, Sudoku,
Tetris, and Ultimate Tic-Tac-Toe.

Most external benchmark pressure comes from GameQALite. The first games
coverage wave added the previously missing Solitaire tableau, marble-chain,
match-3, Ultimate Tic-Tac-Toe, visible-rule-card chess-variant, and Tetris coverage. A few optional
extensions remain for richer FreeCell/Klondike, rhythm, Minecraft inventory,
and benchmark-style UI wrappers.

Relevant benchmark cues:

- GameQALite: named board/card/video-game state reasoning, especially
  Klondike/FreeCell, chess variants, Zuma/marble chain, Ultra Tic-Tac-Toe,
  Jewel/match-3, rhythm games, Sudoku, Snake, Minecraft, and related board
  state questions.
- MathVision: occasional card, board, route, and visual assembly examples, but
  most of those are better handled by `puzzles`, `geometry`, or
  `illustrations` unless the named game mechanics are primary.
- BLINK: not primarily a games benchmark; its jigsaw/IQ/correspondence
  patterns map better to `puzzles`, `illustrations`, `icons`, or `three_d`.

Boundary rule:

- Put a task in `games` when the image depicts a recognizable game artifact and
  the answer depends on game-specific visible rules or game-state mechanics.
- Put it in `puzzles` when the task is an abstract puzzle, hidden-rule grid,
  automaton, folding/assembly problem, voxel/projection puzzle, or
  Sokoban-like state puzzle already owned by the puzzle domain.
- Put it in `geometry` when the answer is a measurement, theorem, coordinate,
  or formula result rather than a game rule.
- Put it in `three_d` when the primary reasoning is camera/object spatial
  relation in a rendered 3D world.
- Put it in `pages` when the task is about UI controls, menu commands, or page
  layout rather than the game state itself.
- Put open-world sports trivia, real game screenshots, and factual knowledge
  outside TRACE unless the answer is grounded in visible synthetic metadata.

## Current Games Surface

Active public game scenes and task counts:

| Scene | Tasks | Status |
|---|---:|---|
| `2048` | 2 | active |
| `backgammon` | 3 | active |
| `battleship` | 2 | active |
| `bingo` | 2 | active |
| `bowling` | 2 | active |
| `brick_breaker` | 2 | active |
| `bubble_shooter` | 3 | active |
| `cards` | 7 | active |
| `checkers` | 3 | active |
| `chess` | 5 | active |
| `chess_variant` | 2 | active |
| `connect_four` | 2 | active |
| `crossing` | 3 | active |
| `darts` | 3 | active |
| `dominoes` | 2 | active |
| `dots_and_boxes` | 2 | active |
| `go` | 3 | active |
| `hex` | 2 | active |
| `marble_chain` | 2 | active |
| `match3` | 2 | active |
| `minecraft` | 3 | active |
| `minesweeper` | 2 | active |
| `minigolf` | 2 | active |
| `nine_mens_morris` | 1 | active |
| `pacman` | 2 | active |
| `platformer` | 2 | active |
| `pool` | 3 | active |
| `reversi` | 2 | active |
| `rhythm` | 2 | active |
| `snake` | 2 | active |
| `snakes_ladders` | 2 | active |
| `solitaire` | 3 | active |
| `space_shooter` | 4 | active |
| `sudoku` | 4 | active |
| `tetris` | 2 | active |
| `ultimate_tictactoe` | 2 | active |

Scene-family grouping:

- Tile/board games: `2048`, `bingo`, `battleship`,
  `connect_four`, `dots_and_boxes`, `go`, `hex`,
  `minesweeper`, `nine_mens_morris`, `reversi`,
  `snakes_ladders`, `sudoku`, and `ultimate_tictactoe`.
- Piece-move games: `checkers`, `chess`, `chess_variant`, and `backgammon`.
- Card and tile games: `cards`, `solitaire`, and `dominoes`.
- Arcade/action game abstractions: `brick_breaker`,
  `bubble_shooter`, `crossing`, `marble_chain`,
  `match3`, `pacman`, `platformer`, `rhythm`,
  `snake`, `space_shooter`, and `tetris`.
- Sports/aiming games: `bowling`, `darts`, `minigolf`, and
  `pool`.
- Block-world game abstraction: `minecraft`.

## Status By Coverage Issue

### A1. Klondike And FreeCell-Style Solitaire Layouts

Status: `implemented baseline / optional remaining`

GameQALite has a large card-state slice for Klondike and FreeCell. TRACE now
has a dedicated `solitaire` scene with three public tasks:

- `task_games__solitaire__foundation_ready_count`
- `task_games__solitaire__move_legality_label`
- `task_games__solitaire__tableau_sequence_count`

This covers fully visible tableau/foundation move-state reasoning. Remaining
optional work would be richer FreeCell-specific free-cell/home-cell layouts,
stock/waste mechanics, or hidden-card conventions. Those should be added only
if we want deeper Solitaire coverage; the first-wave gap is closed.

### A2. Chess Variants And Nonstandard Movement Rules

Status: `implemented`

GameQALite includes chess capture/range variants and Pyramid Chess-like
states. TRACE has strong standard chess coverage:

- `proposal:games/chess/marked_piece_move_count`
- `proposal:games/chess/marked_piece_capture_count`
- `task_games__chess__player_capture_piece_count`
- `task_games__chess__check_attacker_count`
- `task_games__chess__king_escape_square_count`

Implemented public tasks:

- `proposal:games/chess/variant_marked_piece_move_count`
- `proposal:games/chess/variant_marked_piece_capture_count`

The separate `chess_variant` scene uses token-only W/B pieces and a
visible movement rule card so nonstandard movement rules do not overload the
standard `chess` tasks.

### A3. Zuma / Marble Chain Insertion Mechanics

Status: `implemented`

Implemented as `marble_chain`:

- `task_games__marble_chain__shot_effect_value`
- `task_games__marble_chain__shot_direction_label`

The current version uses a central-shooter / curved-chain representation and
single-step removal without recursive cascades. This closes the first-wave
GameQALite Zuma-style gap.

### A4. Match-3 / Jewel Swap Mechanics

Status: `implemented`

Implemented as `match3`:

- `task_games__match3__best_swap_label`
- `task_games__match3__swap_effect_value`

The current version uses immediate one-swap clearing only. Long cascade
planning remains intentionally out of scope.

### A5. Tic-Tac-Toe And Ultimate Tic-Tac-Toe

Status: `implemented`

Implemented as `ultimate_tictactoe`:

- `task_games__ultimate_tictactoe__small_board_status_count`
- `task_games__ultimate_tictactoe__local_tactic_label`

The current version covers macro small-board status counting and local
winning/blocking move selection. It intentionally avoids drawing win-line
overlays or status-color-coded board backgrounds so the model has to infer
three-in-a-row status from marks.

Standard Tic-Tac-Toe is not separately implemented because Ultimate
Tic-Tac-Toe is the benchmark-relevant version and provides richer visual and
reasoning structure.

### A6. Rhythm-Game Variants

Status: `covered / optional remaining`

TRACE has `rhythm`:

- `task_games__rhythm__hit_window_count`
- `task_games__rhythm__lane_choice_value`

Core timing-window and lane-selection reasoning is covered. Optional extensions
could add hold-note handling, simultaneous-note counts, or combo-window
variants if targeted benchmark review shows the current tasks are too narrow.

### A7. Minecraft-Like Block World Task Breadth

Status: `covered / optional remaining`

TRACE has `minecraft`:

- `task_games__minecraft__ore_block_count`
- `task_games__minecraft__tunnel_clearance_count`
- `task_games__minecraft__resource_route_cost_value`

Current coverage is good for visible counting and route-cost reasoning.
Remaining optional benchmark-style variants would be crafting/resource
combinations, inventory panels, tool-choice rules, or multi-step route
planning. These are lower priority than the chess-variant gap.

### A8. Game UI And Option-Presentation Variety

Status: `partially covered / ongoing style work`

GameQALite examples often have game-like UI framing, answer options,
coordinate labels, score strips, rule panels, or state panels. TRACE game
scenes now have broader shared rendering styles and several scene-specific
option panels, but most remain intentionally clean and synthetic.

Guidance:

- Add UI wrappers only where they do not alter board geometry, evidence bboxes,
  rule semantics, or visible cell/piece readability.
- Prefer scene-specific UI/HUD elements over a broad decorative layer.
- Long rule text should remain controlled and short; verifier truth must stay
  in metadata, not OCR of verbose instructions.

### A9. Benchmark Families That Should Stay Outside Games

Status: `routed elsewhere / boundary-sensitive`

Several GameQALite rows are called games but are better owned elsewhere in
TRACE.

Routing:

- Life, Turing machine, and Langton's Ant: `puzzles/automaton`.
- Star Battle, Tents, Sokoban, Rubik, Tangram, word search, color-gradient,
  voxel reconstruction, and 3D maze puzzle variants: `puzzles`.
- General 3D spatial relation: `three_d`.
- Natural-image sports/game screenshots or factual trivia: out of scope unless
  fully synthetic and visibly grounded.

The games doc should not duplicate the puzzle expansion wave. When a benchmark
names a game but the renderer contract is abstract puzzle state, keep
ownership with the domain that already owns that contract.

## Candidate Changes

### G1. Add Explicit Klondike And FreeCell Layout Tasks

Decision: `implemented baseline; optional expansion only`

Implemented public tasks:

- `task_games__solitaire__foundation_ready_count`
- `task_games__solitaire__move_legality_label`
- `task_games__solitaire__tableau_sequence_count`

Optional future tasks, only if Solitaire needs deeper coverage:

- `proposal:games/solitaire/freecell_home_ready_count`
- `proposal:games/solitaire/freecell_legal_move_label`
- `proposal:games/solitaire/stock_waste_move_label`
- `proposal:games/solitaire/hidden_card_exposure_count`

Keep hidden-card and stock randomness out unless the prompt explicitly states
the visible assumptions and the verifier metadata is unambiguous.

### G2. Add Rule-Card Chess Variant Tasks

Decision: `implemented`

Issues addressed:

- A2. Chess variants and nonstandard movement rules.

Implemented as `chess_variant`:

- `proposal:games/chess/variant_marked_piece_move_count`
- `proposal:games/chess/variant_marked_piece_capture_count`

The current first pass covers straight-range, diagonal-range,
straight-or-diagonal-range, and leaper `2+1` / `3+1` rule families with local
destination/capture evidence.

### G3. Add Marble Chain / Zuma Scene

Decision: `implemented`

Implemented public tasks:

- `task_games__marble_chain__shot_effect_value`
- `task_games__marble_chain__shot_direction_label`

No immediate follow-up is required unless we later want recursive cascade
queries.

### G4. Add Match-3 / Jewel Swap Scene

Decision: `implemented`

Implemented public tasks:

- `task_games__match3__best_swap_label`
- `task_games__match3__swap_effect_value`

No immediate follow-up is required unless we later want cascade or special-gem
queries.

### G5. Add Tic-Tac-Toe / Ultimate Tic-Tac-Toe Scene

Decision: `implemented`

Implemented public tasks:

- `task_games__ultimate_tictactoe__small_board_status_count`
- `task_games__ultimate_tictactoe__local_tactic_label`

No separate standard Tic-Tac-Toe scene is planned unless benchmark review shows
that Ultimate Tic-Tac-Toe is not enough.

### G6. Extend Rhythm Lanes Only If Needed

Decision: `lower-priority optional candidate`

Candidate tasks:

- `proposal:games/rhythm/hold_note_count`
- `proposal:games/rhythm/combo_window_count`
- `proposal:games/rhythm/simultaneous_lane_count`

Only add these if current rhythm tasks miss a benchmark slice or become too
narrow after final coverage review.

### G7. Add Scene-Specific Benchmark UI Wrappers

Decision: `ongoing optional style work`

Implementation idea:

- Add optional UI framing for specific game scenes: score strips, short rule
  cards, move-history boxes, candidate-move panels, and simple game HUD
  elements.
- Keep UI text short and trace-generated.
- Never let decorative UI elements add alternative valid answers or occlude
  evidence-bearing cells/pieces.

### G8. Extend Minecraft With Inventory/Crafting Only If Needed

Decision: `lower-priority optional candidate`

Candidate tasks:

- `proposal:games/minecraft/inventory_craftable_count`
- `proposal:games/minecraft/tool_choice_label`
- `proposal:games/minecraft/resource_recipe_value`

These are recognizable game mechanics, but they introduce UI/inventory panels
and more text-like rule metadata. Defer unless benchmark review shows a clear
remaining Minecraft gap.

## Completed First Wave

1. `solitaire`: added three Solitaire tableau/foundation tasks.
2. `marble_chain`: added two Zuma-like shot direction/effect tasks.
3. `match3`: added two Jewel-style one-swap tasks.
4. `ultimate_tictactoe`: added two Ultimate Tic-Tac-Toe tasks.
5. `chess_variant`: added two visible-rule-card chess-variant tasks.
6. `tetris`: added two Tetris next-piece/drop-result tasks.

## Remaining Work

High priority:

1. Calibrate the newly added Tetris tasks and decide whether any branch needs
   difficulty tuning.

Optional / lower priority:

1. Extend Solitaire with explicit FreeCell or stock/waste mechanics.
2. Extend rhythm with hold-note, simultaneous-note, or combo-window tasks.
3. Extend Minecraft with inventory/crafting/tool-choice mechanics.
4. Add scene-specific UI/HUD wrappers where they improve benchmark resemblance
   without adding OCR dependence or evidence ambiguity.

Resolved questions:

1. Klondike/FreeCell baseline is represented by `solitaire`; deeper
   FreeCell or stock/waste mechanics are optional future work.
2. Marble-chain and match-3 are full games scenes, not puzzle-grid variants.
3. Ultimate Tic-Tac-Toe is the retained Tic-Tac-Toe coverage; standard
   Tic-Tac-Toe is omitted for now.
4. Tetris is owned by `games`, not `puzzles`, because the tasks depend on
   falling-piece lock, row-clear, and stack-evaluation rules.

Open question:

1. Whether future Tetris coverage should add next-piece/hold mechanics, or keep
   the current one-drop scope for cleaner evidence and calibration.
