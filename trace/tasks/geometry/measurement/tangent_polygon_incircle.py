"""Incircle tangent-segment measurement tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.background import make_background_canvas
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
from ...shared.text_rendering import load_font
from ..shared.complexity import (
    build_geometry_measurement_complexity,
    clamp_unit_interval,
    normalize_linear,
)
from ..shared.shape_style import (
    extract_background_anchor_colors,
    sample_geometry_shape_style,
)
from ..shared.measurement_rendering import (
    round1 as _round1,
    fmt_measure as _fmt_number,
    bbox_to_list as _bbox_to_list,
    clamp_bbox as _clamp_bbox,
    pad_bbox as _pad_bbox,
    bbox_from_points as _bbox_from_points,
    draw_label as _draw_label,
)

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SCENE_ID = "incircle_tangents"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_tangent_polygon_incircle_v0"

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", TASK_GROUP)

_BACKGROUND_DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "styles": {
        "paper_white": {"kind": "solid", "color": [255, 255, 252]},
        "cool_paper": {"kind": "solid", "color": [248, 252, 255]},
        "warm_paper": {"kind": "solid", "color": [255, 251, 246]},
    },
    "weights": {"paper_white": 1.0, "cool_paper": 1.0, "warm_paper": 1.0},
}

_NOISE_DEFAULTS: Dict[str, Any] = {
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

_TANGENT_PERIMETER_QUERIES: Tuple[str, ...] = (
    "triangle_perimeter_from_tangent_segments",
)
_INCIRCLE_RADIUS_QUERIES: Tuple[str, ...] = ("inradius_from_area_and_tangent_segments",)

_TANGENT_CASES: Tuple[Tuple[int, int, int], ...] = (
    (4, 5, 6),
    (3, 7, 8),
    (5, 9, 10),
    (6, 8, 11),
    (7, 10, 12),
    (8, 11, 14),
    (9, 13, 15),
    (10, 14, 17),
    (11, 16, 18),
    (12, 15, 20),
    (13, 17, 21),
    (14, 19, 23),
)

# Tangent segment lengths from vertices A, B, and C.  Each case has integer
# Heron area, so the shown area label stays clean while the radius answer is
# rounded to one decimal place.
_RADIUS_TANGENT_CASES: Tuple[Tuple[int, int, int], ...] = (
    (5, 5, 8),
    (6, 9, 9),
    (6, 7, 14),
    (8, 8, 9),
    (5, 10, 15),
    (7, 7, 18),
    (4, 16, 16),
    (7, 14, 21),
    (10, 15, 15),
    (8, 21, 21),
    (9, 20, 20),
    (12, 18, 18),
    (16, 16, 18),
    (15, 15, 24),
)


@dataclass
class _RenderContext:
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
class _ResolvedProblem:
    query_id: str
    answer: float
    side_bc: float
    side_ca: float
    side_ab: float
    tangent_a: float
    tangent_b: float
    tangent_c: float
    semiperimeter: float
    area: float
    inradius: float
    query_probabilities: Dict[str, float]
    support_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedIncircleScene:
    image: Image.Image
    answer: float
    evidence_bboxes: Tuple[BBox, ...]
    evidence_roles: Tuple[str, ...]
    label_bboxes: Dict[str, BBox]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]


def _selected_probability_map(
    values: Sequence[int | float], selected: int | float
) -> Dict[str, float]:
    return {
        _fmt_number(value): (1.0 if _round1(value) == _round1(selected) else 0.0)
        for value in values
    }


def _triangle_area(side_a: float, side_b: float, side_c: float) -> float:
    semiperimeter = (float(side_a) + float(side_b) + float(side_c)) / 2.0
    area_sq = (
        semiperimeter
        * (semiperimeter - float(side_a))
        * (semiperimeter - float(side_b))
        * (semiperimeter - float(side_c))
    )
    return math.sqrt(max(0.0, float(area_sq)))


def _problem_from_tangents(
    tangent_a: float, tangent_b: float, tangent_c: float
) -> tuple[float, float, float, float, float]:
    side_ab = float(tangent_a) + float(tangent_b)
    side_bc = float(tangent_b) + float(tangent_c)
    side_ca = float(tangent_c) + float(tangent_a)
    semiperimeter = float(tangent_a) + float(tangent_b) + float(tangent_c)
    area = _triangle_area(side_bc, side_ca, side_ab)
    return side_bc, side_ca, side_ab, semiperimeter, area


def _resolve_problem(
    *,
    task_id: str,
    supported_queries: Sequence[str],
    instance_seed: int,
    params: Mapping[str, Any],
) -> _ResolvedProblem:
    explicit_query_raw = params.get("query_id")
    if explicit_query_raw is not None:
        query_id = str(explicit_query_raw)
        if query_id not in set(supported_queries):
            raise ValueError(f"unsupported query_id for {task_id}: {query_id}")
        query_probabilities = {query_id: 1.0}
    else:
        query_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.query_id",
        )
        query_id = str(
            tuple(supported_queries)[int(query_index) % len(tuple(supported_queries))]
        )
        query_probabilities = {
            str(value): 1.0 / float(len(tuple(supported_queries)))
            for value in tuple(supported_queries)
        }

    case_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.{query_id}.case",
    )
    if query_id == "triangle_perimeter_from_tangent_segments":
        tangent_a, tangent_b, tangent_c = _TANGENT_CASES[
            int(case_index) % len(_TANGENT_CASES)
        ]
        tangent_a = float(params.get("tangent_a", tangent_a))
        tangent_b = float(params.get("tangent_b", tangent_b))
        tangent_c = float(params.get("tangent_c", tangent_c))
        side_bc, side_ca, side_ab, semiperimeter, area = _problem_from_tangents(
            tangent_a, tangent_b, tangent_c
        )
        answer = 2.0 * semiperimeter
        support_values = tuple(2 * sum(case) for case in _TANGENT_CASES)
    elif query_id == "inradius_from_area_and_tangent_segments":
        tangent_a, tangent_b, tangent_c = _RADIUS_TANGENT_CASES[
            int(case_index) % len(_RADIUS_TANGENT_CASES)
        ]
        tangent_a = float(params.get("tangent_a", tangent_a))
        tangent_b = float(params.get("tangent_b", tangent_b))
        tangent_c = float(params.get("tangent_c", tangent_c))
        side_bc, side_ca, side_ab, semiperimeter, area = _problem_from_tangents(
            tangent_a, tangent_b, tangent_c
        )
        area = float(params.get("area", area))
        answer = area / semiperimeter
        support_values = tuple(
            _round1(_problem_from_tangents(*case)[4] / sum(case))
            for case in _RADIUS_TANGENT_CASES
        )
    else:
        raise ValueError(f"unsupported incircle query_id: {query_id}")

    if min(side_bc, side_ca, side_ab, tangent_a, tangent_b, tangent_c) <= 0:
        raise ValueError("incircle triangle measurements must be positive")
    inradius = float(area) / float(semiperimeter)
    return _ResolvedProblem(
        query_id=str(query_id),
        answer=_round1(answer),
        side_bc=float(side_bc),
        side_ca=float(side_ca),
        side_ab=float(side_ab),
        tangent_a=float(tangent_a),
        tangent_b=float(tangent_b),
        tangent_c=float(tangent_c),
        semiperimeter=float(semiperimeter),
        area=float(area),
        inradius=float(inradius),
        query_probabilities=dict(query_probabilities),
        support_probabilities=_selected_probability_map(
            tuple(sorted(set(support_values))), _round1(answer)
        ),
    )


def _triangle_layout(problem: _ResolvedProblem) -> Dict[str, Point | float]:
    side_bc = float(problem.side_bc)
    side_ca = float(problem.side_ca)
    side_ab = float(problem.side_ab)
    ax, ay = 0.0, 0.0
    bx, by = side_ab, 0.0
    cx = (side_ca * side_ca + side_ab * side_ab - side_bc * side_bc) / (2.0 * side_ab)
    cy = math.sqrt(max(0.0, side_ca * side_ca - cx * cx))
    a = (ax, ay)
    b = (bx, by)
    c = (cx, cy)
    perimeter = side_bc + side_ca + side_ab
    incenter = (
        (side_bc * ax + side_ca * bx + side_ab * cx) / perimeter,
        (side_bc * ay + side_ca * by + side_ab * cy) / perimeter,
    )
    d = (float(problem.tangent_a), 0.0)
    e = (
        bx + (cx - bx) * (float(problem.tangent_b) / side_bc),
        by + (cy - by) * (float(problem.tangent_b) / side_bc),
    )
    f = (
        ax + (cx - ax) * (float(problem.tangent_a) / side_ca),
        ay + (cy - ay) * (float(problem.tangent_a) / side_ca),
    )
    return {
        "A": a,
        "B": b,
        "C": c,
        "D": d,
        "E": e,
        "F": f,
        "O": incenter,
        "inradius": float(problem.inradius),
    }


def _transform_layout(
    layout: Mapping[str, Point | float], ctx: _RenderContext
) -> Dict[str, Point | float]:
    points = [layout[key] for key in ("A", "B", "C")]
    xs = [float(point[0]) for point in points if isinstance(point, tuple)]
    ys = [float(point[1]) for point in points if isinstance(point, tuple)]
    margin_x = 112.0
    margin_top = 86.0
    margin_bottom = 98.0
    scale = min(
        (float(ctx.width) - 2.0 * margin_x) / max(1.0, max(xs) - min(xs)),
        (float(ctx.height) - margin_top - margin_bottom) / max(1.0, max(ys) - min(ys)),
    )
    left = (float(ctx.width) - (max(xs) - min(xs)) * scale) / 2.0
    bottom = float(ctx.height) - margin_bottom

    def tx(point: Point) -> Point:
        return (
            left + (float(point[0]) - min(xs)) * scale,
            bottom - (float(point[1]) - min(ys)) * scale,
        )

    transformed: Dict[str, Point | float] = {}
    for key, value in layout.items():
        if isinstance(value, tuple):
            transformed[key] = tx(value)
        else:
            transformed[key] = float(value) * scale
    return transformed


def _unit_vector(start: Point, end: Point) -> Point:
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = math.hypot(dx, dy)
    if length <= 1e-9:
        return (0.0, -1.0)
    return (dx / length, dy / length)


def _side_label_position(
    start: Point, end: Point, interior: Point, offset: float
) -> Point:
    mid = (
        (float(start[0]) + float(end[0])) / 2.0,
        (float(start[1]) + float(end[1])) / 2.0,
    )
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    normals = ((-dy, dx), (dy, -dx))
    best = normals[0]
    best_dist = -1.0
    for normal in normals:
        length = math.hypot(normal[0], normal[1]) or 1.0
        candidate = (
            mid[0] + normal[0] / length * offset,
            mid[1] + normal[1] / length * offset,
        )
        dist = math.hypot(
            candidate[0] - float(interior[0]), candidate[1] - float(interior[1])
        )
        if dist > best_dist:
            best = normal
            best_dist = dist
    norm_len = math.hypot(best[0], best[1]) or 1.0
    return (mid[0] + best[0] / norm_len * offset, mid[1] + best[1] / norm_len * offset)


def _draw_tick(
    ctx: _RenderContext, start: Point, end: Point, *, count: int, color: Color
) -> None:
    ux, uy = _unit_vector(start, end)
    nx, ny = -uy, ux
    mid = (
        (float(start[0]) + float(end[0])) / 2.0,
        (float(start[1]) + float(end[1])) / 2.0,
    )
    spacing = 5.0
    for index in range(int(count)):
        shift = (float(index) - (float(count) - 1.0) / 2.0) * spacing
        cx = mid[0] + ux * shift
        cy = mid[1] + uy * shift
        ctx.draw.line(
            [(cx - nx * 7.0, cy - ny * 7.0), (cx + nx * 7.0, cy + ny * 7.0)],
            fill=color,
            width=2,
        )


def _render_incircle_scene(
    ctx: _RenderContext, problem: _ResolvedProblem
) -> _RenderedIncircleScene:
    raw_layout = _triangle_layout(problem)
    layout = _transform_layout(raw_layout, ctx)
    a = layout["A"]
    b = layout["B"]
    c = layout["C"]
    d = layout["D"]
    e = layout["E"]
    f = layout["F"]
    o = layout["O"]
    inradius_px = float(layout["inradius"])
    assert isinstance(a, tuple) and isinstance(b, tuple) and isinstance(c, tuple)
    assert isinstance(d, tuple) and isinstance(e, tuple) and isinstance(f, tuple)
    assert isinstance(o, tuple)

    triangle_points = [a, b, c]
    ctx.draw.polygon(triangle_points, fill=ctx.fill_color)
    ctx.draw.line(
        [a, b, c, a], fill=ctx.line_color, width=ctx.line_width, joint="curve"
    )
    ctx.draw.ellipse(
        (
            o[0] - inradius_px,
            o[1] - inradius_px,
            o[0] + inradius_px,
            o[1] + inradius_px,
        ),
        outline=ctx.accent_color,
        width=max(2, ctx.line_width - 1),
    )
    for point in (d, e, f):
        ctx.draw.ellipse(
            (point[0] - 4.0, point[1] - 4.0, point[0] + 4.0, point[1] + 4.0),
            fill=ctx.accent_color,
        )
    for label, point, offset in (
        ("A", a, (-20.0, 22.0)),
        ("B", b, (20.0, 22.0)),
        ("C", c, (0.0, -24.0)),
        ("O", o, (0.0, 23.0)),
    ):
        ctx.draw.ellipse(
            (point[0] - 3.5, point[1] - 3.5, point[0] + 3.5, point[1] + 3.5),
            fill=ctx.line_color,
        )
        _draw_label(
            ctx, label, (point[0] + offset[0], point[1] + offset[1]), small=True
        )

    _draw_tick(ctx, a, d, count=1, color=ctx.accent_color)
    _draw_tick(ctx, a, f, count=1, color=ctx.accent_color)
    _draw_tick(ctx, b, d, count=2, color=ctx.accent_color)
    _draw_tick(ctx, b, e, count=2, color=ctx.accent_color)
    _draw_tick(ctx, c, e, count=3, color=ctx.accent_color)
    _draw_tick(ctx, c, f, count=3, color=ctx.accent_color)

    label_bboxes: Dict[str, BBox] = {}
    if problem.query_id == "triangle_perimeter_from_tangent_segments":
        label_bboxes["tangent_a"] = _draw_label(
            ctx,
            f"AD=AF={_fmt_number(problem.tangent_a)}",
            (a[0] - 4.0, a[1] + 54.0),
            small=True,
        )
        label_bboxes["tangent_b"] = _draw_label(
            ctx,
            f"BD=BE={_fmt_number(problem.tangent_b)}",
            (b[0] + 8.0, b[1] + 54.0),
            small=True,
        )
        label_bboxes["tangent_c"] = _draw_label(
            ctx,
            f"CE=CF={_fmt_number(problem.tangent_c)}",
            (c[0], c[1] - 52.0),
            small=True,
        )
        label_bboxes["unknown_perimeter"] = _draw_label(
            ctx, "P=?", (o[0], o[1] - 62.0), small=True
        )
        evidence_roles = ("tangent_a_label", "tangent_b_label", "tangent_c_label")
        evidence_bboxes = (
            label_bboxes["tangent_a"],
            label_bboxes["tangent_b"],
            label_bboxes["tangent_c"],
        )
    elif problem.query_id == "inradius_from_area_and_tangent_segments":
        label_bboxes["tangent_a"] = _draw_label(
            ctx,
            f"AD=AF={_fmt_number(problem.tangent_a)}",
            (a[0] - 4.0, a[1] + 54.0),
            small=True,
        )
        label_bboxes["tangent_b"] = _draw_label(
            ctx,
            f"BD=BE={_fmt_number(problem.tangent_b)}",
            (b[0] + 8.0, b[1] + 54.0),
            small=True,
        )
        label_bboxes["tangent_c"] = _draw_label(
            ctx,
            f"CE=CF={_fmt_number(problem.tangent_c)}",
            (c[0], c[1] - 52.0),
            small=True,
        )
        label_bboxes["area"] = _draw_label(
            ctx, f"Area={_fmt_number(problem.area)}", (596.0, 96.0), small=True
        )
        ctx.draw.line([o, d], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        label_bboxes["unknown_radius"] = _draw_label(
            ctx, "r=?", ((o[0] + d[0]) / 2.0 - 28.0, (o[1] + d[1]) / 2.0), small=True
        )
        evidence_roles = (
            "tangent_a_label",
            "tangent_b_label",
            "tangent_c_label",
            "area_label",
        )
        evidence_bboxes = (
            label_bboxes["tangent_a"],
            label_bboxes["tangent_b"],
            label_bboxes["tangent_c"],
            label_bboxes["area"],
        )
    else:
        raise ValueError(f"unsupported incircle query_id: {problem.query_id}")

    triangle_bbox = _bbox_from_points(
        (a, b, c), width=ctx.width, height=ctx.height, pad=10.0
    )
    incircle_bbox = _pad_bbox(
        (
            o[0] - inradius_px,
            o[1] - inradius_px,
            o[0] + inradius_px,
            o[1] + inradius_px,
        ),
        6.0,
        width=ctx.width,
        height=ctx.height,
    )
    scene_entities = (
        {
            "entity_id": "triangle_ABC",
            "entity_type": "triangle",
            "vertices": {
                "A": [round(a[0], 3), round(a[1], 3)],
                "B": [round(b[0], 3), round(b[1], 3)],
                "C": [round(c[0], 3), round(c[1], 3)],
            },
            "side_lengths": {
                "AB": _round1(problem.side_ab),
                "BC": _round1(problem.side_bc),
                "CA": _round1(problem.side_ca),
            },
            "bbox": _bbox_to_list(triangle_bbox),
        },
        {
            "entity_id": "incircle",
            "entity_type": "circle",
            "center": [round(o[0], 3), round(o[1], 3)],
            "radius_px": round(inradius_px, 3),
            "radius_units": _round1(problem.inradius),
            "bbox": _bbox_to_list(incircle_bbox),
        },
    )
    witness = {
        "formula_family": str(problem.query_id),
        "side_ab": _round1(problem.side_ab),
        "side_bc": _round1(problem.side_bc),
        "side_ca": _round1(problem.side_ca),
        "tangent_a": _round1(problem.tangent_a),
        "tangent_b": _round1(problem.tangent_b),
        "tangent_c": _round1(problem.tangent_c),
        "semiperimeter": _round1(problem.semiperimeter),
        "area": _round1(problem.area),
        "inradius": _round1(problem.inradius),
        "answer_value": float(problem.answer),
    }
    return _RenderedIncircleScene(
        image=ctx.image,
        answer=float(problem.answer),
        evidence_bboxes=tuple(evidence_bboxes),
        evidence_roles=tuple(evidence_roles),
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map={
            "points": {
                key: [round(value[0], 3), round(value[1], 3)]
                for key, value in layout.items()
                if isinstance(value, tuple)
            },
            "incircle_radius_px": round(inradius_px, 3),
            "label_bboxes": {
                key: _bbox_to_list(value) for key, value in label_bboxes.items()
            },
            "coord_space": "pixel",
        },
        witness=witness,
    )


class _TangentPolygonIncircleBaseTask:
    """Shared implementation for incircle tangent-segment tasks."""

    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    public_scene_id = SCENE_ID
    supported_queries: Sequence[str] = ()
    reasoning_kind = "tangent_polygon_incircle"

    def _make_render_context(
        self,
        *,
        instance_seed: int,
        params: Mapping[str, Any],
        render_defaults: Mapping[str, Any],
    ) -> tuple[_RenderContext, Dict[str, Any]]:
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.render")
        width = int(
            params.get(
                "canvas_width", group_default(render_defaults, "canvas_width", 760)
            )
        )
        height = int(
            params.get(
                "canvas_height", group_default(render_defaults, "canvas_height", 560)
            )
        )
        image, background_meta = make_background_canvas(
            canvas_width=int(width),
            canvas_height=int(height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=_BACKGROUND_DEFAULTS,
            fallback_color=(255, 255, 252),
        )
        shape_style = sample_geometry_shape_style(
            rng,
            params=params,
            render_defaults=render_defaults,
            anchor_colors=extract_background_anchor_colors(background_meta),
        )
        accents: Tuple[Color, ...] = (
            (27, 113, 191),
            (189, 91, 37),
            (111, 92, 190),
            (30, 132, 92),
        )
        accent_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.accent",
        )
        accent_color = accents[int(accent_index) % len(accents)]
        fill_color = (
            min(255, int(accent_color[0] * 0.18 + 255 * 0.82)),
            min(255, int(accent_color[1] * 0.18 + 255 * 0.82)),
            min(255, int(accent_color[2] * 0.18 + 255 * 0.82)),
        )
        font_size = int(
            params.get(
                "label_font_size", group_default(render_defaults, "label_font_size", 22)
            )
        )
        small_font_size = int(
            params.get(
                "small_label_font_size",
                group_default(render_defaults, "small_label_font_size", 18),
            )
        )
        line_width = int(
            params.get("line_width", group_default(render_defaults, "line_width", 4))
        )
        ctx = _RenderContext(
            rng=rng,
            image=image,
            draw=ImageDraw.Draw(image),
            width=int(width),
            height=int(height),
            line_color=shape_style.line_color,
            label_color=shape_style.label_color,
            label_stroke_color=shape_style.label_stroke_color,
            accent_color=accent_color,
            fill_color=fill_color,
            line_width=max(2, int(line_width)),
            font=load_font(max(12, int(font_size)), bold=True),
            small_font=load_font(max(10, int(small_font_size)), bold=True),
        )
        render_meta = {
            "background_style": dict(background_meta),
            "shape_style": shape_style.to_trace_dict(),
            "line_width": int(ctx.line_width),
            "label_font_size": int(font_size),
            "small_label_font_size": int(small_font_size),
            "accent_color": list(accent_color),
            "fill_color": list(fill_color),
        }
        return ctx, render_meta

    def _build_complexity(self, rendered: _RenderedIncircleScene) -> TaskComplexity:
        visual_scan = clamp_unit_interval(
            0.38
            + normalize_linear(len(rendered.evidence_bboxes), min_value=3, max_value=5)
            * 0.18
        )
        precision = 0.64 if self.reasoning_kind == "incircle_perimeter" else 0.74
        ambiguity = 0.44 if self.reasoning_kind == "incircle_perimeter" else 0.52
        output_burden = clamp_unit_interval(
            0.45
            + normalize_linear(len(rendered.evidence_bboxes), min_value=3, max_value=5)
            * 0.12
        )
        return build_geometry_measurement_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
            visual_scan=float(visual_scan),
            measurement_precision=float(precision),
            ambiguity=float(ambiguity),
            output_burden=float(output_burden),
        )

    def generate(
        self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int
    ) -> TaskOutput:
        if not self.supported_queries:
            raise ValueError(f"{self.task_id} defines no incircle query support")
        _gen_defaults, render_defaults, prompt_defaults = (
            split_generation_rendering_prompt_defaults(
                _TASK_GROUP_DEFAULTS,
                task_id=str(self.task_id),
            )
        )
        problem = _resolve_problem(
            task_id=str(self.task_id),
            supported_queries=tuple(self.supported_queries),
            instance_seed=int(instance_seed),
            params=params,
        )
        last_error: Exception | None = None
        rendered: _RenderedIncircleScene | None = None
        render_meta: Dict[str, Any] | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                ctx, render_meta_attempt = self._make_render_context(
                    instance_seed=int(instance_seed),
                    params=params,
                    render_defaults=render_defaults,
                )
                rendered = _render_incircle_scene(ctx, problem)
                render_meta = dict(render_meta_attempt)
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
            default_config=_NOISE_DEFAULTS,
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
                "answer_hint_number",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(problem.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(
                    prompt_defaults["json_output_contract_answer_only"]
                ),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint_number"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(
                    prompt_defaults["json_example_answer_only"]
                ),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_bboxes = [_bbox_to_list(bbox) for bbox in rendered.evidence_bboxes]
        evidence_points = [
            [
                round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
                round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
            ]
            for bbox in evidence_bboxes
        ]
        answer_gt = TypedValue(type="number", value=float(rendered.answer))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        query_params = {
            "scene_id": SCENE_ID,
            "scene_variant": "triangle_incircle",
            "query_id": str(problem.query_id),
            "query_id_probabilities": dict(problem.query_probabilities),
            "variant_probabilities": {"default": 1.0},
            "target_support_probabilities": dict(problem.support_probabilities),
            **dict(rendered.witness),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_tangent_polygon_incircle",
                "scene_id": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_id": str(problem.query_id),
                    "scene_variant": "triangle_incircle",
                    "answer_value": float(rendered.answer),
                    "evidence_roles": list(rendered.evidence_roles),
                },
            },
            "query_spec": {
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(
                    prompt_artifacts.prompt_variant_active_key
                ),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_size": [int(image.size[0]), int(image.size[1])],
                "coord_space": "pixel",
                "post_image_noise": dict(noise_meta),
                **dict(render_meta),
            },
            "render_map": {"coord_space": "pixel", **dict(rendered.render_map)},
            "execution_trace": {
                "scene_id": SCENE_ID,
                "scene_variant": "triangle_incircle",
                "query_id": str(problem.query_id),
                "query_id_probabilities": dict(problem.query_probabilities),
                "answer_type": "number",
                "answer_value": float(rendered.answer),
                "answer_rounding": "nearest_tenth",
                "evidence_roles": list(rendered.evidence_roles),
                "reasoning_steps": 2 if "radius" in str(problem.query_id) else 1,
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "type": "tangent_polygon_incircle_formula",
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "answer_value": float(rendered.answer),
                "source_witness_type": "bbox_set",
                "original_evidence_value": list(rendered.evidence_roles),
                **dict(rendered.witness),
            },
            "projected_evidence": {
                "type": "bbox_set",
                "bbox_set": list(evidence_bboxes),
                "pixel_bbox_set": list(evidence_bboxes),
                "point_set": list(evidence_points),
                "pixel_point_set": list(evidence_points),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=self._build_complexity(rendered),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometryIncircleTangentPerimeterValueTask(_TangentPolygonIncircleBaseTask):
    """Compute triangle perimeter from equal tangent segment labels."""

    task_id = "task_geometry__incircle_tangents__incircle_tangent_perimeter_value"
    supported_queries = _TANGENT_PERIMETER_QUERIES
    reasoning_kind = "incircle_perimeter"


@register_task
class GeometryIncircleRadiusFromAreaValueTask(_TangentPolygonIncircleBaseTask):
    """Compute incircle radius from triangle side lengths and area."""

    task_id = "task_geometry__incircle_tangents__incircle_radius_from_area_value"
    supported_queries = _INCIRCLE_RADIUS_QUERIES
    reasoning_kind = "incircle_radius"


__all__ = [
    "GeometryIncircleRadiusFromAreaValueTask",
    "GeometryIncircleTangentPerimeterValueTask",
    "SCENE_ID",
]
