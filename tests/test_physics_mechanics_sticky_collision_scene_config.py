"""Config regression tests for physics mechanics sticky-collision defaults."""

from __future__ import annotations

from trace.core.scene_config import get_scene_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_physics_mechanics_sticky_collision_defaults_expose_scene_query_and_answer_support() -> None:
    cfg = get_scene_defaults("physics", "mechanics")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="physics_mechanics_sticky_collision_family",
    )


    assert bool(generation["balanced_scene_variant_sampling"]) is True

    assert bool(generation["balanced_query_id_sampling"]) is True

    assert bool(generation["balanced_target_answer_sampling"]) is True

    assert bool(generation["balanced_correct_option_letter_sampling"]) is True

    assert set(generation["scene_variant_weights"].keys()) == {"wide_table", "compact_table", "gridded_table"}

    assert set(generation["query_id_weights"].keys()) == {
        "direction_choice",
        "velocity_component",
    }

    assert set(generation["component_axis_weights"].keys()) == {"x", "y"}

    assert set(generation["correct_option_letter_weights"].keys()) == {"A", "B", "C", "D", "E", "F"}

    assert list(generation["component_answer_support"]) == [-6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6]

    assert list(generation["mass_support"]) == [1, 2, 3, 4, 5, 6]

    assert list(generation["speed_support"]) == [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]


    assert int(rendering["canvas_width"]) == 1180

    assert int(rendering["canvas_height"]) == 760

    assert int(rendering["puck_radius_px"]) == 42

    assert int(rendering["option_arrow_length_px"]) == 74


    assert str(prompt["bundle_id"]) == "physics_mechanics_v0"

    assert str(prompt["scene_key"]) == "sticky_collision_diagram"

    assert str(prompt["task_key"]) == "sticky_collision_query"

    assert "six candidate direction arrows" in str(prompt["object_description_wide_table"])

    assert "object mapping puck labels A, B, and A+B" in str(prompt["annotation_hint_direction_choice"])

    assert "[x,y]" in str(prompt["annotation_hint_velocity_component"])

    assert "puck centers" in str(prompt["annotation_hint_velocity_component"])

    assert "do not" not in str(prompt["annotation_hint_velocity_component"]).lower()
