"""Prompt helpers for graph option-panel scenes."""

from __future__ import annotations

from ....shared.prompt_variants import PROMPT_OUTPUT_MODES, PromptTraceArtifacts, build_prompt_trace_artifacts, render_scene_prompt_variants
from .state import SCENE_ID


PROMPT_BUNDLE_ID = "graph_options_v1"
SCENE_PROMPT_KEY = "graph_options"
TASK_PROMPT_KEY = "structure_match_label_query"


def build_graph_options_prompt_artifacts(
    *,
    domain: str,
    bundle_id: str,
    prompt_key: str,
    object_description: str,
    instance_seed: int,
) -> PromptTraceArtifacts:
    """Render prompt variants for one graph-option objective."""

    prompt_selection = render_scene_prompt_variants(
        domain=str(domain),
        scene_id=SCENE_ID,
        bundle_id=str(bundle_id),
        scene_key=SCENE_PROMPT_KEY,
        task_key=TASK_PROMPT_KEY,
        query_key=str(prompt_key),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={"object_description": str(object_description)},
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(prompt_selection)


__all__ = [
    "PROMPT_BUNDLE_ID",
    "SCENE_PROMPT_KEY",
    "TASK_PROMPT_KEY",
    "build_graph_options_prompt_artifacts",
]
