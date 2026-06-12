"""Prompt assembly for error-interval chart tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.scene_config import get_scene_defaults
from trace.tasks.charts.error_interval.shared.interval_chart import (
    SCENE_ID,
    _Dataset,
    error_interval_query_phrase,
)
from trace.tasks.shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.prompt_variants import (
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)


DOMAIN = "charts"
PROMPT_BUNDLE_ID = "charts_error_interval_v1"
_DEFAULTS = get_scene_defaults(DOMAIN, SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _DEFAULTS if isinstance(_DEFAULTS, Mapping) else {},
    **{"task" "_id": "charts_error_interval_prompt"},
)


def _object_description(scene_variant: str) -> str:
    return {
        "horizontal_forest": "a horizontal interval chart with labeled categories, point estimates, and lower-to-upper interval whiskers",
        "vertical_dot_whisker": "a vertical dot-and-whisker interval chart with labeled categories and printed interval endpoints",
        "bar_with_error": "a bar chart with error bars, labeled categories, and printed interval endpoints",
    }[str(scene_variant)]


def dynamic_slots(dataset: _Dataset) -> dict[str, Any]:
    return {
        "object_description": _object_description(str(dataset.scene_variant)),
        "reference_value": int(dataset.reference_value or 0),
        "relation_phrase": error_interval_query_phrase(str(dataset.query.prompt_key)),
    }


def build_prompt_artifacts(
    *,
    prompt_query_key: str,
    dynamic_slot_values: Mapping[str, Any],
    instance_seed: int,
) -> PromptTraceArtifacts:
    rendered_prompt = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(_PROMPT_DEFAULTS.get("bundle_id", PROMPT_BUNDLE_ID)),
        scene_key="error_interval_scene",
        task_key="error_interval_query",
        query_key=str(prompt_query_key),
        dynamic_slots=dict(dynamic_slot_values),
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(rendered_prompt)


__all__ = ["build_prompt_artifacts", "dynamic_slots"]
