"""Shared rendering helpers for arithmetic puzzle scenes with explicit unknown slots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.drawing import draw_centered_text as _draw_centered_text, draw_rounded_rect as _rounded_rect
from ...shared.text_rendering import load_font


SUPPORTED_PUZZLE_ARITHMETIC_SCENE_VARIANTS: Tuple[str, ...] = (
    "equation_strip",
    "equation_card",
    "equation_outline",
)


@dataclass(frozen=True)
class PuzzleArithmeticRenderParams:
    """Resolved render parameters for one arithmetic puzzle scene."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    slot_width_px: int
    slot_height_px: int
    token_gap_px: int
    row_gap_px: int
    slot_corner_radius_px: int
    border_width_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    value_font_size_px: int
    operator_font_size_px: int
    slot_fill_rgb: Tuple[int, int, int]
    unknown_slot_fill_rgb: Tuple[int, int, int]
    panel_fill_rgb: Tuple[int, int, int]
    border_color_rgb: Tuple[int, int, int]
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    accent_color_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class RenderedPuzzleArithmeticScene:
    """Rendered arithmetic puzzle image plus slot/operator geometry traces."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    slot_traces: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    slot_bbox_map: Dict[str, List[float]]


def _text_bbox(draw: ImageDraw.ImageDraw, text: str, *, font, stroke_width: int = 1) -> Tuple[float, float, float, float]:
    """Return text bbox at origin, including stroke, in pixel coordinates."""

    bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
    return float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])


def _text_size(draw: ImageDraw.ImageDraw, text: str, *, font) -> Tuple[float, float]:
    """Return text width and height in pixels."""

    bbox = _text_bbox(draw, str(text), font=font, stroke_width=1)
    return float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1])


def render_puzzle_arithmetic_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    equation_rows: Sequence[Sequence[Mapping[str, Any]]],
    render_params: PuzzleArithmeticRenderParams,
) -> RenderedPuzzleArithmeticScene:
    """Render one arithmetic puzzle scene with one explicit unknown slot."""

    selected_variant = str(scene_variant)
    if selected_variant not in set(SUPPORTED_PUZZLE_ARITHMETIC_SCENE_VARIANTS):
        raise ValueError(f"unsupported puzzle arithmetic scene_variant: {selected_variant}")
    rows = [[dict(token) for token in row] for row in equation_rows]
    if not rows:
        raise ValueError("arithmetic puzzle scenes require at least one row")

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    value_font = load_font(int(render_params.value_font_size_px), bold=True)
    operator_font = load_font(int(render_params.operator_font_size_px), bold=True)

    content_left = float(render_params.scene_margin_left_px)
    content_top = float(render_params.scene_margin_top_px)
    content_right = float(render_params.canvas_width - render_params.scene_margin_right_px)
    content_bottom = float(render_params.canvas_height - render_params.scene_margin_bottom_px)
    slot_width = float(render_params.slot_width_px)
    slot_height = float(render_params.slot_height_px)
    token_gap = float(render_params.token_gap_px)
    row_gap = float(render_params.row_gap_px)

    row_widths: List[float] = []
    row_heights: List[float] = []
    operator_width_maps: List[List[float]] = []
    for row in rows:
        token_widths: List[float] = []
        row_height = float(slot_height)
        operator_widths: List[float] = []
        for token in row:
            if str(token.get("kind")) == "slot":
                token_widths.append(float(slot_width))
                operator_widths.append(0.0)
            else:
                text = str(token.get("text", ""))
                text_width, text_height = _text_size(draw, text, font=operator_font)
                width = max(float(text_width + 20.0), 40.0)
                token_widths.append(float(width))
                operator_widths.append(float(width))
                row_height = max(float(row_height), float(text_height + 16.0))
        row_widths.append(float(sum(token_widths) + max(0, len(token_widths) - 1) * token_gap))
        row_heights.append(float(row_height))
        operator_width_maps.append(operator_widths)

    total_height = float(sum(row_heights) + max(0, len(rows) - 1) * row_gap)
    top_y = float(content_top + max(0.0, 0.5 * ((content_bottom - content_top) - total_height)))
    scene_union_boxes: List[List[float]] = []
    entities: List[Dict[str, Any]] = []
    slot_traces: List[Dict[str, Any]] = []
    slot_bbox_map: Dict[str, List[float]] = {}

    panel_bbox: Tuple[float, float, float, float] | None = None
    if selected_variant == "equation_card":
        panel_bbox = (
            float(content_left),
            float(content_top),
            float(content_right),
            float(content_bottom),
        )
        _rounded_rect(
            draw,
            panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=render_params.panel_fill_rgb,
            outline=render_params.border_color_rgb,
            width=max(1, int(render_params.border_width_px)),
        )

    current_y = float(top_y)
    for row_index, row in enumerate(rows):
        row_height = float(row_heights[int(row_index)])
        row_width = float(row_widths[int(row_index)])
        current_x = float(content_left + max(0.0, 0.5 * ((content_right - content_left) - row_width)))
        for token_index, token in enumerate(row):
            kind = str(token.get("kind"))
            if kind == "slot":
                slot_id = str(token["slot_id"])
                left = float(current_x)
                top = float(current_y + max(0.0, 0.5 * (row_height - slot_height)))
                bbox = (
                    float(left),
                    float(top),
                    float(left + slot_width),
                    float(top + slot_height),
                )
                is_unknown = bool(token.get("is_unknown", False))
                if selected_variant == "equation_outline":
                    fill_rgb = (255, 255, 255)
                    outline_rgb = render_params.accent_color_rgb if is_unknown else render_params.border_color_rgb
                else:
                    fill_rgb = render_params.unknown_slot_fill_rgb if is_unknown else render_params.slot_fill_rgb
                    outline_rgb = render_params.border_color_rgb
                _rounded_rect(
                    draw,
                    bbox,
                    radius=int(render_params.slot_corner_radius_px),
                    fill=fill_rgb,
                    outline=outline_rgb,
                    width=int(render_params.border_width_px),
                )
                center = (float(0.5 * (bbox[0] + bbox[2])), float(0.5 * (bbox[1] + bbox[3])))
                text_bbox = _draw_centered_text(
                    draw,
                    text=str(token["text"]),
                    center=center,
                    font=value_font,
                    fill=render_params.text_color_rgb,
                    stroke_fill=render_params.text_stroke_rgb,
                    stroke_width=1,
                )
                bbox_list = [round(float(value), 3) for value in bbox]
                scene_union_boxes.append(list(bbox_list))
                slot_bbox_map[str(slot_id)] = list(bbox_list)
                slot_trace = {
                    "slot_id": str(slot_id),
                    "bbox_px": list(bbox_list),
                    "text_bbox_px": list(text_bbox),
                    "row_index": int(row_index),
                    "token_index": int(token_index),
                    "text": str(token["text"]),
                    "is_unknown": bool(is_unknown),
                    "value": token.get("value"),
                }
                slot_traces.append(dict(slot_trace))
                entities.append(
                    {
                        "entity_id": str(slot_id),
                        "entity_type": "puzzle_slot",
                        "bbox_px": list(bbox_list),
                        "attrs": {
                            "row_index": int(row_index),
                            "token_index": int(token_index),
                            "text": str(token["text"]),
                            "value": token.get("value"),
                            "is_unknown": bool(is_unknown),
                        },
                    }
                )
                current_x += float(slot_width)
            else:
                token_text = str(token.get("text", ""))
                width = float(operator_width_maps[int(row_index)][int(token_index)])
                center = (
                    float(current_x + 0.5 * width),
                    float(current_y + 0.5 * row_height),
                )
                text_bbox = _draw_centered_text(
                    draw,
                    text=token_text,
                    center=center,
                    font=operator_font,
                    fill=render_params.text_color_rgb,
                    stroke_fill=render_params.text_stroke_rgb,
                    stroke_width=1,
                )
                entities.append(
                    {
                        "entity_id": f"operator_r{int(row_index)}_t{int(token_index)}",
                        "entity_type": "puzzle_operator",
                        "bbox_px": list(text_bbox),
                        "attrs": {
                            "row_index": int(row_index),
                            "token_index": int(token_index),
                            "text": token_text,
                        },
                    }
                )
                scene_union_boxes.append(list(text_bbox))
                current_x += float(width)
            if int(token_index) != int(len(row) - 1):
                current_x += float(token_gap)
        current_y += float(row_height + row_gap)

    if panel_bbox is not None:
        scene_bbox = [round(float(value), 3) for value in panel_bbox]
    else:
        scene_bbox = [
            round(float(min(box[0] for box in scene_union_boxes)), 3),
            round(float(min(box[1] for box in scene_union_boxes)), 3),
            round(float(max(box[2] for box in scene_union_boxes)), 3),
            round(float(max(box[3] for box in scene_union_boxes)), 3),
        ]

    return RenderedPuzzleArithmeticScene(
        image=image,
        entities=list(entities),
        slot_traces=list(slot_traces),
        scene_bbox_px=list(scene_bbox),
        slot_bbox_map={str(key): list(value) for key, value in slot_bbox_map.items()},
    )


__all__ = [
    "PuzzleArithmeticRenderParams",
    "RenderedPuzzleArithmeticScene",
    "SUPPORTED_PUZZLE_ARITHMETIC_SCENE_VARIANTS",
    "render_puzzle_arithmetic_scene",
]
