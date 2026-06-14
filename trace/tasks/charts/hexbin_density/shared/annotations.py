"""Annotation projection for hexbin-density charts."""

from __future__ import annotations

from typing import List

from trace.tasks.charts.hexbin_density.shared.state import HexbinDataset, RenderedHexbinScene


def annotation_bbox_set(dataset: HexbinDataset, rendered: RenderedHexbinScene) -> List[List[float]]:
    annotation: List[List[float]] = []
    for bin_id in dataset.query.annotation_bin_ids:
        box = rendered.bin_bboxes_px.get(str(bin_id))
        if box is None:
            raise RuntimeError(f"missing annotation bbox for bin: {bin_id}")
        annotation.append(list(box))
    return annotation


def projected_annotation_payload(dataset: HexbinDataset, annotation: list[list[float]]) -> dict[str, object]:
    return {
        "type": "bbox_set",
        "bbox_set": [list(value) for value in annotation],
        "pixel_bbox_set": [list(value) for value in annotation],
        "annotation_bin_ids": list(dataset.query.annotation_bin_ids),
    }


__all__ = [
    "annotation_bbox_set",
    "projected_annotation_payload",
]
