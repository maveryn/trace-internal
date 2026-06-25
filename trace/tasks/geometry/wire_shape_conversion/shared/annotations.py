"""Annotation helpers for wire-shape-conversion diagrams."""

from __future__ import annotations

from collections.abc import Sequence

from trace.tasks.geometry.shared.measurement_rendering import bbox_to_list

from .state import RenderedScene

WIRE_LENGTH_ANNOTATION_KEYS: tuple[str, ...] = (
    "wire_shape_bbox",
    "dimension_region_bbox",
)
FRAME_EDGE_ANNOTATION_KEYS: tuple[str, ...] = (
    "source_wire_shape_bbox",
    "target_frame_bbox",
    "source_dimension_region_bbox",
    "target_known_dimension_region_bbox",
    "target_unknown_edge_bbox",
)
MISSING_DIMENSION_ANNOTATION_KEYS: tuple[str, ...] = (
    "source_wire_shape_bbox",
    "target_shape_bbox",
    "source_dimension_region_bbox",
    "target_known_dimension_region_bbox",
    "target_unknown_side_bbox",
)


def annotation_bbox_map(rendered: RenderedScene, keys: Sequence[str]) -> dict[str, list[float]]:
    return {str(key): bbox_to_list(rendered.annotation_bboxes[str(key)]) for key in keys}


def projected_annotation(annotation_value: dict[str, list[float]]) -> dict[str, object]:
    return {
        "type": "bbox_map",
        "bbox_map": dict(annotation_value),
        "pixel_bbox_map": dict(annotation_value),
    }


def example_bbox_for_key(key: str) -> list[int]:
    examples = {
        "wire_shape_bbox": [300, 200, 540, 390],
        "dimension_region_bbox": [255, 160, 605, 460],
        "source_wire_shape_bbox": [130, 220, 345, 390],
        "target_frame_bbox": [555, 205, 725, 415],
        "target_shape_bbox": [555, 205, 725, 415],
        "source_dimension_region_bbox": [100, 165, 395, 460],
        "target_known_dimension_region_bbox": [535, 410, 765, 490],
        "target_unknown_edge_bbox": [565, 415, 720, 465],
        "target_unknown_side_bbox": [565, 415, 720, 465],
    }
    return list(examples[str(key)])


__all__ = [
    "FRAME_EDGE_ANNOTATION_KEYS",
    "MISSING_DIMENSION_ANNOTATION_KEYS",
    "WIRE_LENGTH_ANNOTATION_KEYS",
    "annotation_bbox_map",
    "example_bbox_for_key",
    "projected_annotation",
]
