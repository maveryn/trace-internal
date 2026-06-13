"""Public task for `task_charts__dashboard__dual_source_target_sum_value`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.dashboard._lifecycle import DashboardTaskPlan, MaterializedDashboardTask, dashboard_task_output_fields, run_dashboard_public_task
from trace.tasks.charts.dashboard.shared.prompts import build_prompt_artifacts, build_prompt_slots
from trace.tasks.charts.dashboard.shared.sampling import build_dashboard_base_sample
from trace.tasks.charts.dashboard.shared.state import DOMAIN, SCENE_ID, SCENE_VARIANT, DashboardDataset, DashboardQuery
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id


def _build_task_output(materialized: MaterializedDashboardTask) -> TaskOutput:
    return TaskOutput(**dashboard_task_output_fields(materialized))
from trace.tasks.charts.dashboard.shared.metrics import category_by_id, choose_distinct_rank_params, choose_rank_params, panel_by_id, rank_phrase, ranked_category_id


QUERY_ID = "dual_source_target_sum_value"
TASK_PARAM_DEFAULTS: dict[str, Any] = {"panel_count_max": 5, "category_count_max": 10, "rank_n_support": [1], "panel_kind_weights": {"bar": 1.0, "line": 0.0, "donut": 0.0, "radar": 0.0}}


@register_task
class ChartsDashboardDualSourceTargetSumValueTask:
    """Select categories from two source panels and sum their values in a target panel."""

    task_id = "task_charts__dashboard__dual_source_target_sum_value"
    domain = DOMAIN
    objective_contract = "dual_source_target_sum_value"
    supported_query_ids = (QUERY_ID,)
    default_dataset_enabled = True

    def _prepare_dual_source_target_sum_plan(self, instance_seed: int, params: dict[str, Any], selected_query_id: str) -> DashboardTaskPlan:
        """Bind two source-ranked categories and the two target-panel addends."""
        del selected_query_id
        effective_params = {**TASK_PARAM_DEFAULTS, **dict(params)}
        rng = spawn_rng(int(instance_seed), f"{SCENE_ID}.{self.objective_contract}.selection")
        base_sample = build_dashboard_base_sample(effective_params, instance_seed=int(instance_seed))
        first_source_id, second_source_id, target_id = rng.sample([str(panel.panel_id) for panel in base_sample.panels], 3)
        first_source = panel_by_id(base_sample.panels, first_source_id)
        second_source = panel_by_id(base_sample.panels, second_source_id)
        target_panel = panel_by_id(base_sample.panels, target_id)
        first_direction, first_rank_n = choose_rank_params(rng, params=effective_params, category_count=len(base_sample.categories))
        second_direction, second_rank_n = choose_distinct_rank_params(rng, params=effective_params, category_count=len(base_sample.categories), avoid_phrase=rank_phrase(first_direction, first_rank_n))
        first_category_id = ranked_category_id(categories=base_sample.categories, panel=first_source, direction=first_direction, rank_n=first_rank_n)
        second_category_id = ranked_category_id(categories=base_sample.categories, panel=second_source, direction=second_direction, rank_n=second_rank_n)
        if str(first_category_id) == str(second_category_id):
            raise ValueError("dual-source sum needs two distinct selected categories")
        first_target_value = int(target_panel.values_by_category_id[str(first_category_id)])
        second_target_value = int(target_panel.values_by_category_id[str(second_category_id)])
        answer = int(first_target_value) + int(second_target_value)
        relations = {
            **dict(base_sample.common_params),
            "first_source_panel_id": str(first_source_id),
            "first_source_panel_name": str(first_source.name),
            "second_source_panel_id": str(second_source_id),
            "second_source_panel_name": str(second_source.name),
            "target_panel_id": str(target_id),
            "target_panel_name": str(target_panel.name),
            "first_rank_direction": str(first_direction),
            "first_rank_n": int(first_rank_n),
            "first_rank_phrase": rank_phrase(str(first_direction), int(first_rank_n)),
            "second_rank_direction": str(second_direction),
            "second_rank_n": int(second_rank_n),
            "second_rank_phrase": rank_phrase(str(second_direction), int(second_rank_n)),
            "first_category_id": str(first_category_id),
            "first_category_label": str(category_by_id(base_sample.categories, first_category_id).label),
            "second_category_id": str(second_category_id),
            "second_category_label": str(category_by_id(base_sample.categories, second_category_id).label),
            "first_target_value": int(first_target_value),
            "second_target_value": int(second_target_value),
            "sum_value": int(answer),
        }
        refs = ((str(first_source_id), str(first_category_id)), (str(second_source_id), str(second_category_id)), (str(target_id), str(first_category_id)), (str(target_id), str(second_category_id)))
        dataset = DashboardDataset(scene_variant=SCENE_VARIANT, categories=base_sample.categories, panels=base_sample.panels, query=DashboardQuery(answer=int(answer), answer_type="integer", annotation_refs=refs, params=dict(relations)))
        prompt_artifacts = build_prompt_artifacts(prompt_query_key=QUERY_ID, dynamic_slots=build_prompt_slots(dataset=dataset), instance_seed=int(instance_seed))
        roles = {"first_source_panel": refs[0], "second_source_panel": refs[1], "target_first_category": refs[2], "target_second_category": refs[3]}
        return DashboardTaskPlan(dataset=dataset, prompt_artifacts=prompt_artifacts, relations=relations, answer_gt=TypedValue(type="integer", value=int(answer)), annotation_refs=refs, annotation_roles=roles)

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, _probabilities, task_params = select_task_query_id(instance_seed=int(instance_seed), params={**TASK_PARAM_DEFAULTS, **dict(params)}, supported_query_ids=self.supported_query_ids, default_query_id=QUERY_ID, task_id=self.task_id)
        return run_dashboard_public_task(instance_seed=int(instance_seed), params=task_params, max_attempts=int(max_attempts), selected_query_id=str(selected_query_id), build_plan=self._prepare_dual_source_target_sum_plan, build_output=_build_task_output)


__all__ = ["ChartsDashboardDualSourceTargetSumValueTask"]
