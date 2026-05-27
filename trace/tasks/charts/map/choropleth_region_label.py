"""Map-region count tasks for chart-domain visual reasoning."""

from __future__ import annotations

import math
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_raw as _bbox_union, round_bbox as _round_bbox
from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.config_defaults import (
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.drawing import draw_centered_text, draw_rounded_rect
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.text_rendering import fit_font_to_box, load_font
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin, MergedChartQueryVariantTaskMixin
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.label_assets import resolve_chart_category_labels
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_map_choropleth_region_count_base"
_SUPPORTED_REGION_VALUE_QUERY_VARIANTS: Tuple[str, ...] = (
    "numeric_threshold_region_count",
    "numeric_interval_region_count",
)
_SUPPORTED_REGION_CATEGORY_QUERY_VARIANTS: Tuple[str, ...] = (
    "categorical_region_count",
)
_SUPPORTED_WORLD_FILTERED_QUERY_VARIANTS: Tuple[str, ...] = (
    "continent_region_count",
    "continent_category_region_count",
    "continent_threshold_region_count",
)
_SUPPORTED_WORLD_BORDER_QUERY_VARIANTS: Tuple[str, ...] = ("border_neighbor_count",)
_SUPPORTED_ADJACENT_QUERY_VARIANTS: Tuple[str, ...] = (
    "adjacent_same_category_count",
    "adjacent_category_count",
    "adjacent_numeric_threshold_count",
)
_SUPPORTED_MARKER_QUERY_VARIANTS: Tuple[str, ...] = (
    "marker_region_threshold_count",
    "marker_region_extremum_label",
)
_SUPPORTED_MARKER_RENDER_VARIANTS: Tuple[str, ...] = (
    "proportional_bubble",
    "unit_bubble_count",
)
_SUPPORTED_MARKER_EXTREMUM_DIRECTIONS: Tuple[str, ...] = ("largest", "smallest")
_SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = _SUPPORTED_REGION_VALUE_QUERY_VARIANTS + _SUPPORTED_REGION_CATEGORY_QUERY_VARIANTS
_SUPPORTED_ALL_QUERY_VARIANTS: Tuple[str, ...] = (
    _SUPPORTED_QUERY_VARIANTS
    + _SUPPORTED_WORLD_FILTERED_QUERY_VARIANTS
    + _SUPPORTED_WORLD_BORDER_QUERY_VARIANTS
    + _SUPPORTED_ADJACENT_QUERY_VARIANTS
    + _SUPPORTED_MARKER_QUERY_VARIANTS
)
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("synthetic_region_map", "geographic_region_map")
_SUPPORTED_THRESHOLD_DIRECTIONS: Tuple[str, ...] = ("greater_than", "less_than")
_SUPPORTED_GEOGRAPHIC_MAP_VARIANTS: Tuple[str, ...] = (
    "world_countries",
    "eu_countries",
    "usa_states",
    "china_provinces",
)
_SUPPORTED_LEGEND_POSITIONS: Tuple[str, ...] = ("right", "bottom", "top", "none")
_SUPPORTED_WORLD_MAP_STYLES: Tuple[str, ...] = (
    "atlas_light",
    "report_blue",
    "warm_print",
    "muted_gray",
    "clean_minimal",
)
SUPPORTED_REGION_VALUE_QUERY_VARIANTS = _SUPPORTED_REGION_VALUE_QUERY_VARIANTS
SUPPORTED_REGION_CATEGORY_QUERY_VARIANTS = _SUPPORTED_REGION_CATEGORY_QUERY_VARIANTS
SUPPORTED_QUERY_VARIANTS = _SUPPORTED_QUERY_VARIANTS
SUPPORTED_WORLD_FILTERED_QUERY_VARIANTS = _SUPPORTED_WORLD_FILTERED_QUERY_VARIANTS
SUPPORTED_WORLD_BORDER_QUERY_VARIANTS = _SUPPORTED_WORLD_BORDER_QUERY_VARIANTS
SUPPORTED_ADJACENT_QUERY_VARIANTS = _SUPPORTED_ADJACENT_QUERY_VARIANTS
SUPPORTED_MARKER_QUERY_VARIANTS = _SUPPORTED_MARKER_QUERY_VARIANTS
SUPPORTED_MARKER_RENDER_VARIANTS = _SUPPORTED_MARKER_RENDER_VARIANTS
SUPPORTED_SCENE_VARIANTS = _SUPPORTED_SCENE_VARIANTS
_WORLD_FILTERED_CONTINENTS: Tuple[str, ...] = (
    "Africa",
    "Asia",
    "Europe",
    "North America",
    "South America",
)

_TITLE_OPTIONS: Tuple[str, ...] = (
    "Regional Value Map",
    "District Value Map",
    "Service Area Map",
    "Planning Region Map",
    "County Indicator Map",
)
_WORLD_TITLE_OPTIONS: Tuple[str, ...] = (
    "World Indicator Map",
    "Global Country Map",
    "World Regional Value Map",
    "Global Metric Map",
    "Country Value Overview",
)
_WORLD_CATEGORY_TITLE_OPTIONS: Tuple[str, ...] = (
    "World Category Map",
    "Regional Category Map",
    "Country Category Overview",
    "Area Category Map",
    "Regional Class Map",
)
_WORLD_BORDER_TITLE_OPTIONS: Tuple[str, ...] = (
    "World Country Map",
    "Country Border Map",
    "World Borders Map",
    "Global Country Borders",
    "Land Border Map",
)
_MARKER_MAP_TITLE_OPTIONS: Tuple[str, ...] = (
    "Regional Marker Map",
    "Bubble Indicator Map",
    "Marker Value Map",
    "Area Marker Overview",
    "Region Bubble Map",
)

_NUMERIC_PALETTES_RGB: Dict[str, Tuple[Tuple[int, int, int], ...]] = {
    "blue": (
        (239, 246, 255),
        (219, 234, 254),
        (191, 219, 254),
        (147, 197, 253),
        (96, 165, 250),
        (59, 130, 246),
        (37, 99, 235),
        (30, 64, 175),
    ),
    "green": (
        (240, 253, 244),
        (220, 252, 231),
        (187, 247, 208),
        (134, 239, 172),
        (74, 222, 128),
        (34, 197, 94),
        (22, 163, 74),
        (21, 128, 61),
    ),
    "orange": (
        (255, 247, 237),
        (255, 237, 213),
        (254, 215, 170),
        (253, 186, 116),
        (251, 146, 60),
        (249, 115, 22),
        (234, 88, 12),
        (194, 65, 12),
    ),
    "purple": (
        (250, 245, 255),
        (243, 232, 255),
        (233, 213, 255),
        (216, 180, 254),
        (192, 132, 252),
        (168, 85, 247),
        (147, 51, 234),
        (126, 34, 206),
    ),
    "rose": (
        (255, 241, 242),
        (255, 228, 230),
        (254, 205, 211),
        (253, 164, 175),
        (251, 113, 133),
        (244, 63, 94),
        (225, 29, 72),
        (190, 18, 60),
    ),
    "teal": (
        (240, 253, 250),
        (204, 251, 241),
        (153, 246, 228),
        (94, 234, 212),
        (45, 212, 191),
        (20, 184, 166),
        (13, 148, 136),
        (15, 118, 110),
    ),
    "indigo": (
        (238, 242, 255),
        (224, 231, 255),
        (199, 210, 254),
        (165, 180, 252),
        (129, 140, 248),
        (99, 102, 241),
        (79, 70, 229),
        (67, 56, 202),
    ),
    "magma": (
        (252, 244, 250),
        (246, 210, 238),
        (230, 159, 211),
        (204, 101, 178),
        (172, 54, 143),
        (130, 31, 113),
        (86, 24, 91),
        (42, 17, 61),
    ),
    "earth": (
        (248, 250, 229),
        (230, 242, 194),
        (199, 226, 166),
        (153, 204, 142),
        (105, 172, 123),
        (80, 132, 106),
        (72, 93, 88),
        (57, 64, 67),
    ),
    "sunset": (
        (255, 247, 214),
        (254, 226, 178),
        (253, 198, 138),
        (248, 155, 108),
        (230, 103, 99),
        (197, 63, 101),
        (147, 43, 104),
        (93, 31, 84),
    ),
}
_CATEGORICAL_PALETTES_RGB: Dict[str, Tuple[Tuple[int, int, int], ...]] = {
    "tableau": (
        (78, 121, 167),
        (242, 142, 43),
        (225, 87, 89),
        (118, 183, 178),
        (89, 161, 79),
        (237, 201, 72),
        (176, 122, 161),
        (255, 157, 167),
    ),
    "bold": (
        (35, 92, 146),
        (214, 93, 14),
        (33, 145, 140),
        (128, 64, 173),
        (73, 157, 63),
        (205, 59, 97),
        (166, 118, 29),
        (72, 109, 109),
    ),
    "pastel": (
        (141, 211, 199),
        (255, 255, 179),
        (190, 186, 218),
        (251, 128, 114),
        (128, 177, 211),
        (253, 180, 98),
        (179, 222, 105),
        (252, 205, 229),
    ),
    "metro": (
        (45, 117, 182),
        (239, 142, 72),
        (78, 166, 117),
        (197, 88, 90),
        (122, 95, 172),
        (151, 111, 76),
        (218, 124, 174),
        (116, 116, 116),
    ),
    "harbor": (
        (31, 119, 140),
        (87, 166, 161),
        (167, 203, 161),
        (244, 203, 103),
        (224, 134, 69),
        (193, 84, 84),
        (117, 88, 142),
        (77, 93, 104),
    ),
    "orchid": (
        (107, 70, 193),
        (190, 85, 212),
        (236, 72, 153),
        (244, 114, 182),
        (99, 102, 241),
        (14, 165, 233),
        (20, 184, 166),
        (132, 204, 22),
    ),
    "field": (
        (79, 121, 66),
        (159, 177, 83),
        (226, 193, 95),
        (202, 132, 74),
        (139, 91, 69),
        (94, 124, 139),
        (82, 92, 120),
        (150, 101, 137),
    ),
    "civic": (
        (49, 90, 158),
        (96, 150, 197),
        (244, 162, 97),
        (231, 111, 81),
        (42, 157, 143),
        (138, 176, 125),
        (196, 154, 108),
        (108, 117, 125),
    ),
}

_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "numeric_threshold_region_count": 0.50,
    "numeric_interval_region_count": 0.62,
    "categorical_region_count": 0.46,
    "continent_region_count": 0.56,
    "continent_category_region_count": 0.68,
    "continent_threshold_region_count": 0.70,
    "border_neighbor_count": 0.74,
    "adjacent_same_category_count": 0.64,
    "adjacent_category_count": 0.66,
    "adjacent_numeric_threshold_count": 0.72,
    "marker_region_threshold_count": 0.58,
    "marker_region_extremum_label": 0.54,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "synthetic_region_map": 0.58,
    "geographic_region_map": 0.72,
}
_MAP_ASSET_ROOT = Path(__file__).resolve().parents[4] / "assets" / "charts" / "maps"
_WORLD_MAP_ASSET_ID = "natural_earth_admin0_world_110m_v0"
_GEOGRAPHIC_MAP_ASSETS: Dict[str, Dict[str, str]] = {
    "world_countries": {
        "asset_id": _WORLD_MAP_ASSET_ID,
        "path": "natural_earth_admin0_world_110m_v0.json",
    },
    "eu_countries": {
        "asset_id": "natural_earth_admin0_eu_110m_v0",
        "path": "natural_earth_admin0_eu_110m_v0.json",
    },
    "usa_states": {
        "asset_id": "natural_earth_admin1_usa_contiguous_110m_v0",
        "path": "natural_earth_admin1_usa_contiguous_110m_v0.json",
    },
    "china_provinces": {
        "asset_id": "natural_earth_admin1_china_50m_v0",
        "path": "natural_earth_admin1_china_50m_v0.json",
    },
}
_GEOGRAPHIC_MAP_VARIANT_BY_ASSET_ID: Dict[str, str] = {
    str(spec["asset_id"]): str(variant)
    for variant, spec in _GEOGRAPHIC_MAP_ASSETS.items()
}
_WORLD_MAP_STYLES: Dict[str, Dict[str, Any]] = {
    "atlas_light": {
        "ocean_rgb": (230, 241, 247),
        "land_fill_rgb": (218, 224, 219),
        "land_outline_rgb": (128, 143, 148),
        "selected_outline_rgb": (37, 47, 56),
        "graticule_rgb": (197, 214, 224),
        "graticule_width_px": 1,
        "selected_outline_width_px": 2,
        "show_graticule": True,
    },
    "report_blue": {
        "ocean_rgb": (224, 236, 245),
        "land_fill_rgb": (226, 229, 226),
        "land_outline_rgb": (107, 128, 141),
        "selected_outline_rgb": (24, 40, 58),
        "graticule_rgb": (187, 207, 221),
        "graticule_width_px": 1,
        "selected_outline_width_px": 2,
        "show_graticule": True,
    },
    "warm_print": {
        "ocean_rgb": (244, 239, 226),
        "land_fill_rgb": (224, 219, 205),
        "land_outline_rgb": (139, 127, 110),
        "selected_outline_rgb": (64, 48, 38),
        "graticule_rgb": (218, 207, 188),
        "graticule_width_px": 1,
        "selected_outline_width_px": 2,
        "show_graticule": True,
    },
    "muted_gray": {
        "ocean_rgb": (238, 241, 243),
        "land_fill_rgb": (219, 223, 224),
        "land_outline_rgb": (118, 127, 132),
        "selected_outline_rgb": (31, 35, 40),
        "graticule_rgb": (210, 216, 220),
        "graticule_width_px": 1,
        "selected_outline_width_px": 2,
        "show_graticule": False,
    },
    "clean_minimal": {
        "ocean_rgb": (250, 252, 253),
        "land_fill_rgb": (225, 230, 226),
        "land_outline_rgb": (144, 154, 154),
        "selected_outline_rgb": (39, 45, 52),
        "graticule_rgb": (224, 230, 233),
        "graticule_width_px": 1,
        "selected_outline_width_px": 2,
        "show_graticule": False,
    },
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "map")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="map")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="map", apply_prob=0.0)


Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]


def _public_task_param_overrides(task_id: str) -> Dict[str, Any]:
    """Return task-id-specific generation/rendering params for public wrappers."""

    overrides: Dict[str, Any] = {}
    if not isinstance(_TASK_GROUP_DEFAULTS, Mapping):
        return overrides
    for section in ("generation", "rendering"):
        section_cfg = _TASK_GROUP_DEFAULTS.get(section)
        if not isinstance(section_cfg, Mapping):
            continue
        task_overrides = section_cfg.get("task_overrides")
        if not isinstance(task_overrides, Mapping):
            continue
        task_values = task_overrides.get(str(task_id))
        if isinstance(task_values, Mapping):
            overrides.update(dict(task_values))
    return overrides


def _normalize_geographic_map_variant(value: Any) -> str:
    text = str(value or "").strip()
    if text in _GEOGRAPHIC_MAP_ASSETS:
        return text
    if text in _GEOGRAPHIC_MAP_VARIANT_BY_ASSET_ID:
        return _GEOGRAPHIC_MAP_VARIANT_BY_ASSET_ID[text]
    if not text:
        return "world_countries"
    raise ValueError(f"unsupported geographic_map_variant: {text}")


@lru_cache(maxsize=None)
def _load_geographic_map_asset(map_variant_or_asset_id: str = "world_countries") -> Dict[str, Any]:
    variant = _normalize_geographic_map_variant(map_variant_or_asset_id)
    asset_path = _MAP_ASSET_ROOT / str(_GEOGRAPHIC_MAP_ASSETS[variant]["path"])
    if not asset_path.exists():
        raise FileNotFoundError(f"missing bundled geographic map asset: {asset_path}")
    asset = json.loads(asset_path.read_text(encoding="utf-8"))
    if not isinstance(asset, Mapping):
        raise ValueError("geographic map asset must be a JSON object")
    regions = asset.get("regions")
    if not isinstance(regions, list) or not regions:
        raise ValueError("geographic map asset must contain non-empty regions")
    normalized = dict(asset)
    normalized.setdefault("asset_id", str(_GEOGRAPHIC_MAP_ASSETS[variant]["asset_id"]))
    normalized.setdefault("map_variant", str(variant))
    normalized.setdefault("display_name", "World" if variant == "world_countries" else str(variant).replace("_", " ").title())
    normalized.setdefault("region_noun", "countries" if variant in {"world_countries", "eu_countries"} else "regions")
    normalized.setdefault("region_prefix", "country" if variant == "world_countries" else "geo_region")
    normalized.setdefault(
        "title_options",
        list(_WORLD_TITLE_OPTIONS) if variant == "world_countries" else [str(normalized["display_name"]) + " Value Map"],
    )
    normalized.setdefault(
        "object_description",
        "a world map with selected countries colored by value and a color legend"
        if variant == "world_countries"
        else "a geographic map with selected regions colored by value and a color legend",
    )
    return normalized


def _load_world_map_asset() -> Dict[str, Any]:
    return _load_geographic_map_asset("world_countries")


@dataclass(frozen=True)
class _MapRenderParams:
    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    panel_padding_px: int
    title_band_height_px: int
    legend_width_px: int
    legend_height_px: int
    map_legend_gap_px: int
    region_gap_px: int
    region_border_width_px: int
    label_font_size_px: int
    legend_font_size_px: int
    title_font_size_px: int
    legend_position: str
    legend_position_probabilities: Dict[str, float]
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    title_color_rgb: Tuple[int, int, int]
    map_border_rgb: Tuple[int, int, int]
    region_border_rgb: Tuple[int, int, int]
    legend_fill_rgb: Tuple[int, int, int]
    legend_text_rgb: Tuple[int, int, int]
    map_palette_rgb: Tuple[Tuple[int, int, int], ...]
    map_palette_variant: str
    map_palette_variant_probabilities: Dict[str, float]
    world_map_style_id: str
    world_map_style_probabilities: Dict[str, float]
    world_map_style: Dict[str, Any]
    layout_offset_x_px: int
    layout_offset_y_px: int
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedChoroplethMap:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    panel_bbox_px: List[float]
    title_bbox_px: List[float]
    map_bbox_px: List[float]
    legend_bbox_px: List[float]
    region_bbox_map: Dict[str, List[float]]
    region_center_map: Dict[str, List[float]]
    legend_entry_bbox_map: Dict[str, List[float]]
    render_meta: Dict[str, Any]


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def _rgb_param(params: Mapping[str, Any], key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _int_param(params: Mapping[str, Any], key: str, fallback: int) -> int:
    raw = params.get(key, _RENDER_DEFAULTS.get(key, fallback))
    return int(raw)


def _select_palette_colors(
    palette: Sequence[Sequence[int]],
    *,
    required_palette_count: int,
) -> Tuple[Tuple[int, int, int], ...]:
    colors = tuple(_rgb(item, (120, 140, 160)) for item in palette)
    if not colors:
        colors = tuple(_NUMERIC_PALETTES_RGB["blue"])
    if int(required_palette_count) <= 1:
        return (colors[0],)
    if len(colors) >= int(required_palette_count):
        return tuple(
            colors[int(round(index * (len(colors) - 1) / max(1, int(required_palette_count) - 1)))]
            for index in range(int(required_palette_count))
        )
    out = list(colors)
    while len(out) < int(required_palette_count):
        out.extend(colors)
    return tuple(out[: int(required_palette_count)])


def _resolve_palette(
    params: Mapping[str, Any],
    *,
    required_palette_count: int,
    categorical: bool,
) -> Tuple[str, Dict[str, float], Tuple[Tuple[int, int, int], ...]]:
    explicit_palette_raw = params.get("map_palette_rgb")
    if explicit_palette_raw is not None:
        palette = tuple(_rgb(item, (150, 180, 210)) for item in explicit_palette_raw)
        return "custom", {"custom": 1.0}, _select_palette_colors(palette, required_palette_count=int(required_palette_count))

    palettes = _CATEGORICAL_PALETTES_RGB if bool(categorical) else _NUMERIC_PALETTES_RGB
    supported = tuple(sorted(palettes.keys()))
    prefix = "categorical" if bool(categorical) else "numeric"
    explicit_key = f"{prefix}_palette_variant"
    if "map_palette_variant" in params and explicit_key not in params:
        params = {**dict(params), explicit_key: params.get("map_palette_variant")}
    variant, probabilities = resolve_chart_axis_variant(
        params=params,
        gen_defaults=_RENDER_DEFAULTS,
        instance_seed=_render_style_seed(params),
        supported_variants=supported,
        task_id=TASK_ID,
        explicit_key=explicit_key,
        weights_key=f"{prefix}_palette_variant_weights",
        balance_flag_key=f"balanced_{prefix}_palette_variant_sampling",
        axis_namespace=f"{prefix}_palette_variant",
    )
    palette = palettes.get(str(variant), next(iter(palettes.values())))
    return (
        str(variant),
        {str(key): float(value) for key, value in sorted(probabilities.items())},
        _select_palette_colors(palette, required_palette_count=int(required_palette_count)),
    )


def _resolve_legend_position(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_LEGEND_POSITIONS,
        task_id=TASK_ID,
        explicit_key="legend_position",
        weights_key="legend_position_weights",
        balance_flag_key="balanced_legend_position_sampling",
        axis_namespace="legend_position",
    )


def _resolve_world_map_style(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float], Dict[str, Any]]:
    style_id, probabilities = resolve_chart_axis_variant(
        params=params,
        gen_defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_WORLD_MAP_STYLES,
        task_id=TASK_ID,
        explicit_key="world_map_style",
        weights_key="world_map_style_weights",
        balance_flag_key="balanced_world_map_style_sampling",
        axis_namespace="world_map_style",
    )
    return (
        str(style_id),
        {str(key): float(value) for key, value in sorted(probabilities.items())},
        dict(_WORLD_MAP_STYLES[str(style_id)]),
    )


def _query_variant_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    explicit = str(params.get("query_variant") or "")
    extended_variants = (
        set(_SUPPORTED_WORLD_FILTERED_QUERY_VARIANTS)
        | set(_SUPPORTED_WORLD_BORDER_QUERY_VARIANTS)
        | set(_SUPPORTED_ADJACENT_QUERY_VARIANTS)
        | set(_SUPPORTED_MARKER_QUERY_VARIANTS)
    )
    if explicit in extended_variants:
        return _SUPPORTED_ALL_QUERY_VARIANTS
    weights = params.get("query_variant_weights")
    if isinstance(weights, Mapping) and any(str(key) in extended_variants for key in weights):
        return _SUPPORTED_ALL_QUERY_VARIANTS
    return _SUPPORTED_QUERY_VARIANTS


def _is_categorical_query_variant(query_variant: str) -> bool:
    return str(query_variant) in {
        "categorical_region_count",
        "continent_category_region_count",
        "adjacent_same_category_count",
        "adjacent_category_count",
    }


def _is_world_filtered_query_variant(query_variant: str) -> bool:
    return str(query_variant) in set(_SUPPORTED_WORLD_FILTERED_QUERY_VARIANTS)


def _is_world_border_query_variant(query_variant: str) -> bool:
    return str(query_variant) in set(_SUPPORTED_WORLD_BORDER_QUERY_VARIANTS)


def _is_adjacent_query_variant(query_variant: str) -> bool:
    return str(query_variant) in set(_SUPPORTED_ADJACENT_QUERY_VARIANTS)


def _is_marker_query_variant(query_variant: str) -> bool:
    return str(query_variant) in set(_SUPPORTED_MARKER_QUERY_VARIANTS)


def _resolve_render_params(
    params: Mapping[str, Any],
    *,
    query_variant: str,
    legend_count: int,
) -> _MapRenderParams:
    outer = _int_param(params, "outer_margin_px", 42)
    jitter_left, _jitter_right, jitter_top, _jitter_bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(outer),
        right_px=int(outer),
        top_px=int(outer),
        bottom_px=int(outer),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=_render_style_seed(params),
        namespace=f"{TASK_ID}.layout",
    )
    categorical = _is_categorical_query_variant(str(query_variant))
    palette_variant, palette_probabilities, palette = _resolve_palette(
        params,
        required_palette_count=int(legend_count),
        categorical=bool(categorical),
    )
    legend_position, legend_position_probabilities = _resolve_legend_position(
        params,
        instance_seed=_render_style_seed(params),
    )
    world_map_style_id, world_map_style_probabilities, world_map_style = _resolve_world_map_style(
        params,
        instance_seed=_render_style_seed(params),
    )
    return _MapRenderParams(
        canvas_width=_int_param(params, "canvas_width", 1180),
        canvas_height=_int_param(params, "canvas_height", 760),
        outer_margin_px=int(outer),
        panel_padding_px=_int_param(params, "panel_padding_px", 26),
        title_band_height_px=_int_param(params, "title_band_height_px", 62),
        legend_width_px=_int_param(params, "legend_width_px", 238),
        legend_height_px=_int_param(params, "legend_height_px", 118),
        map_legend_gap_px=_int_param(params, "map_legend_gap_px", 32),
        region_gap_px=_int_param(params, "region_gap_px", 3),
        region_border_width_px=_int_param(params, "region_border_width_px", 3),
        label_font_size_px=_int_param(params, "label_font_size_px", 18),
        legend_font_size_px=_int_param(params, "legend_font_size_px", 17),
        title_font_size_px=_int_param(params, "title_font_size_px", 28),
        legend_position=str(legend_position),
        legend_position_probabilities=dict(legend_position_probabilities),
        panel_fill_rgb=_rgb_param(params, "panel_fill_rgb", (252, 253, 251)),
        panel_border_rgb=_rgb_param(params, "panel_border_rgb", (72, 82, 92)),
        title_color_rgb=_rgb_param(params, "title_color_rgb", (35, 42, 50)),
        map_border_rgb=_rgb_param(params, "map_border_rgb", (74, 84, 94)),
        region_border_rgb=_rgb_param(params, "region_border_rgb", (255, 255, 255)),
        legend_fill_rgb=_rgb_param(params, "legend_fill_rgb", (255, 255, 255)),
        legend_text_rgb=_rgb_param(params, "legend_text_rgb", (36, 42, 50)),
        map_palette_rgb=tuple(palette),
        map_palette_variant=str(palette_variant),
        map_palette_variant_probabilities=dict(palette_probabilities),
        world_map_style_id=str(world_map_style_id),
        world_map_style_probabilities=dict(world_map_style_probabilities),
        world_map_style=dict(world_map_style),
        layout_offset_x_px=int(jitter_left) - int(outer),
        layout_offset_y_px=int(jitter_top) - int(outer),
        layout_jitter_meta=dict(layout_jitter_meta),
    )


def _polygon_bbox(points: Sequence[Point]) -> List[float]:
    return _round_bbox(
        [
            min(float(point[0]) for point in points),
            min(float(point[1]) for point in points),
            max(float(point[0]) for point in points),
            max(float(point[1]) for point in points),
        ]
    )


def _polygon_center(points: Sequence[Point]) -> Point:
    return (
        sum(float(point[0]) for point in points) / float(len(points)),
        sum(float(point[1]) for point in points) / float(len(points)),
    )


def _shrink_polygon(points: Sequence[Point], *, gap_px: float) -> List[Point]:
    cx, cy = _polygon_center(points)
    out: List[Point] = []
    for x, y in points:
        dx = float(x - cx)
        dy = float(y - cy)
        distance = max(1.0, math.hypot(dx, dy))
        scale = max(0.0, (float(distance) - float(gap_px)) / float(distance))
        out.append((float(cx + (dx * scale)), float(cy + (dy * scale))))
    return out


def _color_luminance(color: Sequence[int]) -> float:
    red, green, blue = (int(color[0]), int(color[1]), int(color[2]))
    return (0.299 * float(red)) + (0.587 * float(green)) + (0.114 * float(blue))


def _text_fill_for_color(color: Sequence[int]) -> Tuple[int, int, int]:
    return (255, 255, 255) if _color_luminance(color) < 145.0 else (26, 35, 44)


def _text_stroke_for_color(color: Sequence[int]) -> Tuple[int, int, int]:
    return (24, 32, 40) if _color_luminance(color) < 145.0 else (255, 255, 255)


def _grid_points(
    *,
    rows: int,
    cols: int,
    map_bbox: Sequence[float],
    instance_seed: int,
) -> Dict[Tuple[int, int], Point]:
    left, top, right, bottom = [float(value) for value in map_bbox]
    width = float(right - left)
    height = float(bottom - top)
    jitter_x = min(18.0, width / max(1.0, float(cols)) * 0.16)
    jitter_y = min(16.0, height / max(1.0, float(rows)) * 0.16)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.cartogram_points")
    points: Dict[Tuple[int, int], Point] = {}
    for y in range(int(rows) + 1):
        for x in range(int(cols) + 1):
            px = float(left + (width * float(x) / float(cols)))
            py = float(top + (height * float(y) / float(rows)))
            if 0 < int(x) < int(cols):
                px += float(rng.uniform(-jitter_x, jitter_x))
            if 0 < int(y) < int(rows):
                py += float(rng.uniform(-jitter_y, jitter_y))
            points[(int(x), int(y))] = (float(px), float(py))
    return points


def _region_polygon(
    *,
    row: int,
    col: int,
    grid_points: Mapping[Tuple[int, int], Point],
) -> List[Point]:
    return [
        grid_points[(int(col), int(row))],
        grid_points[(int(col) + 1, int(row))],
        grid_points[(int(col) + 1, int(row) + 1)],
        grid_points[(int(col), int(row) + 1)],
    ]


def _neighbors(cell: Tuple[int, int], *, rows: int, cols: int) -> List[Tuple[int, int]]:
    row, col = int(cell[0]), int(cell[1])
    out: List[Tuple[int, int]] = []
    for delta_row, delta_col in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        next_row = int(row + delta_row)
        next_col = int(col + delta_col)
        if 0 <= next_row < int(rows) and 0 <= next_col < int(cols):
            out.append((int(next_row), int(next_col)))
    return out


def _reading_order_region_ids(region_ids: Sequence[str], regions_by_id: Mapping[str, Mapping[str, Any]]) -> List[str]:
    def sort_key(item: str) -> Tuple[float, float, str]:
        region = regions_by_id[str(item)]
        if "row" in region and "col" in region:
            return (float(region["row"]), float(region["col"]), str(item))
        centroid = region.get("centroid_lonlat")
        if isinstance(centroid, Sequence) and not isinstance(centroid, (str, bytes)) and len(centroid) >= 2:
            return (-float(centroid[1]), float(centroid[0]), str(item))
        return (0.0, 0.0, str(item))

    return [
        str(region_id)
        for region_id in sorted(
            [str(region_id) for region_id in region_ids],
            key=sort_key,
        )
    ]


def _grid_pair_support(
    *,
    row_min: int,
    row_max: int,
    col_min: int,
    col_max: int,
    region_min: int,
) -> List[Tuple[int, int]]:
    return [
        (int(rows), int(cols))
        for rows in range(int(row_min), int(row_max) + 1)
        for cols in range(int(col_min), int(col_max) + 1)
        if int(rows) * int(cols) >= int(region_min)
    ]


def _balanced_int(
    support: Sequence[int],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> int:
    ordered = [int(value) for value in support]
    if not ordered:
        raise ValueError(f"empty support for {namespace}")
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    return int(ordered[int(index) % len(ordered)])


def _choose_random(items: Sequence[Any], *, rng) -> Any:
    if not items:
        raise ValueError("cannot sample from an empty sequence")
    return items[int(rng.randrange(len(items)))]


def _region_sort_key(region_id: str) -> Tuple[int, int | str]:
    text = str(region_id)
    suffix = text.rsplit("_", 1)[-1]
    if suffix.isdigit():
        return (0, int(suffix))
    return (1, text)


def _sample_connected_cells(
    *,
    rows: int,
    cols: int,
    target_count: int,
    rng,
) -> List[Tuple[int, int]]:
    if int(target_count) > int(rows) * int(cols):
        raise ValueError("target_count exceeds grid capacity")
    center = (int(rows) // 2, int(cols) // 2)
    active = {center}
    while len(active) < int(target_count):
        frontier = sorted({neighbor for cell in active for neighbor in _neighbors(cell, rows=int(rows), cols=int(cols)) if neighbor not in active})
        if not frontier:
            raise RuntimeError("failed to grow connected choropleth shape")

        def score(cell: Tuple[int, int]) -> float:
            dr = abs(float(cell[0]) - ((float(rows) - 1.0) / 2.0))
            dc = abs(float(cell[1]) - ((float(cols) - 1.0) / 2.0))
            return float(dr + dc + rng.random() * 1.75)

        frontier = sorted(frontier, key=score)
        pool_size = min(len(frontier), max(2, 1 + len(frontier) // 2))
        active.add(frontier[int(rng.randrange(pool_size))])
    return sorted(active, key=lambda item: (int(item[0]), int(item[1])))


def _resolve_query_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    supported_variants = _query_variant_support(params)
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=supported_variants,
        task_id=TASK_ID,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        balance_flag_key="balanced_query_variant_sampling",
        axis_namespace="query_variant",
    )


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_geographic_map_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    alias_params = dict(params)
    if "map_asset_variant" in alias_params and "geographic_map_variant" not in alias_params:
        alias_params["geographic_map_variant"] = alias_params.get("map_asset_variant")
    if "map_asset_id" in alias_params and "geographic_map_variant" not in alias_params:
        alias_params["geographic_map_variant"] = _normalize_geographic_map_variant(alias_params.get("map_asset_id"))
    return resolve_chart_axis_variant(
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_GEOGRAPHIC_MAP_VARIANTS,
        task_id=TASK_ID,
        explicit_key="geographic_map_variant",
        weights_key="geographic_map_variant_weights",
        balance_flag_key="balanced_geographic_map_variant_sampling",
        axis_namespace="geographic_map_variant",
    )


def _resolve_threshold_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_THRESHOLD_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="threshold_direction",
        weights_key="threshold_direction_weights",
        balance_flag_key="balanced_threshold_direction_sampling",
        axis_namespace="threshold_direction",
    )


def _resolve_marker_render_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_MARKER_RENDER_VARIANTS,
        task_id=TASK_ID,
        explicit_key="marker_render_variant",
        weights_key="marker_render_variant_weights",
        balance_flag_key="balanced_marker_render_variant_sampling",
        axis_namespace="marker_render_variant",
    )


def _resolve_marker_extremum_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_MARKER_EXTREMUM_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="marker_extremum_direction",
        weights_key="marker_extremum_direction_weights",
        balance_flag_key="balanced_marker_extremum_direction_sampling",
        axis_namespace="marker_extremum_direction",
    )


def _uses_uniform_query_variant_cycle(
    params: Mapping[str, Any],
    *,
    query_variant_probabilities: Mapping[str, float],
) -> bool:
    if params.get("query_variant") is not None or params.get("query_variant_weights") is not None:
        return False
    enabled = bool(params.get("balanced_query_variant_sampling", _GEN_DEFAULTS.get("balanced_query_variant_sampling", True)))
    if not bool(enabled):
        return False
    positives = [float(value) for value in query_variant_probabilities.values() if float(value) > 0.0]
    if len(positives) != len(_SUPPORTED_QUERY_VARIANTS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _support_sampling_params(
    params: Mapping[str, Any],
    *,
    query_variant_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    support_params = dict(params)
    sampling_index = support_params.get("_sample_cursor")
    if sampling_index is None:
        return support_params
    if not _uses_uniform_query_variant_cycle(params, query_variant_probabilities=query_variant_probabilities):
        return support_params
    positive_count = len([float(value) for value in query_variant_probabilities.values() if float(value) > 0.0])
    support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, int(positive_count))
    return support_params


def _make_numeric_bins(bin_count: int) -> List[Dict[str, Any]]:
    bins: List[Dict[str, Any]] = []
    for index in range(int(bin_count)):
        lower = int(math.floor(index * 100 / int(bin_count)))
        upper = int(math.floor((index + 1) * 100 / int(bin_count)) - 1)
        bins.append(
            {
                "bin_id": f"legend_bin_{index}",
                "bin_index": int(index),
                "bin_label": f"{lower}-{upper}",
                "lower": int(lower),
                "upper": int(upper),
                "category": "",
            }
        )
    return bins


def _make_category_bins(bin_count: int, *, rng) -> List[Dict[str, Any]]:
    resolved_labels = resolve_chart_category_labels(
        rng,
        count=int(bin_count),
        max_chars=14,
        allow_spaces=True,
    )
    label_source = {
        "label_source_kind": str(resolved_labels.label_source_kind),
        "label_pool_kind": str(resolved_labels.label_pool_kind),
        "label_bucket": str(resolved_labels.label_bucket),
        "label_manifest": str(resolved_labels.label_manifest),
        "label_filter": dict(resolved_labels.label_filter),
        "label_bucket_probabilities": dict(resolved_labels.label_bucket_probabilities),
    }
    labels = [str(label) for label in resolved_labels.labels]
    return [
        {
            "bin_id": f"legend_bin_{index}",
            "bin_index": int(index),
            "bin_label": str(label),
            "lower": None,
            "upper": None,
            "category": str(label),
            "label_source": dict(label_source),
        }
        for index, label in enumerate(labels)
    ]


def _build_regions(
    *,
    query_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    rng,
) -> Tuple[int, int, List[Tuple[int, int]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    row_min, row_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="region_row_count_min",
        max_key="region_row_count_max",
        fallback_min=5,
        fallback_max=7,
        context=f"{TASK_ID} region rows",
    )
    col_min, col_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="region_col_count_min",
        max_key="region_col_count_max",
        fallback_min=5,
        fallback_max=7,
        context=f"{TASK_ID} region cols",
    )
    region_min, region_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="region_count_min",
        max_key="region_count_max",
        fallback_min=14,
        fallback_max=28,
        context=f"{TASK_ID} total regions",
    )
    grid_pairs = _grid_pair_support(
        row_min=int(row_min),
        row_max=int(row_max),
        col_min=int(col_min),
        col_max=int(col_max),
        region_min=int(region_min),
    )
    if not grid_pairs:
        raise ValueError(f"no valid grid pairs for {TASK_ID} with current row/col/region bounds")
    pair_index = _balanced_int(
        list(range(len(grid_pairs))),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.grid_pair",
    )
    rows, cols = grid_pairs[int(pair_index)]
    region_support = list(range(int(region_min), min(int(region_max), int(rows) * int(cols)) + 1))
    region_count = _balanced_int(
        region_support,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{query_variant}.region_count",
    )
    active_cells = _sample_connected_cells(rows=int(rows), cols=int(cols), target_count=int(region_count), rng=rng)

    if "legend_bin_count" in params:
        bin_min = bin_max = int(params["legend_bin_count"])
    else:
        bin_min, bin_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="legend_bin_count_min",
            max_key="legend_bin_count_max",
            fallback_min=4,
            fallback_max=8,
            context=f"{TASK_ID} legend bins",
        )
    bin_count = _balanced_int(
        list(range(int(bin_min), int(bin_max) + 1)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{query_variant}.legend_bin_count",
    )
    legend_bins = (
        _make_category_bins(int(bin_count), rng=rng)
        if _is_categorical_query_variant(str(query_variant))
        else _make_numeric_bins(int(bin_count))
    )

    regions: List[Dict[str, Any]] = []
    for index, (row, col) in enumerate(active_cells):
        regions.append(
            {
                "region_id": f"region_{index}",
                "row": int(row),
                "col": int(col),
                "bin_index": int(rng.randrange(int(bin_count))),
                "bin_label": str(legend_bins[0]["bin_label"]),
            }
        )
    return int(rows), int(cols), list(active_cells), list(regions), list(legend_bins)


def _apply_bin(regions_by_id: Dict[str, Dict[str, Any]], *, region_id: str, bin_index: int, legend_bins: Sequence[Mapping[str, Any]]) -> None:
    bin_spec = dict(legend_bins[int(bin_index)])
    regions_by_id[str(region_id)]["bin_index"] = int(bin_index)
    regions_by_id[str(region_id)]["bin_label"] = str(bin_spec["bin_label"])
    regions_by_id[str(region_id)]["bin_lower"] = bin_spec.get("lower")
    regions_by_id[str(region_id)]["bin_upper"] = bin_spec.get("upper")
    regions_by_id[str(region_id)]["category"] = str(bin_spec.get("category") or "")


def _target_count_support(params: Mapping[str, Any], *, region_count: int) -> List[int]:
    answer_min, answer_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="count_answer_min",
        max_key="count_answer_max",
        fallback_min=3,
        fallback_max=14,
        context=f"{TASK_ID} answer count",
    )
    max_supported = min(int(answer_max), max(1, int(region_count) - 1))
    min_supported = min(int(answer_min), int(max_supported))
    return list(range(int(min_supported), int(max_supported) + 1))


def _sample_target_count(
    params: Mapping[str, Any],
    *,
    region_count: int,
    query_variant: str,
    instance_seed: int,
) -> Tuple[int, List[int]]:
    support = _target_count_support(params, region_count=int(region_count))
    return (
        _balanced_int(
            support,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_variant}.target_count",
        ),
        list(support),
    )


def _assign_matching_bins(
    *,
    regions_by_id: Dict[str, Dict[str, Any]],
    selected_ids: Sequence[str],
    matching_bins: Sequence[int],
    nonmatching_bins: Sequence[int],
    legend_bins: Sequence[Mapping[str, Any]],
    rng,
) -> None:
    selected = {str(region_id) for region_id in selected_ids}
    for region_id in sorted(regions_by_id.keys(), key=_region_sort_key):
        support = list(matching_bins) if str(region_id) in selected else list(nonmatching_bins)
        _apply_bin(
            regions_by_id,
            region_id=str(region_id),
            bin_index=int(_choose_random(support, rng=rng)),
            legend_bins=legend_bins,
        )


def _world_selected_count_support(params: Mapping[str, Any], *, eligible_count: int) -> List[int]:
    count_min = int(
        params.get(
            "geographic_selected_region_count_min",
            params.get(
                "world_selected_region_count_min",
                _GEN_DEFAULTS.get(
                    "geographic_selected_region_count_min",
                    _GEN_DEFAULTS.get("world_selected_region_count_min", 18),
                ),
            ),
        )
    )
    count_max = int(
        params.get(
            "geographic_selected_region_count_max",
            params.get(
                "world_selected_region_count_max",
                _GEN_DEFAULTS.get(
                    "geographic_selected_region_count_max",
                    _GEN_DEFAULTS.get("world_selected_region_count_max", 28),
                ),
            ),
        )
    )
    if int(count_min) > int(count_max):
        raise ValueError(f"{TASK_ID} geographic selected region min cannot exceed max")
    high = min(int(count_max), int(eligible_count))
    low = min(int(count_min), int(high))
    return list(range(int(low), int(high) + 1))


def _centroid_lonlat_from_rings(rings: Sequence[Sequence[Sequence[float]]]) -> List[float]:
    points = [
        (float(point[0]), float(point[1]))
        for ring in rings
        for point in ring
        if len(point) >= 2
    ]
    if not points:
        return [0.0, 0.0]
    return [
        round(sum(point[0] for point in points) / float(len(points)), 3),
        round(sum(point[1] for point in points) / float(len(points)), 3),
    ]


def _world_filtered_region_candidates(regions: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    allowed = set(_WORLD_FILTERED_CONTINENTS)
    return [
        dict(region)
        for region in regions
        if str(region.get("continent") or "") in allowed
    ]


def _border_segment_key(point_a: Sequence[float], point_b: Sequence[float]) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    a = (round(float(point_a[0]), 3), round(float(point_a[1]), 3))
    b = (round(float(point_b[0]), 3), round(float(point_b[1]), 3))
    return tuple(sorted((a, b)))  # type: ignore[return-value]


def _border_segment_length(segment: Tuple[Tuple[float, float], Tuple[float, float]]) -> float:
    (x0, y0), (x1, y1) = segment
    return float(math.hypot(float(x1 - x0), float(y1 - y0)))


def _region_boundary_segments(region: Mapping[str, Any]) -> Dict[Tuple[Tuple[float, float], Tuple[float, float]], float]:
    segments: Dict[Tuple[Tuple[float, float], Tuple[float, float]], float] = {}
    for ring in region.get("rings", []):
        if not isinstance(ring, (list, tuple)):
            continue
        points = [point for point in ring if isinstance(point, (list, tuple)) and len(point) >= 2]
        if len(points) < 2:
            continue
        for point_a, point_b in zip(points, points[1:] + points[:1]):
            segment = _border_segment_key(point_a, point_b)
            length = _border_segment_length(segment)
            if float(length) > 0.0:
                segments[segment] = float(length)
    return dict(segments)


@lru_cache(maxsize=None)
def _geographic_shared_border_lengths(map_variant_or_asset_id: str = "world_countries") -> Dict[str, Dict[str, float]]:
    """Return visible shared-boundary lengths between regions in a bundled map.

    Natural Earth stores adjacent polygons with shared boundary segments. Matching
    normalized boundary segments keeps this dependency-free while still deriving
    the topology from bundled vector geometry.
    """

    asset = _load_geographic_map_asset(str(map_variant_or_asset_id))
    regions = [
        dict(region)
        for region in asset.get("regions", [])
        if isinstance(region, Mapping)
    ]
    segments_by_id = {
        str(region["region_id"]): _region_boundary_segments(region)
        for region in regions
    }
    adjacency: Dict[str, Dict[str, float]] = {str(region["region_id"]): {} for region in regions}
    for index, region_a in enumerate(regions):
        region_id_a = str(region_a["region_id"])
        segments_a = segments_by_id[region_id_a]
        if not segments_a:
            continue
        keys_a = set(segments_a.keys())
        for region_b in regions[index + 1:]:
            region_id_b = str(region_b["region_id"])
            shared = keys_a.intersection(segments_by_id[region_id_b].keys())
            if not shared:
                continue
            shared_length = float(sum(segments_a[segment] for segment in shared))
            if float(shared_length) <= 0.0:
                continue
            adjacency[region_id_a][region_id_b] = float(shared_length)
            adjacency[region_id_b][region_id_a] = float(shared_length)
    return {str(key): dict(value) for key, value in adjacency.items()}


def _geographic_border_neighbors(
    map_variant_or_asset_id: str = "world_countries",
    *,
    min_shared_length_deg: float,
) -> Dict[str, List[str]]:
    lengths = _geographic_shared_border_lengths(str(map_variant_or_asset_id))
    threshold = float(min_shared_length_deg)
    return {
        str(region_id): sorted(
            str(neighbor_id)
            for neighbor_id, shared_length in neighbor_lengths.items()
            if float(shared_length) >= float(threshold)
        )
        for region_id, neighbor_lengths in lengths.items()
    }


def _world_country_shared_border_lengths() -> Dict[str, Dict[str, float]]:
    return _geographic_shared_border_lengths("world_countries")


def _world_country_border_neighbors(*, min_shared_length_deg: float) -> Dict[str, List[str]]:
    return _geographic_border_neighbors("world_countries", min_shared_length_deg=float(min_shared_length_deg))


def _synthetic_region_adjacency(regions_by_id: Mapping[str, Mapping[str, Any]]) -> Dict[str, List[str]]:
    region_id_by_cell = {
        (int(region["row"]), int(region["col"])): str(region_id)
        for region_id, region in regions_by_id.items()
        if "row" in region and "col" in region
    }
    if not region_id_by_cell:
        return {str(region_id): [] for region_id in regions_by_id}
    max_row = max(row for row, _col in region_id_by_cell)
    max_col = max(col for _row, col in region_id_by_cell)
    adjacency: Dict[str, set[str]] = {str(region_id): set() for region_id in regions_by_id}
    for cell, region_id in region_id_by_cell.items():
        row, col = int(cell[0]), int(cell[1])
        neighbor_cells = [
            (row + delta_row, col + delta_col)
            for delta_row in (-1, 0, 1)
            for delta_col in (-1, 0, 1)
            if (delta_row, delta_col) != (0, 0)
            and 0 <= row + delta_row <= int(max_row)
            and 0 <= col + delta_col <= int(max_col)
        ]
        for neighbor_cell in neighbor_cells:
            neighbor_id = region_id_by_cell.get(neighbor_cell)
            if neighbor_id is not None:
                adjacency[str(region_id)].add(str(neighbor_id))
    return {str(region_id): sorted(values) for region_id, values in adjacency.items()}


def _selected_geographic_region_adjacency(
    regions_by_id: Mapping[str, Mapping[str, Any]],
    *,
    map_variant: str,
    min_shared_length_deg: float,
) -> Dict[str, List[str]]:
    region_id_by_asset_id = {
        str(region.get("asset_region_id")): str(region_id)
        for region_id, region in regions_by_id.items()
        if str(region.get("asset_region_id") or "")
    }
    asset_id_by_region_id = {str(region_id): str(asset_id) for asset_id, region_id in region_id_by_asset_id.items()}
    border_neighbors = _geographic_border_neighbors(
        str(map_variant or "world_countries"),
        min_shared_length_deg=float(min_shared_length_deg),
    )
    adjacency: Dict[str, List[str]] = {}
    for region_id, asset_id in asset_id_by_region_id.items():
        adjacency[str(region_id)] = sorted(
            str(region_id_by_asset_id[str(neighbor_asset_id)])
            for neighbor_asset_id in border_neighbors.get(str(asset_id), [])
            if str(neighbor_asset_id) in region_id_by_asset_id
        )
    return dict(adjacency)


def _build_world_regions(
    *,
    query_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    rng,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str], List[int], Dict[str, Any]]:
    world_filtered = _is_world_filtered_query_variant(str(query_variant))
    world_border = _is_world_border_query_variant(str(query_variant))
    geographic_adjacent = _is_adjacent_query_variant(str(query_variant))
    supported_world_variants = {
        "numeric_threshold_region_count",
        "numeric_interval_region_count",
        "categorical_region_count",
        *_SUPPORTED_WORLD_FILTERED_QUERY_VARIANTS,
        *_SUPPORTED_WORLD_BORDER_QUERY_VARIANTS,
        *_SUPPORTED_ADJACENT_QUERY_VARIANTS,
        *_SUPPORTED_MARKER_QUERY_VARIANTS,
    }
    if str(query_variant) not in supported_world_variants:
        raise ValueError(
            "geographic_region_map does not support this query variant"
        )
    geographic_map_variant, geographic_map_variant_probabilities = _resolve_geographic_map_variant(
        params,
        instance_seed=int(instance_seed),
    )
    if (bool(world_filtered) or bool(world_border)) and str(geographic_map_variant) != "world_countries":
        raise ValueError("filtered/border world map counts require geographic_map_variant=world_countries")
    asset = _load_geographic_map_asset(str(geographic_map_variant))
    asset_regions = [dict(region) for region in asset.get("regions", []) if isinstance(region, Mapping)]
    eligible_regions = [
        dict(region)
        for region in asset_regions
        if bool(region.get("question_eligible"))
    ]
    if not eligible_regions:
        raise ValueError("world map asset has no question-eligible regions")

    filtered_eligible_regions = _world_filtered_region_candidates(eligible_regions) if bool(world_filtered) else eligible_regions
    if bool(world_filtered) and not filtered_eligible_regions:
        raise ValueError("world map asset has no eligible filtered-continent regions")

    selected_count_support = _world_selected_count_support(params, eligible_count=len(filtered_eligible_regions))
    selected_count = _balanced_int(
        selected_count_support,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{query_variant}.world_selected_region_count",
    )
    forced_target_asset_ids: List[str] = []
    forced_target_count = 0
    forced_target_support: List[int] = []
    target_continent = ""
    reference_asset_region_id = ""
    reference_region_id = ""
    reference_country_label = ""
    border_min_shared_length_deg = 0.0
    border_neighbor_asset_ids: List[str] = []
    adjacent_min_shared_length_deg = 0.0
    adjacent_neighbor_asset_ids: List[str] = []
    if bool(world_filtered):
        forced_target_count, forced_target_support = _sample_target_count(
            params,
            region_count=int(selected_count),
            query_variant=str(query_variant),
            instance_seed=int(instance_seed),
        )
        regions_by_continent: Dict[str, List[Dict[str, Any]]] = {
            continent: [
                dict(region)
                for region in filtered_eligible_regions
                if str(region.get("continent") or "") == str(continent)
            ]
            for continent in _WORLD_FILTERED_CONTINENTS
        }
        feasible_continents = [
            str(continent)
            for continent, continent_regions in regions_by_continent.items()
            if len(continent_regions) >= int(forced_target_count)
            and (len(filtered_eligible_regions) - len(continent_regions)) >= int(selected_count) - int(forced_target_count)
        ]
        if not feasible_continents:
            raise ValueError("no feasible continent can support the requested filtered count")
        continent_index = _balanced_int(
            list(range(len(feasible_continents))),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_variant}.target_continent",
        )
        target_continent = str(feasible_continents[int(continent_index)])
        target_pool = sorted(regions_by_continent[str(target_continent)], key=lambda item: str(item["region_id"]))
        distractor_pool = sorted(
            [
                dict(region)
                for region in filtered_eligible_regions
                if str(region.get("continent") or "") != str(target_continent)
            ],
            key=lambda item: str(item["region_id"]),
        )
        target_regions = rng.sample(target_pool, int(forced_target_count))
        distractor_regions = rng.sample(distractor_pool, int(selected_count) - int(forced_target_count))
        selected_asset_regions = list(target_regions) + list(distractor_regions)
        rng.shuffle(selected_asset_regions)
        forced_target_asset_ids = [str(region["region_id"]) for region in target_regions]
    elif bool(world_border):
        forced_target_support = _target_count_support(params, region_count=int(selected_count))
        forced_target_count = _balanced_int(
            forced_target_support,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_variant}.reference_degree",
        )
        border_min_shared_length_deg = float(
            params.get(
                "border_min_shared_length_deg",
                _GEN_DEFAULTS.get("border_min_shared_length_deg", 1.0),
            )
        )
        reference_min_area_sqdeg = float(
            params.get(
                "border_reference_min_area_sqdeg",
                _GEN_DEFAULTS.get("border_reference_min_area_sqdeg", 30.0),
            )
        )
        neighbor_min_area_sqdeg = float(
            params.get(
                "border_neighbor_min_area_sqdeg",
                _GEN_DEFAULTS.get("border_neighbor_min_area_sqdeg", 8.0),
            )
        )
        all_regions_by_id = {str(region["region_id"]): dict(region) for region in asset_regions}
        eligible_by_id = {str(region["region_id"]): dict(region) for region in eligible_regions}
        eligible_ids = set(eligible_by_id.keys())
        all_region_ids = set(all_regions_by_id.keys())
        border_neighbors = _world_country_border_neighbors(min_shared_length_deg=float(border_min_shared_length_deg))
        feasible_reference_ids: List[str] = []
        for candidate_id in sorted(eligible_ids):
            candidate = eligible_by_id[str(candidate_id)]
            if float(candidate.get("area_sqdeg") or 0.0) < float(reference_min_area_sqdeg):
                continue
            neighbor_ids = [
                str(neighbor_id)
                for neighbor_id in border_neighbors.get(str(candidate_id), [])
                if str(neighbor_id) in all_region_ids
            ]
            if any(
                float(all_regions_by_id[str(neighbor_id)].get("area_sqdeg") or 0.0) < float(neighbor_min_area_sqdeg)
                for neighbor_id in neighbor_ids
            ):
                continue
            if len(neighbor_ids) == int(forced_target_count):
                feasible_reference_ids.append(str(candidate_id))
        if not feasible_reference_ids:
            raise ValueError("no feasible reference country can support the requested border-neighbor count")
        reference_index = _balanced_int(
            list(range(len(feasible_reference_ids))),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_variant}.reference_country",
        )
        reference_asset_region_id = str(feasible_reference_ids[int(reference_index)])
        reference_country = dict(eligible_by_id[str(reference_asset_region_id)])
        reference_country_label = str(reference_country.get("display_name") or reference_asset_region_id)
        qualified_neighbor_ids = [
            str(neighbor_id)
            for neighbor_id in border_neighbors.get(str(reference_asset_region_id), [])
            if str(neighbor_id) in all_region_ids
            and float(all_regions_by_id[str(neighbor_id)].get("area_sqdeg") or 0.0) >= float(neighbor_min_area_sqdeg)
        ]
        if len(qualified_neighbor_ids) != int(forced_target_count):
            raise ValueError("border-neighbor reference degree does not match target count")
        target_neighbor_ids = sorted(qualified_neighbor_ids)
        selected_asset_regions = [
            dict(reference_country),
            *[dict(all_regions_by_id[str(region_id)]) for region_id in target_neighbor_ids],
        ]
        rng.shuffle(selected_asset_regions)
        forced_target_asset_ids = [str(region_id) for region_id in target_neighbor_ids]
        border_neighbor_asset_ids = list(forced_target_asset_ids)
    elif bool(geographic_adjacent):
        adjacent_min_shared_length_deg = float(
            params.get(
                "adjacent_min_shared_length_deg",
                _GEN_DEFAULTS.get("adjacent_min_shared_length_deg", 0.15),
            )
        )
        reference_min_area_sqdeg = float(
            params.get(
                "adjacent_reference_min_area_sqdeg",
                _GEN_DEFAULTS.get("adjacent_reference_min_area_sqdeg", 0.0),
            )
        )
        neighbor_min_area_sqdeg = float(
            params.get(
                "adjacent_neighbor_min_area_sqdeg",
                _GEN_DEFAULTS.get("adjacent_neighbor_min_area_sqdeg", 0.0),
            )
        )
        adjacent_neighbor_count_min = int(params.get("adjacent_neighbor_count_min", _GEN_DEFAULTS.get("adjacent_neighbor_count_min", 2)))
        adjacent_neighbor_count_max = int(params.get("adjacent_neighbor_count_max", _GEN_DEFAULTS.get("adjacent_neighbor_count_max", 6)))
        all_regions_by_id = {str(region["region_id"]): dict(region) for region in asset_regions}
        eligible_by_id = {str(region["region_id"]): dict(region) for region in eligible_regions}
        eligible_ids = set(eligible_by_id.keys())
        border_neighbors = _geographic_border_neighbors(
            str(geographic_map_variant),
            min_shared_length_deg=float(adjacent_min_shared_length_deg),
        )
        candidate_neighbors_by_ref: Dict[str, List[str]] = {}
        for candidate_id in sorted(eligible_ids):
            candidate = eligible_by_id[str(candidate_id)]
            if float(candidate.get("area_sqdeg") or 0.0) < float(reference_min_area_sqdeg):
                continue
            neighbor_ids = [
                str(neighbor_id)
                for neighbor_id in border_neighbors.get(str(candidate_id), [])
                if str(neighbor_id) in eligible_ids
                and float(all_regions_by_id[str(neighbor_id)].get("area_sqdeg") or 0.0) >= float(neighbor_min_area_sqdeg)
            ]
            if len(neighbor_ids) >= int(adjacent_neighbor_count_min):
                candidate_neighbors_by_ref[str(candidate_id)] = sorted(neighbor_ids)
        if not candidate_neighbors_by_ref:
            raise ValueError("no feasible reference region can support adjacent-region count")
        feasible_reference_ids = sorted(candidate_neighbors_by_ref.keys())
        reference_index = _balanced_int(
            list(range(len(feasible_reference_ids))),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_variant}.adjacent_reference_region",
        )
        reference_asset_region_id = str(feasible_reference_ids[int(reference_index)])
        reference_region = dict(eligible_by_id[str(reference_asset_region_id)])
        reference_country_label = str(reference_region.get("display_name") or reference_asset_region_id)
        neighbor_pool = list(candidate_neighbors_by_ref[str(reference_asset_region_id)])
        neighbor_count_support = list(
            range(
                int(adjacent_neighbor_count_min),
                min(int(adjacent_neighbor_count_max), len(neighbor_pool)) + 1,
            )
        )
        neighbor_count = _balanced_int(
            neighbor_count_support,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_variant}.adjacent_neighbor_count",
        )
        adjacent_neighbor_asset_ids = sorted(rng.sample(neighbor_pool, int(neighbor_count)))
        distractor_pool = [
            dict(region)
            for region in sorted(eligible_regions, key=lambda item: str(item["region_id"]))
            if str(region["region_id"]) not in {str(reference_asset_region_id), *set(adjacent_neighbor_asset_ids)}
        ]
        selected_count = max(int(selected_count), 1 + len(adjacent_neighbor_asset_ids))
        selected_asset_regions = [
            dict(reference_region),
            *[dict(all_regions_by_id[str(region_id)]) for region_id in adjacent_neighbor_asset_ids],
        ]
        distractor_needed = max(0, int(selected_count) - len(selected_asset_regions))
        if distractor_needed > len(distractor_pool):
            distractor_needed = len(distractor_pool)
        selected_asset_regions.extend(rng.sample(distractor_pool, int(distractor_needed)))
        rng.shuffle(selected_asset_regions)
    else:
        selected_asset_regions = rng.sample(
            sorted(eligible_regions, key=lambda item: str(item["region_id"])),
            int(selected_count),
        )

    if "legend_bin_count" in params:
        bin_min = bin_max = int(params["legend_bin_count"])
    else:
        bin_min, bin_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="legend_bin_count_min",
            max_key="legend_bin_count_max",
            fallback_min=3,
            fallback_max=4,
            context=f"{TASK_ID} world legend bins",
        )
    bin_count = _balanced_int(
        list(range(int(bin_min), int(bin_max) + 1)),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{query_variant}.world_legend_bin_count",
    )
    legend_bins = (
        _make_category_bins(int(bin_count), rng=rng)
        if _is_categorical_query_variant(str(query_variant))
        else _make_numeric_bins(int(bin_count))
    )

    regions: List[Dict[str, Any]] = []
    region_prefix = str(asset.get("region_prefix") or "geo_region")
    for asset_region in selected_asset_regions:
        region_id = f"{region_prefix}_{asset_region['region_id']}"
        is_reference_region = (bool(world_border) or bool(geographic_adjacent)) and str(asset_region["region_id"]) == str(reference_asset_region_id)
        if bool(is_reference_region):
            reference_region_id = str(region_id)
        bbox_lonlat = [float(value) for value in asset_region.get("bbox_lonlat", [0.0, 0.0, 0.0, 0.0])]
        regions.append(
            {
                "region_id": str(region_id),
                "asset_region_id": str(asset_region["region_id"]),
                "display_name": str(asset_region.get("display_name") or asset_region["region_id"]),
                "continent": str(asset_region.get("continent") or ""),
                "admin0_a3": str(asset_region.get("admin0_a3") or ""),
                "subregion": str(asset_region.get("subregion") or ""),
                "bbox_lonlat": [round(float(value), 3) for value in bbox_lonlat],
                "centroid_lonlat": _centroid_lonlat_from_rings(asset_region.get("rings", [])),
                "bin_index": int(rng.randrange(int(bin_count))),
                "bin_label": str(legend_bins[0]["bin_label"]),
                "category": "",
                "is_reference_region": bool(is_reference_region),
            }
        )
    asset_meta = {
        "asset_id": str(asset.get("asset_id") or _GEOGRAPHIC_MAP_ASSETS[str(geographic_map_variant)]["asset_id"]),
        "map_variant": str(geographic_map_variant),
        "map_variant_probabilities": dict(geographic_map_variant_probabilities),
        "display_name": str(asset.get("display_name") or ""),
        "region_noun": str(asset.get("region_noun") or "regions"),
        "object_description": str(asset.get("object_description") or ""),
        "title_options": [str(item) for item in asset.get("title_options", [])],
        "category_title_options": list(_WORLD_CATEGORY_TITLE_OPTIONS),
        "forced_target_count": int(forced_target_count),
        "forced_target_support": [int(value) for value in forced_target_support],
        "target_continent": str(target_continent),
        "reference_region_id": str(reference_region_id),
        "reference_asset_region_id": str(reference_asset_region_id),
        "reference_country_label": str(reference_country_label),
        "border_min_shared_length_deg": float(border_min_shared_length_deg),
        "adjacent_min_shared_length_deg": float(adjacent_min_shared_length_deg),
        "border_neighbor_min_area_sqdeg": float(
            params.get(
                "border_neighbor_min_area_sqdeg",
                _GEN_DEFAULTS.get("border_neighbor_min_area_sqdeg", 8.0),
            )
        ),
        "border_neighbor_asset_ids": [str(region_id) for region_id in border_neighbor_asset_ids],
        "adjacent_neighbor_asset_ids": [str(region_id) for region_id in adjacent_neighbor_asset_ids],
        "forced_target_region_ids": [
            f"{region_prefix}_{asset_region_id}"
            for asset_region_id in forced_target_asset_ids
        ],
        "source": dict(asset.get("source", {})) if isinstance(asset.get("source"), Mapping) else {},
    }
    return list(regions), list(legend_bins), [str(region["region_id"]) for region in regions], list(selected_count_support), dict(asset_meta)


def _marker_label_for_index(index: int) -> str:
    """Return spreadsheet-style labels A, B, ..., Z, AA, AB for marker regions."""

    n = int(index)
    letters: List[str] = []
    while True:
        letters.append(chr(ord("A") + (n % 26)))
        n = (n // 26) - 1
        if n < 0:
            break
    return "".join(reversed(letters))


def _marker_value_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="marker_value_min",
        max_key="marker_value_max",
        fallback_min=1,
        fallback_max=5,
        context=f"{TASK_ID} marker values",
    )
    if int(high) - int(low) < 2:
        raise ValueError("marker value support must contain at least three values")
    return int(low), int(high)


def _construct_marker_dataset(
    *,
    query_variant: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    rng,
    rows: int,
    cols: int,
    active_cells: Sequence[Tuple[int, int]],
    regions: Sequence[Mapping[str, Any]],
    legend_bins: Sequence[Mapping[str, Any]],
    map_asset_meta: Mapping[str, Any],
) -> Dict[str, Any]:
    regions_by_id: Dict[str, Dict[str, Any]] = {str(region["region_id"]): dict(region) for region in regions}
    region_ids = _reading_order_region_ids([str(region["region_id"]) for region in regions], regions_by_id)
    if len(region_ids) < 3:
        raise ValueError("marker map needs at least three visible regions")

    marker_render_variant, marker_render_variant_probabilities = _resolve_marker_render_variant(
        params,
        instance_seed=int(instance_seed),
    )
    value_min, value_max = _marker_value_bounds(params)
    value_support = list(range(int(value_min), int(value_max) + 1))
    for index, region_id in enumerate(region_ids):
        regions_by_id[str(region_id)]["marker_label"] = _marker_label_for_index(int(index))
        regions_by_id[str(region_id)]["marker_value"] = int(_choose_random(value_support, rng=rng))
        regions_by_id[str(region_id)]["bin_index"] = 0
        regions_by_id[str(region_id)]["bin_label"] = ""
        regions_by_id[str(region_id)]["category"] = ""

    answer_value: Any
    answer_type: str
    evidence_region_ids: List[str]
    query_params: Dict[str, Any]
    target_count = 0
    target_support: List[int] = []
    threshold_direction = ""

    if str(query_variant) == "marker_region_threshold_count":
        target_count, target_support = _sample_target_count(
            params,
            region_count=len(region_ids),
            query_variant=str(query_variant),
            instance_seed=int(instance_seed),
        )
        target_ids = set(rng.sample(list(region_ids), int(target_count)))
        evidence_region_ids = _reading_order_region_ids(list(target_ids), regions_by_id)
        threshold_direction, threshold_direction_probabilities = _resolve_threshold_direction(
            params,
            instance_seed=int(instance_seed),
        )
        if str(threshold_direction) == "greater_than":
            threshold_value = _balanced_int(
                list(range(int(value_min), int(value_max))),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.{query_variant}.marker_threshold.greater_than",
            )
            matching_values = list(range(int(threshold_value) + 1, int(value_max) + 1))
            nonmatching_values = list(range(int(value_min), int(threshold_value) + 1))
            threshold_phrase = f"greater than {threshold_value}"
        else:
            threshold_value = _balanced_int(
                list(range(int(value_min) + 1, int(value_max) + 1)),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.{query_variant}.marker_threshold.less_than",
            )
            matching_values = list(range(int(value_min), int(threshold_value)))
            nonmatching_values = list(range(int(threshold_value), int(value_max) + 1))
            threshold_phrase = f"less than {threshold_value}"
        for region_id in region_ids:
            support = matching_values if str(region_id) in target_ids else nonmatching_values
            regions_by_id[str(region_id)]["marker_value"] = int(_choose_random(support, rng=rng))
            regions_by_id[str(region_id)]["is_target_marker_region"] = bool(str(region_id) in target_ids)
        answer_value = int(target_count)
        answer_type = "integer"
        query_params = {
            "threshold_direction": str(threshold_direction),
            "threshold_direction_probabilities": dict(threshold_direction_probabilities),
            "threshold_value": int(threshold_value),
            "threshold_phrase": str(threshold_phrase),
            "marker_value_min": int(value_min),
            "marker_value_max": int(value_max),
        }
    elif str(query_variant) == "marker_region_extremum_label":
        extremum_direction, extremum_direction_probabilities = _resolve_marker_extremum_direction(
            params,
            instance_seed=int(instance_seed),
        )
        answer_index = _balanced_int(
            list(range(len(region_ids))),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_variant}.answer_region_index",
        )
        answer_region_id = str(region_ids[int(answer_index)])
        if str(extremum_direction) == "largest":
            answer_marker_value = int(value_max)
            distractor_values = list(range(int(value_min), int(value_max)))
            extremum_word = "largest"
        else:
            answer_marker_value = int(value_min)
            distractor_values = list(range(int(value_min) + 1, int(value_max) + 1))
            extremum_word = "smallest"
        for region_id in region_ids:
            if str(region_id) == str(answer_region_id):
                regions_by_id[str(region_id)]["marker_value"] = int(answer_marker_value)
                regions_by_id[str(region_id)]["is_target_marker_region"] = True
            else:
                regions_by_id[str(region_id)]["marker_value"] = int(_choose_random(distractor_values, rng=rng))
                regions_by_id[str(region_id)]["is_target_marker_region"] = False
        answer_value = str(regions_by_id[str(answer_region_id)]["marker_label"])
        answer_type = "string"
        evidence_region_ids = [str(answer_region_id)]
        target_count = 1
        target_support = [1]
        query_params = {
            "extremum_direction": str(extremum_direction),
            "extremum_direction_probabilities": dict(extremum_direction_probabilities),
            "extremum_word": str(extremum_word),
            "answer_region_id": str(answer_region_id),
            "answer_marker_label": str(answer_value),
            "answer_marker_value": int(answer_marker_value),
            "marker_value_min": int(value_min),
            "marker_value_max": int(value_max),
        }
    else:
        raise ValueError(f"unsupported marker query_variant: {query_variant}")

    final_regions = [dict(regions_by_id[str(region_id)]) for region_id in region_ids]
    world_scene = str(scene_variant) == "geographic_region_map"
    region_noun = str(map_asset_meta.get("region_noun") or ("countries" if world_scene else "regions"))
    map_display = str(map_asset_meta.get("display_name") or "geographic")
    object_description = (
        f"a {map_display.lower() if map_display.lower() == 'world' else map_display} map with marker bubbles over selected {region_noun}"
        if world_scene
        else "a synthetic map with marker bubbles over selected regions"
    )
    return {
        "scene_title": str(_choose_random(_MARKER_MAP_TITLE_OPTIONS, rng=rng)),
        "query_variant": str(query_variant),
        "scene_variant": str(scene_variant),
        "map_asset_id": str(map_asset_meta.get("asset_id") or (_WORLD_MAP_ASSET_ID if world_scene else "")),
        "geographic_map_variant": str(map_asset_meta.get("map_variant") or ""),
        "geographic_map_variant_probabilities": dict(map_asset_meta.get("map_variant_probabilities", {})),
        "map_display_name": str(map_asset_meta.get("display_name") or ""),
        "map_region_noun": str(region_noun),
        "map_object_description": str(object_description),
        "map_source": dict(map_asset_meta.get("source", {})),
        "rows": int(rows),
        "cols": int(cols),
        "region_count": int(len(final_regions)),
        "active_cells": [[int(row), int(col)] for row, col in active_cells],
        "legend_bins": [dict(item) for item in legend_bins],
        "regions": final_regions,
        "regions_by_id": {str(region["region_id"]): dict(region) for region in final_regions},
        "evidence_region_ids": list(evidence_region_ids),
        "answer_value": answer_value,
        "answer_type": str(answer_type),
        "target_count": int(target_count),
        "target_count_probabilities": uniform_probability_map(tuple(target_support)),
        "question_params": {
            "marker_render_variant": str(marker_render_variant),
            "marker_render_variant_probabilities": dict(marker_render_variant_probabilities),
            "marker_region_ids": [str(region_id) for region_id in region_ids],
            **dict(query_params),
        },
        "target_bin_indices": [],
        "nonmatching_bin_indices": [],
        "threshold_direction": str(threshold_direction),
        "marker_render_variant": str(marker_render_variant),
        "marker_render_variant_probabilities": dict(marker_render_variant_probabilities),
        "marker_value_min": int(value_min),
        "marker_value_max": int(value_max),
    }


def _construct_dataset(
    *,
    query_variant: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    if str(scene_variant) not in _SUPPORTED_SCENE_VARIANTS:
        raise ValueError(f"unsupported scene_variant: {scene_variant}")
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    if str(scene_variant) == "geographic_region_map":
        rows = 0
        cols = 0
        active_cells: List[Tuple[int, int]] = []
        regions, legend_bins, _selected_region_ids, _selected_count_support, map_asset_meta = _build_world_regions(
            query_variant=str(query_variant),
            params=params,
            instance_seed=int(instance_seed),
            rng=rng,
        )
    else:
        map_asset_meta = {}
        rows, cols, active_cells, regions, legend_bins = _build_regions(
            query_variant=str(query_variant),
            params=params,
            instance_seed=int(instance_seed),
            rng=rng,
        )
    regions_by_id: Dict[str, Dict[str, Any]] = {str(region["region_id"]): dict(region) for region in regions}
    region_ids = [str(region["region_id"]) for region in regions]
    if _is_marker_query_variant(str(query_variant)):
        return _construct_marker_dataset(
            query_variant=str(query_variant),
            scene_variant=str(scene_variant),
            params=params,
            instance_seed=int(instance_seed),
            rng=rng,
            rows=int(rows),
            cols=int(cols),
            active_cells=list(active_cells),
            regions=list(regions),
            legend_bins=list(legend_bins),
            map_asset_meta=dict(map_asset_meta),
        )
    world_filtered = str(scene_variant) == "geographic_region_map" and _is_world_filtered_query_variant(str(query_variant))
    world_border = str(scene_variant) == "geographic_region_map" and _is_world_border_query_variant(str(query_variant))
    adjacent = _is_adjacent_query_variant(str(query_variant))
    if bool(world_filtered) or bool(world_border):
        target_count = int(map_asset_meta.get("forced_target_count") or 0)
        target_support = [int(value) for value in map_asset_meta.get("forced_target_support", [])]
        if int(target_count) <= 0 or not target_support:
            raise ValueError("world filtered/border task did not construct a target count")
        selected_ids = {
            str(region_id)
            for region_id in map_asset_meta.get("forced_target_region_ids", [])
        }
    elif bool(adjacent):
        if str(scene_variant) == "geographic_region_map":
            adjacency = _selected_geographic_region_adjacency(
                regions_by_id,
                map_variant=str(map_asset_meta.get("map_variant") or "world_countries"),
                min_shared_length_deg=float(map_asset_meta.get("adjacent_min_shared_length_deg") or 0.15),
            )
        else:
            adjacency = _synthetic_region_adjacency(regions_by_id)
        answer_min, answer_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="count_answer_min",
            max_key="count_answer_max",
            fallback_min=1,
            fallback_max=4,
            context=f"{TASK_ID} adjacent answer count",
        )
        feasible_counts = sorted(
            {
                count
                for neighbor_ids in adjacency.values()
                for count in range(int(answer_min), min(int(answer_max), len(neighbor_ids)) + 1)
            }
        )
        if not feasible_counts:
            raise ValueError("no feasible adjacent-region count in selected map")
        target_count = _balanced_int(
            feasible_counts,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_variant}.adjacent_target_count",
        )
        target_support = list(feasible_counts)
        reference_candidates = [
            str(region_id)
            for region_id, neighbor_ids in adjacency.items()
            if len(neighbor_ids) >= int(target_count)
        ]
        forced_reference_region_id = str(map_asset_meta.get("reference_region_id") or "")
        if forced_reference_region_id in reference_candidates:
            reference_region_id = str(forced_reference_region_id)
        else:
            reference_index = _balanced_int(
                list(range(len(reference_candidates))),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.{query_variant}.adjacent_reference_candidate",
            )
            reference_region_id = str(reference_candidates[int(reference_index)])
        regions_by_id[str(reference_region_id)]["is_reference_region"] = True
        neighbor_ids = list(adjacency.get(str(reference_region_id), []))
        selected_ids = set(rng.sample(neighbor_ids, int(target_count)))
        map_asset_meta["reference_region_id"] = str(reference_region_id)
        map_asset_meta["adjacent_neighbor_region_ids"] = list(neighbor_ids)
    else:
        target_count, target_support = _sample_target_count(
            params,
            region_count=len(region_ids),
            query_variant=str(query_variant),
            instance_seed=int(instance_seed),
        )
        selected_ids = set(rng.sample(list(region_ids), int(target_count)))
    evidence_region_ids = _reading_order_region_ids(list(selected_ids), regions_by_id)

    query_params: Dict[str, Any]
    threshold_direction = ""
    threshold_direction_probabilities: Dict[str, float] = {}
    target_bin_indices: List[int] = []
    nonmatching_bin_indices: List[int] = []
    bin_count = int(len(legend_bins))

    if str(query_variant) == "numeric_threshold_region_count":
        threshold_direction, threshold_direction_probabilities = _resolve_threshold_direction(
            params,
            instance_seed=int(instance_seed),
        )
        if str(threshold_direction) == "greater_than":
            threshold_bin = _balanced_int(
                list(range(0, bin_count - 1)),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.threshold_bin.greater_than",
            )
            threshold_value = int(legend_bins[int(threshold_bin)]["upper"])
            target_bin_indices = list(range(int(threshold_bin) + 1, bin_count))
            nonmatching_bin_indices = list(range(0, int(threshold_bin) + 1))
            threshold_phrase = f"greater than {threshold_value}"
        else:
            threshold_bin = _balanced_int(
                list(range(1, bin_count)),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.threshold_bin.less_than",
            )
            threshold_value = int(legend_bins[int(threshold_bin)]["lower"])
            target_bin_indices = list(range(0, int(threshold_bin)))
            nonmatching_bin_indices = list(range(int(threshold_bin), bin_count))
            threshold_phrase = f"less than {threshold_value}"
        _assign_matching_bins(
            regions_by_id=regions_by_id,
            selected_ids=evidence_region_ids,
            matching_bins=target_bin_indices,
            nonmatching_bins=nonmatching_bin_indices,
            legend_bins=legend_bins,
            rng=rng,
        )
        query_params = {
            "threshold_direction": str(threshold_direction),
            "threshold_direction_probabilities": dict(threshold_direction_probabilities),
            "threshold_value": int(threshold_value),
            "threshold_phrase": str(threshold_phrase),
            "target_bin_indices": [int(value) for value in target_bin_indices],
        }
    elif str(query_variant) == "numeric_interval_region_count":
        max_span = min(4, max(2, bin_count - 1))
        span = _balanced_int(
            list(range(2, max_span + 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.interval_span",
        )
        low_bin = _balanced_int(
            list(range(0, bin_count - int(span) + 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.interval_low_bin",
        )
        high_bin = int(low_bin) + int(span) - 1
        target_bin_indices = list(range(int(low_bin), int(high_bin) + 1))
        nonmatching_bin_indices = [index for index in range(bin_count) if index not in set(target_bin_indices)]
        if not nonmatching_bin_indices:
            raise ValueError("interval query must leave at least one nonmatching legend bin")
        lower = int(legend_bins[int(low_bin)]["lower"])
        upper = int(legend_bins[int(high_bin)]["upper"])
        _assign_matching_bins(
            regions_by_id=regions_by_id,
            selected_ids=evidence_region_ids,
            matching_bins=target_bin_indices,
            nonmatching_bins=nonmatching_bin_indices,
            legend_bins=legend_bins,
            rng=rng,
        )
        query_params = {
            "interval_lower": int(lower),
            "interval_upper": int(upper),
            "interval_phrase": f"between {lower} and {upper}, inclusive",
            "interval_bin_span": int(span),
            "target_bin_indices": [int(value) for value in target_bin_indices],
        }
    elif str(query_variant) == "categorical_region_count":
        category_index = _balanced_int(
            list(range(bin_count)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.category_index",
        )
        target_bin_indices = [int(category_index)]
        nonmatching_bin_indices = [index for index in range(bin_count) if int(index) != int(category_index)]
        _assign_matching_bins(
            regions_by_id=regions_by_id,
            selected_ids=evidence_region_ids,
            matching_bins=target_bin_indices,
            nonmatching_bins=nonmatching_bin_indices,
            legend_bins=legend_bins,
            rng=rng,
        )
        query_params = {
            "category_index": int(category_index),
            "category_label": str(legend_bins[int(category_index)]["bin_label"]),
            "target_bin_indices": [int(category_index)],
        }
    elif str(query_variant) == "adjacent_same_category_count":
        reference_region_id = str(map_asset_meta.get("reference_region_id") or "")
        if not reference_region_id:
            raise ValueError("adjacent same-category task did not construct a reference region")
        category_index = _balanced_int(
            list(range(bin_count)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.adjacent_same_category_index",
        )
        target_bin_indices = [int(category_index)]
        nonmatching_bin_indices = [index for index in range(bin_count) if int(index) != int(category_index)]
        _assign_matching_bins(
            regions_by_id=regions_by_id,
            selected_ids=[*evidence_region_ids, str(reference_region_id)],
            matching_bins=target_bin_indices,
            nonmatching_bins=nonmatching_bin_indices,
            legend_bins=legend_bins,
            rng=rng,
        )
        query_params = {
            "reference_region_id": str(reference_region_id),
            "adjacent_neighbor_region_ids": [str(value) for value in map_asset_meta.get("adjacent_neighbor_region_ids", [])],
            "category_index": int(category_index),
            "category_label": str(legend_bins[int(category_index)]["bin_label"]),
            "target_bin_indices": [int(category_index)],
        }
    elif str(query_variant) == "adjacent_category_count":
        reference_region_id = str(map_asset_meta.get("reference_region_id") or "")
        if not reference_region_id:
            raise ValueError("adjacent category task did not construct a reference region")
        category_index = _balanced_int(
            list(range(bin_count)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.adjacent_category_index",
        )
        target_bin_indices = [int(category_index)]
        nonmatching_bin_indices = [index for index in range(bin_count) if int(index) != int(category_index)]
        _assign_matching_bins(
            regions_by_id=regions_by_id,
            selected_ids=evidence_region_ids,
            matching_bins=target_bin_indices,
            nonmatching_bins=nonmatching_bin_indices,
            legend_bins=legend_bins,
            rng=rng,
        )
        query_params = {
            "reference_region_id": str(reference_region_id),
            "adjacent_neighbor_region_ids": [str(value) for value in map_asset_meta.get("adjacent_neighbor_region_ids", [])],
            "category_index": int(category_index),
            "category_label": str(legend_bins[int(category_index)]["bin_label"]),
            "target_bin_indices": [int(category_index)],
        }
    elif str(query_variant) == "adjacent_numeric_threshold_count":
        reference_region_id = str(map_asset_meta.get("reference_region_id") or "")
        if not reference_region_id:
            raise ValueError("adjacent threshold task did not construct a reference region")
        threshold_direction, threshold_direction_probabilities = _resolve_threshold_direction(
            params,
            instance_seed=int(instance_seed),
        )
        if str(threshold_direction) == "greater_than":
            threshold_bin = _balanced_int(
                list(range(0, bin_count - 1)),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.adjacent_threshold_bin.greater_than",
            )
            threshold_value = int(legend_bins[int(threshold_bin)]["upper"])
            target_bin_indices = list(range(int(threshold_bin) + 1, bin_count))
            nonmatching_bin_indices = list(range(0, int(threshold_bin) + 1))
            threshold_phrase = f"greater than {threshold_value}"
        else:
            threshold_bin = _balanced_int(
                list(range(1, bin_count)),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.adjacent_threshold_bin.less_than",
            )
            threshold_value = int(legend_bins[int(threshold_bin)]["lower"])
            target_bin_indices = list(range(0, int(threshold_bin)))
            nonmatching_bin_indices = list(range(int(threshold_bin), bin_count))
            threshold_phrase = f"less than {threshold_value}"
        _assign_matching_bins(
            regions_by_id=regions_by_id,
            selected_ids=evidence_region_ids,
            matching_bins=target_bin_indices,
            nonmatching_bins=nonmatching_bin_indices,
            legend_bins=legend_bins,
            rng=rng,
        )
        query_params = {
            "reference_region_id": str(reference_region_id),
            "adjacent_neighbor_region_ids": [str(value) for value in map_asset_meta.get("adjacent_neighbor_region_ids", [])],
            "threshold_direction": str(threshold_direction),
            "threshold_direction_probabilities": dict(threshold_direction_probabilities),
            "threshold_value": int(threshold_value),
            "threshold_phrase": str(threshold_phrase),
            "target_bin_indices": [int(value) for value in target_bin_indices],
        }
    elif str(query_variant) == "continent_region_count":
        for region_id in region_ids:
            _apply_bin(
                regions_by_id,
                region_id=str(region_id),
                bin_index=int(rng.randrange(bin_count)),
                legend_bins=legend_bins,
            )
        target_bin_indices = []
        nonmatching_bin_indices = list(range(bin_count))
        query_params = {
            "continent_label": str(map_asset_meta.get("target_continent") or ""),
            "target_continent": str(map_asset_meta.get("target_continent") or ""),
            "target_bin_indices": [],
        }
    elif str(query_variant) == "continent_category_region_count":
        category_index = _balanced_int(
            list(range(bin_count)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.continent_category_index",
        )
        target_bin_indices = [int(category_index)]
        nonmatching_bin_indices = [index for index in range(bin_count) if int(index) != int(category_index)]
        _assign_matching_bins(
            regions_by_id=regions_by_id,
            selected_ids=evidence_region_ids,
            matching_bins=target_bin_indices,
            nonmatching_bins=nonmatching_bin_indices,
            legend_bins=legend_bins,
            rng=rng,
        )
        outside_continent_ids = [
            str(region_id)
            for region_id in region_ids
            if str(region_id) not in set(evidence_region_ids)
            and str(regions_by_id[str(region_id)].get("continent") or "") != str(map_asset_meta.get("target_continent") or "")
        ]
        for region_id in rng.sample(outside_continent_ids, min(len(outside_continent_ids), max(1, int(target_count)))):
            _apply_bin(
                regions_by_id,
                region_id=str(region_id),
                bin_index=int(_choose_random(target_bin_indices, rng=rng)),
                legend_bins=legend_bins,
            )
        query_params = {
            "continent_label": str(map_asset_meta.get("target_continent") or ""),
            "target_continent": str(map_asset_meta.get("target_continent") or ""),
            "category_index": int(category_index),
            "category_label": str(legend_bins[int(category_index)]["bin_label"]),
            "target_bin_indices": [int(category_index)],
        }
    elif str(query_variant) == "continent_threshold_region_count":
        threshold_direction, threshold_direction_probabilities = _resolve_threshold_direction(
            params,
            instance_seed=int(instance_seed),
        )
        if str(threshold_direction) == "greater_than":
            threshold_bin = _balanced_int(
                list(range(0, bin_count - 1)),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.continent_threshold_bin.greater_than",
            )
            threshold_value = int(legend_bins[int(threshold_bin)]["upper"])
            target_bin_indices = list(range(int(threshold_bin) + 1, bin_count))
            nonmatching_bin_indices = list(range(0, int(threshold_bin) + 1))
            threshold_phrase = f"greater than {threshold_value}"
        else:
            threshold_bin = _balanced_int(
                list(range(1, bin_count)),
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.continent_threshold_bin.less_than",
            )
            threshold_value = int(legend_bins[int(threshold_bin)]["lower"])
            target_bin_indices = list(range(0, int(threshold_bin)))
            nonmatching_bin_indices = list(range(int(threshold_bin), bin_count))
            threshold_phrase = f"less than {threshold_value}"
        _assign_matching_bins(
            regions_by_id=regions_by_id,
            selected_ids=evidence_region_ids,
            matching_bins=target_bin_indices,
            nonmatching_bins=nonmatching_bin_indices,
            legend_bins=legend_bins,
            rng=rng,
        )
        outside_continent_ids = [
            str(region_id)
            for region_id in region_ids
            if str(region_id) not in set(evidence_region_ids)
            and str(regions_by_id[str(region_id)].get("continent") or "") != str(map_asset_meta.get("target_continent") or "")
        ]
        for region_id in rng.sample(outside_continent_ids, min(len(outside_continent_ids), max(1, int(target_count)))):
            _apply_bin(
                regions_by_id,
                region_id=str(region_id),
                bin_index=int(_choose_random(target_bin_indices, rng=rng)),
                legend_bins=legend_bins,
            )
        query_params = {
            "continent_label": str(map_asset_meta.get("target_continent") or ""),
            "target_continent": str(map_asset_meta.get("target_continent") or ""),
            "threshold_direction": str(threshold_direction),
            "threshold_direction_probabilities": dict(threshold_direction_probabilities),
            "threshold_value": int(threshold_value),
            "threshold_phrase": str(threshold_phrase),
            "target_bin_indices": [int(value) for value in target_bin_indices],
        }
    elif str(query_variant) == "border_neighbor_count":
        for region_id in region_ids:
            _apply_bin(
                regions_by_id,
                region_id=str(region_id),
                bin_index=int(rng.randrange(bin_count)),
                legend_bins=legend_bins,
            )
        target_bin_indices = []
        nonmatching_bin_indices = list(range(bin_count))
        reference_region_id = str(map_asset_meta.get("reference_region_id") or "")
        if not reference_region_id:
            raise ValueError("border-neighbor task did not construct a reference region")
        query_params = {
            "reference_country_label": str(map_asset_meta.get("reference_country_label") or ""),
            "reference_region_id": str(reference_region_id),
            "reference_asset_region_id": str(map_asset_meta.get("reference_asset_region_id") or ""),
            "border_min_shared_length_deg": float(map_asset_meta.get("border_min_shared_length_deg") or 0.0),
            "border_neighbor_min_area_sqdeg": float(map_asset_meta.get("border_neighbor_min_area_sqdeg") or 0.0),
            "target_border_neighbor_region_ids": list(evidence_region_ids),
            "target_border_neighbor_asset_ids": [str(value) for value in map_asset_meta.get("border_neighbor_asset_ids", [])],
            "target_bin_indices": [],
        }
    else:
        raise ValueError(f"unsupported query_variant: {query_variant}")

    final_regions = [dict(regions_by_id[str(region_id)]) for region_id in region_ids]
    regions_by_id = {str(region["region_id"]): dict(region) for region in final_regions}
    world_scene = str(scene_variant) == "geographic_region_map"
    if world_scene and _is_world_border_query_variant(str(query_variant)):
        title_options = list(_WORLD_BORDER_TITLE_OPTIONS)
    elif world_scene and _is_categorical_query_variant(str(query_variant)):
        title_options = list(map_asset_meta.get("category_title_options", []))
    else:
        title_options = list(map_asset_meta.get("title_options", [])) if world_scene else []
    if not title_options:
        title_options = list(
            _WORLD_CATEGORY_TITLE_OPTIONS
            if world_scene and _is_categorical_query_variant(str(query_variant))
            else (_WORLD_TITLE_OPTIONS if world_scene else _TITLE_OPTIONS)
        )
    return {
        "scene_title": str(_choose_random(title_options, rng=rng)),
        "query_variant": str(query_variant),
        "scene_variant": str(scene_variant),
        "map_asset_id": str(map_asset_meta.get("asset_id") or (_WORLD_MAP_ASSET_ID if world_scene else "")),
        "geographic_map_variant": str(map_asset_meta.get("map_variant") or ""),
        "geographic_map_variant_probabilities": dict(map_asset_meta.get("map_variant_probabilities", {})),
        "map_display_name": str(map_asset_meta.get("display_name") or ""),
        "map_region_noun": str(map_asset_meta.get("region_noun") or ""),
        "map_object_description": str(map_asset_meta.get("object_description") or ""),
        "map_source": dict(map_asset_meta.get("source", {})),
        "rows": int(rows),
        "cols": int(cols),
        "region_count": int(len(final_regions)),
        "active_cells": [[int(row), int(col)] for row, col in active_cells],
        "legend_bins": [dict(item) for item in legend_bins],
        "regions": final_regions,
        "regions_by_id": dict(regions_by_id),
        "evidence_region_ids": list(evidence_region_ids),
        "answer_value": int(target_count),
        "answer_type": "integer",
        "target_count": int(target_count),
        "target_count_probabilities": uniform_probability_map(tuple(target_support)),
        "question_params": dict(query_params),
        "target_bin_indices": [int(value) for value in target_bin_indices],
        "nonmatching_bin_indices": [int(value) for value in nonmatching_bin_indices],
        "threshold_direction": str(threshold_direction),
    }


def _layout_bboxes(render_params: _MapRenderParams) -> Tuple[BBox, BBox, BBox, BBox]:
    outer = float(render_params.outer_margin_px)
    offset_x = float(render_params.layout_offset_x_px)
    offset_y = float(render_params.layout_offset_y_px)
    panel_bbox: BBox = (
        outer + offset_x,
        outer + offset_y,
        float(render_params.canvas_width) - outer + offset_x,
        float(render_params.canvas_height) - outer + offset_y,
    )
    title_bbox: BBox = (
        panel_bbox[0] + float(render_params.panel_padding_px),
        panel_bbox[1] + 10.0,
        panel_bbox[2] - float(render_params.panel_padding_px),
        panel_bbox[1] + float(render_params.title_band_height_px),
    )
    content_top = float(title_bbox[3] + 12.0)
    content_bottom = float(panel_bbox[3] - render_params.panel_padding_px)
    if str(render_params.legend_position) == "none":
        legend_bbox = (0.0, 0.0, 0.0, 0.0)
        map_bbox = (
            float(panel_bbox[0] + render_params.panel_padding_px),
            content_top,
            float(panel_bbox[2] - render_params.panel_padding_px),
            content_bottom,
        )
    elif str(render_params.legend_position) == "bottom":
        legend_bbox = (
            float(panel_bbox[0] + render_params.panel_padding_px),
            float(content_bottom - render_params.legend_height_px),
            float(panel_bbox[2] - render_params.panel_padding_px),
            float(content_bottom),
        )
        map_bbox = (
            float(panel_bbox[0] + render_params.panel_padding_px),
            content_top,
            float(panel_bbox[2] - render_params.panel_padding_px),
            float(legend_bbox[1] - render_params.map_legend_gap_px),
        )
    elif str(render_params.legend_position) == "top":
        legend_bbox = (
            float(panel_bbox[0] + render_params.panel_padding_px),
            content_top,
            float(panel_bbox[2] - render_params.panel_padding_px),
            float(content_top + render_params.legend_height_px),
        )
        map_bbox = (
            float(panel_bbox[0] + render_params.panel_padding_px),
            float(legend_bbox[3] + render_params.map_legend_gap_px),
            float(panel_bbox[2] - render_params.panel_padding_px),
            content_bottom,
        )
    else:
        legend_left = float(panel_bbox[2] - render_params.panel_padding_px - render_params.legend_width_px)
        map_bbox = (
            float(panel_bbox[0] + render_params.panel_padding_px),
            content_top,
            float(legend_left - render_params.map_legend_gap_px),
            content_bottom,
        )
        legend_bbox = (
            legend_left,
            content_top,
            float(panel_bbox[2] - render_params.panel_padding_px),
            content_bottom,
        )
    return panel_bbox, title_bbox, map_bbox, legend_bbox


def _draw_legend(
    draw: ImageDraw.ImageDraw,
    *,
    legend_bins: Sequence[Mapping[str, Any]],
    legend_bbox: BBox,
    render_params: _MapRenderParams,
    categorical: bool,
) -> Dict[str, List[float]]:
    if str(render_params.legend_position) == "none":
        return {}
    draw_rounded_rect(
        draw,
        legend_bbox,
        radius=12,
        fill=render_params.legend_fill_rgb,
        outline=render_params.map_border_rgb,
        width=2,
    )
    palette = list(render_params.map_palette_rgb)
    legend_entry_bbox_map: Dict[str, List[float]] = {}
    title = "Category legend" if bool(categorical) else "Value legend"
    title_bbox = (
        legend_bbox[0] + 12.0,
        legend_bbox[1] + 10.0,
        legend_bbox[2] - 12.0,
        legend_bbox[1] + 42.0,
    )
    draw_centered_text(
        draw,
        text=title,
        center=(0.5 * (title_bbox[0] + title_bbox[2]), 0.5 * (title_bbox[1] + title_bbox[3])),
        font=load_font(int(render_params.legend_font_size_px) + 2, bold=True),
        fill=render_params.legend_text_rgb,
        stroke_fill=render_params.legend_fill_rgb,
        stroke_width=1,
    )

    if str(render_params.legend_position) in {"bottom", "top"}:
        count = max(1, len(legend_bins))
        start_x = legend_bbox[0] + 18.0
        usable_w = max(1.0, legend_bbox[2] - legend_bbox[0] - 36.0)
        cell_w = usable_w / float(count)
        swatch_h = 26.0
        swatch_y0 = legend_bbox[1] + 52.0
        label_y0 = swatch_y0 + swatch_h + 3.0
        for index, bin_spec in enumerate(legend_bins):
            left = float(start_x + (index * cell_w) + 4.0)
            right = float(start_x + ((index + 1) * cell_w) - 4.0)
            swatch_bbox = (left, swatch_y0, right, swatch_y0 + swatch_h)
            fill = tuple(int(channel) for channel in palette[int(index) % len(palette)])
            draw.rounded_rectangle(
                swatch_bbox,
                radius=5,
                fill=fill,
                outline=tuple(int(channel) for channel in render_params.map_border_rgb),
                width=1,
            )
            text_bbox = (left - 2.0, label_y0, right + 2.0, legend_bbox[3] - 10.0)
            draw_centered_text(
                draw,
                text=str(bin_spec["bin_label"]),
                center=(0.5 * (text_bbox[0] + text_bbox[2]), 0.5 * (text_bbox[1] + text_bbox[3])),
                font=fit_font_to_box(
                    draw,
                    text=str(bin_spec["bin_label"]),
                    max_width=max(1.0, float(text_bbox[2] - text_bbox[0])),
                    max_height=max(1.0, float(text_bbox[3] - text_bbox[1])),
                    bold=True,
                    min_size_px=9,
                    max_size_px=int(render_params.legend_font_size_px),
                    fill_ratio=0.92,
                ),
                fill=render_params.legend_text_rgb,
                stroke_fill=render_params.legend_fill_rgb,
                stroke_width=1,
            )
            legend_entry_bbox_map[str(bin_spec["bin_id"])] = _round_bbox(swatch_bbox)
    else:
        row_top = legend_bbox[1] + 56.0
        row_step = max(38.0, min(55.0, (legend_bbox[3] - row_top - 14.0) / max(1.0, float(len(legend_bins)))))
        for index, bin_spec in enumerate(legend_bins):
            top = float(row_top + (float(index) * row_step))
            swatch_bbox = (
                float(legend_bbox[0] + 18.0),
                top,
                float(legend_bbox[0] + 66.0),
                top + min(31.0, row_step - 8.0),
            )
            fill = tuple(int(channel) for channel in palette[int(index) % len(palette)])
            draw.rounded_rectangle(
                swatch_bbox,
                radius=6,
                fill=fill,
                outline=tuple(int(channel) for channel in render_params.map_border_rgb),
                width=1,
            )
            text_bbox = (
                float(swatch_bbox[2] + 10.0),
                float(top - 2.0),
                float(legend_bbox[2] - 10.0),
                float(top + min(35.0, row_step - 4.0)),
            )
            draw_centered_text(
                draw,
                text=str(bin_spec["bin_label"]),
                center=(0.5 * (text_bbox[0] + text_bbox[2]), 0.5 * (text_bbox[1] + text_bbox[3])),
                font=fit_font_to_box(
                    draw,
                    text=str(bin_spec["bin_label"]),
                    max_width=max(1.0, float(text_bbox[2] - text_bbox[0])),
                    max_height=max(1.0, float(text_bbox[3] - text_bbox[1])),
                    bold=True,
                    min_size_px=9,
                    max_size_px=int(render_params.legend_font_size_px),
                    fill_ratio=0.94,
                ),
                fill=render_params.legend_text_rgb,
                stroke_fill=render_params.legend_fill_rgb,
                stroke_width=1,
            )
            legend_entry_bbox_map[str(bin_spec["bin_id"])] = _round_bbox(swatch_bbox)
    return dict(legend_entry_bbox_map)


def _project_world_point(
    point: Sequence[float],
    *,
    map_bbox: BBox,
    lon_bounds: Sequence[float],
    lat_bounds: Sequence[float],
) -> Point:
    lon = float(point[0])
    lat = float(point[1])
    lon_min, lon_max = float(lon_bounds[0]), float(lon_bounds[1])
    lat_min, lat_max = float(lat_bounds[0]), float(lat_bounds[1])
    lon = max(lon_min, min(lon_max, lon))
    lat = max(lat_min, min(lat_max, lat))
    x = float(map_bbox[0]) + ((lon - lon_min) / max(1e-9, lon_max - lon_min)) * float(map_bbox[2] - map_bbox[0])
    y = float(map_bbox[1]) + ((lat_max - lat) / max(1e-9, lat_max - lat_min)) * float(map_bbox[3] - map_bbox[1])
    return (float(x), float(y))


def _project_world_rings(
    rings: Sequence[Sequence[Sequence[float]]],
    *,
    map_bbox: BBox,
    lon_bounds: Sequence[float],
    lat_bounds: Sequence[float],
) -> List[List[Point]]:
    projected: List[List[Point]] = []
    for ring in rings:
        points = [
            _project_world_point(point, map_bbox=map_bbox, lon_bounds=lon_bounds, lat_bounds=lat_bounds)
            for point in ring
            if len(point) >= 2
        ]
        if len(points) >= 3:
            projected.append(points)
    return projected


def _fit_bbox_to_aspect(container_bbox: BBox, *, target_aspect: float) -> BBox:
    left, top, right, bottom = [float(value) for value in container_bbox]
    width = max(1.0, float(right - left))
    height = max(1.0, float(bottom - top))
    aspect = width / height
    if aspect > float(target_aspect):
        fitted_width = height * float(target_aspect)
        x0 = left + ((width - fitted_width) / 2.0)
        return (float(x0), top, float(x0 + fitted_width), bottom)
    fitted_height = width / float(target_aspect)
    y0 = top + ((height - fitted_height) / 2.0)
    return (left, float(y0), right, float(y0 + fitted_height))


def _draw_world_graticule(
    draw: ImageDraw.ImageDraw,
    *,
    map_bbox: BBox,
    lon_bounds: Sequence[float],
    lat_bounds: Sequence[float],
    color: Tuple[int, int, int],
    width_px: int = 1,
) -> None:
    for lon in range(-120, 181, 60):
        p0 = _project_world_point((float(lon), float(lat_bounds[0])), map_bbox=map_bbox, lon_bounds=lon_bounds, lat_bounds=lat_bounds)
        p1 = _project_world_point((float(lon), float(lat_bounds[1])), map_bbox=map_bbox, lon_bounds=lon_bounds, lat_bounds=lat_bounds)
        draw.line([p0, p1], fill=color, width=max(1, int(width_px)))
    for lat in range(-30, 61, 30):
        p0 = _project_world_point((float(lon_bounds[0]), float(lat)), map_bbox=map_bbox, lon_bounds=lon_bounds, lat_bounds=lat_bounds)
        p1 = _project_world_point((float(lon_bounds[1]), float(lat)), map_bbox=map_bbox, lon_bounds=lon_bounds, lat_bounds=lat_bounds)
        draw.line([p0, p1], fill=color, width=max(1, int(width_px)))


def _render_world_choropleth_map(
    background: Image.Image,
    *,
    scene_title: str,
    map_asset_id: str,
    regions: Sequence[Mapping[str, Any]],
    legend_bins: Sequence[Mapping[str, Any]],
    render_params: _MapRenderParams,
    instance_seed: int,
    categorical: bool,
    draw_color_legend: bool = True,
    neutral_regions: bool = False,
) -> _RenderedChoroplethMap:
    image = background.copy()
    draw = ImageDraw.Draw(image)
    entities: List[Dict[str, Any]] = []
    region_bbox_map: Dict[str, List[float]] = {}
    region_center_map: Dict[str, List[float]] = {}

    panel_bbox, title_bbox, map_bbox_raw, legend_bbox = _layout_bboxes(render_params)
    asset = _load_geographic_map_asset(str(map_asset_id or "world_countries"))
    lon_bounds = [float(value) for value in asset.get("lon_bounds", [-180.0, 180.0])]
    lat_bounds = [float(value) for value in asset.get("lat_bounds", [-58.0, 84.0])]
    world_aspect = abs(float(lon_bounds[1] - lon_bounds[0])) / max(1e-9, abs(float(lat_bounds[1] - lat_bounds[0])))
    map_bbox = _fit_bbox_to_aspect(
        (
            float(map_bbox_raw[0] + 18.0),
            float(map_bbox_raw[1] + 18.0),
            float(map_bbox_raw[2] - 18.0),
            float(map_bbox_raw[3] - 16.0),
        ),
        target_aspect=float(world_aspect),
    )
    style_id = str(render_params.world_map_style_id)
    style_probabilities = dict(render_params.world_map_style_probabilities)
    style = dict(render_params.world_map_style)
    ocean_rgb = _rgb(style.get("ocean_rgb"), (230, 239, 245))
    land_fill = _rgb(style.get("land_fill_rgb"), (215, 221, 219))
    land_outline = _rgb(style.get("land_outline_rgb"), (132, 144, 148))
    selected_outline = _rgb(style.get("selected_outline_rgb"), (38, 45, 52))
    reference_fill = _rgb(style.get("reference_fill_rgb"), (255, 240, 138))
    reference_outline = _rgb(style.get("reference_outline_rgb"), (20, 28, 36))
    neutral_selected_fill = _rgb(style.get("marker_region_fill_rgb"), (235, 238, 232))
    graticule_rgb = _rgb(style.get("graticule_rgb"), (200, 214, 222))
    graticule_width = max(1, int(style.get("graticule_width_px", 1)))
    selected_outline_width = max(1, int(style.get("selected_outline_width_px", 2)))
    show_graticule = bool(style.get("show_graticule", True))
    draw_rounded_rect(
        draw,
        panel_bbox,
        radius=16,
        fill=render_params.panel_fill_rgb,
        outline=render_params.panel_border_rgb,
        width=2,
    )
    draw.rounded_rectangle(
        map_bbox_raw,
        radius=12,
        fill=ocean_rgb,
        outline=tuple(int(channel) for channel in render_params.map_border_rgb),
        width=2,
    )
    title_text_bbox = draw_centered_text(
        draw,
        text=str(scene_title),
        center=(0.5 * (title_bbox[0] + title_bbox[2]), 0.5 * (title_bbox[1] + title_bbox[3])),
        font=load_font(int(render_params.title_font_size_px), bold=True),
        fill=render_params.title_color_rgb,
        stroke_fill=render_params.panel_fill_rgb,
        stroke_width=1,
    )

    selected_by_asset_id = {str(region["asset_region_id"]): dict(region) for region in regions}
    selected_region_id_by_asset_id = {
        str(region["asset_region_id"]): str(region["region_id"])
        for region in regions
    }
    border_reference_scene = (
        str(render_params.legend_position) == "none"
        and any(bool(region.get("is_reference_region")) for region in regions)
    )
    palette = list(render_params.map_palette_rgb)

    if show_graticule:
        _draw_world_graticule(
            draw,
            map_bbox=map_bbox,
            lon_bounds=lon_bounds,
            lat_bounds=lat_bounds,
            color=graticule_rgb,
            width_px=graticule_width,
        )

    selected_projected: Dict[str, List[List[Point]]] = {}
    all_region_boxes: List[List[float]] = []
    for asset_region in asset.get("regions", []):
        if not isinstance(asset_region, Mapping):
            continue
        asset_region_id = str(asset_region.get("region_id"))
        projected_rings = _project_world_rings(
            asset_region.get("rings", []),
            map_bbox=map_bbox,
            lon_bounds=lon_bounds,
            lat_bounds=lat_bounds,
        )
        if not projected_rings:
            continue
        region_spec = selected_by_asset_id.get(asset_region_id)
        fill = land_fill
        outline = land_outline
        line_width = 1
        if region_spec is not None:
            if bool(region_spec.get("is_reference_region")):
                fill = reference_fill
                outline = reference_outline
                line_width = max(4, int(selected_outline_width) + 2)
            elif bool(border_reference_scene):
                fill = land_fill
                outline = land_outline
                line_width = 1
            elif bool(neutral_regions):
                fill = neutral_selected_fill
                outline = selected_outline
                line_width = selected_outline_width
            else:
                fill = tuple(int(channel) for channel in palette[int(region_spec["bin_index"]) % len(palette)])
                outline = selected_outline
                line_width = selected_outline_width
            selected_projected[selected_region_id_by_asset_id[asset_region_id]] = projected_rings
        for ring in projected_rings:
            draw.polygon(ring, fill=fill, outline=outline)
            draw.line(ring + [ring[0]], fill=outline, width=line_width, joint="curve")
            all_region_boxes.append(_polygon_bbox(ring))

    for region in regions:
        region_id = str(region["region_id"])
        rings = selected_projected.get(region_id, [])
        bbox = _bbox_union(_polygon_bbox(ring) for ring in rings) if rings else [0.0, 0.0, 0.0, 0.0]
        centroid_lonlat = region.get("centroid_lonlat", [0.0, 0.0])
        center = _project_world_point(
            centroid_lonlat,
            map_bbox=map_bbox,
            lon_bounds=lon_bounds,
            lat_bounds=lat_bounds,
        )
        region_bbox_map[region_id] = list(bbox)
        region_center_map[region_id] = [round(float(center[0]), 3), round(float(center[1]), 3)]
        entities.append(
            {
                "entity_id": region_id,
                "entity_type": "world_choropleth_country",
                "bbox_xyxy": list(bbox),
                "attrs": {
                    "asset_region_id": str(region["asset_region_id"]),
                    "display_name": str(region["display_name"]),
                    "continent": str(region.get("continent") or ""),
                    "bin_index": int(region["bin_index"]),
                    "bin_label": str(region["bin_label"]),
                    "bin_lower": region.get("bin_lower"),
                    "bin_upper": region.get("bin_upper"),
                    "category": str(region.get("category") or ""),
                    "is_reference_region": bool(region.get("is_reference_region")),
                    "center_px": list(region_center_map[region_id]),
                    "centroid_lonlat": list(region.get("centroid_lonlat", [])),
                },
            }
        )

    legend_entry_bbox_map = (
        _draw_legend(
            draw,
            legend_bins=legend_bins,
            legend_bbox=legend_bbox,
            render_params=render_params,
            categorical=bool(categorical),
        )
        if bool(draw_color_legend)
        else {}
    )
    map_shape_bbox = _bbox_union(all_region_boxes) if all_region_boxes else _round_bbox(map_bbox)
    entities.insert(0, {"entity_id": "map_panel", "entity_type": "map_panel", "bbox_xyxy": _round_bbox(panel_bbox)})
    entities.insert(
        1,
        {
            "entity_id": "map_title",
            "entity_type": "map_title",
            "bbox_xyxy": list(title_text_bbox),
            "attrs": {"title": str(scene_title)},
        },
    )
    entities.insert(2, {"entity_id": "world_choropleth_map_shape", "entity_type": "world_choropleth_map_shape", "bbox_xyxy": list(map_shape_bbox)})
    return _RenderedChoroplethMap(
        image=image,
        entities=tuple(dict(item) for item in entities),
        panel_bbox_px=_round_bbox(panel_bbox),
        title_bbox_px=list(title_text_bbox),
        map_bbox_px=list(map_shape_bbox),
        legend_bbox_px=_round_bbox(legend_bbox),
        region_bbox_map=dict(region_bbox_map),
        region_center_map=dict(region_center_map),
        legend_entry_bbox_map=dict(legend_entry_bbox_map),
        render_meta={
            "world_map_style": {
                "style_id": str(style_id),
                "style_probabilities": dict(style_probabilities),
                "ocean_rgb": [int(channel) for channel in ocean_rgb],
                "land_fill_rgb": [int(channel) for channel in land_fill],
                "land_outline_rgb": [int(channel) for channel in land_outline],
                "selected_outline_rgb": [int(channel) for channel in selected_outline],
                "reference_fill_rgb": [int(channel) for channel in reference_fill],
                "reference_outline_rgb": [int(channel) for channel in reference_outline],
                "graticule_rgb": [int(channel) for channel in graticule_rgb],
                "show_graticule": bool(show_graticule),
            },
            "world_projection_bbox_px": _round_bbox(map_bbox),
            "world_projection_aspect": round(float(world_aspect), 6),
        },
    )


def _render_choropleth_map(
    background: Image.Image,
    *,
    scene_title: str,
    rows: int,
    cols: int,
    regions: Sequence[Mapping[str, Any]],
    legend_bins: Sequence[Mapping[str, Any]],
    render_params: _MapRenderParams,
    instance_seed: int,
    categorical: bool,
    draw_color_legend: bool = True,
    neutral_regions: bool = False,
) -> _RenderedChoroplethMap:
    image = background.copy()
    draw = ImageDraw.Draw(image)
    entities: List[Dict[str, Any]] = []
    region_bbox_map: Dict[str, List[float]] = {}
    region_center_map: Dict[str, List[float]] = {}

    panel_bbox, title_bbox, map_bbox, legend_bbox = _layout_bboxes(render_params)
    draw_rounded_rect(
        draw,
        panel_bbox,
        radius=16,
        fill=render_params.panel_fill_rgb,
        outline=render_params.panel_border_rgb,
        width=2,
    )
    title_text_bbox = draw_centered_text(
        draw,
        text=str(scene_title),
        center=(0.5 * (title_bbox[0] + title_bbox[2]), 0.5 * (title_bbox[1] + title_bbox[3])),
        font=load_font(int(render_params.title_font_size_px), bold=True),
        fill=render_params.title_color_rgb,
        stroke_fill=render_params.panel_fill_rgb,
        stroke_width=1,
    )

    grid_points = _grid_points(
        rows=int(rows),
        cols=int(cols),
        map_bbox=(
            map_bbox[0] + 20.0,
            map_bbox[1] + 22.0,
            map_bbox[2] - 20.0,
            map_bbox[3] - 18.0,
        ),
        instance_seed=int(instance_seed),
    )

    palette = list(render_params.map_palette_rgb)
    reference_fill = _rgb(render_params.world_map_style.get("reference_fill_rgb"), (255, 240, 138))
    reference_outline = _rgb(render_params.world_map_style.get("reference_outline_rgb"), (20, 28, 36))
    neutral_fills = (
        (235, 238, 232),
        (229, 235, 236),
        (238, 235, 229),
        (233, 232, 240),
    )
    polygons: Dict[str, List[Point]] = {}
    for region in regions:
        region_id = str(region["region_id"])
        polygon = _region_polygon(row=int(region["row"]), col=int(region["col"]), grid_points=grid_points)
        display_polygon = _shrink_polygon(polygon, gap_px=float(render_params.region_gap_px))
        polygons[region_id] = list(display_polygon)

    map_shape_bbox = _bbox_union(_polygon_bbox(points) for points in polygons.values())

    for region in regions:
        region_id = str(region["region_id"])
        display_polygon = polygons[str(region_id)]
        bin_index = int(region["bin_index"])
        fill = tuple(int(channel) for channel in palette[int(bin_index) % len(palette)])
        outline = tuple(int(channel) for channel in render_params.map_border_rgb)
        line_width = max(1, int(render_params.region_border_width_px) - 1)
        if bool(region.get("is_reference_region")):
            fill = reference_fill
            outline = reference_outline
            line_width = max(4, int(render_params.region_border_width_px) + 1)
        elif bool(neutral_regions):
            fill = neutral_fills[int(_region_sort_key(region_id)[1]) % len(neutral_fills)] if isinstance(_region_sort_key(region_id)[1], int) else neutral_fills[0]
            outline = tuple(int(channel) for channel in render_params.map_border_rgb)
            line_width = max(2, int(render_params.region_border_width_px) - 1)
        draw.polygon(
            display_polygon,
            fill=fill,
            outline=tuple(int(channel) for channel in render_params.region_border_rgb),
        )
        draw.line(
            display_polygon + [display_polygon[0]],
            fill=outline,
            width=int(line_width),
            joint="curve",
        )
        bbox = _polygon_bbox(display_polygon)
        center = _polygon_center(display_polygon)
        region_bbox_map[region_id] = list(bbox)
        region_center_map[region_id] = [round(float(center[0]), 3), round(float(center[1]), 3)]
        entities.append(
            {
                "entity_id": region_id,
                "entity_type": "choropleth_region",
                "bbox_xyxy": list(bbox),
                "attrs": {
                    "row": int(region["row"]),
                    "col": int(region["col"]),
                    "bin_index": int(bin_index),
                    "bin_label": str(region["bin_label"]),
                    "bin_lower": region.get("bin_lower"),
                    "bin_upper": region.get("bin_upper"),
                    "category": str(region.get("category") or ""),
                    "is_reference_region": bool(region.get("is_reference_region")),
                    "center_px": list(region_center_map[region_id]),
                },
            }
        )

    legend_entry_bbox_map = (
        _draw_legend(
            draw,
            legend_bins=legend_bins,
            legend_bbox=legend_bbox,
            render_params=render_params,
            categorical=bool(categorical),
        )
        if bool(draw_color_legend)
        else {}
    )

    entities.insert(0, {"entity_id": "map_panel", "entity_type": "map_panel", "bbox_xyxy": _round_bbox(panel_bbox)})
    entities.insert(
        1,
        {
            "entity_id": "map_title",
            "entity_type": "map_title",
            "bbox_xyxy": list(title_text_bbox),
            "attrs": {"title": str(scene_title)},
        },
    )
    entities.insert(2, {"entity_id": "choropleth_map_shape", "entity_type": "choropleth_map_shape", "bbox_xyxy": list(map_shape_bbox)})
    return _RenderedChoroplethMap(
        image=image,
        entities=tuple(dict(item) for item in entities),
        panel_bbox_px=_round_bbox(panel_bbox),
        title_bbox_px=list(title_text_bbox),
        map_bbox_px=list(map_shape_bbox),
        legend_bbox_px=_round_bbox(legend_bbox),
        region_bbox_map=dict(region_bbox_map),
        region_center_map=dict(region_center_map),
        legend_entry_bbox_map=dict(legend_entry_bbox_map),
        render_meta={
            "map_style": {"style_id": "synthetic_irregular_default"},
        },
    )


_MARKER_STYLES: Dict[str, Dict[str, Tuple[int, int, int]]] = {
    "teal": {
        "fill": (20, 126, 136),
        "outline": (8, 70, 78),
        "label_fill": (255, 255, 255),
        "label_outline": (31, 55, 64),
    },
    "coral": {
        "fill": (218, 88, 64),
        "outline": (122, 45, 34),
        "label_fill": (255, 255, 255),
        "label_outline": (97, 48, 41),
    },
    "violet": {
        "fill": (118, 94, 188),
        "outline": (61, 48, 112),
        "label_fill": (255, 255, 255),
        "label_outline": (54, 47, 84),
    },
    "gold": {
        "fill": (224, 166, 55),
        "outline": (121, 82, 28),
        "label_fill": (255, 255, 255),
        "label_outline": (88, 66, 40),
    },
    "ink": {
        "fill": (52, 74, 94),
        "outline": (20, 31, 43),
        "label_fill": (255, 255, 255),
        "label_outline": (20, 31, 43),
    },
}


def _resolve_marker_style(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float], Dict[str, Tuple[int, int, int]]]:
    style_id, probabilities = resolve_chart_axis_variant(
        params=params,
        gen_defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=tuple(sorted(_MARKER_STYLES.keys())),
        task_id=TASK_ID,
        explicit_key="marker_style_variant",
        weights_key="marker_style_variant_weights",
        balance_flag_key="balanced_marker_style_variant_sampling",
        axis_namespace="marker_style_variant",
    )
    return str(style_id), {str(key): float(value) for key, value in sorted(probabilities.items())}, dict(_MARKER_STYLES[str(style_id)])


def _clamp_marker_bbox(bbox: Sequence[float], *, width: int, height: int) -> List[float]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    return _round_bbox(
        [
            max(0.0, min(float(width) - 1.0, x0)),
            max(0.0, min(float(height) - 1.0, y0)),
            max(1.0, min(float(width), x1)),
            max(1.0, min(float(height), y1)),
        ]
    )


def _marker_unit_centers(center: Sequence[float], *, count: int, radius: float) -> List[Point]:
    x, y = float(center[0]), float(center[1])
    count = int(count)
    if count <= 1:
        return [(x, y)]
    cols = min(3, int(math.ceil(math.sqrt(float(count)))))
    rows = int(math.ceil(float(count) / float(cols)))
    gap = float(radius) * 2.35
    out: List[Point] = []
    for index in range(count):
        row = int(index // cols)
        col = int(index % cols)
        px = x + (float(col) - (float(cols) - 1.0) / 2.0) * gap
        py = y + (float(row) - (float(rows) - 1.0) / 2.0) * gap
        out.append((float(px), float(py)))
    return out


def _draw_marker_label(
    draw: ImageDraw.ImageDraw,
    *,
    label: str,
    center: Sequence[float],
    radius: float,
    render_params: _MapRenderParams,
    style: Mapping[str, Tuple[int, int, int]],
) -> List[float]:
    x, y = float(center[0]), float(center[1])
    label_w = 28.0 if len(str(label)) <= 1 else 38.0
    label_h = 24.0
    left = x + float(radius) + 5.0
    top = y - float(radius) - 4.0
    if left + label_w > float(render_params.canvas_width) - 8.0:
        left = x - float(radius) - label_w - 5.0
    if top < 8.0:
        top = y + float(radius) + 4.0
    bbox = (
        float(left),
        float(top),
        float(left + label_w),
        float(top + label_h),
    )
    draw.rounded_rectangle(
        bbox,
        radius=6,
        fill=style["label_fill"],
        outline=style["label_outline"],
        width=2,
    )
    draw_centered_text(
        draw,
        text=str(label),
        center=(0.5 * (bbox[0] + bbox[2]), 0.5 * (bbox[1] + bbox[3])),
        font=load_font(15, bold=True),
        fill=style["label_outline"],
        stroke_fill=style["label_fill"],
        stroke_width=1,
    )
    return _clamp_marker_bbox(bbox, width=int(render_params.canvas_width), height=int(render_params.canvas_height))


def _draw_marker_legend(
    draw: ImageDraw.ImageDraw,
    *,
    render_params: _MapRenderParams,
    marker_render_variant: str,
    value_min: int,
    value_max: int,
    style: Mapping[str, Tuple[int, int, int]],
) -> Dict[str, List[float]]:
    legend_bbox = tuple(float(value) for value in _layout_bboxes(render_params)[3])
    if str(render_params.legend_position) == "none":
        return {}
    draw_rounded_rect(
        draw,
        legend_bbox,
        radius=12,
        fill=render_params.legend_fill_rgb,
        outline=render_params.map_border_rgb,
        width=2,
    )
    title = "Marker value"
    title_bbox = (
        legend_bbox[0] + 12.0,
        legend_bbox[1] + 8.0,
        legend_bbox[2] - 12.0,
        legend_bbox[1] + 38.0,
    )
    draw_centered_text(
        draw,
        text=title,
        center=(0.5 * (title_bbox[0] + title_bbox[2]), 0.5 * (title_bbox[1] + title_bbox[3])),
        font=load_font(int(render_params.legend_font_size_px) + 2, bold=True),
        fill=render_params.legend_text_rgb,
        stroke_fill=render_params.legend_fill_rgb,
        stroke_width=1,
    )
    entries: Dict[str, List[float]] = {}
    values = list(range(int(value_min), int(value_max) + 1))
    if str(marker_render_variant) == "unit_bubble_count":
        note = "1 dot = 1"
        text_bbox = (
            legend_bbox[0] + 12.0,
            legend_bbox[1] + 48.0,
            legend_bbox[2] - 12.0,
            legend_bbox[1] + 76.0,
        )
        draw_centered_text(
            draw,
            text=note,
            center=(0.5 * (text_bbox[0] + text_bbox[2]), 0.5 * (text_bbox[1] + text_bbox[3])),
            font=load_font(int(render_params.legend_font_size_px), bold=True),
            fill=render_params.legend_text_rgb,
            stroke_fill=render_params.legend_fill_rgb,
            stroke_width=1,
        )
        sample_center = (legend_bbox[0] + 38.0, legend_bbox[1] + 94.0)
        r = 6.0
        bbox = (sample_center[0] - r, sample_center[1] - r, sample_center[0] + r, sample_center[1] + r)
        draw.ellipse(bbox, fill=style["fill"], outline=style["outline"], width=2)
        entries["marker_unit_value"] = _round_bbox(bbox)
        return entries

    count = len(values)
    if str(render_params.legend_position) in {"bottom", "top"}:
        start_x = legend_bbox[0] + 30.0
        usable_w = max(1.0, legend_bbox[2] - legend_bbox[0] - 60.0)
        row_y = legend_bbox[1] + 72.0
        for index, value in enumerate(values):
            x = start_x + (usable_w * float(index) / max(1.0, float(count - 1)))
            radius = 5.5 + ((float(value) - float(value_min)) / max(1.0, float(value_max - value_min))) * 11.0
            bbox = (x - radius, row_y - radius, x + radius, row_y + radius)
            draw.ellipse(bbox, fill=style["fill"], outline=style["outline"], width=2)
            draw_centered_text(
                draw,
                text=str(value),
                center=(float(x), float(row_y + 24.0)),
                font=load_font(12, bold=True),
                fill=render_params.legend_text_rgb,
                stroke_fill=render_params.legend_fill_rgb,
                stroke_width=1,
            )
            entries[f"marker_value_{value}"] = _round_bbox(bbox)
    else:
        start_y = legend_bbox[1] + 60.0
        step = max(30.0, min(42.0, (legend_bbox[3] - start_y - 16.0) / max(1.0, float(count))))
        for index, value in enumerate(values):
            y = start_y + (float(index) * step)
            x = legend_bbox[0] + 45.0
            radius = 5.0 + ((float(value) - float(value_min)) / max(1.0, float(value_max - value_min))) * 10.0
            bbox = (x - radius, y - radius, x + radius, y + radius)
            draw.ellipse(bbox, fill=style["fill"], outline=style["outline"], width=2)
            draw_centered_text(
                draw,
                text=str(value),
                center=(legend_bbox[0] + 96.0, y),
                font=load_font(int(render_params.legend_font_size_px), bold=True),
                fill=render_params.legend_text_rgb,
                stroke_fill=render_params.legend_fill_rgb,
                stroke_width=1,
            )
            entries[f"marker_value_{value}"] = _round_bbox(bbox)
    return entries


def _render_marker_layer(
    rendered_scene: _RenderedChoroplethMap,
    *,
    dataset: Mapping[str, Any],
    render_params: _MapRenderParams,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[_RenderedChoroplethMap, Dict[str, List[List[float]]], Dict[str, List[float]], Dict[str, Any]]:
    image = rendered_scene.image.copy()
    draw = ImageDraw.Draw(image)
    style_id, style_probabilities, style = _resolve_marker_style(params, instance_seed=int(instance_seed))
    marker_render_variant = str(dataset.get("marker_render_variant") or "proportional_bubble")
    show_marker_labels = str(dataset.get("query_variant")) == "marker_region_extremum_label"
    value_min = int(dataset.get("marker_value_min", 1))
    value_max = int(dataset.get("marker_value_max", 5))
    marker_bboxes_by_region: Dict[str, List[List[float]]] = {}
    marker_group_bbox_map: Dict[str, List[float]] = {}
    marker_entities: List[Dict[str, Any]] = []
    region_specs = [dict(region) for region in dataset.get("regions", []) if isinstance(region, Mapping)]

    base_radius = float(params.get("marker_unit_radius_px", _RENDER_DEFAULTS.get("marker_unit_radius_px", 6)))
    min_radius = float(params.get("marker_min_radius_px", _RENDER_DEFAULTS.get("marker_min_radius_px", 8)))
    max_radius = float(params.get("marker_max_radius_px", _RENDER_DEFAULTS.get("marker_max_radius_px", 22)))
    for region in region_specs:
        region_id = str(region["region_id"])
        center = rendered_scene.region_center_map.get(str(region_id))
        if not center:
            continue
        value = int(region.get("marker_value", value_min))
        label = str(region.get("marker_label", ""))
        bboxes: List[List[float]] = []
        if str(marker_render_variant) == "unit_bubble_count":
            for unit_index, unit_center in enumerate(_marker_unit_centers(center, count=int(value), radius=float(base_radius))):
                bbox = (
                    float(unit_center[0] - base_radius),
                    float(unit_center[1] - base_radius),
                    float(unit_center[0] + base_radius),
                    float(unit_center[1] + base_radius),
                )
                draw.ellipse(bbox, fill=style["fill"], outline=style["outline"], width=2)
                rounded = _clamp_marker_bbox(bbox, width=int(render_params.canvas_width), height=int(render_params.canvas_height))
                bboxes.append(list(rounded))
                marker_entities.append(
                    {
                        "entity_id": f"{region_id}_marker_{unit_index}",
                        "entity_type": "map_marker_bubble",
                        "bbox_xyxy": list(rounded),
                        "attrs": {
                            "region_id": str(region_id),
                            "marker_label": str(label),
                            "marker_value": int(value),
                            "unit_index": int(unit_index),
                            "marker_render_variant": str(marker_render_variant),
                        },
                    }
                )
            label_radius = max(float(base_radius) * 2.4, 14.0)
        else:
            radius = float(min_radius) + (
                (float(value) - float(value_min)) / max(1.0, float(value_max - value_min))
            ) * max(1.0, float(max_radius - min_radius))
            bbox = (
                float(center[0] - radius),
                float(center[1] - radius),
                float(center[0] + radius),
                float(center[1] + radius),
            )
            draw.ellipse(bbox, fill=style["fill"], outline=style["outline"], width=3)
            rounded = _clamp_marker_bbox(bbox, width=int(render_params.canvas_width), height=int(render_params.canvas_height))
            bboxes.append(list(rounded))
            marker_entities.append(
                {
                    "entity_id": f"{region_id}_marker",
                    "entity_type": "map_marker_bubble",
                    "bbox_xyxy": list(rounded),
                    "attrs": {
                        "region_id": str(region_id),
                        "marker_label": str(label),
                        "marker_value": int(value),
                        "marker_render_variant": str(marker_render_variant),
                    },
                }
            )
            label_radius = float(radius)
        if bool(show_marker_labels):
            label_bbox = _draw_marker_label(
                draw,
                label=str(label),
                center=center,
                radius=float(label_radius),
                render_params=render_params,
                style=style,
            )
            marker_entities.append(
                {
                    "entity_id": f"{region_id}_marker_label",
                    "entity_type": "map_marker_label",
                    "bbox_xyxy": list(label_bbox),
                    "attrs": {
                        "region_id": str(region_id),
                        "marker_label": str(label),
                        "marker_value": int(value),
                    },
                }
            )
        marker_bboxes_by_region[str(region_id)] = [list(bbox) for bbox in bboxes]
        marker_group_bbox_map[str(region_id)] = _bbox_union(bboxes)

    marker_legend_bbox_map = _draw_marker_legend(
        draw,
        render_params=render_params,
        marker_render_variant=str(marker_render_variant),
        value_min=int(value_min),
        value_max=int(value_max),
        style=style,
    )
    marker_meta = {
        "marker_render_variant": str(marker_render_variant),
        "marker_render_variant_probabilities": dict(dataset.get("marker_render_variant_probabilities", {})),
        "marker_style_variant": str(style_id),
        "marker_style_variant_probabilities": dict(style_probabilities),
        "marker_value_min": int(value_min),
        "marker_value_max": int(value_max),
        "marker_fill_rgb": [int(channel) for channel in style["fill"]],
        "marker_outline_rgb": [int(channel) for channel in style["outline"]],
        "show_marker_labels": bool(show_marker_labels),
    }
    return (
        _RenderedChoroplethMap(
            image=image,
            entities=tuple([dict(entity) for entity in rendered_scene.entities] + [dict(entity) for entity in marker_entities]),
            panel_bbox_px=list(rendered_scene.panel_bbox_px),
            title_bbox_px=list(rendered_scene.title_bbox_px),
            map_bbox_px=list(rendered_scene.map_bbox_px),
            legend_bbox_px=list(rendered_scene.legend_bbox_px),
            region_bbox_map=dict(rendered_scene.region_bbox_map),
            region_center_map=dict(rendered_scene.region_center_map),
            legend_entry_bbox_map=dict(marker_legend_bbox_map),
            render_meta={**dict(rendered_scene.render_meta), "marker_layer": dict(marker_meta)},
        ),
        {str(key): [list(bbox) for bbox in value] for key, value in marker_bboxes_by_region.items()},
        {str(key): list(value) for key, value in marker_group_bbox_map.items()},
        dict(marker_meta),
    )


def _json_examples(query_variant: str, *, prompt_defaults: Mapping[str, Any]) -> Tuple[str, str]:
    return (
        str(prompt_defaults[f"json_example_{str(query_variant)}"]),
        str(prompt_defaults[f"json_example_answer_only_{str(query_variant)}"]),
    )


class ChartsMapChoroplethRegionCountTask:
    """Answer count questions over an irregular choropleth region map."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "map"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        public_overrides = (
            _public_task_param_overrides(str(self.task_id))
            if str(self.task_id) != str(TASK_ID)
            else {}
        )
        if public_overrides:
            merged_params = dict(public_overrides)
            merged_params.update(dict(params))
            params = merged_params
        query_variant, query_variant_probabilities = _resolve_query_variant(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        support_params = _support_sampling_params(
            params,
            query_variant_probabilities=query_variant_probabilities,
        )
        dataset = _construct_dataset(
            query_variant=str(query_variant),
            scene_variant=str(scene_variant),
            params=support_params,
            instance_seed=int(instance_seed),
        )
        render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
        render_params = _resolve_render_params(
            render_style_params,
            query_variant=str(query_variant),
            legend_count=len(dataset["legend_bins"]),
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        categorical = _is_categorical_query_variant(str(query_variant))
        marker_task = _is_marker_query_variant(str(query_variant))
        if str(scene_variant) == "geographic_region_map":
            rendered_scene = _render_world_choropleth_map(
                background,
                scene_title=str(dataset["scene_title"]),
                map_asset_id=str(dataset.get("map_asset_id") or _WORLD_MAP_ASSET_ID),
                regions=list(dataset["regions"]),
                legend_bins=list(dataset["legend_bins"]),
                render_params=render_params,
                instance_seed=int(instance_seed),
                categorical=bool(categorical),
                draw_color_legend=not bool(marker_task),
                neutral_regions=bool(marker_task),
            )
        else:
            rendered_scene = _render_choropleth_map(
                background,
                scene_title=str(dataset["scene_title"]),
                rows=int(dataset["rows"]),
                cols=int(dataset["cols"]),
                regions=list(dataset["regions"]),
                legend_bins=list(dataset["legend_bins"]),
                render_params=render_params,
                instance_seed=int(instance_seed),
                categorical=bool(categorical),
                draw_color_legend=not bool(marker_task),
                neutral_regions=bool(marker_task),
            )
        marker_bboxes_by_region: Dict[str, List[List[float]]] = {}
        marker_group_bbox_map: Dict[str, List[float]] = {}
        marker_render_meta: Dict[str, Any] = {}
        if bool(marker_task):
            rendered_scene, marker_bboxes_by_region, marker_group_bbox_map, marker_render_meta = _render_marker_layer(
                rendered_scene,
                dataset=dataset,
                render_params=render_params,
                params=render_style_params,
                instance_seed=int(instance_seed),
            )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_synthetic_region_map",
                "object_description_geographic_region_map",
                "object_description_geographic_categorical_map",
                "object_description_geographic_border_map",
                "object_description_marker_map",
                "answer_hint_count",
                "answer_hint_label",
                "evidence_hint_region_count",
                "evidence_hint_marker",
                "json_example_numeric_threshold_region_count",
                "json_example_numeric_interval_region_count",
                "json_example_categorical_region_count",
                "json_example_continent_region_count",
                "json_example_continent_category_region_count",
                "json_example_continent_threshold_region_count",
                "json_example_border_neighbor_count",
                "json_example_adjacent_same_category_count",
                "json_example_adjacent_category_count",
                "json_example_adjacent_numeric_threshold_count",
                "json_example_marker_region_threshold_count",
                "json_example_marker_region_extremum_label",
                "json_example_answer_only_numeric_threshold_region_count",
                "json_example_answer_only_numeric_interval_region_count",
                "json_example_answer_only_categorical_region_count",
                "json_example_answer_only_continent_region_count",
                "json_example_answer_only_continent_category_region_count",
                "json_example_answer_only_continent_threshold_region_count",
                "json_example_answer_only_border_neighbor_count",
                "json_example_answer_only_adjacent_same_category_count",
                "json_example_answer_only_adjacent_category_count",
                "json_example_answer_only_adjacent_numeric_threshold_count",
                "json_example_answer_only_marker_region_threshold_count",
                "json_example_answer_only_marker_region_extremum_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _json_examples(str(query_variant), prompt_defaults=prompt_defaults)
        qparams = dict(dataset["question_params"])
        if bool(marker_task):
            object_description = str(
                dataset.get("map_object_description")
                or prompt_defaults["object_description_marker_map"]
            )
        elif str(scene_variant) == "geographic_region_map" and _is_world_border_query_variant(str(query_variant)):
            object_description = str(prompt_defaults["object_description_geographic_border_map"])
        elif str(scene_variant) == "geographic_region_map" and bool(categorical):
            asset_description = str(dataset.get("map_object_description") or "")
            object_description = (
                asset_description.replace("colored by value and a color legend", "colored by category and a category legend")
                if asset_description
                else str(prompt_defaults["object_description_geographic_categorical_map"])
            )
        else:
            object_description = str(
                dataset.get("map_object_description")
                or prompt_defaults.get(
                    f"object_description_{str(scene_variant)}",
                    prompt_defaults["object_description_synthetic_region_map"],
                )
            )
        region_noun = str(dataset.get("map_region_noun") or ("countries" if str(scene_variant) == "geographic_region_map" else "regions"))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str("marker_map" if bool(marker_task) else prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(
                    prompt_defaults["evidence_hint_marker"]
                    if bool(marker_task)
                    else prompt_defaults["evidence_hint_region_count"]
                ),
                "answer_hint": str(
                    prompt_defaults["answer_hint_label"]
                    if str(dataset["answer_type"]) == "string"
                    else prompt_defaults["answer_hint_count"]
                ),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "region_noun": str(region_noun),
                "continent_label": str(qparams.get("continent_label", "")),
                "reference_country_label": str(qparams.get("reference_country_label", "")),
                "threshold_phrase": str(qparams.get("threshold_phrase", "")),
                "interval_phrase": str(qparams.get("interval_phrase", "")),
                "category_label": str(qparams.get("category_label", "")),
                "extremum_word": str(qparams.get("extremum_word", "")),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_region_ids = [str(region_id) for region_id in dataset["evidence_region_ids"]]
        if bool(marker_task):
            evidence_bboxes = [
                list(bbox)
                for region_id in evidence_region_ids
                for bbox in marker_bboxes_by_region.get(str(region_id), [])
            ]
        else:
            evidence_bboxes = [list(rendered_scene.region_bbox_map[str(region_id)]) for region_id in evidence_region_ids]
        projected_evidence = {
            "bbox_set": list(evidence_bboxes),
            "bbox_map": (
                {str(region_id): list(marker_group_bbox_map[str(region_id)]) for region_id in evidence_region_ids}
                if bool(marker_task)
                else {str(region_id): list(rendered_scene.region_bbox_map[str(region_id)]) for region_id in evidence_region_ids}
            ),
            "region_ids": list(evidence_region_ids),
            **({"marker_bboxes_by_region": {str(region_id): list(marker_bboxes_by_region.get(str(region_id), [])) for region_id in evidence_region_ids}} if bool(marker_task) else {}),
        }
        answer_gt = TypedValue(
            type=str(dataset["answer_type"]),
            value=(str(dataset["answer_value"]) if str(dataset["answer_type"]) == "string" else int(dataset["answer_value"])),
        )
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        evidence_scan = normalize_int_with_bounds(len(evidence_region_ids), [1, 16])
        region_scan = normalize_int_with_bounds(int(dataset["region_count"]), [14, 28])
        legend_scan = normalize_int_with_bounds(len(dataset["legend_bins"]), [3, 6])
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BY_VARIANT[str(query_variant)])
            + (0.10 * float(evidence_scan))
            + (0.06 * float(legend_scan))
        )
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(region_scan),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
            },
        )
        query_params = {
            "query_variant": str(query_variant),
            "scene_variant": str(scene_variant),
            "query_variant_probabilities": dict(query_variant_probabilities),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "geographic_map_variant": str(dataset.get("geographic_map_variant") or ""),
            "geographic_map_variant_probabilities": dict(dataset.get("geographic_map_variant_probabilities", {})),
            "region_count": int(dataset["region_count"]),
            "legend_bin_count": int(len(dataset["legend_bins"])),
            "target_count": int(dataset["target_count"]),
            "target_count_probabilities": dict(dataset["target_count_probabilities"]),
            **dict(qparams),
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_marker_map" if bool(marker_task) else "chart_region_map",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_variant": str(query_variant),
                    "scene_variant": str(scene_variant),
                    "answer_value": str(dataset["answer_value"]) if str(dataset["answer_type"]) == "string" else int(dataset["answer_value"]),
                    "evidence_region_ids": list(evidence_region_ids),
                    "target_bin_indices": [int(value) for value in dataset["target_bin_indices"]],
                },
            },
            "query_spec": {
                "query_variant": str(query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_variant": str(scene_variant),
                "map_asset_id": str(dataset.get("map_asset_id") or ""),
                "geographic_map_variant": str(dataset.get("geographic_map_variant") or ""),
                "geographic_map_variant_probabilities": dict(dataset.get("geographic_map_variant_probabilities", {})),
                "map_display_name": str(dataset.get("map_display_name") or ""),
                "map_region_noun": str(dataset.get("map_region_noun") or ""),
                "map_source": dict(dataset.get("map_source", {})),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "rows": int(dataset["rows"]),
                "cols": int(dataset["cols"]),
                "active_cells": [[int(row), int(col)] for row, col in dataset["active_cells"]],
                "selected_region_ids": [str(region["region_id"]) for region in dataset["regions"]],
                "legend_bins": [dict(item) for item in dataset["legend_bins"]],
                "legend_position": str(render_params.legend_position),
                "legend_position_probabilities": dict(render_params.legend_position_probabilities),
                **({"marker_render": dict(marker_render_meta)} if bool(marker_task) else {}),
                "map_palette_rgb": [[int(channel) for channel in color] for color in render_params.map_palette_rgb],
                "map_palette_variant": str(render_params.map_palette_variant),
                "map_palette_variant_probabilities": dict(render_params.map_palette_variant_probabilities),
                "region_gap_px": int(render_params.region_gap_px),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "map_render_style": dict(rendered_scene.render_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "panel_bbox_px": list(rendered_scene.panel_bbox_px),
                "title_bbox_px": list(rendered_scene.title_bbox_px),
                "map_bbox_px": list(rendered_scene.map_bbox_px),
                "legend_bbox_px": list(rendered_scene.legend_bbox_px),
                "region_bboxes_px": dict(rendered_scene.region_bbox_map),
                "region_centers_px": dict(rendered_scene.region_center_map),
                "legend_entry_bboxes_px": dict(rendered_scene.legend_entry_bbox_map),
                **({"marker_group_bboxes_px": dict(marker_group_bbox_map), "marker_bboxes_px": dict(marker_bboxes_by_region)} if bool(marker_task) else {}),
                **(
                    {"world_projection_bbox_px": list(rendered_scene.render_meta["world_projection_bbox_px"])}
                    if "world_projection_bbox_px" in rendered_scene.render_meta
                    else {}
                ),
            },
            "execution_trace": {
                "query_variant": str(query_variant),
                "scene_variant": str(scene_variant),
                "question_format": "map_marker_query" if bool(marker_task) else "map_region_count",
                "scene_title": str(dataset["scene_title"]),
                "map_asset_id": str(dataset.get("map_asset_id") or ""),
                "geographic_map_variant": str(dataset.get("geographic_map_variant") or ""),
                "map_display_name": str(dataset.get("map_display_name") or ""),
                "map_region_noun": str(dataset.get("map_region_noun") or ""),
                "rows": int(dataset["rows"]),
                "cols": int(dataset["cols"]),
                "region_count": int(dataset["region_count"]),
                "active_cells": [[int(row), int(col)] for row, col in dataset["active_cells"]],
                "legend_bins": [dict(item) for item in dataset["legend_bins"]],
                "regions": [dict(item) for item in dataset["regions"]],
                "regions_by_id": {str(key): dict(value) for key, value in dict(dataset["regions_by_id"]).items()},
                "answer_value": str(dataset["answer_value"]) if str(dataset["answer_type"]) == "string" else int(dataset["answer_value"]),
                "answer_type": str(dataset["answer_type"]),
                "evidence_region_ids": list(evidence_region_ids),
                "target_bin_indices": [int(value) for value in dataset["target_bin_indices"]],
                "nonmatching_bin_indices": [int(value) for value in dataset["nonmatching_bin_indices"]],
                "threshold_direction": str(dataset["threshold_direction"]),
                "evidence_semantics": str(query_variant),
            },
            "witness_symbolic": {
                "type": "map_marker_witness" if bool(marker_task) else "map_region_count_witness",
                "candidate_region_ids": list(evidence_region_ids),
                "answer_value": str(dataset["answer_value"]) if str(dataset["answer_type"]) == "string" else int(dataset["answer_value"]),
            },
            "projected_evidence": dict(projected_evidence),
            "background": background_meta,
            "post_image_noise": dict(post_noise_meta),
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant=str(query_variant),
            scene_id=str("marker_map" if bool(marker_task) else "region_map"),
            query_id=str(query_variant),
        )


@register_task
class ChartsMapRegionValueCountTask(
    MergedChartQueryVariantTaskMixin,
    ChartsMapChoroplethRegionCountTask,
):
    """Count map regions satisfying a numeric value condition."""

    task_id = "task_charts__region_map__region_value_count"
    allowed_query_variants = _SUPPORTED_REGION_VALUE_QUERY_VARIANTS


@register_task
class ChartsMapRegionCategoryCountTask(
    FixedChartQueryVariantTaskMixin,
    ChartsMapChoroplethRegionCountTask,
):
    """Count map regions matching a qualitative category."""

    task_id = "task_charts__region_map__region_category_count"
    fixed_query_variant = "categorical_region_count"


@register_task
class ChartsMapContinentFilteredCountTask(
    MergedChartQueryVariantTaskMixin,
    ChartsMapChoroplethRegionCountTask,
):
    """Count world-map regions after applying a continent filter."""

    task_id = "task_charts__region_map__continent_filtered_count"
    allowed_query_variants = _SUPPORTED_WORLD_FILTERED_QUERY_VARIANTS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        fixed_params = dict(params)
        fixed_params["scene_variant"] = "geographic_region_map"
        fixed_params["geographic_map_variant"] = "world_countries"
        return super().generate(int(instance_seed), params=fixed_params, max_attempts=int(max_attempts))


@register_task
class ChartsMapBorderNeighborCountTask(
    FixedChartQueryVariantTaskMixin,
    ChartsMapChoroplethRegionCountTask,
):
    """Count countries sharing a visible land border with one highlighted country."""

    task_id = "task_charts__region_map__border_neighbor_count"
    fixed_query_variant = "border_neighbor_count"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        fixed_params = dict(params)
        fixed_params["scene_variant"] = "geographic_region_map"
        fixed_params["geographic_map_variant"] = "world_countries"
        return super().generate(int(instance_seed), params=fixed_params, max_attempts=int(max_attempts))


@register_task
class ChartsMapAdjacentConditionCountTask(
    MergedChartQueryVariantTaskMixin,
    ChartsMapChoroplethRegionCountTask,
):
    """Count highlighted-region neighbors satisfying a legend condition."""

    task_id = "task_charts__region_map__adjacent_condition_count"
    allowed_query_variants = _SUPPORTED_ADJACENT_QUERY_VARIANTS


@register_task
class ChartsMapMarkerRegionThresholdCountTask(
    FixedChartQueryVariantTaskMixin,
    ChartsMapChoroplethRegionCountTask,
):
    """Count map regions whose marker-encoded value satisfies a threshold."""

    task_id = "task_charts__marker_map__marker_region_threshold_count"
    fixed_query_variant = "marker_region_threshold_count"


@register_task
class ChartsMapMarkerRegionExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsMapChoroplethRegionCountTask,
):
    """Identify the labeled map region with the largest or smallest marker value."""

    task_id = "task_charts__marker_map__marker_region_extremum_label"
    fixed_query_variant = "marker_region_extremum_label"


__all__ = [
    "ChartsMapChoroplethRegionCountTask",
    "ChartsMapAdjacentConditionCountTask",
    "ChartsMapBorderNeighborCountTask",
    "ChartsMapContinentFilteredCountTask",
    "ChartsMapMarkerRegionExtremumLabelTask",
    "ChartsMapMarkerRegionThresholdCountTask",
    "ChartsMapRegionCategoryCountTask",
    "ChartsMapRegionValueCountTask",
    "SUPPORTED_ADJACENT_QUERY_VARIANTS",
    "SUPPORTED_MARKER_RENDER_VARIANTS",
    "SUPPORTED_MARKER_QUERY_VARIANTS",
    "SUPPORTED_REGION_CATEGORY_QUERY_VARIANTS",
    "SUPPORTED_REGION_VALUE_QUERY_VARIANTS",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_VARIANTS",
    "SUPPORTED_WORLD_BORDER_QUERY_VARIANTS",
    "SUPPORTED_WORLD_FILTERED_QUERY_VARIANTS",
]
