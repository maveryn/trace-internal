"""Config regression tests for physics circuits defaults."""

from __future__ import annotations

from trace.core.scene_config import get_scene_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_physics_circuits_equivalent_defaults_expose_scene_task_and_answer_support() -> None:
    cfg = get_scene_defaults("physics", "circuits")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="physics_circuits_equivalent_component_family",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert bool(generation["balanced_accent_color_name_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {
        "series_parallel",
    }
    assert set(generation["query_id_weights"].keys()) == {
        "total_resistance",
        "total_capacitance",
    }
    assert float(generation["query_id_weights"]["total_resistance"]) == 1.0
    assert float(generation["query_id_weights"]["total_capacitance"]) == 1.0
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
    assert list(generation["total_resistance_target_answer_support"]) == list(range(1, 21))
    assert list(generation["total_capacitance_target_answer_support"]) == list(range(1, 21))
    assert int(generation["component_value_max"]) == 60
    assert list(generation["parallel_component_count_options"]) == [2, 3, 4]
    assert list(generation["parallel_block_count_options"]) == [1, 2]
    assert list(generation["series_parallel_branch_count_options"]) == [2, 3]

    assert int(rendering["component_symbol_width_px"]) > 0
    assert int(rendering["component_symbol_height_px"]) > 0
    assert int(rendering["wire_width_px"]) > 0
    assert bool(rendering["layout_jitter_enabled"]) is True

    assert str(prompt["bundle_id"]) == "physics_circuits_v0"
    assert str(prompt["scene_key"]) == "equivalent_circuit_diagram"
    assert str(prompt["task_key"]) == "equivalent_component_query"
    assert "one or two labeled parallel resistor blocks" in str(prompt["object_description_series_parallel_total_resistance"])
    assert "one or two labeled parallel capacitor blocks" in str(prompt["object_description_series_parallel_total_capacitance"])
    assert "object mapping each visible resistor label" in str(prompt["annotation_hint_total_resistance"])
    assert "object mapping each visible capacitor label" in str(prompt["annotation_hint_total_capacitance"])
