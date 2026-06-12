"""Shared defaults for the annotated-series chart scene."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.charts.shared.labeled_chart_core import LabeledChartDefaults
from trace.tasks.shared.config_defaults import (
    group_default as _config_group_default,
    load_scene_generation_rendering_prompt_defaults,
    resolve_required_int_bounds,
)


DOMAIN = "charts"
SCENE_ID = "annotated_series"
SCENE_NAMESPACE = "charts.annotated_series"

SUPPORTED_SCENE_VARIANTS = ("line", "bar", "area", "dot_plot", "lollipop")

PROMPT_BUNDLE_ID = "charts_annotated_series_v1"

FALLBACK_CHART_DEFAULTS = LabeledChartDefaults(
    mark_count_min=5,
    mark_count_max=9,
    value_min=10,
    value_max=90,
)

GENERATION_DEFAULTS, RENDERING_DEFAULTS, PROMPT_DEFAULTS = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID)
)

POST_IMAGE_NOISE_DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "shadow_probability": 0.35,
    "paper_texture_probability": 0.30,
    "blur_probability": 0.12,
    "blur_radius_min": 0.15,
    "blur_radius_max": 0.55,
    "noise_probability": 0.18,
    "noise_std_min": 1.5,
    "noise_std_max": 4.5,
    "jpeg_probability": 0.12,
    "jpeg_quality_min": 70,
    "jpeg_quality_max": 92,
}

CONTEXT_PARAM_KEYS = (
    "context_mode_weights",
    "context_element_count_min",
    "context_element_count_max",
    "large_context_probability",
    "large_context_text_source_weights",
    "context_text_source_weights",
)


def group_default(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    fallback: Any,
) -> Any:
    """Return an explicit param value, then scene defaults, then fallback."""

    return params.get(str(key), _config_group_default(defaults, str(key), fallback))


def generation_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(group_default(params, GENERATION_DEFAULTS, key, fallback))


def rendering_value(params: Mapping[str, Any], key: str, fallback: Any) -> Any:
    return group_default(params, RENDERING_DEFAULTS, key, fallback)


def rendering_bool(params: Mapping[str, Any], key: str, fallback: bool) -> bool:
    return bool(rendering_value(params, key, fallback))


def rendering_float(params: Mapping[str, Any], key: str, fallback: float) -> float:
    return float(rendering_value(params, key, fallback))


def rendering_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(rendering_value(params, key, fallback))


def generation_bounds(
    params: Mapping[str, Any],
    lower_key: str,
    upper_key: str,
    fallback_lower: int,
    fallback_upper: int,
) -> tuple[int, int]:
    return resolve_required_int_bounds(
        params,
        GENERATION_DEFAULTS,
        min_key=lower_key,
        max_key=upper_key,
        fallback_min=fallback_lower,
        fallback_max=fallback_upper,
        context=f"generation defaults for {SCENE_NAMESPACE}",
    )
