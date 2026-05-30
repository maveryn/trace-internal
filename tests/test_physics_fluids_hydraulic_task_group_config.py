"""Config regression tests for physics fluids hydraulic-piston defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_physics_fluids_hydraulic_defaults_expose_scene_query_and_support() -> None:
    cfg = get_task_group_defaults("physics", "fluids")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_physics__hydraulic__hydraulic_missing_value",
    )


    assert bool(generation["balanced_scene_variant_sampling"]) is True

    assert bool(generation["balanced_query_id_sampling"]) is True

    assert bool(generation["balanced_target_answer_sampling"]) is True

    assert bool(generation["balanced_accent_color_name_sampling"]) is True

    assert set(generation["scene_variant_weights"].keys()) == {
        "wide_bench",
        "compact_frame",
        "tall_columns",
    }

    assert set(generation["query_id_weights"].keys()) == {
        "missing_output_force",
        "missing_input_force",
        "missing_piston_area",
    }

    assert list(generation["input_force_support"]) == list(range(4, 13))

    assert list(generation["input_area_support"]) == list(range(2, 10))

    assert list(generation["mechanical_advantage_support"]) == [3, 4, 5, 6, 7, 8]

    assert min(generation["output_force_support"]) == 12

    assert max(generation["output_force_support"]) == 96

    assert min(generation["output_area_support"]) == 6

    assert max(generation["output_area_support"]) == 72

    assert int(rendering["canvas_width"]) == 1120

    assert int(rendering["canvas_height"]) == 660

    assert int(rendering["chamber_min_width_px"]) > 0

    assert bool(rendering["layout_jitter_enabled"]) is True

    assert str(prompt["bundle_id"]) == "physics_fluids_v0"

    assert str(prompt["scene_key"]) == "hydraulic_piston_diagram"

    assert "three fluid chambers" in str(prompt["object_description_wide_bench"])

    assert "keys \"input_force\", \"input_area\", and \"output_area\"" in str(prompt["evidence_hint_missing_output_force"])

    assert "keys \"output_force\", \"input_area\", and \"output_area\"" in str(prompt["evidence_hint_missing_input_force"])

    assert "keys \"input_force\", \"output_force\", and \"input_area\"" in str(prompt["evidence_hint_missing_piston_area"])

    assert "red `?`" not in str(prompt["evidence_hint_missing_output_force"])

    assert "red `?`" not in str(prompt["evidence_hint_missing_input_force"])

    assert "red `?`" not in str(prompt["evidence_hint_missing_piston_area"])
