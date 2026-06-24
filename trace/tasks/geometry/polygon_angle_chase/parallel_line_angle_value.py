from __future__ import annotations

from typing import Any

from trace.tasks.registry import register_task

from ._lifecycle import run_angle_chase_entry
from .shared.defaults import DOMAIN
from .shared.output import parallel_render_map, parallel_trace_common
from .shared.rendering import (
    render_parallel_one_transversal_scene,
    render_parallel_two_transversal_scene,
)
from .shared.sampling import (
    build_parallel_single_plan,
    build_parallel_two_plan,
    select_internal_option,
)
from .shared.state import ParallelAnglePlan, RenderContext, RenderedParallelAngleScene

TASK_ID = "task_geometry__polygon_angle_chase__parallel_line_angle_value"
SUPPORTED_QUERY_IDS: tuple[str, ...] = ("single_transversal_chain", "two_transversal_angle_sum")
_SINGLE_TRANSVERSAL_RELATIONS: tuple[str, ...] = ("corresponding_same", "supplementary")
_PROMPT_TASK_KEY = "parallel_line_angle_value"


def _resolve_parallel_plan(**kw) -> ParallelAnglePlan:
    branch = str(kw["query_id"])
    seed = int(kw["instance_seed"])
    params = kw["params"]
    defaults = kw["generation_defaults"]
    if branch == "single_transversal_chain":
        relation_id, _relation_probabilities = select_internal_option(
            options=_SINGLE_TRANSVERSAL_RELATIONS,
            params=params,
            param_name="relation_id",
            instance_seed=seed,
            namespace=f"{TASK_ID}.single_transversal_relation",
        )
        return build_parallel_single_plan(
            relation_id=str(relation_id),
            instance_seed=seed,
            params=params,
            generation_defaults=defaults,
        )
    if branch == "two_transversal_angle_sum":
        return build_parallel_two_plan(
            instance_seed=seed,
            params=params,
            generation_defaults=defaults,
        )
    raise ValueError(f"unsupported query_id for {TASK_ID}: {branch}")


def _render_parallel_plan(**kw) -> RenderedParallelAngleScene:
    if str(kw["query_id"]) == "single_transversal_chain":
        return render_parallel_one_transversal_scene(kw["ctx"], kw["plan"], instance_seed=int(kw["instance_seed"]))
    if str(kw["query_id"]) == "two_transversal_angle_sum":
        return render_parallel_two_transversal_scene(kw["ctx"], kw["plan"], instance_seed=int(kw["instance_seed"]))
    raise ValueError(f"unsupported query_id for {TASK_ID}: {kw['query_id']}")


def _prompt_dynamic_slots(plan: ParallelAnglePlan):
    return {"target_angle_label": str(plan.target_angle_label)}


@register_task
class GeometryPolygonAngleChaseParallelLineAngleValueTask:
    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int):
        return run_angle_chase_entry(
            self,
            int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            task_id=TASK_ID,
            resolve_plan=_resolve_parallel_plan,
            render_plan=_render_parallel_plan,
            prompt_task_key=_PROMPT_TASK_KEY,
            prompt_dynamic_slots=_prompt_dynamic_slots,
            trace_common=parallel_trace_common,
            render_map=parallel_render_map,
        )
