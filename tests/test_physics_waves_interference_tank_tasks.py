"""Contract tests for physics waves interference-tank tasks."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from trace.tasks.physics.waves.interference_tank import (
    PhysicsWavesInterferencePointChoiceTask,
    PhysicsWavesPathDifferenceValueTask,
)


def test_physics_waves_interference_point_choice_contract() -> None:
    out = PhysicsWavesInterferencePointChoiceTask().generate(
        99001,
        params={
            "scene_variant": "clean_tank",
            "phase_relation": "in_phase",
            "target_condition": "constructive",
            "correct_option_letter": "D",
            "accent_color_name": "blue",
        },
        max_attempts=30,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    scenario = execution["choice_scenario"]
    correct_candidates = [candidate for candidate in scenario["candidates"] if candidate["is_correct"]]
    matching_condition = [
        candidate
        for candidate in scenario["candidates"]
        if str(candidate["condition"]) == str(scenario["target_condition"])
    ]


    assert out.answer_gt.type == "option_letter"

    assert out.answer_gt.value == "D"

    assert out.evidence_gt.type == "bbox_set"

    assert len(out.evidence_gt.value) == 1

    assert out.query_id == "default"

    assert out.scene_id == "wave_interference"

    assert out.query_id == "interference_point_choice"
    assert trace["query_spec"]["query_id"] == "default"

    assert trace["query_spec"]["params"]["internal_query_id"] == "interference_point_choice"

    assert execution["phase_relation"] == "in_phase"

    assert scenario["target_condition"] == "constructive"

    assert scenario["correct_option_letter"] == "D"

    assert len(correct_candidates) == 1

    assert len(matching_condition) == 1

    assert correct_candidates[0]["option_letter"] == "D"

    assert correct_candidates[0]["condition"] == "constructive"

    assert execution["evidence_entity_ids"] == ["candidate_D"]

    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value

    assert "candidate points A-E" in out.prompt


def test_physics_waves_path_difference_value_contract() -> None:
    out = PhysicsWavesPathDifferenceValueTask().generate(
        99002,
        params={
            "scene_variant": "grid_tank",
            "phase_relation": "opposite_phase",
            "target_answer": 4,
            "accent_color_name": "cyan",
        },
        max_attempts=30,
    )
    scenario = out.trace_payload["execution_trace"]["path_difference_scenario"]


    assert out.answer_gt.type == "integer"

    assert int(out.answer_gt.value) == 4

    assert out.query_id == "default"

    assert out.scene_id == "wave_interference"

    assert out.query_id == "path_difference_value"

    assert len(out.evidence_gt.value) == 1

    assert scenario["phase_relation"] == "opposite_phase"

    assert scenario["unit"] == "lambda/2"

    assert abs(int(scenario["s1_distance_steps"]) - int(scenario["s2_distance_steps"])) == 4

    assert scenario["path_difference_steps"] == 4

    assert out.trace_payload["execution_trace"]["evidence_entity_ids"] == ["path_difference_witness_region"]

    assert "labeled dashed source-to-P path guides" in out.prompt
    render_map = out.trace_payload["render_map"]

    assert "path_s1_label_bbox_px" in render_map

    assert "path_s2_label_bbox_px" in render_map


def test_physics_waves_tasks_are_deterministic() -> None:
    params = {
        "scene_variant": "lab_sheet",
        "phase_relation": "opposite_phase",
        "target_answer": 4,
        "accent_color_name": "orange",
    }
    task = PhysicsWavesPathDifferenceValueTask()
    out_a = task.generate(99031, params=params, max_attempts=60)
    out_b = task.generate(99031, params=params, max_attempts=60)


    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()

    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()

    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]

    assert out_a.prompt == out_b.prompt

    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_physics_waves_sampling_covers_internal_axes_and_answers() -> None:
    phase_relations: Counter[str] = Counter()
    target_conditions: Counter[str] = Counter()
    option_letters: Counter[str] = Counter()
    path_answers: set[int] = set()

    for sampling_index in range(112):
        choice = PhysicsWavesInterferencePointChoiceTask().generate(
            99100 + sampling_index,
            params={},
            max_attempts=80,
        )
        value = PhysicsWavesPathDifferenceValueTask().generate(
            99200 + sampling_index,
            params={},
            max_attempts=80,
        )
        choice_execution = choice.trace_payload["execution_trace"]
        value_execution = value.trace_payload["execution_trace"]
        phase_relations[str(choice_execution["phase_relation"])] += 1
        phase_relations[str(value_execution["phase_relation"])] += 1
        target_conditions[str(choice_execution["target_condition"])] += 1
        option_letters[str(choice.answer_gt.value)] += 1
        path_answers.add(int(value.answer_gt.value))


    assert set(phase_relations) == {"in_phase", "opposite_phase"}

    assert set(target_conditions) == {"constructive", "destructive"}

    assert set(option_letters) == {"A", "B", "C", "D", "E"}

    assert path_answers == {1, 2, 3, 4}


def test_physics_waves_prompt_bundle_supports_variants() -> None:
    bundle = json.loads(Path("prompts/physics/waves/physics_waves_v0.json").read_text(encoding="utf-8"))

    assert len(bundle["scene_templates"]["wave_interference_tank"]) == 5

    assert set(bundle["query_templates"]) == {
        "interference_point_choice",
        "path_difference_value",
    }

    assert len(bundle["query_templates"]["interference_point_choice"]) == 5

    assert len(bundle["query_templates"]["path_difference_value"]) == 5
