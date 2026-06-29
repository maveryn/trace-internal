"""Prompt artifact assembly for code-grid puzzle tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.shared.config_defaults import required_group_default
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)

from .state import DOMAIN, SCENE_ID


def render_code_grid_prompt_artifacts(
    *,
    prompt_defaults: Mapping[str, Any],
    prompt_task_key: str,
    prompt_query_key: str,
    dynamic_slots: Mapping[str, object],
    instance_seed: int,
) -> PromptTraceArtifacts:
    """Render prompt variants from the code-grid prompt bundle."""

    object_description = required_group_default(
        prompt_defaults,
        "object_description",
        context="code-grid prompt defaults",
    )
    prompt_selection = render_task_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_task_key),
        query_key=str(prompt_query_key),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            "object_description": str(object_description),
            **{str(key): value for key, value in dict(dynamic_slots).items()},
        },
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(prompt_selection)


__all__ = ["render_code_grid_prompt_artifacts"]
