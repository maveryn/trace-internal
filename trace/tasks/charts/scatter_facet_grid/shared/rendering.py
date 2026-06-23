"""Rendering helpers for scatter-facet-grid chart scenes."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw

from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.charts.shared.visual_defaults import chart_font_asset_metadata, sample_chart_font_family
from trace.tasks.shared.render_variation import apply_layout_jitter_to_margins
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font, temporary_default_font_family

from .defaults import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    RENDER_DEFAULTS,
    render_style_seed,
    resolve_int,
    resolve_rgb,
)
from .sampling import region_bounds
from .state import (
    Dataset,
    Panel,
    Point,
    RGB,
    RenderParams,
    RenderedScene,
    SCENE_NAMESPACE,
    ScatterFacetRenderResult,
)


def bbox(values: Sequence[float]) -> list[float]:
    return [round(float(value), 3) for value in values]


def bbox_union(boxes: Sequence[Sequence[float]]) -> list[float]:
    valid = [tuple(float(value) for value in box[:4]) for box in boxes if len(box) >= 4]
    if not valid:
        return []
    return bbox(
        (
            min(box[0] for box in valid),
            min(box[1] for box in valid),
            max(box[2] for box in valid),
            max(box[3] for box in valid),
        )
    )


def resolve_render_params(params: Mapping[str, Any]) -> RenderParams:
    """Resolve scene-level render geometry and style without task/query routing."""

    margin_left = resolve_int(params, "facet_grid_left_px", 92)
    margin_right = resolve_int(params, "facet_grid_right_px", 70)
    margin_top = resolve_int(params, "facet_grid_top_px", 92)
    margin_bottom = resolve_int(params, "facet_grid_bottom_px", 96)
    margin_left, margin_right, margin_top, margin_bottom, jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(margin_left),
        right_px=int(margin_right),
        top_px=int(margin_top),
        bottom_px=int(margin_bottom),
        params=params,
        defaults=RENDER_DEFAULTS,
        namespace=SCENE_NAMESPACE,
        instance_seed=render_style_seed(params),
    )
    return RenderParams(
        canvas_width=resolve_int(params, "facet_canvas_width", 1280),
        canvas_height=resolve_int(params, "facet_canvas_height", 860),
        grid_left_px=int(margin_left),
        grid_right_px=int(margin_right),
        grid_top_px=int(margin_top),
        grid_bottom_px=int(margin_bottom),
        panel_gap_x_px=resolve_int(params, "facet_panel_gap_x_px", 24),
        panel_gap_y_px=resolve_int(params, "facet_panel_gap_y_px", 30),
        axis_line_width_px=resolve_int(params, "facet_axis_line_width_px", 1),
        grid_line_width_px=resolve_int(params, "facet_grid_line_width_px", 1),
        point_radius_px=resolve_int(params, "facet_point_radius_px", 3),
        title_font_size_px=resolve_int(params, "facet_title_font_size_px", 25),
        panel_label_font_size_px=resolve_int(params, "facet_panel_label_font_size_px", 16),
        axis_label_font_size_px=resolve_int(params, "facet_axis_label_font_size_px", 18),
        tick_font_size_px=resolve_int(params, "facet_tick_font_size_px", 11),
        background_point_rgb=resolve_rgb(params, "facet_background_point_rgb", (188, 194, 202)),
        foreground_stroke_rgb=resolve_rgb(params, "facet_foreground_stroke_rgb", (255, 255, 255)),
        region_tint_rgb=resolve_rgb(params, "facet_region_tint_rgb", (252, 231, 160)),
        axis_color_rgb=resolve_rgb(params, "facet_axis_color_rgb", (82, 92, 108)),
        grid_color_rgb=resolve_rgb(params, "facet_grid_color_rgb", (222, 227, 235)),
        text_color_rgb=resolve_rgb(params, "facet_text_color_rgb", (25, 32, 44)),
        text_stroke_rgb=resolve_rgb(params, "facet_text_stroke_rgb", (255, 255, 255)),
        panel_fill_rgb=resolve_rgb(params, "facet_panel_fill_rgb", (250, 251, 253)),
        panel_border_rgb=resolve_rgb(params, "facet_panel_border_rgb", (194, 202, 214)),
        layout_jitter_meta=dict(jitter_meta),
    )


def value_to_px(panel_bbox: Sequence[float], *, x_value: float, y_value: float) -> tuple[float, float]:
    x0, y0, x1, y1 = [float(value) for value in panel_bbox[:4]]
    x_px = x0 + (float(x_value) / 100.0) * (x1 - x0)
    y_px = y1 - (float(y_value) / 100.0) * (y1 - y0)
    return float(x_px), float(y_px)


def region_bbox_px(panel_bbox: Sequence[float], region: str) -> list[float]:
    x0, y0, x1, y1 = region_bounds(str(region))
    px0, py1 = value_to_px(panel_bbox, x_value=x0, y_value=y0)
    px1, py0 = value_to_px(panel_bbox, x_value=x1, y_value=y1)
    return bbox((px0, py0, px1, py1))


def draw_point(
    draw: ImageDraw.ImageDraw,
    center: tuple[float, float],
    *,
    radius: int,
    fill: RGB,
    outline: RGB | None = None,
) -> list[float]:
    x, y = float(center[0]), float(center[1])
    r = float(radius)
    point_bbox = (x - r, y - r, x + r, y + r)
    draw.ellipse(point_bbox, fill=tuple(int(c) for c in fill), outline=outline)
    return bbox(point_bbox)


def all_panel_points(panel: Panel) -> tuple[Point, ...]:
    return tuple(panel.background_points) + tuple(panel.target_points) + tuple(panel.distractor_points)


def render_facet_grid(
    image: Image.Image,
    *,
    dataset: Dataset,
    render_params: RenderParams,
) -> RenderedScene:
    """Draw all panels and record projections for the task-bound density witness."""

    draw = ImageDraw.Draw(image, "RGBA")
    title_font = load_font(render_params.title_font_size_px)
    panel_label_font = load_font(render_params.panel_label_font_size_px)
    axis_label_font = load_font(render_params.axis_label_font_size_px)
    tick_font = load_font(render_params.tick_font_size_px)

    grid_left = float(render_params.grid_left_px)
    grid_top = float(render_params.grid_top_px)
    grid_right = float(render_params.canvas_width - render_params.grid_right_px)
    grid_bottom = float(render_params.canvas_height - render_params.grid_bottom_px)
    usable_width = grid_right - grid_left
    usable_height = grid_bottom - grid_top
    panel_w = (usable_width - (float(dataset.cols - 1) * render_params.panel_gap_x_px)) / float(dataset.cols)
    panel_h = (usable_height - (float(dataset.rows - 1) * render_params.panel_gap_y_px)) / float(dataset.rows)

    title_text = "Faceted Scatter Density"
    title_record = draw_text_traced(
        draw,
        (float(render_params.canvas_width) / 2.0, 34.0),
        title_text,
        font=title_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=1,
        anchor="ma",
        role="readout",
        required=False,
    )
    x_label_record = draw_text_traced(
        draw,
        (float(render_params.canvas_width) / 2.0, float(render_params.canvas_height) - 34.0),
        "X score",
        font=axis_label_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=1,
        anchor="mm",
        role="readout",
        required=False,
    )
    y_label_record = draw_text_traced(
        draw,
        (30.0, float(render_params.canvas_height) / 2.0),
        "Y score",
        font=axis_label_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=1,
        anchor="mm",
        role="readout",
        required=False,
    )

    panel_bboxes: dict[str, list[float]] = {}
    panel_label_bboxes: dict[str, list[float]] = {}
    region_bboxes: dict[str, list[float]] = {}
    density_region_bboxes: dict[str, list[float]] = {}
    point_bboxes: dict[str, list[float]] = {}
    point_centers: dict[str, list[float]] = {}
    entities: list[dict[str, Any]] = []

    for index, panel in enumerate(dataset.panels):
        row = int(index // dataset.cols)
        col = int(index % dataset.cols)
        px0 = grid_left + (float(col) * (panel_w + render_params.panel_gap_x_px))
        py0 = grid_top + (float(row) * (panel_h + render_params.panel_gap_y_px))
        px1 = px0 + panel_w
        py1 = py0 + panel_h
        panel_bbox = bbox((px0, py0, px1, py1))
        panel_bboxes[str(panel.label)] = panel_bbox
        draw.rectangle(
            panel_bbox,
            fill=tuple(render_params.panel_fill_rgb) + (255,),
            outline=tuple(render_params.panel_border_rgb) + (255,),
            width=1,
        )
        label_record = draw_text_traced(
            draw,
            ((px0 + px1) / 2.0, py0 - 7.0),
            str(panel.label),
            font=panel_label_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=2,
            anchor="ms",
            role="readout",
            required=True,
        )
        panel_label_bboxes[str(panel.label)] = list(label_record["bbox_px"])

        region_bbox = region_bbox_px(panel_bbox, dataset.query.target_region)
        region_bboxes[str(panel.label)] = list(region_bbox)
        draw.rectangle(
            region_bbox,
            fill=tuple(render_params.region_tint_rgb) + (54,),
            outline=tuple(render_params.region_tint_rgb) + (130,),
            width=1,
        )

        for tick in (25, 50, 75):
            x_tick, _ = value_to_px(panel_bbox, x_value=float(tick), y_value=0.0)
            _, y_tick = value_to_px(panel_bbox, x_value=0.0, y_value=float(tick))
            draw.line((x_tick, py0, x_tick, py1), fill=tuple(render_params.grid_color_rgb) + (255,), width=render_params.grid_line_width_px)
            draw.line((px0, y_tick, px1, y_tick), fill=tuple(render_params.grid_color_rgb) + (255,), width=render_params.grid_line_width_px)
        draw.line((px0, py1, px1, py1), fill=tuple(render_params.axis_color_rgb) + (255,), width=render_params.axis_line_width_px)
        draw.line((px0, py0, px0, py1), fill=tuple(render_params.axis_color_rgb) + (255,), width=render_params.axis_line_width_px)
        if row == dataset.rows - 1:
            draw_text_traced(draw, (px0, py1 + 4.0), "0", font=tick_font, fill=render_params.text_color_rgb, anchor="la", role="readout", required=False)
            draw_text_traced(draw, (px1, py1 + 4.0), "100", font=tick_font, fill=render_params.text_color_rgb, anchor="ra", role="readout", required=False)
        if col == 0:
            draw_text_traced(draw, (px0 - 5.0, py1), "0", font=tick_font, fill=render_params.text_color_rgb, anchor="rm", role="readout", required=False)
            draw_text_traced(draw, (px0 - 5.0, py0), "100", font=tick_font, fill=render_params.text_color_rgb, anchor="rm", role="readout", required=False)

        for point in panel.background_points:
            center = value_to_px(panel_bbox, x_value=point.x_value, y_value=point.y_value)
            point_box = draw_point(
                draw,
                center,
                radius=max(1, int(render_params.point_radius_px) - 1),
                fill=render_params.background_point_rgb,
                outline=None,
            )
            point_bboxes[str(point.point_id)] = point_box
            point_centers[str(point.point_id)] = bbox((center[0], center[1]))[:2]

        target_boxes: list[list[float]] = []
        for point in tuple(panel.distractor_points) + tuple(panel.target_points):
            center = value_to_px(panel_bbox, x_value=point.x_value, y_value=point.y_value)
            fill_rgb = panel.color_rgb if str(point.layer) == "target" else tuple(max(0, int(c) - 26) for c in panel.color_rgb)
            point_box = draw_point(
                draw,
                center,
                radius=int(render_params.point_radius_px),
                fill=fill_rgb,
                outline=render_params.foreground_stroke_rgb,
            )
            point_bboxes[str(point.point_id)] = point_box
            point_centers[str(point.point_id)] = bbox((center[0], center[1]))[:2]
            if str(point.layer) == "target":
                target_boxes.append(point_box)
        density_bbox = bbox_union(target_boxes)
        density_region_bboxes[str(panel.label)] = density_bbox

        entities.append(
            {
                "entity_id": f"panel:{panel.label}",
                "entity_type": "scatter_facet_panel",
                "label": str(panel.label),
                "bbox_px": list(panel_bbox),
                "target_region_bbox_px": list(region_bbox),
                "density_region_bbox_px": list(density_bbox),
                "target_density_score": round(float(panel.target_density_score), 5),
            }
        )

    return RenderedScene(
        image=image,
        entities=tuple(entities),
        panel_bboxes=dict(panel_bboxes),
        panel_label_bboxes=dict(panel_label_bboxes),
        region_bboxes=dict(region_bboxes),
        density_region_bboxes=dict(density_region_bboxes),
        point_bboxes=dict(point_bboxes),
        point_centers=dict(point_centers),
        title_bbox_px=list(title_record["bbox_px"]),
        x_axis_label_bbox_px=list(x_label_record["bbox_px"]),
        y_axis_label_bbox_px=list(y_label_record["bbox_px"]),
        title_text=str(title_text),
    )


def render_scatter_facet_dataset(
    *,
    dataset: Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> ScatterFacetRenderResult:
    """Render the sampled dataset with scene fonts, background, and post-noise metadata."""

    render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
    render_params = resolve_render_params(render_style_params)
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    chart_font_family = sample_chart_font_family(
        instance_seed=int(instance_seed),
        namespace=SCENE_NAMESPACE,
        params=params,
    )
    with temporary_default_font_family(str(chart_font_family)):
        rendered_scene = render_facet_grid(
            background,
            dataset=dataset,
            render_params=render_params,
        )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return ScatterFacetRenderResult(
        image=image,
        rendered_scene=rendered_scene,
        render_params=render_params,
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        chart_font_family=str(chart_font_family),
    )


def font_assets_payload(*, chart_font_family: str) -> dict[str, Any]:
    return chart_font_asset_metadata(str(chart_font_family))


__all__ = [
    "all_panel_points",
    "bbox",
    "bbox_union",
    "font_assets_payload",
    "region_bbox_px",
    "render_facet_grid",
    "render_scatter_facet_dataset",
    "resolve_render_params",
    "value_to_px",
]
