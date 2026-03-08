"""TRACE task implementations."""

from .registry import TASK_REGISTRY, create_task
from .geometry.measurement_2d import angle as _task_geometry_measurement_2d_angle
from .geometry.measurement_2d import area as _task_geometry_measurement_2d_area
from .geometry.measurement_2d import length as _task_geometry_measurement_2d_length
from .geometry.measurement_2d import perimeter as _task_geometry_measurement_2d_perimeter
from .tile.path import shortest_path as _task_tile_path_shortest_path

__all__ = [
    "TASK_REGISTRY",
    "create_task",
]
