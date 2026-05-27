"""Shared dots-and-boxes board renderer for games-domain tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font
from .dots_boxes_common import DotsAndBoxesBoardState, DotsAndBoxesBoxInstance, DotsAndBoxesEdgeInstance
from .layout import apply_games_layout_jitter_to_bbox
from .style import DotsAndBoxesTheme, build_games_dots_and_boxes_theme


@dataclass(frozen=True)
class DotsAndBoxesRenderParams:
    """Resolved render controls for one dots-and-boxes board scene."""

    canvas_width: int
    canvas_height: int
    board_width_px: int
    board_height_px: int
    board_corner_radius_px: int
    panel_margin_px: int
    title_font_size_px: int
    title_band_height_px: int
    board_padding_px: int
    dot_radius_px: int
    dash_length_px: int
    dash_gap_px: int
    layout_jitter_meta: Dict[str, Any] | None = None


@dataclass(frozen=True)
class RenderedDotsAndBoxesBoxSpec:
    """One rendered dots-and-boxes box region."""

    box_id: str
    row_index: int
    column_index: int
    bbox_px: Tuple[float, float, float, float]


@dataclass(frozen=True)
class RenderedDotsAndBoxesScene:
    """Rendered dots-and-boxes scene plus trace-friendly metadata."""

    image: Image.Image
    box_specs: Tuple[RenderedDotsAndBoxesBoxSpec, ...]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


def _draw_shadow(
    image: Image.Image,
    *,
    bbox_px: Tuple[float, float, float, float],
    radius_px: int,
    theme: DotsAndBoxesTheme,
) -> None:
    """Draw one soft panel shadow for the dots-and-boxes board."""

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    left, top, right, bottom = bbox_px
    dx, dy = theme.shadow_offset_px
    draw.rounded_rectangle(
        [left + dx, top + dy, right + dx, bottom + dy],
        radius=int(radius_px),
        fill=(
            int(theme.shadow_rgb[0]),
            int(theme.shadow_rgb[1]),
            int(theme.shadow_rgb[2]),
            int(theme.shadow_alpha),
        ),
    )
    image.alpha_composite(overlay)


def _draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    *,
    start_xy: Tuple[float, float],
    end_xy: Tuple[float, float],
    dash_length_px: int,
    dash_gap_px: int,
    width_px: int,
    fill_rgb: Tuple[int, int, int],
) -> None:
    """Draw one dashed highlight line between two points."""

    x1, y1 = start_xy
    x2, y2 = end_xy
    total_length = math.hypot(float(x2 - x1), float(y2 - y1))
    if total_length <= 0.0:
        return
    dx = float(x2 - x1) / total_length
    dy = float(y2 - y1) / total_length
    distance = 0.0
    while distance < total_length:
        segment_end = min(total_length, distance + float(dash_length_px))
        sx = float(x1 + (dx * distance))
        sy = float(y1 + (dy * distance))
        ex = float(x1 + (dx * segment_end))
        ey = float(y1 + (dy * segment_end))
        draw.line(
            [(sx, sy), (ex, ey)],
            fill=tuple(int(value) for value in fill_rgb),
            width=int(width_px),
        )
        distance = segment_end + float(dash_gap_px)


def _draw_board_treatment(
    image: Image.Image,
    *,
    board_bbox: Tuple[float, float, float, float],
    radius_px: int,
    theme: DotsAndBoxesTheme,
) -> None:
    """Draw optional inner fill and surface pattern for one board style."""

    draw = ImageDraw.Draw(image)
    left, top, right, bottom = board_bbox
    if theme.board_inner_fill_rgb is not None:
        inset = 10.0
        draw.rounded_rectangle(
            [left + inset, top + inset, right - inset, bottom - inset],
            radius=max(6, int(radius_px) - 8),
            fill=tuple(int(value) for value in theme.board_inner_fill_rgb),
        )
    if theme.board_pattern_rgb is None or int(theme.board_pattern_alpha) <= 0:
        return

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    color = (
        int(theme.board_pattern_rgb[0]),
        int(theme.board_pattern_rgb[1]),
        int(theme.board_pattern_rgb[2]),
        int(theme.board_pattern_alpha),
    )
    pattern = str(theme.board_rendering)
    if pattern == "notebook":
        spacing = 38.0
        y = float(top + 78.0)
        while y < float(bottom - 18.0):
            overlay_draw.line([(left + 18.0, y), (right - 18.0, y)], fill=color, width=1)
            y += spacing
        x = float(left + 86.0)
        overlay_draw.line([(x, top + 18.0), (x, bottom - 18.0)], fill=color, width=2)
    elif pattern == "wood":
        spacing = 58.0
        x = float(left + 24.0)
        while x < float(right - 18.0):
            overlay_draw.line([(x, top + 18.0), (x + 24.0, bottom - 18.0)], fill=color, width=3)
            x += spacing
    else:
        overlay_draw.rounded_rectangle(
            [left + 12.0, top + 12.0, right - 12.0, bottom - 12.0],
            radius=max(6, int(radius_px) - 10),
            outline=color,
            width=2,
        )
    image.alpha_composite(overlay)


def _edge_bbox(
    edge: DotsAndBoxesEdgeInstance,
    *,
    dot_xy: Mapping[Tuple[int, int], Tuple[float, float]],
    pad_px: float,
) -> Tuple[float, float, float, float]:
    """Return one padded bbox for a rendered edge."""

    start_xy = dot_xy[(int(edge.dot_start[0]), int(edge.dot_start[1]))]
    end_xy = dot_xy[(int(edge.dot_end[0]), int(edge.dot_end[1]))]
    x1, y1 = start_xy
    x2, y2 = end_xy
    return (
        round(min(x1, x2) - pad_px, 3),
        round(min(y1, y2) - pad_px, 3),
        round(max(x1, x2) + pad_px, 3),
        round(max(y1, y2) + pad_px, 3),
    )


def render_dots_and_boxes_scene(
    *,
    board_state: DotsAndBoxesBoardState,
    background: Image.Image,
    scene_variant: str,
    style_variant: str,
    params: DotsAndBoxesRenderParams,
) -> RenderedDotsAndBoxesScene:
    """Render one dots-and-boxes board with a highlighted starting edge."""

    if str(scene_variant) != "single_board":
        raise ValueError(f"unsupported dots-and-boxes scene_variant: {scene_variant}")

    image = background.convert("RGBA")
    theme = build_games_dots_and_boxes_theme(style_variant=str(style_variant))
    draw = ImageDraw.Draw(image)
    title_font = load_font(int(params.title_font_size_px), bold=True)

    board_left = float((int(params.canvas_width) - int(params.board_width_px)) / 2)
    board_top = float((int(params.canvas_height) - int(params.board_height_px)) / 2)
    board_right = float(board_left + int(params.board_width_px))
    board_bottom = float(board_top + int(params.board_height_px))
    board_bbox, _dx, _dy, layout_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=(board_left, board_top, board_right, board_bottom),
        canvas_width=int(params.canvas_width),
        canvas_height=int(params.canvas_height),
        jitter=params.layout_jitter_meta,
    )
    board_left, board_top, board_right, board_bottom = [float(value) for value in board_bbox]

    _draw_shadow(
        image,
        bbox_px=board_bbox,
        radius_px=int(params.board_corner_radius_px),
        theme=theme,
    )
    draw.rounded_rectangle(
        board_bbox,
        radius=int(params.board_corner_radius_px),
        fill=tuple(int(value) for value in theme.board_fill_rgb),
        outline=tuple(int(value) for value in theme.board_border_rgb),
        width=int(theme.board_border_width_px),
    )
    _draw_board_treatment(
        image,
        board_bbox=board_bbox,
        radius_px=int(params.board_corner_radius_px),
        theme=theme,
    )

    title_text = "Dots and Boxes"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font, stroke_width=1)
    title_width = float(title_bbox[2] - title_bbox[0])
    title_height = float(title_bbox[3] - title_bbox[1])
    title_x = float(board_left + ((int(params.board_width_px) - title_width) / 2.0))
    title_y = float(board_top + ((int(params.title_band_height_px) - title_height) / 2.0))
    draw.text(
        (title_x, title_y),
        title_text,
        font=title_font,
        fill=tuple(int(value) for value in theme.title_rgb),
        stroke_width=1,
        stroke_fill=(255, 255, 255),
    )

    inner_left = float(board_left + int(params.board_padding_px))
    inner_top = float(board_top + int(params.title_band_height_px) + int(params.board_padding_px))
    inner_right = float(board_right - int(params.board_padding_px))
    inner_bottom = float(board_bottom - int(params.board_padding_px))

    cell_size = min(
        float((inner_right - inner_left) / float(board_state.box_cols)),
        float((inner_bottom - inner_top) / float(board_state.box_rows)),
    )
    grid_width = float(cell_size * float(board_state.box_cols))
    grid_height = float(cell_size * float(board_state.box_rows))
    grid_left = float(inner_left + ((inner_right - inner_left - grid_width) / 2.0))
    grid_top = float(inner_top + ((inner_bottom - inner_top - grid_height) / 2.0))

    dot_xy: Dict[Tuple[int, int], Tuple[float, float]] = {}
    for dot_row in range(int(board_state.box_rows) + 1):
        for dot_col in range(int(board_state.box_cols) + 1):
            dot_xy[(dot_row, dot_col)] = (
                round(float(grid_left + (dot_col * cell_size)), 3),
                round(float(grid_top + (dot_row * cell_size)), 3),
            )

    box_bboxes_px: Dict[str, List[float]] = {}
    box_specs: List[RenderedDotsAndBoxesBoxSpec] = []
    box_by_id = {str(box.box_id): box for box in board_state.boxes}
    for box in board_state.boxes:
        left = float(dot_xy[(int(box.row_index), int(box.column_index))][0] + (0.18 * cell_size))
        top = float(dot_xy[(int(box.row_index), int(box.column_index))][1] + (0.18 * cell_size))
        right = float(dot_xy[(int(box.row_index), int(box.column_index) + 1)][0] - (0.18 * cell_size))
        bottom = float(dot_xy[(int(box.row_index) + 1, int(box.column_index))][1] - (0.18 * cell_size))
        bbox = (
            round(left, 3),
            round(top, 3),
            round(right, 3),
            round(bottom, 3),
        )
        box_bboxes_px[str(box.box_id)] = [float(value) for value in bbox]
        box_specs.append(
            RenderedDotsAndBoxesBoxSpec(
                box_id=str(box.box_id),
                row_index=int(box.row_index),
                column_index=int(box.column_index),
                bbox_px=bbox,
            )
        )

    edge_bboxes_px: Dict[str, List[float]] = {}
    for edge in board_state.edges:
        edge_bboxes_px[str(edge.edge_id)] = list(
            _edge_bbox(
                edge,
                dot_xy=dot_xy,
                pad_px=float(max(theme.edge_width_px, theme.highlight_width_px) + 8),
            )
        )
        if not bool(edge.is_drawn) and not bool(edge.is_highlighted):
            continue
        start_xy = dot_xy[(int(edge.dot_start[0]), int(edge.dot_start[1]))]
        end_xy = dot_xy[(int(edge.dot_end[0]), int(edge.dot_end[1]))]
        if bool(edge.is_drawn):
            draw.line(
                [start_xy, end_xy],
                fill=tuple(int(value) for value in theme.edge_rgb),
                width=int(theme.edge_width_px),
            )
        if bool(edge.is_highlighted):
            _draw_dashed_line(
                draw,
                start_xy=start_xy,
                end_xy=end_xy,
                dash_length_px=int(params.dash_length_px),
                dash_gap_px=int(params.dash_gap_px),
                width_px=int(theme.highlight_width_px),
                fill_rgb=tuple(int(value) for value in theme.highlight_rgb),
            )

    for dot_row in range(int(board_state.box_rows) + 1):
        for dot_col in range(int(board_state.box_cols) + 1):
            cx, cy = dot_xy[(dot_row, dot_col)]
            radius = float(params.dot_radius_px)
            dot_bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
            if str(theme.dot_rendering) == "outlined" and theme.dot_outline_rgb is not None:
                draw.ellipse(
                    [dot_bbox[0] - 1.5, dot_bbox[1] - 1.5, dot_bbox[2] + 1.5, dot_bbox[3] + 1.5],
                    fill=tuple(int(value) for value in theme.dot_outline_rgb),
                )
            draw.ellipse(
                dot_bbox,
                fill=tuple(int(value) for value in theme.dot_rgb),
            )

    scene_entities: List[Dict[str, Any]] = []
    for box_spec in box_specs:
        box = box_by_id[str(box_spec.box_id)]
        scene_entities.append(
            {
                "entity_id": str(box_spec.box_id),
                "kind": "dots_and_boxes_box",
                "bbox": [float(value) for value in box_spec.bbox_px],
                "row_index": int(box.row_index),
                "column_index": int(box.column_index),
            }
        )
    highlighted_edge_ids = tuple(
        str(edge_id)
        for edge_id in getattr(board_state, "highlighted_edge_ids", ())
        if str(edge_id)
    )
    if not highlighted_edge_ids and str(board_state.highlighted_edge_id):
        highlighted_edge_ids = (str(board_state.highlighted_edge_id),)
    for edge_id in highlighted_edge_ids:
        scene_entities.append(
            {
                "entity_id": str(edge_id),
                "kind": "dots_and_boxes_highlighted_edge",
                "bbox": list(edge_bboxes_px[str(edge_id)]),
            }
        )

    return RenderedDotsAndBoxesScene(
        image=image.convert("RGB"),
        box_specs=tuple(box_specs),
        scene_entities=tuple(scene_entities),
        render_map={
            "board_bbox_px": [float(value) for value in board_bbox],
            "box_bboxes_px": box_bboxes_px,
            "edge_bboxes_px": edge_bboxes_px,
            "highlighted_edge_id": str(board_state.highlighted_edge_id),
            "highlighted_edge_ids": [str(edge_id) for edge_id in highlighted_edge_ids],
            "layout_jitter": dict(layout_jitter),
        },
    )


__all__ = [
    "DotsAndBoxesRenderParams",
    "RenderedDotsAndBoxesBoxSpec",
    "RenderedDotsAndBoxesScene",
    "render_dots_and_boxes_scene",
]
