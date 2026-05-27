"""Pythagorean square-dissection measurement tasks."""

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

SCENE_ID = "pythagorean_dissection"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_pythagorean_square_dissection_v0"

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

_SQUARE_AREA_QUERIES: Tuple[str, ...] = ("central_square_area_from_triangle_legs",)

_LEG_CASES: Tuple[Tuple[int, int], ...] = (
    (3, 4),
    (4, 7),
    (5, 8),
    (5, 12),
    (6, 8),
    (6, 11),
    (7, 9),
    (8, 15),
    (9, 12),
    (10, 15),
    (12, 16),
    (13, 14),
)

_ORIENTATIONS: Tuple[Tuple[str, int, int], ...] = (
    ("up_right", 1, -1),
    ("up_left", -1, -1),
    ("down_right", 1, 1),
    ("down_left", -1, 1),
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
    leg_fill_color: Color
    other_leg_fill_color: Color
    hyp_fill_color: Color
    line_width: int
    font: Any
    small_font: Any
    orientation_key: str
    orientation_sign_x: int
    orientation_sign_y: int


@dataclass(frozen=True)
class _ResolvedProblem:
    query_id: str
    answer: float
    leg_vertical: int
    leg_horizontal: int
    vertical_square_area: int
    horizontal_square_area: int
    hypotenuse_square_area: int
    hypotenuse_side: float
    query_probabilities: Dict[str, float]
    support_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedPythagoreanSquareScene:
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


def _polygon_center(points: Sequence[Point]) -> Point:
    return (
        sum(float(point[0]) for point in points) / float(len(points)),
        sum(float(point[1]) for point in points) / float(len(points)),
    )


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
    leg_vertical, leg_horizontal = _LEG_CASES[int(case_index) % len(_LEG_CASES)]
    leg_vertical = int(params.get("leg_vertical", leg_vertical))
    leg_horizontal = int(params.get("leg_horizontal", leg_horizontal))
    if min(leg_vertical, leg_horizontal) <= 0:
        raise ValueError("Pythagorean square legs must be positive")
    vertical_area = int(leg_vertical * leg_vertical)
    horizontal_area = int(leg_horizontal * leg_horizontal)
    hyp_area = int(vertical_area + horizontal_area)
    hyp_side = math.sqrt(float(hyp_area))
    if query_id == "central_square_area_from_triangle_legs":
        answer = float(hyp_area)
        support_values = tuple(a * a + b * b for a, b in _LEG_CASES)
    else:
        raise ValueError(f"unsupported Pythagorean square query_id: {query_id}")
    return _ResolvedProblem(
        query_id=str(query_id),
        answer=_round1(answer),
        leg_vertical=int(leg_vertical),
        leg_horizontal=int(leg_horizontal),
        vertical_square_area=int(vertical_area),
        horizontal_square_area=int(horizontal_area),
        hypotenuse_square_area=int(hyp_area),
        hypotenuse_side=float(hyp_side),
        query_probabilities=dict(query_probabilities),
        support_probabilities=_selected_probability_map(
            tuple(sorted(set(support_values))), answer
        ),
    )


def _render_pythagorean_square_scene(
    ctx: _RenderContext, problem: _ResolvedProblem
) -> _RenderedPythagoreanSquareScene:
    if problem.query_id != "central_square_area_from_triangle_legs":
        raise ValueError(f"unsupported query_id: {problem.query_id}")

    outer_side_units = int(problem.leg_vertical + problem.leg_horizontal)
    square_size = min(float(ctx.width) * 0.62, float(ctx.height) * 0.72)
    left = (float(ctx.width) - square_size) / 2.0
    top = (float(ctx.height) - square_size) / 2.0
    right = left + square_size
    bottom = top + square_size
    scale = square_size / float(outer_side_units)
    short_px = float(problem.leg_vertical) * scale
    long_px = float(problem.leg_horizontal) * scale

    outer_top_left = (left, top)
    outer_top_right = (right, top)
    outer_bottom_right = (right, bottom)
    outer_bottom_left = (left, bottom)
    center_top = (left + short_px, top)
    center_right = (right, top + short_px)
    center_bottom = (left + long_px, bottom)
    center_left = (left, top + long_px)
    outer_square = (
        outer_top_left,
        outer_top_right,
        outer_bottom_right,
        outer_bottom_left,
    )
    central_square = (center_top, center_right, center_bottom, center_left)
    corner_triangles = (
        (outer_top_left, center_top, center_left),
        (outer_top_right, center_right, center_top),
        (outer_bottom_right, center_bottom, center_right),
        (outer_bottom_left, center_left, center_bottom),
    )

    triangle_fills = (
        ctx.leg_fill_color,
        ctx.other_leg_fill_color,
        ctx.leg_fill_color,
        ctx.other_leg_fill_color,
    )
    for triangle, fill in zip(corner_triangles, triangle_fills):
        ctx.draw.polygon(triangle, fill=fill)
    ctx.draw.polygon(central_square, fill=ctx.hyp_fill_color)
    ctx.draw.line(
        list(outer_square) + [outer_square[0]],
        fill=ctx.line_color,
        width=ctx.line_width,
        joint="curve",
    )
    for triangle in corner_triangles:
        ctx.draw.line(
            list(triangle) + [triangle[0]],
            fill=ctx.line_color,
            width=max(2, ctx.line_width - 1),
            joint="curve",
        )
    ctx.draw.line(
        list(central_square) + [central_square[0]],
        fill=ctx.line_color,
        width=ctx.line_width,
        joint="curve",
    )

    marker = 16.0
    angle_marks = (
        [
            (left + marker, top),
            (left + marker, top + marker),
            (left, top + marker),
        ],
        [
            (right - marker, top),
            (right - marker, top + marker),
            (right, top + marker),
        ],
        [
            (right - marker, bottom),
            (right - marker, bottom - marker),
            (right, bottom - marker),
        ],
        [
            (left + marker, bottom),
            (left + marker, bottom - marker),
            (left, bottom - marker),
        ],
    )
    for mark in angle_marks:
        ctx.draw.line(mark, fill=ctx.line_color, width=2)

    label_bboxes: Dict[str, BBox] = {}
    if ctx.orientation_key == "up_right":
        outer_label_center = ((left + right) / 2.0, top - 32.0)
        leg_label_center = ((left + center_top[0]) / 2.0, top + 28.0)
        other_leg_label_center = ((center_top[0] + right) / 2.0, top + 28.0)
    elif ctx.orientation_key == "up_left":
        outer_label_center = (left - 56.0, (top + bottom) / 2.0)
        leg_label_center = (right - 34.0, (top + center_right[1]) / 2.0)
        other_leg_label_center = (
            right - 42.0,
            (center_right[1] + bottom) / 2.0,
        )
    elif ctx.orientation_key == "down_right":
        outer_label_center = ((left + right) / 2.0, bottom + 30.0)
        leg_label_center = ((center_bottom[0] + right) / 2.0, bottom - 28.0)
        other_leg_label_center = ((left + center_bottom[0]) / 2.0, bottom - 28.0)
    else:
        outer_label_center = (right + 56.0, (top + bottom) / 2.0)
        leg_label_center = (left + 34.0, (center_left[1] + bottom) / 2.0)
        other_leg_label_center = (left + 42.0, (top + center_left[1]) / 2.0)
    label_bboxes["outer_square_side"] = _draw_label(
        ctx,
        f"outer side={outer_side_units}",
        outer_label_center,
        small=True,
    )
    label_bboxes["given_triangle_leg"] = _draw_label(
        ctx,
        f"leg={problem.leg_vertical}",
        leg_label_center,
        small=True,
    )
    label_bboxes["other_triangle_leg"] = _draw_label(
        ctx,
        f"other leg={problem.leg_horizontal}",
        other_leg_label_center,
        small=True,
    )
    central_square_center = _polygon_center(central_square)
    label_bboxes["central_square_target"] = _draw_label(
        ctx, "Area=?", central_square_center, small=True
    )

    evidence_roles = (
        "outer_square_side_label",
        "given_triangle_leg_label",
        "other_triangle_leg_label",
    )
    evidence_bboxes = (
        label_bboxes["outer_square_side"],
        label_bboxes["given_triangle_leg"],
        label_bboxes["other_triangle_leg"],
    )

    square_entities = (
        {
            "entity_id": "outer_square",
            "entity_type": "square",
            "side_units": int(outer_side_units),
            "area_units": int(outer_side_units * outer_side_units),
            "vertices": [[round(x, 3), round(y, 3)] for x, y in outer_square],
            "bbox": _bbox_to_list(
                _bbox_from_points(outer_square, width=ctx.width, height=ctx.height)
            ),
        },
        {
            "entity_id": "repeated_corner_triangle",
            "entity_type": "right_triangle",
            "multiplicity": 4,
            "leg_a_units": int(problem.leg_vertical),
            "leg_b_units": int(problem.leg_horizontal),
            "area_units_each": float(
                _round1(problem.leg_vertical * problem.leg_horizontal / 2.0)
            ),
            "vertices_by_instance": [
                [[round(x, 3), round(y, 3)] for x, y in triangle]
                for triangle in corner_triangles
            ],
            "bbox": _bbox_to_list(
                _bbox_from_points(
                    [point for triangle in corner_triangles for point in triangle],
                    width=ctx.width,
                    height=ctx.height,
                )
            ),
        },
        {
            "entity_id": "central_square",
            "entity_type": "square",
            "side_units": _round1(problem.hypotenuse_side),
            "area_units": int(problem.hypotenuse_square_area),
            "vertices": [[round(x, 3), round(y, 3)] for x, y in central_square],
            "bbox": _bbox_to_list(
                _bbox_from_points(central_square, width=ctx.width, height=ctx.height)
            ),
        },
    )
    witness = {
        "formula_family": str(problem.query_id),
        "leg_vertical": int(problem.leg_vertical),
        "leg_horizontal": int(problem.leg_horizontal),
        "outer_square_side": int(outer_side_units),
        "outer_square_area": int(outer_side_units * outer_side_units),
        "given_leg": int(problem.leg_vertical),
        "visible_other_leg": int(problem.leg_horizontal),
        "corner_triangle_area_each": float(
            _round1(problem.leg_vertical * problem.leg_horizontal / 2.0)
        ),
        "corner_triangle_count": 4,
        "vertical_square_area": int(problem.vertical_square_area),
        "horizontal_square_area": int(problem.horizontal_square_area),
        "central_square_area": int(problem.hypotenuse_square_area),
        "central_square_side": _round1(problem.hypotenuse_side),
        "orientation": str(ctx.orientation_key),
        "dissection_relation": "central square area = outer square area - four congruent corner triangle areas",
        "answer_value": float(problem.answer),
    }
    return _RenderedPythagoreanSquareScene(
        image=ctx.image,
        answer=float(problem.answer),
        evidence_bboxes=tuple(evidence_bboxes),
        evidence_roles=tuple(evidence_roles),
        label_bboxes=dict(label_bboxes),
        scene_entities=square_entities,
        render_map={
            "points": {
                "outer_top_left": [
                    round(outer_top_left[0], 3),
                    round(outer_top_left[1], 3),
                ],
                "outer_top_right": [
                    round(outer_top_right[0], 3),
                    round(outer_top_right[1], 3),
                ],
                "outer_bottom_right": [
                    round(outer_bottom_right[0], 3),
                    round(outer_bottom_right[1], 3),
                ],
                "outer_bottom_left": [
                    round(outer_bottom_left[0], 3),
                    round(outer_bottom_left[1], 3),
                ],
            },
            "square_vertices": {
                "outer_square": [[round(x, 3), round(y, 3)] for x, y in outer_square],
                "central_square": [
                    [round(x, 3), round(y, 3)] for x, y in central_square
                ],
            },
            "corner_triangle_vertices": [
                [[round(x, 3), round(y, 3)] for x, y in triangle]
                for triangle in corner_triangles
            ],
            "label_bboxes": {
                key: _bbox_to_list(value) for key, value in label_bboxes.items()
            },
            "orientation": str(ctx.orientation_key),
            "coord_space": "pixel",
        },
        witness=witness,
    )


class _PythagoreanSquareDissectionBaseTask:
    """Shared implementation for Pythagorean attached-square tasks."""

    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    public_scene_id = SCENE_ID
    supported_queries: Sequence[str] = ()
    reasoning_kind = "pythagorean_square_dissection"

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
        palettes: Tuple[Tuple[Color, Color, Color], ...] = (
            ((225, 239, 255), (230, 248, 235), (255, 238, 218)),
            ((235, 232, 255), (224, 246, 247), (255, 233, 232)),
            ((237, 246, 224), (232, 240, 255), (252, 235, 210)),
        )
        palette_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.palette",
        )
        leg_fill, other_leg_fill, hyp_fill = palettes[
            int(palette_index) % len(palettes)
        ]
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
        orientation_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.orientation",
        )
        orientation_key, orientation_sign_x, orientation_sign_y = _ORIENTATIONS[
            int(orientation_index) % len(_ORIENTATIONS)
        ]
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
            leg_fill_color=leg_fill,
            other_leg_fill_color=other_leg_fill,
            hyp_fill_color=hyp_fill,
            line_width=max(2, int(line_width)),
            font=load_font(max(12, int(font_size)), bold=True),
            small_font=load_font(max(10, int(small_font_size)), bold=True),
            orientation_key=str(orientation_key),
            orientation_sign_x=int(orientation_sign_x),
            orientation_sign_y=int(orientation_sign_y),
        )
        render_meta = {
            "background_style": dict(background_meta),
            "shape_style": shape_style.to_trace_dict(),
            "line_width": int(ctx.line_width),
            "label_font_size": int(font_size),
            "small_label_font_size": int(small_font_size),
            "accent_color": list(accent_color),
            "square_fill_colors": [
                list(leg_fill),
                list(other_leg_fill),
                list(hyp_fill),
            ],
            "orientation": str(orientation_key),
            "orientation_sign_x": int(orientation_sign_x),
            "orientation_sign_y": int(orientation_sign_y),
        }
        return ctx, render_meta

    def _build_complexity(
        self, rendered: _RenderedPythagoreanSquareScene
    ) -> TaskComplexity:
        visual_scan = clamp_unit_interval(
            0.40
            + normalize_linear(len(rendered.evidence_bboxes), min_value=2, max_value=4)
            * 0.16
        )
        precision = 0.56 if self.reasoning_kind == "square_area" else 0.72
        ambiguity = 0.42 if self.reasoning_kind == "square_area" else 0.50
        output_burden = 0.44 if self.reasoning_kind == "square_area" else 0.52
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
            raise ValueError(
                f"{self.task_id} defines no Pythagorean square query support"
            )
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
        rendered: _RenderedPythagoreanSquareScene | None = None
        render_meta: Dict[str, Any] | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                ctx, render_meta_attempt = self._make_render_context(
                    instance_seed=int(instance_seed),
                    params=params,
                    render_defaults=render_defaults,
                )
                rendered = _render_pythagorean_square_scene(ctx, problem)
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
            "scene_variant": "attached_squares",
            "query_id": str(problem.query_id),
            "query_id_probabilities": dict(problem.query_probabilities),
            "target_support_probabilities": dict(problem.support_probabilities),
            **dict(rendered.witness),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_pythagorean_square_dissection",
                "scene_id": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_id": str(problem.query_id),
                    "scene_variant": "attached_squares",
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
                "scene_variant": "attached_squares",
                "query_id": str(problem.query_id),
                "query_id_probabilities": dict(problem.query_probabilities),
                "answer_type": "number",
                "answer_value": float(rendered.answer),
                "answer_rounding": "nearest_tenth",
                "evidence_roles": list(rendered.evidence_roles),
                "reasoning_steps": 1 if self.reasoning_kind == "square_area" else 2,
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "type": "pythagorean_square_dissection_formula",
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
class GeometryPythagoreanSquareAreaValueTask(_PythagoreanSquareDissectionBaseTask):
    """Compute central-square area from an outer-square dissection."""

    task_id = "task_geometry__pythagorean_dissection__pythagorean_square_area_value"
    supported_queries = _SQUARE_AREA_QUERIES
    reasoning_kind = "square_area"


__all__ = [
    "GeometryPythagoreanSquareAreaValueTask",
    "SCENE_ID",
]
