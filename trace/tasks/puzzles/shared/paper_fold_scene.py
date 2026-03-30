"""Shared rendering helpers for simple paper-fold result puzzle scenes."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font
from .drawing import draw_arrow, draw_centered_text, draw_dashed_line, draw_rounded_rect
from .paper_fold_common import PuzzleFoldResultRenderParams
from .symbol_rendering import PUZZLE_OBJECT_COLOR_BY_TYPE, draw_puzzle_shape_icon


SUPPORTED_PUZZLE_FOLD_SCENE_VARIANTS: Tuple[str, ...] = (
    "fold_strip",
    "fold_card",
    "fold_outline",
)
FOLD_RESULT_SUPERSAMPLE_SCALE = 2


@dataclass(frozen=True)
class RenderedPuzzleFoldResultScene:
    """Rendered fold-result scene plus traced geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    option_choice_bbox_map: Dict[str, List[float]]
    reference_panel_bbox_px: List[float]
    reference_paper_bbox_px: List[float]


def _paper_bbox_within_panel(
    panel_bbox: Sequence[float],
    *,
    width_ratio: float,
    height_ratio: float,
) -> Tuple[float, float, float, float]:
    """Center one paper rectangle inside a panel."""

    left, top, right, bottom = [float(value) for value in panel_bbox]
    width = float(right - left)
    height = float(bottom - top)
    paper_width = float(width * float(width_ratio))
    paper_height = float(height * float(height_ratio))
    x1 = float(left + 0.5 * (width - paper_width))
    y1 = float(top + 0.5 * (height - paper_height))
    return (float(x1), float(y1), float(x1 + paper_width), float(y1 + paper_height))


def _round_bbox(bbox: Sequence[float]) -> List[float]:
    """Round one bbox to the standard trace precision."""

    return [round(float(value), 3) for value in bbox]


def _scale_bbox(bbox: Sequence[float], *, scale: float) -> List[float]:
    """Scale one bbox from the supersampled canvas back to final pixels."""

    return [round(float(value) / float(scale), 3) for value in bbox]


def _scale_bbox_map(
    bbox_map: Mapping[str, Sequence[float]],
    *,
    scale: float,
) -> Dict[str, List[float]]:
    """Scale a keyed bbox map back to final pixels."""

    return {str(key): _scale_bbox(list(value), scale=scale) for key, value in bbox_map.items()}


def _scale_entities(
    entities: Sequence[Mapping[str, Any]],
    *,
    scale: float,
) -> List[Dict[str, Any]]:
    """Scale traced entity bboxes back to final pixels."""

    scaled: List[Dict[str, Any]] = []
    for entity in entities:
        record = dict(entity)
        if "bbox_px" in record:
            record["bbox_px"] = _scale_bbox(record["bbox_px"], scale=scale)
        scaled.append(record)
    return scaled


def _scale_render_params(
    render_params: PuzzleFoldResultRenderParams,
    *,
    scale: int,
) -> PuzzleFoldResultRenderParams:
    """Scale pixel-valued render params for supersampled drawing."""

    return replace(
        render_params,
        canvas_width=int(render_params.canvas_width * scale),
        canvas_height=int(render_params.canvas_height * scale),
        scene_margin_left_px=int(render_params.scene_margin_left_px * scale),
        scene_margin_right_px=int(render_params.scene_margin_right_px * scale),
        scene_margin_top_px=int(render_params.scene_margin_top_px * scale),
        scene_margin_bottom_px=int(render_params.scene_margin_bottom_px * scale),
        reference_panel_height_px=int(render_params.reference_panel_height_px * scale),
        reference_panel_padding_px=int(render_params.reference_panel_padding_px * scale),
        reference_to_options_gap_px=int(render_params.reference_to_options_gap_px * scale),
        option_gap_px=int(render_params.option_gap_px * scale),
        option_row_gap_px=int(render_params.option_row_gap_px * scale),
        option_label_gap_px=int(render_params.option_label_gap_px * scale),
        paper_corner_radius_px=int(render_params.paper_corner_radius_px * scale),
        panel_corner_radius_px=int(render_params.panel_corner_radius_px * scale),
        border_width_px=max(1, int(render_params.border_width_px * scale)),
        option_label_font_size_px=int(render_params.option_label_font_size_px * scale),
    )


def _draw_paper(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    render_params: PuzzleFoldResultRenderParams,
    border_width_px: int,
    unit_scale: float,
) -> None:
    """Draw one paper rectangle with a soft drop shadow."""

    left, top, right, bottom = [float(value) for value in bbox]
    shadow_offset = float(4.0 * unit_scale)
    draw_rounded_rect(
        draw,
        (
            float(left + shadow_offset),
            float(top + shadow_offset),
            float(right + shadow_offset),
            float(bottom + shadow_offset),
        ),
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


def _cell_bbox(
    paper_bbox: Sequence[float],
    *,
    cols: int,
    rows: int,
    cell_x: int,
    cell_y: int,
    unit_scale: float,
) -> Tuple[float, float, float, float]:
    """Return the cell bbox for one logical paper-grid coordinate."""

    left, top, right, bottom = [float(value) for value in paper_bbox]
    inner_pad = float(10.0 * unit_scale)
    usable_width = float(right - left) - (2.0 * inner_pad)
    usable_height = float(bottom - top) - (2.0 * inner_pad)
    cell_width = float(usable_width / float(cols))
    cell_height = float(usable_height / float(rows))
    x1 = float(left + inner_pad + (float(cell_x) * cell_width))
    y1 = float(top + inner_pad + (float(cell_y) * cell_height))
    return (
        float(x1),
        float(y1),
        float(x1 + cell_width),
        float(y1 + cell_height),
    )


def _draw_marks(
    draw: ImageDraw.ImageDraw,
    *,
    paper_bbox: Sequence[float],
    mark_specs: Sequence[Mapping[str, Any]],
    cols: int,
    rows: int,
    entity_prefix: str,
    unit_scale: float,
) -> List[Dict[str, Any]]:
    """Draw fold marks and return their traced entity records."""

    entities: List[Dict[str, Any]] = []
    for mark_spec in mark_specs:
        mark_id = str(mark_spec["mark_id"])
        object_type = str(mark_spec["object_type"])
        cell_x = int(mark_spec["cell"][0])
        cell_y = int(mark_spec["cell"][1])
        cell_bbox = _cell_bbox(
            paper_bbox,
            cols=int(cols),
            rows=int(rows),
            cell_x=int(cell_x),
            cell_y=int(cell_y),
            unit_scale=float(unit_scale),
        )
        cell_width = float(cell_bbox[2] - cell_bbox[0])
        cell_height = float(cell_bbox[3] - cell_bbox[1])
        draw_puzzle_shape_icon(
            draw,
            bbox=cell_bbox,
            object_type=str(object_type),
            fill_rgb=PUZZLE_OBJECT_COLOR_BY_TYPE[str(object_type)],
            outline_rgb=(44, 52, 66),
            width=max(2, int(round(2.0 * unit_scale))),
            inset_px=float(min(12.0 * unit_scale, 0.22 * min(cell_width, cell_height))),
        )
        attrs = {
            "object_type": str(object_type),
            "cell": [int(cell_x), int(cell_y)],
        }
        if "source_side" in mark_spec:
            attrs["source_side"] = str(mark_spec["source_side"])
        entities.append(
            {
                "entity_id": f"{entity_prefix}_{mark_id}",
                "entity_type": "puzzle_fold_mark",
                "bbox_px": _round_bbox(cell_bbox),
                "attrs": attrs,
            }
        )
    return entities


def _draw_fold_indicator(
    draw: ImageDraw.ImageDraw,
    *,
    paper_bbox: Sequence[float],
    fold_axis: str,
    fold_direction: str,
    render_params: PuzzleFoldResultRenderParams,
    unit_scale: float,
) -> List[Dict[str, Any]]:
    """Draw the fold line plus two outside arrows that indicate the fold direction."""

    left, top, right, bottom = [float(value) for value in paper_bbox]
    center_x = float(0.5 * (left + right))
    center_y = float(0.5 * (top + bottom))
    dash_inset = float(10.0 * unit_scale)
    arrow_offset = float(18.0 * unit_scale)
    arrow_half_span = float(44.0 * unit_scale)
    arrow_pad = float(10.0 * unit_scale)
    arrow_margin = float(8.0 * unit_scale)
    entities: List[Dict[str, Any]] = []

    if str(fold_axis) == "vertical":
        draw_dashed_line(
            draw,
            start=(float(center_x), float(top + dash_inset)),
            end=(float(center_x), float(bottom - dash_inset)),
            fill=render_params.fold_line_rgb,
            width=max(2, int(round(2.0 * unit_scale))),
            dash_px=float(9.0 * unit_scale),
            gap_px=float(7.0 * unit_scale),
        )
        if str(fold_direction) == "left_to_right":
            arrow_start = (float(center_x - arrow_half_span), 0.0)
            arrow_end = (float(center_x + arrow_half_span), 0.0)
        else:
            arrow_start = (float(center_x + arrow_half_span), 0.0)
            arrow_end = (float(center_x - arrow_half_span), 0.0)
        arrow_rows = (
            float(top - arrow_offset),
            float(bottom + arrow_offset),
        )
        line_bbox = [
            round(float(center_x - (2.0 * unit_scale)), 3),
            round(float(top + dash_inset), 3),
            round(float(center_x + (2.0 * unit_scale)), 3),
            round(float(bottom - dash_inset), 3),
        ]
        arrow_segments = [
            ((float(arrow_start[0]), float(arrow_rows[0])), (float(arrow_end[0]), float(arrow_rows[0]))),
            ((float(arrow_start[0]), float(arrow_rows[1])), (float(arrow_end[0]), float(arrow_rows[1]))),
        ]
    else:
        draw_dashed_line(
            draw,
            start=(float(left + dash_inset), float(center_y)),
            end=(float(right - dash_inset), float(center_y)),
            fill=render_params.fold_line_rgb,
            width=max(2, int(round(2.0 * unit_scale))),
            dash_px=float(9.0 * unit_scale),
            gap_px=float(7.0 * unit_scale),
        )
        if str(fold_direction) == "top_to_bottom":
            arrow_start = (0.0, float(center_y - arrow_half_span))
            arrow_end = (0.0, float(center_y + arrow_half_span))
        else:
            arrow_start = (0.0, float(center_y + arrow_half_span))
            arrow_end = (0.0, float(center_y - arrow_half_span))
        arrow_columns = (
            float(left - arrow_offset),
            float(right + arrow_offset),
        )
        line_bbox = [
            round(float(left + dash_inset), 3),
            round(float(center_y - (2.0 * unit_scale)), 3),
            round(float(right - dash_inset), 3),
            round(float(center_y + (2.0 * unit_scale)), 3),
        ]
        arrow_segments = [
            ((float(arrow_columns[0]), float(arrow_start[1])), (float(arrow_columns[0]), float(arrow_end[1]))),
            ((float(arrow_columns[1]), float(arrow_start[1])), (float(arrow_columns[1]), float(arrow_end[1]))),
        ]

    entities.append(
        {
            "entity_id": "reference_fold_line",
            "entity_type": "puzzle_fold_line",
            "bbox_px": line_bbox,
            "attrs": {
                "fold_axis": str(fold_axis),
                "fold_direction": str(fold_direction),
            },
        }
    )
    for arrow_index, (arrow_start_xy, arrow_end_xy) in enumerate(arrow_segments, start=1):
        draw_arrow(
            draw,
            start=arrow_start_xy,
            end=arrow_end_xy,
            fill=render_params.arrow_rgb,
            width=max(3, int(round(3.0 * unit_scale))),
            head_length_px=float(12.0 * unit_scale),
            head_width_px=float(12.0 * unit_scale),
        )
        arrow_bbox = [
            round(float(min(arrow_start_xy[0], arrow_end_xy[0]) - arrow_pad), 3),
            round(float(min(arrow_start_xy[1], arrow_end_xy[1]) - arrow_margin), 3),
            round(float(max(arrow_start_xy[0], arrow_end_xy[0]) + arrow_pad), 3),
            round(float(max(arrow_start_xy[1], arrow_end_xy[1]) + arrow_margin), 3),
        ]
        entities.append(
            {
                "entity_id": f"reference_fold_arrow_{int(arrow_index)}",
                "entity_type": "puzzle_fold_arrow",
                "bbox_px": arrow_bbox,
                "attrs": {
                    "fold_axis": str(fold_axis),
                    "fold_direction": str(fold_direction),
                    "arrow_index": int(arrow_index),
                },
            }
        )
    return entities


def _scene_panel_style(
    scene_variant: str,
    *,
    render_params: PuzzleFoldResultRenderParams,
) -> Tuple[Tuple[int, int, int] | None, Tuple[int, int, int] | None]:
    """Resolve outer reference-panel fill and outline styling."""

    if str(scene_variant) == "fold_outline":
        return None, render_params.border_color_rgb
    if str(scene_variant) == "fold_strip":
        return render_params.instruction_fill_rgb, None
    return render_params.panel_fill_rgb, render_params.border_color_rgb


def _text_height_px(draw: ImageDraw.ImageDraw, *, text: str, font) -> float:
    """Measure one rendered label height."""

    bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=1)
    return float(bbox[3] - bbox[1])


def _render_fold_result_scene_base(
    background: Image.Image,
    *,
    scene_variant: str,
    fold_axis: str,
    fold_direction: str,
    grid_size: int,
    original_mark_specs: Sequence[Mapping[str, Any]],
    option_specs: Sequence[Mapping[str, Any]],
    result_grid_cols: int,
    result_grid_rows: int,
    render_params: PuzzleFoldResultRenderParams,
    unit_scale: float,
) -> RenderedPuzzleFoldResultScene:
    """Render one paper-fold result puzzle on the current working-resolution canvas."""

    canvas = background.copy().convert("RGB")
    draw = ImageDraw.Draw(canvas)
    option_label_font = load_font(int(render_params.option_label_font_size_px))
    border_width = max(1, int(render_params.border_width_px))
    option_label_height = _text_height_px(draw, text="A", font=option_label_font)

    scene_left = float(render_params.scene_margin_left_px)
    scene_top = float(render_params.scene_margin_top_px)
    scene_right = float(render_params.canvas_width - render_params.scene_margin_right_px)
    scene_bottom = float(render_params.canvas_height - render_params.scene_margin_bottom_px)

    reference_panel_bbox = [
        round(float(scene_left), 3),
        round(float(scene_top), 3),
        round(float(scene_right), 3),
        round(float(scene_top + int(render_params.reference_panel_height_px)), 3),
    ]
    reference_fill, reference_outline = _scene_panel_style(
        str(scene_variant),
        render_params=render_params,
    )
    if reference_fill is not None or reference_outline is not None:
        draw_rounded_rect(
            draw,
            tuple(float(value) for value in reference_panel_bbox),
            radius=int(render_params.panel_corner_radius_px),
            fill=reference_fill if reference_fill is not None else (255, 255, 255),
            outline=reference_outline if reference_outline is not None else (255, 255, 255),
            width=max(1, int(border_width if reference_outline is not None else 1)),
        )

    reference_paper_bbox = _paper_bbox_within_panel(
        reference_panel_bbox,
        width_ratio=0.22,
        height_ratio=0.74,
    )
    _draw_paper(
        draw,
        bbox=reference_paper_bbox,
        render_params=render_params,
        border_width_px=int(border_width),
        unit_scale=float(unit_scale),
    )

    entities: List[Dict[str, Any]] = [
        {
            "entity_id": "reference_panel",
            "entity_type": "puzzle_fold_reference_panel",
            "bbox_px": list(reference_panel_bbox),
            "attrs": {"scene_variant": str(scene_variant)},
        },
        {
            "entity_id": "reference_paper",
            "entity_type": "puzzle_fold_reference_paper",
            "bbox_px": _round_bbox(reference_paper_bbox),
            "attrs": {
                "grid_size": int(grid_size),
                "fold_axis": str(fold_axis),
                "fold_direction": str(fold_direction),
            },
        },
    ]
    entities.extend(
        _draw_marks(
            draw,
            paper_bbox=reference_paper_bbox,
            mark_specs=original_mark_specs,
            cols=int(grid_size),
            rows=int(grid_size),
            entity_prefix="reference_mark",
            unit_scale=float(unit_scale),
        )
    )
    entities.extend(
        _draw_fold_indicator(
            draw,
            paper_bbox=reference_paper_bbox,
            fold_axis=str(fold_axis),
            fold_direction=str(fold_direction),
            render_params=render_params,
            unit_scale=float(unit_scale),
        )
    )

    reference_width = float(reference_paper_bbox[2] - reference_paper_bbox[0])
    reference_height = float(reference_paper_bbox[3] - reference_paper_bbox[1])
    option_paper_width = float(reference_width * (float(result_grid_cols) / float(grid_size)))
    option_paper_height = float(reference_height * (float(result_grid_rows) / float(grid_size)))
    option_block_height = float(option_paper_height + float(render_params.option_label_gap_px) + option_label_height)
    option_count = len(option_specs)
    if str(fold_axis) == "vertical":
        option_columns = int(option_count)
    else:
        option_columns = min(3, int(option_count))
    option_rows = int(math.ceil(float(option_count) / float(option_columns)))
    options_total_width = float(
        (float(option_columns) * option_paper_width)
        + (float(max(0, option_columns - 1)) * float(render_params.option_gap_px))
    )
    options_total_height = float(
        (float(option_rows) * option_block_height)
        + (float(max(0, option_rows - 1)) * float(render_params.option_row_gap_px))
    )
    options_left = float(scene_left + 0.5 * ((scene_right - scene_left) - options_total_width))
    options_top = float(reference_panel_bbox[3] + int(render_params.reference_to_options_gap_px))
    options_bottom = float(options_top + options_total_height)
    if float(options_bottom) > float(scene_bottom + 1e-3):
        raise ValueError("fold-result options exceed the scene bounds")

    option_choice_bbox_map: Dict[str, List[float]] = {}
    for option_index, option_spec in enumerate(option_specs):
        option_row = int(option_index // option_columns)
        option_col = int(option_index % option_columns)
        paper_left = float(
            options_left + (option_col * (option_paper_width + float(render_params.option_gap_px)))
        )
        paper_top = float(
            options_top + (option_row * (option_block_height + float(render_params.option_row_gap_px)))
        )
        option_paper_bbox = (
            float(paper_left),
            float(paper_top),
            float(paper_left + option_paper_width),
            float(paper_top + option_paper_height),
        )
        option_choice_id = str(option_spec["option_choice_id"])
        option_choice_bbox_map[str(option_choice_id)] = _round_bbox(option_paper_bbox)
        _draw_paper(
            draw,
            bbox=option_paper_bbox,
            render_params=render_params,
            border_width_px=max(1, int(border_width - 1)),
            unit_scale=float(unit_scale),
        )
        label_center_y = float(
            option_paper_bbox[3]
            + float(render_params.option_label_gap_px)
            + (0.5 * option_label_height)
        )
        label_bbox = draw_centered_text(
            draw,
            text=str(option_spec["option_label"]),
            center=(float(0.5 * (option_paper_bbox[0] + option_paper_bbox[2])), float(label_center_y)),
            font=option_label_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=max(1, int(unit_scale)),
        )
        entities.append(
            {
                "entity_id": str(option_choice_id),
                "entity_type": "puzzle_fold_option_choice",
                "bbox_px": _round_bbox(option_paper_bbox),
                "attrs": {
                    "option_label": str(option_spec["option_label"]),
                    "is_correct": bool(option_spec["is_correct"]),
                },
            }
        )
        entities.append(
            {
                "entity_id": f"{str(option_choice_id)}_label",
                "entity_type": "puzzle_fold_option_label",
                "bbox_px": list(label_bbox),
                "attrs": {
                    "option_label": str(option_spec["option_label"]),
                    "is_correct_option": bool(option_spec["is_correct"]),
                },
            }
        )
        entities.append(
            {
                "entity_id": f"{str(option_choice_id)}_paper",
                "entity_type": "puzzle_fold_result_paper",
                "bbox_px": _round_bbox(option_paper_bbox),
                "attrs": {
                    "option_label": str(option_spec["option_label"]),
                    "is_correct_option": bool(option_spec["is_correct"]),
                    "grid_cols": int(result_grid_cols),
                    "grid_rows": int(result_grid_rows),
                },
            }
        )
        entities.extend(
            _draw_marks(
                draw,
                paper_bbox=option_paper_bbox,
                mark_specs=option_spec["mark_specs"],
                cols=int(result_grid_cols),
                rows=int(result_grid_rows),
                entity_prefix=f"{str(option_choice_id)}_mark",
                unit_scale=float(unit_scale),
            )
        )

    return RenderedPuzzleFoldResultScene(
        image=canvas,
        entities=entities,
        scene_bbox_px=[
            round(float(scene_left), 3),
            round(float(scene_top), 3),
            round(float(scene_right), 3),
            round(float(options_bottom), 3),
        ],
        option_choice_bbox_map=option_choice_bbox_map,
        reference_panel_bbox_px=list(reference_panel_bbox),
        reference_paper_bbox_px=_round_bbox(reference_paper_bbox),
    )


def render_puzzle_fold_result_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    fold_axis: str,
    fold_direction: str,
    grid_size: int,
    original_mark_specs: Sequence[Mapping[str, Any]],
    option_specs: Sequence[Mapping[str, Any]],
    result_grid_cols: int,
    result_grid_rows: int,
    render_params: PuzzleFoldResultRenderParams,
) -> RenderedPuzzleFoldResultScene:
    """Render one paper-fold result puzzle with labeled options."""

    scale = int(FOLD_RESULT_SUPERSAMPLE_SCALE)
    work_render_params = _scale_render_params(render_params, scale=scale)
    work_background = background.resize(
        (int(work_render_params.canvas_width), int(work_render_params.canvas_height)),
        resample=Image.Resampling.BICUBIC,
    )
    rendered = _render_fold_result_scene_base(
        work_background,
        scene_variant=str(scene_variant),
        fold_axis=str(fold_axis),
        fold_direction=str(fold_direction),
        grid_size=int(grid_size),
        original_mark_specs=original_mark_specs,
        option_specs=option_specs,
        result_grid_cols=int(result_grid_cols),
        result_grid_rows=int(result_grid_rows),
        render_params=work_render_params,
        unit_scale=float(scale),
    )
    final_image = rendered.image.resize(
        (int(render_params.canvas_width), int(render_params.canvas_height)),
        resample=Image.Resampling.LANCZOS,
    )
    return RenderedPuzzleFoldResultScene(
        image=final_image,
        entities=_scale_entities(rendered.entities, scale=float(scale)),
        scene_bbox_px=_scale_bbox(rendered.scene_bbox_px, scale=float(scale)),
        option_choice_bbox_map=_scale_bbox_map(rendered.option_choice_bbox_map, scale=float(scale)),
        reference_panel_bbox_px=_scale_bbox(rendered.reference_panel_bbox_px, scale=float(scale)),
        reference_paper_bbox_px=_scale_bbox(rendered.reference_paper_bbox_px, scale=float(scale)),
    )


__all__ = [
    "FOLD_RESULT_SUPERSAMPLE_SCALE",
    "RenderedPuzzleFoldResultScene",
    "SUPPORTED_PUZZLE_FOLD_SCENE_VARIANTS",
    "render_puzzle_fold_result_scene",
]
