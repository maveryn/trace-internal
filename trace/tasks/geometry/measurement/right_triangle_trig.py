"""Right-triangle trigonometry measurement tasks."""

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
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font
from ..shared.complexity import build_geometry_measurement_complexity, clamp_unit_interval, normalize_linear
from ..shared.shape_style import extract_background_anchor_colors, sample_geometry_shape_style
from ..shared.measurement_rendering import (
    round1 as _round1,
    fmt_measure as _fmt_measure,
    bbox_to_list as _bbox_to_list,
    clamp_bbox as _clamp_bbox,
    pad_bbox as _pad_bbox,
    bbox_from_points as _bbox_from_points,
    draw_label as _draw_label,
)

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SCENE_ID = "triangle_relations"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_right_triangle_trig_v0"

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", TASK_GROUP)

_BACKGROUND_DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "styles": {
        "paper_white": {"kind": "solid", "color": [255, 255, 252]},
        "cool_paper": {"kind": "solid", "color": [248, 252, 255]},
        "warm_paper": {"kind": "solid", "color": [255, 252, 246]},
        "field_pale": {"kind": "solid", "color": [249, 254, 249]},
    },
    "weights": {
        "paper_white": 1.0,
        "cool_paper": 1.0,
        "warm_paper": 1.0,
        "field_pale": 1.0,
    },
}

_NOISE_DEFAULTS: Dict[str, Any] = {
    "apply_prob": 0.5,
    "edit_types": ["blur", "downsample", "jpeg", "noise"],
    "edit_count_range": [1, 1],
    "value_ranges": {
        "blur": {"radius": [0.10, 0.28]},
        "downsample": {"scale": [0.94, 0.99]},
        "jpeg": {"quality": [86, 95]},
        "noise": {"alpha": [0.01, 0.025]},
    },
}

_MISSING_SIDE_QUERIES: Tuple[str, ...] = (
    "height_from_angle_and_ground",
    "ground_from_angle_and_height",
    "hypotenuse_from_angle_and_height",
    "height_from_angle_and_hypotenuse",
    "ground_from_angle_and_hypotenuse",
)
_ANGLE_QUERIES: Tuple[str, ...] = (
    "angle_from_opposite_adjacent",
    "angle_from_opposite_hypotenuse",
    "angle_from_adjacent_hypotenuse",
    "angle_of_elevation_from_height_and_distance",
)

_TRIPLES: Tuple[Tuple[int, int, int], ...] = (
    (11, 60, 61),
    (60, 11, 61),
    (12, 5, 13),
    (20, 21, 29),
    (80, 39, 89),
    (9, 40, 41),
    (40, 9, 41),
    (15, 8, 17),
    (8, 15, 17),
    (21, 20, 29),
    (56, 33, 65),
    (33, 56, 65),
    (63, 16, 65),
    (16, 63, 65),
    (39, 80, 89),
    (48, 55, 73),
    (65, 72, 97),
    (72, 65, 97),
    (85, 132, 157),
    (132, 85, 157),
)
_ANGLE_SUPPORT: Tuple[int, ...] = (25, 30, 35, 40, 45, 50, 55, 60, 65)
_KNOWN_SIDE_SUPPORT: Tuple[int, ...] = (8, 10, 12, 14, 16, 18, 20, 24, 28)
_CONTEXT_STYLES: Tuple[str, ...] = ("ramp", "flagpole", "ladder", "survey")


@dataclass
class _RenderContext:
    rng: Any
    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    background_color: Color
    line_color: Color
    label_color: Color
    label_stroke_color: Color
    fill_color: Color
    secondary_fill_color: Color
    accent_color: Color
    line_width: int
    font: Any
    small_font: Any


@dataclass(frozen=True)
class _ResolvedProblem:
    query_id: str
    scene_variant: str
    answer: float
    params: Dict[str, Any]
    query_probabilities: Dict[str, float]
    support_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedRightTriangleScene:
    image: Image.Image
    answer: float
    query_id: str
    scene_variant: str
    evidence_bboxes: Tuple[BBox, ...]
    evidence_roles: Tuple[str, ...]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]
    reasoning_steps: int


def _draw_dimension(
    ctx: _RenderContext,
    start: Point,
    end: Point,
    label: str,
    *,
    label_offset: Point = (0.0, 0.0),
) -> BBox:
    ctx.draw.line([start, end], fill=ctx.label_color, width=max(2, ctx.line_width - 1))
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
                fill=ctx.label_color,
                width=max(2, ctx.line_width - 1),
            )
    center = (
        (float(start[0]) + float(end[0])) / 2.0 + float(label_offset[0]),
        (float(start[1]) + float(end[1])) / 2.0 + float(label_offset[1]),
    )
    return _draw_label(ctx, label, center, small=True)


def _selected_probability_map(values: Sequence[int], selected: int | float) -> Dict[str, float]:
    return {str(value): (1.0 if float(value) == float(selected) else 0.0) for value in values}


def _cycle_index(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    query_count: int,
    explicit_query: bool,
) -> int:
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    return int(index)


def _resolve_problem(
    *,
    task_id: str,
    supported_queries: Sequence[str],
    instance_seed: int,
    params: Mapping[str, Any],
) -> _ResolvedProblem:
    explicit_query_raw = params.get("query_id")
    explicit_query = explicit_query_raw is not None
    if explicit_query:
        query_id = str(explicit_query_raw)
        if query_id not in set(supported_queries):
            raise ValueError(f"unsupported query_id for {task_id}: {query_id}")
        query_probabilities = {query_id: 1.0}
    else:
        query_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.query_id")
        query_id = str(tuple(supported_queries)[int(query_index) % len(tuple(supported_queries))])
        query_probabilities = {str(value): 1.0 / float(len(tuple(supported_queries))) for value in tuple(supported_queries)}

    index = _cycle_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.{query_id}.values",
        query_count=len(tuple(supported_queries)),
        explicit_query=bool(explicit_query),
    )
    context_style = str(params.get("context_style", _CONTEXT_STYLES[int(index) % len(_CONTEXT_STYLES)]))
    if context_style not in set(_CONTEXT_STYLES):
        raise ValueError(f"unsupported context_style for {task_id}: {context_style}")

    if query_id in _ANGLE_QUERIES:
        adjacent_units, opposite_units, hypotenuse_units = _TRIPLES[(int(index) // len(_CONTEXT_STYLES)) % len(_TRIPLES)]
        theta_degrees = math.degrees(math.atan2(float(opposite_units), float(adjacent_units)))
    else:
        theta_values = _ANGLE_SUPPORT
        side_values = _KNOWN_SIDE_SUPPORT
        theta_degrees = float(params.get("theta_degrees", theta_values[(int(index) // len(_CONTEXT_STYLES)) % len(theta_values)]))
        known_side = float(params.get("known_side_units", side_values[(int(index) // (len(_CONTEXT_STYLES) * len(theta_values))) % len(side_values)]))
        radians = math.radians(theta_degrees)
        if query_id == "height_from_angle_and_ground":
            adjacent_units = known_side
            opposite_units = known_side * math.tan(radians)
            hypotenuse_units = math.hypot(adjacent_units, opposite_units)
        elif query_id == "ground_from_angle_and_height":
            opposite_units = known_side
            adjacent_units = known_side / math.tan(radians)
            hypotenuse_units = math.hypot(adjacent_units, opposite_units)
        elif query_id == "hypotenuse_from_angle_and_height":
            opposite_units = known_side
            hypotenuse_units = known_side / math.sin(radians)
            adjacent_units = math.sqrt(max(0.0, hypotenuse_units**2 - opposite_units**2))
        elif query_id == "height_from_angle_and_hypotenuse":
            hypotenuse_units = known_side
            opposite_units = known_side * math.sin(radians)
            adjacent_units = known_side * math.cos(radians)
        elif query_id == "ground_from_angle_and_hypotenuse":
            hypotenuse_units = known_side
            adjacent_units = known_side * math.cos(radians)
            opposite_units = known_side * math.sin(radians)
        else:
            raise ValueError(f"unsupported missing-side query_id: {query_id}")

    adjacent_units = float(params.get("adjacent_units", adjacent_units))
    opposite_units = float(params.get("opposite_units", opposite_units))
    hypotenuse_units = float(params.get("hypotenuse_units", hypotenuse_units))
    theta_degrees = float(params.get("theta_degrees", theta_degrees))

    if query_id == "height_from_angle_and_ground":
        answer = opposite_units
        formula_family = "height_from_tangent"
        requested_value = "height"
        visible_sides = ("adjacent",)
        target_role = "opposite_side_cue"
        reasoning_steps = 1
    elif query_id == "ground_from_angle_and_height":
        answer = adjacent_units
        formula_family = "ground_from_tangent"
        requested_value = "ground"
        visible_sides = ("opposite",)
        target_role = "adjacent_side_cue"
        reasoning_steps = 1
    elif query_id == "hypotenuse_from_angle_and_height":
        answer = hypotenuse_units
        formula_family = "hypotenuse_from_sine"
        requested_value = "hypotenuse"
        visible_sides = ("opposite",)
        target_role = "hypotenuse_side_cue"
        reasoning_steps = 1
    elif query_id == "height_from_angle_and_hypotenuse":
        answer = opposite_units
        formula_family = "height_from_sine"
        requested_value = "height"
        visible_sides = ("hypotenuse",)
        target_role = "opposite_side_cue"
        reasoning_steps = 1
    elif query_id == "ground_from_angle_and_hypotenuse":
        answer = adjacent_units
        formula_family = "ground_from_cosine"
        requested_value = "ground"
        visible_sides = ("hypotenuse",)
        target_role = "adjacent_side_cue"
        reasoning_steps = 1
    elif query_id == "angle_from_opposite_adjacent":
        answer = math.degrees(math.atan2(opposite_units, adjacent_units))
        formula_family = "angle_from_tangent"
        requested_value = "angle"
        visible_sides = ("opposite", "adjacent")
        target_role = "target_angle_cue"
        reasoning_steps = 1
    elif query_id == "angle_from_opposite_hypotenuse":
        answer = math.degrees(math.asin(opposite_units / hypotenuse_units))
        formula_family = "angle_from_sine"
        requested_value = "angle"
        visible_sides = ("opposite", "hypotenuse")
        target_role = "target_angle_cue"
        reasoning_steps = 1
    elif query_id == "angle_from_adjacent_hypotenuse":
        answer = math.degrees(math.acos(adjacent_units / hypotenuse_units))
        formula_family = "angle_from_cosine"
        requested_value = "angle"
        visible_sides = ("adjacent", "hypotenuse")
        target_role = "target_angle_cue"
        reasoning_steps = 1
    elif query_id == "angle_of_elevation_from_height_and_distance":
        answer = math.degrees(math.atan2(opposite_units, adjacent_units))
        formula_family = "angle_of_elevation_from_tangent"
        requested_value = "angle_of_elevation"
        visible_sides = ("opposite", "adjacent")
        target_role = "target_angle_cue"
        context_style = "flagpole"
        reasoning_steps = 1
    else:
        raise ValueError(f"unsupported right-triangle query_id: {query_id}")

    if query_id in _ANGLE_QUERIES:
        scene_variant = f"{context_style}_angle"
        support_values: Sequence[int] = tuple(int(round(math.degrees(math.atan2(opposite, adjacent)))) for adjacent, opposite, _hyp in _TRIPLES)
        support_selected = int(round(answer))
    else:
        scene_variant = f"{context_style}_missing_side"
        support_values = _ANGLE_SUPPORT
        support_selected = int(round(theta_degrees))

    return _ResolvedProblem(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        answer=float(_round1(answer)),
        params={
            "adjacent_units": float(adjacent_units),
            "opposite_units": float(opposite_units),
            "hypotenuse_units": float(hypotenuse_units),
            "theta_degrees": float(theta_degrees),
            "context_style": str(context_style),
            "visible_sides": [str(value) for value in visible_sides],
            "target_role": str(target_role),
            "requested_value": str(requested_value),
            "answer_value": float(_round1(answer)),
            "formula_family": str(formula_family),
            "reasoning_steps": int(reasoning_steps),
        },
        query_probabilities=dict(query_probabilities),
        support_probabilities=_selected_probability_map(support_values, support_selected),
    )


def _side_label(side: str, problem: _ResolvedProblem, *, unknown: bool = False) -> str:
    values = dict(problem.params)
    style = str(values["context_style"])
    names = {
        "adjacent": "ground" if style in {"ramp", "flagpole", "survey"} else "floor",
        "opposite": "height" if style in {"ramp", "flagpole", "survey"} else "wall",
        "hypotenuse": "slope" if style == "ramp" else ("line" if style in {"flagpole", "survey"} else "ladder"),
    }
    if unknown:
        return f"{names[side]}=?"
    value_key = {"adjacent": "adjacent_units", "opposite": "opposite_units", "hypotenuse": "hypotenuse_units"}[side]
    return f"{names[side]}={_fmt_measure(values[value_key])}"


def _draw_angle_cue(ctx: _RenderContext, origin: Point, theta_degrees: float, label: str) -> BBox:
    radius = 54.0
    box = (origin[0] - radius, origin[1] - radius, origin[0] + radius, origin[1] + radius)
    ctx.draw.arc(box, start=-float(theta_degrees), end=0.0, fill=ctx.accent_color, width=max(3, ctx.line_width - 1))
    half_angle = -float(theta_degrees) / 2.0
    label_center = (
        float(origin[0]) + 72.0 * math.cos(math.radians(half_angle)),
        float(origin[1]) + 72.0 * math.sin(math.radians(half_angle)),
    )
    return _draw_label(ctx, label, label_center, small=False)


def _draw_context(ctx: _RenderContext, problem: _ResolvedProblem, a: Point, b: Point, c: Point) -> None:
    style = str(problem.params["context_style"])
    if style == "ramp":
        ground_y = float(a[1]) + 20.0
        ctx.draw.line([(float(a[0]) - 72.0, ground_y), (float(c[0]) + 78.0, ground_y)], fill=ctx.secondary_fill_color, width=5)
        ctx.draw.line([a, b], fill=ctx.accent_color, width=ctx.line_width + 4)
    elif style == "flagpole":
        ctx.draw.line([(float(c[0]), float(c[1]) + 18.0), (float(c[0]), float(b[1]) - 26.0)], fill=ctx.accent_color, width=ctx.line_width + 2)
        ctx.draw.polygon([(float(c[0]), float(b[1]) - 28.0), (float(c[0]) + 34.0, float(b[1]) - 18.0), (float(c[0]), float(b[1]) - 8.0)], fill=ctx.secondary_fill_color)
        ctx.draw.line([a, b], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    elif style == "ladder":
        ctx.draw.line([(float(c[0]) + 18.0, float(c[1]) + 18.0), (float(c[0]) + 18.0, float(b[1]) - 34.0)], fill=ctx.secondary_fill_color, width=6)
        ctx.draw.line([a, b], fill=ctx.accent_color, width=ctx.line_width + 3)
        rung_count = 5
        for idx in range(1, rung_count + 1):
            t = idx / float(rung_count + 1)
            x = float(a[0]) + (float(b[0]) - float(a[0])) * t
            y = float(a[1]) + (float(b[1]) - float(a[1])) * t
            ctx.draw.line([(x - 12.0, y + 6.0), (x + 12.0, y - 6.0)], fill=ctx.line_color, width=2)
    else:
        ctx.draw.line([a, b], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        for idx in range(1, 6):
            x = float(a[0]) + (float(c[0]) - float(a[0])) * idx / 6.0
            ctx.draw.line([(x, float(c[1]) - 4.0), (x, float(c[1]) + 4.0)], fill=ctx.secondary_fill_color, width=2)


def _render_right_triangle_scene(ctx: _RenderContext, problem: _ResolvedProblem) -> _RenderedRightTriangleScene:
    values = dict(problem.params)
    adjacent = float(values["adjacent_units"])
    opposite = float(values["opposite_units"])
    hypotenuse = float(values["hypotenuse_units"])
    theta = float(values["theta_degrees"])
    scale = min(420.0 / max(adjacent, 1.0), 270.0 / max(opposite, 1.0))
    base_px = adjacent * scale
    height_px = opposite * scale
    left = 128.0
    bottom = 426.0
    a = (left, bottom)
    c = (left + base_px, bottom)
    b = (left + base_px, bottom - height_px)

    _draw_context(ctx, problem, a, b, c)
    triangle_fill = (*ctx.fill_color[:3], 72) if len(ctx.fill_color) == 3 else ctx.fill_color
    overlay = Image.new("RGBA", ctx.image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.polygon([a, b, c], fill=triangle_fill)
    ctx.image.paste(Image.alpha_composite(ctx.image.convert("RGBA"), overlay).convert("RGB"))
    ctx.draw = ImageDraw.Draw(ctx.image)
    ctx.draw.line([a, c], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([c, b], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([a, b], fill=ctx.line_color, width=ctx.line_width)
    square = 18.0
    ctx.draw.line([(c[0] - square, c[1]), (c[0] - square, c[1] - square), (c[0], c[1] - square)], fill=ctx.line_color, width=max(2, ctx.line_width - 1))

    visible_sides = tuple(str(value) for value in values["visible_sides"])
    target_role = str(values["target_role"])
    label_bboxes: Dict[str, BBox] = {}
    side_roles = {"adjacent": "adjacent_side_label", "opposite": "opposite_side_label", "hypotenuse": "hypotenuse_side_label"}

    def add_side_label(side: str, *, unknown: bool = False) -> None:
        if side == "adjacent":
            bbox = _draw_dimension(ctx, (a[0], a[1] + 28.0), (c[0], c[1] + 28.0), _side_label(side, problem, unknown=unknown), label_offset=(0.0, 16.0))
        elif side == "opposite":
            bbox = _draw_dimension(ctx, (c[0] + 26.0, c[1]), (b[0] + 26.0, b[1]), _side_label(side, problem, unknown=unknown), label_offset=(44.0, 0.0))
        else:
            bbox = _draw_dimension(ctx, a, b, _side_label(side, problem, unknown=unknown), label_offset=(-24.0, -32.0))
        label_bboxes[side] = bbox

    if target_role == "adjacent_side_cue":
        add_side_label("adjacent", unknown=True)
    elif "adjacent" in visible_sides:
        add_side_label("adjacent")
    if target_role == "opposite_side_cue":
        add_side_label("opposite", unknown=True)
    elif "opposite" in visible_sides:
        add_side_label("opposite")
    if target_role == "hypotenuse_side_cue":
        add_side_label("hypotenuse", unknown=True)
    elif "hypotenuse" in visible_sides:
        add_side_label("hypotenuse")

    if str(problem.query_id) in _ANGLE_QUERIES:
        angle_bbox = _draw_angle_cue(ctx, a, theta, "?")
        angle_role = "target_angle_cue"
    else:
        angle_bbox = _draw_angle_cue(ctx, a, theta, f"theta={_fmt_measure(theta)} deg")
        angle_role = "angle_measure_label"

    if str(problem.query_id) in _MISSING_SIDE_QUERIES:
        target_side = {"adjacent_side_cue": "adjacent", "opposite_side_cue": "opposite", "hypotenuse_side_cue": "hypotenuse"}[target_role]
        evidence_roles = (target_role, angle_role, *tuple(side_roles[side] for side in visible_sides))
        evidence_bboxes = (label_bboxes[target_side], angle_bbox, *tuple(label_bboxes[side] for side in visible_sides))
    else:
        evidence_roles = (angle_role, *tuple(side_roles[side] for side in visible_sides))
        evidence_bboxes = (angle_bbox, *tuple(label_bboxes[side] for side in visible_sides))

    triangle_bbox = _bbox_from_points((a, b, c), width=ctx.width, height=ctx.height, pad=8.0)
    scene_entities = (
        {
            "entity_id": "right_triangle",
            "entity_type": "right_triangle",
            "bbox": _bbox_to_list(triangle_bbox),
            "adjacent_units": float(adjacent),
            "opposite_units": float(opposite),
            "hypotenuse_units": float(hypotenuse),
            "theta_degrees": float(theta),
            "context_style": str(values["context_style"]),
        },
    )
    return _RenderedRightTriangleScene(
        image=ctx.image,
        answer=float(problem.answer),
        query_id=str(problem.query_id),
        scene_variant=str(problem.scene_variant),
        evidence_bboxes=tuple(evidence_bboxes),
        evidence_roles=tuple(evidence_roles),
        scene_entities=scene_entities,
        render_map={
            "target_bbox": _bbox_to_list(evidence_bboxes[0]),
            "triangle_bbox": _bbox_to_list(triangle_bbox),
            "support_bboxes": [_bbox_to_list(bbox) for bbox in evidence_bboxes[1:]],
            "vertices": {"angle_vertex": _bbox_to_list(_pad_bbox((a[0], a[1], a[0], a[1]), 3.0, width=ctx.width, height=ctx.height))},
            "coord_space": "pixel",
        },
        witness={
            "formula_family": str(values["formula_family"]),
            **dict(values),
        },
        reasoning_steps=int(values["reasoning_steps"]),
    )


class _RightTriangleTrigBaseTask:
    """Shared implementation for right-triangle trigonometry tasks."""

    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    public_scene_id = SCENE_ID
    supported_queries: Sequence[str] = ()
    reasoning_kind = "right_triangle_trig"

    def _make_render_context(self, *, instance_seed: int, params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> tuple[_RenderContext, Dict[str, Any]]:
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.render")
        width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 760)))
        height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 560)))
        image, background_meta = make_background_canvas(
            canvas_width=int(width),
            canvas_height=int(height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=_BACKGROUND_DEFAULTS,
            fallback_color=(255, 255, 252),
        )
        bg_color = tuple(int(value) for value in background_meta.get("color", [255, 255, 252])[:3])
        shape_style = sample_geometry_shape_style(
            rng,
            params=params,
            render_defaults=render_defaults,
            anchor_colors=extract_background_anchor_colors(background_meta),
        )
        fill_palette: Tuple[Tuple[Color, Color, Color], ...] = (
            ((86, 156, 218), (98, 176, 122), (22, 93, 150)),
            ((226, 136, 92), (90, 157, 198), (150, 70, 28)),
            ((114, 132, 216), (224, 151, 82), (72, 86, 160)),
            ((92, 174, 139), (216, 122, 150), (34, 116, 78)),
        )
        color_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{self.task_id}.fill") % len(fill_palette)
        fill_color, secondary_fill_color, accent_color = fill_palette[int(color_index)]
        font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
        small_font_size = int(params.get("small_label_font_size", group_default(render_defaults, "small_label_font_size", 18)))
        line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 4)))
        ctx = _RenderContext(
            rng=rng,
            image=image,
            draw=ImageDraw.Draw(image),
            width=int(width),
            height=int(height),
            background_color=(int(bg_color[0]), int(bg_color[1]), int(bg_color[2])),
            line_color=shape_style.line_color,
            label_color=shape_style.label_color,
            label_stroke_color=shape_style.label_stroke_color,
            fill_color=fill_color,
            secondary_fill_color=secondary_fill_color,
            accent_color=accent_color,
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
            "fill_color": list(fill_color),
            "secondary_fill_color": list(secondary_fill_color),
            "accent_color": list(accent_color),
        }
        return ctx, render_meta

    def _build_complexity(self, rendered: _RenderedRightTriangleScene) -> TaskComplexity:
        precision = 0.62
        if self.reasoning_kind == "right_triangle_missing_side":
            precision = 0.76
        elif self.reasoning_kind == "right_triangle_angle":
            precision = 0.82
        if rendered.reasoning_steps > 1:
            precision += 0.06
        visual_scan = clamp_unit_interval(0.40 + normalize_linear(len(rendered.evidence_bboxes), min_value=2, max_value=4) * 0.20)
        ambiguity = 0.40 + (0.08 if rendered.reasoning_steps > 1 else 0.0)
        output_burden = clamp_unit_interval(0.44 + normalize_linear(len(rendered.evidence_bboxes), min_value=2, max_value=4) * 0.16)
        return build_geometry_measurement_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
            visual_scan=float(visual_scan),
            measurement_precision=float(min(1.0, precision)),
            ambiguity=float(ambiguity),
            output_burden=float(output_burden),
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        if not self.supported_queries:
            raise ValueError(f"{self.task_id} defines no right-triangle query support")
        _gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
        )
        problem = _resolve_problem(
            task_id=str(self.task_id),
            supported_queries=tuple(self.supported_queries),
            instance_seed=int(instance_seed),
            params=params,
        )
        last_error: Exception | None = None
        rendered: _RenderedRightTriangleScene | None = None
        render_meta: Dict[str, Any] | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                ctx, render_meta_attempt = self._make_render_context(
                    instance_seed=int(instance_seed),
                    params=params,
                    render_defaults=render_defaults,
                )
                rendered = _render_right_triangle_scene(ctx, problem)
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
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint_number"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
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
            "scene_variant": str(problem.scene_variant),
            "query_id": str(problem.query_id),
            "query_id_probabilities": dict(problem.query_probabilities),
            "variant_probabilities": {"default": 1.0},
            "target_support_probabilities": dict(problem.support_probabilities),
            **dict(problem.params),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_right_triangle_trig",
                "scene_id": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_id": str(problem.query_id),
                    "scene_variant": str(problem.scene_variant),
                    "answer_value": float(rendered.answer),
                    "evidence_roles": list(rendered.evidence_roles),
                },
            },
            "query_spec": {
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_size": [int(image.size[0]), int(image.size[1])],
                "coord_space": "pixel",
                "post_image_noise": dict(noise_meta),
                **dict(render_meta),
            },
            "render_map": {
                "coord_space": "pixel",
                **dict(rendered.render_map),
            },
            "execution_trace": {
                "scene_id": SCENE_ID,
                "scene_variant": str(problem.scene_variant),
                "query_id": str(problem.query_id),
                "query_id_probabilities": dict(problem.query_probabilities),
                "answer_type": "number",
                "answer_value": float(rendered.answer),
                "answer_rounding": "nearest_tenth",
                "evidence_roles": list(rendered.evidence_roles),
                "reasoning_steps": int(rendered.reasoning_steps),
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "type": "right_triangle_trig",
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
class GeometryRightTriangleMissingSideValueTask(_RightTriangleTrigBaseTask):
    """Compute a missing right-triangle side from an angle and one side."""

    task_id = "task_geometry__triangle_relations__right_triangle_missing_side_value"
    supported_queries = _MISSING_SIDE_QUERIES
    reasoning_kind = "right_triangle_missing_side"


@register_task
class GeometryRightTriangleAngleValueTask(_RightTriangleTrigBaseTask):
    """Compute an acute angle or angle of elevation from side labels."""

    task_id = "task_geometry__triangle_relations__right_triangle_angle_value"
    supported_queries = _ANGLE_QUERIES
    reasoning_kind = "right_triangle_angle"


__all__ = [
    "GeometryRightTriangleMissingSideValueTask",
    "GeometryRightTriangleAngleValueTask",
]
