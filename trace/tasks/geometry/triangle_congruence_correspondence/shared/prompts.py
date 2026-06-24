"""Prompt assembly for triangle-congruence correspondence tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.tasks.shared.prompt_json_example import build_keyed_point_prompt_json_examples
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .state import DOMAIN, PROMPT_BUNDLE_ID, SCENE_ID, SCENE_PROMPT_KEY


def build_triangle_congruence_prompt_artifacts(
    *,
    prompt_defaults: Mapping[str, Any],
    task_prompt_key: str,
    prompt_branch_key: str,
    annotation_labels: Sequence[str],
    answer_value: int,
    answer_hint_key: str,
    target_name: str,
    instance_seed: int,
):
    """Render v1 prompt variants for one triangle-congruence objective."""

    labels = tuple(str(label) for label in annotation_labels)
    annotation_key_list = ", ".join(f'"{label}"' for label in labels)
    json_example, json_example_answer_only = build_keyed_point_prompt_json_examples(
        annotation_keys=labels,
        answer=int(answer_value),
    )
    annotation_instruction = (
        "set \"annotation\" to a JSON object with exactly these visible point-label keys: "
        f"{annotation_key_list}; each value must be the pixel point [x,y] at that labeled point"
    )
    prompt_selection = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults.get("bundle_id", PROMPT_BUNDLE_ID)),
        scene_key=str(prompt_defaults.get("scene_key", SCENE_PROMPT_KEY)),
        task_key=str(task_prompt_key),
        query_key=str(prompt_branch_key),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            "annotation_instruction": str(annotation_instruction),
            "annotation_key_list": str(annotation_key_list),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
            "target_name": str(target_name),
        },
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(prompt_selection)


__all__ = ["build_triangle_congruence_prompt_artifacts"]
