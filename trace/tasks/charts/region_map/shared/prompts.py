"""Prompt assembly for region-map chart tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.scene_config import get_scene_defaults
from trace.tasks.shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.prompt_variants import (
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)


DOMAIN = "charts"
SCENE_ID = "region_map"
PROMPT_BUNDLE_ID = "charts_region_map_v1"
SCENE_PROMPT_KEY = "region_map_scene"
TASK_PROMPT_KEY = "region_map_query"

_DEFAULTS = get_scene_defaults(DOMAIN, SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _DEFAULTS if isinstance(_DEFAULTS, Mapping) else {},
    task_id=f"{SCENE_ID}_prompt",
)


def dynamic_slots(*, dataset: Mapping[str, Any], query_id: str, scene_variant: str) -> dict[str, Any]:
    question_params = dict(dataset.get("question_params", {}))
    if _is_region_value_query(str(query_id)):
        object_description = "a map with colored regions, visible region labels, visible integer values, and a legend"
    elif str(query_id) == "group_filtered_region_value":
        object_description = "a world map with selected countries colored by value, visible integer values, and a legend"
    elif str(scene_variant) == "geographic_region_map":
        object_description = str(dataset.get("map_object_description") or "a geographic map with selected colored regions and a legend")
        if _is_categorical_query(str(query_id)):
            object_description = object_description.replace(
                "colored by value and a color legend",
                "colored by category and a category legend",
            )
    else:
        object_description = "a synthetic map with colored regions and a legend"
    return {
        "object_description": str(object_description),
        "region_noun": str(dataset.get("map_region_noun") or ("countries" if str(scene_variant) == "geographic_region_map" else "regions")),
        "continent_label": str(question_params.get("continent_label", "")),
        "threshold_phrase": str(question_params.get("threshold_phrase", "")),
        "interval_phrase": str(question_params.get("interval_phrase", "")),
        "category_label": str(question_params.get("category_label", "")),
        "region_set_name": str(question_params.get("region_set_name", "")),
        "region_set_label_list": str(question_params.get("region_set_label_list", "")),
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
        scene_key=SCENE_PROMPT_KEY,
        task_key=TASK_PROMPT_KEY,
        query_key=str(prompt_query_key),
        dynamic_slots=dict(dynamic_slot_values),
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(rendered_prompt)


def _is_categorical_query(query_id: str) -> bool:
    return str(query_id) in {
        "categorical_region_count",
        "continent_category_region_count",
        "adjacent_same_category_count",
        "adjacent_category_count",
    }


def _is_region_value_query(query_id: str) -> bool:
    return str(query_id) in {"named_region_set_total_value", "group_filtered_region_value"}


__all__ = ["build_prompt_artifacts", "dynamic_slots"]
