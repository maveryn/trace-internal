"""Shared constants, specs, and defaults for mixed-dashboard chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from .....core.sampling import normalize_positive_weights, weighted_choice
from .....core.seed import hash64, spawn_rng
from .....core.scene_config import get_scene_defaults
from ....shared.color_distance import coerce_rgb as _rgb
from ....shared.config_defaults import (
    group_default,
    resolve_required_int_bounds,
    split_scene_generation_rendering_prompt_defaults,
)
from ....shared.deterministic_sampling import resolve_selection_index
from ....shared.font_assets import sample_font_family
from ....shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.visual_defaults import load_chart_scene_background_defaults, load_chart_scene_noise_defaults


SCENE_ID = "dashboard"
SCENE_NAMESPACE = "charts.dashboard"
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("mixed_dashboard",)
_SUPPORTED_RANK_DIRECTIONS: Tuple[str, ...] = ("largest", "smallest")
_SUPPORTED_CONDITION_COMPARISONS: Tuple[str, ...] = ("greater_than", "less_than")
_SUPPORTED_REQUESTED_TRUTHS: Tuple[str, ...] = ("true", "false")
_OPTION_LETTERS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

SUPPORTED_SCENE_VARIANTS = _SUPPORTED_SCENE_VARIANTS

_TASK_GROUP_DEFAULTS = get_scene_defaults("charts", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    **{"task" "_id": SCENE_NAMESPACE},
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id=SCENE_ID)
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)

RGB = Tuple[int, int, int]
BBox = Tuple[int, int, int, int]
Point = Tuple[int, int]

_PANEL_KIND_NAMES: Dict[str, str] = {
    "bar": "Bars",
    "line": "Line",
    "donut": "Donut",
    "radar": "Radar",
}
_SUPPORTED_PANEL_KINDS: Tuple[str, ...] = ("bar", "line", "donut", "radar")
SUPPORTED_PANEL_KINDS = _SUPPORTED_PANEL_KINDS
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "source_rank_target_value": 0.56,
    "source_rank_difference_value": 0.66,
    "dual_source_target_sum_value": 0.82,
    "dual_condition_count": 0.78,
    "panel_gap_extremum_category_label": 0.70,
    "shared_label_rank_gap_extremum": 0.76,
    "statement_option_selection_label": 0.72,
    "top_k_overlap_count": 0.76,
    "category_panel_condition_count": 0.72,
}
_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {"mixed_dashboard": 0.82}


@dataclass(frozen=True)
class _Category:
    category_id: str
    label: str
    color_rgb: RGB


@dataclass(frozen=True)
class _Panel:
    panel_id: str
    kind: str
    name: str
    values_by_category_id: Dict[str, int]


@dataclass(frozen=True)
class _Query:
    prompt_key: str
    answer: int | str
    answer_type: str
    annotation_refs: Tuple[Tuple[str, str], ...]
    params: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    scene_variant: str
    categories: Tuple[_Category, ...]
    panels: Tuple[_Panel, ...]
    query: _Query


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    panel_gap_px: int
    dashboard_margin_px: int
    title_height_px: int
    panel_padding_px: int
    panel_border_width_px: int
    axis_line_width_px: int
    grid_line_width_px: int
    bar_min_height_px: int
    point_radius_px: int
    line_width_px: int
    title_font_size_px: int
    panel_title_font_size_px: int
    label_font_size_px: int
    value_font_size_px: int
    tick_font_size_px: int
    panel_fill_rgb: RGB
    panel_border_rgb: RGB
    axis_color_rgb: RGB
    grid_color_rgb: RGB
    text_color_rgb: RGB
    muted_text_color_rgb: RGB
    connector_color_rgb: RGB
    donut_hole_fill_rgb: RGB
    category_palette_rgb: Tuple[RGB, ...]
    font_family: str
    layout_offset_x_px: int
    layout_offset_y_px: int
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    panel_bboxes_px: Dict[str, BBox]
    support_bboxes_px: Dict[str, Dict[str, BBox]]
    support_points_px: Dict[str, Dict[str, Point]]
    value_label_bboxes_px: Dict[str, Dict[str, BBox]]
    option_statement_bboxes_px: Dict[str, BBox]
    context_text_elements: Tuple[Dict[str, Any], ...]
    context_text_layout: Dict[str, Any]


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def _render_rgb(params: Mapping[str, Any], key: str, fallback: RGB) -> RGB:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=SCENE_NAMESPACE,
    )


def _resolve_context_text_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Resolve dashboard context-text render defaults plus caller overrides."""

    keys = (
        "context_text_enabled",
        "context_text_layout_mode",
        "context_text_placement",
        "context_text_placement_weights",
        "context_text_box_count_min",
        "context_text_box_count_max",
        "context_text_top_reserved_px",
        "context_text_bottom_reserved_px",
        "context_text_left_margin_px",
        "context_text_right_margin_px",
        "context_text_sidebar_width_px",
        "context_text_sidebar_width_min_px",
        "context_text_sidebar_width_max_px",
        "context_text_sidebar_gap_px",
        "context_text_bottom_band_height_min_px",
        "context_text_bottom_band_height_max_px",
        "context_text_bottom_band_gap_px",
        "dashboard_title_enabled",
        "dashboard_title_drop_probability",
    )
    resolved: Dict[str, Any] = {}
    for key in keys:
        if str(key) in params:
            resolved[str(key)] = params[str(key)]
        else:
            try:
                resolved[str(key)] = group_default(_RENDER_DEFAULTS, str(key), None)
            except Exception:
                resolved[str(key)] = None
    return {str(key): value for key, value in resolved.items() if value is not None}


def _rgb_sequence(value: Any, fallback: Sequence[RGB]) -> Tuple[RGB, ...]:
    if not isinstance(value, Sequence):
        return tuple(tuple(item) for item in fallback)
    colors: List[RGB] = []
    for item in value:
        if isinstance(item, Sequence) and len(item) >= 3:
            colors.append(_rgb(item, (0, 0, 0)))
    return tuple(colors or [tuple(item) for item in fallback])


def _resolve_render_params(params: Mapping[str, Any]) -> _RenderParams:
    dashboard_margin = int(params.get("dashboard_margin_px", group_default(_RENDER_DEFAULTS, "dashboard_margin_px", 24)))
    jitter_left, _jitter_right, jitter_top, _jitter_bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(dashboard_margin),
        right_px=int(dashboard_margin),
        top_px=int(dashboard_margin),
        bottom_px=int(dashboard_margin),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=_render_style_seed(params),
        namespace=f"{SCENE_NAMESPACE}.layout",
    )
    palette_fallback: Tuple[RGB, ...] = (
        (35, 99, 180),
        (218, 88, 72),
        (54, 145, 95),
        (140, 88, 184),
        (218, 143, 44),
        (72, 156, 190),
        (187, 84, 130),
        (106, 122, 58),
        (98, 112, 214),
        (35, 157, 170),
        (197, 104, 38),
        (82, 121, 111),
        (165, 78, 168),
        (126, 133, 39),
        (186, 70, 98),
        (69, 132, 204),
    )
    return _RenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1260))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 1000))),
        panel_gap_px=int(params.get("panel_gap_px", group_default(_RENDER_DEFAULTS, "panel_gap_px", 18))),
        dashboard_margin_px=int(dashboard_margin),
        title_height_px=int(params.get("title_height_px", group_default(_RENDER_DEFAULTS, "title_height_px", 44))),
        panel_padding_px=int(params.get("panel_padding_px", group_default(_RENDER_DEFAULTS, "panel_padding_px", 16))),
        panel_border_width_px=int(params.get("panel_border_width_px", group_default(_RENDER_DEFAULTS, "panel_border_width_px", 2))),
        axis_line_width_px=int(params.get("axis_line_width_px", group_default(_RENDER_DEFAULTS, "axis_line_width_px", 2))),
        grid_line_width_px=int(params.get("grid_line_width_px", group_default(_RENDER_DEFAULTS, "grid_line_width_px", 1))),
        bar_min_height_px=int(params.get("bar_min_height_px", group_default(_RENDER_DEFAULTS, "bar_min_height_px", 12))),
        point_radius_px=int(params.get("point_radius_px", group_default(_RENDER_DEFAULTS, "point_radius_px", 5))),
        line_width_px=int(params.get("line_width_px", group_default(_RENDER_DEFAULTS, "line_width_px", 3))),
        title_font_size_px=int(params.get("title_font_size_px", group_default(_RENDER_DEFAULTS, "title_font_size_px", 24))),
        panel_title_font_size_px=int(params.get("panel_title_font_size_px", group_default(_RENDER_DEFAULTS, "panel_title_font_size_px", 18))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", 12))),
        value_font_size_px=int(params.get("value_font_size_px", group_default(_RENDER_DEFAULTS, "value_font_size_px", 12))),
        tick_font_size_px=int(params.get("tick_font_size_px", group_default(_RENDER_DEFAULTS, "tick_font_size_px", 11))),
        panel_fill_rgb=_render_rgb(params, "panel_fill_rgb", (255, 255, 255)),
        panel_border_rgb=_render_rgb(params, "panel_border_rgb", (200, 207, 216)),
        axis_color_rgb=_render_rgb(params, "axis_color_rgb", (72, 78, 88)),
        grid_color_rgb=_render_rgb(params, "grid_color_rgb", (228, 232, 238)),
        text_color_rgb=_render_rgb(params, "text_color_rgb", (35, 40, 48)),
        muted_text_color_rgb=_render_rgb(params, "muted_text_color_rgb", (90, 96, 108)),
        connector_color_rgb=_render_rgb(params, "connector_color_rgb", (80, 87, 99)),
        donut_hole_fill_rgb=_render_rgb(params, "donut_hole_fill_rgb", (255, 255, 255)),
        category_palette_rgb=_rgb_sequence(
            params.get("category_palette_rgb", group_default(_RENDER_DEFAULTS, "category_palette_rgb", palette_fallback)),
            palette_fallback,
        ),
        font_family=sample_font_family(
            role="readout",
            instance_seed=_render_style_seed(params),
            namespace=f"{SCENE_NAMESPACE}.chart_font",
            params=params,
            exclude_tags=("display",),
        ),
        layout_offset_x_px=int(jitter_left) - int(dashboard_margin),
        layout_offset_y_px=int(jitter_top) - int(dashboard_margin),
        layout_jitter_meta=dict(layout_jitter_meta),
    )


def _weighted_choice_from_defaults(
    rng,
    *,
    params: Mapping[str, Any],
    key: str,
    supported: Sequence[str],
    fallback_weights_key: str,
) -> str:
    explicit = params.get(str(key))
    supported_values = [str(item) for item in supported]
    if explicit is not None:
        selected = str(explicit)
        if selected not in set(supported_values):
            raise ValueError(f"unsupported {key}: {selected}")
        return selected
    raw_weights = params.get(
        str(fallback_weights_key),
        group_default(_GEN_DEFAULTS, str(fallback_weights_key), {value: 1.0 for value in supported_values}),
    )
    if not isinstance(raw_weights, Mapping):
        raise ValueError(f"{fallback_weights_key} must be a mapping when provided")
    probabilities = normalize_positive_weights(
        {str(name): float(weight) for name, weight in raw_weights.items() if str(name) in set(supported_values)},
        default_keys=supported_values,
    )
    return str(weighted_choice(rng, probabilities, sort_keys=True))


def _rank_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    raw = params.get("rank_n_support", group_default(_GEN_DEFAULTS, "rank_n_support", [1, 2, 3]))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("rank_n_support must be a sequence")
    values = sorted({int(value) for value in raw if int(value) >= 1})
    if not values:
        raise ValueError("rank_n_support must contain at least one positive integer")
    return tuple(values)


def _condition_count_support(params: Mapping[str, Any], category_count: int) -> Tuple[int, ...]:
    raw = params.get("condition_count_support", group_default(_GEN_DEFAULTS, "condition_count_support", [1, 2, 3, 4, 5]))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("condition_count_support must be a sequence")
    values = sorted({int(value) for value in raw if 0 <= int(value) <= int(category_count)})
    if not values:
        raise ValueError("condition_count_support has no values feasible for category count")
    return tuple(values)


def _top_k_support(params: Mapping[str, Any], category_count: int) -> Tuple[int, ...]:
    raw = params.get("top_k_support", group_default(_GEN_DEFAULTS, "top_k_support", [2, 3, 4, 5, 6]))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("top_k_support must be a sequence")
    values = sorted({int(value) for value in raw if 1 <= int(value) <= int(category_count)})
    if not values:
        raise ValueError("top_k_support has no feasible values for category count")
    return tuple(values)


def _top_k_overlap_count_support(params: Mapping[str, Any], *, category_count: int, top_k: int) -> Tuple[int, ...]:
    raw = params.get("top_k_overlap_count_support", group_default(_GEN_DEFAULTS, "top_k_overlap_count_support", [1, 2, 3, 4, 5]))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("top_k_overlap_count_support must be a sequence")
    min_overlap = max(0, int(top_k) * 2 - int(category_count))
    max_overlap = int(top_k)
    values = sorted({int(value) for value in raw if int(min_overlap) <= int(value) <= int(max_overlap)})
    if not values:
        raise ValueError("top_k_overlap_count_support has no feasible values for category count/top_k")
    return tuple(values)


def _panel_condition_count_support(params: Mapping[str, Any], panel_count: int) -> Tuple[int, ...]:
    raw = params.get("panel_condition_count_support", group_default(_GEN_DEFAULTS, "panel_condition_count_support", [1, 2, 3, 4, 5]))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("panel_condition_count_support must be a sequence")
    values = sorted({int(value) for value in raw if 0 <= int(value) <= int(panel_count)})
    if not values:
        raise ValueError("panel_condition_count_support has no values feasible for panel count")
    return tuple(values)


def _balanced_support_choice(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    namespace: str,
    support: Sequence[int],
) -> int:
    values = tuple(int(value) for value in support)
    if not values:
        raise ValueError("support must contain at least one value")
    base_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    salt = abs(int(hash64(0, str(namespace), 0)))
    return int(values[(int(base_index) + int(salt)) % len(values)])


def _join_labels(values: Sequence[str]) -> str:
    labels = [str(value) for value in values]
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


def _join_quoted_labels(values: Sequence[str]) -> str:
    return _join_labels([f'"{str(value)}"' for value in values])


def _option_count_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    explicit = params.get("option_count")
    if explicit is not None:
        count = int(explicit)
        if count not in {4, 6}:
            raise ValueError("option_count must be either 4 or 6 for dashboard statement options")
        return (int(count),)
    raw_support = params.get(
        "statement_option_count_support",
        group_default(_GEN_DEFAULTS, "statement_option_count_support", (4, 6)),
    )
    if isinstance(raw_support, Sequence) and not isinstance(raw_support, (str, bytes)):
        support = tuple(sorted({int(value) for value in raw_support if int(value) in {4, 6}}))
    else:
        support = ()
    if not support:
        raise ValueError("statement option count support is empty")
    return support


def _rank_phrase(direction: str, rank_n: int) -> str:
    if int(rank_n) == 1:
        return "largest" if str(direction) == "largest" else "smallest"
    prefix = {2: "second", 3: "third", 4: "fourth"}.get(int(rank_n), f"{int(rank_n)}th")
    suffix = "largest" if str(direction) == "largest" else "smallest"
    return f"{prefix} {suffix}"


def _condition_phrase(comparison: str, threshold: int) -> str:
    if str(comparison) == "greater_than":
        return f"greater than {int(threshold)}"
    if str(comparison) == "less_than":
        return f"less than {int(threshold)}"
    raise ValueError(f"unsupported comparison: {comparison}")


def _panel_by_id(panels: Sequence[_Panel], panel_id: str) -> _Panel:
    for panel in panels:
        if str(panel.panel_id) == str(panel_id):
            return panel
    raise KeyError(panel_id)


def _category_by_id(categories: Sequence[_Category], category_id: str) -> _Category:
    for category in categories:
        if str(category.category_id) == str(category_id):
            return category
    raise KeyError(category_id)


def _ranked_category_id(
    *,
    categories: Sequence[_Category],
    panel: _Panel,
    direction: str,
    rank_n: int,
) -> str:
    reverse = str(direction) == "largest"
    ordered = sorted(
        categories,
        key=lambda category: int(panel.values_by_category_id[str(category.category_id)]),
        reverse=bool(reverse),
    )
    if int(rank_n) < 1 or int(rank_n) > len(ordered):
        raise ValueError("rank_n is outside category support")
    return str(ordered[int(rank_n) - 1].category_id)


def _rank_positions_by_category_id(
    *,
    categories: Sequence[_Category],
    panel: _Panel,
    direction: str,
) -> Dict[str, int]:
    reverse = str(direction) == "largest"
    ordered = sorted(
        categories,
        key=lambda category: int(panel.values_by_category_id[str(category.category_id)]),
        reverse=bool(reverse),
    )
    return {
        str(category.category_id): int(index + 1)
        for index, category in enumerate(ordered)
    }
