"""Step-list task for reading the title after a named source step."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.registry import register_task

from . import _lifecycle


TASK_ID = "task_pages__step_list__step_after_named_step_label"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "step_after_named_step"
SOURCE_QUERY_ID = "step_after_named_step"


@register_task
class PagesStepListStepAfterNamedStepLabelTask:
    """Return the step title immediately after a named source step."""

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
            default=SINGLE_QUERY_ID,
            public_task=TASK_ID,
        )
        return _lifecycle.build_step_list_response(
            instance_seed=int(instance_seed),
            params=task_params,
            selected_branch=str(selected_branch),
            branch_probabilities=branch_probabilities,
            lookup_mode=_lifecycle.AFTER_NAMED_TITLE_MODE,
            source_query_id=SOURCE_QUERY_ID,
            prompt_query_key=PROMPT_QUERY_KEY,
            question_format="step_list_step_after_named_step_label",
        )


__all__ = [
    "PROMPT_QUERY_KEY",
    "SOURCE_QUERY_ID",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "PagesStepListStepAfterNamedStepLabelTask",
]
