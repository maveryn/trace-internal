"""Trapezoid completion-to-parallelogram measurement tasks."""

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

SCENE_ID = "trapezoid_extension"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_trapezoid_extension_v0"

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
    "apply_prob": 0.40,
    "edit_types": ["blur", "downsample", "jpeg", "noise"],
    "edit_count_range": [1, 1],
    "value_ranges": {
        "blur": {"radius": [0.06, 0.18]},
        "downsample": {"scale": [0.96, 0.99]},
        "jpeg": {"quality": [90, 97]},
        "noise": {"alpha": [0.006, 0.018]},
    },
}

_LENGTH_QUERIES: Tuple[str, ...] = (
    "extension_from_parallelogram_area",
    "extension_from_parallelogram_perimeter",
)
_AREA_QUERIES: Tuple[str, ...] = (
    "trapezoid_area_from_bases_and_height",
    "trapezoid_area_from_extension_and_height",
    "trapezoid_area_from_parallelogram_area",
)


@dataclass(frozen=True)
class _Case:
    query_id: str
    top_base: int
    extension: int
    height: int
    side: int

    @property
    def bottom_base(self) -> int:
        return int(self.top_base) + int(self.extension)

    @property
    def parallelogram_area(self) -> int:
        return int(self.bottom_base) * int(self.height)

    @property
    def parallelogram_perimeter(self) -> int:
        return 2 * (int(self.bottom_base) + int(self.side))

    @property
    def trapezoid_area(self) -> float:
        return float((int(self.top_base) + int(self.bottom_base)) * int(self.height) / 2.0)


_LENGTH_CASES: Tuple[_Case, ...] = (
    _Case("extension_from_parallelogram_area", 9, 5, 6, 7),
    _Case("extension_from_parallelogram_area", 8, 7, 5, 6),
    _Case("extension_from_parallelogram_area", 11, 6, 7, 8),
    _Case("extension_from_parallelogram_area", 10, 8, 6, 7),
    _Case("extension_from_parallelogram_area", 12, 9, 5, 9),
    _Case("extension_from_parallelogram_perimeter", 7, 6, 6, 5),
    _Case("extension_from_parallelogram_perimeter", 10, 9, 5, 8),
    _Case("extension_from_parallelogram_perimeter", 13, 5, 7, 7),
    _Case("extension_from_parallelogram_perimeter", 9, 8, 6, 6),
    _Case("extension_from_parallelogram_perimeter", 11, 7, 5, 9),
)

_AREA_CASES: Tuple[_Case, ...] = (
    _Case("trapezoid_area_from_bases_and_height", 4, 8, 5, 5),
    _Case("trapezoid_area_from_bases_and_height", 5, 9, 5, 6),
    _Case("trapezoid_area_from_bases_and_height", 6, 10, 5, 7),
    _Case("trapezoid_area_from_bases_and_height", 7, 11, 5, 8),
    _Case("trapezoid_area_from_bases_and_height", 8, 12, 5, 9),
    _Case("trapezoid_area_from_bases_and_height", 9, 13, 5, 10),
    _Case("trapezoid_area_from_bases_and_height", 10, 14, 5, 6),
    _Case("trapezoid_area_from_bases_and_height", 11, 15, 5, 7),
    _Case("trapezoid_area_from_bases_and_height", 12, 16, 5, 8),
    _Case("trapezoid_area_from_bases_and_height", 13, 17, 5, 9),
    _Case("trapezoid_area_from_extension_and_height", 5, 4, 6, 5),
    _Case("trapezoid_area_from_extension_and_height", 7, 4, 6, 6),
    _Case("trapezoid_area_from_extension_and_height", 8, 6, 6, 7),
    _Case("trapezoid_area_from_extension_and_height", 10, 6, 6, 8),
    _Case("trapezoid_area_from_extension_and_height", 11, 8, 6, 9),
    _Case("trapezoid_area_from_extension_and_height", 13, 8, 6, 10),
    _Case("trapezoid_area_from_extension_and_height", 14, 10, 6, 6),
    _Case("trapezoid_area_from_extension_and_height", 16, 10, 6, 7),
    _Case("trapezoid_area_from_extension_and_height", 17, 12, 6, 8),
    _Case("trapezoid_area_from_extension_and_height", 19, 12, 6, 9),
    _Case("trapezoid_area_from_parallelogram_area", 5, 4, 6, 5),
    _Case("trapezoid_area_from_parallelogram_area", 7, 4, 6, 6),
    _Case("trapezoid_area_from_parallelogram_area", 8, 6, 6, 7),
    _Case("trapezoid_area_from_parallelogram_area", 10, 6, 6, 8),
    _Case("trapezoid_area_from_parallelogram_area", 11, 8, 6, 9),
    _Case("trapezoid_area_from_parallelogram_area", 13, 8, 6, 10),
    _Case("trapezoid_area_from_parallelogram_area", 14, 10, 6, 6),
    _Case("trapezoid_area_from_parallelogram_area", 16, 10, 6, 7),
    _Case("trapezoid_area_from_parallelogram_area", 17, 12, 6, 8),
    _Case("trapezoid_area_from_parallelogram_area", 19, 12, 6, 9),
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
    fill_color: Color
    extension_fill_color: Color
    accent_color: Color
    muted_color: Color
    line_width: int
    font: Any
    small_font: Any


@dataclass(frozen=True)
class _ResolvedProblem:
    query_id: str
    answer: float
    case: _Case
    query_probabilities: Dict[str, float]
    support_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedTrapezoidExtensionScene:
    image: Image.Image
    answer: float
    evidence_bboxes: Tuple[BBox, ...]
    evidence_roles: Tuple[str, ...]
    label_bboxes: Dict[str, BBox]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]


def _union_bboxes(bboxes: Sequence[BBox], *, width: int, height: int, pad: float = 0.0) -> BBox:
    if not bboxes:
        return (0.0, 0.0, 1.0, 1.0)
    return _pad_bbox(
        (
            min(bbox[0] for bbox in bboxes),
            min(bbox[1] for bbox in bboxes),
            max(bbox[2] for bbox in bboxes),
            max(bbox[3] for bbox in bboxes),
        ),
        pad,
        width=width,
        height=height,
    )


def _draw_dashed_line(
    ctx: _RenderContext,
    start: Point,
    end: Point,
    *,
    fill: Color | None = None,
    width: int | None = None,
    dash: float = 14.0,
    gap: float = 8.0,
) -> None:
    color = fill if fill is not None else ctx.muted_color
    line_width = int(width if width is not None else ctx.line_width)
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = math.hypot(dx, dy)
    if length <= 1e-9:
        return
    ux = dx / length
    uy = dy / length
    distance = 0.0
    while distance < length:
        next_distance = min(length, distance + dash)
        p0 = (float(start[0]) + ux * distance, float(start[1]) + uy * distance)
        p1 = (float(start[0]) + ux * next_distance, float(start[1]) + uy * next_distance)
        ctx.draw.line([p0, p1], fill=color, width=line_width)
        distance += dash + gap


def _draw_height_marker(ctx: _RenderContext, top_y: float, bottom_y: float, label: str) -> BBox:
    x = 56.0
    tick = 11.0
    ctx.draw.line([(x, top_y), (x, bottom_y)], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    ctx.draw.line([(x - tick, top_y), (x + tick, top_y)], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    ctx.draw.line([(x - tick, bottom_y), (x + tick, bottom_y)], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
    label_bbox = _draw_label(ctx, label, (x + 42.0, (top_y + bottom_y) / 2.0), small=True)
    marker_bbox = _bbox_from_points(
        ((x - tick, top_y), (x + tick, bottom_y)),
        width=ctx.width,
        height=ctx.height,
        pad=5.0,
    )
    return _union_bboxes((marker_bbox, label_bbox), width=ctx.width, height=ctx.height)


def _selected_probability_map(values: Sequence[float], selected: float) -> Dict[str, float]:
    return {
        _fmt_number(value): (1.0 if abs(float(value) - float(selected)) <= 1e-9 else 0.0)
        for value in values
    }


def _resolve_problem(
    *,
    task_id: str,
    supported_queries: Sequence[str],
    cases: Sequence[_Case],
    instance_seed: int,
    params: Mapping[str, Any],
    answer_kind: str,
) -> _ResolvedProblem:
    if not cases:
        raise ValueError(f"{task_id} defines no trapezoid-extension cases")
    explicit_query_raw = params.get("query_id", params.get("query_variant"))
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
        query_id = str(tuple(supported_queries)[int(query_index) % len(tuple(supported_queries))])
        query_probabilities = {
            str(value): 1.0 / float(len(tuple(supported_queries)))
            for value in tuple(supported_queries)
        }

    query_cases = tuple(case for case in cases if case.query_id == query_id)
    if not query_cases:
        raise ValueError(f"{task_id} has no cases for query_id {query_id}")
    case_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.{query_id}.case",
    )
    case = query_cases[int(case_index) % len(query_cases)]
    if min(case.top_base, case.extension, case.height, case.side) <= 0:
        raise ValueError("all trapezoid measurements must be positive")

    answer = float(case.extension if answer_kind == "extension_length" else case.trapezoid_area)
    support_values = (
        tuple(float(candidate.extension) for candidate in cases)
        if answer_kind == "extension_length"
        else tuple(float(candidate.trapezoid_area) for candidate in cases)
    )
    return _ResolvedProblem(
        query_id=str(query_id),
        answer=float(answer),
        case=case,
        query_probabilities=dict(query_probabilities),
        support_probabilities=_selected_probability_map(
            tuple(sorted(set(float(value) for value in support_values))), float(answer)
        ),
    )


def _render_trapezoid_extension_scene(
    ctx: _RenderContext, problem: _ResolvedProblem, *, answer_kind: str
) -> _RenderedTrapezoidExtensionScene:
    case = problem.case
    a = (135.0, 170.0)
    b = (355.0, 170.0)
    e = (685.0, 170.0)
    d = (95.0, 420.0)
    c = (645.0, 420.0)

    trapezoid_points = (a, b, c, d)
    extension_points = (b, e, c)
    parallelogram_points = (a, e, c, d)
    ctx.draw.polygon(trapezoid_points, fill=ctx.fill_color)
    ctx.draw.polygon(extension_points, fill=ctx.extension_fill_color)
    ctx.draw.line([a, b, c, d, a], fill=ctx.line_color, width=ctx.line_width)
    _draw_dashed_line(ctx, b, e, fill=ctx.muted_color, width=ctx.line_width)
    _draw_dashed_line(ctx, e, c, fill=ctx.muted_color, width=ctx.line_width)
    ctx.draw.line([d, c], fill=ctx.line_color, width=ctx.line_width)

    label_bboxes: Dict[str, BBox] = {}
    label_bboxes["top_base"] = _draw_label(ctx, f"AB={case.top_base}", (245.0, 132.0), small=True)
    label_bboxes["height"] = _draw_height_marker(ctx, a[1], d[1], f"h={case.height}")

    supporting_labels: list[BBox] = [label_bboxes["top_base"], label_bboxes["height"]]
    if problem.query_id == "extension_from_parallelogram_area":
        label_bboxes["parallelogram_area"] = _draw_label(
            ctx, f"parallelogram area={case.parallelogram_area}", (520.0, 84.0), small=True
        )
        supporting_labels.append(label_bboxes["parallelogram_area"])
        target_text = "BE=?"
        formula = "BE = parallelogram area / h - AB"
    elif problem.query_id == "extension_from_parallelogram_perimeter":
        label_bboxes["parallelogram_perimeter"] = _draw_label(
            ctx, f"parallelogram perimeter={case.parallelogram_perimeter}", (520.0, 84.0), small=True
        )
        label_bboxes["side"] = _draw_label(ctx, f"AD={case.side}", (94.0, 288.0), small=True)
        supporting_labels.extend((label_bboxes["parallelogram_perimeter"], label_bboxes["side"]))
        target_text = "BE=?"
        formula = "BE = parallelogram perimeter / 2 - AD - AB"
    elif problem.query_id == "trapezoid_area_from_extension_and_height":
        label_bboxes["extension"] = _draw_label(ctx, f"BE={case.extension}", (520.0, 132.0), small=True)
        supporting_labels.append(label_bboxes["extension"])
        target_text = "trapezoid area=?"
        formula = "trapezoid area = h * (AB + DC) / 2, with DC = AB + BE"
    elif problem.query_id == "trapezoid_area_from_bases_and_height":
        label_bboxes["bottom_base"] = _draw_label(ctx, f"DC={case.bottom_base}", (370.0, 458.0), small=True)
        supporting_labels.append(label_bboxes["bottom_base"])
        target_text = "trapezoid area=?"
        formula = "trapezoid area = h * (AB + DC) / 2"
    elif problem.query_id == "trapezoid_area_from_parallelogram_area":
        label_bboxes["parallelogram_area"] = _draw_label(
            ctx, f"parallelogram area={case.parallelogram_area}", (520.0, 84.0), small=True
        )
        supporting_labels.append(label_bboxes["parallelogram_area"])
        target_text = "trapezoid area=?"
        formula = "trapezoid area = h * (AB + DC) / 2, with DC = parallelogram area / h"
    else:
        label_bboxes["parallelogram_perimeter"] = _draw_label(
            ctx, f"parallelogram perimeter={case.parallelogram_perimeter}", (520.0, 84.0), small=True
        )
        label_bboxes["side"] = _draw_label(ctx, f"AD={case.side}", (94.0, 288.0), small=True)
        supporting_labels.extend((label_bboxes["parallelogram_perimeter"], label_bboxes["side"]))
        target_text = "trapezoid area=?"
        formula = "trapezoid area = h * (AB + DC) / 2, with DC = parallelogram perimeter / 2 - AD"

    if answer_kind == "extension_length":
        label_bboxes["target"] = _draw_label(ctx, target_text, (520.0, 202.0), small=True)
    else:
        label_bboxes["target"] = _draw_label(ctx, target_text, (520.0, 505.0), small=True)

    original_bbox = _bbox_from_points(trapezoid_points, width=ctx.width, height=ctx.height, pad=10.0)
    dashed_completion_bbox = _bbox_from_points(extension_points, width=ctx.width, height=ctx.height, pad=10.0)
    supporting_bbox = _union_bboxes(supporting_labels, width=ctx.width, height=ctx.height, pad=4.0)
    evidence_roles = (
        "target_cue",
        "original_trapezoid",
        "dashed_parallelogram_completion",
        "supporting_visible_labels",
    )
    evidence_bboxes = (
        label_bboxes["target"],
        original_bbox,
        dashed_completion_bbox,
        supporting_bbox,
    )
    scene_entities = (
        {
            "entity_id": "original_trapezoid",
            "entity_type": "trapezoid",
            "bbox": _bbox_to_list(original_bbox),
            "points": [[round(x, 3), round(y, 3)] for x, y in trapezoid_points],
        },
        {
            "entity_id": "completion_triangle",
            "entity_type": "dashed_extension_region",
            "bbox": _bbox_to_list(dashed_completion_bbox),
            "points": [[round(x, 3), round(y, 3)] for x, y in extension_points],
        },
        {
            "entity_id": "completed_parallelogram",
            "entity_type": "parallelogram",
            "bbox": _bbox_to_list(
                _bbox_from_points(parallelogram_points, width=ctx.width, height=ctx.height, pad=10.0)
            ),
            "points": [[round(x, 3), round(y, 3)] for x, y in parallelogram_points],
        },
    )
    witness = {
        "formula_family": str(problem.query_id),
        "top_base": int(case.top_base),
        "extension": int(case.extension),
        "bottom_base": int(case.bottom_base),
        "height": int(case.height),
        "side": int(case.side),
        "parallelogram_area": int(case.parallelogram_area),
        "parallelogram_perimeter": int(case.parallelogram_perimeter),
        "trapezoid_area": float(case.trapezoid_area),
        "formula": str(formula),
        "answer_value": float(problem.answer),
    }
    return _RenderedTrapezoidExtensionScene(
        image=ctx.image,
        answer=float(problem.answer),
        evidence_bboxes=tuple(evidence_bboxes),
        evidence_roles=tuple(evidence_roles),
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map={
            "original_trapezoid": {
                "points": [[round(x, 3), round(y, 3)] for x, y in trapezoid_points],
                "bbox": _bbox_to_list(original_bbox),
            },
            "completion_triangle": {
                "points": [[round(x, 3), round(y, 3)] for x, y in extension_points],
                "bbox": _bbox_to_list(dashed_completion_bbox),
            },
            "label_bboxes": {key: _bbox_to_list(value) for key, value in label_bboxes.items()},
            "coord_space": "pixel",
        },
        witness=witness,
    )


class _TrapezoidExtensionBaseTask:
    """Shared implementation for trapezoid completion measurement tasks."""

    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    supported_queries: Sequence[str] = ()
    cases: Sequence[_Case] = ()
    answer_kind = ""
    reasoning_kind = "trapezoid_extension"

    def _make_render_context(
        self,
        *,
        instance_seed: int,
        params: Mapping[str, Any],
        render_defaults: Mapping[str, Any],
    ) -> tuple[_RenderContext, Dict[str, Any]]:
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.render")
        width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 780)))
        height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 560)))
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
        palettes: Tuple[Tuple[Color, Color, Color, Color], ...] = (
            ((229, 240, 255), (245, 224, 178), (26, 123, 185), (126, 143, 156)),
            ((236, 247, 232), (255, 224, 210), (38, 143, 104), (150, 142, 132)),
            ((248, 238, 252), (226, 242, 255), (123, 95, 190), (143, 154, 172)),
            ((255, 244, 224), (226, 240, 255), (196, 102, 44), (132, 146, 160)),
        )
        palette_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.palette",
        )
        fill_color, extension_fill_color, accent_color, muted_color = palettes[
            int(palette_index) % len(palettes)
        ]
        font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
        small_font_size = int(
            params.get(
                "small_label_font_size",
                group_default(render_defaults, "small_label_font_size", 18),
            )
        )
        line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 4)))
        ctx = _RenderContext(
            rng=rng,
            image=image,
            draw=ImageDraw.Draw(image),
            width=int(width),
            height=int(height),
            line_color=shape_style.line_color,
            label_color=shape_style.label_color,
            label_stroke_color=shape_style.label_stroke_color,
            fill_color=fill_color,
            extension_fill_color=extension_fill_color,
            accent_color=accent_color,
            muted_color=muted_color,
            line_width=max(2, int(line_width)),
            font=load_font(max(12, int(font_size)), bold=True),
            small_font=load_font(max(10, int(small_font_size)), bold=True),
        )
        return ctx, {
            "background_style": dict(background_meta),
            "shape_style": shape_style.to_trace_dict(),
            "line_width": int(ctx.line_width),
            "label_font_size": int(font_size),
            "small_label_font_size": int(small_font_size),
            "fill_color": list(fill_color),
            "extension_fill_color": list(extension_fill_color),
            "accent_color": list(accent_color),
            "muted_color": list(muted_color),
        }

    def _build_complexity(self, rendered: _RenderedTrapezoidExtensionScene) -> TaskComplexity:
        visual_scan = clamp_unit_interval(
            0.50
            + normalize_linear(len(rendered.evidence_bboxes), min_value=3, max_value=5)
            * 0.16
        )
        is_perimeter_query = "perimeter" in str(rendered.witness.get("formula_family", ""))
        precision = 0.58 + (0.08 if is_perimeter_query else 0.0)
        ambiguity = 0.52 + (0.08 if self.answer_kind == "area" else 0.0)
        output_burden = clamp_unit_interval(
            0.42
            + normalize_linear(len(rendered.evidence_bboxes), min_value=3, max_value=5)
            * 0.12
        )
        return build_geometry_measurement_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
            visual_scan=float(visual_scan),
            measurement_precision=float(clamp_unit_interval(precision)),
            ambiguity=float(clamp_unit_interval(ambiguity)),
            output_burden=float(output_burden),
        )

    def generate(
        self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int
    ) -> TaskOutput:
        if not self.supported_queries:
            raise ValueError(f"{self.task_id} defines no trapezoid-extension query support")
        _gen_defaults, render_defaults, prompt_defaults = (
            split_generation_rendering_prompt_defaults(
                _TASK_GROUP_DEFAULTS,
                task_id=str(self.task_id),
            )
        )
        problem = _resolve_problem(
            task_id=str(self.task_id),
            supported_queries=tuple(self.supported_queries),
            cases=tuple(self.cases),
            instance_seed=int(instance_seed),
            params=params,
            answer_kind=str(self.answer_kind),
        )
        last_error: Exception | None = None
        rendered: _RenderedTrapezoidExtensionScene | None = None
        render_meta: Dict[str, Any] | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                ctx, render_meta_attempt = self._make_render_context(
                    instance_seed=int(instance_seed),
                    params=params,
                    render_defaults=render_defaults,
                )
                rendered = _render_trapezoid_extension_scene(
                    ctx, problem, answer_kind=str(self.answer_kind)
                )
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
            "query_variant": "default",
            "query_id": str(problem.query_id),
            "query_variant_probabilities": dict(problem.query_probabilities),
            "variant_probabilities": {"default": 1.0},
            "target_support_probabilities": dict(problem.support_probabilities),
            **dict(rendered.witness),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_trapezoid_extension",
                "scene_id": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_variant": "default",
                    "query_id": str(problem.query_id),
                    "answer_value": float(rendered.answer),
                    "evidence_roles": list(rendered.evidence_roles),
                },
            },
            "query_spec": {
                "scene_id": SCENE_ID,
                "query_variant": "default",
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
                "query_variant": "default",
                "query_id": str(problem.query_id),
                "query_variant_probabilities": dict(problem.query_probabilities),
                "answer_type": "number",
                "answer_value": float(rendered.answer),
                "answer_rounding": "integer",
                "evidence_roles": list(rendered.evidence_roles),
                "reasoning_steps": 2 if "perimeter" not in str(problem.query_id) else 3,
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "type": "trapezoid_extension_formula",
                "scene_id": SCENE_ID,
                "query_variant": "default",
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
            query_variant="default",
            scene_id=SCENE_ID,
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometryTrapezoidExtensionLengthValueTask(_TrapezoidExtensionBaseTask):
    """Infer the added extension length after completing a trapezoid to a parallelogram."""

    task_id = "task_geometry__trapezoid_extension__trapezoid_extension_length_value"
    supported_queries = _LENGTH_QUERIES
    cases = _LENGTH_CASES
    answer_kind = "extension_length"
    reasoning_kind = "extension_length"


@register_task
class GeometryTrapezoidExtensionAreaValueTask(_TrapezoidExtensionBaseTask):
    """Infer the trapezoid area using the parallelogram completion."""

    task_id = "task_geometry__trapezoid_extension__trapezoid_extension_area_value"
    supported_queries = _AREA_QUERIES
    cases = _AREA_CASES
    answer_kind = "area"
    reasoning_kind = "area"


__all__ = [
    "GeometryTrapezoidExtensionAreaValueTask",
    "GeometryTrapezoidExtensionLengthValueTask",
    "SCENE_ID",
]
