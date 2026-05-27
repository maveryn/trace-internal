"""Contract tests for physics thermodynamics PV-diagram tasks."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from trace.tasks.physics.thermodynamics.pv_diagram import (
    PhysicsThermodynamicsPVProcessSignChoiceTask,
    PhysicsThermodynamicsPVWorkValueTask,
)


def test_physics_thermodynamics_pv_work_value_single_process_contract() -> None:
    out = PhysicsThermodynamicsPVWorkValueTask().generate(
        71001,
        params={
            "scene_variant": "clean_grid",
            "work_mode": "single_process",
            "target_answer": 24,
            "pressure": 6,
            "volume_start": 2,
            "volume_end": 6,
            "accent_color_name": "blue",
        },
        max_attempts=30,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    scenario = execution["scenario"]


    assert out.answer_gt.type == "integer"

    assert int(out.answer_gt.value) == 24

    assert out.evidence_gt.type == "bbox_set"

    assert len(out.evidence_gt.value) == 1

    assert out.query_id == "default"

    assert out.scene_id == "pv_diagram"

    assert out.query_id == "work_value"
    assert trace["query_spec"]["query_id"] == "default"

    assert trace["query_spec"]["params"]["internal_query_id"] == "work_value"
    assert execution["query_id"] == "default"

    assert execution["internal_query_id"] == "work_value"

    assert execution["evidence_entity_ids"] == ["work_witness_region"]

    assert str(scenario["work_mode"]) == "single_process"

    assert int(scenario["pressure_kpa"]) == 6

    assert int(scenario["volume_start_l"]) == 2

    assert int(scenario["volume_end_l"]) == 6

    assert int(scenario["work_value"]) == 24

    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value


def test_physics_thermodynamics_pv_work_value_cycle_contract() -> None:
    out = PhysicsThermodynamicsPVWorkValueTask().generate(
        71011,
        params={
            "scene_variant": "bold_grid",
            "work_mode": "rectangular_cycle",
            "target_answer": -12,
            "pressure_low": 3,
            "pressure_high": 6,
            "volume_left": 2,
            "volume_right": 6,
            "cycle_direction": "counterclockwise",
            "accent_color_name": "green",
        },
        max_attempts=30,
    )
    scenario = out.trace_payload["execution_trace"]["scenario"]


    assert out.answer_gt.type == "integer"

    assert int(out.answer_gt.value) == -12

    assert str(scenario["work_mode"]) == "rectangular_cycle"

    assert str(scenario["cycle_direction"]) == "counterclockwise"

    assert int(scenario["pressure_high_kpa"]) - int(scenario["pressure_low_kpa"]) == 3

    assert int(scenario["volume_right_l"]) - int(scenario["volume_left_l"]) == 4

    assert int(scenario["work_value"]) == -12

    assert out.trace_payload["execution_trace"]["evidence_entity_ids"] == ["work_witness_region"]


def test_physics_thermodynamics_pv_process_sign_choice_contract() -> None:
    out = PhysicsThermodynamicsPVProcessSignChoiceTask().generate(
        71021,
        params={
            "scene_variant": "paper_grid",
            "target_sign": "zero",
            "correct_option_letter": "D",
            "accent_color_name": "cyan",
        },
        max_attempts=30,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    candidates = execution["process_candidates"]


    assert out.answer_gt.type == "option_letter"

    assert out.answer_gt.value == "D"

    assert out.evidence_gt.type == "bbox_set"

    assert len(out.evidence_gt.value) == 1

    assert out.query_id == "default"

    assert out.query_id == "process_sign_choice"

    assert execution["target_sign"] == "zero"

    assert execution["correct_option_letter"] == "D"

    assert execution["evidence_entity_ids"] == ["option_D"]

    assert sum(1 for candidate in candidates if candidate["sign"] == "zero") == 1

    assert [candidate for candidate in candidates if candidate["is_correct"]][0]["option_letter"] == "D"

    assert trace["render_map"]["option_signs"]["D"] == "zero"


def test_physics_thermodynamics_pv_tasks_are_deterministic() -> None:
    params = {
        "scene_variant": "paper_grid",
        "work_mode": "single_process",
        "target_answer": -18,
        "accent_color_name": "orange",
    }
    task = PhysicsThermodynamicsPVWorkValueTask()
    out_a = task.generate(71031, params=params, max_attempts=60)
    out_b = task.generate(71031, params=params, max_attempts=60)


    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()

    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()

    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]

    assert out_a.prompt == out_b.prompt

    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_physics_thermodynamics_pv_sampling_covers_internal_axes() -> None:
    work_modes: Counter[str] = Counter()
    work_answers: set[int] = set()
    target_signs: Counter[str] = Counter()
    option_letters: Counter[str] = Counter()
    for sampling_index in range(96):
        work = PhysicsThermodynamicsPVWorkValueTask().generate(
            71100 + sampling_index,
            params={},
            max_attempts=80,
        )
        sign = PhysicsThermodynamicsPVProcessSignChoiceTask().generate(
            71200 + sampling_index,
            params={},
            max_attempts=80,
        )
        work_execution = work.trace_payload["execution_trace"]
        sign_execution = sign.trace_payload["execution_trace"]
        work_modes[str(work_execution["work_mode"])] += 1
        work_answers.add(int(work.answer_gt.value))
        target_signs[str(sign_execution["target_sign"])] += 1
        option_letters[str(sign.answer_gt.value)] += 1


    assert set(work_modes) == {"single_process"}

    assert len(work_answers) >= 18

    assert set(target_signs) == {"positive", "negative", "zero"}

    assert set(option_letters) == {"A", "B", "C", "D", "E", "F", "G", "H"}


def test_physics_thermodynamics_pv_prompt_bundle_supports_variants() -> None:
    bundle = json.loads(Path("prompts/physics/thermodynamics/physics_thermodynamics_v0.json").read_text(encoding="utf-8"))

    assert len(bundle["scene_templates"]["thermodynamics_pv_diagram"]) == 5

    assert set(bundle["query_templates"]) == {
        "work_value",
        "process_sign_choice",
    }

    assert len(bundle["query_templates"]["work_value"]) == 5

    assert len(bundle["query_templates"]["process_sign_choice"]) == 5
