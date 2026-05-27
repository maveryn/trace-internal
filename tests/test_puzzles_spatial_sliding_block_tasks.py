"""Contract tests for sliding-block puzzle tasks."""

from __future__ import annotations

from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.spatial.sliding_block import (
    PuzzlesSpatialSlidingBlockBlockerCountTask,
    PuzzlesSpatialSlidingBlockMoveResultLabelTask,
)


TASKS = (
    (
        "task_puzzles__sliding_block__sliding_block_blocker_count",
        PuzzlesSpatialSlidingBlockBlockerCountTask,
        "blocker_count",
        "integer",
    ),
    (
        "task_puzzles__sliding_block__sliding_block_move_result_label",
        PuzzlesSpatialSlidingBlockMoveResultLabelTask,
        "move_result_label",
        "option_letter",
    ),
)


def test_sliding_block_tasks_are_registered_and_taxonomy_mapped() -> None:
    for task_id, task_cls, _query_id, _answer_type in TASKS:
        assert TASK_REGISTRY[task_id] is task_cls
        taxonomy = resolve_task_taxonomy(task_id)
        assert taxonomy.domain == "puzzles"
        assert taxonomy.scene_id == "sliding_block"


def test_sliding_block_tasks_emit_contracts() -> None:
    for index, (_task_id, task_cls, query_id, answer_type) in enumerate(TASKS):
        out = task_cls().generate(2026052700 + index, params={}, max_attempts=30)
        trace = out.trace_payload
        execution = trace["execution_trace"]

        assert out.scene_id == "sliding_block"
        assert out.query_variant == "default"
        assert out.query_id == query_id
        assert out.answer_gt.type == answer_type
        assert out.evidence_gt.type == "bbox_set"
        assert trace["query_spec"]["params"]["query_variant"] == "default"
        assert trace["query_spec"]["params"]["query_id"] == query_id
        assert trace["render_spec"]["scene_id"] == "sliding_block"
        if query_id == "move_result_label":
            assert trace["render_map"]["evidence_source"] == "block_bboxes_px+option_panel_bboxes_px"
        else:
            assert trace["render_map"]["evidence_source"] == "block_bboxes_px"
        assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert out.image.size == (
            int(trace["render_spec"]["canvas_width"]),
            int(trace["render_spec"]["canvas_height"]),
        )
        assert execution["answer_block_ids"]
        if query_id == "blocker_count":
            assert len(out.evidence_gt.value) == len(execution["answer_block_ids"])
            assert int(out.answer_gt.value) == len(execution["blocking_block_ids"])
            assert execution["answer_block_ids"] == execution["blocking_block_ids"]
        else:
            correct_options = [option for option in execution["option_boards"] if option["is_correct"]]
            assert len(correct_options) == 1
            assert str(out.answer_gt.value) == str(correct_options[0]["label"])
            assert 1 <= len(execution["move_sequence"]) <= 3
            assert execution["answer_block_ids"] == execution["moved_block_ids"]
            assert len(out.evidence_gt.value) == len(execution["moved_block_ids"]) + 1
        for bbox in out.evidence_gt.value:
            assert len(bbox) == 4
            assert bbox[0] < bbox[2]
            assert bbox[1] < bbox[3]
