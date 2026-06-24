"""Neutral lifecycle plumbing for trapezoid-extension public task files."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from PIL import Image

from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec

from .shared.annotations import trapezoid_extension_annotation
from .shared.defaults import POST_IMAGE_NOISE_DEFAULTS, load_trapezoid_extension_defaults
from .shared.prompts import build_trapezoid_extension_prompt_artifacts
from .shared.rendering import create_render_context, render_trapezoid_extension_scene
from .shared.state import (
    DOMAIN,
    SCENE_ID,
    SCENE_KIND,
    RenderContext,
    RenderedTrapezoidExtensionScene,
    TrapezoidExtensionProblem,
)

RenderBuilder = Callable[[RenderContext, TrapezoidExtensionProblem], RenderedTrapezoidExtensionScene]


@dataclass(frozen=True)
class TrapezoidExtensionObjectivePlan:
    """Task-owned objective binding prepared by one public task file."""

    prompt_key: str
    problem: TrapezoidExtensionProblem
    render_scene: RenderBuilder
    answer_value: float
    query_params: Mapping[str, Any]
    trace_values: Mapping[str, Any]


@dataclass(frozen=True)
class TrapezoidExtensionRenderedAttempt:
    """Rendered image plus annotation artifacts for one attempt."""

    image: Image.Image
    rendered: RenderedTrapezoidExtensionScene
    render_meta: Mapping[str, Any]
    noise_meta: Mapping[str, Any]
    annotation_artifacts: PixelAnnotationArtifacts


def _render_attempts(
    *,
    plan: TrapezoidExtensionObjectivePlan,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
    render_defaults: Mapping[str, Any],
    namespace: str,
) -> TrapezoidExtensionRenderedAttempt:
    """Retry neutral rendering after a public task has resolved its formula."""

    last_error: Exception | None = None
    for _attempt in range(max(1, int(max_attempts))):
        try:
            context, render_meta_attempt = create_render_context(
                instance_seed=int(instance_seed),
                params=params,
                render_defaults=render_defaults,
                namespace=str(namespace),
            )
            rendered = plan.render_scene(context, plan.problem)
            render_meta = dict(render_meta_attempt)
            render_meta["single_object_scene_rotation"] = context.scene_transform.metadata()
            image, noise_meta = apply_post_image_noise(
                rendered.image,
                instance_seed=int(instance_seed),
                params=params,
                default_config=POST_IMAGE_NOISE_DEFAULTS,
            )
            return TrapezoidExtensionRenderedAttempt(
                image=image,
                rendered=rendered,
                render_meta=render_meta,
                noise_meta=dict(noise_meta),
                annotation_artifacts=trapezoid_extension_annotation(rendered),
            )
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError("failed to render trapezoid-extension scene") from last_error


def _trace_payload(
    *,
    task_identity: str,
    selected_query: str,
    branch_probabilities: Mapping[str, float],
    prompt_artifacts: PromptTraceArtifacts,
    attempt: TrapezoidExtensionRenderedAttempt,
    plan: TrapezoidExtensionObjectivePlan,
) -> dict[str, Any]:
    """Build trace sections from task-owned formula and witness metadata."""

    query_params = {
        "scene_id": SCENE_ID,
        "query_id_probabilities": dict(branch_probabilities),
        **dict(plan.query_params),
    }
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_query),
        params=query_params,
    )
    query_spec["task_id"] = str(task_identity)
    query_spec["scene_id"] = SCENE_ID
    rendered = attempt.rendered
    return {
        "scene_ir": {
            "scene_kind": SCENE_KIND,
            "scene_id": SCENE_ID,
            "task_id": str(task_identity),
            "query_id": str(selected_query),
            "entities": [dict(entity) for entity in rendered.scene_entities],
            "relations": {
                "query_id": str(selected_query),
                "answer_value": float(plan.answer_value),
                "annotation_roles": list(rendered.annotation_roles),
            },
        },
        "query_spec": query_spec,
        "render_spec": {
            "task_id": str(task_identity),
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            "canvas": {"width": int(attempt.image.size[0]), "height": int(attempt.image.size[1])},
            "style": {
                **dict(attempt.render_meta),
                "post_image_noise": dict(attempt.noise_meta),
            },
            "prompt": {
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            },
        },
        "render_map": {"coord_space": "pixel", **dict(rendered.render_map)},
        "execution_trace": {
            "task_id": str(task_identity),
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            "answer_type": "number",
            "answer_value": float(plan.answer_value),
            "answer_rounding": "one_decimal",
            "annotation_roles": list(rendered.annotation_roles),
            "reasoning_steps": int(plan.problem.reasoning_steps),
            **dict(plan.trace_values),
        },
        "witness_symbolic": {
            "task_id": str(task_identity),
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            "type": "trapezoid_extension_formula",
            "source_witness_type": "bbox_map",
            "answer_value": float(plan.answer_value),
            **dict(plan.trace_values),
        },
        "projected_annotation": dict(attempt.annotation_artifacts.projected_annotation),
    }


def run_trapezoid_extension_public_entry(
    task: Any,
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Run common plumbing after one public task binds its objective plan."""

    selected_query, branch_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=tuple(str(value) for value in task.supported_query_ids),
        default_query_id=str(task.default_query_id),
        task_id=str(task.task_id),
        namespace=f"{task.task_id}.query",
    )
    _generation_defaults, render_defaults, prompt_defaults = load_trapezoid_extension_defaults(str(task.task_id))
    plan = task.prepare_objective(
        instance_seed=int(instance_seed),
        params=task_params,
        selected_query=str(selected_query),
        branch_probabilities=branch_probabilities,
    )
    attempt = _render_attempts(
        plan=plan,
        instance_seed=int(instance_seed),
        params=task_params,
        max_attempts=int(max_attempts),
        render_defaults=render_defaults,
        namespace=str(task.task_id),
    )
    prompt_artifacts = build_trapezoid_extension_prompt_artifacts(
        prompt_defaults=prompt_defaults,
        task_prompt_key=str(plan.prompt_key),
        prompt_branch_key=str(selected_query),
        annotation_roles=attempt.rendered.annotation_roles,
        answer_value=float(plan.answer_value),
        instance_seed=int(instance_seed),
    )
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=TypedValue(type="number", value=float(plan.answer_value)),
        annotation_gt=TypedValue(
            type=str(attempt.annotation_artifacts.annotation_type),
            value=attempt.annotation_artifacts.value,
        ),
        image=attempt.image,
        image_id="img0",
        trace_payload=_trace_payload(
            task_identity=str(task.task_id),
            selected_query=str(selected_query),
            branch_probabilities=branch_probabilities,
            prompt_artifacts=prompt_artifacts,
            attempt=attempt,
            plan=plan,
        ),
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(selected_query),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


__all__ = ["TrapezoidExtensionObjectivePlan", "run_trapezoid_extension_public_entry"]
