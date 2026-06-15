"""Contract tests for games match-3 tasks."""

from __future__ import annotations

import json
from pathlib import Path

import trace.tasks  # noqa: F401
from trace.core.scene_config import get_scene_defaults
from trace.tasks.registry import create_task
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults
from trace.tasks.shared.named_colors import named_color


def test_games_match3_defaults_expose_axes_and_prompt_bundle() -> None:
    cfg = get_scene_defaults("games", "match3")
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
    assert list(generation["option_count_support"]) == [4]
    assert list(generation["gem_count_answer_support"]) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert int(rendering["canvas_width"]) == 760
    assert int(rendering["canvas_height"]) == 720
    assert float(rendering["unit_size_scale_max"]) / float(rendering["unit_size_scale_min"]) >= 2.0
    assert str(prompt["bundle_id"]) == "games_match3_v1"


def test_games_match3_prompt_bundle_has_queries() -> None:
    bundle = json.loads(Path("prompts/games/match3/games_match3_v1.json").read_text(encoding="utf-8"))
    assert bundle["schema_version"] == "v1"
    assert set(bundle["templates"]["query"].keys()) == {
        "column_color_gem_count",
        "grid_color_gem_count",
        "max_clear_swap_label",
        "row_color_gem_count",
    }
    assert "target_color_label" in bundle["required_slots_by_key"]["query:grid_color_gem_count"]
    assert "cascades" in str(bundle["code_prompt_defaults"]["match3_rule_text"])


def test_games_match3_best_swap_uses_easier_task_override() -> None:
    cfg = get_scene_defaults("games", "match3")
    generation, rendering, _prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__match3__max_clear_swap_label",
    )

    assert list(generation["row_count_support"]) == [5]
    assert list(generation["col_count_support"]) == [5]
    assert list(generation["gem_type_count_support"]) == [5]
    assert list(generation["option_count_support"]) == [4]
    assert int(rendering["arrow_width_px"]) == 9


def test_games_match3_max_clear_label_has_unique_answer() -> None:
    out = create_task("task_games__match3__max_clear_swap_label").generate(
        71231,
        params={"query_id": "single", "option_count": 6},
        max_attempts=300,
    )
    options = out.trace_payload["execution_trace"]["swap_options"]
    max_clear = max(int(option["clear_count"]) for option in options)
    answers = [str(option["label"]) for option in options if int(option["clear_count"]) == int(max_clear)]

    assert out.answer_gt.type == "option_letter"
    assert answers == [str(out.answer_gt.value)]
    assert out.scene_id == "match3"
    assert out.query_id == "single"
    assert out.trace_payload["query_spec"]["params"]["prompt_query_key"] == "max_clear_swap_label"
    assert len(options) == 4
    assert out.trace_payload["query_spec"]["params"]["option_count"] == 4
    assert out.annotation_gt.type == "point"
    assert out.trace_payload["projected_annotation"]["point"] == out.annotation_gt.value


def test_games_match3_gem_count_uses_canonical_named_colors() -> None:
    out = create_task("task_games__match3__gem_count").generate(
        71251,
        params={"query_id": "grid_color_gem_count", "target_answer": 4},
        max_attempts=500,
    )
    trace = out.trace_payload
    target_color = str(trace["query_spec"]["params"]["target_color_name"])
    target_rgb = tuple(int(value) for value in trace["query_spec"]["params"]["target_color_rgb"])

    assert target_rgb == named_color(target_color)
    assert "[" in str(out.prompt) and "#" in str(out.prompt)
    assert out.answer_gt.type == "integer"
    assert out.scene_id == "match3"
    assert out.query_id == "grid_color_gem_count"
    assert out.annotation_gt.type == "point_set"

    matching = [
        entity
        for entity in trace["scene_ir"]["entities"]
        if entity.get("entity_type") == "match3_gem" and entity.get("color_name") == target_color
    ]
    assert int(out.answer_gt.value) == len(matching)
    assert len(out.annotation_gt.value) == len(matching)
    for entity in matching:
        assert tuple(int(value) for value in entity["color_rgb"]) == named_color(str(entity["color_name"]))


def test_games_match3_row_and_column_gem_count_scopes() -> None:
    for query_id, scope_key in (
        ("row_color_gem_count", "row_index"),
        ("column_color_gem_count", "col_index"),
    ):
        out = create_task("task_games__match3__gem_count").generate(
            71300 + len(query_id),
            params={"query_id": query_id, "target_answer": 2},
            max_attempts=500,
        )
        trace = out.trace_payload
        params = trace["query_spec"]["params"]
        target_color = str(params["target_color_name"])
        scope_index = int(params[scope_key])
        matching = []
        for entity in trace["scene_ir"]["entities"]:
            if entity.get("entity_type") != "match3_gem" or entity.get("color_name") != target_color:
                continue
            if query_id == "row_color_gem_count" and int(entity["row"]) != scope_index:
                continue
            if query_id == "column_color_gem_count" and int(entity["col"]) != scope_index:
                continue
            matching.append(entity)
        assert int(out.answer_gt.value) == len(matching)
        assert len(out.annotation_gt.value) == len(matching)
