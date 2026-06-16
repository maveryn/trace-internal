"""State containers for the RPG interior scene package."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


BBox = tuple[float, float, float, float]
Point = tuple[float, float]
TileBox = tuple[int, int, int, int]


@dataclass(frozen=True)
class RpgInteriorRegion:
    """One named region or support zone in the interior."""

    region_id: str
    public_name: str
    relation_phrase: str
    region_type: str
    tile_xywh: TileBox
    bbox_xyxy: BBox
    metadata: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "region_id": str(self.region_id),
            "public_name": str(self.public_name),
            "relation_phrase": str(self.relation_phrase),
            "region_type": str(self.region_type),
            "tile_xywh": [int(value) for value in self.tile_xywh],
            "bbox": [round(float(value), 3) for value in self.bbox_xyxy],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class RpgInteriorEntity:
    """One rendered entity in the interior."""

    entity_id: str
    public_name: str
    object_type: str
    category: str
    zone_id: str
    tile_xywh: TileBox
    bbox_xyxy: BBox
    point_xy: Point
    layer: str
    countable: bool
    metadata: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        metadata = {
            str(key): value
            for key, value in self.metadata.items()
            if str(key) != "object_record"
        }
        payload = {
            "entity_id": str(self.entity_id),
            "public_name": str(self.public_name),
            "object_type": str(self.object_type),
            "category": str(self.category),
            "zone_id": str(self.zone_id),
            "tile_xywh": [int(value) for value in self.tile_xywh],
            "bbox": [round(float(value), 3) for value in self.bbox_xyxy],
            "point": [round(float(value), 3) for value in self.point_xy],
            "layer": str(self.layer),
            "countable": bool(self.countable),
            "metadata": metadata,
        }
        if "object_record" in self.metadata:
            payload["object_record"] = self.metadata["object_record"]
        return payload


@dataclass(frozen=True)
class RpgInteriorScene:
    """Rendered RPG interior plus metadata used by tasks."""

    image: Any
    entities: tuple[RpgInteriorEntity, ...]
    regions: tuple[RpgInteriorRegion, ...]
    trace: Mapping[str, Any]


__all__ = [
    "BBox",
    "Point",
    "RpgInteriorEntity",
    "RpgInteriorRegion",
    "RpgInteriorScene",
    "TileBox",
]
