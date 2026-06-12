"""Contract tests for games racing-track tasks."""

from __future__ import annotations

import json
from pathlib import Path

import trace.tasks  # noqa: F401
from trace.core.scene_config import get_scene_defaults
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.registry import create_task
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


TASK_ID = "task_games__racing_track__finish_distance_extremum_label"
AHEAD_TASK_ID = "task_games__racing_track__ahead_object_count"


def test_games_racing_track_defaults_expose_axes_and_prompt_bundle() -> None:
    cfg = get_scene_defaults("games", "racing_track")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id=TASK_ID,
    )

    assert set(generation["scene_variant_weights"].keys()) == {"oval_loop", "rounded_loop", "kidney_loop"}
    assert set(generation["query_id_weights"].keys()) == {
        "closest_to_finish_label",
        "farthest_from_finish_label",
        "car_ahead_count",
    }
    assert set(generation["style_variant_weights"].keys()) == {
        "asphalt_day",
        "rally_sand",
        "neon_night",
        "blueprint_track",
        "paper_race",
    }
    assert list(generation["car_count_support"]) == [4, 5, 6, 7]
    assert list(generation["ahead_car_count_support"]) == [5, 6, 7]
    assert list(generation["target_answer_support"]) == [0, 1, 2, 3, 4]
    assert int(rendering["track_width_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_racing_track_v0"
    assert "track in the arrow direction" in str(prompt["distance_rule_text"])


def test_games_racing_track_prompt_bundle_has_queries() -> None:
    bundle = json.loads(Path("prompts/games/racing_track/games_racing_track_v0.json").read_text(encoding="utf-8"))
    assert set(bundle["query_templates"].keys()) == {
        "closest_to_finish_label",
        "farthest_from_finish_label",
        "car_ahead_count",
    }
    assert bundle["required_slots_by_key"]["query:closest_to_finish_label"] == ["distance_rule_text"]
    assert bundle["required_slots_by_key"]["query:farthest_from_finish_label"] == ["distance_rule_text"]
    assert bundle["required_slots_by_key"]["query:car_ahead_count"] == ["ahead_rule_text"]


def test_games_racing_track_closest_answer_matches_remaining_distance_trace() -> None:
    out = create_task(TASK_ID).generate(
        81901,
        params={"query_id": "closest_to_finish_label", "car_count": 6},
        max_attempts=300,
    )
    cars = out.trace_payload["execution_trace"]["cars"]
    expected = min(cars, key=lambda car: float(car["remaining_distance"]))

    assert out.scene_id == "racing_track"
    assert out.query_id == "closest_to_finish_label"
    assert out.answer_gt.type == "string"
    assert out.answer_gt.value == expected["label"]
    assert out.trace_payload["execution_trace"]["answer_entity_id"] == expected["car_id"]
    assert out.annotation_gt.type == "point_set"
    assert len(out.annotation_gt.value) == 1
    assert out.trace_payload["projected_annotation"]["point_set"] == out.annotation_gt.value


def test_games_racing_track_farthest_answer_matches_remaining_distance_trace() -> None:
    out = create_task(TASK_ID).generate(
        81902,
        params={"query_id": "farthest_from_finish_label", "car_count": 7},
        max_attempts=300,
    )
    cars = out.trace_payload["execution_trace"]["cars"]
    expected = max(cars, key=lambda car: float(car["remaining_distance"]))

    assert out.scene_id == "racing_track"
    assert out.query_id == "farthest_from_finish_label"
    assert out.answer_gt.type == "string"
    assert out.answer_gt.value == expected["label"]
    assert out.trace_payload["execution_trace"]["answer_entity_id"] == expected["car_id"]
    assert out.annotation_gt.type == "point_set"
    assert len(out.annotation_gt.value) == 1
    assert out.trace_payload["projected_annotation"]["point_set"] == out.annotation_gt.value


def test_games_racing_track_taxonomy_mapping() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert taxonomy.domain == "games"
    assert taxonomy.scene_id == "racing_track"
    assert taxonomy.source_domain == "games"
    assert taxonomy.source_scene_id == "racing_track"

    ahead_taxonomy = resolve_task_taxonomy(AHEAD_TASK_ID)
    assert ahead_taxonomy.domain == "games"
    assert ahead_taxonomy.scene_id == "racing_track"
    assert ahead_taxonomy.source_domain == "games"
    assert ahead_taxonomy.source_scene_id == "racing_track"


def _ahead_expected_ids(out) -> list[str]:
    execution = out.trace_payload["execution_trace"]
    reference_id = str(execution["reference_car_id"])
    reference = next(car for car in execution["cars"] if str(car["car_id"]) == reference_id)
    reference_progress = float(reference["progress"])
    query_id = str(execution["query_id"])
    if query_id == "car_ahead_count":
        return [
            str(car["car_id"])
            for car in sorted(execution["cars"], key=lambda item: float(item["progress"]))
            if str(car["car_id"]) != reference_id and float(car["progress"]) > reference_progress
        ]
    raise AssertionError(f"unexpected racing-track ahead query: {query_id}")


def test_games_racing_track_ahead_car_answer_matches_trace() -> None:
    out = create_task(AHEAD_TASK_ID).generate(
        81911,
        params={"query_id": "car_ahead_count", "target_answer": 3},
        max_attempts=500,
    )
    expected_ids = _ahead_expected_ids(out)

    assert out.scene_id == "racing_track"
    assert out.query_id == "car_ahead_count"
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 3
    assert len(out.annotation_gt.value) == 3
    assert out.trace_payload["execution_trace"]["annotation_entity_ids"] == expected_ids
    assert out.trace_payload["render_map"]["marked_car_id"] == out.trace_payload["execution_trace"]["reference_car_id"]
    assert "zones" not in out.trace_payload["execution_trace"]
    assert not any(str(entity["type"]).endswith("_zone") for entity in out.trace_payload["scene_ir"]["entities"])


def test_games_racing_track_ahead_zero_answer_uses_empty_annotation() -> None:
    out = create_task(AHEAD_TASK_ID).generate(
        81912,
        params={"query_id": "car_ahead_count", "target_answer": 0},
        max_attempts=500,
    )
    expected_ids = _ahead_expected_ids(out)

    assert out.query_id == "car_ahead_count"
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 0
    assert expected_ids == []
    assert out.annotation_gt.type == "point_set"
    assert out.annotation_gt.value == []
    assert out.trace_payload["execution_trace"]["annotation_entity_ids"] == expected_ids
    assert out.trace_payload["projected_annotation"]["point_set"] == []
