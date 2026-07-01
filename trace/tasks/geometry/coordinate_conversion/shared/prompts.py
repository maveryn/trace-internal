"""Prompt default helpers for coordinate-conversion tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.shared.config_defaults import required_group_defaults
from trace.tasks.shared.prompt_json_example import resolve_prompt_json_examples
from trace.tasks.shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants


def resolve_coordinate_prompt_defaults(
    *,
    prompt_defaults_all: Mapping[str, Any],
    annotation_value: Any,
    object_description_key: str,
    annotation_hint_key: str,
    context: str,
) -> tuple[dict[str, Any], str, str]:
    """Resolve prompt defaults and JSON examples without selecting query semantics."""

    defaults = required_group_defaults(
        prompt_defaults_all,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            str(object_description_key),
            "answer_hint_number",
            str(annotation_hint_key),
        ),
        context=str(context),
    )
    json_example, json_example_answer_only = resolve_prompt_json_examples(
        prompt_defaults_all,
        annotation_value=annotation_value,
        answer_type="number",
    )
    return dict(defaults), str(json_example), str(json_example_answer_only)


def coordinate_prompt_artifacts(
    *,
    prompt_defaults_all: Mapping[str, Any],
    prompt_query_key: str,
    annotation_value: Any,
    object_description_key: str,
    annotation_hint_key: str,
    context: str,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Any:
    """Render coordinate-conversion prompt variants from caller-owned semantics."""

    defaults, json_example, json_example_answer_only = resolve_coordinate_prompt_defaults(
        prompt_defaults_all=prompt_defaults_all,
        annotation_value=annotation_value,
        object_description_key=str(object_description_key),
        annotation_hint_key=str(annotation_hint_key),
        context=str(context),
    )
    prompt_selection = render_scene_prompt_variants(
        domain="geometry",
        scene_id="coordinate_conversion",
        bundle_id=str(defaults["bundle_id"]),
        scene_key=str(defaults["scene_key"]),
        task_key=str(defaults["task_key"]),
        query_key=str(prompt_query_key),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            "object_description": str(defaults[str(object_description_key)]),
            "json_output_contract": str(defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(defaults[str(annotation_hint_key)]),
            "answer_hint": str(defaults["answer_hint_number"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        },
        instance_seed=int(instance_seed),
        preferred_mode=str(params.get("prompt_mode", "answer_and_annotation")),
    )
    return build_prompt_trace_artifacts(prompt_selection)


__all__ = ["coordinate_prompt_artifacts", "resolve_coordinate_prompt_defaults"]
