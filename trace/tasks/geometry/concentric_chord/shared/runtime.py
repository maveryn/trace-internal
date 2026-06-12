"""Scene-local runtime primitives for concentric-circle chord diagrams."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from PIL import Image, ImageDraw

from trace.core.seed import spawn_rng
from trace.core.visual.background import make_background_canvas
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
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
    round1 as _round1,
)
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform
from trace.tasks.geometry.shared.vector2d import unit as _unit

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

DOMAIN = "geometry"
SCENE_ID = "concentric_chord"
PYTHAGOREAN_CASES: Tuple[Tuple[int, int, int], ...] = (
    (5, 3, 4),
    (10, 6, 8),
    (13, 5, 12),
    (13, 12, 5),
    (17, 8, 15),
    (25, 7, 24),
    (25, 15, 20),
    (25, 24, 7),
    (29, 20, 21),
    (34, 16, 30),
    (37, 12, 35),
    (39, 15, 36),
    (41, 9, 40),
    (41, 40, 9),
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
    accent_color: Color
    line_width: int
    font: Any
    small_font: Any
    label_stroke_width: int
    scene_transform: LazySceneTransform


@dataclass(frozen=True)
class ConcentricChordProblem:
    answer: float
    outer_radius: int
    inner_radius: int
    half_chord: int
    chord_length: int
    unknown_measure: str


@dataclass(frozen=True)
class RenderedConcentricChordScene:
    image: Image.Image
    answer: float
    annotation_roles: Tuple[str, ...]
    annotation_keyed_points: Mapping[str, Point]
    label_bboxes: Dict[str, BBox]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]


def select_case_index(*, instance_seed: int, params: Mapping[str, Any], namespace: str) -> int:
    explicit_case = params.get("case_index")
    if explicit_case is not None:
        return int(explicit_case) % len(PYTHAGOREAN_CASES)
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    return int(selection_index) % len(PYTHAGOREAN_CASES)


def _case_values(case_index: int, params: Mapping[str, Any]) -> tuple[int, int, int]:
    outer_radius, inner_radius, half_chord = PYTHAGOREAN_CASES[int(case_index) % len(PYTHAGOREAN_CASES)]
    outer_radius = int(params.get("outer_radius", outer_radius))
    inner_radius = int(params.get("inner_radius", inner_radius))
    half_chord = int(params.get("half_chord", half_chord))
    if outer_radius * outer_radius != inner_radius * inner_radius + half_chord * half_chord:
        raise ValueError("concentric circle case must satisfy R^2 = r^2 + (c/2)^2")
    return int(outer_radius), int(inner_radius), int(half_chord)


def make_chord_length_problem(*, case_index: int, params: Mapping[str, Any]) -> ConcentricChordProblem:
    outer_radius, inner_radius, half_chord = _case_values(int(case_index), params)
    chord_length = 2 * int(half_chord)
    return ConcentricChordProblem(
        answer=_round1(float(chord_length)),
        outer_radius=int(outer_radius),
        inner_radius=int(inner_radius),
        half_chord=int(half_chord),
        chord_length=int(chord_length),
        unknown_measure="chord_length",
    )


def make_inner_radius_problem(*, case_index: int, params: Mapping[str, Any]) -> ConcentricChordProblem:
    outer_radius, inner_radius, half_chord = _case_values(int(case_index), params)
    chord_length = 2 * int(half_chord)
    return ConcentricChordProblem(
        answer=_round1(float(inner_radius)),
        outer_radius=int(outer_radius),
        inner_radius=int(inner_radius),
        half_chord=int(half_chord),
        chord_length=int(chord_length),
        unknown_measure="inner_radius",
    )


def chord_length_support_values() -> tuple[int, ...]:
    return tuple(sorted({2 * int(case[2]) for case in PYTHAGOREAN_CASES}))


def inner_radius_support_values() -> tuple[int, ...]:
    return tuple(sorted({int(case[1]) for case in PYTHAGOREAN_CASES}))


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
    accents: Tuple[Color, ...] = (
        tuple(int(value) for value in diagram_style.accent_rgb),
        tuple(int(value) for value in diagram_style.secondary_accent_rgb),
        tuple(int(value) for value in diagram_style.highlight_rgb),
        tuple(int(value) for value in diagram_style.guide_rgb),
    )
    accent_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"geometry.{SCENE_ID}.accent",
    )
    accent_color = accents[int(accent_index) % len(accents)]
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
        accent_color=accent_color,
        line_width=max(2, int(line_width)),
        font=load_font(max(12, int(font_size)), bold=True, font_family=str(font_family)),
        small_font=load_font(max(10, int(small_font_size)), bold=True, font_family=str(font_family)),
        label_stroke_width=max(0, int(label_stroke_width)),
        scene_transform=LazySceneTransform(
            rng,
            params=params,
            render_defaults=render_defaults,
            canvas_width=int(width),
            canvas_height=int(height),
        ),
    )
    render_meta = {
        "background_style": dict(background_meta),
        "shape_style": shape_style.to_trace_dict(),
        "line_width": int(ctx.line_width),
        "label_font_size": int(font_size),
        "small_label_font_size": int(small_font_size),
        "label_stroke_width": int(ctx.label_stroke_width),
        "accent_color": list(accent_color),
        "technical_diagram_style": geometry_diagram_style_metadata(diagram_style),
        "technical_diagram_style_resolution": dict(diagram_style_resolution),
        "font_family": font_record.to_trace(),
        "font_asset_version": font_asset_version(),
    }
    return ctx, render_meta


def _draw_dimension(
    ctx: RenderContext,
    start: Point,
    end: Point,
    label: str,
    *,
    label_offset: Point = (0.0, 0.0),
    color: Color | None = None,
) -> BBox:
    draw_color = color if color is not None else ctx.label_color
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
                [
                    (float(point[0]) - tick * nx, float(point[1]) - tick * ny),
                    (float(point[0]) + tick * nx, float(point[1]) + tick * ny),
                ],
                fill=draw_color,
                width=max(2, ctx.line_width - 1),
            )
    center = (
        (float(start[0]) + float(end[0])) / 2.0 + float(label_offset[0]),
        (float(start[1]) + float(end[1])) / 2.0 + float(label_offset[1]),
    )
    return _draw_label(ctx, label, center, small=True)


def render_concentric_chord_scene(ctx: RenderContext, problem: ConcentricChordProblem) -> RenderedConcentricChordScene:
    raw_center = (326.0, 292.0)
    raw_outer_px = 178.0
    raw_inner_px = raw_outer_px * float(problem.inner_radius) / float(problem.outer_radius)
    raw_half_chord_px = raw_outer_px * float(problem.half_chord) / float(problem.outer_radius)
    raw_chord_y = raw_center[1] - raw_inner_px
    raw_left = (raw_center[0] - raw_half_chord_px, raw_chord_y)
    raw_right = (raw_center[0] + raw_half_chord_px, raw_chord_y)
    raw_tangent = (raw_center[0], raw_chord_y)
    raw_dim_left = (raw_left[0], raw_chord_y - 46.0)
    raw_dim_right = (raw_right[0], raw_chord_y - 46.0)
    ctx.scene_transform.resolve((raw_center, raw_left, raw_right, raw_tangent, raw_dim_left, raw_dim_right))
    center, left, right, tangent, dim_left, dim_right = ctx.scene_transform.points(
        (raw_center, raw_left, raw_right, raw_tangent, raw_dim_left, raw_dim_right)
    )
    outer_px = raw_outer_px * float(ctx.scene_transform.transform.scale)
    inner_px = raw_inner_px * float(ctx.scene_transform.transform.scale)

    outer_box = (center[0] - outer_px, center[1] - outer_px, center[0] + outer_px, center[1] + outer_px)
    inner_box = (center[0] - inner_px, center[1] - inner_px, center[0] + inner_px, center[1] + inner_px)
    ctx.draw.ellipse(outer_box, outline=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse(inner_box, outline=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([left, right], fill=ctx.accent_color, width=ctx.line_width + 1)
    ctx.draw.line([center, tangent], fill=ctx.line_color, width=max(2, ctx.line_width - 1))
    ctx.draw.line([center, right], fill=ctx.line_color, width=max(2, ctx.line_width - 1))

    marker = 16.0 * float(ctx.scene_transform.transform.scale)
    chord_unit = _unit((float(right[0]) - float(tangent[0]), float(right[1]) - float(tangent[1])))
    radius_unit = _unit((float(center[0]) - float(tangent[0]), float(center[1]) - float(tangent[1])))
    m0 = tangent
    m1 = (m0[0] + chord_unit[0] * marker, m0[1] + chord_unit[1] * marker)
    m2 = (m1[0] + radius_unit[0] * marker, m1[1] + radius_unit[1] * marker)
    m3 = (m0[0] + radius_unit[0] * marker, m0[1] + radius_unit[1] * marker)
    ctx.draw.line([m0, m1, m2, m3], fill=ctx.line_color, width=2)

    for label, point in (("O", center), ("A", left), ("B", right), ("T", tangent)):
        px, py = float(point[0]), float(point[1])
        ctx.draw.ellipse((px - 4.0, py - 4.0, px + 4.0, py + 4.0), fill=ctx.line_color)
        offset = {"O": (0.0, 24.0), "A": (-18.0, -18.0), "B": (18.0, -18.0), "T": (20.0, 20.0)}[label]
        _draw_label(ctx, label, (px + offset[0], py + offset[1]), small=True)

    outer_radius_label = f"R={_fmt_number(problem.outer_radius)}"
    inner_radius_label = f"r={_fmt_number(problem.inner_radius)}"
    chord_label = f"c={_fmt_number(problem.chord_length)}"
    if problem.unknown_measure == "chord_length":
        chord_label = "c=?"
    elif problem.unknown_measure == "inner_radius":
        inner_radius_label = "r=?"
    else:
        raise ValueError(f"unsupported unknown concentric-chord measurement: {problem.unknown_measure}")

    label_bboxes: Dict[str, BBox] = {}
    label_bboxes["outer_radius"] = _draw_dimension(ctx, center, right, outer_radius_label, label_offset=(38.0, 8.0))
    label_bboxes["inner_radius"] = _draw_dimension(ctx, center, tangent, inner_radius_label, label_offset=(-38.0, -4.0))
    label_bboxes["chord"] = _draw_dimension(
        ctx,
        dim_left,
        dim_right,
        chord_label,
        label_offset=(0.0, -18.0),
        color=ctx.accent_color,
    )
    label_bboxes["right_angle"] = _bbox_from_points(
        (tangent, (tangent[0] + marker, tangent[1]), (tangent[0] + marker, tangent[1] + marker), (tangent[0], tangent[1] + marker)),
        width=ctx.width,
        height=ctx.height,
        pad=5.0,
    )

    annotation_keyed_points = {"O": center, "A": left, "B": right, "T": tangent}
    chord_bbox = _bbox_from_points((left, right), width=ctx.width, height=ctx.height, pad=18.0)
    scene_entities = (
        {
            "entity_id": "outer_circle",
            "entity_type": "circle",
            "center": [round(center[0], 3), round(center[1], 3)],
            "radius_px": round(outer_px, 3),
            "radius_units": int(problem.outer_radius),
            "bbox": _bbox_to_list(outer_box),
        },
        {
            "entity_id": "inner_circle",
            "entity_type": "circle",
            "center": [round(center[0], 3), round(center[1], 3)],
            "radius_px": round(inner_px, 3),
            "radius_units": int(problem.inner_radius),
            "bbox": _bbox_to_list(inner_box),
        },
        {
            "entity_id": "outer_chord",
            "entity_type": "segment",
            "endpoints": [[round(left[0], 3), round(left[1], 3)], [round(right[0], 3), round(right[1], 3)]],
            "length_units": int(problem.chord_length),
            "bbox": _bbox_to_list(chord_bbox),
        },
    )
    witness = {
        "formula_family": "concentric_circle_tangent_chord",
        "unknown_measure": str(problem.unknown_measure),
        "outer_radius": int(problem.outer_radius),
        "inner_radius": int(problem.inner_radius),
        "half_chord": int(problem.half_chord),
        "chord_length": int(problem.chord_length),
        "pythagorean_relation": "R^2 = r^2 + (c/2)^2",
        "answer_value": float(problem.answer),
    }
    return RenderedConcentricChordScene(
        image=ctx.image,
        answer=float(problem.answer),
        annotation_roles=tuple(annotation_keyed_points.keys()),
        annotation_keyed_points=dict(annotation_keyed_points),
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map={
            "center": [round(center[0], 3), round(center[1], 3)],
            "outer_radius_px": round(outer_px, 3),
            "inner_radius_px": round(inner_px, 3),
            "chord_endpoints": [[round(left[0], 3), round(left[1], 3)], [round(right[0], 3), round(right[1], 3)]],
            "tangent_point": [round(tangent[0], 3), round(tangent[1], 3)],
            "construction_points": {key: [round(point[0], 3), round(point[1], 3)] for key, point in annotation_keyed_points.items()},
            "label_bboxes": {key: _bbox_to_list(value) for key, value in label_bboxes.items()},
            "coord_space": "pixel",
        },
        witness=witness,
    )


__all__ = [
    "ConcentricChordProblem",
    "DOMAIN",
    "POST_IMAGE_NOISE_DEFAULTS",
    "PYTHAGOREAN_CASES",
    "RenderedConcentricChordScene",
    "SCENE_ID",
    "chord_length_support_values",
    "create_render_context",
    "inner_radius_support_values",
    "make_chord_length_problem",
    "make_inner_radius_problem",
    "render_concentric_chord_scene",
    "select_case_index",
]
