"""Prompt rendering for parallel-segment proportion tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.shared.config_defaults import required_group_defaults
from trace.tasks.shared.prompt_json_example import dump_prompt_json_examples
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .defaults import DOMAIN, SCENE_ID


def parallel_segment_prompt_artifacts(
    *,
    prompt_defaults: Mapping[str, Any],
    prompt_task_key: str,
    object_description: str,
    target_name: str,
    variable_name: str,
    answer: float,
    instance_seed: int,
) -> tuple[dict[str, Any], PromptTraceArtifacts]:
    """Render v1 prompt variants for one public task."""

    defaults = required_group_defaults(
        prompt_defaults,
        ("bundle_id", "scene_key"),
        context="prompt defaults for parallel_segment_proportion",
    )
    example_annotation = [
        [410, 120],
        [175, 430],
        [645, 430],
        [285, 265],
        [535, 265],
    ]
    json_example, json_example_answer_only = dump_prompt_json_examples(
        annotation=example_annotation,
        answer=int(answer) if abs(float(answer) - round(float(answer))) <= 1e-9 else float(answer),
    )
    annotation_hint = (
        "set \"annotation\" to a JSON array of exactly five pixel points [x, y]; "
        "the points should mark the visible construction points A, B, C, D, and E"
    )
    prompt_selection = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(defaults["bundle_id"]),
        scene_key=str(defaults["scene_key"]),
        task_key=str(prompt_task_key),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            "annotation_hint": str(annotation_hint),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
            "object_description": str(object_description),
            "target_name": str(target_name),
            "variable_name": str(variable_name),
        },
        instance_seed=int(instance_seed),
    )
    return dict(defaults), build_prompt_trace_artifacts(prompt_selection)


__all__ = ["parallel_segment_prompt_artifacts"]
