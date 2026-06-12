"""Shared constants, defaults, and helpers for radial Sankey chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from .....core.seed import spawn_rng
from .....core.scene_config import get_scene_defaults
from ....shared.bbox_projection import round_bbox as _round_bbox
from ....shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from ....shared.deterministic_sampling import resolve_selection_index
from ....shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.labeled_chart_common import resolve_chart_axis_variant
from ...shared.visual_defaults import load_chart_scene_background_defaults, load_chart_scene_noise_defaults


TASK_ID = "charts_flow_radial_sankey_base"
SCENE_ID = "radial_sankey"
TRANSFER_TOTAL_QUERY_IDS: Tuple[str, ...] = (
    "source_to_targets_total",
    "sources_to_target_total",
)
DOMINANT_ENDPOINT_QUERY_IDS: Tuple[str, ...] = (
    "largest_target_for_source",
    "largest_source_for_target",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("radial_chord_sankey",)

_TITLE_OPTIONS: Tuple[str, ...] = (
    "Radial Transfer Map",
    "Circular Flow Summary",
    "Endpoint Flow Ring",
    "Transfer Chord Diagram",
    "Radial Sankey Routing",
)
RGB = Tuple[int, int, int]
_RADIAL_COLOR_SCHEMES: Tuple[Dict[str, Any], ...] = (
    {
        "name": "lagoon_coral",
        "source_node_fill_rgb": (34, 99, 137),
        "target_node_fill_rgb": (184, 82, 77),
        "ring_line_rgb": (122, 151, 166),
        "value_label_fill_rgb": (255, 255, 252),
        "value_label_border_rgb": (87, 101, 112),
        "flow_palette_rgb": (
            (39, 125, 161),
            (235, 130, 75),
            (68, 159, 119),
            (181, 86, 110),
            (219, 181, 73),
            (86, 117, 186),
            (143, 108, 179),
        ),
    },
    {
        "name": "forest_plum",
        "source_node_fill_rgb": (71, 121, 65),
        "target_node_fill_rgb": (111, 75, 150),
        "ring_line_rgb": (136, 157, 129),
        "value_label_fill_rgb": (254, 255, 249),
        "value_label_border_rgb": (91, 98, 84),
        "flow_palette_rgb": (
            (75, 142, 84),
            (176, 117, 64),
            (128, 88, 164),
            (207, 154, 65),
            (64, 139, 151),
            (197, 92, 113),
            (99, 118, 62),
        ),
    },
    {
        "name": "ink_gold",
        "source_node_fill_rgb": (45, 74, 112),
        "target_node_fill_rgb": (163, 104, 37),
        "ring_line_rgb": (142, 138, 123),
        "value_label_fill_rgb": (255, 253, 243),
        "value_label_border_rgb": (89, 85, 74),
        "flow_palette_rgb": (
            (53, 91, 146),
            (207, 157, 60),
            (143, 83, 149),
            (70, 147, 133),
            (197, 91, 78),
            (98, 118, 177),
            (168, 122, 51),
        ),
    },
    {
        "name": "berry_teal",
        "source_node_fill_rgb": (44, 128, 133),
        "target_node_fill_rgb": (148, 69, 118),
        "ring_line_rgb": (127, 155, 158),
        "value_label_fill_rgb": (253, 252, 255),
        "value_label_border_rgb": (88, 91, 110),
        "flow_palette_rgb": (
            (42, 145, 151),
            (192, 83, 129),
            (95, 135, 205),
            (228, 151, 70),
            (96, 160, 94),
            (154, 104, 190),
            (204, 92, 84),
        ),
    },
    {
        "name": "copper_blue",
        "source_node_fill_rgb": (57, 88, 145),
        "target_node_fill_rgb": (176, 94, 58),
        "ring_line_rgb": (141, 150, 165),
        "value_label_fill_rgb": (255, 254, 250),
        "value_label_border_rgb": (82, 89, 103),
        "flow_palette_rgb": (
            (57, 101, 177),
            (205, 105, 64),
            (73, 150, 112),
            (194, 151, 54),
            (128, 95, 181),
            (68, 142, 174),
            (181, 82, 95),
        ),
    },
    {
        "name": "slate_citrus",
        "source_node_fill_rgb": (70, 83, 105),
        "target_node_fill_rgb": (105, 128, 48),
        "ring_line_rgb": (143, 150, 153),
        "value_label_fill_rgb": (255, 255, 248),
        "value_label_border_rgb": (86, 94, 96),
        "flow_palette_rgb": (
            (78, 96, 125),
            (151, 164, 55),
            (212, 128, 60),
            (72, 151, 164),
            (175, 82, 132),
            (113, 113, 188),
            (89, 145, 93),
        ),
    },
)
_RADIAL_COLOR_SCHEME_BY_NAME = {str(scheme["name"]): dict(scheme) for scheme in _RADIAL_COLOR_SCHEMES}
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "source_to_targets_total": 0.70,
    "sources_to_target_total": 0.72,
    "largest_target_for_source": 0.58,
    "largest_source_for_target": 0.60,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {"radial_chord_sankey": 0.70}

_TASK_GROUP_DEFAULTS = get_scene_defaults("charts", "radial_sankey")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id="radial_sankey")
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id="radial_sankey", apply_prob=0.0)


Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]



@dataclass(frozen=True)
class _RadialRenderParams:
    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    panel_padding_px: int
    title_band_height_px: int
    ring_radius_px: int
    chord_radius_inset_px: int
    node_width_px: int
    node_height_px: int
    node_border_width_px: int
    min_flow_width_px: int
    max_flow_width_px: int
    value_label_font_size_px: int
    value_label_gap_px: int
    node_label_font_size_px: int
    title_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    plot_fill_rgb: Tuple[int, int, int]
    ring_line_rgb: Tuple[int, int, int]
    source_node_fill_rgb: Tuple[int, int, int]
    target_node_fill_rgb: Tuple[int, int, int]
    node_border_rgb: Tuple[int, int, int]
    node_text_rgb: Tuple[int, int, int]
    value_label_fill_rgb: Tuple[int, int, int]
    value_label_border_rgb: Tuple[int, int, int]
    value_label_text_rgb: Tuple[int, int, int]
    title_color_rgb: Tuple[int, int, int]
    color_scheme_name: str
    flow_palette_rgb: Tuple[RGB, ...]
    flow_alpha: int
    layout_offset_x_px: int
    layout_offset_y_px: int
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedRadialSankey:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    panel_bbox_px: List[float]
    title_bbox_px: List[float]
    plot_bbox_px: List[float]
    node_bbox_map: Dict[str, List[float]]
    node_label_bbox_map: Dict[str, List[float]]
    link_bbox_map: Dict[str, List[float]]
    link_label_bbox_map: Dict[str, List[float]]
    link_center_map: Dict[str, List[float]]


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


def _gen_int_param(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), _GEN_DEFAULTS.get(str(key), int(fallback))))


def _as_rgb(raw: Any, fallback: RGB) -> RGB:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or len(raw) != 3:
        return tuple(int(value) for value in fallback)
    return (int(raw[0]), int(raw[1]), int(raw[2]))


def _resolve_radial_color_scheme(params: Mapping[str, Any], *, instance_seed: int) -> Dict[str, Any]:
    explicit = params.get("radial_color_scheme", _RENDER_DEFAULTS.get("radial_color_scheme"))
    if explicit is not None:
        name = str(explicit)
        if name not in _RADIAL_COLOR_SCHEME_BY_NAME:
            raise ValueError(f"unknown radial_color_scheme: {name}")
        selected = dict(_RADIAL_COLOR_SCHEME_BY_NAME[name])
    else:
        raw_options = params.get("radial_color_scheme_options", _RENDER_DEFAULTS.get("radial_color_scheme_options"))
        option_names = (
            [str(value) for value in raw_options if str(value) in _RADIAL_COLOR_SCHEME_BY_NAME]
            if isinstance(raw_options, Sequence) and not isinstance(raw_options, (str, bytes))
            else []
        )
        if not option_names:
            option_names = [str(scheme["name"]) for scheme in _RADIAL_COLOR_SCHEMES]
        index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.radial_color_scheme",
        )
        selected = dict(_RADIAL_COLOR_SCHEME_BY_NAME[str(option_names[int(index) % len(option_names)])])

    palette = [
        _as_rgb(color, (52, 111, 179))
        for color in selected.get("flow_palette_rgb", ())
    ]
    if len(palette) < 3:
        palette = [
            (52, 111, 179),
            (219, 124, 62),
            (68, 156, 118),
            (149, 111, 190),
            (215, 171, 63),
            (70, 144, 169),
        ]
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.flow_palette.{selected['name']}")
    rng.shuffle(palette)
    selected["flow_palette_rgb"] = tuple(palette)
    return selected


def _clamp_bbox(bbox: Sequence[float], *, width: int, height: int) -> List[float]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    x0 = max(0.0, min(float(width), x0))
    y0 = max(0.0, min(float(height), y0))
    x1 = max(0.0, min(float(width), x1))
    y1 = max(0.0, min(float(height), y1))
    if x1 <= x0:
        x1 = min(float(width), x0 + 1.0)
    if y1 <= y0:
        y1 = min(float(height), y0 + 1.0)
    return _round_bbox((x0, y0, x1, y1))


def _resolve_render_params(params: Mapping[str, Any]) -> _RadialRenderParams:
    outer = _int_param(params, "outer_margin_px", 36)
    color_scheme = _resolve_radial_color_scheme(params, instance_seed=_render_style_seed(params))
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
    return _RadialRenderParams(
        canvas_width=_int_param(params, "canvas_width", 1440),
        canvas_height=_int_param(params, "canvas_height", 1040),
        outer_margin_px=int(outer),
        panel_padding_px=_int_param(params, "panel_padding_px", 28),
        title_band_height_px=_int_param(params, "title_band_height_px", 62),
        ring_radius_px=_int_param(params, "radial_ring_radius_px", 360),
        chord_radius_inset_px=_int_param(params, "radial_chord_radius_inset_px", 54),
        node_width_px=_int_param(params, "radial_node_width_px", 78),
        node_height_px=_int_param(params, "radial_node_height_px", 50),
        node_border_width_px=_int_param(params, "node_border_width_px", 2),
        min_flow_width_px=_int_param(params, "radial_min_flow_width_px", _int_param(params, "min_flow_width_px", 6)),
        max_flow_width_px=_int_param(params, "radial_max_flow_width_px", _int_param(params, "max_flow_width_px", 18)),
        value_label_font_size_px=_int_param(params, "value_label_font_size_px", 25),
        value_label_gap_px=max(8, _int_param(params, "value_label_gap_px", 16)),
        node_label_font_size_px=_int_param(params, "node_label_font_size_px", 30),
        title_font_size_px=_int_param(params, "title_font_size_px", 31),
        panel_fill_rgb=_rgb_param(params, "panel_fill_rgb", (252, 253, 251)),
        panel_border_rgb=_rgb_param(params, "panel_border_rgb", (70, 80, 90)),
        plot_fill_rgb=_rgb_param(params, "plot_fill_rgb", (255, 255, 255)),
        ring_line_rgb=_rgb_param(params, "radial_ring_line_rgb", _as_rgb(color_scheme.get("ring_line_rgb"), (170, 178, 188))),
        source_node_fill_rgb=_rgb_param(
            params,
            "radial_source_node_fill_rgb",
            _as_rgb(color_scheme.get("source_node_fill_rgb"), (42, 99, 150)),
        ),
        target_node_fill_rgb=_rgb_param(
            params,
            "radial_target_node_fill_rgb",
            _as_rgb(color_scheme.get("target_node_fill_rgb"), (130, 83, 148)),
        ),
        node_border_rgb=_rgb_param(params, "node_border_rgb", (30, 38, 46)),
        node_text_rgb=_rgb_param(params, "node_text_rgb", (255, 255, 255)),
        value_label_fill_rgb=_rgb_param(
            params,
            "value_label_fill_rgb",
            _as_rgb(color_scheme.get("value_label_fill_rgb"), (255, 255, 255)),
        ),
        value_label_border_rgb=_rgb_param(
            params,
            "value_label_border_rgb",
            _as_rgb(color_scheme.get("value_label_border_rgb"), (82, 88, 96)),
        ),
        value_label_text_rgb=_rgb_param(params, "value_label_text_rgb", (28, 34, 42)),
        title_color_rgb=_rgb_param(params, "title_color_rgb", (32, 38, 46)),
        color_scheme_name=str(color_scheme["name"]),
        flow_palette_rgb=tuple(_as_rgb(color, (52, 111, 179)) for color in color_scheme["flow_palette_rgb"]),
        flow_alpha=max(40, min(220, _int_param(params, "radial_flow_alpha", _int_param(params, "flow_alpha", 138)))),
        layout_offset_x_px=int(jitter_left) - int(outer),
        layout_offset_y_px=int(jitter_top) - int(outer),
        layout_jitter_meta=dict(layout_jitter_meta),
    )


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
