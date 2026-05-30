"""Radial Sankey-style flow chart tasks."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
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
from ...shared.config_defaults import (
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.drawing import draw_centered_text
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.text_rendering import fit_font_to_box, load_font, temporary_default_font_family
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from ..shared.label_assets import resolve_chart_entity_labels
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import (
    chart_font_asset_metadata,
    load_chart_background_defaults,
    load_chart_noise_defaults,
    sample_chart_font_family,
)


TASK_ID = "charts_flow_radial_sankey_base"
SCENE_ID = "radial_sankey"
TRANSFER_TOTAL_QUERY_IDS: Tuple[str, ...] = (
    "source_to_targets_total",
    "sources_to_target_total",
)
DOMINANT_ENDPOINT_QUERY_IDS: Tuple[str, ...] = (
    "largest_target_for_source",
    "largest_source_for_target",
    "second_largest_target_for_source",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = TRANSFER_TOTAL_QUERY_IDS + DOMINANT_ENDPOINT_QUERY_IDS
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
    "second_largest_target_for_source": 0.68,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {"radial_chord_sankey": 0.70}

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


def _resolve_count(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    explicit_key: str,
    fallback_min: int,
    fallback_max: int,
    instance_seed: int,
    namespace: str,
) -> Tuple[int, Tuple[int, int]]:
    lower, upper = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=f"{TASK_ID} {explicit_key}",
    )
    explicit = params.get(str(explicit_key))
    support = [int(value) for value in range(int(lower), int(upper) + 1)]
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"{explicit_key} must be in {lower}..{upper}")
        return int(selected), (int(lower), int(upper))
    return (
        _balanced_int(support, params=params, instance_seed=int(instance_seed), namespace=str(namespace)),
        (int(lower), int(upper)),
    )


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


def _uses_uniform_query_id_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> bool:
    if params.get("query_id") is not None or params.get("query_id_weights") is not None:
        return False
    enabled = bool(params.get("balanced_query_id_sampling", _GEN_DEFAULTS.get("balanced_query_id_sampling", True)))
    if not enabled:
        return False
    positives = [float(value) for value in query_id_probabilities.values() if float(value) > 0.0]
    if len(positives) != len(SUPPORTED_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _support_sampling_params(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    support_params = dict(params)
    sampling_index = support_params.get("_sample_cursor")
    if sampling_index is None:
        return support_params
    if not _uses_uniform_query_id_cycle(params, query_id_probabilities=query_id_probabilities):
        return support_params
    support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_QUERY_IDS))
    return support_params


def _node_specs(labels: Sequence[str], *, prefix: str, role: str) -> List[Dict[str, Any]]:
    return [
        {
            "node_id": f"{prefix}_{index}",
            "label": str(label),
            "role": str(role),
            "index": int(index),
        }
        for index, label in enumerate(labels)
    ]


def _sample_nodes(rng, *, source_count: int, target_count: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    labels = list(
        resolve_chart_entity_labels(
            rng,
            count=int(source_count) + int(target_count),
            min_chars=2,
            max_chars=6,
            allow_spaces=False,
        ).labels
    )
    source_labels = [str(label) for label in labels[: int(source_count)]]
    target_labels = [str(label) for label in labels[int(source_count) : int(source_count) + int(target_count)]]
    return (
        _node_specs(source_labels, prefix="source", role="source"),
        _node_specs(target_labels, prefix="target", role="target"),
    )


def _link_record(
    *,
    link_id: str,
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    value: int,
) -> Dict[str, Any]:
    return {
        "link_id": str(link_id),
        "source_id": str(source["node_id"]),
        "source_label": str(source["label"]),
        "target_id": str(target["node_id"]),
        "target_label": str(target["label"]),
        "value": int(value),
    }


def _sample_links(
    *,
    rng,
    sources: Sequence[Mapping[str, Any]],
    targets: Sequence[Mapping[str, Any]],
    link_count: int,
    value_min: int,
    value_max: int,
) -> List[Dict[str, Any]]:
    all_pairs = [(source, target) for source in sources for target in targets]
    if int(link_count) > len(all_pairs):
        raise ValueError("link_count exceeds unique radial Sankey source-target pairs")
    selected_pairs = rng.sample(list(all_pairs), k=int(link_count))
    links: List[Dict[str, Any]] = []
    for index, (source, target) in enumerate(selected_pairs):
        links.append(
            _link_record(
                link_id=f"link_{index}",
                source=source,
                target=target,
                value=int(rng.randint(int(value_min), int(value_max))),
            )
        )
    return links


def _link_side_counts(links: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, int]]:
    source_out: Counter[str] = Counter()
    target_in: Counter[str] = Counter()
    for link in links:
        source_out[str(link["source_id"])] += 1
        target_in[str(link["target_id"])] += 1
    return {"source_out": dict(source_out), "target_in": dict(target_in)}


def _links_respect_side_limit(links: Sequence[Mapping[str, Any]], *, max_links_per_node_side: int) -> bool:
    if int(max_links_per_node_side) <= 0:
        return True
    for counts in _link_side_counts(links).values():
        if counts and max(int(value) for value in counts.values()) > int(max_links_per_node_side):
            return False
    return True


def _join_quoted(labels: Sequence[str]) -> str:
    quoted = [f'"{str(label)}"' for label in labels]
    if len(quoted) <= 1:
        return quoted[0] if quoted else ""
    if len(quoted) == 2:
        return f"{quoted[0]} and {quoted[1]}"
    return f"{', '.join(quoted[:-1])}, and {quoted[-1]}"


def _choose_query(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    rng,
    links: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    group_min, group_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="radial_group_size_min",
        max_key="radial_group_size_max",
        fallback_min=2,
        fallback_max=3,
        context=f"{TASK_ID} radial grouped endpoint count",
    )
    answer_min, answer_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="radial_transfer_answer_min",
        max_key="radial_transfer_answer_max",
        fallback_min=16,
        fallback_max=100,
        context=f"{TASK_ID} radial transfer answer",
    )

    if str(query_id) == "source_to_targets_total":
        group_size = _balanced_int(
            list(range(int(group_min), int(group_max) + 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.source_target_group_size",
        )
        by_source: Dict[str, List[Dict[str, Any]]] = {}
        for link in links:
            by_source.setdefault(str(link["source_id"]), []).append(dict(link))
        eligible: List[Tuple[str, List[Dict[str, Any]]]] = []
        for source_id, group in sorted(by_source.items()):
            ordered = sorted(group, key=lambda item: (str(item["target_label"]), str(item["link_id"])))
            if len(ordered) < int(group_size):
                continue
            for start in range(0, len(ordered) - int(group_size) + 1):
                subset = ordered[start : start + int(group_size)]
                answer = sum(int(item["value"]) for item in subset)
                if int(answer_min) <= int(answer) <= int(answer_max):
                    eligible.append((str(source_id), subset))
        if not eligible:
            raise ValueError(f"no eligible source grouped transfer for {TASK_ID}")
        _source_id, selected_links = eligible[int(rng.randrange(len(eligible)))]
        source_label = str(selected_links[0]["source_label"])
        target_labels = [str(link["target_label"]) for link in selected_links]
        answer = sum(int(link["value"]) for link in selected_links)
        return {
            "answer_value": int(answer),
            "answer_type": "integer",
            "source_label": str(source_label),
            "source_labels": [],
            "source_labels_joined": "",
            "target_label": "",
            "target_labels": list(target_labels),
            "target_labels_joined": _join_quoted(target_labels),
            "query_link_ids": [str(link["link_id"]) for link in selected_links],
            "comparison_link_ids": [],
            "evidence_link_ids": [str(link["link_id"]) for link in selected_links],
            "evidence_node_ids": [],
            "group_size": int(len(selected_links)),
            "expression": " + ".join(str(int(link["value"])) for link in selected_links),
            "link_details": [dict(link) for link in selected_links],
        }

    if str(query_id) == "sources_to_target_total":
        group_size = _balanced_int(
            list(range(int(group_min), int(group_max) + 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.target_source_group_size",
        )
        by_target: Dict[str, List[Dict[str, Any]]] = {}
        for link in links:
            by_target.setdefault(str(link["target_id"]), []).append(dict(link))
        eligible: List[Tuple[str, List[Dict[str, Any]]]] = []
        for target_id, group in sorted(by_target.items()):
            ordered = sorted(group, key=lambda item: (str(item["source_label"]), str(item["link_id"])))
            if len(ordered) < int(group_size):
                continue
            for start in range(0, len(ordered) - int(group_size) + 1):
                subset = ordered[start : start + int(group_size)]
                answer = sum(int(item["value"]) for item in subset)
                if int(answer_min) <= int(answer) <= int(answer_max):
                    eligible.append((str(target_id), subset))
        if not eligible:
            raise ValueError(f"no eligible target grouped transfer for {TASK_ID}")
        _target_id, selected_links = eligible[int(rng.randrange(len(eligible)))]
        target_label = str(selected_links[0]["target_label"])
        source_labels = [str(link["source_label"]) for link in selected_links]
        answer = sum(int(link["value"]) for link in selected_links)
        return {
            "answer_value": int(answer),
            "answer_type": "integer",
            "source_label": "",
            "source_labels": list(source_labels),
            "source_labels_joined": _join_quoted(source_labels),
            "target_label": str(target_label),
            "target_labels": [],
            "target_labels_joined": "",
            "query_link_ids": [str(link["link_id"]) for link in selected_links],
            "comparison_link_ids": [],
            "evidence_link_ids": [str(link["link_id"]) for link in selected_links],
            "evidence_node_ids": [],
            "group_size": int(len(selected_links)),
            "expression": " + ".join(str(int(link["value"])) for link in selected_links),
            "link_details": [dict(link) for link in selected_links],
        }

    if str(query_id) == "largest_target_for_source":
        by_source: Dict[str, List[Dict[str, Any]]] = {}
        for link in links:
            by_source.setdefault(str(link["source_id"]), []).append(dict(link))
        eligible_sources: List[List[Dict[str, Any]]] = []
        for group in by_source.values():
            ordered = sorted(group, key=lambda item: (-int(item["value"]), str(item["target_label"]), str(item["link_id"])))
            values = [int(item["value"]) for item in ordered]
            if len(ordered) >= 2 and len(set(values)) == len(values):
                eligible_sources.append(ordered)
        if not eligible_sources:
            raise ValueError(f"no eligible largest target query for {TASK_ID}")
        selected_group = eligible_sources[int(rng.randrange(len(eligible_sources)))]
        winner = dict(selected_group[0])
        return {
            "answer_value": str(winner["target_label"]),
            "answer_type": "string",
            "source_label": str(winner["source_label"]),
            "source_labels": [],
            "source_labels_joined": "",
            "target_label": "",
            "target_labels": [],
            "target_labels_joined": "",
            "query_link_ids": [str(link["link_id"]) for link in selected_group],
            "comparison_link_ids": [str(link["link_id"]) for link in selected_group],
            "evidence_link_ids": [str(link["link_id"]) for link in selected_group],
            "evidence_node_ids": [str(winner["target_id"])],
            "group_size": int(len(selected_group)),
            "expression": f"argmax target for {winner['source_label']}",
            "link_details": [dict(link) for link in selected_group],
        }

    if str(query_id) == "largest_source_for_target":
        by_target: Dict[str, List[Dict[str, Any]]] = {}
        for link in links:
            by_target.setdefault(str(link["target_id"]), []).append(dict(link))
        eligible_targets: List[List[Dict[str, Any]]] = []
        for group in by_target.values():
            ordered = sorted(group, key=lambda item: (-int(item["value"]), str(item["source_label"]), str(item["link_id"])))
            values = [int(item["value"]) for item in ordered]
            if len(ordered) >= 2 and len(set(values)) == len(values):
                eligible_targets.append(ordered)
        if not eligible_targets:
            raise ValueError(f"no eligible largest source query for {TASK_ID}")
        selected_group = eligible_targets[int(rng.randrange(len(eligible_targets)))]
        winner = dict(selected_group[0])
        return {
            "answer_value": str(winner["source_label"]),
            "answer_type": "string",
            "source_label": "",
            "source_labels": [],
            "source_labels_joined": "",
            "target_label": str(winner["target_label"]),
            "target_labels": [],
            "target_labels_joined": "",
            "query_link_ids": [str(link["link_id"]) for link in selected_group],
            "comparison_link_ids": [str(link["link_id"]) for link in selected_group],
            "evidence_link_ids": [str(link["link_id"]) for link in selected_group],
            "evidence_node_ids": [str(winner["source_id"])],
            "group_size": int(len(selected_group)),
            "expression": f"argmax source for {winner['target_label']}",
            "link_details": [dict(link) for link in selected_group],
        }

    if str(query_id) == "second_largest_target_for_source":
        by_source: Dict[str, List[Dict[str, Any]]] = {}
        for link in links:
            by_source.setdefault(str(link["source_id"]), []).append(dict(link))
        eligible_sources: List[List[Dict[str, Any]]] = []
        for group in by_source.values():
            ordered = sorted(group, key=lambda item: (-int(item["value"]), str(item["target_label"]), str(item["link_id"])))
            values = [int(item["value"]) for item in ordered]
            if len(ordered) >= 3 and len(set(values)) == len(values):
                eligible_sources.append(ordered)
        if not eligible_sources:
            raise ValueError(f"no eligible second-largest target query for {TASK_ID}")
        selected_group = eligible_sources[int(rng.randrange(len(eligible_sources)))]
        winner = dict(selected_group[1])
        return {
            "answer_value": str(winner["target_label"]),
            "answer_type": "string",
            "source_label": str(winner["source_label"]),
            "source_labels": [],
            "source_labels_joined": "",
            "target_label": "",
            "target_labels": [],
            "target_labels_joined": "",
            "query_link_ids": [str(link["link_id"]) for link in selected_group],
            "comparison_link_ids": [str(link["link_id"]) for link in selected_group],
            "evidence_link_ids": [str(link["link_id"]) for link in selected_group],
            "evidence_node_ids": [str(winner["target_id"])],
            "group_size": int(len(selected_group)),
            "expression": f"second argmax target for {winner['source_label']}",
            "link_details": [dict(link) for link in selected_group],
        }

    raise ValueError(f"unsupported query_id: {query_id}")


def _construct_dataset(
    *,
    query_id: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    if str(scene_variant) != "radial_chord_sankey":
        raise ValueError(f"unsupported scene_variant: {scene_variant}")

    source_count, source_count_bounds = _resolve_count(
        params,
        min_key="radial_source_count_min",
        max_key="radial_source_count_max",
        explicit_key="radial_source_count",
        fallback_min=4,
        fallback_max=5,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.source_count",
    )
    target_count, target_count_bounds = _resolve_count(
        params,
        min_key="radial_target_count_min",
        max_key="radial_target_count_max",
        explicit_key="radial_target_count",
        fallback_min=4,
        fallback_max=5,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.target_count",
    )
    link_count, link_count_bounds = _resolve_count(
        params,
        min_key="radial_link_count_min",
        max_key="radial_link_count_max",
        explicit_key="radial_link_count",
        fallback_min=7,
        fallback_max=9,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.link_count",
    )
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="radial_link_value_min",
        max_key="radial_link_value_max",
        fallback_min=8,
        fallback_max=35,
        context=f"{TASK_ID} radial link values",
    )
    max_links_per_node_side = max(0, _gen_int_param(params, "radial_max_links_per_node_side", 4))

    for attempt in range(120):
        rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset_attempt", int(attempt))
        sources, targets = _sample_nodes(
            rng,
            source_count=int(source_count),
            target_count=int(target_count),
        )
        try:
            links = _sample_links(
                rng=rng,
                sources=sources,
                targets=targets,
                link_count=int(link_count),
                value_min=int(value_min),
                value_max=int(value_max),
            )
        except ValueError:
            continue
        if not _links_respect_side_limit(links, max_links_per_node_side=int(max_links_per_node_side)):
            continue
        try:
            query = _choose_query(
                query_id=str(query_id),
                params=params,
                instance_seed=int(instance_seed),
                rng=rng,
                links=links,
            )
        except ValueError:
            continue
        return {
            "scene_title": str(rng.choice(_TITLE_OPTIONS)),
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "sources": [dict(node) for node in sources],
            "targets": [dict(node) for node in targets],
            "links": [dict(link) for link in links],
            "links_by_id": {str(link["link_id"]): dict(link) for link in links},
            "source_count": int(source_count),
            "target_count": int(target_count),
            "link_count": int(link_count),
            "max_links_per_node_side": int(max_links_per_node_side),
            "link_side_counts": _link_side_counts(links),
            "source_count_bounds": tuple(int(value) for value in source_count_bounds),
            "target_count_bounds": tuple(int(value) for value in target_count_bounds),
            "link_count_bounds": tuple(int(value) for value in link_count_bounds),
            "value_min": int(value_min),
            "value_max": int(value_max),
            "answer_value": query["answer_value"],
            "answer_type": str(query["answer_type"]),
            "query": dict(query),
        }
    raise ValueError(f"failed to construct feasible {TASK_ID} instance")


def _angle_point(center: Point, radius: float, angle_degrees: float) -> Point:
    theta = math.radians(float(angle_degrees))
    return (
        float(center[0] + (float(radius) * math.cos(theta))),
        float(center[1] + (float(radius) * math.sin(theta))),
    )


def _cubic_point(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    inv = 1.0 - float(t)
    x = (inv**3 * p0[0]) + (3 * inv * inv * t * p1[0]) + (3 * inv * t * t * p2[0]) + (t**3 * p3[0])
    y = (inv**3 * p0[1]) + (3 * inv * inv * t * p1[1]) + (3 * inv * t * t * p2[1]) + (t**3 * p3[1])
    return (float(x), float(y))


def _curve_points(start: Point, end: Point, center: Point, *, bend: float, steps: int = 44) -> List[Point]:
    c1 = (
        float(start[0] + (float(center[0] - start[0]) * float(bend))),
        float(start[1] + (float(center[1] - start[1]) * float(bend))),
    )
    c2 = (
        float(end[0] + (float(center[0] - end[0]) * float(bend))),
        float(end[1] + (float(center[1] - end[1]) * float(bend))),
    )
    return [
        _cubic_point(start, c1, c2, end, float(index) / float(max(1, int(steps) - 1)))
        for index in range(int(steps))
    ]


def _curve_bbox(points: Sequence[Point], *, stroke_width: int, canvas_width: int, canvas_height: int) -> List[float]:
    pad = max(2.0, 0.5 * float(stroke_width) + 2.0)
    return _clamp_bbox(
        (
            min(point[0] for point in points) - pad,
            min(point[1] for point in points) - pad,
            max(point[0] for point in points) + pad,
            max(point[1] for point in points) + pad,
        ),
        width=int(canvas_width),
        height=int(canvas_height),
    )


def _flow_width(value: int, *, render_params: _RadialRenderParams, value_min: int, value_max: int) -> int:
    if int(value_max) <= int(value_min):
        return int(render_params.min_flow_width_px)
    norm = (float(value) - float(value_min)) / float(value_max - value_min)
    width = float(render_params.min_flow_width_px) + (
        clamp_unit_interval(norm) * float(render_params.max_flow_width_px - render_params.min_flow_width_px)
    )
    return max(1, int(round(width)))


def _value_label_size(draw: ImageDraw.ImageDraw, *, text: str, render_params: _RadialRenderParams) -> Tuple[float, float]:
    font = load_font(int(render_params.value_label_font_size_px), bold=True)
    text_bbox = draw.textbbox((0, 0), str(text), font=font)
    text_width = float(text_bbox[2] - text_bbox[0])
    text_height = float(text_bbox[3] - text_bbox[1])
    return (max(38.0, float(text_width + 18.0)), max(28.0, float(text_height + 12.0)))


def _value_label_bbox(draw: ImageDraw.ImageDraw, *, text: str, center: Point, render_params: _RadialRenderParams) -> BBox:
    label_width, label_height = _value_label_size(draw, text=str(text), render_params=render_params)
    cx, cy = float(center[0]), float(center[1])
    return (
        float(cx - (0.5 * label_width)),
        float(cy - (0.5 * label_height)),
        float(cx + (0.5 * label_width)),
        float(cy + (0.5 * label_height)),
    )


def _draw_value_label(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Point,
    render_params: _RadialRenderParams,
) -> List[float]:
    font = load_font(int(render_params.value_label_font_size_px), bold=True)
    bbox = _value_label_bbox(draw, text=str(text), center=center, render_params=render_params)
    draw.rounded_rectangle(
        bbox,
        radius=8,
        fill=tuple(int(channel) for channel in render_params.value_label_fill_rgb),
        outline=tuple(int(channel) for channel in render_params.value_label_border_rgb),
        width=1,
    )
    draw_centered_text(
        draw,
        text=str(text),
        center=(float(center[0]), float(center[1])),
        font=font,
        fill=render_params.value_label_text_rgb,
        stroke_fill=render_params.value_label_fill_rgb,
        stroke_width=1,
    )
    return _round_bbox(bbox)


def _resolve_value_label_centers(
    draw: ImageDraw.ImageDraw,
    *,
    label_specs: Sequence[Mapping[str, Any]],
    plot_bbox: Sequence[float],
    render_params: _RadialRenderParams,
) -> Dict[str, Point]:
    group = sorted(
        [dict(spec) for spec in label_specs],
        key=lambda spec: (float(spec["desired_center"][1]), float(spec["desired_center"][0]), str(spec["link_id"])),
    )
    if not group:
        return {}
    top_limit = float(plot_bbox[1]) + 22.0
    bottom_limit = float(plot_bbox[3]) - 22.0
    available_height = max(1.0, float(bottom_limit - top_limit))
    heights = [_value_label_size(draw, text=str(spec["text"]), render_params=render_params)[1] for spec in group]
    total_label_height = sum(float(height) for height in heights)
    if len(group) > 1:
        effective_gap = min(
            float(render_params.value_label_gap_px),
            max(2.0, (available_height - total_label_height) / float(len(group) - 1)),
        )
    else:
        effective_gap = 0.0

    placed: List[Tuple[Dict[str, Any], float, float]] = []
    previous_bottom = float("-inf")
    for spec, height in zip(group, heights):
        half_height = 0.5 * float(height)
        desired_x, desired_y = [float(value) for value in spec["desired_center"]]
        min_center_y = float(top_limit + half_height)
        max_center_y = float(bottom_limit - half_height)
        center_y = max(min_center_y, min(max_center_y, float(desired_y)))
        if placed:
            center_y = max(float(center_y), float(previous_bottom + effective_gap + half_height))
        placed.append((spec, float(center_y), float(height)))
        previous_bottom = float(center_y + half_height)

    overflow = max(0.0, float(previous_bottom - bottom_limit))
    if overflow > 0.0:
        placed = [(spec, float(center_y - overflow), height) for spec, center_y, height in placed]
    first_top = float(placed[0][1] - (0.5 * placed[0][2]))
    underflow = max(0.0, float(top_limit - first_top))
    if underflow > 0.0:
        placed = [(spec, float(center_y + underflow), height) for spec, center_y, height in placed]

    resolved: Dict[str, Point] = {}
    for spec, center_y, _height in placed:
        desired_x = max(float(plot_bbox[0]) + 28.0, min(float(plot_bbox[2]) - 28.0, float(spec["desired_center"][0])))
        resolved[str(spec["link_id"])] = (float(desired_x), float(center_y))
    return resolved


def _node_angles(
    *,
    sources: Sequence[Mapping[str, Any]],
    targets: Sequence[Mapping[str, Any]],
    instance_seed: int,
) -> Dict[str, float]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.node_angles")
    rotation = float(rng.choice([-12, -8, -4, 0, 4, 8, 12]))

    def _arc_angles(count: int, start: float, end: float) -> List[float]:
        if int(count) == 1:
            return [0.5 * (float(start) + float(end)) + float(rotation)]
        return [
            float(start + ((end - start) * float(index) / float(count - 1)) + float(rotation))
            for index in range(int(count))
        ]

    angles: Dict[str, float] = {}
    for node, angle in zip(sources, _arc_angles(len(sources), 132.0, 228.0)):
        angles[str(node["node_id"])] = float(angle)
    for node, angle in zip(targets, _arc_angles(len(targets), -48.0, 48.0)):
        angles[str(node["node_id"])] = float(angle)
    return angles


def _render_radial_sankey(
    background: Image.Image,
    *,
    scene_title: str,
    sources: Sequence[Mapping[str, Any]],
    targets: Sequence[Mapping[str, Any]],
    links: Sequence[Mapping[str, Any]],
    render_params: _RadialRenderParams,
    value_min: int,
    value_max: int,
    instance_seed: int,
) -> _RenderedRadialSankey:
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
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
    plot_bbox: BBox = (
        panel_bbox[0] + float(render_params.panel_padding_px),
        title_bbox[3] + 18.0,
        panel_bbox[2] - float(render_params.panel_padding_px),
        panel_bbox[3] - float(render_params.panel_padding_px),
    )
    center = (0.5 * (plot_bbox[0] + plot_bbox[2]), 0.5 * (plot_bbox[1] + plot_bbox[3]))
    radius = min(
        float(render_params.ring_radius_px),
        0.5 * min(float(plot_bbox[2] - plot_bbox[0]), float(plot_bbox[3] - plot_bbox[1])) - 58.0,
    )
    chord_radius = max(30.0, float(radius - render_params.chord_radius_inset_px))

    draw.rounded_rectangle(panel_bbox, radius=16, fill=render_params.panel_fill_rgb, outline=render_params.panel_border_rgb, width=2)
    draw.rounded_rectangle(plot_bbox, radius=12, fill=render_params.plot_fill_rgb, outline=render_params.panel_border_rgb, width=1)
    ring_bbox = (
        center[0] - float(radius),
        center[1] - float(radius),
        center[0] + float(radius),
        center[1] + float(radius),
    )
    draw.ellipse(ring_bbox, outline=render_params.ring_line_rgb, width=2)
    title_text_bbox = draw_centered_text(
        draw,
        text=str(scene_title),
        center=(0.5 * (title_bbox[0] + title_bbox[2]), 0.5 * (title_bbox[1] + title_bbox[3])),
        font=load_font(int(render_params.title_font_size_px), bold=True),
        fill=render_params.title_color_rgb,
        stroke_fill=render_params.panel_fill_rgb,
        stroke_width=1,
    )

    angles = _node_angles(sources=sources, targets=targets, instance_seed=int(instance_seed))
    all_nodes = [*sources, *targets]
    node_center_map: Dict[str, Point] = {
        str(node["node_id"]): _angle_point(center, float(radius), float(angles[str(node["node_id"])]))
        for node in all_nodes
    }
    chord_anchor_map: Dict[str, Point] = {
        str(node["node_id"]): _angle_point(center, float(chord_radius), float(angles[str(node["node_id"])]))
        for node in all_nodes
    }

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    flow_draw = ImageDraw.Draw(overlay)
    palette = tuple(render_params.flow_palette_rgb)
    link_bbox_map: Dict[str, List[float]] = {}
    link_center_map: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []

    sorted_links = sorted(links, key=lambda link: (str(link["source_label"]), str(link["target_label"]), str(link["link_id"])))
    for index, link in enumerate(sorted_links):
        link_id = str(link["link_id"])
        color = palette[int(index) % len(palette)]
        start = chord_anchor_map[str(link["source_id"])]
        end = chord_anchor_map[str(link["target_id"])]
        bend = 0.42 + (0.05 * float(index % 3))
        points = _curve_points(start, end, center, bend=float(bend))
        stroke_width = _flow_width(
            int(link["value"]),
            render_params=render_params,
            value_min=int(value_min),
            value_max=int(value_max),
        )
        flow_draw.line(
            points,
            fill=(int(color[0]), int(color[1]), int(color[2]), int(render_params.flow_alpha)),
            width=int(stroke_width),
            joint="curve",
        )
        bbox = _curve_bbox(
            points,
            stroke_width=int(stroke_width),
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
        )
        label_t = 0.34 if int(index) % 2 == 0 else 0.66
        label_point = points[int(round(float(label_t) * float(len(points) - 1)))]
        outward_angle = math.atan2(float(label_point[1] - center[1]), float(label_point[0] - center[0]))
        label_center = (
            float(label_point[0] + (16.0 * math.cos(outward_angle))),
            float(label_point[1] + (16.0 * math.sin(outward_angle))),
        )
        link_bbox_map[str(link_id)] = list(bbox)
        link_center_map[str(link_id)] = [round(float(label_center[0]), 3), round(float(label_center[1]), 3)]

    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(image)
    value_label_specs = [
        {
            "link_id": str(link["link_id"]),
            "text": str(int(link["value"])),
            "desired_center": tuple(float(value) for value in link_center_map[str(link["link_id"])]),
        }
        for link in sorted_links
    ]
    resolved_centers = _resolve_value_label_centers(
        draw,
        label_specs=value_label_specs,
        plot_bbox=plot_bbox,
        render_params=render_params,
    )
    link_label_bbox_map: Dict[str, List[float]] = {}
    for link in sorted_links:
        link_id = str(link["link_id"])
        center_px = tuple(float(value) for value in resolved_centers[str(link_id)])
        link_center_map[str(link_id)] = [round(float(center_px[0]), 3), round(float(center_px[1]), 3)]
        link_label_bbox_map[str(link_id)] = _draw_value_label(
            draw,
            text=str(int(link["value"])),
            center=center_px,
            render_params=render_params,
        )
        entities.append(
            {
                "entity_id": str(link_id),
                "entity_type": "radial_sankey_link",
                "bbox_xyxy": list(link_bbox_map[str(link_id)]),
                "attrs": {
                    "source_id": str(link["source_id"]),
                    "source_label": str(link["source_label"]),
                    "target_id": str(link["target_id"]),
                    "target_label": str(link["target_label"]),
                    "value": int(link["value"]),
                    "label_bbox_xyxy": list(link_label_bbox_map[str(link_id)]),
                },
            }
        )

    node_bbox_map: Dict[str, List[float]] = {}
    node_label_bbox_map: Dict[str, List[float]] = {}
    for node in all_nodes:
        node_id = str(node["node_id"])
        cx, cy = node_center_map[str(node_id)]
        half_w = 0.5 * float(render_params.node_width_px)
        half_h = 0.5 * float(render_params.node_height_px)
        bbox = (
            float(cx - half_w),
            float(cy - half_h),
            float(cx + half_w),
            float(cy + half_h),
        )
        fill = render_params.source_node_fill_rgb if str(node["role"]) == "source" else render_params.target_node_fill_rgb
        node_bbox_map[str(node_id)] = _clamp_bbox(bbox, width=int(render_params.canvas_width), height=int(render_params.canvas_height))
        draw.rounded_rectangle(
            bbox,
            radius=12,
            fill=tuple(int(channel) for channel in fill),
            outline=tuple(int(channel) for channel in render_params.node_border_rgb),
            width=max(1, int(render_params.node_border_width_px)),
        )
        label_font = fit_font_to_box(
            draw,
            text=str(node["label"]),
            max_width=float(bbox[2] - bbox[0] - 12.0),
            max_height=float(bbox[3] - bbox[1] - 8.0),
            bold=True,
            min_size_px=12,
            max_size_px=int(render_params.node_label_font_size_px),
            fill_ratio=0.9,
        )
        label_bbox = draw_centered_text(
            draw,
            text=str(node["label"]),
            center=(float(cx), float(cy)),
            font=label_font,
            fill=render_params.node_text_rgb,
            stroke_fill=tuple(int(channel) for channel in fill),
            stroke_width=1,
        )
        node_label_bbox_map[str(node_id)] = list(label_bbox)
        entities.append(
            {
                "entity_id": str(node_id),
                "entity_type": "radial_sankey_node",
                "bbox_xyxy": list(node_bbox_map[str(node_id)]),
                "attrs": {
                    "label": str(node["label"]),
                    "role": str(node["role"]),
                    "angle_degrees": round(float(angles[str(node_id)]), 3),
                },
            }
        )

    entities.insert(0, {"entity_id": "radial_flow_panel", "entity_type": "flow_panel", "bbox_xyxy": _round_bbox(panel_bbox)})
    entities.insert(
        1,
        {
            "entity_id": "radial_flow_title",
            "entity_type": "flow_title",
            "bbox_xyxy": list(title_text_bbox),
            "attrs": {"title": str(scene_title)},
        },
    )
    return _RenderedRadialSankey(
        image=image,
        entities=tuple(dict(item) for item in entities),
        panel_bbox_px=_round_bbox(panel_bbox),
        title_bbox_px=list(title_text_bbox),
        plot_bbox_px=_round_bbox(plot_bbox),
        node_bbox_map=dict(node_bbox_map),
        node_label_bbox_map=dict(node_label_bbox_map),
        link_bbox_map=dict(link_bbox_map),
        link_label_bbox_map=dict(link_label_bbox_map),
        link_center_map=dict(link_center_map),
    )


def _json_examples(query_id: str, *, prompt_defaults: Mapping[str, Any]) -> Tuple[str, str]:
    return (
        str(prompt_defaults[f"json_example_{str(query_id)}"]),
        str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"]),
    )


class ChartsFlowRadialSankeyTask:
    """Answer endpoint-selection and transfer-total questions over a radial Sankey chart."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "flow"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        support_params = _support_sampling_params(params, query_id_probabilities=query_id_probabilities)
        dataset = _construct_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            params=support_params,
            instance_seed=int(instance_seed),
        )
        render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
        render_params = _resolve_render_params(render_style_params)
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        chart_font_family = sample_chart_font_family(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.chart_font",
            params=params,
        )
        with temporary_default_font_family(str(chart_font_family)):
            rendered_scene = _render_radial_sankey(
                background,
                scene_title=str(dataset["scene_title"]),
                sources=list(dataset["sources"]),
                targets=list(dataset["targets"]),
                links=list(dataset["links"]),
                render_params=render_params,
                value_min=int(dataset["value_min"]),
                value_max=int(dataset["value_max"]),
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
                "radial_scene_key",
                "radial_task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_radial_chord_sankey",
                "radial_answer_hint_value",
                "radial_answer_hint_label",
                "radial_evidence_hint",
                "json_example_source_to_targets_total",
                "json_example_sources_to_target_total",
                "json_example_largest_target_for_source",
                "json_example_largest_source_for_target",
                "json_example_second_largest_target_for_source",
                "json_example_answer_only_source_to_targets_total",
                "json_example_answer_only_sources_to_target_total",
                "json_example_answer_only_largest_target_for_source",
                "json_example_answer_only_largest_source_for_target",
                "json_example_answer_only_second_largest_target_for_source",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        query = dict(dataset["query"])
        json_example, json_example_answer_only = _json_examples(str(query_id), prompt_defaults=prompt_defaults)
        answer_hint = (
            str(prompt_defaults["radial_answer_hint_value"])
            if str(dataset["answer_type"]) == "integer"
            else str(prompt_defaults["radial_answer_hint_label"])
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["radial_scene_key"]),
            task_key=str(prompt_defaults["radial_task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_radial_chord_sankey"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["radial_evidence_hint"]),
                "answer_hint": str(answer_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "source_label": str(query.get("source_label", "")),
                "target_label": str(query.get("target_label", "")),
                "source_labels": str(query.get("source_labels_joined", "")),
                "target_labels": str(query.get("target_labels_joined", "")),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_link_ids = [str(link_id) for link_id in query["evidence_link_ids"]]
        evidence_node_ids = [str(node_id) for node_id in query.get("evidence_node_ids", [])]
        evidence_bboxes = [
            list(rendered_scene.link_label_bbox_map[str(link_id)])
            for link_id in evidence_link_ids
        ] + [
            list(rendered_scene.node_bbox_map[str(node_id)])
            for node_id in evidence_node_ids
        ]
        projected_evidence = {
            "type": "bbox_set",
            "bbox_set": list(evidence_bboxes),
            "pixel_bbox_set": list(evidence_bboxes),
            "link_ids": list(evidence_link_ids),
            "node_ids": list(evidence_node_ids),
            "link_label_bbox_map": {
                str(link_id): list(rendered_scene.link_label_bbox_map[str(link_id)])
                for link_id in evidence_link_ids
            },
            "node_bbox_map": {
                str(node_id): list(rendered_scene.node_bbox_map[str(node_id)])
                for node_id in evidence_node_ids
            },
        }

        if str(dataset["answer_type"]) == "integer":
            answer_gt = TypedValue(type="integer", value=int(dataset["answer_value"]))
        else:
            answer_gt = TypedValue(type="string", value=str(dataset["answer_value"]))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        evidence_scan = normalize_int_with_bounds(len(evidence_bboxes), [2, 7])
        link_scan = normalize_int_with_bounds(int(dataset["link_count"]), list(dataset["link_count_bounds"]))
        node_bounds = [
            int(dataset["source_count_bounds"][0]) + int(dataset["target_count_bounds"][0]),
            int(dataset["source_count_bounds"][1]) + int(dataset["target_count_bounds"][1]),
        ]
        node_scan = normalize_int_with_bounds(int(dataset["source_count"]) + int(dataset["target_count"]), node_bounds)
        visual_scan = clamp_unit_interval((0.65 * float(link_scan)) + (0.35 * float(node_scan)))
        reasoning_load = clamp_unit_interval(float(_REASONING_LOAD_BY_VARIANT[str(query_id)]) + (0.10 * float(evidence_scan)))
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
            },
        )

        query_params = {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "source_count": int(dataset["source_count"]),
            "target_count": int(dataset["target_count"]),
            "link_count": int(dataset["link_count"]),
            "max_links_per_node_side": int(dataset["max_links_per_node_side"]),
            "link_side_counts": dict(dataset["link_side_counts"]),
            "source_label": str(query.get("source_label", "")),
            "target_label": str(query.get("target_label", "")),
            "source_labels": [str(value) for value in query.get("source_labels", [])],
            "target_labels": [str(value) for value in query.get("target_labels", [])],
            "source_labels_joined": str(query.get("source_labels_joined", "")),
            "target_labels_joined": str(query.get("target_labels_joined", "")),
            "group_size": int(query.get("group_size", 0)),
            "query_link_ids": [str(link_id) for link_id in query["query_link_ids"]],
            "comparison_link_ids": [str(link_id) for link_id in query.get("comparison_link_ids", [])],
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_radial_sankey",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "answer_value": dataset["answer_value"],
                    "query_link_ids": [str(link_id) for link_id in query["query_link_ids"]],
                    "evidence_link_ids": list(evidence_link_ids),
                    "evidence_node_ids": list(evidence_node_ids),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_variant": str(scene_variant),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "source_count": int(dataset["source_count"]),
                "target_count": int(dataset["target_count"]),
                "link_count": int(dataset["link_count"]),
                "max_links_per_node_side": int(dataset["max_links_per_node_side"]),
                "value_min": int(dataset["value_min"]),
                "value_max": int(dataset["value_max"]),
                "min_flow_width_px": int(render_params.min_flow_width_px),
                "max_flow_width_px": int(render_params.max_flow_width_px),
                "flow_alpha": int(render_params.flow_alpha),
                "radial_color_scheme": str(render_params.color_scheme_name),
                "flow_palette_rgb": [list(color) for color in render_params.flow_palette_rgb],
                "source_node_fill_rgb": list(render_params.source_node_fill_rgb),
                "target_node_fill_rgb": list(render_params.target_node_fill_rgb),
                "ring_line_rgb": list(render_params.ring_line_rgb),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "background_style": dict(background_meta),
                "font_assets": chart_font_asset_metadata(str(chart_font_family)),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "panel_bbox_px": list(rendered_scene.panel_bbox_px),
                "title_bbox_px": list(rendered_scene.title_bbox_px),
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "node_bboxes_px": dict(rendered_scene.node_bbox_map),
                "node_label_bboxes_px": dict(rendered_scene.node_label_bbox_map),
                "link_bboxes_px": dict(rendered_scene.link_bbox_map),
                "link_label_bboxes_px": dict(rendered_scene.link_label_bbox_map),
                "link_centers_px": dict(rendered_scene.link_center_map),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": "radial_sankey_transfer_total_value"
                if str(query_id) in TRANSFER_TOTAL_QUERY_IDS
                else "radial_sankey_dominant_endpoint_label",
                "scene_title": str(dataset["scene_title"]),
                "sources": [dict(node) for node in dataset["sources"]],
                "targets": [dict(node) for node in dataset["targets"]],
                "links": [dict(link) for link in dataset["links"]],
                "links_by_id": {str(key): dict(value) for key, value in dict(dataset["links_by_id"]).items()},
                "source_count": int(dataset["source_count"]),
                "target_count": int(dataset["target_count"]),
                "link_count": int(dataset["link_count"]),
                "max_links_per_node_side": int(dataset["max_links_per_node_side"]),
                "link_side_counts": dict(dataset["link_side_counts"]),
                "value_min": int(dataset["value_min"]),
                "value_max": int(dataset["value_max"]),
                "answer_value": dataset["answer_value"],
                "answer_type": str(dataset["answer_type"]),
                "query_link_ids": [str(link_id) for link_id in query["query_link_ids"]],
                "comparison_link_ids": [str(link_id) for link_id in query.get("comparison_link_ids", [])],
                "evidence_link_ids": list(evidence_link_ids),
                "evidence_node_ids": list(evidence_node_ids),
                "query_link_details": [dict(link) for link in query["link_details"]],
                "source_label": str(query.get("source_label", "")),
                "target_label": str(query.get("target_label", "")),
                "source_labels": [str(value) for value in query.get("source_labels", [])],
                "target_labels": [str(value) for value in query.get("target_labels", [])],
                "group_size": int(query.get("group_size", 0)),
                "expression": str(query["expression"]),
                "evidence_semantics": str(query_id),
            },
            "witness_symbolic": {
                "type": "radial_sankey_transfer_total_value_witness"
                if str(query_id) in TRANSFER_TOTAL_QUERY_IDS
                else "radial_sankey_dominant_endpoint_label_witness",
                "query_link_ids": [str(link_id) for link_id in query["query_link_ids"]],
                "evidence_link_ids": list(evidence_link_ids),
                "evidence_node_ids": list(evidence_node_ids),
                "answer_value": dataset["answer_value"],
                "expression": str(query["expression"]),
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
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )


@register_task
class ChartsFlowRadialSankeyTransferTotalValuePublicTask(
    MergedChartQueryVariantTaskMixin,
    ChartsFlowRadialSankeyTask,
):
    """Return a grouped transfer total from a radial Sankey chart."""

    task_id = "task_charts__radial_sankey__transfer_total_value"
    allowed_query_ids = TRANSFER_TOTAL_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        transfer_params = dict(params)
        transfer_params.setdefault("radial_group_size_min", 2)
        transfer_params.setdefault("radial_group_size_max", 2)
        transfer_params.setdefault("radial_source_count_min", 4)
        transfer_params.setdefault("radial_source_count_max", 4)
        transfer_params.setdefault("radial_target_count_min", 4)
        transfer_params.setdefault("radial_target_count_max", 4)
        transfer_params.setdefault("radial_link_count_min", 5)
        transfer_params.setdefault("radial_link_count_max", 7)
        return super().generate(int(instance_seed), params=transfer_params, max_attempts=int(max_attempts))


@register_task
class ChartsFlowRadialSankeyDominantEndpointLabelPublicTask(
    MergedChartQueryVariantTaskMixin,
    ChartsFlowRadialSankeyTask,
):
    """Return a dominant source or target endpoint from a radial Sankey chart."""

    task_id = "task_charts__radial_sankey__dominant_endpoint_label"
    allowed_query_ids = DOMINANT_ENDPOINT_QUERY_IDS


__all__ = [
    "ChartsFlowRadialSankeyDominantEndpointLabelPublicTask",
    "ChartsFlowRadialSankeyTask",
    "ChartsFlowRadialSankeyTransferTotalValuePublicTask",
    "DOMINANT_ENDPOINT_QUERY_IDS",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
    "TRANSFER_TOTAL_QUERY_IDS",
]
