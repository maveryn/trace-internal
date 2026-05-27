"""Contracts for trapezoid-completion geometry tasks."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.measurement.trapezoid_extension import (
    SCENE_ID,
    GeometryTrapezoidExtensionAreaValueTask,
    GeometryTrapezoidExtensionLengthValueTask,
)

TASK_CLASSES = (
    GeometryTrapezoidExtensionLengthValueTask,
    GeometryTrapezoidExtensionAreaValueTask,
)

QUERY_IDS_BY_TASK = {
    GeometryTrapezoidExtensionLengthValueTask: (
        "extension_from_parallelogram_area",
        "extension_from_parallelogram_perimeter",
    ),
    GeometryTrapezoidExtensionAreaValueTask: (
        "trapezoid_area_from_bases_and_height",
        "trapezoid_area_from_extension_and_height",
        "trapezoid_area_from_parallelogram_area",
    ),
}


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_trapezoid_extension_tasks_emit_public_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(64001, params={}, max_attempts=20)

    assert out.scene_id == SCENE_ID
    assert out.query_id == "default"
    assert out.query_id in QUERY_IDS_BY_TASK[task_cls]
    assert out.answer_gt.type == "number"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 4
    assert "Evidence format:" in out.prompt_variants["answer_and_evidence"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["scene_id"] == SCENE_ID
    assert trace["scene_ir"]["scene_id"] == SCENE_ID
    assert trace["witness_symbolic"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["query_id"] == "default"
    assert trace["query_spec"]["query_id"] == out.query_id
    assert trace["execution_trace"]["query_id"] == out.query_id
    assert trace["projected_evidence"]["type"] == "bbox_set"

    top_base = int(trace["execution_trace"]["top_base"])
    extension = int(trace["execution_trace"]["extension"])
    bottom_base = int(trace["execution_trace"]["bottom_base"])
    height = int(trace["execution_trace"]["height"])
    side = int(trace["execution_trace"]["side"])
    parallelogram_area = int(trace["execution_trace"]["parallelogram_area"])
    parallelogram_perimeter = int(trace["execution_trace"]["parallelogram_perimeter"])
    trapezoid_area = float(trace["execution_trace"]["trapezoid_area"])

    assert bottom_base == top_base + extension
    assert parallelogram_area == bottom_base * height
    assert parallelogram_perimeter == 2 * (bottom_base + side)
    assert trapezoid_area == pytest.approx((top_base + bottom_base) * height / 2.0)
    if task_cls is GeometryTrapezoidExtensionLengthValueTask:
        assert out.answer_gt.value == pytest.approx(float(extension))
    else:
        assert out.answer_gt.value == pytest.approx(trapezoid_area)


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_trapezoid_extension_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    params = {}
    out_a = task.generate(64011, params=params, max_attempts=20)
    out_b = task.generate(64011, params=params, max_attempts=20)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.evidence_gt == out_b.evidence_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_trapezoid_extension_tasks_support_every_explicit_query(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            64021 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        assert out.query_id == query_id
        assert out.answer_gt.type == "number"
        assert out.trace_payload["query_spec"]["params"][
            "query_id_probabilities"
        ] == {query_id: 1.0}


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_trapezoid_extension_tasks_sample_all_query_ids(task_cls) -> None:
    task = task_cls()
    seen = set()
    for index in range(18):
        out = task.generate(
            64041 + index,
            params={"_sampling_index": index},
            max_attempts=20,
        )
        seen.add(out.query_id)

    assert seen == set(QUERY_IDS_BY_TASK[task_cls])


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_trapezoid_extension_evidence_stays_inside_canvas(task_cls) -> None:
    task = task_cls()
    for index, query_id in enumerate(QUERY_IDS_BY_TASK[task_cls]):
        out = task.generate(
            64061 + index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        width, height = out.image.size
        for x0, y0, x1, y1 in out.evidence_gt.value:
            assert 0.0 <= x0 < x1 <= float(width)
            assert 0.0 <= y0 < y1 <= float(height)
            assert (x1 - x0) > 8.0
            assert (y1 - y0) > 8.0


def test_trapezoid_extension_tasks_reject_unknown_query_id() -> None:
    for task_cls in TASK_CLASSES:
        task = task_cls()
        with pytest.raises(ValueError):
            task.generate(64031, params={"query_id": "not_a_query"}, max_attempts=20)
