"""Contract tests for cube surface/net puzzle tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.spatial.cube_surface_net import (
    FACE_RELATION_QUERY_IDS,
    FACE_RELATION_TASK_ID,
    ROLLING_QUERY_IDS,
    ROLLING_RESULT_TASK_ID,
    SCENE_ID,
    PuzzlesSpatialCubeNetFaceRelationLabelTask,
    PuzzlesSpatialCubeRollingResultLabelTask,
)


def _assert_bbox_in_image(bbox: list[float], image_size: tuple[int, int]) -> None:
    assert len(bbox) == 4
    assert 0 <= float(bbox[0]) < float(bbox[2]) <= image_size[0]
    assert 0 <= float(bbox[1]) < float(bbox[3]) <= image_size[1]


def test_cube_surface_tasks_are_registered() -> None:
    assert TASK_REGISTRY[FACE_RELATION_TASK_ID] is PuzzlesSpatialCubeNetFaceRelationLabelTask
    assert TASK_REGISTRY[ROLLING_RESULT_TASK_ID] is PuzzlesSpatialCubeRollingResultLabelTask

    for task_cls in (PuzzlesSpatialCubeNetFaceRelationLabelTask, PuzzlesSpatialCubeRollingResultLabelTask):
        task = task_cls()
        assert task.domain == "puzzles"
        assert task.task_group == "spatial"


def test_cube_net_face_relation_contracts() -> None:
    task = PuzzlesSpatialCubeNetFaceRelationLabelTask()
    for index, query_id in enumerate(FACE_RELATION_QUERY_IDS):
        out = task.generate(2026052800 + index, params={"query_id": query_id}, max_attempts=50)
        trace = out.trace_payload
        execution = trace["execution_trace"]

        assert out.scene_id == SCENE_ID
        assert out.query_id == "default"
        assert out.query_id == query_id
        assert out.answer_gt.type == "option_letter"
        assert out.evidence_gt.type == "bbox_set"
        assert trace["query_spec"]["params"]["query_id"] == query_id
        assert trace["render_spec"]["scene_id"] == SCENE_ID
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]

        assert str(out.answer_gt.value) == str(execution["answer_value"])
        assert len(out.evidence_gt.value) == 2
        assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
        option_labels = {str(option["option_label"]) for option in execution["option_specs"]}
        assert str(out.answer_gt.value) in option_labels
        for bbox in out.evidence_gt.value:
            _assert_bbox_in_image(bbox, out.image.size)


def test_cube_rolling_result_contracts() -> None:
    task = PuzzlesSpatialCubeRollingResultLabelTask()
    for index, query_id in enumerate(ROLLING_QUERY_IDS):
        out = task.generate(2026052900 + index, params={"query_id": query_id}, max_attempts=50)
        trace = out.trace_payload
        execution = trace["execution_trace"]

        assert out.scene_id == SCENE_ID
        assert out.query_id == "default"
        assert out.query_id == query_id
        assert out.answer_gt.type == "option_letter"
        assert out.evidence_gt.type == "bbox_set"
        assert trace["query_spec"]["params"]["query_id"] == query_id
        assert trace["render_spec"]["scene_id"] == SCENE_ID
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]

        assert str(out.answer_gt.value) == str(execution["answer_value"])
        assert len(out.evidence_gt.value) == 3
        assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
        assert len(execution["path_cells"]) == len(execution["path_directions"]) + 1
        assert execution["correct_face"] == execution["final_orientation"][execution["target_slot"]]
        for bbox in out.evidence_gt.value:
            _assert_bbox_in_image(bbox, out.image.size)


def test_cube_surface_generation_is_deterministic() -> None:
    task = PuzzlesSpatialCubeRollingResultLabelTask()
    params = {"query_id": "final_right_face_label", "scene_variant": "paper_model"}
    out_a = task.generate(2026052999, params=params, max_attempts=50)
    out_b = task.generate(2026052999, params=params, max_attempts=50)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
