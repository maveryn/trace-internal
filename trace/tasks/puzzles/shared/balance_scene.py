"""Shared rendering helpers for arithmetic equality-panel puzzle scenes."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font


SUPPORTED_PUZZLE_BALANCE_SCENE_VARIANTS: Tuple[str, ...] = (
    "balance_strip",
    "balance_card",
    "balance_outline",
)

_OBJECT_COLOR_BY_TYPE: Dict[str, Tuple[int, int, int]] = {
    "circle": (74, 127, 214),
    "triangle": (214, 130, 74),
    "diamond": (64, 164, 108),
    "square": (196, 90, 100),
    "hexagon": (136, 100, 196),
    "star": (205, 162, 62),
}


@dataclass(frozen=True)
class PuzzleBalanceRenderParams:
    """Resolved render parameters for one equality-panel arithmetic scene."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    item_box_width_px: int
    item_box_height_px: int
    item_gap_px: int
    scale_side_gap_px: int
    panel_gap_px: int
    query_gap_px: int
    query_box_width_px: int
    query_box_height_px: int
    scale_width_px: int
    scale_height_px: int
    slot_corner_radius_px: int
    border_width_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    value_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    box_fill_rgb: Tuple[int, int, int]
    query_box_fill_rgb: Tuple[int, int, int]
    border_color_rgb: Tuple[int, int, int]
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    accent_color_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class RenderedPuzzleBalanceScene:
    """Rendered equality-panel arithmetic image plus box geometry traces."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    box_bbox_map: Dict[str, List[float]]


def _rounded_rect(
    draw: ImageDraw.ImageDraw,
    bbox: Tuple[float, float, float, float],
    *,
    radius: int,
    fill: Sequence[int],
    outline: Sequence[int],
    width: int,
) -> None:
    """Draw one rounded rectangle with deterministic styling."""

    draw.rounded_rectangle(
        bbox,
        radius=int(radius),
        fill=tuple(int(value) for value in fill),
        outline=tuple(int(value) for value in outline),
        width=int(width),
    )


def _draw_shape_icon(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[float, float, float, float],
    object_type: str,
    fill_rgb: Sequence[int],
    outline_rgb: Sequence[int],
    width: int,
) -> None:
    """Draw one simple symbolic shape inside a box."""

    left, top, right, bottom = [float(value) for value in bbox]
    inset = 16.0
    x0, y0, x1, y1 = left + inset, top + inset, right - inset, bottom - inset
    cx = 0.5 * (x0 + x1)
    cy = 0.5 * (y0 + y1)
    w = x1 - x0
    h = y1 - y0
    kind = str(object_type)
    fill = tuple(int(value) for value in fill_rgb)
    outline = tuple(int(value) for value in outline_rgb)
    stroke = max(1, int(width))

    if kind == "circle":
        draw.ellipse((x0, y0, x1, y1), fill=fill, outline=outline, width=stroke)
        return
    if kind == "square":
        draw.rectangle((x0, y0, x1, y1), fill=fill, outline=outline, width=stroke)
        return
    if kind == "triangle":
        points = [(cx, y0), (x1, y1), (x0, y1)]
    elif kind == "diamond":
        points = [(cx, y0), (x1, cy), (cx, y1), (x0, cy)]
    elif kind == "hexagon":
        points = [
            (x0 + 0.22 * w, y0),
            (x1 - 0.22 * w, y0),
            (x1, cy),
            (x1 - 0.22 * w, y1),
            (x0 + 0.22 * w, y1),
            (x0, cy),
        ]
    elif kind == "star":
        outer = 0.5 * min(w, h)
        inner = 0.45 * outer
        points = []
        for index in range(10):
            radius = outer if index % 2 == 0 else inner
            angle = -math.pi / 2.0 + (index * math.pi / 5.0)
            points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    else:
        raise ValueError(f"unsupported balance object_type: {object_type}")
    draw.polygon(points, fill=fill, outline=outline, width=stroke)


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font,
    fill: Sequence[int],
    stroke_fill: Sequence[int],
    stroke_width: int = 1,
) -> List[float]:
    """Draw centered text and return its drawn bbox."""

    bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
    left, top, right, bottom = [float(value) for value in bbox]
    cx, cy = float(center[0]), float(center[1])
    tx = float(cx - (0.5 * (left + right)))
    ty = float(cy - (0.5 * (top + bottom)))
    draw.text(
        (tx, ty),
        str(text),
        fill=tuple(int(v) for v in fill),
        font=font,
        stroke_width=max(0, int(stroke_width)),
        stroke_fill=tuple(int(v) for v in stroke_fill),
    )
    return [
        round(float(tx + left), 3),
        round(float(ty + top), 3),
        round(float(tx + right), 3),
        round(float(ty + bottom), 3),
    ]


def _draw_balance_token(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    width_px: float,
    height_px: float,
    color_rgb: Sequence[int],
    stroke_width: int,
) -> List[float]:
    """Draw one centered arithmetic token and return its drawn bbox."""

    cx, cy = float(center[0]), float(center[1])
    token = str(text)
    font_scale = 0.72 if token == "=" else 0.28
    token_bbox = _draw_centered_text(
        draw,
        text=token,
        center=(float(cx), float(cy)),
        font=load_font(max(18, int(font_scale * float(height_px))), bold=True),
        fill=color_rgb,
        stroke_fill=(255, 255, 255),
        stroke_width=max(1, int(stroke_width)),
    )
    left, top, right, bottom = [float(value) for value in token_bbox]
    min_width = float(max(28.0, 0.4 * float(width_px))) if token == "=" else 0.0
    if float(right - left) < float(min_width):
        pad = 0.5 * (float(min_width) - float(right - left))
        left -= float(pad)
        right += float(pad)
    return [
        round(float(left), 3),
        round(float(top), 3),
        round(float(right), 3),
        round(float(bottom), 3),
    ]


def render_puzzle_balance_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    panel_specs: Sequence[Mapping[str, Any]],
    query_spec: Mapping[str, Any],
    render_params: PuzzleBalanceRenderParams,
) -> RenderedPuzzleBalanceScene:
    """Render one equality-panel arithmetic scene with an explicit query row."""

    selected_variant = str(scene_variant)
    if selected_variant not in set(SUPPORTED_PUZZLE_BALANCE_SCENE_VARIANTS):
        raise ValueError(f"unsupported puzzle equality scene_variant: {selected_variant}")
    panels = [dict(panel) for panel in panel_specs]
    if not panels:
        raise ValueError("equality-panel scenes require at least one panel")

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    value_font = load_font(int(render_params.value_font_size_px), bold=True)

    box_width = float(render_params.item_box_width_px)
    box_height = float(render_params.item_box_height_px)
    item_gap = float(render_params.item_gap_px)
    scale_side_gap = float(render_params.scale_side_gap_px)
    scale_width = float(render_params.scale_width_px)
    scale_height = float(render_params.scale_height_px)
    panel_gap = float(render_params.panel_gap_px)
    query_gap = float(render_params.query_gap_px)
    query_box_width = float(render_params.query_box_width_px)
    query_box_height = float(render_params.query_box_height_px)

    left_widths = []
    right_widths = []
    for panel in panels:
        left_count = len(list(panel.get("left_items", ())))
        right_count = len(list(panel.get("right_items", ())))
        left_widths.append(float((left_count * box_width) + max(0, left_count - 1) * item_gap))
        right_widths.append(float((right_count * box_width) + max(0, right_count - 1) * item_gap))
    max_left_width = max(left_widths) if left_widths else 0.0
    max_right_width = max(right_widths) if right_widths else 0.0

    panel_content_width = float(max_left_width + scale_side_gap + scale_width + scale_side_gap + max_right_width)
    query_row_width = float(query_box_width + scale_side_gap + scale_width + scale_side_gap + query_box_width)
    content_width = float(max(panel_content_width, query_row_width))
    content_height = float(
        len(panels) * box_height
        + max(0, len(panels) - 1) * panel_gap
        + query_gap
        + query_box_height
    )
    content_left = float(render_params.scene_margin_left_px + max(0.0, 0.5 * ((render_params.canvas_width - render_params.scene_margin_left_px - render_params.scene_margin_right_px) - content_width)))
    content_top = float(render_params.scene_margin_top_px + max(0.0, 0.5 * ((render_params.canvas_height - render_params.scene_margin_top_px - render_params.scene_margin_bottom_px) - content_height)))
    center_x = float(content_left + 0.5 * content_width)

    panel_bbox: Tuple[float, float, float, float] | None = None
    if selected_variant == "balance_card":
        panel_bbox = (
            float(render_params.scene_margin_left_px),
            float(render_params.scene_margin_top_px),
            float(render_params.canvas_width - render_params.scene_margin_right_px),
            float(render_params.canvas_height - render_params.scene_margin_bottom_px),
        )
        _rounded_rect(
            draw,
            panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=render_params.panel_fill_rgb,
            outline=render_params.border_color_rgb,
            width=max(1, int(render_params.border_width_px)),
        )

    entities: List[Dict[str, Any]] = []
    box_bbox_map: Dict[str, List[float]] = {}
    scene_union_boxes: List[List[float]] = []

    current_y = float(content_top)
    for panel_index, panel in enumerate(panels):
        left_items = [dict(item) for item in panel.get("left_items", ())]
        right_items = [dict(item) for item in panel.get("right_items", ())]
        left_width = float(left_widths[int(panel_index)])
        right_width = float(right_widths[int(panel_index)])
        row_center_y = float(current_y + 0.5 * box_height)
        left_start_x = float(center_x - (0.5 * scale_width) - scale_side_gap - left_width)
        right_start_x = float(center_x + (0.5 * scale_width) + scale_side_gap)

        for side_name, items, start_x in (
            ("left", left_items, left_start_x),
            ("right", right_items, right_start_x),
        ):
            current_x = float(start_x)
            for item_index, item in enumerate(items):
                box_id = str(item["box_id"])
                bbox = (
                    float(current_x),
                    float(current_y),
                    float(current_x + box_width),
                    float(current_y + box_height),
                )
                is_query = bool(item.get("is_query_box", False))
                if selected_variant == "balance_outline":
                    fill_rgb = (255, 255, 255)
                    outline_rgb = render_params.accent_color_rgb if is_query else render_params.border_color_rgb
                else:
                    fill_rgb = render_params.query_box_fill_rgb if is_query else render_params.box_fill_rgb
                    outline_rgb = render_params.accent_color_rgb if is_query else render_params.border_color_rgb
                _rounded_rect(
                    draw,
                    bbox,
                    radius=int(render_params.slot_corner_radius_px),
                    fill=fill_rgb,
                    outline=outline_rgb,
                    width=int(render_params.border_width_px + (1 if is_query else 0)),
                )
                if str(item.get("kind")) == "object":
                    object_type = str(item["object_type"])
                    color_rgb = _OBJECT_COLOR_BY_TYPE.get(object_type, render_params.accent_color_rgb)
                    _draw_shape_icon(
                        draw,
                        bbox=bbox,
                        object_type=object_type,
                        fill_rgb=color_rgb,
                        outline_rgb=render_params.border_color_rgb,
                        width=max(1, int(render_params.border_width_px)),
                    )
                else:
                    text_bbox = _draw_centered_text(
                        draw,
                        text=str(item["text"]),
                        center=(0.5 * (bbox[0] + bbox[2]), 0.5 * (bbox[1] + bbox[3])),
                        font=value_font,
                        fill=render_params.text_color_rgb,
                        stroke_fill=render_params.text_stroke_rgb,
                        stroke_width=1,
                    )
                    scene_union_boxes.append(list(text_bbox))
                bbox_list = [round(float(value), 3) for value in bbox]
                box_bbox_map[str(box_id)] = list(bbox_list)
                scene_union_boxes.append(list(bbox_list))
                entities.append(
                    {
                        "entity_id": str(box_id),
                        "entity_type": "puzzle_balance_box",
                        "bbox_px": list(bbox_list),
                        "attrs": {
                            "panel_index": int(panel_index),
                            "side": str(side_name),
                            "item_index": int(item_index),
                            "kind": str(item.get("kind")),
                            "object_type": item.get("object_type"),
                            "value": item.get("value"),
                            "is_query_box": bool(is_query),
                        },
                    }
                )
                if int(item_index) < len(items) - 1:
                    plus_center_x = float(current_x + box_width + (0.5 * item_gap))
                    plus_bbox = _draw_balance_token(
                        draw,
                        text="+",
                        center=(plus_center_x, row_center_y),
                        width_px=item_gap,
                        height_px=box_height,
                        color_rgb=render_params.border_color_rgb,
                        stroke_width=max(1, int(render_params.border_width_px)),
                    )
                    scene_union_boxes.append(list(plus_bbox))
                    entities.append(
                        {
                            "entity_id": f"balance_plus_{int(panel_index)}_{str(side_name)}_{int(item_index)}",
                            "entity_type": "puzzle_balance_operator",
                            "bbox_px": list(plus_bbox),
                            "attrs": {
                                "panel_index": int(panel_index),
                                "side": str(side_name),
                                "operator_symbol": "+",
                                "after_item_index": int(item_index),
                            },
                        }
                    )
                current_x += float(box_width + item_gap)

        equal_bbox = _draw_balance_token(
            draw,
            text="=",
            center=(center_x, row_center_y),
            width_px=scale_width,
            height_px=scale_height,
            color_rgb=render_params.border_color_rgb,
            stroke_width=max(2, int(render_params.border_width_px)),
        )
        scene_union_boxes.append(list(equal_bbox))
        entities.append(
            {
                "entity_id": f"balance_equals_{int(panel_index)}",
                "entity_type": "puzzle_balance_equals",
                "bbox_px": list(equal_bbox),
                "attrs": {
                    "panel_index": int(panel_index),
                    "text": "=",
                },
            }
        )
        entities.append(
            {
                "entity_id": f"balance_panel_{int(panel_index)}",
                "entity_type": "puzzle_balance_panel",
                "bbox_px": list(
                    [
                        round(float(min(left_start_x, equal_bbox[0], right_start_x)), 3),
                        round(float(current_y), 3),
                        round(float(max(right_start_x + right_width, equal_bbox[2], left_start_x + left_width)), 3),
                        round(float(current_y + box_height), 3),
                    ]
                ),
                "attrs": {
                    "panel_index": int(panel_index),
                },
            }
        )
        current_y += float(box_height + panel_gap)

    query_object_box_id = str(query_spec["query_object_box_id"])
    query_box_id = str(query_spec["query_box_id"])
    query_object_type = str(query_spec["object_type"])
    query_row_left = float(center_x - (0.5 * query_row_width))
    query_top = float(current_y - panel_gap + query_gap)
    query_object_bbox = (
        float(query_row_left),
        float(query_top),
        float(query_row_left + query_box_width),
        float(query_top + query_box_height),
    )
    query_object_fill_rgb = render_params.box_fill_rgb if selected_variant != "balance_outline" else (255, 255, 255)
    _rounded_rect(
        draw,
        query_object_bbox,
        radius=int(render_params.slot_corner_radius_px),
        fill=query_object_fill_rgb,
        outline=render_params.border_color_rgb,
        width=int(render_params.border_width_px),
    )
    query_color_rgb = _OBJECT_COLOR_BY_TYPE.get(query_object_type, render_params.accent_color_rgb)
    _draw_shape_icon(
        draw,
        bbox=query_object_bbox,
        object_type=query_object_type,
        fill_rgb=query_color_rgb,
        outline_rgb=render_params.border_color_rgb,
        width=max(1, int(render_params.border_width_px)),
    )
    query_object_bbox_list = [round(float(value), 3) for value in query_object_bbox]
    box_bbox_map[str(query_object_box_id)] = list(query_object_bbox_list)
    scene_union_boxes.append(list(query_object_bbox_list))
    entities.append(
        {
            "entity_id": str(query_object_box_id),
            "entity_type": "puzzle_balance_box",
            "bbox_px": list(query_object_bbox_list),
            "attrs": {
                "panel_index": None,
                "side": "query",
                "item_index": 0,
                "kind": "object",
                "object_type": str(query_object_type),
                "value": None,
                "query_role": "object",
                "is_query_box": False,
            },
        }
    )
    query_equals_center_x = float(query_row_left + query_box_width + scale_side_gap + (0.5 * scale_width))
    query_center_y = float(query_top + (0.5 * query_box_height))
    query_equal_bbox = _draw_balance_token(
        draw,
        text="=",
        center=(query_equals_center_x, query_center_y),
        width_px=scale_width,
        height_px=scale_height,
        color_rgb=render_params.border_color_rgb,
        stroke_width=max(2, int(render_params.border_width_px)),
    )
    scene_union_boxes.append(list(query_equal_bbox))
    entities.append(
        {
            "entity_id": "balance_equals_query",
            "entity_type": "puzzle_balance_equals",
            "bbox_px": list(query_equal_bbox),
            "attrs": {
                "panel_index": None,
                "text": "=",
                "side": "query",
            },
        }
    )
    query_answer_left = float(query_row_left + query_box_width + scale_side_gap + scale_width + scale_side_gap)
    query_answer_bbox = (
        float(query_answer_left),
        float(query_top),
        float(query_answer_left + query_box_width),
        float(query_top + query_box_height),
    )
    query_outline_rgb = render_params.accent_color_rgb
    query_fill_rgb = render_params.query_box_fill_rgb if selected_variant != "balance_outline" else (255, 255, 255)
    _rounded_rect(
        draw,
        query_answer_bbox,
        radius=int(render_params.slot_corner_radius_px),
        fill=query_fill_rgb,
        outline=query_outline_rgb,
        width=int(render_params.border_width_px + 1),
    )
    query_answer_text_bbox = _draw_centered_text(
        draw,
        text="?",
        center=(0.5 * (query_answer_bbox[0] + query_answer_bbox[2]), 0.5 * (query_answer_bbox[1] + query_answer_bbox[3])),
        font=value_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=1,
    )
    query_answer_bbox_list = [round(float(value), 3) for value in query_answer_bbox]
    box_bbox_map[str(query_box_id)] = list(query_answer_bbox_list)
    scene_union_boxes.append(list(query_answer_bbox_list))
    scene_union_boxes.append(list(query_answer_text_bbox))
    entities.append(
        {
            "entity_id": str(query_box_id),
            "entity_type": "puzzle_balance_box",
            "bbox_px": list(query_answer_bbox_list),
            "attrs": {
                "panel_index": None,
                "side": "query",
                "item_index": 1,
                "kind": "unknown",
                "object_type": None,
                "value": None,
                "query_role": "answer",
                "is_query_box": True,
            },
        }
    )

    if panel_bbox is not None:
        scene_bbox = [round(float(value), 3) for value in panel_bbox]
    else:
        scene_bbox = [
            round(float(min(box[0] for box in scene_union_boxes)), 3),
            round(float(min(box[1] for box in scene_union_boxes)), 3),
            round(float(max(box[2] for box in scene_union_boxes)), 3),
            round(float(max(box[3] for box in scene_union_boxes)), 3),
        ]

    return RenderedPuzzleBalanceScene(
        image=image,
        entities=list(entities),
        scene_bbox_px=list(scene_bbox),
        box_bbox_map={str(key): list(value) for key, value in box_bbox_map.items()},
    )


__all__ = [
    "PuzzleBalanceRenderParams",
    "RenderedPuzzleBalanceScene",
    "SUPPORTED_PUZZLE_BALANCE_SCENE_VARIANTS",
    "render_puzzle_balance_scene",
]
