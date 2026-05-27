"""Contracts for direct solid-formula geometry tasks."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.measurement.solid_formula import (
    SCENE_ID,
    GeometrySolidFormulaMissingDimensionValueTask,
)

TASK_CLASSES = (GeometrySolidFormulaMissingDimensionValueTask,)

QUERY_IDS_BY_TASK = {
    GeometrySolidFormulaMissingDimensionValueTask: (
        "cylinder_cone_radius_from_volume_heights",
        "cylinder_cone_height_from_volume_radius",
        "prism_pyramid_height_from_volume",
        "house_prism_length_from_volume",
    ),
}


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_solid_formula_tasks_emit_public_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(64001, params={}, max_attempts=20)

    assert out.scene_id == SCENE_ID
    assert out.query_variant == "default"
    assert out.query_id
    assert out.answer_gt.type == "number"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) in {4, 5}
    assert "Evidence format:" in out.prompt_variants["answer_and_evidence"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["query_variant"] == "default"
    assert trace["query_spec"]["query_id"] == out.query_id
    assert trace["execution_trace"]["query_id"] == out.query_id
    assert trace["projected_evidence"]["type"] == "bbox_set"
    assert trace["execution_trace"]["answer_rounding"] == "one_decimal"


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_solid_formula_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    params = {}
    out_a = task.generate(64011, params=params, max_attempts=20)
    out_b = task.generate(64011, params=params, max_attempts=20)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.evidence_gt == out_b.evidence_gt
    assert (
        out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    )
    assert out_a.image.tobytes() == out_b.image.tobytes()


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_solid_formula_tasks_support_every_explicit_query(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            64021 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        trace = out.trace_payload["execution_trace"]
        assert out.query_id == query_id
        assert out.answer_gt.type == "number"
        assert out.trace_payload["query_spec"]["params"][
            "query_variant_probabilities"
        ] == {query_id: 1.0}

        if query_id == "cylinder_cone_radius_from_volume_heights":
            radius = float(trace["radius"])
            cylinder_height = float(trace["cylinder_height"])
            cone_height = float(trace["cone_height"])
            assert trace["total_height"] == pytest.approx(cylinder_height + cone_height)
            assert trace["volume_pi_multiple"] == pytest.approx(
                radius**2 * (cylinder_height + (cone_height / 3.0))
            )
            assert out.answer_gt.value == pytest.approx(radius)
        elif query_id == "cylinder_cone_height_from_volume_radius":
            radius = float(trace["radius"])
            cylinder_height = float(trace["cylinder_height"])
            cone_height = float(trace["cone_height"])
            assert trace["volume_pi_multiple"] == pytest.approx(
                radius**2 * (cylinder_height + (cone_height / 3.0))
            )
            assert out.answer_gt.value == pytest.approx(cylinder_height)
        elif query_id == "prism_pyramid_height_from_volume":
            side_a = float(trace["side_a"])
            side_b = float(trace["side_b"])
            prism_height = float(trace["prism_height"])
            pyramid_height = float(trace["pyramid_height"])
            assert trace["volume"] == pytest.approx(
                side_a * side_b * (prism_height + (pyramid_height / 3.0))
            )
            assert out.answer_gt.value == pytest.approx(prism_height)
        elif query_id == "house_prism_length_from_volume":
            triangle_base = float(trace["triangle_base"])
            wall_height = float(trace["wall_height"])
            roof_height = float(trace["roof_height"])
            prism_length = float(trace["prism_length"])
            assert trace["volume"] == pytest.approx(
                (
                    (triangle_base * wall_height)
                    + (0.5 * triangle_base * roof_height)
                )
                * prism_length
            )
            assert out.answer_gt.value == pytest.approx(prism_length)


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_solid_formula_evidence_stays_inside_canvas(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            64041 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        width, height = out.image.size
        for x0, y0, x1, y1 in out.evidence_gt.value:
            assert 0.0 <= x0 < x1 <= float(width)
            assert 0.0 <= y0 < y1 <= float(height)
            assert (x1 - x0) > 8.0
            assert (y1 - y0) > 8.0


def test_solid_formula_tasks_reject_unknown_query_id() -> None:
    task = GeometrySolidFormulaMissingDimensionValueTask()
    with pytest.raises(ValueError):
        task.generate(64031, params={"query_id": "not_a_query"}, max_attempts=20)
