"""Population-pyramid chart tasks for chart-domain visual reasoning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_raw as _bbox_union
from ...shared.color_distance import sample_color_palette_with_distance_constraints
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_int, resolve_render_rgb
from ...shared.text_rendering import draw_text_centered, fit_font_to_box, load_font
from ...shared.text_legibility import draw_traced_text
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from ..shared.information_style import make_chart_information_background, resolve_chart_information_style
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import chart_font_asset_metadata, load_chart_noise_defaults, sample_chart_font_family


TASK_ID = "charts_population_pyramid_base"
SCENE_ID = "population_pyramid"
GAP_QUERY_IDS: Tuple[str, ...] = ("largest_side_gap_label", "smallest_nonzero_side_gap_label")
THRESHOLD_QUERY_IDS: Tuple[str, ...] = (
    "left_side_threshold_count",
    "right_side_threshold_count",
    "combined_total_threshold_count",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = GAP_QUERY_IDS + THRESHOLD_QUERY_IDS
_THRESHOLD_RELATIONS: Tuple[str, ...] = ("at_least", "at_most")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "population_pyramid")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="population_pyramid", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)

RGB = Tuple[int, int, int]

_QUERY_REASONING_LOADS: Dict[str, float] = {
    "largest_side_gap_label": 0.60,
    "smallest_nonzero_side_gap_label": 0.62,
    "left_side_threshold_count": 0.56,
    "right_side_threshold_count": 0.56,
    "combined_total_threshold_count": 0.66,
}


@dataclass(frozen=True)
class _Row:
    row_id: str
    label: str
    left_value: int
    right_value: int

    @property
    def gap(self) -> int:
        return abs(int(self.left_value) - int(self.right_value))

    @property
    def total(self) -> int:
        return int(self.left_value) + int(self.right_value)


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer: int | str
    answer_type: str
    annotation_row_ids: Tuple[str, ...]
    params: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    left_series_label: str
    right_series_label: str
    left_color_rgb: RGB
    right_color_rgb: RGB
    rows: Tuple[_Row, ...]
    query_id: str
    query_id_probabilities: Dict[str, float]
    query: _Query
    title: str


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    plot_margin_left_px: int
    plot_margin_right_px: int
    plot_margin_top_px: int
    plot_margin_bottom_px: int
    title_band_height_px: int
    legend_gap_px: int
    axis_line_width_px: int
    grid_line_width_px: int
    bar_outline_width_px: int
    bar_gap_px: int
    title_font_size_px: int
    label_font_size_px: int
    tick_font_size_px: int
    legend_font_size_px: int
    value_font_size_px: int
    axis_max: int
    tick_step: int
    panel_fill_rgb: RGB
    panel_border_rgb: RGB
    axis_rgb: RGB
    grid_rgb: RGB
    text_rgb: RGB
    muted_text_rgb: RGB
    text_stroke_rgb: RGB
    font_family: str
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: List[float]
    row_bar_bboxes_px: Dict[str, List[float]]
    left_bar_bboxes_px: Dict[str, List[float]]
    right_bar_bboxes_px: Dict[str, List[float]]
    row_label_bboxes_px: Dict[str, List[float]]
    render_meta: Dict[str, Any]


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _probability_map(values: Sequence[int | str]) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if not support:
        return {}
    weight = 1.0 / float(len(support))
    return {str(value): float(weight) for value in support}


def _selection_index(params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> int:
    sample_cursor = params.get("_sample_cursor")
    if sample_cursor is not None:
        return abs(int(sample_cursor))
    return abs(int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))))


def _choose_from_values(
    params: Mapping[str, Any],
    *,
    values: Sequence[int | str],
    instance_seed: int,
    namespace: str,
) -> int | str:
    candidates = tuple(values)
    if not candidates:
        raise ValueError(f"empty support for {namespace}")
    return candidates[_selection_index(params, instance_seed=int(instance_seed), namespace=str(namespace)) % len(candidates)]


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


def _resolve_row_count(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[int, Dict[str, float]]:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="row_count_min",
        max_key="row_count_max",
        fallback_min=8,
        fallback_max=14,
        context=f"generation defaults for {TASK_ID}",
    )
    support = tuple(range(int(low), int(high) + 1))
    return int(
        _choose_from_values(
            params,
            values=support,
            instance_seed=int(instance_seed),
            namespace="charts.population_pyramid.row_count",
        )
    ), _probability_map(support)


def _resolve_threshold_relation(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    relation = str(
        _choose_from_values(
            params,
            values=_THRESHOLD_RELATIONS,
            instance_seed=int(instance_seed),
            namespace="charts.population_pyramid.threshold_relation",
        )
    )
    return relation, _probability_map(_THRESHOLD_RELATIONS)


def _resolve_series_labels(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, str, Dict[str, Any]]:
    label_pairs = params.get("series_label_pairs", group_default(_GEN_DEFAULTS, "series_label_pairs", (("Female", "Male"),)))
    normalized: List[Tuple[str, str]] = []
    if isinstance(label_pairs, Sequence) and not isinstance(label_pairs, (str, bytes)):
        for pair in label_pairs:
            if isinstance(pair, Sequence) and not isinstance(pair, (str, bytes)) and len(pair) >= 2:
                normalized.append((str(pair[0]), str(pair[1])))  # type: ignore[index]
    if not normalized:
        normalized = [("Female", "Male")]
    selected = normalized[
        _selection_index(params, instance_seed=int(instance_seed), namespace="charts.population_pyramid.series_labels")
        % len(normalized)
    ]
    return str(selected[0]), str(selected[1]), {
        "series_label_pairs": [[left, right] for left, right in normalized],
        "series_label_pair_probabilities": {
            f"{left}|{right}": 1.0 / float(len(normalized))
            for left, right in normalized
        },
    }


def _resolve_colors(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[RGB, RGB]:
    configured = params.get("series_palette_rgb", group_default(_RENDER_DEFAULTS, "series_palette_rgb", None))
    if isinstance(configured, Sequence) and not isinstance(configured, (str, bytes)):
        colors: List[RGB] = []
        for raw in configured:
            if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)) and len(raw) >= 3:
                colors.append(tuple(max(0, min(255, int(channel))) for channel in raw[:3]))  # type: ignore[arg-type]
        if len(colors) >= 2:
            offset = _selection_index(params, instance_seed=int(instance_seed), namespace="charts.population_pyramid.palette")
            return colors[int(offset) % len(colors)], colors[(int(offset) + 1) % len(colors)]
    rng = spawn_rng(int(instance_seed), "charts.population_pyramid.palette")
    palette = sample_color_palette_with_distance_constraints(
        rng,
        palette_size=2,
        channel_min=20,
        channel_max=210,
        anchor_colors=((255, 255, 255), (20, 20, 20)),
        min_distance=46.0,
        distance_space="lab",
    )
    return tuple(palette[0]), tuple(palette[1])


def _sample_age_labels(params: Mapping[str, Any], *, row_count: int, instance_seed: int) -> Tuple[Tuple[str, ...], Dict[str, Any]]:
    band_width_options = tuple(int(value) for value in params.get("age_band_width_options", group_default(_GEN_DEFAULTS, "age_band_width_options", (5, 10))))
    start_options = tuple(int(value) for value in params.get("age_start_options", group_default(_GEN_DEFAULTS, "age_start_options", (0, 5, 10))))
    band_width = int(
        _choose_from_values(
            params,
            values=band_width_options,
            instance_seed=int(instance_seed),
            namespace="charts.population_pyramid.age_band_width",
        )
    )
    start_age = int(
        _choose_from_values(
            params,
            values=start_options,
            instance_seed=int(instance_seed),
            namespace="charts.population_pyramid.age_start",
        )
    )
    labels = [
        f"{start_age + (index * band_width)}-{start_age + ((index + 1) * band_width) - 1}"
        for index in range(int(row_count))
    ]
    # Render oldest at the top, matching population-pyramid convention.
    labels = list(reversed(labels))
    return tuple(labels), {
        "age_band_width": int(band_width),
        "age_start": int(start_age),
        "age_band_width_probabilities": _probability_map(band_width_options),
        "age_start_probabilities": _probability_map(start_options),
    }


def _sample_pair_for_gap(rng: Any, *, gap: int, value_min: int, value_max: int, direction: int) -> Tuple[int, int]:
    lo = int(value_min)
    hi = int(value_max) - int(gap)
    if hi < lo:
        raise ValueError("gap exceeds value support")
    base = int(rng.randint(lo, hi))
    if int(direction) >= 0:
        return int(base + int(gap)), int(base)
    return int(base), int(base + int(gap))


def _sample_pair_for_total(rng: Any, *, total_min: int, total_max: int, value_min: int, value_max: int) -> Tuple[int, int]:
    feasible_totals = [
        int(total)
        for total in range(int(total_min), int(total_max) + 1)
        if (2 * int(value_min)) <= int(total) <= (2 * int(value_max))
    ]
    if not feasible_totals:
        raise ValueError("empty total support")
    total = int(rng.choice(feasible_totals))
    left_low = max(int(value_min), int(total) - int(value_max))
    left_high = min(int(value_max), int(total) - int(value_min))
    left = int(rng.randint(int(left_low), int(left_high)))
    right = int(total) - int(left)
    return int(left), int(right)


def _sample_gap_rows(
    *,
    query_id: str,
    labels: Sequence[str],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_Row, ...], Tuple[str, ...], Dict[str, Any]]:
    rng = spawn_rng(int(instance_seed), f"charts.population_pyramid.gap.{query_id}")
    value_min = int(params.get("value_min", group_default(_GEN_DEFAULTS, "value_min", 8)))
    value_max = int(params.get("value_max", group_default(_GEN_DEFAULTS, "value_max", 96)))
    gap_min = int(params.get("gap_min", group_default(_GEN_DEFAULTS, "gap_min", 4)))
    gap_max = int(params.get("gap_max", group_default(_GEN_DEFAULTS, "gap_max", 58)))
    row_count = len(labels)
    answer_index = int(
        _choose_from_values(
            params,
            values=tuple(range(row_count)),
            instance_seed=int(instance_seed),
            namespace=f"charts.population_pyramid.gap.answer_index.{query_id}",
        )
    )
    if str(query_id) == "largest_side_gap_label":
        target_gap = int(rng.randint(max(32, gap_min + 8), int(gap_max)))
        other_support = [gap for gap in range(int(gap_min), max(int(gap_min), int(target_gap) - 7))]
        rank_phrase = "largest"
    else:
        target_gap = int(rng.randint(int(gap_min), min(int(gap_min) + 4, int(gap_max))))
        other_support = [gap for gap in range(int(target_gap) + 7, int(gap_max) + 1)]
        rank_phrase = "smallest nonzero"
    if len(other_support) < row_count - 1:
        raise ValueError("not enough gap support")
    other_gaps = list(rng.sample(other_support, int(row_count) - 1))
    rows: List[_Row] = []
    for index, label in enumerate(labels):
        gap = int(target_gap if int(index) == int(answer_index) else other_gaps.pop())
        direction = 1 if bool(rng.randint(0, 1)) else -1
        left, right = _sample_pair_for_gap(
            rng,
            gap=int(gap),
            value_min=int(value_min),
            value_max=int(value_max),
            direction=int(direction),
        )
        rows.append(_Row(row_id=f"row_{index}", label=str(label), left_value=int(left), right_value=int(right)))
    annotation_row_id = f"row_{answer_index}"
    return tuple(rows), (annotation_row_id,), {
        "rank_phrase": str(rank_phrase),
        "target_gap": int(target_gap),
        "target_row_label": str(labels[int(answer_index)]),
        "target_row_index": int(answer_index),
    }


def _threshold_metric(row: _Row, query_id: str) -> int:
    if str(query_id) == "left_side_threshold_count":
        return int(row.left_value)
    if str(query_id) == "right_side_threshold_count":
        return int(row.right_value)
    if str(query_id) == "combined_total_threshold_count":
        return int(row.total)
    raise ValueError(f"unsupported threshold query id: {query_id}")


def _sample_threshold_rows(
    *,
    query_id: str,
    labels: Sequence[str],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_Row, ...], Tuple[str, ...], Dict[str, Any]]:
    rng = spawn_rng(int(instance_seed), f"charts.population_pyramid.threshold.{query_id}")
    row_count = len(labels)
    value_min = int(params.get("value_min", group_default(_GEN_DEFAULTS, "value_min", 8)))
    value_max = int(params.get("value_max", group_default(_GEN_DEFAULTS, "value_max", 96)))
    relation, relation_probabilities = _resolve_threshold_relation(params, instance_seed=int(instance_seed))
    count_min = int(params.get("threshold_count_min", group_default(_GEN_DEFAULTS, "threshold_count_min", 2)))
    count_max = min(
        int(params.get("threshold_count_max", group_default(_GEN_DEFAULTS, "threshold_count_max", 9))),
        int(row_count) - 1,
    )
    count_support = tuple(range(max(1, int(count_min)), max(int(count_min), int(count_max)) + 1))
    target_count = int(
        _choose_from_values(
            params,
            values=count_support,
            instance_seed=int(instance_seed),
            namespace=f"charts.population_pyramid.threshold.answer_count.{query_id}",
        )
    )
    target_indices = tuple(sorted(rng.sample(list(range(int(row_count))), k=int(target_count))))
    target_index_set = set(int(index) for index in target_indices)

    if str(query_id) == "combined_total_threshold_count":
        threshold_support = tuple(
            range(
                int(params.get("combined_threshold_min", group_default(_GEN_DEFAULTS, "combined_threshold_min", 70))),
                int(params.get("combined_threshold_max", group_default(_GEN_DEFAULTS, "combined_threshold_max", 150))) + 1,
                int(params.get("combined_threshold_step", group_default(_GEN_DEFAULTS, "combined_threshold_step", 10))),
            )
        )
    else:
        threshold_support = tuple(
            range(
                int(params.get("side_threshold_min", group_default(_GEN_DEFAULTS, "side_threshold_min", 28))),
                int(params.get("side_threshold_max", group_default(_GEN_DEFAULTS, "side_threshold_max", 78))) + 1,
                int(params.get("side_threshold_step", group_default(_GEN_DEFAULTS, "side_threshold_step", 5))),
            )
        )
    threshold = int(
        _choose_from_values(
            params,
            values=threshold_support,
            instance_seed=int(instance_seed),
            namespace=f"charts.population_pyramid.threshold.value.{query_id}",
        )
    )

    rows: List[_Row] = []
    for index, label in enumerate(labels):
        is_target = int(index) in target_index_set
        if str(query_id) == "combined_total_threshold_count":
            if str(relation) == "at_least":
                total_min, total_max = (threshold, min(2 * value_max, threshold + 42)) if is_target else (2 * value_min, threshold - 1)
            else:
                total_min, total_max = (2 * value_min, threshold) if is_target else (threshold + 1, min(2 * value_max, threshold + 42))
            left, right = _sample_pair_for_total(
                rng,
                total_min=int(total_min),
                total_max=int(total_max),
                value_min=int(value_min),
                value_max=int(value_max),
            )
        else:
            if str(relation) == "at_least":
                metric_low, metric_high = (threshold, value_max) if is_target else (value_min, threshold - 1)
            else:
                metric_low, metric_high = (value_min, threshold) if is_target else (threshold + 1, value_max)
            if int(metric_low) > int(metric_high):
                raise ValueError("empty side metric support")
            metric_value = int(rng.randint(int(metric_low), int(metric_high)))
            other_value = int(rng.randint(int(value_min), int(value_max)))
            if str(query_id) == "left_side_threshold_count":
                left, right = int(metric_value), int(other_value)
            else:
                left, right = int(other_value), int(metric_value)
        rows.append(_Row(row_id=f"row_{index}", label=str(label), left_value=int(left), right_value=int(right)))

    annotation_row_ids = tuple(f"row_{index}" for index in target_indices)
    metric_values = [_threshold_metric(row, str(query_id)) for row in rows]
    if str(relation) == "at_least":
        observed = tuple(row.row_id for row, value in zip(rows, metric_values) if int(value) >= int(threshold))
        relation_phrase = "at least"
    else:
        observed = tuple(row.row_id for row, value in zip(rows, metric_values) if int(value) <= int(threshold))
        relation_phrase = "at most"
    if tuple(observed) != tuple(annotation_row_ids):
        raise ValueError("constructed threshold support does not match target rows")
    return tuple(rows), tuple(annotation_row_ids), {
        "threshold_relation": str(relation),
        "threshold_relation_phrase": str(relation_phrase),
        "threshold_relation_probabilities": dict(relation_probabilities),
        "threshold_value": int(threshold),
        "threshold_value_probabilities": _probability_map(threshold_support),
        "target_count": int(target_count),
        "target_count_probabilities": _probability_map(count_support),
        "target_row_labels": [str(labels[index]) for index in target_indices],
    }


def _sample_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    query_id, query_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
    row_count, row_count_probabilities = _resolve_row_count(params, instance_seed=int(instance_seed))
    age_labels, age_label_meta = _sample_age_labels(params, row_count=int(row_count), instance_seed=int(instance_seed))
    left_label, right_label, series_label_meta = _resolve_series_labels(params, instance_seed=int(instance_seed))
    left_color, right_color = _resolve_colors(params, instance_seed=int(instance_seed))
    if str(query_id) in GAP_QUERY_IDS:
        rows, annotation_row_ids, query_params = _sample_gap_rows(
            query_id=str(query_id),
            labels=age_labels,
            params=params,
            instance_seed=int(instance_seed),
        )
        answer: int | str = str(next(row.label for row in rows if str(row.row_id) == str(annotation_row_ids[0])))
        answer_type = "string"
    else:
        rows, annotation_row_ids, query_params = _sample_threshold_rows(
            query_id=str(query_id),
            labels=age_labels,
            params=params,
            instance_seed=int(instance_seed),
        )
        answer = int(len(annotation_row_ids))
        answer_type = "integer"

    title_options = params.get("title_options", group_default(_RENDER_DEFAULTS, "title_options", ("Population Pyramid",)))
    if not isinstance(title_options, Sequence) or isinstance(title_options, (str, bytes)) or not title_options:
        title_options = ("Population Pyramid",)
    title = str(
        title_options[
            _selection_index(params, instance_seed=int(instance_seed), namespace="charts.population_pyramid.title")
            % len(title_options)
        ]
    )
    query_params.update(
        {
            "query_id": str(query_id),
            "query_id_probabilities": dict(query_probabilities),
            "row_count": int(row_count),
            "row_count_probabilities": dict(row_count_probabilities),
            "age_label_meta": dict(age_label_meta),
            "series_label_meta": dict(series_label_meta),
        }
    )
    return _Dataset(
        left_series_label=str(left_label),
        right_series_label=str(right_label),
        left_color_rgb=tuple(left_color),
        right_color_rgb=tuple(right_color),
        rows=tuple(rows),
        query_id=str(query_id),
        query_id_probabilities=dict(query_probabilities),
        query=_Query(
            query_id=str(query_id),
            answer=answer,
            answer_type=str(answer_type),
            annotation_row_ids=tuple(str(row_id) for row_id in annotation_row_ids),
            params=dict(query_params),
        ),
        title=str(title),
    )


def _resolve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    left = int(params.get("plot_margin_left_px", group_default(_RENDER_DEFAULTS, "plot_margin_left_px", 162)))
    right = int(params.get("plot_margin_right_px", group_default(_RENDER_DEFAULTS, "plot_margin_right_px", 84)))
    top = int(params.get("plot_margin_top_px", group_default(_RENDER_DEFAULTS, "plot_margin_top_px", 84)))
    bottom = int(params.get("plot_margin_bottom_px", group_default(_RENDER_DEFAULTS, "plot_margin_bottom_px", 104)))
    left, right, top, bottom, jitter_meta = apply_layout_jitter_to_margins(
        left_px=left,
        right_px=right,
        top_px=top,
        bottom_px=bottom,
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="charts.population_pyramid.layout",
    )
    font_family = sample_chart_font_family(
        instance_seed=int(instance_seed),
        namespace="charts.population_pyramid.font",
        params=params,
        exclude_tags=("display",),
    )
    return _RenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1280))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 900))),
        plot_margin_left_px=int(left),
        plot_margin_right_px=int(right),
        plot_margin_top_px=int(top),
        plot_margin_bottom_px=int(bottom),
        title_band_height_px=int(params.get("title_band_height_px", group_default(_RENDER_DEFAULTS, "title_band_height_px", 62))),
        legend_gap_px=int(params.get("legend_gap_px", group_default(_RENDER_DEFAULTS, "legend_gap_px", 28))),
        axis_line_width_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "axis_line_width_px", 2, instance_seed=int(instance_seed), namespace=TASK_ID)),
        grid_line_width_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "grid_line_width_px", 1, instance_seed=int(instance_seed), namespace=TASK_ID)),
        bar_outline_width_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "bar_outline_width_px", 1, instance_seed=int(instance_seed), namespace=TASK_ID)),
        bar_gap_px=int(resolve_render_int(params, _RENDER_DEFAULTS, "bar_gap_px", 5, instance_seed=int(instance_seed), namespace=TASK_ID)),
        title_font_size_px=int(params.get("title_font_size_px", group_default(_RENDER_DEFAULTS, "title_font_size_px", 30))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", 18))),
        tick_font_size_px=int(params.get("tick_font_size_px", group_default(_RENDER_DEFAULTS, "tick_font_size_px", 15))),
        legend_font_size_px=int(params.get("legend_font_size_px", group_default(_RENDER_DEFAULTS, "legend_font_size_px", 18))),
        value_font_size_px=int(params.get("value_font_size_px", group_default(_RENDER_DEFAULTS, "value_font_size_px", 14))),
        axis_max=int(params.get("axis_max", group_default(_RENDER_DEFAULTS, "axis_max", 100))),
        tick_step=int(params.get("tick_step", group_default(_RENDER_DEFAULTS, "tick_step", 20))),
        panel_fill_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "panel_fill_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=TASK_ID),
        panel_border_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "panel_border_rgb", (190, 198, 208), instance_seed=int(instance_seed), namespace=TASK_ID),
        axis_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "axis_rgb", (62, 68, 78), instance_seed=int(instance_seed), namespace=TASK_ID),
        grid_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "grid_rgb", (225, 229, 235), instance_seed=int(instance_seed), namespace=TASK_ID),
        text_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_rgb", (35, 42, 52), instance_seed=int(instance_seed), namespace=TASK_ID),
        muted_text_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "muted_text_rgb", (82, 91, 106), instance_seed=int(instance_seed), namespace=TASK_ID),
        text_stroke_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_stroke_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=TASK_ID),
        font_family=str(font_family),
        layout_jitter_meta=dict(jitter_meta),
    )


def _relative_luminance(color: Sequence[int]) -> float:
    def _channel(value: int) -> float:
        normalized = float(value) / 255.0
        if normalized <= 0.03928:
            return normalized / 12.92
        return ((normalized + 0.055) / 1.055) ** 2.4

    rgb = [max(0, min(255, int(channel))) for channel in color[:3]]
    return (0.2126 * _channel(rgb[0])) + (0.7152 * _channel(rgb[1])) + (0.0722 * _channel(rgb[2]))


def _readable_chart_text_colors(surface_rgb: Sequence[int]) -> Tuple[RGB, RGB, RGB]:
    if _relative_luminance(surface_rgb) >= 0.55:
        return (34, 42, 54), (72, 84, 100), (34, 42, 54)
    return (246, 250, 255), (205, 218, 232), (18, 24, 32)


def _darken(color: RGB, factor: float = 0.70) -> RGB:
    return tuple(max(0, min(255, int(round(float(channel) * float(factor))))) for channel in color)  # type: ignore[return-value]


def _text_on_bar(color: RGB) -> RGB:
    return (18, 24, 32) if _relative_luminance(color) > 0.52 else (248, 250, 252)


def _draw_text(
    draw: ImageDraw.ImageDraw,
    *,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    fill: RGB,
    stroke: RGB,
    stroke_width: int = 1,
    required: bool = True,
) -> None:
    draw_traced_text(
        draw,
        xy=(float(xy[0]), float(xy[1])),
        text=str(text),
        font=font,
        fill_rgb=tuple(int(value) for value in fill),
        stroke_rgb=tuple(int(value) for value in stroke),
        stroke_width=int(stroke_width),
        role="chart_text",
        required=bool(required),
    )


def _render_dataset(dataset: _Dataset, params: Mapping[str, Any], *, instance_seed: int) -> _Rendered:
    render_params = _resolve_render_params(params, instance_seed=int(instance_seed))
    style, style_meta = resolve_chart_information_style(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        task_group="population_pyramid",
        protected_colors=(dataset.left_color_rgb, dataset.right_color_rgb),
        allow_dark=False,
        allow_colored_surface=True,
    )
    image, background_meta = make_chart_information_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=style,
        instance_seed=int(instance_seed),
        namespace="charts.population_pyramid.background",
    )
    if image.mode != "RGB":
        image = image.convert("RGB")
    draw = ImageDraw.Draw(image)
    panel_fill_rgb = tuple(int(value) for value in style.surface_rgb)
    panel_border_rgb = tuple(int(value) for value in style.panel_border_rgb)
    axis_rgb = tuple(int(value) for value in style.axis_rgb)
    grid_rgb = tuple(int(value) for value in style.grid_rgb)
    text_rgb, muted_text_rgb, text_stroke_rgb = _readable_chart_text_colors(panel_fill_rgb)
    text_stroke_width = 1

    plot_left = float(render_params.plot_margin_left_px)
    plot_right = float(render_params.canvas_width - render_params.plot_margin_right_px)
    plot_top = float(render_params.plot_margin_top_px + render_params.title_band_height_px)
    plot_bottom = float(render_params.canvas_height - render_params.plot_margin_bottom_px)
    plot_width = float(plot_right - plot_left)
    plot_height = float(plot_bottom - plot_top)
    if plot_width <= 100 or plot_height <= 100:
        raise ValueError("population pyramid plot area is too small")
    center_x = float(plot_left + (plot_width * 0.52))
    left_width = float(center_x - plot_left - 10)
    right_width = float(plot_right - center_x - 10)
    scale = min(left_width, right_width) / max(1.0, float(render_params.axis_max))
    panel_bbox = [
        max(18.0, float(plot_left - 118)),
        float(render_params.plot_margin_top_px),
        min(float(render_params.canvas_width - 22), float(plot_right + 42)),
        min(float(render_params.canvas_height - 22), float(plot_bottom + 62)),
    ]
    draw.rounded_rectangle(tuple(panel_bbox), radius=14, fill=panel_fill_rgb, outline=panel_border_rgb, width=2)

    title_font = load_font(render_params.title_font_size_px, bold=True, font_family=render_params.font_family)
    tick_font = load_font(render_params.tick_font_size_px, bold=False, font_family=render_params.font_family)
    legend_font = load_font(render_params.legend_font_size_px, bold=True, font_family=render_params.font_family)
    value_font = load_font(render_params.value_font_size_px, bold=True, font_family=render_params.font_family)

    _draw_text(
        draw,
        xy=(plot_left - 82, float(render_params.plot_margin_top_px + 12)),
        text=str(dataset.title),
        font=title_font,
        fill=text_rgb,
        stroke=text_stroke_rgb,
        stroke_width=text_stroke_width,
    )

    legend_y = float(render_params.plot_margin_top_px + 54)
    legend_items = ((dataset.left_series_label, dataset.left_color_rgb), (dataset.right_series_label, dataset.right_color_rgb))
    legend_x = float(center_x - 180)
    for index, (label, color) in enumerate(legend_items):
        x = float(legend_x + index * 230)
        draw.rounded_rectangle((x, legend_y + 3, x + 28, legend_y + 19), radius=4, fill=color, outline=_darken(color, 0.62), width=1)
        _draw_text(
            draw,
            xy=(x + 38, legend_y),
            text=str(label),
            font=legend_font,
            fill=text_rgb,
            stroke=text_stroke_rgb,
            stroke_width=text_stroke_width,
        )

    # Mirrored positive magnitude axis.
    for tick in range(0, int(render_params.axis_max) + 1, int(render_params.tick_step)):
        dx = float(tick) * float(scale)
        if int(tick) == 0:
            xs = [center_x]
        else:
            xs = [center_x - dx, center_x + dx]
        for x in xs:
            draw.line((x, plot_top, x, plot_bottom), fill=axis_rgb if int(tick) == 0 else grid_rgb, width=int(render_params.axis_line_width_px if int(tick) == 0 else render_params.grid_line_width_px))
            label = str(abs(int(tick)))
            draw_text_centered(
                draw,
                text=label,
                center=(x, plot_bottom + 25),
                font=tick_font,
                fill=muted_text_rgb,
                stroke_fill=text_stroke_rgb,
                stroke_width=text_stroke_width,
            )
    draw.line((plot_left, plot_bottom, plot_right, plot_bottom), fill=axis_rgb, width=int(render_params.axis_line_width_px))
    draw.line((plot_left, plot_top, plot_left, plot_bottom), fill=axis_rgb, width=1)
    draw.line((plot_right, plot_top, plot_right, plot_bottom), fill=axis_rgb, width=1)

    row_step = plot_height / float(len(dataset.rows))
    bar_height = max(12.0, min(36.0, row_step - float(render_params.bar_gap_px)))
    row_bar_bboxes: Dict[str, List[float]] = {}
    left_bar_bboxes: Dict[str, List[float]] = {}
    right_bar_bboxes: Dict[str, List[float]] = {}
    row_label_bboxes: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []

    for index, row in enumerate(dataset.rows):
        center_y = float(plot_top + (index + 0.5) * row_step)
        y0 = float(center_y - (bar_height / 2.0))
        y1 = float(center_y + (bar_height / 2.0))
        left_x0 = float(center_x - (float(row.left_value) * scale))
        left_x1 = float(center_x)
        right_x0 = float(center_x)
        right_x1 = float(center_x + (float(row.right_value) * scale))
        left_bbox = _bbox([left_x0, y0, left_x1, y1])
        right_bbox = _bbox([right_x0, y0, right_x1, y1])
        row_bbox = _bbox_union([left_bbox, right_bbox], padding=5)
        left_bar_bboxes[str(row.row_id)] = list(left_bbox)
        right_bar_bboxes[str(row.row_id)] = list(right_bbox)
        row_bar_bboxes[str(row.row_id)] = list(row_bbox)

        draw.rounded_rectangle(tuple(left_bbox), radius=4, fill=dataset.left_color_rgb, outline=_darken(dataset.left_color_rgb, 0.58), width=int(render_params.bar_outline_width_px))
        draw.rounded_rectangle(tuple(right_bbox), radius=4, fill=dataset.right_color_rgb, outline=_darken(dataset.right_color_rgb, 0.58), width=int(render_params.bar_outline_width_px))
        label = str(row.label)
        label_font_fitted = fit_font_to_box(
            draw,
            text=label,
            max_width=86,
            max_height=bar_height + 8,
            bold=True,
            font_family=render_params.font_family,
            min_size_px=9,
            max_size_px=render_params.label_font_size_px,
        )
        text_bbox = draw.textbbox((0, 0), label, font=label_font_fitted, stroke_width=1)
        label_xy = (plot_left - 16 - float(text_bbox[2] - text_bbox[0]), center_y - 0.5 * float(text_bbox[3] - text_bbox[1]))
        label_record = draw_traced_text(
            draw,
            xy=(float(label_xy[0]), float(label_xy[1])),
            text=label,
            font=label_font_fitted,
            fill_rgb=text_rgb,
            stroke_rgb=text_stroke_rgb,
            stroke_width=text_stroke_width,
            role="axis_tick",
            required=True,
        )
        row_label_bboxes[str(row.row_id)] = _bbox(label_record["bbox_px"])

        for side, value, bbox, color in (
            ("left", int(row.left_value), left_bbox, dataset.left_color_rgb),
            ("right", int(row.right_value), right_bbox, dataset.right_color_rgb),
        ):
            value_text = str(value)
            vb = draw.textbbox((0, 0), value_text, font=value_font, stroke_width=1)
            value_width = float(vb[2] - vb[0])
            x0, by0, x1, by1 = [float(v) for v in bbox]
            if float(x1 - x0) >= value_width + 12:
                text_center = ((x0 + x1) / 2.0, center_y)
                fill = _text_on_bar(color)
                stroke = _darken(color, 0.58) if fill == (248, 250, 252) else (248, 250, 252)
            elif side == "left":
                text_center = (max(plot_left + value_width / 2.0, x0 - value_width / 2.0 - 6), center_y)
                fill = text_rgb
                stroke = text_stroke_rgb
            else:
                text_center = (min(plot_right - value_width / 2.0, x1 + value_width / 2.0 + 6), center_y)
                fill = text_rgb
                stroke = text_stroke_rgb
            draw_text_centered(
                draw,
                text=value_text,
                center=text_center,
                font=value_font,
                fill=fill,
                stroke_fill=stroke,
                stroke_width=1,
            )

        entities.append(
            {
                "entity_id": str(row.row_id),
                "entity_type": "population_pyramid_row",
                "row_id": str(row.row_id),
                "row_label": str(row.label),
                "left_series_label": str(dataset.left_series_label),
                "right_series_label": str(dataset.right_series_label),
                "left_value": int(row.left_value),
                "right_value": int(row.right_value),
                "gap": int(row.gap),
                "total": int(row.total),
                "row_bar_bbox_px": list(row_bar_bboxes[str(row.row_id)]),
                "left_bar_bbox_px": list(left_bar_bboxes[str(row.row_id)]),
                "right_bar_bbox_px": list(right_bar_bboxes[str(row.row_id)]),
                "row_label_bbox_px": list(row_label_bboxes[str(row.row_id)]),
            }
        )

    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=_bbox([plot_left, plot_top, plot_right, plot_bottom]),
        row_bar_bboxes_px=dict(row_bar_bboxes),
        left_bar_bboxes_px=dict(left_bar_bboxes),
        right_bar_bboxes_px=dict(right_bar_bboxes),
        row_label_bboxes_px=dict(row_label_bboxes),
        render_meta={
            "panel_bbox_px": _bbox(panel_bbox),
            "center_axis_x_px": round(float(center_x), 3),
            "axis_max": int(render_params.axis_max),
            "tick_step": int(render_params.tick_step),
            "font_assets": chart_font_asset_metadata(render_params.font_family),
            "layout_jitter": dict(render_params.layout_jitter_meta),
            "background": dict(background_meta),
            "information_style": dict(style_meta),
        },
    )


def _build_prompt_slots(dataset: _Dataset, prompt_defaults: Mapping[str, Any]) -> Dict[str, Any]:
    query_id = str(dataset.query_id)
    is_count = query_id in THRESHOLD_QUERY_IDS
    slots: Dict[str, Any] = {
        "object_description": str(prompt_defaults["object_description"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults["answer_hint_count" if is_count else "answer_hint_label"]),
        "annotation_hint": str(prompt_defaults["annotation_hint_count" if is_count else "annotation_hint_label"]),
        "json_example": str(prompt_defaults["json_example_count" if is_count else "json_example_label"]),
        "json_example_answer_only": str(prompt_defaults["json_example_answer_only_count" if is_count else "json_example_answer_only_label"]),
        "left_series_label": str(dataset.left_series_label),
        "right_series_label": str(dataset.right_series_label),
    }
    if query_id in GAP_QUERY_IDS:
        slots["rank_phrase"] = str(dataset.query.params["rank_phrase"])
    if query_id in THRESHOLD_QUERY_IDS:
        relation_phrase = str(dataset.query.params["threshold_relation_phrase"])
        slots["threshold_value"] = int(dataset.query.params["threshold_value"])
        slots["threshold_relation_phrase"] = str(relation_phrase)
        if query_id == "left_side_threshold_count":
            slots["metric_phrase"] = f"the \"{dataset.left_series_label}\" value"
        elif query_id == "right_side_threshold_count":
            slots["metric_phrase"] = f"the \"{dataset.right_series_label}\" value"
        else:
            slots["metric_phrase"] = f"the sum of \"{dataset.left_series_label}\" and \"{dataset.right_series_label}\""
    return slots


class ChartsPopulationPyramidTask:
    """Shared population-pyramid chart generator."""

    domain = "charts"
    task_group = "population_pyramid"
    task_id = TASK_ID
    default_dataset_enabled = False

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        params = dict(params or {})
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "answer_hint_label",
                "answer_hint_count",
                "annotation_hint_label",
                "annotation_hint_count",
                "json_example_label",
                "json_example_count",
                "json_example_answer_only_label",
                "json_example_answer_only_count",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) + int(attempt)
            try:
                dataset = _sample_dataset(params, instance_seed=int(attempt_seed))
                rendered = _render_dataset(dataset, params, instance_seed=int(attempt_seed))
                image, post_noise_meta = apply_post_image_noise(
                    rendered.image,
                    instance_seed=int(attempt_seed),
                    params=params,
                    default_config=POST_IMAGE_NOISE_DEFAULTS,
                )
                query_id = str(dataset.query_id)
                prompt_selection = render_task_prompt_variants(
                    domain=self.domain,
                    task_group=self.task_group,
                    bundle_id=str(prompt_defaults["bundle_id"]),
                    scene_key=str(prompt_defaults["scene_key"]),
                    task_key=str(prompt_defaults["task_key"]),
                    query_key=str(query_id),
                    answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
                    slots=_build_prompt_slots(dataset, prompt_defaults),
                    instance_seed=int(attempt_seed),
                )
                prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
                annotation_bboxes = [
                    list(rendered.row_bar_bboxes_px[str(row_id)])
                    for row_id in dataset.query.annotation_row_ids
                ]
                answer_gt = TypedValue(type=str(dataset.query.answer_type), value=dataset.query.answer)
                annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))
                rows_payload = [
                    {
                        "row_id": str(row.row_id),
                        "label": str(row.label),
                        "left_value": int(row.left_value),
                        "right_value": int(row.right_value),
                        "gap": int(row.gap),
                        "total": int(row.total),
                    }
                    for row in dataset.rows
                ]
                row_count = int(len(dataset.rows))
                annotation_load = normalize_int_with_bounds(len(dataset.query.annotation_row_ids), [1, 9])
                visual_scan = normalize_int_with_bounds(row_count, [8, 14])
                reasoning_load = clamp_unit_interval(float(_QUERY_REASONING_LOADS[str(query_id)]) + (0.06 * float(annotation_load)))
                complexity = build_chart_complexity(
                    weights=_COMPLEXITY_WEIGHTS,
                    components={
                        "visual_scan": float(visual_scan),
                        "reasoning_load": float(reasoning_load),
                        "scene_variant_load": 0.62,
                    },
                )
                query_params = {
                    "query_id": str(query_id),
                    "query_id_probabilities": dict(dataset.query_id_probabilities),
                    "answer_value": dataset.query.answer,
                    "answer_type": str(dataset.query.answer_type),
                    **dict(dataset.query.params),
                }
                trace_payload = {
                    "scene_ir": {
                        "scene_kind": SCENE_ID,
                        "entities": [dict(entity) for entity in rendered.entities],
                        "relations": {
                            "query_id": str(query_id),
                            "answer_value": dataset.query.answer,
                            "annotation_row_ids": [str(value) for value in dataset.query.annotation_row_ids],
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
                        "canvas_width": int(image.size[0]),
                        "canvas_height": int(image.size[1]),
                        "render_meta": dict(rendered.render_meta),
                        "post_image_noise": dict(post_noise_meta),
                    },
                    "render_map": {
                        "plot_bbox_px": list(rendered.plot_bbox_px),
                        "row_bar_bboxes_px": dict(rendered.row_bar_bboxes_px),
                        "left_bar_bboxes_px": dict(rendered.left_bar_bboxes_px),
                        "right_bar_bboxes_px": dict(rendered.right_bar_bboxes_px),
                        "row_label_bboxes_px": dict(rendered.row_label_bboxes_px),
                    },
                    "execution_trace": {
                        "query_id": str(query_id),
                        "question_format": SCENE_ID,
                        "left_series_label": str(dataset.left_series_label),
                        "right_series_label": str(dataset.right_series_label),
                        "row_count": int(row_count),
                        "rows": list(rows_payload),
                        "row_labels": [str(row.label) for row in dataset.rows],
                        "answer_value": dataset.query.answer,
                        "answer_type": str(dataset.query.answer_type),
                        "annotation_row_ids": [str(value) for value in dataset.query.annotation_row_ids],
                        **dict(dataset.query.params),
                    },
                    "witness_symbolic": {
                        "type": "population_pyramid_witness",
                        "answer_value": dataset.query.answer,
                        "annotation_row_ids": [str(value) for value in dataset.query.annotation_row_ids],
                    },
                    "projected_annotation": {
                        "bbox_set": list(annotation_bboxes),
                        "annotation_row_ids": [str(value) for value in dataset.query.annotation_row_ids],
                    },
                    "post_image_noise": dict(post_noise_meta),
                }
                return TaskOutput(
                    prompt=str(prompt_artifacts.prompt),
                    prompt_variants=dict(prompt_artifacts.prompt_variants),
                    answer_gt=answer_gt,
                    annotation_gt=annotation_gt,
                    image=image,
                    image_id="img0",
                    trace_payload=trace_payload,
                    complexity=complexity,
                    task_versions=default_task_versions(),
                    scene_id=SCENE_ID,
                    query_id=str(query_id),
                )
            except Exception as exc:
                last_error = exc
                continue
        raise RuntimeError(f"failed to generate population-pyramid chart after {max_attempts} attempts") from last_error


@register_task
class ChartsPopulationPyramidSideGapExtremumLabelTask(
    MergedChartQueryVariantTaskMixin,
    ChartsPopulationPyramidTask,
):
    """Return the age-group label whose mirrored sides have an extremal gap."""

    task_id = "task_charts__population_pyramid__side_gap_extremum_label"
    default_dataset_enabled = True
    allowed_query_ids = GAP_QUERY_IDS


@register_task
class ChartsPopulationPyramidAgeGroupThresholdCountTask(
    MergedChartQueryVariantTaskMixin,
    ChartsPopulationPyramidTask,
):
    """Count age groups satisfying a side or combined-total threshold."""

    task_id = "task_charts__population_pyramid__age_group_threshold_count"
    default_dataset_enabled = True
    allowed_query_ids = THRESHOLD_QUERY_IDS


__all__ = [
    "ChartsPopulationPyramidAgeGroupThresholdCountTask",
    "ChartsPopulationPyramidSideGapExtremumLabelTask",
    "ChartsPopulationPyramidTask",
    "GAP_QUERY_IDS",
    "SUPPORTED_QUERY_IDS",
    "THRESHOLD_QUERY_IDS",
]
