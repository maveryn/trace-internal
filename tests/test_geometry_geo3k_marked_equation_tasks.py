from __future__ import annotations

import trace.tasks  # noqa: F401
from trace.tasks.registry import create_task, list_task_ids


TASK_QUERIES = {
    "task_geometry__similar_figure_measure_transfer__variable_value": (
        "similar_triangles_side_ratio_variable",
        "similar_polygons_side_ratio_variable",
        "two_expression_side_ratio_variable",
    ),
    "task_geometry__similar_figure_measure_transfer__side_length_from_expression_value": (
        "similar_triangles_target_side_from_expression",
        "similar_polygons_target_side_from_expression",
    ),
    "task_geometry__marked_polygon_equation__side_variable_value": (
        "isosceles_triangle_equal_side_variable",
        "equilateral_triangle_equal_side_variable",
        "marked_polygon_equal_side_variable",
        "isosceles_altitude_base_split_variable",
    ),
    "task_geometry__marked_polygon_equation__angle_variable_value": (
        "marked_equal_angles_variable",
        "isosceles_triangle_base_angle_variable",
        "equilateral_median_right_angle_variable",
    ),
    "task_geometry__marked_polygon_equation__side_length_value": (
        "isosceles_triangle_side_from_expression",
        "equilateral_triangle_side_from_expression",
        "marked_polygon_side_from_expression",
        "equilateral_median_side_length_from_expression",
    ),
    "task_geometry__marked_polygon_equation__angle_value": (
        "marked_equal_angle_from_expression",
        "isosceles_triangle_angle_from_expression",
    ),
    "task_geometry__parallel_segment_proportion__variable_value": (
        "triangle_side_splitter_variable",
        "parallel_transversal_segment_variable",
    ),
    "task_geometry__parallel_segment_proportion__segment_length_value": (
        "triangle_side_splitter_segment_length",
        "parallel_transversal_segment_length",
    ),
}


def _generate(task_id: str, query_id: str, seed: int = 20260607):
    task = create_task(task_id)
    return task.generate(seed, params={"query_id": query_id}, max_attempts=3)


def test_geo3k_marked_equation_tasks_are_registered() -> None:
    registered = set(list_task_ids())
    for task_id in TASK_QUERIES:
        assert task_id in registered


def test_geo3k_marked_equation_queries_emit_keyed_point_annotation() -> None:
    for task_id, query_ids in TASK_QUERIES.items():
        for index, query_id in enumerate(query_ids):
            output = _generate(task_id, query_id, seed=20260607 + index)
            assert output.query_id == query_id
            assert output.answer_gt.type == "number"
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


def test_geo3k_marked_equation_queries_use_expected_scene_ids() -> None:
    assert _generate(
        "task_geometry__similar_figure_measure_transfer__variable_value",
        "similar_triangles_side_ratio_variable",
    ).scene_id == "similar_figure_measure_transfer"
    assert _generate(
        "task_geometry__marked_polygon_equation__side_variable_value",
        "marked_polygon_equal_side_variable",
    ).scene_id == "marked_polygon_equation"
    assert _generate(
        "task_geometry__parallel_segment_proportion__variable_value",
        "parallel_transversal_segment_variable",
    ).scene_id == "parallel_segment_proportion"


def test_geo3k_marked_equation_generation_is_deterministic() -> None:
    task_id = "task_geometry__parallel_segment_proportion__segment_length_value"
    query_id = "triangle_side_splitter_segment_length"
    first = _generate(task_id, query_id, seed=817)
    second = _generate(task_id, query_id, seed=817)
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
