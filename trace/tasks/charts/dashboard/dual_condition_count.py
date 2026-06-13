"""Public task for `task_charts__dashboard__dual_condition_count`."""

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
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.charts.dashboard.shared.defaults import generation_default
from trace.tasks.charts.dashboard.shared.metrics import category_by_id, choose_threshold_pair_for_count, condition_count_support, condition_phrase, weighted_choice_from_defaults
from trace.tasks.charts.dashboard.shared.state import SUPPORTED_CONDITION_COMPARISONS


QUERY_ID = "dual_condition_count"


@register_task
class ChartsDashboardDualConditionCountTask:
    """Count shared categories satisfying one threshold condition in each of two panels."""

    task_id = "task_charts__dashboard__dual_condition_count"
    domain = DOMAIN
    objective_contract = "dual_condition_count"
    supported_query_ids = (QUERY_ID,)
    default_dataset_enabled = True

    def _bind_dual_threshold_category_count_plan(self, instance_seed: int, params: dict[str, Any], selected_query_id: str) -> DashboardTaskPlan:
        """Bind two panel thresholds and count categories satisfying both predicates."""
        del selected_query_id
        rng = spawn_rng(int(instance_seed), f"{SCENE_ID}.{self.objective_contract}.selection")
        base_sample = build_dashboard_base_sample(params, instance_seed=int(instance_seed))
        first_panel_id, second_panel_id = rng.sample([str(panel.panel_id) for panel in base_sample.panels], 2)
        first_panel = next(panel for panel in base_sample.panels if str(panel.panel_id) == first_panel_id)
        second_panel = next(panel for panel in base_sample.panels if str(panel.panel_id) == second_panel_id)
        first_comparison = weighted_choice_from_defaults(rng, params=params, key="first_condition_comparison", supported=SUPPORTED_CONDITION_COMPARISONS, fallback_weights_key="condition_comparison_weights")
        second_comparison = weighted_choice_from_defaults(rng, params=params, key="second_condition_comparison", supported=SUPPORTED_CONDITION_COMPARISONS, fallback_weights_key="condition_comparison_weights")
        support = condition_count_support(params, len(base_sample.categories))
        support_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{SCENE_ID}.dual_condition_count.answer")
        target_count = int(support[abs(int(support_index)) % len(support)])
        value_min = int(params.get("value_min", generation_default("value_min", 12)))
        value_max = int(params.get("value_max", generation_default("value_max", 92)))
        first_threshold, second_threshold, matches = choose_threshold_pair_for_count(rng=rng, categories=base_sample.categories, first_panel=first_panel, second_panel=second_panel, first_comparison=first_comparison, second_comparison=second_comparison, target_count=int(target_count), value_min=value_min, value_max=value_max)
        category_order = {str(category.category_id): index for index, category in enumerate(base_sample.categories)}
        sorted_matches = tuple(sorted(matches, key=lambda item: category_order[str(item)]))
        refs = tuple(ref for category_id in sorted_matches for ref in ((str(first_panel_id), str(category_id)), (str(second_panel_id), str(category_id))))
        relations = {
            **dict(base_sample.common_params),
            "first_condition_panel_id": str(first_panel_id),
            "first_condition_panel_name": str(first_panel.name),
            "second_condition_panel_id": str(second_panel_id),
            "second_condition_panel_name": str(second_panel.name),
            "first_condition_comparison": str(first_comparison),
            "second_condition_comparison": str(second_comparison),
            "first_threshold": int(first_threshold),
            "second_threshold": int(second_threshold),
            "first_condition_phrase": condition_phrase(str(first_comparison), int(first_threshold)),
            "second_condition_phrase": condition_phrase(str(second_comparison), int(second_threshold)),
            "matching_category_ids": list(sorted_matches),
            "matching_category_labels": [str(category_by_id(base_sample.categories, category_id).label) for category_id in sorted_matches],
            "target_count_support": list(support),
            "count_value": int(len(sorted_matches)),
        }
        dataset = DashboardDataset(scene_variant=SCENE_VARIANT, categories=base_sample.categories, panels=base_sample.panels, query=DashboardQuery(answer=int(len(sorted_matches)), answer_type="integer", annotation_refs=refs, params=dict(relations)))
        prompt_artifacts = build_prompt_artifacts(prompt_query_key=QUERY_ID, dynamic_slots=build_prompt_slots(dataset=dataset), instance_seed=int(instance_seed))
        return DashboardTaskPlan(dataset=dataset, prompt_artifacts=prompt_artifacts, relations=relations, answer_gt=TypedValue(type="integer", value=int(len(sorted_matches))), annotation_refs=refs)

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, _probabilities, task_params = select_task_query_id(instance_seed=int(instance_seed), params=params, supported_query_ids=self.supported_query_ids, default_query_id=QUERY_ID, task_id=self.task_id)
        return run_dashboard_public_task(instance_seed=int(instance_seed), params=task_params, max_attempts=int(max_attempts), selected_query_id=str(selected_query_id), build_plan=self._bind_dual_threshold_category_count_plan, build_output=_build_task_output)


__all__ = ["ChartsDashboardDualConditionCountTask"]
