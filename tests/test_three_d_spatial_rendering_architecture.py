from __future__ import annotations

import ast
from pathlib import Path


SPATIAL_TASK_FILES = (
    Path("trace/tasks/three_d/spatial/surface_fixture_count.py"),
    Path("trace/tasks/three_d/spatial/marked_point_common.py"),
    Path("trace/tasks/three_d/spatial/marked_point_depth.py"),
    Path("trace/tasks/three_d/spatial/marked_point_vertical_relation.py"),
    Path("trace/tasks/three_d/spatial/multiview_object_match.py"),
    Path("trace/tasks/three_d/spatial/landmark_correspondence.py"),
    Path("trace/tasks/three_d/spatial/camera_distance.py"),
)


SPATIAL_RENDERING_FILES = (
    Path("trace/tasks/three_d/spatial/surface_fixture_rendering.py"),
    Path("trace/tasks/three_d/spatial/marked_point_rendering.py"),
    Path("trace/tasks/three_d/spatial/multiview_rendering.py"),
    Path("trace/tasks/three_d/spatial/landmark_rendering.py"),
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
    for path in SPATIAL_TASK_FILES:
        source = path.read_text()
        assert all(token not in source for token in forbidden_tokens), str(path)


def test_spatial_task_modules_do_not_reexport_draw_helpers() -> None:
    for path in SPATIAL_TASK_FILES:
        tree = ast.parse(path.read_text(), filename=str(path))
        imported = _imported_names(tree)
        assert not any(name.startswith("_draw_") for name in imported), str(path)


def test_spatial_rendering_helpers_are_scene_local_modules() -> None:
    for path in SPATIAL_RENDERING_FILES:
        assert path.exists(), str(path)
