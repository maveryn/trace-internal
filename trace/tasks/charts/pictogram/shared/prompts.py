"""Prompt assembly for pictogram tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.shared.prompt_variants import (
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .waffle_chart import SCENE_ID, _PROMPT_DEFAULTS


DOMAIN = "charts"
PROMPT_BUNDLE_ID = "charts_pictogram_v1"

_OBJECT_DESCRIPTIONS = {
    "waffle_grid_blocks": "a repeated-mark quantity chart where each colored block represents the unit scale shown in the legend",
    "pictogram_rows": "a repeated-mark pictogram where each icon represents the unit scale shown in the legend",
}


def dynamic_slots(*, dataset, scene_variant: str) -> dict[str, Any]:
    qparams = dict(dataset.query.params)
    return {
        "object_description": str(_OBJECT_DESCRIPTIONS[str(scene_variant)]),
        "category_label": str(qparams.get("target_category_label", "")),
        "category_label_a": str(qparams.get("category_label_a", "")),
        "category_label_b": str(qparams.get("category_label_b", "")),
        "threshold_phrase": str(qparams.get("threshold_phrase", "")),
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
        scene_key="pictogram_scene",
        task_key="pictogram_quantity_query",
        query_key=str(prompt_query_key),
        dynamic_slots=dict(dynamic_slot_values),
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(rendered_prompt)


__all__ = ["build_prompt_artifacts", "dynamic_slots"]
