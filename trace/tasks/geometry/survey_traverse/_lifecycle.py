"""Neutral lifecycle plumbing for survey-traverse public task files."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from PIL import Image

from trace.core.visual.noise import apply_post_image_noise
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.defaults import POST_IMAGE_NOISE_DEFAULTS
from .shared.prompts import build_survey_traverse_prompt_artifacts
from .shared.rendering import create_render_context
from .shared.state import DOMAIN, SCENE_ID, SCENE_KIND, RenderContext, RenderedAreaScene, RenderedPointScene


@dataclass(frozen=True)
class SurveyRenderedAttempt:
    """Rendered image and annotation artifacts returned by one public task."""

    context: RenderContext
    rendered: RenderedPointScene | RenderedAreaScene
    image: Image.Image
    noise_meta: dict[str, Any]
    annotation_artifacts: PixelAnnotationArtifacts


@dataclass(frozen=True)
class SurveyTraceFields:
    """Task-owned metadata fragments injected into the common trace shape."""

    formula_family: str
    query_params_extra: Mapping[str, Any]
    execution_extra: Mapping[str, Any]
    witness_extra: Mapping[str, Any]
    relation_extra: Mapping[str, Any]


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
    branch_name: str,
    rendered_attempt: SurveyRenderedAttempt,
    prompt_artifacts: Any,
    answer_value: int,
    branch_probabilities: Mapping[str, float],
    trace_fields: SurveyTraceFields,
) -> dict[str, Any]:
    """Build the shared trace envelope from task-owned formula metadata."""

    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(branch_name),
        params={
            "scene_id": SCENE_ID,
            "query_id_probabilities": dict(branch_probabilities),
            **dict(trace_fields.query_params_extra),
        },
    )
    query_spec["task_id"] = str(task_identity)
    query_spec["scene_id"] = SCENE_ID
    execution_trace = {
        "task_id": str(task_identity),
        "scene_id": SCENE_ID,
        "query_id": str(branch_name),
        "answer": int(answer_value),
        "formula_family": str(trace_fields.formula_family),
        "annotation_roles": list(rendered_attempt.rendered.annotation_roles),
        **dict(trace_fields.execution_extra),
    }
    return {
        "scene_ir": {
            "scene_kind": SCENE_KIND,
            "scene_id": SCENE_ID,
            "task_id": str(task_identity),
            "query_id": str(branch_name),
            "entities": [dict(entity) for entity in rendered_attempt.rendered.scene_entities],
            "relations": {
                "query_id": str(branch_name),
                "answer_value": int(answer_value),
                "annotation_roles": list(rendered_attempt.rendered.annotation_roles),
                **dict(trace_fields.relation_extra),
            },
        },
        "query_spec": query_spec,
        "render_spec": {
            "task_id": str(task_identity),
            "scene_id": SCENE_ID,
            "query_id": str(branch_name),
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
            "query_id": str(branch_name),
            "formula_family": str(trace_fields.formula_family),
            "answer_value": int(answer_value),
            **dict(trace_fields.witness_extra),
        },
        "projected_annotation": dict(rendered_attempt.annotation_artifacts.projected_annotation),
    }


def run_survey_public_task(
    *,
    task_identity: str,
    supported_branches: Sequence[str],
    default_branch: str,
    task_prompt_key: str,
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
    resolve_problem: Callable[..., Any],
    render_attempt: Callable[..., SurveyRenderedAttempt],
    answer_value: Callable[[Any], int],
    trace_fields: Callable[[Any, SurveyRenderedAttempt, int], SurveyTraceFields],
) -> TaskOutput:
    """Run common public-task plumbing around task-owned objective hooks."""

    branch_name, branch_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=tuple(str(item) for item in supported_branches),
        default_query_id=str(default_branch),
        task_id=str(task_identity),
    )
    problem = resolve_problem(
        branch_name=str(branch_name),
        branch_probabilities=branch_probabilities,
        instance_seed=int(instance_seed),
        params=task_params,
    )
    rendered_attempt = render_attempt(
        problem=problem,
        instance_seed=int(instance_seed),
        params=task_params,
        max_attempts=int(max_attempts),
    )
    answer = int(answer_value(problem))
    prompt_artifacts = build_survey_traverse_prompt_artifacts(
        prompt_defaults=prompt_defaults,
        task_prompt_key=str(task_prompt_key),
        prompt_branch_key=str(branch_name),
        annotation_roles=rendered_attempt.rendered.annotation_roles,
        annotation_kind=str(rendered_attempt.annotation_artifacts.annotation_type),
        answer_value=int(answer),
        instance_seed=int(instance_seed),
    )
    task_trace_fields = trace_fields(problem, rendered_attempt, int(answer))
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=TypedValue(type="integer", value=int(answer)),
        annotation_gt=TypedValue(
            type=str(rendered_attempt.annotation_artifacts.annotation_type),
            value=rendered_attempt.annotation_artifacts.value,
        ),
        image=rendered_attempt.image,
        image_id="img0",
        trace_payload=build_survey_trace_payload(
            task_identity=str(task_identity),
            branch_name=str(branch_name),
            rendered_attempt=rendered_attempt,
            prompt_artifacts=prompt_artifacts,
            answer_value=int(answer),
            branch_probabilities=branch_probabilities,
            trace_fields=task_trace_fields,
        ),
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(branch_name),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


__all__ = ["SurveyRenderedAttempt", "SurveyTraceFields", "render_survey_attempts", "run_survey_public_task"]
