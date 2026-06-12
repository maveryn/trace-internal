"""Prompt assembly helpers for darts scene tasks."""

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


def build_darts_prompt_json_examples(*, prompt_query_key: str) -> Tuple[str, str]:
    """Return prompt JSON examples matching the active darts query semantics."""

    if str(prompt_query_key) == "total_score":
        answer_and_annotation = {"annotation": [[411, 219]], "answer": "C"}
        answer_only = {"answer": "C"}
    else:
        answer_and_annotation = {"annotation": [[411, 219], [525, 364]], "answer": 2}
        answer_only = {"answer": 2}
    return (
        json.dumps(answer_and_annotation, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def darts_target_ring_prompt_text(target_ring: str | None) -> str:
    """Return natural prompt text for one target dartboard ring family."""

    if target_ring is None:
        return ""
    return {
        "single": "single area",
        "double": "double ring",
        "triple": "triple ring",
        "bull": "bull area",
    }.get(str(target_ring), str(target_ring).replace("_", " "))


def build_darts_prompt_artifacts(
    *,
    domain: str,
    scene_variant: str,
    prompt_query_key: str,
    target_ring: str | None,
    target_threshold: int | None,
    instance_seed: int,
) -> tuple[Dict[str, Any], Any]:
    """Build prompt artifacts for one objective-owned darts task file."""

    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description_single_board",
            "scoring_rule_text",
            "ring_rule_text",
            "answer_hint_total_score",
            "answer_hint_ring_count",
            "answer_hint_threshold_score_count",
            "annotation_hint_total_score",
            "annotation_hint_ring_count",
            "annotation_hint_threshold_score_count",
        ),
        context="darts prompt wiring defaults",
    )
    json_example, json_example_answer_only = build_darts_prompt_json_examples(prompt_query_key=str(prompt_query_key))
    prompt_slots = {
        "object_description": str(prompt_defaults[f"object_description_{str(scene_variant)}"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults[f"answer_hint_{str(prompt_query_key)}"]),
        "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(prompt_query_key)}"]),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
        "scoring_rule_text": str(prompt_defaults["scoring_rule_text"]),
        "ring_rule_text": str(prompt_defaults["ring_rule_text"]),
        "target_ring_text": darts_target_ring_prompt_text(target_ring),
        "target_threshold_text": "" if target_threshold is None else str(target_threshold),
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


__all__ = [
    "build_darts_prompt_artifacts",
    "build_darts_prompt_json_examples",
    "darts_target_ring_prompt_text",
]
