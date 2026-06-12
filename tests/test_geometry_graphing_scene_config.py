"""Config regression tests for geometry graphing defaults."""

from __future__ import annotations

from trace.core.scene_config import get_scene_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults



def test_geometry_graphing_task_overrides_expose_scene_query_and_count_axes() -> None:
    cfg = get_scene_defaults("geometry", "graphing")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="geometry_graphing_count_base",
    )

    assert bool(generation["balanced_scene_variant_sampling"]) is True
    assert bool(generation["balanced_query_id_sampling"]) is True
    assert set(generation["scene_variant_weights"].keys()) == {
        "quadratic",
        "absolute_value",
        "cubic",
        "sinusoid",
        "piecewise_linear",
    }
    assert set(generation["query_id_weights"].keys()) == {
        "reference_line_crossing_count",
        "turning_point_count",
        "local_extremum_count",
    }
    assert set(generation["reference_line_kind_weights"].keys()) == {"x_axis", "horizontal_line"}
    assert set(generation["extremum_kind_weights"].keys()) == {"minimum", "maximum"}
    assert bool(generation["balanced_reference_line_kind_sampling"]) is True
    assert bool(generation["balanced_extremum_kind_sampling"]) is True
    assert list(generation["quadratic_reference_line_crossing_support"]) == [2]
    assert list(generation["absolute_value_reference_line_crossing_support"]) == [2]
    assert list(generation["cubic_reference_line_crossing_support"]) == [2, 3]
    assert list(generation["sinusoid_reference_line_crossing_support"]) == [3, 4]
    assert list(generation["piecewise_turning_support"]) == [2, 3, 4, 5, 6]
    assert list(generation["sinusoid_turning_support"]) == [3, 4]
    assert list(generation["sinusoid_local_extremum_support"]) == [2]
    assert list(generation["piecewise_local_extremum_support"]) == [2, 3, 4, 5, 6]
    assert list(generation["horizontal_line_support"]) == [-4, -3, -2, -1, 1, 2, 3, 4]
    assert int(rendering["line_width"]) > 0
    assert str(prompt["bundle_id"]) == "geometry_graphing_v0"
