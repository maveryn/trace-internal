"""Compatibility facade for street-intersection rendering helpers.

Renderer implementations live in family-specific modules in this package. Keep
this module as the stable import surface for street tasks and tests.
"""

from __future__ import annotations

from .intersection_rendering_common import *  # noqa: F403
from .intersection_road_rendering import *  # noqa: F403
from .intersection_vehicle_rendering import *  # noqa: F403
from .intersection_fixture_rendering import *  # noqa: F403
from .intersection_pedestrian_rendering import *  # noqa: F403
from .intersection_building_rendering import *  # noqa: F403
from .intersection_landscape_rendering import *  # noqa: F403
from .intersection_object_rendering import *  # noqa: F403


__all__ = [
    'VEHICLE_OBJECT_TYPES',
    'PEDESTRIAN_OBJECT_TYPES',
    'STREET_BUILDING_CONTEXT_OBJECT_TYPES',
    'STREET_FIXED_BUILDING_STYLE_BY_OBJECT_TYPE',
    'STREET_FULL_BLEED_FALLBACK_EXTENT_MULTIPLIER',
    '_street_object_name',
    '_street_object_fill_rgb',
    '_base_street_object_dimensions',
    '_fixed_building_style_for_street_object',
    '_apply_street_building_style',
    '_dimensions_for_orientation',
    '_orientation_axis_for_xy',
    '_missing_arm_for_layout',
    '_arm_is_present',
    '_draw_shadow',
    '_screen_points_bbox',
    '_draw_projected_limb',
    '_screen_line_bbox',
    '_screen_rect_bbox',
    '_draw_screen_pole',
    '_stable_palette_index',
    '_upright_screen_basis',
    '_world_polygon',
    '_draw_world_rect',
    '_floor_polygon_area_xy',
    '_line_intersection_xy',
    '_dedupe_polygon_points_xy',
    '_clip_polygon_to_convex_floor',
    '_fallback_floor_polygon_xy',
    '_visible_floor_polygon_xy',
    '_canvas_floor_polygon_available',
    '_floor_bounds_xy',
    '_draw_clipped_floor_rect',
    '_draw_crosswalks',
    '_draw_lane_markings',
    '_road_rects_for_layout',
    '_draw_street_shell',
    '_draw_vehicle_projected_details',
    '_draw_vehicle_object',
    '_draw_scooter_object',
    '_draw_bicycle_object',
    '_draw_motorcycle_object',
    '_draw_fire_hydrant_object',
    '_draw_trash_bin_object',
    '_draw_mailbox_object',
    '_draw_construction_barrier_object',
    '_draw_road_barrel_object',
    '_draw_traffic_cone_object',
    '_draw_traffic_light_context_object',
    '_draw_street_sign_context_object',
    '_draw_pedestrian_object',
    '_draw_building_face_rect',
    '_draw_building_window_grid',
    '_draw_building_vertical_glass',
    '_draw_building_horizontal_bands',
    '_draw_retail_front',
    '_draw_shopfront',
    '_draw_styled_building_object',
    '_draw_street_evergreen_tree_object',
    '_draw_street_bush_object',
    '_draw_street_bench_object',
    '_draw_context_object',
    '_draw_candidate_object',
]
