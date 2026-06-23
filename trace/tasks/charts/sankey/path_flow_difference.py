"""Return the absolute value difference on one two-band Sankey path."""

from __future__ import annotations

from typing import Any

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.seed import spawn_rng
from trace.tasks.registry import register_task

from ._lifecycle import build_sankey_plan, run_sankey_task
from .shared.sampling import answer_value_bounds, path_dict, sample_frame
from .shared.state import DOMAIN, SankeyDataset, SankeyQuestion


TASK_ID = "task_charts__sankey__path_flow_difference"
QUERY_ID = SINGLE_QUERY_ID
SUPPORTED_QUERY_IDS = (QUERY_ID,)
DEFAULT_QUERY_ID = QUERY_ID
PROMPT_KEY = "path_flow_difference"

TASK_PARAM_DEFAULTS: dict[str, Any] = {}


def _build_plan(params: dict[str, Any], instance_seed: int, selected: str, probabilities: dict[str, float]):
    """Bind one eligible path and compute the absolute difference between its two values."""

    if str(selected) != QUERY_ID:
        raise ValueError(f"unsupported Sankey path difference branch: {selected}")
    frame = sample_frame(params, instance_seed=int(instance_seed))
    diff_min, diff_max = answer_value_bounds(
        params,
        min_key="path_difference_min",
        max_key="path_difference_max",
        fallback_min=2,
        fallback_max=25,
        context="Sankey path value difference",
    )
    eligible = [
        path
        for path in frame.paths
        if int(diff_min) <= int(path.absolute_difference) <= int(diff_max)
    ]
    if not eligible:
        raise ValueError("no eligible Sankey path difference")
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.path_selection")
    selected_path = eligible[int(rng.randrange(len(eligible)))]
    segment_refs = (
        f"{selected_path.path_id}:source_middle",
        f"{selected_path.path_id}:middle_target",
    )
    question = SankeyQuestion(
        branch_id=QUERY_ID,
        branch_probabilities=dict(probabilities),
        answer=int(selected_path.absolute_difference),
        answer_type="integer",
        annotation_type="bbox_set",
        annotation_segment_ids=tuple(segment_refs),
        params={
            "program_code": "abs_difference(value(source_to_middle), value(middle_to_target))",
            "source_label": str(selected_path.source_label),
            "middle_label": str(selected_path.middle_label),
            "target_label": str(selected_path.target_label),
            "route_count": 1,
            "query_path_ids": [str(selected_path.path_id)],
            "expression": f"abs({int(selected_path.first_value)} - {int(selected_path.second_value)})",
            "path_details": [path_dict(selected_path)],
        },
    )
    return build_sankey_plan(
        dataset=SankeyDataset(frame=frame, question=question),
        prompt_key=PROMPT_KEY,
        question_format="sankey_path_value",
        witness_type="sankey_path_flow_difference_witness",
    )


@register_task
class ChartsFlowSankeyPathFlowDifferencePublicTask:
    """Return the absolute value difference on one two-band Sankey path."""

    task_id = TASK_ID
    domain = DOMAIN
    objective_contract = "path_flow_difference"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = DEFAULT_QUERY_ID
    default_dataset_enabled = True
    _build_plan = staticmethod(_build_plan)

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int):
        return run_sankey_task(
            self,
            int(instance_seed),
            {**TASK_PARAM_DEFAULTS, **dict(params)},
            int(max_attempts),
        )


__all__ = ["ChartsFlowSankeyPathFlowDifferencePublicTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
