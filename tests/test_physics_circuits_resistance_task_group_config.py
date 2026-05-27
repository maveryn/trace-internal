"""Config regression tests for physics circuits defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_physics_circuits_resistance_defaults_expose_scene_task_and_answer_support() -> None:
    cfg = get_task_group_defaults("physics", "circuits")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="physics_circuits_resistance_family",
    )


    assert bool(generation["balanced_scene_variant_sampling"]) is True

    assert bool(generation["balanced_query_id_sampling"]) is True

    assert bool(generation["balanced_target_answer_sampling"]) is True

    assert bool(generation["balanced_accent_color_name_sampling"]) is True

    assert set(generation["scene_variant_weights"].keys()) == {
        "parallel",
        "simple_series_parallel",
    }

    assert float(generation["scene_variant_weights"]["parallel"]) == 0.0

    assert float(generation["scene_variant_weights"]["simple_series_parallel"]) == 1.0

    assert set(generation["query_id_weights"].keys()) == {
        "total_resistance",
        "missing_resistor_value",
    }

    assert float(generation["query_id_weights"]["total_resistance"]) == 1.0

    assert float(generation["query_id_weights"]["missing_resistor_value"]) == 1.0

    assert set(generation["accent_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }

    assert list(generation["parallel_target_answer_support"]) == [1, 2, 3]

    assert list(generation["total_resistance_target_answer_support"]) == list(range(1, 21))

    assert list(generation["simple_series_parallel_target_answer_support"]) == list(range(1, 21))

    assert list(generation["missing_resistor_value_support"]) == [1, 3, 4, 5, 6, 8]

    assert list(generation["parallel_total_branch_count_options"]) == [4, 5]

    assert list(generation["series_parallel_total_count_pairs"]) == [[1, 4], [2, 3], [2, 4]]

    assert list(generation["parallel_missing_left_branch_count_options"]) == [3, 4]

    assert list(generation["parallel_missing_right_branch_count_options"]) == [3, 4]

    assert list(generation["series_parallel_missing_left_count_pairs"]) == [[1, 3]]

    assert list(generation["series_parallel_missing_right_count_pairs"]) == [[1, 3]]

    assert list(generation["compound_parallel_block_count_options"]) == [1]

    assert list(generation["compound_missing_parallel_block_count_options"]) == [2, 3]

    assert list(generation["compound_parallel_branch_count_options"]) == [2, 3]

    assert bool(generation["balanced_compound_block_count_sampling"]) is True

    assert int(rendering["resistor_box_width_px"]) > 0

    assert int(rendering["wire_width_px"]) > 0

    assert int(rendering["pair_scene_width_px"]) > 0

    assert str(prompt["bundle_id"]) == "physics_circuits_v0"

    assert "before, between, or after the blocks" in str(prompt["object_description_simple_series_parallel_total_resistance"])

    assert "resistor boxes" in str(prompt["evidence_hint_total_resistance"])

    assert "red `?` resistor" in str(prompt["evidence_hint_missing_resistor_value"])
