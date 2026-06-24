"""Prompt assembly for split-triangle trig-chain tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.tasks.shared.prompt_json_example import build_keyed_point_prompt_json_examples
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .defaults import PROMPT_BUNDLE_ID, SCENE_PROMPT_KEY, TASK_PROMPT_KEY
from .state import DOMAIN, SCENE_ID


def build_split_triangle_trig_prompt_artifacts(
    *,
    prompt_defaults: Mapping[str, Any],
    prompt_branch_key: str,
    target_name: str,
    annotation_roles: Sequence[str],
    answer_value: float | int,
    instance_seed: int,
):
    """Render v1 prompt variants after the public task chooses its branch."""

    annotation_keys = tuple(str(role) for role in annotation_roles)
    json_example, json_example_answer_only = build_keyed_point_prompt_json_examples(
        annotation_keys=annotation_keys,
        answer=answer_value,
    )
    annotation_key_list = ", ".join(f'"{key}"' for key in annotation_keys)
    prompt_selection = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults.get("bundle_id", PROMPT_BUNDLE_ID)),
        scene_key=str(prompt_defaults.get("scene_key", SCENE_PROMPT_KEY)),
        task_key=str(prompt_defaults.get("task_key", TASK_PROMPT_KEY)),
        query_key=str(prompt_branch_key),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            "target_name": str(target_name),
            "annotation_key_list": str(annotation_key_list),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        },
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(prompt_selection)


__all__ = ["build_split_triangle_trig_prompt_artifacts"]

