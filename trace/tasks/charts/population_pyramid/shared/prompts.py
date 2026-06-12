"""Prompt assembly for population-pyramid tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.shared.prompt_variants import (
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .pyramid import SCENE_ID, _Dataset, _PROMPT_DEFAULTS


DOMAIN = "charts"
PROMPT_BUNDLE_ID = "charts_population_pyramid_v1"


def dynamic_slots(*, dataset: _Dataset) -> dict[str, Any]:
    qparams = dict(dataset.query.params)
    slots: dict[str, Any] = {
        "object_description": (
            "a mirrored horizontal bar chart with one row per age group. "
            "The left and right bars show the two legend series on the same positive scale"
        ),
        "rank_phrase": str(qparams.get("rank_phrase", "")),
        "metric_phrase": "",
        "threshold_relation_phrase": str(qparams.get("threshold_relation_phrase", "")),
        "threshold_value": int(qparams.get("threshold_value", 0)),
    }
    if str(dataset.query_id) == "left_side_threshold_count":
        slots["metric_phrase"] = f'the "{dataset.left_series_label}" value'
    elif str(dataset.query_id) == "right_side_threshold_count":
        slots["metric_phrase"] = f'the "{dataset.right_series_label}" value'
    elif str(dataset.query_id) == "combined_total_threshold_count":
        slots["metric_phrase"] = f'the sum of "{dataset.left_series_label}" and "{dataset.right_series_label}"'
    return slots


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
        scene_key="population_pyramid_scene",
        task_key="population_pyramid_query",
        query_key=str(prompt_query_key),
        dynamic_slots=dict(dynamic_slot_values),
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(rendered_prompt)


__all__ = ["build_prompt_artifacts", "dynamic_slots"]
