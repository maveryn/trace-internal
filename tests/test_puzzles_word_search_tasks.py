"""Tests for word-search puzzle tasks."""

from __future__ import annotations

import trace.tasks  # noqa: F401
from trace.tasks.puzzles.word.search_grid import (
    LETTER_COUNT_TASK_ID,
    LOCATION_TASK_ID,
    PRESENT_WORD_COUNT_TASK_ID,
    PuzzlesWordSearchLetterCountValueTask,
    PuzzlesWordSearchLocationLabelTask,
    PuzzlesWordSearchPresentWordCountTask,
)
from trace.tasks.registry import TASK_REGISTRY


def test_word_search_tasks_are_registered() -> None:
    assert TASK_REGISTRY[LOCATION_TASK_ID] is PuzzlesWordSearchLocationLabelTask
    assert TASK_REGISTRY[LETTER_COUNT_TASK_ID] is PuzzlesWordSearchLetterCountValueTask
    assert TASK_REGISTRY[PRESENT_WORD_COUNT_TASK_ID] is PuzzlesWordSearchPresentWordCountTask


def test_word_search_location_contract() -> None:
    out = PuzzlesWordSearchLocationLabelTask().generate(2026052201, params={}, max_attempts=80)
    trace = out.trace_payload["execution_trace"]

    assert out.scene_id == "word_search"
    assert out.query_id == "default"
    assert out.query_id == "word_location_label"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value in "ABCDEFGH"
    assert trace["query_id"] == "word_location_label"
    assert len(trace["placements"]) == 1
    correct = [spec for spec in trace["option_specs"] if spec["is_correct"]]
    assert len(correct) == 1
    assert correct[0]["label"] == out.answer_gt.value
    assert correct[0]["direction_code"] in {"R", "L", "U", "D", "DR", "UR", "DL", "UL"}
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == len(trace["supporting_item_ids"])


def test_word_search_letter_count_matches_trace() -> None:
    out = PuzzlesWordSearchLetterCountValueTask().generate(2026052202, params={}, max_attempts=80)
    trace = out.trace_payload["execution_trace"]
    target = trace["target_letter"]
    grid_count = sum(1 for row in trace["grid"] for value in row if value == target)

    assert out.scene_id == "word_search"
    assert out.query_id == "default"
    assert out.query_id == "letter_count_value"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == grid_count
    assert len(trace["supporting_item_ids"]) == grid_count
    assert len(out.evidence_gt.value) == grid_count


def test_word_search_present_word_count_matches_trace() -> None:
    out = PuzzlesWordSearchPresentWordCountTask().generate(2026052203, params={}, max_attempts=80)
    trace = out.trace_payload["execution_trace"]

    assert out.scene_id == "word_search"
    assert out.query_id == "default"
    assert out.query_id == "present_word_count"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == len(trace["present_words"])
    assert len(trace["word_bank"]) == 5
    assert 1 <= out.answer_gt.value <= 5
    assert len(trace["placements"]) == out.answer_gt.value
    assert len(out.evidence_gt.value) == len(trace["supporting_item_ids"])


def test_word_search_generation_is_deterministic() -> None:
    task = PuzzlesWordSearchLocationLabelTask()
    a = task.generate(2026052204, params={}, max_attempts=80)
    b = task.generate(2026052204, params={}, max_attempts=80)

    assert a.answer_gt.to_dict() == b.answer_gt.to_dict()
    assert a.trace_payload["execution_trace"]["grid"] == b.trace_payload["execution_trace"]["grid"]
    assert a.trace_payload["execution_trace"]["supporting_item_ids"] == b.trace_payload["execution_trace"]["supporting_item_ids"]
