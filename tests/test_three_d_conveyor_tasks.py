"""Tests for synthetic 3D straight conveyor tasks."""

from __future__ import annotations

from trace.core import task_review_distribution
from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks import create_task
from trace.tasks.three_d.conveyor.belt_total_object_count import (
    QUERY_ID as TOTAL_QUERY_ID,
    TASK_ID as TOTAL_TASK_ID,
)
from trace.tasks.three_d.conveyor.scoped_belt_object_count import (
    COLOR_QUERY_ID,
    OBJECT_TYPE_QUERY_ID,
    TASK_ID as SCOPED_TASK_ID,
)
from trace.tasks.three_d.conveyor.scoped_color_type_count import (
    TASK_ID as COLOR_TYPE_TASK_ID,
)
from trace.tasks.three_d.conveyor.shared.state import CONVEYOR_OBJECT_SHAPE_TYPES
from trace.tasks.three_d.shared.object_confusions import confusable_shape_names
from trace.tasks.three_d.shared.semantic_colors import confusable_color_names
from tests.three_d_canvas_helpers import assert_three_d_canvas_contract


def test_conveyor_object_pool_excludes_cylinder_confusers() -> None:
    assert "cylinder" in CONVEYOR_OBJECT_SHAPE_TYPES
    assert "drum" not in CONVEYOR_OBJECT_SHAPE_TYPES
    assert "pencil" not in CONVEYOR_OBJECT_SHAPE_TYPES
    assert "ruler" not in CONVEYOR_OBJECT_SHAPE_TYPES


def _assert_count_output(output) -> None:
    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    target_ids = [str(object_id) for object_id in trace["target_object_ids"]]
    predicate_kind = str(trace["predicate_kind"])
    expected_query_id_by_predicate = {
        "belt_total": SINGLE_QUERY_ID,
        "object_type": OBJECT_TYPE_QUERY_ID,
        "color": COLOR_QUERY_ID,
        "color_type": SINGLE_QUERY_ID,
    }
    expected_internal_query_id_by_predicate = {
        "belt_total": TOTAL_QUERY_ID,
        "object_type": OBJECT_TYPE_QUERY_ID,
        "color": COLOR_QUERY_ID,
        "color_type": SINGLE_QUERY_ID,
    }

    assert output.scene_id == "conveyor"
    assert output.query_id == expected_query_id_by_predicate[predicate_kind]
    assert output.trace_payload["query_spec"]["internal_query_id"] == expected_internal_query_id_by_predicate[predicate_kind]
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
    if predicate_kind == "belt_total":
        assert target_ids == trace["target_lane_object_ids"]
    else:
        assert set(target_ids).issubset(set(str(object_id) for object_id in trace["target_lane_object_ids"]))
    assert set(render_map["belt_bboxes_px"]) in (
        {"top", "middle", "bottom"},
        {"left", "middle", "right"},
    )
    if predicate_kind == "belt_total":
        assert len({str(spec["shape_type"]) for spec in trace["object_specs"]}) == 1
    assert trace["target_shape_type"] not in {"pencil", "ruler"}
    assert len({str(spec["color_name"]) for spec in trace["object_specs"]}) >= 2
    assert "{target_" not in output.prompt
    if predicate_kind == "belt_total":
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
    conveyor_bbox = [float(value) for value in render_map["conveyor_bbox_px"]]
    if trace["layout_orientation"] == "horizontal_lanes":
        assert (conveyor_bbox[2] - conveyor_bbox[0]) / float(image_w) >= 0.78
    else:
        assert (conveyor_bbox[3] - conveyor_bbox[1]) / float(image_h) >= 0.62
    if predicate_kind == "object_type":
        same_lane_distractors = [
            spec
            for spec in trace["object_specs"]
            if str(spec["lane_key"]) == str(trace["target_lane_key"]) and not bool(spec["matches_query"])
        ]
        assert same_lane_distractors
        assert any(str(spec["shape_type"]) != str(trace["target_shape_type"]) for spec in same_lane_distractors)
    if predicate_kind == "color":
        same_lane_distractors = [
            spec
            for spec in trace["object_specs"]
            if str(spec["lane_key"]) == str(trace["target_lane_key"]) and not bool(spec["matches_query"])
        ]
        assert same_lane_distractors
        assert any(str(spec["color_name"]) != str(trace["target_color_name"]) for spec in same_lane_distractors)
    assert max(int(value) for value in trace["lane_counts"].values()) <= 8


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


def test_conveyor_scoped_belt_count_query_ids() -> None:
    task = create_task(SCOPED_TASK_ID)
    cases = (
        (OBJECT_TYPE_QUERY_ID, 2026062581),
        (COLOR_QUERY_ID, 2026062582),
    )
    for query_id, seed in cases:
        output = task.generate(
            seed,
            params={"query_id": query_id, "post_image_noise_apply_prob": 0.0},
            max_attempts=120,
        )
        _assert_count_output(output)
        assert output.query_id == query_id
        assert 0 <= int(output.answer_gt.value) <= 5


def test_conveyor_scoped_belt_count_supports_zero_and_five() -> None:
    task = create_task(SCOPED_TASK_ID)
    cases = (
        (OBJECT_TYPE_QUERY_ID, "landscape", "top", 0, 2026062583),
        (OBJECT_TYPE_QUERY_ID, "portrait", "left", 5, 2026062585),
        (COLOR_QUERY_ID, "landscape", "middle", 0, 2026062585),
        (COLOR_QUERY_ID, "portrait", "right", 5, 2026062586),
    )
    for query_id, canvas_preset, lane_key, target_count, seed in cases:
        output = task.generate(
            seed,
            params={
                "query_id": query_id,
                "canvas_preset": canvas_preset,
                "target_lane_key": lane_key,
                "target_count": target_count,
                "post_image_noise_apply_prob": 0.0,
            },
            max_attempts=120,
        )
        _assert_count_output(output)
        assert output.query_id == query_id
        assert int(output.answer_gt.value) == int(target_count)
        if int(target_count) == 0:
            assert output.annotation_gt.value == []


def test_conveyor_scoped_color_type_count_uses_conjunction_distractors() -> None:
    task = create_task(COLOR_TYPE_TASK_ID)
    cases = (
        ({"canvas_preset": "landscape", "target_lane_key": "top", "target_count": 0}, 2026062603),
        ({"canvas_preset": "portrait", "target_lane_key": "left", "target_count": 5}, 2026062604),
    )
    for params, seed in cases:
        output = task.generate(
            seed,
            params={**params, "post_image_noise_apply_prob": 0.0},
            max_attempts=120,
        )
        _assert_count_output(output)
        trace = output.trace_payload["execution_trace"]
        target_ids = [str(object_id) for object_id in trace["target_object_ids"]]
        target_shape = str(trace["target_shape_type"])
        target_color = str(trace["target_color_name"])
        target_lane = str(trace["target_lane_key"])
        confusable_shapes = set(confusable_shape_names(target_shape))

        assert trace["predicate_kind"] == "color_type"
        assert int(output.answer_gt.value) == int(params["target_count"])
        assert len(target_ids) == int(params["target_count"])
        assert output.trace_payload["query_spec"]["internal_query_id"] == SINGLE_QUERY_ID
        for spec in trace["object_specs"]:
            is_target = str(spec["object_id"]) in set(target_ids)
            if is_target:
                assert str(spec["lane_key"]) == target_lane
                assert str(spec["shape_type"]) == target_shape
                assert str(spec["color_name"]) == target_color
        same_lane_roles = {
            str(spec["count_role"])
            for spec in trace["object_specs"]
            if str(spec["lane_key"]) == target_lane and not bool(spec["matches_query"])
        }
        assert all(
            str(spec["shape_type"]) not in confusable_shapes
            for spec in trace["object_specs"]
            if str(spec["shape_type"]) != target_shape
        )
        assert "same_belt_same_color_wrong_type" in same_lane_roles
        assert "same_belt_same_type_wrong_color" in same_lane_roles
        assert any(
            str(spec["lane_key"]) != target_lane
            and str(spec["shape_type"]) == target_shape
            and str(spec["color_name"]) == target_color
            for spec in trace["object_specs"]
        )
        if int(params["target_count"]) == 0:
            assert output.annotation_gt.value == []


def test_conveyor_color_type_distractors_avoid_visually_confusable_shapes() -> None:
    output = create_task(COLOR_TYPE_TASK_ID).generate(
        2026062622,
        params={
            "canvas_preset": "landscape",
            "target_lane_key": "top",
            "target_shape_type": "card",
            "target_color_name": "red",
            "target_count": 3,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=120,
    )
    trace = output.trace_payload["execution_trace"]
    confusable_shapes = set(confusable_shape_names("card"))

    assert trace["target_shape_type"] == "card"
    assert trace["target_color_name"] == "red"
    assert all(
        str(spec["shape_type"]) not in confusable_shapes
        for spec in trace["object_specs"]
        if str(spec["shape_type"]) != "card"
    )


def test_conveyor_color_readout_excludes_target_confusable_colors() -> None:
    cases = (
        (SCOPED_TASK_ID, {"query_id": COLOR_QUERY_ID, "target_color_name": "red"}, 2026062613),
        (COLOR_TYPE_TASK_ID, {"target_color_name": "red"}, 2026062614),
    )
    for task_id, params, seed in cases:
        output = create_task(task_id).generate(
            seed,
            params={**params, "post_image_noise_apply_prob": 0.0},
            max_attempts=120,
        )
        trace = output.trace_payload["execution_trace"]
        colors = {str(spec["color_name"]) for spec in trace["object_specs"]}
        assert str(trace["target_color_name"]) == "red"
        assert colors.isdisjoint(set(confusable_color_names("red")))


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
