"""Contract tests for the games Reversi move-count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.reversi.move_count import GamesReversiMoveCountTask
from trace.tasks.games.shared.reversi_common import corner_coords
from trace.tasks.games.shared.style import SUPPORTED_REVERSI_STYLE_VARIANTS
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer", "expected_evidence_count"),
    (
        (
            {
                "scene_variant": "compact_board",
                "query_variant": "legal_move_count",
                "target_answer": 4,
            },
            4,
            4,
        ),
        (
            {
                "scene_variant": "classic_board",
                "query_variant": "corner_move_count",
                "target_answer": 0,
            },
            0,
            0,
        ),
        (
            {
                "scene_variant": "classic_board",
                "query_variant": "flip_count_for_marked_move",
                "target_answer": 5,
            },
            5,
            5,
        ),
    ),
)
def test_games_reversi_move_count_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
    expected_evidence_count: int,
) -> None:
    out = GamesReversiMoveCountTask().generate(28001, params=params, max_attempts=32)
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
    assert all(str(entity_id).startswith("cell_r") for entity_id in execution["evidence_entity_ids"])


def test_games_reversi_move_count_corner_evidence_stays_on_corner_squares() -> None:
    out = GamesReversiMoveCountTask().generate(
        28011,
        params={
            "scene_variant": "classic_board",
            "query_variant": "corner_move_count",
            "target_answer": 2,
        },
        max_attempts=32,
    )
    execution = out.trace_payload["execution_trace"]
    corners = {tuple(coord) for coord in corner_coords(8)}
    evidence_coords = {tuple(coord) for coord in execution["evidence_coords"]}

    assert len(evidence_coords) == 2
    assert evidence_coords.issubset(corners)


def test_games_reversi_move_count_flip_query_marks_move_and_keeps_evidence_on_flipped_discs() -> None:
    out = GamesReversiMoveCountTask().generate(
        28021,
        params={
            "scene_variant": "classic_board",
            "query_variant": "flip_count_for_marked_move",
            "target_answer": 4,
        },
        max_attempts=32,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert execution["marked_move"] is not None
    assert execution["marked_move_cell_id"] is not None
    assert trace["render_map"]["marked_square_bbox_px"] is not None
    assert execution["marked_move_cell_id"] not in set(execution["evidence_entity_ids"])
    assert len(execution["marked_move_flip_coords"]) == 4


def test_games_reversi_move_count_query_cycle_covers_answer_scene_and_style_support() -> None:
    task = GamesReversiMoveCountTask()
    answers_by_variant: dict[str, set[int]] = {
        "legal_move_count": set(),
        "corner_move_count": set(),
        "flip_count_for_marked_move": set(),
    }
    scenes_by_variant: dict[str, set[str]] = {
        "legal_move_count": set(),
        "corner_move_count": set(),
        "flip_count_for_marked_move": set(),
    }
    styles_by_variant: dict[str, set[str]] = {
        "legal_move_count": set(),
        "corner_move_count": set(),
        "flip_count_for_marked_move": set(),
    }

    for sampling_index in range(63):
        out = task.generate(
            28101 + int(sampling_index),
            params={},
            max_attempts=192,
        )
        query_variant = str(out.query_id)
        execution = out.trace_payload["execution_trace"]
        answers_by_variant[query_variant].add(int(out.answer_gt.value))
        scenes_by_variant[query_variant].add(str(execution["scene_variant"]))
        styles_by_variant[query_variant].add(str(execution["style_variant"]))

    assert answers_by_variant == {
        "legal_move_count": {0, 1, 2, 3, 4, 5, 6},
        "corner_move_count": {0, 1, 2, 3, 4},
        "flip_count_for_marked_move": {2, 3, 4, 5, 6},
    }
    assert scenes_by_variant == {
        "legal_move_count": {"compact_board", "classic_board"},
        "corner_move_count": {"compact_board", "classic_board"},
        "flip_count_for_marked_move": {"compact_board", "classic_board"},
    }
    assert styles_by_variant == {
        "legal_move_count": set(SUPPORTED_REVERSI_STYLE_VARIANTS),
        "corner_move_count": set(SUPPORTED_REVERSI_STYLE_VARIANTS),
        "flip_count_for_marked_move": set(SUPPORTED_REVERSI_STYLE_VARIANTS),
    }


def test_games_reversi_move_count_is_deterministic() -> None:
    params = {
        "scene_variant": "compact_board",
        "query_variant": "legal_move_count",
        "target_answer": 6,
    }
    task = GamesReversiMoveCountTask()
    out_a = task.generate(28031, params=params, max_attempts=32)
    out_b = task.generate(28031, params=params, max_attempts=32)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_reversi_move_count_prompt_bundle_requires_rule_text_for_query_specific_prompts() -> None:
    bundle = json.loads(Path("prompts/games/reversi/games_reversi_v0.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["query:legal_move_count"] == ["current_player_name", "legal_move_rule_text"]
    assert required["query:corner_move_count"] == [
        "current_player_name",
        "legal_move_rule_text",
        "corner_rule_text",
    ]
    assert required["query:flip_count_for_marked_move"] == [
        "current_player_name",
        "legal_move_rule_text",
        "marked_move_rule_text",
        "flip_rule_text",
    ]


def test_games_reversi_move_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__reversi__legal_destination_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__reversi__legal_destination_count",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__reversi__legal_destination_count",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=32,
        sampling_seed=73,
    )
    final_path = build_dataset(config, code_hash="games-reversi-move-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "games" for record in train_records)
    assert all(record["task_group"] == "reversi" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games__reversi__legal_destination_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
