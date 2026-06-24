"""Contracts for trapezoid-completion geometry tasks."""

from __future__ import annotations

import pytest

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.geometry.trapezoid_extension.extension_from_parallelogram_area import (
    GeometryTrapezoidExtensionFromParallelogramAreaTask,
)
from trace.tasks.geometry.trapezoid_extension.extension_from_parallelogram_perimeter import (
    GeometryTrapezoidExtensionFromParallelogramPerimeterTask,
)
from trace.tasks.geometry.trapezoid_extension.trapezoid_area_from_bases_and_height import (
    GeometryTrapezoidAreaFromBasesAndHeightTask,
)
from trace.tasks.geometry.trapezoid_extension.trapezoid_area_from_extension_and_height import (
    GeometryTrapezoidAreaFromExtensionAndHeightTask,
)
from trace.tasks.geometry.trapezoid_extension.trapezoid_area_from_parallelogram_area import (
    GeometryTrapezoidAreaFromParallelogramAreaTask,
)
from trace.tasks.geometry.trapezoid_extension.shared.state import SCENE_ID

TASK_CLASSES = (
    GeometryTrapezoidExtensionFromParallelogramAreaTask,
    GeometryTrapezoidExtensionFromParallelogramPerimeterTask,
    GeometryTrapezoidAreaFromBasesAndHeightTask,
    GeometryTrapezoidAreaFromExtensionAndHeightTask,
    GeometryTrapezoidAreaFromParallelogramAreaTask,
)

ANNOTATION_KEYS = {
    "target_cue",
    "original_trapezoid",
    "dashed_parallelogram_completion",
    "supporting_visible_labels",
}


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_trapezoid_extension_tasks_emit_public_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(64001, params={}, max_attempts=20)

    assert out.scene_id == SCENE_ID
    assert out.query_id == SINGLE_QUERY_ID
    assert out.answer_gt.type == "number"
    assert out.annotation_gt.type == "bbox_map"
    assert set(out.annotation_gt.value) == ANNOTATION_KEYS
    assert "Annotation format:" in out.prompt_variants["answer_and_annotation"]
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["scene_id"] == SCENE_ID
    assert trace["scene_ir"]["scene_id"] == SCENE_ID
    assert trace["witness_symbolic"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["query_id"] == SINGLE_QUERY_ID
    assert trace["execution_trace"]["query_id"] == SINGLE_QUERY_ID
    assert trace["projected_annotation"]["type"] == "bbox_map"
    assert trace["query_spec"]["prompt_variant"]["prompt_schema_version"] == "v1"

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
    if task_cls is GeometryTrapezoidExtensionFromParallelogramAreaTask:
        assert out.answer_gt.value == pytest.approx(parallelogram_area / height - top_base)
    elif task_cls is GeometryTrapezoidExtensionFromParallelogramPerimeterTask:
        assert out.answer_gt.value == pytest.approx(parallelogram_perimeter / 2.0 - side - top_base)
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
    assert out_a.annotation_gt == out_b.annotation_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_trapezoid_extension_tasks_support_explicit_single_query(task_cls) -> None:
    task = task_cls()
    for param_key in ("query_id", "query_variant"):
        out = task.generate(
            64021,
            params={param_key: SINGLE_QUERY_ID},
            max_attempts=20,
        )
        assert out.query_id == SINGLE_QUERY_ID
        assert out.answer_gt.type == "number"
        assert out.trace_payload["query_spec"]["params"]["query_id_probabilities"] == {SINGLE_QUERY_ID: 1.0}


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_trapezoid_extension_annotation_stays_inside_canvas(task_cls) -> None:
    task = task_cls()
    out = task.generate(64061, params={"query_id": SINGLE_QUERY_ID}, max_attempts=20)
    width, height = out.image.size
    for x0, y0, x1, y1 in out.annotation_gt.value.values():
        assert 0.0 <= x0 < x1 <= float(width)
        assert 0.0 <= y0 < y1 <= float(height)
        assert (x1 - x0) > 8.0
        assert (y1 - y0) > 8.0


def test_trapezoid_extension_tasks_reject_unknown_query_id() -> None:
    for task_cls in TASK_CLASSES:
        task = task_cls()
        with pytest.raises(ValueError):
            task.generate(64031, params={"query_id": "not_a_query"}, max_attempts=20)
