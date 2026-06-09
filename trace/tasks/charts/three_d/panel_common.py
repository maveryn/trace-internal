"""Shared constants and specs for synthetic 3D chart panel tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from ....core.task_group_config import get_task_group_defaults
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ...shared.render_variation import resolve_render_rgb
from ..shared.complexity import resolve_chart_complexity_weights
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults

TASK_ID = "charts_three_d_panel_query_base"
SCENE_ID = "surface_3d"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "reference_nearest_label",
    "surface_extremum_label",
    "series_trend_label",
    "panel_variation_label",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "three_d_scatter",
    "three_d_surface",
    "three_d_small_multiples",
)
_SUPPORTED_EXTREMA: Tuple[str, ...] = ("highest", "lowest")
_SUPPORTED_TRENDS: Tuple[str, ...] = ("increase", "decrease")
_TIME_POOL: Tuple[int, ...] = (2018, 2019, 2020, 2021, 2022, 2023, 2024)
_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (42, 104, 178),
    (216, 92, 74),
    (54, 148, 96),
    (139, 91, 183),
    (218, 143, 43),
    (75, 156, 190),
    (186, 85, 130),
    (108, 123, 60),
)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "reference_nearest_label": 0.62,
    "surface_extremum_label": 0.70,
    "series_trend_label": 0.74,
    "panel_variation_label": 0.76,
}
_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {
    "three_d_scatter": 0.72,
    "three_d_surface": 0.78,
    "three_d_small_multiples": 0.84,
}

RGB = Tuple[int, int, int]
BBox = List[float]

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "three_d")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="three_d")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="three_d", apply_prob=0.0)


@dataclass(frozen=True)
class _Point3D:
    point_id: str
    label: str
    x_value: float
    y_value: float
    z_value: float
    color_rgb: RGB
    shape: str = "circle"


@dataclass(frozen=True)
class _SurfaceCell:
    cell_id: str
    x_label: str
    y_label: str
    x_index: int
    y_index: int
    value: int


@dataclass(frozen=True)
class _Panel3D:
    panel_label: str
    values: Tuple[int, ...]
    color_rgb: RGB


@dataclass(frozen=True)
class _Query:
    query_id: str
    scene_variant: str
    answer: int | str
    answer_type: str
    annotation_point_ids: Tuple[str, ...] = ()
    annotation_cell_ids: Tuple[str, ...] = ()
    annotation_panel_labels: Tuple[str, ...] = ()
    trace: Dict[str, Any] | None = None


@dataclass(frozen=True)
class _Dataset:
    scene_variant: str
    points: Tuple[_Point3D, ...]
    surface_cells: Tuple[_SurfaceCell, ...]
    panels: Tuple[_Panel3D, ...]
    x_axis_label: str
    y_axis_label: str
    z_axis_label: str
    x_range: Tuple[float, float]
    y_range: Tuple[float, float]
    z_range: Tuple[float, float]
    x_labels: Tuple[str, ...]
    y_labels: Tuple[str, ...]
    query: _Query


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    plot_margin_left_px: int
    plot_margin_right_px: int
    plot_margin_top_px: int
    plot_margin_bottom_px: int
    panel_gap_px: int
    point_radius_px: int
    line_width_px: int
    axis_line_width_px: int
    grid_line_width_px: int
    tick_font_size_px: int
    label_font_size_px: int
    title_font_size_px: int
    panel_title_font_size_px: int
    plot_fill_rgb: RGB
    panel_fill_rgb: RGB
    panel_border_rgb: RGB
    axis_color_rgb: RGB
    grid_color_rgb: RGB
    text_color_rgb: RGB
    text_stroke_rgb: RGB
    surface_low_rgb: RGB
    surface_high_rgb: RGB
    surface_edge_rgb: RGB
    marker_outline_rgb: RGB
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: BBox
    point_bboxes_px: Dict[str, BBox]
    surface_cell_bboxes_px: Dict[str, BBox]
    panel_bboxes_px: Dict[str, BBox]


def _bbox(values: Sequence[float]) -> BBox:
    return [round(float(value), 3) for value in values]


def _as_rgb(value: Any, fallback: RGB) -> RGB:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


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


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_QUERY_IDS,
        task_id=TASK_ID,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )
