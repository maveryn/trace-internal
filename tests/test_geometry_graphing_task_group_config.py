"""Config regression tests for geometry graphing defaults."""

from __future__ import annotations

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults



def test_geometry_graphing_task_overrides_expose_scene_query_and_count_axes() -> None:
    cfg = get_task_group_defaults("geometry", "graphing")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry_graphing_count",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_variant_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {"quadratic", "absolute_value", "piecewise_linear"}
    assert set(generation["query_variant_weights"].keys()) == {
        "x_intercept_count",
        "horizontal_line_intersection_count",
        "turning_point_count",
        "local_minima_count",
        "local_maxima_count",
    }
    assert list(generation["quadratic_x_intercept_support"]) == [0, 1, 2]
    assert list(generation["piecewise_turning_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["piecewise_local_minima_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["piecewise_local_maxima_support"]) == [0, 1, 2, 3, 4]
    assert list(generation["horizontal_line_support"]) == [-4, -3, -2, -1, 1, 2, 3, 4]
    assert int(rendering["line_width"]) > 0
    assert str(prompt["bundle_id"]) == "geometry_graphing_v1"
