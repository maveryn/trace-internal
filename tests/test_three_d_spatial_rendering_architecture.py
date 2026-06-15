from __future__ import annotations

import ast
from pathlib import Path


OBJECT_SCENE_TASK_FILES = (
    Path("trace/tasks/three_d/object_scene/marked_point_depth_extremum_label.py"),
    Path("trace/tasks/three_d/object_scene/marked_point_vertical_relation_label.py"),
    Path("trace/tasks/three_d/object_scene/multiview_object_match_label.py"),
    Path("trace/tasks/three_d/object_scene/landmark_correspondence_label.py"),
    Path("trace/tasks/three_d/object_scene/camera_distance_extremum_label.py"),
    Path("trace/tasks/three_d/object_scene/shared/marked_point_common.py"),
)

SURFACE_FIXTURE_TASK_FILES = (
    Path("trace/tasks/three_d/surface_fixture/repeated_element_count.py"),
    Path("trace/tasks/three_d/surface_fixture/colored_element_count.py"),
    Path("trace/tasks/three_d/surface_fixture/color_count_after_operations_value.py"),
    Path("trace/tasks/three_d/surface_fixture/scoped_colored_element_count.py"),
    Path("trace/tasks/three_d/surface_fixture/empty_or_missing_cell_count.py"),
)


OBJECT_SCENE_RENDERING_FILES = (
    Path("trace/tasks/three_d/object_scene/shared/marked_point_rendering.py"),
    Path("trace/tasks/three_d/object_scene/shared/multiview_rendering.py"),
    Path("trace/tasks/three_d/object_scene/shared/landmark_rendering.py"),
    Path("trace/tasks/three_d/surface_fixture/shared/rendering.py"),
)


def _imported_names(tree: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.extend(alias.name for alias in node.names)
    return names


def test_spatial_task_modules_do_not_own_pil_rendering() -> None:
    forbidden_tokens = (
        "from PIL import",
        "import PIL",
        "ImageDraw",
        "Image.new",
        "ImageDraw.Draw",
        "def _draw_",
        "draw.",
    )
    for path in (*OBJECT_SCENE_TASK_FILES, *SURFACE_FIXTURE_TASK_FILES):
        source = path.read_text()
        assert all(token not in source for token in forbidden_tokens), str(path)


def test_spatial_task_modules_do_not_reexport_draw_helpers() -> None:
    for path in (*OBJECT_SCENE_TASK_FILES, *SURFACE_FIXTURE_TASK_FILES):
        tree = ast.parse(path.read_text(), filename=str(path))
        imported = _imported_names(tree)
        assert not any(name.startswith("_draw_") for name in imported), str(path)


def test_spatial_rendering_helpers_are_scene_local_modules() -> None:
    for path in OBJECT_SCENE_RENDERING_FILES:
        assert path.exists(), str(path)
