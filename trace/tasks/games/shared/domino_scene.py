"""Shared domino-chain and tableau renderer for games-domain tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from .style import DominoTheme, build_games_domino_theme


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


@dataclass(frozen=True)
class RenderedDominoSpec:
    """One rendered domino tile with scene metadata."""

    tile_id: str
    left_value: int
    right_value: int
    role: str
    is_reference: bool
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
) -> None:
    """Draw one pip pattern inside a domino half."""

    left, top, right, bottom = half_bbox_px
    for x_frac, y_frac in _PIP_LAYOUTS[int(value)]:
        cx = float(left + (x_frac * (right - left)))
        cy = float(top + (y_frac * (bottom - top)))
        draw.ellipse(
            [cx - pip_radius_px, cy - pip_radius_px, cx + pip_radius_px, cy + pip_radius_px],
            fill=tuple(int(v) for v in pip_rgb),
        )


def _draw_reference_tag(
    draw: ImageDraw.ImageDraw,
    *,
    tile_bbox_px: Tuple[float, float, float, float],
    params: DominoRenderParams,
    theme: DominoTheme,
) -> Tuple[float, float, float, float]:
    """Draw one small REF tag above a marked domino tile."""

    font = load_font(int(params.reference_tag_font_size_px), bold=True)
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
    draw.text(
        (float(tag_left + pad_x), float(tag_top + pad_y)),
        text,
        font=font,
        fill=tuple(int(value) for value in theme.reference_tag_text_rgb),
        stroke_width=1,
        stroke_fill=(0, 0, 0),
    )
    return tag_bbox


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

    divider_x = float(left + (0.5 * (right - left)))
    draw.line(
        [(divider_x, top + 6), (divider_x, bottom - 6)],
        fill=tuple(int(value) for value in theme.divider_rgb),
        width=int(params.divider_width_px),
    )

    left_half = (left + 6, top + 6, divider_x - 6, bottom - 6)
    right_half = (divider_x + 6, top + 6, right - 6, bottom - 6)
    _draw_pips(
        draw,
        half_bbox_px=left_half,
        value=int(tile.left_value),
        pip_radius_px=int(params.pip_radius_px),
        pip_rgb=tuple(int(value) for value in theme.pip_rgb),
    )
    _draw_pips(
        draw,
        half_bbox_px=right_half,
        value=int(tile.right_value),
        pip_radius_px=int(params.pip_radius_px),
        pip_rgb=tuple(int(value) for value in theme.pip_rgb),
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


def _centered_positions(*, item_count: int, item_width_px: int, gap_px: int, canvas_width: int) -> List[float]:
    """Return centered left-edge positions for a row of fixed-width items."""

    total_width = (int(item_count) * int(item_width_px)) + (max(0, int(item_count) - 1) * int(gap_px))
    start_x = float(0.5 * (int(canvas_width) - total_width))
    return [float(start_x + (index * (int(item_width_px) + int(gap_px)))) for index in range(int(item_count))]


def render_domino_chain_scene(
    *,
    chain_tiles: Sequence[DominoTileInstance],
    candidate_tiles: Sequence[DominoTileInstance],
    background: Image.Image,
    scene_variant: str,
    style_variant: str,
    params: DominoRenderParams,
) -> RenderedDominoScene:
    """Render one domino chain with candidate tableau and return trace metadata."""

    if not chain_tiles:
        raise ValueError("domino scene requires at least one chain tile")
    image = background.convert("RGBA")
    theme = build_games_domino_theme(style_variant=str(style_variant))

    chain_lefts = _centered_positions(
        item_count=len(chain_tiles),
        item_width_px=int(params.tile_width_px),
        gap_px=int(params.chain_gap_px),
        canvas_width=int(params.canvas_width),
    )
    chain_top = float(params.chain_top_px)
    chain_bboxes: List[Tuple[float, float, float, float]] = []
    for left in chain_lefts:
        chain_bboxes.append(
            (
                round(float(left), 3),
                round(float(chain_top), 3),
                round(float(left + params.tile_width_px), 3),
                round(float(chain_top + params.tile_height_px), 3),
            )
        )

    candidate_row_groups: List[Sequence[DominoTileInstance]]
    if str(scene_variant) == "two_row":
        top_count = int(math.ceil(float(len(candidate_tiles)) / 2.0))
        candidate_row_groups = [candidate_tiles[:top_count], candidate_tiles[top_count:]]
    else:
        candidate_row_groups = [candidate_tiles]
    candidate_top = float(chain_top + params.tile_height_px + params.reference_tag_gap_px + 40)

    candidate_bboxes: List[Tuple[float, float, float, float]] = []
    candidate_row_ids: List[List[str]] = []
    order_index = 0
    scene_entities: List[Dict[str, Any]] = []
    domino_specs: List[RenderedDominoSpec] = []
    reference_tag_bboxes: Dict[str, List[float]] = {}

    for row_index, row_tiles in enumerate(candidate_row_groups):
        row_y = float(candidate_top + (row_index * (params.tile_height_px + params.row_gap_px)))
        row_lefts = _centered_positions(
            item_count=len(row_tiles),
            item_width_px=int(params.tile_width_px),
            gap_px=int(params.candidate_gap_px),
            canvas_width=int(params.canvas_width),
        )
        row_ids: List[str] = []
        for local_index, tile in enumerate(row_tiles):
            bbox_px = (
                round(float(row_lefts[local_index]), 3),
                round(float(row_y), 3),
                round(float(row_lefts[local_index] + params.tile_width_px), 3),
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
        domino_specs.append(
            RenderedDominoSpec(
                tile_id=str(tile.tile_id),
                left_value=int(tile.left_value),
                right_value=int(tile.right_value),
                role=str(tile.role),
                is_reference=bool(tile.is_reference),
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
    }
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
