"""Scene-package public task for `task_charts__waterfall__running_total_value`."""

from __future__ import annotations

from ...registry import register_task
from .shared.panel_query import ChartsWaterfallRunningTotalValueTask as _SourceTask


@register_task
class ChartsWaterfallRunningTotalValueTask(_SourceTask):
    """Public scene-package entry point for `running_total_value`."""

    task_id = "task_charts__waterfall__running_total_value"
    domain = "charts"
    scene_id = "waterfall"
    objective_contract = "running_total_value"


__all__ = ["ChartsWaterfallRunningTotalValueTask"]
