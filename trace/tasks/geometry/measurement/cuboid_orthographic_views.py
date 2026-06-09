"""Cuboid orthographic-view measurement tasks."""

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
from ..shared.fixed_query_task import geometry_selected_probability_map as _selected_probability_map
from ..shared.measurement_rendering import (
    bbox_to_list as _bbox_to_list,
    clamp_bbox as _clamp_bbox,
    pad_bbox as _pad_bbox,
    draw_label as _draw_label,
)

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SCENE_ID = "cuboid_views"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_cuboid_orthographic_views_v0"

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

_SURFACE_AREA_QUERIES: Tuple[str, ...] = ("surface_area_from_orthographic_views",)

_CUBOID_CASES: Tuple[Tuple[int, int, int], ...] = (
    (3, 4, 5),
    (4, 5, 6),
    (3, 7, 8),
    (5, 6, 7),
    (4, 6, 9),
    (5, 8, 9),
    (6, 7, 10),
    (6, 9, 11),
    (7, 8, 12),
    (8, 10, 13),
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
    secondary_fill_color: Color
    accent_color: Color
    muted_color: Color
    line_width: int
    font: Any
    small_font: Any


@dataclass(frozen=True)
class _ResolvedProblem:
    query_id: str
    answer: float
    length: int
    width: int
    height: int
    formula: str
    top_view_perimeter: int
    front_view_perimeter: int
    right_view_perimeter: int
    query_probabilities: Dict[str, float]
    support_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedCuboidViewsScene:
    image: Image.Image
    answer: float
    annotation_bboxes: Mapping[str, BBox]
    annotation_roles: Tuple[str, ...]
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
) -> BBox:
    ctx.draw.line([start, end], fill=ctx.label_color, width=max(2, ctx.line_width - 1))
    tick = 7.0
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = (dx**2 + dy**2) ** 0.5
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


def _rect_in_slot(unit_w: float, unit_h: float, slot: BBox, *, scale: float) -> BBox:
    x0, y0, x1, y1 = [float(value) for value in slot]
    slot_w = x1 - x0
    slot_h = y1 - y0
    rect_w = min(slot_w, float(unit_w) * scale)
    rect_h = min(slot_h, float(unit_h) * scale)
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    return (cx - rect_w / 2.0, cy - rect_h / 2.0, cx + rect_w / 2.0, cy + rect_h / 2.0)


def _draw_view_rect(
    ctx: _RenderContext,
    bbox: BBox,
    *,
    title: str,
    title_y: float,
    fill: Color,
) -> None:
    ctx.draw.rounded_rectangle(
        bbox,
        radius=4,
        fill=fill,
        outline=ctx.line_color,
        width=ctx.line_width,
    )
    _draw_label(ctx, title, ((float(bbox[0]) + float(bbox[2])) / 2.0, title_y), small=True)


def _answer_for_case(query_id: str, case: Sequence[int]) -> float:
    length, width, height = [float(value) for value in case]
    if query_id == "surface_area_from_orthographic_views":
        return 2.0 * ((length * width) + (length * height) + (width * height))
    raise ValueError(f"unsupported cuboid orthographic query_id: {query_id}")


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
    selected_case = _CUBOID_CASES[int(case_index) % len(_CUBOID_CASES)]
    length = int(params.get("length_units", selected_case[0]))
    width = int(params.get("width_units", selected_case[1]))
    height = int(params.get("height_units", selected_case[2]))
    if length <= 0 or width <= 0 or height <= 0:
        raise ValueError("cuboid length, width, and height must be positive")

    if query_id == "surface_area_from_orthographic_views":
        answer = 2 * ((length * width) + (length * height) + (width * height))
        formula = "recover L, W, H from the three view perimeters, then SA = 2(LW + LH + WH)"
    else:
        raise ValueError(f"unsupported cuboid orthographic query_id: {query_id}")

    support_values = tuple(_answer_for_case(query_id, case) for case in _CUBOID_CASES)
    return _ResolvedProblem(
        query_id=str(query_id),
        answer=float(answer),
        length=int(length),
        width=int(width),
        height=int(height),
        formula=str(formula),
        top_view_perimeter=int(2 * (length + width)),
        front_view_perimeter=int(2 * (length + height)),
        right_view_perimeter=int(2 * (width + height)),
        query_probabilities=dict(query_probabilities),
        support_probabilities=_selected_probability_map(
            tuple(sorted(set(float(value) for value in support_values))),
            float(answer),
            key_fn=lambda value: str(int(value)),
            is_selected=lambda value, selected: int(value) == int(selected),
        ),
    )


def _render_cuboid_views_scene(
    ctx: _RenderContext, problem: _ResolvedProblem
) -> _RenderedCuboidViewsScene:
    top_slot = (120.0, 64.0, 454.0, 222.0)
    front_slot = (120.0, 298.0, 454.0, 504.0)
    right_slot = (536.0, 298.0, 760.0, 504.0)
    scale = min(
        (top_slot[2] - top_slot[0]) / float(problem.length),
        (top_slot[3] - top_slot[1]) / float(problem.width),
        (front_slot[2] - front_slot[0]) / float(problem.length),
        (front_slot[3] - front_slot[1]) / float(problem.height),
        (right_slot[2] - right_slot[0]) / float(problem.width),
        (right_slot[3] - right_slot[1]) / float(problem.height),
    )
    top_rect = _rect_in_slot(problem.length, problem.width, top_slot, scale=scale)
    front_rect = _rect_in_slot(problem.length, problem.height, front_slot, scale=scale)
    right_rect = _rect_in_slot(problem.width, problem.height, right_slot, scale=scale)

    label_bboxes: Dict[str, BBox] = {}
    _draw_view_rect(ctx, top_rect, title="Top view", title_y=38.0, fill=ctx.secondary_fill_color)
    _draw_view_rect(ctx, front_rect, title="Front view", title_y=270.0, fill=ctx.fill_color)
    _draw_view_rect(ctx, right_rect, title="Right view", title_y=270.0, fill=ctx.fill_color)

    label_bboxes["top_perimeter"] = _draw_label(
        ctx,
        f"P={problem.top_view_perimeter}",
        ((top_rect[0] + top_rect[2]) / 2.0, (top_rect[1] + top_rect[3]) / 2.0),
        small=True,
    )
    label_bboxes["front_perimeter"] = _draw_label(
        ctx,
        f"P={problem.front_view_perimeter}",
        (
            (front_rect[0] + front_rect[2]) / 2.0,
            (front_rect[1] + front_rect[3]) / 2.0,
        ),
        small=True,
    )
    label_bboxes["right_perimeter"] = _draw_label(
        ctx,
        f"P={problem.right_view_perimeter}",
        (
            (right_rect[0] + right_rect[2]) / 2.0,
            (right_rect[1] + right_rect[3]) / 2.0,
        ),
        small=True,
    )

    # Light alignment guides make the three views read as projections without
    # introducing additional numeric annotation.
    for x in (top_rect[0], top_rect[2]):
        ctx.draw.line(
            [(x, top_rect[3] + 10.0), (x, front_rect[1] - 14.0)],
            fill=ctx.muted_color,
            width=2,
        )
    for y in (front_rect[1], front_rect[3]):
        ctx.draw.line(
            [(front_rect[2] + 16.0, y), (right_rect[0] - 16.0, y)],
            fill=ctx.muted_color,
            width=2,
        )

    label_bboxes["target"] = _draw_label(ctx, "SA=?", (642.0, 112.0), small=False)

    annotation_roles = (
        "top_view",
        "front_view",
        "right_view",
    )
    annotation_bboxes = {
        "top_view": top_rect,
        "front_view": front_rect,
        "right_view": right_rect,
    }
    scene_entities = (
        {
            "entity_id": "top_view",
            "entity_type": "orthographic_rectangle",
            "bbox": _bbox_to_list(top_rect),
            "dimensions": ["length", "width"],
        },
        {
            "entity_id": "front_view",
            "entity_type": "orthographic_rectangle",
            "bbox": _bbox_to_list(front_rect),
            "dimensions": ["length", "height"],
        },
        {
            "entity_id": "right_view",
            "entity_type": "orthographic_rectangle",
            "bbox": _bbox_to_list(right_rect),
            "dimensions": ["width", "height"],
        },
    )
    witness = {
        "formula_family": str(problem.query_id),
        "length": int(problem.length),
        "width": int(problem.width),
        "height": int(problem.height),
        "top_view_perimeter": int(problem.top_view_perimeter),
        "front_view_perimeter": int(problem.front_view_perimeter),
        "right_view_perimeter": int(problem.right_view_perimeter),
        "volume": int(problem.length * problem.width * problem.height),
        "surface_area": int(
            2
            * (
                (problem.length * problem.width)
                + (problem.length * problem.height)
                + (problem.width * problem.height)
            )
        ),
        "formula": str(problem.formula),
        "answer_value": float(problem.answer),
    }
    return _RenderedCuboidViewsScene(
        image=ctx.image,
        answer=float(problem.answer),
        annotation_bboxes=dict(annotation_bboxes),
        annotation_roles=tuple(annotation_roles),
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map={
            "views": {
                "top": _bbox_to_list(top_rect),
                "front": _bbox_to_list(front_rect),
                "right": _bbox_to_list(right_rect),
            },
            "label_bboxes": {
                key: _bbox_to_list(value) for key, value in label_bboxes.items()
            },
            "coord_space": "pixel",
        },
        witness=witness,
    )


class _CuboidOrthographicViewsBaseTask:
    """Shared implementation for cuboid orthographic-view tasks."""

    domain = "geometry"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    supported_queries: Sequence[str] = ()
    reasoning_kind = "cuboid_orthographic_views"

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
                "canvas_width", group_default(render_defaults, "canvas_width", 820)
            )
        )
        height = int(
            params.get(
                "canvas_height", group_default(render_defaults, "canvas_height", 580)
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
            ((225, 239, 255), (238, 246, 236), (27, 113, 191), (160, 176, 190)),
            ((255, 237, 222), (236, 240, 255), (189, 91, 37), (164, 150, 136)),
            ((237, 232, 255), (235, 248, 246), (111, 92, 190), (158, 152, 178)),
            ((230, 247, 235), (255, 239, 219), (30, 132, 92), (144, 168, 150)),
        )
        palette_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.palette",
        )
        fill_color, secondary_fill_color, accent_color, muted_color = palettes[
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
            secondary_fill_color=secondary_fill_color,
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
            "secondary_fill_color": list(secondary_fill_color),
            "accent_color": list(accent_color),
            "muted_color": list(muted_color),
        }
        return ctx, render_meta

    def _build_complexity(self, rendered: _RenderedCuboidViewsScene) -> TaskComplexity:
        visual_scan = clamp_unit_interval(0.46 + normalize_linear(len(rendered.annotation_bboxes), min_value=3, max_value=5) * 0.18)
        precision = 0.68
        ambiguity = 0.54
        output_burden = clamp_unit_interval(
            0.42
            + normalize_linear(len(rendered.annotation_bboxes), min_value=3, max_value=5) * 0.12
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
            raise ValueError(f"{self.task_id} defines no cuboid-view query support")
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
        rendered: _RenderedCuboidViewsScene | None = None
        render_meta: Dict[str, Any] | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                ctx, render_meta_attempt = self._make_render_context(
                    instance_seed=int(instance_seed),
                    params=params,
                    render_defaults=render_defaults,
                )
                rendered = _render_cuboid_views_scene(ctx, problem)
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
                "annotation_hint",
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
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(
                    prompt_defaults["json_output_contract_answer_only"]
                ),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint_number"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(
                    prompt_defaults["json_example_answer_only"]
                ),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        annotation_bbox_map = {
            str(role): _bbox_to_list(bbox) for role, bbox in rendered.annotation_bboxes.items()
        }
        answer_gt = TypedValue(type="number", value=float(rendered.answer))
        annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(annotation_bbox_map))
        query_params = {
            "scene_id": SCENE_ID,
            "scene_variant": "three_view_cuboid_projection",
            "query_id": str(problem.query_id),
            "query_id_probabilities": dict(problem.query_probabilities),
            "target_support_probabilities": dict(problem.support_probabilities),
            **dict(rendered.witness),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_cuboid_orthographic_views",
                "scene_id": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_id": str(problem.query_id),
                    "scene_variant": "three_view_cuboid_projection",
                    "answer_value": float(rendered.answer),
                    "annotation_roles": list(rendered.annotation_roles),
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
                "scene_variant": "three_view_cuboid_projection",
                "query_id": str(problem.query_id),
                "query_id_probabilities": dict(problem.query_probabilities),
                "answer_type": "number",
                "answer_value": float(rendered.answer),
                "answer_rounding": "integer",
                "annotation_roles": list(rendered.annotation_roles),
                "reasoning_steps": 2,
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "type": "cuboid_orthographic_formula",
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "answer_value": float(rendered.answer),
                "source_witness_type": "keyed_bbox_map",
                "original_annotation_value": list(rendered.annotation_roles),
                **dict(rendered.witness),
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_bbox_map),
                "pixel_keyed_bbox_map": dict(annotation_bbox_map),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
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
class GeometryCuboidProjectionSurfaceAreaValueTask(_CuboidOrthographicViewsBaseTask):
    """Compute cuboid surface area from orthographic views."""

    task_id = "task_geometry__cuboid_views__cuboid_projection_surface_area_value"
    supported_queries = _SURFACE_AREA_QUERIES
    reasoning_kind = "surface_area"


__all__ = [
    "GeometryCuboidProjectionSurfaceAreaValueTask",
    "SCENE_ID",
]
