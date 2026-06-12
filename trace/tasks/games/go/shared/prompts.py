"""Prompt assembly helpers for Go scene tasks."""

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


def build_go_prompt_json_examples(*, stone_group_query: bool) -> Tuple[str, str]:
    """Return answer+annotation and answer-only JSON examples for Go count tasks."""

    if bool(stone_group_query):
        answer_and_annotation = {"annotation": [[280, 220], [426, 426], [573, 646]], "answer": 3}
        answer_only = {"answer": 3}
    else:
        answer_and_annotation = {"annotation": [[343, 315], [417, 389]], "answer": 4}
        answer_only = {"answer": 4}
    return (
        json.dumps(answer_and_annotation, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def build_go_prompt_artifacts(
    *,
    domain: str,
    scene_variant: str,
    prompt_query_key: str,
    player_color: str,
    stone_group_query: bool,
    instance_seed: int,
) -> tuple[Dict[str, Any], Any]:
    """Build prompt artifacts for one objective-owned Go task file."""

    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description_open_board",
            "object_description_crowded_board",
            "object_description_stone_group_open_board",
            "object_description_stone_group_crowded_board",
            "group_rule_text",
            "liberty_rule_text",
            "adjacent_enemy_rule_text",
            "shared_liberty_rule_text",
            "marked_group_rule_text",
            "answer_hint_marked_group_liberty_count",
            "annotation_hint_marked_group_liberty_count",
            "answer_hint_marked_group_adjacent_enemy_count",
            "annotation_hint_marked_group_adjacent_enemy_count",
            "answer_hint_marked_group_shared_liberty_count",
            "annotation_hint_marked_group_shared_liberty_count",
            "answer_hint_stone_group_count",
            "annotation_hint_stone_group_count",
        ),
        context="go prompt wiring defaults",
    )
    hint_key = "stone_group_count" if bool(stone_group_query) else str(prompt_query_key)
    object_description_key = (
        f"object_description_stone_group_{str(scene_variant)}"
        if bool(stone_group_query)
        else f"object_description_{str(scene_variant)}"
    )
    json_example, json_example_answer_only = build_go_prompt_json_examples(
        stone_group_query=bool(stone_group_query)
    )
    prompt_slots = {
        "object_description": str(prompt_defaults[object_description_key]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults[f"answer_hint_{hint_key}"]).format(player_color=str(player_color)),
        "annotation_hint": str(prompt_defaults[f"annotation_hint_{hint_key}"]).format(player_color=str(player_color)),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
        "player_color": str(player_color),
        "group_rule_text": str(prompt_defaults["group_rule_text"]),
        "liberty_rule_text": str(prompt_defaults["liberty_rule_text"]),
        "adjacent_enemy_rule_text": str(prompt_defaults["adjacent_enemy_rule_text"]),
        "shared_liberty_rule_text": str(prompt_defaults["shared_liberty_rule_text"]),
        "marked_group_rule_text": str(prompt_defaults["marked_group_rule_text"]).format(player_color=str(player_color)),
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


__all__ = ["build_go_prompt_artifacts", "build_go_prompt_json_examples"]
