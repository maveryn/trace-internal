from __future__ import annotations

import trace.tasks  # noqa: F401
from trace.tasks.registry import create_task, list_task_ids


TASK_QUERIES = {
    "task_geometry__split_triangle_angle_chase__target_angle_value": (
        "single_cevian_triangle_angle_sum",
        "shared_vertex_split_angle_sum",
        "two_step_adjacent_triangle_angle_sum",
    ),
    "task_geometry__triangle_relations__angle_bisector_variable_value": (
        "split_segment_ratio_variable",
        "adjacent_side_ratio_variable",
    ),
    "task_geometry__split_triangle_trig_chain__side_length_value": (
        "shared_altitude_two_angles_side",
        "shared_altitude_side_then_hypotenuse",
        "isosceles_altitude_trig_side",
    ),
}


EXPECTED_SCENES = {
    "task_geometry__split_triangle_angle_chase__target_angle_value": "split_triangle_angle_chase",
    "task_geometry__triangle_relations__angle_bisector_variable_value": "triangle_relations",
    "task_geometry__split_triangle_trig_chain__side_length_value": "split_triangle_trig_chain",
}


def _generate(task_id: str, query_id: str, seed: int = 20260607):
    task = create_task(task_id)
    return task.generate(seed, params={"query_id": query_id}, max_attempts=5)


def test_split_triangle_pattern_tasks_are_registered() -> None:
    registered = set(list_task_ids())
    for task_id in TASK_QUERIES:
        assert task_id in registered


def test_split_triangle_pattern_queries_emit_keyed_point_annotation() -> None:
    for task_id, query_ids in TASK_QUERIES.items():
        for index, query_id in enumerate(query_ids):
            output = _generate(task_id, query_id, seed=20260607 + index)
            assert output.scene_id == EXPECTED_SCENES[task_id]
            assert output.query_id == query_id
            assert output.answer_gt.type in {"integer", "number"}
            assert isinstance(output.answer_gt.value, (int, float))
            assert output.annotation_gt.type == "keyed_point_map"
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
            assert trace["projected_annotation"]["type"] == "keyed_point_map"
            assert trace["projected_annotation"]["keyed_point_map"] == output.annotation_gt.value
            assert trace["projected_annotation"]["pixel_keyed_point_map"] == output.annotation_gt.value
            assert "task_variant" not in trace["query_spec"]["params"]
            assert "query_variant" not in trace["query_spec"]["params"]


def test_split_triangle_pattern_answers_match_trace_values() -> None:
    for task_id, query_ids in TASK_QUERIES.items():
        for query_id in query_ids:
            output = _generate(task_id, query_id, seed=20260617)
            trace = output.trace_payload["execution_trace"]
            values = trace["values"]
            assert output.answer_gt.value == trace["answer"]
            assert output.answer_gt.value == values["answer"]
            if task_id.endswith("__target_angle_value"):
                assert output.answer_gt.type == "integer"
                assert 0 < int(output.answer_gt.value) < 180
            elif task_id.endswith("__angle_bisector_variable_value"):
                assert output.answer_gt.type == "integer"
                assert int(output.answer_gt.value) > 0
            else:
                assert output.answer_gt.type == "number"
                assert float(output.answer_gt.value) > 0.0


def test_split_triangle_pattern_generation_is_deterministic() -> None:
    task_id = "task_geometry__split_triangle_angle_chase__target_angle_value"
    query_id = "two_step_adjacent_triangle_angle_sum"
    first = _generate(task_id, query_id, seed=817)
    second = _generate(task_id, query_id, seed=817)
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
