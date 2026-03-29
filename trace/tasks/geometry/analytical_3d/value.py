"""Consolidated analytical 3D geometry task with solid-based scene variants."""

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
from .surface_area import GeometryAnalyticalSurfaceArea3DTask
from .volume import GeometryAnalyticalVolume3DTask

LEGACY_TASK_IDS: Tuple[str, ...] = (
    "task_geometry_analytical_3d_surface_area",
    "task_geometry_analytical_3d_volume",
)
unregister_legacy_tasks(LEGACY_TASK_IDS)

TASK_ID = "task_geometry_analytical_3d_value"
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "rectangular_prism",
    "triangular_prism",
    "square_pyramid",
    "cylinder",
    "cone",
    "sphere",
)
_SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = ("volume", "surface_area")
_COMPATIBILITY: Dict[str, Sequence[str]] = {
    "rectangular_prism": ("volume", "surface_area"),
    "triangular_prism": ("volume", "surface_area"),
    "square_pyramid": ("volume", "surface_area"),
    "cylinder": ("volume", "surface_area"),
    "cone": ("volume", "surface_area"),
    "sphere": ("volume", "surface_area"),
}
_LEGACY_BUILDERS: Dict[Tuple[str, str], Tuple[object, Dict[str, Any]]] = {
    ("rectangular_prism", "volume"): (GeometryAnalyticalVolume3DTask, {"task_variant": "rectangular_prism_given_lwh"}),
    ("triangular_prism", "volume"): (GeometryAnalyticalVolume3DTask, {"task_variant": "triangular_prism_given_b_h_l"}),
    ("square_pyramid", "volume"): (GeometryAnalyticalVolume3DTask, {"task_variant": "square_pyramid_given_base_height"}),
    ("cylinder", "volume"): (GeometryAnalyticalVolume3DTask, {"task_variant": "cylinder_given_r_h"}),
    ("cone", "volume"): (GeometryAnalyticalVolume3DTask, {"task_variant": "cone_given_r_h"}),
    ("sphere", "volume"): (GeometryAnalyticalVolume3DTask, {"task_variant": "sphere_given_r"}),
    ("rectangular_prism", "surface_area"): (GeometryAnalyticalSurfaceArea3DTask, {"task_variant": "rectangular_prism_given_lwh"}),
    ("triangular_prism", "surface_area"): (GeometryAnalyticalSurfaceArea3DTask, {"task_variant": "triangular_prism_given_a_b_c_l"}),
    ("square_pyramid", "surface_area"): (
        GeometryAnalyticalSurfaceArea3DTask,
        {"task_variant": "square_pyramid_given_base_side_slant_height"},
    ),
    ("cylinder", "surface_area"): (GeometryAnalyticalSurfaceArea3DTask, {"task_variant": "cylinder_given_r_h"}),
    ("cone", "surface_area"): (GeometryAnalyticalSurfaceArea3DTask, {"task_variant": "cone_given_r_slant_height"}),
    ("sphere", "surface_area"): (GeometryAnalyticalSurfaceArea3DTask, {"task_variant": "sphere_given_r"}),
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "analytical_3d")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


@register_task
class GeometryAnalytical3DValueTask:
    """Unified analytical 3D geometry task spanning solid scene variants."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = "analytical_3d"

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
        legacy_task_cls, legacy_overrides = _LEGACY_BUILDERS[(str(scene_variant), str(query_variant))]
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
            legacy_scene_variant=str(legacy_trace.get("task_variant", scene_variant)),
            legacy_query_variant=str(output.task_variant),
        )
