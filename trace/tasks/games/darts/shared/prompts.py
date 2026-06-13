"""Prompt assembly helpers for darts scene tasks."""

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


def darts_integer_count_json_examples() -> tuple[str, str]:
    """Return generic JSON examples for integer-count darts tasks."""

    return (
        json.dumps({"annotation": [[411, 219], [525, 364]], "answer": 2}, separators=(",", ":")),
        json.dumps({"answer": 2}, separators=(",", ":")),
    )


def darts_label_json_examples() -> tuple[str, str]:
    """Return generic JSON examples for label-answer darts tasks."""

    return (
        json.dumps({"annotation": [[411, 219]], "answer": "C"}, separators=(",", ":")),
        json.dumps({"answer": "C"}, separators=(",", ":")),
    )


def darts_output_slots(
    *,
    prompt_query_key: str,
    json_example: str,
    json_example_answer_only: str,
) -> Dict[str, Any]:
    """Return answer and annotation prompt slots for one darts query key."""

    return {
        "annotation_hint": required_group_default(
            _PROMPT_DEFAULTS,
            f"annotation_hint_{str(prompt_query_key)}",
            context="darts prompt defaults",
        ),
        "answer_hint": required_group_default(
            _PROMPT_DEFAULTS,
            f"answer_hint_{str(prompt_query_key)}",
            context="darts prompt defaults",
        ),
        "json_output_contract": 'Return JSON with exactly two keys: "annotation" and "answer".',
        "json_output_contract_answer_only": 'Return JSON with exactly one key: "answer".',
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
    }


def build_darts_prompt_artifacts(
    *,
    domain: str,
    prompt_query_key: str,
    dynamic_slots: Mapping[str, Any],
    instance_seed: int,
) -> tuple[Dict[str, Any], Any]:
    """Build prompt artifacts from the external darts prompt bundle."""

    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        PROMPT_WIRING_KEYS,
        context="darts prompt wiring defaults",
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
    "build_darts_prompt_artifacts",
    "darts_integer_count_json_examples",
    "darts_label_json_examples",
    "darts_output_slots",
    "darts_target_ring_prompt_text",
]
