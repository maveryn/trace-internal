"""Rendering helpers for marked-point overlays in 3D spatial tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....shared.text_legibility import draw_text_traced
from ....shared.text_rendering import load_font
from ...shared.object_scene import POINT_COLORS, POINT_LABELS, _RenderParams


def _text_bbox_at_center(
    *,
    draw: ImageDraw.ImageDraw,
    text: str,
    center: Sequence[float],
    font,
    stroke_width: int,
) -> Tuple[Tuple[float, float], List[float]]:
    raw_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=int(stroke_width))
    width = float(raw_bbox[2] - raw_bbox[0])
    height = float(raw_bbox[3] - raw_bbox[1])
    x = float(center[0]) - width * 0.5 - float(raw_bbox[0])
    y = float(center[1]) - height * 0.5 - float(raw_bbox[1])
    bbox = draw.textbbox((x, y), str(text), font=font, stroke_width=int(stroke_width))
    return (round(float(x), 3), round(float(y), 3)), [round(float(value), 3) for value in bbox]


def draw_marked_points(
    image: Image.Image,
    *,
    marked_points: Sequence[Mapping[str, Any]],
    render_params: _RenderParams,
) -> Tuple[Image.Image, Dict[str, Any], List[Dict[str, Any]]]:
    output = image.convert("RGB")
    draw = ImageDraw.Draw(output)
    marker_radius = max(12.0, float(render_params.marker_radius_px) * 0.66)
    label_font = load_font(max(int(render_params.label_font_size_px) + 8, int(round(marker_radius * 2.0))), bold=True)
    marker_centers: Dict[str, List[float]] = {}
    marker_glyph_bboxes: Dict[str, List[float]] = {}
    marker_label_bboxes: Dict[str, List[float]] = {}
    marker_bboxes: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []

    for point in sorted(marked_points, key=lambda item: float(item["camera_distance"]), reverse=True):
        label = str(point["point_label"])
        x, y = (float(point["screen_xy"][0]), float(point["screen_xy"][1]))
        color = tuple(int(channel) for channel in POINT_COLORS[POINT_LABELS.index(label) % len(POINT_COLORS)])
        text_xy, glyph_bbox = _text_bbox_at_center(
            draw=draw,
            text=label,
            center=(x, y),
            font=label_font,
            stroke_width=5,
        )
        draw_text_traced(
            draw,
            text_xy,
            label,
            font=label_font,
            fill=(255, 255, 255),
            stroke_width=7,
            stroke_fill=(255, 255, 255),
            role="marked_point_label_halo",
            required=False,
        )
        draw_text_traced(
            draw,
            text_xy,
            label,
            font=label_font,
            fill=color,
            stroke_width=2,
            stroke_fill=(23, 28, 36),
            role="marked_point_label",
            required=True,
        )
        marker_centers[label] = [round(float(x), 3), round(float(y), 3)]
        marker_glyph_bboxes[label] = list(glyph_bbox)
        marker_label_bboxes[label] = list(glyph_bbox)
        marker_bboxes[label] = list(glyph_bbox)
        entities.append(
            {
                "entity_id": str(point["point_id"]),
                "entity_type": "three_d_marked_point",
                "bbox_px": list(glyph_bbox),
                "attrs": {
                    "point_label": str(label),
                    "marker_id": str(point["marker_id"]),
                    "surface_kind": str(point["surface_kind"]),
                    "attached_object_id": point.get("attached_object_id"),
                    "is_answer_candidate": True,
                    "world_xyz": list(point["world_xyz"]),
                    "screen_xy": [round(float(x), 3), round(float(y), 3)],
                    "camera_xyz": list(point["camera_xyz"]),
                    "camera_distance": float(point["camera_distance"]),
                    "marker_color_rgb": [int(channel) for channel in color],
                    "marker_style": "letter_only",
                },
            }
        )

    return (
        output,
        {
            "marked_point_centers_px": dict(marker_centers),
            "marked_point_glyph_bboxes_px": dict(marker_glyph_bboxes),
            "marked_point_circle_bboxes_px": dict(marker_glyph_bboxes),
            "marked_point_label_bboxes_px": dict(marker_label_bboxes),
            "marked_point_bboxes_px": dict(marker_bboxes),
        },
        entities,
    )


__all__ = ["draw_marked_points"]
