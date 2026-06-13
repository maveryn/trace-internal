"""Public task for `task_charts__dashboard__shared_label_rank_gap_extremum`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.dashboard._lifecycle import DashboardTaskPlan, MaterializedDashboardTask, dashboard_task_output_fields, run_dashboard_public_task
from trace.tasks.charts.dashboard.shared.prompts import build_prompt_artifacts, build_prompt_slots
from trace.tasks.charts.dashboard.shared.sampling import build_dashboard_base_sample, sample_panel_title_labels
from trace.tasks.charts.dashboard.shared.state import DOMAIN, SCENE_ID, SCENE_VARIANT, OPTION_LETTERS, DashboardDataset, DashboardQuery
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id


def _build_task_output(materialized: MaterializedDashboardTask) -> TaskOutput:
    return TaskOutput(**dashboard_task_output_fields(materialized))
from trace.tasks.charts.dashboard.shared.metrics import category_by_id, panel_by_id, rank_positions_by_category_id


HIGH_TO_LOW_LARGEST_GAP_QUERY_ID = "high_to_low_largest_rank_gap_label"
HIGH_TO_LOW_SMALLEST_GAP_QUERY_ID = "high_to_low_smallest_rank_gap_label"
LOW_TO_HIGH_LARGEST_GAP_QUERY_ID = "low_to_high_largest_rank_gap_label"
LOW_TO_HIGH_SMALLEST_GAP_QUERY_ID = "low_to_high_smallest_rank_gap_label"
RANK_AND_GAP_DIRECTIONS_BY_QUERY_ID = {
    HIGH_TO_LOW_LARGEST_GAP_QUERY_ID: ("largest", "largest"),
    HIGH_TO_LOW_SMALLEST_GAP_QUERY_ID: ("largest", "smallest"),
    LOW_TO_HIGH_LARGEST_GAP_QUERY_ID: ("smallest", "largest"),
    LOW_TO_HIGH_SMALLEST_GAP_QUERY_ID: ("smallest", "smallest"),
}


@register_task
class ChartsDashboardSharedLabelRankGapExtremumTask:
    """Compare category rank positions across two panels and return the extremum gap label."""

    task_id = "task_charts__dashboard__shared_label_rank_gap_extremum"
    domain = DOMAIN
    objective_contract = "shared_label_rank_gap_extremum"
    supported_query_ids = (
        HIGH_TO_LOW_LARGEST_GAP_QUERY_ID,
        HIGH_TO_LOW_SMALLEST_GAP_QUERY_ID,
        LOW_TO_HIGH_LARGEST_GAP_QUERY_ID,
        LOW_TO_HIGH_SMALLEST_GAP_QUERY_ID,
    )
    default_dataset_enabled = True

    def _resolve_shared_rank_gap_plan(self, instance_seed: int, params: dict[str, Any], selected_query_id: str) -> DashboardTaskPlan:
        """Bind the category whose rank-position gap is uniquely largest or smallest."""
        rng = spawn_rng(int(instance_seed), f"{SCENE_ID}.{self.objective_contract}.selection")
        base_sample = build_dashboard_base_sample(params, instance_seed=int(instance_seed))
        first_panel_id, second_panel_id = rng.sample([str(panel.panel_id) for panel in base_sample.panels], 2)
        first_panel = panel_by_id(base_sample.panels, first_panel_id)
        second_panel = panel_by_id(base_sample.panels, second_panel_id)
        rank_direction, gap_direction = RANK_AND_GAP_DIRECTIONS_BY_QUERY_ID[str(selected_query_id)]
        first_ranks = rank_positions_by_category_id(categories=base_sample.categories, panel=first_panel, direction=str(rank_direction))
        second_ranks = rank_positions_by_category_id(categories=base_sample.categories, panel=second_panel, direction=str(rank_direction))
        gaps_by_category = {str(category.category_id): abs(int(first_ranks[str(category.category_id)]) - int(second_ranks[str(category.category_id)])) for category in base_sample.categories}
        target_gap = max(int(value) for value in gaps_by_category.values()) if str(gap_direction) == "largest" else min(int(value) for value in gaps_by_category.values())
        answer_category_ids = [str(category_id) for category_id, gap in gaps_by_category.items() if int(gap) == int(target_gap)]
        if len(answer_category_ids) != 1:
            raise ValueError("shared-label rank-gap extremum must have a unique answer")
        answer_category = category_by_id(base_sample.categories, answer_category_ids[0])
        rank_direction_phrase = "highest-to-lowest" if str(rank_direction) == "largest" else "lowest-to-highest"
        relations = {
            **dict(base_sample.common_params),
            "first_rank_gap_panel_id": str(first_panel_id),
            "first_rank_gap_panel_name": str(first_panel.name),
            "second_rank_gap_panel_id": str(second_panel_id),
            "second_rank_gap_panel_name": str(second_panel.name),
            "rank_direction": str(rank_direction),
            "rank_direction_phrase": str(rank_direction_phrase),
            "gap_extremum_direction": str(gap_direction),
            "gap_extremum_phrase": "largest" if str(gap_direction) == "largest" else "smallest",
            "answer_category_id": str(answer_category.category_id),
            "answer_category_label": str(answer_category.label),
            "first_rank_position": int(first_ranks[str(answer_category.category_id)]),
            "second_rank_position": int(second_ranks[str(answer_category.category_id)]),
            "answer_rank_gap": int(target_gap),
            "first_rank_positions_by_category_id": dict(first_ranks),
            "second_rank_positions_by_category_id": dict(second_ranks),
            "rank_gaps_by_category_id": dict(gaps_by_category),
        }
        refs = ((str(first_panel_id), str(answer_category.category_id)), (str(second_panel_id), str(answer_category.category_id)))
        dataset = DashboardDataset(scene_variant=SCENE_VARIANT, categories=base_sample.categories, panels=base_sample.panels, query=DashboardQuery(answer=str(answer_category.label), answer_type="string", annotation_refs=refs, params=dict(relations)))
        prompt_artifacts = build_prompt_artifacts(prompt_query_key=str(selected_query_id), dynamic_slots=build_prompt_slots(dataset=dataset), instance_seed=int(instance_seed))
        return DashboardTaskPlan(dataset=dataset, prompt_artifacts=prompt_artifacts, relations=relations, answer_gt=TypedValue(type="string", value=str(answer_category.label)), annotation_refs=refs, annotation_roles={"first_panel": refs[0], "second_panel": refs[1]})

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, _probabilities, task_params = select_task_query_id(instance_seed=int(instance_seed), params=params, supported_query_ids=self.supported_query_ids, default_query_id=HIGH_TO_LOW_LARGEST_GAP_QUERY_ID, task_id=self.task_id)
        return run_dashboard_public_task(instance_seed=int(instance_seed), params=task_params, max_attempts=int(max_attempts), selected_query_id=str(selected_query_id), build_plan=self._resolve_shared_rank_gap_plan, build_output=_build_task_output)


__all__ = ["ChartsDashboardSharedLabelRankGapExtremumTask"]
