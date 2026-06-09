"""Shared constants and specs for radar chart profile tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from ....core.task_group_config import get_task_group_defaults
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ...shared.font_assets import sample_font_family
from ...shared.render_variation import resolve_render_rgb
from ..shared.complexity import resolve_chart_complexity_weights
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults

TASK_ID = "charts_radar_query_base"
SCENE_ID = "radar"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "highlighted_metric_threshold_panel_count",
    "threshold_metric_count_for_panel",
    "profile_advantage_count",
    "matching_condition_panel_count",
)
SMALL_MULTIPLE_VARIANTS = frozenset(
    {
        "highlighted_metric_threshold_panel_count",
        "threshold_metric_count_for_panel",
        "matching_condition_panel_count",
    }
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "small_multiple_radar",
    "single_radar_multi_profile",
)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "radar")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="radar")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="radar", apply_prob=0.0)

_PANEL_LABELS: Tuple[str, ...] = tuple("ABCDEFGH")
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "highlighted_metric_threshold_panel_count": 0.56,
    "threshold_metric_count_for_panel": 0.58,
    "profile_advantage_count": 0.70,
    "matching_condition_panel_count": 0.82,
}
_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {
    "small_multiple_radar": 0.72,
    "single_radar_multi_profile": 0.58,
}

BBox = Tuple[float, float, float, float]
RGB = Tuple[int, int, int]
Point = List[float]


@dataclass(frozen=True)
class _Profile:
    profile_label: str
    values: Dict[str, int]
    color_rgb: RGB


@dataclass(frozen=True)
class _Panel:
    panel_label: str
    profiles: Tuple[_Profile, ...]


@dataclass(frozen=True)
class _Query:
    query_id: str
    scene_variant: str
    answer: str | int
    answer_type: str
    metric_label: str
    panel_label: str
    profile_a_label: str
    profile_b_label: str
    threshold_value: int
    minimum_metric_count: int
    annotation_point_ids: Tuple[str, ...]
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    metrics: Tuple[str, ...]
    panels: Tuple[_Panel, ...]
    query: _Query


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    point_bboxes: Dict[str, List[float]]
    panel_bboxes: Dict[str, List[float]]
    panel_title_bboxes: Dict[str, List[float]]
    legend_bboxes: Dict[str, List[float]]
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


def _sample_chart_font_family(instance_seed: int, params: Mapping[str, Any]) -> str:
    return str(
        sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.chart_font",
            params=params,
            exclude_tags=("display",),
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        )
    )


def _resolve_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), _RENDER_DEFAULTS.get(str(key), int(fallback))))


def _resolve_gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def _resolve_rgb(params: Mapping[str, Any], key: str, fallback: RGB) -> RGB:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _palette(params: Mapping[str, Any]) -> Tuple[RGB, ...]:
    raw = params.get("profile_palette_rgb", _RENDER_DEFAULTS.get("profile_palette_rgb", ()))
    colors: List[RGB] = []
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        for item in raw:
            if isinstance(item, Sequence) and not isinstance(item, (str, bytes)) and len(item) >= 3:
                colors.append(tuple(max(0, min(255, int(channel))) for channel in item[:3]))  # type: ignore[index]
    if colors:
        return tuple(colors)
    return (
        (41, 108, 179),
        (205, 82, 74),
        (55, 148, 104),
        (139, 92, 186),
        (214, 139, 44),
        (54, 148, 168),
    )


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]
