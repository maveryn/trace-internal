"""Scene-local runtime primitives for cone-sector net diagrams."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from trace.tasks.shared.prompt_json_example import dump_prompt_json_examples
from trace.tasks.shared.text_rendering import load_font
from trace.tasks.geometry.shared.diagram_style import (
    geometry_diagram_style_metadata,
    geometry_shape_style_from_diagram_style,
    prepare_geometry_diagram_style_and_background,
)
from trace.tasks.geometry.shared.measurement_rendering import (
    bbox_from_points as _bbox_from_points,
    bbox_to_list as _bbox_to_list,
    draw_label as _draw_label,
    fmt_measure as _fmt_number,
    pad_bbox as _pad_bbox,
    round1 as _round1,
)

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

DOMAIN = "geometry"
SCENE_ID = "cone_net"
CONE_NET_CASES: Tuple[Tuple[int, int], ...] = (
    (9, 120),
    (10, 144),
    (12, 150),
    (14, 180),
    (15, 120),
    (16, 135),
    (18, 160),
    (20, 162),
    (21, 120),
    (24, 150),
    (24, 180),
    (30, 144),
)

POST_IMAGE_NOISE_DEFAULTS: Dict[str, Any] = {
    "apply_prob": 0.45,
    "edit_types": ["blur", "downsample", "jpeg", "noise"],
    "edit_count_range": [1, 1],
    "value_ranges": {
        "blur": {"radius": [0.08, 0.22]},
        "downsample": {"scale": [0.95, 0.99]},
        "jpeg": {"quality": [88, 96]},
        "noise": {"alpha": [0.008, 0.02]},
    },
}


@dataclass
class RenderContext:
    rng: Any
    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    line_color: Color
    label_color: Color
    label_stroke_color: Color
    fill_color: Color
    cone_fill_color: Color
    accent_color: Color
    line_width: int
    font: Any
    small_font: Any
    label_stroke_width: int


@dataclass(frozen=True)
class ConeNetProblem:
    answer: float
    slant_height: int
    theta_degrees: int
    base_radius: float
    cone_height: float
    arc_length: float
    target_measure: str


@dataclass(frozen=True)
class RenderedConeNetScene:
    image: Image.Image
    answer: float
    annotation_roles: Tuple[str, ...]
    annotation_keyed_points: Mapping[str, Point]
    label_bboxes: Dict[str, BBox]
    point_label_bboxes: Dict[str, BBox]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]


def select_case_index(*, instance_seed: int, params: Mapping[str, Any], namespace: str) -> int:
    explicit_case = params.get("case_index")
    if explicit_case is not None:
        return int(explicit_case) % len(CONE_NET_CASES)
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    return int(selection_index) % len(CONE_NET_CASES)


def _case_values(case_index: int, params: Mapping[str, Any]) -> tuple[int, int, float, float, float]:
    slant_height, theta_degrees = CONE_NET_CASES[int(case_index) % len(CONE_NET_CASES)]
    slant_height = int(params.get("slant_height", slant_height))
    theta_degrees = int(params.get("theta_degrees", theta_degrees))
    if slant_height <= 0:
        raise ValueError("cone net slant height must be positive")
    if not 0 < theta_degrees < 360:
        raise ValueError("cone net central angle must be between 0 and 360 degrees")
    base_radius = float(slant_height) * float(theta_degrees) / 360.0
    cone_height = math.sqrt(max(0.0, float(slant_height) ** 2 - base_radius**2))
    arc_length = (float(theta_degrees) / 360.0) * 2.0 * math.pi * float(slant_height)
    return int(slant_height), int(theta_degrees), _round1(base_radius), _round1(cone_height), _round1(arc_length)


def make_base_radius_problem(*, case_index: int, params: Mapping[str, Any]) -> ConeNetProblem:
    slant_height, theta_degrees, base_radius, cone_height, arc_length = _case_values(int(case_index), params)
    return ConeNetProblem(
        answer=_round1(base_radius),
        slant_height=int(slant_height),
        theta_degrees=int(theta_degrees),
        base_radius=float(base_radius),
        cone_height=float(cone_height),
        arc_length=float(arc_length),
        target_measure="base_radius",
    )


def make_height_problem(*, case_index: int, params: Mapping[str, Any]) -> ConeNetProblem:
    slant_height, theta_degrees, base_radius, cone_height, arc_length = _case_values(int(case_index), params)
    return ConeNetProblem(
        answer=_round1(cone_height),
        slant_height=int(slant_height),
        theta_degrees=int(theta_degrees),
        base_radius=float(base_radius),
        cone_height=float(cone_height),
        arc_length=float(arc_length),
        target_measure="height",
    )


def base_radius_support_values() -> tuple[float, ...]:
    return tuple(sorted({_round1(case[0] * case[1] / 360.0) for case in CONE_NET_CASES}))


def height_support_values() -> tuple[float, ...]:
    return tuple(
        sorted(
            {
                _round1(math.sqrt(max(0.0, case[0] ** 2 - (case[0] * case[1] / 360.0) ** 2)))
                for case in CONE_NET_CASES
            }
        )
    )


def create_render_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    random_namespace: str,
) -> tuple[RenderContext, Dict[str, Any]]:
    rng = spawn_rng(int(instance_seed), str(random_namespace))
    width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 760)))
    height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 560)))
    image, background_meta, diagram_style, diagram_style_resolution = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=int(width),
        canvas_height=int(height),
        allow_dark=True,
    )
    shape_style = geometry_shape_style_from_diagram_style(diagram_style)
    palettes: Tuple[Tuple[Color, Color, Color], ...] = (
        (tuple(int(v) for v in diagram_style.option_fill_rgb), tuple(int(v) for v in diagram_style.panel_alt_fill_rgb), tuple(int(v) for v in diagram_style.accent_rgb)),
        (tuple(int(v) for v in diagram_style.panel_fill_rgb), tuple(int(v) for v in diagram_style.muted_fill_rgb), tuple(int(v) for v in diagram_style.secondary_accent_rgb)),
        (tuple(int(v) for v in diagram_style.muted_fill_rgb), tuple(int(v) for v in diagram_style.option_fill_rgb), tuple(int(v) for v in diagram_style.highlight_rgb)),
        (tuple(int(v) for v in diagram_style.panel_alt_fill_rgb), tuple(int(v) for v in diagram_style.panel_fill_rgb), tuple(int(v) for v in diagram_style.guide_rgb)),
    )
    palette_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"geometry.{SCENE_ID}.palette",
    )
    fill_color, cone_fill_color, accent_color = palettes[int(palette_index) % len(palettes)]
    font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
    small_font_size = int(params.get("small_label_font_size", group_default(render_defaults, "small_label_font_size", 18)))
    line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 4)))
    label_stroke_width = int(params.get("label_stroke_width", group_default(render_defaults, "label_stroke_width", 1)))
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"geometry.{SCENE_ID}.font_family",
        params=params,
    )
    font_record = get_font_family_record(str(font_family))
    ctx = RenderContext(
        rng=rng,
        image=image,
        draw=ImageDraw.Draw(image),
        width=int(width),
        height=int(height),
        line_color=shape_style.line_color,
        label_color=shape_style.label_color,
        label_stroke_color=shape_style.label_stroke_color,
        fill_color=fill_color,
        cone_fill_color=cone_fill_color,
        accent_color=accent_color,
        line_width=max(2, int(line_width)),
        font=load_font(max(12, int(font_size)), bold=True, font_family=str(font_family)),
        small_font=load_font(max(10, int(small_font_size)), bold=True, font_family=str(font_family)),
        label_stroke_width=max(0, int(label_stroke_width)),
    )
    render_meta = {
        "background_style": dict(background_meta),
        "shape_style": shape_style.to_trace_dict(),
        "line_width": int(ctx.line_width),
        "label_font_size": int(font_size),
        "small_label_font_size": int(small_font_size),
        "label_stroke_width": int(ctx.label_stroke_width),
        "fill_color": list(fill_color),
        "cone_fill_color": list(cone_fill_color),
        "accent_color": list(accent_color),
        "technical_diagram_style": geometry_diagram_style_metadata(diagram_style),
        "technical_diagram_style_resolution": dict(diagram_style_resolution),
        "font_family": font_record.to_trace(),
        "font_asset_version": font_asset_version(),
    }
    return ctx, render_meta


def _draw_dashed_line(ctx: RenderContext, start: Point, end: Point, *, fill: Color, width: int, dash: float = 12.0, gap: float = 8.0) -> None:
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = math.hypot(dx, dy)
    if length <= 1e-9:
        return
    ux = dx / length
    uy = dy / length
    pos = 0.0
    while pos < length:
        segment_end = min(length, pos + dash)
        ctx.draw.line(
            [(float(start[0]) + ux * pos, float(start[1]) + uy * pos), (float(start[0]) + ux * segment_end, float(start[1]) + uy * segment_end)],
            fill=fill,
            width=width,
        )
        pos += dash + gap


def _draw_dimension(
    ctx: RenderContext,
    start: Point,
    end: Point,
    label: str,
    *,
    label_offset: Point = (0.0, 0.0),
    color: Color | None = None,
    dashed: bool = False,
) -> BBox:
    draw_color = color if color is not None else ctx.label_color
    if dashed:
        _draw_dashed_line(ctx, start, end, fill=draw_color, width=max(2, ctx.line_width - 1))
    else:
        ctx.draw.line([start, end], fill=draw_color, width=max(2, ctx.line_width - 1))
    tick = 7.0
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = math.hypot(dx, dy)
    if length > 1e-9:
        nx = -dy / length
        ny = dx / length
        for point in (start, end):
            ctx.draw.line(
                [(float(point[0]) - tick * nx, float(point[1]) - tick * ny), (float(point[0]) + tick * nx, float(point[1]) + tick * ny)],
                fill=draw_color,
                width=max(2, ctx.line_width - 1),
            )
    center = ((float(start[0]) + float(end[0])) / 2.0 + float(label_offset[0]), (float(start[1]) + float(end[1])) / 2.0 + float(label_offset[1]))
    return _draw_label(ctx, label, center, small=True)


def _point_on_circle(center: Point, radius: float, degrees: float) -> Point:
    radians = math.radians(float(degrees))
    return (float(center[0]) + float(radius) * math.cos(radians), float(center[1]) + float(radius) * math.sin(radians))


def _draw_arc_band(ctx: RenderContext, box: BBox, *, start: float, end: float, color: Color, width_extra: int = 2) -> None:
    ctx.draw.arc(box, start=float(start), end=float(end), fill=color, width=max(5, int(ctx.line_width) + int(width_extra)))


def _draw_arrow(ctx: RenderContext, start: Point, end: Point) -> None:
    ctx.draw.line([start, end], fill=ctx.accent_color, width=max(3, ctx.line_width - 1))
    angle = math.atan2(float(end[1]) - float(start[1]), float(end[0]) - float(start[0]))
    head = 14.0
    spread = math.radians(28.0)
    left = (float(end[0]) - head * math.cos(angle - spread), float(end[1]) - head * math.sin(angle - spread))
    right = (float(end[0]) - head * math.cos(angle + spread), float(end[1]) - head * math.sin(angle + spread))
    ctx.draw.polygon((end, left, right), fill=ctx.accent_color)


def build_keyed_point_prompt_examples(annotation_keys: Sequence[str], *, answer: float) -> tuple[str, str]:
    annotation: Dict[str, list[int]] = {}
    for index, key in enumerate(annotation_keys):
        annotation[str(key)] = [130 + (42 * int(index)), 180 + (24 * int(index))]
    return dump_prompt_json_examples(annotation=annotation, answer=float(answer), ensure_ascii=False)


def render_cone_net_scene(ctx: RenderContext, problem: ConeNetProblem) -> RenderedConeNetScene:
    sector_center = (245.0, 310.0)
    sector_radius_px = 172.0
    start_deg = -136.0
    end_deg = start_deg + float(problem.theta_degrees)
    mid_deg = (start_deg + end_deg) / 2.0
    arc_box = (sector_center[0] - sector_radius_px, sector_center[1] - sector_radius_px, sector_center[0] + sector_radius_px, sector_center[1] + sector_radius_px)
    p0 = _point_on_circle(sector_center, sector_radius_px, start_deg)
    p1 = _point_on_circle(sector_center, sector_radius_px, end_deg)
    ctx.draw.pieslice(arc_box, start=start_deg, end=end_deg, fill=ctx.fill_color, outline=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([sector_center, p0], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([sector_center, p1], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse((sector_center[0] - 4.0, sector_center[1] - 4.0, sector_center[0] + 4.0, sector_center[1] + 4.0), fill=ctx.line_color)
    _draw_arc_band(ctx, arc_box, start=start_deg, end=end_deg, color=ctx.accent_color, width_extra=4)

    label_bboxes: Dict[str, BBox] = {}
    label_bboxes["slant_height"] = _draw_dimension(ctx, sector_center, p0, f"l={_fmt_number(problem.slant_height)}", label_offset=(-18.0, 28.0))
    small_angle_radius = 58.0
    small_angle_box = (sector_center[0] - small_angle_radius, sector_center[1] - small_angle_radius, sector_center[0] + small_angle_radius, sector_center[1] + small_angle_radius)
    ctx.draw.arc(small_angle_box, start=start_deg, end=end_deg, fill=ctx.accent_color, width=max(3, ctx.line_width - 1))
    angle_center = (sector_center[0] + 82.0 * math.cos(math.radians(mid_deg)), sector_center[1] + 82.0 * math.sin(math.radians(mid_deg)))
    label_bboxes["sector_angle"] = _draw_label(ctx, f"θ={problem.theta_degrees}°", angle_center, small=True)

    cone_apex = (584.0, 122.0)
    cone_base_center = (584.0, 414.0)
    cone_base_left = (486.0, 414.0)
    cone_base_right = (682.0, 414.0)
    cone_base_box = (cone_base_left[0], cone_base_center[1] - 22.0, cone_base_right[0], cone_base_center[1] + 22.0)
    ctx.draw.polygon((cone_apex, cone_base_left, cone_base_right), fill=ctx.cone_fill_color, outline=ctx.line_color)
    ctx.draw.line([cone_apex, cone_base_left], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([cone_apex, cone_base_right], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse(cone_base_box, outline=ctx.accent_color, width=ctx.line_width)
    ctx.draw.arc(cone_base_box, start=0, end=180, fill=ctx.accent_color, width=ctx.line_width + 1)
    _draw_dashed_line(ctx, cone_apex, cone_base_center, fill=ctx.line_color, width=max(2, ctx.line_width - 1))
    ctx.draw.line([cone_base_center, cone_base_right], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    marker = 16.0
    ctx.draw.line([(cone_base_center[0], cone_base_center[1] - marker), (cone_base_center[0] + marker, cone_base_center[1] - marker), (cone_base_center[0] + marker, cone_base_center[1])], fill=ctx.line_color, width=2)
    _draw_label(ctx, "l", ((cone_apex[0] + cone_base_right[0]) / 2.0 + 20.0, (cone_apex[1] + cone_base_right[1]) / 2.0), small=True)
    _draw_arrow(ctx, (405.0, 252.0), (492.0, 342.0))

    if problem.target_measure == "base_radius":
        label_bboxes["target"] = _draw_label(ctx, "r=?", ((cone_base_center[0] + cone_base_right[0]) / 2.0, cone_base_center[1] + 34.0), small=True)
    elif problem.target_measure == "height":
        label_bboxes["target"] = _draw_label(ctx, "h=?", (cone_base_center[0] - 34.0, (cone_apex[1] + cone_base_center[1]) / 2.0), small=True)
    else:
        raise ValueError(f"unsupported cone-net target measure: {problem.target_measure}")

    annotation_keyed_points: Dict[str, Point] = {"S": sector_center, "P": p0, "Q": p1, "C": cone_base_center}
    if problem.target_measure == "base_radius":
        annotation_keyed_points["R"] = cone_base_right
    elif problem.target_measure == "height":
        annotation_keyed_points["A"] = cone_apex

    point_label_bboxes: Dict[str, BBox] = {}
    point_label_offsets: Dict[str, Point] = {"S": (-20.0, 22.0), "P": (-18.0, -16.0), "Q": (18.0, 18.0), "A": (0.0, -20.0), "C": (-24.0, 20.0), "R": (24.0, 2.0)}
    for label, point in annotation_keyed_points.items():
        px, py = float(point[0]), float(point[1])
        ctx.draw.ellipse((px - 3.5, py - 3.5, px + 3.5, py + 3.5), fill=ctx.line_color)
        ox, oy = point_label_offsets.get(str(label), (16.0, -16.0))
        point_label_bboxes[str(label)] = _draw_label(ctx, str(label), (px + float(ox), py + float(oy)), small=True)

    sector_bbox = _pad_bbox(arc_box, 8.0, width=ctx.width, height=ctx.height)
    cone_bbox = _bbox_from_points((cone_apex, cone_base_left, cone_base_right), width=ctx.width, height=ctx.height, pad=24.0)
    scene_entities = (
        {
            "entity_id": "sector_net",
            "entity_type": "sector",
            "bbox": _bbox_to_list(sector_bbox),
            "radius_units": int(problem.slant_height),
            "theta_degrees": int(problem.theta_degrees),
            "arc_length_units": float(problem.arc_length),
        },
        {
            "entity_id": "folded_cone",
            "entity_type": "cone",
            "bbox": _bbox_to_list(cone_bbox),
            "slant_height_units": int(problem.slant_height),
            "base_radius_units": float(problem.base_radius),
            "height_units": float(problem.cone_height),
        },
    )
    witness = {
        "formula_family": "cone_sector_net",
        "target_measure": str(problem.target_measure),
        "slant_height": int(problem.slant_height),
        "theta_degrees": int(problem.theta_degrees),
        "arc_length": float(problem.arc_length),
        "base_radius": float(problem.base_radius),
        "cone_height": float(problem.cone_height),
        "net_relation": "sector arc length equals folded cone base circumference",
        "base_radius_relation": "r = theta * l / 360",
        "height_relation": "h^2 + r^2 = l^2",
        "answer_value": float(problem.answer),
    }
    return RenderedConeNetScene(
        image=ctx.image,
        answer=float(problem.answer),
        annotation_roles=tuple(annotation_keyed_points.keys()),
        annotation_keyed_points=dict(annotation_keyed_points),
        label_bboxes=dict(label_bboxes),
        point_label_bboxes=dict(point_label_bboxes),
        scene_entities=scene_entities,
        render_map={
            "sector": {
                "center": [round(sector_center[0], 3), round(sector_center[1], 3)],
                "radius_px": round(sector_radius_px, 3),
                "start_degrees": round(start_deg, 3),
                "end_degrees": round(end_deg, 3),
                "endpoints": [[round(p0[0], 3), round(p0[1], 3)], [round(p1[0], 3), round(p1[1], 3)]],
            },
            "cone": {
                "apex": [round(cone_apex[0], 3), round(cone_apex[1], 3)],
                "base_center": [round(cone_base_center[0], 3), round(cone_base_center[1], 3)],
                "base_left": [round(cone_base_left[0], 3), round(cone_base_left[1], 3)],
                "base_right": [round(cone_base_right[0], 3), round(cone_base_right[1], 3)],
            },
            "construction_points": {key: [round(point[0], 3), round(point[1], 3)] for key, point in annotation_keyed_points.items()},
            "label_bboxes": {key: _bbox_to_list(value) for key, value in label_bboxes.items()},
            "point_label_bboxes": {key: _bbox_to_list(value) for key, value in point_label_bboxes.items()},
            "coord_space": "pixel",
        },
        witness=witness,
    )


__all__ = [
    "CONE_NET_CASES",
    "ConeNetProblem",
    "DOMAIN",
    "POST_IMAGE_NOISE_DEFAULTS",
    "RenderedConeNetScene",
    "SCENE_ID",
    "base_radius_support_values",
    "build_keyed_point_prompt_examples",
    "create_render_context",
    "height_support_values",
    "make_base_radius_problem",
    "make_height_problem",
    "render_cone_net_scene",
    "select_case_index",
]
