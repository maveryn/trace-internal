"""Hexbin-density chart threshold-count task."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    resolve_required_int_bounds,
    split_scene_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.fixed_query import select_task_query_id
from ...shared.prompt_variants import (
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_int, resolve_render_rgb
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import load_font, temporary_default_font_family
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import (
    chart_font_asset_metadata,
    load_chart_scene_background_defaults,
    load_chart_scene_noise_defaults,
    sample_chart_font_family,
)


TASK_ID = "task_charts__hexbin_density__threshold_bin_count"
SCENE_ID = "hexbin_density"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "above_threshold_bin_count",
    "below_threshold_bin_count",
)
SUPPORTED_DENSITY_PALETTE_SCHEMES: Tuple[str, ...] = (
    "blue",
    "teal",
    "green",
    "purple",
    "amber",
    "rose",
    "slate",
    "viridis",
    "cividis",
)

_SCENE_DEFAULTS = get_scene_defaults("charts", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id=SCENE_ID)
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)

RGB = Tuple[int, int, int]
BBox = Tuple[float, float, float, float]

_TITLE_OPTIONS: Tuple[str, ...] = (
    "Density Field",
    "Sample Density Map",
    "Observation Density",
    "Hexbin Frequency",
    "Spatial Density Summary",
)
_AXIS_LABELS: Tuple[Tuple[str, str], ...] = (
    ("x", "y"),
    ("Feature A", "Feature B"),
    ("Axis 1", "Axis 2"),
    ("Horizontal score", "Vertical score"),
)
_REASONING_LOAD_BY_QUERY: Dict[str, float] = {
    "above_threshold_bin_count": 0.70,
    "below_threshold_bin_count": 0.70,
}
_FALLBACK_DENSITY_PALETTE_SCHEMES: Dict[str, Tuple[RGB, ...]] = {
    "blue": (
        (210, 234, 247),
        (151, 203, 226),
        (88, 161, 197),
        (37, 113, 168),
        (15, 74, 127),
    ),
    "teal": (
        (205, 236, 232),
        (140, 210, 202),
        (76, 174, 166),
        (25, 126, 137),
        (13, 82, 103),
    ),
    "green": (
        (214, 238, 203),
        (166, 218, 145),
        (105, 186, 103),
        (49, 139, 80),
        (19, 90, 58),
    ),
    "purple": (
        (225, 216, 243),
        (188, 171, 226),
        (148, 126, 205),
        (102, 79, 169),
        (67, 49, 122),
    ),
    "amber": (
        (245, 224, 171),
        (236, 190, 101),
        (219, 148, 54),
        (183, 101, 32),
        (125, 65, 26),
    ),
    "rose": (
        (245, 208, 216),
        (232, 150, 166),
        (206, 93, 124),
        (166, 49, 91),
        (109, 28, 62),
    ),
    "slate": (
        (214, 224, 235),
        (164, 181, 199),
        (111, 135, 158),
        (67, 88, 112),
        (36, 52, 76),
    ),
    "viridis": (
        (205, 225, 101),
        (124, 201, 88),
        (53, 164, 121),
        (41, 120, 142),
        (68, 45, 130),
    ),
    "cividis": (
        (232, 211, 90),
        (196, 180, 84),
        (142, 144, 92),
        (87, 106, 110),
        (44, 65, 96),
    ),
}


@dataclass(frozen=True)
class _HexBin:
    bin_id: str
    row_index: int
    column_index: int
    density_level: int
    fill_rgb: RGB


@dataclass(frozen=True)
class _Query:
    query_id: str
    threshold_direction: str
    threshold_phrase: str
    threshold_operator: str
    threshold_level: int
    answer: int
    annotation_bin_ids: Tuple[str, ...]
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    row_count: int
    column_count: int
    bins: Tuple[_HexBin, ...]
    query: _Query
    density_palette_scheme: str
    density_palette_rgb: Tuple[RGB, ...]
    density_palette_trace: Dict[str, Any]


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    margin_left: int
    margin_right: int
    margin_top: int
    margin_bottom: int
    legend_width: int
    axis_line_width: int
    grid_line_width: int
    hex_outline_width: int
    tick_font_size: int
    label_font_size: int
    title_font_size: int
    plot_fill_rgb: RGB
    axis_rgb: RGB
    grid_rgb: RGB
    text_rgb: RGB
    muted_rgb: RGB
    hex_outline_rgb: RGB
    threshold_guide_fill_rgb: RGB
    layout_jitter: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: List[float]
    legend_bbox_px: List[float]
    title_bbox_px: List[float]
    threshold_guide_bbox_px: List[float]
    bin_bboxes_px: Dict[str, List[float]]
    bin_centers_px: Dict[str, List[float]]
    render_meta: Dict[str, Any]


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def _resolve_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(
        resolve_render_int(
            params,
            _RENDER_DEFAULTS,
            str(key),
            int(fallback),
            instance_seed=_render_style_seed(params),
            namespace=TASK_ID,
        )
    )


def _resolve_rgb(params: Mapping[str, Any], key: str, fallback: RGB) -> RGB:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _balanced_int(
    params: Mapping[str, Any],
    *,
    key: str,
    support: Sequence[int],
    instance_seed: int,
    namespace: str,
) -> int:
    if str(key) in params:
        value = int(params[str(key)])
        if value not in set(int(item) for item in support):
            raise ValueError(f"{key}={value} is outside supported values {list(support)}")
        return int(value)
    values = tuple(int(value) for value in support)
    if not values:
        raise ValueError(f"empty integer support for {key}")
    if params.get("_sample_cursor") is not None:
        cursor = abs(int(params["_sample_cursor"]))
        offset = resolve_selection_index(params=params, instance_seed=0, namespace=f"{TASK_ID}.{namespace}.offset")
        return int(values[(cursor + offset) % len(values)])
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.{namespace}")
    return int(values[index % len(values)])


def _resolve_bounds(params: Mapping[str, Any], *, min_key: str, max_key: str, fallback_min: int, fallback_max: int) -> Tuple[int, int]:
    return resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=f"generation defaults for {TASK_ID}",
    )


def _coerce_palette(raw: Any) -> Tuple[RGB, ...]:
    palette: List[RGB] = []
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        for item in raw:
            if isinstance(item, Sequence) and not isinstance(item, (str, bytes)) and len(item) >= 3:
                palette.append(tuple(max(0, min(255, int(channel))) for channel in item[:3]))  # type: ignore[index]
    if len(palette) >= 5:
        return _ensure_level_one_contrast(tuple(palette[:5]))
    return tuple()


def _rgb_distance(a: RGB, b: RGB) -> float:
    return math.sqrt(sum((float(a[index]) - float(b[index])) ** 2 for index in range(3)))


def _ensure_level_one_contrast(palette: Sequence[RGB]) -> Tuple[RGB, ...]:
    resolved = [tuple(int(channel) for channel in color) for color in palette[:5]]
    if not resolved:
        return tuple()
    first = resolved[0]
    if _rgb_distance(first, (255, 255, 255)) < 52.0:
        for delta in (24, 36, 48, 60):
            adjusted = tuple(max(0, int(channel) - int(delta)) for channel in first)
            if _rgb_distance(adjusted, (255, 255, 255)) >= 52.0:
                resolved[0] = adjusted
                break
        else:
            resolved[0] = tuple(max(0, int(channel) - 60) for channel in first)
    return tuple(resolved)


def _configured_palette_schemes(params: Mapping[str, Any]) -> Dict[str, Tuple[RGB, ...]]:
    schemes: Dict[str, Tuple[RGB, ...]] = dict(_FALLBACK_DENSITY_PALETTE_SCHEMES)
    raw = params.get("density_palette_schemes", group_default(_RENDER_DEFAULTS, "density_palette_schemes", {}))
    if isinstance(raw, Mapping):
        for key, value in raw.items():
            palette = _coerce_palette(value)
            if len(palette) >= 5:
                schemes[str(key)] = tuple(palette[:5])
    return schemes


def _resolve_density_palette(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Tuple[RGB, ...], Dict[str, Any]]:
    explicit_palette = params.get("density_palette_rgb")
    if explicit_palette is not None:
        palette = _coerce_palette(explicit_palette)
        if len(palette) < 5:
            raise ValueError("density_palette_rgb must contain at least five RGB colors")
        return (
            "custom",
            tuple(palette[:5]),
            {
                "density_palette_scheme": "custom",
                "density_palette_selection_policy": "explicit_density_palette_rgb",
                "density_palette_scheme_probabilities": {"custom": 1.0},
                "level_one_distance_from_white": round(_rgb_distance(tuple(palette[0]), (255, 255, 255)), 3),
                "level_one_minimum_distance_from_white": 52.0,
            },
        )
    schemes = _configured_palette_schemes(params)
    supported = tuple(str(name) for name in SUPPORTED_DENSITY_PALETTE_SCHEMES if str(name) in schemes)
    if not supported:
        supported = tuple(sorted(schemes))
    scheme, probabilities = resolve_chart_axis_variant(
        params=params,
        gen_defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=supported,
        task_id=TASK_ID,
        explicit_key="density_palette_scheme",
        weights_key="density_palette_scheme_weights",
        balance_flag_key="balanced_density_palette_scheme_sampling",
        axis_namespace="density_palette_scheme",
    )
    palette = tuple(schemes[str(scheme)][:5])
    return (
        str(scheme),
        palette,
        {
            "density_palette_scheme": str(scheme),
            "density_palette_selection_policy": "weighted_density_palette_scheme",
            "density_palette_scheme_probabilities": dict(probabilities),
            "level_one_distance_from_white": round(_rgb_distance(tuple(palette[0]), (255, 255, 255)), 3),
            "level_one_minimum_distance_from_white": 52.0,
        },
    )


def _occupied_cells(
    *,
    row_count: int,
    column_count: int,
    occupied_count: int,
    instance_seed: int,
) -> Tuple[Tuple[int, int], ...]:
    all_cells = [(row, col) for row in range(int(row_count)) for col in range(int(column_count))]
    if int(occupied_count) >= len(all_cells):
        return tuple(all_cells)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.occupied_cells")
    center_count = 2 + (resolve_selection_index(params={}, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.cluster_count") % 2)
    centers = [(rng.uniform(0.15, 0.85), rng.uniform(0.15, 0.85)) for _ in range(int(center_count))]

    def score(cell: Tuple[int, int]) -> float:
        row, col = cell
        x = (float(col) + 0.5) / float(max(1, int(column_count)))
        y = (float(row) + 0.5) / float(max(1, int(row_count)))
        dist = min(math.hypot(float(x) - float(cx), float(y) - float(cy)) for cx, cy in centers)
        return float(dist) + rng.uniform(0.0, 0.18)

    chosen = sorted(all_cells, key=score)[: int(occupied_count)]
    return tuple(sorted(chosen, key=lambda item: (int(item[0]), int(item[1]))))


def _answer_support(params: Mapping[str, Any], *, occupied_count: int) -> Tuple[int, ...]:
    answer_min, answer_max = _resolve_bounds(
        params,
        min_key="threshold_count_answer_min",
        max_key="threshold_count_answer_max",
        fallback_min=4,
        fallback_max=18,
    )
    answer_max = min(int(answer_max), max(1, int(occupied_count) - 1))
    answer_min = min(max(1, int(answer_min)), int(answer_max))
    return tuple(range(int(answer_min), int(answer_max) + 1))


def _build_dataset(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    selected_query_id: str,
    query_probabilities: Mapping[str, float],
) -> _Dataset:
    query_id = str(selected_query_id)
    row_min, row_max = _resolve_bounds(params, min_key="row_count_min", max_key="row_count_max", fallback_min=5, fallback_max=7)
    col_min, col_max = _resolve_bounds(
        params,
        min_key="column_count_min",
        max_key="column_count_max",
        fallback_min=7,
        fallback_max=10,
    )
    row_count = _balanced_int(
        params,
        key="row_count",
        support=range(int(row_min), int(row_max) + 1),
        instance_seed=int(instance_seed),
        namespace="row_count",
    )
    column_count = _balanced_int(
        params,
        key="column_count",
        support=range(int(col_min), int(col_max) + 1),
        instance_seed=int(instance_seed),
        namespace="column_count",
    )
    occupied_min, occupied_max = _resolve_bounds(
        params,
        min_key="occupied_bin_count_min",
        max_key="occupied_bin_count_max",
        fallback_min=24,
        fallback_max=42,
    )
    occupied_cap = int(row_count) * int(column_count)
    occupied_support = range(min(int(occupied_min), occupied_cap), min(int(occupied_max), occupied_cap) + 1)
    occupied_count = _balanced_int(
        params,
        key="occupied_bin_count",
        support=occupied_support,
        instance_seed=int(instance_seed),
        namespace="occupied_bin_count",
    )
    threshold_min, threshold_max = _resolve_bounds(
        params,
        min_key="density_threshold_level_min",
        max_key="density_threshold_level_max",
        fallback_min=2,
        fallback_max=5,
    )
    threshold_support = range(max(2, int(threshold_min)), min(5, int(threshold_max)) + 1)
    threshold_level = _balanced_int(
        params,
        key="density_threshold_level",
        support=threshold_support,
        instance_seed=int(instance_seed),
        namespace="density_threshold_level",
    )
    answer_support = _answer_support(params, occupied_count=int(occupied_count))
    target_count = _balanced_int(
        params,
        key="threshold_count_answer",
        support=answer_support,
        instance_seed=int(instance_seed),
        namespace="threshold_count_answer",
    )
    cells = _occupied_cells(
        row_count=int(row_count),
        column_count=int(column_count),
        occupied_count=int(occupied_count),
        instance_seed=int(instance_seed),
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.density_levels")
    cell_indices = list(range(len(cells)))
    rng.shuffle(cell_indices)
    matching_indices = set(cell_indices[: int(target_count)])
    palette_scheme, palette, palette_trace = _resolve_density_palette(params, instance_seed=int(instance_seed))
    bins: List[_HexBin] = []
    direction = "above" if str(query_id) == "above_threshold_bin_count" else "below"
    for index, (row, col) in enumerate(cells):
        if str(direction) == "above":
            choices = list(range(int(threshold_level), 6)) if index in matching_indices else list(range(1, int(threshold_level)))
        else:
            choices = list(range(1, int(threshold_level))) if index in matching_indices else list(range(int(threshold_level), 6))
        if not choices:
            raise RuntimeError("invalid density-threshold construction")
        level = int(choices[rng.randrange(len(choices))])
        bins.append(
            _HexBin(
                bin_id=f"bin_r{int(row):02d}_c{int(col):02d}",
                row_index=int(row),
                column_index=int(col),
                density_level=int(level),
                fill_rgb=tuple(int(channel) for channel in palette[int(level) - 1]),
            )
        )
    bins_sorted = tuple(sorted(bins, key=lambda item: (int(item.row_index), int(item.column_index))))
    if str(direction) == "above":
        annotation_bins = tuple(bin_item for bin_item in bins_sorted if int(bin_item.density_level) >= int(threshold_level))
        phrase = "at least"
        operator = ">="
    else:
        annotation_bins = tuple(bin_item for bin_item in bins_sorted if int(bin_item.density_level) < int(threshold_level))
        phrase = "below"
        operator = "<"
    if len(annotation_bins) != int(target_count):
        raise RuntimeError("hexbin threshold construction lost target count")
    query = _Query(
        query_id=str(query_id),
        threshold_direction=str(direction),
        threshold_phrase=str(phrase),
        threshold_operator=str(operator),
        threshold_level=int(threshold_level),
        answer=int(target_count),
        annotation_bin_ids=tuple(str(bin_item.bin_id) for bin_item in annotation_bins),
        trace={
            "density_threshold_direction": str(direction),
            "density_threshold_phrase": str(phrase),
            "density_threshold_operator": str(operator),
            "density_threshold_level": int(threshold_level),
            "matching_bin_ids": [str(bin_item.bin_id) for bin_item in annotation_bins],
            "density_level_by_bin_id": {str(bin_item.bin_id): int(bin_item.density_level) for bin_item in bins_sorted},
            "query_id_probabilities": dict(query_probabilities),
        },
    )
    return _Dataset(
        row_count=int(row_count),
        column_count=int(column_count),
        bins=bins_sorted,
        query=query,
        density_palette_scheme=str(palette_scheme),
        density_palette_rgb=tuple(palette),
        density_palette_trace=dict(palette_trace),
    )


def _resolve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    params = {**dict(params), "_render_style_seed": int(instance_seed)}
    left, right, top, bottom, jitter = apply_layout_jitter_to_margins(
        left_px=_resolve_int(params, "plot_margin_left_px", 96),
        right_px=_resolve_int(params, "plot_margin_right_px", 238),
        top_px=_resolve_int(params, "plot_margin_top_px", 94),
        bottom_px=_resolve_int(params, "plot_margin_bottom_px", 92),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.layout",
    )
    return _RenderParams(
        canvas_width=_resolve_int(params, "canvas_width", 1280),
        canvas_height=_resolve_int(params, "canvas_height", 820),
        margin_left=int(left),
        margin_right=int(right),
        margin_top=int(top),
        margin_bottom=int(bottom),
        legend_width=_resolve_int(params, "legend_width_px", 150),
        axis_line_width=_resolve_int(params, "axis_line_width_px", 2),
        grid_line_width=_resolve_int(params, "grid_line_width_px", 1),
        hex_outline_width=_resolve_int(params, "hex_outline_width_px", 2),
        tick_font_size=_resolve_int(params, "tick_font_size_px", 15),
        label_font_size=_resolve_int(params, "label_font_size_px", 17),
        title_font_size=_resolve_int(params, "title_font_size_px", 26),
        plot_fill_rgb=_resolve_rgb(params, "plot_fill_rgb", (255, 255, 255)),
        axis_rgb=_resolve_rgb(params, "axis_color_rgb", (55, 60, 70)),
        grid_rgb=_resolve_rgb(params, "grid_color_rgb", (223, 227, 235)),
        text_rgb=_resolve_rgb(params, "text_color_rgb", (35, 40, 52)),
        muted_rgb=_resolve_rgb(params, "muted_text_rgb", (83, 91, 105)),
        hex_outline_rgb=_resolve_rgb(params, "hex_outline_rgb", (255, 255, 255)),
        threshold_guide_fill_rgb=_resolve_rgb(params, "threshold_guide_fill_rgb", (255, 255, 255)),
        layout_jitter=dict(jitter),
    )


def _plot_bbox(rp: _RenderParams) -> BBox:
    return (
        float(rp.margin_left),
        float(rp.margin_top),
        float(rp.canvas_width - rp.margin_right),
        float(rp.canvas_height - rp.margin_bottom),
    )


def _legend_bbox(plot_bbox: BBox, rp: _RenderParams) -> BBox:
    _x0, y0, x1, y1 = (float(value) for value in plot_bbox)
    return (
        float(x1 + 34.0),
        float(y0 + 58.0),
        float(min(rp.canvas_width - 34, x1 + 34.0 + rp.legend_width)),
        float(min(y1, y0 + 286.0)),
    )


def _scale_point(x_value: float, y_value: float, *, plot_bbox: BBox) -> Tuple[float, float]:
    x0, y0, x1, y1 = (float(value) for value in plot_bbox)
    return (
        float(x0 + (float(x_value) / 100.0) * (x1 - x0)),
        float(y1 - (float(y_value) / 100.0) * (y1 - y0)),
    )


def _draw_axes(draw: ImageDraw.ImageDraw, *, plot_bbox: BBox, rp: _RenderParams) -> Dict[str, Any]:
    x0, y0, x1, y1 = (float(value) for value in plot_bbox)
    draw.rectangle([x0, y0, x1, y1], fill=rp.plot_fill_rgb, outline=rp.grid_rgb, width=1)
    tick_font = load_font(int(rp.tick_font_size), bold=False)
    for tick in (0, 25, 50, 75, 100):
        sx, _ = _scale_point(float(tick), 0.0, plot_bbox=plot_bbox)
        _, sy = _scale_point(0.0, float(tick), plot_bbox=plot_bbox)
        draw.line([sx, y0, sx, y1], fill=rp.grid_rgb, width=max(1, int(rp.grid_line_width)))
        draw.line([x0, sy, x1, sy], fill=rp.grid_rgb, width=max(1, int(rp.grid_line_width)))
        draw_text_traced(draw, (sx - 8.0, y1 + 10.0), str(tick), font=tick_font, fill=rp.muted_rgb, role="readout", required=False)
        draw_text_traced(draw, (x0 - 36.0, sy - 8.0), str(tick), font=tick_font, fill=rp.muted_rgb, role="readout", required=False)
    draw.line([x0, y1, x1, y1], fill=rp.axis_rgb, width=max(1, int(rp.axis_line_width)))
    draw.line([x0, y0, x0, y1], fill=rp.axis_rgb, width=max(1, int(rp.axis_line_width)))
    return {"axis_ticks": [0, 25, 50, 75, 100]}


def _hex_points(center_x: float, center_y: float, radius: float) -> List[Tuple[float, float]]:
    return [
        (
            float(center_x) + float(radius) * math.cos(math.radians(float(angle))),
            float(center_y) + float(radius) * math.sin(math.radians(float(angle))),
        )
        for angle in (0, 60, 120, 180, 240, 300)
    ]


def _hex_bbox(points: Sequence[Tuple[float, float]]) -> List[float]:
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return _bbox([min(xs), min(ys), max(xs), max(ys)])


def _hex_layout(dataset: _Dataset, *, plot_bbox: BBox) -> Tuple[float, Dict[Tuple[int, int], Tuple[float, float]]]:
    x0, y0, x1, y1 = (float(value) for value in plot_bbox)
    inner_pad = 36.0
    usable_w = max(10.0, (x1 - x0) - (2.0 * inner_pad))
    usable_h = max(10.0, (y1 - y0) - (2.0 * inner_pad))
    columns = int(dataset.column_count)
    rows = int(dataset.row_count)
    radius_by_width = usable_w / max(1.0, 1.5 * float(columns - 1) + 2.0)
    radius_by_height = usable_h / max(1.0, math.sqrt(3.0) * (float(rows) + 0.5))
    radius = max(8.0, min(float(radius_by_width), float(radius_by_height)))
    span_w = float(radius) * (1.5 * float(columns - 1) + 2.0)
    span_h = float(radius) * math.sqrt(3.0) * (float(rows) + 0.5)
    origin_x = x0 + ((x1 - x0) - span_w) / 2.0 + float(radius)
    origin_y = y0 + ((y1 - y0) - span_h) / 2.0 + (math.sqrt(3.0) * float(radius) / 2.0)
    centers: Dict[Tuple[int, int], Tuple[float, float]] = {}
    for row in range(rows):
        for col in range(columns):
            centers[(int(row), int(col))] = (
                float(origin_x + (1.5 * float(radius) * float(col))),
                float(origin_y + (math.sqrt(3.0) * float(radius) * float(row)) + ((math.sqrt(3.0) * float(radius) / 2.0) if col % 2 else 0.0)),
            )
    return float(radius), centers


def _draw_hex_bins(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: _Dataset,
    plot_bbox: BBox,
    rp: _RenderParams,
) -> Tuple[Dict[str, List[float]], Dict[str, List[float]]]:
    radius, centers = _hex_layout(dataset, plot_bbox=plot_bbox)
    bin_bboxes: Dict[str, List[float]] = {}
    bin_centers: Dict[str, List[float]] = {}
    for bin_item in dataset.bins:
        center = centers[(int(bin_item.row_index), int(bin_item.column_index))]
        points = _hex_points(float(center[0]), float(center[1]), float(radius) * 0.94)
        draw.polygon(points, fill=bin_item.fill_rgb, outline=rp.hex_outline_rgb)
        if int(rp.hex_outline_width) > 1:
            draw.line([*points, points[0]], fill=rp.hex_outline_rgb, width=max(1, int(rp.hex_outline_width)))
        box = _hex_bbox(points)
        bin_bboxes[str(bin_item.bin_id)] = list(box)
        bin_centers[str(bin_item.bin_id)] = _bbox([float(center[0]), float(center[1])])
    return bin_bboxes, bin_centers


def _draw_legend(draw: ImageDraw.ImageDraw, *, legend_bbox: BBox, palette: Sequence[RGB], rp: _RenderParams) -> None:
    x0, y0, x1, _y1 = (float(value) for value in legend_bbox)
    title_font = load_font(int(rp.label_font_size), bold=True)
    label_font = load_font(int(rp.legend_width * 0 + rp.label_font_size), bold=False)
    draw_text_traced(draw, (x0, y0), "Density level", font=title_font, fill=rp.text_rgb, role="readout", required=False)
    swatch = 22
    y = y0 + 36.0
    for index, color in enumerate(palette[:5], start=1):
        draw.rectangle([x0, y, x0 + swatch, y + swatch], fill=color, outline=rp.grid_rgb, width=1)
        draw_text_traced(
            draw,
            (x0 + swatch + 12.0, y + 2.0),
            str(index),
            font=label_font,
            fill=rp.text_rgb,
            role="readout",
            required=False,
        )
        y += 32.0
    draw.rectangle([x0 - 12.0, y0 - 14.0, x1, y + 4.0], outline=rp.grid_rgb, width=1)


def _draw_threshold_guide(draw: ImageDraw.ImageDraw, *, dataset: _Dataset, plot_bbox: BBox, rp: _RenderParams) -> Tuple[List[float], str]:
    label = f"Count density {dataset.query.threshold_operator} {dataset.query.threshold_level}"
    font = load_font(int(rp.label_font_size), bold=True)
    x0, y0, x1, _ = (float(value) for value in plot_bbox)
    text_bbox = draw.textbbox((0, 0), label, font=font)
    width = float(text_bbox[2] - text_bbox[0]) + 24.0
    height = float(text_bbox[3] - text_bbox[1]) + 16.0
    bx1 = x1 - 10.0
    bx0 = max(x0 + 10.0, bx1 - width)
    by0 = y0 + 10.0
    by1 = by0 + height
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=8, fill=rp.threshold_guide_fill_rgb, outline=rp.grid_rgb, width=1)
    draw_text_traced(draw, (bx0 + 12.0, by0 + 7.0), label, font=font, fill=rp.text_rgb, role="readout", required=False)
    return _bbox([bx0, by0, bx1, by1]), str(label)


def _render_dataset(dataset: _Dataset, *, params: Mapping[str, Any], instance_seed: int) -> _Rendered:
    rp = _resolve_render_params(params, instance_seed=int(instance_seed))
    image, background_meta = make_background_canvas(
        canvas_width=int(rp.canvas_width),
        canvas_height=int(rp.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        fallback_color=(248, 248, 248),
    )
    draw = ImageDraw.Draw(image)
    plot_bbox = _plot_bbox(rp)
    axes_meta = _draw_axes(draw, plot_bbox=plot_bbox, rp=rp)
    title_font = load_font(int(rp.title_font_size), bold=True)
    title_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.title")
    title = str(_TITLE_OPTIONS[title_rng.randrange(len(_TITLE_OPTIONS))])
    x_axis, y_axis = _AXIS_LABELS[title_rng.randrange(len(_AXIS_LABELS))]
    title_xy = (float(plot_bbox[0]), max(14.0, float(plot_bbox[1]) - 48.0))
    title_text_bbox = draw.textbbox(title_xy, title, font=title_font, stroke_width=1)
    draw_text_traced(
        draw,
        title_xy,
        title,
        font=title_font,
        fill=rp.text_rgb,
        stroke_width=1,
        role="readout",
        required=False,
    )
    label_font = load_font(int(rp.label_font_size), bold=False)
    x_label_bbox = draw.textbbox((0, 0), x_axis, font=label_font)
    x_label_xy = (
        float((plot_bbox[0] + plot_bbox[2]) / 2.0) - float(x_label_bbox[2] - x_label_bbox[0]) / 2.0,
        float(plot_bbox[3]) + 45.0,
    )
    draw_text_traced(draw, x_label_xy, x_axis, font=label_font, fill=rp.muted_rgb, role="readout", required=False)
    y_label_xy = (float(plot_bbox[0]) - 76.0, float(plot_bbox[1]) - 28.0)
    draw_text_traced(draw, y_label_xy, y_axis, font=label_font, fill=rp.muted_rgb, role="readout", required=False)
    bin_bboxes, bin_centers = _draw_hex_bins(draw, dataset=dataset, plot_bbox=plot_bbox, rp=rp)
    legend_box = _legend_bbox(plot_bbox, rp)
    _draw_legend(draw, legend_bbox=legend_box, palette=dataset.density_palette_rgb, rp=rp)
    threshold_box, threshold_text = _draw_threshold_guide(draw, dataset=dataset, plot_bbox=plot_bbox, rp=rp)
    image, noise_meta = apply_post_image_noise(
        image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    title_bbox = _bbox(title_text_bbox)
    entities: List[Dict[str, Any]] = [
        {"entity_id": "plot_area", "entity_type": "plot", "bbox_px": _bbox(plot_bbox)},
        {"entity_id": "legend", "entity_type": "legend", "bbox_px": _bbox(legend_box)},
        {"entity_id": "title", "entity_type": "title", "bbox_px": title_bbox},
        {"entity_id": "threshold_guide", "entity_type": "annotation", "bbox_px": threshold_box, "text": threshold_text},
    ]
    for bin_item in dataset.bins:
        entities.append(
            {
                "entity_id": str(bin_item.bin_id),
                "entity_type": "hex_bin",
                "row_index": int(bin_item.row_index),
                "column_index": int(bin_item.column_index),
                "density_level": int(bin_item.density_level),
                "bbox_px": list(bin_bboxes[str(bin_item.bin_id)]),
                "center_px": list(bin_centers[str(bin_item.bin_id)]),
            }
        )
    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=_bbox(plot_bbox),
        legend_bbox_px=_bbox(legend_box),
        title_bbox_px=title_bbox,
        threshold_guide_bbox_px=threshold_box,
        bin_bboxes_px=dict(bin_bboxes),
        bin_centers_px=dict(bin_centers),
        render_meta={
            "background_style": dict(background_meta),
            "post_image_noise": dict(noise_meta),
            "layout_jitter": dict(rp.layout_jitter),
            "axis_labels": {"x": str(x_axis), "y": str(y_axis)},
            "title_text": str(title),
            "density_palette_scheme": str(dataset.density_palette_scheme),
            "density_palette_rgb": [list(color) for color in dataset.density_palette_rgb],
            "density_palette_contrast_policy": dict(dataset.density_palette_trace),
            **dict(axes_meta),
        },
    )


def _annotation_bbox_set(dataset: _Dataset, rendered: _Rendered) -> List[List[float]]:
    annotation: List[List[float]] = []
    for bin_id in dataset.query.annotation_bin_ids:
        box = rendered.bin_bboxes_px.get(str(bin_id))
        if box is None:
            raise RuntimeError(f"missing annotation bbox for bin: {bin_id}")
        annotation.append(list(box))
    return annotation


def _build_prompt(dataset: _Dataset, *, instance_seed: int) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    prompt_selection = render_scene_prompt_variants(
        domain="charts",
        scene_id=SCENE_ID,
        bundle_id=str(_PROMPT_DEFAULTS.get("bundle_id", "charts_hexbin_density_v1")),
        scene_key="hexbin_density_scene",
        task_key="hexbin_density_threshold_query",
        query_key=str(dataset.query.query_id),
        dynamic_slots={
            "object_description": "a hexbin density chart with numeric axes and a discrete density-level legend",
            "density_threshold_phrase": str(dataset.query.threshold_phrase),
            "density_threshold_operator": str(dataset.query.threshold_operator),
            "density_threshold_level": str(dataset.query.threshold_level),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return (
        str(prompt_artifacts.prompt),
        dict(prompt_artifacts.prompt_variants),
        {
            "template_id": str(_PROMPT_DEFAULTS.get("bundle_id", "charts_hexbin_density_v1")),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
        },
    )


@register_task
class ChartsHexbinDensityThresholdBinCountTask:
    """Count visible hex bins satisfying a discrete density threshold."""

    task_id = TASK_ID
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "threshold_bin_count"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=self.supported_query_ids,
            default_query_id="above_threshold_bin_count",
            task_id=self.task_id,
        )
        dataset: _Dataset | None = None
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                attempt_params = {**dict(task_params), "_attempt_index": int(attempt_index)}
                dataset = _build_dataset(
                    attempt_params,
                    instance_seed=int(instance_seed) + int(attempt_index),
                    selected_query_id=str(selected_query_id),
                    query_probabilities=dict(query_probabilities),
                )
                break
            except Exception as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        chart_font_family = sample_chart_font_family(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.chart_font",
            params=params,
        )
        with temporary_default_font_family(str(chart_font_family)):
            rendered = _render_dataset(dataset, params=params, instance_seed=int(instance_seed))
            prompt, prompt_variants, prompt_trace = _build_prompt(dataset, instance_seed=int(instance_seed))
        annotation = _annotation_bbox_set(dataset, rendered)
        answer_value = int(dataset.query.answer)
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=[list(value) for value in annotation])
        projected_annotation = {
            "type": "bbox_set",
            "bbox_set": [list(value) for value in annotation],
            "pixel_bbox_set": [list(value) for value in annotation],
            "annotation_bin_ids": list(dataset.query.annotation_bin_ids),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_hexbin_density",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(dataset.query.query_id),
                    "answer": int(answer_value),
                    "annotation_bin_ids": list(dataset.query.annotation_bin_ids),
                    "density_threshold_level": int(dataset.query.threshold_level),
                    "density_threshold_direction": str(dataset.query.threshold_direction),
                },
            },
            "query_spec": {
                "query_id": str(dataset.query.query_id),
                **dict(prompt_trace),
                "params": {
                    "query_id": str(dataset.query.query_id),
                    "scene_id": SCENE_ID,
                    "row_count": int(dataset.row_count),
                    "column_count": int(dataset.column_count),
                    "occupied_bin_count": int(len(dataset.bins)),
                    **dict(dataset.query.trace),
                },
            },
            "render_spec": {
                "canvas_width": int(rendered.image.size[0]),
                "canvas_height": int(rendered.image.size[1]),
                "coord_space": "pixel",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "legend_bbox_px": list(rendered.legend_bbox_px),
                "title_bbox_px": list(rendered.title_bbox_px),
                "threshold_guide_bbox_px": list(rendered.threshold_guide_bbox_px),
                "font_assets": chart_font_asset_metadata(str(chart_font_family)),
                **dict(rendered.render_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "legend_bbox_px": list(rendered.legend_bbox_px),
                "title_bbox_px": list(rendered.title_bbox_px),
                "threshold_guide_bbox_px": list(rendered.threshold_guide_bbox_px),
                "bin_bboxes_px": dict(rendered.bin_bboxes_px),
                "bin_centers_px": dict(rendered.bin_centers_px),
            },
            "execution_trace": {
                "query_id": str(dataset.query.query_id),
                "scene_id": SCENE_ID,
                "question_format": "hexbin_density_threshold_query",
                "answer": int(answer_value),
                "answer_type": "integer",
                "annotation_type": "bbox_set",
                "row_count": int(dataset.row_count),
                "column_count": int(dataset.column_count),
                "occupied_bin_count": int(len(dataset.bins)),
                "density_class_count": 5,
                "density_palette_scheme": str(dataset.density_palette_scheme),
                "density_palette_rgb": [list(color) for color in dataset.density_palette_rgb],
                "annotation_bin_ids": list(dataset.query.annotation_bin_ids),
                "bins": {
                    str(bin_item.bin_id): {
                        "row_index": int(bin_item.row_index),
                        "column_index": int(bin_item.column_index),
                        "density_level": int(bin_item.density_level),
                    }
                    for bin_item in dataset.bins
                },
                **dict(dataset.query.trace),
            },
            "witness_symbolic": {
                "type": "hexbin_density_threshold_witness",
                "annotation_type": "bbox_set",
                "annotation_bin_ids": list(dataset.query.annotation_bin_ids),
                "answer": int(answer_value),
            },
            "projected_annotation": dict(projected_annotation),
        }
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(dataset.query.query_id),
            prompt_variants=dict(prompt_variants),
        )


__all__ = [
    "ChartsHexbinDensityThresholdBinCountTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
