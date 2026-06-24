"""Contracts for sector formula geometry tasks."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.sector.arc_length_value import GeometrySectorArcLengthValueTask
from trace.tasks.geometry.sector.related_angle_value import GeometrySectorRelatedAngleValueTask
from trace.tasks.geometry.sector.sector_angle_value import GeometrySectorAngleValueTask
from trace.tasks.geometry.sector.sector_area_value import GeometrySectorAreaValueTask


SCENE_ID = "sector"

TASK_CLASSES = (
    GeometrySectorAreaValueTask,
    GeometrySectorArcLengthValueTask,
    GeometrySectorAngleValueTask,
    GeometrySectorRelatedAngleValueTask,
)

QUERY_IDS_BY_TASK = {
    GeometrySectorAreaValueTask: (
        "area_from_arc_length_and_radius",
        "area_from_radius_and_complement_angle",
    ),
    GeometrySectorArcLengthValueTask: (
        "arc_length_from_area_and_radius",
        "arc_length_from_radius_and_supplement_angle",
    ),
    GeometrySectorAngleValueTask: (
        "angle_from_arc_length_and_radius",
        "angle_from_area_and_radius",
    ),
    GeometrySectorRelatedAngleValueTask: (
        "complement_angle_from_arc_length",
        "supplement_angle_from_area",
        "remaining_angle_from_sector_measure",
    ),
}

EXPECTED_ANNOTATION_KEYS = {
    "area_from_arc_length_and_radius": {"target_sector_region", "radius_label", "arc_length_label"},
    "area_from_radius_and_complement_angle": {"target_sector_region", "radius_label", "angle_relation_label"},
    "arc_length_from_area_and_radius": {"target_arc", "radius_label", "sector_area_label"},
    "arc_length_from_radius_and_supplement_angle": {"target_arc", "radius_label", "angle_relation_label"},
    "angle_from_arc_length_and_radius": {"target_angle_cue", "radius_label", "arc_length_label"},
    "angle_from_area_and_radius": {"target_angle_cue", "radius_label", "sector_area_label"},
    "complement_angle_from_arc_length": {
        "target_related_angle_cue",
        "radius_label",
        "arc_length_label",
        "angle_relation_label",
    },
    "supplement_angle_from_area": {
        "target_related_angle_cue",
        "radius_label",
        "sector_area_label",
        "angle_relation_label",
    },
    "remaining_angle_from_sector_measure": {
        "target_related_angle_cue",
        "radius_label",
        "arc_length_label",
        "angle_relation_label",
    },
}

RETIRED_TASK_IDS = {
    "task_geometry__sector__angle_from_sector_measure_angle_from_arc_length_and_radius",
    "task_geometry__sector__angle_from_sector_measure_angle_from_area_and_radius",
    "task_geometry__sector__arc_length_value_arc_length_from_area_and_radius",
    "task_geometry__sector__arc_length_value_arc_length_from_radius_and_supplement_angle",
    "task_geometry__sector__related_angle_from_sector_measure_complement_angle_from_arc_length",
    "task_geometry__sector__related_angle_from_sector_measure_remaining_angle_from_sector_measure",
    "task_geometry__sector__related_angle_from_sector_measure_supplement_angle_from_area",
    "task_geometry__sector__sector_area_value_area_from_arc_length_and_radius",
    "task_geometry__sector__sector_area_value_area_from_radius_and_complement_angle",
}


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_sector_formula_tasks_emit_public_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(55001, params={}, max_attempts=20)

    assert out.scene_id == SCENE_ID
    assert out.query_id in QUERY_IDS_BY_TASK[task_cls]
    assert out.answer_gt.type == "number"
    assert out.annotation_gt.type == "bbox_map"
    assert set(out.annotation_gt.value) == EXPECTED_ANNOTATION_KEYS[out.query_id]
    assert "Annotation format:" in out.prompt_variants["answer_and_annotation"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["params"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["query_id"] == out.query_id
    assert trace["execution_trace"]["query_id"] == out.query_id
    assert trace["projected_annotation"]["type"] == "bbox_map"
    assert trace["projected_annotation"]["bbox_map"] == out.annotation_gt.value


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_sector_formula_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    params = {}
    out_a = task.generate(55011, params=params, max_attempts=20)
    out_b = task.generate(55011, params=params, max_attempts=20)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_sector_formula_tasks_support_every_explicit_query(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            55021 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        assert out.query_id == query_id
        assert out.answer_gt.type == "number"
        assert set(out.annotation_gt.value) == EXPECTED_ANNOTATION_KEYS[query_id]
        probabilities = out.trace_payload["query_spec"]["params"]["query_id_probabilities"]
        assert probabilities[query_id] == 1.0
        assert all(float(value) == 0.0 for key, value in probabilities.items() if key != query_id)


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_sector_formula_annotation_stays_inside_canvas(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            55041 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        width, height = out.image.size
        for bbox in out.annotation_gt.value.values():
            x0, y0, x1, y1 = bbox
            assert 0.0 <= x0 < x1 <= float(width)
            assert 0.0 <= y0 < y1 <= float(height)
            assert (x1 - x0) > 8.0
            assert (y1 - y0) > 8.0


def test_sector_formula_tasks_reject_unknown_query_id() -> None:
    task = GeometrySectorAreaValueTask()
    with pytest.raises(ValueError):
        task.generate(55031, params={"query_id": "not_a_query"}, max_attempts=20)


def test_sector_formula_retired_public_ids_are_not_registered() -> None:
    from trace.tasks.registry import TASK_REGISTRY, ensure_scene_tasks_registered

    ensure_scene_tasks_registered("geometry", SCENE_ID)
    for task_id in RETIRED_TASK_IDS:
        assert task_id not in TASK_REGISTRY
