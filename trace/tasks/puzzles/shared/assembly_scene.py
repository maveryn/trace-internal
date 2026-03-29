"""Shared rendering helpers for spatial assembly puzzle scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font
from .assembly_common import PuzzleAssemblyRenderParams, SUPPORTED_PUZZLE_ASSEMBLY_SCENE_VARIANTS, polyomino_bbox_dims
from .drawing import draw_rounded_rect
from .option_layout import centered_option_grid_shape, centered_option_row_counts
from .option_panels import render_puzzle_option_panel


@dataclass(frozen=True)
class RenderedPuzzleAssemblyScene:
    """Rendered assembly puzzle image plus traced reference/option geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    piece_card_bbox_map: Dict[str, List[float]]
    option_panel_bbox_map: Dict[str, List[float]]


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
    """Draw one polyomino with a fixed unit cell size centered inside `bbox`."""

    canonical = tuple((int(cell[0]), int(cell[1])) for cell in cells)
    width_cells, height_cells = polyomino_bbox_dims(canonical)
    left, top, right, bottom = [float(value) for value in bbox]
    available_width = float(right - left)
    available_height = float(bottom - top)
    unit = float(cell_size_px)
    cell_gap = max(0.0, float(cell_gap_px))
    shape_width = float(width_cells * unit + max(0, width_cells - 1) * cell_gap)
    shape_height = float(height_cells * unit + max(0, height_cells - 1) * cell_gap)
    if shape_width > available_width or shape_height > available_height:
        raise ValueError("polyomino does not fit inside the target bbox with the fixed cell size")
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


def render_puzzle_assembly_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    piece_specs: Sequence[Mapping[str, Any]],
    option_specs: Sequence[Mapping[str, Any]],
    render_params: PuzzleAssemblyRenderParams,
) -> RenderedPuzzleAssemblyScene:
    """Render one spatial assembly puzzle with reference pieces and image options."""

    selected_variant = str(scene_variant)
    if selected_variant not in set(SUPPORTED_PUZZLE_ASSEMBLY_SCENE_VARIANTS):
        raise ValueError(f"unsupported puzzle assembly scene_variant: {scene_variant}")
    pieces = [dict(piece) for piece in piece_specs]
    options = [dict(option) for option in option_specs]
    if len(pieces) < 2:
        raise ValueError("assembly scenes require at least two pieces")
    if len(options) < 2:
        raise ValueError("assembly scenes require at least two options")

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    option_label_font = load_font(int(render_params.option_label_font_size_px), bold=True)

    piece_card_size = float(render_params.piece_card_size_px)
    piece_gap = float(render_params.piece_gap_px)
    piece_row_width = float((len(pieces) * piece_card_size) + max(0, len(pieces) - 1) * piece_gap)
    piece_row_height = float(piece_card_size)

    option_panel_width = float(render_params.option_panel_width_px)
    option_panel_height = float(render_params.option_panel_height_px)
    option_gap = float(render_params.option_gap_px)
    option_row_gap = float(render_params.option_row_gap_px)
    option_cols, option_rows = centered_option_grid_shape(len(options))
    option_row_counts = centered_option_row_counts(len(options), option_cols)
    options_width = float((option_cols * option_panel_width) + max(0, option_cols - 1) * option_gap)
    options_height = float((option_rows * option_panel_height) + max(0, option_rows - 1) * option_row_gap)
    piece_to_options_gap = float(render_params.piece_to_options_gap_px)
    panel_padding = float(render_params.piece_panel_padding_px)

    content_width = float(max(piece_row_width, options_width))
    content_height = float(piece_row_height + piece_to_options_gap + options_height)
    usable_width = float(
        render_params.canvas_width - render_params.scene_margin_left_px - render_params.scene_margin_right_px
    )
    usable_height = float(
        render_params.canvas_height - render_params.scene_margin_top_px - render_params.scene_margin_bottom_px
    )
    content_left = float(render_params.scene_margin_left_px + max(0.0, 0.5 * (usable_width - content_width)))
    content_top = float(render_params.scene_margin_top_px + max(0.0, 0.5 * (usable_height - content_height)))

    pieces_left = float(content_left + 0.5 * (content_width - piece_row_width))
    pieces_top = float(content_top)
    options_left = float(content_left + 0.5 * (content_width - options_width))
    options_top = float(pieces_top + piece_row_height + piece_to_options_gap)

    entities: List[Dict[str, Any]] = []
    piece_card_bbox_map: Dict[str, List[float]] = {}
    option_panel_bbox_map: Dict[str, List[float]] = {}

    pieces_panel_bbox = (
        float(pieces_left - panel_padding),
        float(pieces_top - panel_padding),
        float(pieces_left + piece_row_width + panel_padding),
        float(pieces_top + piece_row_height + panel_padding),
    )
    options_panel_bbox = (
        float(options_left - panel_padding),
        float(options_top - panel_padding),
        float(options_left + options_width + panel_padding),
        float(options_top + options_height + panel_padding),
    )
    if selected_variant in {"assembly_card", "assembly_outline"}:
        fill = render_params.panel_fill_rgb if selected_variant == "assembly_card" else (248, 248, 248)
        draw_rounded_rect(
            draw,
            pieces_panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=fill,
            outline=render_params.border_color_rgb,
            width=int(render_params.border_width_px),
        )
        draw_rounded_rect(
            draw,
            options_panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=fill,
            outline=render_params.border_color_rgb,
            width=int(render_params.border_width_px),
        )
        entities.extend(
            [
                {
                    "entity_id": "assembly_pieces_panel",
                    "entity_type": "puzzle_assembly_panel",
                    "bbox_px": [round(float(value), 3) for value in pieces_panel_bbox],
                    "attrs": {"panel_role": "pieces", "scene_variant": selected_variant},
                },
                {
                    "entity_id": "assembly_options_panel",
                    "entity_type": "puzzle_assembly_panel",
                    "bbox_px": [round(float(value), 3) for value in options_panel_bbox],
                    "attrs": {"panel_role": "options", "scene_variant": selected_variant},
                },
            ]
        )

    for piece_index, piece in enumerate(pieces):
        piece_left = float(pieces_left + piece_index * (piece_card_size + piece_gap))
        piece_top = float(pieces_top)
        piece_bbox = (
            float(piece_left),
            float(piece_top),
            float(piece_left + piece_card_size),
            float(piece_top + piece_card_size),
        )
        piece_id = str(piece["piece_id"])
        draw_rounded_rect(
            draw,
            piece_bbox,
            radius=int(render_params.panel_corner_radius_px * 0.72),
            fill=render_params.piece_card_fill_rgb,
            outline=render_params.border_color_rgb,
            width=int(render_params.border_width_px),
        )
        inner_padding = float(16.0)
        poly_bboxes = _draw_polyomino(
            draw,
            bbox=(
                float(piece_bbox[0] + inner_padding),
                float(piece_bbox[1] + inner_padding),
                float(piece_bbox[2] - inner_padding),
                float(piece_bbox[3] - inner_padding),
            ),
            cells=piece["cells"],
            fill_rgb=render_params.shape_fill_rgb,
            outline_rgb=render_params.border_color_rgb,
            border_width_px=max(1, int(render_params.border_width_px)),
            cell_size_px=float(render_params.shape_cell_size_px),
            cell_gap_px=float(render_params.shape_cell_gap_px),
            cell_corner_radius_px=int(render_params.cell_corner_radius_px),
        )
        bbox_list = [round(float(value), 3) for value in piece_bbox]
        piece_card_bbox_map[piece_id] = list(bbox_list)
        entities.append(
            {
                "entity_id": piece_id,
                "entity_type": "puzzle_assembly_piece_card",
                "bbox_px": list(bbox_list),
                "attrs": {
                    "piece_index": int(piece_index),
                    "cell_count": int(piece["cell_count"]),
                },
            }
        )
        for cell_index, cell_bbox in enumerate(poly_bboxes, start=1):
            entities.append(
                {
                    "entity_id": f"{piece_id}_cell_{int(cell_index)}",
                    "entity_type": "puzzle_assembly_piece_cell",
                    "bbox_px": list(cell_bbox),
                    "attrs": {
                        "piece_id": str(piece_id),
                        "piece_index": int(piece_index),
                        "fill_rgb": list(render_params.shape_fill_rgb),
                    },
                }
            )

    for option_index, option in enumerate(options):
        row_index = int(option_index // option_cols)
        row_option_count = int(option_row_counts[row_index])
        row_base_index = int(sum(option_row_counts[:row_index]))
        col_index = int(option_index - row_base_index)
        row_width = float(
            row_option_count * option_panel_width + max(0, row_option_count - 1) * option_gap
        )
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
        option_panel_bbox_map[option_panel_id] = list(rendered.panel_bbox)
        entities.append(
            {
                "entity_id": option_panel_id,
                "entity_type": "puzzle_assembly_option_panel",
                "bbox_px": list(rendered.panel_bbox),
                "attrs": {
                    "option_index": int(option_index),
                    "option_label": str(option["option_label"]),
                    "is_correct": bool(option["is_correct"]),
                },
            }
        )
        entities.append(
            {
                "entity_id": f"{option_panel_id}_label",
                "entity_type": "puzzle_assembly_option_label",
                "bbox_px": list(rendered.label_bbox),
                "attrs": {
                    "option_panel_id": str(option_panel_id),
                    "option_label": str(option["option_label"]),
                },
            }
        )
        entities.append(
            {
                "entity_id": f"{option_panel_id}_shape_box",
                "entity_type": "puzzle_assembly_option_shape_box",
                "bbox_px": list(rendered.content_bbox),
                "attrs": {"option_panel_id": str(option_panel_id)},
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
                    "entity_type": "puzzle_assembly_option_shape_cell",
                    "bbox_px": list(cell_bbox),
                    "attrs": {
                        "option_panel_id": str(option_panel_id),
                        "option_label": str(option["option_label"]),
                        "is_correct": bool(option["is_correct"]),
                    },
                }
            )

    scene_bbox = [
        round(float(min(pieces_panel_bbox[0], options_panel_bbox[0])), 3),
        round(float(min(pieces_panel_bbox[1], options_panel_bbox[1])), 3),
        round(float(max(pieces_panel_bbox[2], options_panel_bbox[2])), 3),
        round(float(max(pieces_panel_bbox[3], options_panel_bbox[3])), 3),
    ]
    return RenderedPuzzleAssemblyScene(
        image=image,
        entities=entities,
        scene_bbox_px=list(scene_bbox),
        piece_card_bbox_map=piece_card_bbox_map,
        option_panel_bbox_map=option_panel_bbox_map,
    )


__all__ = [
    "RenderedPuzzleAssemblyScene",
    "render_puzzle_assembly_scene",
]
