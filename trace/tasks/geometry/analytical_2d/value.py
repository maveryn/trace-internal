"""Consolidated analytical 2D geometry task with scene/query variants."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import split_generation_rendering_prompt_defaults
from ..shared.consolidated_legacy import (
    normalize_legacy_geometry_output,
    strip_consolidated_params,
    unregister_legacy_tasks,
)
from ..shared.consolidated_sampling import resolve_compatible_scene_query_variants
from .area import GeometryAnalyticalArea2DTask
from .composite_area import GeometryAnalyticalCompositeArea2DTask
from .length import GeometryAnalyticalLength2DTask
from .perimeter import GeometryAnalyticalPerimeter2DTask

LEGACY_TASK_IDS: Tuple[str, ...] = (
    "task_geometry_analytical_2d_area",
    "task_geometry_analytical_2d_composite_area",
    "task_geometry_analytical_2d_length",
    "task_geometry_analytical_2d_perimeter",
)
unregister_legacy_tasks(LEGACY_TASK_IDS)

TASK_ID = "task_geometry_analytical_2d_value"
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "rectangle",
    "triangle",
    "parallelogram",
    "trapezoid",
    "rhombus",
    "circle",
    "ellipse",
    "composite_region",
)
_SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = ("area", "length", "perimeter", "composite_area")
_COMPATIBILITY: Dict[str, Sequence[str]] = {
    "rectangle": ("area", "length", "perimeter"),
    "triangle": ("area", "length", "perimeter"),
    "parallelogram": ("area",),
    "trapezoid": ("area", "length", "perimeter"),
    "rhombus": ("area", "length", "perimeter"),
    "circle": ("area", "length", "perimeter"),
    "ellipse": ("area",),
    "composite_region": ("composite_area",),
}
_AREA_BUILDERS: Dict[str, Tuple[object, Dict[str, Any]]] = {
    "rectangle": (GeometryAnalyticalArea2DTask, {"shape_variant": "rectangle"}),
    "triangle": (GeometryAnalyticalArea2DTask, {"shape_variant": "triangle"}),
    "parallelogram": (GeometryAnalyticalArea2DTask, {"shape_variant": "parallelogram"}),
    "trapezoid": (GeometryAnalyticalArea2DTask, {"shape_variant": "trapezoid"}),
    "rhombus": (GeometryAnalyticalArea2DTask, {"shape_variant": "rhombus"}),
    "circle": (GeometryAnalyticalArea2DTask, {"shape_variant": "circle"}),
    "ellipse": (GeometryAnalyticalArea2DTask, {"shape_variant": "ellipse"}),
}
_LENGTH_BUILDERS: Dict[str, Sequence[Tuple[object, Dict[str, Any]]]] = {
    "triangle": ((GeometryAnalyticalLength2DTask, {"task_variant": "triangle_altitude_side"}),),
    "rectangle": ((GeometryAnalyticalLength2DTask, {"task_variant": "rectangle_diagonal_side"}),),
    "rhombus": ((GeometryAnalyticalLength2DTask, {"task_variant": "rhombus_diagonal_side"}),),
    "trapezoid": ((GeometryAnalyticalLength2DTask, {"task_variant": "isosceles_trapezoid_leg"}),),
    "circle": (
        (GeometryAnalyticalLength2DTask, {"task_variant": "inscribed_square_side"}),
        (GeometryAnalyticalLength2DTask, {"task_variant": "circle_chord_length"}),
    ),
}
_PERIMETER_BUILDERS: Dict[str, Tuple[object, Dict[str, Any]]] = {
    "triangle": (GeometryAnalyticalPerimeter2DTask, {"task_variant": "right_triangle_leg_hypotenuse"}),
    "rectangle": (GeometryAnalyticalPerimeter2DTask, {"task_variant": "rectangle_side_diagonal"}),
    "rhombus": (GeometryAnalyticalPerimeter2DTask, {"task_variant": "rhombus_diagonals"}),
    "trapezoid": (GeometryAnalyticalPerimeter2DTask, {"task_variant": "isosceles_trapezoid_bases_height"}),
    "circle": (GeometryAnalyticalPerimeter2DTask, {"task_variant": "inscribed_square_diameter"}),
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "analytical_2d")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _resolve_legacy_builder(scene_variant: str, query_variant: str, *, instance_seed: int):
    """Resolve the legacy analytical 2D generator for one consolidated pair."""

    if str(query_variant) == "area":
        return _AREA_BUILDERS[str(scene_variant)]
    if str(query_variant) == "perimeter":
        return _PERIMETER_BUILDERS[str(scene_variant)]
    if str(query_variant) == "composite_area":
        return GeometryAnalyticalCompositeArea2DTask, {}
    if str(query_variant) == "length":
        options = list(_LENGTH_BUILDERS[str(scene_variant)])
        if len(options) == 1:
            return options[0]
        rng = spawn_rng(instance_seed, f"{TASK_ID}.{scene_variant}.{query_variant}.legacy_variant")
        return options[int(rng.randrange(len(options)))]
    raise ValueError(f"unsupported analytical 2d pair: {scene_variant} + {query_variant}")


@register_task
class GeometryAnalytical2DValueTask:
    """Unified analytical 2D geometry task spanning multiple shape scenes."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = "analytical_2d"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        rng = spawn_rng(instance_seed, f"{self.task_id}.axes")
        scene_variant, scene_probs, query_variant, query_probs = resolve_compatible_scene_query_variants(
            rng,
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            supported_scene_variants=_SUPPORTED_SCENE_VARIANTS,
            supported_query_variants=_SUPPORTED_QUERY_VARIANTS,
            compatibility=_COMPATIBILITY,
            scene_sampling_namespace=f"{self.task_id}.scene_variant",
            query_sampling_namespace=f"{self.task_id}.query_variant",
        )
        legacy_task_cls, legacy_overrides = _resolve_legacy_builder(
            str(scene_variant),
            str(query_variant),
            instance_seed=int(instance_seed),
        )
        legacy_task = legacy_task_cls()
        legacy_params = strip_consolidated_params(params)
        legacy_params.update(dict(legacy_overrides))
        output = legacy_task.generate(int(instance_seed), params=legacy_params, max_attempts=int(max_attempts))
        legacy_trace = dict(output.trace_payload.get("execution_trace") or {})
        return normalize_legacy_geometry_output(
            output,
            scene_variant=str(scene_variant),
            query_variant=str(query_variant),
            legacy_task_id=str(legacy_task.task_id),
            scene_variant_probabilities=scene_probs,
            query_variant_probabilities=query_probs,
            legacy_scene_variant=str(legacy_trace.get("shape_variant", scene_variant)),
            legacy_query_variant=str(output.task_variant),
        )
