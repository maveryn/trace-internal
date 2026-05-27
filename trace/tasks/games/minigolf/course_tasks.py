"""Games Mini-golf tasks over short putting cues and course obstacles."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

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
from ...shared.support_sampling import resolve_integer_choice
from ..shared.complexity import build_games_minigolf_course_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin
from ..shared.layout import resolve_games_layout_jitter
from ..shared.minigolf_common import (
    SUPPORTED_MINIGOLF_QUERY_IDS,
    SUPPORTED_MINIGOLF_SCENE_VARIANTS,
    SUPPORTED_MINIGOLF_STYLE_VARIANTS,
    MinigolfObstacle,
    MinigolfSample,
    MinigolfShotOption,
    obstacle_entity_id,
    path_entity_id,
    path_label,
    validate_minigolf_sample,
)
from ..shared.minigolf_scene import MinigolfRenderParams, render_minigolf_scene
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "games_minigolf_course_base"
_OBSTACLE_LABELS: Tuple[str, ...] = tuple(chr(ord("A") + index) for index in range(8))
_OBSTACLE_KINDS: Tuple[str, ...] = ("rock", "sand", "water", "block")
_SHOT_MODES: Tuple[str, ...] = ("direct", "bank_left", "bank_right", "bank_top")
_OBSTACLE_RADIUS_NORM = 0.045
_HOLE_RADIUS_NORM = 0.038
_BALL_RADIUS_NORM = 0.026


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Mini-golf scenes."""

    obstacle_count_support: Tuple[int, ...] = (4, 5, 6, 7, 8)
    path_option_count_support: Tuple[int, ...] = (4, 5, 6)
    target_obstacle_label_support: Tuple[str, ...] = _OBSTACLE_LABELS
    target_path_index_support: Tuple[int, ...] = tuple(range(6))
    canvas_width: int = 1000
    canvas_height: int = 740
    panel_margin_px: int = 34
    course_width_px: int = 820
    course_height_px: int = 640
    course_border_width_px: int = 7
    ball_radius_px: int = 18
    hole_radius_px: int = 20
    obstacle_radius_px: int = 34
    path_width_px: int = 6
    label_font_size_px: int = 24


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Mini-golf instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    obstacle_count: int
    path_option_count: int
    target_obstacle_label: str | None
    target_path_index: int | None
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    obstacle_count_probabilities: Dict[str, float]
    path_option_count_probabilities: Dict[str, float]
    target_obstacle_label_probabilities: Dict[str, float] | None
    target_path_index_probabilities: Dict[str, float] | None


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "minigolf")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="minigolf")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="minigolf", apply_prob=0.5)


def _resolve_query_id(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced Mini-golf query id."""

    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_MINIGOLF_QUERY_IDS,
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
    """Resolve one balanced named Mini-golf axis."""

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


def _string_support(params: Mapping[str, Any], *, key: str, fallback: Sequence[str]) -> Tuple[str, ...]:
    """Resolve a string support list from params/defaults."""

    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), tuple(fallback)))
    if raw is None:
        raw = tuple(fallback)
    values = (str(raw),) if isinstance(raw, str) else tuple(str(value) for value in raw)
    values = tuple(value for value in values if value)
    if not values:
        raise ValueError(f"{key} must contain at least one label")
    return values


def _resolve_label_choice(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[str],
    namespace: str,
    balanced_flag_key: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one label-valued support choice."""

    support = _string_support(params, key=str(support_key), fallback=fallback_support)
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        value = str(explicit)
        if value not in support:
            raise ValueError(f"{explicit_key}={value!r} is not in {support_key}")
        return value, {str(item): (1.0 if str(item) == value else 0.0) for item in support}
    probabilities = {str(item): 1.0 / float(len(support)) for item in support}
    sampling_index = params.get("_sample_cursor")
    balanced = bool(params.get(str(balanced_flag_key), group_default(_GEN_DEFAULTS, str(balanced_flag_key), True)))
    if balanced and sampling_index is not None:
        return str(support[abs(int(sampling_index)) % len(support)]), probabilities
    rng = spawn_rng(int(instance_seed), str(namespace))
    return str(rng.choice(tuple(support))), probabilities


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one Mini-golf instance."""

    query_id, query_id_probabilities = _resolve_query_id(instance_seed=int(instance_seed), params=params)
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_MINIGOLF_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_MINIGOLF_STYLE_VARIANTS,
    )
    obstacle_count, obstacle_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="obstacle_count_support",
        explicit_key="obstacle_count",
        fallback_support=_DEFAULTS.obstacle_count_support,
        namespace=f"{TASK_ID}.obstacle_count",
        balanced_flag_key="balanced_obstacle_count_sampling",
        namespace_support_permutation=True,
    )
    path_option_count = 0
    path_option_count_probabilities = {"0": 1.0}

    target_obstacle_label: str | None = None
    target_obstacle_label_probabilities: Dict[str, float] | None = None
    target_path_index: int | None = None
    target_path_index_probabilities: Dict[str, float] | None = None
    if str(query_id) == "first_obstacle_label":
        target_obstacle_label, target_obstacle_label_probabilities = _resolve_label_choice(
            instance_seed=int(instance_seed),
            params=params,
            support_key="target_obstacle_label_support",
            explicit_key="target_obstacle_label",
            fallback_support=_DEFAULTS.target_obstacle_label_support,
            namespace=f"{TASK_ID}.target_obstacle_label",
            balanced_flag_key="balanced_target_obstacle_label_sampling",
        )
    if str(query_id) == "shot_path_label":
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
        obstacle_count=int(obstacle_count),
        path_option_count=int(path_option_count),
        target_obstacle_label=None if target_obstacle_label is None else str(target_obstacle_label),
        target_path_index=None if target_path_index is None else int(target_path_index),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        obstacle_count_probabilities=dict(obstacle_count_probabilities),
        path_option_count_probabilities=dict(path_option_count_probabilities),
        target_obstacle_label_probabilities=None if target_obstacle_label_probabilities is None else dict(target_obstacle_label_probabilities),
        target_path_index_probabilities=None if target_path_index_probabilities is None else dict(target_path_index_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> MinigolfRenderParams:
    """Resolve Mini-golf rendering parameters from config/defaults."""

    return MinigolfRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        course_width_px=int(params.get("course_width_px", group_default(_RENDER_DEFAULTS, "course_width_px", _DEFAULTS.course_width_px))),
        course_height_px=int(params.get("course_height_px", group_default(_RENDER_DEFAULTS, "course_height_px", _DEFAULTS.course_height_px))),
        course_border_width_px=int(params.get("course_border_width_px", group_default(_RENDER_DEFAULTS, "course_border_width_px", _DEFAULTS.course_border_width_px))),
        ball_radius_px=int(params.get("ball_radius_px", group_default(_RENDER_DEFAULTS, "ball_radius_px", _DEFAULTS.ball_radius_px))),
        hole_radius_px=int(params.get("hole_radius_px", group_default(_RENDER_DEFAULTS, "hole_radius_px", _DEFAULTS.hole_radius_px))),
        obstacle_radius_px=int(params.get("obstacle_radius_px", group_default(_RENDER_DEFAULTS, "obstacle_radius_px", _DEFAULTS.obstacle_radius_px))),
        path_width_px=int(params.get("path_width_px", group_default(_RENDER_DEFAULTS, "path_width_px", _DEFAULTS.path_width_px))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px))),
        layout_jitter_meta=resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.minigolf.layout",
        ),
    )


def _normalize_angle(angle_rad: float) -> float:
    """Normalize an angle to [-pi, pi]."""

    value = float(angle_rad)
    while value <= -math.pi:
        value += 2.0 * math.pi
    while value > math.pi:
        value -= 2.0 * math.pi
    return float(value)


def _unit_from_angle(angle_rad: float) -> Tuple[float, float]:
    """Return a unit vector for an angle in course-normalized coordinates."""

    return (math.cos(float(angle_rad)), math.sin(float(angle_rad)))


def _distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Return Euclidean distance in normalized course coordinates."""

    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


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
    fx = ox - cx
    fy = oy - cy
    a = (dx * dx) + (dy * dy)
    b = 2.0 * ((fx * dx) + (fy * dy))
    c = (fx * fx) + (fy * fy) - (float(radius) * float(radius))
    disc = (b * b) - (4.0 * a * c)
    if disc < 0.0 or a <= 1e-9:
        return None
    root = math.sqrt(disc)
    t1 = (-b - root) / (2.0 * a)
    t2 = (-b + root) / (2.0 * a)
    candidates = [float(t) for t in (t1, t2) if float(t) >= 1e-5]
    return None if not candidates else min(candidates)


def _first_hit_obstacle_id(
    *,
    origin: Tuple[float, float],
    angle_rad: float,
    obstacles: Sequence[MinigolfObstacle],
) -> str | None:
    """Return the first obstacle intersected by the shot ray."""

    direction = _unit_from_angle(float(angle_rad))
    best: tuple[float, str] | None = None
    for obstacle in obstacles:
        t = _ray_circle_intersection(
            origin=origin,
            direction=direction,
            center=(float(obstacle.x_norm), float(obstacle.y_norm)),
            radius=float(obstacle.radius_norm),
        )
        if t is None:
            continue
        if best is None or float(t) < best[0]:
            best = (float(t), str(obstacle.obstacle_id))
    return None if best is None else str(best[1])


def _trace_shot_path(
    *,
    ball_xy: Tuple[float, float],
    angle_rad: float,
    hole_xy: Tuple[float, float],
    obstacles: Sequence[MinigolfObstacle],
    max_bounces: int = 2,
) -> Tuple[bool, str | None, Tuple[Tuple[float, float], ...]]:
    """Trace one shot through wall bounces until it reaches hole or fails."""

    x, y = float(ball_xy[0]), float(ball_xy[1])
    dx, dy = _unit_from_angle(float(angle_rad))
    points: list[Tuple[float, float]] = [(float(x), float(y))]
    for _segment_index in range(int(max_bounces) + 1):
        wall_candidates: list[Tuple[float, str]] = []
        if dx > 1e-6:
            wall_candidates.append(((1.0 - x) / dx, "right"))
        elif dx < -1e-6:
            wall_candidates.append(((0.0 - x) / dx, "left"))
        if dy > 1e-6:
            wall_candidates.append(((1.0 - y) / dy, "bottom"))
        elif dy < -1e-6:
            wall_candidates.append(((0.0 - y) / dy, "top"))
        wall_candidates = [(float(t), side) for t, side in wall_candidates if float(t) > 1e-5]
        if not wall_candidates:
            break
        t_wall, wall_side = min(wall_candidates, key=lambda item: item[0])

        t_hole = _ray_circle_intersection(
            origin=(x, y),
            direction=(dx, dy),
            center=(float(hole_xy[0]), float(hole_xy[1])),
            radius=_HOLE_RADIUS_NORM,
        )
        obstacle_hits: list[Tuple[float, str]] = []
        for obstacle in obstacles:
            t_obstacle = _ray_circle_intersection(
                origin=(x, y),
                direction=(dx, dy),
                center=(float(obstacle.x_norm), float(obstacle.y_norm)),
                radius=float(obstacle.radius_norm) + 0.005,
            )
            if t_obstacle is not None:
                obstacle_hits.append((float(t_obstacle), str(obstacle.obstacle_id)))
        first_obstacle = min(obstacle_hits, key=lambda item: item[0]) if obstacle_hits else None

        event_t = float(t_wall)
        event_kind = "wall"
        event_id: str | None = str(wall_side)
        if t_hole is not None and float(t_hole) < event_t:
            event_t = float(t_hole)
            event_kind = "hole"
            event_id = "hole"
        if first_obstacle is not None and float(first_obstacle[0]) < event_t:
            event_t = float(first_obstacle[0])
            event_kind = "obstacle"
            event_id = str(first_obstacle[1])

        x = float(x + (dx * event_t))
        y = float(y + (dy * event_t))
        points.append((max(0.0, min(1.0, x)), max(0.0, min(1.0, y))))
        if event_kind == "hole":
            return True, None, tuple(points)
        if event_kind == "obstacle":
            return False, str(event_id), tuple(points)
        if str(wall_side) in {"left", "right"}:
            dx = -dx
        else:
            dy = -dy
        x = max(0.001, min(0.999, x))
        y = max(0.001, min(0.999, y))
    return False, None, tuple(points)


def _safe_obstacle_position(
    *,
    rng: Any,
    existing: Sequence[MinigolfObstacle],
    avoid_points: Sequence[Tuple[float, float]],
    avoid_paths: Sequence[Tuple[Tuple[float, float], ...]],
) -> Tuple[float, float] | None:
    """Sample an obstacle position away from key points and target paths."""

    for _ in range(160):
        x = float(rng.uniform(0.14, 0.86))
        y = float(rng.uniform(0.16, 0.76))
        point = (x, y)
        if any(_distance(point, other) < 0.15 for other in avoid_points):
            continue
        if any(_distance(point, (float(obs.x_norm), float(obs.y_norm))) < 0.15 for obs in existing):
            continue
        too_close_to_path = False
        for path in avoid_paths:
            for a, b in zip(path, path[1:]):
                ax, ay = float(a[0]), float(a[1])
                bx, by = float(b[0]), float(b[1])
                vx, vy = bx - ax, by - ay
                denom = (vx * vx) + (vy * vy)
                if denom <= 1e-9:
                    continue
                t = max(0.0, min(1.0, (((x - ax) * vx) + ((y - ay) * vy)) / denom))
                closest = (ax + (t * vx), ay + (t * vy))
                if _distance(point, closest) < 0.12:
                    too_close_to_path = True
                    break
            if too_close_to_path:
                break
        if too_close_to_path:
            continue
        return point
    return None


def _obstacles_with_target_label(
    *,
    rng: Any,
    target_label: str,
    target_center: Tuple[float, float],
    obstacle_count: int,
    avoid_paths: Sequence[Tuple[Tuple[float, float], ...]],
    avoid_points: Sequence[Tuple[float, float]],
) -> Tuple[MinigolfObstacle, ...] | None:
    """Create obstacle set with the target label on the first-hit obstacle."""

    other_labels = [str(label) for label in _OBSTACLE_LABELS if str(label) != str(target_label)]
    rng.shuffle(other_labels)
    labels = [str(target_label)] + other_labels[: max(0, int(obstacle_count) - 1)]
    rng.shuffle(labels)
    target_index = labels.index(str(target_label))
    obstacles: list[MinigolfObstacle] = []
    for index, label in enumerate(labels):
        if int(index) == int(target_index):
            center = (float(target_center[0]), float(target_center[1]))
        else:
            maybe = _safe_obstacle_position(
                rng=rng,
                existing=obstacles,
                avoid_points=tuple(avoid_points) + (target_center,),
                avoid_paths=avoid_paths,
            )
            if maybe is None:
                return None
            center = maybe
        obstacles.append(
            MinigolfObstacle(
                obstacle_id=obstacle_entity_id(index),
                label=str(label),
                kind=str(_OBSTACLE_KINDS[int((index + rng.randrange(len(_OBSTACLE_KINDS))) % len(_OBSTACLE_KINDS))]),
                x_norm=float(center[0]),
                y_norm=float(center[1]),
                radius_norm=float(_OBSTACLE_RADIUS_NORM * rng.uniform(0.88, 1.10)),
                color_index=int(index),
            )
        )
    return tuple(obstacles)


def _sample_first_obstacle(*, rng: Any, axes: _ResolvedAxes) -> MinigolfSample:
    """Construct a mini-golf scene where a short cue first hits one labeled obstacle."""

    target_label = str(axes.target_obstacle_label or "A")
    obstacle_count = int(axes.obstacle_count)
    for _attempt in range(128):
        ball = (float(rng.uniform(0.34, 0.66)), float(rng.uniform(0.78, 0.88)))
        angle = float(rng.uniform(-2.42, -1.10))
        direction = _unit_from_angle(angle)
        distance = float(rng.uniform(0.42, 0.64))
        target = (ball[0] + (direction[0] * distance), ball[1] + (direction[1] * distance))
        if not (0.14 <= target[0] <= 0.86 and 0.14 <= target[1] <= 0.72):
            continue
        shown_path = (ball, target)
        obstacles = _obstacles_with_target_label(
            rng=rng,
            target_label=target_label,
            target_center=target,
            obstacle_count=obstacle_count,
            avoid_paths=(shown_path,),
            avoid_points=(ball,),
        )
        if obstacles is None:
            continue
        target_obstacle = next(obstacle for obstacle in obstacles if str(obstacle.label) == str(target_label))
        first_id = _first_hit_obstacle_id(origin=ball, angle_rad=angle, obstacles=obstacles)
        if str(first_id) != str(target_obstacle.obstacle_id):
            continue
        sample = MinigolfSample(
            query_id=str(axes.query_id),
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            answer=str(target_obstacle.label),
            ball_x_norm=float(ball[0]),
            ball_y_norm=float(ball[1]),
            hole_x_norm=float(rng.uniform(0.36, 0.64)),
            hole_y_norm=float(rng.uniform(0.12, 0.24)),
            obstacles=obstacles,
            shot_options=tuple(),
            target_obstacle_id=str(target_obstacle.obstacle_id),
            target_obstacle_label=str(target_obstacle.label),
            target_path_id=None,
            target_path_label=None,
            evidence_entity_ids=(str(target_obstacle.obstacle_id),),
            construction_mode="short_cue_first_obstacle_collision",
            cue_visible_fraction=float(rng.uniform(0.32, 0.43)),
            hidden_paths_norm={"shown_path": tuple(shown_path)},
        )
        validate_minigolf_sample(sample)
        return sample
    raise ValueError("failed to construct Mini-golf first obstacle scene")


def _target_angle_for_mode(*, ball: Tuple[float, float], hole: Tuple[float, float], mode: str) -> float:
    """Return the angle that reaches the hole directly or by one mirror-bank."""

    if str(mode) == "bank_left":
        aim = (-float(hole[0]), float(hole[1]))
    elif str(mode) == "bank_right":
        aim = (2.0 - float(hole[0]), float(hole[1]))
    elif str(mode) == "bank_top":
        aim = (float(hole[0]), -float(hole[1]))
    else:
        aim = (float(hole[0]), float(hole[1]))
    return math.atan2(float(aim[1]) - float(ball[1]), float(aim[0]) - float(ball[0]))


def _make_shot_options(
    *,
    rng: Any,
    option_count: int,
    target_index: int,
    target_angle: float,
    ball: Tuple[float, float],
    hole: Tuple[float, float],
    obstacles: Sequence[MinigolfObstacle],
) -> Tuple[MinigolfShotOption, ...] | None:
    """Create shot options with exactly one hole-reaching option."""

    offsets = [-0.96, -0.76, -0.56, -0.38, 0.38, 0.56, 0.76, 0.96]
    rng.shuffle(offsets)
    angles: list[float | None] = [None for _ in range(int(option_count))]
    angles[int(target_index)] = float(target_angle)
    for index in range(int(option_count)):
        if angles[index] is not None:
            continue
        found = False
        for _ in range(80):
            if offsets:
                candidate = _normalize_angle(float(target_angle) + float(offsets.pop()))
            else:
                candidate = float(rng.uniform(-2.82, -0.32))
            success, _, _ = _trace_shot_path(ball_xy=ball, angle_rad=float(candidate), hole_xy=hole, obstacles=obstacles)
            if success:
                continue
            if any(existing is not None and abs(_normalize_angle(float(existing) - float(candidate))) < 0.22 for existing in angles):
                continue
            angles[index] = float(candidate)
            found = True
            break
        if not found:
            return None
    return tuple(
        MinigolfShotOption(
            path_id=path_entity_id(index),
            label=path_label(index),
            angle_rad=float(angles[index]),
            color_index=int(index),
        )
        for index in range(int(option_count))
    )


def _sample_shot_path(*, rng: Any, axes: _ResolvedAxes) -> MinigolfSample:
    """Construct a mini-golf scene where exactly one numbered cue reaches the hole."""

    option_count = int(axes.path_option_count)
    target_index = int(axes.target_path_index or 0)
    for _attempt in range(160):
        ball = (float(rng.uniform(0.38, 0.62)), float(rng.uniform(0.78, 0.88)))
        hole = (float(rng.uniform(0.30, 0.70)), float(rng.uniform(0.12, 0.25)))
        mode = str(rng.choice(_SHOT_MODES))
        target_angle = _target_angle_for_mode(ball=ball, hole=hole, mode=mode)
        success, _, target_path = _trace_shot_path(ball_xy=ball, angle_rad=target_angle, hole_xy=hole, obstacles=tuple())
        if not success or len(target_path) < 2:
            continue

        obstacles: list[MinigolfObstacle] = []
        for index in range(max(2, int(axes.obstacle_count) - 1)):
            maybe = _safe_obstacle_position(
                rng=rng,
                existing=obstacles,
                avoid_points=(ball, hole),
                avoid_paths=(target_path,),
            )
            if maybe is None:
                break
            obstacles.append(
                MinigolfObstacle(
                    obstacle_id=obstacle_entity_id(index),
                    label=str(_OBSTACLE_LABELS[index % len(_OBSTACLE_LABELS)]),
                    kind=str(_OBSTACLE_KINDS[int((index + rng.randrange(len(_OBSTACLE_KINDS))) % len(_OBSTACLE_KINDS))]),
                    x_norm=float(maybe[0]),
                    y_norm=float(maybe[1]),
                    radius_norm=float(_OBSTACLE_RADIUS_NORM * rng.uniform(0.88, 1.08)),
                    color_index=int(index),
                )
            )
        success, _, target_path = _trace_shot_path(ball_xy=ball, angle_rad=target_angle, hole_xy=hole, obstacles=obstacles)
        if not success:
            continue
        options = _make_shot_options(
            rng=rng,
            option_count=option_count,
            target_index=target_index,
            target_angle=target_angle,
            ball=ball,
            hole=hole,
            obstacles=obstacles,
        )
        if options is None:
            continue
        hidden_paths: Dict[str, Tuple[Tuple[float, float], ...]] = {}
        success_count = 0
        for option in options:
            reaches_hole, _, path = _trace_shot_path(
                ball_xy=ball,
                angle_rad=float(option.angle_rad),
                hole_xy=hole,
                obstacles=obstacles,
            )
            hidden_paths[str(option.path_id)] = tuple(path)
            if reaches_hole:
                success_count += 1
                success_id = str(option.path_id)
        target_option = options[int(target_index)]
        if success_count != 1 or str(success_id) != str(target_option.path_id):
            continue
        sample = MinigolfSample(
            query_id=str(axes.query_id),
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            answer=str(target_option.label),
            ball_x_norm=float(ball[0]),
            ball_y_norm=float(ball[1]),
            hole_x_norm=float(hole[0]),
            hole_y_norm=float(hole[1]),
            obstacles=tuple(obstacles),
            shot_options=options,
            target_obstacle_id=None,
            target_obstacle_label=None,
            target_path_id=str(target_option.path_id),
            target_path_label=str(target_option.label),
            evidence_entity_ids=(str(target_option.path_id),),
            construction_mode=f"unique_numbered_{mode}_cue_reaches_hole",
            cue_visible_fraction=0.36,
            hidden_paths_norm=dict(hidden_paths),
        )
        validate_minigolf_sample(sample)
        return sample
    raise ValueError("failed to construct Mini-golf shot path scene")


def _sample_scene(*, rng: Any, axes: _ResolvedAxes) -> MinigolfSample:
    """Construct one Mini-golf scene for the requested query."""

    query = str(axes.query_id)
    if query == "first_obstacle_label":
        return _sample_first_obstacle(rng=rng, axes=axes)
    if query == "shot_path_label":
        return _sample_shot_path(rng=rng, axes=axes)
    raise ValueError(f"unsupported Mini-golf query_id: {query}")


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Mini-golf JSON output."""

    if str(query_id) == "shot_path_label":
        answer_value = "3"
        evidence_value = [[642, 594, 680, 632]]
    else:
        answer_value = "D"
        evidence_value = [[452, 224, 520, 292]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesMinigolfCourseTask:
    """Return one grounded query over a Mini-golf course scene."""

    task_id = TASK_ID
    domain = "games"
    task_group = "minigolf"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: MinigolfSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes)
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
        rendered_scene = render_minigolf_scene(
            obstacles=sampled_scene.obstacles,
            shot_options=sampled_scene.shot_options,
            query_id=str(sampled_scene.query_id),
            ball_xy_norm=(float(sampled_scene.ball_x_norm), float(sampled_scene.ball_y_norm)),
            hole_xy_norm=(float(sampled_scene.hole_x_norm), float(sampled_scene.hole_y_norm)),
            cue_visible_fraction=float(sampled_scene.cue_visible_fraction),
            hidden_paths_norm=sampled_scene.hidden_paths_norm,
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
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
                "object_description_putting_course",
                "minigolf_cue_rule_text",
                "minigolf_bank_rule_text",
                "answer_hint_first_obstacle_label",
                "evidence_hint_first_obstacle_label",
                "answer_hint_shot_path_label",
                "evidence_hint_shot_path_label",
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
                "minigolf_cue_rule_text": str(prompt_defaults["minigolf_cue_rule_text"]),
                "minigolf_bank_rule_text": str(prompt_defaults["minigolf_bank_rule_text"]),
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
        complexity = build_games_minigolf_course_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            obstacle_count=len(sampled_scene.obstacles),
            path_option_count=len(sampled_scene.shot_options),
            evidence_count=len(sampled_scene.evidence_entity_ids),
        )
        obstacle_trace = [
            {
                "obstacle_id": str(obstacle.obstacle_id),
                "label": str(obstacle.label),
                "kind": str(obstacle.kind),
                "x_norm": float(obstacle.x_norm),
                "y_norm": float(obstacle.y_norm),
                "radius_norm": float(obstacle.radius_norm),
            }
            for obstacle in sampled_scene.obstacles
        ]
        path_trace = [
            {
                "path_id": str(path.path_id),
                "label": str(path.label),
                "angle_rad": float(path.angle_rad),
            }
            for path in sampled_scene.shot_options
        ]
        hidden_paths_trace = {
            str(path_id): [[float(x), float(y)] for x, y in points]
            for path_id, points in sampled_scene.hidden_paths_norm.items()
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_minigolf_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "obstacle_count": len(sampled_scene.obstacles),
                    "path_option_count": len(sampled_scene.shot_options),
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
                    "obstacle_count": int(axes.obstacle_count),
                    "path_option_count": int(axes.path_option_count),
                    "target_obstacle_label": axes.target_obstacle_label,
                    "target_path_index": axes.target_path_index,
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "obstacle_count_probabilities": dict(axes.obstacle_count_probabilities),
                    "path_option_count_probabilities": dict(axes.path_option_count_probabilities),
                    "target_obstacle_label_probabilities": None if axes.target_obstacle_label_probabilities is None else dict(axes.target_obstacle_label_probabilities),
                    "target_path_index_probabilities": None if axes.target_path_index_probabilities is None else dict(axes.target_path_index_probabilities),
                    "target_obstacle_id": sampled_scene.target_obstacle_id,
                    "target_path_id": sampled_scene.target_path_id,
                    "cue_visible_fraction": sampled_scene.cue_visible_fraction,
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
                "ball_xy_norm": [float(sampled_scene.ball_x_norm), float(sampled_scene.ball_y_norm)],
                "hole_xy_norm": [float(sampled_scene.hole_x_norm), float(sampled_scene.hole_y_norm)],
                "obstacles": obstacle_trace,
                "shot_options": path_trace,
                "target_obstacle_id": sampled_scene.target_obstacle_id,
                "target_obstacle_label": sampled_scene.target_obstacle_label,
                "target_path_id": sampled_scene.target_path_id,
                "target_path_label": sampled_scene.target_path_label,
                "cue_visible_fraction": float(sampled_scene.cue_visible_fraction),
                "hidden_paths_norm": hidden_paths_trace,
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
            scene_id="minigolf",
            query_id=str(axes.query_id),
        )


@register_task
class GamesMinigolfFirstObstacleLabelTask(FixedQueryVariantTaskMixin, GamesMinigolfCourseTask):
    """Identify the first labeled obstacle hit by the shown putting cue."""

    task_id = "task_games__minigolf__first_obstacle_label"
    fixed_query_id = "first_obstacle_label"


@register_task
class GamesMinigolfShotPathLabelTask(FixedQueryVariantTaskMixin, GamesMinigolfCourseTask):
    """Identify the numbered shot cue that reaches the hole."""

    task_id = "task_games__minigolf__shot_path_label"
    fixed_query_id = "shot_path_label"


__all__ = [
    "GamesMinigolfCourseTask",
    "GamesMinigolfFirstObstacleLabelTask",
    "GamesMinigolfShotPathLabelTask",
]
