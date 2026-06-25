"""Behavior tests for consolidated geometry task surfaces."""

from __future__ import annotations

from collections import Counter

import pytest

from trace.core.seed import hash64
from trace.tasks.geometry.coordinate_plane.collinear_point_count import GeometryCoordinateCollinearPointCountTask
from trace.tasks.geometry.coordinate_plane.point_in_polygon_count import GeometryCoordinatePointInPolygonCountTask
from trace.tasks.geometry.coordinate_plane.same_quadrant_point_count import GeometryCoordinateSameQuadrantPointCountTask
from trace.tasks.geometry.coordinate_plane.segment_relation_count import GeometryCoordinateSegmentRelationCountTask
from trace.tasks.geometry.graph_paper.angle_extremum_label import GeometryGraphPaperAngleExtremumLabelTask
from trace.tasks.geometry.graph_paper.angle_type_count import GeometryGraphPaperAngleTypeCountTask
from trace.tasks.geometry.graph_paper.area_extremum_label import GeometryGraphPaperAreaExtremumLabelTask
from trace.tasks.geometry.graph_paper.length_extremum_label import GeometryGraphPaperLengthExtremumLabelTask
from trace.tasks.geometry.graph_paper.perimeter_extremum_label import GeometryGraphPaperPerimeterExtremumLabelTask
from trace.tasks.geometry.graph_paper.polygon_convexity_count import GeometryGraphPaperPolygonConvexityCountTask
from trace.tasks.geometry.graph_paper.quadrilateral_type_count import GeometryGraphPaperQuadrilateralTypeCountTask
from trace.tasks.geometry.graph_paper.shape_type_count import GeometryGraphPaperShapeTypeCountTask
from trace.tasks.geometry.graph_paper.triangle_type_count import GeometryGraphPaperTriangleTypeCountTask
from trace.tasks.geometry.shape_gallery.congruent_count import GeometryShapeGalleryCongruentCountTask
from trace.tasks.geometry.shape_gallery.reflection_match import GeometryShapeGalleryReflectionMatchTask
from trace.tasks.geometry.shape_gallery.rotation_match import GeometryShapeGalleryRotationMatchTask
from trace.tasks.geometry.shape_gallery.similar_count import GeometryShapeGallerySimilarCountTask
from trace.tasks.shared.fixed_query import select_geometry_query_id
from trace.tasks.geometry.shape_gallery.shared.construction import _resolve_axes as _resolve_transform_axes
from trace.tasks.geometry.shape_gallery.shared.relations import _resolve_axes as _resolve_relation_axes
from trace.tasks.geometry.shape_gallery.translation_match import GeometryShapeGalleryTranslationMatchTask
from trace.tasks.registry import create_task

REQUIRED_GEOMETRY_SPLIT_TASKS = {
    "task_geometry__function_panels__function_status_label",
    "task_geometry__function_panels__one_to_one_status_label",
    "task_geometry__function_panels__range_match_label",
    "task_geometry__function_panels__sign_interval_label",
    "task_geometry__function_panels__x_axis_symmetry_label",
    "task_geometry__circle_theorem__inscribed_central_angle_value",
    "task_geometry__circle_theorem__inscribed_angle_value_inscribed_angle_from_arc",
    "task_geometry__circle_theorem__tangent_chord_angle_value_tangent_chord_angle_from_arc",
    "task_geometry__circle_theorem__tangent_chord_angle_value_tangent_chord_angle_from_inscribed",
    "task_geometry__coordinate_plane__reflected_point_label",
    "task_geometry__coordinate_plane__rotated_point_label",
    "task_geometry__coordinate_plane__translated_point_label",
    "task_geometry__function_graph__extremum_count_local_extremum_count",
    "task_geometry__function_graph__extremum_count_turning_point_count",
    "task_geometry__angle_relations__algebraic_angle_value",
    "task_geometry__angle_relations__parallel_supplement_angle",
    "task_geometry__angle_relations__triangle_exterior_angle",
    "task_geometry__shape_gallery__congruent_count",
    "task_geometry__shape_gallery__similar_count",
    "task_geometry__shape_gallery__reflection_match",
    "task_geometry__shape_gallery__rotation_match",
    "task_geometry__shape_gallery__translation_match",
}

def test_geometry_registry_includes_consolidated_value_tasks_plus_new_visual_families() -> None:
    for task_id in REQUIRED_GEOMETRY_SPLIT_TASKS:
        task = create_task(task_id)
        assert task.task_id == task_id
        assert getattr(task, "default_dataset_enabled", False)


def test_geometry_query_selection_prefers_query_id_over_legacy_query_variant() -> None:
    selected, probabilities = select_geometry_query_id(
        {"query_variant": "second"},
        query_ids=("first", "second"),
        task_id="task_geometry__example__value",
        instance_seed=17,
    )

    assert selected == "second"
    assert probabilities == {"second": 1.0}

    with pytest.raises(ValueError):
        select_geometry_query_id(
            {"query_id": "second", "query_variant": "first"},
            query_ids=("first", "second"),
            task_id="task_geometry__example__value",
            instance_seed=17,
        )


def _assert_consolidated_probability_metadata(trace: dict, *, scene_variant: str, query_id: str) -> None:
    execution = trace["execution_trace"]
    query_params = trace["query_spec"]["params"]
    scene_probabilities = execution["scene_variant_probabilities"]
    query_probabilities = execution["query_id_probabilities"]

    assert scene_probabilities == query_params["scene_variant_probabilities"]
    assert query_probabilities == query_params["query_id_probabilities"]
    assert scene_variant in scene_probabilities
    assert query_id in query_probabilities
    assert scene_probabilities[scene_variant] == 1.0
    assert query_probabilities[query_id] == 1.0
    assert abs(sum(float(value) for value in scene_probabilities.values()) - 1.0) < 1e-9
    assert abs(sum(float(value) for value in query_probabilities.values()) - 1.0) < 1e-9


@pytest.mark.parametrize(
    ("task_cls", "query_id", "program_code"),
    (
        (GeometryGraphPaperAngleExtremumLabelTask, "largest", "labeled_angles.extremum_label"),
        (GeometryGraphPaperLengthExtremumLabelTask, "smallest", "labeled_segments.length_extremum_label"),
        (GeometryGraphPaperAreaExtremumLabelTask, "largest", "labeled_shapes.area_extremum_label"),
        (GeometryGraphPaperPerimeterExtremumLabelTask, "smallest", "labeled_shapes.perimeter_extremum_label"),
    ),
)
def test_geometry_graph_paper_extremum_split_tasks_track_query_ids(
    task_cls,
    query_id: str,
    program_code: str,
) -> None:
    task = task_cls()
    out = task.generate(23011, params={"query_id": query_id, "object_count": 6}, max_attempts=40)
    trace = out.trace_payload
    assert out.answer_gt.type == "option_letter"
    assert out.query_id == query_id
    assert out.scene_id == "graph_paper"
    assert trace["execution_trace"]["scene_id"] == "graph_paper"
    assert trace["execution_trace"]["query_id"] == query_id
    assert trace["execution_trace"]["program_code"] == program_code
    assert "source_task_id" not in trace["execution_trace"]


@pytest.mark.parametrize(
    ("task_cls", "params", "program_code"),
    (
        (GeometryGraphPaperAngleTypeCountTask, {"angle_type": "acute"}, "angle_set.class_count"),
        (GeometryGraphPaperTriangleTypeCountTask, {"triangle_type": "right"}, "triangle_set.class_count"),
        (GeometryGraphPaperQuadrilateralTypeCountTask, {"quadrilateral_type": "square"}, "quadrilateral_set.class_count"),
        (GeometryGraphPaperShapeTypeCountTask, {"shape_type": "ellipse"}, "shape_set.class_count"),
        (GeometryGraphPaperPolygonConvexityCountTask, {"convexity_kind": "concave"}, "polygon_set.convexity_count"),
    ),
)
def test_geometry_graph_paper_count_split_tasks_track_query_ids(
    task_cls,
    params: dict[str, str],
    program_code: str,
) -> None:
    task = task_cls()
    out = task.generate(23021, params={**params, "object_count": 8}, max_attempts=40)
    trace = out.trace_payload
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert out.query_id == "single"
    assert out.scene_id == "graph_paper"
    assert trace["execution_trace"]["scene_id"] == "graph_paper"
    assert trace["execution_trace"]["query_id"] == "single"
    assert trace["execution_trace"]["program_code"] == program_code
    assert "source_task_id" not in trace["execution_trace"]


@pytest.mark.parametrize(
    ("task_cls", "query_id"),
    (
        (GeometryGraphPaperAreaExtremumLabelTask, "area_extremum"),
        (GeometryGraphPaperTriangleTypeCountTask, "triangle_type_count"),
    ),
)
def test_geometry_graph_paper_split_tasks_reject_legacy_query_ids(task_cls, query_id: str) -> None:
    task = task_cls()
    with pytest.raises(ValueError):
        task.generate(23051, params={"query_id": query_id}, max_attempts=20)


@pytest.mark.parametrize(
    ("scene_variant", "task_cls", "transform_rule", "expected_points"),
    (
        ("triangle", GeometryShapeGalleryTranslationMatchTask, "translation", 3),
        ("quadrilateral", GeometryShapeGalleryReflectionMatchTask, "reflection", 4),
        ("triangle", GeometryShapeGalleryRotationMatchTask, "rotation", 3),
    ),
)
def test_geometry_transformation_match_tracks_scene_and_query_ids(
    scene_variant: str,
    task_cls,
    transform_rule: str,
    expected_points: int,
) -> None:
    task = task_cls()
    out = task.generate(
        23061,
        params={"scene_variant": scene_variant},
        max_attempts=20,
    )
    trace = out.trace_payload
    assert out.answer_gt.type == "option_letter"
    assert out.annotation_gt.type == "point_set"
    assert len(out.annotation_gt.value) == expected_points
    assert out.query_id == "single"
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_id"] == "single"
    assert trace["execution_trace"]["transform_rule"] == transform_rule
    _assert_consolidated_probability_metadata(trace, scene_variant=scene_variant, query_id="single")
    assert trace["scene_ir"]["relations"]["winner_label"] == out.answer_gt.value
    if transform_rule == "rotation":
        assert trace["execution_trace"]["rotation_mode"]
    if transform_rule == "translation":
        assert trace["execution_trace"]["translation_vector"]


@pytest.mark.parametrize(
    ("scene_variant", "task_cls", "relation_rule", "target_count"),
    (
        ("triangle", GeometryShapeGalleryCongruentCountTask, "congruent", 2),
        ("quadrilateral", GeometryShapeGallerySimilarCountTask, "similar", 3),
        ("triangle", GeometryShapeGallerySimilarCountTask, "similar", 0),
        ("quadrilateral", GeometryShapeGalleryCongruentCountTask, "congruent", 5),
    ),
)
def test_geometry_similarity_count_tracks_scene_and_query_ids(
    scene_variant: str,
    task_cls,
    relation_rule: str,
    target_count: int,
) -> None:
    task = task_cls()
    out = task.generate(
        23071,
        params={
            "scene_variant": scene_variant,
            "target_count": target_count,
        },
        max_attempts=30,
    )
    trace = out.trace_payload
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == int(target_count)
    assert len(out.annotation_gt.value) == int(target_count)
    assert out.query_id == "single"
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_id"] == "single"
    assert trace["execution_trace"]["relation_rule"] == relation_rule
    assert trace["execution_trace"]["target_count"] == target_count
    _assert_consolidated_probability_metadata(trace, scene_variant=scene_variant, query_id="single")
    assert (
        trace["witness_symbolic"]["label_set"]
        == trace["scene_ir"]["relations"]["matching_labels"]
    )
    assert trace["projected_annotation"]["bbox_set"] == list(out.annotation_gt.value)


def test_geometry_transformation_match_balances_winner_labels_across_review_seed_stream() -> (
    None
):
    per_rule_labels: dict[str, Counter[str]] = {
        "translation": Counter(),
        "reflection": Counter(),
        "rotation": Counter(),
    }
    collected_counts = {key: 0 for key in per_rule_labels}

    for rule in sorted(per_rule_labels):
        for index in range(10_000):
            if int(collected_counts[rule]) >= 100:
                break
            instance_seed = hash64(0, f"geometry_transformation_match_base.{rule}", index)
            resolved = _resolve_transform_axes(int(instance_seed), params={"transform_rule": rule})
            collected_counts[rule] += 1
            per_rule_labels[rule][str(resolved.winner_label)] += 1

    assert collected_counts == {
        "translation": 100,
        "reflection": 100,
        "rotation": 100,
    }
    for rule, counts in per_rule_labels.items():
        assert set(counts.keys()) == {"A", "B", "C", "D", "E", "F"}
        assert max(counts.values()) <= 30, rule


def test_geometry_transformation_match_decouplesseeded_sampler_axes() -> None:
    per_rule_labels: dict[str, Counter[str]] = {
        "translation": Counter(),
        "reflection": Counter(),
        "rotation": Counter(),
    }
    per_variant_scenes: dict[str, Counter[str]] = {
        "translation": Counter(),
        "reflection": Counter(),
        "rotation": Counter(),
    }

    for rule in sorted(per_rule_labels):
        for index in range(100):
            instance_seed = hash64(0, f"geometry_transformation_match_base.{rule}", index)
            resolved = _resolve_transform_axes(int(instance_seed), params={"transform_rule": rule})
            per_rule_labels[rule][str(resolved.winner_label)] += 1
            per_variant_scenes[rule][str(resolved.scene_variant)] += 1

    assert sum(sum(counter.values()) for counter in per_rule_labels.values()) == 300
    for rule, counts in per_rule_labels.items():
        assert set(counts.keys()) == {"A", "B", "C", "D", "E", "F"}
        assert max(counts.values()) <= 30, rule
        assert set(per_variant_scenes[rule].keys()) == {
            "triangle",
            "quadrilateral",
        }


def test_geometry_similarity_count_balances_target_counts_across_review_seed_stream() -> (
    None
):
    per_rule_counts: dict[str, Counter[int]] = {
        "congruent": Counter(),
        "similar": Counter(),
    }
    collected_counts = {key: 0 for key in per_rule_counts}

    for rule in sorted(per_rule_counts):
        for index in range(10_000):
            if int(collected_counts[rule]) >= 100:
                break
            instance_seed = hash64(0, f"geometry_similarity_count_base.{rule}", index)
            resolved = _resolve_relation_axes(int(instance_seed), params={"relation_rule": rule})
            collected_counts[rule] += 1
            per_rule_counts[rule][int(resolved.target_count)] += 1

    assert collected_counts == {
        "congruent": 100,
        "similar": 100,
    }
    for rule, counts in per_rule_counts.items():
        assert set(counts.keys()) == {0, 1, 2, 3, 4, 5}
        assert max(counts.values()) <= 25, rule


def test_geometry_similarity_count_decouplesseeded_sampler_axes() -> None:
    per_rule_counts: dict[str, Counter[int]] = {
        "congruent": Counter(),
        "similar": Counter(),
    }
    per_variant_scenes: dict[str, Counter[str]] = {
        "congruent": Counter(),
        "similar": Counter(),
    }
    combos: Counter[tuple[str, str, int]] = Counter()

    for rule in sorted(per_rule_counts):
        for index in range(100):
            instance_seed = hash64(0, f"geometry_similarity_count_base.{rule}", index)
            resolved = _resolve_relation_axes(int(instance_seed), params={"relation_rule": rule})
            scene_variant = str(resolved.scene_variant)
            target_count = int(resolved.target_count)
            per_rule_counts[rule][target_count] += 1
            per_variant_scenes[rule][scene_variant] += 1
            combos[(rule, scene_variant, target_count)] += 1

    assert all(sum(counter.values()) == 100 for counter in per_rule_counts.values())
    for rule, counts in per_rule_counts.items():
        assert set(counts.keys()) == {0, 1, 2, 3, 4, 5}
        assert max(counts.values()) <= 25, rule
        assert set(per_variant_scenes[rule].keys()) == {
            "triangle",
            "quadrilateral",
        }
    assert len(combos) >= 22


@pytest.mark.parametrize(
    ("task_cls", "params", "scene_variant", "query_id", "answer_type", "annotation_type"),
    (
        (GeometryCoordinateSegmentRelationCountTask, {"query_id": "parallel_count", "target_count": 2}, "segment_set", "parallel_count", "integer", "segment_set"),
        (GeometryCoordinateSegmentRelationCountTask, {"query_id": "perpendicular_count", "target_count": 2}, "segment_set", "perpendicular_count", "integer", "segment_set"),
        (GeometryCoordinateCollinearPointCountTask, {"target_count": 2}, "line_points", "single", "integer", "point_set"),
        (GeometryCoordinateSameQuadrantPointCountTask, {"target_count": 2}, "quadrant_points", "single", "integer", "point_set"),
        (GeometryCoordinatePointInPolygonCountTask, {"target_count": 4}, "polygon_lattice", "single", "integer", "point_set"),
    ),
)
def test_geometry_coordinate_relation_tracks_scene_and_query_ids(
    task_cls,
    params: dict[str, object],
    scene_variant: str,
    query_id: str,
    answer_type: str,
    annotation_type: str,
) -> None:
    task = task_cls()
    out = task.generate(23081, params=params, max_attempts=30)
    trace = out.trace_payload
    assert out.answer_gt.type == answer_type
    assert out.annotation_gt.type == annotation_type
    assert out.query_id == query_id
    assert trace["execution_trace"]["scene_variant"] == scene_variant
    assert trace["execution_trace"]["query_id"] == query_id
    _assert_consolidated_probability_metadata(trace, scene_variant=scene_variant, query_id=query_id)


def test_geometry_coordinate_split_tasks_reject_legacy_scene_variant_routing() -> None:
    task = GeometryCoordinateSegmentRelationCountTask()
    with pytest.raises(ValueError):
        task.generate(23091, params={"scene_variant": "line_points", "query_id": "collinear_count"}, max_attempts=20)
