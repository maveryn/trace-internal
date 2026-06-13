"""Public task for `task_charts__dashboard__source_rank_difference_value`."""

from __future__ import annotations

from dataclasses import dataclass
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
from trace.tasks.charts.dashboard.shared.metrics import category_by_id, choose_rank_params, panel_by_id, rank_phrase, ranked_category_id


QUERY_ID = "source_rank_difference_value"


@dataclass(frozen=True)
class RankDifferenceOperands:
    """Local operand bundle for the source-rank difference program."""

    source_panel_id: str
    target_panel_id: str
    category_id: str
    source_value: int
    target_value: int
    absolute_delta: int


@register_task
class ChartsDashboardSourceRankDifferenceValueTask:
    """Use source-panel rank selection, then compare the selected category across two panels."""

    task_id = "task_charts__dashboard__source_rank_difference_value"
    domain = DOMAIN
    objective_contract = "source_rank_difference_value"
    supported_query_ids = (QUERY_ID,)
    default_dataset_enabled = True

    def _bind_source_rank_difference_plan(self, instance_seed: int, params: dict[str, Any], selected_query_id: str) -> DashboardTaskPlan:
        """Bind the rank-difference objective and keep both compared marks keyed."""
        del selected_query_id
        rng = spawn_rng(int(instance_seed), f"{SCENE_ID}.{self.objective_contract}.selection")
        base_sample = build_dashboard_base_sample(params, instance_seed=int(instance_seed))
        source_id, target_id = rng.sample([str(panel.panel_id) for panel in base_sample.panels], 2)
        source_panel = panel_by_id(base_sample.panels, source_id)
        target_panel = panel_by_id(base_sample.panels, target_id)
        direction, rank_n = choose_rank_params(rng, params=params, category_count=len(base_sample.categories))
        category_id = ranked_category_id(categories=base_sample.categories, panel=source_panel, direction=direction, rank_n=rank_n)
        selected_category = category_by_id(base_sample.categories, category_id)
        source_value = int(source_panel.values_by_category_id[str(category_id)])
        target_value = int(target_panel.values_by_category_id[str(category_id)])
        answer = abs(int(source_value) - int(target_value))
        if int(answer) == 0:
            raise ValueError("source-rank difference must be non-zero")
        operands = RankDifferenceOperands(
            source_panel_id=str(source_id),
            target_panel_id=str(target_id),
            category_id=str(category_id),
            source_value=int(source_value),
            target_value=int(target_value),
            absolute_delta=int(answer),
        )
        relations = {
            **dict(base_sample.common_params),
            "source_panel_id": str(operands.source_panel_id),
            "source_panel_name": str(source_panel.name),
            "target_panel_id": str(operands.target_panel_id),
            "target_panel_name": str(target_panel.name),
            "rank_direction": str(direction),
            "rank_n": int(rank_n),
            "rank_phrase": rank_phrase(str(direction), int(rank_n)),
            "selected_category_id": str(operands.category_id),
            "selected_category_label": str(selected_category.label),
            "source_value": int(operands.source_value),
            "target_value": int(operands.target_value),
            "absolute_difference": int(operands.absolute_delta),
            "difference_operand_order": ["source_panel", "target_panel"],
            "difference_measure": "absolute_value_gap",
        }
        refs = ((str(operands.source_panel_id), str(operands.category_id)), (str(operands.target_panel_id), str(operands.category_id)))
        dataset = DashboardDataset(scene_variant=SCENE_VARIANT, categories=base_sample.categories, panels=base_sample.panels, query=DashboardQuery(answer=int(operands.absolute_delta), answer_type="integer", annotation_refs=refs, params=dict(relations)))
        prompt_artifacts = build_prompt_artifacts(prompt_query_key=QUERY_ID, dynamic_slots=build_prompt_slots(dataset=dataset), instance_seed=int(instance_seed))
        return DashboardTaskPlan(dataset=dataset, prompt_artifacts=prompt_artifacts, relations=relations, answer_gt=TypedValue(type="integer", value=int(operands.absolute_delta)), annotation_refs=refs, annotation_roles={"source_panel": refs[0], "target_panel": refs[1]})

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, _probabilities, task_params = select_task_query_id(instance_seed=int(instance_seed), params=params, supported_query_ids=self.supported_query_ids, default_query_id=QUERY_ID, task_id=self.task_id)
        return run_dashboard_public_task(instance_seed=int(instance_seed), params=task_params, max_attempts=int(max_attempts), selected_query_id=str(selected_query_id), build_plan=self._bind_source_rank_difference_plan, build_output=_build_task_output)


__all__ = ["ChartsDashboardSourceRankDifferenceValueTask"]
