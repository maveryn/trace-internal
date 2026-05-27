"""Shared bingo-card renderer for games-domain bingo tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from .bingo_common import BINGO_BOARD_SIZE, BINGO_COLUMN_LABELS, BingoCellInstance
from .layout import apply_games_layout_jitter_to_bbox
from .scene_style import GamePanelSceneStyle, draw_panel_scene_chrome, game_panel_scene_style_metadata
from .style import BingoTheme, build_games_bingo_theme


SUPPORTED_BINGO_MARK_SHAPES: Tuple[str, ...] = ("ellipse", "cell", "ring", "slash")
SUPPORTED_BINGO_CELL_FILL_PATTERNS: Tuple[str, ...] = ("solid", "column_tint", "checker_tint")


@dataclass(frozen=True)
class BingoRenderParams:
    """Resolved render controls for one bingo-card scene."""

    canvas_width: int
    canvas_height: int
    card_width_px: int
    card_height_px: int
    card_corner_radius_px: int
    panel_margin_px: int
    title_font_size_px: int
    title_band_height_px: int
    header_font_size_px: int
    header_height_px: int
    grid_gap_px: int
    number_font_size_px: int
    cell_corner_radius_px: int
    cell_gap_px: int
    mark_inset_px: int
    mark_shape: str = "ellipse"
    cell_fill_pattern: str = "solid"
    layout_jitter_meta: Dict[str, Any] | None = None


@dataclass(frozen=True)
class RenderedBingoCellSpec:
    """One visible bingo cell after layout/render assignment."""

    cell_id: str
    row_index: int
    column_index: int
    column_label: str
    number: int
    is_marked: bool
    bbox_px: Tuple[float, float, float, float]


@dataclass(frozen=True)
class RenderedBingoCardScene:
    """Rendered bingo scene plus trace-friendly cell metadata."""

    image: Image.Image
    cell_specs: Tuple[RenderedBingoCellSpec, ...]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


def _draw_shadow(
    image: Image.Image,
    *,
    bbox_px: Tuple[float, float, float, float],
    radius_px: int,
    shadow_rgb: Tuple[int, int, int],
    shadow_alpha: int,
    shadow_offset_px: Tuple[int, int],
) -> None:
    """Draw one soft rounded-rectangle shadow behind the card."""

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    left, top, right, bottom = bbox_px
    dx, dy = shadow_offset_px
    draw.rounded_rectangle(
        [left + dx, top + dy, right + dx, bottom + dy],
        radius=int(radius_px),
        fill=(int(shadow_rgb[0]), int(shadow_rgb[1]), int(shadow_rgb[2]), int(shadow_alpha)),
    )
    image.alpha_composite(overlay)


def render_bingo_card_scene(
    *,
    cells: Sequence[BingoCellInstance],
    background: Image.Image,
    scene_variant: str,
    style_variant: str,
    params: BingoRenderParams,
    panel_style: GamePanelSceneStyle | None = None,
) -> RenderedBingoCardScene:
    """Render one visible bingo card with marked cells and traced cell boxes."""

    if str(scene_variant) != "single_card":
        raise ValueError(f"unsupported bingo scene variant: {scene_variant}")

    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image)
    theme: BingoTheme = build_games_bingo_theme(style_variant=str(style_variant))
    mark_shape = str(params.mark_shape)
    if mark_shape not in SUPPORTED_BINGO_MARK_SHAPES:
        raise ValueError(f"unsupported bingo mark shape: {params.mark_shape}")
    cell_fill_pattern = str(params.cell_fill_pattern)
    if cell_fill_pattern not in SUPPORTED_BINGO_CELL_FILL_PATTERNS:
        raise ValueError(f"unsupported bingo cell fill pattern: {params.cell_fill_pattern}")

    card_left = float(0.5 * (int(params.canvas_width) - int(params.card_width_px)))
    card_top = float(0.5 * (int(params.canvas_height) - int(params.card_height_px)))
    card_right = float(card_left + int(params.card_width_px))
    card_bottom = float(card_top + int(params.card_height_px))
    card_bbox, _dx, _dy, layout_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=(card_left, card_top, card_right, card_bottom),
        canvas_width=int(params.canvas_width),
        canvas_height=int(params.canvas_height),
        jitter=params.layout_jitter_meta,
    )
    card_left, card_top, card_right, card_bottom = [float(value) for value in card_bbox]

    panel_bbox: Tuple[int, int, int, int] | None = None
    if panel_style is not None:
        panel_pad_x = max(20, int(round(float(params.panel_margin_px) * 0.45)))
        panel_pad_top = max(24, int(round(float(params.title_band_height_px) * 0.34)))
        panel_pad_bottom = max(20, int(round(float(params.panel_margin_px) * 0.38)))
        panel_bbox = (
            max(4, int(round(card_left)) - panel_pad_x),
            max(4, int(round(card_top)) - panel_pad_top),
            min(int(params.canvas_width) - 4, int(round(card_right)) + panel_pad_x),
            min(int(params.canvas_height) - 4, int(round(card_bottom)) + panel_pad_bottom),
        )
        draw_panel_scene_chrome(
            draw,
            bbox=panel_bbox,
            style=panel_style,
            radius=max(22, int(params.card_corner_radius_px) + 8),
            border_width=max(2, int(theme.card_border_width_px)),
        )

    _draw_shadow(
        image,
        bbox_px=card_bbox,
        radius_px=int(params.card_corner_radius_px),
        shadow_rgb=tuple(int(value) for value in theme.shadow_rgb),
        shadow_alpha=int(theme.shadow_alpha),
        shadow_offset_px=tuple(int(value) for value in theme.shadow_offset_px),
    )

    draw.rounded_rectangle(
        card_bbox,
        radius=int(params.card_corner_radius_px),
        fill=tuple(int(value) for value in theme.card_fill_rgb),
        outline=tuple(int(value) for value in theme.card_border_rgb),
        width=int(theme.card_border_width_px),
    )

    title_font = load_font(int(params.title_font_size_px), bold=True)
    header_font = load_font(int(params.header_font_size_px), bold=True)
    number_font = load_font(int(params.number_font_size_px), bold=True)

    title_text = "BINGO"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font, stroke_width=1)
    title_origin = (
        float(card_left + (0.5 * ((card_right - card_left) - (title_bbox[2] - title_bbox[0])))),
        float(card_top + max(10.0, 0.5 * (int(params.title_band_height_px) - (title_bbox[3] - title_bbox[1])))),
    )
    draw.text(
        title_origin,
        title_text,
        font=title_font,
        fill=tuple(int(value) for value in theme.title_rgb),
        stroke_width=1,
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.title_rgb)),
    )

    grid_left = float(card_left + int(params.panel_margin_px))
    grid_right = float(card_right - int(params.panel_margin_px))
    header_top = float(card_top + int(params.title_band_height_px))
    header_bottom = float(header_top + int(params.header_height_px))
    grid_top = float(header_bottom + int(params.grid_gap_px))
    grid_bottom = float(card_bottom - int(params.panel_margin_px))

    total_gap_width = float((BINGO_BOARD_SIZE - 1) * int(params.cell_gap_px))
    total_gap_height = float((BINGO_BOARD_SIZE - 1) * int(params.cell_gap_px))
    cell_width = float((grid_right - grid_left - total_gap_width) / BINGO_BOARD_SIZE)
    cell_height = float((grid_bottom - grid_top - total_gap_height) / BINGO_BOARD_SIZE)

    column_header_bboxes: Dict[str, List[float]] = {}
    for column_index, column_label in enumerate(BINGO_COLUMN_LABELS):
        header_bbox = draw.textbbox((0, 0), str(column_label), font=header_font, stroke_width=1)
        header_origin = (
            float(
                grid_left
                + column_index * (cell_width + int(params.cell_gap_px))
                + (0.5 * (cell_width - (header_bbox[2] - header_bbox[0])))
            ),
            float(header_top + (0.5 * (int(params.header_height_px) - (header_bbox[3] - header_bbox[1])))),
        )
        draw.text(
            header_origin,
            str(column_label),
            font=header_font,
            fill=tuple(int(value) for value in theme.header_rgb),
            stroke_width=1,
            stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.header_rgb)),
        )
        column_header_bboxes[str(column_label)] = [
            round(float(header_origin[0]), 3),
            round(float(header_origin[1]), 3),
            round(float(header_origin[0] + (header_bbox[2] - header_bbox[0])), 3),
            round(float(header_origin[1] + (header_bbox[3] - header_bbox[1])), 3),
        ]

    cell_specs: List[RenderedBingoCellSpec] = []
    scene_entities: List[Dict[str, Any]] = []
    cell_bbox_map: Dict[str, List[float]] = {}
    cell_mark_center_map: Dict[str, List[float]] = {}
    mark_overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    mark_draw = ImageDraw.Draw(mark_overlay)

    for cell in cells:
        left = float(grid_left + cell.column_index * (cell_width + int(params.cell_gap_px)))
        top = float(grid_top + cell.row_index * (cell_height + int(params.cell_gap_px)))
        right = float(left + cell_width)
        bottom = float(top + cell_height)
        bbox = (left, top, right, bottom)

        if cell_fill_pattern == "column_tint" and int(cell.column_index) % 2 == 1:
            cell_fill_rgb = tuple(int(value) for value in theme.cell_alt_fill_rgb)
        elif cell_fill_pattern == "checker_tint" and (int(cell.row_index) + int(cell.column_index)) % 2 == 1:
            cell_fill_rgb = tuple(int(value) for value in theme.cell_alt_fill_rgb)
        else:
            cell_fill_rgb = tuple(int(value) for value in theme.cell_fill_rgb)

        draw.rounded_rectangle(
            bbox,
            radius=int(params.cell_corner_radius_px),
            fill=tuple(int(value) for value in cell_fill_rgb),
            outline=tuple(int(value) for value in theme.grid_line_rgb),
            width=2,
        )

        number_text = str(cell.number)
        number_bbox = draw.textbbox((0, 0), number_text, font=number_font, stroke_width=1)
        number_origin = (
            float(left + (0.5 * (cell_width - (number_bbox[2] - number_bbox[0])))),
            float(top + (0.5 * (cell_height - (number_bbox[3] - number_bbox[1])))),
        )
        draw.text(
            number_origin,
            number_text,
            font=number_font,
            fill=tuple(int(value) for value in theme.number_rgb),
            stroke_width=1,
            stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.number_rgb)),
        )

        if bool(cell.is_marked):
            inset = int(params.mark_inset_px)
            mark_bbox = [left + inset, top + inset, right - inset, bottom - inset]
            if mark_shape == "cell":
                mark_draw.rounded_rectangle(
                    [left + 2, top + 2, right - 2, bottom - 2],
                    radius=max(2, int(params.cell_corner_radius_px) - 2),
                    fill=tuple(int(value) for value in theme.mark_fill_rgba),
                    outline=tuple(int(value) for value in theme.mark_outline_rgb),
                    width=3,
                )
            elif mark_shape == "ring":
                mark_draw.ellipse(
                    mark_bbox,
                    fill=tuple(int(value) for value in (*theme.mark_fill_rgba[:3], max(28, int(theme.mark_fill_rgba[3]) // 3))),
                    outline=tuple(int(value) for value in theme.mark_outline_rgb),
                    width=5,
                )
            elif mark_shape == "slash":
                mark_draw.line(
                    [(float(mark_bbox[0]), float(mark_bbox[3])), (float(mark_bbox[2]), float(mark_bbox[1]))],
                    fill=tuple(int(value) for value in (*theme.mark_outline_rgb, 210)),
                    width=max(8, int(params.mark_inset_px)),
                )
                mark_draw.line(
                    [(float(mark_bbox[0]) + 4.0, float(mark_bbox[3])), (float(mark_bbox[2]), float(mark_bbox[1]) - 4.0)],
                    fill=tuple(int(value) for value in theme.mark_fill_rgba),
                    width=max(4, int(params.mark_inset_px) // 2),
                )
            else:
                mark_draw.ellipse(
                    mark_bbox,
                    fill=tuple(int(value) for value in theme.mark_fill_rgba),
                    outline=tuple(int(value) for value in theme.mark_outline_rgb),
                    width=3,
                )

        rounded_bbox = [
            round(float(left), 3),
            round(float(top), 3),
            round(float(right), 3),
            round(float(bottom), 3),
        ]
        cell_bbox_map[str(cell.cell_id)] = list(rounded_bbox)
        cell_mark_center_map[str(cell.cell_id)] = [
            round(float(0.5 * (left + right)), 3),
            round(float(0.5 * (top + bottom)), 3),
        ]
        cell_specs.append(
            RenderedBingoCellSpec(
                cell_id=str(cell.cell_id),
                row_index=int(cell.row_index),
                column_index=int(cell.column_index),
                column_label=str(cell.column_label),
                number=int(cell.number),
                is_marked=bool(cell.is_marked),
                bbox_px=tuple(float(value) for value in rounded_bbox),
            )
        )
        scene_entities.append(
            {
                "entity_id": str(cell.cell_id),
                "kind": "bingo_cell",
                "bbox": list(rounded_bbox),
                "row_index": int(cell.row_index),
                "column_index": int(cell.column_index),
                "column_label": str(cell.column_label),
                "number": int(cell.number),
                "is_marked": bool(cell.is_marked),
            }
        )

    image.alpha_composite(mark_overlay)
    return RenderedBingoCardScene(
        image=image.convert("RGB"),
        cell_specs=tuple(cell_specs),
        scene_entities=tuple(scene_entities),
        render_map={
            "card_bbox_px": [round(float(value), 3) for value in card_bbox],
            "panel_bbox_px": None if panel_bbox is None else [int(value) for value in panel_bbox],
            "column_header_bboxes_px": dict(column_header_bboxes),
            "cell_bboxes_px": dict(cell_bbox_map),
            "cell_mark_centers_px": dict(cell_mark_center_map),
            "mark_shape": str(mark_shape),
            "cell_fill_pattern": str(cell_fill_pattern),
            "style_variant": str(style_variant),
            "panel_scene_style": None if panel_style is None else game_panel_scene_style_metadata(panel_style),
            "layout_jitter": dict(layout_jitter),
        },
    )


__all__ = [
    "BingoRenderParams",
    "RenderedBingoCardScene",
    "RenderedBingoCellSpec",
    "SUPPORTED_BINGO_CELL_FILL_PATTERNS",
    "SUPPORTED_BINGO_MARK_SHAPES",
    "render_bingo_card_scene",
]
