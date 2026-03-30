"""Contract tests for the games Connect Four move-count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.connect_four.move_count import GamesConnectFourMoveCountTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer", "expected_evidence_count"),
    (
        (
            {
                "scene_variant": "midgame_board",
                "query_variant": "winning_move_count",
                "target_answer": 3,
            },
            3,
            3,
        ),
        (
            {
                "scene_variant": "crowded_board",
                "query_variant": "safe_move_count",
                "target_answer": 2,
            },
            2,
            2,
        ),
    ),
)
def test_games_connect_four_move_count_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
    expected_evidence_count: int,
) -> None:
    out = GamesConnectFourMoveCountTask().generate(31001, params=params, max_attempts=48)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == int(expected_evidence_count)
    assert trace["query_spec"]["params"]["task_variant"] == out.task_variant
    assert int(execution["target_answer"]) == int(expected_answer)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == int(expected_evidence_count)
    assert all(str(entity_id).startswith("cell_r") for entity_id in execution["evidence_entity_ids"])


def test_games_connect_four_move_count_winning_evidence_stays_on_immediate_wins() -> None:
    out = GamesConnectFourMoveCountTask().generate(
        31011,
        params={
            "scene_variant": "midgame_board",
            "query_variant": "winning_move_count",
            "target_answer": 4,
        },
        max_attempts=48,
    )
    execution = out.trace_payload["execution_trace"]
    evidence_coords = {tuple(coord) for coord in execution["evidence_coords"]}
    winning_coords = {tuple(coord) for coord in execution["winning_move_coords"]}

    assert evidence_coords == winning_coords
    assert len(evidence_coords) == 4


def test_games_connect_four_move_count_safe_evidence_tracks_safe_landing_squares() -> None:
    out = GamesConnectFourMoveCountTask().generate(
        31021,
        params={
            "scene_variant": "crowded_board",
            "query_variant": "safe_move_count",
            "target_answer": 3,
        },
        max_attempts=48,
    )
    execution = out.trace_payload["execution_trace"]
    evidence_coords = {tuple(coord) for coord in execution["evidence_coords"]}
    safe_coords = {tuple(coord) for coord in execution["safe_move_coords"]}

    assert evidence_coords == safe_coords
    assert len(evidence_coords) == 3
    assert len(execution["winning_move_coords"]) == 0


def test_games_connect_four_move_count_is_deterministic() -> None:
    params = {
        "scene_variant": "crowded_board",
        "query_variant": "safe_move_count",
        "target_answer": 1,
    }
    task = GamesConnectFourMoveCountTask()
    out_a = task.generate(31041, params=params, max_attempts=64)
    out_b = task.generate(31041, params=params, max_attempts=64)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_connect_four_move_count_prompt_bundle_requires_rule_text_for_query_specific_prompts() -> None:
    bundle = json.loads(Path("prompts/games/connect_four/games_connect_four_v1.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["task_variant:winning_move_count"] == [
        "current_player_name",
        "legal_drop_rule_text",
        "winning_rule_text",
    ]
    assert required["task_variant:safe_move_count"] == [
        "current_player_name",
        "opponent_player_name",
        "legal_drop_rule_text",
        "winning_rule_text",
        "safety_rule_text",
    ]


def test_games_connect_four_move_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games_connect_four_move_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games_connect_four_move_count",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games_connect_four_move_count",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=64,
        sampling_seed=79,
    )
    final_path = build_dataset(config, code_hash="games-connect-four-move-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "games" for record in train_records)
    assert all(record["task_group"] == "connect_four" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games_connect_four_move_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
