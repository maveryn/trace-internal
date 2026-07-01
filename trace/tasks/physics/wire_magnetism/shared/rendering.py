"""Rendering primitives for wire-magnetism diagrams."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.tasks.shared.drawing import draw_arrow, draw_centered_text
from trace.tasks.shared.render_variation import resolve_render_int
from trace.tasks.shared.text_rendering import load_font, resolve_text_stroke_fill

from .state import RenderedWireMagnetismScene, WireMagnetismDefaults, WireScenario


def bbox(values: Sequence[float]) -> List[float]:
    """Round one bbox to final image coordinates."""

    return [round(float(value), 3) for value in values[:4]]


def resolve_wire_render_defaults(
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    *,
    fallback_defaults: WireMagnetismDefaults,
    instance_seed: int,
    namespace: str,
) -> Dict[str, int]:
    """Resolve integer rendering defaults for a wire-magnetism scene."""

    keys = ("canvas_width", "canvas_height")
    return {
        key: resolve_render_int(
            params,
            rendering_defaults,
            key,
            int(getattr(fallback_defaults, key)),
            instance_seed=int(instance_seed),
            namespace=str(namespace),
        )
        for key in keys
    }


def _phys_to_screen_vector(vector: Tuple[int, int], length: float) -> Tuple[float, float]:
    return (float(vector[0] * length), float(-vector[1] * length))


def _draw_field_symbol(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    direction: str,
    style: Any,
) -> None:
    x, y = float(center[0]), float(center[1])
    stroke = tuple(int(value) for value in style.stroke_rgb)
    fill = tuple(int(value) for value in style.panel_alt_fill_rgb)
    draw.ellipse((x - 17.0, y - 17.0, x + 17.0, y + 17.0), fill=fill, outline=stroke, width=3)
    if direction == "out_of_page":
        draw.ellipse((x - 5.0, y - 5.0, x + 5.0, y + 5.0), fill=stroke)
    else:
        draw.line((x - 9.0, y - 9.0, x + 9.0, y + 9.0), fill=stroke, width=4)
        draw.line((x - 9.0, y + 9.0, x + 9.0, y - 9.0), fill=stroke, width=4)


def _draw_option_symbol(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    direction: str,
    style: Any,
) -> None:
    x, y = float(center[0]), float(center[1])
    if direction in {"out_of_page", "into_page"}:
        _draw_field_symbol(draw, center=(x, y), direction=str(direction), style=style)
        return
    vectors = {
        "north": (0.0, -1.0),
        "south": (0.0, 1.0),
        "east": (1.0, 0.0),
        "west": (-1.0, 0.0),
    }
    vx, vy = vectors[str(direction)]
    draw_arrow(
        draw,
        start=(x - (vx * 22.0), y - (vy * 22.0)),
        end=(x + (vx * 22.0), y + (vy * 22.0)),
        fill=tuple(int(value) for value in style.stroke_rgb),
        width=6,
        head_length_px=14,
        head_width_px=13,
    )


def render_wire_magnetism_scene(
    *,
    image: Image.Image,
    scenario: WireScenario,
    font_family: str,
    style: Any,
) -> RenderedWireMagnetismScene:
    """Render one current-carrying wire diagram and physical-witness annotations."""

    draw = ImageDraw.Draw(image)
    canvas_width, canvas_height = image.size
    title_font = load_font(27, bold=True, font_family=font_family)
    label_font = load_font(25, bold=True, font_family=font_family)
    option_font = load_font(20, bold=True, font_family=font_family)
    text_rgb = tuple(int(value) for value in style.label_rgb)
    stroke = tuple(int(value) for value in style.stroke_rgb)
    accent = tuple(int(value) for value in style.accent_rgb)

    main_panel = (56.0, 54.0, 744.0, float(canvas_height - 62))
    option_panel = (780.0, 88.0, float(canvas_width - 56), float(canvas_height - 96))
    draw.rounded_rectangle(
        main_panel,
        radius=18,
        fill=tuple(int(value) for value in style.panel_fill_rgb),
        outline=tuple(int(value) for value in style.panel_border_rgb),
        width=3,
    )
    draw.rounded_rectangle(
        option_panel,
        radius=18,
        fill=tuple(int(value) for value in style.panel_fill_rgb),
        outline=tuple(int(value) for value in style.panel_border_rgb),
        width=3,
    )
    draw_centered_text(
        draw,
        text="current-carrying wire",
        center=(main_panel[0] + (0.5 * (main_panel[2] - main_panel[0])), main_panel[1] + 32.0),
        font=title_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )
    draw_centered_text(
        draw,
        text="Field at P",
        center=(option_panel[0] + (0.5 * (option_panel[2] - option_panel[0])), option_panel[1] + 34.0),
        font=title_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )

    wire_center = (390.0, 352.0)
    wire_half = 215.0
    if scenario.orientation == "horizontal":
        wire_start = (wire_center[0] - wire_half, wire_center[1])
        wire_end = (wire_center[0] + wire_half, wire_center[1])
    else:
        wire_start = (wire_center[0], wire_center[1] + wire_half)
        wire_end = (wire_center[0], wire_center[1] - wire_half)

    arrow_vec = _phys_to_screen_vector(scenario.current_vector_phys, 132.0)
    arrow_start = (wire_center[0] - (arrow_vec[0] * 0.5), wire_center[1] - (arrow_vec[1] * 0.5))
    arrow_end = (wire_center[0] + (arrow_vec[0] * 0.5), wire_center[1] + (arrow_vec[1] * 0.5))
    point_vec = _phys_to_screen_vector(scenario.point_offset_phys, 138.0)
    point_p = (wire_center[0] + point_vec[0], wire_center[1] + point_vec[1])

    draw.line((wire_start, wire_end), fill=stroke, width=16)
    draw.line((wire_start, wire_end), fill=tuple(int(value) for value in style.panel_alt_fill_rgb), width=8)
    draw_arrow(draw, start=arrow_start, end=arrow_end, fill=accent, width=9, head_length_px=26, head_width_px=24)
    draw_centered_text(
        draw,
        text="I",
        center=(arrow_end[0] + 28.0, arrow_end[1] - 24.0),
        font=label_font,
        fill=accent,
        stroke_fill=resolve_text_stroke_fill(accent),
        stroke_width=2,
    )

    draw.ellipse(
        (point_p[0] - 15.0, point_p[1] - 15.0, point_p[0] + 15.0, point_p[1] + 15.0),
        fill=(255, 255, 255),
        outline=stroke,
        width=4,
    )
    draw_centered_text(
        draw,
        text="P",
        center=(point_p[0], point_p[1] - 36.0),
        font=label_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )
    draw.line((point_p[0], point_p[1], wire_center[0], wire_center[1]), fill=tuple(int(value) for value in style.guide_rgb), width=2)

    option_bboxes: Dict[str, List[float]] = {}
    box_w = 96.0
    box_h = 86.0
    gap_x = 20.0
    gap_y = 28.0
    start_x = option_panel[0] + 28.0
    start_y = option_panel[1] + 92.0
    for index, (label, direction) in enumerate(sorted(scenario.option_map.items())):
        col = int(index) % 2
        row = int(index) // 2
        left = start_x + (float(col) * (box_w + gap_x))
        top = start_y + (float(row) * (box_h + gap_y))
        box = (left, top, left + box_w, top + box_h)
        draw.rounded_rectangle(
            box,
            radius=14,
            fill=tuple(int(value) for value in style.panel_alt_fill_rgb),
            outline=tuple(int(value) for value in style.panel_border_rgb),
            width=3,
        )
        draw_centered_text(
            draw,
            text=str(label),
            center=(box[0] + 22.0, box[1] + 43.0),
            font=option_font,
            fill=text_rgb,
            stroke_fill=resolve_text_stroke_fill(text_rgb),
            stroke_width=1,
        )
        _draw_option_symbol(draw, center=(box[0] + 63.0, box[1] + 43.0), direction=str(direction), style=style)
        option_bboxes[str(label)] = bbox(box)

    wire_bbox = bbox(
        (
            min(wire_start[0], wire_end[0], arrow_start[0], arrow_end[0]) - 28.0,
            min(wire_start[1], wire_end[1], arrow_start[1], arrow_end[1]) - 36.0,
            max(wire_start[0], wire_end[0], arrow_start[0], arrow_end[0]) + 40.0,
            max(wire_start[1], wire_end[1], arrow_start[1], arrow_end[1]) + 36.0,
        )
    )
    point_bbox = bbox((point_p[0] - 26.0, point_p[1] - 48.0, point_p[0] + 26.0, point_p[1] + 24.0))
    annotation_bboxes = {"wire_current": wire_bbox, "point_p": point_bbox}
    scene_entities = [
        {
            "entity_id": "wire_current",
            "entity_type": "current_carrying_wire",
            "bbox_px": list(wire_bbox),
            "meta": {
                "orientation": str(scenario.orientation),
                "current_direction": str(scenario.current_direction),
            },
        },
        {
            "entity_id": "point_p",
            "entity_type": "marked_point",
            "bbox_px": list(point_bbox),
            "meta": {
                "point_side": str(scenario.point_side),
                "point_offset_phys": list(scenario.point_offset_phys),
            },
        },
    ]
    render_map = {
        "wire_start": [round(float(wire_start[0]), 3), round(float(wire_start[1]), 3)],
        "wire_end": [round(float(wire_end[0]), 3), round(float(wire_end[1]), 3)],
        "point_p": [round(float(point_p[0]), 3), round(float(point_p[1]), 3)],
        "option_bboxes": option_bboxes,
        "option_map": dict(scenario.option_map),
        "correct_label": str(scenario.correct_label),
    }
    return RenderedWireMagnetismScene(
        image=image,
        annotation_bboxes={str(key): list(value) for key, value in annotation_bboxes.items()},
        annotation_entity_ids=["wire_current", "point_p"],
        scene_entities=[dict(entity) for entity in scene_entities],
        render_map=dict(render_map),
    )


__all__ = [
    "bbox",
    "render_wire_magnetism_scene",
    "resolve_wire_render_defaults",
]
