from __future__ import annotations

import trace.tasks  # noqa: F401
from trace.tasks.registry import create_task, list_task_ids


TASK_QUERIES = {
    "task_geometry__triangle_congruence_correspondence__corresponding_side_value": (
        "tick_mark_side_transfer",
        "congruence_statement_side_transfer",
        "overlapping_triangle_side_transfer",
    ),
    "task_geometry__triangle_congruence_correspondence__corresponding_angle_value": (
        "angle_mark_transfer",
        "congruence_statement_angle_transfer",
        "overlapping_triangle_angle_transfer",
    ),
    "task_geometry__triangle_congruence_correspondence__algebraic_side_value": (
        "single_expression_equal_sides",
        "two_expression_equal_sides",
        "shared_side_congruence_expression",
    ),
}


def _generate(task_id: str, query_id: str, seed: int = 20260605):
    task = create_task(task_id)
    return task.generate(seed, params={"query_id": query_id}, max_attempts=3)


def test_triangle_congruence_correspondence_tasks_are_registered() -> None:
    registered = set(list_task_ids())
    for task_id in TASK_QUERIES:
        assert task_id in registered


def test_triangle_congruence_correspondence_queries_emit_keyed_point_annotation() -> None:
    for task_id, query_ids in TASK_QUERIES.items():
        for index, query_id in enumerate(query_ids):
            output = _generate(task_id, query_id, seed=20260605 + index)
            assert output.scene_id == "triangle_congruence_correspondence"
            assert output.query_id == query_id
            assert output.answer_gt.type == "integer"
            assert isinstance(output.answer_gt.value, int)
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


def test_triangle_congruence_correspondence_measurements_match_trace_values() -> None:
    for task_id, query_ids in TASK_QUERIES.items():
        for query_id in query_ids:
            output = _generate(task_id, query_id, seed=20260617)
            trace = output.trace_payload["execution_trace"]
            if task_id == "task_geometry__triangle_congruence_correspondence__corresponding_angle_value":
                assert output.answer_gt.value == int(trace["target_angle_value"])
                assert int(trace["source_angle_value"]) == int(trace["target_angle_value"])
            else:
                assert output.answer_gt.value == int(trace["target_target_side_value"])
                assert int(trace["source_target_side_value"]) == int(trace["target_target_side_value"])
            if task_id == "task_geometry__triangle_congruence_correspondence__algebraic_side_value":
                assert int(trace["x_value"]) > 0
                assert trace["source_target_expression"]
                assert trace["source_support_expression"]
                assert trace["target_support_expression"]


def test_triangle_congruence_correspondence_generation_is_deterministic() -> None:
    task_id = "task_geometry__triangle_congruence_correspondence__algebraic_side_value"
    query_id = "shared_side_congruence_expression"
    first = _generate(task_id, query_id, seed=817)
    second = _generate(task_id, query_id, seed=817)
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
