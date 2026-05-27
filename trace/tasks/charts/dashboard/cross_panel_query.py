"""Mixed-dashboard cross-panel chart task."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.sampling import normalize_positive_weights, weighted_choice
from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.font_assets import font_asset_version, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ...shared.visual_style.context_layer import (
    context_text_layer_metadata,
    draw_dashboard_reserved_margin_context,
    resolve_dashboard_context_layout,
    sample_dashboard_title,
)
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin
from ..shared.unanswerable import (
    UNANSWERABLE_ANSWER,
    absence_proof,
    choose_missing_label,
    should_use_unanswerable_branch,
)
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_dashboard_cross_panel_query_base"

_SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "source_rank_target_value",
    "source_rank_difference_value",
    "dual_source_target_sum_value",
    "dual_condition_count",
    "panel_gap_extremum_category_label",
)
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("mixed_dashboard",)
_SUPPORTED_RANK_DIRECTIONS: Tuple[str, ...] = ("largest", "smallest")
_SUPPORTED_CONDITION_COMPARISONS: Tuple[str, ...] = ("greater_than", "less_than")

SUPPORTED_QUERY_VARIANTS = _SUPPORTED_QUERY_VARIANTS
SUPPORTED_SCENE_VARIANTS = _SUPPORTED_SCENE_VARIANTS

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "dashboard")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="dashboard")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="dashboard", apply_prob=0.0)

RGB = Tuple[int, int, int]
BBox = Tuple[int, int, int, int]

_CATEGORY_LABEL_POOL: Tuple[str, ...] = (
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "P",
    "R",
    "S",
    "T",
    "U",
    "V",
)
_PANEL_KIND_NAMES: Dict[str, str] = {
    "bar": "Bars",
    "line": "Line",
    "donut": "Donut",
    "radar": "Radar",
}
_SUPPORTED_PANEL_KINDS: Tuple[str, ...] = ("bar", "line", "donut", "radar")
SUPPORTED_PANEL_KINDS = _SUPPORTED_PANEL_KINDS
_PANEL_TITLE_SUFFIXES: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H", "I")
_MISSING_PANEL_NAME_POOL: Tuple[str, ...] = (
    "Atlas",
    "Beacon",
    "Cobalt",
    "Delta",
    "Echo",
    "Fusion",
    "Harbor",
    "Ion",
    "Juniper",
    "Keystone",
    "Lumen",
    "Meridian",
)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "source_rank_target_value": 0.56,
    "source_rank_difference_value": 0.66,
    "dual_source_target_sum_value": 0.82,
    "dual_condition_count": 0.78,
    "panel_gap_extremum_category_label": 0.70,
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
    query_variant: str
    answer: int | str
    answer_type: str
    evidence_refs: Tuple[Tuple[str, str], ...]
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
    value_label_bboxes_px: Dict[str, Dict[str, BBox]]
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
        namespace=TASK_ID,
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
        namespace=f"{TASK_ID}.layout",
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
            instance_seed=_render_style_seed(params),
            namespace=f"{TASK_ID}.chart_font",
            params=params,
            exclude_tags=("display",),
        ),
        layout_offset_x_px=int(jitter_left) - int(dashboard_margin),
        layout_offset_y_px=int(jitter_top) - int(dashboard_margin),
        layout_jitter_meta=dict(layout_jitter_meta),
    )


def _resolve_query_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_variant")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=_SUPPORTED_QUERY_VARIANTS,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=_SUPPORTED_QUERY_VARIANTS,
        balance_flag_key="balanced_query_variant_sampling",
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        sampling_namespace=f"{TASK_ID}.query_variant",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


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


def _compare_condition(value: int, comparison: str, threshold: int) -> bool:
    if str(comparison) == "greater_than":
        return int(value) > int(threshold)
    if str(comparison) == "less_than":
        return int(value) < int(threshold)
    raise ValueError(f"unsupported comparison: {comparison}")


def _choose_threshold_pair_for_count(
    *,
    rng,
    categories: Sequence[_Category],
    first_panel: _Panel,
    second_panel: _Panel,
    first_comparison: str,
    second_comparison: str,
    target_count: int,
    value_min: int,
    value_max: int,
) -> Tuple[int, int, Tuple[str, ...]]:
    candidates: List[Tuple[int, int, Tuple[str, ...]]] = []
    for first_threshold in range(int(value_min) + 2, int(value_max) - 1):
        for second_threshold in range(int(value_min) + 2, int(value_max) - 1):
            matches = tuple(
                str(category.category_id)
                for category in categories
                if _compare_condition(
                    int(first_panel.values_by_category_id[str(category.category_id)]),
                    str(first_comparison),
                    int(first_threshold),
                )
                and _compare_condition(
                    int(second_panel.values_by_category_id[str(category.category_id)]),
                    str(second_comparison),
                    int(second_threshold),
                )
            )
            if len(matches) == int(target_count):
                candidates.append((int(first_threshold), int(second_threshold), matches))
    if not candidates:
        raise ValueError("no threshold pair realizes the requested condition count")
    return candidates[int(rng.randrange(len(candidates)))]


def _sample_categories(params: Mapping[str, Any], *, instance_seed: int, render_params: _RenderParams) -> Tuple[_Category, ...]:
    category_min, category_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="category_count_min",
        max_key="category_count_max",
        fallback_min=5,
        fallback_max=10,
        context=TASK_ID,
    )
    if int(category_min) < 4:
        raise ValueError("category_count_min must be at least 4 for dashboard charts")
    category_max = min(int(category_max), len(_CATEGORY_LABEL_POOL), len(render_params.category_palette_rgb))
    if int(category_min) > int(category_max):
        raise ValueError("category_count_min exceeds feasible palette/label support")
    explicit_category_count = params.get("category_count")
    if explicit_category_count is not None:
        category_count = int(explicit_category_count)
        if category_count < int(category_min) or category_count > int(category_max):
            raise ValueError("category_count must be within category_count_min..category_count_max")
    else:
        category_count = _balanced_support_choice(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.category_count",
            support=tuple(range(int(category_min), int(category_max) + 1)),
        )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.categories")
    labels = list(_CATEGORY_LABEL_POOL)
    rng.shuffle(labels)
    color_pool = list(render_params.category_palette_rgb)
    rng.shuffle(color_pool)
    return tuple(
        _Category(
            category_id=f"cat_{index}",
            label=str(labels[index]),
            color_rgb=tuple(color_pool[index]),
        )
        for index in range(int(category_count))
    )


def _sample_panels(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    categories: Sequence[_Category],
) -> Tuple[_Panel, ...]:
    panel_count_min, panel_count_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="panel_count_min",
        max_key="panel_count_max",
        fallback_min=4,
        fallback_max=9,
        context=TASK_ID,
    )
    if int(panel_count_min) < 3:
        raise ValueError("panel_count_min must be at least 3 for dashboard cross-panel queries")
    if int(panel_count_max) > len(_PANEL_TITLE_SUFFIXES):
        raise ValueError("panel_count_max exceeds supported dashboard panel-title suffixes")
    explicit_panel_count = params.get("panel_count")
    if explicit_panel_count is not None:
        panel_count = int(explicit_panel_count)
        if panel_count < int(panel_count_min) or panel_count > int(panel_count_max):
            raise ValueError("panel_count must be within panel_count_min..panel_count_max")
    else:
        panel_count = _balanced_support_choice(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.panel_count",
            support=tuple(range(int(panel_count_min), int(panel_count_max) + 1)),
        )
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="value_min",
        max_key="value_max",
        fallback_min=12,
        fallback_max=92,
        context=TASK_ID,
    )
    if int(value_max) - int(value_min) + 1 < len(categories):
        raise ValueError("value range is too small to give each panel unique category values")
    explicit_kinds = params.get("panel_kinds")
    if explicit_kinds is not None:
        if not isinstance(explicit_kinds, Sequence) or isinstance(explicit_kinds, (str, bytes)):
            raise ValueError("panel_kinds must be a sequence when provided")
        selected_kinds = [str(kind) for kind in explicit_kinds]
        if explicit_panel_count is None:
            panel_count = len(selected_kinds)
            if panel_count < int(panel_count_min) or panel_count > int(panel_count_max):
                raise ValueError("panel_kinds length must be within panel_count_min..panel_count_max")
        if len(selected_kinds) != int(panel_count):
            raise ValueError("panel_kinds length must match sampled or configured panel_count")
        unsupported = sorted(set(selected_kinds) - set(_SUPPORTED_PANEL_KINDS))
        if unsupported:
            raise ValueError(f"unsupported panel kinds: {unsupported}")
    else:
        raw_weights = params.get(
            "panel_kind_weights",
            group_default(_GEN_DEFAULTS, "panel_kind_weights", {kind: 1.0 for kind in _SUPPORTED_PANEL_KINDS}),
        )
        if not isinstance(raw_weights, Mapping):
            raise ValueError("panel_kind_weights must be a mapping when provided")
        probabilities = normalize_positive_weights(
            {str(kind): float(weight) for kind, weight in raw_weights.items() if str(kind) in set(_SUPPORTED_PANEL_KINDS)},
            default_keys=list(_SUPPORTED_PANEL_KINDS),
        )
        kind_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.panel_kinds")
        selected_kinds = [
            str(weighted_choice(kind_rng, probabilities, sort_keys=True))
            for _ in range(int(panel_count))
        ]
    panels: List[_Panel] = []
    for index, kind in enumerate(selected_kinds):
        panel_id = f"panel_{index}"
        name = f"{_PANEL_KIND_NAMES[str(kind)]} {_PANEL_TITLE_SUFFIXES[index]}"
        rng = spawn_rng(int(instance_seed), f"{TASK_ID}.panel_values.{panel_id}")
        values = rng.sample(list(range(int(value_min), int(value_max) + 1)), len(categories))
        panels.append(
            _Panel(
                panel_id=str(panel_id),
                kind=str(kind),
                name=str(name),
                values_by_category_id={
                    str(category.category_id): int(value)
                    for category, value in zip(categories, values)
                },
            )
        )
    return tuple(panels)


def _choose_rank_params(
    rng,
    *,
    params: Mapping[str, Any],
    category_count: int,
) -> Tuple[str, int]:
    direction = _weighted_choice_from_defaults(
        rng,
        params=params,
        key="rank_direction",
        supported=_SUPPORTED_RANK_DIRECTIONS,
        fallback_weights_key="rank_direction_weights",
    )
    support = tuple(value for value in _rank_support(params) if int(value) <= int(category_count))
    if not support:
        raise ValueError("rank support has no feasible values for category count")
    rank_n = int(support[int(rng.randrange(len(support)))])
    return str(direction), int(rank_n)


def _build_query(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    query_variant: str,
    query_variant_probabilities: Mapping[str, float],
    categories: Sequence[_Category],
    panels: Sequence[_Panel],
) -> _Query:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query.{query_variant}")
    panel_ids = [str(panel.panel_id) for panel in panels]

    if str(query_variant) == "source_rank_target_value":
        source_id, target_id = rng.sample(panel_ids, 2)
        source_panel = _panel_by_id(panels, source_id)
        target_panel = _panel_by_id(panels, target_id)
        direction, rank_n = _choose_rank_params(rng, params=params, category_count=len(categories))
        category_id = _ranked_category_id(categories=categories, panel=source_panel, direction=direction, rank_n=rank_n)
        answer = int(target_panel.values_by_category_id[str(category_id)])
        query_params = {
            "query_variant": str(query_variant),
            "scene_variant": "mixed_dashboard",
            "query_variant_probabilities": dict(query_variant_probabilities),
            "source_panel_id": str(source_id),
            "source_panel_name": str(source_panel.name),
            "target_panel_id": str(target_id),
            "target_panel_name": str(target_panel.name),
            "rank_direction": str(direction),
            "rank_n": int(rank_n),
            "rank_phrase": _rank_phrase(str(direction), int(rank_n)),
            "selected_category_id": str(category_id),
            "selected_category_label": str(_category_by_id(categories, category_id).label),
            "source_value": int(source_panel.values_by_category_id[str(category_id)]),
            "target_value": int(answer),
        }
        return _Query(
            query_variant=str(query_variant),
            answer=int(answer),
            answer_type="integer",
            evidence_refs=((str(source_id), str(category_id)), (str(target_id), str(category_id))),
            params=query_params,
        )

    if str(query_variant) == "source_rank_difference_value":
        source_id, target_id = rng.sample(panel_ids, 2)
        source_panel = _panel_by_id(panels, source_id)
        target_panel = _panel_by_id(panels, target_id)
        direction, rank_n = _choose_rank_params(rng, params=params, category_count=len(categories))
        category_id = _ranked_category_id(categories=categories, panel=source_panel, direction=direction, rank_n=rank_n)
        source_value = int(source_panel.values_by_category_id[str(category_id)])
        target_value = int(target_panel.values_by_category_id[str(category_id)])
        answer = abs(int(source_value) - int(target_value))
        if int(answer) == 0:
            raise ValueError("source-rank difference must be non-zero")
        query_params = {
            "query_variant": str(query_variant),
            "scene_variant": "mixed_dashboard",
            "query_variant_probabilities": dict(query_variant_probabilities),
            "source_panel_id": str(source_id),
            "source_panel_name": str(source_panel.name),
            "target_panel_id": str(target_id),
            "target_panel_name": str(target_panel.name),
            "rank_direction": str(direction),
            "rank_n": int(rank_n),
            "rank_phrase": _rank_phrase(str(direction), int(rank_n)),
            "selected_category_id": str(category_id),
            "selected_category_label": str(_category_by_id(categories, category_id).label),
            "source_value": int(source_value),
            "target_value": int(target_value),
            "absolute_difference": int(answer),
        }
        return _Query(
            query_variant=str(query_variant),
            answer=int(answer),
            answer_type="integer",
            evidence_refs=((str(source_id), str(category_id)), (str(target_id), str(category_id))),
            params=query_params,
        )

    if str(query_variant) == "dual_source_target_sum_value":
        first_source_id, second_source_id, target_id = rng.sample(panel_ids, 3)
        first_source = _panel_by_id(panels, first_source_id)
        second_source = _panel_by_id(panels, second_source_id)
        target_panel = _panel_by_id(panels, target_id)
        first_direction, first_rank_n = _choose_rank_params(rng, params=params, category_count=len(categories))
        second_direction, second_rank_n = _choose_rank_params(rng, params=params, category_count=len(categories))
        first_category_id = _ranked_category_id(
            categories=categories,
            panel=first_source,
            direction=first_direction,
            rank_n=first_rank_n,
        )
        second_category_id = _ranked_category_id(
            categories=categories,
            panel=second_source,
            direction=second_direction,
            rank_n=second_rank_n,
        )
        if str(first_category_id) == str(second_category_id):
            raise ValueError("dual-source sum needs two distinct selected categories")
        first_target_value = int(target_panel.values_by_category_id[str(first_category_id)])
        second_target_value = int(target_panel.values_by_category_id[str(second_category_id)])
        answer = int(first_target_value) + int(second_target_value)
        query_params = {
            "query_variant": str(query_variant),
            "scene_variant": "mixed_dashboard",
            "query_variant_probabilities": dict(query_variant_probabilities),
            "first_source_panel_id": str(first_source_id),
            "first_source_panel_name": str(first_source.name),
            "second_source_panel_id": str(second_source_id),
            "second_source_panel_name": str(second_source.name),
            "target_panel_id": str(target_id),
            "target_panel_name": str(target_panel.name),
            "first_rank_direction": str(first_direction),
            "first_rank_n": int(first_rank_n),
            "first_rank_phrase": _rank_phrase(str(first_direction), int(first_rank_n)),
            "second_rank_direction": str(second_direction),
            "second_rank_n": int(second_rank_n),
            "second_rank_phrase": _rank_phrase(str(second_direction), int(second_rank_n)),
            "first_category_id": str(first_category_id),
            "first_category_label": str(_category_by_id(categories, first_category_id).label),
            "second_category_id": str(second_category_id),
            "second_category_label": str(_category_by_id(categories, second_category_id).label),
            "first_target_value": int(first_target_value),
            "second_target_value": int(second_target_value),
            "sum_value": int(answer),
        }
        return _Query(
            query_variant=str(query_variant),
            answer=int(answer),
            answer_type="integer",
            evidence_refs=(
                (str(first_source_id), str(first_category_id)),
                (str(second_source_id), str(second_category_id)),
                (str(target_id), str(first_category_id)),
                (str(target_id), str(second_category_id)),
            ),
            params=query_params,
        )

    if str(query_variant) == "dual_condition_count":
        first_panel_id, second_panel_id = rng.sample(panel_ids, 2)
        first_panel = _panel_by_id(panels, first_panel_id)
        second_panel = _panel_by_id(panels, second_panel_id)
        first_comparison = _weighted_choice_from_defaults(
            rng,
            params=params,
            key="first_condition_comparison",
            supported=_SUPPORTED_CONDITION_COMPARISONS,
            fallback_weights_key="condition_comparison_weights",
        )
        second_comparison = _weighted_choice_from_defaults(
            rng,
            params=params,
            key="second_condition_comparison",
            supported=_SUPPORTED_CONDITION_COMPARISONS,
            fallback_weights_key="condition_comparison_weights",
        )
        support = _condition_count_support(params, len(categories))
        support_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.condition_count",
        )
        target_count = int(support[abs(int(support_index)) % len(support)])
        value_min = int(params.get("value_min", group_default(_GEN_DEFAULTS, "value_min", 12)))
        value_max = int(params.get("value_max", group_default(_GEN_DEFAULTS, "value_max", 92)))
        first_threshold, second_threshold, matches = _choose_threshold_pair_for_count(
            rng=rng,
            categories=categories,
            first_panel=first_panel,
            second_panel=second_panel,
            first_comparison=str(first_comparison),
            second_comparison=str(second_comparison),
            target_count=int(target_count),
            value_min=int(value_min),
            value_max=int(value_max),
        )
        evidence_refs: List[Tuple[str, str]] = []
        category_order = {str(category.category_id): index for index, category in enumerate(categories)}
        for category_id in sorted(matches, key=lambda item: category_order[str(item)]):
            evidence_refs.append((str(first_panel_id), str(category_id)))
            evidence_refs.append((str(second_panel_id), str(category_id)))
        query_params = {
            "query_variant": str(query_variant),
            "scene_variant": "mixed_dashboard",
            "query_variant_probabilities": dict(query_variant_probabilities),
            "first_condition_panel_id": str(first_panel_id),
            "first_condition_panel_name": str(first_panel.name),
            "second_condition_panel_id": str(second_panel_id),
            "second_condition_panel_name": str(second_panel.name),
            "first_condition_comparison": str(first_comparison),
            "second_condition_comparison": str(second_comparison),
            "first_threshold": int(first_threshold),
            "second_threshold": int(second_threshold),
            "first_condition_phrase": _condition_phrase(str(first_comparison), int(first_threshold)),
            "second_condition_phrase": _condition_phrase(str(second_comparison), int(second_threshold)),
            "matching_category_ids": list(matches),
            "matching_category_labels": [str(_category_by_id(categories, category_id).label) for category_id in matches],
            "target_count_support": list(support),
            "count_value": int(len(matches)),
        }
        return _Query(
            query_variant=str(query_variant),
            answer=int(len(matches)),
            answer_type="integer",
            evidence_refs=tuple(evidence_refs),
            params=query_params,
        )

    if str(query_variant) == "panel_gap_extremum_category_label":
        first_panel_id, second_panel_id = rng.sample(panel_ids, 2)
        first_panel = _panel_by_id(panels, first_panel_id)
        second_panel = _panel_by_id(panels, second_panel_id)
        direction = _weighted_choice_from_defaults(
            rng,
            params=params,
            key="gap_extremum_direction",
            supported=_SUPPORTED_RANK_DIRECTIONS,
            fallback_weights_key="gap_extremum_weights",
        )
        if should_use_unanswerable_branch(
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.panel_gap_extremum_category_label",
            enabled=bool(params.get("_enable_unanswerable", False)),
        ):
            visible_panel_names = [str(panel.name) for panel in panels]
            missing_panel_name = choose_missing_label(
                visible_labels=visible_panel_names,
                candidate_labels=_MISSING_PANEL_NAME_POOL,
                fallback_prefix="Panel ",
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.missing_panel",
            )
            missing_first = bool(int(rng.randrange(2)) == 0)
            query_params = {
                "query_variant": str(query_variant),
                "scene_variant": "mixed_dashboard",
                "query_variant_probabilities": dict(query_variant_probabilities),
                "first_gap_panel_id": "" if missing_first else str(first_panel_id),
                "first_gap_panel_name": str(missing_panel_name if missing_first else first_panel.name),
                "second_gap_panel_id": "" if not missing_first else str(second_panel_id),
                "second_gap_panel_name": str(missing_panel_name if not missing_first else second_panel.name),
                "gap_extremum_direction": str(direction),
                "gap_extremum_phrase": "largest" if str(direction) == "largest" else "smallest",
                "answer_category_id": "",
                "answer_category_label": UNANSWERABLE_ANSWER,
                "answerability": "unanswerable",
                "absence_proof": absence_proof(
                    requested_item=f"panel {missing_panel_name}",
                    visible_candidates=visible_panel_names,
                    checked_scope="dashboard panel titles",
                    absence_reason="one named comparison panel is not shown in the dashboard",
                ),
            }
            return _Query(
                query_variant=str(query_variant),
                answer=UNANSWERABLE_ANSWER,
                answer_type="string",
                evidence_refs=(),
                params=query_params,
            )
        gaps_by_category = {
            str(category.category_id): abs(
                int(first_panel.values_by_category_id[str(category.category_id)])
                - int(second_panel.values_by_category_id[str(category.category_id)])
            )
            for category in categories
        }
        if len(set(int(value) for value in gaps_by_category.values())) != len(gaps_by_category):
            raise ValueError("panel gap extremum must be unique across categories")
        reverse = str(direction) == "largest"
        answer_category = sorted(
            categories,
            key=lambda category: int(gaps_by_category[str(category.category_id)]),
            reverse=bool(reverse),
        )[0]
        first_value = int(first_panel.values_by_category_id[str(answer_category.category_id)])
        second_value = int(second_panel.values_by_category_id[str(answer_category.category_id)])
        answer_gap = int(gaps_by_category[str(answer_category.category_id)])
        query_params = {
            "query_variant": str(query_variant),
            "scene_variant": "mixed_dashboard",
            "query_variant_probabilities": dict(query_variant_probabilities),
            "first_gap_panel_id": str(first_panel_id),
            "first_gap_panel_name": str(first_panel.name),
            "second_gap_panel_id": str(second_panel_id),
            "second_gap_panel_name": str(second_panel.name),
            "gap_extremum_direction": str(direction),
            "gap_extremum_phrase": "largest" if str(direction) == "largest" else "smallest",
            "answer_category_id": str(answer_category.category_id),
            "answer_category_label": str(answer_category.label),
            "first_value": int(first_value),
            "second_value": int(second_value),
            "answer_gap": int(answer_gap),
            "gaps_by_category_id": dict(gaps_by_category),
            "answerability": "answerable",
        }
        return _Query(
            query_variant=str(query_variant),
            answer=str(answer_category.label),
            answer_type="string",
            evidence_refs=((str(first_panel_id), str(answer_category.category_id)), (str(second_panel_id), str(answer_category.category_id))),
            params=query_params,
        )

    raise ValueError(f"unsupported query_variant: {query_variant}")


def _build_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
    render_params = _resolve_render_params(render_style_params)
    query_variant, query_variant_probabilities = _resolve_query_variant(params, instance_seed=int(instance_seed))
    categories = _sample_categories(params, instance_seed=int(instance_seed), render_params=render_params)
    panels = _sample_panels(params, instance_seed=int(instance_seed), categories=categories)
    query = _build_query(
        params,
        instance_seed=int(instance_seed),
        query_variant=str(query_variant),
        query_variant_probabilities=query_variant_probabilities,
        categories=categories,
        panels=panels,
    )
    common_query_params = {
        "panel_count": int(len(panels)),
        "category_count": int(len(categories)),
        "panel_name_list": _join_labels([str(panel.name) for panel in panels]),
        "panel_kind_list": _join_labels([str(panel.kind) for panel in panels]),
    }
    query = _Query(
        query_variant=str(query.query_variant),
        answer=query.answer,
        answer_type=str(query.answer_type),
        evidence_refs=tuple(query.evidence_refs),
        params={**common_query_params, **dict(query.params)},
    )
    return _Dataset(
        scene_variant="mixed_dashboard",
        categories=tuple(categories),
        panels=tuple(panels),
        query=query,
    )


def _bbox_tuple(box: Sequence[float]) -> BBox:
    return (
        int(math.floor(float(box[0]))),
        int(math.floor(float(box[1]))),
        int(math.ceil(float(box[2]))),
        int(math.ceil(float(box[3]))),
    )


def _union_bboxes(boxes: Sequence[Sequence[float]]) -> BBox:
    valid = [tuple(float(v) for v in box[:4]) for box in boxes if len(box) >= 4]
    if not valid:
        return (0, 0, 0, 0)
    return _bbox_tuple(
        (
            min(box[0] for box in valid),
            min(box[1] for box in valid),
            max(box[2] for box in valid),
            max(box[3] for box in valid),
        )
    )


def _pad_bbox(box: Sequence[float], padding: int) -> BBox:
    return _bbox_tuple((float(box[0]) - int(padding), float(box[1]) - int(padding), float(box[2]) + int(padding), float(box[3]) + int(padding)))


def _clip_bbox_to_canvas(box: Sequence[int], *, width: int, height: int) -> BBox:
    x0, y0, x1, y1 = [int(value) for value in box[:4]]
    clipped_x0 = min(max(0, x0), max(0, int(width) - 1))
    clipped_y0 = min(max(0, y0), max(0, int(height) - 1))
    clipped_x1 = min(max(clipped_x0 + 1, x1), int(width))
    clipped_y1 = min(max(clipped_y0 + 1, y1), int(height))
    return (int(clipped_x0), int(clipped_y0), int(clipped_x1), int(clipped_y1))


def _clip_bbox_map_to_canvas(mapping: Mapping[str, BBox], *, width: int, height: int) -> Dict[str, BBox]:
    return {
        str(key): _clip_bbox_to_canvas(bbox, width=int(width), height=int(height))
        for key, bbox in mapping.items()
    }


def _bbox_map_to_json(mapping: Mapping[str, Sequence[int]]) -> Dict[str, List[int]]:
    return {str(key): [int(value) for value in bbox[:4]] for key, bbox in mapping.items()}


def _nested_bbox_map_to_json(mapping: Mapping[str, Mapping[str, Sequence[int]]]) -> Dict[str, Dict[str, List[int]]]:
    return {str(key): _bbox_map_to_json(value) for key, value in mapping.items()}


def _draw_text(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    *,
    font,
    fill: RGB,
    anchor: str = "mm",
    stroke_width: int = 0,
) -> BBox:
    stroke_fill = resolve_text_stroke_fill(fill)
    bbox = draw.textbbox(tuple(xy), str(text), font=font, anchor=str(anchor), stroke_width=int(stroke_width))
    draw.text(
        tuple(xy),
        str(text),
        font=font,
        anchor=str(anchor),
        fill=tuple(fill),
        stroke_width=int(stroke_width),
        stroke_fill=tuple(stroke_fill),
    )
    return _bbox_tuple(bbox)


def _panel_layout(render_params: _RenderParams, panel_count: int) -> Tuple[BBox, ...]:
    margin = int(render_params.dashboard_margin_px)
    offset_x = int(render_params.layout_offset_x_px)
    offset_y = int(render_params.layout_offset_y_px)
    gap = int(render_params.panel_gap_px)
    top = int(margin + offset_y + render_params.title_height_px)
    context_placement = str(render_params.layout_jitter_meta.get("context_text_placement", "none"))
    sidebar_width = int(render_params.layout_jitter_meta.get("context_text_sidebar_width_px", 0))
    sidebar_gap = int(render_params.layout_jitter_meta.get("context_text_sidebar_gap_px", 14))
    bottom_band_height = int(render_params.layout_jitter_meta.get("context_text_bottom_band_height_px", 0))
    bottom_band_gap = int(render_params.layout_jitter_meta.get("context_text_bottom_band_gap_px", 14))
    left_reserved = int(sidebar_width + sidebar_gap) if context_placement == "left_sidebar" else 0
    right_reserved = int(sidebar_width + sidebar_gap) if context_placement == "right_sidebar" else 0
    bottom_reserved = int(bottom_band_height + bottom_band_gap) if context_placement == "bottom_band" else 0
    cols = 3 if int(panel_count) >= 7 else 2
    rows = max(1, int(math.ceil(float(panel_count) / float(cols))))
    usable_width = int(render_params.canvas_width) - (2 * margin) - int(left_reserved) - int(right_reserved) - (gap * (cols - 1))
    usable_height = int(render_params.canvas_height) - top - margin - int(bottom_reserved) - (gap * (rows - 1))
    if usable_width < cols * 180:
        usable_width = int(render_params.canvas_width) - (2 * margin) - (gap * (cols - 1))
        left_reserved = 0
        right_reserved = 0
    if usable_height < rows * 150:
        usable_height = int(render_params.canvas_height) - top - margin - (gap * (rows - 1))
    panel_width = int(usable_width // cols)
    panel_height = int(usable_height // rows)
    bboxes: List[BBox] = []
    for index in range(int(panel_count)):
        row = int(index) // cols
        col = int(index) % cols
        x0 = margin + offset_x + int(left_reserved) + col * (panel_width + gap)
        y0 = top + row * (panel_height + gap)
        bboxes.append((x0, y0, x0 + panel_width, y0 + panel_height))
    return tuple(bboxes)


def _scale_y(value: int, plot_bbox: BBox) -> float:
    x0, y0, x1, y1 = plot_bbox
    del x0, x1
    return float(y1) - (float(value) / 100.0) * float(y1 - y0)


def _draw_panel_chrome(
    draw: ImageDraw.ImageDraw,
    *,
    panel: _Panel,
    panel_bbox: BBox,
    render_params: _RenderParams,
) -> BBox:
    draw.rounded_rectangle(
        panel_bbox,
        radius=10,
        fill=tuple(render_params.panel_fill_rgb),
        outline=tuple(render_params.panel_border_rgb),
        width=int(render_params.panel_border_width_px),
    )
    title_font = load_font(int(render_params.panel_title_font_size_px), bold=True, font_family=render_params.font_family)
    title_bbox = _draw_text(
        draw,
        ((panel_bbox[0] + panel_bbox[2]) / 2.0, panel_bbox[1] + 24),
        f"{panel.name} panel",
        font=title_font,
        fill=tuple(render_params.text_color_rgb),
        anchor="mm",
        stroke_width=0,
    )
    return title_bbox


def _draw_bar_panel(
    draw: ImageDraw.ImageDraw,
    *,
    panel: _Panel,
    panel_bbox: BBox,
    categories: Sequence[_Category],
    render_params: _RenderParams,
) -> Tuple[Dict[str, BBox], Dict[str, BBox], List[Dict[str, Any]]]:
    pad = int(render_params.panel_padding_px)
    label_size = 10 if len(categories) > 12 else int(render_params.label_font_size_px)
    value_size = 10 if len(categories) > 12 else int(render_params.value_font_size_px)
    label_font = load_font(int(label_size), bold=True, font_family=render_params.font_family)
    value_font = load_font(int(value_size), bold=True, font_family=render_params.font_family)
    tick_font = load_font(int(render_params.tick_font_size_px), bold=False, font_family=render_params.font_family)
    plot_bbox = (
        panel_bbox[0] + pad + 28,
        panel_bbox[1] + pad + 56,
        panel_bbox[2] - pad - 10,
        panel_bbox[3] - pad - 50,
    )
    draw.line((plot_bbox[0], plot_bbox[3], plot_bbox[2], plot_bbox[3]), fill=tuple(render_params.axis_color_rgb), width=int(render_params.axis_line_width_px))
    draw.line((plot_bbox[0], plot_bbox[1], plot_bbox[0], plot_bbox[3]), fill=tuple(render_params.axis_color_rgb), width=int(render_params.axis_line_width_px))
    for tick in (25, 50, 75):
        y = _scale_y(tick, plot_bbox)
        draw.line((plot_bbox[0], y, plot_bbox[2], y), fill=tuple(render_params.grid_color_rgb), width=int(render_params.grid_line_width_px))
        _draw_text(draw, (plot_bbox[0] - 10, y), str(tick), font=tick_font, fill=tuple(render_params.muted_text_color_rgb), anchor="rm")
    slot = float(plot_bbox[2] - plot_bbox[0]) / float(len(categories))
    bar_width = max(18.0, slot * 0.58)
    support: Dict[str, BBox] = {}
    values: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []
    for index, category in enumerate(categories):
        cx = float(plot_bbox[0]) + slot * (float(index) + 0.5)
        value = int(panel.values_by_category_id[str(category.category_id)])
        y = _scale_y(value, plot_bbox)
        bar_box = _bbox_tuple((cx - bar_width / 2.0, y, cx + bar_width / 2.0, plot_bbox[3]))
        draw.rounded_rectangle(bar_box, radius=4, fill=tuple(category.color_rgb), outline=(55, 62, 72), width=1)
        value_bbox = _draw_text(draw, (cx, y - 10), str(value), font=value_font, fill=tuple(render_params.text_color_rgb), anchor="mb", stroke_width=2)
        label_bbox = _draw_text(draw, (cx, plot_bbox[3] + 16), str(category.label), font=label_font, fill=tuple(render_params.text_color_rgb), anchor="mt", stroke_width=1)
        support[str(category.category_id)] = _pad_bbox(_union_bboxes([bar_box, value_bbox, label_bbox]), 4)
        values[str(category.category_id)] = value_bbox
        entities.append(
            {
                "entity_id": f"{panel.panel_id}:{category.category_id}",
                "entity_type": "dashboard_bar_mark",
                "bbox_xyxy": list(support[str(category.category_id)]),
                "attrs": {
                    "panel_id": str(panel.panel_id),
                    "panel_name": str(panel.name),
                    "category_id": str(category.category_id),
                    "category_label": str(category.label),
                    "value": int(value),
                },
            }
        )
    return support, values, entities


def _draw_line_panel(
    draw: ImageDraw.ImageDraw,
    *,
    panel: _Panel,
    panel_bbox: BBox,
    categories: Sequence[_Category],
    render_params: _RenderParams,
) -> Tuple[Dict[str, BBox], Dict[str, BBox], List[Dict[str, Any]]]:
    pad = int(render_params.panel_padding_px)
    label_size = 10 if len(categories) > 12 else int(render_params.label_font_size_px)
    value_size = 10 if len(categories) > 12 else int(render_params.value_font_size_px)
    label_font = load_font(int(label_size), bold=True, font_family=render_params.font_family)
    value_font = load_font(int(value_size), bold=True, font_family=render_params.font_family)
    tick_font = load_font(int(render_params.tick_font_size_px), bold=False, font_family=render_params.font_family)
    plot_bbox = (
        panel_bbox[0] + pad + 28,
        panel_bbox[1] + pad + 58,
        panel_bbox[2] - pad - 12,
        panel_bbox[3] - pad - 50,
    )
    draw.line((plot_bbox[0], plot_bbox[3], plot_bbox[2], plot_bbox[3]), fill=tuple(render_params.axis_color_rgb), width=int(render_params.axis_line_width_px))
    draw.line((plot_bbox[0], plot_bbox[1], plot_bbox[0], plot_bbox[3]), fill=tuple(render_params.axis_color_rgb), width=int(render_params.axis_line_width_px))
    for tick in (25, 50, 75):
        y = _scale_y(tick, plot_bbox)
        draw.line((plot_bbox[0], y, plot_bbox[2], y), fill=tuple(render_params.grid_color_rgb), width=int(render_params.grid_line_width_px))
        _draw_text(draw, (plot_bbox[0] - 10, y), str(tick), font=tick_font, fill=tuple(render_params.muted_text_color_rgb), anchor="rm")
    if len(categories) == 1:
        x_positions = [(plot_bbox[0] + plot_bbox[2]) / 2.0]
    else:
        slot = float(plot_bbox[2] - plot_bbox[0]) / float(len(categories))
        x_positions = [
            float(plot_bbox[0]) + slot * (float(index) + 0.5)
            for index in range(len(categories))
        ]
    points: List[Tuple[float, float]] = []
    for x, category in zip(x_positions, categories):
        points.append((float(x), _scale_y(int(panel.values_by_category_id[str(category.category_id)]), plot_bbox)))
    if len(points) >= 2:
        draw.line(points, fill=tuple(render_params.connector_color_rgb), width=int(render_params.line_width_px), joint="curve")
    support: Dict[str, BBox] = {}
    values: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []
    radius = int(render_params.point_radius_px)
    for (x, y), category in zip(points, categories):
        value = int(panel.values_by_category_id[str(category.category_id)])
        point_box = _bbox_tuple((x - radius, y - radius, x + radius, y + radius))
        draw.ellipse(point_box, fill=tuple(category.color_rgb), outline=(42, 48, 58), width=2)
        value_anchor_y = y - 10 if y - 10 > plot_bbox[1] + 14 else y + 16
        value_anchor = "mb" if value_anchor_y < y else "mt"
        value_bbox = _draw_text(draw, (x, value_anchor_y), str(value), font=value_font, fill=tuple(render_params.text_color_rgb), anchor=value_anchor, stroke_width=2)
        label_bbox = _draw_text(draw, (x, plot_bbox[3] + 16), str(category.label), font=label_font, fill=tuple(render_params.text_color_rgb), anchor="mt", stroke_width=1)
        support[str(category.category_id)] = _pad_bbox(_union_bboxes([point_box, value_bbox, label_bbox]), 4)
        values[str(category.category_id)] = value_bbox
        entities.append(
            {
                "entity_id": f"{panel.panel_id}:{category.category_id}",
                "entity_type": "dashboard_line_point",
                "bbox_xyxy": list(support[str(category.category_id)]),
                "attrs": {
                    "panel_id": str(panel.panel_id),
                    "panel_name": str(panel.name),
                    "category_id": str(category.category_id),
                    "category_label": str(category.label),
                    "value": int(value),
                },
            }
        )
    return support, values, entities


def _draw_donut_panel(
    draw: ImageDraw.ImageDraw,
    *,
    panel: _Panel,
    panel_bbox: BBox,
    categories: Sequence[_Category],
    render_params: _RenderParams,
) -> Tuple[Dict[str, BBox], Dict[str, BBox], List[Dict[str, Any]]]:
    label_size = 9 if len(categories) > 12 else int(render_params.label_font_size_px)
    value_size = 9 if len(categories) > 12 else int(render_params.value_font_size_px)
    label_font = load_font(int(label_size), bold=True, font_family=render_params.font_family)
    value_font = load_font(int(value_size), bold=True, font_family=render_params.font_family)
    x0, y0, x1, y1 = panel_bbox
    panel_width = int(x1 - x0)
    panel_height = int(y1 - y0)
    donut_center = (x0 + max(86, int(panel_width * 0.29)), y0 + max(142, int(panel_height * 0.58)))
    radius = int(min(86, panel_width * 0.22, panel_height * 0.30))
    donut_box = (donut_center[0] - radius, donut_center[1] - radius, donut_center[0] + radius, donut_center[1] + radius)
    total = sum(int(panel.values_by_category_id[str(category.category_id)]) for category in categories)
    start_angle = -90.0
    for category in categories:
        value = int(panel.values_by_category_id[str(category.category_id)])
        sweep = 360.0 * (float(value) / float(max(1, total)))
        draw.pieslice(donut_box, start=start_angle, end=start_angle + sweep, fill=tuple(category.color_rgb), outline=(255, 255, 255), width=2)
        start_angle += sweep
    inner_radius = max(34, int(radius * 0.46))
    inner_box = (donut_center[0] - inner_radius, donut_center[1] - inner_radius, donut_center[0] + inner_radius, donut_center[1] + inner_radius)
    draw.ellipse(inner_box, fill=tuple(render_params.donut_hole_fill_rgb), outline=tuple(render_params.panel_border_rgb), width=1)
    _draw_text(draw, donut_center, "Value", font=value_font, fill=tuple(render_params.muted_text_color_rgb), anchor="mm")
    support: Dict[str, BBox] = {}
    values: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []
    legend_x = x0 + max(190, int(panel_width * 0.54))
    legend_y = y0 + 58
    row_h = max(12, int((y1 - legend_y - 18) / max(1, len(categories))))
    for index, category in enumerate(categories):
        cy = legend_y + index * row_h
        swatch_size = min(12, max(7, int(row_h - 3)))
        row_mid = cy + row_h / 2.0
        swatch_box = (legend_x, int(row_mid - swatch_size / 2), legend_x + swatch_size, int(row_mid + swatch_size / 2))
        draw.rounded_rectangle(swatch_box, radius=3, fill=tuple(category.color_rgb), outline=(70, 76, 86), width=1)
        label_bbox = _draw_text(draw, (legend_x + swatch_size + 8, row_mid), str(category.label), font=label_font, fill=tuple(render_params.text_color_rgb), anchor="lm")
        value = int(panel.values_by_category_id[str(category.category_id)])
        value_bbox = _draw_text(draw, (x1 - 14, row_mid), str(value), font=value_font, fill=tuple(render_params.text_color_rgb), anchor="rm")
        row_box = _union_bboxes([swatch_box, label_bbox, value_bbox])
        support[str(category.category_id)] = _pad_bbox(row_box, 5)
        values[str(category.category_id)] = value_bbox
        entities.append(
            {
                "entity_id": f"{panel.panel_id}:{category.category_id}",
                "entity_type": "dashboard_donut_legend_row",
                "bbox_xyxy": list(support[str(category.category_id)]),
                "attrs": {
                    "panel_id": str(panel.panel_id),
                    "panel_name": str(panel.name),
                    "category_id": str(category.category_id),
                    "category_label": str(category.label),
                    "value": int(value),
                },
            }
        )
    return support, values, entities


def _draw_radar_panel(
    draw: ImageDraw.ImageDraw,
    *,
    panel: _Panel,
    panel_bbox: BBox,
    categories: Sequence[_Category],
    render_params: _RenderParams,
) -> Tuple[Dict[str, BBox], Dict[str, BBox], List[Dict[str, Any]]]:
    label_size = 9 if len(categories) > 12 else int(render_params.label_font_size_px)
    value_size = 9 if len(categories) > 12 else int(render_params.value_font_size_px)
    label_font = load_font(int(label_size), bold=True, font_family=render_params.font_family)
    value_font = load_font(int(value_size), bold=True, font_family=render_params.font_family)
    x0, y0, x1, y1 = panel_bbox
    panel_width = float(x1 - x0)
    panel_height = float(y1 - y0)
    center = ((x0 + x1) / 2.0, y0 + panel_height * 0.60)
    radius = min(92.0, panel_width * 0.22, panel_height * 0.24)
    for frac in (0.25, 0.5, 0.75, 1.0):
        points = []
        for index in range(len(categories)):
            angle = -math.pi / 2.0 + (2.0 * math.pi * float(index) / float(len(categories)))
            points.append((center[0] + math.cos(angle) * radius * frac, center[1] + math.sin(angle) * radius * frac))
        draw.polygon(points, outline=tuple(render_params.grid_color_rgb))
    vertex_points: List[Tuple[float, float]] = []
    support: Dict[str, BBox] = {}
    values: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []
    point_radius = int(render_params.point_radius_px)
    for index, category in enumerate(categories):
        angle = -math.pi / 2.0 + (2.0 * math.pi * float(index) / float(len(categories)))
        axis_end = (center[0] + math.cos(angle) * radius, center[1] + math.sin(angle) * radius)
        draw.line((center[0], center[1], axis_end[0], axis_end[1]), fill=tuple(render_params.grid_color_rgb), width=1)
        value = int(panel.values_by_category_id[str(category.category_id)])
        r_value = radius * (float(value) / 100.0)
        vx = center[0] + math.cos(angle) * r_value
        vy = center[1] + math.sin(angle) * r_value
        vertex_points.append((vx, vy))
    if len(vertex_points) >= 3:
        draw.line(vertex_points + [vertex_points[0]], fill=tuple(render_params.connector_color_rgb), width=int(render_params.line_width_px))
    for index, (category, point) in enumerate(zip(categories, vertex_points)):
        angle = -math.pi / 2.0 + (2.0 * math.pi * float(index) / float(len(categories)))
        value = int(panel.values_by_category_id[str(category.category_id)])
        label_radius = radius + 17
        label_x = center[0] + math.cos(angle) * label_radius
        label_y = center[1] + math.sin(angle) * label_radius
        label_bbox = _draw_text(draw, (label_x, label_y), str(category.label), font=label_font, fill=tuple(render_params.text_color_rgb), anchor="mm", stroke_width=1)
        point_box = _bbox_tuple((point[0] - point_radius, point[1] - point_radius, point[0] + point_radius, point[1] + point_radius))
        draw.ellipse(point_box, fill=tuple(category.color_rgb), outline=(42, 48, 58), width=2)
        value_offset = -20 if int(value) >= 70 else 17
        value_x = point[0] + math.cos(angle) * value_offset
        value_y = point[1] + math.sin(angle) * value_offset
        value_bbox = _draw_text(draw, (value_x, value_y), str(value), font=value_font, fill=tuple(render_params.text_color_rgb), anchor="mm", stroke_width=2)
        support[str(category.category_id)] = _pad_bbox(_union_bboxes([label_bbox, point_box, value_bbox]), 4)
        values[str(category.category_id)] = value_bbox
        entities.append(
            {
                "entity_id": f"{panel.panel_id}:{category.category_id}",
                "entity_type": "dashboard_radar_vertex",
                "bbox_xyxy": list(support[str(category.category_id)]),
                "attrs": {
                    "panel_id": str(panel.panel_id),
                    "panel_name": str(panel.name),
                    "category_id": str(category.category_id),
                    "category_label": str(category.label),
                    "value": int(value),
                },
            }
        )
    return support, values, entities


def _render_dashboard(
    background: Image.Image,
    *,
    dataset: _Dataset,
    render_params: _RenderParams,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Rendered:
    image = background.copy()
    draw = ImageDraw.Draw(image)
    context_params = _resolve_context_text_params(params)
    context_layout = resolve_dashboard_context_layout(
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{dataset.scene_variant}",
        params=context_params,
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        top_reserved_px=int(render_params.title_height_px + render_params.dashboard_margin_px),
        bottom_reserved_px=int(render_params.dashboard_margin_px),
        left_margin_px=int(render_params.dashboard_margin_px),
        right_margin_px=int(render_params.dashboard_margin_px),
    )
    context_layout_mode = f"{context_layout.get('layout_mode', 'reserved_context')}:{context_layout.get('placement', 'none')}"
    render_params = _RenderParams(
        **{
            **render_params.__dict__,
            "layout_jitter_meta": {
                **dict(render_params.layout_jitter_meta),
                "context_text_layout_mode": str(context_layout_mode),
                "context_text_placement": str(context_layout.get("placement", "none")),
                "context_text_box_count": int(context_layout.get("box_count", 0)),
                "context_text_sidebar_width_px": int(context_layout.get("sidebar_width_px", 0)),
                "context_text_sidebar_gap_px": int(context_layout.get("sidebar_gap_px", 0)),
                "context_text_bottom_band_height_px": int(context_layout.get("bottom_band_height_px", 0)),
                "context_text_bottom_band_gap_px": int(context_layout.get("bottom_band_gap_px", 0)),
            },
        }
    )
    context_elements = draw_dashboard_reserved_margin_context(
        image,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{dataset.scene_variant}",
        params=context_params,
        text_rgb=tuple(render_params.text_color_rgb),
        muted_text_rgb=tuple(render_params.muted_text_color_rgb),
        panel_fill_rgb=tuple(render_params.panel_fill_rgb),
        panel_border_rgb=tuple(render_params.panel_border_rgb),
        accent_rgb=tuple(render_params.connector_color_rgb),
        top_reserved_px=int(render_params.title_height_px + render_params.dashboard_margin_px),
        bottom_reserved_px=int(render_params.dashboard_margin_px),
        left_margin_px=int(render_params.dashboard_margin_px),
        right_margin_px=int(render_params.dashboard_margin_px),
        layout_spec=context_layout,
    )
    layout = _panel_layout(render_params, panel_count=len(dataset.panels))
    title_record = sample_dashboard_title(
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{dataset.scene_variant}",
        params=context_params,
    )
    if bool(title_record.get("enabled", False)):
        title_font_family = sample_font_family(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{dataset.scene_variant}.main_title_font",
            params=context_params,
            exclude_tags=("mono", "display"),
            explicit_key="dashboard_title_font_family",
            weights_key="context_text_font_family_weights",
        )
        title_font = load_font(int(render_params.title_font_size_px), bold=True, font_family=title_font_family)
        title_min_x = min(panel_bbox[0] for panel_bbox in layout) if layout else int(render_params.dashboard_margin_px)
        title_max_x = max(panel_bbox[2] for panel_bbox in layout) if layout else int(render_params.canvas_width)
        title_text = str(title_record.get("text", ""))
        title_available_width = max(180, int(title_max_x) - int(title_min_x) - 60)
        if draw.textbbox((0, 0), title_text, font=title_font)[2] > int(title_available_width):
            title_words = title_text.split()
            while len(title_words) > 1 and draw.textbbox((0, 0), f"{' '.join(title_words)}...", font=title_font)[2] > int(title_available_width):
                title_words.pop()
            title_text = f"{' '.join(title_words)}..." if title_words else "Dashboard"
        title_bbox = _draw_text(
            draw,
            (
                (float(title_min_x) + float(title_max_x)) / 2.0,
                35 + float(render_params.layout_offset_y_px),
            ),
            title_text,
            font=title_font,
            fill=tuple(render_params.text_color_rgb),
            anchor="mm",
        )
        title_element = {
            "context_id": f"context_{len(context_elements):02d}",
            "role": "main_title",
            "text": str(title_text),
            "bbox_xyxy": list(title_bbox),
            "manifest_path": str(title_record.get("manifest_path", "")),
            "source_ids": list(title_record.get("source_ids", [])),
            "row_index": int(title_record.get("row_index", -1)),
            "layout_mode": str(context_layout_mode),
            "font_family": str(title_font_family),
            "excluded_from_answer": True,
        }
        context_element_records = [element.to_trace() for element in context_elements] + [dict(title_element)]
    else:
        context_element_records = [element.to_trace() for element in context_elements]
    panel_bboxes: Dict[str, BBox] = {}
    support_bboxes: Dict[str, Dict[str, BBox]] = {}
    value_label_bboxes: Dict[str, Dict[str, BBox]] = {}
    entities: List[Dict[str, Any]] = [
        {
            "entity_id": str(element["context_id"]),
            "entity_type": "non_answer_context_text",
            "bbox_xyxy": list(element["bbox_xyxy"]),
            "attrs": {
                "role": str(element["role"]),
                "text": str(element["text"]),
                "manifest_path": str(element["manifest_path"]),
                "source_ids": list(element["source_ids"]),
                "row_index": int(element["row_index"]),
                "layout_mode": str(element["layout_mode"]),
                "excluded_from_answer": bool(element["excluded_from_answer"]),
            },
        }
        for element in context_element_records
    ]
    for index, panel in enumerate(dataset.panels):
        panel_bbox = layout[int(index)]
        panel_bboxes[str(panel.panel_id)] = panel_bbox
        title_bbox = _draw_panel_chrome(draw, panel=panel, panel_bbox=panel_bbox, render_params=render_params)
        entities.append(
            {
                "entity_id": f"panel:{panel.panel_id}",
                "entity_type": "dashboard_chart_panel",
                "bbox_xyxy": list(panel_bbox),
                "attrs": {"panel_id": str(panel.panel_id), "panel_name": str(panel.name), "panel_kind": str(panel.kind), "title_bbox": list(title_bbox)},
            }
        )
        if str(panel.kind) == "bar":
            support, value_bboxes, mark_entities = _draw_bar_panel(draw, panel=panel, panel_bbox=panel_bbox, categories=dataset.categories, render_params=render_params)
        elif str(panel.kind) == "line":
            support, value_bboxes, mark_entities = _draw_line_panel(draw, panel=panel, panel_bbox=panel_bbox, categories=dataset.categories, render_params=render_params)
        elif str(panel.kind) == "donut":
            support, value_bboxes, mark_entities = _draw_donut_panel(draw, panel=panel, panel_bbox=panel_bbox, categories=dataset.categories, render_params=render_params)
        elif str(panel.kind) == "radar":
            support, value_bboxes, mark_entities = _draw_radar_panel(draw, panel=panel, panel_bbox=panel_bbox, categories=dataset.categories, render_params=render_params)
        else:
            raise ValueError(f"unsupported panel kind: {panel.kind}")
        support_bboxes[str(panel.panel_id)] = _clip_bbox_map_to_canvas(
            support,
            width=int(render_params.canvas_width),
            height=int(render_params.canvas_height),
        )
        value_label_bboxes[str(panel.panel_id)] = _clip_bbox_map_to_canvas(
            value_bboxes,
            width=int(render_params.canvas_width),
            height=int(render_params.canvas_height),
        )
        entities.extend(mark_entities)
    return _Rendered(
        image=image,
        entities=tuple(entities),
        panel_bboxes_px=dict(panel_bboxes),
        support_bboxes_px=dict(support_bboxes),
        value_label_bboxes_px=dict(value_label_bboxes),
        context_text_elements=tuple(context_element_records),
        context_text_layout=dict(context_layout),
    )


def _build_prompt_slots(dataset: _Dataset, prompt_defaults: Mapping[str, Any]) -> Dict[str, str]:
    answer_type = str(dataset.query.answer_type)
    query_variant = str(dataset.query.query_variant)
    if answer_type == "string":
        answer_hint = str(prompt_defaults["answer_hint_label"])
        evidence_hint = str(prompt_defaults["evidence_hint_label"])
        json_example = str(prompt_defaults["json_example_label"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_label"])
    elif query_variant == "dual_condition_count":
        answer_hint = str(prompt_defaults["answer_hint_count"])
        evidence_hint = str(prompt_defaults["evidence_hint_count"])
        json_example = str(prompt_defaults["json_example_count"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_count"])
    else:
        answer_hint = str(prompt_defaults["answer_hint_value"])
        evidence_hint = str(prompt_defaults["evidence_hint_value"])
        json_example = str(prompt_defaults["json_example_value"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_value"])
    object_description_template = str(prompt_defaults["object_description_mixed_dashboard"])
    object_description = object_description_template.format(
        panel_count=int(len(dataset.panels)),
        category_count=int(len(dataset.categories)),
        panel_name_list=_join_labels([str(panel.name) for panel in dataset.panels]),
        panel_kind_list=_join_labels([str(panel.kind) for panel in dataset.panels]),
    )
    slots: Dict[str, str] = {
        "object_description": str(object_description),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(answer_hint),
        "evidence_hint": str(evidence_hint),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
        "unanswerable_instruction": str(prompt_defaults.get("unanswerable_instruction", "")),
    }
    for key, value in dataset.query.params.items():
        if isinstance(value, (str, int, float)):
            slots[str(key)] = str(value)
    return slots


class ChartsDashboardCrossPanelQueryTask:
    """Generate mixed-dashboard cross-panel chart questions."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "dashboard"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        shared_gen_defaults, _, _ = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        )
        task_gen_defaults, _, _ = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
            task_id=str(self.task_id),
        )
        task_override_params = {
            str(key): value
            for key, value in task_gen_defaults.items()
            if shared_gen_defaults.get(str(key)) != value
        }
        effective_params = dict(task_override_params)
        effective_params.update(dict(params))
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                return self._generate_once(int(instance_seed) + int(attempt), params=dict(effective_params))
            except Exception as exc:
                last_error = exc
                continue
        raise RuntimeError(f"failed to generate {self.task_id} after {max_attempts} attempts: {last_error}") from last_error

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        params = {**dict(params), "_enable_unanswerable": bool(getattr(self, "supports_unanswerable", False))}
        render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
        render_params = _resolve_render_params(render_style_params)
        dataset = _build_dataset(params, instance_seed=int(instance_seed))
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered = _render_dashboard(
            background,
            dataset=dataset,
            render_params=render_params,
            params=params,
            instance_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_value",
                "answer_hint_count",
                "answer_hint_label",
                "evidence_hint_value",
                "evidence_hint_count",
                "evidence_hint_label",
                "json_example_value",
                "json_example_count",
                "json_example_label",
                "json_example_answer_only_value",
                "json_example_answer_only_count",
                "json_example_answer_only_label",
                "object_description_mixed_dashboard",
                "unanswerable_instruction",
            ],
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(dataset.query.query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots=_build_prompt_slots(dataset, prompt_defaults),
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_refs = [(str(panel_id), str(category_id)) for panel_id, category_id in dataset.query.evidence_refs]
        evidence_bboxes = [
            list(rendered.support_bboxes_px[str(panel_id)][str(category_id)])
            for panel_id, category_id in evidence_refs
        ]
        answer_value: int | str = int(dataset.query.answer) if str(dataset.query.answer_type) == "integer" else str(dataset.query.answer)
        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=answer_value)
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        panels_by_id = {str(panel.panel_id): panel for panel in dataset.panels}
        categories_by_id = {str(category.category_id): category for category in dataset.categories}
        projected_evidence = {
            "bbox_set": list(evidence_bboxes),
            "evidence_refs": [
                {
                    "panel_id": str(panel_id),
                    "panel_name": str(panels_by_id[str(panel_id)].name),
                    "category_id": str(category_id),
                    "category_label": str(categories_by_id[str(category_id)].label),
                    "bbox_xyxy": list(rendered.support_bboxes_px[str(panel_id)][str(category_id)]),
                }
                for panel_id, category_id in evidence_refs
            ],
        }
        values_by_panel = {
            str(panel.panel_id): {
                "panel_name": str(panel.name),
                "panel_kind": str(panel.kind),
                "values_by_category_id": {
                    str(category_id): int(value)
                    for category_id, value in panel.values_by_category_id.items()
                },
                "values_by_category_label": {
                    str(categories_by_id[str(category_id)].label): int(value)
                    for category_id, value in panel.values_by_category_id.items()
                },
            }
            for panel in dataset.panels
        }
        category_records = [
            {
                "category_id": str(category.category_id),
                "label": str(category.label),
                "color_rgb": list(category.color_rgb),
            }
            for category in dataset.categories
        ]
        panel_records = [
            {
                "panel_id": str(panel.panel_id),
                "panel_kind": str(panel.kind),
                "panel_name": str(panel.name),
            }
            for panel in dataset.panels
        ]
        context_params = _resolve_context_text_params(params)
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(len(dataset.categories) * len(dataset.panels), [15, 64]),
                "reasoning_load": clamp_unit_interval(_REASONING_LOAD_BY_VARIANT[str(dataset.query.query_variant)]),
                "scene_variant_load": clamp_unit_interval(_SCENE_LOAD_BY_VARIANT[str(dataset.scene_variant)]),
            },
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_mixed_dashboard",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_variant": str(dataset.query.query_variant),
                    "scene_variant": str(dataset.scene_variant),
                    "answer": answer_value,
                    "evidence_refs": [list(ref) for ref in evidence_refs],
                    "answerability": str(dataset.query.params.get("answerability", "answerable")),
                    **(
                        {"absence_proof": dict(dataset.query.params["absence_proof"])}
                        if str(dataset.query.params.get("answerability")) == "unanswerable"
                        else {}
                    ),
                },
            },
            "query_spec": {
                "query_variant": str(dataset.query.query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(dataset.query.params),
            },
            "render_spec": {
                "scene_variant": str(dataset.scene_variant),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "panel_count": int(len(dataset.panels)),
                "category_count": int(len(dataset.categories)),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "font_assets": {
                    "asset_version": font_asset_version(),
                    "chart_font_family": str(render_params.font_family),
                },
                "context_text_layer": context_text_layer_metadata(
                    [],
                    enabled=bool(rendered.context_text_layout.get("enabled", True)),
                    layout_mode=f"{rendered.context_text_layout.get('layout_mode', 'reserved_context')}:{rendered.context_text_layout.get('placement', 'none')}",
                    layout_spec=dict(rendered.context_text_layout),
                )
                | {
                    "element_count": int(len(rendered.context_text_elements)),
                    "elements": [dict(element) for element in rendered.context_text_elements],
                },
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "image_id": "img0",
                "panel_bboxes_px": _bbox_map_to_json(rendered.panel_bboxes_px),
                "support_bboxes_px": _nested_bbox_map_to_json(rendered.support_bboxes_px),
                "value_label_bboxes_px": _nested_bbox_map_to_json(rendered.value_label_bboxes_px),
                "context_text_bboxes_px": {
                    str(element["context_id"]): [int(value) for value in element["bbox_xyxy"]]
                    for element in rendered.context_text_elements
                },
            },
            "execution_trace": {
                "query_variant": str(dataset.query.query_variant),
                "scene_variant": str(dataset.scene_variant),
                "question_format": "dashboard_cross_panel_query",
                "answer": answer_value,
                "answer_type": str(dataset.query.answer_type),
                "category_count": int(len(dataset.categories)),
                "panel_count": int(len(dataset.panels)),
                "categories": list(category_records),
                "panels": list(panel_records),
                "panel_order": [str(panel.panel_id) for panel in dataset.panels],
                "panel_kinds": [str(panel.kind) for panel in dataset.panels],
                "values_by_panel": dict(values_by_panel),
                "evidence_refs": [list(ref) for ref in evidence_refs],
                **dict(dataset.query.params),
            },
            "witness_symbolic": {
                "type": "dashboard_cross_panel_witness",
                "evidence_refs": [list(ref) for ref in evidence_refs],
                "answer": answer_value,
                "answerability": str(dataset.query.params.get("answerability", "answerable")),
                **(
                    {"absence_proof": dict(dataset.query.params["absence_proof"])}
                    if str(dataset.query.params.get("answerability")) == "unanswerable"
                    else {}
                ),
            },
            "projected_evidence": dict(projected_evidence),
            "background": background_meta,
            "post_image_noise": dict(post_noise_meta),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant=str(dataset.query.query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsDashboardSourceRankTargetValueTask(
    FixedChartQueryVariantTaskMixin,
    ChartsDashboardCrossPanelQueryTask,
):
    """Lookup a target-panel value after ranking categories in a source panel."""

    task_id = "task_charts__dashboard__source_rank_target_value"
    fixed_query_variant = "source_rank_target_value"


@register_task
class ChartsDashboardSourceRankDifferenceValueTask(
    FixedChartQueryVariantTaskMixin,
    ChartsDashboardCrossPanelQueryTask,
):
    """Compute the difference after ranking categories in a source panel."""

    task_id = "task_charts__dashboard__source_rank_difference_value"
    fixed_query_variant = "source_rank_difference_value"


@register_task
class ChartsDashboardDualSourceTargetSumValueTask(
    FixedChartQueryVariantTaskMixin,
    ChartsDashboardCrossPanelQueryTask,
):
    """Sum target values selected from two source-panel rankings."""

    task_id = "task_charts__dashboard__dual_source_target_sum_value"
    fixed_query_variant = "dual_source_target_sum_value"


@register_task
class ChartsDashboardDualConditionCountTask(
    FixedChartQueryVariantTaskMixin,
    ChartsDashboardCrossPanelQueryTask,
):
    """Count categories satisfying two dashboard panel conditions."""

    task_id = "task_charts__dashboard__dual_condition_count"
    fixed_query_variant = "dual_condition_count"


@register_task
class ChartsDashboardPanelGapExtremumCategoryLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsDashboardCrossPanelQueryTask,
):
    """Return the category with an extremal gap between two panels."""

    task_id = "task_charts__dashboard__panel_gap_extremum_category_label"
    fixed_query_variant = "panel_gap_extremum_category_label"
    supports_unanswerable = True


__all__ = [
    "ChartsDashboardCrossPanelQueryTask",
    "ChartsDashboardDualConditionCountTask",
    "ChartsDashboardDualSourceTargetSumValueTask",
    "ChartsDashboardPanelGapExtremumCategoryLabelTask",
    "ChartsDashboardSourceRankDifferenceValueTask",
    "ChartsDashboardSourceRankTargetValueTask",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_PANEL_KINDS",
    "SUPPORTED_QUERY_VARIANTS",
]
