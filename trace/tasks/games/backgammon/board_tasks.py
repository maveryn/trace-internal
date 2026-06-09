"""Games Backgammon tasks over visible numbered boards."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.backgammon_common import (
    BACKGAMMON_POINT_STATE_QUERY_IDS,
    BACKGAMMON_QUERY_IDS,
    BACKGAMMON_STYLE_VARIANTS,
    PLAYER_BLACK,
    PLAYER_WHITE,
    POINT_IDS,
    BackgammonPoint,
    BackgammonSample,
    compute_single_die_destinations,
    destination_for_player,
    empty_points,
    opponent_for_player,
    point_matches_state_query,
    point_entity_id,
    stack_at,
    target_destinations_for_query,
    target_points_for_state_query,
    validate_backgammon_sample,
)
from ..shared.backgammon_scene import BackgammonRenderParams, render_backgammon_scene
from ..shared.complexity import build_games_backgammon_board_complexity
from ..shared.fixed_query_task import QuerySubsetTaskMixin
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_backgammon_board_base"
_BACKGAMMON_SCENE_VARIANTS: Tuple[str, ...] = ("standard_board",)
_ACTIVE_PLAYERS: Tuple[str, ...] = (PLAYER_BLACK, PLAYER_WHITE)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for Backgammon board scenes."""

    legal_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    hit_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    blocked_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    point_state_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
    canvas_width: int = 1000
    canvas_height: int = 720
    board_width_px: int = 900
    board_height_px: int = 560
    board_margin_px: int = 50
    board_border_width_px: int = 5
    point_label_font_size_px: int = 20
    header_font_size_px: int = 24
    checker_radius_px: int = 21
    die_size_px: int = 44
    dynamic_canvas_size_enabled: bool = True
    canvas_min_width_px: int = 560
    canvas_min_height_px: int = 420
    canvas_side_padding_px: int = 90
    canvas_vertical_padding_px: int = 80


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Backgammon instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    active_player: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    active_player_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "backgammon")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="backgammon", apply_prob=0.5)


def _resolve_query_id(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced Backgammon query id."""

    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=BACKGAMMON_QUERY_IDS,
    )


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
    """Resolve one balanced named Backgammon axis."""

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


def _uses_uniform_query_cycle(params: Mapping[str, Any], probabilities: Mapping[str, float]) -> bool:
    """Return true when the query axis is using the default balanced cycle."""

    if params.get("query_id") is not None or params.get("query_variant") is not None:
        return False
    enabled = bool(params.get("balanced_query_id_sampling", group_default(_GEN_DEFAULTS, "balanced_query_id_sampling", True)))
    if not enabled:
        return False
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if len(positives) != len(BACKGAMMON_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _params_for_query_occurrence_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-query occurrence index for balanced answer axes."""

    cycle_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return cycle_params
    if not _uses_uniform_query_cycle(params, query_id_probabilities):
        return cycle_params
    cycle_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(BACKGAMMON_QUERY_IDS))
    return cycle_params


def _support_key_for_query(query_id: str) -> Tuple[str, Tuple[int, ...]]:
    """Return the answer-support key and fallback for one query."""

    query = str(query_id)
    if query == "legal_move_count":
        return "legal_count_support", tuple(_DEFAULTS.legal_count_support)
    if query == "hit_move_count":
        return "hit_count_support", tuple(_DEFAULTS.hit_count_support)
    if query == "blocked_destination_count":
        return "blocked_count_support", tuple(_DEFAULTS.blocked_count_support)
    if query in BACKGAMMON_POINT_STATE_QUERY_IDS:
        return "point_state_count_support", tuple(_DEFAULTS.point_state_count_support)
    raise ValueError(f"unsupported Backgammon query_id: {query}")


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one Backgammon instance."""

    query_id, query_id_probabilities = _resolve_query_id(instance_seed=int(instance_seed), params=params)
    answer_cycle_params = _params_for_query_occurrence_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=_BACKGAMMON_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=BACKGAMMON_STYLE_VARIANTS,
    )
    active_player, active_player_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="active_player",
        explicit_key="active_player",
        weights_key="active_player_weights",
        balance_flag_key="balanced_active_player_sampling",
        supported=_ACTIVE_PLAYERS,
    )
    support_key, fallback_support = _support_key_for_query(str(query_id))
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=answer_cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=support_key,
        explicit_key="target_answer",
        fallback_support=fallback_support,
        namespace=f"target_answer.{str(query_id)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_answer_support = resolve_integer_support(
        answer_cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        key=support_key,
        fallback=fallback_support,
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        active_player=str(active_player),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        active_player_probabilities=dict(active_player_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> BackgammonRenderParams:
    """Resolve renderer parameters."""

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.backgammon.text_font",
        params=params,
    )
    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.backgammon.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.backgammon.layout",
        ),
        unit_scale_meta,
    )
    board_width_px = scale_games_px(
        params.get("board_width_px", group_default(_RENDER_DEFAULTS, "board_width_px", _DEFAULTS.board_width_px)),
        unit_scale,
        min_px=450,
    )
    board_height_px = scale_games_px(
        params.get("board_height_px", group_default(_RENDER_DEFAULTS, "board_height_px", _DEFAULTS.board_height_px)),
        unit_scale,
        min_px=280,
    )
    dynamic_canvas_enabled = bool(
        params.get(
            "dynamic_canvas_size_enabled",
            group_default(_RENDER_DEFAULTS, "dynamic_canvas_size_enabled", _DEFAULTS.dynamic_canvas_size_enabled),
        )
    )
    base_canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
    base_canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
    canvas_width = base_canvas_width
    canvas_height = base_canvas_height
    if dynamic_canvas_enabled and params.get("canvas_width") is None:
        canvas_width = min(
            int(base_canvas_width),
            max(
                int(params.get("canvas_min_width_px", group_default(_RENDER_DEFAULTS, "canvas_min_width_px", _DEFAULTS.canvas_min_width_px))),
                int(
                    round(
                        float(board_width_px)
                        + (2.0 * float(params.get("canvas_side_padding_px", group_default(_RENDER_DEFAULTS, "canvas_side_padding_px", _DEFAULTS.canvas_side_padding_px))))
                    )
                ),
            ),
        )
    if dynamic_canvas_enabled and params.get("canvas_height") is None:
        canvas_height = min(
            int(base_canvas_height),
            max(
                int(params.get("canvas_min_height_px", group_default(_RENDER_DEFAULTS, "canvas_min_height_px", _DEFAULTS.canvas_min_height_px))),
                int(
                    round(
                        float(board_height_px)
                        + (2.0 * float(params.get("canvas_vertical_padding_px", group_default(_RENDER_DEFAULTS, "canvas_vertical_padding_px", _DEFAULTS.canvas_vertical_padding_px))))
                    )
                ),
            ),
        )
    return BackgammonRenderParams(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        board_width_px=int(board_width_px),
        board_height_px=int(board_height_px),
        board_margin_px=scale_games_px(params.get("board_margin_px", group_default(_RENDER_DEFAULTS, "board_margin_px", _DEFAULTS.board_margin_px)), unit_scale, min_px=24),
        board_border_width_px=scale_games_px(params.get("board_border_width_px", group_default(_RENDER_DEFAULTS, "board_border_width_px", _DEFAULTS.board_border_width_px)), unit_scale, min_px=2),
        point_label_font_size_px=scale_games_px(params.get("point_label_font_size_px", group_default(_RENDER_DEFAULTS, "point_label_font_size_px", _DEFAULTS.point_label_font_size_px)), unit_scale, min_px=12),
        header_font_size_px=scale_games_px(params.get("header_font_size_px", group_default(_RENDER_DEFAULTS, "header_font_size_px", _DEFAULTS.header_font_size_px)), unit_scale, min_px=14),
        checker_radius_px=scale_games_px(params.get("checker_radius_px", group_default(_RENDER_DEFAULTS, "checker_radius_px", _DEFAULTS.checker_radius_px)), unit_scale, min_px=11),
        die_size_px=scale_games_px(params.get("die_size_px", group_default(_RENDER_DEFAULTS, "die_size_px", _DEFAULTS.die_size_px)), unit_scale, min_px=24),
        font_family=str(font_family),
        layout_jitter_meta=layout_jitter,
    )


def _choose_dice(rng: Any) -> Tuple[int, int]:
    """Choose two non-double dice values."""

    values = list(range(1, 7))
    rng.shuffle(values)
    return int(values[0]), int(values[1])


def _choose_source_points(
    rng: Any,
    *,
    dice: Tuple[int, int],
    source_count: int,
    active_player: str,
) -> Tuple[int, ...]:
    """Choose source points whose single-die destinations are not other sources."""

    if str(active_player) == PLAYER_BLACK:
        candidates = [point for point in POINT_IDS if int(point) > max(int(value) for value in dice)]
    else:
        candidates = [point for point in POINT_IDS if int(point) <= 24 - max(int(value) for value in dice)]
    rng.shuffle(candidates)
    selected: list[int] = []
    for candidate in candidates:
        blocked_by_source_conflict = False
        for existing in selected:
            for die in dice:
                if destination_for_player(int(candidate), int(die), active_player=str(active_player)) == int(existing):
                    blocked_by_source_conflict = True
                if destination_for_player(int(existing), int(die), active_player=str(active_player)) == int(candidate):
                    blocked_by_source_conflict = True
        if blocked_by_source_conflict:
            continue
        selected.append(int(candidate))
        if len(selected) >= int(source_count):
            return tuple(sorted(selected))
    raise ValueError("could not choose enough Backgammon black source points")


def _candidate_destinations(
    *,
    sources: Sequence[int],
    dice: Tuple[int, int],
    active_player: str,
) -> Tuple[int, ...]:
    """Return distinct single-die destination points for active-player sources."""

    destinations = {
        destination_for_player(int(source), int(die), active_player=str(active_player))
        for source in sources
        for die in dice
        if destination_for_player(int(source), int(die), active_player=str(active_player)) in POINT_IDS
    }
    return tuple(sorted(destinations))


def _target_state_for_query(rng: Any, *, query_id: str, is_target: bool, active_player: str) -> BackgammonPoint:
    """Return the stack state to place on a candidate destination."""

    query = str(query_id)
    opponent = opponent_for_player(str(active_player))
    if query == "legal_move_count":
        if bool(is_target):
            return BackgammonPoint(owner=None, count=0)
        return BackgammonPoint(owner=opponent, count=int(rng.randint(2, 4)))
    if query == "hit_move_count":
        if bool(is_target):
            return BackgammonPoint(owner=opponent, count=1)
        if float(rng.random()) < 0.48:
            return BackgammonPoint(owner=opponent, count=int(rng.randint(2, 4)))
        return BackgammonPoint(owner=None, count=0)
    if query == "blocked_destination_count":
        if bool(is_target):
            return BackgammonPoint(owner=opponent, count=int(rng.randint(2, 4)))
        if float(rng.random()) < 0.38:
            return BackgammonPoint(owner=opponent, count=1)
        return BackgammonPoint(owner=None, count=0)
    raise ValueError(f"unsupported Backgammon query_id: {query}")


def _sample_destination_scene(rng: Any, *, axes: _ResolvedAxes) -> BackgammonSample:
    """Construct one exact-answer Backgammon destination-count position."""

    query = str(axes.query_id)
    active_player = str(axes.active_player)
    opponent = opponent_for_player(active_player)
    target_answer = int(axes.target_answer)
    for _inner_attempt in range(1500):
        dice = _choose_dice(rng)
        min_sources = max(2, int((target_answer + 1) // 2))
        max_sources = min(8, max(min_sources, int(target_answer) + 2))
        source_count = int(rng.randint(int(min_sources), int(max_sources)))
        try:
            sources = _choose_source_points(
                rng,
                dice=dice,
                source_count=source_count,
                active_player=active_player,
            )
        except ValueError:
            continue
        candidates = _candidate_destinations(sources=sources, dice=dice, active_player=active_player)
        if len(candidates) < int(target_answer):
            continue
        target_destinations = tuple(sorted(rng.sample(list(candidates), int(target_answer))))
        target_set = set(int(point) for point in target_destinations)

        points = empty_points()
        for source in sources:
            points[int(source)] = BackgammonPoint(owner=active_player, count=int(rng.randint(1, 4)))
        for destination in candidates:
            points[int(destination)] = _target_state_for_query(
                rng,
                query_id=query,
                is_target=int(destination) in target_set,
                active_player=active_player,
            )

        protected_points = set(int(point) for point in sources) | set(int(point) for point in candidates)
        for point in POINT_IDS:
            if int(point) in protected_points:
                continue
            if float(rng.random()) < 0.20:
                points[int(point)] = BackgammonPoint(owner=opponent, count=int(rng.randint(1, 4)))

        outcome = compute_single_die_destinations(points, dice=dice, active_player=active_player)
        expected_targets = target_destinations_for_query(outcome, query_id=query)
        if tuple(expected_targets) != tuple(target_destinations):
            continue
        sample = BackgammonSample(
            points=dict(points),
            dice=(int(dice[0]), int(dice[1])),
            active_player=active_player,
            query_id=query,
            answer=int(target_answer),
            target_destinations=tuple(int(point) for point in target_destinations),
            outcome=outcome,
            style_variant=str(axes.style_variant),
            target_answer=int(target_answer),
            target_points=tuple(int(point) for point in target_destinations),
        )
        validate_backgammon_sample(sample)
        return sample
    raise ValueError(f"could not construct Backgammon sample for {query} answer {target_answer}")


def _target_state_for_point_state_query(rng: Any, *, query_id: str) -> BackgammonPoint:
    """Return a stack state that satisfies one point-state query."""

    query = str(query_id)
    if query == "black_single_checker_point_count":
        return BackgammonPoint(owner=PLAYER_BLACK, count=1)
    if query == "white_single_checker_point_count":
        return BackgammonPoint(owner=PLAYER_WHITE, count=1)
    if query == "black_two_or_more_checker_point_count":
        return BackgammonPoint(owner=PLAYER_BLACK, count=int(rng.randint(2, 4)))
    if query == "white_two_or_more_checker_point_count":
        return BackgammonPoint(owner=PLAYER_WHITE, count=int(rng.randint(2, 4)))
    raise ValueError(f"unsupported Backgammon point-state query_id: {query}")


def _non_target_state_for_point_state_query(rng: Any, *, query_id: str) -> BackgammonPoint:
    """Return a random visible stack state that does not satisfy one point-state query."""

    candidates = [
        BackgammonPoint(owner=None, count=0),
        BackgammonPoint(owner=PLAYER_BLACK, count=1),
        BackgammonPoint(owner=PLAYER_BLACK, count=2),
        BackgammonPoint(owner=PLAYER_BLACK, count=3),
        BackgammonPoint(owner=PLAYER_BLACK, count=4),
        BackgammonPoint(owner=PLAYER_WHITE, count=1),
        BackgammonPoint(owner=PLAYER_WHITE, count=2),
        BackgammonPoint(owner=PLAYER_WHITE, count=3),
        BackgammonPoint(owner=PLAYER_WHITE, count=4),
    ]
    non_matching = [
        candidate
        for candidate in candidates
        if not point_matches_state_query(candidate, query_id=str(query_id))
    ]
    selected = rng.choice(non_matching)
    return BackgammonPoint(owner=selected.owner, count=int(selected.count))


def _sample_point_state_scene(rng: Any, *, axes: _ResolvedAxes) -> BackgammonSample:
    """Construct one exact-answer Backgammon point-state count position."""

    query = str(axes.query_id)
    active_player = str(axes.active_player)
    target_answer = int(axes.target_answer)
    for _inner_attempt in range(500):
        dice = _choose_dice(rng)
        target_points = tuple(sorted(rng.sample(list(POINT_IDS), int(target_answer))))
        target_set = {int(point) for point in target_points}
        points = empty_points()
        for point in target_points:
            points[int(point)] = _target_state_for_point_state_query(rng, query_id=query)

        min_occupied = max(int(target_answer), 8)
        max_occupied = min(20, max(min_occupied, int(target_answer) + 12))
        occupied_count = int(rng.randint(int(min_occupied), int(max_occupied)))
        distractor_count = max(0, int(occupied_count) - int(target_answer))
        available_points = [int(point) for point in POINT_IDS if int(point) not in target_set]
        rng.shuffle(available_points)
        for point in available_points[:distractor_count]:
            points[int(point)] = _non_target_state_for_point_state_query(rng, query_id=query)

        expected_points = target_points_for_state_query(points, query_id=query)
        if tuple(expected_points) != tuple(target_points):
            continue
        outcome = compute_single_die_destinations(points, dice=dice, active_player=active_player)
        sample = BackgammonSample(
            points=dict(points),
            dice=(int(dice[0]), int(dice[1])),
            active_player=active_player,
            query_id=query,
            answer=int(target_answer),
            target_destinations=(),
            outcome=outcome,
            style_variant=str(axes.style_variant),
            target_answer=int(target_answer),
            target_points=tuple(int(point) for point in target_points),
        )
        validate_backgammon_sample(sample)
        return sample
    raise ValueError(f"could not construct Backgammon point-state sample for {query} answer {target_answer}")


def _sample_scene(rng: Any, *, axes: _ResolvedAxes) -> BackgammonSample:
    """Construct one exact-answer Backgammon position."""

    if str(axes.query_id) in BACKGAMMON_POINT_STATE_QUERY_IDS:
        return _sample_point_state_scene(rng, axes=axes)
    return _sample_destination_scene(rng, axes=axes)


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Backgammon JSON output."""

    if str(query_id) == "hit_move_count":
        answer_value = 2
        annotation_value = [[410, 104, 475, 316], [608, 104, 673, 316]]
    elif str(query_id) == "blocked_destination_count":
        answer_value = 3
        annotation_value = [[276, 400, 341, 612], [342, 400, 407, 612], [608, 400, 673, 612]]
    elif str(query_id) in BACKGAMMON_POINT_STATE_QUERY_IDS:
        answer_value = 3
        annotation_value = [[144, 104, 209, 316], [342, 104, 407, 316], [608, 400, 673, 612]]
    else:
        answer_value = 3
        annotation_value = [[144, 104, 209, 316], [210, 104, 275, 316], [608, 104, 673, 316]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesBackgammonBoardTask:
    """Return one grounded query over a visible Backgammon board."""

    task_id = TASK_ID
    domain = "games"
    task_group = "backgammon"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
        }

        sampled_scene: BackgammonSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid Backgammon scene after {max_attempts} attempts")

        allowed_panel_treatments_raw = params.get(
            "panel_scene_treatments",
            group_default(_RENDER_DEFAULTS, "panel_scene_treatments", None),
        )
        if isinstance(allowed_panel_treatments_raw, str):
            allowed_panel_treatments = (str(allowed_panel_treatments_raw),)
        elif allowed_panel_treatments_raw is None:
            allowed_panel_treatments = None
        else:
            allowed_panel_treatments = tuple(str(item) for item in allowed_panel_treatments_raw)
        panel_style, panel_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace="games.backgammon_board.panel_scene_style",
            treatments=allowed_panel_treatments,
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
        rendered_scene = render_backgammon_scene(
            points=sampled_scene.points,
            dice=sampled_scene.dice,
            background=background,
            style_variant=str(axes.style_variant),
            active_player=str(sampled_scene.active_player),
            params=render_params,
            panel_style=panel_style,
        )
        target_points = tuple(int(point) for point in (sampled_scene.target_points or sampled_scene.target_destinations))
        annotation_entity_ids = [point_entity_id(point) for point in target_points]
        annotation_bboxes = [
            list(rendered_scene.render_map["entity_bboxes_px"][str(entity_id)])
            for entity_id in annotation_entity_ids
        ]
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
                "backgammon_rule_text",
                "answer_hint_legal_move_count",
                "annotation_hint_legal_move_count",
                "answer_hint_hit_move_count",
                "annotation_hint_hit_move_count",
                "answer_hint_blocked_destination_count",
                "annotation_hint_blocked_destination_count",
                "answer_hint_black_single_checker_point_count",
                "annotation_hint_black_single_checker_point_count",
                "answer_hint_white_single_checker_point_count",
                "annotation_hint_white_single_checker_point_count",
                "answer_hint_black_two_or_more_checker_point_count",
                "annotation_hint_black_two_or_more_checker_point_count",
                "answer_hint_white_two_or_more_checker_point_count",
                "annotation_hint_white_two_or_more_checker_point_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "backgammon_rule_text": str(prompt_defaults["backgammon_rule_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(axes.query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
        annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])
        active_source_count = sum(
            1
            for point in POINT_IDS
            if str(stack_at(sampled_scene.points, int(point)).owner) == str(sampled_scene.active_player)
        )
        occupied_count = sum(
            1
            for point in POINT_IDS
            if stack_at(sampled_scene.points, int(point)).owner is not None
        )
        complexity = build_games_backgammon_board_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            occupied_point_count=int(occupied_count),
            black_source_count=int(active_source_count),
            target_answer=int(sampled_scene.answer),
            annotation_count=len(annotation_entity_ids),
        )
        point_trace = [
            {
                "point_id": int(point),
                "owner": stack_at(sampled_scene.points, int(point)).owner,
                "count": int(stack_at(sampled_scene.points, int(point)).count),
                "entity_id": point_entity_id(point),
            }
            for point in POINT_IDS
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_backgammon_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "active_player": str(sampled_scene.active_player),
                    "dice": [int(value) for value in sampled_scene.dice],
                    "target_destinations": [int(point) for point in sampled_scene.target_destinations],
                    "target_points": [int(point) for point in target_points],
                    "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
                },
            },
            "query_spec": {
                "query_id": str(axes.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "active_player": str(sampled_scene.active_player),
                    "dice": [int(value) for value in sampled_scene.dice],
                    "target_answer": int(sampled_scene.answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "active_player_probabilities": dict(axes.active_player_probabilities),
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "active_player": str(sampled_scene.active_player),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "text_style": dict(text_style_meta),
                "effective_point_width_px": rendered_scene.render_map.get("effective_point_width_px"),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "active_player": str(sampled_scene.active_player),
                "points": point_trace,
                "dice": [int(value) for value in sampled_scene.dice],
                "outcome": {
                    "legal_destinations": [int(point) for point in sampled_scene.outcome.legal_destinations],
                    "hit_destinations": [int(point) for point in sampled_scene.outcome.hit_destinations],
                    "blocked_destinations": [int(point) for point in sampled_scene.outcome.blocked_destinations],
                },
                "target_destinations": [int(point) for point in sampled_scene.target_destinations],
                "target_points": [int(point) for point in target_points],
                "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
                "construction_mode": "exact_point_state_count"
                if str(axes.query_id) in BACKGAMMON_POINT_STATE_QUERY_IDS
                else "exact_destination_count",
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in annotation_entity_ids],
            },
            "projected_annotation": {
                "bbox_set": [list(bbox) for bbox in annotation_bboxes],
            },
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
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id="backgammon",
            query_id=str(axes.query_id),
        )


@register_task
class GamesBackgammonLegalMoveCountTask(QuerySubsetTaskMixin, GamesBackgammonBoardTask):
    """Count Backgammon legal or hit destination points."""

    task_id = "task_games__backgammon__legal_move_count"
    supported_query_ids = (
        "legal_move_count",
        "hit_move_count",
    )


@register_task
class GamesBackgammonBlockedDestinationCountTask(QuerySubsetTaskMixin, GamesBackgammonBoardTask):
    """Count Backgammon blocked destination points."""

    task_id = "task_games__backgammon__blocked_destination_count"
    supported_query_ids = ("blocked_destination_count",)


@register_task
class GamesBackgammonPointStateCountTask(QuerySubsetTaskMixin, GamesBackgammonBoardTask):
    """Count numbered Backgammon points by checker color and stack state."""

    task_id = "task_games__backgammon__point_state_count"
    supported_query_ids = (
        "black_single_checker_point_count",
        "white_single_checker_point_count",
        "black_two_or_more_checker_point_count",
        "white_two_or_more_checker_point_count",
    )


__all__ = [
    "GamesBackgammonBlockedDestinationCountTask",
    "GamesBackgammonBoardTask",
    "GamesBackgammonLegalMoveCountTask",
    "GamesBackgammonPointStateCountTask",
]
