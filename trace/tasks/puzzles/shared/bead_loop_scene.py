"""Shared rendering helpers for topology bead-loop puzzle scenes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font
from .drawing import draw_centered_text, draw_rounded_rect
from .bead_loop_common import PuzzleBeadLoopRenderParams
from .symbol_rendering import draw_puzzle_shape_icon


SUPPORTED_PUZZLE_BEAD_LOOP_SCENE_VARIANTS: Tuple[str, ...] = (
    "loop_strip",
    "loop_card",
    "loop_outline",
)


@dataclass(frozen=True)
class RenderedPuzzleBeadLoopScene:
    """Rendered topology bead-loop scene plus traced geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    reference_loop_bbox_px: List[float]
    option_choice_bbox_map: Dict[str, List[float]]


def _scene_panel_style(
    scene_variant: str,
    *,
    render_params: PuzzleBeadLoopRenderParams,
) -> Tuple[Tuple[int, int, int] | None, Tuple[int, int, int] | None]:
    """Resolve outer reference-panel styling."""

    if str(scene_variant) == "loop_outline":
        return None, render_params.border_color_rgb
    if str(scene_variant) == "loop_strip":
        return render_params.instruction_fill_rgb, None
    return render_params.panel_fill_rgb, render_params.border_color_rgb


def _round_bbox(bbox: Sequence[float]) -> List[float]:
    """Round one bbox to standard trace precision."""

    return [round(float(value), 3) for value in bbox]


def _loop_bbox_within_image(
    image_bbox: Sequence[float],
    *,
    loop_shape_variant: str,
) -> Tuple[float, float, float, float]:
    """Return one ellipse bbox within an image slot."""

    left, top, right, bottom = [float(value) for value in image_bbox]
    width = float(right - left)
    height = float(bottom - top)
    if str(loop_shape_variant) == "wide":
        width_ratio, height_ratio = 0.76, 0.56
    elif str(loop_shape_variant) == "tall":
        width_ratio, height_ratio = 0.58, 0.78
    else:
        width_ratio, height_ratio = 0.68, 0.68
    loop_width = float(width * width_ratio)
    loop_height = float(height * height_ratio)
    x1 = float(left + 0.5 * (width - loop_width))
    y1 = float(top + 0.5 * (height - loop_height))
    return (
        float(x1),
        float(y1),
        float(x1 + loop_width),
        float(y1 + loop_height),
    )


def _bead_center_points(
    loop_bbox: Sequence[float],
    *,
    bead_count: int,
    start_angle_deg: int,
) -> List[Tuple[float, float]]:
    """Return bead centers in clockwise order around the loop."""

    left, top, right, bottom = [float(value) for value in loop_bbox]
    cx = float(0.5 * (left + right))
    cy = float(0.5 * (top + bottom))
    rx = float(0.5 * (right - left))
    ry = float(0.5 * (bottom - top))
    points: List[Tuple[float, float]] = []
    for index in range(int(bead_count)):
        angle = math.radians(float(start_angle_deg) - (360.0 * float(index) / float(bead_count)))
        points.append((float(cx + rx * math.cos(angle)), float(cy + ry * math.sin(angle))))
    return points


def _draw_bead(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    bead_size_px: float,
    bead_spec: Mapping[str, Any],
    render_params: PuzzleBeadLoopRenderParams,
) -> List[float]:
    """Draw one bead token and return its bbox."""

    cx, cy = float(center[0]), float(center[1])
    half = float(0.5 * bead_size_px)
    bead_bbox = (
        float(cx - half),
        float(cy - half),
        float(cx + half),
        float(cy + half),
    )
    render_mode = str(bead_spec["render_mode"])
    fill_rgb = tuple(int(value) for value in bead_spec.get("fill_rgb") or render_params.shape_fill_rgb)
    outline_rgb = tuple(int(value) for value in render_params.border_color_rgb)
    if render_mode == "color":
        draw.ellipse(
            bead_bbox,
            fill=fill_rgb,
            outline=outline_rgb,
            width=max(2, int(render_params.border_width_px)),
        )
    else:
        draw_puzzle_shape_icon(
            draw,
            bbox=bead_bbox,
            object_type=str(bead_spec["object_type"]),
            fill_rgb=fill_rgb,
            outline_rgb=outline_rgb,
            width=max(2, int(render_params.border_width_px)),
            inset_px=float(min(8.0, 0.20 * bead_size_px)),
        )
    return _round_bbox(bead_bbox)


def _draw_loop_image(
    draw: ImageDraw.ImageDraw,
    *,
    image_bbox: Sequence[float],
    loop_id: str,
    loop_shape_variant: str,
    start_angle_deg: int,
    bead_specs: Sequence[Mapping[str, Any]],
    render_params: PuzzleBeadLoopRenderParams,
    loop_entity_type: str,
    bead_entity_type: str,
) -> List[Dict[str, Any]]:
    """Draw one bead loop and return traced entities."""

    loop_bbox = _loop_bbox_within_image(image_bbox, loop_shape_variant=str(loop_shape_variant))
    draw.ellipse(
        loop_bbox,
        outline=render_params.loop_color_rgb,
        width=max(2, int(render_params.loop_stroke_width_px)),
    )
    entities: List[Dict[str, Any]] = [
        {
            "entity_id": str(loop_id),
            "entity_type": str(loop_entity_type),
            "bbox_px": _round_bbox(loop_bbox),
            "attrs": {
                "loop_shape_variant": str(loop_shape_variant),
                "start_angle_deg": int(start_angle_deg),
                "bead_count": int(len(bead_specs)),
            },
        }
    ]
    centers = _bead_center_points(loop_bbox, bead_count=int(len(bead_specs)), start_angle_deg=int(start_angle_deg))
    for bead_index, (center, bead_spec) in enumerate(zip(centers, bead_specs), start=1):
        bead_bbox = _draw_bead(
            draw,
            center=center,
            bead_size_px=float(render_params.bead_size_px),
            bead_spec=bead_spec,
            render_params=render_params,
        )
        entities.append(
            {
                "entity_id": f"{str(loop_id)}_bead_{int(bead_index)}",
                "entity_type": str(bead_entity_type),
                "bbox_px": list(bead_bbox),
                "attrs": {
                    "token_label": str(bead_spec["token_label"]),
                    "object_type": str(bead_spec["object_type"]),
                    "render_mode": str(bead_spec["render_mode"]),
                },
            }
        )
    return entities


def render_puzzle_bead_loop_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    reference_bead_specs: Sequence[Mapping[str, Any]],
    reference_loop_shape_variant: str,
    reference_start_angle_deg: int,
    option_specs: Sequence[Mapping[str, Any]],
    render_params: PuzzleBeadLoopRenderParams,
) -> RenderedPuzzleBeadLoopScene:
    """Render one topology bead-loop equivalence-count scene."""

    selected_variant = str(scene_variant)
    if selected_variant not in set(SUPPORTED_PUZZLE_BEAD_LOOP_SCENE_VARIANTS):
        raise ValueError(f"unsupported topology bead-loop scene_variant: {scene_variant}")

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    reference_font = load_font(int(render_params.reference_label_font_size_px), bold=True)
    option_font = load_font(int(render_params.option_label_font_size_px), bold=True)
    label_bbox_sample = draw.textbbox((0.0, 0.0), "A", font=option_font, stroke_width=1)
    option_label_height = float(label_bbox_sample[3] - label_bbox_sample[1])

    scene_left = float(render_params.scene_margin_left_px)
    scene_top = float(render_params.scene_margin_top_px)
    scene_right = float(render_params.canvas_width - render_params.scene_margin_right_px)
    scene_bottom = float(render_params.canvas_height - render_params.scene_margin_bottom_px)

    reference_panel_bbox = (
        float(scene_left),
        float(scene_top),
        float(scene_right),
        float(scene_top + render_params.reference_panel_height_px),
    )
    reference_fill, reference_outline = _scene_panel_style(selected_variant, render_params=render_params)
    if reference_fill is not None or reference_outline is not None:
        draw_rounded_rect(
            draw,
            reference_panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=reference_fill if reference_fill is not None else (255, 255, 255),
            outline=reference_outline if reference_outline is not None else (255, 255, 255),
            width=max(1, int(render_params.border_width_px if reference_outline is not None else 1)),
        )

    reference_label_bbox = draw_centered_text(
        draw,
        text="Reference",
        center=(float(0.5 * (scene_left + scene_right)), float(scene_top + 30.0)),
        font=reference_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=1,
    )
    reference_image_bbox = (
        float(scene_left + 0.5 * ((scene_right - scene_left) - render_params.reference_loop_width_px)),
        float(scene_top + render_params.reference_panel_padding_px + 30.0),
        float(scene_left + 0.5 * ((scene_right - scene_left) - render_params.reference_loop_width_px) + render_params.reference_loop_width_px),
        float(scene_top + render_params.reference_panel_padding_px + 30.0 + render_params.reference_loop_height_px),
    )

    entities: List[Dict[str, Any]] = [
        {
            "entity_id": "reference_panel",
            "entity_type": "puzzle_topology_reference_panel",
            "bbox_px": _round_bbox(reference_panel_bbox),
            "attrs": {"scene_variant": selected_variant},
        },
        {
            "entity_id": "reference_label",
            "entity_type": "puzzle_topology_reference_label",
            "bbox_px": list(reference_label_bbox),
            "attrs": {"text": "Reference"},
        },
    ]
    reference_loop_entities = _draw_loop_image(
        draw,
        image_bbox=reference_image_bbox,
        loop_id="reference_loop",
        loop_shape_variant=str(reference_loop_shape_variant),
        start_angle_deg=int(reference_start_angle_deg),
        bead_specs=reference_bead_specs,
        render_params=render_params,
        loop_entity_type="puzzle_topology_reference_loop",
        bead_entity_type="puzzle_topology_reference_bead",
    )
    entities.extend(reference_loop_entities)
    reference_loop_bbox = list(reference_loop_entities[0]["bbox_px"])

    option_count = int(len(option_specs))
    option_columns = 3 if option_count <= 6 else 4
    option_rows = int(math.ceil(float(option_count) / float(option_columns)))
    option_block_height = float(render_params.option_image_height_px + render_params.option_label_gap_px + option_label_height)
    options_total_width = float(
        (option_columns * render_params.option_image_width_px)
        + (max(0, option_columns - 1) * render_params.option_gap_px)
    )
    options_total_height = float(
        (option_rows * option_block_height)
        + (max(0, option_rows - 1) * render_params.option_row_gap_px)
    )
    options_left = float(scene_left + 0.5 * ((scene_right - scene_left) - options_total_width))
    options_top = float(reference_panel_bbox[3] + render_params.reference_to_options_gap_px)
    option_choice_bbox_map: Dict[str, List[float]] = {}

    for option_index, option_spec in enumerate(option_specs):
        row_index = int(option_index // option_columns)
        col_index = int(option_index % option_columns)
        image_left = float(options_left + col_index * (render_params.option_image_width_px + render_params.option_gap_px))
        image_top = float(options_top + row_index * (option_block_height + render_params.option_row_gap_px))
        image_bbox = (
            float(image_left),
            float(image_top),
            float(image_left + render_params.option_image_width_px),
            float(image_top + render_params.option_image_height_px),
        )
        option_choice_id = str(option_spec["option_choice_id"])
        option_choice_bbox_map[option_choice_id] = _round_bbox(image_bbox)
        entities.append(
            {
                "entity_id": str(option_choice_id),
                "entity_type": "puzzle_topology_option_choice",
                "bbox_px": _round_bbox(image_bbox),
                "attrs": {
                    "option_label": str(option_spec["option_label"]),
                    "is_valid": bool(option_spec["is_valid"]),
                },
            }
        )
        entities.extend(
            _draw_loop_image(
                draw,
                image_bbox=image_bbox,
                loop_id=f"{option_choice_id}_loop",
                loop_shape_variant=str(option_spec["loop_shape_variant"]),
                start_angle_deg=int(option_spec["start_angle_deg"]),
                bead_specs=list(option_spec["bead_specs"]),
                render_params=render_params,
                loop_entity_type="puzzle_topology_option_loop",
                bead_entity_type="puzzle_topology_option_bead",
            )
        )
        label_center = (
            float(0.5 * (image_bbox[0] + image_bbox[2])),
            float(image_bbox[3] + render_params.option_label_gap_px + 0.5 * option_label_height),
        )
        label_bbox = draw_centered_text(
            draw,
            text=str(option_spec["option_label"]),
            center=label_center,
            font=option_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )
        entities.append(
            {
                "entity_id": f"{option_choice_id}_label",
                "entity_type": "puzzle_topology_option_label",
                "bbox_px": list(label_bbox),
                "attrs": {"option_label": str(option_spec["option_label"])},
            }
        )

    scene_bbox = [
        round(float(scene_left), 3),
        round(float(scene_top), 3),
        round(float(scene_right), 3),
        round(float(max(scene_bottom, options_top + options_total_height)), 3),
    ]

    return RenderedPuzzleBeadLoopScene(
        image=image,
        entities=entities,
        scene_bbox_px=list(scene_bbox),
        reference_loop_bbox_px=list(reference_loop_bbox),
        option_choice_bbox_map=option_choice_bbox_map,
    )


__all__ = [
    "RenderedPuzzleBeadLoopScene",
    "SUPPORTED_PUZZLE_BEAD_LOOP_SCENE_VARIANTS",
    "render_puzzle_bead_loop_scene",
]
