"""Tests for word-search puzzle tasks."""

from __future__ import annotations

import trace.tasks  # noqa: F401
from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.puzzles.word_search.search_letter_count_value import (
    PuzzlesWordSearchLetterCountValueTask,
    TASK_ID as LETTER_COUNT_TASK_ID,
)
from trace.tasks.puzzles.word_search.search_location_label import (
    PuzzlesWordSearchLocationLabelTask,
    TASK_ID as LOCATION_TASK_ID,
)
from trace.tasks.puzzles.word_search.search_present_word_count import (
    PuzzlesWordSearchPresentWordCountTask,
    TASK_ID as PRESENT_WORD_COUNT_TASK_ID,
)
from trace.tasks.registry import TASK_REGISTRY


def test_word_search_tasks_are_registered() -> None:
    assert TASK_REGISTRY[LOCATION_TASK_ID] is PuzzlesWordSearchLocationLabelTask
    assert TASK_REGISTRY[LETTER_COUNT_TASK_ID] is PuzzlesWordSearchLetterCountValueTask
    assert (
        TASK_REGISTRY[PRESENT_WORD_COUNT_TASK_ID]
        is PuzzlesWordSearchPresentWordCountTask
    )


def test_word_search_location_contract() -> None:
    out = PuzzlesWordSearchLocationLabelTask().generate(
        2026052201, params={}, max_attempts=80
    )
    trace = out.trace_payload["execution_trace"]

    assert out.scene_id == "word_search"
    assert out.query_id == SINGLE_QUERY_ID
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value in "ABCDEFGH"
    assert trace["query_id"] == SINGLE_QUERY_ID
    assert len(trace["placements"]) == 1
    correct = [spec for spec in trace["option_specs"] if spec["is_correct"]]
    assert len(correct) == 1
    assert correct[0]["label"] == out.answer_gt.value
    assert out.annotation_gt.type == "bbox_sequence"
    assert len(out.annotation_gt.value) == len(trace["placements"][0]["cells"])


def test_word_search_letter_count_matches_trace() -> None:
    out = PuzzlesWordSearchLetterCountValueTask().generate(
        2026052202, params={}, max_attempts=80
    )
    trace = out.trace_payload["execution_trace"]
    target = trace["target_letter"]
    grid_count = sum(1 for row in trace["grid"] for value in row if value == target)

    assert out.scene_id == "word_search"
    assert out.query_id == SINGLE_QUERY_ID
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == grid_count
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == grid_count


def test_word_search_present_word_count_matches_trace() -> None:
    out = PuzzlesWordSearchPresentWordCountTask().generate(
        2026052203, params={}, max_attempts=80
    )
    trace = out.trace_payload["execution_trace"]

    assert out.scene_id == "word_search"
    assert out.query_id == SINGLE_QUERY_ID
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == len(trace["present_words"])
    assert len(trace["word_bank"]) == 5
    assert 1 <= out.answer_gt.value <= 5
    assert len(trace["placements"]) == out.answer_gt.value
    assert out.annotation_gt.type == "segment_set"
    assert len(out.annotation_gt.value) == len(trace["placements"])


def test_word_search_generation_is_deterministic() -> None:
    task = PuzzlesWordSearchLocationLabelTask()
    a = task.generate(2026052204, params={}, max_attempts=80)
    b = task.generate(2026052204, params={}, max_attempts=80)

    assert a.answer_gt.to_dict() == b.answer_gt.to_dict()
    assert (
        a.trace_payload["execution_trace"]["grid"]
        == b.trace_payload["execution_trace"]["grid"]
    )
    assert a.annotation_gt.to_dict() == b.annotation_gt.to_dict()
