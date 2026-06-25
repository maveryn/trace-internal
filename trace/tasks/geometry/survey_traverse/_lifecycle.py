"""Neutral lifecycle plumbing for survey-traverse public task files."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from PIL import Image

from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.defaults import POST_IMAGE_NOISE_DEFAULTS
from .shared.rendering import create_render_context
from .shared.state import SCENE_ID, SCENE_KIND, RenderContext, RenderedAreaScene, RenderedPointScene


@dataclass(frozen=True)
class SurveyRenderedAttempt:
    """Rendered image and annotation artifacts returned by one public task."""

    context: RenderContext
    rendered: RenderedPointScene | RenderedAreaScene
    image: Image.Image
    noise_meta: dict[str, Any]
    annotation_artifacts: PixelAnnotationArtifacts


def render_survey_attempts(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
    render_defaults: Mapping[str, Any],
    render_scene: Callable[[RenderContext, int], RenderedPointScene | RenderedAreaScene],
    build_annotation: Callable[[RenderedPointScene | RenderedAreaScene], PixelAnnotationArtifacts],
) -> SurveyRenderedAttempt:
    """Run neutral render retries after a public task has bound its scene case."""

    last_error: Exception | None = None
    for attempt in range(max(1, int(max_attempts))):
        attempt_seed = int(instance_seed) + int(attempt)
        try:
            context, _render_meta = create_render_context(
                instance_seed=int(attempt_seed),
                params=params,
                render_defaults=render_defaults,
            )
            rendered = render_scene(context, int(attempt_seed))
            image, noise_meta = apply_post_image_noise(
                rendered.image,
                instance_seed=int(instance_seed),
                params=params,
                default_config=POST_IMAGE_NOISE_DEFAULTS,
            )
            return SurveyRenderedAttempt(
                context=context,
                rendered=rendered,
                image=image,
                noise_meta=dict(noise_meta),
                annotation_artifacts=build_annotation(rendered),
            )
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError("failed to render survey traverse scene") from last_error


def build_survey_trace_payload(
    *,
    task_identity: str,
    query_id: str,
    formula_family: str,
    rendered_attempt: SurveyRenderedAttempt,
    prompt_artifacts: Any,
    answer_value: int,
    query_probabilities: Mapping[str, float],
    query_params_extra: Mapping[str, Any],
    execution_extra: Mapping[str, Any],
    witness_extra: Mapping[str, Any],
    relation_extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the survey trace envelope from task-owned metadata fragments."""

    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(query_id),
        params={
            "scene_id": SCENE_ID,
            "query_id_probabilities": dict(query_probabilities),
            **dict(query_params_extra),
        },
    )
    query_spec["task_id"] = str(task_identity)
    query_spec["scene_id"] = SCENE_ID
    execution_trace = {
        "task_id": str(task_identity),
        "scene_id": SCENE_ID,
        "query_id": str(query_id),
        "answer": int(answer_value),
        "formula_family": str(formula_family),
        "annotation_roles": list(rendered_attempt.rendered.annotation_roles),
        **dict(execution_extra),
    }
    return {
        "scene_ir": {
            "scene_kind": SCENE_KIND,
            "scene_id": SCENE_ID,
            "task_id": str(task_identity),
            "query_id": str(query_id),
            "entities": [dict(entity) for entity in rendered_attempt.rendered.scene_entities],
            "relations": {
                "query_id": str(query_id),
                "answer_value": int(answer_value),
                "annotation_roles": list(rendered_attempt.rendered.annotation_roles),
                "formula_family": str(formula_family),
                **dict(relation_extra or {}),
            },
        },
        "query_spec": query_spec,
        "render_spec": {
            "task_id": str(task_identity),
            "scene_id": SCENE_ID,
            "query_id": str(query_id),
            "canvas": {"width": int(rendered_attempt.image.size[0]), "height": int(rendered_attempt.image.size[1])},
            "style": {
                "technical_diagram": dict(rendered_attempt.context.diagram_style_meta),
                "background": dict(rendered_attempt.context.background_meta),
                "post_image_noise": dict(rendered_attempt.noise_meta),
            },
            "prompt": {
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            },
        },
        "render_map": dict(rendered_attempt.rendered.render_map),
        "execution_trace": execution_trace,
        "witness_symbolic": {
            "task_id": str(task_identity),
            "scene_id": SCENE_ID,
            "query_id": str(query_id),
            "formula_family": str(formula_family),
            "answer_value": int(answer_value),
            **dict(witness_extra),
        },
        "projected_annotation": dict(rendered_attempt.annotation_artifacts.projected_annotation),
    }


def survey_output_metadata(*, prompt_artifacts: Any, query_name: str) -> dict[str, Any]:
    """Return neutral output metadata for a public task's final TaskOutput."""

    return {
        "task_versions": default_task_versions(),
        "scene_id": SCENE_ID,
        "query_id": str(query_name),
        "prompt_variants": dict(prompt_artifacts.prompt_variants),
    }


__all__ = [
    "SurveyRenderedAttempt",
    "build_survey_trace_payload",
    "render_survey_attempts",
    "survey_output_metadata",
]
