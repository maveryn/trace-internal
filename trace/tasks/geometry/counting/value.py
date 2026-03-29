"""Consolidated geometry counting task with scene/query variant axes."""

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
from .angle import GeometryCountingAngleTask
from .convexity import GeometryCountingConvexityTask
from .quadrilateral import GeometryCountingQuadrilateralTask
from .shape_type import GeometryCountingShapeTypeTask
from .triangle import GeometryCountingTriangleTask

LEGACY_TASK_IDS: Tuple[str, ...] = (
    "task_geometry_counting_angle",
    "task_geometry_counting_convexity",
    "task_geometry_counting_quadrilateral",
    "task_geometry_counting_shape_type",
    "task_geometry_counting_triangle",
)
unregister_legacy_tasks(LEGACY_TASK_IDS)

TASK_ID = "task_geometry_counting_value"
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "angle",
    "triangle",
    "quadrilateral",
    "mixed_shape",
    "polygon",
)
_SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "acute_angle",
    "right_angle",
    "obtuse_angle",
    "equilateral_triangle",
    "isosceles_triangle",
    "scalene_triangle",
    "right_triangle",
    "acute_triangle",
    "obtuse_triangle",
    "square",
    "rectangle_non_square",
    "rhombus_non_square",
    "parallelogram_only",
    "triangle",
    "quadrilateral",
    "pentagon",
    "hexagon",
    "circle",
    "ellipse",
    "convex_polygon",
    "concave_polygon",
)
_COMPATIBILITY: Dict[str, Sequence[str]] = {
    "angle": ("acute_angle", "right_angle", "obtuse_angle"),
    "triangle": (
        "equilateral_triangle",
        "isosceles_triangle",
        "scalene_triangle",
        "right_triangle",
        "acute_triangle",
        "obtuse_triangle",
    ),
    "quadrilateral": ("square", "rectangle_non_square", "rhombus_non_square", "parallelogram_only"),
    "mixed_shape": ("triangle", "quadrilateral", "pentagon", "hexagon", "circle", "ellipse"),
    "polygon": ("convex_polygon", "concave_polygon"),
}
_LEGACY_BUILDERS: Dict[Tuple[str, str], Tuple[object, Dict[str, Any]]] = {
    ("angle", "acute_angle"): (GeometryCountingAngleTask, {"task_variant": "acute_angle"}),
    ("angle", "right_angle"): (GeometryCountingAngleTask, {"task_variant": "right_angle"}),
    ("angle", "obtuse_angle"): (GeometryCountingAngleTask, {"task_variant": "obtuse_angle"}),
    ("triangle", "equilateral_triangle"): (GeometryCountingTriangleTask, {"task_variant": "equilateral_triangle"}),
    ("triangle", "isosceles_triangle"): (GeometryCountingTriangleTask, {"task_variant": "isosceles_triangle"}),
    ("triangle", "scalene_triangle"): (GeometryCountingTriangleTask, {"task_variant": "scalene_triangle"}),
    ("triangle", "right_triangle"): (GeometryCountingTriangleTask, {"task_variant": "right_triangle"}),
    ("triangle", "acute_triangle"): (GeometryCountingTriangleTask, {"task_variant": "acute_triangle"}),
    ("triangle", "obtuse_triangle"): (GeometryCountingTriangleTask, {"task_variant": "obtuse_triangle"}),
    ("quadrilateral", "square"): (GeometryCountingQuadrilateralTask, {"task_variant": "square"}),
    ("quadrilateral", "rectangle_non_square"): (
        GeometryCountingQuadrilateralTask,
        {"task_variant": "rectangle_non_square"},
    ),
    ("quadrilateral", "rhombus_non_square"): (GeometryCountingQuadrilateralTask, {"task_variant": "rhombus_non_square"}),
    ("quadrilateral", "parallelogram_only"): (GeometryCountingQuadrilateralTask, {"task_variant": "parallelogram_only"}),
    ("mixed_shape", "triangle"): (GeometryCountingShapeTypeTask, {"task_variant": "triangle"}),
    ("mixed_shape", "quadrilateral"): (GeometryCountingShapeTypeTask, {"task_variant": "quadrilateral"}),
    ("mixed_shape", "pentagon"): (GeometryCountingShapeTypeTask, {"task_variant": "pentagon"}),
    ("mixed_shape", "hexagon"): (GeometryCountingShapeTypeTask, {"task_variant": "hexagon"}),
    ("mixed_shape", "circle"): (GeometryCountingShapeTypeTask, {"task_variant": "circle"}),
    ("mixed_shape", "ellipse"): (GeometryCountingShapeTypeTask, {"task_variant": "ellipse"}),
    ("polygon", "convex_polygon"): (GeometryCountingConvexityTask, {"task_variant": "convex_polygon"}),
    ("polygon", "concave_polygon"): (GeometryCountingConvexityTask, {"task_variant": "concave_polygon"}),
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


@register_task
class GeometryCountingValueTask:
    """Unified geometry counting task spanning angle, polygon, and mixed-shape scenes."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = "counting"

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
