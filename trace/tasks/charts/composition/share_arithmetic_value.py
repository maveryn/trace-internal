"""Single-chart composition share arithmetic task."""

from __future__ import annotations

import colorsys
import itertools
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
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_int, resolve_render_rgb
from ...shared.text_rendering import load_font
from ..shared.complexity import build_chart_complexity, normalize_int_with_bounds, resolve_chart_complexity_weights
from ..shared.labeled_chart_common import (
    CHART_LABEL_POOL_UP_TO_25,
    LabeledChartDefaults,
    balanced_choice_from_values,
    resolve_chart_axis_variant,
    sample_composition_with_sum,
)
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_composition_share_arithmetic_value_base"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "contiguous_chart_order_sum",
    "positional_segment_share_sum",
    "chart_order_share_to_count",
    "chart_order_remaining_count",
    "sector_share_to_angle",
    "chart_order_adjacent_transfer_gap",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("pie", "donut", "stacked_bar", "stacked_horizontal_bar")
CONTIGUOUS_SCENE_VARIANTS: Tuple[str, ...] = ("pie", "donut")
TRANSFER_GAP_QUERY_IDS: Tuple[str, ...] = (
    "chart_order_adjacent_transfer_gap",
)
PART_WHOLE_QUERY_IDS: Tuple[str, ...] = (
    "chart_order_share_to_count",
    "chart_order_remaining_count",
    "sector_share_to_angle",
)
CIRCULAR_ONLY_QUERY_IDS = frozenset(
    {
        "contiguous_chart_order_sum",
        "positional_segment_share_sum",
        "chart_order_share_to_count",
        "chart_order_remaining_count",
        "sector_share_to_angle",
        "chart_order_adjacent_transfer_gap",
    }
)
COMPACT_VALUE_QUERY_IDS = frozenset(
    {
        "contiguous_chart_order_sum",
        "positional_segment_share_sum",
        *TRANSFER_GAP_QUERY_IDS,
        *PART_WHOLE_QUERY_IDS,
    }
)
CIRCULAR_ORDER_DIRECTIONS: Tuple[str, ...] = ("clockwise", "counterclockwise")
POSITIONAL_RELATIONS: Tuple[str, ...] = (
    "anchor_offset_sum",
    "opposite_neighbor_sum",
)

_DEFAULTS = LabeledChartDefaults(canvas_width=1280, canvas_height=920)
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "composition")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="composition")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="composition", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "contiguous_chart_order_sum": 0.94,
    "positional_segment_share_sum": 0.96,
    "chart_order_share_to_count": 0.96,
    "chart_order_remaining_count": 0.96,
    "sector_share_to_angle": 0.94,
    "chart_order_adjacent_transfer_gap": 0.92,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "pie": 0.52,
    "donut": 0.56,
    "stacked_bar": 0.42,
    "stacked_horizontal_bar": 0.38,
}


def _public_task_param_overrides(task_id: str) -> Dict[str, Any]:
    """Return task-id-specific generation/rendering params for public wrappers."""

    overrides: Dict[str, Any] = {}
    for section in ("generation", "rendering"):
        section_cfg = _TASK_GROUP_DEFAULTS.get(section) if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else None
        if not isinstance(section_cfg, Mapping):
            continue
        task_overrides = section_cfg.get("task_overrides")
        if not isinstance(task_overrides, Mapping):
            continue
        task_values = task_overrides.get(str(task_id))
        if isinstance(task_values, Mapping):
            overrides.update(dict(task_values))
    return overrides


@dataclass(frozen=True)
class _CategorySpec:
    label: str
    value: int
    color_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class _Dataset:
    categories: Tuple[_CategorySpec, ...]
    answer_value: int
    evidence_labels: Tuple[str, ...]
    trace_extras: Dict[str, Any]


@dataclass(frozen=True)
class _TransferQuery:
    source: _CategorySpec
    target: _CategorySpec
    delta: int
    extras: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedShareChart:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: Tuple[int, int, int, int]
    table_bbox_px: Tuple[int, int, int, int]
    chart_traces: Tuple[Dict[str, Any], ...]
    category_traces: Tuple[Dict[str, Any], ...]
    evidence_bbox_by_label: Dict[str, List[float]]
    layout_jitter_meta: Dict[str, Any]


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


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    supported_variants: Sequence[str] = SUPPORTED_SCENE_VARIANTS,
) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=supported_variants,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _axis_is_explicit(params: Mapping[str, Any], *, explicit_key: str, weights_key: str) -> bool:
    return params.get(str(explicit_key)) is not None or params.get(str(weights_key)) is not None


def _task_axis_stride(params: Mapping[str, Any]) -> int:
    if _axis_is_explicit(params, explicit_key="query_id", weights_key="query_id_weights"):
        return 1
    return len(SUPPORTED_QUERY_IDS)


def _scene_axis_stride(params: Mapping[str, Any]) -> int:
    if _axis_is_explicit(params, explicit_key="scene_variant", weights_key="scene_variant_weights"):
        return 1
    return len(SUPPORTED_SCENE_VARIANTS)


def _params_for_scene_axis(params: Mapping[str, Any]) -> Dict[str, Any]:
    shifted = dict(params)
    if "_sample_cursor" not in shifted:
        return shifted
    stride = max(1, int(_task_axis_stride(params)))
    sampling_index = abs(int(shifted["_sample_cursor"]))
    shifted["_sample_cursor"] = int(sampling_index // stride) + int(sampling_index % stride)
    return shifted


def _params_with_shifted_sample_cursor(params: Mapping[str, Any], *, divisor: int) -> Dict[str, Any]:
    shifted = dict(params)
    if "_sample_cursor" not in shifted:
        return shifted
    shifted["_sample_cursor"] = abs(int(shifted["_sample_cursor"])) // max(1, int(divisor))
    return shifted


def _resolve_count_bounds(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, int]:
    min_value = int(params.get(str(min_key), group_default(_GEN_DEFAULTS, str(min_key), int(fallback_min))))
    max_value = int(params.get(str(max_key), group_default(_GEN_DEFAULTS, str(max_key), int(fallback_max))))
    if int(min_value) > int(max_value):
        raise ValueError(f"{min_key} must be <= {max_key}")
    return int(min_value), int(max_value)


def _balanced_int(
    values: Sequence[int],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> int:
    return balanced_choice_from_values(
        [int(value) for value in values],
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )


def _format_quoted(values: Sequence[str]) -> str:
    return ", ".join(f'"{str(value)}"' for value in values)


def _format_offset_list(values: Sequence[int]) -> str:
    phrases = [f"{int(value)} segment{'s' if int(value) != 1 else ''}" for value in values]
    if not phrases:
        return ""
    if len(phrases) == 1:
        return str(phrases[0])
    return f"{', '.join(phrases[:-1])}, and {phrases[-1]}"


def _ordinal(value: int) -> str:
    value_int = int(value)
    if 10 <= int(value_int % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(int(value_int % 10), "th")
    return f"{value_int}{suffix}"


def _largest_rank_descriptor(rank: int) -> str:
    rank_int = int(rank)
    return "largest" if rank_int == 1 else f"{_ordinal(rank_int)} largest"


def _chart_order_phrase(scene_variant: str) -> str:
    if str(scene_variant) in {"pie", "donut"}:
        return "clockwise"
    if str(scene_variant) == "stacked_horizontal_bar":
        return "from left to right"
    if str(scene_variant) == "stacked_bar":
        return "from bottom to top"
    return "in chart order"


def _scene_variants_for_task(query_id: str) -> Tuple[str, ...]:
    if str(query_id) in CIRCULAR_ONLY_QUERY_IDS:
        return CONTIGUOUS_SCENE_VARIANTS
    return SUPPORTED_SCENE_VARIANTS


def _category_count_bounds(params: Mapping[str, Any], *, query_id: str) -> Tuple[int, int]:
    if str(query_id) == "contiguous_chart_order_sum":
        return _resolve_count_bounds(
            params,
            min_key="contiguous_category_count_min",
            max_key="contiguous_category_count_max",
            fallback_min=5,
            fallback_max=10,
        )
    if str(query_id) in TRANSFER_GAP_QUERY_IDS:
        return _resolve_count_bounds(
            params,
            min_key="counterfactual_category_count_min",
            max_key="counterfactual_category_count_max",
            fallback_min=8,
            fallback_max=14,
        )
    if str(query_id) in PART_WHOLE_QUERY_IDS:
        return _resolve_count_bounds(
            params,
            min_key="part_whole_category_count_min",
            max_key="part_whole_category_count_max",
            fallback_min=8,
            fallback_max=14,
        )
    if str(query_id) == "positional_segment_share_sum":
        return _resolve_count_bounds(
            params,
            min_key="positional_category_count_min",
            max_key="positional_category_count_max",
            fallback_min=6,
            fallback_max=12,
        )
    return _resolve_count_bounds(
        params,
        min_key="category_count_min",
        max_key="category_count_max",
        fallback_min=16,
        fallback_max=24,
    )


def _value_bounds(params: Mapping[str, Any], *, query_id: str) -> Tuple[int, int]:
    if str(query_id) in COMPACT_VALUE_QUERY_IDS:
        return _resolve_count_bounds(
            params,
            min_key="compact_value_min",
            max_key="compact_value_max",
            fallback_min=2,
            fallback_max=40,
        )
    return (
        int(params.get("value_min", group_default(_GEN_DEFAULTS, "value_min", 1))),
        int(params.get("value_max", group_default(_GEN_DEFAULTS, "value_max", 18))),
    )


def _palette(count: int, *, instance_seed: int) -> Tuple[Tuple[int, int, int], ...]:
    colors: List[Tuple[int, int, int]] = []
    for index in range(int(count)):
        hue = (0.08 + (float(index) * 0.61803398875)) % 1.0
        lightness = 0.50 + (0.08 if int(index) % 2 else 0.0)
        saturation = 0.64
        red, green, blue = colorsys.hls_to_rgb(float(hue), float(lightness), float(saturation))
        colors.append((int(round(red * 255)), int(round(green * 255)), int(round(blue * 255))))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.palette")
    rng.shuffle(colors)
    return tuple((int(red), int(green), int(blue)) for red, green, blue in colors[: int(count)])


def _sample_categories(
    *,
    category_count: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
) -> Tuple[_CategorySpec, ...]:
    if int(category_count) > len(CHART_LABEL_POOL_UP_TO_25):
        raise ValueError("category_count exceeds available chart label support")
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.categories")
    labels = [str(label) for label in rng.sample(list(CHART_LABEL_POOL_UP_TO_25), k=int(category_count))]
    rng.shuffle(labels)
    value_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.values")
    values = sample_composition_with_sum(
        value_rng,
        target_sum=100,
        count=int(category_count),
        value_min=int(value_min),
        value_max=int(value_max),
    )
    value_rng.shuffle(values)
    colors = _palette(int(category_count), instance_seed=int(instance_seed))
    return tuple(
        _CategorySpec(label=str(label), value=int(value), color_rgb=tuple(colors[index]))
        for index, (label, value) in enumerate(zip(labels, values))
    )


def _sample_ranked_categories(
    *,
    category_count: int,
    instance_seed: int,
) -> Tuple[_CategorySpec, ...]:
    top_rank_count = 7
    if int(category_count) < top_rank_count + 1:
        raise ValueError("ranked share task requires at least 8 categories")
    if int(category_count) > len(CHART_LABEL_POOL_UP_TO_25):
        raise ValueError("category_count exceeds available chart label support")
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.ranked.categories")
    labels = [str(label) for label in rng.sample(list(CHART_LABEL_POOL_UP_TO_25), k=int(category_count))]
    rng.shuffle(labels)
    top_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.ranked.top_values")
    rest_count = int(category_count) - int(top_rank_count)
    top_values: List[int] | None = None
    rest_values: Tuple[int, ...] | None = None
    for attempt in range(120):
        candidate_top = sorted(
            [int(value) for value in top_rng.sample(range(5, 22), k=int(top_rank_count))],
            reverse=True,
        )
        rest_sum = 100 - int(sum(candidate_top))
        rest_value_max = max(1, int(candidate_top[-1]) - 1)
        if int(rest_count) <= int(rest_sum) <= int(rest_count) * int(rest_value_max):
            rest_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.ranked.rest_values.{attempt}")
            rest_values = sample_composition_with_sum(
                rest_rng,
                target_sum=int(rest_sum),
                count=int(rest_count),
                value_min=1,
                value_max=int(rest_value_max),
            )
            top_values = list(candidate_top)
            break
    if top_values is None or rest_values is None:
        raise ValueError("could not construct ranked-share categories with unique top ranks")
    values = [int(value) for value in (*top_values, *rest_values)]
    rng.shuffle(values)
    colors = _palette(int(category_count), instance_seed=int(instance_seed))
    return tuple(
        _CategorySpec(label=str(label), value=int(value), color_rgb=tuple(colors[index]))
        for index, (label, value) in enumerate(zip(labels, values))
    )


def _rank_categories(categories: Sequence[_CategorySpec]) -> Tuple[_CategorySpec, ...]:
    return tuple(
        sorted(
            categories,
            key=lambda category: (-int(category.value), str(category.label)),
        )
    )


def _rank_categories_smallest(categories: Sequence[_CategorySpec]) -> Tuple[_CategorySpec, ...]:
    return tuple(
        sorted(
            categories,
            key=lambda category: (int(category.value), str(category.label)),
        )
    )


def _value_counts(categories: Sequence[_CategorySpec]) -> Dict[int, int]:
    counts: Dict[int, int] = {}
    for category in categories:
        counts[int(category.value)] = int(counts.get(int(category.value), 0)) + 1
    return counts


def _category_has_unique_value(category: _CategorySpec, counts: Mapping[int, int]) -> bool:
    return int(counts.get(int(category.value), 0)) == 1


def _condition_candidates(
    categories: Sequence[_CategorySpec],
    *,
    match_count_min: int,
    match_count_max: int,
) -> List[Tuple[_CategorySpec, _CategorySpec, Tuple[_CategorySpec, ...]]]:
    candidates: List[Tuple[_CategorySpec, _CategorySpec, Tuple[_CategorySpec, ...]]] = []
    for lower_ref in categories:
        for upper_ref in categories:
            if str(lower_ref.label) == str(upper_ref.label) or int(lower_ref.value) >= int(upper_ref.value):
                continue
            selected = tuple(
                category
                for category in categories
                if str(category.label) not in {str(lower_ref.label), str(upper_ref.label)}
                and int(lower_ref.value) < int(category.value) < int(upper_ref.value)
            )
            if int(match_count_min) <= len(selected) <= int(match_count_max):
                candidates.append((lower_ref, upper_ref, selected))
    return candidates


def _sample_conditional_categories_and_query(
    *,
    category_count: int,
    value_min: int,
    value_max: int,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], _CategorySpec, _CategorySpec, Tuple[_CategorySpec, ...], int]:
    match_min, match_max = _resolve_count_bounds(
        params,
        min_key="conditional_match_count_min",
        max_key="conditional_match_count_max",
        fallback_min=4,
        fallback_max=8,
    )
    for attempt in range(80):
        categories = _sample_categories(
            category_count=int(category_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed) + (int(attempt) * 1009),
        )
        candidates = _condition_candidates(
            categories,
            match_count_min=int(match_min),
            match_count_max=int(match_max),
        )
        if not candidates:
            continue
        available_counts = sorted({len(selected) for _, _, selected in candidates})
        target_count = _balanced_int(
            available_counts,
            params=count_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.conditional_match_count",
        )
        filtered_candidates = [
            candidate
            for candidate in candidates
            if len(candidate[2]) == int(target_count)
        ]
        chooser = spawn_rng(int(instance_seed), f"{TASK_ID}.conditional.candidate.{attempt}.{target_count}")
        lower_ref, upper_ref, selected = filtered_candidates[int(chooser.randrange(0, len(filtered_candidates)))]
        return tuple(categories), lower_ref, upper_ref, tuple(selected), int(attempt)
    raise ValueError("could not construct a conditional share query with the configured match-count bounds")


def _resolve_transfer_delta_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    return _resolve_count_bounds(
        params,
        min_key="counterfactual_transfer_delta_min",
        max_key="counterfactual_transfer_delta_max",
        fallback_min=3,
        fallback_max=10,
    )


def _sample_rank_conditioned_transfer(
    categories: Sequence[_CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> _TransferQuery | None:
    delta_min, delta_max = _resolve_transfer_delta_bounds(params)
    rank_min, rank_max = _resolve_count_bounds(
        params,
        min_key="transfer_rank_min",
        max_key="transfer_rank_max",
        fallback_min=1,
        fallback_max=5,
    )
    ranked_largest = _rank_categories(categories)
    ranked_smallest = _rank_categories_smallest(categories)
    max_rank = min(len(categories), int(rank_max))
    options: List[Tuple[int, int, _CategorySpec, _CategorySpec, int]] = []
    for source_rank in range(max(1, int(rank_min)), int(max_rank) + 1):
        for target_rank in range(max(1, int(rank_min)), int(max_rank) + 1):
            source = ranked_largest[int(source_rank) - 1]
            target = ranked_smallest[int(target_rank) - 1]
            if str(source.label) == str(target.label):
                continue
            for delta in range(int(delta_min), int(delta_max) + 1):
                if int(source.value) - int(delta) >= 1:
                    options.append((int(source_rank), int(target_rank), source, target, int(delta)))
    if not options:
        return None
    feasible_deltas = sorted({int(option[4]) for option in options})
    delta = _balanced_int(
        feasible_deltas,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.rank_conditioned_transfer_delta",
    )
    candidates = [option for option in options if int(option[4]) == int(delta)]
    option_index = _balanced_int(
        range(0, len(candidates)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.rank_conditioned_transfer_pair",
    )
    source_rank, target_rank, source, target, _ = candidates[int(option_index)]
    return _TransferQuery(
        source=source,
        target=target,
        delta=int(delta),
        extras={
            "source_rank": int(source_rank),
            "target_rank": int(target_rank),
            "source_rank_text": f"{_ordinal(int(source_rank))} largest",
            "target_rank_text": f"{_ordinal(int(target_rank))} smallest",
            "source_selection_rule": "ranked_largest",
            "target_selection_rule": "ranked_smallest",
            "ranked_largest_labels": [str(category.label) for category in ranked_largest],
            "ranked_smallest_labels": [str(category.label) for category in ranked_smallest],
            "ranked_largest_values": [int(category.value) for category in ranked_largest],
            "ranked_smallest_values": [int(category.value) for category in ranked_smallest],
            "calculation": "rank_conditioned_absolute_gap_after_share_transfer",
        },
    )


def _sample_threshold_conditioned_transfer(
    categories: Sequence[_CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> _TransferQuery | None:
    delta_min, delta_max = _resolve_transfer_delta_bounds(params)
    value_counts = _value_counts(categories)
    options: List[Tuple[_CategorySpec, _CategorySpec, int]] = []
    for source in categories:
        if not _category_has_unique_value(source, value_counts):
            continue
        for target in categories:
            if str(source.label) == str(target.label) or not _category_has_unique_value(target, value_counts):
                continue
            for delta in range(int(delta_min), int(delta_max) + 1):
                if int(source.value) - int(delta) >= 1 and int(target.value) >= 2:
                    options.append((source, target, int(delta)))
    if not options:
        return None
    feasible_deltas = sorted({int(option[2]) for option in options})
    delta = _balanced_int(
        feasible_deltas,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.threshold_conditioned_transfer_delta",
    )
    candidates = [option for option in options if int(option[2]) == int(delta)]
    option_index = _balanced_int(
        range(0, len(candidates)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.threshold_conditioned_transfer_pair",
    )
    source, target, _ = candidates[int(option_index)]
    source_threshold = int(source.value) + 1
    target_threshold = int(target.value) - 1
    return _TransferQuery(
        source=source,
        target=target,
        delta=int(delta),
        extras={
            "source_threshold": int(source_threshold),
            "target_threshold": int(target_threshold),
            "source_selection_rule": "largest_category_below_threshold",
            "target_selection_rule": "smallest_category_above_threshold",
            "calculation": "threshold_conditioned_absolute_gap_after_share_transfer",
        },
    )


def _sample_chart_order_adjacent_transfer(
    categories: Sequence[_CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> _TransferQuery | None:
    delta_min, delta_max = _resolve_transfer_delta_bounds(params)
    options: List[Tuple[str, _CategorySpec, _CategorySpec, int, int, int]] = []
    for source_index, source in enumerate(categories):
        for direction in CIRCULAR_ORDER_DIRECTIONS:
            step = 1 if str(direction) == "clockwise" else -1
            target_index = (int(source_index) + int(step)) % len(categories)
            target = categories[int(target_index)]
            for delta in range(int(delta_min), int(delta_max) + 1):
                if int(source.value) - int(delta) >= 1:
                    options.append(
                        (
                            str(direction),
                            source,
                            target,
                            int(source_index),
                            int(target_index),
                            int(delta),
                        )
                    )
    if not options:
        return None
    feasible_deltas = sorted({int(option[5]) for option in options})
    delta = _balanced_int(
        feasible_deltas,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.chart_order_adjacent_transfer_delta",
    )
    candidates = [option for option in options if int(option[5]) == int(delta)]
    direction_index = _balanced_int(
        range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.chart_order_adjacent_transfer_direction",
    )
    direction = str(CIRCULAR_ORDER_DIRECTIONS[int(direction_index)])
    direction_candidates = [option for option in candidates if str(option[0]) == str(direction)]
    if not direction_candidates:
        direction_candidates = candidates
    option_index = _balanced_int(
        range(0, len(direction_candidates)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.chart_order_adjacent_transfer_source",
    )
    direction, source, target, source_index, target_index, delta = direction_candidates[int(option_index)]
    return _TransferQuery(
        source=source,
        target=target,
        delta=int(delta),
        extras={
            "source_order_direction": str(direction),
            "source_index": int(source_index),
            "target_index": int(target_index),
            "source_selection_rule": "explicit_category_in_chart_order",
            "target_selection_rule": "adjacent_category_in_chart_order",
            "calculation": "adjacent_chart_order_absolute_gap_after_share_transfer",
        },
    )


def _sample_transfer_categories_and_query(
    *,
    query_id: str,
    category_count: int,
    value_min: int,
    value_max: int,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], _TransferQuery, int]:
    selectors = {
        "rank_conditioned_transfer_gap": _sample_rank_conditioned_transfer,
        "threshold_conditioned_transfer_gap": _sample_threshold_conditioned_transfer,
        "chart_order_adjacent_transfer_gap": _sample_chart_order_adjacent_transfer,
    }
    selector = selectors[str(query_id)]
    for attempt in range(160):
        categories = _sample_categories(
            category_count=int(category_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed) + (int(attempt) * 1009),
        )
        query = selector(
            categories,
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed) + int(attempt),
        )
        if query is not None:
            return tuple(categories), query, int(attempt)
    raise ValueError(f"could not construct transfer-gap query for {query_id}")


def _sample_total_count(
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> int:
    configured = params.get("part_whole_total_values", group_default(_GEN_DEFAULTS, "part_whole_total_values", None))
    if configured is None:
        configured = (600, 800, 1000, 1200, 1500, 1800, 2000, 2400, 3000)
    values = [int(value) for value in configured]
    if not values or any(int(value) <= 0 for value in values):
        raise ValueError("part_whole_total_values must contain positive integers")
    if any(int(value) % 100 != 0 for value in values):
        raise ValueError("part_whole_total_values must be multiples of 100 so count answers are integral")
    return _balanced_int(
        values,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.part_whole_total_count",
    )


def _count_from_share(total_count: int, share_value: int) -> int:
    return int((int(total_count) * int(share_value)) // 100)


def _build_selected_share_to_count_query(
    categories: Sequence[_CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], Dict[str, Any]]:
    rank_min, rank_max = _resolve_count_bounds(
        params,
        min_key="part_whole_rank_position_min",
        max_key="part_whole_rank_position_max",
        fallback_min=1,
        fallback_max=6,
    )
    set_size_min, set_size_max = _resolve_count_bounds(
        params,
        min_key="part_whole_rank_set_size_min",
        max_key="part_whole_rank_set_size_max",
        fallback_min=2,
        fallback_max=3,
    )
    feasible_positions = [
        positions
        for set_size in range(max(1, int(set_size_min)), min(int(set_size_max), int(rank_max) - int(rank_min) + 1) + 1)
        for positions in itertools.combinations(range(max(1, int(rank_min)), min(int(rank_max), len(categories)) + 1), int(set_size))
        if all(int(right) - int(left) >= 1 for left, right in zip(positions, positions[1:]))
    ]
    if not feasible_positions:
        raise ValueError("could not construct selected_share_to_count rank positions")
    position_index = _balanced_int(
        range(0, len(feasible_positions)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.part_whole_rank_position_set",
    )
    rank_positions = tuple(int(position) for position in feasible_positions[int(position_index)])
    ranked = _rank_categories(categories)
    selected = tuple(ranked[int(position) - 1] for position in rank_positions)
    return selected, {
        "ranked_labels": [str(category.label) for category in ranked],
        "ranked_values": [int(category.value) for category in ranked],
        "rank_positions": [int(position) for position in rank_positions],
        "rank_position_texts": [_ordinal(int(position)) for position in rank_positions],
        "rank_position_list_text": _format_quoted([_ordinal(int(position)) for position in rank_positions]),
        "rank_direction": "largest",
        "rank_position_set_size": int(len(rank_positions)),
        "rank_position_set_index": int(position_index),
    }


def _build_sector_share_to_angle_query(
    categories: Sequence[_CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], Dict[str, Any]] | None:
    span_min, span_max = _resolve_count_bounds(
        params,
        min_key="part_whole_angle_span_count_min",
        max_key="part_whole_angle_span_count_max",
        fallback_min=2,
        fallback_max=5,
    )
    feasible_span_min = max(1, int(span_min))
    feasible_span_max = min(int(span_max), len(categories) - 1)
    if int(feasible_span_min) > int(feasible_span_max):
        return None
    feasible_spans = range(int(feasible_span_min), int(feasible_span_max) + 1)
    direction_index = _balanced_int(
        range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.part_whole_angle_order_direction",
    )
    order_direction = str(CIRCULAR_ORDER_DIRECTIONS[int(direction_index)])
    step = 1 if str(order_direction) == "clockwise" else -1
    options: List[Tuple[int, int, Tuple[int, ...], int]] = []
    for span_count in feasible_spans:
        for start_index in range(0, len(categories)):
            selected_indices = tuple((int(start_index) + (int(step) * int(offset))) % len(categories) for offset in range(int(span_count)))
            selected_share = int(sum(int(categories[int(index)].value) for index in selected_indices))
            if int(selected_share) % 5 == 0:
                options.append((int(span_count), int(start_index), tuple(int(index) for index in selected_indices), int(selected_share)))
    if not options:
        return None
    option_index = _balanced_int(
        range(0, len(options)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.part_whole_angle_span",
    )
    span_count, start_index, selected_indices, selected_share = options[int(option_index)]
    selected = tuple(categories[int(index)] for index in selected_indices)
    return selected, {
        "start_category": str(selected[0].label),
        "end_category": str(selected[-1].label),
        "start_index": int(start_index),
        "end_index": int(selected_indices[-1]),
        "selected_indices": [int(index) for index in selected_indices],
        "span_count": int(span_count),
        "span_count_range": [int(feasible_span_min), int(feasible_span_max)],
        "chart_order_direction": str(order_direction),
        "selected_share_value": int(selected_share),
        "sector_angle_degrees": int((int(selected_share) * 360) // 100),
    }


def _build_chart_order_span_query(
    categories: Sequence[_CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    namespace_suffix: str,
) -> Tuple[Tuple[_CategorySpec, ...], Dict[str, Any]]:
    span_min, span_max = _resolve_count_bounds(
        params,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
    )
    feasible_span_min = max(2, int(span_min))
    feasible_span_max = min(int(span_max), len(categories) - 1)
    if int(feasible_span_min) > int(feasible_span_max):
        raise ValueError(f"{namespace_suffix} requires enough categories for a non-full chart-order span")
    feasible_spans = range(int(feasible_span_min), int(feasible_span_max) + 1)
    span_count = _balanced_int(
        feasible_spans,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{namespace_suffix}.span_count",
    )
    direction_index = _balanced_int(
        range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{namespace_suffix}.order_direction",
    )
    order_direction = str(CIRCULAR_ORDER_DIRECTIONS[int(direction_index)])
    start_index = _balanced_int(
        range(0, len(categories)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{namespace_suffix}.start_index",
    )
    step = 1 if str(order_direction) == "clockwise" else -1
    selected_indices = tuple((int(start_index) + (int(step) * int(offset))) % len(categories) for offset in range(int(span_count)))
    selected = tuple(categories[int(index)] for index in selected_indices)
    selected_share = int(sum(int(category.value) for category in selected))
    return selected, {
        "start_category": str(selected[0].label),
        "end_category": str(selected[-1].label),
        "start_index": int(start_index),
        "end_index": int(selected_indices[-1]),
        "selected_indices": [int(index) for index in selected_indices],
        "span_count": int(span_count),
        "span_count_range": [int(feasible_span_min), int(feasible_span_max)],
        "chart_order_direction": str(order_direction),
        "selected_share_value": int(selected_share),
    }


def _sample_part_whole_categories_and_query(
    *,
    query_id: str,
    category_count: int,
    value_min: int,
    value_max: int,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], Tuple[_CategorySpec, ...], Dict[str, Any], int]:
    for attempt in range(160):
        categories = _sample_categories(
            category_count=int(category_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed) + (int(attempt) * 1009),
        )
        if str(query_id) in {"chart_order_share_to_count", "chart_order_remaining_count"}:
            selected, query_extras = _build_chart_order_span_query(
                categories,
                params=params,
                count_params=count_params,
                instance_seed=int(instance_seed) + int(attempt),
                min_key="part_whole_span_count_min",
                max_key="part_whole_span_count_max",
                fallback_min=3,
                fallback_max=5,
                namespace_suffix=str(query_id),
            )
            return tuple(categories), tuple(selected), dict(query_extras), int(attempt)
        if str(query_id) == "selected_share_to_count":
            selected, query_extras = _build_selected_share_to_count_query(
                categories,
                params=params,
                count_params=count_params,
                instance_seed=int(instance_seed) + int(attempt),
            )
            return tuple(categories), tuple(selected), dict(query_extras), int(attempt)
        if str(query_id) == "sector_share_to_angle":
            query = _build_sector_share_to_angle_query(
                categories,
                params=params,
                count_params=count_params,
                instance_seed=int(instance_seed) + int(attempt),
            )
            if query is None:
                continue
            selected, query_extras = query
            return tuple(categories), tuple(selected), dict(query_extras), int(attempt)
    raise ValueError(f"could not construct part-whole query for {query_id}")


def _build_ranked_group_share_gap_query(
    categories: Sequence[_CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], Tuple[_CategorySpec, ...], Dict[str, Any]]:
    group_min, group_max = _resolve_count_bounds(
        params,
        min_key="group_gap_group_size_min",
        max_key="group_gap_group_size_max",
        fallback_min=2,
        fallback_max=3,
    )
    feasible_sizes = list(range(max(1, int(group_min)), min(int(group_max), len(categories) // 2) + 1))
    if not feasible_sizes:
        raise ValueError("ranked_group_share_gap requires enough categories for two disjoint groups")
    group_size = _balanced_int(
        feasible_sizes,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.ranked_group_gap_size",
    )
    ranked_largest = _rank_categories(categories)
    ranked_smallest = _rank_categories_smallest(categories)
    largest_group = tuple(ranked_largest[: int(group_size)])
    smallest_group = tuple(ranked_smallest[: int(group_size)])
    largest_share = int(sum(int(category.value) for category in largest_group))
    smallest_share = int(sum(int(category.value) for category in smallest_group))
    return largest_group, smallest_group, {
        "group_size": int(group_size),
        "group_size_range": [int(group_min), int(group_max)],
        "largest_group_labels": [str(category.label) for category in largest_group],
        "smallest_group_labels": [str(category.label) for category in smallest_group],
        "largest_group_share": int(largest_share),
        "smallest_group_share": int(smallest_share),
        "ranked_largest_labels": [str(category.label) for category in ranked_largest],
        "ranked_smallest_labels": [str(category.label) for category in ranked_smallest],
        "ranked_largest_values": [int(category.value) for category in ranked_largest],
        "ranked_smallest_values": [int(category.value) for category in ranked_smallest],
        "calculation": "rank_categories_then_subtract_bottom_group_share_from_top_group_share",
    }


def _sample_known_part_count_categories_and_query(
    *,
    category_count: int,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], Tuple[_CategorySpec, ...], _CategorySpec, Dict[str, Any], int]:
    for attempt in range(160):
        categories = _sample_ranked_categories(
            category_count=int(category_count),
            instance_seed=int(instance_seed) + (int(attempt) * 1009),
        )
        selected, query_extras = _build_selected_share_to_count_query(
            categories,
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed) + int(attempt),
        )
        selected_labels = {str(category.label) for category in selected}
        candidates = [category for category in categories if str(category.label) not in selected_labels]
        if not candidates:
            continue
        candidate_index = _balanced_int(
            range(0, len(candidates)),
            params=count_params,
            instance_seed=int(instance_seed) + int(attempt),
            namespace=f"{TASK_ID}.known_part_category",
        )
        known_category = candidates[int(candidate_index)]
        total_count = _sample_total_count(
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed) + int(attempt),
        )
        known_count = _count_from_share(int(total_count), int(known_category.value))
        selected_share = int(sum(int(category.value) for category in selected))
        return tuple(categories), tuple(selected), known_category, {
            **dict(query_extras),
            "known_count_category": str(known_category.label),
            "known_count_value": int(known_count),
            "known_category_share_value": int(known_category.value),
            "inferred_total_count": int(total_count),
            "selected_share_value": int(selected_share),
            "known_part_sampling_attempt": int(attempt),
            "calculation": "infer_total_from_one_known_category_count_then_convert_ranked_group_share_to_count",
        }, int(attempt)
    raise ValueError("could not construct known_part_to_group_count query")


def _build_cumulative_threshold_query(
    categories: Sequence[_CategorySpec],
    *,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], Dict[str, Any]] | None:
    count_min, count_max = _resolve_count_bounds(
        params,
        min_key="cumulative_threshold_answer_count_min",
        max_key="cumulative_threshold_answer_count_max",
        fallback_min=3,
        fallback_max=6,
    )
    threshold_min, threshold_max = _resolve_count_bounds(
        params,
        min_key="cumulative_threshold_min",
        max_key="cumulative_threshold_max",
        fallback_min=45,
        fallback_max=75,
    )
    ranked = _rank_categories(categories)
    prefix_sums: List[int] = []
    running = 0
    for category in ranked:
        running += int(category.value)
        prefix_sums.append(int(running))

    options: List[Tuple[int, int, int]] = []
    for answer_count in range(max(1, int(count_min)), min(int(count_max), len(ranked)) + 1):
        previous_sum = int(prefix_sums[int(answer_count) - 2]) if int(answer_count) > 1 else 0
        current_sum = int(prefix_sums[int(answer_count) - 1])
        threshold_low = max(int(threshold_min), int(previous_sum) + 1)
        threshold_high = min(int(threshold_max), int(current_sum))
        if int(threshold_low) <= int(threshold_high):
            options.append((int(answer_count), int(threshold_low), int(threshold_high)))
    if not options:
        return None

    feasible_counts = sorted({int(option[0]) for option in options})
    answer_count = _balanced_int(
        feasible_counts,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.cumulative_threshold_answer_count",
    )
    intervals = [(int(low), int(high)) for count, low, high in options if int(count) == int(answer_count)]
    interval_index = _balanced_int(
        range(0, len(intervals)),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.cumulative_threshold_interval",
    )
    threshold_low, threshold_high = intervals[int(interval_index)]
    threshold_value = _balanced_int(
        range(int(threshold_low), int(threshold_high) + 1),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.cumulative_threshold_value",
    )
    selected = tuple(ranked[: int(answer_count)])
    previous_cumulative = int(prefix_sums[int(answer_count) - 2]) if int(answer_count) > 1 else 0
    selected_share = int(prefix_sums[int(answer_count) - 1])
    return selected, {
        "threshold_value": int(threshold_value),
        "threshold_range": [int(threshold_min), int(threshold_max)],
        "cumulative_answer_count": int(answer_count),
        "cumulative_answer_count_range": [int(count_min), int(count_max)],
        "previous_cumulative_share": int(previous_cumulative),
        "selected_share_value": int(selected_share),
        "ranked_labels": [str(category.label) for category in ranked],
        "ranked_values": [int(category.value) for category in ranked],
        "calculation": "rank_categories_largest_to_smallest_then_count_prefix_to_reach_threshold",
    }


def _sample_cumulative_threshold_categories_and_query(
    *,
    category_count: int,
    params: Mapping[str, Any],
    count_params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[_CategorySpec, ...], Tuple[_CategorySpec, ...], Dict[str, Any], int]:
    for attempt in range(160):
        categories = _sample_ranked_categories(
            category_count=int(category_count),
            instance_seed=int(instance_seed) + (int(attempt) * 1009),
        )
        query = _build_cumulative_threshold_query(
            categories,
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed) + int(attempt),
        )
        if query is None:
            continue
        selected, query_extras = query
        return tuple(categories), tuple(selected), dict(query_extras), int(attempt)
    raise ValueError("could not construct cumulative_share_threshold_count query")


def _evidence_value_for_label(
    label: str,
    *,
    extras: Mapping[str, Any],
    values_by_label: Mapping[str, int],
) -> int:
    if str(label) == "__total__":
        return int(extras["total_count"])
    if str(label) == "__known_count__":
        return int(extras["known_count_value"])
    return int(values_by_label[str(label)])


def _build_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Dataset:
    category_min, category_max = _category_count_bounds(params, query_id=str(query_id))
    count_params = _params_with_shifted_sample_cursor(
        params,
        divisor=int(_task_axis_stride(params) * _scene_axis_stride(params)),
    )
    category_count_support = list(range(int(category_min), int(category_max) + 1))
    if str(query_id) == "positional_segment_share_sum":
        category_count_support = [int(value) for value in category_count_support if int(value) % 2 == 0]
        if not category_count_support:
            raise ValueError("positional_segment_share_sum requires at least one even category count")
    category_count = _balanced_int(
        category_count_support,
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.category_count",
    )
    value_min, value_max = _value_bounds(params, query_id=str(query_id))
    transfer_query: _TransferQuery | None = None
    transfer_sampling_attempt: int | None = None
    part_whole_selected: Tuple[_CategorySpec, ...] = ()
    part_whole_query_extras: Dict[str, Any] = {}
    part_whole_sampling_attempt: int | None = None
    ranked_group_largest: Tuple[_CategorySpec, ...] = ()
    ranked_group_smallest: Tuple[_CategorySpec, ...] = ()
    ranked_group_query_extras: Dict[str, Any] = {}
    known_part_selected: Tuple[_CategorySpec, ...] = ()
    known_part_category: _CategorySpec | None = None
    known_part_query_extras: Dict[str, Any] = {}
    known_part_sampling_attempt: int | None = None
    cumulative_selected: Tuple[_CategorySpec, ...] = ()
    cumulative_query_extras: Dict[str, Any] = {}
    cumulative_sampling_attempt: int | None = None
    if str(query_id) == "ranked_position_set_sum":
        categories = _sample_ranked_categories(
            category_count=int(category_count),
            instance_seed=int(instance_seed),
        )
    elif str(query_id) == "conditional_share_sum":
        categories = ()
    elif str(query_id) in TRANSFER_GAP_QUERY_IDS:
        categories, transfer_query, transfer_sampling_attempt = _sample_transfer_categories_and_query(
            query_id=str(query_id),
            category_count=int(category_count),
            value_min=int(value_min),
            value_max=int(value_max),
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed),
        )
    elif str(query_id) in PART_WHOLE_QUERY_IDS:
        categories, part_whole_selected, part_whole_query_extras, part_whole_sampling_attempt = _sample_part_whole_categories_and_query(
            query_id=str(query_id),
            category_count=int(category_count),
            value_min=int(value_min),
            value_max=int(value_max),
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed),
        )
    elif str(query_id) == "ranked_group_share_gap":
        categories = _sample_ranked_categories(
            category_count=int(category_count),
            instance_seed=int(instance_seed),
        )
        ranked_group_largest, ranked_group_smallest, ranked_group_query_extras = _build_ranked_group_share_gap_query(
            categories,
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed),
        )
    elif str(query_id) == "known_part_to_group_count":
        categories, known_part_selected, known_part_category, known_part_query_extras, known_part_sampling_attempt = _sample_known_part_count_categories_and_query(
            category_count=int(category_count),
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed),
        )
    elif str(query_id) == "cumulative_share_threshold_count":
        categories, cumulative_selected, cumulative_query_extras, cumulative_sampling_attempt = _sample_cumulative_threshold_categories_and_query(
            category_count=int(category_count),
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed),
        )
    else:
        categories = _sample_categories(
            category_count=int(category_count),
            value_min=int(value_min),
            value_max=int(value_max),
            instance_seed=int(instance_seed),
        )

    if str(query_id) == "conditional_share_sum":
        categories, lower_ref, upper_ref, selected, sampling_attempt = _sample_conditional_categories_and_query(
            category_count=int(category_count),
            value_min=int(value_min),
            value_max=int(value_max),
            params=params,
            count_params=count_params,
            instance_seed=int(instance_seed),
        )

    labels = tuple(str(category.label) for category in categories)
    values_by_label = {str(category.label): int(category.value) for category in categories}
    extras: Dict[str, Any] = {
        "category_count": int(category_count),
        "category_count_range": [int(category_min), int(category_max)],
        "value_min": int(value_min),
        "value_max": int(value_max),
        "category_values": {str(label): int(values_by_label[str(label)]) for label in labels},
        "chart_order_labels": [str(label) for label in labels],
        "table_order_labels": [str(label) for label in sorted(labels)],
    }

    if str(query_id) == "ranked_position_set_sum":
        rank_min, rank_max = _resolve_count_bounds(
            params,
            min_key="rank_position_min",
            max_key="rank_position_max",
            fallback_min=1,
            fallback_max=7,
        )
        set_size_min, set_size_max = _resolve_count_bounds(
            params,
            min_key="rank_position_set_size_min",
            max_key="rank_position_set_size_max",
            fallback_min=3,
            fallback_max=3,
        )
        feasible_positions = [
            positions
            for set_size in range(max(1, int(set_size_min)), min(int(set_size_max), int(rank_max) - int(rank_min) + 1) + 1)
            for positions in itertools.combinations(range(max(1, int(rank_min)), int(rank_max) + 1), int(set_size))
            if all(int(right) - int(left) >= 2 for left, right in zip(positions, positions[1:]))
        ]
        position_index = _balanced_int(
            range(len(feasible_positions)),
            params=count_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.rank_position_set",
        )
        rank_positions = tuple(int(position) for position in feasible_positions[int(position_index)])
        ranked = _rank_categories(categories)
        selected_categories = tuple(ranked[int(position) - 1] for position in rank_positions)
        selected = tuple(str(category.label) for category in selected_categories)
        answer_value = int(sum(values_by_label[str(label)] for label in selected))
        extras.update(
            {
                "category_list": [str(label) for label in selected],
                "ranked_labels": [str(category.label) for category in ranked],
                "ranked_values": [int(category.value) for category in ranked],
                "rank_positions": [int(position) for position in rank_positions],
                "rank_position_texts": [_ordinal(int(position)) for position in rank_positions],
                "rank_position_list_text": _format_quoted([_ordinal(int(position)) for position in rank_positions]),
                "rank_direction": "largest",
                "rank_position_set_size": int(len(rank_positions)),
                "rank_position_set_index": int(position_index),
                "calculation": "rank_categories_by_share_then_sum_noncontiguous_rank_positions",
            }
        )
        evidence_labels = tuple(str(label) for label in selected)
    elif str(query_id) == "conditional_share_sum":
        selected_labels = tuple(str(category.label) for category in selected)
        answer_value = int(sum(int(category.value) for category in selected))
        extras.update(
            {
                "category_list": [str(label) for label in selected_labels],
                "lower_reference_category": str(lower_ref.label),
                "upper_reference_category": str(upper_ref.label),
                "lower_reference_value": int(lower_ref.value),
                "upper_reference_value": int(upper_ref.value),
                "matching_category_count": int(len(selected)),
                "matching_category_values": [int(category.value) for category in selected],
                "conditional_sampling_attempt": int(sampling_attempt),
                "calculation": "filter_categories_between_two_reference_shares_then_sum",
            }
        )
        evidence_labels = (str(lower_ref.label), str(upper_ref.label), *selected_labels)
    elif str(query_id) == "contiguous_chart_order_sum":
        span_min, span_max = _resolve_count_bounds(
            params,
            min_key="contiguous_span_count_min",
            max_key="contiguous_span_count_max",
            fallback_min=3,
            fallback_max=6,
        )
        feasible_span_min = max(2, int(span_min))
        feasible_span_max = min(int(span_max), int(category_count) - 1)
        if int(feasible_span_min) > int(feasible_span_max):
            raise ValueError("contiguous_chart_order_sum requires enough categories for a non-full chart-order span")
        feasible_spans = range(int(feasible_span_min), int(feasible_span_max) + 1)
        span_count = _balanced_int(
            feasible_spans,
            params=count_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.contiguous_span_count",
        )
        direction_index = _balanced_int(
            range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
            params=count_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.contiguous_order_direction",
        )
        order_direction = str(CIRCULAR_ORDER_DIRECTIONS[int(direction_index)])
        start_index = _balanced_int(
            range(0, int(category_count)),
            params=count_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.contiguous_start_index",
        )
        step = 1 if str(order_direction) == "clockwise" else -1
        selected_indices = tuple((int(start_index) + (int(step) * int(offset))) % int(category_count) for offset in range(int(span_count)))
        selected_categories = tuple(categories[int(index)] for index in selected_indices)
        selected = tuple(str(category.label) for category in selected_categories)
        answer_value = int(sum(int(category.value) for category in selected_categories))
        extras.update(
            {
                "category_list": [str(label) for label in selected],
                "start_category": str(selected[0]),
                "end_category": str(selected[-1]),
                "start_index": int(start_index),
                "end_index": int(selected_indices[-1]),
                "selected_indices": [int(index) for index in selected_indices],
                "span_count": int(span_count),
                "span_count_range": [int(feasible_span_min), int(feasible_span_max)],
                "chart_order_direction": str(order_direction),
                "calculation": "sum_contiguous_categories_in_circular_chart_order",
            }
        )
        evidence_labels = tuple(str(label) for label in selected)
    elif str(query_id) == "positional_segment_share_sum":
        relation_index = _balanced_int(
            range(0, len(POSITIONAL_RELATIONS)),
            params=count_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.positional_relation",
        )
        position_relation = str(POSITIONAL_RELATIONS[int(relation_index)])
        relation_seed = int(instance_seed) + (int(relation_index) * 10007)
        relation_rng = spawn_rng(int(relation_seed), f"{TASK_ID}.positional.{position_relation}")
        evidence_prefix: Tuple[str, ...] = ()
        order_direction = "clockwise"
        anchor_label: str | None = None

        if position_relation == "anchor_offset_sum":
            anchor_index = int(relation_rng.randrange(0, int(category_count)))
            anchor_label = str(categories[int(anchor_index)].label)
            direction_index = _balanced_int(
                range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
                params=count_params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.positional.anchor_direction",
            )
            order_direction = str(CIRCULAR_ORDER_DIRECTIONS[int(direction_index)])
            feasible_offsets = [
                offsets
                for offsets in itertools.combinations(range(1, int(category_count)), 2)
                if int(offsets[1]) - int(offsets[0]) >= 2
            ]
            offset_index = _balanced_int(
                range(0, len(feasible_offsets)),
                params=count_params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.positional.anchor_offsets",
            )
            selected_offsets = tuple(int(offset) for offset in feasible_offsets[int(offset_index)])
            step = 1 if str(order_direction) == "clockwise" else -1
            selected_indices = tuple((int(anchor_index) + (int(step) * int(offset))) % int(category_count) for offset in selected_offsets)
            selected_categories = tuple(categories[int(index)] for index in selected_indices)
            selected = tuple(str(category.label) for category in selected_categories)
            evidence_prefix = (str(anchor_label),)
            positional_instruction = (
                f"Starting at category {anchor_label} and moving {order_direction}, use the segments "
                f"{_format_offset_list(selected_offsets)} away from that anchor. Do not include category {anchor_label}."
            )
            extras.update(
                {
                    "anchor_category": str(anchor_label),
                    "anchor_index": int(anchor_index),
                    "selected_offsets": [int(offset) for offset in selected_offsets],
                    "offset_list_text": _format_offset_list(selected_offsets),
                    "offset_index": int(offset_index),
                }
            )
        elif position_relation == "opposite_neighbor_sum":
            anchor_index = int(relation_rng.randrange(0, int(category_count)))
            anchor_label = str(categories[int(anchor_index)].label)
            direction_index = _balanced_int(
                range(0, len(CIRCULAR_ORDER_DIRECTIONS)),
                params=count_params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.positional.opposite_direction",
            )
            order_direction = str(CIRCULAR_ORDER_DIRECTIONS[int(direction_index)])
            step = 1 if str(order_direction) == "clockwise" else -1
            opposite_index = (int(anchor_index) + (int(category_count) // 2)) % int(category_count)
            neighbor_index = (int(opposite_index) + int(step)) % int(category_count)
            selected_indices = (int(opposite_index), int(neighbor_index))
            selected_categories = tuple(categories[int(index)] for index in selected_indices)
            selected = tuple(str(category.label) for category in selected_categories)
            evidence_prefix = (str(anchor_label),)
            positional_instruction = (
                f"Find the segment opposite category {anchor_label}, then also use the segment immediately "
                f"{order_direction} from that opposite segment."
            )
            extras.update(
                {
                    "anchor_category": str(anchor_label),
                    "anchor_index": int(anchor_index),
                    "opposite_index": int(opposite_index),
                    "opposite_category": str(categories[int(opposite_index)].label),
                    "neighbor_index": int(neighbor_index),
                    "neighbor_category": str(categories[int(neighbor_index)].label),
                }
            )
        else:
            raise ValueError(f"unsupported positional relation: {position_relation}")

        answer_value = int(sum(int(category.value) for category in selected_categories))
        extras.update(
            {
                "category_list": [str(label) for label in selected],
                "selected_indices": [int(index) for index in selected_indices],
                "position_relation": str(position_relation),
                "position_relation_index": int(relation_index),
                "positional_instruction": str(positional_instruction),
                "chart_order_direction": str(order_direction),
                "calculation": "select_segments_by_circular_position_then_sum_shares",
            }
        )
        evidence_labels = (*evidence_prefix, *tuple(str(label) for label in selected))
    elif str(query_id) == "ranked_group_share_gap":
        largest_group = tuple(ranked_group_largest)
        smallest_group = tuple(ranked_group_smallest)
        largest_labels = tuple(str(category.label) for category in largest_group)
        smallest_labels = tuple(str(category.label) for category in smallest_group)
        largest_share = int(sum(int(category.value) for category in largest_group))
        smallest_share = int(sum(int(category.value) for category in smallest_group))
        answer_value = int(largest_share - smallest_share)
        extras.update(
            {
                "category_list": [*list(largest_labels), *list(smallest_labels)],
                "largest_group_share": int(largest_share),
                "smallest_group_share": int(smallest_share),
                **dict(ranked_group_query_extras),
            }
        )
        evidence_labels = (*largest_labels, *smallest_labels)
    elif str(query_id) == "known_part_to_group_count":
        if known_part_category is None:
            raise ValueError("known part category was not constructed")
        selected_categories = tuple(known_part_selected)
        selected = tuple(str(category.label) for category in selected_categories)
        selected_share = int(sum(int(category.value) for category in selected_categories))
        inferred_total_count = int(known_part_query_extras["inferred_total_count"])
        answer_value = _count_from_share(int(inferred_total_count), int(selected_share))
        extras.update(
            {
                "category_list": [str(label) for label in selected],
                "selected_share_value": int(selected_share),
                "known_part_sampling_attempt": int(known_part_sampling_attempt or 0),
                **dict(known_part_query_extras),
            }
        )
        evidence_labels = ("__known_count__", str(known_part_category.label), *tuple(str(label) for label in selected))
    elif str(query_id) == "cumulative_share_threshold_count":
        selected_categories = tuple(cumulative_selected)
        selected = tuple(str(category.label) for category in selected_categories)
        answer_value = int(len(selected_categories))
        extras.update(
            {
                "category_list": [str(label) for label in selected],
                "cumulative_sampling_attempt": int(cumulative_sampling_attempt or 0),
                **dict(cumulative_query_extras),
            }
        )
        evidence_labels = tuple(str(label) for label in selected)
    elif str(query_id) in TRANSFER_GAP_QUERY_IDS:
        if transfer_query is None:
            raise ValueError("transfer query was not constructed")
        source = transfer_query.source
        target = transfer_query.target
        delta = int(transfer_query.delta)
        source_new = int(source.value) - int(delta)
        target_new = int(target.value) + int(delta)
        answer_value = abs(int(target_new) - int(source_new))
        extras.update(
            {
                "source_category": str(source.label),
                "target_category": str(target.label),
                "transfer_delta": int(delta),
                "source_original_value": int(source.value),
                "target_original_value": int(target.value),
                "source_new_value": int(source_new),
                "target_new_value": int(target_new),
                "transfer_sampling_attempt": int(transfer_sampling_attempt or 0),
                **dict(transfer_query.extras),
            }
        )
        evidence_labels = (str(source.label), str(target.label))
    elif str(query_id) in PART_WHOLE_QUERY_IDS:
        selected_categories = tuple(part_whole_selected)
        selected = tuple(str(category.label) for category in selected_categories)
        selected_share = int(sum(int(category.value) for category in selected_categories))
        total_count = 0
        if str(query_id) in {
            "selected_share_to_count",
            "excluded_share_to_remaining_count",
            "chart_order_share_to_count",
            "chart_order_remaining_count",
        }:
            total_count = _sample_total_count(
                params=params,
                count_params=count_params,
                instance_seed=int(instance_seed),
            )
        if str(query_id) in {"selected_share_to_count", "chart_order_share_to_count"}:
            answer_value = _count_from_share(int(total_count), int(selected_share))
            extras.update(
                {
                    "category_list": [str(label) for label in selected],
                    "selected_share_value": int(selected_share),
                    "total_count": int(total_count),
                    "part_whole_sampling_attempt": int(part_whole_sampling_attempt or 0),
                    "calculation": (
                        "sum_chart_order_category_shares_then_convert_to_total_count"
                        if str(query_id) == "chart_order_share_to_count"
                        else "sum_ranked_category_shares_then_convert_to_total_count"
                    ),
                    **dict(part_whole_query_extras),
                }
            )
            evidence_labels = ("__total__", *tuple(str(label) for label in selected))
        elif str(query_id) in {"excluded_share_to_remaining_count", "chart_order_remaining_count"}:
            remaining_share = int(100 - int(selected_share))
            answer_value = _count_from_share(int(total_count), int(remaining_share))
            extras.update(
                {
                    "category_list": [str(label) for label in selected],
                    "selected_share_value": int(selected_share),
                    "remaining_share_value": int(remaining_share),
                    "total_count": int(total_count),
                    "part_whole_sampling_attempt": int(part_whole_sampling_attempt or 0),
                    "calculation": (
                        "exclude_chart_order_category_shares_then_convert_remaining_share_to_count"
                        if str(query_id) == "chart_order_remaining_count"
                        else "exclude_conditioned_category_shares_then_convert_remaining_share_to_count"
                    ),
                    **dict(part_whole_query_extras),
                }
            )
            if str(query_id) == "chart_order_remaining_count":
                evidence_labels = ("__total__", *tuple(str(label) for label in selected))
            else:
                evidence_labels = (
                    "__total__",
                    str(extras["lower_reference_category"]),
                    str(extras["upper_reference_category"]),
                    *tuple(str(label) for label in selected),
                )
        elif str(query_id) == "sector_share_to_angle":
            if int(selected_share) % 5 != 0:
                raise ValueError("sector_share_to_angle requires selected share to be divisible by 5")
            answer_value = int((int(selected_share) * 360) // 100)
            extras.update(
                {
                    "category_list": [str(label) for label in selected],
                    "selected_share_value": int(selected_share),
                    "part_whole_sampling_attempt": int(part_whole_sampling_attempt or 0),
                    "calculation": "convert_circular_sector_share_to_degrees",
                    **dict(part_whole_query_extras),
                }
            )
            evidence_labels = tuple(str(label) for label in selected)
        else:
            raise ValueError(f"unsupported part-whole variant: {query_id}")
    else:
        raise ValueError(f"unsupported query_id: {query_id}")

    extras["answer_value"] = int(answer_value)
    extras["evidence_labels"] = [str(label) for label in evidence_labels]
    extras["evidence_values"] = [
        _evidence_value_for_label(str(label), extras=extras, values_by_label=values_by_label)
        for label in evidence_labels
    ]
    return _Dataset(
        categories=tuple(categories),
        answer_value=int(answer_value),
        evidence_labels=tuple(str(label) for label in evidence_labels),
        trace_extras=dict(extras),
    )


def _text_bbox_at_origin(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: Any,
    *,
    stroke_width: int = 0,
) -> Tuple[float, float, float, float]:
    try:
        bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
        return float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        pad = float(max(0, int(stroke_width)))
        return float(-pad), float(-pad), float(width + pad), float(height + pad)


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: Any, *, stroke_width: int = 0) -> Tuple[float, float]:
    bbox = _text_bbox_at_origin(draw, str(text), font, stroke_width=max(0, int(stroke_width)))
    return float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1])


def _draw_text(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    fill: Tuple[int, int, int],
    *,
    stroke_width: int = 0,
    stroke_fill: Tuple[int, int, int] = (255, 255, 255),
) -> List[float]:
    draw.text(
        (float(xy[0]), float(xy[1])),
        str(text),
        font=font,
        fill=fill,
        stroke_width=max(0, int(stroke_width)),
        stroke_fill=stroke_fill,
    )
    raw = _text_bbox_at_origin(draw, str(text), font, stroke_width=max(0, int(stroke_width)))
    return [
        float(xy[0]) + float(raw[0]),
        float(xy[1]) + float(raw[1]),
        float(xy[0]) + float(raw[2]),
        float(xy[1]) + float(raw[3]),
    ]


def _draw_centered(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    fill: Tuple[int, int, int],
    *,
    stroke_width: int = 0,
    stroke_fill: Tuple[int, int, int] = (255, 255, 255),
) -> List[float]:
    raw = _text_bbox_at_origin(draw, str(text), font, stroke_width=max(0, int(stroke_width)))
    width = float(raw[2] - raw[0])
    height = float(raw[3] - raw[1])
    left = float(xy[0]) - (width / 2.0) - float(raw[0])
    top = float(xy[1]) - (height / 2.0) - float(raw[1])
    return _draw_text(
        draw,
        (float(left), float(top)),
        str(text),
        font,
        fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )


def _centered_text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    *,
    stroke_width: int = 0,
) -> List[float]:
    raw = _text_bbox_at_origin(draw, str(text), font, stroke_width=max(0, int(stroke_width)))
    width = float(raw[2] - raw[0])
    height = float(raw[3] - raw[1])
    left = float(xy[0]) - (width / 2.0) - float(raw[0])
    top = float(xy[1]) - (height / 2.0) - float(raw[1])
    return [
        float(left) + float(raw[0]),
        float(top) + float(raw[1]),
        float(left) + float(raw[2]),
        float(top) + float(raw[3]),
    ]


def _bboxes_overlap(left: Sequence[float], right: Sequence[float], *, padding: float = 0.0) -> bool:
    return not (
        float(left[2]) + float(padding) <= float(right[0])
        or float(right[2]) + float(padding) <= float(left[0])
        or float(left[3]) + float(padding) <= float(right[1])
        or float(right[3]) + float(padding) <= float(left[1])
    )


def _contrast_text(color: Sequence[int]) -> Tuple[int, int, int]:
    red, green, blue = (int(color[0]), int(color[1]), int(color[2]))
    luminance = (0.299 * float(red)) + (0.587 * float(green)) + (0.114 * float(blue))
    return (22, 25, 32) if float(luminance) > 150.0 else (255, 255, 255)


def _render_pie_like(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: _Dataset,
    scene_variant: str,
    chart_bbox: Tuple[float, float, float, float],
    text_color: Tuple[int, int, int],
    panel_fill: Tuple[int, int, int],
    outline_width: int,
    label_font: Any,
) -> Tuple[List[Dict[str, Any]], Tuple[int, int, int, int]]:
    x0, y0, x1, y1 = [float(value) for value in chart_bbox]
    center = ((float(x0) + float(x1)) / 2.0, (float(y0) + float(y1)) / 2.0 + 8.0)
    radius = min((float(x1) - float(x0)) * 0.42, (float(y1) - float(y0)) * 0.43)
    pie_box = (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius)
    start_angle = -90.0
    min_label_share = 5
    label_specs: List[Dict[str, Any]] = []
    candidate_bboxes: List[List[float]] = []
    label_radius = float(radius) * (0.72 if str(scene_variant) == "pie" else 0.78)
    for category in dataset.categories:
        share = int(category.value)
        end_angle = float(start_angle + (float(share) * 3.6))
        mid_angle = math.radians((float(start_angle) + float(end_angle)) / 2.0)
        label_x = float(center[0] + (math.cos(mid_angle) * label_radius))
        label_y = float(center[1] + (math.sin(mid_angle) * label_radius))
        candidate_bbox = _centered_text_bbox(
            draw,
            (label_x, label_y),
            str(category.label),
            label_font,
            stroke_width=2,
        )
        label_specs.append(
            {
                "category": category,
                "start_angle": float(start_angle),
                "end_angle": float(end_angle),
                "label_x": float(label_x),
                "label_y": float(label_y),
                "candidate_bbox": list(candidate_bbox),
            }
        )
        candidate_bboxes.append(list(candidate_bbox))
        start_angle = float(end_angle)
    labels_fit = all(int(category.value) >= int(min_label_share) for category in dataset.categories)
    if bool(labels_fit):
        for left_index, left_bbox in enumerate(candidate_bboxes):
            for right_bbox in candidate_bboxes[int(left_index) + 1 :]:
                if _bboxes_overlap(left_bbox, right_bbox, padding=4.0):
                    labels_fit = False
                    break
            if not labels_fit:
                break

    start_angle = -90.0
    traces: List[Dict[str, Any]] = []
    for spec in label_specs:
        category = spec["category"]
        share = int(category.value)
        end_angle = float(start_angle + (float(share) * 3.6))
        draw.pieslice(
            pie_box,
            start=float(start_angle),
            end=float(end_angle),
            fill=tuple(category.color_rgb),
            outline=(255, 255, 255),
            width=max(1, int(outline_width)),
        )
        if str(scene_variant) == "donut":
            inner = float(radius) * 0.52
            draw.ellipse(
                (center[0] - inner, center[1] - inner, center[0] + inner, center[1] + inner),
                fill=panel_fill,
                outline=panel_fill,
            )
        label_x = float(spec["label_x"])
        label_y = float(spec["label_y"])
        label_bbox: List[float] | None = None
        if bool(labels_fit):
            label_bbox = _draw_centered(
                draw,
                (label_x, label_y),
                str(category.label),
                label_font,
                _contrast_text(category.color_rgb),
                stroke_width=2,
                stroke_fill=(32, 36, 44) if _contrast_text(category.color_rgb) == (255, 255, 255) else (255, 255, 255),
            )
        traces.append(
            {
                "label": str(category.label),
                "value": int(category.value),
                "fill_rgb": [int(channel) for channel in category.color_rgb],
                "slice_angle_start": float(start_angle),
                "slice_angle_end": float(end_angle),
                "slice_center_px": [float(label_x), float(label_y)],
                "label_bbox_px": list(label_bbox) if label_bbox is not None else None,
                "label_display_mode": "all" if bool(labels_fit) else "none",
            }
        )
        start_angle = float(end_angle)
    if str(scene_variant) == "donut":
        _draw_centered(draw, center, "100%", label_font, text_color)
    return traces, tuple(int(round(value)) for value in pie_box)


def _render_stacked(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: _Dataset,
    scene_variant: str,
    chart_bbox: Tuple[float, float, float, float],
    grid_color: Tuple[int, int, int],
    outline_width: int,
    label_font: Any,
) -> Tuple[List[Dict[str, Any]], Tuple[int, int, int, int]]:
    x0, y0, x1, y1 = [float(value) for value in chart_bbox]
    traces: List[Dict[str, Any]] = []
    if str(scene_variant) == "stacked_horizontal_bar":
        bar_x0 = float(x0) + 34.0
        bar_x1 = float(x1) - 34.0
        bar_y0 = (float(y0) + float(y1)) / 2.0 - 52.0
        bar_y1 = (float(y0) + float(y1)) / 2.0 + 52.0
        draw.line((bar_x0, bar_y1 + 22.0, bar_x1, bar_y1 + 22.0), fill=grid_color, width=2)
        for fraction, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
            tick_x = float(bar_x0 + ((bar_x1 - bar_x0) * float(fraction)))
            draw.line((tick_x, bar_y1 + 15.0, tick_x, bar_y1 + 28.0), fill=grid_color, width=2)
            _draw_centered(draw, (tick_x, bar_y1 + 47.0), label, label_font, (64, 68, 76))
        cursor = float(bar_x0)
        for category in dataset.categories:
            seg_width = (float(bar_x1) - float(bar_x0)) * float(category.value) / 100.0
            seg_x1 = float(cursor + seg_width)
            bbox = [float(cursor), float(bar_y0), float(seg_x1), float(bar_y1)]
            draw.rectangle(tuple(bbox), fill=tuple(category.color_rgb), outline=(255, 255, 255), width=max(1, int(outline_width)))
            label_bbox = None
            if float(seg_width) >= 28.0:
                label_bbox = _draw_centered(
                    draw,
                    ((float(cursor) + float(seg_x1)) / 2.0, (float(bar_y0) + float(bar_y1)) / 2.0),
                    str(category.label),
                    label_font,
                    _contrast_text(category.color_rgb),
                    stroke_width=1,
                    stroke_fill=(32, 36, 44) if _contrast_text(category.color_rgb) == (255, 255, 255) else (255, 255, 255),
                )
            traces.append(
                {
                    "label": str(category.label),
                    "value": int(category.value),
                    "fill_rgb": [int(channel) for channel in category.color_rgb],
                    "segment_bbox_px": list(bbox),
                    "label_bbox_px": list(label_bbox) if label_bbox is not None else None,
                }
            )
            cursor = float(seg_x1)
        return traces, (int(round(bar_x0)), int(round(bar_y0)), int(round(bar_x1)), int(round(bar_y1)))

    bar_x0 = (float(x0) + float(x1)) / 2.0 - 56.0
    bar_x1 = (float(x0) + float(x1)) / 2.0 + 56.0
    bar_y0 = float(y0) + 46.0
    bar_y1 = float(y1) - 46.0
    draw.line((bar_x0 - 24.0, bar_y1, bar_x1 + 24.0, bar_y1), fill=grid_color, width=2)
    for fraction, label in ((0.0, "0%"), (0.5, "50%"), (1.0, "100%")):
        tick_y = float(bar_y1 - ((bar_y1 - bar_y0) * float(fraction)))
        draw.line((bar_x0 - 18.0, tick_y, bar_x0 - 8.0, tick_y), fill=grid_color, width=2)
        _draw_text(draw, (bar_x0 - 70.0, tick_y - 10.0), label, label_font, (64, 68, 76))
    cursor = float(bar_y1)
    for category in dataset.categories:
        seg_height = (float(bar_y1) - float(bar_y0)) * float(category.value) / 100.0
        seg_y0 = float(cursor - seg_height)
        bbox = [float(bar_x0), float(seg_y0), float(bar_x1), float(cursor)]
        draw.rectangle(tuple(bbox), fill=tuple(category.color_rgb), outline=(255, 255, 255), width=max(1, int(outline_width)))
        label_bbox = None
        if float(seg_height) >= 24.0:
            label_bbox = _draw_centered(
                draw,
                ((float(bar_x0) + float(bar_x1)) / 2.0, (float(seg_y0) + float(cursor)) / 2.0),
                str(category.label),
                label_font,
                _contrast_text(category.color_rgb),
                stroke_width=1,
                stroke_fill=(32, 36, 44) if _contrast_text(category.color_rgb) == (255, 255, 255) else (255, 255, 255),
            )
        traces.append(
            {
                "label": str(category.label),
                "value": int(category.value),
                "fill_rgb": [int(channel) for channel in category.color_rgb],
                "segment_bbox_px": list(bbox),
                "label_bbox_px": list(label_bbox) if label_bbox is not None else None,
            }
        )
        cursor = float(seg_y0)
    return traces, (int(round(bar_x0)), int(round(bar_y0)), int(round(bar_x1)), int(round(bar_y1)))


def _coerce_position_options(raw: Any) -> Tuple[str, ...]:
    if raw is None:
        return ("right", "left", "bottom", "top")
    if isinstance(raw, str):
        values = [part.strip() for part in raw.split(",")]
    elif isinstance(raw, Sequence):
        values = [str(value).strip() for value in raw]
    else:
        values = []
    allowed = {"right", "left", "bottom", "top"}
    options = tuple(value for value in values if value in allowed)
    return options or ("right", "left", "bottom", "top")


def _resolve_table_position(params: Mapping[str, Any], *, instance_seed: int) -> str:
    explicit = params.get("table_position", group_default(_RENDER_DEFAULTS, "table_position", None))
    if explicit is not None:
        value = str(explicit).strip()
        if value not in {"right", "left", "bottom", "top"}:
            raise ValueError("table_position must be one of right, left, bottom, top")
        return value
    options = _coerce_position_options(
        params.get(
            "table_position_options",
            group_default(_RENDER_DEFAULTS, "table_position_options", ("right", "left", "bottom", "top")),
        )
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.table_position")
    return str(options[int(rng.randrange(0, len(options)))])


def _layout_share_chart_regions(
    *,
    width: int,
    height: int,
    margin_left: int,
    margin_right: int,
    margin_top: int,
    margin_bottom: int,
    table_width: int,
    table_height: int,
    chart_gap: int,
    table_position: str,
) -> Tuple[Tuple[int, int, int, int], Tuple[float, float, float, float], Tuple[int, int, int, int]]:
    content_x0 = int(margin_left)
    content_x1 = int(width - margin_right)
    content_y0 = int(margin_top + 72)
    content_y1 = int(height - margin_bottom)
    plot_bbox = (int(margin_left), int(margin_top), int(width - margin_right), int(height - margin_bottom))
    if str(table_position) == "left":
        table_bbox = (content_x0, content_y0, min(content_x1, content_x0 + int(table_width)), content_y1)
        chart_bbox = (float(table_bbox[2] + int(chart_gap)), float(content_y0), float(content_x1), float(content_y1))
    elif str(table_position) == "top":
        table_bottom = min(content_y1, content_y0 + int(table_height))
        table_bbox = (content_x0, content_y0, content_x1, table_bottom)
        chart_bbox = (float(content_x0), float(table_bbox[3] + int(chart_gap)), float(content_x1), float(content_y1))
    elif str(table_position) == "bottom":
        table_top = max(content_y0, content_y1 - int(table_height))
        table_bbox = (content_x0, table_top, content_x1, content_y1)
        chart_bbox = (float(content_x0), float(content_y0), float(content_x1), float(table_bbox[1] - int(chart_gap)))
    else:
        table_bbox = (max(content_x0, content_x1 - int(table_width)), content_y0, content_x1, content_y1)
        chart_bbox = (float(content_x0), float(content_y0), float(table_bbox[0] - int(chart_gap)), float(content_y1))
    if float(chart_bbox[2] - chart_bbox[0]) < 320.0 or float(chart_bbox[3] - chart_bbox[1]) < 320.0:
        table_bbox = (max(content_x0, content_x1 - int(table_width)), content_y0, content_x1, content_y1)
        chart_bbox = (float(content_x0), float(content_y0), float(table_bbox[0] - int(chart_gap)), float(content_y1))
    return tuple(int(value) for value in table_bbox), chart_bbox, plot_bbox


def _table_column_count(*, table_position: str, category_count: int) -> int:
    if str(table_position) in {"left", "right"}:
        return 1
    return 2 if int(category_count) <= 10 else 3


def _render_share_chart(
    *,
    base_image: Image.Image,
    dataset: _Dataset,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _RenderedShareChart:
    image = base_image.convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    text_color = resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        "text_color_rgb",
        [36, 40, 48],
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    grid_color = resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        "grid_color_rgb",
        [214, 219, 228],
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    panel_fill = resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        "plot_fill_rgb",
        [255, 255, 255],
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    outline_width = resolve_render_int(
        params,
        _RENDER_DEFAULTS,
        "mark_outline_width_px",
        2,
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    title_font = load_font(int(params.get("title_font_size_px", group_default(_RENDER_DEFAULTS, "title_font_size_px", 26))), bold=True)
    label_font = load_font(int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", 18))), bold=True)
    table_font = load_font(int(params.get("table_font_size_px", group_default(_RENDER_DEFAULTS, "table_font_size_px", 18))), bold=False)
    table_header_font = load_font(int(params.get("table_header_font_size_px", group_default(_RENDER_DEFAULTS, "table_header_font_size_px", 19))), bold=True)

    margin_left = int(params.get("plot_margin_left_px", group_default(_RENDER_DEFAULTS, "plot_margin_left_px", 42)))
    margin_right = int(params.get("plot_margin_right_px", group_default(_RENDER_DEFAULTS, "plot_margin_right_px", 42)))
    margin_top = int(params.get("plot_margin_top_px", group_default(_RENDER_DEFAULTS, "plot_margin_top_px", 46)))
    margin_bottom = int(params.get("plot_margin_bottom_px", group_default(_RENDER_DEFAULTS, "plot_margin_bottom_px", 42)))
    margin_left, margin_right, margin_top, margin_bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(margin_left),
        right_px=int(margin_right),
        top_px=int(margin_top),
        bottom_px=int(margin_bottom),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.layout",
    )
    table_width = int(params.get("table_width_px", group_default(_RENDER_DEFAULTS, "table_width_px", 450)))
    table_height = int(params.get("table_height_px", group_default(_RENDER_DEFAULTS, "table_height_px", 280)))
    chart_gap = int(params.get("chart_table_gap_px", group_default(_RENDER_DEFAULTS, "chart_table_gap_px", 34)))
    table_position = _resolve_table_position(params, instance_seed=int(instance_seed))
    table_bbox, chart_bbox, plot_bbox = _layout_share_chart_regions(
        width=int(width),
        height=int(height),
        margin_left=int(margin_left),
        margin_right=int(margin_right),
        margin_top=int(margin_top),
        margin_bottom=int(margin_bottom),
        table_width=int(table_width),
        table_height=int(table_height),
        chart_gap=int(chart_gap),
        table_position=str(table_position),
    )
    table_columns = _table_column_count(table_position=str(table_position), category_count=len(dataset.categories))
    layout_jitter_meta = {
        **dict(layout_jitter_meta),
        "table_position": str(table_position),
        "table_columns": int(table_columns),
    }
    draw.rounded_rectangle(chart_bbox, radius=8, fill=panel_fill, outline=grid_color, width=max(1, int(outline_width)))
    draw.rounded_rectangle(table_bbox, radius=8, fill=panel_fill, outline=grid_color, width=max(1, int(outline_width)))
    _draw_text(draw, (float(margin_left), float(margin_top - 4)), "Category share composition", title_font, text_color)
    total_bbox: List[float] | None = None
    known_count_bbox: List[float] | None = None
    info_y = float(margin_top + 25)
    total_count = dataset.trace_extras.get("total_count")
    if total_count is not None:
        total_bbox = _draw_text(
            draw,
            (float(margin_left), float(info_y)),
            f"Total count: {int(total_count)}",
            table_header_font,
            text_color,
        )
        info_y += 26.0
    known_count_value = dataset.trace_extras.get("known_count_value")
    known_count_category = dataset.trace_extras.get("known_count_category")
    if known_count_value is not None and known_count_category is not None:
        known_count_bbox = _draw_text(
            draw,
            (float(margin_left), float(info_y)),
            f"Known count: {known_count_category} = {int(known_count_value)}",
            table_header_font,
            text_color,
        )

    if str(scene_variant) in {"pie", "donut"}:
        chart_traces, chart_mark_bbox = _render_pie_like(
            draw,
            dataset=dataset,
            scene_variant=str(scene_variant),
            chart_bbox=chart_bbox,
            text_color=text_color,
            panel_fill=panel_fill,
            outline_width=int(outline_width),
            label_font=label_font,
        )
    else:
        chart_traces, chart_mark_bbox = _render_stacked(
            draw,
            dataset=dataset,
            scene_variant=str(scene_variant),
            chart_bbox=chart_bbox,
            grid_color=grid_color,
            outline_width=int(outline_width),
            label_font=label_font,
        )

    table_inner_left = float(table_bbox[0]) + 14.0
    table_inner_right = float(table_bbox[2]) - 14.0
    table_top = float(table_bbox[1]) + 12.0
    column_gap = 14.0 if int(table_columns) > 1 else 0.0
    column_width = (
        float(table_inner_right - table_inner_left) - (float(table_columns - 1) * float(column_gap))
    ) / float(table_columns)
    rows_per_column = int(math.ceil(len(dataset.categories) / float(table_columns)))
    row_area_top = float(table_bbox[1]) + 54.0
    row_area_bottom = float(table_bbox[3]) - 14.0
    row_height = float(row_area_bottom - row_area_top) / float(max(1, rows_per_column))
    swatch_size = min(22.0, max(14.0, float(row_height) * 0.58))
    evidence_bbox_by_label: Dict[str, List[float]] = {}
    category_traces: List[Dict[str, Any]] = []
    entities: List[Dict[str, Any]] = []
    if total_bbox is not None:
        evidence_bbox_by_label["__total__"] = list(total_bbox)
        entities.append(
            {
                "entity_id": "__total__",
                "kind": "composition_total",
                "attrs": {
                    "label": "total_count",
                    "value": int(total_count),
                    "bbox_px": list(total_bbox),
                },
            }
        )
    if known_count_bbox is not None:
        evidence_bbox_by_label["__known_count__"] = list(known_count_bbox)
        entities.append(
            {
                "entity_id": "__known_count__",
                "kind": "composition_known_count",
                "attrs": {
                    "label": "known_count",
                    "category": str(known_count_category),
                    "value": int(known_count_value),
                    "bbox_px": list(known_count_bbox),
                },
            }
        )
    table_categories = tuple(sorted(dataset.categories, key=lambda item: str(item.label)))
    for column_index in range(int(table_columns)):
        col_x0 = float(table_inner_left + (float(column_index) * (float(column_width) + float(column_gap))))
        col_x1 = float(col_x0 + float(column_width))
        _draw_text(draw, (float(col_x0) + 6.0, float(table_top)), "Category", table_header_font, text_color)
        _draw_text(draw, (float(col_x1) - 88.0, float(table_top)), "Share", table_header_font, text_color)
        header_y = float(table_bbox[1]) + 48.0
        draw.line((float(col_x0) + 4.0, header_y, float(col_x1) - 4.0, header_y), fill=grid_color, width=2)
        if int(column_index) > 0:
            separator_x = float(col_x0) - (float(column_gap) / 2.0)
            draw.line(
                (separator_x, float(table_bbox[1]) + 16.0, separator_x, float(table_bbox[3]) - 16.0),
                fill=grid_color,
                width=1,
            )
    for index, category in enumerate(table_categories):
        column_index = int(index) // int(rows_per_column)
        row_index = int(index) % int(rows_per_column)
        col_x0 = float(table_inner_left + (float(column_index) * (float(column_width) + float(column_gap))))
        col_x1 = float(col_x0 + float(column_width))
        row_y0 = float(row_area_top + (float(index) * float(row_height)))
        row_y0 = float(row_area_top + (float(row_index) * float(row_height)))
        row_y1 = float(row_area_top + (float(row_index + 1) * float(row_height)))
        if int(index) % 2 == 1:
            draw.rectangle(
                (float(col_x0) + 4.0, row_y0, float(col_x1) - 4.0, row_y1),
                fill=(248, 249, 251),
            )
        if int(row_index) > 0:
            draw.line((float(col_x0) + 4.0, row_y0, float(col_x1) - 4.0, row_y0), fill=grid_color, width=1)
        swatch_y0 = row_y0 + ((float(row_height) - float(swatch_size)) / 2.0)
        swatch_x0 = float(col_x0) + 8.0
        draw.rounded_rectangle(
            (swatch_x0, swatch_y0, swatch_x0 + swatch_size, swatch_y0 + swatch_size),
            radius=3,
            fill=tuple(category.color_rgb),
            outline=(80, 84, 92),
            width=1,
        )
        text_y = row_y0 + ((float(row_height) - _text_size(draw, str(category.label), table_font)[1]) / 2.0) - 1.0
        label_bbox = _draw_text(draw, (swatch_x0 + swatch_size + 12.0, text_y), str(category.label), table_font, text_color)
        value_text = f"{int(category.value)}%"
        value_width = _text_size(draw, value_text, table_font)[0]
        value_bbox = _draw_text(draw, (float(col_x1) - 12.0 - value_width, text_y), value_text, table_font, text_color)
        full_row_bbox = [float(col_x0) + 5.0, float(row_y0), float(col_x1) - 5.0, float(row_y1)]
        evidence_bbox = [
            max(float(col_x0) + 5.0, float(swatch_x0) - 5.0),
            max(float(row_y0) + 3.0, min(float(swatch_y0), float(label_bbox[1]), float(value_bbox[1])) - 4.0),
            min(float(col_x1) - 5.0, max(float(swatch_x0 + swatch_size), float(label_bbox[2]), float(value_bbox[2])) + 5.0),
            min(float(row_y1) - 3.0, max(float(swatch_y0 + swatch_size), float(label_bbox[3]), float(value_bbox[3])) + 4.0),
        ]
        evidence_bbox_by_label[str(category.label)] = list(evidence_bbox)
        category_trace = {
            "label": str(category.label),
            "value": int(category.value),
            "fill_rgb": [int(channel) for channel in category.color_rgb],
            "table_order_index": int(index),
            "table_column_index": int(column_index),
            "table_row_index": int(row_index),
            "row_bbox_px": list(full_row_bbox),
            "evidence_bbox_px": list(evidence_bbox),
            "label_bbox_px": list(label_bbox),
            "value_bbox_px": list(value_bbox),
        }
        category_traces.append(dict(category_trace))
        entities.append(
            {
                "entity_id": str(category.label),
                "kind": "composition_category",
                "attrs": dict(category_trace),
            }
        )

    for trace in chart_traces:
        entities.append(
            {
                "entity_id": f"chart:{trace['label']}",
                "kind": "composition_mark",
                "attrs": dict(trace),
            }
        )

    return _RenderedShareChart(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=tuple(int(value) for value in plot_bbox),
        table_bbox_px=tuple(int(value) for value in table_bbox),
        chart_traces=tuple(dict(trace) for trace in chart_traces),
        category_traces=tuple(dict(trace) for trace in category_traces),
        evidence_bbox_by_label=dict(evidence_bbox_by_label),
        layout_jitter_meta=dict(layout_jitter_meta),
    )


class ChartsCompositionShareArithmeticValueTask:
    """Return an integer share-arithmetic value from one composition chart."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "composition"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        public_overrides = (
            _public_task_param_overrides(str(self.task_id))
            if str(self.task_id) != str(TASK_ID)
            else {}
        )
        if public_overrides:
            merged_params = dict(public_overrides)
            merged_params.update(dict(params))
            params = merged_params
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        scene_params = _params_for_scene_axis(params)
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            scene_params,
            instance_seed=int(instance_seed),
            supported_variants=_scene_variants_for_task(str(query_id)),
        )
        dataset = _build_dataset(query_id=str(query_id), params=params, instance_seed=int(instance_seed))

        canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
        canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
        background, background_meta = make_background_canvas(
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = _render_share_chart(
            base_image=background,
            dataset=dataset,
            scene_variant=str(scene_variant),
            params=params,
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
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "object_description_pie",
                "object_description_donut",
                "object_description_stacked_bar",
                "object_description_stacked_horizontal_bar",
                "evidence_hint_contiguous_chart_order_sum",
                "evidence_hint_positional_segment_share_sum",
                "evidence_hint_chart_order_share_to_count",
                "evidence_hint_chart_order_remaining_count",
                "evidence_hint_sector_share_to_angle",
                "evidence_hint_chart_order_adjacent_transfer_gap",
                "json_example_contiguous_chart_order_sum",
                "json_example_positional_segment_share_sum",
                "json_example_chart_order_share_to_count",
                "json_example_chart_order_remaining_count",
                "json_example_sector_share_to_angle",
                "json_example_chart_order_adjacent_transfer_gap",
                "json_example_answer_only_contiguous_chart_order_sum",
                "json_example_answer_only_positional_segment_share_sum",
                "json_example_answer_only_chart_order_share_to_count",
                "json_example_answer_only_chart_order_remaining_count",
                "json_example_answer_only_sector_share_to_angle",
                "json_example_answer_only_chart_order_adjacent_transfer_gap",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        extras = dict(dataset.trace_extras)
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        evidence_hint = str(prompt_defaults[f"evidence_hint_{str(query_id)}"])
        json_example = str(prompt_defaults[f"json_example_{str(query_id)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "category_list": _format_quoted([str(label) for label in extras.get("category_list", [])]),
                "rank_position_list_text": str(extras.get("rank_position_list_text", "")),
                "lower_reference_category": str(extras.get("lower_reference_category", "")),
                "upper_reference_category": str(extras.get("upper_reference_category", "")),
                "start_category": str(extras.get("start_category", "")),
                "end_category": str(extras.get("end_category", "")),
                "source_category": str(extras.get("source_category", "")),
                "target_category": str(extras.get("target_category", "")),
                "transfer_delta": str(extras.get("transfer_delta", "")),
                "source_rank_text": str(extras.get("source_rank_text", "")),
                "target_rank_text": str(extras.get("target_rank_text", "")),
                "source_threshold": str(extras.get("source_threshold", "")),
                "target_threshold": str(extras.get("target_threshold", "")),
                "source_order_direction": str(extras.get("source_order_direction", "")),
                "target_order_direction": str(extras.get("target_order_direction", "")),
                "source_extremum_text": str(extras.get("source_extremum_text", "")),
                "target_extremum_text": str(extras.get("target_extremum_text", "")),
                "positional_instruction": str(extras.get("positional_instruction", "")),
                "group_size": str(extras.get("group_size", "")),
                "known_count_category": str(extras.get("known_count_category", "")),
                "threshold_value": str(extras.get("threshold_value", "")),
                "comparison_start_category": str(extras.get("comparison_start_category", "")),
                "chart_order_phrase": str(extras.get("chart_order_direction", _chart_order_phrase(str(scene_variant)))),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        values_by_label = {str(category.label): int(category.value) for category in dataset.categories}
        evidence_values = [
            _evidence_value_for_label(str(label), extras=extras, values_by_label=values_by_label)
            for label in dataset.evidence_labels
        ]
        evidence_bboxes = [
            list(rendered_scene.evidence_bbox_by_label[str(label)])
            for label in dataset.evidence_labels
            if str(label) in rendered_scene.evidence_bbox_by_label
        ]
        answer_gt = TypedValue(type="integer", value=int(dataset.answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": f"chart_{str(scene_variant)}_composition_share_arithmetic",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "category_labels": [str(category.label) for category in dataset.categories],
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "category_count": int(extras["category_count"]),
                    "evidence_labels": [str(label) for label in dataset.evidence_labels],
                },
            },
            "render_spec": {
                "canvas_width": int(canvas_width),
                "canvas_height": int(canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "layout_jitter": dict(rendered_scene.layout_jitter_meta),
                "table_position": str(rendered_scene.layout_jitter_meta.get("table_position", "right")),
                "table_columns": int(rendered_scene.layout_jitter_meta.get("table_columns", 1)),
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "table_bbox_px": list(rendered_scene.table_bbox_px),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "table_bbox_px": list(rendered_scene.table_bbox_px),
                "chart_traces": [dict(trace) for trace in rendered_scene.chart_traces],
                "category_traces": [dict(trace) for trace in rendered_scene.category_traces],
                "evidence_bbox_by_label": {
                    str(label): list(bbox)
                    for label, bbox in rendered_scene.evidence_bbox_by_label.items()
                },
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "answer_value": int(dataset.answer_value),
                "category_count": int(extras["category_count"]),
                "category_count_range": list(extras["category_count_range"]),
                "category_values": {str(label): int(value) for label, value in values_by_label.items()},
                "categories": [
                    {
                        "label": str(category.label),
                        "value": int(category.value),
                        "fill_rgb": [int(channel) for channel in category.color_rgb],
                    }
                    for category in dataset.categories
                ],
                "evidence_labels": [str(label) for label in dataset.evidence_labels],
                "evidence_values": [int(value) for value in evidence_values],
                "question_format": "numeric_open",
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                **dict(extras),
            },
            "witness_symbolic": {
                "type": "composition_share_arithmetic",
                "query_id": str(query_id),
                "answer_value": int(dataset.answer_value),
                "evidence_values": [int(value) for value in evidence_values],
                "calculation": dict(extras),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
                "evidence_labels": [str(label) for label in dataset.evidence_labels],
            },
        }
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(extras["category_count"]), extras["category_count_range"]),
                "reasoning_load": float(_REASONING_LOAD_BY_VARIANT[str(query_id)]),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
            },
        )
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
class ChartsCompositionChartOrderedSegmentValueTask(
    MergedChartQueryVariantTaskMixin,
    ChartsCompositionShareArithmeticValueTask,
):
    """Compute ordered part-whole segment shares, counts, or angles."""

    task_id = "task_charts__part_whole__ordered_segment_value"
    allowed_query_ids = (
        "contiguous_chart_order_sum",
        "positional_segment_share_sum",
        "chart_order_share_to_count",
        "sector_share_to_angle",
    )


@register_task
class ChartsCompositionChartAdjacentTransferGapValueTask(
    MergedChartQueryVariantTaskMixin,
    ChartsCompositionShareArithmeticValueTask,
):
    """Compute a transfer gap after choosing an adjacent chart-order target."""

    task_id = "task_charts__part_whole__adjacent_transfer_gap_value"
    allowed_query_ids = ("chart_order_adjacent_transfer_gap",)


__all__ = [
    "ChartsCompositionChartAdjacentTransferGapValueTask",
    "ChartsCompositionChartOrderedSegmentValueTask",
    "ChartsCompositionShareArithmeticValueTask",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
]
