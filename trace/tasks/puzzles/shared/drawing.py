"""Small drawing primitives shared across multiple puzzle scene renderers."""

from __future__ import annotations

from typing import List, Sequence, Tuple

from PIL import ImageDraw


def draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    bbox: Tuple[float, float, float, float],
    *,
    radius: int,
    fill: Sequence[int],
    outline: Sequence[int],
    width: int,
) -> None:
    """Draw one rounded rectangle with deterministic styling."""

    draw.rounded_rectangle(
        bbox,
        radius=int(radius),
        fill=tuple(int(value) for value in fill),
        outline=tuple(int(value) for value in outline),
        width=int(width),
    )


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font,
    fill: Sequence[int],
    stroke_fill: Sequence[int],
    stroke_width: int = 1,
) -> List[float]:
    """Draw centered text and return the final text bbox."""

    bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
    left, top, right, bottom = [float(value) for value in bbox]
    cx, cy = float(center[0]), float(center[1])
    tx = float(cx - (0.5 * (left + right)))
    ty = float(cy - (0.5 * (top + bottom)))
    draw.text(
        (tx, ty),
        str(text),
        fill=tuple(int(v) for v in fill),
        font=font,
        stroke_width=max(0, int(stroke_width)),
        stroke_fill=tuple(int(v) for v in stroke_fill),
    )
    return [
        round(float(tx + left), 3),
        round(float(ty + top), 3),
        round(float(tx + right), 3),
        round(float(ty + bottom), 3),
    ]


__all__ = [
    "draw_centered_text",
    "draw_rounded_rect",
]
