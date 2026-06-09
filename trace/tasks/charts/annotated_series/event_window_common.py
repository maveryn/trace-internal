"""Shared constants, defaults, and records for annotated-series chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from ....core.task_group_config import get_task_group_defaults
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ..shared.complexity import resolve_chart_complexity_weights
from ..shared.labeled_chart_common import LabeledChartDefaults
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_annotated_series_query_base"
SCENE_ID = "annotated_series"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "event_window_extremum_label",
    "event_window_threshold_count",
    "callout_endpoint_change_value",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "line",
    "bar",
    "area",
    "dot_plot",
    "lollipop",
)
SUPPORTED_EXTREMUM_DIRECTIONS: Tuple[str, ...] = ("highest", "lowest")
SUPPORTED_THRESHOLD_COMPARISONS: Tuple[str, ...] = ("greater_than", "less_than")
SUPPORTED_ENDPOINT_SIDES: Tuple[str, ...] = ("first", "last")

_DEFAULTS = LabeledChartDefaults(mark_count_min=8, mark_count_max=14, value_min=10, value_max=90)
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "annotated_series")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="annotated_series")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="annotated_series", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)

_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "line": 0.22,
    "bar": 0.30,
    "area": 0.42,
    "dot_plot": 0.50,
    "lollipop": 0.58,
}
_REASONING_LOADS: Dict[str, float] = {
    "event_window_extremum_label": 0.50,
    "event_window_threshold_count": 0.68,
    "callout_endpoint_change_value": 0.62,
}

RGB = Tuple[int, int, int]


@dataclass(frozen=True)
class _Dataset:
    query_id: str
    scene_variant: str
    labels: Tuple[str, ...]
    values: Tuple[int, ...]
    window_labels: Tuple[str, ...]
    annotation_labels: Tuple[str, ...]
    answer_value: str | int
    answer_type: str
    query_params: Dict[str, Any]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _Annotation:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    point_set: Tuple[List[float], ...]
    annotation_bboxes: Dict[str, List[float]]


_CONTEXT_PARAM_KEYS: Tuple[str, ...] = (
    "context_text_enabled",
    "context_text_mode_weights",
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
    "context_text_box_count_min",
    "context_text_box_count_max",
    "context_text_font_family_weights",
    "context_text_chrome_font_family",
    "context_text_chip_font_family",
    "context_text_box_font_family",
)

@dataclass(frozen=True)
class _Dataset:
    query_id: str
    scene_variant: str
    labels: Tuple[str, ...]
    values: Tuple[int, ...]
    window_labels: Tuple[str, ...]
    annotation_labels: Tuple[str, ...]
    answer_value: str | int
    answer_type: str
    query_params: Dict[str, Any]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _Annotation:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    point_set: Tuple[List[float], ...]
    annotation_bboxes: Dict[str, List[float]]


def _gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _probability_map_from_weights(
    params: Mapping[str, Any],
    *,
    key: str,
    supported: Sequence[str],
) -> Dict[str, float]:
    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), {str(item): 1.0 for item in supported}))
    if not isinstance(raw, Mapping):
        raise ValueError(f"{key} must be a mapping")
    weights = {
        str(item): max(0.0, float(raw.get(str(item), 0.0)))
        for item in supported
    }
    total = float(sum(weights.values()))
    if total <= 0.0:
        weights = {str(item): 1.0 for item in supported}
        total = float(len(weights))
    return {str(key): float(value) / float(total) for key, value in sorted(weights.items())}


def _render_default_value(params: Mapping[str, Any], key: str, fallback: Any) -> Any:
    return params.get(str(key), group_default(_RENDER_DEFAULTS, str(key), fallback))


def _render_choice(
    params: Mapping[str, Any],
    *,
    key: str,
    fallback: str,
    instance_seed: int,
    namespace: str,
) -> str:
    explicit = params.get(str(key), group_default(_RENDER_DEFAULTS, str(key), None))
    if explicit is not None:
        return str(explicit)
    options = params.get(f"{str(key)}_options", group_default(_RENDER_DEFAULTS, f"{str(key)}_options", ()))
    if isinstance(options, Sequence) and options and not isinstance(options, (str, bytes)):
        index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{str(namespace)}.{str(key)}",
        )
        return str(options[int(index) % len(options)])
    return str(fallback)
