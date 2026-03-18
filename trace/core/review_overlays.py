"""Shared evidence-overlay helpers for review/sample workbooks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from PIL import Image as PILImage
from PIL import ImageDraw as PILImageDraw

__all__ = ["render_evidence_overlay", "resolve_overlay_evidence"]


_EVIDENCE_COLORS: List[Tuple[int, int, int]] = [
    (230, 57, 70),
    (69, 123, 157),
    (46, 139, 87),
    (247, 127, 0),
    (126, 87, 194),
    (0, 150, 136),
    (156, 39, 176),
    (255, 111, 0),
]


def _as_float(value: Any) -> float | None:
    """Best-effort float normalization for review overlay payloads."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _parse_point(value: Any) -> Tuple[float, float] | None:
    """Parse one point-like payload as pixel coordinates."""
    if isinstance(value, (list, tuple)) and len(value) == 2:
        x = _as_float(value[0])
        y = _as_float(value[1])
        if x is None or y is None:
            return None
        return (float(x), float(y))
    return None


def _parse_bbox(value: Any) -> Tuple[float, float, float, float] | None:
    """Parse one bbox-like payload as pixel coordinates."""
    if isinstance(value, (list, tuple)) and len(value) == 4:
        parsed = [_as_float(item) for item in value]
        if any(item is None for item in parsed):
            return None
        x0, y0, x1, y1 = (float(parsed[0]), float(parsed[1]), float(parsed[2]), float(parsed[3]))
        if x1 <= x0 or y1 <= y0:
            return None
        return (x0, y0, x1, y1)
    return None


def _extract_points(value: Any) -> List[Tuple[float, float]]:
    """Extract point payloads from one evidence structure."""
    point = _parse_point(value)
    if point is not None:
        return [point]
    if isinstance(value, list):
        out: List[Tuple[float, float]] = []
        for item in value:
            parsed = _parse_point(item)
            if parsed is not None:
                out.append(parsed)
        return out
    if isinstance(value, Mapping):
        out = []
        for item in value.values():
            parsed = _parse_point(item)
            if parsed is not None:
                out.append(parsed)
        return out
    return []


def _extract_point_map(value: Any) -> Dict[str, Tuple[float, float]]:
    """Extract labeled point payloads from one evidence structure."""
    if not isinstance(value, Mapping):
        return {}
    out: Dict[str, Tuple[float, float]] = {}
    for key, item in value.items():
        parsed = _parse_point(item)
        if parsed is None:
            continue
        out[str(key)] = parsed
    return out


def _extract_bboxes(value: Any) -> List[Tuple[float, float, float, float]]:
    """Extract bbox payloads from one evidence structure."""
    bbox = _parse_bbox(value)
    if bbox is not None:
        return [bbox]
    if isinstance(value, list):
        out: List[Tuple[float, float, float, float]] = []
        for item in value:
            parsed = _parse_bbox(item)
            if parsed is not None:
                out.append(parsed)
        return out
    return []


def resolve_overlay_evidence(
    *,
    evidence_type: str,
    evidence_value: Any,
    trace_payload: Mapping[str, Any] | None,
) -> Tuple[str, Any]:
    """Resolve review-overlay evidence into pixel-space payloads when possible."""
    projected = trace_payload.get("projected_evidence", {}) if isinstance(trace_payload, Mapping) else {}
    if not isinstance(projected, Mapping):
        return str(evidence_type), evidence_value

    if str(evidence_type) == "graph_point":
        point_set = projected.get("pixel_point_set")
        if isinstance(point_set, list) and point_set:
            return "point", point_set[0]
        point_map = projected.get("pixel_point_map")
        if isinstance(point_map, Mapping) and point_map:
            return "point", next(iter(point_map.values()))
    if str(evidence_type) in {"grid_point_set", "grid_point_path"}:
        pixel_key = "pixel_point_path" if str(evidence_type) == "grid_point_path" else "pixel_point_set"
        if pixel_key in projected:
            return str(pixel_key), projected.get(pixel_key)
    if str(evidence_type) == "graph_point_set" and "pixel_point_set" in projected:
        return "pixel_point_set", projected.get("pixel_point_set")
    if str(evidence_type) == "grid_point_map" and "pixel_point_map" in projected:
        return "pixel_point_map", projected.get("pixel_point_map")
    if str(evidence_type) == "measurement_ref_map" and "pixel_annotation_centers" in projected:
        return "pixel_annotation_centers", projected.get("pixel_annotation_centers")
    return str(evidence_type), evidence_value


def render_evidence_overlay(source: PILImage.Image, *, evidence_type: str, evidence_value: Any) -> PILImage.Image:
    """Render one evidence-overlay image for manual review workbooks.

    Review overlays operate in pixel space. If the primary evidence contract uses
    graph-unit coordinates, callers must first pass the payload through
    `resolve_overlay_evidence(...)` so the marker positions align with the image.
    """

    image = source.convert("RGB")
    draw = PILImageDraw.Draw(image, mode="RGBA")
    width, height = image.size
    radius = max(8, int(round(min(width, height) * 0.018)))
    line_width = max(3, int(round(min(width, height) * 0.008)))
    label_offset_x = float(radius) + 6.0
    label_offset_y = float(radius) + 3.0
    evidence_kind = str(evidence_type)

    if evidence_kind in {"point_map", "pixel_point_map", "grid_point_map", "annotation_centers", "pixel_annotation_centers"}:
        point_map = _extract_point_map(evidence_value)
        for idx, (label, point) in enumerate(point_map.items()):
            x, y = point
            color = _EVIDENCE_COLORS[idx % len(_EVIDENCE_COLORS)]
            draw.ellipse(
                [x - radius, y - radius, x + radius, y + radius],
                fill=(color[0], color[1], color[2], 255),
                outline=(0, 0, 0, 255),
                width=3,
            )
            draw.text((x + label_offset_x, y - label_offset_y), str(label), fill=(color[0], color[1], color[2], 255))
        return image

    if evidence_kind in {"point", "graph_point", "point_set", "pixel_point_set", "graph_point_set", "point_path", "pixel_point_path"}:
        points = _extract_points(evidence_value)
        if evidence_kind in {"point_path", "pixel_point_path"} and len(points) >= 2:
            draw.line(points, fill=(220, 20, 60, 180), width=line_width)
        for idx, (x, y) in enumerate(points):
            color = _EVIDENCE_COLORS[idx % len(_EVIDENCE_COLORS)]
            draw.ellipse(
                [x - radius, y - radius, x + radius, y + radius],
                fill=(color[0], color[1], color[2], 255),
                outline=(0, 0, 0, 255),
                width=3,
            )
        return image

    if evidence_kind in {"bbox", "bbox_set"}:
        bboxes = _extract_bboxes(evidence_value)
        for idx, (x0, y0, x1, y1) in enumerate(bboxes):
            color = _EVIDENCE_COLORS[idx % len(_EVIDENCE_COLORS)]
            draw.rectangle([x0, y0, x1, y1], outline=(color[0], color[1], color[2], 255), width=line_width)
        return image

    for idx, (x, y) in enumerate(_extract_points(evidence_value)):
        color = _EVIDENCE_COLORS[idx % len(_EVIDENCE_COLORS)]
        draw.ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill=(color[0], color[1], color[2], 255),
            outline=(0, 0, 0, 255),
            width=3,
        )
    for idx, (x0, y0, x1, y1) in enumerate(_extract_bboxes(evidence_value)):
        color = _EVIDENCE_COLORS[idx % len(_EVIDENCE_COLORS)]
        draw.rectangle([x0, y0, x1, y1], outline=(color[0], color[1], color[2], 255), width=line_width)
    return image
