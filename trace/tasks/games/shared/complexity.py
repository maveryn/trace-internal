"""Shared normalized complexity helpers for games-domain tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from ....core.task_group_config import resolve_task_group_section_defaults
from ....core.types import TaskComplexity


def clamp_unit_interval(value: float) -> float:
    """Clamp one numeric value into the canonical `[0, 1]` interval."""

    return max(0.0, min(1.0, float(value)))


def normalize_linear(value: float, *, min_value: float, max_value: float) -> float:
    """Normalize one value over an inclusive numeric interval."""

    lower = float(min_value)
    upper = float(max_value)
    if float(upper) <= float(lower):
        return 0.0
    return clamp_unit_interval((float(value) - float(lower)) / (float(upper) - float(lower)))


def resolve_games_complexity_weights(
    task_group_defaults: Mapping[str, Any],
    *,
    task_id: str,
) -> Dict[str, float]:
    """Resolve active games-complexity weights for one task."""

    defaults = resolve_task_group_section_defaults(task_group_defaults, "complexity", task_id=task_id)
    raw_weights = defaults.get("criteria_weights", {})
    if not isinstance(raw_weights, Mapping):
        raise ValueError(f"complexity.criteria_weights must be a mapping for {task_id}")
    weights: Dict[str, float] = {}
    for criterion, raw_weight in raw_weights.items():
        weight = float(raw_weight)
        if float(weight) < 0.0:
            raise ValueError(f"complexity weight for '{criterion}' in {task_id} must be non-negative")
        if float(weight) == 0.0:
            continue
        weights[str(criterion)] = float(weight)
    if not weights:
        raise ValueError(f"missing positive games complexity weights for {task_id}")
    return weights


def build_games_complexity(
    *,
    weights: Mapping[str, float],
    components: Mapping[str, float],
) -> TaskComplexity:
    """Build one normalized weighted `TaskComplexity` payload."""

    active_weights = {str(key): float(value) for key, value in weights.items() if float(value) > 0.0}
    if not active_weights:
        raise ValueError("games complexity requires at least one positive active weight")
    normalized_components = {str(key): clamp_unit_interval(float(value)) for key, value in components.items()}
    missing = [criterion for criterion in active_weights if criterion not in normalized_components]
    if missing:
        raise ValueError(f"games complexity is missing active criteria: {missing}")
    total_weight = sum(active_weights.values())
    score = sum(
        float(active_weights[criterion]) * float(normalized_components[criterion])
        for criterion in active_weights
    ) / float(total_weight)
    return TaskComplexity(
        complexity_score=clamp_unit_interval(float(score)),
        complexity_components={criterion: float(normalized_components[criterion]) for criterion in active_weights},
    )


def build_games_cards_hand_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    card_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible playing-card hand-count scenes."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    row_count = max(1, int((int(card_count) + 7) // 8))
    visual_scan = clamp_unit_interval(
        (0.35 * normalize_linear(float(card_count), min_value=16.0, max_value=40.0))
        + (0.65 * normalize_linear(float(row_count), min_value=2.0, max_value=5.0))
    )
    card_reasoning_base = {
        "higher_than_reference_count": 0.00,
        "exact_triple_count": 0.33,
        "same_suit_as_reference_count": 0.66,
        "longest_run_length": 1.00,
    }.get(str(query_id), 1.00)
    card_reasoning = clamp_unit_interval(
        float(card_reasoning_base)
        + (0.05 * normalize_linear(float(target_answer), min_value=0.0, max_value=6.0))
    )
    ambiguity = clamp_unit_interval(
        (0.50 * normalize_linear(float(evidence_count), min_value=0.0, max_value=8.0))
        + (0.12 if str(query_id) == "longest_run_length" and int(row_count) > 1 else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=0.0, max_value=8.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "card_reasoning": float(card_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_dominoes_chain_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    candidate_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for chain-plus-tableau domino counting scenes."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.52 * normalize_linear(float(candidate_count), min_value=7.0, max_value=12.0))
        + (0.12 if str(scene_variant) == "two_row" else 0.0)
    )
    domino_reasoning = clamp_unit_interval(
        (
            0.40
            if str(query_id) == "double_count"
            else 0.46
            if str(query_id) == "sum_to_target_count"
            else 0.50
            if str(query_id) == "matching_end_count"
            else 0.62
            if str(query_id) == "two_step_extension_label"
            else 0.56
        )
        + (0.08 * normalize_linear(float(target_answer), min_value=0.0, max_value=5.0))
    )
    ambiguity = clamp_unit_interval(
        (0.18 * normalize_linear(float(evidence_count), min_value=0.0, max_value=8.0))
        + (0.10 if str(query_id) == "higher_sum_than_reference_count" else 0.0)
        + (0.12 if str(query_id) == "two_step_extension_label" else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=0.0, max_value=8.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "card_reasoning": float(domino_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_darts_score_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    dart_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible dartboard score/count scenes."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.58 * normalize_linear(float(dart_count), min_value=1.0, max_value=9.0))
    )
    board_reasoning = {
        "total_score": 0.74,
        "ring_count": 0.36,
        "threshold_score_count": 0.58,
    }.get(str(query_id), 0.50)
    arithmetic_load = clamp_unit_interval(
        (0.72 if str(query_id) == "total_score" else 0.28 if str(query_id) == "threshold_score_count" else 0.10)
        + (0.08 * normalize_linear(float(target_answer), min_value=0.0, max_value=140.0))
    )
    output_burden = normalize_linear(float(evidence_count), min_value=0.0, max_value=9.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "board_reasoning": float(board_reasoning),
            "arithmetic_load": float(arithmetic_load),
            "output_burden": float(output_burden),
        },
    )


def build_games_reversi_move_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    board_size: int,
    legal_move_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Reversi move-count scenes."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.42 * normalize_linear(float(board_size), min_value=6.0, max_value=8.0))
        + (0.22 * normalize_linear(float(legal_move_count), min_value=0.0, max_value=10.0))
        + (0.08 if str(scene_variant) == "classic_board" else 0.0)
    )
    board_reasoning = clamp_unit_interval(
        (
            0.42
            if str(query_id) == "legal_move_count"
            else 0.52
            if str(query_id) == "corner_move_count"
            else 0.60
        )
        + (0.10 * normalize_linear(float(target_answer), min_value=0.0, max_value=8.0))
    )
    ambiguity = clamp_unit_interval(
        (0.18 * normalize_linear(float(evidence_count), min_value=0.0, max_value=8.0))
        + (0.12 if str(query_id) == "corner_move_count" and int(target_answer) == 0 else 0.0)
        + (0.08 if str(query_id) == "flip_count_for_marked_move" else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=0.0, max_value=8.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "card_reasoning": float(board_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_bingo_completed_line_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    query_id: str,
    marked_cell_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for bingo completed-line counting scenes."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.44 * normalize_linear(float(marked_cell_count), min_value=0.0, max_value=25.0))
        + (0.10 if str(query_id) == "line_sum_extremum_value" else 0.0)
    )
    axis_reasoning = {
        "completed_axis_line_count": 0.36,
        "completed_row_count": 0.34,
        "completed_column_count": 0.38,
        "line_sum_extremum_value": 0.72,
    }.get(str(query_id))
    state_reasoning = clamp_unit_interval(
        (float(axis_reasoning) if axis_reasoning is not None else 0.54)
        + (0.12 * normalize_linear(float(target_answer), min_value=0.0, max_value=8.0))
    )
    ambiguity = clamp_unit_interval(
        (0.18 * normalize_linear(float(evidence_count), min_value=0.0, max_value=25.0))
        + (0.05 if str(query_id) == "line_sum_extremum_value" else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=0.0, max_value=25.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "state_reasoning": float(state_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_connect_four_move_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    occupied_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Connect Four move-count scenes."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.50 * normalize_linear(float(occupied_count), min_value=8.0, max_value=32.0))
        + (0.10 if str(scene_variant) == "crowded_board" else 0.0)
    )
    board_reasoning = clamp_unit_interval(
        (0.44 if str(query_id) == "winning_move_count" else 0.56)
        + (0.10 * normalize_linear(float(target_answer), min_value=0.0, max_value=6.0))
    )
    ambiguity = clamp_unit_interval(
        (0.18 * normalize_linear(float(evidence_count), min_value=0.0, max_value=12.0))
        + (0.10 if str(query_id) == "safe_move_count" and int(target_answer) == 0 else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=0.0, max_value=12.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "card_reasoning": float(board_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_dots_and_boxes_capture_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    query_id: str,
    box_rows: int,
    box_cols: int,
    drawn_edge_count: int,
    target_answer: int,
    path_turn_count: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for dots-and-boxes board-state count scenes."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    total_boxes = int(box_rows) * int(box_cols)
    visual_scan = clamp_unit_interval(
        (0.30 * normalize_linear(float(total_boxes), min_value=6.0, max_value=16.0))
        + (0.30 * normalize_linear(float(drawn_edge_count), min_value=3.0, max_value=22.0))
    )
    query_base = {
        "marked_box_missing_side_count": 0.22,
        "three_sided_box_count": 0.34,
        "capture_move_count": 0.42,
        "highlighted_candidate_capture_count": 0.38,
        "forced_turn_capture_count": 0.52,
    }.get(str(query_id), 0.34)
    state_reasoning = clamp_unit_interval(
        float(query_base)
        + (0.22 * normalize_linear(float(target_answer), min_value=0.0, max_value=6.0))
        + (0.12 * normalize_linear(float(path_turn_count), min_value=0.0, max_value=5.0))
    )
    ambiguity = clamp_unit_interval(
        (0.08 * normalize_linear(float(path_turn_count), min_value=0.0, max_value=5.0))
        + (0.08 if str(query_id) == "capture_move_count" else 0.0)
        + (0.06 if int(target_answer) >= 4 else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=0.0, max_value=6.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "state_reasoning": float(state_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_checkers_move_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    occupied_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Checkers move-count scenes."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.48 * normalize_linear(float(occupied_count), min_value=6.0, max_value=18.0))
        + (0.10 if str(scene_variant) == "crowded_board" else 0.0)
    )
    board_reasoning_base = {
        "legal_move_count": 0.44,
        "capture_move_count": 0.56,
        "max_capture_chain_length": 0.72,
    }.get(str(query_id), 0.56)
    board_reasoning = clamp_unit_interval(
        float(board_reasoning_base)
        + (0.10 * normalize_linear(float(target_answer), min_value=0.0, max_value=5.0))
    )
    ambiguity = clamp_unit_interval(
        (0.18 * normalize_linear(float(evidence_count), min_value=0.0, max_value=6.0))
        + (0.10 if str(query_id) == "capture_move_count" and int(target_answer) == 0 else 0.0)
        + (0.08 if str(query_id) == "max_capture_chain_length" else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=0.0, max_value=6.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "card_reasoning": float(board_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_nine_mens_morris_pieces_in_mill_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    query_id: str,
    total_piece_count: int,
    target_answer: int,
    overlapping_piece_count: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for nine-men's-morris mill-piece counting scenes."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(normalize_linear(float(total_piece_count), min_value=6.0, max_value=18.0))
    state_reasoning = clamp_unit_interval(
        (0.36 if str(query_id) != "all_pieces_in_mill_count" else 0.50)
        + (0.18 * normalize_linear(float(target_answer), min_value=0.0, max_value=18.0))
        + (0.12 * normalize_linear(float(overlapping_piece_count), min_value=0.0, max_value=4.0))
    )
    ambiguity = clamp_unit_interval(
        (0.12 * normalize_linear(float(overlapping_piece_count), min_value=0.0, max_value=4.0))
        + (0.08 if str(query_id) == "all_pieces_in_mill_count" and int(target_answer) == 0 else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=0.0, max_value=18.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "state_reasoning": float(state_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_go_group_property_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    occupied_count: int,
    marked_group_size: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Go group-property counting scenes."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.42 * normalize_linear(float(occupied_count), min_value=8.0, max_value=28.0))
        + (0.10 if str(scene_variant) == "crowded_board" else 0.0)
    )
    if str(query_id) == "marked_group_adjacent_enemy_count":
        variant_base = 0.46
        answer_min, answer_max = 3.0, 8.0
    elif str(query_id) == "marked_group_shared_liberty_count":
        variant_base = 0.50
        answer_min, answer_max = 1.0, 5.0
    else:
        variant_base = 0.40
        answer_min, answer_max = 1.0, 6.0
    board_reasoning = clamp_unit_interval(
        float(variant_base)
        + (0.18 * normalize_linear(float(marked_group_size), min_value=1.0, max_value=9.0))
        + (0.18 * normalize_linear(float(target_answer), min_value=float(answer_min), max_value=float(answer_max)))
    )
    ambiguity = clamp_unit_interval(
        (0.16 * normalize_linear(float(evidence_count), min_value=1.0, max_value=9.0))
        + (0.08 if str(scene_variant) == "crowded_board" else 0.0)
        + (0.06 if int(marked_group_size) >= 3 else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=1.0, max_value=9.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "state_reasoning": float(board_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_sudoku_grid_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    visible_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Sudoku-grid tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.48 * normalize_linear(float(visible_count), min_value=16.0, max_value=42.0))
        + (0.08 if str(scene_variant) == "filled_grid" else 0.0)
    )
    query_base = {
        "unit_missing_digits_count": 0.26,
        "marked_cell_value": 0.44,
        "marked_cell_candidate_count": 0.40,
        "repeated_digit_count": 0.34,
    }.get(str(query_id), 0.38)
    state_reasoning = clamp_unit_interval(
        float(query_base)
        + (0.12 * normalize_linear(float(target_answer), min_value=1.0, max_value=9.0))
    )
    ambiguity = clamp_unit_interval(
        (0.12 * normalize_linear(float(evidence_count), min_value=1.0, max_value=20.0))
        + (0.08 if str(query_id) in {"marked_cell_value", "marked_cell_candidate_count"} else 0.0)
        + (0.06 if str(query_id) == "repeated_digit_count" else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=1.0, max_value=20.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "state_reasoning": float(state_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_minesweeper_grid_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    board_size: int,
    hidden_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Minesweeper-grid tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    cell_count = float(int(board_size) * int(board_size))
    visual_scan = clamp_unit_interval(
        (0.42 * normalize_linear(cell_count, min_value=36.0, max_value=64.0))
        + (0.24 * normalize_linear(float(hidden_count), min_value=4.0, max_value=14.0))
        + (0.08 if str(scene_variant) == "mixed_grid" else 0.0)
    )
    query_base = {
        "forced_mine_count": 0.38,
        "forced_safe_count": 0.34,
        "satisfied_clue_count": 0.36,
    }.get(str(query_id), 0.34)
    state_reasoning = clamp_unit_interval(
        float(query_base)
        + (0.14 * normalize_linear(float(target_answer), min_value=0.0, max_value=5.0))
        + (0.08 * normalize_linear(float(hidden_count), min_value=4.0, max_value=14.0))
    )
    ambiguity = clamp_unit_interval(
        (0.16 * normalize_linear(float(evidence_count), min_value=2.0, max_value=14.0))
        + (0.06 if str(query_id) == "satisfied_clue_count" else 0.0)
        + (0.06 if str(scene_variant) == "mixed_grid" else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=2.0, max_value=14.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "state_reasoning": float(state_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_battleship_grid_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    board_size: int,
    hit_count: int,
    miss_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Battleship tracking-grid tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    cell_count = float(int(board_size) * int(board_size))
    marker_count = float(int(hit_count) + int(miss_count))
    visual_scan = clamp_unit_interval(
        (0.40 * normalize_linear(cell_count, min_value=64.0, max_value=100.0))
        + (0.34 * normalize_linear(marker_count, min_value=12.0, max_value=34.0))
    )
    state_reasoning = clamp_unit_interval(
        0.32
        + (0.14 * normalize_linear(float(target_answer), min_value=1.0, max_value=4.0))
        + (0.08 * normalize_linear(float(hit_count), min_value=8.0, max_value=24.0))
    )
    ambiguity = clamp_unit_interval(
        (0.18 * normalize_linear(float(evidence_count), min_value=2.0, max_value=16.0))
        + (0.04 if str(scene_variant) == "standard_fleet" else 0.0)
        + (0.04 if str(query_id) in {"sunk_ship_count", "partial_ship_count"} else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=2.0, max_value=16.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "state_reasoning": float(state_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_hex_board_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    board_size: int,
    occupied_count: int,
    target_answer: Any,
    evidence_count: int,
    candidate_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Hex-board connection tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    cell_count = float(int(board_size) * int(board_size))
    visual_scan = clamp_unit_interval(
        (0.36 * normalize_linear(cell_count, min_value=25.0, max_value=64.0))
        + (0.34 * normalize_linear(float(occupied_count), min_value=8.0, max_value=34.0))
        + (0.14 * normalize_linear(float(candidate_count), min_value=0.0, max_value=8.0))
        + (0.06 if str(scene_variant) == "crowded_board" else 0.0)
    )
    target_numeric = 1.0
    if isinstance(target_answer, (int, float)):
        target_numeric = float(target_answer)
    query_base = {
        "winning_move_cell_label": 0.42,
        "connection_gap_count": 0.54,
    }.get(str(query_id), 0.46)
    state_reasoning = clamp_unit_interval(
        float(query_base)
        + (0.10 * normalize_linear(float(board_size), min_value=5.0, max_value=8.0))
        + (0.08 * normalize_linear(float(target_numeric), min_value=1.0, max_value=5.0))
    )
    ambiguity = clamp_unit_interval(
        (0.18 * normalize_linear(float(evidence_count), min_value=4.0, max_value=12.0))
        + (0.08 if str(query_id) == "winning_move_cell_label" and int(candidate_count) >= 7 else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=4.0, max_value=12.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "state_reasoning": float(state_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_bubble_shooter_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    bubble_count: int,
    row_count: int,
    col_count: int,
    target_answer: Any,
    option_count: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Bubble-shooter board tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    cell_count = float(int(row_count) * int(col_count))
    visual_scan = clamp_unit_interval(
        (0.34 * normalize_linear(cell_count, min_value=56.0, max_value=90.0))
        + (0.36 * normalize_linear(float(bubble_count), min_value=14.0, max_value=40.0))
        + (0.12 * normalize_linear(float(option_count), min_value=0.0, max_value=6.0))
        + (0.06 if str(scene_variant) == "dense_pack" else 0.0)
    )
    target_numeric = float(target_answer) if isinstance(target_answer, (int, float)) else 3.0
    reasoning_base = {
        "pop_count": 0.44,
        "drop_count": 0.60,
        "pop_color_label": 0.52,
    }.get(str(query_id), 0.48)
    state_reasoning = clamp_unit_interval(
        float(reasoning_base)
        + (0.08 * normalize_linear(float(target_numeric), min_value=1.0, max_value=8.0))
        + (0.08 * normalize_linear(float(row_count), min_value=7.0, max_value=9.0))
    )
    ambiguity = clamp_unit_interval(
        (0.18 * normalize_linear(float(evidence_count), min_value=1.0, max_value=9.0))
        + (0.08 if str(query_id) == "pop_color_label" and int(option_count) >= 6 else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=1.0, max_value=9.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "state_reasoning": float(state_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_backgammon_board_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    occupied_point_count: int,
    black_source_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Backgammon destination-count tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.46 * normalize_linear(float(occupied_point_count), min_value=8.0, max_value=24.0))
        + (0.20 * normalize_linear(float(black_source_count), min_value=2.0, max_value=8.0))
    )
    query_base = {
        "legal_move_count": 0.42,
        "hit_move_count": 0.50,
        "blocked_destination_count": 0.48,
    }.get(str(query_id), 0.46)
    move_reasoning = clamp_unit_interval(
        float(query_base)
        + (0.10 * normalize_linear(float(target_answer), min_value=1.0, max_value=8.0))
        + (0.08 * normalize_linear(float(black_source_count), min_value=2.0, max_value=8.0))
    )
    ambiguity = clamp_unit_interval(
        (0.16 * normalize_linear(float(evidence_count), min_value=1.0, max_value=8.0))
        + (0.07 if str(query_id) == "blocked_destination_count" else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=1.0, max_value=8.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "move_reasoning": float(move_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_chess_board_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    occupied_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Chess-board tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.46 * normalize_linear(float(occupied_count), min_value=6.0, max_value=18.0))
        + (0.08 if str(scene_variant) == "crowded_board" else 0.0)
    )
    query_base = {
        "marked_piece_move_count": 0.30,
        "marked_piece_capture_count": 0.34,
        "player_capture_piece_count": 0.44,
        "check_attacker_count": 0.42,
        "king_escape_square_count": 0.50,
    }.get(str(query_id), 0.36)
    state_reasoning = clamp_unit_interval(
        float(query_base)
        + (0.12 * normalize_linear(float(target_answer), min_value=0.0, max_value=8.0))
        + (0.06 * normalize_linear(float(occupied_count), min_value=6.0, max_value=18.0))
    )
    ambiguity = clamp_unit_interval(
        (0.18 * normalize_linear(float(evidence_count), min_value=0.0, max_value=8.0))
        + (0.08 if str(query_id) in {"player_capture_piece_count", "check_attacker_count"} else 0.0)
        + (0.10 if str(query_id) == "king_escape_square_count" else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=0.0, max_value=8.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "state_reasoning": float(state_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_pool_table_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    object_ball_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for Pool-table direct-shot tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.50 * normalize_linear(float(object_ball_count), min_value=8.0, max_value=15.0))
        + (0.12 if str(scene_variant) == "standard_table" else 0.0)
    )
    query_base = {
        "pottable_ball_count": 0.44,
        "legal_group_pottable_count": 0.50,
        "blocking_ball_count": 0.34,
    }.get(str(query_id), 0.42)
    geometry_reasoning = clamp_unit_interval(
        float(query_base)
        + (0.10 * normalize_linear(float(target_answer), min_value=0.0, max_value=6.0))
        + (0.08 * normalize_linear(float(object_ball_count), min_value=8.0, max_value=15.0))
    )
    ambiguity = clamp_unit_interval(
        (0.16 * normalize_linear(float(evidence_count), min_value=0.0, max_value=8.0))
        + (0.08 if str(query_id) in {"pottable_ball_count", "legal_group_pottable_count"} else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=0.0, max_value=8.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "geometry_reasoning": float(geometry_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_brick_breaker_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    brick_count: int,
    lane_count: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Brick-breaker motion tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.56 * normalize_linear(float(brick_count), min_value=20.0, max_value=54.0))
        + (0.18 * normalize_linear(float(lane_count), min_value=5.0, max_value=8.0))
    )
    motion_reasoning = clamp_unit_interval(
        (
            0.42
            if str(query_id) == "next_hit_label"
            else 0.34
            if str(query_id) == "paddle_catch_label"
            else 0.38
        )
        + (0.08 * normalize_linear(float(lane_count), min_value=5.0, max_value=8.0))
    )
    ambiguity = clamp_unit_interval(
        (0.10 if str(scene_variant) == "brick_wall" else 0.0)
        + (0.10 if str(query_id) == "next_hit_label" else 0.04)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=1.0, max_value=4.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "motion_reasoning": float(motion_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_bowling_lane_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    standing_pin_count: int,
    path_option_count: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Bowling lane motion tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.36 * normalize_linear(float(standing_pin_count), min_value=2.0, max_value=10.0))
        + (0.28 * normalize_linear(float(path_option_count), min_value=0.0, max_value=6.0))
    )
    motion_reasoning = clamp_unit_interval(
        (0.38 if str(query_id) == "first_pin_hit_label" else 0.48)
        + (0.07 * normalize_linear(float(path_option_count), min_value=4.0, max_value=6.0))
    )
    ambiguity = clamp_unit_interval(
        (0.06 if str(scene_variant) == "lane_rack" else 0.0)
        + (0.08 if str(query_id) == "spare_path_label" else 0.04)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=1.0, max_value=4.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "motion_reasoning": float(motion_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def build_games_pacman_maze_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    row_count: int,
    col_count: int,
    route_length: int,
    pellet_count: int,
    item_count: int,
    ghost_count: int,
    target_answer: int | str,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Pac-Man maze route tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.22 * normalize_linear(float(row_count), min_value=7.0, max_value=9.0))
        + (0.22 * normalize_linear(float(col_count), min_value=9.0, max_value=13.0))
        + (0.28 * normalize_linear(float(pellet_count), min_value=4.0, max_value=18.0))
        + (0.18 * normalize_linear(float(item_count), min_value=0.0, max_value=6.0))
        + (0.10 * normalize_linear(float(ghost_count), min_value=1.0, max_value=4.0))
    )
    route_reasoning_base = {
        "path_pellet_count": 0.42,
        "next_item_label": 0.52,
        "pellet_count_before_ghost": 0.58,
    }.get(str(query_id), 0.46)
    route_reasoning = clamp_unit_interval(
        float(route_reasoning_base)
        + (0.14 * normalize_linear(float(route_length), min_value=6.0, max_value=16.0))
    )
    numeric_target = float(len(str(target_answer))) if isinstance(target_answer, str) else float(target_answer)
    ambiguity = clamp_unit_interval(
        (0.12 if str(scene_variant) == "wide_maze" else 0.06)
        + (0.10 * normalize_linear(float(route_length), min_value=6.0, max_value=16.0))
        + (0.06 * normalize_linear(float(numeric_target), min_value=1.0, max_value=10.0))
    )
    output_burden = normalize_linear(float(evidence_count), min_value=1.0, max_value=10.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "route_reasoning": float(route_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )




def build_games_crossing_lane_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    lane_count: int,
    row_count: int,
    vehicle_count: int,
    route_option_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible lane-crossing motion tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.28 * normalize_linear(float(lane_count), min_value=5.0, max_value=8.0))
        + (0.24 * normalize_linear(float(row_count), min_value=5.0, max_value=7.0))
        + (0.44 * normalize_linear(float(vehicle_count), min_value=4.0, max_value=20.0))
    )
    motion_base = {
        "collision_time_value": 0.62,
        "moving_object_count": 0.58,
    }.get(str(query_id), 0.52)
    motion_reasoning = clamp_unit_interval(
        float(motion_base)
        + (0.08 * normalize_linear(float(row_count), min_value=5.0, max_value=7.0))
        + (0.06 * normalize_linear(float(target_answer), min_value=0.0, max_value=6.0))
    )
    route_reasoning = clamp_unit_interval(
        (
            0.48
            if str(query_id) in {"collision_time_value", "moving_object_count"}
            else 0.76
        )
        + (0.12 * normalize_linear(float(route_option_count), min_value=4.0, max_value=8.0))
    )
    output_burden = normalize_linear(float(evidence_count), min_value=1.0, max_value=8.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "motion_reasoning": float(motion_reasoning),
            "route_reasoning": float(route_reasoning),
            "output_burden": float(output_burden),
        },
    )


def build_games_space_shooter_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    lane_count: int,
    enemy_count: int,
    projectile_count: int,
    blocker_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Space-shooter playfield tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.42 * normalize_linear(float(enemy_count), min_value=10.0, max_value=16.0))
        + (0.16 * normalize_linear(float(projectile_count), min_value=1.0, max_value=10.0))
        + (0.14 * normalize_linear(float(blocker_count), min_value=1.0, max_value=9.0))
        + (0.08 * normalize_linear(float(lane_count), min_value=6.0, max_value=9.0))
    )
    query_base = {
        "clear_shot_count": 0.48,
        "projectile_intercept_count": 0.36,
        "highest_threat_label": 0.30,
        "safe_lane_count": 0.42,
    }.get(str(query_id), 0.40)
    spatial_reasoning = clamp_unit_interval(
        float(query_base)
        + (0.10 * normalize_linear(float(lane_count), min_value=6.0, max_value=9.0))
        + (0.08 * normalize_linear(float(target_answer), min_value=1.0, max_value=5.0))
    )
    threat_reasoning = clamp_unit_interval(
        (
            0.34
            if str(query_id) == "highest_threat_label"
            else 0.46
            if str(query_id) == "projectile_intercept_count"
            else 0.52
            if str(query_id) == "clear_shot_count"
            else 0.48
        )
        + (0.08 * normalize_linear(float(projectile_count + blocker_count), min_value=2.0, max_value=16.0))
    )
    output_burden = normalize_linear(float(evidence_count), min_value=1.0, max_value=8.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "spatial_reasoning": float(spatial_reasoning),
            "threat_reasoning": float(threat_reasoning),
            "output_burden": float(output_burden),
        },
    )


def build_games_minigolf_course_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    obstacle_count: int,
    path_option_count: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Mini-golf course tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.48 * normalize_linear(float(obstacle_count), min_value=4.0, max_value=8.0))
        + (0.24 * normalize_linear(float(path_option_count), min_value=0.0, max_value=6.0))
    )
    motion_reasoning = clamp_unit_interval(
        (
            0.46
            if str(query_id) == "first_obstacle_label"
            else 0.68
            if str(query_id) == "shot_path_label"
            else 0.52
        )
        + (0.08 * normalize_linear(float(obstacle_count), min_value=4.0, max_value=8.0))
    )
    path_reasoning = clamp_unit_interval(
        (
            0.36
            if str(query_id) == "first_obstacle_label"
            else 0.74
            if str(query_id) == "shot_path_label"
            else 0.50
        )
        + (0.12 * normalize_linear(float(path_option_count), min_value=4.0, max_value=6.0))
    )
    output_burden = normalize_linear(float(evidence_count), min_value=1.0, max_value=6.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "motion_reasoning": float(motion_reasoning),
            "path_reasoning": float(path_reasoning),
            "output_burden": float(output_burden),
        },
    )


def build_games_platformer_level_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    platform_count: int,
    hazard_count: int,
    collectible_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Platformer level tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.32 * normalize_linear(float(platform_count), min_value=3.0, max_value=7.0))
        + (0.30 * normalize_linear(float(hazard_count), min_value=2.0, max_value=8.0))
        + (0.22 * normalize_linear(float(collectible_count), min_value=3.0, max_value=14.0))
    )
    motion_reasoning = clamp_unit_interval(
        (
            0.56
            if str(query_id) == "jump_landing_label"
            else 0.42
            if str(query_id) == "collectible_count"
            else 0.50
        )
        + (0.08 * normalize_linear(float(target_answer), min_value=1.0, max_value=7.0))
    )
    path_reasoning = clamp_unit_interval(
        (
            0.58
            if str(query_id) == "jump_landing_label"
            else 0.48
            if str(query_id) == "collectible_count"
            else 0.50
        )
        + (0.08 * normalize_linear(float(platform_count + hazard_count), min_value=5.0, max_value=15.0))
    )
    output_burden = normalize_linear(float(evidence_count), min_value=1.0, max_value=7.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "motion_reasoning": float(motion_reasoning),
            "path_reasoning": float(path_reasoning),
            "output_burden": float(output_burden),
        },
    )


def build_games_2048_board_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    filled_count: int,
    merge_count: int,
    target_answer: int | str,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible 2048 board-simulation tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.58 * normalize_linear(float(filled_count), min_value=6.0, max_value=16.0))
        + (0.06 if str(scene_variant) == "standard_board" else 0.0)
    )
    query_base = {
        "merge_count": 0.38,
        "score_value": 0.48,
        "max_tile_value": 0.42,
        "best_move_label": 0.70,
    }.get(str(query_id), 0.46)
    numeric_target = float(len(str(target_answer))) if isinstance(target_answer, str) else float(target_answer)
    rule_simulation = clamp_unit_interval(
        float(query_base)
        + (0.10 * normalize_linear(float(merge_count), min_value=0.0, max_value=4.0))
        + (0.04 * normalize_linear(float(numeric_target), min_value=0.0, max_value=256.0))
    )
    comparison_load = clamp_unit_interval(
        0.78 if str(query_id) == "best_move_label" else 0.18 + (0.05 * normalize_linear(float(filled_count), min_value=6.0, max_value=16.0))
    )
    output_burden = normalize_linear(float(evidence_count), min_value=0.0, max_value=8.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "rule_simulation": float(rule_simulation),
            "comparison_load": float(comparison_load),
            "output_burden": float(output_burden),
        },
    )


def build_games_snakes_ladders_board_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    jump_count: int,
    horizon_roll_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Snakes and Ladders board tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.34 * normalize_linear(float(jump_count), min_value=3.0, max_value=8.0))
        + (0.12 if str(scene_variant) == "standard_board" else 0.0)
    )
    query_base = {
        "move_outcome_value": 0.36,
        "best_roll_value": 0.72,
    }.get(str(query_id), 0.50)
    rule_simulation = clamp_unit_interval(
        float(query_base)
        + (0.13 * normalize_linear(float(horizon_roll_count), min_value=1.0, max_value=3.0))
        + (0.04 * normalize_linear(float(target_answer), min_value=7.0, max_value=100.0))
    )
    comparison_load = clamp_unit_interval(
        (0.78 if str(query_id) == "best_roll_value" else 0.18)
        + (0.04 * normalize_linear(float(jump_count), min_value=3.0, max_value=8.0))
    )
    output_burden = normalize_linear(float(evidence_count), min_value=0.0, max_value=8.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "rule_simulation": float(rule_simulation),
            "comparison_load": float(comparison_load),
            "output_burden": float(output_burden),
        },
    )


def build_games_snake_grid_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_id: str,
    board_size: int,
    body_length: int,
    planned_move_count: int,
    evidence_count: int,
    target_answer: int | str,
) -> TaskComplexity:
    """Build normalized complexity for visible Snake-grid tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.34 * normalize_linear(float(board_size), min_value=7.0, max_value=10.0))
        + (0.36 * normalize_linear(float(body_length), min_value=5.0, max_value=11.0))
        + (0.04 if str(scene_variant) == "square_grid" else 0.0)
    )
    query_base = {
        "single_move_outcome_label": 0.32,
        "safe_direction_count": 0.42,
        "planned_moves_outcome_label": 0.62,
        "first_event_step_value": 0.68,
    }.get(str(query_id), 0.48)
    rule_simulation = clamp_unit_interval(
        float(query_base)
        + (0.13 * normalize_linear(float(planned_move_count), min_value=0.0, max_value=6.0))
    )
    path_reasoning = clamp_unit_interval(
        (
            0.22
            if str(query_id) in {"single_move_outcome_label", "safe_direction_count"}
            else 0.58
        )
        + (0.10 * normalize_linear(float(planned_move_count), min_value=0.0, max_value=6.0))
    )
    answer_scale = float(target_answer) if isinstance(target_answer, int) else float(len(str(target_answer)))
    output_burden = clamp_unit_interval(
        (0.74 * normalize_linear(float(evidence_count), min_value=1.0, max_value=6.0))
        + (0.10 * normalize_linear(float(answer_scale), min_value=0.0, max_value=6.0))
    )
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "rule_simulation": float(rule_simulation),
            "path_reasoning": float(path_reasoning),
            "output_burden": float(output_burden),
        },
    )


def build_games_rhythm_lanes_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    query_id: str,
    lane_count: int,
    row_count: int,
    beat_window: int,
    note_count: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible rhythm-lanes timing tasks."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.46 * normalize_linear(float(note_count), min_value=12.0, max_value=44.0))
        + (0.22 * normalize_linear(float(lane_count), min_value=5.0, max_value=8.0))
        + (0.12 * normalize_linear(float(row_count), min_value=10.0, max_value=14.0))
    )
    timing_reasoning = clamp_unit_interval(
        {
            "lane_hit_count": 0.34,
            "lane_color_hit_count": 0.46,
            "most_hits_lane_label": 0.62,
            "earliest_hit_lane_label": 0.56,
        }.get(str(query_id), 0.50)
        + (0.08 * normalize_linear(float(beat_window), min_value=5.0, max_value=7.0))
    )
    ambiguity = clamp_unit_interval(
        (0.30 * normalize_linear(float(note_count), min_value=12.0, max_value=44.0))
        + (0.35 * normalize_linear(float(evidence_count), min_value=1.0, max_value=7.0))
        + (0.10 if str(query_id) == "lane_color_hit_count" else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=1.0, max_value=7.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "timing_reasoning": float(timing_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


__all__ = [
    "build_games_2048_board_complexity",
    "build_games_battleship_grid_complexity",
    "build_games_backgammon_board_complexity",
    "build_games_bingo_completed_line_complexity",
    "build_games_bowling_lane_complexity",
    "build_games_brick_breaker_complexity",
    "build_games_bubble_shooter_complexity",
    "build_games_cards_hand_complexity",
    "build_games_checkers_move_complexity",
    "build_games_chess_board_complexity",
    "build_games_connect_four_move_complexity",
    "build_games_crossing_lane_complexity",
    "build_games_darts_score_complexity",
    "build_games_dominoes_chain_complexity",
    "build_games_dots_and_boxes_capture_complexity",
    "build_games_go_group_property_complexity",
    "build_games_hex_board_complexity",
    "build_games_minesweeper_grid_complexity",
    "build_games_minigolf_course_complexity",
    "build_games_nine_mens_morris_pieces_in_mill_complexity",
    "build_games_pool_table_complexity",
    "build_games_pacman_maze_complexity",
    "build_games_platformer_level_complexity",
    "build_games_reversi_move_complexity",
    "build_games_rhythm_lanes_complexity",
    "build_games_space_shooter_complexity",
    "build_games_snake_grid_complexity",
    "build_games_snakes_ladders_board_complexity",
    "build_games_sudoku_grid_complexity",
    "build_games_complexity",
    "clamp_unit_interval",
    "normalize_linear",
    "resolve_games_complexity_weights",
]
