"""Compute a polar component from a plotted Cartesian point."""

from __future__ import annotations

from typing import Any

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from ._lifecycle import coordinate_trace_payload
from .shared.output import point_annotation_from_render, projected_scalar_annotation, rendered_style_sections
from .shared.prompts import coordinate_prompt_artifacts
from .shared.rendering import render_cartesian_point_scene
from .shared.sampling import format_number, select_cartesian_point_case

TASK_ID = "task_geometry__coordinate_conversion__polar_component_value"
SCENE_ID = "coordinate_conversion"
QUERY_IDS = ("radius_from_cartesian_point", "angle_from_cartesian_point")
QUERY_COMPONENTS = {
    "radius_from_cartesian_point": "radius",
    "angle_from_cartesian_point": "angle",
}
PROMPT_QUERY_KEYS = {
    "radius_from_cartesian_point": "radius_from_cartesian_point",
    "angle_from_cartesian_point": "angle_from_cartesian_point",
}


def _polar_trace_payload(
    *,
    query_id: str,
    query_probabilities: dict[str, float],
    component: str,
    case: Any,
    rendered: Any,
    annotation_value: Any,
    prompt_artifacts: Any,
) -> dict[str, Any]:
    """Bind Cartesian-point formula fields into the shared trace sections."""

    style_sections = rendered_style_sections(rendered)
    return coordinate_trace_payload(
        scene_id=SCENE_ID,
        query_id=str(query_id),
        scene_kind="coordinate_conversion_cartesian_point",
        scene_entities=rendered.scene_entities,
        scene_relations={
            "component": str(component),
            "point_p_graph": [int(case.x), int(case.y)],
        },
        prompt_artifacts=prompt_artifacts,
        render_sections=style_sections,
        query_params={
            "query_id_probabilities": dict(query_probabilities),
            "component": str(component),
            "answer_support_count": int(case.answer_support_count),
        },
        execution_trace={
            "component": str(component),
            "x": int(case.x),
            "y": int(case.y),
            "radius": float(case.radius),
            "angle_degrees": float(case.angle_degrees),
            "answer_value": float(case.selected_answer),
            "answer_display": format_number(case.selected_answer),
            "answer_candidate_probabilities": dict(case.answer_candidate_probabilities),
        },
        witness_symbolic={
            "type": "coordinate_point_component",
            "point_label": "P",
            "point_graph": [int(case.x), int(case.y)],
            "component": str(component),
        },
        projected_annotation=projected_scalar_annotation(
            annotation_type="point",
            annotation_value=annotation_value,
        ),
    )


@register_task
class GeometryCoordinateConversionPolarComponentValueTask:
    """Answer a polar component for a plotted Cartesian point."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one Cartesian-to-polar coordinate conversion instance."""

        _ = int(max_attempts)
        query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=QUERY_IDS,
            default_query_id=QUERY_IDS[0],
            task_id=TASK_ID,
        )
        component = str(QUERY_COMPONENTS[str(query_id)])
        generation_defaults, rendering_defaults, prompt_defaults_all = load_scene_generation_rendering_prompt_defaults(
            "geometry",
            SCENE_ID,
            task_id=TASK_ID,
        )
        case = select_cartesian_point_case(
            component=component,
            instance_seed=int(instance_seed),
            params=task_params,
            generation_defaults=generation_defaults,
        )
        rendered = render_cartesian_point_scene(
            instance_seed=int(instance_seed),
            params=task_params,
            rendering_defaults=rendering_defaults,
            case=case,
        )
        annotation_value = point_annotation_from_render(rendered.render_map)
        prompt_artifacts = coordinate_prompt_artifacts(
            prompt_defaults_all=prompt_defaults_all,
            prompt_query_key=PROMPT_QUERY_KEYS[str(query_id)],
            annotation_value=annotation_value,
            object_description_key="object_description_cartesian_point",
            annotation_hint_key="annotation_hint_point_p",
            context=f"prompt defaults for {TASK_ID}",
            instance_seed=int(instance_seed),
            params=params,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="number", value=float(case.selected_answer)),
            annotation_gt=TypedValue(type="point", value=annotation_value),
            image=rendered.image,
            image_id=f"{TASK_ID}:{int(instance_seed)}",
            trace_payload=_polar_trace_payload(
                query_id=str(query_id),
                query_probabilities=query_probabilities,
                component=component,
                case=case,
                rendered=rendered,
                annotation_value=annotation_value,
                prompt_artifacts=prompt_artifacts,
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "GeometryCoordinateConversionPolarComponentValueTask",
    "QUERY_IDS",
    "SCENE_ID",
    "TASK_ID",
]
