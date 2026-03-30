"""Renderer for stylized choropleth region-map scenes with legends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.bbox_projection import bbox_center
from ...shared.text_rendering import draw_text_centered, load_font
from .region_common import MapRegionRenderParams


BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class RenderedRegionMapScene:
    """Rendered region-map scene plus traceable geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    region_bbox_map: Dict[str, List[float]]
    legend_entry_bbox_map: Dict[str, List[float]]
    map_bbox_px: List[float]
    legend_bbox_px: List[float]
    divider_bbox_px: List[float]


def _rounded_panel(
    draw: ImageDraw.ImageDraw,
    bbox: BBox,
    *,
    radius: int,
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int],
    width: int,
) -> None:
    """Draw one rounded panel box."""

    draw.rounded_rectangle(
        bbox,
        radius=int(radius),
        fill=tuple(int(channel) for channel in fill),
        outline=tuple(int(channel) for channel in outline),
        width=max(1, int(width)),
    )


def _cell_bbox(
    *,
    cell_x: int,
    cell_y: int,
    map_bbox: BBox,
    cols: int,
    rows: int,
) -> BBox:
    """Return pixel bbox for one hidden grid cell inside the map frame."""

    map_left, map_top, map_right, map_bottom = [float(value) for value in map_bbox]
    cell_width = (float(map_right) - float(map_left)) / float(max(1, int(cols)))
    cell_height = (float(map_bottom) - float(map_top)) / float(max(1, int(rows)))
    left = float(map_left + (float(cell_x) * cell_width))
    top = float(map_top + (float(cell_y) * cell_height))
    return (
        left,
        top,
        float(left + cell_width),
        float(top + cell_height),
    )


def render_region_map_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    grid_cols: int,
    grid_rows: int,
    region_specs: Sequence[Mapping[str, Any]],
    legend_specs: Sequence[Mapping[str, Any]],
    render_params: MapRegionRenderParams,
) -> RenderedRegionMapScene:
    """Render one stylized choropleth region-map scene with legend."""

    image = background.copy().convert("RGB")
    draw = ImageDraw.Draw(image)

    canvas_width = int(render_params.canvas_width)
    canvas_height = int(render_params.canvas_height)
    scene_left = float(render_params.scene_margin_left_px)
    scene_top = float(render_params.scene_margin_top_px)
    map_panel_bbox = (
        scene_left,
        scene_top,
        float(scene_left + render_params.map_panel_width_px),
        float(scene_top + render_params.map_panel_height_px),
    )
    legend_left = float(map_panel_bbox[2] + render_params.panel_gap_px)
    legend_top = float(scene_top + 48)
    legend_panel_bbox = (
        legend_left,
        legend_top,
        float(legend_left + render_params.legend_panel_width_px),
        float(legend_top + render_params.legend_panel_height_px),
    )
    divider_bbox = (
        float(legend_left - (render_params.panel_gap_px * 0.5)),
        float(scene_top + 8),
        float(legend_left - (render_params.panel_gap_px * 0.5) + 2),
        float(canvas_height - render_params.scene_margin_bottom_px - 8),
    )

    if str(scene_variant) in {"map_strip", "map_card"}:
        _rounded_panel(
            draw,
            map_panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=render_params.panel_fill_rgb,
            outline=render_params.border_color_rgb,
            width=int(render_params.outer_border_width_px),
        )
        _rounded_panel(
            draw,
            legend_panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=render_params.legend_fill_rgb,
            outline=render_params.border_color_rgb,
            width=int(render_params.outer_border_width_px),
        )
    else:
        draw.rounded_rectangle(
            map_panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            outline=tuple(int(channel) for channel in render_params.border_color_rgb),
            width=max(1, int(render_params.outer_border_width_px)),
        )
        draw.rounded_rectangle(
            legend_panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            outline=tuple(int(channel) for channel in render_params.border_color_rgb),
            width=max(1, int(render_params.outer_border_width_px)),
        )
    draw.rounded_rectangle(
        divider_bbox,
        radius=1,
        fill=tuple(int(channel) for channel in render_params.divider_rgb),
        outline=None,
    )

    map_bbox = (
        float(map_panel_bbox[0] + render_params.map_padding_px),
        float(map_panel_bbox[1] + render_params.map_padding_px),
        float(map_panel_bbox[2] - render_params.map_padding_px),
        float(map_panel_bbox[3] - render_params.map_padding_px),
    )

    entities: List[Dict[str, Any]] = [
        {
            "entity_id": "map_panel",
            "entity_type": "map_panel",
            "bbox_px": [float(value) for value in map_panel_bbox],
            "attrs": {"scene_variant": str(scene_variant)},
        },
        {
            "entity_id": "map_legend_panel",
            "entity_type": "map_legend_panel",
            "bbox_px": [float(value) for value in legend_panel_bbox],
            "attrs": {},
        },
        {
            "entity_id": "map_divider",
            "entity_type": "map_divider",
            "bbox_px": [float(value) for value in divider_bbox],
            "attrs": {},
        },
    ]

    region_bbox_map: Dict[str, List[float]] = {}
    legend_entry_bbox_map: Dict[str, List[float]] = {}
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    legend_font = load_font(int(render_params.legend_font_size_px), bold=False)
    title_font = load_font(int(render_params.title_font_size_px), bold=True)

    for region_spec in region_specs:
        cells = [(int(cell[0]), int(cell[1])) for cell in region_spec["cells"]]
        fill_rgb = tuple(int(channel) for channel in region_spec["fill_rgb"])
        cell_bboxes = [
            _cell_bbox(
                cell_x=int(cell_x),
                cell_y=int(cell_y),
                map_bbox=map_bbox,
                cols=int(grid_cols),
                rows=int(grid_rows),
            )
            for cell_x, cell_y in cells
        ]
        for bbox in cell_bboxes:
            draw.rectangle(bbox, fill=fill_rgb)
        bbox_left = min(float(bbox[0]) for bbox in cell_bboxes)
        bbox_top = min(float(bbox[1]) for bbox in cell_bboxes)
        bbox_right = max(float(bbox[2]) for bbox in cell_bboxes)
        bbox_bottom = max(float(bbox[3]) for bbox in cell_bboxes)
        region_bbox = [bbox_left, bbox_top, bbox_right, bbox_bottom]
        region_bbox_map[str(region_spec["region_bbox_id"])] = [round(float(value), 3) for value in region_bbox]
        entities.append(
            {
                "entity_id": str(region_spec["region_id"]),
                "entity_type": "map_region",
                "bbox_px": [round(float(value), 3) for value in region_bbox],
                "attrs": {
                    "region_label": str(region_spec["region_label"]),
                    "category_index": int(region_spec["category_index"]),
                    "category_label": str(region_spec["category_label"]),
                    "fill_rgb": [int(channel) for channel in fill_rgb],
                },
            }
        )
        for cell_index, bbox in enumerate(cell_bboxes):
            entities.append(
                {
                    "entity_id": f"{str(region_spec['region_id'])}_cell_{int(cell_index)}",
                    "entity_type": "map_region_cell",
                    "bbox_px": [round(float(value), 3) for value in bbox],
                    "attrs": {
                        "region_id": str(region_spec["region_id"]),
                    },
                }
            )
        label_center = bbox_center((bbox_left, bbox_top, bbox_right, bbox_bottom))
        draw_text_centered(
            draw,
            text=str(region_spec["region_label"]),
            center=label_center,
            font=label_font,
            fill=render_params.label_color_rgb,
            stroke_fill=render_params.label_stroke_rgb,
            stroke_width=max(1, int(round(render_params.label_font_size_px * 0.08))),
        )
        entities.append(
            {
                "entity_id": f"{str(region_spec['region_id'])}_label",
                "entity_type": "map_region_label",
                "bbox_px": [
                    round(float(label_center[0] - 12.0), 3),
                    round(float(label_center[1] - 12.0), 3),
                    round(float(label_center[0] + 12.0), 3),
                    round(float(label_center[1] + 12.0), 3),
                ],
                "attrs": {
                    "region_id": str(region_spec["region_id"]),
                    "region_label": str(region_spec["region_label"]),
                },
            }
        )

    # Draw region borders after fills so the hidden grid disappears inside each region.
    border_rgb = tuple(int(channel) for channel in render_params.border_color_rgb)
    for region_spec in region_specs:
        region_cells = {(int(cell[0]), int(cell[1])) for cell in region_spec["cells"]}
        for cell_x, cell_y in region_cells:
            cell = _cell_bbox(
                cell_x=int(cell_x),
                cell_y=int(cell_y),
                map_bbox=map_bbox,
                cols=int(grid_cols),
                rows=int(grid_rows),
            )
            left, top, right, bottom = [float(value) for value in cell]
            neighbors = {
                "left": (int(cell_x) - 1, int(cell_y)),
                "right": (int(cell_x) + 1, int(cell_y)),
                "up": (int(cell_x), int(cell_y) - 1),
                "down": (int(cell_x), int(cell_y) + 1),
            }
            if neighbors["left"] not in region_cells:
                draw.line((left, top, left, bottom), fill=border_rgb, width=int(render_params.region_border_width_px))
            if neighbors["right"] not in region_cells:
                draw.line((right, top, right, bottom), fill=border_rgb, width=int(render_params.region_border_width_px))
            if neighbors["up"] not in region_cells:
                draw.line((left, top, right, top), fill=border_rgb, width=int(render_params.region_border_width_px))
            if neighbors["down"] not in region_cells:
                draw.line((left, bottom, right, bottom), fill=border_rgb, width=int(render_params.region_border_width_px))

    # Legend chrome.
    legend_title_center = (
        float(legend_panel_bbox[0] + (render_params.legend_panel_width_px * 0.5)),
        float(legend_panel_bbox[1] + 34),
    )
    draw_text_centered(
        draw,
        text="Legend",
        center=legend_title_center,
        font=title_font,
        fill=render_params.label_color_rgb,
        stroke_fill=render_params.label_stroke_rgb,
        stroke_width=max(1, int(round(render_params.title_font_size_px * 0.08))),
    )
    legend_x = float(legend_panel_bbox[0] + 30)
    legend_y = float(legend_panel_bbox[1] + 78)
    for legend_index, legend_spec in enumerate(legend_specs):
        swatch_top = float(legend_y + legend_index * (render_params.legend_swatch_size_px + render_params.legend_item_gap_px))
        swatch_bbox = (
            legend_x,
            swatch_top,
            float(legend_x + render_params.legend_swatch_size_px),
            float(swatch_top + render_params.legend_swatch_size_px),
        )
        draw.rounded_rectangle(
            swatch_bbox,
            radius=6,
            fill=tuple(int(channel) for channel in legend_spec["fill_rgb"]),
            outline=border_rgb,
            width=max(1, int(render_params.region_border_width_px - 1)),
        )
        text_center = (
            float(swatch_bbox[2] + 88),
            float((swatch_bbox[1] + swatch_bbox[3]) * 0.5),
        )
        draw_text_centered(
            draw,
            text=str(legend_spec["category_label"]),
            center=text_center,
            font=legend_font,
            fill=render_params.label_color_rgb,
            stroke_fill=render_params.label_stroke_rgb,
            stroke_width=max(1, int(round(render_params.legend_font_size_px * 0.06))),
        )
        entry_bbox = (
            float(swatch_bbox[0]),
            float(swatch_bbox[1]),
            float(legend_panel_bbox[2] - 24),
            float(swatch_bbox[3]),
        )
        legend_entry_bbox_map[str(legend_spec["legend_entry_id"])] = [round(float(value), 3) for value in entry_bbox]
        entities.append(
            {
                "entity_id": str(legend_spec["legend_entry_id"]),
                "entity_type": "map_legend_entry",
                "bbox_px": [round(float(value), 3) for value in entry_bbox],
                "attrs": {
                    "category_index": int(legend_spec["category_index"]),
                    "category_label": str(legend_spec["category_label"]),
                    "fill_rgb": [int(channel) for channel in legend_spec["fill_rgb"]],
                },
            }
        )

    return RenderedRegionMapScene(
        image=image,
        entities=entities,
        region_bbox_map=region_bbox_map,
        legend_entry_bbox_map=legend_entry_bbox_map,
        map_bbox_px=[round(float(value), 3) for value in map_bbox],
        legend_bbox_px=[round(float(value), 3) for value in legend_panel_bbox],
        divider_bbox_px=[round(float(value), 3) for value in divider_bbox],
    )


__all__ = [
    "RenderedRegionMapScene",
    "render_region_map_scene",
]
