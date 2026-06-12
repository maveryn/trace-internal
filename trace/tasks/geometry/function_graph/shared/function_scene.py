"""Shared graph-paper plotting helpers for geometry function-graph tasks."""

from __future__ import annotations

from typing import Iterable, List, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ....shared.text_rendering import draw_text_centered, load_font, resolve_text_stroke_fill
from ....shared.drawing import draw_dashed_line

PointF = Tuple[float, float]
Color = Tuple[int, int, int]


def graph_units_to_pixel_float(
    point: Sequence[float],
    *,
    graph_origin: Sequence[float],
    graph_spacing: int,
) -> PointF:
    """Project one graph-unit point (possibly fractional) into canonical pixels."""

    return (
        float(graph_origin[0]) + (float(point[0]) * float(graph_spacing)),
        float(graph_origin[1]) - (float(point[1]) * float(graph_spacing)),
    )


def scale_polyline(points: Iterable[PointF], *, scene_scale: int) -> List[PointF]:
    """Scale one canonical polyline into render-space pixels."""

    scale = float(max(1, int(scene_scale)))
    return [
        (float(point[0]) * scale, float(point[1]) * scale)
        for point in points
    ]


def draw_function_polyline(
    draw: ImageDraw.ImageDraw,
    *,
    polyline_graph: Sequence[Sequence[float]],
    graph_origin: Sequence[float],
    graph_spacing: int,
    scene_scale: int,
    line_width: int,
    line_color: Sequence[int],
) -> List[PointF]:
    """Draw one plotted function polyline and return the render-space points."""

    canonical_points = [
        graph_units_to_pixel_float(point, graph_origin=graph_origin, graph_spacing=int(graph_spacing))
        for point in polyline_graph
    ]
    render_points = scale_polyline(canonical_points, scene_scale=int(scene_scale))
    if len(render_points) >= 2:
        draw.line(
            list(render_points),
            fill=tuple(int(value) for value in line_color),
            width=max(1, int(line_width)),
            joint="curve",
        )
    return render_points


def draw_horizontal_query_line(
    draw: ImageDraw.ImageDraw,
    *,
    y_value: int,
    x_min: int,
    x_max: int,
    graph_origin: Sequence[float],
    graph_spacing: int,
    scene_scale: int,
    dash_px: float,
    gap_px: float,
    line_width: int,
    line_color: Sequence[int],
    label_text: str,
    label_font_size_px: int,
    label_color: Sequence[int],
    canvas_size: int,
) -> Mapping[str, object]:
    """Draw one dashed horizontal guide line plus a small `y = c` label."""

    canonical_start = graph_units_to_pixel_float((float(x_min), float(y_value)), graph_origin=graph_origin, graph_spacing=int(graph_spacing))
    canonical_end = graph_units_to_pixel_float((float(x_max), float(y_value)), graph_origin=graph_origin, graph_spacing=int(graph_spacing))
    render_start, render_end = scale_polyline((canonical_start, canonical_end), scene_scale=int(scene_scale))
    draw_dashed_line(
        draw,
        start=render_start,
        end=render_end,
        fill=tuple(int(value) for value in line_color),
        width=max(1, int(line_width)),
        dash_px=float(dash_px),
        gap_px=float(gap_px),
    )

    font = load_font(int(label_font_size_px), bold=True)
    label_fill = tuple(int(value) for value in label_color)
    label_stroke = resolve_text_stroke_fill(tuple(int(value) for value in label_fill))
    label_center = (
        float(render_end[0] - (18.0 * float(max(1, int(scene_scale))))),
        float(render_start[1] - (12.0 * float(max(1, int(scene_scale))))),
    )
    stroke_width = max(1, int(scene_scale))
    raw_bbox = draw.textbbox(
        (0.0, 0.0),
        str(label_text),
        font=font,
        stroke_width=int(stroke_width),
    )
    tx = float(label_center[0]) - (0.5 * float(raw_bbox[0] + raw_bbox[2]))
    ty = float(label_center[1]) - (0.5 * float(raw_bbox[1] + raw_bbox[3]))
    draw_text_centered(
        draw,
        text=str(label_text),
        center=label_center,
        font=font,
        fill=label_fill,
        stroke_fill=label_stroke,
        stroke_width=int(stroke_width),
    )
    bbox = (
        float(tx) + float(raw_bbox[0]),
        float(ty) + float(raw_bbox[1]),
        float(tx) + float(raw_bbox[2]),
        float(ty) + float(raw_bbox[3]),
    )
    return {
        "query_line_pixel": [
            [round(float(canonical_start[0]), 3), round(float(canonical_start[1]), 3)],
            [round(float(canonical_end[0]), 3), round(float(canonical_end[1]), 3)],
        ],
        "query_line_render": [
            [round(float(render_start[0]), 3), round(float(render_start[1]), 3)],
            [round(float(render_end[0]), 3), round(float(render_end[1]), 3)],
        ],
        "query_label_bbox": [
            round(max(0.0, min(float(canvas_size), float(bbox[0]) / float(max(1, int(scene_scale))))), 3),
            round(max(0.0, min(float(canvas_size), float(bbox[1]) / float(max(1, int(scene_scale))))), 3),
            round(max(0.0, min(float(canvas_size), float(bbox[2]) / float(max(1, int(scene_scale))))), 3),
            round(max(0.0, min(float(canvas_size), float(bbox[3]) / float(max(1, int(scene_scale))))), 3),
        ],
    }


def build_query_line_color(*, line_color: Sequence[int], label_color: Sequence[int]) -> Color:
    """Blend one guide-line accent that stays distinct from the main function line."""

    return tuple(
        int(
            round(
                (0.78 * float(int(label_color[index])))
                + (0.22 * float(int(line_color[index])))
            )
        )
        for index in range(3)
    )
