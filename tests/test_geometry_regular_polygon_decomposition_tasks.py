from __future__ import annotations

import math

import trace.tasks  # noqa: F401
from trace.tasks.registry import create_task


TASK_QUERIES = {
    "task_geometry__regular_polygon_decomposition__piece_area_value": (
        "single_wedge_area_from_total",
        "shaded_wedges_area_from_total",
        "wedge_area_from_side_and_apothem",
    ),
    "task_geometry__regular_polygon_decomposition__central_angle_value": (
        "single_wedge_central_angle",
        "marked_wedges_central_angle",
    ),
    "task_geometry__regular_polygon_decomposition__perimeter_value": (
        "perimeter_from_side_length",
        "perimeter_from_total_area_and_apothem",
    ),
    "task_geometry__regular_polygon_decomposition__side_length_value": (
        "side_length_from_perimeter",
        "side_length_from_total_area_and_apothem",
        "side_length_from_wedge_area_and_apothem",
    ),
}


def _generate(task_id: str, query_id: str, seed: int = 20260605):
    task = create_task(task_id)
    return task.generate(seed, params={"query_id": query_id}, max_attempts=3)


def test_regular_polygon_decomposition_tasks_are_registered() -> None:
    for task_id in TASK_QUERIES:
        assert create_task(task_id).task_id == task_id


def test_regular_polygon_decomposition_queries_emit_keyed_point_annotation() -> None:
    for task_id, query_ids in TASK_QUERIES.items():
        for index, query_id in enumerate(query_ids):
            output = _generate(task_id, query_id, seed=20260605 + index)
            assert output.scene_id == "regular_polygon_decomposition"
            assert output.query_id == query_id
            if task_id.endswith("__central_angle_value") or task_id.endswith("__perimeter_value") or task_id.endswith("__side_length_value"):
                assert output.answer_gt.type == "integer"
                assert isinstance(output.answer_gt.value, int)
            else:
                assert output.answer_gt.type == "number"
                assert isinstance(output.answer_gt.value, float)
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


def test_regular_polygon_decomposition_measurements_match_trace_values() -> None:
    for task_id, query_ids in TASK_QUERIES.items():
        for query_id in query_ids:
            output = _generate(task_id, query_id, seed=20260617)
            trace = output.trace_payload["execution_trace"]
            n_sides = int(trace["n_sides"])
            wedge_count = int(trace["wedge_count"])
            assert n_sides >= 5
            assert int(trace["central_angle_degrees"]) == int(round(360.0 / float(n_sides)))
            if query_id == "single_wedge_area_from_total":
                assert math.isclose(float(output.answer_gt.value), float(trace["total_area"]) / float(n_sides))
            elif query_id == "shaded_wedges_area_from_total":
                assert math.isclose(float(output.answer_gt.value), float(trace["wedge_area"]) * float(wedge_count))
            elif query_id == "wedge_area_from_side_and_apothem":
                assert output.answer_gt.value == round(float(trace["side_length"]) * float(trace["apothem"]) / 2.0 + 1e-9, 1)
            elif query_id in {"single_wedge_central_angle", "marked_wedges_central_angle"}:
                assert output.answer_gt.value == int(wedge_count * int(trace["central_angle_degrees"]))
            elif query_id == "perimeter_from_side_length":
                assert output.answer_gt.value == int(n_sides * float(trace["side_length"]))
            elif query_id == "perimeter_from_total_area_and_apothem":
                assert output.answer_gt.value == int(round((2.0 * float(trace["total_area"])) / float(trace["apothem"])))
            elif query_id == "side_length_from_perimeter":
                assert output.answer_gt.value == int(round(float(trace["perimeter"]) / float(n_sides)))
            elif query_id == "side_length_from_total_area_and_apothem":
                assert output.answer_gt.value == int(round((2.0 * float(trace["total_area"])) / (float(n_sides) * float(trace["apothem"]))))
            elif query_id == "side_length_from_wedge_area_and_apothem":
                assert output.answer_gt.value == int(round((2.0 * float(trace["wedge_area"])) / float(trace["apothem"])))
            else:
                raise AssertionError(f"unexpected query_id={query_id}")


def test_regular_polygon_decomposition_generation_is_deterministic() -> None:
    task_id = "task_geometry__regular_polygon_decomposition__piece_area_value"
    query_id = "wedge_area_from_side_and_apothem"
    first = _generate(task_id, query_id, seed=817)
    second = _generate(task_id, query_id, seed=817)
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
