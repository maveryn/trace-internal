"""Triangle-congruence correspondence measurement-transfer tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.core.seed import spawn_rng
from trace.core.scene_config import get_scene_defaults

from trace.core.visual.noise import apply_post_image_noise


from trace.tasks.shared.config_defaults import (
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)

SCENE_ID = "triangle_congruence_correspondence"
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from trace.tasks.shared.prompt_json_example import build_keyed_point_prompt_json_examples
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font
from trace.tasks.geometry.shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.shared.fixed_query import geometry_selected_probability_map as _probability_map
from trace.tasks.geometry.shared.measurement_rendering import bbox_from_points, pad_bbox
from trace.tasks.geometry.shared.metadata_serialization import geometry_json_ready as _json_ready
from trace.tasks.geometry.shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from trace.tasks.geometry.shared.vector2d import add_scaled as _add, mid as _mid, point_to_list as _point_to_list, sub as _sub, unit as _unit

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]
Side = Tuple[int, int]

PROMPT_BUNDLE_ID = "geometry_triangle_congruence_correspondence_v0"
SIDE_OBJECTIVE = "corresponding_side_value"
ANGLE_OBJECTIVE = "corresponding_angle_value"
ALGEBRAIC_SIDE_OBJECTIVE = "algebraic_side_value"

_SCENE_DEFAULTS = get_scene_defaults("geometry", "triangle_congruence_correspondence")

SIDE_QUERY_IDS: Tuple[str, ...] = (
    "tick_mark_side_transfer",
    "congruence_statement_side_transfer",
    "overlapping_triangle_side_transfer",
)
ANGLE_QUERY_IDS: Tuple[str, ...] = (
    "angle_mark_transfer",
    "congruence_statement_angle_transfer",
    "overlapping_triangle_angle_transfer",
)
ALGEBRAIC_SIDE_QUERY_IDS: Tuple[str, ...] = (
    "single_expression_equal_sides",
    "two_expression_equal_sides",
    "shared_side_congruence_expression",
)


@dataclass(frozen=True)
class _Case:
    query_id: str
    layout_kind: str
    answer: int
    target_name: str
    relation: str
    source_target_side_value: int | None = None
    target_target_side_value: int | None = None
    source_angle_value: int | None = None
    target_angle_value: int | None = None
    x_value: int | None = None
    source_target_expression: str | None = None
    source_support_expression: str | None = None
    target_support_expression: str | None = None
    target_side: Side = (0, 1)
    source_side: Side = (0, 1)
    support_side: Side = (1, 2)
    target_angle_index: int = 0
    source_angle_index: int = 0
    show_statement: bool = False


@dataclass(frozen=True)
class _ResolvedProblem:
    objective_id: str
    query_id: str
    case: _Case
    query_probabilities: Dict[str, float]
    case_index: int
    layout_seed: int


@dataclass
class _RenderContext:
    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    line_color: Color
    secondary_color: Color
    label_color: Color
    label_stroke_color: Color
    accent_color: Color
    source_fill: Color
    target_fill: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]


@dataclass(frozen=True)
class _TriangleGeometry:
    source_vertices: Tuple[Point, Point, Point]
    target_vertices: Tuple[Point, Point, Point]
    source_labels: Tuple[str, str, str]
    target_labels: Tuple[str, str, str]
    statement: str


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    geometry: _TriangleGeometry
    annotation_points: Dict[str, Point]
    point_label_bboxes: Dict[str, BBox]
    readout_bboxes: Dict[str, BBox]
    construction_bboxes: Dict[str, BBox]
    render_map: Dict[str, Any]


@dataclass(frozen=True)
class TriangleCongruenceArtifact:
    prompt: str
    answer_type: str
    answer_value: Any
    annotation_type: str
    annotation_value: Any
    image: Image.Image
    trace_payload: Dict[str, Any]
    task_versions: Dict[str, str]
    query_id: str
    prompt_variants: Dict[str, Any]


def _side_target_name(layout_kind: str, side: Side) -> str:
    labels = ("D", "C", "B") if str(layout_kind) == "overlap" else ("D", "E", "F")
    return f"segment {labels[int(side[0])]}{labels[int(side[1])]}"


def _angle_target_name(layout_kind: str, index: int) -> str:
    labels = ("D", "C", "B") if str(layout_kind) == "overlap" else ("D", "E", "F")
    return f"angle {labels[int(index)]}"


def _side_case(query_id: str, layout_kind: str, *, value: int, source_side: Side = (0, 1), target_side: Side = (0, 1)) -> _Case:
    target_name = _side_target_name(layout_kind, target_side)
    return _Case(
        query_id=query_id,
        layout_kind=layout_kind,
        answer=int(value),
        target_name=target_name,
        relation="cpctc_corresponding_side_equal",
        source_target_side_value=int(value),
        target_target_side_value=int(value),
        source_side=source_side,
        target_side=target_side,
        support_side=(1, 2),
        show_statement=query_id != "tick_mark_side_transfer",
    )


def _angle_case(query_id: str, layout_kind: str, *, value: int, source_index: int = 0, target_index: int = 0) -> _Case:
    target_name = _angle_target_name(layout_kind, target_index)
    return _Case(
        query_id=query_id,
        layout_kind=layout_kind,
        answer=int(value),
        target_name=target_name,
        relation="cpctc_corresponding_angle_equal",
        source_angle_value=int(value),
        target_angle_value=int(value),
        source_angle_index=int(source_index),
        target_angle_index=int(target_index),
        show_statement=query_id != "angle_mark_transfer",
    )


def _algebra_case(
    query_id: str,
    layout_kind: str,
    *,
    x_value: int,
    answer: int,
    source_target_expression: str,
    source_support_expression: str,
    target_support_expression: str,
    source_side: Side = (0, 1),
    target_side: Side = (0, 1),
    support_side: Side = (1, 2),
) -> _Case:
    return _Case(
        query_id=query_id,
        layout_kind=layout_kind,
        answer=int(answer),
        target_name=_side_target_name(layout_kind, target_side),
        relation="cpctc_algebraic_corresponding_side_equal",
        source_target_side_value=int(answer),
        target_target_side_value=int(answer),
        x_value=int(x_value),
        source_target_expression=str(source_target_expression),
        source_support_expression=str(source_support_expression),
        target_support_expression=str(target_support_expression),
        source_side=source_side,
        target_side=target_side,
        support_side=support_side,
        show_statement=True,
    )


_SIDE_CASES: Tuple[_Case, ...] = (
    _side_case("tick_mark_side_transfer", "separated", value=8),
    _side_case("tick_mark_side_transfer", "separated", value=10),
    _side_case("tick_mark_side_transfer", "separated", value=12),
    _side_case("tick_mark_side_transfer", "separated", value=14),
    _side_case("tick_mark_side_transfer", "separated", value=16),
    _side_case("congruence_statement_side_transfer", "statement", value=9, source_side=(1, 2), target_side=(1, 2)),
    _side_case("congruence_statement_side_transfer", "statement", value=11, source_side=(1, 2), target_side=(1, 2)),
    _side_case("congruence_statement_side_transfer", "statement", value=13, source_side=(1, 2), target_side=(1, 2)),
    _side_case("congruence_statement_side_transfer", "statement", value=15, source_side=(1, 2), target_side=(1, 2)),
    _side_case("congruence_statement_side_transfer", "statement", value=18, source_side=(1, 2), target_side=(1, 2)),
    _side_case("overlapping_triangle_side_transfer", "overlap", value=8),
    _side_case("overlapping_triangle_side_transfer", "overlap", value=10),
    _side_case("overlapping_triangle_side_transfer", "overlap", value=12),
    _side_case("overlapping_triangle_side_transfer", "overlap", value=14),
    _side_case("overlapping_triangle_side_transfer", "overlap", value=16),
)

_ANGLE_CASES: Tuple[_Case, ...] = (
    _angle_case("angle_mark_transfer", "separated", value=35),
    _angle_case("angle_mark_transfer", "separated", value=45),
    _angle_case("angle_mark_transfer", "separated", value=55),
    _angle_case("angle_mark_transfer", "separated", value=65),
    _angle_case("angle_mark_transfer", "separated", value=75),
    _angle_case("congruence_statement_angle_transfer", "statement", value=40, source_index=1, target_index=1),
    _angle_case("congruence_statement_angle_transfer", "statement", value=50, source_index=1, target_index=1),
    _angle_case("congruence_statement_angle_transfer", "statement", value=60, source_index=1, target_index=1),
    _angle_case("congruence_statement_angle_transfer", "statement", value=70, source_index=1, target_index=1),
    _angle_case("congruence_statement_angle_transfer", "statement", value=80, source_index=1, target_index=1),
    _angle_case("overlapping_triangle_angle_transfer", "overlap", value=35),
    _angle_case("overlapping_triangle_angle_transfer", "overlap", value=45),
    _angle_case("overlapping_triangle_angle_transfer", "overlap", value=55),
    _angle_case("overlapping_triangle_angle_transfer", "overlap", value=65),
    _angle_case("overlapping_triangle_angle_transfer", "overlap", value=75),
)

_ALGEBRA_CASES: Tuple[_Case, ...] = (
    _algebra_case("single_expression_equal_sides", "separated", x_value=5, answer=13, source_target_expression="x+8", source_support_expression="x+4", target_support_expression="9"),
    _algebra_case("single_expression_equal_sides", "separated", x_value=6, answer=15, source_target_expression="x+9", source_support_expression="x+5", target_support_expression="11"),
    _algebra_case("single_expression_equal_sides", "separated", x_value=7, answer=17, source_target_expression="x+10", source_support_expression="x+3", target_support_expression="10"),
    _algebra_case("single_expression_equal_sides", "separated", x_value=8, answer=19, source_target_expression="x+11", source_support_expression="x+4", target_support_expression="12"),
    _algebra_case("single_expression_equal_sides", "separated", x_value=9, answer=21, source_target_expression="x+12", source_support_expression="x+6", target_support_expression="15"),
    _algebra_case("two_expression_equal_sides", "statement", x_value=6, answer=14, source_target_expression="x+8", source_support_expression="2x+1", target_support_expression="x+7"),
    _algebra_case("two_expression_equal_sides", "statement", x_value=7, answer=16, source_target_expression="x+9", source_support_expression="2x+3", target_support_expression="x+10"),
    _algebra_case("two_expression_equal_sides", "statement", x_value=8, answer=18, source_target_expression="x+10", source_support_expression="3x-2", target_support_expression="2x+6"),
    _algebra_case("two_expression_equal_sides", "statement", x_value=9, answer=20, source_target_expression="x+11", source_support_expression="2x+5", target_support_expression="x+14"),
    _algebra_case("two_expression_equal_sides", "statement", x_value=10, answer=22, source_target_expression="x+12", source_support_expression="3x-4", target_support_expression="2x+6"),
    _algebra_case("shared_side_congruence_expression", "overlap", x_value=5, answer=12, source_target_expression="x+7", source_support_expression="2x+2", target_support_expression="12"),
    _algebra_case("shared_side_congruence_expression", "overlap", x_value=6, answer=14, source_target_expression="x+8", source_support_expression="2x+3", target_support_expression="15"),
    _algebra_case("shared_side_congruence_expression", "overlap", x_value=7, answer=16, source_target_expression="x+9", source_support_expression="2x+4", target_support_expression="18"),
    _algebra_case("shared_side_congruence_expression", "overlap", x_value=8, answer=18, source_target_expression="x+10", source_support_expression="2x+5", target_support_expression="21"),
    _algebra_case("shared_side_congruence_expression", "overlap", x_value=9, answer=20, source_target_expression="x+11", source_support_expression="2x+6", target_support_expression="24"),
)


_QUERY_IDS_BY_OBJECTIVE: Dict[str, Tuple[str, ...]] = {
    SIDE_OBJECTIVE: SIDE_QUERY_IDS,
    ANGLE_OBJECTIVE: ANGLE_QUERY_IDS,
    ALGEBRAIC_SIDE_OBJECTIVE: ALGEBRAIC_SIDE_QUERY_IDS,
}


def _cases_for_objective(objective_id: str) -> Tuple[_Case, ...]:
    if objective_id == SIDE_OBJECTIVE:
        return _SIDE_CASES
    if objective_id == ANGLE_OBJECTIVE:
        return _ANGLE_CASES
    if objective_id == ALGEBRAIC_SIDE_OBJECTIVE:
        return _ALGEBRA_CASES
    raise ValueError(f"unknown triangle-congruence objective: {objective_id}")


def _offset_from_segment(a: Point, b: Point, distance: float) -> Point:
    ux, uy = _unit(_sub(b, a))
    return (-uy * float(distance), ux * float(distance))


def _draw_text_centered(ctx: _RenderContext, text: str, center: Point, *, small: bool = True) -> BBox:
    font = ctx.small_font if bool(small) else ctx.font
    draw_text_traced(
        ctx.draw,
        (float(center[0]), float(center[1])),
        str(text),
        anchor="mm",
        font=font,
        fill=ctx.label_color,
        stroke_width=max(0, int(ctx.label_stroke_width)),
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=False,
    )
    bbox = ctx.draw.textbbox(
        (float(center[0]), float(center[1])),
        str(text),
        anchor="mm",
        font=font,
        stroke_width=max(0, int(ctx.label_stroke_width)),
    )
    return pad_bbox(bbox, 3.0, width=ctx.width, height=ctx.height)


def _triangle_geometry(case: _Case, *, width: int, height: int, instance_seed: int) -> _TriangleGeometry:
    rng = spawn_rng(int(instance_seed), f"{SCENE_ID}.{case.layout_kind}.layout")
    if case.layout_kind == "overlap":
        cx = float(width) / 2.0 + rng.uniform(-10.0, 10.0)
        cy = float(height) / 2.0 + rng.uniform(-8.0, 8.0)
        half_base = rng.uniform(115.0, 132.0)
        height_span = rng.uniform(145.0, 165.0)
        b = (cx - half_base, cy)
        c = (cx + half_base, cy)
        a = (cx, cy - height_span)
        d = (cx, cy + height_span)
        return _TriangleGeometry(
            source_vertices=(a, b, c),
            target_vertices=(d, c, b),
            source_labels=("A", "B", "C"),
            target_labels=("D", "C", "B"),
            statement="ABC congruent DCB",
        )
    source_center = (float(width) * 0.32 + rng.uniform(-14.0, 12.0), float(height) * 0.54 + rng.uniform(-12.0, 16.0))
    target_center = (float(width) * 0.69 + rng.uniform(-12.0, 14.0), float(height) * 0.54 + rng.uniform(-12.0, 16.0))
    template = ((0.0, -105.0), (-105.0, 80.0), (116.0, 72.0))
    tilt = rng.uniform(-0.05, 0.05)
    source = tuple((source_center[0] + x + (tilt * y), source_center[1] + y) for x, y in template)
    target = tuple((target_center[0] + x - (tilt * y), target_center[1] + y) for x, y in template)
    return _TriangleGeometry(
        source_vertices=source,  # type: ignore[arg-type]
        target_vertices=target,  # type: ignore[arg-type]
        source_labels=("A", "B", "C"),
        target_labels=("D", "E", "F"),
        statement="ABC congruent DEF",
    )


def _draw_polygon(ctx: _RenderContext, points: Sequence[Point], *, fill: Color, outline: Color) -> BBox:
    polygon = [(float(x), float(y)) for x, y in points]
    ctx.draw.polygon(polygon, fill=fill)
    ctx.draw.line(polygon + [polygon[0]], fill=outline, width=ctx.line_width, joint="curve")
    return bbox_from_points(polygon, width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)


def _draw_vertex_labels(ctx: _RenderContext, points: Sequence[Point], labels: Sequence[str], *, offset: float) -> Dict[str, BBox]:
    center = (sum(point[0] for point in points) / float(len(points)), sum(point[1] for point in points) / float(len(points)))
    bboxes: Dict[str, BBox] = {}
    for label, point in zip(labels, points):
        direction = _unit(_sub(point, center))
        bboxes[str(label)] = _draw_text_centered(ctx, str(label), _add(point, direction, offset), small=True)
    return bboxes


def _draw_tick(ctx: _RenderContext, a: Point, b: Point, *, count: int = 1) -> BBox:
    center = _mid(a, b)
    tangent = _unit(_sub(b, a))
    normal = (-tangent[1], tangent[0])
    points: list[Point] = []
    for index in range(int(count)):
        shift = (float(index) - (float(count) - 1.0) / 2.0) * 9.0
        tick_center = _add(center, tangent, shift)
        p0 = _add(tick_center, normal, -9.0)
        p1 = _add(tick_center, normal, 9.0)
        ctx.draw.line((p0, p1), fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        points.extend([p0, p1])
    return bbox_from_points(points, width=ctx.width, height=ctx.height, pad=3.0)


def _draw_side_label(ctx: _RenderContext, points: Sequence[Point], side: Side, text: str, *, offset: float) -> BBox:
    a = points[int(side[0])]
    b = points[int(side[1])]
    center = _add(_mid(a, b), _offset_from_segment(a, b, offset))
    return _draw_text_centered(ctx, str(text), center, small=True)


def _angle_arc_points(vertex: Point, arm_a: Point, arm_b: Point, *, radius: float) -> Tuple[Point, ...]:
    start = math.atan2(float(arm_a[1]) - float(vertex[1]), float(arm_a[0]) - float(vertex[0]))
    end = math.atan2(float(arm_b[1]) - float(vertex[1]), float(arm_b[0]) - float(vertex[0]))
    delta = (end - start) % (2.0 * math.pi)
    if delta > math.pi:
        delta -= 2.0 * math.pi
    steps = 18
    return tuple(
        (
            float(vertex[0]) + (math.cos(start + (delta * index / steps)) * float(radius)),
            float(vertex[1]) + (math.sin(start + (delta * index / steps)) * float(radius)),
        )
        for index in range(steps + 1)
    )


def _draw_angle_arc(ctx: _RenderContext, points: Sequence[Point], *, index: int, label: str, radius: float = 34.0) -> Tuple[BBox, BBox]:
    vertex = points[int(index)]
    arm_a = points[(int(index) - 1) % 3]
    arm_b = points[(int(index) + 1) % 3]
    arc_points = _angle_arc_points(vertex, arm_a, arm_b, radius=radius)
    ctx.draw.line(arc_points, fill=ctx.accent_color, width=max(2, ctx.line_width - 1), joint="curve")
    middle = arc_points[len(arc_points) // 2]
    direction = _unit(_sub(middle, vertex))
    label_bbox = _draw_text_centered(ctx, str(label), _add(vertex, direction, radius + 24.0), small=True)
    return bbox_from_points(arc_points, width=ctx.width, height=ctx.height, pad=3.0), label_bbox


def _angle_annotation(points: Sequence[Point], index: int) -> Tuple[Point, Point, Point]:
    return (
        points[int(index)],
        points[(int(index) - 1) % 3],
        points[(int(index) + 1) % 3],
    )


def _render_problem(problem: _ResolvedProblem, ctx: _RenderContext) -> _RenderedScene:
    case = problem.case
    geometry = _triangle_geometry(case, width=ctx.width, height=ctx.height, instance_seed=problem.layout_seed)
    construction_bboxes: Dict[str, BBox] = {}
    readout_bboxes: Dict[str, BBox] = {}
    point_label_bboxes: Dict[str, BBox] = {}

    if case.layout_kind == "overlap":
        construction_bboxes["target_triangle"] = _draw_polygon(ctx, geometry.target_vertices, fill=ctx.target_fill, outline=ctx.secondary_color)
        construction_bboxes["source_triangle"] = _draw_polygon(ctx, geometry.source_vertices, fill=ctx.source_fill, outline=ctx.line_color)
    else:
        construction_bboxes["source_triangle"] = _draw_polygon(ctx, geometry.source_vertices, fill=ctx.source_fill, outline=ctx.line_color)
        construction_bboxes["target_triangle"] = _draw_polygon(ctx, geometry.target_vertices, fill=ctx.target_fill, outline=ctx.secondary_color)

    point_label_bboxes.update({f"source_{key}": value for key, value in _draw_vertex_labels(ctx, geometry.source_vertices, geometry.source_labels, offset=24.0).items()})
    point_label_bboxes.update({f"target_{key}": value for key, value in _draw_vertex_labels(ctx, geometry.target_vertices, geometry.target_labels, offset=27.0).items()})

    if case.show_statement:
        readout_bboxes["congruence_statement"] = _draw_text_centered(ctx, geometry.statement, (ctx.width / 2.0, 56.0), small=True)

    if problem.objective_id == ANGLE_OBJECTIVE:
        source_arc, source_label = _draw_angle_arc(ctx, geometry.source_vertices, index=case.source_angle_index, label=f"{case.source_angle_value}\N{DEGREE SIGN}")
        target_arc, target_label = _draw_angle_arc(ctx, geometry.target_vertices, index=case.target_angle_index, label="?")
        construction_bboxes["source_angle_arc"] = source_arc
        construction_bboxes["target_angle_arc"] = target_arc
        readout_bboxes["source_angle_label"] = source_label
        readout_bboxes["target_angle_label"] = target_label
    else:
        readout_bboxes["source_target_side_label"] = _draw_side_label(
            ctx,
            geometry.source_vertices,
            case.source_side,
            str(case.source_target_expression if case.source_target_expression is not None else case.source_target_side_value),
            offset=-28.0,
        )
        readout_bboxes["target_target_side_label"] = _draw_side_label(ctx, geometry.target_vertices, case.target_side, "?", offset=32.0)
        construction_bboxes["source_target_side_tick"] = _draw_tick(
            ctx,
            geometry.source_vertices[case.source_side[0]],
            geometry.source_vertices[case.source_side[1]],
            count=1,
        )
        construction_bboxes["target_target_side_tick"] = _draw_tick(
            ctx,
            geometry.target_vertices[case.target_side[0]],
            geometry.target_vertices[case.target_side[1]],
            count=1,
        )
        if problem.objective_id == ALGEBRAIC_SIDE_OBJECTIVE:
            readout_bboxes["source_support_side_label"] = _draw_side_label(ctx, geometry.source_vertices, case.support_side, str(case.source_support_expression), offset=30.0)
            readout_bboxes["target_support_side_label"] = _draw_side_label(ctx, geometry.target_vertices, case.support_side, str(case.target_support_expression), offset=-34.0)
            construction_bboxes["source_support_side_tick"] = _draw_tick(
                ctx,
                geometry.source_vertices[case.support_side[0]],
                geometry.source_vertices[case.support_side[1]],
                count=2,
            )
            construction_bboxes["target_support_side_tick"] = _draw_tick(
                ctx,
                geometry.target_vertices[case.support_side[0]],
                geometry.target_vertices[case.support_side[1]],
                count=2,
            )
        elif case.query_id != "tick_mark_side_transfer":
            construction_bboxes["source_support_side_tick"] = _draw_tick(
                ctx,
                geometry.source_vertices[case.support_side[0]],
                geometry.source_vertices[case.support_side[1]],
                count=2,
            )
            construction_bboxes["target_support_side_tick"] = _draw_tick(
                ctx,
                geometry.target_vertices[case.support_side[0]],
                geometry.target_vertices[case.support_side[1]],
                count=2,
            )

    annotation = {
        **{label: point for label, point in zip(geometry.source_labels, geometry.source_vertices, strict=True)},
        **{label: point for label, point in zip(geometry.target_labels, geometry.target_vertices, strict=True)},
    }
    render_map = {
        "source_vertices": {label: _point_to_list(point) for label, point in zip(geometry.source_labels, geometry.source_vertices)},
        "target_vertices": {label: _point_to_list(point) for label, point in zip(geometry.target_labels, geometry.target_vertices)},
        "point_label_bboxes": _json_ready(point_label_bboxes),
        "readout_bboxes": _json_ready(readout_bboxes),
        "construction_bboxes": _json_ready(construction_bboxes),
    }
    return _RenderedScene(
        image=ctx.image,
        geometry=geometry,
        annotation_points=annotation,
        point_label_bboxes=point_label_bboxes,
        readout_bboxes=readout_bboxes,
        construction_bboxes=construction_bboxes,
        render_map=render_map,
    )


def _select_problem(
    objective_id: str,
    query_ids: Sequence[str],
    instance_seed: int,
    params: Mapping[str, Any],
    *,
    seed_namespace: str,
) -> _ResolvedProblem:
    forced_query = params.get("query_id")
    if forced_query is not None:
        query_id = str(forced_query)
        if query_id not in query_ids:
            raise ValueError(f"query_id={query_id!r} is not supported by {objective_id}")
    else:
        query_rng = spawn_rng(int(instance_seed), f"{seed_namespace}.query_id")
        query_id = query_ids[int(query_rng.randrange(len(query_ids)))]
    cases = tuple(case for case in _cases_for_objective(objective_id) if case.query_id == query_id)
    if not cases:
        raise ValueError(f"no cases for query_id={query_id!r}")
    case_rng = spawn_rng(int(instance_seed), f"{seed_namespace}.{query_id}.case")
    case_index = int(case_rng.randrange(len(cases)))
    return _ResolvedProblem(
        objective_id=str(objective_id),
        query_id=str(query_id),
        case=cases[case_index],
        query_probabilities=_probability_map(query_ids, query_id if forced_query is not None else None),
        case_index=int(case_index),
        layout_seed=int(instance_seed),
    )


def _build_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> _RenderContext:
    width = int(params.get("canvas_width", rendering_defaults.get("canvas_width", 820)))
    height = int(params.get("canvas_height", rendering_defaults.get("canvas_height", 580)))
    background, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=width,
        canvas_height=height,
        allow_dark=False,
        require_grid=False,
    )
    readout_font_family = str(params.get("readout_font_family", rendering_defaults.get("readout_font_family", "roboto")))
    diagram_style_trace = dict(diagram_style_meta)
    diagram_style_trace["readout_font_family"] = readout_font_family
    image = background.convert("RGB")
    return _RenderContext(
        image=image,
        draw=ImageDraw.Draw(image),
        width=width,
        height=height,
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        accent_color=tuple(int(value) for value in diagram_style.accent_rgb),
        source_fill=tuple(int(value) for value in diagram_style.panel_alt_fill_rgb),
        target_fill=tuple(int(value) for value in diagram_style.option_fill_rgb),
        line_width=max(2, int(params.get("line_width", rendering_defaults.get("line_width", 3)))),
        label_stroke_width=max(0, min(1, int(diagram_style.label_stroke_width_px))),
        font=load_font(int(params.get("label_font_size", rendering_defaults.get("label_font_size", 22))), bold=False, font_family=readout_font_family),
        small_font=load_font(int(params.get("small_label_font_size", rendering_defaults.get("small_label_font_size", 18))), bold=False, font_family=readout_font_family),
        diagram_style_meta=diagram_style_trace,
        background_meta=dict(background_meta),
    )


def _make_prompt_examples(annotation_keys: Sequence[str], *, answer: int) -> tuple[str, str]:
    return build_keyed_point_prompt_json_examples(annotation_keys=annotation_keys, answer=int(answer))


def _answer_hint_for_objective(objective_id: str, prompt_defaults: Mapping[str, Any]) -> str:
    if objective_id == ANGLE_OBJECTIVE:
        return str(prompt_defaults["answer_hint_integer_angle"])
    return str(prompt_defaults["answer_hint_integer_length"])

class TriangleCongruenceCorrespondenceRuntime:
    """Scene-local runtime for congruent-triangle correspondence renderings."""

    domain = "geometry"

    def generate_artifact(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
        public_task_id: str,
        objective_id: str,
        task_prompt_key: str,
        query_ids: Sequence[str],
    ) -> TriangleCongruenceArtifact:
        _generation_defaults, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
            _SCENE_DEFAULTS,
            task_id=str(public_task_id),
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                problem = _select_problem(str(objective_id), tuple(query_ids), int(instance_seed) + int(attempt), params, seed_namespace=str(public_task_id))
                ctx = _build_context(instance_seed=int(instance_seed) + int(attempt), params=params, rendering_defaults=rendering_defaults)
                rendered = _render_problem(problem, ctx)
                break
            except Exception as exc:
                last_error = exc
                continue
        else:
            raise RuntimeError(f"failed to generate {public_task_id}") from last_error

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
                "answer_hint_integer_length",
                "answer_hint_integer_angle",
            ),
            context=f"prompt defaults for {public_task_id}",
        )
        annotation_keys = tuple(rendered.annotation_points.keys())
        json_example, json_example_answer_only = _make_prompt_examples(annotation_keys, answer=int(problem.case.answer))
        annotation_key_list = ", ".join(f'"{key}"' for key in annotation_keys)
        annotation_hint = str(prompt_defaults["annotation_hint"]).format(annotation_keys=annotation_key_list)
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(task_prompt_key),
            query_key=str(problem.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "target_name": str(problem.case.target_name),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": _answer_hint_for_objective(str(objective_id), prompt_defaults),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        annotation_value = {key: _point_to_list(point) for key, point in rendered.annotation_points.items()}
        source_vertices_payload = {
            label: _point_to_list(point)
            for label, point in zip(rendered.geometry.source_labels, rendered.geometry.source_vertices)
        }
        target_vertices_payload = {
            label: _point_to_list(point)
            for label, point in zip(rendered.geometry.target_labels, rendered.geometry.target_vertices)
        }
        measurement_payload = {
            "source_target_side_value": problem.case.source_target_side_value,
            "target_target_side_value": problem.case.target_target_side_value,
            "source_angle_value": problem.case.source_angle_value,
            "target_angle_value": problem.case.target_angle_value,
            "x_value": problem.case.x_value,
            "source_target_expression": problem.case.source_target_expression,
            "source_support_expression": problem.case.source_support_expression,
            "target_support_expression": problem.case.target_support_expression,
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "task_id": str(public_task_id),
                "query_id": str(problem.query_id),
                "entities": [
                    {
                        "type": "congruent_triangle_pair",
                        "layout_kind": str(problem.case.layout_kind),
                        "source_vertices": dict(source_vertices_payload),
                        "target_vertices": dict(target_vertices_payload),
                        "congruence_statement": str(rendered.geometry.statement),
                    },
                ],
                "relations": {
                    "type": str(problem.case.relation),
                    "query_id": str(problem.query_id),
                },
            },
            "query_spec": {
                "task_id": str(public_task_id),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "params": {
                    "query_id": str(problem.query_id),
                    "query_id_probabilities": dict(problem.query_probabilities),
                    "case_index": int(problem.case_index),
                },
            },
            "render_spec": {
                "task_id": str(public_task_id),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "canvas": {"width": int(ctx.width), "height": int(ctx.height)},
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
                "task_id": str(public_task_id),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "target_name": str(problem.case.target_name),
                "relation": str(problem.case.relation),
                "answer": int(problem.case.answer),
                "annotation_roles": list(annotation_keys),
                **dict(measurement_payload),
            },
            "witness_symbolic": {
                "task_id": str(public_task_id),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "target_name": str(problem.case.target_name),
                "relation": str(problem.case.relation),
                "answer": int(problem.case.answer),
                **dict(measurement_payload),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_value),
                "pixel_keyed_point_map": dict(annotation_value),
            },
        }
        return TriangleCongruenceArtifact(
            prompt=str(prompt_artifacts.prompt),
            answer_type="integer",
            answer_value=int(problem.case.answer),
            annotation_type="keyed_point_map",
            annotation_value=dict(annotation_value),
            image=image,
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "ALGEBRAIC_SIDE_OBJECTIVE",
    "ALGEBRAIC_SIDE_QUERY_IDS",
    "ANGLE_OBJECTIVE",
    "ANGLE_QUERY_IDS",
    "SCENE_ID",
    "SIDE_OBJECTIVE",
    "SIDE_QUERY_IDS",
    "TriangleCongruenceArtifact",
    "TriangleCongruenceCorrespondenceRuntime",
]
