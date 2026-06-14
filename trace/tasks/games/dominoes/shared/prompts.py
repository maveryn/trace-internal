"""Prompt assembly helpers for dominoes scene tasks."""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping

from trace.tasks.shared.config_defaults import (
    load_scene_generation_rendering_prompt_defaults,
    required_group_default,
    required_group_defaults,
)
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .defaults import PROMPT_WIRING_KEYS, SCENE_ID


_GEN_DEFAULTS_UNUSED, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
)


def domino_integer_json_examples(answer_value: int = 2) -> tuple[str, str]:
    """Return generic integer-answer JSON examples for domino count tasks."""

    answer = int(answer_value)
    example_boxes = [
        [248, 318, 386, 394],
        [408, 318, 546, 394],
        [568, 318, 706, 394],
        [728, 318, 866, 394],
    ][: max(0, int(answer))]
    return (
        json.dumps({"annotation": example_boxes, "answer": answer}, separators=(",", ":")),
        json.dumps({"answer": answer}, separators=(",", ":")),
    )


def domino_option_label_point_pair_json_examples(answer_value: str = "C") -> tuple[str, str]:
    """Return generic option-label JSON examples for point-pair annotation tasks."""

    return (
        json.dumps({"annotation": [[[312, 142], [326, 142]]], "answer": str(answer_value)}, separators=(",", ":")),
        json.dumps({"answer": str(answer_value)}, separators=(",", ":")),
    )


def domino_output_slots(
    *,
    prompt_query_key: str,
    json_example: str,
    json_example_answer_only: str,
) -> Dict[str, Any]:
    """Return answer and annotation prompt slots for one dominoes query key."""

    return {
        "annotation_hint": required_group_default(
            _PROMPT_DEFAULTS,
            f"annotation_hint_{str(prompt_query_key)}",
            context="dominoes prompt defaults",
        ),
        "answer_hint": required_group_default(
            _PROMPT_DEFAULTS,
            f"answer_hint_{str(prompt_query_key)}",
            context="dominoes prompt defaults",
        ),
        "json_output_contract": 'Return JSON with exactly two keys: "annotation" and "answer".',
        "json_output_contract_answer_only": 'Return JSON with exactly one key: "answer".',
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
    }


def domino_object_description(*, has_chain: bool, has_reference: bool, has_candidates: bool, scene_variant: str) -> str:
    """Return prompt object text for the sampled domino layout."""

    if bool(has_chain) and not bool(has_candidates):
        key = "object_description_chain_only"
    elif bool(has_chain):
        key = f"object_description_chain_{str(scene_variant)}"
    elif bool(has_reference):
        key = f"object_description_tableau_reference_{str(scene_variant)}"
    else:
        key = f"object_description_tableau_{str(scene_variant)}"
    return str(
        required_group_default(
            _PROMPT_DEFAULTS,
            key,
            context="dominoes prompt object-description defaults",
        )
    )


def build_domino_prompt_artifacts(
    *,
    domain: str,
    prompt_query_key: str,
    dynamic_slots: Mapping[str, Any],
    instance_seed: int,
) -> tuple[Dict[str, Any], Any]:
    """Build prompt artifacts from the external dominoes prompt bundle."""

    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        PROMPT_WIRING_KEYS,
        context="dominoes prompt wiring defaults",
    )
    prompt_selection = render_scene_prompt_variants(
        domain=str(domain),
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(prompt_query_key),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots=dict(dynamic_slots),
        instance_seed=int(instance_seed),
    )
    return dict(prompt_defaults), build_prompt_trace_artifacts(prompt_selection)


__all__ = [
    "build_domino_prompt_artifacts",
    "domino_integer_json_examples",
    "domino_option_label_point_pair_json_examples",
    "domino_object_description",
    "domino_output_slots",
]
