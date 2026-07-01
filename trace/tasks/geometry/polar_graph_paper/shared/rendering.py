"""Rendering for polar graph paper readout tasks."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from PIL import ImageDraw

from trace.tasks.geometry.shared.diagram_style import (
    GEOMETRY_STYLE_PROFILE_ANALYTICAL_DIAGRAM,
    prepare_geometry_diagram_style_and_background,
)
from trace.tasks.shared.text_rendering import draw_text_centered, load_font

from .state import PolarReadoutCase, RenderedPolarGraphPaperScene


def _int_default(defaults: Mapping[str, Any], name: str, fallback: int) -> int:
    return int(defaults.get(name, fallback))


def _polar_point(center: tuple[float, float], scale: float, radius: float, theta_degrees: float) -> tuple[float, float]:
    theta = math.radians(theta_degrees)
    return (center[0] + scale * radius * math.cos(theta), center[1] - scale * radius * math.sin(theta))


def _draw_polar_grid(
    draw: ImageDraw.ImageDraw,
    *,
    center: tuple[float, float],
    plot_radius_px: float,
    radius_max: int,
    minor_spoke_step: int,
    major_spoke_step: int,
    radius_label_step: int,
    style: Any,
) -> dict[str, Any]:
    """Draw reusable polar graph paper while preserving radius/spoke scale."""

    scale = plot_radius_px / radius_max
    grid_major = tuple(style.grid_major_rgb)
    grid_minor = tuple(style.grid_minor_rgb)
    axis_color = tuple(style.axis_rgb)
    text_color = tuple(style.label_rgb)
    small_font = load_font(13, bold=False)
    angle_font = load_font(15, bold=False)

    for ring in range(1, radius_max + 1):
        ring_radius = ring * scale
        color = grid_major if ring % 2 == 0 or ring == radius_max else grid_minor
        width = 2 if ring % 2 == 0 or ring == radius_max else 1
        draw.ellipse(
            (
                center[0] - ring_radius,
                center[1] - ring_radius,
                center[0] + ring_radius,
                center[1] + ring_radius,
            ),
            outline=color,
            width=width,
        )

    for theta in range(0, 360, minor_spoke_step):
        endpoint = _polar_point(center, scale, radius_max, theta)
        is_axis = theta % 90 == 0
        is_major = theta % major_spoke_step == 0
        color = axis_color if is_axis else (grid_major if is_major else grid_minor)
        width = 3 if is_axis else (2 if is_major else 1)
        draw.line((center, endpoint), fill=color, width=width)

    for ring in range(radius_label_step, radius_max + 1, radius_label_step):
        ring_point = _polar_point(center, scale, ring, 0)
        draw_text_centered(
            draw,
            center=(ring_point[0], ring_point[1] + 16),
            text=str(ring),
            font=small_font,
            fill=text_color,
            stroke_width=0,
        )

    for theta in range(0, 360, major_spoke_step):
        label_point = _polar_point(center, scale, radius_max + 0.58, theta)
        draw_text_centered(
            draw,
            center=label_point,
            text=f"{theta}\N{DEGREE SIGN}",
            font=angle_font,
            fill=text_color,
            stroke_width=0,
        )

    origin_radius = 4
    draw.ellipse(
        (
            center[0] - origin_radius,
            center[1] - origin_radius,
            center[0] + origin_radius,
            center[1] + origin_radius,
        ),
        fill=axis_color,
    )
    draw_text_centered(
        draw,
        center=(center[0] - 18, center[1] + 20),
        text="O",
        font=small_font,
        fill=text_color,
        stroke_width=0,
    )
    return {"plot_scale_px_per_radius": scale}


def _draw_options(
    draw: ImageDraw.ImageDraw,
    *,
    case: PolarReadoutCase,
    canvas_width: int,
    option_top: int,
    option_height: int,
    option_font_size: int,
    style: Any,
) -> dict[str, list[int]]:
    """Draw the fixed six-option MCQ panel and return label-to-box mapping."""

    card_gap = 18
    side_margin = 54
    columns = 3
    rows = 2
    card_width = (canvas_width - 2 * side_margin - (columns - 1) * card_gap) / columns
    card_height = (option_height - (rows - 1) * card_gap) / rows
    option_font = load_font(option_font_size, bold=False)
    label_font = load_font(option_font_size + 2, bold=True)
    option_bboxes: dict[str, list[int]] = {}

    for index, option in enumerate(case.options):
        row = index // columns
        col = index % columns
        x0 = side_margin + col * (card_width + card_gap)
        y0 = option_top + row * (card_height + card_gap)
        x1 = x0 + card_width
        y1 = y0 + card_height
        bbox = [round(x0), round(y0), round(x1), round(y1)]
        draw.rounded_rectangle(
            bbox,
            radius=10,
            fill=tuple(style.option_fill_rgb),
            outline=tuple(style.panel_border_rgb),
            width=2,
        )
        draw_text_centered(
            draw,
            center=(x0 + 34, (y0 + y1) / 2),
            text=option.label,
            font=label_font,
            fill=tuple(style.accent_rgb),
            stroke_width=0,
        )
        draw_text_centered(
            draw,
            center=((x0 + x1) / 2 + 20, (y0 + y1) / 2),
            text=option.display_text,
            font=option_font,
            fill=tuple(style.label_rgb),
            stroke_width=0,
        )
        option_bboxes[option.label] = bbox

    return option_bboxes


def render_polar_graph_paper_scene(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_id: str,
    case: PolarReadoutCase,
    rendering_defaults: Mapping[str, Any],
) -> RenderedPolarGraphPaperScene:
    """Render the polar grid, point witness, and options from one sampled case."""

    canvas_width = _int_default(rendering_defaults, "canvas_width", 820)
    canvas_height = _int_default(rendering_defaults, "canvas_height", 780)
    radius_max = _int_default(rendering_defaults, "polar_radius_max", 8)
    minor_spoke_step = _int_default(rendering_defaults, "minor_spoke_step_degrees", 15)
    major_spoke_step = _int_default(rendering_defaults, "major_spoke_step_degrees", 30)
    radius_label_step = _int_default(rendering_defaults, "radius_label_step", 1)
    marker_radius = _int_default(rendering_defaults, "marker_radius_px", 9)
    label_font_size = _int_default(rendering_defaults, "label_font_size", 28)
    option_font_size = _int_default(rendering_defaults, "option_font_size", 24)

    background, background_meta, style, style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=scene_id,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        style_profile=GEOMETRY_STYLE_PROFILE_ANALYTICAL_DIAGRAM,
        allow_dark=True,
        require_grid=False,
    )
    image = background
    draw = ImageDraw.Draw(image)

    plot_panel = (42, 32, canvas_width - 42, 552)
    draw.rounded_rectangle(
        plot_panel,
        radius=18,
        fill=tuple(style.panel_fill_rgb),
        outline=tuple(style.panel_border_rgb),
        width=2,
    )

    center = (canvas_width / 2, 292.0)
    plot_radius_px = min(
        (plot_panel[2] - plot_panel[0]) / 2 - 78,
        (plot_panel[3] - plot_panel[1]) / 2 - 58,
    )
    grid_spec = _draw_polar_grid(
        draw,
        center=center,
        plot_radius_px=plot_radius_px,
        radius_max=radius_max,
        minor_spoke_step=minor_spoke_step,
        major_spoke_step=major_spoke_step,
        radius_label_step=radius_label_step,
        style=style,
    )
    scale = grid_spec["plot_scale_px_per_radius"]
    point_xy = _polar_point(center, scale, case.radius, case.theta_degrees)

    draw.line((center, point_xy), fill=tuple(style.accent_rgb), width=2)
    point_bbox = [
        round(point_xy[0] - marker_radius),
        round(point_xy[1] - marker_radius),
        round(point_xy[0] + marker_radius),
        round(point_xy[1] + marker_radius),
    ]
    draw.ellipse(
        point_bbox,
        fill=tuple(style.accent_rgb),
        outline=tuple(style.stroke_rgb),
        width=3,
    )

    label_font = load_font(label_font_size, bold=True)
    label_offset = _polar_point((0.0, 0.0), 1.0, marker_radius + 22, case.theta_degrees + 180)
    draw_text_centered(
        draw,
        center=(point_xy[0] + label_offset[0], point_xy[1] + label_offset[1]),
        text="P",
        font=label_font,
        fill=tuple(style.label_rgb),
        stroke_width=0,
    )

    option_bboxes = _draw_options(
        draw,
        case=case,
        canvas_width=canvas_width,
        option_top=584,
        option_height=152,
        option_font_size=option_font_size,
        style=style,
    )

    point_value = [round(point_xy[0], 3), round(point_xy[1], 3)]
    render_map = {
        "point_p": point_value,
        "point_p_bbox": point_bbox,
        "point_p_polar": {
            "radius": case.radius,
            "theta_degrees": case.theta_degrees,
        },
        "plot_center": [round(center[0], 3), round(center[1], 3)],
        "plot_radius_px": round(plot_radius_px, 3),
        "plot_scale_px_per_radius": round(scale, 3),
        "option_bboxes_by_label": option_bboxes,
        "option_values_by_label": case.option_values_by_label,
        "option_display_by_label": case.option_display_by_label,
    }
    render_spec = {
        "canvas_width": canvas_width,
        "canvas_height": canvas_height,
        "polar_radius_max": radius_max,
        "minor_spoke_step_degrees": minor_spoke_step,
        "major_spoke_step_degrees": major_spoke_step,
        "style_profile": GEOMETRY_STYLE_PROFILE_ANALYTICAL_DIAGRAM,
    }

    return RenderedPolarGraphPaperScene(
        image=image,
        render_map=render_map,
        render_spec=render_spec,
        style_metadata={"background": background_meta, "diagram_style": style_meta},
    )
