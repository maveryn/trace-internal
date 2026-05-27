"""Reusable cube-stack sampling and rendering helpers for puzzle solid-view tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ...geometry.shared.shape_style import GeometryShapeStyle
from ...shared.drawing import draw_centered_text, draw_rounded_rect
from ...shared.isometric_projection import iso_project_point_3d
from ...shared.text_rendering import load_font

Color = Tuple[int, int, int]
FootprintCell = Tuple[int, int]
CubeCell = Tuple[int, int, int]
ViewCell = Tuple[int, int]

TOP_VIEW_QUERY = "top_view_visible_count"
FRONT_VIEW_QUERY = "front_view_visible_count"
RIGHT_VIEW_QUERY = "right_view_visible_count"
SUPPORTED_VIEW_QUERIES: Tuple[str, ...] = (
    TOP_VIEW_QUERY,
    FRONT_VIEW_QUERY,
    RIGHT_VIEW_QUERY,
)


@dataclass(frozen=True)
class CubeStack:
    """One sampled cube stack represented by footprint heights."""

    width: int
    depth: int
    heights: Dict[FootprintCell, int]

    @property
    def cube_count(self) -> int:
        """Return the total number of occupied cubes in the stack."""

        return int(sum(int(height) for height in self.heights.values()))

    @property
    def max_height(self) -> int:
        """Return the tallest stack height."""

        return max((int(height) for height in self.heights.values()), default=0)


@dataclass(frozen=True)
class SolidRenderStyle:
    """Resolved fill and text colors for solid-view scenes."""

    line_color: Color
    top_fill: Color
    left_fill: Color
    right_fill: Color
    panel_fill: Color
    panel_grid_color: Color
    panel_outline_color: Color
    panel_title_color: Color
    panel_title_stroke_color: Color


def _blend_rgb(source: Color, target: Color, *, toward_target: float) -> Color:
    """Blend two colors with one deterministic scalar."""

    alpha = max(0.0, min(1.0, float(toward_target)))
    return tuple(
        int(round((1.0 - alpha) * float(source[index]) + alpha * float(target[index])))
        for index in range(3)
    )


def build_solid_render_style(
    *,
    shape_style: GeometryShapeStyle,
    background_meta: Mapping[str, object] | None,
) -> SolidRenderStyle:
    """Derive cube/panel fills from the shared ink style."""

    background_rgb = (252, 252, 252)
    if isinstance(background_meta, Mapping):
        style_spec = background_meta.get("style_spec", {})
        if isinstance(style_spec, Mapping):
            raw_color = style_spec.get("background_rgb") or style_spec.get("color") or style_spec.get("base_color")
            if isinstance(raw_color, Sequence) and len(raw_color) >= 3:
                background_rgb = (
                    int(raw_color[0]),
                    int(raw_color[1]),
                    int(raw_color[2]),
                )

    line_color = tuple(int(value) for value in shape_style.line_color)
    return SolidRenderStyle(
        line_color=line_color,
        top_fill=_blend_rgb(line_color, background_rgb, toward_target=0.80),
        left_fill=_blend_rgb(line_color, background_rgb, toward_target=0.58),
        right_fill=_blend_rgb(line_color, background_rgb, toward_target=0.46),
        panel_fill=_blend_rgb(line_color, background_rgb, toward_target=0.96),
        panel_grid_color=_blend_rgb(line_color, background_rgb, toward_target=0.70),
        panel_outline_color=_blend_rgb(line_color, background_rgb, toward_target=0.12),
        panel_title_color=tuple(int(value) for value in shape_style.label_color),
        panel_title_stroke_color=tuple(int(value) for value in shape_style.label_stroke_color),
    )


def _neighbors(cell: FootprintCell, *, width: int, depth: int) -> Tuple[FootprintCell, ...]:
    """Return in-bounds 4-neighbors for one footprint cell."""

    x_value, y_value = int(cell[0]), int(cell[1])
    candidates = (
        (x_value - 1, y_value),
        (x_value + 1, y_value),
        (x_value, y_value - 1),
        (x_value, y_value + 1),
    )
    return tuple(
        (int(nx), int(ny))
        for nx, ny in candidates
        if 0 <= int(nx) < int(width) and 0 <= int(ny) < int(depth)
    )


def sample_connected_cube_stack(
    rng,
    *,
    width_min: int,
    width_max: int,
    depth_min: int,
    depth_max: int,
    total_cubes_min: int,
    total_cubes_max: int,
    max_height: int,
) -> CubeStack:
    """Sample one connected cube stack by growing a footprint + stacked heights."""

    width = int(rng.randint(int(width_min), int(width_max)))
    depth = int(rng.randint(int(depth_min), int(depth_max)))
    total_cubes_target = int(rng.randint(int(total_cubes_min), int(total_cubes_max)))
    heights: Dict[FootprintCell, int] = {
        (int(rng.randrange(width)), int(rng.randrange(depth))): 1,
    }

    while sum(int(value) for value in heights.values()) < int(total_cubes_target):
        weighted_options: List[Tuple[FootprintCell, str]] = []
        for x_value in range(int(width)):
            for y_value in range(int(depth)):
                cell = (int(x_value), int(y_value))
                height = int(heights.get(cell, 0))
                if int(height) > 0 and int(height) < int(max_height):
                    weighted_options.append((cell, "stack"))
                if int(height) == 0:
                    if any(int(heights.get(neighbor, 0)) > 0 for neighbor in _neighbors(cell, width=width, depth=depth)):
                        weighted_options.extend([(cell, "footprint")] * 3)
        if not weighted_options:
            raise ValueError("failed to grow connected cube stack within the requested support")
        selected_cell, _ = weighted_options[int(rng.randrange(len(weighted_options)))]
        heights[selected_cell] = int(heights.get(selected_cell, 0)) + 1

    return CubeStack(width=int(width), depth=int(depth), heights=dict(heights))


def occupied_cells_from_stack(stack: CubeStack) -> Tuple[CubeCell, ...]:
    """Expand one height map into occupied cube coordinates."""

    cells: List[CubeCell] = []
    for (x_value, y_value), height in sorted(stack.heights.items()):
        for z_value in range(int(height)):
            cells.append((int(x_value), int(y_value), int(z_value)))
    return tuple(cells)


def projected_view_cells(stack: CubeStack, *, query_id: str) -> Tuple[ViewCell, ...]:
    """Return normalized orthographic occupied cells for one requested query view."""

    occupied = set(occupied_cells_from_stack(stack))
    raw_cells: set[ViewCell] = set()
    normalized_query = str(query_id).strip().lower()
    if normalized_query == TOP_VIEW_QUERY:
        for (x_value, y_value), _height in stack.heights.items():
            row = int(stack.depth - 1 - int(y_value))
            raw_cells.add((int(x_value), int(row)))
    elif normalized_query == FRONT_VIEW_QUERY:
        for x_value in range(int(stack.width)):
            max_column_height = max(
                (int(height) for (cell_x, _cell_y), height in stack.heights.items() if int(cell_x) == int(x_value)),
                default=0,
            )
            for z_value in range(int(max_column_height)):
                row = int(stack.max_height - 1 - int(z_value))
                raw_cells.add((int(x_value), int(row)))
    elif normalized_query == RIGHT_VIEW_QUERY:
        for y_value in range(int(stack.depth)):
            max_column_height = max(
                (int(height) for (_cell_x, cell_y), height in stack.heights.items() if int(cell_y) == int(y_value)),
                default=0,
            )
            for z_value in range(int(max_column_height)):
                row = int(stack.max_height - 1 - int(z_value))
                raw_cells.add((int(y_value), int(row)))
    else:
        raise ValueError(f"unsupported solid-view query_id: {query_id}")
    if not raw_cells:
        return tuple()
    min_col = min(int(cell[0]) for cell in raw_cells)
    min_row = min(int(cell[1]) for cell in raw_cells)
    normalized_cells = {
        (int(cell[0]) - int(min_col), int(cell[1]) - int(min_row))
        for cell in raw_cells
    }
    return tuple(sorted(normalized_cells, key=lambda item: (int(item[1]), int(item[0]))))


def view_grid_dimensions(stack: CubeStack, *, query_id: str) -> Tuple[int, int]:
    """Return orthographic grid width/height for one query view."""

    cells = projected_view_cells(stack, query_id=str(query_id))
    if not cells:
        raise ValueError("solid-view grid dimensions require at least one occupied projected cell")
    max_col = max(int(cell[0]) for cell in cells)
    max_row = max(int(cell[1]) for cell in cells)
    return (int(max_col + 1), int(max_row + 1))


def view_title_for_query(query_id: str) -> str:
    """Return the human-readable panel title for one query view."""

    title_map = {
        TOP_VIEW_QUERY: "Top view",
        FRONT_VIEW_QUERY: "Front view",
        RIGHT_VIEW_QUERY: "Right view",
    }
    normalized_query = str(query_id).strip().lower()
    if normalized_query not in title_map:
        raise ValueError(f"unsupported solid-view query_id: {query_id}")
    return str(title_map[normalized_query])


def draw_query_view_panel(
    draw: ImageDraw.ImageDraw,
    *,
    panel_bbox: Tuple[float, float, float, float],
    grid_dims: Tuple[int, int],
    occupied_cells: Sequence[ViewCell],
    scene_scale: int,
    line_width: int,
    title_text: str,
    title_font_size_px: int,
    style: SolidRenderStyle,
) -> Dict[str, object]:
    """Draw one blank orthographic query panel and return cell bbox metadata."""

    left, top, right, bottom = [float(value) for value in panel_bbox]
    panel_top = float(top)
    panel_outline_width = max(1, int(line_width))
    draw_rounded_rect(
        draw,
        (left, top, right, bottom),
        radius=max(8, int(round(10 * int(scene_scale)))),
        fill=style.panel_fill,
        outline=style.panel_outline_color,
        width=panel_outline_width,
    )

    title_font = load_font(int(title_font_size_px), bold=True)
    title_bbox = draw_centered_text(
        draw,
        text=str(title_text),
        center=((left + right) * 0.5, top + (18.0 * float(scene_scale))),
        font=title_font,
        fill=style.panel_title_color,
        stroke_fill=style.panel_title_stroke_color,
        stroke_width=max(1, int(scene_scale)),
    )
    title_bottom = float(title_bbox[3])
    cols, rows = int(grid_dims[0]), int(grid_dims[1])
    if int(cols) <= 0 or int(rows) <= 0:
        raise ValueError("query panel grid dimensions must be positive")

    inner_padding = 16.0 * float(scene_scale)
    grid_top = float(title_bottom + (12.0 * float(scene_scale)))
    grid_left = float(left + inner_padding)
    grid_right = float(right - inner_padding)
    grid_bottom = float(bottom - inner_padding)
    usable_width = max(20.0, float(grid_right - grid_left))
    usable_height = max(20.0, float(grid_bottom - grid_top))
    cell_side = min(float(usable_width / cols), float(usable_height / rows))
    grid_width = float(cell_side * cols)
    grid_height = float(cell_side * rows)
    grid_left = float(grid_left + ((usable_width - grid_width) * 0.5))
    grid_top = float(grid_top + ((usable_height - grid_height) * 0.5))

    cell_bbox_by_coord: Dict[str, List[float]] = {}
    for col in range(int(cols)):
        for row in range(int(rows)):
            x0 = float(grid_left + (float(col) * cell_side))
            y0 = float(grid_top + (float(row) * cell_side))
            x1 = float(x0 + cell_side)
            y1 = float(y0 + cell_side)
            draw.rectangle(
                (x0, y0, x1, y1),
                outline=style.panel_grid_color,
                width=max(1, panel_outline_width),
            )
            cell_bbox_by_coord[f"{col},{row}"] = [
                round(x0 / float(scene_scale), 3),
                round(y0 / float(scene_scale), 3),
                round(x1 / float(scene_scale), 3),
                round(y1 / float(scene_scale), 3),
            ]

    occupied_bboxes = [
        list(cell_bbox_by_coord[f"{int(col)},{int(row)}"])
        for col, row in occupied_cells
    ]
    return {
        "panel_bbox": [
            round(float(left) / float(scene_scale), 3),
            round(float(top) / float(scene_scale), 3),
            round(float(right) / float(scene_scale), 3),
            round(float(bottom) / float(scene_scale), 3),
        ],
        "grid_bbox": [
            round(float(grid_left) / float(scene_scale), 3),
            round(float(grid_top) / float(scene_scale), 3),
            round(float(grid_left + grid_width) / float(scene_scale), 3),
            round(float(grid_top + grid_height) / float(scene_scale), 3),
        ],
        "cell_bboxes_by_coord": dict(cell_bbox_by_coord),
        "occupied_bboxes": list(occupied_bboxes),
    }


def draw_cube_stack_panel(
    draw: ImageDraw.ImageDraw,
    *,
    panel_bbox: Tuple[float, float, float, float],
    stack: CubeStack,
    scene_scale: int,
    line_width: int,
    title_text: str,
    title_font_size_px: int,
    style: SolidRenderStyle,
    voxel_scale: float = 1.0,
) -> Dict[str, object]:
    """Draw one isometric cube stack inside the requested panel bbox."""

    left, top, right, bottom = [float(value) for value in panel_bbox]
    panel_top = float(top)
    draw_rounded_rect(
        draw,
        (left, top, right, bottom),
        radius=max(8, int(round(10 * int(scene_scale)))),
        fill=style.panel_fill,
        outline=style.panel_outline_color,
        width=max(1, int(line_width)),
    )
    title_font = load_font(int(title_font_size_px), bold=True)
    title_bbox = draw_centered_text(
        draw,
        text=str(title_text),
        center=((left + right) * 0.5, top + (18.0 * float(scene_scale))),
        font=title_font,
        fill=style.panel_title_color,
        stroke_fill=style.panel_title_stroke_color,
        stroke_width=max(1, int(scene_scale)),
    )
    occupied = set(occupied_cells_from_stack(stack))
    if not occupied:
        raise ValueError("cube stack must contain at least one occupied cube")

    raw_points: List[Tuple[float, float]] = []
    cube_faces: List[Tuple[int, Tuple[Tuple[float, float], ...], Color]] = []
    for x_value, y_value, z_value in sorted(occupied, key=lambda cell: (int(cell[0]) + int(cell[1]) + int(cell[2]), int(cell[2]), int(cell[1]), int(cell[0]))):
        cube_points_3d = {
            "000": (float(x_value), float(y_value), float(z_value)),
            "100": (float(x_value + 1), float(y_value), float(z_value)),
            "010": (float(x_value), float(y_value + 1), float(z_value)),
            "110": (float(x_value + 1), float(y_value + 1), float(z_value)),
            "001": (float(x_value), float(y_value), float(z_value + 1)),
            "101": (float(x_value + 1), float(y_value), float(z_value + 1)),
            "011": (float(x_value), float(y_value + 1), float(z_value + 1)),
            "111": (float(x_value + 1), float(y_value + 1), float(z_value + 1)),
        }
        projected = {key: iso_project_point_3d(point) for key, point in cube_points_3d.items()}
        raw_points.extend(projected.values())
        if (int(x_value), int(y_value), int(z_value + 1)) not in occupied:
            cube_faces.append(
                (
                    int(x_value + y_value + z_value),
                    (
                        projected["001"],
                        projected["101"],
                        projected["111"],
                        projected["011"],
                    ),
                    style.top_fill,
                )
            )
        if (int(x_value + 1), int(y_value), int(z_value)) not in occupied:
            cube_faces.append(
                (
                    int(x_value + y_value + z_value) + 1,
                    (
                        projected["100"],
                        projected["110"],
                        projected["111"],
                        projected["101"],
                    ),
                    style.right_fill,
                )
            )
        if (int(x_value), int(y_value + 1), int(z_value)) not in occupied:
            cube_faces.append(
                (
                    int(x_value + y_value + z_value) + 1,
                    (
                        projected["010"],
                        projected["110"],
                        projected["111"],
                        projected["011"],
                    ),
                    style.left_fill,
                )
            )

    min_x = min(point[0] for point in raw_points)
    max_x = max(point[0] for point in raw_points)
    min_y = min(point[1] for point in raw_points)
    max_y = max(point[1] for point in raw_points)
    raw_width = max(1e-6, float(max_x - min_x))
    raw_height = max(1e-6, float(max_y - min_y))
    padding = 24.0 * float(scene_scale)
    content_top = float(max(top, title_bbox[3] + (12.0 * float(scene_scale))))
    usable_width = max(24.0, float((right - left) - (2.0 * padding)))
    usable_height = max(24.0, float((bottom - content_top) - (2.0 * padding)))
    scale = min(float(usable_width / raw_width), float(usable_height / raw_height))
    resolved_voxel_scale = max(0.50, min(1.00, float(voxel_scale)))
    scale *= float(resolved_voxel_scale)
    center_raw_x = 0.5 * (float(min_x) + float(max_x))
    center_raw_y = 0.5 * (float(min_y) + float(max_y))
    center_panel_x = 0.5 * (float(left) + float(right))
    center_panel_y = 0.5 * (float(content_top) + float(bottom))

    def _transform(point: Tuple[float, float]) -> Tuple[float, float]:
        return (
            float(center_panel_x + ((float(point[0]) - float(center_raw_x)) * float(scale))),
            float(center_panel_y + ((float(point[1]) - float(center_raw_y)) * float(scale))),
        )

    for _depth_key, raw_face_points, fill_color in sorted(cube_faces, key=lambda item: int(item[0])):
        face_points = [_transform(point) for point in raw_face_points]
        draw.polygon(face_points, fill=fill_color)
        closed = list(face_points) + [face_points[0]]
        draw.line(closed, fill=style.line_color, width=max(1, int(line_width)), joint="curve")

    return {
        "panel_bbox": [
            round(float(left) / float(scene_scale), 3),
            round(float(panel_top) / float(scene_scale), 3),
            round(float(right) / float(scene_scale), 3),
            round(float(bottom) / float(scene_scale), 3),
        ],
        "cube_count": int(stack.cube_count),
        "voxel_scale": round(float(resolved_voxel_scale), 4),
    }
