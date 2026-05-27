"""Shared rendering helpers for geometry measurement scenes."""

from __future__ import annotations

from typing import Any, Sequence, Tuple

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]


def round1(value: float) -> float:
    """Round one measurement value to one decimal with stable near-integer handling."""

    return round(float(value) + 1e-9, 1)


def fmt_measure(value: float) -> str:
    """Format one measurement value without a trailing decimal when integral."""

    rounded = round(float(value))
    if abs(float(value) - float(rounded)) <= 1e-9:
        return str(int(rounded))
    return f"{float(value):.1f}"


def bbox_to_list(bbox: Sequence[float]) -> list[float]:
    """Return a rounded bbox list for trace payloads."""

    return [round(float(value), 3) for value in bbox]


def clamp_bbox(bbox: Sequence[float], *, width: int, height: int) -> BBox:
    """Clamp an xyxy bbox to a canvas while normalizing inverted coordinates."""

    x0, y0, x1, y1 = [float(value) for value in bbox]
    return (
        round(max(0.0, min(float(width), min(x0, x1))), 3),
        round(max(0.0, min(float(height), min(y0, y1))), 3),
        round(max(0.0, min(float(width), max(x0, x1))), 3),
        round(max(0.0, min(float(height), max(y0, y1))), 3),
    )


def pad_bbox(bbox: Sequence[float], pad: float, *, width: int, height: int) -> BBox:
    """Pad and clamp an xyxy bbox."""

    x0, y0, x1, y1 = [float(value) for value in bbox]
    return clamp_bbox((x0 - pad, y0 - pad, x1 + pad, y1 + pad), width=width, height=height)


def bbox_from_points(points: Sequence[Point], *, width: int, height: int, pad: float = 0.0) -> BBox:
    """Return a padded/clamped bbox covering point coordinates."""

    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return pad_bbox((min(xs), min(ys), max(xs), max(ys)), pad, width=width, height=height)


def draw_label(ctx: Any, text: str, center: Point, *, small: bool = False) -> BBox:
    """Draw centered measurement text using the task render context contract."""

    font = ctx.small_font if bool(small) else ctx.font
    bbox = ctx.draw.textbbox((0, 0), str(text), font=font, stroke_width=2)
    text_w = float(bbox[2] - bbox[0])
    text_h = float(bbox[3] - bbox[1])
    left = float(center[0]) - (text_w / 2.0)
    top = float(center[1]) - (text_h / 2.0)
    ctx.draw.text(
        (left, top),
        str(text),
        font=font,
        fill=ctx.label_color,
        stroke_width=2,
        stroke_fill=ctx.label_stroke_color,
    )
    return pad_bbox((left, top, left + text_w, top + text_h), 4.0, width=ctx.width, height=ctx.height)


__all__ = [
    "BBox",
    "Point",
    "bbox_from_points",
    "bbox_to_list",
    "clamp_bbox",
    "draw_label",
    "fmt_measure",
    "pad_bbox",
    "round1",
]
