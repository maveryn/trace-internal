"""Shared racing-track scene contracts for games-domain tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence, Tuple


Point = Tuple[float, float]

SUPPORTED_RACING_TRACK_QUERY_IDS: Tuple[str, ...] = (
    "closest_to_finish_label",
    "farthest_from_finish_label",
)
SUPPORTED_RACING_TRACK_AHEAD_QUERY_IDS: Tuple[str, ...] = (
    "car_ahead_count",
)
SUPPORTED_RACING_TRACK_ALL_QUERY_IDS: Tuple[str, ...] = (
    *SUPPORTED_RACING_TRACK_QUERY_IDS,
    *SUPPORTED_RACING_TRACK_AHEAD_QUERY_IDS,
)
SUPPORTED_RACING_TRACK_SCENE_VARIANTS: Tuple[str, ...] = (
    "oval_loop",
    "rounded_loop",
    "kidney_loop",
)
SUPPORTED_RACING_TRACK_STYLE_VARIANTS: Tuple[str, ...] = (
    "asphalt_day",
    "rally_sand",
    "neon_night",
    "blueprint_track",
    "paper_race",
)


@dataclass(frozen=True)
class RacingTrackCar:
    """One labeled car on the racing track."""

    car_id: str
    label: str
    progress: float
    center_px: Point
    tangent_px: Point
    remaining_distance: float


@dataclass(frozen=True)
class RacingTrackSample:
    """Generated racing-track scene and query witness."""

    query_id: str
    scene_variant: str
    style_variant: str
    track_width_px: int
    track_height_px: int
    centerline_points_px: Tuple[Point, ...]
    finish_point_px: Point
    finish_tangent_px: Point
    cars: Tuple[RacingTrackCar, ...]
    answer_label: str
    answer_entity_id: str
    annotation_entity_ids: Tuple[str, ...]
    construction_mode: str


@dataclass(frozen=True)
class RacingTrackAheadSample:
    """Generated racing-track ahead-count scene and query witness."""

    query_id: str
    scene_variant: str
    style_variant: str
    track_width_px: int
    track_height_px: int
    centerline_points_px: Tuple[Point, ...]
    finish_point_px: Point
    finish_tangent_px: Point
    cars: Tuple[RacingTrackCar, ...]
    reference_car_id: str
    answer: int
    annotation_entity_ids: Tuple[str, ...]
    construction_mode: str


def car_entity_id(index: int) -> str:
    """Return stable entity id for one visible race car."""

    return f"car_{int(index):02d}"


def remaining_distance_to_finish(progress: float) -> float:
    """Return normalized forward distance to the finish line."""

    value = float(progress) % 1.0
    if value <= 1e-9:
        return 0.0
    return round(1.0 - float(value), 6)


def normalize_vector(vector: Sequence[float]) -> Point:
    """Return one normalized 2D vector."""

    x, y = float(vector[0]), float(vector[1])
    length = math.hypot(x, y)
    if length <= 1e-9:
        return (1.0, 0.0)
    return (round(x / length, 6), round(y / length, 6))


def circular_progress_gap(progress_a: float, progress_b: float) -> float:
    """Return shortest normalized progress gap on a closed loop."""

    raw = abs((float(progress_a) % 1.0) - (float(progress_b) % 1.0))
    return min(float(raw), 1.0 - float(raw))


def progress_is_ahead_of_reference(*, reference_progress: float, object_progress: float) -> bool:
    """Return whether object is after the reference before the finish line."""

    reference = float(reference_progress) % 1.0
    obj = float(object_progress) % 1.0
    return bool(obj > reference)


def track_point(*, scene_variant: str, progress: float, track_width_px: int, track_height_px: int) -> Point:
    """Return a local centerline point for one normalized track progress."""

    width = float(track_width_px)
    height = float(track_height_px)
    cx = width * 0.5
    cy = height * 0.5
    angle = (-0.5 * math.pi) + (math.tau * (float(progress) % 1.0))
    if str(scene_variant) == "rounded_loop":
        rx = width * (0.34 + (0.028 * math.cos(4.0 * angle)))
        ry = height * (0.29 + (0.020 * math.sin(3.0 * angle)))
        x = cx + (rx * math.cos(angle))
        y = cy + (ry * math.sin(angle))
    elif str(scene_variant) == "kidney_loop":
        rx = width * 0.335
        ry = height * 0.285
        x = cx + (rx * (math.cos(angle) + (0.16 * math.sin(2.0 * angle))))
        y = cy + (ry * (math.sin(angle) + (0.12 * math.cos(2.0 * angle))))
    else:
        x = cx + ((width * 0.36) * math.cos(angle))
        y = cy + ((height * 0.30) * math.sin(angle))
    return (round(float(x), 3), round(float(y), 3))


def track_point_and_tangent(
    *,
    scene_variant: str,
    progress: float,
    track_width_px: int,
    track_height_px: int,
) -> Tuple[Point, Point]:
    """Return local centerline point and tangent for one progress value."""

    point = track_point(
        scene_variant=str(scene_variant),
        progress=float(progress),
        track_width_px=int(track_width_px),
        track_height_px=int(track_height_px),
    )
    delta = 1e-4
    before = track_point(
        scene_variant=str(scene_variant),
        progress=float(progress) - delta,
        track_width_px=int(track_width_px),
        track_height_px=int(track_height_px),
    )
    after = track_point(
        scene_variant=str(scene_variant),
        progress=float(progress) + delta,
        track_width_px=int(track_width_px),
        track_height_px=int(track_height_px),
    )
    tangent = normalize_vector((float(after[0]) - float(before[0]), float(after[1]) - float(before[1])))
    return point, tangent


def centerline_points(*, scene_variant: str, track_width_px: int, track_height_px: int, count: int = 180) -> Tuple[Point, ...]:
    """Return local centerline samples for rendering one loop."""

    return tuple(
        track_point(
            scene_variant=str(scene_variant),
            progress=float(index) / float(count),
            track_width_px=int(track_width_px),
            track_height_px=int(track_height_px),
        )
        for index in range(int(count))
    )


def validate_racing_track_sample(sample: RacingTrackSample) -> None:
    """Validate one racing-track sample contract."""

    if str(sample.query_id) not in SUPPORTED_RACING_TRACK_QUERY_IDS:
        raise ValueError(f"unsupported racing-track query_id: {sample.query_id}")
    if str(sample.scene_variant) not in SUPPORTED_RACING_TRACK_SCENE_VARIANTS:
        raise ValueError(f"unsupported racing-track scene_variant: {sample.scene_variant}")
    if str(sample.style_variant) not in SUPPORTED_RACING_TRACK_STYLE_VARIANTS:
        raise ValueError(f"unsupported racing-track style_variant: {sample.style_variant}")
    if int(sample.track_width_px) <= 0 or int(sample.track_height_px) <= 0:
        raise ValueError("racing-track dimensions must be positive")
    if len(sample.centerline_points_px) < 48:
        raise ValueError("racing-track centerline needs enough draw samples")
    if not sample.cars:
        raise ValueError("racing-track sample must include cars")
    labels = [str(car.label) for car in sample.cars]
    if len(labels) != len(set(labels)):
        raise ValueError("racing-track car labels must be unique")
    ids = [str(car.car_id) for car in sample.cars]
    if len(ids) != len(set(ids)):
        raise ValueError("racing-track car ids must be unique")
    for car in sample.cars:
        if not (0.0 < float(car.progress) < 1.0):
            raise ValueError(f"car progress must be in (0, 1): {car.car_id}")
        if abs(float(car.remaining_distance) - remaining_distance_to_finish(float(car.progress))) > 1e-5:
            raise ValueError(f"car remaining distance mismatch: {car.car_id}")

    if str(sample.query_id) == "closest_to_finish_label":
        expected = min(sample.cars, key=lambda car: float(car.remaining_distance))
    elif str(sample.query_id) == "farthest_from_finish_label":
        expected = max(sample.cars, key=lambda car: float(car.remaining_distance))
    else:
        raise ValueError(f"unsupported racing-track query_id: {sample.query_id}")
    if str(sample.answer_label) != str(expected.label):
        raise ValueError("racing-track answer label does not match extremum")
    if str(sample.answer_entity_id) != str(expected.car_id):
        raise ValueError("racing-track answer entity does not match extremum")
    if tuple(str(value) for value in sample.annotation_entity_ids) != (str(expected.car_id),):
        raise ValueError("racing-track annotation must contain only the selected car")


def validate_racing_track_ahead_sample(sample: RacingTrackAheadSample) -> None:
    """Validate one racing-track ahead-count sample contract."""

    if str(sample.query_id) not in SUPPORTED_RACING_TRACK_AHEAD_QUERY_IDS:
        raise ValueError(f"unsupported racing-track ahead query_id: {sample.query_id}")
    if str(sample.scene_variant) not in SUPPORTED_RACING_TRACK_SCENE_VARIANTS:
        raise ValueError(f"unsupported racing-track scene_variant: {sample.scene_variant}")
    if str(sample.style_variant) not in SUPPORTED_RACING_TRACK_STYLE_VARIANTS:
        raise ValueError(f"unsupported racing-track style_variant: {sample.style_variant}")
    if int(sample.track_width_px) <= 0 or int(sample.track_height_px) <= 0:
        raise ValueError("racing-track dimensions must be positive")
    if len(sample.centerline_points_px) < 48:
        raise ValueError("racing-track centerline needs enough draw samples")
    car_ids = [str(car.car_id) for car in sample.cars]
    if str(sample.reference_car_id) not in set(car_ids):
        raise ValueError("racing-track ahead sample reference car is missing")
    if len(car_ids) != len(set(car_ids)):
        raise ValueError("racing-track car ids must be unique")
    reference = next(car for car in sample.cars if str(car.car_id) == str(sample.reference_car_id))
    expected_ids = tuple(
        str(car.car_id)
        for car in sorted(sample.cars, key=lambda item: float(item.progress))
        if str(car.car_id) != str(reference.car_id)
        and progress_is_ahead_of_reference(reference_progress=reference.progress, object_progress=car.progress)
    )
    if tuple(str(value) for value in sample.annotation_entity_ids) != expected_ids:
        raise ValueError("racing-track ahead annotation ids do not match query")
    if int(sample.answer) != len(expected_ids):
        raise ValueError("racing-track ahead answer does not match annotation count")


def visible_car_trace(cars: Sequence[RacingTrackCar]) -> Tuple[dict, ...]:
    """Return trace-friendly car records."""

    return tuple(
        {
            "car_id": str(car.car_id),
            "label": str(car.label),
            "progress": round(float(car.progress), 6),
            "remaining_distance": round(float(car.remaining_distance), 6),
            "center_px_local": [round(float(car.center_px[0]), 3), round(float(car.center_px[1]), 3)],
            "tangent_px": [round(float(car.tangent_px[0]), 6), round(float(car.tangent_px[1]), 6)],
        }
        for car in cars
    )


__all__ = [
    "Point",
    "RacingTrackAheadSample",
    "RacingTrackCar",
    "RacingTrackSample",
    "SUPPORTED_RACING_TRACK_AHEAD_QUERY_IDS",
    "SUPPORTED_RACING_TRACK_ALL_QUERY_IDS",
    "SUPPORTED_RACING_TRACK_QUERY_IDS",
    "SUPPORTED_RACING_TRACK_SCENE_VARIANTS",
    "SUPPORTED_RACING_TRACK_STYLE_VARIANTS",
    "car_entity_id",
    "centerline_points",
    "circular_progress_gap",
    "normalize_vector",
    "progress_is_ahead_of_reference",
    "remaining_distance_to_finish",
    "track_point",
    "track_point_and_tangent",
    "validate_racing_track_sample",
    "validate_racing_track_ahead_sample",
    "visible_car_trace",
]
