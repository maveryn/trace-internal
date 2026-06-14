"""Rendering primitives for error-bar series chart scenes."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.tasks.charts.errorbar_series.shared.defaults import (
    RENDER_DEFAULTS,
    as_rgb,
    group_render_default,
)
from trace.tasks.charts.errorbar_series.shared.state import (
    BBox,
    ErrorbarDataset,
    ErrorbarRenderParams,
    ErrorbarRendered,
    ErrorbarSeries,
    Point,
    RGB,
    SCENE_NAMESPACE,
)
from trace.tasks.shared.render_variation import (
    apply_layout_jitter_to_margins,
    resolve_render_int,
    resolve_render_rgb,
)
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font


def bbox(values: Sequence[float]) -> BBox:
    """Return a JSON-stable pixel bbox."""

    return [round(float(value), 3) for value in values]


def point(x: float, y: float) -> Point:
    """Return a JSON-stable pixel point."""

    return [round(float(x), 3), round(float(y), 3)]


def render_style_seed(params: Mapping[str, Any]) -> int:
    """Resolve the deterministic style seed stored in render params."""

    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def resolve_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    """Resolve one integer rendering parameter."""

    return int(
        resolve_render_int(
            params,
            RENDER_DEFAULTS,
            str(key),
            int(fallback),
            instance_seed=render_style_seed(params),
            namespace=SCENE_NAMESPACE,
        )
    )


def resolve_rgb(params: Mapping[str, Any], key: str, fallback: RGB) -> RGB:
    """Resolve one RGB rendering parameter."""

    return resolve_render_rgb(
        params,
        RENDER_DEFAULTS,
        str(key),
        as_rgb(group_render_default(key, fallback), fallback),
        instance_seed=render_style_seed(params),
        namespace=SCENE_NAMESPACE,
    )


def resolve_errorbar_render_params(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    chart_font_family: str,
) -> ErrorbarRenderParams:
    """Resolve canvas, axis, and mark styling for one render."""

    params = {**dict(params), "_render_style_seed": int(instance_seed)}
    left, right, top, bottom, jitter = apply_layout_jitter_to_margins(
        left_px=resolve_int(params, "plot_margin_left_px", 90),
        right_px=resolve_int(params, "plot_margin_right_px", 180),
        top_px=resolve_int(params, "plot_margin_top_px", 88),
        bottom_px=resolve_int(params, "plot_margin_bottom_px", 94),
        params=params,
        defaults=RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.layout",
    )
    return ErrorbarRenderParams(
        canvas_width=resolve_int(params, "canvas_width", 1280),
        canvas_height=resolve_int(params, "canvas_height", 820),
        margin_left_px=int(left),
        margin_right_px=int(right),
        margin_top_px=int(top),
        margin_bottom_px=int(bottom),
        title_font_size_px=resolve_int(params, "title_font_size_px", 26),
        tick_font_size_px=resolve_int(params, "tick_font_size_px", 15),
        label_font_size_px=resolve_int(params, "label_font_size_px", 17),
        legend_font_size_px=resolve_int(params, "legend_font_size_px", 16),
        axis_min=resolve_int(params, "axis_min", 0),
        axis_max=resolve_int(params, "axis_max", 100),
        tick_step=resolve_int(params, "tick_step", 20),
        axis_line_width_px=resolve_int(params, "axis_line_width_px", 2),
        grid_line_width_px=resolve_int(params, "grid_line_width_px", 1),
        errorbar_line_width_px=resolve_int(params, "errorbar_line_width_px", 3),
        center_line_width_px=resolve_int(params, "center_line_width_px", 2),
        cap_width_px=resolve_int(params, "cap_width_px", 14),
        point_radius_px=resolve_int(params, "point_radius_px", 5),
        series_offset_px=resolve_int(params, "series_offset_px", 11),
        text_rgb=resolve_rgb(params, "text_rgb", (36, 42, 54)),
        muted_text_rgb=resolve_rgb(params, "muted_text_rgb", (86, 94, 110)),
        text_stroke_rgb=resolve_rgb(params, "text_stroke_rgb", (255, 255, 255)),
        axis_rgb=resolve_rgb(params, "axis_rgb", (62, 68, 78)),
        grid_rgb=resolve_rgb(params, "grid_rgb", (222, 227, 234)),
        panel_fill_rgb=resolve_rgb(params, "panel_fill_rgb", (255, 255, 255)),
        panel_outline_rgb=resolve_rgb(params, "panel_outline_rgb", (194, 202, 214)),
        threshold_rgb=resolve_rgb(params, "threshold_rgb", (95, 84, 74)),
        font_family=str(chart_font_family),
        layout_jitter_meta=dict(jitter),
    )


def plot_bbox(render_params: ErrorbarRenderParams) -> BBox:
    """Return the plot area in pixel space."""

    return bbox(
        [
            float(render_params.margin_left_px),
            float(render_params.margin_top_px),
            float(render_params.canvas_width - render_params.margin_right_px),
            float(render_params.canvas_height - render_params.margin_bottom_px),
        ]
    )


def scale_y(value: float, *, render_params: ErrorbarRenderParams, plot_box: Sequence[float]) -> float:
    """Project one data value to the y-axis pixel coordinate."""

    _x0, y0, _x1, y1 = (float(item) for item in plot_box)
    denom = max(1.0, float(render_params.axis_max) - float(render_params.axis_min))
    return y1 - ((float(value) - float(render_params.axis_min)) / denom) * (y1 - y0)


def x_positions(
    dataset: ErrorbarDataset,
    *,
    plot_box: Sequence[float],
    render_params: ErrorbarRenderParams,
) -> Dict[str, Dict[str, float]]:
    """Project every series/x-label mark to an x pixel coordinate."""

    x0, _y0, x1, _y1 = (float(value) for value in plot_box)
    count = len(dataset.x_labels)
    if count <= 1:
        base_positions = [x0 + ((x1 - x0) / 2.0)]
    else:
        step = (x1 - x0) / float(count - 1)
        base_positions = [x0 + step * index for index in range(count)]
    offsets: Dict[str, Dict[str, float]] = {}
    series_count = len(dataset.series)
    for series_index, series in enumerate(dataset.series):
        if str(dataset.scene_variant) == "grouped_errorbar":
            offset = (float(series_index) - ((float(series_count) - 1.0) / 2.0)) * float(render_params.series_offset_px) * 1.35
        else:
            offset = (float(series_index) - ((float(series_count) - 1.0) / 2.0)) * float(render_params.series_offset_px)
        offsets[str(series.series_id)] = {
            str(label): float(base_positions[index] + offset)
            for index, label in enumerate(dataset.x_labels)
        }
    return offsets


def draw_axes(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: ErrorbarDataset,
    render_params: ErrorbarRenderParams,
    plot_box: Sequence[float],
) -> None:
    """Draw the plot frame, grid, y ticks, and x-axis labels."""

    x0, y0, x1, y1 = (float(value) for value in plot_box)
    draw.rectangle([x0, y0, x1, y1], fill=render_params.panel_fill_rgb, outline=render_params.panel_outline_rgb, width=1)
    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)
    label_font = load_font(int(render_params.label_font_size_px), bold=False)
    for tick in range(int(render_params.axis_min), int(render_params.axis_max) + 1, max(1, int(render_params.tick_step))):
        sy = scale_y(float(tick), render_params=render_params, plot_box=plot_box)
        draw.line([x0, sy, x1, sy], fill=render_params.grid_rgb, width=max(1, int(render_params.grid_line_width_px)))
        draw_text_traced(draw, (x0 - 12.0, sy), str(tick), font=tick_font, fill=render_params.muted_text_rgb, anchor="rm", role="readout", required=False)
    draw.line([x0, y1, x1, y1], fill=render_params.axis_rgb, width=max(1, int(render_params.axis_line_width_px)))
    draw.line([x0, y0, x0, y1], fill=render_params.axis_rgb, width=max(1, int(render_params.axis_line_width_px)))
    base_positions = x_positions(dataset, plot_box=plot_box, render_params=render_params)[str(dataset.series[0].series_id)]
    for label in dataset.x_labels:
        x = float(base_positions[str(label)])
        draw.line([x, y1, x, y1 + 5.0], fill=render_params.axis_rgb, width=1)
        draw_text_traced(draw, (x, y1 + 13.0), str(label), font=label_font, fill=render_params.text_rgb, anchor="mt", role="readout", required=False)


def draw_threshold(
    draw: ImageDraw.ImageDraw,
    *,
    threshold_value: int | None,
    render_params: ErrorbarRenderParams,
    plot_box: Sequence[float],
) -> BBox | None:
    """Draw the horizontal threshold line when an objective uses it."""

    if threshold_value is None:
        return None
    x0, _y0, x1, _y1 = (float(value) for value in plot_box)
    sy = scale_y(float(threshold_value), render_params=render_params, plot_box=plot_box)
    draw.line([x0, sy, x1, sy], fill=render_params.threshold_rgb, width=2)
    font = load_font(int(render_params.tick_font_size_px), bold=False)
    draw_text_traced(
        draw,
        (x1 + 10.0, sy),
        f"ref {int(threshold_value)}",
        font=font,
        fill=render_params.threshold_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=2,
        anchor="lm",
        role="readout",
        required=False,
    )
    return bbox([x0, sy - 2.0, x1, sy + 2.0])


def draw_legend(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: ErrorbarDataset,
    render_params: ErrorbarRenderParams,
    plot_box: Sequence[float],
) -> None:
    """Draw one compact right-side series legend."""

    _x0, y0, x1, _y1 = (float(value) for value in plot_box)
    font = load_font(int(render_params.legend_font_size_px), bold=False)
    legend_x = x1 + 24.0
    legend_y = y0 + 24.0
    for index, series in enumerate(dataset.series):
        y = legend_y + float(index) * 30.0
        draw.line([legend_x, y, legend_x + 28.0, y], fill=series.color_rgb, width=max(2, int(render_params.center_line_width_px)))
        radius = 4.0
        draw.ellipse([legend_x + 12.0 - radius, y - radius, legend_x + 12.0 + radius, y + radius], fill=series.color_rgb, outline=render_params.panel_fill_rgb, width=1)
        draw_text_traced(draw, (legend_x + 38.0, y), str(series.label), font=font, fill=render_params.text_rgb, anchor="lm", role="readout", required=False)


def errorbar_key(series: ErrorbarSeries, x_label: str) -> str:
    """Return the stable mark key used by annotation projection."""

    return f"{series.label}:{x_label}"


def draw_series_marks(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: ErrorbarDataset,
    render_params: ErrorbarRenderParams,
    plot_box: Sequence[float],
) -> tuple[tuple[dict[str, Any], ...], dict[str, BBox], dict[str, dict[str, dict[str, Point]]]]:
    """Draw all series marks and return mark projection maps."""

    positions = x_positions(dataset, plot_box=plot_box, render_params=render_params)
    entities: List[Dict[str, Any]] = []
    errorbar_bboxes: Dict[str, BBox] = {}
    point_map: Dict[str, Dict[str, Dict[str, Point]]] = {}
    for series in dataset.series:
        mark_rows: List[Tuple[int, str, float, float, float, float]] = []
        for x_index, x_label in enumerate(dataset.x_labels):
            x = float(positions[str(series.series_id)][str(x_label)])
            y_lower = scale_y(float(series.lower_values[int(x_index)]), render_params=render_params, plot_box=plot_box)
            y_mid = scale_y(float(series.mid_values[int(x_index)]), render_params=render_params, plot_box=plot_box)
            y_upper = scale_y(float(series.upper_values[int(x_index)]), render_params=render_params, plot_box=plot_box)
            mark_rows.append((int(x_index), str(x_label), float(x), float(y_lower), float(y_mid), float(y_upper)))
        if str(dataset.scene_variant) == "line_marker_errorbar":
            mid_points = [(float(row[2]), float(row[4])) for row in mark_rows]
            for first, second in zip(mid_points, mid_points[1:]):
                draw.line([first[0], first[1], second[0], second[1]], fill=series.color_rgb, width=max(1, int(render_params.center_line_width_px)))
        for x_index, x_label, x, y_lower, y_mid, y_upper in mark_rows:
            cap = float(render_params.cap_width_px)
            radius = float(render_params.point_radius_px)
            draw.line([x, y_upper, x, y_lower], fill=series.color_rgb, width=max(1, int(render_params.errorbar_line_width_px)))
            draw.line([x - cap / 2.0, y_upper, x + cap / 2.0, y_upper], fill=series.color_rgb, width=max(1, int(render_params.errorbar_line_width_px)))
            draw.line([x - cap / 2.0, y_lower, x + cap / 2.0, y_lower], fill=series.color_rgb, width=max(1, int(render_params.errorbar_line_width_px)))
            draw.ellipse([x - radius, y_mid - radius, x + radius, y_mid + radius], fill=series.color_rgb, outline=render_params.panel_fill_rgb, width=2)
            key = errorbar_key(series, str(x_label))
            mark_bbox = bbox([x - cap / 2.0 - radius, y_upper - radius, x + cap / 2.0 + radius, y_lower + radius])
            errorbar_bboxes[str(key)] = mark_bbox
            point_map.setdefault(str(series.label), {})[str(x_label)] = {
                "lower_bound": point(x, y_lower),
                "midpoint": point(x, y_mid),
                "upper_bound": point(x, y_upper),
            }
            entities.append(
                {
                    "entity_id": str(key),
                    "entity_type": "errorbar_mark",
                    "bbox_px": list(mark_bbox),
                    "attrs": {
                        "series_id": str(series.series_id),
                        "series_label": str(series.label),
                        "x_index": int(x_index),
                        "x_label": str(x_label),
                        "lower": int(series.lower_values[int(x_index)]),
                        "mid": int(series.mid_values[int(x_index)]),
                        "upper": int(series.upper_values[int(x_index)]),
                    },
                }
            )
    return tuple(entities), dict(errorbar_bboxes), dict(point_map)


def render_errorbar_series_chart(
    image: Image.Image,
    *,
    dataset: ErrorbarDataset,
    params: Mapping[str, Any],
    instance_seed: int,
    chart_font_family: str,
) -> ErrorbarRendered:
    """Draw one complete error-bar chart on a prepared background image."""

    params = {**dict(params), "_render_style_seed": int(instance_seed)}
    render_params = resolve_errorbar_render_params(
        params,
        instance_seed=int(instance_seed),
        chart_font_family=str(chart_font_family),
    )
    canvas = image.convert("RGB")
    draw = ImageDraw.Draw(canvas)
    box = plot_bbox(render_params)
    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    draw_text_traced(draw, (float(render_params.margin_left_px), 30.0), str(dataset.title), font=title_font, fill=render_params.text_rgb, role="readout", required=False)
    draw_axes(draw, dataset=dataset, render_params=render_params, plot_box=box)
    threshold_bbox = draw_threshold(draw, threshold_value=dataset.threshold_value, render_params=render_params, plot_box=box)
    entities, errorbar_bboxes, points = draw_series_marks(draw, dataset=dataset, render_params=render_params, plot_box=box)
    draw_legend(draw, dataset=dataset, render_params=render_params, plot_box=box)
    return ErrorbarRendered(
        image=canvas,
        entities=tuple(entities),
        plot_bbox_px=list(box),
        errorbar_bboxes_px=dict(errorbar_bboxes),
        point_map_px=dict(points),
        threshold_bbox_px=list(threshold_bbox) if threshold_bbox is not None else None,
        render_meta={"layout_jitter": dict(render_params.layout_jitter_meta)},
    )


__all__ = [
    "bbox",
    "draw_axes",
    "draw_legend",
    "draw_series_marks",
    "draw_threshold",
    "errorbar_key",
    "plot_bbox",
    "render_errorbar_series_chart",
    "resolve_errorbar_render_params",
    "scale_y",
    "x_positions",
]
