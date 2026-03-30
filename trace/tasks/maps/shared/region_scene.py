"""Renderer for stylized choropleth region-map scenes with legends."""

from __future__ import annotations

import random
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


def _cell_polygon(
    *,
    cell_x: int,
    cell_y: int,
    map_bbox: BBox,
    cols: int,
    rows: int,
    vertex_grid: Mapping[Tuple[int, int], Tuple[float, float]] | None = None,
) -> List[Tuple[float, float]]:
    """Return one cell polygon, optionally with a jittered shared vertex grid."""

    if vertex_grid is None:
        left, top, right, bottom = _cell_bbox(
            cell_x=int(cell_x),
            cell_y=int(cell_y),
            map_bbox=map_bbox,
            cols=int(cols),
            rows=int(rows),
        )
        return [
            (float(left), float(top)),
            (float(right), float(top)),
            (float(right), float(bottom)),
            (float(left), float(bottom)),
        ]
    return [
        tuple(float(value) for value in vertex_grid[(int(cell_x), int(cell_y))]),
        tuple(float(value) for value in vertex_grid[(int(cell_x) + 1, int(cell_y))]),
        tuple(float(value) for value in vertex_grid[(int(cell_x) + 1, int(cell_y) + 1)]),
        tuple(float(value) for value in vertex_grid[(int(cell_x), int(cell_y) + 1)]),
    ]


def _polygon_bbox(points: Sequence[Tuple[float, float]]) -> BBox:
    """Return one axis-aligned bbox that encloses a polygon."""

    return (
        float(min(point[0] for point in points)),
        float(min(point[1] for point in points)),
        float(max(point[0] for point in points)),
        float(max(point[1] for point in points)),
    )


def _build_jittered_vertex_grid(
    *,
    map_bbox: BBox,
    cols: int,
    rows: int,
    geometry_seed: int,
) -> Dict[Tuple[int, int], Tuple[float, float]]:
    """Build one shared jittered grid so the atlas-style scene reads less like a table."""

    rng = random.Random(int(geometry_seed) ^ 0x5D0F57)
    map_left, map_top, map_right, map_bottom = [float(value) for value in map_bbox]
    cell_width = (float(map_right) - float(map_left)) / float(max(1, int(cols)))
    cell_height = (float(map_bottom) - float(map_top)) / float(max(1, int(rows)))
    jitter_x = float(cell_width * 0.16)
    jitter_y = float(cell_height * 0.16)
    vertex_grid: Dict[Tuple[int, int], Tuple[float, float]] = {}

    for vertex_y in range(int(rows) + 1):
        for vertex_x in range(int(cols) + 1):
            base_x = float(map_left + float(vertex_x) * cell_width)
            base_y = float(map_top + float(vertex_y) * cell_height)
            offset_x = float(rng.uniform(-jitter_x, jitter_x))
            offset_y = float(rng.uniform(-jitter_y, jitter_y))

            if int(vertex_x) == 0:
                offset_x = float(rng.uniform(-jitter_x * 0.65, jitter_x * 0.15))
            elif int(vertex_x) == int(cols):
                offset_x = float(rng.uniform(-jitter_x * 0.15, jitter_x * 0.65))
            if int(vertex_y) == 0:
                offset_y = float(rng.uniform(-jitter_y * 0.65, jitter_y * 0.15))
            elif int(vertex_y) == int(rows):
                offset_y = float(rng.uniform(-jitter_y * 0.15, jitter_y * 0.65))
            if int(vertex_x) in {0, int(cols)} and int(vertex_y) in {0, int(rows)}:
                offset_x *= 0.35
                offset_y *= 0.35

            vertex_grid[(int(vertex_x), int(vertex_y))] = (
                float(base_x + offset_x),
                float(base_y + offset_y),
            )
    return vertex_grid


def _draw_compass(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    size_px: float,
    fill_rgb: Tuple[int, int, int],
    stroke_rgb: Tuple[int, int, int],
    font,
) -> BBox:
    """Draw a simple north arrow inside the atlas-like region-map scene."""

    center_x = float(center[0])
    center_y = float(center[1])
    half_width = float(size_px * 0.22)
    shaft_top = float(center_y - size_px * 0.42)
    shaft_bottom = float(center_y + size_px * 0.28)
    arrow_points = [
        (float(center_x), float(shaft_top)),
        (float(center_x + half_width), float(center_y - size_px * 0.02)),
        (float(center_x - half_width), float(center_y - size_px * 0.02)),
    ]
    draw.polygon(arrow_points, fill=tuple(int(channel) for channel in fill_rgb), outline=tuple(int(channel) for channel in stroke_rgb))
    draw.line(
        (float(center_x), float(center_y - size_px * 0.02), float(center_x), float(shaft_bottom)),
        fill=tuple(int(channel) for channel in stroke_rgb),
        width=max(2, int(round(size_px * 0.08))),
    )
    draw_text_centered(
        draw,
        text="N",
        center=(float(center_x), float(shaft_top - size_px * 0.18)),
        font=font,
        fill=stroke_rgb,
    )
    return (
        float(center_x - size_px * 0.5),
        float(shaft_top - size_px * 0.34),
        float(center_x + size_px * 0.5),
        float(shaft_bottom + size_px * 0.1),
    )


def render_region_map_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    geometry_seed: int,
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

    border_rgb = tuple(int(channel) for channel in render_params.border_color_rgb)
    water_rgb = (220, 233, 243)
    graticule_rgb = (188, 206, 220)
    atlas_legend_fill_rgb = (253, 251, 245)

    if str(scene_variant) == "region_map":
        _rounded_panel(
            draw,
            map_panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=water_rgb,
            outline=border_rgb,
            width=int(render_params.outer_border_width_px),
        )
        _rounded_panel(
            draw,
            legend_panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=atlas_legend_fill_rgb,
            outline=border_rgb,
            width=int(render_params.outer_border_width_px),
        )
    elif str(scene_variant) in {"map_strip", "map_card"}:
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
    if str(scene_variant) != "region_map":
        draw.rounded_rectangle(
            divider_bbox,
            radius=1,
            fill=tuple(int(channel) for channel in render_params.divider_rgb),
            outline=None,
        )

    map_padding_px = int(render_params.map_padding_px + (28 if str(scene_variant) == "region_map" else 0))
    map_bbox = (
        float(map_panel_bbox[0] + map_padding_px),
        float(map_panel_bbox[1] + map_padding_px),
        float(map_panel_bbox[2] - map_padding_px),
        float(map_panel_bbox[3] - map_padding_px),
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
    vertex_grid = None

    if str(scene_variant) == "region_map":
        for longitude_fraction in (0.22, 0.5, 0.78):
            x = float(map_panel_bbox[0] + longitude_fraction * (map_panel_bbox[2] - map_panel_bbox[0]))
            draw.line(
                (x, float(map_panel_bbox[1] + 14), x, float(map_panel_bbox[3] - 14)),
                fill=graticule_rgb,
                width=1,
            )
        for latitude_fraction in (0.3, 0.58):
            y = float(map_panel_bbox[1] + latitude_fraction * (map_panel_bbox[3] - map_panel_bbox[1]))
            draw.line(
                (float(map_panel_bbox[0] + 14), y, float(map_panel_bbox[2] - 14), y),
                fill=graticule_rgb,
                width=1,
            )
        compass_bbox = _draw_compass(
            draw,
            center=(float(map_panel_bbox[0] + 42), float(map_panel_bbox[1] + 52)),
            size_px=44.0,
            fill_rgb=border_rgb,
            stroke_rgb=border_rgb,
            font=legend_font,
        )
        entities.append(
            {
                "entity_id": "map_compass",
                "entity_type": "map_compass",
                "bbox_px": [round(float(value), 3) for value in compass_bbox],
                "attrs": {"direction": "north"},
            }
        )
        vertex_grid = _build_jittered_vertex_grid(
            map_bbox=map_bbox,
            cols=int(grid_cols),
            rows=int(grid_rows),
            geometry_seed=int(geometry_seed),
        )

    for region_spec in region_specs:
        cells = [(int(cell[0]), int(cell[1])) for cell in region_spec["cells"]]
        fill_rgb = tuple(int(channel) for channel in region_spec["fill_rgb"])
        cell_polygons = [
            _cell_polygon(
                cell_x=int(cell_x),
                cell_y=int(cell_y),
                map_bbox=map_bbox,
                cols=int(grid_cols),
                rows=int(grid_rows),
                vertex_grid=vertex_grid,
            )
            for cell_x, cell_y in cells
        ]
        cell_bboxes = []
        for polygon in cell_polygons:
            draw.polygon(polygon, fill=fill_rgb)
            cell_bboxes.append(_polygon_bbox(polygon))
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
    for region_spec in region_specs:
        region_cells = {(int(cell[0]), int(cell[1])) for cell in region_spec["cells"]}
        for cell_x, cell_y in region_cells:
            neighbors = {
                "left": (int(cell_x) - 1, int(cell_y)),
                "right": (int(cell_x) + 1, int(cell_y)),
                "up": (int(cell_x), int(cell_y) - 1),
                "down": (int(cell_x), int(cell_y) + 1),
            }
            polygon = _cell_polygon(
                cell_x=int(cell_x),
                cell_y=int(cell_y),
                map_bbox=map_bbox,
                cols=int(grid_cols),
                rows=int(grid_rows),
                vertex_grid=vertex_grid,
            )
            left_top, right_top, right_bottom, left_bottom = polygon
            if neighbors["left"] not in region_cells:
                draw.line(
                    (left_top[0], left_top[1], left_bottom[0], left_bottom[1]),
                    fill=border_rgb,
                    width=int(render_params.region_border_width_px),
                )
            if neighbors["right"] not in region_cells:
                draw.line(
                    (right_top[0], right_top[1], right_bottom[0], right_bottom[1]),
                    fill=border_rgb,
                    width=int(render_params.region_border_width_px),
                )
            if neighbors["up"] not in region_cells:
                draw.line(
                    (left_top[0], left_top[1], right_top[0], right_top[1]),
                    fill=border_rgb,
                    width=int(render_params.region_border_width_px),
                )
            if neighbors["down"] not in region_cells:
                draw.line(
                    (left_bottom[0], left_bottom[1], right_bottom[0], right_bottom[1]),
                    fill=border_rgb,
                    width=int(render_params.region_border_width_px),
                )

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
