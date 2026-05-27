"""Construction-site illustration scene with workers, materials, and equipment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from .object_catalog import label_map_for_tag, plural_name_map_for_tag, variant_ids_with_tag
from .object_library import BBox, RGB, STYLE_IDS
from .object_registry import make_object_record
from .person_rendering import draw_person_hair_back, draw_person_hair_front, sample_person_gender
from .render_geometry import scale_bbox as _scale_bbox, scale_points as _scale_points


CONSTRUCTION_SETTING_IDS: Tuple[str, ...] = variant_ids_with_tag("construction_setting")
CONSTRUCTION_ZONE_TYPES: Tuple[str, ...] = variant_ids_with_tag("construction_zone")
CONSTRUCTION_MATERIAL_TYPES: Tuple[str, ...] = variant_ids_with_tag("construction_material")
CONSTRUCTION_EQUIPMENT_TYPES: Tuple[str, ...] = variant_ids_with_tag("construction_equipment")
CONSTRUCTION_TOOL_TYPES: Tuple[str, ...] = variant_ids_with_tag("construction_tool")
CONSTRUCTION_COLOR_NAMES: Tuple[str, ...] = ("yellow", "orange", "red", "blue", "green", "purple")

CONSTRUCTION_ZONE_LABELS: Dict[str, str] = label_map_for_tag("construction_zone")
CONSTRUCTION_MATERIAL_LABELS: Dict[str, str] = plural_name_map_for_tag("construction_material")
CONSTRUCTION_EQUIPMENT_LABELS: Dict[str, str] = plural_name_map_for_tag("construction_equipment")
CONSTRUCTION_COLOR_RGB: Dict[str, RGB] = {
    "yellow": (238, 194, 64),
    "orange": (232, 126, 54),
    "red": (198, 73, 62),
    "blue": (63, 118, 183),
    "green": (75, 146, 92),
    "purple": (129, 92, 165),
}


@dataclass(frozen=True)
class ConstructionWorkerSpec:
    """Requested semantic attributes for one rendered worker."""

    hard_hat_color: str
    vest_color: str
    tool_type: str | None = None
    role: str = "distractor"
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConstructionMaterialSpec:
    """Requested semantic material type for one rendered stack/bundle."""

    material_type: str
    role: str = "distractor"
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConstructionEquipmentSpec:
    """Requested semantic equipment type and optional zone placement."""

    equipment_type: str
    zone_id: str | None = None
    role: str = "distractor"
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConstructionZone:
    """One labeled construction-site region."""

    zone_id: str
    label: str
    bbox_xyxy: BBox
    fill_rgb: RGB
    outline_rgb: RGB


@dataclass(frozen=True)
class ConstructionWorker:
    """One rendered construction worker."""

    worker_id: str
    hard_hat_color: str
    vest_color: str
    tool_type: str | None
    bbox_xyxy: BBox
    style_id: str
    gender_id: str
    role: str
    attributes: Mapping[str, Any]


@dataclass(frozen=True)
class ConstructionMaterial:
    """One rendered material stack or bundle."""

    material_id: str
    material_type: str
    material_label: str
    bbox_xyxy: BBox
    style_id: str
    role: str
    attributes: Mapping[str, Any]


@dataclass(frozen=True)
class ConstructionEquipment:
    """One rendered construction vehicle or equipment item."""

    equipment_id: str
    equipment_type: str
    equipment_label: str
    zone_id: str
    bbox_xyxy: BBox
    style_id: str
    role: str
    attributes: Mapping[str, Any]


@dataclass(frozen=True)
class ConstructionDecor:
    """Non-query construction-site visual element."""

    decor_id: str
    decor_type: str
    bbox_xyxy: BBox
    attributes: Mapping[str, Any]


@dataclass(frozen=True)
class RenderedConstructionSiteScene:
    """Rendered construction site plus verifier-ready metadata."""

    image: Image.Image
    setting_id: str
    zones: Tuple[ConstructionZone, ...]
    workers: Tuple[ConstructionWorker, ...]
    materials: Tuple[ConstructionMaterial, ...]
    equipment: Tuple[ConstructionEquipment, ...]
    decor: Tuple[ConstructionDecor, ...]
    canvas_width: int
    canvas_height: int
    render_scale: int
    style_id: str
    layout: Mapping[str, Any]


def construction_color_display_name(color_name: str) -> str:
    """Return a prompt-facing color name."""

    return str(color_name).replace("_", " ")


def construction_material_display_name(material_type: str) -> str:
    """Return prompt-facing plural material text."""

    return CONSTRUCTION_MATERIAL_LABELS.get(str(material_type), str(material_type).replace("_", " ") + "s")


def construction_equipment_display_name(equipment_type: str) -> str:
    """Return prompt-facing plural equipment text."""

    return CONSTRUCTION_EQUIPMENT_LABELS.get(str(equipment_type), str(equipment_type).replace("_", " ") + "s")


def construction_zone_display_name(zone_id: str) -> str:
    """Return prompt-facing construction-zone text."""

    return CONSTRUCTION_ZONE_LABELS.get(str(zone_id), str(zone_id).replace("_", " "))


def _jitter_rgb(rng, color: RGB, amount: int = 10) -> RGB:
    return tuple(max(0, min(255, int(channel) + int(rng.randint(-int(amount), int(amount))))) for channel in color)  # type: ignore[return-value]


def _choose_weighted(rng, weights: Mapping[str, float], support: Sequence[str]) -> str:
    choices = [(str(value), max(0.0, float(weights.get(str(value), 0.0)))) for value in support]
    total = sum(weight for _value, weight in choices)
    if total <= 0.0:
        return str(rng.choice(tuple(support)))
    threshold = float(rng.random()) * total
    running = 0.0
    for value, weight in choices:
        running += weight
        if running >= threshold:
            return str(value)
    return str(choices[-1][0])


def _style_outline(style_id: str) -> Tuple[RGB, int, bool]:
    if str(style_id) == "paper_cutout":
        return (244, 241, 226), 4, True
    if str(style_id) == "outlined_cartoon":
        return (33, 37, 46), 3, False
    if str(style_id) == "soft_shadow":
        return (74, 78, 87), 2, True
    return (74, 78, 87), 1, False


def _rect(
    draw: ImageDraw.ImageDraw,
    bbox: BBox,
    *,
    fill: RGB,
    outline: RGB | None,
    width: int,
    scale: int,
    radius: float = 0.0,
) -> None:
    box = _scale_bbox(bbox, scale)
    line_width = max(1, int(width) * int(scale))
    if float(radius) > 0:
        draw.rounded_rectangle(
            box,
            radius=max(1, int(round(float(radius) * int(scale)))),
            fill=tuple(fill),
            outline=tuple(outline) if outline else None,
            width=line_width,
        )
    else:
        draw.rectangle(box, fill=tuple(fill), outline=tuple(outline) if outline else None, width=line_width)


def _ellipse(
    draw: ImageDraw.ImageDraw,
    bbox: BBox,
    *,
    fill: RGB,
    outline: RGB | None,
    width: int,
    scale: int,
) -> None:
    draw.ellipse(_scale_bbox(bbox, scale), fill=tuple(fill), outline=tuple(outline) if outline else None, width=max(1, int(width) * int(scale)))


def _poly(
    draw: ImageDraw.ImageDraw,
    points: Sequence[Tuple[float, float]],
    *,
    fill: RGB,
    outline: RGB | None,
    width: int,
    scale: int,
) -> None:
    draw.polygon(_scale_points(points, scale), fill=tuple(fill))
    if outline:
        draw.line(_scale_points([*points, points[0]], scale), fill=tuple(outline), width=max(1, int(width) * int(scale)), joint="curve")


def _line(draw: ImageDraw.ImageDraw, points: Sequence[Tuple[float, float]], *, fill: RGB, width: int, scale: int) -> None:
    draw.line(_scale_points(points, scale), fill=tuple(fill), width=max(1, int(width) * int(scale)), joint="curve")


def _font(size: int, scale: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", max(8, int(size) * int(scale)))
    except Exception:
        return ImageFont.load_default()


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    center: Tuple[float, float],
    *,
    font: ImageFont.ImageFont,
    fill: RGB,
    scale: int,
    stroke_fill: RGB | None = None,
) -> None:
    cx, cy = center
    try:
        text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(scale) if stroke_fill else 0))
        text_w = float(text_bbox[2] - text_bbox[0])
        text_h = float(text_bbox[3] - text_bbox[1])
    except Exception:  # pragma: no cover
        text_w, text_h = draw.textsize(str(text), font=font)
    draw.text(
        (int(round(float(cx) * int(scale) - text_w / 2.0)), int(round(float(cy) * int(scale) - text_h / 2.0))),
        str(text),
        font=font,
        fill=tuple(fill),
        stroke_width=max(0, int(scale) if stroke_fill else 0),
        stroke_fill=tuple(stroke_fill) if stroke_fill else None,
    )


def _expanded_intersects(a: BBox, b: BBox, gap: float) -> bool:
    return not (
        float(a[2]) + float(gap) <= float(b[0])
        or float(b[2]) + float(gap) <= float(a[0])
        or float(a[3]) + float(gap) <= float(b[1])
        or float(b[3]) + float(gap) <= float(a[1])
    )


def _center_in_bbox(center: Tuple[float, float], bbox: BBox) -> bool:
    x, y = center
    return float(bbox[0]) <= float(x) <= float(bbox[2]) and float(bbox[1]) <= float(y) <= float(bbox[3])


def _box_center(bbox: BBox) -> Tuple[float, float]:
    return ((float(bbox[0]) + float(bbox[2])) / 2.0, (float(bbox[1]) + float(bbox[3])) / 2.0)


def _safe_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _safe_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_json(item) for item in value]
    if isinstance(value, float):
        return round(float(value), 3)
    return value


def _sample_layout(rng, *, width: int, height: int, setting_id: str) -> Dict[str, Any]:
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


def _draw_background(
    draw: ImageDraw.ImageDraw,
    *,
    rng,
    setting_id: str,
    layout: Mapping[str, Any],
    zones: Sequence[ConstructionZone],
    width: int,
    height: int,
    scale: int,
    style_id: str,
) -> List[ConstructionDecor]:
    decor: List[ConstructionDecor] = []
    sky = _jitter_rgb(rng, (196, 219, 228), 8)
    ground = _jitter_rgb(rng, (180, 168, 138), 10)
    far = _jitter_rgb(rng, (150, 162, 153), 10)
    s = int(scale)
    horizon = float(rng.uniform(178.0, 232.0))
    draw.rectangle((0, 0, int(width) * s, int(height) * s), fill=tuple(sky))
    draw.rectangle(_scale_bbox((0.0, horizon, float(width), float(height)), s), fill=tuple(ground))
    draw.rectangle(_scale_bbox((0.0, horizon, float(width), horizon + 38.0), s), fill=tuple(far))

    # Distant city/building silhouettes and a fence line.
    x = -20.0
    building_idx = 0
    while x < float(width):
        bw = float(rng.uniform(72.0, 132.0))
        bh = float(rng.uniform(82.0, 168.0))
        bbox = (x, horizon - bh, x + bw, horizon + 8.0)
        _rect(draw, bbox, fill=_jitter_rgb(rng, (126, 137, 145), 10), outline=None, width=1, scale=s)
        decor.append(ConstructionDecor(f"decor_building_{building_idx}", "background_building", bbox, {"setting_id": str(setting_id)}))
        x += bw + float(rng.uniform(14.0, 34.0))
        building_idx += 1
    _line(draw, [(0.0, horizon + 52.0), (float(width), horizon + 52.0)], fill=(118, 105, 86), width=4, scale=s)
    for post_x in range(20, int(width), 78):
        _rect(draw, (float(post_x), horizon + 26.0, float(post_x + 8), horizon + 84.0), fill=(126, 105, 78), outline=None, width=1, scale=s)

    # Site-wide visual anchors.
    outline, outline_w, _shadow = _style_outline(str(style_id))
    if str(setting_id) in {"scaffold_site", "urban_build"} or str(layout.get("layout_id")) == "scaffold_front":
        scaffold_box = (74.0, 236.0, 548.0, 528.0)
        for level in range(4):
            y = scaffold_box[1] + 58.0 * level
            _line(draw, [(scaffold_box[0], y), (scaffold_box[2], y)], fill=(94, 101, 109), width=3, scale=s)
        for col in range(6):
            x0 = scaffold_box[0] + 92.0 * col
            _line(draw, [(x0, scaffold_box[1]), (x0, scaffold_box[3])], fill=(94, 101, 109), width=3, scale=s)
        decor.append(ConstructionDecor("decor_scaffold", "scaffold", scaffold_box, {"setting_id": str(setting_id)}))
    if str(setting_id) in {"urban_build", "foundation_yard", "scaffold_site"}:
        base_x = float(rng.uniform(780.0, 960.0))
        crane_box = (base_x, 72.0, base_x + 292.0, 292.0)
        _line(draw, [(base_x + 24.0, 286.0), (base_x + 24.0, 92.0)], fill=(192, 139, 45), width=10, scale=s)
        _line(draw, [(base_x - 44.0, 108.0), (base_x + 248.0, 108.0)], fill=(206, 157, 51), width=8, scale=s)
        _line(draw, [(base_x + 24.0, 92.0), (base_x + 248.0, 108.0)], fill=(166, 119, 40), width=4, scale=s)
        _line(draw, [(base_x + 202.0, 108.0), (base_x + 202.0, 178.0)], fill=(66, 68, 74), width=3, scale=s)
        _rect(draw, (base_x + 186.0, 174.0, base_x + 218.0, 206.0), fill=(112, 99, 82), outline=outline, width=outline_w, scale=s, radius=2)
        decor.append(ConstructionDecor("decor_crane", "tower_crane", crane_box, {"setting_id": str(setting_id)}))
    if str(setting_id) == "roadwork" or str(layout.get("layout_id")) == "diagonal_road":
        road_poly = [(0.0, 752.0), (float(width), 628.0), (float(width), 734.0), (0.0, 860.0)]
        _poly(draw, road_poly, fill=(92, 96, 98), outline=None, width=1, scale=s)
        _line(draw, [(0.0, 802.0), (float(width), 680.0)], fill=(240, 203, 82), width=5, scale=s)

    # Semantic zones are visible and labeled.
    label_font = _font(17, s)
    for zone in zones:
        _rect(draw, zone.bbox_xyxy, fill=zone.fill_rgb, outline=zone.outline_rgb, width=2, scale=s, radius=18)
        cx = (float(zone.bbox_xyxy[0]) + float(zone.bbox_xyxy[2])) / 2.0
        _draw_centered_text(draw, zone.label, (cx, float(zone.bbox_xyxy[1]) + 23.0), font=label_font, fill=(49, 54, 61), stroke_fill=(255, 255, 245), scale=s)
    return decor


def _build_zones(layout: Mapping[str, Any]) -> Tuple[ConstructionZone, ...]:
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


def _zone_lookup(zones: Sequence[ConstructionZone]) -> Dict[str, ConstructionZone]:
    return {str(zone.zone_id): zone for zone in zones}


def _place_box(
    rng,
    zone_bbox: BBox,
    *,
    width: float,
    height: float,
    occupied: List[BBox],
    gap: float,
    max_attempts: int = 180,
) -> BBox:
    x0_min = float(zone_bbox[0]) + 18.0
    x0_max = float(zone_bbox[2]) - float(width) - 18.0
    y0_min = float(zone_bbox[1]) + 50.0
    y0_max = float(zone_bbox[3]) - float(height) - 14.0
    if x0_max < x0_min:
        x0_max = x0_min
    if y0_max < y0_min:
        y0_max = y0_min
    best_box = (x0_min, y0_min, x0_min + float(width), y0_min + float(height))
    for _ in range(int(max_attempts)):
        x0 = float(rng.uniform(x0_min, x0_max))
        y0 = float(rng.uniform(y0_min, y0_max))
        box = (x0, y0, x0 + float(width), y0 + float(height))
        if not any(_expanded_intersects(box, other, gap) for other in occupied):
            occupied.append(box)
            return box
        best_box = box
    occupied.append(best_box)
    return best_box


def _draw_worker(draw: ImageDraw.ImageDraw, worker: ConstructionWorker, *, scale: int) -> None:
    x0, y0, x1, y1 = worker.bbox_xyxy
    w = x1 - x0
    h = y1 - y0
    outline, outline_w, shadow = _style_outline(worker.style_id)
    if shadow:
        _ellipse(draw, (x0 + w * 0.12, y1 - h * 0.08, x1 - w * 0.08, y1 + h * 0.02), fill=(158, 146, 124), outline=None, width=1, scale=scale)
    skin = (178, 126, 83)
    shirt = (84, 118, 154)
    pants = (68, 83, 104)
    hat = CONSTRUCTION_COLOR_RGB.get(str(worker.hard_hat_color), (238, 194, 64))
    vest = CONSTRUCTION_COLOR_RGB.get(str(worker.vest_color), (232, 126, 54))
    head = (x0 + w * 0.33, y0 + h * 0.13, x0 + w * 0.67, y0 + h * 0.43)
    draw_person_hair_back(draw, head_bbox=head, gender_id=str(worker.gender_id), scale=scale, outline=outline)
    _ellipse(draw, head, fill=skin, outline=outline, width=outline_w, scale=scale)
    draw_person_hair_front(draw, head_bbox=head, gender_id=str(worker.gender_id), scale=scale, outline=outline)
    _rect(draw, (x0 + w * 0.25, y0 + h * 0.09, x0 + w * 0.75, y0 + h * 0.25), fill=hat, outline=outline, width=outline_w, scale=scale, radius=8)
    _rect(draw, (x0 + w * 0.20, y0 + h * 0.22, x0 + w * 0.80, y0 + h * 0.28), fill=hat, outline=outline, width=outline_w, scale=scale, radius=4)
    torso = (x0 + w * 0.24, y0 + h * 0.42, x0 + w * 0.76, y0 + h * 0.72)
    _rect(draw, torso, fill=shirt, outline=outline, width=outline_w, scale=scale, radius=7)
    _poly(draw, [(x0 + w * 0.26, y0 + h * 0.43), (x0 + w * 0.43, y0 + h * 0.43), (x0 + w * 0.56, y0 + h * 0.72), (x0 + w * 0.38, y0 + h * 0.72)], fill=vest, outline=None, width=1, scale=scale)
    _poly(draw, [(x0 + w * 0.57, y0 + h * 0.43), (x0 + w * 0.74, y0 + h * 0.43), (x0 + w * 0.62, y0 + h * 0.72), (x0 + w * 0.46, y0 + h * 0.72)], fill=vest, outline=None, width=1, scale=scale)
    _line(draw, [(x0 + w * 0.23, y0 + h * 0.48), (x0 + w * 0.10, y0 + h * 0.66)], fill=skin, width=5, scale=scale)
    _line(draw, [(x0 + w * 0.77, y0 + h * 0.48), (x0 + w * 0.90, y0 + h * 0.66)], fill=skin, width=5, scale=scale)
    _line(draw, [(x0 + w * 0.41, y0 + h * 0.72), (x0 + w * 0.34, y1 - h * 0.06)], fill=pants, width=7, scale=scale)
    _line(draw, [(x0 + w * 0.59, y0 + h * 0.72), (x0 + w * 0.68, y1 - h * 0.06)], fill=pants, width=7, scale=scale)
    if worker.tool_type:
        if str(worker.tool_type) == "shovel":
            _line(draw, [(x0 + w * 0.84, y0 + h * 0.55), (x0 + w * 1.03, y1 - h * 0.04)], fill=(82, 68, 49), width=3, scale=scale)
            _ellipse(draw, (x0 + w * 0.96, y1 - h * 0.09, x0 + w * 1.10, y1 + h * 0.02), fill=(101, 105, 108), outline=outline, width=1, scale=scale)
        elif str(worker.tool_type) == "hammer":
            _line(draw, [(x0 + w * 0.82, y0 + h * 0.58), (x0 + w * 0.98, y0 + h * 0.76)], fill=(86, 65, 44), width=4, scale=scale)
            _rect(draw, (x0 + w * 0.91, y0 + h * 0.51, x0 + w * 1.08, y0 + h * 0.59), fill=(107, 112, 118), outline=outline, width=1, scale=scale, radius=2)
        else:
            _line(draw, [(x0 + w * 0.80, y0 + h * 0.58), (x0 + w * 1.04, y0 + h * 0.70)], fill=(97, 101, 106), width=4, scale=scale)
            _ellipse(draw, (x0 + w * 0.98, y0 + h * 0.66, x0 + w * 1.10, y0 + h * 0.78), fill=(97, 101, 106), outline=outline, width=1, scale=scale)


def _draw_material(draw: ImageDraw.ImageDraw, material: ConstructionMaterial, *, scale: int) -> None:
    x0, y0, x1, y1 = material.bbox_xyxy
    w = x1 - x0
    h = y1 - y0
    outline, outline_w, shadow = _style_outline(material.style_id)
    if shadow:
        _ellipse(draw, (x0 + 4.0, y1 - 10.0, x1 + 8.0, y1 + 8.0), fill=(150, 139, 119), outline=None, width=1, scale=scale)
    kind = str(material.material_type)
    if kind == "brick_stack":
        rows = 4
        cols = 5
        brick = (179, 83, 58)
        for row in range(rows):
            for col in range(cols):
                bx0 = x0 + w * (0.05 + col * 0.18 + (0.08 if row % 2 else 0.0))
                by0 = y0 + h * (0.12 + row * 0.19)
                _rect(draw, (bx0, by0, bx0 + w * 0.16, by0 + h * 0.16), fill=brick, outline=outline, width=1, scale=scale, radius=2)
    elif kind == "pipe_bundle":
        pipe = (104, 125, 133)
        for row in range(3):
            for col in range(4):
                cx = x0 + w * (0.18 + col * 0.19 + (0.08 if row % 2 else 0.0))
                cy = y0 + h * (0.25 + row * 0.20)
                r = min(w, h) * 0.09
                _ellipse(draw, (cx - r, cy - r, cx + r, cy + r), fill=(202, 209, 211), outline=pipe, width=2, scale=scale)
    elif kind == "lumber_stack":
        for row in range(5):
            by0 = y0 + h * (0.14 + row * 0.15)
            _rect(draw, (x0 + w * 0.06, by0, x1 - w * 0.06, by0 + h * 0.10), fill=(177, 123, 68), outline=outline, width=1, scale=scale, radius=3)
            _line(draw, [(x0 + w * 0.12, by0 + h * 0.05), (x1 - w * 0.12, by0 + h * 0.05)], fill=(132, 88, 45), width=1, scale=scale)
    else:
        for row in range(3):
            for col in range(3):
                bx0 = x0 + w * (0.10 + col * 0.28 + (0.06 if row % 2 else 0.0))
                by0 = y0 + h * (0.14 + row * 0.23)
                _rect(draw, (bx0, by0, bx0 + w * 0.23, by0 + h * 0.17), fill=(217, 207, 181), outline=outline, width=outline_w, scale=scale, radius=8)


def _draw_equipment(draw: ImageDraw.ImageDraw, equipment: ConstructionEquipment, *, scale: int) -> None:
    x0, y0, x1, y1 = equipment.bbox_xyxy
    w = x1 - x0
    h = y1 - y0
    outline, outline_w, shadow = _style_outline(equipment.style_id)
    yellow = (229, 169, 48)
    orange = (218, 119, 48)
    bluegray = (87, 107, 124)
    tire = (45, 49, 55)
    if shadow:
        _ellipse(draw, (x0 + w * 0.04, y1 - h * 0.10, x1 - w * 0.02, y1 + h * 0.03), fill=(137, 128, 111), outline=None, width=1, scale=scale)
    kind = str(equipment.equipment_type)
    if kind == "excavator":
        _rect(draw, (x0 + w * 0.06, y0 + h * 0.70, x0 + w * 0.72, y0 + h * 0.90), fill=(57, 61, 65), outline=outline, width=outline_w, scale=scale, radius=12)
        _rect(draw, (x0 + w * 0.18, y0 + h * 0.42, x0 + w * 0.56, y0 + h * 0.72), fill=yellow, outline=outline, width=outline_w, scale=scale, radius=8)
        _rect(draw, (x0 + w * 0.36, y0 + h * 0.28, x0 + w * 0.62, y0 + h * 0.58), fill=(91, 134, 157), outline=outline, width=outline_w, scale=scale, radius=6)
        _line(draw, [(x0 + w * 0.56, y0 + h * 0.45), (x0 + w * 0.82, y0 + h * 0.25), (x0 + w * 0.94, y0 + h * 0.60)], fill=yellow, width=10, scale=scale)
        _poly(draw, [(x0 + w * 0.88, y0 + h * 0.60), (x0 + w * 1.02, y0 + h * 0.62), (x0 + w * 0.92, y0 + h * 0.77)], fill=(83, 77, 65), outline=outline, width=outline_w, scale=scale)
    elif kind == "dump_truck":
        _rect(draw, (x0 + w * 0.08, y0 + h * 0.44, x0 + w * 0.58, y0 + h * 0.72), fill=orange, outline=outline, width=outline_w, scale=scale, radius=6)
        _poly(draw, [(x0 + w * 0.58, y0 + h * 0.38), (x0 + w * 0.84, y0 + h * 0.42), (x0 + w * 0.88, y0 + h * 0.72), (x0 + w * 0.58, y0 + h * 0.72)], fill=yellow, outline=outline, width=outline_w, scale=scale)
        _rect(draw, (x0 + w * 0.66, y0 + h * 0.46, x0 + w * 0.80, y0 + h * 0.60), fill=(112, 154, 173), outline=outline, width=1, scale=scale, radius=3)
        for cx in (x0 + w * 0.24, x0 + w * 0.70):
            _ellipse(draw, (cx - w * 0.07, y0 + h * 0.66, cx + w * 0.07, y0 + h * 0.84), fill=tire, outline=outline, width=outline_w, scale=scale)
    elif kind == "cement_mixer":
        _rect(draw, (x0 + w * 0.10, y0 + h * 0.56, x0 + w * 0.88, y0 + h * 0.74), fill=bluegray, outline=outline, width=outline_w, scale=scale, radius=8)
        _ellipse(draw, (x0 + w * 0.26, y0 + h * 0.28, x0 + w * 0.66, y0 + h * 0.68), fill=(217, 213, 196), outline=outline, width=outline_w, scale=scale)
        _line(draw, [(x0 + w * 0.34, y0 + h * 0.36), (x0 + w * 0.60, y0 + h * 0.60)], fill=(152, 147, 132), width=4, scale=scale)
        _rect(draw, (x0 + w * 0.66, y0 + h * 0.38, x0 + w * 0.88, y0 + h * 0.62), fill=yellow, outline=outline, width=outline_w, scale=scale, radius=5)
        for cx in (x0 + w * 0.28, x0 + w * 0.74):
            _ellipse(draw, (cx - w * 0.07, y0 + h * 0.66, cx + w * 0.07, y0 + h * 0.84), fill=tire, outline=outline, width=outline_w, scale=scale)
    else:
        _rect(draw, (x0 + w * 0.18, y0 + h * 0.46, x0 + w * 0.62, y0 + h * 0.72), fill=yellow, outline=outline, width=outline_w, scale=scale, radius=6)
        _rect(draw, (x0 + w * 0.32, y0 + h * 0.22, x0 + w * 0.58, y0 + h * 0.50), fill=(111, 152, 170), outline=outline, width=outline_w, scale=scale, radius=4)
        _line(draw, [(x0 + w * 0.72, y0 + h * 0.18), (x0 + w * 0.72, y0 + h * 0.80)], fill=(59, 63, 68), width=5, scale=scale)
        _line(draw, [(x0 + w * 0.72, y0 + h * 0.78), (x0 + w * 0.98, y0 + h * 0.78)], fill=(59, 63, 68), width=4, scale=scale)
        for cx in (x0 + w * 0.28, x0 + w * 0.56):
            _ellipse(draw, (cx - w * 0.06, y0 + h * 0.67, cx + w * 0.06, y0 + h * 0.83), fill=tire, outline=outline, width=outline_w, scale=scale)


def render_construction_site_scene(
    *,
    rng,
    worker_specs: Sequence[ConstructionWorkerSpec],
    material_specs: Sequence[ConstructionMaterialSpec],
    equipment_specs: Sequence[ConstructionEquipmentSpec],
    canvas_width: int,
    canvas_height: int,
    render_scale: int,
    setting_weights: Mapping[str, float],
    style_weights: Mapping[str, float],
) -> RenderedConstructionSiteScene:
    """Render a construction-site illustration from semantic specs."""

    width = int(canvas_width)
    height = int(canvas_height)
    scale = int(render_scale)
    setting_id = _choose_weighted(rng, setting_weights, CONSTRUCTION_SETTING_IDS)
    style_id = _choose_weighted(rng, style_weights, STYLE_IDS)
    layout = _sample_layout(rng, width=width, height=height, setting_id=setting_id)
    zones = _build_zones(layout)
    zone_by_id = _zone_lookup(zones)
    image = Image.new("RGB", (width * scale, height * scale), (244, 239, 224))
    draw = ImageDraw.Draw(image)
    decor = _draw_background(
        draw,
        rng=rng,
        setting_id=setting_id,
        layout=layout,
        zones=zones,
        width=width,
        height=height,
        scale=scale,
        style_id=style_id,
    )

    occupied: List[BBox] = []
    materials: List[ConstructionMaterial] = []
    for index, spec in enumerate(material_specs):
        zone = zone_by_id[str(rng.choice(CONSTRUCTION_ZONE_TYPES))]
        box_w = float(rng.uniform(86.0, 138.0))
        box_h = float(rng.uniform(58.0, 94.0))
        bbox = _place_box(rng, zone.bbox_xyxy, width=box_w, height=box_h, occupied=occupied, gap=8.0)
        material = ConstructionMaterial(
            material_id=f"material_{index}",
            material_type=str(spec.material_type),
            material_label=construction_material_display_name(str(spec.material_type)),
            bbox_xyxy=bbox,
            style_id=str(style_id),
            role=str(spec.role),
            attributes=dict(spec.attributes),
        )
        materials.append(material)
    for material in sorted(materials, key=lambda item: (float(item.bbox_xyxy[1]), float(item.bbox_xyxy[0]))):
        _draw_material(draw, material, scale=scale)

    equipment_items: List[ConstructionEquipment] = []
    for index, spec in enumerate(equipment_specs):
        zone_id = str(spec.zone_id or rng.choice(CONSTRUCTION_ZONE_TYPES))
        zone = zone_by_id[zone_id]
        box_w = float(rng.uniform(132.0, 188.0))
        box_h = float(rng.uniform(94.0, 134.0))
        bbox = _place_box(rng, zone.bbox_xyxy, width=box_w, height=box_h, occupied=occupied, gap=12.0)
        equipment = ConstructionEquipment(
            equipment_id=f"equipment_{index}",
            equipment_type=str(spec.equipment_type),
            equipment_label=construction_equipment_display_name(str(spec.equipment_type)),
            zone_id=zone_id,
            bbox_xyxy=bbox,
            style_id=str(style_id),
            role=str(spec.role),
            attributes=dict(spec.attributes),
        )
        equipment_items.append(equipment)
    for equipment in sorted(equipment_items, key=lambda item: (float(item.bbox_xyxy[1]), float(item.bbox_xyxy[0]))):
        _draw_equipment(draw, equipment, scale=scale)

    workers: List[ConstructionWorker] = []
    for index, spec in enumerate(worker_specs):
        zone = zone_by_id[str(rng.choice(CONSTRUCTION_ZONE_TYPES))]
        box_w = float(rng.uniform(44.0, 58.0))
        box_h = float(rng.uniform(94.0, 116.0))
        bbox = _place_box(rng, zone.bbox_xyxy, width=box_w, height=box_h, occupied=occupied, gap=4.0)
        worker = ConstructionWorker(
            worker_id=f"worker_{index}",
            hard_hat_color=str(spec.hard_hat_color),
            vest_color=str(spec.vest_color),
            tool_type=str(spec.tool_type) if spec.tool_type else None,
            bbox_xyxy=bbox,
            style_id=str(style_id),
            gender_id=sample_person_gender(rng),
            role=str(spec.role),
            attributes=dict(spec.attributes),
        )
        workers.append(worker)
    for worker in sorted(workers, key=lambda item: (float(item.bbox_xyxy[1]), float(item.bbox_xyxy[0]))):
        _draw_worker(draw, worker, scale=scale)

    if scale != 1:
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    return RenderedConstructionSiteScene(
        image=image,
        setting_id=str(setting_id),
        zones=tuple(zones),
        workers=tuple(workers),
        materials=tuple(materials),
        equipment=tuple(equipment_items),
        decor=tuple(decor),
        canvas_width=width,
        canvas_height=height,
        render_scale=scale,
        style_id=str(style_id),
        layout=_safe_json(layout),
    )


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


def construction_scene_entities(scene: RenderedConstructionSiteScene) -> List[Dict[str, Any]]:
    """Return trace-ready construction scene entities."""

    entities: List[Dict[str, Any]] = []
    for zone in scene.zones:
        object_record = make_object_record(
            object_id=str(zone.zone_id),
            object_type="zone",
            bbox_xyxy=zone.bbox_xyxy,
            semantic_attributes={"zone_id": str(zone.zone_id), "label": str(zone.label)},
            visual_attributes={
                "fill_rgb": [int(v) for v in zone.fill_rgb],
                "outline_rgb": [int(v) for v in zone.outline_rgb],
            },
            source_entity_type="construction_zone",
        ).as_dict()
        entities.append(
            {
                "id": str(zone.zone_id),
                "type": "construction_zone",
                "label": str(zone.label),
                "bbox_xyxy": [round(float(v), 3) for v in zone.bbox_xyxy],
                "object_record": object_record,
            }
        )
    for worker in scene.workers:
        object_record = make_object_record(
            object_id=str(worker.worker_id),
            object_type="worker",
            bbox_xyxy=worker.bbox_xyxy,
            semantic_attributes={
                "hard_hat_color": str(worker.hard_hat_color),
                "vest_color": str(worker.vest_color),
                "tool_type": str(worker.tool_type) if worker.tool_type else None,
                **dict(worker.attributes),
            },
            visual_attributes={"style_id": str(worker.style_id), "gender_id": str(worker.gender_id)},
            role=str(worker.role),
            source_entity_type="construction_worker",
        ).as_dict()
        entities.append(
            {
                "id": str(worker.worker_id),
                "type": "construction_worker",
                "hard_hat_color": str(worker.hard_hat_color),
                "vest_color": str(worker.vest_color),
                "tool_type": str(worker.tool_type) if worker.tool_type else None,
                "bbox_xyxy": [round(float(v), 3) for v in worker.bbox_xyxy],
                "role": str(worker.role),
                "gender_id": str(worker.gender_id),
                "attributes": _safe_json(worker.attributes),
                "object_record": object_record,
            }
        )
    for material in scene.materials:
        object_record = make_object_record(
            object_id=str(material.material_id),
            object_type="construction_material",
            bbox_xyxy=material.bbox_xyxy,
            semantic_attributes={
                "material_type": str(material.material_type),
                "material_label": str(material.material_label),
                **dict(material.attributes),
            },
            visual_attributes={"style_id": str(material.style_id)},
            role=str(material.role),
            source_entity_type="construction_material",
        ).as_dict()
        entities.append(
            {
                "id": str(material.material_id),
                "type": "construction_material",
                "material_type": str(material.material_type),
                "label": str(material.material_label),
                "bbox_xyxy": [round(float(v), 3) for v in material.bbox_xyxy],
                "role": str(material.role),
                "attributes": _safe_json(material.attributes),
                "object_record": object_record,
            }
        )
    for equipment in scene.equipment:
        object_record = make_object_record(
            object_id=str(equipment.equipment_id),
            object_type="construction_equipment",
            bbox_xyxy=equipment.bbox_xyxy,
            semantic_attributes={
                "equipment_type": str(equipment.equipment_type),
                "equipment_label": str(equipment.equipment_label),
                "zone_id": str(equipment.zone_id),
                **dict(equipment.attributes),
            },
            visual_attributes={"style_id": str(equipment.style_id)},
            role=str(equipment.role),
            source_entity_type="construction_equipment",
        ).as_dict()
        entities.append(
            {
                "id": str(equipment.equipment_id),
                "type": "construction_equipment",
                "equipment_type": str(equipment.equipment_type),
                "label": str(equipment.equipment_label),
                "zone_id": str(equipment.zone_id),
                "bbox_xyxy": [round(float(v), 3) for v in equipment.bbox_xyxy],
                "role": str(equipment.role),
                "attributes": _safe_json(equipment.attributes),
                "object_record": object_record,
            }
        )
    for item in scene.decor:
        object_record = make_object_record(
            object_id=str(item.decor_id),
            object_type="decor",
            bbox_xyxy=item.bbox_xyxy,
            semantic_attributes={"decor_type": str(item.decor_type), **dict(item.attributes)},
            source_entity_type="construction_decor",
        ).as_dict()
        entities.append(
            {
                "id": str(item.decor_id),
                "type": "construction_decor",
                "decor_type": str(item.decor_type),
                "bbox_xyxy": [round(float(v), 3) for v in item.bbox_xyxy],
                "attributes": _safe_json(item.attributes),
                "object_record": object_record,
            }
        )
    return entities


def serialize_construction_scene(scene: RenderedConstructionSiteScene) -> Tuple[List[Dict[str, Any]], Dict[str, List[float]]]:
    """Serialize construction scene for task review metadata."""

    payload = {
        "setting_id": str(scene.setting_id),
        "style_id": str(scene.style_id),
        "layout": _safe_json(scene.layout),
        "zones": [
            {
                "zone_id": str(zone.zone_id),
                "label": str(zone.label),
                "bbox_xyxy": [round(float(v), 3) for v in zone.bbox_xyxy],
            }
            for zone in scene.zones
        ],
        "workers": [
            {
                "worker_id": str(worker.worker_id),
                "hard_hat_color": str(worker.hard_hat_color),
                "vest_color": str(worker.vest_color),
                "tool_type": str(worker.tool_type) if worker.tool_type else None,
                "bbox_xyxy": [round(float(v), 3) for v in worker.bbox_xyxy],
                "gender_id": str(worker.gender_id),
                "role": str(worker.role),
                "attributes": _safe_json(worker.attributes),
            }
            for worker in scene.workers
        ],
        "materials": [
            {
                "material_id": str(material.material_id),
                "material_type": str(material.material_type),
                "material_label": str(material.material_label),
                "bbox_xyxy": [round(float(v), 3) for v in material.bbox_xyxy],
                "role": str(material.role),
                "attributes": _safe_json(material.attributes),
            }
            for material in scene.materials
        ],
        "equipment": [
            {
                "equipment_id": str(equipment.equipment_id),
                "equipment_type": str(equipment.equipment_type),
                "equipment_label": str(equipment.equipment_label),
                "zone_id": str(equipment.zone_id),
                "bbox_xyxy": [round(float(v), 3) for v in equipment.bbox_xyxy],
                "role": str(equipment.role),
                "attributes": _safe_json(equipment.attributes),
            }
            for equipment in scene.equipment
        ],
        "decor": [
            {
                "decor_id": str(item.decor_id),
                "decor_type": str(item.decor_type),
                "bbox_xyxy": [round(float(v), 3) for v in item.bbox_xyxy],
                "attributes": _safe_json(item.attributes),
            }
            for item in scene.decor
        ],
    }
    bbox_map: Dict[str, List[float]] = {}
    bbox_map.update(construction_worker_bbox_map(scene))
    bbox_map.update(construction_material_bbox_map(scene))
    bbox_map.update(construction_equipment_bbox_map(scene))
    bbox_map.update(construction_zone_bbox_map(scene))
    return [payload], bbox_map


__all__ = [
    "CONSTRUCTION_COLOR_NAMES",
    "CONSTRUCTION_EQUIPMENT_TYPES",
    "CONSTRUCTION_MATERIAL_TYPES",
    "CONSTRUCTION_SETTING_IDS",
    "CONSTRUCTION_TOOL_TYPES",
    "CONSTRUCTION_ZONE_TYPES",
    "ConstructionEquipmentSpec",
    "ConstructionMaterialSpec",
    "ConstructionWorkerSpec",
    "RenderedConstructionSiteScene",
    "construction_color_display_name",
    "construction_equipment_bbox_map",
    "construction_equipment_display_name",
    "construction_material_bbox_map",
    "construction_material_display_name",
    "construction_scene_entities",
    "construction_worker_bbox_map",
    "construction_zone_bbox_map",
    "construction_zone_display_name",
    "render_construction_site_scene",
    "serialize_construction_scene",
    "sort_construction_bboxes",
]
