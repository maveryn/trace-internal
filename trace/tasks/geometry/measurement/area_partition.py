"""Area-partition theorem measurement tasks."""

from __future__ import annotations

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
    bbox_to_list as _bbox_to_list,
    clamp_bbox as _clamp_bbox,
    pad_bbox as _pad_bbox,
    bbox_from_points as _bbox_from_points,
    draw_label as _draw_label,
)

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

PARALLELOGRAM_SCENE_ID = "area_partition"
TRIANGLE_SCENE_ID = "area_partition"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_area_partition_v0"

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

_TOTAL_AREA_QUERIES: Tuple[str, ...] = ("total_area_from_shaded_partition",)

_PARALLELOGRAM_PARTITION_CASES: Tuple[Tuple[str, int, int], ...] = (
    ("parallelogram_diagonals_midpoint_eighth", 19, 8),
    ("parallelogram_diagonals_midpoint_eighth", 23, 8),
    ("parallelogram_diagonals_midpoint_eighth", 31, 8),
    ("parallelogram_diagonals_midpoint_eighth", 43, 8),
    ("parallelogram_diagonals_quarter", 37, 4),
    ("parallelogram_diagonals_quarter", 47, 4),
    ("parallelogram_diagonals_quarter", 53, 4),
    ("parallelogram_diagonals_quarter", 61, 4),
    ("parallelogram_diagonals_quarter", 71, 4),
    ("parallelogram_diagonals_quarter", 79, 4),
)

_TRIANGLE_PARTITION_CASES: Tuple[Tuple[str, int, int], ...] = (
    ("triangle_median_half", 68, 2),
    ("triangle_median_half", 84, 2),
    ("triangle_midsegment_quarter", 37, 4),
    ("triangle_midsegment_quarter", 49, 4),
    ("triangle_midsegment_quarter", 62, 4),
    ("triangle_medians_sixth", 23, 6),
    ("triangle_medians_sixth", 31, 6),
    ("triangle_medians_sixth", 43, 6),
    ("triangle_medians_sixth", 57, 6),
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
    shaded_color: Color
    accent_color: Color
    muted_color: Color
    line_width: int
    font: Any
    small_font: Any


@dataclass(frozen=True)
class _ResolvedProblem:
    scene_id: str
    query_id: str
    scene_variant: str
    answer: float
    shaded_area: int
    denominator: int
    formula: str
    query_probabilities: Dict[str, float]
    support_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedAreaPartitionScene:
    image: Image.Image
    answer: float
    evidence_bboxes: Tuple[BBox, ...]
    evidence_roles: Tuple[str, ...]
    label_bboxes: Dict[str, BBox]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]


def _midpoint(a: Point, b: Point) -> Point:
    return ((float(a[0]) + float(b[0])) / 2.0, (float(a[1]) + float(b[1])) / 2.0)


def _centroid(a: Point, b: Point, c: Point) -> Point:
    return (
        (float(a[0]) + float(b[0]) + float(c[0])) / 3.0,
        (float(a[1]) + float(b[1]) + float(c[1])) / 3.0,
    )


def _draw_equal_ticks(ctx: _RenderContext, segments: Sequence[Tuple[Point, Point]]) -> BBox:
    tick_bboxes: list[BBox] = []
    for start, end in segments:
        mid = _midpoint(start, end)
        dx = float(end[0]) - float(start[0])
        dy = float(end[1]) - float(start[1])
        length = max(1e-9, (dx**2 + dy**2) ** 0.5)
        nx = -dy / length
        ny = dx / length
        half = 8.0
        p0 = (mid[0] - nx * half, mid[1] - ny * half)
        p1 = (mid[0] + nx * half, mid[1] + ny * half)
        ctx.draw.line([p0, p1], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
        tick_bboxes.append(_bbox_from_points((p0, p1), width=ctx.width, height=ctx.height, pad=4.0))
    return (
        min(bbox[0] for bbox in tick_bboxes),
        min(bbox[1] for bbox in tick_bboxes),
        max(bbox[2] for bbox in tick_bboxes),
        max(bbox[3] for bbox in tick_bboxes),
    )


def _selected_probability_map(values: Sequence[float], selected: float) -> Dict[str, float]:
    return {
        str(int(value)): (1.0 if int(value) == int(selected) else 0.0)
        for value in values
    }


def _resolve_problem(
    *,
    task_id: str,
    scene_id: str,
    partition_cases: Sequence[Tuple[str, int, int]],
    supported_queries: Sequence[str],
    instance_seed: int,
    params: Mapping[str, Any],
) -> _ResolvedProblem:
    if not partition_cases:
        raise ValueError(f"{task_id} defines no area-partition cases")
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
    scene_variant, shaded_area, denominator = tuple(partition_cases)[
        int(case_index) % len(tuple(partition_cases))
    ]
    scene_variant = str(params.get("scene_variant", scene_variant))
    shaded_area = int(params.get("shaded_area", shaded_area))
    denominator = int(params.get("area_denominator", denominator))
    if shaded_area <= 0 or denominator <= 1:
        raise ValueError("shaded area must be positive and denominator must exceed 1")
    allowed_variants = {str(case[0]) for case in tuple(partition_cases)}
    if scene_variant not in allowed_variants:
        raise ValueError(
            f"unsupported area partition scene_variant for {task_id}: {scene_variant}"
        )

    answer = int(shaded_area) * int(denominator)
    support_values = tuple(case[1] * case[2] for case in tuple(partition_cases))
    return _ResolvedProblem(
        scene_id=str(scene_id),
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        answer=float(answer),
        shaded_area=int(shaded_area),
        denominator=int(denominator),
        formula=f"total area = shaded area * {int(denominator)}",
        query_probabilities=dict(query_probabilities),
        support_probabilities=_selected_probability_map(
            tuple(sorted(set(float(value) for value in support_values))), float(answer)
        ),
    )


def _draw_parallelogram(
    ctx: _RenderContext, problem: _ResolvedProblem
) -> tuple[Tuple[Point, ...], Tuple[Point, ...], BBox, BBox, BBox]:
    a = (130.0, 408.0)
    b = (534.0, 408.0)
    c = (646.0, 152.0)
    d = (242.0, 152.0)
    o = _midpoint(a, c)
    outer = (a, b, c, d)
    if problem.scene_variant == "parallelogram_diagonal_half":
        shaded = (a, b, c)
        partition_points = (a, c)
        ctx.draw.polygon(outer, fill=ctx.fill_color)
        ctx.draw.polygon(shaded, fill=ctx.shaded_color)
        ctx.draw.line([a, b, c, d, a], fill=ctx.line_color, width=ctx.line_width)
        ctx.draw.line([a, c], fill=ctx.accent_color, width=ctx.line_width)
        partition_bbox = _bbox_from_points(partition_points, width=ctx.width, height=ctx.height, pad=10.0)
    elif problem.scene_variant == "parallelogram_diagonals_quarter":
        shaded = (a, b, o)
        partition_points = (a, b, c, d)
        ctx.draw.polygon(outer, fill=ctx.fill_color)
        ctx.draw.polygon(shaded, fill=ctx.shaded_color)
        ctx.draw.line([a, b, c, d, a], fill=ctx.line_color, width=ctx.line_width)
        ctx.draw.line([a, c], fill=ctx.accent_color, width=ctx.line_width)
        ctx.draw.line([b, d], fill=ctx.accent_color, width=ctx.line_width)
        ctx.draw.ellipse((o[0] - 5.0, o[1] - 5.0, o[0] + 5.0, o[1] + 5.0), fill=ctx.accent_color)
        partition_bbox = _bbox_from_points(partition_points, width=ctx.width, height=ctx.height, pad=10.0)
    else:
        m = _midpoint(a, b)
        shaded = (a, m, o)
        ctx.draw.polygon(outer, fill=ctx.fill_color)
        ctx.draw.polygon(shaded, fill=ctx.shaded_color)
        ctx.draw.line([a, b, c, d, a], fill=ctx.line_color, width=ctx.line_width)
        ctx.draw.line([a, c], fill=ctx.accent_color, width=ctx.line_width)
        ctx.draw.line([b, d], fill=ctx.accent_color, width=ctx.line_width)
        ctx.draw.line([m, o], fill=ctx.accent_color, width=ctx.line_width)
        ctx.draw.ellipse((o[0] - 5.0, o[1] - 5.0, o[0] + 5.0, o[1] + 5.0), fill=ctx.accent_color)
        ticks_bbox = _draw_equal_ticks(ctx, ((a, m), (m, b)))
        partition_lines_bbox = _bbox_from_points(
            (a, b, c, d, m, o), width=ctx.width, height=ctx.height, pad=10.0
        )
        partition_bbox = (
            min(ticks_bbox[0], partition_lines_bbox[0]),
            min(ticks_bbox[1], partition_lines_bbox[1]),
            max(ticks_bbox[2], partition_lines_bbox[2]),
            max(ticks_bbox[3], partition_lines_bbox[3]),
        )
    outer_bbox = _bbox_from_points(outer, width=ctx.width, height=ctx.height, pad=8.0)
    shaded_bbox = _bbox_from_points(shaded, width=ctx.width, height=ctx.height, pad=8.0)
    return outer, shaded, outer_bbox, shaded_bbox, partition_bbox


def _draw_triangle(
    ctx: _RenderContext, problem: _ResolvedProblem
) -> tuple[Tuple[Point, ...], Tuple[Point, ...], BBox, BBox, BBox]:
    a = (382.0, 118.0)
    b = (116.0, 430.0)
    c = (654.0, 430.0)
    outer = (a, b, c)
    if problem.scene_variant == "triangle_median_half":
        d = _midpoint(b, c)
        shaded = (a, b, d)
        ctx.draw.polygon(outer, fill=ctx.fill_color)
        ctx.draw.polygon(shaded, fill=ctx.shaded_color)
        ctx.draw.line([a, b, c, a], fill=ctx.line_color, width=ctx.line_width)
        ctx.draw.line([a, d], fill=ctx.accent_color, width=ctx.line_width)
        ticks_bbox = _draw_equal_ticks(ctx, ((b, d), (d, c)))
        median_bbox = _bbox_from_points((a, d), width=ctx.width, height=ctx.height, pad=10.0)
        partition_bbox = (
            min(ticks_bbox[0], median_bbox[0]),
            min(ticks_bbox[1], median_bbox[1]),
            max(ticks_bbox[2], median_bbox[2]),
            max(ticks_bbox[3], median_bbox[3]),
        )
    elif problem.scene_variant == "triangle_midsegment_quarter":
        e = _midpoint(c, a)
        f = _midpoint(a, b)
        shaded = (a, f, e)
        ctx.draw.polygon(outer, fill=ctx.fill_color)
        ctx.draw.polygon(shaded, fill=ctx.shaded_color)
        ctx.draw.line([a, b, c, a], fill=ctx.line_color, width=ctx.line_width)
        ctx.draw.line([f, e], fill=ctx.accent_color, width=ctx.line_width)
        ticks_bbox = _draw_equal_ticks(ctx, ((a, f), (f, b), (a, e), (e, c)))
        midsegment_bbox = _bbox_from_points((f, e), width=ctx.width, height=ctx.height, pad=10.0)
        partition_bbox = (
            min(ticks_bbox[0], midsegment_bbox[0]),
            min(ticks_bbox[1], midsegment_bbox[1]),
            max(ticks_bbox[2], midsegment_bbox[2]),
            max(ticks_bbox[3], midsegment_bbox[3]),
        )
    else:
        d = _midpoint(b, c)
        e = _midpoint(c, a)
        f = _midpoint(a, b)
        g = _centroid(a, b, c)
        shaded = (a, f, g)
        ctx.draw.polygon(outer, fill=ctx.fill_color)
        ctx.draw.polygon(shaded, fill=ctx.shaded_color)
        ctx.draw.line([a, b, c, a], fill=ctx.line_color, width=ctx.line_width)
        for start, end in ((a, d), (b, e), (c, f)):
            ctx.draw.line([start, end], fill=ctx.accent_color, width=ctx.line_width)
        ctx.draw.ellipse((g[0] - 5.0, g[1] - 5.0, g[0] + 5.0, g[1] + 5.0), fill=ctx.accent_color)
        partition_bbox = _bbox_from_points((a, b, c, d, e, f, g), width=ctx.width, height=ctx.height, pad=10.0)
    outer_bbox = _bbox_from_points(outer, width=ctx.width, height=ctx.height, pad=8.0)
    shaded_bbox = _bbox_from_points(shaded, width=ctx.width, height=ctx.height, pad=8.0)
    return outer, shaded, outer_bbox, shaded_bbox, partition_bbox


def _render_area_partition_scene(
    ctx: _RenderContext, problem: _ResolvedProblem
) -> _RenderedAreaPartitionScene:
    if problem.scene_variant.startswith("parallelogram"):
        outer_points, shaded_points, outer_bbox, shaded_bbox, partition_bbox = _draw_parallelogram(ctx, problem)
        shape_type = "parallelogram"
    else:
        outer_points, shaded_points, outer_bbox, shaded_bbox, partition_bbox = _draw_triangle(ctx, problem)
        shape_type = "triangle"

    label_bboxes: Dict[str, BBox] = {}
    label_bboxes["given_area"] = _draw_label(
        ctx, f"shaded area={problem.shaded_area}", (570.0, 82.0), small=True
    )
    label_bboxes["target"] = _draw_label(ctx, "total area=?", (570.0, 510.0), small=True)
    evidence_roles = (
        "target_total_area_cue",
        "shaded_region",
        "given_shaded_area_label",
        "partition_marks",
    )
    evidence_bboxes = (
        label_bboxes["target"],
        shaded_bbox,
        label_bboxes["given_area"],
        partition_bbox,
    )
    scene_entities = (
        {
            "entity_id": "outer_shape",
            "entity_type": shape_type,
            "bbox": _bbox_to_list(outer_bbox),
            "points": [[round(x, 3), round(y, 3)] for x, y in outer_points],
        },
        {
            "entity_id": "shaded_region",
            "entity_type": "area_partition_region",
            "bbox": _bbox_to_list(shaded_bbox),
            "points": [[round(x, 3), round(y, 3)] for x, y in shaded_points],
        },
    )
    witness = {
        "formula_family": str(problem.query_id),
        "scene_variant": str(problem.scene_variant),
        "shape_type": shape_type,
        "shaded_area": int(problem.shaded_area),
        "shaded_fraction_numerator": 1,
        "shaded_fraction_denominator": int(problem.denominator),
        "formula": str(problem.formula),
        "answer_value": float(problem.answer),
    }
    return _RenderedAreaPartitionScene(
        image=ctx.image,
        answer=float(problem.answer),
        evidence_bboxes=tuple(evidence_bboxes),
        evidence_roles=tuple(evidence_roles),
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map={
            "outer_shape": {
                "type": shape_type,
                "points": [[round(x, 3), round(y, 3)] for x, y in outer_points],
                "bbox": _bbox_to_list(outer_bbox),
            },
            "shaded_region": {
                "points": [[round(x, 3), round(y, 3)] for x, y in shaded_points],
                "bbox": _bbox_to_list(shaded_bbox),
            },
            "partition_bbox": _bbox_to_list(partition_bbox),
            "label_bboxes": {
                key: _bbox_to_list(value) for key, value in label_bboxes.items()
            },
            "coord_space": "pixel",
        },
        witness=witness,
    )


class _AreaPartitionBaseTask:
    """Shared implementation for area-partition theorem tasks."""

    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    scene_id = ""
    public_scene_id = ""
    partition_cases: Sequence[Tuple[str, int, int]] = ()
    supported_queries: Sequence[str] = ()
    reasoning_kind = "area_partition"

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
        palettes: Tuple[Tuple[Color, Color, Color, Color], ...] = (
            ((229, 240, 255), (67, 140, 214), (27, 113, 191), (160, 176, 190)),
            ((255, 240, 225), (213, 120, 60), (180, 88, 36), (164, 150, 136)),
            ((238, 235, 255), (128, 102, 205), (111, 92, 190), (158, 152, 178)),
            ((232, 248, 238), (44, 151, 102), (30, 132, 92), (144, 168, 150)),
        )
        palette_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.palette",
        )
        fill_color, shaded_color, accent_color, muted_color = palettes[
            int(palette_index) % len(palettes)
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
            fill_color=fill_color,
            shaded_color=shaded_color,
            accent_color=accent_color,
            muted_color=muted_color,
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
            "shaded_color": list(shaded_color),
            "accent_color": list(accent_color),
            "muted_color": list(muted_color),
        }
        return ctx, render_meta

    def _build_complexity(self, rendered: _RenderedAreaPartitionScene) -> TaskComplexity:
        visual_scan = clamp_unit_interval(
            0.48
            + normalize_linear(len(rendered.evidence_bboxes), min_value=3, max_value=5)
            * 0.18
        )
        denominator = int(rendered.witness.get("shaded_fraction_denominator", 2))
        precision = 0.56 + (0.06 if denominator >= 4 else 0.0) + (0.08 if denominator >= 6 else 0.0)
        ambiguity = 0.48 + (0.08 if denominator >= 4 else 0.0) + (0.08 if denominator >= 6 else 0.0)
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
            raise ValueError(f"{self.task_id} defines no area-partition query support")
        _gen_defaults, render_defaults, prompt_defaults = (
            split_generation_rendering_prompt_defaults(
                _TASK_GROUP_DEFAULTS,
                task_id=str(self.task_id),
            )
        )
        problem = _resolve_problem(
            task_id=str(self.task_id),
            scene_id=str(self.scene_id),
            partition_cases=tuple(self.partition_cases),
            supported_queries=tuple(self.supported_queries),
            instance_seed=int(instance_seed),
            params=params,
        )
        scene_id = str(problem.scene_id)
        last_error: Exception | None = None
        rendered: _RenderedAreaPartitionScene | None = None
        render_meta: Dict[str, Any] | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                ctx, render_meta_attempt = self._make_render_context(
                    instance_seed=int(instance_seed),
                    params=params,
                    render_defaults=render_defaults,
                )
                rendered = _render_area_partition_scene(ctx, problem)
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
            "scene_id": scene_id,
            "scene_variant": str(problem.scene_variant),
            "query_id": str(problem.query_id),
            "query_id_probabilities": dict(problem.query_probabilities),
            "target_support_probabilities": dict(problem.support_probabilities),
            **dict(rendered.witness),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_area_partition",
                "scene_id": scene_id,
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_id": str(problem.query_id),
                    "scene_variant": str(problem.scene_variant),
                    "answer_value": float(rendered.answer),
                    "evidence_roles": list(rendered.evidence_roles),
                },
            },
            "query_spec": {
                "scene_id": scene_id,
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
                "scene_id": scene_id,
                "scene_variant": str(problem.scene_variant),
                "query_id": str(problem.query_id),
                "query_id_probabilities": dict(problem.query_probabilities),
                "answer_type": "number",
                "answer_value": float(rendered.answer),
                "answer_rounding": "integer",
                "evidence_roles": list(rendered.evidence_roles),
                "reasoning_steps": 1,
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "type": "area_partition_formula",
                "scene_id": scene_id,
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
            scene_id=scene_id,
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometryParallelogramAreaPartitionTotalAreaValueTask(_AreaPartitionBaseTask):
    """Infer total area from a shaded parallelogram partition region."""

    task_id = "task_geometry__area_partition__parallelogram_area_partition_total_area_value"
    scene_id = PARALLELOGRAM_SCENE_ID
    public_scene_id = PARALLELOGRAM_SCENE_ID
    partition_cases = _PARALLELOGRAM_PARTITION_CASES
    supported_queries = _TOTAL_AREA_QUERIES
    reasoning_kind = "total_area"


@register_task
class GeometryTriangleAreaPartitionTotalAreaValueTask(_AreaPartitionBaseTask):
    """Infer total area from a shaded triangle partition region."""

    task_id = "task_geometry__area_partition__triangle_area_partition_total_area_value"
    scene_id = TRIANGLE_SCENE_ID
    public_scene_id = TRIANGLE_SCENE_ID
    partition_cases = _TRIANGLE_PARTITION_CASES
    supported_queries = _TOTAL_AREA_QUERIES
    reasoning_kind = "total_area"


__all__ = [
    "GeometryParallelogramAreaPartitionTotalAreaValueTask",
    "GeometryTriangleAreaPartitionTotalAreaValueTask",
    "PARALLELOGRAM_SCENE_ID",
    "TRIANGLE_SCENE_ID",
]
