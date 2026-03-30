"""Numeric set-diagram scene renderer shared across diagrams-domain set tasks."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.drawing import draw_rounded_rect
from .common import draw_diagram_text_in_box, resolve_diagram_panel_geometry, round_diagram_bbox
from .set_common import SetRenderParams


BBox = Tuple[float, float, float, float]
SET_DIAGRAM_SUPERSAMPLE_SCALE = 2


@dataclass(frozen=True)
class RenderedSetScene:
    """Rendered numeric set scene plus traced region and number geometry."""

    image: Image.Image
    entities: List[Dict[str, object]]
    panel_bbox_px: List[float]
    title_bbox_px: List[float]
    region_bbox_map: Dict[str, List[float]]
    set_label_bbox_map: Dict[str, List[float]]
    number_bbox_map: Dict[str, List[float]]
    number_slot_bbox_map: Dict[str, List[float]]


def _scale_bbox(bbox: Sequence[float], *, scale: float) -> List[float]:
    """Scale one bbox from supersampled render space back to final pixels."""

    return [round(float(value) / float(scale), 3) for value in bbox]


def _scale_bbox_map(
    bbox_map: Mapping[str, Sequence[float]],
    *,
    scale: float,
) -> Dict[str, List[float]]:
    """Scale one keyed bbox map back to final pixels."""

    return {str(key): _scale_bbox(list(value), scale=scale) for key, value in bbox_map.items()}


def _scale_entities(
    entities: Sequence[Mapping[str, object]],
    *,
    scale: float,
) -> List[Dict[str, object]]:
    """Scale traced entity bboxes back to final pixels."""

    scaled: List[Dict[str, object]] = []
    for entity in entities:
        record = dict(entity)
        if "bbox_xyxy" in record:
            record["bbox_xyxy"] = _scale_bbox(record["bbox_xyxy"], scale=scale)
        scaled.append(record)
    return scaled


def _scale_render_params(
    render_params: SetRenderParams,
    *,
    scale: int,
) -> SetRenderParams:
    """Scale pixel-valued set render params for supersampled drawing."""

    return replace(
        render_params,
        canvas_width=int(render_params.canvas_width * scale),
        canvas_height=int(render_params.canvas_height * scale),
        outer_margin_px=int(render_params.outer_margin_px * scale),
        panel_padding_px=int(render_params.panel_padding_px * scale),
        panel_corner_radius_px=int(render_params.panel_corner_radius_px * scale),
        title_font_size_px=int(render_params.title_font_size_px * scale),
        title_band_height_px=int(render_params.title_band_height_px * scale),
        region_outline_width_px=max(1, int(render_params.region_outline_width_px * scale)),
        number_slot_width_px=int(render_params.number_slot_width_px * scale),
        number_slot_height_px=int(render_params.number_slot_height_px * scale),
        number_font_size_px=int(render_params.number_font_size_px * scale),
        set_label_width_px=int(render_params.set_label_width_px * scale),
        set_label_height_px=int(render_params.set_label_height_px * scale),
        set_label_font_size_px=int(render_params.set_label_font_size_px * scale),
    )


def _three_set_geometry(
    content_bbox: BBox,
    *,
    render_params: SetRenderParams,
) -> tuple[Dict[str, BBox], Dict[str, BBox], Dict[str, tuple[float, float]]]:
    """Resolve circle, label, and region-slot geometry for a 3-set numeric diagram."""

    left, top, right, bottom = [float(value) for value in content_bbox]
    width = float(right - left)
    height = float(bottom - top)
    unit_scale = float(render_params.number_slot_height_px) / 76.0
    circle_w = min(320.0 * unit_scale, 0.37 * width)
    circle_h = min(320.0 * unit_scale, 0.52 * height)
    center_a_x = float(left + 0.39 * width)
    center_b_x = float(left + 0.61 * width)
    center_c_x = float(0.5 * (center_a_x + center_b_x))
    center_a_y = float(top + 0.42 * height)
    center_b_y = float(top + 0.42 * height)
    center_c_y = float(top + 0.63 * height)
    circles = {
        "set_A_region": (
            center_a_x - (0.5 * circle_w),
            center_a_y - (0.5 * circle_h),
            center_a_x + (0.5 * circle_w),
            center_a_y + (0.5 * circle_h),
        ),
        "set_B_region": (
            center_b_x - (0.5 * circle_w),
            center_b_y - (0.5 * circle_h),
            center_b_x + (0.5 * circle_w),
            center_b_y + (0.5 * circle_h),
        ),
        "set_C_region": (
            center_c_x - (0.5 * circle_w),
            center_c_y - (0.5 * circle_h),
            center_c_x + (0.5 * circle_w),
            center_c_y + (0.5 * circle_h),
        ),
    }
    c_only_center_y = float(center_c_y + (118.0 * unit_scale))
    set_c_label_top = min(
        float(bottom - render_params.set_label_height_px),
        float(c_only_center_y + (0.5 * float(render_params.number_slot_height_px)) + (18.0 * unit_scale)),
    )
    half_label_width = 0.5 * float(render_params.set_label_width_px)
    label_boxes = {
        "set_A_label": (
            center_a_x - half_label_width,
            top + (8.0 * unit_scale),
            center_a_x + half_label_width,
            top + (8.0 * unit_scale) + float(render_params.set_label_height_px),
        ),
        "set_B_label": (
            center_b_x - half_label_width,
            top + (8.0 * unit_scale),
            center_b_x + half_label_width,
            top + (8.0 * unit_scale) + float(render_params.set_label_height_px),
        ),
        "set_C_label": (
            center_c_x - half_label_width,
            set_c_label_top,
            center_c_x + half_label_width,
            set_c_label_top + float(render_params.set_label_height_px),
        ),
    }
    slots = {
        "A_only": (float(center_a_x - (118.0 * unit_scale)), float(center_a_y - (22.0 * unit_scale))),
        "B_only": (float(center_b_x + (118.0 * unit_scale)), float(center_b_y - (22.0 * unit_scale))),
        "C_only": (float(center_c_x), float(c_only_center_y)),
        "AB_only": (float(0.5 * (center_a_x + center_b_x)), float(center_a_y - (64.0 * unit_scale))),
        # Keep the lower side overlaps visibly inside their lenses instead of drifting
        # toward the bottom-only region, and raise the center overlap to preserve
        # separation between the three lower regions.
        "AC_only": (float(center_c_x - (108.0 * unit_scale)), float(center_c_y - (4.0 * unit_scale))),
        "BC_only": (float(center_c_x + (108.0 * unit_scale)), float(center_c_y - (4.0 * unit_scale))),
        "ABC": (float(center_c_x), float(center_c_y - (68.0 * unit_scale))),
    }
    return circles, label_boxes, slots


def _number_slot_bbox(center: tuple[float, float], *, render_params: SetRenderParams) -> BBox:
    """Resolve one number-slot bbox from its center."""

    cx, cy = float(center[0]), float(center[1])
    half_w = 0.5 * float(render_params.number_slot_width_px)
    half_h = 0.5 * float(render_params.number_slot_height_px)
    return (cx - half_w, cy - half_h, cx + half_w, cy + half_h)


def _render_set_scene_base(
    background: Image.Image,
    *,
    scene_title: str,
    set_ids: Sequence[str],
    number_specs: Sequence[Mapping[str, object]],
    set_fill_rgb_map: Mapping[str, Sequence[int]],
    render_params: SetRenderParams,
) -> RenderedSetScene:
    """Render one numeric 3-set overlap diagram at the current working resolution."""

    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    entities: List[Dict[str, object]] = []
    region_bbox_map: Dict[str, List[float]] = {}
    set_label_bbox_map: Dict[str, List[float]] = {}
    number_bbox_map: Dict[str, List[float]] = {}
    number_slot_bbox_map: Dict[str, List[float]] = {}

    panel_bbox, title_bbox, content_bbox = resolve_diagram_panel_geometry(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        outer_margin_px=int(render_params.outer_margin_px),
        title_band_height_px=int(render_params.title_band_height_px),
        panel_padding_px=int(render_params.panel_padding_px),
    )
    draw_rounded_rect(
        draw,
        panel_bbox,
        radius=int(render_params.panel_corner_radius_px),
        fill=render_params.panel_fill_rgb,
        outline=render_params.panel_border_rgb,
        width=2,
    )
    title_text_bbox = draw_diagram_text_in_box(
        draw,
        bbox=title_bbox,
        text=str(scene_title),
        font_size_px=int(render_params.title_font_size_px),
        bold=True,
        fill=render_params.title_color_rgb,
        stroke_fill=render_params.panel_fill_rgb,
        padding_px=12,
    )
    entities.append(
        {
            "entity_id": "diagram_panel",
            "entity_type": "diagram_panel",
            "bbox_xyxy": round_diagram_bbox(panel_bbox),
        }
    )
    entities.append(
        {
            "entity_id": "diagram_title",
            "entity_type": "diagram_title",
            "bbox_xyxy": list(title_text_bbox),
            "text": str(scene_title),
        }
    )

    circle_boxes, label_boxes, region_slots = _three_set_geometry(content_bbox, render_params=render_params)
    region_order = ["set_A_region", "set_B_region", "set_C_region"]
    for region_id in region_order:
        set_id = str(region_id).split("_")[1]
        fill_rgb = tuple(int(value) for value in set_fill_rgb_map[str(set_id)])
        region_box = circle_boxes[str(region_id)]
        fill_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        fill_draw = ImageDraw.Draw(fill_layer, "RGBA")
        fill_draw.ellipse(
            region_box,
            fill=fill_rgb + (int(render_params.set_fill_alpha),),
        )
        image = Image.alpha_composite(image, fill_layer)
        draw = ImageDraw.Draw(image, "RGBA")
        region_bbox_map[str(region_id)] = round_diagram_bbox(region_box)
        entities.append(
            {
                "entity_id": str(region_id),
                "entity_type": "diagram_set_region",
                "bbox_xyxy": round_diagram_bbox(region_box),
                "set_id": str(set_id),
            }
        )
    for region_id in region_order:
        region_box = circle_boxes[str(region_id)]
        draw.ellipse(
            region_box,
            fill=None,
            outline=tuple(int(value) for value in render_params.region_outline_rgb) + (255,),
            width=max(1, int(render_params.region_outline_width_px)),
        )

    for set_id in [str(value) for value in set_ids]:
        label_box = label_boxes[f"set_{set_id}_label"]
        draw_rounded_rect(
            draw,
            label_box,
            radius=int(0.5 * render_params.set_label_height_px),
            fill=render_params.set_label_fill_rgb,
            outline=render_params.set_label_border_rgb,
            width=2,
        )
        label_bbox = draw_diagram_text_in_box(
            draw,
            bbox=label_box,
            text=str(set_id),
            font_size_px=int(render_params.set_label_font_size_px),
            bold=True,
            fill=render_params.set_label_text_rgb,
            stroke_fill=render_params.set_label_fill_rgb,
            padding_px=4,
        )
        label_id = f"set_{set_id}_label"
        set_label_bbox_map[str(label_id)] = list(label_bbox)
        entities.append(
            {
                "entity_id": str(label_id),
                "entity_type": "diagram_set_label",
                "bbox_xyxy": list(label_bbox),
                "text": str(set_id),
            }
        )

    for number_spec in number_specs:
        number_id = str(number_spec["number_id"])
        number_bbox_id = str(number_spec["number_bbox_id"])
        region_id = str(number_spec["region_id"])
        slot_box = _number_slot_bbox(region_slots[str(region_id)], render_params=render_params)
        number_text_bbox = draw_diagram_text_in_box(
            draw,
            bbox=slot_box,
            text=str(number_spec["number_value"]),
            font_size_px=int(render_params.number_font_size_px),
            bold=True,
            fill=render_params.number_text_rgb,
            stroke_fill=render_params.number_text_stroke_rgb,
            padding_px=4,
        )
        number_slot_bbox_map[number_bbox_id] = round_diagram_bbox(slot_box)
        number_bbox_map[number_bbox_id] = list(number_text_bbox)
        entities.append(
            {
                "entity_id": str(number_bbox_id),
                "entity_type": "diagram_set_number",
                "bbox_xyxy": list(number_text_bbox),
                "number_id": str(number_id),
                "region_id": str(region_id),
                "text": str(number_spec["number_value"]),
            }
        )

    return RenderedSetScene(
        image=image.convert("RGB"),
        entities=entities,
        panel_bbox_px=round_diagram_bbox(panel_bbox),
        title_bbox_px=list(title_text_bbox),
        region_bbox_map=region_bbox_map,
        set_label_bbox_map=set_label_bbox_map,
        number_bbox_map=number_bbox_map,
        number_slot_bbox_map=number_slot_bbox_map,
    )


def render_set_scene(
    background: Image.Image,
    *,
    scene_title: str,
    set_ids: Sequence[str],
    number_specs: Sequence[Mapping[str, object]],
    set_fill_rgb_map: Mapping[str, Sequence[int]],
    render_params: SetRenderParams,
) -> RenderedSetScene:
    """Render one numeric 3-set overlap diagram with supersampled anti-aliased circles."""

    scale = int(SET_DIAGRAM_SUPERSAMPLE_SCALE)
    work_render_params = _scale_render_params(render_params, scale=scale)
    work_background = background.resize(
        (int(work_render_params.canvas_width), int(work_render_params.canvas_height)),
        resample=Image.Resampling.BICUBIC,
    )
    rendered = _render_set_scene_base(
        work_background,
        scene_title=str(scene_title),
        set_ids=set_ids,
        number_specs=number_specs,
        set_fill_rgb_map=set_fill_rgb_map,
        render_params=work_render_params,
    )
    final_image = rendered.image.resize(
        (int(render_params.canvas_width), int(render_params.canvas_height)),
        resample=Image.Resampling.LANCZOS,
    )
    return RenderedSetScene(
        image=final_image,
        entities=_scale_entities(rendered.entities, scale=float(scale)),
        panel_bbox_px=_scale_bbox(rendered.panel_bbox_px, scale=float(scale)),
        title_bbox_px=_scale_bbox(rendered.title_bbox_px, scale=float(scale)),
        region_bbox_map=_scale_bbox_map(rendered.region_bbox_map, scale=float(scale)),
        set_label_bbox_map=_scale_bbox_map(rendered.set_label_bbox_map, scale=float(scale)),
        number_bbox_map=_scale_bbox_map(rendered.number_bbox_map, scale=float(scale)),
        number_slot_bbox_map=_scale_bbox_map(rendered.number_slot_bbox_map, scale=float(scale)),
    )
