"""Rendering helpers for polyomino missing-piece puzzle scenes."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.tasks.puzzles.shared.drawing import draw_rounded_rect
from trace.tasks.puzzles.shared.option_layout import (
    centered_option_grid_shape,
    centered_option_row_counts,
)
from trace.tasks.puzzles.shared.option_panels import render_puzzle_option_panel
from trace.tasks.shared.text_rendering import load_font

from .rules import polyomino_bbox_dims
from .state import (
    Cell,
    CustomRenderParams,
    PolyominoOptionRenderParams,
    RenderedPolyominoMissingScene,
)


def draw_cells_at_origin(
    draw: ImageDraw.ImageDraw,
    *,
    origin_x: float,
    origin_y: float,
    cells: Iterable[Sequence[int]],
    cell_size_px: float,
    cell_gap_px: float,
    fill_rgb: Sequence[int],
    outline_rgb: Sequence[int],
    border_width_px: int,
    cell_corner_radius_px: int,
    marked_cells: set[Cell] | None = None,
    marked_fill_rgb: Sequence[int] | None = None,
) -> Tuple[List[List[float]], Dict[Cell, List[float]]]:
    """Draw one cell set at an explicit origin and return cell bboxes."""

    marked = set(marked_cells or set())
    marked_fill = tuple(marked_fill_rgb or fill_rgb)
    bboxes: List[List[float]] = []
    bbox_by_cell: Dict[Cell, List[float]] = {}
    for raw_cell in cells:
        cell_x, cell_y = int(raw_cell[0]), int(raw_cell[1])
        left = float(origin_x + int(cell_x) * (float(cell_size_px) + float(cell_gap_px)))
        top = float(origin_y + int(cell_y) * (float(cell_size_px) + float(cell_gap_px)))
        bbox = [
            round(left, 3),
            round(top, 3),
            round(left + float(cell_size_px), 3),
            round(top + float(cell_size_px), 3),
        ]
        draw_rounded_rect(
            draw,
            tuple(bbox),
            radius=int(cell_corner_radius_px),
            fill=marked_fill if (cell_x, cell_y) in marked else fill_rgb,
            outline=outline_rgb,
            width=int(border_width_px),
        )
        bboxes.append(list(bbox))
        bbox_by_cell[(cell_x, cell_y)] = list(bbox)
    return bboxes, bbox_by_cell


def _draw_polyomino(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[float, float, float, float],
    cells: Sequence[Sequence[int]],
    fill_rgb: Sequence[int],
    outline_rgb: Sequence[int],
    border_width_px: int,
    cell_size_px: float,
    cell_gap_px: float,
    cell_corner_radius_px: int,
) -> List[List[float]]:
    """Draw one polyomino centered inside a target bounding box."""

    canonical = tuple((int(cell[0]), int(cell[1])) for cell in cells)
    width_cells, height_cells = polyomino_bbox_dims(canonical)
    left, top, right, bottom = [float(value) for value in bbox]
    available_width = float(right - left)
    available_height = float(bottom - top)
    cell_gap = max(0.0, float(cell_gap_px))
    max_unit_w = (
        available_width - max(0, width_cells - 1) * cell_gap
    ) / max(1, width_cells)
    max_unit_h = (
        available_height - max(0, height_cells - 1) * cell_gap
    ) / max(1, height_cells)
    unit = min(float(cell_size_px), float(max_unit_w), float(max_unit_h))
    if unit <= 0:
        raise ValueError("polyomino does not fit inside the target bbox")
    shape_width = float(width_cells * unit + max(0, width_cells - 1) * cell_gap)
    shape_height = float(height_cells * unit + max(0, height_cells - 1) * cell_gap)
    origin_x = float(left + 0.5 * (available_width - shape_width))
    origin_y = float(top + 0.5 * (available_height - shape_height))
    bboxes: List[List[float]] = []
    for cell_x, cell_y in canonical:
        cell_left = float(origin_x + int(cell_x) * (unit + cell_gap))
        cell_top = float(origin_y + int(cell_y) * (unit + cell_gap))
        cell_bbox = (
            float(cell_left),
            float(cell_top),
            float(cell_left + unit),
            float(cell_top + unit),
        )
        draw_rounded_rect(
            draw,
            cell_bbox,
            radius=int(cell_corner_radius_px),
            fill=fill_rgb,
            outline=outline_rgb,
            width=int(border_width_px),
        )
        bboxes.append([round(float(value), 3) for value in cell_bbox])
    return bboxes


def render_polyomino_missing_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    dataset: Mapping[str, Any],
    render_params: PolyominoOptionRenderParams,
    custom_params: CustomRenderParams,
) -> RenderedPolyominoMissingScene:
    """Render the target region and labeled option-piece panels."""

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    target_cells = tuple((int(cell[0]), int(cell[1])) for cell in dataset["target_cells"])
    visible_target_cells = tuple(
        (int(cell[0]), int(cell[1]))
        for cell in dataset.get("visible_target_cells", dataset["target_cells"])
    )
    missing_cells = {
        (int(cell[0]), int(cell[1]))
        for cell in dataset.get("missing_cells", dataset.get("marked_cells", []))
    }
    target_width, target_height = polyomino_bbox_dims(target_cells)
    target_cell_size = float(custom_params.target_cell_size_px)
    target_cell_gap = float(custom_params.target_cell_gap_px)
    target_width_px = float(target_width * target_cell_size + max(0, target_width - 1) * target_cell_gap)
    target_height_px = float(target_height * target_cell_size + max(0, target_height - 1) * target_cell_gap)

    option_count = int(dataset["option_count"])
    option_panel_width = float(render_params.option_panel_width_px)
    option_panel_height = float(render_params.option_panel_height_px)
    option_gap = float(render_params.option_gap_px)
    option_row_gap = float(render_params.option_row_gap_px)
    option_cols, option_rows = centered_option_grid_shape(option_count)
    options_width = float(option_cols * option_panel_width + max(0, option_cols - 1) * option_gap)
    options_height = float(option_rows * option_panel_height + max(0, option_rows - 1) * option_row_gap)
    content_width = float(max(target_width_px, options_width))
    content_height = float(target_height_px + render_params.piece_to_options_gap_px + options_height)
    usable_width = float(
        render_params.canvas_width
        - render_params.scene_margin_left_px
        - render_params.scene_margin_right_px
    )
    usable_height = float(
        render_params.canvas_height
        - render_params.scene_margin_top_px
        - render_params.scene_margin_bottom_px
    )
    content_left = float(render_params.scene_margin_left_px + max(0.0, 0.5 * (usable_width - content_width)))
    content_top = float(render_params.scene_margin_top_px + max(0.0, 0.5 * (usable_height - content_height)))
    target_left = float(content_left + 0.5 * (content_width - target_width_px))
    target_top = float(content_top)
    options_left = float(content_left + 0.5 * (content_width - options_width))
    options_top = float(target_top + target_height_px + render_params.piece_to_options_gap_px)
    panel_padding = float(render_params.piece_panel_padding_px)
    target_panel_bbox = (
        float(target_left - panel_padding),
        float(target_top - panel_padding),
        float(target_left + target_width_px + panel_padding),
        float(target_top + target_height_px + panel_padding),
    )
    options_panel_bbox = (
        float(options_left - panel_padding),
        float(options_top - panel_padding),
        float(options_left + options_width + panel_padding),
        float(options_top + options_height + panel_padding),
    )

    entities: List[Dict[str, Any]] = []
    if str(scene_variant) in {"polyomino_card", "polyomino_outline"}:
        panel_fill = (
            render_params.panel_fill_rgb
            if str(scene_variant) == "polyomino_card"
            else (248, 248, 248)
        )
        for panel_id, panel_bbox, panel_role in (
            ("polyomino_target_panel", target_panel_bbox, "target"),
            ("polyomino_options_panel", options_panel_bbox, "options"),
        ):
            draw_rounded_rect(
                draw,
                panel_bbox,
                radius=int(render_params.panel_corner_radius_px),
                fill=panel_fill,
                outline=render_params.border_color_rgb,
                width=int(render_params.border_width_px),
            )
            entities.append(
                {
                    "entity_id": panel_id,
                    "entity_type": "puzzle_polyomino_panel",
                    "bbox_px": [round(float(value), 3) for value in panel_bbox],
                    "attrs": {
                        "panel_role": str(panel_role),
                        "scene_variant": str(scene_variant),
                    },
                }
            )

    cell_bboxes, bbox_by_cell = draw_cells_at_origin(
        draw,
        origin_x=float(target_left),
        origin_y=float(target_top),
        cells=visible_target_cells,
        cell_size_px=float(target_cell_size),
        cell_gap_px=float(target_cell_gap),
        fill_rgb=custom_params.target_cell_rgb,
        outline_rgb=render_params.border_color_rgb,
        border_width_px=max(1, int(render_params.border_width_px)),
        cell_corner_radius_px=int(render_params.cell_corner_radius_px),
    )
    _missing_bboxes, missing_bbox_by_cell = draw_cells_at_origin(
        draw,
        origin_x=float(target_left),
        origin_y=float(target_top),
        cells=missing_cells,
        cell_size_px=float(target_cell_size),
        cell_gap_px=float(target_cell_gap),
        fill_rgb=custom_params.missing_cell_rgb,
        outline_rgb=render_params.border_color_rgb,
        border_width_px=max(1, int(render_params.border_width_px)),
        cell_corner_radius_px=int(render_params.cell_corner_radius_px),
    )
    bbox_by_cell.update(missing_bbox_by_cell)

    for cell, bbox in zip(visible_target_cells, cell_bboxes):
        entities.append(
            {
                "entity_id": f"target_cell_{int(cell[0])}_{int(cell[1])}",
                "entity_type": "puzzle_polyomino_target_cell",
                "bbox_px": list(bbox),
                "attrs": {"x": int(cell[0]), "y": int(cell[1]), "missing": False},
            }
        )
    for cell in sorted(missing_cells):
        entities.append(
            {
                "entity_id": f"missing_cell_{int(cell[0])}_{int(cell[1])}",
                "entity_type": "puzzle_polyomino_missing_cell",
                "bbox_px": list(bbox_by_cell[cell]),
                "attrs": {"x": int(cell[0]), "y": int(cell[1]), "missing": True},
            }
        )

    option_entities, option_bbox_map = render_option_panels(
        draw,
        options=list(dataset["option_specs"]),
        options_left=float(options_left),
        options_top=float(options_top),
        option_panel_width=float(option_panel_width),
        option_panel_height=float(option_panel_height),
        option_gap=float(option_gap),
        option_row_gap=float(option_row_gap),
        render_params=render_params,
    )
    entities.extend(option_entities)

    marked_bbox = [0.0, 0.0, 0.0, 0.0]
    if missing_cells:
        missing_cell_bboxes = [bbox_by_cell[cell] for cell in sorted(missing_cells)]
        marked_bbox = [
            min(float(bbox[0]) for bbox in missing_cell_bboxes),
            min(float(bbox[1]) for bbox in missing_cell_bboxes),
            max(float(bbox[2]) for bbox in missing_cell_bboxes),
            max(float(bbox[3]) for bbox in missing_cell_bboxes),
        ]
    bbox_map = dict(option_bbox_map)
    bbox_map["missing_region"] = [round(float(value), 3) for value in marked_bbox]
    scene_bbox = [
        round(float(min(target_panel_bbox[0], options_panel_bbox[0])), 3),
        round(float(min(target_panel_bbox[1], options_panel_bbox[1])), 3),
        round(float(max(target_panel_bbox[2], options_panel_bbox[2])), 3),
        round(float(max(target_panel_bbox[3], options_panel_bbox[3])), 3),
    ]
    return RenderedPolyominoMissingScene(
        image=image,
        entities=entities,
        scene_bbox_px=scene_bbox,
        bbox_map=bbox_map,
    )


def render_option_panels(
    draw: ImageDraw.ImageDraw,
    *,
    options: Sequence[Mapping[str, Any]],
    options_left: float,
    options_top: float,
    option_panel_width: float,
    option_panel_height: float,
    option_gap: float,
    option_row_gap: float,
    render_params: PolyominoOptionRenderParams,
) -> Tuple[List[Dict[str, Any]], Dict[str, List[float]]]:
    """Render labeled polyomino option panels and return their bboxes."""

    option_label_font = load_font(int(render_params.option_label_font_size_px), bold=True)
    option_cols, _option_rows = centered_option_grid_shape(len(options))
    option_row_counts = centered_option_row_counts(len(options), option_cols)
    options_width = float((option_cols * option_panel_width) + max(0, option_cols - 1) * option_gap)
    entities: List[Dict[str, Any]] = []
    bbox_map: Dict[str, List[float]] = {}
    for option_index, option in enumerate(options):
        row_index = int(option_index // option_cols)
        row_option_count = int(option_row_counts[row_index])
        row_base_index = int(sum(option_row_counts[:row_index]))
        col_index = int(option_index - row_base_index)
        row_width = float(row_option_count * option_panel_width + max(0, row_option_count - 1) * option_gap)
        row_left = float(options_left + 0.5 * (options_width - row_width))
        panel_left = float(row_left + col_index * (option_panel_width + option_gap))
        panel_top = float(options_top + row_index * (option_panel_height + option_row_gap))
        panel_bbox = (
            float(panel_left),
            float(panel_top),
            float(panel_left + option_panel_width),
            float(panel_top + option_panel_height),
        )
        option_panel_id = str(option["option_panel_id"])
        rendered = render_puzzle_option_panel(
            draw,
            panel_bbox=panel_bbox,
            option_label=str(option["option_label"]),
            label_font=option_label_font,
            label_center_y_px=float(panel_top + 28.0),
            content_box_size_px=float(render_params.option_shape_box_size_px),
            content_gap_px=float(render_params.option_label_gap_px),
            panel_fill_rgb=render_params.option_panel_fill_rgb,
            content_fill_rgb=render_params.option_shape_fill_rgb,
            border_color_rgb=render_params.border_color_rgb,
            text_color_rgb=render_params.text_color_rgb,
            text_stroke_rgb=render_params.text_stroke_rgb,
            panel_corner_radius_px=int(render_params.panel_corner_radius_px),
            content_corner_radius_px=int(max(12, render_params.panel_corner_radius_px // 2)),
            border_width_px=int(render_params.border_width_px),
        )
        bbox_map[option_panel_id] = list(rendered.panel_bbox)
        entities.append(
            {
                "entity_id": option_panel_id,
                "entity_type": "puzzle_polyomino_option_panel",
                "bbox_px": list(rendered.panel_bbox),
                "attrs": {
                    "option_index": int(option_index),
                    "option_label": str(option["option_label"]),
                    "is_correct": bool(option["is_correct"]),
                },
            }
        )
        poly_bboxes = _draw_polyomino(
            draw,
            bbox=tuple(rendered.content_bbox),
            cells=option["cells"],
            fill_rgb=render_params.shape_fill_rgb,
            outline_rgb=render_params.border_color_rgb,
            border_width_px=max(1, int(render_params.border_width_px)),
            cell_size_px=float(render_params.shape_cell_size_px),
            cell_gap_px=float(render_params.shape_cell_gap_px),
            cell_corner_radius_px=int(render_params.cell_corner_radius_px),
        )
        for cell_index, cell_bbox in enumerate(poly_bboxes, start=1):
            entities.append(
                {
                    "entity_id": f"{option_panel_id}_cell_{int(cell_index)}",
                    "entity_type": "puzzle_polyomino_option_cell",
                    "bbox_px": list(cell_bbox),
                    "attrs": {
                        "option_panel_id": str(option_panel_id),
                        "option_label": str(option["option_label"]),
                    },
                }
            )
    return entities, bbox_map


__all__ = [
    "draw_cells_at_origin",
    "render_option_panels",
    "render_polyomino_missing_scene",
]
