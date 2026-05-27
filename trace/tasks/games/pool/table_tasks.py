"""Games Pool-table tasks for direct-shot geometry queries."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.complexity import build_games_pool_table_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin, QuerySubsetTaskMixin
from ..shared.layout import resolve_games_layout_jitter
from ..shared.pool_common import (
    POOL_BALL_NUMBERS,
    POOL_POCKETS,
    SUPPORTED_POOL_QUERY_IDS,
    SUPPORTED_POOL_SCENE_VARIANTS,
    PoolBall,
    PoolPocket,
    PoolSample,
    ball_entity_id,
    ball_group,
    balls_on_segment,
    DEFAULT_MAX_DIRECT_SHOT_ANGLE_DEGREES,
    object_balls,
    point_distance,
    pottable_ball_ids,
    sorted_ids,
    validate_pool_sample,
)
from ..shared.pool_scene import PoolRenderParams, render_pool_table_scene
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.style import SUPPORTED_POOL_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "games_pool_table_base"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Pool-table scenes."""

    pottable_ball_count_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    legal_group_pottable_count_support: Tuple[int, ...] = (1, 2, 3, 4)
    blocking_ball_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    object_ball_count_support: Tuple[int, ...] = (7, 8, 9, 10)
    line_clearance: float = 0.055
    max_direct_shot_angle_degrees: float = DEFAULT_MAX_DIRECT_SHOT_ANGLE_DEGREES
    min_ball_distance: float = 0.075
    canvas_width: int = 1120
    canvas_height: int = 760
    panel_margin_px: int = 42
    table_width_px: int = 940
    table_height_px: int = 520
    rail_width_px: int = 44
    pocket_radius_px: int = 24
    ball_radius_px: int = 18
    ball_number_font_size_px: int = 15
    badge_font_size_px: int = 22


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Pool-table instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    object_ball_count: int
    target_answer: int
    target_answer_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    object_ball_count_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "pool")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="pool")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="pool", apply_prob=0.0)


def _target_support_key(query_id: str) -> str:
    """Return the configured answer-support key for one Pool query."""

    return {
        "pottable_ball_count": "pottable_ball_count_support",
        "legal_group_pottable_count": "legal_group_pottable_count_support",
        "blocking_ball_count": "blocking_ball_count_support",
    }[str(query_id)]


def _uses_uniform_query_cycle(params: Mapping[str, Any], probabilities: Mapping[str, float]) -> bool:
    """Return true when the query axis is using the default balanced cycle."""

    if params.get("query_id") is not None or params.get("query_id") is not None:
        return False
    if not bool(params.get("balanced_query_id_sampling", group_default(_GEN_DEFAULTS, "balanced_query_id_sampling", True))):
        return False
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    return len(positives) == len(SUPPORTED_POOL_QUERY_IDS) and max(positives) - min(positives) <= 1e-9


def _params_for_query_occurrence_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-query occurrence index for balanced inner axes."""

    cycle_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None or not _uses_uniform_query_cycle(params, query_id_probabilities):
        return cycle_params
    cycle_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_POOL_QUERY_IDS))
    return cycle_params


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
    """Resolve one balanced named Pool axis."""

    return resolve_games_named_axis(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=[str(item) for item in supported],
    )


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one Pool-table instance."""

    query_id, query_id_probabilities = resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_POOL_QUERY_IDS,
    )
    cycle_params = _params_for_query_occurrence_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=cycle_params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_POOL_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=cycle_params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_POOL_STYLE_VARIANTS,
    )
    object_ball_count, object_ball_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="object_ball_count_support",
        explicit_key="object_ball_count",
        fallback_support=_DEFAULTS.object_ball_count_support,
        namespace=f"{TASK_ID}.object_ball_count.{str(query_id)}",
        balanced_flag_key="balanced_object_ball_count_sampling",
        namespace_support_permutation=True,
    )
    support_key = _target_support_key(str(query_id))
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=support_key,
        explicit_key="target_answer",
        fallback_support=getattr(_DEFAULTS, support_key),
        namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_answer_support = resolve_integer_support(
        cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        key=support_key,
        fallback=getattr(_DEFAULTS, support_key),
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        object_ball_count=int(object_ball_count),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        object_ball_count_probabilities=dict(object_ball_count_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> PoolRenderParams:
    """Resolve Pool rendering parameters from config/defaults."""

    return PoolRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        table_width_px=int(params.get("table_width_px", group_default(_RENDER_DEFAULTS, "table_width_px", _DEFAULTS.table_width_px))),
        table_height_px=int(params.get("table_height_px", group_default(_RENDER_DEFAULTS, "table_height_px", _DEFAULTS.table_height_px))),
        rail_width_px=int(params.get("rail_width_px", group_default(_RENDER_DEFAULTS, "rail_width_px", _DEFAULTS.rail_width_px))),
        pocket_radius_px=int(params.get("pocket_radius_px", group_default(_RENDER_DEFAULTS, "pocket_radius_px", _DEFAULTS.pocket_radius_px))),
        ball_radius_px=int(params.get("ball_radius_px", group_default(_RENDER_DEFAULTS, "ball_radius_px", _DEFAULTS.ball_radius_px))),
        ball_number_font_size_px=int(params.get("ball_number_font_size_px", group_default(_RENDER_DEFAULTS, "ball_number_font_size_px", _DEFAULTS.ball_number_font_size_px))),
        badge_font_size_px=int(params.get("badge_font_size_px", group_default(_RENDER_DEFAULTS, "badge_font_size_px", _DEFAULTS.badge_font_size_px))),
        layout_jitter_meta=resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.pool.layout",
        ),
    )


def _clearance(params: Mapping[str, Any]) -> float:
    """Return the line-clearance radius for direct-shot geometry."""

    return float(params.get("line_clearance", group_default(_GEN_DEFAULTS, "line_clearance", _DEFAULTS.line_clearance)))


def _max_direct_shot_angle_degrees(params: Mapping[str, Any]) -> float:
    """Return the maximum cue-to-ball / ball-to-pocket angle for direct pots."""

    return float(
        params.get(
            "max_direct_shot_angle_degrees",
            group_default(
                _GEN_DEFAULTS,
                "max_direct_shot_angle_degrees",
                _DEFAULTS.max_direct_shot_angle_degrees,
            ),
        )
    )


def _min_ball_distance(params: Mapping[str, Any]) -> float:
    """Return the minimum normalized distance between ball centers."""

    return float(params.get("min_ball_distance", group_default(_GEN_DEFAULTS, "min_ball_distance", _DEFAULTS.min_ball_distance)))


def _is_inside_table(point: Tuple[float, float]) -> bool:
    """Return whether a normalized point is inside the playable table area."""

    x, y = point
    return 0.075 <= float(x) <= 0.925 and 0.095 <= float(y) <= 0.905


def _add_ball(
    balls: list[PoolBall],
    *,
    number: int,
    center: Tuple[float, float],
    is_marked: bool = False,
) -> None:
    """Append one ball to the generated layout."""

    balls.append(
        PoolBall(
            ball_id=ball_entity_id(int(number)),
            number=int(number),
            group=ball_group(int(number)),
            center=(round(float(center[0]), 5), round(float(center[1]), 5)),
            is_cue=bool(int(number) == 0),
            is_marked=bool(is_marked),
        )
    )


def _position_available(center: Tuple[float, float], balls: Sequence[PoolBall], *, min_distance: float) -> bool:
    """Return whether a new ball can be placed at a center."""

    return _is_inside_table(center) and all(point_distance(center, ball.center) >= float(min_distance) for ball in balls)


def _sample_free_position(rng, balls: Sequence[PoolBall], *, min_distance: float) -> Tuple[float, float]:
    """Sample one non-overlapping object-ball position."""

    for _ in range(800):
        center = (float(rng.uniform(0.10, 0.90)), float(rng.uniform(0.13, 0.87)))
        if _position_available(center, balls, min_distance=float(min_distance)):
            return center
    raise ValueError("failed to sample non-overlapping pool ball")


def _random_layout(*, rng, object_ball_count: int, params: Mapping[str, Any]) -> Tuple[PoolBall, ...]:
    """Sample a generic pool-ball layout."""

    balls: list[PoolBall] = []
    cue_center = (float(rng.uniform(0.135, 0.235)), float(rng.uniform(0.42, 0.58)))
    _add_ball(balls, number=0, center=cue_center)
    numbers = list(POOL_BALL_NUMBERS)
    rng.shuffle(numbers)
    selected = numbers[: int(object_ball_count)]
    min_distance = _min_ball_distance(params)
    for number in selected:
        _add_ball(
            balls,
            number=int(number),
            center=_sample_free_position(rng, balls, min_distance=float(min_distance)),
        )
    return tuple(balls)


def _sample_direct_lane_position(
    rng,
    *,
    cue_center: Tuple[float, float],
    pocket: PoolPocket,
    balls: Sequence[PoolBall],
    min_distance: float,
) -> Tuple[float, float]:
    """Sample one object-ball center on a visually clear cue-to-pocket lane."""

    for _ in range(500):
        t = float(rng.uniform(0.30, 0.72))
        offset = float(rng.uniform(-0.012, 0.012))
        center = _point_on_segment(cue_center, pocket.center, t=t, offset=offset)
        if _position_available(center, balls, min_distance=float(min_distance)):
            return center
    raise ValueError("failed to sample clear pool direct-lane ball")


def _exact_pottable_ids(
    *,
    balls: Sequence[PoolBall],
    clearance: float,
    max_angle_degrees: float,
) -> Tuple[str, ...]:
    """Return pottable ids under the shared direct-shot rule."""

    return pottable_ball_ids(
        balls=balls,
        pockets=POOL_POCKETS,
        cue_ball_id="cue_ball",
        clearance=float(clearance),
        max_angle_degrees=float(max_angle_degrees),
    )


def _clear_pottable_count_layout(
    *,
    rng,
    object_ball_count: int,
    target_answer: int,
    params: Mapping[str, Any],
) -> Tuple[PoolBall, ...]:
    """Construct clear direct lanes for the target pottable-ball count."""

    if int(target_answer) > len(POOL_POCKETS):
        raise ValueError("pool pottable answer exceeds available direct-lane anchors")

    min_distance = _min_ball_distance(params)
    clearance = _clearance(params)
    max_angle = _max_direct_shot_angle_degrees(params)
    cue_center = (float(rng.uniform(0.165, 0.220)), float(rng.uniform(0.455, 0.545)))
    balls: list[PoolBall] = []
    _add_ball(balls, number=0, center=cue_center)

    numbers = list(POOL_BALL_NUMBERS)
    rng.shuffle(numbers)
    selected = numbers[: int(object_ball_count)]
    target_numbers = selected[: int(target_answer)]
    target_ids = {ball_entity_id(int(number)) for number in target_numbers}

    pockets = list(POOL_POCKETS)
    rng.shuffle(pockets)
    for number, pocket in zip(target_numbers, pockets):
        for _attempt in range(160):
            trial = list(balls)
            _add_ball(
                trial,
                number=int(number),
                center=_sample_direct_lane_position(
                    rng,
                    cue_center=cue_center,
                    pocket=pocket,
                    balls=trial,
                    min_distance=float(min_distance),
                ),
            )
            if ball_entity_id(int(number)) in set(
                _exact_pottable_ids(
                    balls=trial,
                    clearance=float(clearance),
                    max_angle_degrees=float(max_angle),
                )
            ):
                balls = trial
                break
        else:
            raise ValueError("failed to place target pool pottable ball")

    if set(_exact_pottable_ids(balls=balls, clearance=float(clearance), max_angle_degrees=float(max_angle))) != target_ids:
        raise ValueError("constructed pool targets are not exactly pottable")

    for number in selected[int(target_answer) :]:
        for _attempt in range(1600):
            candidate = _sample_free_position(rng, balls, min_distance=float(min_distance))
            trial = list(balls)
            _add_ball(trial, number=int(number), center=candidate)
            if set(_exact_pottable_ids(balls=trial, clearance=float(clearance), max_angle_degrees=float(max_angle))) == target_ids:
                balls = trial
                break
        else:
            raise ValueError("failed to place non-pottable pool distractor")

    if len(_exact_pottable_ids(balls=balls, clearance=float(clearance), max_angle_degrees=float(max_angle))) != int(target_answer):
        raise ValueError("constructed pool pottable count did not match target")
    return tuple(balls)


def _legal_group_payload(
    *,
    balls: Sequence[PoolBall],
    pockets: Sequence[PoolPocket],
    cue_ball_id: str,
    clearance: float,
    target_answer: int,
    max_angle_degrees: float,
) -> Tuple[str, Tuple[str, ...]]:
    """Choose a current-player group whose pottable count matches the target."""

    all_pottable = set(
        pottable_ball_ids(
            balls=balls,
            pockets=pockets,
            cue_ball_id=str(cue_ball_id),
            clearance=float(clearance),
            max_angle_degrees=float(max_angle_degrees),
        )
    )
    candidates: list[Tuple[str, Tuple[str, ...]]] = []
    for group in ("solid", "stripe"):
        ids = sorted_ids(ball.ball_id for ball in object_balls(balls) if str(ball.group) == group and str(ball.ball_id) in all_pottable)
        if len(ids) == int(target_answer):
            candidates.append((group, ids))
    if not candidates:
        raise ValueError("no legal pool group matches target answer")
    return candidates[0]


def _point_on_segment(
    start: Tuple[float, float],
    end: Tuple[float, float],
    *,
    t: float,
    offset: float,
) -> Tuple[float, float]:
    """Return one point near a shot segment."""

    sx, sy = start
    ex, ey = end
    vx = float(ex - sx)
    vy = float(ey - sy)
    length = max(1e-6, (vx * vx + vy * vy) ** 0.5)
    nx = -vy / length
    ny = vx / length
    return (float(sx + (t * vx) + (offset * nx)), float(sy + (t * vy) + (offset * ny)))


def _blocking_layout(*, rng, target_answer: int, params: Mapping[str, Any]) -> PoolSample:
    """Construct a marked two-segment shot with a controlled blocker count."""

    min_distance = _min_ball_distance(params)
    clearance = _clearance(params)
    cue_center = (float(rng.uniform(0.145, 0.185)), float(rng.uniform(0.48, 0.56)))
    target_center = (float(rng.uniform(0.48, 0.56)), float(rng.uniform(0.36, 0.46)))
    pocket = POOL_POCKETS[2] if target_center[1] < 0.50 else POOL_POCKETS[5]
    target_number = int(rng.choice([2, 3, 4, 5, 6, 9, 10, 11, 12, 13]))
    balls: list[PoolBall] = []
    _add_ball(balls, number=0, center=cue_center)
    _add_ball(balls, number=target_number, center=target_center, is_marked=True)

    used_numbers = {0, target_number}
    blocker_ids: list[str] = []
    blocker_ts = [0.34, 0.54, 0.72, 0.86]
    for index in range(int(target_answer)):
        segment_start, segment_end = (cue_center, target_center) if index % 2 == 0 else (target_center, pocket.center)
        center = _point_on_segment(
            segment_start,
            segment_end,
            t=blocker_ts[index % len(blocker_ts)],
            offset=float(rng.uniform(-0.010, 0.010)),
        )
        if not _position_available(center, balls, min_distance=float(min_distance) * 0.70):
            raise ValueError("failed to place pool blocker")
        number = next(value for value in POOL_BALL_NUMBERS if value not in used_numbers)
        used_numbers.add(int(number))
        _add_ball(balls, number=int(number), center=center)
        blocker_ids.append(ball_entity_id(int(number)))

    foil_count = int(rng.randint(5, 8))
    for _ in range(foil_count):
        number = next(value for value in POOL_BALL_NUMBERS if value not in used_numbers)
        used_numbers.add(int(number))
        for _attempt in range(400):
            center = _sample_free_position(rng, balls, min_distance=float(min_distance))
            if (
                point_distance(center, cue_center) > 0.11
                and point_distance(center, target_center) > 0.11
                and point_distance(center, pocket.center) > 0.11
                and not balls_on_segment(
                    balls=[PoolBall("candidate", number, ball_group(number), center)],
                    start=cue_center,
                    end=target_center,
                    ignore_ball_ids=(),
                    clearance=float(clearance),
                )
                and not balls_on_segment(
                    balls=[PoolBall("candidate", number, ball_group(number), center)],
                    start=target_center,
                    end=pocket.center,
                    ignore_ball_ids=(),
                    clearance=float(clearance),
                )
            ):
                _add_ball(balls, number=int(number), center=center)
                break
        else:
            raise ValueError("failed to place pool foil")

    target_id = ball_entity_id(target_number)
    segment_a = balls_on_segment(
        balls=balls,
        start=cue_center,
        end=target_center,
        ignore_ball_ids=("cue_ball", target_id),
        clearance=float(clearance),
    )
    segment_b = balls_on_segment(
        balls=balls,
        start=target_center,
        end=pocket.center,
        ignore_ball_ids=(target_id,),
        clearance=float(clearance),
    )
    actual_blockers = sorted_ids(ball.ball_id for ball in (*segment_a, *segment_b))
    if len(actual_blockers) != int(target_answer):
        raise ValueError("constructed pool blocker count did not match target")
    sample = PoolSample(
        query_id="blocking_ball_count",
        scene_variant="standard_table",
        answer=int(target_answer),
        balls=tuple(balls),
        pockets=POOL_POCKETS,
        cue_ball_id="cue_ball",
        marked_ball_id=str(target_id),
        marked_pocket_id=str(pocket.pocket_id),
        current_player_group=None,
        evidence_ball_ids=actual_blockers,
        evidence_pocket_ids=tuple(),
        pottable_ball_ids=tuple(),
        legal_pottable_ball_ids=tuple(),
        blocking_ball_ids=actual_blockers,
        target_answer=int(target_answer),
        construction_mode="marked_two_segment_shot_with_controlled_blockers",
    )
    validate_pool_sample(sample)
    return sample


def _sample_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> PoolSample:
    """Construct one Pool-table scene for the requested axes."""

    if str(axes.query_id) == "blocking_ball_count":
        sample = _blocking_layout(rng=rng, target_answer=int(axes.target_answer), params=params)
        return replace(sample, scene_variant=str(axes.scene_variant))

    query = str(axes.query_id)
    if query == "pottable_ball_count":
        balls = _clear_pottable_count_layout(
            rng=rng,
            object_ball_count=int(axes.object_ball_count),
            target_answer=int(axes.target_answer),
            params=params,
        )
    else:
        balls = _random_layout(rng=rng, object_ball_count=int(axes.object_ball_count), params=params)
    pockets = POOL_POCKETS
    clearance = _clearance(params)
    max_angle = _max_direct_shot_angle_degrees(params)
    all_pottable = pottable_ball_ids(
        balls=balls,
        pockets=pockets,
        cue_ball_id="cue_ball",
        clearance=float(clearance),
        max_angle_degrees=float(max_angle),
    )
    if query == "pottable_ball_count":
        if len(all_pottable) != int(axes.target_answer):
            raise ValueError("pool pottable count does not match target")
        sample = PoolSample(
            query_id=query,
            scene_variant=str(axes.scene_variant),
            answer=len(all_pottable),
            balls=balls,
            pockets=pockets,
            cue_ball_id="cue_ball",
            marked_ball_id=None,
            marked_pocket_id=None,
            current_player_group=None,
            evidence_ball_ids=all_pottable,
            evidence_pocket_ids=tuple(),
            pottable_ball_ids=all_pottable,
            legal_pottable_ball_ids=tuple(),
            blocking_ball_ids=tuple(),
            target_answer=int(axes.target_answer),
            construction_mode="clear_direct_lane_pool_layout_pottable_count",
        )
    elif query == "legal_group_pottable_count":
        group, legal_ids = _legal_group_payload(
            balls=balls,
            pockets=pockets,
            cue_ball_id="cue_ball",
            clearance=float(clearance),
            target_answer=int(axes.target_answer),
            max_angle_degrees=float(max_angle),
        )
        sample = PoolSample(
            query_id=query,
            scene_variant=str(axes.scene_variant),
            answer=len(legal_ids),
            balls=balls,
            pockets=pockets,
            cue_ball_id="cue_ball",
            marked_ball_id=None,
            marked_pocket_id=None,
            current_player_group=str(group),
            evidence_ball_ids=legal_ids,
            evidence_pocket_ids=tuple(),
            pottable_ball_ids=all_pottable,
            legal_pottable_ball_ids=legal_ids,
            blocking_ball_ids=tuple(),
            target_answer=int(axes.target_answer),
            construction_mode="random_pool_layout_current_group_pottable_count",
        )
    else:
        raise ValueError(f"unsupported Pool query_id: {axes.query_id}")
    validate_pool_sample(sample)
    return sample


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Pool JSON output."""

    answer_value = 2 if str(query_id) == "blocking_ball_count" else 3
    evidence_value = [[180, 220, 220, 260], [520, 310, 560, 350]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesPoolTableTask:
    """Return one grounded query over a visible Pool-table scene."""

    task_id = TASK_ID
    domain = "games"
    task_group = "pool"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))
        sampled_scene: PoolSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes, params=params)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        badge_text = ""
        if sampled_scene.current_player_group:
            badge_text = f"Current player: {str(sampled_scene.current_player_group).upper()}"
        rendered_scene = render_pool_table_scene(
            balls=sampled_scene.balls,
            pockets=sampled_scene.pockets,
            background=background,
            style_variant=str(axes.style_variant),
            badge_text=badge_text,
            marked_ball_id=sampled_scene.marked_ball_id,
            marked_pocket_id=sampled_scene.marked_pocket_id,
            shot_path_ball_id=sampled_scene.marked_ball_id if str(axes.query_id) == "blocking_ball_count" else None,
            shot_path_pocket_id=sampled_scene.marked_pocket_id if str(axes.query_id) == "blocking_ball_count" else None,
            params=render_params,
        )
        evidence_entity_ids = [*sampled_scene.evidence_ball_ids, *sampled_scene.evidence_pocket_ids]
        evidence_bboxes = [
            list(rendered_scene.render_map["ball_bboxes_px"][entity_id])
            if entity_id in rendered_scene.render_map["ball_bboxes_px"]
            else list(rendered_scene.render_map["pocket_bboxes_px"][entity_id])
            for entity_id in evidence_entity_ids
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
                "object_description_standard_table",
                "direct_shot_rule_text",
                "legal_group_rule_text",
                "marked_shot_rule_text",
                "answer_hint_pottable_ball_count",
                "answer_hint_legal_group_pottable_count",
                "answer_hint_blocking_ball_count",
                "evidence_hint_pottable_ball_count",
                "evidence_hint_legal_group_pottable_count",
                "evidence_hint_blocking_ball_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
        group_text = ""
        if sampled_scene.current_player_group:
            group_text = str(sampled_scene.current_player_group)
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "direct_shot_rule_text": str(prompt_defaults["direct_shot_rule_text"]),
                "legal_group_rule_text": str(prompt_defaults["legal_group_rule_text"]),
                "marked_shot_rule_text": str(prompt_defaults["marked_shot_rule_text"]),
                "current_player_group": str(group_text),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_pool_table_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            object_ball_count=len(object_balls(sampled_scene.balls)),
            target_answer=int(sampled_scene.target_answer),
            evidence_count=len(evidence_entity_ids),
        )

        ball_trace = [
            {
                "ball_id": str(ball.ball_id),
                "number": int(ball.number),
                "group": str(ball.group),
                "center": [float(ball.center[0]), float(ball.center[1])],
                "is_cue": bool(ball.is_cue),
                "is_marked": bool(ball.is_marked),
            }
            for ball in sampled_scene.balls
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_pool_table_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "target_answer": int(sampled_scene.target_answer),
                    "evidence_entity_ids": [str(entity_id) for entity_id in evidence_entity_ids],
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
                    "object_ball_count": int(axes.object_ball_count),
                    "current_player_group": sampled_scene.current_player_group,
                    "marked_ball_id": sampled_scene.marked_ball_id,
                    "marked_pocket_id": sampled_scene.marked_pocket_id,
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "object_ball_count_probabilities": dict(axes.object_ball_count_probabilities),
                    "target_answer": int(sampled_scene.target_answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "line_clearance": float(_clearance(params)),
                    "max_direct_shot_angle_degrees": float(_max_direct_shot_angle_degrees(params)),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "object_ball_count": len(object_balls(sampled_scene.balls)),
                "target_answer": int(sampled_scene.target_answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "balls": ball_trace,
                "pockets": [
                    {
                        "pocket_id": str(pocket.pocket_id),
                        "display_name": str(pocket.display_name),
                        "center": [float(pocket.center[0]), float(pocket.center[1])],
                    }
                    for pocket in sampled_scene.pockets
                ],
                "cue_ball_id": str(sampled_scene.cue_ball_id),
                "marked_ball_id": sampled_scene.marked_ball_id,
                "marked_pocket_id": sampled_scene.marked_pocket_id,
                "current_player_group": sampled_scene.current_player_group,
                "pottable_ball_ids": [str(value) for value in sampled_scene.pottable_ball_ids],
                "legal_pottable_ball_ids": [str(value) for value in sampled_scene.legal_pottable_ball_ids],
                "blocking_ball_ids": [str(value) for value in sampled_scene.blocking_ball_ids],
                "evidence_ball_ids": [str(value) for value in sampled_scene.evidence_ball_ids],
                "evidence_pocket_ids": [str(value) for value in sampled_scene.evidence_pocket_ids],
                "evidence_entity_ids": [str(entity_id) for entity_id in evidence_entity_ids],
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in evidence_entity_ids],
            },
            "projected_evidence": {
                "bbox_set": [list(bbox) for bbox in evidence_bboxes],
            },
            "background": background_meta,
            "post_image_noise": post_noise_meta,
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id="pool",
            query_id=str(axes.query_id),
        )


@register_task
class GamesPoolQualifyingPottableCountTask(QuerySubsetTaskMixin, GamesPoolTableTask):
    """Count pottable balls matching one sampled direct-shot condition."""

    task_id = "task_games__pool__pottable_ball_count"
    supported_query_ids = (
        "pottable_ball_count",
        "legal_group_pottable_count",
    )


@register_task
class GamesPoolBlockingBallCountTask(FixedQueryVariantTaskMixin, GamesPoolTableTask):
    """Count balls blocking the marked direct shot lane."""

    task_id = "task_games__pool__blocking_ball_count"
    fixed_query_id = "blocking_ball_count"


__all__ = [
    "GamesPoolBlockingBallCountTask",
    "GamesPoolQualifyingPottableCountTask",
    "GamesPoolTableTask",
]
