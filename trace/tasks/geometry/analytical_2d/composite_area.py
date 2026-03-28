"""Composite/shaded analytical 2D area task with derived polygon scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from PIL import ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import resolve_scene_label_font_size_px
from ..shared.analytical_2d_scene import (
    Analytical2DAnnotationSpec,
    Analytical2DPolygonEntitySpec,
    Analytical2DSceneBlueprint,
    Analytical2DSegmentEntitySpec,
    analytical_unit_spacing_px,
    render_analytical_2d_scene,
)
from ..shared.analytical_task import required_prompt_text, resolve_answer_bounds, resolve_task_variant
from ..shared.background_defaults import load_geometry_background_defaults
from ..shared.complexity import build_geometry_analytical_complexity
from ..shared.graph_rendering import graph_paper_grid_from_frame
from ..shared.noise_defaults import load_geometry_noise_defaults
from ..shared.render_variation import sample_int_render_param
from ..shared.shape_style import extract_background_anchor_colors, sample_geometry_shape_style
from ..shared.single_object_scene import (
    GraphSceneContext,
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)
from .defaults import ANALYTICAL_SHARED_DEFAULTS

COMPOSITE_AREA_VARIANTS: Tuple[str, ...] = (
    "rectangle_inner_cutout",
    "rectangle_triangle_cutout",
    "rectangle_triangle_union",
    "l_shape_cutout",
    "step_rectangles_union",
)

ANALYTICAL_POST_IMAGE_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="analytical_2d")
ANALYTICAL_POST_IMAGE_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="analytical_2d")


@dataclass(frozen=True)
class _CompositeAreaCase:
    """Rendered analytical composite-area case payload."""

    task_variant: str
    answer_value: int
    answer_scalar: int
    formula_expression: str
    evidence_roles: Tuple[str, ...]
    role_values: Dict[str, Any]
    role_tokens: Dict[str, str]
    evidence_map: Dict[str, Any]
    annotation_centers: Dict[str, list[float]]
    entities: list[Dict[str, Any]]
    render_anchor: Dict[str, Any]


def _dimension_bounds(params: Mapping[str, Any], gen_defaults: Mapping[str, Any]) -> Tuple[int, int]:
    """Resolve inclusive integer dimension bounds for analytical composite-area variants."""
    minimum = int(params.get("dimension_min", gen_defaults.get("dimension_min", 4)))
    maximum = int(params.get("dimension_max", gen_defaults.get("dimension_max", 40)))
    if int(minimum) < 2 or int(minimum) > int(maximum):
        raise ValueError("invalid dimension_min/dimension_max for analytical 2D composite area")
    return int(minimum), int(maximum)


def _answer_in_bounds(answer_value: int, *, answer_min: int, answer_max: int) -> bool:
    """Return true when one sampled integer answer falls within inclusive bounds."""
    return int(answer_min) <= int(answer_value) <= int(answer_max)


def _background_fill_color(background_meta: Mapping[str, Any]) -> Tuple[int, int, int]:
    """Extract one solid background color for cutout rendering."""
    style_spec = background_meta.get("style_spec", {}) if isinstance(background_meta, Mapping) else {}
    if isinstance(style_spec, Mapping):
        color = style_spec.get("color")
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            return (int(color[0]), int(color[1]), int(color[2]))
    return (252, 252, 252)


def _sample_rectangle_inner_cutout(
    rng,
    *,
    answer_min: int,
    answer_max: int,
    dimension_min: int,
    dimension_max: int,
) -> Tuple[Analytical2DSceneBlueprint, int, str]:
    """Shaded rectangular frame defined by an outer rectangle and one inner cutout."""
    for _ in range(600):
        outer_w = int(rng.randint(max(6, int(dimension_min)), max(6, int(dimension_max))))
        outer_h = int(rng.randint(max(6, int(dimension_min)), max(6, int(dimension_max))))
        if int(outer_w) <= 4 or int(outer_h) <= 4:
            continue
        inner_w = int(rng.randint(2, int(outer_w) - 2))
        inner_h = int(rng.randint(2, int(outer_h) - 2))
        max_left = int(outer_w) - int(inner_w) - 1
        max_bottom = int(outer_h) - int(inner_h) - 1
        if int(max_left) < 1 or int(max_bottom) < 1:
            continue
        inner_left = int(rng.randint(1, int(max_left)))
        inner_bottom = int(rng.randint(1, int(max_bottom)))
        answer = (int(outer_w) * int(outer_h)) - (int(inner_w) * int(inner_h))
        if not _answer_in_bounds(int(answer), answer_min=int(answer_min), answer_max=int(answer_max)):
            continue
        point_units = {
            "A": (0.0, 0.0),
            "B": (float(outer_w), 0.0),
            "C": (float(outer_w), float(outer_h)),
            "D": (0.0, float(outer_h)),
            "E": (float(inner_left), float(inner_bottom)),
            "F": (float(inner_left + inner_w), float(inner_bottom)),
            "G": (float(inner_left + inner_w), float(inner_bottom + inner_h)),
            "H": (float(inner_left), float(inner_bottom + inner_h)),
        }
        blueprint = Analytical2DSceneBlueprint(
            point_units=point_units,
            fit_points=tuple(point_units[point_id] for point_id in ("A", "B", "C", "D")),
            polygon_entities=(
                Analytical2DPolygonEntitySpec("outer_rect", "rectangle", ("A", "B", "C", "D"), fill_kind="shaded"),
                Analytical2DPolygonEntitySpec("inner_rect", "cutout_rectangle", ("E", "F", "G", "H"), fill_kind="background"),
            ),
            circle_entities=(),
            segment_entities=(),
            annotation_specs=(
                Analytical2DAnnotationSpec("outer_width", "A", "B", offset_scale=0.95),
                Analytical2DAnnotationSpec("outer_height", "B", "C", offset_scale=0.95),
                Analytical2DAnnotationSpec("inner_width", "E", "F", offset_scale=0.95, direction_override=(0.0, -1.0)),
                Analytical2DAnnotationSpec("inner_height", "F", "G", offset_scale=0.95, direction_override=(1.0, 0.0)),
            ),
            label_point_ids=("A", "B", "C", "E", "F", "G"),
            label_directions={
                "E": (-1.0, -1.0),
                "F": (1.0, -1.0),
                "G": (1.0, 1.0),
            },
            evidence_roles=("outer_width", "outer_height", "inner_width", "inner_height"),
            role_values={
                "outer_width": int(outer_w),
                "outer_height": int(outer_h),
                "inner_width": int(inner_w),
                "inner_height": int(inner_h),
            },
        )
        return blueprint, int(answer), "outer_width * outer_height - inner_width * inner_height"
    raise ValueError("failed to sample rectangle_inner_cutout")


def _sample_rectangle_triangle_cutout(
    rng,
    *,
    answer_min: int,
    answer_max: int,
    dimension_min: int,
    dimension_max: int,
) -> Tuple[Analytical2DSceneBlueprint, int, str]:
    """Rectangle with one right-triangle corner removed from the shaded region."""
    for _ in range(600):
        outer_w = int(rng.randint(max(6, int(dimension_min)), max(6, int(dimension_max))))
        outer_h = int(rng.randint(max(6, int(dimension_min)), max(6, int(dimension_max))))
        cut_top = int(rng.randint(2, int(outer_w) - 1))
        cut_right = int(rng.randint(2, int(outer_h) - 1))
        if (int(cut_top) * int(cut_right)) % 2 != 0:
            continue
        answer = (int(outer_w) * int(outer_h)) - ((int(cut_top) * int(cut_right)) // 2)
        if not _answer_in_bounds(int(answer), answer_min=int(answer_min), answer_max=int(answer_max)):
            continue
        point_units = {
            "A": (0.0, 0.0),
            "B": (float(outer_w), 0.0),
            "C": (float(outer_w), float(outer_h)),
            "D": (0.0, float(outer_h)),
            "E": (float(outer_w - cut_top), float(outer_h)),
            "F": (float(outer_w), float(outer_h - cut_right)),
        }
        blueprint = Analytical2DSceneBlueprint(
            point_units=point_units,
            fit_points=tuple(point_units[point_id] for point_id in ("A", "B", "C", "D")),
            polygon_entities=(
                Analytical2DPolygonEntitySpec("outer_rect", "rectangle", ("A", "B", "C", "D"), fill_kind="shaded"),
                Analytical2DPolygonEntitySpec("cut_triangle", "cutout_triangle", ("E", "C", "F"), fill_kind="background"),
            ),
            circle_entities=(),
            segment_entities=(),
            annotation_specs=(
                Analytical2DAnnotationSpec("outer_width", "A", "B", offset_scale=0.95),
                Analytical2DAnnotationSpec("outer_height", "B", "C", offset_scale=0.95),
                Analytical2DAnnotationSpec("cut_top", "E", "C", offset_scale=1.0, direction_override=(0.0, 1.0)),
                Analytical2DAnnotationSpec("cut_right", "F", "C", offset_scale=1.0, direction_override=(1.0, 0.0)),
            ),
            label_point_ids=("A", "B", "C", "E", "F"),
            label_directions={
                "E": (-1.0, 1.0),
                "F": (1.0, -1.0),
            },
            evidence_roles=("outer_width", "outer_height", "cut_top", "cut_right"),
            role_values={
                "outer_width": int(outer_w),
                "outer_height": int(outer_h),
                "cut_top": int(cut_top),
                "cut_right": int(cut_right),
            },
        )
        return blueprint, int(answer), "outer_width * outer_height - (cut_top * cut_right) / 2"
    raise ValueError("failed to sample rectangle_triangle_cutout")


def _sample_rectangle_triangle_union(
    rng,
    *,
    answer_min: int,
    answer_max: int,
    dimension_min: int,
    dimension_max: int,
) -> Tuple[Analytical2DSceneBlueprint, int, str]:
    """House-like union of one rectangle and one roof triangle."""
    for _ in range(600):
        width = int(rng.randint(max(4, int(dimension_min)), int(dimension_max)))
        rect_height = int(rng.randint(max(4, int(dimension_min)), int(dimension_max)))
        roof_height = int(rng.randint(max(2, int(dimension_min) // 2), max(3, int(dimension_max // 2) + 1)))
        if (int(width) * int(roof_height)) % 2 != 0:
            continue
        answer = (int(width) * int(rect_height)) + ((int(width) * int(roof_height)) // 2)
        if not _answer_in_bounds(int(answer), answer_min=int(answer_min), answer_max=int(answer_max)):
            continue
        half_width = float(width) / 2.0
        point_units = {
            "A": (0.0, 0.0),
            "B": (float(width), 0.0),
            "C": (float(width), float(rect_height)),
            "D": (0.0, float(rect_height)),
            "E": (float(half_width), float(rect_height + roof_height)),
            "M": (float(half_width), float(rect_height)),
        }
        blueprint = Analytical2DSceneBlueprint(
            point_units=point_units,
            fit_points=((0.0, 0.0), (float(width), 0.0), (float(width), float(rect_height + roof_height)), (0.0, float(rect_height + roof_height))),
            polygon_entities=(
                Analytical2DPolygonEntitySpec("rect_body", "rectangle", ("A", "B", "C", "D"), fill_kind="shaded"),
                Analytical2DPolygonEntitySpec("roof_tri", "isosceles_triangle", ("D", "C", "E"), fill_kind="shaded"),
            ),
            circle_entities=(),
            segment_entities=(Analytical2DSegmentEntitySpec("roof_height", "altitude", "M", "E", True),),
            annotation_specs=(
                Analytical2DAnnotationSpec("width", "A", "B", offset_scale=0.95),
                Analytical2DAnnotationSpec("rect_height", "B", "C", offset_scale=0.95),
                Analytical2DAnnotationSpec("roof_height", "M", "E", offset_scale=1.15, direction_override=(1.0, 0.0)),
            ),
            label_point_ids=("A", "B", "C", "D", "E", "M"),
            label_directions={"M": (1.0, 0.0)},
            evidence_roles=("width", "rect_height", "roof_height"),
            role_values={
                "width": int(width),
                "rect_height": int(rect_height),
                "roof_height": int(roof_height),
            },
        )
        return blueprint, int(answer), "width * rect_height + (width * roof_height) / 2"
    raise ValueError("failed to sample rectangle_triangle_union")


def _sample_l_shape_cutout(
    rng,
    *,
    answer_min: int,
    answer_max: int,
    dimension_min: int,
    dimension_max: int,
) -> Tuple[Analytical2DSceneBlueprint, int, str]:
    """L-shaped shaded region sampled from an outer rectangle with one corner removed."""
    for _ in range(600):
        outer_w = int(rng.randint(max(6, int(dimension_min)), max(6, int(dimension_max))))
        outer_h = int(rng.randint(max(6, int(dimension_min)), max(6, int(dimension_max))))
        cut_w = int(rng.randint(2, int(outer_w) - 2))
        cut_h = int(rng.randint(2, int(outer_h) - 2))
        answer = (int(outer_w) * int(outer_h)) - (int(cut_w) * int(cut_h))
        if not _answer_in_bounds(int(answer), answer_min=int(answer_min), answer_max=int(answer_max)):
            continue
        point_units = {
            "A": (0.0, 0.0),
            "B": (float(outer_w), 0.0),
            "C": (float(outer_w), float(outer_h - cut_h)),
            "D": (float(outer_w - cut_w), float(outer_h - cut_h)),
            "E": (float(outer_w - cut_w), float(outer_h)),
            "F": (0.0, float(outer_h)),
        }
        blueprint = Analytical2DSceneBlueprint(
            point_units=point_units,
            fit_points=tuple(point_units.values()),
            polygon_entities=(Analytical2DPolygonEntitySpec("l_shape", "l_shape", ("A", "B", "C", "D", "E", "F"), fill_kind="shaded"),),
            circle_entities=(),
            segment_entities=(),
            annotation_specs=(
                Analytical2DAnnotationSpec("outer_width", "A", "B", offset_scale=0.95),
                Analytical2DAnnotationSpec("outer_height", "F", "A", offset_scale=0.95),
                Analytical2DAnnotationSpec("cut_width", "D", "C", offset_scale=1.0, direction_override=(0.0, -1.0)),
                Analytical2DAnnotationSpec("cut_height", "D", "E", offset_scale=1.0, direction_override=(1.0, 0.0)),
            ),
            label_point_ids=("A", "B", "C", "D", "E", "F"),
            label_directions={
                "D": (1.0, -1.0),
                "E": (1.0, 1.0),
            },
            evidence_roles=("outer_width", "outer_height", "cut_width", "cut_height"),
            role_values={
                "outer_width": int(outer_w),
                "outer_height": int(outer_h),
                "cut_width": int(cut_w),
                "cut_height": int(cut_h),
            },
        )
        return blueprint, int(answer), "outer_width * outer_height - cut_width * cut_height"
    raise ValueError("failed to sample l_shape_cutout")


def _sample_step_rectangles_union(
    rng,
    *,
    answer_min: int,
    answer_max: int,
    dimension_min: int,
    dimension_max: int,
) -> Tuple[Analytical2DSceneBlueprint, int, str]:
    """Step-shaped shaded union of two non-overlapping rectangles."""
    for _ in range(600):
        left_width = int(rng.randint(max(3, int(dimension_min)), int(dimension_max)))
        right_width = int(rng.randint(max(2, int(dimension_min) // 2), max(3, int(dimension_max // 2) + 1)))
        left_height = int(rng.randint(max(5, int(dimension_min) + 1), max(6, int(dimension_max))))
        right_height = int(rng.randint(2, max(3, int(left_height) - 1)))
        if int(right_height) >= int(left_height):
            continue
        answer = (int(left_width) * int(left_height)) + (int(right_width) * int(right_height))
        if not _answer_in_bounds(int(answer), answer_min=int(answer_min), answer_max=int(answer_max)):
            continue
        point_units = {
            "A": (0.0, 0.0),
            "B": (float(left_width + right_width), 0.0),
            "C": (float(left_width + right_width), float(right_height)),
            "D": (float(left_width), float(right_height)),
            "E": (float(left_width), float(left_height)),
            "F": (0.0, float(left_height)),
        }
        blueprint = Analytical2DSceneBlueprint(
            point_units=point_units,
            fit_points=tuple(point_units.values()),
            polygon_entities=(Analytical2DPolygonEntitySpec("step_union", "step_shape", ("A", "B", "C", "D", "E", "F"), fill_kind="shaded"),),
            circle_entities=(),
            segment_entities=(),
            annotation_specs=(
                Analytical2DAnnotationSpec("left_width", "F", "E", offset_scale=1.05, direction_override=(0.0, 1.0)),
                Analytical2DAnnotationSpec("left_height", "F", "A", offset_scale=0.95),
                Analytical2DAnnotationSpec("right_width", "D", "C", offset_scale=1.0, direction_override=(0.0, 1.0)),
                Analytical2DAnnotationSpec("right_height", "B", "C", offset_scale=1.0),
            ),
            label_point_ids=("A", "B", "C", "D", "E", "F"),
            label_directions={
                "D": (1.0, 1.0),
                "E": (1.0, 1.0),
            },
            evidence_roles=("left_width", "left_height", "right_width", "right_height"),
            role_values={
                "left_width": int(left_width),
                "left_height": int(left_height),
                "right_width": int(right_width),
                "right_height": int(right_height),
            },
        )
        return blueprint, int(answer), "left_width * left_height + right_width * right_height"
    raise ValueError("failed to sample step_rectangles_union")


def sample_analytical_2d_composite_area_case(
    rng,
    draw: ImageDraw.ImageDraw,
    *,
    task_variant: str,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    context: GraphSceneContext,
    shape_style,
    line_width: int,
    helper_line_width: int,
    label_offset_px: float,
    label_font_size_px: int,
    label_stroke_width: int,
    fill_ratio: float,
    answer_min: int,
    answer_max: int,
    background_fill_color: Tuple[int, int, int],
) -> _CompositeAreaCase:
    """Sample and render one analytical 2D composite-area case."""
    dimension_min, dimension_max = _dimension_bounds(params, generation_defaults)
    samplers = {
        "rectangle_inner_cutout": lambda: _sample_rectangle_inner_cutout(
            rng,
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            dimension_min=int(dimension_min),
            dimension_max=int(dimension_max),
        ),
        "rectangle_triangle_cutout": lambda: _sample_rectangle_triangle_cutout(
            rng,
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            dimension_min=int(dimension_min),
            dimension_max=int(dimension_max),
        ),
        "rectangle_triangle_union": lambda: _sample_rectangle_triangle_union(
            rng,
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            dimension_min=int(dimension_min),
            dimension_max=int(dimension_max),
        ),
        "l_shape_cutout": lambda: _sample_l_shape_cutout(
            rng,
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            dimension_min=int(dimension_min),
            dimension_max=int(dimension_max),
        ),
        "step_rectangles_union": lambda: _sample_step_rectangles_union(
            rng,
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            dimension_min=int(dimension_min),
            dimension_max=int(dimension_max),
        ),
    }
    if str(task_variant) not in samplers:
        raise ValueError(f"unsupported analytical 2D composite-area task_variant: {task_variant}")
    blueprint, answer_value, formula_expression = samplers[str(task_variant)]()
    rendered = render_analytical_2d_scene(
        rng,
        draw,
        blueprint=blueprint,
        context=context,
        shape_style=shape_style,
        line_width=int(line_width),
        helper_line_width=int(helper_line_width),
        label_offset_px=float(label_offset_px),
        label_font_size_px=int(label_font_size_px),
        label_stroke_width=int(label_stroke_width),
        fill_ratio=float(fill_ratio),
        background_fill_color=tuple(int(value) for value in background_fill_color),
    )
    return _CompositeAreaCase(
        task_variant=str(task_variant),
        answer_value=int(answer_value),
        answer_scalar=int(answer_value),
        formula_expression=str(formula_expression),
        evidence_roles=tuple(str(role) for role in blueprint.evidence_roles),
        role_values=dict(blueprint.role_values),
        role_tokens=dict(rendered.role_tokens),
        evidence_map=dict(rendered.evidence_map),
        annotation_centers=dict(rendered.annotation_centers),
        entities=list(rendered.entities),
        render_anchor=dict(rendered.render_anchor),
    )


@register_task
class GeometryAnalyticalCompositeArea2DTask:
    """Compute shaded/composite area values from annotated analytical 2D scenes."""

    task_id = "task_geometry_analytical_2d_composite_area"
    domain = "geometry"
    task_group = "analytical_2d"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic analytical 2D composite-area instance."""
        task_group_defaults = get_task_group_defaults(self.domain, self.task_group)
        gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            task_group_defaults if isinstance(task_group_defaults, Mapping) else {},
            task_id=str(self.task_id),
        )
        answer_min, answer_max = resolve_answer_bounds(
            params,
            gen_defaults=gen_defaults,
            task_id=str(self.task_id),
            fallback_min=20,
            fallback_max=2500,
        )
        scene_rng = spawn_rng(int(instance_seed), "scene")
        task_variant, variant_probabilities = resolve_task_variant(
            scene_rng,
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
            supported_variants=COMPOSITE_AREA_VARIANTS,
        )
        context_params = dict(params)
        line_width = sample_int_render_param(
            scene_rng,
            params=context_params,
            render_defaults=render_defaults,
            key="line_width",
            fallback=int(ANALYTICAL_SHARED_DEFAULTS.line_width),
            min_key="line_width_min",
            max_key="line_width_max",
            minimum_value=1,
        )
        helper_line_width = sample_int_render_param(
            scene_rng,
            params=context_params,
            render_defaults=render_defaults,
            key="helper_line_width",
            fallback=int(ANALYTICAL_SHARED_DEFAULTS.helper_line_width),
            min_key="helper_line_width_min",
            max_key="helper_line_width_max",
            minimum_value=1,
        )
        label_stroke_width = sample_int_render_param(
            scene_rng,
            params=context_params,
            render_defaults=render_defaults,
            key="label_stroke_width",
            fallback=int(ANALYTICAL_SHARED_DEFAULTS.label_stroke_width),
            min_key="label_stroke_width_min",
            max_key="label_stroke_width_max",
            minimum_value=1,
        )
        fill_ratio = float(group_default(render_defaults, "analytical_scene_fill_ratio", 0.74))

        attempt_budget = max(1, int(max_attempts))
        context: GraphSceneContext | None = None
        image = None
        background_meta: Dict[str, Any] = {}
        shape_style = None
        case = None
        last_error: Exception | None = None

        for _ in range(int(attempt_budget)):
            try:
                context = resolve_graph_scene_context(
                    scene_rng,
                    params=context_params,
                    render_defaults=render_defaults,
                    background_defaults=ANALYTICAL_POST_IMAGE_BACKGROUND_DEFAULTS,
                    fallback_canvas_min=ANALYTICAL_SHARED_DEFAULTS.canvas_size_min,
                    fallback_canvas_max=ANALYTICAL_SHARED_DEFAULTS.canvas_size_max,
                    fallback_cells_min=ANALYTICAL_SHARED_DEFAULTS.graph_cells_min,
                    fallback_cells_max=ANALYTICAL_SHARED_DEFAULTS.graph_cells_max,
                    require_graph_paper_background=False,
                )
                label_offset_px = float(group_default(render_defaults, "label_offset_px", ANALYTICAL_SHARED_DEFAULTS.label_offset_px))
                label_font_size_px = resolve_scene_label_font_size_px(
                    canvas_size=int(context.canvas_size),
                    graph_spacing=int(analytical_unit_spacing_px(context)),
                    scene_scale=int(context.scene_scale),
                    min_px=int(group_default(render_defaults, "label_font_size_min", ANALYTICAL_SHARED_DEFAULTS.label_font_size_min)),
                    max_px=int(group_default(render_defaults, "label_font_size_max", ANALYTICAL_SHARED_DEFAULTS.label_font_size_max)),
                )
                image, draw, background_meta = make_graph_scene_canvas(
                    instance_seed=int(instance_seed),
                    context=context,
                    background_defaults=ANALYTICAL_POST_IMAGE_BACKGROUND_DEFAULTS,
                    require_graph_paper=False,
                )
                shape_style = sample_geometry_shape_style(
                    scene_rng,
                    params=context_params,
                    render_defaults=render_defaults,
                    anchor_colors=extract_background_anchor_colors(background_meta),
                )
                case = sample_analytical_2d_composite_area_case(
                    scene_rng,
                    draw,
                    task_variant=str(task_variant),
                    params=params,
                    generation_defaults=gen_defaults,
                    context=context,
                    shape_style=shape_style,
                    line_width=int(line_width),
                    helper_line_width=int(helper_line_width),
                    label_offset_px=float(label_offset_px),
                    label_font_size_px=int(label_font_size_px),
                    label_stroke_width=int(label_stroke_width),
                    fill_ratio=float(fill_ratio),
                    answer_min=int(answer_min),
                    answer_max=int(answer_max),
                    background_fill_color=_background_fill_color(background_meta),
                )
                break
            except Exception as exc:
                last_error = exc
                context = None
                image = None
                shape_style = None
                case = None
                continue

        if case is None or context is None or image is None or shape_style is None:
            raise RuntimeError("failed to generate task_geometry_analytical_2d_composite_area instance") from last_error

        image, background_meta_final, post_noise_meta = finalize_graph_scene_image(
            image,
            instance_seed=int(instance_seed),
            context=context,
            background_meta=background_meta,
            noise_defaults=ANALYTICAL_POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_required = required_group_defaults(
            prompt_defaults,
            (
                "bundle_id",
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "evidence_hint_measurement_map",
                "answer_hint_integer",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        required_annotations = [
            str(case.role_tokens[role])
            for role in case.evidence_roles
            if str(role) in case.role_tokens
        ]
        evidence_hint_base = str(prompt_required["evidence_hint_measurement_map"]).strip()
        if evidence_hint_base and evidence_hint_base[-1] not in {".", "!", "?", ":", ";"}:
            evidence_hint_base = f"{evidence_hint_base}."
        evidence_hint = (
            f"{evidence_hint_base} Required annotations: {', '.join(required_annotations)}"
            if evidence_hint_base
            else f"Required annotations: {', '.join(required_annotations)}"
        )
        question_text = required_prompt_text(
            prompt_defaults,
            preferred_keys=(f"question_text_{case.task_variant}", "question_text"),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_hint = str(prompt_required["answer_hint_integer"])
        json_example, json_example_answer_only = build_prompt_json_examples(
            evidence_value=case.evidence_map,
            answer_type="integer",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_required["bundle_id"]),
            task_family_key=str(prompt_required["task_family_key"]),
            task_key=str(prompt_required["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_required["object_description"]),
                "question_text": str(question_text),
                "json_output_contract": str(prompt_required["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_required["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(answer_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(case.answer_value))
        evidence_gt = TypedValue(type="measurement_ref_map", value=dict(case.evidence_map))
        complexity = build_geometry_analytical_complexity(
            task_group_defaults=task_group_defaults if isinstance(task_group_defaults, Mapping) else {},
            task_id=str(self.task_id),
            task_kind="composite_area",
            task_variant=str(case.task_variant),
            annotation_count=len(case.evidence_roles),
            answer_format="integer",
        )
        projected_point_set = [
            [float(case.annotation_centers[label][0]), float(case.annotation_centers[label][1])]
            for label in required_annotations
            if label in case.annotation_centers
        ]
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_2d_analytical_composite_area",
                "entities": [dict(entity) for entity in case.entities],
                "relations": {},
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "graph_unit": {
                        "origin_pixel": list(context.graph_frame["origin_pixel"]),
                        "spacing_px": int(context.graph_frame["spacing_px"]),
                        "x_positive": str(context.graph_frame["x_positive"]),
                        "y_positive": str(context.graph_frame["y_positive"]),
                    },
                },
            },
            "query_spec": {
                "task_variant": str(case.task_variant),
                "template_id": str(prompt_required["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "task_variant": str(case.task_variant),
                    "variant_probabilities": dict(variant_probabilities),
                    "answer_min": int(answer_min),
                    "answer_max": int(answer_max),
                },
            },
            "render_spec": {
                "canvas_size": int(context.canvas_size),
                "coord_space": "pixel",
                "background_style": dict(background_meta_final),
                "post_image_noise": dict(post_noise_meta),
                "shape_style": dict(shape_style.to_trace_dict()),
                "graph_coordinate_frame": dict(context.graph_frame),
                "graph_paper_grid": graph_paper_grid_from_frame(context.graph_frame),
            },
            "render_map": {
                "instance_anchor": dict(case.render_anchor),
                "annotation_labels": dict(case.role_tokens),
                "annotation_centers": dict(case.annotation_centers),
                "coord_space": "pixel",
            },
            "execution_trace": {
                "task_variant": str(case.task_variant),
                "formula_expression": str(case.formula_expression),
                "answer_type": "integer",
                "raw_answer_value": int(case.answer_value),
                "answer_scalar": int(case.answer_scalar),
                "answer_value": int(case.answer_value),
                "target_quantity": "area",
                "scene_kind": "composite_region",
                "evidence_roles": list(case.evidence_roles),
                "required_annotations": list(required_annotations),
                "evidence_role_values": dict(case.role_values),
                "evidence_role_tokens": dict(case.role_tokens),
                "evidence_map": dict(case.evidence_map),
                "variant_probabilities": dict(variant_probabilities),
                "answer_min": int(answer_min),
                "answer_max": int(answer_max),
            },
            "witness_symbolic": {
                "type": "annotation_measurement_map",
                "task_variant": str(case.task_variant),
                "formula_expression": str(case.formula_expression),
                "annotation_ids": list(required_annotations),
                "annotation_values": dict(case.evidence_map),
                "annotation_labels": dict(case.role_tokens),
                "measurement_ref_map": dict(case.evidence_map),
            },
            "projected_evidence": {
                "measurement_ref_map": dict(case.evidence_map),
                "id_set": list(required_annotations),
                "pixel_point_set": list(projected_point_set),
                "annotation_labels": dict(case.role_tokens),
                "pixel_annotation_centers": dict(case.annotation_centers),
            },
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img_0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(case.task_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
