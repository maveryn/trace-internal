"""Contracts for curvilinear composite geometry tasks."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.composite_shape.missing_width_from_semicircle_cap_area import GeometryMissingWidthFromSemicircleCapAreaTask
from trace.tasks.geometry.composite_shape.missing_width_from_semicircle_cutout_area import GeometryMissingWidthFromSemicircleCutoutAreaTask
from trace.tasks.geometry.composite_shape.rectangle_quarter_sector_cutout_area import GeometryRectangleQuarterSectorCutoutAreaTask
from trace.tasks.geometry.composite_shape.shared.defaults import SCENE_ID
from trace.tasks.geometry.composite_shape.shared.measurements import round1, semicircle_arc_length
from trace.tasks.geometry.composite_shape.rectangle_quarter_sector_cutout_perimeter import GeometryRectangleQuarterSectorCutoutPerimeterTask
from trace.tasks.geometry.composite_shape.rectangle_semicircle_cap_area import GeometryRectangleSemicircleCapAreaTask
from trace.tasks.geometry.composite_shape.rectangle_semicircle_cap_perimeter import GeometryRectangleSemicircleCapPerimeterTask
from trace.tasks.geometry.composite_shape.rectangle_semicircle_cutout_area import GeometryRectangleSemicircleCutoutAreaTask
from trace.tasks.geometry.composite_shape.rectangle_semicircle_cutout_perimeter import GeometryRectangleSemicircleCutoutPerimeterTask
from trace.tasks.geometry.composite_shape.sector_angle_from_arc_length import GeometrySectorAngleFromArcLengthTask
from trace.tasks.geometry.composite_shape.sector_angle_from_area import GeometrySectorAngleFromAreaTask


TASK_CLASSES = (
    GeometryRectangleSemicircleCapAreaTask,
    GeometryRectangleSemicircleCutoutAreaTask,
    GeometryRectangleQuarterSectorCutoutAreaTask,
    GeometryRectangleSemicircleCapPerimeterTask,
    GeometryRectangleSemicircleCutoutPerimeterTask,
    GeometryRectangleQuarterSectorCutoutPerimeterTask,
    GeometryMissingWidthFromSemicircleCapAreaTask,
    GeometryMissingWidthFromSemicircleCutoutAreaTask,
    GeometrySectorAngleFromArcLengthTask,
    GeometrySectorAngleFromAreaTask,
)

QUERY_IDS_BY_TASK = {
    GeometryRectangleSemicircleCapAreaTask: ("single",),
    GeometryRectangleSemicircleCutoutAreaTask: ("single",),
    GeometryRectangleQuarterSectorCutoutAreaTask: ("single",),
    GeometryRectangleSemicircleCapPerimeterTask: ("single",),
    GeometryRectangleSemicircleCutoutPerimeterTask: ("single",),
    GeometryRectangleQuarterSectorCutoutPerimeterTask: ("single",),
    GeometryMissingWidthFromSemicircleCapAreaTask: ("single",),
    GeometryMissingWidthFromSemicircleCutoutAreaTask: ("single",),
    GeometrySectorAngleFromArcLengthTask: ("single",),
    GeometrySectorAngleFromAreaTask: ("single",),
}

INTERNAL_QUERY_ID_BY_TASK = {
    GeometryRectangleSemicircleCapAreaTask: "rectangle_semicircle_cap_area",
    GeometryRectangleSemicircleCutoutAreaTask: "rectangle_semicircle_cutout_area",
    GeometryRectangleQuarterSectorCutoutAreaTask: "rectangle_quarter_sector_cutout_area",
    GeometryRectangleSemicircleCapPerimeterTask: "rectangle_semicircle_cap_perimeter",
    GeometryRectangleSemicircleCutoutPerimeterTask: "rectangle_semicircle_cutout_perimeter",
    GeometryRectangleQuarterSectorCutoutPerimeterTask: "rectangle_quarter_sector_cutout_perimeter",
    GeometryMissingWidthFromSemicircleCapAreaTask: "missing_width_from_semicircle_cap_area",
    GeometryMissingWidthFromSemicircleCutoutAreaTask: "missing_width_from_semicircle_cutout_area",
    GeometrySectorAngleFromArcLengthTask: "sector_angle_from_arc_length",
    GeometrySectorAngleFromAreaTask: "sector_angle_from_area",
}

EXPECTED_ANNOTATION_KEYS_BY_TASK = {
    GeometryRectangleSemicircleCapAreaTask: {"A", "B", "C", "D", "O"},
    GeometryRectangleSemicircleCutoutAreaTask: {"A", "B", "C", "D", "O"},
    GeometryRectangleQuarterSectorCutoutAreaTask: {"A", "B", "C", "D", "E", "F"},
    GeometryRectangleSemicircleCapPerimeterTask: {"A", "B", "C", "D", "O"},
    GeometryRectangleSemicircleCutoutPerimeterTask: {"A", "B", "C", "D", "O"},
    GeometryRectangleQuarterSectorCutoutPerimeterTask: {"A", "B", "C", "D", "E", "F"},
    GeometryMissingWidthFromSemicircleCapAreaTask: {"A", "B", "C", "D", "O"},
    GeometryMissingWidthFromSemicircleCutoutAreaTask: {"A", "B", "C", "D", "O"},
    GeometrySectorAngleFromArcLengthTask: {"O", "A", "B"},
    GeometrySectorAngleFromAreaTask: {"O", "A", "B"},
}


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_curvilinear_tasks_emit_public_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(54001, params={}, max_attempts=20)

    assert out.scene_id == SCENE_ID
    assert out.query_id
    assert out.answer_gt.type == "number"
    assert out.annotation_gt.type == "keyed_point_map"
    assert set(out.annotation_gt.value) == EXPECTED_ANNOTATION_KEYS_BY_TASK[task_cls]
    assert "Annotation format:" in out.prompt_variants["answer_and_annotation"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["query_id"] == out.query_id
    assert trace["execution_trace"]["query_id"] == out.query_id
    assert trace["projected_annotation"]["type"] == out.annotation_gt.type


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_curvilinear_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    params = {}
    out_a = task.generate(54011, params=params, max_attempts=20)
    out_b = task.generate(54011, params=params, max_attempts=20)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_curvilinear_tasks_support_every_explicit_query(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            54021 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        assert out.query_id == query_id
        assert out.trace_payload["query_spec"]["params"]["internal_query_id"] == INTERNAL_QUERY_ID_BY_TASK[task_cls]
        assert out.answer_gt.type == "number"
        assert out.trace_payload["query_spec"]["params"]["query_id_probabilities"] == {
            query_id: 1.0
        }


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_curvilinear_annotation_stays_inside_canvas(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            54041 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        width, height = out.image.size
        assert out.annotation_gt.type == "keyed_point_map"
        assert set(out.annotation_gt.value) == EXPECTED_ANNOTATION_KEYS_BY_TASK[task_cls]
        for x, y in out.annotation_gt.value.values():
            assert 0.0 <= x <= float(width)
            assert 0.0 <= y <= float(height)


def test_curvilinear_tasks_reject_unknown_query_id() -> None:
    task = GeometryRectangleSemicircleCapAreaTask()
    with pytest.raises(ValueError):
        task.generate(54031, params={"query_id": "not_a_query"}, max_attempts=20)


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_curvilinear_public_annotation_avoids_measurement_label_boxes(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(54061 + index, params={"query_id": query_id}, max_attempts=20)
        assert out.trace_payload["projected_annotation"]["type"] == out.annotation_gt.type
        assert out.trace_payload["projected_annotation"]["keyed_point_map"] == out.annotation_gt.value
        assert out.trace_payload["projected_annotation"]["pixel_keyed_point_map"] == out.annotation_gt.value
        assert set(out.annotation_gt.value) == set(out.trace_payload["execution_trace"]["annotation_roles"])
        assert set(out.annotation_gt.value) == EXPECTED_ANNOTATION_KEYS_BY_TASK[task_cls]
        assert all("label" not in str(role) for role in out.trace_payload["execution_trace"]["annotation_roles"])
        assert "support_roles" in out.trace_payload["render_map"]
        assert set(out.trace_payload["render_map"]["point_label_bboxes"]) == set(out.annotation_gt.value)


def test_quarter_sector_area_omits_obvious_right_angle_label() -> None:
    task = GeometryRectangleQuarterSectorCutoutAreaTask()
    out = task.generate(
        54091,
        params={"query_id": "single"},
        max_attempts=20,
    )

    assert "angle_label" not in out.trace_payload["render_map"]["support_roles"]
    assert set(out.trace_payload["render_map"]["visual_notation_bboxes"]) == {
        "top_left_right_angle",
        "bottom_left_right_angle",
        "bottom_right_right_angle",
        "quarter_sector_right_angle",
    }
    assert "quarter_sector_right_angle" not in out.annotation_gt.value


@pytest.mark.parametrize(
    "task_cls",
    (
        GeometryRectangleSemicircleCapAreaTask,
        GeometryRectangleSemicircleCutoutAreaTask,
        GeometryRectangleSemicircleCapPerimeterTask,
        GeometryRectangleSemicircleCutoutPerimeterTask,
        GeometryMissingWidthFromSemicircleCapAreaTask,
        GeometryMissingWidthFromSemicircleCutoutAreaTask,
    ),
)
def test_semicircle_rectangle_variants_show_all_four_right_angle_markers(task_cls) -> None:
    task = task_cls()
    out = task.generate(
        54095,
        params={"query_id": "single", "width_units": 12, "height_units": 14, "radius_units": 4},
        max_attempts=20,
    )

    assert set(out.trace_payload["render_map"]["visual_notation_bboxes"]) >= {
        "top_left_right_angle",
        "top_right_right_angle",
        "bottom_right_right_angle",
        "bottom_left_right_angle",
    }


@pytest.mark.parametrize(
    "task_cls",
    (
        GeometryRectangleSemicircleCapPerimeterTask,
        GeometryRectangleSemicircleCutoutPerimeterTask,
    ),
)
def test_semicircle_perimeter_includes_right_side_remainders(task_cls) -> None:
    task = task_cls()
    width_units = 12
    height_units = 14
    radius_units = 4
    out = task.generate(
        54097,
        params={
            "query_id": "single",
            "width_units": width_units,
            "height_units": height_units,
            "radius_units": radius_units,
        },
        max_attempts=20,
    )
    expected = round1(
        (2.0 * float(width_units))
        + (2.0 * float(height_units))
        - (2.0 * float(radius_units))
        + semicircle_arc_length(radius_units)
    )

    assert out.answer_gt.value == expected
    assert out.trace_payload["execution_trace"]["straight_boundary_length"] == round1(
        (2.0 * float(width_units))
        + (2.0 * float(height_units))
        - (2.0 * float(radius_units))
    )


def test_curvilinear_perimeter_omits_derived_boundary_total_labels() -> None:
    for task_cls in (
        GeometryRectangleSemicircleCapPerimeterTask,
        GeometryRectangleSemicircleCutoutPerimeterTask,
        GeometryRectangleQuarterSectorCutoutPerimeterTask,
    ):
        task = task_cls()
        query_id = QUERY_IDS_BY_TASK[task_cls][0]
        out = task.generate(
            54101,
            params={"query_id": query_id},
            max_attempts=20,
        )
        support_roles = set(out.trace_payload["render_map"]["support_roles"])

        assert "arc_length_label" not in support_roles
        assert "straight_boundary_length_label" not in support_roles


def test_curvilinear_perimeter_prompts_name_curve_type() -> None:
    expected_terms = {
        GeometryRectangleSemicircleCapPerimeterTask: ("semicircle",),
        GeometryRectangleSemicircleCutoutPerimeterTask: ("semicircle",),
        GeometryRectangleQuarterSectorCutoutPerimeterTask: ("quarter", "circle"),
    }

    for task_cls, terms in expected_terms.items():
        task = task_cls()
        query_id = QUERY_IDS_BY_TASK[task_cls][0]
        out = task.generate(
            54111,
            params={"query_id": query_id},
            max_attempts=20,
        )
        prompt = str(out.prompt).lower()

        assert all(term in prompt for term in terms)
