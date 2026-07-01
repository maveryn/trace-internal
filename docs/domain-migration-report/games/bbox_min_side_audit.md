# Bbox Minimum-Side Audit From Existing Task Reviews

- Checked at: `2026-06-27T09:20:36Z`
- Review root: `review/task-reviews`
- Minimum required side: `24.0 px`
- Scenes: `51`
- Tasks: `160`
- Bbox-family runtime tasks: `105`
- Samples inspected: `16000`
- Bboxes inspected: `29181`
- Failing bbox tasks: `0`
- Invalid bbox tasks: `0`
- Missing review-artifact tasks: `0`
- Doc/runtime annotation mismatches: `0`

## Bbox-Family Task Observations

| Domain | Scene | Task | Runtime Type | Samples | Bboxes | Min W | Min H | Min Side | Status |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| games | 2048 | `task_games__2048__max_tile_value` | ['bbox_set'] | 100 | 200 | 62 | 62 | 62 | pass |
| games | 2048 | `task_games__2048__move_result_board_label` | ['bbox'] | 100 | 100 | 207 | 207 | 207 | pass |
| games | backgammon | `task_games__backgammon__destination_count` | ['bbox_set'] | 100 | 275 | 35.482 | 106.78 | 35.482 | pass |
| games | backgammon | `task_games__backgammon__point_state_count` | ['bbox_set'] | 100 | 313 | 35.325 | 106.4 | 35.325 | pass |
| games | battleship | `task_games__battleship__ship_cell_status_count` | ['bbox_set'] | 100 | 185 | 24.7 | 24.7 | 24.7 | pass |
| games | battleship | `task_games__battleship__ship_status_count` | ['bbox_set_map'] | 100 | 720 | 25.8 | 25.8 | 25.8 | pass |
| games | bingo | `task_games__bingo__called_number_match_count` | ['bbox_set'] | 100 | 246 | 62 | 40 | 40 | pass |
| games | bingo | `task_games__bingo__near_complete_line_count` | ['bbox_set'] | 100 | 169 | 61.2 | 39.4 | 39.4 | pass |
| games | brick_breaker | `task_games__brick_breaker__hit_row_remaining_count` | ['bbox_set'] | 100 | 288 | 56.166 | 24.6 | 24.6 | pass |
| games | bubble_shooter | `task_games__bubble_shooter__drop_count` | ['bbox_set'] | 100 | 201 | 31.986 | 31.986 | 31.986 | pass |
| games | bubble_shooter | `task_games__bubble_shooter__pop_color_label` | ['bbox_set'] | 100 | 348 | 31.038 | 31.038 | 31.038 | pass |
| games | bubble_shooter | `task_games__bubble_shooter__pop_count` | ['bbox_set'] | 100 | 283 | 31.702 | 31.702 | 31.702 | pass |
| games | cards | `task_games__cards__blackjack_best_hand_label` | ['bbox_set'] | 100 | 354 | 78 | 108 | 78 | pass |
| games | cards | `task_games__cards__exact_triple_count` | ['bbox_set_map'] | 100 | 657 | 84 | 122 | 84 | pass |
| games | cards | `task_games__cards__higher_than_reference_count` | ['bbox_set'] | 100 | 255 | 84 | 122 | 84 | pass |
| games | cards | `task_games__cards__longest_run_length` | ['bbox_set'] | 100 | 412 | 84 | 122 | 84 | pass |
| games | cards | `task_games__cards__missing_card_to_complete_hand_label` | ['bbox'] | 100 | 100 | 86 | 120 | 86 | pass |
| games | cards | `task_games__cards__poker_best_hand_label` | ['bbox_set'] | 100 | 500 | 78 | 108 | 78 | pass |
| games | cards | `task_games__cards__poker_draw_card_label` | ['bbox'] | 100 | 100 | 86 | 120 | 86 | pass |
| games | cards | `task_games__cards__same_suit_as_reference_count` | ['bbox_set'] | 100 | 227 | 84 | 122 | 84 | pass |
| games | cards | `task_games__cards__trick_taking_winner_label` | ['bbox'] | 100 | 100 | 96 | 136 | 96 | pass |
| games | cards | `task_games__cards__trick_winning_play_label` | ['bbox'] | 100 | 100 | 86 | 120 | 86 | pass |
| games | checkers | `task_games__checkers__max_capture_chain_length` | ['bbox_set'] | 100 | 316 | 25.08 | 25.08 | 25.08 | pass |
| games | checkers | `task_games__checkers__move_count` | ['bbox_set'] | 100 | 191 | 38 | 38 | 38 | pass |
| games | checkers | `task_games__checkers__piece_mobility_count` | ['bbox_set'] | 100 | 244 | 25.08 | 25.08 | 25.08 | pass |
| games | checkers | `task_games__checkers__piece_state_count` | ['bbox_set'] | 100 | 297 | 25.74 | 25.74 | 25.74 | pass |
| games | chess | `task_games__chess__colored_piece_kind_count` | ['bbox_set'] | 100 | 294 | 29.64 | 29.64 | 29.64 | pass |
| games | chess | `task_games__chess__king_escape_square_count` | ['bbox_set'] | 100 | 222 | 39 | 39 | 39 | pass |
| games | chess | `task_games__chess__marked_piece_blocker_count` | ['bbox_set'] | 100 | 210 | 29.64 | 29.64 | 29.64 | pass |
| games | chess | `task_games__chess__marked_piece_destination_count` | ['bbox_set'] | 100 | 325 | 39 | 39 | 39 | pass |
| games | chess | `task_games__chess__piece_kind_count` | ['bbox_set'] | 100 | 288 | 30.4 | 30.4 | 30.4 | pass |
| games | chess | `task_games__chess__player_capture_piece_count` | ['bbox_set'] | 100 | 338 | 30.4 | 30.4 | 30.4 | pass |
| games | chess | `task_games__chess__target_square_attacker_count` | ['bbox_set'] | 100 | 210 | 28.88 | 28.88 | 28.88 | pass |
| games | chess_variant | `task_games__chess_variant__marked_piece_destination_count` | ['bbox_set'] | 100 | 208 | 38 | 38 | 38 | pass |
| games | chess_variant | `task_games__chess_variant__target_square_reacher_count` | ['bbox_set'] | 100 | 204 | 24.32 | 24.32 | 24.32 | pass |
| games | connect_four | `task_games__connect_four__column_disc_profile_label` | ['bbox_set'] | 100 | 360 | 64 | 64 | 64 | pass |
| games | connect_four | `task_games__connect_four__winning_move_count` | ['bbox_set'] | 100 | 194 | 56 | 56 | 56 | pass |
| games | crossing | `task_games__crossing__moving_object_direction_count` | ['bbox_set'] | 100 | 327 | 70 | 42 | 42 | pass |
| games | darts | `task_games__darts__bullseye_membership_count` | ['bbox_set'] | 100 | 224 | 28 | 28 | 28 | pass |
| games | dominoes | `task_games__dominoes__double_count` | ['bbox_set'] | 100 | 249 | 102 | 76 | 76 | pass |
| games | dominoes | `task_games__dominoes__higher_sum_than_reference_count` | ['bbox_set'] | 100 | 231 | 90 | 76 | 76 | pass |
| games | dominoes | `task_games__dominoes__longest_chain_length_value` | ['bbox_set'] | 100 | 308 | 137 | 76 | 76 | pass |
| games | dominoes | `task_games__dominoes__matching_end_count` | ['bbox_set'] | 100 | 253 | 102 | 76 | 76 | pass |
| games | dominoes | `task_games__dominoes__sum_to_target_count` | ['bbox_set'] | 100 | 211 | 102 | 76 | 76 | pass |
| games | dots_and_boxes | `task_games__dots_and_boxes__completable_box_label` | ['bbox'] | 100 | 100 | 72.5 | 72.5 | 72.5 | pass |
| games | dots_and_boxes | `task_games__dots_and_boxes__owned_box_count` | ['bbox_set'] | 100 | 395 | 66.5 | 66.5 | 66.5 | pass |
| games | dots_and_boxes | `task_games__dots_and_boxes__three_sided_box_count` | ['bbox_set'] | 100 | 252 | 65.25 | 65.25 | 65.25 | pass |
| games | go | `task_games__go__group_adjacent_enemy_count` | ['bbox_set'] | 100 | 332 | 29.434 | 29.434 | 29.434 | pass |
| games | go | `task_games__go__marked_group_stone_count` | ['bbox_set'] | 100 | 422 | 29.143 | 29.143 | 29.143 | pass |
| games | lane_runner | `task_games__lane_runner__safe_path_label` | ['bbox'] | 100 | 100 | 96 | 260 | 96 | pass |
| games | mancala_pit_board | `task_games__mancala_pit_board__post_sow_pit_count_value` | ['bbox_map'] | 100 | 200 | 108 | 68 | 68 | pass |
| games | mancala_pit_board | `task_games__mancala_pit_board__sowing_landing_option_label` | ['bbox'] | 100 | 100 | 108 | 68 | 68 | pass |
| games | marble_chain | `task_games__marble_chain__shot_effect_value` | ['bbox_set'] | 100 | 299 | 28 | 28 | 28 | pass |
| games | match3 | `task_games__match3__gem_count` | ['bbox_set'] | 100 | 333 | 31 | 31 | 31 | pass |
| games | minecraft | `task_games__minecraft__resource_route_cost` | ['bbox_set'] | 100 | 255 | 29 | 30 | 29 | pass |
| games | minecraft | `task_games__minecraft__stack_height_condition_count` | ['bbox_set'] | 100 | 310 | 29 | 45 | 29 | pass |
| games | minecraft | `task_games__minecraft__top_ore_stack_count` | ['bbox_set'] | 100 | 343 | 29 | 30 | 29 | pass |
| games | minesweeper | `task_games__minesweeper__forced_cell_count` | ['bbox_set'] | 100 | 309 | 67 | 67 | 67 | pass |
| games | nine_mens_morris | `task_games__nine_mens_morris__pieces_in_mill_count` | ['bbox_set'] | 100 | 548 | 26 | 26 | 26 | pass |
| games | pinball_table | `task_games__pinball_table__scoreable_object_count` | ['bbox_set'] | 100 | 279 | 38.694 | 25.563 | 25.563 | pass |
| games | platformer | `task_games__platformer__jump_landing_label` | ['bbox'] | 100 | 100 | 86.6 | 26.095 | 26.095 | pass |
| games | pool | `task_games__pool__blocking_ball_count` | ['bbox_set'] | 100 | 201 | 36 | 36 | 36 | pass |
| games | pool | `task_games__pool__group_ball_count` | ['bbox_set'] | 100 | 422 | 36 | 36 | 36 | pass |
| games | racing_track | `task_games__racing_track__ahead_object_count` | ['bbox_set'] | 100 | 182 | 28.424 | 29.054 | 28.424 | pass |
| games | reversi | `task_games__reversi__legal_destination_count` | ['bbox_set'] | 100 | 309 | 46 | 46 | 46 | pass |
| games | rhythm | `task_games__rhythm__earliest_hit_lane_label` | ['bbox'] | 100 | 100 | 53.5 | 43 | 43 | pass |
| games | rhythm | `task_games__rhythm__lane_note_count` | ['bbox_set'] | 100 | 336 | 53.5 | 43 | 43 | pass |
| games | rhythm | `task_games__rhythm__lane_note_score_value` | ['bbox_set'] | 100 | 287 | 53.5 | 43 | 43 | pass |
| games | rhythm | `task_games__rhythm__most_notes_lane_label` | ['bbox_set'] | 100 | 316 | 53.5 | 43 | 43 | pass |
| games | rule_override_board | `task_games__rule_override_board__line_result_count` | ['bbox_set'] | 100 | 261 | 108 | 126 | 108 | pass |
| games | rule_override_board | `task_games__rule_override_board__piece_result_count` | ['bbox_set'] | 100 | 263 | 138 | 156 | 138 | pass |
| games | sliding_block | `task_games__sliding_block__block_orientation_count` | ['bbox_set'] | 100 | 440 | 32 | 32 | 32 | pass |
| games | sliding_block | `task_games__sliding_block__movable_block_count` | ['bbox_set'] | 100 | 660 | 32 | 32 | 32 | pass |
| games | sliding_block | `task_games__sliding_block__sliding_block_blocker_count` | ['bbox_set'] | 100 | 267 | 32 | 32 | 32 | pass |
| games | sliding_block | `task_games__sliding_block__sliding_block_move_result_label` | ['bbox_map'] | 100 | 200 | 130.666 | 130.667 | 130.666 | pass |
| games | slot_machine | `task_games__slot_machine__reel_completion_label` | ['bbox'] | 100 | 100 | 126 | 270 | 126 | pass |
| games | snake | `task_games__snake__path_outcome_option_label` | ['bbox_set'] | 100 | 338 | 30.8 | 30.8 | 30.8 | pass |
| games | snake | `task_games__snake__safe_direction_count` | ['bbox_set'] | 100 | 165 | 30.4 | 30.4 | 30.4 | pass |
| games | snake | `task_games__snake__snake_length_count` | ['bbox_set'] | 100 | 886 | 31.9 | 31.9 | 31.9 | pass |
| games | snakes_ladders | `task_games__snakes_ladders__move_outcome_value` | ['bbox_map'] | 100 | 200 | 76.571 | 76.571 | 76.571 | pass |
| games | snakes_ladders | `task_games__snakes_ladders__remaining_to_finish_value` | ['bbox_map'] | 100 | 200 | 76.571 | 76.571 | 76.571 | pass |
| games | snakes_ladders | `task_games__snakes_ladders__special_square_count` | ['bbox_set'] | 100 | 258 | 76.571 | 76.571 | 76.571 | pass |
| games | sokoban | `task_games__sokoban__box_goal_status_count` | ['bbox_set'] | 100 | 286 | 48 | 48 | 48 | pass |
| games | sokoban | `task_games__sokoban__closest_box_goal_label` | ['bbox'] | 100 | 100 | 48 | 48 | 48 | pass |
| games | sokoban | `task_games__sokoban__push_stand_cell_label` | ['bbox'] | 100 | 100 | 48 | 48 | 48 | pass |
| games | solitaire | `task_games__solitaire__foundation_ready_count` | ['bbox_set'] | 100 | 207 | 74 | 104 | 74 | pass |
| games | solitaire | `task_games__solitaire__move_legality_label` | ['bbox_map'] | 100 | 200 | 74 | 104 | 74 | pass |
| games | solitaire | `task_games__solitaire__tableau_movable_card_count_value` | ['bbox_set'] | 100 | 212 | 74 | 104 | 74 | pass |
| games | space_shooter | `task_games__space_shooter__enemy_ship_count` | ['bbox_set'] | 100 | 996 | 62 | 48 | 48 | pass |
| games | space_shooter | `task_games__space_shooter__enemy_ship_hit_count` | ['bbox_set'] | 100 | 302 | 62 | 48 | 48 | pass |
| games | space_shooter | `task_games__space_shooter__first_hit_enemy_ship_label` | ['bbox'] | 100 | 100 | 62 | 48 | 48 | pass |
| games | space_shooter | `task_games__space_shooter__hit_enemy_ship_label` | ['bbox'] | 100 | 100 | 62 | 48 | 48 | pass |
| games | space_shooter | `task_games__space_shooter__safe_lane_count` | ['bbox_set'] | 100 | 294 | 97.5 | 38 | 38 | pass |
| games | tetris | `task_games__tetris__active_piece_shape_label` | ['bbox'] | 100 | 100 | 34 | 34 | 34 | pass |
| games | tetris | `task_games__tetris__drop_collision_time_value` | ['bbox_set_map'] | 100 | 653 | 34 | 34 | 34 | pass |
| games | tetris | `task_games__tetris__drop_result_label` | ['bbox'] | 100 | 100 | 141 | 297 | 141 | pass |
| games | tetris | `task_games__tetris__edge_occupied_row_cell_count` | ['bbox_set'] | 100 | 455 | 34 | 34 | 34 | pass |
| games | tetris | `task_games__tetris__line_clear_count` | ['bbox_map'] | 100 | 200 | 166 | 194 | 166 | pass |
| games | tetris | `task_games__tetris__row_occupancy_status_count` | ['bbox_set'] | 100 | 232 | 250 | 34 | 34 | pass |
| games | tic_tac_toe_3d | `task_games__tic_tac_toe_3d__winning_move_cell_label` | ['bbox_set'] | 100 | 300 | 73 | 35.44 | 35.44 | pass |
| games | tower_draughts_board | `task_games__tower_draughts_board__controlled_stack_count` | ['bbox_set'] | 100 | 468 | 29.76 | 29.76 | 29.76 | pass |
| games | tower_draughts_board | `task_games__tower_draughts_board__marked_stack_capture_count` | ['bbox_set'] | 100 | 208 | 29.76 | 29.76 | 29.76 | pass |
| games | ultimate_tictactoe | `task_games__ultimate_tictactoe__line_completion_move_label` | ['bbox'] | 100 | 100 | 32 | 32 | 32 | pass |
| games | ultimate_tictactoe | `task_games__ultimate_tictactoe__macro_threat_board_count` | ['bbox_set'] | 100 | 257 | 100 | 100 | 100 | pass |
| games | ultimate_tictactoe | `task_games__ultimate_tictactoe__small_board_status_count` | ['bbox_set'] | 100 | 306 | 100 | 100 | 100 | pass |
