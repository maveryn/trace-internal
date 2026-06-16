"""Annotation projection helpers for marker-map charts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .....core.types import TypedValue
from .rendering import MarkerMapRenderResult


@dataclass(frozen=True)
class MarkerMapAnnotationBundle:
    """Typed annotation payload plus projected review metadata."""

    annotation_gt: TypedValue
    annotation_type: str
    annotation_region_ids: Sequence[str]
    projected_annotation: Mapping[str, Any]
    annotation_refs: Sequence[Mapping[str, Any]]


def marker_bbox_set(rendered: MarkerMapRenderResult, region_ids: Sequence[str]) -> list[list[float]]:
    """Return one marker-group bbox per selected region id."""

    return [list(rendered.marker_group_bbox_map[str(region_id)]) for region_id in region_ids]


def marker_bbox(rendered: MarkerMapRenderResult, region_id: str) -> list[float]:
    """Return the scalar marker-group bbox for one selected region id."""

    return list(rendered.marker_group_bbox_map[str(region_id)])


def projected_bbox_set(
    *,
    rendered: MarkerMapRenderResult,
    region_ids: Sequence[str],
    bboxes: Sequence[Sequence[float]],
) -> dict[str, Any]:
    """Build projected annotation metadata for variable marker-region sets."""

    return {
        "type": "bbox_set",
        "bbox_set": [list(bbox) for bbox in bboxes],
        "pixel_bbox_set": [list(bbox) for bbox in bboxes],
        "bbox_map": {str(region_id): list(rendered.marker_group_bbox_map[str(region_id)]) for region_id in region_ids},
        "region_ids": [str(region_id) for region_id in region_ids],
        "marker_bboxes_by_region": {
            str(region_id): [list(bbox) for bbox in rendered.marker_bboxes_by_region.get(str(region_id), [])]
            for region_id in region_ids
        },
    }


def projected_bbox(
    *,
    rendered: MarkerMapRenderResult,
    region_id: str,
    bbox: Sequence[float],
) -> dict[str, Any]:
    """Build projected annotation metadata for one selected marker region."""

    return {
        "type": "bbox",
        "bbox": list(bbox),
        "pixel_bbox": list(bbox),
        "bbox_map": {str(region_id): list(rendered.marker_group_bbox_map[str(region_id)])},
        "region_id": str(region_id),
        "region_ids": [str(region_id)],
        "marker_bboxes_by_region": {
            str(region_id): [list(item) for item in rendered.marker_bboxes_by_region.get(str(region_id), [])]
        },
    }


def annotation_refs(
    *,
    region_ids: Sequence[str],
    projected_annotation: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return compact region-to-annotation rows for review sidecars."""

    if str(projected_annotation.get("type")) == "bbox":
        return [{"region_id": str(region_ids[0]), "bbox_px": list(projected_annotation.get("bbox", []))}]
    bboxes = list(projected_annotation.get("bbox_set", []))
    return [
        {"region_id": str(region_id), "bbox_px": list(bbox)}
        for region_id, bbox in zip(region_ids, bboxes, strict=False)
    ]


def marker_bbox_set_bundle(rendered: MarkerMapRenderResult, region_ids: Sequence[str]) -> MarkerMapAnnotationBundle:
    """Return the complete bbox-set annotation payload for selected marker regions."""

    selected_region_ids = [str(region_id) for region_id in region_ids]
    bboxes = marker_bbox_set(rendered, selected_region_ids)
    projected_annotation = projected_bbox_set(rendered=rendered, region_ids=selected_region_ids, bboxes=bboxes)
    return MarkerMapAnnotationBundle(
        annotation_gt=TypedValue(type="bbox_set", value=[list(bbox) for bbox in bboxes]),
        annotation_type="bbox_set",
        annotation_region_ids=selected_region_ids,
        projected_annotation=projected_annotation,
        annotation_refs=annotation_refs(region_ids=selected_region_ids, projected_annotation=projected_annotation),
    )


def marker_bbox_bundle(rendered: MarkerMapRenderResult, region_id: str) -> MarkerMapAnnotationBundle:
    """Return the complete scalar bbox annotation payload for one marker region."""

    selected_region_id = str(region_id)
    bbox = marker_bbox(rendered, selected_region_id)
    projected_annotation = projected_bbox(rendered=rendered, region_id=selected_region_id, bbox=bbox)
    return MarkerMapAnnotationBundle(
        annotation_gt=TypedValue(type="bbox", value=list(bbox)),
        annotation_type="bbox",
        annotation_region_ids=[selected_region_id],
        projected_annotation=projected_annotation,
        annotation_refs=annotation_refs(region_ids=[selected_region_id], projected_annotation=projected_annotation),
    )


__all__ = [
    "annotation_refs",
    "MarkerMapAnnotationBundle",
    "marker_bbox",
    "marker_bbox_bundle",
    "marker_bbox_set",
    "marker_bbox_set_bundle",
    "projected_bbox",
    "projected_bbox_set",
]
