"""Games lane-crossing tasks over discrete motion and route safety."""

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
from ..shared.complexity import build_games_crossing_lane_complexity
from ..shared.crossing_common import (
    SUPPORTED_CROSSING_QUERY_IDS,
    SUPPORTED_CROSSING_SCENE_VARIANTS,
    SUPPORTED_CROSSING_STYLE_VARIANTS,
    CrossingRouteOption,
    CrossingSample,
    CrossingVehicle,
    route_cell_entity_id,
    route_collision_vehicle_ids,
    route_entity_id,
    route_first_collision_tick,
    validate_crossing_sample,
    vehicle_col_at_tick,
    vehicle_entity_id,
)
from ..shared.crossing_scene import CrossingRenderParams, render_crossing_scene
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin
from ..shared.layout import resolve_games_layout_jitter
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_crossing_lane_base"
_LABELS: Tuple[str, ...] = tuple(chr(ord("A") + index) for index in range(8))


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for lane-crossing scenes."""

    lane_count_support: Tuple[int, ...] = (5, 6, 7, 8)
    row_count_support: Tuple[int, ...] = (5, 6, 7)
    collision_time_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    collision_time_max_extra_per_row: int = 1
    moving_object_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    moving_object_max_extra_per_row: int = 1
    canvas_width: int = 1000
    canvas_height: int = 780
    playfield_width_px: int = 860
    playfield_height_px: int = 680
    panel_margin_px: int = 40
    border_width_px: int = 5
    safe_band_height_px: int = 82
    vehicle_width_px: int = 70
    vehicle_height_px: int = 42
    path_width_px: int = 5
    label_font_size_px: int = 24


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one lane-crossing instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    lane_count: int
    row_count: int
    target_answer: int | None
    target_answer_support: Tuple[int, ...] | None
    target_label_index: int | None
    target_label_index_support: Tuple[int, ...] | None
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    lane_count_probabilities: Dict[str, float]
    row_count_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float] | None
    target_label_index_probabilities: Dict[str, float] | None


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "crossing")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="crossing", apply_prob=0.5)


def _target_support_key(query_id: str) -> str | None:
    """Return the answer-support key for count/value crossing queries."""

    return {
        "collision_time_value": "collision_time_support",
        "moving_object_count": "moving_object_count_support",
    }.get(str(query_id))


def _resolve_query_id(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced crossing query id."""

    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_CROSSING_QUERY_IDS,
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
    """Resolve one balanced named crossing axis."""

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
    """Resolve all semantic and visual axes for one crossing instance."""

    query_id, query_id_probabilities = _resolve_query_id(instance_seed=int(instance_seed), params=params)
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_CROSSING_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_CROSSING_STYLE_VARIANTS,
    )
    lane_count, lane_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="lane_count_support",
        explicit_key="lane_count",
        fallback_support=_DEFAULTS.lane_count_support,
        namespace=f"{TASK_ID}.lane_count",
        balanced_flag_key="balanced_lane_count_sampling",
        namespace_support_permutation=True,
    )
    row_count, row_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="row_count_support",
        explicit_key="row_count",
        fallback_support=_DEFAULTS.row_count_support,
        namespace=f"{TASK_ID}.row_count",
        balanced_flag_key="balanced_row_count_sampling",
        namespace_support_permutation=True,
    )
    target_answer: int | None = None
    target_answer_support: Tuple[int, ...] | None = None
    target_answer_probabilities: Dict[str, float] | None = None
    support_key = _target_support_key(str(query_id))
    if support_key is not None:
        target_answer, target_answer_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            support_key=str(support_key),
            explicit_key="target_answer",
            fallback_support=getattr(_DEFAULTS, str(support_key)),
            namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
            balanced_flag_key="balanced_target_answer_sampling",
            namespace_support_permutation=True,
        )
        target_answer_support = resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key=str(support_key),
            fallback=getattr(_DEFAULTS, str(support_key)),
        )
        if str(query_id) in {"collision_time_value", "moving_object_count"}:
            lane_count = max(int(lane_count), min(8, int(target_answer) + 2))
        if str(query_id) == "collision_time_value" and int(target_answer) > int(row_count):
            row_count = int(target_answer)
        if str(query_id) == "moving_object_count" and int(target_answer) > int(row_count):
            row_count = int(target_answer)

    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        lane_count=int(lane_count),
        row_count=int(row_count),
        target_answer=None if target_answer is None else int(target_answer),
        target_answer_support=target_answer_support,
        target_label_index=None,
        target_label_index_support=None,
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        lane_count_probabilities=dict(lane_count_probabilities),
        row_count_probabilities=dict(row_count_probabilities),
        target_answer_probabilities=None if target_answer_probabilities is None else dict(target_answer_probabilities),
        target_label_index_probabilities=None,
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> CrossingRenderParams:
    """Resolve crossing rendering parameters."""

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.crossing.font_family",
        params=params,
    )
    return CrossingRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        playfield_width_px=int(params.get("playfield_width_px", group_default(_RENDER_DEFAULTS, "playfield_width_px", _DEFAULTS.playfield_width_px))),
        playfield_height_px=int(params.get("playfield_height_px", group_default(_RENDER_DEFAULTS, "playfield_height_px", _DEFAULTS.playfield_height_px))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        border_width_px=int(params.get("border_width_px", group_default(_RENDER_DEFAULTS, "border_width_px", _DEFAULTS.border_width_px))),
        safe_band_height_px=int(params.get("safe_band_height_px", group_default(_RENDER_DEFAULTS, "safe_band_height_px", _DEFAULTS.safe_band_height_px))),
        vehicle_width_px=int(params.get("vehicle_width_px", group_default(_RENDER_DEFAULTS, "vehicle_width_px", _DEFAULTS.vehicle_width_px))),
        vehicle_height_px=int(params.get("vehicle_height_px", group_default(_RENDER_DEFAULTS, "vehicle_height_px", _DEFAULTS.vehicle_height_px))),
        path_width_px=int(params.get("path_width_px", group_default(_RENDER_DEFAULTS, "path_width_px", _DEFAULTS.path_width_px))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px))),
        font_family=str(font_family),
        layout_jitter_meta=resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.crossing.layout",
        ),
    )


def _row_directions(rng: Any, row_count: int) -> list[int]:
    """Return alternating row directions with a random starting direction."""

    first = -1 if int(rng.randrange(2)) == 0 else 1
    return [int(first if row % 2 == 0 else -first) for row in range(int(row_count))]


def _collision_start_for_col(
    rng: Any,
    *,
    lane_count: int,
    col: int,
    tick: int,
) -> Tuple[int, int] | None:
    """Return direction and start column that will reach col at tick."""

    directions = [-1, 1]
    rng.shuffle(directions)
    for direction in directions:
        start_col = int(col) - (int(direction) * int(tick))
        if 0 <= int(start_col) < int(lane_count):
            return int(direction), int(start_col)
    return None


def _collision_reachable_cols(*, lane_count: int, tick: int) -> Tuple[int, ...]:
    """Return route columns that can be hit by a moving object at one tick."""

    reachable: list[int] = []
    for col in range(int(lane_count)):
        if any(0 <= int(col - (direction * int(tick))) < int(lane_count) for direction in (-1, 1)):
            reachable.append(int(col))
    return tuple(reachable)


def _random_route_path(
    rng: Any,
    *,
    lane_count: int,
    row_count: int,
    required_cols_by_row: Mapping[int, Sequence[int]] | None = None,
) -> Tuple[int, ...] | None:
    """Sample one one-cell-at-a-time lane walk, optionally respecting row constraints."""

    constraints: Dict[int, set[int]] = {}
    if isinstance(required_cols_by_row, Mapping):
        for raw_row, raw_cols in required_cols_by_row.items():
            row = int(raw_row)
            if row < 0 or row >= int(row_count):
                return None
            allowed = {int(col) for col in raw_cols if 0 <= int(col) < int(lane_count)}
            if not allowed:
                return None
            constraints[int(row)] = set(allowed)

    suffix_ok: list[set[int]] = [set() for _ in range(int(row_count))]
    for row in reversed(range(int(row_count))):
        allowed_cols = constraints.get(int(row), set(range(int(lane_count))))
        if int(row) == int(row_count) - 1:
            suffix_ok[int(row)] = set(allowed_cols)
            continue
        next_ok = suffix_ok[int(row) + 1]
        suffix_ok[int(row)] = {
            int(col)
            for col in allowed_cols
            if any(int(next_col) in next_ok for next_col in (int(col) - 1, int(col), int(col) + 1))
        }
    if not suffix_ok or not suffix_ok[0]:
        return None

    candidates = sorted(suffix_ok[0])
    col = int(candidates[int(rng.randrange(len(candidates)))])
    path = [int(col)]
    for row in range(1, int(row_count)):
        candidates = [
            int(next_col)
            for next_col in (int(col) - 1, int(col), int(col) + 1)
            if int(next_col) in suffix_ok[int(row)]
        ]
        if not candidates:
            return None
        rng.shuffle(candidates)
        col = int(candidates[0])
        path.append(int(col))
    return tuple(path)


def _add_vehicle(
    vehicles: list[CrossingVehicle],
    *,
    row: int,
    start_col: int,
    direction: int,
    color_index: int,
) -> CrossingVehicle:
    """Append one vehicle and return it."""

    vehicle = CrossingVehicle(
        vehicle_id=vehicle_entity_id(len(vehicles)),
        row=int(row),
        start_col=int(start_col),
        direction=int(direction),
        color_index=int(color_index),
    )
    vehicles.append(vehicle)
    return vehicle


def _add_clutter(
    rng: Any,
    *,
    vehicles: list[CrossingVehicle],
    lane_count: int,
    row_count: int,
    row_directions: Sequence[int],
    avoid_cols_by_row: Mapping[int, set[int]],
    max_extra_per_row: int = 2,
) -> None:
    """Add nonessential traffic while avoiding specified route collisions."""

    occupied = {(int(vehicle.row), int(vehicle.start_col)) for vehicle in vehicles}
    for row in range(int(row_count)):
        extra_count = int(rng.randint(0, int(max_extra_per_row)))
        direction = int(row_directions[int(row)])
        tick = int(row + 1)
        avoid_cols = set(int(value) for value in avoid_cols_by_row.get(int(row), set()))
        candidates = [
            col
            for col in range(int(lane_count))
            if (int(row), int(col)) not in occupied
            and (
                vehicle_col_at_tick(
                    CrossingVehicle("_tmp", int(row), int(col), int(direction), 0),
                    tick=tick,
                    lane_count=int(lane_count),
                )
                not in avoid_cols
            )
        ]
        rng.shuffle(candidates)
        for col in candidates[:extra_count]:
            _add_vehicle(
                vehicles,
                row=int(row),
                start_col=int(col),
                direction=int(direction),
                color_index=int(rng.randrange(5)),
            )
            occupied.add((int(row), int(col)))


def _sample_collision_time(rng: Any, *, axes: _ResolvedAxes) -> CrossingSample | None:
    """Construct a marked route with a prescribed first collision tick."""

    lane_count = int(axes.lane_count)
    row_count = max(int(axes.row_count), int(axes.target_answer or 1))
    target_tick = int(axes.target_answer or 1)
    target_row = int(target_tick - 1)
    reachable = _collision_reachable_cols(lane_count=lane_count, tick=target_tick)
    route_path = _random_route_path(
        rng,
        lane_count=lane_count,
        row_count=row_count,
        required_cols_by_row={target_row: reachable},
    )
    if route_path is None:
        return None
    hit = _collision_start_for_col(rng, lane_count=lane_count, col=int(route_path[target_row]), tick=target_tick)
    if hit is None:
        return None
    direction, start_col = hit
    row_directions = _row_directions(rng, row_count)
    row_directions[target_row] = int(direction)
    vehicles: list[CrossingVehicle] = []
    hit_vehicle = _add_vehicle(vehicles, row=target_row, start_col=start_col, direction=direction, color_index=int(rng.randrange(5)))
    avoid = {row: {int(route_path[row])} for row in range(target_row + 1)}
    _add_clutter(
        rng,
        vehicles=vehicles,
        lane_count=lane_count,
        row_count=row_count,
        row_directions=row_directions,
        avoid_cols_by_row=avoid,
        max_extra_per_row=int(
            group_default(
                _GEN_DEFAULTS,
                "collision_time_max_extra_per_row",
                _DEFAULTS.collision_time_max_extra_per_row,
            )
        ),
    )
    route = CrossingRouteOption(route_id=route_entity_id("M"), label="M", path_cols=tuple(route_path), color_index=0)
    first_tick = route_first_collision_tick(route, tuple(vehicles), lane_count=lane_count)
    if int(first_tick or -1) != int(target_tick):
        return None
    sample = CrossingSample(
        lane_count=lane_count,
        row_count=row_count,
        query_id=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        answer=int(target_tick),
        row_directions=tuple(int(value) for value in row_directions),
        vehicles=tuple(vehicles),
        start_labels=tuple(_LABELS[:lane_count]),
        route_options=(route,),
        marked_route_label="M",
        target_start_label=None,
        target_route_label=None,
        first_collision_tick=int(target_tick),
        intersecting_vehicle_ids=(str(hit_vehicle.vehicle_id),),
        evidence_entity_ids=(str(hit_vehicle.vehicle_id), route_cell_entity_id("M", target_row)),
        target_answer=int(target_tick),
        target_label_index=None,
        construction_mode="marked_route_first_collision",
    )
    validate_crossing_sample(sample)
    return sample


def _sample_moving_object_count(rng: Any, *, axes: _ResolvedAxes) -> CrossingSample | None:
    """Construct a marked route with an exact number of intersecting vehicles."""

    lane_count = int(axes.lane_count)
    target_count = int(axes.target_answer or 1)
    row_count = max(int(axes.row_count), int(target_count))
    rows = list(range(row_count))
    rng.shuffle(rows)
    target_rows = sorted(rows[:target_count])
    route_path = _random_route_path(
        rng,
        lane_count=lane_count,
        row_count=row_count,
        required_cols_by_row={
            int(row): _collision_reachable_cols(lane_count=lane_count, tick=int(row + 1))
            for row in target_rows
        },
    )
    if route_path is None:
        return None
    row_directions = _row_directions(rng, row_count)
    vehicles: list[CrossingVehicle] = []
    for row in target_rows:
        hit = _collision_start_for_col(rng, lane_count=lane_count, col=int(route_path[row]), tick=int(row + 1))
        if hit is None:
            return None
        direction, start_col = hit
        row_directions[int(row)] = int(direction)
        _add_vehicle(vehicles, row=int(row), start_col=int(start_col), direction=int(direction), color_index=int(rng.randrange(5)))
    _add_clutter(
        rng,
        vehicles=vehicles,
        lane_count=lane_count,
        row_count=row_count,
        row_directions=row_directions,
        avoid_cols_by_row={row: {int(route_path[row])} for row in range(row_count)},
        max_extra_per_row=int(
            group_default(
                _GEN_DEFAULTS,
                "moving_object_max_extra_per_row",
                _DEFAULTS.moving_object_max_extra_per_row,
            )
        ),
    )
    route = CrossingRouteOption(route_id=route_entity_id("M"), label="M", path_cols=tuple(route_path), color_index=0)
    hit_ids = route_collision_vehicle_ids(route, tuple(vehicles), lane_count=lane_count)
    if len(hit_ids) != int(target_count):
        return None
    sample = CrossingSample(
        lane_count=lane_count,
        row_count=row_count,
        query_id=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        answer=int(target_count),
        row_directions=tuple(int(value) for value in row_directions),
        vehicles=tuple(vehicles),
        start_labels=tuple(_LABELS[:lane_count]),
        route_options=(route,),
        marked_route_label="M",
        target_start_label=None,
        target_route_label=None,
        first_collision_tick=route_first_collision_tick(route, tuple(vehicles), lane_count=lane_count),
        intersecting_vehicle_ids=tuple(hit_ids),
        evidence_entity_ids=tuple(hit_ids),
        target_answer=int(target_count),
        target_label_index=None,
        construction_mode="marked_route_intersection_count",
    )
    validate_crossing_sample(sample)
    return sample


def _sample_scene(rng: Any, *, axes: _ResolvedAxes) -> CrossingSample:
    """Construct one exact-answer crossing scene."""

    query = str(axes.query_id)
    builders = {
        "collision_time_value": _sample_collision_time,
        "moving_object_count": _sample_moving_object_count,
    }
    builder = builders.get(query)
    if builder is None:
        raise ValueError(f"unsupported crossing query_id: {query}")
    for _attempt in range(1200):
        sample = builder(rng, axes=axes)
        if sample is not None:
            return sample
    raise ValueError(f"could not construct crossing sample for query {query}")


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for crossing JSON output."""

    query = str(query_id)
    if query == "collision_time_value":
        answer_value = 4
        evidence_value = {
            "colliding_object": [421, 316, 497, 364],
            "route_cell": [408, 300, 516, 380],
        }
    else:
        answer_value = 3
        evidence_value = [[186, 282, 262, 330], [516, 404, 592, 452], [628, 528, 704, 576]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesCrossingLaneTask:
    """Return one grounded query over a lane-crossing motion scene."""

    task_id = TASK_ID
    domain = "games"
    task_group = "crossing"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))
        sampled_scene: CrossingSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(attempt_rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid crossing scene after {max_attempts} attempts")

        panel_style, panel_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace="games.crossing.panel_scene_style",
        )
        background, background_meta = make_panel_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=panel_style,
        )
        rendered_scene = render_crossing_scene(
            lane_count=int(sampled_scene.lane_count),
            row_count=int(sampled_scene.row_count),
            row_directions=tuple(int(value) for value in sampled_scene.row_directions),
            vehicles=tuple(sampled_scene.vehicles),
            start_labels=tuple(sampled_scene.start_labels),
            route_options=tuple(sampled_scene.route_options),
            marked_route_label=sampled_scene.marked_route_label,
            background=background,
            style_variant=str(sampled_scene.style_variant),
            params=render_params,
            panel_style=panel_style,
        )
        entity_bboxes = rendered_scene.render_map["entity_bboxes_px"]
        evidence_bboxes = [list(entity_bboxes[str(entity_id)]) for entity_id in sampled_scene.evidence_entity_ids]
        evidence_keyed_bboxes: Dict[str, list[float]] = {}
        if str(axes.query_id) == "collision_time_value":
            colliding_object_id = str(sampled_scene.evidence_entity_ids[0])
            route_cell_id = str(sampled_scene.evidence_entity_ids[1])
            evidence_keyed_bboxes = {
                "colliding_object": list(entity_bboxes[colliding_object_id]),
                "route_cell": list(entity_bboxes[route_cell_id]),
            }
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
                "object_description_traffic_crossing",
                "crossing_motion_rule_text",
                "answer_hint_collision_time_value",
                "evidence_hint_collision_time_value",
                "answer_hint_moving_object_count",
                "evidence_hint_moving_object_count",
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
                "crossing_motion_rule_text": str(prompt_defaults["crossing_motion_rule_text"]),
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

        if isinstance(sampled_scene.answer, str):
            answer_gt = TypedValue(type="string", value=str(sampled_scene.answer))
        else:
            answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
        if evidence_keyed_bboxes:
            evidence_gt = TypedValue(type="keyed_bbox_map", value=dict(evidence_keyed_bboxes))
        else:
            evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_crossing_lane_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            lane_count=int(sampled_scene.lane_count),
            row_count=int(sampled_scene.row_count),
            vehicle_count=len(sampled_scene.vehicles),
            route_option_count=len(sampled_scene.route_options) if sampled_scene.route_options else len(sampled_scene.start_labels),
            target_answer=0 if sampled_scene.target_answer is None else int(sampled_scene.target_answer),
            evidence_count=len(sampled_scene.evidence_entity_ids),
        )
        vehicle_trace = [
            {
                "vehicle_id": str(vehicle.vehicle_id),
                "row": int(vehicle.row),
                "start_col": int(vehicle.start_col),
                "direction": int(vehicle.direction),
                "color_index": int(vehicle.color_index),
            }
            for vehicle in sampled_scene.vehicles
        ]
        route_trace = [
            {
                "route_id": str(route.route_id),
                "label": str(route.label),
                "path_cols": [int(col) for col in route.path_cols],
                "color_index": int(route.color_index),
            }
            for route in sampled_scene.route_options
        ]
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_crossing_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "lane_count": int(sampled_scene.lane_count),
                    "row_count": int(sampled_scene.row_count),
                    "row_directions": [int(value) for value in sampled_scene.row_directions],
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
                    "lane_count": int(sampled_scene.lane_count),
                    "row_count": int(sampled_scene.row_count),
                    "target_answer": None if sampled_scene.target_answer is None else int(sampled_scene.target_answer),
                    "target_answer_support": None if axes.target_answer_support is None else [int(value) for value in axes.target_answer_support],
                    "target_label_index": None if sampled_scene.target_label_index is None else int(sampled_scene.target_label_index),
                    "target_label_index_support": None if axes.target_label_index_support is None else [int(value) for value in axes.target_label_index_support],
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "lane_count_probabilities": dict(axes.lane_count_probabilities),
                    "row_count_probabilities": dict(axes.row_count_probabilities),
                    "target_answer_probabilities": None if axes.target_answer_probabilities is None else dict(axes.target_answer_probabilities),
                    "target_label_index_probabilities": None if axes.target_label_index_probabilities is None else dict(axes.target_label_index_probabilities),
                },
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
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "lane_count": int(sampled_scene.lane_count),
                "row_count": int(sampled_scene.row_count),
                "row_directions": [int(value) for value in sampled_scene.row_directions],
                "vehicles": vehicle_trace,
                "start_labels": [str(label) for label in sampled_scene.start_labels],
                "route_options": route_trace,
                "marked_route_label": sampled_scene.marked_route_label,
                "target_start_label": sampled_scene.target_start_label,
                "target_route_label": sampled_scene.target_route_label,
                "first_collision_tick": sampled_scene.first_collision_tick,
                "intersecting_vehicle_ids": [str(value) for value in sampled_scene.intersecting_vehicle_ids],
                "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
                **(
                    {
                        "roles": {
                            "colliding_object": str(sampled_scene.evidence_entity_ids[0]),
                            "route_cell": str(sampled_scene.evidence_entity_ids[1]),
                        }
                    }
                    if evidence_keyed_bboxes
                    else {}
                ),
            },
            "projected_evidence": (
                {
                    "type": "keyed_bbox_map",
                    "keyed_bbox_map": dict(evidence_keyed_bboxes),
                    "pixel_keyed_bbox_map": dict(evidence_keyed_bboxes),
                    "bbox_set": [list(bbox) for bbox in evidence_bboxes],
                }
                if evidence_keyed_bboxes
                else {
                    "type": "bbox_set",
                    "bbox_set": [list(bbox) for bbox in evidence_bboxes],
                    "pixel_bbox_set": [list(bbox) for bbox in evidence_bboxes],
                }
            ),
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
            scene_id="crossing",
            query_id=str(axes.query_id),
        )


@register_task
class GamesCrossingCollisionTimeValueTask(FixedQueryVariantTaskMixin, GamesCrossingLaneTask):
    """Return the first collision tick for the marked route."""

    task_id = "task_games__crossing__collision_time_value"
    fixed_query_id = "collision_time_value"


@register_task
class GamesCrossingMovingObjectCountTask(FixedQueryVariantTaskMixin, GamesCrossingLaneTask):
    """Count moving objects that intersect the marked route."""

    task_id = "task_games__crossing__moving_object_count"
    fixed_query_id = "moving_object_count"


__all__ = [
    "GamesCrossingCollisionTimeValueTask",
    "GamesCrossingLaneTask",
    "GamesCrossingMovingObjectCountTask",
]
