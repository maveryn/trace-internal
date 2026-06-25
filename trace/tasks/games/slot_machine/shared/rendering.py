"""Rendering helpers for slot-machine games tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw, ImageFont

from trace.tasks.games.shared.scene_style import (
    game_panel_scene_style_metadata,
    make_panel_scene_background,
    resolve_game_panel_scene_style,
)
from trace.tasks.games.shared.text import draw_centered_game_text
from trace.tasks.shared.config_defaults import group_default
from trace.core.visual.noise import apply_post_image_noise

from .defaults import DEFAULTS, PAYLINE_IDS, POST_IMAGE_NOISE_DEFAULTS, REEL_COUNT, ROW_COUNT, SCENE_NAMESPACE
from .state import PAYLINE_CELLS_BY_ID, SlotMachineScene, cell_grid, payline_entity_id, slot_cell_id, validate_slot_machine_scene


@dataclass(frozen=True)
class SlotMachineRenderParams:
    """Resolved slot-machine render dimensions."""

    canvas_width: int
    canvas_height: int
    cabinet_width_px: int
    cabinet_height_px: int
    reel_cell_width_px: int
    reel_cell_height_px: int
    reel_gap_px: int
    row_gap_px: int
    cabinet_pad_px: int
    label_font_size_px: int
    symbol_font_size_px: int


@dataclass(frozen=True)
class RenderedSlotMachineScene:
    """Rendered slot-machine image plus projection data."""

    image: Image.Image
    render_map: dict[str, Any]
    scene_entities: tuple[dict[str, Any], ...]
    panel_style_meta: dict[str, Any]
    background_meta: dict[str, Any]
    post_noise_meta: dict[str, Any]


def resolve_slot_machine_render_params(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> SlotMachineRenderParams:
    """Resolve pixel dimensions from params, config defaults, and fallbacks."""

    return SlotMachineRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(render_defaults, "canvas_width", DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(render_defaults, "canvas_height", DEFAULTS.canvas_height))),
        cabinet_width_px=int(params.get("cabinet_width_px", group_default(render_defaults, "cabinet_width_px", DEFAULTS.cabinet_width_px))),
        cabinet_height_px=int(params.get("cabinet_height_px", group_default(render_defaults, "cabinet_height_px", DEFAULTS.cabinet_height_px))),
        reel_cell_width_px=int(params.get("reel_cell_width_px", group_default(render_defaults, "reel_cell_width_px", DEFAULTS.reel_cell_width_px))),
        reel_cell_height_px=int(params.get("reel_cell_height_px", group_default(render_defaults, "reel_cell_height_px", DEFAULTS.reel_cell_height_px))),
        reel_gap_px=int(params.get("reel_gap_px", group_default(render_defaults, "reel_gap_px", DEFAULTS.reel_gap_px))),
        row_gap_px=int(params.get("row_gap_px", group_default(render_defaults, "row_gap_px", DEFAULTS.row_gap_px))),
        cabinet_pad_px=int(params.get("cabinet_pad_px", group_default(render_defaults, "cabinet_pad_px", DEFAULTS.cabinet_pad_px))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(render_defaults, "label_font_size_px", DEFAULTS.label_font_size_px))),
        symbol_font_size_px=int(params.get("symbol_font_size_px", group_default(render_defaults, "symbol_font_size_px", DEFAULTS.symbol_font_size_px))),
    )


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    try:
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        return ImageFont.truetype(name, int(size))
    except OSError:
        return ImageFont.load_default()


def _style_colors(style_variant: str) -> dict[str, tuple[int, int, int]]:
    """Return slot-cabinet colors for one visual style variant."""

    palettes = {
        "classic_red": {
            "cabinet": (154, 37, 45),
            "cabinet_dark": (87, 22, 31),
            "trim": (247, 198, 69),
            "reel": (250, 246, 231),
            "payline": (230, 42, 58),
        },
        "chrome_blue": {
            "cabinet": (59, 92, 137),
            "cabinet_dark": (28, 43, 68),
            "trim": (205, 214, 224),
            "reel": (239, 245, 249),
            "payline": (224, 61, 77),
        },
        "neon_night": {
            "cabinet": (38, 31, 76),
            "cabinet_dark": (15, 13, 34),
            "trim": (61, 218, 209),
            "reel": (232, 236, 244),
            "payline": (255, 72, 133),
        },
        "candy_arcade": {
            "cabinet": (205, 83, 132),
            "cabinet_dark": (116, 45, 83),
            "trim": (255, 215, 108),
            "reel": (255, 248, 238),
            "payline": (61, 131, 214),
        },
        "paper_ticket": {
            "cabinet": (118, 97, 78),
            "cabinet_dark": (73, 58, 46),
            "trim": (226, 188, 116),
            "reel": (251, 244, 224),
            "payline": (179, 47, 58),
        },
    }
    return palettes.get(str(style_variant), palettes["classic_red"])


def _draw_symbol(draw: ImageDraw.ImageDraw, bbox: Sequence[float], symbol_key: str, *, colors: Mapping[str, tuple[int, int, int]]) -> None:
    """Draw one simple slot symbol inside a reel cell."""

    x0, y0, x1, y1 = [float(value) for value in bbox]
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    size = min(x1 - x0, y1 - y0) * 0.56
    key = str(symbol_key)
    outline = (42, 42, 48)
    if key == "seven":
        font = _font(int(size * 0.82), bold=True)
        draw_centered_game_text(
            draw,
            text="7",
            center=(cx, cy - size * 0.03),
            font=font,
            fill=(204, 34, 45),
            stroke_fill=(255, 245, 210),
            surface_rgbs=(colors["reel"],),
            role="game_symbol",
            required=True,
            stroke_width=1,
        )
    elif key == "bar":
        rect = [cx - size * 0.48, cy - size * 0.22, cx + size * 0.48, cy + size * 0.22]
        draw.rounded_rectangle(rect, radius=int(size * 0.08), fill=(32, 36, 42), outline=(228, 193, 72), width=3)
        draw_centered_game_text(
            draw,
            text="BAR",
            center=(cx, cy),
            font=_font(int(size * 0.28), bold=True),
            fill=(248, 236, 180),
            stroke_fill=(32, 36, 42),
            surface_rgbs=((32, 36, 42),),
            role="game_symbol",
            required=True,
        )
    elif key == "gem":
        points = [(cx, cy - size * 0.45), (cx + size * 0.45, cy), (cx, cy + size * 0.45), (cx - size * 0.45, cy)]
        draw.polygon(points, fill=(50, 145, 214), outline=outline)
    elif key == "star":
        r1 = size * 0.45
        r2 = size * 0.20
        pts = []
        import math

        for index in range(10):
            angle = -math.pi / 2.0 + index * math.pi / 5.0
            radius = r1 if index % 2 == 0 else r2
            pts.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
        draw.polygon(pts, fill=(245, 181, 46), outline=outline)
    elif key == "bell":
        draw.ellipse([cx - size * 0.28, cy - size * 0.50, cx + size * 0.28, cy - size * 0.08], fill=(240, 196, 66), outline=outline, width=2)
        draw.rounded_rectangle([cx - size * 0.38, cy - size * 0.18, cx + size * 0.38, cy + size * 0.32], radius=int(size * 0.18), fill=(237, 178, 54), outline=outline, width=2)
        draw.ellipse([cx - size * 0.10, cy + size * 0.28, cx + size * 0.10, cy + size * 0.48], fill=(95, 57, 31), outline=outline)
    else:
        draw.ellipse([cx - size * 0.42, cy - size * 0.42, cx + size * 0.42, cy + size * 0.42], fill=(236, 149, 48), outline=outline, width=3)
        draw.ellipse([cx - size * 0.22, cy - size * 0.22, cx + size * 0.22, cy + size * 0.22], fill=(255, 210, 88), outline=(166, 89, 26), width=2)


def render_slot_machine_scene(
    *,
    scene: SlotMachineScene,
    render_params: SlotMachineRenderParams,
    instance_seed: int,
) -> RenderedSlotMachineScene:
    """Render a front-view slot machine and record conceptual payline projections."""

    validate_slot_machine_scene(scene)
    panel_style, panel_style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.panel_style",
        treatments=("bare_canvas", "plain_sheet", "soft_panel", "game_table", "arcade_screen"),
    )
    image, background_meta = make_panel_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=panel_style,
    )
    draw = ImageDraw.Draw(image)
    colors = _style_colors(str(scene.style_variant))
    cabinet_w = float(render_params.cabinet_width_px)
    cabinet_h = float(render_params.cabinet_height_px)
    left = (float(render_params.canvas_width) - cabinet_w) / 2.0
    top = (float(render_params.canvas_height) - cabinet_h) / 2.0
    right = left + cabinet_w
    bottom = top + cabinet_h

    draw.rounded_rectangle([left, top, right, bottom], radius=34, fill=colors["cabinet_dark"], outline=colors["trim"], width=6)
    inset = 18
    draw.rounded_rectangle([left + inset, top + inset, right - inset, bottom - inset], radius=24, fill=colors["cabinet"], outline=colors["trim"], width=3)
    title_h = 76
    draw.rounded_rectangle([left + 44, top + 24, right - 44, top + title_h], radius=18, fill=colors["trim"], outline=colors["cabinet_dark"], width=3)
    draw_centered_game_text(
        draw,
        text="SLOTS",
        center=((left + right) / 2.0, top + title_h / 2.0 + 12),
        font=_font(int(render_params.label_font_size_px) + 8, bold=True),
        fill=colors["cabinet_dark"],
        stroke_fill=colors["trim"],
        surface_rgbs=(colors["trim"],),
        role="readout",
        required=True,
    )

    grid_w = REEL_COUNT * render_params.reel_cell_width_px + (REEL_COUNT - 1) * render_params.reel_gap_px
    grid_h = ROW_COUNT * render_params.reel_cell_height_px + (ROW_COUNT - 1) * render_params.row_gap_px
    grid_left = left + (cabinet_w - grid_w) / 2.0
    grid_top = top + 116
    window_bbox = [grid_left - 18, grid_top - 18, grid_left + grid_w + 18, grid_top + grid_h + 18]
    draw.rounded_rectangle(window_bbox, radius=22, fill=(28, 30, 36), outline=colors["trim"], width=5)

    grid = cell_grid(scene)
    cell_bboxes: dict[str, list[float]] = {}
    cell_centers: dict[str, list[float]] = {}
    scene_entities: list[dict[str, Any]] = []
    for row in range(ROW_COUNT):
        for col in range(REEL_COUNT):
            x0 = grid_left + col * (render_params.reel_cell_width_px + render_params.reel_gap_px)
            y0 = grid_top + row * (render_params.reel_cell_height_px + render_params.row_gap_px)
            x1 = x0 + render_params.reel_cell_width_px
            y1 = y0 + render_params.reel_cell_height_px
            cell_id = slot_cell_id(row, col)
            bbox = [round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)]
            center = [round((x0 + x1) / 2.0, 3), round((y0 + y1) / 2.0, 3)]
            cell_bboxes[cell_id] = bbox
            cell_centers[cell_id] = center
            draw.rounded_rectangle(bbox, radius=12, fill=colors["reel"], outline=(76, 76, 82), width=2)
            _draw_symbol(draw, bbox, grid[row][col], colors=colors)
            scene_entities.append(
                {
                    "id": cell_id,
                    "kind": "slot_cell",
                    "row": int(row),
                    "col": int(col),
                    "symbol_key": str(grid[row][col]),
                    "bbox_px": list(bbox),
                    "center_px": list(center),
                }
            )

    payline_segments: dict[str, list[list[float]]] = {}
    for payline_key in PAYLINE_IDS:
        cells = PAYLINE_CELLS_BY_ID[str(payline_key)]
        first_row, first_col = cells[0]
        last_row, last_col = cells[-1]
        first_center = cell_centers[slot_cell_id(int(first_row), int(first_col))]
        last_center = cell_centers[slot_cell_id(int(last_row), int(last_col))]
        segment = [list(first_center), list(last_center)]
        entity_id = payline_entity_id(str(payline_key))
        payline_segments[entity_id] = segment
        scene_entities.append(
            {
                "id": entity_id,
                "kind": "conceptual_payline",
                "payline_key": str(payline_key),
                "cells": [[int(row), int(col)] for row, col in cells],
                "segment_px": segment,
                "is_winning": bool(str(payline_key) in scene.winning_payline_ids),
                "visible": False,
            }
        )

    lever_x = right - 8
    lever_y0 = top + 152
    lever_y1 = top + 312
    draw.line([(lever_x, lever_y0), (lever_x + 54, lever_y1)], fill=colors["cabinet_dark"], width=11)
    draw.ellipse([lever_x + 34, lever_y1 - 18, lever_x + 76, lever_y1 + 24], fill=colors["trim"], outline=colors["cabinet_dark"], width=3)

    noisy_image, post_noise_meta = apply_post_image_noise(
        image,
        instance_seed=int(instance_seed),
        params={},
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return RenderedSlotMachineScene(
        image=noisy_image,
        render_map={
            "cell_bboxes_px": cell_bboxes,
            "cell_centers_px": cell_centers,
            "payline_segments_px": payline_segments,
            "cabinet_bbox_px": [round(left, 3), round(top, 3), round(right, 3), round(bottom, 3)],
            "window_bbox_px": [round(float(v), 3) for v in window_bbox],
            "style_colors": {key: list(value) for key, value in colors.items()},
        },
        scene_entities=tuple(scene_entities),
        panel_style_meta=game_panel_scene_style_metadata(panel_style),
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
    )


__all__ = [
    "RenderedSlotMachineScene",
    "SlotMachineRenderParams",
    "render_slot_machine_scene",
    "resolve_slot_machine_render_params",
]
