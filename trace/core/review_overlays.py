"""Shared annotation-overlay helpers for review/sample workbooks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from PIL import Image as PILImage
from PIL import ImageDraw as PILImageDraw

__all__ = ["render_annotation_overlay", "resolve_overlay_annotation"]


_ANNOTATION_COLORS: List[Tuple[int, int, int]] = [
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
    """Extract point payloads from one annotation structure."""
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
    """Extract labeled point payloads from one annotation structure."""
    if not isinstance(value, Mapping):
        return {}
    out: Dict[str, Tuple[float, float]] = {}
    for key, item in value.items():
        parsed = _parse_point(item)
        if parsed is None:
            continue
        out[str(key)] = parsed
    return out


def _extract_keyed_point_sets(value: Any) -> Dict[str, List[Tuple[float, float]]]:
    """Extract labeled unordered point-set payloads from one annotation structure."""

    if not isinstance(value, Mapping):
        return {}
    out: Dict[str, List[Tuple[float, float]]] = {}
    for key, item in value.items():
        points = _extract_points(item)
        if points:
            out[str(key)] = points
        elif isinstance(item, list) and not item:
            out[str(key)] = []
    return out


def _extract_bboxes(value: Any) -> List[Tuple[float, float, float, float]]:
    """Extract bbox payloads from one annotation structure."""
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


def _extract_bbox_map(value: Any) -> Dict[str, Tuple[float, float, float, float]]:
    """Extract labeled bbox payloads from one annotation structure."""
    if not isinstance(value, Mapping):
        return {}
    out: Dict[str, Tuple[float, float, float, float]] = {}
    for key, item in value.items():
        parsed = _parse_bbox(item)
        if parsed is None:
            continue
        out[str(key)] = parsed
    return out


def _extract_keyed_bbox_sets(value: Any) -> Dict[str, List[Tuple[float, float, float, float]]]:
    """Extract labeled unordered bbox-set payloads from one annotation structure."""

    if not isinstance(value, Mapping):
        return {}
    out: Dict[str, List[Tuple[float, float, float, float]]] = {}
    for key, item in value.items():
        bboxes = _extract_bboxes(item)
        if bboxes:
            out[str(key)] = bboxes
        elif isinstance(item, list) and not item:
            out[str(key)] = []
    return out


def _extract_edge_segments(value: Any) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """Extract edge-segment payloads from one annotation structure."""

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


def _draw_point_marker(
    draw: PILImageDraw.ImageDraw,
    point: Tuple[float, float],
    *,
    color: Tuple[int, int, int],
    radius: int,
    line_width: int,
) -> None:
    """Draw one high-contrast X marker for point annotation.

    Filled circles are easy to confuse with board pieces, stones, bubbles, and
    darts, so review overlays use an X-shaped annotation for point witnesses.
    """

    x, y = point
    r = float(max(7, int(radius)))
    stroke = max(2, int(line_width))
    black_width = max(int(stroke) + 5, 7)
    white_width = max(int(stroke) + 2, 4)
    segments = (
        [(float(x - r), float(y - r)), (float(x + r), float(y + r))],
        [(float(x - r), float(y + r)), (float(x + r), float(y - r))],
    )
    for segment in segments:
        draw.line(segment, fill=(0, 0, 0, 230), width=black_width)
    for segment in segments:
        draw.line(segment, fill=(255, 255, 255, 245), width=white_width)
    for segment in segments:
        draw.line(segment, fill=(color[0], color[1], color[2], 255), width=stroke)


def resolve_overlay_annotation(
    *,
    annotation_type: str,
    annotation_value: Any,
    trace_payload: Mapping[str, Any] | None,
) -> Tuple[str, Any]:
    """Resolve review-overlay annotation into pixel-space payloads when possible."""
    projected = trace_payload.get("projected_annotation", {}) if isinstance(trace_payload, Mapping) else {}
    if not isinstance(projected, Mapping):
        return str(annotation_type), annotation_value

    annotation_kind = str(annotation_type)
    if annotation_kind in {
        "bbox",
        "bbox_sequence",
        "bbox_set",
        "keyed_bbox_map",
        "keyed_bbox_set_map",
        "keyed_point_map",
        "keyed_point_set_map",
        "point",
        "segment",
        "segment_set",
        "point_sequence",
        "point_set",
    }:
        pixel_key = f"pixel_{annotation_kind}"
        if pixel_key in projected:
            return annotation_kind, projected.get(pixel_key)
        if annotation_kind in projected:
            return annotation_kind, projected.get(annotation_kind)
    return str(annotation_type), annotation_value


def render_annotation_overlay(source: PILImage.Image, *, annotation_type: str, annotation_value: Any) -> PILImage.Image:
    """Render one annotation-overlay image for manual review workbooks.

    Review overlays operate in pixel space. Callers should pass public image-level
    annotation payloads or projected public pixel annotation.
    """

    image = source.convert("RGB")
    draw = PILImageDraw.Draw(image, mode="RGBA")
    width, height = image.size
    radius = max(8, int(round(min(width, height) * 0.018)))
    line_width = max(3, int(round(min(width, height) * 0.008)))
    label_offset_x = float(radius) + 6.0
    label_offset_y = float(radius) + 3.0
    annotation_kind = str(annotation_type)

    if annotation_kind in {
        "point_map",
        "pixel_point_map",
        "keyed_point_map",
        "pixel_keyed_point_map",
        "annotation_centers",
        "pixel_annotation_centers",
    }:
        point_map = _extract_point_map(annotation_value)
        for idx, (label, point) in enumerate(point_map.items()):
            x, y = point
            color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]
            _draw_point_marker(draw, point, color=color, radius=radius, line_width=line_width)
            draw.text((x + label_offset_x, y - label_offset_y), str(label), fill=(color[0], color[1], color[2], 255))
        return image

    if annotation_kind in {"keyed_point_set_map", "pixel_keyed_point_set_map"}:
        point_sets = _extract_keyed_point_sets(annotation_value)
        for idx, (label, points) in enumerate(point_sets.items()):
            color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]
            for point_index, (x, y) in enumerate(points):
                _draw_point_marker(draw, (x, y), color=color, radius=radius, line_width=line_width)
                if point_index == 0:
                    draw.text((x + label_offset_x, y - label_offset_y), str(label), fill=(color[0], color[1], color[2], 255))
        return image

    if annotation_kind in {"keyed_bbox_map", "pixel_keyed_bbox_map"}:
        bbox_map = _extract_bbox_map(annotation_value)
        for idx, (label, bbox) in enumerate(bbox_map.items()):
            color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]
            _draw_bbox_outline(draw, bbox, color=color, line_width=line_width)
            x0, y0, _x1, _y1 = bbox
            draw.text((x0 + 4.0, max(0.0, y0 - 16.0)), str(label), fill=(color[0], color[1], color[2], 255))
        return image

    if annotation_kind in {"keyed_bbox_set_map", "pixel_keyed_bbox_set_map"}:
        bbox_sets = _extract_keyed_bbox_sets(annotation_value)
        for idx, (label, bboxes) in enumerate(bbox_sets.items()):
            color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]
            for bbox_index, bbox in enumerate(bboxes):
                _draw_bbox_outline(draw, bbox, color=color, line_width=line_width)
                if bbox_index == 0:
                    x0, y0, _x1, _y1 = bbox
                    draw.text((x0 + 4.0, max(0.0, y0 - 16.0)), str(label), fill=(color[0], color[1], color[2], 255))
        return image

    if annotation_kind in {
        "point",
        "pixel_point",
        "point_set",
        "pixel_point_set",
        "point_sequence",
        "pixel_point_sequence",
    }:
        points = _extract_points(annotation_value)
        if annotation_kind in {"point_sequence", "pixel_point_sequence"} and len(points) >= 2:
            draw.line(points, fill=(220, 20, 60, 180), width=line_width)
        for idx, (x, y) in enumerate(points):
            color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]
            _draw_point_marker(draw, (x, y), color=color, radius=radius, line_width=line_width)
        return image

    if annotation_kind in {"segment", "segment_set"}:
        edge_segments = _extract_edge_segments(annotation_value)
        for idx, (left, right) in enumerate(edge_segments):
            color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]
            draw.line([left, right], fill=(color[0], color[1], color[2], 220), width=line_width)
            for x, y in (left, right):
                _draw_point_marker(draw, (x, y), color=color, radius=radius, line_width=line_width)
        return image

    if annotation_kind in {"bbox", "bbox_sequence", "bbox_set"}:
        bboxes = _extract_bboxes(annotation_value)
        for idx, bbox in enumerate(bboxes):
            color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]
            _draw_bbox_outline(draw, bbox, color=color, line_width=line_width)
        return image

    for idx, (x, y) in enumerate(_extract_points(annotation_value)):
        color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]
        _draw_point_marker(draw, (x, y), color=color, radius=radius, line_width=line_width)
    for idx, bbox in enumerate(_extract_bboxes(annotation_value)):
        color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]
        _draw_bbox_outline(draw, bbox, color=color, line_width=line_width)
    return image
