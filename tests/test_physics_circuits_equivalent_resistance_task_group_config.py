"""Config regression tests for physics circuits defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_physics_circuits_equivalent_resistance_defaults_expose_scene_query_and_answer_support() -> None:
    cfg = get_task_group_defaults("physics", "circuits")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_physics_circuits_equivalent_resistance",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert bool(generation["balanced_target_answer_sampling"]) is True
    assert bool(generation["balanced_accent_color_name_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {
        "parallel",
        "simple_series_parallel",
    }
    assert set(generation["query_variant_weights"].keys()) == {"total_resistance"}
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
    assert list(generation["parallel_target_answer_support"]) == [1, 2, 3, 4, 5, 6]
    assert list(generation["simple_series_parallel_target_answer_support"]) == list(range(2, 19))
    assert int(rendering["resistor_box_width_px"]) > 0
    assert int(rendering["wire_width_px"]) > 0
    assert str(prompt["bundle_id"]) == "physics_circuits_v1"
    assert "three or four parallel" in str(prompt["object_description_parallel"])
    assert "resistor boxes" in str(prompt["evidence_hint_total_resistance"])
