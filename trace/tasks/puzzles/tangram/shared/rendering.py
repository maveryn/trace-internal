"""Rendering helpers for Tangram puzzle scenes."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw

from trace.tasks.puzzles.shared.drawing import draw_rounded_rect
from trace.tasks.puzzles.shared.marking import (
    draw_semantic_ellipse_marker,
    draw_semantic_polygon_marker,
    resolve_semantic_marker_style,
)
from trace.tasks.puzzles.shared.option_layout import (
    centered_option_grid_shape,
    centered_option_row_counts,
)
from trace.tasks.puzzles.shared.option_panels import render_puzzle_option_panel
from trace.tasks.shared.text_rendering import load_font

from .spatial_primitives import (
    PIECE_FILLS,
    centroid,
    flatten_points,
    normalize_points_to_box,
    rotate_points,
    round_bbox,
)
from .state import (
    OptionSpec,
    Point,
    RenderedTangramScene,
    TangramRenderParams,
    TangramSample,
)


def _scene_variant_rotation(scene_variant: str) -> float:
    """Return the assembly rotation for one scene treatment."""

    angle_by_variant = {
        "tangram_square": 0.0,
        "tangram_diamond": 45.0,
        "tangram_tilted": -16.0,
    }
    return float(angle_by_variant.get(str(scene_variant), 0.0))


def _piece_layout_points(
    *,
    sample: TangramSample,
    scene_variant: str,
    assembly_box: Sequence[float],
) -> dict[str, list[Point]]:
    """Project normalized assembly pieces into the assembly panel."""

    angle = _scene_variant_rotation(str(scene_variant))
    transformed: dict[str, list[Point]] = {}
    for piece in sample.piece_specs:
        transformed[str(piece.piece_id)] = rotate_points(
            piece.points,
            degrees=angle,
            center=(2.0, 2.0),
        )
    return {
        piece_id: normalize_points_to_box(
            points,
            assembly_box,
            padding_px=0.0,
        )
        for piece_id, points in transformed.items()
    }


def _draw_polygon(
    draw: ImageDraw.ImageDraw,
    points: Sequence[Point],
    *,
    fill: Sequence[int],
    outline: Sequence[int],
    width: int,
) -> None:
    """Draw one filled polygon with a stable outline."""

    int_points = [(int(round(x)), int(round(y))) for x, y in points]
    draw.polygon(
        int_points,
        fill=tuple(int(value) for value in fill),
        outline=tuple(int(value) for value in outline),
    )
    if int(width) > 1:
        draw.line(
            int_points + [int_points[0]],
            fill=tuple(int(value) for value in outline),
            width=int(width),
            joint="curve",
        )


def _draw_target_marker(
    draw: ImageDraw.ImageDraw,
    points: Sequence[Point],
    *,
    render_params: TangramRenderParams,
    piece_fill_rgb: Sequence[int],
    piece_id: str,
) -> None:
    """Draw the red semantic marker for one counted Tangram piece."""

    marker_style = resolve_semantic_marker_style(
        instance_seed=int(render_params.instance_seed),
        namespace=f"puzzles.tangram.marked_piece.{piece_id}",
        role="tangram_marked_piece",
        surface_rgbs=(
            tuple(int(value) for value in piece_fill_rgb),
            tuple(int(value) for value in render_params.assembly_panel_fill_rgb),
        ),
        preferred_rgbs=(
            tuple(int(value) for value in render_params.marked_outline_rgb),
        ),
    )
    int_points = [(int(round(x)), int(round(y))) for x, y in points]
    draw_semantic_polygon_marker(
        draw,
        int_points,
        style=marker_style,
        width=int(render_params.highlight_width_px),
        marker_kind="tangram_marked_piece_outline",
        extra_metadata={"piece_id": str(piece_id)},
    )
    cx, cy = centroid(points)
    radius = max(7, int(render_params.highlight_width_px) + 4)
    draw_semantic_ellipse_marker(
        draw,
        (cx - radius, cy - radius, cx + radius, cy + radius),
        style=marker_style,
        width=max(2, int(render_params.highlight_width_px // 2)),
        fill_rgba=(
            int(marker_style.outer_rgb[0]),
            int(marker_style.outer_rgb[1]),
            int(marker_style.outer_rgb[2]),
            235,
        ),
        marker_kind="tangram_marked_piece_center",
        extra_metadata={"piece_id": str(piece_id)},
    )


def _option_layout_bboxes(
    *,
    render_params: TangramRenderParams,
    option_count: int,
    top_y: float,
) -> list[tuple[float, float, float, float]]:
    """Return centered option-panel boxes for 4 to 6 visual options."""

    cols, _rows = centered_option_grid_shape(int(option_count))
    row_counts = centered_option_row_counts(int(option_count), int(cols))
    total_width = float(
        int(cols) * int(render_params.option_panel_width_px)
        + (int(cols) - 1) * int(render_params.option_gap_px)
    )
    start_x = 0.5 * (float(render_params.canvas_width) - total_width)
    bboxes: list[tuple[float, float, float, float]] = []
    for row_index, row_count in enumerate(row_counts):
        row_width = float(
            int(row_count) * int(render_params.option_panel_width_px)
            + (int(row_count) - 1) * int(render_params.option_gap_px)
        )
        row_start_x = float(start_x + 0.5 * (total_width - row_width))
        y0 = float(
            top_y
            + row_index
            * (
                int(render_params.option_panel_height_px)
                + int(render_params.option_row_gap_px)
            )
        )
        for col in range(int(row_count)):
            x0 = float(
                row_start_x
                + col
                * (
                    int(render_params.option_panel_width_px)
                    + int(render_params.option_gap_px)
                )
            )
            bboxes.append(
                (
                    x0,
                    y0,
                    x0 + float(render_params.option_panel_width_px),
                    y0 + float(render_params.option_panel_height_px),
                )
            )
    if bboxes:
        max_right = max(float(bbox[2]) for bbox in bboxes)
        max_bottom = max(float(bbox[3]) for bbox in bboxes)
        if max_right > float(render_params.canvas_width) or max_bottom > float(
            render_params.canvas_height
        ):
            raise ValueError(
                "Tangram option panel layout exceeds canvas: "
                f"right={max_right:.1f}/{render_params.canvas_width}, "
                f"bottom={max_bottom:.1f}/{render_params.canvas_height}"
            )
    return bboxes


def _draw_option_shape(
    draw: ImageDraw.ImageDraw,
    *,
    option: OptionSpec,
    content_bbox: Sequence[float],
    render_params: TangramRenderParams,
) -> None:
    """Draw one candidate missing-piece shape inside its option panel."""

    points = normalize_points_to_box(
        option.shape_points,
        content_bbox,
        padding_px=12.0,
        rotation_degrees=float(option.display_rotation_degrees),
    )
    fill = tuple(int(value) for value in render_params.missing_fill_rgb)
    outline = tuple(int(value) for value in render_params.seam_color_rgb)
    _draw_polygon(
        draw,
        points,
        fill=fill,
        outline=outline,
        width=max(2, int(render_params.seam_width_px)),
    )


def render_tangram_scene(
    base_image: Image.Image,
    *,
    sample: TangramSample,
    scene_variant: str,
    render_params: TangramRenderParams,
) -> RenderedTangramScene:
    """Render one Tangram scene and return traceable bboxes."""

    image = base_image.convert("RGB")
    draw = ImageDraw.Draw(image)
    assembly_panel_bbox = (
        float(
            0.5 * (render_params.canvas_width - render_params.assembly_panel_width_px)
        ),
        float(render_params.scene_margin_top_px),
        float(
            0.5 * (render_params.canvas_width + render_params.assembly_panel_width_px)
        ),
        float(
            render_params.scene_margin_top_px + render_params.assembly_panel_height_px
        ),
    )
    option_top_y = float(
        assembly_panel_bbox[3] + render_params.assembly_to_options_gap_px
    )
    scene_bbox = (
        float(render_params.scene_margin_left_px),
        float(render_params.scene_margin_top_px),
        float(render_params.canvas_width - render_params.scene_margin_right_px),
        float(render_params.canvas_height - render_params.scene_margin_bottom_px),
    )
    draw_rounded_rect(
        draw,
        scene_bbox,
        radius=int(render_params.panel_corner_radius_px),
        fill=render_params.panel_fill_rgb,
        outline=render_params.border_color_rgb,
        width=int(render_params.border_width_px),
    )
    draw_rounded_rect(
        draw,
        assembly_panel_bbox,
        radius=int(render_params.panel_corner_radius_px),
        fill=render_params.assembly_panel_fill_rgb,
        outline=render_params.border_color_rgb,
        width=int(render_params.border_width_px),
    )

    assembly_box = (
        float(assembly_panel_bbox[0] + render_params.assembly_panel_padding_px),
        float(assembly_panel_bbox[1] + render_params.assembly_panel_padding_px),
        float(assembly_panel_bbox[2] - render_params.assembly_panel_padding_px),
        float(assembly_panel_bbox[3] - render_params.assembly_panel_padding_px),
    )
    piece_points = _piece_layout_points(
        sample=sample,
        scene_variant=str(scene_variant),
        assembly_box=assembly_box,
    )
    piece_bbox_map = {
        piece_id: round_bbox(points) for piece_id, points in piece_points.items()
    }
    assembly_bbox = round_bbox(flatten_points(piece_points.values()))
    piece_fill_map = {
        str(piece.piece_id): PIECE_FILLS[index % len(PIECE_FILLS)]
        for index, piece in enumerate(sample.piece_specs)
    }

    target_piece_ids = set(str(item) for item in sample.target_piece_ids)
    contact_piece_ids = set(str(item) for item in sample.contact_piece_ids)
    entities: list[dict[str, Any]] = []
    for piece in sample.piece_specs:
        piece_id = str(piece.piece_id)
        points = piece_points[piece_id]
        if sample.option_specs and piece_id == sample.target_piece_id:
            fill = render_params.missing_fill_rgb
            outline = render_params.marked_outline_rgb
            width = max(
                int(render_params.seam_width_px),
                int(render_params.highlight_width_px) // 2,
            )
        else:
            fill = piece_fill_map[piece_id]
            outline = render_params.seam_color_rgb
            width = int(render_params.seam_width_px)
        _draw_polygon(draw, points, fill=fill, outline=outline, width=width)
        entities.append(
            {
                "id": piece_id,
                "type": "tangram_piece",
                "shape_id": str(piece.shape_id),
                "shape_name": str(piece.shape_name),
                "bbox_px": list(piece_bbox_map[piece_id]),
                "is_target": bool(piece_id in target_piece_ids),
                "touches_target": bool(piece_id in contact_piece_ids),
            }
        )

    if not sample.option_specs:
        for marked_piece_id in sample.target_piece_ids:
            _draw_target_marker(
                draw,
                piece_points[str(marked_piece_id)],
                render_params=render_params,
                piece_fill_rgb=piece_fill_map[str(marked_piece_id)],
                piece_id=str(marked_piece_id),
            )

    option_panel_bbox_map: dict[str, list[float]] = {}
    if sample.option_specs:
        label_font = load_font(int(render_params.option_label_font_size_px), bold=True)
        option_bboxes = _option_layout_bboxes(
            render_params=render_params,
            option_count=int(sample.option_count),
            top_y=float(option_top_y),
        )
        for option, panel_bbox in zip(sample.option_specs, option_bboxes):
            rendered_panel = render_puzzle_option_panel(
                draw,
                panel_bbox=panel_bbox,
                option_label=str(option.option_label),
                label_font=label_font,
                label_center_y_px=float(panel_bbox[1] + 24),
                content_box_size_px=float(render_params.option_shape_box_size_px),
                content_gap_px=float(render_params.option_label_gap_px),
                panel_fill_rgb=render_params.option_panel_fill_rgb,
                content_fill_rgb=render_params.option_shape_fill_rgb,
                border_color_rgb=render_params.border_color_rgb,
                text_color_rgb=render_params.text_color_rgb,
                text_stroke_rgb=render_params.text_stroke_rgb,
                panel_corner_radius_px=int(render_params.panel_corner_radius_px),
                content_corner_radius_px=int(render_params.content_corner_radius_px),
                border_width_px=int(render_params.border_width_px),
            )
            option_panel_bbox_map[str(option.option_id)] = list(
                rendered_panel.panel_bbox
            )
            _draw_option_shape(
                draw,
                option=option,
                content_bbox=rendered_panel.content_bbox,
                render_params=render_params,
            )
            entities.append(
                {
                    "id": str(option.option_id),
                    "type": "tangram_option",
                    "label": str(option.option_label),
                    "shape_id": str(option.shape_id),
                    "bbox_px": list(rendered_panel.panel_bbox),
                    "is_correct": bool(option.is_correct),
                }
            )

    return RenderedTangramScene(
        image=image,
        entities=tuple(entities),
        scene_bbox_px=[round(float(value), 3) for value in scene_bbox],
        assembly_panel_bbox_px=[
            round(float(value), 3) for value in assembly_panel_bbox
        ],
        assembly_bbox_px=list(assembly_bbox),
        piece_bbox_map=piece_bbox_map,
        option_panel_bbox_map=option_panel_bbox_map,
    )


__all__ = [
    "render_tangram_scene",
]
