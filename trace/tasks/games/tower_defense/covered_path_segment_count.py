"""Shared tower-defense generator for games-domain tasks."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, load_scene_generation_rendering_prompt_defaults, required_group_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from .shared.common import (
    SUPPORTED_TOWER_DEFENSE_QUERY_IDS,
    SUPPORTED_TOWER_DEFENSE_SCENE_VARIANTS,
    SUPPORTED_TOWER_DEFENSE_STYLE_VARIANTS,
    Point,
    TowerDefenseEnemy,
    TowerDefenseSample,
    TowerDefenseTower,
    covered_path_segment_ids,
    covered_tower_ids,
    enemy_entity_id,
    local_distance,
    path_segment_entity_id,
    tower_covers_point,
    tower_entity_id,
    validate_tower_defense_sample,
    visible_tower_trace,
)
from .shared.rendering import TowerDefenseRenderParams, render_tower_defense_scene
from ..shared.layout import resolve_games_layout_jitter
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.visual_defaults import load_games_scene_noise_defaults


SCENE_ID = "tower_defense"
TASK_ID = "games_tower_defense_base"
TOWER_COVERAGE_TASK_ID = "task_games__tower_defense__tower_coverage_count"
COVERED_PATH_TASK_ID = "task_games__tower_defense__covered_path_segment_count"
MARKED_ENEMY_QUERY_ID = "marked_enemy_covered_by_tower_count"
COVERED_PATH_QUERY_ID = "covered_path_segment_count"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for tower-defense scenes."""

    tower_count_support: Tuple[int, ...] = (5, 6, 7, 8)
    covered_path_tower_count_support: Tuple[int, ...] = (5, 6, 7, 8, 9, 10)
    path_segment_count_support: Tuple[int, ...] = (10, 11, 12, 13, 14, 15, 16)
    target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    covered_path_target_answer_support: Tuple[int, ...] = (3, 4, 5, 6, 7, 8, 9, 10)
    canvas_width: int = 980
    canvas_height: int = 760
    map_width_px: int = 820
    map_height_px: int = 570
    panel_margin_px: int = 38
    path_width_px: int = 28
    path_node_radius_px: int = 17
    tower_radius_px: int = 19
    enemy_radius_px: int = 13
    range_outline_width_px: int = 3
    range_radius_min_px: int = 118
    range_radius_max_px: int = 190
    covered_path_range_radius_min_px: int = 88
    covered_path_range_radius_max_px: int = 168
    tower_path_clearance_px: int = 42
    tower_min_gap_px: int = 46
    uncovered_margin_px: int = 28


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one tower-defense instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    tower_count: int
    path_segment_count: int
    target_answer: int
    target_answer_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    tower_count_probabilities: Dict[str, float]
    path_segment_count_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_SCENE_DEFAULTS = get_scene_defaults("games", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.5)


def _resolve_query_id(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced tower-defense query id."""

    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_TOWER_DEFENSE_QUERY_IDS,
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
    """Resolve one balanced named tower-defense axis."""

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
    """Resolve semantic and visual axes for one tower-defense instance."""

    query_id, query_id_probabilities = _resolve_query_id(instance_seed=int(instance_seed), params=params)
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_TOWER_DEFENSE_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_TOWER_DEFENSE_STYLE_VARIANTS,
    )
    if str(query_id) == COVERED_PATH_QUERY_ID:
        tower_count_support_key = "covered_path_tower_count_support"
        tower_count_fallback = _DEFAULTS.covered_path_tower_count_support
    else:
        tower_count_support_key = "tower_count_support"
        tower_count_fallback = _DEFAULTS.tower_count_support
    tower_count, tower_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=tower_count_support_key,
        explicit_key="tower_count",
        fallback_support=tower_count_fallback,
        namespace=f"{TASK_ID}.{str(query_id)}.tower_count",
        balanced_flag_key="balanced_tower_count_sampling",
        namespace_support_permutation=True,
    )
    path_segment_count, path_segment_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="path_segment_count_support",
        explicit_key="path_segment_count",
        fallback_support=_DEFAULTS.path_segment_count_support,
        namespace=f"{TASK_ID}.path_segment_count",
        balanced_flag_key="balanced_path_segment_count_sampling",
        namespace_support_permutation=True,
    )
    if str(query_id) == COVERED_PATH_QUERY_ID:
        target_support_key = "covered_path_target_answer_support"
        target_fallback = _DEFAULTS.covered_path_target_answer_support
    else:
        target_support_key = "target_answer_support"
        target_fallback = _DEFAULTS.target_answer_support
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=target_support_key,
        explicit_key="target_answer",
        fallback_support=target_fallback,
        namespace=f"{TASK_ID}.{str(query_id)}.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_answer_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=target_support_key,
        fallback=target_fallback,
    )
    if str(query_id) == COVERED_PATH_QUERY_ID:
        min_path_count = int(target_answer)
        path_segment_count = min(16, max(int(path_segment_count), int(min_path_count)))
        tower_count = max(5, int(tower_count), int(target_answer))
    elif int(target_answer) > int(tower_count):
        tower_count = int(target_answer)
    if str(query_id) != COVERED_PATH_QUERY_ID and int(target_answer) > 0:
        tower_count = max(int(tower_count), min(8, int(target_answer) + 2))
    tower_count = max(5, int(tower_count))
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        tower_count=int(tower_count),
        path_segment_count=int(path_segment_count),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        tower_count_probabilities=dict(tower_count_probabilities),
        path_segment_count_probabilities=dict(path_segment_count_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> TowerDefenseRenderParams:
    """Resolve tower-defense rendering parameters."""

    return TowerDefenseRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        map_width_px=int(params.get("map_width_px", group_default(_RENDER_DEFAULTS, "map_width_px", _DEFAULTS.map_width_px))),
        map_height_px=int(params.get("map_height_px", group_default(_RENDER_DEFAULTS, "map_height_px", _DEFAULTS.map_height_px))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        path_width_px=int(params.get("path_width_px", group_default(_RENDER_DEFAULTS, "path_width_px", _DEFAULTS.path_width_px))),
        path_node_radius_px=int(params.get("path_node_radius_px", group_default(_RENDER_DEFAULTS, "path_node_radius_px", _DEFAULTS.path_node_radius_px))),
        tower_radius_px=int(params.get("tower_radius_px", group_default(_RENDER_DEFAULTS, "tower_radius_px", _DEFAULTS.tower_radius_px))),
        enemy_radius_px=int(params.get("enemy_radius_px", group_default(_RENDER_DEFAULTS, "enemy_radius_px", _DEFAULTS.enemy_radius_px))),
        range_outline_width_px=int(params.get("range_outline_width_px", group_default(_RENDER_DEFAULTS, "range_outline_width_px", _DEFAULTS.range_outline_width_px))),
        layout_jitter_meta=resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.tower_defense.layout_jitter",
        ),
    )


def _resample_polyline(waypoints: Sequence[Point], *, point_count: int) -> Tuple[Point, ...]:
    """Return `point_count` equally spaced points along one polyline."""

    if len(waypoints) < 2:
        raise ValueError("tower-defense path needs at least two waypoints")
    segment_lengths = [
        local_distance(start, end)
        for start, end in zip(waypoints, waypoints[1:])
    ]
    total_length = sum(float(value) for value in segment_lengths)
    if total_length <= 0.0:
        raise ValueError("tower-defense path has zero length")
    count = max(2, int(point_count))
    samples: list[Point] = []
    for sample_index in range(count):
        target = (float(total_length) * float(sample_index)) / float(count - 1)
        cursor = 0.0
        for (start, end), length in zip(zip(waypoints, waypoints[1:]), segment_lengths):
            if target <= cursor + float(length) or (start, end) == (waypoints[-2], waypoints[-1]):
                ratio = 0.0 if float(length) <= 0.0 else (float(target) - float(cursor)) / float(length)
                ratio = max(0.0, min(1.0, float(ratio)))
                samples.append(
                    (
                        round(float(start[0]) + ((float(end[0]) - float(start[0])) * ratio), 3),
                        round(float(start[1]) + ((float(end[1]) - float(start[1])) * ratio), 3),
                    )
                )
                break
            cursor += float(length)
    return tuple(samples)


def _sample_path_points(
    *,
    rng,
    scene_variant: str,
    map_width_px: int,
    map_height_px: int,
    path_segment_count: int,
) -> Tuple[Point, ...]:
    """Construct one readable winding path in local map coordinates."""

    width = float(map_width_px)
    height = float(map_height_px)
    margin_x = 84.0
    if str(scene_variant) == "switchback_path":
        y_fracs = (0.18, 0.34, 0.52, 0.70, 0.84)
        left_x, right_x = margin_x, width - margin_x
    else:
        y_fracs = (0.20, 0.41, 0.62, 0.80)
        left_x, right_x = margin_x, width - margin_x
    waypoints: list[Point] = []
    for index, y_frac in enumerate(y_fracs):
        y = round(float(height * float(y_frac)), 3)
        if index == 0:
            waypoints.append((left_x, y))
        waypoints.append((right_x if index % 2 == 0 else left_x, y))
        if index < len(y_fracs) - 1:
            next_y = round(float(height * float(y_fracs[index + 1])), 3)
            waypoints.append((right_x if index % 2 == 0 else left_x, next_y))
    if rng.random() < 0.5:
        # Slight nonsemantic vertical wiggle while preserving the same route contract.
        jittered = []
        for index, (x, y) in enumerate(waypoints):
            if index in {0, len(waypoints) - 1}:
                jittered.append((x, y))
            else:
                jittered.append((x, round(max(72.0, min(height - 72.0, y + rng.uniform(-12.0, 12.0))), 3)))
        waypoints = jittered
    return _resample_polyline(waypoints, point_count=int(path_segment_count))


def _point_segment_distance(point: Point, start: Point, end: Point) -> float:
    """Return distance from a point to one line segment."""

    px, py = float(point[0]), float(point[1])
    sx, sy = float(start[0]), float(start[1])
    ex, ey = float(end[0]), float(end[1])
    dx, dy = ex - sx, ey - sy
    denom = (dx * dx) + (dy * dy)
    if denom <= 1e-9:
        return math.hypot(px - sx, py - sy)
    ratio = max(0.0, min(1.0, (((px - sx) * dx) + ((py - sy) * dy)) / denom))
    cx, cy = sx + (ratio * dx), sy + (ratio * dy)
    return math.hypot(px - cx, py - cy)


def _min_path_distance(point: Point, path_points: Sequence[Point]) -> float:
    """Return distance from a point to the visible path polyline."""

    if len(path_points) < 2:
        return float("inf")
    return min(
        _point_segment_distance(point, start, end)
        for start, end in zip(path_points, path_points[1:])
    )


def _tower_center_is_valid(
    center: Point,
    *,
    radius: float,
    edge_radius_px: float | None = None,
    map_width_px: int,
    map_height_px: int,
    path_points: Sequence[Point],
    existing_centers: Sequence[Point],
    tower_path_clearance_px: float,
    tower_min_gap_px: float,
) -> bool:
    """Return whether one tower center is visibly valid."""

    x, y = float(center[0]), float(center[1])
    edge_margin = float(radius if edge_radius_px is None else edge_radius_px) + 26.0
    if x < edge_margin or x > float(map_width_px) - edge_margin:
        return False
    if y < edge_margin or y > float(map_height_px) - edge_margin:
        return False
    if _min_path_distance(center, path_points) < float(tower_path_clearance_px):
        return False
    return all(local_distance(center, other) >= float(tower_min_gap_px) for other in existing_centers)


def _sample_tower_center(
    *,
    rng,
    covers_target: bool,
    target_point: Point,
    radius: float,
    map_width_px: int,
    map_height_px: int,
    path_points: Sequence[Point],
    existing_centers: Sequence[Point],
    tower_path_clearance_px: float,
    tower_min_gap_px: float,
    uncovered_margin_px: float,
) -> Point:
    """Sample one tower center satisfying the target coverage predicate."""

    for _ in range(700):
        if bool(covers_target):
            min_distance = max(float(tower_path_clearance_px) + 12.0, 70.0)
            max_distance = max(min_distance + 4.0, float(radius) - 24.0)
            distance = rng.uniform(min_distance, max_distance)
            angle = rng.uniform(0.0, math.tau)
            center = (
                round(float(target_point[0]) + (math.cos(angle) * distance), 3),
                round(float(target_point[1]) + (math.sin(angle) * distance), 3),
            )
        else:
            center = (
                round(rng.uniform(float(radius) + 34.0, float(map_width_px) - float(radius) - 34.0), 3),
                round(rng.uniform(float(radius) + 34.0, float(map_height_px) - float(radius) - 34.0), 3),
            )
        if not _tower_center_is_valid(
            center,
            radius=float(radius),
            edge_radius_px=20.0,
            map_width_px=int(map_width_px),
            map_height_px=int(map_height_px),
            path_points=path_points,
            existing_centers=existing_centers,
            tower_path_clearance_px=float(tower_path_clearance_px),
            tower_min_gap_px=float(tower_min_gap_px),
        ):
            continue
        distance_to_target = local_distance(center, target_point)
        if bool(covers_target) and distance_to_target <= float(radius) - 18.0:
            return center
        if not bool(covers_target) and distance_to_target >= float(radius) + float(uncovered_margin_px):
            return center
    raise ValueError("failed to sample a valid tower center")


def _select_path_coverage_indices(*, rng, path_count: int, target_answer: int) -> Tuple[int, ...]:
    """Select exactly the path indices intended to be covered."""

    if int(target_answer) <= 0:
        raise ValueError("covered path task requires a positive target answer")
    if int(target_answer) > int(path_count):
        raise ValueError("target_answer cannot exceed path segment count")
    return tuple(sorted(int(index) for index in rng.sample(range(int(path_count)), int(target_answer))))


def _path_tangent_at_index(path_points: Sequence[Point], index: int) -> Point:
    """Return local unit tangent near one path point."""

    if len(path_points) < 2:
        return (1.0, 0.0)
    idx = max(0, min(len(path_points) - 1, int(index)))
    if idx == 0:
        start, end = path_points[0], path_points[1]
    elif idx == len(path_points) - 1:
        start, end = path_points[-2], path_points[-1]
    else:
        start, end = path_points[idx - 1], path_points[idx + 1]
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = math.hypot(dx, dy)
    if length <= 1e-6:
        return (1.0, 0.0)
    return (dx / length, dy / length)


def _sample_path_chunk_tower(
    *,
    rng,
    tower_id: str,
    chunk_indices: Sequence[int],
    selected_indices: Sequence[int],
    path_points: Sequence[Point],
    map_width_px: int,
    map_height_px: int,
    range_min: int,
    range_max: int,
    existing_centers: Sequence[Point],
    tower_path_clearance_px: float,
    tower_min_gap_px: float,
) -> TowerDefenseTower:
    """Sample one tower that covers its selected path run without adding outside nodes."""

    if not chunk_indices:
        raise ValueError("path chunk tower needs at least one path index")
    selected_set = {int(index) for index in selected_indices}
    chunk_points = [path_points[int(index)] for index in chunk_indices]
    anchor = (
        round(sum(float(point[0]) for point in chunk_points) / float(len(chunk_points)), 3),
        round(sum(float(point[1]) for point in chunk_points) / float(len(chunk_points)), 3),
    )
    tangent = _path_tangent_at_index(path_points, int(chunk_indices[len(chunk_indices) // 2]))
    perpendicular = (-float(tangent[1]), float(tangent[0]))
    for _ in range(420):
        if len(chunk_points) == 1:
            angle = rng.uniform(0.0, math.tau)
            direction = (math.cos(angle), math.sin(angle))
        else:
            sign = -1.0 if rng.random() < 0.5 else 1.0
            direction = (float(perpendicular[0]) * sign, float(perpendicular[1]) * sign)
        offset = rng.uniform(max(float(tower_path_clearance_px) + 20.0, 68.0), 92.0)
        center = (
            round(float(anchor[0]) + (float(direction[0]) * float(offset)), 3),
            round(float(anchor[1]) + (float(direction[1]) * float(offset)), 3),
        )
        min_radius = max(local_distance(center, point) for point in chunk_points) + rng.uniform(14.0, 23.0)
        radius = float(max(int(range_min), int(math.ceil(min_radius))))
        if float(radius) > float(range_max):
            continue
        if not _tower_center_is_valid(
            center,
            radius=float(radius),
            edge_radius_px=20.0,
            map_width_px=int(map_width_px),
            map_height_px=int(map_height_px),
            path_points=path_points,
            existing_centers=existing_centers,
            tower_path_clearance_px=float(tower_path_clearance_px),
            tower_min_gap_px=float(tower_min_gap_px),
        ):
            continue
        tower = TowerDefenseTower(
            tower_id=str(tower_id),
            center_px=center,
            range_radius_px=float(radius),
            covers_target=False,
        )
        covered_indices = {
            int(index)
            for index, point in enumerate(path_points)
            if tower_covers_point(tower, point)
        }
        if set(int(index) for index in chunk_indices).issubset(covered_indices) and covered_indices.issubset(selected_set):
            return tower
    raise ValueError("failed to place path chunk tower")


def _sample_nonexpanding_tower(
    *,
    rng,
    tower_id: str,
    selected_indices: Sequence[int],
    path_points: Sequence[Point],
    map_width_px: int,
    map_height_px: int,
    range_min: int,
    range_max: int,
    existing_centers: Sequence[Point],
    tower_path_clearance_px: float,
    tower_min_gap_px: float,
) -> TowerDefenseTower:
    """Sample one decoy tower that covers no unselected path segment."""

    selected_set = {int(index) for index in selected_indices}
    for _ in range(700):
        radius = float(rng.randint(int(range_min), int(range_max)))
        center = (
            round(rng.uniform(float(radius) + 34.0, float(map_width_px) - float(radius) - 34.0), 3),
            round(rng.uniform(float(radius) + 34.0, float(map_height_px) - float(radius) - 34.0), 3),
        )
        if not _tower_center_is_valid(
            center,
            radius=float(radius),
            map_width_px=int(map_width_px),
            map_height_px=int(map_height_px),
            path_points=path_points,
            existing_centers=existing_centers,
            tower_path_clearance_px=float(tower_path_clearance_px),
            tower_min_gap_px=float(tower_min_gap_px),
        ):
            continue
        tower = TowerDefenseTower(
            tower_id=str(tower_id),
            center_px=center,
            range_radius_px=float(radius),
            covers_target=False,
        )
        covered_indices = {
            int(index)
            for index, point in enumerate(path_points)
            if tower_covers_point(tower, point)
        }
        if covered_indices.issubset(selected_set):
            return tower
    raise ValueError("failed to place nonexpanding tower")


def _sample_marked_enemy_scene(
    *,
    rng,
    axes: _ResolvedAxes,
    render_params: TowerDefenseRenderParams,
    params: Mapping[str, Any],
) -> TowerDefenseSample:
    """Construct one tower-defense scene for the requested answer count."""

    map_width = int(render_params.map_width_px)
    map_height = int(render_params.map_height_px)
    path_points = _sample_path_points(
        rng=rng,
        scene_variant=str(axes.scene_variant),
        map_width_px=int(map_width),
        map_height_px=int(map_height),
        path_segment_count=int(axes.path_segment_count),
    )
    low_index = max(2, int(len(path_points) * 0.34))
    high_index = min(len(path_points) - 3, int(len(path_points) * 0.70))
    target_index = int(rng.randint(low_index, max(low_index, high_index)))
    enemy = TowerDefenseEnemy(
        enemy_id=enemy_entity_id(),
        center_px=tuple(path_points[int(target_index)]),
        path_index=int(target_index),
    )
    range_min = int(params.get("range_radius_min_px", group_default(_GEN_DEFAULTS, "range_radius_min_px", _DEFAULTS.range_radius_min_px)))
    range_max = int(params.get("range_radius_max_px", group_default(_GEN_DEFAULTS, "range_radius_max_px", _DEFAULTS.range_radius_max_px)))
    if int(range_min) > int(range_max):
        raise ValueError("range_radius_min_px must be <= range_radius_max_px")
    tower_path_clearance = float(params.get("tower_path_clearance_px", group_default(_GEN_DEFAULTS, "tower_path_clearance_px", _DEFAULTS.tower_path_clearance_px)))
    tower_min_gap = float(params.get("tower_min_gap_px", group_default(_GEN_DEFAULTS, "tower_min_gap_px", _DEFAULTS.tower_min_gap_px)))
    uncovered_margin = float(params.get("uncovered_margin_px", group_default(_GEN_DEFAULTS, "uncovered_margin_px", _DEFAULTS.uncovered_margin_px)))

    desired_flags = [True for _ in range(int(axes.target_answer))]
    desired_flags.extend(False for _ in range(max(0, int(axes.tower_count) - int(axes.target_answer))))
    rng.shuffle(desired_flags)
    towers: list[TowerDefenseTower] = []
    existing_centers: list[Point] = []
    for index, covers_target in enumerate(desired_flags):
        if bool(covers_target):
            radius = float(rng.randint(max(int(range_min), 148), int(range_max)))
        else:
            radius = float(rng.randint(int(range_min), int(range_max)))
        center = _sample_tower_center(
            rng=rng,
            covers_target=bool(covers_target),
            target_point=enemy.center_px,
            radius=float(radius),
            map_width_px=int(map_width),
            map_height_px=int(map_height),
            path_points=path_points,
            existing_centers=existing_centers,
            tower_path_clearance_px=float(tower_path_clearance),
            tower_min_gap_px=float(tower_min_gap),
            uncovered_margin_px=float(uncovered_margin),
        )
        tower = TowerDefenseTower(
            tower_id=tower_entity_id(index),
            center_px=center,
            range_radius_px=float(radius),
            covers_target=bool(tower_covers_point(
                TowerDefenseTower(
                    tower_id=tower_entity_id(index),
                    center_px=center,
                    range_radius_px=float(radius),
                    covers_target=bool(covers_target),
                ),
                enemy.center_px,
            )),
        )
        if bool(tower.covers_target) != bool(covers_target):
            raise ValueError("sampled tower coverage did not match target flag")
        towers.append(tower)
        existing_centers.append(center)
    annotation_ids = covered_tower_ids(towers, enemy.center_px)
    sample = TowerDefenseSample(
        mode=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        map_width_px=int(map_width),
        map_height_px=int(map_height),
        path_points_px=tuple(path_points),
        towers=tuple(towers),
        enemy=enemy,
        answer=int(len(annotation_ids)),
        target_answer=int(axes.target_answer),
        annotation_entity_ids=tuple(annotation_ids),
        construction_mode="construct_towers_by_marked_enemy_coverage",
    )
    validate_tower_defense_sample(sample)
    return sample


def _sample_covered_path_scene(
    *,
    rng,
    axes: _ResolvedAxes,
    render_params: TowerDefenseRenderParams,
    params: Mapping[str, Any],
) -> TowerDefenseSample:
    """Construct one tower-defense scene for covered path segment counting."""

    map_width = int(render_params.map_width_px)
    map_height = int(render_params.map_height_px)
    path_points = _sample_path_points(
        rng=rng,
        scene_variant=str(axes.scene_variant),
        map_width_px=int(map_width),
        map_height_px=int(map_height),
        path_segment_count=int(axes.path_segment_count),
    )
    range_min = int(params.get("covered_path_range_radius_min_px", group_default(_GEN_DEFAULTS, "covered_path_range_radius_min_px", _DEFAULTS.covered_path_range_radius_min_px)))
    range_max = int(params.get("covered_path_range_radius_max_px", group_default(_GEN_DEFAULTS, "covered_path_range_radius_max_px", _DEFAULTS.covered_path_range_radius_max_px)))
    if int(range_min) > int(range_max):
        raise ValueError("range_radius_min_px must be <= range_radius_max_px")
    tower_path_clearance = float(params.get("tower_path_clearance_px", group_default(_GEN_DEFAULTS, "tower_path_clearance_px", _DEFAULTS.tower_path_clearance_px)))
    tower_min_gap = float(params.get("tower_min_gap_px", group_default(_GEN_DEFAULTS, "tower_min_gap_px", _DEFAULTS.tower_min_gap_px)))
    selected_indices = _select_path_coverage_indices(
        rng=rng,
        path_count=len(path_points),
        target_answer=int(axes.target_answer),
    )
    towers: list[TowerDefenseTower] = []
    existing_centers: list[Point] = []
    if len(selected_indices) > int(axes.tower_count):
        raise ValueError("not enough towers for selected covered path nodes")
    for path_index in selected_indices:
        tower = _sample_path_chunk_tower(
            rng=rng,
            tower_id=tower_entity_id(len(towers)),
            chunk_indices=(int(path_index),),
            selected_indices=selected_indices,
            path_points=path_points,
            map_width_px=int(map_width),
            map_height_px=int(map_height),
            range_min=int(range_min),
            range_max=int(range_max),
            existing_centers=existing_centers,
            tower_path_clearance_px=float(tower_path_clearance),
            tower_min_gap_px=float(tower_min_gap),
        )
        towers.append(tower)
        existing_centers.append(tower.center_px)

    while len(towers) < int(axes.tower_count):
        tower = _sample_nonexpanding_tower(
            rng=rng,
            tower_id=tower_entity_id(len(towers)),
            selected_indices=selected_indices,
            path_points=path_points,
            map_width_px=int(map_width),
            map_height_px=int(map_height),
            range_min=int(range_min),
            range_max=int(range_max),
            existing_centers=existing_centers,
            tower_path_clearance_px=float(tower_path_clearance),
            tower_min_gap_px=float(tower_min_gap),
        )
        towers.append(tower)
        existing_centers.append(tower.center_px)

    rng.shuffle(towers)
    towers = [
        TowerDefenseTower(
            tower_id=tower_entity_id(index),
            center_px=tower.center_px,
            range_radius_px=float(tower.range_radius_px),
            covers_target=False,
        )
        for index, tower in enumerate(towers)
    ]
    annotation_ids = covered_path_segment_ids(towers, path_points)
    sample = TowerDefenseSample(
        mode=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        map_width_px=int(map_width),
        map_height_px=int(map_height),
        path_points_px=tuple(path_points),
        towers=tuple(towers),
        enemy=None,
        answer=int(len(annotation_ids)),
        target_answer=int(axes.target_answer),
        annotation_entity_ids=tuple(annotation_ids),
        construction_mode="construct_towers_by_path_segment_union_coverage",
    )
    validate_tower_defense_sample(sample)
    return sample


def _sample_scene(
    *,
    rng,
    axes: _ResolvedAxes,
    render_params: TowerDefenseRenderParams,
    params: Mapping[str, Any],
) -> TowerDefenseSample:
    """Construct one tower-defense scene for the requested query."""

    if str(axes.query_id) == COVERED_PATH_QUERY_ID:
        return _sample_covered_path_scene(
            rng=rng,
            axes=axes,
            render_params=render_params,
            params=params,
        )
    return _sample_marked_enemy_scene(
        rng=rng,
        axes=axes,
        render_params=render_params,
        params=params,
    )


def _build_prompt_json_examples() -> Tuple[str, str]:
    """Return prompt examples for tower-defense JSON output."""

    answer_value = 2
    annotation_value = [[246, 314], [514, 226]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )




class GamesTowerDefenseTask:
    """Return one grounded query over a tower-defense map."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    supported_query_ids: Tuple[str, ...] = SUPPORTED_TOWER_DEFENSE_QUERY_IDS
    fixed_query_id: str | None = None

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        task_params = dict(params)
        if self.fixed_query_id is not None:
            task_params["query_id"] = str(self.fixed_query_id)
        axes = _resolve_axes(int(instance_seed), params=task_params)
        render_params = _render_params(task_params, instance_seed=int(instance_seed))

        sampled_scene: TowerDefenseSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(
                    rng=attempt_rng,
                    axes=axes,
                    render_params=render_params,
                    params=task_params,
                )
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid tower-defense map after {max_attempts} attempts")

        panel_style, panel_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace="games.tower_defense.panel_scene_style",
            treatment_weights=task_params.get(
                "panel_scene_treatment_weights",
                group_default(_RENDER_DEFAULTS, "panel_scene_treatment_weights", None),
            ),
            palette_weights=task_params.get(
                "panel_scene_palette_weights",
                group_default(_RENDER_DEFAULTS, "panel_scene_palette_weights", None),
            ),
        )
        background, background_meta = make_panel_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=panel_style,
        )
        rendered_scene = render_tower_defense_scene(
            path_points_px=sampled_scene.path_points_px,
            towers=sampled_scene.towers,
            enemy=sampled_scene.enemy,
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
            panel_style=panel_style,
        )
        annotation_points = [
            list(rendered_scene.render_map["entity_points_px"][str(entity_id)])
            for entity_id in sampled_scene.annotation_entity_ids
        ]
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=task_params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        object_description_key = f"object_description_{str(axes.scene_variant)}_{str(axes.query_id)}"
        rule_key = f"coverage_rule_text_{str(axes.query_id)}"
        answer_hint_key = f"answer_hint_{str(axes.query_id)}"
        annotation_hint_key = f"annotation_hint_{str(axes.query_id)}"
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                object_description_key,
                rule_key,
                answer_hint_key,
                annotation_hint_key,
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples()
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            dynamic_slots={
                "object_description": str(prompt_defaults[object_description_key]),
                "coverage_rule_text": str(prompt_defaults[rule_key]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[answer_hint_key]),
                "annotation_hint": str(prompt_defaults[annotation_hint_key]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
        annotation_gt = TypedValue(type="point_set", value=[list(point) for point in annotation_points])
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_tower_defense_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "tower_count": len(sampled_scene.towers),
                    "path_segment_count": len(sampled_scene.path_points_px),
                    "marked_enemy_id": enemy_entity_id() if sampled_scene.enemy is not None else None,
                    "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
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
                    "tower_count": len(sampled_scene.towers),
                    "path_segment_count": len(sampled_scene.path_points_px),
                    "target_answer": int(sampled_scene.target_answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "tower_count_probabilities": dict(axes.tower_count_probabilities),
                    "path_segment_count_probabilities": dict(axes.path_segment_count_probabilities),
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "map_width_px": int(sampled_scene.map_width_px),
                "map_height_px": int(sampled_scene.map_height_px),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "tower_defense_style": dict(rendered_scene.render_map.get("tower_defense_style", {})),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "map_width_px": int(sampled_scene.map_width_px),
                "map_height_px": int(sampled_scene.map_height_px),
                "path_points_px_local": [
                    [round(float(point[0]), 3), round(float(point[1]), 3)]
                    for point in sampled_scene.path_points_px
                ],
                "marked_enemy": (
                    {
                        "enemy_id": str(sampled_scene.enemy.enemy_id),
                        "center_px_local": [
                            round(float(sampled_scene.enemy.center_px[0]), 3),
                            round(float(sampled_scene.enemy.center_px[1]), 3),
                        ],
                        "path_index": int(sampled_scene.enemy.path_index),
                    }
                    if sampled_scene.enemy is not None
                    else None
                ),
                "towers": list(visible_tower_trace(sampled_scene.towers)),
                "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
            },
            "projected_annotation": {
                "type": "point_set",
                "point_set": [list(point) for point in annotation_points],
                "pixel_point_set": [list(point) for point in annotation_points],
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
            task_versions=default_task_versions(),
            scene_id="tower_defense",
            query_id=str(axes.query_id),
        )


__all__ = [
    "COVERED_PATH_QUERY_ID",
    "COVERED_PATH_TASK_ID",
    "GamesTowerDefenseTask",
    "MARKED_ENEMY_QUERY_ID",
    "TOWER_COVERAGE_TASK_ID",
]

@register_task
class GamesTowerDefenseCoveredPathSegmentCountTask(GamesTowerDefenseTask):
    """Count path segments covered by at least one visible tower range."""

    task_id = COVERED_PATH_TASK_ID
    domain = "games"
    supported_query_ids = (COVERED_PATH_QUERY_ID,)
    fixed_query_id = COVERED_PATH_QUERY_ID


__all__ = ["GamesTowerDefenseCoveredPathSegmentCountTask"]
