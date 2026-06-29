"""Contracts for scene-packaged Tents puzzle tasks."""

from __future__ import annotations

import pytest

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.puzzles.tents.missing_tent_cell_label import (
    PuzzlesTentsMissingTentCellLabelTask,
)
from trace.tasks.puzzles.tents.shared.state import SCENE_ID
from trace.tasks.puzzles.tents.valid_candidate_count import (
    PuzzlesTentsValidCandidateCountTask,
)

TASK_CLASSES = (
    PuzzlesTentsMissingTentCellLabelTask,
    PuzzlesTentsValidCandidateCountTask,
)


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_tents_tasks_emit_scene_package_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(72001, params={}, max_attempts=40)

    assert out.scene_id == SCENE_ID
    assert out.query_id == SINGLE_QUERY_ID
    assert "annotation" in out.prompt_variants["answer_and_annotation"].lower()
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["params"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["params"]["query_id"] == SINGLE_QUERY_ID
    assert trace["execution_trace"]["query_id"] == SINGLE_QUERY_ID
    assert trace["render_map"]["annotation_source"] == "item_bboxes_px"


def test_missing_tent_task_has_one_correct_labeled_cell() -> None:
    task = PuzzlesTentsMissingTentCellLabelTask()
    out = task.generate(72011, params={}, max_attempts=40)
    trace = out.trace_payload["execution_trace"]

    assert out.answer_gt.type == "option_letter"
    assert out.annotation_gt.type == "bbox"
    assert out.answer_gt.value in {"A", "B", "C", "D", "E", "F"}
    correct = [spec for spec in trace["candidate_specs"] if spec["is_correct"]]
    legal = [spec for spec in trace["candidate_specs"] if spec["is_legal"]]
    assert len(correct) == 1
    assert len(legal) == 1
    assert correct[0]["label"] == out.answer_gt.value
    assert out.trace_payload["projected_annotation"]["type"] == "bbox"


def test_valid_candidate_count_matches_legal_candidate_specs() -> None:
    task = PuzzlesTentsValidCandidateCountTask()
    for sampling_index in range(5):
        out = task.generate(72021 + sampling_index, params={}, max_attempts=40)
        trace = out.trace_payload["execution_trace"]
        legal = [spec for spec in trace["candidate_specs"] if spec["is_legal"]]

        assert out.answer_gt.type == "integer"
        assert out.annotation_gt.type == "bbox_set"
        assert int(out.answer_gt.value) == len(legal)
        assert 0 <= int(out.answer_gt.value) <= 4
        assert trace["target_answer_support"] == [0, 1, 2, 3, 4]
        assert len(out.annotation_gt.value) == int(out.answer_gt.value)
        assert out.trace_payload["projected_annotation"]["type"] == "bbox_set"


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_tents_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    params = {}
    out_a = task.generate(72031, params=params, max_attempts=40)
    out_b = task.generate(72031, params=params, max_attempts=40)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert (
        out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    )
