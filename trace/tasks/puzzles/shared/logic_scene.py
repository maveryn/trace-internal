"""Shared rendering helpers for option-based logic-grid puzzle scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font
from .symbol_rendering import PUZZLE_OBJECT_COLOR_BY_TYPE, draw_puzzle_shape_icon


SUPPORTED_PUZZLE_LOGIC_SCENE_VARIANTS: Tuple[str, ...] = (
    "logic_strip",
    "logic_card",
    "logic_outline",
)


@dataclass(frozen=True)
class PuzzleLogicRenderParams:
    """Resolved render parameters for one option-based logic puzzle scene."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    cell_size_px: int
    cell_gap_px: int
    board_panel_padding_px: int
    board_to_options_gap_px: int
    option_panel_width_px: int
    option_panel_height_px: int
    option_gap_px: int
    option_symbol_box_size_px: int
    option_label_gap_px: int
    slot_corner_radius_px: int
    border_width_px: int
    panel_corner_radius_px: int
    value_font_size_px: int
    option_label_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    cell_fill_rgb: Tuple[int, int, int]
    unknown_cell_fill_rgb: Tuple[int, int, int]
    option_panel_fill_rgb: Tuple[int, int, int]
    option_symbol_fill_rgb: Tuple[int, int, int]
    border_color_rgb: Tuple[int, int, int]
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    accent_color_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class RenderedPuzzleLogicScene:
    """Rendered logic puzzle image plus traced board/option geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    cell_bbox_map: Dict[str, List[float]]
    option_panel_bbox_map: Dict[str, List[float]]


def _rounded_rect(
    draw: ImageDraw.ImageDraw,
    bbox: Tuple[float, float, float, float],
    *,
    radius: int,
    fill: Sequence[int],
    outline: Sequence[int],
    width: int,
) -> None:
    """Draw one rounded rectangle with deterministic styling."""

    draw.rounded_rectangle(
        bbox,
        radius=int(radius),
        fill=tuple(int(value) for value in fill),
        outline=tuple(int(value) for value in outline),
        width=int(width),
    )


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font,
    fill: Sequence[int],
    stroke_fill: Sequence[int],
    stroke_width: int = 1,
) -> List[float]:
    """Draw centered text and return the final text bbox."""

    bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
    left, top, right, bottom = [float(value) for value in bbox]
    cx, cy = float(center[0]), float(center[1])
    tx = float(cx - (0.5 * (left + right)))
    ty = float(cy - (0.5 * (top + bottom)))
    draw.text(
        (tx, ty),
        str(text),
        fill=tuple(int(v) for v in fill),
        font=font,
        stroke_width=max(0, int(stroke_width)),
        stroke_fill=tuple(int(v) for v in stroke_fill),
    )
    return [
        round(float(tx + left), 3),
        round(float(ty + top), 3),
        round(float(tx + right), 3),
        round(float(ty + bottom), 3),
    ]


def render_puzzle_logic_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    grid_rows: Sequence[Sequence[Mapping[str, Any]]],
    option_specs: Sequence[Mapping[str, Any]],
    render_params: PuzzleLogicRenderParams,
) -> RenderedPuzzleLogicScene:
    """Render one option-based logic grid with a missing slot and five option panels."""

    selected_variant = str(scene_variant)
    if selected_variant not in set(SUPPORTED_PUZZLE_LOGIC_SCENE_VARIANTS):
        raise ValueError(f"unsupported puzzle logic scene_variant: {scene_variant}")
    rows = [list(row) for row in grid_rows]
    options = [dict(option) for option in option_specs]
    if not rows or not rows[0]:
        raise ValueError("logic scenes require at least one board row")
    if len({len(row) for row in rows}) != 1:
        raise ValueError("logic scenes require a rectangular grid")
    if len(options) < 2:
        raise ValueError("logic scenes require at least two option panels")

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    value_font = load_font(int(render_params.value_font_size_px), bold=True)
    option_label_font = load_font(int(render_params.option_label_font_size_px), bold=True)

    board_rows = int(len(rows))
    board_cols = int(len(rows[0]))
    cell_size = float(render_params.cell_size_px)
    cell_gap = float(render_params.cell_gap_px)
    board_width = float((board_cols * cell_size) + max(0, board_cols - 1) * cell_gap)
    board_height = float((board_rows * cell_size) + max(0, board_rows - 1) * cell_gap)
    board_panel_pad = float(render_params.board_panel_padding_px)
    option_panel_width = float(render_params.option_panel_width_px)
    option_panel_height = float(render_params.option_panel_height_px)
    option_gap = float(render_params.option_gap_px)
    options_width = float((len(options) * option_panel_width) + max(0, len(options) - 1) * option_gap)
    board_to_options_gap = float(render_params.board_to_options_gap_px)
    options_height = float(option_panel_height)

    content_width = float(max(board_width, options_width))
    content_height = float(board_height + board_to_options_gap + options_height)
    usable_width = float(
        render_params.canvas_width - render_params.scene_margin_left_px - render_params.scene_margin_right_px
    )
    usable_height = float(
        render_params.canvas_height - render_params.scene_margin_top_px - render_params.scene_margin_bottom_px
    )
    content_left = float(
        render_params.scene_margin_left_px + max(0.0, 0.5 * (usable_width - content_width))
    )
    content_top = float(
        render_params.scene_margin_top_px + max(0.0, 0.5 * (usable_height - content_height))
    )

    board_left = float(content_left + 0.5 * (content_width - board_width))
    board_top = float(content_top)
    options_left = float(content_left + 0.5 * (content_width - options_width))
    options_top = float(board_top + board_height + board_to_options_gap)

    entities: List[Dict[str, Any]] = []
    cell_bbox_map: Dict[str, List[float]] = {}
    option_panel_bbox_map: Dict[str, List[float]] = {}

    board_panel_bbox = (
        float(board_left - board_panel_pad),
        float(board_top - board_panel_pad),
        float(board_left + board_width + board_panel_pad),
        float(board_top + board_height + board_panel_pad),
    )
    options_panel_bbox = (
        float(options_left - board_panel_pad),
        float(options_top - board_panel_pad),
        float(options_left + options_width + board_panel_pad),
        float(options_top + options_height + board_panel_pad),
    )
    if selected_variant in {"logic_card", "logic_outline"}:
        fill = render_params.panel_fill_rgb if selected_variant == "logic_card" else (248, 248, 248)
        _rounded_rect(
            draw,
            board_panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=fill,
            outline=render_params.border_color_rgb,
            width=int(render_params.border_width_px),
        )
        _rounded_rect(
            draw,
            options_panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=fill,
            outline=render_params.border_color_rgb,
            width=int(render_params.border_width_px),
        )
        entities.append(
            {
                "entity_id": "logic_board_panel",
                "entity_type": "puzzle_logic_panel",
                "bbox_px": [round(float(value), 3) for value in board_panel_bbox],
                "attrs": {"panel_role": "board", "scene_variant": selected_variant},
            }
        )
        entities.append(
            {
                "entity_id": "logic_options_panel",
                "entity_type": "puzzle_logic_panel",
                "bbox_px": [round(float(value), 3) for value in options_panel_bbox],
                "attrs": {"panel_role": "options", "scene_variant": selected_variant},
            }
        )

    for row_index, row in enumerate(rows):
        for col_index, cell in enumerate(row):
            cell_left = float(board_left + col_index * (cell_size + cell_gap))
            cell_top = float(board_top + row_index * (cell_size + cell_gap))
            cell_bbox = (
                float(cell_left),
                float(cell_top),
                float(cell_left + cell_size),
                float(cell_top + cell_size),
            )
            cell_id = str(cell["cell_id"])
            is_unknown = bool(cell.get("is_unknown", False))
            _rounded_rect(
                draw,
                cell_bbox,
                radius=int(render_params.slot_corner_radius_px),
                fill=render_params.unknown_cell_fill_rgb if is_unknown else render_params.cell_fill_rgb,
                outline=render_params.border_color_rgb,
                width=int(render_params.border_width_px),
            )
            if is_unknown:
                _draw_centered_text(
                    draw,
                    text="?",
                    center=(float(cell_left + 0.5 * cell_size), float(cell_top + 0.5 * cell_size)),
                    font=value_font,
                    fill=render_params.accent_color_rgb,
                    stroke_fill=render_params.text_stroke_rgb,
                    stroke_width=1,
                )
            else:
                object_type = str(cell["object_type"])
                fill_rgb = PUZZLE_OBJECT_COLOR_BY_TYPE.get(object_type, render_params.accent_color_rgb)
                draw_puzzle_shape_icon(
                    draw,
                    bbox=cell_bbox,
                    object_type=object_type,
                    fill_rgb=fill_rgb,
                    outline_rgb=render_params.border_color_rgb,
                    width=max(2, int(render_params.border_width_px)),
                )
            bbox_list = [round(float(value), 3) for value in cell_bbox]
            cell_bbox_map[cell_id] = list(bbox_list)
            entities.append(
                {
                    "entity_id": cell_id,
                    "entity_type": "puzzle_logic_cell",
                    "bbox_px": list(bbox_list),
                    "attrs": {
                        "row_index": int(row_index),
                        "col_index": int(col_index),
                        "is_unknown": bool(is_unknown),
                        "object_type": None if is_unknown else str(cell["object_type"]),
                    },
                }
            )

    symbol_box_size = float(render_params.option_symbol_box_size_px)
    option_label_gap = float(render_params.option_label_gap_px)
    for option_index, option in enumerate(options):
        panel_left = float(options_left + option_index * (option_panel_width + option_gap))
        panel_top = float(options_top)
        panel_bbox = (
            float(panel_left),
            float(panel_top),
            float(panel_left + option_panel_width),
            float(panel_top + option_panel_height),
        )
        option_panel_id = str(option["option_panel_id"])
        _rounded_rect(
            draw,
            panel_bbox,
            radius=int(render_params.slot_corner_radius_px),
            fill=render_params.option_panel_fill_rgb,
            outline=render_params.border_color_rgb,
            width=int(render_params.border_width_px),
        )

        label_center = (
            float(panel_left + 0.5 * option_panel_width),
            float(panel_top + 28.0),
        )
        label_bbox = _draw_centered_text(
            draw,
            text=str(option["option_label"]),
            center=label_center,
            font=option_label_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )
        symbol_box_left = float(panel_left + 0.5 * (option_panel_width - symbol_box_size))
        symbol_box_top = float(label_bbox[3] + option_label_gap)
        symbol_box_bbox = (
            float(symbol_box_left),
            float(symbol_box_top),
            float(symbol_box_left + symbol_box_size),
            float(symbol_box_top + symbol_box_size),
        )
        _rounded_rect(
            draw,
            symbol_box_bbox,
            radius=int(max(8, render_params.slot_corner_radius_px - 4)),
            fill=render_params.option_symbol_fill_rgb,
            outline=render_params.border_color_rgb,
            width=int(render_params.border_width_px),
        )
        option_type = str(option["object_type"])
        option_fill = PUZZLE_OBJECT_COLOR_BY_TYPE.get(option_type, render_params.accent_color_rgb)
        draw_puzzle_shape_icon(
            draw,
            bbox=symbol_box_bbox,
            object_type=option_type,
            fill_rgb=option_fill,
            outline_rgb=render_params.border_color_rgb,
            width=max(2, int(render_params.border_width_px)),
        )

        panel_bbox_list = [round(float(value), 3) for value in panel_bbox]
        option_panel_bbox_map[option_panel_id] = list(panel_bbox_list)
        entities.append(
            {
                "entity_id": option_panel_id,
                "entity_type": "puzzle_logic_option_panel",
                "bbox_px": list(panel_bbox_list),
                "attrs": {
                    "option_index": int(option_index),
                    "option_label": str(option["option_label"]),
                    "object_type": option_type,
                    "is_correct": bool(option.get("is_correct", False)),
                },
            }
        )
        entities.append(
            {
                "entity_id": f"{option_panel_id}_label",
                "entity_type": "puzzle_logic_option_label",
                "bbox_px": list(label_bbox),
                "attrs": {
                    "option_index": int(option_index),
                    "option_label": str(option["option_label"]),
                },
            }
        )
        entities.append(
            {
                "entity_id": f"{option_panel_id}_symbol_box",
                "entity_type": "puzzle_logic_option_symbol_box",
                "bbox_px": [round(float(value), 3) for value in symbol_box_bbox],
                "attrs": {
                    "option_index": int(option_index),
                    "option_label": str(option["option_label"]),
                    "object_type": option_type,
                },
            }
        )

    scene_bbox = [
        round(float(min(board_panel_bbox[0], options_panel_bbox[0], board_left)), 3),
        round(float(min(board_panel_bbox[1], options_panel_bbox[1], board_top)), 3),
        round(float(max(board_panel_bbox[2], options_panel_bbox[2], options_left + options_width)), 3),
        round(float(max(board_panel_bbox[3], options_panel_bbox[3], options_top + options_height)), 3),
    ]
    return RenderedPuzzleLogicScene(
        image=image,
        entities=entities,
        scene_bbox_px=scene_bbox,
        cell_bbox_map=cell_bbox_map,
        option_panel_bbox_map=option_panel_bbox_map,
    )


__all__ = [
    "PuzzleLogicRenderParams",
    "RenderedPuzzleLogicScene",
    "SUPPORTED_PUZZLE_LOGIC_SCENE_VARIANTS",
    "render_puzzle_logic_scene",
]
