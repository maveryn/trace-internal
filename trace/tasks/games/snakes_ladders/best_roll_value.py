"""Games Snakes and Ladders tasks over one visible board state."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from trace.tasks.shared.fixed_query import FixedQueryVariantTaskMixin, QuerySubsetTaskMixin
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from .shared.common import (
    LAST_SQUARE,
    SUPPORTED_BOARD_SIDES,
    SUPPORTED_DIE_VALUES,
    SUPPORTED_HORIZON_ROLL_COUNTS,
    SUPPORTED_SNAKES_LADDERS_QUERY_IDS,
    SUPPORTED_SNAKES_LADDERS_SCENE_VARIANTS,
    SUPPORTED_SNAKES_LADDERS_STYLE_VARIANTS,
    SnakesLaddersJump,
    SnakesLaddersMove,
    SnakesLaddersSample,
    apply_die_roll,
    best_final_square,
    board_last_square,
    square_to_cell_id,
    square_to_coord,
    trace_best_route,
    validate_snakes_ladders_sample,
)
from .shared.rendering import SnakesLaddersRenderParams, render_snakes_ladders_board_scene
from ..shared.visual_defaults import load_games_scene_noise_defaults


TASK_ID = "games_snakes_ladders_board_base"
SCENE_ID = "snakes_ladders"
SPECIAL_SQUARE_QUERY_IDS: Tuple[str, ...] = (
    "ladder_start_ahead_count",
    "snake_head_ahead_count",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for Snakes and Ladders scenes."""

    move_outcome_support: Tuple[int, ...] = tuple(range(7, 50))
    best_roll_value_support: Tuple[int, ...] = tuple(range(14, 50))
    special_square_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    board_side_support: Tuple[int, ...] = SUPPORTED_BOARD_SIDES
    horizon_roll_count_support: Tuple[int, ...] = SUPPORTED_HORIZON_ROLL_COUNTS
    move_outcome_jump_probability: float = 0.30
    canvas_width: int = 1120
    canvas_height: int = 900
    board_left_px: int = 56
    board_top_px: int = 72
    board_size_px: int = 740
    side_panel_width_px: int = 220
    cell_gap_px: int = 4
    cell_radius_px: int = 6
    number_font_size_px: int = 24
    token_radius_px: int = 19
    die_size_px: int = 88
    jump_width_px: int = 6


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Snakes and Ladders instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    board_side: int
    target_answer: int
    target_answer_support: Tuple[int, ...]
    die_value: int
    horizon_roll_count: int
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    board_side_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    die_value_probabilities: Dict[str, float]
    horizon_roll_count_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_SCENE_DEFAULTS = get_scene_defaults("games", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id="snakes_ladders", apply_prob=0.5)


def _support_for_query(query_id: str) -> Tuple[int, ...]:
    """Return fallback answer support for one query."""

    if str(query_id) == "move_outcome_value":
        return _DEFAULTS.move_outcome_support
    if str(query_id) == "best_roll_value":
        return _DEFAULTS.best_roll_value_support
    if str(query_id) in SPECIAL_SQUARE_QUERY_IDS:
        return _DEFAULTS.special_square_count_support
    raise ValueError(f"unsupported query_id: {query_id}")


def _support_key_for_query(query_id: str) -> str:
    """Return config support key for one query."""

    if str(query_id) == "move_outcome_value":
        return "move_outcome_support"
    if str(query_id) == "best_roll_value":
        return "best_roll_value_support"
    if str(query_id) in SPECIAL_SQUARE_QUERY_IDS:
        return "special_square_count_support"
    raise ValueError(f"unsupported query_id: {query_id}")


def _resolve_named_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named axis."""

    return resolve_games_named_axis(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=[str(value) for value in supported],
    )


def _resolve_query_id(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    supported_query_ids: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced Snakes and Ladders query."""

    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=supported_query_ids,
    )


def _uses_uniform_query_cycle(
    params: Mapping[str, Any],
    probabilities: Mapping[str, float],
    *,
    supported_query_ids: Sequence[str],
) -> bool:
    """Return true when the query axis uses the default balanced cycle."""

    if params.get("query_id") is not None or params.get("query_variant") is not None:
        return False
    enabled = bool(params.get("balanced_query_id_sampling", group_default(_GEN_DEFAULTS, "balanced_query_id_sampling", True)))
    if not enabled:
        return False
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if len(positives) != len(tuple(supported_query_ids)):
        return False
    return max(positives) - min(positives) <= 1e-9


def _params_for_query_occurrence_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
    supported_query_ids: Sequence[str],
) -> Dict[str, Any]:
    """Use a per-query occurrence index for balanced inner answer axes."""

    cycle_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return cycle_params
    if not _uses_uniform_query_cycle(params, query_id_probabilities, supported_query_ids=supported_query_ids):
        return cycle_params
    cycle_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(tuple(supported_query_ids)))
    return cycle_params


def _resolve_axes(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    supported_query_ids: Sequence[str],
) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one scene."""

    query_id, query_id_probabilities = _resolve_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=supported_query_ids,
    )
    answer_cycle_params = _params_for_query_occurrence_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
        supported_query_ids=supported_query_ids,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_SNAKES_LADDERS_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_SNAKES_LADDERS_STYLE_VARIANTS,
    )
    board_side_support = resolve_integer_support(
        answer_cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        key="board_side_support",
        fallback=_DEFAULTS.board_side_support,
    )
    explicit_target_answer = answer_cycle_params.get("target_answer")
    if explicit_target_answer is not None:
        target_value = int(explicit_target_answer)
        board_side_support = tuple(side for side in board_side_support if target_value <= board_last_square(int(side)))
        if not board_side_support:
            raise ValueError(f"target_answer {target_value} is incompatible with board_side_support")
    board_side_cycle_params = dict(answer_cycle_params)
    board_side_cycle_params["board_side_support"] = [int(value) for value in board_side_support]
    board_side, board_side_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=board_side_cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="board_side_support",
        explicit_key="board_side",
        fallback_support=_DEFAULTS.board_side_support,
        namespace=f"{TASK_ID}.board_side",
        balanced_flag_key="balanced_board_side_sampling",
        namespace_support_permutation=True,
    )
    last_square = board_last_square(int(board_side))
    support_key = _support_key_for_query(str(query_id))
    raw_target_support = resolve_integer_support(
        answer_cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        key=support_key,
        fallback=_support_for_query(str(query_id)),
    )
    target_support = tuple(int(value) for value in raw_target_support if int(value) <= int(last_square))
    if not target_support:
        raise ValueError(f"{support_key} has no values compatible with board_side={int(board_side)}")
    target_cycle_params = dict(answer_cycle_params)
    target_cycle_params[support_key] = [int(value) for value in target_support]
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=target_cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=support_key,
        explicit_key="target_answer",
        fallback_support=target_support,
        namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    die_value, die_value_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=answer_cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="die_value_support",
        explicit_key="die_value",
        fallback_support=SUPPORTED_DIE_VALUES,
        namespace=f"{TASK_ID}.die_value",
        balanced_flag_key="balanced_die_value_sampling",
        namespace_support_permutation=True,
    )
    horizon_roll_count, horizon_roll_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=answer_cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="horizon_roll_count_support",
        explicit_key="horizon_roll_count",
        fallback_support=_DEFAULTS.horizon_roll_count_support,
        namespace=f"{TASK_ID}.horizon_roll_count",
        balanced_flag_key="balanced_horizon_roll_count_sampling",
        namespace_support_permutation=True,
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        board_side=int(board_side),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_support),
        die_value=int(die_value),
        horizon_roll_count=int(horizon_roll_count),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        board_side_probabilities=dict(board_side_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
        die_value_probabilities=dict(die_value_probabilities),
        horizon_roll_count_probabilities=dict(horizon_roll_count_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int, board_side: int) -> SnakesLaddersRenderParams:
    """Resolve rendering parameters from config/defaults."""

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.snakes_ladders.font_family",
        params=params,
    )
    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.snakes_ladders.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.snakes_ladders.layout",
        ),
        unit_scale_meta,
    )
    return SnakesLaddersRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        board_side=int(board_side),
        board_left_px=int(params.get("board_left_px", group_default(_RENDER_DEFAULTS, "board_left_px", _DEFAULTS.board_left_px))),
        board_top_px=int(params.get("board_top_px", group_default(_RENDER_DEFAULTS, "board_top_px", _DEFAULTS.board_top_px))),
        board_size_px=scale_games_px(params.get("board_size_px", group_default(_RENDER_DEFAULTS, "board_size_px", _DEFAULTS.board_size_px)), unit_scale, min_px=370),
        side_panel_width_px=int(params.get("side_panel_width_px", group_default(_RENDER_DEFAULTS, "side_panel_width_px", _DEFAULTS.side_panel_width_px))),
        cell_gap_px=scale_games_px(params.get("cell_gap_px", group_default(_RENDER_DEFAULTS, "cell_gap_px", _DEFAULTS.cell_gap_px)), unit_scale, min_px=2),
        cell_radius_px=scale_games_px(params.get("cell_radius_px", group_default(_RENDER_DEFAULTS, "cell_radius_px", _DEFAULTS.cell_radius_px)), unit_scale, min_px=3),
        number_font_size_px=scale_games_px(params.get("number_font_size_px", group_default(_RENDER_DEFAULTS, "number_font_size_px", _DEFAULTS.number_font_size_px)), unit_scale, min_px=12),
        token_radius_px=scale_games_px(params.get("token_radius_px", group_default(_RENDER_DEFAULTS, "token_radius_px", _DEFAULTS.token_radius_px)), unit_scale, min_px=9),
        die_size_px=scale_games_px(params.get("die_size_px", group_default(_RENDER_DEFAULTS, "die_size_px", _DEFAULTS.die_size_px)), unit_scale, min_px=44),
        jump_width_px=scale_games_px(params.get("jump_width_px", group_default(_RENDER_DEFAULTS, "jump_width_px", _DEFAULTS.jump_width_px)), unit_scale, min_px=3),
        font_family=str(font_family),
        layout_jitter_meta=layout_jitter,
    )


def _make_jump(*, kind: str, start: int, end: int) -> SnakesLaddersJump:
    """Return one validated jump."""

    kind_text = str(kind)
    return SnakesLaddersJump(
        jump_id=f"{kind_text}_{int(start)}_{int(end)}",
        kind=kind_text,
        start_square=int(start),
        end_square=int(end),
    )


def _random_jump_endpoint(rng, *, kind: str, start: int, board_side: int) -> int | None:
    """Return one endpoint for a random visual jump, if feasible."""

    side = int(board_side)
    last_square = board_last_square(side)
    min_span = max(4, int(side) - 1)
    max_span = max(min_span, int(side) * 4)
    if str(kind) == "ladder":
        low = int(start) + int(min_span)
        high = min(int(last_square) - 1, int(start) + int(max_span))
        if low > high:
            return None
        return int(rng.randint(low, high))
    high = int(start) - int(min_span)
    low = max(2, int(start) - int(max_span))
    if low > high:
        return None
    return int(rng.randint(low, high))


def _target_jump_counts(board_side: int) -> Tuple[int, int]:
    """Return the desired ladder/snake counts for a board side length."""

    if int(board_side) <= 7:
        return (1, 1)
    return (2, 2)


def _jump_visual_segment(
    jump: SnakesLaddersJump,
    *,
    board_side: int,
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """Return the board-coordinate segment used to draw one jump."""

    start_row, start_col = square_to_coord(int(jump.start_square), board_side=int(board_side))
    end_row, end_col = square_to_coord(int(jump.end_square), board_side=int(board_side))
    return ((float(start_col), float(start_row)), (float(end_col), float(end_row)))


def _orientation(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
    """Return signed orientation for three points."""

    return float((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))


def _on_segment(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> bool:
    """Return true if b lies on segment ac."""

    eps = 1e-9
    return (
        min(a[0], c[0]) - eps <= b[0] <= max(a[0], c[0]) + eps
        and min(a[1], c[1]) - eps <= b[1] <= max(a[1], c[1]) + eps
        and abs(_orientation(a, b, c)) <= eps
    )


def _segments_intersect(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
    d: Tuple[float, float],
) -> bool:
    """Return true if two board-coordinate segments intersect."""

    o1 = _orientation(a, b, c)
    o2 = _orientation(a, b, d)
    o3 = _orientation(c, d, a)
    o4 = _orientation(c, d, b)
    eps = 1e-9
    if ((o1 > eps and o2 < -eps) or (o1 < -eps and o2 > eps)) and (
        (o3 > eps and o4 < -eps) or (o3 < -eps and o4 > eps)
    ):
        return True
    return _on_segment(a, c, b) or _on_segment(a, d, b) or _on_segment(c, a, d) or _on_segment(c, b, d)


def _jump_conflicts_with_existing(
    candidate: SnakesLaddersJump,
    *,
    existing: Sequence[SnakesLaddersJump],
    board_side: int,
) -> bool:
    """Return true if a candidate would make the connector layout ambiguous."""

    candidate_squares = {int(candidate.start_square), int(candidate.end_square)}
    candidate_start, candidate_end = _jump_visual_segment(candidate, board_side=int(board_side))
    for jump in existing:
        if candidate_squares & {int(jump.start_square), int(jump.end_square)}:
            return True
        existing_start, existing_end = _jump_visual_segment(jump, board_side=int(board_side))
        if _segments_intersect(candidate_start, candidate_end, existing_start, existing_end):
            return True
    return False


def _add_random_jumps(
    *,
    rng,
    jumps: Sequence[SnakesLaddersJump],
    board_side: int,
    protected_starts: Sequence[int],
    protected_range: Sequence[int] = tuple(),
    target_ladders: int = 3,
    target_snakes: int = 3,
) -> Tuple[SnakesLaddersJump, ...]:
    """Add harmless visual snakes/ladders while avoiding protected jump starts."""

    last_square = board_last_square(int(board_side))
    result = list(jumps)
    used_starts = {int(jump.start_square) for jump in result}
    protected = set(int(value) for value in protected_starts) | set(int(value) for value in protected_range)

    def _count(kind: str) -> int:
        return sum(1 for jump in result if str(jump.kind) == str(kind))

    for kind, target in (("ladder", int(target_ladders)), ("snake", int(target_snakes))):
        for _attempt in range(140):
            if _count(kind) >= int(target):
                break
            if str(kind) == "ladder":
                start = int(rng.randint(2, max(2, int(last_square) - max(2, int(board_side)))))
            else:
                start = int(rng.randint(max(3, int(board_side) + 1), int(last_square) - 1))
            if start in used_starts or start in protected:
                continue
            end = _random_jump_endpoint(rng, kind=kind, start=start, board_side=int(board_side))
            if end is None:
                continue
            candidate = _make_jump(kind=kind, start=start, end=int(end))
            if _jump_conflicts_with_existing(candidate, existing=tuple(result), board_side=int(board_side)):
                continue
            result.append(candidate)
            used_starts.add(int(start))
    return tuple(result)


def _special_query_kind(query_id: str) -> str:
    """Return the jump kind counted by one special-square query."""

    if str(query_id) == "ladder_start_ahead_count":
        return "ladder"
    if str(query_id) == "snake_head_ahead_count":
        return "snake"
    raise ValueError(f"unsupported special-square query_id: {query_id}")


def _valid_jump_starts(*, kind: str, board_side: int) -> Tuple[int, ...]:
    """Return jump-start squares with at least one valid endpoint."""

    side = int(board_side)
    last_square = board_last_square(side)
    min_span = max(4, int(side) - 1)
    if str(kind) == "ladder":
        return tuple(range(2, max(1, int(last_square) - int(min_span)) + 1))
    return tuple(range(max(3, int(min_span) + 2), int(last_square)))


def _special_square_entity_ids(
    *,
    jumps: Sequence[SnakesLaddersJump],
    kind: str,
    start_square: int,
    board_side: int,
) -> Tuple[str, ...]:
    """Return square ids for counted jump starts ahead of the token."""

    last_square = board_last_square(int(board_side))
    squares = sorted(
        int(jump.start_square)
        for jump in jumps
        if str(jump.kind) == str(kind)
        and int(start_square) < int(jump.start_square) <= int(last_square)
    )
    return tuple(square_to_cell_id(int(square)) for square in squares)


def _append_jumps_from_allowed_starts(
    *,
    rng,
    jumps: Sequence[SnakesLaddersJump],
    board_side: int,
    kind: str,
    allowed_starts: Sequence[int],
    count: int,
    required: bool,
) -> Tuple[SnakesLaddersJump, ...] | None:
    """Append up to `count` non-conflicting jumps of one kind from allowed starts."""

    result = list(jumps)
    used_starts = {int(jump.start_square) for jump in result}
    candidates = [int(value) for value in allowed_starts if int(value) not in used_starts]
    rng.shuffle(candidates)
    target_count = max(0, int(count))
    for start in candidates:
        if target_count <= 0:
            break
        for _endpoint_attempt in range(12):
            end = _random_jump_endpoint(rng, kind=str(kind), start=int(start), board_side=int(board_side))
            if end is None:
                continue
            candidate = _make_jump(kind=str(kind), start=int(start), end=int(end))
            if _jump_conflicts_with_existing(candidate, existing=tuple(result), board_side=int(board_side)):
                continue
            result.append(candidate)
            used_starts.add(int(start))
            target_count -= 1
            break
    if target_count > 0 and bool(required):
        return None
    return tuple(result)


def _nearby_die_region(start_square: int, *, board_side: int) -> Tuple[int, ...]:
    """Return local squares kept visually clear around the token and die landings."""

    last_square = board_last_square(int(board_side))
    low = max(2, int(start_square) - 2)
    high = min(int(last_square) - 1, int(start_square) + max(4, int(board_side)))
    return tuple(range(low, high + 1))


def _sample_start_for_direct_target(rng, *, target_final: int, die_value: int, board_side: int) -> int | None:
    """Choose a start square that directly lands on the target final square."""

    last_square = board_last_square(int(board_side))
    start = int(target_final) - int(die_value)
    if start >= 1:
        return int(start)
    candidates = [square for square in range(1, int(last_square) + 1) if square + int(die_value) > int(last_square) and square == int(target_final)]
    if candidates:
        return int(rng.choice(tuple(candidates)))
    return None


def _sample_move_outcome_scene(*, rng, axes: _ResolvedAxes) -> SnakesLaddersSample:
    """Construct a single shown-die move-outcome scene."""

    target_final = int(axes.target_answer)
    die_value = int(axes.die_value)
    board_side = int(axes.board_side)
    last_square = board_last_square(board_side)
    jump_probability = float(group_default(_GEN_DEFAULTS, "move_outcome_jump_probability", _DEFAULTS.move_outcome_jump_probability))
    for _attempt in range(180):
        use_jump = bool(rng.random() < max(0.0, min(1.0, jump_probability)))
        jumps: list[SnakesLaddersJump] = []
        start_square: int | None = None
        landing_square: int | None = None
        if use_jump:
            possible_sources: list[int] = []
            for source in range(2, int(last_square)):
                if source == target_final:
                    continue
                if abs(int(source) - int(target_final)) < max(4, int(board_side) - 1):
                    continue
                start = int(source) - int(die_value)
                if start >= 1 and start + int(die_value) == int(source):
                    possible_sources.append(int(source))
            if possible_sources:
                landing_square = int(rng.choice(tuple(possible_sources)))
                start_square = int(landing_square) - int(die_value)
                kind = "ladder" if int(target_final) > int(landing_square) else "snake"
                jumps.append(_make_jump(kind=kind, start=int(landing_square), end=int(target_final)))
        if start_square is None:
            direct_start = _sample_start_for_direct_target(
                rng,
                target_final=int(target_final),
                die_value=int(die_value),
                board_side=int(board_side),
            )
            if direct_start is None:
                continue
            start_square = int(direct_start)
            landing_square = int(target_final)

        protected_starts = {int(landing_square), int(start_square)}
        target_ladders, target_snakes = _target_jump_counts(int(board_side))
        jumps_tuple = _add_random_jumps(
            rng=rng,
            jumps=tuple(jumps),
            board_side=int(board_side),
            protected_starts=tuple(protected_starts),
            protected_range=_nearby_die_region(int(start_square), board_side=int(board_side)),
            target_ladders=int(target_ladders),
            target_snakes=int(target_snakes),
        )
        move = apply_die_roll(int(start_square), int(die_value), jumps_tuple, board_side=int(board_side))
        if int(move.final_square) != int(target_final):
            continue
        annotation_ids = [square_to_cell_id(int(start_square)), square_to_cell_id(int(move.final_square))]
        sample = SnakesLaddersSample(
            mode="move_outcome_value",
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            board_side=int(board_side),
            answer=int(target_final),
            start_square=int(start_square),
            jumps=tuple(jumps_tuple),
            move=move,
            horizon_roll_count=None,
            optimal_route=tuple(),
            annotation_entity_ids=tuple(dict.fromkeys(annotation_ids)),
            construction_mode="single_die_move_outcome",
        )
        validate_snakes_ladders_sample(sample)
        return sample
    raise ValueError("failed to sample Snakes and Ladders move outcome scene")


def _critical_future_range(start_square: int, *, board_side: int) -> Tuple[int, ...]:
    """Return squares that should not receive random jumps in planning scenes."""

    last_square = board_last_square(int(board_side))
    low = max(1, int(start_square))
    high = min(int(last_square), int(start_square) + 24)
    return tuple(range(low, high + 1))


def _sample_best_roll_scene(*, rng, axes: _ResolvedAxes) -> SnakesLaddersSample:
    """Construct a multi-roll planning scene with a sampled best final square."""

    target_final = int(axes.target_answer)
    horizon = int(axes.horizon_roll_count)
    board_side = int(axes.board_side)
    last_square = board_last_square(board_side)
    start_square = int(target_final) - (6 * int(horizon))
    if int(start_square) < 2 or int(start_square) > int(last_square):
        raise ValueError("target final square is incompatible with the planning horizon")
    for _attempt in range(80):
        jumps: list[SnakesLaddersJump] = []
        target_ladders, target_snakes = _target_jump_counts(int(board_side))
        jumps_tuple = _add_random_jumps(
            rng=rng,
            jumps=tuple(jumps),
            board_side=int(board_side),
            protected_starts=tuple(),
            protected_range=_critical_future_range(int(start_square), board_side=int(board_side)),
            target_ladders=int(target_ladders),
            target_snakes=int(target_snakes),
        )
        answer = best_final_square(int(start_square), int(horizon), jumps_tuple, board_side=int(board_side))
        if int(answer) != int(target_final):
            continue
        route = trace_best_route(int(start_square), int(horizon), jumps_tuple, board_side=int(board_side))
        annotation_ids = (square_to_cell_id(int(target_final)),)
        sample = SnakesLaddersSample(
            mode="best_roll_value",
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            board_side=int(board_side),
            answer=int(target_final),
            start_square=int(start_square),
            jumps=tuple(jumps_tuple),
            move=None,
            horizon_roll_count=int(horizon),
            optimal_route=tuple(route),
            annotation_entity_ids=tuple(annotation_ids),
            construction_mode="best_final_square_planning",
        )
        validate_snakes_ladders_sample(sample)
        return sample
    raise ValueError("failed to sample Snakes and Ladders best-final-square scene")


def _sample_special_square_scene(*, rng, axes: _ResolvedAxes) -> SnakesLaddersSample:
    """Construct an interval count scene over visible snake/ladder starts."""

    target_answer = int(axes.target_answer)
    board_side = int(axes.board_side)
    last_square = board_last_square(board_side)
    query_kind = _special_query_kind(str(axes.query_id))
    opposite_kind = "snake" if query_kind == "ladder" else "ladder"
    valid_query_starts = _valid_jump_starts(kind=query_kind, board_side=int(board_side))
    valid_opposite_starts = _valid_jump_starts(kind=opposite_kind, board_side=int(board_side))

    candidate_start_squares = [
        int(square)
        for square in range(1, int(last_square))
        if len([value for value in valid_query_starts if int(value) > int(square)]) >= int(target_answer)
    ]
    if int(target_answer) == 0:
        candidate_start_squares = [
            int(square)
            for square in range(1, int(last_square) + 1)
            if not any(int(value) > int(square) for value in valid_query_starts)
        ]
    if not candidate_start_squares:
        raise ValueError("target special-square answer is incompatible with board side")

    for _attempt in range(220):
        start_square = int(rng.choice(tuple(candidate_start_squares)))
        after_query_starts = [int(value) for value in valid_query_starts if int(value) > int(start_square)]
        before_query_starts = [int(value) for value in valid_query_starts if int(value) < int(start_square)]
        jumps: Tuple[SnakesLaddersJump, ...] = tuple()
        jumps = _append_jumps_from_allowed_starts(
            rng=rng,
            jumps=jumps,
            board_side=int(board_side),
            kind=query_kind,
            allowed_starts=tuple(after_query_starts),
            count=int(target_answer),
            required=True,
        )
        if jumps is None:
            continue
        distractor_same_count = int(rng.randint(0, min(2, len(before_query_starts)))) if before_query_starts else 0
        jumps = _append_jumps_from_allowed_starts(
            rng=rng,
            jumps=jumps,
            board_side=int(board_side),
            kind=query_kind,
            allowed_starts=tuple(before_query_starts),
            count=int(distractor_same_count),
            required=False,
        )
        if jumps is None:
            continue
        allowed_opposite_starts = [int(value) for value in valid_opposite_starts if int(value) != int(start_square)]
        opposite_count = int(rng.randint(1, min(3, max(1, len(allowed_opposite_starts)))))
        jumps = _append_jumps_from_allowed_starts(
            rng=rng,
            jumps=jumps,
            board_side=int(board_side),
            kind=opposite_kind,
            allowed_starts=tuple(allowed_opposite_starts),
            count=int(opposite_count),
            required=False,
        )
        if jumps is None:
            continue
        annotation_ids = _special_square_entity_ids(
            jumps=tuple(jumps),
            kind=query_kind,
            start_square=int(start_square),
            board_side=int(board_side),
        )
        if len(annotation_ids) != int(target_answer):
            continue
        sample = SnakesLaddersSample(
            mode=str(axes.query_id),
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            board_side=int(board_side),
            answer=int(target_answer),
            start_square=int(start_square),
            jumps=tuple(jumps),
            move=None,
            horizon_roll_count=None,
            optimal_route=tuple(),
            annotation_entity_ids=tuple(annotation_ids),
            construction_mode="special_square_interval_count",
        )
        validate_snakes_ladders_sample(sample)
        return sample
    raise ValueError("failed to sample Snakes and Ladders special-square scene")


def _sample_scene(*, rng, axes: _ResolvedAxes) -> SnakesLaddersSample:
    """Construct one Snakes and Ladders sample."""

    if str(axes.query_id) == "move_outcome_value":
        return _sample_move_outcome_scene(rng=rng, axes=axes)
    if str(axes.query_id) == "best_roll_value":
        return _sample_best_roll_scene(rng=rng, axes=axes)
    if str(axes.query_id) in SPECIAL_SQUARE_QUERY_IDS:
        return _sample_special_square_scene(rng=rng, axes=axes)
    raise ValueError(f"unsupported query_id: {axes.query_id}")


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return prompt examples for JSON output."""

    if str(query_id) == "move_outcome_value":
        answer_value = 0
        annotation_value: Any = {
            "start_square": [88, 682, 178, 772],
            "end_square": [462, 398, 552, 488],
        }
    elif str(query_id) in SPECIAL_SQUARE_QUERY_IDS:
        answer_value = 2
        annotation_value = [[188, 682, 278, 772], [374, 496, 464, 586]]
    else:
        answer_value = 0
        annotation_value = [[554, 302, 644, 392]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


def _move_trace(move: SnakesLaddersMove) -> Dict[str, Any]:
    """Serialize one move trace."""

    return move.to_trace()


def _annotation_role_entity_ids(sample: SnakesLaddersSample) -> Dict[str, str]:
    """Return role-bound witness ids when the query needs semantic annotation binding."""

    if str(sample.mode) != "move_outcome_value" or sample.move is None:
        return {}
    move = sample.move
    return {
        "start_square": square_to_cell_id(int(sample.start_square)),
        "end_square": square_to_cell_id(int(move.final_square)),
    }


class GamesSnakesLaddersBoardTask:
    """Return one grounded query over a visible Snakes and Ladders board."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    supported_query_ids: Tuple[str, ...] = SUPPORTED_SNAKES_LADDERS_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params, supported_query_ids=tuple(self.supported_query_ids))
        render_params = _render_params(params, instance_seed=int(instance_seed), board_side=int(axes.board_side))

        sampled_scene: SnakesLaddersSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid Snakes and Ladders board after {max_attempts} attempts")

        panel_style, panel_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace="games.snakes_ladders.panel_scene_style",
            treatment_weights=params.get(
                "panel_scene_treatment_weights",
                group_default(_RENDER_DEFAULTS, "panel_scene_treatment_weights", None),
            ),
            palette_weights=params.get(
                "panel_scene_palette_weights",
                group_default(_RENDER_DEFAULTS, "panel_scene_palette_weights", None),
            ),
        )
        background, background_meta = make_panel_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=panel_style,
        )
        rendered_scene = render_snakes_ladders_board_scene(
            jumps=sampled_scene.jumps,
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
            start_square=int(sampled_scene.start_square),
            die_value=int(axes.die_value) if str(axes.query_id) == "move_outcome_value" else None,
            horizon_roll_count=int(sampled_scene.horizon_roll_count) if sampled_scene.horizon_roll_count is not None else None,
            show_roll_panel=str(axes.query_id) not in SPECIAL_SQUARE_QUERY_IDS,
            panel_style=panel_style,
        )
        annotation_role_entity_ids = _annotation_role_entity_ids(sampled_scene)
        if annotation_role_entity_ids:
            annotation_value: Any = {
                str(role): list(rendered_scene.render_map["entity_bboxes_px"][str(entity_id)])
                for role, entity_id in annotation_role_entity_ids.items()
            }
            annotation_type = "keyed_bbox_map"
            projected_annotation = {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_value),
                "pixel_keyed_bbox_map": dict(annotation_value),
            }
            witness_symbolic = {
                "type": "object_map",
                "ids": dict(annotation_role_entity_ids),
            }
            annotation_count = len(annotation_role_entity_ids)
        else:
            annotation_value = [
                list(rendered_scene.render_map["entity_bboxes_px"][str(entity_id)])
                for entity_id in sampled_scene.annotation_entity_ids
            ]
            annotation_type = "bbox_set"
            projected_annotation = {
                "type": "bbox_set",
                "bbox_set": [list(bbox) for bbox in annotation_value],
                "pixel_bbox_set": [list(bbox) for bbox in annotation_value],
            }
            witness_symbolic = {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
            }
            annotation_count = len(sampled_scene.annotation_entity_ids)
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_standard_board",
                "movement_rule_text",
                "overshoot_rule_text",
                "planning_rule_text",
                "special_square_count_rule_text",
                "answer_hint_move_outcome_value",
                "annotation_hint_move_outcome_value",
                "answer_hint_best_roll_value",
                "annotation_hint_best_roll_value",
                "answer_hint_ladder_start_ahead_count",
                "annotation_hint_ladder_start_ahead_count",
                "answer_hint_snake_head_ahead_count",
                "annotation_hint_snake_head_ahead_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            dynamic_slots={
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "movement_rule_text": str(prompt_defaults["movement_rule_text"]),
                "overshoot_rule_text": str(prompt_defaults["overshoot_rule_text"]),
                "planning_rule_text": str(prompt_defaults["planning_rule_text"]),
                "special_square_count_rule_text": str(prompt_defaults["special_square_count_rule_text"]),
                "die_value": int(axes.die_value),
                "horizon_roll_count": str(int(axes.horizon_roll_count)),
                "horizon_roll_label": f"{int(axes.horizon_roll_count)} roll{'s' if int(axes.horizon_roll_count) != 1 else ''}",
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(axes.query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
        annotation_gt = TypedValue(type=annotation_type, value=annotation_value)
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_snakes_ladders_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "board_side": int(axes.board_side),
                    "last_square": int(board_last_square(int(axes.board_side))),
                    "start_square": int(sampled_scene.start_square),
                    "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
                },
            },
            "query_spec": {
                "query_id": "default",
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "board_side": int(axes.board_side),
                    "board_side_probabilities": dict(axes.board_side_probabilities),
                    "last_square": int(board_last_square(int(axes.board_side))),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "target_answer": int(axes.target_answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "die_value": int(axes.die_value),
                    "die_value_probabilities": dict(axes.die_value_probabilities),
                    "horizon_roll_count": int(axes.horizon_roll_count),
                    "horizon_roll_count_probabilities": dict(axes.horizon_roll_count_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "board_side": int(axes.board_side),
                "last_square": int(board_last_square(int(axes.board_side))),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "text_style": dict(text_style_meta),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "board_side": int(axes.board_side),
                "last_square": int(board_last_square(int(axes.board_side))),
                "start_square": int(sampled_scene.start_square),
                "jumps": [jump.to_trace() for jump in sampled_scene.jumps],
                "shown_move": None if sampled_scene.move is None else _move_trace(sampled_scene.move),
                "horizon_roll_count": None if sampled_scene.horizon_roll_count is None else int(sampled_scene.horizon_roll_count),
                "optimal_route": [_move_trace(move) for move in sampled_scene.optimal_route],
                "best_final_square": int(
                    best_final_square(
                        sampled_scene.start_square,
                        int(sampled_scene.horizon_roll_count or 0),
                        sampled_scene.jumps,
                        board_side=int(axes.board_side),
                    )
                )
                if str(axes.query_id) == "best_roll_value"
                else None,
                "special_square_kind": _special_query_kind(str(axes.query_id)) if str(axes.query_id) in SPECIAL_SQUARE_QUERY_IDS else None,
                "special_square_interval": {
                    "start_exclusive": int(sampled_scene.start_square),
                    "end_inclusive": int(board_last_square(int(axes.board_side))),
                }
                if str(axes.query_id) in SPECIAL_SQUARE_QUERY_IDS
                else None,
                "answer": int(sampled_scene.answer),
                "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
                "annotation_role_entity_ids": dict(annotation_role_entity_ids),
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": dict(witness_symbolic),
            "projected_annotation": dict(projected_annotation),
            "background": background_meta,
            "post_image_noise": post_noise_meta,
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id="snakes_ladders",
            query_id=str(axes.query_id),
        )


class GamesSnakesLaddersMoveOutcomeValueTask(FixedQueryVariantTaskMixin, GamesSnakesLaddersBoardTask):
    """Return the final square after a shown one-die move."""

    task_id = "task_games__snakes_ladders__move_outcome_value"
    fixed_query_id = "move_outcome_value"
    supported_query_ids = ("move_outcome_value",)


@register_task
class GamesSnakesLaddersBestRollValueTask(FixedQueryVariantTaskMixin, GamesSnakesLaddersBoardTask):
    """Return the highest final square reachable over a short horizon."""

    task_id = "task_games__snakes_ladders__best_roll_value"
    fixed_query_id = "best_roll_value"
    supported_query_ids = ("best_roll_value",)


class GamesSnakesLaddersSpecialSquareCountTask(QuerySubsetTaskMixin, GamesSnakesLaddersBoardTask):
    """Count visible snake or ladder start squares ahead of the token."""

    task_id = "task_games__snakes_ladders__special_square_count"
    supported_query_ids = SPECIAL_SQUARE_QUERY_IDS


__all__ = [
    "GamesSnakesLaddersBestRollValueTask",
    "GamesSnakesLaddersBoardTask",
    "GamesSnakesLaddersMoveOutcomeValueTask",
    "GamesSnakesLaddersSpecialSquareCountTask",
]
