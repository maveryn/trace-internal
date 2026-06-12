"""Shared data structures and sampling helpers for part-whole charts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from .....core.scene_config import get_scene_defaults
from ....shared.config_defaults import group_default, split_scene_generation_rendering_prompt_defaults
from ...shared.labeled_chart_common import LabeledChartDefaults
from ...shared.sampling_defaults import balanced_int_from_support, resolve_chart_axis_variant
from ...shared.visual_defaults import load_chart_scene_background_defaults, load_chart_scene_noise_defaults


SCENE_ID = "part_whole"
SCENE_NAMESPACE = "charts_part_whole"
SAMPLING_NAMESPACE = "charts_part_whole.share_arithmetic"

CONTIGUOUS_CHART_ORDER_SUM_QUERY_ID = "contiguous_chart_order_sum"
POSITIONAL_SEGMENT_SHARE_SUM_QUERY_ID = "positional_segment_share_sum"
CHART_ORDER_SHARE_TO_COUNT_QUERY_ID = "chart_order_share_to_count"
SUBSET_DENOMINATOR_SHARE_VALUE_QUERY_ID = "subset_denominator_share_value"
SECTOR_SHARE_TO_ANGLE_QUERY_ID = "sector_share_to_angle"
ADJACENT_TRANSFER_GAP_QUERY_ID = "chart_order_adjacent_transfer_gap"

ACTIVE_QUERY_IDS: Tuple[str, ...] = (
    CONTIGUOUS_CHART_ORDER_SUM_QUERY_ID,
    POSITIONAL_SEGMENT_SHARE_SUM_QUERY_ID,
    CHART_ORDER_SHARE_TO_COUNT_QUERY_ID,
    SUBSET_DENOMINATOR_SHARE_VALUE_QUERY_ID,
    SECTOR_SHARE_TO_ANGLE_QUERY_ID,
    ADJACENT_TRANSFER_GAP_QUERY_ID,
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("pie", "donut")
CIRCULAR_ORDER_DIRECTIONS: Tuple[str, ...] = ("clockwise", "counterclockwise")
POSITIONAL_RELATIONS: Tuple[str, ...] = ("anchor_offset_sum", "opposite_neighbor_sum")
PART_WHOLE_QUERY_IDS: Tuple[str, ...] = (
    CHART_ORDER_SHARE_TO_COUNT_QUERY_ID,
    SUBSET_DENOMINATOR_SHARE_VALUE_QUERY_ID,
    SECTOR_SHARE_TO_ANGLE_QUERY_ID,
)
TRANSFER_GAP_QUERY_IDS: Tuple[str, ...] = (ADJACENT_TRANSFER_GAP_QUERY_ID,)
COMPACT_VALUE_QUERY_IDS = frozenset(ACTIVE_QUERY_IDS)

DEFAULTS = LabeledChartDefaults(canvas_width=1280, canvas_height=920)
TASK_GROUP_DEFAULTS = get_scene_defaults("charts", SCENE_ID)
GEN_DEFAULTS, RENDER_DEFAULTS, PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    TASK_GROUP_DEFAULTS if isinstance(TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=SCENE_NAMESPACE,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id=SCENE_ID)
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)
REASONING_LOAD_BY_QUERY_ID: Dict[str, float] = {
    CONTIGUOUS_CHART_ORDER_SUM_QUERY_ID: 0.94,
    POSITIONAL_SEGMENT_SHARE_SUM_QUERY_ID: 0.96,
    CHART_ORDER_SHARE_TO_COUNT_QUERY_ID: 0.96,
    SUBSET_DENOMINATOR_SHARE_VALUE_QUERY_ID: 0.94,
    SECTOR_SHARE_TO_ANGLE_QUERY_ID: 0.94,
    ADJACENT_TRANSFER_GAP_QUERY_ID: 0.92,
}
SCENE_VARIANT_LOADS: Dict[str, float] = {"pie": 0.52, "donut": 0.56}


@dataclass(frozen=True)
class CategorySpec:
    label: str
    value: int
    color_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class PartWholeDataset:
    categories: Tuple[CategorySpec, ...]
    answer_value: int
    annotation_labels: Tuple[str, ...]
    trace_extras: Dict[str, Any]


@dataclass(frozen=True)
class TransferQuery:
    source: CategorySpec
    target: CategorySpec
    delta: int
    extras: Dict[str, Any]


@dataclass(frozen=True)
class RenderedShareChart:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: Tuple[int, int, int, int]
    table_bbox_px: Tuple[int, int, int, int]
    chart_traces: Tuple[Dict[str, Any], ...]
    category_traces: Tuple[Dict[str, Any], ...]
    annotation_bbox_by_label: Dict[str, List[float]]
    annotation_point_by_label: Dict[str, List[float]]
    layout_jitter_meta: Dict[str, Any]


def resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        task_id=SCENE_NAMESPACE,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def scene_axis_stride(params: Mapping[str, Any]) -> int:
    if params.get("scene_variant") is not None or params.get("scene_variant_weights") is not None:
        return 1
    return len(SUPPORTED_SCENE_VARIANTS)


def params_with_shifted_sample_cursor(params: Mapping[str, Any], *, divisor: int) -> Dict[str, Any]:
    shifted = dict(params)
    if "_sample_cursor" not in shifted:
        return shifted
    shifted["_sample_cursor"] = abs(int(shifted["_sample_cursor"])) // max(1, int(divisor))
    return shifted


def resolve_count_bounds(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, int]:
    min_value = int(params.get(str(min_key), group_default(GEN_DEFAULTS, str(min_key), int(fallback_min))))
    max_value = int(params.get(str(max_key), group_default(GEN_DEFAULTS, str(max_key), int(fallback_max))))
    if int(min_value) > int(max_value):
        raise ValueError(f"{min_key} must be <= {max_key}")
    return int(min_value), int(max_value)


def balanced_int(
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


def configured_int_values(params: Mapping[str, Any], *, key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    raw = params.get(str(key), group_default(GEN_DEFAULTS, str(key), None))
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


def category_count_bounds(params: Mapping[str, Any], *, query_id: str) -> Tuple[int, int]:
    if str(query_id) == CONTIGUOUS_CHART_ORDER_SUM_QUERY_ID:
        return resolve_count_bounds(
            params,
            min_key="contiguous_category_count_min",
            max_key="contiguous_category_count_max",
            fallback_min=5,
            fallback_max=10,
        )
    if str(query_id) in TRANSFER_GAP_QUERY_IDS:
        return resolve_count_bounds(
            params,
            min_key="counterfactual_category_count_min",
            max_key="counterfactual_category_count_max",
            fallback_min=8,
            fallback_max=14,
        )
    if str(query_id) in PART_WHOLE_QUERY_IDS:
        return resolve_count_bounds(
            params,
            min_key="part_whole_category_count_min",
            max_key="part_whole_category_count_max",
            fallback_min=8,
            fallback_max=14,
        )
    if str(query_id) == POSITIONAL_SEGMENT_SHARE_SUM_QUERY_ID:
        return resolve_count_bounds(
            params,
            min_key="positional_category_count_min",
            max_key="positional_category_count_max",
            fallback_min=6,
            fallback_max=12,
        )
    return resolve_count_bounds(
        params,
        min_key="category_count_min",
        max_key="category_count_max",
        fallback_min=16,
        fallback_max=24,
    )


def value_bounds(params: Mapping[str, Any], *, query_id: str) -> Tuple[int, int]:
    if str(query_id) in COMPACT_VALUE_QUERY_IDS:
        return resolve_count_bounds(
            params,
            min_key="compact_value_min",
            max_key="compact_value_max",
            fallback_min=2,
            fallback_max=40,
        )
    return (
        int(params.get("value_min", group_default(GEN_DEFAULTS, "value_min", 1))),
        int(params.get("value_max", group_default(GEN_DEFAULTS, "value_max", 18))),
    )


def format_quoted(values: Sequence[str]) -> str:
    return ", ".join(f'"{str(value)}"' for value in values)


def format_offset_list(values: Sequence[int]) -> str:
    phrases = [f"{int(value)} segment{'s' if int(value) != 1 else ''}" for value in values]
    if not phrases:
        return ""
    if len(phrases) == 1:
        return str(phrases[0])
    return f"{', '.join(phrases[:-1])}, and {phrases[-1]}"


def chart_order_phrase(scene_variant: str) -> str:
    if str(scene_variant) in {"pie", "donut"}:
        return "clockwise"
    return "in chart order"
