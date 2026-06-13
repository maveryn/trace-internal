"""Public task for `task_charts__dashboard__top_k_overlap_count`."""

from __future__ import annotations

from typing import Any, Sequence

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
from trace.tasks.charts.dashboard.shared.defaults import generation_default
from trace.tasks.charts.dashboard.shared.metrics import balanced_support_choice, category_by_id, panel_by_id, top_k_category_ids, top_k_overlap_count_support, top_k_support, weighted_choice_from_defaults
from trace.tasks.charts.dashboard.shared.state import SUPPORTED_RANK_DIRECTIONS


QUERY_ID = "top_k_overlap_count"
TASK_PARAM_DEFAULTS: dict[str, Any] = {"category_count_min": 6}


def _feasible_overlap_targets(params: dict[str, Any], *, category_count: int, possible_top_k: Sequence[int]) -> tuple[int, ...]:
    raw_support = params.get("top_k_overlap_count_support", generation_default("top_k_overlap_count_support", [1, 2, 3, 4, 5]))
    if not isinstance(raw_support, Sequence) or isinstance(raw_support, (str, bytes)):
        raise ValueError("top_k_overlap_count_support must be a sequence")
    feasible = sorted({int(target) for target in raw_support for candidate_top_k in possible_top_k if max(0, int(candidate_top_k) * 2 - int(category_count)) <= int(target) <= int(candidate_top_k)})
    if not feasible:
        raise ValueError("top_k_overlap_count_support has no feasible targets")
    return tuple(feasible)


@register_task
class ChartsDashboardTopKOverlapCountTask:
    """Count labels that appear in the top-k set for two dashboard panels."""

    task_id = "task_charts__dashboard__top_k_overlap_count"
    domain = DOMAIN
    objective_contract = "top_k_overlap_count"
    supported_query_ids = (QUERY_ID,)
    default_dataset_enabled = True

    def _resolve_top_k_overlap_plan(self, instance_seed: int, params: dict[str, Any], selected_query_id: str) -> DashboardTaskPlan:
        """Construct the second panel so the top-k overlap count is realized exactly."""
        del selected_query_id
        effective_params = {**TASK_PARAM_DEFAULTS, **dict(params)}
        rng = spawn_rng(int(instance_seed), f"{SCENE_ID}.{self.objective_contract}.selection")
        base_sample = build_dashboard_base_sample(effective_params, instance_seed=int(instance_seed))
        direction = weighted_choice_from_defaults(rng, params=effective_params, key="top_k_rank_direction", supported=SUPPORTED_RANK_DIRECTIONS, fallback_weights_key="rank_direction_weights")
        top_k_values = top_k_support(effective_params, len(base_sample.categories))
        feasible_targets = _feasible_overlap_targets(effective_params, category_count=len(base_sample.categories), possible_top_k=top_k_values)
        target_count = balanced_support_choice(params=effective_params, instance_seed=int(instance_seed), namespace=f"{SCENE_ID}.top_k_overlap_count.answer", support=feasible_targets)
        feasible_top_k_values = tuple(int(candidate_top_k) for candidate_top_k in top_k_values if max(0, int(candidate_top_k) * 2 - len(base_sample.categories)) <= int(target_count) <= int(candidate_top_k))
        top_k = balanced_support_choice(params=effective_params, instance_seed=int(instance_seed), namespace=f"{SCENE_ID}.top_k_overlap_count.top_k", support=feasible_top_k_values)
        support = top_k_overlap_count_support(effective_params, category_count=len(base_sample.categories), top_k=int(top_k))
        first_panel_id, second_panel_id = rng.sample([str(panel.panel_id) for panel in base_sample.panels], 2)
        first_panel = panel_by_id(base_sample.panels, first_panel_id)
        second_panel = panel_by_id(base_sample.panels, second_panel_id)
        first_top = top_k_category_ids(categories=base_sample.categories, panel=first_panel, direction=str(direction), top_k=int(top_k))
        outside_first_top = [str(category.category_id) for category in base_sample.categories if str(category.category_id) not in set(first_top)]
        if int(top_k) - int(target_count) > len(outside_first_top):
            raise ValueError("target overlap is infeasible for sampled category count/top_k")
        overlap = tuple(rng.sample(list(first_top), int(target_count))) if int(target_count) > 0 else ()
        extra = tuple(rng.sample(outside_first_top, int(top_k) - int(target_count))) if int(top_k) > int(target_count) else ()
        desired_second_top = tuple(overlap) + tuple(extra)
        available_values = sorted(int(value) for value in second_panel.values_by_category_id.values())
        if str(direction) == "largest":
            target_values = list(reversed(available_values[-int(top_k):]))
            other_values = list(reversed(available_values[: len(available_values) - int(top_k)]))
        else:
            target_values = list(available_values[: int(top_k)])
            other_values = list(available_values[int(top_k):])
        target_ids = list(desired_second_top)
        other_ids = [str(category.category_id) for category in base_sample.categories if str(category.category_id) not in set(target_ids)]
        rng.shuffle(target_ids)
        rng.shuffle(other_ids)
        for category_id, value in zip(target_ids, target_values):
            second_panel.values_by_category_id[str(category_id)] = int(value)
        for category_id, value in zip(other_ids, other_values):
            second_panel.values_by_category_id[str(category_id)] = int(value)
        second_top = top_k_category_ids(categories=base_sample.categories, panel=second_panel, direction=str(direction), top_k=int(top_k))
        realized_overlap = tuple(category_id for category_id in first_top if category_id in set(second_top))
        if len(realized_overlap) != int(target_count):
            raise ValueError("constructed top-k overlap did not realize requested count")
        category_order = {str(category.category_id): index for index, category in enumerate(base_sample.categories)}
        overlap_sorted = tuple(sorted(realized_overlap, key=lambda category_id: category_order[str(category_id)]))
        refs = tuple((panel_id, category_id) for category_id in overlap_sorted for panel_id in (str(first_panel_id), str(second_panel_id)))
        rank_word = "highest-valued" if str(direction) == "largest" else "lowest-valued"
        relations = {
            **dict(base_sample.common_params),
            "first_topk_panel_id": str(first_panel_id),
            "first_topk_panel_name": str(first_panel.name),
            "second_topk_panel_id": str(second_panel_id),
            "second_topk_panel_name": str(second_panel.name),
            "top_k_rank_direction": str(direction),
            "top_k": int(top_k),
            "top_k_phrase": f"{int(top_k)} {rank_word}",
            "first_top_category_ids": list(first_top),
            "first_top_category_labels": [str(category_by_id(base_sample.categories, category_id).label) for category_id in first_top],
            "second_top_category_ids": list(second_top),
            "second_top_category_labels": [str(category_by_id(base_sample.categories, category_id).label) for category_id in second_top],
            "overlap_category_ids": list(overlap_sorted),
            "overlap_category_labels": [str(category_by_id(base_sample.categories, category_id).label) for category_id in overlap_sorted],
            "target_count_support": list(support),
            "count_value": int(len(overlap_sorted)),
        }
        dataset = DashboardDataset(scene_variant=SCENE_VARIANT, categories=base_sample.categories, panels=base_sample.panels, query=DashboardQuery(answer=int(len(overlap_sorted)), answer_type="integer", annotation_refs=refs, params=dict(relations)))
        prompt_artifacts = build_prompt_artifacts(prompt_query_key=QUERY_ID, dynamic_slots=build_prompt_slots(dataset=dataset), instance_seed=int(instance_seed))
        return DashboardTaskPlan(dataset=dataset, prompt_artifacts=prompt_artifacts, relations=relations, answer_gt=TypedValue(type="integer", value=int(len(overlap_sorted))), annotation_refs=refs)

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, _probabilities, task_params = select_task_query_id(instance_seed=int(instance_seed), params={**TASK_PARAM_DEFAULTS, **dict(params)}, supported_query_ids=self.supported_query_ids, default_query_id=QUERY_ID, task_id=self.task_id)
        return run_dashboard_public_task(instance_seed=int(instance_seed), params=task_params, max_attempts=int(max_attempts), selected_query_id=str(selected_query_id), build_plan=self._resolve_top_k_overlap_plan, build_output=_build_task_output)


__all__ = ["ChartsDashboardTopKOverlapCountTask"]
