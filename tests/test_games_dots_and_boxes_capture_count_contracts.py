"""Contract tests for the games dots-and-boxes capture-count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.dots_and_boxes.capture_count import GamesDotsAndBoxesCaptureCountTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize("target_answer", (1, 4, 6))
def test_games_dots_and_boxes_capture_count_emits_expected_contract(target_answer: int) -> None:
    out = GamesDotsAndBoxesCaptureCountTask().generate(
        28101 + int(target_answer),
        params={
            "query_variant": "forced_turn_capture_count",
            "target_answer": int(target_answer),
        },
        max_attempts=64,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(target_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert trace["query_spec"]["params"]["task_variant"] == out.task_variant
    assert int(execution["target_answer"]) == int(target_answer)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["captured_box_ids"]) == int(target_answer)
    assert len(out.evidence_gt.value) == int(target_answer)
    assert execution["branching_edge_ids"] == []
    assert execution["captured_box_ids"] == execution["path_box_ids"]


def test_games_dots_and_boxes_capture_count_highlighted_edge_is_not_drawn_initially() -> None:
    out = GamesDotsAndBoxesCaptureCountTask().generate(
        28121,
        params={
            "target_answer": 3,
        },
        max_attempts=64,
    )
    execution = out.trace_payload["execution_trace"]
    assert execution["highlighted_edge_id"] not in execution["drawn_edge_ids"]
    assert execution["move_edge_sequence"][0] == execution["highlighted_edge_id"]


def test_games_dots_and_boxes_capture_count_is_deterministic() -> None:
    params = {
        "query_variant": "forced_turn_capture_count",
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


def test_games_dots_and_boxes_capture_count_prompt_bundle_requires_rule_text() -> None:
    bundle = json.loads(Path("prompts/games/dots_and_boxes/games_dots_and_boxes_v1.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["task_variant:forced_turn_capture_count"] == ["forced_turn_rule_text"]


def test_games_dots_and_boxes_capture_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games_dots_and_boxes_capture_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games_dots_and_boxes_capture_count",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games_dots_and_boxes_capture_count",
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
    assert int(build_report["accepted_counts_by_task"]["task_games_dots_and_boxes_capture_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
