"""Derived analytical 2D perimeter task with annotated scenes."""

from __future__ import annotations

import math
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
    Analytical2DCircleEntitySpec,
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
from ..shared.shape_style import (
    extract_background_anchor_colors,
    sample_geometry_shape_style,
)
from ..shared.single_object_scene import (
    GraphSceneContext,
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)
from .defaults import ANALYTICAL_SHARED_DEFAULTS

PERIMETER_VARIANTS: Tuple[str, ...] = (
    "right_triangle_leg_hypotenuse",
    "rectangle_side_diagonal",
    "rhombus_diagonals",
    "isosceles_trapezoid_bases_height",
    "inscribed_square_diameter",
)

ANALYTICAL_POST_IMAGE_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="analytical_2d")
ANALYTICAL_POST_IMAGE_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="analytical_2d")


@dataclass(frozen=True)
class _PerimeterCase:
    """Rendered analytical perimeter case payload."""

    task_variant: str
    answer_value: float
    raw_answer_value: float
    answer_scalar: int
    formula_expression: str
    evidence_roles: Tuple[str, ...]
    role_values: Dict[str, Any]
    role_tokens: Dict[str, str]
    evidence_map: Dict[str, Any]
    annotation_centers: Dict[str, list[float]]
    entities: list[Dict[str, Any]]
    render_anchor: Dict[str, Any]


def _rounded_tenth(value: float) -> float:
    """Round one numeric answer to the nearest tenth deterministically."""
    return round(float(value) + 1e-9, 1)


def _dimension_bounds(params: Mapping[str, Any], gen_defaults: Mapping[str, Any]) -> Tuple[int, int]:
    """Resolve inclusive integer dimension bounds for analytical perimeter variants."""
    minimum = int(params.get("dimension_min", gen_defaults.get("dimension_min", 4)))
    maximum = int(params.get("dimension_max", gen_defaults.get("dimension_max", 40)))
    if int(minimum) < 1 or int(minimum) > int(maximum):
        raise ValueError("invalid dimension_min/dimension_max for analytical 2D perimeter")
    return int(minimum), int(maximum)


def _circle_radius_bounds(params: Mapping[str, Any], gen_defaults: Mapping[str, Any]) -> Tuple[int, int]:
    """Resolve inclusive integer circle radius bounds."""
    minimum = int(params.get("circle_radius_min", gen_defaults.get("circle_radius_min", 6)))
    maximum = int(params.get("circle_radius_max", gen_defaults.get("circle_radius_max", 36)))
    if int(minimum) < 1 or int(minimum) > int(maximum):
        raise ValueError("invalid circle_radius_min/circle_radius_max for analytical 2D perimeter")
    return int(minimum), int(maximum)


def _answer_in_bounds(raw_answer: float, *, answer_min: int, answer_max: int) -> bool:
    """Return true when the rounded answer stays within inclusive bounds."""
    rounded = _rounded_tenth(float(raw_answer))
    return float(answer_min) <= float(rounded) <= float(answer_max)


def _sample_right_triangle_leg_hypotenuse(
    rng,
    *,
    answer_min: int,
    answer_max: int,
    dimension_min: int,
    dimension_max: int,
) -> Tuple[Analytical2DSceneBlueprint, float, str]:
    """Right triangle with one leg and hypotenuse annotated; infer perimeter."""
    for _ in range(600):
        known_leg = int(rng.randint(max(3, int(dimension_min)), int(dimension_max)))
        hypotenuse = int(
            rng.randint(max(int(known_leg) + 1, int(dimension_min) + 1), max(int(known_leg) + 3, int(dimension_max) + 20))
        )
        residual = float(hypotenuse * hypotenuse) - float(known_leg * known_leg)
        if residual <= 0.0:
            continue
        other_leg = math.sqrt(float(residual))
        if float(other_leg) < 2.0:
            continue
        answer = float(known_leg) + float(hypotenuse) + float(other_leg)
        if not _answer_in_bounds(answer, answer_min=int(answer_min), answer_max=int(answer_max)):
            continue
        point_units = {
            "A": (0.0, 0.0),
            "B": (float(other_leg), 0.0),
            "C": (0.0, float(known_leg)),
        }
        blueprint = Analytical2DSceneBlueprint(
            point_units=point_units,
            fit_points=tuple(point_units.values()),
            polygon_entities=(Analytical2DPolygonEntitySpec("triangle_1", "right_triangle", ("A", "B", "C")),),
            circle_entities=(),
            segment_entities=(),
            annotation_specs=(
                Analytical2DAnnotationSpec("known_leg", "A", "C", offset_scale=0.95),
                Analytical2DAnnotationSpec("hypotenuse", "B", "C", offset_scale=1.1),
            ),
            label_point_ids=("A", "B", "C"),
            label_directions={},
            evidence_roles=("known_leg", "hypotenuse"),
            role_values={"known_leg": int(known_leg), "hypotenuse": int(hypotenuse)},
        )
        return blueprint, float(answer), "known_leg + hypotenuse + sqrt(hypotenuse^2 - known_leg^2)"
    raise ValueError("failed to sample right_triangle_leg_hypotenuse")


def _sample_rectangle_side_diagonal(
    rng,
    *,
    answer_min: int,
    answer_max: int,
    dimension_min: int,
    dimension_max: int,
) -> Tuple[Analytical2DSceneBlueprint, float, str]:
    """Rectangle with one side and diagonal annotated; infer perimeter."""
    for _ in range(600):
        height = int(rng.randint(max(2, int(dimension_min)), int(dimension_max)))
        diagonal = int(rng.randint(max(int(height) + 1, int(dimension_min) + 1), max(int(height) + 3, int(dimension_max) + 20)))
        residual = float(diagonal * diagonal) - float(height * height)
        if residual <= 0.0:
            continue
        width = math.sqrt(float(residual))
        if float(width) < 2.0:
            continue
        answer = 2.0 * (float(height) + float(width))
        if not _answer_in_bounds(answer, answer_min=int(answer_min), answer_max=int(answer_max)):
            continue
        point_units = {
            "A": (0.0, 0.0),
            "B": (float(width), 0.0),
            "C": (float(width), float(height)),
            "D": (0.0, float(height)),
        }
        blueprint = Analytical2DSceneBlueprint(
            point_units=point_units,
            fit_points=tuple(point_units.values()),
            polygon_entities=(Analytical2DPolygonEntitySpec("rectangle_1", "rectangle", ("A", "B", "C", "D")),),
            circle_entities=(),
            segment_entities=(Analytical2DSegmentEntitySpec("diagonal_1", "diagonal", "A", "C", True),),
            annotation_specs=(
                Analytical2DAnnotationSpec("known_side", "B", "C", offset_scale=0.95),
                Analytical2DAnnotationSpec("diagonal", "A", "C", offset_scale=1.1),
            ),
            label_point_ids=("A", "B", "C", "D"),
            label_directions={},
            evidence_roles=("known_side", "diagonal"),
            role_values={"known_side": int(height), "diagonal": int(diagonal)},
        )
        return blueprint, float(answer), "2 * (known_side + sqrt(diagonal^2 - known_side^2))"
    raise ValueError("failed to sample rectangle_side_diagonal")


def _sample_rhombus_diagonals(
    rng,
    *,
    answer_min: int,
    answer_max: int,
    dimension_min: int,
    dimension_max: int,
) -> Tuple[Analytical2DSceneBlueprint, float, str]:
    """Rhombus with both diagonals annotated; infer perimeter."""
    for _ in range(500):
        diag_x = int(rng.randint(max(4, int(dimension_min)), int(dimension_max) * 2))
        diag_y = int(rng.randint(max(4, int(dimension_min)), int(dimension_max) * 2))
        side = math.hypot(float(diag_x) / 2.0, float(diag_y) / 2.0)
        answer = 4.0 * float(side)
        if not _answer_in_bounds(answer, answer_min=int(answer_min), answer_max=int(answer_max)):
            continue
        point_units = {
            "A": (-float(diag_x) / 2.0, 0.0),
            "B": (0.0, float(diag_y) / 2.0),
            "C": (float(diag_x) / 2.0, 0.0),
            "D": (0.0, -float(diag_y) / 2.0),
        }
        blueprint = Analytical2DSceneBlueprint(
            point_units=point_units,
            fit_points=tuple(point_units.values()),
            polygon_entities=(Analytical2DPolygonEntitySpec("rhombus_1", "rhombus", ("A", "B", "C", "D")),),
            circle_entities=(),
            segment_entities=(
                Analytical2DSegmentEntitySpec("diag_x_1", "diagonal", "A", "C", True),
                Analytical2DSegmentEntitySpec("diag_y_1", "diagonal", "B", "D", True),
            ),
            annotation_specs=(
                Analytical2DAnnotationSpec("diag_x", "A", "C", anchor_fraction=0.35, offset_scale=1.6, direction_override=(0.0, -1.0)),
                Analytical2DAnnotationSpec("diag_y", "B", "D", anchor_fraction=0.35, offset_scale=1.6, direction_override=(1.0, 0.0)),
            ),
            label_point_ids=("A", "B", "C", "D"),
            label_directions={},
            evidence_roles=("diag_x", "diag_y"),
            role_values={"diag_x": int(diag_x), "diag_y": int(diag_y)},
        )
        return blueprint, float(answer), "4 * sqrt((diag_x/2)^2 + (diag_y/2)^2)"
    raise ValueError("failed to sample rhombus_diagonals")


def _sample_isosceles_trapezoid_bases_height(
    rng,
    *,
    answer_min: int,
    answer_max: int,
    dimension_min: int,
    dimension_max: int,
) -> Tuple[Analytical2DSceneBlueprint, float, str]:
    """Isosceles trapezoid with both bases and one height annotated; infer perimeter."""
    for _ in range(500):
        base_top = int(rng.randint(max(3, int(dimension_min)), int(dimension_max)))
        half_diff = int(rng.randint(1, max(2, int(dimension_max // 2))))
        base_bottom = int(base_top + (2 * half_diff))
        height = int(rng.randint(max(2, int(dimension_min // 2)), int(dimension_max)))
        leg = math.hypot(float(height), float(half_diff))
        answer = float(base_bottom + base_top) + (2.0 * float(leg))
        if not _answer_in_bounds(answer, answer_min=int(answer_min), answer_max=int(answer_max)):
            continue
        point_units = {
            "A": (-float(base_bottom) / 2.0, 0.0),
            "B": (float(base_bottom) / 2.0, 0.0),
            "C": (float(base_top) / 2.0, float(height)),
            "D": (-float(base_top) / 2.0, float(height)),
            "E": (-float(base_top) / 2.0, 0.0),
        }
        blueprint = Analytical2DSceneBlueprint(
            point_units=point_units,
            fit_points=tuple(point_units.values()),
            polygon_entities=(Analytical2DPolygonEntitySpec("trapezoid_1", "isosceles_trapezoid", ("A", "B", "C", "D")),),
            circle_entities=(),
            segment_entities=(Analytical2DSegmentEntitySpec("height_1", "altitude", "D", "E", True),),
            annotation_specs=(
                Analytical2DAnnotationSpec("base_bottom", "A", "B", offset_scale=0.95),
                Analytical2DAnnotationSpec("base_top", "D", "C", offset_scale=1.15, direction_override=(0.0, -1.0)),
                Analytical2DAnnotationSpec("height", "D", "E", offset_scale=1.2, direction_override=(-1.0, 0.0)),
            ),
            label_point_ids=("A", "B", "C", "D", "E"),
            label_directions={"E": (-1.0, -1.0)},
            evidence_roles=("base_bottom", "base_top", "height"),
            role_values={"base_bottom": int(base_bottom), "base_top": int(base_top), "height": int(height)},
        )
        return blueprint, float(answer), "base_bottom + base_top + 2 * sqrt(height^2 + ((base_bottom - base_top)/2)^2)"
    raise ValueError("failed to sample isosceles_trapezoid_bases_height")


def _sample_inscribed_square_diameter(
    rng,
    *,
    answer_min: int,
    answer_max: int,
    radius_min: int,
    radius_max: int,
) -> Tuple[Analytical2DSceneBlueprint, float, str]:
    """Square inscribed in a circle; infer perimeter from one diameter."""
    for _ in range(320):
        radius = int(rng.randint(int(radius_min), int(radius_max)))
        answer = 4.0 * float(radius) * math.sqrt(2.0)
        if not _answer_in_bounds(answer, answer_min=int(answer_min), answer_max=int(answer_max)):
            continue
        point_units = {
            "A": (0.0, float(radius)),
            "B": (float(radius), 0.0),
            "C": (0.0, -float(radius)),
            "D": (-float(radius), 0.0),
            "O": (0.0, 0.0),
        }
        fit_points = (
            (-float(radius), -float(radius)),
            (-float(radius), float(radius)),
            (float(radius), -float(radius)),
            (float(radius), float(radius)),
        )
        blueprint = Analytical2DSceneBlueprint(
            point_units=point_units,
            fit_points=fit_points,
            polygon_entities=(Analytical2DPolygonEntitySpec("square_1", "square", ("A", "B", "C", "D")),),
            circle_entities=(Analytical2DCircleEntitySpec("circle_1", "O", float(radius)),),
            segment_entities=(Analytical2DSegmentEntitySpec("diameter_1", "diameter", "D", "B", True),),
            annotation_specs=(Analytical2DAnnotationSpec("diameter", "D", "B", offset_scale=1.05, direction_override=(0.0, -1.0)),),
            label_point_ids=("A", "B", "C", "D"),
            label_directions={},
            evidence_roles=("diameter",),
            role_values={"diameter": int(2 * radius)},
        )
        return blueprint, float(answer), "2 * sqrt(2) * diameter"
    raise ValueError("failed to sample inscribed_square_diameter")


def sample_analytical_2d_perimeter_case(
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
) -> _PerimeterCase:
    """Sample and render one analytical 2D perimeter case."""
    dimension_min, dimension_max = _dimension_bounds(params, generation_defaults)
    radius_min, radius_max = _circle_radius_bounds(params, generation_defaults)
    samplers = {
        "right_triangle_leg_hypotenuse": lambda: _sample_right_triangle_leg_hypotenuse(
            rng,
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            dimension_min=int(dimension_min),
            dimension_max=int(dimension_max),
        ),
        "rectangle_side_diagonal": lambda: _sample_rectangle_side_diagonal(
            rng,
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            dimension_min=int(dimension_min),
            dimension_max=int(dimension_max),
        ),
        "rhombus_diagonals": lambda: _sample_rhombus_diagonals(
            rng,
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            dimension_min=int(dimension_min),
            dimension_max=int(dimension_max),
        ),
        "isosceles_trapezoid_bases_height": lambda: _sample_isosceles_trapezoid_bases_height(
            rng,
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            dimension_min=int(dimension_min),
            dimension_max=int(dimension_max),
        ),
        "inscribed_square_diameter": lambda: _sample_inscribed_square_diameter(
            rng,
            answer_min=int(answer_min),
            answer_max=int(answer_max),
            radius_min=int(radius_min),
            radius_max=int(radius_max),
        ),
    }
    if str(task_variant) not in samplers:
        raise ValueError(f"unsupported analytical 2D perimeter task_variant: {task_variant}")
    blueprint, raw_answer_value, formula_expression = samplers[str(task_variant)]()
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
    )
    rounded_answer = _rounded_tenth(float(raw_answer_value))
    return _PerimeterCase(
        task_variant=str(task_variant),
        answer_value=float(rounded_answer),
        raw_answer_value=float(raw_answer_value),
        answer_scalar=int(round(float(rounded_answer) * 10.0)),
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
class GeometryAnalyticalPerimeter2DTask:
    """Compute derived perimeter values from annotated analytical 2D scenes."""

    task_id = "task_geometry_analytical_2d_perimeter"
    domain = "geometry"
    task_group = "analytical_2d"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic analytical 2D perimeter instance."""
        task_group_defaults = get_task_group_defaults(self.domain, self.task_group)
        gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            task_group_defaults if isinstance(task_group_defaults, Mapping) else {},
            task_id=str(self.task_id),
        )
        answer_min, answer_max = resolve_answer_bounds(
            params,
            gen_defaults=gen_defaults,
            task_id=str(self.task_id),
            fallback_min=8,
            fallback_max=250,
        )
        scene_rng = spawn_rng(int(instance_seed), "scene")
        task_variant, variant_probabilities = resolve_task_variant(
            scene_rng,
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
            supported_variants=PERIMETER_VARIANTS,
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
                case = sample_analytical_2d_perimeter_case(
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
            raise RuntimeError("failed to generate task_geometry_analytical_2d_perimeter instance") from last_error

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
        answer_hint = required_prompt_text(
            prompt_defaults,
            preferred_keys=("answer_hint_number", "answer_hint"),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = build_prompt_json_examples(
            evidence_value=case.evidence_map,
            answer_type="number",
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

        answer_gt = TypedValue(type="number", value=float(case.answer_value))
        evidence_gt = TypedValue(type="measurement_ref_map", value=dict(case.evidence_map))
        complexity = build_geometry_analytical_complexity(
            task_group_defaults=task_group_defaults if isinstance(task_group_defaults, Mapping) else {},
            task_id=str(self.task_id),
            task_kind="perimeter",
            task_variant=str(case.task_variant),
            annotation_count=len(case.evidence_roles),
            answer_format="number",
        )
        projected_point_set = [
            [float(case.annotation_centers[label][0]), float(case.annotation_centers[label][1])]
            for label in required_annotations
            if label in case.annotation_centers
        ]
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_2d_analytical_perimeter",
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
                "answer_type": "number",
                "raw_answer_value": float(case.raw_answer_value),
                "answer_scalar": int(case.answer_scalar),
                "answer_value": float(case.answer_value),
                "target_quantity": "perimeter",
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
