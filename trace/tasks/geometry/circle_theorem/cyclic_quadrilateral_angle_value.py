"""Circle-theorem public objective task."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.core.scene_config import get_scene_defaults
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.circle.theorem_runtime import (
    SCENE_ID,
    CircleTheoremComponents,
    generate_circle_theorem_components,
)


_SCENE_DEFAULTS = get_scene_defaults("geometry", SCENE_ID)


def _stamp_task_identity(payload: Dict[str, Any], *, task_id: str) -> Dict[str, Any]:
    stamped = dict(payload)
    for key in ("scene_ir", "query_spec", "render_spec", "execution_trace", "witness_symbolic"):
        section = stamped.get(key)
        if isinstance(section, dict):
            section["task_id"] = str(task_id)
    return stamped


def _build_task_output(
    *,
    task_id: str,
    selected_query: str,
    components: CircleTheoremComponents,
) -> TaskOutput:
    trace_payload = _stamp_task_identity(dict(components.trace_payload), task_id=str(task_id))
    return TaskOutput(
        prompt=str(components.prompt),
        answer_gt=TypedValue(type="integer", value=int(components.answer_value)),
        annotation_gt=TypedValue(type="keyed_point_map", value=dict(components.annotation_keyed_points)),
        image=components.image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(selected_query),
        prompt_variants=dict(components.prompt_variants),
    )


TASK_ID = "task_geometry__circle_theorem__cyclic_quadrilateral_angle_value"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "opposite_angle_supplement",
    "exterior_angle_from_opposite_interior",
)


@register_task
class GeometryCircleCyclicQuadrilateralAngleValueTask:
    """Solve a cyclic quadrilateral angle."""

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
            default_query_id=SUPPORTED_QUERY_IDS[0],
            task_id=TASK_ID,
        )
        components = generate_circle_theorem_components(
            instance_seed=int(instance_seed),
            params=task_params,
            selected_query=str(selected_query),
            query_probabilities=query_probabilities,
            max_attempts=int(max_attempts),
            generation_namespace=f"{TASK_ID}.{selected_query}",
        )
        output = _build_task_output(
            task_id=TASK_ID,
            selected_query=str(selected_query),
            components=components,
        )
        if output.query_id != str(selected_query):
            raise RuntimeError(f"circle theorem query mismatch: {output.query_id} != {selected_query}")
        return output


__all__ = [
    "GeometryCircleCyclicQuadrilateralAngleValueTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
