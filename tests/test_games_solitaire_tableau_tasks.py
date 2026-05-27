"""Contract tests for games solitaire-tableau tasks."""

from __future__ import annotations

import json
from pathlib import Path

import trace.tasks  # noqa: F401
from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.registry import create_task
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def _card_color(suit_name: str) -> str:
    return "red" if str(suit_name) in {"hearts", "diamonds"} else "black"


def _is_legal_tableau(source: dict, target: dict) -> bool:
    return int(target["rank_value"]) == int(source["rank_value"]) + 1 and _card_color(str(target["suit_name"])) != _card_color(str(source["suit_name"]))


def _is_legal_foundation(source: dict, foundation: dict) -> bool:
    return str(source["suit_name"]) == str(foundation["suit_name"]) and int(source["rank_value"]) == int(foundation["top_rank_value"]) + 1


def test_games_solitaire_defaults_expose_scene_axes_and_prompt_bundle() -> None:
    cfg = get_task_group_defaults("games", "solitaire")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__solitaire__move_legality_label",
    )

    assert set(generation["scene_variant_weights"].keys()) == {"klondike_tableau", "freecell_tableau"}
    assert list(generation["move_option_count_support"]) == [4, 5]
    assert list(generation["foundation_ready_target_answer_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["tableau_sequence_target_answer_support"]) == [0, 1, 2, 3, 4]
    assert int(rendering["canvas_width"]) == 1060
    assert int(rendering["card_width_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_solitaire_v0"
    assert "foundation" in str(prompt["foundation_rule_text"])


def test_games_solitaire_prompt_bundle_has_three_queries() -> None:
    bundle = json.loads(Path("prompts/games/solitaire/games_solitaire_v0.json").read_text(encoding="utf-8"))
    assert set(bundle["query_templates"].keys()) == {
        "move_legality_label",
        "foundation_ready_count",
        "tableau_sequence_count",
    }
    assert bundle["required_slots_by_key"]["query:move_legality_label"] == [
        "tableau_rule_text",
        "foundation_rule_text",
    ]


def test_games_solitaire_move_legality_has_one_legal_option() -> None:
    out = create_task("task_games__solitaire__move_legality_label").generate(81331, params={"option_count": 5}, max_attempts=200)
    execution = out.trace_payload["execution_trace"]
    cards = {str(spec["card_id"]): dict(spec) for spec in execution["card_specs"]}
    foundations = {str(spec["foundation_id"]): dict(spec) for spec in execution["foundation_specs"]}

    legal_labels = []
    for option in execution["move_options"]:
        source = cards[str(option["source_card_id"])]
        target_id = str(option["target_id"])
        if target_id in cards:
            legal = _is_legal_tableau(source, cards[target_id])
        else:
            legal = _is_legal_foundation(source, foundations[target_id])
        if legal:
            legal_labels.append(str(option["label"]))

    assert out.answer_gt.type == "string"
    assert legal_labels == [str(out.answer_gt.value)]
    assert execution["answer_option_label"] == out.answer_gt.value
    assert len(out.evidence_gt.value) == 3
    assert set(execution["evidence_entity_ids"]) == {
        f"move_option_{str(out.answer_gt.value).lower()}",
        execution["legal_source_id"],
        execution["legal_target_id"],
    }
    assert out.query_id == "default"
    assert out.scene_id == "solitaire"
    assert out.query_id == "move_legality_label"


def test_games_solitaire_foundation_ready_count_matches_trace() -> None:
    out = create_task("task_games__solitaire__foundation_ready_count").generate(
        81341,
        params={"target_answer": 3},
        max_attempts=200,
    )
    execution = out.trace_payload["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 3
    assert len(execution["ready_card_ids"]) == 3
    assert int(execution["target_answer"]) == 3
    assert out.query_id == "foundation_ready_count"
    assert len(out.evidence_gt.value) >= 4


def test_games_solitaire_tableau_sequence_count_matches_trace() -> None:
    out = create_task("task_games__solitaire__tableau_sequence_count").generate(
        81351,
        params={"target_answer": 4},
        max_attempts=200,
    )
    execution = out.trace_payload["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 4
    assert int(execution["valid_sequence_pair_count"]) == 4
    assert len(execution["valid_sequence_pairs"]) == 4
    assert out.query_id == "tableau_sequence_count"
    assert out.trace_payload["projected_evidence"]["bbox_set"] == out.evidence_gt.value
