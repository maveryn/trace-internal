"""Contract tests for tangram-style puzzle tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.spatial.tangram_assembly import (
    PuzzlesSpatialTangramContactCountTask,
    PuzzlesSpatialTangramMissingPieceLabelTask,
)


TASKS = (
    ("task_puzzles__tangram__tangram_missing_piece_label", PuzzlesSpatialTangramMissingPieceLabelTask, "missing_piece_label"),
    ("task_puzzles__tangram__tangram_contact_count", PuzzlesSpatialTangramContactCountTask, "contact_count"),
)


def test_tangram_tasks_are_registered() -> None:
    for task_id, task_cls, _query_id in TASKS:
        assert TASK_REGISTRY[task_id] is task_cls
        task = task_cls()
        assert task.domain == "puzzles"
        assert task.task_group == "spatial"


def test_tangram_tasks_emit_public_contracts() -> None:
    for index, (task_id, task_cls, query_id) in enumerate(TASKS):
        out = task_cls().generate(2026052100 + index, params={}, max_attempts=20)
        trace = out.trace_payload
        execution = trace["execution_trace"]

        assert out.scene_id == "tangram"
        assert out.query_id == query_id
        assert execution["query_id"] == query_id
        assert trace["query_spec"]["query_id"] == query_id
        assert trace["render_spec"]["scene_id"] == "tangram"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
        assert out.annotation_gt.type == "bbox_set"
        assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
        assert out.image.size == (
            int(trace["render_spec"]["canvas_width"]),
            int(trace["render_spec"]["canvas_height"]),
        )

        for bbox in out.annotation_gt.value:
            assert len(bbox) == 4
            assert 0 <= float(bbox[0]) < float(bbox[2]) <= out.image.size[0]
            assert 0 <= float(bbox[1]) < float(bbox[3]) <= out.image.size[1]

        if query_id == "contact_count":
            assert out.answer_gt.type == "integer"
            assert int(out.answer_gt.value) == int(execution["contact_count"])
            assert len(out.annotation_gt.value) == int(out.answer_gt.value)
        else:
            assert out.answer_gt.type == "option_letter"
            assert str(out.answer_gt.value) == str(execution["answer_value"])
            assert len(out.annotation_gt.value) == 2
            assert 4 <= int(execution["option_count"]) <= 6, task_id


def test_tangram_generation_is_deterministic() -> None:
    task = PuzzlesSpatialTangramMissingPieceLabelTask()
    params = {"scene_variant": "tangram_diamond"}
    out_a = task.generate(2026052199, params=params, max_attempts=20)
    out_b = task.generate(2026052199, params=params, max_attempts=20)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_tangram_notched_targets_do_not_use_mirror_distractors() -> None:
    mirror_shape = {
        "left_notched_piece": "right_notched_piece",
        "right_notched_piece": "left_notched_piece",
    }

    for target_shape_id, mirror_shape_id in mirror_shape.items():
        out = PuzzlesSpatialTangramMissingPieceLabelTask().generate(
            2026052200,
            params={"target_piece_id": "piece_6" if target_shape_id == "left_notched_piece" else "piece_7"},
            max_attempts=20,
        )
        execution = out.trace_payload["execution_trace"]
        assert execution["target_shape_id"] == target_shape_id
        option_shape_ids = {str(option["shape_id"]) for option in execution["option_specs"]}
        assert target_shape_id in option_shape_ids
        assert mirror_shape_id not in option_shape_ids
