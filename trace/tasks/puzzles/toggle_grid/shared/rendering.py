"""Rendering helpers for toggle-grid puzzle scenes."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw

from trace.tasks.shared.drawing import draw_centered_text, draw_rounded_rect
from trace.tasks.shared.text_rendering import load_font

from .state import (
    BBox,
    Cell,
    GridState,
    RenderedToggleScene,
    SwitchOption,
    ToggleDataset,
    ToggleRenderParams,
)


def _bbox(values: Sequence[float]) -> BBox:
    """Normalize one bbox tuple to float coordinates."""

    return tuple(float(value) for value in values[:4])  # type: ignore[return-value]


def _state_colors(style: Any) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """Resolve off/on tile colors from the shared puzzle style."""

    colors = tuple(tuple(int(value) for value in color) for color in style.state_colors)
    on = colors[0] if colors else (77, 137, 201)
    off = tuple(int(value) for value in style.option_fill_rgb)
    return off, on


def _draw_grid(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    title: str,
    state: GridState,
    style: Any,
    render_params: ToggleRenderParams,
    pressed_cells: Sequence[Cell] = (),
    switch_options: Sequence[SwitchOption] = (),
    cell_size: int | None = None,
) -> tuple[BBox, dict[str, BBox]]:
    """Draw one toggle grid panel and return cell bbox projections."""

    x0, y0, x1, y1 = [int(round(float(value))) for value in bbox]
    draw_rounded_rect(
        draw,
        (x0, y0, x1, y1),
        radius=18,
        fill=tuple(style.panel_fill_rgb),
        outline=tuple(style.panel_border_rgb),
        width=2,
    )
    if title:
        draw_centered_text(
            draw,
            text=str(title),
            center=(0.5 * (x0 + x1), y0 + 30),
            font=load_font(int(render_params.panel_title_font_size_px), bold=True),
            fill=tuple(style.text_rgb),
            stroke_fill=tuple(style.text_stroke_rgb),
            stroke_width=1,
        )
    rows = len(state)
    cols = len(state[0])
    title_space = 62 if title else 18
    max_cell = int(min((x1 - x0 - 58) / cols, (y1 - y0 - title_space - 18) / rows))
    cell = int(min(cell_size or max_cell, max_cell))
    grid_w = cell * cols
    grid_h = cell * rows
    gx0 = int(round(0.5 * (x0 + x1 - grid_w)))
    gy0 = int(round(y0 + title_space + max(0, (y1 - y0 - title_space - grid_h) * 0.5)))
    off_rgb, on_rgb = _state_colors(style)
    pressed_lookup = {
        tuple(cell_value): index + 1 for index, cell_value in enumerate(pressed_cells)
    }
    switch_lookup = {
        (int(opt.row), int(opt.col)): str(opt.option_label) for opt in switch_options
    }
    cell_bboxes: dict[str, BBox] = {}
    for row in range(rows):
        for col in range(cols):
            cx0 = gx0 + col * cell
            cy0 = gy0 + row * cell
            cx1 = cx0 + cell
            cy1 = cy0 + cell
            fill = on_rgb if int(state[row][col]) else off_rgb
            draw.rectangle(
                (cx0, cy0, cx1, cy1),
                fill=fill,
                outline=tuple(style.grid_rgb),
                width=2,
            )
            cell_bboxes[f"cell_{row}_{col}"] = _bbox((cx0, cy0, cx1, cy1))
            center = (0.5 * (cx0 + cx1), 0.5 * (cy0 + cy1))
            if (row, col) in pressed_lookup:
                radius = max(10, int(cell * 0.24))
                draw.ellipse(
                    (
                        center[0] - radius,
                        center[1] - radius,
                        center[0] + radius,
                        center[1] + radius,
                    ),
                    outline=tuple(style.mark_rgb),
                    width=4,
                )
                draw_centered_text(
                    draw,
                    text=str(pressed_lookup[(row, col)]),
                    center=center,
                    font=load_font(max(14, int(cell * 0.28)), bold=True),
                    fill=tuple(style.text_rgb),
                    stroke_fill=tuple(style.text_stroke_rgb),
                    stroke_width=2,
                )
            if (row, col) in switch_lookup:
                marker_size = max(24, int(cell * 0.42))
                bx0 = center[0] - marker_size * 0.5
                by0 = center[1] - marker_size * 0.5
                bx1 = center[0] + marker_size * 0.5
                by1 = center[1] + marker_size * 0.5
                draw_rounded_rect(
                    draw,
                    (bx0, by0, bx1, by1),
                    radius=7,
                    fill=tuple(style.option_marker_fill_rgb),
                    outline=tuple(style.panel_border_rgb),
                    width=1,
                )
                draw_centered_text(
                    draw,
                    text=switch_lookup[(row, col)],
                    center=center,
                    font=load_font(max(13, int(cell * 0.24)), bold=True),
                    fill=tuple(style.text_rgb),
                    stroke_fill=tuple(style.text_stroke_rgb),
                    stroke_width=1,
                )
    return _bbox((x0, y0, x1, y1)), dict(cell_bboxes)


def _draw_result_options(
    draw: ImageDraw.ImageDraw,
    *,
    panel_bbox: Sequence[float],
    dataset: ToggleDataset,
    style: Any,
    render_params: ToggleRenderParams,
) -> dict[str, BBox]:
    """Draw result-grid option panels and return option-panel bboxes."""

    x0, y0, x1, y1 = [int(round(float(value))) for value in panel_bbox]
    draw_rounded_rect(
        draw,
        (x0, y0, x1, y1),
        radius=18,
        fill=tuple(style.panel_fill_rgb),
        outline=tuple(style.panel_border_rgb),
        width=2,
    )
    draw_centered_text(
        draw,
        text="Result options",
        center=(0.5 * (x0 + x1), y0 + 26),
        font=load_font(20, bold=True),
        fill=tuple(style.text_rgb),
        stroke_fill=tuple(style.text_stroke_rgb),
        stroke_width=1,
    )
    option_count = len(dataset.result_options)
    gap = 16
    pad = 22
    card_w = int((x1 - x0 - 2 * pad - (option_count - 1) * gap) / option_count)
    card_h = y1 - y0 - 72
    top = y0 + 52
    bboxes: dict[str, BBox] = {}
    for index, option in enumerate(dataset.result_options):
        bx0 = x0 + pad + index * (card_w + gap)
        by0 = top
        bx1 = bx0 + card_w
        by1 = top + card_h
        draw_rounded_rect(
            draw,
            (bx0, by0, bx1, by1),
            radius=12,
            fill=tuple(style.option_fill_rgb),
            outline=tuple(style.panel_border_rgb),
            width=2,
        )
        draw_centered_text(
            draw,
            text=str(option.option_label),
            center=(bx0 + 20, by0 + 20),
            font=load_font(17, bold=True),
            fill=tuple(style.text_rgb),
            stroke_fill=tuple(style.text_stroke_rgb),
            stroke_width=1,
        )
        _draw_grid(
            draw,
            bbox=(bx0 + 10, by0 + 34, bx1 - 10, by1 - 10),
            title="",
            state=option.state,
            style=style,
            render_params=render_params,
            cell_size=int(render_params.mini_cell_size_px),
        )
        bboxes[f"option_{option.option_label}"] = _bbox((bx0, by0, bx1, by1))
    return dict(bboxes)


def render_toggle_result_scene(
    image: Image.Image,
    *,
    dataset: ToggleDataset,
    style: Any,
    render_params: ToggleRenderParams,
) -> RenderedToggleScene:
    """Render the numbered-press start grid and candidate result grids."""

    draw = ImageDraw.Draw(image)
    width = int(render_params.canvas_width)
    height = int(render_params.canvas_height)
    start_bbox, start_cell_bboxes = _draw_grid(
        draw,
        bbox=(54, 54, width - 54, 486),
        title="Start grid: press numbered switches",
        state=dataset.start_state,
        style=style,
        render_params=render_params,
        pressed_cells=dataset.pressed_cells,
        cell_size=int(render_params.main_cell_size_px),
    )
    option_bboxes = _draw_result_options(
        draw,
        panel_bbox=(54, 532, width - 54, height - 54),
        dataset=dataset,
        style=style,
        render_params=render_params,
    )
    return RenderedToggleScene(
        image=image,
        scene_bbox_px=_bbox((54, 54, width - 54, height - 54)),
        start_grid_bbox_px=start_bbox,
        target_grid_bbox_px=None,
        start_cell_bbox_map=dict(start_cell_bboxes),
        target_cell_bbox_map={},
        option_panel_bbox_map=dict(option_bboxes),
    )


def render_toggle_repair_scene(
    image: Image.Image,
    *,
    dataset: ToggleDataset,
    style: Any,
    render_params: ToggleRenderParams,
) -> RenderedToggleScene:
    """Render start/target grids for one-switch repair selection."""

    draw = ImageDraw.Draw(image)
    width = int(render_params.canvas_width)
    height = int(render_params.canvas_height)
    start_bbox, start_cell_bboxes = _draw_grid(
        draw,
        bbox=(54, 74, 540, height - 74),
        title="Start grid: candidate switches",
        state=dataset.start_state,
        style=style,
        render_params=render_params,
        switch_options=dataset.switch_options,
        cell_size=int(render_params.main_cell_size_px),
    )
    target_bbox, target_cell_bboxes = _draw_grid(
        draw,
        bbox=(580, 74, width - 54, height - 74),
        title="Target grid after one press",
        state=dataset.target_state,
        style=style,
        render_params=render_params,
        cell_size=int(render_params.main_cell_size_px),
    )
    return RenderedToggleScene(
        image=image,
        scene_bbox_px=_bbox((54, 74, width - 54, height - 74)),
        start_grid_bbox_px=start_bbox,
        target_grid_bbox_px=target_bbox,
        start_cell_bbox_map=dict(start_cell_bboxes),
        target_cell_bbox_map=dict(target_cell_bboxes),
        option_panel_bbox_map={},
    )
