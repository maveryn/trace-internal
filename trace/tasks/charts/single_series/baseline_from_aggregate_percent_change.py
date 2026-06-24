"""Compute baseline_from_aggregate_percent_change over labeled chart values."""
from __future__ import annotations
from trace.core.query_ids import SINGLE_QUERY_ID
from ._lifecycle import build_counterfactual_plan as B, run_single_series_lifecycle as R
from .shared.state import DOMAIN
from trace.tasks.registry import register_task
T = "task_charts__single_series__baseline_from_aggregate_percent_change"
D = dict(mark_count_min=4, mark_count_max=10, value_min=5, value_max=80, aggregate_count_min=2, aggregate_count_max=3)
PGM = "solve_baseline(sum(values(aggregate_labels)), percent_above_baseline); output=integer_value; annotation=point_set(aggregate_marks); scene=single_series; scope=baseline_from_aggregate_percent_change"
def _build_plan(params, seed, query_id, _):
    if query_id != SINGLE_QUERY_ID: raise ValueError(f"unsupported query_id for {T}: {query_id}")
    return B(params=params, seed=seed, namespace=T, operation="aggregate_baseline", prompt_key="baseline_from_aggregate_percent_change", dynamic_slots={"aggregate_labels_text":"trace:quoted:aggregate_labels", "percent_value":"trace:str:percent_value"}, relation_params={"counterfactual_operation":"aggregate_percent_higher_than_baseline", "aggregate_labels":"trace:list:aggregate_labels", "percent_value":"trace:int:percent_value"}, program_code=PGM, reasoning_load=0.72)

@register_task
class ChartsHypotheticalBaselineFromAggregatePercentChangePublicTask:
    task_id = T
    domain = DOMAIN
    objective_contract = "baseline_from_aggregate_percent_change"
    supported_query_ids = (SINGLE_QUERY_ID,)
    default_query_id = SINGLE_QUERY_ID
    default_dataset_enabled = True

    def generate(self, instance_seed, *, params, max_attempts):
        return R(task=self, instance_seed=instance_seed, params={**D, **params}, max_attempts=max_attempts, default_query_id=self.default_query_id, build_plan=_build_plan)
