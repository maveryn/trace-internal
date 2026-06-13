"""Public task for `task_charts__dashboard__panel_gap_extremum_category_label`."""

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
from trace.tasks.charts.shared.unanswerable import UNANSWERABLE_ANSWER, absence_proof, choose_missing_label, should_use_unanswerable_branch
from trace.tasks.charts.dashboard.shared.metrics import category_by_id, panel_by_id, weighted_choice_from_defaults
from trace.tasks.charts.dashboard.shared.state import SUPPORTED_RANK_DIRECTIONS


QUERY_ID = "panel_gap_extremum_category_label"
TASK_PARAM_DEFAULTS: dict[str, Any] = {"_enable_unanswerable": True}


@register_task
class ChartsDashboardPanelGapExtremumCategoryLabelTask:
    """Find which shared category has the largest or smallest absolute panel gap."""

    task_id = "task_charts__dashboard__panel_gap_extremum_category_label"
    domain = DOMAIN
    objective_contract = "panel_gap_extremum_category_label"
    supported_query_ids = (QUERY_ID,)
    default_dataset_enabled = True

    def _build_unanswerable_plan(self, *, instance_seed: int, params: dict[str, Any], selected_query_id: str, base_sample, first_panel, second_panel, direction: str) -> DashboardTaskPlan:
        rng = spawn_rng(int(instance_seed), f"{SCENE_ID}.{self.objective_contract}.missing_side")
        visible_panel_names = [str(panel.name) for panel in base_sample.panels]
        missing_panel_base_labels, _meta = sample_panel_title_labels(params, count=max(16, len(visible_panel_names) + 8), instance_seed=int(instance_seed), namespace=f"{SCENE_ID}.missing_panel_candidates", reserved_labels=tuple(visible_panel_names))
        missing_panel_candidates = tuple(f"{label} Panel" for label in missing_panel_base_labels)
        missing_panel_name = choose_missing_label(visible_labels=visible_panel_names, candidate_labels=missing_panel_candidates, fallback_prefix="Panel ", instance_seed=int(instance_seed), namespace=f"{SCENE_ID}.missing_panel")
        missing_first = bool(int(rng.randrange(2)) == 0)
        relations = {
            **dict(base_sample.common_params),
            "first_gap_panel_id": "" if missing_first else str(first_panel.panel_id),
            "first_gap_panel_name": str(missing_panel_name if missing_first else first_panel.name),
            "second_gap_panel_id": "" if not missing_first else str(second_panel.panel_id),
            "second_gap_panel_name": str(missing_panel_name if not missing_first else second_panel.name),
            "gap_extremum_direction": str(direction),
            "gap_extremum_phrase": "largest" if str(direction) == "largest" else "smallest",
            "answer_category_id": "",
            "answer_category_label": UNANSWERABLE_ANSWER,
            "answerability": "unanswerable",
            "absence_proof": absence_proof(requested_item=f"panel {missing_panel_name}", visible_candidates=visible_panel_names, checked_scope="dashboard panel titles", absence_reason="one named comparison panel is not shown in the dashboard"),
        }
        dataset = DashboardDataset(scene_variant=SCENE_VARIANT, categories=base_sample.categories, panels=base_sample.panels, query=DashboardQuery(answer=UNANSWERABLE_ANSWER, answer_type="string", annotation_refs=(), params=dict(relations)))
        prompt_artifacts = build_prompt_artifacts(prompt_query_key=QUERY_ID, dynamic_slots=build_prompt_slots(dataset=dataset), instance_seed=int(instance_seed))
        return DashboardTaskPlan(dataset=dataset, prompt_artifacts=prompt_artifacts, relations=relations, answer_gt=TypedValue(type="string", value=UNANSWERABLE_ANSWER), annotation_refs=(), annotation_roles={})

    def _build_plan(self, instance_seed: int, params: dict[str, Any], selected_query_id: str) -> DashboardTaskPlan:
        effective_params = {**TASK_PARAM_DEFAULTS, **dict(params)}
        rng = spawn_rng(int(instance_seed), f"{SCENE_ID}.{self.objective_contract}.selection")
        base_sample = build_dashboard_base_sample(effective_params, instance_seed=int(instance_seed))
        first_panel_id, second_panel_id = rng.sample([str(panel.panel_id) for panel in base_sample.panels], 2)
        first_panel = panel_by_id(base_sample.panels, first_panel_id)
        second_panel = panel_by_id(base_sample.panels, second_panel_id)
        direction = weighted_choice_from_defaults(rng, params=effective_params, key="gap_extremum_direction", supported=SUPPORTED_RANK_DIRECTIONS, fallback_weights_key="gap_extremum_weights")
        if should_use_unanswerable_branch(effective_params, instance_seed=int(instance_seed), namespace=f"{SCENE_ID}.panel_gap_extremum_category_label", enabled=bool(effective_params.get("_enable_unanswerable", False))):
            return self._build_unanswerable_plan(instance_seed=int(instance_seed), params=effective_params, selected_query_id=str(selected_query_id), base_sample=base_sample, first_panel=first_panel, second_panel=second_panel, direction=str(direction))
        gaps_by_category = {str(category.category_id): abs(int(first_panel.values_by_category_id[str(category.category_id)]) - int(second_panel.values_by_category_id[str(category.category_id)])) for category in base_sample.categories}
        if len(set(int(value) for value in gaps_by_category.values())) != len(gaps_by_category):
            raise ValueError("panel gap extremum must be unique across categories")
        answer_category = sorted(base_sample.categories, key=lambda category: int(gaps_by_category[str(category.category_id)]), reverse=str(direction) == "largest")[0]
        first_value = int(first_panel.values_by_category_id[str(answer_category.category_id)])
        second_value = int(second_panel.values_by_category_id[str(answer_category.category_id)])
        answer_gap = int(gaps_by_category[str(answer_category.category_id)])
        relations = {
            **dict(base_sample.common_params),
            "first_gap_panel_id": str(first_panel_id),
            "first_gap_panel_name": str(first_panel.name),
            "second_gap_panel_id": str(second_panel_id),
            "second_gap_panel_name": str(second_panel.name),
            "gap_extremum_direction": str(direction),
            "gap_extremum_phrase": "largest" if str(direction) == "largest" else "smallest",
            "answer_category_id": str(answer_category.category_id),
            "answer_category_label": str(answer_category.label),
            "first_value": int(first_value),
            "second_value": int(second_value),
            "answer_gap": int(answer_gap),
            "gaps_by_category_id": dict(gaps_by_category),
            "answerability": "answerable",
        }
        refs = ((str(first_panel_id), str(answer_category.category_id)), (str(second_panel_id), str(answer_category.category_id)))
        dataset = DashboardDataset(scene_variant=SCENE_VARIANT, categories=base_sample.categories, panels=base_sample.panels, query=DashboardQuery(answer=str(answer_category.label), answer_type="string", annotation_refs=refs, params=dict(relations)))
        prompt_artifacts = build_prompt_artifacts(prompt_query_key=QUERY_ID, dynamic_slots=build_prompt_slots(dataset=dataset), instance_seed=int(instance_seed))
        return DashboardTaskPlan(dataset=dataset, prompt_artifacts=prompt_artifacts, relations=relations, answer_gt=TypedValue(type="string", value=str(answer_category.label)), annotation_refs=refs, annotation_roles={"first_panel": refs[0], "second_panel": refs[1]})

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, _probabilities, task_params = select_task_query_id(instance_seed=int(instance_seed), params={**TASK_PARAM_DEFAULTS, **dict(params)}, supported_query_ids=self.supported_query_ids, default_query_id=QUERY_ID, task_id=self.task_id)
        return run_dashboard_public_task(instance_seed=int(instance_seed), params=task_params, max_attempts=int(max_attempts), selected_query_id=str(selected_query_id), build_plan=self._build_plan, build_output=_build_task_output)


__all__ = ["ChartsDashboardPanelGapExtremumCategoryLabelTask"]
