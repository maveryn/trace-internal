"""Read a circle radius using a visible ruler."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task

from ._lifecycle import run_measuring_public_entry
from .shared.rendering import render_length_measurement
from .shared.sampling import build_ruler_length_plan
from .shared.state import LengthMeasurementPlan

TASK_ID = "task_geometry__measuring_tools__shape_length_value_circle_radius_ruler_reading"
SUPPORTED_QUERY_IDS: tuple[str, ...] = ("single",)
MEASUREMENT_KIND = "circle_radius_ruler_reading"
PROMPT_TASK_KEY = "shape_length_value_circle_radius_ruler_reading"
OBJECT_DESCRIPTION = "a circle with a ruler placed alongside the marked radius"
ANNOTATION_KEYS = ("measure_start", "measure_end", "ruler_start_tick", "ruler_end_tick")


def _build_plan(instance_seed: int, params: Mapping[str, Any], gen_defaults: Mapping[str, Any]) -> LengthMeasurementPlan:
    """Bind circle-radius semantics to a ruler readout."""

    return build_ruler_length_plan(
        params=params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        measurement_kind=MEASUREMENT_KIND,
        shape_kind="circle",
        answer_namespace=f"{TASK_ID}.target_radius",
        offset_namespace=f"{TASK_ID}.ruler_start_cm",
    )


@register_task
class GeometryMeasuringToolsShapeLengthValueCircleRadiusRulerReadingTask:
    """Task-owned circle-radius ruler reading objective."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    build_plan = staticmethod(_build_plan)
    render_measurement = staticmethod(render_length_measurement)
    prompt_task_key = PROMPT_TASK_KEY
    object_description = OBJECT_DESCRIPTION
    annotation_keys = ANNOTATION_KEYS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int):
        return run_measuring_public_entry(self, int(instance_seed), params=params, max_attempts=max_attempts)


__all__ = ["GeometryMeasuringToolsShapeLengthValueCircleRadiusRulerReadingTask"]
