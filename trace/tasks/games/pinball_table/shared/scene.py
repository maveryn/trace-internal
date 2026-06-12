"""Scene-local primitives for pinball-table games tasks."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.shared.config_defaults import group_default, required_group_defaults
from trace.tasks.shared.font_assets import get_font_family_record, sample_font_family
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from trace.tasks.shared.support_sampling import resolve_integer_choice
from .common import (
    SUPPORTED_PINBALL_OBJECT_KINDS,
    SUPPORTED_PINBALL_SCENE_VARIANTS,
    SUPPORTED_PINBALL_STYLE_VARIANTS,
    PinballObject,
    PinballSample,
    pinball_object_id,
    validate_pinball_sample,
)
from .rendering import PinballRenderParams, render_pinball_scene
from trace.tasks.games.shared.layout import resolve_games_layout_jitter
from trace.tasks.games.shared.sampling import resolve_games_named_axis
from trace.tasks.games.shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults


SCENE_ID = "pinball_table"
FIRST_HIT_QUERY_ID = "first_hit_object_label"
PATH_SCORE_QUERY_ID = "path_score_value"
_OBJECT_LABELS: Tuple[str, ...] = tuple(chr(ord("A") + index) for index in range(8))
_PATH_SCORE_SHAPES: Tuple[str, ...] = ("one_ricochet", "two_ricochet", "target_revisit")
_PATH_SCORE_VALUES: Tuple[int, ...] = (10, 20, 30, 50)
_PATH_HIT_COUNT_SUPPORT: Tuple[int, ...] = (2, 3, 4)
_BUMPER_RADIUS_NORM = 0.045
_STANDUP_RADIUS_NORM = 0.034
_DROP_TARGET_WIDTH_NORM = 0.092
_DROP_TARGET_HEIGHT_NORM = 0.060
_ROLLOVER_WIDTH_NORM = 0.135
_ROLLOVER_HEIGHT_NORM = 0.038


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for pinball-table scenes."""

    object_count_support: Tuple[int, ...] = (5, 6, 7, 8)
    canvas_width: int = 900
    canvas_height: int = 760
    panel_margin_px: int = 28
    table_width_px: int = 700
    table_height_px: int = 680
    table_border_width_px: int = 7
    ball_radius_px: int = 17
    bumper_radius_px: int = 32
    target_width_px: int = 72
    target_height_px: int = 34
    cue_width_px: int = 6
    label_font_size_px: int = 26


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one pinball instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    object_count: int
    target_object_label: str
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    object_count_probabilities: Dict[str, float]
    target_object_label_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _ScorePathPlan:
    """Complete drawn scoring path plus any forced scoring events."""

    points: Tuple[Tuple[float, float], ...]
    forced_hit_events: Tuple[Tuple[float, Tuple[float, float]], ...] = ()


@dataclass(frozen=True)
class GeneratedComponents:
    """Prompt, answer, annotation, image, and trace payload for one pinball sample."""

    prompt: str
    prompt_variants: Dict[str, Any]
    answer_gt: TypedValue
    annotation_gt: TypedValue
    image: Image.Image
    trace_payload: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.5)


def _resolve_named_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    namespace_root: str,
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named pinball axis."""

    return resolve_games_named_axis(
        task_id=str(namespace_root),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=[str(value) for value in supported],
    )


def _resolve_target_label(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    namespace: str,
    object_count: int,
) -> Tuple[str, Dict[str, float]]:
    """Resolve a target label from the labels visible in the sampled scene."""

    support = tuple(_OBJECT_LABELS[: int(object_count)])
    explicit = params.get("target_object_label")
    probabilities = {str(label): 1.0 / float(len(support)) for label in support}
    if explicit is not None:
        value = str(explicit)
        if value not in support:
            raise ValueError(f"target_object_label={value!r} requires object_count >= {int(_OBJECT_LABELS.index(value) + 1) if value in _OBJECT_LABELS else '?'}")
        return value, {str(label): (1.0 if str(label) == value else 0.0) for label in support}
    balanced = bool(params.get("balanced_target_object_label_sampling", group_default(gen_defaults, "balanced_target_object_label_sampling", True)))
    if balanced and params.get("_sample_cursor") is not None:
        return str(support[abs(int(params["_sample_cursor"])) % len(support)]), probabilities
    rng = spawn_rng(int(instance_seed), str(namespace))
    return str(rng.choice(support)), probabilities


def resolve_axes(
    instance_seed: int,
    *,
    gen_defaults: Mapping[str, Any],
    namespace: str,
    params: Mapping[str, Any],
    query_id: str,
    query_id_probabilities: Mapping[str, float],
    resolve_target_label_axis: bool = True,
) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one pinball instance."""

    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_PINBALL_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_PINBALL_STYLE_VARIANTS,
    )
    object_count, object_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key="object_count_support",
        explicit_key="object_count",
        fallback_support=_DEFAULTS.object_count_support,
        namespace=f"{str(namespace)}.object_count",
        balanced_flag_key="balanced_object_count_sampling",
        namespace_support_permutation=True,
    )
    if bool(resolve_target_label_axis):
        target_object_label, target_object_label_probabilities = _resolve_target_label(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
            namespace=f"{str(namespace)}.target_object_label",
            object_count=int(object_count),
        )
    else:
        target_object_label = ""
        target_object_label_probabilities = {}
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        object_count=int(object_count),
        target_object_label=str(target_object_label),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        object_count_probabilities=dict(object_count_probabilities),
        target_object_label_probabilities=dict(target_object_label_probabilities),
    )


def _render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    namespace: str,
    instance_seed: int,
) -> PinballRenderParams:
    """Resolve pinball rendering parameters from config/defaults."""

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{str(namespace)}.font_family",
        params=params,
    )
    return PinballRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(render_defaults, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(render_defaults, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(render_defaults, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        table_width_px=int(params.get("table_width_px", group_default(render_defaults, "table_width_px", _DEFAULTS.table_width_px))),
        table_height_px=int(params.get("table_height_px", group_default(render_defaults, "table_height_px", _DEFAULTS.table_height_px))),
        table_border_width_px=int(params.get("table_border_width_px", group_default(render_defaults, "table_border_width_px", _DEFAULTS.table_border_width_px))),
        ball_radius_px=int(params.get("ball_radius_px", group_default(render_defaults, "ball_radius_px", _DEFAULTS.ball_radius_px))),
        bumper_radius_px=int(params.get("bumper_radius_px", group_default(render_defaults, "bumper_radius_px", _DEFAULTS.bumper_radius_px))),
        target_width_px=int(params.get("target_width_px", group_default(render_defaults, "target_width_px", _DEFAULTS.target_width_px))),
        target_height_px=int(params.get("target_height_px", group_default(render_defaults, "target_height_px", _DEFAULTS.target_height_px))),
        cue_width_px=int(params.get("cue_width_px", group_default(render_defaults, "cue_width_px", _DEFAULTS.cue_width_px))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(render_defaults, "label_font_size_px", _DEFAULTS.label_font_size_px))),
        font_family=str(font_family),
        layout_jitter_meta=resolve_games_layout_jitter(
            params,
            render_defaults,
            instance_seed=int(instance_seed),
            namespace=f"{str(namespace)}.layout",
        ),
    )


def _unit_from_angle(angle_rad: float) -> Tuple[float, float]:
    """Return a unit vector for an angle in normalized table coordinates."""

    return (math.cos(float(angle_rad)), math.sin(float(angle_rad)))


def _distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Return Euclidean distance between two normalized table points."""

    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def _distance_to_segment(
    point: Tuple[float, float],
    a: Tuple[float, float],
    b: Tuple[float, float],
) -> float:
    """Return point distance to one line segment."""

    px, py = float(point[0]), float(point[1])
    ax, ay = float(a[0]), float(a[1])
    bx, by = float(b[0]), float(b[1])
    vx, vy = bx - ax, by - ay
    denom = (vx * vx) + (vy * vy)
    if denom <= 1e-9:
        return _distance(point, a)
    t = max(0.0, min(1.0, (((px - ax) * vx) + ((py - ay) * vy)) / denom))
    closest = (ax + (t * vx), ay + (t * vy))
    return _distance(point, closest)


def _distance_to_polyline(point: Tuple[float, float], path: Sequence[Tuple[float, float]]) -> float:
    """Return the minimum distance from a point to a normalized polyline."""

    if len(path) < 2:
        return 1.0e9
    return min(
        _distance_to_segment(point, path[index], path[index + 1])
        for index in range(len(path) - 1)
    )


def _polyline_lengths(path: Sequence[Tuple[float, float]]) -> Tuple[float, Tuple[float, ...]]:
    """Return total polyline length and per-segment lengths."""

    lengths = tuple(
        _distance(path[index], path[index + 1])
        for index in range(max(0, len(path) - 1))
    )
    return float(sum(lengths)), lengths


def _path_distance_at_vertex(path: Sequence[Tuple[float, float]], vertex_index: int) -> float:
    """Return arclength distance from the path start to one vertex."""

    index_limit = max(0, min(int(vertex_index), len(path) - 1))
    if index_limit <= 0:
        return 0.0
    return float(
        sum(
            _distance(path[index], path[index + 1])
            for index in range(index_limit)
        )
    )


def _turn_angle_degrees(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
) -> float:
    """Return the direction-change angle at ``b`` in degrees."""

    v1 = (float(b[0]) - float(a[0]), float(b[1]) - float(a[1]))
    v2 = (float(c[0]) - float(b[0]), float(c[1]) - float(b[1]))
    len1 = math.hypot(float(v1[0]), float(v1[1]))
    len2 = math.hypot(float(v2[0]), float(v2[1]))
    if len1 <= 1e-9 or len2 <= 1e-9:
        return 0.0
    dot = ((float(v1[0]) * float(v2[0])) + (float(v1[1]) * float(v2[1]))) / (len1 * len2)
    dot = max(-1.0, min(1.0, float(dot)))
    return float(math.degrees(math.acos(dot)))


def _has_clean_pinball_turns(path: Sequence[Tuple[float, float]]) -> bool:
    """Return whether turns are visually clear rather than shallow zig-zags."""

    if len(path) < 4:
        return False
    angles = [
        _turn_angle_degrees(path[index - 1], path[index], path[index + 1])
        for index in range(1, len(path) - 1)
    ]
    return bool(angles) and all(52.0 <= float(angle) <= 158.0 for angle in angles)


def _point_at_polyline_distance(path: Sequence[Tuple[float, float]], distance: float) -> Tuple[float, float]:
    """Return one point at arclength distance along a normalized polyline."""

    remaining = max(0.0, float(distance))
    for index in range(max(0, len(path) - 1)):
        start = path[index]
        end = path[index + 1]
        segment_length = _distance(start, end)
        if float(segment_length) <= 1e-9:
            continue
        if float(remaining) <= float(segment_length):
            t = float(remaining / segment_length)
            return (
                float(start[0] + (t * (float(end[0]) - float(start[0])))),
                float(start[1] + (t * (float(end[1]) - float(start[1])))),
            )
        remaining -= float(segment_length)
    return (float(path[-1][0]), float(path[-1][1]))


def _ray_circle_intersection(
    *,
    origin: Tuple[float, float],
    direction: Tuple[float, float],
    center: Tuple[float, float],
    radius: float,
) -> float | None:
    """Return first positive ray/circle intersection distance."""

    ox, oy = float(origin[0]), float(origin[1])
    dx, dy = float(direction[0]), float(direction[1])
    cx, cy = float(center[0]), float(center[1])
    fx, fy = ox - cx, oy - cy
    a = (dx * dx) + (dy * dy)
    b = 2.0 * ((fx * dx) + (fy * dy))
    c = (fx * fx) + (fy * fy) - (float(radius) * float(radius))
    disc = (b * b) - (4.0 * a * c)
    if disc < 0.0 or a <= 1e-9:
        return None
    root = math.sqrt(disc)
    values = [(-b - root) / (2.0 * a), (-b + root) / (2.0 * a)]
    candidates = [float(t) for t in values if float(t) >= 1e-5]
    return None if not candidates else min(candidates)


def _ray_rect_intersection(
    *,
    origin: Tuple[float, float],
    direction: Tuple[float, float],
    center: Tuple[float, float],
    width: float,
    height: float,
) -> float | None:
    """Return first positive ray/axis-aligned-rectangle intersection distance."""

    ox, oy = float(origin[0]), float(origin[1])
    dx, dy = float(direction[0]), float(direction[1])
    cx, cy = float(center[0]), float(center[1])
    left = cx - float(width) / 2.0
    right = cx + float(width) / 2.0
    top = cy - float(height) / 2.0
    bottom = cy + float(height) / 2.0
    if abs(dx) <= 1e-9:
        if ox < left or ox > right:
            return None
        tx_min, tx_max = -1.0e9, 1.0e9
    else:
        tx1 = (left - ox) / dx
        tx2 = (right - ox) / dx
        tx_min, tx_max = min(tx1, tx2), max(tx1, tx2)
    if abs(dy) <= 1e-9:
        if oy < top or oy > bottom:
            return None
        ty_min, ty_max = -1.0e9, 1.0e9
    else:
        ty1 = (top - oy) / dy
        ty2 = (bottom - oy) / dy
        ty_min, ty_max = min(ty1, ty2), max(ty1, ty2)
    t_enter = max(float(tx_min), float(ty_min))
    t_exit = min(float(tx_max), float(ty_max))
    if t_exit < max(float(t_enter), 1e-5):
        return None
    return float(t_enter) if float(t_enter) >= 1e-5 else float(t_exit)


def _object_ray_intersection(
    *,
    origin: Tuple[float, float],
    direction: Tuple[float, float],
    obj: PinballObject,
) -> float | None:
    """Return first positive ray intersection distance for one pinball object."""

    center = (float(obj.x_norm), float(obj.y_norm))
    if str(obj.kind) in {"bumper", "standup_target"}:
        return _ray_circle_intersection(
            origin=origin,
            direction=direction,
            center=center,
            radius=float(obj.radius_norm),
        )
    return _ray_rect_intersection(
        origin=origin,
        direction=direction,
        center=center,
        width=float(obj.width_norm),
        height=float(obj.height_norm),
    )


def _first_hit_object_id(
    *,
    origin: Tuple[float, float],
    angle_rad: float,
    objects: Sequence[PinballObject],
) -> str | None:
    """Return the first object intersected by the launch ray."""

    direction = _unit_from_angle(float(angle_rad))
    hits: list[Tuple[float, str]] = []
    for obj in objects:
        t = _object_ray_intersection(origin=origin, direction=direction, obj=obj)
        if t is not None:
            hits.append((float(t), str(obj.object_id)))
    if not hits:
        return None
    hits.sort(key=lambda item: item[0])
    if len(hits) >= 2 and abs(float(hits[1][0]) - float(hits[0][0])) < 0.035:
        return None
    return str(hits[0][1])


def _safe_object_position(
    *,
    rng: Any,
    kind: str,
    existing: Sequence[PinballObject],
    ball: Tuple[float, float],
    target: Tuple[float, float],
    path: Tuple[Tuple[float, float], Tuple[float, float]],
) -> Tuple[float, float] | None:
    """Sample one distractor position away from key points and the first-hit path."""

    for _ in range(180):
        x, y = _sample_zone_position(rng=rng, kind=str(kind))
        point = (x, y)
        if _distance(point, ball) < 0.18 or _distance(point, target) < 0.16:
            continue
        if any(_distance(point, (float(obj.x_norm), float(obj.y_norm))) < 0.14 for obj in existing):
            continue
        if _distance_to_segment(point, path[0], path[1]) < 0.095:
            continue
        return point
    return None


def _kind_for_target_center(*, y_norm: float, rng: Any) -> str:
    """Choose an answer-object kind that fits the target's playfield zone."""

    y = float(y_norm)
    if y < 0.30:
        return str(rng.choice(("drop_target", "rollover_lane")))
    if y < 0.58:
        return str(rng.choice(("bumper", "bumper", "standup_target")))
    return str(rng.choice(("standup_target", "drop_target")))


def _sample_zone_position(*, rng: Any, kind: str) -> Tuple[float, float]:
    """Sample a plausible normalized playfield zone for one object kind."""

    kind_value = str(kind)
    if kind_value == "bumper":
        return (float(rng.uniform(0.27, 0.73)), float(rng.uniform(0.30, 0.56)))
    if kind_value == "rollover_lane":
        return (float(rng.uniform(0.22, 0.78)), float(rng.uniform(0.14, 0.32)))
    if kind_value == "drop_target":
        if float(rng.random()) < 0.64:
            return (float(rng.uniform(0.20, 0.80)), float(rng.uniform(0.16, 0.36)))
        return (float(rng.choice((rng.uniform(0.14, 0.28), rng.uniform(0.72, 0.86)))), float(rng.uniform(0.42, 0.66)))
    return (float(rng.uniform(0.16, 0.84)), float(rng.uniform(0.34, 0.68)))


def _make_object(
    *,
    index: int,
    label: str,
    kind: str,
    center: Tuple[float, float],
    rng: Any,
    score_value: int | None = None,
) -> PinballObject:
    """Create one pinball object."""

    kind_value = str(kind)
    radius_norm = _BUMPER_RADIUS_NORM
    width_norm = _DROP_TARGET_WIDTH_NORM
    height_norm = _DROP_TARGET_HEIGHT_NORM
    if kind_value == "bumper":
        radius_norm = float(_BUMPER_RADIUS_NORM * float(rng.uniform(0.88, 1.12)))
        width_norm = float(_DROP_TARGET_WIDTH_NORM * float(rng.uniform(0.90, 1.12)))
        height_norm = float(_DROP_TARGET_HEIGHT_NORM * float(rng.uniform(0.90, 1.12)))
    elif kind_value == "standup_target":
        radius_norm = float(_STANDUP_RADIUS_NORM * float(rng.uniform(0.90, 1.10)))
        width_norm = float(_DROP_TARGET_WIDTH_NORM * float(rng.uniform(0.90, 1.12)))
        height_norm = float(_DROP_TARGET_HEIGHT_NORM * float(rng.uniform(0.90, 1.12)))
    elif kind_value == "rollover_lane":
        radius_norm = float(_STANDUP_RADIUS_NORM * float(rng.uniform(0.90, 1.10)))
        width_norm = float(_ROLLOVER_WIDTH_NORM * float(rng.uniform(0.90, 1.10)))
        height_norm = float(_ROLLOVER_HEIGHT_NORM * float(rng.uniform(0.90, 1.10)))
    else:
        radius_norm = float(_STANDUP_RADIUS_NORM * float(rng.uniform(0.90, 1.10)))
        width_norm = float(_DROP_TARGET_WIDTH_NORM * float(rng.uniform(0.90, 1.12)))
        height_norm = float(_DROP_TARGET_HEIGHT_NORM * float(rng.uniform(0.90, 1.12)))
    return PinballObject(
        object_id=pinball_object_id(index),
        label=str(label),
        kind=kind_value,
        x_norm=float(center[0]),
        y_norm=float(center[1]),
        radius_norm=float(radius_norm),
        width_norm=float(width_norm),
        height_norm=float(height_norm),
        color_index=int(index),
        score_value=None if score_value is None else int(score_value),
    )


def _objects_with_target_label(
    *,
    rng: Any,
    axes: _ResolvedAxes,
    ball: Tuple[float, float],
    target: Tuple[float, float],
    path: Tuple[Tuple[float, float], Tuple[float, float]],
) -> Tuple[PinballObject, ...] | None:
    """Create labeled objects with target label on the first-hit object."""

    labels = list(_OBJECT_LABELS[: int(axes.object_count)])
    rng.shuffle(labels)
    target_index = labels.index(str(axes.target_object_label))
    target_kind = _kind_for_target_center(y_norm=float(target[1]), rng=rng)
    kind_pool = list(SUPPORTED_PINBALL_OBJECT_KINDS)
    rng.shuffle(kind_pool)
    kind_plan: list[str] = []
    while len(kind_plan) < int(axes.object_count):
        shuffled = list(kind_pool)
        rng.shuffle(shuffled)
        kind_plan.extend(str(kind) for kind in shuffled)
    objects: list[PinballObject] = []
    for index, label in enumerate(labels):
        kind = str(target_kind if int(index) == int(target_index) else kind_plan[int(index)])
        if int(index) == int(target_index):
            center = target
        else:
            maybe = _safe_object_position(
                rng=rng,
                kind=kind,
                existing=objects,
                ball=ball,
                target=target,
                path=path,
            )
            if maybe is None:
                return None
            center = maybe
        objects.append(_make_object(index=index, label=str(label), kind=kind, center=center, rng=rng))
    return tuple(objects)


def _resolve_path_shape(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the visible trajectory shape for the score task."""

    return _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        namespace="path_shape",
        explicit_key="path_shape",
        weights_key="path_shape_weights",
        balance_flag_key="balanced_path_shape_sampling",
        supported=_PATH_SCORE_SHAPES,
    )


def _resolve_path_hit_count(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    object_count: int,
    gen_defaults: Mapping[str, Any],
    namespace: str,
) -> Tuple[int, Dict[str, float]]:
    """Resolve how many scored objects lie on the shown path."""

    support = tuple(value for value in _PATH_HIT_COUNT_SUPPORT if int(value) <= max(1, int(object_count) - 1))
    hit_count, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key="path_hit_count_support",
        explicit_key="path_hit_count",
        fallback_support=support or (2,),
        namespace=f"{str(namespace)}.path_hit_count",
        balanced_flag_key="balanced_path_hit_count_sampling",
        namespace_support_permutation=True,
    )
    if int(hit_count) >= int(object_count):
        raise ValueError("path_hit_count must be smaller than object_count")
    return int(hit_count), dict(probabilities)


def _sample_score_path(*, rng: Any, path_shape: str) -> _ScorePathPlan | None:
    """Sample one complete drawn pinball trajectory in normalized playfield coordinates."""

    shape = str(path_shape)
    for _attempt in range(180):
        start = (float(rng.uniform(0.40, 0.60)), float(rng.uniform(0.84, 0.89)))
        end = (float(rng.uniform(0.34, 0.66)), float(rng.uniform(0.91, 0.94)))
        forced_hit_events: Tuple[Tuple[float, Tuple[float, float]], ...] = ()
        if shape == "one_ricochet":
            first_side_left = bool(rng.randrange(2))
            side_bounce = (
                float(rng.uniform(0.09, 0.12) if first_side_left else rng.uniform(0.88, 0.91)),
                float(rng.uniform(0.42, 0.60)),
            )
            top_bounce = (
                float(rng.uniform(0.60, 0.80) if first_side_left else rng.uniform(0.20, 0.40)),
                float(rng.uniform(0.10, 0.15)),
            )
            path = (start, side_bounce, top_bounce, end)
        elif shape == "two_ricochet":
            first_side_left = bool(rng.randrange(2))
            side_bounce_1 = (
                float(rng.uniform(0.09, 0.12) if first_side_left else rng.uniform(0.88, 0.91)),
                float(rng.uniform(0.48, 0.64)),
            )
            top_bounce = (
                float(rng.uniform(0.32, 0.68)),
                float(rng.uniform(0.10, 0.15)),
            )
            side_bounce_2 = (
                float(rng.uniform(0.88, 0.91) if first_side_left else rng.uniform(0.09, 0.12)),
                float(rng.uniform(0.36, 0.54)),
            )
            path = (start, side_bounce_1, top_bounce, side_bounce_2, end)
        else:
            first_side_left = bool(rng.randrange(2))
            repeat_center = (float(rng.uniform(0.40, 0.60)), float(rng.uniform(0.36, 0.52)))
            top_bounce = (float(rng.uniform(0.20, 0.80)), float(rng.uniform(0.10, 0.16)))
            end_y = float(rng.uniform(0.91, 0.94))
            scale = (end_y - float(top_bounce[1])) / max(1e-6, float(repeat_center[1]) - float(top_bounce[1]))
            end_x = float(top_bounce[0]) + (scale * (float(repeat_center[0]) - float(top_bounce[0])))
            if not (0.30 <= end_x <= 0.70):
                continue
            if first_side_left:
                rail_bounce = (float(rng.uniform(0.09, 0.12)), float(rng.uniform(0.12, 0.30)))
            else:
                rail_bounce = (float(rng.uniform(0.88, 0.91)), float(rng.uniform(0.12, 0.30)))
            end = (float(end_x), float(end_y))
            path = (start, repeat_center, rail_bounce, top_bounce, end)
            distance_to_second_hit = (
                _path_distance_at_vertex(path, 3)
                + _distance(top_bounce, repeat_center)
            )
            forced_hit_events = (
                (_path_distance_at_vertex(path, 1), repeat_center),
                (float(distance_to_second_hit), repeat_center),
            )
        total_length, segment_lengths = _polyline_lengths(path)
        if float(total_length) < 0.86:
            continue
        if any(float(length) < 0.18 for length in segment_lengths):
            continue
        if len(path) - 1 not in {3, 4}:
            continue
        if float(path[-1][1]) < 0.90:
            continue
        if not _has_clean_pinball_turns(path):
            continue
        return _ScorePathPlan(
            points=tuple((float(x), float(y)) for x, y in path),
            forced_hit_events=tuple(
                (float(distance), (float(center[0]), float(center[1])))
                for distance, center in forced_hit_events
            ),
        )
    return None


def _sample_hit_centers_on_path(
    *,
    rng: Any,
    path: Tuple[Tuple[float, float], ...],
    hit_count: int,
    forced_hit_events: Sequence[Tuple[float, Tuple[float, float]]] = (),
) -> Tuple[Tuple[float, float], ...] | None:
    """Sample ordered scoring-hit centers along a visible trajectory."""

    total_length, _segment_lengths = _polyline_lengths(path)
    if float(total_length) <= 0.0:
        return None
    forced_events = tuple(
        (float(distance), (float(center[0]), float(center[1])))
        for distance, center in forced_hit_events
    )
    if len(forced_events) > int(hit_count):
        return None
    forced_centers = tuple(center for _distance_value, center in forced_events)
    for _attempt in range(120):
        sampled_distances: list[float] = []
        needed_count = int(hit_count) - len(forced_events)
        for _distance_attempt in range(180):
            if len(sampled_distances) >= needed_count:
                break
            candidate = float(rng.uniform(0.12 * total_length, 0.88 * total_length))
            if any(abs(float(candidate) - float(existing)) < 0.13 for existing in sampled_distances):
                continue
            if any(abs(float(candidate) - float(existing)) < 0.13 for existing, _center in forced_events):
                continue
            sampled_distances.append(candidate)
        if len(sampled_distances) < needed_count:
            continue
        distances = sorted(sampled_distances)
        sampled_centers = tuple(_point_at_polyline_distance(path, distance) for distance in distances)
        if any(not (0.13 <= float(x) <= 0.87 and 0.12 <= float(y) <= 0.77) for x, y in sampled_centers + forced_centers):
            continue
        unique_centers: list[Tuple[float, float]] = []
        valid = True
        for center in sampled_centers:
            if any(_distance(center, existing) < 0.13 for existing in unique_centers):
                valid = False
                break
            if any(_distance(center, forced) < 0.13 for forced in forced_centers):
                valid = False
                break
            unique_centers.append(center)
        if not valid:
            continue
        events = [(float(distance), center) for distance, center in zip(distances, sampled_centers)]
        events.extend((float(distance), center) for distance, center in forced_events)
        events.sort(key=lambda item: item[0])
        return tuple((float(center[0]), float(center[1])) for _distance_value, center in events)
    return None


def _safe_score_distractor_position(
    *,
    rng: Any,
    kind: str,
    existing: Sequence[PinballObject],
    ball: Tuple[float, float],
    path: Tuple[Tuple[float, float], ...],
) -> Tuple[float, float] | None:
    """Sample one scored-object distractor away from the shown trajectory."""

    for _attempt in range(220):
        point = _sample_zone_position(rng=rng, kind=str(kind))
        if _distance(point, ball) < 0.18:
            continue
        if any(_distance(point, (float(obj.x_norm), float(obj.y_norm))) < 0.14 for obj in existing):
            continue
        if _distance_to_polyline(point, path) < 0.12:
            continue
        return point
    return None


def _objects_for_path_score(
    *,
    rng: Any,
    axes: _ResolvedAxes,
    path: Tuple[Tuple[float, float], ...],
    hit_count: int,
    forced_hit_events: Sequence[Tuple[float, Tuple[float, float]]] = (),
) -> Tuple[Tuple[PinballObject, ...], Tuple[str, ...]] | None:
    """Create scored pinball objects and ordered scoring-hit annotation ids."""

    hit_centers = _sample_hit_centers_on_path(
        rng=rng,
        path=path,
        hit_count=int(hit_count),
        forced_hit_events=forced_hit_events,
    )
    if hit_centers is None:
        return None
    labels = list(_OBJECT_LABELS[: int(axes.object_count)])
    rng.shuffle(labels)
    kind_pool = list(SUPPORTED_PINBALL_OBJECT_KINDS)
    objects: list[PinballObject] = []
    annotation_ids: list[str] = []
    center_to_object_id: dict[Tuple[int, int], str] = {}
    for center in hit_centers:
        center_key = (int(round(float(center[0]) * 10000.0)), int(round(float(center[1]) * 10000.0)))
        existing_object_id = center_to_object_id.get(center_key)
        if existing_object_id is not None:
            annotation_ids.append(str(existing_object_id))
            continue
        index = len(objects)
        kind = _kind_for_target_center(y_norm=float(center[1]), rng=rng)
        score_value = int(rng.choice(_PATH_SCORE_VALUES))
        obj = _make_object(index=index, label=str(labels[index]), kind=kind, center=center, rng=rng, score_value=score_value)
        objects.append(obj)
        center_to_object_id[center_key] = str(obj.object_id)
        annotation_ids.append(str(obj.object_id))
    for index in range(len(objects), int(axes.object_count)):
        kind = str(kind_pool[int((index + rng.randrange(len(kind_pool))) % len(kind_pool))])
        center = _safe_score_distractor_position(
            rng=rng,
            kind=kind,
            existing=objects,
            ball=path[0],
            path=path,
        )
        if center is None:
            return None
        score_value = int(rng.choice(_PATH_SCORE_VALUES))
        objects.append(_make_object(index=index, label=str(labels[index]), kind=kind, center=center, rng=rng, score_value=score_value))
    return tuple(objects), tuple(annotation_ids)


def _sample_first_hit(*, rng: Any, axes: _ResolvedAxes) -> PinballSample:
    """Construct a pinball playfield where the launch cue first hits one labeled object."""

    for _attempt in range(180):
        ball = (float(rng.uniform(0.38, 0.62)), float(rng.uniform(0.82, 0.90)))
        angle = float(rng.uniform(-2.34, -0.80))
        direction = _unit_from_angle(angle)
        distance = float(rng.uniform(0.42, 0.66))
        target = (ball[0] + (direction[0] * distance), ball[1] + (direction[1] * distance))
        if not (0.16 <= target[0] <= 0.84 and 0.14 <= target[1] <= 0.70):
            continue
        path = (ball, target)
        objects = _objects_with_target_label(rng=rng, axes=axes, ball=ball, target=target, path=path)
        if objects is None:
            continue
        target_object = next(obj for obj in objects if str(obj.label) == str(axes.target_object_label))
        first_id = _first_hit_object_id(origin=ball, angle_rad=angle, objects=objects)
        if str(first_id) != str(target_object.object_id):
            continue
        sample = PinballSample(
            mode=str(axes.query_id),
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            answer=str(target_object.label),
            ball_x_norm=float(ball[0]),
            ball_y_norm=float(ball[1]),
            cue_angle_rad=float(angle),
            cue_visible_fraction=float(rng.uniform(0.34, 0.46)),
            objects=objects,
            target_object_id=str(target_object.object_id),
            target_object_label=str(target_object.label),
            annotation_entity_ids=(str(target_object.object_id),),
            construction_mode="unique_straight_launch_first_hit_projected_playfield",
            hidden_path_norm=tuple(path),
        )
        validate_pinball_sample(sample)
        return sample
    raise ValueError("failed to construct pinball first-hit scene")


def _sample_path_score(
    *,
    rng: Any,
    axes: _ResolvedAxes,
    path_shape: str,
    hit_count: int,
) -> PinballSample:
    """Construct a pinball playfield with a complete shown score trajectory."""

    for _attempt in range(240):
        path_plan = _sample_score_path(rng=rng, path_shape=str(path_shape))
        if path_plan is None:
            continue
        maybe_objects = _objects_for_path_score(
            rng=rng,
            axes=axes,
            path=path_plan.points,
            hit_count=int(hit_count),
            forced_hit_events=path_plan.forced_hit_events,
        )
        if maybe_objects is None:
            continue
        objects, annotation_ids = maybe_objects
        score_by_id = {str(obj.object_id): int(obj.score_value or 0) for obj in objects}
        answer_value = int(sum(int(score_by_id[str(entity_id)]) for entity_id in annotation_ids))
        if int(answer_value) <= 0:
            continue
        sample = PinballSample(
            mode=str(axes.query_id),
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            answer=str(int(answer_value)),
            ball_x_norm=float(path_plan.points[0][0]),
            ball_y_norm=float(path_plan.points[0][1]),
            cue_angle_rad=0.0,
            cue_visible_fraction=1.0,
            objects=objects,
            target_object_id="",
            target_object_label="",
            annotation_entity_ids=tuple(str(entity_id) for entity_id in annotation_ids),
            construction_mode=f"complete_{str(path_shape)}_path_score_sum",
            hidden_path_norm=tuple(path_plan.points),
        )
        validate_pinball_sample(sample)
        return sample
    raise ValueError("failed to construct pinball path-score scene")


def _build_prompt_json_examples(
    *,
    answer_value: str | int = "D",
    annotation_value: Sequence[Sequence[int]] = ((410, 260),),
) -> Tuple[str, str]:
    """Return deterministic prompt examples for pinball JSON output."""

    return (
        json.dumps({"annotation": [list(point) for point in annotation_value], "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


def resolve_score_path_axes(
    instance_seed: int,
    *,
    gen_defaults: Mapping[str, Any],
    namespace: str,
    params: Mapping[str, Any],
    object_count: int,
) -> Tuple[str, Dict[str, float], int, Dict[str, float]]:
    """Resolve score-path-only axes."""

    path_shape, path_shape_probabilities = _resolve_path_shape(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace=f"{str(namespace)}.path_shape",
    )
    path_hit_count, path_hit_count_probabilities = _resolve_path_hit_count(
        instance_seed=int(instance_seed),
        params=params,
        object_count=int(object_count),
        gen_defaults=gen_defaults,
        namespace=f"{str(namespace)}.path_hit_count",
    )
    return str(path_shape), dict(path_shape_probabilities), int(path_hit_count), dict(path_hit_count_probabilities)


def sample_scene(
    *,
    rng: Any,
    axes: _ResolvedAxes,
    path_shape: str = "",
    path_hit_count: int = 0,
) -> PinballSample:
    """Sample one pinball scene for a resolved objective contract."""

    if str(axes.query_id) == FIRST_HIT_QUERY_ID:
        return _sample_first_hit(rng=rng, axes=axes)
    if str(axes.query_id) == PATH_SCORE_QUERY_ID:
        if not path_shape or int(path_hit_count) <= 0:
            raise ValueError("path_score_value requires path_shape and path_hit_count")
        return _sample_path_score(
            rng=rng,
            axes=axes,
            path_shape=str(path_shape),
            hit_count=int(path_hit_count),
        )
    raise ValueError(f"unsupported pinball query_id: {axes.query_id}")


def _build_object_trace(sampled_scene: PinballSample) -> list[Dict[str, Any]]:
    """Build trace records for all labeled/scored pinball objects."""

    return [
        {
            "object_id": str(obj.object_id),
            "label": str(obj.label),
            "kind": str(obj.kind),
            "x_norm": float(obj.x_norm),
            "y_norm": float(obj.y_norm),
            "radius_norm": float(obj.radius_norm),
            "width_norm": float(obj.width_norm),
            "height_norm": float(obj.height_norm),
            "score_value": None if obj.score_value is None else int(obj.score_value),
            "display_text": str(int(obj.score_value)) if obj.score_value is not None else str(obj.label),
        }
        for obj in sampled_scene.objects
    ]


def build_components(
    *,
    sampled_scene: PinballSample,
    axes: _ResolvedAxes,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    namespace: str,
    path_shape: str = "",
    path_shape_probabilities: Mapping[str, float] | None = None,
    path_hit_count: int = 0,
    path_hit_count_probabilities: Mapping[str, float] | None = None,
) -> GeneratedComponents:
    """Render and package one sampled pinball scene without public task identity."""

    render_params = _render_params(
        params,
        render_defaults=render_defaults,
        namespace=str(namespace),
        instance_seed=int(instance_seed),
    )
    allowed_panel_treatments_raw = params.get(
        "panel_scene_treatments",
        group_default(render_defaults, "panel_scene_treatments", None),
    )
    if isinstance(allowed_panel_treatments_raw, str):
        allowed_panel_treatments = (str(allowed_panel_treatments_raw),)
    elif allowed_panel_treatments_raw is None:
        allowed_panel_treatments = None
    else:
        allowed_panel_treatments = tuple(str(item) for item in allowed_panel_treatments_raw)
    panel_style, panel_style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{str(namespace)}.panel_scene_style",
        treatments=allowed_panel_treatments,
        treatment_weights=params.get(
            "panel_scene_treatment_weights",
            group_default(render_defaults, "panel_scene_treatment_weights", None),
        ),
        palette_weights=params.get(
            "panel_scene_palette_weights",
            group_default(render_defaults, "panel_scene_palette_weights", None),
        ),
    )
    background, background_meta = make_panel_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=panel_style,
    )
    rendered_scene = render_pinball_scene(
        objects=sampled_scene.objects,
        ball_xy_norm=(float(sampled_scene.ball_x_norm), float(sampled_scene.ball_y_norm)),
        hidden_path_norm=sampled_scene.hidden_path_norm,
        cue_visible_fraction=float(sampled_scene.cue_visible_fraction),
        background=background,
        style_variant=str(axes.style_variant),
        params=render_params,
        panel_style=panel_style,
    )
    annotation_value = [
        list(rendered_scene.render_map["entity_points_px"][str(entity_id)])
        for entity_id in sampled_scene.annotation_entity_ids
    ]
    is_score_query = str(axes.query_id) == PATH_SCORE_QUERY_ID
    annotation_type = "point_sequence" if is_score_query else "point_set"
    projected_annotation = {
        "type": annotation_type,
        annotation_type: [list(point) for point in annotation_value],
        f"pixel_{annotation_type}": [list(point) for point in annotation_value],
    }
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )

    if is_score_query:
        required_prompt_keys = (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description_score_path",
            "pinball_score_rule_text",
            "answer_hint_path_score_value",
            "annotation_hint_path_score_value",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(
            answer_value=90,
            annotation_value=((310, 250), (420, 330), (520, 270)),
        )
        dynamic_slots = {
            "object_description": str(required_group_defaults(prompt_defaults, required_prompt_keys, context=f"prompt defaults for {SCENE_ID}.{axes.query_id}")["object_description_score_path"]),
            "pinball_score_rule_text": str(required_group_defaults(prompt_defaults, required_prompt_keys, context=f"prompt defaults for {SCENE_ID}.{axes.query_id}")["pinball_score_rule_text"]),
        }
    else:
        required_prompt_keys = (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description_schematic_table",
            "pinball_motion_rule_text",
            "answer_hint_first_hit_object_label",
            "annotation_hint_first_hit_object_label",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples()
        prompt_defaults_checked = required_group_defaults(
            prompt_defaults,
            required_prompt_keys,
            context=f"prompt defaults for {SCENE_ID}.{axes.query_id}",
        )
        dynamic_slots = {
            "object_description": str(prompt_defaults_checked[f"object_description_{str(axes.scene_variant)}"]),
            "pinball_motion_rule_text": str(prompt_defaults_checked["pinball_motion_rule_text"]),
        }

    prompt_defaults_checked = required_group_defaults(
        prompt_defaults,
        required_prompt_keys,
        context=f"prompt defaults for {SCENE_ID}.{axes.query_id}",
    )
    dynamic_slots.update(
        {
            "json_output_contract": str(prompt_defaults_checked["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults_checked["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults_checked[f"answer_hint_{str(axes.query_id)}"]),
            "annotation_hint": str(prompt_defaults_checked[f"annotation_hint_{str(axes.query_id)}"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        }
    )
    prompt_selection = render_scene_prompt_variants(
        domain="games",
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults_checked["bundle_id"]),
        scene_key=str(prompt_defaults_checked["scene_key"]),
        task_key=str(prompt_defaults_checked["task_key"]),
        query_key=str(axes.query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots=dynamic_slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer)) if is_score_query else TypedValue(type="string", value=str(sampled_scene.answer))
    annotation_gt = TypedValue(type=annotation_type, value=annotation_value)
    text_style_meta = {
        "font_family": str(render_params.font_family),
        "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
    }
    object_trace = _build_object_trace(sampled_scene)
    score_by_id = {str(obj.object_id): int(obj.score_value or 0) for obj in sampled_scene.objects}
    hit_score_values = [
        int(score_by_id[str(entity_id)])
        for entity_id in sampled_scene.annotation_entity_ids
    ] if is_score_query else []

    relations: Dict[str, Any] = {
        "scene_variant": str(axes.scene_variant),
        "query_id": str(axes.query_id),
        "style_variant": str(axes.style_variant),
        "object_count": len(sampled_scene.objects),
        "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
    }
    query_params: Dict[str, Any] = {
        "scene_variant": str(axes.scene_variant),
        "query_id": str(axes.query_id),
        "style_variant": str(axes.style_variant),
        "object_count": int(axes.object_count),
        "query_id_probabilities": dict(axes.query_id_probabilities),
        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
        "style_variant_probabilities": dict(axes.style_variant_probabilities),
        "object_count_probabilities": dict(axes.object_count_probabilities),
    }
    execution_trace: Dict[str, Any] = {
        "scene_variant": str(axes.scene_variant),
        "query_id": str(axes.query_id),
        "style_variant": str(axes.style_variant),
        "ball_xy_norm": [float(sampled_scene.ball_x_norm), float(sampled_scene.ball_y_norm)],
        "cue_angle_rad": float(sampled_scene.cue_angle_rad),
        "objects": object_trace,
        "cue_visible_fraction": float(sampled_scene.cue_visible_fraction),
        "hidden_path_norm": [[float(x), float(y)] for x, y in sampled_scene.hidden_path_norm],
        "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
        "construction_mode": str(sampled_scene.construction_mode),
    }
    witness_type = "object_sequence" if is_score_query else "object_set"
    if is_score_query:
        relations.update(
            {
                "path_shape": str(path_shape),
                "path_hit_count": int(path_hit_count),
                "score_total": int(sampled_scene.answer),
                "hit_score_values": list(hit_score_values),
            }
        )
        query_params.update(
            {
                "path_shape": str(path_shape),
                "path_hit_count": int(path_hit_count),
                "path_shape_probabilities": dict(path_shape_probabilities or {}),
                "path_hit_count_probabilities": dict(path_hit_count_probabilities or {}),
                "score_value_support": [int(value) for value in _PATH_SCORE_VALUES],
            }
        )
        execution_trace.update(
            {
                "path_shape": str(path_shape),
                "path_hit_count": int(path_hit_count),
                "path_shape_probabilities": dict(path_shape_probabilities or {}),
                "path_hit_count_probabilities": dict(path_hit_count_probabilities or {}),
                "score_value_support": [int(value) for value in _PATH_SCORE_VALUES],
                "score_total": int(sampled_scene.answer),
                "hit_score_values": list(hit_score_values),
                "repeated_hit_object_ids": sorted(
                    {
                        str(entity_id)
                        for entity_id in sampled_scene.annotation_entity_ids
                        if sampled_scene.annotation_entity_ids.count(str(entity_id)) > 1
                    }
                ),
            }
        )
    else:
        relations.update(
            {
                "target_object_id": str(sampled_scene.target_object_id),
                "target_object_label": str(sampled_scene.target_object_label),
            }
        )
        query_params.update(
            {
                "target_object_label": str(axes.target_object_label),
                "target_object_label_probabilities": dict(axes.target_object_label_probabilities),
                "target_object_id": str(sampled_scene.target_object_id),
                "cue_visible_fraction": float(sampled_scene.cue_visible_fraction),
            }
        )
        execution_trace.update(
            {
                "target_object_id": str(sampled_scene.target_object_id),
                "target_object_label": str(sampled_scene.target_object_label),
            }
        )

    trace_payload = {
        "scene_ir": {
            "scene_kind": f"games_pinball_{str(axes.scene_variant)}",
            "entities": [dict(entity) for entity in rendered_scene.scene_entities],
            "relations": relations,
        },
        "query_spec": {
            "query_id": str(axes.query_id),
            "template_id": str(prompt_defaults_checked["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": query_params,
        },
        "render_spec": {
            "scene_variant": str(axes.scene_variant),
            "style_variant": str(axes.style_variant),
            "canvas_width": int(image.size[0]),
            "canvas_height": int(image.size[1]),
            "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
            "panel_scene_style": dict(panel_style_meta),
            "text_style": dict(text_style_meta),
        },
        "render_map": dict(rendered_scene.render_map),
        "execution_trace": execution_trace,
        "witness_symbolic": {
            "type": witness_type,
            "ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
        },
        "projected_annotation": dict(projected_annotation),
        "background": background_meta,
        "post_image_noise": post_noise_meta,
    }
    return GeneratedComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=image,
        trace_payload=trace_payload,
    )


__all__ = [
    "FIRST_HIT_QUERY_ID",
    "PATH_SCORE_QUERY_ID",
    "SCENE_ID",
    "GeneratedComponents",
    "build_components",
    "resolve_axes",
    "resolve_score_path_axes",
    "sample_scene",
]
