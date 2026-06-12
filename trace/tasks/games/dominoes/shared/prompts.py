"""Prompt assembly helpers for dominoes scene tasks."""

from __future__ import annotations

import json
from typing import Any, Dict, Tuple

from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults, required_group_defaults
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .state import SCENE_ID


_GEN_DEFAULTS_UNUSED, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
)


def build_domino_prompt_json_examples(*, query_id: str) -> Tuple[str, str]:
    """Return prompt JSON examples matching the active domino query semantics."""

    if str(query_id) == "matching_end_count":
        answer_and_annotation = {
            "annotation": [
                [248, 318, 386, 394],
                [408, 318, 546, 394],
            ],
            "answer": 2,
        }
        answer_only = {"answer": 2}
    elif str(query_id) == "higher_sum_than_reference_count":
        answer_and_annotation = {
            "annotation": [
                [248, 318, 386, 394],
                [408, 318, 546, 394],
                [568, 318, 706, 394],
            ],
            "answer": 3,
        }
        answer_only = {"answer": 3}
    elif str(query_id) == "sum_to_target_count":
        answer_and_annotation = {
            "annotation": [
                [248, 318, 386, 394],
                [408, 318, 546, 394],
                [568, 318, 706, 394],
            ],
            "answer": 3,
        }
        answer_only = {"answer": 3}
    elif str(query_id) == "second_play_candidate_count":
        answer_and_annotation = {
            "annotation": [
                [408, 318, 546, 394],
                [568, 318, 706, 394],
            ],
            "answer": 2,
        }
        answer_only = {"answer": 2}
    elif str(query_id) == "extendable_first_play_count":
        answer_and_annotation = {
            "annotation": [
                [248, 318, 386, 394],
                [568, 318, 706, 394],
            ],
            "answer": 2,
        }
        answer_only = {"answer": 2}
    else:
        answer_and_annotation = {
            "annotation": [
                [248, 318, 386, 394],
                [408, 318, 546, 394],
            ],
            "answer": 2,
        }
        answer_only = {"answer": 2}
    return (
        json.dumps(answer_and_annotation, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )




def build_domino_prompt_artifacts(
    *,
    domain: str,
    scene_variant: str,
    prompt_query_key: str,
    target_total: int | None,
    instance_seed: int,
) -> tuple[Dict[str, Any], Any]:
    """Build prompt artifacts for one objective-owned dominoes task file."""

    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description_single_row",
            "object_description_two_row",
            "connection_rule_text",
            "pip_sum_rule_text",
            "double_rule_text",
            "second_play_rule_text",
            "extendable_first_play_rule_text",
            "answer_hint_matching_end_count",
            "answer_hint_higher_sum_than_reference_count",
            "answer_hint_sum_to_target_count",
            "answer_hint_double_count",
            "answer_hint_second_play_candidate_count",
            "answer_hint_extendable_first_play_count",
            "annotation_hint_matching_end_count",
            "annotation_hint_higher_sum_than_reference_count",
            "annotation_hint_sum_to_target_count",
            "annotation_hint_double_count",
            "annotation_hint_second_play_candidate_count",
            "annotation_hint_extendable_first_play_count",
        ),
        context="dominoes prompt wiring defaults",
    )
    json_example, json_example_answer_only = build_domino_prompt_json_examples(query_id=str(prompt_query_key))
    prompt_slots = {
        "object_description": str(prompt_defaults[f"object_description_{str(scene_variant)}"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults[f"answer_hint_{str(prompt_query_key)}"]),
        "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(prompt_query_key)}"]),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
        "connection_rule_text": str(prompt_defaults["connection_rule_text"]),
        "pip_sum_rule_text": str(prompt_defaults["pip_sum_rule_text"]),
        "double_rule_text": str(prompt_defaults["double_rule_text"]),
        "second_play_rule_text": str(prompt_defaults["second_play_rule_text"]),
        "extendable_first_play_rule_text": str(prompt_defaults["extendable_first_play_rule_text"]),
        "target_total_text": "" if target_total is None else str(target_total),
    }
    prompt_selection = render_scene_prompt_variants(
        domain=str(domain),
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(prompt_query_key),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots=prompt_slots,
        instance_seed=int(instance_seed),
    )
    return dict(prompt_defaults), build_prompt_trace_artifacts(prompt_selection)


__all__ = ["build_domino_prompt_artifacts", "build_domino_prompt_json_examples"]
