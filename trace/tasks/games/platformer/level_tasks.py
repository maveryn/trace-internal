"""Games Platformer tasks over side-scroller jump arcs."""

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
from ..shared.complexity import build_games_platformer_level_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.platformer_common import (
    SUPPORTED_PLATFORMER_QUERY_VARIANTS,
    SUPPORTED_PLATFORMER_SCENE_VARIANTS,
    SUPPORTED_PLATFORMER_STYLE_VARIANTS,
    PlatformerCollectible,
    PlatformerHazard,
    PlatformerPlatform,
    PlatformerSample,
    collectible_entity_id,
    hazard_entity_id,
    platform_entity_id,
    validate_platformer_sample,
)
from ..shared.platformer_scene import PlatformerRenderParams, render_platformer_scene
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_variant
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "games_platformer_level_base"
_LABELS: Tuple[str, ...] = tuple(chr(ord("A") + index) for index in range(8))
_HAZARD_KINDS: Tuple[str, ...] = ("spikes", "patrol")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible platformer scenes."""

    platform_count_support: Tuple[int, ...] = (4, 5, 6, 7)
    hazard_count_support: Tuple[int, ...] = (4, 5, 6, 7, 8)
    distractor_collectible_count_support: Tuple[int, ...] = (4, 5, 6, 7, 8)
    target_platform_label_support: Tuple[str, ...] = _LABELS
    target_collectible_count_support: Tuple[int, ...] = (2, 3, 4, 5, 6, 7)
    canvas_width: int = 1000
    canvas_height: int = 740
    level_width_px: int = 860
    level_height_px: int = 610
    level_border_width_px: int = 5
    platform_height_px: int = 34
    player_width_px: int = 38
    player_height_px: int = 58
    hazard_width_px: int = 54
    hazard_height_px: int = 54
    collectible_radius_px: int = 18
    path_width_px: int = 6
    label_font_size_px: int = 24


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Platformer instance."""

    query_variant: str
    scene_variant: str
    style_variant: str
    platform_count: int
    hazard_count: int
    distractor_collectible_count: int
    target_platform_label: str | None
    target_collectible_count: int | None
    query_variant_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    platform_count_probabilities: Dict[str, float]
    hazard_count_probabilities: Dict[str, float]
    distractor_collectible_count_probabilities: Dict[str, float]
    target_platform_label_probabilities: Dict[str, float] | None
    target_collectible_count_probabilities: Dict[str, float] | None


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "platformer")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="platformer")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="platformer", apply_prob=0.5)


def _resolve_query_variant(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced Platformer query variant."""

    return resolve_games_query_variant(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_PLATFORMER_QUERY_VARIANTS,
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
    """Resolve one balanced named Platformer axis."""

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
    """Resolve all semantic and visual axes for one Platformer instance."""

    query_variant, query_variant_probabilities = _resolve_query_variant(instance_seed=int(instance_seed), params=params)
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_PLATFORMER_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_PLATFORMER_STYLE_VARIANTS,
    )
    platform_count, platform_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="platform_count_support",
        explicit_key="platform_count",
        fallback_support=_DEFAULTS.platform_count_support,
        namespace=f"{TASK_ID}.platform_count",
        balanced_flag_key="balanced_platform_count_sampling",
        namespace_support_permutation=True,
    )
    hazard_count, hazard_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="hazard_count_support",
        explicit_key="hazard_count",
        fallback_support=_DEFAULTS.hazard_count_support,
        namespace=f"{TASK_ID}.hazard_count",
        balanced_flag_key="balanced_hazard_count_sampling",
        namespace_support_permutation=True,
    )
    distractor_collectible_count, distractor_collectible_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="distractor_collectible_count_support",
        explicit_key="distractor_collectible_count",
        fallback_support=_DEFAULTS.distractor_collectible_count_support,
        namespace=f"{TASK_ID}.distractor_collectible_count",
        balanced_flag_key="balanced_distractor_collectible_count_sampling",
        namespace_support_permutation=True,
    )

    target_platform_label: str | None = None
    target_platform_label_probabilities: Dict[str, float] | None = None
    target_collectible_count: int | None = None
    target_collectible_count_probabilities: Dict[str, float] | None = None
    if str(query_variant) == "jump_landing_label":
        target_platform_label, target_platform_label_probabilities = _resolve_label_choice(
            instance_seed=int(instance_seed),
            params=params,
            support_key="target_platform_label_support",
            explicit_key="target_platform_label",
            fallback_support=_DEFAULTS.target_platform_label_support,
            namespace=f"{TASK_ID}.target_platform_label",
            balanced_flag_key="balanced_target_platform_label_sampling",
        )
    elif str(query_variant) == "collectible_count":
        target_collectible_count, target_collectible_count_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="target_collectible_count_support",
            explicit_key="target_collectible_count",
            fallback_support=_DEFAULTS.target_collectible_count_support,
            namespace=f"{TASK_ID}.target_collectible_count",
            balanced_flag_key="balanced_target_collectible_count_sampling",
            namespace_support_permutation=True,
        )

    return _ResolvedAxes(
        query_variant=str(query_variant),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        platform_count=int(platform_count),
        hazard_count=int(hazard_count),
        distractor_collectible_count=int(distractor_collectible_count),
        target_platform_label=None if target_platform_label is None else str(target_platform_label),
        target_collectible_count=None if target_collectible_count is None else int(target_collectible_count),
        query_variant_probabilities=dict(query_variant_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        platform_count_probabilities=dict(platform_count_probabilities),
        hazard_count_probabilities=dict(hazard_count_probabilities),
        distractor_collectible_count_probabilities=dict(distractor_collectible_count_probabilities),
        target_platform_label_probabilities=None if target_platform_label_probabilities is None else dict(target_platform_label_probabilities),
        target_collectible_count_probabilities=None if target_collectible_count_probabilities is None else dict(target_collectible_count_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> PlatformerRenderParams:
    """Resolve Platformer rendering parameters from config/defaults."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.platformer.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.platformer.layout",
        ),
        unit_scale_meta,
    )
    return PlatformerRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        level_width_px=scale_games_px(params.get("level_width_px", group_default(_RENDER_DEFAULTS, "level_width_px", _DEFAULTS.level_width_px)), unit_scale, min_px=430),
        level_height_px=scale_games_px(params.get("level_height_px", group_default(_RENDER_DEFAULTS, "level_height_px", _DEFAULTS.level_height_px)), unit_scale, min_px=305),
        level_border_width_px=scale_games_px(params.get("level_border_width_px", group_default(_RENDER_DEFAULTS, "level_border_width_px", _DEFAULTS.level_border_width_px)), unit_scale, min_px=2),
        platform_height_px=scale_games_px(params.get("platform_height_px", group_default(_RENDER_DEFAULTS, "platform_height_px", _DEFAULTS.platform_height_px)), unit_scale, min_px=17),
        player_width_px=scale_games_px(params.get("player_width_px", group_default(_RENDER_DEFAULTS, "player_width_px", _DEFAULTS.player_width_px)), unit_scale, min_px=19),
        player_height_px=scale_games_px(params.get("player_height_px", group_default(_RENDER_DEFAULTS, "player_height_px", _DEFAULTS.player_height_px)), unit_scale, min_px=29),
        hazard_width_px=scale_games_px(params.get("hazard_width_px", group_default(_RENDER_DEFAULTS, "hazard_width_px", _DEFAULTS.hazard_width_px)), unit_scale, min_px=27),
        hazard_height_px=scale_games_px(params.get("hazard_height_px", group_default(_RENDER_DEFAULTS, "hazard_height_px", _DEFAULTS.hazard_height_px)), unit_scale, min_px=27),
        collectible_radius_px=scale_games_px(params.get("collectible_radius_px", group_default(_RENDER_DEFAULTS, "collectible_radius_px", _DEFAULTS.collectible_radius_px)), unit_scale, min_px=9),
        path_width_px=scale_games_px(params.get("path_width_px", group_default(_RENDER_DEFAULTS, "path_width_px", _DEFAULTS.path_width_px)), unit_scale, min_px=3),
        label_font_size_px=scale_games_px(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px)), unit_scale, min_px=12),
        layout_jitter_meta=layout_jitter,
    )


def _distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Return Euclidean distance in normalized level coordinates."""

    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def _curve_point(
    *,
    start: Tuple[float, float],
    control: Tuple[float, float],
    end: Tuple[float, float],
    t: float,
) -> Tuple[float, float]:
    """Return one quadratic Bezier point."""

    u = 1.0 - float(t)
    return (
        (u * u * float(start[0])) + (2.0 * u * float(t) * float(control[0])) + (float(t) * float(t) * float(end[0])),
        (u * u * float(start[1])) + (2.0 * u * float(t) * float(control[1])) + (float(t) * float(t) * float(end[1])),
    )


def _jump_arc(
    *,
    start: Tuple[float, float],
    end: Tuple[float, float],
    rng: Any,
    lift: float | None = None,
    segments: int = 40,
) -> Tuple[Tuple[float, float], ...]:
    """Construct a smooth side-scroller jump arc."""

    control_x = ((float(start[0]) + float(end[0])) / 2.0) + float(rng.uniform(-0.035, 0.035))
    control_y = min(float(start[1]), float(end[1])) - float(lift if lift is not None else rng.uniform(0.24, 0.34))
    control_y = max(0.08, float(control_y))
    return tuple(
        _curve_point(start=start, control=(control_x, control_y), end=end, t=float(index) / float(segments))
        for index in range(int(segments) + 1)
    )


def _point_segment_distance(point: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Distance from a point to one segment in normalized coordinates."""

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


def _point_path_distance(point: Tuple[float, float], path: Sequence[Tuple[float, float]]) -> float:
    """Distance from a point to a polyline."""

    if len(path) < 2:
        return 1.0
    return min(_point_segment_distance(point, a, b) for a, b in zip(path, path[1:]))


def _safe_center(
    *,
    rng: Any,
    existing: Sequence[Tuple[float, float]],
    avoid_path: Sequence[Tuple[float, float]],
    avoid_points: Sequence[Tuple[float, float]],
    x_range: Tuple[float, float],
    y_range: Tuple[float, float],
    min_existing_distance: float,
    min_path_distance: float,
) -> Tuple[float, float] | None:
    """Sample a center away from occupied points and the operative path."""

    for _ in range(180):
        point = (float(rng.uniform(float(x_range[0]), float(x_range[1]))), float(rng.uniform(float(y_range[0]), float(y_range[1]))))
        if any(_distance(point, other) < float(min_existing_distance) for other in existing):
            continue
        if any(_distance(point, other) < float(min_existing_distance) for other in avoid_points):
            continue
        if avoid_path and _point_path_distance(point, avoid_path) < float(min_path_distance):
            continue
        return point
    return None


def _make_platform(
    *,
    index: int,
    label: str,
    center: Tuple[float, float],
    rng: Any,
    width_norm: float | None = None,
) -> PlatformerPlatform:
    """Create one platform object."""

    width = float(width_norm if width_norm is not None else rng.uniform(0.15, 0.23))
    return PlatformerPlatform(
        platform_id=platform_entity_id(index),
        label=str(label),
        x_norm=float(center[0]),
        y_norm=float(center[1]),
        width_norm=float(width),
        height_norm=0.058,
        color_index=int(index),
    )


def _make_hazard(
    *,
    index: int,
    label: str,
    center: Tuple[float, float],
    rng: Any,
) -> PlatformerHazard:
    """Create one hazard object."""

    return PlatformerHazard(
        hazard_id=hazard_entity_id(index),
        label=str(label),
        kind=str(_HAZARD_KINDS[int((index + rng.randrange(len(_HAZARD_KINDS))) % len(_HAZARD_KINDS))]),
        x_norm=float(center[0]),
        y_norm=float(center[1]),
        width_norm=float(rng.uniform(0.060, 0.076)),
        height_norm=float(rng.uniform(0.070, 0.088)),
        color_index=int(index),
    )


def _decorative_hazards(
    *,
    rng: Any,
    count: int,
    avoid_path: Sequence[Tuple[float, float]],
    avoid_points: Sequence[Tuple[float, float]],
) -> Tuple[PlatformerHazard, ...]:
    """Create unlabeled decorative hazards away from the operative path."""

    hazards: list[PlatformerHazard] = []
    centers: list[Tuple[float, float]] = []
    for index in range(int(count)):
        maybe = _safe_center(
            rng=rng,
            existing=centers,
            avoid_path=avoid_path,
            avoid_points=avoid_points,
            x_range=(0.24, 0.86),
            y_range=(0.62, 0.84),
            min_existing_distance=0.13,
            min_path_distance=0.11,
        )
        if maybe is None:
            break
        centers.append(maybe)
        hazards.append(_make_hazard(index=index, label="", center=maybe, rng=rng))
    return tuple(hazards)


def _decorative_collectibles(
    *,
    rng: Any,
    start_index: int,
    count: int,
    avoid_path: Sequence[Tuple[float, float]],
    avoid_points: Sequence[Tuple[float, float]],
) -> Tuple[PlatformerCollectible, ...]:
    """Create decorative collectibles away from the operative path."""

    coins: list[PlatformerCollectible] = []
    centers: list[Tuple[float, float]] = []
    for offset in range(int(count)):
        maybe = _safe_center(
            rng=rng,
            existing=centers,
            avoid_path=avoid_path,
            avoid_points=avoid_points,
            x_range=(0.18, 0.88),
            y_range=(0.22, 0.78),
            min_existing_distance=0.075,
            min_path_distance=0.085,
        )
        if maybe is None:
            break
        centers.append(maybe)
        index = int(start_index) + int(offset)
        coins.append(
            PlatformerCollectible(
                collectible_id=collectible_entity_id(index),
                x_norm=float(maybe[0]),
                y_norm=float(maybe[1]),
                radius_norm=0.022,
                on_path=False,
                color_index=int(index),
            )
        )
    return tuple(coins)


def _sample_landing(*, rng: Any, axes: _ResolvedAxes) -> PlatformerSample:
    """Construct a platformer scene where the jump lands on one labeled platform."""

    target_label = str(axes.target_platform_label or "A")
    for _attempt in range(160):
        player = (float(rng.uniform(0.12, 0.22)), float(rng.uniform(0.76, 0.83)))
        target_top = (float(rng.uniform(0.60, 0.86)), float(rng.uniform(0.44, 0.66)))
        path = _jump_arc(start=player, end=target_top, rng=rng, lift=float(rng.uniform(0.24, 0.34)))
        target_center = (float(target_top[0]), float(target_top[1] + 0.032))

        labels = [str(target_label)] + [str(label) for label in _LABELS if str(label) != str(target_label)]
        labels = labels[: int(axes.platform_count)]
        rng.shuffle(labels)
        target_index = labels.index(str(target_label))
        platforms: list[PlatformerPlatform] = []
        centers: list[Tuple[float, float]] = []
        for index, label in enumerate(labels):
            if int(index) == int(target_index):
                center = target_center
            else:
                maybe = _safe_center(
                    rng=rng,
                    existing=centers + [target_center],
                    avoid_path=path,
                    avoid_points=(player, target_center),
                    x_range=(0.28, 0.88),
                    y_range=(0.32, 0.74),
                    min_existing_distance=0.15,
                    min_path_distance=0.09,
                )
                if maybe is None:
                    break
                center = maybe
            centers.append(center)
            platforms.append(_make_platform(index=index, label=str(label), center=center, rng=rng, width_norm=0.20 if int(index) == int(target_index) else None))
        if len(platforms) != len(labels):
            continue
        target_platform = platforms[target_index]
        hazards = _decorative_hazards(rng=rng, count=max(2, int(axes.hazard_count) - 3), avoid_path=path, avoid_points=(player, target_center))
        coins = _decorative_collectibles(rng=rng, start_index=0, count=4, avoid_path=path, avoid_points=(player, target_center))
        sample = PlatformerSample(
            query_variant=str(axes.query_variant),
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            answer=str(target_platform.label),
            player_x_norm=float(player[0]),
            player_y_norm=float(player[1]),
            path_points_norm=tuple(path),
            visible_path_fraction=float(rng.uniform(0.42, 0.52)),
            platforms=tuple(platforms),
            hazards=tuple(hazards),
            collectibles=tuple(coins),
            target_platform_id=str(target_platform.platform_id),
            target_platform_label=str(target_platform.label),
            target_collectible_ids=tuple(),
            evidence_entity_ids=(str(target_platform.platform_id),),
            construction_mode="short_arc_lands_on_labeled_platform",
        )
        validate_platformer_sample(sample)
        return sample
    raise ValueError("failed to construct Platformer landing scene")


def _sample_collectibles(*, rng: Any, axes: _ResolvedAxes) -> PlatformerSample:
    """Construct a platformer scene with a full shown arc collecting a target coin count."""

    target_count = int(axes.target_collectible_count or 2)
    for _attempt in range(160):
        player = (float(rng.uniform(0.12, 0.20)), float(rng.uniform(0.76, 0.83)))
        end = (float(rng.uniform(0.78, 0.90)), float(rng.uniform(0.54, 0.70)))
        path = _jump_arc(start=player, end=end, rng=rng, lift=float(rng.uniform(0.24, 0.35)))
        t_values = [0.20 + ((0.64 * (idx + 0.5)) / float(target_count)) for idx in range(int(target_count))]
        target_collectibles: list[PlatformerCollectible] = []
        for index, t in enumerate(t_values):
            point = tuple(float(value) for value in path[max(1, min(len(path) - 2, int(round(float(t) * (len(path) - 1)))))])
            target_collectibles.append(
                PlatformerCollectible(
                    collectible_id=collectible_entity_id(index),
                    x_norm=float(point[0]),
                    y_norm=float(point[1]),
                    radius_norm=0.022,
                    on_path=True,
                    color_index=int(index),
                )
            )
        distractors = _decorative_collectibles(
            rng=rng,
            start_index=len(target_collectibles),
            count=int(axes.distractor_collectible_count),
            avoid_path=path,
            avoid_points=(player, end) + tuple((coin.x_norm, coin.y_norm) for coin in target_collectibles),
        )
        platforms = tuple(
            _make_platform(
                index=index,
                label="",
                center=(float(rng.uniform(0.28, 0.88)), float(rng.uniform(0.48, 0.78))),
                rng=rng,
                width_norm=float(rng.uniform(0.14, 0.21)),
            )
            for index in range(max(3, int(axes.platform_count) - 1))
        )
        hazards = _decorative_hazards(rng=rng, count=max(2, int(axes.hazard_count) - 3), avoid_path=path, avoid_points=(player, end))
        target_ids = tuple(str(coin.collectible_id) for coin in target_collectibles)
        sample = PlatformerSample(
            query_variant=str(axes.query_variant),
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            answer=int(len(target_collectibles)),
            player_x_norm=float(player[0]),
            player_y_norm=float(player[1]),
            path_points_norm=tuple(path),
            visible_path_fraction=1.0,
            platforms=platforms,
            hazards=tuple(hazards),
            collectibles=tuple(target_collectibles) + tuple(distractors),
            target_platform_id=None,
            target_platform_label=None,
            target_collectible_ids=target_ids,
            evidence_entity_ids=target_ids,
            construction_mode="full_arc_collectible_count",
        )
        validate_platformer_sample(sample)
        return sample
    raise ValueError("failed to construct Platformer collectible count scene")


def _sample_scene(*, rng: Any, axes: _ResolvedAxes) -> PlatformerSample:
    """Construct one Platformer scene for the requested query."""

    query = str(axes.query_variant)
    if query == "jump_landing_label":
        return _sample_landing(rng=rng, axes=axes)
    if query == "collectible_count":
        return _sample_collectibles(rng=rng, axes=axes)
    raise ValueError(f"unsupported Platformer query_variant: {query}")


def _build_prompt_json_examples(query_variant: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Platformer JSON output."""

    if str(query_variant) == "collectible_count":
        answer_value: str | int = 4
        evidence_value = [[328, 210, 364, 246], [430, 182, 466, 218], [536, 198, 572, 234], [641, 254, 677, 290]]
    else:
        answer_value = "D"
        evidence_value = [[604, 398, 784, 442]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesPlatformerLevelTask:
    """Return one grounded query over a side-scroller platformer level."""

    task_id = TASK_ID
    domain = "games"
    task_group = "platformer"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: PlatformerSample | None = None
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
        rendered_scene = render_platformer_scene(
            platforms=sampled_scene.platforms,
            hazards=sampled_scene.hazards,
            collectibles=sampled_scene.collectibles,
            query_variant=str(sampled_scene.query_variant),
            player_xy_norm=(float(sampled_scene.player_x_norm), float(sampled_scene.player_y_norm)),
            path_points_norm=tuple(sampled_scene.path_points_norm),
            visible_path_fraction=float(sampled_scene.visible_path_fraction),
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
                "object_description_side_scroller",
                "platformer_short_arc_rule_text",
                "platformer_full_arc_rule_text",
                "answer_hint_jump_landing_label",
                "evidence_hint_jump_landing_label",
                "answer_hint_collectible_count",
                "evidence_hint_collectible_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_variant))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "platformer_short_arc_rule_text": str(prompt_defaults["platformer_short_arc_rule_text"]),
                "platformer_full_arc_rule_text": str(prompt_defaults["platformer_full_arc_rule_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_variant)}"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_variant)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        if str(axes.query_variant) == "collectible_count":
            answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
        else:
            answer_gt = TypedValue(type="string", value=str(sampled_scene.answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_platformer_level_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_variant=str(axes.query_variant),
            platform_count=len(sampled_scene.platforms),
            hazard_count=len(sampled_scene.hazards),
            collectible_count=len(sampled_scene.collectibles),
            target_answer=int(sampled_scene.answer) if str(axes.query_variant) == "collectible_count" else len(sampled_scene.evidence_entity_ids),
            evidence_count=len(sampled_scene.evidence_entity_ids),
        )
        platform_trace = [
            {
                "platform_id": str(platform.platform_id),
                "label": str(platform.label),
                "x_norm": float(platform.x_norm),
                "y_norm": float(platform.y_norm),
                "width_norm": float(platform.width_norm),
                "height_norm": float(platform.height_norm),
            }
            for platform in sampled_scene.platforms
        ]
        hazard_trace = [
            {
                "hazard_id": str(hazard.hazard_id),
                "label": str(hazard.label),
                "kind": str(hazard.kind),
                "x_norm": float(hazard.x_norm),
                "y_norm": float(hazard.y_norm),
                "width_norm": float(hazard.width_norm),
                "height_norm": float(hazard.height_norm),
            }
            for hazard in sampled_scene.hazards
        ]
        collectible_trace = [
            {
                "collectible_id": str(coin.collectible_id),
                "x_norm": float(coin.x_norm),
                "y_norm": float(coin.y_norm),
                "radius_norm": float(coin.radius_norm),
                "on_path": bool(coin.on_path),
            }
            for coin in sampled_scene.collectibles
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_platformer_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "query_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "platform_count": len(sampled_scene.platforms),
                    "hazard_count": len(sampled_scene.hazards),
                    "collectible_count": len(sampled_scene.collectibles),
                    "platform_count_axis": int(axes.platform_count),
                    "hazard_count_axis": int(axes.hazard_count),
                    "distractor_collectible_count_axis": int(axes.distractor_collectible_count),
                    "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
                },
            },
            "query_spec": {
                "query_variant": str(axes.query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "query_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "platform_count": int(axes.platform_count),
                    "hazard_count": int(axes.hazard_count),
                    "distractor_collectible_count": int(axes.distractor_collectible_count),
                    "actual_platform_count": len(sampled_scene.platforms),
                    "actual_hazard_count": len(sampled_scene.hazards),
                    "actual_collectible_count": len(sampled_scene.collectibles),
                    "target_platform_label": axes.target_platform_label,
                    "target_collectible_count": axes.target_collectible_count,
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_variant_probabilities": dict(axes.query_variant_probabilities),
                    "query_variant_probabilities": dict(axes.query_variant_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "platform_count_probabilities": dict(axes.platform_count_probabilities),
                    "hazard_count_probabilities": dict(axes.hazard_count_probabilities),
                    "distractor_collectible_count_probabilities": dict(axes.distractor_collectible_count_probabilities),
                    "target_platform_label_probabilities": None if axes.target_platform_label_probabilities is None else dict(axes.target_platform_label_probabilities),
                    "target_collectible_count_probabilities": None if axes.target_collectible_count_probabilities is None else dict(axes.target_collectible_count_probabilities),
                    "target_platform_id": sampled_scene.target_platform_id,
                    "target_collectible_ids": list(sampled_scene.target_collectible_ids),
                    "visible_path_fraction": float(sampled_scene.visible_path_fraction),
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
                "query_variant": str(axes.query_variant),
                "query_variant": str(axes.query_variant),
                "style_variant": str(axes.style_variant),
                "player_xy_norm": [float(sampled_scene.player_x_norm), float(sampled_scene.player_y_norm)],
                "path_points_norm": [[float(x), float(y)] for x, y in sampled_scene.path_points_norm],
                "visible_path_fraction": float(sampled_scene.visible_path_fraction),
                "platforms": platform_trace,
                "hazards": hazard_trace,
                "collectibles": collectible_trace,
                "target_platform_id": sampled_scene.target_platform_id,
                "target_platform_label": sampled_scene.target_platform_label,
                "target_collectible_ids": list(sampled_scene.target_collectible_ids),
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
            query_variant=str(axes.query_variant),
            scene_id="platformer",
            query_id=str(axes.query_variant),
        )


@register_task
class GamesPlatformerJumpLandingLabelTask(FixedQueryVariantTaskMixin, GamesPlatformerLevelTask):
    """Identify the labeled platform reached by a jump arc."""

    task_id = "task_games__platformer__jump_landing_label"
    fixed_query_variant = "jump_landing_label"


@register_task
class GamesPlatformerCollectibleCountTask(FixedQueryVariantTaskMixin, GamesPlatformerLevelTask):
    """Count collectibles lying on the shown jump arc."""

    task_id = "task_games__platformer__collectible_count"
    fixed_query_variant = "collectible_count"


__all__ = [
    "GamesPlatformerCollectibleCountTask",
    "GamesPlatformerJumpLandingLabelTask",
    "GamesPlatformerLevelTask",
]
