"""Behavior tests for consolidated geometry task surfaces."""

from __future__ import annotations

from collections import Counter

import pytest

from trace.core.seed import hash64
from trace.tasks.geometry.analytical_2d.value import GeometryAnalytical2DValueTask
from trace.tasks.geometry.analytical_3d.value import GeometryAnalytical3DValueTask
from trace.tasks.geometry.comparison.value import GeometryComparisonValueTask
from trace.tasks.geometry.counting.value import GeometryCountingValueTask
from trace.tasks.geometry.measurement.value import GeometryMeasurementValueTask
from trace.tasks.geometry.transformation.match import GeometryTransformationMatchTask, _resolve_axes
from trace.tasks import TASK_REGISTRY


EXPECTED_GEOMETRY_TASKS = {
    "task_geometry_measurement_value",
    "task_geometry_comparison_value",
    "task_geometry_counting_value",
    "task_geometry_analytical_2d_value",
    "task_geometry_analytical_3d_value",
    "task_geometry_transformation_match",
}


def test_geometry_registry_includes_consolidated_value_tasks_plus_transformation() -> None:
    geometry_tasks = {task_id for task_id in TASK_REGISTRY if task_id.startswith("task_geometry_")}
    assert geometry_tasks == EXPECTED_GEOMETRY_TASKS


@pytest.mark.parametrize(
    ("scene_variant", "query_variant"),
    (
        ("angle", "angle"),
        ("line", "slope"),
        ("circle", "perimeter"),
        ("ellipse", "area"),
    ),
)
def test_geometry_measurement_value_tracks_scene_and_query_variants(scene_variant: str, query_variant: str) -> None:
    task = GeometryMeasurementValueTask()
    out = task.generate(23001, params={"scene_variant": scene_variant, "query_variant": query_variant}, max_attempts=20)
    trace = out.trace_payload
    assert out.task_variant == query_variant
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert trace["query_spec"]["params"]["scene_variant"] == scene_variant
    assert trace["query_spec"]["params"]["query_variant"] == query_variant
    assert trace["execution_trace"]["legacy_task_id"].startswith("task_geometry_measurement_")
    assert trace["execution_trace"]["task_variant"] == query_variant
    assert trace["execution_trace"]["task_variant_probabilities"] == trace["execution_trace"]["query_variant_probabilities"]
    assert trace["query_spec"]["params"]["variant_probabilities"] == trace["query_spec"]["params"]["query_variant_probabilities"]
    assert out.evidence_gt.type in {"graph_point", "graph_point_set"}


@pytest.mark.parametrize(
    ("scene_variant", "query_variant"),
    (
        ("angle", "largest_angle"),
        ("segment", "smallest_length"),
        ("rectangle", "largest_perimeter"),
    ),
)
def test_geometry_comparison_label_tracks_scene_and_query_variants(scene_variant: str, query_variant: str) -> None:
    task = GeometryComparisonValueTask()
    out = task.generate(23011, params={"scene_variant": scene_variant, "query_variant": query_variant}, max_attempts=20)
    trace = out.trace_payload
    assert out.answer_gt.type == "option_letter"
    assert out.task_variant == query_variant
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert trace["execution_trace"]["legacy_task_id"].startswith("task_geometry_comparison_")
    assert trace["execution_trace"]["task_variant"] == query_variant
    assert trace["execution_trace"]["task_variant_probabilities"] == trace["execution_trace"]["query_variant_probabilities"]
    assert trace["query_spec"]["params"]["variant_probabilities"] == trace["query_spec"]["params"]["query_variant_probabilities"]


@pytest.mark.parametrize(
    ("scene_variant", "query_variant"),
    (
        ("angle", "acute_angle"),
        ("quadrilateral", "square"),
        ("mixed_shape", "ellipse"),
        ("polygon", "concave_polygon"),
    ),
)
def test_geometry_counting_value_tracks_scene_and_query_variants(scene_variant: str, query_variant: str) -> None:
    task = GeometryCountingValueTask()
    out = task.generate(23021, params={"scene_variant": scene_variant, "query_variant": query_variant}, max_attempts=20)
    trace = out.trace_payload
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "label_set"
    assert out.task_variant == query_variant
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert trace["execution_trace"]["legacy_task_id"].startswith("task_geometry_counting_")
    assert trace["execution_trace"]["task_variant"] == query_variant
    assert trace["execution_trace"]["task_variant_probabilities"] == trace["execution_trace"]["query_variant_probabilities"]
    assert trace["query_spec"]["params"]["variant_probabilities"] == trace["query_spec"]["params"]["query_variant_probabilities"]


@pytest.mark.parametrize(
    ("scene_variant", "query_variant"),
    (
        ("triangle", "perimeter"),
        ("circle", "length"),
        ("ellipse", "area"),
        ("composite_region", "composite_area"),
    ),
)
def test_geometry_analytical_2d_value_tracks_scene_and_query_variants(scene_variant: str, query_variant: str) -> None:
    task = GeometryAnalytical2DValueTask()
    out = task.generate(23031, params={"scene_variant": scene_variant, "query_variant": query_variant}, max_attempts=20)
    trace = out.trace_payload
    assert out.evidence_gt.type == "measurement_ref_map"
    assert out.task_variant == query_variant
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert trace["execution_trace"]["legacy_task_id"].startswith("task_geometry_analytical_2d_")
    assert trace["execution_trace"]["task_variant"] == query_variant
    assert trace["execution_trace"]["task_variant_probabilities"] == trace["execution_trace"]["query_variant_probabilities"]
    assert trace["query_spec"]["params"]["variant_probabilities"] == trace["query_spec"]["params"]["query_variant_probabilities"]


@pytest.mark.parametrize(
    ("scene_variant", "query_variant"),
    (
        ("rectangular_prism", "volume"),
        ("sphere", "surface_area"),
    ),
)
def test_geometry_analytical_3d_value_tracks_scene_and_query_variants(scene_variant: str, query_variant: str) -> None:
    task = GeometryAnalytical3DValueTask()
    out = task.generate(23041, params={"scene_variant": scene_variant, "query_variant": query_variant}, max_attempts=20)
    trace = out.trace_payload
    assert out.evidence_gt.type == "measurement_ref_map"
    assert out.task_variant == query_variant
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert trace["execution_trace"]["legacy_task_id"].startswith("task_geometry_analytical_3d_")
    assert trace["execution_trace"]["task_variant"] == query_variant
    assert trace["execution_trace"]["task_variant_probabilities"] == trace["execution_trace"]["query_variant_probabilities"]
    assert trace["query_spec"]["params"]["variant_probabilities"] == trace["query_spec"]["params"]["query_variant_probabilities"]


@pytest.mark.parametrize(
    ("task_cls", "params"),
    (
        (GeometryMeasurementValueTask, {"scene_variant": "triangle", "query_variant": "slope"}),
        (GeometryComparisonValueTask, {"scene_variant": "segment", "query_variant": "largest_area"}),
        (GeometryCountingValueTask, {"scene_variant": "angle", "query_variant": "square"}),
        (GeometryAnalytical2DValueTask, {"scene_variant": "ellipse", "query_variant": "perimeter"}),
        (GeometryAnalytical3DValueTask, {"scene_variant": "sphere", "query_variant": "composite_area"}),
    ),
)
def test_geometry_consolidated_tasks_reject_incompatible_scene_query_pairs(task_cls, params) -> None:
    task = task_cls()
    with pytest.raises(ValueError):
        task.generate(23051, params=params, max_attempts=20)


@pytest.mark.parametrize(
    ("scene_variant", "query_variant", "expected_points"),
    (
        ("triangle", "translation_match", 3),
        ("quadrilateral", "reflection_match", 4),
        ("triangle", "rotation_match", 3),
    ),
)
def test_geometry_transformation_match_tracks_scene_and_query_variants(
    scene_variant: str,
    query_variant: str,
    expected_points: int,
) -> None:
    task = GeometryTransformationMatchTask()
    out = task.generate(23061, params={"scene_variant": scene_variant, "query_variant": query_variant}, max_attempts=20)
    trace = out.trace_payload
    assert out.answer_gt.type == "option_letter"
    assert out.evidence_gt.type == "graph_point_set"
    assert len(out.evidence_gt.value) == expected_points
    assert out.task_variant == query_variant
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert trace["execution_trace"]["task_variant"] == query_variant
    assert trace["execution_trace"]["task_variant_probabilities"] == trace["execution_trace"]["query_variant_probabilities"]
    assert trace["query_spec"]["params"]["variant_probabilities"] == trace["query_spec"]["params"]["query_variant_probabilities"]
    assert trace["scene_ir"]["relations"]["winner_label"] == out.answer_gt.value
    if query_variant == "rotation_match":
        assert trace["execution_trace"]["rotation_mode"]
    if query_variant == "translation_match":
        assert trace["execution_trace"]["translation_vector"]


def test_geometry_transformation_match_balances_winner_labels_across_review_seed_stream() -> None:
    per_variant_labels: dict[str, Counter[str]] = {
        "translation_match": Counter(),
        "reflection_match": Counter(),
        "rotation_match": Counter(),
    }
    collected_counts = {key: 0 for key in per_variant_labels}

    for index in range(10_000):
        if all(int(value) >= 100 for value in collected_counts.values()):
            break
        instance_seed = hash64(0, "task_geometry_transformation_match", index)
        resolved = _resolve_axes(int(instance_seed), params={})
        query_variant = str(resolved.query_variant)
        if int(collected_counts[query_variant]) >= 100:
            continue
        collected_counts[query_variant] += 1
        per_variant_labels[query_variant][str(resolved.winner_label)] += 1

    assert collected_counts == {
        "translation_match": 100,
        "reflection_match": 100,
        "rotation_match": 100,
    }
    for query_variant, counts in per_variant_labels.items():
        assert set(counts.keys()) == {"A", "B", "C", "D", "E", "F"}
        assert max(counts.values()) < 25, query_variant
