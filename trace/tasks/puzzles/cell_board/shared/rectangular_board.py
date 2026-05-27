"""Shared rectangular-tile board layout and rendering helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from PIL import Image, ImageDraw

from trace.tasks.shared.bbox_projection import BBox
from trace.tasks.shared.text_rendering import draw_text_centered, load_font
from trace.tasks.puzzles.shared.scene_style import (
    PuzzleSceneStyle,
    draw_puzzle_chrome_by_mode,
    draw_puzzle_grid_cell,
    make_puzzle_scene_background,
    resolve_panel_chrome_mode,
    resolve_puzzle_scene_style,
)
from .grid_graph import cell_id


Coord = Tuple[int, int]
Color = Tuple[int, int, int]


@dataclass(frozen=True)
class RectangularTileSpec:
    """Resolved per-board tile geometry."""

    short_side_px: int
    aspect_ratio: float
    orientation: str
    tile_width_px: int
    tile_height_px: int


@dataclass(frozen=True)
class RectangularBoardLayout:
    """Resolved pixel layout for one rectangular tile board."""

    rows: int
    cols: int
    canvas_width_px: int
    canvas_height_px: int
    tile_width_px: int
    tile_height_px: int
    board_origin_x_px: int
    board_origin_y_px: int
    board_width_px: int
    board_height_px: int
    left_label_gutter_px: int
    top_label_gutter_px: int
    outer_padding_x_px: int
    outer_padding_y_px: int
    placement_offset_x_px: int
    placement_offset_y_px: int
    tile_outline_width_px: int
    coordinate_labels: bool
    label_font_size_px: int
    label_stroke_width_px: int


def sample_rectangular_tile_spec(
    rng,
    *,
    short_side_px_min: int,
    short_side_px_max: int,
    aspect_ratio_min: float,
    aspect_ratio_max: float,
) -> RectangularTileSpec:
    """Sample one board-uniform rectangular tile geometry spec."""
    short_side_px = int(rng.randint(int(short_side_px_min), int(short_side_px_max)))
    aspect_ratio = float(rng.uniform(float(aspect_ratio_min), float(aspect_ratio_max)))
    orientation = "wide" if bool(rng.randint(0, 1)) else "tall"
    if str(orientation) == "wide":
        tile_width_px = int(round(float(short_side_px) * float(aspect_ratio)))
        tile_height_px = int(short_side_px)
    else:
        tile_width_px = int(short_side_px)
        tile_height_px = int(round(float(short_side_px) * float(aspect_ratio)))
    return RectangularTileSpec(
        short_side_px=int(short_side_px),
        aspect_ratio=float(aspect_ratio),
        orientation=str(orientation),
        tile_width_px=max(1, int(tile_width_px)),
        tile_height_px=max(1, int(tile_height_px)),
    )


def resolve_rectangular_board_layout(
    rng,
    *,
    rows: int,
    cols: int,
    tile_width_px: int,
    tile_height_px: int,
    outer_padding_fraction_min: float,
    outer_padding_fraction_max: float,
    placement_jitter_fraction_min: float,
    placement_jitter_fraction_max: float,
    coordinate_labels: bool = False,
) -> RectangularBoardLayout:
    """Resolve one dynamic canvas layout for a rectangular board."""
    board_width_px = int(cols) * int(tile_width_px)
    board_height_px = int(rows) * int(tile_height_px)
    short_side_px = max(1, min(int(tile_width_px), int(tile_height_px)))
    label_font_size_px = max(12, int(round(float(short_side_px) * 0.38)))
    label_stroke_width_px = max(1, int(round(float(label_font_size_px) * 0.10)))
    tile_outline_width_px = max(1, int(round(float(short_side_px) * 0.06)))
    if bool(coordinate_labels):
        left_label_gutter_px = max(int(label_font_size_px) + 12, int(round(float(tile_width_px) * 0.50)))
        top_label_gutter_px = max(int(label_font_size_px) + 12, int(round(float(tile_height_px) * 0.50)))
    else:
        left_label_gutter_px = 0
        top_label_gutter_px = 0

    padding_fraction = float(rng.uniform(float(outer_padding_fraction_min), float(outer_padding_fraction_max)))
    jitter_fraction = float(rng.uniform(float(placement_jitter_fraction_min), float(placement_jitter_fraction_max)))
    outer_padding_x_px = max(16, int(round(float(board_width_px) * float(padding_fraction))))
    outer_padding_y_px = max(16, int(round(float(board_height_px) * float(padding_fraction))))
    jitter_slack_x_px = max(0, int(round(float(board_width_px) * float(jitter_fraction))))
    jitter_slack_y_px = max(0, int(round(float(board_height_px) * float(jitter_fraction))))
    placement_offset_x_px = int(rng.randint(0, int(jitter_slack_x_px))) if int(jitter_slack_x_px) > 0 else 0
    placement_offset_y_px = int(rng.randint(0, int(jitter_slack_y_px))) if int(jitter_slack_y_px) > 0 else 0

    board_origin_x_px = int(left_label_gutter_px) + int(outer_padding_x_px) + int(placement_offset_x_px)
    board_origin_y_px = int(top_label_gutter_px) + int(outer_padding_y_px) + int(placement_offset_y_px)
    canvas_width_px = (
        int(left_label_gutter_px)
        + int(board_width_px)
        + (2 * int(outer_padding_x_px))
        + int(jitter_slack_x_px)
    )
    canvas_height_px = (
        int(top_label_gutter_px)
        + int(board_height_px)
        + (2 * int(outer_padding_y_px))
        + int(jitter_slack_y_px)
    )
    return RectangularBoardLayout(
        rows=int(rows),
        cols=int(cols),
        canvas_width_px=int(canvas_width_px),
        canvas_height_px=int(canvas_height_px),
        tile_width_px=int(tile_width_px),
        tile_height_px=int(tile_height_px),
        board_origin_x_px=int(board_origin_x_px),
        board_origin_y_px=int(board_origin_y_px),
        board_width_px=int(board_width_px),
        board_height_px=int(board_height_px),
        left_label_gutter_px=int(left_label_gutter_px),
        top_label_gutter_px=int(top_label_gutter_px),
        outer_padding_x_px=int(outer_padding_x_px),
        outer_padding_y_px=int(outer_padding_y_px),
        placement_offset_x_px=int(placement_offset_x_px),
        placement_offset_y_px=int(placement_offset_y_px),
        tile_outline_width_px=int(tile_outline_width_px),
        coordinate_labels=bool(coordinate_labels),
        label_font_size_px=int(label_font_size_px) if bool(coordinate_labels) else 0,
        label_stroke_width_px=int(label_stroke_width_px) if bool(coordinate_labels) else 0,
    )


def build_rectangular_tile_bbox_map(layout: RectangularBoardLayout) -> Dict[str, BBox]:
    """Build deterministic per-tile pixel bounding boxes for a rectangular board."""
    bbox_map: Dict[str, BBox] = {}
    for row in range(int(layout.rows)):
        for col in range(int(layout.cols)):
            x0 = int(layout.board_origin_x_px) + int(col) * int(layout.tile_width_px)
            y0 = int(layout.board_origin_y_px) + int(row) * int(layout.tile_height_px)
            x1 = x0 + int(layout.tile_width_px)
            y1 = y0 + int(layout.tile_height_px)
            bbox_map[cell_id((row, col))] = (float(x0), float(y0), float(x1), float(y1))
    return bbox_map


def render_rectangular_tile_board(
    draw: ImageDraw.ImageDraw,
    *,
    layout: RectangularBoardLayout,
    fill_colors_by_coord: Mapping[Coord, Color],
    tile_outline_color: Color | None = None,
    scene_style: PuzzleSceneStyle | None = None,
    panel_chrome_mode: str = "accent_frame",
) -> Dict[str, BBox]:
    """Render one rectangular-tile board with optional top/left coordinate labels."""
    bbox_map = build_rectangular_tile_bbox_map(layout)
    if scene_style is not None:
        panel_pad = max(8, int(round(float(min(layout.tile_width_px, layout.tile_height_px)) * 0.22)))
        panel_bbox = (
            max(0, int(layout.board_origin_x_px) - panel_pad),
            max(0, int(layout.board_origin_y_px) - panel_pad),
            min(int(layout.canvas_width_px), int(layout.board_origin_x_px) + int(layout.board_width_px) + panel_pad),
            min(int(layout.canvas_height_px), int(layout.board_origin_y_px) + int(layout.board_height_px) + panel_pad),
        )
        draw_puzzle_chrome_by_mode(
            draw,
            bbox=panel_bbox,
            style=scene_style,
            radius=max(6, panel_pad),
            border_width=max(1, int(layout.tile_outline_width_px)),
            mode=str(panel_chrome_mode),
        )

    for row in range(int(layout.rows)):
        for col in range(int(layout.cols)):
            coord = (int(row), int(col))
            bbox = bbox_map[cell_id(coord)]
            fill = fill_colors_by_coord.get(coord, (255, 255, 255))
            if scene_style is None:
                outline_color = tuple(int(value) for value in (tile_outline_color or (84, 84, 84)))
                draw.rectangle(
                    [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])],
                    fill=tuple(int(value) for value in fill),
                    outline=outline_color,
                    width=int(layout.tile_outline_width_px),
                )
            else:
                draw_puzzle_grid_cell(
                    draw,
                    bbox=(int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])),
                    fill=tuple(int(value) for value in fill),
                    style=scene_style,
                    outline=tuple(int(value) for value in tile_outline_color) if tile_outline_color else None,
                    width=int(layout.tile_outline_width_px),
                )
    if bool(layout.coordinate_labels):
        font = load_font(int(layout.label_font_size_px), bold=True)
        label_fill = (
            tuple(int(value) for value in scene_style.text_rgb)
            if scene_style is not None
            else (36, 42, 52)
        )
        label_stroke = (
            tuple(int(value) for value in scene_style.text_stroke_rgb)
            if scene_style is not None
            else (255, 255, 255)
        )
        label_y = float(layout.board_origin_y_px) - (0.5 * float(layout.top_label_gutter_px))
        label_x = float(layout.board_origin_x_px) - (0.5 * float(layout.left_label_gutter_px))
        for col in range(int(layout.cols)):
            center_x = float(layout.board_origin_x_px) + (float(col) + 0.5) * float(layout.tile_width_px)
            draw_text_centered(
                draw,
                text=str(int(col) + 1),
                center=(float(center_x), float(label_y)),
                font=font,
                fill=label_fill,
                stroke_fill=label_stroke,
                stroke_width=int(layout.label_stroke_width_px),
            )
        for row in range(int(layout.rows)):
            center_y = float(layout.board_origin_y_px) + (float(row) + 0.5) * float(layout.tile_height_px)
            draw_text_centered(
                draw,
                text=str(int(row) + 1),
                center=(float(label_x), float(center_y)),
                font=font,
                fill=label_fill,
                stroke_fill=label_stroke,
                stroke_width=int(layout.label_stroke_width_px),
            )
    return bbox_map


def build_rectangular_board_background(
    *,
    canvas_width: int,
    canvas_height: int,
    instance_seed: int,
    namespace: str,
) -> tuple[Image.Image, Dict[str, Any], PuzzleSceneStyle, str]:
    """Build a shared puzzle/game-style canvas for one rectangular cell-board."""

    scene_style, style_metadata = resolve_puzzle_scene_style(
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    chrome_mode, chrome_metadata = resolve_panel_chrome_mode(
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    image, background_meta = make_puzzle_scene_background(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        style=scene_style,
    )
    background_record = dict(background_meta)
    background_record["scene_style"] = {
        **dict(style_metadata),
        "panel_chrome": dict(chrome_metadata),
        "panel_chrome_mode": str(chrome_mode),
    }
    return image, background_record, scene_style, str(chrome_mode)


def build_rectangular_board_render_spec(
    *,
    rows: int,
    cols: int,
    layout: RectangularBoardLayout,
    tile_spec: RectangularTileSpec,
    background_meta: Mapping[str, Any],
    post_noise_meta: Mapping[str, Any],
) -> Dict[str, Any]:
    """Build shared render metadata for one rectangular tile board."""
    return {
        "coord_space": "tile_grid",
        "tiling_type": "rectangular_tiling",
        "canvas_width_px": int(layout.canvas_width_px),
        "canvas_height_px": int(layout.canvas_height_px),
        "rows": int(rows),
        "cols": int(cols),
        "tile_width_px": int(layout.tile_width_px),
        "tile_height_px": int(layout.tile_height_px),
        "board_origin_px": [int(layout.board_origin_x_px), int(layout.board_origin_y_px)],
        "board_size_px": [int(layout.board_width_px), int(layout.board_height_px)],
        "coordinate_gutters_px": {
            "left": int(layout.left_label_gutter_px),
            "top": int(layout.top_label_gutter_px),
        },
        "outer_padding_px": {
            "x": int(layout.outer_padding_x_px),
            "y": int(layout.outer_padding_y_px),
        },
        "placement_offset_px": {
            "x": int(layout.placement_offset_x_px),
            "y": int(layout.placement_offset_y_px),
        },
        "tile_outline_width_px": int(layout.tile_outline_width_px),
        "coordinate_labels": bool(layout.coordinate_labels),
        "label_style": {
            "font_size_px": int(layout.label_font_size_px),
            "stroke_width_px": int(layout.label_stroke_width_px),
        },
        "tile_aspect_ratio": round(float(tile_spec.aspect_ratio), 6),
        "tile_orientation": str(tile_spec.orientation),
        "background_style": dict(background_meta),
        "post_image_noise": dict(post_noise_meta),
    }


__all__ = [
    "Color",
    "Coord",
    "RectangularBoardLayout",
    "RectangularTileSpec",
    "build_rectangular_board_render_spec",
    "build_rectangular_board_background",
    "build_rectangular_tile_bbox_map",
    "render_rectangular_tile_board",
    "resolve_rectangular_board_layout",
    "sample_rectangular_tile_spec",
]
