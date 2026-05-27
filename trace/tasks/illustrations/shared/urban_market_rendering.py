"""Urban market illustration scene with semantic shop inventory metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from .render_geometry import scale_bbox as _scale_bbox, scale_points as _scale_points
from ...shared.text_rendering import fit_font_to_box, load_font
from .object_library import (
    BBox,
    RGB,
    STYLE_IDS,
    choose_object_colors,
    display_name_for_object_type,
    draw_illustration_object,
)
from .object_catalog import (
    label_map_for_tag,
    market_item_allowed_shops,
    market_shop_inventory_types,
    public_name_map_for_tag,
    variant_ids_with_tag,
)
from .object_registry import make_object_record
from .person_rendering import sample_person_gender


MARKET_SETTING_IDS: Tuple[str, ...] = variant_ids_with_tag("market_setting")
MARKET_SHOP_TYPES: Tuple[str, ...] = variant_ids_with_tag("market_shop")
MARKET_SHOP_LABELS: Dict[str, str] = label_map_for_tag("market_shop")
MARKET_SHOP_DISPLAY_NAMES: Dict[str, str] = public_name_map_for_tag("market_shop")
MARKET_SHOP_INVENTORY_TYPES: Dict[str, Tuple[str, ...]] = market_shop_inventory_types()
MARKET_ITEM_DISPLAY_NAMES: Dict[str, str] = public_name_map_for_tag("market_item")
MARKET_QUERY_ITEM_TYPES: Tuple[str, ...] = tuple(
    sorted({item_type for inventory in MARKET_SHOP_INVENTORY_TYPES.values() for item_type in inventory})
)
MARKET_ITEM_ALLOWED_SHOPS: Dict[str, Tuple[str, ...]] = market_item_allowed_shops()


@dataclass(frozen=True)
class MarketShopSpec:
    """Requested semantic inventory for one rendered shop or stall."""

    shop_type: str
    item_types: Tuple[str, ...]
    role: str = "distractor"
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketCustomerSpec:
    """Requested customer figure placed near a market shop or stall type."""

    shop_type: str
    role: str = "distractor"
    object_type: str = "pedestrian_with_bag"
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketItem:
    """One rendered shop inventory item."""

    item_id: str
    item_type: str
    display_name: str
    bbox_xyxy: BBox
    shop_id: str
    slot_index: int
    color_rgb: RGB
    accent_color_rgb: RGB
    attributes: Mapping[str, Any]


@dataclass(frozen=True)
class MarketShop:
    """One rendered market shop or stall."""

    shop_id: str
    shop_type: str
    display_name: str
    bbox_xyxy: BBox
    sign_bbox_xyxy: BBox
    awning_bbox_xyxy: BBox
    facade_bbox_xyxy: BBox
    display_bbox_xyxy: BBox
    counter_bbox_xyxy: BBox
    item_ids: Tuple[str, ...]
    item_types: Tuple[str, ...]
    role: str
    attributes: Mapping[str, Any]


@dataclass(frozen=True)
class MarketDecor:
    """Non-query visual decor drawn into the market scene."""

    decor_id: str
    decor_type: str
    bbox_xyxy: BBox
    attributes: Mapping[str, Any]


@dataclass(frozen=True)
class RenderedUrbanMarketScene:
    """Rendered urban market scene plus trace-ready metadata."""

    image: Image.Image
    setting_id: str
    shops: Tuple[MarketShop, ...]
    items: Tuple[MarketItem, ...]
    decor: Tuple[MarketDecor, ...]
    canvas_width: int
    canvas_height: int
    render_scale: int
    style_id: str
    layout: Mapping[str, Any]


def market_item_display_name(item_type: str) -> str:
    """Return a prompt-facing market item name."""

    key = str(item_type)
    return MARKET_ITEM_DISPLAY_NAMES.get(key, display_name_for_object_type(key))


def market_shop_display_name(shop_type: str) -> str:
    """Return a prompt-facing market shop name."""

    return MARKET_SHOP_DISPLAY_NAMES.get(str(shop_type), str(shop_type).replace("_", " "))




def _jitter_rgb(rng, color: RGB, amount: int = 16) -> RGB:
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


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float):
        return round(float(value), 3)
    return value


def _coerce_rgb(value: Any, fallback: RGB) -> RGB:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 3:
        try:
            return tuple(max(0, min(255, int(round(float(channel))))) for channel in value)  # type: ignore[return-value]
        except Exception:
            return fallback
    return fallback


def _readable_text_color(fill: RGB) -> RGB:
    luminance = 0.299 * float(fill[0]) + 0.587 * float(fill[1]) + 0.114 * float(fill[2])
    return (245, 244, 236) if luminance < 132.0 else (36, 42, 50)


def _draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    bbox: Sequence[float],
    *,
    scale: int,
    radius: float,
    fill: RGB,
    outline: RGB | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(
        _scale_bbox(bbox, scale),
        radius=max(1, int(round(float(radius) * int(scale)))),
        fill=tuple(fill),
        outline=tuple(outline) if outline else None,
        width=max(1, int(width) * int(scale)) if outline else 1,
    )


def _draw_shadow(draw: ImageDraw.ImageDraw, bbox: Sequence[float], *, scale: int, offset: float = 7.0, alpha_rgb: RGB = (196, 190, 178)) -> None:
    x0, y0, x1, y1 = [float(v) for v in bbox]
    draw.ellipse(_scale_bbox((x0 + offset, y1 - 13.0, x1 + offset, y1 + 9.0), scale), fill=tuple(alpha_rgb))


def _draw_fit_text(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    bbox: Sequence[float],
    scale: int,
    fill: RGB = (37, 42, 50),
    bold: bool = True,
    min_size_px: int = 9,
    max_size_px: int = 32,
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
        tb = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(scale) if stroke_fill else 0))
        tw = float(tb[2] - tb[0])
        th = float(tb[3] - tb[1])
    except Exception:
        tw, th = draw.textsize(str(text), font=font)
    tx = float(x0 + (x1 - x0 - tw) * 0.5)
    ty = float(y0 + (y1 - y0 - th) * 0.5)
    draw.text(
        (int(round(tx)), int(round(ty))),
        str(text),
        font=font,
        fill=tuple(fill),
        stroke_width=max(0, int(scale) if stroke_fill else 0),
        stroke_fill=tuple(stroke_fill) if stroke_fill else None,
    )


def _draw_background(
    draw: ImageDraw.ImageDraw,
    *,
    rng,
    setting_id: str,
    width: int,
    height: int,
    scale: int,
) -> Dict[str, Any]:
    palettes = {
        "street_market": ((214, 231, 239), (219, 202, 172), (191, 169, 125)),
        "covered_market": ((229, 222, 209), (216, 193, 157), (190, 162, 116)),
        "plaza_market": ((218, 234, 232), (221, 204, 176), (199, 176, 132)),
    }
    sky_base, ground_base, pavement_base = palettes.get(str(setting_id), palettes["street_market"])
    sky = _jitter_rgb(rng, sky_base, amount=9)
    ground = _jitter_rgb(rng, ground_base, amount=12)
    pavement = _jitter_rgb(rng, pavement_base, amount=9)
    s = int(scale)
    horizon_y = int(round(float(rng.uniform(312.0, 350.0))))
    draw.rectangle((0, 0, int(width) * s, int(height) * s), fill=tuple(sky))
    draw.rectangle((0, horizon_y * s, int(width) * s, int(height) * s), fill=tuple(ground))
    draw.polygon(
        _scale_points(
            (
                (0.0, horizon_y + float(rng.uniform(10.0, 22.0))),
                (float(width), horizon_y + float(rng.uniform(4.0, 18.0))),
                (float(width), float(height)),
                (0.0, float(height)),
            ),
            s,
        ),
        fill=tuple(pavement),
    )
    vanishing_x = float(rng.uniform(500.0, 780.0))
    for step in range(1, 8):
        y = horizon_y + 24.0 + (float(step) ** 1.22) * 36.0
        color = _jitter_rgb(rng, (174, 153, 113), amount=9)
        draw.line(
            _scale_points(((0.0, y), (float(width), y + float(rng.uniform(-7.0, 7.0)))), s),
            fill=tuple(color),
            width=max(1, s),
        )
    for _ in range(90):
        px = float(rng.uniform(0.0, float(width)))
        py = float(rng.uniform(float(horizon_y) + 12.0, float(height)))
        dot = float(rng.uniform(1.0, 2.8))
        color = _jitter_rgb(rng, (154, 128, 88), amount=18)
        draw.ellipse(_scale_bbox((px, py, px + dot, py + dot), s), fill=tuple(color))
    if str(setting_id) == "covered_market":
        canopy_color = _jitter_rgb(rng, (190, 111, 91), amount=13)
        draw.polygon(
            _scale_points(((0.0, 0.0), (float(width), 0.0), (float(width) - 120.0, 112.0), (120.0, 112.0)), s),
            fill=tuple(canopy_color),
        )
        for x in range(0, int(width) + 1, 84):
            stripe = _jitter_rgb(rng, (245, 228, 186), amount=8)
            draw.polygon(
                _scale_points(((x, 0.0), (x + 42.0, 0.0), (x + 30.0, 112.0), (x - 12.0, 112.0)), s),
                fill=tuple(stripe),
            )
    else:
        for i in range(int(rng.randint(4, 7))):
            bx0 = float(i) * (float(width) / 5.2) + float(rng.uniform(-38.0, 28.0))
            bw = float(rng.uniform(88.0, 146.0))
            bh = float(rng.uniform(88.0, 150.0))
            by1 = float(horizon_y) + float(rng.uniform(0.0, 18.0))
            building = (bx0, by1 - bh, bx0 + bw, by1)
            fill = _jitter_rgb(rng, rng.choice(((190, 184, 172), (176, 189, 195), (204, 180, 164), (181, 178, 190))), amount=12)
            draw.rectangle(_scale_bbox(building, s), fill=tuple(fill), outline=(123, 128, 132), width=max(1, s))
            wx = bx0 + 18.0
            while wx < bx0 + bw - 18.0:
                wy = by1 - bh + 20.0
                while wy < by1 - 22.0:
                    draw.rectangle(_scale_bbox((wx, wy, wx + 15.0, wy + 18.0), s), fill=(231, 236, 229), outline=(118, 125, 130), width=max(1, s))
                    wy += 32.0
                wx += 30.0
    return {
        "horizon_y": float(horizon_y),
        "vanishing_x": round(float(vanishing_x), 3),
        "setting_id": str(setting_id),
    }


def _split_lane_counts(rng, shop_count: int, *, allow_unbalanced: bool = True) -> Tuple[int, int]:
    half = int(shop_count) // 2
    if int(shop_count) % 2 == 0:
        if allow_unbalanced and int(shop_count) >= 8 and bool(rng.choice((True, False))):
            first = half - 1
        else:
            first = half
    else:
        first = half + int(rng.choice((0, 1)))
    first = max(2, min(int(shop_count) - 2, int(first)))
    return int(first), int(shop_count) - int(first)


def _split_counts_across_lanes(rng, *, total_count: int, lane_count: int, min_per_lane: int = 3) -> Tuple[int, ...]:
    if int(lane_count) * int(min_per_lane) > int(total_count):
        raise ValueError("lane_count/min_per_lane cannot fit total_count")
    counts = [int(min_per_lane) for _ in range(int(lane_count))]
    remaining = int(total_count) - sum(counts)
    while remaining > 0:
        counts[int(rng.randrange(0, int(lane_count)))] += 1
        remaining -= 1
    if bool(rng.choice((True, False))):
        rng.shuffle(counts)
    return tuple(int(value) for value in counts)


def _lane_widths(rng, *, count: int, start: float, end: float, gap: float) -> List[Tuple[float, float]]:
    available = max(1.0, float(end) - float(start) - float(gap) * (int(count) - 1))
    weights = [float(rng.uniform(0.88, 1.14)) for _ in range(int(count))]
    widths = [available * weight / sum(weights) for weight in weights]
    spans: List[Tuple[float, float]] = []
    x = float(start)
    for lane_width in widths:
        spans.append((x, x + float(lane_width)))
        x += float(lane_width) + float(gap)
    return spans


def _lane_heights(rng, *, count: int, start: float, end: float, gap: float) -> List[Tuple[float, float]]:
    available = max(1.0, float(end) - float(start) - float(gap) * (int(count) - 1))
    weights = [float(rng.uniform(0.90, 1.12)) for _ in range(int(count))]
    heights = [available * weight / sum(weights) for weight in weights]
    spans: List[Tuple[float, float]] = []
    y = float(start)
    for lane_height in heights:
        spans.append((y, y + float(lane_height)))
        y += float(lane_height) + float(gap)
    return spans


def _dense_shop_layout(rng, *, shop_count: int, width: int, height: int) -> Tuple[Tuple[BBox, ...], Dict[str, Any]]:
    axis = str(rng.choice(("rows", "columns")))
    if axis == "columns" and int(shop_count) >= 16:
        lane_count_support = (3,)
    else:
        lane_count_support = (2, 3)
    lane_count = int(rng.choice(tuple(lane_count_support)))
    lane_counts = _split_counts_across_lanes(rng, total_count=int(shop_count), lane_count=int(lane_count), min_per_lane=3)
    shop_gap = float(rng.uniform(10.0, 14.0))
    road_gap = float(rng.uniform(56.0, 74.0))
    boxes: List[BBox] = []
    road_bboxes: List[List[float]] = []
    decor_zones: List[List[float]] = []

    if axis == "columns":
        left = float(rng.uniform(30.0, 42.0))
        right = float(width) - float(rng.uniform(30.0, 42.0))
        top = float(rng.uniform(58.0, 76.0))
        bottom = float(height) - float(rng.uniform(24.0, 34.0))
        lane_spans = _lane_widths(rng, count=int(lane_count), start=left, end=right, gap=road_gap)
        for lane_index, (lane_x0, lane_x1) in enumerate(lane_spans):
            for y0, y1 in _lane_heights(rng, count=int(lane_counts[lane_index]), start=top, end=bottom, gap=shop_gap):
                jitter = float(rng.uniform(-2.0, 2.0))
                boxes.append(
                    (
                        round(float(lane_x0 + jitter), 3),
                        round(float(max(4.0, y0)), 3),
                        round(float(lane_x1 + jitter), 3),
                        round(float(min(float(height) - 8.0, y1)), 3),
                    )
                )
            if lane_index < int(lane_count) - 1:
                road_x0 = lane_x1 + float(rng.uniform(2.0, 4.0))
                road_x1 = lane_spans[lane_index + 1][0] - float(rng.uniform(2.0, 4.0))
                road_bboxes.append([round(float(road_x0), 3), 0.0, round(float(road_x1), 3), float(height)])
                decor_zones.append([round(float(road_x0 + 7.0), 3), round(float(top), 3), round(float(road_x1 - 7.0), 3), round(float(bottom), 3)])
        lane_counts_map = {f"column_{index + 1}": int(count) for index, count in enumerate(lane_counts)}
        lane_bounds = [[round(float(x0), 3), round(float(x1), 3)] for x0, x1 in lane_spans]
    else:
        left = float(rng.uniform(30.0, 42.0))
        right = float(width) - float(rng.uniform(30.0, 42.0))
        top = float(rng.uniform(58.0, 76.0))
        bottom = float(height) - float(rng.uniform(24.0, 34.0))
        lane_spans = _lane_heights(rng, count=int(lane_count), start=top, end=bottom, gap=road_gap)
        for lane_index, (lane_y0, lane_y1) in enumerate(lane_spans):
            for x0, x1 in _lane_widths(rng, count=int(lane_counts[lane_index]), start=left, end=right, gap=shop_gap):
                jitter = float(rng.uniform(-2.0, 2.0))
                boxes.append(
                    (
                        round(float(x0), 3),
                        round(float(max(4.0, lane_y0 + jitter)), 3),
                        round(float(x1), 3),
                        round(float(min(float(height) - 8.0, lane_y1 + jitter)), 3),
                    )
                )
            if lane_index < int(lane_count) - 1:
                road_y0 = lane_y1 + float(rng.uniform(2.0, 4.0))
                road_y1 = lane_spans[lane_index + 1][0] - float(rng.uniform(2.0, 4.0))
                road_bboxes.append([0.0, round(float(road_y0), 3), float(width), round(float(road_y1), 3)])
                decor_zones.append([0.0, round(float(road_y0 + 5.0), 3), float(width), round(float(road_y1 - 5.0), 3)])
        lane_counts_map = {f"row_{index + 1}": int(count) for index, count in enumerate(lane_counts)}
        lane_bounds = [[round(float(y0), 3), round(float(y1), 3)] for y0, y1 in lane_spans]

    return tuple(boxes), {
        "layout_id": f"sign_dense_{axis}",
        "layout_mode": "sign_dense",
        "lane_axis": str(axis),
        "lane_count": int(lane_count),
        "lane_counts": lane_counts_map,
        "lane_bounds": lane_bounds,
        "gap_px": round(float(shop_gap), 3),
        "road_gap_px": round(float(road_gap), 3),
        "road_bbox": road_bboxes[0] if road_bboxes else None,
        "road_bboxes": road_bboxes,
        "decor_zones": decor_zones,
    }


def _shop_layout(rng, *, shop_count: int, width: int, height: int, layout_mode: str = "inventory") -> Tuple[Tuple[BBox, ...], Dict[str, Any]]:
    if str(layout_mode) == "sign_dense":
        return _dense_shop_layout(rng, shop_count=int(shop_count), width=int(width), height=int(height))
    if str(layout_mode) == "customer_plaza":
        top_count, bottom_count = _split_lane_counts(rng, int(shop_count), allow_unbalanced=True)
        shop_gap = float(rng.uniform(14.0, 20.0))
        left = float(rng.uniform(34.0, 50.0))
        right = float(width) - float(rng.uniform(34.0, 50.0))
        top_y0 = float(rng.uniform(108.0, 132.0))
        top_h = float(rng.uniform(244.0, 286.0))
        path_y0 = top_y0 + top_h + float(rng.uniform(20.0, 30.0))
        path_h = float(rng.uniform(166.0, 212.0))
        bottom_y0 = path_y0 + path_h + float(rng.uniform(20.0, 32.0))
        bottom_h = min(float(rng.uniform(244.0, 294.0)), float(height) - bottom_y0 - float(rng.uniform(42.0, 58.0)))
        bottom_h = max(220.0, bottom_h)
        row_specs = (
            ("top", top_count, top_y0, top_y0 + top_h),
            ("bottom", bottom_count, bottom_y0, min(float(height) - 38.0, bottom_y0 + bottom_h)),
        )
        boxes: List[BBox] = []
        for _lane_id, count, y0, y1 in row_specs:
            for x0, x1 in _lane_widths(rng, count=int(count), start=left, end=right, gap=shop_gap):
                jitter = float(rng.uniform(-5.0, 5.0))
                boxes.append((round(float(x0), 3), round(float(y0 + jitter), 3), round(float(x1), 3), round(float(y1 + jitter), 3)))
        path_bbox = [0.0, round(float(path_y0), 3), float(width), round(float(path_y0 + path_h), 3)]
        return tuple(boxes), {
            "layout_id": "customer_open_stall_rows",
            "layout_mode": "customer_plaza",
            "lane_counts": {"top": int(top_count), "bottom": int(bottom_count)},
            "gap_px": round(float(shop_gap), 3),
            "path_style": "dirt_market_path",
            "road_bbox": path_bbox,
            "decor_zones": [[0.0, round(float(path_y0 + 8.0), 3), float(width), round(float(path_y0 + path_h - 8.0), 3)]],
            "top_lane_y": [round(float(top_y0), 3), round(float(top_y0 + top_h), 3)],
            "bottom_lane_y": [round(float(bottom_y0), 3), round(float(min(float(height) - 38.0, bottom_y0 + bottom_h)), 3)],
        }

    layout_choices = ["two_horizontal_lanes"]
    if int(shop_count) <= 8:
        layout_choices.append("two_vertical_lanes")
    layout_id = str(rng.choice(tuple(layout_choices)))
    boxes: List[BBox] = []

    if layout_id == "two_vertical_lanes":
        left_count, right_count = _split_lane_counts(rng, int(shop_count), allow_unbalanced=False)
        road_half_width = float(rng.uniform(108.0, 132.0))
        road_center = float(width) * float(rng.uniform(0.49, 0.51))
        road_x0 = road_center - road_half_width
        road_x1 = road_center + road_half_width
        top = float(rng.uniform(132.0, 160.0))
        bottom = float(height) - float(rng.uniform(62.0, 82.0))
        gap = float(rng.uniform(12.0, 18.0))
        left_x0 = float(rng.uniform(42.0, 58.0))
        left_x1 = road_x0 - float(rng.uniform(38.0, 54.0))
        right_x0 = road_x1 + float(rng.uniform(38.0, 54.0))
        right_x1 = float(width) - float(rng.uniform(42.0, 58.0))
        for lane_id, count, x0, x1 in (
            ("left", left_count, left_x0, left_x1),
            ("right", right_count, right_x0, right_x1),
        ):
            for y0, y1 in _lane_heights(rng, count=int(count), start=top, end=bottom, gap=gap):
                jitter = float(rng.uniform(-7.0, 7.0))
                boxes.append((round(float(x0), 3), round(float(y0 + jitter), 3), round(float(x1), 3), round(float(y1 + jitter), 3)))
        return tuple(boxes), {
            "layout_id": layout_id,
            "layout_mode": "inventory",
            "lane_counts": {"left": int(left_count), "right": int(right_count)},
            "gap_px": round(float(gap), 3),
            "road_bbox": [round(float(road_x0), 3), 0.0, round(float(road_x1), 3), float(height)],
            "decor_zones": [[round(float(road_x0 + 12.0), 3), round(float(top + 16.0), 3), round(float(road_x1 - 12.0), 3), round(float(bottom - 12.0), 3)]],
        }

    top_count, bottom_count = _split_lane_counts(rng, int(shop_count), allow_unbalanced=True)
    gap = float(rng.uniform(12.0, 18.0))
    left = float(rng.uniform(34.0, 54.0))
    right = float(width) - float(rng.uniform(34.0, 54.0))
    top_y0 = float(rng.uniform(126.0, 154.0))
    top_h = float(rng.uniform(276.0, 322.0))
    alley_y0 = top_y0 + top_h + float(rng.uniform(30.0, 44.0))
    alley_h = float(rng.uniform(82.0, 116.0))
    bottom_y0 = alley_y0 + alley_h + float(rng.uniform(22.0, 38.0))
    bottom_h = min(float(rng.uniform(274.0, 318.0)), float(height) - bottom_y0 - float(rng.uniform(54.0, 72.0)))
    bottom_h = max(238.0, bottom_h)
    row_specs = (
        ("top", top_count, top_y0, top_y0 + top_h),
        ("bottom", bottom_count, bottom_y0, min(float(height) - 44.0, bottom_y0 + bottom_h)),
    )
    for lane_id, count, y0, y1 in row_specs:
        for x0, x1 in _lane_widths(rng, count=int(count), start=left, end=right, gap=gap):
            jitter = float(rng.uniform(-8.0, 8.0))
            boxes.append((round(float(x0), 3), round(float(y0 + jitter), 3), round(float(x1), 3), round(float(y1 + jitter), 3)))
    return tuple(boxes), {
        "layout_id": layout_id,
        "layout_mode": "inventory",
        "lane_counts": {"top": int(top_count), "bottom": int(bottom_count)},
        "gap_px": round(float(gap), 3),
        "road_bbox": [0.0, round(float(alley_y0), 3), float(width), round(float(alley_y0 + alley_h), 3)],
        "decor_zones": [[0.0, round(float(alley_y0 + 7.0), 3), float(width), round(float(alley_y0 + alley_h - 7.0), 3)]],
        "top_lane_y": [round(float(top_y0), 3), round(float(top_y0 + top_h), 3)],
        "bottom_lane_y": [round(float(bottom_y0), 3), round(float(min(float(height) - 44.0, bottom_y0 + bottom_h)), 3)],
    }


def _draw_market_paths(draw: ImageDraw.ImageDraw, *, rng, layout: Mapping[str, Any], width: int, height: int, scale: int) -> None:
    road_boxes: List[BBox] = []
    raw_road_bboxes = layout.get("road_bboxes")
    if isinstance(raw_road_bboxes, Sequence) and not isinstance(raw_road_bboxes, (str, bytes)):
        for road_bbox in raw_road_bboxes:
            if isinstance(road_bbox, Sequence) and not isinstance(road_bbox, (str, bytes)) and len(road_bbox) == 4:
                road_boxes.append(tuple(float(v) for v in road_bbox))  # type: ignore[arg-type]
    if not road_boxes:
        road_bbox = layout.get("road_bbox")
        if isinstance(road_bbox, Sequence) and not isinstance(road_bbox, (str, bytes)) and len(road_bbox) == 4:
            road_boxes.append(tuple(float(v) for v in road_bbox))  # type: ignore[arg-type]
    if not road_boxes:
        return
    s = int(scale)
    for road_box in road_boxes:
        x0, y0, x1, y1 = [float(v) for v in road_box]
        fill = _jitter_rgb(rng, (188, 158, 103), amount=13)
        edge = _jitter_rgb(rng, (129, 102, 66), amount=10)
        is_vertical = (x1 - x0) < (y1 - y0)
        if is_vertical:
            left_edge = []
            right_edge = []
            step = max(42.0, (y1 - y0) / 10.0)
            y = y0
            while y <= y1 + 1.0:
                left_edge.append((x0 + float(rng.uniform(-4.0, 4.0)), min(y1, y)))
                right_edge.append((x1 + float(rng.uniform(-4.0, 4.0)), min(y1, y)))
                y += step
            polygon = [*left_edge, *reversed(right_edge)]
        else:
            top_edge = []
            bottom_edge = []
            step = max(50.0, (x1 - x0) / 14.0)
            x = x0
            while x <= x1 + 1.0:
                top_edge.append((min(x1, x), y0 + float(rng.uniform(-4.0, 4.0))))
                bottom_edge.append((min(x1, x), y1 + float(rng.uniform(-4.0, 4.0))))
                x += step
            polygon = [*top_edge, *reversed(bottom_edge)]
        draw.polygon(_scale_points(polygon, s), fill=tuple(fill))
        if is_vertical:
            draw.line(_scale_points(left_edge, s), fill=tuple(edge), width=max(1, s))
            draw.line(_scale_points(right_edge, s), fill=tuple(edge), width=max(1, s))
        else:
            draw.line(_scale_points(top_edge, s), fill=tuple(edge), width=max(1, s))
            draw.line(_scale_points(bottom_edge, s), fill=tuple(edge), width=max(1, s))
        pebble_count = max(10, min(85, int(((x1 - x0) * (y1 - y0)) / 2900.0)))
        for _idx in range(pebble_count):
            px = float(rng.uniform(x0 + 6.0, max(x0 + 7.0, x1 - 6.0)))
            py = float(rng.uniform(y0 + 6.0, max(y0 + 7.0, y1 - 6.0)))
            dot = float(rng.uniform(1.2, 3.5))
            color = _jitter_rgb(rng, rng.choice(((137, 109, 72), (211, 186, 137), (156, 126, 83))), amount=12)
            if bool(rng.choice((True, False))):
                draw.ellipse(_scale_bbox((px, py, px + dot, py + dot), s), fill=tuple(color))
            else:
                draw.line(_scale_points(((px, py), (px + dot * float(rng.uniform(1.2, 2.4)), py + float(rng.uniform(-0.8, 0.8)))), s), fill=tuple(color), width=max(1, s))


def _shop_palette(rng, shop_type: str) -> Tuple[RGB, RGB, RGB, RGB]:
    facade_base = {
        "fruit": (221, 188, 111),
        "bakery": (218, 170, 119),
        "flowers": (197, 161, 191),
        "books": (133, 166, 194),
        "coffee": (173, 139, 108),
        "grocery": (150, 186, 133),
        "fish": (126, 177, 190),
        "clothes": (184, 150, 193),
        "toys": (217, 151, 100),
        "hardware": (162, 165, 174),
        "gift": (199, 142, 152),
    }.get(str(shop_type), (196, 170, 130))
    awning_base = {
        "fruit": (202, 77, 69),
        "bakery": (147, 86, 65),
        "flowers": (152, 78, 138),
        "books": (64, 106, 153),
        "coffee": (96, 70, 58),
        "grocery": (72, 142, 93),
        "fish": (52, 122, 153),
        "clothes": (131, 87, 164),
        "toys": (203, 105, 57),
        "hardware": (89, 98, 110),
        "gift": (181, 82, 102),
    }.get(str(shop_type), (138, 90, 78))
    facade = _jitter_rgb(rng, facade_base, amount=15)
    awning = _jitter_rgb(rng, awning_base, amount=12)
    sign = _jitter_rgb(rng, (246, 238, 208), amount=8)
    trim = _jitter_rgb(rng, (78, 78, 75), amount=8)
    return facade, awning, sign, trim


def _draw_awning(draw: ImageDraw.ImageDraw, *, rng, bbox: BBox, color: RGB, trim: RGB, scale: int) -> None:
    x0, y0, x1, y1 = [float(v) for v in bbox]
    s = int(scale)
    stripe_count = max(3, min(6, int(round((x1 - x0) / 38.0))))
    stripe_w = (x1 - x0) / float(stripe_count)
    draw.rectangle(_scale_bbox((x0, y0, x1, y1), s), fill=tuple(color), outline=tuple(trim), width=max(1, 2 * s))
    light = _jitter_rgb(rng, (246, 226, 184), amount=10)
    for idx in range(stripe_count):
        if idx % 2 == 1:
            sx0 = x0 + idx * stripe_w
            draw.rectangle(_scale_bbox((sx0, y0, sx0 + stripe_w, y1), s), fill=tuple(light))
    scallop_y = y1
    radius = max(8.0, stripe_w * 0.34)
    for idx in range(stripe_count):
        cx0 = x0 + idx * stripe_w
        draw.pieslice(_scale_bbox((cx0, scallop_y - radius, cx0 + stripe_w, scallop_y + radius), s), 0, 180, fill=tuple(color if idx % 2 == 0 else light), outline=tuple(trim), width=max(1, s))


def _item_colors(rng, item_type: str) -> Tuple[RGB, RGB]:
    palette = {
        "apple": ((205, 66, 66), (84, 143, 82)),
        "orange": ((230, 139, 54), (89, 134, 71)),
        "pear": ((198, 184, 79), (88, 137, 78)),
        "grapes": ((126, 88, 168), (88, 137, 78)),
        "banana": ((235, 198, 65), (146, 119, 55)),
        "bread": ((205, 151, 83), (143, 91, 52)),
        "cake": ((231, 160, 182), (96, 72, 64)),
        "pastry": ((219, 166, 90), (153, 98, 55)),
        "muffin": ((178, 112, 73), (238, 201, 126)),
        "flower": ((207, 91, 139), (82, 146, 88)),
        "bouquet": ((206, 89, 135), (79, 142, 87)),
        "book": ((78, 118, 179), (238, 231, 195)),
        "magazine": ((203, 83, 93), (244, 233, 197)),
        "newspaper": ((229, 229, 215), (84, 89, 92)),
        "fish": ((80, 151, 188), (240, 198, 92)),
        "shrimp": ((230, 123, 96), (252, 218, 180)),
        "shirt": ((92, 136, 194), (245, 241, 210)),
        "hat": ((194, 113, 80), (82, 79, 86)),
        "bag": ((184, 130, 77), (73, 70, 64)),
        "scarf": ((188, 78, 103), (248, 220, 142)),
        "ball": ((229, 88, 78), (248, 230, 94)),
        "toy_car": ((70, 131, 190), (38, 42, 48)),
        "kite": ((235, 170, 66), (91, 126, 188)),
        "hammer": ((129, 103, 77), (112, 116, 122)),
        "wrench": ((135, 143, 151), (70, 78, 86)),
    }.get(str(item_type), ((198, 110, 90), (84, 126, 156)))
    return _jitter_rgb(rng, palette[0], amount=12), _jitter_rgb(rng, palette[1], amount=10)


def _draw_market_item(draw: ImageDraw.ImageDraw, *, rng, item_type: str, bbox: BBox, scale: int, style_id: str) -> Tuple[RGB, RGB]:
    primary, accent = _item_colors(rng, str(item_type))
    x0, y0, x1, y1 = [float(v) for v in bbox]
    w = max(1.0, x1 - x0)
    h = max(1.0, y1 - y0)
    s = int(scale)
    outline = (43, 48, 55)
    if str(style_id) == "soft_shadow":
        _draw_shadow(draw, (x0, y0, x1, y1), scale=s, offset=2.8, alpha_rgb=(177, 166, 149))

    def ellipse(box: Sequence[float], fill: RGB, outline_rgb: RGB | None = outline, width: int = 1) -> None:
        draw.ellipse(_scale_bbox(box, s), fill=tuple(fill), outline=tuple(outline_rgb) if outline_rgb else None, width=max(1, width * s))

    def rect(box: Sequence[float], fill: RGB, outline_rgb: RGB | None = outline, width: int = 1) -> None:
        draw.rectangle(_scale_bbox(box, s), fill=tuple(fill), outline=tuple(outline_rgb) if outline_rgb else None, width=max(1, width * s))

    def rounded(box: Sequence[float], fill: RGB, radius: float = 5.0, outline_rgb: RGB | None = outline, width: int = 1) -> None:
        _draw_rounded_rect(draw, box, scale=s, radius=radius, fill=fill, outline=outline_rgb, width=width)

    def line(points: Sequence[Tuple[float, float]], fill: RGB = outline, width: int = 2) -> None:
        draw.line(_scale_points(points, s), fill=tuple(fill), width=max(1, width * s))

    item = str(item_type)
    if item in {"apple", "orange", "pear", "egg", "ball"}:
        ellipse((x0 + 0.16 * w, y0 + 0.12 * h, x1 - 0.14 * w, y1 - 0.08 * h), primary)
        if item == "apple":
            line(((x0 + 0.54 * w, y0 + 0.17 * h), (x0 + 0.59 * w, y0 + 0.02 * h)), fill=(78, 88, 61), width=2)
            ellipse((x0 + 0.58 * w, y0 + 0.02 * h, x0 + 0.82 * w, y0 + 0.24 * h), accent, outline_rgb=None)
        if item == "ball":
            line(((x0 + 0.22 * w, y0 + 0.5 * h), (x1 - 0.2 * w, y0 + 0.5 * h)), width=1)
            line(((x0 + 0.5 * w, y0 + 0.14 * h), (x0 + 0.5 * w, y1 - 0.12 * h)), width=1)
    elif item in {"grapes", "bouquet"}:
        for ox, oy in ((0.32, 0.22), (0.50, 0.21), (0.66, 0.31), (0.40, 0.43), (0.57, 0.51), (0.48, 0.66)):
            ellipse((x0 + (ox - 0.13) * w, y0 + (oy - 0.13) * h, x0 + (ox + 0.13) * w, y0 + (oy + 0.13) * h), primary)
        if item == "bouquet":
            line(((x0 + 0.36 * w, y1 - 0.1 * h), (x0 + 0.5 * w, y0 + 0.55 * h), (x0 + 0.64 * w, y1 - 0.1 * h)), fill=accent, width=2)
    elif item == "banana":
        draw.arc(_scale_bbox((x0 + 0.1 * w, y0 + 0.14 * h, x1 + 0.1 * w, y1 + 0.16 * h), s), 30, 158, fill=tuple(primary), width=max(4, 5 * s))
        draw.arc(_scale_bbox((x0 + 0.15 * w, y0 + 0.05 * h, x1, y1 + 0.03 * h), s), 34, 158, fill=tuple(accent), width=max(1, s))
    elif item in {"bread", "pastry", "muffin"}:
        rounded((x0 + 0.08 * w, y0 + 0.28 * h, x1 - 0.08 * w, y1 - 0.06 * h), primary, radius=9.0)
        for t in (0.32, 0.5, 0.68):
            line(((x0 + t * w, y0 + 0.36 * h), (x0 + (t + 0.06) * w, y0 + 0.58 * h)), fill=accent, width=1)
    elif item == "cake":
        rect((x0 + 0.12 * w, y0 + 0.42 * h, x1 - 0.1 * w, y1 - 0.08 * h), primary)
        rect((x0 + 0.16 * w, y0 + 0.25 * h, x1 - 0.15 * w, y0 + 0.48 * h), accent)
        line(((x0 + 0.22 * w, y0 + 0.25 * h), (x0 + 0.82 * w, y0 + 0.25 * h)), fill=(246, 242, 217), width=2)
    elif item in {"flower", "potted_plant"}:
        if item == "potted_plant":
            rect((x0 + 0.24 * w, y0 + 0.58 * h, x1 - 0.24 * w, y1 - 0.06 * h), accent)
        line(((x0 + 0.5 * w, y1 - 0.08 * h), (x0 + 0.5 * w, y0 + 0.42 * h)), fill=(69, 126, 76), width=2)
        for angle_box in (
            (0.32, 0.25, 0.50, 0.46),
            (0.50, 0.22, 0.68, 0.45),
            (0.42, 0.08, 0.60, 0.30),
        ):
            ellipse((x0 + angle_box[0] * w, y0 + angle_box[1] * h, x0 + angle_box[2] * w, y0 + angle_box[3] * h), primary)
        ellipse((x0 + 0.44 * w, y0 + 0.28 * h, x0 + 0.58 * w, y0 + 0.44 * h), (236, 197, 78))
    elif item in {"book", "magazine", "newspaper"}:
        rounded((x0 + 0.1 * w, y0 + 0.16 * h, x1 - 0.08 * w, y1 - 0.12 * h), primary, radius=3.0)
        rect((x0 + 0.18 * w, y0 + 0.23 * h, x1 - 0.16 * w, y1 - 0.2 * h), accent, outline_rgb=None)
        line(((x0 + 0.24 * w, y0 + 0.4 * h), (x1 - 0.2 * w, y0 + 0.4 * h)), width=1)
        line(((x0 + 0.24 * w, y0 + 0.56 * h), (x1 - 0.2 * w, y0 + 0.56 * h)), width=1)
    elif item in {"mug", "cup", "bottle", "vase", "candle", "bowl"}:
        if item == "bottle":
            rounded((x0 + 0.34 * w, y0 + 0.08 * h, x0 + 0.66 * w, y1 - 0.08 * h), primary, radius=4.0)
            rect((x0 + 0.39 * w, y0 + 0.02 * h, x0 + 0.61 * w, y0 + 0.18 * h), accent)
        elif item == "bowl":
            draw.pieslice(_scale_bbox((x0 + 0.12 * w, y0 + 0.18 * h, x1 - 0.12 * w, y1 + 0.20 * h), s), 0, 180, fill=tuple(primary), outline=tuple(outline), width=max(1, s))
            line(((x0 + 0.15 * w, y0 + 0.52 * h), (x1 - 0.15 * w, y0 + 0.52 * h)), width=1)
        else:
            rounded((x0 + 0.24 * w, y0 + 0.18 * h, x0 + 0.70 * w, y1 - 0.08 * h), primary, radius=5.0)
            if item in {"mug", "cup"}:
                draw.arc(_scale_bbox((x0 + 0.58 * w, y0 + 0.3 * h, x1 - 0.02 * w, y0 + 0.76 * h), s), -70, 76, fill=tuple(outline), width=max(2, 2 * s))
            if item == "candle":
                line(((x0 + 0.50 * w, y0 + 0.18 * h), (x0 + 0.50 * w, y0 + 0.05 * h)), fill=(88, 70, 55), width=1)
                ellipse((x0 + 0.44 * w, y0, x0 + 0.56 * w, y0 + 0.13 * h), accent, outline_rgb=None)
    elif item in {"fish", "shrimp", "duck"}:
        ellipse((x0 + 0.14 * w, y0 + 0.25 * h, x1 - 0.22 * w, y1 - 0.2 * h), primary)
        draw.polygon(_scale_points(((x1 - 0.26 * w, y0 + 0.5 * h), (x1 - 0.04 * w, y0 + 0.28 * h), (x1 - 0.04 * w, y1 - 0.22 * h)), s), fill=tuple(accent), outline=tuple(outline))
        ellipse((x0 + 0.28 * w, y0 + 0.38 * h, x0 + 0.36 * w, y0 + 0.46 * h), (248, 248, 240))
    elif item in {"shirt", "hat", "bag", "scarf", "umbrella"}:
        if item == "shirt":
            draw.polygon(_scale_points(((x0 + 0.34 * w, y0 + 0.12 * h), (x0 + 0.18 * w, y0 + 0.34 * h), (x0 + 0.28 * w, y0 + 0.48 * h), (x0 + 0.34 * w, y0 + 0.39 * h), (x0 + 0.34 * w, y1 - 0.08 * h), (x0 + 0.76 * w, y1 - 0.08 * h), (x0 + 0.74 * w, y0 + 0.39 * h), (x0 + 0.84 * w, y0 + 0.48 * h), (x0 + 0.94 * w, y0 + 0.34 * h), (x0 + 0.76 * w, y0 + 0.12 * h)), s), fill=tuple(primary), outline=tuple(outline))
        elif item == "umbrella":
            draw.pieslice(_scale_bbox((x0 + 0.08 * w, y0 + 0.12 * h, x1 - 0.08 * w, y1 - 0.18 * h), s), 180, 360, fill=tuple(primary), outline=tuple(outline), width=max(1, s))
            line(((x0 + 0.5 * w, y0 + 0.46 * h), (x0 + 0.5 * w, y1 - 0.08 * h)), width=2)
        elif item == "hat":
            ellipse((x0 + 0.2 * w, y0 + 0.44 * h, x1 - 0.1 * w, y1 - 0.2 * h), primary)
            rect((x0 + 0.32 * w, y0 + 0.2 * h, x0 + 0.68 * w, y0 + 0.56 * h), primary)
        elif item == "bag":
            rounded((x0 + 0.22 * w, y0 + 0.36 * h, x1 - 0.18 * w, y1 - 0.08 * h), primary, radius=4.0)
            draw.arc(_scale_bbox((x0 + 0.32 * w, y0 + 0.12 * h, x0 + 0.72 * w, y0 + 0.52 * h), s), 180, 360, fill=tuple(outline), width=max(1, 2 * s))
        else:
            rounded((x0 + 0.12 * w, y0 + 0.42 * h, x1 - 0.10 * w, y0 + 0.63 * h), primary, radius=4.0)
            line(((x0 + 0.22 * w, y0 + 0.62 * h), (x0 + 0.18 * w, y1 - 0.08 * h)), fill=primary, width=3)
    elif item in {"toy_car", "kite", "hammer", "wrench", "scissors", "key", "pencil", "ruler"}:
        if item == "toy_car":
            rounded((x0 + 0.14 * w, y0 + 0.42 * h, x1 - 0.1 * w, y1 - 0.18 * h), primary, radius=5.0)
            ellipse((x0 + 0.24 * w, y1 - 0.3 * h, x0 + 0.42 * w, y1 - 0.08 * h), accent)
            ellipse((x0 + 0.66 * w, y1 - 0.3 * h, x0 + 0.84 * w, y1 - 0.08 * h), accent)
        elif item == "kite":
            draw.polygon(_scale_points(((x0 + 0.5 * w, y0 + 0.08 * h), (x1 - 0.08 * w, y0 + 0.44 * h), (x0 + 0.5 * w, y1 - 0.08 * h), (x0 + 0.08 * w, y0 + 0.44 * h)), s), fill=tuple(primary), outline=tuple(outline))
            line(((x0 + 0.5 * w, y1 - 0.08 * h), (x0 + 0.36 * w, y1 + 0.12 * h)), fill=accent, width=1)
        elif item in {"hammer", "wrench"}:
            line(((x0 + 0.22 * w, y1 - 0.12 * h), (x1 - 0.24 * w, y0 + 0.18 * h)), fill=primary, width=4)
            if item == "hammer":
                rect((x1 - 0.42 * w, y0 + 0.08 * h, x1 - 0.08 * w, y0 + 0.28 * h), accent)
            else:
                draw.arc(_scale_bbox((x1 - 0.42 * w, y0 + 0.06 * h, x1 - 0.06 * w, y0 + 0.44 * h), s), 35, 305, fill=tuple(accent), width=max(2, 3 * s))
        elif item == "key":
            ellipse((x0 + 0.1 * w, y0 + 0.34 * h, x0 + 0.36 * w, y0 + 0.64 * h), primary)
            line(((x0 + 0.32 * w, y0 + 0.5 * h), (x1 - 0.08 * w, y0 + 0.5 * h)), fill=primary, width=3)
            line(((x1 - 0.18 * w, y0 + 0.5 * h), (x1 - 0.18 * w, y0 + 0.66 * h)), fill=primary, width=2)
        else:
            rounded((x0 + 0.08 * w, y0 + 0.42 * h, x1 - 0.08 * w, y0 + 0.60 * h), primary, radius=2.0)
            if item == "ruler":
                for t in (0.25, 0.38, 0.51, 0.64, 0.77):
                    line(((x0 + t * w, y0 + 0.43 * h), (x0 + t * w, y0 + 0.56 * h)), fill=accent, width=1)
    else:
        rounded((x0 + 0.16 * w, y0 + 0.18 * h, x1 - 0.14 * w, y1 - 0.10 * h), primary, radius=6.0)
        ellipse((x0 + 0.32 * w, y0 + 0.3 * h, x0 + 0.5 * w, y0 + 0.48 * h), accent, outline_rgb=None)
    return primary, accent


def _draw_shop(
    draw: ImageDraw.ImageDraw,
    *,
    rng,
    shop_id: str,
    spec: MarketShopSpec,
    shop_bbox: BBox,
    scale: int,
    style_id: str,
    compact: bool = False,
) -> Tuple[MarketShop, Tuple[MarketItem, ...]]:
    x0, y0, x1, y1 = [float(v) for v in shop_bbox]
    w = x1 - x0
    h = y1 - y0
    facade, awning, sign_fill, trim = _shop_palette(rng, str(spec.shop_type))
    spec_attributes = dict(spec.attributes)
    facade = _coerce_rgb(spec_attributes.get("facade_color_rgb"), facade)
    awning = _coerce_rgb(spec_attributes.get("awning_color_rgb"), awning)
    sign_fill = _coerce_rgb(spec_attributes.get("signboard_color_rgb", spec_attributes.get("sign_color_rgb")), sign_fill)
    if compact:
        sign_bbox = (x0 + 0.06 * w, y0 + 0.055 * h, x1 - 0.06 * w, y0 + 0.255 * h)
        awning_bbox = (x0 + 0.035 * w, y0 + 0.305 * h, x1 - 0.035 * w, y0 + 0.455 * h)
        display_bbox = (x0 + 0.10 * w, y0 + 0.51 * h, x1 - 0.10 * w, y0 + 0.69 * h)
        counter_bbox = (x0 + 0.05 * w, y0 + 0.71 * h, x1 - 0.05 * w, y1 - 0.07 * h)
    else:
        sign_bbox = (x0 + 0.08 * w, y0 + 0.035 * h, x1 - 0.08 * w, y0 + 0.145 * h)
        awning_bbox = (x0 + 0.03 * w, y0 + 0.16 * h, x1 - 0.03 * w, y0 + 0.285 * h)
        display_bbox = (x0 + 0.08 * w, y0 + 0.34 * h, x1 - 0.08 * w, y0 + 0.74 * h)
        counter_bbox = (x0 + 0.04 * w, y0 + 0.72 * h, x1 - 0.04 * w, y1 - 0.06 * h)
    side_shadow = _jitter_rgb(rng, (158, 148, 130), amount=8)
    if str(style_id) == "soft_shadow":
        _draw_shadow(draw, shop_bbox, scale=scale, offset=7.0, alpha_rgb=side_shadow)
    _draw_rounded_rect(draw, shop_bbox, scale=scale, radius=6.0 if compact else 8.0, fill=facade, outline=trim, width=2)
    inner_bbox = (x0 + 0.04 * w, y0 + (0.47 if compact else 0.30) * h, x1 - 0.04 * w, y1 - 0.08 * h)
    draw.rectangle(_scale_bbox(inner_bbox, scale), fill=tuple(_jitter_rgb(rng, (245, 238, 215), amount=8)), outline=tuple(trim), width=max(1, int(scale)))
    _draw_rounded_rect(draw, sign_bbox, scale=scale, radius=4.0, fill=sign_fill, outline=trim, width=1)
    _draw_fit_text(
        draw,
        text=MARKET_SHOP_LABELS.get(str(spec.shop_type), str(spec.shop_type).upper()),
        bbox=sign_bbox,
        scale=scale,
        fill=_readable_text_color(sign_fill),
        bold=True,
        min_size_px=8 if compact else 7,
        max_size_px=28 if compact else 25,
        stroke_fill=(36, 42, 50) if _readable_text_color(sign_fill) == (245, 244, 236) else None,
    )
    _draw_awning(draw, rng=rng, bbox=awning_bbox, color=awning, trim=trim, scale=scale)
    draw.rounded_rectangle(_scale_bbox(counter_bbox, scale), radius=max(1, int(7 * scale)), fill=tuple(_jitter_rgb(rng, (150, 100, 64), amount=13)), outline=tuple(trim), width=max(1, 2 * int(scale)))
    front = (
        (counter_bbox[0], counter_bbox[3] - 0.14 * h),
        (counter_bbox[2], counter_bbox[3] - 0.14 * h),
        (counter_bbox[2] - 0.035 * w, counter_bbox[3]),
        (counter_bbox[0] + 0.035 * w, counter_bbox[3]),
    )
    draw.polygon(_scale_points(front, scale), fill=tuple(_jitter_rgb(rng, (121, 78, 51), amount=12)), outline=tuple(trim))
    shelf_count = 1 if compact else 2
    for shelf_i in range(shelf_count):
        sy = display_bbox[1] + (shelf_i + 1) * ((display_bbox[3] - display_bbox[1]) / float(shelf_count + 1))
        draw.line(_scale_points(((display_bbox[0], sy), (display_bbox[2], sy)), scale), fill=tuple(_jitter_rgb(rng, (122, 94, 70), amount=6)), width=max(1, 2 * int(scale)))
    item_count = len(spec.item_types)
    cols = max(2, min(3 if compact else 4, int(round((w - 20.0) / 44.0))))
    rows = max(1, (item_count + cols - 1) // cols)
    item_boxes: List[BBox] = []
    slot_w = (display_bbox[2] - display_bbox[0]) / float(cols)
    slot_h = (display_bbox[3] - display_bbox[1]) / float(max(2, rows))
    for idx, _item_type in enumerate(spec.item_types):
        row = idx // cols
        col = idx % cols
        cx = display_bbox[0] + (col + 0.5) * slot_w + float(rng.uniform(-0.08, 0.08)) * slot_w
        cy = display_bbox[1] + (row + 0.52) * slot_h + float(rng.uniform(-0.06, 0.08)) * slot_h
        size = min(slot_w * float(rng.uniform(0.54, 0.72)), slot_h * float(rng.uniform(0.58, 0.78)), 34.0 if compact else 42.0)
        aspect = float(rng.uniform(0.88, 1.18))
        box_w = size * aspect
        box_h = size / max(0.72, aspect)
        item_boxes.append((round(cx - 0.5 * box_w, 3), round(cy - 0.5 * box_h, 3), round(cx + 0.5 * box_w, 3), round(cy + 0.5 * box_h, 3)))
    items: List[MarketItem] = []
    for idx, item_type in enumerate(spec.item_types):
        item_id = f"{shop_id}_item_{idx:02d}"
        primary, accent = _draw_market_item(draw, rng=rng, item_type=str(item_type), bbox=item_boxes[idx], scale=scale, style_id=style_id)
        items.append(
            MarketItem(
                item_id=item_id,
                item_type=str(item_type),
                display_name=market_item_display_name(str(item_type)),
                bbox_xyxy=item_boxes[idx],
                shop_id=str(shop_id),
                slot_index=int(idx),
                color_rgb=primary,
                accent_color_rgb=accent,
                attributes={"role": str(spec.role)},
            )
        )
    shop = MarketShop(
        shop_id=str(shop_id),
        shop_type=str(spec.shop_type),
        display_name=market_shop_display_name(str(spec.shop_type)),
        bbox_xyxy=(round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)),
        sign_bbox_xyxy=tuple(round(float(v), 3) for v in sign_bbox),  # type: ignore[arg-type]
        awning_bbox_xyxy=tuple(round(float(v), 3) for v in awning_bbox),  # type: ignore[arg-type]
        facade_bbox_xyxy=(round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)),
        display_bbox_xyxy=tuple(round(float(v), 3) for v in display_bbox),  # type: ignore[arg-type]
        counter_bbox_xyxy=tuple(round(float(v), 3) for v in counter_bbox),  # type: ignore[arg-type]
        item_ids=tuple(item.item_id for item in items),
        item_types=tuple(str(value) for value in spec.item_types),
        role=str(spec.role),
        attributes={
            "label": MARKET_SHOP_LABELS.get(str(spec.shop_type), str(spec.shop_type).upper()),
            **_json_safe(spec_attributes),
            "facade_color_rgb": list(facade),
            "awning_color_rgb": list(awning),
            "sign_color_rgb": list(sign_fill),
            "signboard_color_rgb": list(sign_fill),
            "color_overrides": _json_safe(spec_attributes),
        },
    )
    return shop, tuple(items)


def _draw_market_decor(
    draw: ImageDraw.ImageDraw,
    *,
    rng,
    width: int,
    height: int,
    shop_bboxes: Sequence[BBox],
    layout: Mapping[str, Any],
    scale: int,
    style_id: str,
) -> Tuple[MarketDecor, ...]:
    decor: List[MarketDecor] = []
    object_candidates = ("person", "pedestrian_with_bag", "bicycle", "streetlamp", "road_sign")
    count = int(rng.randint(3, 6))
    occupied: List[BBox] = []
    occupied.extend(tuple(float(v) for v in box) for box in shop_bboxes)
    raw_zones = layout.get("decor_zones", [])
    zones: List[BBox] = []
    if isinstance(raw_zones, Sequence) and not isinstance(raw_zones, (str, bytes)):
        for zone in raw_zones:
            if isinstance(zone, Sequence) and not isinstance(zone, (str, bytes)) and len(zone) == 4:
                zones.append(tuple(float(v) for v in zone))  # type: ignore[arg-type]
    if not zones:
        zones = [(60.0, float(height) - 170.0, float(width) - 60.0, float(height) - 28.0)]
    for idx in range(count):
        decor_type = str(rng.choice(object_candidates))
        if decor_type in {"streetlamp", "road_sign"}:
            w, h = float(rng.uniform(30.0, 44.0)), float(rng.uniform(72.0, 104.0))
        elif decor_type == "bicycle":
            w, h = float(rng.uniform(64.0, 88.0)), float(rng.uniform(38.0, 54.0))
        else:
            w, h = float(rng.uniform(32.0, 48.0)), float(rng.uniform(62.0, 88.0))
        for _attempt in range(80):
            zone = tuple(rng.choice(tuple(zones)))
            zx0, zy0, zx1, zy1 = [float(value) for value in zone]
            x0 = float(rng.uniform(zx0 + 8.0, max(zx0 + 9.0, zx1 - w - 8.0)))
            y1 = float(rng.uniform(zy0 + h + 6.0, max(zy0 + h + 7.0, zy1 - 6.0)))
            candidate = (x0, y1 - h, x0 + w, y1)
            if all(candidate[2] < box[0] - 4.0 or candidate[0] > box[2] + 4.0 or candidate[3] < box[1] - 4.0 or candidate[1] > box[3] + 4.0 for box in occupied):
                break
        primary, accent = choose_object_colors(rng, decor_type)
        rendered = draw_illustration_object(
            draw,
            object_id=f"market_decor_{idx:02d}",
            object_type=decor_type,
            bbox_xyxy=candidate,
            primary_color_rgb=primary,
            accent_color_rgb=accent,
            style_id=str(style_id if decor_type not in {"streetlamp", "road_sign"} else "outlined_cartoon"),
            render_scale=scale,
            gender_id=sample_person_gender(rng) if decor_type in {"person", "pedestrian_with_bag"} else None,
        )
        occupied.append(candidate)
        attributes = {"style_id": str(style_id), "primary_color_rgb": list(primary), "accent_color_rgb": list(accent)}
        if decor_type in {"person", "pedestrian_with_bag"}:
            attributes["gender_id"] = str(rendered.attributes.get("gender_id", "male"))
        decor.append(
            MarketDecor(
                decor_id=str(rendered.object_id),
                decor_type=str(decor_type),
                bbox_xyxy=tuple(round(float(v), 3) for v in candidate),  # type: ignore[arg-type]
                attributes=attributes,
            )
        )
    return tuple(decor)


def _road_bboxes_from_layout(layout: Mapping[str, Any]) -> Tuple[BBox, ...]:
    road_boxes: List[BBox] = []
    raw_road_bboxes = layout.get("road_bboxes")
    if isinstance(raw_road_bboxes, Sequence) and not isinstance(raw_road_bboxes, (str, bytes)):
        for road_bbox in raw_road_bboxes:
            if isinstance(road_bbox, Sequence) and not isinstance(road_bbox, (str, bytes)) and len(road_bbox) == 4:
                road_boxes.append(tuple(float(v) for v in road_bbox))  # type: ignore[arg-type]
    if not road_boxes:
        road_bbox = layout.get("road_bbox")
        if isinstance(road_bbox, Sequence) and not isinstance(road_bbox, (str, bytes)) and len(road_bbox) == 4:
            road_boxes.append(tuple(float(v) for v in road_bbox))  # type: ignore[arg-type]
    return tuple(road_boxes)


def _bbox_intersects_with_gap(a: BBox, b: BBox, gap: float) -> bool:
    return not (
        float(a[2]) < float(b[0]) - float(gap)
        or float(a[0]) > float(b[2]) + float(gap)
        or float(a[3]) < float(b[1]) - float(gap)
        or float(a[1]) > float(b[3]) + float(gap)
    )


def _nearest_road_bbox(shop_bbox: BBox, road_bboxes: Sequence[BBox]) -> BBox | None:
    if not road_bboxes:
        return None
    sx = 0.5 * (float(shop_bbox[0]) + float(shop_bbox[2]))
    sy = 0.5 * (float(shop_bbox[1]) + float(shop_bbox[3]))

    def distance_to_road(road_bbox: BBox) -> float:
        rx0, ry0, rx1, ry1 = [float(value) for value in road_bbox]
        dx = 0.0 if rx0 <= sx <= rx1 else min(abs(sx - rx0), abs(sx - rx1))
        dy = 0.0 if ry0 <= sy <= ry1 else min(abs(sy - ry0), abs(sy - ry1))
        return float(dx * dx + dy * dy)

    return min(tuple(road_bboxes), key=distance_to_road)


def _customer_candidate_bbox(
    *,
    rng,
    shop_bbox: BBox,
    road_bbox: BBox | None,
    width: int,
    height: int,
    object_type: str,
) -> BBox:
    if str(object_type) == "pedestrian_with_bag":
        person_h = float(rng.uniform(64.0, 88.0))
        person_w = float(rng.uniform(38.0, 52.0))
    else:
        person_h = float(rng.uniform(60.0, 82.0))
        person_w = float(rng.uniform(32.0, 46.0))
    sx = 0.5 * (float(shop_bbox[0]) + float(shop_bbox[2]))
    sy = 0.5 * (float(shop_bbox[1]) + float(shop_bbox[3]))
    if road_bbox is None:
        x0 = sx + float(rng.uniform(-0.18, 0.18)) * max(1.0, float(shop_bbox[2]) - float(shop_bbox[0])) - 0.5 * person_w
        y1 = min(float(height) - 16.0, float(shop_bbox[3]) + float(rng.uniform(34.0, 82.0)))
        return (
            round(float(max(8.0, min(float(width) - person_w - 8.0, x0))), 3),
            round(float(max(8.0, y1 - person_h)), 3),
            round(float(max(8.0, min(float(width) - person_w - 8.0, x0)) + person_w), 3),
            round(float(y1), 3),
        )

    rx0, ry0, rx1, ry1 = [float(value) for value in road_bbox]
    road_is_vertical = (rx1 - rx0) < (ry1 - ry0)
    if road_is_vertical:
        road_mid = 0.5 * (rx0 + rx1)
        if sx < road_mid:
            edge_x = float(shop_bbox[2]) + float(rng.uniform(8.0, 22.0))
            lane_x0 = max(rx0 + 6.0, edge_x)
            lane_x1 = min(rx1 - 6.0, edge_x + float(rng.uniform(8.0, 24.0)))
        else:
            edge_x = float(shop_bbox[0]) - person_w - float(rng.uniform(8.0, 22.0))
            lane_x0 = max(rx0 + 6.0, edge_x - float(rng.uniform(8.0, 24.0)))
            lane_x1 = min(rx1 - 6.0, edge_x + person_w)
        x0 = float(rng.uniform(lane_x0, max(lane_x0 + 1.0, lane_x1 - person_w)))
        y1_low = max(ry0 + person_h + 8.0, sy - 0.20 * (float(shop_bbox[3]) - float(shop_bbox[1])))
        y1_high = min(ry1 - 8.0, sy + 0.24 * (float(shop_bbox[3]) - float(shop_bbox[1])))
        y1 = float(rng.uniform(y1_low, max(y1_low + 1.0, y1_high)))
    else:
        road_mid = 0.5 * (ry0 + ry1)
        if sy < road_mid:
            front_top = float(shop_bbox[3]) + float(rng.uniform(2.0, 10.0))
            lane_y0 = max(ry0 + 4.0, front_top + person_h)
            lane_y1 = min(ry1 - 8.0, lane_y0 + float(rng.uniform(4.0, 16.0)))
        else:
            front_bottom = float(shop_bbox[1]) - float(rng.uniform(2.0, 10.0))
            lane_y1 = min(ry1 - 8.0, front_bottom)
            lane_y0 = max(ry0 + person_h + 4.0, lane_y1 - float(rng.uniform(4.0, 16.0)))
        x0_low = max(rx0 + 8.0, sx - 0.22 * (float(shop_bbox[2]) - float(shop_bbox[0])) - 0.5 * person_w)
        x0_high = min(rx1 - person_w - 8.0, sx + 0.22 * (float(shop_bbox[2]) - float(shop_bbox[0])) - 0.5 * person_w)
        x0 = float(rng.uniform(x0_low, max(x0_low + 1.0, x0_high)))
        y1 = float(rng.uniform(lane_y0, max(lane_y0 + 1.0, lane_y1)))
    x0 = max(8.0, min(float(width) - person_w - 8.0, x0))
    y1 = max(person_h + 8.0, min(float(height) - 8.0, y1))
    return (
        round(float(x0), 3),
        round(float(y1 - person_h), 3),
        round(float(x0 + person_w), 3),
        round(float(y1), 3),
    )


def _draw_market_customers(
    draw: ImageDraw.ImageDraw,
    *,
    rng,
    customer_specs: Sequence[MarketCustomerSpec],
    shops: Sequence[MarketShop],
    layout: Mapping[str, Any],
    width: int,
    height: int,
    scale: int,
    style_id: str,
) -> Tuple[MarketDecor, ...]:
    if not customer_specs:
        return ()
    shops_by_type: Dict[str, List[MarketShop]] = {}
    for shop in shops:
        shops_by_type.setdefault(str(shop.shop_type), []).append(shop)
    road_bboxes = _road_bboxes_from_layout(layout)
    occupied: List[BBox] = []
    customers: List[MarketDecor] = []
    type_offsets: Dict[str, int] = {}
    for idx, spec in enumerate(customer_specs):
        matching_shops = shops_by_type.get(str(spec.shop_type), [])
        if not matching_shops:
            raise ValueError(f"customer spec references missing shop type: {spec.shop_type}")
        offset = int(type_offsets.get(str(spec.shop_type), 0))
        shop = matching_shops[offset % len(matching_shops)]
        type_offsets[str(spec.shop_type)] = offset + 1
        object_type = str(spec.object_type)
        if object_type not in {"person", "pedestrian_with_bag"}:
            object_type = "person"
        road_bbox = _nearest_road_bbox(shop.bbox_xyxy, road_bboxes)
        candidate = _customer_candidate_bbox(
            rng=rng,
            shop_bbox=shop.bbox_xyxy,
            road_bbox=road_bbox,
            width=int(width),
            height=int(height),
            object_type=str(object_type),
        )
        for _attempt in range(80):
            if all(not _bbox_intersects_with_gap(candidate, other, 7.0) for other in occupied):
                break
            candidate = _customer_candidate_bbox(
                rng=rng,
                shop_bbox=shop.bbox_xyxy,
                road_bbox=road_bbox,
                width=int(width),
                height=int(height),
                object_type=str(object_type),
            )
        primary, accent = choose_object_colors(rng, str(object_type))
        rendered = draw_illustration_object(
            draw,
            object_id=f"market_customer_{idx:02d}",
            object_type=str(object_type),
            bbox_xyxy=candidate,
            primary_color_rgb=primary,
            accent_color_rgb=accent,
            style_id=str(style_id),
            render_scale=scale,
            gender_id=sample_person_gender(rng),
        )
        occupied.append(tuple(float(v) for v in rendered.bbox_xyxy))
        customers.append(
            MarketDecor(
                decor_id=str(rendered.object_id),
                decor_type="customer",
                bbox_xyxy=tuple(round(float(v), 3) for v in rendered.bbox_xyxy),  # type: ignore[arg-type]
                attributes={
                    "style_id": str(style_id),
                    "primary_color_rgb": list(primary),
                    "accent_color_rgb": list(accent),
                    "customer_object_type": str(object_type),
                    "gender_id": str(rendered.attributes.get("gender_id", "male")),
                    "near_shop_id": str(shop.shop_id),
                    "near_shop_type": str(shop.shop_type),
                    "near_shop_name": str(shop.display_name),
                    "near_shop_label": str(MARKET_SHOP_LABELS.get(str(shop.shop_type), str(shop.shop_type).upper())),
                    "role": str(spec.role),
                    **_json_safe(dict(spec.attributes)),
                },
            )
        )
    return tuple(customers)


def render_urban_market_scene(
    *,
    rng,
    shop_specs: Sequence[MarketShopSpec],
    customer_specs: Sequence[MarketCustomerSpec] | None = None,
    canvas_width: int = 1280,
    canvas_height: int = 960,
    render_scale: int = 2,
    style_weights: Mapping[str, float] | None = None,
    setting_weights: Mapping[str, float] | None = None,
    layout_mode: str = "inventory",
    include_generic_decor: bool = True,
) -> RenderedUrbanMarketScene:
    """Render one urban market scene from semantic shop specs."""

    width = int(canvas_width)
    height = int(canvas_height)
    scale = max(1, int(render_scale))
    if not shop_specs:
        raise ValueError("shop_specs must not be empty")
    style_weight_map = dict(style_weights or {style: 1.0 for style in STYLE_IDS})
    setting_weight_map = dict(setting_weights or {setting: 1.0 for setting in MARKET_SETTING_IDS})
    style_id = _choose_weighted(rng, style_weight_map, STYLE_IDS)
    setting_id = _choose_weighted(rng, setting_weight_map, MARKET_SETTING_IDS)
    image = Image.new("RGB", (width * scale, height * scale), (238, 236, 226))
    draw = ImageDraw.Draw(image)
    background_layout = _draw_background(draw, rng=rng, setting_id=str(setting_id), width=width, height=height, scale=scale)
    shop_bboxes, layout_meta = _shop_layout(rng, shop_count=len(shop_specs), width=width, height=height, layout_mode=str(layout_mode))
    _draw_market_paths(draw, rng=rng, layout=layout_meta, width=width, height=height, scale=scale)
    shops: List[MarketShop] = []
    items: List[MarketItem] = []
    for index, spec in enumerate(shop_specs):
        shop, shop_items = _draw_shop(
            draw,
            rng=rng,
            shop_id=f"market_shop_{index:02d}",
            spec=spec,
            shop_bbox=shop_bboxes[index],
            scale=scale,
            style_id=str(style_id),
            compact=str(layout_meta.get("layout_mode")) == "sign_dense",
        )
        shops.append(shop)
        items.extend(shop_items)
    decor_items: List[MarketDecor] = []
    decor_items.extend(
        _draw_market_customers(
            draw,
            rng=rng,
            customer_specs=tuple(customer_specs or ()),
            shops=tuple(shops),
            layout=layout_meta,
            width=width,
            height=height,
            scale=scale,
            style_id=str(style_id),
        )
    )
    if bool(include_generic_decor):
        decor_items.extend(
            _draw_market_decor(
                draw,
                rng=rng,
                width=width,
                height=height,
                shop_bboxes=shop_bboxes,
                layout=layout_meta,
                scale=scale,
                style_id=str(style_id),
            )
        )
    if scale != 1:
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    layout = {
        "setting": background_layout,
        "shop_layout": layout_meta,
        "shop_count": int(len(shop_specs)),
    }
    return RenderedUrbanMarketScene(
        image=image,
        setting_id=str(setting_id),
        shops=tuple(shops),
        items=tuple(items),
        decor=tuple(decor_items),
        canvas_width=width,
        canvas_height=height,
        render_scale=scale,
        style_id=str(style_id),
        layout=layout,
    )


def urban_market_scene_entities(scene: RenderedUrbanMarketScene) -> List[Dict[str, Any]]:
    """Return trace-ready entities for a rendered urban market scene."""

    entities: List[Dict[str, Any]] = []
    for shop in scene.shops:
        object_record = make_object_record(
            object_id=str(shop.shop_id),
            object_type="shop",
            bbox_xyxy=shop.bbox_xyxy,
            semantic_attributes={
                "shop_type": str(shop.shop_type),
                "shop_name": str(shop.display_name),
                "item_types": list(shop.item_types),
                **dict(shop.attributes),
            },
            visual_attributes={
                "signboard_color_rgb": list(shop.attributes.get("signboard_color_rgb", [])),
                "awning_color_rgb": list(shop.attributes.get("awning_color_rgb", [])),
                "facade_color_rgb": list(shop.attributes.get("facade_color_rgb", [])),
            },
            role=str(shop.role),
            source_entity_type="market_shop",
        ).as_dict()
        entities.append(
            {
                "entity_id": str(shop.shop_id),
                "entity_type": "market_shop",
                "shop_type": str(shop.shop_type),
                "shop_name": str(shop.display_name),
                "bbox": [round(float(v), 3) for v in shop.bbox_xyxy],
                "sign_bbox": [round(float(v), 3) for v in shop.sign_bbox_xyxy],
                "awning_bbox": [round(float(v), 3) for v in shop.awning_bbox_xyxy],
                "facade_bbox": [round(float(v), 3) for v in shop.facade_bbox_xyxy],
                "display_bbox": [round(float(v), 3) for v in shop.display_bbox_xyxy],
                "counter_bbox": [round(float(v), 3) for v in shop.counter_bbox_xyxy],
                "item_ids": list(shop.item_ids),
                "item_types": list(shop.item_types),
                "role": str(shop.role),
                "attributes": _json_safe(shop.attributes),
                "object_record": object_record,
            }
        )
    for item in scene.items:
        object_record = make_object_record(
            object_id=str(item.item_id),
            object_type="market_item",
            bbox_xyxy=item.bbox_xyxy,
            semantic_attributes={
                "item_type": str(item.item_type),
                "item_name": str(item.display_name),
                "shop_id": str(item.shop_id),
                "slot_index": int(item.slot_index),
                **dict(item.attributes),
            },
            visual_attributes={
                "color_rgb": [int(v) for v in item.color_rgb],
                "accent_color_rgb": [int(v) for v in item.accent_color_rgb],
            },
            role=str(item.attributes.get("role", "distractor")),
            source_entity_type="market_item",
        ).as_dict()
        entities.append(
            {
                "entity_id": str(item.item_id),
                "entity_type": "market_item",
                "item_type": str(item.item_type),
                "item_name": str(item.display_name),
                "bbox": [round(float(v), 3) for v in item.bbox_xyxy],
                "shop_id": str(item.shop_id),
                "slot_index": int(item.slot_index),
                "attributes": _json_safe(
                    {
                        **dict(item.attributes),
                        "color_rgb": list(item.color_rgb),
                        "accent_color_rgb": list(item.accent_color_rgb),
                    }
                ),
                "object_record": object_record,
            }
        )
    for decor in scene.decor:
        decor_attributes = dict(decor.attributes)
        object_type = str(decor_attributes.get("customer_object_type", decor.decor_type)) if str(decor.decor_type) == "customer" else str(decor.decor_type)
        semantic_attributes = {
            "decor_type": str(decor.decor_type),
            **{key: value for key, value in decor_attributes.items() if key != "gender_id"},
        }
        object_record = make_object_record(
            object_id=str(decor.decor_id),
            object_type=object_type,
            bbox_xyxy=decor.bbox_xyxy,
            semantic_attributes=semantic_attributes,
            visual_attributes={
                key: decor_attributes[key]
                for key in ("primary_color_rgb", "accent_color_rgb", "style_id", "gender_id")
                if key in decor_attributes
            },
            role=str(decor_attributes.get("role", "distractor")),
            source_entity_type="market_decor",
        ).as_dict()
        entities.append(
            {
                "entity_id": str(decor.decor_id),
                "entity_type": "market_decor",
                "decor_type": str(decor.decor_type),
                "bbox": [round(float(v), 3) for v in decor.bbox_xyxy],
                "attributes": _json_safe(decor.attributes),
                "object_record": object_record,
            }
        )
    return entities


def serialize_urban_market_scene(scene: RenderedUrbanMarketScene) -> Tuple[List[Dict[str, Any]], Dict[str, List[float]], Dict[str, List[float]]]:
    """Serialize shops/items plus bbox maps for task render maps."""

    shops: List[Dict[str, Any]] = [
        {
            "shop_id": str(shop.shop_id),
            "shop_type": str(shop.shop_type),
            "shop_name": str(shop.display_name),
            "bbox": [round(float(v), 3) for v in shop.bbox_xyxy],
            "sign_bbox": [round(float(v), 3) for v in shop.sign_bbox_xyxy],
            "awning_bbox": [round(float(v), 3) for v in shop.awning_bbox_xyxy],
            "facade_bbox": [round(float(v), 3) for v in shop.facade_bbox_xyxy],
            "display_bbox": [round(float(v), 3) for v in shop.display_bbox_xyxy],
            "counter_bbox": [round(float(v), 3) for v in shop.counter_bbox_xyxy],
            "item_ids": list(shop.item_ids),
            "item_types": list(shop.item_types),
            "role": str(shop.role),
            "attributes": _json_safe(shop.attributes),
        }
        for shop in scene.shops
    ]
    items: List[Dict[str, Any]] = [
        {
            "item_id": str(item.item_id),
            "item_type": str(item.item_type),
            "item_name": str(item.display_name),
            "bbox": [round(float(v), 3) for v in item.bbox_xyxy],
            "shop_id": str(item.shop_id),
            "slot_index": int(item.slot_index),
            "attributes": _json_safe(
                {
                    **dict(item.attributes),
                    "color_rgb": list(item.color_rgb),
                    "accent_color_rgb": list(item.accent_color_rgb),
                }
            ),
        }
        for item in scene.items
    ]
    decor: List[Dict[str, Any]] = [
        {
            "decor_id": str(item.decor_id),
            "decor_type": str(item.decor_type),
            "bbox": [round(float(v), 3) for v in item.bbox_xyxy],
            "attributes": _json_safe(item.attributes),
        }
        for item in scene.decor
    ]
    shop_bboxes = {str(shop.shop_id): [round(float(v), 3) for v in shop.bbox_xyxy] for shop in scene.shops}
    item_bboxes = {str(item.item_id): [round(float(v), 3) for v in item.bbox_xyxy] for item in scene.items}
    return [{"shops": shops, "items": items, "decor": decor}], shop_bboxes, item_bboxes


def shop_bbox_map(scene: RenderedUrbanMarketScene) -> Dict[str, List[float]]:
    return {str(shop.shop_id): [round(float(v), 3) for v in shop.bbox_xyxy] for shop in scene.shops}


def shop_sign_bbox_map(scene: RenderedUrbanMarketScene) -> Dict[str, List[float]]:
    return {str(shop.shop_id): [round(float(v), 3) for v in shop.sign_bbox_xyxy] for shop in scene.shops}


def shop_awning_bbox_map(scene: RenderedUrbanMarketScene) -> Dict[str, List[float]]:
    return {str(shop.shop_id): [round(float(v), 3) for v in shop.awning_bbox_xyxy] for shop in scene.shops}


def shop_facade_bbox_map(scene: RenderedUrbanMarketScene) -> Dict[str, List[float]]:
    return {str(shop.shop_id): [round(float(v), 3) for v in shop.facade_bbox_xyxy] for shop in scene.shops}


def item_bbox_map(scene: RenderedUrbanMarketScene) -> Dict[str, List[float]]:
    return {str(item.item_id): [round(float(v), 3) for v in item.bbox_xyxy] for item in scene.items}


def market_decor_bbox_map(scene: RenderedUrbanMarketScene) -> Dict[str, List[float]]:
    return {str(item.decor_id): [round(float(v), 3) for v in item.bbox_xyxy] for item in scene.decor}


def customer_bbox_map(scene: RenderedUrbanMarketScene) -> Dict[str, List[float]]:
    return {
        str(item.decor_id): [round(float(v), 3) for v in item.bbox_xyxy]
        for item in scene.decor
        if str(item.decor_type) == "customer"
    }


def sort_market_bboxes(bbox_map: Mapping[str, Sequence[float]], ids: Sequence[str]) -> List[List[float]]:
    boxes = [(str(item_id), [round(float(v), 3) for v in bbox_map[str(item_id)]]) for item_id in ids]
    ordered = sorted(boxes, key=lambda item: (float(item[1][1]), float(item[1][0]), str(item[0])))
    return [box for _item_id, box in ordered]


__all__ = [
    "MARKET_ITEM_ALLOWED_SHOPS",
    "MARKET_QUERY_ITEM_TYPES",
    "MARKET_SETTING_IDS",
    "MARKET_SHOP_INVENTORY_TYPES",
    "MARKET_SHOP_LABELS",
    "MARKET_SHOP_TYPES",
    "MarketCustomerSpec",
    "MarketShopSpec",
    "RenderedUrbanMarketScene",
    "customer_bbox_map",
    "item_bbox_map",
    "market_decor_bbox_map",
    "market_item_display_name",
    "market_shop_display_name",
    "render_urban_market_scene",
    "serialize_urban_market_scene",
    "shop_awning_bbox_map",
    "shop_bbox_map",
    "shop_facade_bbox_map",
    "shop_sign_bbox_map",
    "sort_market_bboxes",
    "urban_market_scene_entities",
]
