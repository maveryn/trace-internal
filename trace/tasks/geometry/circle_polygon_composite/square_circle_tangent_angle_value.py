"""Compute a tangent angle in a square or semicircle construction."""

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
    RenderedAngleScene,
    make_angle_prompt_examples,
    make_render_context,
    render_angle_scene,
    resolve_angle_problem,
)


TASK_ID = "task_geometry__circle_polygon_composite__square_circle_tangent_angle_value"
QUERY_ID_INCIRCLE = "square_incircle_tangent_angle"
QUERY_ID_SEMICIRCLE = "square_semicircle_tangent_angle"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID_INCIRCLE, QUERY_ID_SEMICIRCLE)

_CONSTRUCTION_BY_QUERY = {
    QUERY_ID_INCIRCLE: "incircle",
    QUERY_ID_SEMICIRCLE: "semicircle",
}
_SCENE_DEFAULTS = get_scene_defaults("geometry", SCENE_ID)
_GEN_DEFAULTS_UNUSED, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS,
    task_id=TASK_ID,
)


def _prompt_artifacts(*, selected_query: str, instance_seed: int) -> tuple[Dict[str, Any], Any]:
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
    json_example, json_example_answer_only = make_angle_prompt_examples()
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


def _annotation_value(rendered: RenderedAngleScene) -> Dict[str, list[float]]:
    return {str(key): point_to_list(value) for key, value in rendered.annotation_keyed_points.items()}


@register_task
class GeometryCirclePolygonCompositeSquareCircleTangentAngleValueTask:
    """Compute an angle from a tangent-radius construction."""

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
            default_query_id=QUERY_ID_INCIRCLE,
            task_id=TASK_ID,
        )
        construction_kind = _CONSTRUCTION_BY_QUERY[str(selected_query)]
        problem = resolve_angle_problem(
            instance_seed=int(instance_seed),
            params=task_params,
            construction_kind=str(construction_kind),
            angle_namespace=f"{TASK_ID}.{selected_query}.target_angle",
            side_namespace=f"{TASK_ID}.{selected_query}.side_sign",
        )

        rendered: RenderedAngleScene | None = None
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
                rendered = render_angle_scene(
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
            instance_seed=int(instance_seed),
        )
        annotation_value = _annotation_value(rendered)
        query_spec = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query),
            params={
                "query_id": str(selected_query),
                "query_id_probabilities": dict(query_probabilities),
                "answer_support_probabilities": dict(problem.angle_probabilities),
                "side_probabilities": dict(problem.side_probabilities),
                "construction_kind": str(problem.construction_kind),
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
                    "shape_corners": dict(rendered.render_map["shape_corners"]),
                    "circle_center": list(rendered.render_map["circle_center"]),
                    "tangent_point": list(rendered.render_map["tangent_point"]),
                },
                "relations": {
                    "type": "square_circle_tangent_angle_transfer",
                    "construction_kind": str(problem.construction_kind),
                    "known_angle_degrees": int(problem.answer),
                    "target_angle_degrees": int(problem.answer),
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
                "answer": int(problem.answer),
                "known_angle_degrees": int(problem.answer),
                "target_angle_degrees": int(problem.answer),
                "side_sign": int(problem.side_sign),
                "construction_kind": str(problem.construction_kind),
                "annotation_roles": list(rendered.annotation_roles),
            },
            "witness_symbolic": {
                "task_id": TASK_ID,
                "scene_id": SCENE_ID,
                "query_id": str(selected_query),
                "formula_family": "tangent_radius_perpendicular_angle_transfer",
                "construction_kind": str(problem.construction_kind),
                "known_angle_degrees": int(problem.answer),
                "target_angle_degrees": int(problem.answer),
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
    "GeometryCirclePolygonCompositeSquareCircleTangentAngleValueTask",
    "QUERY_ID_INCIRCLE",
    "QUERY_ID_SEMICIRCLE",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
