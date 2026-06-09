"""Contract tests for physics motion-graph tasks."""

from __future__ import annotations

import trace.tasks  # noqa: F401
from trace.tasks.physics.mechanics.motion_graph import (
    PhysicsMotionGraphIntervalDisplacementValueTask,
    PhysicsMotionGraphSpeedChangeStateChoiceTask,
    PhysicsMotionGraphVelocitySignChoiceTask,
)


def _assert_keyed_bbox_map_in_bounds(out) -> None:
    width, height = out.image.size
    assert out.annotation_gt.type == "keyed_bbox_map"
    for bbox in out.annotation_gt.value.values():
        assert 0 <= bbox[0] < bbox[2] <= width
        assert 0 <= bbox[1] < bbox[3] <= height


def _bbox_overlaps(left, right) -> bool:
    return not (
        float(left[2]) <= float(right[0])
        or float(left[0]) >= float(right[2])
        or float(left[3]) <= float(right[1])
        or float(left[1]) >= float(right[3])
    )


def test_motion_graph_velocity_sign_choice_contract() -> None:
    task = PhysicsMotionGraphVelocitySignChoiceTask()

    for state in ["moving_right", "moving_left", "stationary"]:
        out = task.generate(
            93011,
            params={
                "query_id": "velocity_sign_choice",
                "motion_state": state,
                "correct_option_letter": "C",
            },
            max_attempts=10,
        )
        execution = out.trace_payload["execution_trace"]
        segment = execution["target_segment"]

        assert out.scene_id == "motion_graph"
        assert out.query_id == "velocity_sign_choice"
        assert out.answer_gt.type == "option_letter"
        assert out.answer_gt.value == "C"
        assert execution["graph_kind"] == "position_time"
        assert execution["option_map"][out.answer_gt.value] == state
        assert set(out.annotation_gt.value) == {"query_region", "curve_segment"}
        _assert_keyed_bbox_map_in_bounds(out)
        assert out.trace_payload["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value

        delta = int(segment["y_end"]) - int(segment["y_start"])
        if state == "moving_right":
            assert delta > 0
        elif state == "moving_left":
            assert delta < 0
        else:
            assert delta == 0


def test_motion_graph_speed_change_state_choice_contract() -> None:
    task = PhysicsMotionGraphSpeedChangeStateChoiceTask()

    for state in ["speeding_up", "slowing_down", "constant_speed"]:
        out = task.generate(
            93021,
            params={
                "query_id": "speed_change_state_choice",
                "motion_state": state,
                "correct_option_letter": "A",
            },
            max_attempts=10,
        )
        execution = out.trace_payload["execution_trace"]
        segment = execution["target_segment"]
        y_start = int(segment["y_start"])
        y_end = int(segment["y_end"])

        assert out.scene_id == "motion_graph"
        assert out.query_id == "speed_change_state_choice"
        assert out.answer_gt.type == "option_letter"
        assert out.answer_gt.value == "A"
        assert execution["graph_kind"] == "velocity_time"
        assert execution["option_map"][out.answer_gt.value] == state
        assert set(out.annotation_gt.value) == {"query_region", "curve_segment"}
        _assert_keyed_bbox_map_in_bounds(out)

        if state == "speeding_up":
            assert abs(y_end) > abs(y_start)
        elif state == "slowing_down":
            assert abs(y_end) < abs(y_start)
        else:
            assert abs(y_end) == abs(y_start)
            assert y_start != 0


def test_motion_graph_options_are_visual_not_annotation() -> None:
    out = PhysicsMotionGraphSpeedChangeStateChoiceTask().generate(
        6486597898434820,
        params={
            "query_id": "speed_change_state_choice",
            "motion_state": "speeding_up",
            "correct_option_letter": "C",
        },
        max_attempts=10,
    )
    render_map = out.trace_payload["render_map"]

    assert set(render_map["option_map"]) == {"A", "B", "C", "D"}
    assert out.answer_gt.value in render_map["option_map"]
    assert set(render_map["option_letter_bboxes_px"]) == {"A", "B", "C", "D"}
    assert set(render_map["option_text_bboxes_px"]) == {"A", "B", "C", "D"}
    for letter in ("A", "B", "C", "D"):
        assert not _bbox_overlaps(render_map["option_letter_bboxes_px"][letter], render_map["option_text_bboxes_px"][letter])
    assert out.annotation_gt.value["curve_segment"] not in render_map["option_bboxes_px"].values()
    assert out.annotation_gt.value["query_region"] not in render_map["option_bboxes_px"].values()
    assert out.prompt_variants["answer_only"]
    assert out.prompt_variants["answer_and_annotation"]


def test_motion_graph_constant_velocity_interval_displacement_contract() -> None:
    out = PhysicsMotionGraphIntervalDisplacementValueTask().generate(
        95011,
        params={
            "query_id": "constant_velocity_interval_displacement",
            "t_start": 2,
            "t_end": 5,
            "v_start": 4,
            "v_end": 4,
            "post_image_noise": {"enabled": False},
        },
        max_attempts=10,
    )
    execution = out.trace_payload["execution_trace"]

    assert out.scene_id == "motion_graph"
    assert out.query_id == "constant_velocity_interval_displacement"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 12
    assert set(out.annotation_gt.value) == {"marked_interval", "velocity_segment", "axis_scale"}
    _assert_keyed_bbox_map_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert execution["area_formula"] == "v * delta_t"
    assert execution["delta_t_s"] == 3
    assert execution["v_start_m_s"] == execution["v_end_m_s"] == 4
    assert execution["displacement_m"] == out.answer_gt.value


def test_motion_graph_constant_acceleration_interval_displacement_contract() -> None:
    out = PhysicsMotionGraphIntervalDisplacementValueTask().generate(
        95021,
        params={
            "query_id": "constant_acceleration_interval_displacement",
            "t_start": 2,
            "t_end": 6,
            "v_start": 2,
            "v_end": 6,
            "post_image_noise": {"enabled": False},
        },
        max_attempts=10,
    )
    execution = out.trace_payload["execution_trace"]

    assert out.scene_id == "motion_graph"
    assert out.query_id == "constant_acceleration_interval_displacement"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 16
    assert set(out.annotation_gt.value) == {"marked_interval", "velocity_segment", "axis_scale"}
    _assert_keyed_bbox_map_in_bounds(out)
    assert execution["area_formula"] == "((v_start + v_end) / 2) * delta_t"
    assert execution["delta_t_s"] == 4
    assert execution["v_start_m_s"] == 2
    assert execution["v_end_m_s"] == 6
    assert execution["displacement_m"] == out.answer_gt.value


def test_motion_graph_interval_displacement_is_deterministic() -> None:
    params = {
        "query_id": "constant_acceleration_interval_displacement",
        "scene_variant": "bold_grid",
        "post_image_noise": {"enabled": False},
    }
    task = PhysicsMotionGraphIntervalDisplacementValueTask()
    out_a = task.generate(95031, params=params, max_attempts=10)
    out_b = task.generate(95031, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
