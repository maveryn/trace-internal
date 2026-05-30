"""Shared rectangular-tile board layout and rendering helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from PIL import Image, ImageDraw

from trace.tasks.shared.bbox_projection import BBox
from trace.tasks.shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from trace.tasks.shared.text_rendering import draw_text_centered, load_font
from trace.tasks.puzzles.shared.common import resolve_puzzle_axis_variant
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

SUPPORTED_CELL_BOARD_TILE_STYLES: Tuple[str, ...] = (
    "classic_grid",
    "rounded_tiles",
    "inset_tiles",
    "thin_line",
    "lab_matrix",
)


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


def _resolve_cell_board_tile_style(
    *,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> tuple[str, Dict[str, float]]:
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=rendering_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_CELL_BOARD_TILE_STYLES,
        task_id=str(namespace),
        explicit_key="cell_board_tile_style",
        weights_key="cell_board_tile_style_weights",
        balance_flag_key="balanced_cell_board_tile_style_sampling",
        axis_namespace="cell_board_tile_style",
    )


def _cell_board_tile_style_metadata(
    *,
    tile_style: str,
    tile_style_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    return {
        "tile_style": str(tile_style),
        "tile_style_probabilities": {
            str(key): float(value)
            for key, value in tile_style_probabilities.items()
        },
        "semantic_color_policy": {
            "tile_fill_colors_preserved": True,
            "tile_geometry_preserved": True,
            "style_is_non_semantic": True,
        },
    }


def rectangular_board_tile_style(background_meta: Mapping[str, Any]) -> str:
    """Return the sampled rectangular board tile style from background metadata."""

    scene_style = background_meta.get("scene_style", {}) if isinstance(background_meta, Mapping) else {}
    board_meta = scene_style.get("cell_board", {}) if isinstance(scene_style, Mapping) else {}
    tile_style = board_meta.get("tile_style", "") if isinstance(board_meta, Mapping) else ""
    if str(tile_style) in set(SUPPORTED_CELL_BOARD_TILE_STYLES):
        return str(tile_style)
    return "classic_grid"


def _draw_styled_tile(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: BBox,
    fill: Color,
    outline_color: Color,
    width: int,
    tile_style: str,
    scene_style: PuzzleSceneStyle | None,
) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    tile_style_id = str(tile_style)
    fill_rgb = tuple(int(value) for value in fill)
    outline_rgb = tuple(int(value) for value in outline_color)
    line_width = max(1, int(width))
    cell_w = max(1.0, float(x1) - float(x0))
    cell_h = max(1.0, float(y1) - float(y0))
    radius = max(3, int(round(min(cell_w, cell_h) * 0.11)))

    if scene_style is not None and tile_style_id == "classic_grid":
        draw_puzzle_grid_cell(
            draw,
            bbox=(int(x0), int(y0), int(x1), int(y1)),
            fill=fill_rgb,
            style=scene_style,
            outline=outline_rgb,
            width=line_width,
        )
        return

    if tile_style_id == "rounded_tiles":
        draw.rounded_rectangle(
            [x0, y0, x1, y1],
            radius=radius,
            fill=fill_rgb,
            outline=outline_rgb,
            width=line_width,
        )
        return

    if tile_style_id == "inset_tiles":
        grid_fill = tuple(int(value) for value in (scene_style.grid_rgb if scene_style is not None else outline_rgb))
        draw.rectangle([x0, y0, x1, y1], fill=grid_fill, outline=outline_rgb, width=1)
        inset = max(2.0, min(cell_w, cell_h) * 0.10)
        draw.rounded_rectangle(
            [x0 + inset, y0 + inset, x1 - inset, y1 - inset],
            radius=max(2, radius - 2),
            fill=fill_rgb,
            outline=outline_rgb,
            width=max(1, line_width - 1),
        )
        return

    if tile_style_id == "thin_line":
        draw.rectangle([x0, y0, x1, y1], fill=fill_rgb, outline=outline_rgb, width=max(1, line_width - 1))
        return

    if tile_style_id == "lab_matrix":
        draw.rectangle([x0, y0, x1, y1], fill=fill_rgb, outline=outline_rgb, width=line_width)
        accent_rgb = tuple(int(value) for value in (scene_style.panel_accent_rgb if scene_style is not None else outline_rgb))
        inset = max(3.0, min(cell_w, cell_h) * 0.14)
        draw.line([(x0 + inset, y0 + inset), (x1 - inset, y0 + inset)], fill=accent_rgb, width=1)
        draw.line([(x0 + inset, y0 + inset), (x0 + inset, y1 - inset)], fill=accent_rgb, width=1)
        return

    draw.rectangle([x0, y0, x1, y1], fill=fill_rgb, outline=outline_rgb, width=line_width)


def render_rectangular_tile_board(
    draw: ImageDraw.ImageDraw,
    *,
    layout: RectangularBoardLayout,
    fill_colors_by_coord: Mapping[Coord, Color],
    tile_outline_color: Color | None = None,
    scene_style: PuzzleSceneStyle | None = None,
    panel_chrome_mode: str = "accent_frame",
    label_font_family: str | None = None,
    tile_style: str = "classic_grid",
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
            outline_color = tuple(
                int(value)
                for value in (
                    tile_outline_color
                    or (scene_style.grid_rgb if scene_style is not None else (84, 84, 84))
                )
            )
            _draw_styled_tile(
                draw,
                bbox=bbox,
                fill=tuple(int(value) for value in fill),
                outline_color=outline_color,
                width=int(layout.tile_outline_width_px),
                tile_style=str(tile_style),
                scene_style=scene_style,
            )
    if bool(layout.coordinate_labels):
        font = load_font(int(layout.label_font_size_px), bold=True, font_family=label_font_family)
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
    params: Mapping[str, Any] | None = None,
    rendering_defaults: Mapping[str, Any] | None = None,
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
    label_font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.board_label_font",
        params=params or {},
    )
    label_font_metadata = {
        **get_font_family_record(str(label_font_family)).to_trace(),
        "font_asset_version": font_asset_version(),
        "selection_scope": "cell_board_coordinate_labels",
        "include_tags": [],
        "exclude_tags": [],
    }
    tile_style, tile_style_probabilities = _resolve_cell_board_tile_style(
        params=params or {},
        rendering_defaults=rendering_defaults or {},
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
        "board_label_font": dict(label_font_metadata),
        "cell_board": _cell_board_tile_style_metadata(
            tile_style=str(tile_style),
            tile_style_probabilities=tile_style_probabilities,
        ),
    }
    return image, background_record, scene_style, str(chrome_mode)


def rectangular_board_label_font_family(background_meta: Mapping[str, Any]) -> str:
    """Return the sampled board label font family from background metadata."""

    scene_style = background_meta.get("scene_style", {}) if isinstance(background_meta, Mapping) else {}
    font_meta = scene_style.get("board_label_font", {}) if isinstance(scene_style, Mapping) else {}
    family = font_meta.get("font_family", "") if isinstance(font_meta, Mapping) else ""
    return str(family)


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
    scene_style_meta = background_meta.get("scene_style", {}) if isinstance(background_meta, Mapping) else {}
    label_font_meta = (
        scene_style_meta.get("board_label_font", {})
        if isinstance(scene_style_meta, Mapping)
        else {}
    )
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
            "font": dict(label_font_meta) if isinstance(label_font_meta, Mapping) else {},
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
    "SUPPORTED_CELL_BOARD_TILE_STYLES",
    "build_rectangular_board_render_spec",
    "build_rectangular_board_background",
    "build_rectangular_tile_bbox_map",
    "rectangular_board_label_font_family",
    "rectangular_board_tile_style",
    "render_rectangular_tile_board",
    "resolve_rectangular_board_layout",
    "sample_rectangular_tile_spec",
]
