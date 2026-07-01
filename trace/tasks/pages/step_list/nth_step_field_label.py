"""Step-list task for reading an ordinally referenced step field."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task

from . import _lifecycle


TASK_ID = "task_pages__step_list__nth_step_field_label"
NTH_STEP_TITLE_QUERY_ID = "nth_step_title"
NTH_STEP_DETAIL_QUERY_ID = "nth_step_detail"
SUPPORTED_QUERY_IDS = (NTH_STEP_TITLE_QUERY_ID, NTH_STEP_DETAIL_QUERY_ID)

_LOOKUP_MODE_BY_QUERY_ID = {
    NTH_STEP_TITLE_QUERY_ID: _lifecycle.ORDINAL_TITLE_MODE,
    NTH_STEP_DETAIL_QUERY_ID: _lifecycle.ORDINAL_DETAIL_MODE,
}
_QUESTION_FORMAT_BY_QUERY_ID = {
    NTH_STEP_TITLE_QUERY_ID: "step_list_nth_step_title_label",
    NTH_STEP_DETAIL_QUERY_ID: "step_list_nth_step_detail_label",
}


@register_task
class PagesStepListNthStepFieldLabelTask:
    """Return the requested title or detail field from an ordinally referenced step card."""

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
            default=NTH_STEP_TITLE_QUERY_ID,
            public_task=TASK_ID,
        )
        query_id = str(selected_branch)
        return _lifecycle.build_step_list_response(
            instance_seed=int(instance_seed),
            params=task_params,
            selected_branch=query_id,
            branch_probabilities=branch_probabilities,
            lookup_mode=_LOOKUP_MODE_BY_QUERY_ID[query_id],
            source_query_id=query_id,
            prompt_query_key=query_id,
            question_format=_QUESTION_FORMAT_BY_QUERY_ID[query_id],
        )


__all__ = [
    "NTH_STEP_DETAIL_QUERY_ID",
    "NTH_STEP_TITLE_QUERY_ID",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "PagesStepListNthStepFieldLabelTask",
]
