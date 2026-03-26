"""TRACE task implementations."""

from .registry import TASK_REGISTRY, create_task
from .geometry.analytical_2d import area as _task_geometry_analytical_2d_area
from .geometry.analytical_2d import composite_area as _task_geometry_analytical_2d_composite_area
from .geometry.analytical_2d import length as _task_geometry_analytical_2d_length
from .geometry.analytical_2d import perimeter as _task_geometry_analytical_2d_perimeter
from .geometry.analytical_3d import surface_area as _task_geometry_analytical_3d_surface_area
from .geometry.analytical_3d import volume as _task_geometry_analytical_3d_volume
from .geometry.comparison import angle as _task_geometry_comparison_angle
from .geometry.comparison import length as _task_geometry_comparison_length
from .geometry.measurement import angle as _task_geometry_measurement_angle
from .geometry.measurement import area as _task_geometry_measurement_area
from .geometry.measurement import length as _task_geometry_measurement_length
from .geometry.measurement import perimeter as _task_geometry_measurement_perimeter
from .geometry.measurement import slope as _task_geometry_measurement_slope
from .tile.path import shortest_path as _task_tile_path_shortest_path

__all__ = [
    "TASK_REGISTRY",
    "create_task",
]
