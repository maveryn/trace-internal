"""TRACE task implementations."""

from .registry import TASK_REGISTRY, create_task
from .geometry.analytical_2d import area as _task_geometry_analytical_2d_area
from .geometry.analytical_2d import length as _task_geometry_analytical_2d_length
from .geometry.analytical_3d import surface_area as _task_geometry_analytical_3d_surface_area
from .geometry.analytical_3d import volume as _task_geometry_analytical_3d_volume
from .geometry.measurement import angle as _task_geometry_measurement_angle
from .geometry.measurement import area as _task_geometry_measurement_area
from .geometry.measurement import length as _task_geometry_measurement_length
from .geometry.measurement import perimeter as _task_geometry_measurement_perimeter
from .geometry.measurement import slope as _task_geometry_measurement_slope
from .tile.count import color_components as _task_tile_count_color_components
from .tile.count import color_count as _task_tile_count_color_count
from .tile.count import largest_component_size as _task_tile_count_largest_component_size
from .tile.path import shortest_path as _task_tile_path_shortest_path
from .tile.pattern import run_count as _task_tile_pattern_match3_run_count
from .tile.reachability import reachable_count as _task_tile_reachability_reachable_count
from .tile.symmetry import violation_count as _task_tile_symmetry_violation_count
from .tile.topology import hole_count as _task_tile_topology_hole_count
from .tile.transition import gravity_max_drop as _task_tile_transition_gravity_max_drop

__all__ = [
    "TASK_REGISTRY",
    "create_task",
]
