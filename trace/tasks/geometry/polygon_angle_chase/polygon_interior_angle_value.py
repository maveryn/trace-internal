"""Infer a polygon interior angle from visible algebraic angle labels."""

from __future__ import annotations

from typing import Any

from trace.tasks.registry import register_task

from ._lifecycle import run_angle_chase_entry
from .shared.defaults import DOMAIN
from .shared.measurements import polygon_kind
from .shared.output import polygon_render_map, polygon_trace_common
from .shared.rendering import render_polygon_angle_scene
from .shared.sampling import build_polygon_angle_plan, select_internal_option
from .shared.state import PolygonAnglePlan, RenderContext, RenderedPolygonAngleScene

TASK_ID = "task_geometry__polygon_angle_chase__polygon_interior_angle_value"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (
    "triangle_interior_angle",
    "quadrilateral_interior_angle",
    "pentagon_interior_angle",
    "hexagon_interior_angle",
)
_QUERY_SIDE_COUNTS: dict[str, int] = {
    "triangle_interior_angle": 3,
    "quadrilateral_interior_angle": 4,
    "pentagon_interior_angle": 5,
    "hexagon_interior_angle": 6,
}
_LABEL_STYLES: tuple[str, ...] = ("target_expression_mixed", "all_expression")
_PROMPT_TASK_KEY = "polygon_interior_angle_value"


def _resolve_polygon_plan(
    *,
    query_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> PolygonAnglePlan:
    """Bind the public side-count query to one algebraic polygon construction."""

    side_count = int(_QUERY_SIDE_COUNTS[str(query_id)])
    label_style, _label_probabilities = select_internal_option(
        options=_LABEL_STYLES,
        params=params,
        param_name="label_style",
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.label_style",
    )
    return build_polygon_angle_plan(
        side_count=int(side_count),
        label_style=str(label_style),
        instance_seed=int(instance_seed),
        params=params,
        generation_defaults=generation_defaults,
    )


def _render_polygon_plan(
    *,
    query_id: str,
    ctx: RenderContext,
    plan: PolygonAnglePlan,
    instance_seed: int,
) -> RenderedPolygonAngleScene:
    """Render the polygon construction selected by the public query."""

    return render_polygon_angle_scene(ctx, plan, instance_seed=int(instance_seed))


def _prompt_dynamic_slots(plan: PolygonAnglePlan) -> dict[str, Any]:
    """Bind prompt slots specific to polygon interior-angle questions."""

    return {
        "polygon_kind": polygon_kind(plan.side_count),
        "target_angle_name": str(plan.target_angle_name),
    }


@register_task
class GeometryPolygonAngleChaseInteriorAngleValueTask:
    """Infer a missing polygon interior angle from visible labels."""

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
            resolve_plan=_resolve_polygon_plan,
            render_plan=_render_polygon_plan,
            prompt_task_key=_PROMPT_TASK_KEY,
            prompt_dynamic_slots=_prompt_dynamic_slots,
            trace_common=polygon_trace_common,
            render_map=polygon_render_map,
            include_scene_rotation=True,
        )


__all__ = [
    "GeometryPolygonAngleChaseInteriorAngleValueTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
