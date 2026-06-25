from __future__ import annotations

import trace.tasks  # noqa: F401
from trace.tasks.registry import create_task


TASK_QUERIES = {
    "task_geometry__right_triangle_altitude_theorem__altitude_to_hypotenuse_value": (
        "altitude_from_split_hypotenuse",
        "missing_projection_from_altitude",
    ),
    "task_geometry__right_triangle_altitude_theorem__leg_projection_length_value": (
        "leg_from_hypotenuse_projection",
        "projection_from_leg_and_hypotenuse",
    ),
}


def _generate(task_id: str, query_id: str, seed: int = 20260605):
    task = create_task(task_id)
    return task.generate(seed, params={"query_id": query_id}, max_attempts=3)


def test_right_triangle_altitude_theorem_tasks_are_registered() -> None:
    for task_id in TASK_QUERIES:
        assert create_task(task_id).task_id == task_id


def test_right_triangle_altitude_theorem_queries_emit_keyed_point_annotation() -> None:
    for task_id, query_ids in TASK_QUERIES.items():
        for index, query_id in enumerate(query_ids):
            output = _generate(task_id, query_id, seed=20260605 + index)
            assert output.scene_id == "right_triangle_altitude_theorem"
            assert output.query_id == query_id
            assert output.answer_gt.type == "integer"
            assert isinstance(output.answer_gt.value, int)
            assert output.annotation_gt.type == "point_map"
            assert isinstance(output.annotation_gt.value, dict)
            assert output.annotation_gt.value
            width, height = output.image.size
            for point in output.annotation_gt.value.values():
                assert isinstance(point, list)
                assert len(point) == 2
                assert 0.0 <= float(point[0]) <= float(width)
                assert 0.0 <= float(point[1]) <= float(height)
            trace = output.trace_payload
            assert trace["execution_trace"]["query_id"] == query_id
            assert trace["execution_trace"]["answer"] == output.answer_gt.value
            assert trace["projected_annotation"]["type"] == "point_map"
            assert trace["projected_annotation"]["point_map"] == output.annotation_gt.value
            assert trace["projected_annotation"]["pixel_point_map"] == output.annotation_gt.value
            assert "task_variant" not in trace["query_spec"]["params"]
            assert "query_variant" not in trace["query_spec"]["params"]


def test_right_triangle_altitude_theorem_measurements_match_trace_values() -> None:
    for task_id, query_ids in TASK_QUERIES.items():
        for query_id in query_ids:
            output = _generate(task_id, query_id, seed=20260617)
            trace = output.trace_payload["execution_trace"]
            left_projection = int(trace["left_projection"])
            right_projection = int(trace["right_projection"])
            altitude = int(trace["altitude"])
            hypotenuse = int(trace["hypotenuse"])
            assert left_projection + right_projection == hypotenuse
            assert altitude * altitude == left_projection * right_projection
            if trace["left_leg"] is not None:
                assert int(trace["left_leg"]) ** 2 == hypotenuse * left_projection
            if trace["right_leg"] is not None:
                assert int(trace["right_leg"]) ** 2 == hypotenuse * right_projection
            target_role = str(trace["target_role"])
            if target_role == "altitude":
                assert output.answer_gt.value == altitude
            elif target_role == "left_projection":
                assert output.answer_gt.value == left_projection
            elif target_role == "right_projection":
                assert output.answer_gt.value == right_projection
            elif target_role == "left_leg":
                assert output.answer_gt.value == int(trace["left_leg"])
            elif target_role == "right_leg":
                assert output.answer_gt.value == int(trace["right_leg"])
            else:
                raise AssertionError(f"unexpected target_role={target_role}")


def test_right_triangle_altitude_theorem_generation_is_deterministic() -> None:
    task_id = "task_geometry__right_triangle_altitude_theorem__leg_projection_length_value"
    query_id = "projection_from_leg_and_hypotenuse"
    first = _generate(task_id, query_id, seed=817)
    second = _generate(task_id, query_id, seed=817)
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
