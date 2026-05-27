"""Behavior tests for consolidated geometry task surfaces."""

from __future__ import annotations

from collections import Counter

import pytest

from trace.core.seed import hash64
from trace.tasks.geometry.comparison.value import GeometryComparisonValueTask
from trace.tasks.geometry.coordinate.relation import (
    GeometryCoordinateRelationTask,
    _resolve_axes as _resolve_coordinate_axes,
)
from trace.tasks.geometry.counting.value import GeometryCountingValueTask
from trace.tasks.geometry.graphing.count import (
    GeometryGraphingCountTask,
    _resolve_axes as _resolve_graphing_axes,
)
from trace.tasks.geometry.measurement.value import GeometryMeasurementValueTask
from trace.tasks.geometry.similarity.count import (
    GeometrySimilarityCountTask,
    _resolve_axes as _resolve_similarity_axes,
)
from trace.tasks.geometry.transformation.match import (
    GeometryTransformationMatchTask,
    _resolve_axes,
)
from trace.tasks import TASK_REGISTRY

EXPECTED_GEOMETRY_TASKS = {
    "task_geometry__function_panels__relation_property_label",
    "task_geometry__function_panels__intersection_property_label",
    "task_geometry__function_panels__relation_property_label",
    "task_geometry__function_panels__relation_property_label",
    "task_geometry__function_panels__relation_property_label",
    "task_geometry__function_panels__relation_property_label",
    "task_geometry__circle_theorem__diameter_perpendicular_chord_length_value",
    "task_geometry__circle_theorem__intersecting_chords_arc_measure_value",
    "task_geometry__circle_theorem__inscribed_angle_value",
    "task_geometry__circle_theorem__multi_step_angle_value",
    "task_geometry__circle_theorem__secant_secant_length_value",
    "task_geometry__circle_theorem__tangent_chord_angle_value",
    "task_geometry__circle_theorem__tangent_secant_length_value",
    "task_geometry__graph_paper__angle_extremum_label",
    "task_geometry__graph_paper__area_extremum_label",
    "task_geometry__graph_paper__length_extremum_label",
    "task_geometry__graph_paper__perimeter_extremum_label",
    "task_geometry__coordinate_plane__collinear_point_count",
    "task_geometry__coordinate_plane__locus_panel_match_label",
    "task_geometry__coordinate_plane__locus_point_label",
    "task_geometry__coordinate_plane__missing_endpoint_label",
    "task_geometry__coordinate_plane__point_in_polygon_count",
    "task_geometry__coordinate_plane__quadrilateral_completion_label",
    "task_geometry__coordinate_panels__quadrilateral_shape_match_label",
    "task_geometry__coordinate_plane__same_quadrant_point_count",
    "task_geometry__coordinate_plane__section_point_label",
    "task_geometry__coordinate_plane__segment_relation_count",
    "task_geometry__coordinate_plane__transformed_point_label",
    "task_geometry__graph_paper__angle_type_count",
    "task_geometry__graph_paper__polygon_convexity_count",
    "task_geometry__graph_paper__quadrilateral_type_count",
    "task_geometry__graph_paper__shape_type_count",
    "task_geometry__graph_paper__triangle_type_count",
    "task_geometry__function_graph__average_rate_value",
    "task_geometry__function_graph__extremum_count",
    "task_geometry__function_graph__reference_line_crossing_count",
    "task_geometry__angle_relations__algebraic_angle_value",
    "task_geometry__angle_relations__angle_chain_value",
    "task_geometry__triangle_relations__angle_bisector_segment_value",
    "task_geometry__graph_paper__angle_value",
    "task_geometry__triangle_relations__centroid_median_segment_value",
    "task_geometry__graph_paper__circle_circumference_value",
    "task_geometry__cone_net__cone_sector_net_value",
    "task_geometry__concentric_chord__concentric_circle_chord_value",
    "task_geometry__composite_shape__composite_area_value",
    "task_geometry__composite_shape__composite_perimeter_value",
    "task_geometry__cuboid_views__cuboid_projection_surface_area_value",
    "task_geometry__composite_shape__curvilinear_composite_area_value",
    "task_geometry__composite_shape__curvilinear_composite_perimeter_value",
    "task_geometry__composite_shape__curvilinear_missing_side_from_area_value",
    "task_geometry__composite_shape__curvilinear_sector_angle_value",
    "task_geometry__graph_paper__ellipse_area_value",
    "task_geometry__incircle_tangents__incircle_radius_from_area_value",
    "task_geometry__incircle_tangents__incircle_tangent_perimeter_value",
    "task_geometry__graph_paper__line_slope_value",
    "task_geometry__triangle_relations__parallel_section_length_value",
    "task_geometry__paper_fold__paper_fold_angle_value",
    "task_geometry__area_partition__parallelogram_area_partition_total_area_value",
    "task_geometry__graph_paper__polygon_area_value",
    "task_geometry__graph_paper__polygon_perimeter_value",
    "task_geometry__triangle_relations__pythagorean_length_value",
    "task_geometry__pythagorean_dissection__pythagorean_square_area_value",
    "task_geometry__triangle_relations__right_triangle_angle_value",
    "task_geometry__triangle_relations__right_triangle_missing_side_value",
    "task_geometry__solid_revolution__revolution_cone_volume_value",
    "task_geometry__solid_revolution__revolution_cylinder_volume_value",
    "task_geometry__solid_revolution__revolution_double_cone_volume_value",
    "task_geometry__solid_revolution__revolution_frustum_volume_value",
    "task_geometry__sector__sector_angle_relation_value",
    "task_geometry__sector__sector_measure_value",
    "task_geometry__triangle_relations__parallel_section_length_value",
    "task_geometry__solid_cross_section__solid_cross_section_area_value",
    "task_geometry__solid_formula__solid_formula_missing_dimension_value",
    "task_geometry__tangent_packing__tangent_packing_length_value",
    "task_geometry__tangent_packing__tangent_packing_shaded_area_value",
    "task_geometry__area_partition__triangle_area_partition_total_area_value",
    "task_geometry__trapezoid_extension__trapezoid_extension_area_value",
    "task_geometry__trapezoid_extension__trapezoid_extension_length_value",
    "task_geometry__shape_gallery__shape_relation_count",
    "task_geometry__shape_gallery__transformation_match_label",
}


def test_geometry_registry_includes_consolidated_value_tasks_plus_new_visual_families() -> (
    None
):
    geometry_tasks = {
        task_id for task_id in TASK_REGISTRY if task_id.startswith("task_geometry__")
    }
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
def test_geometry_measurement_value_tracks_scene_and_query_variants(
    scene_variant: str, query_variant: str
) -> None:
    task = GeometryMeasurementValueTask()
    out = task.generate(
        23001,
        params={"scene_variant": scene_variant, "query_variant": query_variant},
        max_attempts=20,
    )
    trace = out.trace_payload
    assert out.query_variant == query_variant
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert trace["query_spec"]["params"]["scene_variant"] == scene_variant
    assert trace["query_spec"]["params"]["query_variant"] == query_variant
    assert trace["execution_trace"]["source_task_id"].startswith(
        "source_geometry_measurement_"
    )
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert (
        trace["execution_trace"]["query_variant_probabilities"]
        == trace["execution_trace"]["query_variant_probabilities"]
    )
    assert (
        trace["query_spec"]["params"]["variant_probabilities"]
        == trace["query_spec"]["params"]["query_variant_probabilities"]
    )
    assert out.evidence_gt.type == "point_set"


@pytest.mark.parametrize(
    ("scene_variant", "query_variant", "extremum_direction"),
    (
        ("angle", "angle_extremum", "largest"),
        ("segment", "length_extremum", "smallest"),
        ("rectangle", "perimeter_extremum", "largest"),
        ("triangle", "area_extremum", "largest"),
    ),
)
def test_geometry_comparison_label_tracks_scene_and_query_variants(
    scene_variant: str,
    query_variant: str,
    extremum_direction: str,
) -> None:
    task = GeometryComparisonValueTask()
    out = task.generate(
        23011,
        params={
            "scene_variant": scene_variant,
            "query_variant": query_variant,
            "extremum_direction": extremum_direction,
        },
        max_attempts=20,
    )
    trace = out.trace_payload
    assert out.answer_gt.type == "option_letter"
    assert out.query_variant == query_variant
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert trace["execution_trace"]["extremum_direction"] == extremum_direction
    assert trace["query_spec"]["params"]["extremum_direction"] == extremum_direction
    assert trace["execution_trace"]["source_task_id"].startswith(
        "source_geometry_comparison_"
    )
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert (
        trace["execution_trace"]["query_variant_probabilities"]
        == trace["execution_trace"]["query_variant_probabilities"]
    )
    assert (
        trace["query_spec"]["params"]["variant_probabilities"]
        == trace["query_spec"]["params"]["query_variant_probabilities"]
    )
    if scene_variant == "triangle":
        assert "triangle" in out.prompt.lower()
        assert "rectangle" not in out.prompt.lower()
        assert "exactly three pixel points" in out.prompt


@pytest.mark.parametrize(
    ("scene_variant", "query_variant", "extremum_direction"),
    (
        ("angle", "angle_extremum", "largest"),
        ("angle", "angle_extremum", "smallest"),
        ("segment", "length_extremum", "largest"),
        ("segment", "length_extremum", "smallest"),
        ("rectangle", "area_extremum", "largest"),
        ("rectangle", "area_extremum", "smallest"),
        ("rectangle", "perimeter_extremum", "largest"),
        ("rectangle", "perimeter_extremum", "smallest"),
        ("triangle", "area_extremum", "largest"),
        ("triangle", "area_extremum", "smallest"),
        ("triangle", "perimeter_extremum", "largest"),
        ("triangle", "perimeter_extremum", "smallest"),
    ),
)
def test_geometry_comparison_value_supports_eight_compared_objects(
    scene_variant: str,
    query_variant: str,
    extremum_direction: str,
) -> None:
    task = GeometryComparisonValueTask()
    out = task.generate(
        23111,
        params={
            "scene_variant": scene_variant,
            "query_variant": query_variant,
            "extremum_direction": extremum_direction,
            "object_count": 8,
        },
        max_attempts=100,
    )
    trace = out.trace_payload
    assert int(trace["execution_trace"]["object_count"]) == 8
    assert len(trace["execution_trace"]["object_labels"]) == 8
    assert set(trace["execution_trace"]["object_labels"]).issubset(set("ABCDEFGH"))
    if scene_variant == "triangle":
        assert len(out.evidence_gt.value) == 3
        assert trace["execution_trace"]["shape_family"] == "triangle"
        assert "triangle" in out.prompt.lower()
        assert "rectangle" not in out.prompt.lower()
        assert "exactly three pixel points" in out.prompt
    if scene_variant == "rectangle":
        assert len(out.evidence_gt.value) == 4
        assert trace["execution_trace"]["shape_family"] == "rectangle"


@pytest.mark.parametrize(
    ("scene_variant", "query_variant", "class_params"),
    (
        ("angle", "angle_type_count", {"angle_type": "acute"}),
        ("quadrilateral", "quadrilateral_type_count", {"quadrilateral_type": "square"}),
        ("mixed_shape", "shape_type_count", {"shape_type": "ellipse"}),
        ("polygon", "polygon_convexity_count", {"convexity_kind": "concave"}),
    ),
)
def test_geometry_counting_value_tracks_scene_and_query_variants(
    scene_variant: str,
    query_variant: str,
    class_params: dict[str, str],
) -> None:
    task = GeometryCountingValueTask()
    out = task.generate(
        23021,
        params={
            "scene_variant": scene_variant,
            "query_variant": query_variant,
            **class_params,
        },
        max_attempts=20,
    )
    trace = out.trace_payload
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert out.query_variant == query_variant
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert trace["execution_trace"]["source_task_id"].startswith(
        "source_geometry_counting_"
    )
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert (
        trace["execution_trace"]["query_variant_probabilities"]
        == trace["execution_trace"]["query_variant_probabilities"]
    )
    assert (
        trace["query_spec"]["params"]["variant_probabilities"]
        == trace["query_spec"]["params"]["query_variant_probabilities"]
    )
    assert trace["execution_trace"]["counted_class_parameter"]
    assert trace["execution_trace"]["counted_class"]
    assert trace["render_spec"]["text_style"]["draw_object_labels"] is False
    assert trace["render_map"]["object_label_centers"] == {}


@pytest.mark.parametrize(
    ("scene_variant", "query_variant"),
    (
        ("angle", "angle_type_count"),
        ("triangle", "triangle_type_count"),
        ("quadrilateral", "quadrilateral_type_count"),
        ("mixed_shape", "shape_type_count"),
        ("polygon", "polygon_convexity_count"),
    ),
)
def test_geometry_counting_value_supports_twelve_objects(
    scene_variant: str, query_variant: str
) -> None:
    task = GeometryCountingValueTask()
    out = task.generate(
        23121,
        params={
            "scene_variant": scene_variant,
            "query_variant": query_variant,
            "object_count": 12,
        },
        max_attempts=100,
    )
    trace = out.trace_payload
    assert int(trace["execution_trace"]["object_count"]) == 12
    assert len(trace["execution_trace"]["object_labels"]) == 12
    assert set(trace["execution_trace"]["object_labels"]) == set("ABCDEFGHIJKL")
    assert 1 <= int(out.answer_gt.value) <= 11


@pytest.mark.parametrize(
    ("task_cls", "params"),
    (
        (
            GeometryMeasurementValueTask,
            {"scene_variant": "triangle", "query_variant": "slope"},
        ),
        (
            GeometryComparisonValueTask,
            {"scene_variant": "segment", "query_variant": "area_extremum"},
        ),
        (
            GeometryCountingValueTask,
            {"scene_variant": "angle", "query_variant": "shape_type_count"},
        ),
    ),
)
def test_geometry_consolidated_tasks_reject_incompatible_scene_query_pairs(
    task_cls, params
) -> None:
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
    out = task.generate(
        23061,
        params={"scene_variant": scene_variant, "query_variant": query_variant},
        max_attempts=20,
    )
    trace = out.trace_payload
    assert out.answer_gt.type == "option_letter"
    assert out.evidence_gt.type == "point_set"
    assert len(out.evidence_gt.value) == expected_points
    assert out.query_variant == query_variant
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert (
        trace["execution_trace"]["query_variant_probabilities"]
        == trace["execution_trace"]["query_variant_probabilities"]
    )
    assert (
        trace["query_spec"]["params"]["variant_probabilities"]
        == trace["query_spec"]["params"]["query_variant_probabilities"]
    )
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
        params={
            "scene_variant": scene_variant,
            "query_variant": query_variant,
            "target_count": target_count,
        },
        max_attempts=30,
    )
    trace = out.trace_payload
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == int(target_count)
    assert len(out.evidence_gt.value) == int(target_count)
    assert out.query_variant == query_variant
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert trace["execution_trace"]["target_count"] == target_count
    assert (
        trace["execution_trace"]["query_variant_probabilities"]
        == trace["execution_trace"]["query_variant_probabilities"]
    )
    assert (
        trace["query_spec"]["params"]["variant_probabilities"]
        == trace["query_spec"]["params"]["query_variant_probabilities"]
    )
    assert (
        trace["witness_symbolic"]["label_set"]
        == trace["scene_ir"]["relations"]["matching_labels"]
    )
    assert trace["projected_evidence"]["bbox_set"] == list(out.evidence_gt.value)


@pytest.mark.parametrize(
    ("scene_variant", "query_variant", "params", "target_count"),
    (
        (
            "quadratic",
            "reference_line_crossing_count",
            {"reference_line_kind": "x_axis"},
            2,
        ),
        (
            "absolute_value",
            "reference_line_crossing_count",
            {"reference_line_kind": "horizontal_line"},
            2,
        ),
        (
            "cubic",
            "reference_line_crossing_count",
            {"reference_line_kind": "x_axis"},
            3,
        ),
        (
            "sinusoid",
            "reference_line_crossing_count",
            {"reference_line_kind": "horizontal_line"},
            4,
        ),
        ("sinusoid", "turning_point_count", {}, 4),
        ("sinusoid", "local_extremum_count", {"extremum_kind": "minimum"}, 2),
        ("sinusoid", "local_extremum_count", {"extremum_kind": "maximum"}, 2),
        ("piecewise_linear", "turning_point_count", {}, 6),
        ("piecewise_linear", "local_extremum_count", {"extremum_kind": "minimum"}, 6),
        ("piecewise_linear", "local_extremum_count", {"extremum_kind": "maximum"}, 6),
    ),
)
def test_geometry_graphing_count_tracks_scene_and_query_variants(
    scene_variant: str,
    query_variant: str,
    params: dict[str, str],
    target_count: int,
) -> None:
    task = GeometryGraphingCountTask()
    generation_params = {
        "scene_variant": scene_variant,
        "query_variant": query_variant,
        "target_count": target_count,
        **dict(params),
    }
    out = task.generate(
        23095,
        params=generation_params,
        max_attempts=40,
    )
    trace = out.trace_payload
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "point_set"
    assert int(out.answer_gt.value) == int(target_count)
    assert len(out.evidence_gt.value) == int(target_count)
    assert out.query_variant == query_variant
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert (
        trace["execution_trace"]["query_variant_probabilities"]
        == trace["execution_trace"]["query_variant_probabilities"]
    )
    assert (
        trace["query_spec"]["params"]["variant_probabilities"]
        == trace["query_spec"]["params"]["query_variant_probabilities"]
    )
    for key, value in params.items():
        assert trace["execution_trace"][key] == value
        assert trace["query_spec"]["params"][key] == value


def test_geometry_transformation_match_balances_winner_labels_across_review_seed_stream() -> (
    None
):
    per_variant_labels: dict[str, Counter[str]] = {
        "translation_match": Counter(),
        "reflection_match": Counter(),
        "rotation_match": Counter(),
    }
    collected_counts = {key: 0 for key in per_variant_labels}

    for index in range(10_000):
        if all(int(value) >= 100 for value in collected_counts.values()):
            break
        instance_seed = hash64(0, "geometry_transformation_match_base", index)
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
        assert max(counts.values()) <= 30, query_variant


def test_geometry_transformation_match_decouplesseeded_sampler_axes() -> None:
    per_variant_labels: dict[str, Counter[str]] = {
        "translation_match": Counter(),
        "reflection_match": Counter(),
        "rotation_match": Counter(),
    }
    per_variant_scenes: dict[str, Counter[str]] = {
        "translation_match": Counter(),
        "reflection_match": Counter(),
        "rotation_match": Counter(),
    }

    for index in range(100):
        instance_seed = hash64(0, "geometry_transformation_match_base", index)
        resolved = _resolve_axes(int(instance_seed), params={})
        query_variant = str(resolved.query_variant)
        per_variant_labels[query_variant][str(resolved.winner_label)] += 1
        per_variant_scenes[query_variant][str(resolved.scene_variant)] += 1

    assert sum(sum(counter.values()) for counter in per_variant_labels.values()) == 100
    for query_variant, counts in per_variant_labels.items():
        assert set(counts.keys()) == {"A", "B", "C", "D", "E", "F"}
        assert max(counts.values()) <= 12, query_variant
        assert set(per_variant_scenes[query_variant].keys()) == {
            "triangle",
            "quadrilateral",
        }


def test_geometry_similarity_count_balances_target_counts_across_review_seed_stream() -> (
    None
):
    per_variant_counts: dict[str, Counter[int]] = {
        "congruent_count": Counter(),
        "similar_count": Counter(),
    }
    collected_counts = {key: 0 for key in per_variant_counts}

    for index in range(10_000):
        if all(int(value) >= 100 for value in collected_counts.values()):
            break
        instance_seed = hash64(0, "geometry_similarity_count_base", index)
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


def test_geometry_similarity_count_decouplesseeded_sampler_axes() -> None:
    per_variant_counts: dict[str, Counter[int]] = {
        "congruent_count": Counter(),
        "similar_count": Counter(),
    }
    per_variant_scenes: dict[str, Counter[str]] = {
        "congruent_count": Counter(),
        "similar_count": Counter(),
    }
    combos: Counter[tuple[str, str, int]] = Counter()

    for index in range(100):
        instance_seed = hash64(0, "geometry_similarity_count_base", index)
        resolved = _resolve_similarity_axes(
            int(instance_seed), params={}
        )
        query_variant = str(resolved.query_variant)
        scene_variant = str(resolved.scene_variant)
        target_count = int(resolved.target_count)
        per_variant_counts[query_variant][target_count] += 1
        per_variant_scenes[query_variant][scene_variant] += 1
        combos[(query_variant, scene_variant, target_count)] += 1

    assert all(40 <= sum(counter.values()) <= 60 for counter in per_variant_counts.values())
    for query_variant, counts in per_variant_counts.items():
        assert set(counts.keys()) == {0, 1, 2, 3, 4, 5}
        assert max(counts.values()) <= 14, query_variant
        assert set(per_variant_scenes[query_variant].keys()) == {
            "triangle",
            "quadrilateral",
        }
    assert len(combos) >= 22


def test_geometry_graphing_count_balances_target_counts_across_review_seed_stream() -> (
    None
):
    per_variant_counts: dict[str, Counter[int]] = {
        "reference_line_crossing_count": Counter(),
        "turning_point_count": Counter(),
        "local_extremum_count": Counter(),
    }
    collected_counts = {key: 0 for key in per_variant_counts}

    for index in range(10_000):
        if all(int(value) >= 100 for value in collected_counts.values()):
            break
        instance_seed = hash64(0, "geometry_graphing_count_base", index)
        resolved = _resolve_graphing_axes(int(instance_seed), params={})
        query_variant = str(resolved.query_variant)
        if int(collected_counts[query_variant]) >= 100:
            continue
        collected_counts[query_variant] += 1
        per_variant_counts[query_variant][int(resolved.target_count)] += 1

    assert collected_counts == {
        "reference_line_crossing_count": 100,
        "turning_point_count": 100,
        "local_extremum_count": 100,
    }
    expected_support = {2, 3, 4, 5, 6}
    for query_variant, counts in per_variant_counts.items():
        assert set(counts.keys()) == expected_support, query_variant
        assert max(counts.values()) <= 30, query_variant


def test_geometry_graphing_count_balances_target_counts_withseeded_sampler_stream() -> (
    None
):
    per_variant_counts: dict[str, Counter[int]] = {
        "reference_line_crossing_count": Counter(),
        "turning_point_count": Counter(),
        "local_extremum_count": Counter(),
    }

    for index in range(300):
        instance_seed = hash64(0, "geometry_graphing_count_base", index)
        resolved = _resolve_graphing_axes(
            int(instance_seed), params={}
        )
        per_variant_counts[str(resolved.query_variant)][int(resolved.target_count)] += 1

    assert all(80 <= sum(counter.values()) <= 120 for counter in per_variant_counts.values())
    for counter in per_variant_counts.values():
        assert set(counter.keys()) == {2, 3, 4, 5, 6}
        assert max(counter.values()) <= 30
        assert min(counter.values()) >= 10


def test_geometry_graphing_count_balances_parameter_axes_withseeded_sampler_stream() -> (
    None
):
    reference_line_counts: Counter[str] = Counter()
    extremum_counts: Counter[str] = Counter()

    for index in range(120):
        instance_seed = hash64(0, "geometry_graphing_count_base.params", index)
        crossing = _resolve_graphing_axes(
            int(instance_seed),
            params={
                "query_variant": "reference_line_crossing_count",
            },
        )
        reference_line_counts[str(crossing.reference_line_kind)] += 1
        local_extremum = _resolve_graphing_axes(
            int(instance_seed),
            params={"query_variant": "local_extremum_count"},
        )
        extremum_counts[str(local_extremum.extremum_kind)] += 1

    assert set(reference_line_counts) == {"x_axis", "horizontal_line"}
    assert set(extremum_counts) == {"minimum", "maximum"}
    assert all(50 <= count <= 70 for count in reference_line_counts.values())
    assert all(50 <= count <= 70 for count in extremum_counts.values())


def test_geometry_measurement_value_decouples_source_answerseeded_sampler() -> None:
    task = GeometryMeasurementValueTask()
    per_variant_answers: dict[str, Counter[str]] = {
        "area": Counter(),
        "perimeter": Counter(),
    }
    all_variants: Counter[str] = Counter()

    for index in range(100):
        instance_seed = hash64(0, "geometry_measurement_value_base", index)
        out = task.generate(
            int(instance_seed),
            params={},
            max_attempts=100,
        )
        all_variants[str(out.query_variant)] += 1
        if str(out.query_variant) in per_variant_answers:
            per_variant_answers[str(out.query_variant)][str(out.answer_gt.value)] += 1

    assert set(all_variants) == {"angle", "area", "perimeter", "slope"}
    assert all(15 <= count <= 35 for count in all_variants.values())
    assert 15 <= sum(per_variant_answers["area"].values()) <= 35
    assert 15 <= sum(per_variant_answers["perimeter"].values()) <= 35
    assert max(per_variant_answers["area"].values()) <= 10
    assert max(per_variant_answers["perimeter"].values()) <= 10


@pytest.mark.parametrize(
    ("scene_variant", "query_variant", "answer_type", "evidence_type"),
    (
        ("segment_set", "parallel_count", "integer", "point_set"),
        ("segment_set", "perpendicular_count", "integer", "point_set"),
        ("line_points", "collinear_count", "integer", "point_set"),
        ("quadrant_points", "same_quadrant_count", "integer", "point_set"),
        ("polygon_lattice", "point_in_shape_count", "integer", "point_set"),
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
    assert out.query_variant == query_variant
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert trace["execution_trace"]["query_variant"] == query_variant
    assert (
        trace["execution_trace"]["query_variant_probabilities"]
        == trace["execution_trace"]["query_variant_probabilities"]
    )
    assert (
        trace["query_spec"]["params"]["variant_probabilities"]
        == trace["query_spec"]["params"]["query_variant_probabilities"]
    )


def test_geometry_coordinate_relation_balances_count_targets_across_review_seed_stream() -> (
    None
):
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
        instance_seed = hash64(0, "geometry_coordinate_relation_base", index)
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
    assert set(per_variant_counts["perpendicular_count"].keys()) == {
        0,
        1,
        2,
        3,
        4,
        5,
        6,
    }
    assert max(per_variant_counts["perpendicular_count"].values()) <= 25
    assert set(per_variant_counts["collinear_count"].keys()) == {0, 1, 2, 3, 4, 5, 6}
    assert max(per_variant_counts["collinear_count"].values()) <= 25
    assert set(per_variant_counts["same_quadrant_count"].keys()) == {
        0,
        1,
        2,
        3,
        4,
        5,
        6,
    }
    assert max(per_variant_counts["same_quadrant_count"].values()) <= 25
    assert set(per_variant_counts["point_in_shape_count"].keys()) == {
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
    }
    assert max(per_variant_counts["point_in_shape_count"].values()) <= 20
