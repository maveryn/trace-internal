from trace.tasks.three_d.shared import object_scene
from trace.tasks.three_d.shared import object_scene_rendering
from trace.tasks.three_d.shared import object_scene_primitives
from trace.tasks.three_d.spatial import camera_distance


def test_camera_distance_reexports_shared_object_scene_rendering_helpers() -> None:
    assert camera_distance._bbox_union is object_scene_rendering._bbox_union
    assert camera_distance._draw_box_object is object_scene_rendering._draw_box_object
    assert camera_distance._draw_option_label is object_scene_rendering._draw_option_label
    assert camera_distance._RenderParams is object_scene._RenderParams
    assert camera_distance._make_object_spec is object_scene._make_object_spec
    assert camera_distance.render_object_scene_3d is object_scene.render_object_scene_3d


def test_object_scene_rendering_reexports_primitive_helpers() -> None:
    assert object_scene_rendering._bbox_union is object_scene_primitives._bbox_union
    assert object_scene_rendering._draw_box_object is object_scene_primitives._draw_box_object
    assert object_scene_rendering._draw_cylinder_object is object_scene_primitives._draw_cylinder_object
    assert object_scene_rendering._draw_torus_object is object_scene_primitives._draw_torus_object
    assert object_scene_rendering._sub_box_spec is object_scene_primitives._sub_box_spec
