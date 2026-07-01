"""Contract tests for physics waves interference-tank tasks."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from trace.core.task_review_distribution import extract_sampling_axes
from trace.tasks.physics.wave_interference.interference_point_choice import (
    PhysicsWavesInterferencePointChoiceTask,
)
from trace.tasks.physics.wave_interference.path_difference_value import (
    PhysicsWavesPathDifferenceValueTask,
)


def test_physics_waves_interference_point_choice_contract() -> None:
    out = PhysicsWavesInterferencePointChoiceTask().generate(
        99001,
        params={
            "query_id": "constructive_interference_point_choice",
            "scene_variant": "clean_tank",
            "phase_relation": "in_phase",
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

    assert out.annotation_gt.type == "point"

    assert out.scene_id == "wave_interference"

    assert out.query_id == "constructive_interference_point_choice"
    assert trace["query_spec"]["query_id"] == "constructive_interference_point_choice"

    assert trace["query_spec"]["params"]["internal_query_id"] == "interference_point_choice"

    assert execution["phase_relation"] == "in_phase"

    assert scenario["target_condition"] == "constructive"

    assert scenario["correct_option_letter"] == "D"

    assert len(correct_candidates) == 1

    assert len(matching_condition) == 1

    assert correct_candidates[0]["option_letter"] == "D"

    assert correct_candidates[0]["condition"] == "constructive"

    assert execution["annotation_entity_ids"] == ["candidate_D"]

    assert trace["projected_annotation"]["type"] == "point"
    assert trace["projected_annotation"]["point"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_point"] == out.annotation_gt.value
    assert trace["render_map"]["annotation_point_px"] == out.annotation_gt.value
    assert trace["render_spec"]["font"]["selection_policy"]["pool"] == "global_approved_font_pool"
    assert trace["render_spec"]["layout_placement"]["mode"] == "whole_wave_tank_offset"

    assert "labeled point A-E" in out.prompt


def test_physics_waves_interference_point_choice_query_ids_bind_conditions() -> None:
    task = PhysicsWavesInterferencePointChoiceTask()

    constructive = task.generate(
        99011,
        params={
            "query_id": "constructive_interference_point_choice",
            "phase_relation": "opposite_phase",
            "correct_option_letter": "B",
        },
        max_attempts=30,
    )
    destructive = task.generate(
        99012,
        params={
            "query_id": "destructive_interference_point_choice",
            "phase_relation": "opposite_phase",
            "correct_option_letter": "C",
        },
        max_attempts=30,
    )

    assert constructive.trace_payload["execution_trace"]["target_condition"] == "constructive"
    assert constructive.trace_payload["execution_trace"]["choice_scenario"]["target_condition"] == "constructive"
    assert constructive.query_id == "constructive_interference_point_choice"
    assert "constructive interference" in constructive.prompt

    assert destructive.trace_payload["execution_trace"]["target_condition"] == "destructive"
    assert destructive.trace_payload["execution_trace"]["choice_scenario"]["target_condition"] == "destructive"
    assert destructive.query_id == "destructive_interference_point_choice"
    assert "destructive interference" in destructive.prompt


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

    assert out.scene_id == "wave_interference"

    assert out.query_id == "single"

    assert out.annotation_gt.type == "segment_set"

    assert len(out.annotation_gt.value) == 2

    assert out.trace_payload["query_spec"]["query_id"] == "single"
    assert out.trace_payload["query_spec"]["params"]["internal_query_id"] == "path_difference_value"
    assert out.trace_payload["projected_annotation"]["type"] == "segment_set"
    assert out.trace_payload["projected_annotation"]["segment_set"] == out.annotation_gt.value
    assert out.trace_payload["projected_annotation"]["pixel_segment_set"] == out.annotation_gt.value
    assert out.trace_payload["render_map"]["annotation_segment_set_px"] == out.annotation_gt.value
    assert out.trace_payload["render_spec"]["font"]["selection_policy"]["pool"] == "global_approved_font_pool"
    assert out.trace_payload["render_spec"]["layout_placement"]["mode"] == "whole_wave_tank_offset"

    assert scenario["phase_relation"] == "opposite_phase"

    assert scenario["unit"] == "lambda/2"

    assert abs(int(scenario["s1_distance_steps"]) - int(scenario["s2_distance_steps"])) == 4

    assert scenario["path_difference_steps"] == 4
    sampling_axes = extract_sampling_axes(out)
    assert sampling_axes["path_difference_steps"]["observed"] == "4"
    assert "path_difference" not in sampling_axes

    assert out.trace_payload["execution_trace"]["annotation_entity_ids"] == ["path_S1P", "path_S2P"]

    assert "lambda/2 steps" in out.prompt
    render_map = out.trace_payload["render_map"]

    assert "path_s1_label_bbox_px" in render_map

    assert "path_s2_label_bbox_px" in render_map

    assert "path_s1p_bbox_px" in render_map

    assert "path_s2p_bbox_px" in render_map


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

    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()

    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]

    assert out_a.prompt == out_b.prompt

    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_physics_waves_sampling_covers_internal_axes_and_answers() -> None:
    phase_relations: Counter[str] = Counter()
    target_conditions: Counter[str] = Counter()
    choice_query_ids: Counter[str] = Counter()
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
        choice_query_ids[str(choice.query_id)] += 1
        phase_relations[str(choice_execution["phase_relation"])] += 1
        phase_relations[str(value_execution["phase_relation"])] += 1
        target_conditions[str(choice_execution["target_condition"])] += 1
        option_letters[str(choice.answer_gt.value)] += 1
        path_answers.add(int(value.answer_gt.value))


    assert set(phase_relations) == {"in_phase", "opposite_phase"}

    assert set(target_conditions) == {"constructive", "destructive"}

    assert set(choice_query_ids) == {
        "constructive_interference_point_choice",
        "destructive_interference_point_choice",
    }

    assert set(option_letters) == {"A", "B", "C", "D", "E"}

    assert path_answers == {1, 2, 3, 4, 5}


def test_physics_waves_prompt_bundle_supports_variants() -> None:
    wave_bundle = json.loads(
        Path("prompts/physics/wave_interference/physics_wave_interference_v1.json").read_text(encoding="utf-8")
    )
    waveform_bundle = json.loads(
        Path("prompts/physics/waveform_panel/physics_waveform_panel_v1.json").read_text(encoding="utf-8")
    )

    assert wave_bundle["bundle_id"] == "physics_wave_interference_v1"
    assert len(wave_bundle["templates"]["scene"]["wave_interference_tank"]) == 5
    assert set(wave_bundle["templates"]["task"]) == {
        "interference_point_choice_query",
        "path_difference_value_query",
    }
    assert len(wave_bundle["templates"]["task"]["interference_point_choice_query"]) == 5
    assert len(wave_bundle["templates"]["task"]["path_difference_value_query"]) == 5
    assert all(str(template).strip() for template in wave_bundle["templates"]["query"]["constructive_interference_point_choice"])
    assert all(str(template).strip() for template in wave_bundle["templates"]["query"]["destructive_interference_point_choice"])
    assert all(str(template).strip() for template in wave_bundle["templates"]["query"]["single"])
    assert wave_bundle["static_slots_by_key"]["task:interference_point_choice_query"]["annotation_hint"].startswith(
        "set \"annotation\" to one pixel point"
    )
    assert "source-to-P pixel segments" in wave_bundle["static_slots_by_key"]["task:path_difference_value_query"]["annotation_hint"]

    assert waveform_bundle["bundle_id"] == "physics_waveform_panel_v1"
    assert len(waveform_bundle["templates"]["scene"]["waveform_panel_diagram"]) == 5

    assert set(waveform_bundle["templates"]["query"]) == {
        "highest_amplitude_label",
        "lowest_amplitude_label",
        "highest_frequency_label",
        "lowest_frequency_label",
        "longest_wavelength_label",
        "shortest_wavelength_label",
    }

    assert len(waveform_bundle["templates"]["query"]["highest_amplitude_label"]) == 5

    assert len(waveform_bundle["templates"]["query"]["shortest_wavelength_label"]) == 5

    assert len(set(waveform_bundle["templates"]["output"]["answer_and_annotation"])) == 5
    assert "one pixel bounding box" in waveform_bundle["static_slots_by_key"]["task:wave_property_extremum_label_query"]["annotation_hint"]
