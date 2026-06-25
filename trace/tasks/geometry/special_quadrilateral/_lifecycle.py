"""Neutral render plumbing for special-quadrilateral tasks."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from PIL import Image

from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.annotations import special_quadrilateral_point_annotation
from .shared.defaults import POST_IMAGE_NOISE_DEFAULTS, load_special_quadrilateral_defaults
from .shared.rendering import create_render_context, draw_special_quadrilateral_scene
from .shared.state import QuadrilateralCase, RenderedSpecialQuadrilateralScene, SpecialQuadrilateralProblem


@dataclass(frozen=True)
class SpecialQuadrilateralRenderParts:
    """Rendered scene artifacts that are independent of public task identity."""

    image: Image.Image
    rendered: RenderedSpecialQuadrilateralScene
    annotation_artifacts: PixelAnnotationArtifacts
    noise_meta: dict[str, Any]
    prompt_defaults: Mapping[str, Any]
    task_versions: dict[str, str]


def expression_payload(case: QuadrilateralCase) -> dict[str, Any]:
    """Serialize visible linear expressions when the resolved case uses them."""

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


def render_special_quadrilateral_problem(
    *,
    problem: SpecialQuadrilateralProblem,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> SpecialQuadrilateralRenderParts:
    """Render one resolved special-quadrilateral case and project annotation."""

    _generation_defaults, render_defaults, prompt_defaults = load_special_quadrilateral_defaults()
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
        raise RuntimeError("failed to render special quadrilateral scene") from last_error
    if rendered is None:
        raise RuntimeError("failed to render special quadrilateral scene")

    image, noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    annotation_artifacts = special_quadrilateral_point_annotation(rendered)
    return SpecialQuadrilateralRenderParts(
        image=image,
        rendered=rendered,
        annotation_artifacts=annotation_artifacts,
        noise_meta=dict(noise_meta),
        prompt_defaults=dict(prompt_defaults),
        task_versions=default_task_versions(),
    )


__all__ = [
    "SpecialQuadrilateralRenderParts",
    "expression_payload",
    "render_special_quadrilateral_problem",
]
