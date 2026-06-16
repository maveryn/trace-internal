"""Prompt assembly for marker-map chart tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.scene_config import get_scene_defaults
from trace.tasks.shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.prompt_variants import (
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .defaults import SCENE_ID, SCENE_NAMESPACE


DOMAIN = "charts"
PROMPT_BUNDLE_ID = "charts_marker_map_v1"
_DEFAULTS = get_scene_defaults(DOMAIN, SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _DEFAULTS if isinstance(_DEFAULTS, Mapping) else {},
)


def dynamic_slots(dataset: Mapping[str, Any]) -> dict[str, Any]:
    question_params = dict(dataset.get("question_params", {}))
    return {
        "object_description": str(dataset.get("map_object_description") or "a map with marker bubbles"),
        "region_noun": str(dataset.get("map_region_noun") or "regions"),
        "threshold_phrase": str(question_params.get("threshold_phrase", "")),
        "extremum_word": str(question_params.get("extremum_word", "")),
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
        scene_key="marker_map_scene",
        task_key="marker_map_query",
        query_key=str(prompt_query_key),
        dynamic_slots=dict(dynamic_slot_values),
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(rendered_prompt)


__all__ = ["build_prompt_artifacts", "dynamic_slots"]
