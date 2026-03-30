"""Shared face-up playing-card hand renderer for games-domain tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from .style import CardTheme, build_games_card_theme, suit_color


SUIT_SYMBOLS: Dict[str, str] = {
    "spades": "♠",
    "hearts": "♥",
    "diamonds": "♦",
    "clubs": "♣",
}


@dataclass(frozen=True)
class CardInstance:
    """One visible face-up playing card before rendering."""

    card_id: str
    rank_label: str
    rank_value: int
    suit_name: str
    is_reference: bool = False


@dataclass(frozen=True)
class RenderedCardSpec:
    """One face-up card after layout/render assignment."""

    card_id: str
    rank_label: str
    rank_value: int
    suit_name: str
    suit_symbol: str
    is_reference: bool
    bbox_px: Tuple[float, float, float, float]
    row_index: int
    order_index: int


@dataclass(frozen=True)
class CardRenderParams:
    """Resolved render controls for one card hand scene."""

    canvas_width: int
    canvas_height: int
    card_width_px: int
    card_height_px: int
    panel_margin_px: int
    card_gap_px: int
    row_gap_px: int
    card_corner_radius_px: int
    rank_font_size_px: int
    center_symbol_font_size_px: int
    reference_banner_height_px: int
    reference_font_size_px: int
    continuation_font_size_px: int
    continuation_gap_px: int


@dataclass(frozen=True)
class RenderedCardHandScene:
    """Rendered card-hand scene plus trace-friendly card metadata."""

    image: Image.Image
    card_specs: Tuple[RenderedCardSpec, ...]
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
    """Draw one soft rectangular card shadow onto an RGBA image."""

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


def _draw_card_face(
    image: Image.Image,
    *,
    bbox_px: Tuple[float, float, float, float],
    card: CardInstance,
    theme: CardTheme,
    params: CardRenderParams,
) -> None:
    """Draw one face-up card inside the provided bounding box."""

    draw = ImageDraw.Draw(image)
    left, top, right, bottom = bbox_px
    radius = int(params.card_corner_radius_px)
    draw.rounded_rectangle(
        [left, top, right, bottom],
        radius=radius,
        fill=tuple(int(value) for value in theme.card_fill_rgb),
        outline=tuple(int(value) for value in theme.card_border_rgb),
        width=int(theme.card_border_width_px),
    )

    banner_height_px = int(params.reference_banner_height_px) if bool(card.is_reference) else 0
    if bool(card.is_reference):
        banner_bottom = float(top + params.reference_banner_height_px)
        draw.rounded_rectangle(
            [left, top, right, banner_bottom],
            radius=radius,
            fill=tuple(int(value) for value in theme.reference_fill_rgb),
        )
        banner_font = load_font(int(params.reference_font_size_px), bold=True)
        banner_text = "REF"
        banner_bbox = draw.textbbox((0, 0), banner_text, font=banner_font, stroke_width=1)
        banner_width = float(banner_bbox[2] - banner_bbox[0])
        banner_height = float(banner_bbox[3] - banner_bbox[1])
        banner_origin = (
            float(left + (0.5 * ((right - left) - banner_width))),
            float(top + (0.5 * (params.reference_banner_height_px - banner_height))),
        )
        draw.text(
            banner_origin,
            banner_text,
            font=banner_font,
            fill=tuple(int(value) for value in theme.reference_text_rgb),
            stroke_width=1,
            stroke_fill=(0, 0, 0),
        )

    suit_symbol = SUIT_SYMBOLS[str(card.suit_name)]
    pip_rgb = suit_color(theme, suit_name=str(card.suit_name))
    rank_rgb = (
        tuple(int(value) for value in theme.rank_rgb_red)
        if str(card.suit_name) in {"hearts", "diamonds"}
        else tuple(int(value) for value in theme.rank_rgb_black)
    )
    small_font = load_font(int(params.rank_font_size_px), bold=True)
    center_font = load_font(int(params.center_symbol_font_size_px), bold=True)
    label = f"{card.rank_label}{suit_symbol}"
    label_stroke = resolve_text_stroke_fill(rank_rgb)
    top_label_inset_px = 10
    top_label_origin = (
        float(left + 10),
        float(top + banner_height_px + top_label_inset_px),
    )
    draw.text(
        top_label_origin,
        label,
        font=small_font,
        fill=rank_rgb,
        stroke_width=1,
        stroke_fill=tuple(int(value) for value in label_stroke),
    )

    bottom_bbox = draw.textbbox((0, 0), label, font=small_font, stroke_width=1)
    bottom_origin = (
        float(right - (bottom_bbox[2] - bottom_bbox[0]) - 10),
        float(bottom - (bottom_bbox[3] - bottom_bbox[1]) - 10),
    )
    draw.text(
        bottom_origin,
        label,
        font=small_font,
        fill=rank_rgb,
        stroke_width=1,
        stroke_fill=tuple(int(value) for value in label_stroke),
    )

    center_bbox = draw.textbbox((0, 0), suit_symbol, font=center_font, stroke_width=1)
    center_vertical_nudge_px = float(max(6, int(0.05 * float(bottom - top))))
    center_origin = (
        float(left + (0.5 * ((right - left) - (center_bbox[2] - center_bbox[0])))),
        float(
            top
            + banner_height_px
            + 20
            + (0.5 * ((bottom - top - banner_height_px - 40) - (center_bbox[3] - center_bbox[1])))
            - center_vertical_nudge_px
        ),
    )
    draw.text(
        center_origin,
        suit_symbol,
        font=center_font,
        fill=pip_rgb,
        stroke_width=1,
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(pip_rgb)),
    )


def _row_card_positions(
    *,
    row_card_count: int,
    canvas_width: int,
    card_width_px: int,
    card_gap_px: int,
) -> List[float]:
    """Return left-edge positions for one centered row of equal-width cards."""

    total_width = (int(row_card_count) * int(card_width_px)) + (max(0, int(row_card_count) - 1) * int(card_gap_px))
    start_x = float(0.5 * (int(canvas_width) - total_width))
    return [
        float(start_x + (index * (int(card_width_px) + int(card_gap_px))))
        for index in range(int(row_card_count))
    ]


def _continuation_bbox(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    font_size_px: int,
    anchor_xy: Tuple[float, float],
) -> Tuple[Tuple[float, float], Tuple[float, float, float, float], Any]:
    """Resolve one continuation cue origin/bbox/font tuple."""

    font = load_font(int(font_size_px), bold=True)
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=1)
    width = float(bbox[2] - bbox[0])
    height = float(bbox[3] - bbox[1])
    origin = (
        float(anchor_xy[0] - (0.5 * width)),
        float(anchor_xy[1] - (0.5 * height)),
    )
    return (
        origin,
        (
            round(float(origin[0]), 3),
            round(float(origin[1]), 3),
            round(float(origin[0] + width), 3),
            round(float(origin[1] + height), 3),
        ),
        font,
    )


def render_cards_hand_scene(
    *,
    cards: Sequence[CardInstance],
    background: Image.Image,
    scene_variant: str,
    style_variant: str,
    params: CardRenderParams,
    show_continuation_cue: bool,
) -> RenderedCardHandScene:
    """Render one visible card hand and return card-level trace metadata."""

    if int(len(cards)) <= 0:
        raise ValueError("card hand renderer requires at least one visible card")

    image = background.convert("RGBA")
    theme = build_games_card_theme(style_variant=str(style_variant))
    draw = ImageDraw.Draw(image)

    ordered_cards = [card for card in cards]
    if str(scene_variant) == "two_row":
        top_count = int(math.ceil(float(len(ordered_cards)) / 2.0))
        bottom_count = int(len(ordered_cards) - top_count)
        row_groups = [ordered_cards[:top_count], ordered_cards[top_count:]]
    else:
        row_groups = [ordered_cards]

    row_left_positions = [
        _row_card_positions(
            row_card_count=len(row_cards),
            canvas_width=int(params.canvas_width),
            card_width_px=int(params.card_width_px),
            card_gap_px=int(params.card_gap_px),
        )
        for row_cards in row_groups
    ]

    card_specs: List[RenderedCardSpec] = []
    top_y = float(params.panel_margin_px)
    second_row_y = float(top_y + params.card_height_px + params.row_gap_px)
    row_ys = [top_y] if len(row_groups) == 1 else [top_y, second_row_y]

    order_index = 0
    for row_index, row_cards in enumerate(row_groups):
        row_y = float(row_ys[row_index])
        for local_index, card in enumerate(row_cards):
            left = float(row_left_positions[row_index][local_index])
            bbox_px = (
                round(float(left), 3),
                round(float(row_y), 3),
                round(float(left + params.card_width_px), 3),
                round(float(row_y + params.card_height_px), 3),
            )
            _draw_shadow(
                image,
                bbox_px=bbox_px,
                radius_px=int(params.card_corner_radius_px),
                shadow_rgb=tuple(int(value) for value in theme.shadow_rgb),
                shadow_alpha=int(theme.shadow_alpha),
                shadow_offset_px=tuple(int(value) for value in theme.shadow_offset_px),
            )
            _draw_card_face(
                image,
                bbox_px=bbox_px,
                card=card,
                theme=theme,
                params=params,
            )
            card_specs.append(
                RenderedCardSpec(
                    card_id=str(card.card_id),
                    rank_label=str(card.rank_label),
                    rank_value=int(card.rank_value),
                    suit_name=str(card.suit_name),
                    suit_symbol=str(SUIT_SYMBOLS[str(card.suit_name)]),
                    is_reference=bool(card.is_reference),
                    bbox_px=bbox_px,
                    row_index=int(row_index),
                    order_index=int(order_index),
                )
            )
            order_index += 1

    continuation_bbox_px: List[float] | None = None
    if bool(show_continuation_cue) and len(row_groups) == 2:
        continuation_text = "continue ↘"
        cue_anchor = (
            float(params.canvas_width - params.panel_margin_px - 112),
            float(top_y + params.card_height_px + (0.5 * params.continuation_gap_px)),
        )
        cue_origin, cue_bbox_px, cue_font = _continuation_bbox(
            draw,
            text=continuation_text,
            font_size_px=int(params.continuation_font_size_px),
            anchor_xy=cue_anchor,
        )
        draw.text(
            cue_origin,
            continuation_text,
            font=cue_font,
            fill=tuple(int(value) for value in theme.continuation_rgb),
            stroke_width=1,
            stroke_fill=(255, 255, 255),
        )
        continuation_bbox_px = [float(value) for value in cue_bbox_px]

    scene_entities = tuple(
        {
            "entity_id": str(spec.card_id),
            "entity_type": "playing_card",
            "bbox_px": [float(value) for value in spec.bbox_px],
            "meta": {
                "rank_label": str(spec.rank_label),
                "rank_value": int(spec.rank_value),
                "suit_name": str(spec.suit_name),
                "is_reference": bool(spec.is_reference),
                "row_index": int(spec.row_index),
                "order_index": int(spec.order_index),
            },
        }
        for spec in card_specs
    )
    render_map = {
        "scene_variant": str(scene_variant),
        "style_variant": str(style_variant),
        "card_bboxes_px": {str(spec.card_id): [float(value) for value in spec.bbox_px] for spec in card_specs},
        "reference_card_ids": [str(spec.card_id) for spec in card_specs if bool(spec.is_reference)],
        "row_card_ids": [
            [str(spec.card_id) for spec in card_specs if int(spec.row_index) == int(row_index)]
            for row_index in range(len(row_groups))
        ],
        "continuation_cue_bbox_px": None if continuation_bbox_px is None else list(continuation_bbox_px),
    }
    return RenderedCardHandScene(
        image=image.convert("RGB"),
        card_specs=tuple(card_specs),
        scene_entities=scene_entities,
        render_map=render_map,
    )


__all__ = [
    "CardInstance",
    "CardRenderParams",
    "RenderedCardHandScene",
    "RenderedCardSpec",
    "SUIT_SYMBOLS",
    "render_cards_hand_scene",
]
