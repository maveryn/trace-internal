"""Scene-private artifact assembly for right-triangle altitude theorem tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec

from .shared.annotations import point_map_for_roles
from .shared.defaults import DOMAIN, POST_IMAGE_NOISE_DEFAULTS, SCENE_ID, raw_scene_defaults
from .shared.prompts import right_triangle_altitude_prompt_artifacts
from .shared.rendering import create_render_context, render_right_triangle_altitude_scene
from .shared.state import RenderedRightTriangleAltitudeScene, RightTriangleAltitudeProblem


@dataclass(frozen=True)
class RightTriangleAltitudeObjectivePlan:
    """Task-owned objective binding prepared after branch selection."""

    prompt_task_key: str
    prompt_branch_key: str
    problem: RightTriangleAltitudeProblem
    answer_gt: TypedValue
    annotation_roles: tuple[str, ...]
    query_params: Mapping[str, Any]
    trace_values: Mapping[str, Any]


@dataclass(frozen=True)
class RightTriangleAltitudeArtifact:
    """Generated scene artifact before the public task wraps it as TaskOutput."""

    prompt_artifacts: PromptTraceArtifacts
    image: Any
    annotation_value: Mapping[str, Any]
    trace_payload: Mapping[str, Any]
    task_versions: Mapping[str, Any]
    rendered_scene: RenderedRightTriangleAltitudeScene


def scene_defaults_for_task(task_id: str) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    """Return split scene defaults for one public task id."""

    return split_scene_generation_rendering_prompt_defaults(raw_scene_defaults(), task_id=str(task_id))


def _measurement_payload(problem: RightTriangleAltitudeProblem) -> dict[str, Any]:
    values = problem.values
    return {
        "left_projection": int(values.left_projection),
        "right_projection": int(values.right_projection),
        "hypotenuse": int(values.hypotenuse),
        "altitude": int(values.altitude),
        "left_leg": values.left_leg,
        "right_leg": values.right_leg,
        "target_name": str(problem.target_name),
        "target_role": str(problem.target_role),
        "relation": str(problem.relation),
        "visible_labels": dict(problem.visible_labels),
    }


def _trace_payload(
    *,
    task_id: str,
    selected_branch: str,
    branch_probabilities: Mapping[str, float],
    prompt_artifacts: PromptTraceArtifacts,
    plan: RightTriangleAltitudeObjectivePlan,
    rendered: RenderedRightTriangleAltitudeScene,
    image_size: tuple[int, int],
    annotation_value: Mapping[str, Any],
    noise_meta: Mapping[str, Any],
    style_meta: Mapping[str, Any],
) -> dict[str, Any]:
    """Serialize trace metadata without choosing objective/query behavior."""

    measurements = _measurement_payload(plan.problem)
    query_params = {
        "scene_id": SCENE_ID,
        "query_id": str(selected_branch),
        "query_id_probabilities": dict(branch_probabilities),
        **dict(plan.query_params),
    }
    trace_values = {
        "answer": plan.answer_gt.value,
        "annotation_roles": list(plan.annotation_roles),
        **measurements,
        **dict(plan.trace_values),
    }
    return {
        "scene_ir": {
            "domain": DOMAIN,
            "scene_id": SCENE_ID,
            "task_id": str(task_id),
            "entities": [
                {
                    "type": "right_triangle_with_altitude_to_hypotenuse",
                    "points": dict(rendered.render_map["points"]),
                    "segments": {
                        "left_projection": "BD",
                        "right_projection": "DC",
                        "hypotenuse": "BC",
                        "altitude": "AD",
                        "left_leg": "AB",
                        "right_leg": "AC",
                    },
                }
            ],
            "relations": {
                "type": str(plan.problem.relation),
                "query_id": str(selected_branch),
                **dict(trace_values),
            },
        },
        "query_spec": build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_branch),
            params=query_params,
        ),
        "render_spec": {
            "task_id": str(task_id),
            "scene_id": SCENE_ID,
            "query_id": str(selected_branch),
            "canvas": {"width": int(image_size[0]), "height": int(image_size[1])},
            "coord_space": "pixel",
            "style": dict(style_meta),
            "prompt": {
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            },
        },
        "render_map": {"coord_space": "pixel", **dict(rendered.render_map)},
        "execution_trace": {
            "task_id": str(task_id),
            "scene_id": SCENE_ID,
            "query_id": str(selected_branch),
            "query_id_probabilities": dict(branch_probabilities),
            **dict(trace_values),
        },
        "witness_symbolic": {
            "task_id": str(task_id),
            "scene_id": SCENE_ID,
            "query_id": str(selected_branch),
            **dict(trace_values),
        },
        "projected_annotation": {
            "type": "point_map",
            "point_map": dict(annotation_value),
            "pixel_point_map": dict(annotation_value),
        },
    }


def build_right_triangle_altitude_artifact(
    *,
    task_id: str,
    instance_seed: int,
    selected_branch: str,
    branch_probabilities: Mapping[str, float],
    task_params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    plan: RightTriangleAltitudeObjectivePlan,
) -> RightTriangleAltitudeArtifact:
    """Build a rendered artifact from a task-owned objective plan."""

    ctx = create_render_context(
        instance_seed=int(instance_seed),
        params=dict(task_params),
        rendering_defaults=rendering_defaults,
    )
    rendered = render_right_triangle_altitude_scene(ctx, plan.problem)
    image, noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=task_params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    annotation_value = point_map_for_roles(rendered, tuple(plan.annotation_roles))
    _prompt_defaults, prompt_artifacts = right_triangle_altitude_prompt_artifacts(
        prompt_defaults=prompt_defaults,
        prompt_task_key=str(plan.prompt_task_key),
        prompt_branch_key=str(plan.prompt_branch_key),
        annotation_roles=tuple(plan.annotation_roles),
        target_name=str(plan.problem.target_name),
        answer=int(plan.answer_gt.value),
        instance_seed=int(instance_seed),
    )
    trace_payload = _trace_payload(
        task_id=str(task_id),
        selected_branch=str(selected_branch),
        branch_probabilities=branch_probabilities,
        prompt_artifacts=prompt_artifacts,
        plan=plan,
        rendered=rendered,
        image_size=image.size,
        annotation_value=annotation_value,
        noise_meta=noise_meta,
        style_meta={
            "technical_diagram": dict(ctx.diagram_style_meta),
            "background": dict(ctx.background_meta),
            "post_image_noise": dict(noise_meta),
            "single_object_scene_rotation": dict(ctx.scene_transform.metadata()),
        },
    )
    return RightTriangleAltitudeArtifact(
        prompt_artifacts=prompt_artifacts,
        image=image,
        annotation_value=dict(annotation_value),
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        rendered_scene=rendered,
    )


def run_right_triangle_altitude_public_entry(
    task: Any,
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Run neutral scene plumbing after the public task resolves objective semantics."""

    selected_branch, branch_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=dict(params),
        supported_query_ids=tuple(str(value) for value in task.supported_query_ids),
        default_query_id=str(task.default_query_id),
        task_id=str(task.task_id),
        namespace=f"{task.task_id}.query",
    )
    _generation_defaults, rendering_defaults, prompt_defaults = scene_defaults_for_task(str(task.task_id))
    last_error: Exception | None = None
    artifact = None
    plan = None
    for attempt_index in range(max(1, int(max_attempts))):
        attempt_seed = int(instance_seed) + int(attempt_index)
        try:
            plan = task.prepare_objective(attempt_seed, str(selected_branch), dict(branch_probabilities))
            artifact = build_right_triangle_altitude_artifact(
                task_id=str(task.task_id),
                instance_seed=attempt_seed,
                selected_branch=str(selected_branch),
                branch_probabilities=branch_probabilities,
                task_params={**dict(task_params), "_render_attempt": int(attempt_index)},
                rendering_defaults=rendering_defaults,
                prompt_defaults=prompt_defaults,
                plan=plan,
            )
            break
        except Exception as exc:
            last_error = exc
            continue
    if artifact is None or plan is None:
        raise RuntimeError(f"failed to generate {task.task_id}") from last_error
    return TaskOutput(
        prompt=str(artifact.prompt_artifacts.prompt),
        answer_gt=plan.answer_gt,
        annotation_gt=TypedValue(type="point_map", value=dict(artifact.annotation_value)),
        image=artifact.image,
        image_id="img0",
        trace_payload=dict(artifact.trace_payload),
        task_versions=dict(artifact.task_versions),
        scene_id=SCENE_ID,
        query_id=str(selected_branch),
        prompt_variants=dict(artifact.prompt_artifacts.prompt_variants),
    )


__all__ = [
    "RightTriangleAltitudeArtifact",
    "RightTriangleAltitudeObjectivePlan",
    "build_right_triangle_altitude_artifact",
    "run_right_triangle_altitude_public_entry",
    "scene_defaults_for_task",
]
