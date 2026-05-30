"""Park and playground illustration scene with activity-labeled people."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from .render_geometry import scale_bbox as _scale_bbox, scale_points as _scale_points
from .object_catalog import label_map_for_tag, plural_name_map_for_tag, variant_ids_with_tag
from .object_library import BBox, RGB, STYLE_IDS
from .object_registry import make_object_record
from .person_rendering import draw_person_hair_back, draw_person_hair_front, draw_person_skirt, normalize_person_gender, sample_person_gender


PARK_SETTING_IDS: Tuple[str, ...] = variant_ids_with_tag("park_setting")
PARK_PERSON_ACTIVITIES: Tuple[str, ...] = variant_ids_with_tag("park_person_activity")
PARK_EQUIPMENT_TYPES: Tuple[str, ...] = variant_ids_with_tag("park_equipment")
PARK_ZONE_TYPES: Tuple[str, ...] = variant_ids_with_tag("park_zone")
PARK_PERSON_ACTIVITY_LABELS: Dict[str, str] = label_map_for_tag("park_person_activity")
PARK_EQUIPMENT_LABELS: Dict[str, str] = plural_name_map_for_tag("park_equipment")
PARK_ZONE_LABELS: Dict[str, str] = label_map_for_tag("park_zone")


@dataclass(frozen=True)
class ParkPersonSpec:
    """Requested semantic activity for one rendered person."""

    activity: str
    role: str = "distractor"
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParkEquipmentSpec:
    """Requested semantic equipment type for one rendered playground item."""

    equipment_type: str
    role: str = "distractor"
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParkPerson:
    """One rendered person with activity metadata."""

    person_id: str
    activity: str
    activity_label: str
    bbox_xyxy: BBox
    primary_color_rgb: RGB
    accent_color_rgb: RGB
    skin_color_rgb: RGB
    style_id: str
    gender_id: str
    role: str
    attributes: Mapping[str, Any]


@dataclass(frozen=True)
class ParkDecor:
    """Non-query park decor or support object."""

    decor_id: str
    decor_type: str
    bbox_xyxy: BBox
    attributes: Mapping[str, Any]


@dataclass(frozen=True)
class RenderedParkPlaygroundScene:
    """Rendered park scene plus verifier-ready metadata."""

    image: Image.Image
    setting_id: str
    persons: Tuple[ParkPerson, ...]
    decor: Tuple[ParkDecor, ...]
    canvas_width: int
    canvas_height: int
    render_scale: int
    style_id: str
    layout: Mapping[str, Any]


def park_activity_display_name(activity: str) -> str:
    """Return prompt-facing activity text."""

    return PARK_PERSON_ACTIVITY_LABELS.get(str(activity), str(activity).replace("_", " "))


def park_equipment_display_name(equipment_type: str) -> str:
    """Return prompt-facing plural equipment text."""

    return PARK_EQUIPMENT_LABELS.get(str(equipment_type), str(equipment_type).replace("_", " ") + "s")


def park_zone_display_name(zone: str) -> str:
    """Return prompt-facing park-zone text."""

    return PARK_ZONE_LABELS.get(str(zone), str(zone).replace("_", " ") + " area")


def _decor_object_type(decor_type: str) -> str:
    if str(decor_type) in set(PARK_EQUIPMENT_TYPES):
        return "playground_equipment"
    if str(decor_type) in {"playground_sand", "picnic_area", "garden_area"}:
        return "zone"
    if str(decor_type) in {"walking_path", "pond"}:
        return "environment_feature"
    return str(decor_type)




def _jitter_rgb(rng, color: RGB, amount: int = 12) -> RGB:
    return tuple(max(0, min(255, int(channel) + int(rng.randint(-int(amount), int(amount))))) for channel in color)  # type: ignore[return-value]


def _choose_weighted(rng, weights: Mapping[str, float], support: Sequence[str]) -> str:
    choices = [(str(value), max(0.0, float(weights.get(str(value), 0.0)))) for value in support]
    total = sum(weight for _value, weight in choices)
    if total <= 0.0:
        return str(rng.choice(tuple(support)))
    threshold = float(rng.random()) * float(total)
    running = 0.0
    for value, weight in choices:
        running += float(weight)
        if running >= threshold:
            return str(value)
    return str(choices[-1][0])


def _style_params(style_id: str) -> Tuple[RGB, int, bool]:
    if str(style_id) == "paper_cutout":
        return (252, 252, 247), 4, True
    if str(style_id) == "outlined_cartoon":
        return (35, 39, 48), 3, False
    if str(style_id) == "soft_shadow":
        return (73, 78, 88), 2, True
    return (73, 78, 88), 1, False


def _rect(draw: ImageDraw.ImageDraw, bbox: BBox, *, fill: RGB, outline: RGB | None, width: int, scale: int, radius: float = 0.0) -> None:
    box = _scale_bbox(bbox, scale)
    if radius > 0:
        draw.rounded_rectangle(box, radius=max(1, int(round(float(radius) * int(scale)))), fill=tuple(fill), outline=tuple(outline) if outline else None, width=max(1, int(width) * int(scale)))
    else:
        draw.rectangle(box, fill=tuple(fill), outline=tuple(outline) if outline else None, width=max(1, int(width) * int(scale)))


def _ellipse(draw: ImageDraw.ImageDraw, bbox: BBox, *, fill: RGB, outline: RGB | None, width: int, scale: int) -> None:
    draw.ellipse(_scale_bbox(bbox, scale), fill=tuple(fill), outline=tuple(outline) if outline else None, width=max(1, int(width) * int(scale)))


def _poly(draw: ImageDraw.ImageDraw, points: Sequence[Tuple[float, float]], *, fill: RGB, outline: RGB | None, width: int, scale: int) -> None:
    draw.polygon(_scale_points(points, scale), fill=tuple(fill))
    if outline:
        draw.line(_scale_points([*points, points[0]], scale), fill=tuple(outline), width=max(1, int(width) * int(scale)), joint="curve")


def _line(draw: ImageDraw.ImageDraw, points: Sequence[Tuple[float, float]], *, fill: RGB, width: int, scale: int) -> None:
    draw.line(_scale_points(points, scale), fill=tuple(fill), width=max(1, int(width) * int(scale)), joint="curve")


def _bbox_union(boxes: Iterable[BBox]) -> BBox:
    values = [tuple(float(v) for v in box) for box in boxes]
    if not values:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(v[0] for v in values), min(v[1] for v in values), max(v[2] for v in values), max(v[3] for v in values))


def _expanded_intersects(a: BBox, b: BBox, gap: float) -> bool:
    return not (
        float(a[2]) + float(gap) <= float(b[0])
        or float(b[2]) + float(gap) <= float(a[0])
        or float(a[3]) + float(gap) <= float(b[1])
        or float(b[3]) + float(gap) <= float(a[1])
    )


def _clamp_bbox_to_canvas(box: BBox, *, width: int, height: int, margin: float = 20.0) -> BBox:
    x0, y0, x1, y1 = (float(v) for v in box)
    box_w = max(1.0, x1 - x0)
    box_h = max(1.0, y1 - y0)
    max_x0 = max(float(margin), float(width) - float(margin) - box_w)
    max_y0 = max(float(margin), float(height) - float(margin) - box_h)
    clamped_x0 = max(float(margin), min(float(x0), max_x0))
    clamped_y0 = max(float(margin), min(float(y0), max_y0))
    return (
        round(float(clamped_x0), 3),
        round(float(clamped_y0), 3),
        round(float(clamped_x0 + box_w), 3),
        round(float(clamped_y0 + box_h), 3),
    )


def _safe_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _safe_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_json(item) for item in value]
    if isinstance(value, float):
        return round(float(value), 3)
    return value


def _sample_layout(rng, *, width: int, height: int, setting_id: str, required_zones: Sequence[str] = ()) -> Dict[str, Any]:
    layout_id = str(rng.choice(("curved_walk", "diagonal_walk", "playground_left", "pond_corner")))
    if str(setting_id) == "pond_playground":
        layout_id = str(rng.choice(("pond_corner", "curved_walk", "diagonal_walk")))
    path_y = float(rng.uniform(610.0, 710.0))
    path_amp = float(rng.uniform(34.0, 68.0))
    path_phase = float(rng.uniform(0.0, math.pi))
    if layout_id == "diagonal_walk":
        path_points = [
            (-40.0, float(height) * 0.82),
            (float(width) * 0.22, float(height) * 0.72),
            (float(width) * 0.52, float(height) * 0.66),
            (float(width) + 40.0, float(height) * 0.55),
        ]
    else:
        path_points = [
            (-40.0, path_y),
            (float(width) * 0.22, path_y - path_amp * 0.40),
            (float(width) * 0.50, path_y + path_amp * math.sin(path_phase)),
            (float(width) * 0.78, path_y - path_amp * 0.55),
            (float(width) + 40.0, path_y + path_amp * 0.20),
        ]
    if layout_id == "playground_left":
        playground_box = (60.0, 305.0, 510.0, 605.0)
        picnic_box = (760.0, 560.0, 1120.0, 760.0)
    elif layout_id == "pond_corner":
        playground_box = (650.0, 300.0, 1165.0, 600.0)
        picnic_box = (90.0, 560.0, 430.0, 760.0)
    else:
        playground_box = (float(rng.uniform(90.0, 170.0)), float(rng.uniform(295.0, 340.0)), float(rng.uniform(560.0, 670.0)), float(rng.uniform(575.0, 635.0)))
        picnic_box = (float(rng.uniform(760.0, 875.0)), float(rng.uniform(545.0, 610.0)), float(rng.uniform(1110.0, 1210.0)), float(rng.uniform(735.0, 810.0)))
    pond_box: BBox | None = None
    if str(setting_id) == "pond_playground" or layout_id == "pond_corner":
        pond_box = (float(rng.uniform(60.0, 150.0)), float(rng.uniform(320.0, 420.0)), float(rng.uniform(360.0, 500.0)), float(rng.uniform(500.0, 625.0)))
    if "pond" in {str(value) for value in required_zones} and pond_box is None:
        pond_box = (float(rng.uniform(62.0, 150.0)), float(rng.uniform(322.0, 410.0)), float(rng.uniform(360.0, 492.0)), float(rng.uniform(500.0, 620.0)))
    if layout_id == "playground_left":
        garden_box = (780.0, 300.0, 1188.0, 500.0)
    elif layout_id == "pond_corner":
        garden_box = (705.0, 625.0, 1150.0, 825.0)
    else:
        garden_box = (float(rng.uniform(520.0, 645.0)), float(rng.uniform(275.0, 335.0)), float(rng.uniform(930.0, 1060.0)), float(rng.uniform(455.0, 545.0)))
    return {
        "layout_id": layout_id,
        "path_points": [[round(float(x), 3), round(float(y), 3)] for x, y in path_points],
        "path_width": round(float(rng.uniform(52.0, 72.0)), 3),
        "playground_bbox": [round(float(v), 3) for v in playground_box],
        "picnic_bbox": [round(float(v), 3) for v in picnic_box],
        "garden_bbox": [round(float(v), 3) for v in garden_box],
        "pond_bbox": [round(float(v), 3) for v in pond_box] if pond_box else None,
    }


def _draw_background(draw: ImageDraw.ImageDraw, *, rng, setting_id: str, layout: Mapping[str, Any], width: int, height: int, scale: int) -> List[ParkDecor]:
    decor: List[ParkDecor] = []
    sky = _jitter_rgb(rng, (206, 229, 239), amount=10)
    grass = _jitter_rgb(rng, (128, 179, 113), amount=12)
    far_grass = _jitter_rgb(rng, (151, 196, 127), amount=12)
    s = int(scale)
    horizon = float(rng.uniform(190.0, 238.0))
    draw.rectangle((0, 0, int(width) * s, int(height) * s), fill=tuple(sky))
    draw.rectangle(_scale_bbox((0.0, horizon, float(width), float(height)), s), fill=tuple(grass))
    draw.rectangle(_scale_bbox((0.0, horizon, float(width), horizon + 42.0), s), fill=tuple(far_grass))
    for index in range(int(rng.randint(2, 5))):
        cx = float(rng.uniform(90.0, float(width) - 90.0))
        cy = float(rng.uniform(44.0, 135.0))
        cloud_w = float(rng.uniform(80.0, 140.0))
        cloud_h = float(rng.uniform(30.0, 48.0))
        for offset in (-0.28, 0.0, 0.26):
            _ellipse(draw, (cx + offset * cloud_w, cy, cx + offset * cloud_w + cloud_w * 0.48, cy + cloud_h), fill=(244, 248, 250), outline=None, width=1, scale=s)
    path_points = [(float(x), float(y)) for x, y in layout["path_points"]]
    path_width = int(round(float(layout["path_width"])))
    _line(draw, path_points, fill=_jitter_rgb(rng, (198, 182, 151), amount=10), width=path_width, scale=s)
    _line(draw, path_points, fill=_jitter_rgb(rng, (169, 151, 122), amount=8), width=max(3, int(path_width * 0.10)), scale=s)
    path_bbox = _bbox_union([(x - path_width * 0.5, y - path_width * 0.5, x + path_width * 0.5, y + path_width * 0.5) for x, y in path_points])
    decor.append(ParkDecor("decor_path", "walking_path", tuple(round(float(v), 3) for v in path_bbox), {"points": layout["path_points"], "width": float(path_width)}))
    playground = tuple(float(v) for v in layout["playground_bbox"])
    _ellipse(draw, playground, fill=_jitter_rgb(rng, (219, 186, 124), amount=12), outline=_jitter_rgb(rng, (139, 114, 84), amount=8), width=3, scale=s)
    decor.append(ParkDecor("decor_playground_zone", "playground_sand", tuple(round(float(v), 3) for v in playground), {}))
    picnic = tuple(float(v) for v in layout["picnic_bbox"])
    _rect(draw, picnic, fill=_jitter_rgb(rng, (132, 171, 118), amount=8), outline=_jitter_rgb(rng, (93, 128, 88), amount=7), width=2, scale=s, radius=18)
    blanket = (picnic[0] + 0.18 * (picnic[2] - picnic[0]), picnic[1] + 0.32 * (picnic[3] - picnic[1]), picnic[0] + 0.72 * (picnic[2] - picnic[0]), picnic[1] + 0.76 * (picnic[3] - picnic[1]))
    _rect(draw, blanket, fill=_jitter_rgb(rng, rng.choice(((205, 91, 86), (89, 138, 190), (219, 181, 84))), amount=8), outline=(92, 82, 76), width=2, scale=s, radius=8)
    decor.append(ParkDecor("decor_picnic_zone", "picnic_area", tuple(round(float(v), 3) for v in picnic), {"blanket_bbox": [round(float(v), 3) for v in blanket]}))
    garden = tuple(float(v) for v in layout["garden_bbox"])
    _ellipse(draw, garden, fill=_jitter_rgb(rng, (112, 157, 93), amount=8), outline=_jitter_rgb(rng, (69, 115, 66), amount=7), width=2, scale=s)
    for flower_index in range(int(rng.randint(10, 16))):
        px = float(rng.uniform(garden[0] + 16.0, garden[2] - 24.0))
        py = float(rng.uniform(garden[1] + 18.0, garden[3] - 28.0))
        _ellipse(
            draw,
            (px, py, px + 13.0, py + 11.0),
            fill=_jitter_rgb(rng, rng.choice(((219, 82, 117), (238, 197, 77), (146, 97, 177), (242, 134, 82))), amount=5),
            outline=None,
            width=1,
            scale=s,
        )
    decor.append(ParkDecor("decor_garden_zone", "garden_area", tuple(round(float(v), 3) for v in garden), {}))
    pond_raw = layout.get("pond_bbox")
    if isinstance(pond_raw, Sequence) and pond_raw:
        pond = tuple(float(v) for v in pond_raw)
        _ellipse(draw, pond, fill=_jitter_rgb(rng, (92, 169, 205), amount=10), outline=_jitter_rgb(rng, (60, 124, 159), amount=8), width=3, scale=s)
        for lily_index in range(int(rng.randint(2, 5))):
            lx = float(rng.uniform(pond[0] + 35.0, pond[2] - 45.0))
            ly = float(rng.uniform(pond[1] + 32.0, pond[3] - 36.0))
            leaf = (lx, ly, lx + 34.0, ly + 20.0)
            _ellipse(draw, leaf, fill=_jitter_rgb(rng, (73, 151, 91), amount=8), outline=(48, 105, 68), width=1, scale=s)
            decor.append(ParkDecor(f"decor_lily_{lily_index}", "lily_pad", tuple(round(float(v), 3) for v in leaf), {}))
        decor.append(ParkDecor("decor_pond", "pond", tuple(round(float(v), 3) for v in pond), {}))
    return decor


def _draw_slide(draw: ImageDraw.ImageDraw, *, rng, bbox: BBox, scale: int) -> None:
    x0, y0, x1, y1 = bbox
    outline = (61, 71, 82)
    ladder = (x0 + 0.08 * (x1 - x0), y0 + 0.14 * (y1 - y0), x0 + 0.34 * (x1 - x0), y1)
    platform = (x0 + 0.16 * (x1 - x0), y0 + 0.08 * (y1 - y0), x0 + 0.46 * (x1 - x0), y0 + 0.28 * (y1 - y0))
    slide = [(x0 + 0.40 * (x1 - x0), y0 + 0.24 * (y1 - y0)), (x1 - 0.06 * (x1 - x0), y1 - 0.06 * (y1 - y0)), (x1 - 0.28 * (x1 - x0), y1 - 0.06 * (y1 - y0)), (x0 + 0.28 * (x1 - x0), y0 + 0.28 * (y1 - y0))]
    _rect(draw, platform, fill=_jitter_rgb(rng, (216, 96, 82), amount=8), outline=outline, width=2, scale=scale, radius=6)
    for lx in (ladder[0], ladder[2]):
        _line(draw, [(lx, ladder[1]), (lx, ladder[3])], fill=outline, width=4, scale=scale)
    for rung_y in (0.35, 0.52, 0.69, 0.86):
        y = y0 + rung_y * (y1 - y0)
        _line(draw, [(ladder[0], y), (ladder[2], y)], fill=outline, width=3, scale=scale)
    _poly(draw, slide, fill=_jitter_rgb(rng, (229, 168, 67), amount=8), outline=outline, width=2, scale=scale)


def _draw_swing(draw: ImageDraw.ImageDraw, *, rng, bbox: BBox, scale: int) -> None:
    x0, y0, x1, y1 = bbox
    outline = (61, 71, 82)
    top = y0 + 0.12 * (y1 - y0)
    _line(draw, [(x0 + 0.10 * (x1 - x0), y1), (x0 + 0.28 * (x1 - x0), top), (x0 + 0.72 * (x1 - x0), top), (x0 + 0.90 * (x1 - x0), y1)], fill=outline, width=5, scale=scale)
    for center in (0.40, 0.62):
        sx = x0 + center * (x1 - x0)
        seat_y = y0 + 0.68 * (y1 - y0)
        _line(draw, [(sx - 22.0, top), (sx - 13.0, seat_y)], fill=outline, width=2, scale=scale)
        _line(draw, [(sx + 22.0, top), (sx + 13.0, seat_y)], fill=outline, width=2, scale=scale)
        _rect(draw, (sx - 30.0, seat_y, sx + 30.0, seat_y + 12.0), fill=_jitter_rgb(rng, (83, 139, 190), amount=8), outline=outline, width=1, scale=scale, radius=3)


def _draw_seesaw(draw: ImageDraw.ImageDraw, *, rng, bbox: BBox, scale: int) -> None:
    x0, y0, x1, y1 = bbox
    outline = (61, 71, 82)
    pivot = [(0.5 * (x0 + x1), y0 + 0.48 * (y1 - y0)), (x0 + 0.39 * (x1 - x0), y1), (x0 + 0.61 * (x1 - x0), y1)]
    _poly(draw, pivot, fill=_jitter_rgb(rng, (142, 105, 77), amount=8), outline=outline, width=2, scale=scale)
    _line(draw, [(x0 + 0.10 * (x1 - x0), y0 + 0.40 * (y1 - y0)), (x1 - 0.10 * (x1 - x0), y0 + 0.64 * (y1 - y0))], fill=_jitter_rgb(rng, (218, 111, 82), amount=8), width=13, scale=scale)


def _draw_climber(draw: ImageDraw.ImageDraw, *, rng, bbox: BBox, scale: int) -> None:
    x0, y0, x1, y1 = bbox
    outline = _jitter_rgb(rng, (70, 82, 96), amount=6)
    cx = 0.5 * (x0 + x1)
    base_y = y1
    top = (cx, y0 + 0.12 * (y1 - y0))
    base = [(x0 + 0.12 * (x1 - x0), base_y), (x1 - 0.12 * (x1 - x0), base_y), top]
    for point in base[:2]:
        _line(draw, [top, point], fill=outline, width=4, scale=scale)
    for frac in (0.32, 0.50, 0.68, 0.84):
        y = y0 + frac * (y1 - y0)
        span = (y - top[1]) / max(1.0, base_y - top[1])
        left_x = cx - span * (cx - base[0][0])
        right_x = cx + span * (base[1][0] - cx)
        _line(draw, [(left_x, y), (right_x, y)], fill=outline, width=3, scale=scale)


def _draw_equipment(draw: ImageDraw.ImageDraw, *, rng, equipment_type: str, bbox: BBox, scale: int) -> None:
    if equipment_type == "slide":
        _draw_slide(draw, rng=rng, bbox=bbox, scale=scale)
    elif equipment_type == "swing_set":
        _draw_swing(draw, rng=rng, bbox=bbox, scale=scale)
    elif equipment_type == "seesaw":
        _draw_seesaw(draw, rng=rng, bbox=bbox, scale=scale)
    else:
        _draw_climber(draw, rng=rng, bbox=bbox, scale=scale)


def _equipment_boxes(rng, *, playground: BBox, count: int) -> Tuple[BBox, ...]:
    columns = 3 if int(count) >= 5 else 2
    rows = max(1, (int(count) + columns - 1) // columns)
    gap_x = 18.0
    gap_y = 12.0
    inner = (playground[0] + 28.0, playground[1] + 34.0, playground[2] - 24.0, playground[3] - 18.0)
    cell_w = max(86.0, (inner[2] - inner[0] - float(columns - 1) * gap_x) / float(columns))
    cell_h = max(74.0, (inner[3] - inner[1] - float(rows - 1) * gap_y) / float(rows))
    boxes: List[BBox] = []
    for index in range(int(count)):
        col = index % columns
        row = index // columns
        x0 = inner[0] + float(col) * (cell_w + gap_x) + float(rng.uniform(-7.0, 7.0))
        y0 = inner[1] + float(row) * (cell_h + gap_y) + float(rng.uniform(-5.0, 6.0))
        ew = min(cell_w - 6.0, float(rng.uniform(94.0, 138.0)))
        eh = min(cell_h - 4.0, float(rng.uniform(74.0, 116.0)))
        boxes.append((round(x0, 3), round(y0, 3), round(min(inner[2], x0 + ew), 3), round(min(inner[3], y0 + eh), 3)))
    return tuple(boxes)


def _draw_equipment_and_fixtures(
    draw: ImageDraw.ImageDraw,
    *,
    rng,
    layout: Mapping[str, Any],
    width: int,
    height: int,
    scale: int,
    equipment_specs: Sequence[ParkEquipmentSpec] | None = None,
) -> List[ParkDecor]:
    decor: List[ParkDecor] = []
    playground = tuple(float(v) for v in layout["playground_bbox"])
    if equipment_specs is None:
        equipment_types = [str(value) for value in rng.sample(PARK_EQUIPMENT_TYPES, k=int(rng.randint(2, 4)))]
        resolved_specs = tuple(ParkEquipmentSpec(equipment_type=str(value), role="decor") for value in equipment_types)
    else:
        resolved_specs = tuple(equipment_specs)
    boxes = _equipment_boxes(rng, playground=playground, count=len(resolved_specs))
    ordered = list(zip(resolved_specs, boxes))
    rng.shuffle(ordered)
    for index, (equipment_spec, box) in enumerate(ordered):
        equipment_type = str(equipment_spec.equipment_type)
        _draw_equipment(draw, rng=rng, equipment_type=equipment_type, bbox=box, scale=scale)
        decor.append(
            ParkDecor(
                f"equipment_{index:02d}",
                equipment_type,
                tuple(round(float(v), 3) for v in box),
                {"zone": "playground", "role": str(equipment_spec.role), **dict(equipment_spec.attributes)},
            )
        )
    tree_count = int(rng.randint(4, 8))
    for index in range(tree_count):
        x = float(rng.uniform(28.0, float(width) - 82.0))
        y = float(rng.uniform(245.0, float(height) - 160.0))
        h = float(rng.uniform(100.0, 165.0))
        w = h * float(rng.uniform(0.65, 0.90))
        box = (x, y, x + w, y + h)
        trunk = (x + 0.43 * w, y + 0.52 * h, x + 0.58 * w, y + 0.96 * h)
        _rect(draw, trunk, fill=_jitter_rgb(rng, (117, 78, 49), amount=8), outline=(80, 60, 43), width=1, scale=scale, radius=4)
        for lx, ly in ((0.28, 0.20), (0.52, 0.12), (0.68, 0.30), (0.38, 0.39), (0.58, 0.46)):
            leaf = (x + (lx - 0.20) * w, y + (ly - 0.15) * h, x + (lx + 0.20) * w, y + (ly + 0.18) * h)
            _ellipse(draw, leaf, fill=_jitter_rgb(rng, (71, 139, 80), amount=12), outline=(51, 103, 60), width=1, scale=scale)
        decor.append(ParkDecor(f"decor_tree_{index}", "tree", tuple(round(float(v), 3) for v in box), {}))
    fixture_count = int(rng.randint(3, 6))
    for index in range(fixture_count):
        fixture_type = str(rng.choice(("bench", "lamp_post", "flower_bed")))
        x = float(rng.uniform(56.0, float(width) - 170.0))
        y = float(rng.uniform(625.0, float(height) - 88.0))
        if fixture_type == "bench":
            box = (x, y, x + 130.0, y + 52.0)
            _draw_bench(draw, rng=rng, bbox=box, scale=scale)
        elif fixture_type == "lamp_post":
            box = (x, y - 110.0, x + 38.0, y + 20.0)
            _line(draw, [(x + 18.0, y - 88.0), (x + 18.0, y + 18.0)], fill=(74, 82, 91), width=5, scale=scale)
            _ellipse(draw, (x + 4.0, y - 122.0, x + 34.0, y - 88.0), fill=(246, 220, 122), outline=(74, 82, 91), width=2, scale=scale)
        else:
            box = (x, y, x + 148.0, y + 48.0)
            _ellipse(draw, box, fill=_jitter_rgb(rng, (93, 148, 81), amount=8), outline=(65, 111, 65), width=1, scale=scale)
            for petal in range(8):
                px = x + float(rng.uniform(16.0, 132.0))
                py = y + float(rng.uniform(10.0, 34.0))
                _ellipse(draw, (px, py, px + 12.0, py + 10.0), fill=_jitter_rgb(rng, rng.choice(((221, 85, 114), (238, 197, 77), (145, 97, 177))), amount=5), outline=None, width=1, scale=scale)
        decor.append(ParkDecor(f"decor_fixture_{index}", fixture_type, tuple(round(float(v), 3) for v in box), {}))
    return decor


def _draw_bench(draw: ImageDraw.ImageDraw, *, rng, bbox: BBox, scale: int) -> None:
    x0, y0, x1, y1 = bbox
    wood = _jitter_rgb(rng, (146, 92, 58), amount=10)
    outline = _jitter_rgb(rng, (75, 56, 43), amount=6)
    _rect(draw, (x0, y0 + 0.20 * (y1 - y0), x1, y0 + 0.44 * (y1 - y0)), fill=wood, outline=outline, width=1, scale=scale, radius=5)
    _rect(draw, (x0 + 8.0, y0 + 0.52 * (y1 - y0), x1 - 8.0, y0 + 0.72 * (y1 - y0)), fill=wood, outline=outline, width=1, scale=scale, radius=5)
    for lx in (x0 + 18.0, x1 - 30.0):
        _rect(draw, (lx, y0 + 0.70 * (y1 - y0), lx + 10.0, y1), fill=outline, outline=None, width=1, scale=scale, radius=2)


def _path_point(rng, layout: Mapping[str, Any]) -> Tuple[float, float]:
    points = [(float(x), float(y)) for x, y in layout["path_points"]]
    segment = int(rng.randint(0, max(0, len(points) - 2)))
    t = float(rng.uniform(0.05, 0.95))
    x0, y0 = points[segment]
    x1, y1 = points[segment + 1]
    return (x0 + t * (x1 - x0), y0 + t * (y1 - y0))


def _zone_bbox(layout: Mapping[str, Any], zone: str) -> BBox | None:
    if str(zone) == "playground":
        return tuple(float(v) for v in layout["playground_bbox"])  # type: ignore[return-value]
    if str(zone) == "picnic":
        return tuple(float(v) for v in layout["picnic_bbox"])  # type: ignore[return-value]
    if str(zone) == "garden":
        return tuple(float(v) for v in layout["garden_bbox"])  # type: ignore[return-value]
    return None


def _zone_for_point(layout: Mapping[str, Any], point: Tuple[float, float]) -> str:
    px, py = float(point[0]), float(point[1])
    for zone in PARK_ZONE_TYPES:
        box = _zone_bbox(layout, str(zone))
        if box and box[0] <= px <= box[2] and box[1] <= py <= box[3]:
            return str(zone)
    return "open_lawn"


def _equipment_user_box(
    rng,
    *,
    equipment_decor: Sequence[ParkDecor],
    equipment_type: str,
    activity: str,
    width: int,
    height: int,
) -> BBox | None:
    matches = tuple(
        item
        for item in equipment_decor
        if str(item.decor_id).startswith("equipment_") and str(item.decor_type) == str(equipment_type)
    )
    if not matches:
        return None
    item = rng.choice(matches)
    ex0, ey0, ex1, ey1 = (float(v) for v in item.bbox_xyxy)
    ew = max(1.0, ex1 - ex0)
    eh = max(1.0, ey1 - ey0)
    if str(equipment_type) == "slide":
        person_h = float(rng.uniform(68.0, 88.0))
        person_w = person_h * float(rng.uniform(0.50, 0.62))
        cx = ex0 + ew * float(rng.uniform(0.42, 0.78))
        bottom = ey0 + eh * float(rng.uniform(0.66, 0.94))
    elif str(equipment_type) == "swing_set":
        person_h = float(rng.uniform(60.0, 78.0)) if str(activity) == "sitting" else float(rng.uniform(68.0, 86.0))
        person_w = person_h * float(rng.uniform(0.60, 0.76))
        seat_fraction = float(rng.choice((0.36, 0.62)))
        cx = ex0 + ew * seat_fraction + float(rng.uniform(-0.05, 0.05)) * ew
        bottom = ey0 + eh * float(rng.uniform(0.78, 0.96))
    elif str(equipment_type) == "seesaw":
        person_h = float(rng.uniform(60.0, 78.0)) if str(activity) == "sitting" else float(rng.uniform(68.0, 86.0))
        person_w = person_h * float(rng.uniform(0.60, 0.78))
        end_fraction = float(rng.choice((0.24, 0.76)))
        cx = ex0 + ew * end_fraction + float(rng.uniform(-0.04, 0.04)) * ew
        bottom = ey0 + eh * float(rng.uniform(0.70, 0.88))
    else:
        person_h = float(rng.uniform(70.0, 90.0))
        person_w = person_h * float(rng.uniform(0.48, 0.62))
        cx = ex0 + ew * float(rng.uniform(0.30, 0.70))
        bottom = ey0 + eh * float(rng.uniform(0.58, 0.88))
    x0 = max(30.0, min(float(width) - person_w - 30.0, cx - person_w * 0.5))
    y1 = max(320.0, min(float(height) - 20.0, bottom))
    return (round(x0, 3), round(y1 - person_h, 3), round(x0 + person_w, 3), round(y1, 3))


def _candidate_person_box(
    rng,
    *,
    activity: str,
    layout: Mapping[str, Any],
    width: int,
    height: int,
    zone: str | None = None,
    equipment_decor: Sequence[ParkDecor] = (),
    equipment_type: str | None = None,
) -> BBox:
    if equipment_type is not None:
        equipment_box = _equipment_user_box(
            rng,
            equipment_decor=equipment_decor,
            equipment_type=str(equipment_type),
            activity=str(activity),
            width=int(width),
            height=int(height),
        )
        if equipment_box is not None:
            return equipment_box
    zone_box = _zone_bbox(layout, str(zone)) if zone else None
    if zone_box is not None:
        person_h = float(rng.uniform(76.0, 104.0))
        if str(activity) == "sitting":
            person_h = float(rng.uniform(66.0, 86.0))
        person_w = person_h * float(rng.uniform(0.52, 0.74))
        cx_low = min(zone_box[2] - 24.0, zone_box[0] + max(34.0, 0.55 * person_w))
        cx_high = max(cx_low, zone_box[2] - max(34.0, 0.55 * person_w))
        bottom_low = min(zone_box[3] - 8.0, zone_box[1] + person_h + 12.0)
        bottom_high = max(bottom_low, zone_box[3] - 8.0)
        cx = float(rng.uniform(cx_low, cx_high))
        bottom = float(rng.uniform(bottom_low, bottom_high))
    elif str(activity) == "sitting":
        person_h = float(rng.uniform(68.0, 88.0))
        person_w = person_h * float(rng.uniform(0.68, 0.84))
        if float(rng.random()) < 0.55:
            picnic = tuple(float(v) for v in layout["picnic_bbox"])
            cx = float(rng.uniform(picnic[0] + 40.0, picnic[2] - 40.0))
            bottom = float(rng.uniform(picnic[1] + 110.0, min(picnic[3] + 28.0, float(height) - 40.0)))
        else:
            cx = float(rng.uniform(110.0, float(width) - 110.0))
            bottom = float(rng.uniform(float(height) * 0.69, float(height) - 46.0))
    elif str(activity) == "walking":
        person_h = float(rng.uniform(88.0, 112.0))
        person_w = person_h * float(rng.uniform(0.48, 0.60))
        cx, cy = _path_point(rng, layout)
        cx += float(rng.uniform(-34.0, 34.0))
        bottom = cy + float(rng.uniform(28.0, 48.0))
    elif str(activity) == "playing_ball":
        person_h = float(rng.uniform(84.0, 108.0))
        person_w = person_h * float(rng.uniform(0.50, 0.62))
        if float(rng.random()) < 0.65:
            playground = tuple(float(v) for v in layout["playground_bbox"])
            cx = float(rng.uniform(playground[0] + 38.0, playground[2] - 38.0))
            bottom = float(rng.uniform(playground[1] + 150.0, playground[3] + 42.0))
        else:
            cx = float(rng.uniform(110.0, float(width) - 110.0))
            bottom = float(rng.uniform(560.0, float(height) - 50.0))
    else:
        person_h = float(rng.uniform(88.0, 114.0))
        person_w = person_h * float(rng.uniform(0.48, 0.58))
        cx = float(rng.uniform(90.0, float(width) - 90.0))
        bottom = float(rng.uniform(500.0, float(height) - 44.0))
    x0 = max(30.0, min(float(width) - person_w - 30.0, cx - person_w * 0.5))
    y1 = max(360.0, min(float(height) - 20.0, bottom))
    return (round(x0, 3), round(y1 - person_h, 3), round(x0 + person_w, 3), round(y1, 3))


def _place_persons(
    rng,
    *,
    specs: Sequence[ParkPersonSpec],
    layout: Mapping[str, Any],
    width: int,
    height: int,
    equipment_decor: Sequence[ParkDecor] = (),
) -> Tuple[Tuple[ParkPersonSpec, BBox, str], ...]:
    placed: List[Tuple[ParkPersonSpec, BBox, str]] = []
    existing: List[BBox] = []
    ordered = list(specs)
    rng.shuffle(ordered)
    for index, spec in enumerate(ordered):
        box: BBox | None = None
        last_candidate: BBox | None = None
        requested_zone = spec.attributes.get("zone")
        equipment_type = spec.attributes.get("using_equipment_type")
        zone = "playground" if equipment_type is not None else (str(requested_zone) if requested_zone is not None else None)
        for attempt in range(220):
            candidate = _candidate_person_box(
                rng,
                activity=str(spec.activity),
                layout=layout,
                width=width,
                height=height,
                zone=zone,
                equipment_decor=equipment_decor,
                equipment_type=str(equipment_type) if equipment_type is not None else None,
            )
            candidate = _clamp_bbox_to_canvas(candidate, width=int(width), height=int(height))
            last_candidate = candidate
            gap = 12.0 if int(attempt) < 130 else 5.0 if int(attempt) < 190 else 0.0
            if all(not _expanded_intersects(candidate, other, gap) for other in existing):
                box = candidate
                break
        if box is None:
            if last_candidate is not None:
                box = last_candidate
            else:
                col = index % 6
                row = index // 6
                px = 88.0 + col * 190.0
                py = 500.0 + row * 160.0
                box = _clamp_bbox_to_canvas((px, py, px + 56.0, py + 96.0), width=int(width), height=int(height))
        existing.append(tuple(float(v) for v in box))
        center = (0.5 * (float(box[0]) + float(box[2])), 0.5 * (float(box[1]) + float(box[3])))
        resolved_zone = zone if zone in set(PARK_ZONE_TYPES) else _zone_for_point(layout, center)
        placed.append((spec, tuple(float(v) for v in box), str(resolved_zone)))
    return tuple(placed)


def _skin_color(rng) -> RGB:
    return tuple(int(v) for v in rng.choice(((200, 145, 101), (169, 111, 82), (219, 164, 113), (136, 89, 68), (232, 181, 130))))  # type: ignore[return-value]


def _clothes_color(rng) -> RGB:
    return tuple(int(v) for v in rng.choice(((74, 122, 180), (194, 83, 85), (220, 169, 75), (94, 151, 124), (130, 104, 160), (83, 154, 177))))  # type: ignore[return-value]


def _draw_shadow(draw: ImageDraw.ImageDraw, bbox: BBox, *, scale: int) -> None:
    x0, y0, x1, y1 = bbox
    _ellipse(draw, (x0 + 0.08 * (x1 - x0), y1 - 0.08 * (y1 - y0), x1 - 0.06 * (x1 - x0), y1 + 0.04 * (y1 - y0)), fill=(102, 126, 102), outline=None, width=1, scale=scale)


def _rel(box: BBox, x0: float, y0: float, x1: float, y1: float) -> BBox:
    bx0, by0, bx1, by1 = box
    w = bx1 - bx0
    h = by1 - by0
    return (bx0 + x0 * w, by0 + y0 * h, bx0 + x1 * w, by0 + y1 * h)


def _draw_activity_support(draw: ImageDraw.ImageDraw, *, rng, person_id: str, activity: str, bbox: BBox, scale: int) -> Tuple[ParkDecor, ...]:
    x0, y0, x1, y1 = bbox
    decor: List[ParkDecor] = []
    if str(activity) == "sitting":
        bench = (x0 - 24.0, y0 + 0.47 * (y1 - y0), x1 + 34.0, y0 + 0.86 * (y1 - y0))
        _draw_bench(draw, rng=rng, bbox=bench, scale=scale)
        decor.append(ParkDecor(f"{person_id}_bench", "activity_bench", tuple(round(float(v), 3) for v in bench), {"supports_person_id": str(person_id)}))
    if str(activity) == "playing_ball":
        ball_size = max(18.0, 0.20 * (y1 - y0))
        side = -1.0 if float(rng.random()) < 0.5 else 1.0
        bx = x0 - ball_size * 0.9 if side < 0 else x1 + ball_size * 0.25
        by = y1 - ball_size * float(rng.uniform(0.75, 1.05))
        ball = (bx, by, bx + ball_size, by + ball_size)
        _ellipse(draw, ball, fill=_jitter_rgb(rng, (236, 128, 71), amount=8), outline=(65, 71, 80), width=2, scale=scale)
        _line(draw, [(ball[0] + 0.18 * ball_size, ball[1] + 0.50 * ball_size), (ball[2] - 0.18 * ball_size, ball[1] + 0.50 * ball_size)], fill=(65, 71, 80), width=1, scale=scale)
        decor.append(ParkDecor(f"{person_id}_ball", "activity_ball", tuple(round(float(v), 3) for v in ball), {"supports_person_id": str(person_id)}))
    return tuple(decor)


def _draw_activity_person(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: BBox,
    activity: str,
    primary: RGB,
    accent: RGB,
    skin: RGB,
    style_id: str,
    gender_id: str,
    scale: int,
) -> None:
    outline, line_width, shadow = _style_params(str(style_id))
    if shadow:
        _draw_shadow(draw, bbox, scale=scale)
    x0, y0, x1, y1 = bbox
    gender = normalize_person_gender(gender_id)
    if str(activity) == "sitting":
        head = _rel(bbox, 0.31, 0.04, 0.69, 0.32)
        body = _rel(bbox, 0.28, 0.32, 0.76, 0.56 if gender == "female" else 0.62)
        draw_person_hair_back(draw, head_bbox=head, gender_id=gender, scale=scale, outline=outline)
        _ellipse(draw, head, fill=skin, outline=outline, width=line_width, scale=scale)
        draw_person_hair_front(draw, head_bbox=head, gender_id=gender, scale=scale, outline=outline)
        _rect(draw, body, fill=primary, outline=outline, width=line_width, scale=scale, radius=8)
        for arm in (_rel(bbox, 0.14, 0.40, 0.31, 0.64), _rel(bbox, 0.72, 0.40, 0.92, 0.62)):
            _line(draw, [(arm[0], arm[1]), (arm[2], arm[3])], fill=primary, width=max(3, line_width + 1), scale=scale)
        leg_color = (65, 74, 91)
        _line(draw, [(x0 + 0.40 * (x1 - x0), y0 + 0.62 * (y1 - y0)), (x0 + 0.25 * (x1 - x0), y0 + 0.87 * (y1 - y0)), (x0 + 0.55 * (x1 - x0), y0 + 0.90 * (y1 - y0))], fill=leg_color, width=max(5, line_width + 3), scale=scale)
        _line(draw, [(x0 + 0.60 * (x1 - x0), y0 + 0.62 * (y1 - y0)), (x0 + 0.75 * (x1 - x0), y0 + 0.86 * (y1 - y0)), (x0 + 0.96 * (x1 - x0), y0 + 0.84 * (y1 - y0))], fill=leg_color, width=max(5, line_width + 3), scale=scale)
        if gender == "female":
            draw_person_skirt(draw, torso_bbox=body, bottom_y=y0 + 0.70 * (y1 - y0), fill=primary, outline=outline, scale=scale, width=line_width)
        return
    head = _rel(bbox, 0.31, 0.04, 0.69, 0.27)
    torso = _rel(bbox, 0.29, 0.28, 0.72, 0.52 if gender == "female" else 0.58)
    draw_person_hair_back(draw, head_bbox=head, gender_id=gender, scale=scale, outline=outline)
    _ellipse(draw, head, fill=skin, outline=outline, width=line_width, scale=scale)
    draw_person_hair_front(draw, head_bbox=head, gender_id=gender, scale=scale, outline=outline)
    _rect(draw, torso, fill=primary, outline=outline, width=line_width, scale=scale, radius=8)
    leg_color = (65, 74, 91)
    if str(activity) == "walking":
        _line(draw, [(x0 + 0.42 * (x1 - x0), y0 + 0.56 * (y1 - y0)), (x0 + 0.22 * (x1 - x0), y0 + 0.92 * (y1 - y0))], fill=leg_color, width=max(5, line_width + 3), scale=scale)
        _line(draw, [(x0 + 0.58 * (x1 - x0), y0 + 0.56 * (y1 - y0)), (x0 + 0.80 * (x1 - x0), y0 + 0.90 * (y1 - y0))], fill=leg_color, width=max(5, line_width + 3), scale=scale)
        _line(draw, [(x0 + 0.30 * (x1 - x0), y0 + 0.35 * (y1 - y0)), (x0 + 0.12 * (x1 - x0), y0 + 0.58 * (y1 - y0))], fill=primary, width=max(4, line_width + 2), scale=scale)
        _line(draw, [(x0 + 0.70 * (x1 - x0), y0 + 0.36 * (y1 - y0)), (x0 + 0.88 * (x1 - x0), y0 + 0.54 * (y1 - y0))], fill=primary, width=max(4, line_width + 2), scale=scale)
    elif str(activity) == "playing_ball":
        _line(draw, [(x0 + 0.38 * (x1 - x0), y0 + 0.56 * (y1 - y0)), (x0 + 0.28 * (x1 - x0), y0 + 0.92 * (y1 - y0))], fill=leg_color, width=max(5, line_width + 3), scale=scale)
        _line(draw, [(x0 + 0.60 * (x1 - x0), y0 + 0.56 * (y1 - y0)), (x0 + 0.82 * (x1 - x0), y0 + 0.80 * (y1 - y0))], fill=leg_color, width=max(5, line_width + 3), scale=scale)
        _line(draw, [(x0 + 0.30 * (x1 - x0), y0 + 0.38 * (y1 - y0)), (x0 - 0.02 * (x1 - x0), y0 + 0.26 * (y1 - y0))], fill=primary, width=max(4, line_width + 2), scale=scale)
        _line(draw, [(x0 + 0.71 * (x1 - x0), y0 + 0.38 * (y1 - y0)), (x0 + 1.03 * (x1 - x0), y0 + 0.28 * (y1 - y0))], fill=primary, width=max(4, line_width + 2), scale=scale)
        _ellipse(draw, _rel(bbox, 0.36, 0.00, 0.64, 0.09), fill=accent, outline=outline, width=1, scale=scale)
    else:
        _line(draw, [(x0 + 0.42 * (x1 - x0), y0 + 0.56 * (y1 - y0)), (x0 + 0.38 * (x1 - x0), y0 + 0.92 * (y1 - y0))], fill=leg_color, width=max(5, line_width + 3), scale=scale)
        _line(draw, [(x0 + 0.58 * (x1 - x0), y0 + 0.56 * (y1 - y0)), (x0 + 0.62 * (x1 - x0), y0 + 0.92 * (y1 - y0))], fill=leg_color, width=max(5, line_width + 3), scale=scale)
        _line(draw, [(x0 + 0.30 * (x1 - x0), y0 + 0.35 * (y1 - y0)), (x0 + 0.18 * (x1 - x0), y0 + 0.62 * (y1 - y0))], fill=primary, width=max(4, line_width + 2), scale=scale)
        _line(draw, [(x0 + 0.70 * (x1 - x0), y0 + 0.35 * (y1 - y0)), (x0 + 0.82 * (x1 - x0), y0 + 0.62 * (y1 - y0))], fill=primary, width=max(4, line_width + 2), scale=scale)
    if gender == "female":
        draw_person_skirt(draw, torso_bbox=torso, bottom_y=y0 + 0.72 * (y1 - y0), fill=primary, outline=outline, scale=scale, width=line_width)


def render_park_playground_scene(
    *,
    rng,
    person_specs: Sequence[ParkPersonSpec],
    equipment_specs: Sequence[ParkEquipmentSpec] | None = None,
    required_zones: Sequence[str] = (),
    canvas_width: int = 1280,
    canvas_height: int = 900,
    render_scale: int = 2,
    setting_weights: Mapping[str, float] | None = None,
    style_weights: Mapping[str, float] | None = None,
) -> RenderedParkPlaygroundScene:
    """Render one synthetic park/playground scene from semantic person specs."""

    width = int(canvas_width)
    height = int(canvas_height)
    scale = max(1, int(render_scale))
    if not person_specs:
        raise ValueError("park playground scene needs at least one person")
    setting_id = _choose_weighted(rng, setting_weights or {setting: 1.0 for setting in PARK_SETTING_IDS}, PARK_SETTING_IDS)
    style_id = _choose_weighted(rng, style_weights or {style: 1.0 for style in STYLE_IDS}, STYLE_IDS)
    layout = _sample_layout(rng, width=width, height=height, setting_id=str(setting_id), required_zones=tuple(required_zones))
    image = Image.new("RGB", (width * scale, height * scale), (232, 238, 221))
    draw = ImageDraw.Draw(image)
    decor: List[ParkDecor] = []
    decor.extend(_draw_background(draw, rng=rng, setting_id=str(setting_id), layout=layout, width=width, height=height, scale=scale))
    decor.extend(_draw_equipment_and_fixtures(draw, rng=rng, layout=layout, width=width, height=height, scale=scale, equipment_specs=equipment_specs))
    equipment_decor = tuple(item for item in decor if str(item.decor_id).startswith("equipment_"))
    placed = _place_persons(rng, specs=person_specs, layout=layout, width=width, height=height, equipment_decor=equipment_decor)
    persons: List[ParkPerson] = []
    placed_sorted = sorted(placed, key=lambda item: (float(item[1][3]), float(item[1][0])))
    for index, (spec, bbox, _zone) in enumerate(placed_sorted):
        if bool(spec.attributes.get("suppress_activity_support", False)):
            continue
        person_id = f"person_{index:02d}"
        decor.extend(_draw_activity_support(draw, rng=rng, person_id=person_id, activity=str(spec.activity), bbox=bbox, scale=scale))
    for index, (spec, bbox, zone) in enumerate(placed_sorted):
        person_id = f"person_{index:02d}"
        primary = _clothes_color(rng)
        accent = _clothes_color(rng)
        skin = _skin_color(rng)
        gender_id = sample_person_gender(rng)
        _draw_activity_person(
            draw,
            bbox=bbox,
            activity=str(spec.activity),
            primary=primary,
            accent=accent,
            skin=skin,
            style_id=str(style_id),
            gender_id=str(gender_id),
            scale=scale,
        )
        persons.append(
            ParkPerson(
                person_id=person_id,
                activity=str(spec.activity),
                activity_label=park_activity_display_name(str(spec.activity)),
                bbox_xyxy=tuple(round(float(v), 3) for v in bbox),
                primary_color_rgb=tuple(int(v) for v in primary),
                accent_color_rgb=tuple(int(v) for v in accent),
                skin_color_rgb=tuple(int(v) for v in skin),
                style_id=str(style_id),
                gender_id=str(gender_id),
                role=str(spec.role),
                attributes={**dict(spec.attributes), "zone": str(zone)},
            )
        )
    if scale != 1:
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    return RenderedParkPlaygroundScene(
        image=image,
        setting_id=str(setting_id),
        persons=tuple(persons),
        decor=tuple(decor),
        canvas_width=width,
        canvas_height=height,
        render_scale=scale,
        style_id=str(style_id),
        layout=dict(layout),
    )


def park_person_bbox_map(scene: RenderedParkPlaygroundScene) -> Dict[str, List[float]]:
    """Return person bboxes keyed by person id."""

    return {str(person.person_id): [round(float(v), 3) for v in person.bbox_xyxy] for person in scene.persons}


def park_decor_bbox_map(scene: RenderedParkPlaygroundScene) -> Dict[str, List[float]]:
    """Return decor bboxes keyed by decor id."""

    return {str(item.decor_id): [round(float(v), 3) for v in item.bbox_xyxy] for item in scene.decor}


def sort_park_bboxes(bbox_map: Mapping[str, Sequence[float]], ids: Iterable[str]) -> List[List[float]]:
    """Return bboxes sorted top-to-bottom then left-to-right for stable evidence."""

    boxes = [list(float(v) for v in bbox_map[str(item_id)]) for item_id in ids]
    boxes.sort(key=lambda box: (round(float(box[1]), 3), round(float(box[0]), 3), round(float(box[3]), 3), round(float(box[2]), 3)))
    return [[round(float(v), 3) for v in box] for box in boxes]


def park_scene_entities(scene: RenderedParkPlaygroundScene) -> List[Dict[str, Any]]:
    """Return generic entity records for the scene trace."""

    entities: List[Dict[str, Any]] = []
    for person in scene.persons:
        object_record = make_object_record(
            object_id=str(person.person_id),
            object_type="person",
            bbox_xyxy=person.bbox_xyxy,
            semantic_attributes={
                "activity": str(person.activity),
                "activity_label": str(person.activity_label),
                **dict(person.attributes),
            },
            visual_attributes={
                "primary_color_rgb": [int(v) for v in person.primary_color_rgb],
                "accent_color_rgb": [int(v) for v in person.accent_color_rgb],
                "skin_color_rgb": [int(v) for v in person.skin_color_rgb],
                "style_id": str(person.style_id),
                "gender_id": str(person.gender_id),
            },
            role=str(person.role),
            source_entity_type="park_person",
        ).as_dict()
        entities.append(
            {
                "entity_id": str(person.person_id),
                "entity_type": "park_person",
                "activity": str(person.activity),
                "activity_label": str(person.activity_label),
                "bbox": [round(float(v), 3) for v in person.bbox_xyxy],
                "role": str(person.role),
                "attributes": _safe_json(person.attributes),
                "object_record": object_record,
            }
        )
    for item in scene.decor:
        object_type = _decor_object_type(str(item.decor_type))
        semantic_attributes = {
            "decor_type": str(item.decor_type),
            **dict(item.attributes),
        }
        if object_type == "playground_equipment":
            semantic_attributes["equipment_type"] = str(item.decor_type)
            semantic_attributes["equipment_label"] = park_equipment_display_name(str(item.decor_type))
        object_record = make_object_record(
            object_id=str(item.decor_id),
            object_type=object_type,
            bbox_xyxy=item.bbox_xyxy,
            semantic_attributes=semantic_attributes,
            role=str(item.attributes.get("role", "distractor")),
            source_entity_type="park_decor",
        ).as_dict()
        entities.append(
            {
                "entity_id": str(item.decor_id),
                "entity_type": "park_decor",
                "decor_type": str(item.decor_type),
                "bbox": [round(float(v), 3) for v in item.bbox_xyxy],
                "attributes": _safe_json(item.attributes),
                "object_record": object_record,
            }
        )
    return entities


def serialize_park_scene(scene: RenderedParkPlaygroundScene) -> Tuple[List[Dict[str, Any]], Dict[str, List[float]]]:
    """Serialize park scene records and person bbox map."""

    person_records = [
        {
            "person_id": str(person.person_id),
            "activity": str(person.activity),
            "activity_label": str(person.activity_label),
            "bbox": [round(float(v), 3) for v in person.bbox_xyxy],
            "primary_color_rgb": [int(v) for v in person.primary_color_rgb],
            "accent_color_rgb": [int(v) for v in person.accent_color_rgb],
            "skin_color_rgb": [int(v) for v in person.skin_color_rgb],
            "style_id": str(person.style_id),
            "gender_id": str(person.gender_id),
            "role": str(person.role),
            "attributes": _safe_json(person.attributes),
        }
        for person in scene.persons
    ]
    decor_records = [
        {
            "decor_id": str(item.decor_id),
            "decor_type": str(item.decor_type),
            "bbox": [round(float(v), 3) for v in item.bbox_xyxy],
            "attributes": _safe_json(item.attributes),
        }
        for item in scene.decor
    ]
    return (
        [
            {
                "setting_id": str(scene.setting_id),
                "layout": _safe_json(scene.layout),
                "persons": person_records,
                "decor": decor_records,
            }
        ],
        park_person_bbox_map(scene),
    )


__all__ = [
    "PARK_EQUIPMENT_LABELS",
    "PARK_EQUIPMENT_TYPES",
    "PARK_PERSON_ACTIVITIES",
    "PARK_PERSON_ACTIVITY_LABELS",
    "PARK_SETTING_IDS",
    "PARK_ZONE_LABELS",
    "PARK_ZONE_TYPES",
    "ParkEquipmentSpec",
    "ParkPersonSpec",
    "RenderedParkPlaygroundScene",
    "park_activity_display_name",
    "park_decor_bbox_map",
    "park_equipment_display_name",
    "park_person_bbox_map",
    "park_scene_entities",
    "park_zone_display_name",
    "render_park_playground_scene",
    "serialize_park_scene",
    "sort_park_bboxes",
]
