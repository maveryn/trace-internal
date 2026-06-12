"""Contract tests for the games Go group-property count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.games.go.group_liberty_count import (
    GamesGoGroupLibertyConditionCountTask,
    GamesGoGroupPropertyCountTask,
    GamesGoStoneGroupCountTask,
)
from trace.tasks.games.go.shared.common import BLACK, WHITE, stone_groups
from trace.tasks.games.go.shared.scene import GO_MARKED_GROUP_RED_RGB
from trace.tasks.games.shared.style import SUPPORTED_GO_STYLE_VARIANTS
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer", "annotation_coord_key"),
    (
        (
            {
                "query_id": "marked_group_liberty_count",
                "player_color": "black",
                "target_answer": 2,
            },
            2,
            "liberty_coords",
        ),
        (
            {
                "query_id": "marked_white_group_liberty_count",
                "target_answer": 6,
            },
            6,
            "liberty_coords",
        ),
        (
            {
                "query_id": "marked_group_adjacent_enemy_count",
                "player_color": "white",
                "target_answer": 2,
            },
            2,
            "adjacent_enemy_coords",
        ),
        (
            {
                "query_id": "marked_group_shared_liberty_count",
                "player_color": "black",
                "target_answer": 4,
            },
            4,
            "shared_liberty_coords",
        ),
    ),
)
def test_games_go_group_property_count_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
    annotation_coord_key: str,
) -> None:
    out = GamesGoGroupPropertyCountTask().generate(34101, params=params, max_attempts=64)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.annotation_gt.type == "point_set"
    assert trace["query_spec"]["params"]["query_id"] == out.query_id
    assert int(execution["target_answer"]) == int(expected_answer)
    assert trace["projected_annotation"]["type"] == "point_set"
    assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_point_set"] == out.annotation_gt.value
    assert trace["render_spec"]["panel_scene_style"]
    assert trace["render_map"]["panel_scene_style"]
    marker_style = trace["render_map"]["marked_group_marker_style"]
    assert marker_style["role"] == "go_marked_stone_group"
    assert marker_style["inner_rgb"] == list(GO_MARKED_GROUP_RED_RGB)
    assert marker_style["passes"] is True
    assert marker_style["surface_rgbs"]
    assert "red outlined" in out.prompt.lower()
    assert len(execution["annotation_entity_ids"]) == len(out.annotation_gt.value) == int(expected_answer)
    assert len(execution[annotation_coord_key]) == int(expected_answer)
    assert len(execution["marked_group_coords"]) >= 1
    assert str(execution["marked_group_color"]) == str(execution["player_color"])


def test_games_go_group_property_count_query_cycle_covers_answer_and_scene_support() -> None:
    task = GamesGoGroupPropertyCountTask()
    answers_by_variant: dict[str, set[int]] = {
        "marked_group_liberty_count": set(),
        "marked_group_adjacent_enemy_count": set(),
        "marked_group_shared_liberty_count": set(),
    }
    scenes_by_variant: dict[str, set[str]] = {
        "marked_group_liberty_count": set(),
        "marked_group_adjacent_enemy_count": set(),
        "marked_group_shared_liberty_count": set(),
    }
    colors_by_variant: dict[str, set[str]] = {key: set() for key in answers_by_variant}
    styles_by_variant: dict[str, set[str]] = {key: set() for key in answers_by_variant}
    for sampling_index in range(96):
        out = task.generate(
            34201 + int(sampling_index),
            params={},
            max_attempts=192,
        )
        execution = out.trace_payload["execution_trace"]
        variant = str(out.query_id or out.query_id)
        answers_by_variant[variant].add(int(out.answer_gt.value))
        scenes_by_variant[variant].add(str(execution["scene_variant"]))
        colors_by_variant[variant].add(str(execution["player_color"]))
        styles_by_variant[variant].add(str(execution["style_variant"]))

    assert answers_by_variant == {
        "marked_group_liberty_count": {1, 2, 3, 4, 6},
        "marked_group_adjacent_enemy_count": {1, 2, 3, 4, 5, 6},
        "marked_group_shared_liberty_count": {1, 2, 3, 4, 5},
    }
    assert all(values == {"crowded_board", "open_board"} for values in scenes_by_variant.values())
    assert all(values == {"black", "white"} for values in colors_by_variant.values())
    assert all(values == set(SUPPORTED_GO_STYLE_VARIANTS) for values in styles_by_variant.values())


def test_games_go_group_property_count_is_deterministic() -> None:
    params = {
        "query_id": "marked_group_adjacent_enemy_count",
        "player_color": "white",
        "target_answer": 6,
    }
    task = GamesGoGroupPropertyCountTask()
    out_a = task.generate(34111, params=params, max_attempts=64)
    out_b = task.generate(34111, params=params, max_attempts=64)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_go_group_property_count_prompt_bundle_requires_rule_texts() -> None:
    bundle = json.loads(Path("prompts/games/go/games_go_v0.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["query:marked_group_liberty_count"] == [
        "marked_group_rule_text",
        "group_rule_text",
        "liberty_rule_text",
        "player_color",
    ]
    assert required["query:marked_group_adjacent_enemy_count"] == [
        "marked_group_rule_text",
        "group_rule_text",
        "adjacent_enemy_rule_text",
        "player_color",
    ]
    assert required["query:marked_group_shared_liberty_count"] == [
        "marked_group_rule_text",
        "group_rule_text",
        "liberty_rule_text",
        "shared_liberty_rule_text",
        "player_color",
    ]


def test_games_go_group_property_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__go__group_liberty_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__go__group_liberty_count",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__go__group_liberty_count",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=64,
        sampling_seed=91,
    )
    final_path = build_dataset(config, code_hash="games-go-group-property-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "games" for record in train_records)
    assert all(record.get("scene_id") == "go" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games__go__group_liberty_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0


@pytest.mark.parametrize(
    ("query_id", "target_answer"),
    (
        ("marked_group_liberty_count", 2),
        ("marked_group_shared_liberty_count", 4),
    ),
)
def test_games_go_liberty_condition_public_task_records_query_id(query_id: str, target_answer: int) -> None:
    out = GamesGoGroupLibertyConditionCountTask().generate(
        34151,
        params={"query_id": query_id, "player_color": "black", "target_answer": target_answer},
        max_attempts=96,
    )
    trace = out.trace_payload

    assert out.query_id == query_id
    assert trace["query_spec"]["params"]["query_id"] == query_id
    assert trace["execution_trace"]["query_id"] == query_id
    assert out.annotation_gt.type == "point_set"
    assert int(out.answer_gt.value) == int(target_answer)


@pytest.mark.parametrize(
    ("query_id", "target_answer", "target_color"),
    (
        ("black_stone_group_count", 1, BLACK),
        ("black_stone_group_count", 8, BLACK),
        ("white_stone_group_count", 5, WHITE),
    ),
)
def test_games_go_stone_group_count_emits_expected_contract(
    query_id: str,
    target_answer: int,
    target_color: int,
) -> None:
    out = GamesGoStoneGroupCountTask().generate(
        34301,
        params={"query_id": query_id, "target_answer": target_answer},
        max_attempts=192,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    board_size = int(execution["board_size"])
    rows = [[0 for _ in range(board_size)] for _ in range(board_size)]
    for spec in execution["stone_specs"]:
        rows[int(spec["row"])][int(spec["col"])] = 1 if str(spec["color"]) == "black" else -1

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(target_answer)
    assert out.annotation_gt.type == "point_set"
    assert len(out.annotation_gt.value) == int(target_answer)
    assert trace["projected_annotation"]["type"] == "point_set"
    assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert trace["render_map"]["marked_group_marker_style"] is None
    assert trace["query_spec"]["params"]["query_id"] == query_id
    assert execution["query_id"] == query_id
    assert str(execution["target_group_color"]) == ("black" if int(target_color) == BLACK else "white")
    assert len(stone_groups(rows, color=int(target_color))) == int(target_answer)
    assert len(execution["target_group_coords"]) == int(target_answer)
    assert len(execution["representative_coords"]) == int(target_answer)
    assert len(execution["annotation_entity_ids"]) == int(target_answer)
    assert "stone groups" in out.prompt.lower()


def test_games_go_stone_group_count_query_cycle_covers_answer_and_scene_support() -> None:
    task = GamesGoStoneGroupCountTask()
    answers_by_query: dict[str, set[int]] = {
        "black_stone_group_count": set(),
        "white_stone_group_count": set(),
    }
    scenes_by_query: dict[str, set[str]] = {key: set() for key in answers_by_query}
    styles_by_query: dict[str, set[str]] = {key: set() for key in answers_by_query}
    for sampling_index in range(96):
        out = task.generate(
            34321 + int(sampling_index),
            params={"_sample_cursor": sampling_index},
            max_attempts=192,
        )
        execution = out.trace_payload["execution_trace"]
        query_id = str(out.query_id)
        answers_by_query[query_id].add(int(out.answer_gt.value))
        scenes_by_query[query_id].add(str(execution["scene_variant"]))
        styles_by_query[query_id].add(str(execution["style_variant"]))

    assert answers_by_query == {
        "black_stone_group_count": {1, 2, 3, 4, 5, 6, 7, 8},
        "white_stone_group_count": {1, 2, 3, 4, 5, 6, 7, 8},
    }
    assert all(values == {"crowded_board", "open_board"} for values in scenes_by_query.values())
    assert all(values == set(SUPPORTED_GO_STYLE_VARIANTS) for values in styles_by_query.values())


def test_games_go_stone_group_count_prompt_bundle_requires_query_slots() -> None:
    bundle = json.loads(Path("prompts/games/go/games_go_v0.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["query:black_stone_group_count"] == ["group_rule_text"]
    assert required["query:white_stone_group_count"] == ["group_rule_text"]


def test_games_go_stone_group_count_public_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy("task_games__go__stone_group_count")
    assert taxonomy.domain == "games"
    assert taxonomy.scene_id == "go"


def test_games_go_stone_group_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__go__stone_group_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__go__stone_group_count",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__go__stone_group_count",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=192,
        sampling_seed=92,
    )
    final_path = build_dataset(config, code_hash="games-go-stone-group-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "games" for record in train_records)
    assert all(record.get("scene_id") == "go" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games__go__stone_group_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
