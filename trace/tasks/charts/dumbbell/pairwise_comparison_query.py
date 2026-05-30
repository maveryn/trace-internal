"""Dumbbell pairwise-comparison chart task."""

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
from ...shared.bbox_projection import bbox_union_raw as _bbox_union
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.font_assets import font_asset_version, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.text_rendering import load_font
from ...shared.text_legibility import draw_text_traced
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin, MergedChartQueryVariantTaskMixin
from ..shared.label_assets import resolve_chart_entity_labels
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_dumbbell_pairwise_comparison_query_base"
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "gap_rank_row_label",
    "side_winner_count",
    "absolute_gap_threshold_count",
)
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("horizontal_dumbbell",)
_SUPPORTED_RANK_ORDERS: Tuple[str, ...] = ("largest", "smallest")
_SUPPORTED_RANK_N: Tuple[int, ...] = (2, 3, 4)
_SUPPORTED_SIDE_DIRECTIONS: Tuple[str, ...] = ("series_a_greater", "series_b_greater")
_SUPPORTED_GAP_THRESHOLD_RELATIONS: Tuple[str, ...] = ("at_least", "at_most")

SUPPORTED_QUERY_IDS = _SUPPORTED_QUERY_IDS
SUPPORTED_SCENE_VARIANTS = _SUPPORTED_SCENE_VARIANTS

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "dumbbell")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="dumbbell")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="dumbbell", apply_prob=0.0)

_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "gap_rank_row_label": 0.68,
    "side_winner_count": 0.70,
    "absolute_gap_threshold_count": 0.64,
}
_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {"horizontal_dumbbell": 0.58}

RGB = Tuple[int, int, int]


@dataclass(frozen=True)
class _Row:
    row_id: str
    label: str
    value_a: int
    value_b: int

    @property
    def gap(self) -> int:
        return abs(int(self.value_a) - int(self.value_b))


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer: str | int
    answer_type: str
    evidence_row_ids: Tuple[str, ...]
    params: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    scene_variant: str
    series_a_name: str
    series_b_name: str
    rows: Tuple[_Row, ...]
    query: _Query


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    plot_margin_left_px: int
    plot_margin_right_px: int
    plot_margin_top_px: int
    plot_margin_bottom_px: int
    axis_line_width_px: int
    grid_line_width_px: int
    row_line_width_px: int
    connector_width_px: int
    point_radius_px: int
    point_outline_width_px: int
    tick_length_px: int
    title_font_size_px: int
    subtitle_font_size_px: int
    label_font_size_px: int
    tick_font_size_px: int
    legend_font_size_px: int
    panel_fill_rgb: RGB
    panel_border_rgb: RGB
    plot_fill_rgb: RGB
    axis_color_rgb: RGB
    grid_color_rgb: RGB
    row_line_rgb: RGB
    connector_rgb: RGB
    text_color_rgb: RGB
    muted_text_rgb: RGB
    text_stroke_rgb: RGB
    series_a_rgb: RGB
    series_b_rgb: RGB
    font_family: str
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: List[float]
    row_label_bboxes_px: Dict[str, List[float]]
    point_bboxes_px: Dict[str, List[float]]
    row_pair_bboxes_px: Dict[str, List[float]]
    connector_bboxes_px: Dict[str, List[float]]
    legend_bboxes_px: Dict[str, List[float]]


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _as_rgb(value: Any, fallback: RGB) -> RGB:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def _render_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), _RENDER_DEFAULTS.get(str(key), int(fallback))))


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


def _gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _balanced_int(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    namespace: str,
    low: int,
    high: int,
) -> Tuple[int, Dict[str, float]]:
    values = [int(value) for value in range(int(low), int(high) + 1)]
    if not values:
        raise ValueError(f"empty integer support for {namespace}")
    selected = values[resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)) % len(values)]
    return int(selected), uniform_probability_map(tuple(values))


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_QUERY_IDS,
        task_id=TASK_ID,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _resolve_rank_order(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_RANK_ORDERS,
        task_id=TASK_ID,
        explicit_key="rank_order",
        weights_key="rank_order_weights",
        balance_flag_key="balanced_rank_order_sampling",
        axis_namespace="rank_order",
    )


def _resolve_rank_n(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[int, Dict[str, float]]:
    raw = params.get("rank_n")
    if raw is not None:
        value = int(raw)
        if value not in _SUPPORTED_RANK_N:
            raise ValueError(f"rank_n must be one of {_SUPPORTED_RANK_N}")
        return int(value), {str(value): 1.0}
    enabled = bool(params.get("balanced_rank_n_sampling", _GEN_DEFAULTS.get("balanced_rank_n_sampling", True)))
    if enabled:
        selection = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.rank_n")
        value = _SUPPORTED_RANK_N[int(selection) % len(_SUPPORTED_RANK_N)]
    else:
        rng = spawn_rng(instance_seed, f"{TASK_ID}.rank_n")
        value = rng.choice(_SUPPORTED_RANK_N)
    return int(value), uniform_probability_map(_SUPPORTED_RANK_N)


def _resolve_side_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_SIDE_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="side_direction",
        weights_key="side_direction_weights",
        balance_flag_key="balanced_side_direction_sampling",
        axis_namespace="side_direction",
    )


def _resolve_gap_threshold_relation(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_GAP_THRESHOLD_RELATIONS,
        task_id=TASK_ID,
        explicit_key="gap_threshold_relation",
        weights_key="gap_threshold_relation_weights",
        balance_flag_key="balanced_gap_threshold_relation_sampling",
        axis_namespace="gap_threshold_relation",
    )


def _resolve_render_params(params: Mapping[str, Any]) -> _RenderParams:
    margin_left = _render_int(params, "plot_margin_left_px", 224)
    margin_right = _render_int(params, "plot_margin_right_px", 88)
    margin_top = _render_int(params, "plot_margin_top_px", 138)
    margin_bottom = _render_int(params, "plot_margin_bottom_px", 112)
    margin_left, margin_right, margin_top, margin_bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(margin_left),
        right_px=int(margin_right),
        top_px=int(margin_top),
        bottom_px=int(margin_bottom),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=_render_style_seed(params),
        namespace=f"{TASK_ID}.layout",
    )
    return _RenderParams(
        canvas_width=_render_int(params, "canvas_width", 1280),
        canvas_height=_render_int(params, "canvas_height", 900),
        plot_margin_left_px=int(margin_left),
        plot_margin_right_px=int(margin_right),
        plot_margin_top_px=int(margin_top),
        plot_margin_bottom_px=int(margin_bottom),
        axis_line_width_px=_render_int(params, "axis_line_width_px", 2),
        grid_line_width_px=_render_int(params, "grid_line_width_px", 1),
        row_line_width_px=_render_int(params, "row_line_width_px", 1),
        connector_width_px=_render_int(params, "connector_width_px", 4),
        point_radius_px=_render_int(params, "point_radius_px", 8),
        point_outline_width_px=_render_int(params, "point_outline_width_px", 2),
        tick_length_px=_render_int(params, "tick_length_px", 8),
        title_font_size_px=_render_int(params, "title_font_size_px", 30),
        subtitle_font_size_px=_render_int(params, "subtitle_font_size_px", 18),
        label_font_size_px=_render_int(params, "label_font_size_px", 20),
        tick_font_size_px=_render_int(params, "tick_font_size_px", 17),
        legend_font_size_px=_render_int(params, "legend_font_size_px", 20),
        panel_fill_rgb=_render_rgb(params, "panel_fill_rgb", (255, 255, 255)),
        panel_border_rgb=_render_rgb(params, "panel_border_rgb", (196, 203, 214)),
        plot_fill_rgb=_render_rgb(params, "plot_fill_rgb", (255, 255, 255)),
        axis_color_rgb=_render_rgb(params, "axis_color_rgb", (62, 68, 78)),
        grid_color_rgb=_render_rgb(params, "grid_color_rgb", (224, 228, 235)),
        row_line_rgb=_render_rgb(params, "row_line_rgb", (236, 239, 244)),
        connector_rgb=_render_rgb(params, "connector_rgb", (154, 162, 174)),
        text_color_rgb=_render_rgb(params, "text_color_rgb", (34, 40, 50)),
        muted_text_rgb=_render_rgb(params, "muted_text_rgb", (83, 94, 110)),
        text_stroke_rgb=_render_rgb(params, "text_stroke_rgb", (255, 255, 255)),
        series_a_rgb=_render_rgb(params, "series_a_rgb", (38, 101, 176)),
        series_b_rgb=_render_rgb(params, "series_b_rgb", (213, 92, 72)),
        font_family=sample_font_family(
            role="readout",
            instance_seed=_render_style_seed(params),
            namespace=f"{TASK_ID}.chart_font",
            params=params,
            exclude_tags=("display",),
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        ),
        layout_jitter_meta=dict(layout_jitter_meta),
    )


def _text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    *,
    stroke_width: int = 0,
) -> List[float]:
    box = draw.textbbox(tuple(float(value) for value in xy), str(text), font=font, stroke_width=max(0, int(stroke_width)))
    return _bbox([box[0], box[1], box[2], box[3]])


def _sample_rows(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    row_count: int,
    labels: Sequence[str],
    target_row_index: int | None,
    query_id: str,
    rank_order: str | None,
    rank_n: int | None,
    threshold: int | None,
    target_count: int | None,
    side_direction: str | None,
    gap_threshold_relation: str | None,
) -> Tuple[Tuple[_Row, ...], Tuple[str, ...], Dict[str, Any]]:
    rng = spawn_rng(instance_seed, f"{TASK_ID}.rows.{query_id}")
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="value_min",
        max_key="value_max",
        fallback_min=0,
        fallback_max=100,
        context=f"generation defaults for {TASK_ID}",
    )
    gap_min = _gen_int(params, "gap_min", 4)
    gap_max = _gen_int(params, "gap_max", 56)
    if int(value_min) < 0 or int(value_max) <= int(value_min):
        raise ValueError("value range must be positive and ordered")
    if int(gap_min) < 1 or int(gap_max) <= int(gap_min):
        raise ValueError("gap range must be positive and ordered")

    evidence_indices: List[int] = []
    gap_by_index: Dict[int, int] = {}
    signed_direction_by_index: Dict[int, int] = {}
    trace_params: Dict[str, Any] = {}

    if str(query_id) == "gap_rank_row_label":
        assert target_row_index is not None
        assert rank_order is not None
        assert rank_n is not None
        support = [gap for gap in range(int(gap_min), int(gap_max) + 1)]
        if len(support) < int(row_count):
            raise ValueError("not enough distinct gaps for ranked-gap query")
        gaps_sorted = sorted(rng.sample(support, int(row_count)))
        ranked = sorted(gaps_sorted, reverse=str(rank_order) == "largest")
        answer_gap = int(ranked[int(rank_n) - 1])
        remaining = [gap for gap in gaps_sorted if int(gap) != int(answer_gap)]
        for index in range(int(row_count)):
            gap_by_index[index] = int(answer_gap if index == int(target_row_index) else remaining.pop())
        evidence_indices = [int(target_row_index)]
        trace_params.update(
            {
                "rank_order": str(rank_order),
                "rank_n": int(rank_n),
                "rank_phrase": _rank_phrase(str(rank_order), int(rank_n)),
                "answer_gap": int(answer_gap),
            }
        )
    elif str(query_id) == "side_winner_count":
        assert threshold is not None
        assert target_count is not None
        assert side_direction is not None
        target_count = min(int(target_count), int(row_count))
        target_indices = sorted(rng.sample(list(range(int(row_count))), int(target_count)))
        evidence_indices = list(target_indices)
        for index in range(int(row_count)):
            is_target = int(index) in set(target_indices)
            if is_target:
                gap_by_index[index] = int(rng.randint(int(threshold), min(int(gap_max), int(threshold) + 22)))
                signed_direction_by_index[index] = 1 if str(side_direction) == "series_a_greater" else -1
            else:
                if rng.random() < 0.55:
                    gap_by_index[index] = int(rng.randint(int(gap_min), max(int(gap_min), int(threshold) - 3)))
                    signed_direction_by_index[index] = 1 if str(side_direction) == "series_a_greater" else -1
                else:
                    gap_by_index[index] = int(rng.randint(int(gap_min), min(int(gap_max), int(threshold) + 18)))
                    signed_direction_by_index[index] = -1 if str(side_direction) == "series_a_greater" else 1
        trace_params.update(
            {
                "side_direction": str(side_direction),
                "threshold_value": int(threshold),
                "target_count": int(target_count),
            }
        )
    elif str(query_id) == "absolute_gap_threshold_count":
        assert threshold is not None
        assert target_count is not None
        assert gap_threshold_relation is not None
        target_count = min(int(target_count), int(row_count))
        target_indices = sorted(rng.sample(list(range(int(row_count))), int(target_count)))
        target_index_set = set(target_indices)
        evidence_indices = list(target_indices)
        if str(gap_threshold_relation) == "at_least":
            target_support = [gap for gap in range(int(threshold), int(gap_max) + 1)]
            distractor_support = [gap for gap in range(int(gap_min), int(threshold))]
        elif str(gap_threshold_relation) == "at_most":
            target_support = [gap for gap in range(int(gap_min), int(threshold) + 1)]
            distractor_support = [gap for gap in range(int(threshold) + 1, int(gap_max) + 1)]
        else:
            raise ValueError(f"unsupported gap threshold relation: {gap_threshold_relation}")
        if not target_support or not distractor_support:
            raise ValueError("empty gap-threshold support")
        for index in range(int(row_count)):
            support = target_support if int(index) in target_index_set else distractor_support
            gap_by_index[index] = int(rng.choice(support))
        trace_params.update(
            {
                "gap_threshold_relation": str(gap_threshold_relation),
                "gap_threshold_value": int(threshold),
                "target_count": int(target_count),
            }
        )
    else:
        raise ValueError(f"unsupported query id: {query_id}")

    rows: List[_Row] = []
    for index, label in enumerate(labels):
        gap = int(gap_by_index[int(index)])
        direction = int(signed_direction_by_index.get(int(index), 1 if rng.random() < 0.5 else -1))
        lo = int(value_min)
        hi = int(value_max) - int(gap)
        if int(lo) > int(hi):
            raise ValueError("gap exceeds feasible value range")
        lower_value = int(rng.randint(int(lo), int(hi)))
        if int(direction) > 0:
            value_a = int(lower_value + int(gap))
            value_b = int(lower_value)
        else:
            value_a = int(lower_value)
            value_b = int(lower_value + int(gap))
        rows.append(_Row(row_id=f"row_{index}", label=str(label), value_a=int(value_a), value_b=int(value_b)))

    return tuple(rows), tuple(f"row_{index}" for index in evidence_indices), dict(trace_params)


def _rank_phrase(rank_order: str, rank_n: int) -> str:
    ordinal = {2: "second", 3: "third", 4: "fourth"}.get(int(rank_n), f"{int(rank_n)}th")
    return f"{ordinal} {str(rank_order)}"


def _build_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    query_id_probabilities: Mapping[str, float],
) -> _Dataset:
    row_min, row_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="row_count_min",
        max_key="row_count_max",
        fallback_min=10,
        fallback_max=16,
        context=f"generation defaults for {TASK_ID}",
    )
    row_count, row_count_probabilities = _balanced_int(
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.row_count",
        low=int(row_min),
        high=int(row_max),
    )
    label_rng = spawn_rng(instance_seed, f"{TASK_ID}.labels")
    labels = list(
        resolve_chart_entity_labels(
            label_rng,
            count=int(row_count),
            min_chars=2,
            max_chars=7,
            allow_spaces=False,
        ).labels
    )
    series_rng = spawn_rng(instance_seed, f"{TASK_ID}.series_labels")
    series_a_name, series_b_name = resolve_chart_entity_labels(
        series_rng,
        count=2,
        min_chars=2,
        max_chars=7,
        allow_spaces=False,
    ).labels

    support_params = dict(params)
    sampling_index = support_params.get("_sample_cursor")
    if sampling_index is not None:
        support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(_SUPPORTED_QUERY_IDS))

    answer_row_index: int | None = None
    rank_order: str | None = None
    rank_order_probabilities: Dict[str, float] = {}
    rank_n: int | None = None
    rank_n_probabilities: Dict[str, float] = {}
    side_direction: str | None = None
    side_direction_probabilities: Dict[str, float] = {}
    gap_threshold_relation: str | None = None
    gap_threshold_relation_probabilities: Dict[str, float] = {}
    threshold: int | None = None
    threshold_probabilities: Dict[str, float] = {}
    target_count: int | None = None
    target_count_probabilities: Dict[str, float] = {}

    if str(query_id) == "gap_rank_row_label":
        answer_row_index = resolve_selection_index(
            params=support_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.answer_row_index",
        ) % int(row_count)
        rank_order, rank_order_probabilities = _resolve_rank_order(support_params, instance_seed=int(instance_seed))
        rank_n, rank_n_probabilities = _resolve_rank_n(support_params, instance_seed=int(instance_seed))
    if str(query_id) == "side_winner_count":
        threshold_min = _gen_int(params, "side_threshold_min", 10)
        threshold_max = _gen_int(params, "side_threshold_max", 24)
        threshold_step = max(1, _gen_int(params, "side_threshold_step", 2))
        threshold_support = tuple(range(int(threshold_min), int(threshold_max) + 1, int(threshold_step)))
        threshold = int(
            threshold_support[
                resolve_selection_index(params=support_params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.threshold")
                % len(threshold_support)
            ]
        )
        threshold_probabilities = uniform_probability_map(threshold_support)
        count_min = _gen_int(params, "side_winner_count_min", 2)
        count_max = min(_gen_int(params, "side_winner_count_max", 10), int(row_count) - 1)
        target_count, target_count_probabilities = _balanced_int(
            support_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.side_winner_count.answer",
            low=int(count_min),
            high=int(count_max),
        )
        side_direction, side_direction_probabilities = _resolve_side_direction(support_params, instance_seed=int(instance_seed))
    if str(query_id) == "absolute_gap_threshold_count":
        threshold_min = _gen_int(params, "gap_threshold_min", 12)
        threshold_max = _gen_int(params, "gap_threshold_max", 28)
        threshold_step = max(1, _gen_int(params, "gap_threshold_step", 4))
        threshold_support = tuple(range(int(threshold_min), int(threshold_max) + 1, int(threshold_step)))
        threshold = int(
            threshold_support[
                resolve_selection_index(params=support_params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.gap_threshold")
                % len(threshold_support)
            ]
        )
        threshold_probabilities = uniform_probability_map(threshold_support)
        count_min = _gen_int(params, "gap_threshold_count_min", 2)
        count_max = min(_gen_int(params, "gap_threshold_count_max", 10), int(row_count) - 1)
        target_count, target_count_probabilities = _balanced_int(
            support_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.gap_threshold_count.answer",
            low=int(count_min),
            high=int(count_max),
        )
        gap_threshold_relation, gap_threshold_relation_probabilities = _resolve_gap_threshold_relation(
            support_params,
            instance_seed=int(instance_seed),
        )

    rows, evidence_row_ids, trace_params = _sample_rows(
        params=params,
        instance_seed=int(instance_seed),
        row_count=int(row_count),
        labels=labels,
        target_row_index=answer_row_index,
        query_id=str(query_id),
        rank_order=rank_order,
        rank_n=rank_n,
        threshold=threshold,
        target_count=target_count,
        side_direction=side_direction,
        gap_threshold_relation=gap_threshold_relation,
    )

    rows_by_id = {row.row_id: row for row in rows}
    if str(query_id) in {"side_winner_count", "absolute_gap_threshold_count"}:
        answer: str | int = int(len(evidence_row_ids))
        answer_type = "integer"
    else:
        answer = str(rows_by_id[str(evidence_row_ids[0])].label)
        answer_type = "string"

    query_params = {
        "query_id": str(query_id),
        "scene_variant": "horizontal_dumbbell",
        "query_id_probabilities": dict(query_id_probabilities),
        "scene_variant_probabilities": {"horizontal_dumbbell": 1.0},
        "row_count": int(row_count),
        "row_count_probabilities": dict(row_count_probabilities),
        "series_a_name": str(series_a_name),
        "series_b_name": str(series_b_name),
        **dict(trace_params),
    }
    if rank_order_probabilities:
        query_params["rank_order_probabilities"] = dict(rank_order_probabilities)
    if rank_n_probabilities:
        query_params["rank_n_probabilities"] = dict(rank_n_probabilities)
    if threshold_probabilities:
        query_params["threshold_value_probabilities"] = dict(threshold_probabilities)
    if target_count_probabilities:
        query_params["target_count_probabilities"] = dict(target_count_probabilities)
    if side_direction_probabilities:
        query_params["side_direction_probabilities"] = dict(side_direction_probabilities)
    if gap_threshold_relation_probabilities:
        query_params["gap_threshold_relation_probabilities"] = dict(gap_threshold_relation_probabilities)

    return _Dataset(
        scene_variant="horizontal_dumbbell",
        series_a_name=str(series_a_name),
        series_b_name=str(series_b_name),
        rows=tuple(rows),
        query=_Query(
            query_id=str(query_id),
            answer=answer,
            answer_type=str(answer_type),
            evidence_row_ids=tuple(evidence_row_ids),
            params=query_params,
        ),
    )


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    *,
    fill: RGB,
    stroke_fill: RGB,
    stroke_width: int = 0,
) -> List[float]:
    box = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
    width = float(box[2] - box[0])
    height = float(box[3] - box[1])
    x = float(xy[0]) - (width / 2.0)
    y = float(xy[1]) - (height / 2.0)
    draw_text_traced(draw,(x, y), str(text), font=font, fill=fill, stroke_fill=stroke_fill, stroke_width=max(0, int(stroke_width)), role="readout", required=False)
    return _bbox([x, y, x + width, y + height])


_TITLE_OPTIONS: Tuple[Tuple[str, str], ...] = (
    ("Paired Dot Comparison", "Horizontal positions encode values; each row compares the two legend series."),
    ("Series Gap Review", "Each connector shows the distance between paired values on one row."),
    ("Matched Value Scan", "Two colored dots share a row label and use the same horizontal axis."),
    ("Pairwise Difference Board", "Read each row by comparing the two dot positions against the shared scale."),
    ("Dumbbell Summary", "The gray segment links the two series values for each category row."),
)


def _render_dumbbell(
    background: Image.Image,
    *,
    dataset: _Dataset,
    render_params: _RenderParams,
    instance_seed: int,
) -> _Rendered:
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    left = float(render_params.plot_margin_left_px)
    right = float(width - int(render_params.plot_margin_right_px))
    top = float(render_params.plot_margin_top_px)
    bottom = float(height - int(render_params.plot_margin_bottom_px))
    plot_bbox = _bbox([left, top, right, bottom])
    panel_margin = 34
    panel_bbox = [panel_margin, 36, width - panel_margin, height - 42]
    draw.rounded_rectangle(panel_bbox, radius=8, fill=render_params.panel_fill_rgb, outline=render_params.panel_border_rgb, width=1)
    draw.rectangle([left, top, right, bottom], fill=render_params.plot_fill_rgb)

    title_font = load_font(render_params.title_font_size_px, bold=True, font_family=render_params.font_family)
    subtitle_font = load_font(render_params.subtitle_font_size_px, bold=False, font_family=render_params.font_family)
    label_font = load_font(render_params.label_font_size_px, bold=True, font_family=render_params.font_family)
    tick_font = load_font(render_params.tick_font_size_px, bold=False, font_family=render_params.font_family)
    legend_font = load_font(render_params.legend_font_size_px, bold=True, font_family=render_params.font_family)

    header_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.header_text")
    title_text, subtitle_text = _TITLE_OPTIONS[int(header_rng.randrange(len(_TITLE_OPTIONS)))]
    draw_text_traced(draw, (panel_margin + 22, 48), title_text, font=title_font, fill=render_params.text_color_rgb, role="readout", required=False)
    draw_text_traced(
        draw,
        (panel_margin + 24, 82),
        subtitle_text,
        font=subtitle_font,
        fill=render_params.muted_text_rgb,
     role="readout", required=False,)

    def x_px(value: float) -> float:
        return left + ((float(value) / 100.0) * (right - left))

    tick_values = [0, 20, 40, 60, 80, 100]
    for value in tick_values:
        x = x_px(float(value))
        draw.line([x, top, x, bottom], fill=render_params.grid_color_rgb, width=render_params.grid_line_width_px)
        draw.line([x, bottom, x, bottom + render_params.tick_length_px], fill=render_params.axis_color_rgb, width=render_params.axis_line_width_px)
        _draw_centered_text(
            draw,
            (x, bottom + 28),
            str(value),
            tick_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )
    draw.line([left, bottom, right, bottom], fill=render_params.axis_color_rgb, width=render_params.axis_line_width_px)

    row_count = len(dataset.rows)
    row_gap = (bottom - top) / max(1, row_count - 1)
    row_label_bboxes: Dict[str, List[float]] = {}
    point_bboxes: Dict[str, List[float]] = {}
    row_pair_bboxes: Dict[str, List[float]] = {}
    connector_bboxes: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []
    radius = float(render_params.point_radius_px)

    for index, row in enumerate(dataset.rows):
        y = top + (float(index) * row_gap)
        draw.line([left, y, right, y], fill=render_params.row_line_rgb, width=render_params.row_line_width_px)
        label_bbox = _text_bbox(draw, (panel_margin + 28, y - 10), row.label, label_font, stroke_width=1)
        draw_text_traced(draw,
            (panel_margin + 28, y - 10),
            row.label,
            font=label_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
         role="readout", required=False,)
        row_label_bboxes[row.row_id] = list(label_bbox)

        xa = x_px(float(row.value_a))
        xb = x_px(float(row.value_b))
        x0, x1 = sorted([xa, xb])
        connector_box = _bbox([x0, y - (render_params.connector_width_px / 2.0), x1, y + (render_params.connector_width_px / 2.0)])
        draw.line([xa, y, xb, y], fill=render_params.connector_rgb, width=render_params.connector_width_px)
        connector_bboxes[row.row_id] = connector_box

        point_a_bbox = _bbox([xa - radius, y - radius, xa + radius, y + radius])
        point_b_bbox = _bbox([xb - radius, y - radius, xb + radius, y + radius])
        draw.ellipse(point_a_bbox, fill=render_params.series_a_rgb, outline=(255, 255, 255), width=render_params.point_outline_width_px)
        draw.ellipse(point_b_bbox, fill=render_params.series_b_rgb, outline=(255, 255, 255), width=render_params.point_outline_width_px)
        point_bboxes[f"{row.row_id}:series_a"] = list(point_a_bbox)
        point_bboxes[f"{row.row_id}:series_b"] = list(point_b_bbox)
        row_pair_bboxes[row.row_id] = _bbox_union([connector_box, point_a_bbox, point_b_bbox], padding=8)
        entities.append(
            {
                "entity_id": row.row_id,
                "entity_type": "dumbbell_row_pair",
                "label": row.label,
                "value_a": int(row.value_a),
                "value_b": int(row.value_b),
                "gap": int(row.gap),
                "bbox_px": list(row_pair_bboxes[row.row_id]),
                "point_a_bbox_px": list(point_a_bbox),
                "point_b_bbox_px": list(point_b_bbox),
            }
        )

    legend_x = right - 250
    legend_y = 58
    legend_bboxes: Dict[str, List[float]] = {}
    for idx, (name, color) in enumerate(
        [(dataset.series_a_name, render_params.series_a_rgb), (dataset.series_b_name, render_params.series_b_rgb)]
    ):
        y = legend_y + (idx * 30)
        dot_bbox = [legend_x, y + 5, legend_x + 16, y + 21]
        draw.ellipse(dot_bbox, fill=color, outline=(255, 255, 255), width=2)
        text_xy = (legend_x + 26, y)
        text_bbox = _text_bbox(draw, text_xy, name, legend_font)
        draw_text_traced(draw,text_xy, name, font=legend_font, fill=render_params.text_color_rgb, role="readout", required=False)
        legend_bboxes[f"series_{idx}"] = _bbox_union([dot_bbox, text_bbox], padding=2)

    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=list(plot_bbox),
        row_label_bboxes_px=dict(row_label_bboxes),
        point_bboxes_px=dict(point_bboxes),
        row_pair_bboxes_px=dict(row_pair_bboxes),
        connector_bboxes_px=dict(connector_bboxes),
        legend_bboxes_px=dict(legend_bboxes),
    )


def _build_prompt_slots(dataset: _Dataset, prompt_defaults: Mapping[str, Any]) -> Dict[str, Any]:
    is_count = str(dataset.query.answer_type) == "integer"
    slots: Dict[str, Any] = {
        "object_description": str(prompt_defaults["object_description_dumbbell_pairwise"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults["answer_hint_count" if is_count else "answer_hint_label"]),
        "evidence_hint": str(prompt_defaults["evidence_hint_count" if is_count else "evidence_hint_label"]),
        "json_example": str(prompt_defaults["json_example_count" if is_count else "json_example_label"]),
        "json_example_answer_only": str(prompt_defaults["json_example_answer_only_count" if is_count else "json_example_answer_only_label"]),
    }
    if str(dataset.query.query_id) == "gap_rank_row_label":
        slots["rank_phrase"] = str(dataset.query.params["rank_phrase"])
    if str(dataset.query.query_id) == "side_winner_count":
        side_direction = str(dataset.query.params["side_direction"])
        if side_direction == "series_a_greater":
            slots["winner_series"] = str(dataset.series_a_name)
            slots["loser_series"] = str(dataset.series_b_name)
        else:
            slots["winner_series"] = str(dataset.series_b_name)
            slots["loser_series"] = str(dataset.series_a_name)
        slots["threshold_value"] = int(dataset.query.params["threshold_value"])
    if str(dataset.query.query_id) == "absolute_gap_threshold_count":
        relation = str(dataset.query.params["gap_threshold_relation"])
        slots["gap_relation_phrase"] = "at least" if relation == "at_least" else "at most"
        slots["gap_threshold_value"] = int(dataset.query.params["gap_threshold_value"])
    return slots


class ChartsDumbbellPairwiseComparisonQueryTask:
    """Generate paired-dot dumbbell chart comparison questions."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "dumbbell"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        if str(self.task_id) != TASK_ID:
            shared_gen_defaults, shared_render_defaults, _ = split_generation_rendering_prompt_defaults(
                _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
            )
            task_gen_defaults, task_render_defaults, _ = split_generation_rendering_prompt_defaults(
                _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
                task_id=str(self.task_id),
            )
            task_override_params = {
                str(key): value
                for key, value in task_gen_defaults.items()
                if shared_gen_defaults.get(str(key)) != value
            }
            task_override_params.update(
                {
                    str(key): value
                    for key, value in task_render_defaults.items()
                    if shared_render_defaults.get(str(key)) != value
                }
            )
            effective_params = dict(task_override_params)
            effective_params.update(dict(params))
            params = effective_params
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                return self._generate_once(int(instance_seed) + int(attempt), params=dict(params))
            except Exception as exc:
                last_error = exc
                continue
        raise RuntimeError(f"failed to generate {self.task_id} after {max_attempts} attempts: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        dataset = _build_dataset(
            params=params,
            instance_seed=int(instance_seed),
            query_id=str(query_id),
            query_id_probabilities=query_id_probabilities,
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
        rendered = _render_dumbbell(
            background,
            dataset=dataset,
            render_params=render_params,
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
                "answer_hint_label",
                "answer_hint_count",
                "evidence_hint_label",
                "evidence_hint_count",
                "json_example_label",
                "json_example_count",
                "json_example_answer_only_label",
                "json_example_answer_only_count",
                "object_description_dumbbell_pairwise",
            ],
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots=_build_prompt_slots(dataset, prompt_defaults),
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_row_ids = [str(row_id) for row_id in dataset.query.evidence_row_ids]
        evidence_bboxes = [list(rendered.row_pair_bboxes_px[row_id]) for row_id in evidence_row_ids]
        answer_value: str | int = int(dataset.query.answer) if str(dataset.query.answer_type) == "integer" else str(dataset.query.answer)
        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=answer_value)
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        rows_by_id = {row.row_id: row for row in dataset.rows}
        projected_evidence = {
            "bbox_set": list(evidence_bboxes),
            "row_ids": list(evidence_row_ids),
            "row_labels": [str(rows_by_id[row_id].label) for row_id in evidence_row_ids],
            "row_pair_bboxes": {
                str(row_id): list(rendered.row_pair_bboxes_px[str(row_id)])
                for row_id in evidence_row_ids
            },
        }

        row_values = [
            {
                "row_id": str(row.row_id),
                "label": str(row.label),
                "value_a": int(row.value_a),
                "value_b": int(row.value_b),
                "gap": int(row.gap),
                "signed_delta_a_minus_b": int(row.value_a) - int(row.value_b),
            }
            for row in dataset.rows
        ]
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(len(dataset.rows), [8, 18]),
                "reasoning_load": clamp_unit_interval(_REASONING_LOAD_BY_VARIANT[str(query_id)]),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(dataset.scene_variant)]),
            },
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_dumbbell_pairwise",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(dataset.scene_variant),
                    "answer": answer_value,
                    "evidence_row_ids": list(evidence_row_ids),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
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
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "point_radius_px": int(render_params.point_radius_px),
                "connector_width_px": int(render_params.connector_width_px),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "font_assets": {
                    "asset_version": font_asset_version(),
                    "chart_font_family": str(render_params.font_family),
                },
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "row_label_bboxes_px": dict(rendered.row_label_bboxes_px),
                "point_bboxes_px": dict(rendered.point_bboxes_px),
                "connector_bboxes_px": dict(rendered.connector_bboxes_px),
                "row_pair_bboxes_px": dict(rendered.row_pair_bboxes_px),
                "legend_bboxes_px": dict(rendered.legend_bboxes_px),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(dataset.scene_variant),
                "question_format": "dumbbell_pairwise_comparison_query",
                "answer": answer_value,
                "answer_type": str(dataset.query.answer_type),
                "series_a_name": str(dataset.series_a_name),
                "series_b_name": str(dataset.series_b_name),
                "row_count": int(len(dataset.rows)),
                "row_labels": [str(row.label) for row in dataset.rows],
                "rows": list(row_values),
                "evidence_row_ids": list(evidence_row_ids),
                "query_id_probabilities": dict(dataset.query.params.get("query_id_probabilities", {})),
                **dict(dataset.query.params),
            },
            "witness_symbolic": {
                "type": "dumbbell_pairwise_witness",
                "row_ids": list(evidence_row_ids),
                "answer": answer_value,
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
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsDumbbellGapRankRowLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsDumbbellPairwiseComparisonQueryTask,
):
    """Return the row label at a requested gap rank."""

    task_id = "task_charts__dumbbell__gap_rank_row_label"
    fixed_query_id = "gap_rank_row_label"


@register_task
class ChartsDumbbellPairRelationCountTask(
    MergedChartQueryVariantTaskMixin,
    ChartsDumbbellPairwiseComparisonQueryTask,
):
    """Count rows satisfying a dumbbell pair relation."""

    task_id = "task_charts__dumbbell__pair_relation_count"
    allowed_query_ids = ("side_winner_count", "absolute_gap_threshold_count")


__all__ = [
    "ChartsDumbbellGapRankRowLabelTask",
    "ChartsDumbbellPairRelationCountTask",
    "ChartsDumbbellPairwiseComparisonQueryTask",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
]
