"""Renderer for code-grid puzzle tasks."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw

from trace.tasks.puzzles.shared.drawing import draw_centered_text, draw_rounded_rect
from trace.tasks.puzzles.shared.word_grid import cell_key, coordinate_token
from trace.tasks.shared.bbox_projection import round_bbox
from trace.tasks.shared.text_rendering import load_font

from .state import CodeGridDataset, CodeGridRenderParams, RenderedCodeGrid


def render_code_grid_scene(
    image: Image.Image,
    *,
    dataset: CodeGridDataset,
    render_params: CodeGridRenderParams,
    rng,
) -> RenderedCodeGrid:
    """Render a row-letter and column-number code grid with traced cells."""

    draw = ImageDraw.Draw(image)
    rows = int(dataset.rows)
    cols = int(dataset.cols)
    cell = int(render_params.cell_size_px)
    header = int(render_params.header_size_px)
    padding = int(render_params.panel_padding_px)
    grid_w = int(header + cols * cell)
    grid_h = int(header + rows * cell)
    panel_w = int(grid_w + 2 * padding)
    panel_h = int(grid_h + 2 * padding)
    canvas_margin = 34
    max_panel_x0 = max(
        canvas_margin,
        int(render_params.canvas_width) - canvas_margin - panel_w,
    )
    max_panel_y0 = max(
        canvas_margin,
        int(render_params.canvas_height) - canvas_margin - panel_h,
    )
    panel_x0 = int(
        canvas_margin + rng.randrange(max(1, max_panel_x0 - canvas_margin + 1))
    )
    panel_y0 = int(
        canvas_margin + rng.randrange(max(1, max_panel_y0 - canvas_margin + 1))
    )
    panel_x1 = int(panel_x0 + panel_w)
    panel_y1 = int(panel_y0 + panel_h)
    grid_x0 = int(panel_x0 + padding)
    grid_y0 = int(panel_y0 + padding)
    layout_jitter = {
        "enabled": True,
        "panel_x0_px": int(panel_x0),
        "panel_y0_px": int(panel_y0),
        "grid_x0_px": int(grid_x0),
        "grid_y0_px": int(grid_y0),
        "available_x0_min_px": int(canvas_margin),
        "available_x0_max_px": int(max_panel_x0),
        "available_y0_min_px": int(canvas_margin),
        "available_y0_max_px": int(max_panel_y0),
    }

    draw_rounded_rect(
        draw,
        (panel_x0, panel_y0, panel_x1, panel_y1),
        radius=int(render_params.panel_corner_radius_px),
        fill=render_params.panel_fill_rgb,
        outline=render_params.grid_line_rgb,
        width=max(1, int(render_params.grid_line_width_px)),
    )
    if str(dataset.scene_variant) == "code_grid_notebook":
        for y_pos in range(panel_y0 + 14, panel_y1 - 8, max(16, cell // 2)):
            draw.line(
                (panel_x0 + 8, y_pos, panel_x1 - 8, y_pos),
                fill=render_params.grid_line_rgb,
                width=1,
            )

    letter_font = load_font(int(render_params.letter_font_size_px), bold=True)
    index_font = load_font(int(render_params.index_font_size_px), bold=True)
    item_bbox_map: dict[str, list[float]] = {}
    cell_bbox_map: dict[str, list[float]] = {}
    entities: list[dict[str, Any]] = [
        {
            "entity_id": "code_grid_panel",
            "entity_type": "puzzle_code_grid_panel",
            "bbox_px": round_bbox((panel_x0, panel_y0, panel_x1, panel_y1)),
            "scene_variant": str(dataset.scene_variant),
        }
    ]

    for row in range(rows + 1):
        for col in range(cols + 1):
            bbox, fill = _cell_bbox_and_fill(
                row=row,
                col=col,
                grid_x0=grid_x0,
                grid_y0=grid_y0,
                header=header,
                cell=cell,
                render_params=render_params,
            )
            draw.rectangle(
                bbox,
                fill=fill,
                outline=render_params.grid_line_rgb,
                width=max(1, int(render_params.grid_line_width_px)),
            )
            if row == 0 and col > 0:
                draw_centered_text(
                    draw,
                    text=str(col),
                    center=((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2),
                    font=index_font,
                    fill=render_params.text_rgb,
                    stroke_fill=render_params.text_stroke_rgb,
                    stroke_width=1,
                )
            elif col == 0 and row > 0:
                draw_centered_text(
                    draw,
                    text=chr(ord("A") + row - 1),
                    center=((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2),
                    font=index_font,
                    fill=render_params.text_rgb,
                    stroke_fill=render_params.text_stroke_rgb,
                    stroke_width=1,
                )
            elif row > 0 and col > 0:
                letter = str(dataset.grid[row - 1][col - 1])
                entity_id = cell_key((row - 1, col - 1))
                rounded = round_bbox(bbox)
                cell_bbox_map[entity_id] = rounded
                item_bbox_map[entity_id] = rounded
                draw_centered_text(
                    draw,
                    text=letter,
                    center=((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2),
                    font=letter_font,
                    fill=render_params.text_rgb,
                    stroke_fill=render_params.text_stroke_rgb,
                    stroke_width=1,
                )
                entities.append(
                    {
                        "entity_id": entity_id,
                        "entity_type": "puzzle_code_grid_cell",
                        "bbox_px": rounded,
                        "row": int(row - 1),
                        "col": int(col - 1),
                        "coordinate": coordinate_token((row - 1, col - 1)),
                        "letter": letter,
                    }
                )

    return RenderedCodeGrid(
        image=image,
        entities=tuple(entities),
        scene_bbox_px=round_bbox((panel_x0, panel_y0, panel_x1, panel_y1)),
        item_bbox_map=dict(item_bbox_map),
        cell_bbox_map=dict(cell_bbox_map),
        layout_jitter=dict(layout_jitter),
    )


def _cell_bbox_and_fill(
    *,
    row: int,
    col: int,
    grid_x0: int,
    grid_y0: int,
    header: int,
    cell: int,
    render_params: CodeGridRenderParams,
) -> tuple[tuple[int, int, int, int], tuple[int, int, int]]:
    """Return one grid/header bbox and fill color."""

    if row == 0 and col == 0:
        bbox = (grid_x0, grid_y0, grid_x0 + header, grid_y0 + header)
        fill = render_params.header_fill_rgb
    elif row == 0:
        bbox = (
            grid_x0 + header + ((col - 1) * cell),
            grid_y0,
            grid_x0 + header + (col * cell),
            grid_y0 + header,
        )
        fill = render_params.header_fill_rgb
    elif col == 0:
        bbox = (
            grid_x0,
            grid_y0 + header + ((row - 1) * cell),
            grid_x0 + header,
            grid_y0 + header + (row * cell),
        )
        fill = render_params.header_fill_rgb
    else:
        bbox = (
            grid_x0 + header + ((col - 1) * cell),
            grid_y0 + header + ((row - 1) * cell),
            grid_x0 + header + (col * cell),
            grid_y0 + header + (row * cell),
        )
        fill = render_params.grid_fill_rgb
    return bbox, fill


__all__ = ["render_code_grid_scene"]
