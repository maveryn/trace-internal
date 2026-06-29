"""Rendering helpers for option-based logic-grid puzzle scenes."""

from __future__ import annotations

from typing import Dict, List, Mapping, Sequence

from PIL import Image, ImageDraw

from trace.tasks.puzzles.shared.drawing import draw_centered_text, draw_rounded_rect
from trace.tasks.puzzles.shared.option_panels import render_puzzle_option_panel
from trace.tasks.puzzles.shared.symbol_rendering import (
    PUZZLE_OBJECT_COLOR_BY_TYPE,
    draw_puzzle_shape_icon,
)
from trace.tasks.shared.text_rendering import load_font

from .state import LogicGridRenderParams, RenderedLogicGridScene, SCENE_VARIANTS


def render_logic_grid_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    grid_rows: Sequence[Sequence[Mapping[str, object]]],
    option_specs: Sequence[Mapping[str, object]],
    render_params: LogicGridRenderParams,
) -> RenderedLogicGridScene:
    """Render one logic grid with a missing slot and labeled option panels."""

    selected_variant = str(scene_variant)
    if selected_variant not in set(SCENE_VARIANTS):
        raise ValueError(f"unsupported logic-grid scene variant: {scene_variant}")
    rows = [list(row) for row in grid_rows]
    options = [dict(option) for option in option_specs]
    if not rows or not rows[0]:
        raise ValueError("logic-grid scenes require at least one board row")
    if len({len(row) for row in rows}) != 1:
        raise ValueError("logic-grid scenes require a rectangular grid")
    if len(options) < 2:
        raise ValueError("logic-grid scenes require at least two option panels")

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

    board_left = float(content_left + 0.5 * (content_width - board_width))
    board_top = float(content_top)
    options_left = float(content_left + 0.5 * (content_width - options_width))
    options_top = float(board_top + board_height + board_to_options_gap)

    entities: List[Dict[str, object]] = []
    cell_bbox_map: Dict[str, List[float]] = {}
    option_panel_bbox_map: Dict[str, List[float]] = {}

    board_panel_bbox = (
        float(board_left - board_panel_pad),
        float(board_top - board_panel_pad),
        float(board_left + board_width + board_panel_pad),
        float(board_top + board_height + board_panel_pad),
    )
    board_bbox = (
        float(board_left),
        float(board_top),
        float(board_left + board_width),
        float(board_top + board_height),
    )
    options_panel_bbox = (
        float(options_left - board_panel_pad),
        float(options_top - board_panel_pad),
        float(options_left + options_width + board_panel_pad),
        float(options_top + options_height + board_panel_pad),
    )
    if selected_variant in {"logic_card", "logic_outline"}:
        fill = (
            render_params.panel_fill_rgb
            if selected_variant == "logic_card"
            else render_params.option_panel_fill_rgb
        )
        draw_rounded_rect(
            draw,
            board_panel_bbox,
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

    _draw_board_cells(
        draw,
        rows=rows,
        board_left=board_left,
        board_top=board_top,
        cell_size=cell_size,
        cell_gap=cell_gap,
        render_params=render_params,
        value_font=value_font,
        entities=entities,
        cell_bbox_map=cell_bbox_map,
    )
    _draw_option_panels(
        draw,
        options=options,
        options_left=options_left,
        options_top=options_top,
        option_panel_width=option_panel_width,
        option_panel_height=option_panel_height,
        option_gap=option_gap,
        render_params=render_params,
        option_label_font=option_label_font,
        entities=entities,
        option_panel_bbox_map=option_panel_bbox_map,
    )

    scene_bbox = [
        round(float(min(board_panel_bbox[0], options_panel_bbox[0], board_left)), 3),
        round(float(min(board_panel_bbox[1], options_panel_bbox[1], board_top)), 3),
        round(float(max(board_panel_bbox[2], options_panel_bbox[2], options_left + options_width)), 3),
        round(float(max(board_panel_bbox[3], options_panel_bbox[3], options_top + options_height)), 3),
    ]
    return RenderedLogicGridScene(
        image=image,
        entities=entities,
        scene_bbox_px=scene_bbox,
        board_bbox_px=[round(float(value), 3) for value in board_bbox],
        cell_bbox_map=cell_bbox_map,
        option_panel_bbox_map=option_panel_bbox_map,
    )


def _draw_board_cells(
    draw: ImageDraw.ImageDraw,
    *,
    rows: Sequence[Sequence[Mapping[str, object]]],
    board_left: float,
    board_top: float,
    cell_size: float,
    cell_gap: float,
    render_params: LogicGridRenderParams,
    value_font,
    entities: List[Dict[str, object]],
    cell_bbox_map: Dict[str, List[float]],
) -> None:
    """Draw grid cells and record cell bboxes."""

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
            draw_rounded_rect(
                draw,
                cell_bbox,
                radius=int(render_params.slot_corner_radius_px),
                fill=render_params.unknown_cell_fill_rgb if is_unknown else render_params.cell_fill_rgb,
                outline=render_params.border_color_rgb,
                width=int(render_params.border_width_px),
            )
            if is_unknown:
                draw_centered_text(
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


def _draw_option_panels(
    draw: ImageDraw.ImageDraw,
    *,
    options: Sequence[Mapping[str, object]],
    options_left: float,
    options_top: float,
    option_panel_width: float,
    option_panel_height: float,
    option_gap: float,
    render_params: LogicGridRenderParams,
    option_label_font,
    entities: List[Dict[str, object]],
    option_panel_bbox_map: Dict[str, List[float]],
) -> None:
    """Draw labeled option panels and record panel bboxes."""

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
        option_panel = render_puzzle_option_panel(
            draw,
            panel_bbox=panel_bbox,
            option_label=str(option["option_label"]),
            label_font=option_label_font,
            label_center_y_px=float(panel_top + 28.0),
            content_box_size_px=float(symbol_box_size),
            content_gap_px=float(option_label_gap),
            panel_fill_rgb=render_params.option_panel_fill_rgb,
            content_fill_rgb=render_params.option_symbol_fill_rgb,
            border_color_rgb=render_params.border_color_rgb,
            text_color_rgb=render_params.text_color_rgb,
            text_stroke_rgb=render_params.text_stroke_rgb,
            panel_corner_radius_px=int(render_params.slot_corner_radius_px),
            content_corner_radius_px=int(max(8, render_params.slot_corner_radius_px - 4)),
            border_width_px=int(render_params.border_width_px),
        )
        option_type = str(option["object_type"])
        option_fill = PUZZLE_OBJECT_COLOR_BY_TYPE.get(option_type, render_params.accent_color_rgb)
        draw_puzzle_shape_icon(
            draw,
            bbox=tuple(float(value) for value in option_panel.content_bbox),
            object_type=option_type,
            fill_rgb=option_fill,
            outline_rgb=render_params.border_color_rgb,
            width=max(2, int(render_params.border_width_px)),
        )

        panel_bbox_list = list(option_panel.panel_bbox)
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
                "bbox_px": list(option_panel.label_bbox),
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
                "bbox_px": list(option_panel.content_bbox),
                "attrs": {
                    "option_index": int(option_index),
                    "option_label": str(option["option_label"]),
                    "object_type": option_type,
                },
            }
        )
