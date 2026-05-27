"""Waffle/pictogram chart tasks where repeated marks encode quantities."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.drawing import draw_rounded_rect
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.text_rendering import draw_text_centered, fit_font_to_box, load_font
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_pictogram_waffle_chart_base"
SCENE_ID = "pictogram"
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "category_total_value",
    "group_difference_value",
    "threshold_count",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "waffle_grid_blocks",
    "pictogram_rows",
)
SUPPORTED_THRESHOLD_DIRECTIONS: Tuple[str, ...] = ("greater_than", "less_than")
SUPPORTED_GLYPHS: Tuple[str, ...] = ("circle", "square", "star", "person", "car", "leaf", "coin", "book")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "pictogram")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="pictogram")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="pictogram", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)

_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "category_total_value": 0.40,
    "group_difference_value": 0.62,
    "threshold_count": 0.70,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "waffle_grid_blocks": 0.38,
    "pictogram_rows": 0.54,
}

_CATEGORY_LABEL_POOL: Tuple[str, ...] = (
    "Aster",
    "Briar",
    "Cedar",
    "Dune",
    "Ember",
    "Fjord",
    "Grove",
    "Harbor",
    "Ivory",
    "Juniper",
    "Kestrel",
    "Lagoon",
    "Meadow",
    "Nimbus",
    "Orchid",
    "Prairie",
    "Quartz",
    "Ripple",
    "Summit",
    "Tundra",
    "Umber",
    "Vale",
    "Willow",
    "Xylo",
    "Yarrow",
    "Zephyr",
)

RGB = Tuple[int, int, int]
BBox = List[float]


@dataclass(frozen=True)
class _Category:
    category_id: str
    label: str
    mark_count: int
    total: int
    color_rgb: RGB


@dataclass(frozen=True)
class _Query:
    query_variant: str
    answer: int
    answer_type: str
    evidence_category_ids: Tuple[str, ...]
    params: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    categories: Tuple[_Category, ...]
    unit_scale: int
    query_variant: str
    query_variant_probabilities: Dict[str, float]
    scene_variant: str
    scene_variant_probabilities: Dict[str, float]
    glyph_name: str
    glyph_probabilities: Dict[str, float]
    query: _Query
    title: str


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    title_band_height_px: int
    legend_height_px: int
    row_gap_px: int
    label_width_px: int
    mark_gap_px: int
    mark_columns_max: int
    mark_size_max_px: int
    row_corner_radius_px: int
    panel_outline_width_px: int
    title_font_size_px: int
    label_font_size_px: int
    legend_font_size_px: int
    value_font_size_px: int
    text_rgb: RGB
    muted_text_rgb: RGB
    text_stroke_rgb: RGB
    panel_fill_rgb: RGB
    panel_outline_rgb: RGB
    legend_fill_rgb: RGB
    mark_outline_rgb: RGB
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: BBox
    legend_bbox_px: BBox
    category_bboxes_px: Dict[str, BBox]
    mark_bboxes_px: Dict[str, List[BBox]]
    render_meta: Dict[str, Any]


def _bbox(values: Sequence[float]) -> BBox:
    return [round(float(value), 3) for value in values]


def _public_task_param_overrides(task_id: str) -> Dict[str, Any]:
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


def _resolve_query_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_QUERY_VARIANTS,
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
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_threshold_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_THRESHOLD_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="threshold_direction",
        weights_key="threshold_direction_weights",
        balance_flag_key="balanced_threshold_direction_sampling",
        axis_namespace="threshold_direction",
    )


def _resolve_glyph(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_GLYPHS,
        task_id=TASK_ID,
        explicit_key="glyph_name",
        weights_key="glyph_weights",
        balance_flag_key="balanced_glyph_sampling",
        axis_namespace="glyph",
    )


def _sample_balanced_int(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    low: int,
    high: int,
) -> int:
    low_i = int(low)
    high_i = int(high)
    if low_i > high_i:
        raise ValueError(f"invalid integer support for {namespace}: {low_i}>{high_i}")
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    return int(low_i + (abs(int(index)) % (high_i - low_i + 1)))


def _sample_balanced_choice(
    values: Sequence[int],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> int:
    support = [int(value) for value in values]
    if not support:
        raise ValueError(f"empty support for {namespace}")
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    return int(support[abs(int(index)) % len(support)])


def _support_probability_map(values: Sequence[int], *, selected: int | None = None) -> Dict[str, float]:
    support = tuple(int(value) for value in values)
    if not support:
        return {}
    if selected is not None:
        return {str(int(value)): (1.0 if int(value) == int(selected) else 0.0) for value in support}
    probability = 1.0 / float(len(support))
    return {str(int(value)): float(probability) for value in support}


def _resolve_unit_scale(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[int, Dict[str, float]]:
    raw_values = params.get("unit_scale_values", group_default(_GEN_DEFAULTS, "unit_scale_values", [1, 2, 3, 4, 5]))
    support = [int(value) for value in raw_values]
    if not support:
        raise ValueError("unit_scale_values must contain at least one integer")
    explicit = params.get("unit_scale")
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(support):
            raise ValueError(f"unsupported unit_scale: {selected}")
        return selected, _support_probability_map(support, selected=selected)
    selected = _sample_balanced_choice(
        support,
        params=params,
        instance_seed=int(instance_seed),
        namespace="charts.pictogram.unit_scale",
    )
    return selected, _support_probability_map(support)


def _category_palette(params: Mapping[str, Any]) -> Tuple[RGB, ...]:
    raw = params.get("category_palette_rgb", group_default(_RENDER_DEFAULTS, "category_palette_rgb", ()))
    palette = [
        (int(item[0]), int(item[1]), int(item[2]))
        for item in raw
        if isinstance(item, Sequence) and len(item) == 3
    ]
    if not palette:
        palette = [
            (37, 99, 235),
            (220, 84, 45),
            (16, 132, 96),
            (139, 92, 246),
            (202, 138, 4),
            (14, 116, 144),
            (190, 58, 90),
            (86, 105, 38),
            (91, 76, 181),
            (181, 94, 36),
        ]
    return tuple(palette)


def _resolve_categories(
    *,
    mark_counts: Sequence[int],
    unit_scale: int,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[_Category, ...]:
    rng = spawn_rng(int(instance_seed), "charts.pictogram.labels")
    labels = list(rng.sample(list(_CATEGORY_LABEL_POOL), k=len(mark_counts)))
    palette = _category_palette(params)
    categories: List[_Category] = []
    for index, mark_count in enumerate(mark_counts):
        color = palette[index % len(palette)]
        categories.append(
            _Category(
                category_id=f"cat_{index}",
                label=str(labels[index]),
                mark_count=int(mark_count),
                total=int(mark_count) * int(unit_scale),
                color_rgb=(int(color[0]), int(color[1]), int(color[2])),
            )
        )
    return tuple(categories)


def _build_category_total_query(
    *,
    mark_counts: List[int],
    unit_scale: int,
    params: Mapping[str, Any],
    instance_seed: int,
    mark_min: int,
    mark_max: int,
) -> Tuple[List[int], _Query]:
    category_count = len(mark_counts)
    target_index = _sample_balanced_int(
        params=params,
        instance_seed=int(instance_seed),
        namespace="charts.pictogram.category_total.target_index",
        low=0,
        high=category_count - 1,
    )
    target_mark = _sample_balanced_int(
        params=params,
        instance_seed=int(instance_seed),
        namespace="charts.pictogram.category_total.answer_marks",
        low=int(mark_min),
        high=int(mark_max),
    )
    mark_counts[target_index] = int(target_mark)
    answer = int(target_mark) * int(unit_scale)
    return mark_counts, _Query(
        query_variant="category_total_value",
        answer=int(answer),
        answer_type="integer",
        evidence_category_ids=(f"cat_{target_index}",),
        params={
            "target_category_id": f"cat_{target_index}",
            "target_category_index": int(target_index),
            "target_mark_count": int(target_mark),
            "answer_mark_count": int(target_mark),
            "answer_mark_count_probabilities": _support_probability_map(range(int(mark_min), int(mark_max) + 1)),
        },
    )


def _build_group_difference_query(
    *,
    mark_counts: List[int],
    unit_scale: int,
    params: Mapping[str, Any],
    instance_seed: int,
    mark_min: int,
    mark_max: int,
) -> Tuple[List[int], _Query]:
    category_count = len(mark_counts)
    diff_min, diff_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="difference_mark_min",
        max_key="difference_mark_max",
        fallback_min=2,
        fallback_max=10,
        context=f"generation defaults for {TASK_ID}",
    )
    diff_max = min(int(diff_max), max(1, int(mark_max) - int(mark_min)))
    diff_min = min(int(diff_min), int(diff_max))
    diff_marks = _sample_balanced_int(
        params=params,
        instance_seed=int(instance_seed),
        namespace="charts.pictogram.group_difference.diff_marks",
        low=int(diff_min),
        high=int(diff_max),
    )
    rng = spawn_rng(int(instance_seed), "charts.pictogram.group_difference.pair")
    pair = sorted(rng.sample(range(category_count), k=2))
    low_value = rng.randint(int(mark_min), int(mark_max) - int(diff_marks))
    high_value = int(low_value) + int(diff_marks)
    if rng.random() < 0.5:
        mark_counts[pair[0]] = int(low_value)
        mark_counts[pair[1]] = int(high_value)
    else:
        mark_counts[pair[0]] = int(high_value)
        mark_counts[pair[1]] = int(low_value)
    answer = int(diff_marks) * int(unit_scale)
    return mark_counts, _Query(
        query_variant="group_difference_value",
        answer=int(answer),
        answer_type="integer",
        evidence_category_ids=(f"cat_{pair[0]}", f"cat_{pair[1]}"),
        params={
            "category_id_a": f"cat_{pair[0]}",
            "category_id_b": f"cat_{pair[1]}",
            "category_index_a": int(pair[0]),
            "category_index_b": int(pair[1]),
            "difference_mark_count": int(diff_marks),
            "difference_mark_count_probabilities": _support_probability_map(range(int(diff_min), int(diff_max) + 1)),
        },
    )


def _build_threshold_query(
    *,
    mark_counts: List[int],
    unit_scale: int,
    params: Mapping[str, Any],
    instance_seed: int,
    mark_min: int,
    mark_max: int,
) -> Tuple[List[int], _Query]:
    direction, direction_probs = _resolve_threshold_direction(params, instance_seed=int(instance_seed))
    category_count = len(mark_counts)
    answer_min, answer_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="threshold_answer_min",
        max_key="threshold_answer_max",
        fallback_min=1,
        fallback_max=5,
        context=f"generation defaults for {TASK_ID}",
    )
    answer_max = min(int(answer_max), int(category_count) - 1)
    answer_min = min(int(answer_min), int(answer_max))
    target_count = _sample_balanced_int(
        params=params,
        instance_seed=int(instance_seed),
        namespace="charts.pictogram.threshold.target_count",
        low=int(answer_min),
        high=int(answer_max),
    )
    rng = spawn_rng(int(instance_seed), "charts.pictogram.threshold")
    threshold_mark = rng.randint(int(mark_min) + 1, int(mark_max) - 1)
    target_indices = set(rng.sample(range(category_count), k=int(target_count)))
    for index in range(category_count):
        if str(direction) == "greater_than":
            if index in target_indices:
                mark_counts[index] = rng.randint(int(threshold_mark) + 1, int(mark_max))
            else:
                mark_counts[index] = rng.randint(int(mark_min), int(threshold_mark))
        else:
            if index in target_indices:
                mark_counts[index] = rng.randint(int(mark_min), int(threshold_mark) - 1)
            else:
                mark_counts[index] = rng.randint(int(threshold_mark), int(mark_max))
    threshold_value = int(threshold_mark) * int(unit_scale)
    threshold_phrase = f"greater than {threshold_value}" if str(direction) == "greater_than" else f"less than {threshold_value}"
    return mark_counts, _Query(
        query_variant="threshold_count",
        answer=int(target_count),
        answer_type="integer",
        evidence_category_ids=tuple(f"cat_{index}" for index in sorted(target_indices)),
        params={
            "threshold_direction": str(direction),
            "threshold_direction_probabilities": dict(direction_probs),
            "threshold_mark_count": int(threshold_mark),
            "threshold_value": int(threshold_value),
            "threshold_phrase": str(threshold_phrase),
            "target_count": int(target_count),
            "target_count_probabilities": _support_probability_map(range(int(answer_min), int(answer_max) + 1)),
        },
    )


def _construct_dataset(
    *,
    query_variant: str,
    query_variant_probabilities: Mapping[str, float],
    scene_variant: str,
    scene_variant_probabilities: Mapping[str, float],
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Dataset:
    category_min, category_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="category_count_min",
        max_key="category_count_max",
        fallback_min=6,
        fallback_max=10,
        context=f"generation defaults for {TASK_ID}",
    )
    mark_min, mark_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="mark_count_min",
        max_key="mark_count_max",
        fallback_min=4,
        fallback_max=16,
        context=f"generation defaults for {TASK_ID}",
    )
    if int(mark_min) < 2:
        raise ValueError("mark_count_min must be at least 2")
    if int(mark_max) <= int(mark_min):
        raise ValueError("mark_count_max must exceed mark_count_min")
    category_count = _sample_balanced_int(
        params=params,
        instance_seed=int(instance_seed),
        namespace="charts.pictogram.category_count",
        low=int(category_min),
        high=int(category_max),
    )
    unit_scale, _unit_probs = _resolve_unit_scale(params, instance_seed=int(instance_seed))
    rng = spawn_rng(int(instance_seed), "charts.pictogram.base_counts")
    mark_counts = [rng.randint(int(mark_min), int(mark_max)) for _ in range(int(category_count))]

    if str(query_variant) == "category_total_value":
        mark_counts, query = _build_category_total_query(
            mark_counts=mark_counts,
            unit_scale=int(unit_scale),
            params=params,
            instance_seed=int(instance_seed),
            mark_min=int(mark_min),
            mark_max=int(mark_max),
        )
    elif str(query_variant) == "group_difference_value":
        mark_counts, query = _build_group_difference_query(
            mark_counts=mark_counts,
            unit_scale=int(unit_scale),
            params=params,
            instance_seed=int(instance_seed),
            mark_min=int(mark_min),
            mark_max=int(mark_max),
        )
    elif str(query_variant) == "threshold_count":
        mark_counts, query = _build_threshold_query(
            mark_counts=mark_counts,
            unit_scale=int(unit_scale),
            params=params,
            instance_seed=int(instance_seed),
            mark_min=int(mark_min),
            mark_max=int(mark_max),
        )
    else:
        raise ValueError(f"unsupported query_variant: {query_variant}")

    glyph, glyph_probabilities = _resolve_glyph(params, instance_seed=int(instance_seed))
    categories = _resolve_categories(
        mark_counts=mark_counts,
        unit_scale=int(unit_scale),
        params=params,
        instance_seed=int(instance_seed),
    )
    category_by_id = {category.category_id: category for category in categories}
    qparams = dict(query.params)
    if "target_category_id" in qparams:
        qparams["target_category_label"] = str(category_by_id[str(qparams["target_category_id"])].label)
    if "category_id_a" in qparams:
        qparams["category_label_a"] = str(category_by_id[str(qparams["category_id_a"])].label)
        qparams["category_label_b"] = str(category_by_id[str(qparams["category_id_b"])].label)
    query = _Query(
        query_variant=str(query.query_variant),
        answer=int(query.answer),
        answer_type=str(query.answer_type),
        evidence_category_ids=tuple(str(value) for value in query.evidence_category_ids),
        params=qparams,
    )
    title_options = ("Unit Quantity Chart", "Category Unit Chart", "Pictogram Totals", "Repeated-Mark Summary")
    title = title_options[abs(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace="charts.pictogram.title")) % len(title_options)]
    return _Dataset(
        categories=tuple(categories),
        unit_scale=int(unit_scale),
        query_variant=str(query_variant),
        query_variant_probabilities={str(key): float(value) for key, value in query_variant_probabilities.items()},
        scene_variant=str(scene_variant),
        scene_variant_probabilities={str(key): float(value) for key, value in scene_variant_probabilities.items()},
        glyph_name=str(glyph),
        glyph_probabilities=dict(glyph_probabilities),
        query=query,
        title=str(title),
    )


def _render_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_RENDER_DEFAULTS, str(key), int(fallback))))


def _resolve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    outer = _render_int(params, "outer_margin_px", 44)
    title_band = _render_int(params, "title_band_height_px", 70)
    legend_height = _render_int(params, "legend_height_px", 58)
    bottom = _render_int(params, "bottom_margin_px", 48)
    left, right, top, bottom, jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(outer),
        right_px=int(outer),
        top_px=int(outer),
        bottom_px=int(bottom),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="charts.pictogram.layout",
    )
    return _RenderParams(
        canvas_width=_render_int(params, "canvas_width", 1320),
        canvas_height=_render_int(params, "canvas_height", 900),
        outer_margin_px=int(left),
        title_band_height_px=int(title_band),
        legend_height_px=int(legend_height),
        row_gap_px=_render_int(params, "row_gap_px", 8),
        label_width_px=_render_int(params, "label_width_px", 178),
        mark_gap_px=_render_int(params, "mark_gap_px", 6),
        mark_columns_max=_render_int(params, "mark_columns_max", 10),
        mark_size_max_px=_render_int(params, "mark_size_max_px", 34),
        row_corner_radius_px=_render_int(params, "row_corner_radius_px", 8),
        panel_outline_width_px=_render_int(params, "panel_outline_width_px", 2),
        title_font_size_px=_render_int(params, "title_font_size_px", 28),
        label_font_size_px=_render_int(params, "label_font_size_px", 22),
        legend_font_size_px=_render_int(params, "legend_font_size_px", 20),
        value_font_size_px=_render_int(params, "value_font_size_px", 15),
        text_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_rgb", (36, 42, 52), instance_seed=int(instance_seed), namespace=TASK_ID),
        muted_text_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "muted_text_rgb", (86, 95, 108), instance_seed=int(instance_seed), namespace=TASK_ID),
        text_stroke_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_stroke_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=TASK_ID),
        panel_fill_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "panel_fill_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=TASK_ID),
        panel_outline_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "panel_outline_rgb", (194, 202, 214), instance_seed=int(instance_seed), namespace=TASK_ID),
        legend_fill_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "legend_fill_rgb", (248, 250, 252), instance_seed=int(instance_seed), namespace=TASK_ID),
        mark_outline_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "mark_outline_rgb", (50, 58, 68), instance_seed=int(instance_seed), namespace=TASK_ID),
        layout_jitter_meta=dict(jitter_meta),
    )


def _star_points(cx: float, cy: float, radius: float) -> List[Tuple[float, float]]:
    points: List[Tuple[float, float]] = []
    inner = float(radius) * 0.46
    for index in range(10):
        angle = -math.pi / 2.0 + (float(index) * math.pi / 5.0)
        r = float(radius) if index % 2 == 0 else float(inner)
        points.append((float(cx + (math.cos(angle) * r)), float(cy + (math.sin(angle) * r))))
    return points


def _draw_glyph(
    draw: ImageDraw.ImageDraw,
    *,
    glyph: str,
    bbox: Sequence[float],
    fill: RGB,
    outline: RGB,
    width: int,
) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    w = float(x1 - x0)
    h = float(y1 - y0)
    cx = float((x0 + x1) / 2.0)
    cy = float((y0 + y1) / 2.0)
    fill_rgb = tuple(int(value) for value in fill)
    outline_rgb = tuple(int(value) for value in outline)
    line_w = max(1, int(width))

    if str(glyph) == "circle" or str(glyph) == "coin":
        draw.ellipse((x0, y0, x1, y1), fill=fill_rgb, outline=outline_rgb, width=line_w)
        if str(glyph) == "coin":
            draw.arc((x0 + w * 0.22, y0 + h * 0.18, x1 - w * 0.22, y1 - h * 0.18), 70, 290, fill=outline_rgb, width=1)
    elif str(glyph) == "square":
        draw.rounded_rectangle((x0, y0, x1, y1), radius=max(2, int(min(w, h) * 0.12)), fill=fill_rgb, outline=outline_rgb, width=line_w)
    elif str(glyph) == "star":
        draw.polygon(_star_points(cx, cy, min(w, h) * 0.48), fill=fill_rgb, outline=outline_rgb)
    elif str(glyph) == "person":
        draw.ellipse((cx - w * 0.18, y0 + h * 0.03, cx + w * 0.18, y0 + h * 0.37), fill=fill_rgb, outline=outline_rgb, width=line_w)
        draw.rounded_rectangle((cx - w * 0.25, y0 + h * 0.40, cx + w * 0.25, y1 - h * 0.05), radius=max(2, int(w * 0.10)), fill=fill_rgb, outline=outline_rgb, width=line_w)
    elif str(glyph) == "car":
        draw.rounded_rectangle((x0 + w * 0.08, y0 + h * 0.34, x1 - w * 0.08, y1 - h * 0.22), radius=max(2, int(w * 0.08)), fill=fill_rgb, outline=outline_rgb, width=line_w)
        draw.polygon([(x0 + w * 0.28, y0 + h * 0.34), (x0 + w * 0.43, y0 + h * 0.16), (x0 + w * 0.68, y0 + h * 0.16), (x0 + w * 0.82, y0 + h * 0.34)], fill=fill_rgb, outline=outline_rgb)
        draw.ellipse((x0 + w * 0.20, y1 - h * 0.25, x0 + w * 0.36, y1 - h * 0.08), fill=outline_rgb)
        draw.ellipse((x1 - w * 0.36, y1 - h * 0.25, x1 - w * 0.20, y1 - h * 0.08), fill=outline_rgb)
    elif str(glyph) == "leaf":
        draw.ellipse((x0 + w * 0.08, y0 + h * 0.08, x1 - w * 0.08, y1 - h * 0.08), fill=fill_rgb, outline=outline_rgb, width=line_w)
        draw.line((x0 + w * 0.28, y1 - h * 0.22, x1 - w * 0.22, y0 + h * 0.24), fill=outline_rgb, width=max(1, line_w))
    elif str(glyph) == "book":
        draw.rounded_rectangle((x0 + w * 0.10, y0 + h * 0.06, x1 - w * 0.10, y1 - h * 0.06), radius=max(2, int(w * 0.06)), fill=fill_rgb, outline=outline_rgb, width=line_w)
        draw.line((cx, y0 + h * 0.10, cx, y1 - h * 0.10), fill=outline_rgb, width=max(1, line_w))
    else:
        draw.ellipse((x0, y0, x1, y1), fill=fill_rgb, outline=outline_rgb, width=line_w)


def _render_chart(
    *,
    background: Image.Image,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Rendered:
    render_params = _resolve_render_params(params, instance_seed=int(instance_seed))
    image = background.copy()
    draw = ImageDraw.Draw(image)
    width = int(render_params.canvas_width)
    height = int(render_params.canvas_height)
    margin = int(render_params.outer_margin_px)
    right = width - margin

    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    legend_font = load_font(int(render_params.legend_font_size_px), bold=True)
    draw_text_centered(
        draw,
        text=str(dataset.title),
        center=(float(width) / 2.0, float(margin + render_params.title_band_height_px * 0.42)),
        font=title_font,
        fill=render_params.text_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=1,
    )

    legend_x0 = float(margin)
    legend_y0 = float(margin + render_params.title_band_height_px)
    legend_x1 = float(right)
    legend_y1 = float(legend_y0 + render_params.legend_height_px)
    draw_rounded_rect(
        draw,
        (legend_x0, legend_y0, legend_x1, legend_y1),
        radius=10,
        fill=render_params.legend_fill_rgb,
        outline=render_params.panel_outline_rgb,
        width=1,
    )
    sample_size = min(30.0, float(render_params.legend_height_px) * 0.48)
    sample_box = (legend_x0 + 24.0, legend_y0 + (legend_y1 - legend_y0 - sample_size) / 2.0, legend_x0 + 24.0 + sample_size, legend_y0 + (legend_y1 - legend_y0 + sample_size) / 2.0)
    sample_color = dataset.categories[0].color_rgb if dataset.categories else (37, 99, 235)
    glyph_for_legend = "square" if str(dataset.scene_variant) == "waffle_grid_blocks" else str(dataset.glyph_name)
    _draw_glyph(draw, glyph=glyph_for_legend, bbox=sample_box, fill=sample_color, outline=render_params.mark_outline_rgb, width=2)
    legend_text = f"1 mark = {dataset.unit_scale} units"
    draw.text(
        (sample_box[2] + 16.0, legend_y0 + (legend_y1 - legend_y0) * 0.32),
        legend_text,
        font=legend_font,
        fill=render_params.text_rgb,
    )

    top = float(legend_y1 + 20.0)
    bottom = float(height - render_params.outer_margin_px)
    category_count = len(dataset.categories)
    available_h = max(1.0, bottom - top - (float(category_count - 1) * float(render_params.row_gap_px)))
    row_h = float(available_h / float(max(1, category_count)))
    plot_x0 = float(margin)
    plot_x1 = float(right)
    mark_area_x0 = float(plot_x0 + render_params.label_width_px)
    mark_area_x1 = float(plot_x1 - 18.0)
    mark_area_w = max(1.0, mark_area_x1 - mark_area_x0)
    max_marks = max(category.mark_count for category in dataset.categories)
    max_cols = max(1, int(render_params.mark_columns_max))
    planned_rows = max(1, int(math.ceil(float(max_marks) / float(max_cols))))
    mark_gap = float(render_params.mark_gap_px)
    size_from_height = (float(row_h) - 14.0 - (float(planned_rows - 1) * mark_gap)) / float(planned_rows)
    size_from_width = (float(mark_area_w) - (float(max_cols - 1) * mark_gap)) / float(max_cols)
    mark_size = max(10.0, min(float(render_params.mark_size_max_px), float(size_from_height), float(size_from_width)))
    mark_cols = max(1, min(max_cols, int((mark_area_w + mark_gap) // (mark_size + mark_gap))))

    category_bboxes: Dict[str, BBox] = {}
    mark_bboxes: Dict[str, List[BBox]] = {}
    entities: List[Dict[str, Any]] = []
    for row_index, category in enumerate(dataset.categories):
        row_y0 = float(top + (float(row_index) * (row_h + float(render_params.row_gap_px))))
        row_y1 = float(row_y0 + row_h)
        row_fill = render_params.panel_fill_rgb if row_index % 2 == 0 else (248, 250, 252)
        row_box = _bbox([plot_x0, row_y0, plot_x1, row_y1])
        draw_rounded_rect(
            draw,
            (plot_x0, row_y0, plot_x1, row_y1),
            radius=int(render_params.row_corner_radius_px),
            fill=row_fill,
            outline=render_params.panel_outline_rgb,
            width=1,
        )
        label_font = fit_font_to_box(
            draw,
            text=str(category.label),
            max_width=float(render_params.label_width_px) - 20.0,
            max_height=float(row_h) - 10.0,
            bold=True,
            min_size_px=12,
            max_size_px=int(render_params.label_font_size_px),
            fill_ratio=0.92,
        )
        draw_text_centered(
            draw,
            text=str(category.label),
            center=(float(plot_x0 + render_params.label_width_px * 0.48), float((row_y0 + row_y1) / 2.0)),
            font=label_font,
            fill=render_params.text_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )
        category_bboxes[category.category_id] = list(row_box)
        marks_for_category: List[BBox] = []
        actual_rows = max(1, int(math.ceil(float(category.mark_count) / float(mark_cols))))
        total_mark_h = (float(actual_rows) * mark_size) + (float(actual_rows - 1) * mark_gap)
        start_y = float(row_y0 + max(5.0, (row_h - total_mark_h) / 2.0))
        for mark_index in range(int(category.mark_count)):
            r = int(mark_index // mark_cols)
            c = int(mark_index % mark_cols)
            x0 = float(mark_area_x0 + float(c) * (mark_size + mark_gap))
            y0 = float(start_y + float(r) * (mark_size + mark_gap))
            box = _bbox([x0, y0, x0 + mark_size, y0 + mark_size])
            glyph = "square" if str(dataset.scene_variant) == "waffle_grid_blocks" else str(dataset.glyph_name)
            _draw_glyph(
                draw,
                glyph=str(glyph),
                bbox=box,
                fill=category.color_rgb,
                outline=render_params.mark_outline_rgb,
                width=max(1, int(render_params.panel_outline_width_px)),
            )
            marks_for_category.append(box)
        mark_bboxes[category.category_id] = marks_for_category
        entities.append(
            {
                "entity_id": str(category.category_id),
                "entity_type": "pictogram_category_row",
                "bbox_xyxy": list(row_box),
                "attrs": {
                    "label": str(category.label),
                    "mark_count": int(category.mark_count),
                    "unit_scale": int(dataset.unit_scale),
                    "total": int(category.total),
                    "color_rgb": [int(channel) for channel in category.color_rgb],
                },
            }
        )
    render_meta = {
        "scene_variant": str(dataset.scene_variant),
        "glyph_name": str(dataset.glyph_name),
        "mark_size_px": round(float(mark_size), 3),
        "mark_columns": int(mark_cols),
        "row_height_px": round(float(row_h), 3),
        "layout_jitter": dict(render_params.layout_jitter_meta),
    }
    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=_bbox([plot_x0, top, plot_x1, bottom]),
        legend_bbox_px=_bbox([legend_x0, legend_y0, legend_x1, legend_y1]),
        category_bboxes_px=category_bboxes,
        mark_bboxes_px=mark_bboxes,
        render_meta=render_meta,
    )


def _json_examples(query_variant: str, *, prompt_defaults: Mapping[str, Any]) -> Tuple[str, str]:
    return (
        str(prompt_defaults[f"json_example_{str(query_variant)}"]),
        str(prompt_defaults[f"json_example_answer_only_{str(query_variant)}"]),
    )


class ChartsPictogramChartTask:
    """Answer quantity questions from repeated marks in a pictogram/waffle chart."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "pictogram"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        public_overrides = _public_task_param_overrides(str(self.task_id)) if str(self.task_id) != TASK_ID else {}
        if public_overrides:
            merged_params = dict(public_overrides)
            merged_params.update(dict(params))
            params = merged_params

        query_variant, query_variant_probabilities = _resolve_query_variant(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        dataset = _construct_dataset(
            query_variant=str(query_variant),
            query_variant_probabilities=query_variant_probabilities,
            scene_variant=str(scene_variant),
            scene_variant_probabilities=scene_variant_probabilities,
            params=params,
            instance_seed=int(instance_seed),
        )
        background, background_meta = make_background_canvas(
            canvas_width=_render_int(params, "canvas_width", 1320),
            canvas_height=_render_int(params, "canvas_height", 900),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered = _render_chart(
            background=background,
            dataset=dataset,
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
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "evidence_hint",
                "object_description_waffle_grid_blocks",
                "object_description_pictogram_rows",
                "json_example_category_total_value",
                "json_example_group_difference_value",
                "json_example_threshold_count",
                "json_example_answer_only_category_total_value",
                "json_example_answer_only_group_difference_value",
                "json_example_answer_only_threshold_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _json_examples(str(query_variant), prompt_defaults=prompt_defaults)
        qparams = dict(dataset.query.params)
        category_by_id = {category.category_id: category for category in dataset.categories}
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "unit_scale": int(dataset.unit_scale),
                "category_label": str(qparams.get("target_category_label", "")),
                "category_label_a": str(qparams.get("category_label_a", "")),
                "category_label_b": str(qparams.get("category_label_b", "")),
                "threshold_phrase": str(qparams.get("threshold_phrase", "")),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_category_ids = [str(value) for value in dataset.query.evidence_category_ids]
        evidence_bboxes = [list(rendered.category_bboxes_px[str(category_id)]) for category_id in evidence_category_ids]
        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=int(dataset.query.answer))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        totals_by_category = {category.label: int(category.total) for category in dataset.categories}
        mark_counts_by_category = {category.label: int(category.mark_count) for category in dataset.categories}
        category_id_to_label = {category.category_id: str(category.label) for category in dataset.categories}
        evidence_labels = [str(category_id_to_label[category_id]) for category_id in evidence_category_ids]

        visual_scan = clamp_unit_interval(
            0.55 * normalize_int_with_bounds(len(dataset.categories), [6, 10])
            + 0.45 * normalize_int_with_bounds(max(category.mark_count for category in dataset.categories), [4, 16])
        )
        evidence_scan = normalize_int_with_bounds(len(evidence_category_ids), [1, 6])
        reasoning_load = clamp_unit_interval(float(_REASONING_LOAD_BY_VARIANT[str(query_variant)]) + (0.08 * evidence_scan))
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
            },
        )

        query_params = {
            "query_variant": str(query_variant),
            "query_variant": str(query_variant),
            "query_id": str(query_variant),
            "query_variant_probabilities": dict(dataset.query_variant_probabilities),
            "query_variant_probabilities": dict(dataset.query_variant_probabilities),
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(dataset.scene_variant_probabilities),
            "glyph_name": str(dataset.glyph_name),
            "glyph_probabilities": dict(dataset.glyph_probabilities),
            "unit_scale": int(dataset.unit_scale),
            "category_count": int(len(dataset.categories)),
            "answer_value": int(dataset.query.answer),
            **dict(qparams),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_variant": str(query_variant),
                    "query_variant": str(query_variant),
                    "query_id": str(query_variant),
                    "scene_variant": str(scene_variant),
                    "unit_scale": int(dataset.unit_scale),
                    "answer_value": int(dataset.query.answer),
                    "evidence_category_ids": list(evidence_category_ids),
                },
            },
            "query_spec": {
                "query_variant": str(query_variant),
                "query_variant": str(query_variant),
                "query_id": str(query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_variant": str(scene_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "unit_scale": int(dataset.unit_scale),
                "glyph_name": str(dataset.glyph_name),
                "category_labels": [str(category.label) for category in dataset.categories],
                "render_meta": dict(rendered.render_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "legend_bbox_px": list(rendered.legend_bbox_px),
                "category_bboxes_px": dict(rendered.category_bboxes_px),
                "mark_bboxes_px": dict(rendered.mark_bboxes_px),
            },
            "execution_trace": {
                "query_variant": str(query_variant),
                "query_variant": str(query_variant),
                "query_id": str(query_variant),
                "question_format": "pictogram_quantity",
                "scene_variant": str(scene_variant),
                "unit_scale": int(dataset.unit_scale),
                "category_count": int(len(dataset.categories)),
                "categories": [str(category.label) for category in dataset.categories],
                "category_id_to_label": dict(category_id_to_label),
                "mark_counts_by_category": dict(mark_counts_by_category),
                "totals_by_category": dict(totals_by_category),
                "answer_value": int(dataset.query.answer),
                "answer_type": str(dataset.query.answer_type),
                "evidence_category_ids": list(evidence_category_ids),
                "evidence_labels": list(evidence_labels),
                **dict(qparams),
            },
            "witness_symbolic": {
                "type": "pictogram_quantity_witness",
                "answer_value": int(dataset.query.answer),
                "evidence_category_ids": list(evidence_category_ids),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
                "bbox_map": {str(category_id): list(rendered.category_bboxes_px[str(category_id)]) for category_id in evidence_category_ids},
                "category_ids": list(evidence_category_ids),
                "category_labels": list(evidence_labels),
            },
            "background": dict(background_meta),
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
            scene_id=SCENE_ID,
            query_id=str(query_variant),
        )


@register_task
class ChartsPictogramCategoryTotalValueTask(FixedChartQueryVariantTaskMixin, ChartsPictogramChartTask):
    """Read one category total from the repeated unit marks."""

    task_id = "task_charts__pictogram__category_total_value"
    fixed_query_variant = "category_total_value"


@register_task
class ChartsPictogramGroupDifferenceValueTask(FixedChartQueryVariantTaskMixin, ChartsPictogramChartTask):
    """Compute the absolute difference between two pictogram category totals."""

    task_id = "task_charts__pictogram__group_difference_value"
    fixed_query_variant = "group_difference_value"


@register_task
class ChartsPictogramThresholdCountTask(FixedChartQueryVariantTaskMixin, ChartsPictogramChartTask):
    """Count categories whose repeated-mark total satisfies a threshold."""

    task_id = "task_charts__pictogram__threshold_count"
    fixed_query_variant = "threshold_count"


__all__ = [
    "ChartsPictogramCategoryTotalValueTask",
    "ChartsPictogramChartTask",
    "ChartsPictogramGroupDifferenceValueTask",
    "ChartsPictogramThresholdCountTask",
    "SUPPORTED_GLYPHS",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_VARIANTS",
    "SUPPORTED_THRESHOLD_DIRECTIONS",
]
