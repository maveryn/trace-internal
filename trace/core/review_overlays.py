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


def _extract_edge_segments(value: Any) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """Extract edge-segment payloads from one evidence structure."""

    def _parse_segment(item: Any) -> Tuple[Tuple[float, float], Tuple[float, float]] | None:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            return None
        left = _parse_point(item[0])
        right = _parse_point(item[1])
        if left is None or right is None:
            return None
        return (left, right)

    segment = _parse_segment(value)
    if segment is not None:
        return [segment]
    if isinstance(value, list):
        out: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
        for item in value:
            parsed = _parse_segment(item)
            if parsed is not None:
                out.append(parsed)
        return out
    return []


def _draw_bbox_outline(
    draw: PILImageDraw.ImageDraw,
    bbox: Tuple[float, float, float, float],
    *,
    color: Tuple[int, int, int],
    line_width: int,
) -> None:
    """Draw one high-contrast bbox outline that remains visible on colored UI regions."""
    x0, y0, x1, y1 = bbox
    shadow_width = max(int(line_width) + 4, 5)
    draw.rectangle([x0, y0, x1, y1], outline=(0, 0, 0, 230), width=shadow_width)
    draw.rectangle([x0, y0, x1, y1], outline=(color[0], color[1], color[2], 255), width=max(1, int(line_width)))


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

    evidence_kind = str(evidence_type)
    if evidence_kind in {"bbox_sequence", "bbox_set", "point_pair_set", "point_sequence", "point_set"}:
        if evidence_kind in projected:
            return evidence_kind, projected.get(evidence_kind)
        pixel_key = f"pixel_{evidence_kind}"
        if pixel_key in projected:
            return evidence_kind, projected.get(pixel_key)
    return str(evidence_type), evidence_value


def render_evidence_overlay(source: PILImage.Image, *, evidence_type: str, evidence_value: Any) -> PILImage.Image:
    """Render one evidence-overlay image for manual review workbooks.

    Review overlays operate in pixel space. Callers should pass public image-level
    evidence payloads or projected public pixel evidence.
    """

    image = source.convert("RGB")
    draw = PILImageDraw.Draw(image, mode="RGBA")
    width, height = image.size
    radius = max(8, int(round(min(width, height) * 0.018)))
    line_width = max(3, int(round(min(width, height) * 0.008)))
    label_offset_x = float(radius) + 6.0
    label_offset_y = float(radius) + 3.0
    evidence_kind = str(evidence_type)

    if evidence_kind in {"point_map", "pixel_point_map", "annotation_centers", "pixel_annotation_centers"}:
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

    if evidence_kind in {
        "point",
        "point_set",
        "pixel_point_set",
        "point_sequence",
        "pixel_point_sequence",
    }:
        points = _extract_points(evidence_value)
        if evidence_kind in {"point_sequence", "pixel_point_sequence"} and len(points) >= 2:
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

    if evidence_kind == "point_pair_set":
        edge_segments = _extract_edge_segments(evidence_value)
        for idx, (left, right) in enumerate(edge_segments):
            color = _EVIDENCE_COLORS[idx % len(_EVIDENCE_COLORS)]
            draw.line([left, right], fill=(color[0], color[1], color[2], 220), width=line_width)
            for x, y in (left, right):
                draw.ellipse(
                    [x - radius, y - radius, x + radius, y + radius],
                    fill=(color[0], color[1], color[2], 255),
                    outline=(0, 0, 0, 255),
                    width=2,
                )
        return image

    if evidence_kind in {"bbox", "bbox_sequence", "bbox_set"}:
        bboxes = _extract_bboxes(evidence_value)
        for idx, bbox in enumerate(bboxes):
            color = _EVIDENCE_COLORS[idx % len(_EVIDENCE_COLORS)]
            _draw_bbox_outline(draw, bbox, color=color, line_width=line_width)
        return image

    for idx, (x, y) in enumerate(_extract_points(evidence_value)):
        color = _EVIDENCE_COLORS[idx % len(_EVIDENCE_COLORS)]
        draw.ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill=(color[0], color[1], color[2], 255),
            outline=(0, 0, 0, 255),
            width=3,
        )
    for idx, bbox in enumerate(_extract_bboxes(evidence_value)):
        color = _EVIDENCE_COLORS[idx % len(_EVIDENCE_COLORS)]
        _draw_bbox_outline(draw, bbox, color=color, line_width=line_width)
    return image
