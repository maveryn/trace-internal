"""Contract tests for games match-3 tasks."""

from __future__ import annotations

import json
from pathlib import Path

import trace.tasks  # noqa: F401
from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.registry import create_task
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_match3_defaults_expose_axes_and_prompt_bundle() -> None:
    cfg = get_task_group_defaults("games", "match3")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
    )

    assert set(generation["scene_variant_weights"].keys()) == {"square_board", "wide_board", "tall_board"}
    assert set(generation["style_variant_weights"].keys()) == {
        "faceted_jewels",
        "round_candies",
        "beveled_tiles",
        "diamond_gems",
        "orb_tokens",
    }
    assert set(generation["effect_value_query_id_weights"].keys()) == {
        "cleared_count_after_marked_swap",
        "created_run_count_after_marked_swap",
    }
    assert set(generation["best_swap_query_id_weights"].keys()) == {
        "max_clear_swap_label",
        "target_clear_swap_label",
    }
    assert list(generation["option_count_support"]) == [5, 6, 7, 8]
    assert list(generation["target_clear_count_support"]) == [0, 3, 4, 5, 6]
    assert int(rendering["canvas_width"]) == 760
    assert int(rendering["canvas_height"]) == 720
    assert float(rendering["unit_size_scale_max"]) / float(rendering["unit_size_scale_min"]) >= 2.0
    assert str(prompt["bundle_id"]) == "games_match3_v0"
    assert "cascades" in str(prompt["match3_rule_text"])


def test_games_match3_prompt_bundle_has_queries() -> None:
    bundle = json.loads(Path("prompts/games/match3/games_match3_v0.json").read_text(encoding="utf-8"))
    assert set(bundle["query_templates"].keys()) == {
        "cleared_count_after_marked_swap",
        "created_run_count_after_marked_swap",
        "max_clear_swap_label",
        "target_clear_swap_label",
    }
    assert "target_clear_count" in bundle["required_slots_by_key"]["query:target_clear_swap_label"]


def test_games_match3_swap_effect_uses_easier_task_override() -> None:
    cfg = get_task_group_defaults("games", "match3")
    generation, rendering, _prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__match3__swap_effect_value",
    )

    assert list(generation["row_count_support"]) == [5, 6]
    assert list(generation["col_count_support"]) == [5, 6]
    assert list(generation["target_clear_count_support"]) == [0, 3, 4]
    assert list(generation["target_run_count_support"]) == [0, 1, 2]
    assert int(rendering["arrow_width_px"]) == 9


def test_games_match3_best_swap_uses_easier_task_override() -> None:
    cfg = get_task_group_defaults("games", "match3")
    generation, rendering, _prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__match3__best_swap_label",
    )

    assert list(generation["row_count_support"]) == [5]
    assert list(generation["col_count_support"]) == [5]
    assert list(generation["gem_type_count_support"]) == [5]
    assert list(generation["option_count_support"]) == [5]
    assert list(generation["target_clear_count_support"]) == [0, 3]
    assert int(rendering["arrow_width_px"]) == 9


def test_games_match3_max_clear_label_has_unique_answer() -> None:
    out = create_task("task_games__match3__best_swap_label").generate(
        71231,
        params={"query_id": "max_clear_swap_label", "option_count": 5},
        max_attempts=300,
    )
    options = out.trace_payload["execution_trace"]["swap_options"]
    max_clear = max(int(option["clear_count"]) for option in options)
    answers = [str(option["label"]) for option in options if int(option["clear_count"]) == int(max_clear)]

    assert out.answer_gt.type == "string"
    assert answers == [str(out.answer_gt.value)]
    assert out.scene_id == "match3"
    assert out.query_id == "max_clear_swap_label"
    assert out.evidence_gt.type == "point_set"
    assert len(out.evidence_gt.value) == 1
    assert out.trace_payload["projected_evidence"]["point_set"] == out.evidence_gt.value


def test_games_match3_target_clear_label_has_unique_answer() -> None:
    out = create_task("task_games__match3__best_swap_label").generate(
        71241,
        params={"query_id": "target_clear_swap_label", "target_answer": 3},
        max_attempts=300,
    )
    options = out.trace_payload["execution_trace"]["swap_options"]
    answers = [str(option["label"]) for option in options if int(option["clear_count"]) == 3]

    assert out.answer_gt.type == "string"
    assert answers == [str(out.answer_gt.value)]
    assert out.trace_payload["execution_trace"]["target_clear_count"] == 3
    assert out.query_id == "target_clear_swap_label"
    assert out.evidence_gt.type == "point_set"
    assert len(out.evidence_gt.value) == 1


def test_games_match3_marked_clear_count_matches_trace() -> None:
    out = create_task("task_games__match3__swap_effect_value").generate(
        71251,
        params={"query_id": "cleared_count_after_marked_swap", "target_answer": 4},
        max_attempts=300,
    )
    marked = out.trace_payload["execution_trace"]["marked_outcome"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 4
    assert int(marked["clear_count"]) == 4
    assert out.query_id == "cleared_count_after_marked_swap"
    assert out.evidence_gt.type == "point_set"
    assert len(out.evidence_gt.value) == int(marked["clear_count"])
    assert out.trace_payload["projected_evidence"]["point_set"] == out.evidence_gt.value


def test_games_match3_marked_run_count_matches_trace() -> None:
    out = create_task("task_games__match3__swap_effect_value").generate(
        71261,
        params={"query_id": "created_run_count_after_marked_swap", "target_answer": 2},
        max_attempts=300,
    )
    marked = out.trace_payload["execution_trace"]["marked_outcome"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 2
    assert int(marked["run_count"]) == 2
    assert out.query_id == "created_run_count_after_marked_swap"
    assert out.evidence_gt.type == "point_set"
    assert len(out.evidence_gt.value) == int(marked["run_count"])
