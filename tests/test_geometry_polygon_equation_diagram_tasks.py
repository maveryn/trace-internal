"""Regression tests for polygon equation diagram geometry tasks."""

from __future__ import annotations

import json

import pytest

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks import create_task


TASK_IDS = (
    "task_geometry__polygon_equation_diagram__equal_side_variable_value",
    "task_geometry__polygon_equation_diagram__equal_side_length_value",
    "task_geometry__polygon_equation_diagram__equal_angle_variable_value",
    "task_geometry__polygon_equation_diagram__equal_angle_measure_value",
    "task_geometry__polygon_equation_diagram__interior_angle_sum_variable_value",
    "task_geometry__polygon_equation_diagram__interior_angle_sum_angle_value",
)


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_polygon_equation_diagram_registered_task(task_id: str) -> None:
    assert create_task(task_id).task_id == task_id


@pytest.mark.parametrize("task_id", TASK_IDS)
@pytest.mark.parametrize("side_count", [3, 4, 5, 6])
def test_polygon_equation_diagram_generates_each_side_count(task_id: str, side_count: int) -> None:
    out = create_task(task_id).generate(
        20260627 + side_count,
        params={"side_count": side_count},
        max_attempts=40,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == "polygon_equation_diagram"
    assert out.query_id == SINGLE_QUERY_ID
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == execution["answer"]
    assert execution["side_count"] == side_count
    assert execution["formula_schema"]
    assert execution["relation"]

    assert out.annotation_gt.type == "point_map"
    annotation = out.annotation_gt.value
    expected_keys = {chr(ord("A") + index) for index in range(side_count)}
    assert set(annotation) == expected_keys
    width, height = out.image.size
    for point in annotation.values():
        assert 0 <= point[0] <= width
        assert 0 <= point[1] <= height

    if "interior_angle_sum" in task_id:
        assert sum(execution["numeric_angle_values"]) == (side_count - 2) * 180
    label_blob = json.dumps(
        {
            "side_labels": execution.get("side_labels", {}),
            "angle_labels": execution.get("angle_labels", {}),
        }
    )
    assert "1x" not in label_blob
    assert "task_variant" not in json.dumps(trace)
    assert "query_variant" not in json.dumps(trace)


def test_polygon_equation_diagram_generation_is_deterministic() -> None:
    task_id = "task_geometry__polygon_equation_diagram__interior_angle_sum_variable_value"
    params = {"side_count": 6}
    first = create_task(task_id).generate(123456, params=params, max_attempts=40)
    second = create_task(task_id).generate(123456, params=params, max_attempts=40)

    assert first.prompt == second.prompt
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
