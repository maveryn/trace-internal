"""Prompt assembly helpers for slot-machine games tasks."""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping

from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults, required_group_default, required_group_defaults
from trace.tasks.shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants

from .defaults import SCENE_ID


_GEN_DEFAULTS_UNUSED, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
)
_PROMPT_WIRING_KEYS = (
    "bundle_id",
    "scene_key",
    "task_key",
    "json_output_contract",
    "json_output_contract_answer_only",
    "object_description",
)


def slot_integer_segment_set_json_examples(answer_value: int = 2) -> tuple[str, str]:
    """Return valid JSON examples for count tasks with segment-set annotation."""

    return (
        json.dumps(
            {
                "annotation": [[[250, 250], [510, 250]], [[250, 470], [510, 250]]],
                "answer": int(answer_value),
            },
            separators=(",", ":"),
        ),
        json.dumps({"answer": int(answer_value)}, separators=(",", ":")),
    )


def slot_label_bbox_json_examples(answer_label: str = "B") -> tuple[str, str]:
    """Return valid JSON examples for option-label tasks with bbox annotation."""

    return (
        json.dumps(
            {
                "annotation": [620, 170, 746, 440],
                "answer": str(answer_label),
            },
            separators=(",", ":"),
        ),
        json.dumps({"answer": str(answer_label)}, separators=(",", ":")),
    )


def slot_output_slots(
    *,
    prompt_query_key: str,
    json_example: str,
    json_example_answer_only: str,
    extra_slots: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return prompt slots for one slot-machine query key."""

    slots = {
        "object_description": required_group_default(
            _PROMPT_DEFAULTS,
            "object_description",
            context="slot-machine prompt defaults",
        ),
        "annotation_hint": required_group_default(
            _PROMPT_DEFAULTS,
            f"annotation_hint_{prompt_query_key}",
            context="slot-machine prompt defaults",
        ),
        "answer_hint": required_group_default(
            _PROMPT_DEFAULTS,
            f"answer_hint_{prompt_query_key}",
            context="slot-machine prompt defaults",
        ),
        "json_output_contract": required_group_default(
            _PROMPT_DEFAULTS,
            "json_output_contract",
            context="slot-machine prompt defaults",
        ),
        "json_output_contract_answer_only": required_group_default(
            _PROMPT_DEFAULTS,
            "json_output_contract_answer_only",
            context="slot-machine prompt defaults",
        ),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
    }
    slots.update(dict(extra_slots or {}))
    return slots


def build_slot_machine_prompt_artifacts(
    *,
    domain: str,
    prompt_query_key: str,
    dynamic_slots: Mapping[str, Any],
    instance_seed: int,
) -> tuple[Dict[str, Any], Any]:
    """Build prompt artifacts from the external slot-machine prompt bundle."""

    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        _PROMPT_WIRING_KEYS,
        context="slot-machine prompt wiring defaults",
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
    "build_slot_machine_prompt_artifacts",
    "slot_integer_segment_set_json_examples",
    "slot_label_bbox_json_examples",
    "slot_output_slots",
]
