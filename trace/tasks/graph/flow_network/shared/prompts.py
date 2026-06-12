"""Prompt assembly helpers for flow-network graph tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .state import SCENE_ID


PROMPT_BUNDLE_ID = "graph_flow_network_v1"
SCENE_PROMPT_KEY = "capacity_network"
TASK_PROMPT_KEY = "flow_network_query"


def build_flow_network_prompt_artifacts(
    *,
    domain: str,
    bundle_id: str,
    prompt_key: str,
    dynamic_slots: Mapping[str, Any],
    instance_seed: int,
) -> Any:
    """Build prompt artifacts from task-provided dynamic slots."""

    prompt_selection = render_scene_prompt_variants(
        domain=str(domain),
        scene_id=SCENE_ID,
        bundle_id=str(bundle_id),
        scene_key=SCENE_PROMPT_KEY,
        task_key=TASK_PROMPT_KEY,
        query_key=str(prompt_key),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={str(key): value for key, value in dynamic_slots.items()},
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(prompt_selection)


__all__ = ["PROMPT_BUNDLE_ID", "build_flow_network_prompt_artifacts"]
