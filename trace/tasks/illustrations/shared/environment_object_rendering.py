"""Rich environmental illustration scenes with semantic layout metadata."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from .render_geometry import scale_bbox as _scale_bbox, scale_points as _scale_points
from .object_library import (
    BBox,
    RGB,
    STYLE_IDS,
    aspect_ratio_for_object,
    choose_object_colors,
    draw_illustration_object,
    family_for_object,
    serialize_object,
)
from .object_catalog import environment_theme_land_object_types, variant_ids_with_tag
from .object_registry import make_object_record
from .person_rendering import sample_person_gender


ENVIRONMENT_THEME_IDS: Tuple[str, ...] = variant_ids_with_tag("environment_theme")
ROAD_OBJECT_TYPES: Tuple[str, ...] = variant_ids_with_tag("env_road")
RIVER_OBJECT_TYPES: Tuple[str, ...] = variant_ids_with_tag("env_river")
SKY_OBJECT_TYPES: Tuple[str, ...] = variant_ids_with_tag("env_sky")
LAND_OBJECT_TYPES: Tuple[str, ...] = variant_ids_with_tag("env_land")
THEME_LAND_OBJECT_TYPES: Dict[str, Tuple[str, ...]] = {
    theme_id: environment_theme_land_object_types(str(theme_id)) for theme_id in ENVIRONMENT_THEME_IDS
}
NO_SHADOW_SKY_STYLE_IDS: Tuple[str, ...] = ("flat_vector", "outlined_cartoon")
THEME_OBJECT_COUNT_CAPS: Dict[str, int] = {
    "park_road": 18,
    "river_meadow": 18,
    "road_and_river": 17,
    "canal_city": 15,
    "skyline_street": 15,
}


@dataclass(frozen=True)
class EnvironmentFeature:
    """One semantic environmental feature, such as a road, river, or bridge."""

    feature_id: str
    feature_type: str
    bbox_xyxy: BBox
    path_points: Tuple[Tuple[float, float], ...]
    width_px: float
    attributes: Mapping[str, Any]


@dataclass(frozen=True)
class EnvironmentBuilding:
    """One skyline/city building with semantic window metadata."""

    building_id: str
    bbox_xyxy: BBox
    roof_type: str
    window_bboxes: Tuple[BBox, ...]
    lit_window_bboxes: Tuple[BBox, ...]
    door_bbox: BBox | None
    attributes: Mapping[str, Any]


@dataclass(frozen=True)
class EnvironmentObjectPlacement:
    """A selected illustration object and its resolved placement."""

    object_id: str
    object_type: str
    bbox_xyxy: BBox
    zone_id: str
    primary_color_rgb: RGB
    accent_color_rgb: RGB
    style_id: str
    relations: Mapping[str, Any]


@dataclass(frozen=True)
class RenderedEnvironmentObjectScene:
    """Rendered environment scene plus trace-ready metadata."""

    image: Image.Image
    theme_id: str
    features: Tuple[EnvironmentFeature, ...]
    buildings: Tuple[EnvironmentBuilding, ...]
    objects: Tuple[Any, ...]
    placements: Tuple[EnvironmentObjectPlacement, ...]
    canvas_width: int
    canvas_height: int
    render_scale: int
    style_id: str
    layout: Mapping[str, Any]




def _bbox_area(box: BBox) -> float:
    return max(0.0, float(box[2]) - float(box[0])) * max(0.0, float(box[3]) - float(box[1]))


def _bbox_overlap_area(a: BBox, b: BBox) -> float:
    x0 = max(float(a[0]), float(b[0]))
    y0 = max(float(a[1]), float(b[1]))
    x1 = min(float(a[2]), float(b[2]))
    y1 = min(float(a[3]), float(b[3]))
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def _inflate(box: BBox, margin: float) -> BBox:
    return (
        float(box[0]) - float(margin),
        float(box[1]) - float(margin),
        float(box[2]) + float(margin),
        float(box[3]) + float(margin),
    )


def _union(bboxes: Iterable[BBox]) -> BBox:
    boxes = [tuple(float(v) for v in box) for box in bboxes]
    if not boxes:
        return (0.0, 0.0, 0.0, 0.0)
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _path_bbox(points: Sequence[Tuple[float, float]], width_px: float) -> BBox:
    pad = float(width_px) * 0.5
    return _inflate(
        (
            min(float(x) for x, _ in points),
            min(float(y) for _, y in points),
            max(float(x) for x, _ in points),
            max(float(y) for _, y in points),
        ),
        pad,
    )


def _interpolate_path_y(path_points: Sequence[Tuple[float, float]], x: float) -> float:
    points = sorted((float(px), float(py)) for px, py in path_points)
    if not points:
        return 0.0
    if float(x) <= points[0][0]:
        return float(points[0][1])
    if float(x) >= points[-1][0]:
        return float(points[-1][1])
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= float(x) <= x1:
            t = 0.0 if abs(x1 - x0) < 1e-6 else (float(x) - x0) / (x1 - x0)
            return float(y0) + t * (float(y1) - float(y0))
    return float(points[-1][1])


def _nearest_point_on_segment(
    point: Tuple[float, float],
    a: Tuple[float, float],
    b: Tuple[float, float],
) -> Tuple[float, float, float]:
    px, py = float(point[0]), float(point[1])
    ax, ay = float(a[0]), float(a[1])
    bx, by = float(b[0]), float(b[1])
    dx = bx - ax
    dy = by - ay
    denom = dx * dx + dy * dy
    if denom <= 1e-9:
        return ax, ay, math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
    qx = ax + t * dx
    qy = ay + t * dy
    return qx, qy, math.hypot(px - qx, py - qy)


def _nearest_path_point(
    point: Tuple[float, float],
    path_points: Sequence[Tuple[float, float]],
) -> Tuple[float, float, float]:
    best = (float(path_points[0][0]), float(path_points[0][1]), float("inf"))
    for a, b in zip(path_points, path_points[1:]):
        candidate = _nearest_point_on_segment(point, a, b)
        if float(candidate[2]) < float(best[2]):
            best = candidate
    return best


def _object_center(box: BBox) -> Tuple[float, float]:
    return (0.5 * (float(box[0]) + float(box[2])), 0.5 * (float(box[1]) + float(box[3])))


def _fits(existing: Sequence[BBox], candidate: BBox, *, min_gap_px: float, max_overlap_fraction: float) -> bool:
    expanded = _inflate(candidate, float(min_gap_px))
    for other in existing:
        overlap = _bbox_overlap_area(expanded, _inflate(other, float(min_gap_px)))
        if overlap <= 0.0:
            continue
        denom = max(1.0, min(_bbox_area(candidate), _bbox_area(other)))
        if float(overlap) / denom > float(max_overlap_fraction):
            return False
    return True


def _draw_line(
    draw: ImageDraw.ImageDraw,
    points: Sequence[Tuple[float, float]],
    *,
    fill: RGB,
    width: float,
    scale: int,
) -> None:
    draw.line(
        _scale_points(points, scale),
        fill=tuple(int(v) for v in fill),
        width=max(1, int(round(float(width) * int(scale)))),
        joint="curve",
    )


def _jitter_rgb(rng, color: RGB, amount: int = 8) -> List[int]:
    return [max(0, min(255, int(value) + int(rng.randint(-amount, amount)))) for value in color]


def _sample_environment_layout(rng, *, theme_id: str, width: int, height: int) -> Dict[str, Any]:
    """Sample explicit environment geometry shared by drawing and placement."""

    theme = str(theme_id)
    h = float(height)
    if theme == "river_meadow":
        land_top = float(rng.uniform(0.32, 0.43)) * h
        river_base = float(rng.uniform(0.57, 0.68)) * h
        road_base = 0.0
    elif theme == "road_and_river":
        land_top = float(rng.uniform(0.24, 0.34)) * h
        river_base = float(rng.uniform(0.57, 0.66)) * h
        road_base = float(rng.uniform(0.32, 0.43)) * h
    elif theme == "canal_city":
        land_top = float(rng.uniform(0.50, 0.59)) * h
        river_base = float(rng.uniform(0.62, 0.72)) * h
        road_base = 0.0
    elif theme == "skyline_street":
        land_top = float(rng.uniform(0.49, 0.58)) * h
        river_base = 0.0
        road_base = float(rng.uniform(0.75, 0.83)) * h
    else:
        land_top = float(rng.uniform(0.38, 0.50)) * h
        river_base = 0.0
        road_base = float(rng.uniform(0.68, 0.79)) * h

    if theme in {"canal_city", "skyline_street"}:
        zone_bias = {
            "sky": float(rng.uniform(0.22, 0.48)),
            "land_above": float(rng.uniform(0.45, 0.90)),
            "land_below": float(rng.uniform(0.95, 1.55)),
            "road": float(rng.uniform(1.15, 1.85)),
            "river": float(rng.uniform(0.85, 1.40)),
        }
    else:
        zone_bias = {
            "sky": float(rng.uniform(0.42, 0.85)),
            "land_above": float(rng.uniform(0.80, 1.45)),
            "land_below": float(rng.uniform(0.80, 1.45)),
            "road": float(rng.uniform(0.75, 1.35)),
            "river": float(rng.uniform(0.75, 1.35)),
        }

    return {
        "layout_id": str(rng.choice(("open_left", "open_right", "center_sweep", "low_foreground"))),
        "land_top_y": round(float(land_top), 3),
        "road_base_y": round(float(road_base), 3),
        "river_base_y": round(float(river_base), 3),
        "road_amplitude_px": round(float(rng.uniform(28.0, 58.0) if theme != "skyline_street" else rng.uniform(18.0, 34.0)), 3),
        "river_amplitude_px": round(float(rng.uniform(30.0, 52.0) if theme != "canal_city" else rng.uniform(18.0, 34.0)), 3),
        "road_width_px": round(float(rng.uniform(84.0, 112.0) if theme != "skyline_street" else rng.uniform(98.0, 124.0)), 3),
        "river_width_px": round(float(rng.uniform(94.0, 116.0) if theme != "canal_city" else rng.uniform(84.0, 104.0)), 3),
        "building_horizon_y": round(float(land_top) + float(rng.uniform(-38.0, 8.0)), 3),
        "sky_rgb": _jitter_rgb(rng, (235, 246, 255), 8),
        "ground_rgb": _jitter_rgb(rng, (221, 234, 204), 10),
        "city_ground_rgb": _jitter_rgb(rng, (224, 223, 210), 9),
        "zone_bias": zone_bias,
        "canvas_width_px": int(width),
    }


def _layout_float(layout: Mapping[str, Any] | None, key: str, fallback: float) -> float:
    if layout is None:
        return float(fallback)
    try:
        return float(layout.get(key, fallback))
    except (TypeError, ValueError):
        return float(fallback)


def _layout_rgb(layout: Mapping[str, Any], key: str, fallback: RGB) -> RGB:
    value = layout.get(key, fallback)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) >= 3:
        return (int(value[0]), int(value[1]), int(value[2]))
    return fallback


def _draw_background(
    draw: ImageDraw.ImageDraw,
    *,
    theme_id: str,
    width: int,
    height: int,
    scale: int,
    layout: Mapping[str, Any],
) -> None:
    w = int(width) * int(scale)
    h = int(height) * int(scale)
    theme = str(theme_id)
    land_top = int(round(_layout_float(layout, "land_top_y", _land_top_y(theme, int(height))) * int(scale)))
    if theme in {"canal_city", "skyline_street"}:
        draw.rectangle((0, 0, w, h), fill=_layout_rgb(layout, "sky_rgb", (232, 242, 250)))
        draw.rectangle((0, land_top, w, h), fill=_layout_rgb(layout, "city_ground_rgb", (224, 223, 210)))
    elif theme == "river_meadow":
        draw.rectangle((0, 0, w, h), fill=_layout_rgb(layout, "sky_rgb", (233, 246, 255)))
        draw.rectangle((0, land_top, w, h), fill=_layout_rgb(layout, "ground_rgb", (215, 235, 196)))
    elif theme == "road_and_river":
        draw.rectangle((0, 0, w, h), fill=_layout_rgb(layout, "sky_rgb", (235, 246, 255)))
        draw.rectangle((0, land_top, w, h), fill=_layout_rgb(layout, "ground_rgb", (221, 234, 204)))
    else:
        draw.rectangle((0, 0, w, h), fill=_layout_rgb(layout, "sky_rgb", (235, 246, 255)))
        draw.rectangle((0, land_top, w, h), fill=_layout_rgb(layout, "ground_rgb", (221, 234, 204)))


def _draw_sky_decor(
    draw: ImageDraw.ImageDraw,
    *,
    rng,
    theme_id: str,
    width: int,
    height: int,
    scale: int,
    land_top_y: float | None = None,
) -> Tuple[EnvironmentFeature, ...]:
    features: List[EnvironmentFeature] = []
    sky_bottom = max(120.0, float(land_top_y if land_top_y is not None else _land_top_y(str(theme_id), int(height))) - 46.0)
    if bool(rng.random() < 0.55):
        r = float(rng.uniform(22.0, 34.0))
        cx = float(rng.uniform(80.0, float(width) - 80.0))
        cy = float(rng.uniform(58.0, min(150.0, sky_bottom - 24.0)))
        for idx in range(12):
            angle = 2.0 * math.pi * idx / 12.0
            _draw_line(
                draw,
                ((cx + r * math.cos(angle), cy + r * math.sin(angle)), (cx + 1.32 * r * math.cos(angle), cy + 1.32 * r * math.sin(angle))),
                fill=(235, 186, 70),
                width=2.0,
                scale=scale,
            )
        box = (cx - r, cy - r, cx + r, cy + r)
        draw.ellipse(_scale_bbox(box, scale), fill=(247, 213, 91), outline=(198, 157, 57), width=max(1, int(2 * scale)))
        features.append(
            EnvironmentFeature(
                feature_id="sun_00",
                feature_type="sun",
                bbox_xyxy=tuple(float(v) for v in box),
                path_points=(),
                width_px=2.0 * r,
                attributes={"role": "sky_decor", "counts_as_foreground_object": False},
            )
        )
    cloud_count = int(rng.randint(1, 4)) if str(theme_id) not in {"canal_city", "skyline_street"} else int(rng.randint(0, 3))
    for index in range(cloud_count):
        cw = float(rng.uniform(88.0, 150.0))
        ch = float(rng.uniform(32.0, 54.0))
        x0 = float(rng.uniform(28.0, float(width) - cw - 28.0))
        y0 = float(rng.uniform(48.0, max(52.0, sky_bottom - ch - 20.0)))
        blobs = (
            (x0, y0 + 0.34 * ch, x0 + 0.42 * cw, y0 + 0.98 * ch),
            (x0 + 0.24 * cw, y0, x0 + 0.66 * cw, y0 + 0.92 * ch),
            (x0 + 0.54 * cw, y0 + 0.28 * ch, x0 + cw, y0 + ch),
        )
        for blob in blobs:
            draw.ellipse(_scale_bbox(blob, scale), fill=(248, 250, 252), outline=(216, 226, 235), width=max(1, int(scale)))
        base = (x0 + 0.12 * cw, y0 + 0.58 * ch, x0 + 0.90 * cw, y0 + ch)
        draw.rounded_rectangle(_scale_bbox(base, scale), radius=max(1, int(10 * scale)), fill=(248, 250, 252))
        bbox = _union([*blobs, base])
        features.append(
            EnvironmentFeature(
                feature_id=f"cloud_{index:02d}",
                feature_type="cloud",
                bbox_xyxy=tuple(float(v) for v in bbox),
                path_points=(),
                width_px=float(cw),
                attributes={"role": "sky_decor", "counts_as_foreground_object": False},
            )
        )
    return tuple(features)


def _land_top_y(theme_id: str, height: int, layout: Mapping[str, Any] | None = None) -> float:
    if layout is not None and "land_top_y" in layout:
        return _layout_float(layout, "land_top_y", 0.42 * float(height))
    theme = str(theme_id)
    if theme == "river_meadow":
        return 0.36 * float(height)
    if theme == "road_and_river":
        return 0.28 * float(height)
    if theme in {"canal_city", "skyline_street"}:
        return 0.54 * float(height)
    return 0.42 * float(height)


def _sample_curve(
    rng,
    *,
    width: int,
    y_base: float,
    amplitude: float,
    phase: float,
    jitter: float,
    point_count: int = 14,
) -> Tuple[Tuple[float, float], ...]:
    points: List[Tuple[float, float]] = []
    for index in range(int(point_count)):
        x = float(width) * float(index) / float(max(1, int(point_count) - 1))
        wave = math.sin(float(index) * 0.68 + float(phase)) + 0.45 * math.sin(float(index) * 1.17 + 0.7 * float(phase))
        y = float(y_base) + float(amplitude) * wave + float(rng.uniform(-jitter, jitter))
        points.append((x, y))
    return tuple(points)


def _draw_river(
    draw: ImageDraw.ImageDraw,
    *,
    path_points: Sequence[Tuple[float, float]],
    width_px: float,
    scale: int,
) -> EnvironmentFeature:
    _draw_line(draw, path_points, fill=(139, 184, 185), width=float(width_px) + 28.0, scale=scale)
    _draw_line(draw, path_points, fill=(88, 169, 205), width=float(width_px), scale=scale)
    _draw_line(draw, path_points, fill=(139, 203, 224), width=max(6.0, float(width_px) * 0.18), scale=scale)
    for offset in (-0.24, 0.24):
        shifted = tuple((float(x), float(y) + offset * float(width_px)) for x, y in path_points)
        _draw_line(draw, shifted, fill=(72, 148, 187), width=3.0, scale=scale)
    return EnvironmentFeature(
        feature_id="river_0",
        feature_type="river",
        bbox_xyxy=_path_bbox(path_points, float(width_px) + 28.0),
        path_points=tuple((float(x), float(y)) for x, y in path_points),
        width_px=float(width_px),
        attributes={"is_curved": True, "surface": "water"},
    )


def _draw_road(
    draw: ImageDraw.ImageDraw,
    *,
    path_points: Sequence[Tuple[float, float]],
    width_px: float,
    scale: int,
) -> EnvironmentFeature:
    _draw_line(draw, path_points, fill=(128, 127, 119), width=float(width_px) + 18.0, scale=scale)
    _draw_line(draw, path_points, fill=(91, 96, 101), width=float(width_px), scale=scale)
    dash_segments = []
    for a, b in zip(path_points[1::2], path_points[2::2]):
        dash_segments.append((a, b))
    for a, b in dash_segments:
        _draw_line(draw, (a, b), fill=(242, 231, 157), width=5.0, scale=scale)
    return EnvironmentFeature(
        feature_id="road_0",
        feature_type="road",
        bbox_xyxy=_path_bbox(path_points, float(width_px) + 18.0),
        path_points=tuple((float(x), float(y)) for x, y in path_points),
        width_px=float(width_px),
        attributes={"is_curved": True, "surface": "asphalt"},
    )


def _draw_bridge(
    draw: ImageDraw.ImageDraw,
    *,
    bridge_id: str,
    river_path: Sequence[Tuple[float, float]],
    x: float,
    river_width: float,
    scale: int,
) -> EnvironmentFeature:
    y = _interpolate_path_y(river_path, float(x))
    box = (
        float(x) - 24.0,
        float(y) - 0.62 * float(river_width),
        float(x) + 24.0,
        float(y) + 0.62 * float(river_width),
    )
    draw.rounded_rectangle(
        _scale_bbox(box, scale),
        radius=max(1, int(8 * int(scale))),
        fill=(199, 169, 119),
        outline=(124, 101, 72),
        width=max(1, int(3 * int(scale))),
    )
    rail_left = (box[0] + 7.0, box[1] + 6.0, box[0] + 12.0, box[3] - 6.0)
    rail_right = (box[2] - 12.0, box[1] + 6.0, box[2] - 7.0, box[3] - 6.0)
    for rail in (rail_left, rail_right):
        draw.rounded_rectangle(_scale_bbox(rail, scale), radius=max(1, int(2 * int(scale))), fill=(117, 88, 61))
    return EnvironmentFeature(
        feature_id=str(bridge_id),
        feature_type="bridge",
        bbox_xyxy=tuple(float(v) for v in box),
        path_points=((float(x), float(box[1])), (float(x), float(box[3]))),
        width_px=float(box[2] - box[0]),
        attributes={"crosses_feature_id": "river_0", "orientation": "vertical"},
    )


def _draw_crosswalk(
    draw: ImageDraw.ImageDraw,
    *,
    crosswalk_id: str,
    road_path: Sequence[Tuple[float, float]],
    x: float,
    road_width: float,
    scale: int,
) -> EnvironmentFeature:
    y = _interpolate_path_y(road_path, float(x))
    stripe_boxes: List[BBox] = []
    for offset in (-18.0, -6.0, 6.0, 18.0):
        box = (
            float(x) + offset - 4.0,
            float(y) - 0.42 * float(road_width),
            float(x) + offset + 4.0,
            float(y) + 0.42 * float(road_width),
        )
        draw.rounded_rectangle(_scale_bbox(box, scale), radius=max(1, int(2 * int(scale))), fill=(245, 243, 230))
        stripe_boxes.append(box)
    return EnvironmentFeature(
        feature_id=str(crosswalk_id),
        feature_type="crosswalk",
        bbox_xyxy=_union(stripe_boxes),
        path_points=((float(x), float(y) - 0.42 * float(road_width)), (float(x), float(y) + 0.42 * float(road_width))),
        width_px=36.0,
        attributes={"crosses_feature_id": "road_0"},
    )


def _draw_buildings(
    draw: ImageDraw.ImageDraw,
    *,
    rng,
    width: int,
    horizon_y: float,
    scale: int,
    max_buildings: int,
    lit_window_count_override: int | None = None,
) -> Tuple[EnvironmentBuilding, ...]:
    building_specs: List[Dict[str, Any]] = []
    x = float(rng.uniform(8.0, 30.0))
    index = 0
    palette = ((92, 115, 139), (129, 121, 147), (151, 132, 112), (91, 132, 146), (152, 104, 102))
    while x < float(width) - 40.0 and index < int(max_buildings):
        bw = float(rng.uniform(54.0, 112.0))
        bh = float(rng.uniform(118.0, 260.0))
        y1 = float(horizon_y) + float(rng.uniform(-5.0, 20.0))
        box = (x, y1 - bh, min(float(width) - 8.0, x + bw), y1)
        fill = tuple(int(v) for v in rng.choice(palette))
        outline = (61, 70, 83)
        draw.rectangle(_scale_bbox(box, scale), fill=fill, outline=outline, width=max(1, int(2 * scale)))
        roof_type = str(rng.choice(("flat", "slanted", "antenna")))
        if roof_type == "slanted":
            roof = ((box[0], box[1]), (0.5 * (box[0] + box[2]), box[1] - 24.0), (box[2], box[1]))
            draw.polygon(_scale_points(roof, scale), fill=(78, 82, 92), outline=outline)
        elif roof_type == "antenna":
            cx = 0.5 * (box[0] + box[2])
            _draw_line(draw, ((cx, box[1]), (cx, box[1] - 28.0)), fill=outline, width=2.0, scale=scale)
            _draw_line(draw, ((cx - 10.0, box[1] - 18.0), (cx + 10.0, box[1] - 18.0)), fill=outline, width=2.0, scale=scale)
        window_bboxes: List[BBox] = []
        cols = max(2, int((box[2] - box[0]) // 24))
        rows = max(2, int((box[3] - box[1]) // 34))
        pad_x = 10.0
        pad_y = 18.0
        cell_w = max(12.0, (box[2] - box[0] - 2.0 * pad_x) / float(cols))
        cell_h = max(14.0, (box[3] - box[1] - 2.0 * pad_y) / float(rows))
        for row in range(rows):
            for col in range(cols):
                wx0 = box[0] + pad_x + col * cell_w + 3.0
                wy0 = box[1] + pad_y + row * cell_h + 4.0
                wb = (wx0, wy0, wx0 + min(14.0, cell_w - 6.0), wy0 + min(18.0, cell_h - 7.0))
                if wb[3] > box[3] - 22.0:
                    continue
                window_bboxes.append(tuple(float(v) for v in wb))
        door: BBox | None = None
        if (box[2] - box[0]) > 60.0:
            door = (0.5 * (box[0] + box[2]) - 10.0, box[3] - 30.0, 0.5 * (box[0] + box[2]) + 10.0, box[3])
            draw.rectangle(_scale_bbox(door, scale), fill=(54, 47, 51))
        building_specs.append(
            {
                "building_id": f"building_{index:02d}",
                "bbox_xyxy": tuple(float(v) for v in box),
                "roof_type": roof_type,
                "window_bboxes": tuple(window_bboxes),
                "door_bbox": door,
            }
        )
        x = box[2] + float(rng.uniform(5.0, 16.0))
        index += 1

    lit_keys: set[Tuple[int, int]] = set()
    if lit_window_count_override is not None:
        all_keys = [
            (building_index, window_index)
            for building_index, spec in enumerate(building_specs)
            for window_index, _bbox in enumerate(spec["window_bboxes"])
        ]
        target = int(lit_window_count_override)
        if target < 0 or target > len(all_keys):
            raise ValueError("lit_window_count_override is outside available window support")
        rng.shuffle(all_keys)
        lit_keys = set(all_keys[:target])

    buildings: List[EnvironmentBuilding] = []
    for building_index, spec in enumerate(building_specs):
        window_bboxes = tuple(spec["window_bboxes"])
        lit_window_bboxes: List[BBox] = []
        for window_index, wb in enumerate(window_bboxes):
            lit = (building_index, window_index) in lit_keys if lit_window_count_override is not None else bool(rng.random() < 0.42)
            draw.rounded_rectangle(
                _scale_bbox(wb, scale),
                radius=max(1, int(2 * scale)),
                fill=(249, 218, 114) if lit else (65, 82, 101),
            )
            if lit:
                lit_window_bboxes.append(tuple(float(v) for v in wb))
        if spec["door_bbox"] is not None:
            draw.rectangle(_scale_bbox(spec["door_bbox"], scale), fill=(54, 47, 51))
        buildings.append(
            EnvironmentBuilding(
                building_id=str(spec["building_id"]),
                bbox_xyxy=tuple(float(v) for v in spec["bbox_xyxy"]),
                roof_type=str(spec["roof_type"]),
                window_bboxes=tuple(window_bboxes),
                lit_window_bboxes=tuple(lit_window_bboxes),
                door_bbox=spec["door_bbox"],
                attributes={
                    "window_count": len(window_bboxes),
                    "lit_window_count": len(lit_window_bboxes),
                    "height_px": round(float(spec["bbox_xyxy"][3] - spec["bbox_xyxy"][1]), 3),
                },
            )
        )
    return tuple(buildings)


def _choose_theme(rng, theme_weights: Mapping[str, float]) -> str:
    choices = [(theme, float(theme_weights.get(theme, 0.0))) for theme in ENVIRONMENT_THEME_IDS]
    total = sum(max(0.0, weight) for _, weight in choices)
    if total <= 0.0:
        return str(rng.choice(ENVIRONMENT_THEME_IDS))
    threshold = float(rng.random()) * total
    running = 0.0
    for theme, weight in choices:
        running += max(0.0, weight)
        if running >= threshold:
            return str(theme)
    return str(choices[-1][0])


def _choose_style(rng, style_weights: Mapping[str, float]) -> str:
    choices = [(style, float(style_weights.get(style, 0.0))) for style in STYLE_IDS]
    total = sum(max(0.0, weight) for _, weight in choices)
    if total <= 0.0:
        return str(rng.choice(STYLE_IDS))
    threshold = float(rng.random()) * total
    running = 0.0
    for style, weight in choices:
        running += max(0.0, weight)
        if running >= threshold:
            return str(style)
    return str(choices[-1][0])


def _choose_zone_style(rng, style_weights: Mapping[str, float], zone_id: str) -> str:
    if str(zone_id) != "sky":
        return _choose_style(rng, style_weights)
    choices = [(style, float(style_weights.get(style, 0.0))) for style in NO_SHADOW_SKY_STYLE_IDS]
    total = sum(max(0.0, weight) for _, weight in choices)
    if total <= 0.0:
        return str(rng.choice(NO_SHADOW_SKY_STYLE_IDS))
    threshold = float(rng.random()) * total
    running = 0.0
    for style, weight in choices:
        running += max(0.0, weight)
        if running >= threshold:
            return str(style)
    return str(choices[-1][0])


def effective_environment_object_count(theme_id: str, requested_object_count: int) -> int:
    cap = int(THEME_OBJECT_COUNT_CAPS.get(str(theme_id), int(requested_object_count)))
    return max(1, min(int(requested_object_count), cap))


def _relation_to_feature(center: Tuple[float, float], feature: EnvironmentFeature) -> Dict[str, Any]:
    px, py = float(center[0]), float(center[1])
    if feature.path_points:
        y_on_path = _interpolate_path_y(feature.path_points, px)
        qx, qy, distance = _nearest_path_point((px, py), feature.path_points)
    else:
        y_on_path = 0.5 * (float(feature.bbox_xyxy[1]) + float(feature.bbox_xyxy[3]))
        qx = max(float(feature.bbox_xyxy[0]), min(float(feature.bbox_xyxy[2]), px))
        qy = max(float(feature.bbox_xyxy[1]), min(float(feature.bbox_xyxy[3]), py))
        distance = math.hypot(px - qx, py - qy)
    margin = max(8.0, float(feature.width_px) * 0.5)
    if py < y_on_path - margin:
        vertical_relation = "above"
    elif py > y_on_path + margin:
        vertical_relation = "below"
    else:
        vertical_relation = "on"
    return {
        "feature_id": str(feature.feature_id),
        "feature_type": str(feature.feature_type),
        "vertical_relation": vertical_relation,
        "signed_vertical_distance_px": round(float(py - y_on_path), 3),
        "nearest_distance_px": round(float(distance), 3),
        "nearest_point_px": [round(float(qx), 3), round(float(qy), 3)],
    }


def _build_feature_relations(box: BBox, features: Sequence[EnvironmentFeature]) -> Dict[str, Any]:
    center = _object_center(box)
    relations = {feature.feature_id: _relation_to_feature(center, feature) for feature in features if feature.feature_type in {"road", "river"}}
    if "road_0" in relations and "river_0" in relations:
        road_side = str(relations["road_0"]["vertical_relation"])
        river_side = str(relations["river_0"]["vertical_relation"])
        signed_road = float(relations["road_0"]["signed_vertical_distance_px"])
        signed_river = float(relations["river_0"]["signed_vertical_distance_px"])
        relations["between_road_and_river"] = bool(signed_road * signed_river < 0.0 and road_side != "on" and river_side != "on")
    else:
        relations["between_road_and_river"] = False
    return relations


def _sample_object_type(rng, zone_id: str, theme_id: str) -> str:
    if str(zone_id) == "road":
        return str(rng.choice(ROAD_OBJECT_TYPES))
    if str(zone_id) == "river":
        return str(rng.choice(RIVER_OBJECT_TYPES))
    if str(zone_id) == "sky":
        return str(rng.choice(SKY_OBJECT_TYPES))
    land_pool = THEME_LAND_OBJECT_TYPES.get(str(theme_id), LAND_OBJECT_TYPES)
    return str(rng.choice(land_pool))


def _zone_for_theme(
    rng,
    theme_id: str,
    features: Sequence[EnvironmentFeature],
    zone_bias: Mapping[str, float] | None = None,
) -> str:
    feature_types = {feature.feature_type for feature in features}
    weights: Dict[str, float] = {"sky": 0.55, "land_above": 1.0, "land_below": 1.0}
    if "road" in feature_types:
        weights["road"] = 0.9 if str(theme_id) != "skyline_street" else 1.5
    if "river" in feature_types:
        weights["river"] = 0.9
    if str(theme_id) in {"canal_city", "skyline_street"}:
        weights["land_above"] = 0.55
        weights["land_below"] = 1.15
        weights["sky"] = 0.32
    for zone_id, multiplier in (zone_bias or {}).items():
        if str(zone_id) in weights:
            weights[str(zone_id)] = max(0.0, float(weights[str(zone_id)]) * float(multiplier))
    total = sum(weights.values())
    threshold = float(rng.random()) * total
    running = 0.0
    for zone_id, weight in weights.items():
        running += float(weight)
        if running >= threshold:
            return str(zone_id)
    return "land_below"


def _candidate_box_for_zone(
    *,
    rng,
    zone_id: str,
    object_type: str,
    width: int,
    height: int,
    road: EnvironmentFeature | None,
    river: EnvironmentFeature | None,
    land_top_y: float,
    size_min_px: int,
    size_max_px: int,
) -> BBox:
    aspect = max(0.35, float(aspect_ratio_for_object(str(object_type))))
    h = float(rng.randint(int(size_min_px), int(size_max_px)))
    if str(zone_id) == "sky":
        h = min(h, 78.0)
    elif str(zone_id) == "road":
        h = min(max(h, 52.0), 82.0)
    elif str(zone_id) == "river":
        h = min(max(h, 46.0), 86.0)
    elif str(zone_id) == "land_above":
        h = min(h, 100.0)
    elif str(zone_id) == "land_below":
        h = min(float(size_max_px), max(h, 64.0))
    if str(object_type) in ROAD_OBJECT_TYPES:
        h = min(h, 82.0)
    if str(object_type) in RIVER_OBJECT_TYPES:
        h = min(h, 86.0)
    if str(object_type) in SKY_OBJECT_TYPES:
        h = min(h, 78.0)
    w = max(32.0, h * aspect)
    x = float(rng.uniform(42.0, max(44.0, float(width) - w - 42.0)))
    if str(zone_id) == "sky":
        low = 42.0
        high = max(low + 1.0, float(land_top_y) - h - 36.0)
        y = float(rng.uniform(low, high))
    elif str(zone_id) == "road" and road is not None:
        path_y = _interpolate_path_y(road.path_points, x + 0.5 * w)
        y = path_y - 0.60 * h + float(rng.uniform(-7.0, 7.0))
    elif str(zone_id) == "river" and river is not None:
        path_y = _interpolate_path_y(river.path_points, x + 0.5 * w)
        y = path_y - 0.50 * h + float(rng.uniform(-9.0, 9.0))
    else:
        feature = road if road is not None else river
        if feature is not None:
            path_y = _interpolate_path_y(feature.path_points, x + 0.5 * w)
            if str(zone_id) == "land_above":
                low = max(42.0, float(land_top_y) + 18.0)
                high = max(low + 1.0, path_y - h - 48.0)
                y = float(rng.uniform(low, high))
            else:
                low = min(float(height) - h - 48.0, path_y + 58.0)
                high = max(low + 1.0, float(height) - h - 42.0)
                y = float(rng.uniform(low, high))
        else:
            y = float(rng.uniform(max(42.0, float(land_top_y) + 18.0), max(88.0, float(height) - h - 46.0)))
    return (float(x), float(y), float(x) + float(w), float(y) + float(h))


def _candidate_respects_zone(
    candidate: BBox,
    *,
    zone_id: str,
    road: EnvironmentFeature | None,
    river: EnvironmentFeature | None,
) -> bool:
    cx, cy = _object_center(candidate)
    h = max(1.0, float(candidate[3]) - float(candidate[1]))
    top = float(candidate[1])
    bottom = float(candidate[3])
    if str(zone_id) == "sky":
        for feature in (road, river):
            if feature is None:
                continue
            path_y = _interpolate_path_y(feature.path_points, cx)
            if bottom >= path_y - 0.5 * float(feature.width_px):
                return False
        return True
    if str(zone_id) == "road":
        if road is None:
            return False
        road_y = _interpolate_path_y(road.path_points, cx)
        return abs(float(cy) - float(road_y)) <= 0.55 * float(road.width_px)
    if str(zone_id) == "river":
        if river is None:
            return False
        river_y = _interpolate_path_y(river.path_points, cx)
        return abs(float(cy) - float(river_y)) <= 0.58 * float(river.width_px)
    clearance = max(18.0, 0.18 * h)
    for feature in (road, river):
        if feature is None:
            continue
        path_y = _interpolate_path_y(feature.path_points, cx)
        feature_top = float(path_y) - 0.5 * float(feature.width_px) - clearance
        feature_bottom = float(path_y) + 0.5 * float(feature.width_px) + clearance
        if bottom >= feature_top and top <= feature_bottom:
            return False
    return True


def _sample_object_placements(
    *,
    rng,
    theme_id: str,
    features: Sequence[EnvironmentFeature],
    object_count: int,
    width: int,
    height: int,
    size_min_px: int,
    size_max_px: int,
    min_gap_px: int,
    max_overlap_fraction: float,
    placement_max_attempts: int,
    style_weights: Mapping[str, float],
    protected_bboxes: Sequence[BBox] = (),
    zone_count_overrides: Mapping[str, int] | None = None,
    land_top_y_override: float | None = None,
    zone_bias: Mapping[str, float] | None = None,
) -> Tuple[EnvironmentObjectPlacement, ...]:
    road = next((feature for feature in features if feature.feature_type == "road"), None)
    river = next((feature for feature in features if feature.feature_type == "river"), None)
    feature_types = {str(feature.feature_type) for feature in features}
    forced_zones: List[str | None] = []
    exact_zones: set[str] = set()
    if zone_count_overrides:
        valid_zones = {"sky", "land_above", "land_below", "road", "river"}
        for zone_id, count in sorted(zone_count_overrides.items()):
            zone = str(zone_id)
            if zone not in valid_zones:
                raise ValueError(f"unsupported forced environment zone: {zone}")
            if zone in {"road", "river"} and zone not in feature_types:
                raise ValueError(f"cannot force {zone} placements when the scene has no {zone}")
            exact_zones.add(zone)
            forced_zones.extend([zone] * max(0, int(count)))
    if len(forced_zones) > int(object_count):
        raise ValueError("forced environment zone counts exceed object_count")
    forced_zones.extend([None] * max(0, int(object_count) - len(forced_zones)))
    rng.shuffle(forced_zones)
    land_top = float(land_top_y_override) if land_top_y_override is not None else _land_top_y(str(theme_id), int(height))
    placements: List[EnvironmentObjectPlacement] = []
    existing: List[BBox] = []
    protected = [tuple(float(v) for v in box) for box in protected_bboxes]
    protected.extend(
        feature.bbox_xyxy
        for feature in features
        if feature.feature_type in {"bridge", "crosswalk"}
    )
    for index in range(int(object_count)):
        placed = False
        forced_zone = forced_zones[index] if index < len(forced_zones) else None
        for attempt in range(max(1, int(placement_max_attempts))):
            shrink = 0.94 ** max(0, int(attempt) // 60)
            attempt_size_max = max(44, int(round(float(size_max_px) * float(shrink))))
            attempt_size_min = min(
                attempt_size_max,
                max(34, int(round(float(size_min_px) * float(shrink)))),
            )
            attempt_gap = max(2.0, float(min_gap_px) * (0.90 ** max(0, int(attempt) // 80)))
            if forced_zone is not None:
                zone_id = str(forced_zone)
            else:
                zone_id = _zone_for_theme(rng, str(theme_id), features, zone_bias=zone_bias)
                if exact_zones:
                    for _ in range(16):
                        if zone_id not in exact_zones:
                            break
                        zone_id = _zone_for_theme(rng, str(theme_id), features, zone_bias=zone_bias)
                    if zone_id in exact_zones:
                        fallback_zones = ["sky", "land_above", "land_below"]
                        if "road" in feature_types:
                            fallback_zones.append("road")
                        if "river" in feature_types:
                            fallback_zones.append("river")
                        candidates = [zone for zone in fallback_zones if zone not in exact_zones]
                        if not candidates:
                            raise ValueError("no available non-forced environment zones")
                        zone_id = str(rng.choice(candidates))
            object_type = _sample_object_type(rng, zone_id, str(theme_id))
            candidate = _candidate_box_for_zone(
                rng=rng,
                zone_id=zone_id,
                object_type=object_type,
                width=int(width),
                height=int(height),
                road=road,
                river=river,
                land_top_y=float(land_top),
                size_min_px=int(attempt_size_min),
                size_max_px=int(attempt_size_max),
            )
            if candidate[1] < 18.0 or candidate[3] > float(height) - 18.0:
                continue
            if not _candidate_respects_zone(candidate, zone_id=zone_id, road=road, river=river):
                continue
            collision_boxes = [*existing, *protected]
            collision_gap = float(attempt_gap)
            if str(zone_id) == "sky":
                roof_clearance = 34.0 if str(theme_id) in {"canal_city", "skyline_street"} else 24.0
                collision_gap = max(collision_gap, roof_clearance)
            if not _fits(
                collision_boxes,
                candidate,
                min_gap_px=float(collision_gap),
                max_overlap_fraction=float(max_overlap_fraction),
            ):
                continue
            primary, accent = choose_object_colors(rng, object_type)
            placements.append(
                EnvironmentObjectPlacement(
                    object_id=f"env_obj_{index:02d}",
                    object_type=object_type,
                    bbox_xyxy=tuple(float(v) for v in candidate),
                    zone_id=str(zone_id),
                    primary_color_rgb=primary,
                    accent_color_rgb=accent,
                    style_id=_choose_zone_style(rng, style_weights, zone_id),
                    relations=_build_feature_relations(candidate, features),
                )
            )
            existing.append(candidate)
            placed = True
            break
        if not placed:
            raise ValueError("could not place all environment illustration objects")
    return tuple(placements)


def render_environment_object_scene(
    *,
    rng,
    canvas_width: int = 1280,
    canvas_height: int = 840,
    object_count: int = 14,
    render_scale: int = 2,
    theme_weights: Mapping[str, float] | None = None,
    style_weights: Mapping[str, float] | None = None,
    object_size_min_px: int = 62,
    object_size_max_px: int = 116,
    min_gap_px: int = 6,
    max_overlap_fraction: float = 0.02,
    placement_max_attempts: int = 420,
    skyline_building_min: int = 7,
    skyline_building_max: int = 14,
    bridge_count_override: int | None = None,
    crosswalk_count_override: int | None = None,
    zone_count_overrides: Mapping[str, int] | None = None,
    lit_window_count_override: int | None = None,
) -> RenderedEnvironmentObjectScene:
    """Render one rich environment illustration with roads/rivers/buildings."""

    width = int(canvas_width)
    height = int(canvas_height)
    scale = max(1, int(render_scale))
    theme_id = _choose_theme(rng, theme_weights or {theme: 1.0 for theme in ENVIRONMENT_THEME_IDS})
    effective_object_count = effective_environment_object_count(theme_id, int(object_count))
    scene_style_id = _choose_style(rng, style_weights or {style: 1.0 for style in STYLE_IDS})
    layout = _sample_environment_layout(rng, theme_id=theme_id, width=width, height=height)
    land_top = _layout_float(layout, "land_top_y", _land_top_y(theme_id, height))
    image = Image.new("RGB", (width * scale, height * scale), (247, 248, 251))
    draw = ImageDraw.Draw(image)
    _draw_background(draw, theme_id=theme_id, width=width, height=height, scale=scale, layout=layout)

    features: List[EnvironmentFeature] = list(
        _draw_sky_decor(draw, rng=rng, theme_id=theme_id, width=width, height=height, scale=scale, land_top_y=land_top)
    )
    buildings: Tuple[EnvironmentBuilding, ...] = ()
    has_river = theme_id in {"river_meadow", "road_and_river", "canal_city"}
    has_road = theme_id in {"park_road", "road_and_river", "skyline_street"}
    has_skyline = theme_id in {"canal_city", "skyline_street"}

    if has_skyline:
        horizon = _layout_float(layout, "building_horizon_y", 390.0 if theme_id == "skyline_street" else 350.0)
        buildings = _draw_buildings(
            draw,
            rng=rng,
            width=width,
            horizon_y=horizon,
            scale=scale,
            max_buildings=int(rng.randint(int(skyline_building_min), int(skyline_building_max))),
            lit_window_count_override=lit_window_count_override,
        )

    river_path: Tuple[Tuple[float, float], ...] | None = None
    road_path: Tuple[Tuple[float, float], ...] | None = None
    if has_river:
        river_base = _layout_float(layout, "river_base_y", 510.0 if theme_id != "canal_city" else 565.0)
        river_path = _sample_curve(
            rng,
            width=width,
            y_base=river_base,
            amplitude=_layout_float(layout, "river_amplitude_px", 42.0 if theme_id != "canal_city" else 30.0),
            phase=float(rng.uniform(0.0, 6.28)),
            jitter=11.0,
            point_count=15,
        )
        river = _draw_river(
            draw,
            path_points=river_path,
            width_px=_layout_float(layout, "river_width_px", 94.0 if theme_id == "canal_city" else 104.0),
            scale=scale,
        )
        features.append(river)
        if bridge_count_override is not None:
            bridge_count = max(0, int(bridge_count_override))
        else:
            bridge_count = 2 if theme_id == "canal_city" else int(rng.randint(1, 3))
        for bridge_index in range(bridge_count):
            bx = float(width) * float(bridge_index + 1) / float(bridge_count + 1) + float(rng.uniform(-55.0, 55.0))
            features.append(
                _draw_bridge(
                    draw,
                    bridge_id=f"bridge_{bridge_index:02d}",
                    river_path=river_path,
                    x=bx,
                    river_width=river.width_px,
                    scale=scale,
                )
            )

    if has_road:
        road_base = _layout_float(layout, "road_base_y", 612.0 if theme_id == "park_road" else 675.0)
        if theme_id == "road_and_river" and road_base <= 0.0:
            road_base = 305.0
        road_path = _sample_curve(
            rng,
            width=width,
            y_base=road_base,
            amplitude=_layout_float(layout, "road_amplitude_px", 48.0 if theme_id != "skyline_street" else 26.0),
            phase=float(rng.uniform(0.0, 6.28)),
            jitter=8.0,
            point_count=15,
        )
        road = _draw_road(
            draw,
            path_points=road_path,
            width_px=_layout_float(layout, "road_width_px", 94.0 if theme_id != "skyline_street" else 108.0),
            scale=scale,
        )
        features.append(road)
        if crosswalk_count_override is not None:
            crosswalk_count = max(0, int(crosswalk_count_override))
        else:
            crosswalk_count = 1 if theme_id == "skyline_street" else int(rng.randint(0, 2))
        for crosswalk_index in range(crosswalk_count):
            cx = float(width) * float(crosswalk_index + 1) / float(crosswalk_count + 1) + float(rng.uniform(-70.0, 70.0))
            features.append(
                _draw_crosswalk(
                    draw,
                    crosswalk_id=f"crosswalk_{crosswalk_index:02d}",
                    road_path=road_path,
                    x=cx,
                    road_width=road.width_px,
                    scale=scale,
                )
            )

    placements = _sample_object_placements(
        rng=rng,
        theme_id=theme_id,
        features=features,
        object_count=int(effective_object_count),
        width=width,
        height=height,
        size_min_px=int(object_size_min_px),
        size_max_px=int(object_size_max_px),
        min_gap_px=int(min_gap_px),
        max_overlap_fraction=float(max_overlap_fraction),
        placement_max_attempts=int(placement_max_attempts),
        style_weights=style_weights or {style: 1.0 for style in STYLE_IDS},
        protected_bboxes=[building.bbox_xyxy for building in buildings],
        zone_count_overrides=zone_count_overrides,
        land_top_y_override=land_top,
        zone_bias=layout.get("zone_bias", {}),
    )
    rendered_objects = []
    for placement in placements:
        rendered_objects.append(
            draw_illustration_object(
                draw,
                object_id=placement.object_id,
                object_type=placement.object_type,
                bbox_xyxy=placement.bbox_xyxy,
                primary_color_rgb=placement.primary_color_rgb,
                accent_color_rgb=placement.accent_color_rgb,
                style_id=placement.style_id,
                render_scale=scale,
                gender_id=sample_person_gender(rng) if family_for_object(str(placement.object_type)) == "person" else None,
            )
        )
    if scale != 1:
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    return RenderedEnvironmentObjectScene(
        image=image,
        theme_id=str(theme_id),
        features=tuple(features),
        buildings=tuple(buildings),
        objects=tuple(rendered_objects),
        placements=tuple(placements),
        canvas_width=width,
        canvas_height=height,
        render_scale=scale,
        style_id=str(scene_style_id),
        layout=dict(layout),
    )


def environment_scene_entities(scene: RenderedEnvironmentObjectScene) -> List[Dict[str, Any]]:
    """Return scene IR entities for environment features, buildings, objects, and parts."""

    entities: List[Dict[str, Any]] = []
    for feature in scene.features:
        object_record = make_object_record(
            object_id=str(feature.feature_id),
            object_type="environment_feature",
            bbox_xyxy=feature.bbox_xyxy,
            semantic_attributes={
                "feature_type": str(feature.feature_type),
                **dict(feature.attributes),
            },
            visual_attributes={"width_px": round(float(feature.width_px), 3)},
            source_entity_type="environment_feature",
        ).as_dict()
        entities.append(
            {
                "entity_id": str(feature.feature_id),
                "entity_type": "environment_feature",
                "feature_type": str(feature.feature_type),
                "bbox": [round(float(v), 3) for v in feature.bbox_xyxy],
                "path_points": [[round(float(x), 3), round(float(y), 3)] for x, y in feature.path_points],
                "width_px": round(float(feature.width_px), 3),
                "attributes": dict(feature.attributes),
                "object_record": object_record,
            }
        )
    for building in scene.buildings:
        object_record = make_object_record(
            object_id=str(building.building_id),
            object_type="building",
            bbox_xyxy=building.bbox_xyxy,
            semantic_attributes={
                "roof_type": str(building.roof_type),
                "window_count": len(building.window_bboxes),
                "lit_window_count": len(building.lit_window_bboxes),
                **dict(building.attributes),
            },
            source_entity_type="environment_building",
        ).as_dict()
        entities.append(
            {
                "entity_id": str(building.building_id),
                "entity_type": "environment_building",
                "bbox": [round(float(v), 3) for v in building.bbox_xyxy],
                "roof_type": str(building.roof_type),
                "window_bboxes": [[round(float(v), 3) for v in box] for box in building.window_bboxes],
                "lit_window_bboxes": [[round(float(v), 3) for v in box] for box in building.lit_window_bboxes],
                "door_bbox": [round(float(v), 3) for v in building.door_bbox] if building.door_bbox else None,
                "attributes": dict(building.attributes),
                "object_record": object_record,
            }
        )
    placement_map = {placement.object_id: placement for placement in scene.placements}
    for rendered in scene.objects:
        serialized = serialize_object(rendered)
        placement = placement_map.get(str(serialized["object_id"]))
        entities.append(
            {
                "entity_id": serialized["object_id"],
                "entity_type": "illustration_object",
                "object_type": serialized["object_type"],
                "family": serialized["family"],
                "bbox": serialized["bbox"],
                "zone_id": placement.zone_id if placement else None,
                "relations": dict(placement.relations) if placement else {},
                "attributes": serialized["attributes"],
                "object_record": serialized["object_record"],
            }
        )
        for part in serialized["parts"]:
            entities.append(
                {
                    "entity_id": part["part_id"],
                    "entity_type": "illustration_part",
                    "part_kind": part["part_kind"],
                    "parent_object_id": serialized["object_id"],
                    "bbox": part["bbox"],
                    "attributes": dict(part["attributes"]),
                }
            )
    return entities


def serialize_environment_scene(scene: RenderedEnvironmentObjectScene) -> Dict[str, Any]:
    """Return a compact trace payload for smoke tests and future task generators."""

    return {
        "scene_id": "environment",
        "theme_id": str(scene.theme_id),
        "canvas_size": [int(scene.canvas_width), int(scene.canvas_height)],
        "render_scale": int(scene.render_scale),
        "style_id": str(scene.style_id),
        "layout": dict(scene.layout),
        "feature_ids": [str(feature.feature_id) for feature in scene.features],
        "building_ids": [str(building.building_id) for building in scene.buildings],
        "object_ids": [str(placement.object_id) for placement in scene.placements],
        "entities": environment_scene_entities(scene),
    }


__all__ = [
    "ENVIRONMENT_THEME_IDS",
    "EnvironmentBuilding",
    "EnvironmentFeature",
    "EnvironmentObjectPlacement",
    "LAND_OBJECT_TYPES",
    "RenderedEnvironmentObjectScene",
    "RIVER_OBJECT_TYPES",
    "ROAD_OBJECT_TYPES",
    "SKY_OBJECT_TYPES",
    "THEME_LAND_OBJECT_TYPES",
    "effective_environment_object_count",
    "environment_scene_entities",
    "render_environment_object_scene",
    "serialize_environment_scene",
]
