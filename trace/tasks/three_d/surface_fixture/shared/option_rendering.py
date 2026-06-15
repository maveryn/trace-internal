"""Option-grid rendering for surface-fixture visual MCQ tasks."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.tasks.shared.text_rendering import load_font

from .rendering import RenderedSurfaceFixture, bbox_union, render_surface_fixture


@dataclass(frozen=True)
class RenderedSurfaceFixtureOptionGrid:
    """Rendered 2x2 option-grid surface fixture scene."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    option_panel_bboxes_px: Dict[str, List[float]]
    option_label_bboxes_px: Dict[str, List[float]]
    option_counts_by_label: Dict[str, int]
    element_bboxes_px: Dict[str, List[float]]
    element_centers_px: Dict[str, List[float]]
    option_records: List[Dict[str, Any]]


def _offset_bbox(bbox: Sequence[float], dx: float, dy: float) -> List[float]:
    return [
        round(float(bbox[0]) + float(dx), 3),
        round(float(bbox[1]) + float(dy), 3),
        round(float(bbox[2]) + float(dx), 3),
        round(float(bbox[3]) + float(dy), 3),
    ]


def _offset_point(point: Sequence[float], dx: float, dy: float) -> List[float]:
    return [
        round(float(point[0]) + float(dx), 3),
        round(float(point[1]) + float(dy), 3),
    ]


def _panel_positions(width: int, height: int) -> Dict[str, List[int]]:
    margin_x = max(42, int(round(float(width) * 0.048)))
    margin_y = max(34, int(round(float(height) * 0.045)))
    gap_x = max(26, int(round(float(width) * 0.030)))
    gap_y = max(26, int(round(float(height) * 0.034)))
    panel_w = int((int(width) - 2 * margin_x - gap_x) // 2)
    panel_h = int((int(height) - 2 * margin_y - gap_y) // 2)
    return {
        "A": [margin_x, margin_y, margin_x + panel_w, margin_y + panel_h],
        "B": [margin_x + panel_w + gap_x, margin_y, margin_x + 2 * panel_w + gap_x, margin_y + panel_h],
        "C": [margin_x, margin_y + panel_h + gap_y, margin_x + panel_w, margin_y + 2 * panel_h + gap_y],
        "D": [
            margin_x + panel_w + gap_x,
            margin_y + panel_h + gap_y,
            margin_x + 2 * panel_w + gap_x,
            margin_y + 2 * panel_h + gap_y,
        ],
    }


def _draw_option_label(draw: ImageDraw.ImageDraw, *, label: str, panel_bbox: Sequence[float]) -> List[float]:
    badge_size = 38
    x0 = float(panel_bbox[0]) + 12.0
    y0 = float(panel_bbox[1]) + 12.0
    badge = [x0, y0, x0 + badge_size, y0 + badge_size]
    draw.rounded_rectangle(tuple(badge), radius=7, fill=(28, 36, 50), outline=(255, 255, 255), width=2)
    font = load_font(24, bold=True)
    text_bbox = draw.textbbox((0, 0), str(label), font=font, stroke_width=0)
    text_w = float(text_bbox[2] - text_bbox[0])
    text_h = float(text_bbox[3] - text_bbox[1])
    draw.text(
        (
            x0 + badge_size * 0.5 - text_w * 0.5,
            y0 + badge_size * 0.5 - text_h * 0.5 - 1.0,
        ),
        str(label),
        font=font,
        fill=(255, 255, 255),
    )
    return [round(float(value), 3) for value in badge]


def _offset_entities(
    rendered: RenderedSurfaceFixture,
    *,
    label: str,
    dx: float,
    dy: float,
) -> List[Dict[str, Any]]:
    entities: List[Dict[str, Any]] = []
    for entity in rendered.entities:
        updated = dict(entity)
        entity_id = str(updated.get("entity_id", "entity"))
        updated["entity_id"] = f"option_{label}.{entity_id}"
        updated["bbox_px"] = _offset_bbox(updated.get("bbox_px", [0, 0, 0, 0]), dx, dy)
        attrs = dict(updated.get("attrs", {}))
        attrs["option_label"] = str(label)
        updated["attrs"] = attrs
        entities.append(updated)
    return entities


def render_surface_fixture_option_grid(
    background: Image.Image,
    *,
    option_datasets: Mapping[str, Mapping[str, Any]],
    render_params: Any,
) -> RenderedSurfaceFixtureOptionGrid:
    """Render four labeled surface-fixture options into one 2x2 canvas."""

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    panel_positions = _panel_positions(int(width), int(height))
    labels = tuple(label for label in ("A", "B", "C", "D") if label in option_datasets)
    if labels != ("A", "B", "C", "D"):
        raise ValueError("surface fixture option grid requires labels A, B, C, D")

    option_panel_bboxes: Dict[str, List[float]] = {}
    option_label_bboxes: Dict[str, List[float]] = {}
    option_counts_by_label: Dict[str, int] = {}
    element_bboxes: Dict[str, List[float]] = {}
    element_centers: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []
    option_records: List[Dict[str, Any]] = []
    scene_bboxes: List[List[float]] = []

    for label in labels:
        panel_bbox = panel_positions[str(label)]
        x0, y0, x1, y1 = [int(value) for value in panel_bbox]
        panel_w = int(x1 - x0)
        panel_h = int(y1 - y0)
        panel_background = Image.new("RGB", (panel_w, panel_h), (246, 249, 250))
        panel_render_params = replace(
            render_params,
            canvas_width=int(panel_w),
            canvas_height=int(panel_h),
            label_font_size_px=max(16, int(round(float(render_params.label_font_size_px) * 0.78))),
        )
        rendered_panel = render_surface_fixture(
            panel_background,
            dataset=dict(option_datasets[str(label)]),
            render_params=panel_render_params,
        )
        image.paste(rendered_panel.image, (x0, y0))

        panel_bbox_float = [float(x0), float(y0), float(x1), float(y1)]
        draw.rounded_rectangle(tuple(panel_bbox_float), radius=8, outline=(59, 72, 86), width=3)
        draw.rounded_rectangle(
            (panel_bbox_float[0] + 3, panel_bbox_float[1] + 3, panel_bbox_float[2] - 3, panel_bbox_float[3] - 3),
            radius=6,
            outline=(236, 242, 245),
            width=1,
        )
        label_bbox = _draw_option_label(draw, label=str(label), panel_bbox=panel_bbox_float)

        option_panel_bboxes[str(label)] = [round(float(value), 3) for value in panel_bbox_float]
        option_label_bboxes[str(label)] = list(label_bbox)
        option_counts_by_label[str(label)] = int(option_datasets[str(label)]["answer_value"])
        entities.append(
            {
                "entity_id": f"option_{label}",
                "entity_type": "three_d_surface_fixture_option_panel",
                "bbox_px": list(option_panel_bboxes[str(label)]),
                "attrs": {
                    "option_label": str(label),
                    "visible_element_count": int(option_counts_by_label[str(label)]),
                },
            }
        )
        entities.extend(_offset_entities(rendered_panel, label=str(label), dx=float(x0), dy=float(y0)))

        for element_id, bbox in rendered_panel.element_bboxes_px.items():
            key = f"{label}:{element_id}"
            element_bboxes[key] = _offset_bbox(bbox, x0, y0)
        for element_id, center in rendered_panel.element_centers_px.items():
            key = f"{label}:{element_id}"
            element_centers[key] = _offset_point(center, x0, y0)

        scene_bbox = _offset_bbox(rendered_panel.scene_bbox_px, x0, y0)
        scene_bboxes.append(list(scene_bbox))
        option_records.append(
            {
                "label": str(label),
                "panel_bbox_px": list(option_panel_bboxes[str(label)]),
                "option_label_bbox_px": list(option_label_bboxes[str(label)]),
                "visible_element_count": int(option_counts_by_label[str(label)]),
                "scene_bbox_px": list(scene_bbox),
                "element_ids": [f"{label}:{element_id}" for element_id in rendered_panel.element_bboxes_px.keys()],
            }
        )

    return RenderedSurfaceFixtureOptionGrid(
        image=image,
        entities=entities,
        scene_bbox_px=bbox_union(*scene_bboxes),
        option_panel_bboxes_px=dict(option_panel_bboxes),
        option_label_bboxes_px=dict(option_label_bboxes),
        option_counts_by_label=dict(option_counts_by_label),
        element_bboxes_px=dict(element_bboxes),
        element_centers_px=dict(element_centers),
        option_records=list(option_records),
    )


__all__ = [
    "RenderedSurfaceFixtureOptionGrid",
    "render_surface_fixture_option_grid",
]
