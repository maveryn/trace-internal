"""Annotation projection helpers for construction-site illustrations."""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Sequence

from .state import RenderedConstructionSiteScene


def construction_worker_bbox_map(scene: RenderedConstructionSiteScene) -> Dict[str, List[float]]:
    """Return worker bbox map keyed by worker id."""

    return {str(worker.worker_id): [round(float(v), 3) for v in worker.bbox_xyxy] for worker in scene.workers}


def construction_material_bbox_map(scene: RenderedConstructionSiteScene) -> Dict[str, List[float]]:
    """Return material bbox map keyed by material id."""

    return {str(material.material_id): [round(float(v), 3) for v in material.bbox_xyxy] for material in scene.materials}


def construction_equipment_bbox_map(scene: RenderedConstructionSiteScene) -> Dict[str, List[float]]:
    """Return equipment bbox map keyed by equipment id."""

    return {str(equipment.equipment_id): [round(float(v), 3) for v in equipment.bbox_xyxy] for equipment in scene.equipment}


def construction_zone_bbox_map(scene: RenderedConstructionSiteScene) -> Dict[str, List[float]]:
    """Return construction-zone bbox map keyed by zone id."""

    return {str(zone.zone_id): [round(float(v), 3) for v in zone.bbox_xyxy] for zone in scene.zones}


def sort_construction_bboxes(bbox_map: Mapping[str, Sequence[float]], ids: Iterable[str]) -> List[List[float]]:
    """Return bbox values sorted by top-left position."""

    boxes = [list(float(v) for v in bbox_map[str(item_id)]) for item_id in ids]
    boxes.sort(key=lambda box: (float(box[1]), float(box[0]), float(box[3]), float(box[2])))
    return [[round(float(v), 3) for v in box] for box in boxes]


__all__ = [
    "construction_equipment_bbox_map",
    "construction_material_bbox_map",
    "construction_worker_bbox_map",
    "construction_zone_bbox_map",
    "sort_construction_bboxes",
]
