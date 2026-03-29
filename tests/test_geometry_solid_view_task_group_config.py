"""Config regression tests for geometry solid-view defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_geometry_solid_view_task_overrides_expose_scene_query_and_count_axes() -> None:
    cfg = get_task_group_defaults("geometry", "solid")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_solid_view_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"cube_stack"}
    assert set(generation["query_variant_weights"].keys()) == {
        "top_view_visible_count",
        "front_view_visible_count",
        "right_view_visible_count",
    }
    assert list(generation["target_count_support"]) == [2, 3, 4, 5, 6, 7]
    assert int(generation["total_cubes_min"]) == 4
    assert int(rendering["line_width"]) > 0
    assert str(prompt["bundle_id"]) == "geometry_solid_v1"
