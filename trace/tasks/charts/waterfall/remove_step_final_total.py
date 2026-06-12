"""Scene-package public task for `task_charts__waterfall__remove_step_final_total`."""

from __future__ import annotations

from ...registry import register_task
from .shared.panel_query import ChartsWaterfallRemoveStepFinalTotalTask as _SourceTask


@register_task
class ChartsWaterfallRemoveStepFinalTotalTask(_SourceTask):
    """Public scene-package entry point for `remove_step_final_total`."""

    task_id = "task_charts__waterfall__remove_step_final_total"
    domain = "charts"
    scene_id = "waterfall"
    objective_contract = "remove_step_final_total"


__all__ = ["ChartsWaterfallRemoveStepFinalTotalTask"]
