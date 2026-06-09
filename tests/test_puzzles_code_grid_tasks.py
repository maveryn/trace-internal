"""Tests for code-grid puzzle tasks."""

from __future__ import annotations

import trace.tasks  # noqa: F401
from trace.tasks.puzzles.word.code_grid import (
    DECODE_COORDINATE_SEQUENCE_QUERY_ID,
    DECODE_SPACED_COORDINATE_SEQUENCE_QUERY_ID,
    DECODED_WORD_TASK_ID,
    PuzzlesCodeGridDecodedWordLabelTask,
)
from trace.tasks.registry import TASK_REGISTRY


def _decoded_word_from_trace(trace: dict) -> str:
    grid = trace["grid"]
    letters = []
    for record in trace["target_cells"]:
        letters.append(str(grid[int(record["row"])][int(record["col"])]))
    return "".join(letters)


def _assert_keyed_bboxes_in_bounds(out) -> None:
    assert out.annotation_gt.type == "keyed_bbox_map"
    width, height = out.image.size
    for bbox in out.annotation_gt.value.values():
        assert len(bbox) == 4
        assert 0 <= float(bbox[0]) < float(bbox[2]) <= width
        assert 0 <= float(bbox[1]) < float(bbox[3]) <= height


def test_code_grid_task_is_registered() -> None:
    assert TASK_REGISTRY[DECODED_WORD_TASK_ID] is PuzzlesCodeGridDecodedWordLabelTask


def test_code_grid_decoded_word_contract() -> None:
    out = PuzzlesCodeGridDecodedWordLabelTask().generate(2026060701, params={}, max_attempts=80)
    trace = out.trace_payload["execution_trace"]

    assert out.scene_id == "code_grid"
    assert out.query_id in {
        DECODE_COORDINATE_SEQUENCE_QUERY_ID,
        DECODE_SPACED_COORDINATE_SEQUENCE_QUERY_ID,
    }
    assert out.answer_gt.type == "string"
    assert out.answer_gt.value == _decoded_word_from_trace(trace)
    assert out.answer_gt.value == trace["answer_value"]
    assert trace["coordinate_tokens"] == [record["coordinate"] for record in trace["target_cells"]]
    assert list(out.annotation_gt.value) == [f"cell_{index}" for index in range(1, len(trace["target_cells"]) + 1)]
    assert out.trace_payload["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert out.trace_payload["render_map"]["annotation_source"] == "keyed_item_bboxes_px"
    _assert_keyed_bboxes_in_bounds(out)


def test_code_grid_query_variants_can_be_forced() -> None:
    for seed, query_id in (
        (2026060711, DECODE_COORDINATE_SEQUENCE_QUERY_ID),
        (2026060712, DECODE_SPACED_COORDINATE_SEQUENCE_QUERY_ID),
    ):
        out = PuzzlesCodeGridDecodedWordLabelTask().generate(
            seed,
            params={"query_id": query_id},
            max_attempts=80,
        )
        trace = out.trace_payload["execution_trace"]

        assert out.query_id == query_id
        assert trace["query_id"] == query_id
        assert out.answer_gt.value == _decoded_word_from_trace(trace)
        if query_id == DECODE_COORDINATE_SEQUENCE_QUERY_ID:
            assert " " not in trace["coordinate_sequence"]
        else:
            assert " " in trace["coordinate_sequence"]
        _assert_keyed_bboxes_in_bounds(out)


def test_code_grid_generation_is_deterministic() -> None:
    task = PuzzlesCodeGridDecodedWordLabelTask()
    params = {
        "query_id": DECODE_SPACED_COORDINATE_SEQUENCE_QUERY_ID,
        "scene_variant": "code_grid_card",
        "grid_size": 5,
    }
    out_a = task.generate(2026060799, params=params, max_attempts=80)
    out_b = task.generate(2026060799, params=params, max_attempts=80)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()
