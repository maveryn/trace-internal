"""Contract tests for games lane-runner tasks."""

from __future__ import annotations

import json
from pathlib import Path

import trace.tasks  # noqa: F401
from trace.core.scene_config import get_scene_defaults
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.games.lane_runner.shared.common import LaneRunnerCoin, path_coin_collection
from trace.tasks.games.lane_runner.shared.common import LaneRunnerHazard, path_hits_hazard, path_option_entity_id
from trace.tasks.registry import create_task, list_default_task_ids
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


PATH_COIN_TASK_ID = "task_games__lane_runner__path_coin_count"
SAFE_PATH_TASK_ID = "task_games__lane_runner__safe_path_label"


def test_games_lane_runner_defaults_expose_axes_and_prompt_bundle() -> None:
    cfg = get_scene_defaults("games", "lane_runner")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="games_lane_runner_path_coin_base",
    )

    assert set(generation["scene_variant_weights"].keys()) == {"two_lane_track"}
    assert generation["query_id_weights"]["path_coin_count"] == 1.0
    assert generation["query_id_weights"]["safe_path_label"] == 0.0
    assert set(generation["style_variant_weights"].keys()) == {
        "arcade_lane",
        "city_road",
        "forest_path",
        "neon_track",
        "paper_course",
    }
    assert list(generation["row_count_support"]) == [5, 6, 7, 8]
    assert list(generation["start_lane_support"]) == [0, 1]
    assert list(generation["target_answer_support"]) == [1, 2, 3, 4, 5, 6]
    assert bool(rendering["dynamic_canvas_size_enabled"]) is True
    assert float(rendering["unit_size_scale_min"]) == 0.5
    assert float(rendering["unit_size_scale_max"]) == 1.0
    assert bool(rendering["layout_jitter_enabled"]) is True
    assert str(prompt["bundle_id"]) == "games_lane_runner_v0"
    assert "shown path" in str(prompt["object_description_two_lane_track_path_coin"])
    assert "Follow the shown path" in str(prompt["lane_runner_path_rule_text"])

    safe_generation, _safe_rendering, safe_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="games_lane_runner_safe_path_base",
    )
    assert safe_generation["query_id_weights"]["path_coin_count"] == 0.0
    assert safe_generation["query_id_weights"]["safe_path_label"] == 1.0
    assert list(safe_generation["option_count_support"]) == [4, 6]
    assert list(safe_generation["answer_option_index_support"]) == [0, 1, 2, 3, 4, 5]
    assert "hazard cell" in str(safe_prompt["safe_path_rule_text"])


def test_games_lane_runner_prompt_bundle_has_active_queries() -> None:
    bundle = json.loads(Path("prompts/games/lane_runner/games_lane_runner_v0.json").read_text(encoding="utf-8"))

    assert set(bundle["query_templates"].keys()) == {"path_coin_count", "safe_path_label"}
    assert bundle["required_slots_by_key"]["query:path_coin_count"] == ["lane_runner_path_rule_text"]
    assert bundle["required_slots_by_key"]["query:safe_path_label"] == ["safe_path_rule_text"]
    assert len(bundle["query_templates"]["path_coin_count"]) == 5
    assert len(bundle["query_templates"]["safe_path_label"]) == 5


def test_games_lane_runner_taxonomy_and_default_registry() -> None:
    default_ids = set(list_default_task_ids())

    path_taxonomy = resolve_task_taxonomy(PATH_COIN_TASK_ID)
    assert path_taxonomy.domain == "games"
    assert path_taxonomy.scene_id == "lane_runner"
    assert path_taxonomy.source_domain == "games"
    assert path_taxonomy.source_scene_id == "lane_runner"
    assert PATH_COIN_TASK_ID in default_ids

    safe_taxonomy = resolve_task_taxonomy(SAFE_PATH_TASK_ID)
    assert safe_taxonomy.domain == "games"
    assert safe_taxonomy.scene_id == "lane_runner"
    assert safe_taxonomy.source_domain == "games"
    assert safe_taxonomy.source_scene_id == "lane_runner"
    assert SAFE_PATH_TASK_ID in default_ids


def test_games_lane_runner_path_coin_answer_matches_shown_path() -> None:
    out = create_task(PATH_COIN_TASK_ID).generate(
        92342,
        params={"row_count": 6, "target_answer": 3, "start_lane": 1},
        max_attempts=200,
    )
    execution = out.trace_payload["execution_trace"]
    coins = tuple(
        LaneRunnerCoin(
            coin_id=str(coin["coin_id"]),
            row=int(coin["row"]),
            lane=int(coin["lane"]),
        )
        for coin in execution["coins"]
    )
    answer, annotation_ids = path_coin_collection(
        coins=coins,
        shown_path_lanes=execution["shown_path_lanes"],
        row_count=int(execution["row_count"]),
        lane_count=int(execution["lane_count"]),
        start_lane=int(execution["start_lane"]),
    )
    coin_cells = {(int(coin.row), int(coin.lane)) for coin in coins}
    has_parallel_row = any(
        (row, int(lane)) in coin_cells and (row, 1 - int(lane)) in coin_cells
        for row, lane in enumerate(execution["shown_path_lanes"])
    )

    assert out.scene_id == "lane_runner"
    assert out.query_id == "path_coin_count"
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(answer) == 3
    assert len(coins) > int(answer)
    assert has_parallel_row is True
    assert execution["annotation_entity_ids"] == list(annotation_ids)
    assert execution["construction_mode"] == "sample_shown_path_with_parallel_coin_distractors"
    assert out.annotation_gt.type == "point_set"
    assert len(out.annotation_gt.value) == int(answer)
    assert out.trace_payload["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert out.trace_payload["render_map"]["shown_path_px"]["lanes_by_row"] == execution["shown_path_lanes"]
    for entity_id, point in zip(annotation_ids, out.annotation_gt.value):
        assert out.trace_payload["render_map"]["entity_points_px"][entity_id] == point


def test_games_lane_runner_safe_path_answer_matches_trace() -> None:
    out = create_task(SAFE_PATH_TASK_ID).generate(
        92741,
        params={"row_count": 6, "option_count": 6, "answer_option_index": 2, "start_lane": 0},
        max_attempts=200,
    )
    execution = out.trace_payload["execution_trace"]
    hazards = tuple(
        LaneRunnerHazard(
            hazard_id=str(hazard["hazard_id"]),
            row=int(hazard["row"]),
            lane=int(hazard["lane"]),
        )
        for hazard in execution["hazards"]
    )
    safe_labels = [
        str(option["label"])
        for option in execution["path_options"]
        if not path_hits_hazard(lanes_by_row=option["lanes_by_row"], hazards=hazards)
    ]
    answer = str(execution["answer"])
    answer_entity_id = path_option_entity_id(answer)

    assert out.scene_id == "lane_runner"
    assert out.query_id == "safe_path_label"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "C"
    assert safe_labels == [answer] == ["C"]
    assert execution["answer_entity_id"] == answer_entity_id
    assert execution["annotation_entity_ids"] == [answer_entity_id]
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == 1
    assert out.trace_payload["projected_annotation"]["type"] == "bbox_set"
    assert out.trace_payload["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert out.trace_payload["projected_annotation"]["pixel_bbox_set"] == out.annotation_gt.value
    assert out.trace_payload["render_map"]["path_options_px"][answer]["card_bbox_px"] == out.annotation_gt.value[0]
    assert out.trace_payload["render_map"]["show_board"] is False
    assert out.trace_payload["render_map"]["cell_bboxes_px"] == {}
    assert out.trace_payload["render_map"]["hazard_bboxes_px"] == {}
