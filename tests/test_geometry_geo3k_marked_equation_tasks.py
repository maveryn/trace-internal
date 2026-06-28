from __future__ import annotations

import pytest

import trace.tasks  # noqa: F401
from trace.tasks.registry import create_task


TASK_QUERIES = {
    "task_geometry__similar_figure_measure_transfer__variable_value": (
        "single",
    ),
    "task_geometry__similar_figure_measure_transfer__side_length_from_expression_value": (
        "single",
    ),
    "task_geometry__parallel_segment_proportion__variable_value": (
        "single",
    ),
    "task_geometry__parallel_segment_proportion__segment_length_value": (
        "single",
    ),
}

PARALLEL_CONSTRUCTION_FAMILIES = (
    "triangle_side_splitter",
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
                assert output.annotation_gt.type == "point_map"
                assert isinstance(output.annotation_gt.value, dict)
                assert set(output.annotation_gt.value) == {"A", "B", "C", "D", "E"}
                width, height = output.image.size
                for point in output.annotation_gt.value.values():
                    assert isinstance(point, list)
                    assert len(point) == 2
                    assert 0.0 <= float(point[0]) <= float(width)
                    assert 0.0 <= float(point[1]) <= float(height)
                trace = output.trace_payload
                assert trace["execution_trace"]["query_id"] == query_id
                assert trace["execution_trace"]["answer"] == output.answer_gt.value
                assert trace["execution_trace"]["construction_family"] == "triangle_side_splitter"
                assert trace["query_spec"]["params"]["construction_family"] == "triangle_side_splitter"
                assert trace["projected_annotation"]["type"] == "point_map"
                assert trace["projected_annotation"]["point_map"] == output.annotation_gt.value
                assert trace["projected_annotation"]["pixel_point_map"] == output.annotation_gt.value
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
        "task_geometry__parallel_segment_proportion__variable_value",
        "single",
    ).scene_id == "parallel_segment_proportion"


def test_geo3k_marked_equation_generation_is_deterministic() -> None:
    task_id = "task_geometry__parallel_segment_proportion__segment_length_value"
    first = _generate(task_id, "single", seed=817, construction_family="triangle_side_splitter")
    second = _generate(task_id, "single", seed=817, construction_family="triangle_side_splitter")
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]


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
            assert output.annotation_gt.type == "point_map"
            assert set(output.annotation_gt.value) == {"A", "B", "C", "D", "E"}
            trace = output.trace_payload
            assert trace["execution_trace"]["construction_family"] == family
            assert trace["query_spec"]["params"]["construction_family"] == family
            assert trace["query_spec"]["params"]["query_id"] == "single"


def test_parallel_segment_proportion_rejects_retired_transversal_family() -> None:
    task = create_task("task_geometry__parallel_segment_proportion__variable_value")
    with pytest.raises(ValueError, match="unsupported construction_family"):
        task.generate(
            20260620,
            params={"query_id": "single", "construction_family": "parallel_transversals"},
            max_attempts=1,
        )


@pytest.mark.parametrize("retired_query_id", RETIRED_PARALLEL_QUERY_IDS)
def test_parallel_segment_proportion_rejects_retired_query_ids(retired_query_id: str) -> None:
    task = create_task("task_geometry__parallel_segment_proportion__variable_value")
    with pytest.raises(ValueError, match="unsupported query_id"):
        task.generate(20260619, params={"query_id": retired_query_id}, max_attempts=1)
