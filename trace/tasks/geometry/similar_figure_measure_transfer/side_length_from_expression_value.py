"""Find a side length in similar figures with expression-labeled sides."""

from __future__ import annotations

from trace.core.seed import spawn_rng
from trace.tasks.registry import register_task

from ._lifecycle import SimilarFigureObjectivePlan, forced_or_sampled_family, run_similar_figure_public_entry
from .shared.algebra import side_expression_case


TASK_ID = "task_geometry__similar_figure_measure_transfer__side_length_from_expression_value"
SUPPORTED_QUERY_IDS = ("single",)
DEFAULT_QUERY_ID = "single"
CONFIG_GROUP_KEY = "side_length_from_expression_value"
PROMPT_BRANCH_KEY = "single"
CONSTRUCTION_FAMILIES = ("triangle_target_expression", "polygon_target_expression")


def _prepare_side_length_from_expression_objective(instance_seed: int, selected_branch: str, branch_probabilities: dict[str, float], task_params: dict) -> SimilarFigureObjectivePlan:
    """Bind the side-length objective to one expression-labeled side setup."""

    family = forced_or_sampled_family(
        context_label=TASK_ID,
        options=CONSTRUCTION_FAMILIES,
        instance_seed=int(instance_seed),
        params=task_params,
        namespace=f"{TASK_ID}.construction_family",
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{family}.case")
    shape_kind = "triangle" if family == "triangle_target_expression" else str(rng.choice(("quadrilateral", "pentagon")))
    case = side_expression_case(
        construction_family=family,
        shape_kind=shape_kind,
        answer=int(rng.randint(8, 31)),
        scale_factor=int(rng.randint(2, 5)),
        coefficient=int(rng.randint(1, 4)),
        variable_value=int(rng.randint(2, 10)),
        support_source=int(rng.randint(3, 12)),
    )
    return SimilarFigureObjectivePlan(
        case=case,
        config_group_key=CONFIG_GROUP_KEY,
        prompt_branch_key=PROMPT_BRANCH_KEY,
        answer_type="number",
        answer_hint_key="answer_hint_number",
        program_scope="side_length_from_expression_value",
        public_branch=str(selected_branch),
        branch_probabilities=dict(branch_probabilities),
    )


@register_task
class GeometrySimilarFigureMeasureTransferSideLengthFromExpressionValueTask:
    """Find a side length in similar figures with expression-labeled sides."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = DEFAULT_QUERY_ID
    prepare_objective = staticmethod(_prepare_side_length_from_expression_objective)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_similar_figure_public_entry(self, int(instance_seed), params=params, max_attempts=int(max_attempts))


__all__ = ["GeometrySimilarFigureMeasureTransferSideLengthFromExpressionValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
