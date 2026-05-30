"""Shared lane-crossing motion helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


SUPPORTED_CROSSING_QUERY_IDS: Tuple[str, ...] = (
    "collision_time_value",
    "moving_object_count",
)
SUPPORTED_CROSSING_SCENE_VARIANTS: Tuple[str, ...] = ("traffic_crossing",)
SUPPORTED_CROSSING_STYLE_VARIANTS: Tuple[str, ...] = (
    "day",
    "night",
    "retro",
    "paper",
    "construction",
)


@dataclass(frozen=True)
class CrossingVehicle:
    """One moving object in a horizontal traffic row."""

    vehicle_id: str
    row: int
    start_col: int
    direction: int
    color_index: int
    vehicle_kind: str = "car"


@dataclass(frozen=True)
class CrossingRouteOption:
    """One visible runner route, with one lane column per traffic row."""

    route_id: str
    label: str
    path_cols: Tuple[int, ...]
    color_index: int


@dataclass(frozen=True)
class CrossingSample:
    """Generated lane-crossing scene and task contract."""

    lane_count: int
    row_count: int
    query_id: str
    scene_variant: str
    style_variant: str
    answer: int | str
    row_directions: Tuple[int, ...]
    vehicles: Tuple[CrossingVehicle, ...]
    start_labels: Tuple[str, ...]
    route_options: Tuple[CrossingRouteOption, ...]
    marked_route_label: str | None
    target_start_label: str | None
    target_route_label: str | None
    first_collision_tick: int | None
    intersecting_vehicle_ids: Tuple[str, ...]
    evidence_entity_ids: Tuple[str, ...]
    target_answer: int | None
    target_label_index: int | None
    construction_mode: str


def vehicle_entity_id(index: int) -> str:
    """Return the stable entity id for one moving object."""

    return f"vehicle_{int(index)}"


def start_entity_id(index: int) -> str:
    """Return the stable entity id for one bottom start pad."""

    return f"start_{int(index)}"


def route_entity_id(label: str) -> str:
    """Return the stable entity id for one visible route option."""

    return f"route_{str(label)}"


def route_cell_entity_id(label: str, row: int) -> str:
    """Return the stable entity id for one route cell at a traffic row."""

    return f"route_{str(label)}_cell_{int(row)}"


def vehicle_col_at_tick(vehicle: CrossingVehicle, *, tick: int, lane_count: int) -> int | None:
    """Return a vehicle's lane column at a tick, or None if it has left the board."""

    col = int(vehicle.start_col) + (int(vehicle.direction) * int(tick))
    if 0 <= int(col) < int(lane_count):
        return int(col)
    return None


def route_collision_vehicle_ids(
    route: CrossingRouteOption,
    vehicles: Tuple[CrossingVehicle, ...],
    *,
    lane_count: int,
) -> Tuple[str, ...]:
    """Return vehicles that intersect a route at the row-crossing tick."""

    hits: list[str] = []
    for vehicle in vehicles:
        row = int(vehicle.row)
        if row < 0 or row >= len(route.path_cols):
            continue
        tick = int(row + 1)
        vehicle_col = vehicle_col_at_tick(vehicle, tick=tick, lane_count=int(lane_count))
        if vehicle_col is not None and int(vehicle_col) == int(route.path_cols[row]):
            hits.append(str(vehicle.vehicle_id))
    return tuple(sorted(set(hits)))


def route_first_collision_tick(
    route: CrossingRouteOption,
    vehicles: Tuple[CrossingVehicle, ...],
    *,
    lane_count: int,
) -> int | None:
    """Return the first tick at which a route intersects any moving object."""

    for row in range(len(route.path_cols)):
        tick = int(row + 1)
        route_col = int(route.path_cols[row])
        for vehicle in vehicles:
            if int(vehicle.row) != int(row):
                continue
            vehicle_col = vehicle_col_at_tick(vehicle, tick=tick, lane_count=int(lane_count))
            if vehicle_col is not None and int(vehicle_col) == int(route_col):
                return int(tick)
    return None


def validate_crossing_sample(sample: CrossingSample) -> None:
    """Validate the generated answer/evidence contract."""

    lane_count = int(sample.lane_count)
    row_count = int(sample.row_count)
    if lane_count < 2:
        raise ValueError("crossing lane_count must be >= 2")
    if row_count < 1:
        raise ValueError("crossing row_count must be positive")
    if len(sample.row_directions) != row_count:
        raise ValueError("row_directions length must match row_count")
    if any(int(direction) not in {-1, 1} for direction in sample.row_directions):
        raise ValueError("row directions must be -1 or 1")
    for vehicle in sample.vehicles:
        if not (0 <= int(vehicle.row) < row_count):
            raise ValueError("vehicle row out of range")
        if not (0 <= int(vehicle.start_col) < lane_count):
            raise ValueError("vehicle start_col out of range")
        if int(vehicle.direction) not in {-1, 1}:
            raise ValueError("vehicle direction must be -1 or 1")
    for route in sample.route_options:
        if len(route.path_cols) != row_count:
            raise ValueError("route path length must match row_count")
        if any(int(col) < 0 or int(col) >= lane_count for col in route.path_cols):
            raise ValueError("route path column out of range")

    vehicle_ids = {str(vehicle.vehicle_id) for vehicle in sample.vehicles}
    start_ids = {start_entity_id(index) for index in range(len(sample.start_labels))}
    route_ids = {route_entity_id(route.label) for route in sample.route_options}
    route_cell_ids = {
        route_cell_entity_id(route.label, row)
        for route in sample.route_options
        for row in range(row_count)
    }
    known_entities = vehicle_ids | start_ids | route_ids | route_cell_ids
    if not set(sample.evidence_entity_ids) <= known_entities:
        raise ValueError("crossing evidence references unknown entities")

    query = str(sample.query_id)
    if query == "collision_time_value":
        if sample.first_collision_tick is None:
            raise ValueError("collision_time_value requires a collision")
        expected_answer = int(sample.first_collision_tick)
        marked = next((route for route in sample.route_options if route.label == sample.marked_route_label), None)
        if marked is None:
            raise ValueError("collision_time_value requires marked route")
        row = int(sample.first_collision_tick) - 1
        colliders = [
            str(vehicle.vehicle_id)
            for vehicle in sample.vehicles
            if int(vehicle.row) == row
            and vehicle_col_at_tick(vehicle, tick=int(sample.first_collision_tick), lane_count=lane_count)
            == int(marked.path_cols[row])
        ]
        expected_evidence = set(colliders[:1]) | {route_cell_entity_id(marked.label, row)}
    elif query == "moving_object_count":
        marked = next((route for route in sample.route_options if route.label == sample.marked_route_label), None)
        if marked is None:
            raise ValueError("moving_object_count requires marked route")
        expected_hit_ids = route_collision_vehicle_ids(marked, sample.vehicles, lane_count=lane_count)
        expected_answer = len(expected_hit_ids)
        expected_evidence = set(expected_hit_ids)
    else:
        raise ValueError(f"unsupported crossing query_id: {query}")

    if sample.answer != expected_answer:
        raise ValueError("crossing answer does not match active query")
    if set(sample.evidence_entity_ids) != set(expected_evidence):
        raise ValueError("crossing evidence ids do not match active query")


__all__ = [
    "SUPPORTED_CROSSING_QUERY_IDS",
    "SUPPORTED_CROSSING_SCENE_VARIANTS",
    "SUPPORTED_CROSSING_STYLE_VARIANTS",
    "CrossingRouteOption",
    "CrossingSample",
    "CrossingVehicle",
    "route_cell_entity_id",
    "route_collision_vehicle_ids",
    "route_entity_id",
    "route_first_collision_tick",
    "start_entity_id",
    "validate_crossing_sample",
    "vehicle_col_at_tick",
    "vehicle_entity_id",
]
