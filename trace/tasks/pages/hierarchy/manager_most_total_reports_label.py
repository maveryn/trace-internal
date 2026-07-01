"""Hierarchy task for selecting the manager with the largest total reporting chain."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task

from . import _lifecycle


TASK_ID = "task_pages__hierarchy__manager_most_total_reports_label"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "manager_most_total_reports_label"
QUESTION_FORMAT = "hierarchy_org_chart"


def _build_total_reports_objective() -> _lifecycle.HierarchyObjectiveBinding:
    """Bind total-report extremum answer and annotation semantics."""

    return _lifecycle.HierarchyObjectiveBinding(
        semantic_branch_key=PROMPT_QUERY_KEY,
        prompt_branch_key=PROMPT_QUERY_KEY,
        answer_type="string",
        annotation_type="bbox",
        question_format=QUESTION_FORMAT,
    )


@register_task
class PagesHierarchyManagerMostTotalReportsLabelTask:
    """Select the non-CEO manager with the most total people below them."""

    task_id = TASK_ID
    domain = _lifecycle.DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one total-report manager extremum hierarchy instance."""

        del max_attempts
        selected_branch, branch_probabilities, task_params = _lifecycle.select_public_branch(
            instance_seed=int(instance_seed),
            params=params,
            supported=SUPPORTED_QUERY_IDS,
            default=SINGLE_QUERY_ID,
            public_task=TASK_ID,
        )
        objective = _build_total_reports_objective()
        return _lifecycle.render_bound_hierarchy(
            instance_seed=int(instance_seed),
            params=task_params,
            selected_branch=str(selected_branch),
            branch_probabilities=branch_probabilities,
            objective=objective,
        )


__all__ = [
    "PROMPT_QUERY_KEY",
    "QUESTION_FORMAT",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "PagesHierarchyManagerMostTotalReportsLabelTask",
]
