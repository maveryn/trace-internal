"""Step-list task for finding the step title or number from a visible detail."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task

from . import _lifecycle


TASK_ID = "task_pages__step_list__step_for_detail_label"
SUPPORTED_QUERY_IDS = ("step_title_for_detail", "step_number_for_detail")


@register_task
class PagesStepListStepForDetailLabelTask:
    """Return the owning step title or number for a named detail line."""

    task_id = TASK_ID
    domain = _lifecycle.DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Mapping[str, Any], max_attempts: int):
        del max_attempts
        selected_branch, branch_probabilities, task_params = _lifecycle.select_public_branch(
            instance_seed=int(instance_seed),
            params=params,
            supported=SUPPORTED_QUERY_IDS,
            default="step_title_for_detail",
            public_task=TASK_ID,
        )
        lookup_mode = (
            _lifecycle.DETAIL_TO_NUMBER_MODE
            if str(selected_branch) == "step_number_for_detail"
            else _lifecycle.DETAIL_TO_TITLE_MODE
        )
        return _lifecycle.build_step_list_response(
            instance_seed=int(instance_seed),
            params=task_params,
            selected_branch=str(selected_branch),
            branch_probabilities=branch_probabilities,
            lookup_mode=lookup_mode,
            source_query_id=str(selected_branch),
            prompt_query_key=str(selected_branch),
            question_format="step_list_step_for_detail_label",
        )


__all__ = [
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "PagesStepListStepForDetailLabelTask",
]
