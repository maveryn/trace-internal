"""Annotation projection helpers for region-map charts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .....core.types import TypedValue
from .rendering import RegionMapRenderResult


@dataclass(frozen=True)
class RegionMapAnnotationBundle:
    """Typed annotation payload plus projected review metadata."""

    annotation_gt: TypedValue
    annotation_type: str
    annotation_region_ids: Sequence[str]
    projected_annotation: Mapping[str, Any]
    annotation_refs: Sequence[Mapping[str, Any]]


def region_bbox_set(rendered: RegionMapRenderResult, region_ids: Sequence[str]) -> list[list[float]]:
    """Return one rendered region bbox per selected region id."""

    return [list(rendered.rendered_scene.region_bbox_map[str(region_id)]) for region_id in region_ids]


def projected_bbox_set(
    *,
    rendered: RegionMapRenderResult,
    region_ids: Sequence[str],
    bboxes: Sequence[Sequence[float]],
) -> dict[str, Any]:
    """Build projected annotation metadata for variable region bbox sets."""

    return {
        "type": "bbox_set",
        "bbox_set": [list(bbox) for bbox in bboxes],
        "pixel_bbox_set": [list(bbox) for bbox in bboxes],
        "bbox_map": {
            str(region_id): list(rendered.rendered_scene.region_bbox_map[str(region_id)])
            for region_id in region_ids
        },
        "center_map": {
            str(region_id): list(rendered.rendered_scene.region_center_map[str(region_id)])
            for region_id in region_ids
        },
        "region_ids": [str(region_id) for region_id in region_ids],
    }


def annotation_refs(
    *,
    region_ids: Sequence[str],
    projected_annotation: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return compact region-to-bbox rows for review sidecars."""

    bboxes = list(projected_annotation.get("bbox_set", []))
    return [
        {"region_id": str(region_id), "bbox_px": list(bbox)}
        for region_id, bbox in zip(region_ids, bboxes, strict=False)
    ]


def region_bbox_set_bundle(rendered: RegionMapRenderResult, region_ids: Sequence[str]) -> RegionMapAnnotationBundle:
    """Return the complete bbox-set annotation payload for selected map regions."""

    selected_region_ids = [str(region_id) for region_id in region_ids]
    bboxes = region_bbox_set(rendered, selected_region_ids)
    projected_annotation = projected_bbox_set(rendered=rendered, region_ids=selected_region_ids, bboxes=bboxes)
    return RegionMapAnnotationBundle(
        annotation_gt=TypedValue(type="bbox_set", value=[list(bbox) for bbox in bboxes]),
        annotation_type="bbox_set",
        annotation_region_ids=selected_region_ids,
        projected_annotation=projected_annotation,
        annotation_refs=annotation_refs(region_ids=selected_region_ids, projected_annotation=projected_annotation),
    )


__all__ = [
    "RegionMapAnnotationBundle",
    "annotation_refs",
    "projected_bbox_set",
    "region_bbox_set",
    "region_bbox_set_bundle",
]
