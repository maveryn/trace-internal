"""Contracts for direct solid-formula geometry tasks."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.solid_formula.cylinder_cone_height_from_volume_radius import (
    SCENE_ID,
    GeometrySolidFormulaCylinderConeHeightFromVolumeRadiusTask,
)
from trace.tasks.geometry.solid_formula.cylinder_cone_radius_from_volume_heights import (
    GeometrySolidFormulaCylinderConeRadiusFromVolumeHeightsTask,
)
from trace.tasks.geometry.solid_formula.house_prism_length_from_volume import (
    GeometrySolidFormulaHousePrismLengthFromVolumeTask,
)
from trace.tasks.geometry.solid_formula.prism_pyramid_height_from_volume import (
    GeometrySolidFormulaPrismPyramidHeightFromVolumeTask,
)

TASK_CLASSES = (
    GeometrySolidFormulaCylinderConeRadiusFromVolumeHeightsTask,
    GeometrySolidFormulaCylinderConeHeightFromVolumeRadiusTask,
    GeometrySolidFormulaPrismPyramidHeightFromVolumeTask,
    GeometrySolidFormulaHousePrismLengthFromVolumeTask,
)

ANNOTATION_KEYS_BY_TASK = {
    GeometrySolidFormulaCylinderConeRadiusFromVolumeHeightsTask: {
        "target_radius_label",
        "volume_label",
        "total_height_label",
        "cone_height_label",
    },
    GeometrySolidFormulaCylinderConeHeightFromVolumeRadiusTask: {
        "target_cylinder_height_label",
        "volume_label",
        "radius_label",
        "cone_height_label",
    },
    GeometrySolidFormulaPrismPyramidHeightFromVolumeTask: {
        "target_prism_height_label",
        "volume_label",
        "known_length_label",
        "known_width_label",
        "pyramid_height_label",
    },
    GeometrySolidFormulaHousePrismLengthFromVolumeTask: {
        "target_length_label",
        "volume_label",
        "triangle_base_label",
        "wall_height_label",
        "roof_height_label",
    },
}


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_solid_formula_tasks_emit_public_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(64001, params={}, max_attempts=20)

    assert out.scene_id == SCENE_ID
    assert out.query_id == "single"
    assert out.answer_gt.type == "number"
    assert out.annotation_gt.type == "bbox_map"
    assert set(out.annotation_gt.value) == ANNOTATION_KEYS_BY_TASK[task_cls]
    assert "Annotation format:" in out.prompt_variants["answer_and_annotation"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["query_id"] == "single"
    assert trace["execution_trace"]["query_id"] == "single"
    assert trace["projected_annotation"]["type"] == "bbox_map"
    assert trace["execution_trace"]["answer_rounding"] == "one_decimal"
    assert trace["query_spec"]["prompt_variant"]["prompt_schema_version"] == "v1"
    assert trace["execution_trace"]["answer_support_size"] >= 50


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_solid_formula_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    params = {}
    out_a = task.generate(64011, params=params, max_attempts=20)
    out_b = task.generate(64011, params=params, max_attempts=20)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert (
        out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    )
    assert out_a.image.tobytes() == out_b.image.tobytes()


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_solid_formula_tasks_support_single_query(task_cls) -> None:
    task = task_cls()
    out = task.generate(64021, params={"query_id": "single"}, max_attempts=20)
    trace = out.trace_payload["execution_trace"]
    assert out.query_id == "single"
    assert out.answer_gt.type == "number"
    assert out.trace_payload["query_spec"]["params"]["query_id_probabilities"] == {
        "single": 1.0
    }

    if task_cls is GeometrySolidFormulaCylinderConeRadiusFromVolumeHeightsTask:
        radius = float(trace["radius"])
        total_height = float(trace["total_height"])
        cone_height = float(trace["cone_height"])
        cylinder_height = float(trace["cylinder_height"])
        assert total_height == pytest.approx(cylinder_height + cone_height)
        assert trace["volume_pi_multiple"] == pytest.approx(
            radius**2 * (cylinder_height + (cone_height / 3.0))
        )
        assert out.answer_gt.value == pytest.approx(radius)
    elif task_cls is GeometrySolidFormulaCylinderConeHeightFromVolumeRadiusTask:
        radius = float(trace["radius"])
        cylinder_height = float(trace["cylinder_height"])
        cone_height = float(trace["cone_height"])
        assert trace["volume_pi_multiple"] == pytest.approx(
            radius**2 * (cylinder_height + (cone_height / 3.0))
        )
        assert out.answer_gt.value == pytest.approx(cylinder_height)
    elif task_cls is GeometrySolidFormulaPrismPyramidHeightFromVolumeTask:
        side_a = float(trace["side_a"])
        side_b = float(trace["side_b"])
        prism_height = float(trace["prism_height"])
        pyramid_height = float(trace["pyramid_height"])
        assert trace["volume"] == pytest.approx(
            side_a * side_b * (prism_height + (pyramid_height / 3.0))
        )
        assert out.answer_gt.value == pytest.approx(prism_height)
    elif task_cls is GeometrySolidFormulaHousePrismLengthFromVolumeTask:
        triangle_base = float(trace["triangle_base"])
        wall_height = float(trace["wall_height"])
        roof_height = float(trace["roof_height"])
        prism_length = float(trace["prism_length"])
        assert trace["volume"] == pytest.approx(
            ((triangle_base * wall_height) + (0.5 * triangle_base * roof_height))
            * prism_length
        )
        assert out.answer_gt.value == pytest.approx(prism_length)


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_solid_formula_annotation_stays_inside_canvas(task_cls) -> None:
    task = task_cls()
    out = task.generate(64041, params={"query_id": "single"}, max_attempts=20)
    width, height = out.image.size
    for x0, y0, x1, y1 in out.annotation_gt.value.values():
        assert 0.0 <= x0 < x1 <= float(width)
        assert 0.0 <= y0 < y1 <= float(height)
        assert (x1 - x0) > 8.0
        assert (y1 - y0) > 8.0


def test_solid_formula_tasks_reject_unknown_query_id() -> None:
    task = GeometrySolidFormulaCylinderConeRadiusFromVolumeHeightsTask()
    with pytest.raises(ValueError):
        task.generate(64031, params={"query_id": "not_a_query"}, max_attempts=20)
