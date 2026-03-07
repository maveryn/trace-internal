"""Shared deterministic geometry-ink style sampling helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from ...shared.config_defaults import resolve_required_int_bounds

Color = Tuple[int, int, int]


@dataclass(frozen=True)
class GeometryShapeStyle:
    """Per-instance shape/label ink colors for geometry scenes."""

    line_color: Color
    label_color: Color
    label_stroke_color: Color

    def to_trace_dict(self) -> Dict[str, Any]:
        """Return JSON-serializable shape-style metadata for trace payloads."""
        return {
            "line_color": [int(self.line_color[0]), int(self.line_color[1]), int(self.line_color[2])],
            "label_color": [int(self.label_color[0]), int(self.label_color[1]), int(self.label_color[2])],
            "label_stroke_color": [
                int(self.label_stroke_color[0]),
                int(self.label_stroke_color[1]),
                int(self.label_stroke_color[2]),
            ],
        }


def _resolve_gray_range(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, int]:
    """Resolve one inclusive grayscale range from params/defaults with validation."""
    min_value, max_value = resolve_required_int_bounds(
        params,
        render_defaults,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context="geometry shape-style grayscale defaults",
    )
    low = max(0, min(255, int(min_value)))
    high = max(0, min(255, int(max_value)))
    if int(low) > int(high):
        raise ValueError(f"{min_key} must be <= {max_key}")
    return (int(low), int(high))


def _sample_gray_triplet(rng, low: int, high: int) -> Color:
    """Sample one grayscale RGB triplet with inclusive integer bounds."""
    value = int(rng.randint(int(low), int(high)))
    return (int(value), int(value), int(value))


def sample_geometry_shape_style(
    rng,
    *,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> GeometryShapeStyle:
    """Sample deterministic geometry shape colors from configured grayscale ranges."""
    line_low, line_high = _resolve_gray_range(
        params,
        render_defaults,
        min_key="shape_line_gray_min",
        max_key="shape_line_gray_max",
        fallback_min=10,
        fallback_max=28,
    )
    label_low, label_high = _resolve_gray_range(
        params,
        render_defaults,
        min_key="shape_label_gray_min",
        max_key="shape_label_gray_max",
        fallback_min=14,
        fallback_max=36,
    )
    stroke_low, stroke_high = _resolve_gray_range(
        params,
        render_defaults,
        min_key="shape_label_stroke_gray_min",
        max_key="shape_label_stroke_gray_max",
        fallback_min=248,
        fallback_max=255,
    )
    return GeometryShapeStyle(
        line_color=_sample_gray_triplet(rng, line_low, line_high),
        label_color=_sample_gray_triplet(rng, label_low, label_high),
        label_stroke_color=_sample_gray_triplet(rng, stroke_low, stroke_high),
    )
