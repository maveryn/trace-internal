"""Rendering primitives for coordinate-panel scenes."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import ImageDraw

from trace.core.seed import spawn_rng
from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.geometry.shared.coordinate_panel_grid import (
    CoordinatePanelConfig,
    CoordinatePanelStyle,
    coordinate_panel_layout,
    draw_coordinate_panel_grid,
    graph_point_to_panel_pixel,
    panel_bbox_for_index,
    plot_bbox_for_panel,
)
from trace.tasks.geometry.shared.option_count import panel_grid_shape_for_option_count

from .defaults import resolve_int_param
from .construction import classify_point_set, is_ambiguous_for_prompt, sample_panel_points, shape_distractor_kinds
from .state import Color, PanelDefaults, PanelScene, PanelSpec, PixelPoint

PANEL_BACKGROUND_DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "styles": {
        "solid_offwhite": {"kind": "solid", "color": [252, 252, 252]},
        "solid_cool": {"kind": "solid", "color": [246, 248, 252]},
        "solid_warm": {"kind": "solid", "color": [252, 249, 245]},
        "solid_mist": {"kind": "solid", "color": [248, 252, 249]},
    },
    "weights": {
        "solid_offwhite": 0.35,
        "solid_cool": 0.25,
        "solid_warm": 0.20,
        "solid_mist": 0.20,
    },
}
PANEL_STYLES: Tuple[CoordinatePanelStyle, ...] = (
    CoordinatePanelStyle(),
    CoordinatePanelStyle(
        panel_fill=(255, 255, 255),
        panel_outline=(190, 205, 218),
        plot_fill=(249, 252, 255),
        plot_outline=(176, 192, 208),
        grid_color=(218, 228, 238),
        axis_color=(94, 115, 135),
        tick_color=(82, 98, 116),
        text_color=(28, 45, 62),
    ),
    CoordinatePanelStyle(
        panel_fill=(255, 255, 252),
        panel_outline=(207, 197, 178),
        plot_fill=(253, 251, 245),
        plot_outline=(194, 183, 162),
        grid_color=(232, 224, 207),
        axis_color=(125, 107, 82),
        tick_color=(104, 91, 72),
        text_color=(55, 45, 34),
    ),
    CoordinatePanelStyle(
        panel_fill=(253, 255, 252),
        panel_outline=(186, 209, 198),
        plot_fill=(248, 253, 249),
        plot_outline=(174, 198, 187),
        grid_color=(218, 232, 224),
        axis_color=(87, 124, 108),
        tick_color=(74, 102, 91),
        text_color=(35, 58, 49),
    ),
)
MARKER_STYLES: Tuple[str, ...] = ("filled_circle", "ring", "cross", "diamond", "square")
MARKER_COLOR_PALETTES: Tuple[Tuple[Color, Color], ...] = (
    ((32, 92, 166), (206, 92, 38)),
    ((38, 123, 96), (129, 77, 172)),
    ((19, 119, 150), (190, 67, 104)),
    ((97, 100, 36), (178, 83, 43)),
    ((54, 94, 132), (185, 104, 28)),
    ((105, 76, 151), (34, 130, 121)),
)
DEFAULTS = PanelDefaults()


def _sample_marker_style(rng, *, params: Mapping[str, Any], defaults: Mapping[str, Any], key: str) -> str:
    explicit = params.get(str(key), defaults.get(str(key), None))
    if explicit is not None:
        style = str(explicit)
        if style not in set(MARKER_STYLES):
            raise ValueError(f"{key}={style!r} is not supported")
        return style
    return str(rng.choice(MARKER_STYLES))


def _draw_marker(
    draw: ImageDraw.ImageDraw,
    point: PixelPoint,
    *,
    style: str,
    color: Color,
    radius: int,
    outline: Color = (255, 255, 255),
    width: int = 2,
) -> None:
    x_value, y_value = float(point[0]), float(point[1])
    radius_px = max(2, int(radius))
    line_width = max(1, int(width))
    fill = tuple(int(value) for value in color)
    stroke = tuple(int(value) for value in outline)
    if str(style) == "ring":
        draw.ellipse([x_value - radius_px, y_value - radius_px, x_value + radius_px, y_value + radius_px], fill=stroke, outline=fill, width=line_width)
    elif str(style) == "cross":
        draw.line([(x_value - radius_px, y_value - radius_px), (x_value + radius_px, y_value + radius_px)], fill=fill, width=line_width)
        draw.line([(x_value - radius_px, y_value + radius_px), (x_value + radius_px, y_value - radius_px)], fill=fill, width=line_width)
    elif str(style) == "diamond":
        draw.polygon(
            [(x_value, y_value - radius_px), (x_value + radius_px, y_value), (x_value, y_value + radius_px), (x_value - radius_px, y_value)],
            fill=fill,
            outline=stroke,
        )
    elif str(style) == "square":
        draw.rectangle(
            [x_value - radius_px, y_value - radius_px, x_value + radius_px, y_value + radius_px],
            fill=fill,
            outline=stroke,
            width=line_width,
        )
    else:
        draw.ellipse([x_value - radius_px, y_value - radius_px, x_value + radius_px, y_value + radius_px], fill=fill, outline=stroke, width=line_width)


def _resolve_marker_colors(rng) -> Tuple[Color, Color, Dict[str, Any]]:
    known_color, candidate_color = rng.choice(MARKER_COLOR_PALETTES)
    return tuple(known_color), tuple(candidate_color), {
        "palette": [list(known_color), list(candidate_color)],
        "known_color": list(known_color),
        "candidate_color": list(candidate_color),
    }


def _panel_style(rng) -> Tuple[CoordinatePanelStyle, Dict[str, Any]]:
    index = int(rng.randrange(len(PANEL_STYLES)))
    style = PANEL_STYLES[int(index)]
    return style, {"style_index": int(index), "style": style.to_trace_dict()}


def render_panel_scene(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    target_kind: str,
    winner_label: str,
    label_pool: Sequence[str],
    panel_count: int,
    option_count_probabilities: Mapping[str, float],
    noise_defaults: Mapping[str, Any],
) -> PanelScene:
    """Render labeled panels after the public task resolves the target shape and answer label."""

    rng = spawn_rng(int(instance_seed), "coordinate_panels.panel_scene")
    max_abs = resolve_int_param(params, generation_defaults, "panel_graph_abs_max", DEFAULTS.panel_graph_abs_max)
    if int(panel_count) > len(tuple(label_pool)):
        raise ValueError("panel_count cannot exceed panel label pool length")
    visible_labels = tuple(str(label) for label in tuple(label_pool)[: int(panel_count)])
    if str(winner_label) not in set(visible_labels):
        visible_labels = tuple([str(winner_label), *[label for label in visible_labels if label != str(winner_label)]])
        visible_labels = visible_labels[: int(panel_count)]

    columns, rows = panel_grid_shape_for_option_count(int(panel_count))
    panel_config = CoordinatePanelConfig(
        grid_min=resolve_int_param(params, rendering_defaults, "panel_grid_min", DEFAULTS.panel_grid_min),
        grid_max=resolve_int_param(params, rendering_defaults, "panel_grid_max", DEFAULTS.panel_grid_max),
        columns=int(columns),
        rows=int(rows),
    )
    canvas_width = resolve_int_param(params, rendering_defaults, "panel_canvas_width", DEFAULTS.panel_canvas_width)
    canvas_height = resolve_int_param(params, rendering_defaults, "panel_canvas_height", DEFAULTS.panel_canvas_height)
    image, background_meta = make_background_canvas(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=PANEL_BACKGROUND_DEFAULTS,
        fallback_color=(248, 250, 252),
    )
    draw = ImageDraw.Draw(image)
    style, panel_style_meta = _panel_style(rng)
    marker_style = _sample_marker_style(rng, params=params, defaults=rendering_defaults, key="panel_marker_style")
    _, marker_color, color_meta = _resolve_marker_colors(rng)
    marker_radius = resolve_int_param(params, rendering_defaults, "panel_marker_radius_px", DEFAULTS.panel_marker_radius_px)
    marker_radius = max(
        resolve_int_param(params, rendering_defaults, "panel_marker_radius_px_min", DEFAULTS.panel_marker_radius_px_min),
        min(
            resolve_int_param(params, rendering_defaults, "panel_marker_radius_px_max", DEFAULTS.panel_marker_radius_px_max),
            int(marker_radius),
        ),
    )
    distractor_kinds = shape_distractor_kinds(str(target_kind), rng=rng, count=int(panel_count) - 1)
    kind_by_label: Dict[str, str] = {}
    distractor_iter = iter(distractor_kinds)
    for label in visible_labels:
        kind_by_label[str(label)] = str(target_kind) if str(label) == str(winner_label) else str(next(distractor_iter))

    layout = coordinate_panel_layout(int(canvas_width), int(canvas_height), config=panel_config)
    panels_by_label: Dict[str, PanelSpec] = {}
    for index, label in enumerate(visible_labels):
        panel_bbox = panel_bbox_for_index(layout, int(index), config=panel_config)
        plot_bbox = plot_bbox_for_panel(panel_bbox)
        draw_coordinate_panel_grid(
            draw,
            panel_bbox=panel_bbox,
            plot_bbox=plot_bbox,
            label=str(label),
            config=panel_config,
            style=style,
        )
        points = sample_panel_points(str(kind_by_label[str(label)]), rng=rng, max_abs=int(max_abs))
        classified_kind = classify_point_set(points)
        if str(kind_by_label[str(label)]) != "other" and str(classified_kind) != str(kind_by_label[str(label)]):
            raise RuntimeError(f"panel {label} sampled as {kind_by_label[str(label)]} but classified {classified_kind}")
        if str(label) != str(winner_label) and is_ambiguous_for_prompt(str(classified_kind), str(target_kind)):
            raise RuntimeError("sampled ambiguous distractor panel")
        points_px = tuple(
            graph_point_to_panel_pixel(point, plot_bbox=plot_bbox, config=panel_config)
            for point in points
        )
        for point_px in points_px:
            _draw_marker(
                draw,
                point_px,
                style=str(marker_style),
                color=marker_color,
                radius=int(marker_radius),
                width=2,
            )
        panels_by_label[str(label)] = PanelSpec(
            label=str(label),
            points=tuple(points),
            points_px=tuple((float(point[0]), float(point[1])) for point in points_px),
            classified_kind=str(classified_kind),
            panel_bbox=[int(value) for value in panel_bbox],
            plot_bbox=[int(value) for value in plot_bbox],
        )

    image, post_noise_meta = apply_post_image_noise(
        image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=noise_defaults,
    )
    marker_meta = {
        "panel_marker_style": str(marker_style),
        "panel_marker_color": list(marker_color),
        "panel_marker_radius_px": int(marker_radius),
        "color_selection": dict(color_meta),
    }
    return PanelScene(
        panels_by_label=dict(panels_by_label),
        marker_meta=dict(marker_meta),
        panel_style_meta=dict(panel_style_meta),
        image=image,
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        option_count_probabilities={str(key): float(value) for key, value in option_count_probabilities.items()},
    )


__all__ = ["render_panel_scene"]
