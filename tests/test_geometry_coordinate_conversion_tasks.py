"""Tests for geometry coordinate-conversion tasks."""

from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

from trace.tasks import create_task
from trace.tasks.geometry.coordinate_conversion.cartesian_component_value import (
    QUERY_IDS as CARTESIAN_QUERY_IDS,
    TASK_ID as CARTESIAN_TASK_ID,
)
from trace.tasks.geometry.coordinate_conversion.polar_component_value import (
    QUERY_IDS as POLAR_QUERY_IDS,
    TASK_ID as POLAR_TASK_ID,
)
from trace.tasks.geometry.coordinate_conversion.shared.sampling import (
    cartesian_abs_max,
    canonical_number_key,
    polar_angle_step,
    polar_radius_bounds,
    rounded_decimal,
    select_cartesian_point_case,
    select_polar_point_case,
)


def _generate(task_id: str, query_id: str, seed: int = 17):
    task = create_task(task_id)
    return task.generate(seed, params={"query_id": query_id}, max_attempts=1)


@pytest.mark.parametrize("query_id", POLAR_QUERY_IDS)
def test_polar_component_task_formula_and_point_annotation(query_id: str) -> None:
    output = _generate(POLAR_TASK_ID, query_id)
    trace = output.trace_payload["execution_trace"]
    expected_radius = rounded_decimal(math.hypot(float(trace["x"]), float(trace["y"])))
    expected_angle = rounded_decimal(math.degrees(math.atan2(float(trace["y"]), float(trace["x"]))) % 360.0)
    expected = expected_radius if query_id == "radius_from_cartesian_point" else expected_angle

    assert output.answer_gt.type == "number"
    assert float(output.answer_gt.value) == pytest.approx(expected)
    assert output.annotation_gt.type == "point"
    assert output.annotation_gt.value == output.trace_payload["render_map"]["point_p_px"]
    assert output.trace_payload["render_spec"]["ray_op_visible"] is False


@pytest.mark.parametrize("query_id", CARTESIAN_QUERY_IDS)
def test_cartesian_component_task_formula_and_segment_annotation(query_id: str) -> None:
    output = _generate(CARTESIAN_TASK_ID, query_id)
    trace = output.trace_payload["execution_trace"]
    theta = math.radians(float(trace["theta_degrees"]))
    expected_x = rounded_decimal(float(trace["radius"]) * math.cos(theta))
    expected_y = rounded_decimal(float(trace["radius"]) * math.sin(theta))
    expected = expected_x if query_id == "x_from_polar_point" else expected_y

    assert output.answer_gt.type == "number"
    assert float(output.answer_gt.value) == pytest.approx(expected)
    assert output.annotation_gt.type == "segment"
    assert output.annotation_gt.value == output.trace_payload["render_map"]["ray_op_px"]
    assert output.trace_payload["render_spec"]["ray_op_visible"] is True


def test_coordinate_conversion_answer_supports_are_large() -> None:
    defaults = {
        "cartesian_abs_max": 12,
        "polar_radius_min": 12,
        "polar_radius_max": 80,
        "polar_angle_step_degrees": 30,
    }
    polar_radius = select_cartesian_point_case(
        component="radius",
        instance_seed=1,
        params={},
        generation_defaults=defaults,
    )
    polar_angle = select_cartesian_point_case(
        component="angle",
        instance_seed=1,
        params={},
        generation_defaults=defaults,
    )
    cartesian_x = select_polar_point_case(
        component="x",
        instance_seed=1,
        params={},
        generation_defaults=defaults,
    )
    cartesian_y = select_polar_point_case(
        component="y",
        instance_seed=1,
        params={},
        generation_defaults=defaults,
    )

    assert polar_radius.answer_support_count >= 50
    assert polar_angle.answer_support_count >= 50
    assert cartesian_x.answer_support_count >= 50
    assert cartesian_y.answer_support_count >= 50
    assert canonical_number_key(polar_radius.selected_answer) in polar_radius.answer_candidate_probabilities


def test_coordinate_conversion_generation_is_deterministic() -> None:
    first = _generate(POLAR_TASK_ID, "angle_from_cartesian_point", seed=91)
    second = _generate(POLAR_TASK_ID, "angle_from_cartesian_point", seed=91)

    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]


def test_coordinate_conversion_invalid_query_id_raises() -> None:
    task = create_task(POLAR_TASK_ID)
    with pytest.raises(ValueError):
        task.generate(3, params={"query_id": "not_a_query"}, max_attempts=1)


def test_coordinate_conversion_config_has_no_query_routing() -> None:
    config_path = Path("configs/domains/geometry/coordinate_conversion.yaml")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert "query_id_weights" not in str(config)
    assert "query_variant" not in str(config)
    assert cartesian_abs_max({}, config["generation"]["shared"]) == 12
    assert polar_radius_bounds({}, config["generation"]["shared"]) == (12, 80)
    assert polar_angle_step({}, config["generation"]["shared"]) == 30
