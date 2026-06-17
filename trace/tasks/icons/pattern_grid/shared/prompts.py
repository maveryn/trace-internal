"""Prompt rendering helpers for the pattern-grid icons scene."""

from __future__ import annotations

from typing import Any, Mapping

from ....shared.config_defaults import required_group_defaults
from ....shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .defaults import DOMAIN, SCENE_ID


def render_pattern_grid_prompt_artifacts(
    *,
    instance_seed: int,
    prompt_defaults: Mapping[str, Any],
    question_text: str,
):
    """Render prompt variants for the selected pattern-grid query branch."""

    required = required_group_defaults(
        prompt_defaults,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description",
            "annotation_hint",
            "answer_hint",
            "json_example",
            "json_example_answer_only",
        ),
        context="pattern_grid prompt defaults",
    )
    selection = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(required["bundle_id"]),
        scene_key=str(required["scene_key"]),
        task_key=str(required["task_key"]),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(required["object_description"]),
            "question_text": str(question_text),
            "json_output_contract": str(required["json_output_contract"]),
            "json_output_contract_answer_only": str(required["json_output_contract_answer_only"]),
            "annotation_hint": str(required["annotation_hint"]),
            "answer_hint": str(required["answer_hint"]),
            "json_example": str(required["json_example"]),
            "json_example_answer_only": str(required["json_example_answer_only"]),
        },
        instance_seed=int(instance_seed),
    )
    return required, build_prompt_trace_artifacts(selection)


__all__ = ["render_pattern_grid_prompt_artifacts"]
