"""Behavior tests for consolidated geometry task surfaces."""

from __future__ import annotations

from collections import Counter

import pytest

from trace.core.seed import hash64
from trace.tasks.geometry.analytical_2d.value import GeometryAnalytical2DValueTask
from trace.tasks.geometry.analytical_3d.value import GeometryAnalytical3DValueTask
from trace.tasks.geometry.comparison.value import GeometryComparisonValueTask
from trace.tasks.geometry.coordinate.relation import GeometryCoordinateRelationTask, _resolve_axes as _resolve_coordinate_axes
from trace.tasks.geometry.counting.value import GeometryCountingValueTask
from trace.tasks.geometry.measurement.value import GeometryMeasurementValueTask
from trace.tasks.geometry.similarity.count import GeometrySimilarityCountTask, _resolve_axes as _resolve_similarity_axes
from trace.tasks.geometry.transformation.match import GeometryTransformationMatchTask, _resolve_axes
from trace.tasks import TASK_REGISTRY


EXPECTED_GEOMETRY_TASKS = {
    "task_geometry_measurement_value",
    "task_geometry_comparison_value",
    "task_geometry_coordinate_relation",
    "task_geometry_counting_value",
    "task_geometry_analytical_2d_value",
    "task_geometry_analytical_3d_value",
    "task_geometry_similarity_count",
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


@pytest.mark.parametrize(
    ("scene_variant", "query_variant", "target_count"),
    (
        ("triangle", "congruent_count", 2),
        ("quadrilateral", "similar_count", 3),
        ("triangle", "similar_count", 0),
        ("quadrilateral", "congruent_count", 5),
    ),
)
def test_geometry_similarity_count_tracks_scene_and_query_variants(
    scene_variant: str,
    query_variant: str,
    target_count: int,
) -> None:
    task = GeometrySimilarityCountTask()
    out = task.generate(
        23071,
        params={"scene_variant": scene_variant, "query_variant": query_variant, "target_count": target_count},
        max_attempts=30,
    )
    trace = out.trace_payload
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "label_set"
    assert int(out.answer_gt.value) == int(target_count)
    assert len(out.evidence_gt.value) == int(target_count)
    assert out.task_variant == query_variant
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert trace["execution_trace"]["task_variant"] == query_variant
    assert trace["execution_trace"]["target_count"] == target_count
    assert trace["execution_trace"]["task_variant_probabilities"] == trace["execution_trace"]["query_variant_probabilities"]
    assert trace["query_spec"]["params"]["variant_probabilities"] == trace["query_spec"]["params"]["query_variant_probabilities"]
    assert trace["scene_ir"]["relations"]["matching_labels"] == list(out.evidence_gt.value)


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


def test_geometry_similarity_count_balances_target_counts_across_review_seed_stream() -> None:
    per_variant_counts: dict[str, Counter[int]] = {
        "congruent_count": Counter(),
        "similar_count": Counter(),
    }
    collected_counts = {key: 0 for key in per_variant_counts}

    for index in range(10_000):
        if all(int(value) >= 100 for value in collected_counts.values()):
            break
        instance_seed = hash64(0, "task_geometry_similarity_count", index)
        resolved = _resolve_similarity_axes(int(instance_seed), params={})
        query_variant = str(resolved.query_variant)
        if int(collected_counts[query_variant]) >= 100:
            continue
        collected_counts[query_variant] += 1
        per_variant_counts[query_variant][int(resolved.target_count)] += 1

    assert collected_counts == {
        "congruent_count": 100,
        "similar_count": 100,
    }
    for query_variant, counts in per_variant_counts.items():
        assert set(counts.keys()) == {0, 1, 2, 3, 4, 5}
        assert max(counts.values()) <= 25, query_variant


@pytest.mark.parametrize(
    ("scene_variant", "query_variant", "answer_type", "evidence_type"),
    (
        ("segment_set", "parallel_count", "integer", "graph_point_set"),
        ("segment_set", "perpendicular_count", "integer", "graph_point_set"),
        ("line_points", "collinear_count", "integer", "graph_point_set"),
        ("quadrant_points", "same_quadrant_count", "integer", "graph_point_set"),
        ("polygon_lattice", "point_in_shape_count", "integer", "graph_point_set"),
    ),
)
def test_geometry_coordinate_relation_tracks_scene_and_query_variants(
    scene_variant: str,
    query_variant: str,
    answer_type: str,
    evidence_type: str,
) -> None:
    task = GeometryCoordinateRelationTask()
    params = {"scene_variant": scene_variant, "query_variant": query_variant}
    if query_variant in {"parallel_count", "perpendicular_count", "collinear_count"}:
        params["target_count"] = 2
    elif query_variant == "same_quadrant_count":
        params["target_count"] = 2
    elif query_variant == "point_in_shape_count":
        params["target_count"] = 4
    out = task.generate(23081, params=params, max_attempts=30)
    trace = out.trace_payload
    assert out.answer_gt.type == answer_type
    assert out.evidence_gt.type == evidence_type
    assert out.task_variant == query_variant
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert trace["execution_trace"]["task_variant"] == query_variant
    assert trace["execution_trace"]["task_variant_probabilities"] == trace["execution_trace"]["query_variant_probabilities"]
    assert trace["query_spec"]["params"]["variant_probabilities"] == trace["query_spec"]["params"]["query_variant_probabilities"]


def test_geometry_coordinate_relation_balances_count_targets_across_review_seed_stream() -> None:
    per_variant_counts: dict[str, Counter[int]] = {
        "parallel_count": Counter(),
        "perpendicular_count": Counter(),
        "collinear_count": Counter(),
        "same_quadrant_count": Counter(),
        "point_in_shape_count": Counter(),
    }
    collected_counts = {key: 0 for key in per_variant_counts}

    for index in range(10_000):
        if all(int(value) >= 100 for value in collected_counts.values()):
            break
        instance_seed = hash64(0, "task_geometry_coordinate_relation", index)
        resolved = _resolve_coordinate_axes(int(instance_seed), params={})
        query_variant = str(resolved.query_variant)
        if query_variant not in per_variant_counts:
            continue
        if int(collected_counts[query_variant]) >= 100:
            continue
        collected_counts[query_variant] += 1
        per_variant_counts[query_variant][int(resolved.target_count)] += 1

    assert collected_counts == {
        "parallel_count": 100,
        "perpendicular_count": 100,
        "collinear_count": 100,
        "same_quadrant_count": 100,
        "point_in_shape_count": 100,
    }
    assert set(per_variant_counts["parallel_count"].keys()) == {0, 1, 2, 3, 4, 5, 6}
    assert max(per_variant_counts["parallel_count"].values()) <= 25
    assert set(per_variant_counts["perpendicular_count"].keys()) == {0, 1, 2, 3, 4, 5, 6}
    assert max(per_variant_counts["perpendicular_count"].values()) <= 25
    assert set(per_variant_counts["collinear_count"].keys()) == {0, 1, 2, 3, 4, 5, 6}
    assert max(per_variant_counts["collinear_count"].values()) <= 25
    assert set(per_variant_counts["same_quadrant_count"].keys()) == {0, 1, 2, 3, 4, 5, 6}
    assert max(per_variant_counts["same_quadrant_count"].values()) <= 25
    assert set(per_variant_counts["point_in_shape_count"].keys()) == {0, 1, 2, 3, 4, 5, 6, 7, 8}
    assert max(per_variant_counts["point_in_shape_count"].values()) <= 20
