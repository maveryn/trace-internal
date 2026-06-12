"""Racing-track ahead-count tasks for the games domain."""

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
    SUPPORTED_RACING_TRACK_AHEAD_QUERY_IDS,
    SUPPORTED_RACING_TRACK_SCENE_VARIANTS,
    SUPPORTED_RACING_TRACK_STYLE_VARIANTS,
    RacingTrackAheadSample,
    RacingTrackCar,
    car_entity_id,
    centerline_points,
    circular_progress_gap,
    progress_is_ahead_of_reference,
    remaining_distance_to_finish,
    track_point_and_tangent,
    validate_racing_track_ahead_sample,
)
from .shared.output import build_racing_track_output_parts
from .shared.rendering import RacingTrackRenderParams, render_racing_track_scene
from ..shared.sampling import resolve_games_named_axis


SCENE_ID = "racing_track"
TASK_ID = "task_games__racing_track__ahead_object_count"
PUBLIC_TASK_ID = "task_games__racing_track__ahead_object_count"
CAR_AHEAD_QUERY_ID = "car_ahead_count"
CAR_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G")
FORBIDDEN_PROGRESS_BANDS: Tuple[Tuple[float, float], ...] = ((0.49, 0.56),)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for racing-track ahead-count scenes."""

    ahead_car_count_support: Tuple[int, ...] = (5, 6, 7)
    target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    canvas_width: int = 1000
    canvas_height: int = 760
    track_width_px: int = 820
    track_height_px: int = 600
    road_width_px: int = 72
    road_border_width_px: int = 8
    car_length_px: int = 48
    car_width_px: int = 28
    marked_outline_width_px: int = 5
    label_font_size_px: int = 24
    min_progress_gap: float = 0.045


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one racing-track ahead instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    car_count: int
    target_answer: int
    car_count_support: Tuple[int, ...]
    target_answer_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    car_count_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


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
    """Resolve semantic and visual axes for one racing-track ahead instance."""

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
        support_key="ahead_car_count_support",
        explicit_key="car_count",
        fallback_support=_DEFAULTS.ahead_car_count_support,
        namespace=f"{TASK_ID}.car_count",
        balanced_flag_key="balanced_car_count_sampling",
        namespace_support_permutation=True,
    )
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="target_answer_support",
        explicit_key="target_answer",
        fallback_support=_DEFAULTS.target_answer_support,
        namespace=f"{TASK_ID}.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    car_count = max(int(car_count), int(target_answer) + 1)
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        car_count=int(car_count),
        target_answer=int(target_answer),
        car_count_support=resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key="ahead_car_count_support",
            fallback=_DEFAULTS.ahead_car_count_support,
        ),
        target_answer_support=resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key="target_answer_support",
            fallback=_DEFAULTS.target_answer_support,
        ),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        car_count_probabilities=dict(car_count_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
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
        marked_outline_width_px=int(params.get("marked_outline_width_px", group_default(_RENDER_DEFAULTS, "marked_outline_width_px", _DEFAULTS.marked_outline_width_px))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px))),
        font_family=str(font_family),
        layout_jitter_meta=resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.racing_track.ahead.layout_jitter",
        ),
    )


def _progress_allowed(progress: float, *, existing: Sequence[float], min_gap: float) -> bool:
    """Return whether one progress value is visually separated from existing objects."""

    value = float(progress)
    if not (0.045 <= value <= 0.955):
        return False
    for low, high in FORBIDDEN_PROGRESS_BANDS:
        if float(low) <= value <= float(high):
            return False
    return all(circular_progress_gap(value, other) >= float(min_gap) for other in existing)


def _sample_progress_values(
    *,
    rng,
    count: int,
    existing: Sequence[float],
    min_gap: float,
) -> Tuple[float, ...]:
    """Sample distinct progress values away from the finish and direction arrow."""

    values = [float(value) for value in existing]
    sampled: list[float] = []
    for _slot in range(int(count)):
        for _attempt in range(500):
            candidate = round(rng.uniform(0.055, 0.945), 6)
            if _progress_allowed(candidate, existing=values, min_gap=float(min_gap)):
                sampled.append(float(candidate))
                values.append(float(candidate))
                break
        else:
            raise ValueError("failed to sample separated racing-track progress values")
    return tuple(sampled)


def _sample_ranked_progress_values(
    *,
    rng,
    count: int,
    min_gap: float,
) -> Tuple[float, ...]:
    """Sample and sort progress values for exact rank-based car counts."""

    for _ in range(300):
        values = _sample_progress_values(rng=rng, count=int(count), existing=(), min_gap=float(min_gap))
        ordered = tuple(sorted(float(value) for value in values))
        if len(ordered) == int(count):
            return ordered
    raise ValueError("failed to sample ranked racing-track progress values")


def _entity_point(*, scene_variant: str, progress: float, render_params: RacingTrackRenderParams) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """Return local point and tangent for a track entity."""

    return track_point_and_tangent(
        scene_variant=str(scene_variant),
        progress=float(progress),
        track_width_px=int(render_params.track_width_px),
        track_height_px=int(render_params.track_height_px),
    )


def _make_car(
    *,
    index: int,
    label: str,
    progress: float,
    axes: _ResolvedAxes,
    render_params: RacingTrackRenderParams,
) -> RacingTrackCar:
    """Build one symbolic car."""

    center, tangent = _entity_point(
        scene_variant=str(axes.scene_variant),
        progress=float(progress),
        render_params=render_params,
    )
    return RacingTrackCar(
        car_id=car_entity_id(int(index)),
        label=str(label),
        progress=float(progress),
        center_px=center,
        tangent_px=tangent,
        remaining_distance=remaining_distance_to_finish(float(progress)),
    )


def _sample_car_query_scene(
    *,
    rng,
    axes: _ResolvedAxes,
    render_params: RacingTrackRenderParams,
    min_gap: float,
) -> Tuple[Tuple[RacingTrackCar, ...], str, Tuple[str, ...]]:
    """Sample a car-ahead count scene with an exact answer."""

    ordered_progress = _sample_ranked_progress_values(
        rng=rng,
        count=int(axes.car_count),
        min_gap=float(min_gap),
    )
    reference_rank = int(axes.car_count) - 1 - int(axes.target_answer)
    reference_progress = float(ordered_progress[int(reference_rank)])
    labels = list(CAR_LABELS[: int(axes.car_count)])
    rng.shuffle(labels)
    cars = tuple(
        _make_car(
            index=index,
            label=str(label),
            progress=float(progress),
            axes=axes,
            render_params=render_params,
        )
        for index, (label, progress) in enumerate(zip(labels, ordered_progress))
    )
    reference_car = next(car for car in cars if abs(float(car.progress) - float(reference_progress)) <= 1e-9)
    annotation_ids = tuple(
        str(car.car_id)
        for car in sorted(cars, key=lambda item: float(item.progress))
        if str(car.car_id) != str(reference_car.car_id)
        and progress_is_ahead_of_reference(reference_progress=reference_car.progress, object_progress=car.progress)
    )

    return cars, str(reference_car.car_id), annotation_ids


def _sample_scene(
    *,
    rng,
    axes: _ResolvedAxes,
    render_params: RacingTrackRenderParams,
    params: Mapping[str, Any],
) -> RacingTrackAheadSample:
    """Construct one racing-track ahead-count scene."""

    min_gap = float(params.get("min_progress_gap", group_default(_GEN_DEFAULTS, "min_progress_gap", _DEFAULTS.min_progress_gap)))
    cars, reference_car_id, annotation_ids = _sample_car_query_scene(
        rng=rng,
        axes=axes,
        render_params=render_params,
        min_gap=float(min_gap),
    )
    finish_point, finish_tangent = track_point_and_tangent(
        scene_variant=str(axes.scene_variant),
        progress=0.0,
        track_width_px=int(render_params.track_width_px),
        track_height_px=int(render_params.track_height_px),
    )
    sample = RacingTrackAheadSample(
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
        reference_car_id=str(reference_car_id),
        answer=int(len(annotation_ids)),
        annotation_entity_ids=tuple(annotation_ids),
        construction_mode="sample_forward_interval_count_from_marked_car",
    )
    validate_racing_track_ahead_sample(sample)
    return sample


def _build_prompt_json_examples() -> Tuple[str, str]:
    """Return prompt examples for racing-track ahead-count JSON output."""

    answer_value = 2
    annotation_value = [[486, 214], [612, 331]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


@register_task
class GamesRacingTrackAheadObjectCountTask:
    """Count cars ahead of a marked car before the finish."""

    task_id = PUBLIC_TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_RACING_TRACK_AHEAD_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_id_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_RACING_TRACK_AHEAD_QUERY_IDS,
            default_query_id=CAR_AHEAD_QUERY_ID,
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
            namespace="games.racing_track.ahead.font",
            params=task_params,
        )
        render_params = _render_params(task_params, instance_seed=int(instance_seed), font_family=str(font_family))

        sampled_scene: RacingTrackAheadSample | None = None
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
            raise RuntimeError(f"{self.task_id} failed to generate a valid racing-track ahead-count scene after {max_attempts} attempts")

        object_description_key = f"object_description_{str(axes.scene_variant)}_ahead_count"
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
            rule_text_key="ahead_rule_text",
            answer_hint_key=answer_hint_key,
            annotation_hint_key=annotation_hint_key,
            json_examples=(json_example, json_example_answer_only),
            query_params={
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "car_count": len(sampled_scene.cars),
                "target_answer": int(axes.target_answer),
                "car_count_support": [int(value) for value in axes.car_count_support],
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "query_id_probabilities": dict(axes.query_id_probabilities),
                "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                "style_variant_probabilities": dict(axes.style_variant_probabilities),
                "car_count_probabilities": dict(axes.car_count_probabilities),
                "target_answer_probabilities": dict(axes.target_answer_probabilities),
            },
            relation_extra={"reference_car_id": str(sampled_scene.reference_car_id)},
            execution_extra={
                "reference_car_id": str(sampled_scene.reference_car_id),
                "answer": int(sampled_scene.answer),
            },
            marked_car_id=str(sampled_scene.reference_car_id),
        )

        answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
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


__all__ = ["GamesRacingTrackAheadObjectCountTask"]
