"""Config regression tests for physics waves interference-tank defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_physics_waves_defaults_expose_scene_query_axes_and_supports() -> None:
    cfg = get_task_group_defaults("physics", "waves")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="physics_waves_interference_tank_family",
    )


    assert bool(generation["balanced_scene_variant_sampling"]) is True

    assert bool(generation["balanced_query_variant_sampling"]) is True

    assert bool(generation["balanced_phase_relation_sampling"]) is True

    assert bool(generation["balanced_target_condition_sampling"]) is True

    assert bool(generation["balanced_option_letter_sampling"]) is True

    assert bool(generation["balanced_target_answer_sampling"]) is True

    assert set(generation["scene_variant_weights"].keys()) == {"clean_tank", "grid_tank", "lab_sheet"}

    assert set(generation["query_variant_weights"].keys()) == {
        "interference_point_choice",
        "path_difference_value",
    }

    assert set(generation["phase_relation_weights"].keys()) == {"in_phase", "opposite_phase"}

    assert set(generation["target_condition_weights"].keys()) == {"constructive", "destructive"}

    assert set(generation["option_letter_weights"].keys()) == {"A", "B", "C", "D", "E"}

    assert generation["path_difference_step_support"] == [1, 2, 3, 4]


    assert int(rendering["canvas_width"]) == 1180

    assert int(rendering["canvas_height"]) == 760

    assert int(rendering["board_width_px"]) == 790

    assert int(rendering["half_wavelength_px"]) == 44


    assert str(prompt["bundle_id"]) == "physics_waves_v0"

    assert str(prompt["scene_key"]) == "wave_interference_tank"

    assert str(prompt["task_key"]) == "wave_interference_tank_query"

    assert "ripple-tank interference diagram" in str(prompt["object_description_clean_tank"])

    assert "candidate points A-E" in str(prompt["object_description_clean_tank_interference_point_choice"])

    assert "labeled dashed source-to-P path guides" in str(prompt["object_description_grid_tank_path_difference_value"])

    assert "correct labeled candidate point" in str(prompt["evidence_hint_interference_point_choice"])

    assert "lambda/2 steps" in str(prompt["answer_hint_path_difference_value"])
