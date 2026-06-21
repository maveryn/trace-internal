"""Rendering helpers for population-pyramid chart scenes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageDraw

from .....core.visual.noise import apply_post_image_noise
from ....shared.bbox_projection import bbox_union_raw as _bbox_union
from ....shared.config_defaults import group_default
from ....shared.render_variation import apply_layout_jitter_to_margins, resolve_render_int, resolve_render_rgb
from ....shared.text_legibility import draw_traced_text
from ....shared.text_rendering import draw_text_centered, fit_font_to_box, load_font
from ...shared.information_style import make_chart_information_background, resolve_chart_information_style
from ...shared.visual_defaults import chart_font_asset_metadata, sample_chart_font_family

from .defaults import POST_IMAGE_NOISE_DEFAULTS, RENDER_DEFAULTS
from .state import (
    RGB,
    SCENE_ID,
    SCENE_NAMESPACE,
    PopulationPyramidDataset,
    PopulationPyramidRenderParams,
    RenderedPopulationPyramidScene,
)


@dataclass(frozen=True)
class PopulationPyramidRenderResult:
    image: Image.Image
    rendered_scene: RenderedPopulationPyramidScene
    post_noise_meta: dict[str, Any]


def _bbox(values: Sequence[float]) -> list[float]:
    return [round(float(value), 3) for value in values]


def _resolve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> PopulationPyramidRenderParams:
    """Resolve only visual/layout knobs; task sampling and annotation contracts are already fixed."""

    left = int(params.get("plot_margin_left_px", group_default(RENDER_DEFAULTS, "plot_margin_left_px", 162)))
    right = int(params.get("plot_margin_right_px", group_default(RENDER_DEFAULTS, "plot_margin_right_px", 84)))
    top = int(params.get("plot_margin_top_px", group_default(RENDER_DEFAULTS, "plot_margin_top_px", 84)))
    bottom = int(params.get("plot_margin_bottom_px", group_default(RENDER_DEFAULTS, "plot_margin_bottom_px", 104)))
    left, right, top, bottom, jitter_meta = apply_layout_jitter_to_margins(
        left_px=left,
        right_px=right,
        top_px=top,
        bottom_px=bottom,
        params=params,
        defaults=RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.layout",
    )
    font_family = sample_chart_font_family(
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.font",
        params=params,
        exclude_tags=("display",),
    )
    return PopulationPyramidRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(RENDER_DEFAULTS, "canvas_width", 1280))),
        canvas_height=int(params.get("canvas_height", group_default(RENDER_DEFAULTS, "canvas_height", 900))),
        plot_margin_left_px=int(left),
        plot_margin_right_px=int(right),
        plot_margin_top_px=int(top),
        plot_margin_bottom_px=int(bottom),
        title_band_height_px=int(params.get("title_band_height_px", group_default(RENDER_DEFAULTS, "title_band_height_px", 62))),
        legend_gap_px=int(params.get("legend_gap_px", group_default(RENDER_DEFAULTS, "legend_gap_px", 28))),
        axis_line_width_px=int(resolve_render_int(params, RENDER_DEFAULTS, "axis_line_width_px", 2, instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE)),
        grid_line_width_px=int(resolve_render_int(params, RENDER_DEFAULTS, "grid_line_width_px", 1, instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE)),
        bar_outline_width_px=int(resolve_render_int(params, RENDER_DEFAULTS, "bar_outline_width_px", 1, instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE)),
        bar_gap_px=int(resolve_render_int(params, RENDER_DEFAULTS, "bar_gap_px", 5, instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE)),
        title_font_size_px=int(params.get("title_font_size_px", group_default(RENDER_DEFAULTS, "title_font_size_px", 30))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(RENDER_DEFAULTS, "label_font_size_px", 18))),
        tick_font_size_px=int(params.get("tick_font_size_px", group_default(RENDER_DEFAULTS, "tick_font_size_px", 15))),
        legend_font_size_px=int(params.get("legend_font_size_px", group_default(RENDER_DEFAULTS, "legend_font_size_px", 18))),
        value_font_size_px=int(params.get("value_font_size_px", group_default(RENDER_DEFAULTS, "value_font_size_px", 14))),
        axis_max=int(params.get("axis_max", group_default(RENDER_DEFAULTS, "axis_max", 100))),
        tick_step=int(params.get("tick_step", group_default(RENDER_DEFAULTS, "tick_step", 20))),
        panel_fill_rgb=resolve_render_rgb(params, RENDER_DEFAULTS, "panel_fill_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE),
        panel_border_rgb=resolve_render_rgb(params, RENDER_DEFAULTS, "panel_border_rgb", (190, 198, 208), instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE),
        axis_rgb=resolve_render_rgb(params, RENDER_DEFAULTS, "axis_rgb", (62, 68, 78), instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE),
        grid_rgb=resolve_render_rgb(params, RENDER_DEFAULTS, "grid_rgb", (225, 229, 235), instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE),
        text_rgb=resolve_render_rgb(params, RENDER_DEFAULTS, "text_rgb", (35, 42, 52), instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE),
        muted_text_rgb=resolve_render_rgb(params, RENDER_DEFAULTS, "muted_text_rgb", (82, 91, 106), instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE),
        text_stroke_rgb=resolve_render_rgb(params, RENDER_DEFAULTS, "text_stroke_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE),
        font_family=str(font_family),
        layout_jitter_meta=dict(jitter_meta),
    )


def _relative_luminance(color: Sequence[int]) -> float:
    def _channel(value: int) -> float:
        normalized = float(value) / 255.0
        if normalized <= 0.03928:
            return normalized / 12.92
        return ((normalized + 0.055) / 1.055) ** 2.4

    rgb = [max(0, min(255, int(channel))) for channel in color[:3]]
    return (0.2126 * _channel(rgb[0])) + (0.7152 * _channel(rgb[1])) + (0.0722 * _channel(rgb[2]))


def _readable_chart_text_colors(surface_rgb: Sequence[int]) -> tuple[RGB, RGB, RGB]:
    if _relative_luminance(surface_rgb) >= 0.55:
        return (34, 42, 54), (72, 84, 100), (34, 42, 54)
    return (246, 250, 255), (205, 218, 232), (18, 24, 32)


def _darken(color: RGB, factor: float = 0.70) -> RGB:
    return tuple(max(0, min(255, int(round(float(channel) * float(factor))))) for channel in color)  # type: ignore[return-value]


def _text_on_bar(color: RGB) -> RGB:
    return (18, 24, 32) if _relative_luminance(color) > 0.52 else (248, 250, 252)


def _draw_text(
    draw: ImageDraw.ImageDraw,
    *,
    xy: tuple[float, float],
    text: str,
    font: Any,
    fill: RGB,
    stroke: RGB,
    stroke_width: int = 1,
    required: bool = True,
) -> None:
    draw_traced_text(
        draw,
        xy=(float(xy[0]), float(xy[1])),
        text=str(text),
        font=font,
        fill_rgb=tuple(int(value) for value in fill),
        stroke_rgb=tuple(int(value) for value in stroke),
        stroke_width=int(stroke_width),
        role="chart_text",
        required=bool(required),
    )


def _render_dataset(dataset: PopulationPyramidDataset, params: Mapping[str, Any], *, instance_seed: int) -> RenderedPopulationPyramidScene:
    """Render a bound population-pyramid dataset without changing its answer contract."""

    render_params = _resolve_render_params(params, instance_seed=int(instance_seed))
    style, style_meta = resolve_chart_information_style(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        protected_colors=(dataset.left_color_rgb, dataset.right_color_rgb),
        allow_dark=False,
        allow_colored_surface=True,
    )
    image, background_meta = make_chart_information_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=style,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.background",
    )
    if image.mode != "RGB":
        image = image.convert("RGB")
    draw = ImageDraw.Draw(image)
    panel_fill_rgb = tuple(int(value) for value in style.surface_rgb)
    panel_border_rgb = tuple(int(value) for value in style.panel_border_rgb)
    axis_rgb = tuple(int(value) for value in style.axis_rgb)
    grid_rgb = tuple(int(value) for value in style.grid_rgb)
    text_rgb, muted_text_rgb, text_stroke_rgb = _readable_chart_text_colors(panel_fill_rgb)
    text_stroke_width = 1

    plot_left = float(render_params.plot_margin_left_px)
    plot_right = float(render_params.canvas_width - render_params.plot_margin_right_px)
    plot_top = float(render_params.plot_margin_top_px + render_params.title_band_height_px)
    plot_bottom = float(render_params.canvas_height - render_params.plot_margin_bottom_px)
    plot_width = float(plot_right - plot_left)
    plot_height = float(plot_bottom - plot_top)
    if plot_width <= 100 or plot_height <= 100:
        raise ValueError("population pyramid plot area is too small")
    center_x = float(plot_left + (plot_width * 0.52))
    left_width = float(center_x - plot_left - 10)
    right_width = float(plot_right - center_x - 10)
    scale = min(left_width, right_width) / max(1.0, float(render_params.axis_max))
    panel_bbox = [
        max(18.0, float(plot_left - 118)),
        float(render_params.plot_margin_top_px),
        min(float(render_params.canvas_width - 22), float(plot_right + 42)),
        min(float(render_params.canvas_height - 22), float(plot_bottom + 62)),
    ]
    draw.rounded_rectangle(tuple(panel_bbox), radius=14, fill=panel_fill_rgb, outline=panel_border_rgb, width=2)

    title_font = load_font(render_params.title_font_size_px, bold=True, font_family=render_params.font_family)
    tick_font = load_font(render_params.tick_font_size_px, bold=False, font_family=render_params.font_family)
    legend_font = load_font(render_params.legend_font_size_px, bold=True, font_family=render_params.font_family)
    value_font = load_font(render_params.value_font_size_px, bold=True, font_family=render_params.font_family)

    _draw_text(
        draw,
        xy=(plot_left - 82, float(render_params.plot_margin_top_px + 12)),
        text=str(dataset.title),
        font=title_font,
        fill=text_rgb,
        stroke=text_stroke_rgb,
        stroke_width=text_stroke_width,
    )

    legend_y = float(render_params.plot_margin_top_px + 54)
    legend_items = ((dataset.left_series_label, dataset.left_color_rgb), (dataset.right_series_label, dataset.right_color_rgb))
    legend_x = float(center_x - 180)
    for index, (label, color) in enumerate(legend_items):
        x = float(legend_x + index * 230)
        draw.rounded_rectangle((x, legend_y + 3, x + 28, legend_y + 19), radius=4, fill=color, outline=_darken(color, 0.62), width=1)
        _draw_text(
            draw,
            xy=(x + 38, legend_y),
            text=str(label),
            font=legend_font,
            fill=text_rgb,
            stroke=text_stroke_rgb,
            stroke_width=text_stroke_width,
        )

    for tick in range(0, int(render_params.axis_max) + 1, int(render_params.tick_step)):
        dx = float(tick) * float(scale)
        xs = [center_x] if int(tick) == 0 else [center_x - dx, center_x + dx]
        for x in xs:
            draw.line(
                (x, plot_top, x, plot_bottom),
                fill=axis_rgb if int(tick) == 0 else grid_rgb,
                width=int(render_params.axis_line_width_px if int(tick) == 0 else render_params.grid_line_width_px),
            )
            draw_text_centered(
                draw,
                text=str(abs(int(tick))),
                center=(x, plot_bottom + 25),
                font=tick_font,
                fill=muted_text_rgb,
                stroke_fill=text_stroke_rgb,
                stroke_width=text_stroke_width,
            )
    draw.line((plot_left, plot_bottom, plot_right, plot_bottom), fill=axis_rgb, width=int(render_params.axis_line_width_px))
    draw.line((plot_left, plot_top, plot_left, plot_bottom), fill=axis_rgb, width=1)
    draw.line((plot_right, plot_top, plot_right, plot_bottom), fill=axis_rgb, width=1)

    row_step = plot_height / float(len(dataset.rows))
    bar_height = max(12.0, min(36.0, row_step - float(render_params.bar_gap_px)))
    row_bar_bboxes: dict[str, list[float]] = {}
    left_bar_bboxes: dict[str, list[float]] = {}
    right_bar_bboxes: dict[str, list[float]] = {}
    row_label_bboxes: dict[str, list[float]] = {}
    entities: list[dict[str, Any]] = []

    for index, row in enumerate(dataset.rows):
        center_y = float(plot_top + (index + 0.5) * row_step)
        y0 = float(center_y - (bar_height / 2.0))
        y1 = float(center_y + (bar_height / 2.0))
        left_x0 = float(center_x - (float(row.left_value) * scale))
        left_x1 = float(center_x)
        right_x0 = float(center_x)
        right_x1 = float(center_x + (float(row.right_value) * scale))
        left_bbox = _bbox([left_x0, y0, left_x1, y1])
        right_bbox = _bbox([right_x0, y0, right_x1, y1])
        row_bbox = _bbox_union([left_bbox, right_bbox], padding=5)
        left_bar_bboxes[str(row.row_id)] = list(left_bbox)
        right_bar_bboxes[str(row.row_id)] = list(right_bbox)
        row_bar_bboxes[str(row.row_id)] = list(row_bbox)

        draw.rounded_rectangle(tuple(left_bbox), radius=4, fill=dataset.left_color_rgb, outline=_darken(dataset.left_color_rgb, 0.58), width=int(render_params.bar_outline_width_px))
        draw.rounded_rectangle(tuple(right_bbox), radius=4, fill=dataset.right_color_rgb, outline=_darken(dataset.right_color_rgb, 0.58), width=int(render_params.bar_outline_width_px))
        label = str(row.label)
        label_font_fitted = fit_font_to_box(
            draw,
            text=label,
            max_width=86,
            max_height=bar_height + 8,
            bold=True,
            font_family=render_params.font_family,
            min_size_px=9,
            max_size_px=render_params.label_font_size_px,
        )
        text_bbox = draw.textbbox((0, 0), label, font=label_font_fitted, stroke_width=1)
        label_xy = (plot_left - 16 - float(text_bbox[2] - text_bbox[0]), center_y - 0.5 * float(text_bbox[3] - text_bbox[1]))
        label_record = draw_traced_text(
            draw,
            xy=(float(label_xy[0]), float(label_xy[1])),
            text=label,
            font=label_font_fitted,
            fill_rgb=text_rgb,
            stroke_rgb=text_stroke_rgb,
            stroke_width=text_stroke_width,
            role="axis_tick",
            required=True,
        )
        row_label_bboxes[str(row.row_id)] = _bbox(label_record["bbox_px"])

        for side, value, bbox, color in (
            ("left", int(row.left_value), left_bbox, dataset.left_color_rgb),
            ("right", int(row.right_value), right_bbox, dataset.right_color_rgb),
        ):
            value_text = str(value)
            value_box = draw.textbbox((0, 0), value_text, font=value_font, stroke_width=1)
            value_width = float(value_box[2] - value_box[0])
            x0, _by0, x1, _by1 = [float(v) for v in bbox]
            if float(x1 - x0) >= value_width + 12:
                text_center = ((x0 + x1) / 2.0, center_y)
                fill = _text_on_bar(color)
                stroke = _darken(color, 0.58) if fill == (248, 250, 252) else (248, 250, 252)
            elif side == "left":
                text_center = (max(plot_left + value_width / 2.0, x0 - value_width / 2.0 - 6), center_y)
                fill = text_rgb
                stroke = text_stroke_rgb
            else:
                text_center = (min(plot_right - value_width / 2.0, x1 + value_width / 2.0 + 6), center_y)
                fill = text_rgb
                stroke = text_stroke_rgb
            draw_text_centered(
                draw,
                text=value_text,
                center=text_center,
                font=value_font,
                fill=fill,
                stroke_fill=stroke,
                stroke_width=1,
            )

        entities.append(
            {
                "entity_id": str(row.row_id),
                "entity_type": "population_pyramid_row",
                "row_id": str(row.row_id),
                "row_label": str(row.label),
                "left_series_label": str(dataset.left_series_label),
                "right_series_label": str(dataset.right_series_label),
                "left_value": int(row.left_value),
                "right_value": int(row.right_value),
                "gap": int(row.gap),
                "total": int(row.total),
                "row_bar_bbox_px": list(row_bar_bboxes[str(row.row_id)]),
                "left_bar_bbox_px": list(left_bar_bboxes[str(row.row_id)]),
                "right_bar_bbox_px": list(right_bar_bboxes[str(row.row_id)]),
                "row_label_bbox_px": list(row_label_bboxes[str(row.row_id)]),
            }
        )

    return RenderedPopulationPyramidScene(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=_bbox([plot_left, plot_top, plot_right, plot_bottom]),
        row_bar_bboxes_px=dict(row_bar_bboxes),
        left_bar_bboxes_px=dict(left_bar_bboxes),
        right_bar_bboxes_px=dict(right_bar_bboxes),
        row_label_bboxes_px=dict(row_label_bboxes),
        render_meta={
            "panel_bbox_px": _bbox(panel_bbox),
            "center_axis_x_px": round(float(center_x), 3),
            "axis_max": int(render_params.axis_max),
            "tick_step": int(render_params.tick_step),
            "font_assets": chart_font_asset_metadata(render_params.font_family),
            "layout_jitter": dict(render_params.layout_jitter_meta),
            "background": dict(background_meta),
            "information_style": dict(style_meta),
        },
    )


def render_population_pyramid_dataset(
    *,
    dataset: PopulationPyramidDataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> PopulationPyramidRenderResult:
    rendered_scene = _render_dataset(dataset, params=params, instance_seed=int(instance_seed))
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return PopulationPyramidRenderResult(
        image=image,
        rendered_scene=rendered_scene,
        post_noise_meta=dict(post_noise_meta),
    )
