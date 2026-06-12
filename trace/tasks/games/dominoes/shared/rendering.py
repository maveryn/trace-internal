"""Shared domino-chain and tableau renderer for games-domain tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from PIL import Image, ImageDraw

from ....shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.text import draw_game_text_traced as draw_text_traced
from ...shared.layout import apply_games_layout_jitter_to_bbox, offset_bbox
from ...shared.scene_style import GamePanelSceneStyle, draw_panel_scene_chrome, game_panel_scene_style_metadata
from ...shared.style import DominoTheme, build_games_domino_theme


_PIP_LAYOUTS: Dict[int, Tuple[Tuple[float, float], ...]] = {
    0: (),
    1: ((0.50, 0.50),),
    2: ((0.28, 0.28), (0.72, 0.72)),
    3: ((0.28, 0.28), (0.50, 0.50), (0.72, 0.72)),
    4: ((0.28, 0.28), (0.72, 0.28), (0.28, 0.72), (0.72, 0.72)),
    5: ((0.28, 0.28), (0.72, 0.28), (0.50, 0.50), (0.28, 0.72), (0.72, 0.72)),
    6: (
        (0.28, 0.24),
        (0.72, 0.24),
        (0.28, 0.50),
        (0.72, 0.50),
        (0.28, 0.76),
        (0.72, 0.76),
    ),
}


@dataclass(frozen=True)
class DominoTileInstance:
    """One visible domino tile before rendering."""

    tile_id: str
    left_value: int
    right_value: int
    role: str
    is_reference: bool = False
    highlight_right_half: bool = False
    option_label: str | None = None


@dataclass(frozen=True)
class RenderedDominoSpec:
    """One rendered domino tile with scene metadata."""

    tile_id: str
    left_value: int
    right_value: int
    role: str
    is_reference: bool
    option_label: str | None
    bbox_px: Tuple[float, float, float, float]
    row_index: int
    order_index: int


@dataclass(frozen=True)
class DominoRenderParams:
    """Resolved render controls for one domino-chain scene."""

    canvas_width: int
    canvas_height: int
    panel_margin_px: int
    chain_top_px: int
    tile_width_px: int
    tile_height_px: int
    chain_gap_px: int
    candidate_gap_px: int
    row_gap_px: int
    tile_corner_radius_px: int
    pip_radius_px: int
    divider_width_px: int
    reference_tag_font_size_px: int
    reference_tag_gap_px: int
    section_label_font_size_px: int
    section_separator_width_px: int
    font_family: str = ""
    layout_jitter_meta: Dict[str, Any] | None = None


@dataclass(frozen=True)
class RenderedDominoScene:
    """Rendered domino-chain scene plus trace-friendly metadata."""

    image: Image.Image
    domino_specs: Tuple[RenderedDominoSpec, ...]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


def _draw_shadow(
    image: Image.Image,
    *,
    bbox_px: Tuple[float, float, float, float],
    radius_px: int,
    theme: DominoTheme,
) -> None:
    """Draw one soft shadow for a domino tile."""

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


def _draw_pips(
    draw: ImageDraw.ImageDraw,
    *,
    half_bbox_px: Tuple[float, float, float, float],
    value: int,
    pip_radius_px: int,
    pip_rgb: Tuple[int, int, int],
    pip_rendering: str = "flat",
) -> None:
    """Draw one pip pattern inside a domino half."""

    left, top, right, bottom = half_bbox_px
    for x_frac, y_frac in _PIP_LAYOUTS[int(value)]:
        cx = float(left + (x_frac * (right - left)))
        cy = float(top + (y_frac * (bottom - top)))
        if str(pip_rendering) == "engraved":
            draw.ellipse(
                [
                    cx - pip_radius_px - 1,
                    cy - pip_radius_px - 1,
                    cx + pip_radius_px + 1,
                    cy + pip_radius_px + 1,
                ],
                fill=(255, 255, 255),
            )
        elif str(pip_rendering) == "ring":
            draw.ellipse(
                [
                    cx - pip_radius_px - 1,
                    cy - pip_radius_px - 1,
                    cx + pip_radius_px + 1,
                    cy + pip_radius_px + 1,
                ],
                fill=tuple(int(v) for v in pip_rgb),
            )
            draw.ellipse(
                [
                    cx - max(1, pip_radius_px - 2),
                    cy - max(1, pip_radius_px - 2),
                    cx + max(1, pip_radius_px - 2),
                    cy + max(1, pip_radius_px - 2),
                ],
                fill=(255, 255, 255),
            )
            continue
        draw.ellipse(
            [cx - pip_radius_px, cy - pip_radius_px, cx + pip_radius_px, cy + pip_radius_px],
            fill=tuple(int(v) for v in pip_rgb),
        )


def _draw_divider(
    draw: ImageDraw.ImageDraw,
    *,
    divider_x: float,
    top: float,
    bottom: float,
    theme: DominoTheme,
    params: DominoRenderParams,
) -> None:
    """Draw one domino divider using the active theme treatment."""

    color = tuple(int(value) for value in theme.divider_rgb)
    width = int(params.divider_width_px)
    if str(theme.divider_rendering) == "notch":
        notch_w = max(2.0, 0.55 * float(width))
        draw.rounded_rectangle(
            [
                float(divider_x - notch_w),
                float(top + 7.0),
                float(divider_x + notch_w),
                float(bottom - 7.0),
            ],
            radius=max(2, int(width)),
            fill=color,
        )
        return
    draw.line(
        [(divider_x, top + 6), (divider_x, bottom - 6)],
        fill=color,
        width=width,
    )


def _draw_reference_tag(
    draw: ImageDraw.ImageDraw,
    *,
    tile_bbox_px: Tuple[float, float, float, float],
    params: DominoRenderParams,
    theme: DominoTheme,
) -> Tuple[float, float, float, float]:
    """Draw one small REF tag above a marked domino tile."""

    font = load_font(
        int(params.reference_tag_font_size_px),
        bold=True,
        font_family=str(params.font_family) or None,
    )
    text = "REF"
    text_bbox = draw.textbbox((0, 0), text, font=font, stroke_width=1)
    text_width = float(text_bbox[2] - text_bbox[0])
    text_height = float(text_bbox[3] - text_bbox[1])
    pad_x = 10.0
    pad_y = 4.0
    tag_width = text_width + (2.0 * pad_x)
    tag_height = text_height + (2.0 * pad_y)
    left, top, right, _ = tile_bbox_px
    tag_left = float(left + (0.5 * ((right - left) - tag_width)))
    tag_top = float(top - params.reference_tag_gap_px - tag_height)
    tag_bbox = (
        round(float(tag_left), 3),
        round(float(tag_top), 3),
        round(float(tag_left + tag_width), 3),
        round(float(tag_top + tag_height), 3),
    )
    draw.rounded_rectangle(
        tag_bbox,
        radius=int(0.5 * tag_height),
        fill=tuple(int(value) for value in theme.reference_tag_fill_rgb),
    )
    draw_text_traced(draw,
        (float(tag_left + pad_x), float(tag_top + pad_y)),
        text,
        font=font,
        fill=tuple(int(value) for value in theme.reference_tag_text_rgb),
        stroke_width=1,
        stroke_fill=(0, 0, 0),
     role="readout", required=False,)
    return tag_bbox


def _draw_option_label(
    draw: ImageDraw.ImageDraw,
    *,
    tile_bbox_px: Tuple[float, float, float, float],
    label: str,
    params: DominoRenderParams,
    theme: DominoTheme,
) -> Tuple[float, float, float, float]:
    """Draw a compact option label above one loose domino."""

    font = load_font(
        max(14, int(params.reference_tag_font_size_px)),
        bold=True,
        font_family=str(params.font_family) or None,
    )
    text = str(label)
    text_bbox = draw.textbbox((0, 0), text, font=font, stroke_width=1)
    text_width = float(text_bbox[2] - text_bbox[0])
    text_height = float(text_bbox[3] - text_bbox[1])
    pad_x = 8.0
    pad_y = 3.0
    width = max(24.0, text_width + (2.0 * pad_x))
    height = text_height + (2.0 * pad_y)
    left, top, right, _ = tile_bbox_px
    label_left = float(left + (0.5 * ((right - left) - width)))
    label_top = max(2.0, float(top - height - 4.0))
    label_bbox = (
        round(float(label_left), 3),
        round(float(label_top), 3),
        round(float(label_left + width), 3),
        round(float(label_top + height), 3),
    )
    fill = tuple(int(value) for value in theme.reference_tag_fill_rgb)
    draw.rounded_rectangle(
        label_bbox,
        radius=int(0.5 * height),
        fill=fill,
        outline=tuple(int(value) for value in theme.reference_outline_rgb),
        width=1,
    )
    draw_text_traced(draw,
        (
            float(label_left + (0.5 * (width - text_width)) - text_bbox[0]),
            float(label_top + pad_y - text_bbox[1]),
        ),
        text,
        font=font,
        fill=tuple(int(value) for value in theme.reference_tag_text_rgb),
        stroke_width=1,
        stroke_fill=(0, 0, 0),
     role="readout", required=False,)
    return label_bbox


def _draw_domino_tile(
    image: Image.Image,
    *,
    bbox_px: Tuple[float, float, float, float],
    tile: DominoTileInstance,
    theme: DominoTheme,
    params: DominoRenderParams,
) -> Tuple[float, float, float, float] | None:
    """Draw one domino tile and return the optional reference-tag bbox."""

    draw = ImageDraw.Draw(image)
    left, top, right, bottom = bbox_px
    radius = int(params.tile_corner_radius_px)
    outline_rgb = theme.reference_outline_rgb if bool(tile.is_reference) else theme.tile_border_rgb
    outline_width = int(theme.tile_border_width_px + (1 if bool(tile.is_reference) else 0))
    draw.rounded_rectangle(
        [left, top, right, bottom],
        radius=radius,
        fill=tuple(int(value) for value in theme.tile_fill_rgb),
        outline=tuple(int(value) for value in outline_rgb),
        width=outline_width,
    )
    if str(theme.tile_rendering) == "inset" and theme.tile_inner_fill_rgb is not None:
        inset = max(4.0, float(outline_width) + 1.0)
        draw.rounded_rectangle(
            [left + inset, top + inset, right - inset, bottom - inset],
            radius=max(4, radius - 4),
            fill=tuple(int(value) for value in theme.tile_inner_fill_rgb),
        )

    divider_x = float(left + (0.5 * (right - left)))
    _draw_divider(
        draw,
        divider_x=divider_x,
        top=top,
        bottom=bottom,
        theme=theme,
        params=params,
    )

    left_half = (left + 6, top + 6, divider_x - 6, bottom - 6)
    right_half = (divider_x + 6, top + 6, right - 6, bottom - 6)
    _draw_pips(
        draw,
        half_bbox_px=left_half,
        value=int(tile.left_value),
        pip_radius_px=int(params.pip_radius_px),
        pip_rgb=tuple(int(value) for value in theme.pip_rgb),
        pip_rendering=str(theme.pip_rendering),
    )
    _draw_pips(
        draw,
        half_bbox_px=right_half,
        value=int(tile.right_value),
        pip_radius_px=int(params.pip_radius_px),
        pip_rgb=tuple(int(value) for value in theme.pip_rgb),
        pip_rendering=str(theme.pip_rendering),
    )

    if bool(tile.highlight_right_half):
        highlight_inset = 5.0
        draw.rounded_rectangle(
            [
                divider_x + highlight_inset,
                top + highlight_inset,
                right - highlight_inset,
                bottom - highlight_inset,
            ],
            radius=max(6, radius - 4),
            outline=tuple(int(value) for value in theme.reference_outline_rgb),
            width=3,
        )

    if bool(tile.is_reference):
        return _draw_reference_tag(
            draw,
            tile_bbox_px=bbox_px,
            params=params,
            theme=theme,
        )
    return None


def _draw_section_chrome(
    image: Image.Image,
    *,
    chain_bboxes: Sequence[Tuple[float, float, float, float]],
    candidate_bboxes: Sequence[Tuple[float, float, float, float]],
    params: DominoRenderParams,
    theme: DominoTheme,
) -> Dict[str, Any]:
    """Draw light chain/candidate separation chrome and return render metadata."""

    if not chain_bboxes or not candidate_bboxes:
        return {}

    chain_top = min(float(bbox[1]) for bbox in chain_bboxes)
    chain_bottom = max(float(bbox[3]) for bbox in chain_bboxes)
    candidate_top = min(float(bbox[1]) for bbox in candidate_bboxes)
    separator_y = round(float(chain_bottom + (0.5 * (candidate_top - chain_bottom))), 3)
    all_bboxes = list(chain_bboxes) + list(candidate_bboxes)
    line_left = max(12.0, min(float(bbox[0]) for bbox in all_bboxes) - 28.0)
    line_right = min(float(params.canvas_width) - 12.0, max(float(bbox[2]) for bbox in all_bboxes) + 28.0)
    line_width = max(1, int(params.section_separator_width_px))

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.line(
        [(line_left, float(separator_y)), (line_right, float(separator_y))],
        fill=(255, 255, 255, 92),
        width=int(line_width),
    )

    font = load_font(
        int(params.section_label_font_size_px),
        bold=True,
        font_family=str(params.font_family) or None,
    )
    text_fill = (255, 255, 255)
    text_stroke = resolve_text_stroke_fill(text_fill)
    label_fill = (
        int(theme.shadow_rgb[0]),
        int(theme.shadow_rgb[1]),
        int(theme.shadow_rgb[2]),
        142,
    )
    pad_x = 10.0
    pad_y = 5.0
    label_bboxes: Dict[str, List[float]] = {}

    def draw_label(key: str, text: str, x: float, y: float) -> None:
        lines = [line for line in str(text).split("\n") if line]
        if not lines:
            return
        line_bboxes = [draw.textbbox((0, 0), line, font=font, stroke_width=1) for line in lines]
        line_widths = [float(bbox[2] - bbox[0]) for bbox in line_bboxes]
        line_heights = [float(bbox[3] - bbox[1]) for bbox in line_bboxes]
        line_gap = 2.0
        text_width = max(line_widths)
        text_height = sum(line_heights) + (line_gap * float(max(0, len(lines) - 1)))
        label_bbox = (
            round(float(x), 3),
            round(float(y), 3),
            round(float(x + text_width + (2.0 * pad_x)), 3),
            round(float(y + text_height + (2.0 * pad_y)), 3),
        )
        draw.rounded_rectangle(
            label_bbox,
            radius=round(float(label_bbox[3] - label_bbox[1]) / 2.0),
            fill=label_fill,
        )
        text_y = float(y + pad_y)
        for line, line_width, line_height in zip(lines, line_widths, line_heights):
            text_x = float(x + pad_x + (0.5 * (text_width - line_width)))
            draw_text_traced(draw,
                (text_x, text_y),
                line,
                font=font,
                fill=text_fill,
                stroke_width=1,
                stroke_fill=text_stroke,
             role="readout", required=False,)
            text_y += float(line_height + line_gap)
        label_bboxes[str(key)] = [float(value) for value in label_bbox]

    chain_label_y = max(14.0, float(chain_top - 50.0))
    candidate_label_y = float(separator_y + 8.0)
    draw_label("chain", "CHAIN", line_left, chain_label_y)
    draw_label("candidates", "LOOSE DOMINOES", line_left, candidate_label_y)

    image.alpha_composite(overlay)
    return {
        "section_separator_bbox_px": [
            float(line_left),
            float(separator_y - max(1.0, line_width / 2.0)),
            float(line_right),
            float(separator_y + max(1.0, line_width / 2.0)),
        ],
        "section_label_bboxes_px": label_bboxes,
    }


def _centered_row_layout(
    *,
    item_count: int,
    item_width_px: int,
    gap_px: int,
    canvas_width: int,
    panel_margin_px: int,
) -> Tuple[List[float], float]:
    """Return centered row positions and a fitted item width that stays on-canvas."""

    count = max(0, int(item_count))
    if count <= 0:
        return [], float(item_width_px)
    available_width = max(1.0, float(canvas_width) - (2.0 * float(panel_margin_px)))
    effective_gap = float(max(0, int(gap_px)))
    min_item_width = min(float(item_width_px), 48.0)
    if count > 1 and (float(count) * min_item_width) + (float(count - 1) * effective_gap) > available_width:
        effective_gap = max(6.0, math.floor((available_width - (float(count) * min_item_width)) / float(count - 1)))
    fitted_width = min(
        float(item_width_px),
        math.floor((available_width - (float(max(0, count - 1)) * effective_gap)) / float(count)),
    )
    fitted_width = max(1.0, float(fitted_width))
    total_width = (float(count) * fitted_width) + (float(max(0, count - 1)) * effective_gap)
    start_x = float(0.5 * (float(canvas_width) - total_width))
    return [float(start_x + (index * (fitted_width + effective_gap))) for index in range(count)], float(fitted_width)


def _panel_bbox_for_dominoes(
    *,
    chain_bboxes: Sequence[Tuple[float, float, float, float]],
    candidate_bboxes: Sequence[Tuple[float, float, float, float]],
    params: DominoRenderParams,
) -> Tuple[int, int, int, int]:
    """Return a shared backing-panel bbox around the jittered domino layout."""

    all_bboxes = list(chain_bboxes) + list(candidate_bboxes)
    x0 = min(float(bbox[0]) for bbox in all_bboxes)
    y0 = min(float(bbox[1]) for bbox in all_bboxes)
    x1 = max(float(bbox[2]) for bbox in all_bboxes)
    y1 = max(float(bbox[3]) for bbox in all_bboxes)
    return (
        max(10, int(round(x0 - 46.0))),
        max(10, int(round(y0 - 70.0))),
        min(int(params.canvas_width) - 10, int(round(x1 + 46.0))),
        min(int(params.canvas_height) - 10, int(round(y1 + 50.0))),
    )


def render_domino_chain_scene(
    *,
    chain_tiles: Sequence[DominoTileInstance],
    candidate_tiles: Sequence[DominoTileInstance],
    background: Image.Image,
    scene_variant: str,
    style_variant: str,
    params: DominoRenderParams,
    panel_style: GamePanelSceneStyle | None = None,
) -> RenderedDominoScene:
    """Render one domino chain with candidate tableau and return trace metadata."""

    if not chain_tiles:
        raise ValueError("domino scene requires at least one chain tile")
    image = background.convert("RGBA")
    theme = build_games_domino_theme(style_variant=str(style_variant))

    chain_lefts, chain_tile_width = _centered_row_layout(
        item_count=len(chain_tiles),
        item_width_px=int(params.tile_width_px),
        gap_px=int(params.chain_gap_px),
        canvas_width=int(params.canvas_width),
        panel_margin_px=int(params.panel_margin_px),
    )
    chain_top = float(params.chain_top_px)
    chain_bboxes: List[Tuple[float, float, float, float]] = []
    for left in chain_lefts:
        chain_bboxes.append(
            (
                round(float(left), 3),
                round(float(chain_top), 3),
                round(float(left + chain_tile_width), 3),
                round(float(chain_top + params.tile_height_px), 3),
            )
        )

    candidate_row_groups: List[Sequence[DominoTileInstance]]
    if str(scene_variant) == "two_row":
        top_count = int(math.ceil(float(len(candidate_tiles)) / 2.0))
        candidate_row_groups = [candidate_tiles[:top_count], candidate_tiles[top_count:]]
    else:
        candidate_row_groups = [candidate_tiles]
    candidate_top = float(chain_top + params.tile_height_px + params.reference_tag_gap_px + 122)

    candidate_bboxes: List[Tuple[float, float, float, float]] = []
    candidate_row_ids: List[List[str]] = []
    order_index = 0
    scene_entities: List[Dict[str, Any]] = []
    domino_specs: List[RenderedDominoSpec] = []
    reference_tag_bboxes: Dict[str, List[float]] = {}
    option_label_bboxes: Dict[str, List[float]] = {}

    for row_index, row_tiles in enumerate(candidate_row_groups):
        row_y = float(candidate_top + (row_index * (params.tile_height_px + params.row_gap_px)))
        row_lefts, candidate_tile_width = _centered_row_layout(
            item_count=len(row_tiles),
            item_width_px=int(params.tile_width_px),
            gap_px=int(params.candidate_gap_px),
            canvas_width=int(params.canvas_width),
            panel_margin_px=int(params.panel_margin_px),
        )
        row_ids: List[str] = []
        for local_index, tile in enumerate(row_tiles):
            bbox_px = (
                round(float(row_lefts[local_index]), 3),
                round(float(row_y), 3),
                round(float(row_lefts[local_index] + candidate_tile_width), 3),
                round(float(row_y + params.tile_height_px), 3),
            )
            candidate_bboxes.append(bbox_px)
            row_ids.append(str(tile.tile_id))
        candidate_row_ids.append(row_ids)

    all_tiles = list(chain_tiles) + list(candidate_tiles)
    all_bboxes = chain_bboxes + candidate_bboxes
    row_indices = ([0] * len(chain_tiles)) + [
        int(1 + row_index)
        for row_index, row_tiles in enumerate(candidate_row_groups)
        for _ in row_tiles
    ]
    group_bbox = (
        min(float(bbox[0]) for bbox in all_bboxes),
        min(float(bbox[1]) for bbox in all_bboxes),
        max(float(bbox[2]) for bbox in all_bboxes),
        max(float(bbox[3]) for bbox in all_bboxes),
    )
    _group_bbox, dx, dy, layout_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=group_bbox,
        canvas_width=int(params.canvas_width),
        canvas_height=int(params.canvas_height),
        jitter=params.layout_jitter_meta,
    )
    all_bboxes = [offset_bbox(bbox_px, dx=dx, dy=dy) for bbox_px in all_bboxes]
    chain_bboxes = list(all_bboxes[: len(chain_tiles)])
    candidate_bboxes = list(all_bboxes[len(chain_tiles) :])
    panel_bbox = _panel_bbox_for_dominoes(
        chain_bboxes=chain_bboxes,
        candidate_bboxes=candidate_bboxes,
        params=params,
    )
    if panel_style is not None:
        draw_panel_scene_chrome(
            ImageDraw.Draw(image),
            bbox=panel_bbox,
            style=panel_style,
            radius=18,
            border_width=3,
        )

    section_chrome = _draw_section_chrome(
        image,
        chain_bboxes=chain_bboxes,
        candidate_bboxes=candidate_bboxes,
        params=params,
        theme=theme,
    )

    for tile, bbox_px, row_index in zip(all_tiles, all_bboxes, row_indices):
        _draw_shadow(
            image,
            bbox_px=bbox_px,
            radius_px=int(params.tile_corner_radius_px),
            theme=theme,
        )
        reference_tag_bbox = _draw_domino_tile(
            image,
            bbox_px=bbox_px,
            tile=tile,
            theme=theme,
            params=params,
        )
        if reference_tag_bbox is not None:
            reference_tag_bboxes[str(tile.tile_id)] = [float(value) for value in reference_tag_bbox]
        if tile.option_label:
            label_bbox = _draw_option_label(
                ImageDraw.Draw(image),
                tile_bbox_px=bbox_px,
                label=str(tile.option_label),
                params=params,
                theme=theme,
            )
            option_label_bboxes[str(tile.tile_id)] = [float(value) for value in label_bbox]
        domino_specs.append(
            RenderedDominoSpec(
                tile_id=str(tile.tile_id),
                left_value=int(tile.left_value),
                right_value=int(tile.right_value),
                role=str(tile.role),
                is_reference=bool(tile.is_reference),
                option_label=None if tile.option_label is None else str(tile.option_label),
                bbox_px=bbox_px,
                row_index=int(row_index),
                order_index=int(order_index),
            )
        )
        scene_entities.append(
            {
                "entity_id": str(tile.tile_id),
                "entity_type": "domino_tile",
                "bbox_px": [float(value) for value in bbox_px],
                "meta": {
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "is_reference": bool(tile.is_reference),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                    "row_index": int(row_index),
                    "order_index": int(order_index),
                },
            }
        )
        order_index += 1

    render_map = {
        "scene_variant": str(scene_variant),
        "style_variant": str(style_variant),
        "domino_bboxes_px": {str(spec.tile_id): [float(value) for value in spec.bbox_px] for spec in domino_specs},
        "chain_tile_ids": [str(tile.tile_id) for tile in chain_tiles],
        "candidate_tile_ids": [str(tile.tile_id) for tile in candidate_tiles],
        "candidate_row_ids": candidate_row_ids,
        "reference_tag_bboxes_px": reference_tag_bboxes,
        "option_label_bboxes_px": option_label_bboxes,
        "layout_jitter": dict(layout_jitter),
        "scene_panel_bbox_px": [int(value) for value in panel_bbox],
        "panel_scene_style": {}
        if panel_style is None
        else game_panel_scene_style_metadata(panel_style),
        "font_family": str(params.font_family),
    }
    render_map.update(section_chrome)
    return RenderedDominoScene(
        image=image.convert("RGB"),
        domino_specs=tuple(domino_specs),
        scene_entities=tuple(scene_entities),
        render_map=render_map,
    )


__all__ = [
    "DominoRenderParams",
    "DominoTileInstance",
    "RenderedDominoScene",
    "RenderedDominoSpec",
    "render_domino_chain_scene",
]
