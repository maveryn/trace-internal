"""Shared rendering helpers for arithmetic puzzle grids with one unknown cell."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.drawing import draw_centered_text as _draw_centered_text, draw_rounded_rect as _rounded_rect
from ...shared.text_rendering import load_font


SUPPORTED_PUZZLE_GRID_SCENE_VARIANTS: Tuple[str, ...] = (
    "grid_strip",
    "grid_card",
    "grid_outline",
)


@dataclass(frozen=True)
class PuzzleGridRenderParams:
    """Resolved render parameters for one arithmetic puzzle grid scene."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    cell_width_px: int
    cell_height_px: int
    cell_gap_px: int
    slot_corner_radius_px: int
    border_width_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    value_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    cell_fill_rgb: Tuple[int, int, int]
    unknown_cell_fill_rgb: Tuple[int, int, int]
    border_color_rgb: Tuple[int, int, int]
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    accent_color_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class RenderedPuzzleGridScene:
    """Rendered arithmetic grid image plus per-cell geometry traces."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    cell_bbox_map: Dict[str, List[float]]


def _text_bbox(draw: ImageDraw.ImageDraw, text: str, *, font, stroke_width: int = 1) -> Tuple[float, float, float, float]:
    """Return one text bbox at the origin."""

    bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
    return float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])


def render_puzzle_grid_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    grid_rows: Sequence[Sequence[Mapping[str, Any]]],
    render_params: PuzzleGridRenderParams,
) -> RenderedPuzzleGridScene:
    """Render one arithmetic grid scene with a highlighted unknown cell."""

    selected_variant = str(scene_variant)
    if selected_variant not in set(SUPPORTED_PUZZLE_GRID_SCENE_VARIANTS):
        raise ValueError(f"unsupported puzzle grid scene_variant: {selected_variant}")
    rows = [[dict(cell) for cell in row] for row in grid_rows]
    if not rows:
        raise ValueError("grid scenes require at least one row")
    col_count = len(rows[0])
    if int(col_count) <= 0:
        raise ValueError("grid scenes require at least one column")
    if any(len(row) != int(col_count) for row in rows):
        raise ValueError("all puzzle grid rows must have the same number of columns")

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    value_font = load_font(int(render_params.value_font_size_px), bold=True)

    board_width = float((int(col_count) * int(render_params.cell_width_px)) + max(0, int(col_count) - 1) * int(render_params.cell_gap_px))
    board_height = float((len(rows) * int(render_params.cell_height_px)) + max(0, len(rows) - 1) * int(render_params.cell_gap_px))
    content_left = float(render_params.scene_margin_left_px)
    content_top = float(render_params.scene_margin_top_px)
    content_right = float(render_params.canvas_width - render_params.scene_margin_right_px)
    content_bottom = float(render_params.canvas_height - render_params.scene_margin_bottom_px)
    board_left = float(content_left + max(0.0, 0.5 * ((content_right - content_left) - board_width)))
    board_top = float(content_top + max(0.0, 0.5 * ((content_bottom - content_top) - board_height)))

    scene_union_boxes: List[List[float]] = []
    entities: List[Dict[str, Any]] = []
    cell_bbox_map: Dict[str, List[float]] = {}

    panel_bbox: Tuple[float, float, float, float] | None = None
    if selected_variant == "grid_card":
        panel_bbox = (
            float(max(0.0, board_left - float(render_params.panel_padding_px))),
            float(max(0.0, board_top - float(render_params.panel_padding_px))),
            float(min(float(render_params.canvas_width), board_left + board_width + float(render_params.panel_padding_px))),
            float(min(float(render_params.canvas_height), board_top + board_height + float(render_params.panel_padding_px))),
        )
        _rounded_rect(
            draw,
            panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=render_params.panel_fill_rgb,
            outline=render_params.border_color_rgb,
            width=max(1, int(render_params.border_width_px)),
        )

    for row_index, row in enumerate(rows):
        for col_index, cell in enumerate(row):
            left = float(board_left + (col_index * (int(render_params.cell_width_px) + int(render_params.cell_gap_px))))
            top = float(board_top + (row_index * (int(render_params.cell_height_px) + int(render_params.cell_gap_px))))
            bbox = (
                float(left),
                float(top),
                float(left + int(render_params.cell_width_px)),
                float(top + int(render_params.cell_height_px)),
            )
            is_unknown = bool(cell.get("is_unknown", False))
            if selected_variant == "grid_outline":
                fill_rgb = (255, 255, 255)
                outline_rgb = render_params.accent_color_rgb if is_unknown else render_params.border_color_rgb
            else:
                fill_rgb = render_params.unknown_cell_fill_rgb if is_unknown else render_params.cell_fill_rgb
                outline_rgb = render_params.border_color_rgb
            _rounded_rect(
                draw,
                bbox,
                radius=int(render_params.slot_corner_radius_px),
                fill=fill_rgb,
                outline=outline_rgb,
                width=int(render_params.border_width_px),
            )
            center = (float(0.5 * (bbox[0] + bbox[2])), float(0.5 * (bbox[1] + bbox[3])))
            text_bbox = _draw_centered_text(
                draw,
                text=str(cell["text"]),
                center=center,
                font=value_font,
                fill=render_params.text_color_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=1,
            )
            cell_id = str(cell["cell_id"])
            bbox_list = [round(float(value), 3) for value in bbox]
            cell_bbox_map[str(cell_id)] = list(bbox_list)
            scene_union_boxes.append(list(bbox_list))
            entities.append(
                {
                    "entity_id": str(cell_id),
                    "entity_type": "puzzle_grid_cell",
                    "bbox_px": list(bbox_list),
                    "attrs": {
                        "row_index": int(row_index),
                        "col_index": int(col_index),
                        "text": str(cell["text"]),
                        "value": cell.get("value"),
                        "is_unknown": bool(is_unknown),
                        "text_bbox_px": list(text_bbox),
                    },
                }
            )

    if panel_bbox is not None:
        scene_bbox = [round(float(value), 3) for value in panel_bbox]
    else:
        min_left = min(box[0] for box in scene_union_boxes)
        min_top = min(box[1] for box in scene_union_boxes)
        max_right = max(box[2] for box in scene_union_boxes)
        max_bottom = max(box[3] for box in scene_union_boxes)
        scene_bbox = [round(float(min_left), 3), round(float(min_top), 3), round(float(max_right), 3), round(float(max_bottom), 3)]

    return RenderedPuzzleGridScene(
        image=image,
        entities=entities,
        scene_bbox_px=list(scene_bbox),
        cell_bbox_map=cell_bbox_map,
    )


__all__ = [
    "PuzzleGridRenderParams",
    "RenderedPuzzleGridScene",
    "SUPPORTED_PUZZLE_GRID_SCENE_VARIANTS",
    "render_puzzle_grid_scene",
]
