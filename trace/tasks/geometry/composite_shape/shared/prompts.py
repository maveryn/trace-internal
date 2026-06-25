"""Prompt artifact construction for composite-shape tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from trace.tasks.shared.config_defaults import required_group_defaults
from trace.tasks.shared.prompt_json_example import dump_prompt_json_examples
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .defaults import SCENE_ID
from .measurements import numeric_prompt_slots


def _prompt_examples(
    *,
    annotation_type: str,
    annotation_keys: Sequence[str],
    answer: int | float,
) -> tuple[str, str]:
    if str(annotation_type) == "point_map":
        annotation = {
            str(key): [120.0 + (42.0 * index), 180.0 + (22.0 * index)]
            for index, key in enumerate(annotation_keys or ("A", "B"))
        }
    elif str(annotation_type) == "bbox_map":
        annotation = {}
        for index, key in enumerate(annotation_keys or ("target_shape",)):
            x0 = 70.0 + (70.0 * index)
            y0 = 90.0 + (24.0 * index)
            annotation[str(key)] = [x0, y0, x0 + 58.0, y0 + 38.0]
    else:
        annotation = [[70.0, 90.0, 128.0, 128.0]]
    return dump_prompt_json_examples(annotation=annotation, answer=answer, ensure_ascii=False)


def composite_shape_prompt_artifacts(
    *,
    prompt_defaults: Mapping[str, Any],
    prompt_query_key: str,
    annotation_type: str,
    annotation_keys: Sequence[str],
    answer_value: int | float,
    prompt_slots: Mapping[str, Any],
    instance_seed: int,
) -> tuple[Dict[str, Any], Any]:
    """Render prompt variants using external scene and task prompt assets."""

    defaults = required_group_defaults(
        prompt_defaults,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "object_description",
            "json_output_contract",
            "json_output_contract_answer_only",
            "annotation_hint",
        ),
        context="prompt defaults for composite shape",
    )
    answer_hint = defaults.get("answer_hint_integer", defaults.get("answer_hint_number", defaults.get("answer_hint", "")))
    json_example = str(defaults.get("json_example", ""))
    json_example_answer_only = str(defaults.get("json_example_answer_only", ""))
    if not json_example or not json_example_answer_only:
        json_example, json_example_answer_only = _prompt_examples(
            annotation_type=str(annotation_type),
            annotation_keys=tuple(str(key) for key in annotation_keys),
            answer=answer_value,
        )
    annotation_key_list = ", ".join(f'"{key}"' for key in annotation_keys)
    annotation_hint_template = str(defaults["annotation_hint"])
    annotation_hint = (
        annotation_hint_template.format(annotation_keys=annotation_key_list)
        if "{annotation_keys}" in annotation_hint_template
        else annotation_hint_template
    )
    slots = {
        "object_description": str(defaults["object_description"]),
        "json_output_contract": str(defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(defaults["json_output_contract_answer_only"]),
        "annotation_hint": str(annotation_hint),
        "answer_hint": str(answer_hint),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
        **numeric_prompt_slots(prompt_slots),
        **{str(key): value for key, value in prompt_slots.items()},
    }
    prompt_selection = render_scene_prompt_variants(
        domain="geometry",
        scene_id=SCENE_ID,
        bundle_id=str(defaults["bundle_id"]),
        scene_key=str(defaults["scene_key"]),
        task_key=str(defaults["task_key"]),
        query_key=str(prompt_query_key),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    return dict(defaults), build_prompt_trace_artifacts(prompt_selection)
