"""Shared constants and specs for parallel-coordinates chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from .....core.seed import spawn_rng
from .....core.scene_config import get_scene_defaults
from ....shared.config_defaults import (
    group_default,
    resolve_required_int_bounds,
    split_scene_generation_rendering_prompt_defaults,
)
from ....shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ....shared.font_assets import sample_font_family
from ....shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.labeled_chart_common import resolve_chart_axis_variant
from ...shared.visual_defaults import load_chart_scene_background_defaults, load_chart_scene_noise_defaults

TASK_ID = "charts_parallel_coords_base"
SCENE_ID = "parallel_coords"

CONDITION_QUERY_IDS: Tuple[str, ...] = (
    "above_on_both_axes",
    "below_on_both_axes",
    "above_on_one_below_on_other",
)
DELTA_QUERY_IDS: Tuple[str, ...] = (
    "largest_increase_between_axes",
    "largest_decrease_between_axes",
    "largest_absolute_change_between_axes",
)
CROSSING_QUERY_IDS: Tuple[str, ...] = (
    "all_crossings_between_adjacent_axes",
    "crossings_involving_profile_between_axes",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("vertical_parallel_coordinates",)

_TASK_GROUP_DEFAULTS = get_scene_defaults("charts", "parallel_coords")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id="parallel_coords")
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id="parallel_coords", apply_prob=0.15)

_PROFILE_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (38, 101, 176),
    (216, 95, 2),
    (27, 158, 119),
    (117, 112, 179),
    (231, 41, 138),
    (102, 166, 30),
    (230, 171, 2),
    (166, 118, 29),
)
_QUERY_LOADS: Dict[str, float] = {
    "above_on_both_axes": 0.60,
    "below_on_both_axes": 0.60,
    "above_on_one_below_on_other": 0.68,
    "largest_increase_between_axes": 0.64,
    "largest_decrease_between_axes": 0.64,
    "largest_absolute_change_between_axes": 0.70,
    "all_crossings_between_adjacent_axes": 0.82,
    "crossings_involving_profile_between_axes": 0.76,
}

RGB = Tuple[int, int, int]
BBox = List[float]
Point = List[float]


@dataclass(frozen=True)
class _Profile:
    profile_id: str
    label: str
    values: Tuple[int, ...]
    color_rgb: RGB


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer: int | str
    answer_type: str
    axis_i: int
    axis_j: int
    threshold: int | None
    reference_profile_id: str | None
    annotation_profile_ids: Tuple[str, ...]
    crossing_pairs: Tuple[Tuple[str, str], ...]
    params: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    scene_variant: str
    metrics: Tuple[str, ...]
    profiles: Tuple[_Profile, ...]
    query: _Query


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    plot_margin_left_px: int
    plot_margin_right_px: int
    plot_margin_top_px: int
    plot_margin_bottom_px: int
    panel_fill_rgb: RGB
    panel_border_rgb: RGB
    plot_fill_rgb: RGB
    axis_rgb: RGB
    selected_axis_rgb: RGB
    grid_rgb: RGB
    threshold_rgb: RGB
    text_rgb: RGB
    muted_text_rgb: RGB
    text_stroke_rgb: RGB
    line_width_px: int
    point_radius_px: int
    axis_line_width_px: int
    selected_axis_line_width_px: int
    grid_line_width_px: int
    label_font_size_px: int
    tick_font_size_px: int
    title_font_size_px: int
    threshold_font_size_px: int
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: BBox
    axis_x_px: Dict[int, float]
    point_bboxes_px: Dict[str, BBox]
    segment_bboxes_px: Dict[str, BBox]
    profile_bboxes_px: Dict[str, BBox]
    label_bboxes_px: Dict[str, BBox]
    threshold_bboxes_px: Dict[int, BBox]


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def _render_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), _RENDER_DEFAULTS.get(str(key), int(fallback))))


def _gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _render_rgb(params: Mapping[str, Any], key: str, fallback: RGB) -> RGB:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _support_probability_map(values: Sequence[int | str]) -> Dict[str, float]:
    if not values:
        return {}
    return {str(value): 1.0 / float(len(values)) for value in values}


def _balanced_int(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    namespace: str,
    low: int,
    high: int,
) -> Tuple[int, Dict[str, float]]:
    values = tuple(int(value) for value in range(int(low), int(high) + 1))
    if not values:
        raise ValueError(f"empty integer support for {namespace}")
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    return int(values[int(index) % len(values)]), uniform_probability_map(values)


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _sample_chart_font_family(instance_seed: int, params: Mapping[str, Any]) -> str:
    return str(
        sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.chart_font",
            params=params,
            exclude_tags=("display",),
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        )
    )


def _resolve_render_params(params: Mapping[str, Any]) -> _RenderParams:
    left = _render_int(params, "plot_margin_left_px", 138)
    right = _render_int(params, "plot_margin_right_px", 138)
    top = _render_int(params, "plot_margin_top_px", 116)
    bottom = _render_int(params, "plot_margin_bottom_px", 118)
    left, right, top, bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(left),
        right_px=int(right),
        top_px=int(top),
        bottom_px=int(bottom),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=_render_style_seed(params),
        namespace=f"{TASK_ID}.layout",
    )
    return _RenderParams(
        canvas_width=_render_int(params, "canvas_width", 1180),
        canvas_height=_render_int(params, "canvas_height", 760),
        plot_margin_left_px=int(left),
        plot_margin_right_px=int(right),
        plot_margin_top_px=int(top),
        plot_margin_bottom_px=int(bottom),
        panel_fill_rgb=_render_rgb(params, "panel_fill_rgb", (255, 255, 255)),
        panel_border_rgb=_render_rgb(params, "panel_border_rgb", (194, 202, 214)),
        plot_fill_rgb=_render_rgb(params, "plot_fill_rgb", (252, 253, 255)),
        axis_rgb=_render_rgb(params, "axis_rgb", (78, 88, 102)),
        selected_axis_rgb=_render_rgb(params, "selected_axis_rgb", (26, 66, 118)),
        grid_rgb=_render_rgb(params, "grid_rgb", (226, 231, 238)),
        threshold_rgb=_render_rgb(params, "threshold_rgb", (204, 56, 60)),
        text_rgb=_render_rgb(params, "text_rgb", (32, 38, 48)),
        muted_text_rgb=_render_rgb(params, "muted_text_rgb", (89, 100, 116)),
        text_stroke_rgb=_render_rgb(params, "text_stroke_rgb", (255, 255, 255)),
        line_width_px=_render_int(params, "line_width_px", 4),
        point_radius_px=_render_int(params, "point_radius_px", 5),
        axis_line_width_px=_render_int(params, "axis_line_width_px", 2),
        selected_axis_line_width_px=_render_int(params, "selected_axis_line_width_px", 4),
        grid_line_width_px=_render_int(params, "grid_line_width_px", 1),
        label_font_size_px=_render_int(params, "label_font_size_px", 18),
        tick_font_size_px=_render_int(params, "tick_font_size_px", 15),
        title_font_size_px=_render_int(params, "title_font_size_px", 28),
        threshold_font_size_px=_render_int(params, "threshold_font_size_px", 15),
        layout_jitter_meta=dict(layout_jitter_meta),
    )
