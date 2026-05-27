"""Contract tests for the games dots-and-boxes count task."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.dots_and_boxes.capture_count import GamesDotsAndBoxesCaptureCountTask, GamesDotsAndBoxesCaptureMoveCountTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("query_id", "target_answer"),
    (
        ("three_sided_box_count", 4),
        ("capture_move_count", 4),
        ("highlighted_candidate_capture_count", 4),
    ),
)
def test_games_dots_and_boxes_capture_count_emits_expected_contract(query_id: str, target_answer: int) -> None:
    out = GamesDotsAndBoxesCaptureCountTask().generate(
        28101 + int(target_answer),
        params={
            "query_id": str(query_id),
            "target_answer": int(target_answer),
        },
        max_attempts=64,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(target_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert trace["query_spec"]["params"]["query_id"] == out.query_id
    assert int(execution["target_answer"]) == int(target_answer)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(out.evidence_gt.value) == int(target_answer)
    assert execution["branching_edge_ids"] == []
    assert execution["captured_box_ids"] == []
    if str(query_id) == "three_sided_box_count":
        assert len(execution["counted_box_ids"]) == int(target_answer)
        assert all(execution["box_drawn_side_counts"][box_id] == 3 for box_id in execution["counted_box_ids"])
    elif str(query_id) == "capture_move_count":
        assert len(execution["counted_edge_ids"]) == int(target_answer)
        assert execution["counted_edge_ids"] == execution["immediate_capture_edge_ids"]
    else:
        assert 5 <= int(execution["candidate_edge_count"]) <= 8
        assert len(execution["candidate_edge_ids"]) == int(execution["candidate_edge_count"])
        assert execution["highlighted_edge_ids"] == execution["candidate_edge_ids"]
        assert len(execution["counted_edge_ids"]) == int(target_answer)
        assert set(execution["counted_edge_ids"]).issubset(set(execution["candidate_edge_ids"]))


def test_games_dots_and_boxes_capture_count_balanced_board_and_candidate_counts() -> None:
    task = GamesDotsAndBoxesCaptureCountTask()
    board_shapes: Counter[tuple[int, int]] = Counter()
    candidate_counts: Counter[int] = Counter()
    styles_by_query: dict[str, set[str]] = {}

    for index in range(90):
        out = task.generate(
            28200 + index,
            params={},
            max_attempts=64,
        )
        execution = out.trace_payload["execution_trace"]
        board_shapes[(int(execution["box_rows"]), int(execution["box_cols"]))] += 1
        candidate_counts[int(execution["candidate_edge_count"])] += 1
        styles_by_query.setdefault(str(out.query_id or out.query_id), set()).add(str(execution["style_variant"]))

    assert set(board_shapes.keys()) == {(3, 3), (3, 4), (4, 3), (4, 4)}
    assert set(candidate_counts.keys()) == {5, 6, 7, 8}
    assert styles_by_query == {
        "capture_move_count": {"classic", "soft", "outlined", "notebook", "slate", "wood_panel"},
        "highlighted_candidate_capture_count": {"classic", "soft", "outlined", "notebook", "slate", "wood_panel"},
        "three_sided_box_count": {"classic", "soft", "outlined", "notebook", "slate", "wood_panel"},
    }


def test_games_dots_and_boxes_capture_count_highlighted_candidate_edges_are_not_drawn() -> None:
    out = GamesDotsAndBoxesCaptureCountTask().generate(
        28121,
        params={
            "query_id": "highlighted_candidate_capture_count",
            "target_answer": 3,
        },
        max_attempts=64,
    )
    execution = out.trace_payload["execution_trace"]
    assert execution["highlighted_edge_ids"]
    assert set(execution["highlighted_edge_ids"]).isdisjoint(set(execution["drawn_edge_ids"]))


def test_games_dots_and_boxes_capture_move_public_task_merges_candidate_query() -> None:
    task = GamesDotsAndBoxesCaptureMoveCountTask()
    query_ids: Counter[str] = Counter()
    answers_by_query: dict[str, set[int]] = {}

    for index in range(36):
        out = task.generate(
            28125 + index,
            params={},
            max_attempts=64,
        )
        execution = out.trace_payload["execution_trace"]
        query_ids[str(out.query_id)] += 1
        answers_by_query.setdefault(str(out.query_id), set()).add(int(out.answer_gt.value))

        assert out.query_id == "default"
        assert str(out.query_id) in {"capture_move_count", "highlighted_candidate_capture_count"}
        assert execution["query_id"] == out.query_id
        assert execution["query_id"] == "default"
        assert out.evidence_gt.type == "bbox_set"
        assert len(out.evidence_gt.value) == int(out.answer_gt.value)
        if str(out.query_id) == "capture_move_count":
            assert execution["highlighted_edge_ids"] == []
        else:
            assert execution["highlighted_edge_ids"] == execution["candidate_edge_ids"]

    assert set(query_ids) == {"capture_move_count", "highlighted_candidate_capture_count"}
    assert all(count > 0 for count in query_ids.values())
    assert answers_by_query["capture_move_count"] == {0, 1, 2, 3, 4, 5}
    assert answers_by_query["highlighted_candidate_capture_count"] == {0, 1, 2, 3, 4, 5}


def test_games_dots_and_boxes_capture_count_is_deterministic() -> None:
    params = {
        "query_id": "capture_move_count",
        "target_answer": 5,
    }
    task = GamesDotsAndBoxesCaptureCountTask()
    out_a = task.generate(28131, params=params, max_attempts=64)
    out_b = task.generate(28131, params=params, max_attempts=64)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_dots_and_boxes_capture_count_prompt_bundle_declares_variants() -> None:
    bundle = json.loads(Path("prompts/games/dots_and_boxes/games_dots_and_boxes_v0.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["query:three_sided_box_count"] == []
    assert required["query:capture_move_count"] == []
    assert required["query:highlighted_candidate_capture_count"] == []


def test_games_dots_and_boxes_capture_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__dots_and_boxes__capture_move_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__dots_and_boxes__capture_move_count",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__dots_and_boxes__capture_move_count",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=64,
        sampling_seed=71,
    )
    final_path = build_dataset(config, code_hash="games-dots-and-boxes-capture-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "games" for record in train_records)
    assert all(record["task_group"] == "dots_and_boxes" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games__dots_and_boxes__capture_move_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
