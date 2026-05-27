"""Contract tests for physics electrostatics field-map tasks."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from trace.tasks.physics.electrostatics.field_map import (
    PhysicsElectrostaticsFieldDirectionChoiceTask,
    PhysicsElectrostaticsPotentialValueTask,
    PhysicsElectrostaticsZeroFieldPointLabelTask,
)


def test_physics_electrostatics_field_direction_choice_contract() -> None:
    out = PhysicsElectrostaticsFieldDirectionChoiceTask().generate(
        81001,
        params={
            "scene_variant": "clean_grid",
            "direction_mode": "force_on_negative_charge",
            "target_direction": "northwest",
            "correct_option_letter": "C",
            "accent_color_name": "blue",
        },
        max_attempts=30,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    scenario = execution["direction_scenario"]


    assert out.answer_gt.type == "option_letter"

    assert out.answer_gt.value == "C"

    assert out.evidence_gt.type == "bbox_set"

    assert len(out.evidence_gt.value) == 1

    assert out.query_variant == "default"

    assert out.scene_id == "electrostatic_field"

    assert out.query_id == "field_direction_choice"
    assert trace["query_spec"]["query_variant"] == "default"

    assert trace["query_spec"]["params"]["internal_query_variant"] == "field_direction_choice"

    assert execution["direction_mode"] == "force_on_negative_charge"

    assert scenario["requested_direction"] == "northwest"

    assert scenario["option_directions"]["C"] == "northwest"

    assert execution["evidence_entity_ids"] == ["option_C"]

    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value

    assert trace["render_spec"]["technical_diagram_style"]["kind"] == "technical_diagram_style"

    assert trace["render_spec"]["technical_diagram_style"]["protected_colors_rgb"]

    assert "labeled candidate direction arrows" in out.prompt

    assert "opposite the electric field" in out.prompt


def test_physics_electrostatics_zero_field_point_label_contract() -> None:
    out = PhysicsElectrostaticsZeroFieldPointLabelTask().generate(
        81002,
        params={
            "scene_variant": "paper_grid",
            "correct_option_letter": "E",
            "accent_color_name": "green",
        },
        max_attempts=30,
    )
    scenario = out.trace_payload["execution_trace"]["zero_field_scenario"]
    correct_points = [point for point in scenario["candidate_points"] if point["is_correct"]]
    correct = correct_points[0]
    field_x = 0.0
    field_y = 0.0
    for charge in scenario["charges"]:
        dx = int(correct["x"]) - int(charge["x"])
        dy = int(correct["y"]) - int(charge["y"])
        distance = float((dx * dx + dy * dy) ** 0.5)
        field_x += float(charge["charge_value"]) * float(dx) / float(distance**3)
        field_y += float(charge["charge_value"]) * float(dy) / float(distance**3)
    charge_values = [int(charge["charge_value"]) for charge in scenario["charges"]]
    midpoint_x = sum(int(charge["x"]) for charge in scenario["charges"]) / 2.0
    midpoint_y = sum(int(charge["y"]) for charge in scenario["charges"]) / 2.0


    assert out.answer_gt.type == "option_letter"

    assert out.answer_gt.value == "E"

    assert out.query_id == "zero_field_point_label"

    assert len(out.evidence_gt.value) == 1

    assert scenario["correct_option_letter"] == "E"

    assert correct["option_letter"] == "E"

    assert len(set(abs(value) for value in charge_values)) == 2

    assert charge_values[0] * charge_values[1] > 0

    assert (float(correct["x"]), float(correct["y"])) != (midpoint_x, midpoint_y)

    assert abs(field_x) < 1e-9

    assert abs(field_y) < 1e-9

    assert out.trace_payload["execution_trace"]["evidence_entity_ids"] == ["candidate_E"]


def test_physics_electrostatics_potential_value_contract() -> None:
    out = PhysicsElectrostaticsPotentialValueTask().generate(
        81003,
        params={
            "scene_variant": "dense_grid",
            "target_answer": 4,
            "potential_contributions": [1, 2, 1],
            "accent_color_name": "cyan",
        },
        max_attempts=30,
    )
    scenario = out.trace_payload["execution_trace"]["potential_scenario"]


    assert out.answer_gt.type == "integer"

    assert int(out.answer_gt.value) == 4

    assert out.query_id == "potential_value"

    assert len(out.evidence_gt.value) == 1

    assert [charge["potential_contribution"] for charge in scenario["charges"]] == [1, 2, 1]

    assert len(scenario["charges"]) == 3

    assert sum(int(charge["charge_value"]) // int(charge["distance_units"]) for charge in scenario["charges"]) == 4

    assert scenario["potential_value"] == 4

    assert out.trace_payload["execution_trace"]["evidence_entity_ids"] == ["potential_witness_region"]


def test_physics_electrostatics_tasks_are_deterministic() -> None:
    params = {
        "scene_variant": "paper_grid",
        "target_answer": -3,
        "accent_color_name": "orange",
    }
    task = PhysicsElectrostaticsPotentialValueTask()
    out_a = task.generate(81031, params=params, max_attempts=60)
    out_b = task.generate(81031, params=params, max_attempts=60)


    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()

    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()

    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]

    assert out_a.prompt == out_b.prompt

    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_physics_electrostatics_sampling_covers_internal_axes() -> None:
    direction_modes: Counter[str] = Counter()
    target_directions: Counter[str] = Counter()
    direction_letters: Counter[str] = Counter()
    zero_letters: Counter[str] = Counter()
    potential_answers: set[int] = set()

    for sampling_index in range(96):
        direction = PhysicsElectrostaticsFieldDirectionChoiceTask().generate(
            81100 + sampling_index,
            params={},
            max_attempts=80,
        )
        zero = PhysicsElectrostaticsZeroFieldPointLabelTask().generate(
            81200 + sampling_index,
            params={},
            max_attempts=80,
        )
        potential = PhysicsElectrostaticsPotentialValueTask().generate(
            81300 + sampling_index,
            params={},
            max_attempts=80,
        )
        direction_execution = direction.trace_payload["execution_trace"]
        direction_modes[str(direction_execution["direction_mode"])] += 1
        target_directions[str(direction_execution["target_direction"])] += 1
        direction_letters[str(direction.answer_gt.value)] += 1
        zero_letters[str(zero.answer_gt.value)] += 1
        potential_answers.add(int(potential.answer_gt.value))


    assert set(direction_modes) == {
        "electric_field_direction",
        "force_on_positive_charge",
        "force_on_negative_charge",
    }

    assert set(target_directions) == {
        "east",
        "northeast",
        "north",
        "northwest",
        "west",
        "southwest",
        "south",
        "southeast",
    }

    assert set(direction_letters) == {"A", "B", "C", "D", "E", "F", "G", "H"}

    assert set(zero_letters) == {"A", "B", "C", "D", "E", "F"}

    assert len(potential_answers) >= 12


def test_physics_electrostatics_prompt_bundle_supports_variants() -> None:
    bundle = json.loads(Path("prompts/physics/electrostatics/physics_electrostatics_v0.json").read_text(encoding="utf-8"))

    assert len(bundle["scene_templates"]["electrostatics_field_map"]) == 5

    assert set(bundle["query_templates"]) == {
        "field_direction_choice",
        "zero_field_point_label",
        "potential_value",
    }

    assert len(bundle["query_templates"]["field_direction_choice"]) == 5

    assert len(bundle["query_templates"]["zero_field_point_label"]) == 5

    assert len(bundle["query_templates"]["potential_value"]) == 5
