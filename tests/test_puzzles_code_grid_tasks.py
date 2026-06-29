"""Tests for code-grid puzzle tasks."""

from __future__ import annotations

import trace.tasks  # noqa: F401
from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.puzzles.code_grid.decoded_word_label import (
    PuzzlesCodeGridDecodedWordLabelTask,
    TASK_ID,
)
from trace.tasks.registry import TASK_REGISTRY


def _decoded_word_from_trace(trace: dict) -> str:
    grid = trace["grid"]
    letters = []
    for record in trace["target_cells"]:
        letters.append(str(grid[int(record["row"])][int(record["col"])]))
    return "".join(letters)


def _assert_bbox_sequence_in_bounds(out) -> None:
    assert out.annotation_gt.type == "bbox_sequence"
    width, height = out.image.size
    for bbox in out.annotation_gt.value:
        assert len(bbox) == 4
        assert 0 <= float(bbox[0]) < float(bbox[2]) <= width
        assert 0 <= float(bbox[1]) < float(bbox[3]) <= height


def test_code_grid_task_is_registered() -> None:
    assert TASK_REGISTRY[TASK_ID] is PuzzlesCodeGridDecodedWordLabelTask


def test_code_grid_decoded_word_contract() -> None:
    out = PuzzlesCodeGridDecodedWordLabelTask().generate(
        2026060701, params={}, max_attempts=80
    )
    trace = out.trace_payload["execution_trace"]

    assert out.scene_id == "code_grid"
    assert out.query_id == SINGLE_QUERY_ID
    assert out.answer_gt.type == "string"
    assert out.answer_gt.value == _decoded_word_from_trace(trace)
    assert out.answer_gt.value == trace["answer_value"]
    assert trace["coordinate_tokens"] == [
        record["coordinate"] for record in trace["target_cells"]
    ]
    assert len(out.annotation_gt.value) == len(trace["target_cells"])
    assert (
        out.trace_payload["projected_annotation"]["bbox_sequence"]
        == out.annotation_gt.value
    )
    assert out.trace_payload["render_map"]["annotation_source"] == "item_bboxes_px"
    _assert_bbox_sequence_in_bounds(out)


def test_code_grid_coordinate_formats_can_be_forced() -> None:
    for seed, coordinate_format in (
        (2026060711, "compact"),
        (2026060712, "spaced"),
    ):
        out = PuzzlesCodeGridDecodedWordLabelTask().generate(
            seed,
            params={
                "query_id": SINGLE_QUERY_ID,
                "coordinate_format": coordinate_format,
            },
            max_attempts=80,
        )
        trace = out.trace_payload["execution_trace"]

        assert out.query_id == SINGLE_QUERY_ID
        assert trace["query_id"] == SINGLE_QUERY_ID
        assert trace["coordinate_format"] == coordinate_format
        assert out.answer_gt.value == _decoded_word_from_trace(trace)
        if coordinate_format == "compact":
            assert " " not in trace["coordinate_sequence"]
        else:
            assert " " in trace["coordinate_sequence"]
        _assert_bbox_sequence_in_bounds(out)


def test_code_grid_generation_is_deterministic() -> None:
    task = PuzzlesCodeGridDecodedWordLabelTask()
    params = {
        "query_id": SINGLE_QUERY_ID,
        "coordinate_format": "spaced",
        "scene_variant": "code_grid_card",
        "grid_size": 5,
    }
    out_a = task.generate(2026060799, params=params, max_attempts=80)
    out_b = task.generate(2026060799, params=params, max_attempts=80)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert (
        out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    )
    assert out_a.image.tobytes() == out_b.image.tobytes()
