"""Shared Braille-cell renderer for misc notation tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font
from .drawing import draw_centered_text, draw_rounded_rect
from .scene_style import MiscSceneStyle


BRAILLE_POSITIONS: tuple[int, ...] = (1, 2, 3, 4, 5, 6)
SUPPORTED_BRAILLE_SCENE_VARIANTS: tuple[str, ...] = ("clean_card", "notebook_card", "exam_scan")


@dataclass(frozen=True)
class BrailleCellSpec:
    item_id: str
    raised_positions: tuple[int, ...]
    label: str = ""
    role: str = "cell"
    marked: bool = False


@dataclass(frozen=True)
class BrailleRenderParams:
    canvas_width: int = 980
    canvas_height: int = 680
    cell_width_px: int = 132
    cell_height_px: int = 184
    dot_radius_px: int = 13
    empty_dot_radius_px: int = 10
    cell_corner_radius_px: int = 18
    cell_border_width_px: int = 2
    marked_border_width_px: int = 5
    option_label_font_size_px: int = 28
    title_font_size_px: int = 24


@dataclass(frozen=True)
class RenderedBrailleScene:
    image: Image.Image
    entities: tuple[dict[str, Any], ...]
    item_bboxes: dict[str, list[float]]
    dot_centers: dict[str, list[float]]
    raised_dot_centers: dict[str, list[float]]
    cell_dot_centers: dict[str, dict[str, list[float]]]
    scene_bbox_px: list[float]
    style_metadata: dict[str, Any]


def _rounded_bbox(values: Sequence[float]) -> list[float]:
    return [round(float(value), 3) for value in values]


def _position_center(
    bbox: Sequence[float],
    *,
    position: int,
) -> tuple[float, float]:
    left, top, right, bottom = [float(value) for value in bbox]
    column = 0 if int(position) in {1, 2, 3} else 1
    row = {1: 0, 2: 1, 3: 2, 4: 0, 5: 1, 6: 2}[int(position)]
    x_pad = 0.34 * float(right - left)
    y_pad = 0.25 * float(bottom - top)
    col_gap = float(right - left) - (2.0 * x_pad)
    row_gap = (float(bottom - top) - (2.0 * y_pad)) / 2.0
    return float(left + x_pad + (column * col_gap)), float(top + y_pad + (row * row_gap))


def _draw_braille_cell(
    draw: ImageDraw.ImageDraw,
    *,
    spec: BrailleCellSpec,
    bbox: Sequence[float],
    params: BrailleRenderParams,
    style: MiscSceneStyle,
    label_position: str,
) -> tuple[dict[str, list[float]], dict[str, list[float]], dict[str, Any]]:
    cell_bbox = _rounded_bbox(bbox)
    raised_set = {int(pos) for pos in spec.raised_positions}
    outline = tuple(int(value) for value in style.panel_border_rgb)
    fill = tuple(int(value) for value in style.panel_fill_rgb)
    if spec.marked:
        outline = tuple(int(value) for value in style.panel_accent_rgb)
    draw_rounded_rect(
        draw,
        tuple(float(value) for value in cell_bbox),
        radius=int(params.cell_corner_radius_px),
        fill=fill,
        outline=outline,
        width=int(params.marked_border_width_px if spec.marked else params.cell_border_width_px),
    )

    dot_centers: dict[str, list[float]] = {}
    raised_dot_centers: dict[str, list[float]] = {}
    for position in BRAILLE_POSITIONS:
        cx, cy = _position_center(cell_bbox, position=int(position))
        dot_id = f"{spec.item_id}_dot_{position}"
        center = [round(float(cx), 3), round(float(cy), 3)]
        dot_centers[dot_id] = center
        if int(position) in raised_set:
            radius = int(params.dot_radius_px)
            dot_fill = tuple(int(value) for value in style.text_rgb)
            dot_outline = tuple(int(value) for value in style.text_rgb)
            raised_dot_centers[dot_id] = center
        else:
            radius = int(params.empty_dot_radius_px)
            dot_fill = tuple(int(value) for value in style.panel_fill_rgb)
            dot_outline = tuple(int(value) for value in style.grid_rgb)
        draw.ellipse(
            (float(cx - radius), float(cy - radius), float(cx + radius), float(cy + radius)),
            fill=dot_fill,
            outline=dot_outline,
            width=2,
        )

    label_bbox: list[float] | None = None
    if str(spec.label).strip():
        font = load_font(int(params.option_label_font_size_px), bold=True)
        label_y = float(cell_bbox[1] - 24) if str(label_position) == "above" else float(cell_bbox[3] + 28)
        label_bbox = draw_centered_text(
            draw,
            text=str(spec.label),
            center=(0.5 * (float(cell_bbox[0]) + float(cell_bbox[2])), label_y),
            font=font,
            fill=style.text_rgb,
            stroke_fill=style.panel_fill_rgb,
            stroke_width=2,
        )

    entity = {
        "item_id": str(spec.item_id),
        "entity_type": "braille_cell",
        "role": str(spec.role),
        "label": str(spec.label),
        "raised_positions": [int(pos) for pos in spec.raised_positions],
        "bbox_px": list(cell_bbox),
        "marked": bool(spec.marked),
        "dot_center_ids": [f"{spec.item_id}_dot_{position}" for position in BRAILLE_POSITIONS],
        "raised_dot_center_ids": [f"{spec.item_id}_dot_{position}" for position in spec.raised_positions],
    }
    if label_bbox is not None:
        entity["label_bbox_px"] = list(label_bbox)
    return dot_centers, raised_dot_centers, entity


def render_braille_count_scene(
    image: Image.Image,
    *,
    cells: Sequence[BrailleCellSpec],
    params: BrailleRenderParams,
    style: MiscSceneStyle,
) -> RenderedBrailleScene:
    """Render a row of Braille cells with one target cell marked."""

    draw = ImageDraw.Draw(image)
    width, height = int(params.canvas_width), int(params.canvas_height)
    cell_count = len(cells)
    if int(cell_count) <= 0:
        raise ValueError("Braille count scene requires at least one cell")
    cell_gap = 34
    if int(cell_count) > 1:
        max_gap = int((max(0, width - 64 - (cell_count * int(params.cell_width_px)))) / (cell_count - 1))
        cell_gap = max(18, min(cell_gap, int(max_gap)))
    total_width = (cell_count * int(params.cell_width_px)) + ((cell_count - 1) * int(cell_gap))
    start_x = max(24, int(round((width - total_width) / 2)))
    top = int(round(0.5 * height - 0.5 * int(params.cell_height_px)))

    entities: list[dict[str, Any]] = []
    item_bboxes: dict[str, list[float]] = {}
    dot_centers: dict[str, list[float]] = {}
    raised_dot_centers: dict[str, list[float]] = {}
    cell_dot_centers: dict[str, dict[str, list[float]]] = {}
    for index, spec in enumerate(cells):
        left = float(start_x + (index * (int(params.cell_width_px) + int(cell_gap))))
        bbox = [left, float(top), left + int(params.cell_width_px), float(top + int(params.cell_height_px))]
        cell_dots, cell_raised, entity = _draw_braille_cell(
            draw,
            spec=spec,
            bbox=bbox,
            params=params,
            style=style,
            label_position="below",
        )
        entities.append(entity)
        item_bboxes[str(spec.item_id)] = _rounded_bbox(bbox)
        dot_centers.update(cell_dots)
        raised_dot_centers.update(cell_raised)
        cell_dot_centers[str(spec.item_id)] = dict(cell_dots)

    scene_bbox = [30.0, float(top - 72), float(width - 30), float(top + int(params.cell_height_px) + 72)]
    return RenderedBrailleScene(
        image=image,
        entities=tuple(entities),
        item_bboxes=item_bboxes,
        dot_centers=dot_centers,
        raised_dot_centers=raised_dot_centers,
        cell_dot_centers=cell_dot_centers,
        scene_bbox_px=_rounded_bbox(scene_bbox),
        style_metadata={"renderer": "braille_cell_v0", "layout": "marked_row"},
    )


def render_braille_match_scene(
    image: Image.Image,
    *,
    reference: BrailleCellSpec,
    options: Sequence[BrailleCellSpec],
    params: BrailleRenderParams,
    style: MiscSceneStyle,
) -> RenderedBrailleScene:
    """Render one reference Braille cell and six labeled option cells."""

    draw = ImageDraw.Draw(image)
    width, height = int(params.canvas_width), int(params.canvas_height)
    option_count = len(options)
    if int(option_count) != 6:
        raise ValueError("Braille matching scene requires exactly six options")

    item_bboxes: dict[str, list[float]] = {}
    dot_centers: dict[str, list[float]] = {}
    raised_dot_centers: dict[str, list[float]] = {}
    cell_dot_centers: dict[str, dict[str, list[float]]] = {}
    entities: list[dict[str, Any]] = []

    ref_left = 88.0
    ref_top = float(round(0.5 * height - 0.5 * int(params.cell_height_px)))
    ref_bbox = [ref_left, ref_top, ref_left + int(params.cell_width_px), ref_top + int(params.cell_height_px)]
    ref_dots, ref_raised, ref_entity = _draw_braille_cell(
        draw,
        spec=reference,
        bbox=ref_bbox,
        params=params,
        style=style,
        label_position="above",
    )
    item_bboxes[str(reference.item_id)] = _rounded_bbox(ref_bbox)
    dot_centers.update(ref_dots)
    raised_dot_centers.update(ref_raised)
    cell_dot_centers[str(reference.item_id)] = dict(ref_dots)
    entities.append(ref_entity)

    option_gap_x = 42
    option_gap_y = 52
    grid_cols = 3
    grid_left = 370.0
    grid_top = float(round(0.5 * height - int(params.cell_height_px) - (0.5 * option_gap_y)))
    for index, spec in enumerate(options):
        row = index // grid_cols
        col = index % grid_cols
        left = grid_left + (col * (int(params.cell_width_px) + option_gap_x))
        top = grid_top + (row * (int(params.cell_height_px) + option_gap_y))
        bbox = [left, top, left + int(params.cell_width_px), top + int(params.cell_height_px)]
        option_dots, option_raised, entity = _draw_braille_cell(
            draw,
            spec=spec,
            bbox=bbox,
            params=params,
            style=style,
            label_position="above",
        )
        item_bboxes[str(spec.item_id)] = _rounded_bbox(bbox)
        dot_centers.update(option_dots)
        raised_dot_centers.update(option_raised)
        cell_dot_centers[str(spec.item_id)] = dict(option_dots)
        entities.append(entity)

    scene_bbox = [40.0, 50.0, float(width - 40), float(height - 48)]
    return RenderedBrailleScene(
        image=image,
        entities=tuple(entities),
        item_bboxes=item_bboxes,
        dot_centers=dot_centers,
        raised_dot_centers=raised_dot_centers,
        cell_dot_centers=cell_dot_centers,
        scene_bbox_px=_rounded_bbox(scene_bbox),
        style_metadata={"renderer": "braille_cell_v0", "layout": "reference_and_six_options"},
    )


__all__ = [
    "BRAILLE_POSITIONS",
    "BrailleCellSpec",
    "BrailleRenderParams",
    "RenderedBrailleScene",
    "SUPPORTED_BRAILLE_SCENE_VARIANTS",
    "render_braille_count_scene",
    "render_braille_match_scene",
]
