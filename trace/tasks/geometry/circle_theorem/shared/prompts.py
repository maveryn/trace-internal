"""Prompt assembly helpers for circle-theorem tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from trace.tasks.shared.config_defaults import required_group_defaults
from trace.tasks.shared.prompt_json_example import dump_prompt_json_examples
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .defaults import PROMPT_DEFAULTS
from .state import DOMAIN, SCENE_ID


def _keyed_point_prompt_examples(
    annotation_keys: Sequence[str], *, answer: int | float
) -> tuple[str, str]:
    """Build JSON examples using the requested visible point-label keys."""

    example_points = {
        str(key): [120 + (37 * index), 180 + (23 * index)]
        for index, key in enumerate(annotation_keys)
    }
    return dump_prompt_json_examples(
        annotation=example_points,
        answer=answer,
        ensure_ascii=False,
    )


def build_circle_theorem_prompt_artifacts(
    *,
    prompt_query_key: str,
    prompt_slots: Mapping[str, Any],
    annotation_keys: Sequence[str],
    answer_hint_key: str,
    answer_example: int | float,
    annotation_hint_key: str = "annotation_hint_circle_points",
    object_description_key: str = "object_description",
    instance_seed: int,
) -> tuple[Dict[str, Any], Any]:
    """Build prompt artifacts for one task-owned circle-theorem query."""

    prompt_defaults = required_group_defaults(
        PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            object_description_key,
            "json_output_contract",
            "json_output_contract_answer_only",
            answer_hint_key,
            annotation_hint_key,
        ),
        context="circle_theorem prompt wiring defaults",
    )
    key_text = ", ".join(f'"{key}"' for key in annotation_keys)
    annotation_hint = str(prompt_defaults[annotation_hint_key]).format(
        annotation_point_keys=key_text,
        annotation_keys=key_text,
    )
    json_example, json_example_answer_only = _keyed_point_prompt_examples(
        annotation_keys,
        answer=answer_example,
    )
    prompt_selection = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(prompt_query_key),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_defaults[object_description_key]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(annotation_hint),
            "answer_hint": str(prompt_defaults[answer_hint_key]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
            **dict(prompt_slots),
        },
        instance_seed=int(instance_seed),
    )
    return dict(prompt_defaults), build_prompt_trace_artifacts(prompt_selection)


__all__ = ["build_circle_theorem_prompt_artifacts"]
