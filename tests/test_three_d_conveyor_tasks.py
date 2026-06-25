"""Tests for synthetic 3D straight conveyor tasks."""

from __future__ import annotations

from trace.core import task_review_distribution
from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks import create_task
from trace.tasks.three_d.conveyor.belt_total_object_count import (
    QUERY_ID as TOTAL_QUERY_ID,
    TASK_ID as TOTAL_TASK_ID,
)
from tests.three_d_canvas_helpers import assert_three_d_canvas_contract


def _assert_count_output(output) -> None:
    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    target_ids = [str(object_id) for object_id in trace["target_object_ids"]]

    assert output.scene_id == "conveyor"
    assert output.query_id == SINGLE_QUERY_ID
    assert output.trace_payload["query_spec"]["internal_query_id"] == TOTAL_QUERY_ID
    assert output.answer_gt.type == "integer"
    assert output.annotation_gt.type == "bbox_set"
    assert int(output.answer_gt.value) == len(target_ids)
    assert len(output.annotation_gt.value) == len(target_ids)
    assert output.annotation_gt.value == [render_map["object_bboxes_px"][object_id] for object_id in target_ids]
    assert output.trace_payload["projected_annotation"]["bbox_set"] == output.annotation_gt.value
    assert output.trace_payload["projected_annotation"]["pixel_bbox_set"] == output.annotation_gt.value
    assert trace["layout_family"] == "straight_parallel_conveyors"
    assert trace["layout_orientation"] in {"horizontal_lanes", "vertical_lanes"}
    assert trace["target_lane_key"] in {"top", "middle", "bottom", "left", "right"}
    assert trace["target_lane_label"] in {"TOP", "MIDDLE", "BOTTOM", "LEFT", "RIGHT"}
    assert target_ids == trace["target_lane_object_ids"]
    assert set(render_map["belt_bboxes_px"]) in (
        {"top", "middle", "bottom"},
        {"left", "middle", "right"},
    )
    assert len({str(spec["shape_type"]) for spec in trace["object_specs"]}) == 1
    assert len({str(spec["color_name"]) for spec in trace["object_specs"]}) >= 2
    assert "{target_" not in output.prompt
    assert "color" not in output.prompt.lower()
    assert "type" not in output.prompt.lower()
    assert "unlettered" not in output.prompt.lower()
    assert_three_d_canvas_contract(output)

    image_w, image_h = output.image.size
    for bbox in output.annotation_gt.value:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        assert 0.0 <= x0 < x1 <= float(image_w)
        assert 0.0 <= y0 < y1 <= float(image_h)
        assert min(x1 - x0, y1 - y0) >= 24.0


def test_conveyor_belt_total_count_uses_lane_positions() -> None:
    task = create_task(TOTAL_TASK_ID)
    cases = (
        ({"canvas_preset": "landscape", "target_lane_key": "top", "target_count": 8}, 2026062503),
        ({"canvas_preset": "portrait", "target_lane_key": "left", "target_count": 8}, 2026062504),
        ({"canvas_preset": "square", "layout_orientation": "horizontal_lanes", "target_lane_key": "bottom", "target_count": 5}, 2026062505),
        ({"canvas_preset": "square", "layout_orientation": "vertical_lanes", "target_lane_key": "right", "target_count": 6}, 2026062506),
    )
    for params, seed in cases:
        output = task.generate(
            seed,
            params={**params, "post_image_noise_apply_prob": 0.0},
            max_attempts=120,
        )
        _assert_count_output(output)
        assert int(output.answer_gt.value) == int(params["target_count"])
        trace = output.trace_payload["execution_trace"]
        if params["canvas_preset"] == "landscape":
            assert trace["layout_orientation"] == "horizontal_lanes"
        if params["canvas_preset"] == "portrait":
            assert trace["layout_orientation"] == "vertical_lanes"


def test_conveyor_sampled_canvas_orientation_follows_long_axis() -> None:
    task = create_task(TOTAL_TASK_ID)
    seen_presets = set()
    for seed in range(2026062510, 2026062570):
        output = task.generate(
            seed,
            params={"post_image_noise_apply_prob": 0.0},
            max_attempts=120,
        )
        _assert_count_output(output)
        render_spec = output.trace_payload["render_spec"]
        trace = output.trace_payload["execution_trace"]
        width = int(render_spec["scene_canvas_width"])
        height = int(render_spec["scene_canvas_height"])
        seen_presets.add(str(render_spec["scene_canvas_preset"]))
        if width > height:
            assert trace["layout_orientation"] == "horizontal_lanes"
        elif height > width:
            assert trace["layout_orientation"] == "vertical_lanes"
        else:
            assert trace["layout_orientation"] in {"horizontal_lanes", "vertical_lanes"}
        if {"landscape", "portrait", "square"}.issubset(seen_presets):
            break
    assert {"landscape", "portrait", "square"}.issubset(seen_presets)


def test_conveyor_non_square_canvas_ignores_conflicting_layout_orientation() -> None:
    task = create_task(TOTAL_TASK_ID)
    cases = (
        (
            {
                "canvas_preset": "portrait",
                "layout_orientation": "horizontal_lanes",
                "target_lane_key": "left",
                "post_image_noise_apply_prob": 0.0,
            },
            "vertical_lanes",
        ),
        (
            {
                "canvas_preset": "landscape",
                "layout_orientation": "vertical_lanes",
                "target_lane_key": "top",
                "post_image_noise_apply_prob": 0.0,
            },
            "horizontal_lanes",
        ),
    )
    for params, expected_orientation in cases:
        output = task.generate(
            2026062571,
            params=dict(params),
            max_attempts=120,
        )
        _assert_count_output(output)
        assert output.trace_payload["execution_trace"]["layout_orientation"] == expected_orientation


def test_conveyor_replay_uses_single_public_query_id() -> None:
    task = create_task(TOTAL_TASK_ID)
    output = task.generate(
        2026062507,
        params={"post_image_noise_apply_prob": 0.0},
        max_attempts=120,
    )
    replay_row = task_review_distribution.random_collector(output, 2026062507)
    assert replay_row["generation_params"]["query_id"] == SINGLE_QUERY_ID
    assert replay_row["generation_params"]["internal_query_id"] == TOTAL_QUERY_ID
