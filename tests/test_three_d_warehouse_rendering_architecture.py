from pathlib import Path


WAREHOUSE_TASK_OR_COMMON_FILES = (
    Path("trace/tasks/three_d/warehouse/robot_forward_path.py"),
    Path("trace/tasks/three_d/warehouse/robot_nearest_object.py"),
    Path("trace/tasks/three_d/warehouse/shelf_level_object_count.py"),
    Path("trace/tasks/three_d/warehouse/warehouse_scene_common.py"),
)

WAREHOUSE_RENDERER_FILES = (
    Path("trace/tasks/three_d/warehouse/warehouse_rendering.py"),
    Path("trace/tasks/three_d/warehouse/warehouse_shelf_rendering.py"),
    Path("trace/tasks/three_d/warehouse/warehouse_support_rendering.py"),
)


def test_warehouse_public_task_modules_are_drawing_free() -> None:
    forbidden_snippets = (
        "from PIL import",
        "import PIL",
        "ImageDraw",
        "Image.new",
        "Image.alpha_composite",
        "def _draw_",
        "draw.",
    )
    forbidden_imports = (
        "from .warehouse_support_rendering import _draw_",
        "from ..shared.warehouse_object_rendering import _draw_",
        "from ..shared.object_scene_rendering import _draw_",
    )

    for path in WAREHOUSE_TASK_OR_COMMON_FILES:
        source = path.read_text()
        for snippet in forbidden_snippets:
            assert snippet not in source, f"{path} should not contain renderer code: {snippet}"
        for snippet in forbidden_imports:
            assert snippet not in source, f"{path} should not import renderer-only helpers: {snippet}"


def test_warehouse_renderer_modules_are_explicit_scene_boundaries() -> None:
    for path in WAREHOUSE_RENDERER_FILES:
        assert path.exists()

    robot_renderer = WAREHOUSE_RENDERER_FILES[0].read_text()
    shelf_renderer = WAREHOUSE_RENDERER_FILES[1].read_text()
    assert "render_warehouse_robot_scene_3d" in robot_renderer
    assert "render_warehouse_robot_nearest_scene_3d" in robot_renderer
    assert "render_warehouse_shelf_level_count_scene_3d" in shelf_renderer
