from trace.tasks.three_d.street import intersection_nearest
from trace.tasks.three_d.street import intersection_rendering
from trace.tasks.three_d.street import intersection_scene


def test_intersection_nearest_uses_shared_street_scene_and_renderer_boundaries() -> None:
    assert intersection_nearest._StreetRenderParams is intersection_scene._StreetRenderParams
    assert intersection_nearest.render_street_intersection_scene_3d is intersection_rendering.render_street_intersection_scene_3d
    assert intersection_nearest._sample_context_specs is intersection_scene._sample_context_specs


def test_street_orientation_dimensions_are_axis_aware() -> None:
    x_dims = intersection_scene._dimensions_for_orientation("car", orientation_axis="x", scale=1.0)
    y_dims = intersection_scene._dimensions_for_orientation("car", orientation_axis="y", scale=1.0)
    assert x_dims[0] == y_dims[1]
    assert x_dims[1] == y_dims[0]
