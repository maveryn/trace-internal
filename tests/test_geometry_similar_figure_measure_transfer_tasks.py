from __future__ import annotations

import trace.tasks  # noqa: F401
from trace.tasks.registry import create_task, list_task_ids


TASK_QUERIES = {
    "task_geometry__similar_figure_measure_transfer__corresponding_side_value": (
        "direct_side_transfer",
        "two_pair_side_transfer",
        "nested_side_transfer",
    ),
    "task_geometry__similar_figure_measure_transfer__scale_factor_value": (
        "scale_factor_from_side_pair",
        "scale_factor_from_perimeter_pair",
        "scale_factor_from_area_pair",
    ),
    "task_geometry__similar_figure_measure_transfer__area_scale_side_length_value": (
        "side_length_from_area_pair",
        "side_length_from_area_ratio",
        "side_length_from_area_and_known_side",
    ),
}


def _generate(task_id: str, query_id: str, seed: int = 20260605):
    task = create_task(task_id)
    return task.generate(seed, params={"query_id": query_id}, max_attempts=3)


def test_similar_figure_measure_transfer_tasks_are_registered() -> None:
    registered = set(list_task_ids())
    for task_id in TASK_QUERIES:
        assert task_id in registered


def test_similar_figure_measure_transfer_queries_emit_keyed_point_annotation() -> None:
    for task_id, query_ids in TASK_QUERIES.items():
        for index, query_id in enumerate(query_ids):
            output = _generate(task_id, query_id, seed=20260605 + index)
            assert output.scene_id == "similar_figure_measure_transfer"
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


def test_similar_figure_measure_transfer_measurements_match_trace_values() -> None:
    for task_id, query_ids in TASK_QUERIES.items():
        for query_id in query_ids:
            output = _generate(task_id, query_id, seed=20260617)
            trace = output.trace_payload["execution_trace"]
            scale_factor = int(trace["scale_factor"])
            if task_id == "task_geometry__similar_figure_measure_transfer__scale_factor_value":
                assert output.answer_gt.value == scale_factor
            else:
                assert output.answer_gt.value == int(trace["target_target_side_value"])
            source_side = trace["source_target_side_value"]
            target_side = trace["target_target_side_value"]
            if source_side is not None and target_side is not None:
                assert int(target_side) == int(source_side) * scale_factor
            source_area = trace["source_area"]
            target_area = trace["target_area"]
            if source_area is not None and target_area is not None:
                assert int(target_area) == int(source_area) * scale_factor * scale_factor


def test_similar_figure_measure_transfer_generation_is_deterministic() -> None:
    task_id = "task_geometry__similar_figure_measure_transfer__area_scale_side_length_value"
    query_id = "side_length_from_area_and_known_side"
    first = _generate(task_id, query_id, seed=817)
    second = _generate(task_id, query_id, seed=817)
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
