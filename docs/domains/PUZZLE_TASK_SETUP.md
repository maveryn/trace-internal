# Puzzle Task Setup

## Purpose
Capture the active contract for the `puzzles` domain.

This is the active puzzles-domain contract. For cross-domain coverage rollups, use the generated inventory in `docs/ACTIVE_TASK_INVENTORY.md` instead of repeating scene/task inventories elsewhere.

## Active families
1. Current active `task_group` values:
   - `automaton`
   - `cell_board`
   - `clock`
   - `counterfactual`
   - `logic`
   - `notation`
   - `probability`
   - `spatial`
   - `topology`
   - `visual`
   - `word`
2. Current active task ids and scene counts are generated in
   `docs/ACTIVE_TASK_INVENTORY.md`.

## Family contract
1. Puzzle families are hidden-rule / hidden-variable reasoning families, not generic icon grids or mini tables.
2. The active automaton family includes agent-turning, cellular-life, and compact tape-machine simulations. Agent tasks ask for final pose or update-count values under visible state-transition rules; Life tasks ask for future-grid options or future live-cell counts under the visible neighbor rule; the tape-machine task asks for a fixed-step written-symbol count under a visible transition table.
3. The active `cell_board` scene includes rectangular board tasks for visible color-attribute counts, color-region counts, path distance, reachability counts, and symmetry-violation counts.
4. The active counterfactual family includes counterfactual board-count puzzles under the `counterfactual_board` scene. These ask for counts on synthetic boards whose familiar visual priors may be intentionally shifted; evidence is projected from the counted board regions/cells rather than from a hidden canonical rule.
5. The active logic family currently includes missing grid-cell option selection, Raven-style matrix tasks, nonogram clue/grid tasks, matchstick arrangement tasks, arithmetic-constraint diagram tasks, tents clue-grid tasks, and Star Battle region-grid tasks. Logic answers are `option_letter` or `integer`, with evidence projected from option panels, clue rails, marked lines, candidate cells, arithmetic diagram panels, marked unknown nodes/cells/symbols, marked trees, marked regions, or marked row/column clues.
6. The active probability family currently includes visible-top dice probability tasks and equal-sector spinner probability tasks with reduced-fraction string answers and tray/panel-level `bbox_set` evidence.
7. The active clock family includes single-clock offset readout and multi-clock comparison tasks, with local evidence on clock hands or the winning clock face.
8. The active spatial family currently mixes option-based transform-result puzzles, cube/voxel structure and projection puzzles, cube surface/net folding and rolling puzzles, a static 2D polyomino missing-region puzzle, Rubik-style cube-net lookup/counting/transform puzzles, Sokoban-style grid movement/path/relation puzzles, sliding-block puzzles, and tangram-style polygon-piece matching/counting puzzles. Prompt-facing evidence stays local to the winning option image/panel, visible cube/voxel structures, cube-net reference regions, ordered option-plus-target-region boxes, moved or blocking board pieces, or query-grid cells that should be filled.
9. The active visual family includes color-gradient anomaly and completion puzzles, with evidence projected from the violating swatch or the blank-plus-option swatches.
10. The active topology family currently includes cyclic-order loop label tasks, one string-component count task with query branches, wall-maze reachability tasks, pipe/conduit 2x2 flow-repair option selection, and voxel-ladder route/count puzzles.
11. The active word family includes row-and-column labeled word-search grids for word location, letter counting, and word-bank presence counting. Evidence is projected from selected option cards, word chips, and ordered grid-cell paths.
12. The active notation family includes synthetic sheet-music staff tasks for pitch/interval reading, key/scale reasoning, chord/harmony labels, and meter/rhythm/symbol reasoning. Evidence is projected from marked notes, chords, key signatures, bars, time signatures, articulation marks, and option cards.
13. Public puzzle task ids are narrow task units. Semantic query families that remain inside a task are recorded as `query_id` or trace parameters, not as public sampling units.
14. Puzzle visual diversity should stay non-semantic: shared panel treatments, palettes, task-local chrome, unit-size jitter, and evidence-safe layout slack are allowed when recorded in render metadata. Do not add changed option geometry, stronger spatial noise, or decorative marks that can affect maze/cube/fold/color-pattern/word-search/notation/relation-diagram reasoning.
15. Shared puzzle background variants live in `configs/domains/puzzles/base.yaml` and are inherited by active automaton, cell-board, counterfactual, logic, notation, probability, clock, spatial, topology, visual, and word task groups through the puzzle visual-default loader.
16. Puzzle scenes built from repeated cells or units should use explicit render-only unit-size jitter. Try for at least a `2x` min-to-max span first, but use a narrower documented range when readability, scene fit, or evidence integrity requires it. This applies to cell-board tiles, counterfactual boards, logic/nonogram/Star Battle/tents grids, maze and pipe cells, automaton cells, word-search cells, music-staff note spacing, polyomino unit squares, Rubik stickers, sliding/Sokoban board cells, and cube/voxel unit cubes. Board-size or option-count variation alone is not enough; evidence bboxes must be derived after the sampled cell or unit size is fixed.
17. Broad style primitives may live in domain-level config/helpers, but concrete rendering variation is applied scene by scene. Each puzzle scene owns how palettes, strokes, board chrome, option cards, labels, unit-size jitter, and layout slack map onto its visual grammar and evidence.
18. Do not use a blind domain-level recolor/layout pass for puzzle scenes; visual variation must preserve semantic contrast and must not alter the answer, evidence, hidden rule, or verifier contract.

## Automaton tasks
1. Active task ids:
   - `task_puzzles__agent_automaton__agent_final_pose_label`
   - `task_puzzles__agent_automaton__agent_cell_flip_count`
   - `task_puzzles__life_automaton__life_future_grid_label`
   - `task_puzzles__life_automaton__life_population_count`
   - `task_puzzles__turing_tape__turing_written_symbol_count`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - agent final-pose records `query_id=binary_rule_final_pose|three_state_rule_final_pose`,
   - agent update-count records `query_id=target_state_flip_count|marked_region_flip_count` and records the sampled turning rule in trace metadata,
   - Life future-grid records `query_id=one_step_future_grid|two_step_future_grid`,
   - Life population-count records `query_id=total_live_count|marked_region_live_count`,
   - Turing written-symbol count records `query_id=written_symbol_count`.
3. Supported `scene_variant` values:
   - `clean_grid`
   - `lab_panel`
   - `notebook_grid`
4. Answer contract:
   - final-pose and future-grid tasks use `answer_gt.type = option_letter`,
   - update-count, population-count, and Turing written-symbol tasks use `answer_gt.type = integer`.
5. Evidence contract:
   - `evidence_gt.type = bbox_set`,
   - final-pose evidence contains the starting-agent box followed by the selected option box,
   - update-count evidence contains the starting-agent box followed by the marked-region or source-grid box,
   - future-grid evidence contains the source-grid box followed by the selected option box,
   - population-count evidence contains the source-grid or marked-region box,
   - Turing written-symbol evidence contains the starting tape/head panel and transition-table boxes.
6. Scene contract:
   - agent automaton scenes show a state grid plus an arrow marker for the starting pose,
   - binary rules use light versus colored state cells, with the actual non-semantic cell palette sampled by the scene style; three-state rules draw state labels `0`, `1`, and `2`,
   - `agent_automaton` samples non-semantic treatment and palette axes through the global shared panel-style layer, using the shared 20-treatment and 20-palette puzzle/game canvas registry,
   - Life scenes use dark cells for alive cells and light cells for empty cells,
   - Turing scenes show the starting tape, head position, start state, step count, queried symbol, and complete transition table,
   - option tasks render exactly five labeled option panels.
7. Trace contract:
   - `scene_ir.entities` and `render_map.item_bboxes_px` expose grid, target, agent, and option bboxes,
   - `execution_trace` stores the visible rule branch, grid dimensions, initial grid, simulation step count, answer value, supporting item ids, and query-specific symbolic fields.

## Cell-board tasks
1. Active task ids:
   - `task_puzzles__cell_board__attribute_count`
   - `task_puzzles__cell_board__color_region_count`
   - `task_puzzles__cell_board__path_distance`
   - `task_puzzles__cell_board__reachability_count`
   - `task_puzzles__cell_board__symmetry_violation_count`
2. Public contract:
   - each task uses public `domain=puzzles` and `scene_id=cell_board`,
   - semantic branches are recorded in `query_id`,
3. Implementation location:
   - active implementations live under `trace/tasks/puzzles/cell_board/`,
   - active defaults live under `configs/domains/puzzles/cell_board_*.yaml`,
   - active prompt bundles live under `prompts/puzzles/cell_board_*/`.
4. Board contract:
   - each instance renders exactly one dense rectangular board,
   - private coordinates are zero-based `(row, col)` with `(0, 0)` at the top-left tile, `row` increasing downward, and `col` increasing rightward,
   - scene/render metadata records `tiling_type=rectangular_tiling`, board dimensions, tile dimensions, and board origin,
   - in-bounds board coordinates must name exactly one tile; tasks may mark tiles as blocked, empty, colored, highlighted, or target-bearing.
5. Visual contract:
   - do not draw row/column coordinate labels or per-cell coordinate text by default,
   - row/column labels are allowed only when the task query explicitly uses visible row or column numbers, such as `task_puzzles__cell_board__attribute_count`,
   - avoid external graph-paper/grid backgrounds because they create a competing coordinate system,
   - use the shared puzzle/game panel-style renderer for non-semantic
     background, panel chrome, grid-line, and placement variation,
   - preserve task-semantic tile colors exactly when prompts refer to colors,
   - movement-style tasks use square cells so equal-cost horizontal and vertical moves look visually uniform.
6. Evidence contract:
   - public evidence is projected into image pixels after final layout,
   - unordered tile sets use tile-center `point_set`,
   - ordered paths or trajectories use tile-center `point_sequence`,
   - grid coordinates and stable tile ids stay private in trace metadata,
   - optional review/debug `bbox_set` projections may be retained in `projected_evidence` but are not the active public evidence contract.
7. Trace contract:
   - `scene_ir.entities` keeps one `tile_cell` entity per board coordinate,
   - `render_spec` or `render_map` records enough board geometry to project tile centers deterministically,
   - `witness_symbolic` stores the private supporting cells/paths,
   - `projected_evidence` stores the final pixel-space points used by the public evidence payload.

## Clock tasks
1. Active task ids:
   - `task_puzzles__analog_clock__offset_readout`
   - `task_puzzles__clock_collection__compare`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - readout tasks record `query_id=minutes_after|minutes_before`,
   - compare records `query_id=earliest_time_label|latest_time_label`.
3. Supported `scene_variant` values:
   - `classic`
   - `minimal`
   - `outline`
4. Answer contract:
   - readout tasks answer with HH:MM or HH:MM:SS strings,
   - compare answers with the winning clock label string.
5. Evidence contract:
   - readout evidence is a `bbox_set` over visible clock hands,
   - compare evidence is a one-box `bbox_set` over the winning clock face.

## Logic grid completion tasks
1. Active task ids:
   - `task_puzzles__logic_grid__grid_uniqueness_completion_label`
   - `task_puzzles__logic_grid__grid_king_non_touch_label`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - uniqueness records `query_id=grid_uniqueness_completion`,
   - king non-touch records `query_id=king_non_touch`.
3. Supported semantic parameter axes:
   - uniqueness uses `uniqueness_query=axis_uniqueness|row_and_column_uniqueness`
   - `axis_uniqueness` samples `uniqueness_axis=row|column`
4. Supported `scene_variant` values:
   - `logic_strip`
   - `logic_card`
   - `logic_outline`
5. Required slots:
   - `answer_gt.type = option_letter`
6. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - exactly one bbox for the winning option panel
7. Scene contract:
   - one square logic grid per image,
   - board size ranges from `5x5` through `7x7` for uniqueness and `3x3` through `5x5` for king non-touch,
   - exactly one board cell shows `?`,
   - exactly six labeled image options (`A..F`) appear below the board,
   - each option panel contains one candidate shape,
   - the king non-touch prompt explicitly states that identical symbols may not touch edge-to-edge or corner-to-corner,
   - the answer is the option letter, not the shape name.
8. Trace contract:
   - `scene_ir.entities` includes `puzzle_logic_cell`, `puzzle_logic_option_panel`, `puzzle_logic_option_label`, and `puzzle_logic_option_symbol_box` entities,
   - `render_map.cell_bboxes_px` stores each board-cell bbox keyed by `cell_id`,
   - `render_map.option_panel_bboxes_px` stores each option-panel bbox keyed by `option_panel_id`,
   - `execution_trace` stores `query_id`, internal replay query fields, `board_values`, `grid_rows`, `symbol_pool`, `query_cell_id`, `query_row_index`, `query_col_index`, `answer_object_type`, `answer_option_label`, `correct_option_index`, `correct_option_panel_id`, `option_specs`, `board_size`, `board_size_range`, `cell_count`, `cell_count_range`, `option_count`, and `solver_trace`,
   - king non-touch also stores `neighbor_coords`, `forced_neighbor_coords`, `forced_neighbor_types`, `query_neighbor_object_types`, and `valid_option_object_types`,
   - prompt-facing evidence is projected from `correct_option_panel_id`, not inferred from pixels.

## Raven matrix logic tasks
1. Active task ids:
   - `task_puzzles__raven_matrix__raven_count_progression_label`
   - `task_puzzles__raven_matrix__raven_spatial_transform_label`
   - `task_puzzles__raven_matrix__raven_set_operation_label`
   - `task_puzzles__raven_matrix__raven_analogical_transform_label`
   - `task_puzzles__raven_matrix__raven_position_progression_label`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - each task records a fixed `query_id`: `count_progression_matrix`, `spatial_transform_matrix`, `set_operation_matrix`, `analogical_transform_matrix`, or `position_progression_matrix`.
3. Supported `scene_variant` values:
   - `raven_strip`
   - `raven_card`
   - `raven_outline`
4. Answer contract:
   - `answer_gt.type = option_letter`
5. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - exactly one bbox for the winning option panel
6. Scene contract:
   - one 3 by 3 visual matrix per image,
   - the lower-right panel shows `?`,
   - exactly six labeled image options (`A..F`) appear below the matrix,
   - matrix/option mini-panels contain attribute icons, count dots, or filled-cell patterns depending on `query_id`,
   - prompt wording stays inductive and does not disclose the active hidden rule family,
   - the Raven prompt renderer uses a generic completion prompt and omits branch-specific task hints,
   - the answer is the option letter, not the rule description.
7. Trace contract:
   - `scene_ir.entities` includes `puzzle_raven_matrix_cell`, `puzzle_raven_option_panel`, `puzzle_raven_option_label`, and `puzzle_raven_option_content_box` entities,
   - `render_map.matrix_cell_bboxes_px` stores each matrix-cell bbox keyed by `cell_id`,
   - `render_map.option_panel_bboxes_px` stores each option-panel bbox keyed by `option_panel_id`,
   - `execution_trace` stores `query_id`, internal replay query fields, `matrix_rows`, `matrix_panel_specs`, `query_cell_id`, `answer_panel_spec`, `answer_option_label`, `correct_option_index`, `correct_option_panel_id`, `option_specs`, `matrix_size`, `cell_count`, `visible_matrix_cell_count`, `option_count`, and `solver_trace`,
   - prompt-facing evidence is projected from `correct_option_panel_id`, not inferred from pixels.

## Nonogram logic tasks
1. Active task ids:
   - `task_puzzles__nonogram__nonogram_line_completion_label`
   - `task_puzzles__nonogram__nonogram_candidate_solution_label`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - task records fixed `query_id=line_completion_label|candidate_solution_label`.
3. Supported `scene_variant` values:
   - `nonogram_classic`
   - `nonogram_card`
   - `nonogram_blueprint`
4. Answer contract:
   - `line_completion_label` and `candidate_solution_label`: `answer_gt.type = option_letter`.
5. Evidence contract:
   - `evidence_gt.type = bbox_set`,
   - line completion evidence contains the marked row clue box, marked row box, and selected row-strip option panel,
   - candidate-solution evidence contains the row-clue rail box, column-clue rail box, and selected candidate panel.
6. Scene contract:
   - one nonogram clue grid per image,
   - grid size defaults to `6x6..9x9`,
   - line/candidate tasks use `4..6` labeled options,
   - partial row-completion scenes mark one row and show known filled/empty cells in that row,
   - candidate-solution scenes show an empty solution grid with row/column clue rails and candidate filled grids.
7. Trace contract:
   - `scene_ir.entities` includes `nonogram`, `nonogram_clue_panel`, `nonogram_clue`, `nonogram_cell`, and optional `nonogram_option_panel` entities,
   - `render_map.item_bboxes_px` stores clue, cell, marked-line, and option-panel bboxes used for evidence,
   - `execution_trace` stores `query_id`, `scene_id`, `scene_variant`, grid dimensions, full grid, display grid, row/column clues, answer value, supporting item ids, option specs when present, and query-specific line/clue fields.

## Matchstick logic tasks
1. Active task ids:
   - `task_puzzles__matchstick__matchstick_loose_endpoint_extremum_label`
   - `task_puzzles__matchstick__matchstick_number_transform_label`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - number transform records `query_id=add_one_stick|remove_one_stick`,
   - loose-endpoint extremum records `query_id=most_loose_endpoints|fewest_loose_endpoints`.
3. Supported `scene_variant` values:
   - `wooden_matches`
   - `colored_rods`
   - `chalk_sticks`
   - `neon_rods`
   - `metal_rods`
4. Answer contract:
   - both tasks use `answer_gt.type = option_letter`.
5. Evidence contract:
   - `evidence_gt.type = bbox_set`,
   - evidence contains one bbox for the selected option panel.
6. Scene contract:
   - number transform shows a Source two-digit number and labeled candidate numbers,
   - loose-endpoint extremum shows six labeled stick arrangements with a unique largest or smallest loose-endpoint count,
   - visual styles change stick material/color/background without changing the option-panel evidence contract.
7. Trace contract:
   - `scene_ir.entities` includes Source and option panel entities for number transform and option panel entities for loose-endpoint extremum,
   - `render_map.item_bboxes_px` stores Source and option-panel bboxes where present,
   - number-transform traces store the Source number, answer number, changed digit index, and added/removed segment keys,
   - loose-endpoint traces store each option edge set, grid size, and per-option loose-endpoint counts.

## Arithmetic-constraint logic task
1. Active task id:
   - `task_puzzles__arithmetic_constraint__arithmetic_constraint_value`
   - `task_puzzles__arithmetic_constraint__cryptarithm_digit_value`
   - `task_puzzles__arithmetic_constraint__operator_grid_value`
   - `task_puzzles__arithmetic_constraint__number_wall_value`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - semantic branches are recorded in `query_id`.
3. Supported `query_id` values:
   - arithmetic constraint: `equal_sum_line_constraint_value`, `paired_cluster_sum_relation_value`, `consecutive_window_sum_value`
   - cryptarithm digit: `hidden_addition_digit_value`, `hidden_subtraction_digit_value`, `letter_digit_value`
   - operator grid: `row_column_total_missing_value`, `operation_table_cell_value`
   - number wall: `addition_wall_missing_value`, `difference_wall_missing_value`, `multiplication_pyramid_value`
4. Supported `scene_variant` values:
   - `constraint_sheet`
   - `constraint_card`
   - `constraint_outline`
5. Answer contract:
   - all branches use `answer_gt.type = integer`.
6. Evidence contract:
   - `evidence_gt.type = bbox_set`,
   - evidence contains the full arithmetic puzzle panel and the marked question-mark node/cell or highlighted query-symbol box.
7. Scene contract:
   - one compact worksheet-style arithmetic diagram per image,
   - equal-side branches draw a triangle/square/pentagon with numbered perimeter nodes and one missing node,
   - paired-cluster branches draw two numbered clusters with a visible sum-relation note,
   - consecutive-window branches draw a strip or arc of numbered cells with one missing cell,
   - cryptarithm branches draw vertical arithmetic or letter-digit equations with one marked target,
   - operator-grid branches draw row/column clue grids or operation tables with one marked target; operation-table rules are inferred from filled cells rather than printed,
   - number-wall branches draw addition walls or multiplication pyramids with one marked brick,
   - number-wall rule text is not printed; the repeated wall/pyramid pattern must be inferred from visible bricks,
   - structural dimensions are sampled per instance: vertical arithmetic varies digit width and addend count, letter puzzles vary letter/equation count, operator grids vary row/column counts, and walls/pyramids vary base width.
8. Trace contract:
   - `scene_ir.entities` includes the arithmetic panel plus branch-specific nodes/cells/symbols,
   - `render_map.item_bboxes_px` stores the puzzle panel and target bboxes used for evidence,
   - `execution_trace.constraint_data` stores the visible values, relation parameters, answer value, and branch-specific solver data.

## Rubik cube-net spatial tasks
1. Active task ids:
   - `task_puzzles__rubiks_net__rubiks_sticker_color_label`
   - `task_puzzles__rubiks_net__rubiks_face_color_count_label`
   - `task_puzzles__rubiks_net__rubiks_move_result_label`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - sticker-color records `query_id=static_sticker_color_label|one_move_sticker_color_label|short_sequence_sticker_color_label`,
   - face-color counting records `query_id=static_face_color_count_label|one_move_face_color_count_label|short_sequence_face_color_count_label`,
   - move-result selection records `query_id=one_move_result_label|two_move_result_label|inverse_sequence_result_label`.
3. Supported `scene_variant` values:
   - `classic_net`
   - `paper_net`
   - `cool_net`
4. Answer contract:
   - all Rubik cube-net tasks use `answer_gt.type = option_letter`,
   - color questions answer with the labeled swatch option, not a free-form color name,
   - count questions answer with the labeled numeric option.
5. Evidence contract:
   - `evidence_gt.type = bbox_set`,
   - prompt-facing evidence contains exactly one bbox for the selected option panel.
6. Scene contract:
   - one unfolded cube net is shown with face labels and a coordinate reference,
   - sticker colors are sampled from the shared TRACE named-color palette and recorded in trace metadata,
   - face coordinates use column increasing left to right and row increasing bottom to top,
   - move sequences use quarter-turn tokens from `U|D|L|R|F|B`, with a prime mark for counterclockwise turns.
7. Trace contract:
   - `scene_ir.entities` includes `rubiks_sticker`, `rubiks_option_panel`, and `rubiks_cube_net` entities,
   - `render_map.sticker_bboxes_px` stores main-net sticker bboxes keyed by face/row/column id,
   - `render_map.option_panel_bboxes_px` stores each answer option bbox,
   - `execution_trace` stores start/final sticker states, sampled face colors, query sequence, option specs, answer option label, and query-specific target sticker or counted sticker ids.

## Sokoban grid spatial tasks
1. Active task ids:
   - `task_puzzles__sokoban__sokoban_path_sequence_label`
   - `task_puzzles__sokoban__sokoban_box_target_relation_label`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - path-sequence records `query_id=shortest_path_sequence_label|valid_path_sequence_label|blocked_path_sequence_label`,
   - box-target relation records `query_id=nearest_target_for_marked_box_label|box_closest_to_marked_target_label|box_target_manhattan_rank_label`.
3. Supported `scene_variant` values:
   - `warehouse_classic`
   - `paper_grid`
   - `cool_room`
4. Answer contract:
   - all Sokoban grid tasks use `answer_gt.type = option_letter`,
   - path answer options are rendered as separate option panels,
   - box-target relation answer options are rendered directly on candidate board boxes, targets, or same-letter box-target pairs.
5. Evidence contract:
   - `evidence_gt.type = bbox_set`,
   - path evidence contains exactly one bbox for the selected option panel,
   - box-target relation evidence contains the selected option-lettered board cell bbox; pair queries contain the box cell bbox followed by the target cell bbox.
6. Trace contract:
   - `scene_ir.entities` includes `sokoban_cell`, `sokoban_box`, `sokoban_target`, `sokoban_player`, `sokoban_option_panel`, and board-letter `sokoban_board_option` entities,
   - `render_map.cell_bboxes_px` stores board cells and `render_map.option_panel_bboxes_px` stores path answer options,
   - `execution_trace` stores walls, boxes, targets, player start, move sequences, path cells, relation distances, option specs, and the selected answer option.

## Tents logic tasks
1. Active task ids:
   - `task_puzzles__tents__tents_missing_tent_cell_label`
   - `task_puzzles__tents__tents_valid_candidate_count`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - task records fixed `query_id=missing_tent_cell_label|valid_candidate_count`.
3. Supported `scene_variant` values:
   - `tents_classic`
   - `tents_card`
   - `tents_blueprint`
4. Supported render-only `palette_variant` values:
   - `garden`
   - `autumn`
   - `lake`
   - `violet`
   - `slate`
5. Answer contract:
   - `missing_tent_cell_label`: `answer_gt.type = option_letter`,
   - `valid_candidate_count`: `answer_gt.type = integer` with support `0..4`.
6. Evidence contract:
   - `evidence_gt.type = bbox_set`,
   - missing-tent evidence contains the selected candidate cell, marked tree, selected row clue, and selected column clue,
   - candidate-count evidence contains the marked tree followed by every legal labeled candidate cell; zero-count cases contain only the marked tree.
7. Scene contract:
   - one partial tents grid per image,
   - grid size defaults to `6x6..8x8`,
   - row and column clues show total tent counts, and visible tents already occupy part of those totals,
   - the no-touch rule forbids tents from touching by edge or corner.
8. Trace contract:
   - `scene_ir.entities` includes `puzzle_tents_panel`, `puzzle_tents_cell`, `puzzle_tents_tree`, `puzzle_tents_tent`, `puzzle_tents_row_clue`, `puzzle_tents_col_clue`, and `puzzle_tents_candidate_cell` entities,
   - `render_map.item_bboxes_px` stores clue, tree, tent, cell, and candidate bboxes used for evidence,
   - `execution_trace` stores `query_id`, `scene_id`, `scene_variant`, `palette_variant`, grid dimensions, row/column clues, marked tree, visible tents, tree cells, candidate specs, legal candidate cells, answer value, and supporting item ids.

## Star Battle logic tasks
1. Active task ids:
   - `task_puzzles__star_battle__star_battle_valid_cell_label`
   - `task_puzzles__star_battle__star_battle_remaining_count`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - the sampled row/column/region query is recorded in `query_id`.
3. Supported `scene_variant` values:
   - `star_battle_classic`
   - `star_battle_pastel`
   - `star_battle_blueprint`
4. Answer contract:
   - `valid_cell_*`: `answer_gt.type = option_letter`,
   - `remaining_valid_cells_*`: `answer_gt.type = integer` with configured support `1..6`.
5. Evidence contract:
   - `evidence_gt.type = bbox_set`,
   - valid-cell evidence contains the selected labeled candidate cell plus the marked region or row when the query is scoped,
   - remaining-count evidence contains the marked row, column, or region followed by every legal cell in that scope.
6. Scene contract:
   - one partial Star Battle grid per image,
   - grid size defaults to `6x6..9x9`,
   - each row, column, and colored region has quota `1`,
   - stars may not touch by edge or corner.
7. Trace contract:
   - `scene_ir.entities` includes `puzzle_star_battle_panel`, `puzzle_star_battle_cell`, `puzzle_star_battle_region`, `puzzle_star_battle_star`, row/column clue entities, and optional candidate cell entities,
   - `render_map.item_bboxes_px` stores clue, region, cell, star, and candidate bboxes used for evidence,
   - `execution_trace` stores `query_id`, `scene_id`, `scene_variant`, grid size, region grid, visible stars, candidate specs, legal cells, scoped legal cells, answer value, and supporting item ids.

## Dice probability tasks
1. Active task ids:
   - `task_puzzles__dice_probability__dice_single_event_value`
   - `task_puzzles__dice_probability__dice_pair_event_value`
   - `task_puzzles__dice_probability__dice_conditional_event_value`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - the sampled probability event is recorded as `query_id`.
3. Supported `scene_variant` values:
   - `dice_tray_clean`
   - `dice_tray_felt`
   - `dice_tray_notebook`
4. Answer contract:
   - `answer_gt.type = string`,
   - answer values are reduced fraction strings such as `"3/8"`.
5. Evidence contract:
   - `evidence_gt.type = bbox_set`,
   - single and conditional evidence contains the full dice tray box,
   - pair evidence contains the full Tray A box followed by the full Tray B box.
6. Scene contract:
   - dice are rendered as individual rounded square dice with visible top-face pips,
   - probability is always over uniformly selecting from the shown dice, not rolling unseen dice,
   - the single task samples parity, threshold, value-set, color-and-value, and color-or-value events,
   - the pair task samples independent one-die selections from Tray A and Tray B with sum, threshold, difference, ordered parity-combo, and color/value events,
   - the conditional task samples one-die selections with image-grounded denominator filters.
7. Trace contract:
   - `scene_ir.entities` includes `dice_tray` and `probability_die` entities,
   - `render_map.die_bboxes_px`, `render_map.tray_bboxes_px`, and `render_map.item_bboxes_px` store die and tray boxes,
   - `execution_trace` stores `query_id`, `scene_id`, `scene_variant`, dice specs, event description, favorable outcome count, total outcome count, reduced fraction answer, tray evidence item ids, and die-level calculation support ids,
   - conditional tasks also store denominator support ids.

## Spinner probability tasks
1. Active task ids:
   - `task_puzzles__spinner_probability__spinner_compound_event_value`
   - `task_puzzles__spinner_probability__spinner_pair_event_value`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - the sampled probability event is recorded as `query_id`.
3. Supported `scene_variant` values:
   - `spinner_clean`
   - `spinner_card`
   - `spinner_notebook`
4. Answer contract:
   - `answer_gt.type = string`,
   - answer values are reduced fraction strings such as `"3/8"`.
5. Evidence contract:
   - `evidence_gt.type = bbox_set`,
   - single-spinner evidence contains the full spinner panel box,
   - pair-spinner evidence contains the full Spinner A panel box followed by the full Spinner B panel box.
6. Scene contract:
   - spinner sectors are equal-probability sectors,
   - single-spinner sectors have a color and a shape marker,
   - pair-spinner sectors are color-only,
   - the single-spinner task samples color, shape, color-and-shape, and color-or-shape events,
   - the pair-spinner task samples independent two-spinner color events such as both target color, at least one target color, and same color.
7. Trace contract:
   - `scene_ir.entities` includes `spinner_panel`, `spinner_sector`, and `spinner_pointer` entities,
   - `render_map.sector_bboxes_px` and `render_map.item_bboxes_px` store sector and panel boxes,
   - `execution_trace` stores `query_id`, `scene_id`, `scene_variant`, sector specs, event description, favorable outcome count, total outcome count, reduced fraction answer, panel evidence item ids, and sector-level calculation support ids.

## Spatial transform result tasks
1. Active task ids:
   - `task_puzzles__paper_fold__paper_fold_result_label`
   - `task_puzzles__paper_fold_cut__paper_fold_cut_result_label`
   - `task_puzzles__overlay__overlay_result_label`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - each task records a fixed `query_id`: `paper_fold_result`, `paper_fold_cut_result`, or `overlay_result`.
3. Supported semantic parameter axes:
   - paper-fold-cut samples `fold_count=1|2`
   - paper-fold and one-fold paper-fold-cut sample `fold_axis=vertical|horizontal`
4. Supported fold `scene_variant` values:
   - `fold_strip`
   - `fold_card`
   - `fold_outline`
5. Supported overlay `scene_variant` values:
   - `overlay_strip`
   - `overlay_card`
   - `overlay_outline`
6. Answer contract: `answer_gt.type = option_letter`
7. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - exactly one bbox for the winning result option image.
8. Scene contract:
   - paper-fold tasks show a folding or fold-cut reference diagram above labeled result options,
   - overlay tasks show two aligned source sheets above labeled result options,
   - exactly `5..6` labeled result options appear below the reference panel,
   - the answer is the option letter, not a free-form view description.
9. Trace contract:
   - `execution_trace.query_id` stores the public query contract and `execution_trace.internal_query_id` stores the renderer grammar,
   - `render_map.option_choice_bboxes_px` stores each option-image bbox keyed by `option_choice_id`,
   - fold-cut tasks also store `render_map.folded_packet_bbox_px`,
   - overlay tasks store `render_map.source_sheet_bboxes_px`,
   - prompt-facing evidence is projected from `correct_option_choice_id`, not inferred from pixels.

## Cube-structure spatial tasks
1. Active task ids:
   - `task_puzzles__voxel_cube__cube_count`
   - `task_puzzles__voxel_cube__cube_structure_change_count`
   - `task_puzzles__voxel_cube__cube_painted_face_count`
   - `task_puzzles__voxel_cube__cube_visible_projection_count`
   - `task_puzzles__voxel_cube__cube_projection_match_label`
   - `task_puzzles__voxel_cube__cube_projection_consistency_label`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - each task records a fixed `query_id`: `cube_count`, `cube_structure_change_count`, `painted_face_count`, `visible_cube_count`, `projection_match_label`, or `projection_consistency_label`,
   - all six tasks share public `scene_id=voxel_cube`.
3. Supported query parameters:
   - structure change: `change_type=missing_to_complete|removed`
   - painted face: `painted_query=exterior_face_total|exact_k_faces_cube_count`
   - visible projection/projection match: `view_direction=top|front|right`
   - projection consistency: `consistency_query=inconsistent_projection_label|candidate_stack_from_views_label`
4. Supported `scene_variant` values:
   - cube/change/painted tasks: `stack_strip`, `stack_card`, `stack_outline`
   - visible projection task: `cube_stack`
   - projection match/consistency tasks use task-specific projection-option layouts
5. Answer contract:
   - cube/change/painted/visible-projection tasks use `answer_gt.type = integer`
   - projection match/consistency tasks use `answer_gt.type = string` with option-letter answers
6. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - cube and painted-face tasks return exactly one bbox for the visible cube structure,
   - structure-change tasks return exactly two bboxes for the left and right structures,
   - visible-projection tasks return one bbox for each query-grid cell that should be filled,
   - projection match/consistency tasks return one bbox for the selected labeled option panel.
7. Scene contract:
   - isometric structure tasks are rendered as fixed-view solid wall-like stacks with no floating cubes,
   - projection tasks show one isometric cube stack on the left and one blank orthographic query grid on the right,
   - `Front view` means looking at the left vertical face of the drawn stack,
   - `Right view` means looking at the right vertical face of the drawn stack,
   - cube color is sampled per instance from a non-semantic named-color support,
   - painted variants paint the whole exterior, including bottom faces.
8. Trace contract:
   - isometric branches store `render_map.structure_bboxes_px` and structure records,
   - projection branches store query-panel geometry, stack footprint/heights, visible counts for `top|front|right`, and projection-cell coordinates,
   - prompt-facing evidence is projected from structure ids or projection cells, not inferred from pixels.

## Cube surface/net spatial tasks
1. Active task ids:
   - `task_puzzles__cube_net__cube_net_face_relation_label`
   - `task_puzzles__cube_net__cube_rolling_result_label`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - cube-net relation records `query_id=opposite_face_label|marked_edge_neighbor_face_label`,
   - cube rolling records `query_id=final_top_face_label|final_front_face_label|final_right_face_label`,
   - both tasks share public `scene_id=cube_net`.
3. Answer contract:
   - both tasks use `answer_gt.type = option_letter`,
   - the answer is the option letter, not a free-form face label.
4. Evidence contract:
   - `evidence_gt.type = bbox_set`,
   - cube-net relation returns the marked reference face bbox followed by the selected option panel bbox,
   - cube rolling returns the start-cube panel bbox, roll-path panel bbox, and selected option panel bbox.
5. Scene contract:
   - cube-net relation scenes show one labeled cube net with a marked reference face and six labeled face options,
   - marked-edge queries may mark an outside edge of the net; the answer is the folded-cube face that shares that edge,
   - cube rolling scenes show a labeled start cube, an arrow path from `S` to `E`, and six labeled face options,
   - face colors and panel styles are non-semantic; face labels and traced orientation metadata define the answer.
6. Trace contract:
   - relation tasks store face labels, net coordinates, reference face, marked side, and correct face,
   - rolling tasks store start and final orientation, grid path cells, path directions, target slot, and correct face,
   - prompt-facing evidence is projected from finalized face, path, cube, and option-panel boxes, not inferred from pixels.

## Polyomino missing-region spatial task
1. Active task id:
   - `task_puzzles__polyomino_missing__polyomino_missing_region_piece_label`
2. Public contract:
   - the task records branch metadata in `query_id`,
   - semantic branches are recorded in `query_id`: `marked_region_piece_label` or `rectangle_complement_piece`.
3. Supported `scene_variant` values:
   - `polyomino_strip`
   - `polyomino_card`
   - `polyomino_outline`
4. Answer contract:
   - `answer_gt.type = option_letter`,
   - the answer is the labeled option piece, not a free-form shape name.
5. Evidence contract:
   - `evidence_gt.type = bbox_set`,
   - evidence contains the selected option panel and the target missing-region or complement-region bbox in the documented task order.
6. Scene contract:
   - the image shows a static polyomino board with one marked missing or complement region plus labeled candidate pieces,
   - rectangle-complement queries record `matching_policy=exact_orientation|rotation_reflection_allowed` as a traced parameter.
7. Trace contract:
   - board cells, missing/complement region cells, option specs, matching policy, and selected option id are metadata source of truth,
   - prompt-facing evidence is projected from recorded region and option bboxes, not inferred from pixels.

## Tangram-style spatial tasks
1. Active task ids:
   - `task_puzzles__tangram__tangram_missing_piece_label`
   - `task_puzzles__tangram__tangram_contact_count`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - each task records a fixed `query_id`: `missing_piece_label` or `contact_count`.
3. Supported `scene_variant` values:
   - `tangram_square`
   - `tangram_diamond`
   - `tangram_tilted`
4. Answer contract:
   - missing-piece uses `answer_gt.type = option_letter`
   - contact-count uses `answer_gt.type = integer`
5. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - missing-piece returns the correct option-panel bbox followed by the black missing-region bbox,
   - contact-count returns the marked-piece bbox or bboxes followed by the bboxes of all unmarked edge-touching pieces; every returned bbox is counted.
6. Scene contract:
   - one tangram-style polygon assembly is rendered from traced polygon pieces,
   - missing-piece queries show a black missing region and ask for the option that fills that gap,
   - missing-piece queries show 4..6 labeled piece options,
   - matching allows rotation but not flipping,
   - contact-count may mark one or two pieces, counts marked pieces plus unmarked edge-touching pieces, and uses edge contact only, not corner-only contact.
7. Trace contract:
   - `render_map.piece_bboxes_px` stores assembled-piece bboxes,
   - `render_map.option_panel_bboxes_px` stores candidate option-panel bboxes,
   - `execution_trace` stores the fixed `query_id`, `scene_variant`, piece specs, target piece or full-assembly target, option specs, contact witnesses, and solver trace,
   - prompt-facing evidence is projected from traced piece and option-panel ids, not inferred from pixels.

## `task_puzzles__cyclic_order__cyclic_order_equivalent_label`
1. Branch metadata: `query_id`
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
6. Answer contract:
   - `answer_gt.type = option_letter`
7. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - exactly one bbox for the equivalent option image.
8. Scene contract:
   - one reference token loop appears above six labeled option loops,
   - the loops may vary by path style and silhouette while preserving token order around each loop,
   - the prompt explicitly allows rotation and smooth deformation but forbids cutting, token crossing, and flipping the loop over,
   - option count is fixed at `6`,
   - exactly one option is valid,
   - token counts default to `4..5`,
   - color-bearing token styles use distinct colors with minimum Lab separation `DeltaE*ab >= 50`,
   - the answer is the single equivalent option letter.
9. Trace contract:
   - `scene_ir.entities` includes `puzzle_topology_reference_panel`, `puzzle_topology_reference_label`, `puzzle_topology_reference_loop`, `puzzle_topology_reference_bead`, `puzzle_topology_option_choice`, `puzzle_topology_option_label`, `puzzle_topology_option_loop`, and `puzzle_topology_option_bead` entities,
   - `render_map.reference_loop_bbox_px` stores the projected reference loop bbox,
   - `render_map.option_choice_bboxes_px` stores option-image bboxes keyed by `option_choice_id`,
   - `execution_trace` stores `query_id=cyclic_order_equivalent_label`, internal replay query fields, token/render axes, option specs, valid option id, answer option id/label, equivalence rule, and solver trace,
   - prompt-facing evidence is projected from the recorded valid option id, not inferred from pixels.

## String-topology count tasks
1. Active task ids:
   - `task_puzzles__string_topology__string_component_count`
2. Public contract:
   - the task records branch metadata in `query_id`,
   - the sampled predicate is recorded as `query_id`: `open_rope_count`, `closed_loop_count`, or `knotted_component_count`.
3. Supported `scene_variant` values:
   - `string_strip`
   - `string_card`
   - `string_outline`
4. Answer contract:
   - `answer_gt.type = integer`
5. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - one bbox for each counted item
6. Scene contract:
   - one open-canvas topology diagram shows randomly placed non-overlapping visual groups,
   - all string-topology count tasks use total visual group counts `6..20`,
   - open strings have visible endpoints,
   - visual groups can contain open strings, closed rings, or knotted loops,
   - over-under crossings indicate knots but do not merge separate string components,
   - answer target count support defaults to `3..10`,
   - distractor count support defaults to `3..10`,
   - total visual group count is `target_count + distractor_count`,
   - target count and distractor count are sampled independently during balanced review sampling,
   - open-rope distractors include closed rings and knotted closed loops,
   - the answer is the requested count as an integer.
7. Trace contract:
   - `scene_ir.entities` includes `puzzle_topology_string_scene_panel`, `puzzle_topology_string_visual_group`, `puzzle_topology_string_component`, and `puzzle_topology_string_crossing` entities,
   - `render_map.visual_group_bboxes_px` stores visual-group placement bboxes keyed by `visual_group_id`,
   - `render_map.component_bboxes_px` stores separate component bboxes keyed by `component_id`,
   - `render_map.crossing_bboxes_px` stores crossing bboxes keyed by `crossing_id`,
   - `render_map.evidence_source` records the component bbox evidence source,
   - `execution_trace` stores `query_id`, internal replay query fields, `component_specs`, `visual_group_specs`, `crossing_specs`, `component_count`, `component_count_range`, `visual_group_count`, `visual_group_count_range`, `object_count`, `object_count_range`, `object_count_probabilities`, `target_count`, `target_answer`, `target_count_range`, `target_count_probabilities`, `distractor_count`, `distractor_count_range`, `distractor_count_probabilities`, `open_rope_count`, `closed_loop_count`, `knotted_component_count`, `target_answer_support`, `answer_value`, `supporting_item_ids`, `supporting_evidence_source`, `topology_rule`, and `solver_trace`,
   - prompt-facing evidence is projected from `supporting_item_ids` using the recorded evidence source, not inferred from pixels.

## Maze tasks
1. Branch metadata: `query_id`
2. Active task ids:
   - `task_puzzles__maze__exit_reachability_label`
   - `task_puzzles__maze__reachable_exit_count`
3. `query_id` values:
   - `exit_reachability_label`
   - `reachable_exit_count`
4. Semantic parameter axes:
   - `query_id`: `exit_reachability_label|reachable_exit_count`
   - `target_reachability`: `reachable|unreachable` for `exit_reachability_label`
5. Supported `scene_variant` values:
   - `classic_wall_maze`
   - `paper_labyrinth_maze`
   - `block_wall_maze`
6. Answer contract:
   - `answer_gt.type = string` for `exit_reachability_label`
   - `answer_gt.type = integer` for `reachable_exit_count`
7. Evidence contract:
   - `evidence_gt.type = bbox_set`
   - exactly one target exit label+doorway bbox for `exit_reachability_label`,
   - one bbox for each reachable exit label+doorway for `reachable_exit_count`.
8. Scene contract:
   - one orthogonal wall maze shows a `START` cell and uniquely labeled exits on the outer boundary,
   - solid walls block movement between cells and wall gaps are passable,
   - maze rows default to `6..8`, columns default to `7..10`, and exit count defaults to `4..6`,
   - the generator constructs either exactly one exit with the sampled target reachability or the sampled number of reachable exits while keeping at least one unreachable exit.
9. Trace contract:
   - `scene_ir.entities` includes one `start` entity and exit entities with reachability recorded in metadata,
   - `render_map.item_bboxes_px` stores exit label+doorway bboxes keyed by item id,
   - `render_map.evidence_source` records `item_bboxes_px`,
   - `execution_trace` stores selected `query_id`, internal replay query fields, maze dimensions, start cell, open edges, exits, reachable/unreachable labels, target reachability when applicable, answer value, supporting item ids, evidence policy, and solver trace,
   - prompt-facing evidence is projected from `supporting_item_ids` using item bboxes, not inferred from pixels.

## Voxel-ladder maze tasks
1. Active task ids:
   - `task_puzzles__voxel_ladder__voxel_ladder_route_label`
   - `task_puzzles__voxel_ladder__voxel_ladder_route_count`
2. Public contract:
   - both tasks record branch metadata in `query_id`,
   - label queries record `query_id=checkpoint_sequence_label|unreachable_checkpoint_label`,
   - count queries record `query_id=reachable_checkpoint_count|shortest_ladder_count`.
3. Supported `scene_variant` values:
   - `clean_isometric_voxels`
   - `worksheet_voxel_maze`
   - `game_board_voxel_maze`
4. Answer contract:
   - `checkpoint_sequence_label` uses `answer_gt.type = option_letter` and the displayed options are color-swatch checkpoint sequences,
   - `unreachable_checkpoint_label` uses `answer_gt.type = string` with a lowercase TRACE color name,
   - count queries use `answer_gt.type = integer`.
5. Evidence contract:
   - `evidence_gt.type = bbox_set`,
   - checkpoint-sequence evidence contains the START cube, route checkpoint cubes, route ladders, and GOAL cube,
   - unreachable-checkpoint evidence contains the unreachable checkpoint cube,
   - reachable-checkpoint evidence contains all reachable checkpoint cubes,
   - shortest-ladder evidence contains the ladders on the shortest START-to-GOAL route.
6. Scene contract:
   - one isometric voxel maze shows a blue `START` cube, red `GOAL` cube, checkpoint cubes sampled without replacement from the canonical TRACE named-color palette, and black ladders between height levels,
   - movement follows adjacent same-height cube tops and black ladders for vertical transitions,
   - route checkpoint count defaults to `2..4`, reachable checkpoint count to `2..5`, route-option count to `4..5`, and shortest-ladder count to `1..3`,
   - the generator constructs unique final answers from metadata and keeps route/counter support item ids tied to rendered item bboxes.
7. Trace contract:
   - `scene_ir.entities` includes voxel cube, checkpoint, ladder, and route-option entities,
   - `render_map.item_bboxes_px` stores cube, checkpoint, ladder, and option bboxes keyed by item id,
   - `render_map.evidence_source` records `item_bboxes_px`,
   - `execution_trace` stores selected `query_id`, internal replay query fields, scene variant, start/goal nodes, route nodes, route edges, graph edges, checkpoints with `color_name` and `color_rgb`, ladders, option specs, answer value, supporting item ids, and evidence policy,
   - prompt-facing evidence is projected from `supporting_item_ids` using final image bboxes, not inferred from pixels.

## Prompt contract for logic grid completion tasks
1. Bundle: `puzzles_logic_v0`
2. `scene_key`: `logic_option_completion_puzzle`
3. `task_key`: `grid_completion_query`
4. Public task ids:
   - `task_puzzles__logic_grid__grid_uniqueness_completion_label`
   - `task_puzzles__logic_grid__grid_king_non_touch_label`
5. Internal `query_key`: `axis_uniqueness|row_and_column_uniqueness|king_non_touch`
6. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Prompt-facing evidence wording should always make the one-box contract explicit: the returned bbox is the winning option image.
8. `king_non_touch` prompt wording should make the rule explicit: identical symbols may not touch by edge or by corner.

## Prompt contract for nonogram logic tasks
1. Bundle: `puzzles_logic_v0`
2. `scene_key`: `nonogram`
3. Task keys:
   - `nonogram_line_completion_query`
   - `nonogram_candidate_solution_query`
4. Public task ids:
   - `task_puzzles__nonogram__nonogram_line_completion_label`
   - `task_puzzles__nonogram__nonogram_candidate_solution_label`
5. Internal `query_key`: `line_completion_label|candidate_solution_label`
6. Required slots:
   - scene: `object_description`
   - line completion query: `line_label`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Line-completion and candidate-solution prompts should ask for option letters.

## Prompt contract for tents logic tasks
1. Bundle: `puzzles_logic_v0`
2. `scene_key`: `tents`
3. Task keys:
   - `tents_missing_tent_query`
   - `tents_valid_candidate_count_query`
4. Public task ids:
   - `task_puzzles__tents__tents_missing_tent_cell_label`
   - `task_puzzles__tents__tents_valid_candidate_count`
5. Internal `query_key`: `missing_tent_cell_label|valid_candidate_count`
6. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Prompt wording should state the no-touch rule and that row/column counts constrain adding a tent.

## Prompt contract for Star Battle logic tasks
1. Bundle: `puzzles_logic_v0`
2. `scene_key`: `star_battle`
3. Task keys:
   - `star_battle_valid_cell_query`
   - `star_battle_remaining_count_query`
4. Public task ids:
   - `task_puzzles__star_battle__star_battle_valid_cell_label`
   - `task_puzzles__star_battle__star_battle_remaining_count`
5. Internal `query_key`: `valid_cell_anywhere_label|valid_cell_in_marked_region_label|valid_cell_for_marked_row_label|remaining_valid_cells_in_marked_region_count|remaining_valid_cells_in_marked_row_count|remaining_valid_cells_in_marked_column_count`
6. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Prompt wording should state the Star Battle quota rule and no-touch rule when asking for a legal placement.

## Prompt contract for dice probability tasks
1. Bundle: `puzzles_probability_v0`
2. `scene_key`: `dice_probability`
3. Task keys:
   - `single_dice_probability_query`
   - `pair_dice_probability_query`
   - `conditional_dice_probability_query`
4. Public task ids:
   - `task_puzzles__dice_probability__dice_single_event_value`
   - `task_puzzles__dice_probability__dice_pair_event_value`
   - `task_puzzles__dice_probability__dice_conditional_event_value`
5. Internal `query_key`: `single_parity_probability|single_threshold_probability|single_value_set_probability|single_color_and_value_probability|single_color_or_value_probability|pair_sum_probability|pair_sum_threshold_probability|pair_difference_probability|pair_parity_combo_probability|pair_color_value_combo_probability|conditional_value_property_given_color_probability|conditional_color_given_value_property_probability|conditional_color_given_value_set_probability`
6. Required slots:
   - scene: `object_description`
   - non-conditional probability query: `event_description`
   - conditional probability query: `given_description`, `event_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Prompt wording must say selections are uniform over shown dice and must refer to visible top values, not rolling dice.

## Prompt contract for spinner probability tasks
1. Bundle: `puzzles_probability_v0`
2. `scene_key`: `spinner_probability`
3. Task keys:
   - `single_spinner_probability_query`
   - `pair_spinner_probability_query`
4. Public task ids:
   - `task_puzzles__spinner_probability__spinner_compound_event_value`
   - `task_puzzles__spinner_probability__spinner_pair_event_value`
5. Internal `query_key`: `single_color_probability|single_shape_probability|single_color_and_shape_probability|single_color_or_shape_probability|pair_both_target_color_probability|pair_at_least_one_target_color_probability|pair_same_color_probability`
6. Required slots:
   - scene: `object_description`
   - probability query: `event_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Prompt wording should state that sectors are equal-probability and ask for a reduced fraction answer.

## Prompt contract for spatial transform result tasks
1. Bundle: `puzzles_spatial_v0`
2. `scene_key`: `spatial_transform_result_puzzle`
3. `task_key`: `transform_result_query`
4. Public task ids:
   - `task_puzzles__paper_fold__paper_fold_result_label`
   - `task_puzzles__paper_fold_cut__paper_fold_cut_result_label`
   - `task_puzzles__overlay__overlay_result_label`
5. Internal `query_key`: `paper_fold_result|paper_fold_cut_result|overlay_result`
6. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Prompt-facing evidence wording should always make the one-box contract explicit: the returned bbox is the winning option image.

## Prompt contract for cube-structure spatial tasks
1. Bundle: `puzzles_spatial_v0`
2. `scene_key`: `spatial_cube_structure_puzzle`
3. `task_key`: `cube_structure_count_query`
4. Public task ids:
   - `task_puzzles__voxel_cube__cube_count`
   - `task_puzzles__voxel_cube__cube_structure_change_count`
   - `task_puzzles__voxel_cube__cube_painted_face_count`
   - `task_puzzles__voxel_cube__cube_visible_projection_count`
   - `task_puzzles__voxel_cube__cube_projection_match_label`
   - `task_puzzles__voxel_cube__cube_projection_consistency_label`
5. Internal `query_key`: prompt templates use the construction query key: `total_cube_count|missing_to_complete_cuboid_count|removed_cube_count|painted_exterior_face_count|exact_k_painted_faces_cube_count|visible_cube_count|projection_match_label|inconsistent_projection_label|candidate_stack_from_views_label`
6. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Prompt-facing evidence wording should make the one-box, two-box, query-grid-cell, or selected-option-panel contract explicit depending on query.

## Prompt contract for polyomino missing-region spatial task
1. Bundle: `puzzles_spatial_v0`
2. `scene_key`: `spatial_polyomino_missing_puzzle`
3. `task_key`: `polyomino_missing_query`
4. Public task ids:
   - `task_puzzles__polyomino_missing__polyomino_missing_region_piece_label`
5. Internal `query_key`: `marked_region_piece_label|rectangle_complement_piece`
6. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Prompt-facing evidence wording should make the option-plus-region order explicit.

## Prompt contract for sliding-block spatial tasks
1. Bundle: `puzzles_spatial_v0`
2. `scene_key`: `sliding_block`
3. `task_key`: `sliding_block_query`
4. Public task ids:
   - `task_puzzles__sliding_block__sliding_block_blocker_count`
   - `task_puzzles__sliding_block__sliding_block_move_result_label`
5. Internal `query_key`: `blocker_count|move_result_label`
6. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Prompt-facing evidence wording should make the bbox contract explicit: blocker-count evidence contains all counted path-blocking blocks, while move-result evidence contains the original moved-block boxes plus the correct final-board option panel.

## Prompt contract for tangram-style spatial tasks
1. Bundle: `puzzles_spatial_v0`
2. `scene_key`: `spatial_tangram_assembly_puzzle`
3. `task_key`: `tangram_assembly_query`
4. Public task ids:
   - `task_puzzles__tangram__tangram_missing_piece_label`
   - `task_puzzles__tangram__tangram_contact_count`
5. Internal `query_key`: `missing_piece_label|contact_count`
6. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Prompt-facing evidence wording should make the option-plus-region order explicit for matching queries and the marked-piece-or-pieces plus unmarked touching-piece order explicit for contact-count queries; every contact-count evidence box is part of the counted set.

## Prompt contract for `task_puzzles__cyclic_order__cyclic_order_equivalent_label`
1. Bundle: `puzzles_topology_v0`
2. `scene_key`: `topology_cyclic_order_puzzle`
3. `task_key`: `cyclic_order_match_query`
4. `query_key`: `cyclic_order_equivalent_label`
5. Required slots:
   - scene: `object_description`
   - query-id: `token_render_style_instruction`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt-facing wording should always make the rule explicit: rotation and smooth deformation are allowed, but cutting, token crossing, and reflection/flipping are not.

## Prompt contract for string-topology count tasks
1. Bundle: `puzzles_topology_v0`
2. `scene_key`: `topology_string_component_puzzle`
3. `task_key`: `string_topology_count_query`
4. Public task ids:
   - `task_puzzles__string_topology__string_component_count`
5. Internal `query_key`: `open_rope_count|closed_loop_count|knotted_component_count`
6. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Prompt-facing wording should always make the count target explicit and preserve the bbox evidence format for counted components.

## Prompt contract for maze tasks
1. Bundle: `puzzles_topology_v0`
2. `scene_key`: `topology_maze_exit_puzzle`
3. `task_key`: `maze_exit_label_query`
4. `query_key`: `exit_reachability_label|reachable_exit_count`
5. Required slots:
   - scene: `object_description`
   - `exit_reachability_label` variant: `target_reachability_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt-facing wording should make the wall-blocked maze movement rule explicit and preserve the exit-label or count answer format.

## Prompt contract for `task_puzzles__pipe_flow__pipe_flow_repair_tile_label`
1. Bundle: `puzzles_topology_v0`
2. `scene_key`: `topology_pipe_flow_puzzle`
3. `task_key`: `pipe_flow_repair_query`
4. `query_key`: `flow_repair_tile_label`
5. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt-facing wording should state that flow follows matching tile-edge openings, that options may be rotated before placement, and exactly one labeled 2x2 option fills the black missing region to connect the green start marker to the red triangular finish flag.
7. Offshoot branches should be generated from the main path and terminate on a grid side so they read as visible side outlets, not as isolated interior fragments.

## Prompt contract for voxel-ladder maze tasks
1. Bundle: `puzzles_topology_v0`
2. `scene_key`: `topology_voxel_ladder`
3. Task keys:
   - `voxel_ladder_route_label_query`
   - `voxel_ladder_route_count_query`
4. Public task ids:
   - `task_puzzles__voxel_ladder__voxel_ladder_route_label`
   - `task_puzzles__voxel_ladder__voxel_ladder_route_count`
5. Internal `query_key`: `checkpoint_sequence_label|unreachable_checkpoint_label|reachable_checkpoint_count|shortest_ladder_count`
6. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Prompt-facing wording should state the cube-top adjacency and black-ladder movement rule and preserve the bbox evidence contract for the queried route, checkpoint, or ladder support.

## Color-gradient visual task
1. Active task ids:
   - `task_puzzles__color_gradient__color_gradient_completion_label`
   - `task_puzzles__color_gradient__color_gradient_violation_cell_label`
2. Public contract:
   - tasks record branch metadata in `query_id`,
   - query ids are `linear_gradient_completion_label` and `color_gradient_violation_cell_label`.
3. Supported `scene_variant` values:
   - `swatch_clean`
   - `swatch_card`
   - `swatch_notebook`
4. Supported internal violation `rule_variant` values:
   - `column_hue_row_lightness`
   - `row_hue_column_lightness`
   - `column_hue_row_saturation`
5. Supported internal completion `rule_variant` values:
   - `hue_gradient`
   - `lightness_gradient`
   - `hue_lightness_gradient`
6. Completion also varies `sequence_length_variant=5_cell|6_cell|7_cell`; `option_count_variant` supports `4_options|5_options|6_options`, but the current calibration config samples `6_options` to keep answer labels balanced.
7. Violation answer contract:
   - `answer_gt.type = option_letter`,
   - answer is the capital-letter label on the violating swatch.
8. Violation evidence contract:
   - `evidence_gt.type = bbox_set`,
   - exactly one bbox for the swatch cell that breaks the progression.
9. Completion answer contract:
   - `answer_gt.type = option_letter`,
   - answer is the capital-letter label on the option swatch that completes the row.
10. Completion evidence contract:
   - `evidence_gt.type = bbox_set`,
   - two bboxes for the blank swatch and the correct option swatch.

## Counterfactual board-grid task
1. Active task id:
   - `task_puzzles__counterfactual_board__board_grid_count`
2. Public contract:
   - branch metadata uses `query_id`,
   - query ids are `row_count|column_count|horizontal_line_count|vertical_line_count`.
3. Supported board styles:
   - `chess_checkers`: fixed canonical board rendering with sparse checker/chess discs; canonical prior `8 x 8`; visible rows/columns sampled `6..10`.
   - `sudoku`: fixed canonical grid rendering with sparse given digits; canonical prior `9 x 9`; visible rows/columns sampled `7..11`.
   - `xiangqi`: fixed canonical line-board rendering with sparse xiangqi-style pieces; canonical prior `10` horizontal lines by `9` vertical lines; visible horizontal lines sampled `8..12` and vertical lines sampled `7..11`.
4. Prompt-facing text intentionally does not name the board/game. The image should carry the familiar-board prior.
5. The scene samples one shared puzzle-domain light background style per instance and does not render a drop shadow under the board.
6. Answer contract:
   - `answer_gt.type = integer`,
   - answer is the requested visible row, column, horizontal-line, or vertical-line count.
7. Evidence contract:
   - `evidence_gt.type = bbox_set`,
   - exactly one bbox for the full board.
8. Decorative digits/pieces are recorded separately in trace metadata and are not part of prompt-facing evidence.

## Prompt contract for `task_puzzles__counterfactual_board__board_grid_count`
1. Bundle: `puzzles_counterfactual_v0`
2. `scene_key`: `counterfactual_board`
3. `task_key`: `board_grid_count_query`
4. `query_key`: selected query id.
5. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt wording should mirror the VLM-bias style: ask generic row, column, cell, horizontal-line, or vertical-line counts without naming the game.

## Prompt contract for `task_puzzles__color_gradient__color_gradient_completion_label`
1. Bundle: `puzzles_visual_v0`
2. `scene_key`: `color_gradient`
3. `task_key`: `color_gradient_completion_query`
4. `query_key`: `linear_gradient_completion_label`
5. Answer contract:
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt-facing wording should ask for the option that completes the blank swatch and should not name the hidden HSL rule.

## Prompt contract for `task_puzzles__color_gradient__color_gradient_violation_cell_label`
1. Bundle: `puzzles_visual_v0`
2. `scene_key`: `color_gradient`
3. `task_key`: `color_gradient_violation_query`
4. `query_key`: `color_gradient_violation_cell_label`
5. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt-facing wording should keep the evidence contract to the violating swatch bbox and should not name the hidden HSL rule.

## Word-search grid tasks
1. Active task ids:
   - `task_puzzles__word_search__search_location_label`
   - `task_puzzles__word_search__search_letter_count_value`
   - `task_puzzles__word_search__search_present_word_count`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - each task maps to scene id `word_search`,
   - query ids are `word_location_label`, `letter_count_value`, and `present_word_count`.
3. Supported `scene_variant` values:
   - `word_search_classic`
   - `word_search_notebook`
   - `word_search_card`
4. Answer contract:
   - location answers are option letters,
   - letter count and present word count answers are integers.
5. Evidence contract:
   - location evidence is the selected option card followed by ordered word-cell boxes; location option cards use compact direction codes explained by an in-image legend,
   - letter-count evidence is all matching letter-cell boxes,
   - present-word evidence is each present word chip followed by ordered word-cell boxes.
6. The word-search group disables post-image noise because the semantic signal is OCR-like letter reading.

## Prompt contract for word-search grid tasks
1. Bundle: `puzzles_word_v0`
2. `scene_key`: `word_search`
3. `task_key`: `word_search_query`
4. Query keys:
   - `word_location_label`
   - `letter_count_value`
   - `present_word_count`
5. Required slots:
   - scene: `object_description`
   - query: `target_word`, `target_letter`, or `word_bank_size`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt wording should use the visible row/column labels and should not expose hidden placement metadata.

## Music-staff notation tasks
1. Active task ids:
   - `task_puzzles__music_staff__pitch_interval_label`
   - `task_puzzles__music_staff__key_scale_label`
   - `task_puzzles__music_staff__chord_harmony_label`
   - `task_puzzles__music_staff__dominant_chord_count`
   - `task_puzzles__music_staff__meter_rhythm_label`
   - `task_puzzles__music_staff__duration_equivalence_label`
   - `task_puzzles__music_staff__bar_count_value`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - each task maps to scene id `music_staff`,
   - query ids cover pitch/interval reading, key/scale reasoning, chord/harmony labels, dominant-chord counting, meter/rhythm labels, duration equivalence, and visible-bar counting.
   - public task units are intentionally grouped by coherent notation concept,
     not by every individual music-theory subroutine:
     - `pitch_interval_label` covers note naming, interval naming, same-pitch
       checks, and transposition checks,
     - `key_scale_label` covers key-signature identification, scale-degree
       function, and scale validation,
     - `chord_harmony_label` covers chord quality, inversion, and
       roman-numeral labeling,
     - `meter_rhythm_label` covers time-signature, meter-type, and articulation
       mark reading as rhythm/notation-mark interpretation.
3. Supported `scene_variant` values:
   - `engraved_sheet`
   - `exam_scan`
   - `notebook_staff`
4. Answer contract:
   - label tasks use string answers,
   - count tasks use integer answers,
   - duration-equivalence uses option-letter string answers.
5. Evidence contract:
   - prompt-facing evidence is `bbox_set`,
   - evidence stays local to marked notes, chords, key signatures, bars, time signatures, articulation marks, or option cards needed for the query.
6. The notation group keeps clef, pitch, rhythm, duration, key, chord, and bar metadata in trace; the verifier uses that metadata rather than OCR or pixel inference.

## Prompt contract for music-staff notation tasks
1. Bundle: `puzzles_notation_v0`
2. `scene_key`: `music_staff`
3. `task_key`: `music_notation_query`
4. Query keys match the public `query_id` values in the active task docs and `configs/domains/puzzles/notation.yaml`.
5. Required slots:
   - scene: `object_description`
   - query-specific notation slots when declared by the prompt bundle
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Prompt wording should ask from the visible staff notation and avoid exposing hidden symbolic metadata.

## Visual policy
1. Puzzles use the same light solid background baseline as the other clean synthetic domains.
2. Logic-grid winning option panels, spatial fold-result winning option images, polyomino/overlay winning option panels, cube/voxel visible regions, solid-view query-grid cells, and topology counted items should stay visually salient relative to the other boxes.

## Determinism + review
1. Deterministic generation/rendering from `instance_seed`.
2. `query_id` and `scene_variant` are sampled independently at the task policy level.
3. No semantic auto-relaxation: every generated puzzle has exactly one valid answer under its declared answer type.
4. Review/sample overlays should use the recorded bbox maps (`render_map.slot_bboxes_px[query_slot_id]`, `render_map.box_bboxes_px[query_box_id]`, `render_map.cell_bboxes_px[query_cell_id]`, `render_map.item_bboxes_px[item_id]`, `render_map.option_panel_bboxes_px[correct_option_panel_id]`, `render_map.option_choice_bboxes_px[correct_option_choice_id]`, `render_map.structure_bboxes_px[structure_bbox_id]`, `render_map.component_bboxes_px[component_id]`, `render_map.crossing_bboxes_px[crossing_id]`, `render_map.piece_card_bboxes_px[piece_id]`, or `render_map.point_bboxes_px[point_label]`) for the prompt-facing witness. Maze shortest-path overlays use ordered centers from `projected_evidence.pixel_point_sequence`.
