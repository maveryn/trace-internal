"""Identity-free sampling helpers for pinball-table game scenes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.tasks.games.shared.sampling import resolve_games_named_axis
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.support_sampling import resolve_integer_choice

from .defaults import (
    BUMPER_RADIUS_NORM,
    DEFAULTS,
    DROP_TARGET_HEIGHT_NORM,
    DROP_TARGET_WIDTH_NORM,
    OBJECT_LABELS,
    PATH_HIT_COUNT_SUPPORT,
    PATH_SCORE_SHAPES,
    PATH_SCORE_VALUES,
    ROLLOVER_HEIGHT_NORM,
    ROLLOVER_WIDTH_NORM,
    STANDUP_RADIUS_NORM,
)
from .state import (
    SUPPORTED_PINBALL_OBJECT_KINDS,
    SUPPORTED_PINBALL_SCENE_VARIANTS,
    SUPPORTED_PINBALL_STYLE_VARIANTS,
    PinballObject,
    PinballSceneState,
    pinball_object_id,
    validate_pinball_scene_state,
)


@dataclass(frozen=True)
class PinballVisualAxes:
    """Resolved scene/render axes shared by pinball-table tasks."""

    scene_variant: str
    style_variant: str
    object_count: int
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    object_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class PinballTargetLabelAxis:
    """Resolved visible-object label target for label-selection tasks."""

    target_object_label: str
    target_object_label_probabilities: Dict[str, float]


@dataclass(frozen=True)
class PinballScorePathAxes:
    """Resolved path-shape and hit-count axes for score-path tasks."""

    path_shape: str
    path_shape_probabilities: Dict[str, float]
    path_hit_count: int
    path_hit_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class PinballFirstHitConstruction:
    """Constructed launch scene with the unique first-hit object bound."""

    scene: PinballSceneState
    target_object_id: str
    target_object_label: str


@dataclass(frozen=True)
class PinballPathScoreConstruction:
    """Constructed drawn-path score scene with ordered hit ids bound."""

    scene: PinballSceneState
    annotation_entity_ids: Tuple[str, ...]
    score_total: int
    hit_score_values: Tuple[int, ...]
    repeated_hit_object_ids: Tuple[str, ...]


@dataclass(frozen=True)
class _ScorePathPlan:
    """Complete drawn scoring path plus any forced scoring events."""

    points: Tuple[Tuple[float, float], ...]
    forced_hit_events: Tuple[Tuple[float, Tuple[float, float]], ...] = ()


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


def resolve_pinball_visual_axes(
    instance_seed: int,
    *,
    gen_defaults: Mapping[str, Any],
    namespace: str,
    params: Mapping[str, Any],
) -> PinballVisualAxes:
    """Resolve shared visual axes without public task or query routing."""

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
        fallback_support=DEFAULTS.object_count_support,
        namespace=f"{str(namespace)}.object_count",
        balanced_flag_key="balanced_object_count_sampling",
        namespace_support_permutation=True,
    )
    return PinballVisualAxes(
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        object_count=int(object_count),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        object_count_probabilities=dict(object_count_probabilities),
    )


def resolve_pinball_target_label(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    namespace: str,
    object_count: int,
) -> PinballTargetLabelAxis:
    """Resolve a target label from labels visible in the sampled scene."""

    support = tuple(OBJECT_LABELS[: int(object_count)])
    explicit = params.get("target_object_label")
    probabilities = {str(label): 1.0 / float(len(support)) for label in support}
    if explicit is not None:
        value = str(explicit)
        if value not in support:
            raise ValueError("target_object_label must be visible for the sampled object_count")
        return PinballTargetLabelAxis(
            target_object_label=value,
            target_object_label_probabilities={str(label): (1.0 if str(label) == value else 0.0) for label in support},
        )
    balanced = bool(params.get("balanced_target_object_label_sampling", group_default(gen_defaults, "balanced_target_object_label_sampling", True)))
    if balanced and params.get("_sample_cursor") is not None:
        value = str(support[abs(int(params["_sample_cursor"])) % len(support)])
        return PinballTargetLabelAxis(
            target_object_label=value,
            target_object_label_probabilities=probabilities,
        )
    rng = spawn_rng(int(instance_seed), str(namespace))
    return PinballTargetLabelAxis(
        target_object_label=str(rng.choice(support)),
        target_object_label_probabilities=probabilities,
    )


def resolve_pinball_score_path_axes(
    instance_seed: int,
    *,
    gen_defaults: Mapping[str, Any],
    namespace: str,
    params: Mapping[str, Any],
    object_count: int,
) -> PinballScorePathAxes:
    """Resolve path-shape and path-hit-count axes for a drawn scoring path."""

    path_shape, path_shape_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        namespace="path_shape",
        explicit_key="path_shape",
        weights_key="path_shape_weights",
        balance_flag_key="balanced_path_shape_sampling",
        supported=PATH_SCORE_SHAPES,
    )
    support = tuple(value for value in PATH_HIT_COUNT_SUPPORT if int(value) <= max(1, int(object_count) - 1))
    path_hit_count, path_hit_count_probabilities = resolve_integer_choice(
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
    if int(path_hit_count) >= int(object_count):
        raise ValueError("path_hit_count must be smaller than object_count")
    return PinballScorePathAxes(
        path_shape=str(path_shape),
        path_shape_probabilities=dict(path_shape_probabilities),
        path_hit_count=int(path_hit_count),
        path_hit_count_probabilities=dict(path_hit_count_probabilities),
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


def first_hit_object_id(
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


def pinball_turn_angle_degrees(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
) -> float:
    """Expose the clean-turn calculation for focused contract tests."""

    return _turn_angle_degrees(a, b, c)


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
    """Choose an object kind that fits the playfield zone."""

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
    """Create one pinball object with kind-appropriate footprint."""

    kind_value = str(kind)
    radius_norm = BUMPER_RADIUS_NORM
    width_norm = DROP_TARGET_WIDTH_NORM
    height_norm = DROP_TARGET_HEIGHT_NORM
    if kind_value == "bumper":
        radius_norm = float(BUMPER_RADIUS_NORM * float(rng.uniform(0.88, 1.12)))
        width_norm = float(DROP_TARGET_WIDTH_NORM * float(rng.uniform(0.90, 1.12)))
        height_norm = float(DROP_TARGET_HEIGHT_NORM * float(rng.uniform(0.90, 1.12)))
    elif kind_value == "standup_target":
        radius_norm = float(STANDUP_RADIUS_NORM * float(rng.uniform(0.90, 1.10)))
        width_norm = float(DROP_TARGET_WIDTH_NORM * float(rng.uniform(0.90, 1.12)))
        height_norm = float(DROP_TARGET_HEIGHT_NORM * float(rng.uniform(0.90, 1.12)))
    elif kind_value == "rollover_lane":
        radius_norm = float(STANDUP_RADIUS_NORM * float(rng.uniform(0.90, 1.10)))
        width_norm = float(ROLLOVER_WIDTH_NORM * float(rng.uniform(0.90, 1.10)))
        height_norm = float(ROLLOVER_HEIGHT_NORM * float(rng.uniform(0.90, 1.10)))
    else:
        radius_norm = float(STANDUP_RADIUS_NORM * float(rng.uniform(0.90, 1.10)))
        width_norm = float(DROP_TARGET_WIDTH_NORM * float(rng.uniform(0.90, 1.12)))
        height_norm = float(DROP_TARGET_HEIGHT_NORM * float(rng.uniform(0.90, 1.12)))
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
    axes: PinballVisualAxes,
    target_object_label: str,
    ball: Tuple[float, float],
    target: Tuple[float, float],
    path: Tuple[Tuple[float, float], Tuple[float, float]],
) -> Tuple[PinballObject, ...] | None:
    """Create labeled objects with a requested label placed on the first-hit object."""

    labels = list(OBJECT_LABELS[: int(axes.object_count)])
    rng.shuffle(labels)
    target_index = labels.index(str(target_object_label))
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


def sample_unique_first_hit_playfield(
    *,
    rng: Any,
    axes: PinballVisualAxes,
    target_object_label: str,
) -> PinballFirstHitConstruction:
    """Construct a playfield where the launch cue first hits one requested label."""

    for _attempt in range(180):
        ball = (float(rng.uniform(0.38, 0.62)), float(rng.uniform(0.82, 0.90)))
        angle = float(rng.uniform(-2.34, -0.80))
        direction = _unit_from_angle(angle)
        distance = float(rng.uniform(0.42, 0.66))
        target = (ball[0] + (direction[0] * distance), ball[1] + (direction[1] * distance))
        if not (0.16 <= target[0] <= 0.84 and 0.14 <= target[1] <= 0.70):
            continue
        path = (ball, target)
        objects = _objects_with_target_label(
            rng=rng,
            axes=axes,
            target_object_label=str(target_object_label),
            ball=ball,
            target=target,
            path=path,
        )
        if objects is None:
            continue
        target_object = next(obj for obj in objects if str(obj.label) == str(target_object_label))
        first_id = first_hit_object_id(origin=ball, angle_rad=angle, objects=objects)
        if str(first_id) != str(target_object.object_id):
            continue
        scene = PinballSceneState(
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            ball_x_norm=float(ball[0]),
            ball_y_norm=float(ball[1]),
            cue_angle_rad=float(angle),
            cue_visible_fraction=float(rng.uniform(0.34, 0.46)),
            objects=objects,
            construction_mode="unique_straight_launch_first_hit_projected_playfield",
            hidden_path_norm=tuple(path),
        )
        validate_pinball_scene_state(scene)
        return PinballFirstHitConstruction(
            scene=scene,
            target_object_id=str(target_object.object_id),
            target_object_label=str(target_object.label),
        )
    raise ValueError("failed to construct pinball first-hit scene")


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
    axes: PinballVisualAxes,
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
    labels = list(OBJECT_LABELS[: int(axes.object_count)])
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
        score_value = int(rng.choice(PATH_SCORE_VALUES))
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
        score_value = int(rng.choice(PATH_SCORE_VALUES))
        objects.append(_make_object(index=index, label=str(labels[index]), kind=kind, center=center, rng=rng, score_value=score_value))
    return tuple(objects), tuple(annotation_ids)


def sample_path_score_playfield(
    *,
    rng: Any,
    axes: PinballVisualAxes,
    path_shape: str,
    hit_count: int,
) -> PinballPathScoreConstruction:
    """Construct a playfield with a complete shown score trajectory."""

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
        hit_score_values = tuple(int(score_by_id[str(entity_id)]) for entity_id in annotation_ids)
        score_total = int(sum(hit_score_values))
        if int(score_total) <= 0:
            continue
        repeated_ids = tuple(
            sorted(
                {
                    str(entity_id)
                    for entity_id in annotation_ids
                    if annotation_ids.count(str(entity_id)) > 1
                }
            )
        )
        scene = PinballSceneState(
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            ball_x_norm=float(path_plan.points[0][0]),
            ball_y_norm=float(path_plan.points[0][1]),
            cue_angle_rad=0.0,
            cue_visible_fraction=1.0,
            objects=objects,
            construction_mode=f"complete_{str(path_shape)}_path_score_sum",
            hidden_path_norm=tuple(path_plan.points),
        )
        validate_pinball_scene_state(scene)
        return PinballPathScoreConstruction(
            scene=scene,
            annotation_entity_ids=tuple(str(entity_id) for entity_id in annotation_ids),
            score_total=int(score_total),
            hit_score_values=hit_score_values,
            repeated_hit_object_ids=repeated_ids,
        )
    raise ValueError("failed to construct pinball path-score scene")


__all__ = [
    "PinballFirstHitConstruction",
    "PinballPathScoreConstruction",
    "PinballScorePathAxes",
    "PinballTargetLabelAxis",
    "PinballVisualAxes",
    "first_hit_object_id",
    "pinball_turn_angle_degrees",
    "resolve_pinball_score_path_axes",
    "resolve_pinball_target_label",
    "resolve_pinball_visual_axes",
    "sample_path_score_playfield",
    "sample_unique_first_hit_playfield",
]
