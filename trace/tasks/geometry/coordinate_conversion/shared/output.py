"""Neutral output serialization helpers for coordinate-conversion scenes."""

from __future__ import annotations

from typing import Any, Mapping


def point_annotation_from_render(render_map: Mapping[str, Any]) -> list[float]:
    """Return the rendered scalar point annotation for point P."""

    point = render_map["point_p_px"]
    return [float(point[0]), float(point[1])]


def segment_annotation_from_render(render_map: Mapping[str, Any]) -> list[list[float]]:
    """Return the rendered scalar segment annotation for segment OP."""

    segment = render_map["ray_op_px"]
    return [[float(segment[0][0]), float(segment[0][1])], [float(segment[1][0]), float(segment[1][1])]]


def projected_scalar_annotation(*, annotation_type: str, annotation_value: Any) -> dict[str, Any]:
    """Return projected scalar annotation payload for trace sidecars."""

    if str(annotation_type) == "point":
        return {
            "type": "point",
            "point": [float(annotation_value[0]), float(annotation_value[1])],
            "pixel_point": [float(annotation_value[0]), float(annotation_value[1])],
        }
    if str(annotation_type) == "segment":
        return {
            "type": "segment",
            "segment": [[float(point[0]), float(point[1])] for point in annotation_value],
            "pixel_segment": [[float(point[0]), float(point[1])] for point in annotation_value],
        }
    raise ValueError(f"unsupported scalar annotation type: {annotation_type!r}")


def rendered_style_sections(rendered: Any) -> dict[str, Any]:
    """Return style and render-map sections shared by both public tasks."""

    return {
        "render_spec": {
            **dict(rendered.render_spec),
            "coord_space": "pixel",
            "background_style": dict(rendered.background_meta),
            "diagram_style": dict(rendered.style_meta),
        },
        "render_map": dict(rendered.render_map),
    }


__all__ = [
    "point_annotation_from_render",
    "projected_scalar_annotation",
    "rendered_style_sections",
    "segment_annotation_from_render",
]
