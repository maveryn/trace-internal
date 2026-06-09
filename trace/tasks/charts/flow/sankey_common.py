"""Shared constants, defaults, and records for Sankey flow chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from ....core.task_group_config import get_task_group_defaults
from ...shared.config_defaults import split_generation_rendering_prompt_defaults
from ...shared.font_assets import sample_font_family
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ..shared.complexity import resolve_chart_complexity_weights
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_flow_sankey_path_value_base"
PATH_VALUE_QUERY_IDS: Tuple[str, ...] = (
    "source_to_target_total_flow",
    "path_bottleneck_value",
    "path_flow_difference",
)
NODE_SIDE_TOTAL_QUERY_IDS: Tuple[str, ...] = (
    "source_outgoing_total_flow",
    "target_incoming_total_flow",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = PATH_VALUE_QUERY_IDS + NODE_SIDE_TOTAL_QUERY_IDS
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("three_column_sankey",)

_TITLE_OPTIONS: Tuple[str, ...] = (
    "Program Flow Summary",
    "Budget Transfer Sankey",
    "Pipeline Flow Paths",
    "Resource Routing Diagram",
    "Channel Flow Map",
)
_FLOW_PALETTE_RGB: Tuple[Tuple[int, int, int], ...] = (
    (51, 113, 176),
    (204, 103, 79),
    (68, 153, 112),
    (139, 111, 190),
    (208, 151, 57),
    (67, 139, 160),
    (176, 89, 136),
    (95, 127, 66),
    (62, 102, 148),
    (190, 126, 84),
    (105, 151, 190),
    (160, 111, 74),
)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "source_to_target_total_flow": 0.90,
    "path_bottleneck_value": 0.62,
    "path_flow_difference": 0.70,
    "source_outgoing_total_flow": 0.66,
    "target_incoming_total_flow": 0.66,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {"three_column_sankey": 0.62}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "flow")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="flow")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="flow", apply_prob=0.0)


Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]

@dataclass(frozen=True)
class _FlowRenderParams:
    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    panel_padding_px: int
    title_band_height_px: int
    node_width_px: int
    node_height_px: int
    node_border_width_px: int
    port_separation_px: int
    shared_pair_lane_gap_px: int
    min_flow_width_px: int
    max_flow_width_px: int
    value_label_font_size_px: int
    value_label_gap_px: int
    source_middle_label_t: float
    middle_target_label_t: float
    node_label_font_size_px: int
    title_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    plot_fill_rgb: Tuple[int, int, int]
    node_fill_rgb: Tuple[int, int, int]
    node_border_rgb: Tuple[int, int, int]
    node_text_rgb: Tuple[int, int, int]
    value_label_fill_rgb: Tuple[int, int, int]
    value_label_border_rgb: Tuple[int, int, int]
    value_label_text_rgb: Tuple[int, int, int]
    title_color_rgb: Tuple[int, int, int]
    flow_alpha: int
    layout_offset_x_px: int
    layout_offset_y_px: int
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedSankey:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    panel_bbox_px: List[float]
    title_bbox_px: List[float]
    plot_bbox_px: List[float]
    node_bbox_map: Dict[str, List[float]]
    node_label_bbox_map: Dict[str, List[float]]
    segment_bbox_map: Dict[str, List[float]]
    segment_label_bbox_map: Dict[str, List[float]]
    segment_center_map: Dict[str, List[float]]


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
    return int(params.get(str(key), _RENDER_DEFAULTS.get(str(key), int(fallback))))


def _float_param(params: Mapping[str, Any], key: str, fallback: float) -> float:
    return float(params.get(str(key), _RENDER_DEFAULTS.get(str(key), float(fallback))))


def _gen_int_param(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), _GEN_DEFAULTS.get(str(key), int(fallback))))


def _resolve_render_params(params: Mapping[str, Any]) -> _FlowRenderParams:
    outer = _int_param(params, "outer_margin_px", 36)
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
    return _FlowRenderParams(
        canvas_width=_int_param(params, "canvas_width", 1180),
        canvas_height=_int_param(params, "canvas_height", 760),
        outer_margin_px=int(outer),
        panel_padding_px=_int_param(params, "panel_padding_px", 28),
        title_band_height_px=_int_param(params, "title_band_height_px", 62),
        node_width_px=_int_param(params, "node_width_px", 96),
        node_height_px=_int_param(params, "node_height_px", 44),
        node_border_width_px=_int_param(params, "node_border_width_px", 2),
        port_separation_px=max(14, _int_param(params, "port_separation_px", 34)),
        shared_pair_lane_gap_px=max(0, _int_param(params, "shared_pair_lane_gap_px", 72)),
        min_flow_width_px=_int_param(params, "min_flow_width_px", 6),
        max_flow_width_px=_int_param(params, "max_flow_width_px", 18),
        value_label_font_size_px=_int_param(params, "value_label_font_size_px", 19),
        value_label_gap_px=max(0, _int_param(params, "value_label_gap_px", 8)),
        source_middle_label_t=max(0.15, min(0.85, _float_param(params, "source_middle_label_t", 0.34))),
        middle_target_label_t=max(0.15, min(0.85, _float_param(params, "middle_target_label_t", 0.66))),
        node_label_font_size_px=_int_param(params, "node_label_font_size_px", 24),
        title_font_size_px=_int_param(params, "title_font_size_px", 29),
        panel_fill_rgb=_rgb_param(params, "panel_fill_rgb", (252, 253, 251)),
        panel_border_rgb=_rgb_param(params, "panel_border_rgb", (70, 80, 90)),
        plot_fill_rgb=_rgb_param(params, "plot_fill_rgb", (255, 255, 255)),
        node_fill_rgb=_rgb_param(params, "node_fill_rgb", (54, 63, 74)),
        node_border_rgb=_rgb_param(params, "node_border_rgb", (30, 38, 46)),
        node_text_rgb=_rgb_param(params, "node_text_rgb", (255, 255, 255)),
        value_label_fill_rgb=_rgb_param(params, "value_label_fill_rgb", (255, 255, 255)),
        value_label_border_rgb=_rgb_param(params, "value_label_border_rgb", (82, 88, 96)),
        value_label_text_rgb=_rgb_param(params, "value_label_text_rgb", (28, 34, 42)),
        title_color_rgb=_rgb_param(params, "title_color_rgb", (32, 38, 46)),
        flow_alpha=max(40, min(220, _int_param(params, "flow_alpha", 138))),
        layout_offset_x_px=int(jitter_left) - int(outer),
        layout_offset_y_px=int(jitter_top) - int(outer),
        layout_jitter_meta=dict(layout_jitter_meta),
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
