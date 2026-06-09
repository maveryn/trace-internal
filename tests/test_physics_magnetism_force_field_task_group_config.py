"""Config regression tests for physics magnetism force-field defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_physics_magnetism_defaults_expose_scene_query_axes_and_supports() -> None:
    cfg = get_task_group_defaults("physics", "magnetism")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="physics_magnetism_force_field_family",
    )


    assert bool(generation["balanced_scene_variant_sampling"]) is True

    assert bool(generation["balanced_query_id_sampling"]) is True

    assert bool(generation["balanced_field_orientation_sampling"]) is True

    assert bool(generation["balanced_velocity_direction_sampling"]) is True

    assert bool(generation["balanced_charge_sign_sampling"]) is True

    assert bool(generation["balanced_direction_option_letter_sampling"]) is True

    assert set(generation["scene_variant_weights"].keys()) == {"field_grid"}

    assert set(generation["query_id_weights"].keys()) == {"force_direction_choice"}

    assert set(generation["field_orientation_weights"].keys()) == {"out_of_page", "into_page"}

    assert set(generation["velocity_direction_weights"].keys()) == {
        "east",
        "northeast",
        "north",
        "northwest",
        "west",
        "southwest",
        "south",
        "southeast",
    }

    assert set(generation["direction_option_letter_weights"].keys()) == {"B", "C", "D", "E", "G", "H"}


    assert int(rendering["canvas_width"]) == 1180

    assert int(rendering["canvas_height"]) == 760

    assert int(rendering["panel_width_px"]) == 760

    assert int(rendering["arrow_length_px"]) == 148

    assert int(rendering["arrow_width_px"]) == 9

    assert int(rendering["option_cell_width_px"]) == 126

    assert int(rendering["option_arrow_length_px"]) == 64

    assert int(rendering["option_arrow_width_px"]) == 8

    assert int(rendering["particle_font_size_px"]) == 31

    assert bool(rendering["layout_jitter_enabled"]) is True


    assert str(prompt["bundle_id"]) == "physics_magnetism_v0"

    assert str(prompt["scene_key"]) == "magnetic_force_field"

    assert str(prompt["task_key"]) == "magnetic_force_field_query"

    assert "magnetic-field panel" in str(prompt["object_description_clean_panel"])

    assert "field_orientation" in str(prompt["annotation_hint_force_direction_choice"])

    assert "charged particle" in str(prompt["annotation_hint_force_direction_choice"])
