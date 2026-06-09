"""Wire-shape conversion geometry measurement tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.prompt_json_example import dump_prompt_json_examples
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import load_font
from ..shared.complexity import build_geometry_measurement_complexity, normalize_linear
from ..shared.diagram_style import prepare_geometry_diagram_style_and_background
from ..shared.fixed_query_task import (
    geometry_query_ids_for_task,
    geometry_selected_probability_map as _probability_map,
    select_indexed_geometry_query_id,
)
from ..shared.measurement_rendering import bbox_to_list, bbox_union_from_bboxes as _bbox_union, pad_bbox
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SCENE_ID = "wire_shape_conversion"
TASK_GROUP = "measurement"
TASK_ID_WIRE_LENGTH = "task_geometry__wire_shape_conversion__wire_length_value"
TASK_ID_FRAME_EDGE_LENGTH = "task_geometry__wire_shape_conversion__frame_edge_length_value"
TASK_ID_MISSING_DIMENSION = "task_geometry__wire_shape_conversion__missing_dimension_value"
TASK_ID = TASK_ID_WIRE_LENGTH
PROMPT_BUNDLE_ID = "geometry_wire_shape_conversion_v0"

QUERY_ID_TRAPEZOID_WIRE_LENGTH = "trapezoid_wire_length"
QUERY_ID_PARALLELOGRAM_WIRE_LENGTH = "parallelogram_wire_length"
QUERY_ID_CIRCLE_WIRE_LENGTH_FROM_AREA = "circle_wire_length_from_area"
QUERY_ID_TRAPEZOID_WIRE_TO_CUBE_FRAME = "trapezoid_wire_to_cube_frame"
QUERY_ID_PARALLELOGRAM_WIRE_TO_CUBOID_FRAME = "parallelogram_wire_to_cuboid_frame"
QUERY_ID_SAME_WIRE_CIRCLE_TO_TRAPEZOID_SIDE = "same_wire_circle_to_trapezoid_side"
QUERY_ID_SAME_WIRE_POLYGON_TO_RECTANGLE_SIDE = "same_wire_polygon_to_rectangle_side"

WIRE_LENGTH_QUERY_IDS: Tuple[str, ...] = (
    QUERY_ID_TRAPEZOID_WIRE_LENGTH,
    QUERY_ID_PARALLELOGRAM_WIRE_LENGTH,
    QUERY_ID_CIRCLE_WIRE_LENGTH_FROM_AREA,
)
FRAME_EDGE_LENGTH_QUERY_IDS: Tuple[str, ...] = (
    QUERY_ID_TRAPEZOID_WIRE_TO_CUBE_FRAME,
    QUERY_ID_PARALLELOGRAM_WIRE_TO_CUBOID_FRAME,
)
MISSING_DIMENSION_QUERY_IDS: Tuple[str, ...] = (
    QUERY_ID_SAME_WIRE_CIRCLE_TO_TRAPEZOID_SIDE,
    QUERY_ID_SAME_WIRE_POLYGON_TO_RECTANGLE_SIDE,
)
QUERY_IDS: Tuple[str, ...] = WIRE_LENGTH_QUERY_IDS + FRAME_EDGE_LENGTH_QUERY_IDS + MISSING_DIMENSION_QUERY_IDS

WIRE_LENGTH_ANNOTATION_KEYS: Tuple[str, ...] = ("wire_shape_bbox", "dimension_region_bbox")
FRAME_EDGE_ANNOTATION_KEYS: Tuple[str, ...] = (
    "source_wire_shape_bbox",
    "target_frame_bbox",
    "source_dimension_region_bbox",
    "target_known_dimension_region_bbox",
    "target_unknown_edge_bbox",
)
MISSING_DIMENSION_ANNOTATION_KEYS: Tuple[str, ...] = (
    "source_wire_shape_bbox",
    "target_shape_bbox",
    "source_dimension_region_bbox",
    "target_known_dimension_region_bbox",
    "target_unknown_side_bbox",
)
ANNOTATION_KEYS: Tuple[str, ...] = WIRE_LENGTH_ANNOTATION_KEYS

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", TASK_GROUP)
_PI_APPROX = 3

_TRAPEZOID_WIRE_CASES: Tuple[Tuple[int, int, int], ...] = (
    (4, 8, 5),
    (6, 10, 7),
    (8, 14, 9),
    (5, 11, 6),
    (7, 13, 8),
)
_PARALLELOGRAM_WIRE_CASES: Tuple[Tuple[int, int], ...] = (
    (5, 3),
    (6, 4),
    (8, 5),
    (9, 5),
    (10, 6),
)
_CIRCLE_AREA_CASES: Tuple[int, ...] = (3, 4, 5, 6, 7)
_TRAPEZOID_TO_CUBE_CASES: Tuple[Tuple[int, int, int], ...] = (
    (4, 8, 6),
    (6, 12, 9),
    (8, 16, 12),
    (10, 18, 16),
    (12, 24, 18),
)
_PARALLELOGRAM_TO_CUBOID_CASES: Tuple[Tuple[int, int, int, int], ...] = (
    (12, 12, 5, 4),
    (14, 14, 5, 5),
    (16, 16, 6, 5),
    (18, 18, 7, 5),
    (20, 20, 7, 6),
    (22, 22, 8, 6),
)
_CIRCLE_TO_TRAPEZOID_SIDE_CASES: Tuple[Tuple[int, int, int], ...] = (
    (5, 8, 10),
    (6, 10, 12),
    (6, 8, 12),
    (7, 10, 14),
    (8, 12, 16),
)
_POLYGON_TO_RECTANGLE_CASES: Tuple[Tuple[int, int, int], ...] = (
    (5, 7, 6),
    (6, 8, 7),
    (7, 9, 8),
    (8, 10, 9),
    (9, 11, 10),
)


@dataclass(frozen=True)
class _ResolvedProblem:
    task_id: str
    query_id: str
    source_shape: str
    target_shape: str
    source_values: Dict[str, int]
    target_values: Dict[str, int]
    answer: int
    formula_family: str
    formula: str
    query_probabilities: Dict[str, float]
    case_probabilities: Dict[str, float]
    answer_support_probabilities: Dict[str, float]


@dataclass
class _RenderContext:
    image: Any
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    line_color: Color
    secondary_color: Color
    label_color: Color
    label_stroke_color: Color
    source_fill: Color
    target_fill: Color
    accent_color: Color
    muted_color: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedScene:
    image: Any
    annotation_bboxes: Dict[str, BBox]
    label_bboxes: Dict[str, BBox]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


_QUERY_IDS_BY_TASK_ID: Dict[str, Tuple[str, ...]] = {
    TASK_ID_WIRE_LENGTH: WIRE_LENGTH_QUERY_IDS,
    TASK_ID_FRAME_EDGE_LENGTH: FRAME_EDGE_LENGTH_QUERY_IDS,
    TASK_ID_MISSING_DIMENSION: MISSING_DIMENSION_QUERY_IDS,
}


def _annotation_keys_for_task(task_id: str) -> Tuple[str, ...]:
    if str(task_id) == TASK_ID_WIRE_LENGTH:
        return WIRE_LENGTH_ANNOTATION_KEYS
    if str(task_id) == TASK_ID_FRAME_EDGE_LENGTH:
        return FRAME_EDGE_ANNOTATION_KEYS
    if str(task_id) == TASK_ID_MISSING_DIMENSION:
        return MISSING_DIMENSION_ANNOTATION_KEYS
    raise ValueError(f"unsupported wire-shape-conversion task_id: {task_id}")


def _case_key(query_id: str, case: Sequence[int] | int) -> str:
    if isinstance(case, int):
        return f"{query_id}:{case}"
    return f"{query_id}:" + "_".join(str(int(value)) for value in case)


def _cases_for_query(query_id: str) -> Tuple[Any, ...]:
    if str(query_id) in {QUERY_ID_TRAPEZOID_WIRE_LENGTH, QUERY_ID_TRAPEZOID_WIRE_TO_CUBE_FRAME}:
        return tuple(_TRAPEZOID_WIRE_CASES if str(query_id) == QUERY_ID_TRAPEZOID_WIRE_LENGTH else _TRAPEZOID_TO_CUBE_CASES)
    if str(query_id) == QUERY_ID_PARALLELOGRAM_WIRE_LENGTH:
        return tuple(_PARALLELOGRAM_WIRE_CASES)
    if str(query_id) == QUERY_ID_CIRCLE_WIRE_LENGTH_FROM_AREA:
        return tuple(_CIRCLE_AREA_CASES)
    if str(query_id) == QUERY_ID_PARALLELOGRAM_WIRE_TO_CUBOID_FRAME:
        return tuple(_PARALLELOGRAM_TO_CUBOID_CASES)
    if str(query_id) == QUERY_ID_SAME_WIRE_CIRCLE_TO_TRAPEZOID_SIDE:
        return tuple(_CIRCLE_TO_TRAPEZOID_SIDE_CASES)
    if str(query_id) == QUERY_ID_SAME_WIRE_POLYGON_TO_RECTANGLE_SIDE:
        return tuple(_POLYGON_TO_RECTANGLE_CASES)
    raise ValueError(f"unsupported query_id: {query_id}")


def _select_case(*, query_id: str, instance_seed: int, params: Mapping[str, Any]) -> tuple[Any, Dict[str, float]]:
    cases = _cases_for_query(str(query_id))
    explicit = params.get("wire_case")
    if explicit is not None:
        if isinstance(explicit, int):
            case: Any = int(explicit)
        elif isinstance(explicit, Sequence) and not isinstance(explicit, (str, bytes)):
            case = tuple(int(value) for value in explicit)
        else:
            raise ValueError("wire_case must be an integer or numeric sequence")
        selected = _case_key(str(query_id), case)
        keys = tuple(_case_key(str(query_id), candidate) for candidate in cases) + (selected,)
        return case, {key: (1.0 if key == selected else 0.0) for key in dict.fromkeys(keys)}
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{query_id}.case")
    case = cases[int(index) % len(cases)]
    probability = 1.0 / float(len(cases))
    return case, {_case_key(str(query_id), candidate): probability for candidate in cases}


def _trapezoid_perimeter(top: int, bottom: int, side: int) -> int:
    return int(top) + int(bottom) + 2 * int(side)


def _parallelogram_perimeter(base: int, side: int) -> int:
    return 2 * (int(base) + int(side))


def _circle_circumference_from_radius(radius: int) -> int:
    return 2 * _PI_APPROX * int(radius)


def _resolve_case(task_id: str, query_id: str, case: Any) -> _ResolvedProblem:
    if str(query_id) == QUERY_ID_TRAPEZOID_WIRE_LENGTH:
        top, bottom, side = [int(value) for value in case]
        answer = _trapezoid_perimeter(top, bottom, side)
        source_values = {"top": top, "bottom": bottom, "side": side, "wire_length": answer}
        target_values: Dict[str, int] = {}
        formula = "wire_length = top_base + bottom_base + 2 * equal_side"
        source_shape, target_shape = "isosceles_trapezoid_wire", ""
    elif str(query_id) == QUERY_ID_PARALLELOGRAM_WIRE_LENGTH:
        base, side = [int(value) for value in case]
        answer = _parallelogram_perimeter(base, side)
        source_values = {"base": base, "side": side, "wire_length": answer}
        target_values = {}
        formula = "wire_length = 2 * (base + side)"
        source_shape, target_shape = "parallelogram_wire", ""
    elif str(query_id) == QUERY_ID_CIRCLE_WIRE_LENGTH_FROM_AREA:
        radius = int(case)
        area = _PI_APPROX * radius * radius
        answer = _circle_circumference_from_radius(radius)
        source_values = {"radius": radius, "area": area, "pi": _PI_APPROX, "wire_length": answer}
        target_values = {}
        formula = "wire_length = 2 * pi * radius, with radius from area = pi * r^2"
        source_shape, target_shape = "circle_wire", ""
    elif str(query_id) == QUERY_ID_TRAPEZOID_WIRE_TO_CUBE_FRAME:
        top, bottom, side = [int(value) for value in case]
        wire_length = _trapezoid_perimeter(top, bottom, side)
        if wire_length % 12 != 0:
            raise ValueError("trapezoid-to-cube frame cases must have perimeter divisible by 12")
        answer = wire_length // 12
        source_values = {"top": top, "bottom": bottom, "side": side, "wire_length": wire_length}
        target_values = {"edge": answer, "frame_edge_count": 12, "wire_length": wire_length}
        formula = "cube_edge = source_wire_length / 12"
        source_shape, target_shape = "isosceles_trapezoid_wire", "cube_frame"
    elif str(query_id) == QUERY_ID_PARALLELOGRAM_WIRE_TO_CUBOID_FRAME:
        base, side, length, width = [int(value) for value in case]
        wire_length = _parallelogram_perimeter(base, side)
        answer = wire_length // 4 - int(length) - int(width)
        if 4 * (int(length) + int(width) + int(answer)) != wire_length or answer <= 0:
            raise ValueError("parallelogram-to-cuboid frame case must yield positive missing edge")
        source_values = {"base": base, "side": side, "wire_length": wire_length}
        target_values = {"length": length, "width": width, "height": answer, "wire_length": wire_length}
        formula = "cuboid_height = source_wire_length / 4 - length - width"
        source_shape, target_shape = "parallelogram_wire", "cuboid_frame"
    elif str(query_id) == QUERY_ID_SAME_WIRE_CIRCLE_TO_TRAPEZOID_SIDE:
        radius, top, bottom = [int(value) for value in case]
        wire_length = _circle_circumference_from_radius(radius)
        answer = (wire_length - int(top) - int(bottom)) // 2
        if int(top) + int(bottom) + 2 * answer != wire_length or answer <= 0:
            raise ValueError("circle-to-trapezoid cases must yield a positive equal side")
        source_values = {"radius": radius, "wire_length": wire_length, "pi": _PI_APPROX}
        target_values = {"top": top, "bottom": bottom, "side": answer}
        formula = "trapezoid_side = (source_circle_wire_length - top_base - bottom_base) / 2"
        source_shape, target_shape = "circle_wire", "isosceles_trapezoid_wire"
    elif str(query_id) == QUERY_ID_SAME_WIRE_POLYGON_TO_RECTANGLE_SIDE:
        top, bottom, known_side = [int(value) for value in case]
        wire_length = _trapezoid_perimeter(top, bottom, known_side)
        answer = wire_length // 2 - int(known_side)
        source_values = {"top": top, "bottom": bottom, "side": known_side, "wire_length": wire_length}
        target_values = {"known_side": known_side, "unknown_side": answer, "wire_length": wire_length}
        formula = "rectangle_unknown_side = source_wire_length / 2 - known_side"
        source_shape, target_shape = "isosceles_trapezoid_wire", "rectangle_wire"
    else:
        raise ValueError(f"unsupported query_id: {query_id}")
    return _ResolvedProblem(
        task_id=str(task_id),
        query_id=str(query_id),
        source_shape=source_shape,
        target_shape=target_shape,
        source_values=dict(source_values),
        target_values=dict(target_values),
        answer=int(answer),
        formula_family="wire_shape_conversion",
        formula=formula,
        query_probabilities={},
        case_probabilities={},
        answer_support_probabilities={},
    )


def _resolve_problem(*, task_id: str, instance_seed: int, params: Mapping[str, Any]) -> _ResolvedProblem:
    query_id, query_probabilities = select_indexed_geometry_query_id(
        params,
        query_ids=geometry_query_ids_for_task(
            str(task_id),
            _QUERY_IDS_BY_TASK_ID,
            context="wire-shape-conversion",
        ),
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        default_means_sample=False,
    )
    case, case_probabilities = _select_case(query_id=str(query_id), instance_seed=int(instance_seed), params=params)
    problem = _resolve_case(str(task_id), str(query_id), case)
    support = sorted({_resolve_case(str(task_id), str(query_id), candidate).answer for candidate in _cases_for_query(str(query_id))})
    return _ResolvedProblem(
        **{
            **problem.__dict__,
            "query_probabilities": dict(query_probabilities),
            "case_probabilities": dict(case_probabilities),
            "answer_support_probabilities": {str(value): 1.0 / float(len(support)) for value in support},
        }
    )


def _line_bbox(p0: Point, p1: Point, *, width: int, height: int, pad: float = 5.0) -> BBox:
    return pad_bbox(
        (
            min(float(p0[0]), float(p1[0])),
            min(float(p0[1]), float(p1[1])),
            max(float(p0[0]), float(p1[0])),
            max(float(p0[1]), float(p1[1])),
        ),
        float(pad),
        width=int(width),
        height=int(height),
    )


def _draw_text(ctx: _RenderContext, text: str, center: Point, *, small: bool = False) -> BBox:
    font = ctx.small_font if small else ctx.font
    bbox = ctx.draw.textbbox((0, 0), str(text), font=font, stroke_width=ctx.label_stroke_width)
    w = float(bbox[2] - bbox[0])
    h = float(bbox[3] - bbox[1])
    x = float(center[0]) - w / 2.0
    y = float(center[1]) - h / 2.0
    draw_text_traced(
        ctx.draw,
        (x, y),
        str(text),
        font=font,
        fill=ctx.label_color,
        stroke_width=ctx.label_stroke_width,
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=False,
    )
    return pad_bbox((x, y, x + w, y + h), 4.0, width=ctx.width, height=ctx.height)


def _draw_value_box(ctx: _RenderContext, text: str, center: Point, *, small: bool = True) -> BBox:
    font = ctx.small_font if small else ctx.font
    bbox = ctx.draw.textbbox((0, 0), str(text), font=font, stroke_width=ctx.label_stroke_width)
    w = float(bbox[2] - bbox[0])
    h = float(bbox[3] - bbox[1])
    x0 = float(center[0]) - w / 2.0 - 9.0
    y0 = float(center[1]) - h / 2.0 - 6.0
    x1 = x0 + w + 18.0
    y1 = y0 + h + 12.0
    ctx.draw.rounded_rectangle((x0, y0, x1, y1), radius=6, fill=(255, 255, 255), outline=ctx.muted_color, width=1)
    draw_text_traced(
        ctx.draw,
        (x0 + 9.0, y0 + 6.0),
        str(text),
        font=font,
        fill=ctx.label_color,
        stroke_width=ctx.label_stroke_width,
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=False,
    )
    return pad_bbox((x0, y0, x1, y1), 3.0, width=ctx.width, height=ctx.height)


def _draw_arrow(ctx: _RenderContext, start: Point, end: Point) -> BBox:
    ctx.draw.line([start, end], fill=ctx.accent_color, width=max(3, ctx.line_width + 1))
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = max(1e-6, (dx * dx + dy * dy) ** 0.5)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    head = 16.0
    wing = 8.0
    p1 = (float(end[0]) - ux * head + px * wing, float(end[1]) - uy * head + py * wing)
    p2 = (float(end[0]) - ux * head - px * wing, float(end[1]) - uy * head - py * wing)
    ctx.draw.polygon([end, p1, p2], fill=ctx.accent_color)
    return _bbox_union(
        ((start[0], start[1], start[0], start[1]), (end[0], end[1], end[0], end[1]), (p1[0], p1[1], p1[0], p1[1]), (p2[0], p2[1], p2[0], p2[1])),
        width=ctx.width,
        height=ctx.height,
        pad=8.0,
    )


def _draw_trapezoid(ctx: _RenderContext, bbox: BBox, *, fill: Color) -> Tuple[Point, ...]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    inset = (x1 - x0) * 0.22
    points = ((x0 + inset, y0), (x1 - inset, y0), (x1, y1), (x0, y1))
    ctx.draw.polygon(points, fill=fill, outline=ctx.line_color)
    ctx.draw.line([*points, points[0]], fill=ctx.line_color, width=ctx.line_width)
    return points


def _draw_parallelogram(ctx: _RenderContext, bbox: BBox, *, fill: Color) -> Tuple[Point, ...]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    shift = (x1 - x0) * 0.18
    points = ((x0 + shift, y0), (x1, y0), (x1 - shift, y1), (x0, y1))
    ctx.draw.polygon(points, fill=fill, outline=ctx.line_color)
    ctx.draw.line([*points, points[0]], fill=ctx.line_color, width=ctx.line_width)
    return points


def _draw_circle(ctx: _RenderContext, bbox: BBox, *, fill: Color) -> None:
    ctx.draw.ellipse(bbox, fill=fill, outline=ctx.line_color, width=ctx.line_width)


def _draw_rectangle_wire(ctx: _RenderContext, bbox: BBox, *, fill: Color) -> Tuple[Point, ...]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    points = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    ctx.draw.polygon(points, fill=fill, outline=ctx.line_color)
    ctx.draw.line([*points, points[0]], fill=ctx.line_color, width=ctx.line_width)
    return points


def _draw_cube_frame(ctx: _RenderContext, bbox: BBox) -> Tuple[BBox, BBox]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    depth = min(54.0, (x1 - x0) * 0.25)
    front = (x0, y0 + depth * 0.45, x1 - depth, y1)
    back = (front[0] + depth, front[1] - depth * 0.45, front[2] + depth, front[3] - depth * 0.45)
    edges = [
        ((front[0], front[1]), (front[2], front[1])),
        ((front[2], front[1]), (front[2], front[3])),
        ((front[2], front[3]), (front[0], front[3])),
        ((front[0], front[3]), (front[0], front[1])),
        ((back[0], back[1]), (back[2], back[1])),
        ((back[2], back[1]), (back[2], back[3])),
        ((back[2], back[3]), (back[0], back[3])),
        ((back[0], back[3]), (back[0], back[1])),
        ((front[0], front[1]), (back[0], back[1])),
        ((front[2], front[1]), (back[2], back[1])),
        ((front[2], front[3]), (back[2], back[3])),
        ((front[0], front[3]), (back[0], back[3])),
    ]
    for edge in edges:
        ctx.draw.line(edge, fill=ctx.line_color, width=ctx.line_width)
    bottom_edge_bbox = _line_bbox((front[0], front[3]), (front[2], front[3]), width=ctx.width, height=ctx.height, pad=6.0)
    height_edge_bbox = _line_bbox((front[0], front[1]), (front[0], front[3]), width=ctx.width, height=ctx.height, pad=6.0)
    return bottom_edge_bbox, height_edge_bbox


def _draw_source_shape(ctx: _RenderContext, problem: _ResolvedProblem, bbox: BBox) -> Tuple[BBox, Tuple[BBox, ...]]:
    label_boxes = []
    if problem.source_shape == "isosceles_trapezoid_wire":
        _draw_trapezoid(ctx, bbox, fill=ctx.source_fill)
        label_boxes.append(_draw_value_box(ctx, f"top={problem.source_values['top']}", ((bbox[0] + bbox[2]) / 2.0, bbox[1] - 18.0)))
        label_boxes.append(_draw_value_box(ctx, f"bottom={problem.source_values['bottom']}", ((bbox[0] + bbox[2]) / 2.0, bbox[3] + 28.0)))
        label_boxes.append(_draw_value_box(ctx, f"side={problem.source_values['side']}", (bbox[2] + 50.0, (bbox[1] + bbox[3]) / 2.0)))
    elif problem.source_shape == "parallelogram_wire":
        _draw_parallelogram(ctx, bbox, fill=ctx.source_fill)
        label_boxes.append(_draw_value_box(ctx, f"base={problem.source_values['base']}", ((bbox[0] + bbox[2]) / 2.0, bbox[3] + 28.0)))
        label_boxes.append(_draw_value_box(ctx, f"side={problem.source_values['side']}", (bbox[0] - 48.0, (bbox[1] + bbox[3]) / 2.0)))
    elif problem.source_shape == "circle_wire":
        _draw_circle(ctx, bbox, fill=ctx.source_fill)
        if "area" in problem.source_values:
            label_boxes.append(_draw_value_box(ctx, f"area={problem.source_values['area']}", ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0), small=False))
        else:
            label_boxes.append(_draw_value_box(ctx, f"r={problem.source_values['radius']}", ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0), small=False))
        label_boxes.append(_draw_value_box(ctx, f"pi={_PI_APPROX}", ((bbox[0] + bbox[2]) / 2.0, bbox[3] + 30.0)))
    else:
        raise ValueError(f"unsupported source shape: {problem.source_shape}")
    return pad_bbox(bbox, 8.0, width=ctx.width, height=ctx.height), tuple(label_boxes)


def _draw_target_shape(ctx: _RenderContext, problem: _ResolvedProblem, bbox: BBox) -> Tuple[BBox, Tuple[BBox, ...], BBox]:
    label_boxes = []
    if problem.target_shape == "cube_frame":
        target_bbox = pad_bbox(bbox, 8.0, width=ctx.width, height=ctx.height)
        edge_bbox, _height_edge_bbox = _draw_cube_frame(ctx, bbox)
        label_boxes.append(_draw_value_box(ctx, "12 equal edges", ((bbox[0] + bbox[2]) / 2.0, bbox[1] - 20.0)))
        unknown_label = _draw_value_box(ctx, "edge=?", ((edge_bbox[0] + edge_bbox[2]) / 2.0, edge_bbox[3] + 22.0))
        unknown_bbox = _bbox_union((edge_bbox, unknown_label), width=ctx.width, height=ctx.height, pad=4.0)
    elif problem.target_shape == "cuboid_frame":
        target_bbox = pad_bbox(bbox, 8.0, width=ctx.width, height=ctx.height)
        _edge_bbox, height_edge_bbox = _draw_cube_frame(ctx, bbox)
        label_boxes.append(_draw_value_box(ctx, f"L={problem.target_values['length']}", ((bbox[0] + bbox[2]) / 2.0, bbox[3] + 28.0)))
        label_boxes.append(_draw_value_box(ctx, f"W={problem.target_values['width']}", (bbox[2] + 48.0, bbox[1] + 45.0)))
        unknown_label = _draw_value_box(ctx, "H=?", (bbox[0] - 36.0, (bbox[1] + bbox[3]) / 2.0))
        unknown_bbox = _bbox_union((height_edge_bbox, unknown_label), width=ctx.width, height=ctx.height, pad=4.0)
    elif problem.target_shape == "isosceles_trapezoid_wire":
        points = _draw_trapezoid(ctx, bbox, fill=ctx.target_fill)
        target_bbox = pad_bbox(bbox, 8.0, width=ctx.width, height=ctx.height)
        label_boxes.append(_draw_value_box(ctx, f"top={problem.target_values['top']}", ((bbox[0] + bbox[2]) / 2.0, bbox[1] - 18.0)))
        label_boxes.append(_draw_value_box(ctx, f"bottom={problem.target_values['bottom']}", ((bbox[0] + bbox[2]) / 2.0, bbox[3] + 28.0)))
        unknown_label = _draw_value_box(ctx, "side=?", (bbox[2] + 50.0, (bbox[1] + bbox[3]) / 2.0))
        unknown_edge = _line_bbox(points[1], points[2], width=ctx.width, height=ctx.height, pad=6.0)
        unknown_bbox = _bbox_union((unknown_edge, unknown_label), width=ctx.width, height=ctx.height, pad=4.0)
    elif problem.target_shape == "rectangle_wire":
        points = _draw_rectangle_wire(ctx, bbox, fill=ctx.target_fill)
        target_bbox = pad_bbox(bbox, 8.0, width=ctx.width, height=ctx.height)
        label_boxes.append(_draw_value_box(ctx, f"side={problem.target_values['known_side']}", (bbox[2] + 48.0, (bbox[1] + bbox[3]) / 2.0)))
        unknown_label = _draw_value_box(ctx, "side=?", ((bbox[0] + bbox[2]) / 2.0, bbox[3] + 28.0))
        unknown_edge = _line_bbox(points[2], points[3], width=ctx.width, height=ctx.height, pad=6.0)
        unknown_bbox = _bbox_union((unknown_edge, unknown_label), width=ctx.width, height=ctx.height, pad=4.0)
    else:
        raise ValueError(f"unsupported target shape: {problem.target_shape}")
    return target_bbox, tuple(label_boxes), unknown_bbox


def _render_scene(ctx: _RenderContext, problem: _ResolvedProblem, *, instance_seed: int) -> _RenderedScene:
    rng = spawn_rng(int(instance_seed), f"{problem.task_id}.render.scene")
    label_bboxes: Dict[str, BBox] = {}
    if str(problem.task_id) == TASK_ID_WIRE_LENGTH:
        panel = (112.0, 92.0, 728.0, 505.0)
        ctx.draw.rounded_rectangle(panel, radius=10, fill=(255, 255, 255), outline=ctx.muted_color, width=1)
        source_bbox = (300.0 + rng.uniform(-12, 12), 200.0, 540.0 + rng.uniform(-12, 12), 390.0)
        if problem.source_shape == "circle_wire":
            source_bbox = (300.0, 175.0, 520.0, 395.0)
        source_shape_bbox, source_label_boxes = _draw_source_shape(ctx, problem, source_bbox)
        label_bboxes["question"] = _draw_value_box(ctx, "wire length ?", (ctx.width / 2.0, 118.0), small=False)
        annotation_bboxes = {
            "wire_shape_bbox": source_shape_bbox,
            "dimension_region_bbox": _bbox_union(source_label_boxes, width=ctx.width, height=ctx.height, pad=5.0),
        }
    else:
        panel = (70.0, 92.0, 785.0, 525.0)
        ctx.draw.rounded_rectangle(panel, radius=10, fill=(255, 255, 255), outline=ctx.muted_color, width=1)
        source_bbox = (130.0 + rng.uniform(-10, 10), 220.0, 345.0 + rng.uniform(-10, 10), 390.0)
        target_bbox = (555.0 + rng.uniform(-10, 10), 205.0, 725.0 + rng.uniform(-10, 10), 415.0)
        if problem.source_shape == "circle_wire":
            source_bbox = (150.0, 195.0, 330.0, 375.0)
        source_shape_bbox, source_label_boxes = _draw_source_shape(ctx, problem, source_bbox)
        target_shape_bbox, target_label_boxes, unknown_bbox = _draw_target_shape(ctx, problem, target_bbox)
        _draw_arrow(ctx, (source_bbox[2] + 38.0, 300.0), (target_bbox[0] - 38.0, 300.0))
        label_bboxes["same_wire"] = _draw_text(ctx, "same wire", (ctx.width / 2.0, 260.0), small=True)
        target_key = "target_frame_bbox" if str(problem.task_id) == TASK_ID_FRAME_EDGE_LENGTH else "target_shape_bbox"
        known_key = "target_known_dimension_region_bbox"
        unknown_key = "target_unknown_edge_bbox" if str(problem.task_id) == TASK_ID_FRAME_EDGE_LENGTH else "target_unknown_side_bbox"
        annotation_bboxes = {
            "source_wire_shape_bbox": source_shape_bbox,
            target_key: target_shape_bbox,
            "source_dimension_region_bbox": _bbox_union(source_label_boxes, width=ctx.width, height=ctx.height, pad=5.0),
            known_key: _bbox_union(target_label_boxes, width=ctx.width, height=ctx.height, pad=5.0),
            unknown_key: unknown_bbox,
        }
    scene_entities = (
        {
            "entity_id": "source_wire_shape",
            "entity_type": str(problem.source_shape),
            "values": dict(problem.source_values),
            "wire_length_units": int(problem.source_values["wire_length"]),
        },
        {
            "entity_id": "target_shape",
            "entity_type": str(problem.target_shape),
            "values": dict(problem.target_values),
        },
    )
    render_map = {
        "coord_space": "pixel",
        "query_id": str(problem.query_id),
        "source_shape": str(problem.source_shape),
        "target_shape": str(problem.target_shape),
        "annotation_bboxes": {key: bbox_to_list(value) for key, value in annotation_bboxes.items()},
    }
    return _RenderedScene(
        image=ctx.image,
        annotation_bboxes=annotation_bboxes,
        label_bboxes=label_bboxes,
        scene_entities=scene_entities,
        render_map=render_map,
    )


def _example_bbox_for_key(key: str) -> list[int]:
    examples = {
        "wire_shape_bbox": [300, 200, 540, 390],
        "dimension_region_bbox": [255, 160, 605, 460],
        "source_wire_shape_bbox": [130, 220, 345, 390],
        "target_frame_bbox": [555, 205, 725, 415],
        "target_shape_bbox": [555, 205, 725, 415],
        "source_dimension_region_bbox": [100, 165, 395, 460],
        "target_known_dimension_region_bbox": [535, 410, 765, 490],
        "target_unknown_edge_bbox": [565, 415, 720, 465],
        "target_unknown_side_bbox": [565, 415, 720, 465],
    }
    return list(examples[str(key)])


def _make_prompt_examples(answer: int, annotation_keys: Sequence[str]) -> tuple[str, str]:
    annotation = {str(key): _example_bbox_for_key(str(key)) for key in annotation_keys}
    return dump_prompt_json_examples(annotation=annotation, answer=int(answer))


class _WireShapeConversionBaseTask:
    domain = "geometry"
    task_group = TASK_GROUP
    task_id = TASK_ID_WIRE_LENGTH
    default_dataset_enabled = True
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    supported_queries: Tuple[str, ...] = WIRE_LENGTH_QUERY_IDS

    def _make_render_context(
        self,
        *,
        instance_seed: int,
        params: Mapping[str, Any],
        render_defaults: Mapping[str, Any],
    ) -> _RenderContext:
        width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 860)))
        height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 620)))
        image, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
            instance_seed=int(instance_seed),
            params=params,
            scene_id=SCENE_ID,
            task_group=TASK_GROUP,
            canvas_width=width,
            canvas_height=height,
            require_grid=False,
        )
        fill_palettes: Tuple[Tuple[Color, Color, Color], ...] = (
            ((246, 241, 230), (235, 245, 255), (46, 122, 180)),
            ((238, 247, 236), (255, 242, 229), (177, 93, 48)),
            ((240, 238, 255), (236, 248, 246), (111, 92, 190)),
        )
        palette_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{self.task_id}.palette")
        source_fill, target_fill, accent = fill_palettes[int(palette_index) % len(fill_palettes)]
        font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
        small_font_size = int(params.get("small_label_font_size", group_default(render_defaults, "small_label_font_size", 17)))
        line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 3)))
        return _RenderContext(
            image=image,
            draw=ImageDraw.Draw(image),
            width=width,
            height=height,
            line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
            secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
            label_color=tuple(int(value) for value in diagram_style.label_rgb),
            label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
            source_fill=source_fill,
            target_fill=target_fill,
            accent_color=accent,
            muted_color=tuple(int(value) for value in diagram_style.panel_border_rgb),
            line_width=max(2, line_width),
            label_stroke_width=max(1, int(diagram_style.label_stroke_width_px)),
            font=load_font(max(12, font_size), bold=True),
            small_font=load_font(max(10, small_font_size), bold=True),
            diagram_style_meta=dict(diagram_style_meta),
            background_meta=dict(background_meta),
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
        )
        annotation_keys = _annotation_keys_for_task(str(self.task_id))
        problem = _resolve_problem(task_id=str(self.task_id), instance_seed=int(instance_seed), params=params)
        rendered: _RenderedScene | None = None
        ctx: _RenderContext | None = None
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                render_seed = int(instance_seed) + int(attempt) * 9973
                ctx = self._make_render_context(instance_seed=render_seed, params=params, render_defaults=render_defaults)
                rendered = _render_scene(ctx, problem, instance_seed=render_seed)
                break
            except Exception as exc:
                last_error = exc
                rendered = None
                ctx = None
        if rendered is None or ctx is None:
            raise RuntimeError(f"failed to generate {self.task_id}") from last_error

        image, noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults = required_group_defaults(
            prompt_defaults,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                "annotation_hint",
                "answer_hint_integer",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _make_prompt_examples(problem.answer, annotation_keys)
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(problem.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint_integer"]),
                "json_example": str(prompt_defaults.get("json_example", json_example)),
                "json_example_answer_only": str(prompt_defaults.get("json_example_answer_only", json_example_answer_only)),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        annotation_value = {str(key): bbox_to_list(rendered.annotation_bboxes[str(key)]) for key in annotation_keys}
        projected_annotation = {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(annotation_value),
            "pixel_keyed_bbox_map": dict(annotation_value),
        }
        query_params = {
            "task_id": str(self.task_id),
            "scene_id": SCENE_ID,
            "query_id": str(problem.query_id),
            "query_id_probabilities": dict(problem.query_probabilities),
            "case_probabilities": dict(problem.case_probabilities),
            "answer_support_probabilities": dict(problem.answer_support_probabilities),
            "source_shape": str(problem.source_shape),
            "target_shape": str(problem.target_shape),
            "source_values": dict(problem.source_values),
            "target_values": dict(problem.target_values),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": self.domain,
                "task_group": self.task_group,
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "type": str(problem.formula_family),
                    "source_wire_length": int(problem.source_values["wire_length"]),
                    "annotation_roles": list(annotation_keys),
                },
            },
            "query_spec": {"task_id": str(self.task_id), "scene_id": SCENE_ID, "query_id": str(problem.query_id), "params": dict(query_params)},
            "render_spec": {
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "canvas": {"width": int(image.size[0]), "height": int(image.size[1])},
                "style": {
                    "technical_diagram": dict(ctx.diagram_style_meta),
                    "background": dict(ctx.background_meta),
                    "post_image_noise": dict(noise_meta),
                },
                "prompt": {
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                },
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "formula_family": str(problem.formula_family),
                "formula": str(problem.formula),
                "source_shape": str(problem.source_shape),
                "target_shape": str(problem.target_shape),
                "source_values": dict(problem.source_values),
                "target_values": dict(problem.target_values),
                "answer": int(problem.answer),
                "annotation_roles": list(annotation_keys),
            },
            "witness_symbolic": dict(query_params),
            "projected_annotation": projected_annotation,
        }
        complexity = build_geometry_measurement_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
            visual_scan=0.60,
            measurement_precision=0.62,
            ambiguity=0.46,
            output_burden=normalize_linear(len(annotation_value), min_value=2, max_value=5),
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(problem.answer)),
            annotation_gt=TypedValue(type="keyed_bbox_map", value=dict(annotation_value)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometryWireShapeConversionWireLengthValueTask(_WireShapeConversionBaseTask):
    """Compute the total length of wire around a shown shape."""

    task_id = TASK_ID_WIRE_LENGTH
    supported_queries = WIRE_LENGTH_QUERY_IDS


@register_task
class GeometryWireShapeConversionFrameEdgeLengthValueTask(_WireShapeConversionBaseTask):
    """Compute a frame edge after reshaping a source wire shape into a 3D frame."""

    task_id = TASK_ID_FRAME_EDGE_LENGTH
    supported_queries = FRAME_EDGE_LENGTH_QUERY_IDS


@register_task
class GeometryWireShapeConversionMissingDimensionValueTask(_WireShapeConversionBaseTask):
    """Compute a missing 2D target dimension after reusing the same wire."""

    task_id = TASK_ID_MISSING_DIMENSION
    supported_queries = MISSING_DIMENSION_QUERY_IDS


__all__ = [
    "FRAME_EDGE_ANNOTATION_KEYS",
    "FRAME_EDGE_LENGTH_QUERY_IDS",
    "MISSING_DIMENSION_ANNOTATION_KEYS",
    "MISSING_DIMENSION_QUERY_IDS",
    "PROMPT_BUNDLE_ID",
    "QUERY_ID_CIRCLE_WIRE_LENGTH_FROM_AREA",
    "QUERY_ID_PARALLELOGRAM_WIRE_LENGTH",
    "QUERY_ID_PARALLELOGRAM_WIRE_TO_CUBOID_FRAME",
    "QUERY_ID_SAME_WIRE_CIRCLE_TO_TRAPEZOID_SIDE",
    "QUERY_ID_SAME_WIRE_POLYGON_TO_RECTANGLE_SIDE",
    "QUERY_ID_TRAPEZOID_WIRE_LENGTH",
    "QUERY_ID_TRAPEZOID_WIRE_TO_CUBE_FRAME",
    "SCENE_ID",
    "TASK_GROUP",
    "TASK_ID",
    "TASK_ID_FRAME_EDGE_LENGTH",
    "TASK_ID_MISSING_DIMENSION",
    "TASK_ID_WIRE_LENGTH",
    "WIRE_LENGTH_ANNOTATION_KEYS",
    "WIRE_LENGTH_QUERY_IDS",
    "GeometryWireShapeConversionFrameEdgeLengthValueTask",
    "GeometryWireShapeConversionMissingDimensionValueTask",
    "GeometryWireShapeConversionWireLengthValueTask",
]
