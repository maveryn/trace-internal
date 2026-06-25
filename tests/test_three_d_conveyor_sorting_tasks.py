"""Tests for synthetic 3D conveyor sorting tasks."""

from __future__ import annotations

from pathlib import Path

from trace.core import task_review_distribution
from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks import create_task
from trace.tasks.three_d.conveyor_sorting.belt_total_object_count import (
    QUERY_ID as TOTAL_QUERY_ID,
    TASK_ID as TOTAL_TASK_ID,
)
from trace.tasks.three_d.conveyor_sorting.scoped_belt_object_count import (
    COLOR_QUERY_ID,
    OBJECT_TYPE_QUERY_ID,
    TASK_ID as SCOPED_TASK_ID,
)
from tests.three_d_canvas_helpers import assert_three_d_canvas_contract


def _assert_count_output(output, *, expected_query_id: str) -> None:
    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    target_ids = [str(object_id) for object_id in trace["target_object_ids"]]

    assert output.scene_id == "conveyor_sorting"
    assert output.query_id == expected_query_id
    assert output.answer_gt.type == "integer"
    assert output.annotation_gt.type == "bbox_set"
    assert int(output.answer_gt.value) == len(target_ids)
    assert len(output.annotation_gt.value) == len(target_ids)
    assert output.annotation_gt.value == [render_map["object_bboxes_px"][object_id] for object_id in target_ids]
    assert output.trace_payload["projected_annotation"]["bbox_set"] == output.annotation_gt.value
    assert output.trace_payload["projected_annotation"]["pixel_bbox_set"] == output.annotation_gt.value
    assert trace["layout_family"] == "elliptical_carousel"
    assert trace["target_belt_key"] in {"inner", "outer"}
    assert trace["target_belt_label"] in {"INNER", "OUTER"}
    assert trace["target_belt_object_ids"]
    assert set(render_map["belt_bboxes_px"]) == {"inner", "outer"}
    assert len({str(spec["shape_type"]) for spec in trace["object_specs"]}) == 1
    assert "{target_" not in output.prompt
    assert "unlettered" not in output.prompt.lower()
    assert "segment" not in output.prompt.lower()
    assert_three_d_canvas_contract(output)

    image_w, image_h = output.image.size
    for bbox in output.annotation_gt.value:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        assert 0.0 <= x0 < x1 <= float(image_w)
        assert 0.0 <= y0 < y1 <= float(image_h)
        assert min(x1 - x0, y1 - y0) >= 24.0


def test_conveyor_sorting_scoped_belt_count_query_ids() -> None:
    task = create_task(SCOPED_TASK_ID)
    cases = (
        (OBJECT_TYPE_QUERY_ID, 2026062401),
        (COLOR_QUERY_ID, 2026062402),
    )
    for query_id, seed in cases:
        output = task.generate(
            seed,
            params={"query_id": query_id, "post_image_noise_apply_prob": 0.0},
            max_attempts=120,
        )
        _assert_count_output(output, expected_query_id=query_id)


def test_conveyor_sorting_belt_total_count_uses_belt_specific_support() -> None:
    task = create_task(TOTAL_TASK_ID)
    cases = (
        ("inner", 8, 2026062501),
        ("outer", 12, 2026062502),
    )
    for belt_key, target_count, seed in cases:
        output = task.generate(
            seed,
            params={
                "target_belt_key": belt_key,
                "target_count": target_count,
                "post_image_noise_apply_prob": 0.0,
            },
            max_attempts=120,
        )
        trace = output.trace_payload["execution_trace"]
        render_map = output.trace_payload["render_map"]
        target_ids = [str(object_id) for object_id in trace["target_object_ids"]]

        assert output.scene_id == "conveyor_sorting"
        assert output.query_id == SINGLE_QUERY_ID
        assert output.trace_payload["query_spec"]["internal_query_id"] == TOTAL_QUERY_ID
        replay_row = task_review_distribution.random_collector(output, seed)
        assert replay_row["generation_params"]["query_id"] == SINGLE_QUERY_ID
        assert replay_row["generation_params"]["internal_query_id"] == TOTAL_QUERY_ID
        assert output.answer_gt.type == "integer"
        assert output.annotation_gt.type == "bbox_set"
        assert trace["target_belt_key"] == belt_key
        assert trace["predicate_kind"] == "belt_total"
        assert int(output.answer_gt.value) == int(target_count)
        assert int(output.answer_gt.value) == len(target_ids)
        assert target_ids == trace["target_belt_object_ids"]
        assert output.annotation_gt.value == [render_map["object_bboxes_px"][object_id] for object_id in target_ids]
        assert len({str(spec["shape_type"]) for spec in trace["object_specs"]}) == 1
        assert len({str(spec["color_name"]) for spec in trace["object_specs"]}) >= 2
        assert "{target_" not in output.prompt
        assert "color" not in output.prompt.lower()
        assert "type" not in output.prompt.lower()
        assert_three_d_canvas_contract(output)

        image_w, image_h = output.image.size
        for bbox in output.annotation_gt.value:
            x0, y0, x1, y1 = [float(value) for value in bbox]
            assert 0.0 <= x0 < x1 <= float(image_w)
            assert 0.0 <= y0 < y1 <= float(image_h)
            assert min(x1 - x0, y1 - y0) >= 24.0


def test_conveyor_sorting_renderer_has_no_unqueried_gate_decoration() -> None:
    source = Path("trace/tasks/three_d/conveyor_sorting/shared/rendering.py").read_text()

    assert "inspection_gate" not in source
    assert "three_d_conveyor_inspection_gate" not in source
