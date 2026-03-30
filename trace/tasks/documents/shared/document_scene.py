"""Structured-document scene renderer shared across documents-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.drawing import draw_rounded_rect
from ...shared.text_rendering import fit_font_to_box, load_font
from .document_common import DocumentRenderParams


BBox = Tuple[float, float, float, float]

_SCENE_STYLE = {
    "form_sheet": {
        "accent_fill_rgb": (71, 127, 104),
        "accent_text_rgb": (255, 255, 255),
        "subtitle_text": "Structured entry fields",
    },
    "invoice_sheet": {
        "accent_fill_rgb": (69, 104, 157),
        "accent_text_rgb": (255, 255, 255),
        "subtitle_text": "Billing details",
    },
    "receipt_sheet": {
        "accent_fill_rgb": (120, 104, 86),
        "accent_text_rgb": (255, 255, 255),
        "subtitle_text": "Point of sale",
    },
}


@dataclass(frozen=True)
class RenderedDocumentScene:
    """Rendered structured-document scene plus traced witness geometry."""

    image: Image.Image
    entities: List[Dict[str, object]]
    page_bbox_px: List[float]
    title_bbox_px: List[float]
    section_label_bbox_map: Dict[str, List[float]]
    section_box_bbox_map: Dict[str, List[float]]
    field_label_bbox_map: Dict[str, List[float]]
    field_value_bbox_map: Dict[str, List[float]]
    field_box_bbox_map: Dict[str, List[float]]


@dataclass(frozen=True)
class RenderedDocumentSelectionScene:
    """Rendered document-selection scene plus traced checkbox geometry."""

    image: Image.Image
    entities: List[Dict[str, object]]
    page_bbox_px: List[float]
    title_bbox_px: List[float]
    section_label_bbox_map: Dict[str, List[float]]
    section_box_bbox_map: Dict[str, List[float]]
    field_label_bbox_map: Dict[str, List[float]]
    field_value_bbox_map: Dict[str, List[float]]
    field_box_bbox_map: Dict[str, List[float]]
    checkbox_bbox_map: Dict[str, List[float]]
    checkbox_label_bbox_map: Dict[str, List[float]]


def _round_bbox(bbox: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in bbox]


def _bbox_center(bbox: BBox) -> Tuple[float, float]:
    return (0.5 * float(bbox[0] + bbox[2]), 0.5 * float(bbox[1] + bbox[3]))


def _mix_rgb(left: Sequence[int], right: Sequence[int], ratio: float) -> Tuple[int, int, int]:
    """Return one linear RGB interpolation between two triples."""

    alpha = max(0.0, min(1.0, float(ratio)))
    return tuple(
        int(round((1.0 - alpha) * float(l_value) + alpha * float(r_value)))
        for l_value, r_value in zip(left, right)
    )


def _union_bboxes(boxes: Sequence[BBox]) -> BBox:
    """Return the tight union box over a non-empty sequence of boxes."""

    if not boxes:
        raise ValueError("expected at least one bbox when computing a union")
    return (
        min(float(box[0]) for box in boxes),
        min(float(box[1]) for box in boxes),
        max(float(box[2]) for box in boxes),
        max(float(box[3]) for box in boxes),
    )


def _draw_text_in_box(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: BBox,
    text: str,
    font_size_px: int,
    bold: bool,
    fill: Sequence[int],
    stroke_fill: Sequence[int],
    align: str,
    padding_px: int,
) -> List[float]:
    """Draw one fitted text string inside a box and return the rendered bbox."""

    left, top, right, bottom = [float(value) for value in bbox]
    width = max(1.0, float(right - left) - (2.0 * float(padding_px)))
    height = max(1.0, float(bottom - top) - (2.0 * float(padding_px)))
    font = fit_font_to_box(
        draw,
        text=str(text),
        max_width=float(width),
        max_height=float(height),
        bold=bool(bold),
        min_size_px=max(10, int(font_size_px * 0.65)),
        max_size_px=int(font_size_px),
        fill_ratio=0.98,
    )
    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=1)
    text_left, text_top, text_right, text_bottom = [float(value) for value in text_bbox]
    text_width = float(text_right - text_left)
    text_height = float(text_bottom - text_top)
    if str(align) == "right":
        origin_x = float(right - padding_px - text_right)
    elif str(align) == "center":
        origin_x = float(((left + right) * 0.5) - (0.5 * (text_left + text_right)))
    else:
        origin_x = float(left + padding_px - text_left)
    origin_y = float(((top + bottom) * 0.5) - (0.5 * (text_top + text_bottom)))
    draw.text(
        (float(origin_x), float(origin_y)),
        str(text),
        font=font,
        fill=tuple(int(value) for value in fill),
        stroke_width=1,
        stroke_fill=tuple(int(value) for value in stroke_fill),
    )
    return _round_bbox(
        [
            float(origin_x + text_left),
            float(origin_y + text_top),
            float(origin_x + text_right),
            float(origin_y + text_bottom),
        ]
    )


def _form_layout(page_bbox: BBox) -> List[BBox]:
    left, top, right, bottom = [float(value) for value in page_bbox]
    content_top = float(top + 128.0)
    inner_left = float(left + 44.0)
    inner_right = float(right - 44.0)
    field_gap = 24.0
    col_width = float((inner_right - inner_left - field_gap) / 2.0)
    row_height = 108.0
    row_gap = 18.0
    boxes: List[BBox] = []
    for row_index in range(4):
        row_top = float(content_top + row_index * (row_height + row_gap))
        for col_index in range(2):
            col_left = float(inner_left + col_index * (col_width + field_gap))
            boxes.append((col_left, row_top, col_left + col_width, row_top + row_height))
    final_top = float(content_top + 4 * (row_height + row_gap))
    boxes.append((inner_left, final_top, inner_right, final_top + row_height))
    return boxes


def _invoice_layout(page_bbox: BBox) -> List[BBox]:
    left, top, right, bottom = [float(value) for value in page_bbox]
    content_top = float(top + 126.0)
    inner_left = float(left + 40.0)
    inner_right = float(right - 40.0)
    field_gap = 22.0
    half_width = float((inner_right - inner_left - field_gap) / 2.0)
    third_gap = 16.0
    third_width = float((inner_right - inner_left - 2.0 * third_gap) / 3.0)
    row_height = 98.0
    summary_height = 104.0
    boxes = [
        (inner_left, content_top, inner_left + half_width, content_top + row_height),
        (inner_left + half_width + field_gap, content_top, inner_right, content_top + row_height),
    ]
    row_two_top = float(content_top + row_height + 18.0)
    for col_index in range(3):
        col_left = float(inner_left + col_index * (third_width + third_gap))
        boxes.append((col_left, row_two_top, col_left + third_width, row_two_top + row_height))
    row_three_top = float(row_two_top + row_height + 18.0)
    for col_index in range(2):
        col_left = float(inner_left + col_index * (half_width + field_gap))
        boxes.append((col_left, row_three_top, col_left + half_width, row_three_top + row_height))
    row_four_top = float(row_three_top + row_height + 18.0)
    for col_index in range(2):
        col_left = float(inner_left + col_index * (half_width + field_gap))
        boxes.append((col_left, row_four_top, col_left + half_width, row_four_top + row_height))
    summary_top = float(row_four_top + row_height + 20.0)
    for col_index in range(2):
        col_left = float(inner_left + col_index * (half_width + field_gap))
        boxes.append((col_left, summary_top, col_left + half_width, summary_top + summary_height))
    return boxes


def _receipt_layout(page_bbox: BBox) -> List[BBox]:
    left, top, right, bottom = [float(value) for value in page_bbox]
    content_top = float(top + 112.0)
    row_height = 60.0
    row_gap = 10.0
    inner_left = float(left + 26.0)
    inner_right = float(right - 26.0)
    boxes: List[BBox] = []
    for row_index in range(9):
        row_top = float(content_top + row_index * (row_height + row_gap))
        boxes.append((inner_left, row_top, inner_right, row_top + row_height))
    return boxes


def _split_label_value_boxes(field_box: BBox, *, scene_variant: str) -> Tuple[BBox, BBox]:
    left, top, right, bottom = [float(value) for value in field_box]
    if str(scene_variant) == "receipt_sheet":
        label_box = (left + 8.0, top + 8.0, left + 0.42 * (right - left), bottom - 8.0)
        value_box = (left + 0.44 * (right - left), top + 8.0, right - 8.0, bottom - 8.0)
        return label_box, value_box
    label_box = (left + 14.0, top + 10.0, right - 14.0, top + 36.0)
    value_box = (left + 14.0, top + 38.0, right - 14.0, bottom - 14.0)
    return label_box, value_box


def _render_field_boxes(
    draw: ImageDraw.ImageDraw,
    *,
    field_specs: Sequence[Mapping[str, str]],
    field_boxes: Sequence[BBox],
    scene_variant: str,
    render_params: DocumentRenderParams,
    entities: List[Dict[str, object]],
) -> Tuple[Dict[str, List[float]], Dict[str, List[float]], Dict[str, List[float]]]:
    """Render one ordered sequence of label/value field boxes and trace their bboxes."""

    field_label_bbox_map: Dict[str, List[float]] = {}
    field_value_bbox_map: Dict[str, List[float]] = {}
    field_box_bbox_map: Dict[str, List[float]] = {}
    for field_spec, field_box in zip(field_specs, field_boxes):
        field_id = str(field_spec["field_id"])
        field_box_bbox_map[field_id] = _round_bbox(field_box)
        if str(scene_variant) != "receipt_sheet":
            draw_rounded_rect(
                draw,
                field_box,
                radius=int(render_params.field_corner_radius_px),
                fill=render_params.field_fill_rgb,
                outline=render_params.field_outline_rgb,
                width=int(render_params.field_outline_width_px),
            )
        else:
            draw.line(
                [(field_box[0], field_box[3]), (field_box[2], field_box[3])],
                fill=tuple(int(value) for value in render_params.divider_rgb),
                width=1,
            )
        label_box, value_box = _split_label_value_boxes(field_box, scene_variant=str(scene_variant))
        label_bbox_px = _draw_text_in_box(
            draw,
            bbox=label_box,
            text=str(field_spec["field_label"]),
            font_size_px=int(render_params.label_font_size_px),
            bold=True,
            fill=render_params.label_fill_rgb,
            stroke_fill=render_params.label_stroke_rgb,
            align="left",
            padding_px=2 if str(scene_variant) == "receipt_sheet" else 0,
        )
        value_bbox_px = _draw_text_in_box(
            draw,
            bbox=value_box,
            text=str(field_spec["field_value"]),
            font_size_px=int(render_params.value_font_size_px),
            bold=False,
            fill=render_params.value_fill_rgb,
            stroke_fill=render_params.label_stroke_rgb,
            align="right" if str(scene_variant) == "receipt_sheet" else "left",
            padding_px=2 if str(scene_variant) == "receipt_sheet" else 0,
        )
        field_label_bbox_map[str(field_spec["label_bbox_id"])] = list(label_bbox_px)
        field_value_bbox_map[str(field_spec["value_bbox_id"])] = list(value_bbox_px)
        entities.extend(
            [
                {
                    "entity_id": f"{field_id}:field",
                    "entity_type": "document_field_box",
                    "bbox_id": field_id,
                    "bbox_px": _round_bbox(field_box),
                    "field_id": field_id,
                },
                {
                    "entity_id": f"{field_id}:label",
                    "entity_type": "document_field_label",
                    "bbox_id": str(field_spec["label_bbox_id"]),
                    "bbox_px": list(label_bbox_px),
                    "field_id": field_id,
                    "text": str(field_spec["field_label"]),
                },
                {
                    "entity_id": f"{field_id}:value",
                    "entity_type": "document_field_value",
                    "bbox_id": str(field_spec["value_bbox_id"]),
                    "bbox_px": list(value_bbox_px),
                    "field_id": field_id,
                    "text": str(field_spec["field_value"]),
                },
            ]
        )
    return field_label_bbox_map, field_value_bbox_map, field_box_bbox_map


def _form_selection_layout(page_bbox: BBox) -> Tuple[List[BBox], List[List[BBox]]]:
    """Return context-field boxes plus checkbox-row boxes for the form variant."""

    left, top, right, bottom = [float(value) for value in page_bbox]
    inner_left = float(left + 44.0)
    inner_right = float(right - 44.0)
    content_top = float(top + 126.0)
    field_gap = 24.0
    context_width = float((inner_right - inner_left - field_gap) / 2.0)
    context_height = 74.0
    context_row_gap = 14.0
    context_boxes: List[BBox] = []
    for row_index in range(2):
        row_top = float(content_top + row_index * (context_height + context_row_gap))
        for col_index in range(2):
            col_left = float(inner_left + col_index * (context_width + field_gap))
            context_boxes.append((col_left, row_top, col_left + context_width, row_top + context_height))
    section_width = float(inner_right - inner_left)
    row_height = 42.0
    row_gap = 8.0
    section_top = float(content_top + 2.0 * (context_height + context_row_gap) + 24.0)
    section_boxes: List[List[BBox]] = []
    for section_index in range(2):
        top_y = float(section_top + section_index * (4.0 * row_height + 3.0 * row_gap + 28.0))
        rows = []
        for row_index in range(4):
            row_top = float(top_y + row_index * (row_height + row_gap))
            rows.append((inner_left, row_top, inner_left + section_width, row_top + row_height))
        section_boxes.append(rows)
    return context_boxes, section_boxes


def _invoice_selection_layout(page_bbox: BBox) -> Tuple[List[BBox], List[List[BBox]]]:
    """Return context-field boxes plus checkbox-row boxes for the invoice variant."""

    left, top, right, bottom = [float(value) for value in page_bbox]
    inner_left = float(left + 40.0)
    inner_right = float(right - 40.0)
    content_top = float(top + 124.0)
    gap = 18.0
    third_width = float((inner_right - inner_left - 2.0 * gap) / 3.0)
    context_height = 82.0
    context_boxes = []
    for index in range(3):
        box_left = float(inner_left + index * (third_width + gap))
        context_boxes.append((box_left, content_top, box_left + third_width, content_top + context_height))
    section_top = float(content_top + context_height + 28.0)
    section_gap = 24.0
    section_width = float((inner_right - inner_left - section_gap) / 2.0)
    row_height = 46.0
    row_gap = 10.0
    section_boxes: List[List[BBox]] = []
    for section_index in range(2):
        section_left = float(inner_left + section_index * (section_width + section_gap))
        rows = []
        for row_index in range(4):
            row_top = float(section_top + row_index * (row_height + row_gap))
            rows.append((section_left, row_top, section_left + section_width, row_top + row_height))
        section_boxes.append(rows)
    return context_boxes, section_boxes


def _receipt_selection_layout(page_bbox: BBox) -> Tuple[List[BBox], List[List[BBox]]]:
    """Return context-field boxes plus checkbox-row boxes for the receipt variant."""

    left, top, right, bottom = [float(value) for value in page_bbox]
    inner_left = float(left + 26.0)
    inner_right = float(right - 26.0)
    content_top = float(top + 112.0)
    context_height = 56.0
    context_gap = 8.0
    context_boxes = []
    for index in range(3):
        row_top = float(content_top + index * (context_height + context_gap))
        context_boxes.append((inner_left, row_top, inner_right, row_top + context_height))
    section_top = float(content_top + 3.0 * (context_height + context_gap) + 20.0)
    row_height = 40.0
    row_gap = 8.0
    section_gap = 48.0
    section_boxes: List[List[BBox]] = []
    for section_index in range(2):
        top_y = float(section_top + section_index * (4.0 * row_height + 3.0 * row_gap + section_gap))
        rows = []
        for row_index in range(4):
            row_top = float(top_y + row_index * (row_height + row_gap))
            rows.append((inner_left, row_top, inner_right, row_top + row_height))
        section_boxes.append(rows)
    return context_boxes, section_boxes


def _draw_checkbox_mark(
    draw: ImageDraw.ImageDraw,
    *,
    checkbox_box: BBox,
    checked: bool,
    accent_rgb: Sequence[int],
    render_params: DocumentRenderParams,
) -> None:
    """Draw one checked or unchecked checkbox square."""

    fill = tuple(int(value) for value in render_params.field_fill_rgb)
    outline = tuple(int(value) for value in render_params.field_outline_rgb)
    if bool(checked):
        fill = tuple(int(value) for value in accent_rgb)
        outline = tuple(int(value) for value in accent_rgb)
    draw_rounded_rect(
        draw,
        checkbox_box,
        radius=6,
        fill=fill,
        outline=outline,
        width=2,
    )
    if not bool(checked):
        return
    left, top, right, bottom = [float(value) for value in checkbox_box]
    draw.line(
        [
            (left + 6.0, top + 0.55 * (bottom - top)),
            (left + 0.42 * (right - left), bottom - 6.0),
            (right - 6.0, top + 6.0),
        ],
        fill=(255, 255, 255),
        width=3,
        joint="curve",
    )


def _page_bbox(scene_variant: str, render_params: DocumentRenderParams) -> BBox:
    canvas_width = float(render_params.canvas_width)
    canvas_height = float(render_params.canvas_height)
    if str(scene_variant) == "receipt_sheet":
        page_width = float(render_params.receipt_page_width_px)
        page_height = float(render_params.receipt_page_height_px)
    else:
        page_width = float(render_params.sheet_page_width_px)
        page_height = float(render_params.sheet_page_height_px)
    left = float((canvas_width - page_width) * 0.5)
    top = float((canvas_height - page_height) * 0.5)
    return (left, top, left + page_width, top + page_height)


def render_document_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    geometry_seed: int,
    scene_title: str,
    field_specs: Sequence[Mapping[str, str]],
    render_params: DocumentRenderParams,
    section_specs: Sequence[Mapping[str, object]] | None = None,
) -> RenderedDocumentScene:
    """Render one structured document scene and trace field/text bboxes."""

    del geometry_seed
    image = background.copy().convert("RGB")
    draw = ImageDraw.Draw(image)
    style = dict(_SCENE_STYLE[str(scene_variant)])

    page_bbox = _page_bbox(str(scene_variant), render_params)
    shadow_bbox = (
        float(page_bbox[0] + render_params.page_shadow_offset_px),
        float(page_bbox[1] + render_params.page_shadow_offset_px),
        float(page_bbox[2] + render_params.page_shadow_offset_px),
        float(page_bbox[3] + render_params.page_shadow_offset_px),
    )
    draw_rounded_rect(
        draw,
        shadow_bbox,
        radius=int(render_params.page_corner_radius_px),
        fill=render_params.page_shadow_rgb,
        outline=render_params.page_shadow_rgb,
        width=0,
    )
    draw_rounded_rect(
        draw,
        page_bbox,
        radius=int(render_params.page_corner_radius_px),
        fill=render_params.page_fill_rgb,
        outline=render_params.page_outline_rgb,
        width=int(render_params.page_outline_width_px),
    )

    title_band_bbox = (
        float(page_bbox[0]),
        float(page_bbox[1]),
        float(page_bbox[2]),
        float(page_bbox[1] + 84.0),
    )
    draw_rounded_rect(
        draw,
        title_band_bbox,
        radius=int(render_params.page_corner_radius_px),
        fill=tuple(int(value) for value in style["accent_fill_rgb"]),
        outline=tuple(int(value) for value in style["accent_fill_rgb"]),
        width=0,
    )
    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    title_bbox = draw.textbbox((0, 0), str(scene_title), font=title_font, stroke_width=1)
    title_width = float(title_bbox[2] - title_bbox[0])
    title_height = float(title_bbox[3] - title_bbox[1])
    title_origin = (
        float(page_bbox[0] + 32.0),
        float(page_bbox[1] + 0.5 * (84.0 - title_height) - title_bbox[1]),
    )
    draw.text(
        title_origin,
        str(scene_title),
        font=title_font,
        fill=tuple(int(value) for value in style["accent_text_rgb"]),
        stroke_width=1,
        stroke_fill=tuple(int(value) for value in render_params.page_fill_rgb),
    )
    title_bbox_px = _round_bbox(
        [
            float(title_origin[0] + title_bbox[0]),
            float(title_origin[1] + title_bbox[1]),
            float(title_origin[0] + title_bbox[2]),
            float(title_origin[1] + title_bbox[3]),
        ]
    )

    subtitle_font = load_font(int(render_params.section_font_size_px), bold=False)
    subtitle_bbox = draw.textbbox((0, 0), str(style["subtitle_text"]), font=subtitle_font, stroke_width=1)
    subtitle_origin = (
        float(page_bbox[2] - 32.0 - (subtitle_bbox[2] - subtitle_bbox[0])),
        float(page_bbox[1] + 0.5 * (84.0 - (subtitle_bbox[3] - subtitle_bbox[1])) - subtitle_bbox[1]),
    )
    draw.text(
        subtitle_origin,
        str(style["subtitle_text"]),
        font=subtitle_font,
        fill=tuple(int(value) for value in style["accent_text_rgb"]),
        stroke_width=1,
        stroke_fill=tuple(int(value) for value in render_params.page_fill_rgb),
    )
    subtitle_bbox_px = _round_bbox(
        [
            float(subtitle_origin[0] + subtitle_bbox[0]),
            float(subtitle_origin[1] + subtitle_bbox[1]),
            float(subtitle_origin[0] + subtitle_bbox[2]),
            float(subtitle_origin[1] + subtitle_bbox[3]),
        ]
    )

    if str(scene_variant) == "form_sheet":
        field_boxes = _form_layout(page_bbox)
    elif str(scene_variant) == "invoice_sheet":
        field_boxes = _invoice_layout(page_bbox)
    else:
        field_boxes = _receipt_layout(page_bbox)
    if len(field_boxes) != len(field_specs):
        raise ValueError(
            f"scene_variant='{scene_variant}' expected {len(field_boxes)} fields, got {len(field_specs)}"
        )

    entities: List[Dict[str, object]] = [
        {
            "entity_id": "page",
            "entity_type": "document_page",
            "bbox_id": "page",
            "bbox_px": _round_bbox(page_bbox),
        },
        {
            "entity_id": "title",
            "entity_type": "document_title",
            "bbox_id": "title",
            "bbox_px": list(title_bbox_px),
            "text": str(scene_title),
        },
    ]
    section_label_bbox_map: Dict[str, List[float]] = {}
    section_box_bbox_map: Dict[str, List[float]] = {}
    field_label_bbox_map: Dict[str, List[float]] = {}
    field_value_bbox_map: Dict[str, List[float]] = {}
    field_box_bbox_map: Dict[str, List[float]] = {}
    pending_section_headers: List[Dict[str, object]] = []
    field_box_lookup = {
        str(field_spec["field_id"]): field_box
        for field_spec, field_box in zip(field_specs, field_boxes)
    }

    if section_specs:
        section_font = load_font(max(15, int(render_params.section_font_size_px) - 2), bold=True)
        section_outline_rgb = _mix_rgb(render_params.divider_rgb, style["accent_fill_rgb"], 0.30)
        section_fill_rgb = _mix_rgb(render_params.page_fill_rgb, style["accent_fill_rgb"], 0.08)
        title_content_bottom = max(float(title_bbox_px[3]), float(subtitle_bbox_px[3]))
        title_band_bottom = float(max(float(page_bbox[1] + 56.0), title_content_bottom + 12.0))
        for section_spec in section_specs:
            section_id = str(section_spec["section_id"])
            member_ids = [str(field_id) for field_id in section_spec["field_ids"]]
            member_boxes = [field_box_lookup[field_id] for field_id in member_ids if field_id in field_box_lookup]
            if not member_boxes:
                continue
            union_box = _union_bboxes(member_boxes)
            header_band_top = max(float(title_band_bottom + 8.0), float(union_box[1] - 36.0))
            container_box = (
                float(union_box[0] - 12.0),
                float(header_band_top),
                float(union_box[2] + 12.0),
                float(union_box[3] + 12.0),
            )
            draw_rounded_rect(
                draw,
                container_box,
                radius=max(12, int(render_params.field_corner_radius_px)),
                fill=section_fill_rgb,
                outline=section_outline_rgb,
                width=1,
            )
            section_box_bbox_map[section_id] = _round_bbox(container_box)
            pending_section_headers.append(
                {
                    "section_id": section_id,
                    "section_label": str(section_spec["section_label"]),
                    "member_ids": list(member_ids),
                    "container_box": container_box,
                    "union_box": union_box,
                    "font": section_font,
                }
            )
            entities.append(
                {
                    "entity_id": f"{section_id}:section",
                    "entity_type": "document_section",
                    "bbox_id": section_id,
                    "bbox_px": list(section_box_bbox_map[section_id]),
                    "section_id": section_id,
                    "field_ids": list(member_ids),
                }
            )

    field_label_bbox_map, field_value_bbox_map, field_box_bbox_map = _render_field_boxes(
        draw,
        field_specs=field_specs,
        field_boxes=field_boxes,
        scene_variant=str(scene_variant),
        render_params=render_params,
        entities=entities,
    )

    for section_header in pending_section_headers:
        section_id = str(section_header["section_id"])
        section_label = str(section_header["section_label"])
        container_box = tuple(float(value) for value in section_header["container_box"])
        union_box = tuple(float(value) for value in section_header["union_box"])
        text_bbox = draw.textbbox((0, 0), section_label, font=section_header["font"], stroke_width=1)
        pill_padding_x = 12.0
        available_top = float(container_box[1] + 6.0)
        available_bottom = float(union_box[1] - 8.0)
        pill_height = max(18.0, min(30.0, float(available_bottom - available_top)))
        pill_width = min(
            float(container_box[2] - container_box[0] - 32.0),
            float((text_bbox[2] - text_bbox[0]) + 2.0 * pill_padding_x),
        )
        pill_left = float(container_box[0] + 16.0)
        pill_top = float(max(available_top, available_bottom - pill_height - 2.0))
        pill_box = (
            pill_left,
            pill_top,
            float(pill_left + pill_width),
            float(pill_top + pill_height),
        )
        draw_rounded_rect(
            draw,
            pill_box,
            radius=max(10, int(render_params.field_corner_radius_px) - 2),
            fill=tuple(int(value) for value in style["accent_fill_rgb"]),
            outline=tuple(int(value) for value in style["accent_fill_rgb"]),
            width=1,
        )
        label_bbox_px = _draw_text_in_box(
            draw,
            bbox=pill_box,
            text=section_label,
            font_size_px=max(15, int(render_params.section_font_size_px) - 5),
            bold=True,
            fill=tuple(int(value) for value in style["accent_text_rgb"]),
            stroke_fill=tuple(int(value) for value in style["accent_fill_rgb"]),
            align="center",
            padding_px=4,
        )
        section_label_bbox_map[section_id] = _round_bbox(pill_box)
        entities.append(
            {
                "entity_id": f"{section_id}:label",
                "entity_type": "document_section_label",
                "bbox_id": f"{section_id}:label",
                "bbox_px": list(section_label_bbox_map[section_id]),
                "section_id": section_id,
                "text": section_label,
            }
        )

    return RenderedDocumentScene(
        image=image,
        entities=entities,
        page_bbox_px=_round_bbox(page_bbox),
        title_bbox_px=list(title_bbox_px),
        section_label_bbox_map=section_label_bbox_map,
        section_box_bbox_map=section_box_bbox_map,
        field_label_bbox_map=field_label_bbox_map,
        field_value_bbox_map=field_value_bbox_map,
        field_box_bbox_map=field_box_bbox_map,
    )


def render_document_selection_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    geometry_seed: int,
    scene_title: str,
    context_field_specs: Sequence[Mapping[str, str]],
    checkbox_section_specs: Sequence[Mapping[str, object]],
    render_params: DocumentRenderParams,
) -> RenderedDocumentSelectionScene:
    """Render one structured document scene with checkbox sections."""

    del geometry_seed
    image = background.copy().convert("RGB")
    draw = ImageDraw.Draw(image)
    style = dict(_SCENE_STYLE[str(scene_variant)])

    page_bbox = _page_bbox(str(scene_variant), render_params)
    shadow_bbox = (
        float(page_bbox[0] + render_params.page_shadow_offset_px),
        float(page_bbox[1] + render_params.page_shadow_offset_px),
        float(page_bbox[2] + render_params.page_shadow_offset_px),
        float(page_bbox[3] + render_params.page_shadow_offset_px),
    )
    draw_rounded_rect(
        draw,
        shadow_bbox,
        radius=int(render_params.page_corner_radius_px),
        fill=render_params.page_shadow_rgb,
        outline=render_params.page_shadow_rgb,
        width=0,
    )
    draw_rounded_rect(
        draw,
        page_bbox,
        radius=int(render_params.page_corner_radius_px),
        fill=render_params.page_fill_rgb,
        outline=render_params.page_outline_rgb,
        width=int(render_params.page_outline_width_px),
    )
    title_band_bbox = (
        float(page_bbox[0]),
        float(page_bbox[1]),
        float(page_bbox[2]),
        float(page_bbox[1] + 84.0),
    )
    draw_rounded_rect(
        draw,
        title_band_bbox,
        radius=int(render_params.page_corner_radius_px),
        fill=tuple(int(value) for value in style["accent_fill_rgb"]),
        outline=tuple(int(value) for value in style["accent_fill_rgb"]),
        width=0,
    )
    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    title_bbox = draw.textbbox((0, 0), str(scene_title), font=title_font, stroke_width=1)
    title_height = float(title_bbox[3] - title_bbox[1])
    title_origin = (
        float(page_bbox[0] + 32.0),
        float(page_bbox[1] + 0.5 * (84.0 - title_height) - title_bbox[1]),
    )
    draw.text(
        title_origin,
        str(scene_title),
        font=title_font,
        fill=tuple(int(value) for value in style["accent_text_rgb"]),
        stroke_width=1,
        stroke_fill=tuple(int(value) for value in render_params.page_fill_rgb),
    )
    title_bbox_px = _round_bbox(
        [
            float(title_origin[0] + title_bbox[0]),
            float(title_origin[1] + title_bbox[1]),
            float(title_origin[0] + title_bbox[2]),
            float(title_origin[1] + title_bbox[3]),
        ]
    )

    subtitle_font = load_font(int(render_params.section_font_size_px), bold=False)
    subtitle_text = str(style["subtitle_text"])
    if str(scene_variant) == "form_sheet":
        subtitle_text = "Selections and preferences"
    elif str(scene_variant) == "invoice_sheet":
        subtitle_text = "Delivery and billing flags"
    elif str(scene_variant) == "receipt_sheet":
        subtitle_text = "Selections and follow-up"
    subtitle_bbox_px: List[float] | None = None
    if str(scene_variant) != "receipt_sheet":
        subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=subtitle_font, stroke_width=1)
        subtitle_origin = (
            float(page_bbox[2] - 32.0 - (subtitle_bbox[2] - subtitle_bbox[0])),
            float(page_bbox[1] + 0.5 * (84.0 - (subtitle_bbox[3] - subtitle_bbox[1])) - subtitle_bbox[1]),
        )
        draw.text(
            subtitle_origin,
            subtitle_text,
            font=subtitle_font,
            fill=tuple(int(value) for value in style["accent_text_rgb"]),
            stroke_width=1,
            stroke_fill=tuple(int(value) for value in render_params.page_fill_rgb),
        )
        subtitle_bbox_px = _round_bbox(
            [
                float(subtitle_origin[0] + subtitle_bbox[0]),
                float(subtitle_origin[1] + subtitle_bbox[1]),
                float(subtitle_origin[0] + subtitle_bbox[2]),
                float(subtitle_origin[1] + subtitle_bbox[3]),
            ]
        )

    if str(scene_variant) == "form_sheet":
        context_boxes, section_row_boxes = _form_selection_layout(page_bbox)
    elif str(scene_variant) == "invoice_sheet":
        context_boxes, section_row_boxes = _invoice_selection_layout(page_bbox)
    else:
        context_boxes, section_row_boxes = _receipt_selection_layout(page_bbox)
    if len(context_boxes) != len(context_field_specs):
        raise ValueError(
            f"scene_variant='{scene_variant}' expected {len(context_boxes)} context fields, got {len(context_field_specs)}"
        )
    if len(section_row_boxes) != len(checkbox_section_specs):
        raise ValueError(
            f"scene_variant='{scene_variant}' expected {len(section_row_boxes)} checkbox sections, got {len(checkbox_section_specs)}"
        )

    entities: List[Dict[str, object]] = [
        {
            "entity_id": "page",
            "entity_type": "document_page",
            "bbox_id": "page",
            "bbox_px": _round_bbox(page_bbox),
        },
        {
            "entity_id": "title",
            "entity_type": "document_title",
            "bbox_id": "title",
            "bbox_px": list(title_bbox_px),
            "text": str(scene_title),
        },
    ]
    field_label_bbox_map, field_value_bbox_map, field_box_bbox_map = _render_field_boxes(
        draw,
        field_specs=context_field_specs,
        field_boxes=context_boxes,
        scene_variant=str(scene_variant),
        render_params=render_params,
        entities=entities,
    )
    section_label_bbox_map: Dict[str, List[float]] = {}
    section_box_bbox_map: Dict[str, List[float]] = {}
    checkbox_bbox_map: Dict[str, List[float]] = {}
    checkbox_label_bbox_map: Dict[str, List[float]] = {}

    title_content_bottom = float(title_bbox_px[3])
    if subtitle_bbox_px is not None:
        title_content_bottom = max(title_content_bottom, float(subtitle_bbox_px[3]))
    title_band_bottom = float(max(float(page_bbox[1] + 56.0), title_content_bottom + 12.0))
    for section_spec, row_boxes in zip(checkbox_section_specs, section_row_boxes):
        section_id = str(section_spec["section_id"])
        section_label = str(section_spec["section_label"])
        items = list(section_spec["items"])
        if len(items) != len(row_boxes):
            raise ValueError(
                f"section '{section_id}' expected {len(row_boxes)} items, got {len(items)}"
            )
        union_box = _union_bboxes(row_boxes)
        header_band_top = max(float(title_band_bottom + 8.0), float(union_box[1] - 34.0))
        container_box = (
            float(union_box[0] - 12.0),
            float(header_band_top),
            float(union_box[2] + 12.0),
            float(union_box[3] + 12.0),
        )
        draw_rounded_rect(
            draw,
            container_box,
            radius=max(12, int(render_params.field_corner_radius_px)),
            fill=_mix_rgb(render_params.page_fill_rgb, style["accent_fill_rgb"], 0.08),
            outline=_mix_rgb(render_params.divider_rgb, style["accent_fill_rgb"], 0.30),
            width=1,
        )
        section_box_bbox_map[section_id] = _round_bbox(container_box)
        section_font = load_font(max(15, int(render_params.section_font_size_px) - 2), bold=True)
        text_bbox = draw.textbbox((0, 0), section_label, font=section_font, stroke_width=1)
        pill_left = float(container_box[0] + 16.0)
        available_top = float(container_box[1] + 6.0)
        available_bottom = float(union_box[1] - 6.0)
        pill_height = max(18.0, min(30.0, float(available_bottom - available_top)))
        pill_width = min(
            float(container_box[2] - container_box[0] - 32.0),
            float((text_bbox[2] - text_bbox[0]) + 24.0),
        )
        pill_top = float(max(available_top, available_bottom - pill_height))
        pill_box = (
            pill_left,
            pill_top,
            float(pill_left + pill_width),
            float(pill_top + pill_height),
        )
        draw_rounded_rect(
            draw,
            pill_box,
            radius=max(10, int(render_params.field_corner_radius_px) - 2),
            fill=tuple(int(value) for value in style["accent_fill_rgb"]),
            outline=tuple(int(value) for value in style["accent_fill_rgb"]),
            width=1,
        )
        label_bbox_px = _draw_text_in_box(
            draw,
            bbox=pill_box,
            text=section_label,
            font_size_px=max(15, int(render_params.section_font_size_px) - 5),
            bold=True,
            fill=tuple(int(value) for value in style["accent_text_rgb"]),
            stroke_fill=tuple(int(value) for value in style["accent_fill_rgb"]),
            align="center",
            padding_px=4,
        )
        section_label_bbox_map[section_id] = list(label_bbox_px)
        entities.extend(
            [
                {
                    "entity_id": f"{section_id}:section",
                    "entity_type": "document_section",
                    "bbox_id": section_id,
                    "bbox_px": list(section_box_bbox_map[section_id]),
                    "section_id": section_id,
                    "checkbox_ids": [str(item["item_id"]) for item in items],
                },
                {
                    "entity_id": f"{section_id}:label",
                    "entity_type": "document_section_label",
                    "bbox_id": f"{section_id}:label",
                    "bbox_px": list(label_bbox_px),
                    "section_id": section_id,
                    "text": section_label,
                },
            ]
        )
        for item_spec, row_box in zip(items, row_boxes):
            row_fill = render_params.field_fill_rgb if str(scene_variant) != "receipt_sheet" else render_params.page_fill_rgb
            if str(scene_variant) != "receipt_sheet":
                draw_rounded_rect(
                    draw,
                    row_box,
                    radius=max(10, int(render_params.field_corner_radius_px) - 2),
                    fill=row_fill,
                    outline=render_params.field_outline_rgb,
                    width=1,
                )
            else:
                draw.line(
                    [(row_box[0], row_box[3]), (row_box[2], row_box[3])],
                    fill=tuple(int(value) for value in render_params.divider_rgb),
                    width=1,
                )
            checkbox_left = float(row_box[0] + 14.0)
            checkbox_size = 24.0 if str(scene_variant) != "receipt_sheet" else 22.0
            checkbox_box = (
                checkbox_left,
                float(((row_box[1] + row_box[3]) * 0.5) - 0.5 * checkbox_size),
                float(checkbox_left + checkbox_size),
                float(((row_box[1] + row_box[3]) * 0.5) + 0.5 * checkbox_size),
            )
            _draw_checkbox_mark(
                draw,
                checkbox_box=checkbox_box,
                checked=bool(item_spec["checked"]),
                accent_rgb=style["accent_fill_rgb"],
                render_params=render_params,
            )
            label_box = (
                float(checkbox_box[2] + 12.0),
                float(row_box[1] + 4.0),
                float(row_box[2] - 12.0),
                float(row_box[3] - 4.0),
            )
            label_bbox_px = _draw_text_in_box(
                draw,
                bbox=label_box,
                text=str(item_spec["label"]),
                font_size_px=max(16, int(render_params.label_font_size_px) - 1),
                bold=False,
                fill=render_params.value_fill_rgb,
                stroke_fill=render_params.label_stroke_rgb,
                align="left",
                padding_px=0,
            )
            checkbox_bbox_id = str(item_spec["checkbox_bbox_id"])
            checkbox_label_bbox_id = str(item_spec["label_bbox_id"])
            checkbox_bbox_map[checkbox_bbox_id] = _round_bbox(checkbox_box)
            checkbox_label_bbox_map[checkbox_label_bbox_id] = list(label_bbox_px)
            entities.extend(
                [
                    {
                        "entity_id": f"{item_spec['item_id']}:checkbox",
                        "entity_type": "document_checkbox",
                        "bbox_id": checkbox_bbox_id,
                        "bbox_px": list(checkbox_bbox_map[checkbox_bbox_id]),
                        "item_id": str(item_spec["item_id"]),
                        "checked": bool(item_spec["checked"]),
                        "section_id": section_id,
                    },
                    {
                        "entity_id": f"{item_spec['item_id']}:label",
                        "entity_type": "document_checkbox_label",
                        "bbox_id": checkbox_label_bbox_id,
                        "bbox_px": list(label_bbox_px),
                        "item_id": str(item_spec["item_id"]),
                        "section_id": section_id,
                        "text": str(item_spec["label"]),
                    },
                ]
            )

    return RenderedDocumentSelectionScene(
        image=image,
        entities=entities,
        page_bbox_px=_round_bbox(page_bbox),
        title_bbox_px=list(title_bbox_px),
        section_label_bbox_map=section_label_bbox_map,
        section_box_bbox_map=section_box_bbox_map,
        field_label_bbox_map=field_label_bbox_map,
        field_value_bbox_map=field_value_bbox_map,
        field_box_bbox_map=field_box_bbox_map,
        checkbox_bbox_map=checkbox_bbox_map,
        checkbox_label_bbox_map=checkbox_label_bbox_map,
    )


__all__ = [
    "RenderedDocumentScene",
    "RenderedDocumentSelectionScene",
    "render_document_scene",
    "render_document_selection_scene",
]
