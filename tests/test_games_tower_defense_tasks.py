"""Contract tests for games tower-defense tasks."""

from __future__ import annotations

import json
import math
from pathlib import Path

import trace.tasks  # noqa: F401
from trace.core.task_group_config import get_task_group_defaults
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.registry import create_task
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


TOWER_COVERAGE_TASK_ID = "task_games__tower_defense__tower_coverage_count"
COVERED_PATH_TASK_ID = "task_games__tower_defense__covered_path_segment_count"


def _distance(point_a: list[float], point_b: list[float]) -> float:
    return math.hypot(float(point_a[0]) - float(point_b[0]), float(point_a[1]) - float(point_b[1]))


def test_games_tower_defense_defaults_expose_axes_and_prompt_bundle() -> None:
    cfg = get_task_group_defaults("games", "tower_defense")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id=TOWER_COVERAGE_TASK_ID,
    )

    assert set(generation["scene_variant_weights"].keys()) == {"winding_path", "switchback_path"}
    assert set(generation["query_id_weights"].keys()) == {
        "marked_enemy_covered_by_tower_count",
        "covered_path_segment_count",
    }
    assert set(generation["style_variant_weights"].keys()) == {
        "grass_field",
        "desert_path",
        "blueprint_grid",
        "night_ops",
        "paper_map",
    }
    assert list(generation["target_answer_support"]) == [0, 1, 2, 3, 4, 5]
    assert list(generation["covered_path_target_answer_support"]) == [3, 4, 5, 6, 7, 8, 9, 10]
    assert list(generation["tower_count_support"]) == [5, 6, 7, 8]
    assert list(generation["covered_path_tower_count_support"]) == [5, 6, 7, 8, 9, 10]
    assert int(rendering["map_width_px"]) > 0
    assert str(prompt["bundle_id"]) == "games_tower_defense_v0"
    assert "visible range ring" in str(prompt["coverage_rule_text_marked_enemy_covered_by_tower_count"])
    assert "path node" in str(prompt["coverage_rule_text_covered_path_segment_count"])


def test_games_tower_defense_prompt_bundle_has_coverage_query() -> None:
    bundle = json.loads(Path("prompts/games/tower_defense/games_tower_defense_v0.json").read_text(encoding="utf-8"))
    assert set(bundle["query_templates"].keys()) == {
        "marked_enemy_covered_by_tower_count",
        "covered_path_segment_count",
    }
    assert bundle["required_slots_by_key"]["query:marked_enemy_covered_by_tower_count"] == [
        "coverage_rule_text",
    ]
    assert bundle["required_slots_by_key"]["query:covered_path_segment_count"] == [
        "coverage_rule_text",
    ]


def test_games_tower_defense_target_answer_matches_distance_trace() -> None:
    out = create_task(TOWER_COVERAGE_TASK_ID).generate(
        92041,
        params={"target_answer": 3},
        max_attempts=300,
    )
    execution = out.trace_payload["execution_trace"]
    enemy_center = execution["marked_enemy"]["center_px_local"]
    covering_ids = []
    for tower in execution["towers"]:
        if _distance(tower["center_px_local"], enemy_center) <= float(tower["range_radius_px"]) + 1e-6:
            covering_ids.append(str(tower["tower_id"]))

    assert out.scene_id == "tower_defense"
    assert out.query_id == "marked_enemy_covered_by_tower_count"
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 3
    assert covering_ids == list(execution["annotation_entity_ids"])
    assert len(out.annotation_gt.value) == 3
    assert out.annotation_gt.type == "point_set"
    assert out.trace_payload["projected_annotation"]["type"] == "point_set"
    assert out.trace_payload["render_map"]["marked_enemy_id"] == "marked_enemy"


def test_games_tower_defense_zero_answer_uses_empty_point_set() -> None:
    out = create_task(TOWER_COVERAGE_TASK_ID).generate(
        92042,
        params={"target_answer": 0},
        max_attempts=300,
    )
    execution = out.trace_payload["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 0
    assert execution["annotation_entity_ids"] == []
    assert out.annotation_gt.type == "point_set"
    assert out.annotation_gt.value == []
    assert out.trace_payload["projected_annotation"]["point_set"] == []


def test_games_tower_defense_covered_path_answer_matches_distance_trace() -> None:
    out = create_task(COVERED_PATH_TASK_ID).generate(
        92043,
        params={"target_answer": 7},
        max_attempts=500,
    )
    execution = out.trace_payload["execution_trace"]
    covered_ids = []
    for index, point in enumerate(execution["path_points_px_local"]):
        if any(_distance(tower["center_px_local"], point) <= float(tower["range_radius_px"]) + 1e-6 for tower in execution["towers"]):
            covered_ids.append(f"path_segment_{index:02d}")

    assert out.scene_id == "tower_defense"
    assert out.query_id == "covered_path_segment_count"
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 7
    assert covered_ids == list(execution["annotation_entity_ids"])
    assert len(out.annotation_gt.value) == 7
    assert out.annotation_gt.type == "point_set"
    assert out.trace_payload["projected_annotation"]["type"] == "point_set"
    assert execution["marked_enemy"] is None
    assert out.trace_payload["render_map"]["marked_enemy_id"] is None


def test_games_tower_defense_taxonomy_mapping() -> None:
    taxonomy = resolve_task_taxonomy(TOWER_COVERAGE_TASK_ID)

    assert taxonomy.domain == "games"
    assert taxonomy.scene_id == "tower_defense"
    assert taxonomy.source_domain == "games"
    assert taxonomy.source_task_group == "tower_defense"

    path_taxonomy = resolve_task_taxonomy(COVERED_PATH_TASK_ID)
    assert path_taxonomy.domain == "games"
    assert path_taxonomy.scene_id == "tower_defense"
    assert path_taxonomy.source_domain == "games"
    assert path_taxonomy.source_task_group == "tower_defense"
