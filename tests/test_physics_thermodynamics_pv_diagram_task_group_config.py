"""Config regression tests for physics thermodynamics PV-diagram defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_physics_thermodynamics_pv_defaults_expose_scene_query_and_answer_support() -> None:
    cfg = get_task_group_defaults("physics", "thermodynamics")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="physics_thermodynamics_pv_diagram_family",
    )


    assert bool(generation["balanced_scene_variant_sampling"]) is True

    assert bool(generation["balanced_query_id_sampling"]) is True

    assert bool(generation["balanced_work_mode_sampling"]) is True

    assert bool(generation["balanced_target_sign_sampling"]) is True

    assert bool(generation["balanced_correct_option_letter_sampling"]) is True

    assert bool(generation["balanced_target_answer_sampling"]) is True

    assert set(generation["scene_variant_weights"].keys()) == {"clean_grid", "paper_grid", "bold_grid"}

    assert set(generation["query_id_weights"].keys()) == {
        "work_value",
        "process_sign_choice",
    }

    assert set(generation["work_mode_weights"].keys()) == {"single_process", "rectangular_cycle"}

    assert set(generation["target_sign_weights"].keys()) == {"positive", "negative", "zero"}

    assert set(generation["correct_option_letter_weights"].keys()) == {"A", "B", "C", "D", "E", "F", "G", "H"}

    assert list(generation["pressure_support"]) == [2, 3, 4, 5, 6]

    assert list(generation["volume_support"]) == [1, 2, 3, 4, 5, 6, 7, 8, 9]

    assert list(generation["work_answer_support"]) == [
        -24,
        -20,
        -18,
        -16,
        -15,
        -12,
        -10,
        -9,
        -8,
        -6,
        -4,
        4,
        6,
        8,
        9,
        10,
        12,
        15,
        16,
        18,
        20,
        24,
    ]


    assert int(rendering["canvas_width"]) == 1180

    assert int(rendering["canvas_height"]) == 760

    assert int(rendering["plot_width_px"]) == 760

    assert int(rendering["mini_cell_width_px"]) == 262

    assert bool(rendering["layout_jitter_enabled"]) is True

    assert int(rendering["layout_jitter_min_margin_px"]) == 8


    assert str(prompt["bundle_id"]) == "physics_thermodynamics_v0"

    assert str(prompt["scene_key"]) == "thermodynamics_pv_diagram"

    assert str(prompt["task_key"]) == "pv_diagram_query"

    assert "pressure-volume diagram" in str(prompt["object_description_clean_grid"])

    assert "highlighted PV process or cycle" in str(prompt["evidence_hint_work_value"])

    assert "correct labeled candidate process" in str(prompt["evidence_hint_process_sign_choice"])
