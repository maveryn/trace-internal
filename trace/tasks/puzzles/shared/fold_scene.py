"""Shared rendering helpers for folded-paper hole-punch puzzle scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font
from .drawing import draw_arrow, draw_dashed_line, draw_rounded_rect
from .fold_hole_common import PuzzleFoldHoleRenderParams
from .option_panels import render_puzzle_option_panel


SUPPORTED_PUZZLE_FOLD_SCENE_VARIANTS: Tuple[str, ...] = (
    "fold_strip",
    "fold_card",
    "fold_outline",
)


@dataclass(frozen=True)
class RenderedPuzzleFoldHoleScene:
    """Rendered fold-hole scene plus traced geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    option_panel_bbox_map: Dict[str, List[float]]
    reference_panel_bbox_px: List[float]
    step_panel_bbox_map: Dict[str, List[float]]


def _paper_bbox_within_panel(
    panel_bbox: Sequence[float],
    *,
    width_ratio: float,
    height_ratio: float,
) -> Tuple[float, float, float, float]:
    """Center one paper rectangle inside a step or option content box."""

    left, top, right, bottom = [float(value) for value in panel_bbox]
    width = float(right - left)
    height = float(bottom - top)
    paper_width = float(width * float(width_ratio))
    paper_height = float(height * float(height_ratio))
    x1 = float(left + 0.5 * (width - paper_width))
    y1 = float(top + 0.5 * (height - paper_height))
    return (float(x1), float(y1), float(x1 + paper_width), float(y1 + paper_height))


def _draw_paper(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    render_params: PuzzleFoldHoleRenderParams,
    border_width_px: int,
) -> None:
    """Draw one sheet or folded packet with a subtle shadow."""

    left, top, right, bottom = [float(value) for value in bbox]
    shadow_offset = 4.0
    draw_rounded_rect(
        draw,
        (float(left + shadow_offset), float(top + shadow_offset), float(right + shadow_offset), float(bottom + shadow_offset)),
        radius=int(render_params.paper_corner_radius_px),
        fill=render_params.paper_shadow_rgb,
        outline=render_params.paper_shadow_rgb,
        width=1,
    )
    draw_rounded_rect(
        draw,
        (float(left), float(top), float(right), float(bottom)),
        radius=int(render_params.paper_corner_radius_px),
        fill=render_params.paper_fill_rgb,
        outline=render_params.border_color_rgb,
        width=max(1, int(border_width_px)),
    )


def _grid_cell_center(
    bbox: Sequence[float],
    *,
    cols: int,
    rows: int,
    cell_x: int,
    cell_y: int,
) -> Tuple[float, float]:
    """Return the center point for one logical paper cell."""

    left, top, right, bottom = [float(value) for value in bbox]
    inner_pad = 10.0
    usable_width = float(right - left) - (2.0 * inner_pad)
    usable_height = float(bottom - top) - (2.0 * inner_pad)
    cell_width = float(usable_width / float(cols))
    cell_height = float(usable_height / float(rows))
    center_x = float(left + inner_pad + ((float(cell_x) + 0.5) * cell_width))
    center_y = float(top + inner_pad + ((float(cell_y) + 0.5) * cell_height))
    return (float(center_x), float(center_y))


def _draw_holes(
    draw: ImageDraw.ImageDraw,
    *,
    paper_bbox: Sequence[float],
    cells: Sequence[Sequence[int]],
    cols: int,
    rows: int,
    render_params: PuzzleFoldHoleRenderParams,
) -> List[List[float]]:
    """Draw circular punched holes on one paper rectangle."""

    radius = max(5.0, min(float(paper_bbox[2] - paper_bbox[0]), float(paper_bbox[3] - paper_bbox[1])) * 0.045)
    bboxes: List[List[float]] = []
    for raw_x, raw_y in cells:
        center_x, center_y = _grid_cell_center(
            paper_bbox,
            cols=int(cols),
            rows=int(rows),
            cell_x=int(raw_x),
            cell_y=int(raw_y),
        )
        bbox = [
            round(float(center_x - radius), 3),
            round(float(center_y - radius), 3),
            round(float(center_x + radius), 3),
            round(float(center_y + radius), 3),
        ]
        draw.ellipse(
            bbox,
            fill=tuple(int(value) for value in render_params.hole_fill_rgb),
            outline=tuple(int(value) for value in render_params.border_color_rgb),
            width=1,
        )
        bboxes.append(list(bbox))
    return bboxes


def _draw_fold_step(
    draw: ImageDraw.ImageDraw,
    *,
    panel_bbox: Sequence[float],
    paper_bbox: Sequence[float],
    fold_axis: str,
    render_params: PuzzleFoldHoleRenderParams,
    border_width_px: int,
) -> None:
    """Draw one explicit fold instruction on a paper panel."""

    del border_width_px
    left, top, right, bottom = [float(value) for value in paper_bbox]
    center_x = float(0.5 * (left + right))
    center_y = float(0.5 * (top + bottom))
    if str(fold_axis) == "vertical":
        draw_dashed_line(
            draw,
            start=(float(center_x), float(top + 10.0)),
            end=(float(center_x), float(bottom - 10.0)),
            fill=render_params.fold_line_rgb,
            width=2,
            dash_px=9.0,
            gap_px=7.0,
        )
        draw_arrow(
            draw,
            start=(float(right - 18.0), float(center_y - 16.0)),
            end=(float(center_x + 12.0), float(center_y - 16.0)),
            fill=render_params.arrow_rgb,
            width=3,
            head_length_px=12.0,
            head_width_px=12.0,
        )
    else:
        draw_dashed_line(
            draw,
            start=(float(left + 10.0), float(center_y)),
            end=(float(right - 10.0), float(center_y)),
            fill=render_params.fold_line_rgb,
            width=2,
            dash_px=9.0,
            gap_px=7.0,
        )
        draw_arrow(
            draw,
            start=(float(center_x + 16.0), float(bottom - 18.0)),
            end=(float(center_x + 16.0), float(center_y + 12.0)),
            fill=render_params.arrow_rgb,
            width=3,
            head_length_px=12.0,
            head_width_px=12.0,
        )


def _step_paper_geometry(
    *,
    fold_mode: str,
    fold_axes: Sequence[str],
    step_index: int,
    panel_bbox: Sequence[float],
) -> Tuple[Tuple[float, float, float, float], int, int]:
    """Return paper bbox and local cell grid for one step panel."""

    if str(fold_mode) == "single":
        if int(step_index) == 0:
            return _paper_bbox_within_panel(panel_bbox, width_ratio=0.78, height_ratio=0.78), 6, 6
        axis = str(fold_axes[0])
        if axis == "vertical":
            return _paper_bbox_within_panel(panel_bbox, width_ratio=0.48, height_ratio=0.8), 3, 6
        return _paper_bbox_within_panel(panel_bbox, width_ratio=0.8, height_ratio=0.48), 6, 3
    if int(step_index) == 0:
        return _paper_bbox_within_panel(panel_bbox, width_ratio=0.78, height_ratio=0.78), 6, 6
    if int(step_index) == 1:
        return _paper_bbox_within_panel(panel_bbox, width_ratio=0.48, height_ratio=0.8), 3, 6
    return _paper_bbox_within_panel(panel_bbox, width_ratio=0.52, height_ratio=0.52), 3, 3


def _scene_panel_style(
    scene_variant: str,
    *,
    render_params: PuzzleFoldHoleRenderParams,
) -> Tuple[Tuple[int, int, int] | None, Tuple[int, int, int] | None]:
    """Resolve outer reference-panel fill/outline styling."""

    if str(scene_variant) == "fold_outline":
        return None, render_params.border_color_rgb
    if str(scene_variant) == "fold_strip":
        return render_params.instruction_fill_rgb, None
    return render_params.panel_fill_rgb, render_params.border_color_rgb


def render_puzzle_fold_hole_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    fold_mode: str,
    fold_axes: Sequence[str],
    folded_hole_cells: Sequence[Sequence[int]],
    option_specs: Sequence[Mapping[str, Any]],
    grid_size: int,
    render_params: PuzzleFoldHoleRenderParams,
) -> RenderedPuzzleFoldHoleScene:
    """Render one folded-paper hole-punch puzzle with labeled options."""

    canvas = background.copy().convert("RGB")
    draw = ImageDraw.Draw(canvas)
    option_label_font = load_font(int(render_params.option_label_font_size_px))
    border_width = max(1, int(render_params.border_width_px))

    scene_left = float(render_params.scene_margin_left_px)
    scene_top = float(render_params.scene_margin_top_px)
    scene_right = float(render_params.canvas_width - render_params.scene_margin_right_px)
    scene_bottom = float(render_params.canvas_height - render_params.scene_margin_bottom_px)

    option_count = len(option_specs)
    option_width = float((option_count * int(render_params.option_panel_width_px)) + ((option_count - 1) * int(render_params.option_gap_px)))
    options_left = float(scene_left + 0.5 * ((scene_right - scene_left) - option_width))
    options_top = float(scene_bottom - int(render_params.option_panel_height_px))
    options_bottom = float(scene_bottom)

    reference_panel_bbox = [
        round(float(scene_left), 3),
        round(float(scene_top), 3),
        round(float(scene_right), 3),
        round(float(options_top - int(render_params.reference_to_options_gap_px)), 3),
    ]
    reference_fill, reference_outline = _scene_panel_style(str(scene_variant), render_params=render_params)
    if reference_fill is not None or reference_outline is not None:
        draw_rounded_rect(
            draw,
            tuple(float(value) for value in reference_panel_bbox),
            radius=int(render_params.panel_corner_radius_px),
            fill=reference_fill if reference_fill is not None else (255, 255, 255),
            outline=reference_outline if reference_outline is not None else (255, 255, 255),
            width=max(1, int(border_width if reference_outline is not None else 1)),
        )

    step_panel_width = float(render_params.step_panel_width_px)
    step_panel_gap = float(render_params.step_panel_gap_px)
    step_count = 3
    total_step_width = float((step_count * step_panel_width) + ((step_count - 1) * step_panel_gap))
    step_top = float(reference_panel_bbox[1] + render_params.reference_panel_padding_px)
    step_left = float(reference_panel_bbox[0] + 0.5 * ((reference_panel_bbox[2] - reference_panel_bbox[0]) - total_step_width))

    entities: List[Dict[str, Any]] = []
    step_panel_bbox_map: Dict[str, List[float]] = {}
    option_panel_bbox_map: Dict[str, List[float]] = {}

    for step_index in range(step_count):
        panel_left = float(step_left + (step_index * (step_panel_width + step_panel_gap)))
        panel_bbox = (
            float(panel_left),
            float(step_top),
            float(panel_left + step_panel_width),
            float(step_top + float(render_params.step_panel_height_px)),
        )
        step_panel_id = f"step_panel_{int(step_index + 1)}"
        step_panel_bbox = [round(float(value), 3) for value in panel_bbox]
        step_panel_bbox_map[str(step_panel_id)] = list(step_panel_bbox)
        draw_rounded_rect(
            draw,
            panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=render_params.instruction_fill_rgb,
            outline=render_params.border_color_rgb,
            width=max(1, int(border_width)),
        )
        paper_bbox, paper_cols, paper_rows = _step_paper_geometry(
            fold_mode=str(fold_mode),
            fold_axes=fold_axes,
            step_index=int(step_index),
            panel_bbox=panel_bbox,
        )
        _draw_paper(draw, bbox=paper_bbox, render_params=render_params, border_width_px=int(border_width))

        if str(fold_mode) == "single":
            axis = str(fold_axes[0])
            if int(step_index) == 0:
                _draw_fold_step(
                    draw,
                    panel_bbox=panel_bbox,
                    paper_bbox=paper_bbox,
                    fold_axis=str(axis),
                    render_params=render_params,
                    border_width_px=int(border_width),
                )
            if int(step_index) == 2:
                hole_bboxes = _draw_holes(
                    draw,
                    paper_bbox=paper_bbox,
                    cells=folded_hole_cells,
                    cols=int(paper_cols),
                    rows=int(paper_rows),
                    render_params=render_params,
                )
                for hole_index, hole_bbox in enumerate(hole_bboxes, start=1):
                    entities.append(
                        {
                            "entity_id": f"{step_panel_id}_hole_{int(hole_index)}",
                            "entity_type": "puzzle_fold_hole",
                            "bbox_px": list(hole_bbox),
                            "attrs": {"step_index": int(step_index + 1), "paper_state": "folded_packet"},
                        }
                    )
        else:
            if int(step_index) == 0:
                _draw_fold_step(
                    draw,
                    panel_bbox=panel_bbox,
                    paper_bbox=paper_bbox,
                    fold_axis="vertical",
                    render_params=render_params,
                    border_width_px=int(border_width),
                )
            elif int(step_index) == 1:
                _draw_fold_step(
                    draw,
                    panel_bbox=panel_bbox,
                    paper_bbox=paper_bbox,
                    fold_axis="horizontal",
                    render_params=render_params,
                    border_width_px=int(border_width),
                )
            else:
                hole_bboxes = _draw_holes(
                    draw,
                    paper_bbox=paper_bbox,
                    cells=folded_hole_cells,
                    cols=int(paper_cols),
                    rows=int(paper_rows),
                    render_params=render_params,
                )
                for hole_index, hole_bbox in enumerate(hole_bboxes, start=1):
                    entities.append(
                        {
                            "entity_id": f"{step_panel_id}_hole_{int(hole_index)}",
                            "entity_type": "puzzle_fold_hole",
                            "bbox_px": list(hole_bbox),
                            "attrs": {"step_index": int(step_index + 1), "paper_state": "folded_packet"},
                        }
                    )

        entities.append(
            {
                "entity_id": str(step_panel_id),
                "entity_type": "puzzle_fold_step_panel",
                "bbox_px": list(step_panel_bbox),
                "attrs": {"step_index": int(step_index + 1)},
            }
        )
        if int(step_index) < int(step_count - 1):
            arrow_start_x = float(panel_bbox[2] + render_params.step_arrow_gap_px)
            arrow_end_x = float(panel_bbox[2] + step_panel_gap - render_params.step_arrow_gap_px)
            arrow_y = float(0.5 * (panel_bbox[1] + panel_bbox[3]))
            draw_arrow(
                draw,
                start=(float(arrow_start_x), float(arrow_y)),
                end=(float(arrow_end_x), float(arrow_y)),
                fill=render_params.arrow_rgb,
                width=3,
                head_length_px=12.0,
                head_width_px=12.0,
            )

    for option_index, option_spec in enumerate(option_specs):
        panel_left = float(options_left + (option_index * (int(render_params.option_panel_width_px) + int(render_params.option_gap_px))))
        panel_bbox = (
            float(panel_left),
            float(options_top),
            float(panel_left + int(render_params.option_panel_width_px)),
            float(options_bottom),
        )
        rendered_panel = render_puzzle_option_panel(
            draw,
            panel_bbox=panel_bbox,
            option_label=str(option_spec["option_label"]),
            label_font=option_label_font,
            label_center_y_px=float(options_top + 0.18 * int(render_params.option_panel_height_px)),
            content_box_size_px=float(render_params.option_content_box_size_px),
            content_gap_px=float(render_params.option_label_gap_px),
            panel_fill_rgb=render_params.option_panel_fill_rgb,
            content_fill_rgb=render_params.option_content_fill_rgb,
            border_color_rgb=render_params.border_color_rgb,
            text_color_rgb=render_params.text_color_rgb,
            text_stroke_rgb=render_params.text_stroke_rgb,
            panel_corner_radius_px=int(render_params.panel_corner_radius_px),
            content_corner_radius_px=int(render_params.paper_corner_radius_px),
            border_width_px=int(border_width),
        )
        option_panel_bbox_map[str(option_spec["option_panel_id"])] = list(rendered_panel.panel_bbox)
        option_paper_bbox = _paper_bbox_within_panel(
            rendered_panel.content_bbox,
            width_ratio=0.86,
            height_ratio=0.86,
        )
        _draw_paper(draw, bbox=option_paper_bbox, render_params=render_params, border_width_px=max(1, int(border_width - 1)))
        hole_bboxes = _draw_holes(
            draw,
            paper_bbox=option_paper_bbox,
            cells=option_spec["hole_cells"],
            cols=int(grid_size),
            rows=int(grid_size),
            render_params=render_params,
        )
        entities.append(
            {
                "entity_id": str(option_spec["option_panel_id"]),
                "entity_type": "puzzle_option_panel",
                "bbox_px": list(rendered_panel.panel_bbox),
                "attrs": {
                    "option_label": str(option_spec["option_label"]),
                    "is_correct": bool(option_spec["is_correct"]),
                },
            }
        )
        for hole_index, hole_bbox in enumerate(hole_bboxes, start=1):
            entities.append(
                {
                    "entity_id": f"{str(option_spec['option_panel_id'])}_hole_{int(hole_index)}",
                    "entity_type": "puzzle_fold_hole",
                    "bbox_px": list(hole_bbox),
                    "attrs": {
                        "option_label": str(option_spec["option_label"]),
                        "is_correct_option": bool(option_spec["is_correct"]),
                    },
                }
            )

    return RenderedPuzzleFoldHoleScene(
        image=canvas,
        entities=entities,
        scene_bbox_px=[
            round(float(scene_left), 3),
            round(float(scene_top), 3),
            round(float(scene_right), 3),
            round(float(scene_bottom), 3),
        ],
        option_panel_bbox_map=option_panel_bbox_map,
        reference_panel_bbox_px=list(reference_panel_bbox),
        step_panel_bbox_map=step_panel_bbox_map,
    )


__all__ = [
    "RenderedPuzzleFoldHoleScene",
    "SUPPORTED_PUZZLE_FOLD_SCENE_VARIANTS",
    "render_puzzle_fold_hole_scene",
]
