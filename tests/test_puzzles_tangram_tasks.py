"""Contract tests for Tangram puzzle scene-package tasks."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.tangram.contact_count import PuzzlesTangramContactCountTask
from trace.tasks.puzzles.tangram.missing_piece_label import (
    PuzzlesTangramMissingPieceLabelTask,
)

TASKS = (
    (
        "task_puzzles__tangram__contact_count",
        PuzzlesTangramContactCountTask,
        "bbox_set",
    ),
    (
        "task_puzzles__tangram__missing_piece_label",
        PuzzlesTangramMissingPieceLabelTask,
        "bbox_map",
    ),
)


def test_tangram_tasks_are_registered() -> None:
    """Public clean task ids should register to scene-package classes."""

    for task_id, task_cls, _annotation_type in TASKS:
        assert TASK_REGISTRY[task_id] is task_cls
        task = task_cls()
        assert task.domain == "puzzles"
        assert task.supported_query_ids == (SINGLE_QUERY_ID,)


def test_tangram_tasks_emit_public_contracts() -> None:
    """Generated outputs should match public answer and annotation contracts."""

    for index, (_task_id, task_cls, expected_annotation_type) in enumerate(TASKS):
        out = task_cls().generate(2026052100 + index, params={}, max_attempts=20)
        trace = out.trace_payload
        execution = trace["execution_trace"]

        assert out.scene_id == "tangram"
        assert out.query_id == SINGLE_QUERY_ID
        assert execution["query_id"] == SINGLE_QUERY_ID
        assert trace["query_spec"]["query_id"] == SINGLE_QUERY_ID
        assert trace["render_spec"]["scene_id"] == "tangram"
        assert sorted(out.prompt_variants.keys()) == [
            "answer_and_annotation",
            "answer_only",
        ]
        assert out.annotation_gt.type == expected_annotation_type
        assert out.image.size == (
            int(trace["render_spec"]["canvas_width"]),
            int(trace["render_spec"]["canvas_height"]),
        )

        if expected_annotation_type == "bbox_set":
            assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
            assert out.answer_gt.type == "integer"
            assert int(out.answer_gt.value) == int(execution["contact_count"])
            assert len(out.annotation_gt.value) == int(out.answer_gt.value)
            for bbox in out.annotation_gt.value:
                _assert_bbox_in_image(bbox, out.image.size)
        else:
            assert trace["projected_annotation"]["bbox_map"] == out.annotation_gt.value
            assert out.answer_gt.type == "option_letter"
            assert str(out.answer_gt.value) == str(execution["answer_option_label"])
            assert sorted(out.annotation_gt.value.keys()) == [
                "missing_region",
                "selected_option",
            ]
            assert 4 <= int(execution["option_count"]) <= 6
            for bbox in out.annotation_gt.value.values():
                _assert_bbox_in_image(bbox, out.image.size)


def test_tangram_generation_is_deterministic() -> None:
    """Same seed and params should produce identical output artifacts."""

    task = PuzzlesTangramMissingPieceLabelTask()
    params = {"scene_variant": "tangram_diamond"}
    out_a = task.generate(2026052199, params=params, max_attempts=20)
    out_b = task.generate(2026052199, params=params, max_attempts=20)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert (
        out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    )
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_tangram_notched_targets_do_not_use_mirror_distractors() -> None:
    """Asymmetric notched missing pieces must not include mirror distractors."""

    mirror_shape = {
        "left_notched_piece": "right_notched_piece",
        "right_notched_piece": "left_notched_piece",
    }
    for target_shape_id, mirror_shape_id in mirror_shape.items():
        target_piece_id = (
            "piece_6" if target_shape_id == "left_notched_piece" else "piece_7"
        )
        out = PuzzlesTangramMissingPieceLabelTask().generate(
            2026052200,
            params={"target_piece_id": target_piece_id},
            max_attempts=20,
        )
        execution = out.trace_payload["execution_trace"]
        assert execution["target_shape_id"] == target_shape_id
        option_shape_ids = {
            str(option["shape_id"]) for option in execution["option_specs"]
        }
        assert target_shape_id in option_shape_ids
        assert mirror_shape_id not in option_shape_ids


def _assert_bbox_in_image(bbox, image_size: tuple[int, int]) -> None:
    """Assert one bbox is non-empty and within the image."""

    assert len(bbox) == 4
    assert 0 <= float(bbox[0]) < float(bbox[2]) <= image_size[0]
    assert 0 <= float(bbox[1]) < float(bbox[3]) <= image_size[1]
