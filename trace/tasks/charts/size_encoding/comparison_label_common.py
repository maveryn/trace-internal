"""Shared constants and specs for size-encoded chart comparison tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.task_group_config import get_task_group_defaults
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ...shared.render_variation import resolve_render_rgb
from ..shared.complexity import resolve_chart_complexity_weights
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults

TASK_ID = "charts_size_encoding_comparison_label_base"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "filtered_item_extremum_label",
    "reference_size_neighbor_label",
    "category_total_extremum_label",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "rect_word_cloud",
    "circle_word_cloud",
    "packed_bubble_cloud",
    "small_multiple_bubble_cloud",
)
SUPPORTED_EXTREMUM_DIRECTIONS: Tuple[str, ...] = ("largest", "smallest")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "size_encoding")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="size_encoding")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="size_encoding", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)

_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "filtered_item_extremum_label": 0.44,
    "reference_size_neighbor_label": 0.72,
    "category_total_extremum_label": 0.86,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "rect_word_cloud": 0.22,
    "circle_word_cloud": 0.34,
    "packed_bubble_cloud": 0.40,
    "small_multiple_bubble_cloud": 0.72,
}

BBox = Tuple[float, float, float, float]
RGB = Tuple[int, int, int]


@dataclass(frozen=True)
class _Item:
    item_id: str
    label: str
    category: str
    panel: str
    value: int


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer: str
    annotation_item_ids: Tuple[str, ...]
    annotation_panel_labels: Tuple[str, ...]
    annotation_category_labels: Tuple[str, ...]
    category_label: str
    panel_label: str
    reference_label: str
    extremum_direction: str
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    items: Tuple[_Item, ...]
    categories: Tuple[str, ...]
    panels: Tuple[str, ...]
    query: _Query


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    item_bboxes: Dict[str, List[float]]
    panel_title_bboxes: Dict[str, List[float]]
    category_legend_bboxes: Dict[str, List[float]]
    plot_bbox_px: List[float]
    render_meta: Dict[str, Any]


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
    query_id: str,
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
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


def _resolve_extremum_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_EXTREMUM_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="extremum_direction",
        weights_key="extremum_direction_weights",
        balance_flag_key="balanced_extremum_direction_sampling",
        axis_namespace="extremum_direction",
    )


def _resolve_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def _resolve_rgb(params: Mapping[str, Any], key: str, fallback: Sequence[int]) -> RGB:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _category_palette(params: Mapping[str, Any], category_count: int) -> Tuple[RGB, ...]:
    raw = params.get("category_palette_rgb", group_default(_RENDER_DEFAULTS, "category_palette_rgb", []))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or len(raw) < int(category_count):
        raise ValueError("category_palette_rgb must contain enough RGB colors")
    colors: List[RGB] = []
    for value in raw[: int(category_count)]:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
            raise ValueError("category_palette_rgb entries must be RGB sequences")
        colors.append((int(value[0]), int(value[1]), int(value[2])))
    return tuple(colors)
