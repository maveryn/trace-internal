"""Shared rendering helpers for spatial cube-view puzzle scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font
from .drawing import draw_centered_text, draw_rounded_rect
from .option_panels import render_puzzle_option_panel
from .symbol_rendering import PUZZLE_OBJECT_COLOR_BY_TYPE, draw_puzzle_shape_icon


SUPPORTED_PUZZLE_CUBE_SCENE_VARIANTS: Tuple[str, ...] = (
    "cube_strip",
    "cube_card",
    "cube_outline",
)


@dataclass(frozen=True)
class PuzzleCubeRenderParams:
    """Resolved render parameters for one cube-view puzzle scene."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    reference_cube_box_size_px: int
    reference_panel_padding_px: int
    reference_to_pairs_gap_px: int
    pair_group_gap_px: int
    pair_box_size_px: int
    pair_token_gap_px: int
    pairs_to_options_gap_px: int
    option_panel_width_px: int
    option_panel_height_px: int
    option_gap_px: int
    option_cube_box_size_px: int
    option_label_gap_px: int
    slot_corner_radius_px: int
    border_width_px: int
    panel_corner_radius_px: int
    option_label_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    option_panel_fill_rgb: Tuple[int, int, int]
    option_cube_fill_rgb: Tuple[int, int, int]
    border_color_rgb: Tuple[int, int, int]
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    accent_color_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class RenderedPuzzleCubeScene:
    """Rendered cube-view puzzle image plus traced reference/option geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    option_panel_bbox_map: Dict[str, List[float]]
    option_cube_bbox_map: Dict[str, List[float]]
    reference_cube_bbox_px: List[float]
    pair_box_bbox_map: Dict[str, List[float]]


def _mix_with_white(rgb: Sequence[int], alpha: float) -> Tuple[int, int, int]:
    """Return one lightened face color while keeping symbol identity visible."""

    return tuple(
        int(round((1.0 - float(alpha)) * 255.0 + float(alpha) * float(channel)))
        for channel in rgb
    )


def _polygon_bbox(points: Sequence[Tuple[float, float]]) -> List[float]:
    """Return the axis-aligned bbox for one polygon."""

    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return [
        round(float(min(xs)), 3),
        round(float(min(ys)), 3),
        round(float(max(xs)), 3),
        round(float(max(ys)), 3),
    ]


def _centroid(points: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    """Return a simple centroid approximation for one face polygon."""

    return (
        float(sum(float(point[0]) for point in points) / float(len(points))),
        float(sum(float(point[1]) for point in points) / float(len(points))),
    )


def _cube_face_polygons(cube_bbox: Sequence[float]) -> Tuple[float, Dict[str, List[Tuple[float, float]]]]:
    """Build deterministic top/front/right face polygons inside one cube box."""

    left, top, right, bottom = [float(value) for value in cube_bbox]
    width = float(right - left)
    height = float(bottom - top)
    side = float(min(width / 1.55, height / 1.62))
    dx = float(0.48 * side)
    dy = float(0.28 * side)
    cube_width = float(2.0 * dx)
    cube_height = float(side + (2.0 * dy))
    cx = float(left + 0.5 * width)
    y0 = float(top + 0.5 * (height - cube_height))
    top_face = [
        (float(cx), float(y0)),
        (float(cx + dx), float(y0 + dy)),
        (float(cx), float(y0 + (2.0 * dy))),
        (float(cx - dx), float(y0 + dy)),
    ]
    front_face = [
        (float(cx - dx), float(y0 + dy)),
        (float(cx), float(y0 + (2.0 * dy))),
        (float(cx), float(y0 + (2.0 * dy) + side)),
        (float(cx - dx), float(y0 + dy + side)),
    ]
    right_face = [
        (float(cx), float(y0 + (2.0 * dy))),
        (float(cx + dx), float(y0 + dy)),
        (float(cx + dx), float(y0 + dy + side)),
        (float(cx), float(y0 + (2.0 * dy) + side)),
    ]
    return float(side), {"top": top_face, "front": front_face, "right": right_face}


def _draw_cube_view(
    draw: ImageDraw.ImageDraw,
    *,
    cube_bbox: Sequence[float],
    view_spec: Mapping[str, Any],
    border_color_rgb: Sequence[int],
    border_width_px: int,
) -> Dict[str, List[float]]:
    """Draw one cube view and return per-face bboxes."""

    side, polygons = _cube_face_polygons(cube_bbox)
    face_role_to_object = {
        "top": str(view_spec["top_object_type"]),
        "front": str(view_spec["front_object_type"]),
        "right": str(view_spec["right_object_type"]),
    }
    face_bbox_map: Dict[str, List[float]] = {}
    face_alpha = {"top": 0.45, "front": 0.62, "right": 0.55}
    icon_scale = {"top": 0.28, "front": 0.34, "right": 0.34}
    for face_role in ("top", "front", "right"):
        object_type = str(face_role_to_object[face_role])
        base_rgb = PUZZLE_OBJECT_COLOR_BY_TYPE.get(object_type, (180, 180, 180))
        face_fill_rgb = _mix_with_white(base_rgb, float(face_alpha[face_role]))
        points = polygons[face_role]
        draw.polygon(
            points,
            fill=face_fill_rgb,
            outline=tuple(int(value) for value in border_color_rgb),
            width=max(2, int(border_width_px)),
        )
        center_x, center_y = _centroid(points)
        icon_size = float(icon_scale[face_role]) * float(side)
        icon_bbox = (
            float(center_x - 0.5 * icon_size),
            float(center_y - 0.5 * icon_size),
            float(center_x + 0.5 * icon_size),
            float(center_y + 0.5 * icon_size),
        )
        draw_puzzle_shape_icon(
            draw,
            bbox=icon_bbox,
            object_type=object_type,
            fill_rgb=(255, 255, 255),
            outline_rgb=border_color_rgb,
            width=max(2, int(border_width_px)),
            inset_px=max(3.0, 0.12 * float(icon_size)),
        )
        face_bbox_map[face_role] = _polygon_bbox(points)
    return face_bbox_map


def render_puzzle_cube_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    reference_view: Mapping[str, Any],
    opposite_pair_specs: Sequence[Mapping[str, Any]],
    option_specs: Sequence[Mapping[str, Any]],
    render_params: PuzzleCubeRenderParams,
) -> RenderedPuzzleCubeScene:
    """Render one reference cube plus labeled option cubes."""

    selected_variant = str(scene_variant)
    if selected_variant not in set(SUPPORTED_PUZZLE_CUBE_SCENE_VARIANTS):
        raise ValueError(f"unsupported puzzle cube scene_variant: {selected_variant}")
    options = [dict(option) for option in option_specs]
    if len(options) < 2:
        raise ValueError("cube-view scenes require at least two option panels")

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    option_label_font = load_font(int(render_params.option_label_font_size_px), bold=True)
    pair_token_font = load_font(max(18, int(0.32 * float(render_params.pair_box_size_px))), bold=True)

    reference_cube_box_size = float(render_params.reference_cube_box_size_px)
    pair_box_size = float(render_params.pair_box_size_px)
    option_panel_width = float(render_params.option_panel_width_px)
    option_panel_height = float(render_params.option_panel_height_px)
    option_gap = float(render_params.option_gap_px)
    options_width = float((len(options) * option_panel_width) + max(0, len(options) - 1) * option_gap)
    pair_token_bbox = draw.textbbox((0, 0), "<->", font=pair_token_font, stroke_width=1)
    pair_token_width = float(pair_token_bbox[2] - pair_token_bbox[0])
    pair_group_width = float((2.0 * pair_box_size) + (2.0 * float(render_params.pair_token_gap_px)) + pair_token_width)
    pair_row_width = float(
        (len(opposite_pair_specs) * pair_group_width)
        + max(0, len(opposite_pair_specs) - 1) * float(render_params.pair_group_gap_px)
    )
    reference_section_height = float(
        reference_cube_box_size
        + float(render_params.reference_to_pairs_gap_px)
        + pair_box_size
    )
    content_width = float(max(reference_cube_box_size, pair_row_width, options_width))
    content_height = float(reference_section_height + float(render_params.pairs_to_options_gap_px) + option_panel_height)

    usable_width = float(
        render_params.canvas_width - render_params.scene_margin_left_px - render_params.scene_margin_right_px
    )
    usable_height = float(
        render_params.canvas_height - render_params.scene_margin_top_px - render_params.scene_margin_bottom_px
    )
    content_left = float(
        render_params.scene_margin_left_px + max(0.0, 0.5 * (usable_width - content_width))
    )
    content_top = float(
        render_params.scene_margin_top_px + max(0.0, 0.5 * (usable_height - content_height))
    )

    reference_cube_left = float(content_left + 0.5 * (content_width - reference_cube_box_size))
    reference_cube_top = float(content_top)
    pairs_left = float(content_left + 0.5 * (content_width - pair_row_width))
    pairs_top = float(reference_cube_top + reference_cube_box_size + float(render_params.reference_to_pairs_gap_px))
    options_left = float(content_left + 0.5 * (content_width - options_width))
    options_top = float(content_top + reference_section_height + float(render_params.pairs_to_options_gap_px))

    reference_cube_bbox = [
        round(float(reference_cube_left), 3),
        round(float(reference_cube_top), 3),
        round(float(reference_cube_left + reference_cube_box_size), 3),
        round(float(reference_cube_top + reference_cube_box_size), 3),
    ]
    reference_panel_bbox = (
        float(reference_cube_left - float(render_params.reference_panel_padding_px)),
        float(reference_cube_top - float(render_params.reference_panel_padding_px)),
        float(reference_cube_left + reference_cube_box_size + float(render_params.reference_panel_padding_px)),
        float(pairs_top + pair_box_size + float(render_params.reference_panel_padding_px)),
    )
    options_panel_bbox = (
        float(options_left - float(render_params.reference_panel_padding_px)),
        float(options_top - float(render_params.reference_panel_padding_px)),
        float(options_left + options_width + float(render_params.reference_panel_padding_px)),
        float(options_top + option_panel_height + float(render_params.reference_panel_padding_px)),
    )

    entities: List[Dict[str, Any]] = []
    option_panel_bbox_map: Dict[str, List[float]] = {}
    option_cube_bbox_map: Dict[str, List[float]] = {}
    pair_box_bbox_map: Dict[str, List[float]] = {}
    if selected_variant in {"cube_card", "cube_outline"}:
        fill_rgb = render_params.panel_fill_rgb if selected_variant == "cube_card" else (248, 248, 248)
        draw_rounded_rect(
            draw,
            reference_panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=fill_rgb,
            outline=render_params.border_color_rgb,
            width=int(render_params.border_width_px),
        )
        draw_rounded_rect(
            draw,
            options_panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=fill_rgb,
            outline=render_params.border_color_rgb,
            width=int(render_params.border_width_px),
        )
        entities.append(
            {
                "entity_id": "puzzle_cube_reference_panel",
                "entity_type": "puzzle_cube_panel",
                "bbox_px": [round(float(value), 3) for value in reference_panel_bbox],
                "attrs": {"panel_role": "reference", "scene_variant": selected_variant},
            }
        )
        entities.append(
            {
                "entity_id": "puzzle_cube_options_panel",
                "entity_type": "puzzle_cube_panel",
                "bbox_px": [round(float(value), 3) for value in options_panel_bbox],
                "attrs": {"panel_role": "options", "scene_variant": selected_variant},
            }
        )

    reference_face_bboxes = _draw_cube_view(
        draw,
        cube_bbox=reference_cube_bbox,
        view_spec=reference_view,
        border_color_rgb=render_params.border_color_rgb,
        border_width_px=int(render_params.border_width_px),
    )
    entities.append(
        {
            "entity_id": "reference_cube",
            "entity_type": "puzzle_cube_reference",
            "bbox_px": list(reference_cube_bbox),
            "attrs": {
                "top_object_type": str(reference_view["top_object_type"]),
                "front_object_type": str(reference_view["front_object_type"]),
                "right_object_type": str(reference_view["right_object_type"]),
            },
        }
    )
    for face_role, face_bbox in reference_face_bboxes.items():
        entities.append(
            {
                "entity_id": f"reference_cube_{face_role}_face",
                "entity_type": "puzzle_cube_face",
                "bbox_px": list(face_bbox),
                "attrs": {
                    "cube_role": "reference",
                    "face_role": str(face_role),
                    "object_type": str(reference_view[f"{face_role}_object_type"]),
                },
            }
        )

    for pair_index, pair_spec in enumerate(opposite_pair_specs):
        group_left = float(pairs_left + pair_index * (pair_group_width + float(render_params.pair_group_gap_px)))
        left_box_bbox = (
            float(group_left),
            float(pairs_top),
            float(group_left + pair_box_size),
            float(pairs_top + pair_box_size),
        )
        token_center_x = float(group_left + pair_box_size + float(render_params.pair_token_gap_px) + 0.5 * pair_token_width)
        token_center_y = float(pairs_top + 0.5 * pair_box_size)
        right_box_left = float(group_left + pair_box_size + (2.0 * float(render_params.pair_token_gap_px)) + pair_token_width)
        right_box_bbox = (
            float(right_box_left),
            float(pairs_top),
            float(right_box_left + pair_box_size),
            float(pairs_top + pair_box_size),
        )
        for box_role, box_bbox, object_type in (
            ("left", left_box_bbox, str(pair_spec["left_object_type"])),
            ("right", right_box_bbox, str(pair_spec["right_object_type"])),
        ):
            draw_rounded_rect(
                draw,
                box_bbox,
                radius=int(max(10, render_params.slot_corner_radius_px - 4)),
                fill=render_params.option_cube_fill_rgb,
                outline=render_params.border_color_rgb,
                width=int(render_params.border_width_px),
            )
            draw_puzzle_shape_icon(
                draw,
                bbox=box_bbox,
                object_type=object_type,
                fill_rgb=PUZZLE_OBJECT_COLOR_BY_TYPE.get(object_type, render_params.accent_color_rgb),
                outline_rgb=render_params.border_color_rgb,
                width=max(2, int(render_params.border_width_px)),
            )
            box_id = str(pair_spec[f"{box_role}_box_id"])
            box_bbox_list = [round(float(value), 3) for value in box_bbox]
            pair_box_bbox_map[box_id] = list(box_bbox_list)
            entities.append(
                {
                    "entity_id": box_id,
                    "entity_type": "puzzle_cube_pair_box",
                    "bbox_px": list(box_bbox_list),
                    "attrs": {
                        "pair_index": int(pair_index),
                        "pair_role": str(box_role),
                        "object_type": str(object_type),
                        "anchor_face": str(pair_spec["anchor_face"]),
                        "opposite_face": str(pair_spec["opposite_face"]),
                    },
                }
            )
        token_bbox = draw_centered_text(
            draw,
            text="<->",
            center=(float(token_center_x), float(token_center_y)),
            font=pair_token_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )
        entities.append(
            {
                "entity_id": f"pair_{pair_index}_token",
                "entity_type": "puzzle_cube_pair_token",
                "bbox_px": list(token_bbox),
                "attrs": {
                    "pair_index": int(pair_index),
                    "token": "<->",
                },
            }
        )

    for option_index, option in enumerate(options):
        panel_left = float(options_left + option_index * (option_panel_width + option_gap))
        panel_top = float(options_top)
        panel_bbox = (
            float(panel_left),
            float(panel_top),
            float(panel_left + option_panel_width),
            float(panel_top + option_panel_height),
        )
        option_panel = render_puzzle_option_panel(
            draw,
            panel_bbox=panel_bbox,
            option_label=str(option["option_label"]),
            label_font=option_label_font,
            label_center_y_px=float(panel_top + 28.0),
            content_box_size_px=float(render_params.option_cube_box_size_px),
            content_gap_px=float(render_params.option_label_gap_px),
            panel_fill_rgb=render_params.option_panel_fill_rgb,
            content_fill_rgb=render_params.option_cube_fill_rgb,
            border_color_rgb=render_params.border_color_rgb,
            text_color_rgb=render_params.text_color_rgb,
            text_stroke_rgb=render_params.text_stroke_rgb,
            panel_corner_radius_px=int(render_params.slot_corner_radius_px),
            content_corner_radius_px=int(max(8, render_params.slot_corner_radius_px - 4)),
            border_width_px=int(render_params.border_width_px),
        )
        option_panel_id = str(option["option_panel_id"])
        option_panel_bbox_map[option_panel_id] = list(option_panel.panel_bbox)
        option_cube_bbox_map[option_panel_id] = list(option_panel.content_bbox)

        option_face_bboxes = _draw_cube_view(
            draw,
            cube_bbox=option_panel.content_bbox,
            view_spec=option,
            border_color_rgb=render_params.border_color_rgb,
            border_width_px=int(render_params.border_width_px),
        )
        entities.append(
            {
                "entity_id": option_panel_id,
                "entity_type": "puzzle_cube_option_panel",
                "bbox_px": list(option_panel.panel_bbox),
                "attrs": {
                    "option_index": int(option_index),
                    "option_label": str(option["option_label"]),
                    "is_correct": bool(option.get("is_correct", False)),
                    "is_valid_view": bool(option.get("is_valid_view", False)),
                },
            }
        )
        entities.append(
            {
                "entity_id": f"{option_panel_id}_label",
                "entity_type": "puzzle_cube_option_label",
                "bbox_px": list(option_panel.label_bbox),
                "attrs": {
                    "option_index": int(option_index),
                    "option_label": str(option["option_label"]),
                },
            }
        )
        entities.append(
            {
                "entity_id": f"{option_panel_id}_cube_box",
                "entity_type": "puzzle_cube_option_box",
                "bbox_px": list(option_panel.content_bbox),
                "attrs": {
                    "option_index": int(option_index),
                    "option_label": str(option["option_label"]),
                },
            }
        )
        for face_role, face_bbox in option_face_bboxes.items():
            entities.append(
                {
                    "entity_id": f"{option_panel_id}_{face_role}_face",
                    "entity_type": "puzzle_cube_face",
                    "bbox_px": list(face_bbox),
                    "attrs": {
                        "cube_role": "option",
                        "option_index": int(option_index),
                        "option_label": str(option["option_label"]),
                        "face_role": str(face_role),
                        "object_type": str(option[f"{face_role}_object_type"]),
                    },
                }
            )

    if selected_variant in {"cube_card", "cube_outline"}:
        scene_bbox = [
            round(float(min(reference_panel_bbox[0], options_panel_bbox[0])), 3),
            round(float(min(reference_panel_bbox[1], options_panel_bbox[1])), 3),
            round(float(max(reference_panel_bbox[2], options_panel_bbox[2])), 3),
            round(float(max(reference_panel_bbox[3], options_panel_bbox[3])), 3),
        ]
    else:
        scene_bbox = [
            round(float(min(reference_cube_bbox[0], options_left)), 3),
            round(float(min(reference_cube_bbox[1], options_top)), 3),
            round(float(max(reference_cube_bbox[2], options_left + options_width)), 3),
            round(float(max(reference_cube_bbox[3], options_top + option_panel_height)), 3),
        ]
    return RenderedPuzzleCubeScene(
        image=image,
        entities=entities,
        scene_bbox_px=list(scene_bbox),
        option_panel_bbox_map=option_panel_bbox_map,
        option_cube_bbox_map=option_cube_bbox_map,
        reference_cube_bbox_px=list(reference_cube_bbox),
        pair_box_bbox_map=pair_box_bbox_map,
    )


__all__ = [
    "PuzzleCubeRenderParams",
    "RenderedPuzzleCubeScene",
    "SUPPORTED_PUZZLE_CUBE_SCENE_VARIANTS",
    "render_puzzle_cube_scene",
]
