"""Return the bottleneck value on one two-band Sankey path."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.seed import spawn_rng
from trace.tasks.registry import register_task

from ._lifecycle import build_sankey_plan, run_sankey_task
from .shared.sampling import path_dict, sample_frame
from .shared.state import DOMAIN, SankeyDataset, SankeyQuestion


TASK_ID = "task_charts__sankey__path_bottleneck_value"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)


def _build_plan(params, instance_seed, selected, probabilities):
    """Bind one path and compute the smaller of its two printed flow values."""

    if str(selected) != SINGLE_QUERY_ID:
        raise ValueError(f"unsupported Sankey path bottleneck branch: {selected}")
    frame = sample_frame(params, instance_seed=int(instance_seed))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.path_selection")
    path = frame.paths[int(rng.randrange(len(frame.paths)))]
    segments = (
        f"{path.path_id}:source_middle",
        f"{path.path_id}:middle_target",
    )
    question = SankeyQuestion(
        branch_id=SINGLE_QUERY_ID,
        branch_probabilities=dict(probabilities),
        answer=int(path.bottleneck_value),
        answer_type="integer",
        annotation_type="bbox_set",
        annotation_segment_ids=segments,
        params={
            "program_code": "min(value(source_to_middle), value(middle_to_target))",
            "source_label": str(path.source_label),
            "middle_label": str(path.middle_label),
            "target_label": str(path.target_label),
            "route_count": 1,
            "query_path_ids": [str(path.path_id)],
            "expression": f"min({int(path.first_value)}, {int(path.second_value)})",
            "path_details": [path_dict(path)],
        },
    )
    return build_sankey_plan(
        dataset=SankeyDataset(frame=frame, question=question),
        prompt_key="path_bottleneck_value",
        question_format="sankey_path_value",
        witness_type="sankey_path_bottleneck_value_witness",
    )


@register_task
class ChartsFlowSankeyPathBottleneckValuePublicTask:
    """Return the bottleneck value on one two-band Sankey path."""

    task_id = TASK_ID
    domain = DOMAIN
    objective_contract = "path_bottleneck_value"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = SINGLE_QUERY_ID
    default_dataset_enabled = True
    _build_plan = staticmethod(_build_plan)

    def generate(self, instance_seed, *, params, max_attempts):
        return run_sankey_task(
            self,
            int(instance_seed),
            dict(params),
            int(max_attempts),
        )
