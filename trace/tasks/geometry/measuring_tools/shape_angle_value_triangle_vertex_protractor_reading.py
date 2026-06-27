"""Read a triangle vertex angle using a visible protractor."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task

from ._lifecycle import run_measuring_public_entry
from .shared.rendering import render_angle_measurement
from .shared.sampling import build_angle_measurement_plan
from .shared.state import AngleMeasurementPlan

TASK_ID = "task_geometry__measuring_tools__shape_angle_value_triangle_vertex_protractor_reading"
SUPPORTED_QUERY_IDS: tuple[str, ...] = ("single",)
MEASUREMENT_KIND = "triangle_vertex_protractor_reading"
PROMPT_TASK_KEY = "shape_angle_value_triangle_vertex_protractor_reading"
OBJECT_DESCRIPTION = "a triangle with a protractor placed at the marked vertex angle"
ANNOTATION_KEYS = ("angle_vertex", "protractor_reading_tick")


def _build_plan(instance_seed: int, params: Mapping[str, Any], gen_defaults: Mapping[str, Any]) -> AngleMeasurementPlan:
    """Bind triangle-angle semantics to the protractor support."""

    return build_angle_measurement_plan(
        params=params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        measurement_kind=MEASUREMENT_KIND,
        shape_kind="triangle",
        answer_namespace=f"{TASK_ID}.target_angle",
    )


@register_task
class GeometryMeasuringToolsShapeAngleValueTriangleVertexProtractorReadingTask:
    """Task-owned triangle-angle protractor reading objective."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    build_plan = staticmethod(_build_plan)
    render_measurement = staticmethod(render_angle_measurement)
    prompt_task_key = PROMPT_TASK_KEY
    object_description = OBJECT_DESCRIPTION
    annotation_keys = ANNOTATION_KEYS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int):
        return run_measuring_public_entry(self, int(instance_seed), params=params, max_attempts=max_attempts)


__all__ = ["GeometryMeasuringToolsShapeAngleValueTriangleVertexProtractorReadingTask"]
