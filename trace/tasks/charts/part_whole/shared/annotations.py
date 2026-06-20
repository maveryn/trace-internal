"""Annotation projection helpers for part-whole chart tasks."""

from __future__ import annotations

from typing import Any, Mapping

from .state import PartWholeDataset, RenderedShareChart


def annotation_value_for_label(
    label: str,
    *,
    extras: Mapping[str, Any],
    values_by_label: Mapping[str, int],
) -> int:
    """Return the symbolic value associated with one annotation key."""

    if str(label) == "__total__":
        return int(extras["total_count"])
    return int(values_by_label[str(label)])


def public_annotation_key(label: str) -> str:
    """Map internal witness labels to prompt-facing point-map keys."""

    if str(label) == "__total__":
        return "total_count"
    return str(label)


def point_map_annotation(
    *,
    dataset: PartWholeDataset,
    rendered_scene: RenderedShareChart,
) -> dict[str, Any]:
    """Project selected category witnesses to point-map annotation artifacts."""

    values_by_label = {str(category.label): int(category.value) for category in dataset.categories}
    extras = dict(dataset.trace_extras)
    annotation_values = [
        annotation_value_for_label(str(label), extras=extras, values_by_label=values_by_label)
        for label in dataset.annotation_labels
    ]
    annotation_bboxes = [
        list(rendered_scene.annotation_bbox_by_label[str(label)])
        for label in dataset.annotation_labels
        if str(label) in rendered_scene.annotation_bbox_by_label
    ]
    annotation_points = [
        list(rendered_scene.annotation_point_by_label[str(label)])
        for label in dataset.annotation_labels
        if str(label) in rendered_scene.annotation_point_by_label
    ]
    annotation_keyed_points = {
        public_annotation_key(str(label)): list(rendered_scene.annotation_point_by_label[str(label)])
        for label in dataset.annotation_labels
        if str(label) in rendered_scene.annotation_point_by_label
    }
    annotation_keys = [public_annotation_key(str(label)) for label in dataset.annotation_labels]
    projected = {
        "type": "point_map",
        "point_map": dict(annotation_keyed_points),
        "pixel_point_map": dict(annotation_keyed_points),
        "point_set": list(annotation_points),
        "pixel_point_set": list(annotation_points),
        "bbox_set": list(annotation_bboxes),
        "annotation_labels": [str(label) for label in dataset.annotation_labels],
        "annotation_keys": [str(key) for key in annotation_keys],
    }
    return {
        "values": [int(value) for value in annotation_values],
        "bboxes": list(annotation_bboxes),
        "points": list(annotation_points),
        "point_map": dict(annotation_keyed_points),
        "keys": [str(key) for key in annotation_keys],
        "projected": dict(projected),
    }
