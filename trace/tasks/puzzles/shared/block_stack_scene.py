"""Shared rendering helpers for spatial block-stack puzzle scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.isometric_projection import iso_project_point_3d
from ...shared.text_rendering import load_font
from .drawing import draw_arrow, draw_centered_text, draw_rounded_rect
from .spatial_blocks_common import PuzzleBlockStackRenderParams

Point2 = Tuple[float, float]
Point3 = Tuple[float, float, float]


SUPPORTED_PUZZLE_BLOCK_SCENE_VARIANTS: Tuple[str, ...] = (
    "stack_strip",
    "stack_card",
    "stack_outline",
)


@dataclass(frozen=True)
class RenderedPuzzleBlockComparisonScene:
    """Rendered block-comparison scene plus traced geometry."""

    image: Any
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    original_structure_bbox_px: List[float]
    remaining_structure_bbox_px: List[float]
    structure_bbox_map: Dict[str, List[float]]


def _scene_panel_style(
    scene_variant: str,
    *,
    render_params: PuzzleBlockStackRenderParams,
) -> Tuple[Tuple[int, int, int] | None, Tuple[int, int, int] | None]:
    """Resolve outer scene-panel fill and outline styling."""

    if str(scene_variant) == "stack_outline":
        return None, render_params.border_color_rgb
    if str(scene_variant) == "stack_strip":
        return render_params.instruction_fill_rgb, None
    return render_params.panel_fill_rgb, render_params.border_color_rgb


def _cube_face_vertices(
    *,
    row_index: int,
    col_index: int,
    level_index: int,
    face_type: str,
) -> Tuple[Point3, Point3, Point3, Point3]:
    """Return the 3D vertices for one visible cube face."""

    x0 = float(col_index)
    x1 = float(col_index + 1)
    y0 = float(row_index)
    y1 = float(row_index + 1)
    z0 = float(level_index)
    z1 = float(level_index + 1)
    if str(face_type) == "top":
        return ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))
    if str(face_type) == "right":
        return ((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1))
    if str(face_type) == "front":
        return ((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1))
    raise ValueError(f"unsupported cube face type: {face_type}")


def _visible_face_vertices(cube_records: Sequence[Mapping[str, Any]]) -> List[Point3]:
    """Collect 3D vertices from all visible faces in one structure."""

    vertices: List[Point3] = []
    for record in cube_records:
        for face_type in ("front", "right", "top"):
            if not bool(record["visible_faces"][str(face_type)]):
                continue
            vertices.extend(
                _cube_face_vertices(
                    row_index=int(record["row_index"]),
                    col_index=int(record["col_index"]),
                    level_index=int(record["level_index"]),
                    face_type=str(face_type),
                )
            )
    return vertices


def _raw_projected_points(points_3d: Iterable[Point3]) -> Dict[Point3, Point2]:
    """Project a 3D point set into raw isometric 2D coordinates."""

    return {tuple(float(value) for value in point): iso_project_point_3d(point) for point in points_3d}


def _fit_projected_points_with_shared_scale(
    points_3d: Iterable[Point3],
    *,
    target_bbox: Sequence[float],
    shared_raw_width: float,
    shared_raw_height: float,
) -> Dict[Point3, Point2]:
    """Project and fit one 3D point set into the target bbox with a shared scale."""

    projected = _raw_projected_points(points_3d)
    x_values = [float(point[0]) for point in projected.values()]
    y_values = [float(point[1]) for point in projected.values()]
    min_x, max_x = min(x_values), max(x_values)
    min_y, max_y = min(y_values), max(y_values)
    raw_center_x = 0.5 * (float(min_x) + float(max_x))
    raw_center_y = 0.5 * (float(min_y) + float(max_y))
    left, top, right, bottom = [float(value) for value in target_bbox]
    usable_width = float(right - left)
    usable_height = float(bottom - top)
    scale = min(
        float(usable_width / max(1e-6, float(shared_raw_width))),
        float(usable_height / max(1e-6, float(shared_raw_height))),
    )
    target_center_x = 0.5 * (float(left) + float(right))
    target_center_y = 0.5 * (float(top) + float(bottom))
    return {
        key: (
            float((float(value[0]) - raw_center_x) * float(scale) + target_center_x),
            float((float(value[1]) - raw_center_y) * float(scale) + target_center_y),
        )
        for key, value in projected.items()
    }


def _build_structure_faces(
    *,
    structure_id: str,
    cube_records: Sequence[Mapping[str, Any]],
    target_bbox: Sequence[float],
    render_params: PuzzleBlockStackRenderParams,
    shared_raw_width: float,
    shared_raw_height: float,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[float]]:
    """Build visible face draw specs, entities, and one structure bbox."""

    all_face_vertices = _visible_face_vertices(cube_records)
    if not all_face_vertices:
        raise ValueError("block comparison scene must contain at least one visible face")
    projected_point_map = _fit_projected_points_with_shared_scale(
        all_face_vertices,
        target_bbox=target_bbox,
        shared_raw_width=float(shared_raw_width),
        shared_raw_height=float(shared_raw_height),
    )

    faces: List[Dict[str, Any]] = []
    for record in cube_records:
        visible_faces = dict(record["visible_faces"])
        for face_type in ("front", "right", "top"):
            if not bool(visible_faces[str(face_type)]):
                continue
            vertices_3d = _cube_face_vertices(
                row_index=int(record["row_index"]),
                col_index=int(record["col_index"]),
                level_index=int(record["level_index"]),
                face_type=str(face_type),
            )
            polygon = [projected_point_map[tuple(float(value) for value in vertex)] for vertex in vertices_3d]
            depth = float(record["row_index"]) + float(record["col_index"]) + float(record["level_index"])
            if str(face_type) == "front":
                fill_rgb = render_params.face_left_rgb
                depth += 0.2
            elif str(face_type) == "right":
                fill_rgb = render_params.face_right_rgb
                depth += 0.3
            else:
                fill_rgb = render_params.face_top_rgb
                depth += 0.8
            faces.append(
                {
                    "cube_id": str(record["cube_id"]),
                    "face_type": str(face_type),
                    "polygon": list(polygon),
                    "depth": float(depth),
                    "fill_rgb": tuple(int(value) for value in fill_rgb),
                    "row_index": int(record["row_index"]),
                    "col_index": int(record["col_index"]),
                    "level_index": int(record["level_index"]),
                }
            )

    faces.sort(key=lambda item: (float(item["depth"]), int(item["row_index"]), int(item["col_index"]), int(item["level_index"])))

    face_entities: List[Dict[str, Any]] = []
    all_points: List[Point2] = []
    for index, face in enumerate(faces, start=1):
        polygon = [(float(point[0]), float(point[1])) for point in face["polygon"]]
        all_points.extend(polygon)
        x_values = [float(point[0]) for point in polygon]
        y_values = [float(point[1]) for point in polygon]
        face_entities.append(
            {
                "entity_id": f"{str(structure_id)}_face_{int(index)}",
                "entity_type": "puzzle_block_face",
                "bbox_px": [
                    round(min(x_values), 3),
                    round(min(y_values), 3),
                    round(max(x_values), 3),
                    round(max(y_values), 3),
                ],
                "attrs": {
                    "structure_id": str(structure_id),
                    "cube_id": str(face["cube_id"]),
                    "face_type": str(face["face_type"]),
                },
            }
        )

    structure_bbox = [
        round(min(float(point[0]) for point in all_points), 3),
        round(min(float(point[1]) for point in all_points), 3),
        round(max(float(point[0]) for point in all_points), 3),
        round(max(float(point[1]) for point in all_points), 3),
    ]
    return faces, face_entities, structure_bbox


def render_puzzle_block_comparison_scene(
    background,
    *,
    scene_variant: str,
    original_height_rows: Sequence[Sequence[int]],
    original_cube_records: Sequence[Mapping[str, Any]],
    remaining_height_rows: Sequence[Sequence[int]],
    remaining_cube_records: Sequence[Mapping[str, Any]],
    render_params: PuzzleBlockStackRenderParams,
) -> RenderedPuzzleBlockComparisonScene:
    """Render one original-vs-remaining block comparison scene."""

    canvas = background.copy().convert("RGB")
    draw = ImageDraw.Draw(canvas)
    border_width = max(1, int(render_params.border_width_px))

    scene_left = float(render_params.scene_margin_left_px)
    scene_top = float(render_params.scene_margin_top_px)
    scene_right = float(render_params.canvas_width - render_params.scene_margin_right_px)
    scene_bottom = float(render_params.canvas_height - render_params.scene_margin_bottom_px)
    scene_bbox = [
        round(float(scene_left), 3),
        round(float(scene_top), 3),
        round(float(scene_right), 3),
        round(float(scene_bottom), 3),
    ]

    scene_fill, scene_outline = _scene_panel_style(str(scene_variant), render_params=render_params)
    if scene_fill is not None or scene_outline is not None:
        draw_rounded_rect(
            draw,
            tuple(float(value) for value in scene_bbox),
            radius=int(render_params.panel_corner_radius_px),
            fill=scene_fill if scene_fill is not None else (255, 255, 255),
            outline=scene_outline if scene_outline is not None else (255, 255, 255),
            width=max(1, int(border_width if scene_outline is not None else 1)),
        )

    caption_font = load_font(int(render_params.caption_font_size_px), bold=True)
    caption_band_top = float(scene_top + int(render_params.structure_padding_px))
    caption_band_bottom = float(caption_band_top + int(render_params.caption_font_size_px))
    content_top = float(caption_band_bottom + int(render_params.caption_gap_px))
    content_left = float(scene_left + int(render_params.structure_padding_px))
    content_right = float(scene_right - int(render_params.structure_padding_px))
    content_bottom = float(scene_bottom - int(render_params.structure_padding_px))
    pair_gap = float(render_params.structure_pair_gap_px)
    structure_width = float(max(1.0, (content_right - content_left - pair_gap) / 2.0))
    left_target_bbox = (
        float(content_left),
        float(content_top),
        float(content_left + structure_width),
        float(content_bottom),
    )
    right_target_bbox = (
        float(content_left + structure_width + pair_gap),
        float(content_top),
        float(content_right),
        float(content_bottom),
    )

    original_vertices = _visible_face_vertices(original_cube_records)
    remaining_vertices = _visible_face_vertices(remaining_cube_records)
    raw_original = _raw_projected_points(original_vertices)
    raw_remaining = _raw_projected_points(remaining_vertices)
    shared_raw_width = max(
        max(float(point[0]) for point in raw_original.values()) - min(float(point[0]) for point in raw_original.values()),
        max(float(point[0]) for point in raw_remaining.values()) - min(float(point[0]) for point in raw_remaining.values()),
    )
    shared_raw_height = max(
        max(float(point[1]) for point in raw_original.values()) - min(float(point[1]) for point in raw_original.values()),
        max(float(point[1]) for point in raw_remaining.values()) - min(float(point[1]) for point in raw_remaining.values()),
    )
    shared_raw_width = max(1e-6, float(shared_raw_width))
    shared_raw_height = max(1e-6, float(shared_raw_height))

    original_faces, original_face_entities, original_structure_bbox = _build_structure_faces(
        structure_id="original_structure",
        cube_records=original_cube_records,
        target_bbox=left_target_bbox,
        render_params=render_params,
        shared_raw_width=float(shared_raw_width),
        shared_raw_height=float(shared_raw_height),
    )
    remaining_faces, remaining_face_entities, remaining_structure_bbox = _build_structure_faces(
        structure_id="remaining_structure",
        cube_records=remaining_cube_records,
        target_bbox=right_target_bbox,
        render_params=render_params,
        shared_raw_width=float(shared_raw_width),
        shared_raw_height=float(shared_raw_height),
    )

    all_faces = []
    for structure_id, faces in (
        ("original_structure", original_faces),
        ("remaining_structure", remaining_faces),
    ):
        for face in faces:
            all_faces.append({**face, "structure_id": str(structure_id)})
    all_faces.sort(
        key=lambda item: (
            float(item["depth"]),
            str(item["structure_id"]),
            int(item["row_index"]),
            int(item["col_index"]),
            int(item["level_index"]),
        )
    )
    for face in all_faces:
        polygon = [(float(point[0]), float(point[1])) for point in face["polygon"]]
        draw.polygon(
            polygon,
            fill=tuple(int(value) for value in face["fill_rgb"]),
            outline=tuple(int(value) for value in render_params.border_color_rgb),
        )

    original_caption_bbox = draw_centered_text(
        draw,
        text="Original",
        center=(0.5 * (float(left_target_bbox[0]) + float(left_target_bbox[2])), 0.5 * (caption_band_top + caption_band_bottom)),
        font=caption_font,
        fill=render_params.caption_fill_rgb,
        stroke_fill=render_params.caption_stroke_rgb,
        stroke_width=1,
    )
    remaining_caption_bbox = draw_centered_text(
        draw,
        text="After",
        center=(0.5 * (float(right_target_bbox[0]) + float(right_target_bbox[2])), 0.5 * (caption_band_top + caption_band_bottom)),
        font=caption_font,
        fill=render_params.caption_fill_rgb,
        stroke_fill=render_params.caption_stroke_rgb,
        stroke_width=1,
    )
    arrow_start = (
        float(left_target_bbox[2] + (0.18 * pair_gap)),
        float(0.5 * (content_top + content_bottom)),
    )
    arrow_end = (
        float(right_target_bbox[0] - (0.18 * pair_gap)),
        float(0.5 * (content_top + content_bottom)),
    )
    draw_arrow(
        draw,
        start=arrow_start,
        end=arrow_end,
        fill=render_params.arrow_rgb,
        width=int(render_params.arrow_width_px),
        head_length_px=float(render_params.arrow_head_length_px),
        head_width_px=float(render_params.arrow_head_width_px),
    )
    arrow_bbox = [
        round(min(float(arrow_start[0]), float(arrow_end[0])), 3),
        round(min(float(arrow_start[1]), float(arrow_end[1])) - float(render_params.arrow_head_width_px), 3),
        round(max(float(arrow_start[0]), float(arrow_end[0])), 3),
        round(max(float(arrow_start[1]), float(arrow_end[1])) + float(render_params.arrow_head_width_px), 3),
    ]

    structure_bbox_map = {
        "original_structure": list(original_structure_bbox),
        "remaining_structure": list(remaining_structure_bbox),
    }
    entities: List[Dict[str, Any]] = [
        {
            "entity_id": "original_structure",
            "entity_type": "puzzle_block_structure",
            "bbox_px": list(original_structure_bbox),
            "attrs": {
                "structure_role": "original",
                "row_count": int(len(original_height_rows)),
                "col_count": int(len(original_height_rows[0])) if original_height_rows else 0,
            },
        },
        {
            "entity_id": "remaining_structure",
            "entity_type": "puzzle_block_structure",
            "bbox_px": list(remaining_structure_bbox),
            "attrs": {
                "structure_role": "remaining",
                "row_count": int(len(remaining_height_rows)),
                "col_count": int(len(remaining_height_rows[0])) if remaining_height_rows else 0,
            },
        },
        {
            "entity_id": "original_caption",
            "entity_type": "puzzle_block_caption",
            "bbox_px": list(original_caption_bbox),
            "attrs": {"structure_role": "original", "text": "Original"},
        },
        {
            "entity_id": "remaining_caption",
            "entity_type": "puzzle_block_caption",
            "bbox_px": list(remaining_caption_bbox),
            "attrs": {"structure_role": "remaining", "text": "After"},
        },
        {
            "entity_id": "block_transition_arrow",
            "entity_type": "puzzle_block_arrow",
            "bbox_px": list(arrow_bbox),
            "attrs": {},
        },
    ]
    entities.extend(original_face_entities)
    entities.extend(remaining_face_entities)

    return RenderedPuzzleBlockComparisonScene(
        image=canvas,
        entities=entities,
        scene_bbox_px=list(scene_bbox),
        original_structure_bbox_px=list(original_structure_bbox),
        remaining_structure_bbox_px=list(remaining_structure_bbox),
        structure_bbox_map=structure_bbox_map,
    )


__all__ = [
    "RenderedPuzzleBlockComparisonScene",
    "SUPPORTED_PUZZLE_BLOCK_SCENE_VARIANTS",
    "render_puzzle_block_comparison_scene",
]
