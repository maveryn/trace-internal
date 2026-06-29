"""Contract tests for migrated voxel-cube puzzle tasks."""

from __future__ import annotations

from trace.tasks import create_task

TASK_IDS = (
    "task_puzzles__voxel_cube__cube_count",
    "task_puzzles__voxel_cube__cube_structure_change_count",
    "task_puzzles__voxel_cube__cube_painted_face_count",
    "task_puzzles__voxel_cube__cube_visible_projection_count",
    "task_puzzles__voxel_cube__cube_projection_match_label",
    "task_puzzles__voxel_cube__cube_projection_consistency_label",
)


def test_voxel_cube_tasks_generate_with_migrated_scene_contracts() -> None:
    for index, task_id in enumerate(TASK_IDS):
        output = create_task(task_id).generate(
            51100 + index,
            params={},
            max_attempts=80,
        )
        assert output.scene_id == "voxel_cube"
        assert output.query_id == "single"
        assert output.trace_payload["query_spec"]["params"]["scene_id"] == "voxel_cube"
        assert output.trace_payload["execution_trace"]["task_id"] == task_id


def test_voxel_cube_annotation_schemas_match_public_contracts() -> None:
    expected = {
        "task_puzzles__voxel_cube__cube_count": "bbox",
        "task_puzzles__voxel_cube__cube_structure_change_count": "bbox_set",
        "task_puzzles__voxel_cube__cube_painted_face_count": "bbox",
        "task_puzzles__voxel_cube__cube_visible_projection_count": "bbox_set",
        "task_puzzles__voxel_cube__cube_projection_match_label": "bbox",
        "task_puzzles__voxel_cube__cube_projection_consistency_label": "bbox",
    }
    for index, task_id in enumerate(TASK_IDS):
        output = create_task(task_id).generate(
            51200 + index,
            params={},
            max_attempts=80,
        )
        assert output.annotation_gt.type == expected[task_id]
        if output.annotation_gt.type == "bbox":
            assert len(output.annotation_gt.value) == 4
        if output.annotation_gt.type == "bbox_set":
            assert all(len(bbox) == 4 for bbox in output.annotation_gt.value)


def test_voxel_cube_semantic_axes_can_be_pinned() -> None:
    cases = [
        (
            "task_puzzles__voxel_cube__cube_structure_change_count",
            {"change_type": "missing_to_complete"},
            "missing_to_complete",
        ),
        (
            "task_puzzles__voxel_cube__cube_structure_change_count",
            {"change_type": "removed"},
            "removed",
        ),
        (
            "task_puzzles__voxel_cube__cube_painted_face_count",
            {"painted_query": "exterior_face_total"},
            "exterior_face_total",
        ),
        (
            "task_puzzles__voxel_cube__cube_painted_face_count",
            {"painted_query": "exact_k_faces_cube_count"},
            "exact_k_faces_cube_count",
        ),
        (
            "task_puzzles__voxel_cube__cube_visible_projection_count",
            {"view_direction": "top"},
            "top",
        ),
        (
            "task_puzzles__voxel_cube__cube_projection_match_label",
            {"view_direction": "front"},
            "front",
        ),
    ]
    for index, (task_id, params, expected_value) in enumerate(cases):
        output = create_task(task_id).generate(
            51300 + index,
            params=dict(params),
            max_attempts=100,
        )
        execution = output.trace_payload["execution_trace"]
        assert expected_value in {
            str(value) for key, value in execution.items() if key in params
        }
