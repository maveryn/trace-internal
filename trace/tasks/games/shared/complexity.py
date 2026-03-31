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
    query_variant: str,
    card_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible playing-card hand-count scenes."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.54 * normalize_linear(float(card_count), min_value=7.0, max_value=14.0))
        + (0.12 if str(scene_variant) == "two_row" else 0.0)
    )
    card_reasoning = clamp_unit_interval(
        (0.36 if str(query_variant) == "same_suit_as_reference_count" else 0.40 if str(query_variant) == "higher_than_reference_count" else 0.52 if str(query_variant) == "pair_count" else 0.62)
        + (0.10 * normalize_linear(float(target_answer), min_value=0.0, max_value=6.0))
    )
    ambiguity = clamp_unit_interval(
        (0.18 * normalize_linear(float(evidence_count), min_value=0.0, max_value=8.0))
        + (0.10 if str(query_variant) == "pair_count" and int(target_answer) == 0 else 0.0)
        + (0.12 if str(query_variant) == "longest_run_length" and str(scene_variant) == "two_row" else 0.0)
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
    query_variant: str,
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
            if str(query_variant) == "double_count"
            else 0.46
            if str(query_variant) == "sum_to_target_count"
            else 0.50
            if str(query_variant) == "matching_end_count"
            else 0.56
        )
        + (0.08 * normalize_linear(float(target_answer), min_value=0.0, max_value=5.0))
    )
    ambiguity = clamp_unit_interval(
        (0.18 * normalize_linear(float(evidence_count), min_value=0.0, max_value=8.0))
        + (0.10 if str(query_variant) == "higher_sum_than_reference_count" else 0.0)
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


def build_games_reversi_move_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_variant: str,
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
            if str(query_variant) == "legal_move_count"
            else 0.52
            if str(query_variant) == "corner_move_count"
            else 0.60
        )
        + (0.10 * normalize_linear(float(target_answer), min_value=0.0, max_value=8.0))
    )
    ambiguity = clamp_unit_interval(
        (0.18 * normalize_linear(float(evidence_count), min_value=0.0, max_value=8.0))
        + (0.12 if str(query_variant) == "corner_move_count" and int(target_answer) == 0 else 0.0)
        + (0.08 if str(query_variant) == "flip_count_for_marked_move" else 0.0)
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
    query_variant: str,
    marked_cell_count: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for bingo completed-line counting scenes."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.44 * normalize_linear(float(marked_cell_count), min_value=0.0, max_value=25.0))
        + (0.14 if str(query_variant) == "completed_straight_line_count" else 0.0)
    )
    state_reasoning = clamp_unit_interval(
        (0.34 if str(query_variant) == "completed_row_count" else 0.38 if str(query_variant) == "completed_column_count" else 0.54)
        + (0.12 * normalize_linear(float(target_answer), min_value=0.0, max_value=8.0))
    )
    ambiguity = clamp_unit_interval(
        (0.18 * normalize_linear(float(evidence_count), min_value=0.0, max_value=25.0))
        + (0.08 if str(query_variant) == "completed_straight_line_count" and int(target_answer) == 0 else 0.0)
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
    query_variant: str,
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
        (0.44 if str(query_variant) == "winning_move_count" else 0.56)
        + (0.10 * normalize_linear(float(target_answer), min_value=0.0, max_value=6.0))
    )
    ambiguity = clamp_unit_interval(
        (0.18 * normalize_linear(float(evidence_count), min_value=0.0, max_value=12.0))
        + (0.10 if str(query_variant) == "safe_move_count" and int(target_answer) == 0 else 0.0)
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
    box_rows: int,
    box_cols: int,
    drawn_edge_count: int,
    target_answer: int,
    path_turn_count: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for dots-and-boxes forced-turn capture scenes."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    total_boxes = int(box_rows) * int(box_cols)
    visual_scan = clamp_unit_interval(
        (0.30 * normalize_linear(float(total_boxes), min_value=6.0, max_value=16.0))
        + (0.30 * normalize_linear(float(drawn_edge_count), min_value=3.0, max_value=22.0))
    )
    state_reasoning = clamp_unit_interval(
        0.34
        + (0.36 * normalize_linear(float(target_answer), min_value=1.0, max_value=6.0))
        + (0.12 * normalize_linear(float(path_turn_count), min_value=0.0, max_value=5.0))
    )
    ambiguity = clamp_unit_interval(
        (0.10 * normalize_linear(float(path_turn_count), min_value=0.0, max_value=5.0))
        + (0.06 if int(target_answer) >= 4 else 0.0)
    )
    output_burden = normalize_linear(float(evidence_count), min_value=1.0, max_value=6.0)
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
    query_variant: str,
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
    board_reasoning = clamp_unit_interval(
        (0.44 if str(query_variant) == "legal_move_count" else 0.56)
        + (0.10 * normalize_linear(float(target_answer), min_value=0.0, max_value=5.0))
    )
    ambiguity = clamp_unit_interval(
        (0.18 * normalize_linear(float(evidence_count), min_value=0.0, max_value=6.0))
        + (0.10 if str(query_variant) == "capture_move_count" and int(target_answer) == 0 else 0.0)
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
    query_variant: str,
    total_piece_count: int,
    target_answer: int,
    overlapping_piece_count: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for nine-men's-morris mill-piece counting scenes."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.34 * normalize_linear(float(total_piece_count), min_value=6.0, max_value=18.0))
        + 0.18
    )
    state_reasoning = clamp_unit_interval(
        (0.36 if str(query_variant) != "all_pieces_in_mill_count" else 0.50)
        + (0.18 * normalize_linear(float(target_answer), min_value=0.0, max_value=18.0))
        + (0.12 * normalize_linear(float(overlapping_piece_count), min_value=0.0, max_value=4.0))
    )
    ambiguity = clamp_unit_interval(
        (0.12 * normalize_linear(float(overlapping_piece_count), min_value=0.0, max_value=4.0))
        + (0.08 if str(query_variant) == "all_pieces_in_mill_count" and int(target_answer) == 0 else 0.0)
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


def build_games_mancala_move_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    scene_variant: str,
    query_variant: str,
    total_stones: int,
    target_answer: int,
    evidence_count: int,
) -> TaskComplexity:
    """Build normalized complexity for visible Mancala move-count scenes."""

    weights = resolve_games_complexity_weights(task_group_defaults, task_id=task_id)
    visual_scan = clamp_unit_interval(
        (0.44 * normalize_linear(float(total_stones), min_value=12.0, max_value=60.0))
        + (0.10 if str(scene_variant) == "crowded_board" else 0.0)
    )
    board_reasoning = clamp_unit_interval(
        (0.46 if str(query_variant) == "extra_turn_move_count" else 0.58)
        + (0.10 * normalize_linear(float(target_answer), min_value=0.0, max_value=5.0))
    )
    ambiguity = clamp_unit_interval(
        (0.16 * normalize_linear(float(evidence_count), min_value=0.0, max_value=6.0))
        + (0.10 if str(query_variant) == "capture_move_count" and int(target_answer) == 0 else 0.0)
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


__all__ = [
    "build_games_bingo_completed_line_complexity",
    "build_games_cards_hand_complexity",
    "build_games_checkers_move_complexity",
    "build_games_connect_four_move_complexity",
    "build_games_dominoes_chain_complexity",
    "build_games_dots_and_boxes_capture_complexity",
    "build_games_mancala_move_complexity",
    "build_games_nine_mens_morris_pieces_in_mill_complexity",
    "build_games_reversi_move_complexity",
    "build_games_complexity",
    "clamp_unit_interval",
    "normalize_linear",
    "resolve_games_complexity_weights",
]
