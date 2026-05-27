"""Games Bowling tasks over lane trajectories and spare-path selection."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
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
from ...shared.support_sampling import resolve_integer_choice
from ..shared.bowling_common import (
    SUPPORTED_BOWLING_QUERY_IDS,
    SUPPORTED_BOWLING_SCENE_VARIANTS,
    SUPPORTED_BOWLING_STYLE_VARIANTS,
    BowlingPathOption,
    BowlingPin,
    BowlingSample,
    option_label,
    path_entity_id,
    pin_entity_id,
    validate_bowling_sample,
)
from ..shared.bowling_scene import BowlingRenderParams, render_bowling_scene
from ..shared.complexity import build_games_bowling_lane_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin
from ..shared.layout import resolve_games_layout_jitter
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_bowling_lane_base"
_PIN_LABELS: Tuple[str, ...] = tuple(chr(ord("A") + index) for index in range(10))
_SPARE_GROUPS: Tuple[Tuple[int, ...], ...] = (
    (9,),
    (8,),
    (7,),
    (5,),
    (6,),
    (5, 9),
    (6, 3),
    (4, 0),
    (8, 2),
    (7, 1),
)
_PIN_X_NORM: Tuple[float, ...] = (
    0.407,
    0.469,
    0.531,
    0.593,
    0.438,
    0.500,
    0.562,
    0.469,
    0.531,
    0.500,
)
_PIN_Y_NORM: Tuple[float, ...] = (
    0.145,
    0.145,
    0.145,
    0.145,
    0.205,
    0.205,
    0.205,
    0.265,
    0.265,
    0.325,
)
_BALL_Y_NORM = 0.875
_PATH_AIM_Y_NORM = 0.09
_LANE_WIDTH_FOR_HIT = 760.0
_LANE_HEIGHT_FOR_HIT = 660.0
_PIN_HIT_RADIUS_PX = 27.0
_PIN_VISUAL_CLEARANCE_RADIUS_PX = 44.0


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Bowling scenes."""

    visible_pin_count_support: Tuple[int, ...] = (4, 5, 6, 7, 8, 9)
    path_option_count_support: Tuple[int, ...] = (4, 5, 6)
    target_pin_index_support: Tuple[int, ...] = tuple(range(10))
    target_path_index_support: Tuple[int, ...] = tuple(range(6))
    canvas_width: int = 1000
    canvas_height: int = 740
    panel_margin_px: int = 36
    lane_width_px: int = 760
    lane_height_px: int = 660
    lane_border_width_px: int = 6
    pin_radius_px: int = 22
    ball_radius_px: int = 24
    path_width_px: int = 5
    label_font_size_px: int = 24


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Bowling instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    visible_pin_count: int
    path_option_count: int
    target_pin_index: int | None
    target_path_index: int | None
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    visible_pin_count_probabilities: Dict[str, float]
    path_option_count_probabilities: Dict[str, float]
    target_pin_index_probabilities: Dict[str, float] | None
    target_path_index_probabilities: Dict[str, float] | None


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "bowling")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="bowling", apply_prob=0.5)


def _resolve_query_id(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced Bowling query id."""

    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_BOWLING_QUERY_IDS,
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
    """Resolve one balanced named Bowling axis."""

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


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one Bowling instance."""

    query_id, query_id_probabilities = _resolve_query_id(instance_seed=int(instance_seed), params=params)
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_BOWLING_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_BOWLING_STYLE_VARIANTS,
    )
    path_option_count = 0
    path_option_count_probabilities = {"0": 1.0}
    visible_pin_count = 0
    visible_pin_count_probabilities = {"0": 1.0}

    target_pin_index: int | None = None
    target_pin_index_probabilities: Dict[str, float] | None = None
    target_path_index: int | None = None
    target_path_index_probabilities: Dict[str, float] | None = None
    if str(query_id) == "first_pin_hit_label":
        visible_pin_count, visible_pin_count_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="visible_pin_count_support",
            explicit_key="visible_pin_count",
            fallback_support=_DEFAULTS.visible_pin_count_support,
            namespace=f"{TASK_ID}.visible_pin_count",
            balanced_flag_key="balanced_visible_pin_count_sampling",
            namespace_support_permutation=True,
        )
        target_pin_index, target_pin_index_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="target_pin_index_support",
            explicit_key="target_pin_index",
            fallback_support=_DEFAULTS.target_pin_index_support,
            namespace=f"{TASK_ID}.target_pin_index",
            balanced_flag_key="balanced_target_pin_sampling",
            namespace_support_permutation=True,
        )
    if str(query_id) == "spare_path_label":
        path_option_count, path_option_count_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="path_option_count_support",
            explicit_key="path_option_count",
            fallback_support=_DEFAULTS.path_option_count_support,
            namespace=f"{TASK_ID}.path_option_count",
            balanced_flag_key="balanced_path_option_count_sampling",
            namespace_support_permutation=True,
        )
        target_path_index, target_path_index_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="target_path_index_support",
            explicit_key="target_path_index",
            fallback_support=_DEFAULTS.target_path_index_support,
            namespace=f"{TASK_ID}.target_path_index",
            balanced_flag_key="balanced_target_path_sampling",
            namespace_support_permutation=True,
        )
        path_option_count = max(int(path_option_count), int(target_path_index) + 1)
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        visible_pin_count=int(visible_pin_count),
        path_option_count=int(path_option_count),
        target_pin_index=None if target_pin_index is None else int(target_pin_index),
        target_path_index=None if target_path_index is None else int(target_path_index),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        visible_pin_count_probabilities=dict(visible_pin_count_probabilities),
        path_option_count_probabilities=dict(path_option_count_probabilities),
        target_pin_index_probabilities=None if target_pin_index_probabilities is None else dict(target_pin_index_probabilities),
        target_path_index_probabilities=None if target_path_index_probabilities is None else dict(target_path_index_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> BowlingRenderParams:
    """Resolve Bowling rendering parameters from config/defaults."""

    return BowlingRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        lane_width_px=int(params.get("lane_width_px", group_default(_RENDER_DEFAULTS, "lane_width_px", _DEFAULTS.lane_width_px))),
        lane_height_px=int(params.get("lane_height_px", group_default(_RENDER_DEFAULTS, "lane_height_px", _DEFAULTS.lane_height_px))),
        lane_border_width_px=int(params.get("lane_border_width_px", group_default(_RENDER_DEFAULTS, "lane_border_width_px", _DEFAULTS.lane_border_width_px))),
        pin_radius_px=int(params.get("pin_radius_px", group_default(_RENDER_DEFAULTS, "pin_radius_px", _DEFAULTS.pin_radius_px))),
        ball_radius_px=int(params.get("ball_radius_px", group_default(_RENDER_DEFAULTS, "ball_radius_px", _DEFAULTS.ball_radius_px))),
        path_width_px=int(params.get("path_width_px", group_default(_RENDER_DEFAULTS, "path_width_px", _DEFAULTS.path_width_px))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px))),
        layout_jitter_meta=resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.bowling.layout",
        ),
    )


def _pin_row_col(rack_index: int) -> Tuple[int, int]:
    """Return row/column within the visible rack for a 0-based rack index."""

    remaining = int(rack_index)
    for row, count in enumerate((4, 3, 2, 1)):
        if remaining < count:
            return int(row), int(remaining)
        remaining -= count
    raise ValueError(f"unsupported rack_index: {rack_index}")


def _jitter_pin_positions(*, rng: Any) -> Dict[int, Tuple[float, float]]:
    """Return mildly haphazard visible pin positions in lane-normalized coordinates."""

    positions: Dict[int, Tuple[float, float]] = {}
    for rack_index, (base_x, base_y) in enumerate(zip(_PIN_X_NORM, _PIN_Y_NORM)):
        x = float(base_x + rng.uniform(-0.014, 0.014))
        y = float(base_y + rng.uniform(-0.012, 0.012))
        positions[int(rack_index)] = (max(0.34, min(0.66, x)), max(0.105, min(0.355, y)))
    return positions


def _pins_with_labels(
    *,
    target_label: str,
    target_rack_index: int,
    rng: Any,
) -> Tuple[str, ...]:
    """Assign labels haphazardly while keeping the requested answer label on the hit pin."""

    labels = [str(label) for label in _PIN_LABELS if str(label) != str(target_label)]
    rng.shuffle(labels)
    assigned: list[str] = []
    for rack_index in range(10):
        if int(rack_index) == int(target_rack_index):
            assigned.append(str(target_label))
        else:
            assigned.append(str(labels.pop()))
    return tuple(assigned)


def _make_pins(
    *,
    standing_ids: set[int] | None = None,
    include_ids: set[int] | None = None,
    positions_norm: Mapping[int, Tuple[float, float]] | None = None,
    labels: Sequence[str] | None = None,
) -> Tuple[BowlingPin, ...]:
    """Create visible labeled bowling pins."""

    include = set(range(10)) if include_ids is None else {int(value) for value in include_ids}
    standing = set(include) if standing_ids is None else ({int(value) for value in standing_ids} & set(include))
    label_values = tuple(str(label) for label in (labels if labels is not None else _PIN_LABELS))
    if len(label_values) != 10:
        raise ValueError("Bowling label assignment must contain exactly 10 labels")
    pins: list[BowlingPin] = []
    for rack_index in sorted(include):
        row, col = _pin_row_col(rack_index)
        pos = None if positions_norm is None else positions_norm.get(int(rack_index))
        pins.append(
            BowlingPin(
                pin_id=pin_entity_id(rack_index),
                label=label_values[rack_index],
                rack_index=int(rack_index),
                row=int(row),
                col=int(col),
                color_index=int(rack_index % 5),
                standing=int(rack_index) in standing,
                x_norm=None if pos is None else float(pos[0]),
                y_norm=None if pos is None else float(pos[1]),
            )
        )
    return tuple(pins)


def _first_intersected_pin_id(
    *,
    pins: Sequence[BowlingPin],
    ball_x_norm: float,
    aim_x_norm: float,
    aim_y_norm: float,
) -> str | None:
    """Return the first standing pin intersected by the ball ray."""

    sx = float(ball_x_norm) * _LANE_WIDTH_FOR_HIT
    sy = _BALL_Y_NORM * _LANE_HEIGHT_FOR_HIT
    ex = float(aim_x_norm) * _LANE_WIDTH_FOR_HIT
    ey = float(aim_y_norm) * _LANE_HEIGHT_FOR_HIT
    dx = ex - sx
    dy = ey - sy
    length_sq = (dx * dx) + (dy * dy)
    if length_sq <= 1e-6:
        return None
    length = math.sqrt(length_sq)
    best: tuple[float, str] | None = None
    for pin in pins:
        if not bool(pin.standing) or pin.x_norm is None or pin.y_norm is None:
            continue
        px = float(pin.x_norm) * _LANE_WIDTH_FOR_HIT
        py = float(pin.y_norm) * _LANE_HEIGHT_FOR_HIT
        t = (((px - sx) * dx) + ((py - sy) * dy)) / length_sq
        if t < 0.0 or t > 1.06:
            continue
        closest_x = sx + (t * dx)
        closest_y = sy + (t * dy)
        distance = math.hypot(px - closest_x, py - closest_y)
        if distance > _PIN_HIT_RADIUS_PX:
            continue
        entry_offset = math.sqrt(max(0.0, (_PIN_HIT_RADIUS_PX * _PIN_HIT_RADIUS_PX) - (distance * distance))) / length
        entry_t = float(t - entry_offset)
        if best is None or entry_t < best[0]:
            best = (entry_t, str(pin.pin_id))
    return None if best is None else str(best[1])


def _non_target_path_clearance_px(
    *,
    pins: Sequence[BowlingPin],
    target_pin_id: str,
    ball_x_norm: float,
    aim_x_norm: float,
    aim_y_norm: float,
) -> float | None:
    """Return the closest non-target pin distance to the target ray in lane pixels."""

    sx = float(ball_x_norm) * _LANE_WIDTH_FOR_HIT
    sy = _BALL_Y_NORM * _LANE_HEIGHT_FOR_HIT
    ex = float(aim_x_norm) * _LANE_WIDTH_FOR_HIT
    ey = float(aim_y_norm) * _LANE_HEIGHT_FOR_HIT
    dx = ex - sx
    dy = ey - sy
    length_sq = (dx * dx) + (dy * dy)
    if length_sq <= 1e-6:
        return None

    nearest: float | None = None
    for pin in pins:
        if str(pin.pin_id) == str(target_pin_id) or not bool(pin.standing) or pin.x_norm is None or pin.y_norm is None:
            continue
        px = float(pin.x_norm) * _LANE_WIDTH_FOR_HIT
        py = float(pin.y_norm) * _LANE_HEIGHT_FOR_HIT
        t = (((px - sx) * dx) + ((py - sy) * dy)) / length_sq
        if t < -0.02 or t > 1.04:
            continue
        closest_x = sx + (t * dx)
        closest_y = sy + (t * dy)
        distance = math.hypot(px - closest_x, py - closest_y)
        nearest = float(distance) if nearest is None else min(float(nearest), float(distance))
    return nearest


def _sample_first_pin_hit(*, rng: Any, axes: _ResolvedAxes) -> BowlingSample:
    """Construct a scene where the shown path first reaches one pin."""

    target_label = str(_PIN_LABELS[int(axes.target_pin_index or 0)])
    for _layout_attempt in range(96):
        positions = _jitter_pin_positions(rng=rng)
        target_rack_indices = list(range(10))
        rng.shuffle(target_rack_indices)
        ball_candidates = [0.26, 0.30, 0.34, 0.38, 0.42, 0.46, 0.50, 0.54, 0.58, 0.62, 0.66, 0.70, 0.74]
        ball_candidates.extend(float(rng.uniform(0.24, 0.76)) for _ in range(18))
        rng.shuffle(ball_candidates)
        for target_rack_index in target_rack_indices:
            label_order = _pins_with_labels(
                target_label=target_label,
                target_rack_index=int(target_rack_index),
                rng=rng,
            )
            visible_ids = {int(target_rack_index)}
            other_rack_indices = [int(index) for index in range(10) if int(index) != int(target_rack_index)]
            rng.shuffle(other_rack_indices)
            visible_ids.update(other_rack_indices[: max(0, int(axes.visible_pin_count) - 1)])
            pins = _make_pins(
                positions_norm=positions,
                labels=label_order,
                include_ids=visible_ids,
                standing_ids=visible_ids,
            )
            target_pin = next(pin for pin in pins if int(pin.rack_index) == int(target_rack_index))
            if target_pin.x_norm is None or target_pin.y_norm is None:
                continue
            for ball_x in ball_candidates:
                first_pin_id = _first_intersected_pin_id(
                    pins=pins,
                    ball_x_norm=float(ball_x),
                    aim_x_norm=float(target_pin.x_norm),
                    aim_y_norm=float(target_pin.y_norm),
                )
                if str(first_pin_id) != str(target_pin.pin_id):
                    continue
                clearance_px = _non_target_path_clearance_px(
                    pins=pins,
                    target_pin_id=str(target_pin.pin_id),
                    ball_x_norm=float(ball_x),
                    aim_x_norm=float(target_pin.x_norm),
                    aim_y_norm=float(target_pin.y_norm),
                )
                if clearance_px is not None and float(clearance_px) < _PIN_VISUAL_CLEARANCE_RADIUS_PX:
                    continue
                sample = BowlingSample(
                    query_id=str(axes.query_id),
                    scene_variant=str(axes.scene_variant),
                    style_variant=str(axes.style_variant),
                    answer=str(target_pin.label),
                    pins=pins,
                    path_options=tuple(),
                    ball_x_norm=float(ball_x),
                    target_pin_id=str(target_pin.pin_id),
                    target_pin_label=str(target_pin.label),
                    target_path_id=None,
                    target_path_label=None,
                    remaining_pin_ids=tuple(pin.pin_id for pin in pins if bool(pin.standing)),
                    evidence_entity_ids=(str(target_pin.pin_id),),
                    construction_mode="verified_first_collision_path",
                    path_visible_fraction=None,
                    path_clearance_px=None if clearance_px is None else float(clearance_px),
                )
                validate_bowling_sample(sample)
                return sample
    raise ValueError("failed to construct a first-pin Bowling path with unique first contact")


def _make_path_options(*, rng: Any, option_count: int, target_index: int, target_aim_x: float) -> Tuple[BowlingPathOption, ...]:
    """Create labeled aiming paths with one target option."""

    candidate_offsets = [-0.29, -0.24, -0.19, -0.14, -0.095, 0.095, 0.14, 0.19, 0.24, 0.29]
    candidate_positions: list[float] = []
    for offset in candidate_offsets:
        candidate = max(0.28, min(0.72, float(target_aim_x + offset)))
        if abs(candidate - float(target_aim_x)) < 0.055:
            continue
        if all(abs(candidate - other) >= 0.045 for other in candidate_positions):
            candidate_positions.append(float(candidate))
    for candidate in (0.28, 0.34, 0.40, 0.46, 0.54, 0.60, 0.66, 0.72):
        if abs(float(candidate) - float(target_aim_x)) < 0.055:
            continue
        if all(abs(float(candidate) - other) >= 0.045 for other in candidate_positions):
            candidate_positions.append(float(candidate))
    rng.shuffle(candidate_positions)

    aim_values: list[float] = []
    for index in range(int(option_count)):
        if int(index) == int(target_index):
            aim_values.append(float(target_aim_x))
            continue
        if not candidate_positions:
            raise ValueError("not enough distinct Bowling path aim positions")
        aim_values.append(float(candidate_positions.pop()))
    return tuple(
        BowlingPathOption(
            path_id=path_entity_id(index),
            label=option_label(index),
            aim_x_norm=float(aim_values[index]),
            color_index=int(index),
        )
        for index in range(int(option_count))
    )


def _sample_spare_path(*, rng: Any, axes: _ResolvedAxes) -> BowlingSample:
    """Construct a scene where one labeled path covers all standing spare pins."""

    option_count = int(axes.path_option_count)
    target_path_index = int(axes.target_path_index or 0)
    group = tuple(int(value) for value in _SPARE_GROUPS[int(rng.randrange(len(_SPARE_GROUPS)))])
    target_aim_x = float(rng.uniform(0.36, 0.64))
    positions = _jitter_pin_positions(rng=rng)
    line_t_values = [0.79, 0.86]
    perpendicular_jitter = float(rng.uniform(-0.004, 0.004))
    for group_index, pin_index in enumerate(group):
        t = float(line_t_values[min(group_index, len(line_t_values) - 1)])
        x = float(0.50 + (t * (target_aim_x - 0.50)) + perpendicular_jitter)
        y = float(_BALL_Y_NORM + (t * (_PATH_AIM_Y_NORM - _BALL_Y_NORM)))
        positions[int(pin_index)] = (max(0.34, min(0.66, x)), max(0.115, min(0.36, y)))
    path_options = _make_path_options(
        rng=rng,
        option_count=option_count,
        target_index=target_path_index,
        target_aim_x=float(target_aim_x),
    )
    target_path = path_options[int(target_path_index)]
    sample = BowlingSample(
        query_id=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        answer=str(target_path.label),
        pins=_make_pins(standing_ids=set(group), include_ids=set(group), positions_norm=positions),
        path_options=path_options,
        ball_x_norm=0.50,
        target_pin_id=None,
        target_pin_label=None,
        target_path_id=str(target_path.path_id),
        target_path_label=str(target_path.label),
        remaining_pin_ids=tuple(pin_entity_id(index) for index in group),
        evidence_entity_ids=(str(target_path.path_id),),
        construction_mode="unique_path_through_remaining_pins",
        path_visible_fraction=float(rng.uniform(0.42, 0.56)),
        path_clearance_px=None,
    )
    validate_bowling_sample(sample)
    return sample


def _sample_scene(*, rng: Any, axes: _ResolvedAxes) -> BowlingSample:
    """Construct one Bowling scene for the requested query."""

    query = str(axes.query_id)
    if query == "first_pin_hit_label":
        return _sample_first_pin_hit(rng=rng, axes=axes)
    if query == "spare_path_label":
        return _sample_spare_path(rng=rng, axes=axes)
    raise ValueError(f"unsupported Bowling query_id: {query}")


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Bowling JSON output."""

    if str(query_id) == "spare_path_label":
        answer_value = "4"
        evidence_value = [[624, 642, 660, 678]]
    else:
        answer_value = "G"
        evidence_value = [[510, 164, 554, 224]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesBowlingLaneTask:
    """Return one grounded query over a Bowling lane scene."""

    task_id = TASK_ID
    domain = "games"
    task_group = "bowling"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: BowlingSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

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
            namespace="games.bowling_lane.panel_scene_style",
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
        rendered_scene = render_bowling_scene(
            pins=sampled_scene.pins,
            path_options=sampled_scene.path_options,
            query_id=str(sampled_scene.query_id),
            ball_x_norm=float(sampled_scene.ball_x_norm),
            target_pin_id=sampled_scene.target_pin_id,
            target_path_id=sampled_scene.target_path_id,
            path_visible_fraction=sampled_scene.path_visible_fraction,
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
            panel_style=panel_style,
        )
        evidence_bboxes = [
            list(rendered_scene.render_map["entity_bboxes_px"][str(entity_id)])
            for entity_id in sampled_scene.evidence_entity_ids
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
                "object_description_lane_rack",
                "bowling_motion_rule_text",
                "spare_path_rule_text",
                "answer_hint_first_pin_hit_label",
                "evidence_hint_first_pin_hit_label",
                "answer_hint_spare_path_label",
                "evidence_hint_spare_path_label",
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
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "bowling_motion_rule_text": str(prompt_defaults["bowling_motion_rule_text"]),
                "spare_path_rule_text": str(prompt_defaults["spare_path_rule_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="string", value=str(sampled_scene.answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        standing_pin_count = sum(1 for pin in sampled_scene.pins if bool(pin.standing))
        complexity = build_games_bowling_lane_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            standing_pin_count=int(standing_pin_count),
            path_option_count=len(sampled_scene.path_options),
            evidence_count=len(sampled_scene.evidence_entity_ids),
        )
        pin_trace = [
            {
                "pin_id": str(pin.pin_id),
                "label": str(pin.label),
                "rack_index": int(pin.rack_index),
                "row": int(pin.row),
                "col": int(pin.col),
                "standing": bool(pin.standing),
                "x_norm": None if pin.x_norm is None else float(pin.x_norm),
                "y_norm": None if pin.y_norm is None else float(pin.y_norm),
            }
            for pin in sampled_scene.pins
        ]
        path_trace = [
            {
                "path_id": str(path.path_id),
                "label": str(path.label),
                "aim_x_norm": float(path.aim_x_norm),
            }
            for path in sampled_scene.path_options
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_bowling_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "standing_pin_count": int(standing_pin_count),
                    "path_option_count": len(sampled_scene.path_options),
                    "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
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
                    "visible_pin_count": len(sampled_scene.pins),
                    "path_option_count": len(sampled_scene.path_options),
                    "target_pin_index": axes.target_pin_index,
                    "target_pin_label_index": axes.target_pin_index,
                    "target_path_index": axes.target_path_index,
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "visible_pin_count_probabilities": dict(axes.visible_pin_count_probabilities),
                    "path_option_count_probabilities": dict(axes.path_option_count_probabilities),
                    "target_pin_index_probabilities": None if axes.target_pin_index_probabilities is None else dict(axes.target_pin_index_probabilities),
                    "target_path_index_probabilities": None if axes.target_path_index_probabilities is None else dict(axes.target_path_index_probabilities),
                    "target_pin_id": sampled_scene.target_pin_id,
                    "target_pin_label": sampled_scene.target_pin_label,
                    "target_path_id": sampled_scene.target_path_id,
                    "target_path_label": sampled_scene.target_path_label,
                    "path_visible_fraction": sampled_scene.path_visible_fraction,
                    "path_clearance_px": sampled_scene.path_clearance_px,
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "visible_pin_count": len(sampled_scene.pins),
                "pins": pin_trace,
                "path_options": path_trace,
                "ball_x_norm": float(sampled_scene.ball_x_norm),
                "target_pin_id": sampled_scene.target_pin_id,
                "target_pin_label": sampled_scene.target_pin_label,
                "target_path_id": sampled_scene.target_path_id,
                "target_path_label": sampled_scene.target_path_label,
                "path_visible_fraction": sampled_scene.path_visible_fraction,
                "path_clearance_px": sampled_scene.path_clearance_px,
                "remaining_pin_ids": [str(entity_id) for entity_id in sampled_scene.remaining_pin_ids],
                "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
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
            scene_id="bowling",
            query_id=str(axes.query_id),
        )


@register_task
class GamesBowlingFirstPinHitLabelTask(FixedQueryVariantTaskMixin, GamesBowlingLaneTask):
    """Identify the labeled pin hit first by the visible ball path."""

    task_id = "task_games__bowling__first_pin_hit_label"
    fixed_query_id = "first_pin_hit_label"


@register_task
class GamesBowlingSparePathLabelTask(FixedQueryVariantTaskMixin, GamesBowlingLaneTask):
    """Identify the labeled path that picks up the visible spare."""

    task_id = "task_games__bowling__spare_path_label"
    fixed_query_id = "spare_path_label"


__all__ = [
    "GamesBowlingFirstPinHitLabelTask",
    "GamesBowlingLaneTask",
    "GamesBowlingSparePathLabelTask",
]
