"""Prompt assembly for dumbbell chart tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.scene_config import get_scene_defaults
from trace.tasks.charts.dumbbell.shared.pairwise_comparison_query import SCENE_ID, _Dataset
from trace.tasks.shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.prompt_variants import (
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)


DOMAIN = "charts"
PROMPT_BUNDLE_ID = "charts_dumbbell_v1"
_DEFAULTS = get_scene_defaults(DOMAIN, SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _DEFAULTS if isinstance(_DEFAULTS, Mapping) else {},
    **{"task" "_id": "charts_dumbbell_prompt"},
)


def dynamic_slots(dataset: _Dataset) -> dict[str, Any]:
    params = dict(dataset.query.params)
    winner_series = str(dataset.series_a_name)
    loser_series = str(dataset.series_b_name)
    if str(params.get("side_direction")) == "series_b_greater":
        winner_series = str(dataset.series_b_name)
        loser_series = str(dataset.series_a_name)
    gap_relation = "at least" if str(params.get("gap_threshold_relation")) == "at_least" else "at most"
    return {
        "object_description": (
            "a horizontal dumbbell chart. Each row is a category label, and the two colored dots on that row "
            "give the values for the two legend series on the shared horizontal numeric axis. The gray "
            "connector shows the gap between the two dots"
        ),
        "rank_phrase": str(params.get("rank_phrase", "second largest")),
        "winner_series": str(winner_series),
        "loser_series": str(loser_series),
        "threshold_value": int(params.get("threshold_value", 0) or 0),
        "gap_relation_phrase": str(gap_relation),
        "gap_threshold_value": int(params.get("gap_threshold_value", 0) or 0),
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
        scene_key="dumbbell_pairwise_chart",
        task_key="dumbbell_pairwise_comparison_query",
        query_key=str(prompt_query_key),
        dynamic_slots=dict(dynamic_slot_values),
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(rendered_prompt)


__all__ = ["build_prompt_artifacts", "dynamic_slots"]
