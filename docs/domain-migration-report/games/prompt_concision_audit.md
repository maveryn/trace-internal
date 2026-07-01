# Prompt Concision Audit

- rendered prompts: `414`
- tasks covered: `160`
- observed query ids covered: `207`

## Variant Coverage

- tasks with incomplete query ids or generation errors: `0`

| task | expected_query_ids | collected_query_id_counts | generated | issues |
| --- | --- | --- | ---: | --- |
| task_games__2048__max_tile_value | `single` | `{'single': 1}` | 2 | `` |
| task_games__2048__merge_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__2048__move_result_board_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__backgammon__destination_count | `blocked_destination_count, hit_move_count, legal_move_count` | `{'blocked_destination_count': 1, 'hit_move_count': 1, 'legal_move_count': 1}` | 3 | `` |
| task_games__backgammon__point_state_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__battleship__last_ship_cell_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__battleship__ship_cell_status_count | `named_ship_hit_cell_count, named_ship_unhit_cell_count` | `{'named_ship_hit_cell_count': 1, 'named_ship_unhit_cell_count': 1}` | 2 | `` |
| task_games__battleship__ship_status_count | `partial_ship_count, sunk_ship_count` | `{'partial_ship_count': 1, 'sunk_ship_count': 1}` | 2 | `` |
| task_games__bingo__called_number_match_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__bingo__completed_column_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__bingo__completed_line_sum_value | `single` | `{'single': 1}` | 2 | `` |
| task_games__bingo__near_complete_line_count | `near_complete_column_count, near_complete_row_count` | `{'near_complete_column_count': 1, 'near_complete_row_count': 1}` | 2 | `` |
| task_games__bowling__first_pin_hit_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__bowling__spare_path_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__brick_breaker__hit_row_remaining_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__brick_breaker__next_hit_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__brick_breaker__paddle_catch_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__bubble_shooter__drop_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__bubble_shooter__pop_color_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__bubble_shooter__pop_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__cards__blackjack_best_hand_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__cards__exact_triple_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__cards__higher_than_reference_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__cards__longest_run_length | `single` | `{'single': 1}` | 2 | `` |
| task_games__cards__missing_card_to_complete_hand_label | `missing_flush_card_label, missing_full_house_card_label, missing_straight_card_label, missing_three_of_kind_card_label` | `{'missing_flush_card_label': 1, 'missing_full_house_card_label': 1, 'missing_straight_card_label': 1, 'missing_three_of_kind_card_label': 1}` | 4 | `` |
| task_games__cards__poker_best_hand_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__cards__poker_draw_card_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__cards__same_suit_as_reference_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__cards__trick_taking_winner_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__cards__trick_winning_play_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__checkers__max_capture_chain_length | `single` | `{'single': 1}` | 2 | `` |
| task_games__checkers__move_count | `capture_move_count, legal_move_count` | `{'capture_move_count': 1, 'legal_move_count': 1}` | 2 | `` |
| task_games__checkers__piece_mobility_count | `piece_with_capture_move_count, piece_with_legal_move_count` | `{'piece_with_capture_move_count': 1, 'piece_with_legal_move_count': 1}` | 2 | `` |
| task_games__checkers__piece_state_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__chess__checkmate_move_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__chess__colored_piece_kind_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__chess__king_escape_square_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__chess__marked_piece_blocker_count | `bishop_diagonal_blocker_count, queen_line_blocker_count, rook_line_blocker_count` | `{'bishop_diagonal_blocker_count': 1, 'queen_line_blocker_count': 1, 'rook_line_blocker_count': 1}` | 3 | `` |
| task_games__chess__marked_piece_destination_count | `marked_piece_capture_count, marked_piece_move_count` | `{'marked_piece_capture_count': 1, 'marked_piece_move_count': 1}` | 2 | `` |
| task_games__chess__piece_kind_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__chess__player_capture_piece_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__chess__target_square_attacker_count | `black_piece_attacks_target_square_count, king_square_attacker_count, white_piece_attacks_target_square_count` | `{'black_piece_attacks_target_square_count': 1, 'king_square_attacker_count': 1, 'white_piece_attacks_target_square_count': 1}` | 3 | `` |
| task_games__chess_variant__marked_piece_destination_count | `marked_piece_capture_count, marked_piece_move_count` | `{'marked_piece_capture_count': 1, 'marked_piece_move_count': 1}` | 2 | `` |
| task_games__chess_variant__target_square_reacher_count | `black_piece_reaches_target_count, white_piece_reaches_target_count` | `{'black_piece_reaches_target_count': 1, 'white_piece_reaches_target_count': 1}` | 2 | `` |
| task_games__circular_chess__marked_piece_destination_count | `marked_piece_capture_count, marked_piece_move_count` | `{'marked_piece_capture_count': 1, 'marked_piece_move_count': 1}` | 2 | `` |
| task_games__circular_chess__target_cell_reacher_count | `black_piece_reaches_target_count, white_piece_reaches_target_count` | `{'black_piece_reaches_target_count': 1, 'white_piece_reaches_target_count': 1}` | 2 | `` |
| task_games__connect_four__column_disc_profile_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__connect_four__winning_move_column_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__connect_four__winning_move_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__crossing__first_exit_object_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__crossing__hit_object_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__crossing__moving_object_direction_count | `left_moving_object_count, right_moving_object_count` | `{'left_moving_object_count': 1, 'right_moving_object_count': 1}` | 2 | `` |
| task_games__darts__bullseye_membership_count | `inside_bullseye_count, outside_bullseye_count` | `{'inside_bullseye_count': 1, 'outside_bullseye_count': 1}` | 2 | `` |
| task_games__darts__dart_score_value | `single` | `{'single': 1}` | 2 | `` |
| task_games__dominoes__double_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__dominoes__higher_sum_than_reference_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__dominoes__invalid_join_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__dominoes__longest_chain_length_value | `single` | `{'single': 1}` | 2 | `` |
| task_games__dominoes__matching_end_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__dominoes__sum_to_target_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__dots_and_boxes__completable_box_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__dots_and_boxes__owned_box_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__dots_and_boxes__three_sided_box_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__go__group_adjacent_enemy_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__go__group_liberty_count | `marked_group_liberty_count, marked_group_shared_liberty_count` | `{'marked_group_liberty_count': 1, 'marked_group_shared_liberty_count': 1}` | 2 | `` |
| task_games__go__marked_group_stone_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__hex__candidate_neighbor_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__hex__connection_gap_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__hex__winning_move_cell_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__irregular_link_board__capture_move_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__irregular_link_board__marked_piece_destination_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__lane_runner__path_coin_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__lane_runner__safe_path_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__ludo_board__capture_roll_option_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__ludo_board__move_result_option_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__ludo_board__winning_roll_value | `single` | `{'single': 1}` | 2 | `` |
| task_games__mancala_pit_board__post_sow_pit_count_value | `single` | `{'single': 1}` | 2 | `` |
| task_games__mancala_pit_board__sowing_landing_option_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__marble_chain__max_pop_direction_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__marble_chain__shot_effect_value | `single` | `{'single': 1}` | 2 | `` |
| task_games__match3__gem_count | `column_color_gem_count, grid_color_gem_count, row_color_gem_count` | `{'column_color_gem_count': 1, 'grid_color_gem_count': 1, 'row_color_gem_count': 1}` | 3 | `` |
| task_games__match3__max_clear_swap_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__minecraft__resource_route_cost | `single` | `{'single': 1}` | 2 | `` |
| task_games__minecraft__stack_height_condition_count | `at_least_height_count, exact_height_count` | `{'at_least_height_count': 1, 'exact_height_count': 1}` | 2 | `` |
| task_games__minecraft__top_ore_stack_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__minesweeper__forced_cell_count | `forced_mine_count, forced_safe_count` | `{'forced_mine_count': 1, 'forced_safe_count': 1}` | 2 | `` |
| task_games__minesweeper__forced_mine_cell_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__minesweeper__remaining_mine_count_value | `single` | `{'single': 1}` | 2 | `` |
| task_games__minigolf__first_obstacle_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__minigolf__shot_path_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__nine_mens_morris__mill_completion_point_count | `black_mill_completion_point_count, white_mill_completion_point_count` | `{'black_mill_completion_point_count': 1, 'white_mill_completion_point_count': 1}` | 2 | `` |
| task_games__nine_mens_morris__pieces_in_mill_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__pacman__next_item_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__pacman__path_pellet_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__pacman__pellet_count_before_ghost | `single` | `{'single': 1}` | 2 | `` |
| task_games__pacman__route_score_value | `single` | `{'single': 1}` | 2 | `` |
| task_games__pinball_table__first_hit_object_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__pinball_table__scoreable_object_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__platformer__collectible_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__platformer__jump_collectible_score_value | `single` | `{'single': 1}` | 2 | `` |
| task_games__platformer__jump_landing_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__pool__blocking_ball_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__pool__group_ball_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__racing_track__ahead_object_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__racing_track__finish_distance_extremum_label | `closest_to_finish_label, farthest_from_finish_label` | `{'closest_to_finish_label': 1, 'farthest_from_finish_label': 1}` | 2 | `` |
| task_games__radial_hunt_board__capture_move_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__radial_hunt_board__marked_piece_destination_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__reversi__frontier_disc_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__reversi__legal_destination_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__reversi__marked_move_flip_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__rhythm__earliest_hit_lane_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__rhythm__lane_note_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__rhythm__lane_note_score_value | `single` | `{'single': 1}` | 2 | `` |
| task_games__rhythm__most_notes_lane_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__rule_override_board__line_result_count | `line_override_loss_count, line_override_win_count` | `{'line_override_loss_count': 1, 'line_override_win_count': 1}` | 2 | `` |
| task_games__rule_override_board__piece_result_count | `piece_override_loss_count, piece_override_win_count` | `{'piece_override_loss_count': 1, 'piece_override_win_count': 1}` | 2 | `` |
| task_games__sixteen_soldiers__marked_piece_capture_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__sixteen_soldiers__marked_piece_destination_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__sliding_block__block_orientation_count | `horizontal_block_count, vertical_block_count` | `{'horizontal_block_count': 1, 'vertical_block_count': 1}` | 2 | `` |
| task_games__sliding_block__movable_block_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__sliding_block__sliding_block_blocker_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__sliding_block__sliding_block_move_result_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__slot_machine__paytable_score_value | `single` | `{'single': 1}` | 2 | `` |
| task_games__slot_machine__reel_completion_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__slot_machine__winning_payline_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__snake__path_outcome_option_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__snake__safe_direction_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__snake__snake_length_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__snakes_ladders__move_outcome_value | `single` | `{'single': 1}` | 2 | `` |
| task_games__snakes_ladders__remaining_to_finish_value | `single` | `{'single': 1}` | 2 | `` |
| task_games__snakes_ladders__special_square_count | `ladder_count, snake_count` | `{'ladder_count': 1, 'snake_count': 1}` | 2 | `` |
| task_games__sokoban__box_goal_status_count | `box_off_goal_count, box_on_goal_count` | `{'box_off_goal_count': 1, 'box_on_goal_count': 1}` | 2 | `` |
| task_games__sokoban__closest_box_goal_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__sokoban__push_stand_cell_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__solitaire__cascade_card_at_depth_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__solitaire__column_card_count_value | `single` | `{'single': 1}` | 2 | `` |
| task_games__solitaire__foundation_ready_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__solitaire__move_legality_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__solitaire__tableau_movable_card_count_value | `single` | `{'single': 1}` | 2 | `` |
| task_games__space_shooter__enemy_ship_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__space_shooter__enemy_ship_hit_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__space_shooter__first_hit_enemy_ship_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__space_shooter__hit_enemy_ship_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__space_shooter__safe_lane_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__tetris__active_piece_shape_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__tetris__drop_collision_time_value | `left_shift_collision_time, no_shift_collision_time, right_shift_collision_time` | `{'left_shift_collision_time': 1, 'no_shift_collision_time': 1, 'right_shift_collision_time': 1}` | 3 | `` |
| task_games__tetris__drop_result_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__tetris__edge_occupied_row_cell_count | `bottom_occupied_row_empty_cell_count, bottom_occupied_row_filled_cell_count, top_occupied_row_empty_cell_count, top_occupied_row_filled_cell_count` | `{'bottom_occupied_row_empty_cell_count': 1, 'bottom_occupied_row_filled_cell_count': 1, 'top_occupied_row_empty_cell_count': 1, 'top_occupied_row_filled_cell_count': 1}` | 4 | `` |
| task_games__tetris__line_clear_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__tetris__row_occupancy_status_count | `full_row_count, one_gap_row_count` | `{'full_row_count': 1, 'one_gap_row_count': 1}` | 2 | `` |
| task_games__tic_tac_toe_3d__layer_piece_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__tic_tac_toe_3d__winning_move_cell_label | `o_winning_move_label, x_winning_move_label` | `{'o_winning_move_label': 1, 'x_winning_move_label': 1}` | 2 | `` |
| task_games__tower_defense__best_tower_position_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__tower_defense__covered_path_segment_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__tower_defense__nearest_exit_enemy_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__tower_draughts_board__controlled_stack_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__tower_draughts_board__marked_stack_capture_count | `single` | `{'single': 1}` | 2 | `` |
| task_games__ultimate_tictactoe__line_completion_move_label | `o_blocking_move_label, o_winning_move_label, x_blocking_move_label, x_winning_move_label` | `{'o_blocking_move_label': 1, 'o_winning_move_label': 1, 'x_blocking_move_label': 1, 'x_winning_move_label': 1}` | 4 | `` |
| task_games__ultimate_tictactoe__macro_threat_board_count | `o_immediate_win_board_count, x_immediate_win_board_count` | `{'o_immediate_win_board_count': 1, 'x_immediate_win_board_count': 1}` | 2 | `` |
| task_games__ultimate_tictactoe__small_board_status_count | `drawn_board_count, neither_won_board_count, o_won_board_count, x_won_board_count` | `{'drawn_board_count': 1, 'neither_won_board_count': 1, 'o_won_board_count': 1, 'x_won_board_count': 1}` | 4 | `` |

## Longest Prompts

### task_games__chess_variant__target_square_reacher_count / answer_and_annotation / sample 8969480411857182

- `query_id`: `black_piece_reaches_target_count`
- `instance_seed`: `8969480411857182`
- `word_count`: `187`
- `body_word_count`: `120`

```text
You are shown a chess-like 8 by 8 board with a small set of white and black chess pieces and a visible movement rule card. The rule card says pieces move diagonally up to 3 squares. White pieces are one side and black pieces are the other side. Every piece uses the displayed movement rule. The blue outlined square is the target square. A counted piece may move to the target square if the target is empty or contains an opponent piece, but not if it contains a friendly piece. For range rules, movement stops at the first occupied square in each direction and cannot pass through it. Count the Black pieces that can reach the blue outlined target square.
Annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for every black piece that can legally move to the blue outlined target square.
Answer format: set "answer" to the number of black pieces that can legally move to the blue outlined target square.
Example JSON:
{"annotation":[[140,220,210,290],[210,220,280,290],[280,220,350,290]],"answer":3}
```

### task_games__chess_variant__target_square_reacher_count / answer_and_annotation / sample 551304661166316

- `query_id`: `white_piece_reaches_target_count`
- `instance_seed`: `551304661166316`
- `word_count`: `180`
- `body_word_count`: `111`

```text
The image shows a chess-like 8 by 8 board with a small set of white and black chess pieces and a visible movement rule card. White pieces are one side and black pieces are the other side. Every piece uses the displayed movement rule. The blue outlined square is the target square. Using the displayed movement rule, how many White pieces can move to that square? A counted piece may move to the target square if the target is empty or contains an opponent piece, but not if it contains a friendly piece. For range rules, movement stops at the first occupied square in each direction and cannot pass through it.
Required annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for every white piece that can legally move to the blue outlined target square.
Required answer format: set "answer" to the number of white pieces that can legally move to the blue outlined target square.
Example JSON:
{"annotation":[[140,220,210,290],[210,220,280,290],[280,220,350,290]],"answer":3}
```

### task_games__chess_variant__marked_piece_destination_count / answer_and_annotation / sample 6889077305685315

- `query_id`: `marked_piece_move_count`
- `instance_seed`: `6889077305685315`
- `word_count`: `174`
- `body_word_count`: `112`

```text
The visual shows a chess-like 8 by 8 board with many white and black chess pieces and a visible movement rule card. The rule card says the marked piece moves diagonally up to 3 squares. The marked piece may land on an empty square or an opponent piece, but not on a friendly piece. For range rules, movement stops at the first occupied square in each direction and cannot pass through it. White pieces are one side and black pieces are the other side. Every piece uses the displayed movement rule. The red outlined square contains the marked piece. What is the number of legal squares the marked piece can move to?
Final answer format: set "answer" to the count of legal destination squares for the marked piece.
Annotation format: set "annotation" to a JSON array of pixel-space square boxes [x0, y0, x1, y1] for every legal destination square of the marked piece.
Example JSON:
{"annotation":[[140,220,210,290],[210,220,280,290],[280,220,350,290],[350,220,420,290]],"answer":4}
```

### task_games__circular_chess__target_cell_reacher_count / answer_and_annotation / sample 7841531722063098

- `query_id`: `black_piece_reaches_target_count`
- `instance_seed`: `7841531722063098`
- `word_count`: `173`
- `body_word_count`: `114`

```text
The scene contains a circular chess board with four rings, sixteen sectors per ring, and a small set of white and black chess pieces. Use standard chess movement on this circular board. Rooks move around rings or across rings, bishops move diagonally between rings and sectors, queens combine rook and bishop movement, knights jump, and kings move one step. Sectors wrap around each ring; rings do not wrap inward or outward. A piece may land on an empty cell or an opponent piece, but not on a friendly piece. Sliding pieces stop at the first occupied cell in a direction. Count every Black piece that has the red marked cell as a legal destination.
Annotation format: set "annotation" to a JSON array of pixel-space points [x, y] at the centers of every Black piece that can move to the red marked target cell.
Answer format: set "answer" to the number of Black pieces that can move to the red marked target cell.
Example JSON:
{"annotation":[[420,210],[502,244],[536,328]],"answer":3}
```

### task_games__snake__path_outcome_option_label / answer_and_annotation / sample 3245331601158289

- `query_id`: `single`
- `instance_seed`: `3245331601158289`
- `word_count`: `173`
- `body_word_count`: `102`

```text
The visual shows a Snake game board with a yellow snake head, connected body cells, red food, and gray wall cells. A move is safe when the head stays inside the board and does not enter the snake body or a gray wall cell. Moving onto red food counts as safe. The planned moves are 1. RIGHT, 2. LEFT, 3. UP, 4. DOWN. Choose the labeled option in the image that matches the result: a marked point cell or GAME OVER. For a game-over result, use boxes around the visible in-board head path cells up to the hit cell or board edge.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] around the in-board cells the head traverses until the result; for an off-board hit, use the visible path cells up to the board edge.
Answer format: set "answer" to the option letter shown in the image, one of "A", "B", "C", or "D".
Example JSON:
{"annotation":[[338,332,410,404],[410,332,482,404],[482,332,554,404]],"answer":"B"}
```

### task_games__circular_chess__target_cell_reacher_count / answer_and_annotation / sample 179360609203867

- `query_id`: `white_piece_reaches_target_count`
- `instance_seed`: `179360609203867`
- `word_count`: `169`
- `body_word_count`: `110`

```text
The figure shows a circular chess board with four rings, sixteen sectors per ring, and many white and black chess pieces. How many White pieces could legally move onto the red marked target cell? Sectors wrap around each ring; rings do not wrap inward or outward. Use standard chess movement on this circular board. Rooks move around rings or across rings, bishops move diagonally between rings and sectors, queens combine rook and bishop movement, knights jump, and kings move one step. A piece may land on an empty cell or an opponent piece, but not on a friendly piece. Sliding pieces stop at the first occupied cell in a direction.
Annotation format: set "annotation" to a JSON array of pixel-space points [x, y] at the centers of every White piece that can move to the red marked target cell.
Answer format: set "answer" to the number of White pieces that can move to the red marked target cell.
Example JSON:
{"annotation":[[420,210],[502,244],[536,328]],"answer":3}
```

### task_games__chess_variant__marked_piece_destination_count / answer_and_annotation / sample 5419749470631630

- `query_id`: `marked_piece_capture_count`
- `instance_seed`: `5419749470631630`
- `word_count`: `167`
- `body_word_count`: `108`

```text
The figure shows a chess-like 8 by 8 board with many white and black chess pieces and a visible movement rule card. White pieces are one side and black pieces are the other side. Every piece uses the displayed movement rule. The red outlined square contains the marked piece. The rule card says the marked piece jumps exactly 3 rows and 1 column, or 1 row and 3 columns. The marked piece may land on an empty square or an opponent piece, but not on a friendly piece. For jump rules, the marked piece may jump over occupied squares. Count the opponent pieces capturable by the marked piece.
Annotation format: set "annotation" to a JSON array of pixel-space square boxes [x0, y0, x1, y1] for every destination square occupied by an opponent piece that the marked piece can capture.
Answer format: set "answer" to the count of capture destination squares for the marked piece.
Example JSON:
{"annotation":[[140,220,210,290],[210,220,280,290]],"answer":2}
```

### task_games__snakes_ladders__move_outcome_value / answer_and_annotation / sample 1560067821300292

- `query_id`: `single`
- `instance_seed`: `1560067821300292`
- `word_count`: `164`
- `body_word_count`: `111`

```text
The scene shows a numbered Snakes and Ladders board with one token and visible snakes and ladders. A move advances the token by the selected die value, then immediately follows a ladder upward or a snake downward if the landing square is the start of one. A ladder starts at its lower square and ends at the arrowhead on the higher square; a snake starts at its head and ends at its pointed tail on the lower square. If a die roll would move past the final square, the token stays on its current square for that roll. Move once using the shown die; what square is the token on afterward?
Annotation format: set "annotation" to a JSON object mapping start_square and end_square to bounding boxes [x0, y0, x1, y1].
Answer format: set "answer" to the final square number after the shown die roll and any snake or ladder.
Example JSON:
{"annotation":{"start_square":[88,682,178,772],"end_square":[462,398,552,488]},"answer":31}
```

### task_games__battleship__ship_status_count / answer_and_annotation / sample 6216507372498437

- `query_id`: `partial_ship_count`
- `instance_seed`: `6216507372498437`
- `word_count`: `162`
- `body_word_count`: `75`

```text
The visual shows a Battleship tracking grid with red hit markers, gray miss markers, optional candidate labels, and a fleet-shape panel for Line 5, Line 4, Line 3, Square 2x2, and L 3 beside the grid. Each fleet ship is placed exactly once on the board. A ship is sunk only when every cell of that ship has a red hit marker. Determine the number of ships that have some, but not all, cells hit.
Annotation format: set "annotation" to a JSON object mapping each partially hit ship's displayed fleet-shape name to a list of pixel-space cell boxes [x0, y0, x1, y1] for every red hit-marker cell on that ship; use an empty object if no ship is partially hit.
Answer format: set "answer" to the number of ships that have at least one red hit marker but are not sunk.
Example JSON:
{"annotation":{"Line 4":[[195,265,225,295],[225,265,255,295]],"L 3":[[195,475,225,505]]},"answer":2}
```

### task_games__marble_chain__shot_effect_value / answer_and_annotation / sample 7598429217710859

- `query_id`: `single`
- `instance_seed`: `7598429217710859`
- `word_count`: `156`
- `body_word_count`: `86`

```text
The scene shows a Zuma-like marble-chain board with a central shooter, a colored shooter marble, arrow shot options, and colored marbles on a curved track. Fire the shooter marble straight along the chosen arrow. It inserts at the chain gap indicated by that arrow. If the inserted marble's same-color contiguous run has at least three marbles, the existing marbles in that run are removed and the chain closes once. Do not apply any later cascade. Count the existing marbles that pop after the shown marked shot.
Required annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one for each existing chain marble that would pop; use an empty array if none pop.
Required answer format: set "answer" to the number of existing chain marbles removed by the marked shot, excluding the shooter marble.
Example JSON:
{"annotation":[[430,206,466,242],[484,224,520,260],[533,258,569,294],[572,304,608,340]],"answer":4}
```

### task_games__battleship__ship_status_count / answer_and_annotation / sample 7372897504446350

- `query_id`: `sunk_ship_count`
- `instance_seed`: `7372897504446350`
- `word_count`: `152`
- `body_word_count`: `71`

```text
The visual shows a Battleship tracking grid with red hit markers, gray miss markers, optional candidate labels, and a fleet-shape panel for Line 5, Line 4, Line 3, Square 2x2, and L 3 beside the grid. Each fleet ship is placed exactly once on the board. A ship is sunk only when every cell of that ship has a red hit marker. Determine the number of sunk ships on the board.
Annotation format: set "annotation" to a JSON object mapping each sunk ship's displayed fleet-shape name to a list of pixel-space cell boxes [x0, y0, x1, y1] for every red hit-marker cell on that ship; use an empty object if no ship is sunk.
Answer format: set "answer" to the number of ships whose every cell has a red hit marker.
Example JSON:
{"annotation":{"Line 5":[[195,205,225,235],[225,205,255,235]],"Line 3":[[195,325,225,355]]},"answer":2}
```

### task_games__backgammon__destination_count / answer_and_annotation / sample 3689716281841559

- `query_id`: `blocked_destination_count`
- `instance_seed`: `3689716281841559`
- `word_count`: `148`
- `body_word_count`: `94`

```text
This scene shows a numbered backgammon board with black and white checker stacks and two dice. The board header shows which player moves and whether that player moves 24 to 1 or 1 to 24. For each occupied active-player point, use either shown die in that direction to get a candidate destination number. Count each distinct destination number once, even if more than one checker or die reaches it. A destination point with two or more opposing checkers is blocked. Considering the active player's possible single-die destinations, how many distinct destination points are blocked?
Final answer format: set "answer" to the number of distinct blocked destination points.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] around the distinct possible destination points blocked by two or more opposing checkers.
Example JSON:
{"annotation":[[276,400,341,612],[342,400,407,612],[608,400,673,612]],"answer":3}
```

### task_games__backgammon__destination_count / answer_and_annotation / sample 5640797118990632

- `query_id`: `legal_move_count`
- `instance_seed`: `5640797118990632`
- `word_count`: `144`
- `body_word_count`: `92`

```text
The visual shows a numbered backgammon board with black and white checker stacks and two dice. The board header shows which player moves and whether that player moves 24 to 1 or 1 to 24. For each occupied active-player point, use either shown die in that direction to get a candidate destination number. Count each distinct destination number once, even if more than one checker or die reaches it. A destination point with two or more opposing checkers is blocked. How many distinct destination points can the active player legally move to?
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] around the distinct destination points where the active player can legally move.
Answer format: set "answer" to the number of distinct legal destination points.
Example JSON:
{"annotation":[[144,104,209,316],[210,104,275,316],[608,104,673,316]],"answer":3}
```

### task_games__battleship__ship_cell_status_count / answer_and_annotation / sample 630050909704750

- `query_id`: `named_ship_hit_cell_count`
- `instance_seed`: `630050909704750`
- `word_count`: `144`
- `body_word_count`: `72`

```text
The scene shows a Battleship tracking grid with red hit markers, gray miss markers, optional candidate labels, and a fleet-shape panel for Line 5, Line 4, Line 3, Square 2x2, and L 3 beside the grid. Each fleet ship is placed exactly once on the board. A ship is sunk only when every cell of that ship has a red hit marker. Determine the number of red hit markers on Line 4.
Annotation format: set "annotation" to a JSON array of pixel-space cell boxes [x0, y0, x1, y1] for the red hit-marker cells on the named ship; use an empty array if none of that ship's cells are hit.
Answer format: set "answer" to the number of cells on the named ship that have red hit markers.
Example JSON:
{"annotation":[[195,205,225,235],[225,205,255,235],[255,205,285,235]],"answer":3}
```

### task_games__chess_variant__target_square_reacher_count / answer_only / sample 8969480411857182

- `query_id`: `black_piece_reaches_target_count`
- `instance_seed`: `8969480411857182`
- `word_count`: `144`
- `body_word_count`: `120`

```text
You are shown a chess-like 8 by 8 board with a small set of white and black chess pieces and a visible movement rule card. The rule card says pieces move diagonally up to 3 squares. White pieces are one side and black pieces are the other side. Every piece uses the displayed movement rule. The blue outlined square is the target square. A counted piece may move to the target square if the target is empty or contains an opponent piece, but not if it contains a friendly piece. For range rules, movement stops at the first occupied square in each direction and cannot pass through it. Count the Black pieces that can reach the blue outlined target square.
Answer format: set "answer" to the number of black pieces that can legally move to the blue outlined target square.
Example JSON:
{"answer":3}
```

### task_games__backgammon__destination_count / answer_and_annotation / sample 5950614440045382

- `query_id`: `hit_move_count`
- `instance_seed`: `5950614440045382`
- `word_count`: `143`
- `body_word_count`: `92`

```text
This scene shows a numbered backgammon board with black and white checker stacks and two dice. The board header shows which player moves and whether that player moves 24 to 1 or 1 to 24. For each occupied active-player point, use either shown die in that direction to get a candidate destination number. Count each distinct destination number once, even if more than one checker or die reaches it. A destination point with two or more opposing checkers is blocked. How many distinct single-die destinations are hit moves for the active player?
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] around the distinct destination points where the active player would hit exactly one opposing checker.
Answer format: set "answer" to the number of distinct hit destination points.
Example JSON:
{"annotation":[[410,104,475,316],[608,104,673,316]],"answer":2}
```

### task_games__checkers__max_capture_chain_length / answer_and_annotation / sample 1713661661325778

- `query_id`: `single`
- `instance_seed`: `1713661661325778`
- `word_count`: `143`
- `body_word_count`: `74`

```text
The visual shows an 8 by 8 checkers board with red and black pieces. Black to move. A jump captures one adjacent opponent piece and lands on the empty square beyond. The outlined checker is a king; it may capture diagonally in any direction, remove the jumped piece, and continue jumping from each landing square while another capture is available. Count the largest possible number of captures in one chain for the marked king.
Required annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for the opponent pieces captured along the longest chain.
Required answer format: set "answer" to the maximum number of opponent pieces the marked king can capture in one continuous jump chain.
Example JSON:
{"annotation":[[144,200,184,240],[216,272,256,312],[288,344,328,384],[360,416,400,456]],"answer":4}
```

### task_games__space_shooter__enemy_ship_hit_count / answer_and_annotation / sample 1456636717856132

- `query_id`: `single`
- `instance_seed`: `1456636717856132`
- `word_count`: `142`
- `body_word_count`: `82`

```text
The visual shows a retro space-shooter playfield with enemy ships, red downward enemy shots, blue upward player shots, a player ship, and bottom lane pads. Count enemy ships that can be destroyed by the current blue shots. Each blue shot hits one ship above it in the same vertical lane, starting from the lower ships. Bottom lane pads define the vertical lanes. Enemy ships and shots stay in their own lane; red enemy shots move downward and blue player shots move upward.
Final answer format: set "answer" to the number of enemy ships that can be destroyed by the current blue shots.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] for the enemy ships that can be destroyed by blue player shots.
Example JSON:
{"annotation":[[140,130,202,178],[420,250,482,298],[700,170,762,218]],"answer":3}
```

### task_games__battleship__ship_cell_status_count / answer_and_annotation / sample 8942211811482471

- `query_id`: `named_ship_unhit_cell_count`
- `instance_seed`: `8942211811482471`
- `word_count`: `141`
- `body_word_count`: `74`

```text
The visual shows a Battleship tracking grid with red hit markers, gray miss markers, optional candidate labels, and a fleet-shape panel for Line 5, Line 4, Line 3, Square 2x2, and L 3 beside the grid. Each fleet ship is placed exactly once on the board. A ship is sunk only when every cell of that ship has a red hit marker. Determine the number of cells without red hit markers on Line 3.
Annotation format: set "annotation" to a JSON array of pixel-space cell boxes [x0, y0, x1, y1] for the named ship's intact cells; use an empty array if every cell of that ship is hit.
Answer format: set "answer" to the number of cells on the named ship that do not have red hit markers.
Example JSON:
{"annotation":[[285,205,315,235],[315,205,345,235]],"answer":2}
```

### task_games__circular_chess__marked_piece_destination_count / answer_and_annotation / sample 2544417858435633

- `query_id`: `marked_piece_move_count`
- `instance_seed`: `2544417858435633`
- `word_count`: `138`
- `body_word_count`: `85`

```text
The image shows a circular chess board with four rings, sixteen sectors per ring, and many white and black chess pieces. Use the marked piece's standard chess movement on this circular board. Sectors wrap around each ring; rings do not wrap inward or outward. A piece may land on an empty cell or an opponent piece, but not on a friendly piece. Sliding pieces stop at the first occupied cell in a direction. How many legal movement destinations are available to the red marked piece?
Required annotation format: set "annotation" to a JSON array of pixel-space points [x, y] at the centers of every legal destination cell for the marked piece.
Required answer format: set "answer" to the number of legal destination cells for the marked piece.
Example JSON:
{"annotation":[[420,210],[502,244],[536,328]],"answer":3}
```

### task_games__minesweeper__forced_cell_count / answer_and_annotation / sample 3403252503280498

- `query_id`: `forced_mine_count`
- `instance_seed`: `3403252503280498`
- `word_count`: `138`
- `body_word_count`: `86`

```text
The figure shows a Minesweeper grid with opened number cells, hidden cells, flags, and extra hidden distractor cells. In Minesweeper, each opened number tells how many mines are in its eight neighboring cells, and each flag marks a known mine. If a number already has that many adjacent flags, its other hidden neighbors are safe. If the number still needs exactly all remaining hidden neighbors, those hidden neighbors are mines. Use the outlined opened clue cell(s). How many hidden cells are forced to be mines?
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one for each hidden cell forced to be a mine.
Answer format: set "answer" to the count of hidden cells that must be mines.
Example JSON:
{"annotation":[[147,227,203,283],[217,227,273,283],[287,227,343,283]],"answer":3}
```

### task_games__circular_chess__marked_piece_destination_count / answer_and_annotation / sample 2042779560694741

- `query_id`: `marked_piece_capture_count`
- `instance_seed`: `2042779560694741`
- `word_count`: `137`
- `body_word_count`: `87`

```text
The scene contains a circular chess board with four rings, sixteen sectors per ring, and a small set of white and black chess pieces. Use the marked piece's standard chess movement on this circular board. Sectors wrap around each ring; rings do not wrap inward or outward. A piece may land on an empty cell or an opponent piece, but not on a friendly piece. Sliding pieces stop at the first occupied cell in a direction. How many capture destinations are available to the red marked piece?
Annotation format: set "annotation" to a JSON array of pixel-space points [x, y] at the centers of every opponent-occupied destination cell the marked piece can capture.
Answer format: set "answer" to the number of opponent pieces the marked piece can capture.
Example JSON:
{"annotation":[[420,210],[502,244]],"answer":2}
```

### task_games__circular_chess__target_cell_reacher_count / answer_only / sample 7841531722063098

- `query_id`: `black_piece_reaches_target_count`
- `instance_seed`: `7841531722063098`
- `word_count`: `137`
- `body_word_count`: `114`

```text
The scene contains a circular chess board with four rings, sixteen sectors per ring, and a small set of white and black chess pieces. Use standard chess movement on this circular board. Rooks move around rings or across rings, bishops move diagonally between rings and sectors, queens combine rook and bishop movement, knights jump, and kings move one step. Sectors wrap around each ring; rings do not wrap inward or outward. A piece may land on an empty cell or an opponent piece, but not on a friendly piece. Sliding pieces stop at the first occupied cell in a direction. Count every Black piece that has the red marked cell as a legal destination.
Answer format: set "answer" to the number of Black pieces that can move to the red marked target cell.
Example JSON:
{"answer":3}
```

### task_games__minesweeper__forced_cell_count / answer_and_annotation / sample 3763056537079632

- `query_id`: `forced_safe_count`
- `instance_seed`: `3763056537079632`
- `word_count`: `137`
- `body_word_count`: `85`

```text
This scene shows a Minesweeper grid with opened number cells, hidden cells, flags, and extra hidden distractor cells. In Minesweeper, each opened number tells how many mines are in its eight neighboring cells, and each flag marks a known mine. If a number already has that many adjacent flags, its other hidden neighbors are safe. If the number still needs exactly all remaining hidden neighbors, those hidden neighbors are mines. Use the outlined opened clue cell(s). Count the hidden cells that cannot contain mines.
Final answer format: set "answer" to the count of hidden cells that must be safe.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one for each hidden cell forced to be safe.
Example JSON:
{"annotation":[[147,227,203,283],[217,227,273,283],[287,227,343,283]],"answer":3}
```

### task_games__chess_variant__target_square_reacher_count / answer_only / sample 551304661166316

- `query_id`: `white_piece_reaches_target_count`
- `instance_seed`: `551304661166316`
- `word_count`: `136`
- `body_word_count`: `111`

```text
The image shows a chess-like 8 by 8 board with a small set of white and black chess pieces and a visible movement rule card. White pieces are one side and black pieces are the other side. Every piece uses the displayed movement rule. The blue outlined square is the target square. Using the displayed movement rule, how many White pieces can move to that square? A counted piece may move to the target square if the target is empty or contains an opponent piece, but not if it contains a friendly piece. For range rules, movement stops at the first occupied square in each direction and cannot pass through it.
Required answer format: set "answer" to the number of white pieces that can legally move to the blue outlined target square.
Example JSON:
{"answer":3}
```

## Repeated Scaffolding Terms

### task_games__ultimate_tictactoe__small_board_status_count / answer_and_annotation / sample 3815539239753956

- `query_id`: `neither_won_board_count`
- `instance_seed`: `3815539239753956`
- `word_count`: `110`
- `body_word_count`: `57`
- `repeated_terms`: `{'board': 5}`

```text
This game board shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. A small board is won by X or O when that player has three marks in a row inside that small board. A drawn small board is full and has no winner. Count the small boards that neither X nor O has won.
Required annotation format: set "annotation" to an array containing the [x0, y0, x1, y1] boxes of all small boards that neither player has won.
Required answer format: set "answer" to the number of small boards that neither player has won.
Example JSON:
{"annotation":[[110,110,260,260],[450,280,600,430]],"answer":2}
```

### task_games__ultimate_tictactoe__small_board_status_count / answer_and_annotation / sample 6863603579111245

- `query_id`: `x_won_board_count`
- `instance_seed`: `6863603579111245`
- `word_count`: `103`
- `body_word_count`: `55`
- `repeated_terms`: `{'board': 5}`

```text
This game board shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. A small board is won by X or O when that player has three marks in a row inside that small board. A drawn small board is full and has no winner. Determine how many small boards are won by X.
Final answer format: set "answer" to the number of small boards won by X.
Annotation format: set "annotation" to an array containing the [x0, y0, x1, y1] boxes of all small boards won by X.
Example JSON:
{"annotation":[[110,110,260,260],[450,280,600,430]],"answer":2}
```

### task_games__ultimate_tictactoe__small_board_status_count / answer_and_annotation / sample 3135051356869887

- `query_id`: `drawn_board_count`
- `instance_seed`: `3135051356869887`
- `word_count`: `97`
- `body_word_count`: `52`
- `repeated_terms`: `{'board': 5}`

```text
This game board shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. A small board is won by X or O when that player has three marks in a row inside that small board. A drawn small board is full and has no winner. How many small boards are drawn?
Required annotation format: set "annotation" to an array containing the [x0, y0, x1, y1] boxes of all drawn small boards.
Required answer format: set "answer" to the number of drawn small boards.
Example JSON:
{"annotation":[[110,110,260,260],[450,280,600,430]],"answer":2}
```

### task_games__ultimate_tictactoe__small_board_status_count / answer_only / sample 3815539239753956

- `query_id`: `neither_won_board_count`
- `instance_seed`: `3815539239753956`
- `word_count`: `77`
- `body_word_count`: `57`
- `repeated_terms`: `{'board': 5}`

```text
This game board shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. A small board is won by X or O when that player has three marks in a row inside that small board. A drawn small board is full and has no winner. Count the small boards that neither X nor O has won.
Required answer format: set "answer" to the number of small boards that neither player has won.
Example JSON:
{"answer":2}
```

### task_games__ultimate_tictactoe__small_board_status_count / answer_only / sample 6863603579111245

- `query_id`: `x_won_board_count`
- `instance_seed`: `6863603579111245`
- `word_count`: `73`
- `body_word_count`: `55`
- `repeated_terms`: `{'board': 5}`

```text
This game board shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. A small board is won by X or O when that player has three marks in a row inside that small board. A drawn small board is full and has no winner. Determine how many small boards are won by X.
Required answer format: set "answer" to the number of small boards won by X.
Example JSON:
{"answer":2}
```

### task_games__ultimate_tictactoe__small_board_status_count / answer_only / sample 3135051356869887

- `query_id`: `drawn_board_count`
- `instance_seed`: `3135051356869887`
- `word_count`: `67`
- `body_word_count`: `52`
- `repeated_terms`: `{'board': 5}`

```text
This game board shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. A small board is won by X or O when that player has three marks in a row inside that small board. A drawn small board is full and has no winner. How many small boards are drawn?
Answer format: set "answer" to the number of drawn small boards.
Example JSON:
{"answer":2}
```

### task_games__snake__path_outcome_option_label / answer_and_annotation / sample 3245331601158289

- `query_id`: `single`
- `instance_seed`: `3245331601158289`
- `word_count`: `173`
- `body_word_count`: `102`
- `repeated_terms`: `{'board': 4}`

```text
The visual shows a Snake game board with a yellow snake head, connected body cells, red food, and gray wall cells. A move is safe when the head stays inside the board and does not enter the snake body or a gray wall cell. Moving onto red food counts as safe. The planned moves are 1. RIGHT, 2. LEFT, 3. UP, 4. DOWN. Choose the labeled option in the image that matches the result: a marked point cell or GAME OVER. For a game-over result, use boxes around the visible in-board head path cells up to the hit cell or board edge.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] around the in-board cells the head traverses until the result; for an off-board hit, use the visible path cells up to the board edge.
Answer format: set "answer" to the option letter shown in the image, one of "A", "B", "C", or "D".
Example JSON:
{"annotation":[[338,332,410,404],[410,332,482,404],[482,332,554,404]],"answer":"B"}
```

### task_games__snake__path_outcome_option_label / answer_only / sample 3245331601158289

- `query_id`: `single`
- `instance_seed`: `3245331601158289`
- `word_count`: `126`
- `body_word_count`: `102`
- `repeated_terms`: `{'board': 4}`

```text
The visual shows a Snake game board with a yellow snake head, connected body cells, red food, and gray wall cells. A move is safe when the head stays inside the board and does not enter the snake body or a gray wall cell. Moving onto red food counts as safe. The planned moves are 1. RIGHT, 2. LEFT, 3. UP, 4. DOWN. Choose the labeled option in the image that matches the result: a marked point cell or GAME OVER. For a game-over result, use boxes around the visible in-board head path cells up to the hit cell or board edge.
Required answer format: set "answer" to the option letter shown in the image, one of "A", "B", "C", or "D".
Example JSON:
{"answer":"B"}
```

### task_games__ultimate_tictactoe__small_board_status_count / answer_and_annotation / sample 4515165754503893

- `query_id`: `o_won_board_count`
- `instance_seed`: `4515165754503893`
- `word_count`: `99`
- `body_word_count`: `52`
- `repeated_terms`: `{'board': 4}`

```text
The visual shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. A small board is won by X or O when that player has three marks in a row inside that small board. A drawn small board is full and has no winner. How many small boards has O won?
Annotation format: set "annotation" to an array containing the [x0, y0, x1, y1] boxes of all small boards won by O.
Answer format: set "answer" to the number of small boards won by O.
Example JSON:
{"annotation":[[110,110,260,260],[450,280,600,430]],"answer":2}
```

### task_games__sliding_block__sliding_block_move_result_label / answer_and_annotation / sample 7801928296850567

- `query_id`: `single`
- `instance_seed`: `7801928296850567`
- `word_count`: `95`
- `body_word_count`: `37`
- `repeated_terms`: `{'board': 4}`

```text
This scene shows a sliding-block puzzle board with labeled rectangular blocks and four final-board options. Use the original board, perform these slides in order: 1. block E slides 2 cells right. Which option is the resulting board?
Annotation format: set "annotation" to a JSON object with keys "source_board" and "selected_option"; each value is an image-pixel bounding box [x0,y0,x1,y1] for the original board and the selected option panel.
Answer format: set "answer" to only the selected option letter.
Example JSON:
{"annotation":{"source_board":[80,120,300,340],"selected_option":[430,500,650,680]},"answer":"B"}
```

### task_games__ultimate_tictactoe__small_board_status_count / answer_only / sample 4515165754503893

- `query_id`: `o_won_board_count`
- `instance_seed`: `4515165754503893`
- `word_count`: `69`
- `body_word_count`: `52`
- `repeated_terms`: `{'board': 4}`

```text
The visual shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. A small board is won by X or O when that player has three marks in a row inside that small board. A drawn small board is full and has no winner. How many small boards has O won?
Answer format: set "answer" to the number of small boards won by O.
Example JSON:
{"answer":2}
```

### task_games__sliding_block__sliding_block_move_result_label / answer_only / sample 7801928296850567

- `query_id`: `single`
- `instance_seed`: `7801928296850567`
- `word_count`: `51`
- `body_word_count`: `37`
- `repeated_terms`: `{'board': 4}`

```text
This scene shows a sliding-block puzzle board with labeled rectangular blocks and four final-board options. Use the original board, perform these slides in order: 1. block E slides 2 cells right. Which option is the resulting board?
Answer format: set "answer" to only the selected option letter.
Example JSON:
{"answer":"B"}
```

### task_games__ultimate_tictactoe__line_completion_move_label / answer_and_annotation / sample 7056817449041372

- `query_id`: `o_winning_move_label`
- `instance_seed`: `7056817449041372`
- `word_count`: `96`
- `body_word_count`: `60`
- `repeated_terms`: `{'board': 3}`

```text
The image shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. Use only the highlighted small board. A winning move places the requested mark to make three in a row; a blocking move places a mark on the only cell that stops the opponent's immediate three-in-a-row threat. Which labeled empty cell lets O win the highlighted small board?
Final answer format: set "answer" to only the selected option letter.
Annotation format: set "annotation" to the [x0, y0, x1, y1] box of the selected empty-cell option.
Example JSON:
{"annotation":[410,240,470,300],"answer":"C"}
```

### task_games__ludo_board__move_result_option_label / answer_and_annotation / sample 2616582892462626

- `query_id`: `single`
- `instance_seed`: `2616582892462626`
- `word_count`: `95`
- `body_word_count`: `52`
- `repeated_terms`: `{'board': 3}`

```text
The scene shows a Ludo-style cross board with one visible token for each player color and twelve two-cell arrows showing the clockwise track direction. Use the dice sequence shown below the board and move clockwise along the track. After applying the shown sequence to the yellow token, which board letter is reached?
Annotation format: set "annotation" to an object with keys "moving_token" and "destination_cell", each mapped to a point as [x,y] in pixels.
Answer format: set "answer" to the selected shown destination label.
Example JSON:
{"annotation":{"moving_token":[115,215],"destination_cell":[342,282]},"answer":"D"}
```

### task_games__ultimate_tictactoe__line_completion_move_label / answer_and_annotation / sample 8402092056090952

- `query_id`: `x_winning_move_label`
- `instance_seed`: `8402092056090952`
- `word_count`: `95`
- `body_word_count`: `60`
- `repeated_terms`: `{'board': 3}`

```text
The scene shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. Use only the highlighted small board. A winning move places the requested mark to make three in a row; a blocking move places a mark on the only cell that stops the opponent's immediate three-in-a-row threat. Which labeled empty cell lets X win the highlighted small board?
Annotation format: set "annotation" to the [x0, y0, x1, y1] box of the selected empty-cell option.
Answer format: set "answer" to only the selected option letter.
Example JSON:
{"annotation":[410,240,470,300],"answer":"C"}
```

### task_games__tetris__drop_result_label / answer_and_annotation / sample 8513383769665272

- `query_id`: `single`
- `instance_seed`: `8513383769665272`
- `word_count`: `94`
- `body_word_count`: `60`
- `repeated_terms`: `{'board': 3}`

```text
The image shows a Tetris board with colored locked blocks and tetromino pieces. In the START board, the falling piece drops straight down from its shown position without moving sideways or rotating. After the piece locks, every completely filled row clears and all rows above fall down by the number of cleared rows. Which labeled board shows the final state?
Final answer format: set "answer" to only the selected option letter.
Annotation format: set "annotation" to the selected result-board bounding box [x0, y0, x1, y1].
Example JSON:
{"annotation":[520,180,760,520],"answer":"B"}
```

### task_games__tetris__drop_result_label / answer_only / sample 8513383769665272

- `query_id`: `single`
- `instance_seed`: `8513383769665272`
- `word_count`: `75`
- `body_word_count`: `60`
- `repeated_terms`: `{'board': 3}`

```text
The image shows a Tetris board with colored locked blocks and tetromino pieces. In the START board, the falling piece drops straight down from its shown position without moving sideways or rotating. After the piece locks, every completely filled row clears and all rows above fall down by the number of cleared rows. Which labeled board shows the final state?
Final answer format: set "answer" to only the selected option letter.
Example JSON:
{"answer":"B"}
```

### task_games__ultimate_tictactoe__line_completion_move_label / answer_only / sample 7056817449041372

- `query_id`: `o_winning_move_label`
- `instance_seed`: `7056817449041372`
- `word_count`: `75`
- `body_word_count`: `60`
- `repeated_terms`: `{'board': 3}`

```text
The image shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. Use only the highlighted small board. A winning move places the requested mark to make three in a row; a blocking move places a mark on the only cell that stops the opponent's immediate three-in-a-row threat. Which labeled empty cell lets O win the highlighted small board?
Final answer format: set "answer" to only the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_games__ultimate_tictactoe__line_completion_move_label / answer_only / sample 8402092056090952

- `query_id`: `x_winning_move_label`
- `instance_seed`: `8402092056090952`
- `word_count`: `74`
- `body_word_count`: `60`
- `repeated_terms`: `{'board': 3}`

```text
The scene shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. Use only the highlighted small board. A winning move places the requested mark to make three in a row; a blocking move places a mark on the only cell that stops the opponent's immediate three-in-a-row threat. Which labeled empty cell lets X win the highlighted small board?
Answer format: set "answer" to only the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_games__ludo_board__move_result_option_label / answer_only / sample 2616582892462626

- `query_id`: `single`
- `instance_seed`: `2616582892462626`
- `word_count`: `67`
- `body_word_count`: `52`
- `repeated_terms`: `{'board': 3}`

```text
The scene shows a Ludo-style cross board with one visible token for each player color and twelve two-cell arrows showing the clockwise track direction. Use the dice sequence shown below the board and move clockwise along the track. After applying the shown sequence to the yellow token, which board letter is reached?
Required answer format: set "answer" to the selected shown destination label.
Example JSON:
{"answer":"D"}
```

## All Prompt Samples

### task_games__2048__max_tile_value / single / answer_and_annotation / sample 3670062844506536

- `instance_seed`: `3670062844506536`
- `word_count`: `98`
- `body_word_count`: `43`

```text
The figure shows a 4 x 4 2048 board with numbered tiles and move arrows. In 2048, a move slides all tiles toward the arrow; equal adjacent tiles in that direction merge once. Which tile value is the maximum after the one-arrow move?
Required annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] around the original tile cell or cells that form the largest tile after the shown move.
Required answer format: set "answer" to the largest tile value after the shown move.
Example JSON:
{"annotation":[[224,224,344,344],[358,224,478,344]],"answer":128}
```

### task_games__2048__max_tile_value / single / answer_only / sample 3670062844506536

- `instance_seed`: `3670062844506536`
- `word_count`: `61`
- `body_word_count`: `43`

```text
The figure shows a 4 x 4 2048 board with numbered tiles and move arrows. In 2048, a move slides all tiles toward the arrow; equal adjacent tiles in that direction merge once. Which tile value is the maximum after the one-arrow move?
Required answer format: set "answer" to the largest tile value after the shown move.
Example JSON:
{"answer":128}
```

### task_games__2048__merge_count / single / answer_and_annotation / sample 3198046276517893

- `instance_seed`: `3198046276517893`
- `word_count`: `125`
- `body_word_count`: `47`

```text
The image shows a 4 x 4 2048 board with numbered tiles and move arrows. In 2048, a move slides all tiles toward the arrow; equal adjacent tiles in that direction merge once. If the board is moved in the arrow direction, how many merge events happen?
Annotation format: set "annotation" to a list of merge segments. Each segment uses two pixel-point endpoints [x, y] in [[x0, y0], [x1, y1]] form, connecting the centers of the two source tile cells before the move that combine into one tile after the move; use [] when the merge count is 0.
Answer format: set "answer" to the number of merges made by the shown move.
Example JSON:
{"annotation":[[[284,284],[418,284]],[[284,418],[418,418]]],"answer":2}
```

### task_games__2048__merge_count / single / answer_only / sample 3198046276517893

- `instance_seed`: `3198046276517893`
- `word_count`: `68`
- `body_word_count`: `47`

```text
The image shows a 4 x 4 2048 board with numbered tiles and move arrows. In 2048, a move slides all tiles toward the arrow; equal adjacent tiles in that direction merge once. If the board is moved in the arrow direction, how many merge events happen?
Format for the "answer" field: set "answer" to the number of merges made by the shown move.
Example JSON:
{"answer":2}
```

### task_games__2048__move_result_board_label / single / answer_and_annotation / sample 5348524522518325

- `instance_seed`: `5348524522518325`
- `word_count`: `106`
- `body_word_count`: `58`

```text
The visual shows a 4 x 4 2048 board with numbered tiles and move arrows. In 2048, a move slides all tiles toward the arrow; equal adjacent tiles in that direction merge once. Labeled candidate boards are shown below. Use only the slide-and-merge result before any new tile is added. Report the option letter for the post-move board.
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected candidate result board.
Answer format: set "answer" to the single option letter of the candidate board that matches the result after the shown move.
Example JSON:
{"annotation":[356,542,508,694],"answer":"C"}
```

### task_games__2048__move_result_board_label / single / answer_only / sample 5348524522518325

- `instance_seed`: `5348524522518325`
- `word_count`: `83`
- `body_word_count`: `58`

```text
The visual shows a 4 x 4 2048 board with numbered tiles and move arrows. In 2048, a move slides all tiles toward the arrow; equal adjacent tiles in that direction merge once. Labeled candidate boards are shown below. Use only the slide-and-merge result before any new tile is added. Report the option letter for the post-move board.
Answer format: set "answer" to the single option letter of the candidate board that matches the result after the shown move.
Example JSON:
{"answer":"C"}
```

### task_games__backgammon__destination_count / blocked_destination_count / answer_and_annotation / sample 3689716281841559

- `instance_seed`: `3689716281841559`
- `word_count`: `148`
- `body_word_count`: `94`

```text
This scene shows a numbered backgammon board with black and white checker stacks and two dice. The board header shows which player moves and whether that player moves 24 to 1 or 1 to 24. For each occupied active-player point, use either shown die in that direction to get a candidate destination number. Count each distinct destination number once, even if more than one checker or die reaches it. A destination point with two or more opposing checkers is blocked. Considering the active player's possible single-die destinations, how many distinct destination points are blocked?
Final answer format: set "answer" to the number of distinct blocked destination points.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] around the distinct possible destination points blocked by two or more opposing checkers.
Example JSON:
{"annotation":[[276,400,341,612],[342,400,407,612],[608,400,673,612]],"answer":3}
```

### task_games__backgammon__destination_count / blocked_destination_count / answer_only / sample 3689716281841559

- `instance_seed`: `3689716281841559`
- `word_count`: `113`
- `body_word_count`: `94`

```text
This scene shows a numbered backgammon board with black and white checker stacks and two dice. The board header shows which player moves and whether that player moves 24 to 1 or 1 to 24. For each occupied active-player point, use either shown die in that direction to get a candidate destination number. Count each distinct destination number once, even if more than one checker or die reaches it. A destination point with two or more opposing checkers is blocked. Considering the active player's possible single-die destinations, how many distinct destination points are blocked?
Format for the "answer" field: set "answer" to the number of distinct blocked destination points.
Example JSON:
{"answer":3}
```

### task_games__backgammon__destination_count / hit_move_count / answer_and_annotation / sample 5950614440045382

- `instance_seed`: `5950614440045382`
- `word_count`: `143`
- `body_word_count`: `92`

```text
This scene shows a numbered backgammon board with black and white checker stacks and two dice. The board header shows which player moves and whether that player moves 24 to 1 or 1 to 24. For each occupied active-player point, use either shown die in that direction to get a candidate destination number. Count each distinct destination number once, even if more than one checker or die reaches it. A destination point with two or more opposing checkers is blocked. How many distinct single-die destinations are hit moves for the active player?
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] around the distinct destination points where the active player would hit exactly one opposing checker.
Answer format: set "answer" to the number of distinct hit destination points.
Example JSON:
{"annotation":[[410,104,475,316],[608,104,673,316]],"answer":2}
```

### task_games__backgammon__destination_count / hit_move_count / answer_only / sample 5950614440045382

- `instance_seed`: `5950614440045382`
- `word_count`: `108`
- `body_word_count`: `92`

```text
This scene shows a numbered backgammon board with black and white checker stacks and two dice. The board header shows which player moves and whether that player moves 24 to 1 or 1 to 24. For each occupied active-player point, use either shown die in that direction to get a candidate destination number. Count each distinct destination number once, even if more than one checker or die reaches it. A destination point with two or more opposing checkers is blocked. How many distinct single-die destinations are hit moves for the active player?
Answer format: set "answer" to the number of distinct hit destination points.
Example JSON:
{"answer":2}
```

### task_games__backgammon__destination_count / legal_move_count / answer_and_annotation / sample 5640797118990632

- `instance_seed`: `5640797118990632`
- `word_count`: `144`
- `body_word_count`: `92`

```text
The visual shows a numbered backgammon board with black and white checker stacks and two dice. The board header shows which player moves and whether that player moves 24 to 1 or 1 to 24. For each occupied active-player point, use either shown die in that direction to get a candidate destination number. Count each distinct destination number once, even if more than one checker or die reaches it. A destination point with two or more opposing checkers is blocked. How many distinct destination points can the active player legally move to?
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] around the distinct destination points where the active player can legally move.
Answer format: set "answer" to the number of distinct legal destination points.
Example JSON:
{"annotation":[[144,104,209,316],[210,104,275,316],[608,104,673,316]],"answer":3}
```

### task_games__backgammon__destination_count / legal_move_count / answer_only / sample 5640797118990632

- `instance_seed`: `5640797118990632`
- `word_count`: `108`
- `body_word_count`: `104`

```text
The visual shows a numbered backgammon board with black and white checker stacks and two dice. The board header shows which player moves and whether that player moves 24 to 1 or 1 to 24. For each occupied active-player point, use either shown die in that direction to get a candidate destination number. Count each distinct destination number once, even if more than one checker or die reaches it. A destination point with two or more opposing checkers is blocked. How many distinct destination points can the active player legally move to?
Answer field: set "answer" to the number of distinct legal destination points.
Example JSON:
{"answer":3}
```

### task_games__backgammon__point_state_count / single / answer_and_annotation / sample 7232889366149495

- `instance_seed`: `7232889366149495`
- `word_count`: `82`
- `body_word_count`: `29`

```text
This scene shows a numbered backgammon board with black and white checker stacks and two dice. What is the number of points that have two or more white checkers?
Final answer format: set "answer" to the number of numbered points matching the requested checker-stack condition.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] around the numbered points matching the requested checker-stack condition.
Example JSON:
{"annotation":[[144,104,209,316],[342,104,407,316],[608,400,673,612]],"answer":3}
```

### task_games__backgammon__point_state_count / single / answer_only / sample 7232889366149495

- `instance_seed`: `7232889366149495`
- `word_count`: `48`
- `body_word_count`: `29`

```text
This scene shows a numbered backgammon board with black and white checker stacks and two dice. What is the number of points that have two or more white checkers?
Answer format: set "answer" to the number of numbered points matching the requested checker-stack condition.
Example JSON:
{"answer":3}
```

### task_games__battleship__last_ship_cell_label / single / answer_and_annotation / sample 8326966582146529

- `instance_seed`: `8326966582146529`
- `word_count`: `126`
- `body_word_count`: `85`

```text
The scene shows a Battleship tracking grid with red hit markers, gray miss markers, optional candidate labels, and a fleet-shape panel for Line 5, Line 4, Line 3, Square 2x2, and L 3 beside the grid. Each fleet ship is placed exactly once on the board. A ship is sunk only when every cell of that ship has a red hit marker. Use the fleet shapes and the hit/miss markers to find the only unhit cell of the not-yet-sunk ship. Which label marks it?
Required annotation format: set "annotation" to one pixel-space point [x, y] at the center of the selected labeled cell.
Required answer format: set "answer" to the single selected option label shown on the board.
Example JSON:
{"annotation":[315,405],"answer":"D"}
```

### task_games__battleship__last_ship_cell_label / single / answer_only / sample 8326966582146529

- `instance_seed`: `8326966582146529`
- `word_count`: `103`
- `body_word_count`: `85`

```text
The scene shows a Battleship tracking grid with red hit markers, gray miss markers, optional candidate labels, and a fleet-shape panel for Line 5, Line 4, Line 3, Square 2x2, and L 3 beside the grid. Each fleet ship is placed exactly once on the board. A ship is sunk only when every cell of that ship has a red hit marker. Use the fleet shapes and the hit/miss markers to find the only unhit cell of the not-yet-sunk ship. Which label marks it?
Answer format: set "answer" to the single selected option label shown on the board.
Example JSON:
{"answer":"D"}
```

### task_games__battleship__ship_cell_status_count / named_ship_hit_cell_count / answer_and_annotation / sample 630050909704750

- `instance_seed`: `630050909704750`
- `word_count`: `144`
- `body_word_count`: `72`

```text
The scene shows a Battleship tracking grid with red hit markers, gray miss markers, optional candidate labels, and a fleet-shape panel for Line 5, Line 4, Line 3, Square 2x2, and L 3 beside the grid. Each fleet ship is placed exactly once on the board. A ship is sunk only when every cell of that ship has a red hit marker. Determine the number of red hit markers on Line 4.
Annotation format: set "annotation" to a JSON array of pixel-space cell boxes [x0, y0, x1, y1] for the red hit-marker cells on the named ship; use an empty array if none of that ship's cells are hit.
Answer format: set "answer" to the number of cells on the named ship that have red hit markers.
Example JSON:
{"annotation":[[195,205,225,235],[225,205,255,235],[255,205,285,235]],"answer":3}
```

### task_games__battleship__ship_cell_status_count / named_ship_hit_cell_count / answer_only / sample 630050909704750

- `instance_seed`: `630050909704750`
- `word_count`: `95`
- `body_word_count`: `72`

```text
The scene shows a Battleship tracking grid with red hit markers, gray miss markers, optional candidate labels, and a fleet-shape panel for Line 5, Line 4, Line 3, Square 2x2, and L 3 beside the grid. Each fleet ship is placed exactly once on the board. A ship is sunk only when every cell of that ship has a red hit marker. Determine the number of red hit markers on Line 4.
Final answer format: set "answer" to the number of cells on the named ship that have red hit markers.
Example JSON:
{"answer":3}
```

### task_games__battleship__ship_cell_status_count / named_ship_unhit_cell_count / answer_and_annotation / sample 8942211811482471

- `instance_seed`: `8942211811482471`
- `word_count`: `141`
- `body_word_count`: `74`

```text
The visual shows a Battleship tracking grid with red hit markers, gray miss markers, optional candidate labels, and a fleet-shape panel for Line 5, Line 4, Line 3, Square 2x2, and L 3 beside the grid. Each fleet ship is placed exactly once on the board. A ship is sunk only when every cell of that ship has a red hit marker. Determine the number of cells without red hit markers on Line 3.
Annotation format: set "annotation" to a JSON array of pixel-space cell boxes [x0, y0, x1, y1] for the named ship's intact cells; use an empty array if every cell of that ship is hit.
Answer format: set "answer" to the number of cells on the named ship that do not have red hit markers.
Example JSON:
{"annotation":[[285,205,315,235],[315,205,345,235]],"answer":2}
```

### task_games__battleship__ship_cell_status_count / named_ship_unhit_cell_count / answer_only / sample 8942211811482471

- `instance_seed`: `8942211811482471`
- `word_count`: `99`
- `body_word_count`: `74`

```text
The visual shows a Battleship tracking grid with red hit markers, gray miss markers, optional candidate labels, and a fleet-shape panel for Line 5, Line 4, Line 3, Square 2x2, and L 3 beside the grid. Each fleet ship is placed exactly once on the board. A ship is sunk only when every cell of that ship has a red hit marker. Determine the number of cells without red hit markers on Line 3.
Required answer format: set "answer" to the number of cells on the named ship that do not have red hit markers.
Example JSON:
{"answer":2}
```

### task_games__battleship__ship_status_count / partial_ship_count / answer_and_annotation / sample 6216507372498437

- `instance_seed`: `6216507372498437`
- `word_count`: `162`
- `body_word_count`: `75`

```text
The visual shows a Battleship tracking grid with red hit markers, gray miss markers, optional candidate labels, and a fleet-shape panel for Line 5, Line 4, Line 3, Square 2x2, and L 3 beside the grid. Each fleet ship is placed exactly once on the board. A ship is sunk only when every cell of that ship has a red hit marker. Determine the number of ships that have some, but not all, cells hit.
Annotation format: set "annotation" to a JSON object mapping each partially hit ship's displayed fleet-shape name to a list of pixel-space cell boxes [x0, y0, x1, y1] for every red hit-marker cell on that ship; use an empty object if no ship is partially hit.
Answer format: set "answer" to the number of ships that have at least one red hit marker but are not sunk.
Example JSON:
{"annotation":{"Line 4":[[195,265,225,295],[225,265,255,295]],"L 3":[[195,475,225,505]]},"answer":2}
```

### task_games__battleship__ship_status_count / partial_ship_count / answer_only / sample 6216507372498437

- `instance_seed`: `6216507372498437`
- `word_count`: `100`
- `body_word_count`: `96`

```text
The visual shows a Battleship tracking grid with red hit markers, gray miss markers, optional candidate labels, and a fleet-shape panel for Line 5, Line 4, Line 3, Square 2x2, and L 3 beside the grid. Each fleet ship is placed exactly once on the board. A ship is sunk only when every cell of that ship has a red hit marker. Determine the number of ships that have some, but not all, cells hit.
Answer field: set "answer" to the number of ships that have at least one red hit marker but are not sunk.
Example JSON:
{"answer":2}
```

### task_games__battleship__ship_status_count / sunk_ship_count / answer_and_annotation / sample 7372897504446350

- `instance_seed`: `7372897504446350`
- `word_count`: `152`
- `body_word_count`: `71`

```text
The visual shows a Battleship tracking grid with red hit markers, gray miss markers, optional candidate labels, and a fleet-shape panel for Line 5, Line 4, Line 3, Square 2x2, and L 3 beside the grid. Each fleet ship is placed exactly once on the board. A ship is sunk only when every cell of that ship has a red hit marker. Determine the number of sunk ships on the board.
Annotation format: set "annotation" to a JSON object mapping each sunk ship's displayed fleet-shape name to a list of pixel-space cell boxes [x0, y0, x1, y1] for every red hit-marker cell on that ship; use an empty object if no ship is sunk.
Answer format: set "answer" to the number of ships whose every cell has a red hit marker.
Example JSON:
{"annotation":{"Line 5":[[195,205,225,235],[225,205,255,235]],"Line 3":[[195,325,225,355]]},"answer":2}
```

### task_games__battleship__ship_status_count / sunk_ship_count / answer_only / sample 7372897504446350

- `instance_seed`: `7372897504446350`
- `word_count`: `93`
- `body_word_count`: `71`

```text
The visual shows a Battleship tracking grid with red hit markers, gray miss markers, optional candidate labels, and a fleet-shape panel for Line 5, Line 4, Line 3, Square 2x2, and L 3 beside the grid. Each fleet ship is placed exactly once on the board. A ship is sunk only when every cell of that ship has a red hit marker. Determine the number of sunk ships on the board.
Final answer format: set "answer" to the number of ships whose every cell has a red hit marker.
Example JSON:
{"answer":2}
```

### task_games__bingo__called_number_match_count / single / answer_and_annotation / sample 3998767610955361

- `instance_seed`: `3998767610955361`
- `word_count`: `81`
- `body_word_count`: `26`

```text
The bingo card shows one face-up 5 x 5 bingo card. Using the CALLED list, count how many listed numbers are printed on the bingo card.
Annotation format: set "annotation" to an array of pixel-space cell boxes [x0, y0, x1, y1] for the card cells whose printed numbers are in the CALLED list.
Answer format: set "answer" to the number of CALLED-list numbers that appear on the card.
Example JSON:
{"annotation":[[100,80,150,130],[220,240,270,290]],"answer":2}
```

### task_games__bingo__called_number_match_count / single / answer_only / sample 3998767610955361

- `instance_seed`: `3998767610955361`
- `word_count`: `48`
- `body_word_count`: `26`

```text
The bingo card shows one face-up 5 x 5 bingo card. Using the CALLED list, count how many listed numbers are printed on the bingo card.
Format for the "answer" field: set "answer" to the number of CALLED-list numbers that appear on the card.
Example JSON:
{"answer":2}
```

### task_games__bingo__completed_column_label / single / answer_and_annotation / sample 4023242799677861

- `instance_seed`: `4023242799677861`
- `word_count`: `73`
- `body_word_count`: `16`

```text
The image shows one face-up 5 x 5 bingo card. Which BINGO column is fully marked?
Annotation format: set "annotation" to one segment using two pixel-point endpoints [x, y] in [[x0, y0], [x1, y1]] form, at the centers of the top and bottom cells in the completed column.
Answer format: set "answer" to the completed column label as B, I, N, G, or O.
Example JSON:
{"annotation":[[180,90],[180,330]],"answer":"I"}
```

### task_games__bingo__completed_column_label / single / answer_only / sample 4023242799677861

- `instance_seed`: `4023242799677861`
- `word_count`: `37`
- `body_word_count`: `16`

```text
The image shows one face-up 5 x 5 bingo card. Which BINGO column is fully marked?
Required answer format: set "answer" to the completed column label as B, I, N, G, or O.
Example JSON:
{"answer":"I"}
```

### task_games__bingo__completed_line_sum_value / single / answer_and_annotation / sample 5125465189877803

- `instance_seed`: `5125465189877803`
- `word_count`: `81`
- `body_word_count`: `21`

```text
The image shows one face-up 5 x 5 bingo card. Using the completed column, what total do its five numbers make?
Annotation format: set "annotation" to an array of points [x, y], one at the center of each of the five cells in the completed row or column.
Answer format: set "answer" to the sum of the five printed numbers in the completed row or column.
Example JSON:
{"annotation":[[65,105],[125,105],[185,105],[245,105],[305,105]],"answer":184}
```

### task_games__bingo__completed_line_sum_value / single / answer_only / sample 5125465189877803

- `instance_seed`: `5125465189877803`
- `word_count`: `43`
- `body_word_count`: `39`

```text
The image shows one face-up 5 x 5 bingo card. Using the completed column, what total do its five numbers make?
Answer field: set "answer" to the sum of the five printed numbers in the completed row or column.
Example JSON:
{"answer":184}
```

### task_games__bingo__near_complete_line_count / near_complete_column_count / answer_and_annotation / sample 4775073093396308

- `instance_seed`: `4775073093396308`
- `word_count`: `79`
- `body_word_count`: `32`

```text
The visual shows one face-up 5 x 5 bingo card. Count the columns that are exactly one mark away from complete. A near-complete column is a column with exactly one unmarked cell.
Annotation format: set "annotation" to an array of bounding boxes [x0, y0, x1, y1] for the single unmarked gap cell in each near-complete column.
Answer format: set "answer" to the number of near-complete columns.
Example JSON:
{"annotation":[[160,160,210,210],[280,240,330,290]],"answer":2}
```

### task_games__bingo__near_complete_line_count / near_complete_column_count / answer_only / sample 4775073093396308

- `instance_seed`: `4775073093396308`
- `word_count`: `47`
- `body_word_count`: `32`

```text
The visual shows one face-up 5 x 5 bingo card. Count the columns that are exactly one mark away from complete. A near-complete column is a column with exactly one unmarked cell.
Required answer format: set "answer" to the number of near-complete columns.
Example JSON:
{"answer":2}
```

### task_games__bingo__near_complete_line_count / near_complete_row_count / answer_and_annotation / sample 1686846686692217

- `instance_seed`: `1686846686692217`
- `word_count`: `80`
- `body_word_count`: `32`

```text
The figure shows one face-up 5 x 5 bingo card. Count the rows that are exactly one mark away from complete. A near-complete row is a row with exactly one unmarked cell.
Final answer format: set "answer" to the number of near-complete rows.
Annotation format: set "annotation" to an array of bounding boxes [x0, y0, x1, y1] for the single unmarked gap cell in each near-complete row.
Example JSON:
{"annotation":[[220,80,270,130],[100,240,150,290]],"answer":2}
```

### task_games__bingo__near_complete_line_count / near_complete_row_count / answer_only / sample 1686846686692217

- `instance_seed`: `1686846686692217`
- `word_count`: `49`
- `body_word_count`: `32`

```text
The figure shows one face-up 5 x 5 bingo card. Count the rows that are exactly one mark away from complete. A near-complete row is a row with exactly one unmarked cell.
Format for the "answer" field: set "answer" to the number of near-complete rows.
Example JSON:
{"answer":2}
```

### task_games__bowling__first_pin_hit_label / single / answer_and_annotation / sample 6730952105596430

- `instance_seed`: `6730952105596430`
- `word_count`: `71`
- `body_word_count`: `31`

```text
The figure shows a bowling lane with a ball, labeled pins, and any shown aiming paths. The dashed arrow shows the ball's current straight path. Which labeled pin is hit first?
Annotation format: set "annotation" to one point [x, y] at the center of the first pin hit by the shown path.
Answer format: set "answer" to the selected pin label as a string.
Example JSON:
{"annotation":[532,194],"answer":"G"}
```

### task_games__bowling__first_pin_hit_label / single / answer_only / sample 6730952105596430

- `instance_seed`: `6730952105596430`
- `word_count`: `50`
- `body_word_count`: `31`

```text
The figure shows a bowling lane with a ball, labeled pins, and any shown aiming paths. The dashed arrow shows the ball's current straight path. Which labeled pin is hit first?
Format for the "answer" field: set "answer" to the selected pin label as a string.
Example JSON:
{"answer":"G"}
```

### task_games__bowling__spare_path_label / single / answer_and_annotation / sample 7572708746975645

- `instance_seed`: `7572708746975645`
- `word_count`: `102`
- `body_word_count`: `51`

```text
The scene shows a bowling lane with a ball, labeled pins, and any shown aiming paths. Compare the numbered dashed paths. Extend each numbered dashed path straight toward the pins; the correct spare path is the extended line that passes through every remaining standing pin. Which path number should be selected?
Final answer format: set "answer" to the selected numbered path label as a string.
Annotation format: set "annotation" to one segment using two pixel-point endpoints [x, y] in [[x0, y0], [x1, y1]] form, matching the endpoints of the selected visible dashed cue.
Example JSON:
{"annotation":[[430,610],[620,250]],"answer":"4"}
```

### task_games__bowling__spare_path_label / single / answer_only / sample 7572708746975645

- `instance_seed`: `7572708746975645`
- `word_count`: `69`
- `body_word_count`: `51`

```text
The scene shows a bowling lane with a ball, labeled pins, and any shown aiming paths. Compare the numbered dashed paths. Extend each numbered dashed path straight toward the pins; the correct spare path is the extended line that passes through every remaining standing pin. Which path number should be selected?
Required answer format: set "answer" to the selected numbered path label as a string.
Example JSON:
{"answer":"4"}
```

### task_games__brick_breaker__hit_row_remaining_count / single / answer_and_annotation / sample 6564635917168759

- `instance_seed`: `6564635917168759`
- `word_count`: `120`
- `body_word_count`: `49`

```text
The visual shows a brick-breaker playfield with labeled bricks at the top, a short ball-direction cue, and labeled catch lanes at the bottom. The short dashed arrow shows the ball's current straight direction. After removing the brick hit by that line, how many bricks remain in that brick's row?
Required annotation format: set "annotation" to an array of pixel-space brick boxes [x0, y0, x1, y1] for the bricks left in the same row after the hit brick is removed.
Required answer format: set "answer" to the number of bricks left in that row after the hit brick is removed.
Example JSON:
{"annotation":[[135,258,205,298],[245,258,315,298],[355,258,425,298],[465,258,535,298]],"answer":4}
```

### task_games__brick_breaker__hit_row_remaining_count / single / answer_only / sample 6564635917168759

- `instance_seed`: `6564635917168759`
- `word_count`: `73`
- `body_word_count`: `49`

```text
The visual shows a brick-breaker playfield with labeled bricks at the top, a short ball-direction cue, and labeled catch lanes at the bottom. The short dashed arrow shows the ball's current straight direction. After removing the brick hit by that line, how many bricks remain in that brick's row?
Required answer format: set "answer" to the number of bricks left in that row after the hit brick is removed.
Example JSON:
{"answer":4}
```

### task_games__brick_breaker__next_hit_label / single / answer_and_annotation / sample 8146354322545373

- `instance_seed`: `8146354322545373`
- `word_count`: `86`
- `body_word_count`: `44`

```text
The scene shows a brick-breaker playfield with labeled bricks at the top, a short ball-direction cue, and labeled catch lanes at the bottom. The short dashed arrow shows the ball's current straight direction. What is the label of the first brick on that line?
Annotation format: set "annotation" to one pixel-space point [x, y] at the center of the brick hit first after extrapolating the ball direction.
Answer format: set "answer" to the selected brick label as a string.
Example JSON:
{"annotation":[476,207],"answer":"H"}
```

### task_games__brick_breaker__next_hit_label / single / answer_only / sample 8146354322545373

- `instance_seed`: `8146354322545373`
- `word_count`: `61`
- `body_word_count`: `44`

```text
The scene shows a brick-breaker playfield with labeled bricks at the top, a short ball-direction cue, and labeled catch lanes at the bottom. The short dashed arrow shows the ball's current straight direction. What is the label of the first brick on that line?
Required answer format: set "answer" to the selected brick label as a string.
Example JSON:
{"answer":"H"}
```

### task_games__brick_breaker__paddle_catch_label / single / answer_and_annotation / sample 7260641070446242

- `instance_seed`: `7260641070446242`
- `word_count`: `82`
- `body_word_count`: `42`

```text
This scene shows a brick-breaker playfield with labeled bricks at the top, a short ball-direction cue, and labeled catch lanes at the bottom. The short dashed arrow shows the ball's current straight direction. Which labeled bottom lane should the paddle be in?
Annotation format: set "annotation" to one pixel-space point [x, y] at the center of the selected bottom catch lane pad.
Answer format: set "answer" to the selected bottom lane label as a string.
Example JSON:
{"annotation":[295,403],"answer":"C"}
```

### task_games__brick_breaker__paddle_catch_label / single / answer_only / sample 7260641070446242

- `instance_seed`: `7260641070446242`
- `word_count`: `60`
- `body_word_count`: `42`

```text
This scene shows a brick-breaker playfield with labeled bricks at the top, a short ball-direction cue, and labeled catch lanes at the bottom. The short dashed arrow shows the ball's current straight direction. Which labeled bottom lane should the paddle be in?
Required answer format: set "answer" to the selected bottom lane label as a string.
Example JSON:
{"answer":"C"}
```

### task_games__bubble_shooter__drop_count / single / answer_and_annotation / sample 6763308201588

- `instance_seed`: `6763308201588`
- `word_count`: `118`
- `body_word_count`: `60`

```text
This scene shows a close-packed bubble-shooter board with colored bubbles, a marked landing target, and a visible launcher area. A shot bubble attaches at the marked target. Same-color connected bubbles pop when the placed bubble makes that group size at least three; then bubbles no longer connected to the top drop. How many bubbles drop after resolving the shown shot?
Final answer format: set "answer" to the number of bubbles that drop after the shot is resolved.
Annotation format: set "annotation" to an array of pixel-space bubble boxes [x0, y0, x1, y1] for the bubbles that drop.
Example JSON:
{"annotation":[[462,352,504,394],[508,352,550,394],[485,392,527,434],[531,392,573,434]],"answer":4}
```

### task_games__bubble_shooter__drop_count / single / answer_only / sample 6763308201588

- `instance_seed`: `6763308201588`
- `word_count`: `81`
- `body_word_count`: `60`

```text
This scene shows a close-packed bubble-shooter board with colored bubbles, a marked landing target, and a visible launcher area. A shot bubble attaches at the marked target. Same-color connected bubbles pop when the placed bubble makes that group size at least three; then bubbles no longer connected to the top drop. How many bubbles drop after resolving the shown shot?
Required answer format: set "answer" to the number of bubbles that drop after the shot is resolved.
Example JSON:
{"answer":4}
```

### task_games__bubble_shooter__pop_color_label / single / answer_and_annotation / sample 4119748115532496

- `instance_seed`: `4119748115532496`
- `word_count`: `115`
- `body_word_count`: `60`

```text
The scene shows a close-packed bubble-shooter board with colored bubbles, a marked landing target, and a visible launcher area. A shot bubble attaches at the marked target. A same-color connected group pops when the placed bubble makes that group size at least three. If one option color is shot to the marked target, which option label would cause a pop?
Annotation format: set "annotation" to an array of pixel-space bubble boxes [x0, y0, x1, y1] for the existing board bubbles that would pop for the selected option.
Answer format: set "answer" to the single option label whose color would make bubbles pop.
Example JSON:
{"annotation":[[382,258,424,300],[428,258,470,300]],"answer":"C"}
```

### task_games__bubble_shooter__pop_color_label / single / answer_only / sample 4119748115532496

- `instance_seed`: `4119748115532496`
- `word_count`: `82`
- `body_word_count`: `60`

```text
The scene shows a close-packed bubble-shooter board with colored bubbles, a marked landing target, and a visible launcher area. A shot bubble attaches at the marked target. A same-color connected group pops when the placed bubble makes that group size at least three. If one option color is shot to the marked target, which option label would cause a pop?
Format for the "answer" field: set "answer" to the single option label whose color would make bubbles pop.
Example JSON:
{"answer":"C"}
```

### task_games__bubble_shooter__pop_count / single / answer_and_annotation / sample 4758267788619280

- `instance_seed`: `4758267788619280`
- `word_count`: `117`
- `body_word_count`: `65`

```text
The image shows a close-packed bubble-shooter board with colored bubbles, a marked landing target, and a visible launcher area. A shot bubble attaches at the marked target. A same-color connected group pops when the placed bubble makes that group size at least three. Do not count the shot bubble or the marked target itself. How many existing board bubbles pop after the shown same-color shot?
Annotation format: set "annotation" to an array of pixel-space bubble boxes [x0, y0, x1, y1] for the existing board bubbles that pop.
Answer format: set "answer" to the number of existing board bubbles that pop.
Example JSON:
{"annotation":[[352,216,394,258],[398,216,440,258],[375,256,417,298]],"answer":3}
```

### task_games__bubble_shooter__pop_count / single / answer_only / sample 4758267788619280

- `instance_seed`: `4758267788619280`
- `word_count`: `83`
- `body_word_count`: `65`

```text
The image shows a close-packed bubble-shooter board with colored bubbles, a marked landing target, and a visible launcher area. A shot bubble attaches at the marked target. A same-color connected group pops when the placed bubble makes that group size at least three. Do not count the shot bubble or the marked target itself. How many existing board bubbles pop after the shown same-color shot?
Required answer format: set "answer" to the number of existing board bubbles that pop.
Example JSON:
{"answer":5}
```

### task_games__cards__blackjack_best_hand_label / single / answer_and_annotation / sample 3176277245957885

- `instance_seed`: `3176277245957885`
- `word_count`: `133`
- `body_word_count`: `80`

```text
The scene shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Use blackjack values: number cards count as printed and J/Q/K count as 10. Count each Ace as 11, but reduce Aces to 1 as needed to keep the hand at 21 or below. If a hand is still over 21 after Ace reductions, it is bust and worse than any non-bust hand. Select the option letter for the best labeled blackjack hand.
Required annotation format: set "annotation" to an array of bounding boxes [x0, y0, x1, y1] for every card in the winning blackjack hand.
Required answer format: set "answer" to only the winning blackjack hand option letter.
Example JSON:
{"annotation":[[120,80,200,190],[220,80,300,190],[320,80,400,190]],"answer":"B"}
```

### task_games__cards__blackjack_best_hand_label / single / answer_only / sample 3176277245957885

- `instance_seed`: `3176277245957885`
- `word_count`: `97`
- `body_word_count`: `80`

```text
The scene shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Use blackjack values: number cards count as printed and J/Q/K count as 10. Count each Ace as 11, but reduce Aces to 1 as needed to keep the hand at 21 or below. If a hand is still over 21 after Ace reductions, it is bust and worse than any non-bust hand. Select the option letter for the best labeled blackjack hand.
Final answer format: set "answer" to only the winning blackjack hand option letter.
Example JSON:
{"answer":"B"}
```

### task_games__cards__exact_triple_count / single / answer_and_annotation / sample 1392126847659813

- `instance_seed`: `1392126847659813`
- `word_count`: `96`
- `body_word_count`: `30`

```text
The scene shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Looking only at rank matches, how many exact triples are present in this hand?
Annotation format: set "annotation" to an object mapping each rank label that appears exactly three times to an array of three card bounding boxes [x0, y0, x1, y1] for that rank.
Answer format: set "answer" to the number of ranks that appear exactly three times in the hand.
Example JSON:
{"annotation":{"7":[[120,80,200,190],[220,80,300,190],[320,80,400,190]]},"answer":1}
```

### task_games__cards__exact_triple_count / single / answer_only / sample 1392126847659813

- `instance_seed`: `1392126847659813`
- `word_count`: `52`
- `body_word_count`: `30`

```text
The scene shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Looking only at rank matches, how many exact triples are present in this hand?
Final answer format: set "answer" to the number of ranks that appear exactly three times in the hand.
Example JSON:
{"answer":1}
```

### task_games__cards__higher_than_reference_count / single / answer_and_annotation / sample 702355942240405

- `instance_seed`: `702355942240405`
- `word_count`: `103`
- `body_word_count`: `50`

```text
The figure shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Use rank order 2 < 3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A, with Ace high only. What is the number of non-reference cards with rank greater than the `REF` card?
Annotation format: set "annotation" to an array of bounding boxes [x0, y0, x1, y1] for every non-reference card ranked higher than the reference card.
Answer format: set "answer" to the number of non-reference cards ranked higher than the reference card.
Example JSON:
{"annotation":[[120,80,200,190],[220,80,300,190]],"answer":2}
```

### task_games__cards__higher_than_reference_count / single / answer_only / sample 702355942240405

- `instance_seed`: `702355942240405`
- `word_count`: `70`
- `body_word_count`: `66`

```text
The figure shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Use rank order 2 < 3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A, with Ace high only. What is the number of non-reference cards with rank greater than the `REF` card?
Answer field: set "answer" to the number of non-reference cards ranked higher than the reference card.
Example JSON:
{"answer":2}
```

### task_games__cards__longest_run_length / single / answer_and_annotation / sample 8046262527830553

- `instance_seed`: `8046262527830553`
- `word_count`: `124`
- `body_word_count`: `72`

```text
The image shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Use rank order 2 < 3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A, with Ace high only. Ignore suits. Read each row from left to right; continue from the top row to each lower row in order. Determine the size of the longest consecutive run when the cards are read in display order.
Annotation format: set "annotation" to an array of bounding boxes [x0, y0, x1, y1] for the cards in the unique longest run.
Answer format: set "answer" to the length of the unique longest consecutive run.
Example JSON:
{"annotation":[[120,80,200,190],[220,80,300,190],[320,80,400,190]],"answer":3}
```

### task_games__cards__longest_run_length / single / answer_only / sample 8046262527830553

- `instance_seed`: `8046262527830553`
- `word_count`: `90`
- `body_word_count`: `72`

```text
The image shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Use rank order 2 < 3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A, with Ace high only. Ignore suits. Read each row from left to right; continue from the top row to each lower row in order. Determine the size of the longest consecutive run when the cards are read in display order.
Required answer format: set "answer" to the length of the unique longest consecutive run.
Example JSON:
{"answer":3}
```

### task_games__cards__missing_card_to_complete_hand_label / missing_flush_card_label / answer_and_annotation / sample 4111994402139026

- `instance_seed`: `4111994402139026`
- `word_count`: `64`
- `body_word_count`: `26`

```text
The figure shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Which candidate card completes a flush for the top hand?
Final answer format: set "answer" to only the selected candidate option letter.
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] for the selected candidate card.
Example JSON:
{"annotation":[320,300,400,420],"answer":"B"}
```

### task_games__cards__missing_card_to_complete_hand_label / missing_flush_card_label / answer_only / sample 4111994402139026

- `instance_seed`: `4111994402139026`
- `word_count`: `42`
- `body_word_count`: `26`

```text
The figure shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Which candidate card completes a flush for the top hand?
Final answer format: set "answer" to only the selected candidate option letter.
Example JSON:
{"answer":"B"}
```

### task_games__cards__missing_card_to_complete_hand_label / missing_full_house_card_label / answer_and_annotation / sample 3212447388236547

- `instance_seed`: `3212447388236547`
- `word_count`: `66`
- `body_word_count`: `27`

```text
You are shown face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Which candidate card completes a full house for the top hand?
Required annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] for the selected candidate card.
Required answer format: set "answer" to only the selected candidate option letter.
Example JSON:
{"annotation":[320,300,400,420],"answer":"B"}
```

### task_games__cards__missing_card_to_complete_hand_label / missing_full_house_card_label / answer_only / sample 3212447388236547

- `instance_seed`: `3212447388236547`
- `word_count`: `43`
- `body_word_count`: `27`

```text
You are shown face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Which candidate card completes a full house for the top hand?
Required answer format: set "answer" to only the selected candidate option letter.
Example JSON:
{"answer":"B"}
```

### task_games__cards__missing_card_to_complete_hand_label / missing_straight_card_label / answer_and_annotation / sample 7788927318216681

- `instance_seed`: `7788927318216681`
- `word_count`: `80`
- `body_word_count`: `43`

```text
The scene shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Use rank order 2 < 3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A, with Ace high only. Which labeled candidate card finishes the straight?
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] for the selected candidate card.
Answer format: set "answer" to only the selected candidate option letter.
Example JSON:
{"annotation":[320,300,400,420],"answer":"B"}
```

### task_games__cards__missing_card_to_complete_hand_label / missing_straight_card_label / answer_only / sample 7788927318216681

- `instance_seed`: `7788927318216681`
- `word_count`: `58`
- `body_word_count`: `43`

```text
The scene shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Use rank order 2 < 3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A, with Ace high only. Which labeled candidate card finishes the straight?
Answer format: set "answer" to only the selected candidate option letter.
Example JSON:
{"answer":"B"}
```

### task_games__cards__missing_card_to_complete_hand_label / missing_three_of_kind_card_label / answer_and_annotation / sample 2018736655941222

- `instance_seed`: `2018736655941222`
- `word_count`: `67`
- `body_word_count`: `28`

```text
The image shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Which option letter completes the top hand as three of a kind?
Required annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] for the selected candidate card.
Required answer format: set "answer" to only the selected candidate option letter.
Example JSON:
{"annotation":[320,300,400,420],"answer":"B"}
```

### task_games__cards__missing_card_to_complete_hand_label / missing_three_of_kind_card_label / answer_only / sample 2018736655941222

- `instance_seed`: `2018736655941222`
- `word_count`: `43`
- `body_word_count`: `28`

```text
The image shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Which option letter completes the top hand as three of a kind?
Answer format: set "answer" to only the selected candidate option letter.
Example JSON:
{"answer":"B"}
```

### task_games__cards__poker_best_hand_label / single / answer_and_annotation / sample 3965099683393090

- `instance_seed`: `3965099683393090`
- `word_count`: `102`
- `body_word_count`: `43`

```text
The image shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Use standard five-card poker ranking. Compare categories first; if categories match, use the usual rank tie-breakers with Ace high. Which option letter labels the winning poker hand?
Annotation format: set "annotation" to an array of bounding boxes [x0, y0, x1, y1] for every card in the winning poker hand.
Answer format: set "answer" to only the winning poker hand option letter.
Example JSON:
{"annotation":[[120,80,200,190],[220,80,300,190],[320,80,400,190],[420,80,500,190],[520,80,600,190]],"answer":"B"}
```

### task_games__cards__poker_best_hand_label / single / answer_only / sample 3965099683393090

- `instance_seed`: `3965099683393090`
- `word_count`: `59`
- `body_word_count`: `55`

```text
The image shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Use standard five-card poker ranking. Compare categories first; if categories match, use the usual rank tie-breakers with Ace high. Which option letter labels the winning poker hand?
Answer field: set "answer" to only the winning poker hand option letter.
Example JSON:
{"answer":"B"}
```

### task_games__cards__poker_draw_card_label / single / answer_and_annotation / sample 7025183544611782

- `instance_seed`: `7025183544611782`
- `word_count`: `87`
- `body_word_count`: `50`

```text
The visual shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Use standard five-card poker ranking. Compare categories first; if categories match, use the usual rank tie-breakers with Ace high. Which candidate card makes the strongest five-card poker hand when added to the top hand?
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] for the selected candidate card.
Answer format: set "answer" to only the selected candidate option letter.
Example JSON:
{"annotation":[320,300,400,420],"answer":"B"}
```

### task_games__cards__poker_draw_card_label / single / answer_only / sample 7025183544611782

- `instance_seed`: `7025183544611782`
- `word_count`: `68`
- `body_word_count`: `50`

```text
The visual shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Use standard five-card poker ranking. Compare categories first; if categories match, use the usual rank tie-breakers with Ace high. Which candidate card makes the strongest five-card poker hand when added to the top hand?
Format for the "answer" field: set "answer" to only the selected candidate option letter.
Example JSON:
{"answer":"B"}
```

### task_games__cards__same_suit_as_reference_count / single / answer_and_annotation / sample 4146575344685257

- `instance_seed`: `4146575344685257`
- `word_count`: `85`
- `body_word_count`: `30`

```text
The visual shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. What is the number of other visible cards that share the reference card's suit?
Annotation format: set "annotation" to an array of bounding boxes [x0, y0, x1, y1] for every non-reference card with the same suit as the reference card.
Answer format: set "answer" to the number of non-reference cards that share the reference card's suit.
Example JSON:
{"annotation":[[120,80,200,190],[220,80,300,190]],"answer":2}
```

### task_games__cards__same_suit_as_reference_count / single / answer_only / sample 4146575344685257

- `instance_seed`: `4146575344685257`
- `word_count`: `51`
- `body_word_count`: `30`

```text
The visual shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. What is the number of other visible cards that share the reference card's suit?
Final answer format: set "answer" to the number of non-reference cards that share the reference card's suit.
Example JSON:
{"answer":2}
```

### task_games__cards__trick_taking_winner_label / single / answer_and_annotation / sample 885716199949201

- `instance_seed`: `885716199949201`
- `word_count`: `114`
- `body_word_count`: `76`

```text
The scene shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Use rank order 2 < 3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A, with Ace high only. The leftmost card is the led card. If any trump card is played, the highest trump wins; otherwise the highest card in the led suit wins. Trump suit: clubs. Identify the option letter for the player who takes this trick.
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] for the single winning played card.
Answer format: set "answer" to only the winning player option letter.
Example JSON:
{"annotation":[320,120,400,250],"answer":"B"}
```

### task_games__cards__trick_taking_winner_label / single / answer_only / sample 885716199949201

- `instance_seed`: `885716199949201`
- `word_count`: `92`
- `body_word_count`: `76`

```text
The scene shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Use rank order 2 < 3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A, with Ace high only. The leftmost card is the led card. If any trump card is played, the highest trump wins; otherwise the highest card in the led suit wins. Trump suit: clubs. Identify the option letter for the player who takes this trick.
Required answer format: set "answer" to only the winning player option letter.
Example JSON:
{"answer":"B"}
```

### task_games__cards__trick_winning_play_label / single / answer_and_annotation / sample 1587525629189333

- `instance_seed`: `1587525629189333`
- `word_count`: `124`
- `body_word_count`: `86`

```text
The image shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Use rank order 2 < 3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A, with Ace high only. The top row shows cards already played. The card marked LED led the trick. If any trump card is played or chosen, the highest trump wins; otherwise the highest card in the led suit wins. There is no trump suit. Which candidate card would win the trick if played next?
Final answer format: set "answer" to only the selected candidate option letter.
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] for the selected candidate card.
Example JSON:
{"annotation":[320,300,400,420],"answer":"B"}
```

### task_games__cards__trick_winning_play_label / single / answer_only / sample 1587525629189333

- `instance_seed`: `1587525629189333`
- `word_count`: `101`
- `body_word_count`: `86`

```text
The image shows face-up playing cards arranged as a hand, labeled hands, or labeled candidate cards. Use rank order 2 < 3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A, with Ace high only. The top row shows cards already played. The card marked LED led the trick. If any trump card is played or chosen, the highest trump wins; otherwise the highest card in the led suit wins. There is no trump suit. Which candidate card would win the trick if played next?
Answer format: set "answer" to only the selected candidate option letter.
Example JSON:
{"answer":"B"}
```

### task_games__checkers__max_capture_chain_length / single / answer_and_annotation / sample 1713661661325778

- `instance_seed`: `1713661661325778`
- `word_count`: `143`
- `body_word_count`: `74`

```text
The visual shows an 8 by 8 checkers board with red and black pieces. Black to move. A jump captures one adjacent opponent piece and lands on the empty square beyond. The outlined checker is a king; it may capture diagonally in any direction, remove the jumped piece, and continue jumping from each landing square while another capture is available. Count the largest possible number of captures in one chain for the marked king.
Required annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for the opponent pieces captured along the longest chain.
Required answer format: set "answer" to the maximum number of opponent pieces the marked king can capture in one continuous jump chain.
Example JSON:
{"annotation":[[144,200,184,240],[216,272,256,312],[288,344,328,384],[360,416,400,456]],"answer":4}
```

### task_games__checkers__max_capture_chain_length / single / answer_only / sample 1713661661325778

- `instance_seed`: `1713661661325778`
- `word_count`: `100`
- `body_word_count`: `74`

```text
The visual shows an 8 by 8 checkers board with red and black pieces. Black to move. A jump captures one adjacent opponent piece and lands on the empty square beyond. The outlined checker is a king; it may capture diagonally in any direction, remove the jumped piece, and continue jumping from each landing square while another capture is available. Count the largest possible number of captures in one chain for the marked king.
Final answer format: set "answer" to the maximum number of opponent pieces the marked king can capture in one continuous jump chain.
Example JSON:
{"answer":4}
```

### task_games__checkers__move_count / capture_move_count / answer_and_annotation / sample 142105274151844

- `instance_seed`: `142105274151844`
- `word_count`: `111`
- `body_word_count`: `58`

```text
The scene shows an 8 by 8 checkers board with red and black pieces. Red moves next. Red moves upward and Black moves downward. A jump captures one adjacent opponent piece and lands on the empty square beyond. Count only one jump per move; ignore follow-up jumps. What is the number of legal capture landing squares for Red?
Annotation format: set "annotation" to a JSON array of pixel-space square boxes [x0, y0, x1, y1] for every capture landing square; use an empty array if none are available.
Answer format: set "answer" to the count of capture landing squares.
Example JSON:
{"annotation":[[132,188,196,252],[204,188,268,252]],"answer":2}
```

### task_games__checkers__move_count / capture_move_count / answer_only / sample 142105274151844

- `instance_seed`: `142105274151844`
- `word_count`: `73`
- `body_word_count`: `69`

```text
The scene shows an 8 by 8 checkers board with red and black pieces. Red moves next. Red moves upward and Black moves downward. A jump captures one adjacent opponent piece and lands on the empty square beyond. Count only one jump per move; ignore follow-up jumps. What is the number of legal capture landing squares for Red?
Answer field: set "answer" to the count of capture landing squares.
Example JSON:
{"answer":2}
```

### task_games__checkers__move_count / legal_move_count / answer_and_annotation / sample 5182724987378522

- `instance_seed`: `5182724987378522`
- `word_count`: `123`
- `body_word_count`: `66`

```text
The scene shows a crowded 8 by 8 checkers board with many red and black pieces. Black moves next. Black moves downward and Red moves upward. A jump captures one adjacent opponent piece and lands on the empty square beyond. Count only one jump per move; ignore follow-up jumps. Include simple diagonal steps and capture jumps. What is the number of legal landing squares for Black?
Annotation format: set "annotation" to a JSON array of pixel-space square boxes [x0, y0, x1, y1] for every legal landing square; use an empty array if none are available.
Answer format: set "answer" to the count of legal landing squares.
Example JSON:
{"annotation":[[132,188,196,252],[204,188,268,252],[276,188,340,252]],"answer":3}
```

### task_games__checkers__move_count / legal_move_count / answer_only / sample 5182724987378522

- `instance_seed`: `5182724987378522`
- `word_count`: `81`
- `body_word_count`: `77`

```text
The scene shows a crowded 8 by 8 checkers board with many red and black pieces. Black moves next. Black moves downward and Red moves upward. A jump captures one adjacent opponent piece and lands on the empty square beyond. Count only one jump per move; ignore follow-up jumps. Include simple diagonal steps and capture jumps. What is the number of legal landing squares for Black?
Answer field: set "answer" to the count of legal landing squares.
Example JSON:
{"answer":3}
```

### task_games__checkers__piece_mobility_count / piece_with_capture_move_count / answer_and_annotation / sample 3425338681655655

- `instance_seed`: `3425338681655655`
- `word_count`: `120`
- `body_word_count`: `57`

```text
This scene shows an 8 by 8 checkers board with red and black pieces. Red moves next. Red moves upward and Black moves downward. A jump captures one adjacent opponent piece and lands on the empty square beyond. Count only one jump per move; ignore follow-up jumps. What is the number of Red pieces that can capture?
Annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for every current-player piece with at least one capture jump; use an empty array if none are available.
Answer format: set "answer" to the number of current-player pieces with at least one capture jump.
Example JSON:
{"annotation":[[144,200,184,240],[216,272,256,312]],"answer":2}
```

### task_games__checkers__piece_mobility_count / piece_with_capture_move_count / answer_only / sample 3425338681655655

- `instance_seed`: `3425338681655655`
- `word_count`: `77`
- `body_word_count`: `73`

```text
This scene shows an 8 by 8 checkers board with red and black pieces. Red moves next. Red moves upward and Black moves downward. A jump captures one adjacent opponent piece and lands on the empty square beyond. Count only one jump per move; ignore follow-up jumps. What is the number of Red pieces that can capture?
Answer field: set "answer" to the number of current-player pieces with at least one capture jump.
Example JSON:
{"answer":2}
```

### task_games__checkers__piece_mobility_count / piece_with_legal_move_count / answer_and_annotation / sample 3825237304870731

- `instance_seed`: `3825237304870731`
- `word_count`: `133`
- `body_word_count`: `66`

```text
The visual shows a crowded 8 by 8 checkers board with many red and black pieces. Black moves next. Black moves downward and Red moves upward. A jump captures one adjacent opponent piece and lands on the empty square beyond. Count only one jump per move; ignore follow-up jumps. Include simple diagonal steps and capture jumps. What is the number of Black pieces that can move?
Annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for every current-player piece with at least one legal move; use an empty array if none are available.
Answer format: set "answer" to the number of current-player pieces with at least one legal move.
Example JSON:
{"annotation":[[144,200,184,240],[216,272,256,312],[288,344,328,384]],"answer":3}
```

### task_games__checkers__piece_mobility_count / piece_with_legal_move_count / answer_only / sample 3825237304870731

- `instance_seed`: `3825237304870731`
- `word_count`: `86`
- `body_word_count`: `82`

```text
The visual shows a crowded 8 by 8 checkers board with many red and black pieces. Black moves next. Black moves downward and Red moves upward. A jump captures one adjacent opponent piece and lands on the empty square beyond. Count only one jump per move; ignore follow-up jumps. Include simple diagonal steps and capture jumps. What is the number of Black pieces that can move?
Answer field: set "answer" to the number of current-player pieces with at least one legal move.
Example JSON:
{"answer":3}
```

### task_games__checkers__piece_state_count / single / answer_and_annotation / sample 3394037100585796

- `instance_seed`: `3394037100585796`
- `word_count`: `88`
- `body_word_count`: `27`

```text
The visual shows a crowded 8 by 8 checkers board with many red and black pieces. Determine the count of red pieces that are on the board.
Annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for every piece requested in the question; use an empty array if none are present.
Answer format: set "answer" to the number of pieces requested in the question.
Example JSON:
{"annotation":[[144,200,184,240],[216,272,256,312],[288,344,328,384]],"answer":3}
```

### task_games__checkers__piece_state_count / single / answer_only / sample 3394037100585796

- `instance_seed`: `3394037100585796`
- `word_count`: `44`
- `body_word_count`: `27`

```text
The visual shows a crowded 8 by 8 checkers board with many red and black pieces. Determine the count of red pieces that are on the board.
Answer format: set "answer" to the number of pieces requested in the question.
Example JSON:
{"answer":3}
```

### task_games__chess__checkmate_move_label / single / answer_and_annotation / sample 5551611561224049

- `instance_seed`: `5551611561224049`
- `word_count`: `107`
- `body_word_count`: `39`

```text
The image shows a partial chess board with white and black pieces. Use normal chess piece movement. Do not use castling, en passant, or promotion. Black to move. Using the coordinate labels, choose the option that checkmates White now.
Required annotation format: set "annotation" to a JSON object with keys "from", "to", and "king", each mapped to a pixel-space point [x, y] at the center of the selected move's source square, destination square, and opposing king square.
Required answer format: set "answer" to the single selected option letter shown in the move-option panel.
Example JSON:
{"annotation":{"from":[140,140],"to":[220,140],"king":[300,140]},"answer":"B"}
```

### task_games__chess__checkmate_move_label / single / answer_only / sample 5551611561224049

- `instance_seed`: `5551611561224049`
- `word_count`: `61`
- `body_word_count`: `39`

```text
The image shows a partial chess board with white and black pieces. Use normal chess piece movement. Do not use castling, en passant, or promotion. Black to move. Using the coordinate labels, choose the option that checkmates White now.
Format for the "answer" field: set "answer" to the single selected option letter shown in the move-option panel.
Example JSON:
{"answer":"B"}
```

### task_games__chess__colored_piece_kind_count / single / answer_and_annotation / sample 5308224719420149

- `instance_seed`: `5308224719420149`
- `word_count`: `73`
- `body_word_count`: `20`

```text
The image shows a partial chess board with white and black pieces. Count all White pawns shown on the board.
Annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for every matching visible piece; use an empty array if none are shown.
Answer format: set "answer" to the count of matching visible pieces.
Example JSON:
{"annotation":[[116,116,164,164],[276,116,324,164]],"answer":2}
```

### task_games__chess__colored_piece_kind_count / single / answer_only / sample 5308224719420149

- `instance_seed`: `5308224719420149`
- `word_count`: `35`
- `body_word_count`: `31`

```text
The image shows a partial chess board with white and black pieces. Count all White pawns shown on the board.
Answer field: set "answer" to the count of matching visible pieces.
Example JSON:
{"answer":2}
```

### task_games__chess__king_escape_square_count / single / answer_and_annotation / sample 2928519335346223

- `instance_seed`: `2928519335346223`
- `word_count`: `120`
- `body_word_count`: `60`

```text
The figure shows a partial chess board with white and black pieces. Use normal chess piece movement. Do not use castling, en passant, or promotion. The red outlined square contains the marked king. Count one-step king destinations that are empty or capturable and are not attacked after the king moves there. Count the safe movement destinations for the marked king.
Required annotation format: set "annotation" to a JSON array of pixel-space square boxes [x0, y0, x1, y1] for every safe destination square; use an empty array if there are none.
Required answer format: set "answer" to the count of safe one-step destination squares for the marked king.
Example JSON:
{"annotation":[[108,108,172,172],[268,108,332,172]],"answer":2}
```

### task_games__chess__king_escape_square_count / single / answer_only / sample 2928519335346223

- `instance_seed`: `2928519335346223`
- `word_count`: `83`
- `body_word_count`: `60`

```text
The figure shows a partial chess board with white and black pieces. Use normal chess piece movement. Do not use castling, en passant, or promotion. The red outlined square contains the marked king. Count one-step king destinations that are empty or capturable and are not attacked after the king moves there. Count the safe movement destinations for the marked king.
Format for the "answer" field: set "answer" to the count of safe one-step destination squares for the marked king.
Example JSON:
{"answer":2}
```

### task_games__chess__marked_piece_blocker_count / bishop_diagonal_blocker_count / answer_and_annotation / sample 3256531198725095

- `instance_seed`: `3256531198725095`
- `word_count`: `120`
- `body_word_count`: `51`

```text
The image shows a partial chess board with white and black pieces. The red outlined square contains the source piece. The blue outlined square is the target square. Count only pieces on the intervening squares along the bishop's diagonal movement line. Determine the number of intervening pieces on that bishop diagonal.
Annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for every intervening piece on that bishop diagonal; use an empty array if none are on the path.
Answer format: set "answer" to the count of pieces on the intervening squares along the marked bishop's diagonal to the target square.
Example JSON:
{"annotation":[[116,116,164,164],[276,116,324,164]],"answer":2}
```

### task_games__chess__marked_piece_blocker_count / bishop_diagonal_blocker_count / answer_only / sample 3256531198725095

- `instance_seed`: `3256531198725095`
- `word_count`: `80`
- `body_word_count`: `51`

```text
The image shows a partial chess board with white and black pieces. The red outlined square contains the source piece. The blue outlined square is the target square. Count only pieces on the intervening squares along the bishop's diagonal movement line. Determine the number of intervening pieces on that bishop diagonal.
Format for the "answer" field: set "answer" to the count of pieces on the intervening squares along the marked bishop's diagonal to the target square.
Example JSON:
{"answer":2}
```

### task_games__chess__marked_piece_blocker_count / queen_line_blocker_count / answer_and_annotation / sample 4906266297188375

- `instance_seed`: `4906266297188375`
- `word_count`: `125`
- `body_word_count`: `54`

```text
The scene shows a partial chess board with white and black pieces. The red outlined square contains the source piece. The blue outlined square is the target square. Count only pieces on the intervening squares along the queen's row, column, or diagonal movement line. Determine the number of intervening pieces on that queen line.
Annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for every intervening piece on that queen movement line; use an empty array if none are on the path.
Answer format: set "answer" to the count of pieces on the intervening squares along the marked queen's movement line to the target square.
Example JSON:
{"annotation":[[116,116,164,164],[276,116,324,164]],"answer":2}
```

### task_games__chess__marked_piece_blocker_count / queen_line_blocker_count / answer_only / sample 4906266297188375

- `instance_seed`: `4906266297188375`
- `word_count`: `81`
- `body_word_count`: `77`

```text
The scene shows a partial chess board with white and black pieces. The red outlined square contains the source piece. The blue outlined square is the target square. Count only pieces on the intervening squares along the queen's row, column, or diagonal movement line. Determine the number of intervening pieces on that queen line.
Answer field: set "answer" to the count of pieces on the intervening squares along the marked queen's movement line to the target square.
Example JSON:
{"answer":2}
```

### task_games__chess__marked_piece_blocker_count / rook_line_blocker_count / answer_and_annotation / sample 568455377085864

- `instance_seed`: `568455377085864`
- `word_count`: `124`
- `body_word_count`: `53`

```text
This scene shows a partial chess board with white and black pieces. The red outlined square contains the source piece. The blue outlined square is the target square. Count only pieces on the intervening squares along the rook's row or column movement line. Determine the number of intervening pieces on that rook line.
Annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for every intervening piece on that rook movement line; use an empty array if none are on the path.
Answer format: set "answer" to the count of pieces on the intervening squares along the marked rook's movement line to the target square.
Example JSON:
{"annotation":[[116,116,164,164],[276,116,324,164]],"answer":2}
```

### task_games__chess__marked_piece_blocker_count / rook_line_blocker_count / answer_only / sample 568455377085864

- `instance_seed`: `568455377085864`
- `word_count`: `80`
- `body_word_count`: `53`

```text
This scene shows a partial chess board with white and black pieces. The red outlined square contains the source piece. The blue outlined square is the target square. Count only pieces on the intervening squares along the rook's row or column movement line. Determine the number of intervening pieces on that rook line.
Answer format: set "answer" to the count of pieces on the intervening squares along the marked rook's movement line to the target square.
Example JSON:
{"answer":2}
```

### task_games__chess__marked_piece_destination_count / marked_piece_capture_count / answer_and_annotation / sample 3355913793251530

- `instance_seed`: `3355913793251530`
- `word_count`: `100`
- `body_word_count`: `33`

```text
The visual shows a partial chess board with white and black pieces. The red outlined square contains the marked piece. Using normal chess movement, how many opponent pieces are capturable by that piece?
Required annotation format: set "annotation" to a JSON array of pixel-space square boxes [x0, y0, x1, y1] for every capturable destination square occupied by an opponent piece; use an empty array if none are available.
Required answer format: set "answer" to the count of opponent pieces the marked piece can capture in one move.
Example JSON:
{"annotation":[[108,108,172,172],[268,108,332,172]],"answer":2}
```

### task_games__chess__marked_piece_destination_count / marked_piece_capture_count / answer_only / sample 3355913793251530

- `instance_seed`: `3355913793251530`
- `word_count`: `55`
- `body_word_count`: `51`

```text
The visual shows a partial chess board with white and black pieces. The red outlined square contains the marked piece. Using normal chess movement, how many opponent pieces are capturable by that piece?
Answer field: set "answer" to the count of opponent pieces the marked piece can capture in one move.
Example JSON:
{"answer":2}
```

### task_games__chess__marked_piece_destination_count / marked_piece_move_count / answer_and_annotation / sample 800167121841720

- `instance_seed`: `800167121841720`
- `word_count`: `108`
- `body_word_count`: `45`

```text
The scene shows a partial chess board with white and black pieces. Use normal chess piece movement. Do not use castling, en passant, or promotion. The red outlined square contains the marked piece. Count the squares the marked piece can move to in one move.
Required annotation format: set "annotation" to a JSON array of pixel-space square boxes [x0, y0, x1, y1] for every destination square the marked piece can move to; use an empty array if none are available.
Required answer format: set "answer" to the count of destination squares for the marked piece.
Example JSON:
{"annotation":[[108,108,172,172],[268,108,332,172]],"answer":2}
```

### task_games__chess__marked_piece_destination_count / marked_piece_move_count / answer_only / sample 800167121841720

- `instance_seed`: `800167121841720`
- `word_count`: `66`
- `body_word_count`: `45`

```text
The scene shows a partial chess board with white and black pieces. Use normal chess piece movement. Do not use castling, en passant, or promotion. The red outlined square contains the marked piece. Count the squares the marked piece can move to in one move.
Format for the "answer" field: set "answer" to the count of destination squares for the marked piece.
Example JSON:
{"answer":2}
```

### task_games__chess__piece_kind_count / single / answer_and_annotation / sample 8098943541670380

- `instance_seed`: `8098943541670380`
- `word_count`: `72`
- `body_word_count`: `19`

```text
The image shows a partial chess board with white and black pieces. How many rooks are on the board?
Annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for every matching visible piece; use an empty array if none are shown.
Answer format: set "answer" to the count of matching visible pieces.
Example JSON:
{"annotation":[[116,116,164,164],[276,116,324,164]],"answer":2}
```

### task_games__chess__piece_kind_count / single / answer_only / sample 8098943541670380

- `instance_seed`: `8098943541670380`
- `word_count`: `34`
- `body_word_count`: `19`

```text
The image shows a partial chess board with white and black pieces. How many rooks are on the board?
Answer format: set "answer" to the count of matching visible pieces.
Example JSON:
{"answer":2}
```

### task_games__chess__player_capture_piece_count / single / answer_and_annotation / sample 8906421582782072

- `instance_seed`: `8906421582782072`
- `word_count`: `97`
- `body_word_count`: `37`

```text
This scene shows a partial chess board with white and black pieces. Use normal chess piece movement. Do not use castling, en passant, or promotion. Count the White pieces that are capturable by Black in one move.
Annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for every capturable opponent piece; use an empty array if none are available.
Answer format: set "answer" to the count of opponent pieces capturable in one move by the named side.
Example JSON:
{"annotation":[[116,116,164,164],[276,116,324,164]],"answer":2}
```

### task_games__chess__player_capture_piece_count / single / answer_only / sample 8906421582782072

- `instance_seed`: `8906421582782072`
- `word_count`: `60`
- `body_word_count`: `37`

```text
This scene shows a partial chess board with white and black pieces. Use normal chess piece movement. Do not use castling, en passant, or promotion. Count the White pieces that are capturable by Black in one move.
Required answer format: set "answer" to the count of opponent pieces capturable in one move by the named side.
Example JSON:
{"answer":2}
```

### task_games__chess__target_square_attacker_count / black_piece_attacks_target_square_count / answer_and_annotation / sample 5814128200201630

- `instance_seed`: `5814128200201630`
- `word_count`: `92`
- `body_word_count`: `35`

```text
The scene shows a partial chess board with white and black pieces. Use normal chess piece movement. Do not use castling, en passant, or promotion. Determine how many black pieces attack the marked target square.
Annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for every black attacking piece; use an empty array if none are attacking.
Answer format: set "answer" to the count of black pieces attacking the marked target square.
Example JSON:
{"annotation":[[116,116,164,164],[276,116,324,164]],"answer":2}
```

### task_games__chess__target_square_attacker_count / black_piece_attacks_target_square_count / answer_only / sample 5814128200201630

- `instance_seed`: `5814128200201630`
- `word_count`: `54`
- `body_word_count`: `35`

```text
The scene shows a partial chess board with white and black pieces. Use normal chess piece movement. Do not use castling, en passant, or promotion. Determine how many black pieces attack the marked target square.
Answer format: set "answer" to the count of black pieces attacking the marked target square.
Example JSON:
{"answer":2}
```

### task_games__chess__target_square_attacker_count / king_square_attacker_count / answer_and_annotation / sample 1315125547725738

- `instance_seed`: `1315125547725738`
- `word_count`: `100`
- `body_word_count`: `42`

```text
The figure shows a partial chess board with white and black pieces. Use normal chess piece movement. Do not use castling, en passant, or promotion. The red outlined square contains the marked king. How many opponent pieces are attacking the marked king?
Required annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for every attacking opponent piece; use an empty array if none are attacking.
Required answer format: set "answer" to the count of opponent pieces attacking the marked king.
Example JSON:
{"annotation":[[116,116,164,164],[276,116,324,164]],"answer":2}
```

### task_games__chess__target_square_attacker_count / king_square_attacker_count / answer_only / sample 1315125547725738

- `instance_seed`: `1315125547725738`
- `word_count`: `60`
- `body_word_count`: `56`

```text
The figure shows a partial chess board with white and black pieces. Use normal chess piece movement. Do not use castling, en passant, or promotion. The red outlined square contains the marked king. How many opponent pieces are attacking the marked king?
Answer field: set "answer" to the count of opponent pieces attacking the marked king.
Example JSON:
{"answer":2}
```

### task_games__chess__target_square_attacker_count / white_piece_attacks_target_square_count / answer_and_annotation / sample 4085047352368915

- `instance_seed`: `4085047352368915`
- `word_count`: `98`
- `body_word_count`: `41`

```text
The scene shows a partial chess board with white and black pieces. Use normal chess piece movement. Do not use castling, en passant, or promotion. The red outlined square marks the target square. How many white pieces attack the target square?
Annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for every white attacking piece; use an empty array if none are attacking.
Answer format: set "answer" to the count of white pieces attacking the marked target square.
Example JSON:
{"annotation":[[116,116,164,164],[276,116,324,164]],"answer":2}
```

### task_games__chess__target_square_attacker_count / white_piece_attacks_target_square_count / answer_only / sample 4085047352368915

- `instance_seed`: `4085047352368915`
- `word_count`: `61`
- `body_word_count`: `41`

```text
The scene shows a partial chess board with white and black pieces. Use normal chess piece movement. Do not use castling, en passant, or promotion. The red outlined square marks the target square. How many white pieces attack the target square?
Final answer format: set "answer" to the count of white pieces attacking the marked target square.
Example JSON:
{"answer":2}
```

### task_games__chess_variant__marked_piece_destination_count / marked_piece_capture_count / answer_and_annotation / sample 5419749470631630

- `instance_seed`: `5419749470631630`
- `word_count`: `167`
- `body_word_count`: `108`

```text
The figure shows a chess-like 8 by 8 board with many white and black chess pieces and a visible movement rule card. White pieces are one side and black pieces are the other side. Every piece uses the displayed movement rule. The red outlined square contains the marked piece. The rule card says the marked piece jumps exactly 3 rows and 1 column, or 1 row and 3 columns. The marked piece may land on an empty square or an opponent piece, but not on a friendly piece. For jump rules, the marked piece may jump over occupied squares. Count the opponent pieces capturable by the marked piece.
Annotation format: set "annotation" to a JSON array of pixel-space square boxes [x0, y0, x1, y1] for every destination square occupied by an opponent piece that the marked piece can capture.
Answer format: set "answer" to the count of capture destination squares for the marked piece.
Example JSON:
{"annotation":[[140,220,210,290],[210,220,280,290]],"answer":2}
```

### task_games__chess_variant__marked_piece_destination_count / marked_piece_capture_count / answer_only / sample 5419749470631630

- `instance_seed`: `5419749470631630`
- `word_count`: `127`
- `body_word_count`: `123`

```text
The figure shows a chess-like 8 by 8 board with many white and black chess pieces and a visible movement rule card. White pieces are one side and black pieces are the other side. Every piece uses the displayed movement rule. The red outlined square contains the marked piece. The rule card says the marked piece jumps exactly 3 rows and 1 column, or 1 row and 3 columns. The marked piece may land on an empty square or an opponent piece, but not on a friendly piece. For jump rules, the marked piece may jump over occupied squares. Count the opponent pieces capturable by the marked piece.
Answer field: set "answer" to the count of capture destination squares for the marked piece.
Example JSON:
{"answer":2}
```

### task_games__chess_variant__marked_piece_destination_count / marked_piece_move_count / answer_and_annotation / sample 6889077305685315

- `instance_seed`: `6889077305685315`
- `word_count`: `174`
- `body_word_count`: `112`

```text
The visual shows a chess-like 8 by 8 board with many white and black chess pieces and a visible movement rule card. The rule card says the marked piece moves diagonally up to 3 squares. The marked piece may land on an empty square or an opponent piece, but not on a friendly piece. For range rules, movement stops at the first occupied square in each direction and cannot pass through it. White pieces are one side and black pieces are the other side. Every piece uses the displayed movement rule. The red outlined square contains the marked piece. What is the number of legal squares the marked piece can move to?
Final answer format: set "answer" to the count of legal destination squares for the marked piece.
Annotation format: set "annotation" to a JSON array of pixel-space square boxes [x0, y0, x1, y1] for every legal destination square of the marked piece.
Example JSON:
{"annotation":[[140,220,210,290],[210,220,280,290],[280,220,350,290],[350,220,420,290]],"answer":4}
```

### task_games__chess_variant__marked_piece_destination_count / marked_piece_move_count / answer_only / sample 6889077305685315

- `instance_seed`: `6889077305685315`
- `word_count`: `132`
- `body_word_count`: `112`

```text
The visual shows a chess-like 8 by 8 board with many white and black chess pieces and a visible movement rule card. The rule card says the marked piece moves diagonally up to 3 squares. The marked piece may land on an empty square or an opponent piece, but not on a friendly piece. For range rules, movement stops at the first occupied square in each direction and cannot pass through it. White pieces are one side and black pieces are the other side. Every piece uses the displayed movement rule. The red outlined square contains the marked piece. What is the number of legal squares the marked piece can move to?
Final answer format: set "answer" to the count of legal destination squares for the marked piece.
Example JSON:
{"answer":4}
```

### task_games__chess_variant__target_square_reacher_count / black_piece_reaches_target_count / answer_and_annotation / sample 8969480411857182

- `instance_seed`: `8969480411857182`
- `word_count`: `187`
- `body_word_count`: `120`

```text
You are shown a chess-like 8 by 8 board with a small set of white and black chess pieces and a visible movement rule card. The rule card says pieces move diagonally up to 3 squares. White pieces are one side and black pieces are the other side. Every piece uses the displayed movement rule. The blue outlined square is the target square. A counted piece may move to the target square if the target is empty or contains an opponent piece, but not if it contains a friendly piece. For range rules, movement stops at the first occupied square in each direction and cannot pass through it. Count the Black pieces that can reach the blue outlined target square.
Annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for every black piece that can legally move to the blue outlined target square.
Answer format: set "answer" to the number of black pieces that can legally move to the blue outlined target square.
Example JSON:
{"annotation":[[140,220,210,290],[210,220,280,290],[280,220,350,290]],"answer":3}
```

### task_games__chess_variant__target_square_reacher_count / black_piece_reaches_target_count / answer_only / sample 8969480411857182

- `instance_seed`: `8969480411857182`
- `word_count`: `144`
- `body_word_count`: `120`

```text
You are shown a chess-like 8 by 8 board with a small set of white and black chess pieces and a visible movement rule card. The rule card says pieces move diagonally up to 3 squares. White pieces are one side and black pieces are the other side. Every piece uses the displayed movement rule. The blue outlined square is the target square. A counted piece may move to the target square if the target is empty or contains an opponent piece, but not if it contains a friendly piece. For range rules, movement stops at the first occupied square in each direction and cannot pass through it. Count the Black pieces that can reach the blue outlined target square.
Answer format: set "answer" to the number of black pieces that can legally move to the blue outlined target square.
Example JSON:
{"answer":3}
```

### task_games__chess_variant__target_square_reacher_count / white_piece_reaches_target_count / answer_and_annotation / sample 551304661166316

- `instance_seed`: `551304661166316`
- `word_count`: `180`
- `body_word_count`: `111`

```text
The image shows a chess-like 8 by 8 board with a small set of white and black chess pieces and a visible movement rule card. White pieces are one side and black pieces are the other side. Every piece uses the displayed movement rule. The blue outlined square is the target square. Using the displayed movement rule, how many White pieces can move to that square? A counted piece may move to the target square if the target is empty or contains an opponent piece, but not if it contains a friendly piece. For range rules, movement stops at the first occupied square in each direction and cannot pass through it.
Required annotation format: set "annotation" to a JSON array of pixel-space piece boxes [x0, y0, x1, y1] for every white piece that can legally move to the blue outlined target square.
Required answer format: set "answer" to the number of white pieces that can legally move to the blue outlined target square.
Example JSON:
{"annotation":[[140,220,210,290],[210,220,280,290],[280,220,350,290]],"answer":3}
```

### task_games__chess_variant__target_square_reacher_count / white_piece_reaches_target_count / answer_only / sample 551304661166316

- `instance_seed`: `551304661166316`
- `word_count`: `136`
- `body_word_count`: `111`

```text
The image shows a chess-like 8 by 8 board with a small set of white and black chess pieces and a visible movement rule card. White pieces are one side and black pieces are the other side. Every piece uses the displayed movement rule. The blue outlined square is the target square. Using the displayed movement rule, how many White pieces can move to that square? A counted piece may move to the target square if the target is empty or contains an opponent piece, but not if it contains a friendly piece. For range rules, movement stops at the first occupied square in each direction and cannot pass through it.
Required answer format: set "answer" to the number of white pieces that can legally move to the blue outlined target square.
Example JSON:
{"answer":3}
```

### task_games__circular_chess__marked_piece_destination_count / marked_piece_capture_count / answer_and_annotation / sample 2042779560694741

- `instance_seed`: `2042779560694741`
- `word_count`: `137`
- `body_word_count`: `87`

```text
The scene contains a circular chess board with four rings, sixteen sectors per ring, and a small set of white and black chess pieces. Use the marked piece's standard chess movement on this circular board. Sectors wrap around each ring; rings do not wrap inward or outward. A piece may land on an empty cell or an opponent piece, but not on a friendly piece. Sliding pieces stop at the first occupied cell in a direction. How many capture destinations are available to the red marked piece?
Annotation format: set "annotation" to a JSON array of pixel-space points [x, y] at the centers of every opponent-occupied destination cell the marked piece can capture.
Answer format: set "answer" to the number of opponent pieces the marked piece can capture.
Example JSON:
{"annotation":[[420,210],[502,244]],"answer":2}
```

### task_games__circular_chess__marked_piece_destination_count / marked_piece_capture_count / answer_only / sample 2042779560694741

- `instance_seed`: `2042779560694741`
- `word_count`: `109`
- `body_word_count`: `87`

```text
The scene contains a circular chess board with four rings, sixteen sectors per ring, and a small set of white and black chess pieces. Use the marked piece's standard chess movement on this circular board. Sectors wrap around each ring; rings do not wrap inward or outward. A piece may land on an empty cell or an opponent piece, but not on a friendly piece. Sliding pieces stop at the first occupied cell in a direction. How many capture destinations are available to the red marked piece?
Format for the "answer" field: set "answer" to the number of opponent pieces the marked piece can capture.
Example JSON:
{"answer":2}
```

### task_games__circular_chess__marked_piece_destination_count / marked_piece_move_count / answer_and_annotation / sample 2544417858435633

- `instance_seed`: `2544417858435633`
- `word_count`: `138`
- `body_word_count`: `85`

```text
The image shows a circular chess board with four rings, sixteen sectors per ring, and many white and black chess pieces. Use the marked piece's standard chess movement on this circular board. Sectors wrap around each ring; rings do not wrap inward or outward. A piece may land on an empty cell or an opponent piece, but not on a friendly piece. Sliding pieces stop at the first occupied cell in a direction. How many legal movement destinations are available to the red marked piece?
Required annotation format: set "annotation" to a JSON array of pixel-space points [x, y] at the centers of every legal destination cell for the marked piece.
Required answer format: set "answer" to the number of legal destination cells for the marked piece.
Example JSON:
{"annotation":[[420,210],[502,244],[536,328]],"answer":3}
```

### task_games__circular_chess__marked_piece_destination_count / marked_piece_move_count / answer_only / sample 2544417858435633

- `instance_seed`: `2544417858435633`
- `word_count`: `104`
- `body_word_count`: `85`

```text
The image shows a circular chess board with four rings, sixteen sectors per ring, and many white and black chess pieces. Use the marked piece's standard chess movement on this circular board. Sectors wrap around each ring; rings do not wrap inward or outward. A piece may land on an empty cell or an opponent piece, but not on a friendly piece. Sliding pieces stop at the first occupied cell in a direction. How many legal movement destinations are available to the red marked piece?
Answer format: set "answer" to the number of legal destination cells for the marked piece.
Example JSON:
{"answer":3}
```

### task_games__circular_chess__target_cell_reacher_count / black_piece_reaches_target_count / answer_and_annotation / sample 7841531722063098

- `instance_seed`: `7841531722063098`
- `word_count`: `173`
- `body_word_count`: `114`

```text
The scene contains a circular chess board with four rings, sixteen sectors per ring, and a small set of white and black chess pieces. Use standard chess movement on this circular board. Rooks move around rings or across rings, bishops move diagonally between rings and sectors, queens combine rook and bishop movement, knights jump, and kings move one step. Sectors wrap around each ring; rings do not wrap inward or outward. A piece may land on an empty cell or an opponent piece, but not on a friendly piece. Sliding pieces stop at the first occupied cell in a direction. Count every Black piece that has the red marked cell as a legal destination.
Annotation format: set "annotation" to a JSON array of pixel-space points [x, y] at the centers of every Black piece that can move to the red marked target cell.
Answer format: set "answer" to the number of Black pieces that can move to the red marked target cell.
Example JSON:
{"annotation":[[420,210],[502,244],[536,328]],"answer":3}
```

### task_games__circular_chess__target_cell_reacher_count / black_piece_reaches_target_count / answer_only / sample 7841531722063098

- `instance_seed`: `7841531722063098`
- `word_count`: `137`
- `body_word_count`: `114`

```text
The scene contains a circular chess board with four rings, sixteen sectors per ring, and a small set of white and black chess pieces. Use standard chess movement on this circular board. Rooks move around rings or across rings, bishops move diagonally between rings and sectors, queens combine rook and bishop movement, knights jump, and kings move one step. Sectors wrap around each ring; rings do not wrap inward or outward. A piece may land on an empty cell or an opponent piece, but not on a friendly piece. Sliding pieces stop at the first occupied cell in a direction. Count every Black piece that has the red marked cell as a legal destination.
Answer format: set "answer" to the number of Black pieces that can move to the red marked target cell.
Example JSON:
{"answer":3}
```

### task_games__circular_chess__target_cell_reacher_count / white_piece_reaches_target_count / answer_and_annotation / sample 179360609203867

- `instance_seed`: `179360609203867`
- `word_count`: `169`
- `body_word_count`: `110`

```text
The figure shows a circular chess board with four rings, sixteen sectors per ring, and many white and black chess pieces. How many White pieces could legally move onto the red marked target cell? Sectors wrap around each ring; rings do not wrap inward or outward. Use standard chess movement on this circular board. Rooks move around rings or across rings, bishops move diagonally between rings and sectors, queens combine rook and bishop movement, knights jump, and kings move one step. A piece may land on an empty cell or an opponent piece, but not on a friendly piece. Sliding pieces stop at the first occupied cell in a direction.
Annotation format: set "annotation" to a JSON array of pixel-space points [x, y] at the centers of every White piece that can move to the red marked target cell.
Answer format: set "answer" to the number of White pieces that can move to the red marked target cell.
Example JSON:
{"annotation":[[420,210],[502,244],[536,328]],"answer":3}
```

### task_games__circular_chess__target_cell_reacher_count / white_piece_reaches_target_count / answer_only / sample 179360609203867

- `instance_seed`: `179360609203867`
- `word_count`: `134`
- `body_word_count`: `110`

```text
The figure shows a circular chess board with four rings, sixteen sectors per ring, and many white and black chess pieces. How many White pieces could legally move onto the red marked target cell? Sectors wrap around each ring; rings do not wrap inward or outward. Use standard chess movement on this circular board. Rooks move around rings or across rings, bishops move diagonally between rings and sectors, queens combine rook and bishop movement, knights jump, and kings move one step. A piece may land on an empty cell or an opponent piece, but not on a friendly piece. Sliding pieces stop at the first occupied cell in a direction.
Final answer format: set "answer" to the number of White pieces that can move to the red marked target cell.
Example JSON:
{"answer":3}
```

### task_games__connect_four__column_disc_profile_label / single / answer_and_annotation / sample 323534151492722

- `instance_seed`: `323534151492722`
- `word_count`: `81`
- `body_word_count`: `33`

```text
You are shown a Connect Four board in a midgame position with red and yellow discs. Read the labels under the columns. Which labeled column has red-disc count 3 and yellow-disc count 1?
Annotation format: set "annotation" to a JSON array of pixel-space cell boxes [x0, y0, x1, y1] for the occupied cells in the selected column.
Answer format: set "answer" to the selected column label as a capital letter shown below the board.
Example JSON:
{"annotation":[[155,215]],"answer":"C"}
```

### task_games__connect_four__column_disc_profile_label / single / answer_only / sample 323534151492722

- `instance_seed`: `323534151492722`
- `word_count`: `54`
- `body_word_count`: `33`

```text
You are shown a Connect Four board in a midgame position with red and yellow discs. Read the labels under the columns. Which labeled column has red-disc count 3 and yellow-disc count 1?
Answer format: set "answer" to the selected column label as a capital letter shown below the board.
Example JSON:
{"answer":"C"}
```

### task_games__connect_four__winning_move_column_label / single / answer_and_annotation / sample 6762374181650789

- `instance_seed`: `6762374181650789`
- `word_count`: `107`
- `body_word_count`: `60`

```text
The scene contains a Connect Four board in a crowded late-game position with red and yellow discs. It is Yellow's turn. Use the column labels shown below the board. A legal drop chooses one non-full column and lands in its lowest empty square. A horizontal, vertical, or diagonal line of four matching discs wins. Which column lets Yellow win immediately?
Required annotation format: set "annotation" to one point [x, y] at the center of the landing square in the selected winning column.
Required answer format: set "answer" to the selected column label as a capital letter shown below the board.
Example JSON:
{"annotation":[155,215],"answer":"C"}
```

### task_games__connect_four__winning_move_column_label / single / answer_only / sample 6762374181650789

- `instance_seed`: `6762374181650789`
- `word_count`: `81`
- `body_word_count`: `60`

```text
The scene contains a Connect Four board in a crowded late-game position with red and yellow discs. It is Yellow's turn. Use the column labels shown below the board. A legal drop chooses one non-full column and lands in its lowest empty square. A horizontal, vertical, or diagonal line of four matching discs wins. Which column lets Yellow win immediately?
Answer format: set "answer" to the selected column label as a capital letter shown below the board.
Example JSON:
{"answer":"C"}
```

### task_games__connect_four__winning_move_count / single / answer_and_annotation / sample 2718176578363693

- `instance_seed`: `2718176578363693`
- `word_count`: `99`
- `body_word_count`: `57`

```text
The visual shows a Connect Four board in a crowded late-game position with red and yellow discs. It is Yellow's turn. A legal drop chooses one non-full column and lands in its lowest empty square. A horizontal, vertical, or diagonal line of four matching discs wins. How many columns give Yellow an immediate win on this move?
Annotation format: set "annotation" to a JSON array of pixel-space cell boxes [x0, y0, x1, y1] for every immediate-winning landing square.
Answer format: set "answer" to the number of legal drop columns that win immediately.
Example JSON:
{"annotation":[[155,215]],"answer":3}
```

### task_games__connect_four__winning_move_count / single / answer_only / sample 2718176578363693

- `instance_seed`: `2718176578363693`
- `word_count`: `78`
- `body_word_count`: `57`

```text
The visual shows a Connect Four board in a crowded late-game position with red and yellow discs. It is Yellow's turn. A legal drop chooses one non-full column and lands in its lowest empty square. A horizontal, vertical, or diagonal line of four matching discs wins. How many columns give Yellow an immediate win on this move?
Format for the "answer" field: set "answer" to the number of legal drop columns that win immediately.
Example JSON:
{"answer":3}
```

### task_games__crossing__first_exit_object_label / single / answer_and_annotation / sample 4605779918798983

- `instance_seed`: `4605779918798983`
- `word_count`: `112`
- `body_word_count`: `55`

```text
The scene shows a lane-crossing game board with moving objects and direction arrows. At each tick, every moving object shifts one lane cell in its arrow direction. A moving object exits when it moves past the left or right edge. Identify the labeled moving object that reaches an outer edge before the other labeled objects.
Final answer format: set "answer" to the visible label of the moving object that leaves the board first; the value is one of A, B, C, or D.
Annotation format: set "annotation" to one point [x, y] at the center of the labeled moving object that leaves the board first.
Example JSON:
{"annotation":[463,363],"answer":"C"}
```

### task_games__crossing__first_exit_object_label / single / answer_only / sample 4605779918798983

- `instance_seed`: `4605779918798983`
- `word_count`: `89`
- `body_word_count`: `55`

```text
The scene shows a lane-crossing game board with moving objects and direction arrows. At each tick, every moving object shifts one lane cell in its arrow direction. A moving object exits when it moves past the left or right edge. Identify the labeled moving object that reaches an outer edge before the other labeled objects.
Format for the "answer" field: set "answer" to the visible label of the moving object that leaves the board first; the value is one of A, B, C, or D.
Example JSON:
{"answer":"C"}
```

### task_games__crossing__hit_object_label / single / answer_and_annotation / sample 1453239204912451

- `instance_seed`: `1453239204912451`
- `word_count`: `135`
- `body_word_count`: `79`

```text
The visual shows a lane-crossing game board with moving objects, direction arrows, start pads, and one marked route line. At tick 1, the runner enters the bottom traffic row; at each next tick, the runner moves one row upward. Each moving object shifts one lane cell per tick in its arrow direction. Objects that reach an edge leave the board. Identify the labeled moving object that reaches the same lane cell as the yellow route at the matching tick.
Annotation format: set "annotation" to one point [x, y] at the center of the labeled moving object that hits the marked route.
Answer format: set "answer" to the visible label of the moving object that hits the marked route; the value is one of A, B, C, or D.
Example JSON:
{"annotation":[463,363],"answer":"C"}
```

### task_games__crossing__hit_object_label / single / answer_only / sample 1453239204912451

- `instance_seed`: `1453239204912451`
- `word_count`: `113`
- `body_word_count`: `79`

```text
The visual shows a lane-crossing game board with moving objects, direction arrows, start pads, and one marked route line. At tick 1, the runner enters the bottom traffic row; at each next tick, the runner moves one row upward. Each moving object shifts one lane cell per tick in its arrow direction. Objects that reach an edge leave the board. Identify the labeled moving object that reaches the same lane cell as the yellow route at the matching tick.
Format for the "answer" field: set "answer" to the visible label of the moving object that hits the marked route; the value is one of A, B, C, or D.
Example JSON:
{"answer":"C"}
```

### task_games__crossing__moving_object_direction_count / left_moving_object_count / answer_and_annotation / sample 7205177858096334

- `instance_seed`: `7205177858096334`
- `word_count`: `77`
- `body_word_count`: `22`

```text
The figure shows a lane-crossing game board with moving objects and direction arrows. What is the number of moving objects moving left?
Annotation format: set "annotation" to a JSON array of pixel-space object boxes [x0, y0, x1, y1], one for every moving object whose arrow points left.
Answer format: set "answer" to the number of moving objects whose arrow points left; the value is between 1 and 6.
Example JSON:
{"annotation":[[224,306],[554,428]],"answer":2}
```

### task_games__crossing__moving_object_direction_count / left_moving_object_count / answer_only / sample 7205177858096334

- `instance_seed`: `7205177858096334`
- `word_count`: `48`
- `body_word_count`: `22`

```text
The figure shows a lane-crossing game board with moving objects and direction arrows. What is the number of moving objects moving left?
Required answer format: set "answer" to the number of moving objects whose arrow points left; the value is between 1 and 6.
Example JSON:
{"answer":2}
```

### task_games__crossing__moving_object_direction_count / right_moving_object_count / answer_and_annotation / sample 1063417339328134

- `instance_seed`: `1063417339328134`
- `word_count`: `79`
- `body_word_count`: `22`

```text
The visual shows a lane-crossing game board with moving objects and direction arrows. What is the number of moving objects moving right?
Required annotation format: set "annotation" to a JSON array of pixel-space object boxes [x0, y0, x1, y1], one for every moving object whose arrow points right.
Required answer format: set "answer" to the number of moving objects whose arrow points right; the value is between 1 and 6.
Example JSON:
{"annotation":[[224,306],[554,428]],"answer":2}
```

### task_games__crossing__moving_object_direction_count / right_moving_object_count / answer_only / sample 1063417339328134

- `instance_seed`: `1063417339328134`
- `word_count`: `48`
- `body_word_count`: `22`

```text
The visual shows a lane-crossing game board with moving objects and direction arrows. What is the number of moving objects moving right?
Required answer format: set "answer" to the number of moving objects whose arrow points right; the value is between 1 and 6.
Example JSON:
{"answer":2}
```

### task_games__darts__bullseye_membership_count / inside_bullseye_count / answer_and_annotation / sample 4266655091740059

- `instance_seed`: `4266655091740059`
- `word_count`: `62`
- `body_word_count`: `19`

```text
The image shows a simplified labeled dartboard with visible dart markers. Find the count of darts in the bullseye.
Annotation format: set "annotation" to a JSON array of pixel-space dart boxes [x0, y0, x1, y1] for every dart inside the bullseye.
Answer format: set "answer" to the number of darts inside the bullseye.
Example JSON:
{"annotation":[[411,219],[525,364]],"answer":2}
```

### task_games__darts__bullseye_membership_count / inside_bullseye_count / answer_only / sample 4266655091740059

- `instance_seed`: `4266655091740059`
- `word_count`: `35`
- `body_word_count`: `31`

```text
The image shows a simplified labeled dartboard with visible dart markers. Find the count of darts in the bullseye.
Answer field: set "answer" to the number of darts inside the bullseye.
Example JSON:
{"answer":2}
```

### task_games__darts__bullseye_membership_count / outside_bullseye_count / answer_and_annotation / sample 5970187456310819

- `instance_seed`: `5970187456310819`
- `word_count`: `66`
- `body_word_count`: `21`

```text
The visual shows a simplified labeled dartboard with visible dart markers. Count the darts that did not land in the bullseye.
Required annotation format: set "annotation" to a JSON array of pixel-space dart boxes [x0, y0, x1, y1] for every dart outside the bullseye.
Required answer format: set "answer" to the number of darts outside the bullseye.
Example JSON:
{"annotation":[[411,219],[525,364]],"answer":2}
```

### task_games__darts__bullseye_membership_count / outside_bullseye_count / answer_only / sample 5970187456310819

- `instance_seed`: `5970187456310819`
- `word_count`: `37`
- `body_word_count`: `21`

```text
The visual shows a simplified labeled dartboard with visible dart markers. Count the darts that did not land in the bullseye.
Answer format: set "answer" to the number of darts outside the bullseye.
Example JSON:
{"answer":2}
```

### task_games__darts__dart_score_value / single / answer_and_annotation / sample 5487596683737279

- `instance_seed`: `5487596683737279`
- `word_count`: `73`
- `body_word_count`: `39`

```text
This scene shows a simplified labeled dartboard with visible dart markers. Using the simplified dartboard scoring rule, what is the dart's score? A dart in a numbered sector scores that number; a dart in the center bullseye scores 50.
Annotation format: set "annotation" to one pixel point [x, y] at the center of the dart.
Answer format: set "answer" to the integer score of the dart.
Example JSON:
{"annotation":[411,219],"answer":17}
```

### task_games__darts__dart_score_value / single / answer_only / sample 5487596683737279

- `instance_seed`: `5487596683737279`
- `word_count`: `54`
- `body_word_count`: `39`

```text
This scene shows a simplified labeled dartboard with visible dart markers. Using the simplified dartboard scoring rule, what is the dart's score? A dart in a numbered sector scores that number; a dart in the center bullseye scores 50.
Answer format: set "answer" to the integer score of the dart.
Example JSON:
{"answer":17}
```

### task_games__dominoes__double_count / single / answer_and_annotation / sample 2247839516483497

- `instance_seed`: `2247839516483497`
- `word_count`: `76`
- `body_word_count`: `28`

```text
The visual shows one row of face-up dominoes. Looking at the visible dominoes, how many are doubles? A double has the same number of pips on both halves.
Required annotation format: set "annotation" to a JSON array of bounding boxes [x0, y0, x1, y1] for every shown domino that is a double.
Required answer format: set "answer" to the count of shown doubles.
Example JSON:
{"annotation":[[248,318,386,394],[408,318,546,394]],"answer":2}
```

### task_games__dominoes__double_count / single / answer_only / sample 2247839516483497

- `instance_seed`: `2247839516483497`
- `word_count`: `42`
- `body_word_count`: `28`

```text
The visual shows one row of face-up dominoes. Looking at the visible dominoes, how many are doubles? A double has the same number of pips on both halves.
Answer format: set "answer" to the count of shown doubles.
Example JSON:
{"answer":2}
```

### task_games__dominoes__higher_sum_than_reference_count / single / answer_and_annotation / sample 4612807418500257

- `instance_seed`: `4612807418500257`
- `word_count`: `108`
- `body_word_count`: `46`

```text
The visual shows two rows of face-up dominoes with one tile marked `REF`. Using the tile marked `REF` as the reference, how many other face-up dominoes have a higher total? The pip sum of a domino is the total number of pips across its two halves.
Required annotation format: set "annotation" to a JSON array of bounding boxes [x0, y0, x1, y1] for every non-reference domino with a larger pip sum than `REF`.
Required answer format: set "answer" to the count of loose dominoes with a larger pip sum than `REF`.
Example JSON:
{"annotation":[[248,318,386,394],[408,318,546,394],[568,318,706,394]],"answer":3}
```

### task_games__dominoes__higher_sum_than_reference_count / single / answer_only / sample 4612807418500257

- `instance_seed`: `4612807418500257`
- `word_count`: `67`
- `body_word_count`: `63`

```text
The visual shows two rows of face-up dominoes with one tile marked `REF`. Using the tile marked `REF` as the reference, how many other face-up dominoes have a higher total? The pip sum of a domino is the total number of pips across its two halves.
Answer field: set "answer" to the count of loose dominoes with a larger pip sum than `REF`.
Example JSON:
{"answer":3}
```

### task_games__dominoes__invalid_join_label / single / answer_and_annotation / sample 2287120420555829

- `instance_seed`: `2287120420555829`
- `word_count`: `104`
- `body_word_count`: `43`

```text
This layout shows one face-up domino chain with six labeled joins. Look at the six labeled joins in the chain. A valid domino chain has matching pip numbers on the two halves that touch at each join. Which label marks the broken join?
Annotation format: set "annotation" to one segment using two pixel-point endpoints [x, y] in [[x0, y0], [x1, y1]] form, at the centers of the two touching domino halves at the invalid join.
Answer format: set "answer" to the label of the invalid join, one of `A`, `B`, `C`, `D`, `E`, or `F`.
Example JSON:
{"annotation":[[312,142],[326,142]],"answer":"C"}
```

### task_games__dominoes__invalid_join_label / single / answer_only / sample 2287120420555829

- `instance_seed`: `2287120420555829`
- `word_count`: `68`
- `body_word_count`: `43`

```text
This layout shows one face-up domino chain with six labeled joins. Look at the six labeled joins in the chain. A valid domino chain has matching pip numbers on the two halves that touch at each join. Which label marks the broken join?
Final answer format: set "answer" to the label of the invalid join, one of `A`, `B`, `C`, `D`, `E`, or `F`.
Example JSON:
{"answer":"C"}
```

### task_games__dominoes__longest_chain_length_value / single / answer_and_annotation / sample 213458943073416

- `instance_seed`: `213458943073416`
- `word_count`: `123`
- `body_word_count`: `62`

```text
The figure shows a short face-up domino chain across the top with two rows of face-up candidate dominoes below. Each loose domino may be used at most once. A domino can be added when either half matches the current open end. Do not count `REF`. Beginning at `REF`'s open right end, what is the longest chain length using the loose dominoes?
Final answer format: set "answer" to the maximum number of loose dominoes that can be added after `REF`.
Annotation format: set "annotation" to a JSON array of bounding boxes [x0, y0, x1, y1] for the loose dominoes in the unique longest chain from `REF`.
Example JSON:
{"annotation":[[248,318,386,394],[408,318,546,394],[568,318,706,394]],"answer":3}
```

### task_games__dominoes__longest_chain_length_value / single / answer_only / sample 213458943073416

- `instance_seed`: `213458943073416`
- `word_count`: `83`
- `body_word_count`: `79`

```text
The figure shows a short face-up domino chain across the top with two rows of face-up candidate dominoes below. Each loose domino may be used at most once. A domino can be added when either half matches the current open end. Do not count `REF`. Beginning at `REF`'s open right end, what is the longest chain length using the loose dominoes?
Answer field: set "answer" to the maximum number of loose dominoes that can be added after `REF`.
Example JSON:
{"answer":3}
```

### task_games__dominoes__matching_end_count / single / answer_and_annotation / sample 5023975697233483

- `instance_seed`: `5023975697233483`
- `word_count`: `118`
- `body_word_count`: `60`

```text
This layout shows a short face-up domino chain across the top with one row of face-up candidate dominoes below. The chain's last tile is marked `REF`. A loose domino can connect to the open right end if either half has the same number of pips as that open end. How many loose dominoes shown below match that open right end?
Annotation format: set "annotation" to a JSON array of bounding boxes [x0, y0, x1, y1] for every loose domino that matches the `REF` tile's open right end.
Answer format: set "answer" to the count of loose dominoes that match the `REF` tile's open right end.
Example JSON:
{"annotation":[[248,318,386,394],[408,318,546,394]],"answer":2}
```

### task_games__dominoes__matching_end_count / single / answer_only / sample 5023975697233483

- `instance_seed`: `5023975697233483`
- `word_count`: `85`
- `body_word_count`: `60`

```text
This layout shows a short face-up domino chain across the top with one row of face-up candidate dominoes below. The chain's last tile is marked `REF`. A loose domino can connect to the open right end if either half has the same number of pips as that open end. How many loose dominoes shown below match that open right end?
Format for the "answer" field: set "answer" to the count of loose dominoes that match the `REF` tile's open right end.
Example JSON:
{"answer":2}
```

### task_games__dominoes__sum_to_target_count / single / answer_and_annotation / sample 6332153921277468

- `instance_seed`: `6332153921277468`
- `word_count`: `93`
- `body_word_count`: `36`

```text
The layout shows one row of face-up dominoes. Looking only at the shown dominoes, The pip sum of a domino is the total number of pips across its two halves. how many have pip sum 6?
Final answer format: set "answer" to the count of shown dominoes with the target pip sum.
Annotation format: set "annotation" to a JSON array of bounding boxes [x0, y0, x1, y1] for every shown domino with the target pip sum.
Example JSON:
{"annotation":[[248,318,386,394],[408,318,546,394],[568,318,706,394]],"answer":3}
```

### task_games__dominoes__sum_to_target_count / single / answer_only / sample 6332153921277468

- `instance_seed`: `6332153921277468`
- `word_count`: `56`
- `body_word_count`: `36`

```text
The layout shows one row of face-up dominoes. Looking only at the shown dominoes, The pip sum of a domino is the total number of pips across its two halves. how many have pip sum 6?
Required answer format: set "answer" to the count of shown dominoes with the target pip sum.
Example JSON:
{"answer":3}
```

### task_games__dots_and_boxes__completable_box_label / single / answer_and_annotation / sample 1230120631941245

- `instance_seed`: `1230120631941245`
- `word_count`: `62`
- `body_word_count`: `18`

```text
The visual shows a dots-and-boxes grid with some edges already drawn. Which labeled cell can be completed next?
Annotation format: set "annotation" to the full-cell bounding box [x0, y0, x1, y1] of the selected labeled box.
Answer format: set "answer" to the option letter, one of A, B, C, D, E, or F.
Example JSON:
{"annotation":[180,220,300,340],"answer":"F"}
```

### task_games__dots_and_boxes__completable_box_label / single / answer_only / sample 1230120631941245

- `instance_seed`: `1230120631941245`
- `word_count`: `40`
- `body_word_count`: `18`

```text
The visual shows a dots-and-boxes grid with some edges already drawn. Which labeled cell can be completed next?
Required answer format: set "answer" to the option letter, one of A, B, C, D, E, or F.
Example JSON:
{"answer":"F"}
```

### task_games__dots_and_boxes__owned_box_count / single / answer_and_annotation / sample 6061600071196157

- `instance_seed`: `6061600071196157`
- `word_count`: `68`
- `body_word_count`: `19`

```text
The image shows a dots-and-boxes grid with some edges already drawn. Find the number of box cells marked A.
Annotation format: set "annotation" to a JSON array of full-cell bounding boxes [x0, y0, x1, y1] for every box marked with player A.
Answer format: set "answer" to the number of boxes marked with player A.
Example JSON:
{"annotation":[[180,220,300,340],[310,220,430,340]],"answer":8}
```

### task_games__dots_and_boxes__owned_box_count / single / answer_only / sample 6061600071196157

- `instance_seed`: `6061600071196157`
- `word_count`: `37`
- `body_word_count`: `19`

```text
The image shows a dots-and-boxes grid with some edges already drawn. Find the number of box cells marked A.
Required answer format: set "answer" to the number of boxes marked with player A.
Example JSON:
{"answer":8}
```

### task_games__dots_and_boxes__three_sided_box_count / single / answer_and_annotation / sample 186981617374056

- `instance_seed`: `186981617374056`
- `word_count`: `73`
- `body_word_count`: `22`

```text
The scene shows a dots-and-boxes grid with some edges already drawn. Find the number of boxes with exactly three visible sides drawn.
Annotation format: set "annotation" to a JSON array of full-cell bounding boxes [x0, y0, x1, y1] for every box with exactly three drawn sides.
Answer format: set "answer" to the number of boxes with exactly three drawn sides.
Example JSON:
{"annotation":[[180,220,300,340],[310,220,430,340]],"answer":2}
```

### task_games__dots_and_boxes__three_sided_box_count / single / answer_only / sample 186981617374056

- `instance_seed`: `186981617374056`
- `word_count`: `40`
- `body_word_count`: `22`

```text
The scene shows a dots-and-boxes grid with some edges already drawn. Find the number of boxes with exactly three visible sides drawn.
Answer format: set "answer" to the number of boxes with exactly three drawn sides.
Example JSON:
{"answer":2}
```

### task_games__go__group_adjacent_enemy_count / single / answer_and_annotation / sample 2300596088029025

- `instance_seed`: `2300596088029025`
- `word_count`: `123`
- `body_word_count`: `60`

```text
The scene shows a Go board with many surrounding black and white stones. The red outlined black stones are the marked group. Same-color stones connected edge to edge form one group. Count only opponent stones touching the marked group edge to edge; diagonals do not count. What is the number of opponent stones directly adjacent to the marked black group?
Required annotation format: set "annotation" to a JSON array of pixel-space stone boxes [x0, y0, x1, y1] for every opponent stone directly adjacent to the marked black group.
Required answer format: set "answer" to the number of opponent stones directly adjacent to the marked black group.
Example JSON:
{"annotation":[[258,198,302,242],[331,198,375,242],[404,271,448,315]],"answer":3}
```

### task_games__go__group_adjacent_enemy_count / single / answer_only / sample 2300596088029025

- `instance_seed`: `2300596088029025`
- `word_count`: `81`
- `body_word_count`: `60`

```text
The scene shows a Go board with many surrounding black and white stones. The red outlined black stones are the marked group. Same-color stones connected edge to edge form one group. Count only opponent stones touching the marked group edge to edge; diagonals do not count. What is the number of opponent stones directly adjacent to the marked black group?
Answer format: set "answer" to the number of opponent stones directly adjacent to the marked black group.
Example JSON:
{"answer":3}
```

### task_games__go__group_liberty_count / marked_group_liberty_count / answer_and_annotation / sample 3171365816528742

- `instance_seed`: `3171365816528742`
- `word_count`: `103`
- `body_word_count`: `54`

```text
The visual shows a Go board with many surrounding black and white stones. The red outlined black stones are the marked group. Same-color stones connected edge to edge form one group. A liberty is an empty orthogonal neighbor of the group; diagonals do not count. Determine the liberty count of the marked black group.
Final answer format: set "answer" to the number of liberties of the marked black group.
Annotation format: set "annotation" to a JSON array of pixel-space points [x, y] at every liberty of the marked black group.
Example JSON:
{"annotation":[[343,315],[417,389],[491,389],[565,463]],"answer":4}
```

### task_games__go__group_liberty_count / marked_group_liberty_count / answer_only / sample 3171365816528742

- `instance_seed`: `3171365816528742`
- `word_count`: `72`
- `body_word_count`: `54`

```text
The visual shows a Go board with many surrounding black and white stones. The red outlined black stones are the marked group. Same-color stones connected edge to edge form one group. A liberty is an empty orthogonal neighbor of the group; diagonals do not count. Determine the liberty count of the marked black group.
Answer format: set "answer" to the number of liberties of the marked black group.
Example JSON:
{"answer":4}
```

### task_games__go__group_liberty_count / marked_group_shared_liberty_count / answer_and_annotation / sample 3345544386860084

- `instance_seed`: `3345544386860084`
- `word_count`: `126`
- `body_word_count`: `75`

```text
The visual shows a Go board with black and white stones and many open intersections. The red outlined black stones are the marked group. Same-color stones connected edge to edge form one group. A liberty is an empty orthogonal neighbor of the group; diagonals do not count. A shared liberty also touches at least one opponent stone edge to edge. How many empty neighboring intersections of the marked black group also touch an enemy stone?
Final answer format: set "answer" to the number of shared liberties of the marked black group.
Annotation format: set "annotation" to a JSON array of pixel-space points [x, y] at every shared liberty of the marked black group.
Example JSON:
{"annotation":[[343,315],[417,389],[491,389],[565,463]],"answer":4}
```

### task_games__go__group_liberty_count / marked_group_shared_liberty_count / answer_only / sample 3345544386860084

- `instance_seed`: `3345544386860084`
- `word_count`: `95`
- `body_word_count`: `75`

```text
The visual shows a Go board with black and white stones and many open intersections. The red outlined black stones are the marked group. Same-color stones connected edge to edge form one group. A liberty is an empty orthogonal neighbor of the group; diagonals do not count. A shared liberty also touches at least one opponent stone edge to edge. How many empty neighboring intersections of the marked black group also touch an enemy stone?
Final answer format: set "answer" to the number of shared liberties of the marked black group.
Example JSON:
{"answer":4}
```

### task_games__go__marked_group_stone_count / single / answer_and_annotation / sample 2926796833469359

- `instance_seed`: `2926796833469359`
- `word_count`: `112`
- `body_word_count`: `45`

```text
The scene shows a Go board with many surrounding black and white stones. The red outlined black stone marks the group to inspect. Same-color stones connected edge to edge form one group. What is the size of the connected group containing the marked black stone?
Annotation format: set "annotation" to a JSON array of pixel-space stone boxes [x0, y0, x1, y1] for every stone in the connected group containing the marked black stone.
Answer format: set "answer" to the number of stones in the connected group containing the marked black stone.
Example JSON:
{"annotation":[[258,198,302,242],[331,198,375,242],[331,271,375,315],[404,271,448,315]],"answer":4}
```

### task_games__go__marked_group_stone_count / single / answer_only / sample 2926796833469359

- `instance_seed`: `2926796833469359`
- `word_count`: `68`
- `body_word_count`: `45`

```text
The scene shows a Go board with many surrounding black and white stones. The red outlined black stone marks the group to inspect. Same-color stones connected edge to edge form one group. What is the size of the connected group containing the marked black stone?
Required answer format: set "answer" to the number of stones in the connected group containing the marked black stone.
Example JSON:
{"answer":4}
```

### task_games__hex__candidate_neighbor_count / single / answer_and_annotation / sample 1928691864614956

- `instance_seed`: `1928691864614956`
- `word_count`: `96`
- `body_word_count`: `38`

```text
The figure shows a Hex board with red and blue stones, colored goal sides, and open cells. In Hex, adjacent cells are the six cells sharing an edge. How many cells adjacent to the green cell are empty?
Annotation format: set "annotation" to a JSON array of pixel-space points [x, y] at the centers of empty neighboring cells adjacent to the green reference cell; use [] if none match.
Answer format: set "answer" to the number of empty neighboring cells adjacent to the green reference cell.
Example JSON:
{"annotation":[[150,220],[210,250],[270,280]],"answer":3}
```

### task_games__hex__candidate_neighbor_count / single / answer_only / sample 1928691864614956

- `instance_seed`: `1928691864614956`
- `word_count`: `60`
- `body_word_count`: `38`

```text
The figure shows a Hex board with red and blue stones, colored goal sides, and open cells. In Hex, adjacent cells are the six cells sharing an edge. How many cells adjacent to the green cell are empty?
Required answer format: set "answer" to the number of empty neighboring cells adjacent to the green reference cell.
Example JSON:
{"answer":3}
```

### task_games__hex__connection_gap_count / single / answer_and_annotation / sample 1797963840849540

- `instance_seed`: `1797963840849540`
- `word_count`: `122`
- `body_word_count`: `62`

```text
The image shows a Hex board with red and blue stones, colored goal sides, and a crowded mix of open cells and stones. In Hex, adjacent cells are the six cells sharing an edge. Red connects the left and right red sides. Blue connects the top and bottom blue sides. Find the smallest number of empty cells that would complete Red's connection.
Required annotation format: set "annotation" to a JSON array of pixel-space points [x, y] at the centers of the empty cells in the unique minimum connection gap for Red.
Required answer format: set "answer" to the minimum number of empty cells Red must fill to connect the required sides.
Example JSON:
{"annotation":[[150,220],[210,250],[270,280]],"answer":3}
```

### task_games__hex__connection_gap_count / single / answer_only / sample 1797963840849540

- `instance_seed`: `1797963840849540`
- `word_count`: `85`
- `body_word_count`: `62`

```text
The image shows a Hex board with red and blue stones, colored goal sides, and a crowded mix of open cells and stones. In Hex, adjacent cells are the six cells sharing an edge. Red connects the left and right red sides. Blue connects the top and bottom blue sides. Find the smallest number of empty cells that would complete Red's connection.
Answer format: set "answer" to the minimum number of empty cells Red must fill to connect the required sides.
Example JSON:
{"answer":3}
```

### task_games__hex__winning_move_cell_label / single / answer_and_annotation / sample 5976219003145949

- `instance_seed`: `5976219003145949`
- `word_count`: `99`
- `body_word_count`: `56`

```text
The visual shows a Hex board with red and blue stones, colored goal sides, and open cells. In Hex, adjacent cells are the six cells sharing an edge. Red connects the left and right red sides. Blue connects the top and bottom blue sides. Which candidate cell gives Blue a connected path between the required sides?
Annotation format: set "annotation" to one pixel-space point [x, y] at the center of the chosen winning cell.
Answer format: set "answer" to the single candidate letter of the empty cell that lets Blue win immediately.
Example JSON:
{"annotation":[210,250],"answer":"C"}
```

### task_games__hex__winning_move_cell_label / single / answer_only / sample 5976219003145949

- `instance_seed`: `5976219003145949`
- `word_count`: `78`
- `body_word_count`: `56`

```text
The visual shows a Hex board with red and blue stones, colored goal sides, and open cells. In Hex, adjacent cells are the six cells sharing an edge. Red connects the left and right red sides. Blue connects the top and bottom blue sides. Which candidate cell gives Blue a connected path between the required sides?
Answer format: set "answer" to the single candidate letter of the empty cell that lets Blue win immediately.
Example JSON:
{"answer":"C"}
```

### task_games__irregular_link_board__capture_move_count / single / answer_and_annotation / sample 3549793975558685

- `instance_seed`: `3549793975558685`
- `word_count`: `113`
- `body_word_count`: `52`

```text
The scene shows a point-and-link movement board with many missing links and several pieces. A capture move jumps over one adjacent opposing piece along a straight drawn line and lands on the empty point immediately beyond it. How many empty linked landing points can the X-marked piece reach by a capture jump?
Final answer format: set "answer" to the number of legal capture moves for the X-marked piece.
Annotation format: set "annotation" to [x, y] pixel points at the centers of every empty point where the X-marked piece can move to capture; use an empty array if there are none.
Example JSON:
{"annotation":[[180.0,220.0],[268.0,220.0]],"answer":2}
```

### task_games__irregular_link_board__capture_move_count / single / answer_only / sample 3549793975558685

- `instance_seed`: `3549793975558685`
- `word_count`: `72`
- `body_word_count`: `52`

```text
The scene shows a point-and-link movement board with many missing links and several pieces. A capture move jumps over one adjacent opposing piece along a straight drawn line and lands on the empty point immediately beyond it. How many empty linked landing points can the X-marked piece reach by a capture jump?
Required answer format: set "answer" to the number of legal capture moves for the X-marked piece.
Example JSON:
{"answer":2}
```

### task_games__irregular_link_board__marked_piece_destination_count / single / answer_and_annotation / sample 3891994840102763

- `instance_seed`: `3891994840102763`
- `word_count`: `98`
- `body_word_count`: `39`

```text
The image shows a point-and-link movement board with many missing links and several pieces. A piece can move one step only along a drawn link to an adjacent empty point. Count the legal empty destinations for the X-marked piece.
Final answer format: set "answer" to the number of legal destinations for the X-marked piece.
Annotation format: set "annotation" to [x, y] pixel points at the centers of every empty point the X-marked piece can legally move to; use an empty array if there are none.
Example JSON:
{"annotation":[[180.0,220.0],[268.0,220.0]],"answer":2}
```

### task_games__irregular_link_board__marked_piece_destination_count / single / answer_only / sample 3891994840102763

- `instance_seed`: `3891994840102763`
- `word_count`: `58`
- `body_word_count`: `39`

```text
The image shows a point-and-link movement board with many missing links and several pieces. A piece can move one step only along a drawn link to an adjacent empty point. Count the legal empty destinations for the X-marked piece.
Final answer format: set "answer" to the number of legal destinations for the X-marked piece.
Example JSON:
{"answer":2}
```

### task_games__lane_runner__path_coin_count / single / answer_and_annotation / sample 5691141334671037

- `instance_seed`: `5691141334671037`
- `word_count`: `104`
- `body_word_count`: `61`

```text
The image shows a two-lane runner track with a start marker, a finish band, visible coins in lane cells, and one shown path. Follow the shown path from start to finish. Each step moves one row toward the finish; the path may stay in the same lane or switch diagonally to the other lane. How many coins does the runner collect?
Annotation format: set "annotation" to [x, y] pixel points at the centers of every coin collected by the shown path.
Answer format: set "answer" to the number of coins collected by the shown path.
Example JSON:
{"annotation":[[176,412],[176,240]],"answer":2}
```

### task_games__lane_runner__path_coin_count / single / answer_only / sample 5691141334671037

- `instance_seed`: `5691141334671037`
- `word_count`: `79`
- `body_word_count`: `61`

```text
The image shows a two-lane runner track with a start marker, a finish band, visible coins in lane cells, and one shown path. Follow the shown path from start to finish. Each step moves one row toward the finish; the path may stay in the same lane or switch diagonally to the other lane. How many coins does the runner collect?
Answer format: set "answer" to the number of coins collected by the shown path.
Example JSON:
{"answer":2}
```

### task_games__lane_runner__safe_path_label / single / answer_and_annotation / sample 2345015311561397

- `instance_seed`: `2345015311561397`
- `word_count`: `86`
- `body_word_count`: `46`

```text
The image shows labeled candidate path cards, each showing a two-lane track with hazard cells and one candidate path. Each path moves one row toward the finish. A safe path never enters a hazard cell. Find the labeled route that stays clear of every hazard cell.
Final answer format: set "answer" to the selected path label as a capital letter.
Annotation format: set "annotation" to one bounding box [x0,y0,x1,y1] around the selected path card.
Example JSON:
{"annotation":[[314,128,392,310]],"answer":"C"}
```

### task_games__lane_runner__safe_path_label / single / answer_only / sample 2345015311561397

- `instance_seed`: `2345015311561397`
- `word_count`: `64`
- `body_word_count`: `46`

```text
The image shows labeled candidate path cards, each showing a two-lane track with hazard cells and one candidate path. Each path moves one row toward the finish. A safe path never enters a hazard cell. Find the labeled route that stays clear of every hazard cell.
Final answer format: set "answer" to the selected path label as a capital letter.
Example JSON:
{"answer":"C"}
```

### task_games__ludo_board__capture_roll_option_label / single / answer_and_annotation / sample 2229181273877924

- `instance_seed`: `2229181273877924`
- `word_count`: `97`
- `body_word_count`: `54`

```text
The board shows a Ludo-style cross board with one visible token for each player color and twelve two-cell arrows showing the clockwise track direction. Move clockwise along the track. A "6 then k" option means move 6 spaces, then k more spaces. Which roll option lets the blue token land on the yellow token?
Annotation format: set "annotation" to an object with keys "mover_token" and "target_token", each mapped to a point as [x,y] in pixels.
Answer format: set "answer" to the selected shown option letter.
Example JSON:
{"annotation":{"mover_token":[115,215],"target_token":[275,215]},"answer":"C"}
```

### task_games__ludo_board__capture_roll_option_label / single / answer_only / sample 2229181273877924

- `instance_seed`: `2229181273877924`
- `word_count`: `69`
- `body_word_count`: `54`

```text
The board shows a Ludo-style cross board with one visible token for each player color and twelve two-cell arrows showing the clockwise track direction. Move clockwise along the track. A "6 then k" option means move 6 spaces, then k more spaces. Which roll option lets the blue token land on the yellow token?
Required answer format: set "answer" to the selected shown option letter.
Example JSON:
{"answer":"C"}
```

### task_games__ludo_board__move_result_option_label / single / answer_and_annotation / sample 2616582892462626

- `instance_seed`: `2616582892462626`
- `word_count`: `95`
- `body_word_count`: `52`

```text
The scene shows a Ludo-style cross board with one visible token for each player color and twelve two-cell arrows showing the clockwise track direction. Use the dice sequence shown below the board and move clockwise along the track. After applying the shown sequence to the yellow token, which board letter is reached?
Annotation format: set "annotation" to an object with keys "moving_token" and "destination_cell", each mapped to a point as [x,y] in pixels.
Answer format: set "answer" to the selected shown destination label.
Example JSON:
{"annotation":{"moving_token":[115,215],"destination_cell":[342,282]},"answer":"D"}
```

### task_games__ludo_board__move_result_option_label / single / answer_only / sample 2616582892462626

- `instance_seed`: `2616582892462626`
- `word_count`: `67`
- `body_word_count`: `52`

```text
The scene shows a Ludo-style cross board with one visible token for each player color and twelve two-cell arrows showing the clockwise track direction. Use the dice sequence shown below the board and move clockwise along the track. After applying the shown sequence to the yellow token, which board letter is reached?
Required answer format: set "answer" to the selected shown destination label.
Example JSON:
{"answer":"D"}
```

### task_games__ludo_board__winning_roll_value / single / answer_and_annotation / sample 7829444500816313

- `instance_seed`: `7829444500816313`
- `word_count`: `74`
- `body_word_count`: `44`

```text
The image shows a Ludo-style cross board with one visible token for each player color and twelve two-cell arrows showing the clockwise track direction. A token must land exactly on finish. What die roll does the yellow token need to reach the yellow finish?
Annotation format: set "annotation" to one pixel point [x,y] at the token center.
Answer format: set "answer" to the integer die roll.
Example JSON:
{"annotation":[115,215],"answer":4}
```

### task_games__ludo_board__winning_roll_value / single / answer_only / sample 7829444500816313

- `instance_seed`: `7829444500816313`
- `word_count`: `58`
- `body_word_count`: `44`

```text
The image shows a Ludo-style cross board with one visible token for each player color and twelve two-cell arrows showing the clockwise track direction. A token must land exactly on finish. What die roll does the yellow token need to reach the yellow finish?
Final answer format: set "answer" to the integer die roll.
Example JSON:
{"answer":4}
```

### task_games__mancala_pit_board__post_sow_pit_count_value / single / answer_and_annotation / sample 5565852715385162

- `instance_seed`: `5565852715385162`
- `word_count`: `103`
- `body_word_count`: `43`

```text
The visual shows a two-row pit board with visible seeds and an arrow direction. Pick up all seeds from the X-marked pit and sow one seed at a time in the arrow direction. What is the final seed count for the target-marked pit?
Required annotation format: set "annotation" to an object with keys "source_pit" and "target_pit", each mapped to that pit bounding box as [x0,y0,x1,y1] in pixels.
Required answer format: set "answer" to the integer number of seeds in the target-marked pit after the move.
Example JSON:
{"annotation":{"source_pit":[80,140,180,204],"target_pit":[420,140,520,204]},"answer":5}
```

### task_games__mancala_pit_board__post_sow_pit_count_value / single / answer_only / sample 5565852715385162

- `instance_seed`: `5565852715385162`
- `word_count`: `65`
- `body_word_count`: `43`

```text
The visual shows a two-row pit board with visible seeds and an arrow direction. Pick up all seeds from the X-marked pit and sow one seed at a time in the arrow direction. What is the final seed count for the target-marked pit?
Required answer format: set "answer" to the integer number of seeds in the target-marked pit after the move.
Example JSON:
{"answer":5}
```

### task_games__mancala_pit_board__sowing_landing_option_label / single / answer_and_annotation / sample 7184798545373255

- `instance_seed`: `7184798545373255`
- `word_count`: `81`
- `body_word_count`: `42`

```text
The visual shows a two-row pit board with visible seeds and an arrow direction. Pick up all seeds from the X-marked pit and sow one seed at a time in the arrow direction. Which option letter is on the final landing pit?
Annotation format: set "annotation" to one bounding box [x0,y0,x1,y1] around the selected landing pit.
Answer format: set "answer" to the option letter marking the final landing pit.
Example JSON:
{"annotation":[420,140,520,204],"answer":"B"}
```

### task_games__mancala_pit_board__sowing_landing_option_label / single / answer_only / sample 7184798545373255

- `instance_seed`: `7184798545373255`
- `word_count`: `60`
- `body_word_count`: `42`

```text
The visual shows a two-row pit board with visible seeds and an arrow direction. Pick up all seeds from the X-marked pit and sow one seed at a time in the arrow direction. Which option letter is on the final landing pit?
Required answer format: set "answer" to the option letter marking the final landing pit.
Example JSON:
{"answer":"B"}
```

### task_games__marble_chain__max_pop_direction_label / single / answer_and_annotation / sample 6017111492138897

- `instance_seed`: `6017111492138897`
- `word_count`: `122`
- `body_word_count`: `86`

```text
The figure shows a Zuma-like marble-chain board with a central shooter, a colored shooter marble, arrow shot options, and colored marbles on a curved track. Fire the shooter marble straight along the chosen arrow. It inserts at the chain gap indicated by that arrow. If the inserted marble's same-color contiguous run has at least three marbles, the existing marbles in that run are removed and the chain closes once. Do not apply any later cascade. Which labeled arrow gives the maximum number of existing marbles removed?
Annotation format: set "annotation" to one pixel-space point [x, y] at the insertion gap indicated by the selected arrow.
Answer format: set "answer" to only the selected shot-arrow letter.
Example JSON:
{"annotation":[465,286],"answer":"C"}
```

### task_games__marble_chain__max_pop_direction_label / single / answer_only / sample 6017111492138897

- `instance_seed`: `6017111492138897`
- `word_count`: `100`
- `body_word_count`: `86`

```text
The figure shows a Zuma-like marble-chain board with a central shooter, a colored shooter marble, arrow shot options, and colored marbles on a curved track. Fire the shooter marble straight along the chosen arrow. It inserts at the chain gap indicated by that arrow. If the inserted marble's same-color contiguous run has at least three marbles, the existing marbles in that run are removed and the chain closes once. Do not apply any later cascade. Which labeled arrow gives the maximum number of existing marbles removed?
Answer format: set "answer" to only the selected shot-arrow letter.
Example JSON:
{"answer":"C"}
```

### task_games__marble_chain__shot_effect_value / single / answer_and_annotation / sample 7598429217710859

- `instance_seed`: `7598429217710859`
- `word_count`: `156`
- `body_word_count`: `86`

```text
The scene shows a Zuma-like marble-chain board with a central shooter, a colored shooter marble, arrow shot options, and colored marbles on a curved track. Fire the shooter marble straight along the chosen arrow. It inserts at the chain gap indicated by that arrow. If the inserted marble's same-color contiguous run has at least three marbles, the existing marbles in that run are removed and the chain closes once. Do not apply any later cascade. Count the existing marbles that pop after the shown marked shot.
Required annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one for each existing chain marble that would pop; use an empty array if none pop.
Required answer format: set "answer" to the number of existing chain marbles removed by the marked shot, excluding the shooter marble.
Example JSON:
{"annotation":[[430,206,466,242],[484,224,520,260],[533,258,569,294],[572,304,608,340]],"answer":4}
```

### task_games__marble_chain__shot_effect_value / single / answer_only / sample 7598429217710859

- `instance_seed`: `7598429217710859`
- `word_count`: `110`
- `body_word_count`: `86`

```text
The scene shows a Zuma-like marble-chain board with a central shooter, a colored shooter marble, arrow shot options, and colored marbles on a curved track. Fire the shooter marble straight along the chosen arrow. It inserts at the chain gap indicated by that arrow. If the inserted marble's same-color contiguous run has at least three marbles, the existing marbles in that run are removed and the chain closes once. Do not apply any later cascade. Count the existing marbles that pop after the shown marked shot.
Answer format: set "answer" to the number of existing chain marbles removed by the marked shot, excluding the shooter marble.
Example JSON:
{"answer":4}
```

### task_games__match3__gem_count / column_color_gem_count / answer_and_annotation / sample 8963860111492987

- `instance_seed`: `8963860111492987`
- `word_count`: `75`
- `body_word_count`: `23`

```text
The scene shows a match-3 jewel grid with row and column numbers and colored gems. Count the red [#E63232] gems in column 5.
Final answer format: set "answer" to the exact count as an integer.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one for each matching gem in the column.
Example JSON:
{"annotation":[[224,310,280,366],[290,310,346,366],[356,310,412,366],[422,310,478,366]],"answer":4}
```

### task_games__match3__gem_count / column_color_gem_count / answer_only / sample 8963860111492987

- `instance_seed`: `8963860111492987`
- `word_count`: `39`
- `body_word_count`: `23`

```text
The scene shows a match-3 jewel grid with row and column numbers and colored gems. Count the red [#E63232] gems in column 5.
Required answer format: set "answer" to the exact count as an integer.
Example JSON:
{"answer":4}
```

### task_games__match3__gem_count / grid_color_gem_count / answer_and_annotation / sample 8425662409023108

- `instance_seed`: `8425662409023108`
- `word_count`: `74`
- `body_word_count`: `24`

```text
The scene shows a match-3 jewel grid with row and column numbers and colored gems. Count the red [#E63232] gems in the whole grid.
Required annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one for each matching gem.
Required answer format: set "answer" to the exact count as an integer.
Example JSON:
{"annotation":[[224,310,280,366],[290,310,346,366],[356,310,412,366],[422,310,478,366]],"answer":4}
```

### task_games__match3__gem_count / grid_color_gem_count / answer_only / sample 8425662409023108

- `instance_seed`: `8425662409023108`
- `word_count`: `39`
- `body_word_count`: `24`

```text
The scene shows a match-3 jewel grid with row and column numbers and colored gems. Count the red [#E63232] gems in the whole grid.
Answer format: set "answer" to the exact count as an integer.
Example JSON:
{"answer":4}
```

### task_games__match3__gem_count / row_color_gem_count / answer_and_annotation / sample 8065513264599721

- `instance_seed`: `8065513264599721`
- `word_count`: `77`
- `body_word_count`: `24`

```text
The scene shows a match-3 jewel grid with row and column numbers and colored gems. How many purple [#963ACA] gems are in row 3?
Required annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one for each matching gem in the row.
Required answer format: set "answer" to the exact count as an integer.
Example JSON:
{"annotation":[[224,310,280,366],[290,310,346,366],[356,310,412,366],[422,310,478,366]],"answer":4}
```

### task_games__match3__gem_count / row_color_gem_count / answer_only / sample 8065513264599721

- `instance_seed`: `8065513264599721`
- `word_count`: `39`
- `body_word_count`: `24`

```text
The scene shows a match-3 jewel grid with row and column numbers and colored gems. How many purple [#963ACA] gems are in row 3?
Answer format: set "answer" to the exact count as an integer.
Example JSON:
{"answer":4}
```

### task_games__match3__max_clear_swap_label / single / answer_and_annotation / sample 6666885382773001

- `instance_seed`: `6666885382773001`
- `word_count`: `99`
- `body_word_count`: `66`

```text
This board shows a match-3 jewel grid with row and column numbers, colored gems, and labeled adjacent-swap arrows. Swap only the two adjacent gems connected by the arrow. After the swap, immediately clear every horizontal or vertical run of three or more matching gems. Count only this immediate clear; do not apply falling, refill, special effects, or cascades. Which labeled swap arrow clears the most gems?
Final answer format: set "answer" to only the selected swap-arrow letter.
Annotation format: set "annotation" to the [x,y] pixel point on the selected swap arrow.
Example JSON:
{"annotation":[456,284],"answer":"C"}
```

### task_games__match3__max_clear_swap_label / single / answer_only / sample 6666885382773001

- `instance_seed`: `6666885382773001`
- `word_count`: `81`
- `body_word_count`: `66`

```text
This board shows a match-3 jewel grid with row and column numbers, colored gems, and labeled adjacent-swap arrows. Swap only the two adjacent gems connected by the arrow. After the swap, immediately clear every horizontal or vertical run of three or more matching gems. Count only this immediate clear; do not apply falling, refill, special effects, or cascades. Which labeled swap arrow clears the most gems?
Final answer format: set "answer" to only the selected swap-arrow letter.
Example JSON:
{"answer":"C"}
```

### task_games__minecraft__resource_route_cost / single / answer_and_annotation / sample 5368666606328913

- `instance_seed`: `5368666606328913`
- `word_count`: `106`
- `body_word_count`: `37`

```text
The image shows a Minecraft-like isometric block world with cube terrain, visible cube stacks or raised blocks, and any marked track needed for the question. How many raised stone or dirt blocks lie on the shown track?
Required annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one around each raised stone or dirt block on the visible track; use an empty array if the count is 0.
Required answer format: set "answer" to the integer number of raised blocks on the track.
Example JSON:
{"annotation":[[290,286,340,342],[319,257,369,313],[498,182,548,238],[527,210,577,266]],"answer":4}
```

### task_games__minecraft__resource_route_cost / single / answer_only / sample 5368666606328913

- `instance_seed`: `5368666606328913`
- `word_count`: `56`
- `body_word_count`: `37`

```text
The image shows a Minecraft-like isometric block world with cube terrain, visible cube stacks or raised blocks, and any marked track needed for the question. How many raised stone or dirt blocks lie on the shown track?
Required answer format: set "answer" to the integer number of raised blocks on the track.
Example JSON:
{"answer":4}
```

### task_games__minecraft__stack_height_condition_count / at_least_height_count / answer_and_annotation / sample 8769253213208838

- `instance_seed`: `8769253213208838`
- `word_count`: `95`
- `body_word_count`: `36`

```text
The figure shows a Minecraft-like isometric block world with cube terrain, visible cube stacks or raised blocks, and any marked track needed for the question. Count the visible stacks that are at least 3 cubes tall.
Required annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one around each visible stack that is at least the named height.
Required answer format: set "answer" to the integer number of stacks that are at least the named height.
Example JSON:
{"annotation":[[265,218,315,274],[398,174,448,230],[517,250,567,306]],"answer":3}
```

### task_games__minecraft__stack_height_condition_count / at_least_height_count / answer_only / sample 8769253213208838

- `instance_seed`: `8769253213208838`
- `word_count`: `58`
- `body_word_count`: `36`

```text
The figure shows a Minecraft-like isometric block world with cube terrain, visible cube stacks or raised blocks, and any marked track needed for the question. Count the visible stacks that are at least 3 cubes tall.
Final answer format: set "answer" to the integer number of stacks that are at least the named height.
Example JSON:
{"answer":3}
```

### task_games__minecraft__stack_height_condition_count / exact_height_count / answer_and_annotation / sample 6049726165737765

- `instance_seed`: `6049726165737765`
- `word_count`: `88`
- `body_word_count`: `32`

```text
This scene shows a Minecraft-like isometric block world with cube terrain, visible cube stacks or raised blocks, and any marked track needed for the question. How many stacks have exactly 3 cubes?
Final answer format: set "answer" to the integer number of stacks that are exactly the named height.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one around each visible stack that is exactly the named height.
Example JSON:
{"annotation":[[265,218,315,274],[398,174,448,230],[517,250,567,306]],"answer":3}
```

### task_games__minecraft__stack_height_condition_count / exact_height_count / answer_only / sample 6049726165737765

- `instance_seed`: `6049726165737765`
- `word_count`: `53`
- `body_word_count`: `32`

```text
This scene shows a Minecraft-like isometric block world with cube terrain, visible cube stacks or raised blocks, and any marked track needed for the question. How many stacks have exactly 3 cubes?
Required answer format: set "answer" to the integer number of stacks that are exactly the named height.
Example JSON:
{"answer":3}
```

### task_games__minecraft__top_ore_stack_count / single / answer_and_annotation / sample 5474574971262962

- `instance_seed`: `5474574971262962`
- `word_count`: `105`
- `body_word_count`: `38`

```text
This scene shows a Minecraft-like isometric block world with cube terrain, visible cube stacks or raised blocks, and any marked track needed for the question. Among the visible stacks, how many show diamond ore as their top cube?
Required annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one around each visible stack whose top cube is the named ore.
Required answer format: set "answer" to the integer number of stacks whose top cube is the named ore.
Example JSON:
{"annotation":[[314,278,364,334],[372,249,422,305],[430,220,480,276],[459,191,509,247],[343,162,393,218]],"answer":5}
```

### task_games__minecraft__top_ore_stack_count / single / answer_only / sample 5474574971262962

- `instance_seed`: `5474574971262962`
- `word_count`: `59`
- `body_word_count`: `38`

```text
This scene shows a Minecraft-like isometric block world with cube terrain, visible cube stacks or raised blocks, and any marked track needed for the question. Among the visible stacks, how many show diamond ore as their top cube?
Answer format: set "answer" to the integer number of stacks whose top cube is the named ore.
Example JSON:
{"answer":5}
```

### task_games__minesweeper__forced_cell_count / forced_mine_count / answer_and_annotation / sample 3403252503280498

- `instance_seed`: `3403252503280498`
- `word_count`: `138`
- `body_word_count`: `86`

```text
The figure shows a Minesweeper grid with opened number cells, hidden cells, flags, and extra hidden distractor cells. In Minesweeper, each opened number tells how many mines are in its eight neighboring cells, and each flag marks a known mine. If a number already has that many adjacent flags, its other hidden neighbors are safe. If the number still needs exactly all remaining hidden neighbors, those hidden neighbors are mines. Use the outlined opened clue cell(s). How many hidden cells are forced to be mines?
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one for each hidden cell forced to be a mine.
Answer format: set "answer" to the count of hidden cells that must be mines.
Example JSON:
{"annotation":[[147,227,203,283],[217,227,273,283],[287,227,343,283]],"answer":3}
```

### task_games__minesweeper__forced_cell_count / forced_mine_count / answer_only / sample 3403252503280498

- `instance_seed`: `3403252503280498`
- `word_count`: `105`
- `body_word_count`: `86`

```text
The figure shows a Minesweeper grid with opened number cells, hidden cells, flags, and extra hidden distractor cells. In Minesweeper, each opened number tells how many mines are in its eight neighboring cells, and each flag marks a known mine. If a number already has that many adjacent flags, its other hidden neighbors are safe. If the number still needs exactly all remaining hidden neighbors, those hidden neighbors are mines. Use the outlined opened clue cell(s). How many hidden cells are forced to be mines?
Required answer format: set "answer" to the count of hidden cells that must be mines.
Example JSON:
{"answer":3}
```

### task_games__minesweeper__forced_cell_count / forced_safe_count / answer_and_annotation / sample 3763056537079632

- `instance_seed`: `3763056537079632`
- `word_count`: `137`
- `body_word_count`: `85`

```text
This scene shows a Minesweeper grid with opened number cells, hidden cells, flags, and extra hidden distractor cells. In Minesweeper, each opened number tells how many mines are in its eight neighboring cells, and each flag marks a known mine. If a number already has that many adjacent flags, its other hidden neighbors are safe. If the number still needs exactly all remaining hidden neighbors, those hidden neighbors are mines. Use the outlined opened clue cell(s). Count the hidden cells that cannot contain mines.
Final answer format: set "answer" to the count of hidden cells that must be safe.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one for each hidden cell forced to be safe.
Example JSON:
{"annotation":[[147,227,203,283],[217,227,273,283],[287,227,343,283]],"answer":3}
```

### task_games__minesweeper__forced_cell_count / forced_safe_count / answer_only / sample 3763056537079632

- `instance_seed`: `3763056537079632`
- `word_count`: `103`
- `body_word_count`: `85`

```text
This scene shows a Minesweeper grid with opened number cells, hidden cells, flags, and extra hidden distractor cells. In Minesweeper, each opened number tells how many mines are in its eight neighboring cells, and each flag marks a known mine. If a number already has that many adjacent flags, its other hidden neighbors are safe. If the number still needs exactly all remaining hidden neighbors, those hidden neighbors are mines. Use the outlined opened clue cell(s). Count the hidden cells that cannot contain mines.
Answer format: set "answer" to the count of hidden cells that must be safe.
Example JSON:
{"answer":3}
```

### task_games__minesweeper__forced_mine_cell_label / single / answer_and_annotation / sample 6035462209380766

- `instance_seed`: `6035462209380766`
- `word_count`: `132`
- `body_word_count`: `85`

```text
The visual shows a Minesweeper grid with opened number cells, hidden cells, flags, and extra hidden distractor cells. In Minesweeper, each opened number tells how many mines are in its eight neighboring cells, and each flag marks a known mine. If a number already has that many adjacent flags, its other hidden neighbors are safe. If the number still needs exactly all remaining hidden neighbors, those hidden neighbors are mines. Using the visible numbers and nearby flags, which labeled covered cell is certainly a mine?
Annotation format: set "annotation" to the [x, y] pixel point at the center of the labeled hidden cell that is guaranteed to be a mine.
Answer format: set "answer" to the single option letter printed inside the guaranteed mine cell.
Example JSON:
{"annotation":[245,255],"answer":"B"}
```

### task_games__minesweeper__forced_mine_cell_label / single / answer_only / sample 6035462209380766

- `instance_seed`: `6035462209380766`
- `word_count`: `104`
- `body_word_count`: `85`

```text
The visual shows a Minesweeper grid with opened number cells, hidden cells, flags, and extra hidden distractor cells. In Minesweeper, each opened number tells how many mines are in its eight neighboring cells, and each flag marks a known mine. If a number already has that many adjacent flags, its other hidden neighbors are safe. If the number still needs exactly all remaining hidden neighbors, those hidden neighbors are mines. Using the visible numbers and nearby flags, which labeled covered cell is certainly a mine?
Answer format: set "answer" to the single option letter printed inside the guaranteed mine cell.
Example JSON:
{"answer":"B"}
```

### task_games__minesweeper__remaining_mine_count_value / single / answer_and_annotation / sample 3666282509205039

- `instance_seed`: `3666282509205039`
- `word_count`: `136`
- `body_word_count`: `88`

```text
The scene shows a Minesweeper grid with opened number cells, hidden cells, flags, and extra hidden distractor cells. In Minesweeper, each opened number tells how many mines are in its eight neighboring cells, and each flag marks a known mine. If a number already has that many adjacent flags, its other hidden neighbors are safe. If the number still needs exactly all remaining hidden neighbors, those hidden neighbors are mines. Use the outlined opened clue cell and nearby flags. How many more adjacent mines does that number require?
Required annotation format: set "annotation" to the [x, y] pixel point at the center of the marked opened number cell.
Required answer format: set "answer" to the number of additional mines that must be adjacent to the marked opened number cell.
Example JSON:
{"annotation":[245,255],"answer":2}
```

### task_games__minesweeper__remaining_mine_count_value / single / answer_only / sample 3666282509205039

- `instance_seed`: `3666282509205039`
- `word_count`: `112`
- `body_word_count`: `88`

```text
The scene shows a Minesweeper grid with opened number cells, hidden cells, flags, and extra hidden distractor cells. In Minesweeper, each opened number tells how many mines are in its eight neighboring cells, and each flag marks a known mine. If a number already has that many adjacent flags, its other hidden neighbors are safe. If the number still needs exactly all remaining hidden neighbors, those hidden neighbors are mines. Use the outlined opened clue cell and nearby flags. How many more adjacent mines does that number require?
Answer format: set "answer" to the number of additional mines that must be adjacent to the marked opened number cell.
Example JSON:
{"answer":2}
```

### task_games__minigolf__first_obstacle_label / single / answer_and_annotation / sample 4293811882434532

- `instance_seed`: `4293811882434532`
- `word_count`: `88`
- `body_word_count`: `46`

```text
The figure shows a mini-golf putting course with a ball, a hole, visible obstacles, and any shown shot cues. The dashed cue shows the starting direction of the putt; extend it as a straight line. What is the label of the first obstacle on that line?
Annotation format: set "annotation" to one [x, y] pixel point at the center of the first labeled obstacle hit by the extended cue.
Answer format: set "answer" to the selected obstacle label as a string.
Example JSON:
{"annotation":[486,258],"answer":"D"}
```

### task_games__minigolf__first_obstacle_label / single / answer_only / sample 4293811882434532

- `instance_seed`: `4293811882434532`
- `word_count`: `62`
- `body_word_count`: `46`

```text
The figure shows a mini-golf putting course with a ball, a hole, visible obstacles, and any shown shot cues. The dashed cue shows the starting direction of the putt; extend it as a straight line. What is the label of the first obstacle on that line?
Answer format: set "answer" to the selected obstacle label as a string.
Example JSON:
{"answer":"D"}
```

### task_games__minigolf__shot_path_label / single / answer_and_annotation / sample 7179003808968588

- `instance_seed`: `7179003808968588`
- `word_count`: `99`
- `body_word_count`: `44`

```text
This scene shows a mini-golf putting course with a ball, a hole, visible obstacles, and any shown shot cues. Compare the numbered starting cues. A shot travels straight and bounces off course walls like a mirror before continuing. Which shot number reaches the hole?
Annotation format: set "annotation" to one path segment using two pixel-point endpoints [x, y] in [[x0, y0], [x1, y1]] form, matching the endpoints of the selected visible dashed cue from the ball outward.
Answer format: set "answer" to the selected numbered shot label as a string.
Example JSON:
{"annotation":[[486,562],[592,520]],"answer":"3"}
```

### task_games__minigolf__shot_path_label / single / answer_only / sample 7179003808968588

- `instance_seed`: `7179003808968588`
- `word_count`: `62`
- `body_word_count`: `44`

```text
This scene shows a mini-golf putting course with a ball, a hole, visible obstacles, and any shown shot cues. Compare the numbered starting cues. A shot travels straight and bounces off course walls like a mirror before continuing. Which shot number reaches the hole?
Required answer format: set "answer" to the selected numbered shot label as a string.
Example JSON:
{"answer":"3"}
```

### task_games__nine_mens_morris__mill_completion_point_count / black_mill_completion_point_count / answer_and_annotation / sample 3707864399150484

- `instance_seed`: `3707864399150484`
- `word_count`: `109`
- `body_word_count`: `56`

```text
The visual shows a Nine Men's Morris board with light and dark pieces placed on intersections. A mill is three same-color pieces on one straight line. Count each piece only once even if it belongs to more than one mill. How many empty points would complete a mill for black if black placed one piece there?
Annotation format: set "annotation" to [x, y] pixel points at the centers of every empty point where placing one black piece would complete a mill.
Answer format: set "answer" to the number of empty points where placing one black piece would complete a mill.
Example JSON:
{"annotation":[[242,202],[362,202]],"answer":2}
```

### task_games__nine_mens_morris__mill_completion_point_count / black_mill_completion_point_count / answer_only / sample 3707864399150484

- `instance_seed`: `3707864399150484`
- `word_count`: `79`
- `body_word_count`: `56`

```text
The visual shows a Nine Men's Morris board with light and dark pieces placed on intersections. A mill is three same-color pieces on one straight line. Count each piece only once even if it belongs to more than one mill. How many empty points would complete a mill for black if black placed one piece there?
Answer format: set "answer" to the number of empty points where placing one black piece would complete a mill.
Example JSON:
{"answer":2}
```

### task_games__nine_mens_morris__mill_completion_point_count / white_mill_completion_point_count / answer_and_annotation / sample 3359752947733344

- `instance_seed`: `3359752947733344`
- `word_count`: `106`
- `body_word_count`: `53`

```text
This scene shows a Nine Men's Morris board with light and dark pieces placed on intersections. A mill is three same-color pieces on one straight line. Count each piece only once even if it belongs to more than one mill. What is the number of empty points that would complete a white mill?
Annotation format: set "annotation" to [x, y] pixel points at the centers of every empty point where placing one white piece would complete a mill.
Answer format: set "answer" to the number of empty points where placing one white piece would complete a mill.
Example JSON:
{"annotation":[[242,202],[362,202]],"answer":2}
```

### task_games__nine_mens_morris__mill_completion_point_count / white_mill_completion_point_count / answer_only / sample 3359752947733344

- `instance_seed`: `3359752947733344`
- `word_count`: `76`
- `body_word_count`: `53`

```text
This scene shows a Nine Men's Morris board with light and dark pieces placed on intersections. A mill is three same-color pieces on one straight line. Count each piece only once even if it belongs to more than one mill. What is the number of empty points that would complete a white mill?
Answer format: set "answer" to the number of empty points where placing one white piece would complete a mill.
Example JSON:
{"answer":2}
```

### task_games__nine_mens_morris__pieces_in_mill_count / single / answer_and_annotation / sample 1292939820745900

- `instance_seed`: `1292939820745900`
- `word_count`: `109`
- `body_word_count`: `51`

```text
The visual shows a Nine Men's Morris board with light and dark pieces placed on intersections. How many visible pieces belong to at least one mill overall? A mill is three same-color pieces on one straight line. Count each piece only once even if it belongs to more than one mill.
Required annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one around each piece that belongs to at least one mill.
Required answer format: set "answer" to the total number of pieces that belong to at least one mill.
Example JSON:
{"annotation":[[180,220,224,264],[340,220,384,264],[500,220,544,264]],"answer":3}
```

### task_games__nine_mens_morris__pieces_in_mill_count / single / answer_only / sample 1292939820745900

- `instance_seed`: `1292939820745900`
- `word_count`: `73`
- `body_word_count`: `51`

```text
The visual shows a Nine Men's Morris board with light and dark pieces placed on intersections. How many visible pieces belong to at least one mill overall? A mill is three same-color pieces on one straight line. Count each piece only once even if it belongs to more than one mill.
Required answer format: set "answer" to the total number of pieces that belong to at least one mill.
Example JSON:
{"answer":3}
```

### task_games__pacman__next_item_label / single / answer_and_annotation / sample 2359380262578424

- `instance_seed`: `2359380262578424`
- `word_count`: `86`
- `body_word_count`: `36`

```text
The figure shows a wider Pac-Man style maze with a visible Pac-Man marker, ghosts, normal pellets, bonus items, and a highlighted route. Among the labeled bonus items, which one is encountered first on the highlighted route?
Annotation format: set "annotation" to one [x, y] point coordinate at the center of the first labeled bonus item reached along the route.
Answer format: set "answer" to the single option letter of the first labeled bonus item reached along the highlighted route.
Example JSON:
{"annotation":[509,305],"answer":"D"}
```

### task_games__pacman__next_item_label / single / answer_only / sample 2359380262578424

- `instance_seed`: `2359380262578424`
- `word_count`: `60`
- `body_word_count`: `36`

```text
The figure shows a wider Pac-Man style maze with a visible Pac-Man marker, ghosts, normal pellets, bonus items, and a highlighted route. Among the labeled bonus items, which one is encountered first on the highlighted route?
Answer format: set "answer" to the single option letter of the first labeled bonus item reached along the highlighted route.
Example JSON:
{"answer":"D"}
```

### task_games__pacman__path_pellet_count / single / answer_and_annotation / sample 7771494224160508

- `instance_seed`: `7771494224160508`
- `word_count`: `78`
- `body_word_count`: `35`

```text
This scene shows a wider Pac-Man style maze with a visible Pac-Man marker, ghosts, normal pellets, bonus items, and a highlighted route. Report the count of normal pellets that lie directly on the highlighted route.
Annotation format: set "annotation" to [x, y] pixel points at the centers of every normal pellet on the highlighted route.
Answer format: set "answer" to the number of normal pellets on the highlighted route.
Example JSON:
{"annotation":[[315,209],[369,209]],"answer":5}
```

### task_games__pacman__path_pellet_count / single / answer_only / sample 7771494224160508

- `instance_seed`: `7771494224160508`
- `word_count`: `53`
- `body_word_count`: `35`

```text
This scene shows a wider Pac-Man style maze with a visible Pac-Man marker, ghosts, normal pellets, bonus items, and a highlighted route. Report the count of normal pellets that lie directly on the highlighted route.
Answer format: set "answer" to the number of normal pellets on the highlighted route.
Example JSON:
{"answer":5}
```

### task_games__pacman__pellet_count_before_ghost / single / answer_and_annotation / sample 1385109207079144

- `instance_seed`: `1385109207079144`
- `word_count`: `100`
- `body_word_count`: `40`

```text
The figure shows a Pac-Man style maze with a visible Pac-Man marker, ghosts, normal pellets, bonus items, and a highlighted route. Follow the highlighted route from Pac-Man. How many normal pellets are reached before the first ghost on that route?
Annotation format: set "annotation" to {"counted_pellets":[[x, y], ...], "first_ghost":[[x, y]]}, using center points for pellets before the ghost and the first route ghost.
Answer format: set "answer" to the number of normal pellets reached before the first ghost on the highlighted route.
Example JSON:
{"annotation":{"counted_pellets":[[355,217],[415,277],[475,277],[535,277]],"first_ghost":[[548,278]]},"answer":4}
```

### task_games__pacman__pellet_count_before_ghost / single / answer_only / sample 1385109207079144

- `instance_seed`: `1385109207079144`
- `word_count`: `64`
- `body_word_count`: `40`

```text
The figure shows a Pac-Man style maze with a visible Pac-Man marker, ghosts, normal pellets, bonus items, and a highlighted route. Follow the highlighted route from Pac-Man. How many normal pellets are reached before the first ghost on that route?
Final answer format: set "answer" to the number of normal pellets reached before the first ghost on the highlighted route.
Example JSON:
{"answer":4}
```

### task_games__pacman__route_score_value / single / answer_and_annotation / sample 5303103110037517

- `instance_seed`: `5303103110037517`
- `word_count`: `97`
- `body_word_count`: `45`

```text
The figure shows a Pac-Man style maze with a visible Pac-Man marker, ghosts, normal pellets, bonus items, and a highlighted route. Pellets score 1; bonus items score their printed value. Add the scores of the normal pellets and printed-value bonus items on the highlighted route.
Final answer format: set "answer" to the integer total score from collectibles on the highlighted route.
Annotation format: set "annotation" to [x, y] pixel points at the centers of each normal pellet or printed-value bonus item included in the route score.
Example JSON:
{"annotation":[[315,209],[369,209],[424,264]],"answer":12}
```

### task_games__pacman__route_score_value / single / answer_only / sample 5303103110037517

- `instance_seed`: `5303103110037517`
- `word_count`: `65`
- `body_word_count`: `45`

```text
The figure shows a Pac-Man style maze with a visible Pac-Man marker, ghosts, normal pellets, bonus items, and a highlighted route. Pellets score 1; bonus items score their printed value. Add the scores of the normal pellets and printed-value bonus items on the highlighted route.
Final answer format: set "answer" to the integer total score from collectibles on the highlighted route.
Example JSON:
{"answer":12}
```

### task_games__pinball_table__first_hit_object_label / single / answer_and_annotation / sample 5119459785954719

- `instance_seed`: `5119459785954719`
- `word_count`: `77`
- `body_word_count`: `36`

```text
The image shows a tilted pinball playfield with a ball, a straight launch cue, flippers, bumpers, lanes, and labeled targets. The ball follows the arrow direction in a straight line. Which labeled object is hit first?
Annotation format: set "annotation" to one [x, y] pixel point at the center of the first labeled object hit by the path.
Answer format: set "answer" to the selected object label as a string.
Example JSON:
{"annotation":[410,260],"answer":"D"}
```

### task_games__pinball_table__first_hit_object_label / single / answer_only / sample 5119459785954719

- `instance_seed`: `5119459785954719`
- `word_count`: `53`
- `body_word_count`: `36`

```text
The image shows a tilted pinball playfield with a ball, a straight launch cue, flippers, bumpers, lanes, and labeled targets. The ball follows the arrow direction in a straight line. Which labeled object is hit first?
Required answer format: set "answer" to the selected object label as a string.
Example JSON:
{"answer":"D"}
```

### task_games__pinball_table__scoreable_object_count / single / answer_and_annotation / sample 255902490365477

- `instance_seed`: `255902490365477`
- `word_count`: `89`
- `body_word_count`: `40`

```text
The scene shows a tilted pinball playfield with a ball, flippers, bumpers, lanes, numeric score targets, and blank objects. Objects with a number are scoreable; objects without a number are not scoreable. How many numeric-score objects are on the table?
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one around each object that shows a numeric score label.
Answer format: set "answer" to the integer count of scoreable objects.
Example JSON:
{"annotation":[[238,158,282,202],[398,288,442,332],[548,218,592,262]],"answer":3}
```

### task_games__pinball_table__scoreable_object_count / single / answer_only / sample 255902490365477

- `instance_seed`: `255902490365477`
- `word_count`: `56`
- `body_word_count`: `40`

```text
The scene shows a tilted pinball playfield with a ball, flippers, bumpers, lanes, numeric score targets, and blank objects. Objects with a number are scoreable; objects without a number are not scoreable. How many numeric-score objects are on the table?
Required answer format: set "answer" to the integer count of scoreable objects.
Example JSON:
{"answer":3}
```

### task_games__platformer__collectible_count / single / answer_and_annotation / sample 10685334019604

- `instance_seed`: `10685334019604`
- `word_count`: `91`
- `body_word_count`: `37`

```text
The visual shows a side-scroller platformer level with a player character, platforms, hazards, coins, bonus items, and a dashed jump arc. The dashed arc shows the jump path to follow. How many coins lie on that arc?
Required annotation format: set "annotation" to [x, y] pixel points at the centers of each coin lying on the dashed jump arc.
Required answer format: set "answer" to the number of coins lying on the dashed jump arc as an integer.
Example JSON:
{"annotation":[[346,228],[448,200],[554,216],[659,272]],"answer":4}
```

### task_games__platformer__collectible_count / single / answer_only / sample 10685334019604

- `instance_seed`: `10685334019604`
- `word_count`: `60`
- `body_word_count`: `37`

```text
The visual shows a side-scroller platformer level with a player character, platforms, hazards, coins, bonus items, and a dashed jump arc. The dashed arc shows the jump path to follow. How many coins lie on that arc?
Final answer format: set "answer" to the number of coins lying on the dashed jump arc as an integer.
Example JSON:
{"answer":4}
```

### task_games__platformer__jump_collectible_score_value / single / answer_and_annotation / sample 6185062697555905

- `instance_seed`: `6185062697555905`
- `word_count`: `95`
- `body_word_count`: `43`

```text
The visual shows a side-scroller platformer level with a player character, platforms, hazards, coins, bonus items, and a dashed jump arc. Coins score 1; bonus items score their printed value. The character follows the dashed arc. What score is collected on that path?
Final answer format: set "answer" to the integer total score from collectibles on the dashed jump arc.
Annotation format: set "annotation" to [x, y] pixel points at the centers of each coin or printed-value bonus item included in the dashed-arc score.
Example JSON:
{"annotation":[[346,228],[448,200],[554,216]],"answer":13}
```

### task_games__platformer__jump_collectible_score_value / single / answer_only / sample 6185062697555905

- `instance_seed`: `6185062697555905`
- `word_count`: `63`
- `body_word_count`: `43`

```text
The visual shows a side-scroller platformer level with a player character, platforms, hazards, coins, bonus items, and a dashed jump arc. Coins score 1; bonus items score their printed value. The character follows the dashed arc. What score is collected on that path?
Answer format: set "answer" to the integer total score from collectibles on the dashed jump arc.
Example JSON:
{"answer":13}
```

### task_games__platformer__jump_landing_label / single / answer_and_annotation / sample 899617163022087

- `instance_seed`: `899617163022087`
- `word_count`: `86`
- `body_word_count`: `45`

```text
The visual shows a side-scroller platformer level with a player character, platforms, hazards, coins, bonus items, and a dashed jump arc. The dashed arc shows the first part of the jump; extend the same smooth arc forward. Identify the labeled platform where the jump ends.
Annotation format: set "annotation" to one bounding box [x0, y0, x1, y1] around the labeled platform where the jump lands.
Answer format: set "answer" to the selected platform label as a string.
Example JSON:
{"annotation":[604,398,784,442],"answer":"D"}
```

### task_games__platformer__jump_landing_label / single / answer_only / sample 899617163022087

- `instance_seed`: `899617163022087`
- `word_count`: `61`
- `body_word_count`: `45`

```text
The visual shows a side-scroller platformer level with a player character, platforms, hazards, coins, bonus items, and a dashed jump arc. The dashed arc shows the first part of the jump; extend the same smooth arc forward. Identify the labeled platform where the jump ends.
Answer format: set "answer" to the selected platform label as a string.
Example JSON:
{"answer":"D"}
```

### task_games__pool__blocking_ball_count / single / answer_and_annotation / sample 4938558360210663

- `instance_seed`: `4938558360210663`
- `word_count`: `99`
- `body_word_count`: `50`

```text
The figure shows a pool table with a cue ball, numbered object balls, and six pockets. The shown shot has two straight segments: cue ball to the marked target ball, then the marked target ball to the marked pocket. Count every other ball obstructing either part of the planned shot.
Required annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one around each other ball blocking either shot segment.
Required answer format: set "answer" to the number of other balls blocking either shot segment.
Example JSON:
{"annotation":[[242,282,278,318],[502,242,538,278]],"answer":2}
```

### task_games__pool__blocking_ball_count / single / answer_only / sample 4938558360210663

- `instance_seed`: `4938558360210663`
- `word_count`: `69`
- `body_word_count`: `50`

```text
The figure shows a pool table with a cue ball, numbered object balls, and six pockets. The shown shot has two straight segments: cue ball to the marked target ball, then the marked target ball to the marked pocket. Count every other ball obstructing either part of the planned shot.
Final answer format: set "answer" to the number of other balls blocking either shot segment.
Example JSON:
{"answer":2}
```

### task_games__pool__group_ball_count / single / answer_and_annotation / sample 8175137646740239

- `instance_seed`: `8175137646740239`
- `word_count`: `79`
- `body_word_count`: `26`

```text
The image shows a pool table with a cue ball, numbered object balls, and six pockets. Report the number of visible balls in the stripes group.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one around each visible ball in the current player's group.
Answer format: set "answer" to the number of visible balls in the current player's group.
Example JSON:
{"annotation":[[202,232,238,268],[412,312,448,348],[592,262,628,298]],"answer":3}
```

### task_games__pool__group_ball_count / single / answer_only / sample 8175137646740239

- `instance_seed`: `8175137646740239`
- `word_count`: `45`
- `body_word_count`: `26`

```text
The image shows a pool table with a cue ball, numbered object balls, and six pockets. Report the number of visible balls in the stripes group.
Answer format: set "answer" to the number of visible balls in the current player's group.
Example JSON:
{"answer":3}
```

### task_games__racing_track__ahead_object_count / single / answer_and_annotation / sample 7779934177908826

- `instance_seed`: `7779934177908826`
- `word_count`: `111`
- `body_word_count`: `53`

```text
This scene shows a rounded loop racing track with a checkered finish line, a direction arrow, a marked car, and other labeled cars. Follow the arrow direction from the marked car to the finish line. Do not count the marked car. Count the other cars between the marked car and the finish line.
Required annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1], one around each counted car; use an empty array when none qualify.
Required answer format: set "answer" to the integer count of other cars ahead of the marked car before the finish line.
Example JSON:
{"annotation":[[462,200,510,228],[588,317,636,345]],"answer":2}
```

### task_games__racing_track__ahead_object_count / single / answer_only / sample 7779934177908826

- `instance_seed`: `7779934177908826`
- `word_count`: `78`
- `body_word_count`: `53`

```text
This scene shows a rounded loop racing track with a checkered finish line, a direction arrow, a marked car, and other labeled cars. Follow the arrow direction from the marked car to the finish line. Do not count the marked car. Count the other cars between the marked car and the finish line.
Required answer format: set "answer" to the integer count of other cars ahead of the marked car before the finish line.
Example JSON:
{"answer":2}
```

### task_games__racing_track__finish_distance_extremum_label / closest_to_finish_label / answer_and_annotation / sample 6378569852393749

- `instance_seed`: `6378569852393749`
- `word_count`: `73`
- `body_word_count`: `37`

```text
The visual shows a top-down loop racing track with a checkered finish line, a direction arrow, and labeled cars. Measure distance along the track in the arrow direction. Which labeled car is closest to the finish line?
Required annotation format: set "annotation" to [x, y], the pixel center of the selected car.
Required answer format: set "answer" to the selected car label as a capital letter.
Example JSON:
{"annotation":[486,214],"answer":"C"}
```

### task_games__racing_track__finish_distance_extremum_label / closest_to_finish_label / answer_only / sample 6378569852393749

- `instance_seed`: `6378569852393749`
- `word_count`: `54`
- `body_word_count`: `37`

```text
The visual shows a top-down loop racing track with a checkered finish line, a direction arrow, and labeled cars. Measure distance along the track in the arrow direction. Which labeled car is closest to the finish line?
Answer format: set "answer" to the selected car label as a capital letter.
Example JSON:
{"answer":"C"}
```

### task_games__racing_track__finish_distance_extremum_label / farthest_from_finish_label / answer_and_annotation / sample 8762408655685272

- `instance_seed`: `8762408655685272`
- `word_count`: `76`
- `body_word_count`: `40`

```text
The visual shows a top-down loop racing track with a checkered finish line, a direction arrow, and labeled cars. Measure distance along the track in the arrow direction. Select the car with the longest remaining distance to the finish line.
Required annotation format: set "annotation" to [x, y], the pixel center of the selected car.
Required answer format: set "answer" to the selected car label as a capital letter.
Example JSON:
{"annotation":[486,214],"answer":"C"}
```

### task_games__racing_track__finish_distance_extremum_label / farthest_from_finish_label / answer_only / sample 8762408655685272

- `instance_seed`: `8762408655685272`
- `word_count`: `57`
- `body_word_count`: `40`

```text
The visual shows a top-down loop racing track with a checkered finish line, a direction arrow, and labeled cars. Measure distance along the track in the arrow direction. Select the car with the longest remaining distance to the finish line.
Answer format: set "answer" to the selected car label as a capital letter.
Example JSON:
{"answer":"C"}
```

### task_games__radial_hunt_board__capture_move_count / single / answer_and_annotation / sample 2996214024674987

- `instance_seed`: `2996214024674987`
- `word_count`: `120`
- `body_word_count`: `56`

```text
The board shows a radial point-and-line hunt board with three concentric circles, three diameters, and a few pieces. A capture move jumps over one adjacent opposing piece along the same drawn circle or diameter line and lands on the empty point immediately beyond it. What is the number of jump-over capture moves for the X-marked piece?
Required annotation format: set "annotation" to [x, y] pixel points at the centers of every empty point where the X-marked piece can land by a capture jump; use an empty array if there are none.
Required answer format: set "answer" to the number of legal capture moves for the X-marked piece.
Example JSON:
{"annotation":[[180.0,220.0],[268.0,220.0]],"answer":2}
```

### task_games__radial_hunt_board__capture_move_count / single / answer_only / sample 2996214024674987

- `instance_seed`: `2996214024674987`
- `word_count`: `76`
- `body_word_count`: `56`

```text
The board shows a radial point-and-line hunt board with three concentric circles, three diameters, and a few pieces. A capture move jumps over one adjacent opposing piece along the same drawn circle or diameter line and lands on the empty point immediately beyond it. What is the number of jump-over capture moves for the X-marked piece?
Required answer format: set "answer" to the number of legal capture moves for the X-marked piece.
Example JSON:
{"answer":2}
```

### task_games__radial_hunt_board__marked_piece_destination_count / single / answer_and_annotation / sample 8671490477695253

- `instance_seed`: `8671490477695253`
- `word_count`: `115`
- `body_word_count`: `54`

```text
This scene shows a radial point-and-line hunt board with three concentric circles, three diameters, and many pieces. A simple move goes one step along a drawn circle or diameter line to an adjacent empty point. Do not count capture jumps. How many adjacent empty points can the X-marked piece reach without a capture jump?
Final answer format: set "answer" to the number of one-step adjacent empty destinations for the X-marked piece.
Annotation format: set "annotation" to [x, y] pixel points at the centers of every one-step adjacent empty destination for the X-marked piece; use an empty array when the count is 0.
Example JSON:
{"annotation":[[180.0,220.0],[268.0,220.0]],"answer":2}
```

### task_games__radial_hunt_board__marked_piece_destination_count / single / answer_only / sample 8671490477695253

- `instance_seed`: `8671490477695253`
- `word_count`: `75`
- `body_word_count`: `54`

```text
This scene shows a radial point-and-line hunt board with three concentric circles, three diameters, and many pieces. A simple move goes one step along a drawn circle or diameter line to an adjacent empty point. Do not count capture jumps. How many adjacent empty points can the X-marked piece reach without a capture jump?
Required answer format: set "answer" to the number of one-step adjacent empty destinations for the X-marked piece.
Example JSON:
{"answer":2}
```

### task_games__reversi__frontier_disc_count / single / answer_and_annotation / sample 7599358082455192

- `instance_seed`: `7599358082455192`
- `word_count`: `75`
- `body_word_count`: `34`

```text
The scene shows an 8 by 8 Reversi board with black and white discs. A frontier disc touches at least one empty square horizontally, vertically, or diagonally. Determine the count of Black frontier discs.
Annotation format: set "annotation" to one pixel point [x,y] at the center of every counted Black frontier disc.
Answer format: set "answer" to the count of Black frontier discs.
Example JSON:
{"annotation":[[144,216],[216,216],[288,216]],"answer":3}
```

### task_games__reversi__frontier_disc_count / single / answer_only / sample 7599358082455192

- `instance_seed`: `7599358082455192`
- `word_count`: `49`
- `body_word_count`: `34`

```text
The scene shows an 8 by 8 Reversi board with black and white discs. A frontier disc touches at least one empty square horizontally, vertically, or diagonally. Determine the count of Black frontier discs.
Answer format: set "answer" to the count of Black frontier discs.
Example JSON:
{"answer":3}
```

### task_games__reversi__legal_destination_count / single / answer_and_annotation / sample 6155938070143178

- `instance_seed`: `6155938070143178`
- `word_count`: `85`
- `body_word_count`: `46`

```text
The image shows a 6 by 6 Reversi board with black and white discs. Black is to move. A legal move is an empty square that brackets one or more opponent discs in at least one straight line. Count the legal move squares available to Black.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] for every legal move square.
Answer format: set "answer" to the count of legal moves.
Example JSON:
{"annotation":[[112,184,176,248],[184,184,248,248]],"answer":2}
```

### task_games__reversi__legal_destination_count / single / answer_only / sample 6155938070143178

- `instance_seed`: `6155938070143178`
- `word_count`: `60`
- `body_word_count`: `46`

```text
The image shows a 6 by 6 Reversi board with black and white discs. Black is to move. A legal move is an empty square that brackets one or more opponent discs in at least one straight line. Count the legal move squares available to Black.
Answer format: set "answer" to the count of legal moves.
Example JSON:
{"answer":2}
```

### task_games__reversi__marked_move_flip_count / single / answer_and_annotation / sample 2466342950624372

- `instance_seed`: `2466342950624372`
- `word_count`: `111`
- `body_word_count`: `65`

```text
The figure shows an 8 by 8 Reversi board with black and white discs. White is to move. A legal move is an empty square that brackets one or more opponent discs in at least one straight line. The red marked empty square is the marked move. The marked move flips every bracketed opponent disc. How many opponent discs would flip after the marked move?
Annotation format: set "annotation" to one pixel point [x,y] at the center of every disc flipped by the marked move.
Answer format: set "answer" to the count of discs flipped by the marked move.
Example JSON:
{"annotation":[[144,216],[216,216],[288,216]],"answer":3}
```

### task_games__reversi__marked_move_flip_count / single / answer_only / sample 2466342950624372

- `instance_seed`: `2466342950624372`
- `word_count`: `83`
- `body_word_count`: `65`

```text
The figure shows an 8 by 8 Reversi board with black and white discs. White is to move. A legal move is an empty square that brackets one or more opponent discs in at least one straight line. The red marked empty square is the marked move. The marked move flips every bracketed opponent disc. How many opponent discs would flip after the marked move?
Answer format: set "answer" to the count of discs flipped by the marked move.
Example JSON:
{"answer":3}
```

### task_games__rhythm__earliest_hit_lane_label / single / answer_and_annotation / sample 415062412905858

- `instance_seed`: `415062412905858`
- `word_count`: `95`
- `body_word_count`: `53`

```text
The scene shows a rhythm-game lane grid with colored falling notes, lane numbers, and a bottom hit line. Notes fall one row per beat. The bottom line is the hit line. A long vertical note counts as one note. Report the lane number of the first note to arrive at the hit line.
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the note that reaches the hit line earliest.
Answer format: set "answer" to the winning lane number as an integer.
Example JSON:
{"annotation":[260,432,341,479],"answer":4}
```

### task_games__rhythm__earliest_hit_lane_label / single / answer_only / sample 415062412905858

- `instance_seed`: `415062412905858`
- `word_count`: `69`
- `body_word_count`: `53`

```text
The scene shows a rhythm-game lane grid with colored falling notes, lane numbers, and a bottom hit line. Notes fall one row per beat. The bottom line is the hit line. A long vertical note counts as one note. Report the lane number of the first note to arrive at the hit line.
Answer format: set "answer" to the winning lane number as an integer.
Example JSON:
{"answer":4}
```

### task_games__rhythm__lane_note_count / single / answer_and_annotation / sample 1970285545540495

- `instance_seed`: `1970285545540495`
- `word_count`: `70`
- `body_word_count`: `26`

```text
The visual shows a rhythm-game lane grid with colored falling notes, lane numbers, and a bottom hit line. Count all visible note objects in lane 5.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] around all note objects in the specified lane.
Answer format: set "answer" to the integer count.
Example JSON:
{"annotation":[[260,498,341,545],[260,432,341,479],[260,302,341,349]],"answer":3}
```

### task_games__rhythm__lane_note_count / single / answer_only / sample 1970285545540495

- `instance_seed`: `1970285545540495`
- `word_count`: `39`
- `body_word_count`: `26`

```text
The visual shows a rhythm-game lane grid with colored falling notes, lane numbers, and a bottom hit line. Count all visible note objects in lane 5.
Final answer format: set "answer" to the integer count.
Example JSON:
{"answer":3}
```

### task_games__rhythm__lane_note_score_value / single / answer_and_annotation / sample 3052791030976938

- `instance_seed`: `3052791030976938`
- `word_count`: `89`
- `body_word_count`: `42`

```text
This scene shows a rhythm-game lane grid with colored falling notes, lane numbers, and a bottom hit line. What is the total score for lane 5? Use the side score palette value for each note object. A long vertical note counts once.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] around every note object in the specified lane that is included in the score.
Answer format: set "answer" to the total integer score.
Example JSON:
{"annotation":[[260,498,341,545],[260,432,341,479]],"answer":7}
```

### task_games__rhythm__lane_note_score_value / single / answer_only / sample 3052791030976938

- `instance_seed`: `3052791030976938`
- `word_count`: `56`
- `body_word_count`: `42`

```text
This scene shows a rhythm-game lane grid with colored falling notes, lane numbers, and a bottom hit line. What is the total score for lane 5? Use the side score palette value for each note object. A long vertical note counts once.
Required answer format: set "answer" to the total integer score.
Example JSON:
{"answer":7}
```

### task_games__rhythm__most_notes_lane_label / single / answer_and_annotation / sample 7477780222553963

- `instance_seed`: `7477780222553963`
- `word_count`: `80`
- `body_word_count`: `28`

```text
This scene shows a rhythm-game lane grid with colored falling notes, lane numbers, and a bottom hit line. Which lane contains the highest number of visible note objects?
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] around all note objects in the lane with the most note objects.
Answer format: set "answer" to the winning lane number as an integer.
Example JSON:
{"annotation":[[260,498,341,545],[260,432,341,479],[260,302,341,349]],"answer":3}
```

### task_games__rhythm__most_notes_lane_label / single / answer_only / sample 7477780222553963

- `instance_seed`: `7477780222553963`
- `word_count`: `44`
- `body_word_count`: `28`

```text
This scene shows a rhythm-game lane grid with colored falling notes, lane numbers, and a bottom hit line. Which lane contains the highest number of visible note objects?
Answer format: set "answer" to the winning lane number as an integer.
Example JSON:
{"answer":3}
```

### task_games__rule_override_board__line_result_count / line_override_loss_count / answer_and_annotation / sample 5935758252441833

- `instance_seed`: `5935758252441833`
- `word_count`: `87`
- `body_word_count`: `32`

```text
The image shows several small labeled game boards. Rule: For the target player, making a full row, column, or diagonal loses; otherwise that player wins. How many mini-boards are losses for O?
Annotation format: set "annotation" to bounding boxes [x0,y0,x1,y1] around every counted mini-board where the target player loses under the stated rule; use [] if none.
Answer format: set "answer" to the integer number of target-player losses.
Example JSON:
{"annotation":[[80,170,258,378],[286,170,464,378],[492,170,670,378]],"answer":3}
```

### task_games__rule_override_board__line_result_count / line_override_loss_count / answer_only / sample 5935758252441833

- `instance_seed`: `5935758252441833`
- `word_count`: `47`
- `body_word_count`: `32`

```text
The image shows several small labeled game boards. Rule: For the target player, making a full row, column, or diagonal loses; otherwise that player wins. How many mini-boards are losses for O?
Answer format: set "answer" to the integer number of target-player losses.
Example JSON:
{"answer":3}
```

### task_games__rule_override_board__line_result_count / line_override_win_count / answer_and_annotation / sample 3570396316012371

- `instance_seed`: `3570396316012371`
- `word_count`: `91`
- `body_word_count`: `34`

```text
The board display shows several small labeled game boards. How many labeled boards are wins for O? Rule: For the target player, making a full row, column, or diagonal loses; otherwise that player wins.
Required annotation format: set "annotation" to bounding boxes [x0,y0,x1,y1] around every counted mini-board where the target player wins under the stated rule; use [] if none.
Required answer format: set "answer" to the integer number of target-player wins.
Example JSON:
{"annotation":[[80,170,258,378],[286,170,464,378],[492,170,670,378]],"answer":3}
```

### task_games__rule_override_board__line_result_count / line_override_win_count / answer_only / sample 3570396316012371

- `instance_seed`: `3570396316012371`
- `word_count`: `50`
- `body_word_count`: `34`

```text
The board display shows several small labeled game boards. How many labeled boards are wins for O? Rule: For the target player, making a full row, column, or diagonal loses; otherwise that player wins.
Required answer format: set "answer" to the integer number of target-player wins.
Example JSON:
{"answer":3}
```

### task_games__rule_override_board__piece_result_count / piece_override_loss_count / answer_and_annotation / sample 5977831699860498

- `instance_seed`: `5977831699860498`
- `word_count`: `88`
- `body_word_count`: `33`

```text
The figure shows several small labeled game boards. How many labeled boards are losses for White? Rule: For the target player, having fewer pieces than the other player wins; having more pieces loses.
Annotation format: set "annotation" to bounding boxes [x0,y0,x1,y1] around every counted mini-board where the target player loses under the stated rule; use [] if none.
Answer format: set "answer" to the integer number of target-player losses.
Example JSON:
{"annotation":[[80,170,258,378],[286,170,464,378],[492,170,670,378]],"answer":3}
```

### task_games__rule_override_board__piece_result_count / piece_override_loss_count / answer_only / sample 5977831699860498

- `instance_seed`: `5977831699860498`
- `word_count`: `49`
- `body_word_count`: `33`

```text
The figure shows several small labeled game boards. How many labeled boards are losses for White? Rule: For the target player, having fewer pieces than the other player wins; having more pieces loses.
Required answer format: set "answer" to the integer number of target-player losses.
Example JSON:
{"answer":3}
```

### task_games__rule_override_board__piece_result_count / piece_override_win_count / answer_and_annotation / sample 8401595877411480

- `instance_seed`: `8401595877411480`
- `word_count`: `86`
- `body_word_count`: `31`

```text
The image shows several small labeled game boards. How many boards does Black win? Rule: For the target player, having fewer pieces than the other player wins; having more pieces loses.
Annotation format: set "annotation" to bounding boxes [x0,y0,x1,y1] around every counted mini-board where the target player wins under the stated rule; use [] if none.
Answer format: set "answer" to the integer number of target-player wins.
Example JSON:
{"annotation":[[80,170,258,378],[286,170,464,378],[492,170,670,378]],"answer":3}
```

### task_games__rule_override_board__piece_result_count / piece_override_win_count / answer_only / sample 8401595877411480

- `instance_seed`: `8401595877411480`
- `word_count`: `46`
- `body_word_count`: `31`

```text
The image shows several small labeled game boards. How many boards does Black win? Rule: For the target player, having fewer pieces than the other player wins; having more pieces loses.
Answer format: set "answer" to the integer number of target-player wins.
Example JSON:
{"answer":3}
```

### task_games__sixteen_soldiers__marked_piece_capture_count / single / answer_and_annotation / sample 2746192219759138

- `instance_seed`: `2746192219759138`
- `word_count`: `125`
- `body_word_count`: `63`

```text
The scene shows a Sixteen Soldiers board with red and blue pieces on points connected by drawn movement lines. A capture is possible when the piece marked with an X can jump along one drawn straight line over an adjacent opponent piece and land on the empty point immediately beyond it. How many immediate captures does the piece marked with an X have?
Annotation format: set "annotation" to [x, y] pixel points at the centers of every opponent piece that the X-marked piece can capture immediately; use an empty array if there are none.
Answer format: set "answer" to the number of immediate captures available to the piece marked with an X.
Example JSON:
{"annotation":[[180.0,220.0],[268.0,308.0]],"answer":2}
```

### task_games__sixteen_soldiers__marked_piece_capture_count / single / answer_only / sample 2746192219759138

- `instance_seed`: `2746192219759138`
- `word_count`: `86`
- `body_word_count`: `63`

```text
The scene shows a Sixteen Soldiers board with red and blue pieces on points connected by drawn movement lines. A capture is possible when the piece marked with an X can jump along one drawn straight line over an adjacent opponent piece and land on the empty point immediately beyond it. How many immediate captures does the piece marked with an X have?
Final answer format: set "answer" to the number of immediate captures available to the piece marked with an X.
Example JSON:
{"answer":2}
```

### task_games__sixteen_soldiers__marked_piece_destination_count / single / answer_and_annotation / sample 135086359829622

- `instance_seed`: `135086359829622`
- `word_count`: `118`
- `body_word_count`: `50`

```text
The visual shows a Sixteen Soldiers board with red and blue pieces on points connected by drawn movement lines. A simple move goes along one drawn line to an adjacent empty point. Do not count jumps or captures. How many adjacent empty points can the X-marked piece reach without jumping?
Required annotation format: set "annotation" to [x, y] pixel points at the centers of every one-step adjacent empty destination for the piece marked with an X; use an empty array when the count is 0.
Required answer format: set "answer" to the number of one-step adjacent empty destinations for the piece marked with an X.
Example JSON:
{"annotation":[[180.0,220.0],[268.0,308.0]],"answer":2}
```

### task_games__sixteen_soldiers__marked_piece_destination_count / single / answer_only / sample 135086359829622

- `instance_seed`: `135086359829622`
- `word_count`: `74`
- `body_word_count`: `50`

```text
The visual shows a Sixteen Soldiers board with red and blue pieces on points connected by drawn movement lines. A simple move goes along one drawn line to an adjacent empty point. Do not count jumps or captures. How many adjacent empty points can the X-marked piece reach without jumping?
Required answer format: set "answer" to the number of one-step adjacent empty destinations for the piece marked with an X.
Example JSON:
{"answer":2}
```

### task_games__sliding_block__block_orientation_count / horizontal_block_count / answer_and_annotation / sample 6528769451256456

- `instance_seed`: `6528769451256456`
- `word_count`: `61`
- `body_word_count`: `17`

```text
The visual shows a sliding-block puzzle board with labeled rectangular blocks. How many blocks have horizontal orientation?
Annotation format: set "annotation" to a JSON array of pixel-space bounding boxes [x0,y0,x1,y1] for the blocks matching the requested orientation.
Answer format: set "answer" to the integer count.
Example JSON:
{"annotation":[[110,150,235,220],[310,250,430,320]],"answer":2}
```

### task_games__sliding_block__block_orientation_count / horizontal_block_count / answer_only / sample 6528769451256456

- `instance_seed`: `6528769451256456`
- `word_count`: `30`
- `body_word_count`: `17`

```text
The visual shows a sliding-block puzzle board with labeled rectangular blocks. How many blocks have horizontal orientation?
Required answer format: set "answer" to the integer count.
Example JSON:
{"answer":2}
```

### task_games__sliding_block__block_orientation_count / vertical_block_count / answer_and_annotation / sample 1871204425237054

- `instance_seed`: `1871204425237054`
- `word_count`: `67`
- `body_word_count`: `22`

```text
The scene shows a sliding-block puzzle board with labeled rectangular blocks. Count the labeled blocks that are taller than they are wide.
Final answer format: set "answer" to the integer count.
Annotation format: set "annotation" to a JSON array of pixel-space bounding boxes [x0,y0,x1,y1] for the blocks matching the requested orientation.
Example JSON:
{"annotation":[[110,150,235,220],[310,250,430,320]],"answer":2}
```

### task_games__sliding_block__block_orientation_count / vertical_block_count / answer_only / sample 1871204425237054

- `instance_seed`: `1871204425237054`
- `word_count`: `35`
- `body_word_count`: `22`

```text
The scene shows a sliding-block puzzle board with labeled rectangular blocks. Count the labeled blocks that are taller than they are wide.
Required answer format: set "answer" to the integer count.
Example JSON:
{"answer":2}
```

### task_games__sliding_block__movable_block_count / single / answer_and_annotation / sample 3649472932990206

- `instance_seed`: `3649472932990206`
- `word_count`: `86`
- `body_word_count`: `44`

```text
The visual shows a sliding-block puzzle board with labeled rectangular blocks. Using the rule that horizontal blocks move left/right and vertical blocks move up/down, how many labeled blocks can slide at least one cell without leaving the board or overlapping another block?
Final answer format: set "answer" to the integer count.
Annotation format: set "annotation" to a JSON array of pixel-space bounding boxes [x0,y0,x1,y1] for the movable blocks.
Example JSON:
{"annotation":[[110,150,195,235],[310,250,390,335]],"answer":2}
```

### task_games__sliding_block__movable_block_count / single / answer_only / sample 3649472932990206

- `instance_seed`: `3649472932990206`
- `word_count`: `56`
- `body_word_count`: `44`

```text
The visual shows a sliding-block puzzle board with labeled rectangular blocks. Using the rule that horizontal blocks move left/right and vertical blocks move up/down, how many labeled blocks can slide at least one cell without leaving the board or overlapping another block?
Answer format: set "answer" to the integer count.
Example JSON:
{"answer":2}
```

### task_games__sliding_block__sliding_block_blocker_count / single / answer_and_annotation / sample 868361395634868

- `instance_seed`: `868361395634868`
- `word_count`: `76`
- `body_word_count`: `34`

```text
The image shows a sliding-block puzzle board with labeled rectangular blocks, an exit arrow, and one red target block labeled T. How many blocks are in the red target block T's direct exit path?
Final answer format: set "answer" to the integer count.
Annotation format: set "annotation" to a JSON array of pixel-space bounding boxes [x0,y0,x1,y1] for the blocking blocks.
Example JSON:
{"annotation":[[120,160,210,245],[225,160,315,245]],"answer":2}
```

### task_games__sliding_block__sliding_block_blocker_count / single / answer_only / sample 868361395634868

- `instance_seed`: `868361395634868`
- `word_count`: `46`
- `body_word_count`: `42`

```text
The image shows a sliding-block puzzle board with labeled rectangular blocks, an exit arrow, and one red target block labeled T. How many blocks are in the red target block T's direct exit path?
Answer field: set "answer" to the integer count.
Example JSON:
{"answer":2}
```

### task_games__sliding_block__sliding_block_move_result_label / single / answer_and_annotation / sample 7801928296850567

- `instance_seed`: `7801928296850567`
- `word_count`: `95`
- `body_word_count`: `37`

```text
This scene shows a sliding-block puzzle board with labeled rectangular blocks and four final-board options. Use the original board, perform these slides in order: 1. block E slides 2 cells right. Which option is the resulting board?
Annotation format: set "annotation" to a JSON object with keys "source_board" and "selected_option"; each value is an image-pixel bounding box [x0,y0,x1,y1] for the original board and the selected option panel.
Answer format: set "answer" to only the selected option letter.
Example JSON:
{"annotation":{"source_board":[80,120,300,340],"selected_option":[430,500,650,680]},"answer":"B"}
```

### task_games__sliding_block__sliding_block_move_result_label / single / answer_only / sample 7801928296850567

- `instance_seed`: `7801928296850567`
- `word_count`: `51`
- `body_word_count`: `37`

```text
This scene shows a sliding-block puzzle board with labeled rectangular blocks and four final-board options. Use the original board, perform these slides in order: 1. block E slides 2 cells right. Which option is the resulting board?
Answer format: set "answer" to only the selected option letter.
Example JSON:
{"answer":"B"}
```

### task_games__slot_machine__paytable_score_value / single / answer_and_annotation / sample 8363672966029897

- `instance_seed`: `8363672966029897`
- `word_count`: `113`
- `body_word_count`: `47`

```text
The scene shows a toy slot machine with three reels, three visible rows, simple symbol icons, and a side paytable of symbol scores. Use the side paytable. For every full row or long diagonal with three matching symbols, add that symbol's score. What total score is shown?
Final answer format: set "answer" to the integer total score from the side paytable.
Annotation format: set "annotation" to a JSON array of image-pixel segments, each using two endpoint points [x, y] in [[x0, y0], [x1, y1]] form; include one segment along each winning row or diagonal payline that contributes to the score.
Example JSON:
{"annotation":[[[250,250],[510,250]],[[250,470],[510,250]]],"answer":14}
```

### task_games__slot_machine__paytable_score_value / single / answer_only / sample 8363672966029897

- `instance_seed`: `8363672966029897`
- `word_count`: `64`
- `body_word_count`: `47`

```text
The scene shows a toy slot machine with three reels, three visible rows, simple symbol icons, and a side paytable of symbol scores. Use the side paytable. For every full row or long diagonal with three matching symbols, add that symbol's score. What total score is shown?
Answer format: set "answer" to the integer total score from the side paytable.
Example JSON:
{"answer":14}
```

### task_games__slot_machine__reel_completion_label / single / answer_and_annotation / sample 3321263263953760

- `instance_seed`: `3321263263953760`
- `word_count`: `75`
- `body_word_count`: `39`

```text
The visual shows a toy slot machine with two visible reels and four labeled options for the third reel. Only rows and the two long diagonals count as paylines. Which option for the third reel creates one matching-symbol payline?
Annotation format: set "annotation" to the image-pixel bounding box [x0, y0, x1, y1] around the selected third-reel option.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[620,170,746,440],"answer":"B"}
```

### task_games__slot_machine__reel_completion_label / single / answer_only / sample 3321263263953760

- `instance_seed`: `3321263263953760`
- `word_count`: `53`
- `body_word_count`: `39`

```text
The visual shows a toy slot machine with two visible reels and four labeled options for the third reel. Only rows and the two long diagonals count as paylines. Which option for the third reel creates one matching-symbol payline?
Required answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"B"}
```

### task_games__slot_machine__winning_payline_count / single / answer_and_annotation / sample 1332719529870376

- `instance_seed`: `1332719529870376`
- `word_count`: `102`
- `body_word_count`: `39`

```text
The image shows a toy slot machine with three reels, three visible rows, and simple symbol icons. How many paylines win, where paylines are the full rows plus the two long diagonals and a win has three identical symbols?
Annotation format: set "annotation" to a JSON array of image-pixel segments, each using two endpoint points [x, y] in [[x0, y0], [x1, y1]] form; include one segment along each winning row or diagonal payline; use [] if no payline wins.
Answer format: set "answer" to the integer count of winning paylines.
Example JSON:
{"annotation":[[[250,250],[510,250]],[[250,470],[510,250]]],"answer":2}
```

### task_games__slot_machine__winning_payline_count / single / answer_only / sample 1332719529870376

- `instance_seed`: `1332719529870376`
- `word_count`: `55`
- `body_word_count`: `39`

```text
The image shows a toy slot machine with three reels, three visible rows, and simple symbol icons. How many paylines win, where paylines are the full rows plus the two long diagonals and a win has three identical symbols?
Required answer format: set "answer" to the integer count of winning paylines.
Example JSON:
{"answer":2}
```

### task_games__snake__path_outcome_option_label / single / answer_and_annotation / sample 3245331601158289

- `instance_seed`: `3245331601158289`
- `word_count`: `173`
- `body_word_count`: `102`

```text
The visual shows a Snake game board with a yellow snake head, connected body cells, red food, and gray wall cells. A move is safe when the head stays inside the board and does not enter the snake body or a gray wall cell. Moving onto red food counts as safe. The planned moves are 1. RIGHT, 2. LEFT, 3. UP, 4. DOWN. Choose the labeled option in the image that matches the result: a marked point cell or GAME OVER. For a game-over result, use boxes around the visible in-board head path cells up to the hit cell or board edge.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] around the in-board cells the head traverses until the result; for an off-board hit, use the visible path cells up to the board edge.
Answer format: set "answer" to the option letter shown in the image, one of "A", "B", "C", or "D".
Example JSON:
{"annotation":[[338,332,410,404],[410,332,482,404],[482,332,554,404]],"answer":"B"}
```

### task_games__snake__path_outcome_option_label / single / answer_only / sample 3245331601158289

- `instance_seed`: `3245331601158289`
- `word_count`: `126`
- `body_word_count`: `102`

```text
The visual shows a Snake game board with a yellow snake head, connected body cells, red food, and gray wall cells. A move is safe when the head stays inside the board and does not enter the snake body or a gray wall cell. Moving onto red food counts as safe. The planned moves are 1. RIGHT, 2. LEFT, 3. UP, 4. DOWN. Choose the labeled option in the image that matches the result: a marked point cell or GAME OVER. For a game-over result, use boxes around the visible in-board head path cells up to the hit cell or board edge.
Required answer format: set "answer" to the option letter shown in the image, one of "A", "B", "C", or "D".
Example JSON:
{"answer":"B"}
```

### task_games__snake__safe_direction_count / single / answer_and_annotation / sample 420784345678859

- `instance_seed`: `420784345678859`
- `word_count`: `122`
- `body_word_count`: `64`

```text
The visual shows a Snake game board with a yellow snake head, connected body cells, red food, and gray wall cells. A move is safe when the head stays inside the board and does not enter the snake body or a gray wall cell. Moving onto red food counts as safe. How many of the four next moves (up, down, left, right) are safe?
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] around each destination cell that is safe for the next move; include the food cell if it is safely reachable.
Answer format: set "answer" to the number of safe next-move directions as an integer.
Example JSON:
{"annotation":[[338,332,410,404],[410,332,482,404]],"answer":2}
```

### task_games__snake__safe_direction_count / single / answer_only / sample 420784345678859

- `instance_seed`: `420784345678859`
- `word_count`: `83`
- `body_word_count`: `64`

```text
The visual shows a Snake game board with a yellow snake head, connected body cells, red food, and gray wall cells. A move is safe when the head stays inside the board and does not enter the snake body or a gray wall cell. Moving onto red food counts as safe. How many of the four next moves (up, down, left, right) are safe?
Required answer format: set "answer" to the number of safe next-move directions as an integer.
Example JSON:
{"answer":2}
```

### task_games__snake__snake_length_count / single / answer_and_annotation / sample 3515251134387541

- `instance_seed`: `3515251134387541`
- `word_count`: `109`
- `body_word_count`: `36`

```text
The image shows a Snake game board with a yellow snake head, connected body cells, red food, and gray wall cells. Count every visible snake cell, including the head, body, and tail. What is the total?
Required annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] around every snake-occupied cell, including the head and tail.
Required answer format: set "answer" to the total number of snake-occupied cells as an integer.
Example JSON:
{"annotation":[[338,332,410,404],[410,332,482,404],[482,332,554,404],[554,332,626,404],[626,332,698,404],[698,332,770,404],[770,332,842,404],[842,332,914,404]],"answer":8}
```

### task_games__snake__snake_length_count / single / answer_only / sample 3515251134387541

- `instance_seed`: `3515251134387541`
- `word_count`: `54`
- `body_word_count`: `36`

```text
The image shows a Snake game board with a yellow snake head, connected body cells, red food, and gray wall cells. Count every visible snake cell, including the head, body, and tail. What is the total?
Answer format: set "answer" to the total number of snake-occupied cells as an integer.
Example JSON:
{"answer":8}
```

### task_games__snakes_ladders__move_outcome_value / single / answer_and_annotation / sample 1560067821300292

- `instance_seed`: `1560067821300292`
- `word_count`: `164`
- `body_word_count`: `111`

```text
The scene shows a numbered Snakes and Ladders board with one token and visible snakes and ladders. A move advances the token by the selected die value, then immediately follows a ladder upward or a snake downward if the landing square is the start of one. A ladder starts at its lower square and ends at the arrowhead on the higher square; a snake starts at its head and ends at its pointed tail on the lower square. If a die roll would move past the final square, the token stays on its current square for that roll. Move once using the shown die; what square is the token on afterward?
Annotation format: set "annotation" to a JSON object mapping start_square and end_square to bounding boxes [x0, y0, x1, y1].
Answer format: set "answer" to the final square number after the shown die roll and any snake or ladder.
Example JSON:
{"annotation":{"start_square":[88,682,178,772],"end_square":[462,398,552,488]},"answer":31}
```

### task_games__snakes_ladders__move_outcome_value / single / answer_only / sample 1560067821300292

- `instance_seed`: `1560067821300292`
- `word_count`: `134`
- `body_word_count`: `111`

```text
The scene shows a numbered Snakes and Ladders board with one token and visible snakes and ladders. A move advances the token by the selected die value, then immediately follows a ladder upward or a snake downward if the landing square is the start of one. A ladder starts at its lower square and ends at the arrowhead on the higher square; a snake starts at its head and ends at its pointed tail on the lower square. If a die roll would move past the final square, the token stays on its current square for that roll. Move once using the shown die; what square is the token on afterward?
Answer format: set "answer" to the final square number after the shown die roll and any snake or ladder.
Example JSON:
{"answer":31}
```

### task_games__snakes_ladders__remaining_to_finish_value / single / answer_and_annotation / sample 789880838881250

- `instance_seed`: `789880838881250`
- `word_count`: `78`
- `body_word_count`: `29`

```text
The scene shows a numbered Snakes and Ladders board with one token and visible snakes and ladders. How many squares remain from the token's square to the final square?
Final answer format: set "answer" to the final square number minus the token's square number.
Annotation format: set "annotation" to a JSON object mapping token_square and finish_square to bounding boxes [x0, y0, x1, y1].
Example JSON:
{"annotation":{"token_square":[356,598,446,688],"finish_square":[542,132,632,222]},"answer":12}
```

### task_games__snakes_ladders__remaining_to_finish_value / single / answer_only / sample 789880838881250

- `instance_seed`: `789880838881250`
- `word_count`: `47`
- `body_word_count`: `29`

```text
The scene shows a numbered Snakes and Ladders board with one token and visible snakes and ladders. How many squares remain from the token's square to the final square?
Answer format: set "answer" to the final square number minus the token's square number.
Example JSON:
{"answer":12}
```

### task_games__snakes_ladders__special_square_count / ladder_count / answer_and_annotation / sample 5493802715699345

- `instance_seed`: `5493802715699345`
- `word_count`: `69`
- `body_word_count`: `26`

```text
This scene shows a numbered Snakes and Ladders board with one token and visible snakes and ladders. How many ladder starts are shown on the board?
Annotation format: set "annotation" to a JSON array of bounding boxes [x0,y0,x1,y1] around every counted ladder-start square.
Answer format: set "answer" to the number of visible ladders.
Example JSON:
{"annotation":[[188,682,278,772],[374,496,464,586]],"answer":2}
```

### task_games__snakes_ladders__special_square_count / ladder_count / answer_only / sample 5493802715699345

- `instance_seed`: `5493802715699345`
- `word_count`: `40`
- `body_word_count`: `26`

```text
This scene shows a numbered Snakes and Ladders board with one token and visible snakes and ladders. How many ladder starts are shown on the board?
Answer format: set "answer" to the number of visible ladders.
Example JSON:
{"answer":2}
```

### task_games__snakes_ladders__special_square_count / snake_count / answer_and_annotation / sample 726239787484687

- `instance_seed`: `726239787484687`
- `word_count`: `68`
- `body_word_count`: `25`

```text
The image shows a numbered Snakes and Ladders board with one token and visible snakes and ladders. How many snakes are visible on the board?
Annotation format: set "annotation" to a JSON array of bounding boxes [x0,y0,x1,y1] around every counted snake-head square.
Answer format: set "answer" to the number of visible snakes.
Example JSON:
{"annotation":[[188,682,278,772],[374,496,464,586]],"answer":2}
```

### task_games__snakes_ladders__special_square_count / snake_count / answer_only / sample 726239787484687

- `instance_seed`: `726239787484687`
- `word_count`: `39`
- `body_word_count`: `25`

```text
The image shows a numbered Snakes and Ladders board with one token and visible snakes and ladders. How many snakes are visible on the board?
Answer format: set "answer" to the number of visible snakes.
Example JSON:
{"answer":2}
```

### task_games__sokoban__box_goal_status_count / box_off_goal_count / answer_and_annotation / sample 4170072641838226

- `instance_seed`: `4170072641838226`
- `word_count`: `95`
- `body_word_count`: `43`

```text
This scene shows a Sokoban board with walls, a player, colored boxes, and colored goal dots; a box on its matching goal has the goal dot drawn on top of the box. How many boxes are not on their matching colored goal dots?
Annotation format: set "annotation" to a JSON array of image-pixel box-cell bounding boxes [x0,y0,x1,y1], one for each counted box; use [] if none are counted.
Answer format: set "answer" to the number of boxes satisfying the question.
Example JSON:
{"annotation":[[180,160,232,212],[300,220,352,272]],"answer":2}
```

### task_games__sokoban__box_goal_status_count / box_off_goal_count / answer_only / sample 4170072641838226

- `instance_seed`: `4170072641838226`
- `word_count`: `60`
- `body_word_count`: `43`

```text
This scene shows a Sokoban board with walls, a player, colored boxes, and colored goal dots; a box on its matching goal has the goal dot drawn on top of the box. How many boxes are not on their matching colored goal dots?
Final answer format: set "answer" to the number of boxes satisfying the question.
Example JSON:
{"answer":2}
```

### task_games__sokoban__box_goal_status_count / box_on_goal_count / answer_and_annotation / sample 140370942672761

- `instance_seed`: `140370942672761`
- `word_count`: `96`
- `body_word_count`: `44`

```text
The visual shows a Sokoban board with walls, a player, colored boxes, and colored goal dots; a box on its matching goal has the goal dot drawn on top of the box. How many crates have been pushed onto their matching colored goal dots?
Annotation format: set "annotation" to a JSON array of image-pixel box-cell bounding boxes [x0,y0,x1,y1], one for each counted box; use [] if none are counted.
Answer format: set "answer" to the number of boxes satisfying the question.
Example JSON:
{"annotation":[[180,160,232,212],[300,220,352,272]],"answer":2}
```

### task_games__sokoban__box_goal_status_count / box_on_goal_count / answer_only / sample 140370942672761

- `instance_seed`: `140370942672761`
- `word_count`: `61`
- `body_word_count`: `44`

```text
The visual shows a Sokoban board with walls, a player, colored boxes, and colored goal dots; a box on its matching goal has the goal dot drawn on top of the box. How many crates have been pushed onto their matching colored goal dots?
Required answer format: set "answer" to the number of boxes satisfying the question.
Example JSON:
{"answer":2}
```

### task_games__sokoban__closest_box_goal_label / single / answer_and_annotation / sample 2044157018432306

- `instance_seed`: `2044157018432306`
- `word_count`: `86`
- `body_word_count`: `50`

```text
The image shows a Sokoban board with walls, a player, lettered colored boxes, and matching colored goal dots; no box is already on its matching goal. Compare each labeled box with its same-colored goal dot. Which box has the smallest Manhattan distance when walls, boxes, and other objects are ignored?
Annotation format: set "annotation" to the selected box-cell bounding box as [x0,y0,x1,y1] in image pixels.
Answer format: set "answer" to the selected box letter.
Example JSON:
{"annotation":[220,180,280,240],"answer":"B"}
```

### task_games__sokoban__closest_box_goal_label / single / answer_only / sample 2044157018432306

- `instance_seed`: `2044157018432306`
- `word_count`: `64`
- `body_word_count`: `50`

```text
The image shows a Sokoban board with walls, a player, lettered colored boxes, and matching colored goal dots; no box is already on its matching goal. Compare each labeled box with its same-colored goal dot. Which box has the smallest Manhattan distance when walls, boxes, and other objects are ignored?
Required answer format: set "answer" to the selected box letter.
Example JSON:
{"answer":"B"}
```

### task_games__sokoban__push_stand_cell_label / single / answer_and_annotation / sample 7045093931512217

- `instance_seed`: `7045093931512217`
- `word_count`: `86`
- `body_word_count`: `47`

```text
The scene shows a Sokoban board with walls, a player, colored boxes, matching colored goal dots, and four labeled candidate standing squares around one box. Which labeled player position lets the brown [#887044] box be pushed in a straight line to its matching brown [#887044] goal dot?
Required annotation format: set "annotation" to the selected standing-square cell bounding box as [x0,y0,x1,y1] in image pixels.
Required answer format: set "answer" to the selected standing-square letter.
Example JSON:
{"annotation":[160,220,212,272],"answer":"C"}
```

### task_games__sokoban__push_stand_cell_label / single / answer_only / sample 7045093931512217

- `instance_seed`: `7045093931512217`
- `word_count`: `60`
- `body_word_count`: `47`

```text
The scene shows a Sokoban board with walls, a player, colored boxes, matching colored goal dots, and four labeled candidate standing squares around one box. Which labeled player position lets the brown [#887044] box be pushed in a straight line to its matching brown [#887044] goal dot?
Answer format: set "answer" to the selected standing-square letter.
Example JSON:
{"answer":"B"}
```

### task_games__solitaire__cascade_card_at_depth_label / single / answer_and_annotation / sample 1728887031953851

- `instance_seed`: `1728887031953851`
- `word_count`: `65`
- `body_word_count`: `24`

```text
The visual shows solitaire columns and foundation piles. Which labeled option matches the card at visible position 1st from the top of column 8?
Annotation format: set "annotation" to one [x, y] image-pixel point on the visible part of the target card in the column.
Answer format: set "answer" to only the option letter showing the requested card.
Example JSON:
{"annotation":[323,306],"answer":"B"}
```

### task_games__solitaire__cascade_card_at_depth_label / single / answer_only / sample 1728887031953851

- `instance_seed`: `1728887031953851`
- `word_count`: `42`
- `body_word_count`: `24`

```text
The visual shows solitaire columns and foundation piles. Which labeled option matches the card at visible position 1st from the top of column 8?
Final answer format: set "answer" to only the option letter showing the requested card.
Example JSON:
{"answer":"B"}
```

### task_games__solitaire__column_card_count_value / single / answer_and_annotation / sample 4949750040575384

- `instance_seed`: `4949750040575384`
- `word_count`: `70`
- `body_word_count`: `19`

```text
This solitaire layout shows solitaire columns and foundation piles. What is the number of visible cards in column 5?
Final answer format: set "answer" to the number of visible cards in the requested column.
Annotation format: set "annotation" to an array of [x, y] image-pixel points, one point on the visible part of each card in the requested column.
Example JSON:
{"annotation":[[287,236],[287,268],[287,336]],"answer":3}
```

### task_games__solitaire__column_card_count_value / single / answer_only / sample 4949750040575384

- `instance_seed`: `4949750040575384`
- `word_count`: `38`
- `body_word_count`: `19`

```text
This solitaire layout shows solitaire columns and foundation piles. What is the number of visible cards in column 5?
Required answer format: set "answer" to the number of visible cards in the requested column.
Example JSON:
{"answer":3}
```

### task_games__solitaire__foundation_ready_count / single / answer_and_annotation / sample 7742086234691027

- `instance_seed`: `7742086234691027`
- `word_count`: `109`
- `body_word_count`: `49`

```text
The image shows solitaire columns and foundation piles. A card can move to a foundation only if it matches that foundation suit and is exactly one rank above the foundation's current top card; an Ace can move to an empty foundation. How many exposed cards are legal foundation moves?
Annotation format: set "annotation" to an array of bounding boxes [x0, y0, x1, y1] for the counted exposed cards; use an empty array when no cards are counted.
Answer format: set "answer" to the number of exposed column cards that can move to a foundation pile now.
Example JSON:
{"annotation":[[250,220,324,324],[342,220,416,324]],"answer":2}
```

### task_games__solitaire__foundation_ready_count / single / answer_only / sample 7742086234691027

- `instance_seed`: `7742086234691027`
- `word_count`: `72`
- `body_word_count`: `49`

```text
The image shows solitaire columns and foundation piles. A card can move to a foundation only if it matches that foundation suit and is exactly one rank above the foundation's current top card; an Ace can move to an empty foundation. How many exposed cards are legal foundation moves?
Answer format: set "answer" to the number of exposed column cards that can move to a foundation pile now.
Example JSON:
{"answer":2}
```

### task_games__solitaire__move_legality_label / single / answer_and_annotation / sample 5292496676928945

- `instance_seed`: `5292496676928945`
- `word_count`: `126`
- `body_word_count`: `76`

```text
The solitaire layout shows solitaire columns and foundation piles. For moves between columns, a card can be placed on another column card only if the target is exactly one rank higher and the opposite color. A card can move to a foundation only if it matches that foundation suit and is exactly one rank above the foundation's current top card; an Ace can move to an empty foundation. Which option letter shows a legal solitaire move?
Required annotation format: set "annotation" to an object mapping "source_card" and "target" to their bounding boxes [x0, y0, x1, y1].
Required answer format: set "answer" to only the visible move option letter, for example "C".
Example JSON:
{"annotation":{"source_card":[250,220,324,324],"target":[342,220,416,324]},"answer":"C"}
```

### task_games__solitaire__move_legality_label / single / answer_only / sample 5292496676928945

- `instance_seed`: `5292496676928945`
- `word_count`: `94`
- `body_word_count`: `76`

```text
The solitaire layout shows solitaire columns and foundation piles. For moves between columns, a card can be placed on another column card only if the target is exactly one rank higher and the opposite color. A card can move to a foundation only if it matches that foundation suit and is exactly one rank above the foundation's current top card; an Ace can move to an empty foundation. Which option letter shows a legal solitaire move?
Answer format: set "answer" to only the visible move option letter, for example "C".
Example JSON:
{"answer":"C"}
```

### task_games__solitaire__tableau_movable_card_count_value / single / answer_and_annotation / sample 5658151222816371

- `instance_seed`: `5658151222816371`
- `word_count`: `107`
- `body_word_count`: `45`

```text
The solitaire layout shows solitaire columns. For moves between columns, a card can be placed on another column card only if the target is exactly one rank higher and the opposite color. Count the exposed column cards that can move onto another exposed column card.
Final answer format: set "answer" to the number of exposed column cards that have at least one legal column move.
Annotation format: set "annotation" to an array of bounding boxes [x0, y0, x1, y1] for every counted exposed column card; use an empty array when no cards are counted.
Example JSON:
{"annotation":[[342,220,416,324],[434,220,508,324]],"answer":2}
```

### task_games__solitaire__tableau_movable_card_count_value / single / answer_only / sample 5658151222816371

- `instance_seed`: `5658151222816371`
- `word_count`: `69`
- `body_word_count`: `45`

```text
The solitaire layout shows solitaire columns. For moves between columns, a card can be placed on another column card only if the target is exactly one rank higher and the opposite color. Count the exposed column cards that can move onto another exposed column card.
Required answer format: set "answer" to the number of exposed column cards that have at least one legal column move.
Example JSON:
{"answer":2}
```

### task_games__space_shooter__enemy_ship_count / single / answer_and_annotation / sample 8407700967343716

- `instance_seed`: `8407700967343716`
- `word_count`: `86`
- `body_word_count`: `42`

```text
The visual shows a retro space-shooter playfield with enemy ships, red downward enemy shots, blue upward player shots, a player ship, and bottom lane pads. How many enemy ships are visible in the playfield? Do not count the player ship or projectiles.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] for every visible enemy ship.
Answer format: set "answer" to the number of visible enemy ships.
Example JSON:
{"annotation":[[120,180,182,228],[320,260,382,308],[520,340,582,388]],"answer":3}
```

### task_games__space_shooter__enemy_ship_count / single / answer_only / sample 8407700967343716

- `instance_seed`: `8407700967343716`
- `word_count`: `58`
- `body_word_count`: `42`

```text
The visual shows a retro space-shooter playfield with enemy ships, red downward enemy shots, blue upward player shots, a player ship, and bottom lane pads. How many enemy ships are visible in the playfield? Do not count the player ship or projectiles.
Final answer format: set "answer" to the number of visible enemy ships.
Example JSON:
{"answer":3}
```

### task_games__space_shooter__enemy_ship_hit_count / single / answer_and_annotation / sample 1456636717856132

- `instance_seed`: `1456636717856132`
- `word_count`: `142`
- `body_word_count`: `82`

```text
The visual shows a retro space-shooter playfield with enemy ships, red downward enemy shots, blue upward player shots, a player ship, and bottom lane pads. Count enemy ships that can be destroyed by the current blue shots. Each blue shot hits one ship above it in the same vertical lane, starting from the lower ships. Bottom lane pads define the vertical lanes. Enemy ships and shots stay in their own lane; red enemy shots move downward and blue player shots move upward.
Final answer format: set "answer" to the number of enemy ships that can be destroyed by the current blue shots.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] for the enemy ships that can be destroyed by blue player shots.
Example JSON:
{"annotation":[[140,130,202,178],[420,250,482,298],[700,170,762,218]],"answer":3}
```

### task_games__space_shooter__enemy_ship_hit_count / single / answer_only / sample 1456636717856132

- `instance_seed`: `1456636717856132`
- `word_count`: `106`
- `body_word_count`: `82`

```text
The visual shows a retro space-shooter playfield with enemy ships, red downward enemy shots, blue upward player shots, a player ship, and bottom lane pads. Count enemy ships that can be destroyed by the current blue shots. Each blue shot hits one ship above it in the same vertical lane, starting from the lower ships. Bottom lane pads define the vertical lanes. Enemy ships and shots stay in their own lane; red enemy shots move downward and blue player shots move upward.
Final answer format: set "answer" to the number of enemy ships that can be destroyed by the current blue shots.
Example JSON:
{"answer":3}
```

### task_games__space_shooter__first_hit_enemy_ship_label / single / answer_and_annotation / sample 3917159665022474

- `instance_seed`: `3917159665022474`
- `word_count`: `93`
- `body_word_count`: `51`

```text
The image shows a retro space-shooter playfield with enemy ships, red downward enemy shots, blue upward player shots, a player ship, and bottom lane pads. Each blue shot travels straight upward and first hits the nearest enemy ship above it in the same lane. Which labeled enemy ship is hit first?
Required annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] for the labeled enemy ship selected as the answer.
Required answer format: set "answer" to the selected enemy ship label.
Example JSON:
{"annotation":[414,510,438,546],"answer":"B"}
```

### task_games__space_shooter__first_hit_enemy_ship_label / single / answer_only / sample 3917159665022474

- `instance_seed`: `3917159665022474`
- `word_count`: `65`
- `body_word_count`: `51`

```text
The image shows a retro space-shooter playfield with enemy ships, red downward enemy shots, blue upward player shots, a player ship, and bottom lane pads. Each blue shot travels straight upward and first hits the nearest enemy ship above it in the same lane. Which labeled enemy ship is hit first?
Answer format: set "answer" to the selected enemy ship label.
Example JSON:
{"answer":"B"}
```

### task_games__space_shooter__hit_enemy_ship_label / single / answer_and_annotation / sample 5649198123085485

- `instance_seed`: `5649198123085485`
- `word_count`: `107`
- `body_word_count`: `67`

```text
This scene shows a retro space-shooter playfield with enemy ships, red downward enemy shots, blue upward player shots, a player ship, and bottom lane pads. Bottom lane pads define the vertical lanes. Enemy ships and shots stay in their own lane; red enemy shots move downward and blue player shots move upward. Among the labeled enemy ships, which one will be destroyed by a current blue shot?
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] for the labeled enemy ship selected as the answer.
Answer format: set "answer" to the selected enemy ship label.
Example JSON:
{"annotation":[420,250,482,298],"answer":"C"}
```

### task_games__space_shooter__hit_enemy_ship_label / single / answer_only / sample 5649198123085485

- `instance_seed`: `5649198123085485`
- `word_count`: `82`
- `body_word_count`: `67`

```text
This scene shows a retro space-shooter playfield with enemy ships, red downward enemy shots, blue upward player shots, a player ship, and bottom lane pads. Bottom lane pads define the vertical lanes. Enemy ships and shots stay in their own lane; red enemy shots move downward and blue player shots move upward. Among the labeled enemy ships, which one will be destroyed by a current blue shot?
Final answer format: set "answer" to the selected enemy ship label.
Example JSON:
{"answer":"C"}
```

### task_games__space_shooter__safe_lane_count / single / answer_and_annotation / sample 4436159051671942

- `instance_seed`: `4436159051671942`
- `word_count`: `123`
- `body_word_count`: `70`

```text
The scene shows a retro space-shooter playfield with enemy ships, red downward enemy shots, blue upward player shots, a player ship, and bottom lane pads. Count the bottom lane pads that are not threatened by a red enemy shot in the same lane. Bottom lane pads define the vertical lanes. Enemy ships and shots stay in their own lane; red enemy shots move downward and blue player shots move upward.
Annotation format: set "annotation" to bounding boxes [x0, y0, x1, y1] for the safe bottom lane pads.
Answer format: set "answer" to the number of bottom lane pads with no red enemy shot in that lane.
Example JSON:
{"annotation":[[115,695,205,733],[360,695,450,733],[610,695,700,733]],"answer":3}
```

### task_games__space_shooter__safe_lane_count / single / answer_only / sample 4436159051671942

- `instance_seed`: `4436159051671942`
- `word_count`: `93`
- `body_word_count`: `70`

```text
The scene shows a retro space-shooter playfield with enemy ships, red downward enemy shots, blue upward player shots, a player ship, and bottom lane pads. Count the bottom lane pads that are not threatened by a red enemy shot in the same lane. Bottom lane pads define the vertical lanes. Enemy ships and shots stay in their own lane; red enemy shots move downward and blue player shots move upward.
Answer format: set "answer" to the number of bottom lane pads with no red enemy shot in that lane.
Example JSON:
{"answer":3}
```

### task_games__tetris__active_piece_shape_label / single / answer_and_annotation / sample 4958966531385397

- `instance_seed`: `4958966531385397`
- `word_count`: `60`
- `body_word_count`: `22`

```text
The figure shows a Tetris board with colored locked blocks and tetromino pieces. Select the option with the correct falling-piece shape name.
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] enclosing the falling piece on the board.
Answer format: set "answer" to only the selected option letter.
Example JSON:
{"annotation":[246,92,352,166],"answer":"B"}
```

### task_games__tetris__active_piece_shape_label / single / answer_only / sample 4958966531385397

- `instance_seed`: `4958966531385397`
- `word_count`: `37`
- `body_word_count`: `22`

```text
The figure shows a Tetris board with colored locked blocks and tetromino pieces. Select the option with the correct falling-piece shape name.
Required answer format: set "answer" to only the selected option letter.
Example JSON:
{"answer":"B"}
```

### task_games__tetris__drop_collision_time_value / left_shift_collision_time / answer_and_annotation / sample 350535997256092

- `instance_seed`: `350535997256092`
- `word_count`: `106`
- `body_word_count`: `55`

```text
This Tetris scene shows a Tetris board with colored locked blocks and tetromino pieces. Starting from the shown falling piece, move it 2 columns left. A timestep is one successful downward move by one row after the horizontal shift; do not count the failed collision move. How many downward timesteps can it move before collision?
Annotation format: set "annotation" to an object mapping "start_piece" and "stop_witness" to arrays of cell bounding boxes [x0, y0, x1, y1].
Answer format: set "answer" to the number of successful downward timesteps.
Example JSON:
{"annotation":{"start_piece":[[120,80,150,110],[154,80,184,110]],"stop_witness":[[120,320,150,350]]},"answer":5}
```

### task_games__tetris__drop_collision_time_value / left_shift_collision_time / answer_only / sample 350535997256092

- `instance_seed`: `350535997256092`
- `word_count`: `71`
- `body_word_count`: `55`

```text
This Tetris scene shows a Tetris board with colored locked blocks and tetromino pieces. Starting from the shown falling piece, move it 2 columns left. A timestep is one successful downward move by one row after the horizontal shift; do not count the failed collision move. How many downward timesteps can it move before collision?
Final answer format: set "answer" to the number of successful downward timesteps.
Example JSON:
{"answer":5}
```

### task_games__tetris__drop_collision_time_value / no_shift_collision_time / answer_and_annotation / sample 7455166713877939

- `instance_seed`: `7455166713877939`
- `word_count`: `111`
- `body_word_count`: `60`

```text
This Tetris scene shows a Tetris board with colored locked blocks and tetromino pieces. Use the falling piece in the START board. First do not move it sideways; then drop it vertically. A timestep is one successful downward move by one row after the horizontal shift; do not count the failed collision move. What is the timestep count before collision?
Annotation format: set "annotation" to an object mapping "start_piece" and "stop_witness" to arrays of cell bounding boxes [x0, y0, x1, y1].
Answer format: set "answer" to the number of successful downward timesteps.
Example JSON:
{"annotation":{"start_piece":[[120,80,150,110],[154,80,184,110]],"stop_witness":[[120,320,150,350]]},"answer":5}
```

### task_games__tetris__drop_collision_time_value / no_shift_collision_time / answer_only / sample 7455166713877939

- `instance_seed`: `7455166713877939`
- `word_count`: `75`
- `body_word_count`: `60`

```text
This Tetris scene shows a Tetris board with colored locked blocks and tetromino pieces. Use the falling piece in the START board. First do not move it sideways; then drop it vertically. A timestep is one successful downward move by one row after the horizontal shift; do not count the failed collision move. What is the timestep count before collision?
Answer format: set "answer" to the number of successful downward timesteps.
Example JSON:
{"answer":5}
```

### task_games__tetris__drop_collision_time_value / right_shift_collision_time / answer_and_annotation / sample 6139875104383952

- `instance_seed`: `6139875104383952`
- `word_count`: `106`
- `body_word_count`: `54`

```text
The visual shows a Tetris board with colored locked blocks and tetromino pieces. Starting from the shown falling piece, move it 2 columns right. A timestep is one successful downward move by one row after the horizontal shift; do not count the failed collision move. How many downward timesteps can it move before collision?
Final answer format: set "answer" to the number of successful downward timesteps.
Annotation format: set "annotation" to an object mapping "start_piece" and "stop_witness" to arrays of cell bounding boxes [x0, y0, x1, y1].
Example JSON:
{"annotation":{"start_piece":[[120,80,150,110],[154,80,184,110]],"stop_witness":[[120,320,150,350]]},"answer":5}
```

### task_games__tetris__drop_collision_time_value / right_shift_collision_time / answer_only / sample 6139875104383952

- `instance_seed`: `6139875104383952`
- `word_count`: `70`
- `body_word_count`: `54`

```text
The visual shows a Tetris board with colored locked blocks and tetromino pieces. Starting from the shown falling piece, move it 2 columns right. A timestep is one successful downward move by one row after the horizontal shift; do not count the failed collision move. How many downward timesteps can it move before collision?
Required answer format: set "answer" to the number of successful downward timesteps.
Example JSON:
{"answer":5}
```

### task_games__tetris__drop_result_label / single / answer_and_annotation / sample 8513383769665272

- `instance_seed`: `8513383769665272`
- `word_count`: `94`
- `body_word_count`: `60`

```text
The image shows a Tetris board with colored locked blocks and tetromino pieces. In the START board, the falling piece drops straight down from its shown position without moving sideways or rotating. After the piece locks, every completely filled row clears and all rows above fall down by the number of cleared rows. Which labeled board shows the final state?
Final answer format: set "answer" to only the selected option letter.
Annotation format: set "annotation" to the selected result-board bounding box [x0, y0, x1, y1].
Example JSON:
{"annotation":[520,180,760,520],"answer":"B"}
```

### task_games__tetris__drop_result_label / single / answer_only / sample 8513383769665272

- `instance_seed`: `8513383769665272`
- `word_count`: `75`
- `body_word_count`: `60`

```text
The image shows a Tetris board with colored locked blocks and tetromino pieces. In the START board, the falling piece drops straight down from its shown position without moving sideways or rotating. After the piece locks, every completely filled row clears and all rows above fall down by the number of cleared rows. Which labeled board shows the final state?
Final answer format: set "answer" to only the selected option letter.
Example JSON:
{"answer":"B"}
```

### task_games__tetris__edge_occupied_row_cell_count / bottom_occupied_row_empty_cell_count / answer_and_annotation / sample 737497204712123

- `instance_seed`: `737497204712123`
- `word_count`: `81`
- `body_word_count`: `29`

```text
The figure shows a Tetris board with colored locked blocks and tetromino pieces. In the lowest board row with at least one block, how many empty cells are there?
Final answer format: set "answer" to the number of counted cells in the selected row.
Annotation format: set "annotation" to an array containing one cell bounding box [x0, y0, x1, y1] for each counted cell in the selected row.
Example JSON:
{"annotation":[[120,220,150,250],[154,220,184,250]],"answer":2}
```

### task_games__tetris__edge_occupied_row_cell_count / bottom_occupied_row_empty_cell_count / answer_only / sample 737497204712123

- `instance_seed`: `737497204712123`
- `word_count`: `48`
- `body_word_count`: `29`

```text
The figure shows a Tetris board with colored locked blocks and tetromino pieces. In the lowest board row with at least one block, how many empty cells are there?
Final answer format: set "answer" to the number of counted cells in the selected row.
Example JSON:
{"answer":2}
```

### task_games__tetris__edge_occupied_row_cell_count / bottom_occupied_row_filled_cell_count / answer_and_annotation / sample 6419586756112357

- `instance_seed`: `6419586756112357`
- `word_count`: `79`
- `body_word_count`: `27`

```text
The scene shows a Tetris board with colored locked blocks and tetromino pieces. In the lowest row that contains any block, how many filled cells are there?
Final answer format: set "answer" to the number of counted cells in the selected row.
Annotation format: set "annotation" to an array containing one cell bounding box [x0, y0, x1, y1] for each counted cell in the selected row.
Example JSON:
{"annotation":[[120,220,150,250],[154,220,184,250]],"answer":2}
```

### task_games__tetris__edge_occupied_row_cell_count / bottom_occupied_row_filled_cell_count / answer_only / sample 6419586756112357

- `instance_seed`: `6419586756112357`
- `word_count`: `46`
- `body_word_count`: `27`

```text
The scene shows a Tetris board with colored locked blocks and tetromino pieces. In the lowest row that contains any block, how many filled cells are there?
Required answer format: set "answer" to the number of counted cells in the selected row.
Example JSON:
{"answer":2}
```

### task_games__tetris__edge_occupied_row_cell_count / top_occupied_row_empty_cell_count / answer_and_annotation / sample 4682003721666540

- `instance_seed`: `4682003721666540`
- `word_count`: `78`
- `body_word_count`: `25`

```text
The visual shows a Tetris board with colored locked blocks and tetromino pieces. In the top occupied row of the board, count the empty cells.
Required annotation format: set "annotation" to an array containing one cell bounding box [x0, y0, x1, y1] for each counted cell in the selected row.
Required answer format: set "answer" to the number of counted cells in the selected row.
Example JSON:
{"annotation":[[120,220,150,250],[154,220,184,250]],"answer":2}
```

### task_games__tetris__edge_occupied_row_cell_count / top_occupied_row_empty_cell_count / answer_only / sample 4682003721666540

- `instance_seed`: `4682003721666540`
- `word_count`: `43`
- `body_word_count`: `25`

```text
The visual shows a Tetris board with colored locked blocks and tetromino pieces. In the top occupied row of the board, count the empty cells.
Answer format: set "answer" to the number of counted cells in the selected row.
Example JSON:
{"answer":2}
```

### task_games__tetris__edge_occupied_row_cell_count / top_occupied_row_filled_cell_count / answer_and_annotation / sample 4463217250581388

- `instance_seed`: `4463217250581388`
- `word_count`: `78`
- `body_word_count`: `25`

```text
The image shows a Tetris board with colored locked blocks and tetromino pieces. In the top occupied row of the board, count the filled cells.
Required annotation format: set "annotation" to an array containing one cell bounding box [x0, y0, x1, y1] for each counted cell in the selected row.
Required answer format: set "answer" to the number of counted cells in the selected row.
Example JSON:
{"annotation":[[120,220,150,250],[154,220,184,250]],"answer":2}
```

### task_games__tetris__edge_occupied_row_cell_count / top_occupied_row_filled_cell_count / answer_only / sample 4463217250581388

- `instance_seed`: `4463217250581388`
- `word_count`: `44`
- `body_word_count`: `25`

```text
The image shows a Tetris board with colored locked blocks and tetromino pieces. In the top occupied row of the board, count the filled cells.
Required answer format: set "answer" to the number of counted cells in the selected row.
Example JSON:
{"answer":2}
```

### task_games__tetris__line_clear_count / single / answer_and_annotation / sample 3198363356224517

- `instance_seed`: `3198363356224517`
- `word_count`: `116`
- `body_word_count`: `66`

```text
This Tetris scene shows a Tetris board with colored locked blocks and tetromino pieces. The NEXT piece may be rotated and moved sideways, then it falls straight down until it rests. After the piece locks, every completely filled row clears and all rows above fall down by the number of cleared rows. Considering every rotation and horizontal position, how many rows can be cleared at most?
Final answer format: set "answer" to the maximum number of rows the NEXT piece can clear.
Annotation format: set "annotation" to an object mapping "board" and "next_piece" to their bounding boxes [x0, y0, x1, y1].
Example JSON:
{"annotation":{"board":[40,120,320,640],"next_piece":[420,140,520,260]},"answer":2}
```

### task_games__tetris__line_clear_count / single / answer_only / sample 3198363356224517

- `instance_seed`: `3198363356224517`
- `word_count`: `85`
- `body_word_count`: `66`

```text
This Tetris scene shows a Tetris board with colored locked blocks and tetromino pieces. The NEXT piece may be rotated and moved sideways, then it falls straight down until it rests. After the piece locks, every completely filled row clears and all rows above fall down by the number of cleared rows. Considering every rotation and horizontal position, how many rows can be cleared at most?
Answer format: set "answer" to the maximum number of rows the NEXT piece can clear.
Example JSON:
{"answer":2}
```

### task_games__tetris__row_occupancy_status_count / full_row_count / answer_and_annotation / sample 6138630112819886

- `instance_seed`: `6138630112819886`
- `word_count`: `64`
- `body_word_count`: `21`

```text
The figure shows a Tetris board with colored locked blocks and tetromino pieces. What is the number of completely filled rows?
Annotation format: set "annotation" to an array containing one whole-row bounding box [x0, y0, x1, y1] for each qualifying row.
Answer format: set "answer" to the number of qualifying rows.
Example JSON:
{"annotation":[[120,360,520,392],[120,430,520,462]],"answer":2}
```

### task_games__tetris__row_occupancy_status_count / full_row_count / answer_only / sample 6138630112819886

- `instance_seed`: `6138630112819886`
- `word_count`: `35`
- `body_word_count`: `21`

```text
The figure shows a Tetris board with colored locked blocks and tetromino pieces. What is the number of completely filled rows?
Answer format: set "answer" to the number of qualifying rows.
Example JSON:
{"answer":2}
```

### task_games__tetris__row_occupancy_status_count / one_gap_row_count / answer_and_annotation / sample 3442535389343515

- `instance_seed`: `3442535389343515`
- `word_count`: `64`
- `body_word_count`: `21`

```text
The visual shows a Tetris board with colored locked blocks and tetromino pieces. How many rows are missing exactly one block?
Annotation format: set "annotation" to an array containing one whole-row bounding box [x0, y0, x1, y1] for each qualifying row.
Answer format: set "answer" to the number of qualifying rows.
Example JSON:
{"annotation":[[120,360,520,392],[120,430,520,462]],"answer":2}
```

### task_games__tetris__row_occupancy_status_count / one_gap_row_count / answer_only / sample 3442535389343515

- `instance_seed`: `3442535389343515`
- `word_count`: `36`
- `body_word_count`: `21`

```text
The visual shows a Tetris board with colored locked blocks and tetromino pieces. How many rows are missing exactly one block?
Final answer format: set "answer" to the number of qualifying rows.
Example JSON:
{"answer":2}
```

### task_games__tic_tac_toe_3d__layer_piece_count / single / answer_and_annotation / sample 2182824315707512

- `instance_seed`: `2182824315707512`
- `word_count`: `78`
- `body_word_count`: `29`

```text
The figure shows three stacked 3 by 3 layers of a 3D Tic-Tac-Toe board, ordered from top to bottom. Determine how many X marks appear in the middle layer.
Final answer format: set "answer" to the number of X pieces in the requested layer.
Annotation format: set "annotation" to an array containing pixel-coordinate [x, y] points at the centers of all X pieces in the requested layer.
Example JSON:
{"annotation":[[212,318],[285,391],[358,318]],"answer":3}
```

### task_games__tic_tac_toe_3d__layer_piece_count / single / answer_only / sample 2182824315707512

- `instance_seed`: `2182824315707512`
- `word_count`: `48`
- `body_word_count`: `29`

```text
The figure shows three stacked 3 by 3 layers of a 3D Tic-Tac-Toe board, ordered from top to bottom. Determine how many X marks appear in the middle layer.
Required answer format: set "answer" to the number of X pieces in the requested layer.
Example JSON:
{"answer":3}
```

### task_games__tic_tac_toe_3d__winning_move_cell_label / o_winning_move_label / answer_and_annotation / sample 1423279151876197

- `instance_seed`: `1423279151876197`
- `word_count`: `105`
- `body_word_count`: `50`

```text
The figure shows three stacked 3 by 3 layers of a 3D Tic-Tac-Toe board, ordered from top to bottom. A line can run within one layer, straight through the layers, diagonally across a face, or diagonally through all three layers. Choose the labeled empty cell where O completes a line.
Required annotation format: set "annotation" to an array containing [x0, y0, x1, y1] boxes for the three board cells that form the completed winning line for O.
Required answer format: set "answer" to only the selected option letter.
Example JSON:
{"annotation":[[320,190,380,250],[250,190,310,250],[390,190,450,250]],"answer":"B"}
```

### task_games__tic_tac_toe_3d__winning_move_cell_label / o_winning_move_label / answer_only / sample 1423279151876197

- `instance_seed`: `1423279151876197`
- `word_count`: `65`
- `body_word_count`: `50`

```text
The figure shows three stacked 3 by 3 layers of a 3D Tic-Tac-Toe board, ordered from top to bottom. A line can run within one layer, straight through the layers, diagonally across a face, or diagonally through all three layers. Choose the labeled empty cell where O completes a line.
Required answer format: set "answer" to only the selected option letter.
Example JSON:
{"answer":"B"}
```

### task_games__tic_tac_toe_3d__winning_move_cell_label / x_winning_move_label / answer_and_annotation / sample 8335398106098293

- `instance_seed`: `8335398106098293`
- `word_count`: `103`
- `body_word_count`: `48`

```text
The scene shows three stacked 3 by 3 layers of a 3D Tic-Tac-Toe board, ordered from top to bottom. A line can run within one layer, straight through the layers, diagonally across a face, or diagonally through all three layers. Which empty-cell label completes a line for X?
Required annotation format: set "annotation" to an array containing [x0, y0, x1, y1] boxes for the three board cells that form the completed winning line for X.
Required answer format: set "answer" to only the selected option letter.
Example JSON:
{"annotation":[[320,190,380,250],[250,190,310,250],[390,190,450,250]],"answer":"B"}
```

### task_games__tic_tac_toe_3d__winning_move_cell_label / x_winning_move_label / answer_only / sample 8335398106098293

- `instance_seed`: `8335398106098293`
- `word_count`: `62`
- `body_word_count`: `48`

```text
The scene shows three stacked 3 by 3 layers of a 3D Tic-Tac-Toe board, ordered from top to bottom. A line can run within one layer, straight through the layers, diagonally across a face, or diagonally through all three layers. Which empty-cell label completes a line for X?
Answer format: set "answer" to only the selected option letter.
Example JSON:
{"answer":"B"}
```

### task_games__tower_defense__best_tower_position_label / single / answer_and_annotation / sample 7324200124057522

- `instance_seed`: `7324200124057522`
- `word_count`: `96`
- `body_word_count`: `53`

```text
The image shows a tower-defense map with a switchback path, small enemy markers on the path, and four labeled candidate tower positions A through D. A candidate covers a path enemy when that enemy's center is inside the candidate's visible range ring. Which candidate tower would cover the most enemies on the path?
Required annotation format: set "annotation" to the [x, y] pixel point at the center of the chosen candidate tower.
Required answer format: set "answer" to the chosen candidate label, one of A, B, C, or D.
Example JSON:
{"annotation":[420,260],"answer":"B"}
```

### task_games__tower_defense__best_tower_position_label / single / answer_only / sample 7324200124057522

- `instance_seed`: `7324200124057522`
- `word_count`: `74`
- `body_word_count`: `53`

```text
The image shows a tower-defense map with a switchback path, small enemy markers on the path, and four labeled candidate tower positions A through D. A candidate covers a path enemy when that enemy's center is inside the candidate's visible range ring. Which candidate tower would cover the most enemies on the path?
Required answer format: set "answer" to the chosen candidate label, one of A, B, C, or D.
Example JSON:
{"answer":"B"}
```

### task_games__tower_defense__covered_path_segment_count / single / answer_and_annotation / sample 1766278390239642

- `instance_seed`: `1766278390239642`
- `word_count`: `92`
- `body_word_count`: `48`

```text
The figure shows a tower-defense map with a winding path, circular tower range rings, and small enemy markers on the path. A path enemy is covered when its center is inside at least one visible tower range ring. Count the path enemies covered by one or more towers.
Annotation format: set "annotation" to [x, y] pixel points at the centers of every covered path enemy.
Answer format: set "answer" to the number of path enemies covered by at least one tower range ring.
Example JSON:
{"annotation":[[246,314],[514,226]],"answer":2}
```

### task_games__tower_defense__covered_path_segment_count / single / answer_only / sample 1766278390239642

- `instance_seed`: `1766278390239642`
- `word_count`: `70`
- `body_word_count`: `48`

```text
The figure shows a tower-defense map with a winding path, circular tower range rings, and small enemy markers on the path. A path enemy is covered when its center is inside at least one visible tower range ring. Count the path enemies covered by one or more towers.
Answer format: set "answer" to the number of path enemies covered by at least one tower range ring.
Example JSON:
{"answer":2}
```

### task_games__tower_defense__nearest_exit_enemy_label / single / answer_and_annotation / sample 4008683785322462

- `instance_seed`: `4008683785322462`
- `word_count`: `93`
- `body_word_count`: `49`

```text
This scene shows a tower-defense map with a winding path, small enemy markers, six labeled path enemies A through F, and an exit marker. Follow the drawn path toward the exit marker; compare path order, not straight-line distance. Which labeled enemy is closest to the exit along the path?
Final answer format: set "answer" to the selected enemy label, one of A, B, C, D, E, or F.
Annotation format: set "annotation" to the [x, y] pixel point at the center of the selected labeled enemy.
Example JSON:
{"annotation":[420,260],"answer":"E"}
```

### task_games__tower_defense__nearest_exit_enemy_label / single / answer_only / sample 4008683785322462

- `instance_seed`: `4008683785322462`
- `word_count`: `71`
- `body_word_count`: `49`

```text
This scene shows a tower-defense map with a winding path, small enemy markers, six labeled path enemies A through F, and an exit marker. Follow the drawn path toward the exit marker; compare path order, not straight-line distance. Which labeled enemy is closest to the exit along the path?
Answer format: set "answer" to the selected enemy label, one of A, B, C, D, E, or F.
Example JSON:
{"answer":"E"}
```

### task_games__tower_draughts_board__controlled_stack_count / single / answer_and_annotation / sample 7161182436857775

- `instance_seed`: `7161182436857775`
- `word_count`: `92`
- `body_word_count`: `38`

```text
This board shows a tower-draughts-style board with stacks of red and black disks on alternating playable squares. A stack is controlled by the color of its top disk. How many visible stacks have a black disk on top?
Annotation format: set "annotation" to bounding boxes [[x0, y0, x1, y1], ...] around every stack controlled by the named color; use an empty array if there are none.
Answer format: set "answer" to the number of stacks controlled by the named color.
Example JSON:
{"annotation":[[140,180,190,230],[250,290,300,340]],"answer":2}
```

### task_games__tower_draughts_board__controlled_stack_count / single / answer_only / sample 7161182436857775

- `instance_seed`: `7161182436857775`
- `word_count`: `57`
- `body_word_count`: `38`

```text
This board shows a tower-draughts-style board with stacks of red and black disks on alternating playable squares. A stack is controlled by the color of its top disk. How many visible stacks have a black disk on top?
Required answer format: set "answer" to the number of stacks controlled by the named color.
Example JSON:
{"answer":2}
```

### task_games__tower_draughts_board__marked_stack_capture_count / single / answer_and_annotation / sample 7348103385990527

- `instance_seed`: `7348103385990527`
- `word_count`: `114`
- `body_word_count`: `59`

```text
This board shows a tower-draughts-style board with stacks of red and black disks on alternating playable squares. A stack is controlled by the color of its top disk. A stack captures by jumping diagonally over an adjacent opponent-controlled stack into the empty playable square immediately beyond it. What is the number of capture jumps available to the X-marked stack?
Annotation format: set "annotation" to bounding boxes [[x0, y0, x1, y1], ...] around every opponent-controlled stack the X-marked stack can capture; use an empty array if there are none.
Answer format: set "answer" to the number of immediate captures for the X-marked stack.
Example JSON:
{"annotation":[[130,190,184,244],[242,300,296,354]],"answer":2}
```

### task_games__tower_draughts_board__marked_stack_capture_count / single / answer_only / sample 7348103385990527

- `instance_seed`: `7348103385990527`
- `word_count`: `77`
- `body_word_count`: `59`

```text
This board shows a tower-draughts-style board with stacks of red and black disks on alternating playable squares. A stack is controlled by the color of its top disk. A stack captures by jumping diagonally over an adjacent opponent-controlled stack into the empty playable square immediately beyond it. What is the number of capture jumps available to the X-marked stack?
Answer format: set "answer" to the number of immediate captures for the X-marked stack.
Example JSON:
{"answer":2}
```

### task_games__ultimate_tictactoe__line_completion_move_label / o_blocking_move_label / answer_and_annotation / sample 3007960619782479

- `instance_seed`: `3007960619782479`
- `word_count`: `91`
- `body_word_count`: `56`

```text
The figure shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. Use only the highlighted small board. A winning move places the requested mark to make three in a row; a blocking move places a mark on the only cell that stops the opponent's immediate three-in-a-row threat. Which option is O's immediate blocking move?
Annotation format: set "annotation" to the [x0, y0, x1, y1] box of the selected empty-cell option.
Answer format: set "answer" to only the selected option letter.
Example JSON:
{"annotation":[410,240,470,300],"answer":"C"}
```

### task_games__ultimate_tictactoe__line_completion_move_label / o_blocking_move_label / answer_only / sample 3007960619782479

- `instance_seed`: `3007960619782479`
- `word_count`: `70`
- `body_word_count`: `56`

```text
The figure shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. Use only the highlighted small board. A winning move places the requested mark to make three in a row; a blocking move places a mark on the only cell that stops the opponent's immediate three-in-a-row threat. Which option is O's immediate blocking move?
Answer format: set "answer" to only the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_games__ultimate_tictactoe__line_completion_move_label / o_winning_move_label / answer_and_annotation / sample 7056817449041372

- `instance_seed`: `7056817449041372`
- `word_count`: `96`
- `body_word_count`: `60`

```text
The image shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. Use only the highlighted small board. A winning move places the requested mark to make three in a row; a blocking move places a mark on the only cell that stops the opponent's immediate three-in-a-row threat. Which labeled empty cell lets O win the highlighted small board?
Final answer format: set "answer" to only the selected option letter.
Annotation format: set "annotation" to the [x0, y0, x1, y1] box of the selected empty-cell option.
Example JSON:
{"annotation":[410,240,470,300],"answer":"C"}
```

### task_games__ultimate_tictactoe__line_completion_move_label / o_winning_move_label / answer_only / sample 7056817449041372

- `instance_seed`: `7056817449041372`
- `word_count`: `75`
- `body_word_count`: `60`

```text
The image shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. Use only the highlighted small board. A winning move places the requested mark to make three in a row; a blocking move places a mark on the only cell that stops the opponent's immediate three-in-a-row threat. Which labeled empty cell lets O win the highlighted small board?
Final answer format: set "answer" to only the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_games__ultimate_tictactoe__line_completion_move_label / x_blocking_move_label / answer_and_annotation / sample 3077778263929006

- `instance_seed`: `3077778263929006`
- `word_count`: `95`
- `body_word_count`: `60`

```text
The image shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. Use only the highlighted small board. A winning move places the requested mark to make three in a row; a blocking move places a mark on the only cell that stops the opponent's immediate three-in-a-row threat. Which empty-cell label stops O from completing three in a row?
Annotation format: set "annotation" to the [x0, y0, x1, y1] box of the selected empty-cell option.
Answer format: set "answer" to only the selected option letter.
Example JSON:
{"annotation":[410,240,470,300],"answer":"C"}
```

### task_games__ultimate_tictactoe__line_completion_move_label / x_blocking_move_label / answer_only / sample 3077778263929006

- `instance_seed`: `3077778263929006`
- `word_count`: `74`
- `body_word_count`: `60`

```text
The image shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. Use only the highlighted small board. A winning move places the requested mark to make three in a row; a blocking move places a mark on the only cell that stops the opponent's immediate three-in-a-row threat. Which empty-cell label stops O from completing three in a row?
Answer format: set "answer" to only the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_games__ultimate_tictactoe__line_completion_move_label / x_winning_move_label / answer_and_annotation / sample 8402092056090952

- `instance_seed`: `8402092056090952`
- `word_count`: `95`
- `body_word_count`: `60`

```text
The scene shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. Use only the highlighted small board. A winning move places the requested mark to make three in a row; a blocking move places a mark on the only cell that stops the opponent's immediate three-in-a-row threat. Which labeled empty cell lets X win the highlighted small board?
Annotation format: set "annotation" to the [x0, y0, x1, y1] box of the selected empty-cell option.
Answer format: set "answer" to only the selected option letter.
Example JSON:
{"annotation":[410,240,470,300],"answer":"C"}
```

### task_games__ultimate_tictactoe__line_completion_move_label / x_winning_move_label / answer_only / sample 8402092056090952

- `instance_seed`: `8402092056090952`
- `word_count`: `74`
- `body_word_count`: `60`

```text
The scene shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. Use only the highlighted small board. A winning move places the requested mark to make three in a row; a blocking move places a mark on the only cell that stops the opponent's immediate three-in-a-row threat. Which labeled empty cell lets X win the highlighted small board?
Answer format: set "answer" to only the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_games__ultimate_tictactoe__macro_threat_board_count / o_immediate_win_board_count / answer_and_annotation / sample 1285866371426355

- `instance_seed`: `1285866371426355`
- `word_count`: `109`
- `body_word_count`: `52`

```text
The visual shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. Count only open small boards where the requested player can win in one move. Already won or drawn small boards do not count. What is the number of open small boards where O can complete three in a row?
Annotation format: set "annotation" to an array containing the [x0, y0, x1, y1] boxes of every open small board where O can win in one move.
Answer format: set "answer" to the number of open small boards where O can win in one move.
Example JSON:
{"annotation":[[110,110,260,260],[450,280,600,430]],"answer":2}
```

### task_games__ultimate_tictactoe__macro_threat_board_count / o_immediate_win_board_count / answer_only / sample 1285866371426355

- `instance_seed`: `1285866371426355`
- `word_count`: `75`
- `body_word_count`: `52`

```text
The visual shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. Count only open small boards where the requested player can win in one move. Already won or drawn small boards do not count. What is the number of open small boards where O can complete three in a row?
Required answer format: set "answer" to the number of open small boards where O can win in one move.
Example JSON:
{"answer":2}
```

### task_games__ultimate_tictactoe__macro_threat_board_count / x_immediate_win_board_count / answer_and_annotation / sample 2999332337815306

- `instance_seed`: `2999332337815306`
- `word_count`: `104`
- `body_word_count`: `47`

```text
The visual shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. Count only open small boards where the requested player can win in one move. Already won or drawn small boards do not count. Count the small boards where X has an immediate winning move.
Annotation format: set "annotation" to an array containing the [x0, y0, x1, y1] boxes of every open small board where X can win in one move.
Answer format: set "answer" to the number of open small boards where X can win in one move.
Example JSON:
{"annotation":[[110,110,260,260],[450,280,600,430]],"answer":2}
```

### task_games__ultimate_tictactoe__macro_threat_board_count / x_immediate_win_board_count / answer_only / sample 2999332337815306

- `instance_seed`: `2999332337815306`
- `word_count`: `69`
- `body_word_count`: `47`

```text
The visual shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. Count only open small boards where the requested player can win in one move. Already won or drawn small boards do not count. Count the small boards where X has an immediate winning move.
Answer format: set "answer" to the number of open small boards where X can win in one move.
Example JSON:
{"answer":2}
```

### task_games__ultimate_tictactoe__small_board_status_count / drawn_board_count / answer_and_annotation / sample 3135051356869887

- `instance_seed`: `3135051356869887`
- `word_count`: `97`
- `body_word_count`: `52`

```text
This game board shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. A small board is won by X or O when that player has three marks in a row inside that small board. A drawn small board is full and has no winner. How many small boards are drawn?
Required annotation format: set "annotation" to an array containing the [x0, y0, x1, y1] boxes of all drawn small boards.
Required answer format: set "answer" to the number of drawn small boards.
Example JSON:
{"annotation":[[110,110,260,260],[450,280,600,430]],"answer":2}
```

### task_games__ultimate_tictactoe__small_board_status_count / drawn_board_count / answer_only / sample 3135051356869887

- `instance_seed`: `3135051356869887`
- `word_count`: `67`
- `body_word_count`: `52`

```text
This game board shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. A small board is won by X or O when that player has three marks in a row inside that small board. A drawn small board is full and has no winner. How many small boards are drawn?
Answer format: set "answer" to the number of drawn small boards.
Example JSON:
{"answer":2}
```

### task_games__ultimate_tictactoe__small_board_status_count / neither_won_board_count / answer_and_annotation / sample 3815539239753956

- `instance_seed`: `3815539239753956`
- `word_count`: `110`
- `body_word_count`: `57`

```text
This game board shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. A small board is won by X or O when that player has three marks in a row inside that small board. A drawn small board is full and has no winner. Count the small boards that neither X nor O has won.
Required annotation format: set "annotation" to an array containing the [x0, y0, x1, y1] boxes of all small boards that neither player has won.
Required answer format: set "answer" to the number of small boards that neither player has won.
Example JSON:
{"annotation":[[110,110,260,260],[450,280,600,430]],"answer":2}
```

### task_games__ultimate_tictactoe__small_board_status_count / neither_won_board_count / answer_only / sample 3815539239753956

- `instance_seed`: `3815539239753956`
- `word_count`: `77`
- `body_word_count`: `57`

```text
This game board shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. A small board is won by X or O when that player has three marks in a row inside that small board. A drawn small board is full and has no winner. Count the small boards that neither X nor O has won.
Required answer format: set "answer" to the number of small boards that neither player has won.
Example JSON:
{"answer":2}
```

### task_games__ultimate_tictactoe__small_board_status_count / o_won_board_count / answer_and_annotation / sample 4515165754503893

- `instance_seed`: `4515165754503893`
- `word_count`: `99`
- `body_word_count`: `52`

```text
The visual shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. A small board is won by X or O when that player has three marks in a row inside that small board. A drawn small board is full and has no winner. How many small boards has O won?
Annotation format: set "annotation" to an array containing the [x0, y0, x1, y1] boxes of all small boards won by O.
Answer format: set "answer" to the number of small boards won by O.
Example JSON:
{"annotation":[[110,110,260,260],[450,280,600,430]],"answer":2}
```

### task_games__ultimate_tictactoe__small_board_status_count / o_won_board_count / answer_only / sample 4515165754503893

- `instance_seed`: `4515165754503893`
- `word_count`: `69`
- `body_word_count`: `52`

```text
The visual shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. A small board is won by X or O when that player has three marks in a row inside that small board. A drawn small board is full and has no winner. How many small boards has O won?
Answer format: set "answer" to the number of small boards won by O.
Example JSON:
{"answer":2}
```

### task_games__ultimate_tictactoe__small_board_status_count / x_won_board_count / answer_and_annotation / sample 6863603579111245

- `instance_seed`: `6863603579111245`
- `word_count`: `103`
- `body_word_count`: `55`

```text
This game board shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. A small board is won by X or O when that player has three marks in a row inside that small board. A drawn small board is full and has no winner. Determine how many small boards are won by X.
Final answer format: set "answer" to the number of small boards won by X.
Annotation format: set "annotation" to an array containing the [x0, y0, x1, y1] boxes of all small boards won by X.
Example JSON:
{"annotation":[[110,110,260,260],[450,280,600,430]],"answer":2}
```

### task_games__ultimate_tictactoe__small_board_status_count / x_won_board_count / answer_only / sample 6863603579111245

- `instance_seed`: `6863603579111245`
- `word_count`: `73`
- `body_word_count`: `55`

```text
This game board shows an Ultimate Tic-Tac-Toe board made of nine small Tic-Tac-Toe boards. A small board is won by X or O when that player has three marks in a row inside that small board. A drawn small board is full and has no winner. Determine how many small boards are won by X.
Required answer format: set "answer" to the number of small boards won by X.
Example JSON:
{"answer":2}
```
