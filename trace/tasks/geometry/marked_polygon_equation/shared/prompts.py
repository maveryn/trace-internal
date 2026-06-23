"""Prompt rendering for marked polygon equation tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.tasks.shared.config_defaults import required_group_defaults
from trace.tasks.shared.prompt_json_example import build_keyed_point_prompt_json_examples
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .defaults import DOMAIN, SCENE_ID


def number_answer(value: int | float) -> int | float:
    """Normalize exact integer-like numeric answers for prompts and verifier payloads."""

    rounded = round(float(value), 1)
    if abs(rounded - round(rounded)) < 1e-9:
        return int(round(rounded))
    return float(rounded)


def marked_equation_prompt_artifacts(
    *,
    prompt_defaults: Mapping[str, Any],
    prompt_task_key: str,
    prompt_question_key: str,
    annotation_keys: Sequence[str],
    target_name: str,
    variable_name: str,
    answer: int | float,
    instance_seed: int,
) -> tuple[dict[str, Any], PromptTraceArtifacts]:
    """Render v1 prompt variants from scene/task/query prompt assets."""

    defaults = required_group_defaults(
        prompt_defaults,
        ("bundle_id", "scene_key", "task_key"),
        context="prompt defaults for marked_polygon_equation",
    )
    json_example, json_example_answer_only = build_keyed_point_prompt_json_examples(
        annotation_keys=tuple(str(key) for key in annotation_keys),
        answer=number_answer(answer),
    )
    annotation_key_list = ", ".join(f'"{key}"' for key in annotation_keys)
    annotation_hint = (
        "set \"annotation\" to a JSON object with exactly these visible point-label keys: "
        f"{annotation_key_list}; each value must be that labeled construction point's pixel point [x,y]"
    )
    prompt_selection = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(defaults["bundle_id"]),
        scene_key=str(defaults["scene_key"]),
        task_key=str(prompt_task_key),
        query_key=str(prompt_question_key),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            "annotation_hint": str(annotation_hint),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
            "target_name": str(target_name),
            "variable_name": str(variable_name),
        },
        instance_seed=int(instance_seed),
    )
    return dict(defaults), build_prompt_trace_artifacts(prompt_selection)


__all__ = ["marked_equation_prompt_artifacts", "number_answer"]
