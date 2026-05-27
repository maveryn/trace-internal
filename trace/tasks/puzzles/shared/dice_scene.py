"""Shared dice-tray renderer for puzzle probability tasks."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.bbox_projection import round_bbox as _round_bbox
from ...shared.color_distance import normalize_rgb as _rgb
from ...shared.drawing import draw_centered_text, draw_rounded_rect
from ...shared.text_rendering import load_font
from .scene_style import PuzzleSceneStyle


SUPPORTED_DICE_SCENE_VARIANTS: Tuple[str, ...] = (
    "dice_tray_clean",
    "dice_tray_felt",
    "dice_tray_notebook",
)


@dataclass(frozen=True)
class DiceRenderParams:
    """Pixel geometry and style controls for dice probability scenes."""

    canvas_width: int = 1100
    canvas_height: int = 780
    single_tray_bbox_px: Tuple[int, int, int, int] = (145, 112, 955, 650)
    pair_left_tray_bbox_px: Tuple[int, int, int, int] = (68, 142, 522, 628)
    pair_right_tray_bbox_px: Tuple[int, int, int, int] = (578, 142, 1032, 628)
    die_size_px: int = 72
    die_gap_px: int = 18
    tray_corner_radius_px: int = 24
    tray_outline_width_px: int = 3
    die_corner_radius_px: int = 14
    die_outline_width_px: int = 3
    pip_radius_px: int = 6
    title_font_size_px: int = 28


@dataclass(frozen=True)
class RenderedDiceScene:
    """Rendered dice scene plus traceable geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    item_bbox_map: Dict[str, List[float]]
    die_bbox_map: Dict[str, List[float]]
    tray_bbox_map: Dict[str, List[float]]
    scene_bbox_px: List[float]


def _luminance(rgb: Sequence[int]) -> float:
    red, green, blue = _rgb(rgb)
    return 0.2126 * float(red) + 0.7152 * float(green) + 0.0722 * float(blue)


def _pip_centers(bbox: Sequence[float], value: int) -> List[Tuple[float, float]]:
    x0, y0, x1, y1 = [float(v) for v in bbox]
    width = float(x1 - x0)
    height = float(y1 - y0)
    left = float(x0 + 0.30 * width)
    mid_x = float(x0 + 0.50 * width)
    right = float(x0 + 0.70 * width)
    top = float(y0 + 0.30 * height)
    mid_y = float(y0 + 0.50 * height)
    bottom = float(y0 + 0.70 * height)
    value = int(value)
    if value == 1:
        return [(mid_x, mid_y)]
    if value == 2:
        return [(left, top), (right, bottom)]
    if value == 3:
        return [(left, top), (mid_x, mid_y), (right, bottom)]
    if value == 4:
        return [(left, top), (right, top), (left, bottom), (right, bottom)]
    if value == 5:
        return [(left, top), (right, top), (mid_x, mid_y), (left, bottom), (right, bottom)]
    return [(left, top), (right, top), (left, mid_y), (right, mid_y), (left, bottom), (right, bottom)]


def _draw_die(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int],
    value: int,
    params: DiceRenderParams,
) -> None:
    x0, y0, x1, y1 = [float(v) for v in bbox]
    shadow = (38, 42, 50, 62)
    draw_rounded_rect(
        draw,
        (x0 + 4.0, y0 + 5.0, x1 + 4.0, y1 + 5.0),
        radius=int(params.die_corner_radius_px),
        fill=shadow,
        outline=shadow,
        width=1,
    )
    draw_rounded_rect(
        draw,
        (x0, y0, x1, y1),
        radius=int(params.die_corner_radius_px),
        fill=fill,
        outline=outline,
        width=int(params.die_outline_width_px),
    )
    highlight = tuple(min(255, int(channel) + 34) for channel in fill)
    draw.arc(
        [x0 + 8.0, y0 + 8.0, x1 - 8.0, y1 - 8.0],
        start=202,
        end=276,
        fill=highlight,
        width=2,
    )
    pip_fill = (255, 255, 255) if _luminance(fill) < 145.0 else (24, 28, 36)
    pip_outline = (24, 28, 36) if _luminance(fill) < 145.0 else (255, 255, 255)
    radius = float(params.pip_radius_px)
    for cx, cy in _pip_centers((x0, y0, x1, y1), int(value)):
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=pip_fill,
            outline=pip_outline,
            width=1,
        )


def _layout_dice(*, count: int, tray_bbox: Sequence[float], params: DiceRenderParams) -> List[List[float]]:
    x0, y0, x1, y1 = [float(v) for v in tray_bbox]
    title_pad = 66.0
    inner_pad = 32.0
    usable_x0 = float(x0 + inner_pad)
    usable_y0 = float(y0 + title_pad)
    usable_x1 = float(x1 - inner_pad)
    usable_y1 = float(y1 - inner_pad)
    die = float(params.die_size_px)
    gap = float(params.die_gap_px)
    count = max(1, int(count))
    max_cols = max(1, int((usable_x1 - usable_x0 + gap) // (die + gap)))
    cols = max(2, int(math.ceil(math.sqrt(float(count)))))
    cols = min(max_cols, max(1, cols))
    while int(math.ceil(float(count) / float(cols))) * (die + gap) - gap > (usable_y1 - usable_y0) and cols < max_cols:
        cols += 1
    rows = int(math.ceil(float(count) / float(cols)))
    block_w = float(cols * die + max(0, cols - 1) * gap)
    block_h = float(rows * die + max(0, rows - 1) * gap)
    start_x = float(usable_x0 + 0.5 * ((usable_x1 - usable_x0) - block_w))
    start_y = float(usable_y0 + 0.5 * ((usable_y1 - usable_y0) - block_h))
    bboxes: List[List[float]] = []
    for index in range(count):
        row = int(index // cols)
        col = int(index % cols)
        dx0 = float(start_x + col * (die + gap))
        dy0 = float(start_y + row * (die + gap))
        bboxes.append(_round_bbox([dx0, dy0, dx0 + die, dy0 + die]))
    return bboxes


def _style_for_variant(scene_variant: str, scene_style: PuzzleSceneStyle | None = None) -> Dict[str, Tuple[int, int, int]]:
    base = {
        "tray_fill": (250, 251, 249),
        "tray_outline": (67, 75, 88),
        "title": (29, 34, 43),
        "title_stroke": (255, 255, 255),
        "die_outline": (28, 34, 44),
        "notebook_grid": (232, 225, 211),
    }
    if str(scene_variant) == "dice_tray_felt":
        base.update(
            {
                "tray_fill": (227, 242, 233),
                "tray_outline": (48, 105, 82),
                "title": (22, 63, 50),
            }
        )
    elif str(scene_variant) == "dice_tray_notebook":
        base.update(
            {
                "tray_fill": (252, 249, 240),
                "tray_outline": (117, 91, 67),
                "title": (83, 65, 51),
            }
        )
    if scene_style is not None:
        base.update(
            {
                "tray_fill": tuple(int(value) for value in scene_style.panel_fill_rgb),
                "tray_outline": tuple(int(value) for value in scene_style.panel_border_rgb),
                "title": tuple(int(value) for value in scene_style.text_rgb),
                "title_stroke": tuple(int(value) for value in scene_style.text_stroke_rgb),
                "die_outline": tuple(int(value) for value in scene_style.grid_rgb),
                "notebook_grid": tuple(int(value) for value in scene_style.notebook_line_rgb),
            }
        )
    return base


def _draw_tray(
    draw: ImageDraw.ImageDraw,
    *,
    tray: Mapping[str, Any],
    tray_bbox: Sequence[float],
    params: DiceRenderParams,
    style: Mapping[str, Tuple[int, int, int]],
    entities: List[Dict[str, Any]],
    item_bbox_map: Dict[str, List[float]],
    die_bbox_map: Dict[str, List[float]],
    tray_bbox_map: Dict[str, List[float]],
) -> None:
    tray_id = str(tray["tray_id"])
    title = str(tray.get("title", "Dice tray"))
    tray_bbox_rounded = _round_bbox(tray_bbox)
    tray_bbox_map[tray_id] = list(tray_bbox_rounded)
    item_bbox_map[tray_id] = list(tray_bbox_rounded)
    draw_rounded_rect(
        draw,
        tuple(tray_bbox_rounded),
        radius=int(params.tray_corner_radius_px),
        fill=style["tray_fill"],
        outline=style["tray_outline"],
        width=int(params.tray_outline_width_px),
    )
    title_font = load_font(int(params.title_font_size_px), bold=True)
    draw_centered_text(
        draw,
        text=title,
        center=(0.5 * (float(tray_bbox_rounded[0]) + float(tray_bbox_rounded[2])), float(tray_bbox_rounded[1]) + 34.0),
        font=title_font,
        fill=style["title"],
        stroke_fill=style["title_stroke"],
        stroke_width=1,
    )
    dice = [dict(die) for die in tray.get("dice", [])]
    for die, bbox in zip(dice, _layout_dice(count=len(dice), tray_bbox=tray_bbox_rounded, params=params)):
        die_id = str(die["die_id"])
        fill = _rgb(die.get("color_rgb", (230, 230, 230)))
        _draw_die(
            draw,
            bbox=bbox,
            fill=fill,
            outline=style["die_outline"],
            value=int(die["value"]),
            params=params,
        )
        die_bbox_map[die_id] = list(bbox)
        item_bbox_map[die_id] = list(bbox)
        entities.append(
            {
                "entity_id": die_id,
                "entity_type": "probability_die",
                "tray_id": tray_id,
                "die_index": int(die.get("die_index", 0)),
                "value": int(die["value"]),
                "color_name": str(die["color_name"]),
                "bbox_px": list(bbox),
            }
        )
    entities.append(
        {
            "entity_id": tray_id,
            "entity_type": "dice_tray",
            "tray_id": tray_id,
            "bbox_px": list(tray_bbox_rounded),
        }
    )


def render_dice_probability_scene(
    image: Image.Image,
    *,
    scene_variant: str,
    mode: str,
    tray_specs: Sequence[Mapping[str, Any]],
    render_params: DiceRenderParams,
    scene_style: PuzzleSceneStyle | None = None,
) -> RenderedDiceScene:
    """Render one single-, pair-, or conditional-dice probability panel."""

    if str(scene_variant) not in SUPPORTED_DICE_SCENE_VARIANTS:
        raise ValueError(f"unsupported dice scene variant: {scene_variant}")
    if str(mode) not in {"single", "pair", "conditional"}:
        raise ValueError(f"unsupported dice probability mode: {mode}")

    draw = ImageDraw.Draw(image, "RGBA")
    style = _style_for_variant(str(scene_variant), scene_style=scene_style)
    if str(scene_variant) == "dice_tray_notebook":
        grid_color = tuple(int(value) for value in style["notebook_grid"]) + (140,)
        for x in range(34, int(render_params.canvas_width), 34):
            draw.line([(x, 0), (x, int(render_params.canvas_height))], fill=grid_color, width=1)
        for y in range(34, int(render_params.canvas_height), 34):
            draw.line([(0, y), (int(render_params.canvas_width), y)], fill=grid_color, width=1)

    entities: List[Dict[str, Any]] = []
    item_bbox_map: Dict[str, List[float]] = {}
    die_bbox_map: Dict[str, List[float]] = {}
    tray_bbox_map: Dict[str, List[float]] = {}

    if str(mode) in {"single", "conditional"}:
        if len(tray_specs) != 1:
            raise ValueError("single or conditional dice scene requires exactly one tray spec")
        _draw_tray(
            draw,
            tray=tray_specs[0],
            tray_bbox=render_params.single_tray_bbox_px,
            params=render_params,
            style=style,
            entities=entities,
            item_bbox_map=item_bbox_map,
            die_bbox_map=die_bbox_map,
            tray_bbox_map=tray_bbox_map,
        )
    else:
        if len(tray_specs) != 2:
            raise ValueError("pair dice scene requires exactly two tray specs")
        for tray, bbox in zip(tray_specs, [render_params.pair_left_tray_bbox_px, render_params.pair_right_tray_bbox_px]):
            _draw_tray(
                draw,
                tray=tray,
                tray_bbox=bbox,
                params=render_params,
                style=style,
                entities=entities,
                item_bbox_map=item_bbox_map,
                die_bbox_map=die_bbox_map,
                tray_bbox_map=tray_bbox_map,
            )

    bboxes = list(tray_bbox_map.values())
    scene_bbox = _round_bbox(
        [
            min(bbox[0] for bbox in bboxes),
            min(bbox[1] for bbox in bboxes),
            max(bbox[2] for bbox in bboxes),
            max(bbox[3] for bbox in bboxes),
        ]
    )
    return RenderedDiceScene(
        image=image,
        entities=entities,
        item_bbox_map=item_bbox_map,
        die_bbox_map=die_bbox_map,
        tray_bbox_map=tray_bbox_map,
        scene_bbox_px=list(scene_bbox),
    )


__all__ = [
    "DiceRenderParams",
    "RenderedDiceScene",
    "SUPPORTED_DICE_SCENE_VARIANTS",
    "render_dice_probability_scene",
]
