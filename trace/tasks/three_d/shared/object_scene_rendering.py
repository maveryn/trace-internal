"""Shared object-scene rendering primitives for synthetic three_d scenes."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ...shared.text_legibility import draw_text_traced
from .camera_projection import (
    CameraSpec as _CameraSpec,
    ProjectionFrame as _ProjectionFrame,
    canvas_floor_polygon_xy as _canvas_floor_polygon_xy,
    distance as _distance,
    grid_values_for_range as _grid_values_for_range,
    polygon_axis_line_segment as _polygon_axis_line_segment,
    project_xy as _project_xy,
)
from .object_scene_primitives import (
    _arrow_footprint_points,
    _bbox_from_screen_points,
    _bbox_union,
    _draw_box_object,
    _draw_box_parts_object,
    _draw_cone_object,
    _draw_cylinder_object,
    _draw_footprint_prism_object,
    _draw_half_cylinder_object,
    _draw_line,
    _draw_polyline,
    _draw_pyramid_object,
    _draw_sphere_object,
    _draw_torus_object,
    _draw_upright_profile_object,
    _draw_wedge_object,
    _face_distance,
    _gear_footprint_points,
    _heart_profile_points,
    _hexagon_footprint_points,
    _object_vertices,
    _oval_profile_points,
    _project_face,
    _radius_px_for_object,
    _shade,
    _star_footprint_points,
    _sub_box_spec,
    _tint,
    _upright_profile_world_points,
    _upright_screen_points,
)
from .object_scene_glyphs_symbolic import (
    _draw_shield_object,
    _draw_heart_object,
    _draw_diamond_object,
    _draw_sword_object,
    _draw_key_object,
    _draw_crown_object,
    _draw_hourglass_object,
    _draw_anchor_object,
    _draw_horseshoe_object,
    _draw_hammer_object,
    _draw_bell_object,
    _draw_trophy_object,
    _draw_open_book_object,
    _draw_dumbbell_object,
    _draw_mushroom_object,
    _draw_lantern_object,
    _draw_wrench_object,
)
from .object_scene_glyphs_household import (
    _draw_padlock_object,
    _draw_magnifying_glass_object,
    _draw_candle_object,
    _draw_scroll_object,
    _draw_paint_brush_object,
    _draw_paint_palette_object,
    _draw_goblet_object,
    _draw_teapot_object,
    _draw_watering_can_object,
    _draw_basket_object,
    _draw_mail_envelope_object,
    _draw_camera_object,
    _draw_compass_object,
    _draw_flask_object,
    _draw_test_tube_rack_object,
    _draw_scroll_map_object,
    _draw_microphone_object,
    _draw_stopwatch_object,
)
from .object_scene_glyphs_nature_apparel import (
    _draw_apple_object,
    _draw_carrot_object,
    _draw_pear_object,
    _draw_fish_object,
    _draw_leaf_object,
    _draw_feather_object,
    _draw_shoe_object,
    _draw_glove_object,
    _draw_hat_object,
    _draw_helmet_object,
    _draw_cup_object,
    _draw_bottle_object,
    _draw_vase_object,
    _draw_umbrella_object,
)
from .object_scene_glyphs_tools_devices import (
    _draw_pencil_object,
    _draw_thumb_pin_object,
    _draw_flat_rect_object,
    _draw_ticket_tag_object,
    _draw_puzzle_piece_object,
    _draw_candy_disc_object,
    _draw_cd_object,
    _draw_berry_object,
    _draw_marble_object,
    _draw_bead_object,
    _draw_dot_object,
    _draw_button_object,
    _draw_plate_object,
    _draw_bowl_object,
    _draw_screw_object,
    _draw_bolt_object,
    _draw_hex_nut_object,
    _draw_washer_object,
    _draw_paper_clip_object,
    _draw_u_bolt_object,
    _draw_nail_object,
    _draw_rod_object,
    _draw_stick_object,
    _draw_straw_object,
    _draw_tube_object,
    _draw_clip_object,
    _draw_socket_object,
    _draw_magnet_object,
    _draw_heater_object,
    _draw_flower_object,
    _draw_plant_pot_object,
    _draw_glass_object,
    _draw_jar_object,
    _draw_can_object,
    _draw_lid_object,
    _draw_pillow_cushion_object,
    _draw_stool_object,
    _draw_drawer_object,
    _draw_cap_object,
    _draw_bucket_object,
    _draw_tray_object,
    _draw_coaster_object,
    _draw_rose_object,
    _draw_banana_object,
    _draw_tomato_object,
    _draw_peanut_object,
    _draw_coffee_bean_object,
    _draw_hook_object,
    _draw_bracket_object,
    _draw_battery_object,
    _draw_tape_roll_object,
    _draw_bag_object,
    _draw_chess_piece_object,
    _draw_hanger_object,
    _draw_light_bulb_object,
    _draw_egg_object,
    _draw_chili_object,
    _draw_fork_object,
    _draw_knife_object,
    _draw_spoon_object,
    _draw_calculator_object,
    _draw_dice_object,
    _draw_kite_object,
    _draw_cactus_object,
)
from .object_scene_glyphs_misc import (
    _draw_guitar_object,
    _draw_drum_object,
    _draw_pliers_object,
    _draw_telescope_object,
    _draw_ruler_object,
    _draw_pickaxe_object,
    _draw_paint_roller_object,
    _draw_tape_measure_object,
    _draw_remote_control_object,
    _draw_plug_object,
    _draw_wallet_object,
    _draw_purse_object,
    _draw_sunglasses_object,
    _draw_violin_object,
    _draw_trumpet_object,
    _draw_donut_object,
    _draw_pretzel_object,
    _draw_lollipop_object,
    _draw_ice_cream_cone_object,
    _draw_soap_bar_object,
    _draw_clock_object,
)
from .object_scene_glyphs_large import (
    _draw_arch_object,
    _draw_table_object,
    _draw_shelf_object,
    _draw_open_box_object,
    _draw_refrigerator_object,
    _draw_washing_machine_object,
    _draw_vending_machine_object,
    _draw_trash_bin_object,
    _draw_bench_object,
    _draw_piano_object,
    _draw_locker_object,
    _draw_cabinet_object,
    _draw_sofa_object,
    _draw_barrel_object,
    _draw_chair_object,
)


def _draw_room(
    draw: ImageDraw.ImageDraw,
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    render_params: Any,
    scene_variant: str,
) -> Tuple[List[float], List[Dict[str, Any]]]:
    extent = float(render_params.room_extent)
    floor = [
        _project_xy((-extent, -extent, 0.0), camera, frame),
        _project_xy((extent, -extent, 0.0), camera, frame),
        _project_xy((extent, extent, 0.0), camera, frame),
        _project_xy((-extent, extent, 0.0), camera, frame),
    ]
    if str(scene_variant) == "tabletop_room":
        floor_fill = (226, 218, 199)
        border_rgb = (128, 108, 86)
        grid_rgb = (190, 176, 151)
    elif str(scene_variant) == "studio_platform":
        floor_fill = (231, 235, 244)
        border_rgb = (88, 100, 118)
        grid_rgb = (181, 192, 211)
    else:
        floor_fill = render_params.floor_rgb
        border_rgb = render_params.edge_rgb
        grid_rgb = render_params.grid_rgb
    full_bleed = bool(render_params.full_bleed_floor)
    if full_bleed:
        draw.rectangle(
            (0, 0, int(render_params.canvas_width), int(render_params.canvas_height)),
            fill=floor_fill,
        )
    else:
        draw.polygon(floor, fill=floor_fill)
        draw.line(floor + [floor[0]], fill=border_rgb, width=max(1, int(render_params.line_width_px) + 1))

    draw_grid = float(render_params.grid_step) > 0.0
    grid_mode = "bounded_stage" if bool(draw_grid) else "none"
    grid_extent = 0.0
    grid_world_bbox: List[float] | None = None
    if not draw_grid:
        grid_extent = 0.0
    elif full_bleed:
        floor_polygon_xy = _canvas_floor_polygon_xy(camera=camera, frame=frame, render_params=render_params)
        if floor_polygon_xy:
            grid_mode = "screen_ray_floor_plane"
            min_x = min(float(point[0]) for point in floor_polygon_xy)
            max_x = max(float(point[0]) for point in floor_polygon_xy)
            min_y = min(float(point[1]) for point in floor_polygon_xy)
            max_y = max(float(point[1]) for point in floor_polygon_xy)
            grid_world_bbox = [round(min_x, 4), round(min_y, 4), round(max_x, 4), round(max_y, 4)]
            grid_x_values = _grid_values_for_range(min_x, max_x, float(render_params.grid_step))
            grid_y_values = _grid_values_for_range(min_y, max_y, float(render_params.grid_step))
            for value in grid_y_values:
                segment = _polygon_axis_line_segment(floor_polygon_xy, axis="y", value=float(value))
                if segment is None:
                    continue
                _draw_line(
                    draw,
                    _project_xy((segment[0][0], segment[0][1], 0.0), camera, frame),
                    _project_xy((segment[1][0], segment[1][1], 0.0), camera, frame),
                    fill=grid_rgb,
                    width=render_params.line_width_px,
                )
            for value in grid_x_values:
                segment = _polygon_axis_line_segment(floor_polygon_xy, axis="x", value=float(value))
                if segment is None:
                    continue
                _draw_line(
                    draw,
                    _project_xy((segment[0][0], segment[0][1], 0.0), camera, frame),
                    _project_xy((segment[1][0], segment[1][1], 0.0), camera, frame),
                    fill=grid_rgb,
                    width=render_params.line_width_px,
                )
            grid_extent = max(abs(min_x), abs(max_x), abs(min_y), abs(max_y))
        else:
            grid_mode = "bounded_stage_fallback"
            grid_extent = min(
                float(extent) * max(1.0, float(render_params.full_bleed_floor_extent_multiplier)),
                max(float(extent), float(camera.distance) * 0.74),
            )
            grid_count = int(math.ceil((2.0 * grid_extent) / float(render_params.grid_step)))
            grid_values = [round(-grid_extent + index * float(render_params.grid_step), 6) for index in range(grid_count + 1)]
            if grid_values[-1] < grid_extent:
                grid_values.append(grid_extent)
            grid_values = [max(-grid_extent, min(grid_extent, float(value))) for value in grid_values]
            for value in grid_values:
                _draw_line(
                    draw,
                    _project_xy((-grid_extent, value, 0.0), camera, frame),
                    _project_xy((grid_extent, value, 0.0), camera, frame),
                    fill=grid_rgb,
                    width=render_params.line_width_px,
                )
                _draw_line(
                    draw,
                    _project_xy((value, -grid_extent, 0.0), camera, frame),
                    _project_xy((value, grid_extent, 0.0), camera, frame),
                    fill=grid_rgb,
                    width=render_params.line_width_px,
                )
    else:
        grid_extent = float(extent)
        grid_count = int(math.ceil((2.0 * grid_extent) / float(render_params.grid_step)))
        grid_values = [round(-grid_extent + index * float(render_params.grid_step), 6) for index in range(grid_count + 1)]
        if grid_values[-1] < grid_extent:
            grid_values.append(grid_extent)
        grid_values = [max(-grid_extent, min(grid_extent, float(value))) for value in grid_values]
        for value in grid_values:
            _draw_line(
                draw,
                _project_xy((-grid_extent, value, 0.0), camera, frame),
                _project_xy((grid_extent, value, 0.0), camera, frame),
                fill=grid_rgb,
                width=render_params.line_width_px,
            )
            _draw_line(
                draw,
                _project_xy((value, -grid_extent, 0.0), camera, frame),
                _project_xy((value, grid_extent, 0.0), camera, frame),
                fill=grid_rgb,
                width=render_params.line_width_px,
            )
    platform_points: List[Tuple[float, float]] = []
    if str(scene_variant) == "studio_platform" and not full_bleed:
        platform_points = [
            _project_xy((-2.4, -2.35, 0.03), camera, frame),
            _project_xy((2.4, -2.35, 0.03), camera, frame),
            _project_xy((2.4, 2.35, 0.03), camera, frame),
            _project_xy((-2.4, 2.35, 0.03), camera, frame),
        ]
        draw.line(platform_points + [platform_points[0]], fill=(78, 90, 106), width=max(2, int(render_params.line_width_px) + 1))

    if full_bleed:
        room_bbox = [0.0, 0.0, float(render_params.canvas_width), float(render_params.canvas_height)]
    else:
        all_points = list(floor) + list(platform_points)
        room_bbox = [
            round(float(min(point[0] for point in all_points)), 3),
            round(float(min(point[1] for point in all_points)), 3),
            round(float(max(point[0] for point in all_points)), 3),
            round(float(max(point[1] for point in all_points)), 3),
        ]
    return room_bbox, [
        {
            "entity_id": "open_floor_stage",
            "entity_type": "three_d_open_floor_stage",
            "bbox_px": list(room_bbox),
            "attrs": {
                "scene_variant": str(scene_variant),
                "room_extent": float(extent),
                "full_bleed_floor": bool(full_bleed),
                "grid_extent": float(grid_extent),
                "grid_mode": str(grid_mode),
                "grid_world_bbox": list(grid_world_bbox) if grid_world_bbox is not None else None,
                "has_walls": False,
            },
        }
    ]














def _draw_option_label(
    draw: ImageDraw.ImageDraw,
    *,
    label: str,
    center: Sequence[float],
    font,
) -> List[float]:
    x, y = float(center[0]), float(center[1])
    text_bbox = draw.textbbox((0, 0), str(label), font=font, stroke_width=3)
    width = float(text_bbox[2] - text_bbox[0])
    height = float(text_bbox[3] - text_bbox[1])
    label_bbox = [
        round(x - width * 0.5 - 4.0, 3),
        round(y - height * 0.5 - 5.0, 3),
        round(x + width * 0.5 + 4.0, 3),
        round(y + height * 0.5 + 3.0, 3),
    ]
    draw_text_traced(draw,
        (x - width * 0.5, y - height * 0.5 - 1.0),
        str(label),
        font=font,
        fill=(255, 255, 255),
        stroke_width=3,
        stroke_fill=(24, 29, 38),
     role="readout", required=False,)
    return list(label_bbox)


draw_open_box_object = _draw_open_box_object
draw_table_object = _draw_table_object


__all__ = [
    "draw_open_box_object",
    "draw_table_object",
]
