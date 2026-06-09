"""Shared renderer for worksheet-style balance-scale puzzle scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.bbox_projection import round_bbox
from ...shared.text_rendering import load_font
from .drawing import draw_centered_text, draw_rounded_rect
from .scene_style import PuzzleSceneStyle, draw_puzzle_panel_chrome
from .symbol_rendering import PUZZLE_OBJECT_COLOR_BY_TYPE, draw_puzzle_shape_icon


SUPPORTED_BALANCE_SCALE_SCENE_VARIANTS: Tuple[str, ...] = (
    "balance_sheet",
    "balance_card",
    "balance_outline",
)


@dataclass(frozen=True)
class BalanceScaleRenderParams:
    """Resolved render parameters for one balance-scale scene."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    panel_border_width_px: int
    scale_panel_gap_px: int
    query_row_height_px: int
    beam_width_px: int
    pan_width_px: int
    pan_height_px: int
    token_size_px: int
    token_gap_px: int
    line_width_px: int
    value_font_size_px: int
    label_font_size_px: int
    query_font_size_px: int
    unit_size_jitter: Dict[str, Any]


@dataclass(frozen=True)
class RenderedBalanceScaleScene:
    """Rendered image plus traceable balance-scale geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    item_bbox_map: Dict[str, List[float]]


def _panel_bbox(params: BalanceScaleRenderParams) -> Tuple[float, float, float, float]:
    return (
        float(params.scene_margin_left_px),
        float(params.scene_margin_top_px),
        float(params.canvas_width - params.scene_margin_right_px),
        float(params.canvas_height - params.scene_margin_bottom_px),
    )


def _draw_object_token(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    object_label: str,
    object_type: str,
    fill_rgb: Sequence[int],
    outline_rgb: Sequence[int],
    text_rgb: Sequence[int],
    text_stroke_rgb: Sequence[int],
    stroke_width: int,
    label_font_size_px: int,
    highlight_rgb: Sequence[int] | None = None,
) -> None:
    box = tuple(float(value) for value in bbox)
    if highlight_rgb is not None:
        pad = max(3.0, float(stroke_width) + 1.0)
        draw.rounded_rectangle(
            (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad),
            radius=max(6, int(0.18 * (box[2] - box[0]))),
            outline=tuple(int(value) for value in highlight_rgb),
            width=max(2, int(stroke_width) + 1),
        )
    draw_puzzle_shape_icon(
        draw,
        bbox=(box[0], box[1], box[2], box[3]),
        object_type=str(object_type),
        fill_rgb=fill_rgb,
        outline_rgb=outline_rgb,
        width=max(1, int(stroke_width)),
        inset_px=max(4.0, 0.10 * float(box[2] - box[0])),
    )
    draw_centered_text(
        draw,
        text=str(object_label),
        center=((box[0] + box[2]) * 0.5, (box[1] + box[3]) * 0.5),
        font=load_font(max(12, int(label_font_size_px)), bold=True),
        fill=tuple(int(value) for value in text_rgb),
        stroke_fill=tuple(int(value) for value in text_stroke_rgb),
        stroke_width=1,
    )


def _draw_numeric_chip(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    value: int,
    fill_rgb: Sequence[int],
    outline_rgb: Sequence[int],
    text_rgb: Sequence[int],
    text_stroke_rgb: Sequence[int],
    stroke_width: int,
    value_font_size_px: int,
) -> None:
    box = tuple(float(item) for item in bbox)
    draw_rounded_rect(
        draw,
        box,
        radius=max(6, int(0.14 * (box[3] - box[1]))),
        fill=tuple(int(value) for value in fill_rgb),
        outline=tuple(int(value) for value in outline_rgb),
        width=max(1, int(stroke_width)),
    )
    draw_centered_text(
        draw,
        text=str(int(value)),
        center=((box[0] + box[2]) * 0.5, (box[1] + box[3]) * 0.5),
        font=load_font(max(12, int(value_font_size_px)), bold=True),
        fill=tuple(int(item) for item in text_rgb),
        stroke_fill=tuple(int(item) for item in text_stroke_rgb),
        stroke_width=1,
    )


def _item_bbox_grid(
    *,
    pan_bbox: Sequence[float],
    item_count: int,
    token_size_px: int,
    token_gap_px: int,
) -> List[Tuple[float, float, float, float]]:
    if int(item_count) <= 0:
        return []
    left, top, right, bottom = [float(value) for value in pan_bbox]
    max_cols = 3 if int(item_count) > 4 else 4
    cols = min(int(max_cols), int(item_count))
    rows = (int(item_count) + int(cols) - 1) // int(cols)
    size = float(token_size_px)
    if rows > 1:
        available_h = max(1.0, bottom - top - float(token_gap_px))
        size = min(size, available_h / float(rows))
    row_gap = float(token_gap_px)
    col_gap = float(token_gap_px)
    total_h = rows * size + (rows - 1) * row_gap
    y0 = top + 0.5 * ((bottom - top) - total_h)
    boxes: List[Tuple[float, float, float, float]] = []
    remaining = int(item_count)
    index = 0
    for row in range(rows):
        row_cols = min(cols, remaining)
        total_w = row_cols * size + (row_cols - 1) * col_gap
        x0 = left + 0.5 * ((right - left) - total_w)
        for col in range(row_cols):
            x = x0 + col * (size + col_gap)
            y = y0 + row * (size + row_gap)
            boxes.append((x, y, x + size, y + size))
            index += 1
        remaining -= row_cols
    return boxes


def _draw_pan_items(
    draw: ImageDraw.ImageDraw,
    *,
    items: Sequence[Mapping[str, Any]],
    pan_bbox: Sequence[float],
    colors: Mapping[str, Tuple[int, int, int]],
    object_specs: Mapping[str, Mapping[str, Any]],
    item_bbox_map: Dict[str, List[float]],
    entities: List[Dict[str, Any]],
    params: BalanceScaleRenderParams,
    target_label: str,
    highlight_target: bool,
) -> None:
    boxes = _item_bbox_grid(
        pan_bbox=pan_bbox,
        item_count=len(items),
        token_size_px=int(params.token_size_px),
        token_gap_px=int(params.token_gap_px),
    )
    for item, bbox in zip(items, boxes):
        item_id = str(item["item_id"])
        item_bbox_map[item_id] = round_bbox(bbox)
        if str(item["kind"]) == "object":
            object_label = str(item["object_label"])
            object_spec = object_specs[object_label]
            object_type = str(object_spec["object_type"])
            fill_rgb = tuple(int(value) for value in object_spec["fill_rgb"])
            _draw_object_token(
                draw,
                bbox=bbox,
                object_label=object_label,
                object_type=object_type,
                fill_rgb=fill_rgb,
                outline_rgb=colors["line"],
                text_rgb=colors["text"],
                text_stroke_rgb=colors["stroke"],
                stroke_width=int(params.line_width_px),
                label_font_size_px=int(params.label_font_size_px),
                highlight_rgb=colors["mark"] if highlight_target and object_label == target_label else None,
            )
            entity_type = "balance_object_token"
        else:
            _draw_numeric_chip(
                draw,
                bbox=bbox,
                value=int(item["value"]),
                fill_rgb=colors["weight_fill"],
                outline_rgb=colors["line"],
                text_rgb=colors["text"],
                text_stroke_rgb=colors["stroke"],
                stroke_width=int(params.line_width_px),
                value_font_size_px=int(params.value_font_size_px),
            )
            entity_type = "balance_numeric_weight"
        entity = dict(item)
        entity.update(
            {
                "entity_id": item_id,
                "entity_type": entity_type,
                "bbox_px": list(item_bbox_map[item_id]),
            }
        )
        entities.append(entity)


def _draw_scale_panel(
    draw: ImageDraw.ImageDraw,
    *,
    panel: Mapping[str, Any],
    panel_bbox: Sequence[float],
    colors: Mapping[str, Tuple[int, int, int]],
    object_specs: Mapping[str, Mapping[str, Any]],
    item_bbox_map: Dict[str, List[float]],
    entities: List[Dict[str, Any]],
    params: BalanceScaleRenderParams,
    target_label: str,
    highlight_target: bool,
) -> None:
    left, top, right, bottom = [float(value) for value in panel_bbox]
    pad = float(params.panel_padding_px)
    width = right - left
    scale_cx = 0.5 * (left + right)
    beam_y = top + 0.42 * (bottom - top)
    left_x = left + 0.30 * width
    right_x = left + 0.70 * width
    beam_half = min(0.5 * float(params.beam_width_px), 0.42 * width)
    pan_y = top + 0.68 * (bottom - top)
    pan_w = min(float(params.pan_width_px), 0.32 * width)
    pan_h = float(params.pan_height_px)
    line_width = max(2, int(params.line_width_px))
    left_total = int(panel.get("left_total", 0))
    right_total = int(panel.get("right_total", 0))
    tilt_px = 0.0
    if left_total != right_total:
        tilt_px = min(28.0, max(18.0, 0.13 * (bottom - top)))
    left_offset = tilt_px if left_total > right_total else -tilt_px if left_total < right_total else 0.0
    right_offset = -left_offset

    title = str(panel.get("panel_label", ""))
    if title:
        draw_centered_text(
            draw,
            text=title,
            center=(left + pad + 36, top + pad * 0.75),
            font=load_font(max(12, int(0.75 * params.label_font_size_px)), bold=True),
            fill=colors["muted_text"],
            stroke_fill=colors["stroke"],
            stroke_width=1,
        )

    beam_left = (scale_cx - beam_half, beam_y + left_offset)
    beam_right = (scale_cx + beam_half, beam_y + right_offset)
    draw.line([beam_left, beam_right], fill=colors["line"], width=line_width)
    draw.polygon(
        [
            (scale_cx, beam_y + 8),
            (scale_cx - 28, beam_y + 72),
            (scale_cx + 28, beam_y + 72),
        ],
        fill=colors["stand_fill"],
        outline=colors["line"],
    )
    draw.line(
        [(scale_cx, beam_y + 70), (scale_cx, min(bottom - pad, beam_y + 92))],
        fill=colors["line"],
        width=line_width,
    )

    left_pan = (
        left_x - pan_w / 2.0,
        pan_y + left_offset - pan_h / 2.0,
        left_x + pan_w / 2.0,
        pan_y + left_offset + pan_h / 2.0,
    )
    right_pan = (
        right_x - pan_w / 2.0,
        pan_y + right_offset - pan_h / 2.0,
        right_x + pan_w / 2.0,
        pan_y + right_offset + pan_h / 2.0,
    )

    def _beam_y_at(x: float) -> float:
        beam_span = max(1.0, beam_right[0] - beam_left[0])
        t = (float(x) - beam_left[0]) / beam_span
        return beam_left[1] + t * (beam_right[1] - beam_left[1])

    for x, pan_bbox in ((left_x, left_pan), (right_x, right_pan)):
        draw.line([(x, _beam_y_at(x)), (x, pan_bbox[1])], fill=colors["line"], width=max(1, line_width - 1))
        draw_rounded_rect(
            draw,
            pan_bbox,
            radius=12,
            fill=colors["pan_fill"],
            outline=colors["line"],
            width=line_width,
        )

    _draw_pan_items(
        draw,
        items=panel["left_items"],
        pan_bbox=left_pan,
        colors=colors,
        object_specs=object_specs,
        item_bbox_map=item_bbox_map,
        entities=entities,
        params=params,
        target_label=target_label,
        highlight_target=highlight_target,
    )
    _draw_pan_items(
        draw,
        items=panel["right_items"],
        pan_bbox=right_pan,
        colors=colors,
        object_specs=object_specs,
        item_bbox_map=item_bbox_map,
        entities=entities,
        params=params,
        target_label=target_label,
        highlight_target=highlight_target,
    )

    panel_id = str(panel["panel_id"])
    item_bbox_map[panel_id] = round_bbox(panel_bbox)
    entities.append(
        {
            "entity_id": panel_id,
            "entity_type": "balance_scale_panel",
            "bbox_px": list(item_bbox_map[panel_id]),
            "left_total": int(panel["left_total"]),
            "right_total": int(panel["right_total"]),
            "is_balanced": bool(panel["left_total"] == panel["right_total"]),
            "balance_state": str(panel.get("balance_state", "balanced")),
            "heavier_side": str(panel.get("heavier_side", "none")),
        }
    )


def _draw_missing_weight_query_row(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: Mapping[str, Any],
    row_bbox: Sequence[float],
    colors: Mapping[str, Tuple[int, int, int]],
    item_bbox_map: Dict[str, List[float]],
    entities: List[Dict[str, Any]],
    params: BalanceScaleRenderParams,
) -> None:
    left, top, right, bottom = [float(value) for value in row_bbox]
    cx = 0.5 * (left + right)
    cy = 0.5 * (top + bottom)
    token_size = float(params.token_size_px) * 1.18
    gap = 34.0
    eq_w = 34.0
    q_w = token_size * 1.22
    total_w = token_size + gap + eq_w + gap + q_w
    token_left = cx - total_w / 2.0
    token_bbox = (token_left, cy - token_size / 2.0, token_left + token_size, cy + token_size / 2.0)
    eq_center_x = token_bbox[2] + gap + eq_w / 2.0
    q_left = eq_center_x + eq_w / 2.0 + gap
    question_bbox = (q_left, cy - token_size / 2.0, q_left + q_w, cy + token_size / 2.0)
    target_label = str(dataset["target_label"])
    object_spec = dataset["object_specs"][target_label]

    draw_centered_text(
        draw,
        text="Query",
        center=(left + 54, top + 0.5 * (bottom - top)),
        font=load_font(max(12, int(0.70 * params.label_font_size_px)), bold=True),
        fill=colors["muted_text"],
        stroke_fill=colors["stroke"],
        stroke_width=1,
    )
    _draw_object_token(
        draw,
        bbox=token_bbox,
        object_label=target_label,
        object_type=str(object_spec["object_type"]),
        fill_rgb=object_spec["fill_rgb"],
        outline_rgb=colors["line"],
        text_rgb=colors["text"],
        text_stroke_rgb=colors["stroke"],
        stroke_width=int(params.line_width_px),
        label_font_size_px=int(params.query_font_size_px),
        highlight_rgb=colors["mark"],
    )
    draw_centered_text(
        draw,
        text="=",
        center=(eq_center_x, cy),
        font=load_font(max(18, int(params.query_font_size_px * 1.05)), bold=True),
        fill=colors["text"],
        stroke_fill=colors["stroke"],
        stroke_width=1,
    )
    draw_rounded_rect(
        draw,
        question_bbox,
        radius=12,
        fill=colors["query_fill"],
        outline=colors["mark"],
        width=max(2, int(params.line_width_px) + 1),
    )
    draw_centered_text(
        draw,
        text="?",
        center=((question_bbox[0] + question_bbox[2]) * 0.5, cy),
        font=load_font(max(20, int(params.query_font_size_px * 1.15)), bold=True),
        fill=colors["text"],
        stroke_fill=colors["stroke"],
        stroke_width=1,
    )

    item_bbox_map["query_object"] = round_bbox(token_bbox)
    item_bbox_map["missing_value_box"] = round_bbox(question_bbox)
    entities.append(
        {
            "entity_id": "query_object",
            "entity_type": "balance_query_object",
            "object_label": target_label,
            "bbox_px": list(item_bbox_map["query_object"]),
        }
    )
    entities.append(
        {
            "entity_id": "missing_value_box",
            "entity_type": "balance_missing_value_box",
            "bbox_px": list(item_bbox_map["missing_value_box"]),
        }
    )


def _draw_equivalent_count_query_row(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: Mapping[str, Any],
    row_bbox: Sequence[float],
    colors: Mapping[str, Tuple[int, int, int]],
    item_bbox_map: Dict[str, List[float]],
    entities: List[Dict[str, Any]],
    params: BalanceScaleRenderParams,
) -> None:
    left, top, right, bottom = [float(value) for value in row_bbox]
    cx = 0.5 * (left + right)
    cy = 0.5 * (top + bottom)
    token_size = float(params.token_size_px) * 1.06
    gap = 24.0
    eq_w = 28.0
    mult_w = 28.0
    q_w = token_size * 1.10
    total_w = token_size + gap + eq_w + gap + q_w + gap + mult_w + gap + token_size
    source_left = cx - total_w / 2.0
    source_bbox = (source_left, cy - token_size / 2.0, source_left + token_size, cy + token_size / 2.0)
    eq_center_x = source_bbox[2] + gap + eq_w / 2.0
    question_left = eq_center_x + eq_w / 2.0 + gap
    question_bbox = (question_left, cy - token_size / 2.0, question_left + q_w, cy + token_size / 2.0)
    mult_center_x = question_bbox[2] + gap + mult_w / 2.0
    repeated_left = mult_center_x + mult_w / 2.0 + gap
    repeated_bbox = (repeated_left, cy - token_size / 2.0, repeated_left + token_size, cy + token_size / 2.0)
    source_label = str(dataset["source_label"])
    repeated_label = str(dataset["repeated_label"])
    source_spec = dataset["object_specs"][source_label]
    repeated_spec = dataset["object_specs"][repeated_label]

    draw_centered_text(
        draw,
        text="Query",
        center=(left + 54, top + 0.5 * (bottom - top)),
        font=load_font(max(12, int(0.70 * params.label_font_size_px)), bold=True),
        fill=colors["muted_text"],
        stroke_fill=colors["stroke"],
        stroke_width=1,
    )
    _draw_object_token(
        draw,
        bbox=source_bbox,
        object_label=source_label,
        object_type=str(source_spec["object_type"]),
        fill_rgb=source_spec["fill_rgb"],
        outline_rgb=colors["line"],
        text_rgb=colors["text"],
        text_stroke_rgb=colors["stroke"],
        stroke_width=int(params.line_width_px),
        label_font_size_px=int(params.query_font_size_px),
        highlight_rgb=colors["mark"],
    )
    draw_centered_text(
        draw,
        text="=",
        center=(eq_center_x, cy),
        font=load_font(max(18, int(params.query_font_size_px)), bold=True),
        fill=colors["text"],
        stroke_fill=colors["stroke"],
        stroke_width=1,
    )
    draw_rounded_rect(
        draw,
        question_bbox,
        radius=12,
        fill=colors["query_fill"],
        outline=colors["mark"],
        width=max(2, int(params.line_width_px) + 1),
    )
    draw_centered_text(
        draw,
        text="?",
        center=((question_bbox[0] + question_bbox[2]) * 0.5, cy),
        font=load_font(max(20, int(params.query_font_size_px * 1.05)), bold=True),
        fill=colors["text"],
        stroke_fill=colors["stroke"],
        stroke_width=1,
    )
    draw_centered_text(
        draw,
        text="x",
        center=(mult_center_x, cy),
        font=load_font(max(18, int(params.query_font_size_px * 0.92)), bold=True),
        fill=colors["text"],
        stroke_fill=colors["stroke"],
        stroke_width=1,
    )
    _draw_object_token(
        draw,
        bbox=repeated_bbox,
        object_label=repeated_label,
        object_type=str(repeated_spec["object_type"]),
        fill_rgb=repeated_spec["fill_rgb"],
        outline_rgb=colors["line"],
        text_rgb=colors["text"],
        text_stroke_rgb=colors["stroke"],
        stroke_width=int(params.line_width_px),
        label_font_size_px=int(params.query_font_size_px),
        highlight_rgb=colors["mark"],
    )

    item_bbox_map["source_object"] = round_bbox(source_bbox)
    item_bbox_map["repeated_object"] = round_bbox(repeated_bbox)
    item_bbox_map["missing_count_box"] = round_bbox(question_bbox)
    entities.append(
        {
            "entity_id": "source_object",
            "entity_type": "balance_query_source_object",
            "object_label": source_label,
            "bbox_px": list(item_bbox_map["source_object"]),
        }
    )
    entities.append(
        {
            "entity_id": "repeated_object",
            "entity_type": "balance_query_repeated_object",
            "object_label": repeated_label,
            "bbox_px": list(item_bbox_map["repeated_object"]),
        }
    )
    entities.append(
        {
            "entity_id": "missing_count_box",
            "entity_type": "balance_missing_count_box",
            "bbox_px": list(item_bbox_map["missing_count_box"]),
        }
    )


def _draw_weight_order_query_row(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: Mapping[str, Any],
    row_bbox: Sequence[float],
    colors: Mapping[str, Tuple[int, int, int]],
    item_bbox_map: Dict[str, List[float]],
    entities: List[Dict[str, Any]],
    params: BalanceScaleRenderParams,
) -> None:
    left, top, right, bottom = [float(value) for value in row_bbox]
    cy = 0.5 * (top + bottom)
    query_id = str(dataset["query_id"])
    query_text = "Heaviest?" if query_id == "heaviest_object_label" else "Lightest?"
    candidate_labels = [str(label) for label in dataset.get("candidate_labels", dataset["object_labels"])]
    token_size = float(params.token_size_px) * 1.02
    gap = max(18.0, float(params.token_gap_px) * 2.4)
    text_w = 150.0
    total_w = text_w + gap + len(candidate_labels) * token_size + max(0, len(candidate_labels) - 1) * gap
    start_x = 0.5 * (left + right - total_w)
    text_center_x = start_x + text_w / 2.0
    token_x = start_x + text_w + gap

    draw_centered_text(
        draw,
        text=query_text,
        center=(text_center_x, cy),
        font=load_font(max(16, int(params.query_font_size_px * 0.82)), bold=True),
        fill=colors["text"],
        stroke_fill=colors["stroke"],
        stroke_width=1,
    )

    for index, label in enumerate(candidate_labels):
        x0 = token_x + index * (token_size + gap)
        bbox = (x0, cy - token_size / 2.0, x0 + token_size, cy + token_size / 2.0)
        object_spec = dataset["object_specs"][label]
        _draw_object_token(
            draw,
            bbox=bbox,
            object_label=label,
            object_type=str(object_spec["object_type"]),
            fill_rgb=object_spec["fill_rgb"],
            outline_rgb=colors["line"],
            text_rgb=colors["text"],
            text_stroke_rgb=colors["stroke"],
            stroke_width=int(params.line_width_px),
            label_font_size_px=int(params.query_font_size_px),
            highlight_rgb=None,
        )
        item_id = f"candidate_{label}"
        item_bbox_map[item_id] = round_bbox(bbox)
        entities.append(
            {
                "entity_id": item_id,
                "entity_type": "balance_order_candidate_object",
                "object_label": label,
                "candidate_index": int(index),
                "bbox_px": list(item_bbox_map[item_id]),
            }
        )


def _draw_query_row(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: Mapping[str, Any],
    row_bbox: Sequence[float],
    colors: Mapping[str, Tuple[int, int, int]],
    item_bbox_map: Dict[str, List[float]],
    entities: List[Dict[str, Any]],
    params: BalanceScaleRenderParams,
) -> None:
    query_row_kind = str(dataset.get("query_row_kind", dataset.get("query_id", "")))
    if query_row_kind == "weight_order_label":
        _draw_weight_order_query_row(
            draw,
            dataset=dataset,
            row_bbox=row_bbox,
            colors=colors,
            item_bbox_map=item_bbox_map,
            entities=entities,
            params=params,
        )
        return
    if query_row_kind == "equivalent_object_count_value":
        _draw_equivalent_count_query_row(
            draw,
            dataset=dataset,
            row_bbox=row_bbox,
            colors=colors,
            item_bbox_map=item_bbox_map,
            entities=entities,
            params=params,
        )
        return
    _draw_missing_weight_query_row(
        draw,
        dataset=dataset,
        row_bbox=row_bbox,
        colors=colors,
        item_bbox_map=item_bbox_map,
        entities=entities,
        params=params,
    )


def render_balance_scale_scene(
    image: Image.Image,
    *,
    dataset: Mapping[str, Any],
    scene_variant: str,
    render_params: BalanceScaleRenderParams,
    scene_style: PuzzleSceneStyle,
) -> RenderedBalanceScaleScene:
    """Render a static balance-scale puzzle scene."""

    draw = ImageDraw.Draw(image)
    panel_bbox = _panel_bbox(render_params)
    item_bbox_map: Dict[str, List[float]] = {"diagram_panel": round_bbox(panel_bbox)}
    entities: List[Dict[str, Any]] = [
        {
            "entity_id": "diagram_panel",
            "entity_type": "balance_scale_scene",
            "bbox_px": list(item_bbox_map["diagram_panel"]),
            "scene_variant": str(scene_variant),
            "query_id": str(dataset["query_id"]),
        }
    ]
    colors = {
        "panel_fill": tuple(int(value) for value in scene_style.panel_fill_rgb),
        "line": tuple(int(value) for value in scene_style.panel_border_rgb),
        "text": tuple(int(value) for value in scene_style.text_rgb),
        "muted_text": tuple(int(value) for value in scene_style.grid_rgb),
        "stroke": tuple(int(value) for value in scene_style.text_stroke_rgb),
        "mark": tuple(int(value) for value in scene_style.mark_rgb),
        "pan_fill": tuple(int(value) for value in scene_style.option_fill_rgb),
        "weight_fill": tuple(int(value) for value in scene_style.step_fill_rgb),
        "stand_fill": tuple(int(value) for value in scene_style.panel_accent_rgb),
        "query_fill": tuple(int(value) for value in scene_style.option_fill_rgb),
    }
    if str(scene_variant) == "balance_outline":
        draw.rounded_rectangle(
            panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            outline=colors["line"],
            width=int(render_params.panel_border_width_px),
        )
    elif str(scene_variant) == "balance_card":
        draw_puzzle_panel_chrome(
            draw,
            bbox=tuple(int(round(value)) for value in panel_bbox),
            style=scene_style,
            radius=int(render_params.panel_corner_radius_px),
            border_width=int(render_params.panel_border_width_px),
        )
    else:
        draw_rounded_rect(
            draw,
            panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=colors["panel_fill"],
            outline=colors["line"],
            width=int(render_params.panel_border_width_px),
        )

    panels = [dict(panel) for panel in dataset["panels"]]
    gap = float(render_params.scale_panel_gap_px)
    inner_left = panel_bbox[0] + float(render_params.panel_padding_px)
    inner_right = panel_bbox[2] - float(render_params.panel_padding_px)
    inner_top = panel_bbox[1] + float(render_params.panel_padding_px)
    inner_bottom = panel_bbox[3] - float(render_params.panel_padding_px)
    query_h = float(render_params.query_row_height_px)
    available_h = inner_bottom - inner_top - query_h - gap * len(panels)
    scale_h = available_h / max(1, len(panels))
    y = inner_top
    highlight_target = str(dataset.get("target_cue_mode", "query_row_only")) == "query_row_and_highlight"
    for panel in panels:
        scale_bbox = (inner_left, y, inner_right, y + scale_h)
        _draw_scale_panel(
            draw,
            panel=panel,
            panel_bbox=scale_bbox,
            colors=colors,
            object_specs=dataset["object_specs"],
            item_bbox_map=item_bbox_map,
            entities=entities,
            params=render_params,
            target_label=str(dataset["target_label"]),
            highlight_target=highlight_target,
        )
        y += scale_h + gap
    query_bbox = (inner_left, y, inner_right, min(inner_bottom, y + query_h))
    _draw_query_row(
        draw,
        dataset=dataset,
        row_bbox=query_bbox,
        colors=colors,
        item_bbox_map=item_bbox_map,
        entities=entities,
        params=render_params,
    )
    item_bbox_map["query_row"] = round_bbox(query_bbox)
    entities.append(
        {
            "entity_id": "query_row",
            "entity_type": "balance_query_row",
            "bbox_px": list(item_bbox_map["query_row"]),
        }
    )
    return RenderedBalanceScaleScene(
        image=image,
        entities=entities,
        scene_bbox_px=round_bbox(panel_bbox),
        item_bbox_map={str(key): list(value) for key, value in item_bbox_map.items()},
    )


__all__ = [
    "BalanceScaleRenderParams",
    "RenderedBalanceScaleScene",
    "SUPPORTED_BALANCE_SCALE_SCENE_VARIANTS",
    "render_balance_scale_scene",
]
