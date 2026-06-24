"""Find a linear scale factor between similar figures."""

from __future__ import annotations

from trace.core.seed import spawn_rng
from trace.tasks.registry import register_task

from ._lifecycle import SimilarFigureObjectivePlan, run_similar_figure_public_entry
from .shared.measurements import (
    scale_factor_from_area_case,
    scale_factor_from_perimeter_case,
    scale_factor_from_side_case,
)


TASK_ID = "task_geometry__similar_figure_measure_transfer__scale_factor_value"
SUPPORTED_QUERY_IDS = (
    "scale_factor_from_side_pair",
    "scale_factor_from_perimeter_pair",
    "scale_factor_from_area_pair",
)
DEFAULT_QUERY_ID = SUPPORTED_QUERY_IDS[0]
CONFIG_GROUP_KEY = "scale_factor_value"


def _prepare_scale_factor_objective(instance_seed: int, selected_branch: str, branch_probabilities: dict[str, float], task_params: dict) -> SimilarFigureObjectivePlan:
    """Bind one public scale-factor query to its numeric source relation."""

    _ = task_params
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{selected_branch}.case")
    shape_kind = str(rng.choice(("triangle", "quadrilateral", "pentagon")))
    scale_factor = int(rng.randint(2, 10))
    layout_kind = str(rng.choice(("side_by_side", "rotated_pair")))
    if selected_branch == "scale_factor_from_side_pair":
        case = scale_factor_from_side_case(
            shape_kind=shape_kind,
            scale_factor=scale_factor,
            source_side=int(rng.randint(3, 13)),
            layout_kind=layout_kind,
        )
    elif selected_branch == "scale_factor_from_perimeter_pair":
        case = scale_factor_from_perimeter_case(
            shape_kind=shape_kind,
            scale_factor=scale_factor,
            source_perimeter=int(rng.randint(10, 37)),
            layout_kind=layout_kind,
        )
    elif selected_branch == "scale_factor_from_area_pair":
        case = scale_factor_from_area_case(
            shape_kind=shape_kind,
            scale_factor=scale_factor,
            source_area=int(rng.randint(3, 21)),
            layout_kind=layout_kind,
        )
    else:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_branch}")
    return SimilarFigureObjectivePlan(
        case=case,
        config_group_key=CONFIG_GROUP_KEY,
        prompt_branch_key=str(selected_branch),
        answer_type="integer",
        answer_hint_key="answer_hint_integer_scale",
        program_scope="scale_factor_value",
        public_branch=str(selected_branch),
        branch_probabilities=dict(branch_probabilities),
    )


@register_task
class GeometrySimilarFigureMeasureTransferScaleFactorValueTask:
    """Find a linear scale factor between similar figures."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = DEFAULT_QUERY_ID
    prepare_objective = staticmethod(_prepare_scale_factor_objective)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_similar_figure_public_entry(self, int(instance_seed), params=params, max_attempts=int(max_attempts))


__all__ = ["GeometrySimilarFigureMeasureTransferScaleFactorValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
