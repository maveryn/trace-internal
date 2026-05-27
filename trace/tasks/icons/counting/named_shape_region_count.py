"""Count prompt-named procedural icons inside or outside visible regions."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.weighted_sampling import sample_weighted_value, weighted_probability_map
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.icon_noise import serialize_icon_noise_edits
from ..shared.icon_scene import (
    BBox,
    draw_single_panel,
    max_overlap_with_existing,
    resolve_single_panel_layout,
    single_panel_geometry_to_trace,
    sort_bboxes_reading_order,
)
from ..shared.icon_style import sample_icon_palette
from ..shared.icon_task_rendering import icon_render_style_trace, resolve_icon_render_params, sample_icon_instance_noise
from ..shared.procedural_named_icon_field_scene import (
    SCENE_ID,
    bbox_center_float,
    bbox_from_center_and_size,
    resolve_named_icon_fill_style_probabilities,
    resolve_named_icon_fill_style_support,
    resolve_named_icon_int_bounds,
    rotation_for_named_shape,
    uniform_string_probability_map,
)
from ..shared.procedural_named_icons import (
    PROCEDURAL_NAMED_ICON_FILL_STYLES,
    PROCEDURAL_NAMED_ICON_SHAPES,
    procedural_named_icon_display_name,
    procedural_named_icon_fill_style_probability_map,
    render_procedural_named_icon_rgba,
    sample_procedural_named_icon_fill_style,
    validate_procedural_named_icon_fill_style_support,
)


TASK_ID = "task_icons__named_field__region_shape_count"

QUERY_IDS: Tuple[str, ...] = (
    "inside_shape_count",
    "outside_shape_count",
    "inside_band_count",
    "outside_band_count",
    "inside_quadrant_count",
    "inside_shelf_count",
)

_INSIDE_QUERY_IDS = {
    "inside_shape_count",
    "inside_band_count",
    "inside_quadrant_count",
    "inside_shelf_count",
}


@dataclass(frozen=True)
class _TaskDefaults:
    object_count_min: int = 10
    object_count_max: int = 18
    target_count_min: int = 1
    target_count_max: int = 6
    target_opposite_count_min: int = 1
    target_opposite_count_max: int = 3
    canvas_width: int = 800
    canvas_height: int = 480
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = 48
    scene_icon_size_max_px: int = 96
    scene_max_overlap_fraction: float = 0.0
    scene_placement_max_attempts: int = 160
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    reference_panel_width_px: int = ICON_SHARED_DEFAULTS.reference_panel_width_px
    reference_icon_size_px: int = ICON_SHARED_DEFAULTS.reference_icon_size_px
    panel_gap_px: int = ICON_SHARED_DEFAULTS.panel_gap_px
    palette_size_min: int = 8
    palette_size_max: int = 12
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 40.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = ICON_SHARED_DEFAULTS.icon_noise_edit_count_range
    region_shape_kinds: Tuple[str, ...] = ("rectangle", "ellipse")
    band_kinds: Tuple[str, ...] = ("vertical", "horizontal", "slanted_positive", "slanted_negative")
    quadrant_ids: Tuple[str, ...] = ("top_left", "top_right", "bottom_left", "bottom_right")
    shelf_count_min: int = 3
    shelf_count_max: int = 4
    region_boundary_margin_px: int = 18
    region_fill_rgb: Tuple[int, int, int] = (255, 226, 105)
    region_outline_rgb: Tuple[int, int, int] = (49, 103, 191)
    region_guide_rgb: Tuple[int, int, int] = (154, 164, 180)
    region_fill_alpha: int = 54
    region_outline_width_px: int = 3
    named_icon_fill_style_support: Tuple[str, ...] = PROCEDURAL_NAMED_ICON_FILL_STYLES


@dataclass(frozen=True)
class _RegionSpec:
    query_id: str
    region_kind: str
    counts_inside: bool
    shape_kind: str = ""
    band_kind: str = ""
    quadrant_id: str = ""
    shelf_index: int = -1
    shelf_count: int = 0
    bbox_xyxy: Tuple[int, int, int, int] | None = None
    ellipse_center_xy: Tuple[float, float] | None = None
    ellipse_radii_xy: Tuple[float, float] | None = None
    band_normal_xy: Tuple[float, float] | None = None
    band_center_distance: float | None = None
    band_half_width_px: float | None = None
    band_polygon_xy: Tuple[Tuple[float, float], ...] = ()


@dataclass(frozen=True)
class _IconPlan:
    shape_id: str
    desired_inside_region: bool
    is_target_shape: bool


@dataclass(frozen=True)
class _RenderedRegionIcon:
    instance_id: str
    shape_id: str
    shape_name: str
    bbox_xyxy: Tuple[int, int, int, int]
    center_xy: Tuple[float, float]
    nominal_size_px: int
    rotation_degrees: int
    tint_rgb: Tuple[int, int, int]
    fill_style: str
    inside_region: bool
    counted: bool
    noise_edits: Tuple[Dict[str, Any], ...]
    noise_seed: int | None


@dataclass(frozen=True)
class _ScenePayload:
    image: Image.Image
    panel_geometry: Dict[str, Any]
    region: _RegionSpec
    target_shape_id: str
    target_shape_name: str
    target_count: int
    object_count: int
    instances: Tuple[_RenderedRegionIcon, ...]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    query_probabilities: Dict[str, float]
    shape_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    object_count_probabilities: Dict[str, float]
    fill_style_support: Tuple[str, ...]
    fill_style_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)



def _int_default(params: Mapping[str, Any], defaults: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(key, group_default(defaults, key, fallback)))


def _rgb_default(params: Mapping[str, Any], defaults: Mapping[str, Any], key: str, fallback: Sequence[int]) -> Tuple[int, int, int]:
    raw = params.get(key, group_default(defaults, key, tuple(fallback)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or len(raw) < 3:
        raw = tuple(fallback)
    return tuple(int(value) for value in raw[:3])


def _shape_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("shape_id_support", group_default(_GEN_DEFAULTS, "shape_id_support", PROCEDURAL_NAMED_ICON_SHAPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("shape_id_support must be a sequence")
    values = tuple(str(value) for value in raw)
    unsupported = sorted(set(values) - set(PROCEDURAL_NAMED_ICON_SHAPES))
    if unsupported:
        raise ValueError(f"unsupported procedural named icon shapes: {unsupported}")
    support = tuple(dict.fromkeys(values))
    if len(support) < 5:
        raise ValueError("shape_id_support must include at least five shapes")
    return support


def _query_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("named_region_query_ids", group_default(_GEN_DEFAULTS, "named_region_query_ids", QUERY_IDS))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("named_region_query_ids must be a sequence")
    values = tuple(dict.fromkeys(str(value) for value in raw if str(value).strip()))
    unsupported = sorted(set(values) - set(QUERY_IDS))
    if unsupported:
        raise ValueError(f"unsupported named-region query ids: {unsupported}")
    if not values:
        raise ValueError("named_region_query_ids resolved no query ids")
    return values




def _string_support(
    params: Mapping[str, Any],
    *,
    key: str,
    fallback: Sequence[str],
    allowed: Sequence[str],
) -> Tuple[str, ...]:
    raw = params.get(key, group_default(_GEN_DEFAULTS, key, tuple(fallback)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raw = tuple(fallback)
    values = tuple(dict.fromkeys(str(value) for value in raw if str(value).strip()))
    unsupported = sorted(set(values) - set(allowed))
    if unsupported:
        raise ValueError(f"unsupported {key}: {unsupported}")
    if not values:
        raise ValueError(f"{key} resolved no values")
    return values






def _region_to_trace(region: _RegionSpec) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "query_id": str(region.query_id),
        "region_kind": str(region.region_kind),
        "counts_inside": bool(region.counts_inside),
        "shape_kind": str(region.shape_kind),
        "band_kind": str(region.band_kind),
        "quadrant_id": str(region.quadrant_id),
        "shelf_index": int(region.shelf_index),
        "shelf_count": int(region.shelf_count),
    }
    if region.bbox_xyxy is not None:
        payload["bbox_xyxy"] = [int(value) for value in region.bbox_xyxy]
    if region.ellipse_center_xy is not None:
        payload["ellipse_center_xy"] = [float(value) for value in region.ellipse_center_xy]
    if region.ellipse_radii_xy is not None:
        payload["ellipse_radii_xy"] = [float(value) for value in region.ellipse_radii_xy]
    if region.band_normal_xy is not None:
        payload["band_normal_xy"] = [float(value) for value in region.band_normal_xy]
    if region.band_center_distance is not None:
        payload["band_center_distance"] = float(region.band_center_distance)
    if region.band_half_width_px is not None:
        payload["band_half_width_px"] = float(region.band_half_width_px)
    if region.band_polygon_xy:
        payload["band_polygon_xy"] = [[float(x), float(y)] for x, y in region.band_polygon_xy]
    return payload


def _point_inside_region(region: _RegionSpec, center_xy: Sequence[float]) -> bool:
    cx, cy = float(center_xy[0]), float(center_xy[1])
    if region.region_kind in {"shape", "quadrant", "shelf"}:
        if region.shape_kind == "ellipse":
            if region.ellipse_center_xy is None or region.ellipse_radii_xy is None:
                raise ValueError("ellipse region is missing center/radii")
            ex, ey = region.ellipse_center_xy
            rx, ry = region.ellipse_radii_xy
            return ((cx - float(ex)) / max(1e-6, float(rx))) ** 2 + ((cy - float(ey)) / max(1e-6, float(ry))) ** 2 <= 1.0
        if region.bbox_xyxy is None:
            raise ValueError("box-like region is missing bbox")
        x0, y0, x1, y1 = [float(value) for value in region.bbox_xyxy]
        return x0 <= cx <= x1 and y0 <= cy <= y1
    if region.region_kind == "band":
        if region.band_normal_xy is None or region.band_center_distance is None or region.band_half_width_px is None:
            raise ValueError("band region is missing normal/center/width")
        nx, ny = region.band_normal_xy
        distance = abs((float(cx) * float(nx)) + (float(cy) * float(ny)) - float(region.band_center_distance))
        return distance <= float(region.band_half_width_px)
    raise ValueError(f"unsupported region kind: {region.region_kind}")


def _point_safely_matches_region(
    region: _RegionSpec,
    center_xy: Sequence[float],
    *,
    desired_inside: bool,
    margin_px: int,
) -> bool:
    cx, cy = float(center_xy[0]), float(center_xy[1])
    margin = float(max(0, int(margin_px)))
    if region.region_kind in {"shape", "quadrant", "shelf"}:
        if region.shape_kind == "ellipse":
            if region.ellipse_center_xy is None or region.ellipse_radii_xy is None:
                raise ValueError("ellipse region is missing center/radii")
            ex, ey = region.ellipse_center_xy
            rx, ry = region.ellipse_radii_xy
            scale_margin = margin / max(1.0, min(float(rx), float(ry)))
            value = ((cx - float(ex)) / max(1e-6, float(rx))) ** 2 + ((cy - float(ey)) / max(1e-6, float(ry))) ** 2
            if bool(desired_inside):
                return value <= max(0.0, (1.0 - scale_margin) ** 2)
            return value >= (1.0 + scale_margin) ** 2
        if region.bbox_xyxy is None:
            raise ValueError("box-like region is missing bbox")
        x0, y0, x1, y1 = [float(value) for value in region.bbox_xyxy]
        if bool(desired_inside):
            return x0 + margin <= cx <= x1 - margin and y0 + margin <= cy <= y1 - margin
        return cx <= x0 - margin or cx >= x1 + margin or cy <= y0 - margin or cy >= y1 + margin
    if region.region_kind == "band":
        if region.band_normal_xy is None or region.band_center_distance is None or region.band_half_width_px is None:
            raise ValueError("band region is missing normal/center/width")
        nx, ny = region.band_normal_xy
        distance = abs((float(cx) * float(nx)) + (float(cy) * float(ny)) - float(region.band_center_distance))
        if bool(desired_inside):
            return distance <= max(0.0, float(region.band_half_width_px) - margin)
        return distance >= float(region.band_half_width_px) + margin
    raise ValueError(f"unsupported region kind: {region.region_kind}")


def _bbox_corners(box: Sequence[int | float]) -> Tuple[Tuple[float, float], ...]:
    x0, y0, x1, y1 = [float(value) for value in box]
    return ((x0, y0), (x1, y0), (x1, y1), (x0, y1))


def _bbox_safely_matches_region(
    region: _RegionSpec,
    bbox_xyxy: Sequence[int | float],
    *,
    desired_inside: bool,
    margin_px: int,
) -> bool:
    x0, y0, x1, y1 = [float(value) for value in bbox_xyxy]
    margin = float(max(0, int(margin_px)))
    if region.region_kind in {"shape", "quadrant", "shelf"}:
        if region.shape_kind == "ellipse":
            if region.ellipse_center_xy is None or region.ellipse_radii_xy is None:
                raise ValueError("ellipse region is missing center/radii")
            ex, ey = region.ellipse_center_xy
            rx, ry = region.ellipse_radii_xy
            scale_margin = margin / max(1.0, min(float(rx), float(ry)))
            if bool(desired_inside):
                threshold = max(0.0, (1.0 - scale_margin) ** 2)
                return all(
                    ((float(cx) - float(ex)) / max(1e-6, float(rx))) ** 2
                    + ((float(cy) - float(ey)) / max(1e-6, float(ry))) ** 2
                    <= threshold
                    for cx, cy in _bbox_corners(bbox_xyxy)
                )
            nearest_x = min(max(float(ex), float(x0)), float(x1))
            nearest_y = min(max(float(ey), float(y0)), float(y1))
            value = ((float(nearest_x) - float(ex)) / max(1e-6, float(rx))) ** 2 + (
                (float(nearest_y) - float(ey)) / max(1e-6, float(ry))
            ) ** 2
            return value >= (1.0 + scale_margin) ** 2
        if region.bbox_xyxy is None:
            raise ValueError("box-like region is missing bbox")
        rx0, ry0, rx1, ry1 = [float(value) for value in region.bbox_xyxy]
        if bool(desired_inside):
            return rx0 + margin <= x0 and x1 <= rx1 - margin and ry0 + margin <= y0 and y1 <= ry1 - margin
        return x1 <= rx0 - margin or x0 >= rx1 + margin or y1 <= ry0 - margin or y0 >= ry1 + margin
    if region.region_kind == "band":
        if region.band_normal_xy is None or region.band_center_distance is None or region.band_half_width_px is None:
            raise ValueError("band region is missing normal/center/width")
        nx, ny = region.band_normal_xy
        signed_distances = [
            (float(cx) * float(nx)) + (float(cy) * float(ny)) - float(region.band_center_distance)
            for cx, cy in _bbox_corners(bbox_xyxy)
        ]
        lower = min(float(value) for value in signed_distances)
        upper = max(float(value) for value in signed_distances)
        half_width = float(region.band_half_width_px)
        if bool(desired_inside):
            return lower >= -half_width + margin and upper <= half_width - margin
        return lower >= half_width + margin or upper <= -half_width - margin
    raise ValueError(f"unsupported region kind: {region.region_kind}")


def _sample_box_region(rng, *, query_id: str, content_bbox: BBox, shape_kind: str) -> _RegionSpec:
    x0, y0, x1, y1 = [int(value) for value in content_bbox]
    width = int(x1 - x0)
    height = int(y1 - y0)
    box_w = int(round(float(width) * float(rng.uniform(0.36, 0.56))))
    box_h = int(round(float(height) * float(rng.uniform(0.38, 0.62))))
    box_x0 = int(rng.randint(int(x0 + 18), int(max(x0 + 18, x1 - box_w - 18))))
    box_y0 = int(rng.randint(int(y0 + 16), int(max(y0 + 16, y1 - box_h - 16))))
    bbox = (int(box_x0), int(box_y0), int(box_x0 + box_w), int(box_y0 + box_h))
    center = bbox_center_float(bbox)
    return _RegionSpec(
        query_id=str(query_id),
        region_kind="shape",
        counts_inside=str(query_id) in _INSIDE_QUERY_IDS,
        shape_kind=str(shape_kind),
        bbox_xyxy=bbox,
        ellipse_center_xy=center if str(shape_kind) == "ellipse" else None,
        ellipse_radii_xy=(0.5 * float(box_w), 0.5 * float(box_h)) if str(shape_kind) == "ellipse" else None,
    )


def _band_normal(kind: str) -> Tuple[float, float]:
    if str(kind) == "vertical":
        return (1.0, 0.0)
    if str(kind) == "horizontal":
        return (0.0, 1.0)
    if str(kind) == "slanted_positive":
        return (math.sqrt(0.5), -math.sqrt(0.5))
    if str(kind) == "slanted_negative":
        return (math.sqrt(0.5), math.sqrt(0.5))
    raise ValueError(f"unsupported band kind: {kind}")


def _sample_band_region(rng, *, query_id: str, content_bbox: BBox, band_kind: str) -> _RegionSpec:
    x0, y0, x1, y1 = [float(value) for value in content_bbox]
    width = float(x1 - x0)
    height = float(y1 - y0)
    nx, ny = _band_normal(str(band_kind))
    corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    values = [(float(x) * float(nx)) + (float(y) * float(ny)) for x, y in corners]
    min_value = min(values)
    max_value = max(values)
    span = max(1.0, float(max_value - min_value))
    half_width = float(rng.uniform(0.13, 0.20)) * min(width, height)
    center_min = min_value + (0.32 * span)
    center_max = max_value - (0.32 * span)
    center_distance = float(rng.uniform(center_min, center_max)) if center_min < center_max else 0.5 * (min_value + max_value)
    tx, ty = -float(ny), float(nx)
    base_x = float(nx) * float(center_distance)
    base_y = float(ny) * float(center_distance)
    line_half_len = 2.0 * math.hypot(width, height)
    polygon = (
        (base_x - float(nx) * half_width - tx * line_half_len, base_y - float(ny) * half_width - ty * line_half_len),
        (base_x - float(nx) * half_width + tx * line_half_len, base_y - float(ny) * half_width + ty * line_half_len),
        (base_x + float(nx) * half_width + tx * line_half_len, base_y + float(ny) * half_width + ty * line_half_len),
        (base_x + float(nx) * half_width - tx * line_half_len, base_y + float(ny) * half_width - ty * line_half_len),
    )
    return _RegionSpec(
        query_id=str(query_id),
        region_kind="band",
        counts_inside=str(query_id) in _INSIDE_QUERY_IDS,
        band_kind=str(band_kind),
        band_normal_xy=(float(nx), float(ny)),
        band_center_distance=float(center_distance),
        band_half_width_px=float(half_width),
        band_polygon_xy=tuple((float(x), float(y)) for x, y in polygon),
    )


def _sample_quadrant_region(rng, *, query_id: str, content_bbox: BBox, quadrant_id: str) -> _RegionSpec:
    x0, y0, x1, y1 = [int(value) for value in content_bbox]
    xm = int(round(0.5 * float(x0 + x1)))
    ym = int(round(0.5 * float(y0 + y1)))
    quadrant_to_bbox = {
        "top_left": (x0, y0, xm, ym),
        "top_right": (xm, y0, x1, ym),
        "bottom_left": (x0, ym, xm, y1),
        "bottom_right": (xm, ym, x1, y1),
    }
    bbox = quadrant_to_bbox[str(quadrant_id)]
    return _RegionSpec(
        query_id=str(query_id),
        region_kind="quadrant",
        counts_inside=True,
        shape_kind="rectangle",
        quadrant_id=str(quadrant_id),
        bbox_xyxy=tuple(int(value) for value in bbox),
    )


def _sample_shelf_region(rng, *, query_id: str, content_bbox: BBox, shelf_count_min: int, shelf_count_max: int) -> _RegionSpec:
    x0, y0, x1, y1 = [int(value) for value in content_bbox]
    shelf_count = int(rng.randint(int(shelf_count_min), int(shelf_count_max)))
    shelf_index = int(rng.randrange(0, int(shelf_count)))
    shelf_h = float(y1 - y0) / float(max(1, int(shelf_count)))
    sy0 = int(round(float(y0) + float(shelf_index) * shelf_h))
    sy1 = int(round(float(y0) + float(shelf_index + 1) * shelf_h))
    return _RegionSpec(
        query_id=str(query_id),
        region_kind="shelf",
        counts_inside=True,
        shape_kind="rectangle",
        shelf_index=int(shelf_index),
        shelf_count=int(shelf_count),
        bbox_xyxy=(int(x0), int(sy0), int(x1), int(sy1)),
    )


def _sample_region(
    *,
    rng,
    query_id: str,
    content_bbox: BBox,
    params: Mapping[str, Any],
) -> _RegionSpec:
    if str(query_id) in {"inside_shape_count", "outside_shape_count"}:
        shape_support = _string_support(
            params,
            key="region_shape_kinds",
            fallback=_DEFAULTS.region_shape_kinds,
            allowed=("rectangle", "ellipse"),
        )
        explicit = params.get("region_shape_kind")
        shape_kind = str(explicit) if explicit is not None else str(rng.choice(shape_support))
        if shape_kind not in set(shape_support):
            raise ValueError(f"region_shape_kind must be one of {shape_support}")
        return _sample_box_region(rng, query_id=str(query_id), content_bbox=content_bbox, shape_kind=str(shape_kind))
    if str(query_id) in {"inside_band_count", "outside_band_count"}:
        band_support = _string_support(
            params,
            key="band_kinds",
            fallback=_DEFAULTS.band_kinds,
            allowed=("vertical", "horizontal", "slanted_positive", "slanted_negative"),
        )
        explicit = params.get("band_kind")
        band_kind = str(explicit) if explicit is not None else str(rng.choice(band_support))
        if band_kind not in set(band_support):
            raise ValueError(f"band_kind must be one of {band_support}")
        return _sample_band_region(rng, query_id=str(query_id), content_bbox=content_bbox, band_kind=str(band_kind))
    if str(query_id) == "inside_quadrant_count":
        quadrant_support = _string_support(
            params,
            key="quadrant_ids",
            fallback=_DEFAULTS.quadrant_ids,
            allowed=("top_left", "top_right", "bottom_left", "bottom_right"),
        )
        explicit = params.get("quadrant_id")
        quadrant_id = str(explicit) if explicit is not None else str(rng.choice(quadrant_support))
        if quadrant_id not in set(quadrant_support):
            raise ValueError(f"quadrant_id must be one of {quadrant_support}")
        return _sample_quadrant_region(rng, query_id=str(query_id), content_bbox=content_bbox, quadrant_id=str(quadrant_id))
    if str(query_id) == "inside_shelf_count":
        shelf_min = _int_default(params, _GEN_DEFAULTS, "shelf_count_min", _DEFAULTS.shelf_count_min)
        shelf_max = _int_default(params, _GEN_DEFAULTS, "shelf_count_max", _DEFAULTS.shelf_count_max)
        if shelf_min <= 0 or shelf_max < shelf_min:
            raise ValueError("invalid shelf_count_min/shelf_count_max")
        return _sample_shelf_region(
            rng,
            query_id=str(query_id),
            content_bbox=content_bbox,
            shelf_count_min=int(shelf_min),
            shelf_count_max=int(shelf_max),
        )
    raise ValueError(f"unsupported query_id: {query_id}")


def _sample_center(
    rng,
    *,
    content_bbox: BBox,
    sprite_size: Tuple[int, int],
    region: _RegionSpec,
    desired_inside: bool,
    margin_px: int,
    require_bbox_clearance: bool,
) -> Tuple[float, float]:
    x0, y0, x1, y1 = [int(value) for value in content_bbox]
    half_w = 0.5 * float(sprite_size[0])
    half_h = 0.5 * float(sprite_size[1])
    min_x = float(x0) + half_w
    max_x = float(x1) - half_w
    min_y = float(y0) + half_h
    max_y = float(y1) - half_h
    if min_x >= max_x or min_y >= max_y:
        raise ValueError("sprite does not fit content bbox")
    for _ in range(900):
        cx = float(rng.uniform(min_x, max_x))
        cy = float(rng.uniform(min_y, max_y))
        if bool(require_bbox_clearance):
            bbox = bbox_from_center_and_size((cx, cy), sprite_size)
            if _bbox_safely_matches_region(region, bbox, desired_inside=bool(desired_inside), margin_px=int(margin_px)):
                return (float(cx), float(cy))
            continue
        if _point_safely_matches_region(region, (cx, cy), desired_inside=bool(desired_inside), margin_px=int(margin_px)):
            return (float(cx), float(cy))
    raise ValueError("could not sample center with requested region membership")


def _draw_clipped_polygon(
    image: Image.Image,
    *,
    content_bbox: BBox,
    polygon: Sequence[Sequence[float]],
    fill_rgba: Tuple[int, int, int, int],
    outline_rgba: Tuple[int, int, int, int] | None,
    width: int,
) -> None:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    points = [(float(x), float(y)) for x, y in polygon]
    draw.polygon(points, fill=tuple(int(value) for value in fill_rgba))
    if outline_rgba is not None:
        draw.line(points + [points[0]], fill=tuple(int(value) for value in outline_rgba), width=max(1, int(width)))
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rectangle(tuple(int(value) for value in content_bbox), fill=255)
    alpha = ImageChops.multiply(overlay.getchannel("A"), mask)
    overlay.putalpha(alpha)
    image.alpha_composite(overlay)


def _draw_region_underlay(image: Image.Image, *, region: _RegionSpec, content_bbox: BBox, render_params: Mapping[str, Any]) -> None:
    fill = tuple(int(value) for value in render_params["region_fill_rgb"]) + (int(render_params["region_fill_alpha"]),)
    guide = tuple(int(value) for value in render_params["region_guide_rgb"]) + (150,)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    if region.region_kind in {"shape", "quadrant", "shelf"}:
        if region.bbox_xyxy is None:
            raise ValueError("box-like region is missing bbox")
        if region.shape_kind == "ellipse":
            draw.ellipse(tuple(int(value) for value in region.bbox_xyxy), fill=fill)
        else:
            draw.rectangle(tuple(int(value) for value in region.bbox_xyxy), fill=fill)
        if region.region_kind == "quadrant":
            x0, y0, x1, y1 = [int(value) for value in content_bbox]
            xm = int(round(0.5 * float(x0 + x1)))
            ym = int(round(0.5 * float(y0 + y1)))
            draw.line((xm, y0, xm, y1), fill=guide, width=2)
            draw.line((x0, ym, x1, ym), fill=guide, width=2)
        if region.region_kind == "shelf":
            x0, y0, x1, y1 = [int(value) for value in content_bbox]
            for row in range(1, int(region.shelf_count)):
                y = int(round(float(y0) + (float(row) * float(y1 - y0) / float(max(1, int(region.shelf_count))))))
                draw.line((x0, y, x1, y), fill=guide, width=2)
        image.alpha_composite(overlay)
        return
    if region.region_kind == "band":
        _draw_clipped_polygon(
            image,
            content_bbox=content_bbox,
            polygon=region.band_polygon_xy,
            fill_rgba=fill,
            outline_rgba=None,
            width=int(render_params["region_outline_width_px"]),
        )
        return
    raise ValueError(f"unsupported region kind: {region.region_kind}")


def _draw_region_outline(image: Image.Image, *, region: _RegionSpec, content_bbox: BBox, render_params: Mapping[str, Any]) -> None:
    outline = tuple(int(value) for value in render_params["region_outline_rgb"]) + (230,)
    guide = tuple(int(value) for value in render_params["region_guide_rgb"]) + (170,)
    width = max(1, int(render_params["region_outline_width_px"]))
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    if region.region_kind in {"shape", "quadrant", "shelf"}:
        if region.bbox_xyxy is None:
            raise ValueError("box-like region is missing bbox")
        if region.region_kind == "quadrant":
            x0, y0, x1, y1 = [int(value) for value in content_bbox]
            xm = int(round(0.5 * float(x0 + x1)))
            ym = int(round(0.5 * float(y0 + y1)))
            draw.line((xm, y0, xm, y1), fill=guide, width=2)
            draw.line((x0, ym, x1, ym), fill=guide, width=2)
        if region.region_kind == "shelf":
            x0, y0, x1, y1 = [int(value) for value in content_bbox]
            for row in range(1, int(region.shelf_count)):
                y = int(round(float(y0) + (float(row) * float(y1 - y0) / float(max(1, int(region.shelf_count))))))
                draw.line((x0, y, x1, y), fill=guide, width=2)
        if region.shape_kind == "ellipse":
            draw.ellipse(tuple(int(value) for value in region.bbox_xyxy), outline=outline, width=width)
        else:
            draw.rectangle(tuple(int(value) for value in region.bbox_xyxy), outline=outline, width=width)
        image.alpha_composite(overlay)
        return
    if region.region_kind == "band":
        _draw_clipped_polygon(
            image,
            content_bbox=content_bbox,
            polygon=region.band_polygon_xy,
            fill_rgba=(0, 0, 0, 0),
            outline_rgba=outline,
            width=width,
        )
        return
    raise ValueError(f"unsupported region kind: {region.region_kind}")


def _serialize_icon(instance: _RenderedRegionIcon) -> Dict[str, Any]:
    return {
        "entity_kind": "procedural_named_icon",
        "instance_id": str(instance.instance_id),
        "shape_id": str(instance.shape_id),
        "shape_name": str(instance.shape_name),
        "bbox_xyxy": [int(value) for value in instance.bbox_xyxy],
        "center_xy": [float(value) for value in instance.center_xy],
        "nominal_size_px": int(instance.nominal_size_px),
        "rotation_degrees": int(instance.rotation_degrees),
        "tint_rgb": [int(value) for value in instance.tint_rgb],
        "fill_style": str(instance.fill_style),
        "inside_region": bool(instance.inside_region),
        "counted": bool(instance.counted),
        "noise_edits": [dict(edit) for edit in instance.noise_edits],
        "noise_seed": None if instance.noise_seed is None else int(instance.noise_seed),
    }


def _make_scene(*, instance_seed: int, params: Mapping[str, Any], render_params: Mapping[str, Any], attempt: int) -> _ScenePayload:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt))
    layout = resolve_single_panel_layout(
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
    )
    content_bbox = tuple(int(value) for value in layout.scene_content_xyxy)
    query_support = _query_support(params)
    fill_style_support = resolve_named_icon_fill_style_support(params, _GEN_DEFAULTS, fallback_support=_DEFAULTS.named_icon_fill_style_support)
    fill_style_probabilities = resolve_named_icon_fill_style_probabilities(params, _GEN_DEFAULTS, fill_style_support)
    explicit_query = params.get("query_id", params.get("named_region_query_id"))
    if explicit_query is not None:
        query_id = str(explicit_query)
        if query_id not in set(query_support):
            raise ValueError(f"query_id must be one of {query_support}")
    else:
        query_id = str(rng.choice(query_support))
    region = _sample_region(rng=rng, query_id=str(query_id), content_bbox=content_bbox, params=params)
    shape_support = _shape_support(params)
    explicit_shape = params.get("shape_id", params.get("target_shape_id"))
    if explicit_shape is not None:
        target_shape_id = str(explicit_shape)
        if target_shape_id not in set(shape_support):
            raise ValueError(f"target shape must be one of {shape_support}")
    else:
        target_shape_id = str(rng.choice(shape_support))

    answer_min, answer_max = resolve_named_icon_int_bounds(params, _GEN_DEFAULTS, "target_count_min", "target_count_max", _DEFAULTS.target_count_min, _DEFAULTS.target_count_max)
    object_min, object_max = resolve_named_icon_int_bounds(params, _GEN_DEFAULTS, "object_count_min", "object_count_max", _DEFAULTS.object_count_min, _DEFAULTS.object_count_max)
    opposite_min, opposite_max = resolve_named_icon_int_bounds(params, _GEN_DEFAULTS,
        "target_opposite_count_min",
        "target_opposite_count_max",
        _DEFAULTS.target_opposite_count_min,
        _DEFAULTS.target_opposite_count_max,
    )
    if answer_min < 1:
        raise ValueError("named-shape region count uses target_count_min >= 1")
    target_support = tuple(range(int(answer_min), int(answer_max) + 1))
    target_count_probabilities = weighted_probability_map(
        target_support,
        params.get("target_count_weights", group_default(_GEN_DEFAULTS, "target_count_weights", None)),
    )
    explicit_target = params.get("target_count", params.get("target_answer"))
    if explicit_target is not None:
        target_count = int(explicit_target)
        if target_count not in set(target_support):
            raise ValueError(f"target_count must be in {target_support}")
    else:
        target_count = int(sample_weighted_value(rng, target_support, target_count_probabilities))
    target_opposite_count = int(rng.randint(int(opposite_min), int(opposite_max)))
    min_object_count = max(int(object_min), int(target_count) + int(target_opposite_count) + 4)
    if min_object_count > int(object_max):
        raise ValueError("object_count range cannot support requested target/opposite counts")
    object_support = tuple(range(int(min_object_count), int(object_max) + 1))
    explicit_object = params.get("object_count")
    if explicit_object is not None:
        object_count = int(explicit_object)
        if object_count not in set(object_support):
            raise ValueError(f"object_count must be in {object_support}")
    else:
        object_count = int(rng.choice(object_support))

    counts_inside = bool(region.counts_inside)
    plans: list[_IconPlan] = []
    for _ in range(int(target_count)):
        plans.append(_IconPlan(shape_id=str(target_shape_id), desired_inside_region=bool(counts_inside), is_target_shape=True))
    for _ in range(int(target_opposite_count)):
        plans.append(_IconPlan(shape_id=str(target_shape_id), desired_inside_region=not bool(counts_inside), is_target_shape=True))
    distractor_shapes = [str(value) for value in shape_support if str(value) != str(target_shape_id)]
    rng.shuffle(distractor_shapes)
    non_target_count = int(object_count) - len(plans)
    for index in range(int(non_target_count)):
        plans.append(
            _IconPlan(
                shape_id=str(rng.choice(distractor_shapes)),
                desired_inside_region=bool(index % 2 == 0),
                is_target_shape=False,
            )
        )
    rng.shuffle(plans)

    palette_size = int(rng.randint(int(render_params["palette_size_min"]), int(render_params["palette_size_max"])))
    palette = sample_icon_palette(
        rng,
        palette_size=int(palette_size),
        channel_min=int(render_params["color_channel_min"]),
        channel_max=int(render_params["color_channel_max"]),
        anchor_colors=(
            tuple(int(value) for value in render_params["background_color_rgb"]),
            tuple(int(value) for value in render_params["panel_fill_rgb"]),
            tuple(int(value) for value in render_params["panel_border_rgb"]),
            tuple(int(value) for value in render_params["header_text_rgb"]),
            tuple(int(value) for value in render_params["region_fill_rgb"]),
            tuple(int(value) for value in render_params["region_outline_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    )

    image = Image.new("RGBA", (int(layout.canvas_width), int(layout.canvas_height)))
    draw_single_panel(
        image=image,
        layout=layout,
        background_rgb=tuple(int(value) for value in render_params["background_color_rgb"]),
        panel_fill_rgb=tuple(int(value) for value in render_params["panel_fill_rgb"]),
        panel_border_rgb=tuple(int(value) for value in render_params["panel_border_rgb"]),
        title_color_rgb=tuple(int(value) for value in render_params["header_text_rgb"]),
        corner_radius_px=int(render_params["panel_corner_radius_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
        scene_title="Scene",
    )
    _draw_region_underlay(image, region=region, content_bbox=content_bbox, render_params=render_params)

    min_size = max(12, int(render_params["scene_icon_size_min_px"]))
    max_size = max(min_size, int(render_params["scene_icon_size_max_px"]))
    existing_bboxes: list[BBox] = []
    rendered: list[_RenderedRegionIcon] = []
    margin_px = int(render_params["region_boundary_margin_px"])
    for index, plan in enumerate(plans):
        placed = False
        nominal_size = int(rng.randint(int(min_size), int(max_size)))
        rotation = rotation_for_named_shape(rng, str(plan.shape_id))
        tint_rgb = tuple(int(value) for value in rng.choice(palette))
        fill_style = sample_procedural_named_icon_fill_style(
            rng,
            support=fill_style_support,
            probabilities=fill_style_probabilities,
        )
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:named_icon_{int(index)}",
            render_params=render_params,
        )
        for shrink_round in range(8):
            candidate_size = max(28, int(round(float(nominal_size) * (0.92 ** int(shrink_round)))))
            sprite = render_procedural_named_icon_rgba(
                shape_id=str(plan.shape_id),
                size_px=int(candidate_size),
                tint_rgb=tint_rgb,
                fill_style=str(fill_style),
                rotation_degrees=int(rotation),
                mirror_x=False,
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
            for _ in range(int(render_params["scene_placement_max_attempts"])):
                center = _sample_center(
                    rng,
                    content_bbox=content_bbox,
                    sprite_size=tuple(int(value) for value in sprite.size),
                    region=region,
                    desired_inside=bool(plan.desired_inside_region),
                    margin_px=int(margin_px),
                    require_bbox_clearance=bool(plan.is_target_shape),
                )
                bbox = bbox_from_center_and_size(center, sprite.size)
                if max_overlap_with_existing(bbox, existing_bboxes) > float(render_params["scene_max_overlap_fraction"]):
                    continue
                image.alpha_composite(sprite, (int(bbox[0]), int(bbox[1])))
                inside_region = _point_inside_region(region, center)
                counted = bool(plan.is_target_shape and inside_region == counts_inside)
                rendered.append(
                    _RenderedRegionIcon(
                        instance_id=f"named_region_icon_{int(index):02d}",
                        shape_id=str(plan.shape_id),
                        shape_name=procedural_named_icon_display_name(str(plan.shape_id)),
                        bbox_xyxy=tuple(int(value) for value in bbox),
                        center_xy=(float(center[0]), float(center[1])),
                        nominal_size_px=int(candidate_size),
                        rotation_degrees=int(rotation),
                        tint_rgb=tuple(int(value) for value in tint_rgb),
                        fill_style=str(fill_style),
                        inside_region=bool(inside_region),
                        counted=bool(counted),
                        noise_edits=serialize_icon_noise_edits(tuple(noise_edits)),
                        noise_seed=int(noise_seed),
                    )
                )
                existing_bboxes.append(tuple(int(value) for value in bbox))
                placed = True
                break
            if placed:
                break
        if not placed:
            raise ValueError("could not place named-region icon with requested membership")

    _draw_region_outline(image, region=region, content_bbox=content_bbox, render_params=render_params)
    counted_count = sum(1 for instance in rendered if instance.counted)
    if int(counted_count) != int(target_count):
        raise RuntimeError("rendered region count did not match target answer")

    return _ScenePayload(
        image=image.convert("RGB"),
        panel_geometry=single_panel_geometry_to_trace(layout),
        region=region,
        target_shape_id=str(target_shape_id),
        target_shape_name=procedural_named_icon_display_name(str(target_shape_id)),
        target_count=int(target_count),
        object_count=int(object_count),
        instances=tuple(rendered),
        sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in palette),
        query_probabilities=uniform_string_probability_map(query_support, selected=str(query_id) if explicit_query is not None else None),
        shape_probabilities=uniform_string_probability_map(shape_support, selected=str(target_shape_id) if explicit_shape is not None else None),
        target_count_probabilities=dict(uniform_probability_map(target_support, selected=int(target_count)) if explicit_target is not None else target_count_probabilities),
        object_count_probabilities=dict(uniform_probability_map(object_support, selected=int(object_count) if explicit_object is not None else None)),
        fill_style_support=tuple(fill_style_support),
        fill_style_probabilities=dict(fill_style_probabilities),
    )


def _complexity(scene: _ScenePayload, *, render_params: Mapping[str, Any]) -> TaskComplexity:
    answer_load = (int(scene.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    object_load = (int(scene.object_count) - _DEFAULTS.object_count_min) / max(1, _DEFAULTS.object_count_max - _DEFAULTS.object_count_min)
    region_difficulty = {
        "shape": 0.45 if str(scene.region.shape_kind) == "rectangle" else 0.55,
        "band": 0.62 if str(scene.region.band_kind) in {"vertical", "horizontal"} else 0.76,
        "quadrant": 0.42,
        "shelf": 0.36,
    }[str(scene.region.region_kind)]
    outside_bonus = 0.12 if not bool(scene.region.counts_inside) else 0.0
    shape_diversity = len(set(instance.shape_id for instance in scene.instances)) / max(1.0, float(scene.object_count))
    score = (
        0.24 * max(0.0, min(1.0, answer_load))
        + 0.22 * max(0.0, min(1.0, object_load))
        + 0.28 * float(region_difficulty)
        + 0.16 * max(0.0, min(1.0, shape_diversity))
        + 0.10 * float(outside_bonus)
    )
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "answer_load": round(float(answer_load), 6),
            "object_load": round(float(object_load), 6),
            "region_difficulty": round(float(region_difficulty), 6),
            "outside_bonus": round(float(outside_bonus), 6),
            "shape_diversity": round(float(shape_diversity), 6),
            "query_id": str(scene.region.query_id),
            "target_shape_id": str(scene.target_shape_id),
            "target_count": int(scene.target_count),
            "object_count": int(scene.object_count),
            "region_kind": str(scene.region.region_kind),
            "region_shape_kind": str(scene.region.shape_kind),
            "band_kind": str(scene.region.band_kind),
            "scene_icon_size_min_px": int(render_params["scene_icon_size_min_px"]),
            "scene_icon_size_max_px": int(render_params["scene_icon_size_max_px"]),
        },
    )


@register_task
class IconsCountingNamedShapeRegionCountTask:
    """Count named procedural icon shapes satisfying a visible region filter."""

    task_id = TASK_ID
    domain = "icons"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        render_params = resolve_icon_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        render_params["region_shape_kinds"] = tuple(
            str(value)
            for value in params.get("region_shape_kinds", group_default(_GEN_DEFAULTS, "region_shape_kinds", _DEFAULTS.region_shape_kinds))
        )
        render_params["band_kinds"] = tuple(str(value) for value in params.get("band_kinds", group_default(_GEN_DEFAULTS, "band_kinds", _DEFAULTS.band_kinds)))
        render_params["quadrant_ids"] = tuple(
            str(value)
            for value in params.get("quadrant_ids", group_default(_GEN_DEFAULTS, "quadrant_ids", _DEFAULTS.quadrant_ids))
        )
        render_params["region_boundary_margin_px"] = _int_default(
            params,
            _RENDER_DEFAULTS,
            "region_boundary_margin_px",
            _DEFAULTS.region_boundary_margin_px,
        )
        render_params["region_fill_rgb"] = _rgb_default(params, _RENDER_DEFAULTS, "region_fill_rgb", _DEFAULTS.region_fill_rgb)
        render_params["region_outline_rgb"] = _rgb_default(params, _RENDER_DEFAULTS, "region_outline_rgb", _DEFAULTS.region_outline_rgb)
        render_params["region_guide_rgb"] = _rgb_default(params, _RENDER_DEFAULTS, "region_guide_rgb", _DEFAULTS.region_guide_rgb)
        render_params["region_fill_alpha"] = _int_default(params, _RENDER_DEFAULTS, "region_fill_alpha", _DEFAULTS.region_fill_alpha)
        render_params["region_outline_width_px"] = _int_default(
            params,
            _RENDER_DEFAULTS,
            "region_outline_width_px",
            _DEFAULTS.region_outline_width_px,
        )

        last_error: Exception | None = None
        scene: _ScenePayload | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                scene = _make_scene(
                    instance_seed=int(instance_seed),
                    params=params,
                    render_params=render_params,
                    attempt=int(attempt),
                )
                break
            except Exception as exc:  # pragma: no cover - exercised by generation smoke tests.
                last_error = exc
                scene = None
        if scene is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        evidence_bboxes = sort_bboxes_reading_order(tuple(instance.bbox_xyxy for instance in scene.instances if instance.counted))
        if len(evidence_bboxes) != int(scene.target_count):
            raise RuntimeError("projected region evidence did not match target answer")

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                f"question_text_{scene.region.query_id}",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_key = f"question_text_{scene.region.query_id}"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults[question_key]).format(shape_name=str(scene.target_shape_name)),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]).format(shape_name=str(scene.target_shape_name)),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        serialized_instances = [_serialize_icon(instance) for instance in scene.instances]
        shape_counts = dict(Counter(str(instance.shape_id) for instance in scene.instances))
        inside_shape_counts = dict(Counter(str(instance.shape_id) for instance in scene.instances if instance.inside_region))
        outside_shape_counts = dict(Counter(str(instance.shape_id) for instance in scene.instances if not instance.inside_region))
        counted_instance_ids = tuple(str(instance.instance_id) for instance in scene.instances if instance.counted)
        region_payload = _region_to_trace(scene.region)
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_named_shape_region_field",
                "scene_id": SCENE_ID,
                "entities": list(serialized_instances),
                "relations": {
                    "counting_rule": "target_shape_center_membership_in_visible_region",
                    "target_shape_id": str(scene.target_shape_id),
                    "target_shape_name": str(scene.target_shape_name),
                    "target_count": int(scene.target_count),
                    "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                    "inside_shape_counts": {str(key): int(value) for key, value in inside_shape_counts.items()},
                    "outside_shape_counts": {str(key): int(value) for key, value in outside_shape_counts.items()},
                    "region": dict(region_payload),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene.panel_geometry),
                },
            },
            "query_spec": {
                "query_variant": "default",
                "query_id": str(scene.region.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "target_shape_id": str(scene.target_shape_id),
                    "target_shape_name": str(scene.target_shape_name),
                    "target_count": int(scene.target_count),
                    "object_count": int(scene.object_count),
                    "query_id": str(scene.region.query_id),
                    "region": dict(region_payload),
                    "shape_id_support": list(_shape_support(params)),
                    "query_probabilities": dict(scene.query_probabilities),
                    "shape_probabilities": dict(scene.shape_probabilities),
                    "target_count_probabilities": dict(scene.target_count_probabilities),
                    "object_count_probabilities": dict(scene.object_count_probabilities),
                    "named_icon_fill_style_support": list(scene.fill_style_support),
                    "fill_style_probabilities": dict(scene.fill_style_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": list(scene.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "panel_geometry": dict(scene.panel_geometry),
                "style": {
                    **icon_render_style_trace(render_params=render_params, sampled_palette_rgb=scene.sampled_palette_rgb),
                    "named_icon_fill_style_support": list(scene.fill_style_support),
                    "region_fill_rgb": [int(value) for value in render_params["region_fill_rgb"]],
                    "region_outline_rgb": [int(value) for value in render_params["region_outline_rgb"]],
                    "region_guide_rgb": [int(value) for value in render_params["region_guide_rgb"]],
                    "region_fill_alpha": int(render_params["region_fill_alpha"]),
                    "region_outline_width_px": int(render_params["region_outline_width_px"]),
                    "region_boundary_margin_px": int(render_params["region_boundary_margin_px"]),
                },
            },
            "render_map": {
                "image_id": "img0",
                "object_bboxes_px": {
                    str(instance.instance_id): [int(value) for value in instance.bbox_xyxy]
                    for instance in scene.instances
                },
                "object_centers_px": {
                    str(instance.instance_id): [float(value) for value in instance.center_xy]
                    for instance in scene.instances
                },
                "counted_instance_ids": list(counted_instance_ids),
                "region": dict(region_payload),
            },
            "execution_trace": {
                "scene_variant": "single_panel_named_shape_region_field",
                "query_variant": "default",
                "query_id": str(scene.region.query_id),
                "question_format": "count_named_shape_icons_by_visible_region_membership",
                "target_shape_id": str(scene.target_shape_id),
                "target_shape_name": str(scene.target_shape_name),
                "target_count": int(scene.target_count),
                "object_count": int(scene.object_count),
                "region": dict(region_payload),
                "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                "inside_shape_counts": {str(key): int(value) for key, value in inside_shape_counts.items()},
                "outside_shape_counts": {str(key): int(value) for key, value in outside_shape_counts.items()},
                "counted_instance_ids": list(counted_instance_ids),
            },
            "witness_symbolic": {
                "target_shape_id": str(scene.target_shape_id),
                "target_shape_name": str(scene.target_shape_name),
                "answer": int(scene.target_count),
                "counted_instance_ids": list(counted_instance_ids),
                "region": dict(region_payload),
            },
            "projected_evidence": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
                "counted_instance_ids": list(counted_instance_ids),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(scene.target_count)),
            evidence_gt=TypedValue(type="bbox_set", value=list(evidence_bboxes)),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_complexity(scene, render_params=render_params),
            task_versions=default_task_versions(),
            query_variant="default",
            scene_id=SCENE_ID,
            query_id=str(scene.region.query_id),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        )


__all__ = ["IconsCountingNamedShapeRegionCountTask"]
