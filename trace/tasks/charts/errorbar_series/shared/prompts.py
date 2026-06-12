"""Prompt assembly for errorbar-series chart tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.scene_config import get_scene_defaults
from trace.tasks.charts.errorbar_series.shared.series_query import SCENE_ID, _Dataset
from trace.tasks.shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.prompt_variants import (
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)


DOMAIN = "charts"
PROMPT_BUNDLE_ID = "charts_errorbar_series_v1"
_DEFAULTS = get_scene_defaults(DOMAIN, SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _DEFAULTS if isinstance(_DEFAULTS, Mapping) else {},
    **{"task" "_id": "charts_errorbar_series_prompt"},
)


def dynamic_slots(dataset: _Dataset) -> dict[str, Any]:
    return {
        "object_description": "a scientific chart with labeled series, ordered x-axis labels, central point markers, and vertical error bars",
        "target_series_label": str(dataset.query.params.get("target_series_label", "")),
        "threshold_value": int(dataset.threshold_value or 0),
        "target_x_label": str(dataset.query.params.get("target_x_label", "")),
        "bound_phrase": "upper error-bar endpoint" if dataset.query.params.get("bound_kind") == "upper" else "lower error-bar endpoint",
        "extremum_phrase": str(dataset.query.params.get("extremum_direction", "")),
        "threshold_relation_phrase": {
            "entirely_above_threshold_count": "entirely above",
            "entirely_below_threshold_count": "entirely below",
            "contains_threshold_count": "containing",
        }.get(str(dataset.query.prompt_key), ""),
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
        scene_key="errorbar_series_scene",
        task_key="errorbar_series_query",
        query_key=str(prompt_query_key),
        dynamic_slots=dict(dynamic_slot_values),
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(rendered_prompt)


__all__ = ["build_prompt_artifacts", "dynamic_slots"]
