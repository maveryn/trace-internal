"""Prompt rendering for Pythagorean dissection tasks."""

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


def pythagorean_dissection_prompt_artifacts(
    *,
    prompt_defaults: Mapping[str, Any],
    prompt_task_key: str,
    annotation_keys: Sequence[str],
    answer: int,
    instance_seed: int,
) -> tuple[dict[str, Any], PromptTraceArtifacts]:
    """Render v1 prompt variants for the central-square area objective."""

    defaults = required_group_defaults(
        prompt_defaults,
        (
            "bundle_id",
            "scene_key",
            "json_output_contract",
            "json_output_contract_answer_only",
        ),
        context="prompt defaults for pythagorean_dissection",
    )
    key_list = ", ".join(f'"{key}"' for key in annotation_keys)
    annotation_hint = (
        f"set \"annotation\" to a JSON object with exactly these keys: {key_list}; "
        "each value must be a pixel bounding box [x0,y0,x1,y1] around that visual witness"
    )
    example_annotation = {
        "central_square": [310, 180, 470, 340],
        "leg_a_label": [220, 118, 286, 146],
        "leg_b_label": [390, 118, 476, 146],
    }
    json_example, json_example_answer_only = dump_prompt_json_examples(
        annotation=example_annotation,
        answer=int(answer),
        ensure_ascii=False,
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
            "answer_hint": "set \"answer\" to the area of the central square as an integer",
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        },
        instance_seed=int(instance_seed),
    )
    return dict(defaults), build_prompt_trace_artifacts(prompt_selection)


__all__ = ["pythagorean_dissection_prompt_artifacts"]
