"""Prompt rendering for polygon angle-chase tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.tasks.shared.config_defaults import required_group_defaults
from trace.tasks.shared.prompt_json_example import dump_prompt_json_examples
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .defaults import DOMAIN, SCENE_ID


def angle_chase_prompt_artifacts(
    *,
    prompt_defaults: Mapping[str, Any],
    prompt_task_key: str,
    prompt_query_key: str,
    dynamic_slots: Mapping[str, Any],
    annotation_keys: Sequence[str],
    answer: int,
    instance_seed: int,
) -> tuple[dict[str, Any], PromptTraceArtifacts]:
    """Render v1 prompt variants for one polygon angle-chase task."""

    defaults = required_group_defaults(
        prompt_defaults,
        ("bundle_id", "scene_key"),
        context="prompt defaults for polygon_angle_chase",
    )
    annotation = {
        str(key): [120 + (index * 45), 180 + (index * 18)]
        for index, key in enumerate(annotation_keys)
    }
    json_example, json_example_answer_only = dump_prompt_json_examples(
        annotation=annotation,
        answer=int(answer),
        ensure_ascii=False,
    )
    prompt_selection = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(defaults["bundle_id"]),
        scene_key=str(defaults["scene_key"]),
        task_key=str(prompt_task_key),
        query_key=str(prompt_query_key),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            **dict(dynamic_slots),
            "annotation_keys": ", ".join(f'"{key}"' for key in annotation_keys),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        },
        instance_seed=int(instance_seed),
    )
    return dict(defaults), build_prompt_trace_artifacts(prompt_selection)


__all__ = ["angle_chase_prompt_artifacts"]
