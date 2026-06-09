"""Consolidated geometry measurement task with shape-based scene variants."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import split_generation_rendering_prompt_defaults
from ..shared.consolidated_source import (
    normalize_source_geometry_output,
    strip_consolidated_params,
    unregister_source_tasks,
)
from ..shared.consolidated_sampling import resolve_compatible_scene_query_ids
from ..shared.fixed_query_task import FixedGeometryQueryTaskMixin
from .angle import GeometryAngleMeasure2DTask
from .area import GeometryAreaMeasure2DTask
from .perimeter import GeometryPerimeterMeasure2DTask
from .slope import GeometrySlopeMeasureTask

SOURCE_TASK_IDS: Tuple[str, ...] = (
    "source_geometry_measurement_angle",
    "source_geometry_measurement_area",
    "source_geometry_measurement_length",
    "source_geometry_measurement_perimeter",
    "source_geometry_measurement_slope",
)
unregister_source_tasks(SOURCE_TASK_IDS)

TASK_ID = "geometry_measurement_value_base"
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "angle",
    "triangle",
    "quadrilateral",
    "circle",
    "ellipse",
    "line",
)
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "angle",
    "area",
    "perimeter",
    "slope",
)
_COMPATIBILITY: Dict[str, Sequence[str]] = {
    "angle": ("angle",),
    "triangle": ("area", "perimeter"),
    "quadrilateral": ("area", "perimeter"),
    "circle": ("perimeter",),
    "ellipse": ("area",),
    "line": ("slope",),
}
_SOURCE_BUILDERS: Dict[Tuple[str, str], Tuple[object, Dict[str, Any]]] = {
    ("angle", "angle"): (GeometryAngleMeasure2DTask, {}),
    ("triangle", "area"): (GeometryAreaMeasure2DTask, {"shape_variant": "triangle"}),
    ("quadrilateral", "area"): (GeometryAreaMeasure2DTask, {"shape_variant": "quadrilateral"}),
    ("ellipse", "area"): (GeometryAreaMeasure2DTask, {"shape_variant": "ellipse"}),
    ("triangle", "perimeter"): (GeometryPerimeterMeasure2DTask, {"shape_variant": "triangle"}),
    ("quadrilateral", "perimeter"): (GeometryPerimeterMeasure2DTask, {"shape_variant": "quadrilateral"}),
    ("circle", "perimeter"): (GeometryPerimeterMeasure2DTask, {"shape_variant": "circle"}),
    ("line", "slope"): (GeometrySlopeMeasureTask, {}),
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "measurement")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_SOURCE_SAMPLING_SALT = 440


def _source_sampling_params(
    params: Mapping[str, Any],
    *,
    scene_variant: str,
    query_id: str,
) -> Dict[str, Any]:
    """Return source params for the shared renderer."""

    source_params = strip_consolidated_params(params)
    _ = scene_variant, query_id
    return source_params


class GeometryMeasurementValueTask:
    """Unified geometry measurement task spanning shape scenes and query types."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = "measurement"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        rng = spawn_rng(instance_seed, f"{self.task_id}.axes")
        scene_variant, scene_probs, query_id, query_probs = resolve_compatible_scene_query_ids(
            rng,
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            supported_scene_variants=_SUPPORTED_SCENE_VARIANTS,
            supported_query_ids=_SUPPORTED_QUERY_IDS,
            compatibility=_COMPATIBILITY,
            scene_sampling_namespace=f"{self.task_id}.scene_variant",
            query_sampling_namespace=f"{self.task_id}.query_id",
        )
        source_task_cls, source_overrides = _SOURCE_BUILDERS[(str(scene_variant), str(query_id))]
        source_task = source_task_cls()
        source_params = _source_sampling_params(
            params,
            scene_variant=str(scene_variant),
            query_id=str(query_id),
        )
        source_params.update(dict(source_overrides))
        output = source_task.generate(int(instance_seed), params=source_params, max_attempts=int(max_attempts))
        source_trace = dict(output.trace_payload.get("execution_trace") or {})
        return normalize_source_geometry_output(
            output,
            scene_variant=str(scene_variant),
            query_id=str(query_id),
            source_task_id=str(source_task.task_id),
            scene_variant_probabilities=scene_probs,
            query_id_probabilities=query_probs,
            source_scene_variant=str(source_trace.get("scene_variant", scene_variant)),
            source_query_id=str(output.query_id),
        )


@register_task
class GeometryMeasurementAngleValueTask(FixedGeometryQueryTaskMixin, GeometryMeasurementValueTask):
    """Public geometry angle-measurement task."""

    task_id = "task_geometry__graph_paper__angle_value"
    fixed_query_id = "angle"
    scene_id = "graph_paper"
    public_scene_id = "graph_paper"
    allowed_scene_variants = ("angle",)


@register_task
class GeometryMeasurementPolygonAreaValueTask(FixedGeometryQueryTaskMixin, GeometryMeasurementValueTask):
    """Public polygon-area measurement task."""

    task_id = "task_geometry__graph_paper__polygon_area_value"
    fixed_query_id = "area"
    scene_id = "graph_paper"
    public_scene_id = "graph_paper"
    allowed_scene_variants = ("triangle", "quadrilateral")


@register_task
class GeometryMeasurementEllipseAreaValueTask(FixedGeometryQueryTaskMixin, GeometryMeasurementValueTask):
    """Public ellipse-area measurement task."""

    task_id = "task_geometry__graph_paper__ellipse_area_value"
    fixed_query_id = "area"
    scene_id = "graph_paper"
    public_scene_id = "graph_paper"
    allowed_scene_variants = ("ellipse",)


@register_task
class GeometryMeasurementPolygonPerimeterValueTask(FixedGeometryQueryTaskMixin, GeometryMeasurementValueTask):
    """Public polygon-perimeter measurement task."""

    task_id = "task_geometry__graph_paper__polygon_perimeter_value"
    fixed_query_id = "perimeter"
    scene_id = "graph_paper"
    public_scene_id = "graph_paper"
    allowed_scene_variants = ("triangle", "quadrilateral")


@register_task
class GeometryMeasurementCircleCircumferenceValueTask(FixedGeometryQueryTaskMixin, GeometryMeasurementValueTask):
    """Public circle-circumference measurement task."""

    task_id = "task_geometry__graph_paper__circle_circumference_value"
    fixed_query_id = "perimeter"
    scene_id = "graph_paper"
    public_scene_id = "graph_paper"
    allowed_scene_variants = ("circle",)


@register_task
class GeometryMeasurementLineSlopeValueTask(FixedGeometryQueryTaskMixin, GeometryMeasurementValueTask):
    """Public line-slope measurement task."""

    task_id = "task_geometry__graph_paper__line_slope_value"
    fixed_query_id = "slope"
    scene_id = "graph_paper"
    public_scene_id = "graph_paper"
    allowed_scene_variants = ("line",)
