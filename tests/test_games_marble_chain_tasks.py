"""Contract tests for games marble-chain tasks."""

from __future__ import annotations

import json
import math
from pathlib import Path

from trace.core.scene_config import get_scene_defaults
from trace.tasks.registry import create_task
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def _assert_shot_labels_are_separated_from_marbles(out) -> None:
    """Check option label markers are not placed on top of chain marbles."""

    entities = out.trace_payload["scene_ir"]["entities"]
    marble_centers = [
        tuple(float(value) for value in entity["center_px"])
        for entity in entities
        if entity.get("entity_type") == "chain_marble"
    ]
    label_centers = [
        tuple(float(value) for value in entity["label_center_px"])
        for entity in entities
        if entity.get("entity_type") == "shot_direction_arrow"
    ]
    assert label_centers
    assert min(
        math.hypot(label[0] - marble[0], label[1] - marble[1])
        for label in label_centers
        for marble in marble_centers
    ) >= 42.0


def test_games_marble_chain_defaults_expose_axes_and_prompt_bundle() -> None:
    cfg = get_scene_defaults("games", "marble_chain")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_games__marble_chain__max_pop_direction_label",
    )

    assert set(generation["scene_variant_weights"].keys()) == {"semicircle_track", "spiral_track", "double_arc_track"}
    assert set(generation["style_variant_weights"].keys()) == {
        "classic_track",
        "arcade_track",
        "neon_track",
        "chalk_track",
        "copper_track",
    }
    assert list(generation["option_count_support"]) == [4, 5, 6]
    assert list(generation["chain_length_support"]) == list(range(18, 29))
    assert list(generation["color_count_support"]) == [4, 5, 6]
    assert int(rendering["canvas_width"]) == 900
    assert int(rendering["canvas_height"]) == 760
    assert float(rendering["unit_size_scale_max"]) / float(rendering["unit_size_scale_min"]) >= 2.0
    assert str(prompt["bundle_id"]) == "games_marble_chain_v1"


def test_games_marble_chain_prompt_bundle_has_three_queries() -> None:
    bundle = json.loads(Path("prompts/games/marble_chain/games_marble_chain_v1.json").read_text(encoding="utf-8"))
    assert str(bundle["schema_version"]) == "v1"
    assert set(bundle["templates"]["query"].keys()) == {
        "max_pop_direction_label",
        "target_pop_direction_label",
        "pop_count_after_marked_shot",
    }
    assert "cascade" in str(bundle["code_prompt_defaults"]["marble_chain_rule_text"])
    assert "target_pop_count" in bundle["required_slots_by_key"]["query:target_pop_direction_label"]


def test_games_marble_chain_max_pop_direction_has_unique_answer() -> None:
    out = create_task("task_games__marble_chain__max_pop_direction_label").generate(
        91231,
        params={"option_count": 6},
        max_attempts=300,
    )
    execution = out.trace_payload["execution_trace"]
    options = execution["shot_options"]
    max_pop = max(int(option["pop_count"]) for option in options)
    answers = [str(option["label"]) for option in options if int(option["pop_count"]) == int(max_pop)]

    assert out.answer_gt.type == "option_letter"
    assert answers == [str(out.answer_gt.value)]
    assert out.scene_id == "marble_chain"
    assert out.query_id == "single"
    assert out.trace_payload["query_spec"]["params"]["prompt_query_key"] == "max_pop_direction_label"
    assert out.annotation_gt.type == "point"
    assert out.trace_payload["projected_annotation"]["point"] == out.annotation_gt.value
    for spec in out.trace_payload["scene_ir"]["entities"]:
        if spec.get("entity_type") == "shot_direction_arrow":
            assert "label_center_px" in spec
    _assert_shot_labels_are_separated_from_marbles(out)


def test_games_marble_chain_target_pop_direction_has_unique_answer() -> None:
    out = create_task("task_games__marble_chain__target_pop_direction_label").generate(
        91241,
        params={"target_pop_count": 3, "option_count": 4},
        max_attempts=300,
    )
    execution = out.trace_payload["execution_trace"]
    options = execution["shot_options"]
    answers = [str(option["label"]) for option in options if int(option["pop_count"]) == 3]

    assert out.answer_gt.type == "option_letter"
    assert answers == [str(out.answer_gt.value)]
    assert execution["target_pop_count"] == 3
    assert out.query_id == "single"
    assert out.trace_payload["query_spec"]["params"]["prompt_query_key"] == "target_pop_direction_label"
    assert out.annotation_gt.type == "point"
    assert out.trace_payload["projected_annotation"]["point"] == out.annotation_gt.value
    _assert_shot_labels_are_separated_from_marbles(out)


def test_games_marble_chain_pop_count_matches_marked_outcome() -> None:
    out = create_task("task_games__marble_chain__shot_effect_value").generate(
        91251,
        params={"query_id": "single", "target_answer": 4},
        max_attempts=300,
    )
    marked = out.trace_payload["execution_trace"]["marked_outcome"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 4
    assert int(marked["pop_count"]) == 4
    assert out.query_id == "single"
    assert out.trace_payload["query_spec"]["params"]["prompt_query_key"] == "pop_count_after_marked_shot"
    assert out.annotation_gt.type == "point_set"
    assert len(out.annotation_gt.value) == 4
    assert out.trace_payload["projected_annotation"]["point_set"] == out.annotation_gt.value
