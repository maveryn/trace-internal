"""Regular-polygon decomposition measurement tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.core.seed import spawn_rng
from trace.core.scene_config import get_scene_defaults
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.shared.config_defaults import required_group_defaults, split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants
from trace.tasks.shared.prompt_json_example import build_keyed_point_prompt_json_examples
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font
from trace.tasks.geometry.shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.geometry.shared.measurement_rendering import bbox_from_points, fmt_measure, pad_bbox, round1
from trace.tasks.geometry.shared.metadata_serialization import geometry_json_ready as _json_ready
from trace.tasks.geometry.shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform
from trace.tasks.geometry.shared.vector2d import add_scaled as _add, mid as _mid, point_to_list as _point_to_list, sub as _sub, unit as _unit


SCENE_ID = "regular_polygon_decomposition"
Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

PROMPT_BUNDLE_ID = "geometry_regular_polygon_decomposition_v0"
PIECE_OBJECTIVE_KEY = "piece_area"
ANGLE_OBJECTIVE_KEY = "central_angle"
PERIMETER_OBJECTIVE_KEY = "perimeter"
SIDE_LENGTH_OBJECTIVE_KEY = "side_length"

_SCENE_DEFAULTS = get_scene_defaults("geometry", "regular_polygon_decomposition")

_PIECE_QUERY_IDS: Tuple[str, ...] = (
    "single_wedge_area_from_total",
    "shaded_wedges_area_from_total",
    "wedge_area_from_side_and_apothem",
)
_ANGLE_QUERY_IDS: Tuple[str, ...] = (
    "single_wedge_central_angle",
    "marked_wedges_central_angle",
)
_PERIMETER_QUERY_IDS: Tuple[str, ...] = (
    "perimeter_from_side_length",
    "perimeter_from_total_area_and_apothem",
)
_SIDE_LENGTH_QUERY_IDS: Tuple[str, ...] = (
    "side_length_from_perimeter",
    "side_length_from_total_area_and_apothem",
    "side_length_from_wedge_area_and_apothem",
)
_N_SUPPORT: Tuple[int, ...] = (5, 6, 8, 9, 10, 12)
_WEDGE_AREA_SUPPORT: Tuple[int, ...] = (8, 10, 12, 15, 18, 20, 24, 30)
_SIDE_LENGTH_SUPPORT: Tuple[int, ...] = (5, 6, 7, 8, 9, 10, 12)


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
    fill_color: Color
    shaded_fill_color: Color
    panel_fill_color: Color
    panel_border_color: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]
    scene_transform: LazySceneTransform


@dataclass(frozen=True)
class _ResolvedProblem:
    objective_key: str
    query_id: str
    n_sides: int
    wedge_count: int
    start_index: int
    answer: float
    answer_type: str
    target_name: str
    relation: str
    total_area: float | None
    wedge_area: float | None
    side_length: float | None
    apothem: float | None
    perimeter: float | None
    central_angle_degrees: int
    query_probabilities: Dict[str, float]
    case_index: int
    layout_seed: int


@dataclass(frozen=True)
class _SceneGeometry:
    center: Point
    vertices: Tuple[Point, ...]
    selected_wedge_indices: Tuple[int, ...]
    selected_region_midpoint: Point
    angle_span_degrees: float


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    geometry: _SceneGeometry
    annotation_points: Dict[str, Point]
    readout_bboxes: Dict[str, BBox]
    construction_bboxes: Dict[str, BBox]
    render_map: Dict[str, Any]


def _blend(color_a: Color, color_b: Color, alpha: float) -> Color:
    amount = max(0.0, min(1.0, float(alpha)))
    return tuple(
        int(round((float(color_a[index]) * amount) + (float(color_b[index]) * (1.0 - amount))))
        for index in range(3)
    )  # type: ignore[return-value]


def _draw_text_centered(ctx: _RenderContext, text: str, center: Point, *, small: bool = True, role: str = "readout") -> BBox:
    font = ctx.small_font if bool(small) else ctx.font
    stroke_width = max(0, int(ctx.label_stroke_width))
    draw_text_traced(
        ctx.draw,
        (float(center[0]), float(center[1])),
        str(text),
        anchor="mm",
        font=font,
        fill=ctx.label_color,
        stroke_width=stroke_width,
        stroke_fill=ctx.label_stroke_color,
        role=str(role),
        required=False,
    )
    bbox = ctx.draw.textbbox((float(center[0]), float(center[1])), str(text), anchor="mm", font=font, stroke_width=stroke_width)
    return pad_bbox(bbox, 3.0, width=ctx.width, height=ctx.height)


def _draw_readout_panel(ctx: _RenderContext, lines: Sequence[str]) -> Dict[str, BBox]:
    if not lines:
        return {}
    padding_x = 14
    padding_y = 10
    line_gap = 6
    text_boxes = [ctx.draw.textbbox((0, 0), line, font=ctx.small_font, stroke_width=ctx.label_stroke_width) for line in lines]
    text_width = max(box[2] - box[0] for box in text_boxes)
    text_height = sum(box[3] - box[1] for box in text_boxes) + (len(lines) - 1) * line_gap
    left = 28
    top = 26
    panel = (
        float(left),
        float(top),
        float(left + text_width + (2 * padding_x)),
        float(top + text_height + (2 * padding_y)),
    )
    ctx.draw.rounded_rectangle(panel, radius=8, fill=ctx.panel_fill_color, outline=ctx.panel_border_color, width=max(1, ctx.line_width - 2))
    bboxes: Dict[str, BBox] = {"readout_panel": pad_bbox(panel, 0, width=ctx.width, height=ctx.height)}
    cursor_y = top + padding_y
    for index, line in enumerate(lines):
        box = text_boxes[index]
        x = left + padding_x
        y = cursor_y - box[1]
        draw_text_traced(
            ctx.draw,
            (float(x), float(y)),
            str(line),
            font=ctx.small_font,
            fill=ctx.label_color,
            stroke_width=ctx.label_stroke_width,
            stroke_fill=ctx.label_stroke_color,
            role="readout",
            required=False,
        )
        bboxes[f"readout_{index}"] = pad_bbox((x, y + box[1], x + (box[2] - box[0]), y + box[3]), 3.0, width=ctx.width, height=ctx.height)
        cursor_y += (box[3] - box[1]) + line_gap
    return bboxes


def _polygon_vertices(center: Point, radius: float, n_sides: int, rotation_degrees: float) -> Tuple[Point, ...]:
    points: list[Point] = []
    for index in range(int(n_sides)):
        theta = math.radians(float(rotation_degrees) + (360.0 * float(index) / float(n_sides)))
        points.append((float(center[0]) + float(radius) * math.cos(theta), float(center[1]) + float(radius) * math.sin(theta)))
    return tuple(points)


def _point_on_ray(center: Point, radius: float, degrees: float) -> Point:
    theta = math.radians(float(degrees))
    return (float(center[0]) + float(radius) * math.cos(theta), float(center[1]) + float(radius) * math.sin(theta))


def _draw_arc_polyline(ctx: _RenderContext, center: Point, radius: float, start_degrees: float, span_degrees: float) -> BBox:
    sample_count = max(8, int(abs(float(span_degrees)) // 5) + 2)
    points = [
        _point_on_ray(center, radius, float(start_degrees) + (float(span_degrees) * float(i) / float(sample_count - 1)))
        for i in range(sample_count)
    ]
    ctx.draw.line(points, fill=ctx.accent_color, width=max(3, ctx.line_width + 1), joint="curve")
    return bbox_from_points(points, width=ctx.width, height=ctx.height, pad=ctx.line_width + 4)


def _draw_dimension_label(ctx: _RenderContext, start: Point, end: Point, label: str, *, center_reference: Point, distance: float) -> BBox:
    direction = _unit(_sub(end, start))
    normal = (-direction[1], direction[0])
    midpoint = _mid(start, end)
    candidate = _add(midpoint, normal, distance)
    if math.hypot(candidate[0] - center_reference[0], candidate[1] - center_reference[1]) < math.hypot(midpoint[0] - center_reference[0], midpoint[1] - center_reference[1]):
        normal = (-normal[0], -normal[1])
    label_center = _add(midpoint, normal, distance)
    return _draw_text_centered(ctx, label, label_center, small=True)


def _draw_apothem(ctx: _RenderContext, center: Point, side_start: Point, side_end: Point, label: str) -> BBox:
    side_mid = _mid(side_start, side_end)
    ctx.draw.line((center, side_mid), fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
    bbox_line = bbox_from_points((center, side_mid), width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)
    label_center = _add(_mid(center, side_mid), _unit(_sub(side_mid, center)), 14.0)
    label_bbox = _draw_text_centered(ctx, label, label_center, small=True)
    return bbox_from_points(((bbox_line[0], bbox_line[1]), (bbox_line[2], bbox_line[3]), (label_bbox[0], label_bbox[1]), (label_bbox[2], label_bbox[3])), width=ctx.width, height=ctx.height, pad=2.0)


def _clean_side_apothem_case(rng: Any, n_sides: int) -> tuple[float, float, float, float, float]:
    """Choose labels whose rounded readouts recover the intended integer linear values."""
    side_order = list(_SIDE_LENGTH_SUPPORT)
    start = int(rng.randrange(len(side_order)))
    for offset in range(len(side_order)):
        side_length = float(side_order[(start + offset) % len(side_order)])
        apothem = round1(float(side_length) / (2.0 * math.tan(math.pi / float(n_sides))))
        if float(apothem) <= 0.0:
            continue
        wedge_area = round1(float(side_length) * float(apothem) / 2.0)
        total_area = round1(float(n_sides) * float(wedge_area))
        perimeter = float(n_sides) * float(side_length)
        perimeter_from_labels = (2.0 * float(total_area)) / float(apothem)
        side_from_total_labels = (2.0 * float(total_area)) / (float(n_sides) * float(apothem))
        side_from_wedge_labels = (2.0 * float(wedge_area)) / float(apothem)
        if (
            math.isclose(perimeter_from_labels, perimeter, abs_tol=1e-8)
            and math.isclose(side_from_total_labels, side_length, abs_tol=1e-8)
            and math.isclose(side_from_wedge_labels, side_length, abs_tol=1e-8)
        ):
            return side_length, apothem, wedge_area, total_area, perimeter
    raise RuntimeError(f"could not find clean side/apothem labels for n_sides={n_sides}")


def _select_problem(
    *,
    objective_key: str,
    query_id: str,
    query_probabilities: Mapping[str, float],
    instance_seed: int,
    params: Mapping[str, Any],
) -> _ResolvedProblem:
    query_probability_map = {str(key): float(value) for key, value in dict(query_probabilities).items()}
    rng = spawn_rng(int(instance_seed), f"{objective_key}.{query_id}.case")
    case_index = int(rng.randrange(10_000_000))
    n_sides = int(params.get("n_sides", _N_SUPPORT[int(rng.randrange(len(_N_SUPPORT)))]))
    central_angle = int(round(360.0 / float(n_sides)))
    max_wedges = min(4, int(n_sides) - 1)
    max_marked_angle_wedges = max(2, min(max_wedges, int(n_sides) // 2))

    total_area: float | None = None
    wedge_area: float | None = None
    side_length: float | None = None
    apothem: float | None = None
    perimeter: float | None = None
    relation = ""

    if query_id == "single_wedge_area_from_total":
        wedge_count = 1
        wedge_area = float(_WEDGE_AREA_SUPPORT[int(rng.randrange(len(_WEDGE_AREA_SUPPORT)))])
        total_area = float(n_sides) * float(wedge_area)
        answer = float(wedge_area)
        answer_type = "number"
        target_name = "the shaded wedge"
        relation = "equal_wedge_area_from_total_regular_polygon_area"
    elif query_id == "shaded_wedges_area_from_total":
        wedge_count = int(rng.randrange(2, max_wedges + 1))
        wedge_area = float(_WEDGE_AREA_SUPPORT[int(rng.randrange(len(_WEDGE_AREA_SUPPORT)))])
        total_area = float(n_sides) * float(wedge_area)
        answer = float(wedge_count) * float(wedge_area)
        answer_type = "number"
        target_name = "the shaded region"
        relation = "contiguous_wedge_group_area_from_total_regular_polygon_area"
    elif query_id == "wedge_area_from_side_and_apothem":
        wedge_count = 1
        side_length, apothem, wedge_area, _total_area, _perimeter = _clean_side_apothem_case(rng, n_sides)
        answer = float(wedge_area)
        answer_type = "number"
        target_name = "the shaded wedge"
        relation = "triangle_wedge_area_from_side_and_apothem"
    elif query_id == "single_wedge_central_angle":
        wedge_count = 1
        answer = float(central_angle)
        answer_type = "integer"
        target_name = "the marked center angle"
        relation = "single_regular_polygon_center_wedge_angle"
    elif query_id == "marked_wedges_central_angle":
        wedge_count = int(rng.randrange(2, max_marked_angle_wedges + 1))
        answer = float(wedge_count * central_angle)
        answer_type = "integer"
        target_name = "the marked center angle"
        relation = "contiguous_regular_polygon_center_wedge_angle_sum"
    elif query_id == "perimeter_from_side_length":
        wedge_count = 1
        side_length, apothem, wedge_area, total_area, perimeter = _clean_side_apothem_case(rng, n_sides)
        answer = float(perimeter)
        answer_type = "integer"
        target_name = "the regular polygon perimeter"
        relation = "regular_polygon_perimeter_from_side_length"
    elif query_id == "perimeter_from_total_area_and_apothem":
        wedge_count = 1
        side_length, apothem, wedge_area, total_area, perimeter = _clean_side_apothem_case(rng, n_sides)
        answer = float(perimeter)
        answer_type = "integer"
        target_name = "the regular polygon perimeter"
        relation = "regular_polygon_perimeter_from_area_and_apothem"
    elif query_id == "side_length_from_perimeter":
        wedge_count = 1
        side_length, apothem, wedge_area, total_area, perimeter = _clean_side_apothem_case(rng, n_sides)
        answer = float(side_length)
        answer_type = "integer"
        target_name = "the marked side"
        relation = "regular_polygon_side_length_from_perimeter"
    elif query_id == "side_length_from_total_area_and_apothem":
        wedge_count = 1
        side_length, apothem, wedge_area, total_area, perimeter = _clean_side_apothem_case(rng, n_sides)
        answer = float(side_length)
        answer_type = "integer"
        target_name = "the marked side"
        relation = "regular_polygon_side_length_from_area_and_apothem"
    elif query_id == "side_length_from_wedge_area_and_apothem":
        wedge_count = 1
        side_length, apothem, wedge_area, total_area, perimeter = _clean_side_apothem_case(rng, n_sides)
        answer = float(side_length)
        answer_type = "integer"
        target_name = "the marked side"
        relation = "regular_polygon_side_length_from_wedge_area_and_apothem"
    else:
        raise ValueError(f"unsupported query_id: {query_id}")

    start_upper = max(0, int(n_sides) - int(wedge_count))
    start_index = int(rng.randrange(start_upper + 1))
    return _ResolvedProblem(
        objective_key=str(objective_key),
        query_id=str(query_id),
        n_sides=int(n_sides),
        wedge_count=int(wedge_count),
        start_index=int(start_index),
        answer=float(answer),
        answer_type=str(answer_type),
        target_name=str(target_name),
        relation=str(relation),
        total_area=total_area,
        wedge_area=wedge_area,
        side_length=side_length,
        apothem=apothem,
        perimeter=perimeter,
        central_angle_degrees=int(central_angle),
        query_probabilities=dict(query_probability_map),
        case_index=int(case_index),
        layout_seed=int(instance_seed),
    )


def _build_context(*, instance_seed: int, params: Mapping[str, Any], rendering_defaults: Mapping[str, Any]) -> _RenderContext:
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
    line_color = tuple(int(value) for value in diagram_style.stroke_rgb)
    panel_fill = tuple(int(value) for value in diagram_style.panel_fill_rgb)
    accent = tuple(int(value) for value in diagram_style.accent_rgb)
    image = background.convert("RGB")
    return _RenderContext(
        image=image,
        draw=ImageDraw.Draw(image),
        width=width,
        height=height,
        line_color=line_color,
        secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        accent_color=accent,
        fill_color=tuple(int(value) for value in diagram_style.panel_alt_fill_rgb),
        shaded_fill_color=_blend(accent, panel_fill, 0.34),
        panel_fill_color=panel_fill,
        panel_border_color=tuple(int(value) for value in diagram_style.panel_border_rgb),
        line_width=max(2, int(params.get("line_width", rendering_defaults.get("line_width", 3)))),
        label_stroke_width=max(0, min(1, int(diagram_style.label_stroke_width_px))),
        font=load_font(int(params.get("label_font_size", rendering_defaults.get("label_font_size", 22))), bold=False, font_family=readout_font_family),
        small_font=load_font(int(params.get("small_label_font_size", rendering_defaults.get("small_label_font_size", 18))), bold=False, font_family=readout_font_family),
        diagram_style_meta=diagram_style_trace,
        background_meta=dict(background_meta),
        scene_transform=LazySceneTransform(
            spawn_rng(int(instance_seed), f"{SCENE_ID}.scene_transform"),
            params=params,
            render_defaults=rendering_defaults,
            canvas_width=int(width),
            canvas_height=int(height),
        ),
    )


def _render_problem(problem: _ResolvedProblem, ctx: _RenderContext) -> _RenderedScene:
    rng = spawn_rng(int(problem.layout_seed), f"{SCENE_ID}.layout")
    radius = min(float(ctx.width) * 0.285, float(ctx.height) * 0.345) * rng.uniform(0.92, 1.05)
    center = (
        float(ctx.width) * 0.53 + rng.uniform(-24.0, 28.0),
        float(ctx.height) * 0.57 + rng.uniform(-18.0, 18.0),
    )
    rotation = -90.0 + (180.0 / float(problem.n_sides)) + rng.uniform(-8.0, 8.0)
    vertices = _polygon_vertices(center, radius, problem.n_sides, rotation)
    selected_indices = tuple(range(int(problem.start_index), int(problem.start_index + problem.wedge_count)))
    start_degrees = rotation + (360.0 * float(problem.start_index) / float(problem.n_sides))
    angle_span = 360.0 * float(problem.wedge_count) / float(problem.n_sides)
    target_midpoint = _point_on_ray(center, radius * 0.54, start_degrees + (angle_span / 2.0))
    transform = ctx.scene_transform.resolve((center, *vertices, target_midpoint))
    center = transform.point(center)
    vertices = transform.points(vertices)
    target_midpoint = transform.point(target_midpoint)
    radius = float(radius) * float(transform.scale)
    start_degrees += float(transform.angle_degrees)

    construction_bboxes: Dict[str, BBox] = {}
    readout_bboxes: Dict[str, BBox] = {}
    polygon_points = tuple(vertices)
    ctx.draw.polygon(polygon_points, fill=ctx.fill_color)
    for wedge_index in selected_indices:
        ctx.draw.polygon((center, vertices[wedge_index], vertices[(wedge_index + 1) % problem.n_sides]), fill=ctx.shaded_fill_color)
    ctx.draw.line((*polygon_points, polygon_points[0]), fill=ctx.line_color, width=ctx.line_width, joint="curve")
    for vertex in vertices:
        ctx.draw.line((center, vertex), fill=ctx.secondary_color, width=max(1, ctx.line_width - 1))
    center_dot = max(4, ctx.line_width + 2)
    ctx.draw.ellipse((center[0] - center_dot, center[1] - center_dot, center[0] + center_dot, center[1] + center_dot), fill=ctx.line_color)
    _draw_text_centered(ctx, "O", _add(center, (0.0, -22.0)), small=True, role="label")

    construction_bboxes["regular_polygon"] = bbox_from_points(vertices, width=ctx.width, height=ctx.height, pad=ctx.line_width + 4)
    end_index = (int(problem.start_index) + int(problem.wedge_count)) % int(problem.n_sides)
    side_start = vertices[problem.start_index]
    side_end = vertices[(problem.start_index + 1) % problem.n_sides]
    side_mid = _mid(side_start, side_end)
    construction_bboxes["selected_region"] = bbox_from_points(
        (center, vertices[problem.start_index], vertices[end_index]),
        width=ctx.width,
        height=ctx.height,
        pad=ctx.line_width + 4,
    )

    if problem.query_id in {"single_wedge_central_angle", "marked_wedges_central_angle"}:
        construction_bboxes["marked_angle_arc"] = _draw_arc_polyline(ctx, center, radius * 0.27, start_degrees, angle_span)
        question_point = _point_on_ray(center, radius * 0.34, start_degrees + (angle_span / 2.0))
        readout_bboxes["unknown_angle_label"] = _draw_text_centered(ctx, "?", question_point, small=False)

    if problem.query_id == "wedge_area_from_side_and_apothem":
        readout_bboxes["side_length_label"] = _draw_dimension_label(
            ctx,
            side_start,
            side_end,
            f"s = {fmt_measure(float(problem.side_length))}",
            center_reference=center,
            distance=32.0,
        )
        construction_bboxes["apothem"] = _draw_apothem(ctx, center, side_start, side_end, f"a = {fmt_measure(float(problem.apothem))}")
    elif problem.query_id == "perimeter_from_side_length":
        readout_bboxes["side_length_label"] = _draw_dimension_label(
            ctx,
            side_start,
            side_end,
            f"s = {fmt_measure(float(problem.side_length))}",
            center_reference=center,
            distance=32.0,
        )
    elif problem.query_id == "perimeter_from_total_area_and_apothem":
        construction_bboxes["apothem"] = _draw_apothem(ctx, center, side_start, side_end, f"a = {fmt_measure(float(problem.apothem))}")
        readout_bboxes.update(_draw_readout_panel(ctx, (f"Total area = {fmt_measure(float(problem.total_area))}",)))
    elif problem.query_id == "side_length_from_perimeter":
        readout_bboxes["target_side_label"] = _draw_dimension_label(
            ctx,
            side_start,
            side_end,
            "s = ?",
            center_reference=center,
            distance=32.0,
        )
        readout_bboxes.update(_draw_readout_panel(ctx, (f"Perimeter = {fmt_measure(float(problem.perimeter))}",)))
    elif problem.query_id == "side_length_from_total_area_and_apothem":
        readout_bboxes["target_side_label"] = _draw_dimension_label(
            ctx,
            side_start,
            side_end,
            "s = ?",
            center_reference=center,
            distance=32.0,
        )
        construction_bboxes["apothem"] = _draw_apothem(ctx, center, side_start, side_end, f"a = {fmt_measure(float(problem.apothem))}")
        readout_bboxes.update(_draw_readout_panel(ctx, (f"Total area = {fmt_measure(float(problem.total_area))}",)))
    elif problem.query_id == "side_length_from_wedge_area_and_apothem":
        readout_bboxes["target_side_label"] = _draw_dimension_label(
            ctx,
            side_start,
            side_end,
            "s = ?",
            center_reference=center,
            distance=32.0,
        )
        construction_bboxes["apothem"] = _draw_apothem(ctx, center, side_start, side_end, f"a = {fmt_measure(float(problem.apothem))}")
        readout_bboxes.update(_draw_readout_panel(ctx, (f"Wedge area = {fmt_measure(float(problem.wedge_area))}",)))
    elif problem.total_area is not None:
        readout_bboxes.update(_draw_readout_panel(ctx, (f"Total area = {fmt_measure(float(problem.total_area))}",)))

    start_vertex = vertices[problem.start_index]
    end_vertex = vertices[end_index]
    if problem.objective_key == PIECE_OBJECTIVE_KEY:
        annotation = {
            "center": center,
            "wedge_vertex_start": start_vertex,
            "wedge_vertex_end": end_vertex,
            "target_region_midpoint": target_midpoint,
        }
    elif problem.objective_key == ANGLE_OBJECTIVE_KEY:
        annotation = {
            "center": center,
            "angle_ray_start": start_vertex,
            "angle_ray_end": end_vertex,
        }
    elif problem.objective_key == PERIMETER_OBJECTIVE_KEY:
        annotation = {
            "center": center,
            "side_start": side_start,
            "side_end": side_end,
        }
        if problem.query_id == "perimeter_from_total_area_and_apothem":
            annotation["apothem_foot"] = side_mid
    elif problem.objective_key == SIDE_LENGTH_OBJECTIVE_KEY:
        annotation = {
            "center": center,
            "target_side_start": side_start,
            "target_side_end": side_end,
        }
        if problem.query_id in {"side_length_from_total_area_and_apothem", "side_length_from_wedge_area_and_apothem"}:
            annotation["apothem_foot"] = side_mid
        if problem.query_id == "side_length_from_wedge_area_and_apothem":
            annotation["target_region_midpoint"] = target_midpoint
    else:
        raise ValueError(f"unsupported task_id: {problem.task_id}")

    geometry = _SceneGeometry(
        center=center,
        vertices=vertices,
        selected_wedge_indices=selected_indices,
        selected_region_midpoint=target_midpoint,
        angle_span_degrees=float(angle_span),
    )
    render_map = {
        "center": _point_to_list(center),
        "vertices": [_point_to_list(point) for point in vertices],
        "selected_wedge_indices": [int(index) for index in selected_indices],
        "readout_bboxes": _json_ready(readout_bboxes),
        "construction_bboxes": _json_ready(construction_bboxes),
    }
    return _RenderedScene(
        image=ctx.image,
        geometry=geometry,
        annotation_points=annotation,
        readout_bboxes=readout_bboxes,
        construction_bboxes=construction_bboxes,
        render_map=render_map,
    )


def _answer_value(problem: _ResolvedProblem) -> int | float:
    if problem.answer_type == "integer":
        return int(round(float(problem.answer)))
    return float(round1(float(problem.answer)))


def _make_prompt_examples(annotation_keys: Sequence[str], *, answer: int | float) -> tuple[str, str]:
    answer_value: int | float = int(answer) if isinstance(answer, int) else float(answer)
    return build_keyed_point_prompt_json_examples(annotation_keys=annotation_keys, answer=answer_value)




@dataclass(frozen=True)
class RegularPolygonDecompositionArtifact:
    prompt: str
    answer_type: str
    answer: int | float
    annotation_value: Dict[str, Any]
    image: Image.Image
    trace_payload: Dict[str, Any]
    task_versions: Dict[str, Any]
    query_id: str
    prompt_variants: Dict[str, Any]


class RegularPolygonDecompositionRuntime:
    """Scene-local runtime shared by regular-polygon decomposition tasks."""

    def generate_artifact(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
        runtime_namespace: str,
        query_id: str,
        query_probabilities: Mapping[str, float],
        objective_key: str,
        task_key: str,
        answer_hint_key: str,
    ) -> RegularPolygonDecompositionArtifact:
        _generation_defaults, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
            _SCENE_DEFAULTS,
            task_id=str(runtime_namespace),
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                problem = _select_problem(
                    objective_key=str(objective_key),
                    query_id=str(query_id),
                    query_probabilities=query_probabilities,
                    instance_seed=int(instance_seed) + int(attempt),
                    params=params,
                )
                ctx = _build_context(instance_seed=int(instance_seed) + int(attempt), params=params, rendering_defaults=rendering_defaults)
                rendered = _render_problem(problem, ctx)
                break
            except Exception as exc:
                last_error = exc
                continue
        else:
            raise RuntimeError(f"failed to generate {str(runtime_namespace)}") from last_error

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
                answer_hint_key,
            ),
            context=f"prompt defaults for {str(runtime_namespace)}",
        )
        annotation_keys = tuple(rendered.annotation_points.keys())
        answer_value = _answer_value(problem)
        json_example, json_example_answer_only = _make_prompt_examples(annotation_keys, answer=answer_value)
        annotation_key_list = ", ".join(f'"{key}"' for key in annotation_keys)
        annotation_hint = str(prompt_defaults["annotation_hint"]).format(annotation_keys=annotation_key_list)
        prompt_selection = render_scene_prompt_variants(
            domain="geometry",
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(problem.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "target_name": str(problem.target_name),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults[answer_hint_key]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        annotation_value = {key: _point_to_list(point) for key, point in rendered.annotation_points.items()}
        measurement_payload = {
            "n_sides": int(problem.n_sides),
            "wedge_count": int(problem.wedge_count),
            "start_index": int(problem.start_index),
            "selected_wedge_indices": [int(index) for index in rendered.geometry.selected_wedge_indices],
            "central_angle_degrees": int(problem.central_angle_degrees),
            "angle_span_degrees": round(float(rendered.geometry.angle_span_degrees), 3),
            "total_area": None if problem.total_area is None else float(problem.total_area),
            "wedge_area": None if problem.wedge_area is None else float(problem.wedge_area),
            "side_length": None if problem.side_length is None else float(problem.side_length),
            "apothem": None if problem.apothem is None else float(problem.apothem),
            "perimeter": None if problem.perimeter is None else float(problem.perimeter),
            "target_name": str(problem.target_name),
            "relation": str(problem.relation),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": "geometry",
                "scene_id": SCENE_ID,
                "task_id": str(runtime_namespace),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "entities": [
                    {
                        "type": "regular_polygon_cut_into_center_wedges",
                        "n_sides": int(problem.n_sides),
                        "center": _point_to_list(rendered.geometry.center),
                        "vertices": [_point_to_list(point) for point in rendered.geometry.vertices],
                        "selected_wedge_indices": [int(index) for index in rendered.geometry.selected_wedge_indices],
                    },
                ],
                "relations": {
                    "type": str(problem.relation),
                    "query_id": str(problem.query_id),
                },
            },
            "query_spec": {
                "task_id": str(runtime_namespace),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "params": {
                    "query_id": str(problem.query_id),
                    "query_id_probabilities": dict(problem.query_probabilities),
                    "case_index": int(problem.case_index),
                    "n_sides": int(problem.n_sides),
                    "wedge_count": int(problem.wedge_count),
                },
            },
            "render_spec": {
                "task_id": str(runtime_namespace),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "canvas": {"width": int(ctx.width), "height": int(ctx.height)},
                "single_object_scene_rotation": ctx.scene_transform.metadata(),
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
                "task_id": str(runtime_namespace),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "answer": answer_value,
                **dict(measurement_payload),
                "annotation_roles": list(annotation_keys),
            },
            "witness_symbolic": {
                "task_id": str(runtime_namespace),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "answer": answer_value,
                **dict(measurement_payload),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_value),
                "pixel_keyed_point_map": dict(annotation_value),
            },
        }
        answer_format = "integer" if problem.answer_type == "integer" else "number"
        return RegularPolygonDecompositionArtifact(
            prompt=str(prompt_artifacts.prompt),
            answer_type=str(answer_format),
            answer=answer_value,
            annotation_value=dict(annotation_value),
            image=image,
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "ANGLE_OBJECTIVE_KEY",
    "PERIMETER_OBJECTIVE_KEY",
    "PIECE_OBJECTIVE_KEY",
    "RegularPolygonDecompositionArtifact",
    "RegularPolygonDecompositionRuntime",
    "SCENE_ID",
    "SIDE_LENGTH_OBJECTIVE_KEY",
]
