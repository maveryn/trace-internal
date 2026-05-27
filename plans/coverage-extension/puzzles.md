# Puzzles Coverage Extension

## Scope

This note tracks puzzle-domain coverage gaps found from the external benchmark
failure analysis, then records candidate changes for `puzzles`.

Current working conclusion after reconciling against the active registry: the
puzzle domain already covers a large share of the relevant benchmark patterns
through `71` default puzzle tasks across automata, cell boards, clocks, logic
grids, Raven matrices, nonograms, matchsticks, Star Battle, Tents, dice and
spinner probability, cube/voxel stacks, solid-view projections, polyominoes,
paper folding, overlays, Rubik-style cubes, Sokoban, tangram, sliding blocks,
topology/string/maze/pipe/voxel-ladder puzzles, color gradients, word searches,
music notation, and counterfactual board grids. The first-wave semantic gaps
called out in earlier versions of this note are now either implemented or
intentionally skipped as too narrow/overlapping. There is no remaining puzzle
task from this note that clearly needs implementation now. Any additional work
should be evaluation-driven: a consolidated word-search route extension only if
word-path misses recur, and scene-specific style packs only if robustness
rather than task coverage is the observed gap.

Relevant benchmark cues:

- GameQALite: rule simulation over games, automata, logic grids, and board
  states; especially 2D Turing machine, Langton's Ant, voxel reconstruction,
  3D maze navigation, Star Battle, Sokoban, color-gradient, word-search,
  Tangram, Rubik, Tents, Sudoku, cards, chess, Snake, Minecraft, and marble
  chain games.
- MathVision: contest-style visual math and puzzle diagrams, visible object
  and missing-block counts, point/selection grounding, arithmetic constraints,
  balance-like sketches, and spatial relation/order/path questions.
- MathVista TestMini: math-targeted diagram reasoning, clocks, abstract
  counting scenes, object-sequence completion, and point/answer selection.
- BLINK: IQ-test visual patterns and jigsaw/missing-corner correspondence.
- MMMU-ProVis: Music questions are entirely sheet-music images, with local
  qwen25vl7b accuracy at `7/35 = 0.20` on the sampled Music rows. The visible
  patterns are pitch/interval/transposition, key/scale, chord/harmony,
  meter/rhythm/duration, notation symbols, and instrument-tuning style staff
  reading.

Boundary rule:

- Put a task in `puzzles` when the source of truth is a synthetic hidden rule,
  hidden state, transformation, assembly relation, or constraint system over
  puzzle objects.
- Put it in `games` when named game mechanics are primary, especially cards,
  chess variants, Snake, Minecraft-like mechanics, Zuma/marble chains, and
  other game-state rules.
- Put it in `geometry` when a mathematical theorem, coordinate system, formula,
  or measurement object is the verifier source of truth.
- Put it in `physics` when weights, torque, forces, mechanics, or physical
  state changes determine the answer.
- Put it in `three_d` when the primary reasoning is camera/object spatial
  relation in a rendered 3D world.
- Put it in `illustrations` or `icons` when object recognition, object counting,
  attributes, or simple visual correspondence are primary rather than a puzzle
  rule.

## Current Puzzle Surface

Registry audit: all `70` registered `task_puzzles__*` tasks are
default-enabled. Closest active scene families:

- `agent_automaton_grid` and `life_automaton_grid`: final pose, cell-flip
  counts, future-grid selection, and future population counts.
- `cell_board`: color-region counts, reachability counts, path distance, and
  symmetry-violation counts.
- `logic_grid`, `raven_matrix`, `nonogram_grid_panel`, `star_battle_grid`,
  `tents_grid`, and `matchstick_arrangement`: missing-cell, rule-completion,
  constraint, matrix, and matchstick option/value tasks.
- `dice_probability_panel` and `spinner_probability_panel`: visible probability
  computations with reduced-fraction answers.
- `single_analog_clock` and `clock_face_collection`: clock readout and clock
  comparison.
- `fold`, `fold_cut`, `overlay`, `cube_voxel_puzzle`, `polyomino`,
  `rubiks_cube`, `sokoban_grid`, `tangram`, and `sliding_block_board`:
  spatial transform, assembly, cube/voxel, solid-view, block, and grid
  movement puzzles.
- `bead_loop`, `string_topology`, `maze_grid`, `pipe_flow_grid`, and
  `voxel_ladder_maze`: cyclic order, component counting, maze reachability,
  pipe repair, and isometric voxel-ladder route/count tasks.
- `color_gradient_grid`: color-gradient completion and violation tasks.
- `word_search_grid`: word location, letter counting, and present-word count.
- `counterfactual_board_grid`: board row/column/line-count counterfactuals.
- `music_staff_notation`: pitch/interval, key/scale, chord/harmony, and
  meter/rhythm/symbol tasks over synthetic sheet-music staff notation.

## Identified Issues

### Z1. Automaton And Grid-State Transition Breadth

Status: `implemented`

GameQALite contains several explicit automaton and grid-transition mechanics.
Current TRACE now has Life-style automaton tasks and turning-agent tasks, so
the earlier "Life is a gap" benchmark note should be treated as stale. The
remaining gap is narrow. TRACE now includes one distinct machine-style
automaton task rather than several more grid-transition tasks.

Closest existing tasks:

- `proposal:puzzles/automaton/agent_final_pose_label`
- `proposal:puzzles/automaton/agent_cell_flip_count`
- `proposal:puzzles/automaton/life_future_grid_label`
- `proposal:puzzles/automaton/life_population_count`
- `proposal:puzzles/automaton/turing_written_symbol_count`
- `proposal:puzzles/cell/board_reachability_count`

Interpretation:

- Current turning-agent tasks already cover Langton-like local turn/update
  simulation, and current Life tasks already cover cellular grid transitions.
- Do not add separate Langton or generic rule-table tasks unless benchmark
  misses later show a specific need.
- The added Turing-machine style written-symbol count covers the remaining
  tape/head/state simulation case that was visually and semantically distinct
  from both existing automaton scenes.

### Z2. Contest-Style Arithmetic Puzzle Diagrams

Status: `implemented / covered`

MathVision includes many small puzzle diagrams where arithmetic is embedded in
shapes, paths, flowers, ropes, missing numbers, or equal-sum constraints. Some
examples overlap geometry or physics, but many are pure puzzle constraints.

Closest existing tasks:

- `proposal:puzzles/logic/arithmetic_constraint_value`
- `proposal:puzzles/logic/cryptarithm_digit_value`
- `proposal:puzzles/logic/operator_grid_value`
- `proposal:puzzles/logic/number_wall_value`
- `proposal:puzzles/logic/raven_count_progression_label`
- `proposal:puzzles/logic/matchstick_number_transform_label`
- `proposal:puzzles/probability/dice_pair_event_value`
- `proposal:puzzles/counterfactual/board_grid_count`
- `proposal:physics/mechanics/missing_weight_balance_value`
- `proposal:geometry/measurement/composite_area_value`

Interpretation:

- TRACE now covers this through one `arithmetic_constraint_puzzle` scene with
  four public task units: base equal-side/cluster/window constraints,
  cryptarithm digit puzzles, operator-grid puzzles, and number-wall puzzles.
- This should not become open-ended math QA.
- Additional number-flower or symbolic-equation microtasks are not needed now;
  they would mostly duplicate the active arithmetic-constraint scene unless
  post-evaluation errors show a repeated uncovered pattern.
- True lever/weight mechanics should remain in `physics`.

### Z3. Voxel, Solid-View, And 3D Reconstruction Puzzle Expansion

Status: `covered / skip new tasks for now`

GameQALite has 3D reconstruction questions over voxel structures and target
projections. MathVision also includes missing-block, brick, and cube-count
style failures. TRACE now has cube-stack, change-count, painted-face,
visible-projection, projection-match, and projection-consistency tasks under
the shared `cube_voxel_puzzle` scene.

Closest existing tasks:

- `proposal:puzzles/spatial/cube_count`
- `proposal:puzzles/spatial/cube_structure_change_count`
- `proposal:puzzles/spatial/cube_painted_face_count`
- `proposal:puzzles/spatial/cube_visible_projection_count`
- `proposal:puzzles/spatial/cube_projection_match_label`
- `proposal:puzzles/spatial/cube_projection_consistency_label`

Interpretation:

- This is a good fit for `puzzles/spatial`, not `three_d`, when the task is a
  symbolic voxel/projection puzzle rather than camera-scene spatial relation.
- Missing-to-complete and removed/extra cube counts are already covered by
  `proposal:puzzles/spatial/cube_structure_change_count` through its internal
  `missing_to_complete_cuboid_count` and `removed_cube_count` query keys.
- Projection match and projection consistency are already public default
  tasks. Do not re-add them as new voxel task ids.
- Do not add `minimum_added_count` now. It is narrower than the active cube
  structure-change and projection-consistency tasks, and does not justify a new
  task until post-evaluation misses show a specific reconstruction gap.

### Z4. Route, Turn, And Path Puzzle Variants

Status: `covered for current wave / skip broad route scene`

MathVision has route-following and path-choice questions, including examples
where the solver follows turn instructions or reads letters along one side of a
route. GameQALite includes 3D maze navigation. TRACE has cell-board paths,
Sokoban, maze-grid reachability, voxel-ladder route puzzles, and map navigation
in `pages`, but not all route-instruction puzzle forms.

Closest existing tasks:

- `proposal:puzzles/cell/board_path_distance`
- `proposal:puzzles/topology/maze_exit_reachability`
- `proposal:puzzles/topology/voxel_ladder_route_label`
- `proposal:puzzles/topology/voxel_ladder_route_count`
- `proposal:puzzles/spatial/sokoban_path_sequence_label`
- `task_pages__map__navigation_label`

Interpretation:

- The implemented `voxel_ladder_maze` scene covers the distinct GameQALite-style
  isometric 3D maze cue using a blue START cube, red GOAL cube, TRACE named-color
  checkpoints, and black ladders. It exposes checkpoint-sequence, unreachable
  checkpoint, reachable-checkpoint count, and shortest-ladder count queries.
  The route-label branch uses visible color-swatch sequences rather than tiny
  checkpoint letters.
- Do not add a generic `route_instruction_puzzle` now. Final-cell, turn-count,
  route-option, and letter-sequence tasks overlap with existing cell-board
  paths, maze reachability, voxel-ladder route queries, Sokoban path sequences,
  word-search paths, and page-map navigation.
- A surface-net route task is the only potentially distinct idea, because it
  would require following a path across folded cube/net adjacency. Keep it as a
  later benchmark-driven option, not a current implementation target.

### Z5. Piece Assembly, Jigsaw, And Visual Correspondence

Status: `covered enough / skip synthetic-piece microtasks`

BLINK has jigsaw and missing-corner patterns, while MathVision has assembly
tasks involving cards, tower parts, patterns, and missing pieces. TRACE already
has polyomino missing-region, tangram, paper fold/cut, overlay, Raven transform, color-pattern,
and illustration-domain missing-patch/jigsaw tasks. Earlier versions of this
note treated synthetic puzzle-piece correspondence as a possible gap, but it is
now considered too narrow and overlapping for a new puzzle task.

Closest existing tasks:

- `proposal:puzzles/spatial/polyomino_missing_region_piece_label`
- `proposal:puzzles/spatial/tangram_missing_piece_label`
- `proposal:puzzles/spatial/tangram_contact_count`
- `proposal:puzzles/spatial/overlay_result_label`
- `proposal:puzzles/spatial/paper_fold_result_label`
- `proposal:puzzles/spatial/paper_fold_cut_result_label`
- `proposal:illustrations/visual/missing_patch_label`

Interpretation:

- Current polyomino, tangram, fold/cut, overlay, Raven transform, color
  pattern, and illustration jigsaw/missing-patch tasks already cover the broad
  correspondence space.
- Do not add corner-match, same-shape-after-transform, two-piece completion, or
  pattern-patch-position tasks now. They are too specific relative to current
  coverage and would mostly duplicate existing assembly/transform contracts.
- Natural semantic correspondence and functional object correspondence from
  BLINK should not be forced into puzzles; those are better suited to a future
  multi-image correspondence scene in `illustrations` or `three_d`.

### Z6. Word-Grid And Letter-Path Puzzle Breadth

Status: `covered enough / benchmark-driven optional`

GameQALite includes word-search questions. TRACE now has explicit word-search
tasks, so the raw benchmark gap is mostly covered. Remaining useful extensions
would involve route-like word paths, crossing words, direction counts, and
hidden-word variants.

Closest existing tasks:

- `proposal:puzzles/word/search_location_label`
- `proposal:puzzles/word/search_letter_count_value`
- `proposal:puzzles/word/search_present_word_count`
- `proposal:puzzles/cell/board_path_distance`

Interpretation:

- This is not a current implementation target because the core word-search
  family exists.
- If benchmark review later shows repeated misses, prefer one consolidated
  word-search route/property task with internal `query_id` branches rather than
  four separate task ids.

### Z7. Color And Visual Pattern Puzzle Breadth

Status: `covered / partial`

GameQALite hue/color-gradient puzzles map well to current color-gradient tasks.
BLINK IQ-test rows also overlap with Raven matrix and icon/geometry
transformation tasks, but can include broader visual analogies.

Closest existing tasks:

- `proposal:puzzles/visual/color_gradient_completion_label`
- `proposal:puzzles/visual/color_gradient_violation_cell_label`
- `proposal:puzzles/logic/raven_analogical_transform_label`
- `proposal:puzzles/logic/raven_spatial_transform_label`
- `proposal:icons/pattern/grid_color_violation`

Interpretation:

- Current coverage is reasonably strong.
- Additional work should be targeted: broader Raven rule families, option
  styles, or color-pattern grid variants if solve-rate or benchmark evidence
  justifies it.

### Z8. Named Game Mechanics That Should Stay In `games`

Status: `boundary-sensitive`

GameQALite contains many named game mechanics that are puzzle-like but should
not automatically move into `puzzles`: Klondike, FreeCell, chess variants,
Snake, Minecraft, Zuma, Sudoku, rhythm games, and other board/video/card game
states.

Closest existing tasks:

- `task_games__sudoku__marked_cell_value`
- `task_games__snake__safe_direction_count`
- `proposal:games/cards/solitaire_legal_move_label`
- `proposal:games/chess/marked_piece_capture_count`
- `task_games__minecraft__resource_route_cost_value`

Interpretation:

- Keep `puzzles` focused on abstract puzzle rules and transformations.
- Add named-game variants under `games` unless the task is deliberately
  abstracted into a domain-neutral puzzle scene.

### Z9. Puzzle Scene Style, Density, And Benchmark-Like Presentation

Status: `not a task gap / robustness candidate`

Benchmark puzzle images often look like contest workbook panels, game UI
screens, labeled option sheets, or scanned puzzle pages. Current TRACE puzzle
scenes are generally clean and controlled.

Closest existing tasks:

- all current puzzle tasks.

Interpretation:

- Style variation can help, but puzzle tasks are often geometry-sensitive.
- Any new style wrappers must not move grid coordinates, option geometry,
  maze topology, cube geometry, fold/overlay coordinates, word-grid cells, or
  evidence semantics.
- For puzzles, prefer scene-specific style packs over broad decorative clutter.

### Z10. Sheet-Music Notation Reasoning

Status: `implemented`

MMMU-ProVis includes a full Music subject where all inspected rows use sheet
music. The local benchmark run sampled 35 Music rows and missed 28, for
`0.20` accuracy. These examples mostly ask symbolic notation questions rather
than broad music history or audio reasoning.

Implemented coverage:

- `proposal:puzzles/notation/pitch_interval_label`
- `proposal:puzzles/notation/key_scale_label`
- `proposal:puzzles/notation/chord_harmony_label`
- `proposal:puzzles/notation/meter_rhythm_label`

Interpretation:

- This belongs in `puzzles/notation` for the first wave because the source of
  truth is a symbolic staff-notation rule system with synthetic metadata.
- Do not create a full `music` domain unless future coverage expands beyond
  staff notation into a broader renderer/world model.
- Keep audio, music history, performer recognition, and real score-OCR out of
  scope unless answers are generated and verifier-grounded.

## Candidate Changes

### R1. Add One Machine-Style Automaton Task

Decision: implemented.

Issues addressed:

- Z1. Automaton and grid-state transition breadth.

Implementation:

- Extended the existing automaton infrastructure with one compact
  tape/head/state scene.
- Added task:
  - `proposal:puzzles/automaton/turing_written_symbol_count`
- Do not add Langton-style tasks or generic rule-table future-grid tasks now;
  current agent and Life automata already cover those nearby reasoning modes.

### R2. Add Arithmetic Constraint Puzzle Diagrams

Decision: implemented for the first-wave scalar-value coverage.

Issues addressed:

- Z2. Contest-style arithmetic puzzle diagrams.
- Some MathVision point/selection and missing-number failures.

Implementation:

- Added these tasks under scene `arithmetic_constraint_puzzle`:
  - `proposal:puzzles/logic/arithmetic_constraint_value`
  - `proposal:puzzles/logic/cryptarithm_digit_value`
  - `proposal:puzzles/logic/operator_grid_value`
  - `proposal:puzzles/logic/number_wall_value`
- Internal query branches cover equal-side sums, paired cluster relations,
  consecutive-window sums, hidden arithmetic digits, letter-digit equations,
  row/column clue grids, operation tables, adjacent-rule walls, and number
  pyramids.
- These branches now sample structural dimensions rather than using a fixed
  shape: digit width/addend count, letter/equation count, grid/table shape, and
  wall/pyramid base width vary within config ranges.
- Operation-table and number-wall rule text is intentionally not printed in the
  prompt or image; the model must infer the repeated arithmetic relation from
  visible entries.
- Final answers are scalar integers with `bbox_set` evidence on the puzzle
  panel plus the marked target.
- Option-letter arithmetic can be considered later as a separate task only if
  coverage analysis shows enough remaining gap.
- If a diagram uses torque, force, or physical balance, route it to `physics`
  instead.

### R3. Expand Voxel Projection And Reconstruction Puzzles

Decision: skip for now; current cube coverage is sufficient.

Issues addressed:

- Z3. Voxel, solid-view, and 3D reconstruction puzzle expansion.

Implementation decision:

- Current cube-count, structure-change, visible-projection, projection-match,
  and projection-consistency tasks cover the important voxel reconstruction
  surface.
- Do not add separate `voxel_missing_count` or `voxel_extra_count` tasks; those
  are already covered by the structure-change task.
- Do not duplicate projection-match or projection-consistency task ids; both
  are already active public tasks.
- Do not add `proposal:puzzles/spatial/cube_minimum_added_count` unless later
  benchmark errors show a repeated minimum-reconstruction failure not covered
  by the current tasks.

### R4. Add Route And Turn Instruction Puzzle Variants

Decision: skip broad route-instruction scene for now.

Issues addressed:

- Z4. Route, turn, and path puzzle variants.

Implementation decision:

- Do not add `proposal:puzzles/topology/route_final_cell_label`,
  `proposal:puzzles/topology/route_turn_count_value`,
  `proposal:puzzles/topology/route_valid_path_label`, or
  `proposal:puzzles/topology/route_letter_sequence_label`; these overlap with
  cell-board path distance, maze-grid reachability, Sokoban path sequences,
  word-search paths, and page-map navigation.
- Keep `proposal:puzzles/topology/surface_net_path_label` only as a later
  benchmark-driven idea if folded-net route failures remain after current
  cube/Rubik/spatial coverage is evaluated.

### R5. Add Piece Assembly And Correspondence Variants

Decision: skip for now; current assembly/correspondence coverage is sufficient.

Issues addressed:

- Z5. Piece assembly, jigsaw, and visual correspondence.

Implementation decision:

- Do not add `proposal:puzzles/spatial/piece_corner_match_label`,
  `proposal:puzzles/spatial/piece_same_shape_after_transform_label`,
  `proposal:puzzles/spatial/two_piece_completion_label`, or
  `proposal:puzzles/spatial/pattern_patch_position_label`; they are too specific
  and overlap with active polyomino, tangram, fold/cut, overlay, Raven
  transform, color-pattern, and illustration jigsaw/missing-patch tasks.
- Keep natural semantic/functional correspondence out of puzzles unless the
  objects are synthetic puzzle pieces with explicit part metadata.

### R6. Extend Word-Search And Letter-Path Tasks

Decision: defer; not a current task target.

Issues addressed:

- Z6. Word-grid and letter-path puzzle breadth.

Implementation decision:

- Do not add separate word-search direction/crossing/hidden-path/missing-letter
  task ids now.
- If benchmark errors later justify this, add one consolidated task such as
  `proposal:puzzles/word/search_route_property` with internal query branches for
  direction count, crossing-word count, hidden-path label, or missing-letter
  value.

### R7. Add Puzzle-Specific Style Packs Carefully

Decision: defer; style robustness only.

Issues addressed:

- Z9. Puzzle scene style, density, and benchmark-like presentation.

Implementation idea:

- Add scene-specific style packs such as contest worksheet, puzzle magazine,
  game UI panel, notebook, lab/grid board, or option-card sheet.
- Keep style variation non-semantic and geometry-preserving.
- Record style/chrome/distractor metadata in `render_spec`.
- Avoid broad clutter that can obscure small cells, fold marks, maze walls,
  option labels, color gradients, or word-grid letters.

### R8. Add Sheet-Music Notation Puzzle Scene

Decision: implemented for MMMU-ProVis Music coverage.

Issues addressed:

- Z10. Sheet-music notation reasoning.

Implementation:

- Added scene `music_staff_notation` under `puzzles/notation`.
- Added tasks:
  - `proposal:puzzles/notation/pitch_interval_label`
  - `proposal:puzzles/notation/key_scale_label`
  - `proposal:puzzles/notation/chord_harmony_label`
  - `proposal:puzzles/notation/meter_rhythm_label`
- Internal query branches cover note names, intervals, pitch equivalence,
  transposition checks, key signatures, scale validation, scale degrees, chord
  qualities, roman numerals, inversions, dominant counts, time signatures, bar
  counts, duration matching, simple/compound meter, and articulation symbols.
- First-wave scope intentionally uses synthetic staff notation rather than
  open score-OCR, audio, or broad music-domain knowledge.

## Genuine Remaining Missing Candidates

After checking the current default puzzle task set, there are no first-wave
semantic additions that clearly need implementation now. The table below is
kept only as a deferred, evaluation-driven watch list:

| Priority | Deferred item | Possible future contract | Current decision |
|---|---|---|---|
| 1 | word-path extension | one consolidated `proposal:puzzles/word/search_route_property` with query branches for direction count, crossing-word count, hidden-path label, or missing-letter value | Defer. Current word-search tasks cover location, letter count, and present-word count. Add only if evaluation shows repeated word-path failures. |
| 2 | puzzle-specific style packs | no new task ids; scene-level style packs for selected active scenes | Defer. This is a rendering robustness pass, not a missing task. It must preserve geometry, evidence, and readability. |

## Suggested First Wave

1. Done: Turing-machine style written-symbol-count task.
2. Done: arithmetic-constraint puzzle diagrams.
3. Done: sheet-music notation puzzle scene for MMMU-ProVis Music coverage.
4. Skip for now: broad route/turn instruction tasks, synthetic-piece
   correspondence microtasks, and cube minimum-added reconstruction.
5. No additional first-wave puzzle task remains from this note. Remaining work
   should be evaluation-driven: only add a consolidated word-search route task
   or scene-specific style packs if benchmark errors show a repeated gap.

## Remaining Open Questions

1. For GameQALite named mechanics, which ones should become `games` extensions
   instead of `puzzles` extensions?
2. How much worksheet/game-UI style variation is safe for puzzles without
   harming small-cell readability and evidence projection?
3. After current puzzle evaluation, do word-search errors justify a single
   consolidated word-path/direction/crossing extension?
