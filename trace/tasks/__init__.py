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
from .tile import count_color_components as _task_tile_count_color_components
from .tile import count_color_count as _task_tile_count_color_count
from .tile import count_largest_component_size as _task_tile_count_largest_component_size
from .tile import path_reachable_target_count as _task_tile_path_reachable_target_count
from .tile import path_shortest_path as _task_tile_path_shortest_path
from .tile import pattern_match3_run_count as _task_tile_pattern_match3_run_count
from .tile import reachability_region_size as _task_tile_reachability_region_size
from .tile import relation_min_distance as _task_tile_relation_min_distance
from .tile import symmetry_violation_count as _task_tile_symmetry_violation_count
from .tile import transition_gravity_max_drop as _task_tile_transition_gravity_max_drop

__all__ = [
    "TASK_REGISTRY",
    "create_task",
]
