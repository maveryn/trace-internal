"""Contract tests for the games Checkers move-count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.checkers.move_count import (
    GamesCheckersMaxCaptureChainLengthTask,
    GamesCheckersMoveCountPublicTask,
    GamesCheckersMoveCountTask,
)
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer", "expected_evidence_count"),
    (
        (
            {
                "scene_variant": "midgame_board",
                "query_variant": "legal_move_count",
                "target_answer": 3,
            },
            3,
            3,
        ),
        (
            {
                "scene_variant": "crowded_board",
                "query_variant": "capture_move_count",
                "target_answer": 2,
            },
            2,
            2,
        ),
        (
            {
                "scene_variant": "midgame_board",
                "query_variant": "max_capture_chain_length",
                "target_answer": 4,
            },
            4,
            4,
        ),
    ),
)
def test_games_checkers_move_count_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
    expected_evidence_count: int,
) -> None:
    out = GamesCheckersMoveCountTask().generate(33001, params=params, max_attempts=96)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == int(expected_evidence_count)
    assert trace["query_spec"]["params"]["query_variant"] == out.query_variant
    assert int(execution["target_answer"]) == int(expected_answer)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == int(expected_evidence_count)
    if str(params["query_variant"]) == "max_capture_chain_length":
        assert all(str(entity_id).startswith("piece_") for entity_id in execution["evidence_entity_ids"])
        assert execution["evidence_kind"] == "piece"
        assert execution["max_capture_chain_length"] == int(expected_answer)
    else:
        assert all(str(entity_id).startswith("cell_r") for entity_id in execution["evidence_entity_ids"])


def test_games_checkers_move_count_legal_evidence_tracks_unique_landing_squares() -> None:
    out = GamesCheckersMoveCountTask().generate(
        33011,
        params={
            "scene_variant": "midgame_board",
            "query_variant": "legal_move_count",
            "target_answer": 5,
        },
        max_attempts=96,
    )
    execution = out.trace_payload["execution_trace"]
    evidence_coords = {tuple(coord) for coord in execution["evidence_coords"]}
    landing_coords = {tuple(move["landing"]) for move in execution["legal_move_specs"]}

    assert evidence_coords == landing_coords
    assert len(evidence_coords) == 5


def test_games_checkers_move_count_capture_evidence_tracks_capture_landings_only() -> None:
    out = GamesCheckersMoveCountTask().generate(
        33021,
        params={
            "scene_variant": "crowded_board",
            "query_variant": "capture_move_count",
            "target_answer": 4,
        },
        max_attempts=96,
    )
    execution = out.trace_payload["execution_trace"]
    evidence_coords = {tuple(coord) for coord in execution["evidence_coords"]}
    capture_landings = {
        tuple(move["landing"])
        for move in execution["legal_move_specs"]
        if move["captured"] is not None
    }

    assert evidence_coords == capture_landings
    assert len(evidence_coords) == 4


def test_games_checkers_max_capture_chain_evidence_tracks_captured_pieces() -> None:
    out = GamesCheckersMaxCaptureChainLengthTask().generate(
        33041,
        params={
            "scene_variant": "crowded_board",
            "target_answer": 5,
        },
        max_attempts=160,
    )
    execution = out.trace_payload["execution_trace"]
    evidence_coords = {tuple(coord) for coord in execution["evidence_coords"]}
    chain = execution["max_capture_chain_specs"][0]
    captured_coords = {tuple(coord) for coord in chain["captured"]}

    assert out.query_variant == "default"
    assert out.query_id == "max_capture_chain_length"
    assert int(out.answer_gt.value) == 5
    assert evidence_coords == captured_coords
    assert len(evidence_coords) == 5


def test_games_checkers_move_count_query_cycle_covers_legal_answer_support() -> None:
    task = GamesCheckersMoveCountTask()
    legal_answers: list[int] = []
    chain_answers: list[int] = []
    scenes_by_variant: dict[str, set[str]] = {
        "capture_move_count": set(),
        "legal_move_count": set(),
        "max_capture_chain_length": set(),
    }
    styles_by_variant: dict[str, set[str]] = {
        "capture_move_count": set(),
        "legal_move_count": set(),
        "max_capture_chain_length": set(),
    }
    for sampling_index in range(108):
        out = task.generate(
            33101 + int(sampling_index),
            params={},
            max_attempts=160,
        )
        query_variant = str(out.query_variant)
        execution = out.trace_payload["execution_trace"]
        scenes_by_variant[query_variant].add(str(execution["scene_variant"]))
        styles_by_variant[query_variant].add(str(execution["style_variant"]))
        if query_variant == "legal_move_count":
            legal_answers.append(int(out.answer_gt.value))
        if query_variant == "max_capture_chain_length":
            chain_answers.append(int(out.answer_gt.value))

    assert set(legal_answers) == {0, 1, 2, 3, 4, 5}
    assert set(chain_answers) == {1, 2, 3, 4, 5}
    assert scenes_by_variant == {
        "capture_move_count": {"crowded_board", "midgame_board"},
        "legal_move_count": {"crowded_board", "midgame_board"},
        "max_capture_chain_length": {"crowded_board", "midgame_board"},
    }
    assert styles_by_variant == {
        "capture_move_count": {"classic", "soft", "outlined", "wood_token", "blue_table", "charcoal"},
        "legal_move_count": {"classic", "soft", "outlined", "wood_token", "blue_table", "charcoal"},
        "max_capture_chain_length": {"classic", "soft", "outlined", "wood_token", "blue_table", "charcoal"},
    }


def test_games_checkers_move_count_is_deterministic() -> None:
    params = {
        "scene_variant": "crowded_board",
        "query_variant": "capture_move_count",
        "target_answer": 1,
    }
    task = GamesCheckersMoveCountTask()
    out_a = task.generate(33031, params=params, max_attempts=96)
    out_b = task.generate(33031, params=params, max_attempts=96)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_checkers_move_count_prompt_bundle_requires_rule_text_for_query_specific_prompts() -> None:
    bundle = json.loads(Path("prompts/games/checkers/games_checkers_v0.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["query:legal_move_count"] == [
        "current_player_name",
        "movement_rule_text",
        "capture_rule_text",
        "single_jump_rule_text",
        "legal_move_rule_text",
    ]
    assert required["query:capture_move_count"] == [
        "current_player_name",
        "movement_rule_text",
        "capture_rule_text",
        "single_jump_rule_text",
    ]
    assert required["query:max_capture_chain_length"] == [
        "current_player_name",
        "capture_rule_text",
        "king_chain_rule_text",
    ]


def test_games_checkers_move_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__checkers__move_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__checkers__move_count",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__checkers__move_count",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=96,
        sampling_seed=83,
    )
    final_path = build_dataset(config, code_hash="games-checkers-move-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "games" for record in train_records)
    assert all(record["task_group"] == "checkers" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games__checkers__move_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
