"""Compute open-box dimensions or volume from a corner-cut net."""

from __future__ import annotations

from typing import Mapping

from trace.core.types import TypedValue
from trace.tasks.registry import register_task

from ._lifecycle import RectangularSolidObjectivePlan, run_rectangular_solid_public_entry
from .shared.annotations import bbox_map_annotation
from .shared.construction import resolve_open_box_dimension, resolve_open_box_volume
from .shared.defaults import DOMAIN
from .shared.rendering import render_open_box_net_scene


TASK_ID = "task_geometry__rectangular_solid__open_box_net_dimension_value"
QUERY_ID_OPEN_BOX_DIMENSION = "open_box_dimension_from_corner_cut"
QUERY_ID_OPEN_BOX_VOLUME = "open_box_volume_from_net"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (
    QUERY_ID_OPEN_BOX_DIMENSION,
    QUERY_ID_OPEN_BOX_VOLUME,
)
DEFAULT_QUERY_ID = QUERY_ID_OPEN_BOX_DIMENSION
PROMPT_TASK_KEY = "open_box_net_dimension_value"


def _prepare_open_box_objective(
    instance_seed,
    task_params: Mapping[str, object],
    selected_branch,
    branch_probabilities,
):
    """Bind resulting base-dimension or volume solving for the net."""

    if str(selected_branch) == QUERY_ID_OPEN_BOX_DIMENSION:
        problem = resolve_open_box_dimension(
            instance_seed=int(instance_seed),
            params=task_params,
            sampling_label=f"{TASK_ID}.{selected_branch}",
        )
    else:
        problem = resolve_open_box_volume(
            instance_seed=int(instance_seed),
            params=task_params,
            sampling_label=f"{TASK_ID}.{selected_branch}",
        )
    trace_values = {
        "target_role": str(problem.target_role),
        "sheet_length": int(problem.sheet_length),
        "sheet_width": int(problem.sheet_width),
        "cut_size": int(problem.cut_size),
        "base_length": int(problem.base_length),
        "base_width": int(problem.base_width),
        "height": int(problem.cut_size),
        "open_box_volume": int(problem.open_box_volume),
    }
    return RectangularSolidObjectivePlan(
        prompt_task_key=PROMPT_TASK_KEY,
        prompt_branch_key=str(selected_branch),
        problem=problem,
        render_scene=render_open_box_net_scene,
        bind_annotation=bbox_map_annotation,
        answer_gt=TypedValue(type="integer", value=int(problem.answer)),
        query_params={
            "query_id_probabilities": dict(branch_probabilities),
            "case_probabilities": dict(problem.case_probabilities),
            "answer_support_probabilities": dict(problem.answer_support_probabilities),
            **dict(trace_values),
        },
        trace_values=trace_values,
    )


@register_task
class GeometryRectangularSolidOpenBoxNetDimensionValueTask:
    """Compute a resulting base dimension or volume from an open-box net."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = DEFAULT_QUERY_ID
    prepare_objective = staticmethod(_prepare_open_box_objective)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        """Generate one open-box net measurement problem."""

        return run_rectangular_solid_public_entry(
            self,
            int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )
