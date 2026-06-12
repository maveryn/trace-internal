"""Config regression tests for physics electrostatics field-map defaults."""

from __future__ import annotations

from trace.core.scene_config import get_scene_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_physics_electrostatics_defaults_expose_scene_query_and_answer_support() -> None:
    cfg = get_scene_defaults("physics", "electrostatics")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="physics_electrostatics_field_map_family",
    )


    assert bool(generation["balanced_scene_variant_sampling"]) is True

    assert bool(generation["balanced_query_id_sampling"]) is True

    assert bool(generation["balanced_direction_mode_sampling"]) is True

    assert bool(generation["balanced_target_direction_sampling"]) is True

    assert bool(generation["balanced_direction_option_letter_sampling"]) is True

    assert bool(generation["balanced_point_option_letter_sampling"]) is True

    assert bool(generation["balanced_target_answer_sampling"]) is True

    assert set(generation["scene_variant_weights"].keys()) == {"clean_grid", "paper_grid", "dense_grid"}

    assert set(generation["query_id_weights"].keys()) == {
        "field_direction_choice",
        "zero_field_point_label",
        "potential_value",
    }

    assert set(generation["direction_mode_weights"].keys()) == {
        "electric_field_direction",
        "force_on_positive_charge",
        "force_on_negative_charge",
    }

    assert set(generation["target_direction_weights"].keys()) == {
        "east",
        "northeast",
        "north",
        "northwest",
        "west",
        "southwest",
        "south",
        "southeast",
    }

    assert set(generation["direction_option_letter_weights"].keys()) == {"A", "B", "C", "D", "E", "F", "G", "H"}

    assert set(generation["point_option_letter_weights"].keys()) == {"A", "B", "C", "D", "E", "F"}

    assert -9 in generation["potential_answer_support"]

    assert 9 in generation["potential_answer_support"]


    assert int(rendering["canvas_width"]) == 1180

    assert int(rendering["canvas_height"]) == 760

    assert int(rendering["board_width_px"]) == 760

    assert int(rendering["option_cell_width_px"]) == 140

    assert bool(rendering["layout_jitter_enabled"]) is True


    assert str(prompt["bundle_id"]) == "physics_electrostatics_v0"

    assert str(prompt["scene_key"]) == "electrostatics_field_map"

    assert str(prompt["task_key"]) == "electrostatics_field_map_query"

    assert "electrostatics coordinate grid" in str(prompt["object_description_clean_grid"])

    assert "charges labeled Q1, Q2, and Q3" in str(prompt["object_description_clean_grid_field_direction_choice"])

    assert "charges labeled Q1 and Q2" in str(prompt["object_description_paper_grid_zero_field_point_label"])

    assert "visible distance labels" in str(prompt["object_description_dense_grid_potential_value"])

    assert 'keys "Q1", "Q2", "Q3", and "P"' in str(prompt["annotation_hint_field_direction_choice"])

    assert 'keys "Q1", "Q2", "Q3", and "P"' in str(prompt["annotation_hint_potential_value"])

    assert 'keys "Q1" and "Q2"' in str(prompt["annotation_hint_zero_field_point_label"])

    assert "do not" not in str(prompt["annotation_hint_potential_value"]).lower()

    assert "zero-field point" in str(prompt["answer_hint_zero_field_point_label"])
