"""Objective-neutral diagram construction for angle-relations tasks."""

from __future__ import annotations

import math

from ...shared.composite_measurement_cases import (
    _RenderContext,
    _angle_annotation_point,
    _bbox_from_points,
    _draw_angle_label,
    _draw_point_labels,
    _draw_polygon,
    _draw_polyline,
    _offset_points,
    _triangle_from_base_angles,
)
from .relations import (
    exterior_angle_value,
    format_angle_expression,
    format_degrees,
    format_linear_expression,
    linear_expression_value,
    supplement_angle_value,
)
from .state import (
    ANGLE_ABC,
    ANGLE_AEF,
    ANGLE_BAC,
    ANGLE_BCD,
    ANGLE_CFE,
    POINT_A,
    POINT_B,
    POINT_C,
    POINT_D,
    AngleRelationCase,
    RenderedAngleRelationScene,
)


def _draw_parallel_arrow_marks(ctx: _RenderContext, segments: tuple[tuple[tuple[float, float], tuple[float, float]], ...]) -> tuple[float, float, float, float]:
    """Draw arrow-style parallel markers on each parallel segment."""

    marker_points: list[tuple[float, float]] = []
    for start, end in segments:
        dx = float(end[0]) - float(start[0])
        dy = float(end[1]) - float(start[1])
        length = max(1e-9, math.hypot(dx, dy))
        ux = dx / length
        uy = dy / length
        nx = -uy
        ny = ux
        center = ((float(start[0]) + float(end[0])) / 2.0, (float(start[1]) + float(end[1])) / 2.0)
        half_len = 20.0
        head_len = 10.0
        head_half_width = 6.0
        tail = (center[0] - ux * half_len, center[1] - uy * half_len)
        tip = (center[0] + ux * half_len, center[1] + uy * half_len)
        head_left = (
            tip[0] - ux * head_len + nx * head_half_width,
            tip[1] - uy * head_len + ny * head_half_width,
        )
        head_right = (
            tip[0] - ux * head_len - nx * head_half_width,
            tip[1] - uy * head_len - ny * head_half_width,
        )
        width = max(2, int(ctx.line_width) - 1)
        _draw_polyline(ctx, [tail, tip], fill=ctx.accent_color, width=width)
        _draw_polyline(ctx, [head_left, tip, head_right], fill=ctx.accent_color, width=width)
        marker_points.extend([tail, tip, head_left, head_right])
    return _bbox_from_points(marker_points, width=ctx.width, height=ctx.height, pad=5.0)


def make_triangle_exterior_case(given_a: int, answer_b: int) -> AngleRelationCase:
    """Construct a reusable triangle exterior-angle scene case."""

    exterior = exterior_angle_value(given_a, answer_b)
    right_interior = 180 - int(exterior)

    def build(ctx: _RenderContext) -> RenderedAngleRelationScene:
        """Render triangle/exterior geometry without choosing task identity."""

        a, b, c = _triangle_from_base_angles(
            left_angle=int(given_a),
            right_angle=int(right_interior),
            canvas_width=float(ctx.width),
            canvas_height=float(ctx.height),
        )
        d = (min(ctx.width - 70.0, c[0] + 95.0), c[1])
        a, b, c, d = _offset_points(ctx, (a, b, c, d))
        _draw_polygon(ctx, [a, b, c])
        _draw_polyline(ctx, [c, d])
        labels = _draw_point_labels(ctx, {"A": a, "B": b, "C": c, "D": d})
        target_arc, target_label = _draw_angle_label(ctx, "?", b, a, c, radius=66.0)
        given_arc, label_a = _draw_angle_label(ctx, format_degrees(given_a), a, c, b, radius=66.0)
        exterior_arc, label_ext = _draw_angle_label(ctx, format_degrees(exterior), c, b, d, radius=72.0)
        annotation_points = {
            ANGLE_ABC: _angle_annotation_point(b, a, c, label_radius=66.0),
            ANGLE_BAC: _angle_annotation_point(a, c, b, label_radius=66.0),
            ANGLE_BCD: _angle_annotation_point(c, b, d, label_radius=72.0),
        }
        return RenderedAngleRelationScene(
            image=ctx.image,
            answer=int(answer_b),
            annotation_bboxes=(target_arc, given_arc, exterior_arc),
            annotation_roles=(ANGLE_ABC, ANGLE_BAC, ANGLE_BCD),
            scene_entities=(
                {"type": "triangle", "points": {"A": a, "B": b, "C": c}},
                {"type": "extension_ray", "points": {"C": c, "D": d}},
            ),
            render_map={
                "point_label_bboxes": labels,
                "angle_arc_bboxes": {ANGLE_ABC: target_arc, ANGLE_BAC: given_arc, ANGLE_BCD: exterior_arc},
                "angle_label_bboxes": {ANGLE_ABC: target_label, ANGLE_BAC: label_a, ANGLE_BCD: label_ext},
            },
            witness={
                "given_angle_A": int(given_a),
                "given_exterior_angle_BCD": int(exterior),
                "answer_angle_ABC": int(answer_b),
            },
            reasoning_steps=2,
            annotation_keyed_points=annotation_points,
        )

    return AngleRelationCase(answer=int(answer_b), build=build)


def make_parallel_supplement_case(given: int) -> AngleRelationCase:
    """Construct a reusable parallel-line supplement scene case."""

    answer = supplement_angle_value(given)

    def build(ctx: _RenderContext) -> RenderedAngleRelationScene:
        """Render parallel-line geometry without choosing task identity."""

        top_l, top_r = (135.0, 170.0), (585.0, 170.0)
        bot_l, bot_r = (105.0, 385.0), (615.0, 385.0)
        x_top = 300.0
        vertical_gap = float(bot_l[1] - top_l[1])
        target_theta = math.radians(float(answer))
        x_bot = x_top + (vertical_gap / max(0.25, math.tan(target_theta)))
        p = (x_top, top_l[1])
        q = (x_bot, bot_l[1])
        top_l, top_r, bot_l, bot_r, p, q = _offset_points(ctx, (top_l, top_r, bot_l, bot_r, p, q))
        _draw_polyline(ctx, [top_l, top_r])
        _draw_polyline(ctx, [bot_l, bot_r])
        _draw_polyline(ctx, [p, q])
        mark_bbox = _draw_parallel_arrow_marks(ctx, ((top_l, top_r), (bot_l, bot_r)))
        labels = _draw_point_labels(ctx, {"A": top_l, "B": top_r, "C": bot_l, "D": bot_r, "E": p, "F": q})
        given_arc, given_bbox = _draw_angle_label(ctx, format_degrees(given), p, top_l, q, radius=64.0)
        target_arc, target_bbox = _draw_angle_label(ctx, "?", q, bot_l, p, radius=64.0)
        annotation_points = {
            ANGLE_CFE: _angle_annotation_point(q, bot_l, p, label_radius=64.0),
            ANGLE_AEF: _angle_annotation_point(p, top_l, q, label_radius=64.0),
        }
        return RenderedAngleRelationScene(
            image=ctx.image,
            answer=int(answer),
            annotation_bboxes=(target_arc, given_arc),
            annotation_roles=(ANGLE_CFE, ANGLE_AEF),
            scene_entities=(
                {"type": "parallel_lines", "segments": {"AB": (top_l, top_r), "CD": (bot_l, bot_r)}},
                {"type": "transversal", "segment": (p, q), "points": {"E": p, "F": q}},
            ),
            render_map={
                "point_label_bboxes": labels,
                "angle_arc_bboxes": {ANGLE_CFE: target_arc, ANGLE_AEF: given_arc},
                "angle_label_bboxes": {ANGLE_CFE: target_bbox, ANGLE_AEF: given_bbox},
                "parallel_marks_bbox": mark_bbox,
            },
            witness={
                "given_angle_AEF": int(given),
                "parallel_lines": ["AB", "CD"],
                "answer_angle_CFE": int(answer),
            },
            reasoning_steps=2,
            annotation_keyed_points=annotation_points,
        )

    return AngleRelationCase(answer=int(answer), build=build)


def make_algebraic_single_extension_case(
    given_angle_a: int,
    x_value: int,
    target_coeff: int,
    target_const: int,
    exterior_coeff: int,
) -> AngleRelationCase:
    """Construct a reusable single-extension algebraic angle case."""

    answer_angle_b = linear_expression_value(target_coeff, target_const, x_value)
    exterior_c = exterior_angle_value(given_angle_a, answer_angle_b)
    exterior_const = int(exterior_c) - (int(exterior_coeff) * int(x_value))
    angle_c = 180 - int(given_angle_a) - int(answer_angle_b)

    def build(ctx: _RenderContext) -> RenderedAngleRelationScene:
        """Render single-extension algebraic geometry for task-owned solving."""

        a, b, c = _triangle_from_base_angles(
            left_angle=int(given_angle_a),
            right_angle=int(angle_c),
            width=380.0,
            canvas_width=float(ctx.width),
            canvas_height=float(ctx.height),
        )
        d = (min(ctx.width - 54.0, c[0] + 92.0), c[1])
        a, b, c, d = _offset_points(ctx, (a, b, c, d))
        _draw_polygon(ctx, [a, b, c])
        _draw_polyline(ctx, [c, d])
        labels = _draw_point_labels(ctx, {"A": a, "B": b, "C": c, "D": d})
        target_expr = format_angle_expression(target_coeff, target_const)
        exterior_expr = format_angle_expression(exterior_coeff, exterior_const)
        target_arc, target_bbox = _draw_angle_label(ctx, target_expr, b, a, c, radius=66.0)
        given_arc, given_bbox = _draw_angle_label(ctx, format_degrees(given_angle_a), a, c, b, radius=64.0)
        exterior_arc, exterior_bbox = _draw_angle_label(ctx, exterior_expr, c, b, d, radius=76.0)
        annotation_points = {POINT_A: a, POINT_B: b, POINT_C: c, POINT_D: d}
        return RenderedAngleRelationScene(
            image=ctx.image,
            answer=int(answer_angle_b),
            annotation_bboxes=(target_arc, given_arc, exterior_arc),
            annotation_roles=(POINT_A, POINT_B, POINT_C, POINT_D),
            scene_entities=(
                {"type": "triangle", "points": {"A": a, "B": b, "C": c}},
                {"type": "extension_ray", "points": {"C": c, "D": d}},
            ),
            render_map={
                "point_label_bboxes": labels,
                "angle_arc_bboxes": {ANGLE_ABC: target_arc, ANGLE_BAC: given_arc, ANGLE_BCD: exterior_arc},
                "angle_label_bboxes": {ANGLE_ABC: target_bbox, ANGLE_BAC: given_bbox, ANGLE_BCD: exterior_bbox},
            },
            witness={
                "equation": "exterior_BCD = angle_BAC + angle_ABC",
                "angle_BAC": int(given_angle_a),
                "x": int(x_value),
                "expression_angle_ABC": format_linear_expression(target_coeff, target_const),
                "expression_exterior_BCD": format_linear_expression(exterior_coeff, exterior_const),
                "answer_angle_ABC": int(answer_angle_b),
            },
            reasoning_steps=3,
            annotation_keyed_points=annotation_points,
        )

    return AngleRelationCase(answer=int(answer_angle_b), build=build)


def make_algebraic_double_extension_case(
    given_angle_a: int,
    x_value: int,
    target_coeff: int,
    target_const: int,
    exterior_coeff: int,
) -> AngleRelationCase:
    """Construct a reusable double-extension algebraic angle case."""

    answer_angle_b = linear_expression_value(target_coeff, target_const, x_value)
    exterior_c = exterior_angle_value(given_angle_a, answer_angle_b)
    exterior_const = int(exterior_c) - (int(exterior_coeff) * int(x_value))
    angle_c = 180 - int(given_angle_a) - int(answer_angle_b)

    def build(ctx: _RenderContext) -> RenderedAngleRelationScene:
        """Render double-extension algebraic geometry for task-owned solving."""

        a, b, c = _triangle_from_base_angles(
            left_angle=int(given_angle_a),
            right_angle=int(angle_c),
            width=380.0,
            canvas_width=float(ctx.width),
            canvas_height=float(ctx.height),
        )
        d = (min(ctx.width - 54.0, c[0] + 92.0), c[1])
        e = (max(54.0, a[0] - 92.0), a[1])
        a, b, c, d, e = _offset_points(ctx, (a, b, c, d, e))
        _draw_polyline(ctx, [e, a])
        _draw_polygon(ctx, [a, b, c])
        _draw_polyline(ctx, [c, d])
        labels = _draw_point_labels(ctx, {"E": e, "A": a, "B": b, "C": c, "D": d})
        target_expr = format_angle_expression(target_coeff, target_const)
        exterior_expr = format_angle_expression(exterior_coeff, exterior_const)
        target_arc, target_bbox = _draw_angle_label(ctx, target_expr, b, a, c, radius=66.0)
        given_arc, given_bbox = _draw_angle_label(ctx, format_degrees(given_angle_a), a, c, b, radius=64.0)
        exterior_c_arc, exterior_c_bbox = _draw_angle_label(ctx, exterior_expr, c, b, d, radius=76.0)
        annotation_points = {POINT_A: a, POINT_B: b, POINT_C: c, POINT_D: d}
        return RenderedAngleRelationScene(
            image=ctx.image,
            answer=int(answer_angle_b),
            annotation_bboxes=(target_arc, given_arc, exterior_c_arc),
            annotation_roles=(POINT_A, POINT_B, POINT_C, POINT_D),
            scene_entities=(
                {"type": "triangle", "points": {"A": a, "B": b, "C": c}},
                {"type": "extension_ray", "points": {"A": a, "E": e}},
                {"type": "extension_ray", "points": {"C": c, "D": d}},
            ),
            render_map={
                "point_label_bboxes": labels,
                "angle_arc_bboxes": {ANGLE_ABC: target_arc, ANGLE_BAC: given_arc, ANGLE_BCD: exterior_c_arc},
                "angle_label_bboxes": {ANGLE_ABC: target_bbox, ANGLE_BAC: given_bbox, ANGLE_BCD: exterior_c_bbox},
            },
            witness={
                "equation": "exterior_BCD = angle_BAC + angle_ABC",
                "angle_BAC": int(given_angle_a),
                "x": int(x_value),
                "expression_angle_ABC": format_linear_expression(target_coeff, target_const),
                "expression_exterior_BCD": format_linear_expression(exterior_coeff, exterior_const),
                "answer_angle_ABC": int(answer_angle_b),
            },
            reasoning_steps=3,
            annotation_keyed_points=annotation_points,
        )

    return AngleRelationCase(answer=int(answer_angle_b), build=build)


__all__ = [
    "make_algebraic_double_extension_case",
    "make_algebraic_single_extension_case",
    "make_parallel_supplement_case",
    "make_triangle_exterior_case",
]
