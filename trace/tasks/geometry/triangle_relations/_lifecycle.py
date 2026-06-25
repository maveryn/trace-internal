"""Neutral lifecycle plumbing for triangle-relations public task files."""

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

from .shared.annotations import triangle_relations_annotation
from .shared.construction import case_trace_values
from .shared.defaults import POST_IMAGE_NOISE_DEFAULTS, load_triangle_relations_defaults
from .shared.prompts import build_triangle_relations_prompt_artifacts
from .shared.rendering import create_render_context, render_triangle_relations_scene
from .shared.state import (
    DOMAIN,
    SCENE_ID,
    SCENE_KIND,
    RenderContext,
    RenderedTriangleRelationsScene,
    TriangleRelationsCase,
    TriangleRelationsProblem,
)

RenderBuilder = Callable[[RenderContext, TriangleRelationsProblem], RenderedTriangleRelationsScene]


@dataclass(frozen=True)
class TriangleRelationsObjectivePlan:
    """Task-owned objective binding prepared by one public task file."""

    prompt_key: str
    problem: TriangleRelationsProblem
    render_scene: RenderBuilder
    answer_value: int | float
    answer_type: str
    answer_rounding: str
    query_params: Mapping[str, Any]
    trace_values: Mapping[str, Any]


@dataclass(frozen=True)
class TriangleRelationsRenderedAttempt:
    """Rendered image plus annotation artifacts for one attempt."""

    image: Image.Image
    rendered: RenderedTriangleRelationsScene
    render_meta: Mapping[str, Any]
    noise_meta: Mapping[str, Any]
    annotation_artifacts: PixelAnnotationArtifacts


def bind_triangle_relations_plan(
    *,
    prompt_key: str,
    case: TriangleRelationsCase,
    answer_support_probabilities: Mapping[str, float],
    branch_probabilities: Mapping[str, float],
    trace_values: Mapping[str, Any] | None = None,
) -> TriangleRelationsObjectivePlan:
    """Bind a task-selected construction case into lifecycle-neutral state."""

    if case.point_annotation_labels:
        annotation_mode = "point_map"
    elif case.target_point is not None:
        annotation_mode = "point"
    elif case.target_segment is not None:
        annotation_mode = "segment"
    else:
        raise ValueError("triangle-relations case must define an annotation witness")
    combined_trace = {
        "target_support_probabilities": dict(answer_support_probabilities),
        "query_id_probabilities": dict(branch_probabilities),
        **dict(trace_values or {}),
    }
    return TriangleRelationsObjectivePlan(
        prompt_key=str(prompt_key),
        problem=TriangleRelationsProblem(
            case=case,
            answer_support_probabilities=dict(answer_support_probabilities),
            prompt_target=str(case.trace_values.get("target_name", "target value")),
            annotation_mode=annotation_mode,
        ),
        render_scene=render_triangle_relations_scene,
        answer_value=case.answer,
        answer_type=str(case.answer_type),
        answer_rounding=str(case.answer_rounding),
        query_params=dict(combined_trace),
        trace_values=dict(combined_trace),
    )


def _render_attempts(
    *,
    plan: TriangleRelationsObjectivePlan,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
    render_defaults: Mapping[str, Any],
) -> TriangleRelationsRenderedAttempt:
    """Retry neutral rendering after a public task has resolved its case."""

    last_error: Exception | None = None
    for attempt_index in range(max(1, int(max_attempts))):
        attempt_seed = int(instance_seed) + int(attempt_index)
        try:
            context = create_render_context(
                instance_seed=attempt_seed,
                params={**dict(params), "_render_attempt": attempt_index},
                render_defaults=dict(render_defaults),
            )
            rendered = plan.render_scene(context, plan.problem)
            image, noise_meta = apply_post_image_noise(
                rendered.image,
                instance_seed=attempt_seed,
                params=params,
                default_config=POST_IMAGE_NOISE_DEFAULTS,
            )
            return TriangleRelationsRenderedAttempt(
                image=image,
                rendered=rendered,
                render_meta={
                    "technical_diagram": dict(context.diagram_style_meta),
                    "background": dict(context.background_meta),
                    "single_object_scene_rotation": context.scene_transform.metadata(),
                },
                noise_meta=dict(noise_meta),
                annotation_artifacts=triangle_relations_annotation(rendered),
            )
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError("failed to render triangle-relations scene") from last_error


def _trace_payload(
    *,
    task_identity: str,
    selected_branch: str,
    branch_probabilities: Mapping[str, float],
    prompt_artifacts: PromptTraceArtifacts,
    attempt: TriangleRelationsRenderedAttempt,
    plan: TriangleRelationsObjectivePlan,
) -> dict[str, Any]:
    """Build trace sections from task-owned formula and witness metadata."""

    rendered = attempt.rendered
    case = plan.problem.case
    query_params = {
        "scene_id": SCENE_ID,
        "query_id_probabilities": dict(branch_probabilities),
        **dict(plan.query_params),
    }
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_branch),
        params=query_params,
    )
    query_spec["task_id"] = str(task_identity)
    query_spec["scene_id"] = SCENE_ID
    execution_values = {
        "task_id": str(task_identity),
        "scene_id": SCENE_ID,
        "query_id": str(selected_branch),
        "answer": plan.answer_value,
        "answer_type": str(plan.answer_type),
        "answer_rounding": str(plan.answer_rounding),
        "annotation_type": str(attempt.annotation_artifacts.annotation_type),
        "annotation_roles": list(rendered.annotation_roles),
        **case_trace_values(case),
        **dict(plan.trace_values),
    }
    return {
        "scene_ir": {
            "domain": DOMAIN,
            "scene_kind": SCENE_KIND,
            "scene_id": SCENE_ID,
            "task_id": str(task_identity),
            "query_id": str(selected_branch),
            "entities": [dict(entity) for entity in rendered.scene_entities],
            "relations": {
                "formula_family": str(case.formula_family),
                "answer": plan.answer_value,
                "annotation_type": str(attempt.annotation_artifacts.annotation_type),
            },
        },
        "query_spec": query_spec,
        "render_spec": {
            "task_id": str(task_identity),
            "scene_id": SCENE_ID,
            "query_id": str(selected_branch),
            "canvas": {"width": int(attempt.image.size[0]), "height": int(attempt.image.size[1])},
            "style": {**dict(attempt.render_meta), "post_image_noise": dict(attempt.noise_meta)},
            "prompt": {
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            },
        },
        "render_map": {"coord_space": "pixel", **dict(rendered.render_map)},
        "execution_trace": execution_values,
        "witness_symbolic": {
            "task_id": str(task_identity),
            "scene_id": SCENE_ID,
            "query_id": str(selected_branch),
            "type": "triangle_relations_formula",
            "source_witness_type": str(attempt.annotation_artifacts.annotation_type),
            **execution_values,
        },
        "projected_annotation": dict(attempt.annotation_artifacts.projected_annotation),
    }


def run_triangle_relations_public_entry(
    task: Any,
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Run common plumbing after one public task binds its objective plan."""

    selected_branch, branch_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=tuple(str(value) for value in task.supported_query_ids),
        default_query_id=str(task.default_query_id),
        task_id=str(task.task_id),
        namespace=f"{task.task_id}.query",
    )
    _generation_defaults, render_defaults, prompt_defaults = load_triangle_relations_defaults(str(task.task_id))
    plan = task.prepare_objective(
        instance_seed=int(instance_seed),
        params=task_params,
        selected_branch=str(selected_branch),
        branch_probabilities=branch_probabilities,
    )
    attempt = _render_attempts(
        plan=plan,
        instance_seed=int(instance_seed),
        params=task_params,
        max_attempts=int(max_attempts),
        render_defaults=render_defaults,
    )
    prompt_artifacts = build_triangle_relations_prompt_artifacts(
        prompt_defaults=prompt_defaults,
        task_prompt_key=str(plan.prompt_key),
        prompt_branch_key=str(selected_branch),
        annotation_mode=str(plan.problem.annotation_mode),
        annotation_roles=tuple(attempt.rendered.annotation_roles),
        answer_value=plan.answer_value,
        instance_seed=int(instance_seed),
    )
    trace_payload = _trace_payload(
        task_identity=str(task.task_id),
        selected_branch=str(selected_branch),
        branch_probabilities=branch_probabilities,
        prompt_artifacts=prompt_artifacts,
        attempt=attempt,
        plan=plan,
    )
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=TypedValue(type=str(plan.answer_type), value=plan.answer_value),
        annotation_gt=TypedValue(
            type=str(attempt.annotation_artifacts.annotation_type),
            value=attempt.annotation_artifacts.value,
        ),
        image=attempt.image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(selected_branch),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


__all__ = ["TriangleRelationsObjectivePlan", "bind_triangle_relations_plan", "run_triangle_relations_public_entry"]
