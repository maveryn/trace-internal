"""Rendering helpers for scientific axis-frame chart scenes."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from PIL import ImageDraw, ImageFont

from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.charts.scientific_axis_frame.shared.defaults import (
    BACKGROUND_DEFAULTS,
    NOISE_DEFAULTS,
    resolve_render_params,
)
from trace.tasks.charts.scientific_axis_frame.shared.state import (
    AxisFrameDataset,
    AxisFrameRenderResult,
    AxisFrameRenderParams,
    AxisSpec,
    BBox,
    RGB,
    RenderedAxisFrameScene,
    SCENE_NAMESPACE,
    bbox,
)
from trace.tasks.charts.shared.visual_defaults import chart_font_asset_metadata, sample_chart_font_family
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font, temporary_default_font_family


def font_assets_payload(*, chart_font_family: str) -> dict[str, Any]:
    return chart_font_asset_metadata(str(chart_font_family))


def render_axis_frame_dataset(
    *,
    dataset: AxisFrameDataset,
    params: Mapping[str, Any],
    instance_seed: int,
    highlight_tick_keys: Sequence[str] = (),
) -> AxisFrameRenderResult:
    chart_font_family = sample_chart_font_family(
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.chart_font",
        params=params,
    )
    with temporary_default_font_family(str(chart_font_family)):
        return _render_dataset(
            dataset=dataset,
            params={**dict(params), "_render_style_seed": int(instance_seed)},
            instance_seed=int(instance_seed),
            chart_font_family=str(chart_font_family),
            highlight_tick_keys=tuple(str(value) for value in highlight_tick_keys),
        )


def _render_dataset(
    *,
    dataset: AxisFrameDataset,
    params: Mapping[str, Any],
    instance_seed: int,
    chart_font_family: str,
    highlight_tick_keys: Sequence[str],
) -> AxisFrameRenderResult:
    """Render the numeric plot frame and project tick-label geometry.

    Invariant: highlighted ticks are supplied as semantic tick keys by the
    public task; the renderer only draws the requested keys and never infers
    objective behavior.
    """

    render_params = resolve_render_params(params, chart_font_family=str(chart_font_family))
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=BACKGROUND_DEFAULTS,
        fallback_color=(247, 248, 250),
    )
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    axis_label_font = load_font(int(render_params.axis_label_font_size_px), bold=True)
    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)

    plot_left = float(render_params.margin_left_px)
    plot_top = float(render_params.margin_top_px)
    plot_right = float(render_params.canvas_width - render_params.margin_right_px)
    plot_bottom = float(render_params.canvas_height - render_params.margin_bottom_px)
    plot_bbox = bbox([plot_left, plot_top, plot_right, plot_bottom])
    draw.rectangle(plot_bbox, fill=render_params.panel_fill_rgb, outline=render_params.panel_outline_rgb, width=1)

    tick_bboxes: dict[str, BBox] = {}
    entities: list[dict[str, Any]] = []
    for value in dataset.y_axis.values:
        y = _scale_y(float(value), y_axis=dataset.y_axis, plot_top=plot_top, plot_bottom=plot_bottom)
        draw.line([(plot_left, y), (plot_right, y)], fill=render_params.grid_rgb, width=int(render_params.grid_line_width_px))
        draw.line([(plot_left - 7.0, y), (plot_left, y)], fill=render_params.axis_rgb, width=int(render_params.axis_line_width_px))
        tick_bbox = _draw_centered(
            draw,
            center=(plot_left - 34.0, y),
            text=str(int(value)),
            font=tick_font,
            fill=render_params.muted_text_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )
        key = f"y:{int(value)}"
        tick_bboxes[key] = tick_bbox
        entities.append({"entity_id": key, "entity_type": "axis_tick_label", "bbox_px": list(tick_bbox), "attrs": {"axis": "y", "value": int(value)}})

    for value in dataset.x_axis.values:
        x = _scale_x(float(value), x_axis=dataset.x_axis, plot_left=plot_left, plot_right=plot_right)
        draw.line([(x, plot_top), (x, plot_bottom)], fill=render_params.grid_rgb, width=int(render_params.grid_line_width_px))
        draw.line([(x, plot_bottom), (x, plot_bottom + 7.0)], fill=render_params.axis_rgb, width=int(render_params.axis_line_width_px))
        tick_bbox = _draw_centered(
            draw,
            center=(x, plot_bottom + 28.0),
            text=str(int(value)),
            font=tick_font,
            fill=render_params.muted_text_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )
        key = f"x:{int(value)}"
        tick_bboxes[key] = tick_bbox
        entities.append({"entity_id": key, "entity_type": "axis_tick_label", "bbox_px": list(tick_bbox), "attrs": {"axis": "x", "value": int(value)}})

    draw.line([(plot_left, plot_top), (plot_left, plot_bottom)], fill=render_params.axis_rgb, width=int(render_params.axis_line_width_px))
    draw.line([(plot_left, plot_bottom), (plot_right, plot_bottom)], fill=render_params.axis_rgb, width=int(render_params.axis_line_width_px))

    x_axis_label_bbox = _draw_centered(
        draw,
        center=(0.5 * (plot_left + plot_right), plot_bottom + 66.0),
        text="x",
        font=axis_label_font,
        fill=render_params.text_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=1,
    )
    y_axis_label_bbox = _draw_centered(
        draw,
        center=(plot_left - 70.0, 0.5 * (plot_top + plot_bottom)),
        text="y",
        font=axis_label_font,
        fill=render_params.text_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=1,
    )

    series_px = [
        (
            _scale_x(float(x), x_axis=dataset.x_axis, plot_left=plot_left, plot_right=plot_right),
            _scale_y(float(y), y_axis=dataset.y_axis, plot_top=plot_top, plot_bottom=plot_bottom),
        )
        for x, y in dataset.series_points
    ]
    if len(series_px) >= 2:
        draw.line(series_px, fill=render_params.series_rgb, width=int(render_params.line_width_px), joint="curve")
    for x, y in series_px:
        radius = float(render_params.point_radius_px)
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=render_params.series_rgb, outline=render_params.panel_fill_rgb, width=1)

    for key in tuple(str(value) for value in highlight_tick_keys):
        if key in tick_bboxes:
            _draw_highlight(draw, tick_bboxes[str(key)], color=render_params.marker_rgb)

    image, noise_meta = apply_post_image_noise(
        image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=NOISE_DEFAULTS,
    )
    render_meta = {
        "background_style": dict(background_meta),
        "post_image_noise": dict(noise_meta),
        "chart_font_family": str(chart_font_family),
        "layout_jitter": dict(render_params.layout_jitter_meta),
        "rendering_contract": "scientific_axis_frame_numeric_ticks",
        "title_bbox_px": [],
        "title_text": "",
        "highlight_tick_keys": [str(value) for value in highlight_tick_keys],
    }
    rendered_scene = RenderedAxisFrameScene(
        image=image,
        entities=tuple(dict(entity) for entity in entities),
        plot_bbox_px=list(plot_bbox),
        tick_label_bboxes_px=dict(tick_bboxes),
        axis_label_bboxes_px={"x": list(x_axis_label_bbox), "y": list(y_axis_label_bbox)},
        render_meta=dict(render_meta),
    )
    return AxisFrameRenderResult(
        image=image,
        rendered_scene=rendered_scene,
        chart_font_family=str(chart_font_family),
        render_params=render_params,
        background_meta=dict(background_meta),
        post_noise_meta=dict(noise_meta),
    )


def _scale_x(value: float, *, x_axis: AxisSpec, plot_left: float, plot_right: float) -> float:
    span = max(1.0, float(x_axis.values[-1]) - float(x_axis.values[0]))
    return float(plot_left) + ((float(value) - float(x_axis.values[0])) / span) * float(plot_right - plot_left)


def _scale_y(value: float, *, y_axis: AxisSpec, plot_top: float, plot_bottom: float) -> float:
    span = max(1.0, float(y_axis.values[-1]) - float(y_axis.values[0]))
    return float(plot_bottom) - ((float(value) - float(y_axis.values[0])) / span) * float(plot_bottom - plot_top)


def _text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    *,
    anchor: str | None = None,
    stroke_width: int = 0,
) -> BBox:
    try:
        box = draw.textbbox((float(xy[0]), float(xy[1])), str(text), font=font, anchor=anchor, stroke_width=max(0, int(stroke_width)))
        return bbox(list(box))
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        return bbox([float(xy[0]), float(xy[1]), float(xy[0]) + float(width), float(xy[1]) + float(height)])


def _draw_centered(
    draw: ImageDraw.ImageDraw,
    *,
    center: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: RGB,
    stroke_fill: RGB,
    stroke_width: int = 0,
) -> BBox:
    try:
        box = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
        width = float(box[2] - box[0])
        height = float(box[3] - box[1])
        x = float(center[0]) - 0.5 * width - float(box[0])
        y = float(center[1]) - 0.5 * height - float(box[1])
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        x = float(center[0]) - 0.5 * float(width)
        y = float(center[1]) - 0.5 * float(height)
    draw_text_traced(
        draw,
        (float(x), float(y)),
        str(text),
        font=font,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=max(0, int(stroke_width)),
        role="readout",
        required=False,
    )
    return _text_bbox(draw, (float(x), float(y)), str(text), font, stroke_width=max(0, int(stroke_width)))


def _expanded_bbox(box: Sequence[float], pad: float) -> BBox:
    return bbox([float(box[0]) - float(pad), float(box[1]) - float(pad), float(box[2]) + float(pad), float(box[3]) + float(pad)])


def _draw_highlight(draw: ImageDraw.ImageDraw, box: Sequence[float], *, color: RGB) -> None:
    x0, y0, x1, y1 = _expanded_bbox(box, 5.0)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=4, outline=tuple(color), width=3)


__all__ = [
    "font_assets_payload",
    "render_axis_frame_dataset",
]
