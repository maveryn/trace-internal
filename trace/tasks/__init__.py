"""TRACE task implementations."""

from .registry import TASK_REGISTRY, create_task
from .geometry.analytical_2d import area as _task_geometry_analytical_2d_area
from .geometry.analytical_2d import composite_area as _task_geometry_analytical_2d_composite_area
from .geometry.analytical_2d import length as _task_geometry_analytical_2d_length
from .geometry.analytical_2d import perimeter as _task_geometry_analytical_2d_perimeter
from .geometry.analytical_3d import surface_area as _task_geometry_analytical_3d_surface_area
from .geometry.analytical_3d import volume as _task_geometry_analytical_3d_volume
from .geometry.comparison import angle as _task_geometry_comparison_angle
from .geometry.comparison import area as _task_geometry_comparison_area
from .geometry.comparison import length as _task_geometry_comparison_length
from .geometry.comparison import perimeter as _task_geometry_comparison_perimeter
from .geometry.counting import angle as _task_geometry_counting_angle
from .geometry.counting import convexity as _task_geometry_counting_convexity
from .geometry.counting import quadrilateral as _task_geometry_counting_quadrilateral
from .geometry.counting import shape_type as _task_geometry_counting_shape_type
from .geometry.counting import triangle as _task_geometry_counting_triangle
from .geometry.measurement import angle as _task_geometry_measurement_angle
from .geometry.measurement import area as _task_geometry_measurement_area
from .geometry.measurement import length as _task_geometry_measurement_length
from .geometry.measurement import perimeter as _task_geometry_measurement_perimeter
from .geometry.measurement import slope as _task_geometry_measurement_slope
from .icons.counting import color as _task_icons_counting_color
from .icons.counting import orientation as _task_icons_counting_orientation
from .icons.counting import type as _task_icons_counting_type
from .icons.transformation import pair_count as _task_icons_transformation_pair_count
from .charts.composition import subset_value as _task_charts_composition_subset_value
from .charts.counting import value_count as _task_charts_counting_value_count
from .charts.distribution import boxplot_label as _task_charts_distribution_boxplot_label
from .charts.distribution import density_label as _task_charts_distribution_density_label
from .charts.distribution import histogram_count as _task_charts_distribution_histogram_count
from .charts.multiseries import pairwise_comparison_count as _task_charts_multiseries_pairwise_comparison_count
from .charts.readout import subset_value as _task_charts_readout_subset_value
from .charts.statistics import summary_label as _task_charts_statistics_summary_label
from .charts.statistics import summary_value as _task_charts_statistics_summary_value
from .charts.trend import structure_value as _task_charts_trend_structure_value
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
