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


_ALL_QUERY_IDS: Tuple[str, ...] = (
    "diameter_perpendicular_chord_length",
    "secant_secant_variable_segment_length",
    "tangent_secant_length",
    "secant_secant_length",
    "intersecting_chords_arc_measure",
    "multi_step_angle_value",
    "inscribed_angle_from_central",
    "central_angle_from_inscribed",
    "inscribed_angle_from_arc",
    "tangent_chord_angle_from_arc",
    "tangent_chord_angle_from_inscribed",
    "external_two_secants_angle_from_arcs",
    "opposite_angle_supplement",
    "exterior_angle_from_opposite_interior",
)


class GeometryCircleTheoremValueTask:
    """Legacy unregistered facade used by circle-theorem regression tests."""

    task_id = "geometry_circle_theorem_value_base"
    domain = "geometry"
    scene_id = SCENE_ID
    default_dataset_enabled = False
    supported_query_ids = _ALL_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=_ALL_QUERY_IDS,
            default_query_id="diameter_perpendicular_chord_length",
            task_id=str(self.task_id),
        )
        components = generate_circle_theorem_components(
            instance_seed=int(instance_seed),
            params=task_params,
            selected_query=str(selected_query),
            query_probabilities=query_probabilities,
            max_attempts=int(max_attempts),
            generation_namespace=str(self.task_id),
        )
        output = _build_task_output(
            task_id=str(self.task_id),
            selected_query=str(selected_query),
            components=components,
        )
        if output.query_id != str(selected_query):
            raise RuntimeError(f"circle theorem query mismatch: {output.query_id} != {selected_query}")
        return output


TASK_ID = "task_geometry__circle_theorem__diameter_perpendicular_chord_length_value"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("diameter_perpendicular_chord_length",)


@register_task
class GeometryCircleDiameterPerpendicularChordLengthValueTask:
    """Solve a length in a diameter-perpendicular-chord diagram."""

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
    "GeometryCircleTheoremValueTask",
    "GeometryCircleDiameterPerpendicularChordLengthValueTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
