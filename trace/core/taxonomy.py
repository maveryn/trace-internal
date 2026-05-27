"""Public TRACE taxonomy helpers.

This module resolves the active public task surface:
``domain -> scene_id -> task_id``.

``source_domain`` and ``source_task_group`` record implementation/config routing
for current task classes. They are not public taxonomy levels.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class TaxonomyEntry:
    """Canonical public taxonomy for one task id."""

    domain: str
    scene_id: str
    source_domain: str
    source_task_group: str


ACTIVE_DOMAINS: tuple[str, ...] = (
    "charts",
    "games",
    "geometry",
    "graph",
    "icons",
    "illustrations",
    "pages",
    "physics",
    "puzzles",
    "three_d",
)


def _entry(
    canonical_domain: str,
    scene_id: str,
    source_domain: str,
    source_task_group: str,
) -> TaxonomyEntry:
    return TaxonomyEntry(
        domain=str(canonical_domain),
        scene_id=str(scene_id),
        source_domain=str(source_domain),
        source_task_group=str(source_task_group),
    )


TASK_TAXONOMY: dict[str, TaxonomyEntry] = {
    # Charts and table-like data displays.
    "task_charts__area__interval_area_value": _entry("charts", "area", "charts", "area"),
    "task_charts__area__stacked_band_dominance_label": _entry("charts", "area", "charts", "area"),
    "task_charts__area__stacked_band_interval_sum_value": _entry("charts", "area", "charts", "area"),
    "task_charts__bar_3d__axis_gap_value": _entry("charts", "bar_3d", "charts", "three_d_bar"),
    "task_charts__bar_3d__axis_total_value": _entry("charts", "bar_3d", "charts", "three_d_bar"),
    "task_charts__bar_3d__condition_count": _entry("charts", "bar_3d", "charts", "three_d_bar"),
    "task_charts__boxplot__median_rank_difference_value": _entry("charts", "boxplot", "charts", "distribution"),
    "task_charts__boxplot__paired_median_shift_label": _entry("charts", "boxplot", "charts", "distribution"),
    "task_charts__boxplot__summary_statistic_label": _entry("charts", "boxplot", "charts", "distribution"),
    "task_charts__candlestick__counterfactual_close_value": _entry("charts", "candlestick", "charts", "candlestick"),
    "task_charts__candlestick__range_extremum_label": _entry("charts", "candlestick", "charts", "candlestick"),
    "task_charts__combo_mark__conditioned_extremum_label": _entry("charts", "combo_mark", "charts", "combo"),
    "task_charts__combo_mark__cross_mark_difference_value": _entry("charts", "combo_mark", "charts", "combo"),
    "task_charts__combo_mark__dual_condition_count": _entry("charts", "combo_mark", "charts", "combo"),
    "task_charts__combo_mark__gap_extremum_label": _entry("charts", "combo_mark", "charts", "combo"),
    "task_charts__combo_mark__interval_change_comparison_value": _entry("charts", "combo_mark", "charts", "combo"),
    "task_charts__curve_panels__cross_panel_delta_extremum_label": _entry("charts", "curve_panels", "charts", "scientific"),
    "task_charts__curve_panels__curve_at_x_extremum_label": _entry("charts", "curve_panels", "charts", "scientific"),
    "task_charts__curve_panels__curve_intersection_count": _entry("charts", "curve_panels", "charts", "scientific"),
    "task_charts__curve_panels__earliest_maximum_panel_label": _entry("charts", "curve_panels", "charts", "scientific"),
    "task_charts__curve_panels__threshold_series_count": _entry("charts", "curve_panels", "charts", "scientific"),
    "task_charts__dashboard__dual_condition_count": _entry("charts", "dashboard", "charts", "dashboard"),
    "task_charts__dashboard__dual_source_target_sum_value": _entry("charts", "dashboard", "charts", "dashboard"),
    "task_charts__dashboard__panel_gap_extremum_category_label": _entry("charts", "dashboard", "charts", "dashboard"),
    "task_charts__dashboard__source_rank_difference_value": _entry("charts", "dashboard", "charts", "dashboard"),
    "task_charts__dashboard__source_rank_target_value": _entry("charts", "dashboard", "charts", "dashboard"),
    "task_charts__dumbbell__gap_rank_row_label": _entry("charts", "dumbbell", "charts", "dumbbell"),
    "task_charts__dumbbell__pair_relation_count": _entry("charts", "dumbbell", "charts", "dumbbell"),
    "task_charts__error_interval__interval_width_rank_label": _entry("charts", "error_interval", "charts", "error_interval"),
    "task_charts__error_interval__reference_relation_count": _entry("charts", "error_interval", "charts", "error_interval"),
    "task_charts__heatmap__axis_cell_extremum_label": _entry("charts", "heatmap", "charts", "heatmap"),
    "task_charts__heatmap__axis_condition_extremum_label": _entry("charts", "heatmap", "charts", "heatmap"),
    "task_charts__heatmap__condition_run_extremum_label": _entry("charts", "heatmap", "charts", "heatmap"),
    "task_charts__histogram__cumulative_rank_bin_label": _entry("charts", "histogram", "charts", "distribution"),
    "task_charts__histogram__interval_value": _entry("charts", "histogram", "charts", "distribution"),
    "task_charts__marker_map__marker_region_extremum_label": _entry("charts", "marker_map", "charts", "map"),
    "task_charts__marker_map__marker_region_threshold_count": _entry("charts", "marker_map", "charts", "map"),
    "task_charts__matrix__axis_extremum_label": _entry("charts", "matrix", "charts", "matrix"),
    "task_charts__matrix__threshold_cell_count": _entry("charts", "matrix", "charts", "matrix"),
    "task_charts__multiseries__category_total_extremum_label": _entry("charts", "multiseries", "charts", "multiseries"),
    "task_charts__multiseries__ranked_metric_extremum_label": _entry("charts", "multiseries", "charts", "multiseries"),
    "task_charts__multiseries__series_comparison_count": _entry("charts", "multiseries", "charts", "multiseries"),
    "task_charts__parallel_coords__axis_condition_count": _entry("charts", "parallel_coords", "charts", "parallel_coordinates"),
    "task_charts__parallel_coords__axis_delta_extremum_label": _entry("charts", "parallel_coords", "charts", "parallel_coordinates"),
    "task_charts__parallel_coords__crossing_count": _entry("charts", "parallel_coords", "charts", "parallel_coordinates"),
    "task_charts__part_whole__adjacent_transfer_gap_value": _entry("charts", "part_whole", "charts", "composition"),
    "task_charts__part_whole__order_count_conversion_value": _entry("charts", "part_whole", "charts", "composition"),
    "task_charts__part_whole__order_sector_angle_value": _entry("charts", "part_whole", "charts", "composition"),
    "task_charts__part_whole__order_share_sum_value": _entry("charts", "part_whole", "charts", "composition"),
    "task_charts__pictogram__category_total_value": _entry("charts", "pictogram", "charts", "pictogram"),
    "task_charts__pictogram__group_difference_value": _entry("charts", "pictogram", "charts", "pictogram"),
    "task_charts__pictogram__threshold_count": _entry("charts", "pictogram", "charts", "pictogram"),
    "task_charts__radar__profile_advantage_count": _entry("charts", "radar", "charts", "radar"),
    "task_charts__radar__threshold_metric_count_for_panel": _entry("charts", "radar", "charts", "radar"),
    "task_charts__radar__threshold_panel_count": _entry("charts", "radar", "charts", "radar"),
    "task_charts__radial_progress__condition_count": _entry("charts", "radial_progress", "charts", "radial_progress"),
    "task_charts__radial_sankey__dominant_endpoint_label": _entry("charts", "radial_sankey", "charts", "flow"),
    "task_charts__radial_sankey__transfer_total_value": _entry("charts", "radial_sankey", "charts", "flow"),
    "task_charts__region_map__adjacent_condition_count": _entry("charts", "region_map", "charts", "map"),
    "task_charts__region_map__border_neighbor_count": _entry("charts", "region_map", "charts", "map"),
    "task_charts__region_map__continent_filtered_count": _entry("charts", "region_map", "charts", "map"),
    "task_charts__region_map__region_category_count": _entry("charts", "region_map", "charts", "map"),
    "task_charts__region_map__region_value_count": _entry("charts", "region_map", "charts", "map"),
    "task_charts__sankey__node_side_total_value": _entry("charts", "sankey", "charts", "flow"),
    "task_charts__sankey__path_value": _entry("charts", "sankey", "charts", "flow"),
    "task_charts__scatter_cluster__cluster_feature_extremum_label": _entry("charts", "scatter_cluster", "charts", "scatter"),
    "task_charts__scatter_cluster__cluster_trend_direction_label": _entry("charts", "scatter_cluster", "charts", "scatter"),
    "task_charts__scatter_readout__series_point_lookup_value": _entry("charts", "scatter_readout", "charts", "scatter"),
    "task_charts__scatter_readout__series_x_extremum_label": _entry("charts", "scatter_readout", "charts", "scatter"),
    "task_charts__single_series__counterfactual_value": _entry("charts", "single_series", "charts", "hypothetical"),
    "task_charts__single_series__interval_change_value": _entry("charts", "single_series", "charts", "trend"),
    "task_charts__single_series__monotone_streak_length": _entry("charts", "single_series", "charts", "trend"),
    "task_charts__single_series__order_statistic_label": _entry("charts", "single_series", "charts", "statistics"),
    "task_charts__single_series__order_statistic_value": _entry("charts", "single_series", "charts", "statistics"),
    "task_charts__single_series__threshold_crossing_label": _entry("charts", "single_series", "charts", "trend"),
    "task_charts__single_series__turning_point_count": _entry("charts", "single_series", "charts", "trend"),
    "task_charts__single_series__value_predicate_count": _entry("charts", "single_series", "charts", "counting"),
    "task_charts__size_encoding__category_total_extremum_label": _entry("charts", "size_encoding", "charts", "size_encoding"),
    "task_charts__size_encoding__filtered_item_extremum_label": _entry("charts", "size_encoding", "charts", "size_encoding"),
    "task_charts__size_encoding__reference_size_neighbor_label": _entry("charts", "size_encoding", "charts", "size_encoding"),
    "task_charts__small_multiple__aggregate_value": _entry("charts", "small_multiple", "charts", "composition"),
    "task_charts__small_multiple__difference_value": _entry("charts", "small_multiple", "charts", "composition"),
    "task_charts__sunburst__conditional_leaf_count": _entry("charts", "sunburst", "charts", "composition"),
    "task_charts__sunburst__parent_total_extremum_label": _entry("charts", "sunburst", "charts", "composition"),
    "task_charts__sunburst__parent_total_value": _entry("charts", "sunburst", "charts", "composition"),
    "task_charts__surface_3d__panel_variation_label": _entry("charts", "surface_3d", "charts", "three_d"),
    "task_charts__surface_3d__reference_nearest_label": _entry("charts", "surface_3d", "charts", "three_d"),
    "task_charts__surface_3d__series_trend_label": _entry("charts", "surface_3d", "charts", "three_d"),
    "task_charts__surface_3d__surface_extremum_label": _entry("charts", "surface_3d", "charts", "three_d"),
    "task_charts__table__column_rank_label": _entry("charts", "table", "charts", "table_ranking"),
    "task_charts__table__column_summary_value": _entry("charts", "table", "charts", "table_statistics"),
    "task_charts__table__temporal_row_interval_difference_value": _entry("charts", "table", "charts", "table_temporal"),
    "task_charts__table__value_predicate_count": _entry("charts", "table", "charts", "table_counting"),
    "task_charts__treemap__group_total_value": _entry("charts", "treemap", "charts", "composition"),
    "task_charts__treemap__repeated_leaf_aggregate_value": _entry("charts", "treemap", "charts", "composition"),
    "task_charts__violin__feature_extremum_label": _entry("charts", "violin", "charts", "distribution"),
    "task_charts__violin__shape_feature_label": _entry("charts", "violin", "charts", "distribution"),
    "task_charts__waterfall__counterfactual_final_value": _entry("charts", "waterfall", "charts", "waterfall"),
    "task_charts__waterfall__running_total_value": _entry("charts", "waterfall", "charts", "waterfall"),
    "task_charts__waterfall__threshold_crossing_label": _entry("charts", "waterfall", "charts", "waterfall"),
    # Pages: structured page, diagram-like, map, schedule, and static UI scenes.
    "task_pages__form_section__section_expression_value": _entry("pages", "form_section", "pages", "arithmetic"),
    "task_pages__calendar__marked_day_class_count": _entry("pages", "calendar", "pages", "calendar"),
    "task_pages__calendar__weekday_occurrence_date": _entry("pages", "calendar", "pages", "calendar"),
    "task_pages__concept_map__branch_item_count": _entry("pages", "concept_map", "pages", "concept_map"),
    "task_pages__concept_map__filtered_node_count": _entry("pages", "concept_map", "pages", "concept_map"),
    "task_pages__concept_map__ordered_child_label": _entry("pages", "concept_map", "pages", "concept_map"),
    "task_pages__paired_forms__reconciliation_value": _entry("pages", "paired_forms", "pages", "cross_form"),
    "task_pages__cycle__offset_stage_label": _entry("pages", "cycle", "pages", "cycle"),
    "task_pages__hierarchy__tree_count": _entry("pages", "hierarchy", "pages", "hierarchy"),
    "task_pages__infographic__column_profile_comparison_value": _entry("pages", "infographic", "pages", "infographic"),
    "task_pages__infographic__filtered_section_extremum_label": _entry("pages", "infographic", "pages", "infographic"),
    "task_pages__infographic__filtered_metric_total_value": _entry("pages", "infographic", "pages", "infographic"),
    "task_pages__infographic__metric_arithmetic_value": _entry("pages", "infographic", "pages", "infographic"),
    "task_pages__infographic__section_ranked_total_label": _entry("pages", "infographic", "pages", "infographic"),
    "task_pages__map__navigation_label": _entry("pages", "map", "pages", "map"),
    "task_pages__process_flow__actor_handoff_count": _entry("pages", "process_flow", "pages", "process_flow"),
    "task_pages__process_flow__condition_path_endpoint_label": _entry("pages", "process_flow", "pages", "process_flow"),
    "task_pages__process_flow__filtered_node_count": _entry("pages", "process_flow", "pages", "process_flow"),
    "task_pages__control_board__filter_count": _entry("pages", "control_board", "pages", "counting"),
    "task_pages__command_matrix__command_intent_target_label": _entry("pages", "command_matrix", "pages", "relation"),
    "task_pages__navigation_flow__navigation_path_target_label": _entry("pages", "navigation_flow", "pages", "relation"),
    "task_pages__workspace__professional_target_label": _entry("pages", "workspace", "pages", "relation"),
    "task_pages__web_action__web_action_target_label": _entry("pages", "web_action", "pages", "relation"),
    "task_pages__schedule__longer_than_reference_count": _entry("pages", "schedule", "pages", "schedule"),
    "task_pages__schedule__maximum_non_overlapping_count": _entry("pages", "schedule", "pages", "schedule"),
    "task_pages__schedule__overlap_count": _entry("pages", "schedule", "pages", "schedule"),
    "task_pages__schema__field_role_count": _entry("pages", "schema", "pages", "schema"),
    "task_pages__schema__relationship_count": _entry("pages", "schema", "pages", "schema"),
    "task_pages__timeline__interval_membership_count": _entry("pages", "timeline", "pages", "timeline"),
    # Games.
    "task_games__backgammon__destination_count": _entry("games", "backgammon", "games", "backgammon"),
    "task_games__battleship__ship_status_count": _entry("games", "battleship", "games", "battleship"),
    "task_games__bingo__completed_line_count": _entry("games", "bingo", "games", "bingo"),
    "task_games__bingo__line_sum_extremum_value": _entry("games", "bingo", "games", "bingo"),
    "task_games__bowling__first_pin_hit_label": _entry("games", "bowling", "games", "bowling"),
    "task_games__bowling__spare_path_label": _entry("games", "bowling", "games", "bowling"),
    "task_games__brick_breaker__hit_row_remaining_count": _entry("games", "brick_breaker", "games", "brick_breaker"),
    "task_games__brick_breaker__trajectory_target_label": _entry("games", "brick_breaker", "games", "brick_breaker"),
    "task_games__2048__best_move_label": _entry("games", "2048", "games", "2048"),
    "task_games__2048__move_result_value": _entry("games", "2048", "games", "2048"),
    "task_games__bubble_shooter__pop_color_label": _entry("games", "bubble_shooter", "games", "bubble_shooter"),
    "task_games__bubble_shooter__shot_effect_count": _entry("games", "bubble_shooter", "games", "bubble_shooter"),
    "task_games__cards__blackjack_best_hand_label": _entry("games", "cards", "games", "cards"),
    "task_games__cards__exact_triple_count": _entry("games", "cards", "games", "cards"),
    "task_games__cards__longest_run_length": _entry("games", "cards", "games", "cards"),
    "task_games__cards__poker_best_hand_label": _entry("games", "cards", "games", "cards"),
    "task_games__cards__reference_condition_count": _entry("games", "cards", "games", "cards"),
    "task_games__cards__trick_taking_winner_label": _entry("games", "cards", "games", "cards"),
    "task_games__checkers__move_count": _entry("games", "checkers", "games", "checkers"),
    "task_games__checkers__max_capture_chain_length": _entry("games", "checkers", "games", "checkers"),
    "task_games__chess__check_attacker_count": _entry("games", "chess", "games", "chess"),
    "task_games__chess__king_escape_square_count": _entry("games", "chess", "games", "chess"),
    "task_games__chess__marked_piece_destination_count": _entry("games", "chess", "games", "chess"),
    "task_games__chess__player_capture_piece_count": _entry("games", "chess", "games", "chess"),
    "task_games__chess_variant__marked_piece_destination_count": _entry("games", "chess_variant", "games", "chess_variant"),
    "task_games__connect_four__move_count": _entry("games", "connect_four", "games", "connect_four"),
    "task_games__crossing__collision_time_value": _entry("games", "crossing", "games", "crossing"),
    "task_games__crossing__moving_object_count": _entry("games", "crossing", "games", "crossing"),
    "task_games__crossing__safe_route_label": _entry("games", "crossing", "games", "crossing"),
    "task_games__darts__condition_count": _entry("games", "darts", "games", "darts"),
    "task_games__darts__total_score_option_label": _entry("games", "darts", "games", "darts"),
    "task_games__dominoes__property_count": _entry("games", "dominoes", "games", "dominoes"),
    "task_games__dominoes__two_step_extension_label": _entry("games", "dominoes", "games", "dominoes"),
    "task_games__dots_and_boxes__capture_move_count": _entry("games", "dots_and_boxes", "games", "dots_and_boxes"),
    "task_games__dots_and_boxes__three_sided_box_count": _entry("games", "dots_and_boxes", "games", "dots_and_boxes"),
    "task_games__go__group_adjacent_enemy_count": _entry("games", "go", "games", "go"),
    "task_games__go__group_liberty_count": _entry("games", "go", "games", "go"),
    "task_games__hex__connection_gap_count": _entry("games", "hex", "games", "hex"),
    "task_games__hex__winning_move_cell_label": _entry("games", "hex", "games", "hex"),
    "task_games__marble_chain__shot_direction_label": _entry("games", "marble_chain", "games", "marble_chain"),
    "task_games__marble_chain__shot_effect_value": _entry("games", "marble_chain", "games", "marble_chain"),
    "task_games__match3__best_swap_label": _entry("games", "match3", "games", "match3"),
    "task_games__match3__swap_effect_value": _entry("games", "match3", "games", "match3"),
    "task_games__minecraft__ore_block_count": _entry("games", "minecraft", "games", "minecraft"),
    "task_games__minecraft__resource_route_cost_value": _entry("games", "minecraft", "games", "minecraft"),
    "task_games__minecraft__tunnel_clearance_count": _entry("games", "minecraft", "games", "minecraft"),
    "task_games__minesweeper__forced_cell_count": _entry("games", "minesweeper", "games", "minesweeper"),
    "task_games__minesweeper__satisfied_clue_count": _entry("games", "minesweeper", "games", "minesweeper"),
    "task_games__minigolf__first_obstacle_label": _entry("games", "minigolf", "games", "minigolf"),
    "task_games__minigolf__shot_path_label": _entry("games", "minigolf", "games", "minigolf"),
    "task_games__nine_mens_morris__pieces_in_mill_count": _entry("games", "nine_mens_morris", "games", "nine_mens_morris"),
    "task_games__pacman__next_item_label": _entry("games", "pacman", "games", "pacman"),
    "task_games__pacman__route_pellet_count": _entry("games", "pacman", "games", "pacman"),
    "task_games__platformer__collectible_count": _entry("games", "platformer", "games", "platformer"),
    "task_games__platformer__jump_landing_label": _entry("games", "platformer", "games", "platformer"),
    "task_games__pool__blocking_ball_count": _entry("games", "pool", "games", "pool"),
    "task_games__pool__pottable_ball_count": _entry("games", "pool", "games", "pool"),
    "task_games__reversi__marked_move_flip_count": _entry("games", "reversi", "games", "reversi"),
    "task_games__reversi__legal_destination_count": _entry("games", "reversi", "games", "reversi"),
    "task_games__rhythm__hit_window_count": _entry("games", "rhythm", "games", "rhythm"),
    "task_games__rhythm__lane_choice_value": _entry("games", "rhythm", "games", "rhythm"),
    "task_games__snake__safe_direction_count": _entry("games", "snake", "games", "snake"),
    "task_games__snake__path_outcome_option_label": _entry("games", "snake", "games", "snake"),
    "task_games__solitaire__foundation_ready_count": _entry("games", "solitaire", "games", "solitaire"),
    "task_games__solitaire__move_legality_label": _entry("games", "solitaire", "games", "solitaire"),
    "task_games__solitaire__tableau_sequence_count": _entry("games", "solitaire", "games", "solitaire"),
    "task_games__space_shooter__clear_shot_count": _entry("games", "space_shooter", "games", "space_shooter"),
    "task_games__space_shooter__highest_threat_label": _entry("games", "space_shooter", "games", "space_shooter"),
    "task_games__space_shooter__projectile_intercept_count": _entry("games", "space_shooter", "games", "space_shooter"),
    "task_games__space_shooter__safe_lane_count": _entry("games", "space_shooter", "games", "space_shooter"),
    "task_games__snakes_ladders__best_roll_value": _entry("games", "snakes_ladders", "games", "snakes_ladders"),
    "task_games__snakes_ladders__move_outcome_value": _entry("games", "snakes_ladders", "games", "snakes_ladders"),
    "task_games__sudoku__marked_cell_value": _entry("games", "sudoku", "games", "sudoku"),
    "task_games__sudoku__marked_cell_candidate_count": _entry("games", "sudoku", "games", "sudoku"),
    "task_games__sudoku__repeated_digit_count": _entry("games", "sudoku", "games", "sudoku"),
    "task_games__sudoku__unit_missing_digits_count": _entry("games", "sudoku", "games", "sudoku"),
    "task_games__tetris__drop_result_label": _entry("games", "tetris", "games", "tetris"),
    "task_games__tetris__line_clear_count": _entry("games", "tetris", "games", "tetris"),
    "task_games__ultimate_tictactoe__local_tactic_label": _entry(
        "games", "ultimate_tictactoe", "games", "ultimate_tictactoe"
    ),
    "task_games__ultimate_tictactoe__small_board_status_count": _entry(
        "games", "ultimate_tictactoe", "games", "ultimate_tictactoe"
    ),
    # Geometry.
    "task_geometry__function_panels__relation_property_label": _entry("geometry", "function_panels", "geometry", "analytical"),
    "task_geometry__function_panels__intersection_property_label": _entry("geometry", "function_panels", "geometry", "analytical"),
    "task_geometry__circle_theorem__diameter_perpendicular_chord_length_value": _entry("geometry", "circle_theorem", "geometry", "circle"),
    "task_geometry__circle_theorem__inscribed_angle_value": _entry("geometry", "circle_theorem", "geometry", "circle"),
    "task_geometry__circle_theorem__intersecting_chords_arc_measure_value": _entry("geometry", "circle_theorem", "geometry", "circle"),
    "task_geometry__circle_theorem__multi_step_angle_value": _entry("geometry", "circle_theorem", "geometry", "circle"),
    "task_geometry__circle_theorem__secant_secant_length_value": _entry("geometry", "circle_theorem", "geometry", "circle"),
    "task_geometry__circle_theorem__tangent_chord_angle_value": _entry("geometry", "circle_theorem", "geometry", "circle"),
    "task_geometry__circle_theorem__tangent_secant_length_value": _entry("geometry", "circle_theorem", "geometry", "circle"),
    "task_geometry__graph_paper__angle_extremum_label": _entry("geometry", "graph_paper", "geometry", "comparison"),
    "task_geometry__graph_paper__area_extremum_label": _entry("geometry", "graph_paper", "geometry", "comparison"),
    "task_geometry__graph_paper__length_extremum_label": _entry("geometry", "graph_paper", "geometry", "comparison"),
    "task_geometry__graph_paper__perimeter_extremum_label": _entry("geometry", "graph_paper", "geometry", "comparison"),
    "task_geometry__coordinate_plane__collinear_point_count": _entry("geometry", "coordinate_plane", "geometry", "coordinate"),
    "task_geometry__coordinate_plane__locus_panel_match_label": _entry("geometry", "coordinate_plane", "geometry", "coordinate"),
    "task_geometry__coordinate_plane__locus_point_label": _entry("geometry", "coordinate_plane", "geometry", "coordinate"),
    "task_geometry__coordinate_plane__missing_endpoint_label": _entry("geometry", "coordinate_plane", "geometry", "coordinate"),
    "task_geometry__coordinate_plane__point_in_polygon_count": _entry("geometry", "coordinate_plane", "geometry", "coordinate"),
    "task_geometry__coordinate_plane__quadrilateral_completion_label": _entry("geometry", "coordinate_plane", "geometry", "coordinate"),
    "task_geometry__coordinate_panels__quadrilateral_shape_match_label": _entry("geometry", "coordinate_panels", "geometry", "coordinate"),
    "task_geometry__coordinate_plane__same_quadrant_point_count": _entry("geometry", "coordinate_plane", "geometry", "coordinate"),
    "task_geometry__coordinate_plane__section_point_label": _entry("geometry", "coordinate_plane", "geometry", "coordinate"),
    "task_geometry__coordinate_plane__segment_relation_count": _entry("geometry", "coordinate_plane", "geometry", "coordinate"),
    "task_geometry__coordinate_plane__transformed_point_label": _entry("geometry", "coordinate_plane", "geometry", "coordinate"),
    "task_geometry__graph_paper__angle_type_count": _entry("geometry", "graph_paper", "geometry", "counting"),
    "task_geometry__graph_paper__polygon_convexity_count": _entry("geometry", "graph_paper", "geometry", "counting"),
    "task_geometry__graph_paper__quadrilateral_type_count": _entry("geometry", "graph_paper", "geometry", "counting"),
    "task_geometry__graph_paper__shape_type_count": _entry("geometry", "graph_paper", "geometry", "counting"),
    "task_geometry__graph_paper__triangle_type_count": _entry("geometry", "graph_paper", "geometry", "counting"),
    "task_geometry__function_graph__average_rate_value": _entry("geometry", "function_graph", "geometry", "graphing"),
    "task_geometry__function_graph__extremum_count": _entry("geometry", "function_graph", "geometry", "graphing"),
    "task_geometry__function_graph__reference_line_crossing_count": _entry("geometry", "function_graph", "geometry", "graphing"),
    "task_geometry__angle_relations__algebraic_angle_value": _entry("geometry", "angle_relations", "geometry", "measurement"),
    "task_geometry__triangle_relations__angle_bisector_segment_value": _entry("geometry", "triangle_relations", "geometry", "measurement"),
    "task_geometry__angle_relations__angle_chain_value": _entry("geometry", "angle_relations", "geometry", "measurement"),
    "task_geometry__graph_paper__angle_value": _entry("geometry", "graph_paper", "geometry", "measurement"),
    "task_geometry__triangle_relations__centroid_median_segment_value": _entry("geometry", "triangle_relations", "geometry", "measurement"),
    "task_geometry__graph_paper__circle_circumference_value": _entry("geometry", "graph_paper", "geometry", "measurement"),
    "task_geometry__composite_shape__composite_area_value": _entry("geometry", "composite_shape", "geometry", "measurement"),
    "task_geometry__composite_shape__composite_perimeter_value": _entry("geometry", "composite_shape", "geometry", "measurement"),
    "task_geometry__concentric_chord__concentric_circle_chord_value": _entry("geometry", "concentric_chord", "geometry", "measurement"),
    "task_geometry__cone_net__cone_sector_net_value": _entry("geometry", "cone_net", "geometry", "measurement"),
    "task_geometry__cuboid_views__cuboid_projection_surface_area_value": _entry("geometry", "cuboid_views", "geometry", "measurement"),
    "task_geometry__composite_shape__curvilinear_composite_area_value": _entry("geometry", "composite_shape", "geometry", "measurement"),
    "task_geometry__composite_shape__curvilinear_composite_perimeter_value": _entry("geometry", "composite_shape", "geometry", "measurement"),
    "task_geometry__composite_shape__curvilinear_missing_side_from_area_value": _entry("geometry", "composite_shape", "geometry", "measurement"),
    "task_geometry__composite_shape__curvilinear_sector_angle_value": _entry("geometry", "composite_shape", "geometry", "measurement"),
    "task_geometry__graph_paper__ellipse_area_value": _entry("geometry", "graph_paper", "geometry", "measurement"),
    "task_geometry__incircle_tangents__incircle_radius_from_area_value": _entry("geometry", "incircle_tangents", "geometry", "measurement"),
    "task_geometry__incircle_tangents__incircle_tangent_perimeter_value": _entry("geometry", "incircle_tangents", "geometry", "measurement"),
    "task_geometry__graph_paper__line_slope_value": _entry("geometry", "graph_paper", "geometry", "measurement"),
    "task_geometry__paper_fold__paper_fold_angle_value": _entry("geometry", "paper_fold", "geometry", "measurement"),
    "task_geometry__triangle_relations__parallel_section_length_value": _entry("geometry", "triangle_relations", "geometry", "measurement"),
    "task_geometry__area_partition__parallelogram_area_partition_total_area_value": _entry("geometry", "area_partition", "geometry", "measurement"),
    "task_geometry__graph_paper__polygon_area_value": _entry("geometry", "graph_paper", "geometry", "measurement"),
    "task_geometry__graph_paper__polygon_perimeter_value": _entry("geometry", "graph_paper", "geometry", "measurement"),
    "task_geometry__triangle_relations__pythagorean_length_value": _entry("geometry", "triangle_relations", "geometry", "measurement"),
    "task_geometry__pythagorean_dissection__pythagorean_square_area_value": _entry("geometry", "pythagorean_dissection", "geometry", "measurement"),
    "task_geometry__solid_revolution__revolution_cone_volume_value": _entry("geometry", "solid_revolution", "geometry", "measurement"),
    "task_geometry__solid_revolution__revolution_cylinder_volume_value": _entry("geometry", "solid_revolution", "geometry", "measurement"),
    "task_geometry__solid_revolution__revolution_double_cone_volume_value": _entry("geometry", "solid_revolution", "geometry", "measurement"),
    "task_geometry__solid_revolution__revolution_frustum_volume_value": _entry("geometry", "solid_revolution", "geometry", "measurement"),
    "task_geometry__triangle_relations__right_triangle_angle_value": _entry("geometry", "triangle_relations", "geometry", "measurement"),
    "task_geometry__triangle_relations__right_triangle_missing_side_value": _entry("geometry", "triangle_relations", "geometry", "measurement"),
    "task_geometry__sector__sector_angle_relation_value": _entry("geometry", "sector", "geometry", "measurement"),
    "task_geometry__sector__sector_measure_value": _entry("geometry", "sector", "geometry", "measurement"),
    "task_geometry__solid_cross_section__solid_cross_section_area_value": _entry("geometry", "solid_cross_section", "geometry", "measurement"),
    "task_geometry__solid_formula__solid_formula_missing_dimension_value": _entry("geometry", "solid_formula", "geometry", "measurement"),
    "task_geometry__tangent_packing__tangent_packing_length_value": _entry("geometry", "tangent_packing", "geometry", "measurement"),
    "task_geometry__tangent_packing__tangent_packing_shaded_area_value": _entry("geometry", "tangent_packing", "geometry", "measurement"),
    "task_geometry__trapezoid_extension__trapezoid_extension_area_value": _entry("geometry", "trapezoid_extension", "geometry", "measurement"),
    "task_geometry__trapezoid_extension__trapezoid_extension_length_value": _entry("geometry", "trapezoid_extension", "geometry", "measurement"),
    "task_geometry__area_partition__triangle_area_partition_total_area_value": _entry("geometry", "area_partition", "geometry", "measurement"),
    "task_geometry__shape_gallery__shape_relation_count": _entry("geometry", "shape_gallery", "geometry", "similarity"),
    "task_geometry__shape_gallery__transformation_match_label": _entry("geometry", "shape_gallery", "geometry", "transformation"),
    # Graph.
    "task_graph__node_link__degree_extremum_value": _entry("graph", "node_link", "graph", "comparison"),
    "task_graph__adjacency__component_count": _entry("graph", "adjacency", "graph", "counting"),
    "task_graph__node_link__articulation_point_count": _entry("graph", "node_link", "graph", "counting"),
    "task_graph__binary_tree__node_property_count": _entry("graph", "binary_tree", "graph", "counting"),
    "task_graph__node_link__bridge_count": _entry("graph", "node_link", "graph", "counting"),
    "task_graph__node_link__cross_color_edge_count": _entry("graph", "node_link", "graph", "counting"),
    "task_graph__node_link__degree_predicate_count": _entry("graph", "node_link", "graph", "counting"),
    "task_graph__node_link__edge_color_count": _entry("graph", "node_link", "graph", "counting"),
    "task_graph__node_link__edge_text_count": _entry("graph", "node_link", "graph", "counting"),
    "task_graph__node_link__isolated_after_removal_count": _entry("graph", "node_link", "graph", "counting"),
    "task_graph__node_link__named_node_degree_value": _entry("graph", "node_link", "graph", "counting"),
    "task_graph__node_link__node_color_count": _entry("graph", "node_link", "graph", "counting"),
    "task_graph__pipe_network__bridge_count": _entry("graph", "pipe_network", "graph", "counting"),
    "task_graph__metro__station_membership_count": _entry("graph", "metro", "graph", "counting"),
    "task_graph__flow_network__max_flow_value": _entry("graph", "flow_network", "graph", "optimization"),
    "task_graph__flow_network__min_cut_edge_count": _entry("graph", "flow_network", "graph", "optimization"),
    "task_graph__adjacency__mst_weight": _entry(
        "graph", "adjacency", "graph", "optimization"
    ),
    "task_graph__node_link__mst_weight": _entry("graph", "node_link", "graph", "optimization"),
    "task_graph__adjacency__traversal_kth_label": _entry("graph", "adjacency", "graph", "order"),
    "task_graph__binary_tree__traversal_kth_label": _entry("graph", "binary_tree", "graph", "order"),
    "task_graph__node_link__topological_position_value": _entry("graph", "node_link", "graph", "order"),
    "task_graph__node_link__longest_path_length": _entry("graph", "node_link", "graph", "path"),
    "task_graph__metro__shortest_path_length": _entry("graph", "metro", "graph", "path"),
    "task_graph__metro__transfer_count": _entry("graph", "metro", "graph", "path"),
    "task_graph__pipe_network__shortest_path_length": _entry("graph", "pipe_network", "graph", "path"),
    "task_graph__node_link__shortest_path_length": _entry("graph", "node_link", "graph", "path"),
    "task_graph__node_link__component_membership_count": _entry("graph", "node_link", "graph", "relation"),
    "task_graph__automaton__state_after_input_label": _entry("graph", "automaton", "graph", "relation"),
    "task_graph__automaton__accepted_string_label": _entry(
        "graph", "automaton", "graph", "relation"
    ),
    "task_graph__binary_tree__node_relation_label": _entry("graph", "binary_tree", "graph", "relation"),
    "task_graph__node_link__common_neighbor_count": _entry("graph", "node_link", "graph", "relation"),
    "task_graph__node_link__edge_attribute_label": _entry("graph", "node_link", "graph", "relation"),
    "task_graph__pipe_network__junction_path_count": _entry("graph", "pipe_network", "graph", "relation"),
    "task_graph__metro__exact_distance_station_count": _entry("graph", "metro", "graph", "relation"),
    "task_graph__node_link__reachable_node_count": _entry("graph", "node_link", "graph", "relation"),
    "task_graph__binary_tree__tree_operation_label": _entry("graph", "binary_tree", "graph", "relation"),
    "task_graph__graph_options__structure_match_label": _entry("graph", "graph_options", "graph", "relation"),
    "task_graph__node_link__unique_node_label": _entry("graph", "node_link", "graph", "relation"),
    "task_graph__node_link__unique_cycle_size": _entry("graph", "node_link", "graph", "relation"),
    # Icons.
    "task_icons__icon_field__type_frequency_count": _entry("icons", "icon_field", "icons", "counting"),
    "task_icons__reference_canvas__attribute_match_count": _entry("icons", "reference_canvas", "icons", "counting"),
    "task_icons__reference_canvas__size_relation_count": _entry("icons", "reference_canvas", "icons", "counting"),
    "task_icons__reference_canvas__anchor_position_count": _entry("icons", "reference_canvas", "icons", "relation"),
    "task_icons__named_field__shape_count": _entry("icons", "named_field", "icons", "counting"),
    "task_icons__named_field__shape_attribute_boolean_count": _entry("icons", "named_field", "icons", "counting"),
    "task_icons__named_field__shape_pair_total_count": _entry("icons", "named_field", "icons", "counting"),
    "task_icons__named_field__shape_pair_difference_count": _entry("icons", "named_field", "icons", "counting"),
    "task_icons__named_field__closer_to_reference_count": _entry("icons", "named_field", "icons", "counting"),
    "task_icons__named_field__shape_counterfactual_count": _entry("icons", "named_field", "icons", "counting"),
    "task_icons__named_field__region_shape_count": _entry("icons", "named_field", "icons", "counting"),
    "task_icons__named_field__reference_distance_rank_label": _entry("icons", "named_field", "icons", "relation"),
    "task_icons__venn_field__venn_region_shape_count": _entry("icons", "venn_field", "icons", "counting"),
    "task_icons__paired_canvas__panel_difference_count": _entry("icons", "paired_canvas", "icons", "counting"),
    "task_icons__paired_canvas__panel_exact_match_count": _entry("icons", "paired_canvas", "icons", "counting"),
    "task_icons__paired_canvas__panel_movement_direction_count": _entry("icons", "paired_canvas", "icons", "relation"),
    "task_icons__paired_canvas__panel_attribute_change_count": _entry("icons", "paired_canvas", "icons", "transformation"),
    "task_icons__paired_canvas__original_attribute_label": _entry("icons", "paired_canvas", "icons", "relation"),
    "task_icons__pair_grid__pair_attribute_rule_count": _entry("icons", "pair_grid", "icons", "transformation"),
    "task_icons__pair_grid__pair_geometric_transform_count": _entry("icons", "pair_grid", "icons", "transformation"),
    "task_icons__mirror_grid__mirror_symmetry_count": _entry("icons", "mirror_grid", "icons", "relation"),
    "task_icons__mirror_grid__reflection_match_label": _entry("icons", "mirror_grid", "icons", "relation"),
    "task_icons__overlap_grid__occlusion_order_count": _entry("icons", "overlap_grid", "icons", "relation"),
    "task_icons__two_anchor__between_anchors_count": _entry("icons", "two_anchor", "icons", "relation"),
    "task_icons__pattern_grid__color_pattern_violation_index": _entry("icons", "pattern_grid", "icons", "pattern"),
    "task_icons__pattern_grid__size_pattern_violation_index": _entry("icons", "pattern_grid", "icons", "pattern"),
    "task_icons__sequence_strip__rotation_sequence_violation_index": _entry("icons", "sequence_strip", "icons", "pattern"),
    "task_icons__sequence_strip__missing_count_value": _entry("icons", "sequence_strip", "icons", "sequence"),
    # Illustrations.
    "task_illustrations__environment__lit_window_count": _entry(
        "illustrations", "environment", "illustrations", "counting"
    ),
    "task_illustrations__indoor_room__container_object_count": _entry("illustrations", "indoor_room", "illustrations", "counting"),
    "task_illustrations__market__customer_at_shop_count": _entry(
        "illustrations", "market", "illustrations", "counting"
    ),
    "task_illustrations__construction_site__equipment_zone_count": _entry(
        "illustrations", "construction_site", "illustrations", "counting"
    ),
    "task_illustrations__environment__feature_relation_count": _entry(
        "illustrations", "environment", "illustrations", "counting"
    ),
    "task_illustrations__library__section_book_count": _entry("illustrations", "library", "illustrations", "counting"),
    "task_illustrations__market__shop_attribute_count": _entry(
        "illustrations", "market", "illustrations", "counting"
    ),
    "task_illustrations__construction_site__material_stack_count": _entry(
        "illustrations", "construction_site", "illustrations", "counting"
    ),
    "task_illustrations__indoor_room__surface_object_count": _entry(
        "illustrations", "indoor_room", "illustrations", "counting"
    ),
    "task_illustrations__park_playground__person_count": _entry(
        "illustrations", "park_playground", "illustrations", "counting"
    ),
    "task_illustrations__park_playground__playground_equipment_count": _entry(
        "illustrations", "park_playground", "illustrations", "counting"
    ),
    "task_illustrations__transit_terminal__entity_location_count": _entry(
        "illustrations", "transit_terminal", "illustrations", "counting"
    ),
    "task_illustrations__object_field__object_type_count": _entry("illustrations", "object_field", "illustrations", "counting"),
    "task_illustrations__object_field__visible_part_count": _entry("illustrations", "object_field", "illustrations", "counting"),
    "task_illustrations__construction_site__worker_attribute_count": _entry(
        "illustrations", "construction_site", "illustrations", "counting"
    ),
    "task_illustrations__single_object_figure__visible_part_count": _entry(
        "illustrations", "single_object_figure", "illustrations", "counterfactual"
    ),
    "task_illustrations__source_scene_edit__object_count_after_edit": _entry(
        "illustrations", "source_scene_edit", "illustrations", "counterfactual"
    ),
    "task_illustrations__indoor_room__furniture_side_count": _entry("illustrations", "indoor_room", "illustrations", "relation"),
    "task_illustrations__object_field__named_object_side_count": _entry("illustrations", "object_field", "illustrations", "relation"),
    "task_illustrations__image_cutout_board__jigsaw_piece_order": _entry("illustrations", "image_cutout_board", "illustrations", "visual"),
    "task_illustrations__missing_patch__missing_patch_label": _entry("illustrations", "missing_patch", "illustrations", "visual"),
    "task_illustrations__scene_options__odd_scene_label": _entry(
        "illustrations", "scene_options", "illustrations", "visual"
    ),
    "task_illustrations__difference_pair__object_difference_count": _entry(
        "illustrations", "difference_pair", "illustrations", "visual"
    ),
    "task_illustrations__image_cutout_board__rotated_tile_label": _entry(
        "illustrations", "image_cutout_board", "illustrations", "visual"
    ),
    # Physics.
    "task_physics__paired_resistor__missing_resistor_value": _entry("physics", "paired_resistor", "physics", "circuits"),
    "task_physics__resistor__total_resistance_value": _entry("physics", "resistor", "physics", "circuits"),
    "task_physics__electrostatic_field__field_direction_choice": _entry("physics", "electrostatic_field", "physics", "electrostatics"),
    "task_physics__electrostatic_field__potential_value": _entry("physics", "electrostatic_field", "physics", "electrostatics"),
    "task_physics__electrostatic_field__zero_field_point_label": _entry("physics", "electrostatic_field", "physics", "electrostatics"),
    "task_physics__hydraulic__hydraulic_missing_value": _entry("physics", "hydraulic", "physics", "fluids"),
    "task_physics__magnetic_force__force_direction_choice": _entry("physics", "magnetic_force", "physics", "magnetism"),
    "task_physics__lever__missing_weight_balance_value": _entry("physics", "lever", "physics", "mechanics"),
    "task_physics__pulley__pulley_mechanical_advantage": _entry("physics", "pulley", "physics", "mechanics"),
    "task_physics__lever__side_torque_value": _entry("physics", "lever", "physics", "mechanics"),
    "task_physics__collision__sticky_collision_direction_choice": _entry("physics", "collision", "physics", "mechanics"),
    "task_physics__collision__sticky_collision_velocity_component_value": _entry("physics", "collision", "physics", "mechanics"),
    "task_physics__spring__spring_extension_difference": _entry("physics", "spring", "physics", "mechanics"),
    "task_physics__spring__spring_missing_value": _entry("physics", "spring", "physics", "mechanics"),
    "task_physics__ray_optics__ray_bounce_count": _entry("physics", "ray_optics", "physics", "optics"),
    "task_physics__ray_optics__ray_target_hit_count": _entry("physics", "ray_optics", "physics", "optics"),
    "task_physics__pv_diagram__pv_process_sign_choice": _entry("physics", "pv_diagram", "physics", "thermodynamics"),
    "task_physics__pv_diagram__pv_work_value": _entry("physics", "pv_diagram", "physics", "thermodynamics"),
    "task_physics__wave_interference__interference_point_choice": _entry("physics", "wave_interference", "physics", "waves"),
    "task_physics__wave_interference__path_difference_value": _entry("physics", "wave_interference", "physics", "waves"),
    # Synthetic 3D scenes.
    "task_three_d__object_scene__between_references_label": _entry("three_d", "object_scene", "three_d", "spatial"),
    "task_three_d__object_scene__camera_distance_extremum_label": _entry("three_d", "object_scene", "three_d", "spatial"),
    "task_three_d__object_scene__height_extremum_label": _entry("three_d", "object_scene", "three_d", "spatial"),
    "task_three_d__object_scene__occlusion_order_label": _entry("three_d", "object_scene", "three_d", "spatial"),
    "task_three_d__object_scene__object_relation_label": _entry("three_d", "object_scene", "three_d", "spatial"),
    "task_three_d__object_scene__reference_nearest_label": _entry("three_d", "object_scene", "three_d", "spatial"),
    "task_three_d__room__wall_mounted_object_count": _entry("three_d", "room", "three_d", "room"),
    "task_three_d__room__wall_object_camera_distance_label": _entry("three_d", "room", "three_d", "room"),
    "task_three_d__room__wall_object_side_relation_label": _entry("three_d", "room", "three_d", "room"),
    "task_three_d__room__wall_object_same_wall_reference_label": _entry("three_d", "room", "three_d", "room"),
    "task_three_d__street__intersection_nearest_label": _entry("three_d", "street", "three_d", "street"),
    "task_three_d__street__lane_ahead_object_label": _entry("three_d", "street", "three_d", "street"),
    "task_three_d__street__same_road_arm_reference_label": _entry("three_d", "street", "three_d", "street"),
    "task_three_d__warehouse__robot_forward_path_label": _entry("three_d", "warehouse", "three_d", "warehouse"),
    "task_three_d__warehouse__robot_nearest_object_label": _entry("three_d", "warehouse", "three_d", "warehouse"),
    # Puzzles, including tile scenes.
    "task_puzzles__agent_automaton__agent_cell_flip_count": _entry("puzzles", "agent_automaton", "puzzles", "automaton"),
    "task_puzzles__agent_automaton__agent_final_pose_label": _entry("puzzles", "agent_automaton", "puzzles", "automaton"),
    "task_puzzles__life_automaton__life_future_grid_label": _entry("puzzles", "life_automaton", "puzzles", "automaton"),
    "task_puzzles__life_automaton__life_population_count": _entry("puzzles", "life_automaton", "puzzles", "automaton"),
    "task_puzzles__turing_tape__turing_written_symbol_count": _entry("puzzles", "turing_tape", "puzzles", "automaton"),
    "task_puzzles__counterfactual_board__board_grid_count": _entry("puzzles", "counterfactual_board", "puzzles", "counterfactual"),
    "task_puzzles__arithmetic_constraint__arithmetic_constraint_value": _entry("puzzles", "arithmetic_constraint", "puzzles", "logic"),
    "task_puzzles__arithmetic_constraint__cryptarithm_digit_value": _entry("puzzles", "arithmetic_constraint", "puzzles", "logic"),
    "task_puzzles__logic_grid__grid_king_non_touch_label": _entry("puzzles", "logic_grid", "puzzles", "logic"),
    "task_puzzles__logic_grid__grid_uniqueness_completion_label": _entry("puzzles", "logic_grid", "puzzles", "logic"),
    "task_puzzles__matchstick__matchstick_loose_endpoint_extremum_label": _entry("puzzles", "matchstick", "puzzles", "logic"),
    "task_puzzles__matchstick__matchstick_number_transform_label": _entry("puzzles", "matchstick", "puzzles", "logic"),
    "task_puzzles__nonogram__nonogram_candidate_solution_label": _entry("puzzles", "nonogram", "puzzles", "logic"),
    "task_puzzles__nonogram__nonogram_line_completion_label": _entry("puzzles", "nonogram", "puzzles", "logic"),
    "task_puzzles__arithmetic_constraint__number_wall_value": _entry("puzzles", "arithmetic_constraint", "puzzles", "logic"),
    "task_puzzles__arithmetic_constraint__operator_grid_value": _entry("puzzles", "arithmetic_constraint", "puzzles", "logic"),
    "task_puzzles__raven_matrix__raven_analogical_transform_label": _entry("puzzles", "raven_matrix", "puzzles", "logic"),
    "task_puzzles__raven_matrix__raven_count_progression_label": _entry("puzzles", "raven_matrix", "puzzles", "logic"),
    "task_puzzles__raven_matrix__raven_position_progression_label": _entry("puzzles", "raven_matrix", "puzzles", "logic"),
    "task_puzzles__raven_matrix__raven_set_operation_label": _entry("puzzles", "raven_matrix", "puzzles", "logic"),
    "task_puzzles__raven_matrix__raven_spatial_transform_label": _entry("puzzles", "raven_matrix", "puzzles", "logic"),
    "task_puzzles__star_battle__star_battle_remaining_count": _entry("puzzles", "star_battle", "puzzles", "logic"),
    "task_puzzles__star_battle__star_battle_valid_cell_label": _entry("puzzles", "star_battle", "puzzles", "logic"),
    "task_puzzles__tents__tents_missing_tent_cell_label": _entry("puzzles", "tents", "puzzles", "logic"),
    "task_puzzles__tents__tents_valid_candidate_count": _entry("puzzles", "tents", "puzzles", "logic"),
    "task_puzzles__music_staff__chord_harmony_label": _entry("puzzles", "music_staff", "puzzles", "notation"),
    "task_puzzles__music_staff__dominant_chord_count": _entry("puzzles", "music_staff", "puzzles", "notation"),
    "task_puzzles__music_staff__key_scale_label": _entry("puzzles", "music_staff", "puzzles", "notation"),
    "task_puzzles__music_staff__bar_count_value": _entry("puzzles", "music_staff", "puzzles", "notation"),
    "task_puzzles__music_staff__duration_equivalence_label": _entry("puzzles", "music_staff", "puzzles", "notation"),
    "task_puzzles__music_staff__meter_rhythm_label": _entry("puzzles", "music_staff", "puzzles", "notation"),
    "task_puzzles__music_staff__pitch_interval_label": _entry("puzzles", "music_staff", "puzzles", "notation"),
    "task_puzzles__dice_probability__dice_conditional_event_value": _entry("puzzles", "dice_probability", "puzzles", "probability"),
    "task_puzzles__dice_probability__dice_pair_event_value": _entry("puzzles", "dice_probability", "puzzles", "probability"),
    "task_puzzles__dice_probability__dice_single_event_value": _entry("puzzles", "dice_probability", "puzzles", "probability"),
    "task_puzzles__spinner_probability__spinner_compound_event_value": _entry("puzzles", "spinner_probability", "puzzles", "probability"),
    "task_puzzles__spinner_probability__spinner_pair_event_value": _entry("puzzles", "spinner_probability", "puzzles", "probability"),
    "task_puzzles__voxel_cube__cube_count": _entry("puzzles", "voxel_cube", "puzzles", "spatial"),
    "task_puzzles__voxel_cube__cube_painted_face_count": _entry("puzzles", "voxel_cube", "puzzles", "spatial"),
    "task_puzzles__voxel_cube__cube_projection_consistency_label": _entry("puzzles", "voxel_cube", "puzzles", "spatial"),
    "task_puzzles__voxel_cube__cube_projection_match_label": _entry("puzzles", "voxel_cube", "puzzles", "spatial"),
    "task_puzzles__cube_net__cube_net_face_relation_label": _entry("puzzles", "cube_net", "puzzles", "spatial"),
    "task_puzzles__cube_net__cube_rolling_result_label": _entry("puzzles", "cube_net", "puzzles", "spatial"),
    "task_puzzles__voxel_cube__cube_structure_change_count": _entry("puzzles", "voxel_cube", "puzzles", "spatial"),
    "task_puzzles__voxel_cube__cube_visible_projection_count": _entry("puzzles", "voxel_cube", "puzzles", "spatial"),
    "task_puzzles__polyomino_missing__polyomino_missing_region_piece_label": _entry("puzzles", "polyomino_missing", "puzzles", "spatial"),
    "task_puzzles__rubiks_net__rubiks_face_color_count_label": _entry("puzzles", "rubiks_net", "puzzles", "spatial"),
    "task_puzzles__rubiks_net__rubiks_move_result_label": _entry("puzzles", "rubiks_net", "puzzles", "spatial"),
    "task_puzzles__rubiks_net__rubiks_sticker_color_label": _entry("puzzles", "rubiks_net", "puzzles", "spatial"),
    "task_puzzles__sliding_block__sliding_block_blocker_count": _entry("puzzles", "sliding_block", "puzzles", "spatial"),
    "task_puzzles__sliding_block__sliding_block_move_result_label": _entry("puzzles", "sliding_block", "puzzles", "spatial"),
    "task_puzzles__sokoban__sokoban_box_target_relation_label": _entry("puzzles", "sokoban", "puzzles", "spatial"),
    "task_puzzles__sokoban__sokoban_path_sequence_label": _entry("puzzles", "sokoban", "puzzles", "spatial"),
    "task_puzzles__tangram__tangram_contact_count": _entry("puzzles", "tangram", "puzzles", "spatial"),
    "task_puzzles__tangram__tangram_missing_piece_label": _entry("puzzles", "tangram", "puzzles", "spatial"),
    "task_puzzles__overlay__overlay_result_label": _entry("puzzles", "overlay", "puzzles", "spatial"),
    "task_puzzles__paper_fold_cut__paper_fold_cut_result_label": _entry("puzzles", "paper_fold_cut", "puzzles", "spatial"),
    "task_puzzles__paper_fold__paper_fold_result_label": _entry("puzzles", "paper_fold", "puzzles", "spatial"),
    "task_puzzles__clock_collection__compare": _entry("puzzles", "clock_collection", "puzzles", "clock"),
    "task_puzzles__analog_clock__offset_readout": _entry("puzzles", "analog_clock", "puzzles", "clock"),
    "task_puzzles__cyclic_order__cyclic_order_equivalent_label": _entry("puzzles", "cyclic_order", "puzzles", "topology"),
    "task_puzzles__maze__exit_reachability_label": _entry("puzzles", "maze", "puzzles", "topology"),
    "task_puzzles__maze__reachable_exit_count": _entry("puzzles", "maze", "puzzles", "topology"),
    "task_puzzles__pipe_flow__pipe_flow_repair_tile_label": _entry("puzzles", "pipe_flow", "puzzles", "topology"),
    "task_puzzles__string_topology__string_component_count": _entry("puzzles", "string_topology", "puzzles", "topology"),
    "task_puzzles__voxel_ladder__voxel_ladder_route_count": _entry("puzzles", "voxel_ladder", "puzzles", "topology"),
    "task_puzzles__voxel_ladder__voxel_ladder_route_label": _entry("puzzles", "voxel_ladder", "puzzles", "topology"),
    "task_puzzles__color_gradient__color_gradient_completion_label": _entry("puzzles", "color_gradient", "puzzles", "visual"),
    "task_puzzles__color_gradient__color_gradient_violation_cell_label": _entry("puzzles", "color_gradient", "puzzles", "visual"),
    "task_puzzles__word_search__search_letter_count_value": _entry("puzzles", "word_search", "puzzles", "word"),
    "task_puzzles__word_search__search_location_label": _entry("puzzles", "word_search", "puzzles", "word"),
    "task_puzzles__word_search__search_present_word_count": _entry("puzzles", "word_search", "puzzles", "word"),
    "task_puzzles__cell_board__attribute_count": _entry("puzzles", "cell_board", "puzzles", "cell_board"),
    "task_puzzles__cell_board__color_region_count": _entry("puzzles", "cell_board", "puzzles", "cell_board"),
    "task_puzzles__cell_board__path_distance": _entry("puzzles", "cell_board", "puzzles", "cell_board"),
    "task_puzzles__cell_board__reachability_count": _entry("puzzles", "cell_board", "puzzles", "cell_board"),
    "task_puzzles__cell_board__symmetry_violation_count": _entry("puzzles", "cell_board", "puzzles", "cell_board"),
}


def canonical_domain(domain: str) -> str:
    """Return a normalized public domain label."""

    return str(domain or "").strip()


def lookup_task_taxonomy(task_id: str) -> TaxonomyEntry | None:
    """Return explicit taxonomy metadata for a known task id."""

    return TASK_TAXONOMY.get(str(task_id))


def resolve_task_taxonomy(
    task_id: str,
    *,
    source_domain: str = "",
    source_task_group: str = "",
) -> TaxonomyEntry:
    """Resolve taxonomy for known tasks, with a permissive fallback for tests/tools."""

    entry = lookup_task_taxonomy(str(task_id))
    if entry is not None:
        return entry

    fallback_domain = canonical_domain(str(source_domain or "unknown"))
    fallback_scene = str(source_task_group or "unknown").strip() or "unknown"
    return TaxonomyEntry(
        domain=fallback_domain,
        scene_id=fallback_scene,
        source_domain=str(source_domain or fallback_domain),
        source_task_group=str(source_task_group or fallback_scene),
    )


def resolve_task_query_id(
    *,
    query_variant: str | None = None,
    trace_payload: Mapping[str, Any] | None = None,
) -> str:
    """Resolve the diagnostic query id for one generated instance.

    ``query_id`` is the public branch identifier. ``query_variant`` is only an
    internal replay/sampling selector and is used here as a final fallback for
    wrappers that have not populated the public id yet.
    """

    trace_payload = trace_payload if isinstance(trace_payload, Mapping) else {}
    query_spec = trace_payload.get("query_spec") if isinstance(trace_payload.get("query_spec"), Mapping) else {}
    execution_trace = (
        trace_payload.get("execution_trace")
        if isinstance(trace_payload.get("execution_trace"), Mapping)
        else {}
    )
    for source in (query_spec, execution_trace):
        query_id = source.get("query_id") if isinstance(source, Mapping) else None
        if query_id is not None and str(query_id).strip():
            return str(query_id)

    variant = str(query_variant or "").strip()
    if variant and variant != "default":
        return variant
    return ""


def _string_or_empty(value: Any) -> str:
    """Return a stripped string value, or ``""`` for empty/None values."""

    text = str(value or "").strip()
    return text


def _mapping_values(trace_payload: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield metadata-bearing mappings from one trace payload."""

    for key in ("scene_ir", "query_spec", "render_spec", "execution_trace"):
        value = trace_payload.get(key)
        if not isinstance(value, Mapping):
            continue
        yield value
        relations = value.get("relations")
        if isinstance(relations, Mapping):
            yield relations
        params = value.get("params")
        if isinstance(params, Mapping):
            yield params
        prompt_variant = value.get("prompt_variant")
        if isinstance(prompt_variant, Mapping):
            yield prompt_variant
        prompt_variants = value.get("prompt_variants")
        if isinstance(prompt_variants, Mapping):
            for prompt_record in prompt_variants.values():
                if not isinstance(prompt_record, Mapping):
                    continue
                metadata = prompt_record.get("metadata")
                if isinstance(metadata, Mapping):
                    yield metadata


def _first_payload_value(trace_payload: Mapping[str, Any], *keys: str) -> str:
    """Return the first non-empty string stored under any key in trace metadata."""

    for mapping in _mapping_values(trace_payload):
        for key in keys:
            candidate = _string_or_empty(mapping.get(str(key)))
            if candidate:
                return candidate
    return ""


def inject_taxonomy_metadata(
    trace_payload: Mapping[str, Any],
    *,
    task_id: str,
    taxonomy: TaxonomyEntry,
    query_id: str = "",
    registered_domain: str = "",
    registered_task_group: str = "",
) -> dict[str, Any]:
    """Return a trace payload copy with explicit taxonomy metadata injected.

    Consumers should prefer the nested blocks:

    - ``public``: public dataset taxonomy and query id.
    - ``registered``: the registered wrapper task object that produced output.
    - ``source``: source implementation/config/prompt surfaces used internally.
    """

    payload = deepcopy(dict(trace_payload))
    public_task_id = str(task_id)
    public_query_id = str(query_id).strip()
    registered_domain_text = _string_or_empty(registered_domain) or taxonomy.domain
    registered_task_group_text = _string_or_empty(registered_task_group) or taxonomy.source_task_group
    source_task_id = _first_payload_value(payload, "source_task_id", "implementation_task_id")
    if not source_task_id:
        candidate_task_id = _first_payload_value(payload, "task_id")
        if candidate_task_id and candidate_task_id != public_task_id:
            source_task_id = candidate_task_id
    source_task_id = source_task_id or public_task_id
    source_domain = (
        _first_payload_value(payload, "source_domain", "implementation_domain")
        or registered_domain_text
    )
    source_task_group = (
        _first_payload_value(payload, "source_task_group", "implementation_task_group")
        or registered_task_group_text
    )
    prompt_domain = _first_payload_value(payload, "prompt_domain") or source_domain
    prompt_task_group = _first_payload_value(payload, "prompt_task_group") or source_task_group

    public_metadata = {
        "domain": taxonomy.domain,
        "scene_id": taxonomy.scene_id,
        "task_id": public_task_id,
    }
    if public_query_id:
        public_metadata["query_id"] = public_query_id
    registered_metadata = {
        "task_id": public_task_id,
        "domain": registered_domain_text,
        "task_group": registered_task_group_text,
    }
    source_metadata = {
        "implementation_task_id": source_task_id,
        "implementation_domain": source_domain,
        "implementation_task_group": source_task_group,
        "config_domain": registered_domain_text,
        "config_task_group": registered_task_group_text,
        "prompt_domain": prompt_domain,
        "prompt_task_group": prompt_task_group,
    }
    metadata = {
        "metadata_schema_version": "v0",
        "domain": taxonomy.domain,
        "scene_id": taxonomy.scene_id,
        "task_id": public_task_id,
        "public": public_metadata,
        "registered": registered_metadata,
        "source": source_metadata,
    }
    if public_query_id:
        metadata["query_id"] = public_query_id
    payload["taxonomy"] = metadata

    for key in ("scene_ir", "query_spec", "render_spec", "execution_trace"):
        value = payload.get(key)
        if not isinstance(value, dict):
            continue
        value.setdefault("domain", taxonomy.domain)
        value.setdefault("scene_id", taxonomy.scene_id)
        value.setdefault("task_id", public_task_id)
        if public_query_id:
            value.setdefault("query_id", public_query_id)

    return payload


def missing_taxonomy_task_ids(task_ids: Iterable[str]) -> list[str]:
    """Return task ids without explicit public taxonomy metadata."""

    return sorted(str(task_id) for task_id in task_ids if str(task_id) not in TASK_TAXONOMY)
