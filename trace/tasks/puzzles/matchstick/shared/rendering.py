"""Rendering helpers for matchstick puzzle scenes."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.tasks.puzzles.shared.scene_style import make_puzzle_scene_background
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.drawing import draw_centered_text, draw_rounded_rect
from trace.tasks.shared.font_assets import (
    font_asset_version,
    get_font_family_record,
    sample_font_family,
)
from trace.tasks.shared.text_rendering import load_font

from .rules import edge_signature, edge_trace, number_segments, number_text
from .state import BBox, Color, Edge, NumberDataset, RenderParams, RenderedScene, ShapeDataset


def _to_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(fallback)


def resolve_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> RenderParams:
    """Resolve all render dimensions from params and scene defaults."""

    return RenderParams(
        canvas_width=max(
            900,
            _to_int(
                params.get("canvas_width", group_default(render_defaults, "canvas_width", 1200)),
                1200,
            ),
        ),
        canvas_height=max(
            760,
            _to_int(
                params.get("canvas_height", group_default(render_defaults, "canvas_height", 900)),
                900,
            ),
        ),
        margin_px=max(
            40,
            _to_int(params.get("margin_px", group_default(render_defaults, "margin_px", 58)), 58),
        ),
        source_panel_height_px=max(
            160,
            _to_int(
                params.get(
                    "source_panel_height_px",
                    group_default(render_defaults, "source_panel_height_px", 230),
                ),
                230,
            ),
        ),
        option_panel_width_px=max(
            180,
            _to_int(
                params.get(
                    "option_panel_width_px",
                    group_default(render_defaults, "option_panel_width_px", 320),
                ),
                320,
            ),
        ),
        option_panel_height_px=max(
            150,
            _to_int(
                params.get(
                    "option_panel_height_px",
                    group_default(render_defaults, "option_panel_height_px", 218),
                ),
                218,
            ),
        ),
        option_gap_px=max(
            12,
            _to_int(
                params.get("option_gap_px", group_default(render_defaults, "option_gap_px", 28)),
                28,
            ),
        ),
        panel_corner_radius_px=max(
            0,
            _to_int(
                params.get(
                    "panel_corner_radius_px",
                    group_default(render_defaults, "panel_corner_radius_px", 20),
                ),
                20,
            ),
        ),
        panel_border_width_px=max(
            1,
            _to_int(
                params.get(
                    "panel_border_width_px",
                    group_default(render_defaults, "panel_border_width_px", 3),
                ),
                3,
            ),
        ),
        stick_width_px=max(
            5,
            _to_int(
                params.get("stick_width_px", group_default(render_defaults, "stick_width_px", 13)),
                13,
            ),
        ),
        option_label_font_size_px=max(
            18,
            _to_int(
                params.get(
                    "option_label_font_size_px",
                    group_default(render_defaults, "option_label_font_size_px", 26),
                ),
                26,
            ),
        ),
        caption_font_size_px=max(
            16,
            _to_int(
                params.get(
                    "caption_font_size_px",
                    group_default(render_defaults, "caption_font_size_px", 21),
                ),
                21,
            ),
        ),
        source_caption_font_size_px=max(
            18,
            _to_int(
                params.get(
                    "source_caption_font_size_px",
                    group_default(render_defaults, "source_caption_font_size_px", 24),
                ),
                24,
            ),
        ),
    )


def sample_matchstick_font(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    namespace: str,
) -> str:
    """Sample one global font family for option labels and captions."""

    return sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.matchstick_font",
        params={**dict(render_defaults), **dict(params)},
    )


def font_trace_record(font_family: str) -> Dict[str, Any]:
    """Build trace metadata for the sampled label/caption font."""

    return {
        **get_font_family_record(str(font_family)).to_trace(),
        "source": "global_font_pool",
        "font_asset_version": font_asset_version(),
        "selection_scope": "matchstick_option_labels_and_captions",
        "include_tags": [],
        "exclude_tags": [],
    }


def style_for_variant(scene_variant: str) -> Dict[str, Any]:
    """Return the material palette for one matchstick visual variant."""

    if scene_variant == "chalk_sticks":
        return {
            "background": (33, 39, 45),
            "panel_fill": (42, 49, 57),
            "panel_outline": (142, 154, 166),
            "stick": (235, 237, 230),
            "stick_shadow": (22, 26, 30),
            "label_fill": (248, 249, 244),
            "label_text": (25, 30, 36),
            "caption": (244, 246, 240),
            "tip": None,
            "palette": (),
        }
    if scene_variant == "neon_rods":
        return {
            "background": (20, 24, 39),
            "panel_fill": (26, 30, 49),
            "panel_outline": (80, 95, 150),
            "stick": (84, 214, 230),
            "stick_shadow": (30, 74, 92),
            "label_fill": (236, 244, 255),
            "label_text": (24, 30, 48),
            "caption": (232, 240, 255),
            "tip": None,
            "palette": (
                (84, 214, 230),
                (238, 111, 196),
                (255, 214, 96),
                (140, 226, 153),
            ),
        }
    if scene_variant == "colored_rods":
        return {
            "background": (246, 249, 252),
            "panel_fill": (255, 255, 255),
            "panel_outline": (86, 99, 122),
            "stick": (78, 137, 205),
            "stick_shadow": (225, 232, 242),
            "label_fill": (32, 40, 54),
            "label_text": (255, 255, 255),
            "caption": (28, 34, 44),
            "tip": None,
            "palette": (
                (64, 129, 202),
                (224, 107, 82),
                (64, 156, 118),
                (171, 108, 202),
                (222, 167, 62),
            ),
        }
    if scene_variant == "metal_rods":
        return {
            "background": (247, 248, 250),
            "panel_fill": (252, 253, 255),
            "panel_outline": (102, 111, 124),
            "stick": (154, 163, 174),
            "stick_shadow": (218, 222, 228),
            "label_fill": (40, 45, 54),
            "label_text": (255, 255, 255),
            "caption": (30, 35, 43),
            "tip": None,
            "palette": (),
        }
    return {
        "background": (251, 247, 238),
        "panel_fill": (255, 253, 247),
        "panel_outline": (128, 103, 75),
        "stick": (213, 174, 112),
        "stick_shadow": (236, 219, 188),
        "label_fill": (67, 52, 35),
        "label_text": (255, 255, 255),
        "caption": (55, 43, 31),
        "tip": (197, 54, 48),
        "palette": (),
    }


def matchstick_style_trace(scene_variant: str) -> Dict[str, Any]:
    """Serialize one material style for trace metadata."""

    style = style_for_variant(str(scene_variant))
    trace: Dict[str, Any] = {
        "scene_variant": str(scene_variant),
        "panel_fill_rgb": [int(value) for value in style["panel_fill"]],
        "panel_outline_rgb": [int(value) for value in style["panel_outline"]],
        "stick_rgb": [int(value) for value in style["stick"]],
        "stick_shadow_rgb": [int(value) for value in style["stick_shadow"]],
        "label_fill_rgb": [int(value) for value in style["label_fill"]],
        "label_text_rgb": [int(value) for value in style["label_text"]],
        "caption_rgb": [int(value) for value in style["caption"]],
        "palette_rgb": [[int(value) for value in color] for color in style.get("palette", ())],
    }
    tip = style.get("tip")
    trace["tip_rgb"] = None if tip is None else [int(value) for value in tip]
    return trace


def _stick_color(style: Mapping[str, Any], stick_id: str) -> Color:
    palette = style.get("palette") or ()
    if isinstance(palette, tuple) and palette:
        index = sum(ord(ch) for ch in str(stick_id)) % len(palette)
        return tuple(int(value) for value in palette[index])  # type: ignore[return-value]
    return tuple(int(value) for value in style["stick"])  # type: ignore[return-value]


def _draw_stick(
    draw: ImageDraw.ImageDraw,
    *,
    start: tuple[float, float],
    end: tuple[float, float],
    width: int,
    style: Mapping[str, Any],
    stick_id: str,
) -> None:
    sx, sy = float(start[0]), float(start[1])
    ex, ey = float(end[0]), float(end[1])
    shadow = tuple(int(value) for value in style["stick_shadow"])
    color = _stick_color(style, str(stick_id))
    shadow_width = int(width) + max(2, int(width // 3))
    draw.line([(sx, sy), (ex, ey)], fill=shadow, width=shadow_width)
    radius = max(2, int(shadow_width // 2))
    draw.ellipse((sx - radius, sy - radius, sx + radius, sy + radius), fill=shadow)
    draw.ellipse((ex - radius, ey - radius, ex + radius, ey + radius), fill=shadow)
    draw.line([(sx, sy), (ex, ey)], fill=color, width=int(width))
    radius = max(2, int(width // 2))
    draw.ellipse((sx - radius, sy - radius, sx + radius, sy + radius), fill=color)
    draw.ellipse((ex - radius, ey - radius, ex + radius, ey + radius), fill=color)
    tip = style.get("tip")
    if tip is not None:
        tip_radius = max(3, int(width // 2))
        draw.ellipse(
            (ex - tip_radius, ey - tip_radius, ex + tip_radius, ey + tip_radius),
            fill=tuple(int(v) for v in tip),
        )


def _draw_label_chip(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: tuple[int, int, int, int],
    label: str,
    render_params: RenderParams,
    style: Mapping[str, Any],
) -> None:
    chip = int(max(34, render_params.option_label_font_size_px + 16))
    chip_bbox = (
        int(bbox[0] + 12),
        int(bbox[1] + 10),
        int(bbox[0] + 12 + chip),
        int(bbox[1] + 10 + chip),
    )
    draw.rounded_rectangle(
        chip_bbox,
        radius=9,
        fill=tuple(style["label_fill"]),
        outline=(255, 255, 255),
        width=1,
    )
    font = load_font(int(render_params.option_label_font_size_px), bold=True)
    draw_centered_text(
        draw,
        text=str(label),
        center=((chip_bbox[0] + chip_bbox[2]) / 2, (chip_bbox[1] + chip_bbox[3]) / 2),
        font=font,
        fill=tuple(style["label_text"]),
        stroke_fill=tuple(style["label_fill"]),
        stroke_width=0,
    )


def _draw_caption(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: tuple[int, int, int, int],
    text: str,
    font_size: int,
    style: Mapping[str, Any],
) -> None:
    font = load_font(int(font_size), bold=True)
    draw_centered_text(
        draw,
        text=str(text),
        center=((bbox[0] + bbox[2]) / 2.0, bbox[1] + int(font_size * 0.9)),
        font=font,
        fill=tuple(style["caption"]),
        stroke_fill=tuple(style["panel_fill"]),
        stroke_width=1,
    )


def _draw_number(
    draw: ImageDraw.ImageDraw,
    *,
    number: int,
    bbox: tuple[int, int, int, int],
    render_params: RenderParams,
    style: Mapping[str, Any],
    small: bool,
) -> None:
    segments = number_segments(int(number))
    min_x = min(min(start[0], end[0]) for _sid, start, end in segments)
    max_x = max(max(start[0], end[0]) for _sid, start, end in segments)
    min_y = min(min(start[1], end[1]) for _sid, start, end in segments)
    max_y = max(max(start[1], end[1]) for _sid, start, end in segments)
    usable_w = max(1, int((bbox[2] - bbox[0]) * (0.62 if small else 0.52)))
    usable_h = max(1, int((bbox[3] - bbox[1]) * (0.58 if small else 0.66)))
    scale = min(
        float(usable_w) / max(1e-6, max_x - min_x),
        float(usable_h) / max(1e-6, max_y - min_y),
    )
    cx = (bbox[0] + bbox[2]) / 2.0
    cy = (bbox[1] + bbox[3]) / 2.0 + (10 if small else 14)
    total_w = (max_x - min_x) * scale
    total_h = (max_y - min_y) * scale
    origin_x = cx - (total_w / 2.0) - (min_x * scale)
    origin_y = cy - (total_h / 2.0) - (min_y * scale)
    width = max(5, int(render_params.stick_width_px * (0.82 if small else 1.20)))
    for segment_id, start, end in segments:
        _draw_stick(
            draw,
            start=(origin_x + start[0] * scale, origin_y + start[1] * scale),
            end=(origin_x + end[0] * scale, origin_y + end[1] * scale),
            width=width,
            style=style,
            stick_id=f"number:{segment_id}",
        )


def _draw_edge_arrangement(
    draw: ImageDraw.ImageDraw,
    *,
    edges: Sequence[Edge],
    bbox: tuple[int, int, int, int],
    grid_size: int,
    render_params: RenderParams,
    style: Mapping[str, Any],
    small: bool,
) -> None:
    left = bbox[0] + int((bbox[2] - bbox[0]) * 0.20)
    right = bbox[2] - int((bbox[2] - bbox[0]) * 0.16)
    top = bbox[1] + int((bbox[3] - bbox[1]) * (0.24 if small else 0.22))
    bottom = bbox[3] - int((bbox[3] - bbox[1]) * 0.14)
    scale = min(
        (right - left) / max(1, int(grid_size)),
        (bottom - top) / max(1, int(grid_size)),
    )
    offset_x = (left + right - (int(grid_size) * scale)) / 2.0
    offset_y = (top + bottom - (int(grid_size) * scale)) / 2.0
    width = max(5, int(render_params.stick_width_px * (0.72 if small else 0.95)))
    for edge_index, (a, b) in enumerate(edge_signature(edges)):
        start = (offset_x + int(a[0]) * scale, offset_y + int(a[1]) * scale)
        end = (offset_x + int(b[0]) * scale, offset_y + int(b[1]) * scale)
        _draw_stick(
            draw,
            start=start,
            end=end,
            width=width,
            style=style,
            stick_id=f"edge:{edge_index}:{a}:{b}",
        )


def option_bboxes(
    render_params: RenderParams,
    option_count: int,
    *,
    include_source: bool,
) -> list[tuple[int, int, int, int]]:
    """Return the 3-by-2 option-card layout used by both tasks."""

    cols = 3
    rows = 2
    total_w = (
        cols * render_params.option_panel_width_px
        + (cols - 1) * render_params.option_gap_px
    )
    start_x = int((render_params.canvas_width - total_w) / 2)
    if include_source:
        start_y = int(render_params.margin_px + render_params.source_panel_height_px + 44)
    else:
        total_h = (
            rows * render_params.option_panel_height_px
            + (rows - 1) * render_params.option_gap_px
        )
        start_y = int((render_params.canvas_height - total_h) / 2)
    bboxes: list[tuple[int, int, int, int]] = []
    for index in range(int(option_count)):
        row = int(index // cols)
        col = int(index % cols)
        if row >= rows:
            break
        x0 = int(start_x + col * (render_params.option_panel_width_px + render_params.option_gap_px))
        y0 = int(start_y + row * (render_params.option_panel_height_px + render_params.option_gap_px))
        bboxes.append(
            (
                x0,
                y0,
                int(x0 + render_params.option_panel_width_px),
                int(y0 + render_params.option_panel_height_px),
            )
        )
    return bboxes


def _draw_panel(
    draw: ImageDraw.ImageDraw,
    bbox: tuple[int, int, int, int],
    *,
    render_params: RenderParams,
    style: Mapping[str, Any],
) -> None:
    draw_rounded_rect(
        draw,
        bbox,
        radius=int(render_params.panel_corner_radius_px),
        fill=tuple(style["panel_fill"]),
        outline=tuple(style["panel_outline"]),
        width=int(render_params.panel_border_width_px),
    )


def make_scene_background(
    *,
    render_params: RenderParams,
    style: Any,
) -> tuple[Image.Image, Dict[str, Any]]:
    """Create the shared puzzle canvas background for matchstick panels."""

    return make_puzzle_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=style,
    )


def render_number_scene(
    *,
    background: Image.Image,
    dataset: NumberDataset,
    render_params: RenderParams,
) -> RenderedScene:
    """Render a source matchstick number and six candidate numbers."""

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    style = style_for_variant(str(dataset.scene_variant))
    source_bbox = (
        int(render_params.margin_px),
        int(render_params.margin_px),
        int(render_params.canvas_width - render_params.margin_px),
        int(render_params.margin_px + render_params.source_panel_height_px),
    )
    _draw_panel(draw, source_bbox, render_params=render_params, style=style)
    _draw_caption(
        draw,
        bbox=source_bbox,
        text="Source",
        font_size=int(render_params.source_caption_font_size_px),
        style=style,
    )
    _draw_number(
        draw,
        number=int(dataset.source_number),
        bbox=source_bbox,
        render_params=render_params,
        style=style,
        small=False,
    )
    item_bbox_map: Dict[str, BBox] = {
        "source_panel": tuple(float(value) for value in source_bbox)
    }
    entities: list[Dict[str, Any]] = [
        {
            "id": "source_panel",
            "type": "matchstick_number_source",
            "bbox_px": [int(value) for value in source_bbox],
            "number": number_text(int(dataset.source_number)),
        }
    ]
    bboxes = option_bboxes(render_params, int(dataset.option_count), include_source=True)
    for index, option in enumerate(dataset.option_specs):
        bbox = bboxes[int(index)]
        option_id = f"option_{option.label}"
        _draw_panel(draw, bbox, render_params=render_params, style=style)
        _draw_label_chip(
            draw,
            bbox=bbox,
            label=str(option.label),
            render_params=render_params,
            style=style,
        )
        _draw_number(
            draw,
            number=int(option.value),
            bbox=bbox,
            render_params=render_params,
            style=style,
            small=True,
        )
        item_bbox_map[str(option_id)] = tuple(float(value) for value in bbox)
        entities.append(
            {
                "id": str(option_id),
                "type": "matchstick_number_option",
                "label": str(option.label),
                "bbox_px": [int(value) for value in bbox],
                "number": number_text(int(option.value)),
                "is_correct": bool(option.is_correct),
            }
        )
    scene_bbox = (
        float(render_params.margin_px),
        float(render_params.margin_px),
        float(render_params.canvas_width - render_params.margin_px),
        float(render_params.canvas_height - render_params.margin_px),
    )
    return RenderedScene(
        image=image,
        scene_bbox_px=scene_bbox,
        item_bbox_map=item_bbox_map,
        entities=tuple(entities),
    )


def render_shape_scene(
    *,
    background: Image.Image,
    dataset: ShapeDataset,
    render_params: RenderParams,
) -> RenderedScene:
    """Render six lattice-stick arrangements for endpoint comparison."""

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    style = style_for_variant(str(dataset.scene_variant))
    item_bbox_map: Dict[str, BBox] = {}
    entities: list[Dict[str, Any]] = []
    bboxes = option_bboxes(render_params, int(dataset.option_count), include_source=False)
    for index, option in enumerate(dataset.option_specs):
        bbox = bboxes[int(index)]
        option_id = f"option_{option.label}"
        _draw_panel(draw, bbox, render_params=render_params, style=style)
        _draw_label_chip(
            draw,
            bbox=bbox,
            label=str(option.label),
            render_params=render_params,
            style=style,
        )
        _draw_edge_arrangement(
            draw,
            edges=option.value,
            bbox=bbox,
            grid_size=int(dataset.grid_size),
            render_params=render_params,
            style=style,
            small=True,
        )
        item_bbox_map[str(option_id)] = tuple(float(value) for value in bbox)
        entities.append(
            {
                "id": str(option_id),
                "type": "matchstick_endpoint_option",
                "label": str(option.label),
                "bbox_px": [int(value) for value in bbox],
                "edges": edge_trace(option.value),
                "loose_endpoint_count": int(option.metric_value or 0),
                "is_correct": bool(option.is_correct),
            }
        )
    scene_bbox = (
        float(render_params.margin_px),
        float(render_params.margin_px),
        float(render_params.canvas_width - render_params.margin_px),
        float(render_params.canvas_height - render_params.margin_px),
    )
    return RenderedScene(
        image=image,
        scene_bbox_px=scene_bbox,
        item_bbox_map=item_bbox_map,
        entities=tuple(entities),
    )


__all__ = [
    "font_trace_record",
    "make_scene_background",
    "matchstick_style_trace",
    "render_number_scene",
    "render_shape_scene",
    "resolve_render_params",
    "sample_matchstick_font",
]
