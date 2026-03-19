"""Single-object analytical 3D surface-area task."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
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
from ..shared.analytical_3d_solids import (
    SURFACE_AREA_VARIANTS,
    sample_analytical_3d_surface_area_case,
)
from ..shared.analytical_3d_task import (
    required_prompt_text,
    resolve_answer_bounds,
    resolve_task_variant,
)
from ..shared.background_defaults import load_geometry_background_defaults
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
from .defaults import ANALYTICAL_3D_SHARED_DEFAULTS

ANALYTICAL_3D_POST_IMAGE_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="analytical_3d")
ANALYTICAL_3D_POST_IMAGE_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="analytical_3d")


@register_task
class GeometryAnalyticalSurfaceArea3DTask:
    """Compute total surface area from one annotated 3D solid."""

    task_id = "task_geometry_analytical_3d_surface_area"
    domain = "geometry"
    task_group = "analytical_3d"

    def _complexity(
        self,
        *,
        task_variant: str,
        answer_scalar: int,
        answer_max: int,
    ) -> TaskComplexity:
        """Compute complexity from variant family and answer magnitude."""
        variant_weight = {
            "rectangular_prism_given_lwh": 0.28,
            "triangular_prism_given_a_b_c_l": 0.48,
            "square_pyramid_given_base_side_slant_height": 0.54,
            "cylinder_given_r_h": 0.40,
            "cone_given_r_slant_height": 0.58,
            "sphere_given_r": 0.46,
        }.get(str(task_variant), 0.45)
        magnitude = 0.0
        if int(answer_max) > 0:
            magnitude = min(1.0, float(answer_scalar) / float(max(1, int(answer_max))))
        score = max(0.0, min(1.0, 0.30 + (0.54 * float(variant_weight)) + (0.16 * float(magnitude))))
        return TaskComplexity(
            complexity_score=float(score),
            complexity_components={
                "task_variant": str(task_variant),
                "answer_scalar": int(answer_scalar),
                "variant_component": float(variant_weight),
                "magnitude_component": float(magnitude),
            },
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic analytical 3D surface-area instance."""
        task_group_defaults = get_task_group_defaults(self.domain, self.task_group)
        gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            task_group_defaults if isinstance(task_group_defaults, Mapping) else {},
            task_id=str(self.task_id),
        )
        answer_min, answer_max = resolve_answer_bounds(
            params,
            gen_defaults=gen_defaults,
            task_id=str(self.task_id),
            fallback_min=int(ANALYTICAL_3D_SHARED_DEFAULTS.answer_min),
            fallback_max=int(ANALYTICAL_3D_SHARED_DEFAULTS.answer_max),
        )
        scene_rng = spawn_rng(int(instance_seed), "scene")
        task_variant, variant_probabilities = resolve_task_variant(
            scene_rng,
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
            supported_variants=SURFACE_AREA_VARIANTS,
        )
        context_params = dict(params)
        line_width = sample_int_render_param(
            scene_rng,
            params=context_params,
            render_defaults=render_defaults,
            key="line_width",
            fallback=int(ANALYTICAL_3D_SHARED_DEFAULTS.line_width),
            min_key="line_width_min",
            max_key="line_width_max",
            minimum_value=1,
        )
        helper_line_width = sample_int_render_param(
            scene_rng,
            params=context_params,
            render_defaults=render_defaults,
            key="helper_line_width",
            fallback=int(ANALYTICAL_3D_SHARED_DEFAULTS.helper_line_width),
            min_key="helper_line_width_min",
            max_key="helper_line_width_max",
            minimum_value=1,
        )
        label_stroke_width = sample_int_render_param(
            scene_rng,
            params=context_params,
            render_defaults=render_defaults,
            key="label_stroke_width",
            fallback=int(ANALYTICAL_3D_SHARED_DEFAULTS.label_stroke_width),
            min_key="label_stroke_width_min",
            max_key="label_stroke_width_max",
            minimum_value=1,
        )

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
                    background_defaults=ANALYTICAL_3D_POST_IMAGE_BACKGROUND_DEFAULTS,
                    fallback_canvas_min=ANALYTICAL_3D_SHARED_DEFAULTS.canvas_size_min,
                    fallback_canvas_max=ANALYTICAL_3D_SHARED_DEFAULTS.canvas_size_max,
                    fallback_cells_min=ANALYTICAL_3D_SHARED_DEFAULTS.graph_cells_min,
                    fallback_cells_max=ANALYTICAL_3D_SHARED_DEFAULTS.graph_cells_max,
                    require_graph_paper_background=False,
                )
                label_offset_px = float(
                    group_default(render_defaults, "label_offset_px", ANALYTICAL_3D_SHARED_DEFAULTS.label_offset_px)
                )
                label_font_size_px = resolve_scene_label_font_size_px(
                    canvas_size=int(context.canvas_size),
                    graph_spacing=int(context.graph_spacing),
                    scene_scale=int(context.scene_scale),
                    min_px=int(
                        group_default(
                            render_defaults,
                            "label_font_size_min",
                            ANALYTICAL_3D_SHARED_DEFAULTS.label_font_size_min,
                        )
                    ),
                    max_px=int(
                        group_default(
                            render_defaults,
                            "label_font_size_max",
                            ANALYTICAL_3D_SHARED_DEFAULTS.label_font_size_max,
                        )
                    ),
                )
                image, draw, background_meta = make_graph_scene_canvas(
                    instance_seed=int(instance_seed),
                    context=context,
                    background_defaults=ANALYTICAL_3D_POST_IMAGE_BACKGROUND_DEFAULTS,
                    require_graph_paper=False,
                )
                shape_style = sample_geometry_shape_style(
                    scene_rng,
                    params=context_params,
                    render_defaults=render_defaults,
                    anchor_colors=extract_background_anchor_colors(background_meta),
                )
                case = sample_analytical_3d_surface_area_case(
                    scene_rng,
                    draw,
                    task_variant=str(task_variant),
                    params=params,
                    generation_defaults=gen_defaults,
                    canvas_size=int(context.canvas_size),
                    scene_scale=int(context.scene_scale),
                    shape_style=shape_style,
                    line_width=int(line_width),
                    helper_line_width=int(helper_line_width),
                    label_offset_px=float(label_offset_px),
                    label_font_size_px=int(label_font_size_px),
                    label_stroke_width=int(label_stroke_width),
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
            raise RuntimeError("failed to generate task_geometry_analytical_3d_surface_area instance") from last_error

        image, background_meta_final, post_noise_meta = finalize_graph_scene_image(
            image,
            instance_seed=int(instance_seed),
            context=context,
            background_meta=background_meta,
            noise_defaults=ANALYTICAL_3D_POST_IMAGE_NOISE_DEFAULTS,
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
        answer_family = "pi" if str(case.answer_type) == "pi_expression" else "integer"
        question_text = required_prompt_text(
            prompt_defaults,
            preferred_keys=(f"question_text_{case.task_variant}", "question_text"),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_hint = required_prompt_text(
            prompt_defaults,
            preferred_keys=(f"answer_hint_{answer_family}", "answer_hint"),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = build_prompt_json_examples(
            evidence_value=case.evidence_map,
            answer_type=str(case.answer_type),
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

        if str(case.answer_type) == "pi_expression":
            answer_gt = TypedValue(type="pi_expression", value=str(case.answer_value))
        else:
            answer_gt = TypedValue(type="integer", value=int(case.answer_value))
        evidence_gt = TypedValue(type="measurement_ref_map", value=dict(case.evidence_map))
        complexity = self._complexity(
            task_variant=str(case.task_variant),
            answer_scalar=int(case.answer_scalar),
            answer_max=int(answer_max),
        )

        projected_point_set = [
            [float(case.annotation_centers[label][0]), float(case.annotation_centers[label][1])]
            for label in required_annotations
            if label in case.annotation_centers
        ]
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_3d_analytical_surface_area",
                "entities": [dict(case.entity)],
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
                "entity_id": str(case.entity["entity_id"]),
                "instance_anchor": dict(case.render_anchor),
                "annotation_labels": dict(case.role_tokens),
                "annotation_centers": dict(case.annotation_centers),
                "coord_space": "pixel",
            },
            "execution_trace": {
                "task_variant": str(case.task_variant),
                "formula_expression": str(case.formula_expression),
                "answer_type": str(case.answer_type),
                "answer_scalar": int(case.answer_scalar),
                "answer_value": case.answer_value,
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
