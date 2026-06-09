"""Shared constants and sampling helpers for part-whole composition chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from ....core.task_group_config import get_task_group_defaults
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ..shared.complexity import resolve_chart_complexity_weights
from ..shared.labeled_chart_common import LabeledChartDefaults
from ..shared.sampling_defaults import (
    balanced_int_from_support,
    public_task_param_overrides,
    resolve_chart_axis_variant,
)
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults

TASK_ID = "charts_composition_share_arithmetic_value_base"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "contiguous_chart_order_sum",
    "positional_segment_share_sum",
    "chart_order_share_to_count",
    "chart_order_remaining_count",
    "subset_denominator_share_value",
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
    "subset_denominator_share_value",
    "sector_share_to_angle",
)
CIRCULAR_ONLY_QUERY_IDS = frozenset(
    {
        "contiguous_chart_order_sum",
        "positional_segment_share_sum",
        "chart_order_share_to_count",
        "chart_order_remaining_count",
        "subset_denominator_share_value",
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
    "subset_denominator_share_value": 0.94,
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

    return public_task_param_overrides(_TASK_GROUP_DEFAULTS, str(task_id))


@dataclass(frozen=True)
class _CategorySpec:
    label: str
    value: int
    color_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class _Dataset:
    categories: Tuple[_CategorySpec, ...]
    answer_value: int
    annotation_labels: Tuple[str, ...]
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
    annotation_bbox_by_label: Dict[str, List[float]]
    annotation_point_by_label: Dict[str, List[float]]
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
    return balanced_int_from_support(
        [int(value) for value in values],
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )


def _configured_int_values(params: Mapping[str, Any], *, key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), None))
    if raw is None:
        raw = tuple(int(value) for value in fallback)
    if isinstance(raw, str):
        values = [part.strip() for part in raw.split(",")]
    elif isinstance(raw, Sequence):
        values = list(raw)
    else:
        values = []
    parsed = tuple(sorted({int(value) for value in values if str(value).strip()}))
    if not parsed:
        raise ValueError(f"{key} must contain at least one integer")
    return tuple(int(value) for value in parsed)


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
