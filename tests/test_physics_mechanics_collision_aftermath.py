"""Contract tests for physics mechanics collision-aftermath cause task."""

from __future__ import annotations

from collections import Counter

from trace.tasks.physics.mechanics.collision_aftermath import (
    DIRECTION_NAMES,
    OPTION_LETTERS,
    PhysicsCollisionIncomingPathCauseChoiceTask,
    _option_directions,
)


def _assert_keyed_bbox_map_in_bounds(out) -> None:
    width, height = out.image.size
    assert out.annotation_gt.type == "keyed_bbox_map"
    for bbox in out.annotation_gt.value.values():
        assert 0 <= bbox[0] < bbox[2] <= width
        assert 0 <= bbox[1] < bbox[3] <= height


def test_collision_aftermath_contract_and_trace() -> None:
    out = PhysicsCollisionIncomingPathCauseChoiceTask().generate(
        93001,
        params={
            "scene_variant": "aftermath_table",
            "final_motion_direction": "northeast",
            "correct_option_letter": "D",
            "post_image_noise": {"enabled": False},
        },
        max_attempts=20,
    )
    trace = out.trace_payload
    scenario = trace["execution_trace"]["scenario"]

    assert out.scene_id == "collision"
    assert out.query_id == "incoming_path_cause_choice"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "D"
    assert set(out.annotation_gt.value) == {"impact_point", "target_after_motion"}
    _assert_keyed_bbox_map_in_bounds(out)
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_keyed_bbox_map"] == out.annotation_gt.value
    assert scenario["final_motion_direction"] == "northeast"
    assert scenario["correct_incoming_direction"] == "northeast"
    assert scenario["option_directions"]["D"] == "northeast"
    assert "option_D" not in out.annotation_gt.value
    assert out.prompt_variants["answer_only"]
    assert out.prompt_variants["answer_and_annotation"]


def test_collision_aftermath_option_distractors_are_non_adjacent() -> None:
    option_directions = _option_directions(
        instance_seed=93011,
        final_motion_direction="north",
        correct_option_letter="C",
    )
    correct_index = DIRECTION_NAMES.index("north")

    assert option_directions["C"] == "north"
    assert set(option_directions) == set(OPTION_LETTERS)
    assert len(set(option_directions.values())) == len(OPTION_LETTERS)
    for letter, direction in option_directions.items():
        if letter == "C":
            continue
        direction_index = DIRECTION_NAMES.index(direction)
        circular_delta = min(
            abs(direction_index - correct_index),
            len(DIRECTION_NAMES) - abs(direction_index - correct_index),
        )
        assert circular_delta >= 2


def test_collision_aftermath_is_deterministic() -> None:
    params = {
        "scene_variant": "aftermath_gridded_table",
        "final_motion_direction": "west",
        "correct_option_letter": "A",
        "accent_color_name": "cyan",
        "post_image_noise": {"enabled": False},
    }
    task = PhysicsCollisionIncomingPathCauseChoiceTask()
    out_a = task.generate(93021, params=params, max_attempts=20)
    out_b = task.generate(93021, params=params, max_attempts=20)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_collision_aftermath_sampling_covers_letters_and_directions() -> None:
    letters: Counter[str] = Counter()
    directions: Counter[str] = Counter()
    task = PhysicsCollisionIncomingPathCauseChoiceTask()
    for index in range(96):
        out = task.generate(93100 + index, params={}, max_attempts=20)
        letters[str(out.answer_gt.value)] += 1
        directions[str(out.trace_payload["execution_trace"]["final_motion_direction"])] += 1

    assert set(letters) == set(OPTION_LETTERS)
    assert set(directions) == set(DIRECTION_NAMES)
