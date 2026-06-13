"""Layout and placement helpers for construction-site illustrations."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ...shared.object_library import BBox

from .labels import construction_zone_display_name
from .state import CONSTRUCTION_ZONE_TYPES, ConstructionZone


def _expanded_intersects(a: BBox, b: BBox, gap: float) -> bool:
    return not (
        float(a[2]) + float(gap) <= float(b[0])
        or float(b[2]) + float(gap) <= float(a[0])
        or float(a[3]) + float(gap) <= float(b[1])
        or float(b[3]) + float(gap) <= float(a[1])
    )


def sample_construction_layout(rng, *, width: int, height: int, setting_id: str) -> Dict[str, Any]:
    """Sample stable work-zone geometry shared by construction tasks."""

    layout_id = str(rng.choice(("horizontal_yard", "vertical_yard", "diagonal_road", "scaffold_front")))
    if str(setting_id) == "roadwork":
        layout_id = str(rng.choice(("diagonal_road", "horizontal_yard", "vertical_yard")))
    elif str(setting_id) == "scaffold_site":
        layout_id = str(rng.choice(("scaffold_front", "horizontal_yard", "vertical_yard")))

    if layout_id == "vertical_yard":
        zones = {
            "excavation_zone": (68.0, 260.0, 428.0, 760.0),
            "loading_zone": (458.0, 255.0, 820.0, 760.0),
            "roadwork_zone": (852.0, 260.0, 1212.0, 760.0),
        }
    elif layout_id == "diagonal_road":
        zones = {
            "excavation_zone": (74.0, 250.0, 492.0, 550.0),
            "loading_zone": (700.0, 245.0, 1190.0, 548.0),
            "roadwork_zone": (238.0, 590.0, 1048.0, 820.0),
        }
    elif layout_id == "scaffold_front":
        zones = {
            "excavation_zone": (70.0, 568.0, 472.0, 810.0),
            "loading_zone": (504.0, 560.0, 840.0, 812.0),
            "roadwork_zone": (872.0, 560.0, 1210.0, 812.0),
        }
    else:
        zones = {
            "excavation_zone": (72.0, 300.0, 520.0, 610.0),
            "loading_zone": (566.0, 298.0, 1210.0, 610.0),
            "roadwork_zone": (168.0, 650.0, 1118.0, 830.0),
        }
    jittered: Dict[str, List[float]] = {}
    for zone_id, box in zones.items():
        dx = float(rng.uniform(-14.0, 14.0))
        dy = float(rng.uniform(-10.0, 10.0))
        jittered[zone_id] = [
            max(40.0, float(box[0]) + dx),
            max(218.0, float(box[1]) + dy),
            min(float(width) - 40.0, float(box[2]) + dx),
            min(float(height) - 36.0, float(box[3]) + dy),
        ]
    return {"layout_id": layout_id, "zone_bboxes": jittered}


def build_construction_zones(layout: Mapping[str, Any]) -> Tuple[ConstructionZone, ...]:
    """Build visible labeled zones from sampled construction layout."""

    zone_bboxes = layout.get("zone_bboxes", {})
    fills = {
        "excavation_zone": (218, 191, 136),
        "loading_zone": (195, 208, 217),
        "roadwork_zone": (207, 197, 176),
    }
    outlines = {
        "excavation_zone": (140, 102, 54),
        "loading_zone": (86, 113, 133),
        "roadwork_zone": (126, 115, 94),
    }
    zones: List[ConstructionZone] = []
    for zone_id in CONSTRUCTION_ZONE_TYPES:
        raw = zone_bboxes.get(zone_id)
        if not isinstance(raw, Sequence) or len(raw) != 4:
            raise ValueError(f"missing construction zone bbox for {zone_id}")
        zones.append(
            ConstructionZone(
                zone_id=str(zone_id),
                label=construction_zone_display_name(str(zone_id)),
                bbox_xyxy=tuple(float(v) for v in raw),  # type: ignore[arg-type]
                fill_rgb=fills[str(zone_id)],
                outline_rgb=outlines[str(zone_id)],
            )
        )
    return tuple(zones)


def construction_zone_lookup(zones: Sequence[ConstructionZone]) -> Dict[str, ConstructionZone]:
    """Return zones keyed by zone id."""

    return {str(zone.zone_id): zone for zone in zones}


def place_construction_box(
    rng,
    zone_bbox: BBox,
    *,
    width: float,
    height: float,
    occupied: List[BBox],
    gap: float,
    protected: Sequence[BBox] | None = None,
    allow_overlap_fallback: bool = True,
    max_attempts: int = 180,
) -> BBox:
    """Place a non-overlapping bbox inside a construction zone."""

    x0_min = float(zone_bbox[0]) + 18.0
    x0_max = float(zone_bbox[2]) - float(width) - 18.0
    y0_min = float(zone_bbox[1]) + 50.0
    y0_max = float(zone_bbox[3]) - float(height) - 14.0
    if x0_max < x0_min:
        x0_max = x0_min
    if y0_max < y0_min:
        y0_max = y0_min
    gap_candidates = (float(gap), 0.0) if float(gap) > 0.0 else (0.0,)

    def try_place(blockers: Sequence[BBox], active_gap: float) -> BBox | None:
        for _ in range(int(max_attempts)):
            x0 = float(rng.uniform(x0_min, x0_max))
            y0 = float(rng.uniform(y0_min, y0_max))
            box = (x0, y0, x0 + float(width), y0 + float(height))
            if not any(_expanded_intersects(box, other, float(active_gap)) for other in blockers):
                return box
        return None

    for active_gap in gap_candidates:
        box = try_place(occupied, float(active_gap))
        if box is not None:
            occupied.append(box)
            return box

    protected_boxes = tuple(protected or ())
    if protected_boxes:
        for active_gap in gap_candidates:
            box = try_place(protected_boxes, float(active_gap))
            if box is not None:
                occupied.append(box)
                return box

    if bool(allow_overlap_fallback):
        x0 = float(rng.uniform(x0_min, x0_max))
        y0 = float(rng.uniform(y0_min, y0_max))
        box = (x0, y0, x0 + float(width), y0 + float(height))
        occupied.append(box)
        return box

    raise ValueError("could not place a non-overlapping construction item")


__all__ = [
    "build_construction_zones",
    "construction_zone_lookup",
    "place_construction_box",
    "sample_construction_layout",
]
