"""Consolidated geometry comparison task with shape-family scene variants."""

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
from .angle import GeometryComparisonAngleTask
from .area import GeometryComparisonAreaTask
from .length import GeometryComparisonLengthTask
from .perimeter import GeometryComparisonPerimeterTask

LEGACY_TASK_IDS: Tuple[str, ...] = (
    "task_geometry_comparison_angle",
    "task_geometry_comparison_area",
    "task_geometry_comparison_length",
    "task_geometry_comparison_perimeter",
)
unregister_legacy_tasks(LEGACY_TASK_IDS)

TASK_ID = "task_geometry_comparison_value"
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("angle", "segment", "rectangle")
_SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "largest_angle",
    "smallest_angle",
    "largest_length",
    "smallest_length",
    "largest_area",
    "smallest_area",
    "largest_perimeter",
    "smallest_perimeter",
)
_COMPATIBILITY: Dict[str, Sequence[str]] = {
    "angle": ("largest_angle", "smallest_angle"),
    "segment": ("largest_length", "smallest_length"),
    "rectangle": ("largest_area", "smallest_area", "largest_perimeter", "smallest_perimeter"),
}
_LEGACY_BUILDERS: Dict[Tuple[str, str], Tuple[object, Dict[str, Any]]] = {
    ("angle", "largest_angle"): (GeometryComparisonAngleTask, {"query_type": "largest"}),
    ("angle", "smallest_angle"): (GeometryComparisonAngleTask, {"query_type": "smallest"}),
    ("segment", "largest_length"): (GeometryComparisonLengthTask, {"query_type": "largest"}),
    ("segment", "smallest_length"): (GeometryComparisonLengthTask, {"query_type": "smallest"}),
    ("rectangle", "largest_area"): (GeometryComparisonAreaTask, {"query_type": "largest"}),
    ("rectangle", "smallest_area"): (GeometryComparisonAreaTask, {"query_type": "smallest"}),
    ("rectangle", "largest_perimeter"): (GeometryComparisonPerimeterTask, {"query_type": "largest"}),
    ("rectangle", "smallest_perimeter"): (GeometryComparisonPerimeterTask, {"query_type": "smallest"}),
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "comparison")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


@register_task
class GeometryComparisonValueTask:
    """Unified geometry comparison task spanning angle, segment, and region scenes."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = "comparison"

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
            legacy_scene_variant=str(legacy_trace.get("scene_variant", scene_variant)),
            legacy_query_variant=str(output.task_variant),
        )
