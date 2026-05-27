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
    ("params", "expected_answer", "expected_evidence_count", "expected_rows", "expected_columns"),
    (
        (
            {
                "scene_variant": "midgame_board",
                "query_variant": "winning_move_count",
                "target_answer": 3,
                "board_size_variant": "standard_7x6",
            },
            3,
            3,
            6,
            7,
        ),
        (
            {
                "scene_variant": "crowded_board",
                "query_variant": "safe_move_count",
                "target_answer": 3,
                "board_size_variant": "small_6x5",
            },
            3,
            3,
            5,
            6,
        ),
    ),
)
def test_games_connect_four_move_count_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
    expected_evidence_count: int,
    expected_rows: int,
    expected_columns: int,
) -> None:
    out = GamesConnectFourMoveCountTask().generate(31001, params=params, max_attempts=48)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == int(expected_evidence_count)
    assert trace["query_spec"]["params"]["query_variant"] == out.query_variant
    assert int(execution["target_answer"]) == int(expected_answer)
    assert int(execution["board_row_count"]) == int(expected_rows)
    assert int(execution["board_column_count"]) == int(expected_columns)
    assert int(trace["render_map"]["rows"]) == int(expected_rows)
    assert int(trace["render_map"]["columns"]) == int(expected_columns)
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
            "board_size_variant": "standard_7x6",
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


def test_games_connect_four_safe_move_count_default_board_size_uses_square_range() -> None:
    task = GamesConnectFourMoveCountTask()
    out = task.generate(
        31025,
        params={
            "query_variant": "safe_move_count",
            "target_answer": 2,
        },
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]

    assert str(execution["board_size_variant"]) in {"square_5x5", "square_6x6"}
    assert int(execution["board_row_count"]) == int(execution["board_column_count"])
    assert int(execution["board_row_count"]) in {5, 6}

    forced_six = task.generate(
        31026,
        params={
            "query_variant": "safe_move_count",
            "target_answer": 6,
        },
        max_attempts=256,
    )
    forced_execution = forced_six.trace_payload["execution_trace"]

    assert str(forced_execution["board_size_variant"]) == "square_6x6"
    assert int(forced_execution["board_row_count"]) == 6
    assert int(forced_execution["board_column_count"]) == 6


def test_games_connect_four_move_count_query_cycle_covers_safe_answer_support() -> None:
    safe_answers: list[int] = []
    styles_by_variant: dict[str, set[str]] = {
        "safe_move_count": set(),
        "winning_move_count": set(),
    }
    task = GamesConnectFourMoveCountTask()
    cases = (
        (
            "winning_move_count",
            {
                "scene_variant": "midgame_board",
                "board_size_variant": "standard_7x6",
                "target_answer": 3,
            },
        ),
        (
                "safe_move_count",
                {
                    "scene_variant": "crowded_board",
                    "board_size_variant": "small_6x5",
                    "target_answer": 3,
                },
        ),
    )
    expected_styles = {"classic", "soft", "outlined", "arcade_blue", "teal_frame", "charcoal"}
    for query_variant, base_params in cases:
        for sampling_index, style_variant in enumerate(sorted(expected_styles)):
            params = dict(base_params)
            params["query_variant"] = str(query_variant)
            params["style_variant"] = str(style_variant)
            params["_sample_cursor"] = int(sampling_index)
            out = task.generate(
                20260506 + int(sampling_index),
                params=params,
                max_attempts=96,
            )
            assert str(out.query_variant) == str(query_variant)
            execution = out.trace_payload["execution_trace"]
            styles_by_variant[str(query_variant)].add(str(execution["style_variant"]))
            if str(query_variant) == "safe_move_count":
                safe_answers.append(int(out.answer_gt.value))

    assert set(safe_answers) == {3}
    assert styles_by_variant == {
        "safe_move_count": expected_styles,
        "winning_move_count": expected_styles,
    }


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
    bundle = json.loads(Path("prompts/games/connect_four/games_connect_four_v0.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["query:winning_move_count"] == [
        "current_player_name",
        "legal_drop_rule_text",
        "winning_rule_text",
    ]
    assert required["query:safe_move_count"] == [
        "current_player_name",
        "opponent_player_name",
        "legal_drop_rule_text",
        "winning_rule_text",
        "safety_rule_text",
    ]


def test_games_connect_four_move_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__connect_four__move_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__connect_four__move_count",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__connect_four__move_count",
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
    assert int(build_report["accepted_counts_by_task"]["task_games__connect_four__move_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
