from __future__ import annotations

from trace.tasks.registry import create_task

LENGTH_KEYS = {"measure_start", "measure_end", "ruler_start_tick", "ruler_end_tick"}
ANGLE_KEYS = {"angle_vertex", "baseline_ray_point", "target_ray_point", "protractor_reading_tick"}

TASK_EXPECTATIONS = {
    "task_geometry__measuring_tools__shape_length_value_polygon_side_ruler_reading": {
        "keys": LENGTH_KEYS,
        "tool_kind": "ruler",
        "measurement_kind": "polygon_side_ruler_reading",
    },
    "task_geometry__measuring_tools__shape_length_value_circle_radius_ruler_reading": {
        "keys": LENGTH_KEYS,
        "tool_kind": "ruler",
        "measurement_kind": "circle_radius_ruler_reading",
    },
    "task_geometry__measuring_tools__shape_angle_value_triangle_vertex_protractor_reading": {
        "keys": ANGLE_KEYS,
        "tool_kind": "protractor",
        "measurement_kind": "triangle_vertex_protractor_reading",
    },
    "task_geometry__measuring_tools__shape_angle_value_quadrilateral_vertex_protractor_reading": {
        "keys": ANGLE_KEYS,
        "tool_kind": "protractor",
        "measurement_kind": "quadrilateral_vertex_protractor_reading",
    },
}


def test_measuring_tools_tasks_use_single_query_integer_answers_and_point_maps() -> None:
    for index, (task_id, expected) in enumerate(TASK_EXPECTATIONS.items()):
        out = create_task(task_id).generate(
            instance_seed=2026062300 + index,
            params={},
            max_attempts=50,
        )

        assert out.query_id == "single"
        assert out.answer_gt.type == "integer"
        assert isinstance(out.answer_gt.value, int)
        assert out.annotation_gt.type == "point_map"
        assert set(out.annotation_gt.value) == expected["keys"]

        projected = out.trace_payload["projected_annotation"]
        assert projected["type"] == "point_map"
        assert projected["point_map"] == out.annotation_gt.value
        assert projected["pixel_point_map"] == out.annotation_gt.value

        query_spec = out.trace_payload["query_spec"]
        assert query_spec["query_id"] == "single"
        assert query_spec["params"]["query_id"] == "single"
        assert query_spec["params"]["tool_kind"] == expected["tool_kind"]
        assert query_spec["params"]["measurement_kind"] == expected["measurement_kind"]
        assert query_spec["prompt_variant"]["prompt_schema_version"] == "v1"


def test_measuring_tools_tasks_validate_query_id_params() -> None:
    task = create_task("task_geometry__measuring_tools__shape_length_value_polygon_side_ruler_reading")
    assert task.generate(instance_seed=17, params={"query_id": "single"}, max_attempts=50).query_id == "single"
    assert task.generate(instance_seed=17, params={"query_variant": "single"}, max_attempts=50).query_id == "single"

    try:
        task.generate(instance_seed=17, params={"query_id": "unsupported"}, max_attempts=50)
    except ValueError as exc:
        assert "query_id" in str(exc)
    else:  # pragma: no cover - assertion path
        raise AssertionError("unsupported query_id should fail")
