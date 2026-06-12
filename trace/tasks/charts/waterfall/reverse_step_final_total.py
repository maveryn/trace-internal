"""Scene-package public task for `task_charts__waterfall__reverse_step_final_total`."""

from __future__ import annotations

from ...registry import register_task
from .shared.panel_query import ChartsWaterfallReverseStepFinalTotalTask as _SourceTask


@register_task
class ChartsWaterfallReverseStepFinalTotalTask(_SourceTask):
    """Public scene-package entry point for `reverse_step_final_total`."""

    task_id = "task_charts__waterfall__reverse_step_final_total"
    domain = "charts"
    scene_id = "waterfall"
    objective_contract = "reverse_step_final_total"


__all__ = ["ChartsWaterfallReverseStepFinalTotalTask"]
