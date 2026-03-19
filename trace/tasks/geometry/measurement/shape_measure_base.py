"""Shared base implementation for single-object geometry shape-measurement tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...shared.config_defaults import (
    group_default,
    required_group_default,
    required_group_defaults,
    resolve_optional_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import resolve_scene_label_font_size_px
from ..shared.conic_geometry import (
    CircleInstance,
    EllipseInstance,
    circle_radii_for_pi_coefficient,
    circle_scene_entity,
    conic_render_anchor,
    draw_circle_outline,
    draw_ellipse_outline,
    ellipse_axis_pairs,
    ellipse_scene_entity,
    feasible_circle_radii_on_graph_paper,
    feasible_ellipse_axis_pairs_on_graph_paper,
    sample_circle_instance_on_graph_paper,
    sample_ellipse_instance_on_graph_paper,
)
from ..shared.graph_rendering import graph_paper_grid_from_frame, scale_point
from ..shared.labeled_point_evidence import labeled_grid_point_evidence_artifacts
from ..shared.point_labels import draw_labeled_points
from ..shared.polygon_geometry import (
    PolygonInstance,
    alphabetic_labels,
    draw_polygon_labels,
    draw_polygon_outline,
    polygon_render_anchor,
    polygon_scene_entity,
    sample_polygon_instance_on_graph_paper,
)
from ..shared.prompt_text import append_required_labels_clause
from ..shared.render_variation import sample_int_render_param
from ..shared.shape_style import extract_background_anchor_colors, sample_geometry_shape_style
from ..shared.single_object_scene import (
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)
from ..shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from .defaults import MEASUREMENT_SHARED_DEFAULTS
from ..shared.background_defaults import POST_IMAGE_BACKGROUND_DEFAULTS
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS

_POLYGON_VARIANT_TO_SIDES: Dict[str, int] = {
    "triangle": 3,
    "quadrilateral": 4,
    "pentagon": 5,
}
_POLYGON_VARIANTS = set(_POLYGON_VARIANT_TO_SIDES)


def _pi_expression(value: int) -> str:
    """Format one integer coefficient as canonical `kπ` text."""
    coefficient = int(value)
    if int(coefficient) == 1:
        return "π"
    return f"{int(coefficient)}π"


def _prompt_family_for_variant(variant_kind: str) -> str:
    """Return prompt-family suffix for one shape variant."""
    if str(variant_kind) in _POLYGON_VARIANTS:
        return "polygon"
    if str(variant_kind) == "ellipse":
        return "ellipse"
    if str(variant_kind) == "circle":
        return "circle"
    return str(variant_kind)


def _required_prompt_text(prompt_defaults: Mapping[str, Any], *, preferred_keys: Sequence[str], context: str) -> str:
    """Return first available non-empty prompt text among ordered key candidates."""
    for key in preferred_keys:
        if str(key) in prompt_defaults:
            return str(required_group_default(prompt_defaults, str(key), context=context))
    raise ValueError(f"missing required prompt key in {context}: one of {list(preferred_keys)}")


def _optional_prompt_text(prompt_defaults: Mapping[str, Any], *, preferred_keys: Sequence[str]) -> str | None:
    """Return first available non-empty optional prompt text among ordered key candidates."""
    for key in preferred_keys:
        value = prompt_defaults.get(str(key))
        if value is None:
            continue
        if isinstance(value, str) and not str(value).strip():
            continue
        return str(value)
    return None


class GeometryShapeMeasureBase:
    """Reusable base for geometry area/perimeter tasks over multiple shape variants."""

    task_id = ""
    domain = "geometry"
    task_group = "measurement"
    scene_kind = ""
    query_template_id = ""
    answer_component_key = ""
    supported_shape_variants: Tuple[str, ...] = ()

    def _answer_scalar_from_polygon_instance(self, instance: PolygonInstance) -> int:
        """Return scalar answer value for one polygon instance."""
        raise NotImplementedError

    def _answer_scalar_from_ellipse_instance(self, instance: EllipseInstance) -> int:
        """Return scalar answer value for one ellipse instance."""
        raise NotImplementedError

    def _answer_scalar_from_circle_instance(self, instance: CircleInstance) -> int:
        """Return scalar answer value for one circle instance."""
        raise NotImplementedError

    def _complexity_score(
        self,
        *,
        variant_kind: str,
        answer_scalar: int,
        polygon_sides: int | None,
    ) -> float:
        """Return task-specific complexity score."""
        raise NotImplementedError

    def _pi_variants(self) -> set[str]:
        """Return shape variants that emit π-expression answers."""
        return set()

    def _circle_answer_coefficient_scale(self) -> int:
        """Return coefficient scale for circle `kπ` answers."""
        return 2

    def _resolve_required_graph_cells(
        self,
        *,
        variant_kind: str,
        answer_min: int | None,
        answer_max: int | None,
        gen_defaults: Mapping[str, Any],
    ) -> int:
        """Return minimum graph-cell count required by one selected variant."""
        variant = str(variant_kind)
        if variant == "ellipse":
            axis_min = int(group_default(gen_defaults, "ellipse_axis_min", MEASUREMENT_SHARED_DEFAULTS.ellipse_axis_min))
            axis_max = int(group_default(gen_defaults, "ellipse_axis_max", MEASUREMENT_SHARED_DEFAULTS.ellipse_axis_max))
            allow_circle = bool(
                group_default(gen_defaults, "ellipse_allow_circle", MEASUREMENT_SHARED_DEFAULTS.ellipse_allow_circle)
            )
            pairs = ellipse_axis_pairs(
                axis_min=int(axis_min),
                axis_max=int(axis_max),
                coefficient_min=(int(answer_min) if answer_min is not None else None),
                coefficient_max=(int(answer_max) if answer_max is not None else None),
                allow_circle=bool(allow_circle),
            )
            if not pairs:
                raise ValueError("no feasible ellipse semiaxis pairs for requested answer bounds")
            min_extent = min(max(int(semi_x), int(semi_y)) for semi_x, semi_y in pairs)
            return int((2 * int(min_extent)) + 2)
        if variant == "circle":
            radius_min = int(group_default(gen_defaults, "circle_radius_min", MEASUREMENT_SHARED_DEFAULTS.circle_radius_min))
            radius_max = int(group_default(gen_defaults, "circle_radius_max", MEASUREMENT_SHARED_DEFAULTS.circle_radius_max))
            radii = circle_radii_for_pi_coefficient(
                radius_min=int(radius_min),
                radius_max=int(radius_max),
                coefficient_min=(int(answer_min) if answer_min is not None else None),
                coefficient_max=(int(answer_max) if answer_max is not None else None),
                coefficient_scale=int(self._circle_answer_coefficient_scale()),
            )
            if not radii:
                raise ValueError("no feasible circle radii for requested answer bounds")
            min_radius = min(int(radius) for radius in radii)
            return int((2 * int(min_radius)) + 2)
        return 0

    def _resolve_polygon_target_answer(
        self,
        *,
        instance_seed: int,
        params: Mapping[str, Any],
        variant_kind: str,
        answer_min: int | None,
        answer_max: int | None,
        gen_defaults: Mapping[str, Any],
        render_defaults: Mapping[str, Any],
    ) -> Tuple[int | None, Dict[str, float], List[int], int]:
        """Return optional target answer support for polygon variants.

        Default behavior does not preselect a polygon target answer.
        """

        return None, {}, [], 0

    def _resolve_circle_target_answer(
        self,
        *,
        instance_seed: int,
        params: Mapping[str, Any],
        variant_kind: str,
        answer_min: int | None,
        answer_max: int | None,
        gen_defaults: Mapping[str, Any],
        render_defaults: Mapping[str, Any],
    ) -> Tuple[int | None, Dict[str, float], List[int], int]:
        """Return optional target answer support for circle variants.

        Default behavior does not preselect a circle target answer.
        """

        return None, {}, [], 0

    def _sample_polygon_instance(
        self,
        rng,
        *,
        variant_kind: str,
        target_answer_scalar: int | None,
        context,
        gen_defaults: Mapping[str, Any],
    ) -> PolygonInstance:
        """Sample one polygon instance for the active polygon variant."""

        polygon_sides = int(_POLYGON_VARIANT_TO_SIDES[str(variant_kind)])
        return sample_polygon_instance_on_graph_paper(
            rng,
            allowed_sides=[int(polygon_sides)],
            canvas_size=int(context.canvas_size),
            graph_spacing=int(context.graph_spacing),
            graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
            padding_units=0,
            max_attempts=8,
            min_area_square_units=4,
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic shape-measurement instance."""
        task_group_defaults = get_task_group_defaults(self.domain, self.task_group)
        gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            task_group_defaults if isinstance(task_group_defaults, Mapping) else {},
            task_id=str(self.task_id),
        )

        scene_rng = spawn_rng(instance_seed, "scene")
        supported_variants = [str(item) for item in self.supported_shape_variants]
        if not supported_variants:
            raise ValueError(f"{self.task_id} must define non-empty supported_shape_variants")
        selected_variant, variant_probabilities = resolve_variant(
            scene_rng,
            params=params,
            gen_defaults=gen_defaults,
            supported_variants=supported_variants,
        )
        variant_kind = apply_balanced_variant_sampling(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
            selected_variant=str(selected_variant),
            variant_probabilities=variant_probabilities,
            supported_variants=supported_variants,
        )

        answer_min, answer_max = resolve_optional_int_bounds(
            params,
            gen_defaults,
            min_key="answer_min",
            max_key="answer_max",
            context=f"generation defaults for {self.task_id}",
        )
        selected_polygon_target_answer = None
        polygon_answer_probabilities: Dict[str, float] = {}
        polygon_feasible_answer_values: List[int] = []
        polygon_required_graph_cells = 0
        selected_circle_target_answer = None
        circle_answer_probabilities: Dict[str, float] = {}
        circle_feasible_answer_values: List[int] = []
        circle_required_graph_cells = 0
        if str(variant_kind) in _POLYGON_VARIANTS:
            (
                selected_polygon_target_answer,
                polygon_answer_probabilities,
                polygon_feasible_answer_values,
                polygon_required_graph_cells,
            ) = self._resolve_polygon_target_answer(
                instance_seed=int(instance_seed),
                params=params,
                variant_kind=str(variant_kind),
                answer_min=answer_min,
                answer_max=answer_max,
                gen_defaults=gen_defaults,
                render_defaults=render_defaults,
            )
        if str(variant_kind) == "circle":
            (
                selected_circle_target_answer,
                circle_answer_probabilities,
                circle_feasible_answer_values,
                circle_required_graph_cells,
            ) = self._resolve_circle_target_answer(
                instance_seed=int(instance_seed),
                params=params,
                variant_kind=str(variant_kind),
                answer_min=answer_min,
                answer_max=answer_max,
                gen_defaults=gen_defaults,
                render_defaults=render_defaults,
            )
        required_graph_cells = self._resolve_required_graph_cells(
            variant_kind=str(variant_kind),
            answer_min=answer_min,
            answer_max=answer_max,
            gen_defaults=gen_defaults,
        )
        if int(polygon_required_graph_cells) > 0:
            required_graph_cells = max(int(required_graph_cells), int(polygon_required_graph_cells))
        if int(circle_required_graph_cells) > 0:
            required_graph_cells = max(int(required_graph_cells), int(circle_required_graph_cells))
        context_params = dict(params)
        if int(required_graph_cells) > 0:
            if "graph_cells" in context_params:
                if int(context_params.get("graph_cells", 0)) < int(required_graph_cells):
                    raise ValueError("graph_cells is too small for selected shape variant and answer bounds")
            else:
                current_min_cells = int(
                    context_params.get(
                        "graph_cells_min",
                        group_default(render_defaults, "graph_cells_min", MEASUREMENT_SHARED_DEFAULTS.graph_cells_min),
                    )
                )
                current_max_cells = int(
                    context_params.get(
                        "graph_cells_max",
                        group_default(render_defaults, "graph_cells_max", MEASUREMENT_SHARED_DEFAULTS.graph_cells_max),
                    )
                )
                resolved_min_cells = max(int(current_min_cells), int(required_graph_cells))
                resolved_max_cells = max(int(current_max_cells), int(resolved_min_cells))
                context_params["graph_cells_min"] = int(resolved_min_cells)
                context_params["graph_cells_max"] = int(resolved_max_cells)

        context = resolve_graph_scene_context(
            scene_rng,
            params=context_params,
            render_defaults=render_defaults,
            background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
            fallback_canvas_min=MEASUREMENT_SHARED_DEFAULTS.canvas_size_min,
            fallback_canvas_max=MEASUREMENT_SHARED_DEFAULTS.canvas_size_max,
            fallback_cells_min=MEASUREMENT_SHARED_DEFAULTS.graph_cells_min,
            fallback_cells_max=MEASUREMENT_SHARED_DEFAULTS.graph_cells_max,
        )
        line_width = sample_int_render_param(
            scene_rng,
            params=context_params,
            render_defaults=render_defaults,
            key="line_width",
            fallback=int(MEASUREMENT_SHARED_DEFAULTS.line_width),
            min_key="line_width_min",
            max_key="line_width_max",
            minimum_value=1,
        )
        label_offset_px = float(
            context_params.get(
                "label_offset_px",
                group_default(render_defaults, "label_offset_px", MEASUREMENT_SHARED_DEFAULTS.label_offset_px),
            )
        )
        label_font_size_px = resolve_scene_label_font_size_px(
            canvas_size=int(context.canvas_size),
            graph_spacing=int(context.graph_spacing),
            scene_scale=int(context.scene_scale),
            min_px=int(group_default(render_defaults, "label_font_size_min", MEASUREMENT_SHARED_DEFAULTS.label_font_size_min)),
            max_px=int(group_default(render_defaults, "label_font_size_max", MEASUREMENT_SHARED_DEFAULTS.label_font_size_max)),
        )
        label_stroke_width = sample_int_render_param(
            scene_rng,
            params=context_params,
            render_defaults=render_defaults,
            key="label_stroke_width",
            fallback=int(MEASUREMENT_SHARED_DEFAULTS.label_stroke_width),
            min_key="label_stroke_width_min",
            max_key="label_stroke_width_max",
            minimum_value=1,
        )
        image, draw, background_meta = make_graph_scene_canvas(
            instance_seed=int(instance_seed),
            context=context,
            background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        shape_style = sample_geometry_shape_style(
            scene_rng,
            params=context_params,
            render_defaults=render_defaults,
            anchor_colors=extract_background_anchor_colors(background_meta),
        )

        ellipse_pairs_for_context: List[Tuple[int, int]] | None = None
        circle_radii_for_context: List[int] | None = None
        if str(variant_kind) == "ellipse":
            ellipse_pairs = ellipse_axis_pairs(
                axis_min=int(group_default(gen_defaults, "ellipse_axis_min", MEASUREMENT_SHARED_DEFAULTS.ellipse_axis_min)),
                axis_max=int(group_default(gen_defaults, "ellipse_axis_max", MEASUREMENT_SHARED_DEFAULTS.ellipse_axis_max)),
                coefficient_min=(int(answer_min) if answer_min is not None else None),
                coefficient_max=(int(answer_max) if answer_max is not None else None),
                allow_circle=bool(
                    group_default(gen_defaults, "ellipse_allow_circle", MEASUREMENT_SHARED_DEFAULTS.ellipse_allow_circle)
                ),
            )
            ellipse_pairs_for_context = feasible_ellipse_axis_pairs_on_graph_paper(
                canvas_size=int(context.canvas_size),
                graph_spacing=int(context.graph_spacing),
                graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
                axis_pairs=ellipse_pairs,
                padding_units=0,
            )
            if not ellipse_pairs_for_context:
                raise RuntimeError(
                    "no feasible ellipse semiaxis pairs for current graph-paper context and answer bounds"
                )
        if str(variant_kind) == "circle":
            circle_radii = circle_radii_for_pi_coefficient(
                radius_min=int(group_default(gen_defaults, "circle_radius_min", MEASUREMENT_SHARED_DEFAULTS.circle_radius_min)),
                radius_max=int(group_default(gen_defaults, "circle_radius_max", MEASUREMENT_SHARED_DEFAULTS.circle_radius_max)),
                coefficient_min=(
                    int(selected_circle_target_answer)
                    if selected_circle_target_answer is not None
                    else (int(answer_min) if answer_min is not None else None)
                ),
                coefficient_max=(
                    int(selected_circle_target_answer)
                    if selected_circle_target_answer is not None
                    else (int(answer_max) if answer_max is not None else None)
                ),
                coefficient_scale=int(self._circle_answer_coefficient_scale()),
            )
            circle_radii_for_context = feasible_circle_radii_on_graph_paper(
                canvas_size=int(context.canvas_size),
                graph_spacing=int(context.graph_spacing),
                graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
                radii=circle_radii,
                padding_units=0,
            )
            if not circle_radii_for_context:
                raise RuntimeError("no feasible circle radii for current graph-paper context and answer bounds")

        answer_scalar = None
        polygon_instance: PolygonInstance | None = None
        ellipse_instance: EllipseInstance | None = None
        circle_instance: CircleInstance | None = None
        evidence: Dict[str, Any] | None = None
        entity: Dict[str, Any] | None = None
        anchor: Dict[str, Any] | None = None
        range_rejections = 0
        last_error: Exception | None = None
        attempt_budget = max(1, int(max_attempts))
        if str(variant_kind) in _POLYGON_VARIANTS and (answer_min is not None or answer_max is not None):
            attempt_budget = int(attempt_budget) * 3
        for _ in range(max(1, int(attempt_budget))):
            try:
                if str(variant_kind) in _POLYGON_VARIANTS:
                    candidate_polygon = self._sample_polygon_instance(
                        scene_rng,
                        variant_kind=str(variant_kind),
                        target_answer_scalar=(
                            None if selected_polygon_target_answer is None else int(selected_polygon_target_answer)
                        ),
                        context=context,
                        gen_defaults=gen_defaults,
                    )
                    candidate_answer = int(self._answer_scalar_from_polygon_instance(candidate_polygon))
                    if (
                        selected_polygon_target_answer is not None
                        and int(candidate_answer) != int(selected_polygon_target_answer)
                    ):
                        range_rejections += 1
                        continue
                    if answer_min is not None and int(candidate_answer) < int(answer_min):
                        range_rejections += 1
                        continue
                    if answer_max is not None and int(candidate_answer) > int(answer_max):
                        range_rejections += 1
                        continue
                    draw_polygon_outline(
                        draw,
                        vertices=[scale_point(point, int(context.scene_scale)) for point in candidate_polygon.vertices],
                        line_width=max(1, int(line_width) * int(context.scene_scale)),
                        line_color=tuple(int(value) for value in shape_style.line_color),
                    )
                    draw_polygon_labels(
                        draw,
                        vertices=[scale_point(point, int(context.scene_scale)) for point in candidate_polygon.vertices],
                        labels=list(candidate_polygon.labels),
                        label_offset_px=float(label_offset_px) * float(context.scene_scale),
                        font_size_px=int(label_font_size_px),
                        text_stroke_width=max(1, int(label_stroke_width)),
                        label_color=tuple(int(value) for value in shape_style.label_color),
                        label_stroke_color=tuple(int(value) for value in shape_style.label_stroke_color),
                        canvas_size=int(context.canvas_size) * int(context.scene_scale),
                    )
                    polygon_instance = candidate_polygon
                    answer_scalar = int(candidate_answer)
                    evidence_points = {
                        str(label): point
                        for label, point in zip(candidate_polygon.labels, candidate_polygon.vertices)
                    }
                    evidence = labeled_grid_point_evidence_artifacts(
                        points_by_label=evidence_points,
                        graph_origin=context.graph_origin,
                        graph_spacing=int(context.graph_spacing),
                        witness_type="polygon_vertex_map",
                        ordered_labels=[str(label) for label in candidate_polygon.labels],
                    )
                    entity = polygon_scene_entity(candidate_polygon)
                    anchor = polygon_render_anchor(candidate_polygon)
                    break

                if str(variant_kind) == "ellipse":
                    candidate_ellipse = sample_ellipse_instance_on_graph_paper(
                        scene_rng,
                        canvas_size=int(context.canvas_size),
                        graph_spacing=int(context.graph_spacing),
                        graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
                        axis_pairs=(ellipse_pairs_for_context if ellipse_pairs_for_context is not None else []),
                        padding_units=0,
                        max_attempts=8,
                    )
                    candidate_answer = int(self._answer_scalar_from_ellipse_instance(candidate_ellipse))
                    if answer_min is not None and int(candidate_answer) < int(answer_min):
                        range_rejections += 1
                        continue
                    if answer_max is not None and int(candidate_answer) > int(answer_max):
                        range_rejections += 1
                        continue
                    draw_ellipse_outline(
                        draw,
                        center=scale_point(candidate_ellipse.center, int(context.scene_scale)),
                        semi_axis_x_px=int(candidate_ellipse.semi_axis_x_units) * int(context.graph_spacing) * int(context.scene_scale),
                        semi_axis_y_px=int(candidate_ellipse.semi_axis_y_units) * int(context.graph_spacing) * int(context.scene_scale),
                        line_width=max(1, int(line_width) * int(context.scene_scale)),
                        line_color=tuple(int(value) for value in shape_style.line_color),
                    )
                    center = (float(candidate_ellipse.center[0]), float(candidate_ellipse.center[1]))
                    axis_x_endpoint = (
                        float(center[0] + (int(candidate_ellipse.semi_axis_x_units) * int(context.graph_spacing))),
                        float(center[1]),
                    )
                    axis_y_endpoint = (
                        float(center[0]),
                        float(center[1] - (int(candidate_ellipse.semi_axis_y_units) * int(context.graph_spacing))),
                    )
                    evidence_labels = list(alphabetic_labels(3, start_index=int(scene_rng.randrange(26))))
                    evidence_points = {
                        str(evidence_labels[0]): center,
                        str(evidence_labels[1]): axis_x_endpoint,
                        str(evidence_labels[2]): axis_y_endpoint,
                    }
                    draw_labeled_points(
                        draw,
                        points=[
                            scale_point(center, int(context.scene_scale)),
                            scale_point(axis_x_endpoint, int(context.scene_scale)),
                            scale_point(axis_y_endpoint, int(context.scene_scale)),
                        ],
                        labels=evidence_labels,
                        label_offset_px=float(label_offset_px) * float(context.scene_scale),
                        font_size_px=int(label_font_size_px),
                        text_stroke_width=max(1, int(label_stroke_width)),
                        marker_radius_px=max(1, int(context.scene_scale)),
                        marker_color=tuple(int(value) for value in shape_style.line_color),
                        label_color=tuple(int(value) for value in shape_style.label_color),
                        label_stroke_color=tuple(int(value) for value in shape_style.label_stroke_color),
                        canvas_size=int(context.canvas_size) * int(context.scene_scale),
                    )
                    ellipse_instance = candidate_ellipse
                    answer_scalar = int(candidate_answer)
                    evidence = labeled_grid_point_evidence_artifacts(
                        points_by_label=evidence_points,
                        graph_origin=context.graph_origin,
                        graph_spacing=int(context.graph_spacing),
                        witness_type="ellipse_reference_points",
                        ordered_labels=evidence_labels,
                    )
                    entity = ellipse_scene_entity(candidate_ellipse)
                    entity["attrs"]["evidence_labels"] = {
                        "center": str(evidence_labels[0]),
                        "axis_x_endpoint": str(evidence_labels[1]),
                        "axis_y_endpoint": str(evidence_labels[2]),
                    }
                    anchor = conic_render_anchor(
                        center=candidate_ellipse.center,
                        semi_axis_x_px=int(candidate_ellipse.semi_axis_x_units) * int(context.graph_spacing),
                        semi_axis_y_px=int(candidate_ellipse.semi_axis_y_units) * int(context.graph_spacing),
                    )
                    break

                if str(variant_kind) == "circle":
                    candidate_circle = sample_circle_instance_on_graph_paper(
                        scene_rng,
                        canvas_size=int(context.canvas_size),
                        graph_spacing=int(context.graph_spacing),
                        graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
                        radii=(circle_radii_for_context if circle_radii_for_context is not None else []),
                        padding_units=0,
                        max_attempts=8,
                    )
                    candidate_answer = int(self._answer_scalar_from_circle_instance(candidate_circle))
                    if (
                        selected_circle_target_answer is not None
                        and int(candidate_answer) != int(selected_circle_target_answer)
                    ):
                        range_rejections += 1
                        continue
                    if answer_min is not None and int(candidate_answer) < int(answer_min):
                        range_rejections += 1
                        continue
                    if answer_max is not None and int(candidate_answer) > int(answer_max):
                        range_rejections += 1
                        continue
                    draw_circle_outline(
                        draw,
                        center=scale_point(candidate_circle.center, int(context.scene_scale)),
                        radius_px=int(candidate_circle.radius_units) * int(context.graph_spacing) * int(context.scene_scale),
                        line_width=max(1, int(line_width) * int(context.scene_scale)),
                        line_color=tuple(int(value) for value in shape_style.line_color),
                    )
                    center = (float(candidate_circle.center[0]), float(candidate_circle.center[1]))
                    radius_endpoint = (
                        float(center[0] + (int(candidate_circle.radius_units) * int(context.graph_spacing))),
                        float(center[1]),
                    )
                    evidence_labels = list(alphabetic_labels(2, start_index=int(scene_rng.randrange(26))))
                    evidence_points = {
                        str(evidence_labels[0]): center,
                        str(evidence_labels[1]): radius_endpoint,
                    }
                    draw_labeled_points(
                        draw,
                        points=[
                            scale_point(center, int(context.scene_scale)),
                            scale_point(radius_endpoint, int(context.scene_scale)),
                        ],
                        labels=evidence_labels,
                        label_offset_px=float(label_offset_px) * float(context.scene_scale),
                        font_size_px=int(label_font_size_px),
                        text_stroke_width=max(1, int(label_stroke_width)),
                        marker_radius_px=max(1, int(context.scene_scale)),
                        marker_color=tuple(int(value) for value in shape_style.line_color),
                        label_color=tuple(int(value) for value in shape_style.label_color),
                        label_stroke_color=tuple(int(value) for value in shape_style.label_stroke_color),
                        canvas_size=int(context.canvas_size) * int(context.scene_scale),
                    )
                    circle_instance = candidate_circle
                    answer_scalar = int(candidate_answer)
                    evidence = labeled_grid_point_evidence_artifacts(
                        points_by_label=evidence_points,
                        graph_origin=context.graph_origin,
                        graph_spacing=int(context.graph_spacing),
                        witness_type="circle_reference_points",
                        ordered_labels=evidence_labels,
                    )
                    entity = circle_scene_entity(candidate_circle)
                    entity["attrs"]["evidence_labels"] = {
                        "center": str(evidence_labels[0]),
                        "radius_endpoint": str(evidence_labels[1]),
                    }
                    anchor = conic_render_anchor(
                        center=candidate_circle.center,
                        semi_axis_x_px=int(candidate_circle.radius_units) * int(context.graph_spacing),
                        semi_axis_y_px=int(candidate_circle.radius_units) * int(context.graph_spacing),
                    )
                    break

                raise ValueError(f"unsupported variant_kind: {variant_kind}")
            except Exception as exc:
                last_error = exc
                continue

        if answer_scalar is None or evidence is None or entity is None or anchor is None:
            if range_rejections > 0 and last_error is None:
                raise RuntimeError(
                    f"failed to generate {self.task_id} instance in requested answer range "
                    f"[{answer_min}, {answer_max}]"
                )
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        image, background_meta_final, post_noise_meta = finalize_graph_scene_image(
            image,
            instance_seed=int(instance_seed),
            context=context,
            background_meta=background_meta,
            noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
        )

        base_prompt_required = required_group_defaults(
            prompt_defaults,
            (
                "bundle_id",
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_bundle_id = str(base_prompt_required["bundle_id"])
        prompt_task_family_key = str(base_prompt_required["task_family_key"])
        prompt_task_key = str(base_prompt_required["task_key"])
        json_output_contract = str(base_prompt_required["json_output_contract"])
        json_output_contract_answer_only = str(base_prompt_required["json_output_contract_answer_only"])

        prompt_family = _prompt_family_for_variant(str(variant_kind))
        answer_family = "pi" if str(variant_kind) in self._pi_variants() else "integer"
        required_labels = [str(label) for label in evidence.get("required_labels", []) if str(label).strip()]

        object_description = _required_prompt_text(
            prompt_defaults,
            preferred_keys=(f"object_description_{prompt_family}", "object_description"),
            context=f"prompt defaults for {self.task_id}",
        )
        question_text = _required_prompt_text(
            prompt_defaults,
            preferred_keys=(f"question_text_{prompt_family}", "question_text"),
            context=f"prompt defaults for {self.task_id}",
        )
        evidence_hint_base = _required_prompt_text(
            prompt_defaults,
            preferred_keys=(f"evidence_hint_{prompt_family}", "evidence_hint_point_map", "evidence_hint"),
            context=f"prompt defaults for {self.task_id}",
        )
        evidence_hint = append_required_labels_clause(str(evidence_hint_base), required_labels)
        answer_hint = _required_prompt_text(
            prompt_defaults,
            preferred_keys=(f"answer_hint_{answer_family}", "answer_hint"),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example = _optional_prompt_text(
            prompt_defaults,
            preferred_keys=(
                f"json_example_{variant_kind}",
                f"json_example_{prompt_family}",
                f"json_example_{answer_family}",
                "json_example",
            ),
        )
        json_example_answer_only = _optional_prompt_text(
            prompt_defaults,
            preferred_keys=(
                f"json_example_answer_only_{variant_kind}",
                f"json_example_answer_only_{answer_family}",
                "json_example_answer_only",
            ),
        )
        if json_example is None or json_example_answer_only is None:
            generated_json_example, generated_json_example_answer_only = build_prompt_json_examples(
                evidence_value=evidence.get("evidence_value", {}),
                answer_type=("pi_expression" if str(answer_family) == "pi" else "integer"),
            )
            if json_example is None:
                json_example = str(generated_json_example)
            if json_example_answer_only is None:
                json_example_answer_only = str(generated_json_example_answer_only)

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=prompt_bundle_id,
            task_family_key=prompt_task_family_key,
            task_key=prompt_task_key,
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "question_text": str(question_text),
                "json_output_contract": str(json_output_contract),
                "json_output_contract_answer_only": str(json_output_contract_answer_only),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(answer_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        if str(variant_kind) in self._pi_variants():
            answer_gt = TypedValue(type="pi_expression", value=_pi_expression(int(answer_scalar)))
            answer_format = "pi_expression"
        else:
            answer_gt = TypedValue(type="integer", value=int(answer_scalar))
            answer_format = "integer"

        execution_trace: Dict[str, Any] = {
            "shape_variant": str(variant_kind),
            "answer_scalar": int(answer_scalar),
            "answer_format": str(answer_format),
            "variant_probabilities": dict(variant_probabilities),
            "required_graph_cells": int(required_graph_cells),
            "required_evidence_labels": [str(label) for label in evidence.get("required_labels", [])],
        }
        polygon_sides = None
        if polygon_instance is not None:
            polygon_sides = int(polygon_instance.sides)
            execution_trace.update(
                {
                    "area_square_units": int(polygon_instance.area_square_units),
                    "perimeter_units": int(polygon_instance.perimeter_units),
                    "polygon_sides": int(polygon_instance.sides),
                    "template_id": str(polygon_instance.template_id),
                }
            )
            if polygon_feasible_answer_values:
                execution_trace.update(
                    {
                        "feasible_answer_values": [int(value) for value in polygon_feasible_answer_values],
                        "answer_scalar_probabilities": dict(polygon_answer_probabilities),
                    }
                )
        if ellipse_instance is not None:
            execution_trace.update(
                {
                    "ellipse_semi_axis_x_units": int(ellipse_instance.semi_axis_x_units),
                    "ellipse_semi_axis_y_units": int(ellipse_instance.semi_axis_y_units),
                    "ellipse_area_pi_coefficient": int(ellipse_instance.area_pi_coefficient),
                }
            )
        if circle_instance is not None:
            execution_trace.update(
                {
                    "circle_radius_units": int(circle_instance.radius_units),
                    "circle_area_pi_coefficient": int(circle_instance.area_pi_coefficient),
                    "circle_circumference_pi_coefficient": int(circle_instance.circumference_pi_coefficient),
                }
            )
            if circle_feasible_answer_values:
                execution_trace.update(
                    {
                        "feasible_answer_values": [int(value) for value in circle_feasible_answer_values],
                        "answer_scalar_probabilities": dict(circle_answer_probabilities),
                    }
                )

        trace_payload = {
            "scene_ir": {
                "scene_kind": str(self.scene_kind),
                "entities": [dict(entity)],
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
                "task_variant": str(variant_kind),
                "template_id": str(self.query_template_id),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "shape_variant": str(variant_kind),
                    "supported_shape_variants": [str(item) for item in supported_variants],
                    "variant_probabilities": dict(variant_probabilities),
                    "answer_min": (int(answer_min) if answer_min is not None else None),
                    "answer_max": (int(answer_max) if answer_max is not None else None),
                    "required_graph_cells": int(required_graph_cells),
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
            "render_map": {"image_id": "img0", "anchors": {"target_1": dict(anchor)}},
            "execution_trace": dict(execution_trace),
            "witness_symbolic": dict(evidence["witness_symbolic"]),
            "projected_evidence": dict(evidence["projected_evidence"]),
        }

        complexity = TaskComplexity(
            complexity_score=self._complexity_score(
                variant_kind=str(variant_kind),
                answer_scalar=int(answer_scalar),
                polygon_sides=(int(polygon_sides) if polygon_sides is not None else None),
            ),
            complexity_components={
                "shape_variant": str(variant_kind),
                str(self.answer_component_key): int(answer_scalar),
                "polygon_sides": (int(polygon_sides) if polygon_sides is not None else None),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=TypedValue(type=str(evidence["evidence_type"]), value=evidence["evidence_value"]),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(variant_kind),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
