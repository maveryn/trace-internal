"""Find the first linear_projection threshold crossing label in an ordered chart."""
from __future__ import annotations
from ._lifecycle import build_crossing_plan as B, run_single_series_lifecycle as R
from .shared.state import DOMAIN
from trace.tasks.registry import register_task
T = "task_charts__single_series__projected_threshold_crossing_label"
Q = {"projected_above_threshold_crossing_label": ("linear_projection_crosses_above", "above"), "projected_below_threshold_crossing_label": ("linear_projection_crosses_below", "below")}
D = dict(value_min=1, value_max=80, threshold_edge_margin=8, threshold_min=20, threshold_max=60, observed_count_min=3, observed_count_max=5, projection_count_min=4, projection_count_max=6, projection_step_min=1, projection_step_max=5)
PGM = "first_future_label(linear_project(sequence(values), comparison, threshold)); output=string_label; annotation=point_set(last_observed_marks_and_projected_slots); scene=single_series; scope=projected_threshold_crossing_label"
def _build_plan(params, seed, query_id, _):
    variant, direction = Q[str(query_id)]
    return B(params=params, seed=seed, namespace=T, crossing_variant=variant, crossing_mode="linear_projection", direction=direction, prompt_key=query_id, projected=True, program_code=PGM, reasoning_load=0.78)

@register_task
class ChartsTrendProjectedThresholdCrossingLabelTask:
    task_id = T
    domain = DOMAIN
    objective_contract = "projected_threshold_crossing_label"
    supported_query_ids = tuple(Q)
    default_query_id = "projected_above_threshold_crossing_label"
    default_dataset_enabled = True

    def generate(self, instance_seed, *, params, max_attempts):
        return R(task=self, instance_seed=instance_seed, params={**D, **params}, max_attempts=max_attempts, default_query_id=self.default_query_id, build_plan=_build_plan)
