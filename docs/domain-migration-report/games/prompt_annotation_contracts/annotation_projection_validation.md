# Annotation Projection Validation

- sampled instances: `207`
- query ids covered: `207`
- annotation projection/geometry issues: `0`
- annotation types: `{'bbox': 24, 'bbox_map': 6, 'bbox_set': 111, 'bbox_set_map': 6, 'point': 22, 'point_map': 3, 'point_set': 27, 'point_set_map': 1, 'segment': 4, 'segment_set': 3}`
- tasks with incomplete coverage or generation errors: `0`

## Coverage

| task | expected query ids | collected counts | generated | issues |
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
| task_games__connect_four__column_disc_profile_label | `column_disc_profile_label` | `{'column_disc_profile_label': 1}` | 1 | `` |
| task_games__connect_four__winning_move_column_label | `single` | `{'single': 1}` | 2 | `` |
| task_games__connect_four__winning_move_count | `winning_move_count` | `{'winning_move_count': 1}` | 1 | `` |
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

## Issues

No issues found.
