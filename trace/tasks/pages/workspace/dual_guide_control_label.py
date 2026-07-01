"""Workspace task identifying a target control from two visible guide cues."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.registry import register_task

from . import _lifecycle


TASK_ID = "task_pages__workspace__dual_guide_control_label"
OBJECTIVE_KEY = _lifecycle.PROMPT_DUAL_GUIDE_LABEL_KEY
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)


@register_task
class PagesWorkspaceDualGuideControlLabelTask:
    """Identify the labeled workspace control matching context and action guide cues."""

    task_id = TASK_ID
    domain = "pages"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Mapping[str, Any], max_attempts: int):
        del max_attempts
        return _lifecycle.build_workspace_response(
            instance_seed=int(instance_seed),
            params=params,
            task_id=TASK_ID,
            objective_key=OBJECTIVE_KEY,
            question_format="workspace_dual_guide_control_label",
        )


__all__ = [
    "OBJECTIVE_KEY",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "PagesWorkspaceDualGuideControlLabelTask",
]
