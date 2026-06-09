"""Shared nine-men's-morris board renderer for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from .text import draw_game_text_traced as draw_text_traced
from .layout import apply_games_layout_jitter_to_bbox
from .morris_common import NineMensMorrisBoardState, NineMensMorrisPieceInstance, POSITION_LAYOUT
from .scene_style import GamePanelSceneStyle, draw_panel_scene_chrome, game_panel_scene_style_metadata
from .style import NineMensMorrisTheme, build_games_nine_mens_morris_theme


@dataclass(frozen=True)
class NineMensMorrisRenderParams:
    """Resolved render controls for one nine-men's-morris scene."""

    canvas_width: int
    canvas_height: int
    board_width_px: int
    board_height_px: int
    board_corner_radius_px: int
    panel_margin_px: int
    title_font_size_px: int
    title_band_height_px: int
    board_padding_px: int
    piece_radius_px: int
    node_radius_px: int
    font_family: str = ""
    layout_jitter_meta: Dict[str, Any] | None = None


@dataclass(frozen=True)
class RenderedNineMensMorrisPieceSpec:
    """One rendered nine-men's-morris piece."""

    piece_id: str
    node_index: int
    node_label: str
    color: str
    bbox_px: Tuple[float, float, float, float]


@dataclass(frozen=True)
class RenderedNineMensMorrisScene:
    """Rendered nine-men's-morris scene plus trace-friendly metadata."""

    image: Image.Image
    piece_specs: Tuple[RenderedNineMensMorrisPieceSpec, ...]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


def _draw_shadow(
    image: Image.Image,
    *,
    bbox_px: Tuple[float, float, float, float],
    radius_px: int,
    theme: NineMensMorrisTheme,
) -> None:
    """Draw one soft panel shadow for the board."""

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


def _node_xy(
    *,
    node_index: int,
    board_left: float,
    board_top: float,
    board_size_px: float,
) -> Tuple[float, float]:
    """Return the pixel center for one Morris board node."""

    _, x_frac, y_frac = POSITION_LAYOUT[int(node_index)]
    return (
        round(float(board_left + (float(x_frac) * board_size_px)), 3),
        round(float(board_top + (float(y_frac) * board_size_px)), 3),
    )


def render_nine_mens_morris_scene(
    *,
    board_state: NineMensMorrisBoardState,
    background: Image.Image,
    scene_variant: str,
    style_variant: str,
    params: NineMensMorrisRenderParams,
    panel_style: GamePanelSceneStyle | None = None,
) -> RenderedNineMensMorrisScene:
    """Render one visible nine-men's-morris board."""

    if str(scene_variant) != "single_board":
        raise ValueError(f"unsupported nine-men's-morris scene_variant: {scene_variant}")

    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image)
    theme = build_games_nine_mens_morris_theme(style_variant=str(style_variant))
    title_font = load_font(int(params.title_font_size_px), bold=True, font_family=str(params.font_family))

    board_left = float((int(params.canvas_width) - int(params.board_width_px)) / 2)
    board_top = float((int(params.canvas_height) - int(params.board_height_px)) / 2)
    board_right = float(board_left + int(params.board_width_px))
    board_bottom = float(board_top + int(params.board_height_px))
    panel_bbox, _dx, _dy, layout_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=(board_left, board_top, board_right, board_bottom),
        canvas_width=int(params.canvas_width),
        canvas_height=int(params.canvas_height),
        jitter=params.layout_jitter_meta,
    )
    board_left, board_top, board_right, board_bottom = [float(value) for value in panel_bbox]

    if panel_style is not None:
        chrome_pad_x = max(14, int(round(float(params.panel_margin_px) * 0.34)))
        chrome_pad_y = max(14, int(round(float(params.panel_margin_px) * 0.28)))
        chrome_bbox = (
            max(4, int(round(board_left)) - chrome_pad_x),
            max(4, int(round(board_top)) - chrome_pad_y),
            min(int(params.canvas_width) - 4, int(round(board_right)) + chrome_pad_x),
            min(int(params.canvas_height) - 4, int(round(board_bottom)) + chrome_pad_y),
        )
        draw_panel_scene_chrome(
            draw,
            bbox=chrome_bbox,
            style=panel_style,
            radius=int(params.board_corner_radius_px) + 8,
            border_width=max(1, min(3, int(theme.board_border_width_px))),
        )

    _draw_shadow(
        image,
        bbox_px=panel_bbox,
        radius_px=int(params.board_corner_radius_px),
        theme=theme,
    )
    draw.rounded_rectangle(
        panel_bbox,
        radius=int(params.board_corner_radius_px),
        fill=tuple(int(value) for value in theme.board_fill_rgb),
        outline=tuple(int(value) for value in theme.board_border_rgb),
        width=int(theme.board_border_width_px),
    )

    title_text = "Nine Men's Morris"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font, stroke_width=1)
    title_width = float(title_bbox[2] - title_bbox[0])
    title_height = float(title_bbox[3] - title_bbox[1])
    title_x = float(board_left + ((int(params.board_width_px) - title_width) / 2.0))
    title_y = float(board_top + ((int(params.title_band_height_px) - title_height) / 2.0))
    draw_text_traced(draw,
        (title_x, title_y),
        title_text,
        font=title_font,
        fill=tuple(int(value) for value in theme.title_rgb),
        stroke_width=1,
        stroke_fill=resolve_text_stroke_fill(tuple(int(value) for value in theme.title_rgb)),
     role="readout", required=False,)

    inner_left = float(board_left + int(params.board_padding_px))
    inner_top = float(board_top + int(params.title_band_height_px) + int(params.board_padding_px))
    inner_right = float(board_right - int(params.board_padding_px))
    inner_bottom = float(board_bottom - int(params.board_padding_px))
    board_size_px = float(min(inner_right - inner_left, inner_bottom - inner_top))
    board_left_px = float(inner_left + ((inner_right - inner_left - board_size_px) / 2.0))
    board_top_px = float(inner_top + ((inner_bottom - inner_top - board_size_px) / 2.0))

    def p(node_index: int) -> Tuple[float, float]:
        return _node_xy(node_index=int(node_index), board_left=board_left_px, board_top=board_top_px, board_size_px=board_size_px)

    line_rgb = tuple(int(value) for value in theme.line_rgb)
    line_width = int(theme.line_width_px)

    draw.rectangle([p(0), p(23)], outline=line_rgb, width=line_width)
    draw.rectangle([p(3), p(20)], outline=line_rgb, width=line_width)
    draw.rectangle([p(6), p(17)], outline=line_rgb, width=line_width)
    draw.line([p(1), p(7)], fill=line_rgb, width=line_width)
    draw.line([p(16), p(22)], fill=line_rgb, width=line_width)
    draw.line([p(9), p(11)], fill=line_rgb, width=line_width)
    draw.line([p(12), p(14)], fill=line_rgb, width=line_width)

    node_centers_px: Dict[str, List[float]] = {}
    for node_index, (node_label, _, _) in enumerate(POSITION_LAYOUT):
        cx, cy = p(node_index)
        node_centers_px[str(node_label)] = [float(cx), float(cy)]
        radius = float(params.node_radius_px)
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=tuple(int(value) for value in theme.node_rgb),
        )

    piece_specs: List[RenderedNineMensMorrisPieceSpec] = []
    piece_bboxes_px: Dict[str, List[float]] = {}
    piece_centers_px: Dict[str, List[float]] = {}
    scene_entities: List[Dict[str, Any]] = []
    for piece in board_state.piece_specs:
        cx, cy = p(int(piece.node_index))
        radius = float(params.piece_radius_px)
        bbox = (
            round(float(cx - radius), 3),
            round(float(cy - radius), 3),
            round(float(cx + radius), 3),
            round(float(cy + radius), 3),
        )
        if str(piece.color) == "white":
            fill_rgb = tuple(int(value) for value in theme.white_piece_fill_rgb)
            outline_rgb = tuple(int(value) for value in theme.white_piece_outline_rgb)
        else:
            fill_rgb = tuple(int(value) for value in theme.black_piece_fill_rgb)
            outline_rgb = tuple(int(value) for value in theme.black_piece_outline_rgb)
        draw.ellipse(bbox, fill=fill_rgb, outline=outline_rgb, width=3)
        piece_specs.append(
            RenderedNineMensMorrisPieceSpec(
                piece_id=str(piece.piece_id),
                node_index=int(piece.node_index),
                node_label=str(piece.node_label),
                color=str(piece.color),
                bbox_px=bbox,
            )
        )
        piece_bboxes_px[str(piece.piece_id)] = [float(value) for value in bbox]
        piece_centers_px[str(piece.piece_id)] = [round(float(cx), 3), round(float(cy), 3)]
        scene_entities.append(
            {
                "entity_id": str(piece.piece_id),
                "kind": "nine_mens_morris_piece",
                "bbox": [float(value) for value in bbox],
                "point": list(piece_centers_px[str(piece.piece_id)]),
                "node_index": int(piece.node_index),
                "node_label": str(piece.node_label),
                "color": str(piece.color),
            }
        )

    return RenderedNineMensMorrisScene(
        image=image.convert("RGB"),
        piece_specs=tuple(piece_specs),
        scene_entities=tuple(scene_entities),
        render_map={
            "board_bbox_px": [float(value) for value in panel_bbox],
            "piece_bboxes_px": piece_bboxes_px,
            "piece_centers_px": piece_centers_px,
            "node_centers_px": node_centers_px,
            "layout_jitter": dict(layout_jitter),
            "style_variant": str(style_variant),
            "font_family": str(params.font_family),
            "text_style": {
                "font_family": str(params.font_family),
            },
            "panel_scene_style": None if panel_style is None else game_panel_scene_style_metadata(panel_style),
        },
    )


__all__ = [
    "NineMensMorrisRenderParams",
    "RenderedNineMensMorrisPieceSpec",
    "RenderedNineMensMorrisScene",
    "render_nine_mens_morris_scene",
]
