"""Concentric-circle tangent-chord measurement tasks."""

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

SCENE_ID = "concentric_chord"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_concentric_circle_chord_v0"

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

_CHORD_LENGTH_QUERIES: Tuple[str, ...] = ("chord_length_from_radii",)
_INNER_RADIUS_QUERIES: Tuple[str, ...] = ("inner_radius_from_chord",)
_ALL_CONCENTRIC_CHORD_QUERIES: Tuple[str, ...] = (
    *_CHORD_LENGTH_QUERIES,
    *_INNER_RADIUS_QUERIES,
)

_PYTHAGOREAN_CASES: Tuple[Tuple[int, int, int], ...] = (
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
    line_width: int
    font: Any
    small_font: Any


@dataclass(frozen=True)
class _ResolvedProblem:
    query_id: str
    answer: float
    outer_radius: int
    inner_radius: int
    half_chord: int
    chord_length: int
    query_probabilities: Dict[str, float]
    support_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedConcentricScene:
    image: Image.Image
    answer: float
    evidence_bboxes: Tuple[BBox, ...]
    evidence_roles: Tuple[str, ...]
    label_bboxes: Dict[str, BBox]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]


def _draw_dimension(
    ctx: _RenderContext,
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


def _selected_probability_map(
    values: Sequence[int], selected: int | float
) -> Dict[str, float]:
    return {
        str(value): (1.0 if float(value) == float(selected) else 0.0)
        for value in values
    }


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

    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.{query_id}.case",
    )
    outer_radius, inner_radius, half_chord = _PYTHAGOREAN_CASES[
        int(index) % len(_PYTHAGOREAN_CASES)
    ]
    outer_radius = int(params.get("outer_radius", outer_radius))
    inner_radius = int(params.get("inner_radius", inner_radius))
    half_chord = int(params.get("half_chord", half_chord))
    if int(outer_radius * outer_radius) != int(inner_radius * inner_radius) + int(
        half_chord * half_chord
    ):
        raise ValueError("concentric circle case must satisfy R^2 = r^2 + (c/2)^2")
    chord_length = int(2 * int(half_chord))
    if query_id == "chord_length_from_radii":
        answer = float(chord_length)
        support_values = tuple(2 * case[2] for case in _PYTHAGOREAN_CASES)
    elif query_id == "inner_radius_from_chord":
        answer = float(inner_radius)
        support_values = tuple(case[1] for case in _PYTHAGOREAN_CASES)
    else:
        raise ValueError(f"unsupported concentric-circle query_id: {query_id}")
    return _ResolvedProblem(
        query_id=str(query_id),
        answer=_round1(answer),
        outer_radius=int(outer_radius),
        inner_radius=int(inner_radius),
        half_chord=int(half_chord),
        chord_length=int(chord_length),
        query_probabilities=dict(query_probabilities),
        support_probabilities=_selected_probability_map(
            tuple(sorted(set(support_values))), answer
        ),
    )


def _render_concentric_scene(
    ctx: _RenderContext, problem: _ResolvedProblem
) -> _RenderedConcentricScene:
    center = (326.0, 292.0)
    outer_px = 178.0
    inner_px = outer_px * float(problem.inner_radius) / float(problem.outer_radius)
    half_chord_px = outer_px * float(problem.half_chord) / float(problem.outer_radius)
    chord_y = center[1] - inner_px
    left = (center[0] - half_chord_px, chord_y)
    right = (center[0] + half_chord_px, chord_y)
    tangent = (center[0], chord_y)

    outer_box = (
        center[0] - outer_px,
        center[1] - outer_px,
        center[0] + outer_px,
        center[1] + outer_px,
    )
    inner_box = (
        center[0] - inner_px,
        center[1] - inner_px,
        center[0] + inner_px,
        center[1] + inner_px,
    )
    ctx.draw.ellipse(outer_box, outline=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse(inner_box, outline=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([left, right], fill=ctx.accent_color, width=ctx.line_width + 1)
    ctx.draw.line(
        [center, tangent], fill=ctx.line_color, width=max(2, ctx.line_width - 1)
    )
    ctx.draw.line(
        [center, right], fill=ctx.line_color, width=max(2, ctx.line_width - 1)
    )

    marker = 16.0
    ctx.draw.line(
        [(tangent[0], tangent[1]), (tangent[0] + marker, tangent[1])],
        fill=ctx.line_color,
        width=2,
    )
    ctx.draw.line(
        [(tangent[0] + marker, tangent[1]), (tangent[0] + marker, tangent[1] + marker)],
        fill=ctx.line_color,
        width=2,
    )
    ctx.draw.line(
        [(tangent[0] + marker, tangent[1] + marker), (tangent[0], tangent[1] + marker)],
        fill=ctx.line_color,
        width=2,
    )

    for label, point in (("O", center), ("A", left), ("B", right), ("T", tangent)):
        px, py = float(point[0]), float(point[1])
        ctx.draw.ellipse((px - 4.0, py - 4.0, px + 4.0, py + 4.0), fill=ctx.line_color)
        offset = {
            "O": (0.0, 24.0),
            "A": (-18.0, -18.0),
            "B": (18.0, -18.0),
            "T": (20.0, 20.0),
        }[label]
        _draw_label(ctx, label, (px + offset[0], py + offset[1]), small=True)

    outer_radius_label = f"R={_fmt_number(problem.outer_radius)}"
    inner_radius_label = f"r={_fmt_number(problem.inner_radius)}"
    chord_label = f"c={_fmt_number(problem.chord_length)}"
    if problem.query_id == "chord_length_from_radii":
        chord_label = "c=?"
    elif problem.query_id == "inner_radius_from_chord":
        inner_radius_label = "r=?"

    label_bboxes: Dict[str, BBox] = {}
    label_bboxes["outer_radius"] = _draw_dimension(
        ctx, center, right, outer_radius_label, label_offset=(38.0, 8.0)
    )
    label_bboxes["inner_radius"] = _draw_dimension(
        ctx, center, tangent, inner_radius_label, label_offset=(-38.0, -4.0)
    )
    dim_y = chord_y - 46.0
    label_bboxes["chord"] = _draw_dimension(
        ctx,
        (left[0], dim_y),
        (right[0], dim_y),
        chord_label,
        label_offset=(0.0, -18.0),
        color=ctx.accent_color,
    )
    label_bboxes["right_angle"] = _bbox_from_points(
        (
            tangent,
            (tangent[0] + marker, tangent[1]),
            (tangent[0] + marker, tangent[1] + marker),
            (tangent[0], tangent[1] + marker),
        ),
        width=ctx.width,
        height=ctx.height,
        pad=5.0,
    )

    if problem.query_id == "chord_length_from_radii":
        evidence_roles = ("outer_radius_label", "inner_radius_label")
        evidence_bboxes = (label_bboxes["outer_radius"], label_bboxes["inner_radius"])
    elif problem.query_id == "inner_radius_from_chord":
        evidence_roles = ("outer_radius_label", "chord_length_label")
        evidence_bboxes = (label_bboxes["outer_radius"], label_bboxes["chord"])
    else:
        raise ValueError(f"unsupported concentric-circle query_id: {problem.query_id}")

    chord_bbox = _bbox_from_points(
        (left, right), width=ctx.width, height=ctx.height, pad=18.0
    )
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
            "endpoints": [
                [round(left[0], 3), round(left[1], 3)],
                [round(right[0], 3), round(right[1], 3)],
            ],
            "length_units": int(problem.chord_length),
            "bbox": _bbox_to_list(chord_bbox),
        },
    )
    witness = {
        "formula_family": str(problem.query_id),
        "outer_radius": int(problem.outer_radius),
        "inner_radius": int(problem.inner_radius),
        "half_chord": int(problem.half_chord),
        "chord_length": int(problem.chord_length),
        "pythagorean_relation": "R^2 = r^2 + (c/2)^2",
        "answer_value": float(problem.answer),
    }
    return _RenderedConcentricScene(
        image=ctx.image,
        answer=float(problem.answer),
        evidence_bboxes=tuple(evidence_bboxes),
        evidence_roles=tuple(evidence_roles),
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map={
            "center": [round(center[0], 3), round(center[1], 3)],
            "outer_radius_px": round(outer_px, 3),
            "inner_radius_px": round(inner_px, 3),
            "chord_endpoints": [
                [round(left[0], 3), round(left[1], 3)],
                [round(right[0], 3), round(right[1], 3)],
            ],
            "tangent_point": [round(tangent[0], 3), round(tangent[1], 3)],
            "label_bboxes": {
                key: _bbox_to_list(value) for key, value in label_bboxes.items()
            },
            "coord_space": "pixel",
        },
        witness=witness,
    )


class _ConcentricCircleChordBaseTask:
    """Shared implementation for concentric-circle tangent-chord tasks."""

    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    public_scene_id = SCENE_ID
    supported_queries: Sequence[str] = ()
    reasoning_kind = "concentric_circle_chord"

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
        }
        return ctx, render_meta

    def _build_complexity(self, rendered: _RenderedConcentricScene) -> TaskComplexity:
        visual_scan = clamp_unit_interval(
            0.36
            + normalize_linear(len(rendered.evidence_bboxes), min_value=2, max_value=4)
            * 0.18
        )
        formula_family = str(rendered.witness.get("formula_family", ""))
        is_chord_length = formula_family == "chord_length_from_radii"
        precision = 0.72 if is_chord_length else 0.78
        ambiguity = 0.42 if is_chord_length else 0.48
        output_burden = clamp_unit_interval(
            0.42
            + normalize_linear(len(rendered.evidence_bboxes), min_value=2, max_value=4)
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
            raise ValueError(
                f"{self.task_id} defines no concentric-circle query support"
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
        rendered: _RenderedConcentricScene | None = None
        render_meta: Dict[str, Any] | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                ctx, render_meta_attempt = self._make_render_context(
                    instance_seed=int(instance_seed),
                    params=params,
                    render_defaults=render_defaults,
                )
                rendered = _render_concentric_scene(ctx, problem)
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
            "scene_variant": "tangent_chord",
            "query_id": str(problem.query_id),
            "query_id_probabilities": dict(problem.query_probabilities),
            "target_support_probabilities": dict(problem.support_probabilities),
            **dict(rendered.witness),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_concentric_circle_chord",
                "scene_id": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_id": str(problem.query_id),
                    "scene_variant": "tangent_chord",
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
            "render_map": {
                "coord_space": "pixel",
                **dict(rendered.render_map),
            },
            "execution_trace": {
                "scene_id": SCENE_ID,
                "scene_variant": "tangent_chord",
                "query_id": str(problem.query_id),
                "query_id_probabilities": dict(problem.query_probabilities),
                "answer_type": "number",
                "answer_value": float(rendered.answer),
                "answer_rounding": "nearest_tenth",
                "evidence_roles": list(rendered.evidence_roles),
                "reasoning_steps": 1,
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "type": "concentric_circle_chord_formula",
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
class GeometryConcentricCircleChordValueTask(_ConcentricCircleChordBaseTask):
    """Compute a chord or radius value in a concentric-circle tangent-chord diagram."""

    task_id = "task_geometry__concentric_chord__concentric_circle_chord_value"
    supported_queries = _ALL_CONCENTRIC_CHORD_QUERIES
    reasoning_kind = "concentric_circle_chord"


__all__ = [
    "GeometryConcentricCircleChordValueTask",
    "SCENE_ID",
]
