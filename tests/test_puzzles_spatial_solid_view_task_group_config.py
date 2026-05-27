"""Config regression tests for puzzle spatial solid-view defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_puzzles_spatial_solid_view_task_overrides_expose_scene_query_and_count_axes() -> None:
    cfg = get_task_group_defaults("puzzles", "spatial")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="puzzles_spatial_cube_structure_internal",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) >= {"stack_strip", "stack_card", "stack_outline"}
    assert set(generation["query_id_weights"].keys()) == {
        "visible_cube_count",
    }
    assert set(generation["view_direction_weights"].keys()) == {"top", "front", "right"}
    assert bool(generation["balanced_view_direction_sampling"]) is True
    assert bool(generation["balanced_consistency_query_sampling"]) is True
    assert set(generation["consistency_query_weights"].keys()) == {
        "inconsistent_projection_label",
        "candidate_stack_from_views_label",
    }
    assert list(generation["target_count_support"]) == [3, 4, 5, 6, 7]
    assert int(generation["projection_consistency_option_count_min"]) == 5
    assert int(generation["projection_consistency_option_count_max"]) == 5
    assert int(generation["total_cubes_min"]) == 4
    assert float(rendering["voxel_scale_min"]) == 0.50
    assert float(rendering["voxel_scale_max"]) == 1.00
    assert int(rendering["voxel_scale_percent_min"]) == 50
    assert int(rendering["voxel_scale_percent_max"]) == 100
    assert int(rendering["line_width"]) > 0
    assert str(prompt["bundle_id"]) == "puzzles_spatial_v0"
    assert str(prompt["scene_key"]) == "spatial_cube_structure_puzzle"
    assert "cube-stack projection puzzle" in str(prompt["object_description_visible_cube_count"])
    assert "cube-stack consistency puzzle" in str(prompt["object_description_projection_consistency_label"])
