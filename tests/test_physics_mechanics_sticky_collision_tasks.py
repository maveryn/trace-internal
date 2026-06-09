"""Contract tests for physics mechanics sticky-collision tasks."""

from __future__ import annotations

import math
from collections import Counter

from trace.tasks.physics.mechanics.sticky_collision import (
    PhysicsMechanicsStickyCollisionDirectionChoiceTask,
    PhysicsMechanicsStickyCollisionVelocityComponentValueTask,
)


def test_physics_mechanics_sticky_collision_direction_choice_contract() -> None:
    out = PhysicsMechanicsStickyCollisionDirectionChoiceTask().generate(
        41001,
        params={
            "scene_variant": "wide_table",
            "target_answer": "D",
            "horizontal_mass": 2,
            "vertical_mass": 2,
            "horizontal_speed": 8,
            "vertical_speed": 6,
            "horizontal_direction": "right",
            "vertical_direction": "up",
        },
        max_attempts=30,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    scenario = execution["scenario"]


    assert out.answer_gt.type == "option_letter"

    assert out.answer_gt.value == "D"

    assert out.annotation_gt.type == "keyed_point_map"

    assert set(out.annotation_gt.value) == {"A", "B", "A+B"}

    assert out.query_id == "direction_choice"
    assert trace["query_spec"]["query_id"] == "direction_choice"

    assert trace["query_spec"]["params"]["internal_query_id"] == "direction_choice"
    assert execution["query_id"] == "direction_choice"

    assert execution["internal_query_id"] == "direction_choice"

    assert scenario["correct_option_letter"] == "D"

    assert execution["annotation_entity_ids"] == [
        "horizontal_puck",
        "vertical_puck",
        "stuck_pucks",
    ]
    assert execution["annotation_key_by_entity_id"] == {
        "horizontal_puck": "A",
        "vertical_puck": "B",
        "stuck_pucks": "A+B",
    }
    assert trace["projected_annotation"]["keyed_point_map"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_keyed_point_map"] == out.annotation_gt.value

    assert "resultant_arrow_bbox_px" not in trace["render_map"]

    assert int(scenario["final_vx"]) == 4

    assert int(scenario["final_vy"]) == 3

    assert math.isclose(float(scenario["direction_angle_degrees"]), math.degrees(math.atan2(3, 4)), abs_tol=0.01)


def test_physics_mechanics_sticky_collision_component_contracts() -> None:
    base_params = {
        "scene_variant": "gridded_table",
        "horizontal_mass": 2,
        "vertical_mass": 2,
        "horizontal_speed": 8,
        "vertical_speed": 6,
        "horizontal_direction": "left",
        "vertical_direction": "down",
        "correct_option_letter": "F",
    }
    component_task = PhysicsMechanicsStickyCollisionVelocityComponentValueTask()
    horizontal = component_task.generate(
        41011,
        params={**base_params, "component_axis": "x", "target_answer": -4},
        max_attempts=30,
    )
    vertical = component_task.generate(
        41012,
        params={**base_params, "component_axis": "y", "target_answer": -3},
        max_attempts=30,
    )


    assert horizontal.answer_gt.type == "integer"

    assert int(horizontal.answer_gt.value) == -4

    assert horizontal.query_id == "velocity_component"

    assert horizontal.annotation_gt.type == "keyed_point_map"

    assert set(horizontal.annotation_gt.value) == {"A", "B", "A+B"}

    assert horizontal.trace_payload["execution_trace"]["component_axis"] == "x"

    assert horizontal.trace_payload["execution_trace"]["annotation_entity_ids"] == [
        "horizontal_puck",
        "vertical_puck",
        "stuck_pucks",
    ]
    assert horizontal.trace_payload["projected_annotation"]["keyed_point_map"] == horizontal.annotation_gt.value

    assert int(horizontal.trace_payload["execution_trace"]["final_vx"]) == -4

    assert int(horizontal.trace_payload["execution_trace"]["final_vy"]) == -3


    assert vertical.answer_gt.type == "integer"

    assert int(vertical.answer_gt.value) == -3

    assert vertical.query_id == "velocity_component"

    assert vertical.annotation_gt.type == "keyed_point_map"

    assert set(vertical.annotation_gt.value) == {"A", "B", "A+B"}

    assert vertical.trace_payload["execution_trace"]["component_axis"] == "y"

    assert vertical.trace_payload["execution_trace"]["annotation_entity_ids"] == [
        "horizontal_puck",
        "vertical_puck",
        "stuck_pucks",
    ]
    assert vertical.trace_payload["projected_annotation"]["keyed_point_map"] == vertical.annotation_gt.value

    assert int(vertical.trace_payload["execution_trace"]["final_vx"]) == -4

    assert int(vertical.trace_payload["execution_trace"]["final_vy"]) == -3


def test_physics_mechanics_sticky_collision_is_deterministic() -> None:
    params = {
        "scene_variant": "compact_table",
        "component_axis": "x",
        "target_answer": 5,
        "correct_option_letter": "C",
        "accent_color_name": "cyan",
    }
    task = PhysicsMechanicsStickyCollisionVelocityComponentValueTask()
    out_a = task.generate(41021, params=params, max_attempts=60)
    out_b = task.generate(41021, params=params, max_attempts=60)


    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()

    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()

    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]

    assert out_a.prompt == out_b.prompt

    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_physics_mechanics_sticky_collision_sampling_covers_answers() -> None:
    direction_letters: Counter[str] = Counter()
    component_values: set[int] = set()
    component_axes: Counter[str] = Counter()
    for sampling_index in range(96):
        direction = PhysicsMechanicsStickyCollisionDirectionChoiceTask().generate(
            41100 + sampling_index,
            params={},
            max_attempts=80,
        )
        component = PhysicsMechanicsStickyCollisionVelocityComponentValueTask().generate(
            41200 + sampling_index,
            params={},
            max_attempts=80,
        )
        direction_letters[str(direction.answer_gt.value)] += 1
        component_values.add(int(component.answer_gt.value))
        component_axes[str(component.trace_payload["execution_trace"]["component_axis"])] += 1


    assert set(direction_letters) == {"A", "B", "C", "D", "E", "F"}

    assert component_values == {-6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6}

    assert set(component_axes) == {"x", "y"}
