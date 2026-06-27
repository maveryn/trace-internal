from __future__ import annotations

import re

import pytest

import trace.tasks  # noqa: F401
from trace.tasks.geometry.marked_polygon_equation.shared.construction import (
    isosceles_angle_from_expression,
    isosceles_base_angle_variable,
)
from trace.tasks.registry import create_task


TASK_QUERIES = {
    "task_geometry__similar_figure_measure_transfer__variable_value": (
        "single",
    ),
    "task_geometry__similar_figure_measure_transfer__side_length_from_expression_value": (
        "single",
    ),
    "task_geometry__marked_polygon_equation__side_variable_value": (
        "single",
    ),
    "task_geometry__marked_polygon_equation__angle_variable_value": (
        "single",
    ),
    "task_geometry__marked_polygon_equation__side_length_value": (
        "single",
    ),
    "task_geometry__marked_polygon_equation__angle_value": (
        "single",
    ),
    "task_geometry__marked_polygon_equation__polygon_angle_sum_variable_value": (
        "single",
    ),
    "task_geometry__marked_polygon_equation__polygon_angle_sum_angle_value": (
        "single",
    ),
    "task_geometry__parallel_segment_proportion__variable_value": (
        "single",
    ),
    "task_geometry__parallel_segment_proportion__segment_length_value": (
        "single",
    ),
}

MARKED_CONSTRUCTION_FAMILIES = {
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
    "task_geometry__marked_polygon_equation__polygon_angle_sum_variable_value": (
        "triangle_angle_sum_variable",
        "quadrilateral_angle_sum_variable",
    ),
    "task_geometry__marked_polygon_equation__polygon_angle_sum_angle_value": (
        "triangle_angle_sum_angle_measure",
        "quadrilateral_angle_sum_angle_measure",
    ),
}

PARALLEL_CONSTRUCTION_FAMILIES = (
    "triangle_side_splitter",
    "parallel_transversals",
)

PARALLEL_TASK_IDS = frozenset(
    {
        "task_geometry__parallel_segment_proportion__variable_value",
        "task_geometry__parallel_segment_proportion__segment_length_value",
    }
)

SIMILAR_CONSTRUCTION_FAMILIES = {
    "task_geometry__similar_figure_measure_transfer__variable_value": (
        "triangle_ratio",
        "polygon_ratio",
        "two_expression_ratio",
    ),
    "task_geometry__similar_figure_measure_transfer__side_length_from_expression_value": (
        "triangle_target_expression",
        "polygon_target_expression",
    ),
}

RETIRED_PARALLEL_QUERY_IDS = (
    "triangle_side_splitter_variable",
    "parallel_transversal_segment_variable",
    "triangle_side_splitter_segment_length",
    "parallel_transversal_segment_length",
)


def _eval_marked_angle_label(label: str, variable_name: str, variable_value: int) -> int:
    text = label.strip()
    if text.endswith("°"):
        text = text[:-1]
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    if variable_name not in text:
        return int(text)

    match = re.fullmatch(r"([+-]?\d*)%s([+-]\d+)?" % re.escape(variable_name), text)
    assert match is not None, text
    coefficient_text, offset_text = match.groups()
    if coefficient_text in ("", "+"):
        coefficient = 1
    elif coefficient_text == "-":
        coefficient = -1
    else:
        coefficient = int(coefficient_text)
    offset = int(offset_text or 0)
    return coefficient * int(variable_value) + offset


def _degree_value(label: str) -> int:
    assert label.endswith("°")
    return int(label[:-1])


def _generate(task_id: str, query_id: str, seed: int = 20260607, **extra_params):
    task = create_task(task_id)
    return task.generate(seed, params={"query_id": query_id, **extra_params}, max_attempts=3)


def test_geo3k_marked_equation_tasks_are_registered() -> None:
    for task_id in TASK_QUERIES:
        assert create_task(task_id).task_id == task_id


def test_geo3k_marked_equation_queries_emit_keyed_point_annotation() -> None:
    for task_id, query_ids in TASK_QUERIES.items():
        for index, query_id in enumerate(query_ids):
            output = _generate(task_id, query_id, seed=20260607 + index)
            assert output.query_id == query_id
            assert output.answer_gt.type == "number"
            assert isinstance(output.answer_gt.value, (int, float))

            if task_id in PARALLEL_TASK_IDS:
                assert output.annotation_gt.type == "segment_set"
                assert isinstance(output.annotation_gt.value, list)
                assert len(output.annotation_gt.value) == 4
                width, height = output.image.size
                for segment in output.annotation_gt.value:
                    assert isinstance(segment, list)
                    assert len(segment) == 2
                    for point in segment:
                        assert isinstance(point, list)
                        assert len(point) == 2
                        assert 0.0 <= float(point[0]) <= float(width)
                        assert 0.0 <= float(point[1]) <= float(height)
                trace = output.trace_payload
                assert trace["execution_trace"]["query_id"] == query_id
                assert trace["execution_trace"]["answer"] == output.answer_gt.value
                assert trace["projected_annotation"]["type"] == "segment_set"
                assert trace["projected_annotation"]["segment_set"] == output.annotation_gt.value
                assert trace["projected_annotation"]["pixel_segment_set"] == output.annotation_gt.value
                assert "task_variant" not in trace["query_spec"]["params"]
                assert "query_variant" not in trace["query_spec"]["params"]
                continue

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


def test_geo3k_marked_equation_queries_use_expected_scene_ids() -> None:
    assert _generate(
        "task_geometry__similar_figure_measure_transfer__variable_value",
        "single",
    ).scene_id == "similar_figure_measure_transfer"
    assert _generate(
        "task_geometry__marked_polygon_equation__side_variable_value",
        "single",
    ).scene_id == "marked_polygon_equation"
    assert _generate(
        "task_geometry__parallel_segment_proportion__variable_value",
        "single",
        construction_family="parallel_transversals",
    ).scene_id == "parallel_segment_proportion"


def test_geo3k_marked_equation_generation_is_deterministic() -> None:
    task_id = "task_geometry__parallel_segment_proportion__segment_length_value"
    first = _generate(task_id, "single", seed=817, construction_family="triangle_side_splitter")
    second = _generate(task_id, "single", seed=817, construction_family="triangle_side_splitter")
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]


def test_marked_polygon_equation_construction_families_are_trace_metadata() -> None:
    for task_id, families in MARKED_CONSTRUCTION_FAMILIES.items():
        for index, family in enumerate(families):
            output = _generate(
                task_id,
                "single",
                seed=20260617 + index,
                construction_family=family,
            )
            assert output.query_id == "single"
            trace = output.trace_payload
            assert trace["execution_trace"]["construction_family"] == family
            assert trace["query_spec"]["params"]["construction_family"] == family
            assert trace["query_spec"]["params"]["query_id"] == "single"
            assert "distractor_labels" in trace["execution_trace"]


def test_marked_polygon_isosceles_angle_labels_are_geometrically_consistent() -> None:
    for index in range(29):
        case = isosceles_base_angle_variable(index)
        base_a = _eval_marked_angle_label(case.labels["angle_a"], "x", case.answer)
        base_b = _eval_marked_angle_label(case.labels["angle_b"], "x", case.answer)
        apex = _degree_value(case.distractor_labels["angle_A"])
        assert base_a == base_b
        assert apex == 180 - (2 * base_a)
        assert 0 < apex < 180

    for index in range(18):
        case = isosceles_angle_from_expression(index)
        base_a = case.answer
        base_b = _eval_marked_angle_label(case.labels["angle_a"], "x", 4 + (index % 12))
        apex = _degree_value(case.distractor_labels["angle_A"])
        assert base_a == base_b
        assert apex == 180 - (2 * base_a)
        assert 0 < apex < 180


def test_similar_figure_equation_construction_families_are_trace_metadata() -> None:
    for task_id, families in SIMILAR_CONSTRUCTION_FAMILIES.items():
        for index, family in enumerate(families):
            output = _generate(
                task_id,
                "single",
                seed=20260616 + index,
                construction_family=family,
            )
            assert output.query_id == "single"
            trace = output.trace_payload
            assert trace["execution_trace"]["construction_family"] == family
            assert trace["query_spec"]["params"]["construction_family"] == family
            assert trace["query_spec"]["params"]["query_id"] == "single"


def test_parallel_segment_proportion_construction_families_are_trace_metadata() -> None:
    for task_id in sorted(PARALLEL_TASK_IDS):
        for index, family in enumerate(PARALLEL_CONSTRUCTION_FAMILIES):
            output = _generate(
                task_id,
                "single",
                seed=20260618 + index,
                construction_family=family,
            )
            assert output.query_id == "single"
            assert output.annotation_gt.type == "segment_set"
            trace = output.trace_payload
            assert trace["execution_trace"]["construction_family"] == family
            assert trace["query_spec"]["params"]["construction_family"] == family
            assert trace["query_spec"]["params"]["query_id"] == "single"


@pytest.mark.parametrize("retired_query_id", RETIRED_PARALLEL_QUERY_IDS)
def test_parallel_segment_proportion_rejects_retired_query_ids(retired_query_id: str) -> None:
    task = create_task("task_geometry__parallel_segment_proportion__variable_value")
    with pytest.raises(ValueError, match="unsupported query_id"):
        task.generate(20260619, params={"query_id": retired_query_id}, max_attempts=1)
