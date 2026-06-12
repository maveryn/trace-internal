"""Prompt assembly for scatter-cluster chart tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.shared.prompt_variants import (
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .cluster_common import _PROMPT_DEFAULTS, _is_area_rank_query
from .cluster_common import _Dataset


DOMAIN = "charts"
SCENE_ID = "scatter_cluster"
PROMPT_BUNDLE_ID = "charts_scatter_cluster_v1"


def dynamic_slots(*, dataset: _Dataset) -> dict[str, Any]:
    trace = dict(dataset.query.trace)
    query_id = str(dataset.query.query_id)
    return {
        "object_description": (
            "a scatter plot with several colored point clusters, shaded cluster footprints, and a matching legend"
            if _is_area_rank_query(query_id)
            else "a scatter plot with several colored point clusters and a matching legend"
        ),
        "trend_direction_phrase": str(trace.get("trend_direction", "")),
        "reference_cluster_label": str(trace.get("reference_cluster_label", "")),
        "separation_extremum_phrase": "closest to"
        if str(trace.get("separation_extremum")) == "closest"
        else "farthest from",
        "spread_axis_phrase": str(trace.get("spread_axis", "")),
        "spread_extremum_phrase": str(trace.get("spread_extremum", "")),
        "area_rank_phrase": str(trace.get("area_rank_phrase", "")),
        "target_cluster_label": str(trace.get("target_cluster_label", "")),
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
        scene_key="scatter_cluster",
        task_key="scatter_cluster_query",
        query_key=str(prompt_query_key),
        dynamic_slots=dict(dynamic_slot_values),
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(rendered_prompt)


__all__ = ["build_prompt_artifacts", "dynamic_slots"]
