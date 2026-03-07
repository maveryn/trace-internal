"""TRACE task implementations."""

from .registry import TASK_REGISTRY, create_task
from .geometry.measurement import angle as _task_geometry_measurement_angle
from .geometry.measurement import polygon_area as _task_geometry_measurement_polygon_area
from .geometry.measurement import polygon_perimeter as _task_geometry_measurement_polygon_perimeter
from .tile.path import shortest_path as _task_tile_path_shortest_path

__all__ = [
    "TASK_REGISTRY",
    "create_task",
]
