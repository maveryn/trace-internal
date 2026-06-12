"""Racing-track distance-to-finish tasks for the games domain."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    load_scene_generation_rendering_prompt_defaults,
)
from ...shared.fixed_query import select_task_query_id
from ...shared.font_assets import sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.layout import resolve_games_layout_jitter
from .shared.common import (
    SUPPORTED_RACING_TRACK_QUERY_IDS,
    SUPPORTED_RACING_TRACK_SCENE_VARIANTS,
    SUPPORTED_RACING_TRACK_STYLE_VARIANTS,
    RacingTrackCar,
    RacingTrackSample,
    car_entity_id,
    centerline_points,
    circular_progress_gap,
    remaining_distance_to_finish,
    track_point_and_tangent,
    validate_racing_track_sample,
)
from .shared.output import build_racing_track_output_parts
from .shared.rendering import RacingTrackRenderParams, render_racing_track_scene
from ..shared.sampling import resolve_games_named_axis


SCENE_ID = "racing_track"
TASK_ID = "task_games__racing_track__finish_distance_extremum_label"
PUBLIC_TASK_ID = "task_games__racing_track__finish_distance_extremum_label"
CLOSEST_QUERY_ID = "closest_to_finish_label"
FARTHEST_QUERY_ID = "farthest_from_finish_label"
CAR_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for racing-track scenes."""

    car_count_support: Tuple[int, ...] = (4, 5, 6, 7)
    canvas_width: int = 1000
    canvas_height: int = 760
    track_width_px: int = 820
    track_height_px: int = 600
    road_width_px: int = 72
    road_border_width_px: int = 8
    car_length_px: int = 48
    car_width_px: int = 28
    label_font_size_px: int = 24
    min_progress_gap: float = 0.055
    min_remaining_gap: float = 0.08


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one racing-track instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    car_count: int
    car_count_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    car_count_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
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
    """Resolve one balanced named racing-track axis."""

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


def _resolve_axes(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    query_id: str,
    query_id_probabilities: Mapping[str, float],
) -> _ResolvedAxes:
    """Resolve semantic and visual axes for one racing-track instance."""

    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_RACING_TRACK_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_RACING_TRACK_STYLE_VARIANTS,
    )
    car_count, car_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="car_count_support",
        explicit_key="car_count",
        fallback_support=_DEFAULTS.car_count_support,
        namespace=f"{TASK_ID}.car_count",
        balanced_flag_key="balanced_car_count_sampling",
        namespace_support_permutation=True,
    )
    car_count_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="car_count_support",
        fallback=_DEFAULTS.car_count_support,
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        car_count=int(car_count),
        car_count_support=tuple(int(value) for value in car_count_support),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        car_count_probabilities=dict(car_count_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int, font_family: str) -> RacingTrackRenderParams:
    """Resolve racing-track rendering parameters."""

    return RacingTrackRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        track_width_px=int(params.get("track_width_px", group_default(_RENDER_DEFAULTS, "track_width_px", _DEFAULTS.track_width_px))),
        track_height_px=int(params.get("track_height_px", group_default(_RENDER_DEFAULTS, "track_height_px", _DEFAULTS.track_height_px))),
        road_width_px=int(params.get("road_width_px", group_default(_RENDER_DEFAULTS, "road_width_px", _DEFAULTS.road_width_px))),
        road_border_width_px=int(params.get("road_border_width_px", group_default(_RENDER_DEFAULTS, "road_border_width_px", _DEFAULTS.road_border_width_px))),
        car_length_px=int(params.get("car_length_px", group_default(_RENDER_DEFAULTS, "car_length_px", _DEFAULTS.car_length_px))),
        car_width_px=int(params.get("car_width_px", group_default(_RENDER_DEFAULTS, "car_width_px", _DEFAULTS.car_width_px))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px))),
        font_family=str(font_family),
        layout_jitter_meta=resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.racing_track.layout_jitter",
        ),
    )


def _sample_progresses(
    *,
    rng,
    query_id: str,
    car_count: int,
    min_progress_gap: float,
    min_remaining_gap: float,
) -> Tuple[float, ...]:
    """Sample car progress values with a unique closest/farthest answer."""

    for _ in range(500):
        if str(query_id) == CLOSEST_QUERY_ID:
            answer_progress = rng.uniform(0.88, 0.96)
            trap_progress = rng.uniform(0.04, 0.12)
        else:
            answer_progress = rng.uniform(0.04, 0.12)
            trap_progress = rng.uniform(0.88, 0.96)
        progress_values = [round(float(answer_progress), 6), round(float(trap_progress), 6)]
        candidate_bands = (
            (0.20, 0.32),
            (0.38, 0.46),
            (0.60, 0.72),
            (0.76, 0.82),
        )
        for _slot in range(max(0, int(car_count) - 2)):
            placed = False
            for _attempt in range(120):
                low, high = rng.choice(candidate_bands)
                candidate = round(rng.uniform(float(low), float(high)), 6)
                if all(circular_progress_gap(candidate, existing) >= float(min_progress_gap) for existing in progress_values):
                    progress_values.append(float(candidate))
                    placed = True
                    break
            if not placed:
                break
        if len(progress_values) != int(car_count):
            continue
        remaining = [remaining_distance_to_finish(value) for value in progress_values]
        sorted_remaining = sorted(float(value) for value in remaining)
        min_gap = min(abs(float(a) - float(b)) for a, b in zip(sorted_remaining, sorted_remaining[1:]))
        if float(min_gap) < float(min_remaining_gap):
            continue
        if str(query_id) == CLOSEST_QUERY_ID and remaining.index(min(remaining)) != 0:
            continue
        if str(query_id) == FARTHEST_QUERY_ID and remaining.index(max(remaining)) != 0:
            continue
        return tuple(float(value) for value in progress_values)
    raise ValueError("failed to sample racing-track car positions")


def _sample_scene(
    *,
    rng,
    axes: _ResolvedAxes,
    render_params: RacingTrackRenderParams,
    params: Mapping[str, Any],
) -> RacingTrackSample:
    """Construct one racing-track scene."""

    min_progress_gap = float(params.get("min_progress_gap", group_default(_GEN_DEFAULTS, "min_progress_gap", _DEFAULTS.min_progress_gap)))
    min_remaining_gap = float(params.get("min_remaining_gap", group_default(_GEN_DEFAULTS, "min_remaining_gap", _DEFAULTS.min_remaining_gap)))
    progress_values = list(
        _sample_progresses(
            rng=rng,
            query_id=str(axes.query_id),
            car_count=int(axes.car_count),
            min_progress_gap=float(min_progress_gap),
            min_remaining_gap=float(min_remaining_gap),
        )
    )
    labels = list(CAR_LABELS[: int(axes.car_count)])
    rng.shuffle(labels)
    paired = list(zip(labels, progress_values))
    rng.shuffle(paired)

    cars: list[RacingTrackCar] = []
    for index, (label, progress) in enumerate(paired):
        center, tangent = track_point_and_tangent(
            scene_variant=str(axes.scene_variant),
            progress=float(progress),
            track_width_px=int(render_params.track_width_px),
            track_height_px=int(render_params.track_height_px),
        )
        cars.append(
            RacingTrackCar(
                car_id=car_entity_id(index),
                label=str(label),
                progress=float(progress),
                center_px=center,
                tangent_px=tangent,
                remaining_distance=remaining_distance_to_finish(float(progress)),
            )
        )
    if str(axes.query_id) == CLOSEST_QUERY_ID:
        answer_car = min(cars, key=lambda car: float(car.remaining_distance))
    else:
        answer_car = max(cars, key=lambda car: float(car.remaining_distance))
    finish_point, finish_tangent = track_point_and_tangent(
        scene_variant=str(axes.scene_variant),
        progress=0.0,
        track_width_px=int(render_params.track_width_px),
        track_height_px=int(render_params.track_height_px),
    )
    sample = RacingTrackSample(
        mode=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        track_width_px=int(render_params.track_width_px),
        track_height_px=int(render_params.track_height_px),
        centerline_points_px=centerline_points(
            scene_variant=str(axes.scene_variant),
            track_width_px=int(render_params.track_width_px),
            track_height_px=int(render_params.track_height_px),
        ),
        finish_point_px=finish_point,
        finish_tangent_px=finish_tangent,
        cars=tuple(cars),
        answer_label=str(answer_car.label),
        answer_entity_id=str(answer_car.car_id),
        annotation_entity_ids=(str(answer_car.car_id),),
        construction_mode="sample_closed_loop_extremal_finish_distance",
    )
    validate_racing_track_sample(sample)
    return sample


def _build_prompt_json_examples() -> Tuple[str, str]:
    """Return prompt examples for racing-track JSON output."""

    answer_value = "C"
    annotation_value = [[486, 214]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


@register_task
class GamesRacingTrackFinishDistanceExtremumTask:
    """Select the car closest or farthest from the finish along the track."""

    task_id = PUBLIC_TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_RACING_TRACK_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_id_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_RACING_TRACK_QUERY_IDS,
            default_query_id=CLOSEST_QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        axes = _resolve_axes(
            int(instance_seed),
            params=task_params,
            query_id=str(query_id),
            query_id_probabilities=query_id_probabilities,
        )
        font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace="games.racing_track.font",
            params=task_params,
        )
        render_params = _render_params(task_params, instance_seed=int(instance_seed), font_family=str(font_family))

        sampled_scene: RacingTrackSample | None = None
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
            raise RuntimeError(f"{self.task_id} failed to generate a valid racing-track scene after {max_attempts} attempts")

        object_description_key = f"object_description_{str(axes.scene_variant)}"
        answer_hint_key = f"answer_hint_{str(axes.query_id)}"
        annotation_hint_key = f"annotation_hint_{str(axes.query_id)}"
        json_example, json_example_answer_only = _build_prompt_json_examples()
        output_parts = build_racing_track_output_parts(
            domain=self.domain,
            scene_id=self.scene_id,
            instance_seed=int(instance_seed),
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            prompt_defaults=_PROMPT_DEFAULTS,
            render_params=render_params,
            sampled_scene=sampled_scene,
            query_id=str(axes.query_id),
            object_description_key=object_description_key,
            rule_text_key="distance_rule_text",
            answer_hint_key=answer_hint_key,
            annotation_hint_key=annotation_hint_key,
            json_examples=(json_example, json_example_answer_only),
            query_params={
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "car_count": len(sampled_scene.cars),
                "car_count_support": [int(value) for value in axes.car_count_support],
                "query_id_probabilities": dict(axes.query_id_probabilities),
                "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                "style_variant_probabilities": dict(axes.style_variant_probabilities),
                "car_count_probabilities": dict(axes.car_count_probabilities),
            },
            relation_extra={
                "finish_point_px_local": [
                    round(float(sampled_scene.finish_point_px[0]), 3),
                    round(float(sampled_scene.finish_point_px[1]), 3),
                ],
            },
            execution_extra={
                "answer_label": str(sampled_scene.answer_label),
                "answer_entity_id": str(sampled_scene.answer_entity_id),
            },
        )

        answer_gt = TypedValue(type="string", value=str(sampled_scene.answer_label))
        annotation_gt = TypedValue(type="point_set", value=[list(point) for point in output_parts.annotation_points])
        return TaskOutput(
            prompt=str(output_parts.prompt),
            prompt_variants=dict(output_parts.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=output_parts.image,
            image_id="img0",
            trace_payload=dict(output_parts.trace_payload),
            task_versions=default_task_versions(),
            scene_id=self.scene_id,
            query_id=str(axes.query_id),
        )


__all__ = ["GamesRacingTrackFinishDistanceExtremumTask"]
