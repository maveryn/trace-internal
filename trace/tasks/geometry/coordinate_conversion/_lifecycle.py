"""Private trace-section assembly for coordinate-conversion scene tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.output import projected_scalar_annotation, rendered_style_sections, segment_annotation_from_render
from .shared.prompts import coordinate_prompt_artifacts
from .shared.rendering import render_polar_point_scene
from .shared.sampling import format_number, select_polar_point_case


def coordinate_trace_payload(
    *,
    scene_id: str,
    query_id: str,
    scene_kind: str,
    scene_entities: Any,
    scene_relations: Mapping[str, Any],
    prompt_artifacts: Any,
    render_sections: Mapping[str, Any],
    query_params: Mapping[str, Any],
    execution_trace: Mapping[str, Any],
    witness_symbolic: Mapping[str, Any],
    projected_annotation: Mapping[str, Any],
) -> dict[str, Any]:
    """Compose query-bearing sidecar sections from task-owned semantic fields."""

    return {
        "scene_id": str(scene_id),
        "query_id": str(query_id),
        "scene_ir": {
            "scene_kind": str(scene_kind),
            "entities": list(scene_entities),
            "relations": {
                "scene_id": str(scene_id),
                "query_id": str(query_id),
                **dict(scene_relations),
            },
        },
        "query_spec": {
            "query_id": str(query_id),
            "template_id": "geometry_coordinate_conversion_v1",
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "scene_id": str(scene_id),
                "query_id": str(query_id),
                **dict(query_params),
            },
        },
        "render_spec": dict(render_sections["render_spec"]),
        "render_map": dict(render_sections["render_map"]),
        "execution_trace": {
            "scene_id": str(scene_id),
            "query_id": str(query_id),
            **dict(execution_trace),
        },
        "witness_symbolic": dict(witness_symbolic),
        "projected_annotation": dict(projected_annotation),
        "prompt": {
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
        },
    }


def run_cartesian_component_value(
    task: Any,
    instance_seed: int,
    *,
    params: dict[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Run the polar-to-Cartesian public objective through task-owned hooks."""

    _ = int(max_attempts)
    task_identifier = str(task.task_id)
    supported = tuple(str(value) for value in task.supported_query_ids)
    selected_branch, branch_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=supported,
        default_query_id=supported[0],
        task_id=task_identifier,
    )
    objective = dict(task.prepare_objective(str(selected_branch)))
    generation_defaults, rendering_defaults, prompt_defaults_all = load_scene_generation_rendering_prompt_defaults(
        "geometry",
        "coordinate_conversion",
        task_id=task_identifier,
    )
    case = select_polar_point_case(
        component=str(objective["component"]),
        instance_seed=int(instance_seed),
        params=task_params,
        generation_defaults=generation_defaults,
    )
    rendered = render_polar_point_scene(
        instance_seed=int(instance_seed),
        params=task_params,
        rendering_defaults=rendering_defaults,
        case=case,
    )
    annotation_value = segment_annotation_from_render(rendered.render_map)
    prompt_artifacts = coordinate_prompt_artifacts(
        prompt_defaults_all=prompt_defaults_all,
        prompt_query_key=str(selected_branch),
        annotation_value=annotation_value,
        object_description_key=str(objective["object_description_key"]),
        annotation_hint_key=str(objective["annotation_hint_key"]),
        context=f"prompt defaults for {task_identifier}",
        instance_seed=int(instance_seed),
        params=params,
    )
    render_sections = rendered_style_sections(rendered)
    payload = coordinate_trace_payload(
        scene_id="coordinate_conversion",
        query_id=str(selected_branch),
        scene_kind="coordinate_conversion_polar_point",
        scene_entities=rendered.scene_entities,
        scene_relations={
            "component": str(objective["component"]),
            "radius": int(case.radius),
            "theta_degrees": int(case.theta_degrees),
        },
        prompt_artifacts=prompt_artifacts,
        render_sections=render_sections,
        query_params={
            "query_id_probabilities": dict(branch_probabilities),
            "component": str(objective["component"]),
            "answer_support_count": int(case.answer_support_count),
        },
        execution_trace={
            "component": str(objective["component"]),
            "radius": int(case.radius),
            "theta_degrees": int(case.theta_degrees),
            "x_component": float(case.x_component),
            "y_component": float(case.y_component),
            "answer_value": float(case.selected_answer),
            "answer_display": format_number(case.selected_answer),
            "answer_candidate_probabilities": dict(case.answer_candidate_probabilities),
        },
        witness_symbolic={
            "type": "polar_ray_component",
            "point_label": "P",
            "origin_label": "O",
            "component": str(objective["component"]),
            "radius": int(case.radius),
            "theta_degrees": int(case.theta_degrees),
        },
        projected_annotation=projected_scalar_annotation(
            annotation_type="segment",
            annotation_value=annotation_value,
        ),
    )
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=TypedValue(type="number", value=float(case.selected_answer)),
        annotation_gt=TypedValue(type="segment", value=annotation_value),
        image=rendered.image,
        image_id=f"{task_identifier}:{int(instance_seed)}",
        trace_payload=payload,
        task_versions=default_task_versions(),
        scene_id="coordinate_conversion",
        query_id=str(selected_branch),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


__all__ = ["coordinate_trace_payload", "run_cartesian_component_value"]
