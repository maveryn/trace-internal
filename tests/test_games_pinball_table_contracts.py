"""Contract tests for games Pinball-table tasks."""

from __future__ import annotations

import inspect
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.pinball_table.first_hit_object_label import (
    GamesPinballFirstHitObjectLabelTask,
    _first_hit_object_id,
    _turn_angle_degrees,
)
from trace.tasks.games.pinball_table.path_score_value import GamesPinballPathScoreValueTask
from trace.tasks.games.pinball_table.shared.common import (
    SUPPORTED_PINBALL_QUERY_IDS,
    SUPPORTED_PINBALL_SCENE_VARIANTS,
    SUPPORTED_PINBALL_STYLE_VARIANTS,
    PinballObject,
)
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from tests.helpers import read_jsonl


def test_games_pinball_table_scene_package_source_layout() -> None:
    expected_sources = {
        GamesPinballFirstHitObjectLabelTask: Path("trace/tasks/games/pinball_table/first_hit_object_label.py"),
        GamesPinballPathScoreValueTask: Path("trace/tasks/games/pinball_table/path_score_value.py"),
    }

    for task_cls, relative_path in expected_sources.items():
        source_path = Path(inspect.getsourcefile(task_cls) or "").resolve()
        assert source_path == (Path.cwd() / relative_path).resolve()
        assert getattr(task_cls, "scene_id", "")
        assert getattr(task_cls, "scene_id") == "pinball_table"


def test_games_pinball_table_defaults_present() -> None:
    generation, _rendering, prompt = load_scene_generation_rendering_prompt_defaults(
        "games",
        "pinball_table",
        task_id="task_games__pinball_table__first_hit_object_label",
    )

    assert set(generation["scene_variant_weights"].keys()) == set(SUPPORTED_PINBALL_SCENE_VARIANTS)
    assert set(generation["query_id_weights"].keys()) == set(SUPPORTED_PINBALL_QUERY_IDS)
    assert set(generation["style_variant_weights"].keys()) == set(SUPPORTED_PINBALL_STYLE_VARIANTS)
    assert len(SUPPORTED_PINBALL_STYLE_VARIANTS) >= 5
    assert str(prompt["bundle_id"]) == "games_pinball_table_v0"
    assert "straight path" in str(prompt["pinball_motion_rule_text"]).lower()
    assert "full drawn ball path" in str(prompt["object_description_score_path"]).lower()
    assert "[x, y] pixel point" in str(prompt["annotation_hint_first_hit_object_label"])
    assert "add it twice" in str(prompt["pinball_score_rule_text"]).lower()
    assert "ordered json array" in str(prompt["annotation_hint_path_score_value"]).lower()
    assert "[x, y] pixel point" in str(prompt["annotation_hint_path_score_value"])


def test_games_pinball_first_hit_emits_expected_contract() -> None:
    out = GamesPinballFirstHitObjectLabelTask().generate(
        98100,
        params={"object_count": 8, "target_object_label": "H", "style_variant": "neon"},
        max_attempts=512,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "string"
    assert out.annotation_gt.type == "point_set"
    assert len(out.annotation_gt.value) == 1
    assert out.query_id == "first_hit_object_label"
    assert out.scene_id == "pinball_table"
    assert trace["query_spec"]["query_id"] == "first_hit_object_label"
    assert trace["query_spec"]["params"]["query_id"] == "first_hit_object_label"
    assert execution["query_id"] == "first_hit_object_label"
    assert trace["projected_annotation"]["type"] == "point_set"
    assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_point_set"] == out.annotation_gt.value
    assert trace["render_map"]["playfield_projection"]["kind"] == "trapezoid_isometric"
    assert trace["render_map"]["decorative_entities"]
    assert "panel_scene_style" in trace["render_spec"]
    assert "text_style" in trace["render_spec"]
    assert len(execution["annotation_entity_ids"]) == 1
    decorative_ids = {str(entity["id"]) for entity in trace["render_map"]["decorative_entities"]}
    assert not decorative_ids.intersection(str(entity_id) for entity_id in execution["annotation_entity_ids"])


def test_games_pinball_first_hit_matches_recomputed_ray_hit() -> None:
    out = GamesPinballFirstHitObjectLabelTask().generate(
        98110,
        params={"object_count": 8, "target_object_label": "G", "style_variant": "classic"},
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    target_id = str(execution["target_object_id"])
    ball = tuple(float(value) for value in execution["ball_xy_norm"])
    objects = tuple(
        PinballObject(
            object_id=str(obj["object_id"]),
            label=str(obj["label"]),
            kind=str(obj["kind"]),
            x_norm=float(obj["x_norm"]),
            y_norm=float(obj["y_norm"]),
            radius_norm=float(obj["radius_norm"]),
            width_norm=float(obj["width_norm"]),
            height_norm=float(obj["height_norm"]),
            color_index=0,
        )
        for obj in execution["objects"]
    )

    first_hit = _first_hit_object_id(
        origin=ball,
        angle_rad=float(execution["cue_angle_rad"]),
        objects=objects,
    )
    assert str(first_hit) == target_id
    assert str(out.answer_gt.value) == str(execution["target_object_label"])
    assert list(execution["annotation_entity_ids"]) == [target_id]
    assert 5 <= len(execution["objects"]) <= 8
    assert out.annotation_gt.value == [out.trace_payload["render_map"]["entity_points_px"][target_id]]


def test_games_pinball_path_score_emits_expected_contract() -> None:
    out = GamesPinballPathScoreValueTask().generate(
        98200,
        params={
            "object_count": 8,
            "path_hit_count": 3,
            "path_shape": "one_ricochet",
            "style_variant": "neon",
        },
        max_attempts=512,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    annotation_entity_ids = [str(entity_id) for entity_id in execution["annotation_entity_ids"]]
    score_by_id = {
        str(obj["object_id"]): int(obj["score_value"])
        for obj in execution["objects"]
    }

    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "point_sequence"
    assert out.query_id == "path_score_value"
    assert out.scene_id == "pinball_table"
    assert trace["query_spec"]["query_id"] == "path_score_value"
    assert trace["query_spec"]["params"]["query_id"] == "path_score_value"
    assert execution["query_id"] == "path_score_value"
    assert execution["path_shape"] == "one_ricochet"
    assert execution["path_hit_count"] == 3
    assert len(annotation_entity_ids) == 3
    path_points_norm = execution["hidden_path_norm"]
    assert len(trace["render_map"]["motion_paths_px"]["shown_path"]["points"]) >= 3
    assert len(path_points_norm) - 1 == 3
    turn_angles = [
        _turn_angle_degrees(
            tuple(float(value) for value in path_points_norm[index - 1]),
            tuple(float(value) for value in path_points_norm[index]),
            tuple(float(value) for value in path_points_norm[index + 1]),
        )
        for index in range(1, len(path_points_norm) - 1)
    ]
    assert min(turn_angles) >= 52.0
    assert float(path_points_norm[-1][1]) >= 0.90
    assert out.answer_gt.value == sum(score_by_id[entity_id] for entity_id in annotation_entity_ids)
    assert out.annotation_gt.value == [
        trace["render_map"]["entity_points_px"][entity_id]
        for entity_id in annotation_entity_ids
    ]
    assert trace["projected_annotation"]["type"] == "point_sequence"
    assert trace["projected_annotation"]["point_sequence"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_point_sequence"] == out.annotation_gt.value
    assert all(
        int(obj["score_value"]) > 0 and str(obj["display_text"]) == str(int(obj["score_value"]))
        for obj in execution["objects"]
    )


def test_games_pinball_path_score_repeated_hit_adds_score_twice() -> None:
    out = GamesPinballPathScoreValueTask().generate(
        98231,
        params={
            "object_count": 8,
            "path_hit_count": 3,
            "path_shape": "target_revisit",
            "style_variant": "classic",
        },
        max_attempts=512,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    annotation_entity_ids = [str(entity_id) for entity_id in execution["annotation_entity_ids"]]
    repeated_ids = {
        entity_id
        for entity_id in annotation_entity_ids
        if annotation_entity_ids.count(entity_id) > 1
    }
    score_by_id = {
        str(obj["object_id"]): int(obj["score_value"])
        for obj in execution["objects"]
    }

    assert execution["path_shape"] == "target_revisit"
    assert len(execution["hidden_path_norm"]) - 1 == 4
    assert repeated_ids
    assert execution["repeated_hit_object_ids"] == sorted(repeated_ids)
    assert out.annotation_gt.type == "point_sequence"
    assert out.answer_gt.value == sum(score_by_id[entity_id] for entity_id in annotation_entity_ids)
    assert out.annotation_gt.value == [
        trace["render_map"]["entity_points_px"][entity_id]
        for entity_id in annotation_entity_ids
    ]


def test_games_pinball_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__pinball_table"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__pinball_table",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(task_id="task_games__pinball_table__first_hit_object_label", count=1, params={}),
            BuildTaskConfig(task_id="task_games__pinball_table__path_score_value", count=1, params={}),
        ],
        max_attempts_per_instance=512,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-pinball-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 2
    assert {row["task"] for row in rows} == {
        "task_games__pinball_table__first_hit_object_label",
        "task_games__pinball_table__path_score_value",
    }
    assert all(row["domain"] == "games" for row in rows)
    assert all(row["scene_id"] == "pinball_table" for row in rows)
    assert all(row.get("scene_id") for row in rows)
