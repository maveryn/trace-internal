"""Error-bar and confidence-interval chart tasks."""

from __future__ import annotations

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
from ...shared.drawing import draw_centered_text, draw_dashed_line, draw_rounded_rect
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import resolve_render_rgb
from ...shared.text_rendering import load_font
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_error_interval_base"
SCENE_ID = "error_interval"

REFERENCE_COUNT_QUERY_VARIANTS: Tuple[str, ...] = (
    "contains_reference_count",
    "entirely_above_reference_count",
    "entirely_below_reference_count",
)
RELATION_LABEL_QUERY_VARIANTS: Tuple[str, ...] = (
    "widest_interval_label",
    "narrowest_interval_label",
    "second_widest_interval_label",
    "second_narrowest_interval_label",
)
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = REFERENCE_COUNT_QUERY_VARIANTS + RELATION_LABEL_QUERY_VARIANTS
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "horizontal_forest",
    "vertical_dot_whisker",
    "bar_with_error",
)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "error_interval")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="error_interval")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="error_interval", apply_prob=0.5)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)

_QUERY_LOADS: Dict[str, float] = {
    "contains_reference_count": 0.54,
    "entirely_above_reference_count": 0.58,
    "entirely_below_reference_count": 0.58,
    "widest_interval_label": 0.56,
    "narrowest_interval_label": 0.56,
    "second_widest_interval_label": 0.70,
    "second_narrowest_interval_label": 0.70,
}
_SCENE_LOADS: Dict[str, float] = {
    "horizontal_forest": 0.44,
    "vertical_dot_whisker": 0.56,
    "bar_with_error": 0.62,
}

_LABEL_POOL: Tuple[str, ...] = (
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
)

RGB = Tuple[int, int, int]
BBox = List[float]


@dataclass(frozen=True)
class _IntervalItem:
    item_id: str
    label: str
    lower: int
    midpoint: int
    upper: int
    color_rgb: RGB


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer: int | str
    answer_type: str
    evidence_item_ids: Tuple[str, ...]
    params: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    items: Tuple[_IntervalItem, ...]
    query_id: str
    query_probabilities: Dict[str, float]
    scene_variant: str
    scene_variant_probabilities: Dict[str, float]
    reference_value: int | None
    title: str
    query: _Query


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    title_band_height_px: int
    label_band_px: int
    plot_padding_px: int
    panel_corner_radius_px: int
    panel_outline_width_px: int
    axis_line_width_px: int
    grid_line_width_px: int
    interval_line_width_px: int
    cap_length_px: int
    point_radius_px: int
    bar_width_fraction: float
    title_font_size_px: int
    label_font_size_px: int
    tick_font_size_px: int
    value_font_size_px: int
    axis_min: int
    axis_max: int
    tick_step: int
    text_rgb: RGB
    muted_text_rgb: RGB
    text_stroke_rgb: RGB
    panel_fill_rgb: RGB
    panel_outline_rgb: RGB
    axis_rgb: RGB
    grid_rgb: RGB
    reference_rgb: RGB
    interval_outline_rgb: RGB


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: BBox
    item_bboxes_px: Dict[str, BBox]
    interval_bboxes_px: Dict[str, BBox]
    render_meta: Dict[str, Any]


def _bbox(values: Sequence[float]) -> BBox:
    return [round(float(value), 3) for value in values]


def _support_probability_map(values: Sequence[int | str]) -> Dict[str, float]:
    support = [str(value) for value in values]
    if not support:
        return {}
    weight = 1.0 / float(len(support))
    return {str(value): float(weight) for value in support}


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


def _sample_int_range(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    instance_seed: int,
    namespace: str,
) -> Tuple[int, Dict[str, float]]:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=f"generation defaults for {TASK_ID}",
    )
    support = list(range(int(low), int(high) + 1))
    index = abs(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)))
    return int(support[int(index % len(support))]), _support_probability_map(support)


def _choose_labels(*, count: int, instance_seed: int) -> List[str]:
    rng = spawn_rng(int(instance_seed), "charts.error_interval.labels")
    labels = list(_LABEL_POOL)
    rng.shuffle(labels)
    return labels[: int(count)]


def _palette(params: Mapping[str, Any], *, count: int, instance_seed: int) -> List[RGB]:
    raw_palette = params.get("interval_palette_rgb", group_default(_RENDER_DEFAULTS, "interval_palette_rgb", []))
    palette: List[RGB] = []
    if isinstance(raw_palette, Sequence):
        for raw in raw_palette:
            if isinstance(raw, Sequence) and len(raw) == 3:
                palette.append(tuple(int(channel) for channel in raw))
    if not palette:
        palette = [
            (37, 99, 235),
            (220, 84, 45),
            (16, 132, 96),
            (139, 92, 246),
            (202, 138, 4),
            (14, 116, 144),
            (190, 58, 90),
        ]
    offset = abs(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace="charts.error_interval.palette")) % len(palette)
    return [palette[(index + int(offset)) % len(palette)] for index in range(int(count))]


def _clamp_interval(lower: int, midpoint: int, upper: int) -> Tuple[int, int, int]:
    lower = max(0, min(100, int(lower)))
    upper = max(0, min(100, int(upper)))
    if int(lower) > int(upper):
        lower, upper = upper, lower
    midpoint = max(int(lower), min(int(upper), int(midpoint)))
    return int(lower), int(midpoint), int(upper)


def _interval_around(midpoint: int, width: int) -> Tuple[int, int, int]:
    width = max(2, int(width))
    half_low = int(width // 2)
    lower = int(midpoint) - int(half_low)
    upper = int(lower) + int(width)
    if lower < 0:
        upper -= lower
        lower = 0
    if upper > 100:
        lower -= int(upper) - 100
        upper = 100
    midpoint = int(round((int(lower) + int(upper)) / 2.0))
    return _clamp_interval(int(lower), int(midpoint), int(upper))


def _construct_reference_intervals(
    *,
    query_id: str,
    category_count: int,
    answer_count: int,
    labels: Sequence[str],
    colors: Sequence[RGB],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_IntervalItem, ...], int, Tuple[str, ...], Dict[str, Any]]:
    rng = spawn_rng(int(instance_seed), f"charts.error_interval.reference.{query_id}")
    ref_min, ref_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="reference_value_min",
        max_key="reference_value_max",
        fallback_min=38,
        fallback_max=62,
        context=f"generation defaults for {TASK_ID}",
    )
    reference_value = int(ref_min) + int(abs(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"charts.error_interval.reference_value.{query_id}")) % (int(ref_max) - int(ref_min) + 1))
    target_indices = set(rng.sample(range(int(category_count)), k=int(answer_count)))

    items: List[_IntervalItem] = []
    evidence_ids: List[str] = []
    for index in range(int(category_count)):
        item_id = f"i{index}"
        is_target = int(index) in target_indices
        if query_id == "contains_reference_count":
            if is_target:
                half_width = int(rng.randint(6, 15))
                mid = int(reference_value + rng.randint(-3, 3))
                lower = min(int(reference_value), int(mid - half_width))
                upper = max(int(reference_value), int(mid + half_width))
                evidence_ids.append(item_id)
            elif (index + int(reference_value)) % 2 == 0:
                upper = int(reference_value) - int(rng.randint(3, 13))
                width = int(rng.randint(8, 18))
                lower = int(upper) - int(width)
                mid = int(round((int(lower) + int(upper)) / 2.0))
            else:
                lower = int(reference_value) + int(rng.randint(3, 13))
                width = int(rng.randint(8, 18))
                upper = int(lower) + int(width)
                mid = int(round((int(lower) + int(upper)) / 2.0))
        elif query_id == "entirely_above_reference_count":
            if is_target:
                lower = int(reference_value) + int(rng.randint(3, 13))
                width = int(rng.randint(8, 18))
                upper = int(lower) + int(width)
                mid = int(round((int(lower) + int(upper)) / 2.0))
                evidence_ids.append(item_id)
            elif (index + int(reference_value)) % 2 == 0:
                half_width = int(rng.randint(6, 14))
                mid = int(reference_value + rng.randint(-2, 2))
                lower = min(int(reference_value), int(mid - half_width))
                upper = max(int(reference_value), int(mid + half_width))
            else:
                upper = int(reference_value) - int(rng.randint(3, 11))
                width = int(rng.randint(8, 16))
                lower = int(upper) - int(width)
                mid = int(round((int(lower) + int(upper)) / 2.0))
        elif query_id == "entirely_below_reference_count":
            if is_target:
                upper = int(reference_value) - int(rng.randint(3, 13))
                width = int(rng.randint(8, 18))
                lower = int(upper) - int(width)
                mid = int(round((int(lower) + int(upper)) / 2.0))
                evidence_ids.append(item_id)
            elif (index + int(reference_value)) % 2 == 0:
                half_width = int(rng.randint(6, 14))
                mid = int(reference_value + rng.randint(-2, 2))
                lower = min(int(reference_value), int(mid - half_width))
                upper = max(int(reference_value), int(mid + half_width))
            else:
                lower = int(reference_value) + int(rng.randint(3, 11))
                width = int(rng.randint(8, 16))
                upper = int(lower) + int(width)
                mid = int(round((int(lower) + int(upper)) / 2.0))
        else:
            raise ValueError(f"unsupported reference query: {query_id}")

        lower, mid, upper = _clamp_interval(int(lower), int(mid), int(upper))
        items.append(
            _IntervalItem(
                item_id=item_id,
                label=str(labels[index]),
                lower=int(lower),
                midpoint=int(mid),
                upper=int(upper),
                color_rgb=tuple(int(v) for v in colors[index]),
            )
        )
    return tuple(items), int(reference_value), tuple(evidence_ids), {
        "answer_count": int(answer_count),
        "answer_count_probabilities": _support_probability_map(range(1, 6)),
    }


def _construct_relation_intervals(
    *,
    query_id: str,
    category_count: int,
    labels: Sequence[str],
    colors: Sequence[RGB],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_IntervalItem, ...], Tuple[str, ...], str, Dict[str, Any]]:
    rng = spawn_rng(int(instance_seed), f"charts.error_interval.relation.{query_id}")
    winner_index = abs(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"charts.error_interval.winner.{query_id}")) % int(category_count)
    width_low = int(rng.randint(6, 13))
    width_high = min(34, int(width_low) + int(rng.randint(int(category_count) + 5, int(category_count) + 10)))
    width_pool = list(range(int(width_low), int(width_high) + 1))
    rng.shuffle(width_pool)
    widths_sorted = sorted(width_pool[: int(category_count)])
    if query_id == "widest_interval_label":
        winner_width = int(widths_sorted[-1])
    elif query_id == "narrowest_interval_label":
        winner_width = int(widths_sorted[0])
    elif query_id == "second_widest_interval_label":
        winner_width = int(widths_sorted[-2])
    elif query_id == "second_narrowest_interval_label":
        winner_width = int(widths_sorted[1])
    else:
        raise ValueError(f"unsupported relation query: {query_id}")
    remaining_widths = [int(width) for width in widths_sorted if int(width) != int(winner_width)]
    rng.shuffle(remaining_widths)
    items: List[_IntervalItem] = []

    for index in range(int(category_count)):
        width = int(winner_width) if int(index) == int(winner_index) else int(remaining_widths.pop())
        midpoint = int(rng.randint(25, 75))
        lower, mid, upper = _interval_around(int(midpoint), int(width))
        items.append(
            _IntervalItem(
                item_id=f"i{index}",
                label=str(labels[index]),
                lower=int(lower),
                midpoint=int(mid),
                upper=int(upper),
                color_rgb=tuple(int(v) for v in colors[index]),
            )
        )
    winner_id = f"i{winner_index}"
    return tuple(items), (winner_id,), str(labels[int(winner_index)]), {
        "winner_index": int(winner_index),
        "winner_label": str(labels[int(winner_index)]),
        "winner_width": int(winner_width),
        "width_support": [int(width) for width in widths_sorted],
    }


def _construct_dataset(
    *,
    query_id: str,
    query_probabilities: Dict[str, float],
    scene_variant: str,
    scene_variant_probabilities: Dict[str, float],
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Dataset:
    category_count, category_count_probabilities = _sample_int_range(
        params,
        min_key="category_count_min",
        max_key="category_count_max",
        fallback_min=6,
        fallback_max=10,
        instance_seed=int(instance_seed),
        namespace="charts.error_interval.category_count",
    )
    labels = _choose_labels(count=int(category_count), instance_seed=int(instance_seed))
    colors = _palette(params, count=int(category_count), instance_seed=int(instance_seed))
    title_options = [str(value) for value in params.get("title_options", group_default(_RENDER_DEFAULTS, "title_options", ["Estimate Intervals"]))] or ["Estimate Intervals"]
    title_index = abs(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace="charts.error_interval.title")) % len(title_options)

    if str(query_id) in REFERENCE_COUNT_QUERY_VARIANTS:
        answer_count, answer_count_probs = _sample_int_range(
            params,
            min_key="reference_answer_count_min",
            max_key="reference_answer_count_max",
            fallback_min=1,
            fallback_max=5,
            instance_seed=int(instance_seed),
            namespace=f"charts.error_interval.answer_count.{query_id}",
        )
        items, reference_value, evidence_item_ids, extra = _construct_reference_intervals(
            query_id=str(query_id),
            category_count=int(category_count),
            answer_count=int(answer_count),
            labels=labels,
            colors=colors,
            params=params,
            instance_seed=int(instance_seed),
        )
        query = _Query(
            query_id=str(query_id),
            answer=int(answer_count),
            answer_type="integer",
            evidence_item_ids=tuple(evidence_item_ids),
            params={
                "reference_value": int(reference_value),
                "answer_count_probabilities": dict(answer_count_probs),
                **dict(extra),
            },
        )
    else:
        items, evidence_item_ids, answer_label, extra = _construct_relation_intervals(
            query_id=str(query_id),
            category_count=int(category_count),
            labels=labels,
            colors=colors,
            params=params,
            instance_seed=int(instance_seed),
        )
        query = _Query(
            query_id=str(query_id),
            answer=str(answer_label),
            answer_type="string",
            evidence_item_ids=tuple(evidence_item_ids),
            params=dict(extra),
        )
        reference_value = None

    return _Dataset(
        items=tuple(items),
        query_id=str(query_id),
        query_probabilities=dict(query_probabilities),
        scene_variant=str(scene_variant),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        reference_value=reference_value,
        title=str(title_options[int(title_index)]),
        query=query,
    )


def _render_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_RENDER_DEFAULTS, str(key), int(fallback))))


def _render_float(params: Mapping[str, Any], key: str, fallback: float) -> float:
    return float(params.get(str(key), group_default(_RENDER_DEFAULTS, str(key), float(fallback))))


def _resolve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    return _RenderParams(
        canvas_width=_render_int(params, "canvas_width", 1320),
        canvas_height=_render_int(params, "canvas_height", 900),
        outer_margin_px=_render_int(params, "outer_margin_px", 54),
        title_band_height_px=_render_int(params, "title_band_height_px", 72),
        label_band_px=_render_int(params, "label_band_px", 154),
        plot_padding_px=_render_int(params, "plot_padding_px", 32),
        panel_corner_radius_px=_render_int(params, "panel_corner_radius_px", 10),
        panel_outline_width_px=_render_int(params, "panel_outline_width_px", 2),
        axis_line_width_px=_render_int(params, "axis_line_width_px", 2),
        grid_line_width_px=_render_int(params, "grid_line_width_px", 1),
        interval_line_width_px=_render_int(params, "interval_line_width_px", 5),
        cap_length_px=_render_int(params, "cap_length_px", 20),
        point_radius_px=_render_int(params, "point_radius_px", 7),
        bar_width_fraction=_render_float(params, "bar_width_fraction", 0.58),
        title_font_size_px=_render_int(params, "title_font_size_px", 30),
        label_font_size_px=_render_int(params, "label_font_size_px", 20),
        tick_font_size_px=_render_int(params, "tick_font_size_px", 17),
        value_font_size_px=_render_int(params, "value_font_size_px", 15),
        axis_min=_render_int(params, "axis_min", 0),
        axis_max=_render_int(params, "axis_max", 100),
        tick_step=max(1, _render_int(params, "tick_step", 20)),
        text_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_rgb", [38, 41, 48], instance_seed=int(instance_seed), namespace="charts.error_interval"),
        muted_text_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "muted_text_rgb", [88, 96, 112], instance_seed=int(instance_seed), namespace="charts.error_interval"),
        text_stroke_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_stroke_rgb", [255, 255, 255], instance_seed=int(instance_seed), namespace="charts.error_interval"),
        panel_fill_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "panel_fill_rgb", [255, 255, 255], instance_seed=int(instance_seed), namespace="charts.error_interval"),
        panel_outline_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "panel_outline_rgb", [194, 202, 214], instance_seed=int(instance_seed), namespace="charts.error_interval"),
        axis_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "axis_rgb", [64, 68, 76], instance_seed=int(instance_seed), namespace="charts.error_interval"),
        grid_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "grid_rgb", [224, 227, 232], instance_seed=int(instance_seed), namespace="charts.error_interval"),
        reference_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "reference_rgb", [76, 84, 94], instance_seed=int(instance_seed), namespace="charts.error_interval"),
        interval_outline_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "interval_outline_rgb", [34, 40, 48], instance_seed=int(instance_seed), namespace="charts.error_interval"),
    )


def _draw_text(
    draw: ImageDraw.ImageDraw,
    *,
    xy: Tuple[float, float],
    text: str,
    font,
    fill: RGB,
    stroke_fill: RGB,
    stroke_width: int = 1,
    anchor: str = "la",
) -> BBox:
    try:
        draw.text(
            (float(xy[0]), float(xy[1])),
            str(text),
            font=font,
            fill=tuple(fill),
            stroke_width=max(0, int(stroke_width)),
            stroke_fill=tuple(stroke_fill),
            anchor=str(anchor),
        )
        bbox = draw.textbbox(
            (float(xy[0]), float(xy[1])),
            str(text),
            font=font,
            stroke_width=max(0, int(stroke_width)),
            anchor=str(anchor),
        )
        return _bbox(bbox)
    except Exception:
        draw.text(
            (float(xy[0]), float(xy[1])),
            str(text),
            font=font,
            fill=tuple(fill),
            stroke_width=max(0, int(stroke_width)),
            stroke_fill=tuple(stroke_fill),
        )
        bbox = draw.textbbox((float(xy[0]), float(xy[1])), str(text), font=font, stroke_width=max(0, int(stroke_width)))
        return _bbox(bbox)


def _draw_axis_ticks_horizontal(
    draw: ImageDraw.ImageDraw,
    *,
    p: _RenderParams,
    plot_bbox: Sequence[float],
) -> None:
    left, top, right, bottom = [float(value) for value in plot_bbox]
    tick_font = load_font(p.tick_font_size_px, bold=False)

    def x_for(value: int) -> float:
        return float(left + ((int(value) - p.axis_min) / max(1, p.axis_max - p.axis_min)) * (right - left))

    for tick in range(int(p.axis_min), int(p.axis_max) + 1, int(p.tick_step)):
        x = x_for(int(tick))
        draw.line([(x, top), (x, bottom)], fill=tuple(p.grid_rgb), width=int(p.grid_line_width_px))
        draw.line([(x, bottom), (x, bottom + 7)], fill=tuple(p.axis_rgb), width=int(p.axis_line_width_px))
        _draw_text(draw, xy=(x, bottom + 12), text=str(tick), font=tick_font, fill=p.muted_text_rgb, stroke_fill=p.text_stroke_rgb, anchor="mt")
    draw.line([(left, bottom), (right, bottom)], fill=tuple(p.axis_rgb), width=int(p.axis_line_width_px))


def _draw_axis_ticks_vertical(
    draw: ImageDraw.ImageDraw,
    *,
    p: _RenderParams,
    plot_bbox: Sequence[float],
) -> None:
    left, top, right, bottom = [float(value) for value in plot_bbox]
    tick_font = load_font(p.tick_font_size_px, bold=False)

    def y_for(value: int) -> float:
        return float(bottom - ((int(value) - p.axis_min) / max(1, p.axis_max - p.axis_min)) * (bottom - top))

    for tick in range(int(p.axis_min), int(p.axis_max) + 1, int(p.tick_step)):
        y = y_for(int(tick))
        draw.line([(left, y), (right, y)], fill=tuple(p.grid_rgb), width=int(p.grid_line_width_px))
        draw.line([(left - 7, y), (left, y)], fill=tuple(p.axis_rgb), width=int(p.axis_line_width_px))
        _draw_text(draw, xy=(left - 12, y), text=str(tick), font=tick_font, fill=p.muted_text_rgb, stroke_fill=p.text_stroke_rgb, anchor="rm")
    draw.line([(left, top), (left, bottom)], fill=tuple(p.axis_rgb), width=int(p.axis_line_width_px))
    draw.line([(left, bottom), (right, bottom)], fill=tuple(p.axis_rgb), width=int(p.axis_line_width_px))


def _render_horizontal_forest(
    *,
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    dataset: _Dataset,
    p: _RenderParams,
    panel_bbox: Sequence[float],
) -> Tuple[BBox, Dict[str, BBox], Dict[str, BBox], List[Dict[str, Any]]]:
    left, top, right, bottom = [float(value) for value in panel_bbox]
    plot_left = left + p.label_band_px
    plot_right = right - p.plot_padding_px
    plot_top = top + p.title_band_height_px + 10
    plot_bottom = bottom - 54
    plot_bbox = _bbox([plot_left, plot_top, plot_right, plot_bottom])
    _draw_axis_ticks_horizontal(draw, p=p, plot_bbox=plot_bbox)

    def x_for(value: int) -> float:
        return float(plot_left + ((int(value) - p.axis_min) / max(1, p.axis_max - p.axis_min)) * (plot_right - plot_left))

    if dataset.reference_value is not None:
        ref_x = x_for(int(dataset.reference_value))
        draw_dashed_line(
            draw,
            start=(ref_x, plot_top),
            end=(ref_x, plot_bottom),
            fill=p.reference_rgb,
            width=2,
            dash_px=10,
            gap_px=7,
        )
        ref_font = load_font(p.tick_font_size_px, bold=True)
        _draw_text(draw, xy=(ref_x + 6, plot_top - 8), text=f"ref {dataset.reference_value}", font=ref_font, fill=p.reference_rgb, stroke_fill=p.text_stroke_rgb, anchor="lb")

    row_h = float((plot_bottom - plot_top) / max(1, len(dataset.items)))
    label_font = load_font(p.label_font_size_px, bold=True)
    value_font = load_font(p.value_font_size_px, bold=False)
    item_bboxes: Dict[str, BBox] = {}
    interval_bboxes: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []

    for index, item in enumerate(dataset.items):
        y = float(plot_top + (index + 0.5) * row_h)
        row_top = float(plot_top + index * row_h + 4)
        row_bottom = float(plot_top + (index + 1) * row_h - 4)
        if index % 2 == 0:
            draw.rounded_rectangle(
                (left + 12, row_top, right - 12, row_bottom),
                radius=8,
                fill=(248, 250, 252),
                outline=None,
            )
        _draw_text(draw, xy=(left + 26, y), text=item.label, font=label_font, fill=p.text_rgb, stroke_fill=p.text_stroke_rgb, anchor="lm")
        x0 = x_for(item.lower)
        xm = x_for(item.midpoint)
        x1 = x_for(item.upper)
        cap = float(p.cap_length_px) * 0.5
        draw.line([(x0, y), (x1, y)], fill=tuple(p.interval_outline_rgb), width=int(p.interval_line_width_px + 2))
        draw.line([(x0, y), (x1, y)], fill=tuple(item.color_rgb), width=int(p.interval_line_width_px))
        draw.line([(x0, y - cap), (x0, y + cap)], fill=tuple(p.interval_outline_rgb), width=2)
        draw.line([(x1, y - cap), (x1, y + cap)], fill=tuple(p.interval_outline_rgb), width=2)
        r = float(p.point_radius_px)
        draw.ellipse((xm - r, y - r, xm + r, y + r), fill=tuple(item.color_rgb), outline=tuple(p.interval_outline_rgb), width=2)
        _draw_text(draw, xy=(x0, y - cap - 3), text=str(item.lower), font=value_font, fill=p.text_rgb, stroke_fill=p.text_stroke_rgb, anchor="mb")
        _draw_text(draw, xy=(x1, y + cap + 3), text=str(item.upper), font=value_font, fill=p.text_rgb, stroke_fill=p.text_stroke_rgb, anchor="mt")
        interval_bbox = _bbox([min(x0, x1) - 20, y - cap - 20, max(x0, x1) + 20, y + cap + 20])
        item_bbox = _bbox([left + 12, row_top, right - 12, row_bottom])
        interval_bboxes[item.item_id] = interval_bbox
        item_bboxes[item.item_id] = item_bbox
        entities.append(_entity_record(item, interval_bbox=interval_bbox, item_bbox=item_bbox))
    if dataset.reference_value is not None:
        ref_x = x_for(int(dataset.reference_value))
        draw_dashed_line(
            draw,
            start=(ref_x, plot_top),
            end=(ref_x, plot_bottom),
            fill=p.reference_rgb,
            width=2,
            dash_px=10,
            gap_px=7,
        )
    return plot_bbox, item_bboxes, interval_bboxes, entities


def _render_vertical_dot_whisker(
    *,
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    dataset: _Dataset,
    p: _RenderParams,
    panel_bbox: Sequence[float],
) -> Tuple[BBox, Dict[str, BBox], Dict[str, BBox], List[Dict[str, Any]]]:
    del image
    left, top, right, bottom = [float(value) for value in panel_bbox]
    plot_left = left + 82
    plot_right = right - 42
    plot_top = top + p.title_band_height_px + 10
    plot_bottom = bottom - 92
    plot_bbox = _bbox([plot_left, plot_top, plot_right, plot_bottom])
    _draw_axis_ticks_vertical(draw, p=p, plot_bbox=plot_bbox)

    def y_for(value: int) -> float:
        return float(plot_bottom - ((int(value) - p.axis_min) / max(1, p.axis_max - p.axis_min)) * (plot_bottom - plot_top))

    if dataset.reference_value is not None:
        ref_y = y_for(int(dataset.reference_value))
        draw_dashed_line(draw, start=(plot_left, ref_y), end=(plot_right, ref_y), fill=p.reference_rgb, width=2, dash_px=11, gap_px=7)
        ref_font = load_font(p.tick_font_size_px, bold=True)
        _draw_text(draw, xy=(plot_right - 4, ref_y - 5), text=f"ref {dataset.reference_value}", font=ref_font, fill=p.reference_rgb, stroke_fill=p.text_stroke_rgb, anchor="rb")

    slot_w = float((plot_right - plot_left) / max(1, len(dataset.items)))
    label_font = load_font(p.label_font_size_px, bold=True)
    value_font = load_font(p.value_font_size_px, bold=False)
    item_bboxes: Dict[str, BBox] = {}
    interval_bboxes: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []

    for index, item in enumerate(dataset.items):
        x = float(plot_left + (index + 0.5) * slot_w)
        y0 = y_for(item.lower)
        ym = y_for(item.midpoint)
        y1 = y_for(item.upper)
        cap = min(float(p.cap_length_px), slot_w * 0.34)
        draw.line([(x, min(y0, y1)), (x, max(y0, y1))], fill=tuple(p.interval_outline_rgb), width=int(p.interval_line_width_px + 2))
        draw.line([(x, min(y0, y1)), (x, max(y0, y1))], fill=tuple(item.color_rgb), width=int(p.interval_line_width_px))
        draw.line([(x - cap, y0), (x + cap, y0)], fill=tuple(p.interval_outline_rgb), width=2)
        draw.line([(x - cap, y1), (x + cap, y1)], fill=tuple(p.interval_outline_rgb), width=2)
        r = float(p.point_radius_px)
        draw.ellipse((x - r, ym - r, x + r, ym + r), fill=tuple(item.color_rgb), outline=tuple(p.interval_outline_rgb), width=2)
        _draw_text(draw, xy=(x - cap - 3, y0), text=str(item.lower), font=value_font, fill=p.text_rgb, stroke_fill=p.text_stroke_rgb, anchor="rm")
        _draw_text(draw, xy=(x + cap + 3, y1), text=str(item.upper), font=value_font, fill=p.text_rgb, stroke_fill=p.text_stroke_rgb, anchor="lm")
        _draw_text(draw, xy=(x, plot_bottom + 19), text=item.label, font=label_font, fill=p.text_rgb, stroke_fill=p.text_stroke_rgb, anchor="mt")
        interval_bbox = _bbox([x - cap - 28, min(y0, y1) - 14, x + cap + 28, max(y0, y1) + 14])
        item_bbox = _bbox([x - slot_w * 0.45, plot_top, x + slot_w * 0.45, plot_bottom + 48])
        interval_bboxes[item.item_id] = interval_bbox
        item_bboxes[item.item_id] = item_bbox
        entities.append(_entity_record(item, interval_bbox=interval_bbox, item_bbox=item_bbox))
    return plot_bbox, item_bboxes, interval_bboxes, entities


def _render_bar_with_error(
    *,
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    dataset: _Dataset,
    p: _RenderParams,
    panel_bbox: Sequence[float],
) -> Tuple[BBox, Dict[str, BBox], Dict[str, BBox], List[Dict[str, Any]]]:
    del image
    left, top, right, bottom = [float(value) for value in panel_bbox]
    plot_left = left + 82
    plot_right = right - 42
    plot_top = top + p.title_band_height_px + 10
    plot_bottom = bottom - 92
    plot_bbox = _bbox([plot_left, plot_top, plot_right, plot_bottom])
    _draw_axis_ticks_vertical(draw, p=p, plot_bbox=plot_bbox)

    def y_for(value: int) -> float:
        return float(plot_bottom - ((int(value) - p.axis_min) / max(1, p.axis_max - p.axis_min)) * (plot_bottom - plot_top))

    if dataset.reference_value is not None:
        ref_y = y_for(int(dataset.reference_value))
        draw_dashed_line(draw, start=(plot_left, ref_y), end=(plot_right, ref_y), fill=p.reference_rgb, width=2, dash_px=11, gap_px=7)
        ref_font = load_font(p.tick_font_size_px, bold=True)
        _draw_text(draw, xy=(plot_right - 4, ref_y - 5), text=f"ref {dataset.reference_value}", font=ref_font, fill=p.reference_rgb, stroke_fill=p.text_stroke_rgb, anchor="rb")

    slot_w = float((plot_right - plot_left) / max(1, len(dataset.items)))
    bar_w = max(18.0, float(slot_w) * float(p.bar_width_fraction))
    label_font = load_font(p.label_font_size_px, bold=True)
    value_font = load_font(p.value_font_size_px, bold=False)
    item_bboxes: Dict[str, BBox] = {}
    interval_bboxes: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []

    for index, item in enumerate(dataset.items):
        x = float(plot_left + (index + 0.5) * slot_w)
        y_lower = y_for(item.lower)
        y_mid = y_for(item.midpoint)
        y_upper = y_for(item.upper)
        baseline_y = y_for(0)
        bar_bbox = (x - bar_w * 0.5, min(y_mid, baseline_y), x + bar_w * 0.5, max(y_mid, baseline_y))
        draw.rounded_rectangle(bar_bbox, radius=5, fill=tuple(item.color_rgb), outline=tuple(p.interval_outline_rgb), width=2)
        cap = min(float(p.cap_length_px), slot_w * 0.36)
        draw.line([(x, min(y_lower, y_upper)), (x, max(y_lower, y_upper))], fill=tuple(p.interval_outline_rgb), width=int(p.interval_line_width_px))
        draw.line([(x - cap, y_lower), (x + cap, y_lower)], fill=tuple(p.interval_outline_rgb), width=2)
        draw.line([(x - cap, y_upper), (x + cap, y_upper)], fill=tuple(p.interval_outline_rgb), width=2)
        draw.ellipse((x - 4, y_mid - 4, x + 4, y_mid + 4), fill=tuple(p.text_stroke_rgb), outline=tuple(p.interval_outline_rgb), width=1)
        _draw_text(draw, xy=(x - cap - 3, y_lower), text=str(item.lower), font=value_font, fill=p.text_rgb, stroke_fill=p.text_stroke_rgb, anchor="rm")
        _draw_text(draw, xy=(x + cap + 3, y_upper), text=str(item.upper), font=value_font, fill=p.text_rgb, stroke_fill=p.text_stroke_rgb, anchor="lm")
        _draw_text(draw, xy=(x, plot_bottom + 19), text=item.label, font=label_font, fill=p.text_rgb, stroke_fill=p.text_stroke_rgb, anchor="mt")
        interval_bbox = _bbox([x - max(cap + 30, bar_w * 0.5), min(y_lower, y_upper) - 16, x + max(cap + 30, bar_w * 0.5), max(y_lower, y_upper) + 16])
        item_bbox = _bbox([x - slot_w * 0.45, plot_top, x + slot_w * 0.45, plot_bottom + 48])
        interval_bboxes[item.item_id] = interval_bbox
        item_bboxes[item.item_id] = item_bbox
        entities.append(_entity_record(item, interval_bbox=interval_bbox, item_bbox=item_bbox))
    return plot_bbox, item_bboxes, interval_bboxes, entities


def _entity_record(item: _IntervalItem, *, interval_bbox: Sequence[float], item_bbox: Sequence[float]) -> Dict[str, Any]:
    return {
        "entity_id": str(item.item_id),
        "entity_type": "error_interval_item",
        "label": str(item.label),
        "lower": int(item.lower),
        "midpoint": int(item.midpoint),
        "upper": int(item.upper),
        "interval_width": int(item.upper) - int(item.lower),
        "bbox_px": list(item_bbox),
        "interval_bbox_px": list(interval_bbox),
    }


def _render_chart(
    *,
    background: Image.Image,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Rendered:
    p = _resolve_render_params(params, instance_seed=int(instance_seed))
    image = background.convert("RGB")
    if image.size != (int(p.canvas_width), int(p.canvas_height)):
        image = image.resize((int(p.canvas_width), int(p.canvas_height)))
    draw = ImageDraw.Draw(image)

    margin = float(p.outer_margin_px)
    panel_bbox = _bbox([margin, margin, p.canvas_width - margin, p.canvas_height - margin])
    draw_rounded_rect(
        draw,
        tuple(panel_bbox),
        radius=int(p.panel_corner_radius_px),
        fill=p.panel_fill_rgb,
        outline=p.panel_outline_rgb,
        width=int(p.panel_outline_width_px),
    )
    title_font = load_font(p.title_font_size_px, bold=True)
    draw_centered_text(
        draw,
        text=str(dataset.title),
        center=(p.canvas_width / 2.0, margin + p.title_band_height_px * 0.43),
        font=title_font,
        fill=p.text_rgb,
        stroke_fill=p.text_stroke_rgb,
        stroke_width=1,
    )

    if dataset.scene_variant == "horizontal_forest":
        plot_bbox, item_bboxes, interval_bboxes, entities = _render_horizontal_forest(
            image=image,
            draw=draw,
            dataset=dataset,
            p=p,
            panel_bbox=panel_bbox,
        )
    elif dataset.scene_variant == "vertical_dot_whisker":
        plot_bbox, item_bboxes, interval_bboxes, entities = _render_vertical_dot_whisker(
            image=image,
            draw=draw,
            dataset=dataset,
            p=p,
            panel_bbox=panel_bbox,
        )
    elif dataset.scene_variant == "bar_with_error":
        plot_bbox, item_bboxes, interval_bboxes, entities = _render_bar_with_error(
            image=image,
            draw=draw,
            dataset=dataset,
            p=p,
            panel_bbox=panel_bbox,
        )
    else:
        raise ValueError(f"unsupported scene variant: {dataset.scene_variant}")

    render_meta = {
        "scene_variant": str(dataset.scene_variant),
        "axis_min": int(p.axis_min),
        "axis_max": int(p.axis_max),
        "tick_step": int(p.tick_step),
        "reference_value": dataset.reference_value,
        "style": {
            "panel_fill_rgb": list(p.panel_fill_rgb),
            "panel_outline_rgb": list(p.panel_outline_rgb),
            "axis_rgb": list(p.axis_rgb),
            "grid_rgb": list(p.grid_rgb),
            "reference_rgb": list(p.reference_rgb),
        },
    }
    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=list(plot_bbox),
        item_bboxes_px=dict(item_bboxes),
        interval_bboxes_px=dict(interval_bboxes),
        render_meta=render_meta,
    )


def _json_examples(query_id: str, *, prompt_defaults: Mapping[str, Any]) -> Tuple[str, str]:
    if str(query_id) in REFERENCE_COUNT_QUERY_VARIANTS:
        return (
            str(prompt_defaults["json_example_reference_count"]),
            str(prompt_defaults["json_example_answer_only_reference_count"]),
        )
    return (
        str(prompt_defaults["json_example_relation_label"]),
        str(prompt_defaults["json_example_answer_only_relation_label"]),
    )


def _query_phrase(query_id: str) -> str:
    return {
        "contains_reference_count": "include the reference value",
        "entirely_above_reference_count": "are entirely above the reference value",
        "entirely_below_reference_count": "are entirely below the reference value",
        "widest_interval_label": "widest interval",
        "narrowest_interval_label": "narrowest interval",
        "second_widest_interval_label": "second widest interval",
        "second_narrowest_interval_label": "second narrowest interval",
    }[str(query_id)]


class ChartsErrorIntervalChartTask:
    """Answer interval-relation questions over error-bar style charts."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "error_interval"
    default_dataset_enabled = False

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        public_overrides = _public_task_param_overrides(str(self.task_id)) if str(self.task_id) != TASK_ID else {}
        if public_overrides:
            merged_params = dict(public_overrides)
            merged_params.update(dict(params))
            params = merged_params

        query_id, query_probabilities = _resolve_query_variant(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        dataset = _construct_dataset(
            query_id=str(query_id),
            query_probabilities=query_probabilities,
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
                "answer_hint_count",
                "answer_hint_label",
                "evidence_hint",
                "object_description_horizontal_forest",
                "object_description_vertical_dot_whisker",
                "object_description_bar_with_error",
                "json_example_reference_count",
                "json_example_relation_label",
                "json_example_answer_only_reference_count",
                "json_example_answer_only_relation_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _json_examples(str(query_id), prompt_defaults=prompt_defaults)
        answer_hint = str(prompt_defaults["answer_hint_count" if str(query_id) in REFERENCE_COUNT_QUERY_VARIANTS else "answer_hint_label"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{dataset.scene_variant}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(answer_hint),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "reference_value": "" if dataset.reference_value is None else int(dataset.reference_value),
                "relation_phrase": _query_phrase(str(query_id)),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_item_ids = [str(value) for value in dataset.query.evidence_item_ids]
        evidence_bboxes = [list(rendered.interval_bboxes_px[str(item_id)]) for item_id in evidence_item_ids]
        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=dataset.query.answer)
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        item_by_id = {item.item_id: item for item in dataset.items}
        label_to_interval = {
            item.label: {"lower": int(item.lower), "midpoint": int(item.midpoint), "upper": int(item.upper)}
            for item in dataset.items
        }
        evidence_labels = [str(item_by_id[item_id].label) for item_id in evidence_item_ids]
        visual_scan = clamp_unit_interval(
            0.65 * normalize_int_with_bounds(len(dataset.items), [6, 10])
            + 0.35 * float(_SCENE_LOADS[str(dataset.scene_variant)])
        )
        evidence_scan = normalize_int_with_bounds(len(evidence_item_ids), [1, 5])
        reasoning_load = clamp_unit_interval(float(_QUERY_LOADS[str(query_id)]) + (0.08 * evidence_scan))
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOADS[str(dataset.scene_variant)]),
            },
        )

        query_params = {
            "query_variant": str(query_id),
            "query_variant": str(query_id),
            "query_id": str(query_id),
            "query_variant_probabilities": dict(dataset.query_probabilities),
            "query_variant_probabilities": dict(dataset.query_probabilities),
            "scene_variant": str(dataset.scene_variant),
            "scene_variant_probabilities": dict(dataset.scene_variant_probabilities),
            "category_count": int(len(dataset.items)),
            "category_count_probabilities": dict(_support_probability_map(range(6, 11))),
            "reference_value": dataset.reference_value,
            "answer_value": dataset.query.answer,
            **dict(dataset.query.params),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_variant": str(query_id),
                    "query_variant": str(query_id),
                    "query_id": str(query_id),
                    "scene_variant": str(dataset.scene_variant),
                    "reference_value": dataset.reference_value,
                    "answer_value": dataset.query.answer,
                    "evidence_item_ids": list(evidence_item_ids),
                },
            },
            "query_spec": {
                "query_variant": str(query_id),
                "query_variant": str(query_id),
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_variant": str(dataset.scene_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "category_labels": [str(item.label) for item in dataset.items],
                "render_meta": dict(rendered.render_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "item_bboxes_px": dict(rendered.item_bboxes_px),
                "interval_bboxes_px": dict(rendered.interval_bboxes_px),
            },
            "execution_trace": {
                "query_variant": str(query_id),
                "query_variant": str(query_id),
                "query_id": str(query_id),
                "question_format": "error_interval",
                "scene_variant": str(dataset.scene_variant),
                "category_count": int(len(dataset.items)),
                "reference_value": dataset.reference_value,
                "items": [dict(entity) for entity in rendered.entities],
                "label_to_interval": dict(label_to_interval),
                "answer_value": dataset.query.answer,
                "answer_type": str(dataset.query.answer_type),
                "evidence_item_ids": list(evidence_item_ids),
                "evidence_labels": list(evidence_labels),
                **dict(dataset.query.params),
            },
            "witness_symbolic": {
                "type": "error_interval_witness",
                "answer_value": dataset.query.answer,
                "evidence_item_ids": list(evidence_item_ids),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
                "bbox_map": {str(item_id): list(rendered.interval_bboxes_px[str(item_id)]) for item_id in evidence_item_ids},
                "item_ids": list(evidence_item_ids),
                "item_labels": list(evidence_labels),
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
            query_variant=str(query_id),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )


@register_task
class ChartsErrorIntervalReferenceCountTask(MergedChartQueryVariantTaskMixin, ChartsErrorIntervalChartTask):
    """Count intervals by relation to a reference value."""

    task_id = "task_charts__error_interval__reference_relation_count"
    default_dataset_enabled = True
    allowed_query_variants = REFERENCE_COUNT_QUERY_VARIANTS


@register_task
class ChartsErrorIntervalRelationLabelTask(MergedChartQueryVariantTaskMixin, ChartsErrorIntervalChartTask):
    """Identify a category by interval width or midpoint relation."""

    task_id = "task_charts__error_interval__interval_width_rank_label"
    default_dataset_enabled = True
    allowed_query_variants = RELATION_LABEL_QUERY_VARIANTS


__all__ = [
    "ChartsErrorIntervalChartTask",
    "ChartsErrorIntervalReferenceCountTask",
    "ChartsErrorIntervalRelationLabelTask",
    "REFERENCE_COUNT_QUERY_VARIANTS",
    "RELATION_LABEL_QUERY_VARIANTS",
    "SUPPORTED_QUERY_VARIANTS",
    "SUPPORTED_SCENE_VARIANTS",
]
