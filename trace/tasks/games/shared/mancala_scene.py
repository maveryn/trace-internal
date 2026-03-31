"""Shared Mancala board renderer for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from .mancala_common import MancalaState, pit_entity_id, player_name, store_entity_id
from .style import MancalaTheme, build_games_mancala_theme


@dataclass(frozen=True)
class MancalaRenderParams:
    """Resolved render controls for one Mancala scene."""

    canvas_width: int
    canvas_height: int
    panel_margin_px: int
    player_badge_height_px: int
    player_badge_width_px: int
    header_gap_px: int
    board_width_px: int
    board_height_px: int
    board_corner_radius_px: int
    board_frame_width_px: int
    pit_gap_px: int
    store_width_px: int
    pit_corner_radius_px: int
    count_font_size_px: int
    side_label_font_size_px: int
    player_badge_font_size_px: int


@dataclass(frozen=True)
class RenderedMancalaScene:
    """Rendered Mancala scene plus trace-friendly metadata."""

    image: Image.Image
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


def render_mancala_scene(
    *,
    state: MancalaState,
    background: Image.Image,
    scene_variant: str,
    style_variant: str,
    current_player_name: str,
    params: MancalaRenderParams,
) -> RenderedMancalaScene:
    """Render one visible Mancala board state."""

    del scene_variant
    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image)
    theme = build_games_mancala_theme(style_variant=str(style_variant))

    board_left = int(0.5 * (int(params.canvas_width) - int(params.board_width_px)))
    available_height = int(params.canvas_height) - (2 * int(params.panel_margin_px)) - int(params.player_badge_height_px) - int(params.header_gap_px)
    board_top = int(
        params.panel_margin_px
        + params.player_badge_height_px
        + params.header_gap_px
        + max(0, 0.5 * (available_height - int(params.board_height_px)))
    )
    board_bbox = (
        round(float(board_left), 3),
        round(float(board_top), 3),
        round(float(board_left + params.board_width_px), 3),
        round(float(board_top + params.board_height_px), 3),
    )
    draw.rounded_rectangle(
        board_bbox,
        radius=int(params.board_corner_radius_px),
        fill=tuple(int(value) for value in theme.board_frame_rgb),
    )
    inner_inset = float(params.board_frame_width_px)
    inner_bbox = (
        round(float(board_bbox[0] + inner_inset), 3),
        round(float(board_bbox[1] + inner_inset), 3),
        round(float(board_bbox[2] - inner_inset), 3),
        round(float(board_bbox[3] - inner_inset), 3),
    )
    draw.rounded_rectangle(
        inner_bbox,
        radius=max(8, int(params.board_corner_radius_px) - int(params.board_frame_width_px)),
        fill=tuple(int(value) for value in theme.board_fill_rgb),
    )

    badge_font = load_font(int(params.player_badge_font_size_px), bold=True)
    badge_text = f"{str(current_player_name)} to move"
    badge_text_bbox = draw.textbbox((0, 0), badge_text, font=badge_font, stroke_width=1)
    badge_width = max(
        int(params.player_badge_width_px),
        int((badge_text_bbox[2] - badge_text_bbox[0]) + 32),
    )
    badge_left = int(0.5 * (int(params.canvas_width) - int(badge_width)))
    badge_top = int(params.panel_margin_px)
    badge_bbox = (
        round(float(badge_left), 3),
        round(float(badge_top), 3),
        round(float(badge_left + badge_width), 3),
        round(float(badge_top + params.player_badge_height_px), 3),
    )
    draw.rounded_rectangle(
        badge_bbox,
        radius=int(0.5 * int(params.player_badge_height_px)),
        fill=tuple(int(value) for value in theme.badge_fill_rgb),
        outline=tuple(int(value) for value in theme.badge_outline_rgb),
        width=2,
    )
    badge_text_rgb = tuple(int(value) for value in theme.badge_text_rgb)
    draw.text(
        (
            float(badge_left + 16),
            float(badge_top + 0.5 * (int(params.player_badge_height_px) - (badge_text_bbox[3] - badge_text_bbox[1]))),
        ),
        badge_text,
        font=badge_font,
        fill=badge_text_rgb,
        stroke_width=1,
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(badge_text_rgb)),
    )

    left_store_bbox = (
        round(float(board_left + 28), 3),
        round(float(board_top + 48), 3),
        round(float(board_left + 28 + params.store_width_px), 3),
        round(float(board_top + params.board_height_px - 48), 3),
    )
    right_store_bbox = (
        round(float(board_left + params.board_width_px - 28 - params.store_width_px), 3),
        round(float(board_top + 48), 3),
        round(float(board_left + params.board_width_px - 28), 3),
        round(float(board_top + params.board_height_px - 48), 3),
    )
    pit_area_left = float(left_store_bbox[2] + 28)
    pit_area_right = float(right_store_bbox[0] - 28)
    pit_width = float((pit_area_right - pit_area_left - (5 * int(params.pit_gap_px))) / 6.0)
    pit_height = float((int(params.board_height_px) - 120 - int(params.pit_gap_px)) / 2.0)
    top_row_y = float(board_top + 36)
    bottom_row_y = float(top_row_y + pit_height + int(params.pit_gap_px))

    count_font = load_font(int(params.count_font_size_px), bold=True)
    side_label_font = load_font(int(params.side_label_font_size_px), bold=True)
    count_text_rgb = tuple(int(value) for value in theme.count_text_rgb)

    def _draw_bowl(bbox: Tuple[float, float, float, float], *, fill_rgb: Tuple[int, int, int], outline_rgb: Tuple[int, int, int]) -> None:
        draw.rounded_rectangle(
            bbox,
            radius=int(params.pit_corner_radius_px),
            fill=tuple(int(value) for value in fill_rgb),
            outline=tuple(int(value) for value in outline_rgb),
            width=int(theme.pit_outline_width_px),
        )

    scene_entities: List[Dict[str, Any]] = []
    pit_bboxes_px: Dict[str, List[float]] = {}
    store_bboxes_px: Dict[str, List[float]] = {}

    _draw_bowl(left_store_bbox, fill_rgb=theme.store_fill_rgb, outline_rgb=theme.store_outline_rgb)
    _draw_bowl(right_store_bbox, fill_rgb=theme.store_fill_rgb, outline_rgb=theme.store_outline_rgb)

    for side_name, bbox, count in (
        ("top", left_store_bbox, int(state.top_store)),
        ("bottom", right_store_bbox, int(state.bottom_store)),
    ):
        entity_id = store_entity_id(side=str(side_name))
        store_bboxes_px[str(entity_id)] = list(bbox)
        count_text = str(int(count))
        text_bbox = draw.textbbox((0, 0), count_text, font=count_font, stroke_width=1)
        draw.text(
            (
                float(0.5 * (bbox[0] + bbox[2] - (text_bbox[2] - text_bbox[0]))),
                float(0.5 * (bbox[1] + bbox[3] - (text_bbox[3] - text_bbox[1]))),
            ),
            count_text,
            font=count_font,
            fill=count_text_rgb,
            stroke_width=1,
            stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(count_text_rgb)),
        )
        scene_entities.append(
            {
                "id": str(entity_id),
                "kind": "store",
                "side": str(side_name),
                "count": int(count),
                "bbox_px": list(bbox),
            }
        )

    top_label = f"{player_name(-1)} side"
    bottom_label = f"{player_name(1)} side"
    top_label_bbox = draw.textbbox((0, 0), top_label, font=side_label_font, stroke_width=1)
    bottom_label_bbox = draw.textbbox((0, 0), bottom_label, font=side_label_font, stroke_width=1)
    draw.text(
        (
            float(board_left + 0.5 * params.board_width_px - 0.5 * (top_label_bbox[2] - top_label_bbox[0])),
            float(top_row_y - 26),
        ),
        top_label,
        font=side_label_font,
        fill=tuple(int(value) for value in theme.top_side_text_rgb),
        stroke_width=1,
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(tuple(int(value) for value in theme.top_side_text_rgb))),
    )
    draw.text(
        (
            float(board_left + 0.5 * params.board_width_px - 0.5 * (bottom_label_bbox[2] - bottom_label_bbox[0])),
            float(bottom_row_y + pit_height + 8),
        ),
        bottom_label,
        font=side_label_font,
        fill=tuple(int(value) for value in theme.bottom_side_text_rgb),
        stroke_width=1,
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(tuple(int(value) for value in theme.bottom_side_text_rgb))),
    )

    for index in range(6):
        left = float(pit_area_left + index * (pit_width + int(params.pit_gap_px)))
        top_bbox = (
            round(left, 3),
            round(float(top_row_y), 3),
            round(float(left + pit_width), 3),
            round(float(top_row_y + pit_height), 3),
        )
        bottom_bbox = (
            round(left, 3),
            round(float(bottom_row_y), 3),
            round(float(left + pit_width), 3),
            round(float(bottom_row_y + pit_height), 3),
        )
        _draw_bowl(top_bbox, fill_rgb=theme.pit_fill_rgb, outline_rgb=theme.pit_outline_rgb)
        _draw_bowl(bottom_bbox, fill_rgb=theme.pit_fill_rgb, outline_rgb=theme.pit_outline_rgb)
        for side_name, count, bbox in (
            ("top", int(state.top_pits[index]), top_bbox),
            ("bottom", int(state.bottom_pits[index]), bottom_bbox),
        ):
            entity_id = pit_entity_id(side=str(side_name), index=int(index))
            pit_bboxes_px[str(entity_id)] = list(bbox)
            count_text = str(int(count))
            text_bbox = draw.textbbox((0, 0), count_text, font=count_font, stroke_width=1)
            draw.text(
                (
                    float(0.5 * (bbox[0] + bbox[2] - (text_bbox[2] - text_bbox[0]))),
                    float(0.5 * (bbox[1] + bbox[3] - (text_bbox[3] - text_bbox[1]))),
                ),
                count_text,
                font=count_font,
                fill=count_text_rgb,
                stroke_width=1,
                stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(count_text_rgb)),
            )
            scene_entities.append(
                {
                    "id": str(entity_id),
                    "kind": "pit",
                    "side": str(side_name),
                    "pit_index": int(index),
                    "count": int(count),
                    "bbox_px": list(bbox),
                }
            )

    render_map = {
        "board_bbox_px": list(board_bbox),
        "pit_bboxes_px": pit_bboxes_px,
        "store_bboxes_px": store_bboxes_px,
        "player_badge_bbox_px": list(badge_bbox),
    }
    return RenderedMancalaScene(
        image=image,
        scene_entities=tuple(scene_entities),
        render_map=render_map,
    )


__all__ = [
    "MancalaRenderParams",
    "RenderedMancalaScene",
    "render_mancala_scene",
]
