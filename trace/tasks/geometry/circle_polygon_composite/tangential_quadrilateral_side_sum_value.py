"""Compute an opposite-side sum in a tangential quadrilateral."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.core.scene_config import get_scene_defaults
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import required_group_defaults, split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_query_spec,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from trace.tasks.geometry.shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from trace.tasks.geometry.shared.vector2d import point_to_list

from .shared.rendering import (
    SCENE_ID,
    RenderedTangentialScene,
    make_render_context,
    make_tangential_prompt_examples,
    render_tangential_scene,
    resolve_tangential_problem,
)


TASK_ID = "task_geometry__circle_polygon_composite__tangential_quadrilateral_side_sum_value"
QUERY_ID = "opposite_side_sum_from_tangent_quadrilateral"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)

SQUARE_CIRCLE_TANGENT_ANGLE_TASK_ID = "task_geometry__circle_polygon_composite__square_circle_tangent_angle_value"
SQUARE_CIRCLE_TANGENT_ANGLE_QUERY_IDS: Tuple[str, ...] = (
    "square_incircle_tangent_angle",
    "square_semicircle_tangent_angle",
)

_SCENE_DEFAULTS = get_scene_defaults("geometry", SCENE_ID)
_GEN_DEFAULTS_UNUSED, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS,
    task_id=TASK_ID,
)


def _prompt_artifacts(*, selected_query: str, problem: Any, instance_seed: int) -> tuple[Dict[str, Any], Any]:
    defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "object_description",
            "json_output_contract",
            "json_output_contract_answer_only",
            "annotation_hint",
            "answer_hint_integer",
        ),
        context=f"prompt defaults for {TASK_ID}",
    )
    json_example, json_example_answer_only = make_tangential_prompt_examples()
    prompt_selection = render_scene_prompt_variants(
        domain="geometry",
        scene_id=SCENE_ID,
        bundle_id=str(defaults["bundle_id"]),
        scene_key=str(defaults["scene_key"]),
        task_key=str(defaults["task_key"]),
        query_key=str(selected_query),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(defaults["object_description"]),
            "target_pair": str(problem.target_pair_label),
            "known_pair": str(problem.known_pair_label),
            "json_output_contract": str(defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(defaults["annotation_hint"]),
            "answer_hint": str(defaults["answer_hint_integer"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        },
        instance_seed=int(instance_seed),
    )
    return dict(defaults), build_prompt_trace_artifacts(prompt_selection)


def _annotation_value(rendered: RenderedTangentialScene) -> Dict[str, list[float]]:
    return {str(key): point_to_list(value) for key, value in rendered.annotation_keyed_points.items()}


@register_task
class GeometryCirclePolygonCompositeTangentialQuadrilateralSideSumValueTask:
    """Compute an opposite side sum in a tangential quadrilateral."""

    task_id = TASK_ID
    domain = "geometry"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
        )
        problem = resolve_tangential_problem(
            instance_seed=int(instance_seed),
            params=task_params,
            target_pair_namespace=f"{TASK_ID}.{selected_query}.target_pair",
            tangent_case_namespace=f"{TASK_ID}.{selected_query}.tangent_case",
        )

        rendered: RenderedTangentialScene | None = None
        ctx = None
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_params = dict(task_params)
            attempt_params["_render_attempt"] = int(attempt)
            try:
                ctx = make_render_context(
                    instance_seed=int(instance_seed) + int(attempt),
                    params=attempt_params,
                    rendering_defaults=_RENDER_DEFAULTS,
                    fill_namespace=f"{TASK_ID}.{selected_query}.fill_palette",
                )
                rendered = render_tangential_scene(
                    ctx,
                    problem,
                    instance_seed=int(instance_seed) + int(attempt),
                    render_namespace=f"{TASK_ID}.{selected_query}.render.scene",
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if rendered is None or ctx is None:
            raise RuntimeError(f"failed to generate {TASK_ID}") from last_error

        image, noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=task_params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults, prompt_artifacts = _prompt_artifacts(
            selected_query=str(selected_query),
            problem=problem,
            instance_seed=int(instance_seed),
        )
        annotation_value = _annotation_value(rendered)
        opposite_sum_ab_cd = int(problem.side_lengths["AB"] + problem.side_lengths["CD"])
        opposite_sum_bc_da = int(problem.side_lengths["BC"] + problem.side_lengths["DA"])
        query_spec = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query),
            params={
                "query_id": str(selected_query),
                "query_id_probabilities": dict(query_probabilities),
                "target_pair": str(problem.target_pair),
                "target_pair_probabilities": dict(problem.target_pair_probabilities),
                "tangent_case_probabilities": dict(problem.tangent_case_probabilities),
            },
        )
        query_spec["scene_id"] = SCENE_ID
        query_spec["task_id"] = TASK_ID
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "task_id": TASK_ID,
                "query_id": str(selected_query),
                "entities": {
                    "vertices": dict(rendered.render_map["vertices"]),
                    "tangency_points": dict(rendered.render_map["tangency_points"]),
                    "incircle_center": list(rendered.render_map["incircle_center"]),
                },
                "relations": {
                    "type": "tangential_quadrilateral_opposite_side_sum",
                    "target_pair": str(problem.target_pair),
                    "known_pair": str(problem.known_pair),
                },
            },
            "query_spec": query_spec,
            "render_spec": {
                "task_id": TASK_ID,
                "scene_id": SCENE_ID,
                "query_id": str(selected_query),
                "canvas": {"width": int(ctx.width), "height": int(ctx.height)},
                "single_object_scene_rotation": ctx.scene_transform.metadata(),
                "style": {
                    "technical_diagram": dict(ctx.diagram_style_meta),
                    "background": dict(ctx.background_meta),
                    "post_image_noise": dict(noise_meta),
                },
                "prompt": {
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                },
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "task_id": TASK_ID,
                "scene_id": SCENE_ID,
                "query_id": str(selected_query),
                "target_pair": str(problem.target_pair),
                "known_pair": str(problem.known_pair),
                "vertex_tangents": dict(problem.vertex_tangents),
                "side_lengths": dict(problem.side_lengths),
                "opposite_sum_AB_CD": int(opposite_sum_ab_cd),
                "opposite_sum_BC_DA": int(opposite_sum_bc_da),
                "answer": int(problem.answer),
                "annotation_roles": list(rendered.annotation_roles),
            },
            "witness_symbolic": {
                "task_id": TASK_ID,
                "scene_id": SCENE_ID,
                "query_id": str(selected_query),
                "formula_family": "pitot_theorem_tangential_quadrilateral",
                "target_pair": str(problem.target_pair),
                "known_pair": str(problem.known_pair),
                "vertex_tangents": dict(problem.vertex_tangents),
                "side_lengths": dict(problem.side_lengths),
                "opposite_sum_AB_CD": int(opposite_sum_ab_cd),
                "opposite_sum_BC_DA": int(opposite_sum_bc_da),
                "answer_value": int(problem.answer),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_value),
                "pixel_keyed_point_map": dict(annotation_value),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(problem.answer)),
            annotation_gt=TypedValue(type="keyed_point_map", value=dict(annotation_value)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "GeometryCirclePolygonCompositeTangentialQuadrilateralSideSumValueTask",
    "QUERY_ID",
    "SUPPORTED_QUERY_IDS",
    "SQUARE_CIRCLE_TANGENT_ANGLE_QUERY_IDS",
    "SQUARE_CIRCLE_TANGENT_ANGLE_TASK_ID",
    "TASK_ID",
]
