"""Prompt assembly for radial Sankey tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.shared.prompt_variants import (
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .radial_sankey_common import SCENE_ID, _PROMPT_DEFAULTS


DOMAIN = "charts"
PROMPT_BUNDLE_ID = "charts_radial_sankey_v1"


def dynamic_slots(*, dataset: Mapping[str, Any]) -> dict[str, Any]:
    query = dict(dataset["query"])
    return {
        "object_description": (
            "a radial Sankey-style flow diagram. Source nodes and target nodes are labeled around a ring, "
            "and each curved band has a printed integer flow value"
        ),
        "source_label": str(query.get("source_label", "")),
        "target_label": str(query.get("target_label", "")),
        "source_labels": str(query.get("source_labels_joined", "")),
        "target_labels": str(query.get("target_labels_joined", "")),
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
        scene_key="radial_sankey",
        task_key="radial_sankey_query",
        query_key=str(prompt_query_key),
        dynamic_slots=dict(dynamic_slot_values),
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(rendered_prompt)


__all__ = ["build_prompt_artifacts", "dynamic_slots"]
