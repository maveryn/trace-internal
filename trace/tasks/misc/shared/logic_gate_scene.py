"""Shared Boolean logic-gate circuit renderer for misc notation tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font
from .drawing import draw_centered_text, draw_rounded_rect
from .scene_style import MiscSceneStyle


SUPPORTED_LOGIC_GATE_TYPES: tuple[str, ...] = ("AND", "OR", "NOT", "XOR", "NAND", "NOR")
SUPPORTED_LOGIC_GATE_SCENE_VARIANTS: tuple[str, ...] = ("clean_worksheet", "notebook_problem", "exam_scan")


@dataclass(frozen=True)
class LogicInputSpec:
    item_id: str
    label: str
    value: int | None = None


@dataclass(frozen=True)
class LogicGateSpec:
    item_id: str
    gate_type: str
    input_signal_ids: tuple[str, ...]
    output_signal_id: str


@dataclass(frozen=True)
class LogicCircuitSpec:
    item_id: str
    label: str
    inputs: tuple[LogicInputSpec, ...]
    gates: tuple[LogicGateSpec, ...]
    output_signal_id: str
    output_value: int | None = None
    role: str = "circuit"


@dataclass(frozen=True)
class CandidateAssignmentSpec:
    item_id: str
    label: str
    values: Mapping[str, int]
    output_value: int
    is_correct: bool = False


@dataclass(frozen=True)
class LogicGateRenderParams:
    canvas_width: int = 1180
    canvas_height: int = 820
    card_corner_radius_px: int = 18
    card_border_width_px: int = 2
    gate_width_px: int = 72
    gate_height_px: int = 38
    wire_width_px: int = 3
    node_radius_px: int = 5
    label_font_size_px: int = 22
    small_font_size_px: int = 16
    gate_font_size_px: int = 15
    table_font_size_px: int = 20


@dataclass(frozen=True)
class RenderedLogicGateScene:
    image: Image.Image
    entities: tuple[dict[str, Any], ...]
    item_bboxes: dict[str, list[float]]
    output_points: dict[str, list[float]]
    signal_points: dict[str, list[float]]
    scene_bbox_px: list[float]
    style_metadata: dict[str, Any]


def _rounded_bbox(values: Sequence[float]) -> list[float]:
    return [round(float(value), 3) for value in values]


def _rounded_point(x: float, y: float) -> list[float]:
    return [round(float(x), 3), round(float(y), 3)]


def evaluate_logic_gate(gate_type: str, input_values: Sequence[int]) -> int:
    """Evaluate one supported Boolean gate over 0/1 input values."""

    gate = str(gate_type).upper()
    values = tuple(1 if int(value) else 0 for value in input_values)
    if gate not in SUPPORTED_LOGIC_GATE_TYPES:
        raise ValueError(f"unsupported logic gate type: {gate_type}")
    if gate == "NOT":
        if len(values) != 1:
            raise ValueError("NOT gate requires exactly one input")
        return 0 if values[0] else 1
    if len(values) != 2:
        raise ValueError(f"{gate} gate requires exactly two inputs")
    a, b = int(values[0]), int(values[1])
    if gate == "AND":
        return 1 if a and b else 0
    if gate == "OR":
        return 1 if a or b else 0
    if gate == "XOR":
        return 1 if a != b else 0
    if gate == "NAND":
        return 0 if a and b else 1
    if gate == "NOR":
        return 0 if a or b else 1
    raise AssertionError(f"unhandled logic gate type: {gate}")


def evaluate_logic_circuit(circuit: LogicCircuitSpec, assignment: Mapping[str, int] | None = None) -> int:
    """Evaluate a topologically ordered circuit spec."""

    assignment_values = {str(key): int(value) for key, value in dict(assignment or {}).items()}
    signal_values: dict[str, int] = {}
    for input_spec in circuit.inputs:
        if input_spec.value is None:
            if str(input_spec.label) not in assignment_values:
                raise ValueError(f"missing assignment value for input {input_spec.label!r}")
            value = int(assignment_values[str(input_spec.label)])
        else:
            value = int(input_spec.value)
        signal_values[str(input_spec.item_id)] = 1 if value else 0
    for gate in circuit.gates:
        inputs = [signal_values[str(signal_id)] for signal_id in gate.input_signal_ids]
        signal_values[str(gate.output_signal_id)] = evaluate_logic_gate(str(gate.gate_type), inputs)
    return int(signal_values[str(circuit.output_signal_id)])


def _draw_wire(
    draw: ImageDraw.ImageDraw,
    *,
    start: Sequence[float],
    end: Sequence[float],
    rgb: Sequence[int],
    width: int,
) -> None:
    sx, sy = float(start[0]), float(start[1])
    ex, ey = float(end[0]), float(end[1])
    mid_x = sx + max(12.0, 0.5 * (ex - sx))
    draw.line((sx, sy, mid_x, sy, mid_x, ey, ex, ey), fill=tuple(int(v) for v in rgb), width=int(width), joint="curve")


def _gate_input_ports(gate_bbox: Sequence[float], count: int) -> tuple[tuple[float, float], ...]:
    left, top, _right, bottom = [float(value) for value in gate_bbox]
    if int(count) == 1:
        return ((left, 0.5 * (top + bottom)),)
    return ((left, top + 0.34 * (bottom - top)), (left, top + 0.66 * (bottom - top)))


def _draw_output_node(
    draw: ImageDraw.ImageDraw,
    *,
    center: Sequence[float],
    params: LogicGateRenderParams,
    style: MiscSceneStyle,
) -> None:
    cx, cy = float(center[0]), float(center[1])
    radius = int(params.node_radius_px)
    draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=tuple(int(v) for v in style.panel_accent_rgb),
        outline=tuple(int(v) for v in style.text_rgb),
        width=1,
    )


def _draw_logic_circuit(
    draw: ImageDraw.ImageDraw,
    *,
    circuit: LogicCircuitSpec,
    bbox: Sequence[float],
    params: LogicGateRenderParams,
    style: MiscSceneStyle,
    show_fixed_input_values: bool,
    title: str | None = None,
) -> tuple[dict[str, Any], dict[str, list[float]], dict[str, list[float]], dict[str, list[float]]]:
    """Draw one circuit inside a panel and return entity/geometry maps."""

    left, top, right, bottom = [float(value) for value in bbox]
    item_bboxes: dict[str, list[float]] = {str(circuit.item_id): _rounded_bbox(bbox)}
    output_points: dict[str, list[float]] = {}
    signal_points: dict[str, list[float]] = {}

    draw_rounded_rect(
        draw,
        (left, top, right, bottom),
        radius=int(params.card_corner_radius_px),
        fill=tuple(int(v) for v in style.panel_fill_rgb),
        outline=tuple(int(v) for v in style.panel_border_rgb),
        width=int(params.card_border_width_px),
    )

    title_font = load_font(int(params.label_font_size_px), bold=True)
    small_font = load_font(int(params.small_font_size_px), bold=True)
    gate_font = load_font(int(params.gate_font_size_px), bold=True)
    if str(circuit.label).strip():
        label_bbox = draw_centered_text(
            draw,
            text=str(circuit.label),
            center=(left + 22.0, top + 24.0),
            font=title_font,
            fill=style.text_rgb,
            stroke_fill=style.panel_fill_rgb,
            stroke_width=2,
        )
        item_bboxes[f"{circuit.item_id}_label"] = list(label_bbox)
    if title:
        draw_centered_text(
            draw,
            text=str(title),
            center=(0.5 * (left + right), top + 24.0),
            font=small_font,
            fill=style.text_rgb,
            stroke_fill=style.panel_fill_rgb,
            stroke_width=2,
        )

    input_x = left + 48.0
    input_top = top + 62.0
    input_bottom = bottom - 58.0
    input_count = max(1, len(circuit.inputs))
    input_gap = 0.0 if input_count == 1 else (input_bottom - input_top) / float(input_count - 1)
    signal_source_points: dict[str, tuple[float, float]] = {}
    for index, input_spec in enumerate(circuit.inputs):
        y = input_top + (index * input_gap)
        text = str(input_spec.label)
        if bool(show_fixed_input_values) and input_spec.value is not None:
            text = f"{input_spec.label}={int(input_spec.value)}"
        input_bbox = draw_centered_text(
            draw,
            text=text,
            center=(input_x, y),
            font=small_font,
            fill=style.text_rgb,
            stroke_fill=style.panel_fill_rgb,
            stroke_width=2,
        )
        port = (input_x + 36.0, y)
        signal_source_points[str(input_spec.item_id)] = port
        signal_points[str(input_spec.item_id)] = _rounded_point(*port)
        item_bboxes[str(input_spec.item_id)] = _rounded_bbox(input_bbox)
        draw.ellipse((port[0] - 3, port[1] - 3, port[0] + 3, port[1] + 3), fill=tuple(int(v) for v in style.text_rgb))

    signal_level: dict[str, int] = {str(input_spec.item_id): 0 for input_spec in circuit.inputs}
    gate_levels: dict[str, int] = {}
    level_counts: dict[int, int] = {}
    level_indices: dict[str, int] = {}
    for gate in circuit.gates:
        level = 1 + max(signal_level[str(signal_id)] for signal_id in gate.input_signal_ids)
        gate_levels[str(gate.item_id)] = int(level)
        level_indices[str(gate.item_id)] = int(level_counts.get(int(level), 0))
        level_counts[int(level)] = int(level_counts.get(int(level), 0)) + 1
        signal_level[str(gate.output_signal_id)] = int(level)

    max_level = max(gate_levels.values(), default=1)
    gate_area_left = left + 145.0
    gate_area_right = right - 112.0
    level_gap = 0.0 if max_level <= 1 else (gate_area_right - gate_area_left) / float(max_level - 1)
    gate_centers: dict[str, tuple[float, float]] = {}
    for gate in circuit.gates:
        level = int(gate_levels[str(gate.item_id)])
        count_on_level = int(level_counts[int(level)])
        index_on_level = int(level_indices[str(gate.item_id)])
        x = gate_area_left + ((level - 1) * level_gap)
        y_min = top + 72.0
        y_max = bottom - 72.0
        if count_on_level == 1:
            y = 0.5 * (y_min + y_max)
        else:
            center_y = 0.5 * (y_min + y_max)
            desired_gap = float(params.gate_height_px) + 10.0
            available_span = max(1.0, y_max - y_min)
            gap = min(desired_gap, available_span / float(max(1, count_on_level - 1)))
            y = center_y - (0.5 * gap * float(count_on_level - 1)) + (float(index_on_level) * gap)
        gate_centers[str(gate.item_id)] = (x, y)

    gate_draw_specs: list[dict[str, Any]] = []
    wire_segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for gate in circuit.gates:
        cx, cy = gate_centers[str(gate.item_id)]
        gate_bbox = (
            cx - 0.5 * int(params.gate_width_px),
            cy - 0.5 * int(params.gate_height_px),
            cx + 0.5 * int(params.gate_width_px),
            cy + 0.5 * int(params.gate_height_px),
        )
        input_ports = _gate_input_ports(gate_bbox, len(gate.input_signal_ids))
        for input_index, signal_id in enumerate(gate.input_signal_ids):
            wire_segments.append((signal_source_points[str(signal_id)], input_ports[int(input_index)]))
        if str(gate.gate_type).upper() in {"NOT", "NAND", "NOR"}:
            bubble_r = 4.0
            bubble_cx = float(gate_bbox[2]) + bubble_r
            bubble_cy = cy
            out_port = (bubble_cx + bubble_r, bubble_cy)
        else:
            bubble_r = 0.0
            bubble_cx = 0.0
            bubble_cy = 0.0
            out_port = (float(gate_bbox[2]), cy)
        signal_source_points[str(gate.output_signal_id)] = out_port
        signal_points[str(gate.output_signal_id)] = _rounded_point(*out_port)
        item_bboxes[str(gate.item_id)] = _rounded_bbox(gate_bbox)
        gate_draw_specs.append(
            {
                "gate_type": str(gate.gate_type),
                "bbox": gate_bbox,
                "center": (cx, cy),
                "has_bubble": str(gate.gate_type).upper() in {"NOT", "NAND", "NOR"},
                "bubble": (bubble_cx, bubble_cy, bubble_r),
            }
        )

    final_source = signal_source_points[str(circuit.output_signal_id)]
    output_center = (right - 54.0, final_source[1])
    wire_segments.append((final_source, output_center))
    for start, end in wire_segments:
        _draw_wire(
            draw,
            start=start,
            end=end,
            rgb=style.text_rgb,
            width=int(params.wire_width_px),
        )
    for gate_spec in gate_draw_specs:
        gate_bbox = gate_spec["bbox"]
        cx, cy = gate_spec["center"]
        draw_rounded_rect(
            draw,
            gate_bbox,
            radius=10,
            fill=tuple(int(v) for v in style.panel_fill_rgb),
            outline=tuple(int(v) for v in style.text_rgb),
            width=2,
        )
        draw_centered_text(
            draw,
            text=str(gate_spec["gate_type"]),
            center=(float(cx), float(cy)),
            font=gate_font,
            fill=style.text_rgb,
            stroke_fill=style.panel_fill_rgb,
            stroke_width=1,
        )
        if bool(gate_spec["has_bubble"]):
            bubble_cx, bubble_cy, bubble_r = gate_spec["bubble"]
            draw.ellipse(
                (
                    float(bubble_cx) - float(bubble_r),
                    float(bubble_cy) - float(bubble_r),
                    float(bubble_cx) + float(bubble_r),
                    float(bubble_cy) + float(bubble_r),
                ),
                fill=tuple(int(v) for v in style.panel_fill_rgb),
                outline=tuple(int(v) for v in style.text_rgb),
                width=2,
            )
    _draw_output_node(draw, center=output_center, params=params, style=style)
    draw_centered_text(
        draw,
        text="OUT",
        center=(right - 54.0, output_center[1] + 23.0),
        font=small_font,
        fill=style.text_rgb,
        stroke_fill=style.panel_fill_rgb,
        stroke_width=2,
    )
    output_id = f"{circuit.item_id}_output"
    output_points[output_id] = _rounded_point(*output_center)
    signal_points[output_id] = _rounded_point(*output_center)
    item_bboxes[output_id] = _rounded_bbox(
        (
            output_center[0] - int(params.node_radius_px),
            output_center[1] - int(params.node_radius_px),
            output_center[0] + int(params.node_radius_px),
            output_center[1] + int(params.node_radius_px),
        )
    )
    entity = {
        "item_id": str(circuit.item_id),
        "entity_type": "logic_circuit",
        "role": str(circuit.role),
        "label": str(circuit.label),
        "bbox_px": _rounded_bbox(bbox),
        "input_ids": [str(item.item_id) for item in circuit.inputs],
        "gate_ids": [str(item.item_id) for item in circuit.gates],
        "output_point_id": str(output_id),
        "output_value": None if circuit.output_value is None else int(circuit.output_value),
    }
    return entity, item_bboxes, output_points, signal_points


def render_logic_gate_count_scene(
    image: Image.Image,
    *,
    circuits: Sequence[LogicCircuitSpec],
    params: LogicGateRenderParams,
    style: MiscSceneStyle,
) -> RenderedLogicGateScene:
    """Render six independent circuit panels for output-value counting."""

    if len(circuits) != 6:
        raise ValueError("logic-gate count scenes require exactly six circuits")
    draw = ImageDraw.Draw(image)
    width, height = int(params.canvas_width), int(params.canvas_height)
    margin_x = 44
    margin_y = 50
    gap_x = 28
    gap_y = 24
    card_w = (width - (2 * margin_x) - gap_x) / 2.0
    card_h = (height - (2 * margin_y) - (2 * gap_y)) / 3.0

    entities: list[dict[str, Any]] = []
    item_bboxes: dict[str, list[float]] = {}
    output_points: dict[str, list[float]] = {}
    signal_points: dict[str, list[float]] = {}
    for index, circuit in enumerate(circuits):
        row = index // 2
        col = index % 2
        left = margin_x + col * (card_w + gap_x)
        top = margin_y + row * (card_h + gap_y)
        bbox = (left, top, left + card_w, top + card_h)
        entity, boxes, points, signals = _draw_logic_circuit(
            draw,
            circuit=circuit,
            bbox=bbox,
            params=params,
            style=style,
            show_fixed_input_values=True,
        )
        entities.append(entity)
        item_bboxes.update(boxes)
        output_points.update(points)
        signal_points.update(signals)

    return RenderedLogicGateScene(
        image=image,
        entities=tuple(entities),
        item_bboxes=item_bboxes,
        output_points=output_points,
        signal_points=signal_points,
        scene_bbox_px=_rounded_bbox((30, 32, width - 30, height - 32)),
        style_metadata={"renderer": "logic_gate_circuit_v0", "layout": "six_circuit_grid"},
    )


def render_logic_assignment_scene(
    image: Image.Image,
    *,
    circuit: LogicCircuitSpec,
    candidates: Sequence[CandidateAssignmentSpec],
    params: LogicGateRenderParams,
    style: MiscSceneStyle,
) -> RenderedLogicGateScene:
    """Render one source circuit and six labeled candidate assignment rows."""

    if len(candidates) != 6:
        raise ValueError("logic-gate assignment scenes require exactly six candidates")
    draw = ImageDraw.Draw(image)
    width, height = int(params.canvas_width), int(params.canvas_height)
    entities: list[dict[str, Any]] = []
    item_bboxes: dict[str, list[float]] = {}
    output_points: dict[str, list[float]] = {}
    signal_points: dict[str, list[float]] = {}

    circuit_bbox = (48.0, 120.0, 730.0, 690.0)
    entity, boxes, points, signals = _draw_logic_circuit(
        draw,
        circuit=circuit,
        bbox=circuit_bbox,
        params=params,
        style=style,
        show_fixed_input_values=False,
        title="Source circuit",
    )
    entities.append(entity)
    item_bboxes.update(boxes)
    output_points.update(points)
    signal_points.update(signals)

    table_bbox = (775.0, 126.0, float(width - 48), 690.0)
    draw_rounded_rect(
        draw,
        table_bbox,
        radius=int(params.card_corner_radius_px),
        fill=tuple(int(v) for v in style.panel_fill_rgb),
        outline=tuple(int(v) for v in style.panel_border_rgb),
        width=int(params.card_border_width_px),
    )
    table_font = load_font(int(params.table_font_size_px), bold=True)
    small_font = load_font(int(params.small_font_size_px), bold=True)
    title_font = load_font(int(params.label_font_size_px), bold=True)
    draw_centered_text(
        draw,
        text="Assignments",
        center=(0.5 * (table_bbox[0] + table_bbox[2]), table_bbox[1] + 28.0),
        font=title_font,
        fill=style.text_rgb,
        stroke_fill=style.panel_fill_rgb,
        stroke_width=2,
    )

    header_y = table_bbox[1] + 70.0
    col_x = {
        "label": table_bbox[0] + 38.0,
        "x": table_bbox[0] + 122.0,
        "y": table_bbox[0] + 206.0,
        "z": table_bbox[0] + 290.0,
    }
    for key, label in (("label", ""), ("x", "x"), ("y", "y"), ("z", "z")):
        draw_centered_text(
            draw,
            text=str(label),
            center=(col_x[str(key)], header_y),
            font=small_font,
            fill=style.text_rgb,
            stroke_fill=style.panel_fill_rgb,
            stroke_width=2,
        )
    draw.line(
        (table_bbox[0] + 18, header_y + 24, table_bbox[2] - 18, header_y + 24),
        fill=tuple(int(v) for v in style.grid_rgb),
        width=2,
    )

    row_h = 66.0
    row_top = header_y + 42.0
    for index, candidate in enumerate(candidates):
        top = row_top + (index * row_h)
        bbox = (table_bbox[0] + 18.0, top, table_bbox[2] - 18.0, top + row_h - 10.0)
        if index % 2 == 0:
            draw.rounded_rectangle(
                bbox,
                radius=8,
                fill=tuple(int(0.5 * int(a) + 0.5 * int(b)) for a, b in zip(style.panel_fill_rgb, style.background_rgb)),
                outline=None,
            )
        y_center = 0.5 * (bbox[1] + bbox[3])
        draw_centered_text(
            draw,
            text=str(candidate.label),
            center=(col_x["label"], y_center),
            font=table_font,
            fill=style.text_rgb,
            stroke_fill=style.panel_fill_rgb,
            stroke_width=2,
        )
        for key in ("x", "y", "z"):
            draw_centered_text(
                draw,
                text=str(int(candidate.values[str(key)])),
                center=(col_x[str(key)], y_center),
                font=table_font,
                fill=style.text_rgb,
                stroke_fill=style.panel_fill_rgb,
                stroke_width=2,
            )
        item_bboxes[str(candidate.item_id)] = _rounded_bbox(bbox)
        entities.append(
            {
                "item_id": str(candidate.item_id),
                "entity_type": "logic_assignment_option",
                "role": "correct_option" if bool(candidate.is_correct) else "distractor_option",
                "label": str(candidate.label),
                "values": {str(key): int(value) for key, value in candidate.values.items()},
                "output_value": int(candidate.output_value),
                "is_correct": bool(candidate.is_correct),
                "bbox_px": _rounded_bbox(bbox),
            }
        )

    item_bboxes["assignment_table"] = _rounded_bbox(table_bbox)
    entities.append(
        {
            "item_id": "assignment_table",
            "entity_type": "logic_assignment_table",
            "role": "candidate_options",
            "bbox_px": _rounded_bbox(table_bbox),
            "option_ids": [str(candidate.item_id) for candidate in candidates],
        }
    )
    return RenderedLogicGateScene(
        image=image,
        entities=tuple(entities),
        item_bboxes=item_bboxes,
        output_points=output_points,
        signal_points=signal_points,
        scene_bbox_px=_rounded_bbox((34, 60, width - 34, height - 52)),
        style_metadata={"renderer": "logic_gate_circuit_v0", "layout": "source_circuit_and_assignment_options"},
    )


__all__ = [
    "CandidateAssignmentSpec",
    "LogicCircuitSpec",
    "LogicGateRenderParams",
    "LogicGateSpec",
    "LogicInputSpec",
    "RenderedLogicGateScene",
    "SUPPORTED_LOGIC_GATE_SCENE_VARIANTS",
    "SUPPORTED_LOGIC_GATE_TYPES",
    "evaluate_logic_circuit",
    "evaluate_logic_gate",
    "render_logic_assignment_scene",
    "render_logic_gate_count_scene",
]
