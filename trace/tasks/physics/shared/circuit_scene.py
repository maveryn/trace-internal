"""Shared resistor-network rendering helpers for physics circuits tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.drawing import draw_rounded_rect
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from .style import build_physics_circuit_theme


@dataclass(frozen=True)
class CircuitResistorSpec:
    """One visible resistor box in a rendered circuit scene."""

    resistor_id: str
    value: int
    bbox_px: List[float]


@dataclass(frozen=True)
class RenderedCircuitScene:
    """Rendered resistor-network scene plus prompt-facing evidence metadata."""

    image: Image.Image
    resistor_specs: List[CircuitResistorSpec]
    evidence_bboxes: List[List[float]]
    evidence_entity_ids: List[str]
    render_map: Dict[str, Any]
    scene_entities: List[Dict[str, Any]]


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center_xy: Tuple[float, float],
    font,
    fill: Tuple[int, int, int],
    stroke_width_px: int,
) -> List[float]:
    """Draw centered text and return the rendered bbox."""

    stroke_fill = resolve_text_stroke_fill(fill)
    bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width_px)))
    left, top, right, bottom = [float(value) for value in bbox]
    center_x, center_y = float(center_xy[0]), float(center_xy[1])
    origin = (
        float(center_x - (0.5 * (left + right))),
        float(center_y - (0.5 * (top + bottom))),
    )
    draw.text(
        origin,
        str(text),
        font=font,
        fill=tuple(int(value) for value in fill),
        stroke_width=max(0, int(stroke_width_px)),
        stroke_fill=tuple(int(value) for value in stroke_fill),
    )
    return [
        round(float(origin[0] + left), 3),
        round(float(origin[1] + top), 3),
        round(float(origin[0] + right), 3),
        round(float(origin[1] + bottom), 3),
    ]


def _draw_terminal(
    draw: ImageDraw.ImageDraw,
    *,
    center_xy: Tuple[float, float],
    label: str,
    radius_px: float,
    font,
    theme,
    stroke_width_px: int,
) -> tuple[List[float], List[float]]:
    """Draw one labeled terminal and return circle/text bboxes."""

    center_x, center_y = float(center_xy[0]), float(center_xy[1])
    circle_bbox = [
        round(float(center_x - radius_px), 3),
        round(float(center_y - radius_px), 3),
        round(float(center_x + radius_px), 3),
        round(float(center_y + radius_px), 3),
    ]
    draw.ellipse(
        tuple(float(value) for value in circle_bbox),
        fill=tuple(int(channel) for channel in theme.terminal_fill_rgb),
        outline=tuple(int(channel) for channel in theme.terminal_outline_rgb),
        width=3,
    )
    text_bbox = _draw_centered_text(
        draw,
        text=str(label),
        center_xy=(float(center_x), float(center_y - (radius_px + 22.0))),
        font=font,
        fill=tuple(int(channel) for channel in theme.terminal_text_rgb),
        stroke_width_px=int(stroke_width_px),
    )
    return circle_bbox, text_bbox


def _draw_resistor_box(
    draw: ImageDraw.ImageDraw,
    *,
    bbox_px: Sequence[float],
    value: int,
    font,
    theme,
    stroke_width_px: int,
) -> List[float]:
    """Draw one resistor box with its integer value."""

    draw_rounded_rect(
        draw,
        tuple(float(value_px) for value_px in bbox_px),
        radius=10,
        fill=tuple(int(channel) for channel in theme.resistor_fill_rgb),
        outline=tuple(int(channel) for channel in theme.resistor_outline_rgb),
        width=3,
    )
    return _draw_centered_text(
        draw,
        text=str(int(value)),
        center_xy=(
            float(0.5 * (float(bbox_px[0]) + float(bbox_px[2]))),
            float(0.5 * (float(bbox_px[1]) + float(bbox_px[3]))),
        ),
        font=font,
        fill=tuple(int(channel) for channel in theme.resistor_text_rgb),
        stroke_width_px=int(stroke_width_px),
    )


def render_resistor_network_scene(
    *,
    scene_variant: str,
    series_values: Sequence[int],
    parallel_values: Sequence[int],
    background: Image.Image,
    render_defaults: Mapping[str, Any],
    accent_color_name: str,
    series_parallel_orientation: str = "series_then_parallel",
) -> RenderedCircuitScene:
    """Render one resistor network between labeled terminals `A` and `B`."""

    canvas = background.convert("RGB")
    draw = ImageDraw.Draw(canvas)
    theme = build_physics_circuit_theme(str(accent_color_name))
    canvas_width = int(render_defaults["canvas_width"])
    canvas_height = int(render_defaults["canvas_height"])
    mid_y = float(0.5 * canvas_height)
    wire_width = int(render_defaults["wire_width_px"])
    terminal_radius = float(render_defaults["terminal_radius_px"])
    resistor_box_width = float(render_defaults["resistor_box_width_px"])
    resistor_box_height = float(render_defaults["resistor_box_height_px"])
    terminal_label_font = load_font(int(render_defaults["terminal_font_size_px"]), bold=True)
    resistor_font = load_font(int(render_defaults["resistor_font_size_px"]), bold=True)
    label_stroke_width = int(render_defaults["label_stroke_width_px"])

    terminal_left = (float(render_defaults["terminal_left_x_px"]), float(mid_y))
    terminal_right = (float(canvas_width - int(render_defaults["terminal_left_x_px"])), float(mid_y))
    left_circle_bbox, left_label_bbox = _draw_terminal(
        draw,
        center_xy=terminal_left,
        label="A",
        radius_px=float(terminal_radius),
        font=terminal_label_font,
        theme=theme,
        stroke_width_px=label_stroke_width,
    )
    right_circle_bbox, right_label_bbox = _draw_terminal(
        draw,
        center_xy=terminal_right,
        label="B",
        radius_px=float(terminal_radius),
        font=terminal_label_font,
        theme=theme,
        stroke_width_px=label_stroke_width,
    )

    resistor_specs: List[CircuitResistorSpec] = []
    scene_entities: List[Dict[str, Any]] = [
        {
            "entity_id": "terminal_A",
            "entity_type": "physics_circuit_terminal",
            "bbox_px": list(left_circle_bbox),
            "meta": {"terminal_label": "A"},
        },
        {
            "entity_id": "terminal_B",
            "entity_type": "physics_circuit_terminal",
            "bbox_px": list(right_circle_bbox),
            "meta": {"terminal_label": "B"},
        },
    ]
    wire_segments: List[List[List[float]]] = []

    def line(start_xy: Tuple[float, float], end_xy: Tuple[float, float]) -> None:
        draw.line(
            [tuple(float(v) for v in start_xy), tuple(float(v) for v in end_xy)],
            fill=tuple(int(channel) for channel in theme.wire_rgb),
            width=max(1, int(wire_width)),
        )
        wire_segments.append(
            [
                [round(float(start_xy[0]), 3), round(float(start_xy[1]), 3)],
                [round(float(end_xy[0]), 3), round(float(end_xy[1]), 3)],
            ]
        )

    def add_resistor(resistor_id: str, value: int, bbox_px: Sequence[float]) -> None:
        _draw_resistor_box(
            draw,
            bbox_px=bbox_px,
            value=int(value),
            font=resistor_font,
            theme=theme,
            stroke_width_px=label_stroke_width,
        )
        bbox = [round(float(component), 3) for component in bbox_px]
        resistor_specs.append(
            CircuitResistorSpec(
                resistor_id=str(resistor_id),
                value=int(value),
                bbox_px=list(bbox),
            )
        )
        scene_entities.append(
            {
                "entity_id": str(resistor_id),
                "entity_type": "physics_resistor",
                "bbox_px": list(bbox),
                "meta": {"value": int(value)},
            }
        )

    next_resistor_index = 1

    def add_series_chain(start_x: float, end_x: float, values: Sequence[int]) -> None:
        nonlocal next_resistor_index
        if not values:
            line((float(start_x), float(mid_y)), (float(end_x), float(mid_y)))
            return
        count = len(values)
        usable_width = float(end_x - start_x)
        step = usable_width / float(count)
        previous_x = float(start_x)
        for value_index, value in enumerate(values):
            center_x = float(start_x + ((value_index + 0.5) * step))
            bbox = [
                round(float(center_x - (0.5 * resistor_box_width)), 3),
                round(float(mid_y - (0.5 * resistor_box_height)), 3),
                round(float(center_x + (0.5 * resistor_box_width)), 3),
                round(float(mid_y + (0.5 * resistor_box_height)), 3),
            ]
            line((float(previous_x), float(mid_y)), (float(bbox[0]), float(mid_y)))
            add_resistor(f"resistor_{int(next_resistor_index)}", int(value), bbox)
            next_resistor_index += 1
            previous_x = float(bbox[2])
        line((float(previous_x), float(mid_y)), (float(end_x), float(mid_y)))

    def add_parallel_bank(left_x: float, right_x: float, values: Sequence[int]) -> None:
        nonlocal next_resistor_index
        if not values:
            return
        branch_top_y = float(render_defaults["parallel_branch_top_y_px"])
        branch_bottom_y = float(render_defaults["parallel_branch_bottom_y_px"])
        if len(values) == 1:
            branch_ys = [float(0.5 * (branch_top_y + branch_bottom_y))]
        else:
            step_y = float(branch_bottom_y - branch_top_y) / float(len(values) - 1)
            branch_ys = [float(branch_top_y + (index * step_y)) for index in range(len(values))]
        line((left_x, float(min(branch_ys))), (left_x, float(max(branch_ys))))
        line((right_x, float(min(branch_ys))), (right_x, float(max(branch_ys))))
        resistor_center_x = 0.5 * float(left_x + right_x)
        for value, branch_y in zip(values, branch_ys, strict=True):
            bbox = [
                round(float(resistor_center_x - (0.5 * resistor_box_width)), 3),
                round(float(branch_y - (0.5 * resistor_box_height)), 3),
                round(float(resistor_center_x + (0.5 * resistor_box_width)), 3),
                round(float(branch_y + (0.5 * resistor_box_height)), 3),
            ]
            line((left_x, float(branch_y)), (float(bbox[0]), float(branch_y)))
            line((float(bbox[2]), float(branch_y)), (right_x, float(branch_y)))
            add_resistor(f"resistor_{int(next_resistor_index)}", int(value), bbox)
            next_resistor_index += 1

    if str(scene_variant) == "parallel":
        rail_left_x = float(render_defaults["parallel_rail_left_x_px"])
        rail_right_x = float(canvas_width - int(render_defaults["parallel_rail_left_x_px"]))
        line((float(terminal_left[0] + terminal_radius), float(mid_y)), (rail_left_x, float(mid_y)))
        line((rail_right_x, float(mid_y)), (float(terminal_right[0] - terminal_radius), float(mid_y)))
        add_parallel_bank(rail_left_x, rail_right_x, parallel_values)
    else:
        branch_left_x = float(render_defaults["series_parallel_branch_left_x_px"])
        branch_right_x = float(canvas_width - int(render_defaults["series_parallel_branch_left_x_px"]))
        left_anchor_x = float(terminal_left[0] + terminal_radius)
        right_anchor_x = float(terminal_right[0] - terminal_radius)
        if str(series_parallel_orientation) == "series_then_parallel":
            add_series_chain(left_anchor_x, branch_left_x, series_values)
            line((branch_right_x, float(mid_y)), (right_anchor_x, float(mid_y)))
        else:
            line((left_anchor_x, float(mid_y)), (branch_left_x, float(mid_y)))
            add_series_chain(branch_right_x, right_anchor_x, series_values)
        add_parallel_bank(branch_left_x, branch_right_x, parallel_values)

    render_map = {
        "accent_color_name": str(accent_color_name),
        "resistor_bboxes_px": {spec.resistor_id: list(spec.bbox_px) for spec in resistor_specs},
        "wire_segments_px": list(wire_segments),
        "terminal_bboxes_px": {
            "A": list(left_circle_bbox),
            "B": list(right_circle_bbox),
        },
        "terminal_label_bboxes_px": {
            "A": list(left_label_bbox),
            "B": list(right_label_bbox),
        },
        "evidence_entity_ids": [str(spec.resistor_id) for spec in resistor_specs],
    }
    return RenderedCircuitScene(
        image=canvas,
        resistor_specs=list(resistor_specs),
        evidence_bboxes=[list(spec.bbox_px) for spec in resistor_specs],
        evidence_entity_ids=[str(spec.resistor_id) for spec in resistor_specs],
        render_map=render_map,
        scene_entities=list(scene_entities),
    )


__all__ = [
    "CircuitResistorSpec",
    "RenderedCircuitScene",
    "render_resistor_network_scene",
]
