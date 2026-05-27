"""Contract tests for the games Go group-property count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.go.group_property_count import GamesGoGroupLibertyConditionCountTask, GamesGoGroupPropertyCountTask
from trace.tasks.games.shared.style import SUPPORTED_GO_STYLE_VARIANTS
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer", "evidence_coord_key"),
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
    evidence_coord_key: str,
) -> None:
    out = GamesGoGroupPropertyCountTask().generate(34101, params=params, max_attempts=64)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert trace["query_spec"]["params"]["query_id"] == out.query_id
    assert int(execution["target_answer"]) == int(expected_answer)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == len(out.evidence_gt.value) == int(expected_answer)
    assert len(execution[evidence_coord_key]) == int(expected_answer)
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
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
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
    assert all(record["task_group"] == "go" for record in train_records)

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

    assert out.query_id == "default"
    assert out.query_id == query_id
    assert trace["query_spec"]["params"]["query_id"] == "default"
    assert trace["query_spec"]["params"]["query_id"] == query_id
    assert trace["execution_trace"]["query_id"] == "default"
    assert trace["execution_trace"]["query_id"] == query_id
    assert int(out.answer_gt.value) == int(target_answer)
