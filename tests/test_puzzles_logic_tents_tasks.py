"""Contracts for tents-grid logic puzzle tasks."""

from __future__ import annotations

import pytest

from trace.tasks.puzzles.logic.tents_grid import (
    SCENE_ID,
    PuzzlesLogicTentsMissingTentCellLabelTask,
    PuzzlesLogicTentsValidCandidateCountTask,
)


TASK_CLASSES = (
    PuzzlesLogicTentsMissingTentCellLabelTask,
    PuzzlesLogicTentsValidCandidateCountTask,
)


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_tents_tasks_emit_public_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(72001, params={}, max_attempts=40)

    assert out.scene_id == SCENE_ID
    assert out.query_id == "default"
    assert out.query_id
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) >= 1
    assert "Evidence format:" in out.prompt_variants["answer_and_evidence"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["params"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["params"]["query_id"] == "default"
    assert trace["query_spec"]["params"]["query_id"] == out.query_id
    assert trace["execution_trace"]["query_id"] == out.query_id
    assert trace["projected_evidence"]["type"] == "bbox_set"


def test_missing_tent_task_has_one_correct_labeled_cell() -> None:
    task = PuzzlesLogicTentsMissingTentCellLabelTask()
    out = task.generate(72011, params={}, max_attempts=40)
    trace = out.trace_payload["execution_trace"]

    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value in {"A", "B", "C", "D", "E", "F"}
    correct = [spec for spec in trace["candidate_specs"] if spec["is_correct"]]
    legal = [spec for spec in trace["candidate_specs"] if spec["is_legal"]]
    assert len(correct) == 1
    assert len(legal) == 1
    assert correct[0]["label"] == out.answer_gt.value


def test_valid_candidate_count_matches_legal_candidate_specs() -> None:
    task = PuzzlesLogicTentsValidCandidateCountTask()
    for sampling_index in range(5):
        out = task.generate(72021 + sampling_index, params={}, max_attempts=40)
        trace = out.trace_payload["execution_trace"]
        legal = [spec for spec in trace["candidate_specs"] if spec["is_legal"]]

        assert out.answer_gt.type == "integer"
        assert int(out.answer_gt.value) == len(legal)
        assert 0 <= int(out.answer_gt.value) <= 4
        assert trace["target_answer_support"] == [0, 1, 2, 3, 4]


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_tents_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    params = {}
    out_a = task.generate(72031, params=params, max_attempts=40)
    out_b = task.generate(72031, params=params, max_attempts=40)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.evidence_gt == out_b.evidence_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
