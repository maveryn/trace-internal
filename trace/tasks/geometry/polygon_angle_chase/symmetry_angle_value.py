"""Infer an angle from symmetry and equal-side relations."""

from __future__ import annotations

from typing import Any

from trace.tasks.registry import register_task

from ._lifecycle import run_angle_chase_entry
from .shared.defaults import DOMAIN
from .shared.output import symmetry_render_map, symmetry_trace_common
from .shared.rendering import (
    render_isosceles_angle_scene,
    render_rectangle_diagonal_scene,
    render_reflection_axis_scene,
)
from .shared.sampling import (
    build_isosceles_plan,
    build_rectangle_diagonal_plan,
    build_reflection_axis_plan,
    select_internal_option,
)
from .shared.state import RenderContext, RenderedSymmetryAngleScene, SymmetryAnglePlan

TASK_ID = "task_geometry__polygon_angle_chase__symmetry_angle_value"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (
    "rectangle_diagonal_angle",
    "reflection_axis_angle",
    "isosceles_base_angle_chain",
)
_ISOSCELES_TARGET_ROLES: tuple[str, ...] = ("base_angle", "apex_angle")
_PROMPT_TASK_KEY = "symmetry_angle_value"


def _resolve_symmetry_plan(
    *,
    query_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> SymmetryAnglePlan:
    """Bind the public symmetry query to one numeric construction."""

    if str(query_id) == "rectangle_diagonal_angle":
        return build_rectangle_diagonal_plan(
            instance_seed=int(instance_seed),
            params=params,
            generation_defaults=generation_defaults,
        )
    if str(query_id) == "reflection_axis_angle":
        return build_reflection_axis_plan(
            instance_seed=int(instance_seed),
            params=params,
            generation_defaults=generation_defaults,
        )
    if str(query_id) == "isosceles_base_angle_chain":
        target_role, _target_role_probabilities = select_internal_option(
            options=_ISOSCELES_TARGET_ROLES,
            params=params,
            param_name="target_role",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.isosceles_target_role",
        )
        return build_isosceles_plan(
            target_role=str(target_role),
            instance_seed=int(instance_seed),
            params=params,
            generation_defaults=generation_defaults,
        )
    raise ValueError(f"unsupported query_id for {TASK_ID}: {query_id}")


def _render_symmetry_plan(
    *,
    query_id: str,
    ctx: RenderContext,
    plan: SymmetryAnglePlan,
    instance_seed: int,
) -> RenderedSymmetryAngleScene:
    """Render the construction selected by the public task branch."""

    if str(query_id) == "rectangle_diagonal_angle":
        return render_rectangle_diagonal_scene(ctx, plan, instance_seed=int(instance_seed))
    if str(query_id) == "reflection_axis_angle":
        return render_reflection_axis_scene(ctx, plan, instance_seed=int(instance_seed))
    if str(query_id) == "isosceles_base_angle_chain":
        return render_isosceles_angle_scene(ctx, plan, instance_seed=int(instance_seed))
    raise ValueError(f"unsupported query_id for {TASK_ID}: {query_id}")


def _prompt_dynamic_slots(plan: SymmetryAnglePlan) -> dict[str, Any]:
    """Bind prompt slots specific to symmetry/equal-side angle questions."""

    return {"target_angle_label": str(plan.target_angle_label)}


@register_task
class GeometryPolygonAngleChaseSymmetryAngleValueTask:
    """Infer a missing angle from visible symmetry or equal-angle structure."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        """Own query selection, answer binding, annotation binding, and final output."""

        return run_angle_chase_entry(
            self,
            int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            task_id=TASK_ID,
            resolve_plan=_resolve_symmetry_plan,
            render_plan=_render_symmetry_plan,
            prompt_task_key=_PROMPT_TASK_KEY,
            prompt_dynamic_slots=_prompt_dynamic_slots,
            trace_common=symmetry_trace_common,
            render_map=symmetry_render_map,
        )


__all__ = [
    "GeometryPolygonAngleChaseSymmetryAngleValueTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
