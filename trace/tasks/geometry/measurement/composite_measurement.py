"""Analytical measurement geometry value tasks.

The render helpers in this module are shared by several public scene grammars:
angle relations, parallel sections, Pythagorean length constructions, triangle
special segments, and rectilinear composite shapes. Public evidence is
image-level bbox evidence over the target cue plus the visible supporting
labels/marks needed for the computation.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font
from ..shared.complexity import (
    build_geometry_task_complexity,
    clamp_unit_interval,
    normalize_linear,
    resolve_geometry_complexity_weights,
)
from ..shared.shape_style import extract_background_anchor_colors, sample_geometry_shape_style
from ..shared.measurement_rendering import (
    clamp_bbox as _clamp_bbox,
    pad_bbox as _pad_bbox,
    bbox_from_points as _bbox_from_points,
)

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_analytical_measurement_v0"

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", TASK_GROUP)

_COMPOSITE_MEASUREMENT_BACKGROUND_DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "styles": {
        "paper_white": {"kind": "solid", "color": [255, 255, 252]},
        "cool_paper": {"kind": "solid", "color": [249, 252, 255]},
        "warm_paper": {"kind": "solid", "color": [255, 252, 246]},
        "mint_paper": {"kind": "solid", "color": [249, 254, 251]},
    },
    "weights": {
        "paper_white": 1.0,
        "cool_paper": 1.0,
        "warm_paper": 1.0,
        "mint_paper": 1.0,
    },
}
_COMPOSITE_MEASUREMENT_NOISE_DEFAULTS: Dict[str, Any] = {
    "apply_prob": 0.5,
    "edit_types": ["blur", "downsample", "jpeg", "noise"],
    "edit_count_range": [1, 1],
    "value_ranges": {
        "blur": {"radius": [0.12, 0.32]},
        "downsample": {"scale": [0.93, 0.98]},
        "jpeg": {"quality": [84, 94]},
        "noise": {"alpha": [0.01, 0.03]},
    },
}


@dataclass(frozen=True)
class _MeasurementCase:
    """One constructively valid composite measurement diagram case."""

    query_id: str
    answer: int
    build: Callable[["_RenderContext"], "_RenderedCompositeScene"]


@dataclass
class _RenderContext:
    """Resolved rendering inputs shared by case builders."""

    rng: Any
    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    line_color: Color
    label_color: Color
    label_stroke_color: Color
    accent_color: Color
    fill_color: Color
    line_width: int
    font: Any
    small_font: Any


@dataclass(frozen=True)
class _RenderedCompositeScene:
    """Rendered image plus task/evidence metadata."""

    image: Image.Image
    answer: int
    question_text: str
    query_id: str
    evidence_bboxes: Tuple[BBox, ...]
    evidence_roles: Tuple[str, ...]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]
    reasoning_steps: int


def _combine_bboxes(bboxes: Sequence[Sequence[float]], *, width: int, height: int, pad: float = 0.0) -> BBox:
    if not bboxes:
        return (0.0, 0.0, 0.0, 0.0)
    return _bbox_from_points(
        [(bbox[0], bbox[1]) for bbox in bboxes] + [(bbox[2], bbox[3]) for bbox in bboxes],
        width=width,
        height=height,
        pad=pad,
    )


def _unit(vector: Point) -> Point:
    dx, dy = float(vector[0]), float(vector[1])
    norm = math.hypot(dx, dy)
    if norm <= 1e-9:
        return (1.0, 0.0)
    return (dx / norm, dy / norm)


def _add(point: Point, vector: Point, scale: float = 1.0) -> Point:
    return (float(point[0]) + (float(vector[0]) * float(scale)), float(point[1]) + (float(vector[1]) * float(scale)))


def _sub(a: Point, b: Point) -> Point:
    return (float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def _mid(a: Point, b: Point) -> Point:
    return ((float(a[0]) + float(b[0])) / 2.0, (float(a[1]) + float(b[1])) / 2.0)


def _perp(vector: Point) -> Point:
    return (-float(vector[1]), float(vector[0]))


def _draw_text(
    ctx: _RenderContext,
    text: str,
    center: Point,
    *,
    font: Any | None = None,
    fill: Color | None = None,
    stroke_width: int = 3,
) -> BBox:
    active_font = font if font is not None else ctx.font
    active_fill = fill if fill is not None else ctx.label_color
    x, y = float(center[0]), float(center[1])
    try:
        ctx.draw.text(
            (x, y),
            str(text),
            anchor="mm",
            font=active_font,
            fill=active_fill,
            stroke_width=max(0, int(stroke_width)),
            stroke_fill=ctx.label_stroke_color,
        )
        bbox = ctx.draw.textbbox(
            (x, y),
            str(text),
            anchor="mm",
            font=active_font,
            stroke_width=max(0, int(stroke_width)),
        )
    except Exception:
        ctx.draw.text((x, y), str(text), font=active_font, fill=active_fill)
        bbox = ctx.draw.textbbox((x, y), str(text), font=active_font)
    return _pad_bbox(bbox, 2.0, width=ctx.width, height=ctx.height)


def _draw_point_labels(ctx: _RenderContext, points: Mapping[str, Point]) -> Dict[str, BBox]:
    bboxes: Dict[str, BBox] = {}
    for label, point in points.items():
        x, y = float(point[0]), float(point[1])
        if y > ctx.height * 0.68:
            offset = (0.0, 22.0)
        elif y < ctx.height * 0.25:
            offset = (0.0, -22.0)
        elif x < ctx.width * 0.28:
            offset = (-22.0, 0.0)
        else:
            offset = (22.0, 0.0)
        bboxes[str(label)] = _draw_text(
            ctx,
            str(label),
            (x + offset[0], y + offset[1]),
            font=ctx.small_font,
            stroke_width=3,
        )
    return bboxes


def _draw_polyline(ctx: _RenderContext, points: Sequence[Point], *, fill: Color | None = None, width: int | None = None) -> BBox:
    line_fill = fill if fill is not None else ctx.line_color
    line_width = int(width if width is not None else ctx.line_width)
    ctx.draw.line([(float(x), float(y)) for x, y in points], fill=line_fill, width=line_width, joint="curve")
    return _bbox_from_points(points, width=ctx.width, height=ctx.height, pad=line_width + 2)


def _draw_polygon(
    ctx: _RenderContext,
    points: Sequence[Point],
    *,
    outline: Color | None = None,
    fill: Color | None = None,
    width: int | None = None,
) -> BBox:
    if fill is not None:
        ctx.draw.polygon([(float(x), float(y)) for x, y in points], fill=fill)
    closed = list(points) + [points[0]]
    return _draw_polyline(ctx, closed, fill=outline, width=width)


def _draw_angle_arc(ctx: _RenderContext, vertex: Point, arm_a: Point, arm_b: Point, *, radius: float = 38.0) -> BBox:
    va = _unit(_sub(arm_a, vertex))
    vb = _unit(_sub(arm_b, vertex))
    angle_a = math.atan2(va[1], va[0])
    angle_b = math.atan2(vb[1], vb[0])
    delta = (angle_b - angle_a + math.pi) % (2.0 * math.pi) - math.pi
    steps = max(8, int(abs(delta) / math.radians(7.5)))
    pts: list[Point] = []
    for idx in range(steps + 1):
        angle = angle_a + (delta * (float(idx) / float(steps)))
        pts.append((float(vertex[0]) + (math.cos(angle) * float(radius)), float(vertex[1]) + (math.sin(angle) * float(radius))))
    _draw_polyline(ctx, pts, fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    return _bbox_from_points(pts, width=ctx.width, height=ctx.height, pad=5.0)


def _angle_label_center(vertex: Point, arm_a: Point, arm_b: Point, *, radius: float = 62.0) -> Point:
    va = _unit(_sub(arm_a, vertex))
    vb = _unit(_sub(arm_b, vertex))
    bisector = _unit((va[0] + vb[0], va[1] + vb[1]))
    if math.hypot(bisector[0], bisector[1]) <= 1e-6:
        bisector = _unit(_perp(va))
    return _add(vertex, bisector, radius)


def _draw_angle_label(
    ctx: _RenderContext,
    text: str,
    vertex: Point,
    arm_a: Point,
    arm_b: Point,
    *,
    radius: float = 62.0,
) -> tuple[BBox, BBox]:
    arc_bbox = _draw_angle_arc(ctx, vertex, arm_a, arm_b, radius=max(28.0, radius - 24.0))
    text_bbox = _draw_text(ctx, str(text), _angle_label_center(vertex, arm_a, arm_b, radius=radius))
    return arc_bbox, text_bbox


def _draw_right_angle_marker(ctx: _RenderContext, vertex: Point, arm_a: Point, arm_b: Point, *, size: float = 26.0) -> BBox:
    va = _unit(_sub(arm_a, vertex))
    vb = _unit(_sub(arm_b, vertex))
    p1 = _add(vertex, va, size)
    p2 = _add(p1, vb, size)
    p3 = _add(vertex, vb, size)
    _draw_polyline(ctx, [p1, p2, p3], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    return _bbox_from_points([p1, p2, p3], width=ctx.width, height=ctx.height, pad=4.0)


def _draw_segment_label(ctx: _RenderContext, text: str, a: Point, b: Point, *, offset: float = 24.0) -> BBox:
    direction = _unit(_sub(b, a))
    normal = _perp(direction)
    center = _add(_mid(a, b), normal, offset)
    return _draw_text(ctx, str(text), center)


def _draw_unknown_segment_label(ctx: _RenderContext, segment_name: str, a: Point, b: Point, *, offset: float = 24.0) -> BBox:
    return _draw_segment_label(ctx, f"{segment_name} = ?", a, b, offset=offset)


def _draw_parallel_marks(ctx: _RenderContext, segments: Sequence[tuple[Point, Point]], *, count: int = 1) -> BBox:
    boxes: list[BBox] = []
    for seg_a, seg_b in segments:
        direction = _unit(_sub(seg_b, seg_a))
        normal = _unit(_perp(direction))
        center = _mid(seg_a, seg_b)
        for offset_idx in range(count):
            along_offset = (float(offset_idx) - ((float(count) - 1.0) / 2.0)) * 12.0
            mark_center = _add(center, direction, along_offset)
            p1 = _add(mark_center, normal, -9.0)
            p2 = _add(mark_center, normal, 9.0)
            _draw_polyline(ctx, [p1, p2], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
            boxes.append(_bbox_from_points([p1, p2], width=ctx.width, height=ctx.height, pad=4.0))
    return _combine_bboxes(boxes, width=ctx.width, height=ctx.height, pad=1.0)


def _draw_equal_ticks(ctx: _RenderContext, segments: Sequence[tuple[Point, Point]], *, count: int = 1) -> BBox:
    return _draw_parallel_marks(ctx, segments, count=count)


def _format_degrees(value: int | str) -> str:
    return f"{value}°"


def _linear_expr_value(coefficient: int, constant: int, x_value: int) -> int:
    return (int(coefficient) * int(x_value)) + int(constant)


def _format_linear_expr(coefficient: int, constant: int) -> str:
    coeff = int(coefficient)
    const = int(constant)
    if coeff == 1:
        body = "x"
    elif coeff == -1:
        body = "-x"
    else:
        body = f"{coeff}x"
    if const > 0:
        return f"{body}+{const}"
    if const < 0:
        return f"{body}{const}"
    return body


def _format_angle_expression(coefficient: int, constant: int) -> str:
    return f"({_format_linear_expr(coefficient, constant)})°"


def _json_ready(value: Any) -> Any:
    """Return a JSON-native copy of geometry metadata."""

    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    return value


def _prompt_examples(evidence_count: int) -> tuple[str, str]:
    bboxes: list[list[int]] = []
    for idx in range(max(1, int(evidence_count))):
        x0 = 36 + (72 * idx)
        y0 = 48 + (22 * idx)
        bboxes.append([x0, y0, x0 + 48, y0 + 24])
    answer = {"answer": 42}
    answer_and_evidence = {"evidence": bboxes, "answer": 42}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def _intersect_rays(origin_a: Point, angle_a_degrees: float, origin_b: Point, angle_b_degrees: float) -> Point:
    ax, ay = float(origin_a[0]), float(origin_a[1])
    bx, by = float(origin_b[0]), float(origin_b[1])
    da = (math.cos(math.radians(angle_a_degrees)), -math.sin(math.radians(angle_a_degrees)))
    db = (math.cos(math.radians(angle_b_degrees)), -math.sin(math.radians(angle_b_degrees)))
    det = (da[0] * (-db[1])) - (da[1] * (-db[0]))
    if abs(det) <= 1e-9:
        return ((ax + bx) / 2.0, min(ay, by) - 180.0)
    rhs = (bx - ax, by - ay)
    t = ((rhs[0] * (-db[1])) - (rhs[1] * (-db[0]))) / det
    return (ax + (t * da[0]), ay + (t * da[1]))


def _triangle_from_base_angles(
    *,
    left_angle: int,
    right_angle: int,
    width: float = 390.0,
    base_y: float = 410.0,
    canvas_width: float = 720.0,
    canvas_height: float = 560.0,
) -> tuple[Point, Point, Point]:
    top_margin = 94.0
    bottom_margin = 54.0
    side_margin = 58.0
    requested_width = float(width)
    max_base_y = max(top_margin + 120.0, float(canvas_height) - bottom_margin)
    max_height = max(120.0, max_base_y - top_margin)

    local_left = (0.0, 0.0)
    local_right = (requested_width, 0.0)
    local_apex = _intersect_rays(local_left, float(left_angle), local_right, 180.0 - float(right_angle))
    local_height = max(1.0, -float(local_apex[1]))
    scale = min(1.0, max_height / local_height)
    fitted_width = requested_width * scale

    local_right = (fitted_width, 0.0)
    local_apex = _intersect_rays(local_left, float(left_angle), local_right, 180.0 - float(right_angle))
    fitted_height = max(1.0, -float(local_apex[1]))
    fitted_base_y = min(max_base_y, max(float(base_y), top_margin + fitted_height))

    local_points = (
        (0.0, fitted_base_y),
        (float(local_apex[0]), fitted_base_y + float(local_apex[1])),
        (fitted_width, fitted_base_y),
    )
    min_x = min(point[0] for point in local_points)
    max_x = max(point[0] for point in local_points)
    desired_center_x = 160.0 + (requested_width / 2.0)
    x_offset = desired_center_x - ((min_x + max_x) / 2.0)
    x_offset = max(side_margin - min_x, min(float(canvas_width) - side_margin - max_x, x_offset))
    return tuple((float(x) + x_offset, float(y)) for x, y in local_points)  # type: ignore[return-value]


def _case_triangle_exterior(given_a: int, answer_b: int) -> _MeasurementCase:
    exterior = int(given_a) + int(answer_b)
    right_interior = 180 - int(exterior)

    def build(ctx: _RenderContext) -> _RenderedCompositeScene:
        a, b, c = _triangle_from_base_angles(
            left_angle=int(given_a),
            right_angle=int(right_interior),
            canvas_width=float(ctx.width),
            canvas_height=float(ctx.height),
        )
        d = (min(ctx.width - 70.0, c[0] + 95.0), c[1])
        _draw_polygon(ctx, [a, b, c])
        _draw_polyline(ctx, [c, d])
        labels = _draw_point_labels(ctx, {"A": a, "B": b, "C": c, "D": d})
        target_arc, target_label = _draw_angle_label(ctx, "?", b, a, c, radius=66.0)
        _, label_a = _draw_angle_label(ctx, _format_degrees(given_a), a, c, b, radius=66.0)
        _, label_ext = _draw_angle_label(ctx, _format_degrees(exterior), c, b, d, radius=72.0)
        evidence = (target_label, label_a, label_ext)
        return _RenderedCompositeScene(
            image=ctx.image,
            answer=int(answer_b),
            question_text='What is the measure of angle "ABC"?',
            query_id="triangle_exterior_angle",
            evidence_bboxes=evidence,
            evidence_roles=("target_angle_ABC", "given_angle_A", "given_exterior_angle_BCD"),
            scene_entities=(
                {"type": "triangle", "points": {"A": a, "B": b, "C": c}},
                {"type": "extension_ray", "points": {"C": c, "D": d}},
            ),
            render_map={"point_label_bboxes": labels, "target_arc_bbox": target_arc},
            witness={"given_angle_A": int(given_a), "given_exterior_angle_BCD": int(exterior), "answer_angle_ABC": int(answer_b)},
            reasoning_steps=2,
        )

    return _MeasurementCase(query_id="triangle_exterior_angle", answer=int(answer_b), build=build)


def _case_parallel_supplement(given: int) -> _MeasurementCase:
    answer = 180 - int(given)

    def build(ctx: _RenderContext) -> _RenderedCompositeScene:
        top_l, top_r = (135.0, 170.0), (585.0, 170.0)
        bot_l, bot_r = (105.0, 385.0), (615.0, 385.0)
        x_top, x_bot = 300.0, 500.0
        p = (x_top, top_l[1])
        q = (x_bot, bot_l[1])
        _draw_polyline(ctx, [top_l, top_r])
        _draw_polyline(ctx, [bot_l, bot_r])
        _draw_polyline(ctx, [p, q])
        mark_bbox = _draw_parallel_marks(ctx, [(top_l, top_r), (bot_l, bot_r)], count=1)
        labels = _draw_point_labels(ctx, {"A": top_l, "B": top_r, "C": bot_l, "D": bot_r, "E": p, "F": q})
        _, given_bbox = _draw_angle_label(ctx, _format_degrees(given), p, top_r, q, radius=64.0)
        target_arc, target_bbox = _draw_angle_label(ctx, "?", q, p, bot_l, radius=64.0)
        evidence = (target_bbox, given_bbox, mark_bbox)
        return _RenderedCompositeScene(
            image=ctx.image,
            answer=int(answer),
            question_text='Lines "AB" and "CD" are parallel. What is the measure of angle "CFE"?',
            query_id="parallel_supplement_angle",
            evidence_bboxes=evidence,
            evidence_roles=("target_angle_CFE", "given_angle_BEF", "parallel_line_marks"),
            scene_entities=(
                {"type": "parallel_lines", "segments": {"AB": (top_l, top_r), "CD": (bot_l, bot_r)}},
                {"type": "transversal", "segment": (p, q)},
            ),
            render_map={"point_label_bboxes": labels, "target_arc_bbox": target_arc},
            witness={"given_angle_BEF": int(given), "parallel_lines": ["AB", "CD"], "answer_angle_CFE": int(answer)},
            reasoning_steps=2,
        )

    return _MeasurementCase(query_id="parallel_supplement_angle", answer=int(answer), build=build)


def _case_algebraic_single_extension(
    given_angle_a: int,
    x_value: int,
    target_coeff: int,
    target_const: int,
    exterior_coeff: int,
) -> _MeasurementCase:
    answer_angle_b = _linear_expr_value(target_coeff, target_const, x_value)
    exterior_c = int(given_angle_a) + int(answer_angle_b)
    exterior_const = int(exterior_c) - (int(exterior_coeff) * int(x_value))
    angle_c = 180 - int(given_angle_a) - int(answer_angle_b)

    def build(ctx: _RenderContext) -> _RenderedCompositeScene:
        a, b, c = _triangle_from_base_angles(
            left_angle=int(given_angle_a),
            right_angle=int(angle_c),
            width=380.0,
            canvas_width=float(ctx.width),
            canvas_height=float(ctx.height),
        )
        d = (min(ctx.width - 54.0, c[0] + 92.0), c[1])
        _draw_polygon(ctx, [a, b, c])
        _draw_polyline(ctx, [c, d])
        labels = _draw_point_labels(ctx, {"A": a, "B": b, "C": c, "D": d})
        target_expr = _format_angle_expression(target_coeff, target_const)
        exterior_expr = _format_angle_expression(exterior_coeff, exterior_const)
        target_arc, target_bbox = _draw_angle_label(ctx, target_expr, b, a, c, radius=66.0)
        _, given_bbox = _draw_angle_label(ctx, _format_degrees(given_angle_a), a, c, b, radius=64.0)
        _, exterior_bbox = _draw_angle_label(ctx, exterior_expr, c, b, d, radius=76.0)
        return _RenderedCompositeScene(
            image=ctx.image,
            answer=int(answer_angle_b),
            question_text='Use angle "BAC" and exterior angle "BCD". Solve for x, then substitute it into the expression at angle "ABC". What is the measure of angle "ABC"?',
            query_id="triangle_single_extension_expression",
            evidence_bboxes=(target_bbox, given_bbox, exterior_bbox),
            evidence_roles=("target_expression_angle_ABC", "given_angle_BAC", "expression_exterior_angle_BCD"),
            scene_entities=(
                {"type": "triangle", "points": {"A": a, "B": b, "C": c}},
                {"type": "extension_ray", "points": {"C": c, "D": d}},
            ),
            render_map={"point_label_bboxes": labels, "target_arc_bbox": target_arc},
            witness={
                "equation": "exterior_BCD = angle_BAC + angle_ABC",
                "angle_BAC": int(given_angle_a),
                "x": int(x_value),
                "expression_angle_ABC": _format_linear_expr(target_coeff, target_const),
                "expression_exterior_BCD": _format_linear_expr(exterior_coeff, exterior_const),
                "answer_angle_ABC": int(answer_angle_b),
            },
            reasoning_steps=3,
        )

    return _MeasurementCase(query_id="triangle_single_extension_expression", answer=int(answer_angle_b), build=build)


def _case_algebraic_double_extension(
    given_angle_a: int,
    x_value: int,
    target_coeff: int,
    target_const: int,
    exterior_coeff: int,
) -> _MeasurementCase:
    answer_angle_b = _linear_expr_value(target_coeff, target_const, x_value)
    exterior_c = int(given_angle_a) + int(answer_angle_b)
    exterior_const = int(exterior_c) - (int(exterior_coeff) * int(x_value))
    angle_c = 180 - int(given_angle_a) - int(answer_angle_b)

    def build(ctx: _RenderContext) -> _RenderedCompositeScene:
        a, b, c = _triangle_from_base_angles(
            left_angle=int(given_angle_a),
            right_angle=int(angle_c),
            width=380.0,
            canvas_width=float(ctx.width),
            canvas_height=float(ctx.height),
        )
        d = (min(ctx.width - 54.0, c[0] + 92.0), c[1])
        e = (max(54.0, a[0] - 92.0), a[1])
        _draw_polyline(ctx, [e, a])
        _draw_polygon(ctx, [a, b, c])
        _draw_polyline(ctx, [c, d])
        labels = _draw_point_labels(ctx, {"E": e, "A": a, "B": b, "C": c, "D": d})
        target_expr = _format_angle_expression(target_coeff, target_const)
        exterior_expr = _format_angle_expression(exterior_coeff, exterior_const)
        target_arc, target_bbox = _draw_angle_label(ctx, target_expr, b, a, c, radius=66.0)
        _, given_bbox = _draw_angle_label(ctx, _format_degrees(given_angle_a), a, c, b, radius=64.0)
        _, exterior_c_bbox = _draw_angle_label(ctx, exterior_expr, c, b, d, radius=76.0)
        return _RenderedCompositeScene(
            image=ctx.image,
            answer=int(answer_angle_b),
            question_text='Use interior angle "BAC" and exterior angle "BCD" in the triangle whose base is extended through "A" and "C". Solve for x, then substitute it into the expression at angle "ABC". What is the measure of angle "ABC"?',
            query_id="triangle_double_extension_expression",
            evidence_bboxes=(target_bbox, given_bbox, exterior_c_bbox),
            evidence_roles=("target_expression_angle_ABC", "given_angle_BAC", "expression_exterior_angle_BCD"),
            scene_entities=(
                {"type": "triangle", "points": {"A": a, "B": b, "C": c}},
                {"type": "extension_ray", "points": {"A": a, "E": e}},
                {"type": "extension_ray", "points": {"C": c, "D": d}},
            ),
            render_map={"point_label_bboxes": labels, "target_arc_bbox": target_arc},
            witness={
                "equation": "exterior_BCD = angle_BAC + angle_ABC",
                "angle_BAC": int(given_angle_a),
                "x": int(x_value),
                "expression_angle_ABC": _format_linear_expr(target_coeff, target_const),
                "expression_exterior_BCD": _format_linear_expr(exterior_coeff, exterior_const),
                "answer_angle_ABC": int(answer_angle_b),
            },
            reasoning_steps=3,
        )

    return _MeasurementCase(query_id="triangle_double_extension_expression", answer=int(answer_angle_b), build=build)


def _case_similarity(ad: int, db: int, ae: int) -> _MeasurementCase:
    ec = int((int(ae) * int(db)) / int(ad))

    def build(ctx: _RenderContext) -> _RenderedCompositeScene:
        a, b, c = (355.0, 105.0), (130.0, 420.0), (585.0, 420.0)
        ratio = float(ad) / float(ad + db)
        d = (a[0] + ((b[0] - a[0]) * ratio), a[1] + ((b[1] - a[1]) * ratio))
        e = (a[0] + ((c[0] - a[0]) * ratio), a[1] + ((c[1] - a[1]) * ratio))
        _draw_polygon(ctx, [a, b, c])
        _draw_polyline(ctx, [d, e])
        mark_bbox = _draw_parallel_marks(ctx, [(d, e), (b, c)], count=1)
        labels = _draw_point_labels(ctx, {"A": a, "B": b, "C": c, "D": d, "E": e})
        ad_bbox = _draw_segment_label(ctx, str(ad), a, d, offset=-24.0)
        db_bbox = _draw_segment_label(ctx, str(db), d, b, offset=-24.0)
        ae_bbox = _draw_segment_label(ctx, str(ae), a, e, offset=24.0)
        target_bbox = _draw_unknown_segment_label(ctx, "EC", e, c, offset=24.0)
        evidence = (target_bbox, ad_bbox, db_bbox, ae_bbox, mark_bbox)
        return _RenderedCompositeScene(
            image=ctx.image,
            answer=int(ec),
            question_text='Segment "DE" is parallel to segment "BC". What is the length of segment "EC"?',
            query_id="similar_triangles_side_length",
            evidence_bboxes=evidence,
            evidence_roles=("target_segment_EC", "length_AD", "length_DB", "length_AE", "parallel_marks_DE_BC"),
            scene_entities=({"type": "nested_similar_triangles", "points": {"A": a, "B": b, "C": c, "D": d, "E": e}},),
            render_map={"point_label_bboxes": labels},
            witness={"AD": int(ad), "DB": int(db), "AE": int(ae), "scale_relation": "AD/AB = AE/AC", "answer_EC": int(ec)},
            reasoning_steps=3,
        )

    return _MeasurementCase(query_id="similar_triangles_side_length", answer=int(ec), build=build)


def _case_parallel_section_cross_length(ad: int, db: int, bc: int) -> _MeasurementCase:
    ab = int(ad) + int(db)
    answer = int((int(bc) * int(ad)) / int(ab))

    def build(ctx: _RenderContext) -> _RenderedCompositeScene:
        a, b, c = (355.0, 105.0), (130.0, 420.0), (585.0, 420.0)
        ratio = float(ad) / float(ab)
        d = (a[0] + ((b[0] - a[0]) * ratio), a[1] + ((b[1] - a[1]) * ratio))
        e = (a[0] + ((c[0] - a[0]) * ratio), a[1] + ((c[1] - a[1]) * ratio))
        _draw_polygon(ctx, [a, b, c])
        _draw_polyline(ctx, [d, e])
        mark_bbox = _draw_parallel_marks(ctx, [(d, e), (b, c)], count=1)
        labels = _draw_point_labels(ctx, {"A": a, "B": b, "C": c, "D": d, "E": e})
        ad_bbox = _draw_segment_label(ctx, str(ad), a, d, offset=-24.0)
        db_bbox = _draw_segment_label(ctx, str(db), d, b, offset=-24.0)
        bc_bbox = _draw_segment_label(ctx, str(bc), b, c, offset=28.0)
        target_bbox = _draw_unknown_segment_label(ctx, "DE", d, e, offset=-24.0)
        return _RenderedCompositeScene(
            image=ctx.image,
            answer=int(answer),
            question_text='What is the length of segment "DE"?',
            query_id="parallel_section_cross_length",
            evidence_bboxes=(target_bbox, ad_bbox, db_bbox, bc_bbox, mark_bbox),
            evidence_roles=("target_segment_DE", "length_AD", "length_DB", "length_BC", "parallel_marks_DE_BC"),
            scene_entities=({"type": "nested_similar_triangles", "points": {"A": a, "B": b, "C": c, "D": d, "E": e}},),
            render_map={"point_label_bboxes": labels},
            witness={"AD": int(ad), "DB": int(db), "AB": int(ab), "BC": int(bc), "scale_relation": "DE/BC = AD/AB", "answer_DE": int(answer)},
            reasoning_steps=3,
        )

    return _MeasurementCase(query_id="parallel_section_cross_length", answer=int(answer), build=build)


def _case_parallel_section_base_length(ad: int, db: int, de: int) -> _MeasurementCase:
    ab = int(ad) + int(db)
    answer = int((int(de) * int(ab)) / int(ad))

    def build(ctx: _RenderContext) -> _RenderedCompositeScene:
        a, b, c = (355.0, 105.0), (130.0, 420.0), (585.0, 420.0)
        ratio = float(ad) / float(ab)
        d = (a[0] + ((b[0] - a[0]) * ratio), a[1] + ((b[1] - a[1]) * ratio))
        e = (a[0] + ((c[0] - a[0]) * ratio), a[1] + ((c[1] - a[1]) * ratio))
        _draw_polygon(ctx, [a, b, c])
        _draw_polyline(ctx, [d, e])
        mark_bbox = _draw_parallel_marks(ctx, [(d, e), (b, c)], count=1)
        labels = _draw_point_labels(ctx, {"A": a, "B": b, "C": c, "D": d, "E": e})
        ad_bbox = _draw_segment_label(ctx, str(ad), a, d, offset=-24.0)
        db_bbox = _draw_segment_label(ctx, str(db), d, b, offset=-24.0)
        de_bbox = _draw_segment_label(ctx, str(de), d, e, offset=-24.0)
        target_bbox = _draw_unknown_segment_label(ctx, "BC", b, c, offset=28.0)
        return _RenderedCompositeScene(
            image=ctx.image,
            answer=int(answer),
            question_text='What is the length of segment "BC"?',
            query_id="parallel_section_base_length",
            evidence_bboxes=(target_bbox, ad_bbox, db_bbox, de_bbox, mark_bbox),
            evidence_roles=("target_segment_BC", "length_AD", "length_DB", "length_DE", "parallel_marks_DE_BC"),
            scene_entities=({"type": "nested_similar_triangles", "points": {"A": a, "B": b, "C": c, "D": d, "E": e}},),
            render_map={"point_label_bboxes": labels},
            witness={"AD": int(ad), "DB": int(db), "AB": int(ab), "DE": int(de), "scale_relation": "DE/BC = AD/AB", "answer_BC": int(answer)},
            reasoning_steps=3,
        )

    return _MeasurementCase(query_id="parallel_section_base_length", answer=int(answer), build=build)


def _case_chained_rectangle_diagonal(left_width: int, height_value: int, left_diagonal: int, right_width: int, target_diagonal: int) -> _MeasurementCase:
    total_width = int(left_width) + int(right_width)
    if (int(left_width) ** 2) + (int(height_value) ** 2) != int(left_diagonal) ** 2:
        raise ValueError("left rectangle dimensions must form a Pythagorean triple")
    if (int(total_width) ** 2) + (int(height_value) ** 2) != int(target_diagonal) ** 2:
        raise ValueError("outer rectangle dimensions must form a Pythagorean triple")

    def build(ctx: _RenderContext) -> _RenderedCompositeScene:
        scale = min(24.0, 420.0 / float(total_width), 280.0 / float(height_value))
        a = (165.0, 405.0)
        e = (a[0] + (float(left_width) * scale), a[1])
        b = (a[0] + (float(total_width) * scale), a[1])
        d = (a[0], a[1] - (float(height_value) * scale))
        f = (e[0], d[1])
        c = (b[0], d[1])
        _draw_polygon(ctx, [a, b, c, d], fill=ctx.fill_color)
        _draw_polygon(ctx, [a, b, c, d])
        _draw_polyline(ctx, [e, f])
        _draw_polyline(ctx, [d, e], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        _draw_polyline(ctx, [d, b], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        labels = _draw_point_labels(ctx, {"A": a, "E": e, "B": b, "C": c, "D": d, "F": f})
        right_bbox = _draw_right_angle_marker(ctx, a, d, b)
        left_bbox = _draw_segment_label(ctx, str(left_width), a, e, offset=25.0)
        left_diagonal_bbox = _draw_segment_label(ctx, str(left_diagonal), d, e, offset=-27.0)
        right_width_bbox = _draw_segment_label(ctx, str(right_width), e, b, offset=25.0)
        target_bbox = _draw_unknown_segment_label(ctx, "DB", d, b, offset=-27.0)
        return _RenderedCompositeScene(
            image=ctx.image,
            answer=int(target_diagonal),
            question_text='In the split rectangle, use diagonal "DE" first to infer the height. What is the length of diagonal "DB"?',
            query_id="chained_rectangle_diagonal_length",
            evidence_bboxes=(target_bbox, left_bbox, left_diagonal_bbox, right_width_bbox, right_bbox),
            evidence_roles=("target_diagonal_DB", "length_AE", "diagonal_DE", "length_EB", "right_angle_A"),
            scene_entities=({"type": "split_rectangle_with_chained_diagonals", "points": {"A": a, "E": e, "B": b, "C": c, "D": d, "F": f}},),
            render_map={"point_label_bboxes": labels},
            witness={
                "AE": int(left_width),
                "DE": int(left_diagonal),
                "derived_AD": int(height_value),
                "EB": int(right_width),
                "AB": int(total_width),
                "answer_DB": int(target_diagonal),
            },
            reasoning_steps=4,
        )

    return _MeasurementCase(query_id="chained_rectangle_diagonal_length", answer=int(target_diagonal), build=build)


def _case_rectangle_triangle_shared_height(rect_width: int, shared_height: int, rect_diagonal: int, triangle_base: int, target_hypotenuse: int) -> _MeasurementCase:
    if (int(rect_width) ** 2) + (int(shared_height) ** 2) != int(rect_diagonal) ** 2:
        raise ValueError("rectangle side and diagonal must form a Pythagorean triple")
    if (int(triangle_base) ** 2) + (int(shared_height) ** 2) != int(target_hypotenuse) ** 2:
        raise ValueError("right triangle side and shared height must form a Pythagorean triple")

    def build(ctx: _RenderContext) -> _RenderedCompositeScene:
        scale = min(22.0, 220.0 / float(rect_width), 250.0 / float(triangle_base), 275.0 / float(shared_height))
        b = (335.0, 410.0)
        a = (b[0] - (float(rect_width) * scale), b[1])
        c = (b[0] + (float(triangle_base) * scale), b[1])
        d = (b[0], b[1] - (float(shared_height) * scale))
        e = (a[0], d[1])
        _draw_polygon(ctx, [a, b, d, e], fill=ctx.fill_color)
        _draw_polygon(ctx, [b, c, d], fill=ctx.fill_color)
        _draw_polygon(ctx, [a, b, d, e])
        _draw_polygon(ctx, [b, c, d])
        _draw_polyline(ctx, [a, d], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        labels = _draw_point_labels(ctx, {"A": a, "B": b, "C": c, "D": d, "E": e})
        right_bbox = _draw_right_angle_marker(ctx, b, a, d)
        ab_bbox = _draw_segment_label(ctx, str(rect_width), a, b, offset=25.0)
        ad_bbox = _draw_segment_label(ctx, str(rect_diagonal), a, d, offset=-27.0)
        bc_bbox = _draw_segment_label(ctx, str(triangle_base), b, c, offset=25.0)
        target_bbox = _draw_unknown_segment_label(ctx, "CD", c, d, offset=-28.0)
        return _RenderedCompositeScene(
            image=ctx.image,
            answer=int(target_hypotenuse),
            question_text='The rectangle and right triangle share segment "BD". Use diagonal "AD" first, then find the length of segment "CD".',
            query_id="rectangle_triangle_shared_height_length",
            evidence_bboxes=(target_bbox, ab_bbox, ad_bbox, bc_bbox, right_bbox),
            evidence_roles=("target_segment_CD", "length_AB", "diagonal_AD", "length_BC", "right_angle_B"),
            scene_entities=({"type": "rectangle_and_triangle_shared_height", "points": {"A": a, "B": b, "C": c, "D": d, "E": e}},),
            render_map={"point_label_bboxes": labels},
            witness={"AB": int(rect_width), "AD": int(rect_diagonal), "derived_BD": int(shared_height), "BC": int(triangle_base), "answer_CD": int(target_hypotenuse)},
            reasoning_steps=4,
        )

    return _MeasurementCase(query_id="rectangle_triangle_shared_height_length", answer=int(target_hypotenuse), build=build)


def _angle_bisector_triangle_points(ab: int, ac: int, bd: int, dc: int) -> tuple[Point, Point, Point, Point]:
    bc = int(bd) + int(dc)
    scale = min(28.0, 420.0 / float(bc), 310.0 / float(max(ab, ac)))
    base_width = float(bc) * scale
    x_from_b = (((float(ab) ** 2) + (float(bc) ** 2) - (float(ac) ** 2)) / (2.0 * float(bc))) * scale
    height_sq = max(64.0, ((float(ab) * scale) ** 2) - (x_from_b**2))
    height = math.sqrt(height_sq)
    left = 360.0 - (base_width / 2.0)
    base_y = 420.0
    b = (left, base_y)
    c = (left + base_width, base_y)
    a = (left + x_from_b, base_y - height)
    d = (left + (float(bd) * scale), base_y)
    return a, b, c, d


def _draw_angle_bisector_marks(ctx: _RenderContext, a: Point, b: Point, d: Point, c: Point) -> BBox:
    first = _draw_angle_arc(ctx, a, b, d, radius=38.0)
    second = _draw_angle_arc(ctx, a, d, c, radius=48.0)
    return _combine_bboxes([first, second], width=ctx.width, height=ctx.height, pad=1.0)


def _case_angle_bisector_split(ab: int, ac: int, bd: int) -> _MeasurementCase:
    dc = (int(bd) * int(ac)) // int(ab)

    def build(ctx: _RenderContext) -> _RenderedCompositeScene:
        a, b, c, d = _angle_bisector_triangle_points(int(ab), int(ac), int(bd), int(dc))
        _draw_polygon(ctx, [a, b, c])
        _draw_polyline(ctx, [a, d], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        labels = _draw_point_labels(ctx, {"A": a, "B": b, "C": c, "D": d})
        bisector_bbox = _draw_angle_bisector_marks(ctx, a, b, d, c)
        ab_bbox = _draw_segment_label(ctx, str(ab), a, b, offset=-27.0)
        ac_bbox = _draw_segment_label(ctx, str(ac), a, c, offset=27.0)
        bd_bbox = _draw_segment_label(ctx, str(bd), b, d, offset=25.0)
        target_bbox = _draw_unknown_segment_label(ctx, "DC", d, c, offset=25.0)
        return _RenderedCompositeScene(
            image=ctx.image,
            answer=int(dc),
            question_text='Segment "AD" bisects angle "BAC". What is the length of segment "DC"?',
            query_id="angle_bisector_split_length",
            evidence_bboxes=(target_bbox, ab_bbox, ac_bbox, bd_bbox, bisector_bbox),
            evidence_roles=("target_segment_DC", "length_AB", "length_AC", "length_BD", "angle_bisector_marks"),
            scene_entities=({"type": "triangle_angle_bisector", "points": {"A": a, "B": b, "C": c, "D": d}},),
            render_map={"point_label_bboxes": labels, "angle_bisector_marks_bbox": bisector_bbox},
            witness={"AB": int(ab), "AC": int(ac), "BD": int(bd), "AD_bisects_angle_BAC": True, "answer_DC": int(dc)},
            reasoning_steps=3,
        )

    return _MeasurementCase(query_id="angle_bisector_split_length", answer=int(dc), build=build)


def _case_angle_bisector_base(ab: int, ac: int, bd: int) -> _MeasurementCase:
    dc = (int(bd) * int(ac)) // int(ab)
    answer = int(bd) + int(dc)

    def build(ctx: _RenderContext) -> _RenderedCompositeScene:
        a, b, c, d = _angle_bisector_triangle_points(int(ab), int(ac), int(bd), int(dc))
        _draw_polygon(ctx, [a, b, c])
        _draw_polyline(ctx, [a, d], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        labels = _draw_point_labels(ctx, {"A": a, "B": b, "C": c, "D": d})
        bisector_bbox = _draw_angle_bisector_marks(ctx, a, b, d, c)
        ab_bbox = _draw_segment_label(ctx, str(ab), a, b, offset=-27.0)
        ac_bbox = _draw_segment_label(ctx, str(ac), a, c, offset=27.0)
        bd_bbox = _draw_segment_label(ctx, str(bd), b, d, offset=25.0)
        target_bbox = _draw_unknown_segment_label(ctx, "BC", b, c, offset=43.0)
        return _RenderedCompositeScene(
            image=ctx.image,
            answer=int(answer),
            question_text='Segment "AD" bisects angle "BAC". What is the full length of segment "BC"?',
            query_id="angle_bisector_base_length",
            evidence_bboxes=(target_bbox, ab_bbox, ac_bbox, bd_bbox, bisector_bbox),
            evidence_roles=("target_segment_BC", "length_AB", "length_AC", "length_BD", "angle_bisector_marks"),
            scene_entities=({"type": "triangle_angle_bisector", "points": {"A": a, "B": b, "C": c, "D": d}},),
            render_map={"point_label_bboxes": labels, "angle_bisector_marks_bbox": bisector_bbox},
            witness={"AB": int(ab), "AC": int(ac), "BD": int(bd), "AD_bisects_angle_BAC": True, "derived_DC": int(dc), "answer_BC": int(answer)},
            reasoning_steps=4,
        )

    return _MeasurementCase(query_id="angle_bisector_base_length", answer=int(answer), build=build)


def _case_centroid_vertex_segment(gd: int) -> _MeasurementCase:
    ag = 2 * int(gd)

    def build(ctx: _RenderContext) -> _RenderedCompositeScene:
        a, b, c = (360.0, 115.0), (145.0, 420.0), (585.0, 420.0)
        d = _mid(b, c)
        g = (a[0] + ((d[0] - a[0]) * (2.0 / 3.0)), a[1] + ((d[1] - a[1]) * (2.0 / 3.0)))
        _draw_polygon(ctx, [a, b, c])
        _draw_polyline(ctx, [a, d], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        ctx.draw.ellipse((g[0] - 5.0, g[1] - 5.0, g[0] + 5.0, g[1] + 5.0), fill=ctx.accent_color)
        labels = _draw_point_labels(ctx, {"A": a, "B": b, "C": c, "D": d, "G": g})
        midpoint_bbox = _draw_equal_ticks(ctx, [(b, d), (d, c)], count=1)
        gd_bbox = _draw_segment_label(ctx, str(gd), g, d, offset=25.0)
        target_bbox = _draw_unknown_segment_label(ctx, "AG", a, g, offset=-25.0)
        return _RenderedCompositeScene(
            image=ctx.image,
            answer=int(ag),
            question_text='Point "G" is the centroid, and "D" is the midpoint of segment "BC". What is the length of segment "AG"?',
            query_id="centroid_vertex_segment_length",
            evidence_bboxes=(target_bbox, gd_bbox, midpoint_bbox),
            evidence_roles=("target_segment_AG", "length_GD", "midpoint_ticks_BD_DC"),
            scene_entities=({"type": "triangle_centroid_median", "points": {"A": a, "B": b, "C": c, "D": d, "G": g}},),
            render_map={"point_label_bboxes": labels},
            witness={"G_is_centroid": True, "D_midpoint_of_BC": True, "GD": int(gd), "answer_AG": int(ag)},
            reasoning_steps=2,
        )

    return _MeasurementCase(query_id="centroid_vertex_segment_length", answer=int(ag), build=build)


def _case_centroid_whole_median(ag: int) -> _MeasurementCase:
    answer = (3 * int(ag)) // 2
    gd = int(ag) // 2

    def build(ctx: _RenderContext) -> _RenderedCompositeScene:
        a, b, c = (360.0, 115.0), (145.0, 420.0), (585.0, 420.0)
        d = _mid(b, c)
        g = (a[0] + ((d[0] - a[0]) * (2.0 / 3.0)), a[1] + ((d[1] - a[1]) * (2.0 / 3.0)))
        _draw_polygon(ctx, [a, b, c])
        _draw_polyline(ctx, [a, d], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        ctx.draw.ellipse((g[0] - 5.0, g[1] - 5.0, g[0] + 5.0, g[1] + 5.0), fill=ctx.accent_color)
        labels = _draw_point_labels(ctx, {"A": a, "B": b, "C": c, "D": d, "G": g})
        midpoint_bbox = _draw_equal_ticks(ctx, [(b, d), (d, c)], count=1)
        ag_bbox = _draw_segment_label(ctx, str(ag), a, g, offset=-25.0)
        target_bbox = _draw_unknown_segment_label(ctx, "AD", a, d, offset=25.0)
        return _RenderedCompositeScene(
            image=ctx.image,
            answer=int(answer),
            question_text='Point "G" is the centroid, and "D" is the midpoint of segment "BC". What is the full length of median "AD"?',
            query_id="centroid_whole_median_length",
            evidence_bboxes=(target_bbox, ag_bbox, midpoint_bbox),
            evidence_roles=("target_median_AD", "length_AG", "midpoint_ticks_BD_DC"),
            scene_entities=({"type": "triangle_centroid_median", "points": {"A": a, "B": b, "C": c, "D": d, "G": g}},),
            render_map={"point_label_bboxes": labels},
            witness={"G_is_centroid": True, "D_midpoint_of_BC": True, "AG": int(ag), "derived_GD": int(gd), "answer_AD": int(answer)},
            reasoning_steps=2,
        )

    return _MeasurementCase(query_id="centroid_whole_median_length", answer=int(answer), build=build)


def _case_rectangle_minus_triangle(width_value: int, height_value: int, cut_base: int, cut_height: int) -> _MeasurementCase:
    answer = (int(width_value) * int(height_value)) - ((int(cut_base) * int(cut_height)) // 2)

    def build(ctx: _RenderContext) -> _RenderedCompositeScene:
        left, top = 150.0, 135.0
        w_px = 390.0
        h_px = 270.0
        rect = [(left, top), (left + w_px, top), (left + w_px, top + h_px), (left, top + h_px)]
        tri = [(left + w_px, top + h_px), (left + w_px - (w_px * cut_base / width_value), top + h_px), (left + w_px, top + h_px - (h_px * cut_height / height_value))]
        _draw_polygon(ctx, rect, fill=ctx.fill_color)
        ctx.draw.polygon([(float(x), float(y)) for x, y in tri], fill=(255, 255, 255))
        _draw_polygon(ctx, rect)
        _draw_polygon(ctx, tri, outline=ctx.accent_color, width=max(2, ctx.line_width - 1))
        region_bbox = _bbox_from_points(rect, width=ctx.width, height=ctx.height, pad=2.0)
        w_bbox = _draw_segment_label(ctx, str(width_value), rect[3], rect[2], offset=26.0)
        h_bbox = _draw_segment_label(ctx, str(height_value), rect[0], rect[3], offset=-26.0)
        cb_bbox = _draw_segment_label(ctx, str(cut_base), tri[1], tri[0], offset=24.0)
        ch_bbox = _draw_segment_label(ctx, str(cut_height), tri[0], tri[2], offset=25.0)
        _draw_text(ctx, "shaded", (left + 175.0, top + 130.0), font=ctx.small_font, fill=ctx.accent_color, stroke_width=2)
        return _RenderedCompositeScene(
            image=ctx.image,
            answer=int(answer),
            question_text="What is the area of the shaded region?",
            query_id="rectangle_minus_triangle_area",
            evidence_bboxes=(region_bbox, w_bbox, h_bbox, cb_bbox, ch_bbox),
            evidence_roles=("target_shaded_region", "outer_width", "outer_height", "cutout_base", "cutout_height"),
            scene_entities=({"type": "rectangle_minus_triangle", "outer": rect, "cutout": tri},),
            render_map={"target_region_bbox": region_bbox},
            witness={"outer_width": int(width_value), "outer_height": int(height_value), "cutout_base": int(cut_base), "cutout_height": int(cut_height), "answer_area": int(answer)},
            reasoning_steps=3,
        )

    return _MeasurementCase(query_id="rectangle_minus_triangle_area", answer=int(answer), build=build)


def _case_l_shape_area(width_value: int, height_value: int, cut_width: int, cut_height: int) -> _MeasurementCase:
    answer = (int(width_value) * int(height_value)) - (int(cut_width) * int(cut_height))

    def build(ctx: _RenderContext) -> _RenderedCompositeScene:
        left, top = 145.0, 125.0
        w_px, h_px = 420.0, 300.0
        cut_w_px = w_px * cut_width / width_value
        cut_h_px = h_px * cut_height / height_value
        pts = [
            (left, top),
            (left + w_px, top),
            (left + w_px, top + h_px - cut_h_px),
            (left + w_px - cut_w_px, top + h_px - cut_h_px),
            (left + w_px - cut_w_px, top + h_px),
            (left, top + h_px),
        ]
        _draw_polygon(ctx, pts, fill=ctx.fill_color)
        _draw_polygon(ctx, pts)
        region_bbox = _bbox_from_points(pts, width=ctx.width, height=ctx.height, pad=2.0)
        w_bbox = _draw_segment_label(ctx, str(width_value), pts[5], pts[4], offset=26.0)
        h_bbox = _draw_segment_label(ctx, str(height_value), pts[0], pts[5], offset=-26.0)
        cw_bbox = _draw_segment_label(ctx, str(cut_width), pts[3], pts[2], offset=-24.0)
        ch_bbox = _draw_segment_label(ctx, str(cut_height), pts[2], (pts[1][0], pts[1][1]), offset=25.0)
        _draw_text(ctx, "shaded", (left + 170.0, top + 130.0), font=ctx.small_font, fill=ctx.accent_color, stroke_width=2)
        return _RenderedCompositeScene(
            image=ctx.image,
            answer=int(answer),
            question_text="What is the area of the shaded region?",
            query_id="l_shape_area",
            evidence_bboxes=(region_bbox, w_bbox, h_bbox, cw_bbox, ch_bbox),
            evidence_roles=("target_shaded_region", "outer_width", "outer_height", "missing_width", "missing_height"),
            scene_entities=({"type": "l_shape", "outline": pts},),
            render_map={"target_region_bbox": region_bbox},
            witness={"outer_width": int(width_value), "outer_height": int(height_value), "missing_width": int(cut_width), "missing_height": int(cut_height), "answer_area": int(answer)},
            reasoning_steps=3,
        )

    return _MeasurementCase(query_id="l_shape_area", answer=int(answer), build=build)


def _case_house_perimeter(width_value: int, wall_height: int, roof_side: int) -> _MeasurementCase:
    answer = int(width_value) + (2 * int(wall_height)) + (2 * int(roof_side))

    def build(ctx: _RenderContext) -> _RenderedCompositeScene:
        scale = 26.0
        w_px = float(width_value) * scale
        half_w = w_px / 2.0
        roof_h = math.sqrt(max(1.0, (float(roof_side) * scale) ** 2 - (half_w ** 2)))
        left, base_y = 165.0, 415.0
        a = (left, base_y)
        b = (left + w_px, base_y)
        c = (left + w_px, base_y - (float(wall_height) * scale))
        d = (left + w_px / 2.0, c[1] - roof_h)
        e = (left, c[1])
        pts = [a, b, c, d, e]
        _draw_polygon(ctx, pts, fill=ctx.fill_color)
        _draw_polygon(ctx, pts)
        labels = _draw_point_labels(ctx, {"A": a, "B": b, "C": c, "D": d, "E": e})
        target_bbox = _bbox_from_points(pts, width=ctx.width, height=ctx.height, pad=4.0)
        base_bbox = _draw_segment_label(ctx, str(width_value), a, b, offset=25.0)
        height_bbox = _draw_segment_label(ctx, str(wall_height), a, e, offset=-25.0)
        roof_bbox = _draw_segment_label(ctx, str(roof_side), d, c, offset=28.0)
        return _RenderedCompositeScene(
            image=ctx.image,
            answer=int(answer),
            question_text='What is the perimeter of the outer boundary of pentagon "ABCDE"?',
            query_id="house_outline_perimeter",
            evidence_bboxes=(target_bbox, base_bbox, height_bbox, roof_bbox),
            evidence_roles=("target_outer_boundary_ABCDE", "base_length_AB", "wall_height_AE", "roof_side_CD"),
            scene_entities=({"type": "house_pentagon", "points": {"A": a, "B": b, "C": c, "D": d, "E": e}},),
            render_map={"point_label_bboxes": labels, "target_boundary_bbox": target_bbox},
            witness={"AB": int(width_value), "AE": int(wall_height), "CD_equals_DE": int(roof_side), "BC_equals_AE": True, "answer_perimeter": int(answer)},
            reasoning_steps=2,
        )

    return _MeasurementCase(query_id="house_outline_perimeter", answer=int(answer), build=build)


def _case_tabbed_perimeter(width_value: int, height_value: int, tab_height: int) -> _MeasurementCase:
    answer = (2 * int(width_value)) + (2 * int(height_value)) + (2 * int(tab_height))

    def build(ctx: _RenderContext) -> _RenderedCompositeScene:
        scale = 25.0
        w_px, h_px, tab_h_px = float(width_value) * scale, float(height_value) * scale, float(tab_height) * scale
        tab_w_px = w_px * 0.42
        left, bottom = 145.0, 420.0
        x0 = left + (w_px - tab_w_px) / 2.0
        x1 = x0 + tab_w_px
        pts = [
            (left, bottom),
            (left + w_px, bottom),
            (left + w_px, bottom - h_px),
            (x1, bottom - h_px),
            (x1, bottom - h_px - tab_h_px),
            (x0, bottom - h_px - tab_h_px),
            (x0, bottom - h_px),
            (left, bottom - h_px),
        ]
        _draw_polygon(ctx, pts, fill=ctx.fill_color)
        _draw_polygon(ctx, pts)
        target_bbox = _bbox_from_points(pts, width=ctx.width, height=ctx.height, pad=4.0)
        width_bbox = _draw_segment_label(ctx, str(width_value), pts[0], pts[1], offset=25.0)
        height_bbox = _draw_segment_label(ctx, str(height_value), pts[0], pts[7], offset=-25.0)
        tab_bbox = _draw_segment_label(ctx, str(tab_height), pts[3], pts[4], offset=26.0)
        return _RenderedCompositeScene(
            image=ctx.image,
            answer=int(answer),
            question_text="What is the perimeter of the outer boundary of the shaded figure?",
            query_id="tabbed_rectilinear_perimeter",
            evidence_bboxes=(target_bbox, width_bbox, height_bbox, tab_bbox),
            evidence_roles=("target_outer_boundary", "overall_width", "main_height", "tab_height"),
            scene_entities=({"type": "tabbed_rectilinear_polygon", "outline": pts},),
            render_map={"target_boundary_bbox": target_bbox},
            witness={"overall_width": int(width_value), "main_height": int(height_value), "tab_height": int(tab_height), "answer_perimeter": int(answer)},
            reasoning_steps=2,
        )

    return _MeasurementCase(query_id="tabbed_rectilinear_perimeter", answer=int(answer), build=build)


_ANGLE_CHAIN_CASES: Tuple[_MeasurementCase, ...] = (
    _case_triangle_exterior(45, 65),
    _case_triangle_exterior(55, 70),
    _case_triangle_exterior(60, 50),
    _case_triangle_exterior(70, 45),
    _case_triangle_exterior(50, 55),
    _case_triangle_exterior(62, 60),
    _case_parallel_supplement(105),
    _case_parallel_supplement(112),
    _case_parallel_supplement(118),
    _case_parallel_supplement(126),
    _case_parallel_supplement(128),
    _case_parallel_supplement(132),
)
_ALGEBRAIC_ANGLE_CASES: Tuple[_MeasurementCase, ...] = (
    _case_algebraic_single_extension(40, 25, 1, 25, 2),
    _case_algebraic_single_extension(45, 22, 1, 30, 2),
    _case_algebraic_single_extension(50, 18, 2, 12, 3),
    _case_algebraic_single_extension(55, 20, 2, 15, 3),
    _case_algebraic_single_extension(35, 24, 1, 34, 2),
    _case_algebraic_single_extension(60, 16, 3, 12, 4),
    _case_algebraic_double_extension(50, 22, 1, 30, 2),
    _case_algebraic_double_extension(60, 20, 1, 35, 2),
    _case_algebraic_double_extension(45, 21, 1, 29, 2),
    _case_algebraic_double_extension(55, 30, 1, 24, 2),
    _case_algebraic_double_extension(48, 28, 1, 28, 2),
    _case_algebraic_double_extension(62, 26, 1, 32, 2),
)
_SIMILARITY_CASES: Tuple[_MeasurementCase, ...] = (
    _case_similarity(2, 3, 2),
    _case_similarity(3, 2, 6),
    _case_similarity(2, 3, 4),
    _case_similarity(3, 4, 9),
    _case_similarity(3, 5, 6),
    _case_similarity(4, 7, 8),
    _case_similarity(4, 5, 12),
    _case_similarity(5, 6, 15),
)
_PARALLEL_SECTION_SCALE_CASES: Tuple[_MeasurementCase, ...] = (
    _case_parallel_section_cross_length(2, 3, 20),
    _case_parallel_section_cross_length(4, 6, 30),
    _case_parallel_section_cross_length(3, 2, 25),
    _case_parallel_section_cross_length(4, 3, 28),
    _case_parallel_section_cross_length(3, 2, 30),
    _case_parallel_section_cross_length(5, 3, 32),
    _case_parallel_section_cross_length(5, 3, 40),
    _case_parallel_section_base_length(2, 3, 8),
    _case_parallel_section_base_length(3, 2, 15),
    _case_parallel_section_base_length(4, 3, 16),
    _case_parallel_section_base_length(4, 6, 12),
    _case_parallel_section_base_length(5, 3, 20),
    _case_parallel_section_base_length(3, 4, 15),
    _case_parallel_section_base_length(5, 7, 20),
)
_PYTHAGOREAN_CASES: Tuple[_MeasurementCase, ...] = (
    _case_chained_rectangle_diagonal(5, 12, 13, 4, 15),
    _case_chained_rectangle_diagonal(5, 12, 13, 11, 20),
    _case_chained_rectangle_diagonal(8, 15, 17, 12, 25),
    _case_chained_rectangle_diagonal(7, 24, 25, 3, 26),
    _case_chained_rectangle_diagonal(15, 20, 25, 6, 29),
    _case_chained_rectangle_diagonal(20, 21, 29, 8, 35),
    _case_rectangle_triangle_shared_height(5, 12, 13, 9, 15),
    _case_rectangle_triangle_shared_height(8, 15, 17, 20, 25),
    _case_rectangle_triangle_shared_height(7, 24, 25, 10, 26),
    _case_rectangle_triangle_shared_height(15, 20, 25, 21, 29),
    _case_rectangle_triangle_shared_height(20, 21, 29, 28, 35),
    _case_rectangle_triangle_shared_height(12, 35, 37, 12, 37),
)
_ANGLE_BISECTOR_SEGMENT_CASES: Tuple[_MeasurementCase, ...] = (
    _case_angle_bisector_split(6, 9, 4),
    _case_angle_bisector_split(8, 12, 6),
    _case_angle_bisector_split(10, 15, 8),
    _case_angle_bisector_split(9, 12, 6),
    _case_angle_bisector_split(12, 18, 10),
    _case_angle_bisector_split(15, 20, 12),
    _case_angle_bisector_base(6, 9, 4),
    _case_angle_bisector_base(8, 12, 6),
    _case_angle_bisector_base(10, 15, 8),
    _case_angle_bisector_base(9, 12, 6),
    _case_angle_bisector_base(12, 18, 10),
    _case_angle_bisector_base(15, 20, 12),
)
_CENTROID_MEDIAN_SEGMENT_CASES: Tuple[_MeasurementCase, ...] = (
    _case_centroid_vertex_segment(4),
    _case_centroid_vertex_segment(5),
    _case_centroid_vertex_segment(6),
    _case_centroid_vertex_segment(7),
    _case_centroid_vertex_segment(8),
    _case_centroid_vertex_segment(9),
    _case_centroid_whole_median(8),
    _case_centroid_whole_median(10),
    _case_centroid_whole_median(12),
    _case_centroid_whole_median(14),
    _case_centroid_whole_median(16),
    _case_centroid_whole_median(18),
)
_COMPOSITE_AREA_CASES: Tuple[_MeasurementCase, ...] = (
    _case_rectangle_minus_triangle(12, 8, 6, 4),
    _case_rectangle_minus_triangle(14, 9, 8, 5),
    _case_rectangle_minus_triangle(13, 10, 4, 5),
    _case_rectangle_minus_triangle(16, 10, 6, 8),
    _case_rectangle_minus_triangle(15, 12, 10, 6),
    _case_l_shape_area(13, 9, 4, 3),
    _case_l_shape_area(12, 10, 4, 3),
    _case_l_shape_area(15, 10, 6, 4),
    _case_l_shape_area(14, 11, 5, 4),
    _case_l_shape_area(16, 12, 6, 5),
)
_COMPOSITE_PERIMETER_CASES: Tuple[_MeasurementCase, ...] = (
    _case_house_perimeter(8, 6, 5),
    _case_house_perimeter(10, 7, 6),
    _case_house_perimeter(12, 8, 7),
    _case_house_perimeter(14, 9, 8),
    _case_house_perimeter(16, 10, 9),
    _case_tabbed_perimeter(10, 6, 2),
    _case_tabbed_perimeter(12, 7, 3),
    _case_tabbed_perimeter(14, 8, 4),
    _case_tabbed_perimeter(16, 9, 5),
    _case_tabbed_perimeter(18, 10, 6),
    _case_tabbed_perimeter(20, 11, 7),
)


def _probability_map(values: Sequence[str]) -> Dict[str, float]:
    if not values:
        return {}
    p = 1.0 / float(len(values))
    return {str(value): float(p) for value in sorted(set(str(item) for item in values))}


class _CompositeMeasurementBaseTask:
    """Shared implementation for one public analytical measurement value task."""

    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    public_scene_id = ""
    scene_id = ""
    scene_kind = "geometry_analytical_measurement"
    witness_type = "analytical_measurement_geometry_value"
    cases: Sequence[_MeasurementCase] = ()
    reasoning_kind = "measurement"

    def _select_case(self, instance_seed: int, params: Mapping[str, Any]) -> tuple[_MeasurementCase, Dict[str, float]]:
        if not self.cases:
            raise ValueError(f"{self.task_id} defines no composite measurement cases")
        by_query: Dict[str, list[_MeasurementCase]] = {}
        for case in self.cases:
            by_query.setdefault(str(case.query_id), []).append(case)
        supported_queries = tuple(sorted(by_query.keys()))
        explicit_query = params.get("query_id", params.get("query_variant"))
        if explicit_query is not None:
            query_id = str(explicit_query)
            if query_id not in by_query:
                raise ValueError(f"unsupported query_id for {self.task_id}: {query_id}")
            query_index = list(supported_queries).index(query_id)
            query_probs = {query_id: 1.0}
        else:
            query_selection_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{self.task_id}.query_id",
            )
            query_index = int(query_selection_index) % len(supported_queries)
            query_id = str(supported_queries[query_index])
            query_probs = _probability_map(supported_queries)

        case_values = by_query[query_id]
        explicit_case = params.get("case_index")
        if explicit_case is not None:
            case_index = int(explicit_case) % len(case_values)
        else:
            raw_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{self.task_id}.{query_id}.case",
            )
            case_index = int(raw_index) % len(case_values)
        return case_values[case_index], query_probs

    def _make_render_context(self, instance_seed: int, params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> tuple[_RenderContext, Dict[str, Any]]:
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.render")
        width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 720)))
        height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 560)))
        image, background_meta = make_background_canvas(
            canvas_width=int(width),
            canvas_height=int(height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=_COMPOSITE_MEASUREMENT_BACKGROUND_DEFAULTS,
            fallback_color=(255, 255, 252),
        )
        anchors = extract_background_anchor_colors(background_meta)
        shape_style = sample_geometry_shape_style(
            rng,
            params=params,
            render_defaults=render_defaults,
            anchor_colors=anchors,
        )
        line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 4)))
        font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
        small_font_size = int(params.get("point_label_font_size", group_default(render_defaults, "point_label_font_size", 18)))
        fill_choices: tuple[Color, ...] = ((222, 235, 255), (230, 244, 231), (255, 236, 214), (242, 230, 255))
        accent_choices: tuple[Color, ...] = ((30, 92, 168), (31, 119, 80), (165, 85, 24), (116, 72, 172))
        color_idx = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{self.task_id}.accent")) % len(fill_choices)
        ctx = _RenderContext(
            rng=rng,
            image=image,
            draw=ImageDraw.Draw(image),
            width=int(width),
            height=int(height),
            line_color=shape_style.line_color,
            label_color=shape_style.label_color,
            label_stroke_color=shape_style.label_stroke_color,
            accent_color=accent_choices[color_idx],
            fill_color=fill_choices[color_idx],
            line_width=max(2, int(line_width)),
            font=load_font(max(12, int(font_size)), bold=True),
            small_font=load_font(max(10, int(small_font_size)), bold=True),
        )
        render_meta = {
            "background_style": dict(background_meta),
            "shape_style": shape_style.to_trace_dict(),
            "line_width": int(ctx.line_width),
            "label_font_size": int(font_size),
            "point_label_font_size": int(small_font_size),
            "accent_color": list(ctx.accent_color),
            "fill_color": list(ctx.fill_color),
        }
        return ctx, render_meta

    def _build_complexity(self, *, rendered: _RenderedCompositeScene, case_count: int) -> TaskComplexity:
        weights = resolve_geometry_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=str(self.task_id))
        reasoning_load = {
            "angle_chain": 0.62,
            "algebraic_angle": 0.74,
            "parallel_section_length": 0.71,
            "similarity": 0.70,
            "parallel_section_scale": 0.72,
            "pythagorean": 0.74,
            "angle_bisector_segment": 0.72,
            "centroid_median_segment": 0.66,
            "composite_area": 0.76,
            "composite_perimeter": 0.66,
        }.get(str(self.reasoning_kind), 0.60)
        evidence_count = len(rendered.evidence_bboxes)
        components = {
            "visual_scan": clamp_unit_interval(normalize_linear(evidence_count, min_value=2.0, max_value=6.0)),
            "measurement_precision": float(reasoning_load),
            "ambiguity": clamp_unit_interval(0.30 + (0.08 * max(0, min(5, case_count - 1)))),
            "output_burden": clamp_unit_interval(normalize_linear(evidence_count, min_value=2.0, max_value=6.0)),
        }
        return build_geometry_task_complexity(weights=weights, components=components)

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        scene_id = str(self.scene_id or self.public_scene_id)
        if not scene_id:
            raise ValueError(f"{self.task_id} defines no public scene_id")
        gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
        )
        del gen_defaults
        case, query_probs = self._select_case(int(instance_seed), params)
        last_error: Exception | None = None
        rendered: _RenderedCompositeScene | None = None
        render_meta: Dict[str, Any] | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                attempt_params = dict(params)
                attempt_params["_render_attempt"] = int(attempt)
                ctx, render_meta = self._make_render_context(
                    int(instance_seed) + int(attempt),
                    attempt_params,
                    render_defaults,
                )
                rendered = case.build(ctx)
                break
            except Exception as exc:
                last_error = exc
                continue
        if rendered is None or render_meta is None:
            raise RuntimeError(f"failed to generate {self.task_id}") from last_error

        image, noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=_COMPOSITE_MEASUREMENT_NOISE_DEFAULTS,
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
                "evidence_hint",
                "answer_hint_integer",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _prompt_examples(len(rendered.evidence_bboxes))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(rendered.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(rendered.question_text),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint_integer"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        evidence_bboxes = [
            [round(float(coord), 3) for coord in bbox]
            for bbox in rendered.evidence_bboxes
        ]
        evidence_points = [
            [
                round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
                round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
            ]
            for bbox in evidence_bboxes
        ]
        rendered_entities = _json_ready(rendered.scene_entities)
        rendered_map = _json_ready(rendered.render_map)
        rendered_witness = _json_ready(rendered.witness)
        answer_gt = TypedValue(type="integer", value=int(rendered.answer))
        evidence_gt = TypedValue(type="bbox_set", value=evidence_bboxes)
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": str(self.scene_kind),
                "scene_id": scene_id,
                "entities": rendered_entities,
                "relations": {
                    "query_variant": "default",
                    "query_id": str(rendered.query_id),
                    "answer_value": int(rendered.answer),
                    "evidence_roles": list(rendered.evidence_roles),
                },
            },
            "query_spec": {
                "scene_id": scene_id,
                "query_variant": "default",
                "query_id": str(rendered.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_id": scene_id,
                    "query_variant": "default",
                    "query_id": str(rendered.query_id),
                    "query_variant_probabilities": dict(query_probs),
                    "variant_probabilities": {"default": 1.0},
                    "case_answer": int(rendered.answer),
                },
            },
            "render_spec": {
                "canvas_size": [int(image.size[0]), int(image.size[1])],
                "coord_space": "pixel",
                "post_image_noise": dict(noise_meta),
                **dict(render_meta),
            },
            "render_map": {
                "coord_space": "pixel",
                **dict(rendered_map),
            },
            "execution_trace": {
                "scene_id": scene_id,
                "query_variant": "default",
                "query_id": str(rendered.query_id),
                "query_variant_probabilities": dict(query_probs),
                "answer_type": "integer",
                "answer_value": int(rendered.answer),
                "evidence_roles": list(rendered.evidence_roles),
                "reasoning_steps": int(rendered.reasoning_steps),
                **dict(rendered_witness),
            },
            "witness_symbolic": {
                "type": str(self.witness_type),
                "scene_id": scene_id,
                "query_variant": "default",
                "query_id": str(rendered.query_id),
                "answer_value": int(rendered.answer),
                "evidence_roles": list(rendered.evidence_roles),
                "source_witness_type": "bbox_set",
                "original_evidence_value": list(rendered.evidence_roles),
                **dict(rendered_witness),
            },
            "projected_evidence": {
                "type": "bbox_set",
                "bbox_set": list(evidence_bboxes),
                "pixel_bbox_set": list(evidence_bboxes),
                "point_set": list(evidence_points),
                "pixel_point_set": list(evidence_points),
            },
        }
        complexity = self._build_complexity(rendered=rendered, case_count=len(tuple(self.cases)))
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant="default",
            scene_id=scene_id,
            query_id=str(rendered.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometryMeasurementAngleChainValueTask(_CompositeMeasurementBaseTask):
    """Infer a missing angle from a short theorem/constraint chain."""

    task_id = "task_geometry__angle_relations__angle_chain_value"
    public_scene_id = "angle_relations"
    scene_id = public_scene_id
    scene_kind = "geometry_angle_relation"
    reasoning_kind = "angle_chain"
    cases = _ANGLE_CHAIN_CASES


@register_task
class GeometryMeasurementAlgebraicAngleValueTask(_CompositeMeasurementBaseTask):
    """Solve a simple angle equation and report the requested angle value."""

    task_id = "task_geometry__angle_relations__algebraic_angle_value"
    public_scene_id = "angle_relations"
    scene_id = public_scene_id
    scene_kind = "geometry_angle_relation"
    reasoning_kind = "algebraic_angle"
    cases = _ALGEBRAIC_ANGLE_CASES


@register_task
class GeometryMeasurementParallelSectionLengthValueTask(_CompositeMeasurementBaseTask):
    """Infer a triangle segment length using similar-triangle/parallel-section relations."""

    task_id = "task_geometry__triangle_relations__parallel_section_length_value"
    public_scene_id = "triangle_relations"
    scene_id = public_scene_id
    scene_kind = "geometry_parallel_section_length"
    reasoning_kind = "parallel_section_length"
    cases = _SIMILARITY_CASES + _PARALLEL_SECTION_SCALE_CASES


@register_task
class GeometryMeasurementPythagoreanLengthValueTask(_CompositeMeasurementBaseTask):
    """Infer a composite right-triangle length from the Pythagorean theorem."""

    task_id = "task_geometry__triangle_relations__pythagorean_length_value"
    public_scene_id = "triangle_relations"
    scene_id = public_scene_id
    scene_kind = "geometry_pythagorean_length"
    reasoning_kind = "pythagorean"
    cases = _PYTHAGOREAN_CASES


@register_task
class GeometryMeasurementAngleBisectorSegmentValueTask(_CompositeMeasurementBaseTask):
    """Infer a triangle segment length from the angle bisector theorem."""

    task_id = "task_geometry__triangle_relations__angle_bisector_segment_value"
    public_scene_id = "triangle_relations"
    scene_id = public_scene_id
    scene_kind = "geometry_triangle_special_segment"
    reasoning_kind = "angle_bisector_segment"
    cases = _ANGLE_BISECTOR_SEGMENT_CASES


@register_task
class GeometryMeasurementCentroidMedianSegmentValueTask(_CompositeMeasurementBaseTask):
    """Infer a median segment length from the centroid theorem."""

    task_id = "task_geometry__triangle_relations__centroid_median_segment_value"
    public_scene_id = "triangle_relations"
    scene_id = public_scene_id
    scene_kind = "geometry_triangle_special_segment"
    reasoning_kind = "centroid_median_segment"
    cases = _CENTROID_MEDIAN_SEGMENT_CASES


@register_task
class GeometryMeasurementCompositeAreaValueTask(_CompositeMeasurementBaseTask):
    """Compute a composite shaded area by subtraction/decomposition."""

    task_id = "task_geometry__composite_shape__composite_area_value"
    public_scene_id = "composite_shape"
    scene_id = public_scene_id
    scene_kind = "geometry_rectilinear_composite_shape"
    reasoning_kind = "composite_area"
    cases = _COMPOSITE_AREA_CASES


@register_task
class GeometryMeasurementCompositePerimeterValueTask(_CompositeMeasurementBaseTask):
    """Compute the outer perimeter of a composite measurement shape."""

    task_id = "task_geometry__composite_shape__composite_perimeter_value"
    public_scene_id = "composite_shape"
    scene_id = public_scene_id
    scene_kind = "geometry_rectilinear_composite_shape"
    reasoning_kind = "composite_perimeter"
    cases = _COMPOSITE_PERIMETER_CASES
