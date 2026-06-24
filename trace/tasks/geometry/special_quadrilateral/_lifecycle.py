"""Neutral render, prompt, and trace plumbing for special-quadrilateral tasks."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from PIL import Image

from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import special_quadrilateral_point_annotation
from .shared.defaults import DOMAIN, POST_IMAGE_NOISE_DEFAULTS, SCENE_ID, SCENE_KIND, load_special_quadrilateral_defaults
from .shared.prompts import build_special_quadrilateral_prompt_artifacts
from .shared.rendering import create_render_context, draw_special_quadrilateral_scene
from .shared.state import QuadrilateralCase, RenderedSpecialQuadrilateralScene, SpecialQuadrilateralProblem


@dataclass(frozen=True)
class SpecialQuadrilateralTaskParts:
    """Prepared non-verifier output fields for one public task."""

    prompt: str
    prompt_variants: dict[str, str]
    image: Image.Image
    annotation_artifacts: PixelAnnotationArtifacts
    trace_payload: dict[str, Any]
    task_versions: dict[str, str]
    scene_id: str


def _expression_payload(case: QuadrilateralCase) -> dict[str, Any]:
    """Serialize algebraic labels when the selected case has visible expressions."""

    if case.target_expression is None or case.support_expression is None:
        return {}
    x_value = int(case.x_value or 0)
    return {
        "x_value": int(x_value),
        "target_expression": {
            "coefficient": int(case.target_expression.coefficient),
            "constant": int(case.target_expression.constant),
            "value": int(case.target_expression.evaluate(x_value)),
            "display": str(case.target_label),
        },
        "support_expression": {
            "coefficient": int(case.support_expression.coefficient),
            "constant": int(case.support_expression.constant),
            "value": int(case.support_expression.evaluate(x_value)),
            "display": str(case.support_label),
        },
    }


def _trace_payload(
    *,
    public_task_id: str,
    selected_query: str,
    branch_probabilities: Mapping[str, float],
    answer_probabilities: Mapping[str, float],
    prompt_artifacts: Any,
    problem: SpecialQuadrilateralProblem,
    rendered: RenderedSpecialQuadrilateralScene,
    annotation_artifacts: PixelAnnotationArtifacts,
    noise_meta: Mapping[str, Any],
    image_size: tuple[int, int],
) -> dict[str, Any]:
    """Build trace sections from task-bound values and rendered annotations."""

    case = problem.case
    annotation_roles = [str(role) for role in rendered.annotation_points.keys()]
    expression_payload = _expression_payload(case)
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_query),
        params={
            "scene_id": SCENE_ID,
            "query_id_probabilities": dict(branch_probabilities),
            "answer_support_probabilities": dict(answer_probabilities),
            "case_index": int(problem.case_index),
            "shape_kind": str(case.shape_kind),
            "theorem": str(case.theorem),
            **dict(expression_payload),
        },
    )
    query_spec["scene_id"] = SCENE_ID
    trace_values = {
        "scene_id": SCENE_ID,
        "query_id": str(selected_query),
        "query_id_probabilities": dict(branch_probabilities),
        "answer_support_probabilities": dict(answer_probabilities),
        "shape_kind": str(case.shape_kind),
        "target_name": str(case.target_name),
        "target_label": str(case.target_label),
        "support_label": str(case.support_label),
        "theorem": str(case.theorem),
        "answer_type": "integer",
        "answer": int(case.answer),
        "answer_value": int(case.answer),
        "annotation_roles": list(annotation_roles),
        **dict(expression_payload),
    }
    return {
        "scene_ir": {
            "domain": DOMAIN,
            "scene_kind": SCENE_KIND,
            "scene_id": SCENE_ID,
            "task_id": str(public_task_id),
            "query_id": str(selected_query),
            "entities": [
                {
                    "type": str(case.shape_kind),
                    "labels": ["A", "B", "C", "D"],
                    "vertices": {
                        key: [round(float(point[0]), 3), round(float(point[1]), 3)]
                        for key, point in rendered.vertices.items()
                    },
                }
            ],
            "relations": {
                "theorem": str(case.theorem),
                "query_id": str(selected_query),
                "answer_value": int(case.answer),
            },
        },
        "query_spec": query_spec,
        "render_spec": {
            "task_id": str(public_task_id),
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            "canvas": {"width": int(image_size[0]), "height": int(image_size[1])},
            "single_object_scene_rotation": rendered.render_map.get("single_object_scene_rotation", {}),
            "style": {
                "post_image_noise": dict(noise_meta),
            },
            "prompt": {
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            },
        },
        "render_map": dict(rendered.render_map),
        "execution_trace": dict(trace_values),
        "witness_symbolic": {
            "type": "special_quadrilateral_theorem_measurement",
            "task_id": str(public_task_id),
            **dict(trace_values),
        },
        "projected_annotation": dict(annotation_artifacts.projected_annotation),
    }


def prepare_special_quadrilateral_task_parts(
    *,
    public_task_id: str,
    selected_query: str,
    branch_probabilities: Mapping[str, float],
    answer_probabilities: Mapping[str, float],
    problem: SpecialQuadrilateralProblem,
    prompt_task_key: str,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> SpecialQuadrilateralTaskParts:
    """Render shared artifacts after the public task binds the objective case."""

    _generation_defaults, render_defaults, prompt_defaults = load_special_quadrilateral_defaults(str(public_task_id))
    last_error: Exception | None = None
    rendered: RenderedSpecialQuadrilateralScene | None = None
    for attempt in range(max(1, int(max_attempts))):
        try:
            attempt_seed = int(instance_seed) + int(attempt)
            ctx = create_render_context(
                instance_seed=int(attempt_seed),
                params=params,
                render_defaults=render_defaults,
            )
            rendered = draw_special_quadrilateral_scene(
                problem=replace(problem, layout_seed=int(attempt_seed)),
                ctx=ctx,
            )
            rendered.render_map["single_object_scene_rotation"] = ctx.scene_transform.metadata()
            rendered.render_map["style"] = {
                "technical_diagram": dict(ctx.diagram_style_meta),
                "background": dict(ctx.background_meta),
            }
            break
        except Exception as exc:
            last_error = exc
            continue
    else:
        raise RuntimeError(f"failed to render special quadrilateral scene for {public_task_id}") from last_error
    if rendered is None:
        raise RuntimeError(f"failed to render special quadrilateral scene for {public_task_id}")

    image, noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    annotation_artifacts = special_quadrilateral_point_annotation(rendered)
    prompt_artifacts = build_special_quadrilateral_prompt_artifacts(
        prompt_defaults=prompt_defaults,
        prompt_task_key=str(prompt_task_key),
        prompt_query_key=str(selected_query),
        target_name=str(problem.case.target_name),
        annotation_roles=tuple(annotation_artifacts.value.keys()),
        answer_value=int(problem.case.answer),
        instance_seed=int(instance_seed),
    )
    trace_payload = _trace_payload(
        public_task_id=str(public_task_id),
        selected_query=str(selected_query),
        branch_probabilities=branch_probabilities,
        answer_probabilities=answer_probabilities,
        prompt_artifacts=prompt_artifacts,
        problem=problem,
        rendered=rendered,
        annotation_artifacts=annotation_artifacts,
        noise_meta=noise_meta,
        image_size=(int(image.size[0]), int(image.size[1])),
    )
    return SpecialQuadrilateralTaskParts(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        image=image,
        annotation_artifacts=annotation_artifacts,
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
    )


__all__ = [
    "SpecialQuadrilateralTaskParts",
    "prepare_special_quadrilateral_task_parts",
]
