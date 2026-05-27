"""Transit terminal illustration scene with labeled boarding areas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from .render_geometry import scale_bbox as _scale_bbox, scale_points as _scale_points
from ...shared.text_rendering import fit_font_to_box
from .object_catalog import label_map_for_tag, plural_name_map_for_tag, variant_ids_with_tag
from .object_library import BBox, RGB, STYLE_IDS
from .object_registry import make_object_record
from .person_rendering import draw_person_hair_back, draw_person_hair_front, draw_person_skirt, normalize_person_gender, sample_person_gender


TRANSIT_SETTING_IDS: Tuple[str, ...] = variant_ids_with_tag("transit_setting")
TRANSIT_BOARDING_AREA_IDS: Tuple[str, ...] = variant_ids_with_tag("transit_boarding_area")
TRANSIT_BOARDING_AREA_LABELS: Dict[str, str] = label_map_for_tag("transit_boarding_area")
TRANSIT_PERSON_POSES: Tuple[str, ...] = variant_ids_with_tag("transit_person_pose")
TRANSIT_LUGGAGE_TYPES: Tuple[str, ...] = variant_ids_with_tag("transit_luggage")
TRANSIT_LUGGAGE_LABELS: Dict[str, str] = plural_name_map_for_tag("transit_luggage")
TRANSIT_SERVICE_POINT_IDS: Tuple[str, ...] = variant_ids_with_tag("transit_service_point")
TRANSIT_SERVICE_POINT_LABELS: Dict[str, str] = label_map_for_tag("transit_service_point")


@dataclass(frozen=True)
class TransitPersonSpec:
    """Requested semantic placement for one rendered person."""

    area_id: str
    role: str = "distractor"
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TransitLuggageSpec:
    """Requested semantic placement for one loose luggage item."""

    area_id: str
    luggage_type: str
    role: str = "distractor"
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TransitPerson:
    """One rendered person with semantic boarding-area metadata."""

    person_id: str
    area_id: str
    pose_id: str
    bbox_xyxy: BBox
    primary_color_rgb: RGB
    accent_color_rgb: RGB
    skin_color_rgb: RGB
    gender_id: str
    role: str
    attributes: Mapping[str, Any]


@dataclass(frozen=True)
class TransitLuggageItem:
    """One rendered loose luggage item with semantic boarding-area metadata."""

    luggage_id: str
    area_id: str
    luggage_type: str
    bbox_xyxy: BBox
    primary_color_rgb: RGB
    role: str
    attributes: Mapping[str, Any]


@dataclass(frozen=True)
class TransitArea:
    """One labeled boarding area."""

    area_id: str
    display_name: str
    label: str
    bbox_xyxy: BBox
    sign_bbox_xyxy: BBox
    platform_bbox_xyxy: BBox
    attributes: Mapping[str, Any]


@dataclass(frozen=True)
class TransitServicePoint:
    """One labeled terminal service point with a visible queue lane."""

    service_point_id: str
    display_name: str
    bbox_xyxy: BBox
    sign_bbox_xyxy: BBox
    queue_bbox_xyxy: BBox
    attributes: Mapping[str, Any]


@dataclass(frozen=True)
class TransitDecor:
    """Non-query visual support object in the terminal scene."""

    decor_id: str
    decor_type: str
    bbox_xyxy: BBox
    attributes: Mapping[str, Any]


@dataclass(frozen=True)
class RenderedTransitTerminalScene:
    """Rendered transit terminal scene plus trace-ready metadata."""

    image: Image.Image
    setting_id: str
    areas: Tuple[TransitArea, ...]
    service_points: Tuple[TransitServicePoint, ...]
    persons: Tuple[TransitPerson, ...]
    luggage: Tuple[TransitLuggageItem, ...]
    decor: Tuple[TransitDecor, ...]
    canvas_width: int
    canvas_height: int
    render_scale: int
    style_id: str
    layout: Mapping[str, Any]


def transit_area_display_name(area_id: str) -> str:
    """Return prompt-facing boarding-area text."""

    return TRANSIT_BOARDING_AREA_LABELS.get(str(area_id), str(area_id).replace("_", " ").title())


def transit_luggage_display_name(luggage_type: str) -> str:
    """Return prompt-facing luggage type text."""

    return TRANSIT_LUGGAGE_LABELS.get(str(luggage_type), str(luggage_type).replace("_", " "))


def transit_service_point_display_name(service_point_id: str) -> str:
    """Return prompt-facing service-point text."""

    return TRANSIT_SERVICE_POINT_LABELS.get(str(service_point_id), str(service_point_id).replace("_", " "))




def _jitter_rgb(rng, color: RGB, amount: int = 14) -> RGB:
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
        return (246, 245, 236), 4, True
    if str(style_id) == "outlined_cartoon":
        return (37, 42, 52), 3, False
    if str(style_id) == "soft_shadow":
        return (66, 73, 84), 2, True
    return (66, 73, 84), 1, False


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
    scaled_width = max(1, int(width) * int(scale))
    if radius > 0:
        draw.rounded_rectangle(
            box,
            radius=max(1, int(round(float(radius) * int(scale)))),
            fill=tuple(fill),
            outline=tuple(outline) if outline else None,
            width=scaled_width,
        )
    else:
        draw.rectangle(box, fill=tuple(fill), outline=tuple(outline) if outline else None, width=scaled_width)


def _ellipse(draw: ImageDraw.ImageDraw, bbox: BBox, *, fill: RGB, outline: RGB | None, width: int, scale: int) -> None:
    draw.ellipse(_scale_bbox(bbox, scale), fill=tuple(fill), outline=tuple(outline) if outline else None, width=max(1, int(width) * int(scale)))


def _poly(draw: ImageDraw.ImageDraw, points: Sequence[Tuple[float, float]], *, fill: RGB, outline: RGB | None, width: int, scale: int) -> None:
    draw.polygon(_scale_points(points, scale), fill=tuple(fill))
    if outline:
        draw.line(_scale_points([*points, points[0]], scale), fill=tuple(outline), width=max(1, int(width) * int(scale)), joint="curve")


def _line(draw: ImageDraw.ImageDraw, points: Sequence[Tuple[float, float]], *, fill: RGB, width: int, scale: int) -> None:
    draw.line(_scale_points(points, scale), fill=tuple(fill), width=max(1, int(width) * int(scale)), joint="curve")


def _draw_fit_text(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    bbox: Sequence[float],
    scale: int,
    fill: RGB = (35, 40, 48),
    bold: bool = True,
    min_size_px: int = 8,
    max_size_px: int = 30,
    stroke_fill: RGB | None = None,
) -> None:
    x0, y0, x1, y1 = [float(value) * int(scale) for value in bbox]
    font = fit_font_to_box(
        draw,
        text=str(text),
        max_width=max(1.0, float(x1 - x0)),
        max_height=max(1.0, float(y1 - y0)),
        bold=bool(bold),
        min_size_px=int(min_size_px) * int(scale),
        max_size_px=int(max_size_px) * int(scale),
        fill_ratio=0.84,
    )
    try:
        text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(scale) if stroke_fill else 0))
        text_w = float(text_bbox[2] - text_bbox[0])
        text_h = float(text_bbox[3] - text_bbox[1])
    except Exception:
        text_w, text_h = draw.textsize(str(text), font=font)
    tx = float(x0 + (x1 - x0 - text_w) * 0.5)
    ty = float(y0 + (y1 - y0 - text_h) * 0.5)
    draw.text(
        (int(round(tx)), int(round(ty))),
        str(text),
        font=font,
        fill=tuple(fill),
        stroke_width=max(0, int(scale) if stroke_fill else 0),
        stroke_fill=tuple(stroke_fill) if stroke_fill else None,
    )


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


def _safe_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _safe_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_json(item) for item in value]
    if isinstance(value, float):
        return round(float(value), 3)
    return value


def _sample_layout(rng, *, width: int, height: int) -> Dict[str, Any]:
    layout_id = str(rng.choice(("linear_bays", "two_level_hall", "central_concourse")))
    margin_x = 58.0
    if layout_id == "linear_bays":
        bay_w = (float(width) - 2.0 * margin_x - 3.0 * 24.0) / 4.0
        y0 = float(rng.uniform(288.0, 330.0))
        y1 = float(rng.uniform(620.0, 682.0))
        area_boxes = {
            area_id: [round(margin_x + i * (bay_w + 24.0), 3), round(y0, 3), round(margin_x + i * (bay_w + 24.0) + bay_w, 3), round(y1, 3)]
            for i, area_id in enumerate(TRANSIT_BOARDING_AREA_IDS)
        }
        concourse = [55.0, y1 + 34.0, float(width) - 55.0, float(height) - 50.0]
    elif layout_id == "two_level_hall":
        left = 72.0
        gap_x = 34.0
        gap_y = 34.0
        bay_w = (float(width) - 2.0 * left - gap_x) / 2.0
        bay_h = float(rng.uniform(188.0, 224.0))
        top_y = float(rng.uniform(238.0, 275.0))
        area_boxes = {}
        for index, area_id in enumerate(TRANSIT_BOARDING_AREA_IDS):
            col = index % 2
            row = index // 2
            x0 = left + float(col) * (bay_w + gap_x)
            y0 = top_y + float(row) * (bay_h + gap_y)
            area_boxes[area_id] = [round(x0, 3), round(y0, 3), round(x0 + bay_w, 3), round(y0 + bay_h, 3)]
        concourse = [82.0, top_y + 2.0 * bay_h + gap_y + 30.0, float(width) - 82.0, float(height) - 48.0]
    else:
        left_w = float(rng.uniform(260.0, 310.0))
        right_w = float(rng.uniform(260.0, 310.0))
        top = float(rng.uniform(240.0, 284.0))
        area_h = float(rng.uniform(170.0, 214.0))
        area_boxes = {
            "area_a": [58.0, top, 58.0 + left_w, top + area_h],
            "area_b": [58.0, top + area_h + 40.0, 58.0 + left_w, top + 2.0 * area_h + 40.0],
            "area_c": [float(width) - 58.0 - right_w, top, float(width) - 58.0, top + area_h],
            "area_d": [float(width) - 58.0 - right_w, top + area_h + 40.0, float(width) - 58.0, top + 2.0 * area_h + 40.0],
        }
        area_boxes = {key: [round(float(v), 3) for v in box] for key, box in area_boxes.items()}
        concourse = [58.0 + left_w + 34.0, top + 22.0, float(width) - 58.0 - right_w - 34.0, min(float(height) - 58.0, top + 2.0 * area_h + 72.0)]
    return {
        "layout_id": layout_id,
        "area_bboxes": area_boxes,
        "concourse_bbox": [round(float(v), 3) for v in concourse],
        "horizon_y": round(float(rng.uniform(184.0, 230.0)), 3),
    }


def _area_bbox(layout: Mapping[str, Any], area_id: str) -> BBox | None:
    boxes = layout.get("area_bboxes")
    if isinstance(boxes, Mapping) and str(area_id) in boxes:
        return tuple(float(v) for v in boxes[str(area_id)])  # type: ignore[return-value]
    if str(area_id) == "concourse":
        return tuple(float(v) for v in layout["concourse_bbox"])  # type: ignore[return-value]
    return None


def _draw_terminal_shell(draw: ImageDraw.ImageDraw, *, rng, setting_id: str, layout: Mapping[str, Any], width: int, height: int, scale: int) -> List[TransitDecor]:
    decor: List[TransitDecor] = []
    wall_top = _jitter_rgb(rng, (202, 220, 229), amount=8)
    wall = _jitter_rgb(rng, (224, 228, 226), amount=8)
    floor = _jitter_rgb(rng, (193, 188, 179), amount=10)
    horizon = float(layout["horizon_y"])
    _rect(draw, (0.0, 0.0, float(width), horizon), fill=wall_top, outline=None, width=1, scale=scale)
    _rect(draw, (0.0, horizon, float(width), float(height)), fill=wall, outline=None, width=1, scale=scale)
    _poly(
        draw,
        [(0.0, horizon + 82.0), (float(width), horizon + 82.0), (float(width), float(height)), (0.0, float(height))],
        fill=floor,
        outline=None,
        width=1,
        scale=scale,
    )
    for x in (float(width) * 0.12, float(width) * 0.32, float(width) * 0.55, float(width) * 0.78):
        _line(draw, [(x, horizon + 82.0), (x + float(rng.uniform(-90.0, 90.0)), float(height))], fill=_jitter_rgb(rng, (171, 166, 158), 5), width=2, scale=scale)
    if str(setting_id) == "airport_concourse":
        for index in range(5):
            x0 = 88.0 + float(index) * 228.0
            window = (x0, 60.0, x0 + 154.0, 172.0)
            _rect(draw, window, fill=_jitter_rgb(rng, (171, 207, 229), 7), outline=(107, 123, 136), width=2, scale=scale, radius=8)
            decor.append(TransitDecor(f"decor_window_{index}", "terminal_window", tuple(round(float(v), 3) for v in window), {}))
        plane = (865.0, 92.0, 1180.0, 162.0)
        _ellipse(draw, plane, fill=_jitter_rgb(rng, (236, 239, 241), 5), outline=(92, 103, 117), width=2, scale=scale)
        _poly(draw, [(980.0, 108.0), (1058.0, 32.0), (1082.0, 114.0)], fill=_jitter_rgb(rng, (96, 139, 190), 6), outline=(72, 82, 94), width=2, scale=scale)
        decor.append(TransitDecor("decor_airplane", "airplane_outside_window", tuple(round(float(v), 3) for v in plane), {}))
    else:
        for index in range(4):
            x0 = 95.0 + float(index) * 285.0
            arch = (x0, 78.0, x0 + 180.0, 188.0)
            _rect(draw, arch, fill=_jitter_rgb(rng, (180, 199, 205), 8), outline=(111, 121, 129), width=2, scale=scale, radius=12)
            decor.append(TransitDecor(f"decor_terminal_arch_{index}", "terminal_window", tuple(round(float(v), 3) for v in arch), {}))
    board = (float(rng.uniform(490.0, 610.0)), 58.0, float(rng.uniform(825.0, 950.0)), 152.0)
    _rect(draw, board, fill=(37, 52, 62), outline=(20, 27, 32), width=2, scale=scale, radius=8)
    _draw_fit_text(draw, text="DEPARTURES", bbox=(board[0] + 18.0, board[1] + 12.0, board[2] - 18.0, board[1] + 42.0), scale=scale, fill=(240, 224, 106), max_size_px=22)
    for row in range(3):
        y = board[1] + 48.0 + float(row) * 23.0
        _line(draw, [(board[0] + 18.0, y), (board[2] - 18.0, y)], fill=(95, 115, 125), width=1, scale=scale)
    decor.append(TransitDecor("decor_departure_board", "departure_board", tuple(round(float(v), 3) for v in board), {}))
    clock_cx = float(rng.choice((196.0, 1090.0)))
    clock = (clock_cx - 38.0, 72.0, clock_cx + 38.0, 148.0)
    _ellipse(draw, clock, fill=(244, 244, 238), outline=(58, 66, 77), width=3, scale=scale)
    _line(draw, [(clock_cx, 110.0), (clock_cx, 88.0)], fill=(58, 66, 77), width=3, scale=scale)
    _line(draw, [(clock_cx, 110.0), (clock_cx + 24.0, 122.0)], fill=(58, 66, 77), width=3, scale=scale)
    decor.append(TransitDecor("decor_clock", "clock", tuple(round(float(v), 3) for v in clock), {}))
    return decor


def _draw_vehicle_for_area(
    draw: ImageDraw.ImageDraw,
    *,
    rng,
    setting_id: str,
    area_id: str,
    area_box: BBox,
    scale: int,
) -> TransitDecor:
    x0, y0, x1, y1 = area_box
    if str(setting_id) == "rail_station":
        vehicle = (x0 + 18.0, y0 + 20.0, x1 - 18.0, y0 + 86.0)
        _rect(draw, vehicle, fill=_jitter_rgb(rng, (91, 129, 170), 8), outline=(52, 62, 76), width=2, scale=scale, radius=10)
        for index in range(4):
            wx0 = vehicle[0] + 26.0 + float(index) * max(28.0, (vehicle[2] - vehicle[0] - 72.0) / 4.0)
            _rect(draw, (wx0, vehicle[1] + 16.0, wx0 + 34.0, vehicle[1] + 42.0), fill=(198, 225, 232), outline=(52, 62, 76), width=1, scale=scale, radius=4)
        _line(draw, [(x0 + 10.0, vehicle[3] + 15.0), (x1 - 10.0, vehicle[3] + 15.0)], fill=(76, 82, 86), width=4, scale=scale)
        return TransitDecor(f"decor_vehicle_{area_id}", "train_car", tuple(round(float(v), 3) for v in vehicle), {"area_id": str(area_id)})
    if str(setting_id) == "bus_terminal":
        vehicle = (x0 + 26.0, y0 + 18.0, x1 - 24.0, y0 + 98.0)
        _rect(draw, vehicle, fill=_jitter_rgb(rng, rng.choice(((218, 151, 69), (82, 151, 178), (207, 93, 88))), 8), outline=(56, 64, 74), width=2, scale=scale, radius=12)
        _rect(draw, (vehicle[0] + 20.0, vehicle[1] + 16.0, vehicle[2] - 42.0, vehicle[1] + 46.0), fill=(200, 225, 232), outline=(56, 64, 74), width=1, scale=scale, radius=5)
        for wx in (vehicle[0] + 42.0, vehicle[2] - 62.0):
            _ellipse(draw, (wx, vehicle[3] - 10.0, wx + 30.0, vehicle[3] + 20.0), fill=(45, 49, 55), outline=(23, 26, 29), width=1, scale=scale)
        return TransitDecor(f"decor_vehicle_{area_id}", "bus", tuple(round(float(v), 3) for v in vehicle), {"area_id": str(area_id)})
    gate = (x0 + 34.0, y0 + 18.0, x1 - 34.0, y0 + 82.0)
    _rect(draw, gate, fill=_jitter_rgb(rng, (185, 206, 218), 8), outline=(88, 101, 116), width=2, scale=scale, radius=8)
    jetway = (gate[0] + 0.20 * (gate[2] - gate[0]), gate[3] - 10.0, gate[0] + 0.78 * (gate[2] - gate[0]), gate[3] + 26.0)
    _rect(draw, jetway, fill=_jitter_rgb(rng, (151, 164, 171), 6), outline=(88, 101, 116), width=1, scale=scale, radius=5)
    return TransitDecor(f"decor_vehicle_{area_id}", "airport_gate_window", tuple(round(float(v), 3) for v in gate), {"area_id": str(area_id)})


def _draw_area(
    draw: ImageDraw.ImageDraw,
    *,
    rng,
    setting_id: str,
    area_id: str,
    area_box: BBox,
    scale: int,
) -> Tuple[TransitArea, List[TransitDecor]]:
    x0, y0, x1, y1 = area_box
    decor: List[TransitDecor] = []
    platform = (x0, y0 + 102.0, x1, y1)
    sign = (x0 + 18.0, y0 + 12.0, min(x1 - 18.0, x0 + 215.0), y0 + 58.0)
    _rect(draw, area_box, fill=_jitter_rgb(rng, (205, 202, 190), 8), outline=(129, 123, 111), width=2, scale=scale, radius=12)
    vehicle_decor = _draw_vehicle_for_area(draw, rng=rng, setting_id=str(setting_id), area_id=str(area_id), area_box=area_box, scale=scale)
    decor.append(vehicle_decor)
    _poly(
        draw,
        [(platform[0], platform[1]), (platform[2], platform[1] + 8.0), (platform[2] - 6.0, platform[3]), (platform[0] + 6.0, platform[3])],
        fill=_jitter_rgb(rng, (185, 177, 162), 8),
        outline=(122, 116, 104),
        width=2,
        scale=scale,
    )
    _line(draw, [(platform[0] + 10.0, platform[1] + 28.0), (platform[2] - 10.0, platform[1] + 28.0)], fill=(226, 195, 70), width=5, scale=scale)
    sign_fill = _jitter_rgb(rng, rng.choice(((46, 85, 138), (43, 111, 108), (115, 74, 139), (133, 82, 54))), 6)
    _rect(draw, sign, fill=sign_fill, outline=(38, 45, 52), width=2, scale=scale, radius=6)
    label = transit_area_display_name(str(area_id)).replace("Boarding ", "")
    _draw_fit_text(draw, text=label.upper(), bbox=(sign[0] + 8.0, sign[1] + 5.0, sign[2] - 8.0, sign[3] - 5.0), scale=scale, fill=(248, 247, 238), max_size_px=22, stroke_fill=(38, 45, 52))
    bench_y = platform[1] + 48.0
    if y1 - bench_y > 72.0 and float(rng.random()) < 0.82:
        bench = (x0 + 24.0, bench_y, min(x1 - 28.0, x0 + 150.0), bench_y + 42.0)
        _draw_bench(draw, rng=rng, bbox=bench, scale=scale)
        decor.append(TransitDecor(f"decor_bench_{area_id}", "bench", tuple(round(float(v), 3) for v in bench), {"area_id": str(area_id)}))
    return (
        TransitArea(
            area_id=str(area_id),
            display_name=transit_area_display_name(str(area_id)),
            label=str(label),
            bbox_xyxy=tuple(round(float(v), 3) for v in area_box),
            sign_bbox_xyxy=tuple(round(float(v), 3) for v in sign),
            platform_bbox_xyxy=tuple(round(float(v), 3) for v in platform),
            attributes={"setting_id": str(setting_id)},
        ),
        decor,
    )


def _draw_bench(draw: ImageDraw.ImageDraw, *, rng, bbox: BBox, scale: int) -> None:
    x0, y0, x1, y1 = bbox
    wood = _jitter_rgb(rng, (142, 91, 58), 8)
    outline = (74, 57, 45)
    _rect(draw, (x0, y0 + 5.0, x1, y0 + 18.0), fill=wood, outline=outline, width=1, scale=scale, radius=4)
    _rect(draw, (x0 + 8.0, y0 + 24.0, x1 - 8.0, y0 + 36.0), fill=wood, outline=outline, width=1, scale=scale, radius=4)
    for lx in (x0 + 20.0, x1 - 30.0):
        _rect(draw, (lx, y0 + 34.0, lx + 8.0, y1), fill=outline, outline=None, width=1, scale=scale, radius=2)


def _draw_terminal_decor(
    draw: ImageDraw.ImageDraw,
    *,
    rng,
    layout: Mapping[str, Any],
    width: int,
    height: int,
    scale: int,
    show_service_points: bool,
) -> List[TransitDecor]:
    decor: List[TransitDecor] = []
    concourse = tuple(float(v) for v in layout["concourse_bbox"])
    if not bool(show_service_points):
        kiosk = (concourse[0] + float(rng.uniform(18.0, 58.0)), concourse[1] + 18.0, concourse[0] + float(rng.uniform(118.0, 168.0)), concourse[1] + 120.0)
        _rect(draw, kiosk, fill=_jitter_rgb(rng, (104, 139, 158), 8), outline=(55, 65, 74), width=2, scale=scale, radius=8)
        _draw_fit_text(draw, text="INFO", bbox=(kiosk[0] + 10.0, kiosk[1] + 12.0, kiosk[2] - 10.0, kiosk[1] + 42.0), scale=scale, fill=(250, 246, 226), max_size_px=22)
        decor.append(TransitDecor("decor_info_kiosk", "info_kiosk", tuple(round(float(v), 3) for v in kiosk), {}))
    cart_count = int(rng.randint(4, 7))
    for index in range(cart_count):
        x = float(rng.uniform(concourse[0] + 20.0, max(concourse[0] + 22.0, concourse[2] - 90.0)))
        y = float(rng.uniform(concourse[1] + 28.0, max(concourse[1] + 30.0, concourse[3] - 70.0)))
        cart = (x, y, x + 68.0, y + 48.0)
        _rect(draw, (x + 10.0, y + 10.0, x + 58.0, y + 34.0), fill=_jitter_rgb(rng, (185, 101, 83), 8), outline=(64, 70, 78), width=1, scale=scale, radius=5)
        _line(draw, [(x + 6.0, y + 38.0), (x + 64.0, y + 38.0)], fill=(64, 70, 78), width=3, scale=scale)
        for wx in (x + 12.0, x + 52.0):
            _ellipse(draw, (wx, y + 35.0, wx + 10.0, y + 45.0), fill=(48, 52, 56), outline=None, width=1, scale=scale)
        decor.append(TransitDecor(f"decor_luggage_cart_{index}", "luggage_cart", tuple(round(float(v), 3) for v in cart), {}))
    rope_y = concourse[1] + float(rng.uniform(130.0, max(134.0, min(205.0, concourse[3] - concourse[1] - 30.0))))
    rope = (concourse[0] + 90.0, rope_y - 22.0, concourse[2] - 72.0, rope_y + 24.0)
    for i in range(4):
        px = rope[0] + float(i) * max(46.0, (rope[2] - rope[0]) / 3.0)
        _line(draw, [(px, rope_y - 18.0), (px, rope_y + 18.0)], fill=(70, 75, 82), width=4, scale=scale)
    _line(draw, [(rope[0], rope_y), (rope[2], rope_y)], fill=(168, 72, 76), width=4, scale=scale)
    decor.append(TransitDecor("decor_queue_rope", "queue_rope", tuple(round(float(v), 3) for v in rope), {}))
    return decor


def _service_point_layout(layout: Mapping[str, Any], *, width: int, height: int) -> Dict[str, Dict[str, BBox]]:
    concourse = tuple(float(v) for v in layout["concourse_bbox"])
    cx0, cy0, cx1, cy1 = concourse
    available_w = max(360.0, cx1 - cx0)
    available_h = max(124.0, cy1 - cy0)
    lane_gap = 14.0
    lane_w = max(118.0, (available_w - 2.0 * lane_gap) / 3.0)
    top = cy0 + 14.0
    if available_h < 158.0:
        top = cy0 + 8.0
    counter_h = 34.0
    queue_top = top + counter_h + 6.0
    queue_bottom = min(cy1 - 8.0, queue_top + max(72.0, available_h - counter_h - 30.0))
    result: Dict[str, Dict[str, BBox]] = {}
    for index, service_id in enumerate(TRANSIT_SERVICE_POINT_IDS):
        x0 = cx0 + float(index) * (lane_w + lane_gap) + 8.0
        x1 = min(cx1 - 8.0, x0 + lane_w - 16.0)
        if x1 - x0 < 96.0:
            x0 = max(28.0, cx0 + 12.0 + float(index % 2) * max(120.0, 0.46 * available_w))
            x1 = min(float(width) - 28.0, x0 + max(110.0, 0.42 * available_w))
        counter = (x0, top, x1, top + counter_h)
        sign = (x0 + 8.0, top + 5.0, x1 - 8.0, top + counter_h - 5.0)
        queue = (x0 + 4.0, queue_top, x1 - 4.0, max(queue_top + 62.0, queue_bottom))
        result[str(service_id)] = {
            "counter": tuple(round(float(v), 3) for v in counter),  # type: ignore[dict-item]
            "sign": tuple(round(float(v), 3) for v in sign),  # type: ignore[dict-item]
            "queue": tuple(round(float(v), 3) for v in queue),  # type: ignore[dict-item]
        }
    return result


def _draw_service_points(
    draw: ImageDraw.ImageDraw,
    *,
    rng,
    layout: Mapping[str, Any],
    width: int,
    height: int,
    scale: int,
) -> Tuple[TransitServicePoint, ...]:
    service_layout = _service_point_layout(layout, width=width, height=height)
    colors: Dict[str, RGB] = {
        "security_queue": (88, 120, 170),
        "ticket_counter": (63, 143, 122),
        "gate_queue": (150, 102, 166),
    }
    label_text = {
        "security_queue": "SECURITY",
        "ticket_counter": "TICKETS",
        "gate_queue": "GATE",
    }
    points: List[TransitServicePoint] = []
    for service_id in TRANSIT_SERVICE_POINT_IDS:
        spec = service_layout[str(service_id)]
        counter = spec["counter"]
        sign = spec["sign"]
        queue = spec["queue"]
        fill = _jitter_rgb(rng, colors[str(service_id)], 6)
        _rect(draw, counter, fill=fill, outline=(42, 49, 58), width=2, scale=scale, radius=6)
        _draw_fit_text(
            draw,
            text=label_text[str(service_id)],
            bbox=sign,
            scale=scale,
            fill=(250, 246, 232),
            max_size_px=18,
            stroke_fill=(42, 49, 58),
        )
        qx0, qy0, qx1, qy1 = queue
        rope_color = _jitter_rgb(rng, (162, 72, 76), 5)
        post_color = (72, 77, 84)
        for px in (qx0 + 8.0, qx1 - 8.0):
            _line(draw, [(px, qy0 + 3.0), (px, qy1 - 3.0)], fill=post_color, width=3, scale=scale)
        _line(draw, [(qx0 + 8.0, qy0 + 12.0), (qx1 - 8.0, qy0 + 12.0)], fill=rope_color, width=3, scale=scale)
        _line(draw, [(qx0 + 8.0, qy1 - 12.0), (qx1 - 8.0, qy1 - 12.0)], fill=rope_color, width=3, scale=scale)
        points.append(
            TransitServicePoint(
                service_point_id=str(service_id),
                display_name=transit_service_point_display_name(str(service_id)),
                bbox_xyxy=tuple(round(float(v), 3) for v in counter),
                sign_bbox_xyxy=tuple(round(float(v), 3) for v in sign),
                queue_bbox_xyxy=tuple(round(float(v), 3) for v in queue),
                attributes={"label": str(label_text[str(service_id)])},
            )
        )
    return tuple(points)


def _candidate_person_box(rng, *, layout: Mapping[str, Any], area_id: str, pose_id: str, width: int, height: int) -> BBox:
    area = _area_bbox(layout, str(area_id)) or tuple(float(v) for v in layout["concourse_bbox"])
    if str(area_id) in set(TRANSIT_BOARDING_AREA_IDS):
        y_min = area[1] + min(138.0, 0.50 * (area[3] - area[1]))
        y_max = area[3] - 12.0
        x_min = area[0] + 24.0
        x_max = area[2] - 24.0
    else:
        x_min, y_min, x_max, y_max = area[0] + 26.0, area[1] + 20.0, area[2] - 26.0, area[3] - 14.0
    person_h = float(rng.uniform(76.0, 104.0))
    if str(pose_id) == "seated":
        person_h = float(rng.uniform(62.0, 82.0))
    person_w = person_h * float(rng.uniform(0.46, 0.64))
    if x_max <= x_min:
        x_min, x_max = 70.0, float(width) - 70.0
    if y_max <= y_min:
        y_min, y_max = 430.0, float(height) - 40.0
    cx = float(rng.uniform(x_min, x_max))
    bottom = float(rng.uniform(y_min + person_h, y_max))
    x0 = max(18.0, min(float(width) - person_w - 18.0, cx - 0.5 * person_w))
    y1 = max(260.0, min(float(height) - 18.0, bottom))
    return (round(x0, 3), round(y1 - person_h, 3), round(x0 + person_w, 3), round(y1, 3))


def _queue_person_box(
    rng,
    *,
    layout: Mapping[str, Any],
    service_point_id: str,
    queue_index: int,
    width: int,
    height: int,
) -> BBox:
    service_layout = _service_point_layout(layout, width=width, height=height)
    queue = service_layout.get(str(service_point_id), service_layout[TRANSIT_SERVICE_POINT_IDS[0]])["queue"]
    qx0, qy0, qx1, qy1 = queue
    person_h = float(rng.uniform(58.0, 72.0))
    person_w = person_h * float(rng.uniform(0.44, 0.55))
    usable_w = max(person_w + 8.0, qx1 - qx0 - 18.0)
    usable_h = max(person_h + 8.0, qy1 - qy0 - 10.0)
    cols = max(1, min(4, int(usable_w // max(36.0, person_w + 10.0))))
    row = int(queue_index) // int(cols)
    col = int(queue_index) % int(cols)
    row_h = max(person_h + 6.0, usable_h / max(1.0, float(row + 1)))
    if qy0 + 8.0 + float(row + 1) * row_h + 4.0 > qy1:
        cols = max(1, min(5, int(usable_w // max(30.0, person_w + 6.0))))
        row = int(queue_index) // int(cols)
        col = int(queue_index) % int(cols)
        row_h = max(44.0, min(person_h + 4.0, usable_h / max(1.0, float(row + 1))))
        person_h = min(person_h, max(48.0, row_h - 4.0))
        person_w = min(person_w, max(24.0, usable_w / max(1, cols) - 8.0))
    cell_w = usable_w / max(1, cols)
    cx = qx0 + 9.0 + (float(col) + 0.5) * cell_w + float(rng.uniform(-3.0, 3.0))
    bottom = qy0 + 8.0 + (float(row) + 1.0) * row_h + float(rng.uniform(-2.0, 2.0))
    bottom = min(qy1 - 5.0, max(qy0 + person_h + 4.0, bottom))
    x0 = max(18.0, min(float(width) - person_w - 18.0, cx - 0.5 * person_w))
    return (round(x0, 3), round(bottom - person_h, 3), round(x0 + person_w, 3), round(bottom, 3))


def _place_persons(rng, *, specs: Sequence[TransitPersonSpec], layout: Mapping[str, Any], width: int, height: int) -> Tuple[Tuple[TransitPersonSpec, BBox, str], ...]:
    placed: List[Tuple[TransitPersonSpec, BBox, str]] = []
    existing: List[BBox] = []
    ordered = list(specs)
    rng.shuffle(ordered)
    queue_counts: Dict[str, int] = {}
    for index, spec in enumerate(ordered):
        pose_id = str(spec.attributes.get("pose_id") or rng.choice(TRANSIT_PERSON_POSES))
        box: BBox | None = None
        service_point_id = spec.attributes.get("service_point_id")
        if bool(spec.attributes.get("queue_member")) and service_point_id is not None:
            queue_index = int(queue_counts.get(str(service_point_id), 0))
            queue_counts[str(service_point_id)] = int(queue_index) + 1
            box = _queue_person_box(
                rng,
                layout=layout,
                service_point_id=str(service_point_id),
                queue_index=int(queue_index),
                width=width,
                height=height,
            )
        else:
            for _attempt in range(200):
                candidate = _candidate_person_box(rng, layout=layout, area_id=str(spec.area_id), pose_id=pose_id, width=width, height=height)
                if all(not _expanded_intersects(candidate, other, 8.0) for other in existing):
                    box = candidate
                    break
        if box is None:
            col = index % 8
            row = index // 8
            x = 78.0 + float(col) * 138.0
            y = 530.0 + float(row) * 112.0
            box = (x, y, x + 42.0, y + 84.0)
        existing.append(tuple(float(v) for v in box))
        placed.append((spec, tuple(float(v) for v in box), pose_id))
    return tuple(placed)


def _skin_color(rng) -> RGB:
    return tuple(int(v) for v in rng.choice(((200, 145, 101), (169, 111, 82), (219, 164, 113), (136, 89, 68), (232, 181, 130))))  # type: ignore[return-value]


def _clothes_color(rng) -> RGB:
    return tuple(int(v) for v in rng.choice(((74, 122, 180), (194, 83, 85), (220, 169, 75), (94, 151, 124), (130, 104, 160), (83, 154, 177), (202, 114, 80))))  # type: ignore[return-value]


def _rel(box: BBox, x0: float, y0: float, x1: float, y1: float) -> BBox:
    bx0, by0, bx1, by1 = box
    w = bx1 - bx0
    h = by1 - by0
    return (bx0 + x0 * w, by0 + y0 * h, bx0 + x1 * w, by0 + y1 * h)


def _draw_shadow(draw: ImageDraw.ImageDraw, bbox: BBox, *, scale: int) -> None:
    x0, y0, x1, y1 = bbox
    _ellipse(draw, (x0 + 0.08 * (x1 - x0), y1 - 0.06 * (y1 - y0), x1 - 0.04 * (x1 - x0), y1 + 0.04 * (y1 - y0)), fill=(132, 128, 119), outline=None, width=1, scale=scale)


def _draw_person(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: BBox,
    pose_id: str,
    primary: RGB,
    accent: RGB,
    skin: RGB,
    gender_id: str,
    style_id: str,
    scale: int,
) -> Tuple[TransitDecor, ...]:
    outline, line_width, shadow = _style_params(str(style_id))
    if shadow:
        _draw_shadow(draw, bbox, scale=scale)
    x0, y0, x1, y1 = bbox
    decor: List[TransitDecor] = []
    gender = normalize_person_gender(gender_id)
    head = _rel(bbox, 0.30, 0.03, 0.70, 0.27)
    torso = _rel(bbox, 0.28, 0.29, 0.74, 0.53 if gender == "female" else 0.60)
    draw_person_hair_back(draw, head_bbox=head, gender_id=gender, scale=scale, outline=outline)
    _ellipse(draw, head, fill=skin, outline=outline, width=line_width, scale=scale)
    draw_person_hair_front(draw, head_bbox=head, gender_id=gender, scale=scale, outline=outline)
    _rect(draw, torso, fill=primary, outline=outline, width=line_width, scale=scale, radius=7)
    leg_color = (63, 71, 88)
    if str(pose_id) == "walking":
        _line(draw, [(x0 + 0.42 * (x1 - x0), y0 + 0.58 * (y1 - y0)), (x0 + 0.18 * (x1 - x0), y1 - 2.0)], fill=leg_color, width=max(4, line_width + 3), scale=scale)
        _line(draw, [(x0 + 0.58 * (x1 - x0), y0 + 0.58 * (y1 - y0)), (x0 + 0.82 * (x1 - x0), y1 - 4.0)], fill=leg_color, width=max(4, line_width + 3), scale=scale)
        _line(draw, [(x0 + 0.32 * (x1 - x0), y0 + 0.36 * (y1 - y0)), (x0 + 0.15 * (x1 - x0), y0 + 0.56 * (y1 - y0))], fill=primary, width=max(3, line_width + 2), scale=scale)
        _line(draw, [(x0 + 0.70 * (x1 - x0), y0 + 0.36 * (y1 - y0)), (x0 + 0.90 * (x1 - x0), y0 + 0.50 * (y1 - y0))], fill=primary, width=max(3, line_width + 2), scale=scale)
    elif str(pose_id) == "seated":
        _line(draw, [(x0 + 0.38 * (x1 - x0), y0 + 0.60 * (y1 - y0)), (x0 + 0.20 * (x1 - x0), y0 + 0.82 * (y1 - y0)), (x0 + 0.48 * (x1 - x0), y0 + 0.84 * (y1 - y0))], fill=leg_color, width=max(4, line_width + 3), scale=scale)
        _line(draw, [(x0 + 0.60 * (x1 - x0), y0 + 0.60 * (y1 - y0)), (x0 + 0.78 * (x1 - x0), y0 + 0.82 * (y1 - y0)), (x0 + 0.98 * (x1 - x0), y0 + 0.80 * (y1 - y0))], fill=leg_color, width=max(4, line_width + 3), scale=scale)
    else:
        _line(draw, [(x0 + 0.42 * (x1 - x0), y0 + 0.58 * (y1 - y0)), (x0 + 0.36 * (x1 - x0), y1 - 3.0)], fill=leg_color, width=max(4, line_width + 3), scale=scale)
        _line(draw, [(x0 + 0.58 * (x1 - x0), y0 + 0.58 * (y1 - y0)), (x0 + 0.66 * (x1 - x0), y1 - 3.0)], fill=leg_color, width=max(4, line_width + 3), scale=scale)
        _line(draw, [(x0 + 0.30 * (x1 - x0), y0 + 0.36 * (y1 - y0)), (x0 + 0.18 * (x1 - x0), y0 + 0.62 * (y1 - y0))], fill=primary, width=max(3, line_width + 2), scale=scale)
        _line(draw, [(x0 + 0.70 * (x1 - x0), y0 + 0.36 * (y1 - y0)), (x0 + 0.82 * (x1 - x0), y0 + 0.62 * (y1 - y0))], fill=primary, width=max(3, line_width + 2), scale=scale)
    if gender == "female":
        bottom_factor = 0.70 if str(pose_id) == "seated" else 0.73
        draw_person_skirt(draw, torso_bbox=torso, bottom_y=y0 + bottom_factor * (y1 - y0), fill=primary, outline=outline, scale=scale, width=line_width)
    if str(pose_id) == "with_luggage":
        bag = (x1 + 2.0, y1 - 0.35 * (y1 - y0), x1 + 0.22 * (y1 - y0), y1 - 2.0)
        _rect(draw, bag, fill=accent, outline=outline, width=1, scale=scale, radius=4)
        _line(draw, [(bag[0] + 0.5 * (bag[2] - bag[0]), bag[1]), (bag[0] + 0.5 * (bag[2] - bag[0]), bag[1] - 14.0)], fill=outline, width=2, scale=scale)
        decor.append(TransitDecor("pending_luggage", "person_luggage", tuple(round(float(v), 3) for v in bag), {}))
    return tuple(decor)


def _candidate_luggage_box(rng, *, layout: Mapping[str, Any], area_id: str, luggage_type: str, width: int, height: int) -> BBox:
    area = _area_bbox(layout, str(area_id)) or tuple(float(v) for v in layout["concourse_bbox"])
    if str(area_id) in set(TRANSIT_BOARDING_AREA_IDS):
        x_min = area[0] + 18.0
        x_max = area[2] - 18.0
        y_min = area[1] + min(142.0, 0.54 * (area[3] - area[1]))
        y_max = area[3] - 8.0
    else:
        x_min, y_min, x_max, y_max = area[0] + 18.0, area[1] + 18.0, area[2] - 18.0, area[3] - 12.0
    if str(luggage_type) == "luggage_cart":
        item_w = float(rng.uniform(54.0, 66.0))
        item_h = float(rng.uniform(34.0, 44.0))
    elif str(luggage_type) == "backpack":
        item_w = float(rng.uniform(28.0, 38.0))
        item_h = float(rng.uniform(36.0, 50.0))
    else:
        item_w = float(rng.uniform(32.0, 44.0))
        item_h = float(rng.uniform(40.0, 54.0))
    if x_max <= x_min:
        x_min, x_max = 64.0, float(width) - 64.0
    if y_max <= y_min:
        y_min, y_max = 390.0, float(height) - 34.0
    x0 = float(rng.uniform(x_min, max(x_min + 1.0, x_max - item_w)))
    y1 = float(rng.uniform(y_min + item_h, max(y_min + item_h + 1.0, y_max)))
    return (round(x0, 3), round(y1 - item_h, 3), round(x0 + item_w, 3), round(y1, 3))


def _place_luggage(
    rng,
    *,
    specs: Sequence[TransitLuggageSpec],
    layout: Mapping[str, Any],
    width: int,
    height: int,
    occupied: Sequence[BBox] = (),
) -> Tuple[Tuple[TransitLuggageSpec, BBox], ...]:
    placed: List[Tuple[TransitLuggageSpec, BBox]] = []
    existing: List[BBox] = [tuple(float(v) for v in box) for box in occupied]
    ordered = list(specs)
    rng.shuffle(ordered)
    for index, spec in enumerate(ordered):
        box: BBox | None = None
        for _attempt in range(220):
            candidate = _candidate_luggage_box(
                rng,
                layout=layout,
                area_id=str(spec.area_id),
                luggage_type=str(spec.luggage_type),
                width=width,
                height=height,
            )
            if all(not _expanded_intersects(candidate, other, 1.0) for other in existing):
                box = candidate
                break
        if box is None:
            area = _area_bbox(layout, str(spec.area_id)) or tuple(float(v) for v in layout["concourse_bbox"])
            col = index % 7
            row = index // 7
            item_w = 34.0 if str(spec.luggage_type) != "luggage_cart" else 50.0
            item_h = 40.0 if str(spec.luggage_type) != "luggage_cart" else 34.0
            if str(spec.area_id) in set(TRANSIT_BOARDING_AREA_IDS):
                min_x = area[0] + 18.0
                max_x = area[2] - item_w - 12.0
                min_y = area[1] + min(136.0, 0.52 * (area[3] - area[1]))
                max_y = area[3] - item_h - 8.0
            else:
                min_x = area[0] + 18.0
                max_x = area[2] - item_w - 12.0
                min_y = area[1] + 18.0
                max_y = area[3] - item_h - 8.0
            x = max(min_x, min(max_x, min_x + float(col) * 39.0))
            y = max(min_y, min(max_y, min_y + float(row) * 34.0))
            box = (x, y, x + item_w, y + item_h)
        existing.append(tuple(float(v) for v in box))
        placed.append((spec, tuple(float(v) for v in box)))
    return tuple(placed)


def _draw_luggage_item(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: BBox,
    luggage_type: str,
    color: RGB,
    style_id: str,
    scale: int,
) -> None:
    outline, line_width, shadow = _style_params(str(style_id))
    if shadow:
        _draw_shadow(draw, bbox, scale=scale)
    x0, y0, x1, y1 = bbox
    if str(luggage_type) == "luggage_cart":
        _rect(draw, (x0 + 0.08 * (x1 - x0), y0 + 0.24 * (y1 - y0), x1 - 0.06 * (x1 - x0), y1 - 0.18 * (y1 - y0)), fill=color, outline=outline, width=line_width, scale=scale, radius=5)
        _line(draw, [(x0 + 0.06 * (x1 - x0), y1 - 0.12 * (y1 - y0)), (x1 - 0.02 * (x1 - x0), y1 - 0.12 * (y1 - y0))], fill=outline, width=max(2, line_width + 1), scale=scale)
        _line(draw, [(x1 - 0.16 * (x1 - x0), y0 + 0.12 * (y1 - y0)), (x1 - 0.02 * (x1 - x0), y0 - 0.10 * (y1 - y0))], fill=outline, width=max(2, line_width), scale=scale)
        for wx in (x0 + 0.18 * (x1 - x0), x1 - 0.22 * (x1 - x0)):
            _ellipse(draw, (wx - 4.0, y1 - 8.0, wx + 6.0, y1 + 2.0), fill=(45, 49, 55), outline=None, width=1, scale=scale)
        return
    if str(luggage_type) == "backpack":
        _rect(draw, (x0 + 0.10 * (x1 - x0), y0 + 0.08 * (y1 - y0), x1 - 0.08 * (x1 - x0), y1 - 0.02 * (y1 - y0)), fill=color, outline=outline, width=line_width, scale=scale, radius=10)
        _rect(draw, (x0 + 0.24 * (x1 - x0), y0 + 0.44 * (y1 - y0), x1 - 0.18 * (x1 - x0), y1 - 0.16 * (y1 - y0)), fill=color, outline=outline, width=1, scale=scale, radius=5)
        _line(draw, [(x0 + 0.28 * (x1 - x0), y0 + 0.10 * (y1 - y0)), (x0 + 0.05 * (x1 - x0), y0 + 0.54 * (y1 - y0))], fill=outline, width=max(2, line_width), scale=scale)
        _line(draw, [(x1 - 0.28 * (x1 - x0), y0 + 0.10 * (y1 - y0)), (x1 - 0.04 * (x1 - x0), y0 + 0.54 * (y1 - y0))], fill=outline, width=max(2, line_width), scale=scale)
        return
    _rect(draw, (x0 + 0.08 * (x1 - x0), y0 + 0.18 * (y1 - y0), x1 - 0.04 * (x1 - x0), y1 - 0.04 * (y1 - y0)), fill=color, outline=outline, width=line_width, scale=scale, radius=6)
    _line(draw, [(x0 + 0.40 * (x1 - x0), y0 + 0.18 * (y1 - y0)), (x0 + 0.40 * (x1 - x0), y0 - 0.06 * (y1 - y0)), (x0 + 0.72 * (x1 - x0), y0 - 0.06 * (y1 - y0)), (x0 + 0.72 * (x1 - x0), y0 + 0.18 * (y1 - y0))], fill=outline, width=max(2, line_width), scale=scale)
    _line(draw, [(x0 + 0.20 * (x1 - x0), y1 - 0.20 * (y1 - y0)), (x1 - 0.16 * (x1 - x0), y1 - 0.20 * (y1 - y0))], fill=color, width=max(2, line_width), scale=scale)


def render_transit_terminal_scene(
    *,
    rng,
    person_specs: Sequence[TransitPersonSpec],
    luggage_specs: Sequence[TransitLuggageSpec] = (),
    canvas_width: int = 1280,
    canvas_height: int = 900,
    render_scale: int = 2,
    setting_weights: Mapping[str, float] | None = None,
    style_weights: Mapping[str, float] | None = None,
    show_service_points: bool = False,
) -> RenderedTransitTerminalScene:
    """Render one synthetic transit terminal scene from semantic entity specs."""

    width = int(canvas_width)
    height = int(canvas_height)
    scale = max(1, int(render_scale))
    if not person_specs:
        raise ValueError("transit terminal scene needs at least one person")
    setting_id = _choose_weighted(rng, setting_weights or {setting: 1.0 for setting in TRANSIT_SETTING_IDS}, TRANSIT_SETTING_IDS)
    style_id = _choose_weighted(rng, style_weights or {style: 1.0 for style in STYLE_IDS}, STYLE_IDS)
    layout = _sample_layout(rng, width=width, height=height)
    image = Image.new("RGB", (width * scale, height * scale), (226, 230, 226))
    draw = ImageDraw.Draw(image)
    decor: List[TransitDecor] = []
    decor.extend(_draw_terminal_shell(draw, rng=rng, setting_id=str(setting_id), layout=layout, width=width, height=height, scale=scale))
    areas: List[TransitArea] = []
    for area_id in TRANSIT_BOARDING_AREA_IDS:
        box = _area_bbox(layout, str(area_id))
        if box is None:
            continue
        area, area_decor = _draw_area(draw, rng=rng, setting_id=str(setting_id), area_id=str(area_id), area_box=box, scale=scale)
        areas.append(area)
        decor.extend(area_decor)
    concourse = tuple(float(v) for v in layout["concourse_bbox"])
    _rect(draw, concourse, fill=_jitter_rgb(rng, (202, 196, 184), 8), outline=(132, 126, 116), width=2, scale=scale, radius=16)
    decor.append(TransitDecor("decor_concourse", "concourse", tuple(round(float(v), 3) for v in concourse), {}))
    decor.extend(_draw_terminal_decor(draw, rng=rng, layout=layout, width=width, height=height, scale=scale, show_service_points=bool(show_service_points)))
    service_points = (
        _draw_service_points(draw, rng=rng, layout=layout, width=width, height=height, scale=scale)
        if bool(show_service_points)
        else tuple()
    )
    placed_luggage = _place_luggage(rng, specs=luggage_specs, layout=layout, width=width, height=height)
    luggage_items: List[TransitLuggageItem] = []
    for index, (spec, bbox) in enumerate(sorted(placed_luggage, key=lambda item: (float(item[1][3]), float(item[1][0])))):
        luggage_id = f"luggage_{index:02d}"
        color = _clothes_color(rng)
        luggage_items.append(
            TransitLuggageItem(
                luggage_id=str(luggage_id),
                area_id=str(spec.area_id),
                luggage_type=str(spec.luggage_type),
                bbox_xyxy=tuple(round(float(v), 3) for v in bbox),
                primary_color_rgb=tuple(int(v) for v in color),
                role=str(spec.role),
                attributes={**dict(spec.attributes), "area_id": str(spec.area_id), "luggage_type": str(spec.luggage_type)},
            )
        )
    placed = _place_persons(rng, specs=person_specs, layout=layout, width=width, height=height)
    placed_sorted = sorted(placed, key=lambda item: (float(item[1][3]), float(item[1][0])))
    persons: List[TransitPerson] = []
    for index, (spec, bbox, pose_id) in enumerate(placed_sorted):
        person_id = f"person_{index:02d}"
        primary = _clothes_color(rng)
        accent = _clothes_color(rng)
        skin = _skin_color(rng)
        gender_id = sample_person_gender(rng)
        accessory_decor = _draw_person(
            draw,
            bbox=bbox,
            pose_id=str(pose_id),
            primary=primary,
            accent=accent,
            skin=skin,
            gender_id=str(gender_id),
            style_id=str(style_id),
            scale=scale,
        )
        for decor_index, item in enumerate(accessory_decor):
            decor.append(
                TransitDecor(
                    f"{person_id}_luggage_{decor_index}",
                    str(item.decor_type),
                    tuple(round(float(v), 3) for v in item.bbox_xyxy),
                    {"supports_person_id": str(person_id), **dict(item.attributes)},
                )
            )
        persons.append(
            TransitPerson(
                person_id=person_id,
                area_id=str(spec.area_id),
                pose_id=str(pose_id),
                bbox_xyxy=tuple(round(float(v), 3) for v in bbox),
                primary_color_rgb=tuple(int(v) for v in primary),
                accent_color_rgb=tuple(int(v) for v in accent),
                skin_color_rgb=tuple(int(v) for v in skin),
                gender_id=str(gender_id),
                role=str(spec.role),
                attributes={**dict(spec.attributes), "area_id": str(spec.area_id), "pose_id": str(pose_id)},
            )
        )
    for item in luggage_items:
        _draw_luggage_item(
            draw,
            bbox=item.bbox_xyxy,
            luggage_type=str(item.luggage_type),
            color=tuple(int(v) for v in item.primary_color_rgb),
            style_id=str(style_id),
            scale=scale,
        )
    if scale != 1:
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    return RenderedTransitTerminalScene(
        image=image,
        setting_id=str(setting_id),
        areas=tuple(areas),
        service_points=tuple(service_points),
        persons=tuple(persons),
        luggage=tuple(luggage_items),
        decor=tuple(decor),
        canvas_width=width,
        canvas_height=height,
        render_scale=scale,
        style_id=str(style_id),
        layout=dict(layout),
    )


def transit_person_bbox_map(scene: RenderedTransitTerminalScene) -> Dict[str, List[float]]:
    """Return person bboxes keyed by person id."""

    return {str(person.person_id): [round(float(v), 3) for v in person.bbox_xyxy] for person in scene.persons}


def transit_luggage_bbox_map(scene: RenderedTransitTerminalScene) -> Dict[str, List[float]]:
    """Return loose luggage bboxes keyed by luggage id."""

    return {str(item.luggage_id): [round(float(v), 3) for v in item.bbox_xyxy] for item in scene.luggage}


def sort_transit_bboxes(bbox_map: Mapping[str, Sequence[float]], ids: Iterable[str]) -> List[List[float]]:
    """Return bboxes sorted top-to-bottom then left-to-right for stable evidence."""

    boxes = [list(float(v) for v in bbox_map[str(item_id)]) for item_id in ids]
    boxes.sort(key=lambda box: (round(float(box[1]), 3), round(float(box[0]), 3), round(float(box[3]), 3), round(float(box[2]), 3)))
    return [[round(float(v), 3) for v in box] for box in boxes]


def transit_scene_entities(scene: RenderedTransitTerminalScene) -> List[Dict[str, Any]]:
    """Return generic entity records for the scene trace."""

    entities: List[Dict[str, Any]] = []
    for area in scene.areas:
        object_record = make_object_record(
            object_id=str(area.area_id),
            object_type="boarding_area",
            bbox_xyxy=area.bbox_xyxy,
            semantic_attributes={
                "area_id": str(area.area_id),
                "display_name": str(area.display_name),
                "label": str(area.label),
                **dict(area.attributes),
            },
            source_entity_type="transit_boarding_area",
        ).as_dict()
        entities.append(
            {
                "entity_id": str(area.area_id),
                "entity_type": "transit_boarding_area",
                "display_name": str(area.display_name),
                "bbox": [round(float(v), 3) for v in area.bbox_xyxy],
                "sign_bbox": [round(float(v), 3) for v in area.sign_bbox_xyxy],
                "platform_bbox": [round(float(v), 3) for v in area.platform_bbox_xyxy],
                "attributes": _safe_json(area.attributes),
                "object_record": object_record,
            }
        )
    for person in scene.persons:
        object_record = make_object_record(
            object_id=str(person.person_id),
            object_type="person",
            bbox_xyxy=person.bbox_xyxy,
            semantic_attributes={
                "area_id": str(person.area_id),
                "pose_id": str(person.pose_id),
                **dict(person.attributes),
            },
            visual_attributes={
                "primary_color_rgb": [int(v) for v in person.primary_color_rgb],
                "accent_color_rgb": [int(v) for v in person.accent_color_rgb],
                "skin_color_rgb": [int(v) for v in person.skin_color_rgb],
                "gender_id": str(person.gender_id),
            },
            role=str(person.role),
            source_entity_type="transit_person",
        ).as_dict()
        entities.append(
            {
                "entity_id": str(person.person_id),
                "entity_type": "transit_person",
                "area_id": str(person.area_id),
                "pose_id": str(person.pose_id),
                "bbox": [round(float(v), 3) for v in person.bbox_xyxy],
                "role": str(person.role),
                "attributes": _safe_json(person.attributes),
                "object_record": object_record,
            }
        )
    for item in scene.luggage:
        object_record = make_object_record(
            object_id=str(item.luggage_id),
            object_type="luggage",
            bbox_xyxy=item.bbox_xyxy,
            semantic_attributes={
                "area_id": str(item.area_id),
                "luggage_type": str(item.luggage_type),
                **dict(item.attributes),
            },
            visual_attributes={"primary_color_rgb": [int(v) for v in item.primary_color_rgb]},
            role=str(item.role),
            source_entity_type="transit_luggage",
        ).as_dict()
        entities.append(
            {
                "entity_id": str(item.luggage_id),
                "entity_type": "transit_luggage",
                "area_id": str(item.area_id),
                "luggage_type": str(item.luggage_type),
                "bbox": [round(float(v), 3) for v in item.bbox_xyxy],
                "role": str(item.role),
                "attributes": _safe_json(item.attributes),
                "object_record": object_record,
            }
        )
    for point in scene.service_points:
        object_record = make_object_record(
            object_id=str(point.service_point_id),
            object_type="service_point",
            bbox_xyxy=point.bbox_xyxy,
            semantic_attributes={
                "service_point_id": str(point.service_point_id),
                "display_name": str(point.display_name),
                **dict(point.attributes),
            },
            source_entity_type="transit_service_point",
        ).as_dict()
        entities.append(
            {
                "entity_id": str(point.service_point_id),
                "entity_type": "transit_service_point",
                "display_name": str(point.display_name),
                "bbox": [round(float(v), 3) for v in point.bbox_xyxy],
                "sign_bbox": [round(float(v), 3) for v in point.sign_bbox_xyxy],
                "queue_bbox": [round(float(v), 3) for v in point.queue_bbox_xyxy],
                "attributes": _safe_json(point.attributes),
                "object_record": object_record,
            }
        )
    for item in scene.decor:
        object_record = make_object_record(
            object_id=str(item.decor_id),
            object_type="decor",
            bbox_xyxy=item.bbox_xyxy,
            semantic_attributes={"decor_type": str(item.decor_type), **dict(item.attributes)},
            source_entity_type="transit_decor",
        ).as_dict()
        entities.append(
            {
                "entity_id": str(item.decor_id),
                "entity_type": "transit_decor",
                "decor_type": str(item.decor_type),
                "bbox": [round(float(v), 3) for v in item.bbox_xyxy],
                "attributes": _safe_json(item.attributes),
                "object_record": object_record,
            }
        )
    return entities


def serialize_transit_scene(scene: RenderedTransitTerminalScene) -> Tuple[List[Dict[str, Any]], Dict[str, List[float]]]:
    """Serialize transit scene records and person bbox map."""

    area_records = [
        {
            "area_id": str(area.area_id),
            "display_name": str(area.display_name),
            "label": str(area.label),
            "bbox": [round(float(v), 3) for v in area.bbox_xyxy],
            "sign_bbox": [round(float(v), 3) for v in area.sign_bbox_xyxy],
            "platform_bbox": [round(float(v), 3) for v in area.platform_bbox_xyxy],
            "attributes": _safe_json(area.attributes),
        }
        for area in scene.areas
    ]
    person_records = [
        {
            "person_id": str(person.person_id),
            "area_id": str(person.area_id),
            "pose_id": str(person.pose_id),
            "bbox": [round(float(v), 3) for v in person.bbox_xyxy],
            "primary_color_rgb": [int(v) for v in person.primary_color_rgb],
            "accent_color_rgb": [int(v) for v in person.accent_color_rgb],
            "skin_color_rgb": [int(v) for v in person.skin_color_rgb],
            "gender_id": str(person.gender_id),
            "role": str(person.role),
            "attributes": _safe_json(person.attributes),
        }
        for person in scene.persons
    ]
    luggage_records = [
        {
            "luggage_id": str(item.luggage_id),
            "area_id": str(item.area_id),
            "luggage_type": str(item.luggage_type),
            "bbox": [round(float(v), 3) for v in item.bbox_xyxy],
            "primary_color_rgb": [int(v) for v in item.primary_color_rgb],
            "role": str(item.role),
            "attributes": _safe_json(item.attributes),
        }
        for item in scene.luggage
    ]
    service_point_records = [
        {
            "service_point_id": str(point.service_point_id),
            "display_name": str(point.display_name),
            "bbox": [round(float(v), 3) for v in point.bbox_xyxy],
            "sign_bbox": [round(float(v), 3) for v in point.sign_bbox_xyxy],
            "queue_bbox": [round(float(v), 3) for v in point.queue_bbox_xyxy],
            "attributes": _safe_json(point.attributes),
        }
        for point in scene.service_points
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
                "areas": area_records,
                "service_points": service_point_records,
                "persons": person_records,
                "luggage": luggage_records,
                "decor": decor_records,
            }
        ],
        transit_person_bbox_map(scene),
    )


__all__ = [
    "TRANSIT_BOARDING_AREA_IDS",
    "TRANSIT_BOARDING_AREA_LABELS",
    "TRANSIT_LUGGAGE_LABELS",
    "TRANSIT_LUGGAGE_TYPES",
    "TRANSIT_PERSON_POSES",
    "TRANSIT_SERVICE_POINT_IDS",
    "TRANSIT_SERVICE_POINT_LABELS",
    "TRANSIT_SETTING_IDS",
    "RenderedTransitTerminalScene",
    "TransitLuggageSpec",
    "TransitPersonSpec",
    "render_transit_terminal_scene",
    "serialize_transit_scene",
    "sort_transit_bboxes",
    "transit_area_display_name",
    "transit_luggage_bbox_map",
    "transit_luggage_display_name",
    "transit_person_bbox_map",
    "transit_scene_entities",
    "transit_service_point_display_name",
]
