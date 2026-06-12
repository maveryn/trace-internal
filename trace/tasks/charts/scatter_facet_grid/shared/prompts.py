"""Prompt assembly for scatter-facet-grid chart tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.shared.prompt_variants import (
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .facet_grid_query import _Dataset, _PROMPT_DEFAULTS


DOMAIN = "charts"
SCENE_ID = "scatter_facet_grid"
PROMPT_BUNDLE_ID = "charts_scatter_facet_grid_v1"


def dynamic_slots(*, dataset: _Dataset) -> dict[str, Any]:
    return {
        "object_description": (
            "a grid of small scatter panels with shared x- and y-axes and a highlighted target region in each panel"
        ),
        "target_region_phrase": str(dataset.query.trace["target_region_phrase"]),
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
        scene_key="scatter_facet_grid",
        task_key="scatter_facet_grid_query",
        query_key=str(prompt_query_key),
        dynamic_slots=dict(dynamic_slot_values),
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(rendered_prompt)


__all__ = ["build_prompt_artifacts", "dynamic_slots"]
