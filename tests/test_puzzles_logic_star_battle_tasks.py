"""Contracts for Star Battle logic puzzle tasks."""

from __future__ import annotations

import pytest

from trace.tasks.puzzles.logic.star_battle_grid import (
    REMAINING_COUNT_QUERY_IDS,
    SCENE_ID,
    VALID_CELL_QUERY_IDS,
    PuzzlesLogicStarBattleRemainingCountTask,
    PuzzlesLogicStarBattleValidCellLabelTask,
)


TASK_CLASSES = (
    PuzzlesLogicStarBattleValidCellLabelTask,
    PuzzlesLogicStarBattleRemainingCountTask,
)


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_star_battle_tasks_emit_public_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(83101, params={}, max_attempts=80)

    assert out.scene_id == SCENE_ID
    assert out.query_variant == "default"
    assert out.query_id
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) >= 1
    assert "evidence" in out.prompt_variants["answer_and_evidence"].lower()
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["params"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["params"]["query_variant"] == "default"
    assert trace["query_spec"]["params"]["query_id"] == out.query_id
    assert trace["execution_trace"]["query_id"] == out.query_id
    assert trace["projected_evidence"]["type"] == "bbox_set"


@pytest.mark.parametrize("query_id", VALID_CELL_QUERY_IDS)
def test_star_battle_valid_cell_task_has_one_correct_labeled_cell(query_id: str) -> None:
    task = PuzzlesLogicStarBattleValidCellLabelTask()
    out = task.generate(83111, params={"query_variant": query_id}, max_attempts=80)
    trace = out.trace_payload["execution_trace"]

    assert out.query_id == query_id
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value in {"A", "B", "C", "D", "E", "F", "G", "H"}
    correct = [spec for spec in trace["candidate_specs"] if spec["is_correct"]]
    legal = [spec for spec in trace["candidate_specs"] if spec["is_legal"]]
    assert len(correct) == 1
    assert len(legal) == 1
    assert correct[0]["label"] == out.answer_gt.value


@pytest.mark.parametrize("query_id", REMAINING_COUNT_QUERY_IDS)
def test_star_battle_remaining_count_matches_scoped_legal_cells(query_id: str) -> None:
    task = PuzzlesLogicStarBattleRemainingCountTask()
    out = task.generate(83121, params={"query_variant": query_id}, max_attempts=80)
    trace = out.trace_payload["execution_trace"]

    assert out.query_id == query_id
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == len(trace["scoped_legal_cells"])
    target_min, target_max = trace["target_count_range"]
    assert int(target_min) <= int(out.answer_gt.value) <= int(target_max)


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_star_battle_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    params = {}
    out_a = task.generate(83131, params=params, max_attempts=80)
    out_b = task.generate(83131, params=params, max_attempts=80)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.evidence_gt == out_b.evidence_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
